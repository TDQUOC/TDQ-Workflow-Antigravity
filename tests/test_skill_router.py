"""Test cho scripts/skill_router.py — nguyên mẫu kho tra cứu skill.

Test quan trọng nhất ở đây là `TiLeTrungTest`: nó trả lời câu hỏi duy nhất khiến
cả hướng E đáng hay không đáng làm — **tra có TRÚNG không**. Router tra trượt còn
hại hơn tốn token, vì nó làm mất một skill lẽ ra phải dùng mà không ai biết.

Bộ prompt mẫu dưới đây cố ý KHÔNG toàn ca dễ. Ba nhóm:
  * `dễ`   — prompt nhắc thẳng tên công cụ ("unity shader", "mongodb").
  * `vừa`  — prompt nói việc, không nói tên công cụ.
  * `khó`  — prompt nói ý định bằng lời thường, không trùng từ khoá nào với mô tả.
Nhóm `khó` là nhóm phản ánh đúng cách người ta gõ prompt thật. Bỏ nó ra thì tỉ lệ
trúng đẹp lên nhưng con số hết nghĩa.
"""
import ast
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import helper  # noqa: F401  — chèn scripts/ vào sys.path
import skill_router

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "scripts", "skill_router.py")

# (prompt, tuple skill CHẤP NHẬN ĐƯỢC, độ khó).
#
# Vì sao là TUPLE chứ không phải một tên: router phục vụ việc "lọc 284 skill xuống
# vài cái để đọc kỹ", nên tra trúng nghĩa là **một skill làm được việc đó** lọt vào
# top-k — không phải đúng cái tên tôi thích nhất. Vài prompt có hơn một skill làm
# được thật, chối điều đó thì con số bi quan sai lệch.
#
# Luật đặt đáp án, để tuple không thành cái cớ nới lỏng cho đẹp số:
#   1. Mọi tên trong tuple phải đọc mô tả của CHÍNH skill đó rồi mới đưa vào — mô tả
#      phải nói nó làm đúng việc prompt hỏi. Không đưa vào vì router trả ra nó.
#   2. Cấm nới tuple sau khi thấy kết quả trượt. Ba tuple hai tên dưới đây đều nới
#      vì mô tả nói thẳng, có trích trong comment ngay cạnh.
MAU = [
    ("sửa lỗi unity shader bị đen trên mobile", ("unity-shadergraph-design",), "dễ"),
    ("truy vấn mongodb aggregate cho báo cáo",
     ("mongodb-natural-language-querying",), "dễ"),
    ("crawl toàn bộ trang tài liệu về markdown", ("firecrawl-crawl",), "dễ"),
    ("lấy design token từ file figma", ("figma-generate-library",), "dễ"),
    ("viết spec cho request mới", ("tdq-spec",), "dễ"),
    ("viết plan có checkbox từng task", ("tdq-plan",), "dễ"),
    ("mở request mới và phân tích yêu cầu", ("tdq-intake",), "dễ"),
    ("chạy quét sonarqube cho nhánh này", ("sonar-analyze",), "dễ"),
    # skill-development mô tả: 'create a skill', 'add a skill to plugin' — đúng việc.
    ("tạo skill mới cho plugin của tôi", ("skill-creator", "skill-development"), "dễ"),
    # hook-development mô tả: 'create a hook', 'add a PreToolUse/PostToolUse/Stop hook'.
    ("dựng hook chặn hành vi lặp lại",
     ("writing-hookify-rules", "hook-development"), "dễ"),
    # Playwright chỉ có MCP tool, không có skill nào trong kho → đáp án đơn.
    ("tôi muốn tự động hoá thao tác trên trình duyệt", ("chrome-devtools",), "vừa"),
    ("kiểm tra chất lượng code trước khi merge", ("sonar-quality-gate",), "vừa"),
    ("ghi nhớ một quyết định kiến trúc cho lần sau", ("mem0-memory",), "vừa"),
    ("nghiên cứu sâu một chủ đề trên web rồi tổng hợp", ("tavily-research",), "vừa"),
    ("đóng gói bộ skill thành plugin cài được", ("plugin-structure",), "vừa"),
    ("làm ảnh bìa cho bài đăng mạng xã hội",
     ("canva-resize-for-social-media",), "vừa"),
    ("dữ liệu đang chậm, cần xếp lại bảng cho nhanh",
     ("mongodb-query-optimizer",), "khó"),
    ("nhân vật trong game đi xuyên tường", ("unity-patterns",), "khó"),
    ("tôi cần biết cái nút này bấm vào thì gọi hàm nào", ("graphify",), "khó"),
    ("mọi thứ trông lệch nhau, không thẳng hàng", ("frontend-design",), "khó"),
    ("giao việc cho nhiều trợ lý chạy song song",
     ("dispatching-parallel-agents",), "khó"),
    ("kiểm lại xem việc đã xong đúng chưa",
     ("verification-before-completion",), "khó"),
]


