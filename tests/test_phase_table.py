"""P1/P3 — PHASE_TABLE là nguồn sự thật duy nhất; doc phải khớp hằng trong code."""
import os
import re
import tempfile
import unittest

from helper import ROOT, tdq_state, write_state

REQUIRED_KEYS = {"entry", "action", "cmd", "checklist", "done_when", "forbidden"}
DOC_FILES = [
    os.path.join(ROOT, "skills", "tdq-conventions", "references", "phases.md"),
]


class PhaseTableTest(unittest.TestCase):
    def test_all_phases_covered(self):
        keys = set(tdq_state.PHASE_TABLE)
        self.assertTrue(tdq_state.VALID_PHASES <= keys,
                        f"thiếu phase: {tdq_state.VALID_PHASES - keys}")
        self.assertIn("no_state", keys)
        self.assertIn("quick", keys)
        self.assertIn("quick_analyze", keys)
        # 8 pha hợp lệ + `no_state` + `quick` + `quick_analyze`. Pha `diagram` bị gỡ
        # ngày 2026-09-01 (11 → 10); `quick_analyze` thêm 2026-09-01 (10 → 11).
        self.assertEqual(len(keys), 11, sorted(keys))

    def test_every_row_complete(self):
        for name, row in tdq_state.PHASE_TABLE.items():
            with self.subTest(phase=name):
                self.assertEqual(REQUIRED_KEYS, set(row), name)
                self.assertTrue(row["checklist"], name)
                self.assertTrue(all(isinstance(i, str) and i.strip() for i in row["checklist"]))
                for key in ("entry", "action", "cmd", "done_when", "forbidden"):
                    self.assertTrue(str(row[key]).strip(), f"{name}.{key} rỗng")

    def test_phase_key_mapping(self):
        self.assertEqual(tdq_state.phase_key(None), "no_state")
        self.assertEqual(tdq_state.phase_key({}), "no_state")
        self.assertEqual(tdq_state.phase_key({"active_request": "r", "lane": "quick",
                                              "phase": "implement"}), "quick")
        self.assertEqual(tdq_state.phase_key({"active_request": "r", "lane": "full",
                                              "phase": "qc"}), "qc")
        self.assertEqual(tdq_state.phase_key({"active_request": "r", "lane": "full",
                                              "phase": "sai"}), "idle")

    def test_phase_key_quick_terminal(self):
        """A6: lane quick phải có terminal — quick_approved + phase=idle là đã xong."""
        base = {"active_request": "r", "lane": "quick"}
        self.assertEqual(tdq_state.phase_key({**base, "phase": "idle"}), "quick")
        self.assertEqual(tdq_state.phase_key({**base, "phase": "implement",
                                              "quick_approved": True}), "quick")
        self.assertEqual(tdq_state.phase_key({**base, "phase": "idle",
                                              "quick_approved": True}), "idle")

    def test_phase_key_quick_analyze(self):
        """Phương án 2a: lane nhanh có pha `analyze` HIỆN TÊN, nhưng không thêm cổng.

        Trước 2026-09-01 `phase_key` nuốt mọi pha của lane quick về hàng `quick`, nên
        bước phân tích không nhìn thấy được ở đâu cả. Hàng riêng chỉ hiện khi đúng
        `phase=analyze`; mọi pha khác vẫn về `quick` như cũ.
        """
        base = {"active_request": "r", "lane": "quick"}
        self.assertEqual(tdq_state.phase_key({**base, "phase": "analyze"}), "quick_analyze")
        self.assertEqual(tdq_state.phase_key({**base, "phase": "implement"}), "quick")
        # Đã duyệt rồi thì phân tích xong từ lâu — không quay lại hàng phân tích nữa.
        self.assertEqual(tdq_state.phase_key({**base, "phase": "analyze",
                                              "quick_approved": True}), "quick")

    def test_lane_quick_van_chi_mot_cong(self):
        """Canh 2a không trượt thành 2c: thêm pha phân tích KHÔNG được thêm cổng duyệt."""
        self.assertEqual(tdq_state.CONG_THEO_LANE["quick"], ("quick",))

    def test_quick_analyze_khong_nhay_implement_truoc_duyet(self):
        """play3clone 2026-11-08: `cmd` cũ bảo `set phase=implement` khi quick CHƯA duyệt —
        hàng này chỉ hiện trước `quick_approved`, nên lệnh kế phải là chính cổng duyệt."""
        cmd = tdq_state.PHASE_TABLE["quick_analyze"]["cmd"]
        self.assertNotIn("phase=implement", cmd)
        self.assertIn("approve quick", cmd)
        self.assertNotIn("analyze", tdq_state.APPROVE_TARGETS)
        state = {"active_request": "r", "lane": "quick", "phase": "analyze"}
        self.assertEqual(tdq_state.cong_dang_cho(state), "quick")
        self.assertIsNone(tdq_state.cong_dang_cho({**state, "quick_approved": True}))

    def test_render_no_regex_escape_artifact(self):
        """Bug A1: escape sai trong re.sub → literal `\\1` thay vì lệnh thật."""
        doc = tdq_state.render_phases_md()
        self.assertNotIn("`\\1`", doc, "phases-doc chứa literal `\\1` — lệnh bị nuốt")
        for line in doc.splitlines():
            if re.match(r"^\d+\. ", line):
                self.assertNotIn("``", line, f"wrap đôi hỏng inline-code: {line}")
        # Từ 2026-08-09 phases-doc không sinh mục chi tiết từng phase nữa; lệnh thật
        # nằm ở khối "Lệnh nguyên văn" và ở cột lệnh của bảng.
        self.assertNotIn("\n## analyze", doc, "phases-doc còn sinh mục chi tiết phase")
        block = doc.split("The commands verbatim", 1)[1]
        for section in ("analyze", "spec", "plan"):
            self.assertIn(f"{section}: python3 scripts/", block,
                          f"khối lệnh nguyên văn mất lệnh của {section}")
        for section in ("spec", "plan"):
            self.assertIn(f"{section}: python3 scripts/tdq_state.py", block,
                          f"khối lệnh nguyên văn mất lệnh tdq_state.py của {section}")

    def test_quick_row_muc_qc_and_terminal(self):
        """2026-09-23: biến thể bỏ QC thay bằng thang mức `muc_qc`; A6: có bước đóng."""
        row = tdq_state.PHASE_TABLE["quick"]
        self.assertNotIn("--no-qc", row["cmd"])
        joined = " ".join(row["checklist"])
        self.assertIn("muc_qc", joined)
        self.assertIn("set phase=report", joined)
        self.assertNotIn("set phase=idle", joined)

    def test_quick_report_reuses_existing_phase_and_gate(self):
        base = {"active_request": "r", "lane": "quick"}
        self.assertEqual(tdq_state.phase_key({**base, "phase": "report", "quick_approved": True}), "report")
        self.assertEqual(tdq_state.phase_key({**base, "phase": "report", "quick_approved": False}), "quick")
        self.assertEqual(tdq_state.PHASE_TABLE["report"]["cmd"], "python3 scripts/tdq_state.py set phase=idle")
        self.assertEqual(tdq_state.CONG_THEO_LANE["quick"], ("quick",))
        self.assertNotIn("report", tdq_state.APPROVE_TARGETS)

    def test_render_plugin_root_variant(self):
        """A40: bản chạy trong ngữ cảnh plugin phải in path plugin-root."""
        doc = tdq_state.render_phases_md(plugin_root=True)
        self.assertIn('python3 "${CLAUDE_PLUGIN_ROOT}/scripts/tdq_state.py"', doc)
        self.assertNotIn("python3 scripts/", doc)

    def test_docs_match_constant(self):
        """Mỗi phase phải xuất hiện trong doc kèm đúng lệnh chuyển tiếp.

        A40: bản conventions chạy trong ngữ cảnh plugin → lệnh dạng plugin-root.
        """
        for doc in DOC_FILES:
            self.assertTrue(os.path.isfile(doc), f"thiếu {doc}")
            with open(doc, encoding="utf-8") as fh:
                text = fh.read()
            for name, row in tdq_state.PHASE_TABLE.items():
                with self.subTest(doc=os.path.basename(doc), phase=name):
                    self.assertIn(name, text, f"{doc}: thiếu phase {name}")
                    cmd = tdq_state.plugin_root_cmd(row["cmd"])
                    self.assertIn(cmd, text, f"{doc}: lệnh của {name} không khớp code")


