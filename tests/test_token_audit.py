"""Test cho scripts/token_audit.py — đo carry-cost của tool output trong transcript."""

import json
import os
import subprocess
import sys
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scripts"))

import token_audit  # noqa: E402
from helper import LY_DO_TOKEN, co_bo_dem_token  # noqa: E402


def _assistant(tool_id, name, inp, usage=True):
    msg = {"role": "assistant", "content": [
        {"type": "tool_use", "id": tool_id, "name": name, "input": inp}]}
    if usage:
        msg["usage"] = {"input_tokens": 1, "output_tokens": 1,
                        "cache_read_input_tokens": 100}
    return {"type": "assistant", "message": msg}


def _result(tool_id, text):
    return {"type": "user", "message": {"role": "user", "content": [
        {"type": "tool_result", "tool_use_id": tool_id, "content": text}]}}


def _write(path, records):
    with open(path, "w", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r) + "\n")


# 2026-09-21: hỏi chính skill_tokens (đoán `.venv-tokens/bin/python` thì Windows luôn skip).
CO_THU_VIEN = co_bo_dem_token()


class IterEventsTest(unittest.TestCase):
    def test_bo_qua_dong_hong_khong_crash(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "s.jsonl")
            with open(p, "w", encoding="utf-8") as fh:
                fh.write(json.dumps({"ok": 1}) + "\n")
                fh.write("{ dòng hỏng không phải json\n")
                fh.write("\n")
                fh.write(json.dumps({"ok": 2}) + "\n")
            events = list(token_audit.iter_events(p))
        self.assertEqual([e.get("ok") for e in events], [1, 2])

    def test_file_khong_ton_tai_tra_rong(self):
        self.assertEqual(list(token_audit.iter_events("/khong/co/that.jsonl")), [])


class TranscriptPathTest(unittest.TestCase):
    def test_windows_drive_and_both_separators(self):
        for project in (r"C:\Users\Example\TDQ_Workflow", "C:/Users/Example/TDQ_Workflow"):
            with self.subTest(project=project):
                actual = token_audit.default_transcript_dir(project)
                self.assertEqual(os.path.basename(actual), "C--Users-Example-TDQ-Workflow")
                self.assertEqual(os.path.basename(os.path.dirname(actual)), "projects")

    def test_posix_unicode_and_spaces(self):
        actual = token_audit.default_transcript_dir("/Users/Example/Dự án_test")
        self.assertEqual(os.path.basename(actual), "-Users-Example-D---n-test")


class CarryCostTest(unittest.TestCase):
    @unittest.skipUnless(CO_THU_VIEN, "chưa cài anthropic-tokenizer trong .venv-tokens")
    def test_cong_thuc_token_that_nhan_so_call_con_lai(self):
        # 3 API call; tool_result của call 1 nằm trước call 2 và 3.
        text = "x" * 400
        records = [
            _assistant("t1", "Read", {"file_path": "/a.md"}),   # api call 1
            _result("t1", text),
            _assistant("t2", "Read", {"file_path": "/b.md"}),   # api call 2
            _result("t2", text),
            _assistant("t3", "Read", {"file_path": "/c.md"}),   # api call 3
        ]
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "s.jsonl")
            _write(p, records)
            rows = token_audit.carry_cost([p])
        by = {r.group: r for r in rows}
        # result 1 còn 2 call phía sau (call 2, 3) → n*2
        # result 2 còn 1 call phía sau (call 3)    → n*1
        n = token_audit.dem_token(text)
        self.assertEqual(by["Read file"].tokens, n * 3)
        self.assertEqual(by["Read file"].count, 2)

    @unittest.skipUnless(CO_THU_VIEN, "chưa cài anthropic-tokenizer trong .venv-tokens")
    def test_gom_nhom_theo_loai_lenh_bash(self):
        records = [
            _assistant("t1", "Bash", {"command": "python3 scripts/tdq_state.py next"}),
            _result("t1", "y" * 40),
            _assistant("t2", "Bash", {"command": "cd tests && python3 -m unittest discover"}),
            _result("t2", "y" * 40),
            _assistant("t3", "Bash", {"command": "ls"}),
            _result("t3", "y" * 40),
            _assistant("t4", "Edit", {"file_path": "/a.md"}),
        ]
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "s.jsonl")
            _write(p, records)
            groups = {r.group for r in token_audit.carry_cost([p])}
        self.assertIn("tdq_state.py (dump JSON)", groups)
        self.assertIn("test suite run", groups)
        self.assertIn("other Bash", groups)

    def test_khong_co_session_tra_bang_rong(self):
        self.assertEqual(token_audit.carry_cost([]), [])


