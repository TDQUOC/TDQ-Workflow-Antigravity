#!/usr/bin/env python3
"""Tests for Antigravity Caveman Node launcher, secrets.env loader, and installer backup."""

from __future__ import annotations

import copy
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from unittest import mock

import pytest

WORKTREE_ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = WORKTREE_ROOT / "tools"
SCRIPTS_DIR = WORKTREE_ROOT / "scripts"
for _path in (str(TOOLS_DIR), str(SCRIPTS_DIR)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import caveman_config
import install_agy_plugin
from patches import agy_launchers

AGY_SAMPLE_MCP = {
    "mcpServers": {
        "lsp": {
            "command": "node",
            "args": ["${PLUGIN_ROOT}/scripts/tdq_mcp_launcher.mjs", "lsp"],
        },
        "chrome-devtools": {
            "command": "node",
            "args": [
                "${PLUGIN_ROOT}/scripts/tdq_mcp_launcher.mjs",
                "npx",
                "-y",
                "chrome-devtools-mcp@latest",
                "--userDataDir=${PLUGIN_DATA}/chrome-devtools-profile",
            ],
        },
        "tavily-primary": {
            "command": "node",
            "args": [
                "${PLUGIN_ROOT}/scripts/tdq_mcp_launcher.mjs",
                "npx",
                "-y",
                "tavily-mcp@latest",
            ],
        },
    }
}

CLAUDE_SAMPLE_MCP = {
    "mcpServers": {
        "lsp": {
            "command": "C:/bin/agent-lsp.exe",
            "args": ["python:pyright-langserver.cmd,--stdio"],
        },
        "tavily-primary": {
            "command": "npx.cmd",
            "args": ["-y", "tavily-mcp@latest"],
            "env": {"TAVILY_API_KEY": "explicit-placeholder"},
        },
    }
}


def _run_node_eval(
    module_path: Path, expr: str, env_extra: dict[str, str] | None = None
) -> subprocess.CompletedProcess:
    code = (
        f"import * as m from {json.dumps(module_path.resolve().as_uri())};\n"
        f"const out = ({expr});\n"
        "console.log(JSON.stringify(out === undefined ? null : out));\n"
    )
    env = os.environ.copy()
    env.setdefault("TDQ_LOG", "0")
    if env_extra:
        env.update(env_extra)
    kw: dict[str, object] = {
        "input": code,
        "text": True,
        "capture_output": True,
        "encoding": "utf-8",
        "env": env,
        "timeout": 15,
    }
    if os.name == "nt":
        kw["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
    return subprocess.run(["node", "--input-type=module", "-"], check=False, **kw)


def test_caveman_wrap_agy_preserves_node_no_personal_paths_and_roundtrips(tmp_path: Path):
    plugin_root = tmp_path / "plugin"
    (plugin_root / "scripts").mkdir(parents=True)
    shrink_src = (SCRIPTS_DIR / "tdq_mcp_shrink.py").read_text(encoding="utf-8")
    proxy_script = plugin_root / "scripts" / "tdq_mcp_shrink.py"
    proxy_script.write_text(shrink_src, encoding="utf-8")
    (plugin_root / "scripts" / "tdq_mcp_launcher.mjs").write_text("// launcher\n", encoding="utf-8")

    mcp_file = plugin_root / "mcp_config.json"
    mcp_file.write_text(json.dumps(AGY_SAMPLE_MCP, indent=2) + "\n", encoding="utf-8")

    wrapped = caveman_config.wrap_mcp_config(mcp_file, proxy_script)
    assert wrapped == ["lsp", "chrome-devtools", "tavily-primary"]

    raw_after = mcp_file.read_text(encoding="utf-8")
    assert sys.executable not in raw_after
    assert str(proxy_script) not in raw_after
    assert str(tmp_path) not in raw_after

    cfg_after = json.loads(raw_after)
    for name in ("lsp", "chrome-devtools", "tavily-primary"):
        entry = cfg_after["mcpServers"][name]
        orig = AGY_SAMPLE_MCP["mcpServers"][name]
        assert entry["command"] == "node"
        assert entry["args"][0] == "${PLUGIN_ROOT}/scripts/tdq_mcp_launcher.mjs"
        assert entry["args"][1] == "caveman"
        assert entry["args"][2] == "--"
        assert entry["args"][3:] == [orig["command"], *orig["args"]]
        assert entry["env"]["PYTHONUTF8"] == "1"
        assert entry["env"]["PYTHONUNBUFFERED"] == "1"

    # Second wrap must be idempotent
    assert caveman_config.wrap_mcp_config(mcp_file, proxy_script) == []

    # Probe reports Antigravity wrapped servers accurately
    caveman_config.enable_caveman(approve=True, wrapped_servers=wrapped, home=str(tmp_path))
    probe = caveman_config.probe_caveman(plugin_root=plugin_root, home=str(tmp_path))
    assert probe["enabled"] is True
    assert probe["active"] is True
    assert probe["mcp_wrapped_servers"] == ["lsp", "chrome-devtools", "tavily-primary"]
    assert probe["mcp_wrapper_mode"] == "node_launcher"

    # Unwrap restores exact original Antigravity config
    unwrapped = caveman_config.unwrap_mcp_config(mcp_file)
    assert unwrapped == ["lsp", "chrome-devtools", "tavily-primary"]
    assert json.loads(mcp_file.read_text(encoding="utf-8")) == AGY_SAMPLE_MCP
    assert caveman_config.unwrap_mcp_config(mcp_file) == []


def test_caveman_wrap_claude_backward_compat(tmp_path: Path):
    mcp_file = tmp_path / "claude_mcp.json"
    proxy_script = SCRIPTS_DIR / "tdq_mcp_shrink.py"
    mcp_file.write_text(json.dumps(CLAUDE_SAMPLE_MCP, indent=2) + "\n", encoding="utf-8")

    wrapped = caveman_config.wrap_mcp_config(mcp_file, proxy_script)
    assert wrapped == ["lsp", "tavily-primary"]
    cfg = json.loads(mcp_file.read_text(encoding="utf-8"))
    assert cfg["mcpServers"]["lsp"]["command"] == sys.executable
    assert cfg["mcpServers"]["lsp"]["args"][:4] == [
        "-u",
        str(proxy_script),
        "--",
        "C:/bin/agent-lsp.exe",
    ]
    assert cfg["mcpServers"]["tavily-primary"]["env"]["TAVILY_API_KEY"] == "explicit-placeholder"
    assert caveman_config.wrap_mcp_config(mcp_file, proxy_script) == []

    unwrapped = caveman_config.unwrap_mcp_config(mcp_file)
    assert unwrapped == ["lsp", "tavily-primary"]
    assert json.loads(mcp_file.read_text(encoding="utf-8")) == CLAUDE_SAMPLE_MCP


def test_mcp_launcher_caveman_spawn_spec_and_windowsapps_avoidance(tmp_path: Path):
    created = agy_launchers.generate_launchers(tmp_path)
    assert sorted(p.name for p in created) == ["tdq_hook_launcher.mjs", "tdq_mcp_launcher.mjs"]

    mcp_mjs = tmp_path / "scripts" / "tdq_mcp_launcher.mjs"
    shrink_path = str((tmp_path / "scripts" / "tdq_mcp_shrink.py").resolve())

    # Fake PATH containing WindowsApps stub BEFORE real Python directory
    winapps = tmp_path / "Microsoft" / "WindowsApps"
    winapps.mkdir(parents=True)
    (winapps / "python.exe").write_text("", encoding="utf-8")
    real_py_dir = tmp_path / "Python312"
    real_py_dir.mkdir(parents=True)
    (real_py_dir / "python.exe").write_text("", encoding="utf-8")

    fake_path = f"{winapps};{real_py_dir}"
    res = _run_node_eval(
        mcp_mjs,
        f"""(() => {{
            const winSpec = m.buildSpawnSpec(
                'caveman',
                ['--', 'node', 'tdq_mcp_launcher.mjs', 'lsp'],
                'win32',
                'agent-lsp',
                {{ command: 'py', prefix: ['-3'] }}
            );
            const macSpec = m.buildSpawnSpec(
                'caveman',
                ['--', 'node', 'tdq_mcp_launcher.mjs', 'lsp'],
                'darwin'
            );
            const lnxSpec = m.buildSpawnSpec(
                'caveman',
                ['--', 'node', 'tdq_mcp_launcher.mjs', 'npx', '-y', 'tavily-mcp@latest'],
                'linux'
            );
            const pyWin = m.resolvePythonSpec('win32', {json.dumps(fake_path)});
            let missingDashErr = '';
            try {{ m.buildSpawnSpec('caveman', ['node', 'lsp'], 'linux'); }}
            catch (e) {{ missingDashErr = e.message; }}
            let missingTargetErr = '';
            try {{ m.buildSpawnSpec('caveman', ['--'], 'linux'); }}
            catch (e) {{ missingTargetErr = e.message; }}
            return {{ winSpec, macSpec, lnxSpec, pyWin, missingDashErr, missingTargetErr }};
        }})()""",
    )
    assert res.returncode == 0, res.stderr
    data = json.loads(res.stdout)

    assert data["winSpec"]["command"] == "py"
    assert data["winSpec"]["args"][0:2] == ["-3", "-u"]
    assert Path(data["winSpec"]["args"][2]).resolve() == Path(shrink_path)
    assert data["winSpec"]["args"][3:] == ["--", "node", "tdq_mcp_launcher.mjs", "lsp"]
    assert data["winSpec"]["shell"] is False

    assert data["macSpec"]["command"] == "python3"
    assert data["macSpec"]["args"][0] == "-u"
    assert Path(data["macSpec"]["args"][1]).resolve() == Path(shrink_path)
    assert data["macSpec"]["args"][2:] == ["--", "node", "tdq_mcp_launcher.mjs", "lsp"]

    assert data["lnxSpec"]["command"] == "python3"
    assert data["lnxSpec"]["args"][2:] == [
        "--",
        "node",
        "tdq_mcp_launcher.mjs",
        "npx",
        "-y",
        "tavily-mcp@latest",
    ]

    assert Path(data["pyWin"]["command"]).resolve() == (real_py_dir / "python.exe").resolve()
    assert "windowsapps" not in data["pyWin"]["command"].lower()
    assert data["missingDashErr"] != ""
    assert data["missingTargetErr"] != ""


def test_mcp_launcher_path_expansion_and_secrets_env(tmp_path: Path):
    agy_launchers.generate_launchers(tmp_path)
    mcp_mjs = tmp_path / "scripts" / "tdq_mcp_launcher.mjs"

    fake_home = tmp_path / "home"
    (fake_home / ".local" / "bin").mkdir(parents=True)
    (fake_home / ".cargo" / "bin").mkdir(parents=True)
    (fake_home / ".local" / "share" / "fnm" / "aliases" / "default" / "bin").mkdir(parents=True)
    (fake_home / ".nvm" / "versions" / "node" / "v18.19.0" / "bin").mkdir(parents=True)
    (fake_home / ".nvm" / "versions" / "node" / "v24.5.0" / "bin").mkdir(parents=True)

    state_dir = tmp_path / "state"
    state_dir.mkdir(parents=True)
    secrets_file = state_dir / "secrets.env"
    secrets_file.write_text(
        "# comment line\n"
        "\n"
        'TAVILY_API_KEY="tvly-secret=abc==123"\n'
        "QUOTED_SINGLE='val=with=eq'\n"
        "export UNQUOTED_TOK=plain=token==9\n"
        "EMPTY_OVERRIDE_TARGET=fill-me-in\n",
        encoding="utf-8",
    )

    win_apps = r"C:\Users\u\AppData\Local\Microsoft\WindowsApps"
    posix_home = "/home/tdquser"
    dup_posix_local = f"{posix_home}/.local/bin"
    res = _run_node_eval(
        mcp_mjs,
        f"""(() => {{
            const linuxPath = m.expandUserPath(
                {json.dumps(f"{dup_posix_local}:/usr/bin:{dup_posix_local}")},
                {json.dumps(posix_home)},
                'linux',
                {{}}
            );
            const winPath = m.expandUserPath(
                {json.dumps(win_apps)},
                {json.dumps(str(fake_home))},
                'win32',
                {{ USERPROFILE: {json.dumps(str(fake_home))} }}
            );
            const hostNvmPath = m.expandUserPath(
                '',
                {json.dumps(str(fake_home))},
                process.platform,
                {{}}
            );
            const parsed = m.loadSecretsEnv(
                {{ TDQ_SETUP_STATE_DIR: {json.dumps(str(state_dir))} }},
                {json.dumps(str(fake_home))}
            );
            const childEnv = m.buildChildEnv(
                {{
                    PATH: '/usr/bin',
                    TAVILY_API_KEY: 'explicit-wins',
                    EMPTY_OVERRIDE_TARGET: '',
                    TDQ_SETUP_STATE_DIR: {json.dumps(str(state_dir))},
                }},
                {json.dumps(posix_home)},
                'linux'
            );
            const isolatedEnv = m.loadSecretsEnv(
                {{ TDQ_KHONG_CHAM_MAY: '1', PLUGIN_DATA: {json.dumps(str(state_dir))} }},
                {json.dumps(str(tmp_path / 'empty_home'))}
            );
            return {{ linuxPath, winPath, hostNvmPath, parsed, childEnv, isolatedEnv }};
        }})()""",
    )
    assert res.returncode == 0, res.stderr
    data = json.loads(res.stdout)

    lnx_parts = data["linuxPath"].split(":")
    assert len(lnx_parts) == len(set(lnx_parts))
    assert f"{posix_home}/.local/bin" in lnx_parts
    assert f"{posix_home}/.cargo/bin" in lnx_parts
    assert f"{posix_home}/.local/share/fnm/aliases/default/bin" in lnx_parts
    assert "/opt/homebrew/bin" in lnx_parts

    assert str(fake_home / ".nvm" / "versions" / "node" / "v24.5.0" / "bin") in data["hostNvmPath"]
    assert str(fake_home / ".nvm" / "versions" / "node" / "v18.19.0" / "bin") not in data["hostNvmPath"]

    win_parts = data["winPath"].split(";")
    local_idx = win_parts.index(str(fake_home / ".local" / "bin"))
    apps_idx = win_parts.index(win_apps)
    assert local_idx < apps_idx

    assert data["parsed"] == {
        "TAVILY_API_KEY": "tvly-secret=abc==123",
        "QUOTED_SINGLE": "val=with=eq",
        "UNQUOTED_TOK": "plain=token==9",
        "EMPTY_OVERRIDE_TARGET": "fill-me-in",
    }
    assert data["childEnv"]["TAVILY_API_KEY"] == "explicit-wins"
    assert data["childEnv"]["QUOTED_SINGLE"] == "val=with=eq"
    assert data["childEnv"]["UNQUOTED_TOK"] == "plain=token==9"
    assert data["childEnv"]["EMPTY_OVERRIDE_TARGET"] == "fill-me-in"
    assert data["isolatedEnv"] == {}


def test_mcp_launcher_caveman_end_to_end_shrink_and_secrets_non_leak(tmp_path: Path):
    agy_launchers.generate_launchers(tmp_path)
    (tmp_path / "scripts" / "tdq_mcp_shrink.py").write_text(
        (SCRIPTS_DIR / "tdq_mcp_shrink.py").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (tmp_path / "scripts" / "utf8_io.py").write_text(
        (SCRIPTS_DIR / "utf8_io.py").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    secret_val = "tvly-top-secret=xyz=42"
    state_dir = tmp_path / "plugin_data"
    state_dir.mkdir(parents=True)
    (state_dir / "secrets.env").write_text(
        f'TAVILY_API_KEY="{secret_val}"\n',
        encoding="utf-8",
    )

    mock_mcp = tmp_path / "mock_mcp.mjs"
    mock_mcp.write_text(
        'import readline from "node:readline";\n'
        'const rl = readline.createInterface({ input: process.stdin, crlfDelay: Infinity });\n'
        'rl.on("line", (line) => {\n'
        "  if (!line.trim()) return;\n"
        "  const req = JSON.parse(line);\n"
        '  if (req.method === "tools/list") {\n'
        "    const okSecret = process.env.TAVILY_API_KEY === "
        + json.dumps(secret_val)
        + ";\n"
        "    const resp = {\n"
        '      jsonrpc: "2.0",\n'
        "      id: req.id,\n"
        "      result: {\n"
        "        tools: [{\n"
        '          name: "probe",\n'
        '          description: "This tool allows you to simply check secret status (for example via env). Must remain intact.",\n'
        "          inputSchema: {\n"
        '            $schema: "https://json-schema.org/draft/2020-12/schema",\n'
        '            title: "RedundantTitle",\n'
        '            type: "object",\n'
        '            properties: { ok: { type: "boolean", title: okSecret ? "secret_ok" : "secret_bad" } },\n'
        "          },\n"
        "        }],\n"
        "      },\n"
        "    };\n"
        "    console.log(JSON.stringify(resp));\n"
        "  }\n"
        "});\n",
        encoding="utf-8",
    )

    env_on = os.environ.copy()
    env_on["TDQ_LOG"] = "1"
    env_on["TDQ_SETUP_STATE_DIR"] = str(state_dir)
    env_on.pop("TAVILY_API_KEY", None)

    kw: dict[str, object] = {
        "cwd": str(tmp_path),
        "input": '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}\n',
        "text": True,
        "capture_output": True,
        "encoding": "utf-8",
        "timeout": 20,
    }
    if os.name == "nt":
        kw["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)

    proc_on = subprocess.run(
        [
            "node",
            "scripts/tdq_mcp_launcher.mjs",
            "caveman",
            "--",
            "node",
            str(mock_mcp),
        ],
        check=False,
        env=env_on,
        **kw,
    )
    assert proc_on.returncode == 0, proc_on.stderr
    assert secret_val not in proc_on.stderr
    assert secret_val not in proc_on.stdout
    assert re.search(
        r"^\[\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\] tdq_mcp_launcher:",
        proc_on.stderr,
        re.MULTILINE,
    )
    out_msg = json.loads(proc_on.stdout.strip())
    tool = out_msg["result"]["tools"][0]
    assert "$schema" not in tool["inputSchema"]
    assert "Must remain intact." in tool["description"]
    assert "This tool allows you to" not in tool["description"]
    assert "title" not in tool["inputSchema"]["properties"]["ok"]

    # Also test nested inner launcher + ${PLUGIN_ROOT} expansion
    nested_proc = subprocess.run(
        [
            "node",
            "scripts/tdq_mcp_launcher.mjs",
            "caveman",
            "--",
            "node",
            "${PLUGIN_ROOT}/scripts/tdq_mcp_launcher.mjs",
            "lsp",
            str(mock_mcp),
        ],
        check=False,
        env=dict(env_on, TDQ_MCP_OVERRIDE_CMD="node"),
        **kw,
    )
    assert nested_proc.returncode == 0, nested_proc.stderr
    assert "$schema" not in json.loads(nested_proc.stdout.strip())["result"]["tools"][0]["inputSchema"]

    # TDQ_LOG=0 silences stderr completely
    env_off = dict(env_on, TDQ_LOG="0")
    proc_off = subprocess.run(
        [
            "node",
            "scripts/tdq_mcp_launcher.mjs",
            "caveman",
            "--",
            "node",
            str(mock_mcp),
        ],
        check=False,
        env=env_off,
        **kw,
    )
    assert proc_off.returncode == 0
    assert proc_off.stderr == ""


def test_install_agy_plugin_chmods_sh_and_backups_outside_plugins_dir(tmp_path: Path):
    fake_dst = tmp_path / "home" / ".gemini" / "config" / "plugins" / "tdq-workflow-agy"
    scripts_dir = fake_dst / "scripts"
    scripts_dir.mkdir(parents=True)
    sh_file = scripts_dir / "bootstrap.sh"
    sh_file.write_text("#!/bin/sh\necho ok\n", encoding="utf-8")
    mjs_file = scripts_dir / "tdq_hook_launcher.mjs"
    mjs_file.write_text("console.log('{}');\n", encoding="utf-8")
    (fake_dst / "plugin.json").write_text('{"name":"tdq-workflow-agy"}\n', encoding="utf-8")

    chmod_calls: list[tuple[str, int]] = []
    orig_chmod = Path.chmod

    def _spy_chmod(self: Path, mode: int) -> None:
        chmod_calls.append((self.name, mode))
        if os.name != "nt":
            orig_chmod(self, mode)

    with mock.patch("install_agy_plugin.os.name", "posix"), mock.patch.object(
        Path, "chmod", _spy_chmod
    ), mock.patch.object(install_agy_plugin.shutil, "which", return_value="node"):
        install_agy_plugin._ensure_binary_executable_and_hooks(fake_dst)

    assert ("bootstrap.sh", 0o755) in chmod_calls
    assert ("tdq_hook_launcher.mjs", 0o755) in chmod_calls

    data_dir = tmp_path / "home" / ".gemini" / "antigravity" / "plugin_data" / "tdq-workflow-agy"
    backup_dir = install_agy_plugin.backup_plugin_dir(fake_dst, data_dir=data_dir)
    assert backup_dir is not None
    assert backup_dir.is_dir()
    assert (backup_dir / "plugin.json").is_file()
    assert (backup_dir / "scripts" / "bootstrap.sh").is_file()
    assert fake_dst.parent not in backup_dir.parents

    # Fail closed if someone attempts to place backup inside plugins/
    with pytest.raises(ValueError, match="outside"):
        install_agy_plugin.backup_plugin_dir(fake_dst, data_dir=fake_dst.parent)


def test_install_agy_plugin_with_caveman_keeps_node_and_zero_personal_paths(tmp_path: Path):
    src = tmp_path / "src_plugin"
    (src / "scripts").mkdir(parents=True)
    (src / "plugin.json").write_text('{"name":"tdq-workflow-agy"}\n', encoding="utf-8")
    (src / "hooks.json").write_text("{}\n", encoding="utf-8")
    (src / "mcp_config.json").write_text(
        json.dumps(copy.deepcopy(AGY_SAMPLE_MCP), indent=2) + "\n", encoding="utf-8"
    )
    (src / "scripts" / "tdq_mcp_shrink.py").write_text(
        (SCRIPTS_DIR / "tdq_mcp_shrink.py").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    agy_launchers.generate_launchers(src)

    dst = tmp_path / "dst_plugin"
    caveman_cfg = tmp_path / "caveman.json"
    with mock.patch.dict(
        os.environ, {"TDQ_CAVEMAN_CONFIG": str(caveman_cfg), "TDQ_LOG": "0"}
    ):
        rc = install_agy_plugin.main(
            [
                "--src",
                str(src),
                "--target",
                str(dst),
                "--with-caveman",
                "--skip-rtk",
            ]
        )
    assert rc == 0
    installed_mcp = json.loads((dst / "mcp_config.json").read_text(encoding="utf-8"))
    for name in ("lsp", "chrome-devtools", "tavily-primary"):
        entry = installed_mcp["mcpServers"][name]
        assert entry["command"] == "node"
        assert entry["args"][1] == "caveman"
    installed_raw = (dst / "mcp_config.json").read_text(encoding="utf-8")
    assert sys.executable not in installed_raw
    assert str(tmp_path) not in installed_raw