def chay(*args, env=None):
    proc = subprocess.run([sys.executable, SCRIPT, *args], check=False,
                          capture_output=True, encoding="utf-8", text=True, timeout=300,
                          env=dict(os.environ, TDQ_LOG="0", **(env or {})))
    return proc.returncode, proc.stdout, proc.stderr


class KhoTest(unittest.TestCase):
    """Kho phải khớp inventory, nếu không thì router đang tra trên tập skill sai."""

    def test_kho_da_dung_va_du_bon_truong(self):
        ban_ghi = skill_router.doc_kho()
        self.assertGreater(len(ban_ghi), 100)
        for b in ban_ghi[:50]:
            with self.subTest(ten=b.get("ten")):
                for t in skill_router.TRUONG:
                    self.assertIn(t, b)

    def test_so_ban_ghi_khop_skill_inventory(self):
        """The invariant is "building loses nobody", and that is a BUILD-time property.

        Comparing the committed fixture against the machine running the test compares the
        author's 284 skills with whatever this machine happens to have — 11 here, and the case
        failed for that reason alone. Build a store now and compare THAT against the same
        inventory it was built from: true on every machine, and it still catches a record
        silently dropped in `dung_kho`.
        """
        import skill_inventory
        vua_dung = skill_router.dung_kho(ROOT)
        self.assertEqual(len(vua_dung), len(skill_inventory.inventory(ROOT)))

    def test_moi_ban_ghi_deu_co_duong_dan(self):
        """Spec §6 Q15 đòi "mọi duong_dan mở được" — bản ghi rỗng KHÔNG đạt.

        Bản đầu tra bảng bằng tên thư mục nên 10/284 skill không dò ra SKILL.md, vì
        tên khai khác tên thư mục (`canva-brand-check` ở thư mục `brand-check/`,
        `unity-mcp-orchestrator` ở `unity-mcp-skill/`) và một skill khai tên kèm dấu
        nháy kép. Cái giá không phải là thiếu một dòng log: mọi kiến trúc "giấu mô tả
        rồi đọc thẳng SKILL.md khi cần" đều mù với đúng 10 skill đó, im lặng.
        """
        rong = [b["ten"] for b in skill_router.doc_kho() if not b["duong_dan"]]
        self.assertEqual(rong, [], f"{len(rong)} bản ghi không có đường dẫn")

    def test_moi_duong_dan_khac_rong_deu_dung_khuon(self):
        """The SHAPE of every path, not its existence on the machine running the test.

        `docs/tdq/audit/skill-index.json` is committed on purpose: it is the measurement
        fixture the hit-rate cases below are scored against, and those numbers only mean
        something against the exact 284-skill set they were measured on (see `len > 100` and
        the 80 % floor). It therefore holds the ABSOLUTE paths of the machine that built it.

        Asserting those paths still exist made the suite fail 285 times on every other machine
        — one subTest per record — for a reason that says nothing about the router. What can
        be checked anywhere is that a record points at a real skill file: non-empty, and ending
        in SKILL.md. A path that exists here is checked by `--dung-kho` at build time, where
        the answer is meaningful.
        """
        for b in skill_router.doc_kho():
            if b["duong_dan"]:
                with self.subTest(ten=b["ten"]):
                    duong = b["duong_dan"].replace("\\", "/")
                    self.assertTrue(duong.endswith("SKILL.md"), duong)
                    self.assertNotIn("//", duong)

    def test_kho_thieu_thi_bao_loi_kem_lenh_dung_lai(self):
        rc, out, err = chay("--tra", "bất kỳ",
                            env={"TDQ_ROUTER_KHO": "/khong/he/co.json"})
        # Biến môi trường trên chưa được hỗ trợ; đường chắc chắn của ca này là gọi
        # thẳng `doc_kho` với đường dẫn không tồn tại trong tiến trình con.
        rc2 = subprocess.run(
            [sys.executable, "-c",
             "import sys; sys.path.insert(0, {!r}); import skill_router;"
             "skill_router.doc_kho('/khong/he/co.json')".format(
                 os.path.join(ROOT, "scripts"))],
            check=False, capture_output=True, encoding="utf-8", text=True, timeout=120,
            env=dict(os.environ, TDQ_LOG="0"))
        self.assertEqual(rc2.returncode, skill_router.EXIT_THIEU_KHO)
        self.assertIn("--dung-kho", rc2.stderr)
        del rc, out, err


