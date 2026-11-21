"""V3 Verification: Live cmd.exe /c dual-protocol hooks, 23 AGY TDQ:* codes, EC-01..EC-17."""
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent
PLUGIN_DIR = WORKSPACE / "plugins" / "tdq-workflow-agy"
HOOKS_DIR = PLUGIN_DIR / "hooks" / "scripts"
for _p in (str(PLUGIN_DIR / "scripts"), str(HOOKS_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)
_spec = importlib.util.spec_from_file_location("_agy_plugin_common", HOOKS_DIR / "_common.py")
_common = importlib.util.module_from_spec(_spec)
sys.modules["_agy_plugin_common"] = _common
_spec.loader.exec_module(_common)
_gg_spec = importlib.util.spec_from_file_location("_agy_plugin_gate_guidance", HOOKS_DIR / "gate_guidance.py")
_gate_guidance = importlib.util.module_from_spec(_gg_spec)
sys.modules["_agy_plugin_gate_guidance"] = _gate_guidance
_gg_spec.loader.exec_module(_gate_guidance)


EXPECTED_23_CODES = {
    "APPROVE", "GIT", "TEAM", "STATE", "READONLY", "VUNG", "ZERO-POPUP",
    "SUBAGENT", "UNFINISHED", "LSP", "SEARCH", "TICK", "DOC", "LOG",
    "OUTPUT", "SETUP", "GON", "NEXT", "WORKTREE", "ANCHOR", "DOD", "INTAKE",
    "PLAIN",
}
LEAN_REMOVED_CODES = {"ASK", "DEVTOOL", "FEEDBACK", "GATE", "QC", "RULE", "STUCK"}


def _init_git_repo(repo: Path) -> None:
    kw = {"cwd": str(repo), "capture_output": True, "text": True, "encoding": "utf-8", "timeout": 15}
    subprocess.run(["git", "init", "-b", "main"], check=True, **kw)
    subprocess.run(["git", "config", "user.email", "tdq@example.com"], check=True, **kw)
    subprocess.run(["git", "config", "user.name", "TDQ Tester"], check=True, **kw)
    (repo / "app.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    subprocess.run(["git", "add", "app.py"], check=True, **kw)
    subprocess.run(["git", "commit", "-m", "init"], check=True, **kw)


def _run_hook(script_name: str, payload: dict, event: str | None = None, cwd: Path = PLUGIN_DIR, extra_env=None):
    ev_flag = f"--event {event}" if event else ""
    cmd = f'cmd /c py -3 -X utf8 "{HOOKS_DIR / script_name}" {ev_flag}'.strip()
    env = dict(os.environ, TDQ_KHOI_TAO_NEN="0", TDQ_KHONG_CHAM_MAY="1", TDQ_LOG="0")
    if extra_env:
        env.update(extra_env)
    kw = {
        "cwd": str(cwd),
        "input": json.dumps(payload),
        "capture_output": True,
        "text": True,
        "encoding": "utf-8",
        "timeout": 20,
        "env": env,
    }
    if os.name == "nt":
        kw["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
    return subprocess.run(cmd, **kw)


def _state_cli(repo: Path, *args: str):
    kw = {"cwd": str(repo), "capture_output": True, "text": True, "encoding": "utf-8", "timeout": 20}
    return subprocess.run([sys.executable, "-X", "utf8", str(PLUGIN_DIR / "scripts" / "tdq_state.py"), *args], **kw)


def test_all_23_tdq_codes_registered():
    assert len(_common.CODES) == 23
    assert set(_common.CODES) == EXPECTED_23_CODES
    assert LEAN_REMOVED_CODES.isdisjoint(set(_common.CODES))
    assert set(_gate_guidance.ALL_AGY_CODES) == EXPECTED_23_CODES
    assert set(_gate_guidance.LEAN_REMOVED_CODES) == LEAN_REMOVED_CODES


def test_ec01_to_ec14_live_cmd_hooks(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo(repo)
    assert _state_cli(repo, "init", "2026-11-13-1200-test-ec", "express", "--bo-qua-lsp", "unit test").returncode == 0
    assert _state_cli(repo, "approve", "quick", "--by", "duyet nhanh", "--bo-qua-archify", "unit test").returncode == 0

    # EC-11: SessionStart emits valid AGY protojson {"injectSteps": [{"systemMessage": {"systemMessage": ...}}]}
    ss = _run_hook("session_start.py", {"cwd": str(repo), "conversation_id": "conv-ec", "source": "compact"}, event="SessionStart", cwd=repo)
    assert ss.returncode == 0
    ss_json = json.loads(ss.stdout.strip())
    assert "injectSteps" in ss_json
    assert "[TDQ:ANCHOR]" in ss_json["injectSteps"][0]["systemMessage"]["systemMessage"]

    # EC-10: question gate blocks ask_question popup with [TDQ:ZERO-POPUP]
    ak = _run_hook("ask_" + "gate.py", {"cwd": str(repo), "conversation_id": "conv-ec", "tool_name": "ask_question", "tool_input": {"questions": []}}, event="PreToolUse", cwd=repo)
    assert ak.returncode == 0
    ak_json = json.loads(ak.stdout.strip())
    assert ak_json["decision"] == "deny"
    assert "[TDQ:ZERO-POPUP]" in ak_json["reason"]

    # EC-01 + EC-14: step-0 transcriptPath marks subagent tdq-reviewer -> edit_gate denies [TDQ:READONLY]
    tr = tmp_path / "sub_transcript.jsonl"
    tr.write_text(json.dumps({"step_index": 0, "type": "USER_INPUT", "content": "You are tdq-reviewer checking spec."}) + "\n", encoding="utf-8")
    ed_ro = _run_hook(
        "edit_gate.py",
        {"cwd": str(repo), "conversation_id": "conv-rev", "transcriptPath": str(tr), "tool_name": "edit_file", "tool_input": {"TargetFile": str(repo / "app.py")}},
        event="PreToolUse",
        cwd=repo,
    )
    assert ed_ro.returncode == 0
    ed_ro_json = json.loads(ed_ro.stdout.strip())
    assert ed_ro_json["decision"] == "deny"
    assert "[TDQ:READONLY]" in ed_ro_json["reason"]

    # EC-02: subagent_dispatch_gate overwrites Workspace='inherit' for WORKTREE:; denies swarm
    sd = _run_hook(
        "subagent_dispatch_gate.py",
        {"cwd": str(repo), "conversation_id": "conv-ec", "tool_name": "invoke_subagent", "tool_input": {"Role": "tdq-implementer", "Workspace": "branch", "Prompt": "TASK: T1.1\nWORKTREE: C:/tmp/wt\n"}},
        event="PreToolUse",
        cwd=repo,
    )
    assert sd.returncode == 0
    assert json.loads(sd.stdout.strip()) == {"decision": "allow", "overwrite": {"Workspace": "inherit"}}

    sd_swarm = _run_hook(
        "subagent_dispatch_gate.py",
        {"cwd": str(repo), "conversation_id": "conv-ec", "tool_name": "swarm", "tool_input": {"action": "add"}},
        event="PreToolUse",
        cwd=repo,
    )
    assert sd_swarm.returncode == 0
    sd_swarm_json = json.loads(sd_swarm.stdout.strip())
    assert sd_swarm_json["decision"] == "deny"
    assert "[TDQ:SUBAGENT]" in sd_swarm_json["reason"]

    # EC-06: bash_gate blocks banned branch name AND PowerShell Set-Content on state.json
    bg_br = _run_hook("bash_gate.py", {"cwd": str(repo), "conversation_id": "conv-ec", "tool_name": "run_command", "tool_input": {"CommandLine": "git checkout -b claude-bad"}}, event="PreToolUse", cwd=repo)
    assert json.loads(bg_br.stdout.strip())["decision"] == "deny"
    bg_ps = _run_hook("bash_gate.py", {"cwd": str(repo), "conversation_id": "conv-ec", "tool_name": "run_command", "tool_input": {"CommandLine": "Set-Content -Path docs/tdq/state.json -Value '{}'"}}, event="PreToolUse", cwd=repo)
    assert json.loads(bg_ps.stdout.strip())["decision"] == "deny"

    # EC-07: search_observe unwraps call_mcp_tool(ServerName='lsp', ToolName='start_lsp') and emits {} on PostToolUse
    so = _run_hook(
        "search_observe.py",
        {"cwd": str(repo), "conversation_id": "conv-ec", "tool_name": "call_mcp_tool", "tool_input": {"ServerName": "lsp", "ToolName": "start_lsp", "Arguments": {"root_dir": str(repo)}}},
        event="PostToolUse",
        cwd=repo,
    )
    assert so.returncode == 0
    assert json.loads(so.stdout.strip()) == {}

    # EC-08: prompt_context emits [TDQ:NEXT] and 1-line [TDQ:GON], drops [TDQ:FEEDBACK], skips repeat mid-turn
    pc_payload = {"cwd": str(repo), "conversation_id": "conv-ec", "prompt": "cái này lỗi rồi sửa lại giúp tôi"}  # i18n-allow
    pc = _run_hook("prompt_context.py", pc_payload, event="PreInvocation", cwd=repo)
    assert pc.returncode == 0
    pc_msg = json.loads(pc.stdout.strip())["injectSteps"][0]["systemMessage"]["systemMessage"]
    assert "[TDQ:NEXT]" in pc_msg
    assert "[TDQ:FEEDBACK]" not in pc_msg
    assert "[TDQ:GON]" in pc_msg
    pc_mid = _run_hook("prompt_context.py", pc_payload, event="PreInvocation", cwd=repo)
    assert pc_mid.returncode == 0
    assert json.loads(pc_mid.stdout.strip()) == {}
    assert "same as last turn" not in pc_mid.stdout

    # EC-09: read_gate normalizes read_file StartLine/EndLine and emits {"decision": "allow"}
    rg = _run_hook("read_gate.py", {"cwd": str(repo), "conversation_id": "conv-ec", "tool_name": "read_file", "tool_input": {"AbsolutePath": str(repo / "app.py"), "StartLine": 1, "EndLine": 2}}, event="PreToolUse", cwd=repo)
    assert rg.returncode == 0
    assert json.loads(rg.stdout.strip())["decision"] == "allow"

    # EC-14: PostInvocation flushes any queued PreToolUse reminders via injectSteps + user_markdown
    _common.queue_remind(str(repo), {"conversation_id": "conv-q"}, "TEST", "[TDQ:TEST] run pytest")
    pi = _run_hook("post_invocation.py", {"cwd": str(repo), "conversation_id": "conv-q"}, event="PostInvocation", cwd=repo)
    pi_msg = json.loads(pi.stdout.strip())["injectSteps"][0]["systemMessage"]
    assert "[TDQ:TEST]" in pi_msg["systemMessage"]
    assert "[TDQ:TEST]" in pi_msg["metadata"]["user_markdown"]

    # EC-13: codex_edit_gate enforces TDQ_CODEX_VUNG [TDQ:VUNG] (lives in root hooks/ for Codex compat)
    cx = _run_hook(
        str(WORKSPACE / "hooks" / "scripts" / "codex_edit_gate.py"),
        {"cwd": str(repo), "tool_name": "apply_patch", "tool_input": {"command": "*** Update File: secret/out.py\n+x=1"}},
        cwd=repo,
        extra_env={"TDQ_CODEX_TASK": "T1.1", "TDQ_CODEX_VUNG": "app.py"},
    )
    assert "[TDQ:VUNG]" in cx.stdout

    # EC-03: stop_gate hard-blocks [TDQ:LOG] on AGY when real source changed without workinglog
    _run_hook("prompt_context.py", {"cwd": str(repo), "conversation_id": "conv-stop", "prompt": "check stop"}, event="PreInvocation", cwd=repo)
    (repo / "app.py").write_text("def add(a, b):\n    return a + b + 1\n", encoding="utf-8")
    sg = _run_hook("stop_gate.py", {"cwd": str(repo), "conversation_id": "conv-stop"}, event="Stop", cwd=repo)
    assert sg.returncode == 0
    sg_json = json.loads(sg.stdout.strip())
    assert sg_json["decision"] == "continue"
    assert "[TDQ:LOG]" in sg_json["reason"]

    # Backward compat: Claude Code payload (no --event, Claude tool names) still emits hookSpecificOutput
    ak_claude = _run_hook("ask_" + "gate.py", {"cwd": str(repo), "session_id": "claude-1", "tool_name": "AskUserQuestion", "tool_input": {}}, event=None, cwd=repo)
    assert ak_claude.returncode == 0
    if ak_claude.stdout.strip():
        assert "hookSpecificOutput" in ak_claude.stdout


def test_ec15_protojson_toolcall_workspacepaths_and_terminal_stop(tmp_path):
    repo = tmp_path / "repo_proto"
    repo.mkdir()
    _init_git_repo(repo)
    assert _state_cli(repo, "init", "2026-11-14-0400-test-proto", "express", "--bo-qua-lsp", "unit test").returncode == 0
    assert _state_cli(repo, "approve", "quick", "--by", "duyet nhanh", "--bo-qua-archify", "unit test").returncode == 0

    # SessionStart with file:// workspacePaths returns strict protojson injectSteps
    ss = _run_hook(
        "session_start.py",
        {"workspacePaths": [repo.as_uri()], "conversation_id": "conv-proto", "source": "resume"},
        event="SessionStart",
        cwd=PLUGIN_DIR,
    )
    assert ss.returncode == 0
    ss_json = json.loads(ss.stdout.strip())
    assert "additionalContext" not in ss_json
    assert "[TDQ:ANCHOR]" in ss_json["injectSteps"][0]["systemMessage"]["systemMessage"]

    # EC-02 + EC-15 guard: unticked plan (0 [~]) hard-denies edit_gate on AGY with 4-part [TDQ:TICK]
    plan_file = repo / "docs" / "tdq" / "plan" / "2026-11-14-0400-test-proto.md"
    plan_file.parent.mkdir(parents=True, exist_ok=True)
    plan_file.write_text("- [ ] **T1.1**: Unticked item\n", encoding="utf-8")
    assert _state_cli(repo, "set", "plan_file=docs/tdq/plan/2026-11-14-0400-test-proto.md", "phase=implement").returncode == 0
    assert not (repo / "docs" / "workinglog").exists()
    eg = _run_hook(
        "edit_gate.py",
        {
            "workspacePaths": [repo.as_uri()],
            "conversationId": "conv-proto",
            "toolCall": {"name": "edit_file", "args": {"TargetFile": str(repo / "unticked.py")}},
        },
        event="PreToolUse",
        cwd=PLUGIN_DIR,
    )
    assert eg.returncode == 0
    eg_json = json.loads(eg.stdout.strip())
    assert eg_json["decision"] == "deny"
    assert "[TDQ:TICK]" in eg_json["reason"]
    assert "Chuyện gì" in eg_json["reason"] and "Làm gì" in eg_json["reason"]  # i18n-allow

    # PreToolUse with nested toolCall.args.CommandLine + workspacePaths blocks banned branch name
    bg = _run_hook(
        "bash_gate.py",
        {
            "workspacePaths": [str(repo)],
            "conversation_id": "conv-proto",
            "toolCall": {"name": "run_command", "args": {"CommandLine": "git checkout -b gemini-bad"}},
        },
        event="PreToolUse",
        cwd=PLUGIN_DIR,
    )
    assert bg.returncode == 0
    assert json.loads(bg.stdout.strip())["decision"] == "deny"

    # PreInvocation with lastUserInput fallback emits [TDQ:NEXT], drops [TDQ:FEEDBACK], skips repeat mid-turn
    pc_proto = {"workspacePaths": [str(repo)], "conversation_id": "conv-proto", "lastUserInput": "cái này lỗi rồi sửa lại"}  # i18n-allow
    pc = _run_hook("prompt_context.py", pc_proto, event="PreInvocation", cwd=PLUGIN_DIR)
    assert pc.returncode == 0
    pc_proto_msg = json.loads(pc.stdout.strip())["injectSteps"][0]["systemMessage"]["systemMessage"]
    assert "[TDQ:NEXT]" in pc_proto_msg
    assert "[TDQ:FEEDBACK]" not in pc_proto_msg
    pc_proto_mid = _run_hook("prompt_context.py", pc_proto, event="PreInvocation", cwd=PLUGIN_DIR)
    assert pc_proto_mid.returncode == 0
    assert json.loads(pc_proto_mid.stdout.strip()) == {}

    # Stop with USER_CANCELED emits allow and marks turn_closed=True
    (repo / "app.py").write_text("def add(a, b):\n    return a + b + 99\n", encoding="utf-8")
    sg = _run_hook(
        "stop_gate.py",
        {"workspacePaths": [str(repo)], "conversation_id": "conv-proto", "terminationReason": "USER_CANCELED"},
        event="Stop",
        cwd=PLUGIN_DIR,
    )
    assert sg.returncode == 0
    assert json.loads(sg.stdout.strip())["decision"] == "allow"
    assert _common.read_turn_meta(str(repo), "conv-proto").get("turn_closed") is True

    # On analyze phase, modified repo without workinglog hard-blocks Stop with [TDQ:LOG]
    assert _state_cli(repo, "set", "phase=analyze").returncode == 0
    sg_log = _run_hook(
        "stop_gate.py",
        {"workspacePaths": [str(repo)], "conversation_id": "conv-proto"},
        event="Stop",
        cwd=PLUGIN_DIR,
    )
    assert sg_log.returncode == 0
    sg_log_json = json.loads(sg_log.stdout.strip())
    assert sg_log_json["decision"] == "continue"
    assert "[TDQ:LOG]" in sg_log_json["reason"]

    # On implement phase with open tasks (clean turn), Stop enforces MAX_STREAK_AGY=2 across continuationActive
    assert _state_cli(repo, "set", "phase=implement").returncode == 0
    assert _run_hook(
        "prompt_context.py",
        {"workspacePaths": [str(repo)], "conversation_id": "conv-proto-unf", "prompt": "check unfinished stop"},
        event="PreInvocation",
        cwd=PLUGIN_DIR,
    ).returncode == 0
    for extra in ({}, {"continuationActive": True}):
        sg_block = _run_hook(
            "stop_gate.py",
            {"workspacePaths": [str(repo)], "conversation_id": "conv-proto-unf", **extra},
            event="Stop",
            cwd=PLUGIN_DIR,
        )
        assert sg_block.returncode == 0
        sg_block_json = json.loads(sg_block.stdout.strip())
        assert sg_block_json["decision"] == "continue"
        assert "[TDQ:UNFINISHED]" in sg_block_json["reason"]

    sg_cont = _run_hook(
        "stop_gate.py",
        {"workspacePaths": [str(repo)], "conversation_id": "conv-proto-unf", "continuationActive": True},
        event="Stop",
        cwd=PLUGIN_DIR,
    )
    assert sg_cont.returncode == 0
    assert json.loads(sg_cont.stdout.strip()) == {"decision": "allow"}
    assert _common.read_turn_meta(str(repo), "conv-proto-unf").get("turn_closed") is True
    unf_model, _ = _common.flush_pending_channels(str(repo), "conv-proto-unf")
    assert "[TDQ:UNFINISHED]" in unf_model

    # Claude compat backward-check for edit_gate [TDQ:TICK] block (guards _tick_notify recursion)
    log_file = repo / _common.tdq_state.today_log_rel()
    log_file.parent.mkdir(parents=True, exist_ok=True)
    log_file.write_text("# log\n", encoding="utf-8")
    eg_claude = _run_hook(
        "edit_gate.py",
        {"cwd": str(repo), "session_id": "claude-tick", "tool_name": "Edit", "tool_input": {"file_path": str(repo / "app.py")}},
        event=None,
        cwd=PLUGIN_DIR,
    )
    assert eg_claude.returncode == 0
    eg_claude_json = json.loads(eg_claude.stdout.strip())
    assert eg_claude_json["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "[TDQ:TICK]" in eg_claude_json["hookSpecificOutput"]["permissionDecisionReason"]


def test_ec16_lsp_gate_mcp_routing_and_empty_args(tmp_path):
    """EC-16: Compiled plugin lsp_gate allows Chrome/Tavily/LSP queries/other_lsp, denies empty start_lsp."""
    repo = tmp_path / "repo_lsp"
    repo.mkdir()
    _init_git_repo(repo)
    (repo / "docs" / "tdq").mkdir(parents=True, exist_ok=True)
    (repo / "docs" / "tdq" / ".tdq-lsp-module.json").write_text(
        json.dumps({"module": {"python:.": {"lang": "python", "goc": "."}}}),
        encoding="utf-8",
    )

    allow_cases = [
        ("chrome-devtools", "select_page", {"bringToFront": True, "pageId": 1}),
        ("chrome-devtools", "list_pages", {}),
        ("chrome-devtools", "click", {"pageId": 1, "uid": "btn-1", "dblClick": False}),
        ("chrome-devtools", "navigate_page", {"pageId": 1, "type": "url", "url": "https://example.com"}),
        ("tdq-workflow-agy_tavily-primary", "tavily_search", {"query": "tdq workflow"}),
        ("tdq-workflow-agy_lsp", "find_references", {"file_path": "app.py", "line": 1, "character": 1}),
        ("other_lsp", "start_lsp", {"root_dir": str(repo)}),
    ]
    for srv, tool, args in allow_cases:
        res = _run_hook(
            "lsp_gate.py",
            {
                "workspacePaths": [str(repo)],
                "conversation_id": "conv-ec16",
                "tool_name": "call_mcp_tool",
                "tool_input": {"ServerName": srv, "ToolName": tool, "Arguments": args},
            },
            event="PreToolUse",
            cwd=PLUGIN_DIR,
        )
        assert res.returncode == 0
        assert json.loads(res.stdout.strip())["decision"] == "allow", (srv, tool, res.stdout)

    overwrite_cases = [
        ({}, False),
        ("{}", True),
        (json.dumps(json.dumps({"root_dir": str(repo)})), True),
    ]
    for raw_args, expect_str in overwrite_cases:
        ov_res = _run_hook(
            "lsp_gate.py",
            {
                "workspacePaths": [str(repo)],
                "conversation_id": "conv-ec16",
                "tool_name": "call_mcp_tool",
                "tool_input": {
                    "ServerName": "tdq-workflow-agy_lsp",
                    "ToolName": "start_lsp",
                    "Arguments": raw_args,
                },
            },
            event="PreToolUse",
            cwd=PLUGIN_DIR,
        )
        assert ov_res.returncode == 0
        body = json.loads(ov_res.stdout.strip())
        assert body["decision"] == "allow", (raw_args, body)
        ov_args = body["overwrite"]["Arguments"]
        assert isinstance(ov_args, str) is expect_str
        decoded = json.loads(ov_args) if expect_str else ov_args
        assert decoded["language_id"] == "python"

    # When project language cannot be determined in O(1), empty start_lsp still denies [TDQ:LSP]
    unknown_repo = tmp_path / "repo_lsp_unknown"
    unknown_repo.mkdir()
    _init_git_repo(unknown_repo)
    deny_res = _run_hook(
        "lsp_gate.py",
        {
            "workspacePaths": [str(unknown_repo)],
            "conversation_id": "conv-ec16-deny",
            "tool_name": "call_mcp_tool",
            "tool_input": {
                "ServerName": "tdq-workflow-agy_lsp",
                "ToolName": "start_lsp",
                "Arguments": "{}",
            },
        },
        event="PreToolUse",
        cwd=PLUGIN_DIR,
    )
    assert deny_res.returncode == 0
    deny_body = json.loads(deny_res.stdout.strip())
    assert deny_body["decision"] == "deny"
    assert "[TDQ:LSP]" in deny_body["reason"]

    broken_res = _run_hook(
        "lsp_gate.py",
        {
            "workspacePaths": [str(repo)],
            "conversation_id": "conv-ec16",
            "tool_name": "call_mcp_tool",
            "tool_input": {
                "ServerName": "tdq-workflow-agy_lsp",
                "ToolName": "start_lsp",
                "Arguments": "{broken",
            },
        },
        event="PreToolUse",
        cwd=PLUGIN_DIR,
    )
    assert broken_res.returncode == 0
    assert json.loads(broken_res.stdout.strip())["decision"] == "allow"


def _make_fake_rtk_shim(bin_dir: Path) -> None:
    """Create an isolated fake rtk binary supporting --version, gain, and rewrite."""
    bin_dir.mkdir(parents=True, exist_ok=True)
    impl_src = (
        "import sys\n"
        "args = sys.argv[1:]\n"
        "if args == ['--version']:\n"
        "    print('rtk 0.30.0')\n"
        "elif args == ['gain']:\n"
        "    print('total saved: 0')\n"
        "elif len(args) >= 2 and args[0] == 'rewrite':\n"
        "    cmd = args[2] if args[1] == '--' and len(args) >= 3 else args[1]\n"
        "    if cmd.startswith('git '):\n"
        "        print('rtk ' + cmd)\n"
        "        sys.exit(3)\n"
        "    sys.exit(1)\n"
    )
    if os.name == "nt":
        from pip._vendor.distlib.scripts import ScriptMaker

        launcher = ScriptMaker(None, str(bin_dir))._get_launcher("t")
        zbuf = io.BytesIO()
        with zipfile.ZipFile(zbuf, "w") as zf:
            zf.writestr("__main__.py", impl_src)
        shebang = f"#!{sys.executable}\n".encode("utf-8")
        (bin_dir / "rtk.exe").write_bytes(launcher + shebang + zbuf.getvalue())
    else:
        helper_py = bin_dir / "fake_rtk_impl.py"
        helper_py.write_text(impl_src, encoding="utf-8")
        shim = bin_dir / "rtk"
        shim.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{helper_py}" "$@"\n', encoding="utf-8")
        os.chmod(shim, 0o755)


def test_ec17_command_gate_rtk_collapse_and_setup_notice(tmp_path):
    """EC-17: Compiled command_gate collapses search+bash+rtk, and session_start emits [TDQ:SETUP] once."""
    repo = tmp_path / "repo_ec17"
    repo.mkdir()
    _init_git_repo(repo)

    fake_home = tmp_path / "fake_home"
    fake_home.mkdir()
    fake_bin = tmp_path / "fake_bin"
    _make_fake_rtk_shim(fake_bin)

    base_paths = [os.path.dirname(sys.executable)]
    for tool_name in ("py", "cmd", "git"):
        found = shutil.which(tool_name)
        if found:
            tool_dir = os.path.dirname(found)
            if tool_dir not in base_paths:
                base_paths.append(tool_dir)
    if os.name == "nt":
        sys_root = os.environ.get("SystemRoot", r"C:\Windows")
        for win_dir in (sys_root, os.path.join(sys_root, "System32")):
            if win_dir not in base_paths:
                base_paths.append(win_dir)
    else:
        for posix_dir in ("/usr/bin", "/bin"):
            if posix_dir not in base_paths:
                base_paths.append(posix_dir)
    clean_path = os.pathsep.join(base_paths)

    isolated_env = {
        "HOME": str(fake_home),
        "USERPROFILE": str(fake_home),
        "APPDATA": str(fake_home / "AppData" / "Roaming"),
        "LOCALAPPDATA": str(fake_home / "AppData" / "Local"),
        "XDG_CONFIG_HOME": str(fake_home / ".config"),
        "TDQ_RTK_BIN": "",
        "PATH": clean_path,
    }
    rtk_env = {**isolated_env, "PATH": str(fake_bin) + os.pathsep + clean_path}

    # 1. rtk bypass grep foo src/ -> denied by collapsed search_gate with [TDQ:SEARCH]
    bypass_res = _run_hook(
        "command_gate.py",
        {
            "workspacePaths": [str(repo)],
            "conversation_id": "conv-ec17-search",
            "tool_name": "run_command",
            "tool_input": {"CommandLine": "rtk bypass grep foo src/"},
        },
        event="PreToolUse",
        cwd=PLUGIN_DIR,
        extra_env=rtk_env,
    )
    assert bypass_res.returncode == 0
    bypass_body = json.loads(bypass_res.stdout.strip())
    assert bypass_body["decision"] == "deny"
    assert "[TDQ:SEARCH]" in bypass_body["reason"]
    assert "overwrite" not in bypass_body

    # 2. git checkout -b claude-bad -> [TDQ:GIT] recorded in turn ledger & denied on AGY PreToolUse
    bad_branch_cmd = "git checkout -b " + "claude" + "-bad"
    git_res = _run_hook(
        "command_gate.py",
        {
            "workspacePaths": [str(repo)],
            "conversation_id": "conv-ec17-git",
            "tool_name": "run_command",
            "tool_input": {"CommandLine": bad_branch_cmd},
        },
        event="PreToolUse",
        cwd=PLUGIN_DIR,
        extra_env=rtk_env,
    )
    assert git_res.returncode == 0
    git_body = json.loads(git_res.stdout.strip())
    assert git_body["decision"] == "deny"
    assert "[TDQ:GIT]" in git_body["reason"]
    assert "overwrite" not in git_body
    git_rows = _common.turn_rows(str(repo), {"cwd": str(repo), "conversation_id": "conv-ec17-git"})
    assert any(r.get("kind") == "block" and r.get("code") == "GIT" for r in git_rows)

    # 3. git status with fake rtk shim -> allow + overwrite.CommandLine = "rtk git status"
    status_res = _run_hook(
        "command_gate.py",
        {
            "workspacePaths": [str(repo)],
            "conversation_id": "conv-ec17-rtk",
            "tool_name": "run_command",
            "tool_input": {"CommandLine": "git status"},
        },
        event="PreToolUse",
        cwd=PLUGIN_DIR,
        extra_env=rtk_env,
    )
    assert status_res.returncode == 0
    assert json.loads(status_res.stdout.strip()) == {
        "decision": "allow",
        "overwrite": {"CommandLine": "rtk git status"},
    }

    # 4. Compiled session_start.py without rtk on PATH emits [TDQ:SETUP] --with-rtk once, skips when muted
    ss1 = _run_hook(
        "session_start.py",
        {"workspacePaths": [str(repo)], "conversation_id": "conv-ec17-ss1"},
        event="SessionStart",
        cwd=PLUGIN_DIR,
        extra_env=isolated_env,
    )
    assert ss1.returncode == 0
    msg1 = json.loads(ss1.stdout.strip())["injectSteps"][0]["systemMessage"]["systemMessage"]
    assert "[TDQ:SETUP]" in msg1
    assert "--with-rtk" in msg1

    ss2 = _run_hook(
        "session_start.py",
        {"workspacePaths": [str(repo)], "conversation_id": "conv-ec17-ss1"},
        event="SessionStart",
        cwd=PLUGIN_DIR,
        extra_env=isolated_env,
    )
    assert ss2.returncode == 0
    msg2 = json.loads(ss2.stdout.strip())["injectSteps"][0]["systemMessage"]["systemMessage"]
    assert "--with-rtk" not in msg2

    prefs_file = fake_home / ".gemini" / "config" / "tdq-rtk-prefs.json"
    prefs_file.parent.mkdir(parents=True, exist_ok=True)
    prefs_file.write_text(json.dumps({"mute_prompt": True}) + "\n", encoding="utf-8")
    ss_muted = _run_hook(
        "session_start.py",
        {"workspacePaths": [str(repo)], "conversation_id": "conv-ec17-ss2"},
        event="SessionStart",
        cwd=PLUGIN_DIR,
        extra_env=isolated_env,
    )
    assert ss_muted.returncode == 0
    msg_muted = json.loads(ss_muted.stdout.strip())["injectSteps"][0]["systemMessage"]["systemMessage"]
    assert "--with-rtk" not in msg_muted
