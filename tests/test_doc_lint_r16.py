"""Tests for doc_lint R16: Layer-1 readability gate for spec, plan, and reports."""
import contextlib
import io
import os
import shutil
import sys
import tempfile
import unittest

import pytest

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
if TESTS_DIR not in sys.path:
    sys.path.insert(0, TESTS_DIR)

from helper import ROOT

sys.path.insert(0, os.path.join(ROOT, "scripts"))
import doc_lint

pytestmark = pytest.mark.smoke

MOC_SLUG = "2026-11-21-1819-demo.md"
OLD_SLUG = "2026-11-21-1536-old.md"

CLEAN_BODY_15W = (
    "Hệ thống cũ khó đọc vì trộn dữ liệu thô. "
    "Bản mới tách hai lớp rõ ràng."
)


def _doc_text(
    title="# SPEC — Cải tiến trình bày",
    meta="Ngày: 2026-11-21 · Bản: 1.0",
    soul="Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md",
    callout="> **Tóm tắt dễ hiểu:** " + CLEAN_BODY_15W,
    extra_opening="",
    layer2_heading="## 1. Mục tiêu & phạm vi",
    layer2_body="- Chi tiết `scripts/doc_lint.py:1516` và bảng bên dưới.\n",
):
    parts = [title, "", meta, soul]
    if callout is not None:
        parts.extend(["", callout])
    if extra_opening:
        parts.extend(["", extra_opening])
    parts.extend(["", layer2_heading, "", layer2_body])
    return "\n".join(parts)


