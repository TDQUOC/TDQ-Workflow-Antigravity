"""Integration & adversarial parity tests for TDQ work_kind=investigate V2."""
from __future__ import annotations

import importlib.util
import json
import os
import re
import statistics
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
PLUGIN_DIR = REPO_ROOT / "plugins" / "tdq-workflow-agy"
RUST_BIN = PLUGIN_DIR / "bin" / ("tdq-dispatch.exe" if os.name == "nt" else "tdq-dispatch")
PYTHON_DISPATCH = PLUGIN_DIR / "hooks" / "scripts" / "dispatch.py"
STATE_CLI = REPO_ROOT / "scripts" / "tdq_state.py"
TEAM_CLI = REPO_ROOT / "scripts" / "tdq_team.py"
LINT_CLI = REPO_ROOT / "scripts" / "doc_lint.py"
TIMING_CLI = REPO_ROOT / "scripts" / "tdq_timing.py"
GUIDANCE_JSON = REPO_ROOT / "tools" / "patches" / "gate_guidance.json"


_scripts_dir = str(REPO_ROOT / "scripts")
if _scripts_dir not in sys.path:
    sys.path.insert(0, _scripts_dir)

import doc_lint  # noqa: E402
import tdq_bench  # noqa: E402
import tdq_state  # noqa: E402


def _load_plugin_common():
    """Load packaged _common cleanly without leaving PLUGIN_DIR paths on sys.path."""
    saved_path = list(sys.path)
    try:
        spec = importlib.util.spec_from_file_location(
            "_inv_plugin_common", PLUGIN_DIR / "hooks" / "scripts" / "_common.py"
        )
        assert spec is not None and spec.loader is not None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    finally:
        sys.path[:] = saved_path


_common = _load_plugin_common()

ISO_RE = re.compile(r"\[\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")
SLUG_PARITY = "2026-11-21-0400-inv-parity"


def _sub_env(
    repo: Path,
    fake_home: Path,
    *,
    tdq_log: str = "0",
    engine: str | None = None,
    include_project_dir: bool = True,
) -> dict[str, str]:
    """Build isolated subprocess environment anchored inside tmp_path."""
    fake_home.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env["PATH"] = os.path.dirname(sys.executable) + os.pathsep + env.get("PATH", "")
    env.update({
        "HOME": str(fake_home),
        "USERPROFILE": str(fake_home),
        "APPDATA": str(fake_home / "AppData" / "Roaming"),
        "LOCALAPPDATA": str(fake_home / "AppData" / "Local"),
        "XDG_CONFIG_HOME": str(fake_home / ".config"),
        "GEMINI_CONFIG_DIR": str(fake_home / ".gemini"),
        "PLUGIN_ROOT": str(PLUGIN_DIR),
        "TDQ_LOG": tdq_log,
        "TDQ_KHOI_TAO_NEN": "0",
        "TDQ_KHONG_CHAM_MAY": "1",
        "TDQ_RTK": "0",
        "RTK_DISABLED": "1",
    })
    if include_project_dir:
        env["TDQ_PROJECT_DIR"] = str(repo)
    else:
        env.pop("TDQ_PROJECT_DIR", None)
    if engine:
        env["TDQ_HOOK_ENGINE"] = engine
    else:
        env.pop("TDQ_HOOK_ENGINE", None)
    return env


