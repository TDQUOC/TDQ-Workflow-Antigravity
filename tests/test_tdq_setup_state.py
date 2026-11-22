"""Isolated unit tests for scripts/tdq_setup_state.py (Red -> Green TDD)."""

from __future__ import annotations

import datetime
import json
import os
import stat
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import tdq_setup_state as setup_state  # noqa: E402


def _clear_state_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Clear state-resolution environment overrides for deterministic tests."""
    for key in (
        "TDQ_SETUP_STATE_DIR",
        "TDQ_KHONG_CHAM_MAY",
        "PLUGIN_DATA",
        "GEMINI_CONFIG_DIR",
        "HOME",
        "USERPROFILE",
    ):
        monkeypatch.delenv(key, raising=False)


def test_resolve_plugin_data_dir_precedence(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Verify full precedence chain and TDQ_KHONG_CHAM_MAY=1 isolation."""
    _clear_state_env(monkeypatch)
    fake_home = tmp_path / "home"
    real_plugin_data = tmp_path / "real_plugin_data"
    override_dir = tmp_path / "override_state"

    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.setenv("USERPROFILE", str(fake_home))
    monkeypatch.setenv("PLUGIN_DATA", str(real_plugin_data))

    assert setup_state.resolve_plugin_data_dir() == real_plugin_data

    monkeypatch.setenv("TDQ_KHONG_CHAM_MAY", "1")
    expected = (
        fake_home / ".gemini" / "antigravity" / "plugin_data" / "tdq-workflow-agy"
    )
    assert setup_state.resolve_plugin_data_dir() == expected

    monkeypatch.setenv("TDQ_SETUP_STATE_DIR", str(override_dir))
    assert setup_state.resolve_plugin_data_dir() == override_dir
    assert setup_state.resolve_plugin_data_dir(home=str(tmp_path / "x")) == override_dir


