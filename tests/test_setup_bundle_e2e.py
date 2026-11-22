"""End-to-end tests for compiled Antigravity setup bundle, backup, install, and verify."""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = ROOT / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import build_agy_plugin
import install_agy_plugin

pytestmark = [pytest.mark.smoke, pytest.mark.e2e]

PERSONAL_PATH_NEEDLES: tuple[str, ...] = (
    "Users\\admin",
    "Users/admin",
    "Add_on_for_claude",
)
EXPECTED_COMPONENTS = {
    "agents": 8,
    "hooks": 6,
    "mcpServers": 3,
    "rules": 10,
    "sidecars": 0,
    "skills": 12,
}


def _run(
    cmd: list[str],
    cwd: Path = ROOT,
    env: dict[str, str] | None = None,
    timeout: int = 90,
) -> subprocess.CompletedProcess[str]:
    """Run a child command without console flashes and return completed process."""
    kw: dict = {
        "cwd": str(cwd),
        "capture_output": True,
        "text": True,
        "encoding": "utf-8",
        "timeout": timeout,
    }
    if env is not None:
        kw["env"] = env
    if os.name == "nt":
        kw["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
    return subprocess.run(cmd, check=False, **kw)


def _isolated_env(home: Path, state_dir: Path, *, keep_log: bool = False) -> dict[str, str]:
    """Build an isolated environment anchored strictly to temp directories."""
    home.mkdir(parents=True, exist_ok=True)
    state_dir.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env.pop("TDQ_KHONG_CHAM_MAY", None)
    env.update({
        "HOME": str(home),
        "USERPROFILE": str(home),
        "APPDATA": str(home / "AppData" / "Roaming"),
        "LOCALAPPDATA": str(home / "AppData" / "Local"),
        "GEMINI_CONFIG_DIR": str(home / ".gemini" / "config"),
        "ANTIGRAVITY_GEMINI_DIR": str(home / ".gemini"),
        "TDQ_SETUP_STATE_DIR": str(state_dir),
        "PLUGIN_DATA": str(state_dir),
        "TDQ_CAVEMAN_CONFIG": str(home / ".tdq" / "caveman.json"),
        "TDQ_HOST": "antigravity",
        "TDQ_KHOI_TAO_NEN": "0",
        "TDQ_PROJECT_DIR": str(ROOT),
    })
    if keep_log:
        env.pop("TDQ_LOG", None)
    else:
        env["TDQ_LOG"] = "0"
    return env


def _snapshot_tree(root: Path) -> dict[str, tuple[int, int]]:
    """Capture relative file sizes and mtimes to verify real host stays untouched."""
    if not root.is_dir():
        return {}
    snap: dict[str, tuple[int, int]] = {}
    for item in sorted(root.rglob("*")):
        if item.is_file():
            st = item.stat()
            snap[item.relative_to(root).as_posix()] = (st.st_size, st.st_mtime_ns)
    return snap


def _agy_validate(target: Path) -> dict:
    """Run strict Antigravity plugin validator and return parsed JSON."""
    agy_bin = shutil.which("agy.EXE") or shutil.which("agy")
    assert agy_bin, "agy CLI must be available on PATH"
    res = _run([agy_bin, "plugin", "validate", str(target), "--strict", "--json"], cwd=target)
    assert res.returncode == 0, f"agy validate failed: {res.stdout}\n{res.stderr}"
    return json.loads(res.stdout)


def _create_lightweight_upstream(dest: Path) -> Path:
    """Create a fast upstream checkout copy with dummy magic-valid Rust binaries."""
    for folder in ("scripts", "skills", "agents"):
        shutil.copytree(ROOT / folder, dest / folder)
    shutil.copytree(ROOT / "hooks" / "scripts", dest / "hooks" / "scripts")
    prebuilt = dest / "hooks" / "rust" / "tdq-dispatch" / "prebuilt"
    prebuilt.mkdir(parents=True, exist_ok=True)
    (prebuilt / "tdq-dispatch.exe").write_bytes(b"MZ\x90\x00test-pe")
    (prebuilt / "tdq-dispatch-linux-x86_64").write_bytes(b"\x7fELF\x02\x01test-elf")
    (prebuilt / "tdq-dispatch-darwin-arm64").write_bytes(b"\xcf\xfa\xed\xfetest-macho")
    return dest


@pytest.fixture(scope="module")
def compiled_bundle(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    """Compile the full standalone Antigravity plugin once into an isolated temp dir."""
    compiled = tmp_path_factory.mktemp("compiled_bundle") / "compiled"
    stats = build_agy_plugin.build(upstream=ROOT, output=compiled)
    return compiled, stats


def test_e2e_compiled_bundle_validate_and_assets(compiled_bundle: tuple[Path, dict]) -> None:
    """Verify compiled bundle passes strict validation and includes all setup assets."""
    compiled, stats = compiled_bundle
    assert stats["status"] == "OK"
    assert stats["md_checked_budget"] == 22

    report = _agy_validate(compiled)
    assert report["findings"] == []
    assert report["components"] == EXPECTED_COMPONENTS

    required_paths = (
        "scripts/tdq_setup_probe.mjs",
        "scripts/bootstrap.ps1",
        "scripts/bootstrap.sh",
        "scripts/tdq_setup_state.py",
        "scripts/tdq_simulate_verify.py",
        "scripts/tdq_mcp_launcher.mjs",
        "scripts/tdq_mcp_shrink.py",
        "skills/tdq-setup/references/zero-to-full-agy.md",
    )
    for rel in required_paths:
        assert (compiled / rel).is_file(), f"Missing compiled setup asset: {rel}"

    ref_files = sorted((compiled / "skills").glob("*/references/**/*.md"))
    assert ref_files, "Expected compiled skill reference files"
    for ref in ref_files:
        assert len(ref.read_bytes()) < 24000, f"Reference exceeds 24KB budget: {ref}"


def test_e2e_compiled_bundle_portability_and_unwrapped_mcp(
    compiled_bundle: tuple[Path, dict],
) -> None:
    """Verify zero personal paths, unwrapped mcp_config.json, and valid Node ESM syntax."""
    compiled, _ = compiled_bundle
    runtime_targets = [
        compiled / "mcp_config.json",
        compiled / "hooks.json",
        *sorted((compiled / "scripts").glob("*.mjs")),
    ]
    skill_targets = [p for p in sorted((compiled / "skills").rglob("*")) if p.is_file()]

    for path in runtime_targets + skill_targets:
        text = path.read_text(encoding="utf-8", errors="replace")
        for needle in PERSONAL_PATH_NEEDLES:
            assert needle not in text, f"Leaked {needle!r} in {path.relative_to(compiled)}"

    for path in runtime_targets:
        text = path.read_text(encoding="utf-8", errors="replace")
        assert "sys.executable" not in text, f"Leaked sys.executable in {path.relative_to(compiled)}"

    for path in skill_targets:
        for lineno, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if "sys.executable" in line:
                assert "never" in line.lower(), (
                    f"Unexpected sys.executable command reference at {path.name}:{lineno}"
                )

    assert not (compiled / "mcp_config.json.bak").exists()
    mcp_cfg = json.loads((compiled / "mcp_config.json").read_text(encoding="utf-8"))
    for srv_name, entry in mcp_cfg["mcpServers"].items():
        assert entry["command"] == "node", f"{srv_name} must use node launcher"
        assert entry["args"][0] == "${PLUGIN_ROOT}/scripts/tdq_mcp_launcher.mjs"
        assert "caveman" not in entry["args"], f"{srv_name} must stay unwrapped in source bundle"
        assert "PYTHONUTF8" not in (entry.get("env") or {}), f"{srv_name} must stay unwrapped"

    node_bin = shutil.which("node")
    assert node_bin, "node CLI must be available for .mjs syntax checks"
    for mjs in sorted((compiled / "scripts").glob("*.mjs")):
        chk = _run([node_bin, "--check", str(mjs)], cwd=compiled)
        assert chk.returncode == 0, f"node --check failed on {mjs.name}: {chk.stderr}"


def test_e2e_build_enforces_reference_budgets_and_portability(
    tmp_path: Path,
    compiled_bundle: tuple[Path, dict],
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify build_agy_plugin enforces reference <24KB budgets, portability checks, and TDQ_LOG."""
    compiled, _ = compiled_bundle
    stage = tmp_path / "stage_check"
    shutil.copytree(compiled, stage)

    ref_count, ref_violations = build_agy_plugin.check_reference_md_budgets(stage)
    assert ref_count >= 1
    assert ref_violations == []
    assert build_agy_plugin.check_bundle_portability(stage) == []

    oversized = stage / "skills" / "tdq-setup" / "references" / "oversized.md"
    oversized.write_text("# Big\n" + ("x" * 24000), encoding="utf-8")
    _, bad_refs = build_agy_plugin.check_reference_md_budgets(stage)
    assert any("oversized.md" in item for item in bad_refs)

    (stage / "scripts" / "bad_probe.mjs").write_text(
        'const py = "sys.executable";\n', encoding="utf-8"
    )
    (stage / "skills" / "tdq-setup" / "references" / "leak.md").write_text(
        "C:\\Users\\admin\\secret\n", encoding="utf-8"
    )
    port_errs = build_agy_plugin.check_bundle_portability(stage)
    assert any("bad_probe.mjs" in item for item in port_errs)
    assert any("leak.md" in item for item in port_errs)

    fake_upstream = _create_lightweight_upstream(tmp_path / "upstream")
    zero_ref = fake_upstream / "skills" / "tdq-setup" / "references" / "zero-to-full-agy.md"
    zero_ref.write_text("# Too Big\n" + ("a" * 24050), encoding="utf-8")
    out_dir = tmp_path / "out_fail"
    with pytest.raises(RuntimeError, match="zero-to-full-agy.md"):
        build_agy_plugin.build(upstream=fake_upstream, output=out_dir)
    assert not out_dir.exists()

    monkeypatch.setenv("TDQ_LOG", "1")
    build_agy_plugin._log("probe-enabled")
    err_on = capsys.readouterr().err
    assert "build_agy_plugin: probe-enabled" in err_on

    monkeypatch.setenv("TDQ_LOG", "0")
    build_agy_plugin._log("probe-muted")
    assert capsys.readouterr().err == ""


def _assert_caveman_wrapped_mcp(fake_dst: Path) -> None:
    """Assert installed mcp_config.json wraps all servers via Node launcher without sys.executable."""
    mcp_raw = (fake_dst / "mcp_config.json").read_text(encoding="utf-8")
    assert "sys.executable" not in mcp_raw
    assert (fake_dst / "scripts" / "tdq_mcp_shrink.py").is_file()
    mcp_cfg = json.loads(mcp_raw)
    for srv_name in ("lsp", "chrome-devtools", "tavily-primary"):
        entry = mcp_cfg["mcpServers"][srv_name]
        assert entry["command"] == "node"
        assert entry["args"][:4] == [
            "${PLUGIN_ROOT}/scripts/tdq_mcp_launcher.mjs",
            "caveman",
            "--",
            "node",
        ]


def test_e2e_isolated_backup_and_caveman_install(
    tmp_path: Path, compiled_bundle: tuple[Path, dict]
) -> None:
    """Verify backup stays outside plugins/ and Caveman install wraps via Node launcher."""
    compiled, _ = compiled_bundle
    real_cfg = Path.home() / ".gemini" / "config"
    real_before = _snapshot_tree(real_cfg)

    fake_home = tmp_path / "fake_home"
    state_dir = tmp_path / "state"
    fake_plugins = fake_home / ".gemini" / "config" / "plugins"
    fake_dst = fake_plugins / "tdq-workflow-agy"
    fake_dst.mkdir(parents=True)
    (fake_dst / "old_version.txt").write_text("0.104.0\n", encoding="utf-8")
    (fake_dst / "plugin.json").write_text('{"name": "tdq-workflow-agy"}\n', encoding="utf-8")

    bkp_dir = install_agy_plugin.backup_plugin_dir(fake_dst, data_dir=state_dir)
    assert bkp_dir is not None
    assert (state_dir / "backups") in bkp_dir.parents
    assert fake_plugins not in bkp_dir.parents
    assert (bkp_dir / "old_version.txt").read_text(encoding="utf-8") == "0.104.0\n"

    env = _isolated_env(fake_home, state_dir)
    inst = _run(
        [
            sys.executable, "-X", "utf8", str(ROOT / "tools" / "install_agy_plugin.py"),
            "--src", str(compiled), "--target", str(fake_dst),
            "--backup", "--with-caveman", "--skip-rtk",
        ],
        cwd=ROOT,
        env=env,
    )
    assert inst.returncode == 0, f"Installer failed: {inst.stderr}\n{inst.stdout}"
    payload = json.loads(inst.stdout)
    assert payload["caveman"]["enabled"] is True
    assert payload["caveman"]["active"] is True
    assert set(payload["caveman"]["wrapped_servers"]) == {"lsp", "chrome-devtools", "tavily-primary"}
    assert Path(payload["backup_path"]).parent == (state_dir / "backups")

    _assert_caveman_wrapped_mcp(fake_dst)
    assert _agy_validate(fake_dst)["findings"] == []
    plugin_json_hits = sorted(
        p.relative_to(fake_plugins).as_posix() for p in fake_plugins.rglob("*plugin.json*")
    )
    assert plugin_json_hits == ["tdq-workflow-agy/plugin.json"]
    assert list(fake_plugins.iterdir()) == [fake_dst]
    assert _snapshot_tree(real_cfg) == real_before


def _assert_installed_setup_cli(
    compiled: Path, fake_home: Path, state_dir: Path, env: dict[str, str]
) -> None:
    """Verify compiled tdq_setup.py --scan-json and --post-restart-verify in isolated home."""
    fake_dst = fake_home / ".gemini" / "config" / "plugins" / "tdq-workflow-agy"
    inst = _run(
        [
            sys.executable, "-X", "utf8", str(ROOT / "tools" / "install_agy_plugin.py"),
            "--src", str(compiled), "--target", str(fake_dst), "--with-caveman", "--skip-rtk",
        ],
        cwd=ROOT,
        env=env,
    )
    assert inst.returncode == 0, inst.stderr

    setup_py = str(compiled / "scripts" / "tdq_setup.py")
    scan = _run([sys.executable, "-X", "utf8", setup_py, "--scan-json"], cwd=ROOT, env=env)
    assert scan.returncode == 0, scan.stderr
    scan_data = json.loads(scan.stdout)
    assert scan_data["claude_debt_count"] == 0
    assert scan_data["host"] == "antigravity"

    (state_dir / "setup-pending.flag").write_text("pending\n", encoding="utf-8")
    verify_cmd = _run(
        [
            sys.executable, "-X", "utf8", setup_py,
            "--post-restart-verify", "--confirm-restarted",
            "--state-dir", str(state_dir), "--json",
        ],
        cwd=ROOT,
        env=env,
    )
    assert verify_cmd.returncode == 0, verify_cmd.stderr + verify_cmd.stdout
    verify_data = json.loads(verify_cmd.stdout)
    assert verify_data["status"] == "verified"
    assert verify_data["verify"]["core_gate"] == "PASS"
    assert verify_data["verify"]["temp_cleaned"] is True
    assert not (state_dir / "setup-pending.flag").exists()


def test_e2e_compiled_post_restart_simulate_verify(
    tmp_path: Path,
    compiled_bundle: tuple[Path, dict],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify compiled bundle passes 6-layer post-restart verification in isolated sandbox."""
    compiled, _ = compiled_bundle
    real_cfg = Path.home() / ".gemini" / "config"
    real_before = _snapshot_tree(real_cfg)

    fake_home = tmp_path / "fake_home"
    state_dir = tmp_path / "state"
    env = _isolated_env(fake_home, state_dir)
    for key in (
        "HOME", "USERPROFILE", "GEMINI_CONFIG_DIR", "ANTIGRAVITY_GEMINI_DIR",
        "TDQ_SETUP_STATE_DIR", "PLUGIN_DATA", "TDQ_CAVEMAN_CONFIG", "TDQ_HOST", "TDQ_LOG",
    ):
        monkeypatch.setenv(key, env[key])
    monkeypatch.delenv("TDQ_KHONG_CHAM_MAY", raising=False)

    monkeypatch.syspath_prepend(str(compiled / "scripts"))
    for mod_name in ("tdq_simulate_verify", "tdq_setup_state", "tdq_lsp"):
        sys.modules.pop(mod_name, None)
    import tdq_simulate_verify  # type: ignore[import-not-found]

    sim_res = tdq_simulate_verify.run_simulate_verify(plugin_root=compiled, data_dir=state_dir)
    failing_layers = {
        k: v for k, v in (sim_res.get("layers") or {}).items() if v.get("status") != "PASS"
    }
    assert sim_res["core_gate"] == "PASS", (
        f"core_gate={sim_res.get('core_gate')} temp_cleaned={sim_res.get('temp_cleaned')} "
        f"config_untouched={sim_res.get('config_untouched')} elapsed={sim_res.get('elapsed_sec')} "
        f"errors={sim_res.get('errors')} failing={failing_layers}"
    )
    assert sim_res["temp_cleaned"] is True
    assert sim_res["config_untouched"] is True
    assert sim_res["errors"] == []
    for layer_name in ("T1", "T2", "T3", "T4", "T5", "T6"):
        assert sim_res["layers"][layer_name]["status"] == "PASS", (
            layer_name,
            sim_res["layers"][layer_name],
        )

    _assert_installed_setup_cli(compiled, fake_home, state_dir, env)
    assert _snapshot_tree(real_cfg) == real_before