class UsageTotalsTest(unittest.TestCase):
    @unittest.skipUnless(co_bo_dem_token(), LY_DO_TOKEN)
    def test_cong_don_usage_va_dem_api_call(self):
        records = [
            _assistant("t1", "Read", {"file_path": "/a.md"}),
            _result("t1", "z" * 8),
            _assistant("t2", "Read", {"file_path": "/b.md"}),
        ]
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "s.jsonl")
            _write(p, records)
            tot = token_audit.usage_totals([p])
        self.assertEqual(tot["api_calls"], 2)
        self.assertEqual(tot["cache_read"], 200)
        self.assertEqual(tot["output"], 2)


def _assistant_line(mid, blocks, usage=None):
    """Một DÒNG jsonl của message `mid` — Claude Code tách 1 message ra nhiều dòng."""
    msg = {"role": "assistant", "id": mid, "content": blocks}
    msg["usage"] = usage or {"input_tokens": 10, "output_tokens": 5,
                             "cache_read_input_tokens": 100,
                             "cache_creation_input_tokens": 20}
    return {"type": "assistant", "message": msg}


class MessageIdTest(unittest.TestCase):
    """Một message nằm nhiều dòng jsonl → chỉ được tính LÀ MỘT API call."""

    def _records(self):
        return [
            _assistant_line("msg_1", [{"type": "thinking", "thinking": "..."}]),
            _assistant_line("msg_1", [{"type": "text", "text": "làm thôi"}]),
            _assistant_line("msg_1", [{"type": "tool_use", "id": "t1",
                                       "name": "Read", "input": {"file_path": "/a.md"}}]),
            _assistant_line("msg_1", [{"type": "tool_use", "id": "t1",
                                       "name": "Read", "input": {"file_path": "/a.md"}}]),
        ]

    def test_ba_dong_cung_message_id_dem_mot_api_call(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "s.jsonl")
            _write(p, self._records())
            tot = token_audit.usage_totals([p])
        self.assertEqual(tot["api_calls"], 1)

    def test_usage_cong_mot_lan_cho_moi_message(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "s.jsonl")
            _write(p, self._records())
            tot = token_audit.usage_totals([p])
        self.assertEqual(tot["cache_read"], 100)
        self.assertEqual(tot["cache_write"], 20)
        self.assertEqual(tot["input"], 10)
        self.assertEqual(tot["output"], 5)

    def test_dedup_tool_use_theo_id(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "s.jsonl")
            _write(p, self._records())
            tot = token_audit.usage_totals([p])
        self.assertEqual(tot["tool_calls"], 1)

    def test_message_khong_co_id_van_dem_tung_dong(self):
        # transcript cũ/không có `message.id` → giữ nguyên cách đếm cũ, không mất số
        records = [
            _assistant("t1", "Read", {"file_path": "/a.md"}),
            _assistant("t2", "Read", {"file_path": "/b.md"}),
        ]
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "s.jsonl")
            _write(p, records)
            tot = token_audit.usage_totals([p])
        self.assertEqual(tot["api_calls"], 2)
        self.assertEqual(tot["tool_calls"], 2)


class CostEquivalentTest(unittest.TestCase):
    """Quy hóa đơn về input-token tương đương theo hệ số của trang giá chính thức."""

    TOTALS = {"cache_read": 1000, "cache_write": 100, "input": 10, "output": 20}

    def test_ttl_1h_dung_he_so_2(self):
        # 1000*0,1 + 100*2 + 10*1 + 20*5 = 410
        equiv, parts = token_audit.cost_equivalent(self.TOTALS, "1h")
        self.assertEqual(equiv, 410)
        self.assertEqual(parts["cache_write"], 200)

    def test_ttl_5m_dung_he_so_1_25(self):
        # 1000*0,1 + 100*1,25 + 10*1 + 20*5 = 335
        equiv, _ = token_audit.cost_equivalent(self.TOTALS, "5m")
        self.assertEqual(equiv, 335)

    def test_mac_dinh_la_ttl_1h(self):
        self.assertEqual(token_audit.cost_equivalent(self.TOTALS)[0], 410)

    def test_totals_rong_tra_0(self):
        self.assertEqual(token_audit.cost_equivalent({})[0], 0)


