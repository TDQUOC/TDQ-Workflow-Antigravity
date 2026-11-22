#!/usr/bin/env python3
"""Red-Green TDD tests for scripts/tdq_simulate_verify.py (6-layer verification)."""

from __future__ import annotations

import json
import os
import re
import shutil
import sys
import tempfile
import time
from pathlib import Path
from unittest import mock

import pytest

WORKTREE_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = WORKTREE_ROOT / "scripts"
TOOLS_DIR = WORKTREE_ROOT / "tools"
PLUGIN_DIR = WORKTREE_ROOT / "plugins" / "tdq-workflow-agy"
for _path in (str(SCRIPTS_DIR), str(TOOLS_DIR)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import archify_delivery
import rtk_integration
import tdq_devtool_mcp
import tdq_setup
import tdq_setup_state
import tdq_simulate_verify as sim_verify
from patches import agy_launchers


def _snapshot_tree(root: Path) -> dict[str, tuple[int, int]]:
    """Capture relative path -> (size, mtime_ns) for non-mutating invariants."""
    if not root.is_dir():
        return {}
    snap: dict[str, tuple[int, int]] = {}
    for item in sorted(root.rglob("*")):
        if item.is_file():
            st = item.stat()
            snap[item.relative_to(root).as_posix()] = (st.st_size, st.st_mtime_ns)
    return snap


def _snapshot_single_file(path: Path) -> tuple[bool, int, int]:
    """Capture (exists, size, mtime_ns) for a single file."""
    if not path.is_file():
        return (False, 0, 0)
    st = path.stat()
    return (True, st.st_size, st.st_mtime_ns)


def _list_sim_dirs(tmp_base: Path) -> set[str]:
    """Return existing tdq_sim_* directory names under `tmp_base`."""
    if not tmp_base.is_dir():
        return set()
    return {p.name for p in tmp_base.iterdir() if p.is_dir() and p.name.startswith("tdq_sim_")}


def _is_pid_alive(pid: int) -> bool:
    """Return True if process `pid` still exists on OS."""
    if pid <= 0:
        return False
    if os.name == "nt":
        import ctypes

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(0x1000, False, pid)
        if not handle:
            return False
        try:
            code = ctypes.c_ulong(0)
            ok = kernel32.GetExitCodeProcess(handle, ctypes.byref(code))
            return bool(ok and code.value == 259)
        finally:
            kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _isolate_sandbox_home(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    preserve_archify: bool = True,
) -> tuple[Path, Path]:
    """Isolate HOME/USERPROFILE/GEMINI_CONFIG_DIR/state inside tmp_path."""
    real_archify = archify_delivery.find_archify_root() if preserve_archify else None
    fake_home = tmp_path / "isolated_home"
    fake_home.mkdir(parents=True, exist_ok=True)
    state_dir = tmp_path / "isolated_state"
    state_dir.mkdir(parents=True, exist_ok=True)
    for key in ("PLUGIN_DATA", "TAVILY_API_KEY", "CHROME_PATH"):
        monkeypatch.delenv(key, raising=False)
    if real_archify:
        monkeypatch.setenv("ARCHIFY_ROOT", str(real_archify))
    else:
        monkeypatch.delenv("ARCHIFY_ROOT", raising=False)
    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.setenv("USERPROFILE", str(fake_home))
    monkeypatch.setenv("GEMINI_CONFIG_DIR", str(fake_home / ".gemini" / "config"))
    monkeypatch.setenv("ANTIGRAVITY_GEMINI_DIR", str(fake_home / ".gemini"))
    monkeypatch.setenv("TDQ_SETUP_STATE_DIR", str(state_dir))
    monkeypatch.setenv("TDQ_KHONG_CHAM_MAY", "1")
    return fake_home, state_dir


def _build_echo_mcp_server(script_path: Path) -> None:
    """Write a minimal stdio JSON-RPC 2.0 MCP echo server for pipe tests."""
    code = '''import json, sys
for line in sys.stdin:
    raw = line.strip()
    if not raw:
        continue
    msg = json.loads(raw)
    req_id = msg.get("id")
    method = msg.get("method", "")
    if req_id is None:
        continue
    if method == "initialize":
        res = {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "sim-tavily", "version": "1.0"},
        }
    elif method == "tools/list":
        res = {"tools": [{"name": "tavily_search", "description": "Use this tool to search the web."}]}
    else:
        res = {}
    sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": req_id, "result": res}) + "\\n")
    sys.stdout.flush()
'''
    script_path.write_text(code, encoding="utf-8")


def test_full_six_layer_verify_compiled_plugin_and_snapshot_invariant(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Run all 6 layers against plugins/tdq-workflow-agy without mutating ~/.gemini/config or repo state."""
    real_gemini_cfg = Path(os.path.expanduser("~")) / ".gemini" / "config"
    real_repo_state = WORKTREE_ROOT / "docs" / "tdq" / "state.json"
    before_cfg = _snapshot_tree(real_gemini_cfg)
    before_repo_state = _snapshot_single_file(real_repo_state)

    _isolate_sandbox_home(monkeypatch, tmp_path, preserve_archify=True)
    data_dir = tmp_path / "verify_data"
    tmp_base = Path(tempfile.gettempdir())
    before_sim_dirs = _list_sim_dirs(tmp_base)

    result = sim_verify.run_simulate_verify(plugin_root=PLUGIN_DIR, data_dir=data_dir)

    assert result["core_gate"] == "PASS"
    assert result["optional_gate"] == "SKIPPED"
    assert result["temp_cleaned"] is True
    assert result["config_untouched"] is True
    assert result["elapsed_sec"] < 90.0
    assert _list_sim_dirs(tmp_base) == before_sim_dirs
    assert _snapshot_tree(real_gemini_cfg) == before_cfg
    assert _snapshot_single_file(real_repo_state) == before_repo_state

    layers = result["layers"]
    assert set(layers.keys()) == {"T1", "T2", "T3", "T4", "T5", "T6"}
    for name in ("T1", "T2", "T3", "T4", "T5", "T6"):
        assert layers[name]["status"] == "PASS", f"{name} failed: {layers[name]}"

    # T1: bundle validation + toolchain probe
    t1_details = layers["T1"]["details"]
    assert t1_details["toolchain"]["schema_version"] == 1
    assert t1_details["toolchain"]["node"]["usable"] is True
    assert t1_details["toolchain"]["python"]["usable"] is True
    if shutil.which("agy") or shutil.which("agy.EXE"):
        assert t1_details["agy_validate"]["ok"] is True

    # T2: all 6 lifecycle hooks + Rust hot hooks < 50ms
    t2_details = layers["T2"]["details"]
    assert t2_details["engine"] == "rust_binary"
    events = t2_details["events"]
    assert set(events.keys()) == {
        "SessionStart",
        "PreInvocation",
        "PreToolUse",
        "PostToolUse",
        "PostInvocation",
        "Stop",
    }
    for hot in ("PreToolUse", "PostToolUse", "PostInvocation", "Stop"):
        assert events[hot]["returncode"] == 0
        assert events[hot]["elapsed_ms"] < 50.0, f"Hot hook {hot} took {events[hot]['elapsed_ms']}ms"

    # T3: LSP handshake + Caveman shrink check + skipped optional add-ons
    t3_details = layers["T3"]["details"]
    assert t3_details["lsp"]["tools_count"] >= 60
    assert t3_details["caveman"]["shrink_verified"] is True
    assert result["optional_addons"]["tavily_primary"]["status"] == "SKIPPED"
    assert result["optional_addons"]["chrome_devtools"]["status"] == "SKIPPED"

    # T4: LSP semantic find_symbol + graphify check
    t4_details = layers["T4"]["details"]
    assert t4_details["lsp_semantic"]["symbol_found"] is True
    if shutil.which("graphify"):
        assert t4_details["graphify"]["status"] == "PASS"

    # T5: rtk+rg smoke + archify HTML render strictly inside sandbox
    t5_details = layers["T5"]["details"]
    if t5_details["archify"]["status"] == "PASS":
        assert "tdq_sim_" in t5_details["archify"]["output_path"]

    # T6: 8 agents + subagent lifecycle hooks
    t6_details = layers["T6"]["details"]
    assert t6_details["agents_count"] == 8
    assert t6_details["subagent_hooks"]["PreInvocation"]["returncode"] == 0
    assert t6_details["subagent_hooks"]["SubagentStop"]["returncode"] == 0


def test_repo_root_python_hook_fallback_and_missing_optional_addons(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Repo root without compiled bin/ falls back to Python hooks and separates optional gate."""
    _isolate_sandbox_home(monkeypatch, tmp_path, preserve_archify=True)
    data_dir = tmp_path / "repo_data"

    with mock.patch.object(tdq_devtool_mcp, "get_chrome_executable", return_value=""):
        result = sim_verify.run_simulate_verify(plugin_root=WORKTREE_ROOT, data_dir=data_dir)

    assert result["core_gate"] == "PASS"
    assert result["optional_gate"] == "SKIPPED"
    assert result["temp_cleaned"] is True
    assert result["layers"]["T2"]["details"]["engine"] == "python_fallback"
    assert set(result["layers"]["T2"]["details"]["events"].keys()) == {
        "SessionStart",
        "PreInvocation",
        "PreToolUse",
        "PostToolUse",
        "PostInvocation",
        "Stop",
    }
    assert result["layers"]["T6"]["details"]["agents_count"] == 8
    assert "SubagentStart" in result["layers"]["T6"]["details"]["subagent_hooks"]


def test_caveman_node_launcher_and_graphify_graceful_skip(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify Node caveman launcher mode and graceful graphify skip when absent."""
    _isolate_sandbox_home(monkeypatch, tmp_path, preserve_archify=False)
    fake_plugin = tmp_path / "node_plugin"
    (fake_plugin / "scripts").mkdir(parents=True)
    agy_launchers.generate_launchers(fake_plugin)
    shutil.copy2(SCRIPTS_DIR / "tdq_mcp_shrink.py", fake_plugin / "scripts" / "tdq_mcp_shrink.py")
    shutil.copy2(SCRIPTS_DIR / "utf8_io.py", fake_plugin / "scripts" / "utf8_io.py")

    cav_res = sim_verify._probe_caveman_wrapper(fake_plugin, dict(os.environ), timeout_sec=10.0)
    assert cav_res["shrink_verified"] is True
    assert cav_res["wrapper_mode"] == "node_launcher"
    assert cav_res["tools_count"] >= 60

    orig_which = shutil.which

    def _no_graphify(name: str, *args: object, **kwargs: object) -> str | None:
        if name == "graphify":
            return None
        return orig_which(name, *args, **kwargs)

    sample_repo = sim_verify._create_sample_repo(tmp_path / "sample_no_graph")
    with mock.patch.object(sim_verify.shutil, "which", side_effect=_no_graphify):
        ok, graph_info = sim_verify._probe_graphify_sample(
            sample_repo, dict(os.environ), deadline=time.monotonic() + 10.0
        )
    assert ok is True
    assert graph_info["status"] == "SKIPPED"


def test_tavily_secret_handshake_redacted_and_timeout_kills_children(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Present TAVILY_API_KEY runs JSON-RPC handshake without leaking secret; timeout kills child."""
    _isolate_sandbox_home(monkeypatch, tmp_path, preserve_archify=False)
    secret_val = "tvly-sim-secret-must-never-leak-777"
    data_dir = tmp_path / "secret_state"
    tdq_setup_state.save_tavily_secret(secret_val, data_dir=data_dir)

    fake_mcp_plugin = tmp_path / "fake_plugin"
    (fake_mcp_plugin / "scripts").mkdir(parents=True)
    stub_srv = tmp_path / "tavily_stub.py"
    _build_echo_mcp_server(stub_srv)
    (fake_mcp_plugin / "mcp_config.json").write_text(
        json.dumps({
            "mcpServers": {
                "tavily-primary": {
                    "command": sys.executable,
                    "args": [str(stub_srv)],
                }
            }
        }),
        encoding="utf-8",
    )

    tav_res = sim_verify._probe_optional_tavily(
        mcp_cfg=json.loads((fake_mcp_plugin / "mcp_config.json").read_text(encoding="utf-8")),
        cfg_root=fake_mcp_plugin,
        data_dir=data_dir,
        env=dict(os.environ),
        timeout_sec=5.0,
    )
    assert tav_res["status"] == "PASS"
    assert tav_res["tools_count"] == 1
    captured = capsys.readouterr()
    assert secret_val not in captured.out
    assert secret_val not in captured.err
    assert secret_val not in json.dumps(tav_res)

    # Timeout test: hung MCP server must raise TimeoutError and leave zero live child PIDs
    pid_file = tmp_path / "hung.pid"
    hung_srv = tmp_path / "hung_mcp.py"
    hung_srv.write_text(
        f"import os, pathlib, time\n"
        f"pathlib.Path({json.dumps(str(pid_file))}).write_text(str(os.getpid()), encoding='utf-8')\n"
        f"time.sleep(30)\n",
        encoding="utf-8",
    )
    with pytest.raises(TimeoutError):
        sim_verify.run_mcp_jsonrpc_handshake(
            [sys.executable, str(hung_srv)],
            cwd=tmp_path,
            env=dict(os.environ),
            timeout_sec=0.4,
        )
    if pid_file.is_file():
        hung_pid = int(pid_file.read_text(encoding="utf-8").strip())
        assert not _is_pid_alive(hung_pid), f"Child process {hung_pid} leaked after timeout"


def test_rtk_collision_fails_t5_and_agent_validation_rejects_bad_frontmatter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """RTK collision fails T5; missing Archify skips; bad agent markdown fails T6 validator."""
    _isolate_sandbox_home(monkeypatch, tmp_path, preserve_archify=False)
    sample_repo = tmp_path / "sample_repo"
    sample_repo.mkdir()
    (sample_repo / "util.py").write_text("def calc_sum(a, b):\n    return a + b\n", encoding="utf-8")
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()

    with mock.patch.object(
        rtk_integration,
        "probe_rtk",
        return_value={"valid": False, "collision": True, "reason": "collision_rust_type_kit"},
    ), mock.patch.object(
        rtk_integration, "locate_rg_binary", return_value=""
    ), mock.patch.object(
        archify_delivery,
        "check_environment",
        return_value={"node_ok": True, "node_version": "v22.0.0", "archify_root": "", "ready": False, "error": "missing"},
    ):
        t5_fail = sim_verify._run_t5_rtk_and_archify(
            sample_repo=sample_repo,
            sandbox=sandbox,
            env=dict(os.environ),
            timeout_sec=10.0,
            log_file=None,
        )
    assert t5_fail["status"] == "FAIL"
    assert t5_fail["details"]["rtk_rg"]["collision"] is True
    assert t5_fail["details"]["archify"]["status"] == "SKIPPED"

    bad_agent = tmp_path / "tdq-explorer.md"
    bad_agent.write_text("---\nname: tdq-explorer\n---\n\nMissing fields.\n", encoding="utf-8")
    assert sim_verify._validate_agent_markdown(bad_agent, require_tools=True) is False


def test_forced_exception_mid_layer_cleans_sandbox_and_logs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Mid-layer failure still runs finally, cleans tdq_sim_* sandbox, and keeps logging contract."""
    _isolate_sandbox_home(monkeypatch, tmp_path, preserve_archify=True)
    data_dir = tmp_path / "err_data"
    tmp_base = Path(tempfile.gettempdir())
    before_sim_dirs = _list_sim_dirs(tmp_base)

    monkeypatch.setenv("TDQ_LOG", "1")
    with mock.patch.object(
        sim_verify, "_run_t4_lsp_and_graphify", side_effect=RuntimeError("forced_mid_layer_boom")
    ):
        res = sim_verify.run_simulate_verify(plugin_root=PLUGIN_DIR, data_dir=data_dir)

    err_text = capsys.readouterr().err
    assert res["core_gate"] == "FAIL"
    assert res["temp_cleaned"] is True
    assert _list_sim_dirs(tmp_base) == before_sim_dirs
    assert any("forced_mid_layer_boom" in e for e in res["errors"])
    assert re.search(r"\[\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", err_text)
    log_path = data_dir / "logs" / "tdq-simulate-verify.log"
    assert log_path.is_file()
    assert "tdq_simulate_verify" in log_path.read_text(encoding="utf-8")

    # TDQ_LOG=0 mutes stderr completely
    monkeypatch.setenv("TDQ_LOG", "0")
    capsys.readouterr()
    rc = sim_verify.main(["--plugin-root", str(PLUGIN_DIR), "--state-dir", str(data_dir), "--json"])
    out_muted = capsys.readouterr()
    assert rc == 0
    assert out_muted.err == ""
    parsed = json.loads(out_muted.out)
    assert parsed["core_gate"] == "PASS"


def test_integration_tdq_setup_post_restart_verify_clears_pending_flag(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """tdq_setup.py --post-restart-verify --confirm-restarted --json transitions state to verified."""
    _isolate_sandbox_home(monkeypatch, tmp_path, preserve_archify=True)
    state_dir = tmp_path / "setup_state"
    tdq_setup_state.save_setup_state(
        {
            "version": 2,
            "status": "awaiting_restart",
            "host": "antigravity",
            "host_fingerprint": "old-fp-000",
        },
        pending=True,
        data_dir=state_dir,
    )
    assert (state_dir / tdq_setup_state.PENDING_FLAG_FILENAME).is_file()

    monkeypatch.setenv("TDQ_LOG", "0")
    rc = tdq_setup.main([
        "--post-restart-verify",
        "--state-dir",
        str(state_dir),
        "--confirm-restarted",
        "--json",
    ])
    captured = capsys.readouterr()
    assert rc == 0
    payload = json.loads(captured.out)
    assert payload["status"] == "verified"
    assert payload["verify"]["core_gate"] == "PASS"
    assert payload["verify"]["temp_cleaned"] is True
    assert not (state_dir / tdq_setup_state.PENDING_FLAG_FILENAME).exists()
    persisted = tdq_setup_state.load_setup_state(data_dir=state_dir)
    assert persisted["status"] == "verified"
    assert persisted["pending_flag"] is False


def test_sandbox_env_suppresses_bytecode_and_snapshot_skips_pycache(tmp_path: Path) -> None:
    """First verify right after clean install must not fail config_untouched due to .pyc files."""
    sandbox = tmp_path / "sb"
    sample_repo = tmp_path / "repo"
    sample_repo.mkdir()
    s_env = sim_verify._sandbox_env(sandbox, WORKTREE_ROOT, sample_repo)
    assert s_env["PYTHONDONTWRITEBYTECODE"] == "1"

    cfg_dir = tmp_path / ".gemini" / "config"
    plugin_scripts = cfg_dir / "plugins" / "tdq-workflow-agy" / "scripts"
    plugin_scripts.mkdir(parents=True)
    (cfg_dir / "config.json").write_text("{}\n", encoding="utf-8")
    before = sim_verify._snapshot_tree(cfg_dir)

    pycache = plugin_scripts / "__pycache__"
    pycache.mkdir()
    (pycache / "tdq_setup.cpython-313.pyc").write_bytes(b"pyc-bytes")
    assert sim_verify._snapshot_tree(cfg_dir) == before

    (cfg_dir / "config.json").write_text('{"mutated": true}\n', encoding="utf-8")
    assert sim_verify._snapshot_tree(cfg_dir) != before
