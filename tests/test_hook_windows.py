"""The six hooks must SURVIVE a turn on every host, Windows included.

This is the test the 0.48.0 suite did not have, and its absence is why the plugin shipped dead
on Windows for an unknown number of releases: every hook died at its first `print` carrying `✓`
or Vietnamese, because Python takes the console encoding from the locale and a stock Windows box
answers cp1252. Nothing in 1907 tests ran a hook the way the host runs one — as a child process
whose stdout is a pipe, with no PYTHONUTF8 in the environment.

So that is exactly what these cases do: spawn each hook as a child, feed it a payload on stdin,
and demand exit 0 with its block intact. The environment is scrubbed of `PYTHONUTF8` and
`PYTHONIOENCODING` on purpose — inheriting them would hide the very bug this file exists to
catch, and the suite would stay green while the product stayed broken.
"""
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from helper import ROOT

HOOKS = os.path.join(ROOT, "hooks", "scripts")

# hook file -> (payload, a fragment its output must carry; "" = only the exit code matters)
CA_KIEM = {
    "session_start.py": ({"hook_event_name": "SessionStart"}, "[TDQ:NEXT]"),
    "subagent_start.py": ({"hook_event_name": "SubagentStart"}, ""),
    "prompt_context.py": ({"hook_event_name": "UserPromptSubmit",
                           "prompt": "một việc nhỏ"}, ""),
    "stop_gate.py": ({"hook_event_name": "Stop"}, ""),
    "edit_gate.py": ({"hook_event_name": "PreToolUse", "tool_name": "Edit",
                      "tool_input": {"file_path": "src/a.py"}}, ""),
    "read_gate.py": ({"hook_event_name": "PreToolUse", "tool_name": "Read",
                      "tool_input": {"file_path": "src/a.py"}}, ""),
    "bash_gate.py": ({"hook_event_name": "PreToolUse", "tool_name": "Bash",
                      "tool_input": {"command": "git commit -m x"}}, ""),
    "search_gate.py": ({"hook_event_name": "PreToolUse", "tool_name": "Grep",
                        "tool_input": {"pattern": "foo"}}, ""),
    "search_observe.py": ({"hook_event_name": "PostToolUse", "tool_name": "mcp__lsp__find_symbol",
                           "tool_input": {"name": "bar"}}, ""),
    "lsp_gate.py": ({"hook_event_name": "PreToolUse", "tool_name": "mcp__lsp__start_lsp",
                     "tool_input": {"root_dir": "c:/repo", "language_id": "python"}}, ""),
    "ask_gate.py": ({"hook_event_name": "PreToolUse", "tool_name": "AskUserQuestion",
                     "tool_input": {"question": "ok?"}}, ""),
}


def moi_truong_nhu_host():
    """The host's environment, minus the two variables that would paper over the bug."""
    env = dict(os.environ)
    env.pop("PYTHONUTF8", None)
    env.pop("PYTHONIOENCODING", None)
    # A hook must never be judged against the machine's own live request.
    env["TDQ_LOG"] = "0"
    return env