class TachTuTest(unittest.TestCase):
    """Chuẩn hoá từ — cùng một hàm cho lúc dựng kho và lúc tra, nếu không thì lệch."""

    def test_bo_dau_tieng_viet(self):
        self.assertEqual(skill_router.tach_tu("Thời Gian"), ["thoi", "gian"])

    def test_chu_d_gach_ngang_ve_d_thuong(self):
        self.assertIn("dong", skill_router.tach_tu("đóng"))

    def test_bo_dau_cau_va_giu_so(self):
        self.assertEqual(skill_router.tach_tu("unity-3d, shader!"),
                         ["unity", "3d", "shader"])

    def test_camel_case_va_acronym_va_snake_case(self):
        self.assertEqual(skill_router.tach_tu("getHTTPResponse"),
                         ["get", "http", "response"])
        self.assertEqual(skill_router.tach_tu("camelCase"),
                         ["camel", "case"])
        self.assertEqual(skill_router.tach_tu("snake_case_query"),
                         ["snake", "case", "query"])

    def test_chu_d_hoa_gach_ngang_ve_d_thuong(self):
        self.assertIn("dong", skill_router.tach_tu("ĐóngGói"))
        self.assertIn("goi", skill_router.tach_tu("ĐóngGói"))


class TraTest(unittest.TestCase):
    """Hành vi tra: offline, có thứ tự điểm, không văng khi không khớp gì."""

    def test_tra_chay_duoc_khi_khong_co_bien_api_key(self):
        sach = {k: "" for k in os.environ
                if "API_KEY" in k.upper() or "TOKEN" in k.upper()}
        rc, out, _err = chay("--tra", "sửa lỗi unity shader", env=sach)
        self.assertEqual(rc, 0)
        self.assertIn("unity", out)

    def test_diem_giam_dan(self):
        kho = skill_router.KhoBM25(skill_router.doc_kho())
        diem = [d for d, _ in kho.tra("viết spec cho request mới", 5)]
        self.assertEqual(diem, sorted(diem, reverse=True))

    def test_cau_khong_khop_gi_thi_bao_khong_co_chu_khong_van(self):
        rc, out, _err = chay("--tra", "zzzqqqxxx")
        self.assertEqual(rc, 0)
        self.assertIn("No skill matches", out)

    def test_hai_co_cung_luc_bi_tu_choi(self):
        rc, _out, err = chay("--dung-kho", "--tra", "x")
        self.assertEqual(rc, 2)
        self.assertIn("--dung-kho", err)