def test_resolve_plugin_data_dir_gemini_config_variants(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Handle GEMINI_CONFIG_DIR pointing at ~/.gemini/config or ~/.gemini."""
    _clear_state_env(monkeypatch)
    fake_home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.setenv("USERPROFILE", str(fake_home))

    cfg_sub = tmp_path / "agy_root" / ".gemini" / "config"
    monkeypatch.setenv("GEMINI_CONFIG_DIR", str(cfg_sub))
    expected_sub = (
        tmp_path
        / "agy_root"
        / ".gemini"
        / "antigravity"
        / "plugin_data"
        / "tdq-workflow-agy"
    )
    assert setup_state.resolve_plugin_data_dir() == expected_sub

    gemini_root = tmp_path / "isolated" / ".gemini"
    monkeypatch.setenv("GEMINI_CONFIG_DIR", str(gemini_root))
    expected_root = (
        gemini_root / "antigravity" / "plugin_data" / "tdq-workflow-agy"
    )
    assert setup_state.resolve_plugin_data_dir() == expected_root

    monkeypatch.delenv("GEMINI_CONFIG_DIR", raising=False)
    explicit_home = tmp_path / "explicit_home"
    expected_explicit = (
        explicit_home / ".gemini" / "antigravity" / "plugin_data" / "tdq-workflow-agy"
    )
    resolved_explicit = setup_state.resolve_plugin_data_dir(home=str(explicit_home))
    assert resolved_explicit == expected_explicit


def test_compute_host_session_fingerprint_real_and_fast() -> None:
    """Measure real host session fingerprint within 20 ms and verify schema."""
    first = setup_state.compute_host_session_fingerprint()
    second = setup_state.compute_host_session_fingerprint()

    required = {
        "root_pid",
        "root_name",
        "create_time",
        "fingerprint",
        "elapsed_ms",
        "platform",
    }
    assert required.issubset(first.keys())
    assert isinstance(first["root_pid"], int) and first["root_pid"] > 0
    assert isinstance(first["root_name"], str) and first["root_name"]
    assert isinstance(first["create_time"], str) and first["create_time"]
    assert isinstance(first["fingerprint"], str) and len(first["fingerprint"]) == 64
    assert isinstance(first["elapsed_ms"], float) and first["elapsed_ms"] <= 20.0
    assert first["platform"] == sys.platform
    assert first["fingerprint"] == second["fingerprint"]


def test_fingerprint_linux_proc_stat_with_spaces_and_parens(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Parse Linux /proc/<pid>/stat safely when comm contains spaces and parens."""
    tail = "S {ppid} 1 1 0 -1 0 0 0 0 0 0 0 0 0 20 0 1 0 {start} 0 0"
    proc_table = {
        300: "300 (python3) " + tail.format(ppid=200, start=5000),
        200: "200 (bash (login)) " + tail.format(ppid=150, start=4000),
        150: "150 (language_server) " + tail.format(ppid=100, start=3000),
        100: "100 (antigravity (UI)) " + tail.format(ppid=1, start=123456),
        1: "1 (systemd) " + tail.format(ppid=0, start=10),
    }
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(os, "getpid", lambda: 300)
    monkeypatch.setattr(
        setup_state, "_read_proc_stat_text", lambda pid: proc_table.get(pid)
    )

    fp = setup_state.compute_host_session_fingerprint()
    assert fp["root_pid"] == 100
    assert "antigravity" in fp["root_name"].lower()
    assert fp["create_time"] == "ticks:123456"
    assert fp["platform"] == "linux"


def test_fingerprint_macos_ps_and_ide_restart_diff(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Parse macOS ps output and verify restart changes fingerprint."""
    agy_bin = "/Applications/Antigravity.app/Contents/MacOS/Electron"
    ps_rows = {
        500: "  400 python3 Sun Nov 22 10:00:00 2026\n",
        400: "  300 zsh Sun Nov 22 09:59:00 2026\n",
        300: f"  200 {agy_bin} Sun Nov 22 09:30:00 2026\n",
        200: "    1 /sbin/launchd Sun Nov 22 08:00:00 2026\n",
    }

    def fake_run(cmd: list[str], **_kwargs: object) -> SimpleNamespace:
        pid = int(cmd[-1])
        out = ps_rows.get(pid, "")
        return SimpleNamespace(returncode=0 if out else 1, stdout=out, stderr="")

    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(os, "getpid", lambda: 500)
    monkeypatch.setattr(setup_state, "_run_quiet_command", fake_run)

    fp1 = setup_state.compute_host_session_fingerprint()
    assert fp1["root_pid"] == 300
    assert "antigravity" in fp1["root_name"].lower()
    assert fp1["create_time"] == "Sun Nov 22 09:30:00 2026"

    ps_rows[400] = "  301 zsh Sun Nov 22 10:05:00 2026\n"
    ps_rows[301] = f"  200 {agy_bin} Sun Nov 22 10:04:00 2026\n"
    fp2 = setup_state.compute_host_session_fingerprint()
    assert fp2["root_pid"] == 301
    assert fp2["fingerprint"] != fp1["fingerprint"]


def test_fingerprint_respects_hop_limit_and_cycle_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Stop cleanly at <= 12 hops even when parent tree has a cycle."""
    visited: list[int] = []

    def fake_linux_stat(pid: int) -> str:
        visited.append(pid)
        next_pid = 20 if pid == 10 else pid - 1
        return (
            f"{pid} (worker) S {next_pid} "
            f"1 1 0 -1 0 0 0 0 0 0 0 0 0 20 0 1 0 {pid * 10} 0 0"
        )

    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(os, "getpid", lambda: 30)
    monkeypatch.setattr(setup_state, "_read_proc_stat_text", fake_linux_stat)

    fp = setup_state.compute_host_session_fingerprint()
    assert fp["root_pid"] > 0
    assert len(visited) <= 13


def test_load_and_save_setup_state_corrupt_recovery(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Recover safely from missing, truncated, or non-object JSON."""
    monkeypatch.delenv("TDQ_LOG", raising=False)
    data_dir = tmp_path / "plugin_data"

    missing = setup_state.load_setup_state(data_dir=data_dir)
    assert missing == {"version": 2, "status": "idle", "pending_flag": False}

    data_dir.mkdir(parents=True)
    state_file = data_dir / "setup-state.json"
    state_file.write_text('{"version": 2, "status": "awaiting_res', encoding="utf-8")
    corrupted = setup_state.load_setup_state(data_dir=data_dir)
    assert corrupted == {"version": 2, "status": "idle", "pending_flag": False}

    state_file.write_text('["not", "an", "object"]', encoding="utf-8")
    wrong_type = setup_state.load_setup_state(data_dir=data_dir)
    assert wrong_type == {"version": 2, "status": "idle", "pending_flag": False}

    saved_path = setup_state.save_setup_state(
        {"version": 2, "status": "awaiting_restart", "host_fingerprint": "fp-1"},
        pending=True,
        data_dir=data_dir,
    )
    assert saved_path == state_file
    assert (data_dir / "setup-pending.flag").is_file()
    loaded = setup_state.load_setup_state(data_dir=data_dir)
    assert loaded["status"] == "awaiting_restart"
    assert loaded["pending_flag"] is True
    assert loaded["host_fingerprint"] == "fp-1"
    assert datetime.datetime.fromisoformat(loaded["updated_at"]).utcoffset() is not None

    setup_state.save_setup_state(loaded, pending=False, data_dir=data_dir)
    assert not (data_dir / "setup-pending.flag").exists()
    cleared = setup_state.load_setup_state(data_dir=data_dir)
    assert cleared["pending_flag"] is False
    assert capsys.readouterr().err


def test_evaluate_restart_resume_transitions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test none, TTL expiry, remind_restart, new-fingerprint, and confirm_manual."""
    data_dir = tmp_path / "plugin_data"

    idle_res = setup_state.evaluate_restart_resume(is_new_turn=True, data_dir=data_dir)
    assert idle_res["action"] == "none"
    assert set(idle_res.keys()) == {"action", "reason", "state"}

    monkeypatch.setattr(
        setup_state,
        "compute_host_session_fingerprint",
        lambda: {
            "root_pid": 100,
            "root_name": "Antigravity.exe",
            "create_time": "2026-11-22T10:00:00+00:00",
            "fingerprint": "fp-old",
            "elapsed_ms": 1.2,
            "platform": sys.platform,
        },
    )
    setup_state.save_setup_state(
        {"version": 2, "status": "awaiting_restart", "host_fingerprint": "fp-old"},
        pending=True,
        data_dir=data_dir,
    )
    same_fp = setup_state.evaluate_restart_resume(is_new_turn=True, data_dir=data_dir)
    assert same_fp["action"] == "remind_restart"

    monkeypatch.setattr(
        setup_state,
        "compute_host_session_fingerprint",
        lambda: {
            "root_pid": 200,
            "root_name": "Antigravity.exe",
            "create_time": "2026-11-22T11:00:00+00:00",
            "fingerprint": "fp-new",
            "elapsed_ms": 1.1,
            "platform": sys.platform,
        },
    )
    not_new = setup_state.evaluate_restart_resume(is_new_turn=False, data_dir=data_dir)
    assert not_new["action"] == "remind_restart"

    resumed = setup_state.evaluate_restart_resume(is_new_turn=True, data_dir=data_dir)
    assert resumed["action"] == "run_verify"
    assert resumed["state"]["status"] == "validating_after_restart"
    disk_state = setup_state.load_setup_state(data_dir=data_dir)
    assert disk_state["status"] == "validating_after_restart"

    setup_state.save_setup_state(
        {"version": 2, "status": "awaiting_restart", "host_fingerprint": "fp-new"},
        pending=True,
        data_dir=data_dir,
    )
    manual = setup_state.evaluate_restart_resume(
        is_new_turn=False, confirm_manual=True, data_dir=data_dir
    )
    assert manual["action"] == "run_verify"
    assert manual["state"]["status"] == "validating_after_restart"

    setup_state.save_setup_state(
        {"version": 2, "status": "awaiting_restart", "host_fingerprint": ""},
        pending=True,
        data_dir=data_dir,
    )
    missing_fp = setup_state.evaluate_restart_resume(
        is_new_turn=True, data_dir=data_dir
    )
    assert missing_fp["action"] == "remind_restart"
    assert missing_fp["reason"] == "missing_fingerprint"

    stale_dt = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(
        hours=25
    )
    state_file = data_dir / "setup-state.json"
    raw = json.loads(state_file.read_text(encoding="utf-8"))
    raw["updated_at"] = stale_dt.isoformat()
    state_file.write_text(json.dumps(raw), encoding="utf-8")

    expired = setup_state.evaluate_restart_resume(is_new_turn=True, data_dir=data_dir)
    assert expired["action"] == "none"
    assert expired["reason"] == "expired_ttl"
    assert expired["state"]["status"] == "expired"
    assert not (data_dir / "setup-pending.flag").exists()


def test_evaluate_restart_resume_orphan_flag_cleanup(tmp_path: Path) -> None:
    """Clean up orphan setup-pending.flag when state JSON is missing or corrupt."""
    data_dir = tmp_path / "plugin_data"
    data_dir.mkdir(parents=True)
    flag_path = data_dir / "setup-pending.flag"
    flag_path.write_text("", encoding="utf-8")
    (data_dir / "setup-state.json").write_text("{corrupt", encoding="utf-8")

    res = setup_state.evaluate_restart_resume(is_new_turn=True, data_dir=data_dir)
    assert res["action"] == "none"
    assert not flag_path.exists()


def test_secrets_env_roundtrip_validation_and_masking(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Validate secret storage, '=' handling, private perms, and log redaction."""
    monkeypatch.delenv("TDQ_LOG", raising=False)
    data_dir = tmp_path / "plugin_data"
    data_dir.mkdir(parents=True)
    secrets_file = data_dir / "secrets.env"
    secrets_file.write_text(
        '# comment line\n\nOTHER_KEY="val=with=equals"\n'
        "export QUOTED='single=val'\nBAD LINE\n",
        encoding="utf-8",
    )

    for bad_key in ("", "   ", "tvly-1\nINJECT=1", "tvly-2\r", "tvly-3\x00"):
        with pytest.raises(ValueError) as exc_info:
            setup_state.save_tavily_secret(bad_key, data_dir=data_dir)
        assert "tvly-" not in str(exc_info.value)

    secret_val = "tvly-secret-test-999=abc==xyz"
    out_path = setup_state.save_tavily_secret(secret_val, data_dir=data_dir)
    assert out_path == secrets_file

    loaded = setup_state.load_secrets_env(data_dir=data_dir)
    assert loaded["TAVILY_API_KEY"] == secret_val
    assert loaded["OTHER_KEY"] == "val=with=equals"
    assert loaded["QUOTED"] == "single=val"

    if os.name != "nt":
        assert stat.S_IMODE(secrets_file.stat().st_mode) == 0o600

    captured = capsys.readouterr()
    assert secret_val not in captured.out
    assert secret_val not in captured.err
    assert "tvly-secret-test-999" not in captured.err
    assert captured.err


def test_apply_private_permissions_windows_icacls_invocation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify Windows permission hardening invokes icacls with owner-only DACL."""
    calls: list[list[str]] = []

    def fake_run(cmd: list[str], **_kwargs: object) -> SimpleNamespace:
        calls.append(cmd)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(os, "name", "nt")
    monkeypatch.setenv("USERDOMAIN", "HOST")
    monkeypatch.setenv("USERNAME", "tester")
    monkeypatch.setattr(setup_state, "_run_quiet_command", fake_run)

    secret_path = setup_state.save_tavily_secret(
        "tvly-win-check-123", data_dir=tmp_path
    )
    assert secret_path.is_file()
    assert calls
    assert calls[0][0] == "icacls"
    assert "/inheritance:r" in calls[0]
    assert "HOST\\tester:F" in calls[0]


def test_logging_iso_timestamp_and_tdq_log_mute(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify TDQ_LOG=0 mutes both in-process calls and CLI subprocess stderr."""
    monkeypatch.setenv("TDQ_LOG", "0")
    data_dir = tmp_path / "inproc"
    setup_state.compute_host_session_fingerprint()
    setup_state.save_setup_state({"status": "idle"}, pending=False, data_dir=data_dir)
    setup_state.load_setup_state(data_dir=data_dir)
    setup_state.evaluate_restart_resume(is_new_turn=True, data_dir=data_dir)
    setup_state.save_tavily_secret("tvly-muted-key", data_dir=data_dir)
    setup_state.load_secrets_env(data_dir=data_dir)
    assert capsys.readouterr().err == ""

    state_dir = tmp_path / "cli_state"
    base_env = {
        **os.environ,
        "TDQ_KHONG_CHAM_MAY": "1",
        "TDQ_SETUP_STATE_DIR": str(state_dir),
    }

    env_on = {**base_env}
    env_on.pop("TDQ_LOG", None)
    proc_on = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "tdq_setup_state.py"), "status", "--json"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env_on,
        timeout=15,
    )
    assert proc_on.returncode == 0
    assert json.loads(proc_on.stdout)["state"]["status"] == "idle"
    assert proc_on.stderr.strip()
    for line in proc_on.stderr.strip().splitlines():
        assert line.startswith("[")
        stamp, _msg = line[1:].split("] ", 1)
        assert datetime.datetime.fromisoformat(stamp).utcoffset() is not None

    env_off = {**base_env, "TDQ_LOG": "0"}
    proc_off = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "tdq_setup_state.py"), "status", "--json"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env_off,
        timeout=15,
    )
    assert proc_off.returncode == 0
    assert proc_off.stderr == ""
    assert json.loads(proc_off.stdout)["state"]["status"] == "idle"


def test_windows_icacls_failure_fails_closed_before_writing_secret(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Failing icacls ACL hardening on Windows must raise PermissionError and delete temp secret."""
    data_dir = tmp_path / "acl_state"
    monkeypatch.setattr(setup_state.os, "name", "nt")
    monkeypatch.setenv("USERNAME", "tester")
    monkeypatch.setenv("USERDOMAIN", "LOCAL")

    fake_proc = subprocess.CompletedProcess(args=["icacls"], returncode=1, stdout="", stderr="denied")
    monkeypatch.setattr(setup_state, "_run_quiet_command", lambda *_a, **_kw: fake_proc)

    with pytest.raises(PermissionError, match="icacls"):
        setup_state.save_tavily_secret("tvly-fail-closed-999", data_dir=data_dir)
    assert not (data_dir / setup_state.SECRETS_FILENAME).exists()
    leftover = [p.name for p in data_dir.glob("*.tmp")] if data_dir.exists() else []
    assert leftover == []
