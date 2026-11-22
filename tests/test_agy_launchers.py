"""Unit and integration tests for multi-OS Node.js hook and MCP launchers."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parent.parent
TOOLS_DIR = WORKSPACE / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))


def _file_uri(path: Path) -> str:
    return path.resolve().as_uri()


def _run_node_eval(module_path: Path, expr: str, env_extra=None) -> subprocess.CompletedProcess:
    code = (
        f'import * as m from {json.dumps(_file_uri(module_path))};\n'
        f'const out = ({expr});\n'
        'console.log(JSON.stringify(out === undefined ? null : out));\n'
    )
    env = os.environ.copy()
    env.setdefault("TDQ_LOG", "0")
    if env_extra:
        env.update(env_extra)
    kw = {"input": code, "text": True, "capture_output": True, "encoding": "utf-8", "env": env, "timeout": 15}
    if os.name == "nt":
        kw["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
    return subprocess.run(["node", "--input-type=module", "-"], **kw)


def test_generate_launchers_creates_valid_mjs_files(tmp_path: Path):
    from patches import agy_launchers

    created = agy_launchers.generate_launchers(tmp_path)
    names = sorted(p.name for p in created)
    assert names == ["tdq_hook_launcher.mjs", "tdq_mcp_launcher.mjs"]
    for path in created:
        assert path.is_file()
        assert path.parent.name == "scripts"
        res = subprocess.run(["node", "--check", str(path)], capture_output=True, text=True, encoding="utf-8", check=False)
        assert res.returncode == 0, f"node --check failed on {path.name}: {res.stderr}"


def test_hook_launcher_platform_binary_and_python_resolution(tmp_path: Path):
    from patches import agy_launchers

    agy_launchers.generate_launchers(tmp_path)
    hook_mjs = tmp_path / "scripts" / "tdq_hook_launcher.mjs"

    matrix = _run_node_eval(
        hook_mjs,
        """({
            win64: m.resolveBinaryName('win32', 'x64'),
            macArm: m.resolveBinaryName('darwin', 'arm64'),
            macX64: m.resolveBinaryName('darwin', 'x64'),
            lnx64: m.resolveBinaryName('linux', 'x64'),
            other: m.resolveBinaryName('freebsd', 'x64'),
            winPy: m.selectPythonFallback('win32'),
            unixPy: m.selectPythonFallback('linux'),
            stubWin: m.isWindowsAppsStub('C:\\\\Users\\\\u\\\\AppData\\\\Local\\\\Microsoft\\\\WindowsApps\\\\python.exe'),
            realPy: m.isWindowsAppsStub('C:\\\\Python312\\\\python.exe')
        })""",
    )
    assert matrix.returncode == 0, matrix.stderr
    data = json.loads(matrix.stdout)
    assert data["win64"] == "tdq-dispatch.exe"
    assert data["macArm"] == "tdq-dispatch-darwin-arm64"
    assert data["macX64"] == "tdq-dispatch-darwin-x64"
    assert data["lnx64"] == "tdq-dispatch-linux-x86_64"
    assert data["other"] is None
    assert data["winPy"][0]["cmd"] == "py"
    assert data["unixPy"][0]["cmd"] == "python3"
    assert data["stubWin"] is True
    assert data["realPy"] is False


def test_hook_launcher_python_fallback_and_fail_open_logging(tmp_path: Path):
    from patches import agy_launchers

    agy_launchers.generate_launchers(tmp_path)
    hook_mjs = tmp_path / "scripts" / "tdq_hook_launcher.mjs"
    dispatch_dir = tmp_path / "hooks" / "scripts"
    dispatch_dir.mkdir(parents=True, exist_ok=True)
    dispatch_py = dispatch_dir / "dispatch.py"
    dispatch_py.write_text(
        "import json, os, sys\n"
        "payload = json.loads(sys.stdin.read() or '{}')\n"
        "print(json.dumps({'decision': 'allow', 'plugin_root': os.environ.get('PLUGIN_ROOT', ''), 'saw': payload.get('k')}))\n",
        encoding="utf-8",
    )

    kw = {
        "cwd": str(tmp_path),
        "input": '{"k": "probe"}',
        "text": True,
        "capture_output": True,
        "encoding": "utf-8",
        "timeout": 15,
    }
    if os.name == "nt":
        kw["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)

    # Fallback when binary is absent -> runs dispatch.py cleanly with PLUGIN_ROOT + default log on stderr
    env_on = dict(os.environ, TDQ_LOG="1")
    res_py = subprocess.run(["node", "scripts/tdq_hook_launcher.mjs", "--event", "PreToolUse"], env=env_on, **kw)
    assert res_py.returncode == 0, res_py.stderr
    out_py = json.loads(res_py.stdout.strip())
    assert out_py["decision"] == "allow"
    assert Path(out_py["plugin_root"]).resolve() == tmp_path.resolve()
    assert out_py["saw"] == "probe"
    assert "tdq_hook_launcher:" in res_py.stderr

    # TDQ_LOG=0 silences stderr completely even when fallback -> fail-open (remove dispatch.py)
    dispatch_py.unlink()
    env_off = dict(os.environ, TDQ_LOG="0")
    res_fail_open_quiet = subprocess.run(
        ["node", "scripts/tdq_hook_launcher.mjs", "--event", "Stop"], env=env_off, **kw
    )
    assert res_fail_open_quiet.returncode == 0
    assert json.loads(res_fail_open_quiet.stdout.strip()) == {}
    assert res_fail_open_quiet.stderr == ""


def test_mcp_launcher_resolution_user_data_dir_and_logging(tmp_path: Path):
    from patches import agy_launchers

    agy_launchers.generate_launchers(tmp_path)
    mcp_mjs = tmp_path / "scripts" / "tdq_mcp_launcher.mjs"

    fake_home = tmp_path / "fakehome"
    local_bin = fake_home / ".local" / "bin"
    local_bin.mkdir(parents=True, exist_ok=True)
    for bin_name in ("agent-lsp", "agent-lsp.exe"):
        fake_lsp = local_bin / bin_name
        fake_lsp.write_text("#!/bin/sh\necho ok\n", encoding="utf-8")
        if os.name != "nt":
            fake_lsp.chmod(0o755)

    res = _run_node_eval(
        mcp_mjs,
        f"""({{
            lspWin: m.resolveAgentLspCommand('', {json.dumps(str(fake_home))}, 'win32'),
            lspUnix: m.resolveAgentLspCommand('/usr/bin', {json.dumps(str(fake_home))}, 'darwin'),
            specNpxWin: m.buildSpawnSpec('npx', ['-y', 'tavily-mcp@latest'], 'win32'),
            specNpxUnix: m.buildSpawnSpec('npx', ['-y', 'tavily-mcp@latest'], 'linux'),
            specLsp: m.buildSpawnSpec('lsp', [], 'linux', '/opt/homebrew/bin/agent-lsp')
        }})""",
    )
    assert res.returncode == 0, res.stderr
    data = json.loads(res.stdout)
    assert Path(data["lspWin"]) == local_bin / "agent-lsp.exe"
    assert Path(data["lspUnix"]) == local_bin / "agent-lsp"
    assert data["specNpxWin"]["command"] == "cmd.exe"
    assert data["specNpxWin"]["args"] == ["/d", "/s", "/c", "npx.cmd", "-y", "tavily-mcp@latest"]
    assert data["specNpxWin"]["shell"] is False
    assert data["specNpxUnix"]["command"] == "npx"
    assert data["specNpxUnix"]["shell"] is False
    assert data["specLsp"] == {"command": "/opt/homebrew/bin/agent-lsp", "args": [], "shell": False}

    # Test real child spawn with auto-created --userDataDir and TDQ_LOG on/off
    echo_script = tmp_path / "mock_lsp.mjs"
    echo_script.write_text("console.log(JSON.stringify(process.argv.slice(2)));", encoding="utf-8")
    profile_dir = tmp_path / "data" / "chrome-devtools-profile"
    env_log = dict(os.environ, TDQ_LOG="1", TDQ_MCP_OVERRIDE_CMD="node")
    kw = {"cwd": str(tmp_path), "text": True, "capture_output": True, "encoding": "utf-8", "timeout": 15}
    if os.name == "nt":
        kw["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
    run_on = subprocess.run(
        ["node", "scripts/tdq_mcp_launcher.mjs", "lsp", str(echo_script), f"--userDataDir={profile_dir}"],
        env=env_log,
        **kw,
    )
    assert run_on.returncode == 0, run_on.stderr
    assert profile_dir.is_dir()
    assert f"--userDataDir={profile_dir}" in json.loads(run_on.stdout.strip())
    assert "tdq_mcp_launcher:" in run_on.stderr

    env_quiet = dict(os.environ, TDQ_LOG="0", TDQ_MCP_OVERRIDE_CMD="node")
    run_off = subprocess.run(
        ["node", "scripts/tdq_mcp_launcher.mjs", "lsp", str(echo_script)], env=env_quiet, **kw
    )
    assert run_off.returncode == 0
    assert run_off.stderr == ""
