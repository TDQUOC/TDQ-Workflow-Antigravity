#!/usr/bin/env python3
"""Subprocess and API verification for the setup/verify ISO-8601 log service.

Covers default-on ISO-8601 stderr logging, `${PLUGIN_DATA}/logs/` file output,
complete silence under `TDQ_LOG=0` and `--khong-log` with uncorrupted JSON stdout,
and secret redaction across all setup and verify modules.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

WORKTREE_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = WORKTREE_ROOT / "scripts"
PLUGIN_DIR = WORKTREE_ROOT / "plugins" / "tdq-workflow-agy"
MCP_LAUNCHER_MJS = PLUGIN_DIR / "scripts" / "tdq_mcp_launcher.mjs"
PROBE_MJS = SCRIPTS_DIR / "tdq_setup_probe.mjs"
ISO_LOG_LINE_RE = re.compile(r"^\[\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")
FAKE_TAVILY_SECRET = "tvly-secret-test-999"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import tdq_setup_state


def _build_isolated_env(
    tmp_path: Path,
    *,
    name: str,
    tdq_log: str | None = None,
    use_plugin_data: bool = True,
    state_dir: Path | None = None,
    dry_run: bool = True,
) -> tuple[dict[str, str], Path, Path]:
    """Create an isolated subprocess environment strictly scoped to `tmp_path`."""
    root = tmp_path / name
    home_dir = root / "home"
    plugin_data_dir = root / "plugin_data"
    project_dir = root / "project"
    home_dir.mkdir(parents=True, exist_ok=True)
    project_dir.mkdir(parents=True, exist_ok=True)

    env = dict(os.environ)
    for key in (
        "TDQ_LOG",
        "TDQ_SETUP_STATE_DIR",
        "PLUGIN_DATA",
        "TAVILY_API_KEY",
        "CHROME_PATH",
        "ARCHIFY_ROOT",
        "TDQ_KHONG_CHAM_MAY",
        "TDQ_MCP_OVERRIDE_CMD",
    ):
        env.pop(key, None)

    env["HOME"] = str(home_dir)
    env["USERPROFILE"] = str(home_dir)
    env["GEMINI_CONFIG_DIR"] = str(home_dir / ".gemini" / "config")
    env["ANTIGRAVITY_GEMINI_DIR"] = str(home_dir / ".gemini")
    env["TDQ_PROJECT_DIR"] = str(project_dir)
    env["TDQ_HOST"] = "antigravity"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    if dry_run:
        env["TDQ_KHONG_CHAM_MAY"] = "1"
    if use_plugin_data:
        env["PLUGIN_DATA"] = str(plugin_data_dir)
    if state_dir is not None:
        env["TDQ_SETUP_STATE_DIR"] = str(state_dir)
    if tdq_log is not None:
        env["TDQ_LOG"] = tdq_log
    return env, home_dir, plugin_data_dir


def _run_subprocess(
    cmd: list[str],
    env: dict[str, str],
    *,
    cwd: Path = WORKTREE_ROOT,
    timeout: float = 45.0,
) -> subprocess.CompletedProcess[str]:
    """Execute one subprocess cleanly with UTF-8 stdio and no Windows console flash."""
    kwargs: dict[str, Any] = {
        "cwd": str(cwd),
        "env": env,
        "capture_output": True,
        "text": True,
        "encoding": "utf-8",
        "errors": "replace",
        "timeout": timeout,
    }
    if os.name == "nt":
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
    return subprocess.run(cmd, check=False, **kwargs)


def _assert_iso_stderr_and_json(
    proc: subprocess.CompletedProcess[str],
    *,
    expected_marker: str | None = None,
) -> dict[str, Any]:
    """Assert non-empty ISO-8601 stderr lines and valid JSON dict on stdout."""
    lines = [line for line in proc.stderr.splitlines() if line.strip()]
    assert lines, f"Expected ISO-8601 log lines on stderr, got empty: {proc.stderr!r}"
    for line in lines:
        assert ISO_LOG_LINE_RE.match(line), f"Non-ISO log line on stderr: {line!r}"
    if expected_marker is not None:
        assert expected_marker in proc.stderr
    parsed = json.loads(proc.stdout)
    assert isinstance(parsed, dict)
    return parsed


def _assert_muted_stderr_and_json(
    proc: subprocess.CompletedProcess[str],
) -> dict[str, Any]:
    """Assert completely empty stderr and uncorrupted JSON dict on stdout."""
    assert proc.stderr == "", f"Expected silent stderr under TDQ_LOG=0, got: {proc.stderr!r}"
    parsed = json.loads(proc.stdout)
    assert isinstance(parsed, dict)
    return parsed


def _assert_log_file_iso_lines(log_path: Path, expected_token: str) -> None:
    """Assert disk log file exists, is non-empty, and uses ISO-8601 timestamps."""
    assert log_path.is_file(), f"Missing expected log file: {log_path}"
    content = log_path.read_text(encoding="utf-8")
    lines = [line for line in content.splitlines() if line.strip()]
    assert lines, f"Log file is empty: {log_path}"
    for line in lines:
        assert ISO_LOG_LINE_RE.match(line), f"Non-ISO line in {log_path}: {line!r}"
    assert expected_token in content


def test_python_setup_state_and_setup_scan_stderr_toggles(tmp_path: Path) -> None:
    """Verify tdq_setup_state.py and tdq_setup.py --scan-json default logs and silencing."""
    state_dir = tmp_path / "python_state"
    env_on, _, _ = _build_isolated_env(
        tmp_path, name="py_on", tdq_log=None, use_plugin_data=False, state_dir=state_dir
    )
    env_off, _, _ = _build_isolated_env(
        tmp_path, name="py_off", tdq_log="0", use_plugin_data=False, state_dir=state_dir
    )

    state_cli = [sys.executable, "-X", "utf8", str(SCRIPTS_DIR / "tdq_setup_state.py")]
    st_on = _run_subprocess([*state_cli, "status", "--json"], env_on)
    assert st_on.returncode == 0
    assert _assert_iso_stderr_and_json(
        st_on, expected_marker="tdq_setup_state:"
    )["state"]["status"] == "idle"

    st_off = _run_subprocess([*state_cli, "status", "--json"], env_off)
    assert st_off.returncode == 0
    assert _assert_muted_stderr_and_json(st_off)["state"]["status"] == "idle"

    st_flag = _run_subprocess([*state_cli, "--khong-log", "fingerprint", "--json"], env_on)
    assert st_flag.returncode == 0
    assert "fingerprint" in _assert_muted_stderr_and_json(st_flag)

    setup_cli = [sys.executable, "-X", "utf8", str(SCRIPTS_DIR / "tdq_setup.py")]
    scan_on = _run_subprocess([*setup_cli, "--scan-json"], env_on)
    assert scan_on.returncode == 0
    manifest = _assert_iso_stderr_and_json(scan_on, expected_marker="scan_setup_manifest")
    assert manifest["host"] == "antigravity"
    assert manifest["claude_debt_count"] == 0

    scan_off = _run_subprocess([*setup_cli, "--scan-json"], env_off)
    assert scan_off.returncode == 0
    assert _assert_muted_stderr_and_json(scan_off)["host"] == "antigravity"

    scan_flag = _run_subprocess([*setup_cli, "--scan-json", "--khong-log"], env_on)
    assert scan_flag.returncode == 0
    assert _assert_muted_stderr_and_json(scan_flag)["host"] == "antigravity"


def test_node_probe_stderr_and_tdq_log_zero(tmp_path: Path) -> None:
    """Verify tdq_setup_probe.mjs emits ISO-8601 stderr by default and obeys TDQ_LOG=0."""
    node_bin = shutil.which("node")
    assert node_bin, "node executable is required for ESM subprocess checks"

    probe_env_on, _, _ = _build_isolated_env(
        tmp_path, name="probe_on", tdq_log=None, use_plugin_data=False
    )
    probe_env_on["PATH"] = ""
    if os.name == "nt" and "SystemRoot" in os.environ:
        probe_env_on["SystemRoot"] = os.environ["SystemRoot"]
    probe_env_off = {**probe_env_on, "TDQ_LOG": "0"}

    probe_on = _run_subprocess([node_bin, str(PROBE_MJS), "--json"], probe_env_on)
    assert probe_on.returncode == 0
    assert _assert_iso_stderr_and_json(
        probe_on, expected_marker="tdq_setup_probe:"
    )["schema_version"] == 1

    probe_off = _run_subprocess([node_bin, str(PROBE_MJS), "--json"], probe_env_off)
    assert probe_off.returncode == 0
    assert _assert_muted_stderr_and_json(probe_off)["schema_version"] == 1


def test_node_mcp_launcher_stderr_and_tdq_log_zero(tmp_path: Path) -> None:
    """Verify tdq_mcp_launcher.mjs logInfo ISO stderr, secret safety, and TDQ_LOG=0."""
    node_bin = shutil.which("node")
    assert node_bin, "node executable is required for ESM subprocess checks"

    launcher_state = tmp_path / "launcher_state"
    launcher_state.mkdir(parents=True, exist_ok=True)
    (launcher_state / "secrets.env").write_text(
        f"TAVILY_API_KEY={FAKE_TAVILY_SECRET}\n", encoding="utf-8"
    )
    probe_child = tmp_path / "echo_probe.mjs"
    probe_child.write_text(
        'process.stdout.write(JSON.stringify({ok: true, has_key: Boolean(process.env.TAVILY_API_KEY)}) + "\\n");\n',
        encoding="utf-8",
    )

    env_on, _, _ = _build_isolated_env(
        tmp_path, name="mcp_on", tdq_log=None, use_plugin_data=False, state_dir=launcher_state
    )
    env_on["TDQ_MCP_OVERRIDE_CMD"] = node_bin
    env_off = {**env_on, "TDQ_LOG": "0"}

    mcp_on = _run_subprocess([node_bin, str(MCP_LAUNCHER_MJS), "lsp", str(probe_child)], env_on)
    assert mcp_on.returncode == 0
    assert _assert_iso_stderr_and_json(mcp_on, expected_marker="tdq_mcp_launcher:") == {
        "ok": True,
        "has_key": True,
    }
    assert "loaded 1 env key(s) from secrets.env" in mcp_on.stderr
    assert FAKE_TAVILY_SECRET not in mcp_on.stdout
    assert FAKE_TAVILY_SECRET not in mcp_on.stderr

    mcp_off = _run_subprocess([node_bin, str(MCP_LAUNCHER_MJS), "lsp", str(probe_child)], env_off)
    assert mcp_off.returncode == 0
    assert _assert_muted_stderr_and_json(mcp_off) == {"ok": True, "has_key": True}

    err_env_on = {**env_on, "TDQ_MCP_OVERRIDE_CMD": "nonexistent-tdq-mcp-probe-bin"}
    missing_on = _run_subprocess([node_bin, str(MCP_LAUNCHER_MJS), "lsp"], err_env_on)
    assert missing_on.returncode != 0
    assert ISO_LOG_LINE_RE.match(missing_on.stderr.splitlines()[0])
    assert "tdq_mcp_launcher: spawn error" in missing_on.stderr

    missing_off = _run_subprocess(
        [node_bin, str(MCP_LAUNCHER_MJS), "lsp"], {**err_env_on, "TDQ_LOG": "0"}
    )
    assert missing_off.returncode != 0
    assert missing_off.stderr == ""


def test_setup_disk_log_file_created_and_suppressed(tmp_path: Path) -> None:
    """Verify PLUGIN_DATA/logs/setup.log creation and TDQ_LOG=0 / --khong-log suppression."""
    env_on, _, data_on = _build_isolated_env(
        tmp_path, name="setup_disk_on", tdq_log=None, use_plugin_data=True, dry_run=False
    )
    env_off, _, data_off = _build_isolated_env(
        tmp_path, name="setup_disk_off", tdq_log="0", use_plugin_data=True, dry_run=False
    )
    setup_cli = [sys.executable, "-X", "utf8", str(SCRIPTS_DIR / "tdq_setup.py")]

    set_on = _run_subprocess(
        [*setup_cli, "--set-tavily-key", "tvly-disk-log-check-1", "--json"], env_on
    )
    assert set_on.returncode == 0
    assert _assert_iso_stderr_and_json(set_on)["ok"] is True
    _assert_log_file_iso_lines(data_on / "logs" / "setup.log", "--set-tavily-key")

    set_off = _run_subprocess(
        [*setup_cli, "--set-tavily-key", "tvly-disk-log-check-2", "--json"], env_off
    )
    assert set_off.returncode == 0
    assert _assert_muted_stderr_and_json(set_off)["ok"] is True
    assert not (data_off / "logs" / "setup.log").exists()

    khong_state = tmp_path / "setup_khong_state"
    env_dry, _, _ = _build_isolated_env(
        tmp_path, name="setup_flag", tdq_log=None, use_plugin_data=False, dry_run=True
    )
    set_flag = _run_subprocess(
        [
            *setup_cli,
            "--set-tavily-key",
            "tvly-disk-log-check-3",
            "--state-dir",
            str(khong_state),
            "--khong-log",
            "--json",
        ],
        env_dry,
    )
    assert set_flag.returncode == 0
    assert _assert_muted_stderr_and_json(set_flag)["ok"] is True
    assert not (khong_state / "logs" / "setup.log").exists()


def test_simulate_verify_disk_log_file_created_and_suppressed(tmp_path: Path) -> None:
    """Verify PLUGIN_DATA/logs/tdq-simulate-verify.log creation and TDQ_LOG=0 suppression."""
    env_on, _, data_on = _build_isolated_env(
        tmp_path, name="sim_disk_on", tdq_log=None, use_plugin_data=True, dry_run=False
    )
    env_off, _, data_off = _build_isolated_env(
        tmp_path, name="sim_disk_off", tdq_log="0", use_plugin_data=True, dry_run=False
    )
    verify_cli = [
        sys.executable,
        "-X",
        "utf8",
        str(SCRIPTS_DIR / "tdq_simulate_verify.py"),
        "--plugin-root",
        str(PLUGIN_DIR),
        "--json",
    ]

    sim_on = _run_subprocess(verify_cli, env_on, timeout=60.0)
    assert sim_on.returncode == 0, sim_on.stderr
    assert _assert_iso_stderr_and_json(
        sim_on, expected_marker="tdq_simulate_verify:"
    )["core_gate"] == "PASS"
    _assert_log_file_iso_lines(
        data_on / "logs" / "tdq-simulate-verify.log", "tdq_simulate_verify:"
    )

    sim_off = _run_subprocess(verify_cli, env_off, timeout=60.0)
    assert sim_off.returncode == 0, sim_off.stderr
    assert _assert_muted_stderr_and_json(sim_off)["core_gate"] == "PASS"
    assert not (data_off / "logs" / "tdq-simulate-verify.log").exists()

    khong_state = tmp_path / "sim_khong_state"
    env_dry, _, _ = _build_isolated_env(
        tmp_path, name="sim_flag", tdq_log=None, use_plugin_data=False, dry_run=True
    )
    sim_flag = _run_subprocess(
        [*verify_cli, "--state-dir", str(khong_state), "--khong-log"],
        env_dry,
        timeout=60.0,
    )
    assert sim_flag.returncode == 0, sim_flag.stderr
    assert _assert_muted_stderr_and_json(sim_flag)["core_gate"] == "PASS"
    assert not (khong_state / "logs" / "tdq-simulate-verify.log").exists()


def test_secret_redaction_in_state_api(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Ensure tdq_setup_state.save_tavily_secret redacts secrets and honors TDQ_LOG=0."""
    api_state = tmp_path / "api_secret_state"
    monkeypatch.delenv("TDQ_LOG", raising=False)
    tdq_setup_state.save_tavily_secret(FAKE_TAVILY_SECRET, data_dir=api_state)
    api_cap = capsys.readouterr()
    assert ISO_LOG_LINE_RE.match(api_cap.err.strip())
    assert FAKE_TAVILY_SECRET not in api_cap.out
    assert FAKE_TAVILY_SECRET not in api_cap.err

    monkeypatch.setenv("TDQ_LOG", "0")
    tdq_setup_state.save_tavily_secret(FAKE_TAVILY_SECRET, data_dir=api_state)
    assert capsys.readouterr().err == ""


