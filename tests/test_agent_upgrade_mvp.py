#!/usr/bin/env python3
"""Integration and unit tests for the TDQ 4-pillar agent upgrade MVP."""

from __future__ import annotations

import datetime
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest import mock

TESTS_DIR = Path(__file__).resolve().parent
ROOT = TESTS_DIR.parent
SCRIPTS_DIR = ROOT / "scripts"
for _path in (str(TESTS_DIR), str(SCRIPTS_DIR)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import tdq_config  # noqa: E402


def _clean_env(**updates: str) -> dict[str, str]:
    """Return a copy of os.environ without config overrides, then apply updates."""
    env = dict(os.environ)
    env.pop("TDQ_MAX_QC_SUBAGENTS", None)
    env.pop("TDQ_PROJECT_DIR", None)
    env.pop("TDQ_LOG", None)
    env.update(updates)
    return env


def _write_json(path: Path, payload: object) -> None:
    """Write JSON payload to path creating parent directories."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


class TestTdqConfig(unittest.TestCase):
    """Verify tdq_config precedence, fallbacks, model ladder, and TDQ_LOG=0."""

    def test_default_config_and_deep_copy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.dict(os.environ, _clean_env(TDQ_LOG="0"), clear=True):
                cfg = tdq_config.load_config(tmp)
                self.assertEqual(tdq_config.max_qc_subagents(tmp), 5)
                self.assertTrue(cfg["qc"]["full_light_qc"])
                self.assertEqual(cfg["agents"]["default_model"], "inherit")
                self.assertEqual(cfg["agents"]["auto_escalate_retries"], 2)
                cfg["qc"]["ultra_max_subagents"] = 99
                self.assertEqual(tdq_config.DEFAULT_CONFIG["qc"]["ultra_max_subagents"], 5)

    def test_precedence_env_over_project_over_plugin(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            plugin_dir = base / "plugin"
            project_dir = base / "project"
            _write_json(plugin_dir / "tdq-config.json", {"qc": {"ultra_max_subagents": 7}})
            _write_json(
                project_dir / "docs" / "tdq" / "config.json",
                {"qc": {"ultra_max_subagents": 3}},
            )
            with mock.patch.object(tdq_config, "PLUGIN_ROOT", plugin_dir):
                with mock.patch.dict(os.environ, _clean_env(TDQ_LOG="0"), clear=True):
                    self.assertEqual(tdq_config.max_qc_subagents(project_dir), 3)
                with mock.patch.dict(
                    os.environ,
                    _clean_env(TDQ_LOG="0", TDQ_MAX_QC_SUBAGENTS="9"),
                    clear=True,
                ):
                    self.assertEqual(tdq_config.max_qc_subagents(project_dir), 9)
                other_project = base / "other"
                other_project.mkdir()
                with mock.patch.dict(os.environ, _clean_env(TDQ_LOG="0"), clear=True):
                    self.assertEqual(tdq_config.max_qc_subagents(other_project), 7)

    def test_unlimited_keywords_and_zero_return_none(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp)
            _write_json(
                project_dir / "docs" / "tdq" / "config.json",
                {"qc": {"ultra_max_subagents": 0}},
            )
            with mock.patch.dict(os.environ, _clean_env(TDQ_LOG="0"), clear=True):
                self.assertIsNone(tdq_config.max_qc_subagents(project_dir))
            for raw in ("unlimited", "0", "none", "khong-gioi-han", "UNLIMITED"):
                with self.subTest(raw=raw):
                    with mock.patch.dict(
                        os.environ,
                        _clean_env(TDQ_LOG="0", TDQ_MAX_QC_SUBAGENTS=raw),
                        clear=True,
                    ):
                        self.assertIsNone(tdq_config.max_qc_subagents(project_dir))

    def test_corrupt_json_falls_back_to_default_and_logs_warning(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            project_dir = base / "project"
            cfg_file = project_dir / "docs" / "tdq" / "config.json"
            cfg_file.parent.mkdir(parents=True, exist_ok=True)
            cfg_file.write_text("{corrupt json", encoding="utf-8")

            err = io.StringIO()
            with mock.patch.dict(os.environ, _clean_env(TDQ_LOG="1"), clear=True):
                with redirect_stderr(err):
                    loaded = tdq_config.load_config(project_dir)
                    limit = tdq_config.max_qc_subagents(project_dir)
            self.assertEqual(limit, 5)
            self.assertEqual(loaded, tdq_config.DEFAULT_CONFIG)
            self.assertIsNot(loaded, tdq_config.DEFAULT_CONFIG)
            self.assertIn("tdq_config:", err.getvalue())

            plugin_dir = base / "plugin"
            plugin_dir.mkdir(parents=True, exist_ok=True)
            (plugin_dir / "tdq-config.json").write_text("[1, 2]", encoding="utf-8")
            clean_project = base / "clean_project"
            clean_project.mkdir()
            err_plugin = io.StringIO()
            with mock.patch.object(tdq_config, "PLUGIN_ROOT", plugin_dir):
                with mock.patch.dict(os.environ, _clean_env(TDQ_LOG="1"), clear=True):
                    with redirect_stderr(err_plugin):
                        self.assertEqual(tdq_config.max_qc_subagents(clean_project), 5)
            self.assertIn("tdq_config:", err_plugin.getvalue())

    def test_invalid_max_qc_values_fallback_to_five(self) -> None:
        bad_values: list[object] = [-1, -42, True, False, 2.5, "abc", "-3", None]
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp)
            for bad in bad_values:
                with self.subTest(bad=bad):
                    _write_json(
                        project_dir / "docs" / "tdq" / "config.json",
                        {"qc": {"ultra_max_subagents": bad}},
                    )
                    err = io.StringIO()
                    with mock.patch.dict(os.environ, _clean_env(TDQ_LOG="1"), clear=True):
                        with redirect_stderr(err):
                            self.assertEqual(tdq_config.max_qc_subagents(project_dir), 5)
                    self.assertTrue(err.getvalue().strip())

    def test_model_ladder_order_and_resolve_role_escalation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.dict(os.environ, _clean_env(TDQ_LOG="0"), clear=True):
                ladder = tdq_config.model_ladder(tmp)
                families = [entry["family"] for entry in ladder]
                self.assertEqual(
                    families,
                    [
                        "gemini-3.8-flash",
                        "gemini-4-hydrogen",
                        "gemini-4-neon",
                        "gemini-4-carbon",
                    ],
                )
                self.assertEqual([entry["tier"] for entry in ladder], [1, 2, 3, 4])

                exp = tdq_config.resolve_model_for_role("tdq-explorer", attempt=1, cwd=tmp)
                self.assertEqual(exp["tier"], 1)
                self.assertEqual(exp["invoke_model"], "flash")
                self.assertFalse(exp["escalated"])

                impl1 = tdq_config.resolve_model_for_role("tdq-implementer", attempt=1, cwd=tmp)
                self.assertEqual(impl1["tier"], 2)
                self.assertFalse(impl1["escalated"])

                impl3 = tdq_config.resolve_model_for_role("tdq-implementer", attempt=3, cwd=tmp)
                self.assertGreater(impl3["tier"], impl1["tier"])
                self.assertEqual(impl3["family"], "gemini-4-neon")
                self.assertTrue(impl3["escalated"])

                sec = tdq_config.resolve_model_for_role("tdq-security-reviewer", attempt=1, cwd=tmp)
                self.assertEqual(sec["tier"], 4)
                self.assertEqual(sec["invoke_model"], "pro")

                fallback_role = tdq_config.resolve_model_for_role("custom-role", attempt=0, cwd=tmp)
                self.assertEqual(fallback_role["tier"], 2)
                self.assertEqual(fallback_role["attempt"], 1)
                self.assertFalse(fallback_role["escalated"])

    def test_cli_and_tdq_log_zero_mutes_stderr(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp)
            script = str(SCRIPTS_DIR / "tdq_config.py")

            logged = subprocess.run(
                [sys.executable, script, "show", "--json", "--cwd", str(project_dir)],
                env=_clean_env(TDQ_LOG="1"),
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=20,
            )
            self.assertEqual(logged.returncode, 0, logged.stderr)
            parsed = json.loads(logged.stdout)
            self.assertEqual(parsed["qc"]["ultra_max_subagents"], 5)
            err_lines = [line for line in logged.stderr.splitlines() if line.strip()]
            self.assertTrue(err_lines)
            stamp = err_lines[0][1:].split("] ", 1)[0]
            self.assertIsNotNone(datetime.datetime.fromisoformat(stamp).utcoffset())

            muted = subprocess.run(
                [sys.executable, script, "show", "--json", "--cwd", str(project_dir)],
                env=_clean_env(TDQ_LOG="0"),
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=20,
            )
            self.assertEqual(muted.returncode, 0, muted.stderr)
            self.assertEqual(muted.stderr, "")

            max_qc_proc = subprocess.run(
                [sys.executable, script, "max-qc", "--cwd", str(project_dir)],
                env=_clean_env(TDQ_LOG="0", TDQ_MAX_QC_SUBAGENTS="unlimited"),
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=20,
            )
            self.assertEqual(max_qc_proc.returncode, 0, max_qc_proc.stderr)
            self.assertEqual(max_qc_proc.stdout.strip(), "unlimited")
            self.assertEqual(max_qc_proc.stderr, "")

            max_qc_json = subprocess.run(
                [sys.executable, script, "max-qc", "--json", "--cwd", str(project_dir)],
                env=_clean_env(TDQ_LOG="0", TDQ_MAX_QC_SUBAGENTS="unlimited"),
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=20,
            )
            self.assertEqual(max_qc_json.returncode, 0, max_qc_json.stderr)
            self.assertEqual(json.loads(max_qc_json.stdout), {"ultra_max_subagents": None, "unlimited": True})

            corrupt_file = project_dir / "docs" / "tdq" / "config.json"
            corrupt_file.parent.mkdir(parents=True, exist_ok=True)
            corrupt_file.write_text("{broken", encoding="utf-8")
            corrupt_muted = subprocess.run(
                [sys.executable, script, "max-qc", "--cwd", str(project_dir)],
                env=_clean_env(TDQ_LOG="0"),
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=20,
            )
            self.assertEqual(corrupt_muted.returncode, 0)
            self.assertEqual(corrupt_muted.stdout.strip(), "5")
            self.assertEqual(corrupt_muted.stderr, "")

            show_text = subprocess.run(
                [sys.executable, script, "show", "--cwd", str(project_dir)],
                env=_clean_env(TDQ_LOG="0"),
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=20,
            )
            self.assertEqual(show_text.returncode, 0, show_text.stderr)
            self.assertIn("gemini-3.8-flash", show_text.stdout)
            self.assertIn("gemini-4-carbon", show_text.stdout)


if __name__ == "__main__":
    unittest.main()