if __name__ == "__main__":
    unittest.main()


class ModeRowsTest(unittest.TestCase):
    """T1.2 — `phase_row` rẽ bằng BẢNG TRA, không bằng `if == "subagent"`.

    Ba bất biến:
    1. Mọi mode trong VALID_MODES đều khai một hàng phase `implement`.
    2. `phase_row` trả đúng hàng đã khai cho từng mode — vòng qua cả bảng,
       nên thêm mode thứ tư chỉ cần thêm một dòng bảng.
    3. Mode có trong VALID_MODES mà thiếu khai thì lỗi NGAY lúc nạp bảng,
       không phải lỗi im lặng lúc hiển thị.
    """

    def _state(self, mode):
        return {"active_request": "r", "lane": "full", "phase": "implement",
                "plan_approved": True, "spec_approved": True,
                "implement_mode": mode}

    def test_moi_mode_deu_khai_hang_implement(self):
        for mode in tdq_state.VALID_MODES:
            with self.subTest(mode=mode):
                self.assertIn(mode, tdq_state.MODE_ROWS)

    def test_phase_row_tra_dung_hang_da_khai(self):
        for mode in tdq_state.VALID_MODES:
            with self.subTest(mode=mode):
                row = tdq_state.phase_row(self._state(mode))
                khai = tdq_state.MODE_ROWS[mode] or tdq_state.PHASE_TABLE["implement"]
                self.assertIs(row, khai)
                self.assertEqual(REQUIRED_KEYS, set(row))

    def test_hang_cua_moi_mode_la_rieng_biet(self):
        """Hai mode khác nhau không được dùng chung một hàng — nếu dùng chung
        thì người đọc `next` không biết mình đang ở nhịp nào."""
        thay = [id(tdq_state.MODE_ROWS[m] or tdq_state.PHASE_TABLE["implement"])
                for m in tdq_state.VALID_MODES]
        self.assertEqual(len(thay), len(set(thay)), "hai mode dùng chung một hàng")

    def test_thieu_khai_thi_loi_ngay_luc_nap_bang(self):
        with self.assertRaises(Exception) as ctx:
            tdq_state.kiem_bang_mode(("main", "subagent", "codex", "mode_gia"),
                                     tdq_state.MODE_ROWS)
        self.assertIn("mode_gia", str(ctx.exception))

    def test_them_mode_chi_can_them_dong_bang(self):
        """Thêm mode giả VÀ khai hàng cho nó thì bảng hợp lệ — không phải sửa
        thân hàm nào."""
        hang_gia = dict(tdq_state.PHASE_TABLE["implement"])
        bang = dict(tdq_state.MODE_ROWS, mode_gia=hang_gia)
        tdq_state.kiem_bang_mode(("main", "subagent", "codex", "mode_gia"), bang)


