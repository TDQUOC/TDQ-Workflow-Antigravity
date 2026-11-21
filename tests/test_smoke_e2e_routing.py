"""Tests for smoke-e2e routing, CLI execution, markers, fail-fast, and logging."""
import json
import os
import re
import shutil
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

from helper import ROOT

sys.path.insert(0, os.path.join(ROOT, "scripts"))
import tdq_test

SCRIPT = os.path.join(ROOT, "scripts", "tdq_test.py")
LOG_LINE_RE = re.compile(r"^\[\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d", re.MULTILINE)


def _write(repo, rel, content):
    target = Path(repo, *rel.split("/"))
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return target


def _run_smoke_cli(repo, *args, log=True):
    env = dict(os.environ)
    env["TDQ_LOG"] = "1" if log else "0"
    env["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run(
        [sys.executable, SCRIPT, "smoke-e2e", "--repo", str(repo), *args],
        check=False, capture_output=True, text=True, encoding="utf-8", env=env, timeout=120,
    )


def _ledger_rows(repo):
    ledger = Path(repo, "docs/tdq/.tdq-test.jsonl")
    if not ledger.is_file():
        return []
    return [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines() if line.strip()]


class SmokeRoutingUnitTests(unittest.TestCase):
    def test_smoke_routes_define_all_core_areas(self):
        prefixes = {prefix for route in tdq_test.SMOKE_ROUTES for prefix in route["prefixes"]}
        for expected in (
            "agents/", "tools/patches/", "hooks/", "scripts/tdq_test",
            "scripts/tdq_state", "scripts/doc_lint", "scripts/tdq_timing", "skills/",
        ):
            self.assertTrue(
                any(expected.startswith(prefix) or prefix.startswith(expected) for prefix in prefixes),
                f"Missing route for {expected}",
            )

    def test_select_smoke_targets_maps_changed_paths_and_fallback(self):
        agents_plan = tdq_test.select_smoke_targets(["agents/tdq-explorer.md", "tools/patches/skills_and_agents.py"])
        self.assertFalse(agents_plan["fallback"])
        self.assertIn("tests/test_agent_frontmatter.py", agents_plan["modules"])
        self.assertIn("tests/test_agy_plugin_validate.py", agents_plan["modules"])
        self.assertIn("tests/test_v01030_regression_smoke.py", agents_plan["modules"])

        hooks_plan = tdq_test.select_smoke_targets(["hooks/scripts/stop_gate.py"])
        self.assertFalse(hooks_plan["fallback"])
        self.assertIn("tests/test_rust_dispatch_parity.py", hooks_plan["modules"])
        self.assertIn("tests/test_bash_gate.py", hooks_plan["modules"])

        state_plan = tdq_test.select_smoke_targets(["scripts/tdq_state.py"])
        self.assertFalse(state_plan["fallback"])
        self.assertIn("tests/test_state_muc_qc.py", state_plan["modules"])

        lint_plan = tdq_test.select_smoke_targets(["scripts/doc_lint.py"])
        self.assertFalse(lint_plan["fallback"])
        self.assertIn("tests/test_doc_lint_r15.py", lint_plan["modules"])

        timing_plan = tdq_test.select_smoke_targets(["scripts/tdq_timing.py"])
        self.assertFalse(timing_plan["fallback"])
        self.assertIn("tests/test_timing.py", timing_plan["modules"])

        skills_plan = tdq_test.select_smoke_targets(["skills/tdq-build/SKILL.md"])
        self.assertFalse(skills_plan["fallback"])
        self.assertIn("tests/test_token_budget.py", skills_plan["modules"])

        empty_plan = tdq_test.select_smoke_targets([])
        self.assertTrue(empty_plan["fallback"])
        self.assertEqual(empty_plan["marker"], "smoke")
        self.assertTrue(empty_plan["modules"])

        unknown_plan = tdq_test.select_smoke_targets(["README.md"])
        self.assertTrue(unknown_plan["fallback"])
        self.assertEqual(unknown_plan["marker"], "smoke")