class TiLeTrungTest(unittest.TestCase):
    """Con số quyết định hướng E có đáng làm hay không."""

    @classmethod
    def setUpClass(cls):
        cls.kho = skill_router.KhoBM25(skill_router.doc_kho())
        cls.co_that = {b["ten"] for b in cls.kho.ban_ghi}

    def _ket_qua(self, k):
        trung = []
        for prompt, dung, do_kho in MAU:
            ten = [b["ten"] for _d, b in self.kho.tra(prompt, k)]
            trung.append((prompt, dung, do_kho, any(d in ten for d in dung), ten))
        return trung

    def test_moi_skill_dung_trong_bo_mau_deu_co_that_trong_kho(self):
        """Đặt đáp án là skill không tồn tại thì tỉ lệ trúng tự động đẹp lên vì
        chẳng bao giờ so được — phải chặn ngay từ đây."""
        for _prompt, dung, _do_kho in MAU:
            for d in dung:
                with self.subTest(skill=d):
                    self.assertIn(d, self.co_that)

    def test_khong_prompt_nao_duoc_nhieu_hon_hai_dap_an(self):
        """Chặn đường nới tuple cho tới khi trúng: nới rộng là lách, không phải đo."""
        for prompt, dung, _do_kho in MAU:
            with self.subTest(prompt=prompt):
                self.assertLessEqual(len(dung), 2)

    def test_bo_mau_du_20_prompt_va_du_ba_do_kho(self):
        self.assertGreaterEqual(len(MAU), 20)
        for muc in ("dễ", "vừa", "khó"):
            self.assertGreaterEqual(sum(1 for m in MAU if m[2] == muc), 3)

    def test_in_ti_le_trung_top_1_va_top_5(self):
        """Test này LUÔN xanh — nó công bố số, không phán quyết. Ngưỡng nằm ở
        `test_bao_cao_phai_khuyen_nghi_dung_neu_top5_duoi_90`."""
        top1 = self._ket_qua(1)
        top5 = self._ket_qua(5)
        t1 = sum(1 for r in top1 if r[3]) / len(top1) * 100
        t5 = sum(1 for r in top5 if r[3]) / len(top5) * 100
        theo_kho = {}
        for _, _, do_kho, ok, _ in top5:
            o = theo_kho.setdefault(do_kho, [0, 0])
            o[0] += int(ok)
            o[1] += 1
        print(f"\nTỈ LỆ TRÚNG trên {len(MAU)} prompt mẫu: "
              f"top-1 = {t1:.1f}% · top-5 = {t5:.1f}%")
        for muc in ("dễ", "vừa", "khó"):
            if muc in theo_kho:
                dung, tong = theo_kho[muc]
                print(f"  top-5 nhóm {muc}: {dung}/{tong} = {dung / tong * 100:.1f}%")
        truot = [r[0] for r in top5 if not r[3]]
        if truot:
            print(f"  TRƯỢT top-5 ({len(truot)}): " + " · ".join(truot))
        self.assertGreaterEqual(t5, t1, "top-5 không thể tệ hơn top-1")

    def test_hoi_tieng_anh_trung_han_hoi_tieng_viet_cung_mot_y(self):
        """Bằng chứng cho nguyên nhân gốc, không phải để router đẹp lên.

        Cùng MỘT ý định, hỏi hai thứ tiếng. Kho mô tả gần như toàn tiếng Anh, nên
        nếu tiếng Anh trúng mà tiếng Việt trượt thì cái hỏng KHÔNG phải BM25 — là
        khoảng cách ngôn ngữ giữa câu hỏi và mô tả. Số này quyết định câu khuyến
        nghị ở đề án: router từ khoá không phục vụ được user gõ tiếng Việt.
        """
        cap = [
            ("mọi thứ trông lệch nhau, không thẳng hàng",
             "elements are misaligned, fix the visual layout", "frontend-design"),
            ("nhân vật trong game đi xuyên tường",
             "game character passes through walls, collision bug", "unity-patterns"),
            ("kiểm tra chất lượng code trước khi merge",
             "check code quality gate before merging", "sonar-quality-gate"),
            ("nghiên cứu sâu một chủ đề trên web rồi tổng hợp",
             "deep research a topic on the web and synthesize", "tavily-research"),
        ]
        viet = anh = 0
        for cau_viet, cau_anh, dung in cap:
            tv = dung in [b["ten"] for _, b in self.kho.tra(cau_viet, 5)]
            ta = dung in [b["ten"] for _, b in self.kho.tra(cau_anh, 5)]
            viet += tv
            anh += ta
            print(f"  {dung}: VI={'trúng' if tv else 'TRƯỢT'} · "
                  f"EN={'trúng' if ta else 'TRƯỢT'}")
        print(f"CÙNG Ý ĐỊNH, {len(cap)} cặp — top-5 tiếng Việt {viet}/{len(cap)} · "
              f"tiếng Anh {anh}/{len(cap)}")
        self.assertGreater(anh, viet,
                           "nếu hai thứ tiếng ngang nhau thì nguyên nhân gốc là thứ "
                           "khác, phải đi tìm lại chứ không được kết luận vội")

    def test_nhom_de_phai_gan_nhu_trung_het(self):
        """Prompt nhắc thẳng tên công cụ mà còn trượt thì BM25 hỏng, không phải khó."""
        de = [r for r in self._ket_qua(5) if r[2] == "dễ"]
        ti_le = sum(1 for r in de if r[3]) / len(de) * 100
        self.assertGreaterEqual(ti_le, 80.0,
                                f"nhóm dễ chỉ trúng {ti_le:.1f}% — chỉ mục có vấn đề")


