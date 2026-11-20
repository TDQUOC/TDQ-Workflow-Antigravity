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


class TestPythonHooksSecurity(unittest.TestCase):
    """T3.1: QC scoped allowlist, shell bypasses, >= non-false-positive, SubagentStop & telemetry."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cwd = Path(self.tmp.name)
        (self.cwd / "docs" / "tdq").mkdir(parents=True, exist_ok=True)
        self.addCleanup(self.tmp.cleanup)

    def _run_hook(self, script_name: str, payload: dict, extra_env: dict | None = None) -> tuple[int, str, str]:
        env = _clean_env(TDQ_LOG="0", TDQ_PROJECT_DIR=str(self.cwd))
        if extra_env:
            env.update(extra_env)
        proc = subprocess.run(
            [sys.executable, str(ROOT / "hooks" / "scripts" / script_name)],
            input=json.dumps(payload),
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=20,
        )
        return proc.returncode, proc.stdout, proc.stderr

    def test_qc_allowlist_helper_and_edit_gate_scoping(self):
        sys.path.insert(0, str(ROOT / "hooks" / "scripts"))
        try:
            import _common
        finally:
            if sys.path and sys.path[0] == str(ROOT / "hooks" / "scripts"):
                sys.path.pop(0)

        self.assertTrue(_common.is_qc_report_target("docs/tdq/qc/2026-11-20-q1.md", str(self.cwd)))
        self.assertTrue(_common.is_qc_report_target("docs/tdq/qc/shards/shard1.md", str(self.cwd)))
        self.assertFalse(_common.is_qc_report_target("docs/tdq/qc/../../a.py", str(self.cwd)))
        self.assertFalse(_common.is_qc_report_target("docs/tdq/qc/evil.py", str(self.cwd)))
        self.assertFalse(_common.is_qc_report_target("scripts/tdq_config.py", str(self.cwd)))

        # Register subagent roles and run edit_gate CLI
        _common.register_subagent_role(str(self.cwd), "qc-1", "tdq-qc-tester")
        rc_ok, out_ok, err_ok = self._run_hook(
            "edit_gate.py",
            {
                "cwd": str(self.cwd),
                "conversationId": "qc-1",
                "tool_name": "write_to_file",
                "tool_input": {"file_path": "docs/tdq/qc/2026-11-20-q1.md"},
            },
            extra_env={"ANTIGRAVITY_PROJECT_DIR": str(self.cwd)},
        )
        self.assertEqual(rc_ok, 0, err_ok)
        if out_ok.strip():
            self.assertEqual(json.loads(out_ok).get("decision"), "allow", out_ok)

        rc_bad, out_bad, err_bad = self._run_hook(
            "edit_gate.py",
            {
                "cwd": str(self.cwd),
                "conversationId": "qc-1",
                "tool_name": "write_to_file",
                "tool_input": {"file_path": "docs/tdq/qc/../../a.py"},
            },
            extra_env={"ANTIGRAVITY_PROJECT_DIR": str(self.cwd)},
        )
        self.assertEqual(rc_bad, 0, err_bad)
        self.assertIn("READONLY", out_bad)

        _common.register_subagent_role(str(self.cwd), "exp-1", "tdq-explorer")
        rc_exp, out_exp, _ = self._run_hook(
            "edit_gate.py",
            {
                "cwd": str(self.cwd),
                "conversationId": "exp-1",
                "tool_name": "write_to_file",
                "tool_input": {"file_path": "docs/tdq/qc/2026-11-20-q1.md"},
            },
            extra_env={"ANTIGRAVITY_PROJECT_DIR": str(self.cwd)},
        )
        self.assertEqual(rc_exp, 0)
        self.assertIn("READONLY", out_exp)

    def test_bash_gate_shell_bypasses_and_ge_not_false_positive(self):
        sys.path.insert(0, str(ROOT / "hooks" / "scripts"))
        try:
            import bash_gate
            import _common
        finally:
            if sys.path and sys.path[0] == str(ROOT / "hooks" / "scripts"):
                sys.path.pop(0)

        self.assertFalse(bash_gate._is_shell_write('py -3 -c "assert x >= 1"'))
        self.assertFalse(bash_gate._is_shell_write('python3 -c "print(2 >= 1 and 1 <= 2)"'))
        self.assertTrue(bash_gate._is_shell_write("py -3 -c \"Path('a').write_text('x')\""))
        self.assertTrue(bash_gate._is_shell_write('node -e "fs.writeFileSync(\'a\', \'b\')"'))
        self.assertTrue(bash_gate._is_shell_write("git -C .tdq-worktrees/t1 commit -m done"))

        _common.register_subagent_role(str(self.cwd), "qc-bash", "tdq-qc-tester")
        rc_ge, out_ge, err_ge = self._run_hook(
            "bash_gate.py",
            {
                "cwd": str(self.cwd),
                "conversationId": "qc-bash",
                "tool_name": "run_command",
                "tool_input": {"command": 'py -3 -c "assert 5 >= 1"'},
            },
            extra_env={"ANTIGRAVITY_PROJECT_DIR": str(self.cwd)},
        )
        self.assertEqual(rc_ge, 0, err_ge)
        self.assertNotIn("READONLY", out_ge)

        rc_wr, out_wr, err_wr = self._run_hook(
            "bash_gate.py",
            {
                "cwd": str(self.cwd),
                "conversationId": "qc-bash",
                "tool_name": "run_command",
                "tool_input": {"command": "py -3 -c \"Path('x.py').write_text('bad')\""},
            },
            extra_env={"ANTIGRAVITY_PROJECT_DIR": str(self.cwd)},
        )
        self.assertEqual(rc_wr, 0, err_wr)
        self.assertIn("READONLY", out_wr)

    def test_subagent_stop_telemetry_blackboard_and_hooks_json(self):
        hooks_cfg = json.loads((ROOT / "hooks" / "hooks.json").read_text(encoding="utf-8"))
        self.assertIn("SubagentStop", hooks_cfg["hooks"])
        post_matchers = [e.get("matcher", "") for e in hooks_cfg["hooks"]["PostToolUse"]]
        self.assertTrue(any("invoke_subagent" in m and "Task" in m for m in post_matchers), post_matchers)

        # Init open request state so stop_gate is armed for leader, then verify subagentStop writes telemetry & blackboard
        state_file = self.cwd / "docs" / "tdq" / "state.json"
        state_file.write_text(
            json.dumps({
                "active_request": "2026-11-20-t31",
                "lane": "full",
                "phase": "implement",
                "spec_approved": True,
                "plan_approved": True,
                "plan_file": "docs/tdq/plan/2026-11-20-t31.md",
            }),
            encoding="utf-8",
        )
        (self.cwd / "docs" / "tdq" / "plan").mkdir(parents=True, exist_ok=True)
        (self.cwd / "docs" / "tdq" / "plan" / "2026-11-20-t31.md").write_text(
            "- [>] **T3.1** Demo — Test: `pytest`\n", encoding="utf-8"
        )

        failed_handoff = json.dumps({
            "task_id": "T3.1",
            "status": "failed",
            "files": ["scripts/demo.py"],
            "test_result": "pytest -> 1 failed",
            "branch": "team/t3.1",
            "merge_ready": False,
            "tick_ready": False,
            "notes": "scripts/demo.py:10 — fn — AssertionError",
            "role": "tdq-implementer",
            "model": "gemini-4-hydrogen-high",
            "effort": "high",
            "elapsed_s": 12.5,
        })
        rc, out, err = self._run_hook(
            "subagent_stop.py",
            {
                "cwd": str(self.cwd),
                "session_id": "sub-t31",
                "agent_type": "tdq-implementer",
                "last_assistant_message": failed_handoff,
            },
        )
        self.assertEqual(rc, 0, err + out)
        tel_path = self.cwd / "docs" / "tdq" / ".tdq-agent-telemetry.jsonl"
        self.assertTrue(tel_path.is_file(), "telemetry jsonl not created")
        rows = [json.loads(line) for line in tel_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        self.assertEqual(rows[-1]["role"], "tdq-implementer")
        self.assertEqual(rows[-1]["task_id"], "T3.1")
        self.assertEqual(rows[-1]["status"], "failed")

        bb_path = self.cwd / ".tdq-runtime" / "blackboard" / "2026-11-20-t31.json"
        self.assertTrue(bb_path.is_file(), "blackboard json not updated on failed handoff")
        bb = json.loads(bb_path.read_text(encoding="utf-8"))
        self.assertEqual(bb["entries"][-1]["task_id"], "T3.1")

        # stop_gate must NOT block a subagent with leader TDQ:UNFINISHED / TDQ:TICK
        rc_sg, out_sg, err_sg = self._run_hook(
            "stop_gate.py",
            {
                "cwd": str(self.cwd),
                "conversationId": "sub-t31-agy",
                "agent_type": "tdq-implementer",
                "hookEventName": "Stop",
            },
            extra_env={"ANTIGRAVITY_PROJECT_DIR": str(self.cwd)},
        )
        self.assertEqual(rc_sg, 0, err_sg + out_sg)
        self.assertNotIn("TDQ:UNFINISHED", out_sg)
        self.assertNotIn("TDQ:TICK", out_sg)


if __name__ == "__main__":
    unittest.main()
