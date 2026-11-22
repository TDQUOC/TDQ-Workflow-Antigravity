#!/usr/bin/env python3
"""Unit tests for scripts/caveman_config.py (user-level opt-in and MCP wrapping)."""

from __future__ import annotations

import copy
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

WORKTREE_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = WORKTREE_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
import caveman_config

SAMPLE_MCP_CONFIG = {
    "mcpServers": {
        "lsp": {
            "command": "C:/bin/agent-lsp.exe",
            "args": ["python:pyright-langserver.cmd,--stdio"],
        },
        "chrome-devtools": {
            "command": "npx.cmd",
            "args": ["-y", "chrome-devtools-mcp@latest"],
        },
        "tavily-primary": {
            "command": "npx.cmd",
            "args": ["-y", "tavily-mcp@latest"],
            "env": {"TAVILY_API_KEY": "secret-placeholder"},
        },
    }
}


class TestCavemanConfigPathAndState(unittest.TestCase):
    """Verify config_path resolution, default opt-in safety, and atomic writes."""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="tdq-caveman-cfg-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def test_config_path_respects_env_and_home_precedence(self) -> None:
        custom_file = self.tmp / "custom" / "my-caveman.json"
        with mock.patch.dict(
            os.environ,
            {
                "TDQ_CAVEMAN_CONFIG": str(custom_file),
                "HOME": str(self.tmp / "home-ignored"),
            },
            clear=False,
        ):
            self.assertEqual(caveman_config.config_path(), custom_file)
            explicit = caveman_config.config_path(home=str(self.tmp / "explicit"))
            self.assertEqual(
                explicit, self.tmp / "explicit" / ".tdq" / "caveman.json"
            )

        with mock.patch.dict(
            os.environ,
            {"TDQ_CAVEMAN_CONFIG": "", "HOME": str(self.tmp / "unix-home")},
            clear=False,
        ):
            self.assertEqual(
                caveman_config.config_path(),
                self.tmp / "unix-home" / ".tdq" / "caveman.json",
            )

    def test_defaults_when_missing_or_corrupt(self) -> None:
        cfg = caveman_config.load_config(home=str(self.tmp))
        self.assertFalse(cfg["enabled"])
        self.assertFalse(cfg["prompt_muted"])
        self.assertEqual(cfg["wrapped_servers"], [])
        self.assertFalse(caveman_config.is_prompt_muted(home=str(self.tmp)))

        target = caveman_config.config_path(home=str(self.tmp))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("{broken json", encoding="utf-8")
        corrupt_cfg = caveman_config.load_config(home=str(self.tmp))
        self.assertFalse(corrupt_cfg["enabled"])
        self.assertFalse(corrupt_cfg["prompt_muted"])

    def test_enable_requires_explicit_approval(self) -> None:
        res = caveman_config.enable_caveman(approve=False, home=str(self.tmp))
        self.assertFalse(res["ok"])
        self.assertEqual(res["reason"], "approval_required")
        self.assertFalse(res["enabled"])
        self.assertFalse(caveman_config.config_path(home=str(self.tmp)).exists())

    def test_enable_disable_and_prompt_mute_roundtrip(self) -> None:
        muted_path = caveman_config.set_prompt_muted(True, home=str(self.tmp))
        self.assertTrue(muted_path.is_file())
        self.assertTrue(caveman_config.is_prompt_muted(home=str(self.tmp)))
        self.assertFalse(caveman_config.load_config(home=str(self.tmp))["enabled"])

        enabled = caveman_config.enable_caveman(
            approve=True,
            wrapped_servers=["lsp", "chrome-devtools", "tavily-primary"],
            home=str(self.tmp),
        )
        self.assertTrue(enabled["ok"])
        self.assertTrue(enabled["enabled"])
        self.assertTrue(enabled["prompt_muted"])
        self.assertEqual(
            enabled["wrapped_servers"],
            ["lsp", "chrome-devtools", "tavily-primary"],
        )
        self.assertTrue(enabled["updated_at"])

        disabled = caveman_config.disable_caveman(home=str(self.tmp))
        self.assertTrue(disabled["ok"])
        self.assertFalse(disabled["enabled"])
        self.assertEqual(disabled["wrapped_servers"], [])
        self.assertTrue(disabled["prompt_muted"])

        caveman_config.set_prompt_muted(False, home=str(self.tmp))
        self.assertFalse(caveman_config.is_prompt_muted(home=str(self.tmp)))


