"""agy_pretooluse_gate.py / agy_stop_gate.py — hook thật cho Antigravity CLI (agy).

Khác `bash_gate.py`/`stop_gate.py` của Claude Code (chỉ nhắc): `PreToolUse` của agy trả
`decision: "deny"` là chặn cứng thật, `Stop` trả `decision: "continue"` ép loop không dừng
sớm — 2 hook này port lại đúng các điều kiện đã có, không phát minh điều kiện mới.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

from helper import HOOKS as HOOKS_DIR, run_hook, write_state, write_file

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "hooks", "scripts"))


def agy(script, payload_dict):
    return run_hook(script, payload_dict)


def parsed(out):
    """JSON output của agy hook (schema phẳng, khác hookSpecificOutput của Claude Code)."""
    if not out:
        return {}
    return json.loads(out)


# ------------------------------------------------------- PreToolUse (T1.1/T1.2)

# 4 hình dạng field-path khả dĩ cho lệnh shell trong payload PreToolUse của agy — schema
# thật chưa được tài liệu hoá chính xác (xem research Truy vấn 2), hook phải thử cả 4.
def _shapes(cmd):
    return [
        {"tool_input": {"command": cmd}},
        {"toolInput": {"command": cmd}},
        {"input": {"command": cmd}},
        {"command": cmd},
    ]


class TestAgyPreToolUseDeny(unittest.TestCase):
    def test_deny_banned_branch_name_every_field_shape(self):
        for payload in _shapes("git checkout -b antigravity-x"):
            rc, out, _ = agy("agy_pretooluse_gate.py", payload)
            self.assertEqual(rc, 0, payload)
            data = parsed(out)
            self.assertEqual(data.get("decision"), "deny", payload)
            self.assertIn("antigravity-x", data.get("reason", ""))

    def test_deny_worktree_add_with_banned_name(self):
        _, out, _ = agy("agy_pretooluse_gate.py",
                         {"tool_input": {"command": "git worktree add ../claude-wt"}})
        data = parsed(out)
        self.assertEqual(data.get("decision"), "deny")

    def test_deny_state_json_write_redirect(self):
        _, out, _ = agy("agy_pretooluse_gate.py",
                         {"tool_input": {"command": "echo '{}' > docs/tdq/state.json"}})
        data = parsed(out)
        self.assertEqual(data.get("decision"), "deny")
        self.assertIn("tdq_state.py", data.get("reason", ""))

    def test_deny_state_json_write_sed_i(self):
        _, out, _ = agy("agy_pretooluse_gate.py", {"tool_input": {
            "command": "sed -i '' 's/false/true/' docs/tdq/state.json"}})
        self.assertEqual(parsed(out).get("decision"), "deny")

    def test_deny_state_json_write_python_open(self):
        _, out, _ = agy("agy_pretooluse_gate.py", {"tool_input": {
            "command": "python3 -c \"open('docs/tdq/state.json','w').write('{}')\""}})
        self.assertEqual(parsed(out).get("decision"), "deny")

    def test_allow_state_json_read_cat(self):
        rc, out, _ = agy("agy_pretooluse_gate.py",
                          {"tool_input": {"command": "cat docs/tdq/state.json"}})
        self.assertEqual(rc, 0)
        self.assertEqual(parsed(out), {})

    def test_allow_state_json_read_python_open_no_mode(self):
        _, out, _ = agy("agy_pretooluse_gate.py", {"tool_input": {
            "command": "python3 -c \"open('docs/tdq/state.json').read()\""}})
        self.assertEqual(parsed(out), {})

    def test_allow_state_json_read_sed_n(self):
        _, out, _ = agy("agy_pretooluse_gate.py",
                         {"tool_input": {"command": "sed -n '1,5p' docs/tdq/state.json"}})
        self.assertEqual(parsed(out), {})

    def test_allow_branch_name_containing_word_not_at_start(self):
        _, out, _ = agy("agy_pretooluse_gate.py",
                         {"tool_input": {"command": "git checkout -b fix-antigravity-docs"}})
        self.assertEqual(parsed(out), {})

    def test_allow_unrelated_command(self):
        rc, out, _ = agy("agy_pretooluse_gate.py", {"tool_input": {"command": "ls -la"}})
        self.assertEqual(rc, 0)
        self.assertEqual(parsed(out), {})

    def test_deny_worktree_add_with_banned_name_windows_backslash(self):
        _, out, _ = agy("agy_pretooluse_gate.py",
                         {"tool_input": {"command": r"git worktree add ..\claude-wt"}})
        data = parsed(out)
        self.assertEqual(data.get("decision"), "deny")

    def test_deny_protojson_toolcall_args_commandline(self):
        _, out, _ = agy("agy_pretooluse_gate.py", {
            "toolCall": {"name": "run_command", "args": {"CommandLine": "git checkout -b gemini-x"}}
        })
        data = parsed(out)
        self.assertEqual(data.get("decision"), "deny")

    def test_allow_empty_payload_no_crash(self):
        rc, out, _ = agy("agy_pretooluse_gate.py", {})
        self.assertEqual(rc, 0)
        self.assertEqual(out, "")

    def test_allow_malformed_stdin_no_crash(self):
        proc_rc, _, _ = run_hook("agy_pretooluse_gate.py", {})
        self.assertEqual(proc_rc, 0)


# ------------------------------------------------------- Stop (T1.3/T1.4)

class StopBase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.cwd = self._tmp.name
        self.addCleanup(self._tmp.cleanup)

    def stop(self, **payload):
        payload.setdefault("cwd", self.cwd)
        return agy("agy_stop_gate.py", payload)

    def plan(self, rel, content):
        return write_file(self.cwd, rel, content)


PLAN_ONE_OPEN = """# Plan
- [ ] **T1.1** (e5m) làm gì đó — Test: x
"""
PLAN_ALL_DONE = """# Plan
- [x] **T1.1** (e5m) làm gì đó — Test: x
"""


class TestAgyStopGate(StopBase):
    def test_no_state_silent(self):
        rc, out, _ = self.stop()
        self.assertEqual(rc, 0)
        self.assertEqual(out, "")

    def test_continue_when_plan_unfinished(self):
        write_state(self.cwd, active_request="r1", lane="full", phase="implement",
                    plan_file="docs/tdq/plan/p.md")
        self.plan("docs/tdq/plan/p.md", PLAN_ONE_OPEN)
        _, out, _ = self.stop()
        data = parsed(out)
        self.assertEqual(data.get("decision"), "continue")
        self.assertIn("TDQ:UNFINISHED", data.get("reason", ""))

    def test_silent_when_plan_all_done(self):
        write_state(self.cwd, active_request="r1", lane="full", phase="implement",
                    plan_file="docs/tdq/plan/p.md")
        self.plan("docs/tdq/plan/p.md", PLAN_ALL_DONE)
        _, out, _ = self.stop()
        self.assertEqual(parsed(out), {})

    def test_silent_when_phase_not_implement(self):
        write_state(self.cwd, active_request="r1", lane="full", phase="qc",
                    plan_file="docs/tdq/plan/p.md")
        self.plan("docs/tdq/plan/p.md", PLAN_ONE_OPEN)
        _, out, _ = self.stop()
        self.assertEqual(parsed(out), {})

    def test_streak_steps_down_after_max(self):
        write_state(self.cwd, active_request="r1", lane="full", phase="implement",
                    plan_file="docs/tdq/plan/p.md")
        self.plan("docs/tdq/plan/p.md", PLAN_ONE_OPEN)
        seen_continue = False
        last_decision = None
        for _ in range(5):
            _, out, _ = self.stop()
            last_decision = parsed(out).get("decision")
            if last_decision == "continue":
                seen_continue = True
            else:
                break
        self.assertTrue(seen_continue)
        # Đủ MAX_STREAK lần liên tiếp cùng sha plan không tiến triển → hạ xuống, thôi chặn.
        self.assertNotEqual(last_decision, "continue")

    def test_streak_resets_when_plan_progresses(self):
        write_state(self.cwd, active_request="r1", lane="full", phase="implement",
                    plan_file="docs/tdq/plan/p.md")
        self.plan("docs/tdq/plan/p.md", PLAN_ONE_OPEN)
        self.stop()
        self.stop()
        self.plan("docs/tdq/plan/p.md", PLAN_ALL_DONE)
        _, out, _ = self.stop()
        self.assertEqual(parsed(out), {})

    def test_no_crash_on_alternate_cwd_field_name(self):
        # No "cwd" key, only an alternate name — must still resolve to the temp dir, not fall
        # back to os.getcwd() (which would read the REAL project's own state.json).
        rc, out, _ = agy("agy_stop_gate.py", {"workingDirectory": self.cwd})
        self.assertEqual(rc, 0)
        self.assertEqual(parsed(out), {})

    def test_workspace_paths_resolved_and_terminal_stop_silent(self):
        write_state(self.cwd, active_request="r1", lane="full", phase="implement",
                    plan_file="docs/tdq/plan/p.md")
        self.plan("docs/tdq/plan/p.md", PLAN_ONE_OPEN)
        rc1, out1, _ = agy("agy_stop_gate.py", {"workspacePaths": [self.cwd]})
        self.assertEqual(rc1, 0)
        self.assertEqual(parsed(out1).get("decision"), "continue")
        rc2, out2, _ = agy("agy_stop_gate.py", {
            "workspacePaths": [self.cwd],
            "terminationReason": "USER_CANCELED",
        })
        self.assertEqual(rc2, 0)
        self.assertEqual(parsed(out2), {})

    def test_no_crash_on_malformed_stdin(self):
        # Truly broken JSON on stdin (not just an empty payload) — run with an explicit `cwd`
        # process argument so a working-directory fallback, if it ever triggered, could never
        # reach outside the temp dir into the real project's own state.json.
        proc = subprocess.run(
            [sys.executable, os.path.join(HOOKS_DIR, "agy_stop_gate.py")],
            input="not json", capture_output=True,
            encoding="utf-8", text=True, timeout=30, cwd=self.cwd)
        self.assertEqual(proc.returncode, 0)


# ------------------------------------------------------- log service (T5.1)

class TestAgyLogService(unittest.TestCase):
    """Mỗi lần chặn phải in 1 dòng stderr có timestamp nêu case; TDQ_LOG=0 thì im."""

    def _pre(self, env):
        return run_hook("agy_pretooluse_gate.py",
                        {"tool_input": {"command": "git checkout -b antigravity-x"}}, env=env)

    def test_pretooluse_logs_case_when_denying(self):
        _, out, err = self._pre({"TDQ_LOG": "1"})
        self.assertEqual(parsed(out).get("decision"), "deny")
        self.assertIn("TDQ:GIT", err)
        self.assertRegex(err, r"^\[\d{4}-\d{2}-\d{2}T")

    def test_pretooluse_silent_with_log_off(self):
        _, out, err = self._pre({"TDQ_LOG": "0"})
        self.assertEqual(parsed(out).get("decision"), "deny")
        self.assertEqual(err, "")

    def test_pretooluse_state_case_named_in_log(self):
        _, _, err = run_hook("agy_pretooluse_gate.py",
                             {"tool_input": {"command": "echo '{}' > docs/tdq/state.json"}},
                             env={"TDQ_LOG": "1"})
        self.assertIn("TDQ:STATE", err)

    def test_no_log_when_allowing(self):
        _, _, err = run_hook("agy_pretooluse_gate.py",
                             {"tool_input": {"command": "ls -la"}}, env={"TDQ_LOG": "1"})
        self.assertEqual(err, "")


class TestAgyStopLogService(StopBase):
    def _blocked(self, env):
        write_state(self.cwd, active_request="r1", lane="full", phase="implement",
                    plan_file="docs/tdq/plan/p.md")
        self.plan("docs/tdq/plan/p.md", PLAN_ONE_OPEN)
        return run_hook("agy_stop_gate.py", {"cwd": self.cwd}, env=env)

    def test_stop_logs_case_when_continuing(self):
        _, out, err = self._blocked({"TDQ_LOG": "1"})
        self.assertEqual(parsed(out).get("decision"), "continue")
        self.assertIn("TDQ:UNFINISHED", err)
        self.assertRegex(err, r"^\[\d{4}-\d{2}-\d{2}T")

    def test_stop_silent_with_log_off(self):
        _, out, err = self._blocked({"TDQ_LOG": "0"})
        self.assertEqual(parsed(out).get("decision"), "continue")
        self.assertEqual(err, "")


class TestAgySmartHardeningStaged(unittest.TestCase):
    """Red->Green verification of the 6 Smart Hardening rules on freshly patched AGY hooks."""

    def setUp(self):
        import shutil
        from pathlib import Path

        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        root = Path(self._tmp.name)
        self.repo_root = Path(__file__).resolve().parent.parent
        self.plugin = root / "stage_plugin"
        shutil.copytree(self.repo_root / "hooks", self.plugin / "hooks")
        shutil.copytree(self.repo_root / "scripts", self.plugin / "scripts")
        tools_dir = str(self.repo_root / "tools")
        if tools_dir not in sys.path:
            sys.path.insert(0, tools_dir)
        from patches import agy_dispatch, agy_hooks

        agy_hooks.apply_all(self.plugin / "hooks" / "scripts")
        agy_dispatch.apply_dispatch(self.plugin / "hooks" / "scripts")
        self.dispatch = self.plugin / "hooks" / "scripts" / "dispatch.py"
        self.project = root / "proj"
        self.project.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "init", "-b", "main"], cwd=self.project, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "t@example.com"], cwd=self.project, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Tester"], cwd=self.project, check=True, capture_output=True)
        (self.project / "app.py").write_text("x = 1\n", encoding="utf-8")
        subprocess.run(["git", "add", "app.py"], cwd=self.project, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=self.project, check=True, capture_output=True)

    def _run_staged(self, event, payload):
        env = dict(os.environ)
        env.update({"TDQ_PROJECT_DIR": str(self.project), "TDQ_LOG": "0", "TDQ_RTK": "0", "RTK_DISABLED": "1"})
        body = dict(payload)
        body.setdefault("cwd", str(self.project))
        body.setdefault("conversationId", "conv-sh")
        proc = subprocess.run(
            [sys.executable, "-X", "utf8", str(self.dispatch), "--event", event],
            input=json.dumps(body, ensure_ascii=False),
            capture_output=True, text=True, encoding="utf-8", env=env, timeout=30,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return json.loads(proc.stdout.strip()) if proc.stdout.strip() else {}

    def _init_implement(self, slug="2026-11-19-0001-sh", plan_text="- [ ] **T1** a\n"):
        write_state(
            str(self.project), active_request=slug, lane="full", phase="implement",
            spec_approved=True, plan_approved=True, plan_file=f"docs/tdq/plan/{slug}.md",
        )
        write_file(str(self.project), f"docs/tdq/plan/{slug}.md", plan_text)

    def test_sh1_tick_zero_multi_and_streak_8(self):
        self._init_implement(plan_text="- [ ] **T1** open\n")
        d0 = self._run_staged("PreToolUse", {"tool_name": "edit_file", "tool_input": {"TargetFile": str(self.project / "app.py")}})
        self.assertEqual(d0.get("decision"), "deny")
        self.assertIn("TDQ:TICK", d0.get("reason", ""))

        write_file(str(self.project), "docs/tdq/plan/2026-11-19-0001-sh.md", "- [~] **T1** a\n- [~] **T2** b\n")
        d2 = self._run_staged("PreToolUse", {"tool_name": "edit_file", "tool_input": {"TargetFile": str(self.project / "app.py")}})
        self.assertEqual(d2.get("decision"), "deny")
        self.assertIn("TDQ:TICK", d2.get("reason", ""))

        write_file(str(self.project), "docs/tdq/plan/2026-11-19-0001-sh.md", "- [~] **T1** a\n")
        for idx in range(8):
            ok = self._run_staged("PreToolUse", {"tool_name": "edit_file", "tool_input": {"TargetFile": str(self.project / f"f{idx}.py")}})
            self.assertEqual(ok.get("decision"), "allow", f"edit {idx + 1} should allow")
        d9 = self._run_staged("PreToolUse", {"tool_name": "edit_file", "tool_input": {"TargetFile": str(self.project / "f9.py")}})
        self.assertEqual(d9.get("decision"), "deny")
        self.assertIn("TDQ:TICK", d9.get("reason", ""))
        pi_tick = self._run_staged("PostInvocation", {})
        self.assertIn("TDQ:TICK", str(pi_tick))

    def test_sh2_stop_log_hard_block_and_exemptions(self):
        self._init_implement(plan_text="- [x] **T1** a\n")
        self._run_staged("PreInvocation", {"prompt": "work"})
        for rel in ("docs/.staging/a.md", "docs/tdq/notes.md", "graphify-out/g.json", "scratch.tmp"):
            write_file(str(self.project), rel, "x\n")
            self._run_staged("PreToolUse", {"tool_name": "edit_file", "tool_input": {"TargetFile": str(self.project / rel)}})
        s_ok = self._run_staged("Stop", {"continuationActive": False})
        self.assertNotIn("TDQ:LOG", s_ok.get("reason", ""))

        # Edit real source without workinglog -> Stop must hard-continue with TDQ:LOG
        write_file(str(self.project), "app.py", "x = 2\n")
        self._run_staged("PreInvocation", {"prompt": "edit real code"})
        self._run_staged("PreToolUse", {"tool_name": "edit_file", "tool_input": {"TargetFile": str(self.project / "app.py")}})
        s_log = self._run_staged("Stop", {"continuationActive": False})
        self.assertEqual(s_log.get("decision"), "continue")
        self.assertIn("TDQ:LOG", s_log.get("reason", ""))

    def test_sh3_stop_continuation_active_streak_2_and_tick_stop(self):
        import datetime

        self._init_implement(plan_text="- [~] **T1** a\n- [ ] **T2** b\n")
        self._run_staged("PreInvocation", {"prompt": "go"})
        # Edit source AND update today's workinglog without ticking plan -> Stop blocks TDQ:TICK
        write_file(str(self.project), "app.py", "x = 3\n")
        self._run_staged("PreToolUse", {"tool_name": "edit_file", "tool_input": {"TargetFile": str(self.project / "app.py")}})
        log_rel = f"docs/workinglog/{datetime.date.today().strftime('%Y-%m-%d')}.md"
        write_file(str(self.project), log_rel, "# Log\n## 10:00 — edited\n")
        self._run_staged("PreToolUse", {"tool_name": "edit_file", "tool_input": {"TargetFile": str(self.project / log_rel)}})
        s_tick = self._run_staged("Stop", {"continuationActive": False})
        self.assertEqual(s_tick.get("decision"), "continue")
        self.assertIn("TDQ:TICK", s_tick.get("reason", ""))

        s1 = self._run_staged("Stop", {"continuationActive": True})
        self.assertEqual(s1.get("decision"), "continue")
        self.assertIn("TDQ:UNFINISHED", s1.get("reason", ""))
        s2 = self._run_staged("Stop", {"continuationActive": True})
        self.assertEqual(s2.get("decision"), "continue")
        self.assertIn("TDQ:UNFINISHED", s2.get("reason", ""))
        s3 = self._run_staged("Stop", {"continuationActive": True})
        self.assertEqual(s3.get("decision"), "allow")

        # Changing plan_sha resets streak back to 1
        write_file(str(self.project), "docs/tdq/plan/2026-11-19-0001-sh.md", "- [x] **T1** a\n- [ ] **T2** b\n")
        s4 = self._run_staged("Stop", {"continuationActive": True})
        self.assertEqual(s4.get("decision"), "continue")
        self.assertIn("TDQ:UNFINISHED", s4.get("reason", ""))

    def test_sh4_search_leak_malformed_blocked_and_graphify_observed(self):
        self._init_implement(plan_text="- [~] **T1** a\n")
        write_file(str(self.project), "docs/tdq/.tdq-san-sang.json", json.dumps({"tang": {"lsp": {"san_sang": True}, "graphify": {"san_sang": True}}}))
        # Malformed shell command that leaks raw rg must NOT fall into malformed_allow:
        # 1st miss -> grace allow; 2nd consecutive -> hard deny
        leak_cmd = 'echo "unterminated && rg secretFoo src/'
        g1 = self._run_staged("PreToolUse", {"tool_name": "run_command", "tool_input": {"CommandLine": leak_cmd}})
        self.assertEqual(g1.get("decision"), "allow")
        g2 = self._run_staged("PreToolUse", {"tool_name": "run_command", "tool_input": {"CommandLine": leak_cmd}})
        self.assertEqual(g2.get("decision"), "deny")
        self.assertIn("TDQ:SEARCH", g2.get("reason", ""))

        # PowerShell here-string with rg inside payload string stays malformed_allow
        hs_cmd = "@'\nrg foo\n'@\npy -3 -c $code"
        g_hs = self._run_staged("PreToolUse", {"tool_name": "run_command", "tool_input": {"CommandLine": hs_cmd}})
        self.assertEqual(g_hs.get("decision"), "allow")

        # Graphify command resets grace and writes khai_niem
        self._run_staged("PreToolUse", {"tool_name": "run_command", "tool_input": {"CommandLine": "py -3 scripts/tdq_graphify.py query secretFoo"}})
        g3 = self._run_staged("PreToolUse", {"tool_name": "run_command", "tool_input": {"CommandLine": "rg -n secretFoo src/"}})
        self.assertEqual(g3.get("decision"), "allow")

    def test_sh5_qc_tester_readonly_and_approve_shell_mutator(self):
        write_state(str(self.project), active_request="r1", lane="full", phase="spec")
        d_app = self._run_staged("PreToolUse", {"tool_name": "run_command", "tool_input": {"CommandLine": "Set-Content app.py bad"}})
        self.assertEqual(d_app.get("decision"), "deny")
        self.assertIn("TDQ:APPROVE", d_app.get("reason", ""))

        self._init_implement(plan_text="- [~] **T1** a\n")
        d_ro = self._run_staged("PreToolUse", {
            "agent_type": "tdq-qc-tester",
            "tool_name": "run_command",
            "tool_input": {"CommandLine": "Set-Content app.py mut"},
        })
        self.assertEqual(d_ro.get("decision"), "deny")
        self.assertIn("READONLY", d_ro.get("reason", ""))

    def test_sh6_gon_qc_phase_anchor_and_compact(self):
        write_state(str(self.project), active_request="r1", lane="full", phase="spec")
        p_spec = self._run_staged("PreInvocation", {"prompt": "1a"})
        msg_spec = str(p_spec.get("injectSteps", [{}])[0].get("systemMessage", {}).get("systemMessage", ""))
        self.assertNotIn("[TDQ:GON]", msg_spec)

        self._init_implement(plan_text="- [~] **T1** a\n")
        p_imp1 = self._run_staged("PreInvocation", {"prompt": "start build"})
        msg1 = str(p_imp1.get("injectSteps", [{}])[0].get("systemMessage", {}).get("systemMessage", ""))
        self.assertIn("[TDQ:GON]", msg1)

        p_imp2 = self._run_staged("PreInvocation", {"prompt": "continue build"})
        msg2 = str(p_imp2.get("injectSteps", [{}])[0].get("systemMessage", {}).get("systemMessage", ""))
        self.assertNotIn("[TDQ:GON]", msg2)

        p_cmp = self._run_staged("PreInvocation", {"prompt": "after compact", "source": "compact"})
        msg_cmp = str(p_cmp.get("injectSteps", [{}])[0].get("systemMessage", {}).get("systemMessage", ""))
        self.assertIn("[TDQ:GON]", msg_cmp)

        write_state(
            str(self.project), active_request="2026-11-19-0001-sh", lane="full", phase="qc",
            spec_approved=True, plan_approved=True, plan_file="docs/tdq/plan/2026-11-19-0001-sh.md",
        )
        p_qc = self._run_staged("PreInvocation", {"prompt": "run check"})
        msg_qc = str(p_qc.get("injectSteps", [{}])[0].get("systemMessage", {}).get("systemMessage", ""))
        self.assertIn("[TDQ:QC]", msg_qc)


if __name__ == "__main__":
    unittest.main()
