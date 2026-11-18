"""Unit tests for tools/patches/gate_guidance.py (4-part AGY guidance dictionary and formatters)."""
import importlib.util
import io
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.patches import gate_guidance

EXPECTED_HARD_DENY = (
    "APPROVE",
    "GIT",
    "TEAM",
    "STATE",
    "READONLY",
    "VUNG",
    "ZERO-POPUP",
    "SUBAGENT",
    "UNFINISHED",
)
EXPECTED_OVERWRITE = ("LSP", "SUBAGENT")
EXPECTED_GUIDANCE = (
    "SEARCH",
    "TICK",
    "DOC",
    "LOG",
    "OUTPUT",
    "SETUP",
    "GON",
    "NEXT",
    "WORKTREE",
    "ANCHOR",
    "DOD",
    "INTAKE",
)
EXPECTED_REMOVED = ("ASK", "DEVTOOL", "FEEDBACK", "GATE", "QC", "RULE", "STUCK")
FOUR_PART_LABELS = (
    "Chuyện gì",  # i18n-allow
    "Vì sao",  # i18n-allow
    "Làm gì",  # i18n-allow
    "Bỏ qua",  # i18n-allow
)
BANNED_CHARS = ("✅", "❌", "⚠️", "┌", "│", "─")


class TestGateGuidanceConstants(unittest.TestCase):
    """Verify code groups, deduplicated 22-code union, and 7 removed codes."""

    def test_code_groups_and_counts(self):
        self.assertEqual(gate_guidance.HARD_DENY_CODES, EXPECTED_HARD_DENY)
        self.assertEqual(gate_guidance.OVERWRITE_CODES, EXPECTED_OVERWRITE)
        self.assertEqual(gate_guidance.GUIDANCE_CODES, EXPECTED_GUIDANCE)
        self.assertEqual(gate_guidance.LEAN_REMOVED_CODES, EXPECTED_REMOVED)

        self.assertEqual(len(gate_guidance.HARD_DENY_CODES), 9)
        self.assertEqual(len(gate_guidance.OVERWRITE_CODES), 2)
        self.assertEqual(len(gate_guidance.GUIDANCE_CODES), 12)
        self.assertEqual(len(gate_guidance.LEAN_REMOVED_CODES), 7)

        union_codes = (
            set(gate_guidance.HARD_DENY_CODES)
            | set(gate_guidance.OVERWRITE_CODES)
            | set(gate_guidance.GUIDANCE_CODES)
        )
        self.assertEqual(len(union_codes), 22)
        self.assertEqual(len(gate_guidance.ALL_AGY_CODES), 22)
        self.assertEqual(set(gate_guidance.ALL_AGY_CODES), union_codes)
        self.assertEqual(
            set(gate_guidance.HARD_DENY_CODES) & set(gate_guidance.OVERWRITE_CODES),
            {"SUBAGENT"},
        )
        self.assertTrue(
            set(gate_guidance.LEAN_REMOVED_CODES).isdisjoint(gate_guidance.ALL_AGY_CODES)
        )

    def test_guidance_table_complete_and_valid(self):
        self.assertEqual(
            set(gate_guidance.GUIDANCE_TABLE.keys()),
            set(gate_guidance.ALL_AGY_CODES),
        )
        required_keys = ("chuyen_gi", "vi_sao", "lam_gi", "bo_qua", "model_hint")
        for code, entry in gate_guidance.GUIDANCE_TABLE.items():
            for key in required_keys:
                self.assertIn(key, entry, f"{code} missing {key}")
                val = entry[key]
                self.assertIsInstance(val, str, f"{code}.{key} must be str")
                self.assertTrue(val.strip(), f"{code}.{key} must be non-empty")
            hint = entry["model_hint"]
            self.assertLessEqual(len(hint), 160, f"{code} model_hint exceeds 160 chars")
            self.assertTrue(hint.isascii(), f"{code} model_hint must be pure ASCII English")
            self.assertLessEqual(
                len(f"[TDQ:{code}] {hint}"),
                160,
                f"{code} full model_line exceeds 160 chars",
            )
            for field in ("chuyen_gi", "vi_sao", "lam_gi", "bo_qua"):
                text = entry[field]
                for ch in BANNED_CHARS:
                    self.assertNotIn(ch, text, f"{code}.{field} contains banned char {ch}")


