"""End-to-end verification of Antigravity R1-R3 dispatch, 4-part guidance, TDQ_LOG."""
import importlib.util
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent
PLUGIN_DIR = WORKSPACE / "plugins" / "tdq-workflow-agy"
DISPATCH_PY = PLUGIN_DIR / "hooks" / "scripts" / "dispatch.py"
STATE_PY = PLUGIN_DIR / "scripts" / "tdq_state.py"
CODEX_GATE_PY = WORKSPACE / "hooks" / "scripts" / "codex_edit_gate.py"
GUIDANCE_PY = PLUGIN_DIR / "hooks" / "scripts" / "gate_guidance.py"

FOUR_PART_LABELS = (
    "Chuyện gì",  # i18n-allow
    "Vì sao",  # i18n-allow
    "Làm gì",  # i18n-allow
    "Bỏ qua",  # i18n-allow
)
ISO_LOG_RE = re.compile(r"^\[\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\]")


def _load_gate_guidance():
    """Load compiled gate_guidance module directly from the AGY plugin."""
    spec = importlib.util.spec_from_file_location("agy_gate_guidance_test", GUIDANCE_PY)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _init_git_repo(repo: Path) -> None:
    """Create a clean isolated git repository with an initial commit."""
    repo.mkdir(parents=True, exist_ok=True)
    kw = {
        "cwd": str(repo),
        "capture_output": True,
        "text": True,
        "encoding": "utf-8",
        "timeout": 15,
    }
    subprocess.run(["git", "init", "-b", "main"], check=True, **kw)
    subprocess.run(["git", "config", "user.email", "tdq@example.com"], check=True, **kw)
    subprocess.run(["git", "config", "user.name", "TDQ Tester"], check=True, **kw)
    (repo / "app.py").write_text(
        "def add(a: int, b: int) -> int:\n    return a + b\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "add", "app.py"], check=True, **kw)
    subprocess.run(["git", "commit", "-m", "init"], check=True, **kw)


def _build_env(
    repo: Path,
    fake_home: Path,
    keep_tdq_log: bool = False,
    extra_env: dict[str, str] | None = None,
) -> dict[str, str]:
    """Build isolated subprocess environment anchored to tmp_path without home leaks."""
    fake_home.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    py_dir = os.path.dirname(sys.executable)
    env["PATH"] = py_dir + os.pathsep + env.get("PATH", "")
    env.update({
        "HOME": str(fake_home),
        "USERPROFILE": str(fake_home),
        "APPDATA": str(fake_home / "AppData" / "Roaming"),
        "LOCALAPPDATA": str(fake_home / "AppData" / "Local"),
        "XDG_CONFIG_HOME": str(fake_home / ".config"),
        "GEMINI_CONFIG_DIR": str(fake_home / ".gemini"),
        "TDQ_PROJECT_DIR": str(repo),
        "TDQ_KHONG_CHAM_MAY": "1",
        "TDQ_KHOI_TAO_NEN": "0",
        "TDQ_RTK": "0",
        "RTK_DISABLED": "1",
    })
    if keep_tdq_log:
        env.pop("TDQ_LOG", None)
    else:
        env["TDQ_LOG"] = "0"
    if extra_env:
        env.update(extra_env)
    return env


def _run_state_cli(
    repo: Path, fake_home: Path, *args: str
) -> subprocess.CompletedProcess[str]:
    """Run compiled tdq_state.py CLI against isolated repo."""
    kw = {
        "cwd": str(repo),
        "capture_output": True,
        "text": True,
        "encoding": "utf-8",
        "timeout": 20,
        "env": _build_env(repo, fake_home),
    }
    if os.name == "nt":
        kw["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
    return subprocess.run(["python", "-X", "utf8", str(STATE_PY), *args], **kw)


def _run_dispatch(
    event: str,
    payload: dict | str,
    repo: Path,
    fake_home: Path,
    keep_tdq_log: bool = False,
    extra_env: dict[str, str] | None = None,
) -> tuple[subprocess.CompletedProcess[str], dict, float]:
    """Invoke compiled dispatch.py via `python -X utf8` and parse stdout JSON."""
    raw_in = payload if isinstance(payload, str) else json.dumps(
        payload, ensure_ascii=False
    )
    env = _build_env(repo, fake_home, keep_tdq_log=keep_tdq_log, extra_env=extra_env)
    kw = {
        "cwd": str(repo),
        "input": raw_in,
        "capture_output": True,
        "text": True,
        "encoding": "utf-8",
        "timeout": 20,
        "env": env,
    }
    if os.name == "nt":
        kw["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
    t0 = time.perf_counter()
    proc = subprocess.run(
        ["python", "-X", "utf8", str(DISPATCH_PY), "--event", event],
        **kw,
    )
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    assert proc.returncode == 0, (
        f"{event} failed rc={proc.returncode}: stderr={proc.stderr!r}"
    )
    out = json.loads(proc.stdout.strip()) if proc.stdout.strip() else {}
    return proc, out, elapsed_ms


def _read_jsonl(path: Path) -> list[dict]:
    """Read valid JSON lines from a ledger file."""
    if not path.is_file():
        return []
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _assert_four_parts(text: str, code: str) -> None:
    """Assert text carries [TDQ:<CODE>] and all four Vietnamese guidance sections."""
    assert f"[TDQ:{code}]" in text, f"Missing [TDQ:{code}] in {text!r}"
    for label in FOUR_PART_LABELS:
        assert label in text, f"Missing label {label!r} for [TDQ:{code}] in {text!r}"


def _assert_flushed_dual_channel(
    out: dict, expected_codes: tuple[str, ...]
) -> tuple[str, str]:
    """Assert injectSteps carries model summary <= 200 and user_markdown > 200."""
    steps = out.get("injectSteps") or []
    assert len(steps) == 1
    msg_obj = steps[0]["systemMessage"]
    model_text = msg_obj["systemMessage"]
    user_md = msg_obj["metadata"]["user_markdown"]
    assert model_text
    assert len(model_text) <= 200
    assert user_md
    assert 200 < len(user_md) <= 1200
    for code in expected_codes:
        assert f"[TDQ:{code}]" in model_text or f"[TDQ:{code}]" in user_md
        assert f"[TDQ:{code}]" in user_md
    for label in FOUR_PART_LABELS:
        assert label in user_md
    return model_text, user_md


def _setup_implement_repo(
    tmp_path: Path,
    name: str,
    slug: str,
    plan_body: str,
    lane: str = "express",
    impl_mode: str = "main",
) -> tuple[Path, Path]:
    """Initialize a repo with state.json in phase=implement and a plan file."""
    repo = tmp_path / name
    fake_home = tmp_path / f"{name}_home"
    _init_git_repo(repo)
    assert _run_state_cli(
        repo, fake_home, "init", slug, lane, "--bo-qua-lsp", "unit test"
    ).returncode == 0
    if lane == "express":
        assert _run_state_cli(
            repo, fake_home, "approve", "quick", "--by", "duyet nhanh",
            "--bo-qua-archify", "unit test",
        ).returncode == 0
    else:
        spec_rel = f"docs/tdq/spec/{slug}.md"
        spec_path = repo / spec_rel
        spec_path.parent.mkdir(parents=True, exist_ok=True)
        spec_path.write_text("# Spec\n", encoding="utf-8")
        assert _run_state_cli(
            repo, fake_home, "set", f"spec_file={spec_rel}"
        ).returncode == 0
        assert _run_state_cli(
            repo, fake_home, "approve", "spec", "--by", "duyet spec",
            "--bo-qua-archify", "unit test",
        ).returncode == 0
    plan_rel = f"docs/tdq/plan/{slug}.md"
    plan_path = repo / plan_rel
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text(plan_body, encoding="utf-8")
    assert _run_state_cli(
        repo, fake_home, "set", f"plan_file={plan_rel}",
        "phase=implement", f"implement_mode={impl_mode}",
    ).returncode == 0
    if lane != "express":
        assert _run_state_cli(
            repo, fake_home, "approve", "plan", "--mode", impl_mode,
            "--by", "duyet plan", "--bo-qua-archify", "unit test",
        ).returncode == 0
    return repo, fake_home


def test_r1_turn_detection_repeated_1a_and_no_midturn_git(tmp_path: Path) -> None:
    """Verify R1 turn detection, repeated '1a', 0 mid-turn git, and already_reminded."""
    repo = tmp_path / "repo_r1"
    fake_home = tmp_path / "home_r1"
    _init_git_repo(repo)
    slug = "2026-11-18-1200-r1-turn"
    assert _run_state_cli(
        repo, fake_home, "init", slug, "deep", "--bo-qua-lsp", "unit test"
    ).returncode == 0
    spec_path = repo / "docs" / "tdq" / "spec" / f"{slug}.md"
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    spec_path.write_text("# Spec R1\n", encoding="utf-8")
    assert _run_state_cli(
        repo, fake_home, "set", "phase=spec", f"spec_file=docs/tdq/spec/{slug}.md"
    ).returncode == 0

    sid = "conv-r1"
    transcript = tmp_path / "transcript.jsonl"
    step1 = {
        "step_index": 1,
        "type": "USER_INPUT",
        "created_at": "2026-11-18T10:00:00Z",
        "content": "1a",
    }
    transcript.write_text(json.dumps(step1) + "\n", encoding="utf-8")

    base_pre = {
        "cwd": str(repo),
        "conversation_id": sid,
        "transcriptPath": str(transcript),
        "prompt": "1a",
    }
    trace1 = tmp_path / "git_turn1.trace"
    _, out1, _ = _run_dispatch(
        "PreInvocation", base_pre, repo, fake_home, extra_env={"GIT_TRACE": str(trace1)}
    )
    msg1 = out1["injectSteps"][0]["systemMessage"]["systemMessage"]
    assert "[TDQ:APPROVE]" in msg1
    assert "[TDQ:GON]" not in msg1
    assert "same as last turn" not in msg1
    assert trace1.is_file() and trace1.read_text(encoding="utf-8").strip()

    runtime_dir = repo / "docs" / "tdq" / ".tdq-runtime"
    meta_path = runtime_dir / f"turn-meta-{sid}.json"
    meta1 = json.loads(meta_path.read_text(encoding="utf-8"))
    assert meta1["last_user_sig"] == "ui:1:2026-11-18T10:00:00Z"
    assert meta1["turn_closed"] is False

    # Create per-turn shard entry via PreToolUse soft reminder [TDQ:OUTPUT], then flush
    cmd_payload = {
        "cwd": str(repo),
        "conversation_id": sid,
        "tool_name": "run_command",
        "tool_input": {"CommandLine": "cat app.py"},
    }
    _, cmd_out1, _ = _run_dispatch("PreToolUse", cmd_payload, repo, fake_home)
    assert cmd_out1 == {"decision": "allow"}
    turns_path = runtime_dir / f"turns-{sid}.jsonl"
    assert turns_path.is_file()
    assert any(
        r.get("kind") == "remind" and r.get("code") == "OUTPUT"
        for r in _read_jsonl(turns_path)
    )
    _run_dispatch(
        "PostInvocation", {"cwd": str(repo), "conversation_id": sid}, repo, fake_home
    )

    turn_ledger = repo / "docs" / "tdq" / ".tdq-turn.jsonl"
    turn_starts_before = [
        r for r in _read_jsonl(turn_ledger) if r.get("kind") == "turn_start"
    ]
    assert len(turn_starts_before) == 1
    turns_before = _read_jsonl(turns_path)

    # Mid-turn PreInvocation: 0 git calls, keeps turns shard, no GON or repeat text
    trace_mid = tmp_path / "git_mid.trace"
    _, out_mid, _ = _run_dispatch(
        "PreInvocation",
        base_pre,
        repo,
        fake_home,
        extra_env={"GIT_TRACE": str(trace_mid)},
    )
    assert out_mid == {}
    assert not trace_mid.exists()
    assert turns_path.is_file()
    assert _read_jsonl(turns_path) == turns_before
    turn_starts_mid = [
        r for r in _read_jsonl(turn_ledger) if r.get("kind") == "turn_start"
    ]
    assert turn_starts_mid == turn_starts_before

    # Mid-turn repeat of same soft trigger must not spam pending-reminders again
    _, cmd_out2, _ = _run_dispatch("PreToolUse", cmd_payload, repo, fake_home)
    assert cmd_out2 == {"decision": "allow"}
    assert not (runtime_dir / f"pending-reminders-{sid}.jsonl").exists()

    # Append NEW USER_INPUT step with identical text "1a" -> recognized as new user turn
    step2 = {
        "step_index": 2,
        "type": "USER_INPUT",
        "created_at": "2026-11-18T10:01:00Z",
        "content": "1a",
    }
    with transcript.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(step2) + "\n")
    trace2 = tmp_path / "git_turn2.trace"
    _, out2, _ = _run_dispatch(
        "PreInvocation", base_pre, repo, fake_home, extra_env={"GIT_TRACE": str(trace2)}
    )
    msg2 = out2["injectSteps"][0]["systemMessage"]["systemMessage"]
    assert "[TDQ:APPROVE]" in msg2
    assert trace2.is_file() and trace2.read_text(encoding="utf-8").strip()
    meta2 = json.loads(meta_path.read_text(encoding="utf-8"))
    assert meta2["last_user_sig"] == "ui:2:2026-11-18T10:01:00Z"
    assert not turns_path.exists()

    # Fresh turn re-arms already_reminded so [TDQ:OUTPUT] can fire once in the new turn
    _, cmd_out3, _ = _run_dispatch("PreToolUse", cmd_payload, repo, fake_home)
    assert cmd_out3 == {"decision": "allow"}
    assert (runtime_dir / f"pending-reminders-{sid}.jsonl").is_file()


def test_r2_call_mcp_tool_lsp_overwrite_and_subagent_overwrite(tmp_path: Path) -> None:
    """Verify O(1) LSP start_lsp/blast_radius overwrites, empty deny, SUBAGENT rules."""
    py_repo = tmp_path / "py_repo"
    fake_home = tmp_path / "home_r2"
    _init_git_repo(py_repo)
    (py_repo / "pyproject.toml").write_text(
        '[project]\nname = "sample"\n', encoding="utf-8"
    )

    # 1. call_mcp_tool start_lsp with JSON str Arguments -> allow + str overwrite < 1s
    p_str = {
        "cwd": str(py_repo),
        "conversation_id": "conv-lsp-str",
        "tool_name": "call_mcp_tool",
        "tool_input": {
            "ServerName": "lsp",
            "ToolName": "start_lsp",
            "Arguments": json.dumps({"root_dir": str(py_repo)}),
        },
    }
    _, out_str, elapsed_ms = _run_dispatch("PreToolUse", p_str, py_repo, fake_home)
    assert out_str["decision"] == "allow"
    assert elapsed_ms < 1000.0
    assert not (py_repo / "docs" / "tdq" / ".tdq-lsp-module.json").exists()
    ov_str = out_str["overwrite"]
    assert "ServerName" not in ov_str and "ToolName" not in ov_str
    assert isinstance(ov_str["Arguments"], str)
    assert json.loads(ov_str["Arguments"]) == {
        "root_dir": str(py_repo),
        "language_id": "python",
    }

    # 2. call_mcp_tool start_lsp with dict Arguments -> preserve dict type
    p_dict = {
        "cwd": str(py_repo),
        "conversation_id": "conv-lsp-dict",
        "tool_name": "call_mcp_tool",
        "tool_input": {
            "ServerName": "lsp",
            "ToolName": "start_lsp",
            "Arguments": {"root_dir": str(py_repo)},
        },
    }
    _, out_dict, _ = _run_dispatch("PreToolUse", p_dict, py_repo, fake_home)
    assert out_dict["decision"] == "allow"
    assert isinstance(out_dict["overwrite"]["Arguments"], dict)
    assert out_dict["overwrite"]["Arguments"] == {
        "root_dir": str(py_repo),
        "language_id": "python",
    }

    # 3. call_mcp_tool blast_radius -> overwrite scope="exported", transitive=False
    br_sample = {
        "changed_files": ["app.py"],
        "scope": "all",
        "include_transitive": True,
    }
    for raw_args, expect_str in ((json.dumps(br_sample), True), (br_sample, False)):
        p_br = {
            "cwd": str(py_repo),
            "conversation_id": "conv-br",
            "tool_name": "call_mcp_tool",
            "tool_input": {
                "ServerName": "lsp",
                "ToolName": "blast_radius",
                "Arguments": raw_args,
            },
        }
        _, out_br, _ = _run_dispatch("PreToolUse", p_br, py_repo, fake_home)
        assert out_br["decision"] == "allow"
        ov_args = out_br["overwrite"]["Arguments"]
        assert isinstance(ov_args, str) is expect_str
        parsed_br = json.loads(ov_args) if expect_str else ov_args
        assert parsed_br["changed_files"] == ["app.py"]
        assert parsed_br["scope"] == "exported"
        assert parsed_br["include_transitive"] is False

    # 4. Empty repo with no language marker -> start_lsp denies with 4 parts
    empty_repo = tmp_path / "empty_repo"
    empty_home = tmp_path / "empty_home"
    _init_git_repo(empty_repo)
    p_empty = {
        "cwd": str(empty_repo),
        "conversation_id": "conv-empty",
        "tool_name": "call_mcp_tool",
        "tool_input": {
            "ServerName": "lsp",
            "ToolName": "start_lsp",
            "Arguments": json.dumps({"root_dir": str(empty_repo)}),
        },
    }
    _, out_empty, _ = _run_dispatch("PreToolUse", p_empty, empty_repo, empty_home)
    assert out_empty["decision"] == "deny"
    _assert_four_parts(out_empty["reason"], "LSP")

    # 5. invoke_subagent with WORKTREE: + Workspace="branch" -> overwrite="inherit"
    sub_repo, sub_home = _setup_implement_repo(
        tmp_path,
        "sub_repo",
        "2026-11-18-1201-subagent",
        "- [~] **T1.1** Work — Test: `py -3 -m pytest`\n",
        impl_mode="subagent",
    )
    prompt_ok = (
        "TASK: T1.1\nWORKTREE: C:/tmp/wt\n"
        "VÙNG FILE: app.py\nTEST: py -3 -m pytest\nTRẢ VỀ: done"  # i18n-allow
    )
    p_sub = {
        "cwd": str(sub_repo),
        "conversation_id": "conv-sub",
        "tool_name": "invoke_subagent",
        "tool_input": {
            "Role": "tdq-implementer",
            "Workspace": "branch",
            "Prompt": prompt_ok,
        },
    }
    _, out_sub, _ = _run_dispatch("PreToolUse", p_sub, sub_repo, sub_home)
    assert out_sub == {"decision": "allow", "overwrite": {"Workspace": "inherit"}}

    # 6. swarm add when implement_mode != subagent -> hard deny 4-part [TDQ:SUBAGENT]
    main_repo, main_home = _setup_implement_repo(
        tmp_path,
        "main_repo",
        "2026-11-18-1202-swarm-deny",
        "- [~] **T1.1** Work — Test: `py -3 -m pytest`\n",
        impl_mode="main",
    )
    p_swarm = {
        "cwd": str(main_repo),
        "conversation_id": "conv-swarm",
        "tool_name": "swarm",
        "tool_input": {"action": "add", "tasks": ["T1.1"]},
    }
    _, out_swarm, _ = _run_dispatch("PreToolUse", p_swarm, main_repo, main_home)
    assert out_swarm["decision"] == "deny"
    _assert_four_parts(out_swarm["reason"], "SUBAGENT")


def test_r2_search_huong_a_and_malformed_allow(tmp_path: Path) -> None:
    """Verify Option A search grace/deny/reset, PowerShell allow, and rtk bypass."""
    repo, fake_home = _setup_implement_repo(
        tmp_path,
        "search_repo",
        "2026-11-18-1203-search-a",
        "- [~] **T1.1** Search check — Test: `py -3 -m pytest`\n",
    )
    stamp = repo / "docs" / "tdq" / ".tdq-san-sang.json"
    stamp.parent.mkdir(parents=True, exist_ok=True)
    stamp_data = {"tang": {"lsp": {"san_sang": True}, "graphify": {"san_sang": True}}}
    stamp.write_text(json.dumps(stamp_data), encoding="utf-8")
    sid = "conv-search-a"

    # 1. PowerShell here-string & backtick-n py -3 -c commands never deny as malformed
    for ps_cmd in (
        "$code = @'\nrg foo\n'@\npy -3 -c $code",
        'py -3 -c "print(\\"hello `n world\\")"',
        r'py -3 -c "print(\"hello \`n world\")"',
    ):
        _, cmd_out, _ = _run_dispatch(
            "PreToolUse",
            {
                "cwd": str(repo),
                "conversation_id": sid,
                "tool_name": "run_command",
                "tool_input": {"CommandLine": ps_cmd},
            },
            repo,
            fake_home,
        )
        assert cmd_out == {"decision": "allow"}
    rem_path = repo / "docs" / "tdq" / ".tdq-runtime" / f"pending-reminders-{sid}.jsonl"
    assert not rem_path.exists()

    # 2. First blind grep_search -> allow + queue [TDQ:SEARCH], flushed with 4-part MD
    grep1 = {
        "cwd": str(repo),
        "conversation_id": sid,
        "tool_name": "grep_search",
        "tool_input": {"Query": "missingSymbolAlpha", "SearchPath": str(repo / "src")},
    }
    _, g1_out, _ = _run_dispatch("PreToolUse", grep1, repo, fake_home)
    assert g1_out == {"decision": "allow"}
    _, pi_out, _ = _run_dispatch(
        "PostInvocation", {"cwd": str(repo), "conversation_id": sid}, repo, fake_home
    )
    _assert_flushed_dual_channel(pi_out, ("SEARCH",))

    # 3. Second consecutive blind grep_search -> hard deny 4-part [TDQ:SEARCH]
    grep2 = {
        "cwd": str(repo),
        "conversation_id": sid,
        "tool_name": "grep_search",
        "tool_input": {"Query": "missingSymbolBeta", "SearchPath": str(repo / "src")},
    }
    _, g2_out, _ = _run_dispatch("PreToolUse", grep2, repo, fake_home)
    assert g2_out["decision"] == "deny"
    _assert_four_parts(g2_out["reason"], "SEARCH")

    # 4. PostToolUse mcp_lsp_find_symbol resets streak and unlocks grep
    _, post_lsp, _ = _run_dispatch(
        "PostToolUse",
        {
            "cwd": str(repo),
            "conversation_id": sid,
            "tool_name": "mcp_lsp_find_symbol",
            "tool_input": {"name_path_pattern": "add"},
            "tool_response": {"symbols": ["add"]},
        },
        repo,
        fake_home,
    )
    assert post_lsp == {}
    turns = _read_jsonl(repo / "docs" / "tdq" / ".tdq-runtime" / f"turns-{sid}.jsonl")
    assert any(
        r.get("type") == "search_grace" and r.get("state") == "reset" for r in turns
    )

    _, g3_out, _ = _run_dispatch("PreToolUse", grep2, repo, fake_home)
    assert g3_out == {"decision": "allow"}

    # 5. rtk bypass grep denies immediately even on a fresh session
    _, bypass_out, _ = _run_dispatch(
        "PreToolUse",
        {
            "cwd": str(repo),
            "conversation_id": "conv-rtk-bypass",
            "tool_name": "run_command",
            "tool_input": {"CommandLine": "rtk bypass grep missingSym src/"},
        },
        repo,
        fake_home,
    )
    assert bypass_out["decision"] == "deny"
    _assert_four_parts(bypass_out["reason"], "SEARCH")


def _assert_nine_hard_gates(tmp_path: Path) -> None:
    """Trigger all 9 HARD_DENY_CODES and verify deny/continue carries 4-part cards."""
    # 1. APPROVE
    app_repo = tmp_path / "hard_approve"
    app_home = tmp_path / "hard_approve_home"
    _init_git_repo(app_repo)
    assert _run_state_cli(
        app_repo, app_home, "init", "2026-11-18-1210-hard", "deep", "--bo-qua-lsp", "t"
    ).returncode == 0
    spec_rel = "docs/tdq/spec/2026-11-18-1210-hard.md"
    spec_p = app_repo / spec_rel
    spec_p.parent.mkdir(parents=True, exist_ok=True)
    spec_p.write_text("# Spec\n", encoding="utf-8")
    assert _run_state_cli(
        app_repo, app_home, "set", "phase=spec", f"spec_file={spec_rel}"
    ).returncode == 0
    _, out_app, _ = _run_dispatch(
        "PreToolUse",
        {
            "cwd": str(app_repo),
            "conversation_id": "h-app",
            "tool_name": "edit_file",
            "tool_input": {"TargetFile": str(app_repo / "app.py")},
        },
        app_repo,
        app_home,
    )
    assert out_app["decision"] == "deny"
    _assert_four_parts(out_app["reason"], "APPROVE")

    # 2. GIT + 4. STATE + 7. ZERO-POPUP + 9. UNFINISHED on implement repo
    impl_repo, impl_home = _setup_implement_repo(
        tmp_path,
        "hard_impl",
        "2026-11-18-1211-hard-impl",
        "- [ ] **T1.1** Open task — Test: `py -3 -m pytest`\n",
    )
    _, out_git, _ = _run_dispatch(
        "PreToolUse",
        {
            "cwd": str(impl_repo),
            "conversation_id": "h-git",
            "tool_name": "run_command",
            "tool_input": {"CommandLine": "git checkout -b claude-bad"},
        },
        impl_repo,
        impl_home,
    )
    assert out_git["decision"] == "deny"
    _assert_four_parts(out_git["reason"], "GIT")

    _, out_state, _ = _run_dispatch(
        "PreToolUse",
        {
            "cwd": str(impl_repo),
            "conversation_id": "h-st",
            "tool_name": "run_command",
            "tool_input": {
                "CommandLine": "Set-Content -Path docs/tdq/state.json -Value '{}'"
            },
        },
        impl_repo,
        impl_home,
    )
    assert out_state["decision"] == "deny"
    _assert_four_parts(out_state["reason"], "STATE")

    _, out_pop, _ = _run_dispatch(
        "PreToolUse",
        {
            "cwd": str(impl_repo),
            "conversation_id": "h-pop",
            "tool_name": "ask_question",
            "tool_input": {"questions": []},
        },
        impl_repo,
        impl_home,
    )
    assert out_pop["decision"] == "deny"
    _assert_four_parts(out_pop["reason"], "ZERO-POPUP")

    _, out_unf, _ = _run_dispatch(
        "Stop",
        {"cwd": str(impl_repo), "conversation_id": "h-unf"},
        impl_repo,
        impl_home,
    )
    assert out_unf["decision"] == "continue"
    _assert_four_parts(out_unf["reason"], "UNFINISHED")

    # 3. TEAM (subagent missing map) + 8. SUBAGENT (swarm wrong mode)
    team_repo, team_home = _setup_implement_repo(
        tmp_path,
        "hard_team",
        "2026-11-18-1212-hard-team",
        "- [~] **T1.1** Task\n  - Chạm: `app.py`\n",  # i18n-allow
        impl_mode="subagent",
    )
    _, out_team, _ = _run_dispatch(
        "PreToolUse",
        {
            "cwd": str(team_repo),
            "conversation_id": "h-team",
            "tool_name": "edit_file",
            "tool_input": {"TargetFile": str(team_repo / "app.py")},
        },
        team_repo,
        team_home,
    )
    assert out_team["decision"] == "deny"
    _assert_four_parts(out_team["reason"], "TEAM")

    _, out_sub, _ = _run_dispatch(
        "PreToolUse",
        {
            "cwd": str(impl_repo),
            "conversation_id": "h-sub",
            "tool_name": "swarm",
            "tool_input": {"action": "add"},
        },
        impl_repo,
        impl_home,
    )
    assert out_sub["decision"] == "deny"
    _assert_four_parts(out_sub["reason"], "SUBAGENT")

    # 5. READONLY (reviewer subagent transcript)
    rev_tr = tmp_path / "rev_transcript.jsonl"
    rev_line = json.dumps(
        {"step_index": 0, "type": "USER_INPUT", "content": "You are tdq-reviewer."}
    )
    rev_tr.write_text(rev_line + "\n", encoding="utf-8")
    _, out_ro, _ = _run_dispatch(
        "PreToolUse",
        {
            "cwd": str(impl_repo),
            "conversation_id": "h-ro",
            "transcriptPath": str(rev_tr),
            "tool_name": "edit_file",
            "tool_input": {"TargetFile": str(impl_repo / "app.py")},
        },
        impl_repo,
        impl_home,
    )
    assert out_ro["decision"] == "deny"
    _assert_four_parts(out_ro["reason"], "READONLY")

    # 6. VUNG (codex_edit_gate + 4-part guidance formatter)
    cx_payload = {
        "cwd": str(impl_repo),
        "tool_name": "apply_patch",
        "tool_input": {"command": "*** Update File: secret/out.py\n+x=1"},
    }
    cx = subprocess.run(
        ["python", "-X", "utf8", str(CODEX_GATE_PY)],
        cwd=str(impl_repo),
        input=json.dumps(cx_payload),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=20,
        env=_build_env(
            impl_repo,
            impl_home,
            extra_env={"TDQ_CODEX_TASK": "T1.1", "TDQ_CODEX_VUNG": "app.py"},
        ),
    )
    assert cx.returncode == 0
    cx_out = json.loads(cx.stdout.strip())
    assert cx_out["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "[TDQ:VUNG]" in cx_out["hookSpecificOutput"]["permissionDecisionReason"]
    vung_card = _load_gate_guidance().format_deny_4part("VUNG", "secret/out.py")
    _assert_four_parts(vung_card, "VUNG")


def test_r2_user_markdown_4part_and_tick_log_soft(tmp_path: Path) -> None:
    """Verify soft TICK/LOG/DOC guidance flushes 4-part user_markdown; 9 hard deny."""
    repo, fake_home = _setup_implement_repo(
        tmp_path,
        "soft_repo",
        "2026-11-18-1204-soft",
        "- [ ] **T1.1** Unticked item — Test: `py -3 -m pytest`\n",
    )
    sid = "conv-soft"
    big_file = repo / "large_mod.py"
    big_file.write_text(("x = 1\n" * 450), encoding="utf-8")

    # Trigger TICK + LOG at edit_gate -> must allow (0 deny tick_loop) and queue
    _, e1, _ = _run_dispatch(
        "PreToolUse",
        {
            "cwd": str(repo),
            "conversation_id": sid,
            "tool_name": "edit_file",
            "tool_input": {"TargetFile": str(repo / "src_mod.py")},
        },
        repo,
        fake_home,
    )
    assert e1 == {"decision": "allow"}

    # Even with 1 [~] task and 4 consecutive edits (>= 3), tick stays soft allow
    plan_file = repo / "docs" / "tdq" / "plan" / "2026-11-18-1204-soft.md"
    plan_file.write_text(
        "- [~] **T1.1** Active item — Test: `py -3 -m pytest`\n", encoding="utf-8"
    )
    for idx in range(4):
        _, streak_out, _ = _run_dispatch(
            "PreToolUse",
            {
                "cwd": str(repo),
                "conversation_id": sid,
                "tool_name": "edit_file",
                "tool_input": {"TargetFile": str(repo / f"m{idx}.py")},
            },
            repo,
            fake_home,
        )
        assert streak_out == {"decision": "allow"}

    # Trigger DOC via two whole-file reads of >2KB file
    read_payload = {
        "cwd": str(repo),
        "conversation_id": sid,
        "tool_name": "read_file",
        "tool_input": {"AbsolutePath": str(big_file)},
    }
    assert _run_dispatch("PreToolUse", read_payload, repo, fake_home)[1] == {
        "decision": "allow"
    }
    assert _run_dispatch("PreToolUse", read_payload, repo, fake_home)[1] == {
        "decision": "allow"
    }

    # Flush queued soft gates via PostInvocation -> 4-part user_markdown and <= 200 cap
    _, pi_out, _ = _run_dispatch(
        "PostInvocation", {"cwd": str(repo), "conversation_id": sid}, repo, fake_home
    )
    _assert_flushed_dual_channel(pi_out, ("LOG", "TICK", "DOC"))

    # All 9 hard gates still enforce deny / continue with 4-part guidance
    _assert_nine_hard_gates(tmp_path)


def test_r3_stop_continuation_active_once_and_cleanup_7d(tmp_path: Path) -> None:
    """Verify Stop continuationActive 1-shot, .staging exemption, and 7d cleanup."""
    repo, fake_home = _setup_implement_repo(
        tmp_path,
        "stop_repo",
        "2026-11-18-1205-stop",
        (
            "- [~] **T1.1** In progress — Test: `py -3 -m pytest`\n"
            "- [ ] **T1.2** Next — Test: `py -3 -m pytest`\n"
        ),
    )
    sid = "conv-stop"
    _run_dispatch(
        "PreInvocation",
        {"cwd": str(repo), "conversation_id": sid, "prompt": "work"},
        repo,
        fake_home,
    )
    meta_path = repo / "docs" / "tdq" / ".tdq-runtime" / f"turn-meta-{sid}.json"
    assert json.loads(meta_path.read_text(encoding="utf-8"))["turn_closed"] is False

    # 1. Stop with continuationActive=False -> continue once with 4-part UNFINISHED
    _, s1, _ = _run_dispatch(
        "Stop",
        {"cwd": str(repo), "conversation_id": sid, "continuationActive": False},
        repo,
        fake_home,
    )
    assert s1["decision"] == "continue"
    _assert_four_parts(s1["reason"], "UNFINISHED")

    # 2. Stop with continuationActive=True -> allow and close turn
    _, s2, _ = _run_dispatch(
        "Stop",
        {"cwd": str(repo), "conversation_id": sid, "continuationActive": True},
        repo,
        fake_home,
    )
    assert s2 == {"decision": "allow"}
    assert json.loads(meta_path.read_text(encoding="utf-8"))["turn_closed"] is True

    # 3. Editing docs/.staging/x.log does not trigger LOG reminder or block at Stop
    assert _run_state_cli(repo, fake_home, "set", "phase=analyze").returncode == 0
    sid_stage = "conv-staging"
    _run_dispatch(
        "PreInvocation",
        {"cwd": str(repo), "conversation_id": sid_stage, "prompt": "stage"},
        repo,
        fake_home,
    )
    stage_log = repo / "docs" / ".staging" / "x.log"
    stage_log.parent.mkdir(parents=True, exist_ok=True)
    stage_log.write_text("staging line\n", encoding="utf-8")
    _run_dispatch(
        "PreToolUse",
        {
            "cwd": str(repo),
            "conversation_id": sid_stage,
            "tool_name": "edit_file",
            "tool_input": {"TargetFile": str(stage_log)},
        },
        repo,
        fake_home,
    )
    _, s_stage, _ = _run_dispatch(
        "Stop",
        {"cwd": str(repo), "conversation_id": sid_stage, "continuationActive": False},
        repo,
        fake_home,
    )
    assert s_stage == {"decision": "allow"}
    stage_rem = (
        repo / "docs" / "tdq" / ".tdq-runtime" / f"pending-reminders-{sid_stage}.jsonl"
    )
    assert not stage_rem.exists()
    _, pi_stage, _ = _run_dispatch(
        "PostInvocation",
        {"cwd": str(repo), "conversation_id": sid_stage},
        repo,
        fake_home,
    )
    assert pi_stage == {}

    # 4. SessionStart removes >7d allowlisted runtime files and preserves 1d files
    rdir = repo / "docs" / "tdq" / ".tdq-runtime"
    rdir.mkdir(parents=True, exist_ok=True)
    now = time.time()
    old_ts = now - (8 * 86400)
    fresh_ts = now - (1 * 86400)
    stale_files = [
        rdir / "stale.lock",
        rdir / "turns-old-sid.jsonl",
        rdir / "pending-reminders-old-sid.jsonl",
        rdir / "turn-meta-old-sid.json",
    ]
    fresh_files = [
        rdir / "fresh.lock",
        rdir / "turns-new-sid.jsonl",
        rdir / "pending-reminders-new-sid.jsonl",
        rdir / "turn-meta-new-sid.json",
        rdir / "sessions.json",
    ]
    for path in stale_files:
        path.write_text("{}\n", encoding="utf-8")
        os.utime(path, (old_ts, old_ts))
    for path in fresh_files:
        path.write_text("{}\n", encoding="utf-8")
        ts = old_ts if path.name == "sessions.json" else fresh_ts
        os.utime(path, (ts, ts))

    _, ss_out, _ = _run_dispatch(
        "SessionStart",
        {"cwd": str(repo), "conversation_id": "conv-clean"},
        repo,
        fake_home,
    )
    assert "injectSteps" in ss_out
    for path in stale_files:
        assert not path.exists(), f"Stale runtime file was not cleaned: {path.name}"
    for path in fresh_files:
        assert path.exists(), f"Valid runtime file was wrongly removed: {path.name}"


def test_tdq_log_default_and_disabled(tmp_path: Path) -> None:
    """Verify dispatch.py emits ISO stderr telemetry by default; mute on TDQ_LOG=0."""
    repo, fake_home = _setup_implement_repo(
        tmp_path,
        "log_repo",
        "2026-11-18-1206-log",
        "- [~] **T1.1** Task — Test: `py -3 -m pytest`\n",
    )
    payload = {"cwd": str(repo), "conversation_id": "conv-log", "prompt": "hello"}

    proc_on, _, _ = _run_dispatch(
        "PreInvocation", payload, repo, fake_home, keep_tdq_log=True
    )
    lines = [ln for ln in proc_on.stderr.splitlines() if ln.strip()]
    assert any(
        ISO_LOG_RE.match(ln) and "dispatch" in ln and "event=PreInvocation" in ln
        for ln in lines
    )

    proc_off, _, _ = _run_dispatch(
        "PreInvocation", payload, repo, fake_home, keep_tdq_log=False
    )
    assert proc_off.stderr.strip() == ""


def test_empty_and_malformed_payload_fail_open(tmp_path: Path) -> None:
    """Verify empty '{}' and malformed JSON stdin payloads fail open across events."""
    repo = tmp_path / "failopen_repo"
    fake_home = tmp_path / "failopen_home"
    _init_git_repo(repo)
    for event in ("PreInvocation", "PreToolUse", "PostInvocation", "Stop"):
        for raw_payload in ({}, "{broken-json"):
            _, out, _ = _run_dispatch(event, raw_payload, repo, fake_home)
            if event in ("PreToolUse", "Stop"):
                assert out.get("decision") == "allow"
            else:
                assert isinstance(out, dict)


def test_qc2_git_hard_gate_blocks_slash_worktree_and_coauthored(tmp_path: Path) -> None:
    """Verify TDQ:GIT hard blocks slash branches, worktree add, and Co-Authored-By commits."""
    repo, fake_home = _setup_implement_repo(
        tmp_path,
        "git_hard_repo",
        "2026-11-18-2145-git-hard",
        "- [~] **T1.1** Work — Test: `py -3 -m pytest`\n",
    )
    bad_cmds = [
        "git checkout -b claude/bad-branch",
        "git switch -c gemini/bad-branch",
        "git worktree add -b codex-wt ../wt",
        'git commit -m "feat: ok" -m "Co-Authored-By: Claude Code <noreply@x.com>"',
    ]
    for idx, cmd in enumerate(bad_cmds):
        _, out, _ = _run_dispatch(
            "PreToolUse",
            {
                "cwd": str(repo),
                "conversation_id": f"conv-git-{idx}",
                "toolCall": {"name": "run_command", "args": {"CommandLine": cmd}},
            },
            repo,
            fake_home,
        )
        assert out.get("decision") == "deny", (cmd, out)
        assert "[TDQ:GIT]" in out.get("reason", ""), (cmd, out)


def test_qc2_team_blocks_agy_subagent_before_implement(tmp_path: Path) -> None:
    """Verify AGY subagents detected via transcriptPath cannot mutate before implement."""
    repo = tmp_path / "team_agy_repo"
    fake_home = tmp_path / "team_agy_home"
    _init_git_repo(repo)
    assert _run_state_cli(repo, fake_home, "init", "2026-11-18-2146-team", "full", "--bo-qua-lsp", "test").returncode == 0
    tr = tmp_path / "subagent_tr.jsonl"
    tr.write_text(json.dumps({"role": "tdq-implementer", "text": "You are tdq-implementer agent"}) + "\n", encoding="utf-8")

    _, edit_out, _ = _run_dispatch(
        "PreToolUse",
        {
            "cwd": str(repo),
            "conversation_id": "conv-team-1",
            "transcriptPath": str(tr),
            "toolCall": {"name": "edit_file", "args": {"TargetFile": str(repo / "app.py")}},
        },
        repo,
        fake_home,
    )
    assert edit_out.get("decision") == "deny", edit_out
    assert "[TDQ:TEAM]" in edit_out.get("reason", ""), edit_out

    _, bash_out, _ = _run_dispatch(
        "PreToolUse",
        {
            "cwd": str(repo),
            "conversation_id": "conv-team-2",
            "transcriptPath": str(tr),
            "toolCall": {"name": "run_command", "args": {"CommandLine": "Set-Content -Path app.py -Value bad"}},
        },
        repo,
        fake_home,
    )
    assert bash_out.get("decision") == "deny", bash_out
    assert "[TDQ:TEAM]" in bash_out.get("reason", ""), bash_out


def test_qc2_malformed_search_deduped_and_prompt_over_64kb(tmp_path: Path) -> None:
    """Verify malformed search reminds once per turn and >64KB pasted prompt resets turn."""
    repo, fake_home = _setup_implement_repo(
        tmp_path,
        "qc2_edge_repo",
        "2026-11-18-2147-edge",
        "- [~] **T1.1** Work — Test: `py -3 -m pytest`\n",
    )
    tr = tmp_path / "big_tr.jsonl"
    tr.write_text(
        json.dumps({"step_index": 1, "type": "USER_INPUT", "created_at": "2026-11-18T21:00:00Z", "content": "start"}) + "\n",
        encoding="utf-8",
    )
    _run_dispatch(
        "PreInvocation",
        {"cwd": str(repo), "conversation_id": "conv-edge", "transcriptPath": str(tr), "prompt": "start"},
        repo,
        fake_home,
    )
    bad_cmd = {"name": "run_command", "args": {"CommandLine": 'rg "unterminated'}}
    for _ in range(2):
        _, cg_out, _ = _run_dispatch(
            "PreToolUse",
            {"cwd": str(repo), "conversation_id": "conv-edge", "toolCall": bad_cmd},
            repo,
            fake_home,
        )
        assert cg_out.get("decision") == "allow"
    _, pi1, _ = _run_dispatch(
        "PostInvocation",
        {"cwd": str(repo), "conversation_id": "conv-edge"},
        repo,
        fake_home,
    )
    assert "injectSteps" in pi1
    # Calling malformed command again after flush should be deduped within same turn
    _run_dispatch(
        "PreToolUse",
        {"cwd": str(repo), "conversation_id": "conv-edge", "toolCall": bad_cmd},
        repo,
        fake_home,
    )
    _, pi2, _ = _run_dispatch(
        "PostInvocation",
        {"cwd": str(repo), "conversation_id": "conv-edge"},
        repo,
        fake_home,
    )
    assert pi2 == {}, f"Malformed SEARCH reminder should dedupe within same turn: {pi2}"

    # Now append > 70 KB padding & huge > 70 KB USER_INPUT line with changed prompt (turn not closed)
    with tr.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"step_index": 2, "type": "TOOL_OUTPUT", "text": "x" * 70000}) + "\n")
        fh.write(json.dumps({
            "step_index": 3, "type": "USER_INPUT",
            "created_at": "2026-11-18T21:05:00Z", "content": "y" * 70000,
        }) + "\n")
    turns_file = repo / "docs" / "tdq" / ".tdq-runtime" / "turns-conv-edge.jsonl"
    assert turns_file.is_file()
    _run_dispatch(
        "PreInvocation",
        {"cwd": str(repo), "conversation_id": "conv-edge", "transcriptPath": str(tr), "prompt": "y" * 70000},
        repo,
        fake_home,
    )
    assert not turns_file.exists(), "New >64KB pasted prompt must trigger new-turn detection"


def test_qc2_excluded_dead_agy_scripts_absent_from_plugin() -> None:
    """Verify 4 non-AGY / duplicate hook scripts are excluded from compiled plugin."""
    scripts_dir = PLUGIN_DIR / "hooks" / "scripts"
    root_hooks = WORKSPACE / "hooks" / "scripts"
    for name in (
        "agy_pretooluse_gate.py",
        "agy_stop_gate.py",
        "codex_edit_gate.py",
        "subagent_start.py",
    ):
        assert not (scripts_dir / name).exists(), f"Dead AGY script left in plugin: {name}"
        assert (root_hooks / name).is_file(), f"Original root script removed: {name}"