class CliTest(unittest.TestCase):
    def _run(self, args, env=None):
        e = dict(os.environ)
        if env:
            e.update(env)
        return subprocess.run(
            [sys.executable, os.path.join(REPO, "scripts", "token_audit.py")] + args,
            capture_output=True, encoding="utf-8", text=True, env=e)

    def test_khong_co_session_van_exit_0(self):
        with tempfile.TemporaryDirectory() as d:
            r = self._run(["--transcript-dir", d])
        self.assertEqual(r.returncode, 0, r.stderr)

    @unittest.skipUnless(CO_THU_VIEN, "chưa cài anthropic-tokenizer trong .venv-tokens")
    def test_in_bang_carry_cost(self):
        with tempfile.TemporaryDirectory() as d:
            _write(os.path.join(d, "s.jsonl"), [
                _assistant("t1", "Read", {"file_path": "/a.md"}),
                _result("t1", "q" * 400),
                _assistant("t2", "Read", {"file_path": "/b.md"}),
            ])
            r = self._run(["--transcript-dir", d])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("carry-cost", r.stdout)
        self.assertIn("Read file", r.stdout)

    def test_log_bat_mac_dinh_ra_stderr(self):
        with tempfile.TemporaryDirectory() as d:
            r = self._run(["--transcript-dir", d])
        self.assertTrue(r.stderr.strip(), "log phải bật mặc định")

    def test_tat_log_bang_bien_moi_truong(self):
        with tempfile.TemporaryDirectory() as d:
            r = self._run(["--transcript-dir", d], env={"TDQ_AUDIT_LOG": "0"})
        self.assertEqual(r.stderr.strip(), "")


class DemBangTokenizerThatTest(unittest.TestCase):
    """Luật xương sống của hướng B: đếm bằng tokenizer thật, cấm ước lượng ký tự/4.

    Bản trước dùng `CHARS_PER_TOKEN = 4`. Ước lượng đó lệch mạnh đúng ở nhóm tốn
    nhất — chuỗi lặp và base64 nén rất tốt, văn bản tiếng Việt có dấu thì ngược lại.
    """

    def test_co_ham_dem_token_dung_chung_mot_bo_dem_voi_skill_tokens(self):
        self.assertTrue(hasattr(token_audit, "dem_token"))

    @unittest.skipUnless(CO_THU_VIEN, "chưa cài anthropic-tokenizer trong .venv-tokens")
    def test_carry_cost_lay_so_tu_tokenizer_chu_khong_phai_do_dai_chia_4(self):
        text = "x" * 400
        records = [
            _assistant("t1", "Read", {"file_path": "/a.md"}),
            _result("t1", text),
            _assistant("t2", "Read", {"file_path": "/b.md"}),
            _result("t2", text),
            _assistant("t3", "Read", {"file_path": "/c.md"}),
        ]
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "s.jsonl")
            _write(p, records)
            rows = token_audit.carry_cost([p])
        that = token_audit.dem_token(text)
        self.assertNotEqual(that, len(text) // 4,
                            "chọn chuỗi khác: ca này phải phân biệt được hai cách đếm")
        by = {r.group: r for r in rows}
        self.assertEqual(by["Read file"].tokens, that * 2 + that * 1)

    def test_thieu_thu_vien_thi_thoat_khac_0_kem_huong_dan_cai(self):
        """Chặn đường nhảy sang venv để dựng lại đúng cảnh máy chưa cài gì."""
        e = dict(os.environ)
        e.update({"TDQ_TOKENS_DA_NHAY": "1", "TDQ_TOKENS_VENV": "khong-co"})
        with tempfile.TemporaryDirectory() as d:
            _write(os.path.join(d, "s.jsonl"), [
                _assistant("t1", "Read", {"file_path": "/a.md"}),
                _result("t1", "q" * 400),
                _assistant("t2", "Read", {"file_path": "/b.md"}),
            ])
            r = subprocess.run(
                [sys.executable, os.path.join(REPO, "scripts", "token_audit.py"),
                 "--transcript-dir", d],
                capture_output=True, encoding="utf-8", text=True, env=e)
        if r.returncode == 0:
            self.skipTest("python chạy test đã có sẵn anthropic-tokenizer")
        self.assertEqual(r.returncode, token_audit.EXIT_THIEU_THU_VIEN)
        self.assertNotIn("carry-cost", r.stdout)
        self.assertIn("anthropic-tokenizer", r.stderr)