def _run_cmd(
    cmd: list[str],
    cwd: Path,
    env: dict[str, str],
    *,
    stdin_text: str | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run subprocess with UTF-8 pipes and hidden console window on Windows."""
    kw: dict = {
        "cwd": str(cwd),
        "capture_output": True,
        "text": True,
        "encoding": "utf-8",
        "errors": "replace",
        "timeout": 30,
        "env": env,
    }
    if stdin_text is not None:
        kw["input"] = stdin_text
    if os.name == "nt":
        kw["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
    return subprocess.run(cmd, check=False, **kw)


def _init_git_ws(repo: Path) -> None:
    """Create minimal git repository inside tmp_path."""
    repo.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    _run_cmd(["git", "init", "-b", "main"], repo, env)
    _run_cmd(["git", "config", "user.email", "tester@example.com"], repo, env)
    _run_cmd(["git", "config", "user.name", "TDQ Tester"], repo, env)
    (repo / "app.py").write_text("def add(a: int, b: int) -> int:\n    return a + b\n", encoding="utf-8")
    _run_cmd(["git", "add", "."], repo, env)
    _run_cmd(["git", "commit", "-m", "init"], repo, env)


def _setup_inv_repo(root: Path, slug: str = SLUG_PARITY) -> tuple[Path, Path]:
    """Initialize isolated investigate+implement repo with artifact dirs and sessions."""
    fake_home = root.parent / f"{root.name}_home"
    _init_git_ws(root)
    (root / "docs" / "tdq" / "artifacts" / slug / "sub" / "deep").mkdir(parents=True, exist_ok=True)
    (root / "docs" / "tdq" / "artifacts" / "other-slug").mkdir(parents=True, exist_ok=True)
    (root / "docs" / "tdq" / "research").mkdir(parents=True, exist_ok=True)
    state = tdq_state.default_state()
    state.update({
        "active_request": slug,
        "work_kind": "investigate",
        "lane": "full",
        "phase": "implement",
        "spec_approved": True,
        "plan_approved": True,
        "implement_mode": "subagent",
    })
    tdq_state.save(str(root), state)
    sessions = {
        "sess-exp": {"role": "tdq-explorer", "task": "T1.1"},
        "sess-dbg": {"role": "tdq-debugger", "task": "T1.2"},
        "sess-rev": {"role": "tdq-reviewer", "task": "T1.3"},
        "sess-sec": {"role": "tdq-security-reviewer", "task": "T1.4"},
        "sess-brw": {"role": "tdq-browser", "task": "T1.5"},
    }
    rt = root / "docs" / "tdq" / ".tdq-runtime"
    rt.mkdir(parents=True, exist_ok=True)
    (rt / "sessions.json").write_text(json.dumps(sessions, indent=2), encoding="utf-8")
    return root, fake_home


def _run_hook_engine(
    engine: str,
    payload: dict,
    repo: Path,
    fake_home: Path,
    *,
    tdq_log: str = "0",
) -> tuple[subprocess.CompletedProcess[str], dict]:
    """Execute AGY PreToolUse via Rust binary or TDQ_HOOK_ENGINE=python fallback."""
    assert RUST_BIN.is_file(), f"Missing Rust binary: {RUST_BIN}"
    env = _sub_env(
        repo,
        fake_home,
        tdq_log=tdq_log,
        engine="python" if engine == "python" else None,
    )
    proc = _run_cmd([str(RUST_BIN), "--event", "PreToolUse"], repo, env, stdin_text=json.dumps(payload))
    assert proc.returncode == 0, f"{engine} failed ({proc.returncode}): {proc.stderr}"
    lines = [ln for ln in proc.stdout.strip().splitlines() if ln.strip()]
    assert len(lines) == 1, f"{engine} expected 1 JSON line, got: {proc.stdout!r}"
    return proc, json.loads(lines[0])


def _turn_events(repo: Path, sid: str) -> list[str]:
    """Read event names recorded in turns-<sid>.jsonl."""
    path = repo / "docs" / "tdq" / ".tdq-runtime" / f"turns-{sid}.jsonl"
    if not path.is_file():
        return []
    rows = [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    return [str(r.get("event") or "") for r in rows]


def _run_cli(
    script: Path,
    args: list[str],
    repo: Path,
    fake_home: Path,
    *,
    cwd: Path | None = None,
    tdq_log: str = "0",
    include_project_dir: bool = True,
) -> subprocess.CompletedProcess[str]:
    """Run one TDQ Python script CLI in isolated environment."""
    env = _sub_env(repo, fake_home, tdq_log=tdq_log, include_project_dir=include_project_dir)
    return _run_cmd([sys.executable, "-X", "utf8", str(script), *args], cwd or repo, env)


@pytest.mark.parametrize(
    "identity,target",
    [
        ({"agent_type": "tdq-explorer"}, f"docs/tdq/artifacts/{SLUG_PARITY}/shard.md"),
        ({"agent_type": "tdq-debugger"}, f"docs/tdq/artifacts/{SLUG_PARITY}/shard.json"),
        ({"agent_type": "tdq-reviewer"}, f"docs/tdq/artifacts/{SLUG_PARITY}/shard.jsonl"),
        ({"agent_type": "tdq-explorer"}, f"docs/tdq/artifacts/{SLUG_PARITY}/sub/deep/s.md"),
        ({"agent_type": "tdq-explorer"}, f"docs/tdq/research/{SLUG_PARITY}-note.md"),
        ({"conversationId": "sess-exp"}, f"docs/tdq/artifacts/{SLUG_PARITY}/from-sess.md"),
        ({"conversationId": "sess-dbg"}, f"docs/tdq/artifacts/{SLUG_PARITY}/from-sess.json"),
        ({"conversationId": "sess-rev"}, f"docs/tdq/research/{SLUG_PARITY}-rev.md"),
    ],
)
def test_scoped_write_allow_parity_and_observe_edit(
    tmp_path: Path, identity: dict[str, str], target: str
) -> None:
    """Allow scoped shard writes in both Python & Rust and record observe('edit')."""
    r_repo, r_home = _setup_inv_repo(tmp_path / "r")
    p_repo, p_home = _setup_inv_repo(tmp_path / "p")
    base_sid = identity.get("conversationId") or f"ag-{identity['agent_type']}"
    payload = {
        "conversationId": base_sid,
        "toolName": "write_to_file",
        "toolInput": {"TargetFile": target},
        **identity,
    }
    _, r_out = _run_hook_engine("rust", {**payload, "cwd": str(r_repo)}, r_repo, r_home)
    _, p_out = _run_hook_engine("python", {**payload, "cwd": str(p_repo)}, p_repo, p_home)
    assert r_out.get("decision") == "allow" and p_out.get("decision") == "allow"
    assert "edit" in _turn_events(r_repo, base_sid)
    assert "edit" in _turn_events(p_repo, base_sid)


def test_scoped_write_helper_rejects_generic_subagent_and_empty_role(tmp_path: Path) -> None:
    """Layer-2 deny-first rejects empty role and generic 'subagent' for scoped-write."""
    repo, _ = _setup_inv_repo(tmp_path / "helper_chk")
    state = tdq_state.load(str(repo), heal=False)
    for role in ("tdq-explorer", "tdq-debugger", "tdq-reviewer"):
        assert _common.is_investigation_artifact_target(
            f"docs/tdq/artifacts/{SLUG_PARITY}/shard.md", str(repo), role, state
        )
    for denied in ("tdq-security-reviewer", "tdq-browser", "subagent", "", "tdq-qc-tester"):
        assert not _common.is_investigation_artifact_target(
            f"docs/tdq/artifacts/{SLUG_PARITY}/shard.md", str(repo), denied, state
        )


@pytest.mark.parametrize(
    "identity,target",
    [
        ({"agent_type": "tdq-security-reviewer"}, f"docs/tdq/artifacts/{SLUG_PARITY}/shard.md"),
        ({"conversationId": "sess-sec"}, f"docs/tdq/artifacts/{SLUG_PARITY}/shard.md"),
        ({"agent_type": "tdq-browser"}, f"docs/tdq/artifacts/{SLUG_PARITY}/shard.md"),
        ({"conversationId": "sess-brw"}, f"docs/tdq/artifacts/{SLUG_PARITY}/shard.md"),
        ({"agent_type": "tdq-explorer"}, f"docs/tdq/artifacts/{SLUG_PARITY}/evidence.jsonl"),
        ({"agent_type": "tdq-explorer"}, f"docs/tdq/artifacts/{SLUG_PARITY}/evidence-log.md"),
        ({"agent_type": "tdq-explorer"}, f"docs/tdq/artifacts/{SLUG_PARITY}/trial_1.json"),
        ({"agent_type": "tdq-explorer"}, f"docs/tdq/artifacts/{SLUG_PARITY}/rec_1.json"),
        ({"agent_type": "tdq-explorer"}, f"docs/tdq/artifacts/{SLUG_PARITY}/evil.py"),
        ({"agent_type": "tdq-explorer"}, "docs/tdq/artifacts/other-slug/shard.md"),
        ({"agent_type": "tdq-explorer"}, f"docs/tdq/research/{SLUG_PARITY}/nested.md"),
        ({"agent_type": "tdq-explorer"}, f"docs/tdq/artifacts/{SLUG_PARITY}/../other-slug/pwn.md"),
        ({"agent_type": "tdq-explorer"}, f"docs/tdq/artifacts/{SLUG_PARITY}/sub/../../outside.md"),
        ({"agent_type": "tdq-explorer"}, f"docs/tdq/artifacts/{SLUG_PARITY}/shard.md:stream"),
    ],
)
def test_scoped_write_deny_readonly_parity(
    tmp_path: Path, identity: dict[str, str], target: str
) -> None:
    """Deny forbidden roles, denylisted names, wrong slug, traversal, and ADS identically."""
    r_repo, r_home = _setup_inv_repo(tmp_path / "r")
    p_repo, p_home = _setup_inv_repo(tmp_path / "p")
    sid = identity.get("conversationId") or "deny-sid"
    payload = {
        "conversationId": sid,
        "toolName": "write_to_file",
        "toolInput": {"TargetFile": target},
        **identity,
    }
    _, r_out = _run_hook_engine("rust", {**payload, "cwd": str(r_repo)}, r_repo, r_home)
    _, p_out = _run_hook_engine("python", {**payload, "cwd": str(p_repo)}, p_repo, p_home)
    assert r_out.get("decision") == "deny" and "[TDQ:READONLY]" in r_out.get("reason", "")
    assert p_out.get("decision") == "deny" and "[TDQ:READONLY]" in p_out.get("reason", "")


def _assert_link_escape_denied(repo: Path, home: Path, link_rel: str) -> None:
    """Verify both Python and Rust deny scoped-write escaping through link_rel."""
    payload = {
        "cwd": str(repo),
        "conversationId": "link-esc",
        "agent_type": "tdq-explorer",
        "toolName": "write_to_file",
        "toolInput": {"TargetFile": f"{link_rel}/pwn.md"},
    }
    _, r_out = _run_hook_engine("rust", payload, repo, home)
    _, p_out = _run_hook_engine("python", payload, repo, home)
    assert r_out.get("decision") == "deny" and "[TDQ:READONLY]" in r_out.get("reason", "")
    assert p_out.get("decision") == "deny" and "[TDQ:READONLY]" in p_out.get("reason", "")


def test_scoped_write_windows_ntfs_junction_escape_denied(tmp_path: Path) -> None:
    """Deny NTFS junction escape on Windows in both Python and Rust."""
    if os.name != "nt":
        pytest.skip("NTFS mklink /J is Windows-specific")
    repo, home = _setup_inv_repo(tmp_path / "junc")
    outside = tmp_path / "outside_junc"
    outside.mkdir(parents=True, exist_ok=True)
    jpath = repo / "docs" / "tdq" / "artifacts" / SLUG_PARITY / "ext_link"
    mk = _run_cmd(["cmd.exe", "/c", "mklink", "/J", str(jpath), str(outside)], repo, dict(os.environ))
    assert mk.returncode == 0, mk.stdout + mk.stderr
    try:
        _assert_link_escape_denied(repo, home, f"docs/tdq/artifacts/{SLUG_PARITY}/ext_link")
    finally:
        _run_cmd(["cmd.exe", "/c", "rmdir", str(jpath)], repo, dict(os.environ))


def test_scoped_write_symlink_escape_denied(tmp_path: Path) -> None:
    """Deny symlink directory escape in both Python and Rust when OS permits symlinks."""
    repo, home = _setup_inv_repo(tmp_path / "sym")
    outside = tmp_path / "outside_sym"
    outside.mkdir(parents=True, exist_ok=True)
    sym_path = repo / "docs" / "tdq" / "artifacts" / SLUG_PARITY / "sym_link"
    try:
        os.symlink(outside, sym_path, target_is_directory=True)
    except OSError as exc:
        if os.name == "nt" and getattr(exc, "winerror", None) == 1314:
            pytest.skip(f"Windows symlink requires Developer Mode / SeCreateSymbolicLinkPrivilege: {exc}")
        raise
    _assert_link_escape_denied(repo, home, f"docs/tdq/artifacts/{SLUG_PARITY}/sym_link")


@pytest.mark.parametrize(
    "role,cmd,expected_decision,expected_tag",
    [
        ("tdq-explorer", 'cmd /c "echo pwn > evil.py"', "deny", "[TDQ:READONLY]"),
        ("tdq-explorer", "cmd /c del /f app.py", "deny", "[TDQ:READONLY]"),
        ("tdq-reviewer", "pwsh -Command \"[IO.File]::WriteAllText('app.py','x')\"", "deny", "[TDQ:READONLY]"),
        ("tdq-security-reviewer", "[System.IO.File]::WriteAllText('docs/tdq/state.json','{}')", "deny", "[TDQ:READONLY]"),
        ("", "[System.IO.File]::WriteAllText('docs/tdq/state.json','{}')", "deny", "[TDQ:STATE]"),
        ("tdq-explorer", "py -3 scripts/tdq_team.py evidence add --shard T1 --claim-file f.txt --source a.py:1", "allow", ""),
    ],
)
def test_shell_bypass_and_evidence_cli_parity(
    tmp_path: Path, role: str, cmd: str, expected_decision: str, expected_tag: str
) -> None:
    """Verify cmd /c, del /f, pwsh [IO.File], state.json write, and evidence add parity."""
    r_repo, r_home = _setup_inv_repo(tmp_path / "r")
    p_repo, p_home = _setup_inv_repo(tmp_path / "p")
    payload = {
        "conversationId": "sh-parity",
        "toolName": "run_command",
        "toolInput": {"CommandLine": cmd},
    }
    if role:
        payload["agent_type"] = role
    _, r_out = _run_hook_engine("rust", {**payload, "cwd": str(r_repo)}, r_repo, r_home)
    _, p_out = _run_hook_engine("python", {**payload, "cwd": str(p_repo)}, p_repo, p_home)
    assert r_out.get("decision") == expected_decision
    assert p_out.get("decision") == expected_decision
    if expected_tag:
        assert expected_tag in r_out.get("reason", "")
        assert expected_tag in p_out.get("reason", "")


def _measure_ranged_reads(repo: Path, home: Path, sid: str, count: int) -> list[float]:
    """Run count ranged-read PreToolUse calls through Rust binary and return ms latencies."""
    env = _sub_env(repo, home, tdq_log="0")
    latencies: list[float] = []
    for _ in range(count):
        rd = {"cwd": str(repo), "conversationId": sid, "toolName": "view_file",
              "toolInput": {"AbsolutePath": str(repo / "app.py"), "StartLine": 1, "EndLine": 10}}
        t0 = time.perf_counter()
        proc = _run_cmd([str(RUST_BIN), "--event", "PreToolUse"], repo, env, stdin_text=json.dumps(rd))
        latencies.append((time.perf_counter() - t0) * 1000.0)
        assert proc.returncode == 0 and json.loads(proc.stdout)["decision"] == "allow"
    return latencies


def test_weighted_burden_sid_isolation_hot_latency_and_23_guidance_codes(tmp_path: Path) -> None:
    """Measure <=25ms ranged-read hot-direct, verify sid burden >=40 DOC, and 23 AGY codes."""
    repo, home = _setup_inv_repo(tmp_path / "burden")
    _measure_ranged_reads(repo, home, "warm-sid", 3)
    latencies = _measure_ranged_reads(repo, home, "worker-a", 14)
    med_ms = statistics.median(latencies)
    assert med_ms <= 25.0, f"Hot-direct ranged read median {med_ms:.2f}ms exceeded 25.0ms"

    rt_dir = repo / "docs" / "tdq" / ".tdq-runtime"
    rem_a = rt_dir / "pending-reminders-worker-a.jsonl"
    assert rem_a.is_file() and "DOC" in rem_a.read_text(encoding="utf-8")

    wb = {"cwd": str(repo), "conversationId": "worker-b", "agent_type": "tdq-debugger",
          "toolName": "write_to_file", "toolInput": {"TargetFile": f"docs/tdq/artifacts/{SLUG_PARITY}/wb.md"}}
    assert _run_hook_engine("rust", wb, repo, home)[1]["decision"] == "allow"
    assert json.loads((rt_dir / "checkpoint-worker-a.json").read_text(encoding="utf-8"))["score"] == 42

    wa = {"cwd": str(repo), "conversationId": "worker-a", "agent_type": "tdq-explorer",
          "toolName": "write_to_file", "toolInput": {"TargetFile": f"docs/tdq/artifacts/{SLUG_PARITY}/wa.md"}}
    assert _run_hook_engine("rust", wa, repo, home)[1]["decision"] == "allow"
    assert json.loads((rt_dir / "checkpoint-worker-a.json").read_text(encoding="utf-8"))["score"] == 0

    _measure_ranged_reads(repo, home, "worker-c", 14)
    assert json.loads((rt_dir / "checkpoint-worker-c.json").read_text(encoding="utf-8"))["score"] == 42
    ev_cmd = {"cwd": str(repo), "conversationId": "worker-c", "agent_type": "tdq-explorer",
              "toolName": "run_command", "toolInput": {"CommandLine": "py -3 scripts/tdq_team.py evidence add --shard T1 --claim-file c.txt --source app.py:1"}}
    assert _run_hook_engine("rust", ev_cmd, repo, home)[1]["decision"] == "allow"
    assert json.loads((rt_dir / "checkpoint-worker-c.json").read_text(encoding="utf-8"))["score"] == 0

    guidance = json.loads(GUIDANCE_JSON.read_text(encoding="utf-8"))
    assert len(guidance["guidance_codes"]) == 23
    assert len(guidance["all_agy_codes"]) == 23 and "DOC" in guidance["guidance_codes"]


def test_tdq_log_0_silences_stderr_and_default_emits_iso(tmp_path: Path) -> None:
    """Verify TDQ_LOG=0 silences stderr across CLI/lint/Rust while default emits ISO logs."""
    repo, home = _setup_inv_repo(tmp_path / "logging")
    sub = repo / "sub"
    sub.mkdir(exist_ok=True)
    claim_file = repo / "docs" / "tdq" / "artifacts" / SLUG_PARITY / "c1.txt"
    claim_file.write_text("Verified claim in app.py", encoding="utf-8")
    note_md = repo / "docs" / "tdq" / "research" / "note.md"
    note_md.write_text("# Ghi chú\n\nNội dung kiểm tra.\n", encoding="utf-8")  # i18n-allow

    p_on = _run_cli(STATE_CLI, ["next"], repo, home, cwd=sub, tdq_log="1", include_project_dir=False)
    p_off = _run_cli(STATE_CLI, ["next"], repo, home, cwd=sub, tdq_log="0", include_project_dir=False)
    assert p_on.returncode == 0 and ISO_RE.search(p_on.stderr)
    assert p_off.returncode == 0 and p_off.stderr.strip() == ""

    add_args = ["evidence", "add", "--slug", SLUG_PARITY, "--shard", "T1", "--claim-file", str(claim_file), "--source", "app.py:1"]
    t_add_on = _run_cli(TEAM_CLI, add_args, repo, home, tdq_log="1")
    t_add_off = _run_cli(TEAM_CLI, add_args, repo, home, tdq_log="0")
    assert t_add_on.returncode == 0 and ISO_RE.search(t_add_on.stderr)
    assert t_add_off.returncode == 0 and t_add_off.stderr.strip() == ""

    t_mrg_on = _run_cli(TEAM_CLI, ["evidence", "merge", "--slug", SLUG_PARITY], repo, home, tdq_log="1")
    t_mrg_off = _run_cli(TEAM_CLI, ["evidence", "merge", "--slug", SLUG_PARITY], repo, home, tdq_log="0")
    assert t_mrg_on.returncode == 0 and ISO_RE.search(t_mrg_on.stderr)
    assert t_mrg_off.returncode == 0 and t_mrg_off.stderr.strip() == ""

    l_on = _run_cli(LINT_CLI, [str(note_md)], repo, home, tdq_log="1")
    l_off = _run_cli(LINT_CLI, [str(note_md)], repo, home, tdq_log="0")
    assert l_on.returncode == 0 and ISO_RE.search(l_on.stderr)
    assert l_off.returncode == 0 and l_off.stderr.strip() == ""

    hook_payload = {"cwd": str(repo), "conversationId": "log-chk", "toolName": "view_file",
                    "toolInput": {"AbsolutePath": str(repo / "app.py"), "StartLine": 1, "EndLine": 5}}
    r_on, _ = _run_hook_engine("rust", hook_payload, repo, home, tdq_log="1")
    r_off, _ = _run_hook_engine("rust", hook_payload, repo, home, tdq_log="0")
    assert ISO_RE.search(r_on.stderr)
    assert r_off.stderr.strip() == ""


def _ca1_approve_and_lint_spec(repo: Path, home: Path, slug: str) -> None:
    """Create investigate full spec without 2b/preview and verify approval + lint."""
    spec_rel = f"docs/tdq/spec/{slug}.md"
    spec_path = repo / spec_rel
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    spec_lines = [
        "# SPEC — Ca 1", "",
        "Ngày: 2026-11-20 · Lane: full · Work kind: investigate", "",  # i18n-allow
        "## 3b. Năng lực & công cụ", "",  # i18n-allow
        "| Skill | Nguồn | Phán quyết | Ghi chú |", "|---|---|---|---|",  # i18n-allow
        "| `tdq-intake` | plugin | NỀN | workflow |", "",  # i18n-allow
        "## 6. QC & Definition of Done", "",  # i18n-allow
        "| # | Hạng mục kiểm | Điều kiện PASS |", "|---|---|---|",  # i18n-allow
        "| Q1 | Thu thập bằng chứng | >= 10 phát hiện và <= 15 lượt đọc |", "",  # i18n-allow
    ]
    spec_path.write_text("\n".join(spec_lines), encoding="utf-8")
    assert _run_cli(STATE_CLI, ["set", "phase=spec", f"spec_file={spec_rel}"], repo, home).returncode == 0
    app_spec = _run_cli(STATE_CLI, ["approve", "spec", "--by", "duyet spec"], repo, home)
    assert app_spec.returncode == 0, app_spec.stderr
    assert tdq_state.load(str(repo))["archify_bo_qua"] is None
    assert not (repo / "docs" / "tdq" / "spec" / f"{slug}-preview.manifest.json").exists()
    lint_res = _run_cli(LINT_CLI, [str(spec_path)], repo, home)
    assert lint_res.returncode == 0, lint_res.stdout + lint_res.stderr


def test_sim_ca1_1056_full_research_waives_2b_r14_archify_and_uses_no_worktree(tmp_path: Path) -> None:
    """Ca 1 (2026-11-20-1056): full research skips 2b, R14, preview, and runs no_worktree + evidence."""
    repo, home = tmp_path / "ca1", tmp_path / "ca1_home"
    _init_git_ws(repo)
    slug = "2026-11-20-1056-ca1-research"
    assert _run_cli(STATE_CLI, ["init", slug, "full", "--kind", "investigate", "--bo-qua-lsp", "docs"], repo, home).returncode == 0
    _ca1_approve_and_lint_spec(repo, home, slug)

    plan_rel = f"docs/tdq/plan/{slug}.md"
    plan_path = repo / plan_rel
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_lines = [
        "# PLAN — Ca 1", "",
        "Ngày: 2026-11-20 · Lane: full · Work kind: investigate", "",  # i18n-allow
        "## P1 — Điều tra",  # i18n-allow
        '- [ ] **T1.1** (e5m) Khảo sát nhánh A — Test: `py -3 -c "print(\'ok\')"`',  # i18n-allow
        f"  - Chạm: `docs/tdq/artifacts/{slug}/t1.md`",  # i18n-allow
        "  - Worktree: no_worktree",
        '- [ ] **T1.2** (e5m) Khảo sát nhánh B — Test: `py -3 -c "print(\'ok\')"`',  # i18n-allow
        f"  - Chạm: `docs/tdq/artifacts/{slug}/t2.md`",  # i18n-allow
        "  - Worktree: no_worktree", "",
    ]
    plan_path.write_text("\n".join(plan_lines), encoding="utf-8")
    assert _run_cli(STATE_CLI, ["set", "phase=plan", f"plan_file={plan_rel}"], repo, home).returncode == 0
    assert _run_cli(STATE_CLI, ["approve", "plan", "--mode", "subagent", "--by", "duyet plan"], repo, home).returncode == 0
    assert _run_cli(TEAM_CLI, ["assign"], repo, home).returncode == 0
    team_map = json.loads((repo / "docs" / "tdq" / "team" / f"{slug}.json").read_text(encoding="utf-8"))
    assert team_map["tasks"]["T1.1"]["worktree_required"] is False
    assert team_map["tasks"]["T1.2"]["worktree_required"] is False

    c1, c2 = repo / "c1.txt", repo / "c2.txt"
    c1.write_text("Claim A from branch 1", encoding="utf-8")
    c2.write_text("Claim B from branch 2", encoding="utf-8")
    assert _run_cli(TEAM_CLI, ["evidence", "add", "--slug", slug, "--shard", "T1.1", "--claim-file", str(c1), "--source", "app.py:1"], repo, home).returncode == 0
    assert _run_cli(TEAM_CLI, ["evidence", "add", "--slug", slug, "--shard", "T1.2", "--claim-file", str(c2), "--source", "app.py:2"], repo, home).returncode == 0
    assert _run_cli(TEAM_CLI, ["evidence", "merge", "--slug", slug], repo, home).returncode == 0
    ev_md = repo / "docs" / "tdq" / "artifacts" / slug / "evidence-log.md"
    first_md = ev_md.read_text(encoding="utf-8")
    assert "Claim A from branch 1" in first_md and "Claim B from branch 2" in first_md
    assert _run_cli(TEAM_CLI, ["evidence", "render", "--slug", slug], repo, home).returncode == 0
    assert ev_md.read_text(encoding="utf-8") == first_md


def test_sim_ca2_1457_quick_audit_waives_flow_and_records_implement_timing(tmp_path: Path) -> None:
    """Ca 2 (2026-11-19-1457): quick investigate waives flow manifest and logs implement > 0s."""
    repo, home = tmp_path / "ca2", tmp_path / "ca2_home"
    _init_git_ws(repo)
    slug = "2026-11-19-1457-ca2-audit"
    assert _run_cli(STATE_CLI, ["init", slug, "quick", "--kind", "investigate", "--bo-qua-lsp", "audit"], repo, home).returncode == 0

    plan_rel = f"docs/tdq/plan/{slug}.md"
    plan_path = repo / plan_rel
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    mini_lines = [
        f"# QUICK — {slug}",
        "Ngày: 2026-11-19 · Lane: quick · Work kind: investigate",  # i18n-allow
        "",
        "- [ ] **T1.1** Audit hooks — Test: `py -3 -c \"print('ok')\"`",
        f"  - Chạm: `docs/tdq/artifacts/{slug}/audit.md`",  # i18n-allow
    ] + [f"  - Note {i}: scope item {i}" for i in range(40)]
    assert len(mini_lines) <= 65
    plan_path.write_text("\n".join(mini_lines) + "\n", encoding="utf-8")
    assert _run_cli(STATE_CLI, ["set", f"plan_file={plan_rel}"], repo, home).returncode == 0

    app_q = _run_cli(STATE_CLI, ["approve", "quick", "--by", "duyet nhanh"], repo, home)
    assert app_q.returncode == 0, app_q.stderr
    assert not (repo / "docs" / "tdq" / "plan" / f"{slug}-flow.manifest.json").exists()
    st = tdq_state.load(str(repo))
    assert st["quick_approved"] is True and st["phase"] == "implement"
    assert st["phase_history"][-1]["phase"] == "implement"

    impl_at = datetime.fromisoformat(st["phase_history"][-1]["at"])
    close_now = (impl_at + timedelta(seconds=90)).isoformat(timespec="seconds")
    assert _run_cli(TIMING_CLI, ["close", "--now", close_now], repo, home).returncode == 0
    rows = [json.loads(ln) for ln in (repo / "docs" / "tdq" / "timing.jsonl").read_text(encoding="utf-8").splitlines() if ln.strip()]
    impl_rows = [p for p in rows[-1]["phases"] if p["phase"] == "implement"]
    assert impl_rows and impl_rows[0]["treo_tuong_giay"] > 0


def test_sim_ca3_1346_bench_py_isolation_and_zero_t_hop(tmp_path: Path) -> None:
    """Ca 3 (2026-11-18-1346): bench .py avoids R15-Full while src/ triggers it, and t_hop=0."""
    bench_py = "docs/tdq/bench/2026-11-18-1346-scan/probe.py"
    assert doc_lint.is_product_source_path(bench_py) is False
    assert doc_lint.is_product_source_path("src/probe.py") is True

    plan_dir = tmp_path / "docs" / "tdq" / "plan"
    plan_dir.mkdir(parents=True, exist_ok=True)
    hdr = "\n".join([
        "# PLAN — Bench", "",
        "Ngày: 2026-11-21 · Lane: full · Work kind: investigate", "",  # i18n-allow
        "## Phân bổ Model & Effort", "",  # i18n-allow
        "| Pha | Vai trò | Model | Effort |", "|---|---|---|---|",  # i18n-allow
        "| implement | tdq-explorer | inherit | high |",
        "| qc | tdq-qc-tester | inherit | high |",
        "| report | Leader | inherit | high |", "",
    ]) + "\n"
    bench_plan = plan_dir / "2026-11-21-0100-bench.md"
    bench_plan.write_text(hdr + f"- [ ] **T1.1** Probe — Test: `py -3 {bench_py}`\n  - Chạm: `{bench_py}`\n", encoding="utf-8")  # i18n-allow
    assert doc_lint.r15_loi(doc_lint.Doc(str(bench_plan))) == []

    prod_plan = plan_dir / "2026-11-21-0100-prod.md"
    prod_plan.write_text(hdr + "- [ ] **T1.1** Edit src — Test: `pytest -q`\n  - Chạm: `src/probe.py`\n", encoding="utf-8")  # i18n-allow
    prod_errs = doc_lint.r15_loi(doc_lint.Doc(str(prod_plan)))
    assert any("R15-Full" in e for e in prod_errs)

    hs = {"t_task": 60.0, "t_tick": 5.0, "t_phat": 10.0, "t_kiem": 4.0, "t_hop": 50.0, "t_don": 6.0}
    from tdq_team import Task
    t_no_wt = Task("T1.1", " ", "P1")
    t_no_wt.vung_file = [bench_py]
    t_no_wt.worktree_required = False
    kq = tdq_bench.mo_phong_tasks([t_no_wt], hs)
    assert kq.phi_dot == pytest.approx(hs["t_phat"] + hs["t_kiem"])


def test_sim_ca4_1953_bugfix_two_stage_escalation(tmp_path: Path) -> None:
    """Ca 4 (2026-11-16-1953): block set work_kind=build, require --by, re-enable build gates."""
    repo, home = tmp_path / "ca4", tmp_path / "ca4_home"
    _init_git_ws(repo)
    slug = "2026-11-16-1953-ca4-bug"
    assert _run_cli(STATE_CLI, ["init", slug, "full", "--kind", "investigate", "--bo-qua-lsp", "bugfix"], repo, home).returncode == 0
    assert _run_cli(STATE_CLI, ["set", "phase=spec"], repo, home).returncode == 0

    bad_set = _run_cli(STATE_CLI, ["set", "work_kind=build"], repo, home)
    assert bad_set.returncode != 0 and "escalate-to-build" in bad_set.stderr
    assert tdq_state.load(str(repo))["work_kind"] == "investigate"

    assert _run_cli(STATE_CLI, ["escalate-to-build"], repo, home).returncode != 0

    esc = _run_cli(STATE_CLI, ["escalate-to-build", "--by", "user confirmed fix", "--json"], repo, home)
    assert esc.returncode == 0, esc.stderr
    esc_data = json.loads(esc.stdout)
    assert esc_data["work_kind"] == "build"
    assert esc_data["escalated_from_investigate"]["by"] == "user confirmed fix"

    spec_rel = f"docs/tdq/spec/{slug}.md"
    spec_path = repo / spec_rel
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    spec_lines = [
        "# SPEC — Bugfix", "",
        "Ngày: 2026-11-16 · Lane: full · Work kind: build", "",  # i18n-allow
        "## 3b. Năng lực & công cụ", "",  # i18n-allow
        "| Skill | Nguồn | Phán quyết | Ghi chú |", "|---|---|---|---|",  # i18n-allow
        "| `tdq-build` | plugin | NỀN | workflow |", "",  # i18n-allow
    ]
    spec_path.write_text("\n".join(spec_lines), encoding="utf-8")
    assert _run_cli(STATE_CLI, ["set", f"spec_file={spec_rel}"], repo, home).returncode == 0
    lint_build = _run_cli(LINT_CLI, [str(spec_path)], repo, home)
    assert lint_build.returncode == 1 and "[R10]" in lint_build.stdout
    app_build = _run_cli(STATE_CLI, ["approve", "spec", "--by", "duyet"], repo, home)
    assert app_build.returncode != 0 and "Archify" in app_build.stderr


def _setup_p1_parity_repo(
    root: Path,
    *,
    mode: str,
    domain_id: str | None,
    work_kind: str,
    with_plan: bool = True,
) -> tuple[Path, Path]:
    """Create isolated repo with optional [~] plan task, today log, and P1 state fields."""
    repo, home = _setup_inv_repo(root)
    (repo / "src").mkdir(exist_ok=True)
    (repo / "src" / "app.py").write_text("x = 1\n", encoding="utf-8")
    (repo / "docs" / "tdq" / "research" / "note.md").write_text("# Note\n", encoding="utf-8")
    log_path = repo / tdq_state.today_log_rel()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text("# Log\n\n## 01:00 — setup\n", encoding="utf-8")
    state = tdq_state.load(str(repo), heal=False)
    assert state is not None
    state["implement_mode"] = mode
    state["domain_id"] = domain_id
    state["work_kind"] = work_kind
    if with_plan:
        plan_rel = f"docs/tdq/plan/{SLUG_PARITY}.md"
        plan_path = repo / plan_rel
        plan_path.parent.mkdir(parents=True, exist_ok=True)
        plan_path.write_text(
            "# Plan\n\n"
            "## Model & Effort\n\n"
            "| Phase | Role | Model | Effort |\n|---|---|---|---|\n"
            "| implement | self | inherit | high |\n"
            "| qc | tdq-qc-tester | inherit | high |\n"
            "| report | self | inherit | medium |\n\n"
            "- [~] **T1.1** Fix bug — Test: `py -3 -c \"print('ok')\"`\n",
            encoding="utf-8",
        )
        state["plan_file"] = plan_rel
    tdq_state.save(str(repo), state)
    return repo, home


def _assert_edit_parity(
    r_repo: Path,
    r_home: Path,
    p_repo: Path,
    p_home: Path,
    target: str,
    expected_decision: str,
    *,
    expected_tag: str = "",
    expected_sub: str = "",
    agent_type: str | None = None,
) -> None:
    """Assert identical Rust and Python PreToolUse edit decision and diagnostic markers."""
    sid = "p1-impl" if agent_type else "p1-main"
    payload: dict[str, object] = {
        "conversationId": sid,
        "toolName": "write_to_file",
        "toolInput": {"TargetFile": target},
    }
    if agent_type:
        payload["agent_type"] = agent_type
    _, r_out = _run_hook_engine("rust", {**payload, "cwd": str(r_repo)}, r_repo, r_home)
    _, p_out = _run_hook_engine("python", {**payload, "cwd": str(p_repo)}, p_repo, p_home)
    assert r_out.get("decision") == expected_decision
    assert p_out.get("decision") == expected_decision
    if expected_tag:
        assert expected_tag in r_out.get("reason", "")
        assert expected_tag in p_out.get("reason", "")
    if expected_sub:
        assert expected_sub in r_out.get("reason", "")
        assert expected_sub in p_out.get("reason", "")


def _check_p1_locked_pair(
    base: Path,
    *,
    mode: str,
    domain_id: str | None,
    work_kind: str,
    with_plan: bool = True,
) -> tuple[Path, Path, Path, Path]:
    """Set up Rust/Python repo pair and verify zero-downgrade deny + docs allow."""
    r_repo, r_home = _setup_p1_parity_repo(
        base / "r", mode=mode, domain_id=domain_id, work_kind=work_kind, with_plan=with_plan
    )
    p_repo, p_home = _setup_p1_parity_repo(
        base / "p", mode=mode, domain_id=domain_id, work_kind=work_kind, with_plan=with_plan
    )
    _assert_edit_parity(
        r_repo, r_home, p_repo, p_home, "src/app.py", "deny",
        expected_tag="[TDQ:APPROVE]", expected_sub="escalate-to-build",
    )
    if mode == "subagent":
        _assert_edit_parity(
            r_repo, r_home, p_repo, p_home, "src/app.py", "deny",
            expected_tag="[TDQ:APPROVE]", expected_sub="escalate-to-build",
            agent_type="tdq-implementer",
        )
    _assert_edit_parity(r_repo, r_home, p_repo, p_home, "docs/tdq/research/note.md", "allow")
    return r_repo, r_home, p_repo, p_home


def _check_p1_full_escalation(base: Path) -> None:
    """Verify full-lane escalate-to-build, downgrade lock, plan re-approval, and allow parity."""
    r_repo, r_home, p_repo, p_home = _check_p1_locked_pair(
        base, mode="main", domain_id="research-rca", work_kind="investigate"
    )
    for repo, home in ((r_repo, r_home), (p_repo, p_home)):
        esc = _run_cli(STATE_CLI, ["escalate-to-build", "--by", "fix bug"], repo, home)
        assert esc.returncode == 0, esc.stderr
        st = tdq_state.load(str(repo), heal=False)
        assert st is not None and st["work_kind"] == "build"
        assert st["domain_id"] == "code-build" and st["downgrade_locked"] is True
        assert _run_cli(STATE_CLI, ["set", "domain_id=research-rca"], repo, home).returncode != 0
        assert _run_cli(STATE_CLI, ["set", "work_kind=investigate"], repo, home).returncode != 0
    _assert_edit_parity(
        r_repo, r_home, p_repo, p_home, "src/app.py", "deny", expected_tag="[TDQ:APPROVE]"
    )
    for repo, home in ((r_repo, r_home), (p_repo, p_home)):
        app = _run_cli(STATE_CLI, ["approve", "plan", "--mode", "main", "--by", "fix bug"], repo, home)
        assert app.returncode == 0, app.stderr
    _assert_edit_parity(r_repo, r_home, p_repo, p_home, "src/app.py", "allow")


def test_p1_zero_downgrade_edit_parity_and_rollback(tmp_path: Path) -> None:
    """Verify Rust/Python parity for P1 zero-downgrade lock, escalation, and rollback."""
    for idx, (mode, domain_id, work_kind) in enumerate([
        ("main", "research-rca", "build"),
        ("main", None, "investigate"),
        ("subagent", "research-rca", "build"),
        ("subagent", None, "investigate"),
    ]):
        _check_p1_locked_pair(
            tmp_path / f"lock_{idx}", mode=mode, domain_id=domain_id, work_kind=work_kind
        )
    _check_p1_full_escalation(tmp_path / "esc_full")
    for name, mode, with_plan, exp_dec, exp_tag in [
        ("esc_inline_main", "main", True, "allow", ""),
        ("esc_inline_sub_noplan", "subagent", False, "allow", ""),
        ("esc_inline_sub_plan", "subagent", True, "deny", "[TDQ:TEAM]"),
    ]:
        rr, rh, pr, ph = _check_p1_locked_pair(
            tmp_path / name, mode=mode, domain_id="research-rca",
            work_kind="investigate", with_plan=with_plan,
        )
        for repo, home in ((rr, rh), (pr, ph)):
            esc_in = _run_cli(
                STATE_CLI, ["escalate-to-build", "--by", "fix bug", "--inline-fix"], repo, home
            )
            assert esc_in.returncode == 0, esc_in.stderr
        _assert_edit_parity(rr, rh, pr, ph, "src/app.py", exp_dec, expected_tag=exp_tag)
    for name, mode, domain_id, work_kind, with_plan in [
        ("rb_dom_main", "main", "research-rca", "build", True),
        ("rb_inv_main", "main", None, "investigate", True),
        ("rb_sub", "subagent", "research-rca", "investigate", False),
    ]:
        rr, rh, pr, ph = _check_p1_locked_pair(
            tmp_path / name, mode=mode, domain_id=domain_id,
            work_kind=work_kind, with_plan=with_plan,
        )
        cfg_text = json.dumps({"p1": {"zero_downgrade_enabled": False}})
        (rr / "docs" / "tdq" / "config.json").write_text(cfg_text, encoding="utf-8")
        (pr / "docs" / "tdq" / "config.json").write_text(cfg_text, encoding="utf-8")
        _assert_edit_parity(rr, rh, pr, ph, "src/app.py", "allow")
