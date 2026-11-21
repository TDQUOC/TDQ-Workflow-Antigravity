"""Cổng nhắc đọc lại — `hooks/scripts/read_gate.py`.

Vì sao cổng này tồn tại, bằng số đo: trong một phiên thật 22,76 MB, `scripts/tdq_state.py` bị đọc
**12 lần** và `scripts/build_portable.py` **19 lần**; riêng hai file đó chiếm 502.816 token, bằng
28% toàn bộ nội dung đọc vào của phiên. Repo đã có luật chống việc này ở
`skills/tdq-conventions/references/context-budget.md`, nhưng luật nằm trong một file reference và
không cổng nào cưỡng chế.

Cổng CHỈ NHẮC, không bao giờ chặn — user chốt vậy, và nó đúng với `docs/kien-truc.md` 2026-07-29
("hook chỉ nhắc và kiểm bằng hiệu ứng thật"). Agent tự quyết có đọc lại hay không.

Bốn hành vi bị khoá ở đây, chạy riêng được bằng `-k`: `nhac`, `im_vung`, `im_doi`, `mot_lan`,
cộng `nhe` (không spawn tiến trình, không đọc nội dung file) và `log`.
"""
import io
import json
import os
import sys
import tempfile
import time
import unittest

import pytest

from helper import ROOT, run_hook

sys.path.insert(0, os.path.join(ROOT, "scripts"))
import tdq_state  # noqa: E402

sys.path.insert(0, os.path.join(ROOT, 'hooks', 'scripts'))
import _common  # noqa: E402
import read_gate  # noqa: E402 — lấy hằng số từ chính cổng, khỏi chép tay
import subagent_stop  # noqa: E402
read_gate_SO_SACH = read_gate.SO_SACH
read_gate_TRAN_DONG = read_gate.TRAN_DONG

pytestmark = pytest.mark.smoke

GATE = "read_gate.py"
PHIEN = "phien-thu-read-gate"


def _nguon_khong_docstring():
    """Mã của cổng, đã bỏ docstring và chú thích.

    Phải bỏ: bản đầu của phép kiểm này grep chữ "subprocess" trên cả file, nên nó bắt luôn câu
    "No subprocess" trong chính docstring — đỏ vì một lời hứa, không vì một lời gọi.
    """
    import ast
    nguon = io.open(os.path.join(ROOT, "hooks", "scripts", "read_gate.py"),
                    encoding="utf-8").read()
    cay = ast.parse(nguon)
    for nut in ast.walk(cay):
        if isinstance(nut, (ast.Module, ast.FunctionDef, ast.ClassDef)) and ast.get_docstring(nut):
            nut.body = nut.body[1:]
    return ast.unparse(cay)


def _payload(duong, cwd=None, **tool_input):
    vao = {"file_path": duong}
    vao.update(tool_input)
    return {"session_id": PHIEN, "cwd": cwd, "tool_name": "Read", "tool_input": vao}


