"""Tests for T2.3 unified PreToolUse `command_gate.py` and manifest/AGENTS rules."""
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from helper import HOOKS, ROOT

TOOLS = os.path.join(ROOT, "tools")


def _install_fake_rtk(bin_dir):
    """Create a fake rtk executable/cmd shim in bin_dir supporting --version, gain, rewrite."""
    os.makedirs(bin_dir, exist_ok=True)
    if sys.platform.startswith("win"):
        py_helper = os.path.join(bin_dir, "fake_rtk_impl.py")
        cmd_shim = os.path.join(bin_dir, "rtk.cmd")
        Path(py_helper).write_text(
            "import sys\n"
            "args = sys.argv[1:]\n"
            "if args == ['--version']:\n"
            "    print('rtk 1.2.0')\n"
            "elif args == ['gain']:\n"
            "    print('total saved: 0')\n"
            "elif len(args) >= 2 and args[0] == 'rewrite':\n"
            "    cmd = args[2] if args[1] == '--' and len(args) >= 3 else args[1]\n"
            "    if cmd.startswith(('git ', 'pytest ', 'cargo ')):\n"
            "        print('rtk ' + cmd)\n"
            "        sys.exit(3)\n"
            "    sys.exit(1)\n",
            encoding="utf-8",
        )
        Path(cmd_shim).write_text(
            f'@echo off\r\n"{sys.executable}" "{py_helper}" %*\r\n',
            encoding="utf-8",
        )
        return cmd_shim
    sh_bin = os.path.join(bin_dir, "rtk")
    Path(sh_bin).write_text(
        f'#!{sys.executable}\n'
        "import sys\n"
        "args = sys.argv[1:]\n"
        "if args == ['--version']:\n"
        "    print('rtk 1.2.0')\n"
        "elif args == ['gain']:\n"
        "    print('total saved: 0')\n"
        "elif len(args) >= 2 and args[0] == 'rewrite':\n"
        "    cmd = args[2] if args[1] == '--' and len(args) >= 3 else args[1]\n"
        "    if cmd.startswith(('git ', 'pytest ', 'cargo ')):\n"
        "        print('rtk ' + cmd)\n"
        "        sys.exit(3)\n"
        "    sys.exit(1)\n",
        encoding="utf-8",
    )
    os.chmod(sh_bin, os.stat(sh_bin).st_mode | stat.S_IXUSR)
    return sh_bin