class PhanRaHanhViTest(unittest.TestCase):
    """Bảng phân rã hành vi — trả lời "cắt cái gì", điều mà tổng carry-cost không nói.

    Một nhóm tốn nhiều có thể vì gọi rất nhiều lần mỗi lần nhỏ (sửa hành vi), hoặc vì
    vài lần khổng lồ (sửa trần output). Trung vị/p90/p99/max phân biệt đúng hai ca đó.
    """

    def _session(self, d, records):
        p = os.path.join(d, "s.jsonl")
        _write(p, records)
        return p

    @unittest.skipUnless(CO_THU_VIEN, "chưa cài anthropic-tokenizer trong .venv-tokens")
    def test_moi_nhom_co_du_n_trung_vi_p90_p99_max(self):
        with tempfile.TemporaryDirectory() as d:
            recs = []
            for i in range(5):
                recs.append(_assistant(f"t{i}", "Read", {"file_path": f"/f{i}.md"}))
                recs.append(_result(f"t{i}", f"dòng {i} " * (i + 1) * 10))
            rows = token_audit.phan_ra([self._session(d, recs)])
        by = {r.group: r for r in rows}
        self.assertIn("Read file", by)
        for truong in ("count", "trung_vi", "p90", "p99", "lon_nhat"):
            with self.subTest(truong=truong):
                self.assertTrue(hasattr(by["Read file"], truong))
        self.assertEqual(by["Read file"].count, 5)

    @unittest.skipUnless(CO_THU_VIEN, "chưa cài anthropic-tokenizer trong .venv-tokens")
    def test_so_thong_ke_lay_tu_chinh_bo_dem_that(self):
        """Chốt vị trí phân vị theo hạng gần nhất, và chốt rằng số vào bảng là token
        THẬT của từng output — không phải carry-cost, không phải ký tự."""
        doan = [f"đoạn {i} " * (i + 1) * 8 for i in range(5)]
        with tempfile.TemporaryDirectory() as d:
            recs = []
            for i, t in enumerate(doan):
                recs.append(_assistant(f"t{i}", "Read", {"file_path": f"/f{i}.md"}))
                recs.append(_result(f"t{i}", t))
            rows = token_audit.phan_ra([self._session(d, recs)])
        mong = sorted(token_audit.dem_token(t) for t in doan)
        r = {x.group: x for x in rows}["Read file"]
        self.assertEqual(r.trung_vi, mong[2])
        self.assertEqual(r.lon_nhat, mong[-1])
        self.assertEqual(r.p90, mong[4])          # hạng gần nhất: ceil(0,9×5) = 5
        self.assertEqual(r.p99, mong[4])

    def test_ti_le_read_co_pham_vi_offset_limit(self):
        with tempfile.TemporaryDirectory() as d:
            recs = [
                _assistant("a", "Read", {"file_path": "/a.md"}),
                _result("a", "x"),
                _assistant("b", "Read", {"file_path": "/b.md", "offset": 10, "limit": 20}),
                _result("b", "x"),
                _assistant("c", "Read", {"file_path": "/c.md", "limit": 5}),
                _result("c", "x"),
                _assistant("d", "Bash", {"command": "ls"}),
                _result("d", "x"),
            ]
            hv = token_audit.hanh_vi_read([self._session(d, recs)])
        self.assertEqual(hv.tong, 3)
        self.assertEqual(hv.co_pham_vi, 2)

    def test_ti_le_read_doc_lai_cung_file_trong_mot_session(self):
        """Đọc lại là hành vi ĐÚNG theo luật TDQ ở nhiều ca — bảng chỉ ĐO, không phán."""
        with tempfile.TemporaryDirectory() as d:
            recs = [
                _assistant("a", "Read", {"file_path": "/a.md"}),
                _result("a", "x"),
                _assistant("b", "Read", {"file_path": "/a.md"}),
                _result("b", "x"),
                _assistant("c", "Read", {"file_path": "/a.md"}),
                _result("c", "x"),
                _assistant("e", "Read", {"file_path": "/b.md"}),
                _result("e", "x"),
            ]
            hv = token_audit.hanh_vi_read([self._session(d, recs)])
        self.assertEqual(hv.tong, 4)
        self.assertEqual(hv.doc_lai, 2)           # 4 lần đọc trên 2 file khác nhau

    def test_doc_lai_khong_cong_don_giua_hai_session(self):
        with tempfile.TemporaryDirectory() as d:
            paths = []
            for ten in ("s1", "s2"):
                p = os.path.join(d, f"{ten}.jsonl")
                _write(p, [_assistant("a", "Read", {"file_path": "/a.md"}),
                           _result("a", "x")])
                paths.append(p)
            hv = token_audit.hanh_vi_read(paths)
        self.assertEqual(hv.tong, 2)
        self.assertEqual(hv.doc_lai, 0)

    @unittest.skipUnless(CO_THU_VIEN, "chưa cài anthropic-tokenizer trong .venv-tokens")
    def test_cli_in_bang_phan_ra_va_ti_le_read(self):
        with tempfile.TemporaryDirectory() as d:
            self._session(d, [
                _assistant("a", "Read", {"file_path": "/a.md"}),
                _result("a", "q" * 400),
                _assistant("b", "Read", {"file_path": "/a.md", "limit": 5}),
                _result("b", "q" * 40),
                _assistant("c", "Bash", {"command": "ls"}),
            ])
            r = subprocess.run(
                [sys.executable, os.path.join(REPO, "scripts", "token_audit.py"),
                 "--transcript-dir", d],
                capture_output=True,
                encoding="utf-8", text=True, env=dict(os.environ, TDQ_AUDIT_LOG="0"))
        self.assertEqual(r.returncode, 0, r.stderr)
        for cot in ("median", "p90", "p99", "largest"):
            with self.subTest(cot=cot):
                self.assertIn(cot, r.stdout)
        self.assertIn("re-read", r.stdout)