class BaseReadGate(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cwd = self.tmp.name
        os.makedirs(os.path.join(self.cwd, "docs", "tdq"), exist_ok=True)
        self.tep = os.path.join(self.cwd, "to-sach.md")
        with io.open(self.tep, "w", encoding="utf-8") as fh:
            # Phải lớn hơn ngưỡng của cổng: file nhỏ thì đọc lại không đáng một dòng nhắc.
            # Các file thật gây ra vấn đề này (`tdq_state.py`, `build_portable.py`) là 8-27 KB.
            fh.write("# Một file\n" + "dòng nội dung dài cho đủ kích thước thật\n" * 300)

    def chay(self, tep=None, log="0", **tool_input):
        """Gọi cổng một lần -> (rc, stdout, stderr).

        Payload VÀ env dựng ở cùng một chỗ: sổ của cổng nằm dưới `cwd` của payload còn
        `TDQ_PROJECT_DIR` nằm trong env, nên test nào đặt thiếu một trong hai sẽ đọc một cái sổ
        khác với cái nó vừa ghi.
        """
        return run_hook(GATE, _payload(tep or self.tep, self.cwd, **tool_input),
                        env={"TDQ_PROJECT_DIR": self.cwd, "TDQ_LOG": log})

    def goi(self, **tool_input):
        rc, out, err = self.chay(**tool_input)
        self.assertEqual(rc, 0, f"cổng phải luôn thoát 0 — nó chỉ nhắc: {err}")
        return out

    def nhac_trong(self, out):
        """-> dòng nhắc, hoặc "" khi cổng im lặng."""
        if not out:
            return ""
        goi = json.loads(out).get("hookSpecificOutput") or {}
        self.assertEqual(goi.get("permissionDecision"), "allow",
                         "cổng này KHÔNG được chặn, dù một lần")
        return goi.get("additionalContext") or ""


class NhacKhiDocLai(BaseReadGate):
    def test_nhac_lan_doc_thu_hai_cua_file_khong_doi(self):
        self.assertEqual(self.nhac_trong(self.goi()), "", "lần đọc đầu phải im lặng")
        nhac = self.nhac_trong(self.goi())
        self.assertIn("TDQ:DOC", nhac)
        self.assertIn("to-sach.md", nhac)

    def test_nhac_mang_so_lieu_chu_khong_phai_loi_khuyen_chung(self):
        """Nhắc suông thì agent bỏ qua. Nhắc phải nói ra đã đọc ở đâu và tốn bao nhiêu."""
        self.goi()
        nhac = self.nhac_trong(self.goi())
        self.assertRegex(nhac, r"\d", "dòng nhắc phải mang con số")

    def test_nhac_khi_lap_doan_offset_limit(self):
        """Đọc lặp lại cùng một đoạn có overlap >= 70% từ lần 2 trở lên thì phải nhắc."""
        # Lần 1: đọc [1000, 1100] (offset=1000, limit=100) -> lần đầu, im lặng ("")
        self.assertEqual(self.nhac_trong(self.goi(offset=1000, limit=100)), "")
        # Lần 2: đọc [1020, 1120] (offset=1020, limit=100, overlap 80/100 = 80% >= 70%) -> repeat_count < 2 -> vẫn im lặng
        self.assertEqual(self.nhac_trong(self.goi(offset=1020, limit=100)), "")
        # Lần 3: đọc [1010, 1110] (offset=1010, limit=100, overlap >= 70%) -> repeat_count >= 2 -> nhắc [TDQ:DOC]
        nhac = self.nhac_trong(self.goi(offset=1010, limit=100))
        self.assertIn("TDQ:DOC", nhac)
        self.assertIn("to-sach.md", nhac)
        self.assertTrue(any(tu in nhac.lower() for tu in ("lặp", "overlap", "trùng", "repeat")),
                        f"thông điệp nhắc phải đề cập lặp/trùng lặp: {nhac}")

    def test_thong_diep_remind_ai(self):
        """Thông điệp nhắc AI phải mang số dòng, tên file và chỉ dẫn hành động rõ ràng."""
        self.goi(offset=1000, limit=100)
        self.goi(offset=1005, limit=100)
        nhac = self.nhac_trong(self.goi(offset=1010, limit=100))
        self.assertIn("to-sach.md", nhac)
        self.assertIn("1010-1110", nhac)
        self.assertIn("tổng hợp", nhac.lower())


class ImLangDungCho(BaseReadGate):
    def test_im_vung_khac_thi_khong_nhac(self):
        """Đọc vùng khác KHÔNG phải đọc lại — đó chính là việc cổng này muốn khuyến khích."""
        self.assertEqual(self.nhac_trong(self.goi(offset=200, limit=40)), "")
        self.assertEqual(self.nhac_trong(self.goi(offset=500, limit=50)), "")

    def test_im_doi_file_thi_khong_nhac(self):
        self.goi()
        with io.open(self.tep, "a", encoding="utf-8") as fh:
            fh.write("một dòng mới làm đổi kích thước\n")
        self.assertEqual(self.nhac_trong(self.goi()), "")

    def test_im_lan_dau_tien(self):
        self.assertEqual(self.nhac_trong(self.goi()), "")

    def test_im_khi_file_khong_ton_tai(self):
        rc, out, _ = self.chay(tep=os.path.join(self.cwd, "khong-co.md"))
        self.assertEqual(rc, 0)
        self.assertEqual(self.nhac_trong(out), "", "không có file thì không có gì để nói")


class NhacMotLanMoiFile(BaseReadGate):
    def test_mot_lan_cho_moi_file(self):
        self.goi()
        self.assertNotEqual(self.nhac_trong(self.goi()), "", "lần hai phải nhắc")
        self.assertEqual(self.nhac_trong(self.goi()), "",
                         "lần ba trở đi im — đã nhắc về file này rồi")

    def test_mot_lan_nhung_file_khac_van_duoc_nhac(self):
        """Dedupe theo FILE, không theo mã. `_common.remind` dedupe theo mã trên cả phiên, nên
        dùng nó sẽ làm file thứ hai không bao giờ được nhắc."""
        tep2 = os.path.join(self.cwd, "to-sach-hai.md")
        with io.open(tep2, "w", encoding="utf-8") as fh:
            fh.write("# File hai\n" + "nội dung dài cho đủ kích thước thật\n" * 300)
        self.goi()
        self.assertNotEqual(self.nhac_trong(self.goi()), "")
        out = ""
        for _ in range(2):
            out = self.goi(tep=tep2)
        self.assertNotEqual(self.nhac_trong(out), "", "file thứ hai cũng phải được nhắc")


class CongPhaiNhe(BaseReadGate):
    def test_nhe_khong_spawn_tien_trinh_con(self):
        """Cổng chạy trước MỌI lần `Read`, nên nó không được gọi tiến trình con nào."""
        nguon = _nguon_khong_docstring()
        for xau in ("subprocess", "os.system(", "os.popen(", "os.spawn"):
            self.assertNotIn(xau, nguon, f"cổng không được dùng {xau}")

    def test_nhe_khong_doc_noi_dung_file_duoc_hoi(self):
        """Nó chỉ cần `os.stat`. Đọc nội dung file để đếm token là tự nhân đôi cái nó muốn cắt."""
        nguon = _nguon_khong_docstring()
        self.assertNotIn("count_tokens", nguon)
        self.assertNotIn("io.open", nguon)


class LogService(BaseReadGate):
    def test_log_tat_duoc_bang_bien_moi_truong(self):
        _, _, err = self.chay(log="0")
        self.assertEqual(err, "")

    def test_log_bat_mac_dinh_co_timestamp(self):
        _, _, err = self.chay(log="1")
        self.assertRegex(err, r"\[\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")


class GhiSoRieng(BaseReadGate):
    """Sổ của cổng — và vì sao nó KHÔNG dùng sổ lượt chung.

    Sổ lượt bị `prompt_context.py` xoá ở MỖI lần user gửi prompt (`turn_log_clear`), nên ký ức
    dựng trên nó chỉ thấy được việc đọc lại trong MỘT lượt — còn thứ cần bắt (một file đọc 12
    lần) xảy ra QUA NHIỀU lượt của một phiên.
    """

    def so(self):
        duong = os.path.join(self.cwd, *read_gate_SO_SACH.split(os.sep))
        if not os.path.isfile(duong):
            return []
        return [json.loads(d) for d in io.open(duong, encoding='utf-8') if d.strip()]

    def test_so_ghi_duong_dan_dang_posix(self):
        """Đường dẫn trong sổ được so với đầu ra của git, thứ luôn in `/`."""
        self.goi()
        duong = [r.get('path') for r in self.so() if r.get('path')]
        self.assertTrue(duong, 'cổng phải ghi lại mỗi lần đọc vào sổ của nó')
        self.assertNotIn("\\", duong[-1])

    def test_so_khong_dung_so_luot_chung(self):
        self.goi()
        self.assertEqual(tdq_state.turn_log_read(self.cwd, session=PHIEN), [],
                         'cổng không được ghi vào sổ lượt — sổ đó bị xoá mỗi prompt')

    def test_so_khong_phinh_vo_han(self):
        duong = os.path.join(self.cwd, *read_gate_SO_SACH.split(os.sep))
        os.makedirs(os.path.dirname(duong), exist_ok=True)
        with io.open(duong, 'w', encoding='utf-8') as fh:
            for i in range(read_gate_TRAN_DONG + 50):
                fh.write(json.dumps({'ts': time.time(), 'session': PHIEN,
                                     'path': f'x{i}.md', 'dau': 0, 'cuoi': 0,
                                     'byte': 1, 'mtime': 1, 'da_nhac': False}) + "\n")
        self.goi()
        self.assertLessEqual(len(self.so()), read_gate_TRAN_DONG,
                             'sổ phải được rút gọn khi quá trần')


class SoKhongVaoRepo(unittest.TestCase):
    """Sổ của cổng phải bị `.gitignore` — nó là chuyện của MỘT phiên trên MỘT máy.

    Không có luật này thì mỗi lượt kết turn lại thêm một file lạ vào `git status`, và tới lúc
    commit thì sổ đọc của máy người này đi vào repo của người khác.
    """

    def test_so_bi_gitignore(self):
        duong = io.open(os.path.join(ROOT, ".gitignore"), encoding="utf-8").read()
        self.assertIn(read_gate.SO_SACH.replace(os.sep, "/"), duong,
                      "sổ của cổng chưa bị .gitignore")


class NhoQuaNhieuLuot(BaseReadGate):
    """Ca thật mà cổng được dựng để bắt: cùng một file, đọc trọn ở HAI lượt khác nhau."""

    def test_mot_lan_van_nhac_sau_khi_so_luot_bi_xoa(self):
        self.assertEqual(self.nhac_trong(self.goi()), '', 'lần đọc đầu phải im')
        # Đúng việc `prompt_context.py` làm khi user gửi prompt kế tiếp.
        tdq_state.turn_log_clear(self.cwd, PHIEN)
        self.assertNotEqual(self.nhac_trong(self.goi()), '',
                            'đọc lại ở lượt sau vẫn là đọc lại — phải nhắc')


class NhacCcrFileDuLieuLon(BaseReadGate):
    """T3.2: non-blocking CCR hint when reading large structured/log files > 32 KB."""

    def test_nhac_ccr_cho_file_log_lon_va_khong_chan(self):
        tep_log = os.path.join(self.cwd, "app.log")
        with io.open(tep_log, "w", encoding="utf-8") as fh:
            fh.write("ERROR failed step\n" * 2500)
        rc, out, _err = self.chay(tep=tep_log)
        self.assertEqual(rc, 0)
        nhac = self.nhac_trong(out)
        self.assertIn("tdq_ccr.py summarize", nhac)
        self.assertEqual(self.nhac_trong(self.goi(tep=tep_log)), "")

    def test_im_voi_file_code_lon_va_doc_phan_doan(self):
        tep_py = os.path.join(self.cwd, "big.py")
        with io.open(tep_py, "w", encoding="utf-8") as fh:
            fh.write("x = 1\n" * 7000)
        self.assertEqual(self.nhac_trong(self.goi(tep=tep_py)), "")
        tep_json = os.path.join(self.cwd, "big.json")
        with io.open(tep_json, "w", encoding="utf-8") as fh:
            fh.write('{"k": "' + ("a" * 35000) + '"}\n')
        self.assertEqual(self.nhac_trong(self.goi(tep=tep_json, offset=1, limit=20)), "")


class TestScopedWriteSecurityAndInvestigateHooks(unittest.TestCase):
    """V2 M3/M4: 5-layer scoped-write security, subagent_stop, static anchor, TDQ:GON, hooks.json."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.cwd = self._tmp.name
        os.makedirs(os.path.join(self.cwd, "docs", "tdq", "artifacts", "2026-11-21-inv"), exist_ok=True)
        os.makedirs(os.path.join(self.cwd, "docs", "tdq", "artifacts", "other-slug"), exist_ok=True)
        os.makedirs(os.path.join(self.cwd, "docs", "tdq", "research"), exist_ok=True)
        st = tdq_state.default_state()
        st.update({
            "active_request": "2026-11-21-inv",
            "lane": "full",
            "phase": "implement",
            "spec_approved": True,
            "plan_approved": True,
            "implement_mode": "subagent",
            "work_kind": "investigate",
        })
        tdq_state.save(self.cwd, st)
        self.state = st

    def tearDown(self):
        self._tmp.cleanup()

    def test_normalize_tool_aliases_maps_target_file_and_line_ranges(self):
        norm = _common._normalize_tool_aliases("read_file", {
            "TargetFile": "docs/tdq/artifacts/2026-11-21-inv/t1.md",
            "StartLine": 10,
            "EndLine": 25,
        })
        self.assertEqual(norm["file_path"], "docs/tdq/artifacts/2026-11-21-inv/t1.md")
        self.assertEqual(norm["offset"], 10)
        self.assertEqual(norm["limit"], 16)

    def test_5_layer_scoped_write_security_matrix(self):
        slug = "2026-11-21-inv"
        allowed_roles = ("tdq-explorer", "explorer", "tdq-debugger", "debugger", "tdq-reviewer", "reviewer")
        for role in allowed_roles:
            with self.subTest(allowed_role=role):
                self.assertTrue(_common.is_investigation_artifact_target(
                    f"docs/tdq/artifacts/{slug}/shard.md", self.cwd, role, self.state))
                self.assertTrue(_common.is_investigation_artifact_target(
                    f"docs/tdq/artifacts/{slug}/nested/deep/shard.json", self.cwd, role, self.state))
                self.assertTrue(_common.is_investigation_artifact_target(
                    f"docs/tdq/research/{slug}.md", self.cwd, role, self.state))
                self.assertTrue(_common.is_investigation_artifact_target(
                    f"docs/tdq/research/{slug}-part1.md", self.cwd, role, self.state))

        denied_cases = [
            ("tdq-security-reviewer", f"docs/tdq/artifacts/{slug}/shard.md"),
            ("security-reviewer", f"docs/tdq/artifacts/{slug}/shard.md"),
            ("tdq-browser", f"docs/tdq/artifacts/{slug}/shard.md"),
            ("browser", f"docs/tdq/artifacts/{slug}/shard.md"),
            ("subagent", f"docs/tdq/artifacts/{slug}/shard.md"),
            ("", f"docs/tdq/artifacts/{slug}/shard.md"),
            ("fake-explorer", f"docs/tdq/artifacts/{slug}/shard.md"),
            ("tdq-qc-tester", f"docs/tdq/artifacts/{slug}/shard.md"),
            ("tdq-explorer", f"docs/tdq/artifacts/{slug}/evidence.jsonl"),
            ("tdq-explorer", f"docs/tdq/artifacts/{slug}/evidence-log.md"),
            ("tdq-explorer", f"docs/tdq/artifacts/{slug}/trial_1.json"),
            ("tdq-explorer", f"docs/tdq/artifacts/{slug}/rec_01.json"),
            ("tdq-explorer", f"docs/tdq/artifacts/{slug}/evil.py"),
            ("tdq-explorer", f"docs/tdq/artifacts/{slug}/../other-slug/pwn.md"),
            ("tdq-explorer", f"docs/tdq/artifacts/other-slug/shard.md"),
            ("tdq-explorer", f"docs/tdq/research/{slug}/nested.md"),
            ("tdq-explorer", "docs/tdq/research/other-slug.md"),
            ("tdq-explorer", "scripts/tdq_state.py"),
            ("tdq-explorer", f"docs/tdq/artifacts/{slug}/sub/../../outside.md"),
        ]
        for role, path in denied_cases:
            with self.subTest(role=role, path=path):
                self.assertFalse(_common.is_investigation_artifact_target(path, self.cwd, role, self.state))

        # Traversal in active_slug must fail closed
        bad_state = dict(self.state, active_request="../escape")
        self.assertFalse(_common.is_investigation_artifact_target(
            "docs/tdq/artifacts/2026-11-21-inv/t1.md", self.cwd, "tdq-explorer", bad_state))

    def test_edit_gate_allows_scoped_write_and_blocks_security_reviewer(self):
        from helper import decision as get_decision
        ok_payload = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Edit",
            "cwd": self.cwd,
            "session_id": "exp-scoped-ok",
            "agent_id": "ag-exp",
            "agent_type": "tdq-explorer",
            "tool_input": {"file_path": "docs/tdq/artifacts/2026-11-21-inv/t1.md"},
        }
        rc, out, _ = run_hook("edit_gate.py", ok_payload)
        self.assertEqual(rc, 0)
        self.assertNotIn("deny", out)

        bad_payload = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Edit",
            "cwd": self.cwd,
            "session_id": "sec-rev-deny",
            "agent_id": "ag-sec",
            "agent_type": "tdq-security-reviewer",
            "tool_input": {"file_path": "docs/tdq/artifacts/2026-11-21-inv/t1.md"},
        }
        rc2, out2, _ = run_hook("edit_gate.py", bad_payload)
        self.assertEqual(rc2, 0)
        self.assertEqual(get_decision(out2)[0], "deny")
        self.assertIn("READONLY", out2)

    def test_subagent_stop_posttooluse_registers_only_without_telemetry(self):
        payload = {
            "hook_event_name": "PostToolUse",
            "tool_name": "invoke_subagent",
            "cwd": self.cwd,
            "session_id": "leader-sid",
            "tool_input": {"TypeName": "tdq-explorer", "Prompt": "Investigate T2.2"},
            "response": {"conversationId": "conv-exp-99"},
        }
        rc = subagent_stop._handle_spawn_event(payload, self.cwd, "PostToolUse")
        self.assertEqual(rc, 0)
        sess_path = os.path.join(self.cwd, "docs", "tdq", ".tdq-runtime", "sessions.json")
        self.assertTrue(os.path.isfile(sess_path))
        tel_path = os.path.join(self.cwd, "docs", "tdq", ".tdq-agent-telemetry.jsonl")
        self.assertFalse(os.path.exists(tel_path), "PostToolUse spawn must not record premature stop telemetry")

    def test_session_start_and_prompt_context_investigate_gon_and_static_anchor(self):
        import re as _re
        plan_path = os.path.join(self.cwd, "docs", "tdq", "plan", "2026-11-21-inv.md")
        os.makedirs(os.path.dirname(plan_path), exist_ok=True)
        with io.open(plan_path, "w", encoding="utf-8") as fh:
            fh.write("- [~] **T1.1** Investigate\n")

        # 1. session_start with source=resume and work_kind=investigate swaps TDQ:GON + static anchor < 600c
        ss_payload = {
            "hook_event_name": "SessionStart",
            "cwd": self.cwd,
            "session_id": "ss-inv-resume",
            "source": "resume",
        }
        rc, out, _ = run_hook("session_start.py", ss_payload)
        self.assertEqual(rc, 0)
        ctx = json.loads(out).get("hookSpecificOutput", {}).get("additionalContext", "") if out.lstrip().startswith("{") else out
        self.assertIn("[TDQ:GON]", ctx)
        self.assertNotIn("rung 1", ctx.lower())
        self.assertIn("artifact", ctx.lower())
        self.assertIn("[TDQ:ANCHOR]", ctx)
        anchor_section = ctx[ctx.index("[TDQ:ANCHOR]"):]
        self.assertLess(len(anchor_section), 600)
        self.assertIsNone(_re.search(r"\d{2}:\d{2}:\d{2}", anchor_section))

        # 2. prompt_context subagent anchor on resume/compact
        _common.register_subagent_role(self.cwd, "sub-exp-1", "tdq-explorer", target_task="T1.1")
        sub_payload = {
            "hook_event_name": "UserPromptSubmit",
            "cwd": self.cwd,
            "session_id": "sub-exp-1",
            "source": "resume",
            "prompt": "continue",
        }
        rc2, out2, _ = run_hook("prompt_context.py", sub_payload)
        self.assertEqual(rc2, 0)
        ctx2 = json.loads(out2).get("hookSpecificOutput", {}).get("additionalContext", "") if out2.lstrip().startswith("{") else out2
        self.assertIn("[TDQ:ANCHOR]", ctx2)
        self.assertIn("2026-11-21-inv", ctx2)
        self.assertLess(len(ctx2), 600)

    def test_hooks_json_contains_search_web_matcher(self):
        with io.open(os.path.join(ROOT, "hooks", "hooks.json"), encoding="utf-8") as fh:
            cfg = json.load(fh)
        pre = [item.get("matcher", "") for item in cfg["hooks"]["PreToolUse"]]
        post = [item.get("matcher", "") for item in cfg["hooks"]["PostToolUse"]]
        self.assertTrue(any("search_web" in m for m in pre))
        self.assertTrue(any("search_web" in m for m in post))


if __name__ == "__main__":
    unittest.main()