class DomainBoostTest(unittest.TestCase):
    """Domain-aware BM25 boosting, tra_cuu() signatures, and CLI --domain behavior."""

    @staticmethod
    def _synthetic_records():
        return [
            {
                "ten": "generic-alpha",
                "mo_ta": "deploy release verify workflow",
                "nguon": "test",
                "duong_dan": "skills/generic-alpha/SKILL.md",
            },
            {
                "ten": "tdq-status",
                "mo_ta": "report current tdq status and verify workflow next step",
                "nguon": "test",
                "duong_dan": "skills/tdq-status/SKILL.md",
            },
            {
                "ten": "tdq-setup",
                "mo_ta": "install and verify workflow setup dependencies",
                "nguon": "test",
                "duong_dan": "skills/tdq-setup/SKILL.md",
            },
            {
                "ten": "tdq-checkportable",
                "mo_ta": "verify portable packaging manifest",
                "nguon": "test",
                "duong_dan": "skills/tdq-checkportable/SKILL.md",
            },
            {
                "ten": "extra-unrelated",
                "mo_ta": "unrelated frontend styling helper",
                "nguon": "test",
                "duong_dan": "skills/extra-unrelated/SKILL.md",
            },
        ]

    def test_tra_preferred_skills_boosts_1_25x_and_preserves_default(self):
        kho = skill_router.KhoBM25(self._synthetic_records())
        base = kho.tra("verify workflow", 5)
        self.assertEqual(base[0][1]["ten"], "generic-alpha")
        base_map = {b["ten"]: s for s, b in base}

        boosted = kho.tra("verify workflow", 5, preferred_skills=["tdq-setup", "tdq-status"])
        boosted_map = {b["ten"]: s for s, b in boosted}
        self.assertAlmostEqual(boosted_map["tdq-setup"], base_map["tdq-setup"] * 1.25)
        self.assertAlmostEqual(boosted_map["tdq-status"], base_map["tdq-status"] * 1.25)
        self.assertAlmostEqual(boosted_map["generic-alpha"], base_map["generic-alpha"])
        self.assertEqual([b["ten"] for _, b in boosted[:2]], ["tdq-setup", "tdq-status"])

    def test_tra_preferred_skills_floor_0_05_on_zero_match(self):
        kho = skill_router.KhoBM25(self._synthetic_records())
        self.assertEqual(kho.tra("zzzqqqxxx", 5), [])
        fallback = kho.tra(
            "zzzqqqxxx",
            2,
            preferred_skills=["tdq-setup", "tdq-status", "tdq-checkportable"],
        )
        self.assertEqual(len(fallback), 2)
        self.assertEqual([b["ten"] for _, b in fallback], ["tdq-checkportable", "tdq-setup"])
        self.assertTrue(all(abs(score - 0.05) < 1e-9 for score, _ in fallback))

    def test_tra_cuu_supports_spec_and_helper_signatures(self):
        records = self._synthetic_records()
        with tempfile.TemporaryDirectory() as tmp:
            res_spec = skill_router.tra_cuu(
                "verify workflow",
                records,
                domain_id="ops-checklist",
                top_k=3,
                cwd=tmp,
            )
            self.assertIsInstance(res_spec, list)
            self.assertTrue(all(isinstance(item, dict) for item in res_spec))
            self.assertIn(res_spec[0]["ten"], ("tdq-setup", "tdq-status", "tdq-checkportable"))
            self.assertNotIn("score", records[0])

            res_helper = skill_router.tra_cuu(
                "project status",
                k=3,
                domain_id="ops-checklist",
                project=tmp,
            )
            self.assertEqual(res_helper[0]["ten"], "tdq-status")

            res_pos = skill_router.tra_cuu("project status", 3, "ops-checklist", tmp)
            self.assertEqual(res_pos[0]["ten"], "tdq-status")

    def test_tra_cuu_respects_override_and_router_disabled_rollback(self):
        records = self._synthetic_records()
        with tempfile.TemporaryDirectory() as tmp:
            dom_dir = Path(tmp) / "docs" / "tdq" / "domains"
            dom_dir.mkdir(parents=True, exist_ok=True)
            (dom_dir / "custom-ops.json").write_text(
                json.dumps({
                    "domain_id": "custom-ops",
                    "preferred_skills": ["tdq-checkportable"],
                }),
                encoding="utf-8",
            )
            res_custom = skill_router.tra_cuu(
                "zzzqqqxxx", records, domain_id="custom-ops", top_k=2, cwd=tmp
            )
            self.assertEqual([item["ten"] for item in res_custom], ["tdq-checkportable"])

            cfg_path = Path(tmp) / "docs" / "tdq" / "config.json"
            cfg_path.write_text(
                json.dumps({"p1": {"domain_router_enabled": False}}),
                encoding="utf-8",
            )
            self.assertEqual(
                skill_router.tra_cuu("zzzqqqxxx", records, domain_id="custom-ops", cwd=tmp),
                [],
            )
            base_real = skill_router.tra_cuu("project status", k=3)
            disabled_real = skill_router.tra_cuu(
                "project status", k=3, domain_id="ops-checklist", project=tmp
            )
            self.assertEqual(
                [item["ten"] for item in disabled_real],
                [item["ten"] for item in base_real],
            )
            self.assertEqual(disabled_real[0]["ten"], "sonar-quality-gate")

            cfg_path.write_text(json.dumps({"domain_router_enabled": False}), encoding="utf-8")
            self.assertEqual(
                skill_router.tra_cuu(
                    "project status", k=3, domain_id="ops-checklist", project=tmp
                )[0]["ten"],
                "sonar-quality-gate",
            )

            cfg_path.unlink()
            with mock.patch.dict(os.environ, {"TDQ_DOMAIN_ROUTER_ENABLED": "0"}):
                self.assertEqual(
                    skill_router.tra_cuu(
                        "project status", k=3, domain_id="ops-checklist", project=tmp
                    )[0]["ten"],
                    "sonar-quality-gate",
                )

    def test_cli_domain_boost_unknown_domain_and_logging(self):
        rc_base, out_base, _ = chay("--tra", "project status", "-k", "3")
        self.assertEqual(rc_base, 0)
        self.assertIn("| 1 | sonar-quality-gate |", out_base)

        rc_boost, out_boost, err_boost = chay(
            "--tra", "project status", "-k", "3", "--domain", "ops-checklist"
        )
        self.assertEqual(rc_boost, 0)
        self.assertEqual(err_boost, "")
        self.assertIn("| 1 | tdq-status |", out_boost)

        rc_unk, out_unk, _ = chay(
            "--tra", "project status", "-k", "3", "--domain", "khong-ton-tai"
        )
        self.assertEqual(rc_unk, 0)
        self.assertEqual(out_unk, out_base)

        rc_floor, out_floor, _ = chay(
            "--tra", "zzzqqqxxx", "-k", "3", "--domain", "ops-checklist"
        )
        self.assertEqual(rc_floor, 0)
        self.assertIn("| 1 | tdq-status | 0.05 |", out_floor)

        proc_log = subprocess.run(
            [sys.executable, "-X", "utf8", SCRIPT, "--tra", "project status",
             "--domain", "ops-checklist"],
            check=False,
            capture_output=True,
            encoding="utf-8",
            timeout=60,
            env=dict(os.environ, TDQ_LOG="1"),
        )
        self.assertEqual(proc_log.returncode, 0)
        self.assertRegex(
            proc_log.stderr,
            r"^\[\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[^\]]*\]\s+skill_router",
        )

        proc_quiet = subprocess.run(
            [sys.executable, "-X", "utf8", SCRIPT, "--tra", "project status",
             "--domain", "ops-checklist"],
            check=False,
            capture_output=True,
            env=dict(os.environ, TDQ_LOG="0"),
            timeout=60,
        )
        self.assertEqual(proc_quiet.returncode, 0)
        self.assertEqual(proc_quiet.stderr, b"")

    def test_module_static_invariants_utf8_io_hooks_and_line_cap(self):
        src = (Path(ROOT) / "scripts" / "skill_router.py").read_text(encoding="utf-8")
        tree = ast.parse(src)
        top_imports = set()
        for node in tree.body:
            if isinstance(node, ast.Import):
                top_imports.update(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                top_imports.add(node.module.split(".")[0])
        self.assertIn("utf8_io", top_imports)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertNotIn("hooks", alias.name)
            elif isinstance(node, ast.ImportFrom):
                self.assertNotIn("hooks", node.module or "")
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                span = (node.end_lineno or node.lineno) - node.lineno + 1
                self.assertLessEqual(span, 50, f"{node.name} is {span} lines (> 50)")
        self.assertIsNotNone(re.search(r"utf8_io\.force_utf8\(", src))


if __name__ == "__main__":
    unittest.main()