class TestNormalizeAndFormatters(unittest.TestCase):
    """Verify normalization, 4-part formatting, reminder building, and caps."""

    def test_normalize_code_variants(self):
        cases = {
            "APPROVE": "APPROVE",
            "approve": "APPROVE",
            "[TDQ:APPROVE]": "APPROVE",
            "TDQ:SEARCH": "SEARCH",
            "  [tdq:zero-popup]  ": "ZERO-POPUP",
            "[DOC]": "DOC",
            "tdq: subagent": "SUBAGENT",
            "": "",
            "   ": "",
        }
        for raw, expected in cases.items():
            self.assertEqual(gate_guidance.normalize_code(raw), expected, raw)

    def test_format_deny_4part_variants_and_unknown(self):
        for raw in ("[TDQ:APPROVE]", "TDQ:SEARCH", "APPROVE", "CUSTOM_UNKNOWN", ""):
            rendered = gate_guidance.format_deny_4part(raw, detail="file=a.py")
            norm = gate_guidance.normalize_code(raw) or "UNKNOWN"
            self.assertIn(f"[TDQ:{norm}]", rendered)
            self.assertIn("file=a.py", rendered)
            self.assertLessEqual(len(rendered), 1200)
            for label in FOUR_PART_LABELS:
                self.assertIn(label, rendered, f"{raw} missing label {label}")

    def test_format_deny_4part_caps_giant_detail_cleanly(self):
        giant = "token " * 400
        rendered = gate_guidance.format_deny_4part("STATE", detail=giant)
        self.assertLessEqual(len(rendered), 1200)
        self.assertIn("[TDQ:STATE]", rendered)
        for label in FOUR_PART_LABELS:
            self.assertIn(label, rendered)

    def test_build_reminder_entry_all_codes_and_fallback(self):
        for raw in list(gate_guidance.ALL_AGY_CODES) + ["[TDQ:SEARCH]", "TDQ:LSP", "NONEXISTENT", ""]:
            entry = gate_guidance.build_reminder_entry(raw, detail="extra detail context")
            norm = gate_guidance.normalize_code(raw) or "UNKNOWN"
            self.assertEqual(entry["code"], norm)
            self.assertTrue(entry["model_line"].startswith(f"[TDQ:{norm}] "))
            self.assertLessEqual(len(entry["model_line"]), 160)
            self.assertIn(f"[TDQ:{norm}]", entry["user_card"])
            self.assertLessEqual(len(entry["user_card"]), 1200)
            for label in FOUR_PART_LABELS:
                self.assertIn(label, entry["user_card"])

        huge_entry = gate_guidance.build_reminder_entry("SEARCH", detail="word " * 300)
        self.assertLessEqual(len(huge_entry["model_line"]), 160)
        self.assertLessEqual(len(huge_entry["user_card"]), 1200)

    def test_format_user_markdown_empty_dedup_and_order(self):
        self.assertEqual(gate_guidance.format_user_markdown([]), "")
        entries = [
            gate_guidance.build_reminder_entry("TDQ:SEARCH", detail="rg foo"),
            gate_guidance.build_reminder_entry("[TDQ:DOC]", detail="state.py"),
            gate_guidance.build_reminder_entry("SEARCH", detail="duplicate"),
        ]
        md = gate_guidance.format_user_markdown(entries)
        self.assertLessEqual(len(md), 1200)
        self.assertEqual(md.count("[TDQ:SEARCH]"), 1)
        self.assertEqual(md.count("[TDQ:DOC]"), 1)
        self.assertLess(md.index("[TDQ:SEARCH]"), md.index("[TDQ:DOC]"))
        for label in FOUR_PART_LABELS:
            self.assertIn(label, md)

    def test_format_user_markdown_synthesizes_missing_card_and_caps_many_entries(self):
        raw_entries = [
            {"code": f"TDQ:{c}", "detail": f"src/{c.lower()}.py"}
            for c in gate_guidance.ALL_AGY_CODES
        ]
        md = gate_guidance.format_user_markdown(raw_entries)
        self.assertTrue(md)
        self.assertLessEqual(len(md), 1200)
        for label in FOUR_PART_LABELS:
            self.assertIn(label, md)
        lines = md.splitlines()
        self.assertTrue(all(line == line.rstrip() for line in lines))
        table_rows = [ln for ln in lines if ln.startswith("|")]
        self.assertGreater(len(table_rows), 2)
        for row in table_rows:
            self.assertTrue(row.endswith("|"), f"Truncated table row: {row!r}")
            self.assertEqual(row.count("`") % 2, 0, f"Unbalanced backticks in row: {row!r}")

    def test_format_model_summary_empty_dedup_and_200_cap(self):
        self.assertEqual(gate_guidance.format_model_summary([]), "")
        entries = [
            gate_guidance.build_reminder_entry("SEARCH"),
            gate_guidance.build_reminder_entry("DOC"),
            gate_guidance.build_reminder_entry("[TDQ:SEARCH]"),
        ]
        summary = gate_guidance.format_model_summary(entries)
        self.assertTrue(summary)
        self.assertLessEqual(len(summary), 200)
        self.assertEqual(summary.count("[TDQ:SEARCH]"), 1)
        self.assertIn("[TDQ:SEARCH]", summary)
        self.assertIn("[TDQ:DOC]", summary)

        oversized_pair = [
            gate_guidance.build_reminder_entry("LSP"),
            gate_guidance.build_reminder_entry("SUBAGENT"),
        ]
        pair_summary = gate_guidance.format_model_summary(oversized_pair)
        self.assertLessEqual(len(pair_summary), 200)
        self.assertIn("[TDQ:LSP]", pair_summary)
        self.assertIn("[TDQ:SUBAGENT]", pair_summary)

        all_entries = [gate_guidance.build_reminder_entry(c) for c in gate_guidance.ALL_AGY_CODES]
        capped = gate_guidance.format_model_summary(all_entries)
        self.assertTrue(capped)
        self.assertLessEqual(len(capped), 200)
        self.assertIn("[TDQ:APPROVE]", capped)

    def test_standalone_import_and_tdq_log_toggle(self):
        mod_path = ROOT / "tools" / "patches" / "gate_guidance.py"
        spec = importlib.util.spec_from_file_location("standalone_gate_guidance", mod_path)
        self.assertIsNotNone(spec)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        buf_on = io.StringIO()
        with patch.dict(os.environ, {"TDQ_LOG": "1"}), patch("sys.stderr", buf_on):
            module.build_reminder_entry("UNKNOWN_TEST_CODE")
        self.assertIn("gate_guidance:", buf_on.getvalue())

        buf_off = io.StringIO()
        with patch.dict(os.environ, {"TDQ_LOG": "0"}), patch("sys.stderr", buf_off):
            module.build_reminder_entry("UNKNOWN_TEST_CODE")
        self.assertEqual(buf_off.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
