"""End-to-end release branch, isolated agy CLI install, and TDQ_LOG tests."""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = WORKSPACE / "scripts"


def _run(cmd, cwd=WORKSPACE, env=None, input_text=None):
    kw = {
        "cwd": str(cwd),
        "capture_output": True,
        "text": True,
        "encoding": "utf-8",
        "timeout": 90,
        "env": env,
        "input": input_text,
    }
    if os.name == "nt":
        kw["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
    return subprocess.run(cmd, **kw)


def _snapshot_real_gemini_cfg() -> tuple[int, float]:
    cfg_dir = Path.home() / ".gemini" / "config"
    if not cfg_dir.exists():
        return (0, 0.0)
    files = [p for p in cfg_dir.rglob("*") if p.is_file()]
    newest = max((p.stat().st_mtime for p in files), default=0.0)
    return (len(files), newest)


def test_release_branch_and_isolated_agy_install_preserve_home(tmp_path: Path):
    before_cfg = _snapshot_real_gemini_cfg()

    # 1. Stage a clean temp git repo holding the built plugin under plugins/tdq-workflow-agy
    src_repo = tmp_path / "src_repo"
    bundle_dst = src_repo / "plugins" / "tdq-workflow-agy"
    shutil.copytree(WORKSPACE / "plugins" / "tdq-workflow-agy", bundle_dst)
    assert _run(["git", "init", "-b", "dev"], cwd=src_repo).returncode == 0
    assert _run(["git", "config", "user.name", "TDQ E2E"], cwd=src_repo).returncode == 0
    assert _run(["git", "config", "user.email", "tdq-e2e@example.com"], cwd=src_repo).returncode == 0
    assert _run(["git", "add", "-f", "plugins/tdq-workflow-agy"], cwd=src_repo).returncode == 0
    assert _run(["git", "commit", "-m", "commit built agy plugin"], cwd=src_repo).returncode == 0

    # 2. Publish release/antigravity via build_portable CLI & check TDQ_LOG on/off
    cli = [
        sys.executable,
        "-X",
        "utf8",
        str(SCRIPTS_DIR / "build_portable.py"),
        "--repo",
        str(src_repo),
        "--sinh-release-agy",
        "--nguon",
        "dev",
        "--nhanh-dich",
        "release/antigravity",
    ]
    res_on = _run(cli, env=dict(os.environ, TDQ_LOG="1"))
    assert res_on.returncode == 0, res_on.stderr
    assert "build_portable:" in res_on.stderr

    res_off = _run(cli, env=dict(os.environ, TDQ_LOG="0"))
    assert res_off.returncode == 0, res_off.stderr
    assert res_off.stderr.strip() == ""

    # 3. Clone release/antigravity like another user machine & validate strict
    clone_dir = tmp_path / "cloned_release"
    cl = _run(["git", "clone", "--branch", "release/antigravity", "--depth", "1", str(src_repo), str(clone_dir)])
    assert cl.returncode == 0, cl.stderr
    assert (clone_dir / "plugin.json").is_file()
    assert not (clone_dir / "plugins").exists()

    agy_bin = shutil.which("agy") or shutil.which("agy.EXE")
    assert agy_bin, "agy CLI is required on host for isolated install verification"
    val = _run([agy_bin, "plugin", "validate", str(clone_dir), "--strict", "--json"])
    assert val.returncode == 0, val.stdout + val.stderr
    val_json = json.loads(val.stdout)
    assert val_json["findings"] == []
    assert val_json["components"] == {
        "agents": 8,
        "hooks": 6,
        "mcpServers": 3,
        "rules": 10,
        "sidecars": 0,
        "skills": 12,
    }

    # 4. Install into isolated HOME/USERPROFILE and run hook + check MCP/plugins
    iso_home = tmp_path / "iso_home"
    iso_home.mkdir()
    iso_env = dict(os.environ, USERPROFILE=str(iso_home), HOME=str(iso_home))
    inst = _run([agy_bin, "plugin", "install", str(clone_dir)], env=iso_env)
    assert inst.returncode == 0, inst.stdout + inst.stderr

    listed = _run([agy_bin, "plugin", "list", "--json"], env=iso_env)
    assert listed.returncode == 0, listed.stderr
    plugins = json.loads(listed.stdout)
    agy_entry = next(p for p in plugins if p["name"] == "tdq-workflow-agy")
    assert len(agy_entry["skills"]) == 12
    assert len(agy_entry["agents"]) == 8
    assert len(agy_entry["rules"]) == 10
    assert len(agy_entry["mcpServers"]) == 3
    assert len(agy_entry["hooks"]) == 6

    installed_dir = Path(agy_entry["path"])
    hooks_obj = json.loads((installed_dir / "hooks.json").read_text(encoding="utf-8"))
    hook_cmds = [
        h["command"]
        for group in hooks_obj.values()
        if isinstance(group, dict)
        for ev_val in group.values()
        if isinstance(ev_val, list)
        for item in ev_val
        for h in (item.get("hooks", [item]) if isinstance(item, dict) else [])
        if isinstance(h, dict) and "command" in h
    ]
    assert len(hook_cmds) >= 12
    assert all(c.startswith("node scripts/tdq_hook_launcher.mjs --event ") and '"' not in c for c in hook_cmds)
    mcp_txt = (installed_dir / "mcp_config.json").read_text(encoding="utf-8")
    assert "${PLUGIN_ROOT}/scripts/tdq_mcp_launcher.mjs" in mcp_txt
    assert "${PLUGIN_DATA}/chrome-devtools-profile" in mcp_txt

    hook_run = _run(
        ["node", "scripts/tdq_hook_launcher.mjs", "--event", "PreInvocation"],
        cwd=installed_dir,
        env=dict(iso_env, TDQ_LOG="1"),
        input_text=json.dumps({"conversationId": "e2e-rel", "lastUserInput": "ok"}),
    )
    assert hook_run.returncode == 0, hook_run.stderr
    assert isinstance(json.loads(hook_run.stdout.strip()), dict)

    assert _snapshot_real_gemini_cfg() == before_cfg
