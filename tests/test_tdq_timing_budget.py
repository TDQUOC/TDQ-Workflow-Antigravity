"""Unit tests for soft-warn and hard-stop budget tracking in scripts/tdq_timing.py."""

from __future__ import annotations

import ast
import contextlib
import importlib
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

tdq_timing = importlib.import_module("tdq_timing")

ISO_LOG_RE = re.compile(r"^\[20\d{2}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[^\]]*\]\s+")


def _write_telemetry(project: Path, lines: list[dict | str]) -> Path:
    path = project / tdq_timing.TELEMETRY_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "".join(
        (item if isinstance(item, str) else json.dumps(item)) + "\n"
        for item in lines
    )
    path.write_text(text, encoding="utf-8")
    return path


def _write_config(project: Path, budget_caps: dict) -> Path:
    path = project / "docs" / "tdq" / "config.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"p0": {"budget_caps": budget_caps}}
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


class TestBudgetStatus(unittest.TestCase):
    def test_null_caps_always_ok_even_with_high_telemetry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            _write_telemetry(
                project,
                [
                    {"tokens": 5_000_000, "cost_usd": 250.0},
                    {"input_tokens": 1_000_000, "output_tokens": 500_000, "usd": 99.0},
                ],
            )
            stderr = io.StringIO()
            with (
                mock.patch.dict(os.environ, {"TDQ_LOG": "1"}),
                contextlib.redirect_stderr(stderr),
            ):
                res = tdq_timing.check_budget_status(project)
            self.assertEqual(
                res,
                {"state": "ok", "ratio": 0.0, "tokens": 0, "cost_usd": 0.0},
            )
            self.assertEqual(stderr.getvalue(), "")

    def test_invalid_or_non_positive_caps_treated_as_unset(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            _write_telemetry(project, [{"tokens": 999_999, "cost_usd": 50.0}])
            cfg = {
                "p0": {
                    "budget_caps": {
                        "soft_warn_ratio": 0.8,
                        "hard_stop_tokens": 0,
                        "hard_stop_usd": -1.5,
                    }
                }
            }
            res = tdq_timing.check_budget_status(project, config=cfg)
            self.assertEqual(res["state"], "ok")
            self.assertEqual(res["ratio"], 0.0)

            bool_cfg = {
                "p0": {
                    "budget_caps": {
                        "hard_stop_tokens": True,
                        "hard_stop_usd": "10",
                    }
                }
            }
            res_bool = tdq_timing.check_budget_status(project, config=bool_cfg)
            self.assertEqual(res_bool["state"], "ok")

    def test_token_cap_ok_soft_warn_and_hard_stop(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            cfg = {
                "p0": {
                    "budget_caps": {
                        "soft_warn_ratio": 0.8,
                        "hard_stop_tokens": 1000,
                        "hard_stop_usd": None,
                    }
                }
            }
            _write_telemetry(project, [{"tokens": 799}])
            ok_res = tdq_timing.check_budget_status(project, config=cfg)
            self.assertEqual(ok_res["state"], "ok")
            self.assertAlmostEqual(ok_res["ratio"], 0.799, places=6)
            self.assertEqual(ok_res["tokens"], 799)

            _write_telemetry(
                project,
                [
                    {"tokens": 500},
                    {"total_tokens": 300},
                ],
            )
            stderr = io.StringIO()
            with (
                mock.patch.dict(os.environ, {"TDQ_LOG": "1"}),
                contextlib.redirect_stderr(stderr),
            ):
                warn_res = tdq_timing.check_budget_status(project, config=cfg)
            self.assertEqual(warn_res["state"], "soft_warn")
            self.assertAlmostEqual(warn_res["ratio"], 0.8, places=6)
            self.assertEqual(warn_res["tokens"], 800)
            self.assertRegex(stderr.getvalue(), ISO_LOG_RE)
            self.assertIn("soft_warn", stderr.getvalue())

            _write_telemetry(
                project,
                [
                    {"tokens": 500},
                    {"input_tokens": 350, "output_tokens": 200},
                ],
            )
            stop_res = tdq_timing.check_budget_status(project, config=cfg)
            self.assertEqual(stop_res["state"], "hard_stop")
            self.assertAlmostEqual(stop_res["ratio"], 1.05, places=6)
            self.assertEqual(stop_res["tokens"], 1050)

    def test_usd_cap_loaded_from_project_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            _write_config(
                project,
                {
                    "soft_warn_ratio": 0.8,
                    "hard_stop_tokens": None,
                    "hard_stop_usd": 1.0,
                },
            )
            _write_telemetry(
                project,
                [
                    {"cost_usd": 0.1},
                    {"usd": 0.7},
                ],
            )
            warn_res = tdq_timing.check_budget_status(project)
            self.assertEqual(warn_res["state"], "soft_warn")
            self.assertAlmostEqual(warn_res["ratio"], 0.8, places=6)
            self.assertAlmostEqual(warn_res["cost_usd"], 0.8, places=6)

            _write_telemetry(
                project,
                [
                    {"cost_usd": 0.6},
                    {"usd": 0.4},
                ],
            )
            stop_res = tdq_timing.check_budget_status(project)
            self.assertEqual(stop_res["state"], "hard_stop")
            self.assertAlmostEqual(stop_res["ratio"], 1.0, places=6)
            self.assertAlmostEqual(stop_res["cost_usd"], 1.0, places=6)

    def test_missing_telemetry_and_malformed_lines_do_not_crash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            cfg = {
                "p0": {
                    "budget_caps": {
                        "soft_warn_ratio": 0.8,
                        "hard_stop_tokens": 1000,
                        "hard_stop_usd": 5.0,
                    }
                }
            }
            missing = tdq_timing.check_budget_status(project, config=cfg)
            self.assertEqual(
                missing,
                {"state": "ok", "ratio": 0.0, "tokens": 0, "cost_usd": 0.0},
            )

            _write_telemetry(
                project,
                [
                    "",
                    "   ",
                    "{truncated json",
                    "[1, 2, 3]",
                    '"string-row"',
                    {"tokens": True, "cost_usd": False},
                    {"tokens": -50, "cost_usd": -2.0},
                    {"input_tokens": -10, "output_tokens": 100, "usd": 0.5},
                ],
            )
            res = tdq_timing.check_budget_status(project, config=cfg)
            self.assertEqual(res["state"], "ok")
            self.assertEqual(res["tokens"], 100)
            self.assertAlmostEqual(res["cost_usd"], 0.5, places=6)
            self.assertAlmostEqual(res["ratio"], 0.1, places=6)

    def test_combined_caps_take_max_ratio_and_bad_soft_warn_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            _write_telemetry(project, [{"tokens": 200, "cost_usd": 1.6}])
            cfg = {
                "p0": {
                    "budget_caps": {
                        "soft_warn_ratio": 1.5,
                        "hard_stop_tokens": 1000,
                        "hard_stop_usd": 2.0,
                    }
                }
            }
            res = tdq_timing.check_budget_status(project, config=cfg)
            self.assertEqual(res["state"], "soft_warn")
            self.assertAlmostEqual(res["ratio"], 0.8, places=6)
            self.assertEqual(res["tokens"], 200)
            self.assertAlmostEqual(res["cost_usd"], 1.6, places=6)

    def test_config_loader_failure_falls_back_to_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            _write_telemetry(project, [{"tokens": 1_000_000}])
            with mock.patch("tdq_config.load_config", side_effect=RuntimeError("boom")):
                res = tdq_timing.check_budget_status(project)
            self.assertEqual(
                res,
                {"state": "ok", "ratio": 0.0, "tokens": 0, "cost_usd": 0.0},
            )

    def test_tdq_log_zero_mutes_budget_and_cli_status_stderr(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            home = project / "home"
            home.mkdir()
            _write_telemetry(project, [{"tokens": 1000, "cost_usd": 2.0}])
            cfg = {"p0": {"budget_caps": {"hard_stop_tokens": 1000}}}
            stderr = io.StringIO()
            with (
                mock.patch.dict(os.environ, {"TDQ_LOG": "0"}),
                contextlib.redirect_stderr(stderr),
            ):
                res = tdq_timing.check_budget_status(project, config=cfg)
            self.assertEqual(res["state"], "hard_stop")
            self.assertEqual(stderr.getvalue(), "")

            state_path = project / "docs" / "tdq" / "state.json"
            state_path.parent.mkdir(parents=True, exist_ok=True)
            state_path.write_text(
                json.dumps(
                    {
                        "active_request": "2026-11-25-0000-budget-cli",
                        "lane": "full",
                        "phase": "implement",
                        "started_at": "2026-11-25T00:00:00+00:00",
                        "phase_history": [
                            {"phase": "implement", "at": "2026-11-25T00:00:00+00:00"}
                        ],
                    }
                ),
                encoding="utf-8",
            )
            env = dict(os.environ)
            env.update(
                {
                    "TDQ_LOG": "0",
                    "TDQ_PROJECT_DIR": str(project),
                    "HOME": str(home),
                    "USERPROFILE": str(home),
                }
            )
            proc = subprocess.run(
                [
                    sys.executable,
                    "-X",
                    "utf8",
                    str(SCRIPTS_DIR / "tdq_timing.py"),
                    "status",
                    "--project",
                    str(project),
                    "--now",
                    "2026-11-25T00:00:05+00:00",
                    "--transcript-dir",
                    str(project / "missing-transcripts"),
                ],
                check=False,
                capture_output=True,
                env=env,
                timeout=20,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(proc.stderr, b"")

    def test_tdq_timing_has_no_hooks_imports_and_keeps_constants(self) -> None:
        src = (SCRIPTS_DIR / "tdq_timing.py").read_text(encoding="utf-8")
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertNotIn("hooks", alias.name)
            elif isinstance(node, ast.ImportFrom):
                self.assertNotIn("hooks", node.module or "")
            elif isinstance(node, ast.FunctionDef) and node.name in {
                "check_budget_status",
                "_load_budget_caps",
                "_extract_budget_caps",
                "_sum_telemetry_usage",
                "_row_tokens",
                "_row_cost_usd",
            }:
                span = (node.end_lineno or node.lineno) - node.lineno + 1
                self.assertLessEqual(span, 50, f"{node.name} is {span} lines")
        self.assertEqual(
            tdq_timing.TIMING_REL,
            os.path.join("docs", "tdq", "timing.jsonl"),
        )
        self.assertEqual(
            tdq_timing.TELEMETRY_REL,
            os.path.join("docs", "tdq", ".tdq-agent-telemetry.jsonl"),
        )


if __name__ == "__main__":
    unittest.main()
