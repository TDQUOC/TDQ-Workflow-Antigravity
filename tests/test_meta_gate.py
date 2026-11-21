"""Tests for scripts/tdq_meta_gate.py (Auto Meta-Gate 1-line summary & TDQ_LOG)."""
import datetime
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import pytest

from helper import ROOT

pytestmark = pytest.mark.smoke

SCRIPTS_DIR = os.path.join(ROOT, "scripts")
ISO_LOG_RE = re.compile(r"^\[(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[^\]]*)\] \S")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)


class MetaGateTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="tdq-meta-gate-")
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name)

    def _write(self, rel: str, content: str) -> Path:
        path = self.repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def _run_script(self, script_name: str, *args: str, env: dict[str, str] | None = None):
        full_env = dict(os.environ)
        full_env.pop("TDQ_LOG", None)
        full_env["TDQ_KHONG_CHAM_MAY"] = "1"
        full_env["TDQ_KHOI_TAO_NEN"] = "0"
        if env:
            full_env.update(env)
        return subprocess.run(
            [sys.executable, os.path.join(SCRIPTS_DIR, script_name), *args],
            check=False,
            cwd=str(self.repo),
            env=full_env,
            capture_output=True,
            encoding="utf-8",
            text=True,
            timeout=30,
        )

    def _run(self, *args: str, env: dict[str, str] | None = None):
        return self._run_script("tdq_meta_gate.py", *args, env=env)

    def _assert_log_lines(self, proc, expected_token: str, *, require_tz: bool = True) -> None:
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertTrue(proc.stderr, "TDQ_LOG enabled/default must emit stderr logs")
        for line in proc.stderr.splitlines():
            match = ISO_LOG_RE.match(line)
            self.assertIsNotNone(match, line)
            stamp = datetime.datetime.fromisoformat(match.group(1))
            if require_tz:
                self.assertIsNotNone(stamp.tzinfo, line)
        self.assertIn(expected_token, proc.stderr)
        self.assertNotRegex(proc.stdout, r"(?m)^\[\d{4}-\d{2}-\d{2}T")

    def _assert_tdq_log_parity(
        self,
        script_name: str,
        args: tuple[str, ...],
        expected_token: str,
        *,
        require_tz: bool = True,
        extra_env: dict[str, str] | None = None,
    ) -> None:
        base_env = dict(extra_env or {})
        default_proc = self._run_script(script_name, *args, env=base_env)
        self._assert_log_lines(default_proc, expected_token, require_tz=require_tz)

        loud_proc = self._run_script(script_name, *args, env={**base_env, "TDQ_LOG": "1"})
        self._assert_log_lines(loud_proc, expected_token, require_tz=require_tz)

        quiet_proc = self._run_script(script_name, *args, env={**base_env, "TDQ_LOG": "0"})
        self.assertEqual(quiet_proc.returncode, 0, quiet_proc.stdout + quiet_proc.stderr)
        self.assertEqual(
            quiet_proc.stderr, "", f"TDQ_LOG=0 must silence stderr: {quiet_proc.stderr!r}"
        )
        self.assertNotRegex(quiet_proc.stdout, r"(?m)^\[\d{4}-\d{2}-\d{2}T")

    def _write_clean_skill(self, rel: str = "skills/demo/SKILL.md") -> Path:
        content = (
            "---\nname: demo\n---\n\n# Demo Skill\n\n"
            "## Steps\n\n1. Run check.\n\n"
            "Done when: check passes.\nNext step: continue.\n"
        )
        return self._write(rel, content)

    def _write_token_lock(self, rel: str, token_count: int = 50) -> None:
        target = self.repo / rel
        raw = target.read_text(encoding="utf-8").replace("\r\n", "\n")
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        lock = {rel.replace("\\", "/"): {"token": token_count, "sha256": digest}}
        self._write(
            "docs/tdq/token-budget.json",
            json.dumps(lock, indent=2, sort_keys=True) + "\n",
        )

    def test_pass_prints_exact_one_line_and_exits_zero(self):
        doc = self._write("docs/tdq/brief/note.md", "# Brief\n\nShort summary.\n")
        proc = self._run("--repo", str(self.repo), "--files", str(doc))
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        lines = proc.stdout.strip().splitlines()
        self.assertEqual(len(lines), 1, proc.stdout)
        self.assertRegex(lines[0], r"^Auto Meta-Gate: PASS \(\d+/\d+ checks, \d+\.\d{2}s\)$")

    def test_fail_closed_on_doc_lint_violation(self):
        bad_skill = self._write(
            "skills/demo/SKILL.md",
            "---\nname: demo\n---\n\n# Demo\n\n## Steps\n\n1. First.\n3. Skipped two.\n",
        )
        proc = self._run("--repo", str(self.repo), "--files", str(bad_skill))
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertRegex(
            proc.stdout.splitlines()[0],
            r"^Auto Meta-Gate: FAIL \(\d+/\d+ checks, \d+\.\d{2}s\)$",
        )
        self.assertIn("[R1]", proc.stdout)

    def test_fail_closed_on_i18n_violation(self):
        self._write_clean_skill("skills/demo/SKILL.md")
        bad_py = self._write(
            "scripts/demo.py", "# note: ghi ch\u00fa ti\u1ebfng Vi\u1ec7t\nVALUE = 1\n"
        )
        proc = self._run("--repo", str(self.repo), "--files", str(bad_py))
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("Auto Meta-Gate: FAIL", proc.stdout)
        self.assertIn("demo.py:1", proc.stdout)

    def test_token_budget_triggered_for_skills_and_all(self):
        ref = self._write("skills/tdq-demo/references/guide.md", "# Guide\n\nEnglish text.\n")
        self._write_token_lock("skills/tdq-demo/references/guide.md", token_count=20)
        ok_proc = self._run("--repo", str(self.repo), "--files", str(ref))
        self.assertEqual(ok_proc.returncode, 0, ok_proc.stdout + ok_proc.stderr)

        ref.write_text("# Guide\n\nChanged text making lock stale.\n", encoding="utf-8")
        stale_proc = self._run("--repo", str(self.repo), "--all")
        self.assertEqual(stale_proc.returncode, 1, stale_proc.stdout + stale_proc.stderr)
        self.assertIn("Auto Meta-Gate: FAIL", stale_proc.stdout)
        self.assertIn("sha256", stale_proc.stdout)

    def test_git_msg_file_blocks_co_authored_by_and_allows_clean(self):
        doc = self._write("docs/tdq/brief/note.md", "# Brief\n\nClean content.\n")
        bad_msg = self._write(
            "COMMIT_EDITMSG",
            "feat(meta): add gate\n\nCo-Authored-By: Claude <noreply@anthropic.com>\n",
        )
        fail_proc = self._run(
            "--repo", str(self.repo), "--files", str(doc), "--git-msg-file", str(bad_msg)
        )
        self.assertEqual(fail_proc.returncode, 1, fail_proc.stdout + fail_proc.stderr)
        self.assertIn("Auto Meta-Gate: FAIL", fail_proc.stdout)
        self.assertIn("Co-Authored-By", fail_proc.stdout)

        clean_msg = self._write("COMMIT_EDITMSG", "feat(meta): add gate\n")
        pass_proc = self._run(
            "--repo", str(self.repo), "--files", str(doc), "--git-msg-file", str(clean_msg)
        )
        self.assertEqual(pass_proc.returncode, 0, pass_proc.stdout + pass_proc.stderr)
        self.assertEqual(len(pass_proc.stdout.strip().splitlines()), 1)

        missing_proc = self._run(
            "--repo", str(self.repo), "--files", str(doc),
            "--git-msg-file", str(self.repo / "NO_SUCH_MSG"),
        )
        self.assertEqual(missing_proc.returncode, 1, missing_proc.stdout + missing_proc.stderr)
        self.assertIn("Auto Meta-Gate: FAIL", missing_proc.stdout)

    def test_check_cli_rejects_bad_flag_in_bug_board(self):
        self._write(
            "scripts/sample_cli.py",
            "import argparse\nap = argparse.ArgumentParser()\nap.add_argument('--files')\n",
        )
        self._write(
            "docs/tdq/bugs/BUG_BOARD.md",
            "# Bug Board\n\n- Repro: `py -3 scripts/sample_cli.py --khong-ton-tai`\n",
        )
        proc = self._run("--repo", str(self.repo), "--check-cli")
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("Auto Meta-Gate: FAIL", proc.stdout)
        self.assertIn("--khong-ton-tai", proc.stdout)

    def test_missing_explicit_file_fails_closed(self):
        proc = self._run("--repo", str(self.repo), "--files", "does_not_exist.md")
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("Auto Meta-Gate: FAIL", proc.stdout)
        self.assertIn("does_not_exist.md", proc.stdout)

    def test_tdq_log_on_default_and_off_clean_stderr(self):
        doc = self._write("docs/tdq/brief/note.md", "# Brief\n\nLog check.\n")
        self._assert_tdq_log_parity(
            "tdq_meta_gate.py",
            ("--repo", str(self.repo), "--files", str(doc)),
            "tdq_meta_gate:",
        )

    def test_tdq_test_cli_tdq_log_parity(self):
        self._write(
            "docs/tdq/state.json",
            json.dumps({
                "active_request": "2026-11-21-0000-log-parity",
                "phase": "implement",
                "nhanh_goc": "main",
            }),
        )
        self._write("tests/test_smoke_stub.py", "def test_ok():\n    assert True\n")
        self._write("docs/tdq/brief/note.md", "# Brief\n\nLog check.\n")
        iso_env = {"TDQ_PROJECT_DIR": str(self.repo)}
        self._assert_tdq_log_parity(
            "tdq_test.py",
            (
                "smoke-e2e",
                "--repo",
                str(self.repo),
                "--files",
                "agents/tdq-explorer.md",
                "--plan-only",
            ),
            "tdq_test: smoke-e2e plan",
            extra_env=iso_env,
        )
        self._assert_tdq_log_parity(
            "tdq_test.py",
            (
                "vung-cham",
                "--repo",
                str(self.repo),
                "--silent",
                "--khong-ep-tron-bo",
                "--files",
                "docs/tdq/brief/note.md",
            ),
            "tdq_test: vung-cham",
            extra_env=iso_env,
        )

    def test_tdq_timing_show_tdq_log_parity(self):
        home_dir = self.repo / ".home"
        home_dir.mkdir(parents=True, exist_ok=True)
        started = "2026-11-21T10:00:00+00:00"
        now = "2026-11-21T10:00:20+00:00"
        self._write(
            "docs/tdq/state.json",
            json.dumps({
                "active_request": "2026-11-21-0000-log-parity",
                "lane": "full",
                "phase": "implement",
                "started_at": started,
                "phase_history": [{"phase": "analyze", "at": started}],
            }),
        )
        iso_env = {
            "TDQ_PROJECT_DIR": str(self.repo),
            "HOME": str(home_dir),
            "USERPROFILE": str(home_dir),
        }
        self._assert_tdq_log_parity(
            "tdq_timing.py",
            ("show", "--project", str(self.repo), "--now", now),
            "timing: hid",
            extra_env=iso_env,
        )

    def test_doc_lint_tdq_log_parity(self):
        doc = self._write("docs/tdq/brief/note.md", "# Brief\n\nClean note.\n")
        self._assert_tdq_log_parity(
            "doc_lint.py",
            (str(doc),),
            "doc_lint:",
            require_tz=False,
        )

    def test_git_auto_discovery_without_files(self):
        subprocess.run(["git", "init"], cwd=str(self.repo), check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "tdq-test"], cwd=str(self.repo), check=True)
        subprocess.run(["git", "config", "user.email", "tdq@test.local"], cwd=str(self.repo), check=True)
        self._write("docs/tdq/brief/init.md", "# Brief\n\nClean init.\n")
        subprocess.run(["git", "add", "."], cwd=str(self.repo), check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "chore: init"], cwd=str(self.repo), check=True, capture_output=True)

        clean_proc = self._run("--repo", str(self.repo))
        self.assertEqual(clean_proc.returncode, 0, clean_proc.stdout + clean_proc.stderr)

        self._write("scripts/dirty.py", "# note: c\u00f2n ti\u1ebfng Vi\u1ec7t\nX = 1\n")
        dirty_proc = self._run("--repo", str(self.repo))
        self.assertEqual(dirty_proc.returncode, 1, dirty_proc.stdout + dirty_proc.stderr)
        self.assertIn("dirty.py:1", dirty_proc.stdout)

    def test_run_meta_gate_python_api(self):
        import tdq_meta_gate

        doc = self._write("docs/tdq/brief/api.md", "# Brief\n\nAPI check.\n")
        rc = tdq_meta_gate.run_meta_gate([str(doc)], check_cli=True, repo=str(self.repo))
        self.assertEqual(rc, 0)

    def test_check_i18n_skips_cleanly_without_i18n_module(self):
        from unittest import mock

        import tdq_meta_gate

        skill = self._write("skills/demo/SKILL.md", "---\nname: demo\ndescription: demo\n---\n\n# Demo\n")
        with mock.patch.object(tdq_meta_gate, "_load_i18n_check", return_value=None):
            result = tdq_meta_gate._check_i18n([str(skill)], str(self.repo), run_all=False)
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