class TestMcpConfigWrapping(unittest.TestCase):
    """Verify atomic wrap_mcp_config, idempotency, backup, and exact unwrap."""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="tdq-caveman-mcp-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.mcp_file = self.tmp / "mcp_config.json"
        self.proxy_script = SCRIPTS_DIR / "tdq_mcp_shrink.py"

    def test_wrap_is_idempotent_creates_backup_and_unwrap_restores_exact(self) -> None:
        original_text = json.dumps(SAMPLE_MCP_CONFIG, indent=2) + "\n"
        self.mcp_file.write_text(original_text, encoding="utf-8")

        wrapped = caveman_config.wrap_mcp_config(self.mcp_file, self.proxy_script)
        self.assertEqual(wrapped, ["lsp", "chrome-devtools", "tavily-primary"])

        bak_file = self.tmp / "mcp_config.json.bak"
        self.assertTrue(bak_file.is_file())
        self.assertEqual(bak_file.read_text(encoding="utf-8"), original_text)

        wrapped_cfg = json.loads(self.mcp_file.read_text(encoding="utf-8"))
        for name in ("lsp", "chrome-devtools", "tavily-primary"):
            srv = wrapped_cfg["mcpServers"][name]
            orig = SAMPLE_MCP_CONFIG["mcpServers"][name]
            self.assertEqual(srv["command"], sys.executable)
            self.assertEqual(
                srv["args"],
                ["-u", str(self.proxy_script), "--", orig["command"], *orig["args"]],
            )
            self.assertEqual(srv["env"]["PYTHONUTF8"], "1")
            self.assertEqual(srv["env"]["PYTHONUNBUFFERED"], "1")
        self.assertEqual(
            wrapped_cfg["mcpServers"]["tavily-primary"]["env"]["TAVILY_API_KEY"],
            "secret-placeholder",
        )

        # Second wrap call must be a clean no-op and keep backup untouched.
        second = caveman_config.wrap_mcp_config(self.mcp_file, self.proxy_script)
        self.assertEqual(second, [])
        self.assertEqual(
            json.loads(self.mcp_file.read_text(encoding="utf-8")),
            wrapped_cfg,
        )

        unwrapped = caveman_config.unwrap_mcp_config(self.mcp_file)
        self.assertEqual(unwrapped, ["lsp", "chrome-devtools", "tavily-primary"])
        restored_cfg = json.loads(self.mcp_file.read_text(encoding="utf-8"))
        self.assertEqual(restored_cfg, SAMPLE_MCP_CONFIG)

        # Second unwrap is also idempotent.
        self.assertEqual(caveman_config.unwrap_mcp_config(self.mcp_file), [])

    def test_wrap_partial_servers_leaves_unknown_untouched(self) -> None:
        partial = {
            "mcpServers": {
                "lsp": copy.deepcopy(SAMPLE_MCP_CONFIG["mcpServers"]["lsp"]),
                "tavily-primary": copy.deepcopy(
                    SAMPLE_MCP_CONFIG["mcpServers"]["tavily-primary"]
                ),
                "custom-other": {"command": "node", "args": ["server.js"]},
            }
        }
        self.mcp_file.write_text(json.dumps(partial, indent=2), encoding="utf-8")

        wrapped = caveman_config.wrap_mcp_config(self.mcp_file, self.proxy_script)
        self.assertEqual(wrapped, ["lsp", "tavily-primary"])
        after = json.loads(self.mcp_file.read_text(encoding="utf-8"))
        self.assertEqual(
            after["mcpServers"]["custom-other"],
            {"command": "node", "args": ["server.js"]},
        )

        unwrapped = caveman_config.unwrap_mcp_config(self.mcp_file)
        self.assertEqual(unwrapped, ["lsp", "tavily-primary"])
        self.assertEqual(
            json.loads(self.mcp_file.read_text(encoding="utf-8")),
            partial,
        )

    def test_wrap_missing_file_raises(self) -> None:
        with self.assertRaises(FileNotFoundError):
            caveman_config.wrap_mcp_config(
                self.tmp / "nonexistent.json", self.proxy_script
            )