def test_secret_redaction_across_setup_cli_and_logs(tmp_path: Path) -> None:
    """Ensure --set-tavily-key never leaks secret to stdout, stderr, state JSON, or logs."""
    cli_state_on = tmp_path / "cli_secret_on"
    cli_state_off = tmp_path / "cli_secret_off"
    tdq_setup_state.save_setup_state(
        {"version": 2, "status": "awaiting_restart"},
        pending=True,
        data_dir=cli_state_on,
    )

    env_on, _, _ = _build_isolated_env(
        tmp_path, name="sec_on", tdq_log=None, use_plugin_data=False, state_dir=cli_state_on
    )
    env_off, _, _ = _build_isolated_env(
        tmp_path, name="sec_off", tdq_log="0", use_plugin_data=False, state_dir=cli_state_off
    )
    setup_cli = [sys.executable, "-X", "utf8", str(SCRIPTS_DIR / "tdq_setup.py")]

    res_on = _run_subprocess(
        [*setup_cli, "--set-tavily-key", FAKE_TAVILY_SECRET, "--state-dir", str(cli_state_on), "--json"],
        env_on,
    )
    res_off = _run_subprocess(
        [*setup_cli, "--set-tavily-key", FAKE_TAVILY_SECRET, "--state-dir", str(cli_state_off), "--json"],
        env_off,
    )
    assert res_on.returncode == 0
    assert res_off.returncode == 0
    stderr_on, stderr_off = res_on.stderr, res_off.stderr
    assert FAKE_TAVILY_SECRET not in stderr_on and stderr_off == ""
    assert FAKE_TAVILY_SECRET not in res_on.stdout
    assert FAKE_TAVILY_SECRET not in res_off.stdout
    assert json.loads(res_on.stdout)["ok"] is True
    assert json.loads(res_off.stdout)["ok"] is True

    scan_res = _run_subprocess([*setup_cli, "--scan-json"], env_on)
    assert scan_res.returncode == 0
    assert FAKE_TAVILY_SECRET not in scan_res.stdout
    assert FAKE_TAVILY_SECRET not in scan_res.stderr
    assert json.loads(scan_res.stdout)["optional_companions"]["tavily"]["key_configured"] is True

    assert FAKE_TAVILY_SECRET in (cli_state_on / "secrets.env").read_text(encoding="utf-8")
    assert FAKE_TAVILY_SECRET not in (cli_state_on / "setup-state.json").read_text(encoding="utf-8")

    log_files = sorted((cli_state_on / "logs").glob("*.log"))
    assert log_files, "Expected at least one .log file under <state_dir>/logs/"
    for log_file in log_files:
        assert FAKE_TAVILY_SECRET not in log_file.read_text(encoding="utf-8")
    assert not (cli_state_off / "logs" / "setup.log").exists()