class InvestigatePhaseRowsTest(unittest.TestCase):
    """M1 — INVESTIGATE_PHASE_ROWS routes investigation phases without mutating PHASE_TABLE."""

    EXPECTED_KEYS = {"analyze", "spec", "plan", "implement", "qc", "quick_analyze", "quick"}

    def test_phase_table_unchanged_for_build(self):
        self.assertEqual(len(tdq_state.PHASE_TABLE), 11)
        for phase in ("analyze", "spec", "plan", "qc"):
            row = tdq_state.phase_row(
                {"active_request": "r", "lane": "full", "phase": phase, "work_kind": "build"}
            )
            self.assertIs(row, tdq_state.PHASE_TABLE[phase])

    def test_investigate_phase_rows_complete_and_single_line(self):
        self.assertEqual(set(tdq_state.INVESTIGATE_PHASE_ROWS), self.EXPECTED_KEYS)
        for name, row in tdq_state.INVESTIGATE_PHASE_ROWS.items():
            with self.subTest(phase=name):
                self.assertEqual(REQUIRED_KEYS, set(row))
                self.assertTrue(row["checklist"])
                self.assertTrue(all(isinstance(i, str) and i.strip() for i in row["checklist"]))
                for field in ("entry", "action", "cmd", "done_when", "forbidden"):
                    val = str(row[field]).strip()
                    self.assertTrue(val, f"{name}.{field} empty")
                    self.assertNotIn("\n", val, f"{name}.{field} must stay single-line")

    def test_phase_row_routes_investigate_and_ignores_build_subagent_row(self):
        for key in ("analyze", "spec", "plan", "implement", "qc"):
            with self.subTest(phase=key):
                row = tdq_state.phase_row(
                    {"active_request": "r", "lane": "full", "phase": key, "work_kind": "investigate"}
                )
                self.assertIs(row, tdq_state.INVESTIGATE_PHASE_ROWS[key])

        sub_row = tdq_state.phase_row(
            {
                "active_request": "r",
                "lane": "full",
                "phase": "implement",
                "implement_mode": "subagent",
                "work_kind": "investigate",
            }
        )
        self.assertIs(sub_row, tdq_state.INVESTIGATE_PHASE_ROWS["implement"])

        qa_row = tdq_state.phase_row(
            {"active_request": "r", "lane": "quick", "phase": "analyze", "work_kind": "investigate"}
        )
        self.assertIs(qa_row, tdq_state.INVESTIGATE_PHASE_ROWS["quick_analyze"])

        q_row = tdq_state.phase_row(
            {
                "active_request": "r",
                "lane": "quick",
                "phase": "implement",
                "quick_approved": True,
                "work_kind": "investigate",
            }
        )
        self.assertIs(q_row, tdq_state.INVESTIGATE_PHASE_ROWS["quick"])

        rep_row = tdq_state.phase_row(
            {"active_request": "r", "lane": "full", "phase": "report", "work_kind": "investigate"}
        )
        self.assertIs(rep_row, tdq_state.PHASE_TABLE["report"])

    def test_investigate_guidance_references_expected_mechanisms(self):
        analyze_txt = (
            tdq_state.INVESTIGATE_PHASE_ROWS["analyze"]["action"]
            + " ".join(tdq_state.INVESTIGATE_PHASE_ROWS["analyze"]["checklist"])
        ).lower()
        self.assertIn("hypothes", analyze_txt)

        impl_txt = (
            tdq_state.INVESTIGATE_PHASE_ROWS["implement"]["action"]
            + " ".join(tdq_state.INVESTIGATE_PHASE_ROWS["implement"]["checklist"])
        )
        self.assertIn("evidence merge", impl_txt)
        self.assertIn("Weighted Burden", impl_txt)

        qc_txt = (
            tdq_state.INVESTIGATE_PHASE_ROWS["qc"]["action"]
            + " ".join(tdq_state.INVESTIGATE_PHASE_ROWS["qc"]["checklist"])
        )
        self.assertIn("QC-I1..I4", qc_txt)
        self.assertIn("docs/tdq/", qc_txt)

    def test_investigate_compact_head_and_state_md_budgets(self):
        rule_line = (
            "[TDQ] Rule: a [TDQ:<CODE>] line means do exactly that job FIRST, "
            "then print ✓ [TDQ:<CODE>]. Write state only via scripts/tdq_state.py."
        )
        with tempfile.TemporaryDirectory() as tmp:
            long_cwd = tmp
            while len(long_cwd) < 180:
                long_cwd = os.path.join(long_cwd, "long-folder-segment-name")
            os.makedirs(long_cwd, exist_ok=True)
            slug = "2026-11-21-0217-very-long-investigate-slug"
            for lane, phase, approved in (
                ("full", "analyze", False),
                ("full", "spec", False),
                ("full", "plan", True),
                ("full", "implement", True),
                ("full", "qc", True),
                ("quick", "analyze", False),
                ("quick", "implement", True),
            ):
                state = write_state(
                    long_cwd,
                    active_request=slug,
                    lane=lane,
                    phase=phase,
                    work_kind="investigate",
                    spec_approved=approved,
                    plan_approved=approved,
                    quick_approved=approved,
                    implement_mode="subagent" if approved else None,
                )
                with self.subTest(lane=lane, phase=phase):
                    compact = tdq_state.render_next(long_cwd, state, compact=True)
                    head_block = rule_line + "\n" + compact
                    self.assertLessEqual(len(head_block), 600)
                    self.assertLessEqual(len(head_block.splitlines()), 12)
                    self.assertIn("· kind:inv", compact.splitlines()[0])
                    self.assertIn("Done when:", compact)

                    full_next = tdq_state.render_next(long_cwd, state)
                    self.assertLessEqual(len(full_next.splitlines()), 20)

                    md = tdq_state.render_state_md(long_cwd, state)
                    self.assertLessEqual(len(md.splitlines()), 30)
                    self.assertIn("| Work kind | investigate |", md)