class SauHookSongTest(unittest.TestCase):
    """One case per hook. A dead hook costs the whole turn, so exit 0 is the floor."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def chay(self, ten_hook, payload):
        day_du = dict(payload, session_id="s1", cwd=self.tmp.name)
        return subprocess.run(
            [sys.executable, os.path.join(HOOKS, ten_hook)],
            input=json.dumps(day_du), capture_output=True, text=True,
            encoding="utf-8", errors="replace", env=moi_truong_nhu_host(), timeout=120)

    def test_moi_hook_thoat_0(self):
        for ten_hook, (payload, _) in CA_KIEM.items():
            with self.subTest(hook=ten_hook):
                proc = self.chay(ten_hook, payload)
                self.assertEqual(proc.returncode, 0,
                                 f"{ten_hook} died:\n{proc.stderr[-800:]}")

    def test_khong_hook_nao_no_vi_encoding(self):
        """The exact failure that shipped: UnicodeEncodeError on the first non-ASCII print."""
        for ten_hook, (payload, _) in CA_KIEM.items():
            with self.subTest(hook=ten_hook):
                proc = self.chay(ten_hook, payload)
                self.assertNotIn("UnicodeEncodeError", proc.stderr)
                self.assertNotIn("UnicodeDecodeError", proc.stderr)

    def test_khoi_tdq_ra_nguyen_ven(self):
        for ten_hook, (payload, manh) in CA_KIEM.items():
            if not manh:
                continue
            with self.subTest(hook=ten_hook):
                proc = self.chay(ten_hook, payload)
                self.assertIn(manh, proc.stdout)

    def test_session_start_giu_duoc_tieng_viet_va_dau_tick(self):
        """Output must survive the pipe as UTF-8 — mojibake is a silent kind of dead."""
        proc = self.chay("session_start.py", {"hook_event_name": "SessionStart"})
        self.assertIn("✓", proc.stdout)

    def test_payload_hong_khong_giet_hook_nao(self):
        """A malformed payload is a bad turn, never a dead session."""
        for ten_hook in CA_KIEM:
            with self.subTest(hook=ten_hook):
                proc = subprocess.run(
                    [sys.executable, os.path.join(HOOKS, ten_hook)],
                    input="{not json", capture_output=True, text=True,
                    encoding="utf-8", errors="replace",
                    env=moi_truong_nhu_host(), timeout=120)
                self.assertEqual(proc.returncode, 0, ten_hook)

    def test_bash_gate_powershell_parity(self):
        """PowerShell commands receive the exact same git/ai trace inspection as Bash (O03)."""
        proc = self.chay("bash_gate.py", {
            "hook_event_name": "PreToolUse",
            "tool_name": "PowerShell",
            "tool_input": {"command": "git commit -m 'feat: test co-authored-by: claude'"}
        })
        self.assertEqual(proc.returncode, 0)
        self.assertIn("TDQ:GIT", proc.stdout + proc.stderr)

    def test_opencode_tdq_workflow_wrapper_filtered(self):
        """Injected <TDQ_WORKFLOW> wrapper from OpenCode is stripped before checking approval (O03)."""
        sys.path.insert(0, HOOKS)
        try:
            import prompt_context
            # Prompt that only has approval words INSIDE wrapper is NOT an approval
            p_wrapped_only = "<TDQ_WORKFLOW>Quy tắc: duyệt spec khi sẵn sàng</TDQ_WORKFLOW>\n\nHãy giải thích code này"
            self.assertFalse(prompt_context.looks_like_approval(p_wrapped_only, "spec"))

            # Prompt that has approval OUTSIDE wrapper IS an approval
            p_real_approve = "<TDQ_WORKFLOW>Chỉ dẫn hệ thống</TDQ_WORKFLOW>\n\nduyệt spec"
            self.assertTrue(prompt_context.looks_like_approval(p_real_approve, "spec"))
        finally:
            if sys.path and sys.path[0] == HOOKS:
                sys.path.pop(0)

    def test_quote_path_in_build_portable_antigravity(self):
        """Antigravity hook commands must quote script paths to survive spaces on Windows (O03)."""
        sys.path.insert(0, os.path.join(ROOT, "scripts"))
        try:
            import build_portable
            out_file = os.path.join(self.tmp.name, "hooks.json")
            build_portable._sinh_hooks_agy(out_file, nen_tang="win32", goc_cai="C:/Program Files/My Plugin")
            with open(out_file, encoding="utf-8") as f:
                data = json.load(f)
            hooks = data.get("hooks", {})
            found = False
            for hook_list in hooks.values():
                for h_entry in hook_list:
                    for h in h_entry.get("hooks", []):
                        cmd = h.get("command", "")
                        if "agy_pretooluse_gate.py" in cmd:
                            found = True
                            self.assertIn('"C:/Program Files/My Plugin/hooks/scripts/agy_pretooluse_gate.py"', cmd)
            self.assertTrue(found, "Did not find agy_pretooluse_gate hook in antigravity hooks")
        finally:
            if sys.path and sys.path[0] == os.path.join(ROOT, "scripts"):
                sys.path.pop(0)

    def test_utf8_io_switches_stdin(self):
        """force_utf8 must be able to switch stdin encoding as well (O03)."""
        sys.path.insert(0, os.path.join(ROOT, "scripts"))
        try:
            import utf8_io
            class FakeStream:
                def __init__(self, enc):
                    self.encoding = enc
                    self.reconfigured = False
                def reconfigure(self, encoding, errors=None):
                    del errors
                    self.encoding = encoding
                    self.reconfigured = True

            fake_in = FakeStream("cp1252")
            fake_out = FakeStream("utf-8")
            fake_err = FakeStream("utf-8")
            changed = utf8_io.force_utf8(out=fake_out, err=fake_err, inp=fake_in)
            self.assertEqual(changed, 1)
            self.assertTrue(fake_in.reconfigured)
            self.assertEqual(fake_in.encoding, "utf-8")
        finally:
            if sys.path and sys.path[0] == os.path.join(ROOT, "scripts"):
                sys.path.pop(0)


class TestCommonMcpNormalization(unittest.TestCase):
    """Verify _common.normalize_payload unifies MCP naming and _tool_args_present."""

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, HOOKS)
        try:
            import _common
            cls._common = _common
        finally:
            if sys.path and sys.path[0] == HOOKS:
                sys.path.pop(0)

    def setUp(self):
        self._saved_runtime_state = dict(self._common._RUNTIME_STATE)
        self._saved_runtime_state["context_lines"] = list(
            self._saved_runtime_state.get("context_lines") or []
        )

    def tearDown(self):
        self._common._RUNTIME_STATE.clear()
        self._common._RUNTIME_STATE.update(self._saved_runtime_state)

    def test_runtime_state_restored_after_teardown(self):
        saved_is_agy = self._saved_runtime_state.get("is_agy")
        self._common.normalize_payload({
            "hookEventName": "PreToolUse",
            "tool_name": "call_mcp_tool",
            "tool_input": {"ServerName": "chrome-devtools", "ToolName": "list_pages", "Arguments": {}},
        })
        self.assertIs(self._common._RUNTIME_STATE["is_agy"], True)
        self.tearDown()
        self.assertIs(self._common._RUNTIME_STATE["is_agy"], saved_is_agy)

    def test_unwrap_chrome_devtools_and_tavily_keeps_server_name(self):
        out = self._common.normalize_payload({
            "hookEventName": "PreToolUse",
            "tool_name": "call_mcp_tool",
            "tool_input": {
                "ServerName": "chrome-devtools",
                "ToolName": "select_page",
                "Arguments": {"bringToFront": True, "pageId": 1},
            },
        })
        self.assertEqual(out["tool_name"], "mcp__chrome-devtools__select_page")
        self.assertEqual(out["tool_input"], {"bringToFront": True, "pageId": 1})
        self.assertNotIn("_tool_args_present", out)
        self.assertIs(self._common.has_tool_args(), True)

    def test_unwrap_other_lsp_never_maps_to_tdq_lsp(self):
        out_lazy = self._common.normalize_payload({
            "hookEventName": "PreToolUse",
            "tool_name": "call_mcp_tool",
            "tool_input": {"ServerName": "other_lsp", "ToolName": "find_symbol", "Arguments": {}},
        })
        self.assertEqual(out_lazy["tool_name"], "mcp__other_lsp__find_symbol")
        out_eager = self._common.normalize_payload({
            "hookEventName": "PreToolUse",
            "tool_name": "mcp_other_lsp_find_symbol",
            "tool_input": {"query": "foo"},
        })
        self.assertEqual(out_eager["tool_name"], "mcp_other_lsp_find_symbol")

    def test_tool_args_present_distinguishes_empty_dict_from_missing_or_broken(self):
        out_empty = self._common.normalize_payload({
            "hookEventName": "PreToolUse",
            "tool_name": "call_mcp_tool",
            "tool_input": {
                "ServerName": "tdq-workflow-agy_lsp",
                "ToolName": "start_lsp",
                "Arguments": {},
            },
        })
        self.assertEqual(out_empty["tool_name"], "mcp__lsp__start_lsp")
        self.assertEqual(out_empty["tool_input"], {})
        self.assertNotIn("_tool_args_present", out_empty)
        self.assertIs(self._common.has_tool_args(), True)

        self._common.normalize_payload({
            "hookEventName": "PreToolUse",
            "tool_name": "call_mcp_tool",
            "tool_input": {
                "ServerName": "tdq-workflow-agy_lsp",
                "ToolName": "start_lsp",
                "Arguments": "{}",
            },
        })
        self.assertIs(self._common.has_tool_args(), True)

        out_broken = self._common.normalize_payload({
            "hookEventName": "PreToolUse",
            "tool_name": "call_mcp_tool",
            "tool_input": {
                "ServerName": "tdq-workflow-agy_lsp",
                "ToolName": "start_lsp",
                "Arguments": "{bad json",
            },
        })
        self.assertEqual(out_broken["tool_name"], "mcp__lsp__start_lsp")
        self.assertIs(self._common.has_tool_args(), False)

        out_missing_claude = self._common.normalize_payload({
            "tool_name": "mcp__lsp__start_lsp",
            "cwd": ".",
        })
        self.assertNotIn("_tool_args_present", out_missing_claude)
        self.assertIs(self._common.has_tool_args(), False)


class TestCommonCollapsedSessionAndOverwrite(unittest.TestCase):
    """Collapsed session cache + Antigravity PreToolUse `overwrite` emitter."""

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, HOOKS)
        try:
            import _common
            cls._common = _common
        finally:
            if sys.path and sys.path[0] == HOOKS:
                sys.path.pop(0)

    def setUp(self):
        _common = self._common
        self._saved = dict(_common._RUNTIME_STATE)
        self._saved["context_lines"] = list(_common._RUNTIME_STATE.get("context_lines") or [])
        self._saved["overwrite"] = dict(_common._RUNTIME_STATE.get("overwrite") or {})
        _common._RUNTIME_STATE.update({
            "event": None,
            "is_agy": False,
            "deny_reason": None,
            "stop_reason": None,
            "context_lines": [],
            "registered": False,
            "tool_args_present": False,
            "overwrite": {},
            "collapsed_payload": None,
        })

    def tearDown(self):
        self._common._RUNTIME_STATE.clear()
        self._common._RUNTIME_STATE.update(self._saved)

    def test_collapsed_session_reuses_payload_without_rereading_stdin(self):
        cached = self._common.begin_collapsed_session({
            "hookEventName": "PreToolUse",
            "tool_name": "run_command",
            "toolInput": {"CommandLine": "git status"},
            "cwd": ".",
        })
        self.assertEqual(cached["tool_input"]["command"], "git status")
        with mock.patch("sys.stdin", io.StringIO("not json")):
            again = self._common.read_payload()
        self.assertEqual(again["tool_input"]["command"], "git status")
        self.assertIs(self._common._RUNTIME_STATE["is_agy"], True)
        self._common.end_collapsed_session()
        self.assertIsNone(self._common._RUNTIME_STATE["collapsed_payload"])

    def test_flush_agy_stdout_emits_overwrite_on_allow_only(self):
        self._common._RUNTIME_STATE.update({
            "event": "PreToolUse",
            "is_agy": True,
            "deny_reason": None,
            "overwrite": {},
        })
        self._common.set_overwrite({"CommandLine": "rtk git status"})
        buf = io.StringIO()
        with mock.patch("sys.stdout", buf):
            self._common._flush_agy_stdout()
        data = json.loads(buf.getvalue())
        self.assertEqual(
            data,
            {"decision": "allow", "overwrite": {"CommandLine": "rtk git status"}},
        )

    def test_flush_agy_stdout_drops_overwrite_when_denied(self):
        self._common._RUNTIME_STATE.update({
            "event": "PreToolUse",
            "is_agy": True,
            "deny_reason": "[TDQ:SEARCH] forbidden",
            "overwrite": {},
        })
        self._common.set_overwrite({"CommandLine": "rtk rg foo"})
        buf = io.StringIO()
        with mock.patch("sys.stdout", buf):
            self._common._flush_agy_stdout()
        data = json.loads(buf.getvalue())
        self.assertEqual(data["decision"], "deny")
        self.assertNotIn("overwrite", data)


if __name__ == "__main__":
    unittest.main()