class _TmpDocMixin:
    def _make_tmp(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        return tmp

    def _write_doc(self, tmp, rel_path, content):
        full = os.path.join(tmp, rel_path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as fh:
            fh.write(content)
        return full

    def _r16_lint_messages(self, path):
        with contextlib.redirect_stderr(io.StringIO()):
            return [line for line in doc_lint.lint_file(path) if "[R16]" in line]


class TestR16ScopeAndMoc(unittest.TestCase, _TmpDocMixin):
    """Historical docs before R16_MOC, non-slugs, and non-target dirs are exempt."""

    def test_r16_moc_constant_matches_cutoff(self):
        self.assertEqual(doc_lint.R16_MOC, "2026-11-21-1819")

    def test_historical_files_before_moc_exempt(self):
        dirty = _doc_text(
            title="# REPORT — Cũ (a · b · c · d)",
            callout=None,
            extra_opening="Dòng mở đầu · có · bốn · dấu · chấm",
        )
        for rel in (
            f"docs/tdq/reports/{OLD_SLUG}",
            "docs/tdq/spec/2026-11-21-1818-old.md",
            "docs/tdq/plan/2026-10-03-0732-old.md",
        ):
            self.assertEqual(doc_lint.r16_loi(dirty, rel), [], rel)

        tmp = self._make_tmp()
        path = self._write_doc(tmp, f"docs/tdq/reports/{OLD_SLUG}", dirty)
        self.assertEqual(self._r16_lint_messages(path), [])

    def test_files_without_slug_exempt(self):
        dirty = _doc_text(callout=None, extra_opening="Một · hai · ba · bốn")
        for rel in (
            "docs/tdq/reports/README.md",
            "docs/tdq/spec/2026-11-21-notes.md",
            "docs/tdq/plan/summary.md",
        ):
            self.assertEqual(doc_lint.r16_loi(dirty, rel), [], rel)

    def test_non_target_dirs_exempt(self):
        dirty = _doc_text(callout=None, extra_opening="Một · hai · ba · bốn")
        for rel in (
            f"docs/tdq/brief/{MOC_SLUG}",
            f"docs/tdq/qc/{MOC_SLUG}",
            f"docs/tdq/research/{MOC_SLUG}",
            "docs/tdq/artifacts/2026-11-21-1819-demo/notes.md",
            f"docs/tdq/artifacts/2026-11-21-1819-demo/reports/{MOC_SLUG}",
            "docs/workinglog/2026-11-21.md",
        ):
            self.assertEqual(doc_lint.r16_loi(dirty, rel), [], rel)

        tmp = self._make_tmp()
        for rel in (f"docs/tdq/brief/{MOC_SLUG}", f"docs/tdq/qc/{MOC_SLUG}"):
            path = self._write_doc(tmp, rel, dirty)
            self.assertEqual(self._r16_lint_messages(path), [], rel)

    def test_existing_historical_repo_docs_produce_zero_r16(self):
        for folder in ("spec", "plan", "reports"):
            dir_path = os.path.join(ROOT, "docs", "tdq", folder)
            if not os.path.isdir(dir_path):
                continue
            for name in sorted(os.listdir(dir_path)):
                if not name.endswith(".md") or name[:15] >= doc_lint.R16_MOC:
                    continue
                full = os.path.join(dir_path, name)
                self.assertEqual(self._r16_lint_messages(full), [], full)


class TestR16CalloutViolations(unittest.TestCase, _TmpDocMixin):
    """Callout presence, word limits, sentence length, backtick density, raw paths."""

    def test_missing_callout_flagged_across_target_dirs(self):
        content = _doc_text(callout=None)
        for folder in ("spec", "plan", "reports"):
            rel = f"docs/tdq/{folder}/{MOC_SLUG}"
            findings = doc_lint.r16_loi(content, rel)
            self.assertTrue(findings, rel)

        tmp = self._make_tmp()
        path = self._write_doc(tmp, f"docs/tdq/reports/{MOC_SLUG}", content)
        self.assertTrue(self._r16_lint_messages(path))

    def test_empty_callout_flagged(self):
        content = _doc_text(callout="> **Tóm tắt dễ hiểu:**   ")
        findings = doc_lint.r16_loi(content, f"docs/tdq/spec/{MOC_SLUG}")
        self.assertTrue(findings)

    def test_callout_word_cap_120_boundary(self):
        # 4 sentences x 30 words = 120 words -> passes
        sent_30 = " ".join(["chữ"] * 29) + " cuối."
        ok_120 = "> **Tóm tắt dễ hiểu:** " + " ".join([sent_30] * 4)
        self.assertEqual(doc_lint.r16_loi(_doc_text(callout=ok_120), f"docs/tdq/plan/{MOC_SLUG}"), [])

        # 121 words (5 short sentences) -> flagged
        sent_24 = " ".join(["chữ"] * 23) + " cuối."
        over_121 = "> **Tóm tắt dễ hiểu:** " + " ".join([sent_24] * 5) + " thêm."
        findings = doc_lint.r16_loi(_doc_text(callout=over_121), f"docs/tdq/plan/{MOC_SLUG}")
        self.assertTrue(findings)

    def test_callout_sentence_over_35_words_flagged(self):
        sent_35 = " ".join(["từ"] * 35) + "."
        self.assertEqual(
            doc_lint.r16_loi(_doc_text(callout="> **Tóm tắt dễ hiểu:** " + sent_35), f"docs/tdq/reports/{MOC_SLUG}"),
            [],
        )
        sent_36 = " ".join(["từ"] * 36) + "."
        findings = doc_lint.r16_loi(
            _doc_text(callout="> **Tóm tắt dễ hiểu:** " + sent_36),
            f"docs/tdq/reports/{MOC_SLUG}",
        )
        self.assertTrue(findings)

    def test_callout_backtick_density_limit_6_per_100_words(self):
        # 50 words across 2 short sentences, 3 backtick pairs = 6.0 / 100w -> passes
        sent_a = " ".join(["từ"] * 25) + "."
        ok_bt = "> **Tóm tắt dễ hiểu:** `một` `hai` `ba` " + " ".join(["từ"] * 22) + ". " + sent_a
        self.assertEqual(doc_lint.r16_loi(_doc_text(callout=ok_bt), f"docs/tdq/spec/{MOC_SLUG}"), [])

        # 50 words across 2 short sentences, 4 backtick pairs = 8.0 / 100w -> flagged
        dense_bt = "> **Tóm tắt dễ hiểu:** `một` `hai` `ba` `bốn` " + " ".join(["từ"] * 21) + ". " + sent_a
        findings = doc_lint.r16_loi(_doc_text(callout=dense_bt), f"docs/tdq/spec/{MOC_SLUG}")
        self.assertEqual(len(findings), 1, findings)
        self.assertIn("backtick density", findings[0][1])

    def test_callout_raw_paths_and_line_refs_flagged(self):
        filler = " ".join(["từ"] * 25) + "."
        cases = (
            ("Sửa `scripts/doc_lint.py` xong rồi. " + filler, "path"),
            ("Xem tệp ../brief/2026-11-21-1819.md để biết. " + filler, "path"),
            ("Lỗi tại doc_lint.py:123 đã được xử lý. " + filler, ":line"),
            ("Kiểm tại :123 trước khi đóng gói. " + filler, ":line"),
        )
        for bad_ref, expected_kind in cases:
            findings = doc_lint.r16_loi(
                _doc_text(callout="> **Tóm tắt dễ hiểu:** " + bad_ref),
                f"docs/tdq/reports/{MOC_SLUG}",
            )
            self.assertEqual(len(findings), 1, (bad_ref, findings))
            self.assertIn(expected_kind, findings[0][1], findings)

        # Legitimate time-of-day and slash word pairs must not false-positive
        ok_prose = (
            "> **Tóm tắt dễ hiểu:** Phiên lúc 17:30 cải thiện cách đọc trước/sau khi chạy "
            "cho spec/plan/report mà vẫn giữ đầy đủ kết quả."
        )
        self.assertEqual(doc_lint.r16_loi(_doc_text(callout=ok_prose), f"docs/tdq/reports/{MOC_SLUG}"), [])

    def test_multiline_callout_supported_and_checked(self):
        ok_multi = (
            "> **Tóm tắt dễ hiểu:** Bản cũ hay trộn thông số vào đầu tài liệu.\n"
            "> Bản mới tách hai lớp rõ ràng hơn."
        )
        self.assertEqual(doc_lint.r16_loi(_doc_text(callout=ok_multi), f"docs/tdq/plan/{MOC_SLUG}"), [])

        bad_multi = (
            "> **Tóm tắt dễ hiểu:** Bản cũ hay trộn thông số vào đầu tài liệu.\n"
            "> Xem thêm ở scripts/doc_lint.py:42 để kiểm tra lại toàn bộ hệ thống sau sửa."
        )
        self.assertTrue(doc_lint.r16_loi(_doc_text(callout=bad_multi), f"docs/tdq/plan/{MOC_SLUG}"))


class TestR16OpeningAndLayer2(unittest.TestCase, _TmpDocMixin):
    """Middle-dot packing in Layer 1 vs immunity for Soul, tables, link lines, and Layer 2."""

    def test_middle_dots_3_or_more_in_opening_flagged(self):
        bad_prose = _doc_text(extra_opening="Mục A · Mục B · Mục C · Mục D")
        self.assertTrue(doc_lint.r16_loi(bad_prose, f"docs/tdq/reports/{MOC_SLUG}"))

        bad_h1 = _doc_text(title="# REPORT — Kiểm thử (`slug` · lane full · mode main · 4/4 task)")
        self.assertTrue(doc_lint.r16_loi(bad_h1, f"docs/tdq/reports/{MOC_SLUG}"))

    def test_soul_table_blockquote_and_1_or_2_dots_exempt(self):
        clean_opening = _doc_text(
            meta="Ngày: 2026-11-21 · Bản: 1.0 · Trạng thái: XONG",
            soul="Soul: chất lượng > runtime > context cost · a · b · c · d",
            extra_opening=(
                "| Cột 1 · Cột 2 · Cột 3 · Cột 4 |\n"
                "|---|\n"
                "| A · B · C · D |\n\n"
                "> Ghi chú · phụ · vẫn · bỏ qua"
            ),
        )
        self.assertEqual(doc_lint.r16_loi(clean_opening, f"docs/tdq/spec/{MOC_SLUG}"), [])

    def test_link_lines_after_callout_are_not_rejected(self):
        link_line = (
            "**Tệp liên quan:** [Báo cáo trước](../reports/2026-11-21-1736-old.md) · "
            "[Sổ bằng chứng](../artifacts/2026-11-21-1819-demo/evidence.md)"
        )
        content = _doc_text(extra_opening=link_line)
        self.assertEqual(doc_lint.r16_loi(content, f"docs/tdq/reports/{MOC_SLUG}"), [])

    def test_layer2_after_section1_or_toc_never_triggers_r16(self):
        dense_layer2 = (
            "| Hàm | Tệp | Ghi chú |\n"
            "|---|---|---|\n"
            "| `r16_loi` | `scripts/doc_lint.py:1500` | `a` · `b` · `c` · `d` |\n\n"
            "```python\n"
            "def demo(): return 'scripts/a.py:10'\n"
            "```\n\n"
            "- Chạy `py -3 -X utf8 scripts/doc_lint.py` với `a` `b` `c` `d` `e` `f` `g` tại `scripts/doc_lint.py:99` · x · y · z.\n\n"
            "## Thời gian\n\n"
            "Request `2026-11-21-1819-demo` · lane full · opened at 2026-11-21T18:19:00+07:00\n\n"
            "Model compute time is unavailable (`model_giay=null`). API includes network latency.\n"
        )
        for heading in ("## 1. Mục tiêu & phạm vi", "## Mục lục"):
            content = _doc_text(layer2_heading=heading, layer2_body=dense_layer2)
            self.assertEqual(doc_lint.r16_loi(content, f"docs/tdq/spec/{MOC_SLUG}"), [], heading)


class TestR16CleanAndAllow(unittest.TestCase, _TmpDocMixin):
    """Clean 2026-11-21-1819 docs, allow-comment suppression, and logging."""

    def test_clean_synthetic_spec_plan_report_pass(self):
        tmp = self._make_tmp()
        for folder, title in (
            ("spec", "# SPEC — Triển khai trình bày hai tầng"),
            ("plan", "# PLAN — Triển khai trình bày hai tầng"),
            ("reports", "# BÁO CÁO — Triển khai trình bày hai tầng"),
        ):
            content = _doc_text(
                title=title,
                layer2_heading="## Mục lục" if folder != "reports" else "## 1. Trước request",
            )
            rel = f"docs/tdq/{folder}/{MOC_SLUG}"
            self.assertEqual(doc_lint.r16_loi(content, rel), [], folder)
            path = self._write_doc(tmp, rel, content)
            self.assertEqual(self._r16_lint_messages(path), [], folder)

    def test_current_2026_11_21_1819_plan_on_disk_passes_when_present(self):
        plan_path = os.path.join(ROOT, "docs", "tdq", "plan", "2026-11-21-1819-trien-khai-trinh-bay-2-tang.md")
        if os.path.isfile(plan_path):
            self.assertEqual(self._r16_lint_messages(plan_path), [])

    def test_allow_r16_comment_suppresses_offending_lines(self):
        tmp = self._make_tmp()
        # 1) Above offending callout
        bad_callout = "> **Tóm tắt dễ hiểu:** " + " ".join(["từ"] * 40) + "."
        allowed_callout = _doc_text(callout="<!-- doc-lint: allow R16 -->\n" + bad_callout)
        self.assertEqual(doc_lint.r16_loi(allowed_callout, f"docs/tdq/reports/{MOC_SLUG}"), [])
        p1 = self._write_doc(tmp, f"docs/tdq/reports/{MOC_SLUG}", allowed_callout)
        self.assertEqual(self._r16_lint_messages(p1), [])

        # 2) Above 3+ middle-dot line
        allowed_dots = _doc_text(extra_opening="<!-- doc-lint: allow R16 -->\nA · B · C · D")
        self.assertEqual(doc_lint.r16_loi(allowed_dots, f"docs/tdq/plan/{MOC_SLUG}"), [])
        p2 = self._write_doc(tmp, f"docs/tdq/plan/{MOC_SLUG}", allowed_dots)
        self.assertEqual(self._r16_lint_messages(p2), [])

        # 3) Line 1 allow for missing callout
        allowed_missing = "<!-- doc-lint: allow R16 -->\n" + _doc_text(callout=None)
        self.assertEqual(doc_lint.r16_loi(allowed_missing, f"docs/tdq/spec/{MOC_SLUG}"), [])
        p3 = self._write_doc(tmp, f"docs/tdq/spec/{MOC_SLUG}", allowed_missing)
        self.assertEqual(self._r16_lint_messages(p3), [])

        # 4) Wrong allow code still triggers R16
        wrong_allow = _doc_text(extra_opening="<!-- doc-lint: allow R15 -->\nA · B · C · D")
        self.assertTrue(doc_lint.r16_loi(wrong_allow, f"docs/tdq/plan/{MOC_SLUG}"))

    def test_r16_logs_iso_timestamp_and_respects_tdq_log_zero(self):
        tmp = self._make_tmp()
        path = self._write_doc(tmp, f"docs/tdq/reports/{MOC_SLUG}", _doc_text())
        old_val = os.environ.get("TDQ_LOG")
        self.addCleanup(
            lambda: os.environ.__setitem__("TDQ_LOG", old_val)
            if old_val is not None
            else os.environ.pop("TDQ_LOG", None)
        )

        os.environ["TDQ_LOG"] = "1"
        buf_on = io.StringIO()
        with contextlib.redirect_stderr(buf_on):
            doc_lint.lint_file(path)
        self.assertRegex(buf_on.getvalue(), r"\[\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\].*R16")

        os.environ["TDQ_LOG"] = "0"
        buf_off = io.StringIO()
        with contextlib.redirect_stderr(buf_off):
            doc_lint.lint_file(path)
        self.assertEqual(buf_off.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