class SmokeE2EExecutionTests(unittest.TestCase):
    def setUp(self):
        import tempfile
        temp = tempfile.TemporaryDirectory(prefix="tdq-smoke-e2e-")
        self.addCleanup(temp.cleanup)
        self.repo = Path(temp.name)
        _write(self.repo, "docs/tdq/state.json", json.dumps({
            "active_request": "smoke-req", "phase": "implement", "nhanh_goc": "main",
        }))

    def test_plan_only_prints_routes_without_running_or_writing_ledger(self):
        _write(self.repo, "tests/test_agent_frontmatter.py", "def test_ok():\n    assert True\n")
        proc = _run_smoke_cli(self.repo, "--files", "agents/tdq-explorer.md", "--plan-only")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(len(proc.stdout.strip().splitlines()), 1)
        self.assertIn("routes=agents", proc.stdout)
        self.assertIn("test_agent_frontmatter.py", proc.stdout)
        self.assertTrue(LOG_LINE_RE.search(proc.stderr), proc.stderr)
        self.assertFalse((self.repo / "docs/tdq/.tdq-test.jsonl").exists())
        self.assertFalse((self.repo / "docs/tdq/cache/test-runs").exists())

    def test_smoke_e2e_runs_marked_smoke_tests_skips_unmarked_and_toggles_log(self):
        _write(
            self.repo,
            "tests/test_agent_frontmatter.py",
            "import pytest\n\n"
            "@pytest.mark.smoke\n"
            "def test_fast_smoke():\n    assert True\n\n"
            "def test_unmarked_slow():\n    assert False, 'unmarked test must not run'\n",
        )
        # No pytest.ini in self.repo -> runner must register smoke/e2e markers via -o markers
        loud = _run_smoke_cli(self.repo, "--files", "agents/tdq-explorer.md", log=True)
        self.assertEqual(loud.returncode, 0, loud.stdout + loud.stderr)
        self.assertIn("[TDQ:TEST] PASS", loud.stdout)
        self.assertIn("tests=1", loud.stdout)
        self.assertTrue(LOG_LINE_RE.search(loud.stderr), loud.stderr)
        rows = _ledger_rows(self.repo)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["kind"], "smoke-e2e")
        self.assertEqual(rows[0]["tests_run"], 1)

        quiet = _run_smoke_cli(self.repo, "--files", "agents/tdq-explorer.md", log=False)
        self.assertEqual(quiet.returncode, 0, quiet.stdout + quiet.stderr)
        self.assertIsNone(LOG_LINE_RE.search(quiet.stderr), quiet.stderr)

    @unittest.skipUnless(shutil.which("git"), "git not installed")
    def test_empty_git_diff_with_changed_runs_smoke_fallback_and_never_skips_as_pass(self):
        _write(self.repo, ".gitignore", "__pycache__/\ndocs/tdq/state.json\ndocs/tdq/cache/\n")
        _write(
            self.repo,
            "pytest.ini",
            "[pytest]\nmarkers =\n    smoke: smoke tests\n    e2e: e2e tests\n    slow: slow tests\n",
        )
        _write(
            self.repo,
            "tests/test_core_smoke.py",
            "import pytest\n\n@pytest.mark.smoke\ndef test_smoke_core():\n    assert True\n",
        )
        _write(
            self.repo,
            "tests/test_non_smoke.py",
            "def test_other_broken():\n    assert False, 'unmarked non-smoke must not execute'\n",
        )

        def git(*args):
            subprocess.run(["git", "-C", str(self.repo), *args], check=True, capture_output=True)

        git("init", "-q")
        git("symbolic-ref", "HEAD", "refs/heads/main")
        git("config", "user.email", "t@example.com")
        git("config", "user.name", "t")
        git("config", "core.autocrlf", "false")
        git("add", "-A")
        git("commit", "-q", "-m", "base")

        proc = _run_smoke_cli(self.repo, "--changed")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("[TDQ:TEST] PASS", proc.stdout)
        self.assertIn("tests=1", proc.stdout)
        rows = _ledger_rows(self.repo)
        self.assertEqual(rows[-1]["tests_run"], 1)
        self.assertEqual(rows[-1]["status"], "PASS")

    def test_empty_tests_dir_does_not_silently_pass(self):
        (self.repo / "tests").mkdir(exist_ok=True)
        proc = _run_smoke_cli(self.repo, "--files", "agents/tdq-explorer.md")
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("[TDQ:TEST] INCOMPLETE", proc.stdout)
        self.assertNotIn("[TDQ:TEST] PASS", proc.stdout)

    def test_fail_fast_stops_on_first_failure(self):
        _write(
            self.repo,
            "pytest.ini",
            "[pytest]\nmarkers =\n    smoke: smoke tests\n    e2e: e2e tests\n",
        )
        _write(
            self.repo,
            "tests/test_agent_frontmatter.py",
            "import pytest\n\n"
            "pytestmark = pytest.mark.smoke\n\n"
            "def test_first_fails():\n    assert False, 'boom 1'\n\n"
            "def test_second_never_runs():\n    assert False, 'boom 2'\n",
        )
        proc = _run_smoke_cli(self.repo, "--files", "agents/tdq-explorer.md", "--fail-fast")
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("[TDQ:TEST] FAIL", proc.stdout)
        self.assertIn("tests=1", proc.stdout)

    def test_smoke_e2e_rejects_workers_auto_combined_with_parallel(self):
        _write(self.repo, "tests/test_agent_frontmatter.py", "def test_ok():\n    assert True\n")
        proc = _run_smoke_cli(self.repo, "--files", "agents/tdq-explorer.md", "--workers", "auto", "--parallel")
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertIn("not allowed with argument", proc.stderr)

    def test_smoke_e2e_accepts_workers_auto(self):
        _write(self.repo, "tests/test_agent_frontmatter.py", "def test_ok():\n    assert True\n")
        with mock.patch.object(tdq_test.os, "cpu_count", return_value=8):
            self.assertEqual(tdq_test._worker_count("auto", False), 6)
        proc = _run_smoke_cli(self.repo, "--files", "agents/tdq-explorer.md", "--workers", "auto")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("[TDQ:TEST] PASS", proc.stdout)

    def test_string_literal_marker_mention_does_not_trigger_empty_m_filter(self):
        _write(
            self.repo,
            "tests/test_agent_frontmatter.py",
            'FIXTURE = "@pytest.mark.smoke"\n\ndef test_unmarked_real():\n    assert FIXTURE\n',
        )
        proc = _run_smoke_cli(self.repo, "--files", "agents/tdq-explorer.md")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("[TDQ:TEST] PASS", proc.stdout)
        self.assertIn("tests=1", proc.stdout)


if __name__ == "__main__":
    unittest.main()
