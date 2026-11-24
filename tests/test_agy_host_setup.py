#!/usr/bin/env python3
"""Unit tests for Antigravity host setup, --setupfully manifest, GEMINI pin, and Archify installer."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import types
from pathlib import Path
from unittest import mock

import pytest

WORKTREE_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = WORKTREE_ROOT / "scripts"
TOOLS_DIR = WORKTREE_ROOT / "tools"
for _p in (str(SCRIPTS_DIR), str(TOOLS_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import archify_delivery  # noqa: E402
from patches import cli_fixes_a  # noqa: E402
import setup_status  # noqa: E402
import tdq_devtool_mcp  # noqa: E402
import tdq_lsp  # noqa: E402
import tdq_setup  # noqa: E402
import tdq_setup_state  # noqa: E402


def _make_agy_home(tmp_path: Path, with_chrome_plugin: bool = False) -> Path:
    """Create an isolated synthetic Antigravity HOME without any ~/.claude* files."""
    home = tmp_path / "agy_home"
    (home / ".gemini" / "config" / "plugins" / "tdq-workflow-agy").mkdir(
        parents=True, exist_ok=True
    )
    if with_chrome_plugin:
        cdp = home / ".gemini" / "config" / "plugins" / "chrome-devtools-plugin"
        cdp.mkdir(parents=True, exist_ok=True)
        (cdp / "plugin.json").write_text(
            json.dumps({"name": "chrome-devtools-plugin", "version": "1.0.0"}),
            encoding="utf-8",
        )
    return home


def _isolate_agy_env(
    monkeypatch: pytest.MonkeyPatch,
    home: Path,
    state_dir: Path,
    project: Path,
    *,
    dry: bool = True,
) -> None:
    """Point HOME/USERPROFILE/GEMINI/TDQ vars strictly inside tmp_path."""
    for key in ("PLUGIN_DATA", "ARCHIFY_ROOT", "TAVILY_API_KEY", "CHROME_PATH"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    monkeypatch.setenv("GEMINI_CONFIG_DIR", str(home / ".gemini" / "config"))
    monkeypatch.setenv("ANTIGRAVITY_GEMINI_DIR", str(home / ".gemini"))
    monkeypatch.setenv("TDQ_SETUP_STATE_DIR", str(state_dir))
    monkeypatch.setenv("TDQ_PROJECT_DIR", str(project))
    monkeypatch.setenv("TDQ_HOST", "antigravity")
    monkeypatch.setenv("TDQ_KHONG_CHAM_MAY", "1" if dry else "0")


def test_scan_json_on_synthetic_agy_home_zero_claude_debt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """--scan-json reports host=antigravity, claude_debt_count=0, and creates no ~/.claude*."""
    home = _make_agy_home(tmp_path, with_chrome_plugin=False)
    state_dir = tmp_path / "state"
    project = tmp_path / "proj"
    project.mkdir()
    _isolate_agy_env(monkeypatch, home, state_dir, project, dry=True)

    mcp_cfg = home / ".gemini" / "config" / "mcp_config.json"
    mcp_cfg.write_text(
        json.dumps({
            "mcpServers": {
                "lsp": {
                    "command": "node",
                    "args": ["${PLUGIN_ROOT}/scripts/tdq_mcp_launcher.mjs", "lsp"],
                }
            }
        }),
        encoding="utf-8",
    )

    with mock.patch.object(tdq_setup, "_probe_agy_plugins", return_value=[]), mock.patch.object(
        tdq_devtool_mcp, "get_chrome_executable", return_value=""
    ):
        rc = tdq_setup.main(["--khong-log", "--scan-json"])

    assert rc == 0
    manifest = json.loads(capsys.readouterr().out)
    assert manifest["host"] == "antigravity"
    assert manifest["claude_debt_count"] == 0
    for key in ("core", "addons", "optional_companions", "actions"):
        assert key in manifest
    assert "chrome_devtools_plugin" in manifest["optional_companions"]
    assert manifest["optional_companions"]["chrome_devtools_plugin"]["installed"] is False
    assert not (home / ".claude.json").exists()
    assert not (home / ".claude").exists()


def test_tdq_lsp_rungs_2_3_4_5_with_node_launcher_and_caveman(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """tdq_lsp Rungs 2/3/4/5 support Antigravity mcp_config.json, .mjs caveman, and hooks."""
    home = _make_agy_home(tmp_path)
    state_dir = tmp_path / "state"
    project = tmp_path / "py_proj"
    project.mkdir()
    for idx in range(4):
        (project / f"mod_{idx}.py").write_text(f"def fn_{idx}():\n    return {idx}\n", encoding="utf-8")
    (project / "pyrightconfig.json").write_text('{"include": ["."]}', encoding="utf-8")

    _isolate_agy_env(monkeypatch, home, state_dir, project, dry=True)

    # Verify _all_mcp_configs includes ~/.gemini/config/mcp_config.json
    configs = tdq_lsp._all_mcp_configs()
    expected_cfg = os.path.expanduser("~/.gemini/config/mcp_config.json")
    assert any(os.path.normpath(c) == os.path.normpath(expected_cfg) for c in configs)

    # Empty Antigravity config -> Rung 2 & Rung 4 fail mentioning mcp_config.json, never ~/.claude*
    r2_missing = tdq_lsp.bac2_mcp()
    r4_missing = tdq_lsp.bac4_quyen_tool()
    assert r2_missing.dat is False
    assert "mcp_config.json" in r2_missing.chi_tiet
    assert ".claude" not in r2_missing.chi_tiet
    assert r4_missing.dat is False
    assert "mcp_config.json" in r4_missing.chi_tiet
    assert ".claude" not in r4_missing.chi_tiet

    # Populate ~/.gemini/config/mcp_config.json with BOTH lsp and caveman-wrapped lsp modes
    agy_mcp = home / ".gemini" / "config" / "mcp_config.json"
    for args_variant in (
        ["${PLUGIN_ROOT}/scripts/tdq_mcp_launcher.mjs", "lsp"],
        [
            "${PLUGIN_ROOT}/scripts/tdq_mcp_launcher.mjs",
            "caveman",
            "--",
            "node",
            "C:\\Users\\demo\\scripts\\tdq_mcp_launcher.mjs",
            "lsp",
        ],
    ):
        agy_mcp.write_text(
            json.dumps({"mcpServers": {"lsp": {"command": "node", "args": args_variant}}}),
            encoding="utf-8",
        )
        assert tdq_lsp.bac2_mcp().dat is True
        assert tdq_lsp.bac4_quyen_tool().dat is True

        doctor_cmds: list[list[str]] = []

        def fake_run(cmd, cwd=None, timeout=90):
            doctor_cmds.append(list(cmd))
            return 0, "● python (pyright-langserver)\n  Status:  ok\n\nSummary: 1 ok, 0 failed\n"

        with mock.patch.object(tdq_lsp.shutil, "which", return_value="/bin/tool"), mock.patch.object(
            tdq_lsp, "_run", side_effect=fake_run
        ):
            r3 = tdq_lsp.bac3_language_server(str(project))
        assert r3.dat is True, f"Rung 3 failed for {args_variant}: {r3.chi_tiet}"
        assert doctor_cmds == [["/bin/tool", "doctor"]], (
            f"_chay_doctor leaked launcher tokens: {doctor_cmds}"
        )

    # Rung 5 scans ~/.gemini/config/plugins/*/hooks.json and ~/.gemini/config/hooks.json
    ext_plugin = home / ".gemini" / "config" / "plugins" / "other-search-plugin"
    ext_plugin.mkdir(parents=True)
    (ext_plugin / "hooks.json").write_text(
        json.dumps({"PreToolUse": [{"matcher": "Grep|Glob"}]}),
        encoding="utf-8",
    )
    conflicts = tdq_lsp.hook_xung_dot()
    assert len(conflicts) == 1
    assert conflicts[0][0] == "other-search-plugin"
    assert ".claude" not in conflicts[0][1]


    # Also verify ~/.gemini/config/hooks.json conflict detection & TDQ own-hook exclusion
    user_hooks = home / ".gemini" / "config" / "hooks.json"
    user_hooks.write_text(
        json.dumps({
            "tdq-pre-tool": {"enabled": True, "PreToolUse": [{"matcher": "Grep", "hooks": [{"command": "node scripts/tdq_hook_launcher.mjs"}]}]},
            "custom-user-gate": {"enabled": True, "PreToolUse": [{"matcher": "Bash"}]},
        }),
        encoding="utf-8",
    )
    conflicts_with_user = tdq_lsp.hook_xung_dot()
    assert any(c[0] == "gemini-config" and c[2] == "Bash" for c in conflicts_with_user)
    assert not any(c[2] == "Grep" for c in conflicts_with_user)


def test_setup_status_thu_thuc_nhan_agy_filters_mjs_args(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """setup_status.thu_thuc_nhan uses Antigravity MCP + agy plugin list and strips .mjs args."""
    home = _make_agy_home(tmp_path)
    state_dir = tmp_path / "state"
    project = tmp_path / "proj"
    project.mkdir()
    _isolate_agy_env(monkeypatch, home, state_dir, project, dry=True)

    agy_mcp = home / ".gemini" / "config" / "mcp_config.json"
    agy_mcp.write_text(
        json.dumps({
            "mcpServers": {
                "lsp": {
                    "command": "node",
                    "args": [
                        "${PLUGIN_ROOT}/scripts/tdq_mcp_launcher.mjs",
                        "caveman",
                        "--",
                        "node",
                        "C:\\fake\\tdq_mcp_launcher.mjs",
                        "lsp",
                    ],
                },
                "tavily-primary": {
                    "command": "node",
                    "args": ["${PLUGIN_ROOT}/scripts/tdq_mcp_launcher.mjs", "npx", "-y", "tavily-mcp@latest"],
                },
            }
        }),
        encoding="utf-8",
    )

    seen_calls: list[tuple[str, list[str]]] = []

    def fake_run_tool(binary, args, goi_y="", timeout=90, env=None):
        seen_calls.append((binary, list(args)))
        if binary == "agy":
            payload = [{"name": "tdq-workflow-agy", "enabled": True, "mcpServers": ["lsp", "tavily-primary"]}]
            return {
                "co": True, "chay_duoc": True, "duong_dan": "/bin/agy", "ma": 0,
                "ra": json.dumps(payload), "loi": "", "chi_tiet": "", "goi_y": goi_y,
            }
        if binary == "agent-lsp":
            return {
                "co": True, "chay_duoc": True, "duong_dan": "/bin/agent-lsp", "ma": 0,
                "ra": "● python (pyright)\n  Status:  ok\n\nSummary: 1 ok, 0 failed\n",
                "loi": "", "chi_tiet": "", "goi_y": goi_y,
            }
        raise AssertionError(f"Unexpected tool call on Antigravity: {binary} {args}")

    with mock.patch.object(setup_status, "_run_tool", side_effect=fake_run_tool):
        res = setup_status.thu_thuc_nhan()

    assert not any(b == "claude" for b, _ in seen_calls)
    doctor_args = [a for b, a in seen_calls if b == "agent-lsp"]
    assert doctor_args == [["doctor"]]
    assert [s["ten"] for s in res["mcp"]["server"]] == ["lsp", "tavily-primary"]
    assert all(s["noi_duoc"] for s in res["mcp"]["server"])


def test_tdq_devtool_mcp_antigravity_probe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """check_devtool_setup detects Antigravity mcp_config.json and chrome-devtools-plugin."""
    home = _make_agy_home(tmp_path, with_chrome_plugin=True)
    state_dir = tmp_path / "state"
    project = tmp_path / "proj"
    project.mkdir()
    _isolate_agy_env(monkeypatch, home, state_dir, project, dry=True)

    agy_mcp = home / ".gemini" / "config" / "mcp_config.json"
    agy_mcp.write_text(
        json.dumps({"mcpServers": {"chrome-devtools": {"command": "node", "args": []}}}),
        encoding="utf-8",
    )
    fake_chrome = tmp_path / "chrome.exe"
    fake_chrome.write_text("", encoding="utf-8")

    with mock.patch.object(tdq_devtool_mcp, "get_chrome_executable", return_value=str(fake_chrome)):
        st = tdq_devtool_mcp.check_devtool_setup(
            agy_plugins_probe=lambda: [
                {"name": "chrome-devtools-plugin", "enabled": True, "version": "1.10.1"}
            ]
        )

    assert st["mcp_registered"] is True
    assert st["permission_allowed"] is True
    assert st["chrome_available"] is True
    assert st["all_ready"] is True
    assert st["chrome_devtools_plugin_enabled"] is True


def test_gemini_md_pin_antigravity_format_and_claude_preserved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """GEMINI.md pin is <24KB, uses AGY tool names, omits Claude symbols, and preserves KHOI_HUONG_DAN."""
    home = _make_agy_home(tmp_path)
    state_dir = tmp_path / "state"
    project = tmp_path / "proj"
    project.mkdir()
    _isolate_agy_env(monkeypatch, home, state_dir, project, dry=True)

    gemini_md = home / ".gemini" / "GEMINI.md"
    gemini_md.write_text("# My User Notes\n\nKeep me intact.\n", encoding="utf-8")

    changed = tdq_setup.pin_agy_gemini_md(str(gemini_md), plugin_root=str(WORKTREE_ROOT))
    assert changed is True
    # Idempotent second pin
    assert tdq_setup.pin_agy_gemini_md(str(gemini_md), plugin_root=str(WORKTREE_ROOT)) is False

    content = gemini_md.read_text(encoding="utf-8")
    assert "Keep me intact." in content
    assert len(content.encode("utf-8")) < 24000
    assert content.count(tdq_setup.MOC_MO) == 1
    assert content.count(tdq_setup.MOC_DONG) == 1
    for required in ("start_lsp", "tdq-intake", "/plan", "ask_question"):
        assert required in content, f"Missing AGY token {required}"
    for forbidden in ("mcp__lsp__", "CLAUDE_PLUGIN_ROOT", "EnterPlanMode", "AskUserQuestion"):
        assert forbidden not in content, f"Forbidden Claude token {forbidden} leaked into GEMINI.md"

    # Legacy Claude KHOI_HUONG_DAN remains intact
    claude_pin = tdq_setup.khoi_huong_dan(tdq_setup.GOC_MAU)
    assert "mcp__lsp__start_lsp" in claude_pin
    assert "${CLAUDE_PLUGIN_ROOT}" in claude_pin


def test_archify_candidate_root_and_ensure_archify_installed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """archify_delivery finds ~/.local/share/archify and ensure_archify_installed respects dry-mode."""
    fake_home = tmp_path / "home"
    archify_dir = fake_home / ".local" / "share" / "archify"

    monkeypatch.delenv("ARCHIFY_ROOT", raising=False)
    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.setenv("USERPROFILE", str(fake_home))

    with mock.patch("pathlib.Path.home", return_value=fake_home):
        cands = archify_delivery._gather_candidate_roots()
        assert archify_dir in cands

        # Not installed + TDQ_KHONG_CHAM_MAY=1 -> skips cleanly without running git
        monkeypatch.setenv("TDQ_KHONG_CHAM_MAY", "1")
        with mock.patch.object(tdq_setup.tdq_ten_lenh, "chay_subprocess") as sub:
            ok, msg = tdq_setup.ensure_archify_installed(home=str(fake_home))
        sub.assert_not_called()
        assert ok is False
        assert "dry-mode" in msg.lower() or "skipped" in msg.lower()

        # Install mocked git clone when TDQ_KHONG_CHAM_MAY=0
        monkeypatch.setenv("TDQ_KHONG_CHAM_MAY", "0")
        git_cmds: list[list[str]] = []

        def fake_git(cmd, **_kw):
            git_cmds.append(list(cmd))
            (archify_dir / "bin").mkdir(parents=True, exist_ok=True)
            (archify_dir / "bin" / "archify.mjs").write_text("// ok\n", encoding="utf-8")
            return mock.MagicMock(returncode=0, stdout="cloned\n", stderr="")

        with mock.patch.object(tdq_setup.shutil, "which", return_value="/bin/git"), mock.patch.object(
            tdq_setup.tdq_ten_lenh, "chay_subprocess", side_effect=fake_git
        ), mock.patch.object(
            archify_delivery, "_check_node_environment", return_value=(True, "v22.0.0", [])
        ):
            ok_install, path_or_msg = tdq_setup.ensure_archify_installed(home=str(fake_home))

        assert ok_install is True
        assert Path(path_or_msg) == archify_dir
        assert git_cmds and "https://github.com/tt-a1i/archify.git" in git_cmds[0]
        assert "--branch" in git_cmds[0] and "main" in git_cmds[0]

        # Now present on disk + TDQ_KHONG_CHAM_MAY=1 -> returns (True, path)
        monkeypatch.setenv("TDQ_KHONG_CHAM_MAY", "1")
        assert Path(archify_delivery.find_archify_root()) == archify_dir
        ok_existing, path_existing = tdq_setup.ensure_archify_installed(home=str(fake_home))
        assert ok_existing is True
        assert Path(path_existing) == archify_dir


def test_apply_setup_manifest_set_tavily_key_and_post_restart_verify(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Test --setupfully state persistence, secret redaction, and lazy --post-restart-verify."""
    home = _make_agy_home(tmp_path)
    state_dir = tmp_path / "state"
    project = tmp_path / "proj"
    project.mkdir()
    _isolate_agy_env(monkeypatch, home, state_dir, project, dry=True)

    # 1. --set-tavily-key must not leak the secret to stdout or stderr
    secret_val = "tvly-secret-test-never-echo-987654"
    monkeypatch.setenv("TDQ_LOG", "1")
    rc_key = tdq_setup.main(["--state-dir", str(state_dir), "--set-tavily-key", secret_val])
    captured = capsys.readouterr()
    assert rc_key == 0
    assert secret_val not in captured.out
    assert secret_val not in captured.err
    assert tdq_setup_state.load_secrets_env(data_dir=state_dir)["TAVILY_API_KEY"] == secret_val

    # 2. apply_setup_manifest writes awaiting_restart + pending=True into isolated state_dir
    with mock.patch.object(tdq_setup, "_probe_agy_plugins", return_value=[]):
        receipt = tdq_setup.apply_setup_manifest(str(project), setupfully=True)
    assert receipt["host"] == "antigravity"
    assert receipt["claude_debt_count"] == 0
    assert receipt["status"] == "awaiting_restart"
    assert receipt["pending"] is True
    assert (state_dir / tdq_setup_state.PENDING_FLAG_FILENAME).is_file()
    saved = tdq_setup_state.load_setup_state(data_dir=state_dir)
    assert saved["status"] == "awaiting_restart"
    assert len(saved["host_fingerprint"]) == 64

    # 3. Verify tdq_setup does NOT import tdq_simulate_verify at top level (created in Wave 4 T2.3)
    kw_imp: dict = {"capture_output": True, "text": True, "encoding": "utf-8", "timeout": 15}
    if os.name == "nt":
        kw_imp["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
    probe_imp = subprocess.run(
        [
            sys.executable,
            "-X",
            "utf8",
            "-c",
            "import sys; sys.path.insert(0, sys.argv[1]); import tdq_setup; "
            "assert 'tdq_simulate_verify' not in sys.modules",
            str(SCRIPTS_DIR),
        ],
        check=False,
        **kw_imp,
    )
    assert probe_imp.returncode == 0, f"tdq_setup eagerly imported tdq_simulate_verify: {probe_imp.stderr}"
    top_src = (SCRIPTS_DIR / "tdq_setup.py").read_text(encoding="utf-8")
    assert "\nimport tdq_simulate_verify" not in top_src

    # 4. --post-restart-verify lazy-imports tdq_simulate_verify, clears pending flag on PASS
    fake_sim = types.ModuleType("tdq_simulate_verify")
    fake_sim.run_simulate_verify = mock.Mock(
        return_value={"core_gate": "PASS", "optional_gate": "SKIPPED", "temp_cleaned": True}
    )
    monkeypatch.setitem(sys.modules, "tdq_simulate_verify", fake_sim)

    rc_ver = tdq_setup.main([
        "--khong-log",
        "--state-dir",
        str(state_dir),
        "--confirm-restarted",
        "--post-restart-verify",
    ])
    assert rc_ver == 0
    fake_sim.run_simulate_verify.assert_called_once()
    assert not (state_dir / tdq_setup_state.PENDING_FLAG_FILENAME).exists()
    verified_state = tdq_setup_state.load_setup_state(data_dir=state_dir)
    assert verified_state["status"] == "verified"
    assert verified_state["pending_flag"] is False


def test_cli_fixes_a_apply_all_idempotent_on_updated_scripts(tmp_path: Path) -> None:
    """cli_fixes_a.apply_all runs cleanly twice on a temp copy of scripts/ without errors."""
    copied_scripts = tmp_path / "scripts"
    shutil.copytree(SCRIPTS_DIR, copied_scripts)

    cli_fixes_a.apply_all(copied_scripts)
    cli_fixes_a.apply_all(copied_scripts)

    lsp_mod_text = (copied_scripts / "lsp_module.py").read_text(encoding="utf-8")
    assert "~/.gemini/config/mcp_config.json" in lsp_mod_text


def test_default_agy_main_caveman_node_wrap_fail_closed_verify_and_logging(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Verify default AGY main flow, Node Caveman wrap, fail-closed verify, and TDQ_LOG mute."""
    home = _make_agy_home(tmp_path)
    state_dir = tmp_path / "state"
    project = tmp_path / "proj"
    project.mkdir()
    _isolate_agy_env(monkeypatch, home, state_dir, project, dry=True)

    installed_plugin = home / ".gemini" / "config" / "plugins" / "tdq-workflow-agy"
    (installed_plugin / "scripts").mkdir(parents=True, exist_ok=True)
    (installed_plugin / "scripts" / "tdq_mcp_shrink.py").write_text("# proxy\n", encoding="utf-8")
    installed_mcp = installed_plugin / "mcp_config.json"
    installed_mcp.write_text(
        json.dumps({
            "mcpServers": {
                "lsp": {
                    "command": "node",
                    "args": ["${PLUGIN_ROOT}/scripts/tdq_mcp_launcher.mjs", "lsp"],
                }
            }
        }),
        encoding="utf-8",
    )

    # Default Antigravity flow without --setupfully (TDQ_LOG=1 emits ISO timestamp)
    monkeypatch.setenv("TDQ_LOG", "1")
    with mock.patch.object(tdq_setup, "_probe_agy_plugins", return_value=[]):
        rc_default = tdq_setup.main(["--state-dir", str(state_dir)])
    out_def = capsys.readouterr()
    assert rc_default == 0
    assert "host=antigravity" in out_def.out
    assert "claude_debt=0" in out_def.out
    assert not (home / ".claude").exists()
    assert not (home / ".claude.json").exists()
    import re
    assert re.search(r"\[\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\]", out_def.err)

    # TDQ_LOG=0 mutes stderr cleanly while --setupfully wraps Caveman preserving command=node
    monkeypatch.setenv("TDQ_LOG", "0")
    with mock.patch.object(tdq_setup, "_probe_agy_plugins", return_value=[]):
        rc_full = tdq_setup.main(["--state-dir", str(state_dir), "--setupfully", "--json"])
    out_full = capsys.readouterr()
    assert rc_full == 0
    assert out_full.err == ""
    receipt = json.loads(out_full.out)
    assert receipt["addons"]["caveman"]["enabled"] is True
    wrapped_mcp = json.loads(installed_mcp.read_text(encoding="utf-8"))
    assert wrapped_mcp["mcpServers"]["lsp"]["command"] == "node"
    assert wrapped_mcp["mcpServers"]["lsp"]["args"][1] == "caveman"
    assert sys.executable not in installed_mcp.read_text(encoding="utf-8")

    # --post-restart-verify fail-closed preserves pending flag when core_gate != PASS
    fake_sim = types.ModuleType("tdq_simulate_verify")
    fake_sim.run_simulate_verify = mock.Mock(
        return_value={"core_gate": "FAIL", "optional_gate": "SKIPPED", "temp_cleaned": True}
    )
    monkeypatch.setitem(sys.modules, "tdq_simulate_verify", fake_sim)
    rc_fail = tdq_setup.main(["--khong-log", "--state-dir", str(state_dir), "--post-restart-verify"])
    assert rc_fail == 1
    assert (state_dir / tdq_setup_state.PENDING_FLAG_FILENAME).is_file()
    assert tdq_setup_state.load_setup_state(data_dir=state_dir)["status"] == "verify_failed"


def test_archify_origin_validation_and_stdin_tavily_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Verify --set-tavily-key - reads stdin and Archify refuses untrusted git origins."""
    home = _make_agy_home(tmp_path)
    state_dir = tmp_path / "sec_state"
    project = tmp_path / "sec_proj"
    project.mkdir()
    _isolate_agy_env(monkeypatch, home, state_dir, project, dry=False)

    monkeypatch.setattr(sys, "stdin", __import__("io").StringIO("tvly-stdin-secret-888\n"))
    rc_stdin = tdq_setup.main(["--khong-log", "--state-dir", str(state_dir), "--set-tavily-key", "-"])
    assert rc_stdin == 0
    out_stdin = capsys.readouterr().out
    assert "tvly-stdin-secret-888" not in out_stdin
    assert tdq_setup_state.load_secrets_env(data_dir=state_dir)["TAVILY_API_KEY"] == "tvly-stdin-secret-888"

    # Combined --setupfully --set-tavily-key - must also read stdin instead of saving "-"
    monkeypatch.setattr(sys, "stdin", __import__("io").StringIO("tvly-setupfully-stdin-999\n"))
    with mock.patch.object(tdq_setup, "_apply_core_agy_tools", return_value={}), mock.patch.object(
        tdq_setup, "_apply_addons_agy", return_value={}
    ), mock.patch.object(
        tdq_setup, "_apply_optional_companions_agy", return_value={}
    ):
        rc_combo = tdq_setup.main(
            ["--khong-log", "--state-dir", str(state_dir), "--setupfully", "--set-tavily-key", "-", "--json"]
        )
    assert rc_combo == 0
    out_combo = capsys.readouterr().out
    assert "tvly-setupfully-stdin-999" not in out_combo
    assert tdq_setup_state.load_secrets_env(data_dir=state_dir)["TAVILY_API_KEY"] == "tvly-setupfully-stdin-999"

    existing = home / ".local" / "share" / "archify"
    (existing / ".git").mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(tdq_setup.shutil, "which", lambda cmd: "git" if cmd == "git" else None)
    monkeypatch.setattr(
        tdq_setup,
        "_run_git_cmd",
        lambda args: (0, "https://evil.example/archify.git") if "get-url" in args else (0, ""),
    )
    ok_origin, msg_origin = tdq_setup._clone_or_update_archify(existing, existing)
    assert ok_origin is False
    assert "origin" in msg_origin.lower()


def test_scan_manifest_and_apply_addons_tree_sitter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """AGY manifest includes tree_sitter addon, action, and offline guard."""
    home = _make_agy_home(tmp_path)
    state_dir = tmp_path / "ts_state"
    project = tmp_path / "ts_proj"
    project.mkdir()
    _isolate_agy_env(monkeypatch, home, state_dir, project, dry=True)

    # 1. Missing tree-sitter-rust -> installed=False + install_tree_sitter action
    with (
        mock.patch.object(tdq_setup, "_probe_agy_plugins", return_value=[]),
        mock.patch.object(tdq_devtool_mcp, "get_chrome_executable", return_value=""),
        mock.patch.dict(sys.modules, {"tree_sitter_rust": None}),
    ):
        manifest_missing = tdq_setup.scan_setup_manifest(str(project))

    for key in ("rtk", "caveman", "archify", "tree_sitter"):
        assert key in manifest_missing["addons"]
    ts_missing = manifest_missing["addons"]["tree_sitter"]
    for key in ("installed", "missing", "languages", "version", "packages"):
        assert key in ts_missing
    assert ts_missing["installed"] is False
    assert "tree-sitter-rust" in ts_missing["missing"]
    assert ts_missing["packages"] == list(tdq_setup.TREE_SITTER_PACKAGES)
    assert {
        "id": "install_tree_sitter",
        "category": "addon",
        "blocking": False,
    } in manifest_missing["actions"]

    # 2. All 5 present -> installed=True and no install_tree_sitter action
    with (
        mock.patch.object(tdq_setup, "_probe_agy_plugins", return_value=[]),
        mock.patch.object(tdq_devtool_mcp, "get_chrome_executable", return_value=""),
    ):
        rc = tdq_setup.main(["--khong-log", "--scan-json"])
    assert rc == 0
    manifest_ok = json.loads(capsys.readouterr().out)
    ts_ok = manifest_ok["addons"]["tree_sitter"]
    assert ts_ok["installed"] is True
    assert ts_ok["missing"] == []
    assert "python" in ts_ok["languages"]
    assert ts_ok["version"]
    assert not any(
        a["id"] == "install_tree_sitter" for a in manifest_ok["actions"]
    )

    # 3. _apply_addons_agy honors dry_run/TDQ_KHONG_CHAM_MAY=1 and installs when allowed
    applied: list[str] = []
    skipped: list[str] = []
    with (
        mock.patch.dict(sys.modules, {"tree_sitter_rust": None}),
        mock.patch.object(
            tdq_setup,
            "_apply_rtk_addon",
            return_value={"ok": False, "installed": False},
        ),
        mock.patch.object(
            tdq_setup,
            "_apply_caveman_addon",
            return_value={"wrapped": [], "enabled": False},
        ),
        mock.patch.object(
            tdq_setup,
            "ensure_archify_installed",
            return_value=(False, "skipped: TDQ_KHONG_CHAM_MAY=1"),
        ),
        mock.patch.object(tdq_setup.tdq_ten_lenh, "chay_subprocess") as sub_dry,
    ):
        addons_dry = tdq_setup._apply_addons_agy(
            str(project),
            home,
            setupfully=True,
            dry_run=True,
            applied=applied,
            skipped=skipped,
        )
    sub_dry.assert_not_called()
    assert addons_dry["tree_sitter"]["ok"] is False
    assert "tree-sitter-rust" in addons_dry["tree_sitter"]["detail"]

    monkeypatch.setenv("TDQ_KHONG_CHAM_MAY", "0")
    state = {"fixed": False}

    def fake_support():
        if state["fixed"]:
            return {
                "available": True,
                "missing": [],
                "installed": list(tdq_setup.TREE_SITTER_PACKAGES),
                "languages": ["python", "javascript", "typescript", "tsx", "rust"],
                "version": "0.25.0",
            }
        return {
            "available": False,
            "missing": ["tree-sitter-rust"],
            "installed": ["tree-sitter"],
            "languages": [],
            "version": "0.25.0",
        }

    def fake_pip(cmd, **_kw):
        state["fixed"] = True
        return mock.MagicMock(returncode=0, stdout="ok\n", stderr="")

    with (
        mock.patch.object(
            tdq_setup,
            "_apply_rtk_addon",
            return_value={"ok": True, "installed": False},
        ),
        mock.patch.object(
            tdq_setup,
            "_apply_caveman_addon",
            return_value={"wrapped": [], "enabled": False},
        ),
        mock.patch.object(
            tdq_setup,
            "ensure_archify_installed",
            return_value=(True, str(home / ".local" / "share" / "archify")),
        ),
        mock.patch.object(
            tdq_setup.archify_registry,
            "check_tree_sitter_support",
            side_effect=fake_support,
        ),
        mock.patch.object(
            tdq_setup.tdq_ten_lenh, "chay_subprocess", side_effect=fake_pip
        ) as sub_live,
    ):
        addons_live = tdq_setup._apply_addons_agy(
            str(project), home, setupfully=True, dry_run=False, applied=[], skipped=[]
        )
    sub_live.assert_called_once()
    assert addons_live["tree_sitter"]["ok"] is True
    assert "0.25.0" in addons_live["tree_sitter"]["detail"]