class TestCommandGate(unittest.TestCase):
    """Verify collapsed command_gate.py execution and agy_manifests outputs."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.cwd = self._tmp.name
        self.fake_bin = os.path.join(self.cwd, "fake-bin")
        _install_fake_rtk(self.fake_bin)

    def tearDown(self):
        self._tmp.cleanup()

    def _run_gate_cli(self, payload, extra_path=True):
        gate_path = os.path.join(HOOKS, "command_gate.py")
        env = dict(os.environ)
        env["PYTHONUTF8"] = "1"
        env["TDQ_PROJECT_DIR"] = self.cwd
        if extra_path:
            env["PATH"] = self.fake_bin + os.pathsep + env.get("PATH", "")
        else:
            env["PATH"] = os.path.dirname(sys.executable)
        proc = subprocess.run(
            [sys.executable, "-X", "utf8", gate_path, "--event", "PreToolUse"],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env,
            cwd=self.cwd,
            timeout=15,
        )
        return proc

    def test_empty_payload_allows_cleanly(self):
        proc = self._run_gate_cli({}, extra_path=False)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        data = json.loads(proc.stdout)
        self.assertEqual(data, {"decision": "allow"})

    def test_rtk_bypass_grep_is_denied_before_rewrite(self):
        payload = {
            "cwd": self.cwd,
            "session_id": "cmd-gate-search-deny",
            "tool_name": "run_command",
            "tool_input": {"CommandLine": "rtk bypass rg foo src/"},
        }
        proc = self._run_gate_cli(payload, extra_path=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        data = json.loads(proc.stdout)
        self.assertEqual(data["decision"], "deny")
        self.assertIn("[TDQ:SEARCH]", data["reason"])
        self.assertNotIn("overwrite", data)

    def test_git_status_emits_overwrite_command_line(self):
        payload = {
            "cwd": self.cwd,
            "session_id": "cmd-gate-git-status",
            "tool_name": "run_command",
            "tool_input": {"CommandLine": "git status"},
        }
        proc = self._run_gate_cli(payload, extra_path=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        data = json.loads(proc.stdout)
        self.assertEqual(
            data,
            {"decision": "allow", "overwrite": {"CommandLine": "rtk git status"}},
        )

    def test_git_diff_with_rtk_rewrites_and_suppresses_output_remind(self):
        sys.path.insert(0, HOOKS)
        try:
            import _common
        finally:
            if sys.path and sys.path[0] == HOOKS:
                sys.path.pop(0)
        payload = {
            "cwd": self.cwd,
            "session_id": "cmd-gate-git-diff",
            "tool_name": "run_command",
            "tool_input": {"CommandLine": "git diff"},
        }
        proc = self._run_gate_cli(payload, extra_path=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        data = json.loads(proc.stdout)
        self.assertEqual(data["decision"], "allow")
        self.assertEqual(data["overwrite"]["CommandLine"], "rtk git diff")
        rows = _common.turn_rows(self.cwd, {"cwd": self.cwd, "session_id": "cmd-gate-git-diff"})
        self.assertFalse(any(r.get("code") == "TDQ:OUTPUT" for r in rows))

    def test_qc_role_skips_git_diff_compression(self):
        sys.path.insert(0, HOOKS)
        try:
            import _common
            import command_gate
        finally:
            if sys.path and sys.path[0] == HOOKS:
                sys.path.pop(0)
        _common.register_subagent_role(self.cwd, "qc-subagent-1", "tdq-qc-tester")
        saved = dict(_common._RUNTIME_STATE)
        saved["context_lines"] = list(saved.get("context_lines") or [])
        saved["overwrite"] = dict(saved.get("overwrite") or {})
        try:
            payload = {
                "cwd": self.cwd,
                "session_id": "qc-subagent-1",
                "hookEventName": "PreToolUse",
                "tool_name": "run_command",
                "toolInput": {"CommandLine": "git diff"},
            }
            rewritten = command_gate.process_payload(payload)
            self.assertIsNone(rewritten)
            self.assertEqual(_common._RUNTIME_STATE.get("overwrite"), {})
        finally:
            _common._RUNTIME_STATE.clear()
            _common._RUNTIME_STATE.update(saved)

    def test_python_pytest_is_never_rewritten(self):
        payload = {
            "cwd": self.cwd,
            "session_id": "cmd-gate-pytest",
            "tool_name": "run_command",
            "tool_input": {"CommandLine": "py -3 -m pytest -q"},
        }
        proc = self._run_gate_cli(payload, extra_path=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        data = json.loads(proc.stdout)
        self.assertEqual(data, {"decision": "allow"})

    def test_agy_manifests_collapse_and_agents_rtk_rules(self):
        sys.path.insert(0, TOOLS)
        try:
            from patches import agy_manifests
        finally:
            if sys.path and sys.path[0] == TOOLS:
                sys.path.pop(0)
        out_dir = Path(self.cwd) / "plugin-out"
        (out_dir / "hooks").mkdir(parents=True, exist_ok=True)
        (out_dir / "rules").mkdir(parents=True, exist_ok=True)
        agy_manifests.generate_hooks_json(out_dir)
        agy_manifests.generate_two_tier_rules(out_dir)
        hooks_data = json.loads((out_dir / "hooks.json").read_text(encoding="utf-8"))
        self.assertEqual(len(hooks_data.keys()), 6)
        pre = hooks_data["tdq-pre-tool-gates"]["PreToolUse"]
        cmd_entries = [m for m in pre if m["matcher"] == "run_command"]
        self.assertEqual(len(cmd_entries), 1)
        self.assertIn("command_gate.py", cmd_entries[0]["hooks"][0]["command"])
        search_entries = [m for m in pre if "grep_search" in m["matcher"]]
        self.assertEqual(len(search_entries), 1)
        self.assertNotIn("run_command", search_entries[0]["matcher"])
        agents_text = (out_dir / "rules" / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("rtk recall", agents_text)
        self.assertIn("rtk bypass", agents_text)


if __name__ == "__main__":
    unittest.main()
