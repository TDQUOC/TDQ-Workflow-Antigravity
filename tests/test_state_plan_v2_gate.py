#!/usr/bin/env python3
"""Tests for T1.4: tdq_state R15 pre-approval gate, multiline Cham targets, and tdq_eval RE_TICK."""
from __future__ import annotations

import contextlib
import importlib
import io
import os
import sys
import tempfile
import unittest
from unittest import mock

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
if TESTS_DIR not in sys.path:
    sys.path.insert(0, TESTS_DIR)

from helper import ROOT, read_state, run_state_cli

if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
SCRIPTS_DIR = os.path.join(ROOT, "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import tdq_eval
import tdq_state


def _valid_full_plan(slug: str = "2026-11-20-0200-valid") -> str:
    return (
        f"# PLAN — {slug}\n\n"
        "Ngày: 2026-11-20 · Lane: full\n\n"  # i18n-allow
        "## Ownership Map\n\n"
        "| Contract | Owner | Users |\n"
        "|---|---|---|\n"
        "| `run` | `src/app.py` | `T1.1` |\n\n"
        "## P1 — Core\n\n"
        "- [ ] **T1.1** (e10m) Implement runner — Test: `py -3 -m unittest tests/test_app.py`\n"
        "  - Req: `§2 #1` · Ngoài phạm vi: `GIỮ NGUYÊN` CLI flags\n"  # i18n-allow
        "  - Chạm: `src/app.py`\n"  # i18n-allow
        "  - Neo & Công cụ: `Edit` on `src/app.py` (`run()`)\n"  # i18n-allow
        "  - Trước → Sau: `run()` returns None -> returns status dict\n"  # i18n-allow
        "  - Tiêu chí chấp nhận (EARS): KHI call `run()`, HỆ THỐNG PHẢI return dict\n"  # i18n-allow
        "  - Logic cốt lõi:\n"  # i18n-allow
        "    1. Parse payload.\n"
        "    2. Return status dict.\n"
        "  - Ca góc hiểm & Assert:\n"  # i18n-allow
        "    - Ca hiểm: empty dict\n"  # i18n-allow
        "    - Tiêu chí: `assert run({})['ok'] is True`\n\n"  # i18n-allow
        "## Cụm song song\n\n"  # i18n-allow
        "Single cluster.\n\n"
        "## Definition of Done\n\n"
        "- [ ] Q1 App — `py -3 -m unittest tests/test_app.py`\n"
    )


def _valid_quick_plan() -> str:
    return (
        "# QUICK — Fix parser\n\n"
        "Ngày: 2026-11-20 · Lane: quick\n\n"  # i18n-allow
        "## P1 — Quick\n\n"
        "- [ ] **T1.1** (e5m) Patch parser — Test: `py -3 -m unittest tests/test_app.py`\n"
        "  - Chạm: `src/app.py`\n"  # i18n-allow
        "  - Vị trí neo: `src/app.py` (`parse()`)\n"  # i18n-allow
        "  - Trước → Sau: old parse -> new parse\n"  # i18n-allow
        "  - Logic: Parse input cleanly.\n"
        "  - Tiêu chí: `assert parse('a')['ok'] is True`\n\n"  # i18n-allow
        "## Definition of Done\n\n"
        "- [ ] Q1 Parser — `py -3 -m unittest tests/test_app.py`\n"
    )


def _write_file(base_dir: str, rel_path: str, content: str) -> str:
    full = os.path.join(base_dir, rel_path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as fh:
        fh.write(content)
    return full


class TestExtractPlanTargets(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cwd = self.tmp.name

    def test_single_and_multiline_cham_skips_fences_and_resets_cleanly(self):
        plan_rel = "docs/tdq/plan/2026-11-20-0010-targets.md"
        plan_md = (
            "# PLAN — Targets\n\n"
            "```markdown\n"
            "- Chạm: `ignored/in_backtick_fence.py`\n"  # i18n-allow
            "```\n\n"
            "- [ ] **T1.1** Single line — Test: `pytest`\n"
            "  - Chạm: `scripts\\a.py`, `scripts/b.py`, ``\n"  # i18n-allow
            "  - Logic: keep working.\n\n"
            "- [ ] **T1.2** Multiline — Test: `pytest`\n"
            "  - Chạm: `scripts/b.py`\n"  # i18n-allow
            "    - `skills/tdq-plan/SKILL.md`\n"
            "    - `tests\\test_foo.py`\n"
            "  - Tham chiếu: `scripts/ignored_ref.py`\n"  # i18n-allow
            "    - `scripts/ignored_nested_ref.py`\n"
            "  - Logic:\n"
            "    ```python\n"
            "    - Chạm: `ignored/nested_fence.py`\n"  # i18n-allow
            "    ```\n\n"
            "- [ ] **T1.3** Top-level and tilde fence — Test: `pytest`\n"
            "Chạm:\n"  # i18n-allow
            "  - `docs/top.md`\n"
            "  ~~~\n"
            "  - `ignored/in_tilde_fence.py`\n"
            "  ~~~\n"
            "  - `ignored/after_tilde_fence.py`\n\n"
            "Logic: `ignored/after_blank.py`\n"
        )
        _write_file(self.cwd, plan_rel, plan_md)
        targets = tdq_state._extract_plan_targets(self.cwd, {"plan_file": plan_rel})
        self.assertEqual(
            targets,
            [
                "scripts/a.py",
                "scripts/b.py",
                "skills/tdq-plan/SKILL.md",
                "tests/test_foo.py",
                "docs/top.md",
            ],
        )

    def test_missing_or_empty_state_returns_empty_list(self):
        self.assertEqual(tdq_state._extract_plan_targets(self.cwd, {}), [])
        self.assertEqual(
            tdq_state._extract_plan_targets(self.cwd, {"plan_file": "docs/tdq/plan/missing.md"}),
            [],
        )


class TestSetPlanFileR15Gate(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cwd = self.tmp.name

    def test_set_plan_file_blocks_bad_post_cutoff_plan_and_keeps_state(self):
        slug = "2026-11-20-0100-bad-plan"
        rc, _, err = run_state_cli(self.cwd, "init", slug, "full", "--bo-qua-lsp", "unit test")
        self.assertEqual(rc, 0, err)
        plan_rel = f"docs/tdq/plan/{slug}.md"
        _write_file(
            self.cwd,
            plan_rel,
            "# PLAN — Bad\n\nNgày: 2026-11-20 · Lane: full\n\n"  # i18n-allow
            "- [ ] **T1.1** (e5m) Missing fields — Test: `pytest`\n"
            "  - Chạm: `src/app.py`\n"  # i18n-allow
            "  - Logic: TBD\n",
        )
        rc, _, err = run_state_cli(self.cwd, "set", f"plan_file={plan_rel}")
        self.assertEqual(rc, 1, err)
        self.assertIn("R15", err)
        self.assertIn("TBD", err.upper())
        self.assertIsNone(read_state(self.cwd)["plan_file"])

    def test_set_plan_file_null_and_valid_and_legacy_succeed(self):
        slug = "2026-11-20-0200-valid"
        rc, _, err = run_state_cli(self.cwd, "init", slug, "full", "--bo-qua-lsp", "unit test")
        self.assertEqual(rc, 0, err)
        plan_rel = f"docs/tdq/plan/{slug}.md"
        _write_file(self.cwd, plan_rel, _valid_full_plan(slug))

        rc, _, err = run_state_cli(self.cwd, "set", f"plan_file={plan_rel}")
        self.assertEqual(rc, 0, err)
        self.assertEqual(read_state(self.cwd)["plan_file"], plan_rel)

        rc, _, err = run_state_cli(self.cwd, "set", "plan_file=null")
        self.assertEqual(rc, 0, err)
        self.assertIsNone(read_state(self.cwd)["plan_file"])

        old_slug = "2026-08-19-0900-legacy"
        rc, _, err = run_state_cli(self.cwd, "init", old_slug, "full", "--bo-qua-lsp", "unit test")
        self.assertEqual(rc, 0, err)
        old_rel = f"docs/tdq/plan/{old_slug}.md"
        _write_file(
            self.cwd,
            old_rel,
            "# PLAN — Legacy\n\nNgày: 2026-08-19 · Lane: full\n\n"  # i18n-allow
            "- [ ] **T1.1** (e5m) Legacy without logic — Test: `pytest`\n"
            "  - Chạm: `src/app.py`\n",  # i18n-allow
        )
        rc, _, err = run_state_cli(self.cwd, "set", f"plan_file={old_rel}")
        self.assertEqual(rc, 0, err)
        self.assertEqual(read_state(self.cwd)["plan_file"], old_rel)


class TestApproveR15Gate(unittest.TestCase):
    ISO_RE = r"\[\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}\]"

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cwd = self.tmp.name

    def _setup_full_with_spec(self, slug: str) -> str:
        rc, _, err = run_state_cli(self.cwd, "init", slug, "full", "--bo-qua-lsp", "unit test")
        self.assertEqual(rc, 0, err)
        spec_rel = f"docs/tdq/spec/{slug}.md"
        _write_file(self.cwd, spec_rel, "# Spec\n\n## 1. Goal\n\nDemo.\n")
        rc, _, err = run_state_cli(self.cwd, "set", "phase=spec", f"spec_file={spec_rel}")
        self.assertEqual(rc, 0, err)
        rc, _, err = run_state_cli(
            self.cwd, "approve", "spec", "--by", "approve spec", "--bo-qua-do", "test", "--bo-qua-archify", "test"
        )
        self.assertEqual(rc, 0, err)
        return f"docs/tdq/plan/{slug}.md"

    def test_approve_plan_blocks_tampered_plan_then_allows_valid(self):
        slug = "2026-11-20-0300-plan-gate"
        plan_rel = self._setup_full_with_spec(slug)
        plan_abs = _write_file(self.cwd, plan_rel, _valid_full_plan(slug))
        rc, _, err = run_state_cli(self.cwd, "set", "phase=plan", f"plan_file={plan_rel}")
        self.assertEqual(rc, 0, err)

        # Tamper plan after registration to ensure approve plan also runs R15 gate.
        with open(plan_abs, "w", encoding="utf-8") as fh:
            fh.write(_valid_full_plan(slug).replace("assert run({})['ok'] is True", "assert True"))
        rc, _, err = run_state_cli(
            self.cwd, "approve", "plan", "--mode", "main", "--by", "approve plan", "--bo-qua-archify", "test"
        )
        self.assertEqual(rc, 1, err)
        self.assertIn("R15", err)
        self.assertIn("ANTI-2", err)
        self.assertRegex(err, self.ISO_RE)
        self.assertFalse(read_state(self.cwd)["plan_approved"])

        with open(plan_abs, "w", encoding="utf-8") as fh:
            fh.write(_valid_full_plan(slug))
        rc, _, err = run_state_cli(
            self.cwd, "approve", "plan", "--mode", "main", "--by", "approve plan", "--bo-qua-archify", "test"
        )
        self.assertEqual(rc, 0, err)
        self.assertTrue(read_state(self.cwd)["plan_approved"])

    def test_approve_quick_without_plan_file_fails_open_exit_0(self):
        slug = "2026-11-20-0400-quick-nofile"
        rc, _, err = run_state_cli(self.cwd, "init", slug, "quick", "--bo-qua-lsp", "unit test")
        self.assertEqual(rc, 0, err)
        rc, _, err = run_state_cli(
            self.cwd, "approve", "quick", "--by", "duyet nhanh", "--bo-qua-archify", "test"  # i18n-allow
        )
        self.assertEqual(rc, 0, err)
        self.assertTrue(read_state(self.cwd)["quick_approved"])

    def test_approve_quick_with_invalid_plan_blocked_exit_1(self):
        bad_cases = {
            "missing_compact": (
                "# QUICK — Missing\n\nNgày: 2026-11-20 · Lane: quick\n\n"  # i18n-allow
                "- [ ] **T1.1** (e5m) Patch — Test: `pytest`\n"
                "  - Chạm: `src/app.py`\n"  # i18n-allow
            ),
            "tbd_placeholder": _valid_quick_plan().replace("Parse input cleanly.", "TBD"),
            "anti2_assert_true": _valid_quick_plan().replace("assert parse('a')['ok'] is True", "assert True"),
        }
        for name, content in bad_cases.items():
            with self.subTest(case=name):
                sub_dir = os.path.join(self.cwd, name)
                os.makedirs(sub_dir, exist_ok=True)
                slug = f"2026-11-20-0500-{name.replace('_', '-')}"
                rc, _, err = run_state_cli(sub_dir, "init", slug, "quick", "--bo-qua-lsp", "unit test")
                self.assertEqual(rc, 0, err)
                _write_file(sub_dir, f"docs/tdq/plan/{slug}.md", content)
                rc, _, err = run_state_cli(
                    sub_dir, "approve", "quick", "--by", "duyet nhanh", "--bo-qua-archify", "test"  # i18n-allow
                )
                self.assertEqual(rc, 1, err)
                self.assertIn("R15", err)
                self.assertFalse(read_state(sub_dir)["quick_approved"])

    def test_approve_quick_with_valid_r15_compact_succeeds(self):
        slug = "2026-11-20-0600-quick-valid"
        rc, _, err = run_state_cli(self.cwd, "init", slug, "quick", "--bo-qua-lsp", "unit test")
        self.assertEqual(rc, 0, err)
        _write_file(self.cwd, f"docs/tdq/plan/{slug}.md", _valid_quick_plan())
        rc, _, err = run_state_cli(
            self.cwd, "approve", "quick", "--by", "duyet nhanh", "--bo-qua-archify", "test"  # i18n-allow
        )
        self.assertEqual(rc, 0, err)
        self.assertTrue(read_state(self.cwd)["quick_approved"])

    def test_legacy_pre_cutoff_minimal_plan_passes_set_and_approve_plan(self):
        slug = "2026-08-19-0900-legacy-eval"
        plan_rel = self._setup_full_with_spec(slug)
        _write_file(
            self.cwd,
            plan_rel,
            "# PLAN — Legacy Eval\n\nNgày: 2026-08-19 · Lane: full\n\n"  # i18n-allow
            "- [ ] **T1.1** (e5m) Minimal task — Test: `pytest`\n"
            "  - Chạm: `src/app.py`\n",  # i18n-allow
        )
        rc, _, err = run_state_cli(self.cwd, "set", "phase=plan", f"plan_file={plan_rel}")
        self.assertEqual(rc, 0, err)
        rc, _, err = run_state_cli(
            self.cwd, "approve", "plan", "--mode", "main", "--by", "approve plan"
        )
        self.assertEqual(rc, 0, err)
        self.assertTrue(read_state(self.cwd)["plan_approved"])

    def test_tdq_log_0_mutes_warning_but_still_blocks_exit_1(self):
        slug = "2026-11-20-0700-log-mute"
        rc, _, err = run_state_cli(self.cwd, "init", slug, "full", "--bo-qua-lsp", "unit test")
        self.assertEqual(rc, 0, err)
        plan_rel = f"docs/tdq/plan/{slug}.md"
        _write_file(
            self.cwd,
            plan_rel,
            "# PLAN — Bad\n\nNgày: 2026-11-20 · Lane: full\n\n"  # i18n-allow
            "- [ ] **T1.1** (e5m) Bad — Test: `pytest`\n  - Chạm: `src/app.py`\n  - Logic: TBD\n",  # i18n-allow
        )
        old_log = os.environ.get("TDQ_LOG")
        os.environ["TDQ_LOG"] = "0"
        try:
            rc, _, err = run_state_cli(self.cwd, "set", f"plan_file={plan_rel}")
        finally:
            if old_log is None:
                os.environ.pop("TDQ_LOG", None)
            else:
                os.environ["TDQ_LOG"] = old_log
        self.assertEqual(rc, 1)
        self.assertIn("R15", err)
        self.assertNotRegex(err, self.ISO_RE)

    def test_package_import_and_missing_doc_lint_fail_open(self):
        pkg_mod = importlib.import_module("scripts.tdq_state")
        self.assertTrue(hasattr(pkg_mod, "_kiem_r15_plan"))
        slug = "2026-11-20-0800-pkg"
        plan_abs = _write_file(
            self.cwd,
            f"docs/tdq/plan/{slug}.md",
            _valid_full_plan(slug).replace("assert run({})['ok'] is True", "assert True"),
        )
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf), self.assertRaises(SystemExit) as ctx:
            pkg_mod._kiem_r15_plan(self.cwd, plan_abs, "full")
        self.assertEqual(ctx.exception.code, 1)
        self.assertIn("R15", buf.getvalue())
        self.assertIn("ANTI-2", buf.getvalue())
        with mock.patch.object(pkg_mod, "_import_doc_lint", return_value=None):
            pkg_mod._kiem_r15_plan(self.cwd, plan_abs, "full")


class TestEvalReTick(unittest.TestCase):
    def test_re_tick_matches_all_task_marks_and_ids(self):
        samples = [
            ("- [ ] **T1** first", (" ", "T1")),
            ("- [>] **T2.1a** variant", (">", "T2.1a")),
            ("- [~] **QC1.1** qc task", ("~", "QC1.1")),
            ("- [x] **T1.4** done", ("x", "T1.4")),
            ("- [ ] **QC2** bare qc", (" ", "QC2")),
        ]
        for line, expected in samples:
            with self.subTest(line=line):
                m = tdq_eval.RE_TICK.search(line)
                self.assertIsNotNone(m, f"RE_TICK failed to match {line!r}")
                self.assertEqual((m.group(1), m.group(2)), expected)

    def test_chuyen_tick_tracks_qc_and_variant_ids(self):
        phien = {
            "goi": [
                {
                    "ten": "Edit",
                    "file": "docs/tdq/plan/p.md",
                    "input": {"new_string": "- [~] **QC1.1** fix"},
                },
                {
                    "ten": "Edit",
                    "file": "docs/tdq/plan/p.md",
                    "input": {"new_string": "- [x] **QC1.1** fix"},
                },
                {
                    "ten": "Edit",
                    "file": "docs/tdq/plan/p.md",
                    "input": {"new_string": "- [>] **T2.1a** split"},
                },
            ]
        }
        self.assertEqual(
            tdq_eval._chuyen_tick(phien),
            [(0, "QC1.1", "~"), (1, "QC1.1", "x"), (2, "T2.1a", ">")],
        )


if __name__ == "__main__":
    unittest.main()
