"""Tests for T3.1 RTK/rg trigger in install.py and tools/install_agy_plugin.py."""
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import pytest

ROOT = Path(__file__).resolve().parent.parent
for _p in (str(ROOT), str(ROOT / "scripts"), str(ROOT / "tools")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import install  # noqa: E402
import install_agy_plugin  # noqa: E402
import rtk_integration  # noqa: E402


def _make_args(**overrides):
    defaults = {"with_rtk": False, "skip_rtk": False, "dry_run": False}
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _make_fake_plugin_src(tmp_path: Path) -> tuple[Path, Path]:
    src = tmp_path / "src_plugin"
    dst = tmp_path / "dst_plugin"
    src.mkdir(parents=True, exist_ok=True)
    (src / "plugin.json").write_text('{"name": "tdq-workflow-agy"}\n', encoding="utf-8")
    (src / "mcp_config.json").write_text('{"mcpServers": {"lsp": {}}}\n', encoding="utf-8")
    return src, dst


def test_install_handle_rtk_trigger_tty_decline(monkeypatch):
    called = []
    monkeypatch.setattr(rtk_integration, "probe_rtk", lambda cwd=None: {"valid": False, "reason": "not_found"})
    monkeypatch.setattr(rtk_integration, "locate_rg_binary", lambda: None)
    monkeypatch.setattr(rtk_integration, "install_rtk_and_rg", lambda **kw: called.append(kw) or {"ok": True})

    rc = install._handle_rtk_trigger(_make_args(), stdin_tty=True, ask_fn=lambda _prompt: "n")
    assert rc == 0
    assert called == []


def test_install_handle_rtk_trigger_tty_accept(monkeypatch):
    called = []
    monkeypatch.setattr(rtk_integration, "probe_rtk", lambda cwd=None: {"valid": False, "reason": "not_found"})
    monkeypatch.setattr(rtk_integration, "locate_rg_binary", lambda: None)
    monkeypatch.setattr(
        rtk_integration,
        "install_rtk_and_rg",
        lambda **kw: called.append(kw) or {"ok": True, "rtk_version": "0.30.0", "rg_version": "14.1.0"},
    )

    rc = install._handle_rtk_trigger(_make_args(), stdin_tty=True, ask_fn=lambda _prompt: "y")
    assert rc == 0
    assert len(called) == 1
    assert called[0].get("approve") is True


def test_install_handle_rtk_trigger_non_tty_never_prompts(monkeypatch):
    called = []
    monkeypatch.setattr(rtk_integration, "probe_rtk", lambda cwd=None: {"valid": False, "reason": "not_found"})
    monkeypatch.setattr(rtk_integration, "locate_rg_binary", lambda: None)
    monkeypatch.setattr(rtk_integration, "install_rtk_and_rg", lambda **kw: called.append(kw) or {"ok": True})

    def fail_ask(_prompt):
        raise AssertionError("ask_fn must not be called when stdin_tty=False")

    rc = install._handle_rtk_trigger(_make_args(), stdin_tty=False, ask_fn=fail_ask)
    assert rc == 0
    assert called == []


def test_install_handle_rtk_trigger_skip_rtk(monkeypatch):
    called = []
    monkeypatch.setattr(rtk_integration, "probe_rtk", lambda cwd=None: {"valid": False, "reason": "not_found"})
    monkeypatch.setattr(rtk_integration, "locate_rg_binary", lambda: None)
    monkeypatch.setattr(rtk_integration, "install_rtk_and_rg", lambda **kw: called.append(kw) or {"ok": True})

    rc = install._handle_rtk_trigger(
        _make_args(skip_rtk=True, with_rtk=True),
        stdin_tty=True,
        ask_fn=lambda _prompt: pytest.fail("must not prompt with --skip-rtk"),
    )
    assert rc == 0
    assert called == []


def test_install_handle_rtk_trigger_dry_run_with_rtk(monkeypatch, capsys):
    called = []
    monkeypatch.setattr(rtk_integration, "probe_rtk", lambda cwd=None: {"valid": False, "reason": "not_found"})
    monkeypatch.setattr(rtk_integration, "locate_rg_binary", lambda: None)
    monkeypatch.setattr(rtk_integration, "install_rtk_and_rg", lambda **kw: called.append(kw) or {"ok": True})

    rc = install._handle_rtk_trigger(_make_args(dry_run=True, with_rtk=True), stdin_tty=False)
    out = capsys.readouterr().out
    assert rc == 0
    assert called == []
    assert "[DRY-RUN]" in out


def test_install_handle_rtk_trigger_with_rtk_installs(monkeypatch):
    called = []
    monkeypatch.setattr(rtk_integration, "probe_rtk", lambda cwd=None: {"valid": False, "reason": "not_found"})
    monkeypatch.setattr(rtk_integration, "locate_rg_binary", lambda: None)
    monkeypatch.setattr(
        rtk_integration,
        "install_rtk_and_rg",
        lambda **kw: called.append(kw) or {"ok": True, "rtk_version": "0.30.0", "rg_version": "14.1.0"},
    )

    rc = install._handle_rtk_trigger(_make_args(with_rtk=True), stdin_tty=False)
    assert rc == 0
    assert len(called) == 1
    assert called[0].get("approve") is True


def test_install_handle_rtk_trigger_existing_tools_runs_ensure_config(monkeypatch):
    cfg_calls = []
    install_calls = []
    monkeypatch.setattr(
        rtk_integration,
        "probe_rtk",
        lambda cwd=None: {"valid": True, "version": "0.30.0", "path": "/usr/local/bin/rtk"},
    )
    monkeypatch.setattr(rtk_integration, "locate_rg_binary", lambda: "/usr/local/bin/rg")
    monkeypatch.setattr(rtk_integration, "ensure_rtk_config", lambda: cfg_calls.append(True) or (True, "ok"))
    monkeypatch.setattr(rtk_integration, "install_rtk_and_rg", lambda **kw: install_calls.append(kw) or {"ok": True})

    rc = install._handle_rtk_trigger(_make_args(), stdin_tty=False)
    assert rc == 0
    assert cfg_calls == [True]
    assert install_calls == []


def test_agy_installer_parses_with_rtk_and_skip_rtk_flags():
    ns_with = install_agy_plugin.parse_args(["--with-rtk"])
    assert ns_with.with_rtk is True
    assert ns_with.skip_rtk is False

    ns_skip = install_agy_plugin.parse_args(["--skip-rtk"])
    assert ns_skip.skip_rtk is True
    assert ns_skip.with_rtk is False


def test_agy_installer_non_tty_without_with_rtk_never_blocks_or_installs(tmp_path, monkeypatch, capsys):
    src, dst = _make_fake_plugin_src(tmp_path)
    monkeypatch.setattr(
        rtk_integration,
        "probe_rtk",
        lambda cwd=None: {"valid": False, "version": "", "path": "", "reason": "not_found"},
    )
    monkeypatch.setattr(rtk_integration, "locate_rg_binary", lambda: None)
    monkeypatch.setattr(
        rtk_integration,
        "install_rtk_and_rg",
        lambda **_kw: pytest.fail("install_rtk_and_rg must not be called without --with-rtk"),
    )

    with mock.patch("builtins.input", side_effect=AssertionError("input() must not be called")):
        rc = install_agy_plugin.main(["--src", str(src), "--target", str(dst)])

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert "rtk" in payload
    rtk = payload["rtk"]
    assert isinstance(rtk, dict)
    for key in ("present", "valid", "rg_present", "version", "installed", "skipped"):
        assert key in rtk
    assert rtk["valid"] is False
    assert rtk["rg_present"] is False
    assert rtk["installed"] is False
    assert rtk["skipped"] is False


def test_agy_installer_with_rtk_calls_install_and_skip_rtk_skips(tmp_path, monkeypatch, capsys):
    src, dst = _make_fake_plugin_src(tmp_path)
    calls = []
    monkeypatch.setattr(
        rtk_integration,
        "probe_rtk",
        lambda cwd=None: {"valid": False, "version": "", "path": "", "reason": "not_found"},
    )
    monkeypatch.setattr(rtk_integration, "locate_rg_binary", lambda: None)
    monkeypatch.setattr(
        rtk_integration,
        "install_rtk_and_rg",
        lambda **kw: calls.append(kw) or {"ok": True, "rtk_version": "0.30.1", "rg_version": "14.1.1"},
    )

    rc = install_agy_plugin.main(["--src", str(src), "--target", str(dst), "--with-rtk"])
    assert rc == 0
    assert calls == [{"approve": True}]
    payload = json.loads(capsys.readouterr().out)
    assert payload["rtk"]["installed"] is True
    assert payload["rtk"]["valid"] is True
    assert payload["rtk"]["rg_present"] is True
    assert payload["rtk"]["version"] == "0.30.1"
    assert payload["rtk"]["skipped"] is False

    calls.clear()
    rc_skip = install_agy_plugin.main(["--src", str(src), "--target", str(dst), "--with-rtk", "--skip-rtk"])
    assert rc_skip == 0
    assert calls == []
    skip_payload = json.loads(capsys.readouterr().out)
    assert skip_payload["rtk"]["skipped"] is True
    assert skip_payload["rtk"]["installed"] is False


def test_agy_installer_dry_run_with_rtk_never_installs_and_existing_ensures_config(tmp_path, monkeypatch, capsys):
    src, dst = _make_fake_plugin_src(tmp_path)
    monkeypatch.setattr(
        rtk_integration,
        "probe_rtk",
        lambda cwd=None: {"valid": False, "version": "", "path": "", "reason": "not_found"},
    )
    monkeypatch.setattr(rtk_integration, "locate_rg_binary", lambda: None)
    monkeypatch.setattr(
        rtk_integration,
        "install_rtk_and_rg",
        lambda **_kw: pytest.fail("must not install in --dry-run"),
    )

    rc_dry = install_agy_plugin.main(["--src", str(src), "--target", str(dst), "--dry-run", "--with-rtk"])
    assert rc_dry == 0
    dry_payload = json.loads(capsys.readouterr().out)
    assert dry_payload["dry_run"] is True
    assert dry_payload["rtk"]["would_install"] is True
    assert dry_payload["rtk"]["installed"] is False

    cfg_calls = []
    monkeypatch.setattr(
        rtk_integration,
        "probe_rtk",
        lambda cwd=None: {"valid": True, "version": "0.30.1", "path": "/usr/local/bin/rtk", "reason": "ok"},
    )
    monkeypatch.setattr(rtk_integration, "locate_rg_binary", lambda: "/usr/local/bin/rg")
    monkeypatch.setattr(rtk_integration, "ensure_rtk_config", lambda: cfg_calls.append(True) or (True, "ok"))

    rc_ok = install_agy_plugin.main(["--src", str(src), "--target", str(dst)])
    assert rc_ok == 0
    assert cfg_calls == [True]
    ok_payload = json.loads(capsys.readouterr().out)
    assert ok_payload["rtk"]["valid"] is True
    assert ok_payload["rtk"]["rg_present"] is True
    assert ok_payload["rtk"]["installed"] is False
