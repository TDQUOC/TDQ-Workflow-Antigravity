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

import doc_lint  # noqa: E402
import tdq_config  # noqa: E402
import tdq_team  # noqa: E402
import tdq_timing  # noqa: E402
import token_audit  # noqa: E402


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


def _write_text(path: Path, content: str) -> Path:
    """Write UTF-8 text to path creating parent directories."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _run_py(script_rel: str, cwd: Path, *args: str, stdin_data: str | None = None,
            extra_env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    """Run a repository Python script with isolated project env and timeout."""
    env = _clean_env(TDQ_LOG="0", TDQ_PROJECT_DIR=str(cwd))
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        [sys.executable, str(ROOT / script_rel), *args],
        cwd=str(cwd),
        input=stdin_data,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=20,
    )


def _register_role(cwd: Path, conv_id: str, role: str) -> None:
    """Register a subagent conversation role inside temporary project sessions.json."""
    hooks_scripts = str(ROOT / "hooks" / "scripts")
    sys.path.insert(0, hooks_scripts)
    try:
        import _common
        _common.register_subagent_role(str(cwd), conv_id, role)
    finally:
        if sys.path and sys.path[0] == hooks_scripts:
            sys.path.pop(0)


class TestHandoffAndBlackboard(unittest.TestCase):
    """Unified handoff schema, multi-lang packet extraction, and blackboard escalation."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.cwd = Path(self._tmp.name)
        self.slug = "2026-11-20-1230-handoff-mvp"
        self.addCleanup(self._tmp.cleanup)

    def test_unified_handoff_schema_contract(self) -> None:
        schema_path = ROOT / "skills" / "tdq-conventions" / "references" / "handoff-schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        self.assertEqual(schema["title"], "TDQ_HANDOFF_PAYLOAD")
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(
            schema["required"],
            ["task_id", "status", "files", "test_result", "branch", "merge_ready", "tick_ready", "notes"],
        )
        props = schema["properties"]
        self.assertEqual(props["status"]["enum"], ["done", "completed", "failed", "blocked"])
        self.assertEqual(props["test_verdict"]["enum"], ["pass", "fail"])
        self.assertEqual(props["notes"]["maxLength"], 1500)

    def test_packet_multilang_ts_rs_ps1_and_minispec(self) -> None:
        _write_text(
            self.cwd / "src" / "widget.ts",
            "\n".join([
                "export function beforeHelper() { return 0; }",
                "export async function computeWidget(name: string): Promise<number> {",
                "  return name.length * 2;",
                "}",
            ]),
        )
        _write_text(
            self.cwd / "src" / "lib.rs",
            "pub fn handle_pre_tool(raw: &str) -> bool {\n    !raw.is_empty()\n}\n",
        )
        _write_text(
            self.cwd / "scripts" / "check.ps1",
            "function Invoke-Check {\n    param($Target)\n    return $Target\n}\n",
        )
        plan_path = _write_text(
            self.cwd / "docs" / "tdq" / "plan" / f"{self.slug}.md",
            "\n".join([
                "# PLAN — Multi-lang MVP",
                "",
                "## P1 — Core",
                "- [ ] **T1.1** (e10m) Update `computeWidget` and `handle_pre_tool` — Test: `pytest -q`",
                "  - Req: `§2#2` · Ngoài phạm vi: `GIỮ NGUYÊN` `beforeHelper`",
                "  - Chạm: `src/widget.ts`, `src/lib.rs`, `scripts/check.ps1`",
                "  - Tiêu chí chấp nhận (EARS): KHI truyền tên hợp lệ, HỆ THỐNG PHẢI trả về số > 0.",
                "  - Logic cốt lõi: Nhân đôi độ dài tên và kiểm tra chuỗi không rỗng.",
                "  - Ca góc hiểm & Assert: Chuỗi rỗng trả false · `assert computeWidget('ab') == 4`",
            ]),
        )
        proc = _run_py("scripts/tdq_team.py", self.cwd, "packet", "T1.1", "--plan", str(plan_path), "--format", "json")
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        payload = json.loads(proc.stdout)
        mini = payload["mini_spec"]
        self.assertIn("§2#2", mini["req"])
        self.assertIn("beforeHelper", mini["giu_nguyen"])
        self.assertIn("KHI truyền", mini["ears"])
        self.assertIn("Nhân đôi", mini["logic"])
        by_path = {entry["path"]: entry for entry in payload["symbol_spans"]}
        self.assertEqual(by_path["src/widget.ts"]["symbol"], "computeWidget")
        self.assertEqual(by_path["src/lib.rs"]["symbol"], "handle_pre_tool")
        self.assertEqual(by_path["scripts/check.ps1"]["mode"], "read-exact")

    def test_validate_handoff_pass_and_fail(self) -> None:
        valid_payload = {
            "task_id": "T5.2",
            "status": "done",
            "files": ["tests/test_agent_upgrade_mvp.py"],
            "test_result": "pytest -> 10 passed",
            "branch": "tdq/demo/t5.2",
            "merge_ready": True,
            "tick_ready": True,
            "notes": "tests/test_agent_upgrade_mvp.py:1 — TestHandoffAndBlackboard — verified",
        }
        ok, errs = tdq_team.validate_handoff_payload(valid_payload, project=str(self.cwd))
        self.assertTrue(ok, errs)
        cli_ok = _run_py("scripts/tdq_team.py", self.cwd, "validate-handoff", "--text", json.dumps(valid_payload), "--json")
        self.assertEqual(cli_ok.returncode, 0, cli_ok.stderr)
        self.assertTrue(json.loads(cli_ok.stdout)["ok"])

        for bad_case in (
            {"task_id": "T5.2"},
            dict(valid_payload, status="invalid_state"),
            dict(valid_payload, unknown_prop="nope"),
            dict(valid_payload, notes="n" * 1501),
        ):
            bad_ok, bad_errs = tdq_team.validate_handoff_payload(bad_case, project=str(self.cwd))
            self.assertFalse(bad_ok)
            self.assertTrue(bad_errs)
        cli_bad = _run_py("scripts/tdq_team.py", self.cwd, "validate-handoff", "--text", '{"task_id":"T5.2"}')
        self.assertEqual(cli_bad.returncode, 1)

    def test_blackboard_record_and_escalation_at_two_retries(self) -> None:
        tdq_team.blackboard_record(
            str(self.cwd), "T5.2", "failed", "first syntax error",
            slug=self.slug, role="tdq-implementer", error="SyntaxError L10",
        )
        self.assertIsNone(tdq_team.suggest_escalation(str(self.cwd), self.slug, "T5.2"))

        tdq_team.blackboard_record(
            str(self.cwd), "T5.2", "blocked", "second type error",
            slug=self.slug, role="tdq-implementer", error="TypeError L22",
        )
        esc = tdq_team.suggest_escalation(str(self.cwd), self.slug, "T5.2")
        self.assertIsNotNone(esc)
        self.assertEqual(esc["failures"], 2)
        self.assertEqual(esc["threshold"], 2)
        self.assertEqual(esc["recommended_agent"], "tdq-build-resolver")
        self.assertGreaterEqual(esc["recommended_tier"], 2)
        self.assertTrue(esc["recommended_model"])

        cli_read = _run_py(
            "scripts/tdq_team.py", self.cwd, "blackboard", "read", "--slug", self.slug, "--task", "T5.2", "--json"
        )
        self.assertEqual(cli_read.returncode, 0, cli_read.stderr)
        self.assertEqual(len(json.loads(cli_read.stdout)["entries"]), 2)


