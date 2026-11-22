"""Red-Green tests for T2.2 setupfully prompt trigger, restart resume hooks, and Rust flag routing."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOOKS_SCRIPTS = ROOT / "hooks" / "scripts"
SCRIPTS_DIR = ROOT / "scripts"
RUST_DIR = ROOT / "hooks" / "rust" / "tdq-dispatch"
TOOLS_DIR = ROOT / "tools"

for p in (str(HOOKS_SCRIPTS), str(SCRIPTS_DIR), str(TOOLS_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

import tdq_setup_state


def _subproc_env(state_dir: Path, home: Path, extra: dict[str, str] | None = None) -> dict[str, str]:
    env = dict(os.environ)
    env.pop("PLUGIN_DATA", None)
    env.update({
        "HOME": str(home),
        "USERPROFILE": str(home),
        "GEMINI_CONFIG_DIR": str(home / ".gemini"),
        "TDQ_SETUP_STATE_DIR": str(state_dir),
        "TDQ_KHONG_CHAM_MAY": "1",
        "TDQ_LOG": "0",
        "TDQ_KHOI_TAO_NEN": "0",
    })
    if extra:
        env.update(extra)
    return env


def _run_hook_script(script_path: Path, event: str, payload: dict, cwd: Path, env: dict[str, str]) -> dict:
    kw: dict = {
        "cwd": str(cwd),
        "input": json.dumps(payload),
        "capture_output": True,
        "text": True,
        "encoding": "utf-8",
        "timeout": 15,
        "env": env,
    }
    if os.name == "nt":
        kw["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
    proc = subprocess.run([sys.executable, "-X", "utf8", str(script_path), "--event", event], check=False, **kw)
    assert proc.returncode == 0, f"{script_path.name} failed ({proc.returncode}): {proc.stderr}"
    raw = proc.stdout.strip()
    if not raw:
        return {}
    if raw.startswith("{"):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"plain": raw}
    return {"plain": raw}


def _extract_context_text(resp: dict) -> str:
    parts: list[str] = []
    if resp.get("plain"):
        parts.append(str(resp["plain"]))
    hso = resp.get("hookSpecificOutput") or {}
    if hso.get("additionalContext"):
        parts.append(str(hso["additionalContext"]))
    for step in resp.get("injectSteps") or []:
        if not isinstance(step, dict):
            continue
        sys_msg = step.get("systemMessage")
        if isinstance(sys_msg, dict):
            if sys_msg.get("systemMessage"):
                parts.append(str(sys_msg["systemMessage"]))
            meta = sys_msg.get("metadata") or {}
            if meta.get("user_markdown"):
                parts.append(str(meta["user_markdown"]))
        elif sys_msg:
            parts.append(str(sys_msg))
    for item in resp.get("inject") or []:
        if isinstance(item, dict):
            parts.append(str(item.get("model_text") or ""))
            parts.append(str(item.get("user_markdown") or ""))
    return "\n".join(p for p in parts if p)


def test_extract_setupfully_trigger_positive_and_guards():
    import prompt_context

    assert prompt_context.extract_setupfully_trigger("setupfully tdq-workflow") is True
    assert prompt_context.extract_setupfully_trigger("hãy setupfully tdq-workflow cho antigravity") is True
    assert prompt_context.extract_setupfully_trigger("SetupFully tdq-workflow!") is True

    # Questions, negations, quoted text, wrappers, and partial phrases must be rejected.
    for blocked in (
        "",
        "setup tdq-workflow",
        "setupfully tdq-workflow là gì?",
        "cách chạy setupfully tdq-workflow?",
        "không chạy setupfully tdq-workflow",
        "đừng setupfully tdq-workflow",
        "don't run setupfully tdq-workflow",
        "never setupfully tdq-workflow",
        '"setupfully tdq-workflow"',
        'the user said: "setupfully tdq-workflow"',
        "<system-reminder>setupfully tdq-workflow</system-reminder>",
        "<TDQ_WORKFLOW>setupfully tdq-workflow</TDQ_WORKFLOW>hello",
    ):
        assert prompt_context.extract_setupfully_trigger(blocked) is False, f"expected False for {blocked!r}"


def test_prompt_context_setupfully_and_restart_resume_flows(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    state_dir = tmp_path / "setup_state"
    home = tmp_path / "home"
    home.mkdir()
    env = _subproc_env(state_dir, home)
    pc_script = HOOKS_SCRIPTS / "prompt_context.py"

    # 1. Explicit setupfully prompt injects [TDQ:SETUP] on a clean machine
    resp_trigger = _run_hook_script(
        pc_script,
        "UserPromptSubmit",
        {"cwd": str(repo), "session_id": "s1", "prompt": "setupfully tdq-workflow"},
        repo,
        env,
    )
    ctx_trigger = _extract_context_text(resp_trigger)
    assert "[TDQ:SETUP]" in ctx_trigger
    assert "--setupfully" in ctx_trigger

    # 2. Subagent prompt must NEVER fire setupfully or restart resume
    resp_sub = _run_hook_script(
        pc_script,
        "PreInvocation",
        {
            "cwd": str(repo),
            "session_id": "s_sub",
            "agent_type": "tdq-explorer",
            "prompt": "setupfully tdq-workflow",
        },
        repo,
        env,
    )
    assert "[TDQ:SETUP]" not in _extract_context_text(resp_sub)

    # 3. awaiting_restart with SAME host fingerprint -> remind_restart (must not verify early)
    cur_fp = str(tdq_setup_state.compute_host_session_fingerprint().get("fingerprint") or "fp_same")
    tdq_setup_state.save_setup_state(
        {"status": "awaiting_restart", "host_fingerprint": cur_fp, "phase": 1},
        pending=True,
        data_dir=state_dir,
    )
    resp_same = _run_hook_script(
        pc_script,
        "UserPromptSubmit",
        {"cwd": str(repo), "session_id": "s2", "prompt": "hi"},
        repo,
        env,
    )
    ctx_same = _extract_context_text(resp_same)
    assert "[TDQ:SETUP]" in ctx_same
    assert "--post-restart-verify" not in ctx_same

    # 4. awaiting_restart with DIFFERENT host fingerprint -> run_verify & --post-restart-verify
    tdq_setup_state.save_setup_state(
        {"status": "awaiting_restart", "host_fingerprint": "old_ide_pid_0001", "phase": 1},
        pending=True,
        data_dir=state_dir,
    )
    resp_new = _run_hook_script(
        pc_script,
        "UserPromptSubmit",
        {"cwd": str(repo), "session_id": "s3", "prompt": "check setup"},
        repo,
        env,
    )
    ctx_new = _extract_context_text(resp_new)
    assert "[TDQ:SETUP]" in ctx_new
    assert "--post-restart-verify" in ctx_new
    assert tdq_setup_state.load_setup_state(data_dir=state_dir)["status"] == "validating_after_restart"


def test_session_start_reports_pending_setup_flag(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    state_dir = tmp_path / "setup_state"
    home = tmp_path / "home"
    home.mkdir()
    env = _subproc_env(state_dir, home)

    tdq_setup_state.save_setup_state(
        {"status": "awaiting_restart", "host_fingerprint": "old_fp_1234", "phase": 1},
        pending=True,
        data_dir=state_dir,
    )
    resp = _run_hook_script(
        HOOKS_SCRIPTS / "session_start.py",
        "SessionStart",
        {"cwd": str(repo), "session_id": "ss1", "source": "startup"},
        repo,
        env,
    )
    ctx = _extract_context_text(resp)
    assert "[TDQ:SETUP]" in ctx
    assert "restart" in ctx.lower() or "verify" in ctx.lower()


def test_compiled_agy_hooks_in_tmp_emit_user_markdown_and_setup_code(tmp_path: Path):
    from tools.patches import agy_hooks

    stage = tmp_path / "agy_stage"
    stage_hooks = stage / "hooks" / "scripts"
    stage_scripts = stage / "scripts"
    shutil.copytree(HOOKS_SCRIPTS, stage_hooks)
    shutil.copytree(SCRIPTS_DIR, stage_scripts)
    agy_hooks.apply_all(stage_hooks)

    pc_compiled = stage_hooks / "prompt_context.py"
    repo = tmp_path / "repo"
    repo.mkdir()
    state_dir = tmp_path / "state_dir"
    home = tmp_path / "home"
    home.mkdir()
    tdq_setup_state.save_setup_state(
        {"status": "awaiting_restart", "host_fingerprint": "old_pid_fp", "phase": 1},
        pending=True,
        data_dir=state_dir,
    )
    tpath = tmp_path / "transcript.jsonl"
    tpath.write_text(
        json.dumps({"type": "USER_INPUT", "source": "USER_EXPLICIT", "step_index": 1, "content": "hi"}) + "\n",
        encoding="utf-8",
    )
    env = _subproc_env(state_dir, home, {"PLUGIN_ROOT": str(stage)})
    resp = _run_hook_script(
        pc_compiled,
        "PreInvocation",
        {
            "cwd": str(repo),
            "session_id": "agy_s1",
            "lastUserInput": "hi",
            "transcriptPath": str(tpath),
        },
        repo,
        env,
    )
    steps = resp.get("injectSteps") or []
    matched = False
    for step in steps:
        if not isinstance(step, dict):
            continue
        sys_msg = step.get("systemMessage") or {}
        if not isinstance(sys_msg, dict):
            continue
        model_text = str(sys_msg.get("systemMessage") or "")
        user_md = str((sys_msg.get("metadata") or {}).get("user_markdown") or "")
        if "[TDQ:SETUP]" in model_text and "--post-restart-verify" in model_text and "[TDQ:SETUP]" in user_md:
            matched = True
            break
    assert matched, f"Expected compiled AGY PreInvocation injectSteps with user_markdown, got: {resp}"


def test_rust_unit_suite_and_parity_isolation():
    parity_text = (ROOT / "tests" / "test_rust_dispatch_parity.py").read_text(encoding="utf-8")
    assert 'pop("PLUGIN_DATA"' in parity_text, "test_rust_dispatch_parity._isolated_env must clear PLUGIN_DATA"

    wf_text = (ROOT / ".github" / "workflows" / "build-rust-hooks.yml").read_text(encoding="utf-8")
    assert "cargo test" in wf_text, "CI workflow must verify Rust unit tests before uploading binaries"

    kw: dict = {
        "cwd": str(ROOT),
        "capture_output": True,
        "text": True,
        "encoding": "utf-8",
        "timeout": 120,
    }
    if os.name == "nt":
        kw["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
    res = subprocess.run(
        ["cargo", "test", "--manifest-path", str(RUST_DIR / "Cargo.toml")],
        check=False,
        **kw,
    )
    assert res.returncode == 0, f"cargo test failed:\n{res.stdout}\n{res.stderr}"
