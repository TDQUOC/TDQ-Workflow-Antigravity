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

from helper import ROOT

META_GATE = os.path.join(ROOT, "scripts", "tdq_meta_gate.py")
SCRIPTS_DIR = os.path.join(ROOT, "scripts")
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

    def _run(self, *args: str, env: dict[str, str] | None = None):
        full_env = dict(os.environ)
        full_env.pop("TDQ_LOG", None)
        full_env["TDQ_KHONG_CHAM_MAY"] = "1"
        full_env["TDQ_KHOI_TAO_NEN"] = "0"
        if env:
            full_env.update(env)
        return subprocess.run(
            [sys.executable, META_GATE, *args],
            check=False,
            cwd=str(self.repo),
            env=full_env,
            capture_output=True,
            encoding="utf-8",
            text=True,
            timeout=30,
        )

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
        doc = self._write("docs/tdq/brief/note.md", "# Brief\n\nTóm tắt ngắn gọn.\n")
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
        bad_py = self._write("scripts/demo.py", "# ghi chú tiếng Việt\nVALUE = 1\n")
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
        doc = self._write("docs/tdq/brief/note.md", "# Brief\n\nNội dung sạch.\n")
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
        doc = self._write("docs/tdq/brief/note.md", "# Brief\n\nKiểm tra log.\n")
        loud = self._run("--repo", str(self.repo), "--files", str(doc), env={"TDQ_LOG": "1"})
        self.assertEqual(loud.returncode, 0, loud.stdout + loud.stderr)
        self.assertTrue(loud.stderr, "TDQ_LOG=1 must emit stderr logs")
        for line in loud.stderr.splitlines():
            match = re.match(r"^\[([^\]]+)\] tdq_meta_gate: \S", line)
            self.assertIsNotNone(match, line)
            stamp = datetime.datetime.fromisoformat(match.group(1))
            self.assertIsNotNone(stamp.tzinfo, line)
        self.assertNotRegex(loud.stdout, r"(?m)^\[\d{4}-\d{2}-\d{2}T")

        default_loud = self._run("--repo", str(self.repo), "--files", str(doc))
        self.assertEqual(default_loud.returncode, 0)
        self.assertIn("tdq_meta_gate:", default_loud.stderr)

        quiet = self._run("--repo", str(self.repo), "--files", str(doc), env={"TDQ_LOG": "0"})
        self.assertEqual(quiet.returncode, 0, quiet.stdout + quiet.stderr)
        self.assertEqual(quiet.stderr, "", f"TDQ_LOG=0 must silence stderr: {quiet.stderr!r}")

    def test_git_auto_discovery_without_files(self):
        subprocess.run(["git", "init"], cwd=str(self.repo), check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "tdq-test"], cwd=str(self.repo), check=True)
        subprocess.run(["git", "config", "user.email", "tdq@test.local"], cwd=str(self.repo), check=True)
        self._write("docs/tdq/brief/init.md", "# Brief\n\nKhởi tạo sạch.\n")
        subprocess.run(["git", "add", "."], cwd=str(self.repo), check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "chore: init"], cwd=str(self.repo), check=True, capture_output=True)

        clean_proc = self._run("--repo", str(self.repo))
        self.assertEqual(clean_proc.returncode, 0, clean_proc.stdout + clean_proc.stderr)

        self._write("scripts/dirty.py", "# còn tiếng Việt\nX = 1\n")
        dirty_proc = self._run("--repo", str(self.repo))
        self.assertEqual(dirty_proc.returncode, 1, dirty_proc.stdout + dirty_proc.stderr)
        self.assertIn("dirty.py:1", dirty_proc.stdout)

    def test_run_meta_gate_python_api(self):
        import tdq_meta_gate

        doc = self._write("docs/tdq/brief/api.md", "# Brief\n\nKiểm API.\n")
        rc = tdq_meta_gate.run_meta_gate([str(doc)], check_cli=True, repo=str(self.repo))
        self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()