class TestRoleTelemetry(unittest.TestCase):
    """Role telemetry aggregation across tdq_timing/token_audit and tdq-config parity."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.cwd = Path(self._tmp.name)
        (self.cwd / "docs" / "tdq").mkdir(parents=True, exist_ok=True)
        self.addCleanup(self._tmp.cleanup)

    def test_role_summary_and_token_audit_aggregate_telemetry_jsonl(self) -> None:
        rows = [
            {"role": "tdq-explorer", "model": "gemini-3.8-flash-high", "effort": "high",
             "status": "done", "elapsed_s": 3.5, "task_id": "E1", "attempt": 1},
            {"role": "tdq-implementer", "model": "gemini-4-hydrogen-high", "effort": "high",
             "status": "failed", "first_pass": False, "elapsed_s": 10.0, "task_id": "T1.1", "attempt": 1},
            "{corrupt line",
            {"role": "tdq-implementer", "model": "gemini-4-neon-high", "effort": "high",
             "status": "done", "elapsed_s": 14.0, "task_id": "T1.1", "attempt": 2},
            {"role": "tdq-qc-tester", "model": "gemini-4-neon-high", "effort": "high",
             "status": "done", "elapsed_s": 8.5, "task_id": "Q1", "attempt": 1},
        ]
        tel_path = self.cwd / "docs" / "tdq" / ".tdq-agent-telemetry.jsonl"
        tel_path.write_text(
            "\n".join(item if isinstance(item, str) else json.dumps(item) for item in rows) + "\n",
            encoding="utf-8",
        )
        with mock.patch.dict(os.environ, _clean_env(TDQ_LOG="0", TDQ_AUDIT_LOG="0"), clear=True):
            timing_rows = tdq_timing.role_summary(self.cwd)
            audit_rows = token_audit.role_telemetry_summary(self.cwd)
        self.assertEqual(timing_rows, audit_rows)
        by_role = {row["role"]: row for row in timing_rows}
        self.assertEqual(set(by_role), {"tdq-explorer", "tdq-implementer", "tdq-qc-tester"})
        impl = by_role["tdq-implementer"]
        self.assertEqual(impl["runs"], 2)
        self.assertEqual(impl["first_pass_count"], 0)
        self.assertEqual(impl["retries"], 1)
        self.assertAlmostEqual(impl["avg_elapsed_s"], 12.0, places=2)
        self.assertEqual(impl["models"], ["gemini-4-hydrogen-high", "gemini-4-neon-high"])

        cli_roles = _run_py("scripts/tdq_timing.py", self.cwd, "roles", "--json", "--project", str(self.cwd))
        self.assertEqual(cli_roles.returncode, 0, cli_roles.stderr)
        self.assertEqual(json.loads(cli_roles.stdout)["role_telemetry"], timing_rows)

    def test_agy_tdq_config_byte_for_byte_parity_with_root(self) -> None:
        root_cfg = (ROOT / "tdq-config.json").read_bytes()
        agy_cfg = (ROOT / "plugins" / "tdq-workflow-agy" / "tdq-config.json").read_bytes()
        self.assertEqual(root_cfg, agy_cfg)
        self.assertEqual(json.loads(root_cfg.decode("utf-8")), tdq_config.DEFAULT_CONFIG)


class TestAgyBundleParity(unittest.TestCase):
    """AGY plugin manifest, valid hook events, and Plan Model & Effort linter checks."""

    def test_plugin_json_mentions_eight_domain_subagents(self) -> None:
        pjson = json.loads((ROOT / "plugins" / "tdq-workflow-agy" / "plugin.json").read_text(encoding="utf-8"))
        self.assertIn("8 domain subagents", pjson["description"])

    def test_hooks_json_events_and_post_tool_observe_matcher(self) -> None:
        hooks = json.loads((ROOT / "plugins" / "tdq-workflow-agy" / "hooks.json").read_text(encoding="utf-8"))
        valid_events = {"SessionStart", "PreToolUse", "PostToolUse", "PreInvocation", "PostInvocation", "Stop"}
        seen_events = set()
        for group in hooks.values():
            for key in group:
                if key != "enabled":
                    seen_events.add(key)
        self.assertLessEqual(seen_events, valid_events)
        self.assertEqual(seen_events, valid_events)
        post_entries = hooks["tdq-post-tool-observe"]["PostToolUse"]
        self.assertEqual(len(post_entries), 1)
        self.assertIn("invoke_subagent|swarm|define_subagent", post_entries[0]["matcher"])

    def test_plan_model_effort_section_lint(self) -> None:
        self.assertTrue(doc_lint._plan_yeu_cau_model_effort("2026-11-20-1230-demo.md"))
        self.assertFalse(doc_lint._plan_yeu_cau_model_effort("2026-11-20-0015-old.md"))
        with tempfile.TemporaryDirectory() as tmp:
            plan_dir = Path(tmp) / "docs" / "tdq" / "plan"
            p_missing = _write_text(plan_dir / "2026-11-20-1230-missing.md", "# PLAN\n\n## P1\n")
            out_missing: list[str] = []
            doc_lint._check_model_effort_section(doc_lint.Doc(str(p_missing)), out_missing)
            self.assertEqual(len(out_missing), 1)
            self.assertIn("missing required '## Phân bổ Model & Effort'", out_missing[0])

            p_partial = _write_text(
                plan_dir / "2026-11-20-1230-partial.md",
                "# PLAN\n\n## Phân bổ Model & Effort\n- implement: gemini-4-hydrogen-high\n",
            )
            out_partial: list[str] = []
            doc_lint._check_model_effort_section(doc_lint.Doc(str(p_partial)), out_partial)
            self.assertEqual(len(out_partial), 1)
            self.assertIn("qc", out_partial[0])

            p_ok = _write_text(
                plan_dir / "2026-11-20-1230-ok.md",
                "\n".join([
                    "# PLAN",
                    "",
                    "## Phân bổ Model & Effort",
                    "| Phase | Role | Model + Effort |",
                    "|---|---|---|",
                    "| implement | tdq-implementer | gemini-4-hydrogen-high |",
                    "| qc | tdq-qc-tester | gemini-4-neon-high |",
                    "| report | main | gemini-3.8-flash-medium |",
                ]),
            )
            out_ok: list[str] = []
            doc_lint._check_model_effort_section(doc_lint.Doc(str(p_ok)), out_ok)
            self.assertEqual(out_ok, [])


class TestSmokeAndRuntime(unittest.TestCase):
    """Real subprocess smoke checks against tdq-dispatch.exe and TDQ_LOG toggles."""

    DISPATCH_EXE = ROOT / "plugins" / "tdq-workflow-agy" / "bin" / "tdq-dispatch.exe"

    def setUp(self) -> None:
        if os.name == "nt":
            self.assertTrue(self.DISPATCH_EXE.is_file(), f"Missing Rust binary: {self.DISPATCH_EXE}")
        elif not self.DISPATCH_EXE.is_file():
            self.skipTest("tdq-dispatch.exe missing on non-Windows OS")
        if os.name != "nt":
            self.skipTest("tdq-dispatch.exe Windows binary cannot run directly on non-Windows OS")
        self._tmp = tempfile.TemporaryDirectory()
        self.cwd = Path(self._tmp.name)
        (self.cwd / "docs" / "tdq").mkdir(parents=True, exist_ok=True)
        self.addCleanup(self._tmp.cleanup)

    def _run_dispatch(self, event: str, payload: dict, extra_env: dict[str, str] | None = None
                      ) -> subprocess.CompletedProcess[str]:
        env = _clean_env(
            TDQ_LOG="0",
            TDQ_PROJECT_DIR=str(self.cwd),
            ANTIGRAVITY_PROJECT_DIR=str(self.cwd),
        )
        if extra_env:
            env.update(extra_env)
        kwargs: dict[str, object] = {}
        if os.name == "nt":
            kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
        return subprocess.run(
            [str(self.DISPATCH_EXE), "--event", event],
            cwd=str(self.cwd),
            input=json.dumps(payload),
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=20,
            **kwargs,
        )

    def test_qc_tester_and_explorer_edit_gates_via_tdq_dispatch(self) -> None:
        _register_role(self.cwd, "qc-smoke", "tdq-qc-tester")
        _register_role(self.cwd, "exp-smoke", "tdq-explorer")

        for tool_name in ("write_to_file", "write_file"):
            res_ok = self._run_dispatch(
                "PreToolUse",
                {
                    "cwd": str(self.cwd),
                    "conversationId": "qc-smoke",
                    "tool_name": tool_name,
                    "tool_input": {"file_path": "docs/tdq/qc/q1.md"},
                },
            )
            self.assertEqual(res_ok.returncode, 0, res_ok.stderr)
            self.assertEqual(json.loads(res_ok.stdout)["decision"], "allow", res_ok.stdout)

        res_trav = self._run_dispatch(
            "PreToolUse",
            {
                "cwd": str(self.cwd),
                "conversationId": "qc-smoke",
                "tool_name": "write_to_file",
                "tool_input": {"file_path": "docs/tdq/qc/../../evil.py"},
            },
        )
        self.assertEqual(res_trav.returncode, 0, res_trav.stderr)
        trav_json = json.loads(res_trav.stdout)
        self.assertEqual(trav_json["decision"], "deny")
        self.assertIn("READONLY", trav_json["reason"])

        res_exp = self._run_dispatch(
            "PreToolUse",
            {
                "cwd": str(self.cwd),
                "conversationId": "exp-smoke",
                "tool_name": "write_file",
                "tool_input": {"file_path": "docs/tdq/qc/q1.md"},
            },
        )
        self.assertEqual(res_exp.returncode, 0, res_exp.stderr)
        exp_json = json.loads(res_exp.stdout)
        self.assertEqual(exp_json["decision"], "deny")
        self.assertIn("READONLY", exp_json["reason"])

    def test_qc_tester_run_command_ge_and_mutation_via_tdq_dispatch(self) -> None:
        _register_role(self.cwd, "qc-cmd", "tdq-qc-tester")

        res_ge = self._run_dispatch(
            "PreToolUse",
            {
                "cwd": str(self.cwd),
                "conversationId": "qc-cmd",
                "tool_name": "run_command",
                "tool_input": {"command": 'py -3 -c "assert 5 >= 1"'},
            },
        )
        self.assertEqual(res_ge.returncode, 0, res_ge.stderr)
        self.assertNotIn("READONLY", res_ge.stdout)
        self.assertEqual(json.loads(res_ge.stdout)["decision"], "allow")

        res_wr = self._run_dispatch(
            "PreToolUse",
            {
                "cwd": str(self.cwd),
                "conversationId": "qc-cmd",
                "tool_name": "run_command",
                "tool_input": {"command": "py -3 -c \"Path('x.py').write_text('bad')\""},
            },
        )
        self.assertEqual(res_wr.returncode, 0, res_wr.stderr)
        self.assertIn("READONLY", res_wr.stdout)
        self.assertEqual(json.loads(res_wr.stdout)["decision"], "deny")

    def test_tdq_log_toggle_across_dispatch_config_and_subagent_stop(self) -> None:
        _register_role(self.cwd, "qc-log", "tdq-qc-tester")
        payload = {
            "cwd": str(self.cwd),
            "conversationId": "qc-log",
            "tool_name": "write_to_file",
            "tool_input": {"file_path": "docs/tdq/qc/q1.md"},
        }
        disp_on = self._run_dispatch("PreToolUse", payload, extra_env={"TDQ_LOG": "1"})
        disp_off = self._run_dispatch("PreToolUse", payload, extra_env={"TDQ_LOG": "0"})
        self.assertEqual(disp_on.returncode, 0)
        self.assertIn("tdq-dispatch:", disp_on.stderr)
        self.assertRegex(disp_on.stderr, r"\[\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")
        self.assertEqual(disp_off.returncode, 0)
        self.assertEqual(disp_off.stderr.strip(), "")

        cfg_on = _run_py("scripts/tdq_config.py", self.cwd, "show", "--json", "--cwd", str(self.cwd),
                         extra_env={"TDQ_LOG": "1"})
        cfg_off = _run_py("scripts/tdq_config.py", self.cwd, "show", "--json", "--cwd", str(self.cwd),
                          extra_env={"TDQ_LOG": "0"})
        self.assertRegex(cfg_on.stderr, r"\[\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")
        self.assertEqual(cfg_off.stderr.strip(), "")

        stop_payload = json.dumps({
            "cwd": str(self.cwd),
            "session_id": "sub-log-1",
            "agent_type": "tdq-implementer",
            "last_assistant_message": json.dumps({
                "task_id": "T5.2",
                "status": "failed",
                "files": ["scripts/tdq_config.py"],
                "test_result": "pytest -> 1 failed",
                "branch": "team/t5.2",
                "merge_ready": False,
                "tick_ready": False,
                "notes": "scripts/tdq_config.py:1 — load_config — fail",
            }),
        })
        stop_on = _run_py("hooks/scripts/subagent_stop.py", self.cwd, stdin_data=stop_payload,
                          extra_env={"TDQ_LOG": "1"})
        stop_off = _run_py("hooks/scripts/subagent_stop.py", self.cwd, stdin_data=stop_payload,
                           extra_env={"TDQ_LOG": "0"})
        self.assertEqual(stop_on.returncode, 0, stop_on.stderr)
        self.assertRegex(stop_on.stderr, r"\[\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")
        self.assertEqual(stop_off.returncode, 0, stop_off.stderr)
        self.assertEqual(stop_off.stderr.strip(), "")

    def test_qc11_adversarial_fixes_verified_end_to_end(self) -> None:
        # 1. validate-handoff rejects invalid test_verdict and missing --file cleanly (no Traceback)
        bad_verdict = json.dumps({
            "task_id": "T1.1", "status": "done", "files": ["a.py"], "test_result": "ok",
            "test_verdict": "bogus", "branch": "b", "merge_ready": True, "tick_ready": True,
            "notes": "tests/a.py:1 — fn — ok",
        })
        vh_bad = _run_py("scripts/tdq_team.py", self.cwd, "validate-handoff", "--text", bad_verdict)
        self.assertEqual(vh_bad.returncode, 1)
        self.assertIn("test_verdict", vh_bad.stderr + vh_bad.stdout)

        vh_missing = _run_py("scripts/tdq_team.py", self.cwd, "validate-handoff", "--file", "no_such_handoff.json")
        self.assertNotEqual(vh_missing.returncode, 0)
        self.assertNotIn("Traceback", vh_missing.stderr)

        # 2. Root subagent_stop: PostToolUse registers child role only (ND-6), SubagentStop records telemetry
        (self.cwd / "docs" / "tdq").mkdir(parents=True, exist_ok=True)
        post_ev = json.dumps({
            "cwd": str(self.cwd),
            "conversationId": "parent-99",
            "tool_name": "invoke_subagent",
            "tool_input": {"TypeName": "tdq-explorer", "Role": "tdq-explorer"},
            "response": {"result": {"conversationId": "child-exp-99"}},
        })
        ps = _run_py("hooks/scripts/subagent_stop.py", self.cwd, "--event", "PostToolUse", stdin_data=post_ev)
        self.assertEqual(ps.returncode, 0, ps.stderr)
        sess = json.loads((self.cwd / "docs" / "tdq" / ".tdq-runtime" / "sessions.json").read_text(encoding="utf-8"))
        self.assertEqual(sess["child-exp-99"]["role"], "tdq-explorer")
        tel_path = self.cwd / "docs" / "tdq" / ".tdq-agent-telemetry.jsonl"
        self.assertFalse(tel_path.exists())
        stop_ev = json.dumps({"cwd": str(self.cwd), "conversationId": "child-exp-99", "last_assistant_message": "done"})
        ss = _run_py("hooks/scripts/subagent_stop.py", self.cwd, "--event", "SubagentStop", stdin_data=stop_ev)
        self.assertEqual(ss.returncode, 0, ss.stderr)
        tel = tel_path.read_text(encoding="utf-8").splitlines()
        self.assertEqual(json.loads(tel[-1])["session"], "child-exp-99")

        # 3. Quote-aware shell parser in BOTH Python and compiled Rust tdq-dispatch.exe
        sys.path.insert(0, str(ROOT / "hooks" / "scripts"))
        try:
            import bash_gate
        finally:
            if sys.path and sys.path[0] == str(ROOT / "hooks" / "scripts"):
                sys.path.pop(0)
        _register_role(self.cwd, "qc-adv", "tdq-qc-tester")

        allow_cmds = (
            'py -3 -c "assert 5 > 1"',
            'py -3 -c "print(\'a > b\')"',
            'bash -c "python3 -c \'assert 5 > 1\'"',
        )
        for cmd in allow_cmds:
            with self.subTest(allow=cmd):
                self.assertFalse(bash_gate._is_shell_write(cmd))
                r = self._run_dispatch("PreToolUse", {
                    "cwd": str(self.cwd), "conversationId": "qc-adv",
                    "tool_name": "run_command", "tool_input": {"command": cmd},
                })
                self.assertEqual(r.returncode, 0, r.stderr)
                self.assertNotIn("READONLY", r.stdout)

        deny_cmds = (
            "node -e \"const fs = require('fs'); fs.writeFileSync('evil.py','x')\"",
            "py -3 -c \"from pathlib import Path; Path('evil.js').write_text('x')\"",
            "python3 -c \"import shutil; shutil.rmtree('src_dir')\"",
            'bash -c "echo hi > evil.py"',
        )
        for cmd in deny_cmds:
            with self.subTest(deny=cmd):
                self.assertTrue(bash_gate._is_shell_write(cmd))
                r = self._run_dispatch("PreToolUse", {
                    "cwd": str(self.cwd), "conversationId": "qc-adv",
                    "tool_name": "run_command", "tool_input": {"command": cmd},
                })
                self.assertEqual(r.returncode, 0, r.stderr)
                self.assertEqual(json.loads(r.stdout)["decision"], "deny")
                self.assertIn("READONLY", r.stdout)

        # 4. doc_lint checks all 3 phases (implement, qc, report) on post-cutoff full plans
        sys.path.insert(0, str(ROOT / "scripts"))
        try:
            import doc_lint
        finally:
            if sys.path and sys.path[0] == str(ROOT / "scripts"):
                sys.path.pop(0)
        p_no_rep = _write_text(
            self.cwd / "docs" / "tdq" / "plan" / "2026-11-20-1230-norep.md",
            "# PLAN\n\n## Phân bổ Model & Effort\n| implement | a | b |\n| qc | c | d |\n",
        )
        out_rep: list[str] = []
        doc_lint._check_model_effort_section(doc_lint.Doc(str(p_no_rep)), out_rep)
        self.assertEqual(len(out_rep), 1)
        self.assertIn("report", out_rep[0])


if __name__ == "__main__":
    unittest.main()