class TestProbeAndLogging(unittest.TestCase):
    """Verify probe_caveman status reporting and TDQ_LOG=0 stderr muting."""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="tdq-caveman-probe-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.plugin_root = self.tmp / "plugin"
        (self.plugin_root / "scripts").mkdir(parents=True, exist_ok=True)
        self.proxy = self.plugin_root / "scripts" / "tdq_mcp_shrink.py"
        self.proxy.write_text("#!/usr/bin/env python3\n", encoding="utf-8")
        self.mcp_file = self.plugin_root / "mcp_config.json"
        self.mcp_file.write_text(json.dumps(SAMPLE_MCP_CONFIG), encoding="utf-8")

    def test_probe_reports_before_and_after_opt_in(self) -> None:
        before = caveman_config.probe_caveman(
            plugin_root=self.plugin_root, home=str(self.tmp)
        )
        self.assertFalse(before["enabled"])
        self.assertFalse(before["active"])
        self.assertTrue(before["proxy_exists"])
        self.assertEqual(before["mcp_wrapped_servers"], [])
        self.assertEqual(
            before["mcp_present_servers"],
            ["lsp", "chrome-devtools", "tavily-primary"],
        )

        wrapped = caveman_config.wrap_mcp_config(self.mcp_file, self.proxy)
        caveman_config.enable_caveman(
            approve=True, wrapped_servers=wrapped, home=str(self.tmp)
        )
        after = caveman_config.probe_caveman(
            plugin_root=self.plugin_root, home=str(self.tmp)
        )
        self.assertTrue(after["enabled"])
        self.assertTrue(after["active"])
        self.assertEqual(
            after["mcp_wrapped_servers"],
            ["lsp", "chrome-devtools", "tavily-primary"],
        )

    def test_tdq_log_zero_mutes_stderr_in_process_and_cli(self) -> None:
        buf_muted = io.StringIO()
        with mock.patch.dict(os.environ, {"TDQ_LOG": "0"}), mock.patch(
            "sys.stderr", buf_muted
        ):
            caveman_config.set_prompt_muted(True, home=str(self.tmp))
        self.assertEqual(buf_muted.getvalue(), "")

        buf_on = io.StringIO()
        with mock.patch.dict(os.environ, {"TDQ_LOG": "1"}), mock.patch(
            "sys.stderr", buf_on
        ):
            caveman_config.set_prompt_muted(False, home=str(self.tmp))
        self.assertRegex(
            buf_on.getvalue(),
            re.compile(r"^\[\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\] caveman_config:"),
        )

        env_on = dict(os.environ, TDQ_LOG="1", HOME=str(self.tmp))
        env_on.pop("TDQ_CAVEMAN_CONFIG", None)
        proc_on = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS_DIR / "caveman_config.py"),
                "--plugin-root",
                str(self.plugin_root),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env_on,
            check=False,
        )
        self.assertEqual(proc_on.returncode, 0)
        self.assertIn("T", proc_on.stderr)
        self.assertEqual(json.loads(proc_on.stdout)["enabled"], False)

        env_off = dict(env_on, TDQ_LOG="0")
        proc_off = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS_DIR / "caveman_config.py"),
                "--plugin-root",
                str(self.plugin_root),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env_off,
            check=False,
        )
        self.assertEqual(proc_off.returncode, 0)
        self.assertEqual(proc_off.stderr, "")

    def test_wrap_agy_plugin_raw_synced_server_uses_node_launcher(self) -> None:
        agy_dir = self.tmp / "agy-plugin"
        (agy_dir / "scripts").mkdir(parents=True)
        (agy_dir / "plugin.json").write_text('{"name":"tdq-workflow-agy"}\n', encoding="utf-8")
        (agy_dir / "scripts" / "tdq_mcp_launcher.mjs").write_text("// launcher\n", encoding="utf-8")
        mcp_path = agy_dir / "mcp_config.json"
        mcp_path.write_text(json.dumps(SAMPLE_MCP_CONFIG, indent=2), encoding="utf-8")
        wrapped = caveman_config.wrap_mcp_config(mcp_path, self.tmp / "tdq_mcp_shrink.py")
        self.assertEqual(wrapped, ["lsp", "chrome-devtools", "tavily-primary"])
        cfg = json.loads(mcp_path.read_text(encoding="utf-8"))
        self.assertEqual(cfg["mcpServers"]["lsp"]["command"], "node")
        self.assertIn("tdq_mcp_launcher.mjs", cfg["mcpServers"]["lsp"]["args"][0])
        self.assertEqual(cfg["mcpServers"]["lsp"]["args"][1:4], ["caveman", "--", "C:/bin/agent-lsp.exe"])
        self.assertNotIn(sys.executable, mcp_path.read_text(encoding="utf-8"))
        restored = caveman_config.unwrap_mcp_config(mcp_path)
        self.assertEqual(restored, ["lsp", "chrome-devtools", "tavily-primary"])
        self.assertEqual(
            json.loads(mcp_path.read_text(encoding="utf-8"))["mcpServers"]["lsp"]["command"],
            "C:/bin/agent-lsp.exe",
        )


if __name__ == "__main__":
    unittest.main()