def _anh_png(w, h):
    """PNG hợp lệ tối thiểu: chỉ cần chữ ký + IHDR là đọc được kích thước."""
    import base64
    import struct
    import zlib
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)
    khoi = (b"\x89PNG\r\n\x1a\n" + struct.pack(">I", len(ihdr)) + b"IHDR" + ihdr
            + struct.pack(">I", zlib.crc32(b"IHDR" + ihdr)))
    return base64.b64encode(khoi + b"\x00" * 4000).decode()


def _result_anh(tool_id, w, h):
    return {"type": "user", "message": {"role": "user", "content": [
        {"type": "tool_result", "tool_use_id": tool_id, "content": [
            {"type": "image", "source": {"type": "base64", "media_type": "image/png",
                                         "data": _anh_png(w, h)}}]}]}}


class DemAnhTest(unittest.TestCase):
    """Ảnh KHÔNG tốn theo độ dài base64 — nó tốn theo số patch 28×28.

    Vì sao khoá: bảng đo bản đầu cho `get_canvas_screenshot` trung vị 378.014
    token/lần vì đếm chuỗi base64. Ảnh thật 960×1605 chỉ tốn 2.030 token. Sai gấp
    ~186 lần, và cái sai đó chỉ ra đúng một kết luận: "cắt năng lực chụp canvas đi" —
    cắt nhầm. Thước đo sai một chiều thì mọi quyết định dựng trên nó sai theo.

    Nguồn công thức: tài liệu Vision của Claude — mỗi patch 28×28 px là một token
    thị giác, ảnh tốn `⌈w/28⌉ × ⌈h/28⌉` token.
    """

    def test_dem_theo_patch_28_chu_khong_theo_do_dai_base64(self):
        self.assertEqual(token_audit.dem_anh("image/png", _anh_png(960, 1605)),
                         (960 + 27) // 28 * ((1605 + 27) // 28))

    def test_anh_nho_ton_it_token(self):
        self.assertEqual(token_audit.dem_anh("image/png", _anh_png(56, 28)), 2)

    def test_khong_doc_duoc_kich_thuoc_thi_dung_tran_co_nguon(self):
        self.assertEqual(token_audit.dem_anh("image/gif", "khong-phai-anh"),
                         token_audit.TOKEN_ANH_KHONG_RO)

    @unittest.skipUnless(CO_THU_VIEN, "chưa cài anthropic-tokenizer trong .venv-tokens")
    def test_carry_cost_cua_khoi_anh_khong_phinh_theo_base64(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "s.jsonl")
            _write(p, [
                _assistant("t1", "mcp__excalidraw__get_canvas_screenshot", {}),
                _result_anh("t1", 960, 1605),
                _assistant("t2", "Read", {"file_path": "/b.md"}),
            ])
            rows = token_audit.phan_ra([p])
        r = {x.group: x for x in rows}["mcp__excalidraw__get_canvas_screenshot"]
        self.assertLess(r.lon_nhat, 3000,
                        "khối ảnh vẫn đang được đếm bằng độ dài base64")
        self.assertGreaterEqual(r.lon_nhat, 2030)


class MultiHostAuditTest(unittest.TestCase):
    """Multi-host audit for Antigravity, Codex, and Claude Code with measured/inferred labels."""

    def _write_jsonl(self, path, lines):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            for item in lines:
                if isinstance(item, str):
                    fh.write(item + "\n")
                else:
                    fh.write(json.dumps(item, ensure_ascii=False) + "\n")
        return path

    def _stage_agy_session(self, home, conv_id="conv-1", with_usage=True, broken=False):
        path = os.path.join(
            home, ".gemini", "antigravity", "brain", conv_id, ".system_generated", "logs", "transcript.jsonl"
        )
        r1 = {
            "type": "PLANNER_RESPONSE",
            "step_index": 1,
            "created_at": "2026-11-18T05:00:00Z",
            "tool_calls": [
                {"name": "read_file", "args": {"Path": json.dumps("/work/a.py")}},
                {"name": "invoke_subagent", "args": {"AgentName": "tdq-implementer"}},
            ],
        }
        r2 = {
            "type": "PLANNER_RESPONSE",
            "step_index": 4,
            "created_at": "2026-11-18T05:00:05Z",
            "tool_calls": [
                {"name": "read_file", "args": {"Path": json.dumps("/work/a.py"), "StartLine": "1", "EndLine": "20"}},
            ],
        }
        r3 = {"type": "PLANNER_RESPONSE", "step_index": 6, "created_at": "2026-11-18T05:00:10Z", "tool_calls": []}
        if with_usage:
            r1.update({"input_tokens": 1000, "cache_read_tokens": 200, "output_tokens": 50})
            r2.update({"input_tokens": 1400, "cache_read_tokens": 300, "output_tokens": 60})
            r3.update({"input_tokens": 1800, "cache_read_tokens": 400, "output_tokens": 70})
        records = [
            r1,
            {"type": "GENERIC", "step_index": 2, "source": "MODEL", "content": "a" * 400},
            {"type": "TOOL_RESPONSE", "step_index": 3, "content": "subagent result " * 30},
            r2,
            {"type": "GENERIC", "step_index": 5, "source": "MODEL", "content": "b" * 160},
            r3,
        ]
        if broken:
            records.insert(2, "{truncated json line")
        return self._write_jsonl(path, records)

    def _stage_codex_session(self, home, name="rollout-1.jsonl"):
        path = os.path.join(home, ".codex", "sessions", "2026", "11", "18", name)
        records = [
            {"type": "session_meta", "timestamp": "2026-11-18T05:00:00Z", "payload": {"id": "cx-1", "cwd": "/work"}},
            {"type": "response_item", "timestamp": "2026-11-18T05:00:01Z",
             "payload": {"type": "custom_tool_call", "call_id": "c1", "name": "exec", "input": "cat /work/x.py"}},
            {"type": "response_item", "timestamp": "2026-11-18T05:00:02Z",
             "payload": {"type": "custom_tool_call_output", "call_id": "c1",
                         "output": [{"type": "input_text", "text": "z" * 320}]}},
            {"type": "event_msg", "timestamp": "2026-11-18T05:00:03Z",
             "payload": {"type": "token_count", "info": {
                 "total_token_usage": {"input_tokens": 800, "cached_input_tokens": 300, "output_tokens": 40},
                 "last_token_usage": {"input_tokens": 800, "cached_input_tokens": 300, "output_tokens": 40},
             }}},
            {"type": "response_item", "timestamp": "2026-11-18T05:00:04Z",
             "payload": {"type": "function_call", "call_id": "c2", "name": "spawn_agent",
                         "arguments": json.dumps({"prompt": "check"})}},
            {"type": "response_item", "timestamp": "2026-11-18T05:00:05Z",
             "payload": {"type": "function_call_output", "call_id": "c2", "output": "done " * 40}},
            {"type": "event_msg", "timestamp": "2026-11-18T05:00:06Z",
             "payload": {"type": "token_count", "info": {
                 "total_token_usage": {"input_tokens": 1600, "cached_input_tokens": 700, "output_tokens": 90},
                 "last_token_usage": {"input_tokens": 800, "cached_input_tokens": 400, "output_tokens": 50},
             }}},
        ]
        return self._write_jsonl(path, records)

    def test_audit_multi_host_agy_and_codex_fixtures(self):
        with tempfile.TemporaryDirectory() as home:
            self._stage_agy_session(home, broken=True)
            self._stage_codex_session(home)
            report = token_audit.audit_multi_host(host="all", project_dir="/work", limit=5, top=10, home=home)
        self.assertGreaterEqual(report["sessions_scanned"], 2)
        self.assertTrue(report["hosts"])
        self.assertTrue(all(row["basis"] in ("measured", "inferred") for row in report["hosts"]))
        host_names = {row["host"] for row in report["hosts"]}
        self.assertEqual(host_names, {"agy", "codex"})
        self.assertTrue(report["top_items"])
        self.assertTrue(report["repeated_reads"])
        self.assertEqual(report["repeated_reads"][0]["file_path"], "/work/a.py")
        self.assertEqual(report["repeated_reads"][0]["re_reads"], 1)
        self.assertTrue(report["subagent_calls"])

    def test_missing_tokenizer_falls_back_to_inferred_for_non_claude_hosts(self):
        with tempfile.TemporaryDirectory() as home:
            self._stage_agy_session(home, with_usage=False)
            self._stage_codex_session(home)
            env = dict(os.environ, TDQ_TOKENS_DA_NHAY="1", TDQ_TOKENS_VENV="khong-co",
                       USERPROFILE=home, HOME=home, TDQ_LOG="0")
            r = subprocess.run(
                [sys.executable, os.path.join(REPO, "scripts", "token_audit.py"),
                 "--host", "all", "--sessions", "5", "--top", "5"],
                check=False, capture_output=True, encoding="utf-8", text=True, env=env,
            )
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("inferred", r.stdout)
        self.assertIn("agy", r.stdout)
        self.assertIn("codex", r.stdout)
        self.assertEqual(r.stderr.strip(), "")

    def test_empty_session_and_empty_home_handled_cleanly(self):
        with tempfile.TemporaryDirectory() as home:
            self._write_jsonl(
                os.path.join(home, ".gemini", "antigravity", "brain", "empty", ".system_generated", "logs",
                             "transcript.jsonl"),
                [],
            )
            report = token_audit.audit_multi_host(host="agy", limit=5, home=home)
            self.assertEqual(report["sessions_scanned"], 1)
            self.assertEqual(report["hosts"][0]["basis"], "inferred")

        with tempfile.TemporaryDirectory() as empty_home:
            report_none = token_audit.audit_multi_host(host="all", limit=5, home=empty_home)
            self.assertEqual(report_none["sessions_scanned"], 0)
            self.assertEqual(report_none["hosts"], [])


if __name__ == "__main__":
    unittest.main()
