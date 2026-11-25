"""Unit tests for scripts/mcp_policy.py."""

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
from datetime import datetime
from pathlib import Path
from typing import Any
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

ISO_LOG_RE = re.compile(r"^\[([^\]]+)\]\s+mcp_policy:\s+")


def _load_module() -> Any:
    return importlib.import_module("mcp_policy")


def _run_cli(args: list[str], tdq_log: str = "1") -> subprocess.CompletedProcess[bytes]:
    env = dict(os.environ)
    env["TDQ_LOG"] = tdq_log
    return subprocess.run(
        [sys.executable, "-X", "utf8", str(SCRIPTS_DIR / "mcp_policy.py"), *args],
        check=False,
        capture_output=True,
        env=env,
        timeout=15,
    )


class TestMcpPolicyContracts(unittest.TestCase):
    def test_isolation_no_hooks_or_tdq_state_imports(self) -> None:
        src = (SCRIPTS_DIR / "mcp_policy.py").read_text(encoding="utf-8")
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertNotIn("hooks", alias.name)
                    self.assertNotEqual(alias.name, "_common")
                    self.assertNotIn("tdq_state", alias.name)
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                self.assertNotIn("hooks", mod)
                self.assertNotEqual(mod, "_common")
                self.assertNotIn("tdq_state", mod)

    def test_function_line_lengths_stay_under_cap(self) -> None:
        src = (SCRIPTS_DIR / "mcp_policy.py").read_text(encoding="utf-8")
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self.assertIsNotNone(node.end_lineno)
                span = (node.end_lineno or node.lineno) - node.lineno + 1
                self.assertLessEqual(span, 50, f"{node.name} is {span} lines (> 50)")

    def test_canonical_schema_hash_is_deterministic(self) -> None:
        mcp_policy = _load_module()
        schema_a = {"b": [1, 2], "a": {"z": True, "y": "ok"}}
        schema_b = {"a": {"y": "ok", "z": True}, "b": [1, 2]}
        self.assertEqual(
            mcp_policy.canonical_schema_hash(schema_a),
            mcp_policy.canonical_schema_hash(schema_b),
        )
        self.assertEqual(len(mcp_policy.canonical_schema_hash(schema_a)), 64)
        self.assertEqual(
            mcp_policy.canonical_schema_hash(None),
            mcp_policy.canonical_schema_hash({}),
        )

    def test_classify_tool_tier_priorities_and_prefixes(self) -> None:
        mcp_policy = _load_module()
        with tempfile.TemporaryDirectory() as tmp:
            policy, corrupt = mcp_policy.load_policy(tmp)
        self.assertFalse(corrupt)
        cases = [
            ("unknown-srv", "get_item", "read"),
            ("unknown-srv", "type_hierarchy", "read"),
            ("chrome-devtools", "type_text", "write"),
            ("chrome-devtools", "fill_form", "write"),
            ("github", "mcp__github__create_issue", "write"),
            ("github", "mcp__github__delete_repo", "destructive"),
            ("ops", "deploy_release", "destructive"),
            ("ops", "reset", "destructive"),
            ("unknown-srv", "mystery_mutation", "write"),
            ("unknown-srv", "drop_database", "destructive"),
            ("tdq-lsp", "custom_lookup", "read"),
            ("lsp", "lsp.find_symbol", "read"),
        ]
        for srv, tool, expected in cases:
            with self.subTest(server=srv, tool=tool):
                self.assertEqual(mcp_policy.classify_tool_tier(srv, tool, policy), expected)


class TestMcpPolicyEvaluationAndCli(unittest.TestCase):
    def test_balanced_allows_read_and_tdq_lsp_fast_path(self) -> None:
        mcp_policy = _load_module()
        with tempfile.TemporaryDirectory() as tmp:
            read_res = mcp_policy.evaluate_tool_call(tmp, "external-docs", "search_items")
            self.assertEqual(read_res["decision"], "allow")
            self.assertIsNone(read_res["code"])
            self.assertEqual(read_res["tier"], "read")

            lsp_read = mcp_policy.evaluate_tool_call(tmp, "tdq-lsp", "start_lsp")
            self.assertEqual(lsp_read["decision"], "allow")
            self.assertIsNone(lsp_read["code"])

            lsp_edit = mcp_policy.evaluate_tool_call(tmp, "tdq-workflow-agy_lsp", "apply_edit")
            self.assertEqual(lsp_edit["decision"], "allow")
            self.assertIsNone(lsp_edit["code"])
            self.assertEqual(lsp_edit["reason"], "balanced_read_or_trusted")

    def test_unknown_write_and_destructive_denied_with_hint(self) -> None:
        mcp_policy = _load_module()
        with tempfile.TemporaryDirectory() as tmp:
            write_res = mcp_policy.evaluate_tool_call(tmp, "github", "create_issue")
            self.assertEqual(write_res["decision"], "deny")
            self.assertEqual(write_res["code"], "READONLY")
            self.assertEqual(write_res["tier"], "write")
            self.assertIn("approve", write_res["hint"])

            destr_res = mcp_policy.evaluate_tool_call(tmp, "db", "delete_record")
            self.assertEqual(destr_res["decision"], "deny")
            self.assertEqual(destr_res["code"], "READONLY")
            self.assertEqual(destr_res["tier"], "destructive")
            self.assertIn("approve", destr_res["hint"])

    def test_approve_cli_and_schema_mutation_quarantine(self) -> None:
        mcp_policy = _load_module()
        schema_v1 = {"type": "object", "v": 1}
        schema_v2 = {"type": "object", "v": 2}
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            before = mcp_policy.evaluate_tool_call(cwd, "github", "create_issue", schema_v1)
            self.assertEqual(before["decision"], "deny")

            proc = _run_cli(
                [
                    "approve",
                    "github",
                    "create_issue",
                    "--cwd",
                    str(cwd),
                    "--schema-json",
                    json.dumps(schema_v1),
                    "--json",
                ]
            )
            self.assertEqual(proc.returncode, 0, proc.stderr.decode("utf-8", errors="replace"))
            policy_file = cwd / "docs" / "tdq" / "mcp-policy.json"
            self.assertTrue(policy_file.is_file())
            self.assertTrue(Path(f"{policy_file}.lock").exists())

            allowed = mcp_policy.evaluate_tool_call(cwd, "github", "create_issue", schema_v1)
            self.assertEqual(allowed["decision"], "allow")
            self.assertIsNone(allowed["code"])
            self.assertEqual(allowed["reason"], "approved_baseline_match")

            mutated = mcp_policy.evaluate_tool_call(cwd, "github", "create_issue", schema_v2)
            self.assertEqual(mutated["decision"], "deny")
            self.assertEqual(mutated["code"], "READONLY")
            self.assertEqual(mutated["sha256"], mcp_policy.canonical_schema_hash(schema_v2))

    def test_approve_empty_server_placeholder_and_reset_cli(self) -> None:
        mcp_policy = _load_module()
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            denied = mcp_policy.evaluate_tool_call(cwd, "", "write_note")
            self.assertEqual(denied["decision"], "deny")
            self.assertIn("approve _ write_note", denied["hint"])

            proc_app = _run_cli(["approve", "_", "write_note", "--cwd", str(cwd), "--json"])
            self.assertEqual(proc_app.returncode, 0)
            self.assertEqual(mcp_policy.evaluate_tool_call(cwd, "", "write_note")["decision"], "allow")

            proc_one = _run_cli(
                ["reset", "--cwd", str(cwd), "--server", "_", "--tool", "write_note", "--json"]
            )
            self.assertEqual(proc_one.returncode, 0)
            self.assertEqual(mcp_policy.evaluate_tool_call(cwd, "", "write_note")["decision"], "deny")

            mcp_policy.approve_tool(cwd, "github", "create_issue")
            mcp_policy.approve_tool(cwd, "db", "delete_record")
            proc_all = _run_cli(["reset", "--cwd", str(cwd), "--json"])
            self.assertEqual(proc_all.returncode, 0)
            cleared = json.loads(proc_all.stdout.decode("utf-8"))
            self.assertEqual(cleared["count"], 2)

    def test_corrupt_policy_denies_write_allows_read_and_logs(self) -> None:
        mcp_policy = _load_module()
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            policy_path = cwd / "docs" / "tdq" / "mcp-policy.json"
            policy_path.parent.mkdir(parents=True, exist_ok=True)
            policy_path.write_text("{not-valid-json", encoding="utf-8")

            buf = io.StringIO()
            with (
                mock.patch.dict(os.environ, {"TDQ_LOG": "1"}),
                contextlib.redirect_stderr(buf),
            ):
                write_res = mcp_policy.evaluate_tool_call(cwd, "github", "create_issue")
                read_res = mcp_policy.evaluate_tool_call(cwd, "github", "list_issues")

            self.assertEqual(write_res["decision"], "deny")
            self.assertEqual(write_res["code"], "READONLY")
            self.assertEqual(read_res["decision"], "allow")
            self.assertIsNone(read_res["code"])
            stderr_lines = buf.getvalue().strip().splitlines()
            self.assertTrue(stderr_lines)
            self.assertIsNotNone(ISO_LOG_RE.match(stderr_lines[0]))

    def test_kill_switch_and_strict_mode_config(self) -> None:
        mcp_policy = _load_module()
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            cfg_path = cwd / "docs" / "tdq" / "config.json"
            cfg_path.parent.mkdir(parents=True, exist_ok=True)
            cfg_path.write_text(
                json.dumps({"p0": {"mcp_quarantine_enabled": False}}),
                encoding="utf-8",
            )
            res = mcp_policy.evaluate_tool_call(cwd, "ops", "delete_cluster")
            self.assertEqual(res["decision"], "allow")
            self.assertEqual(res["reason"], "mcp_quarantine_disabled")

            cfg_path.write_text(
                json.dumps({"p0": {"mcp_quarantine_enabled": True, "mcp_mode": "strict"}}),
                encoding="utf-8",
            )
            strict_read = mcp_policy.evaluate_tool_call(cwd, "github", "list_issues")
            self.assertEqual(strict_read["decision"], "deny")
            self.assertEqual(strict_read["code"], "READONLY")

    def test_cli_check_exit_codes_and_tdq_log_toggle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            proc_deny = _run_cli(
                ["check", "github", "create_issue", "--cwd", str(cwd), "--json"],
                tdq_log="1",
            )
            self.assertEqual(proc_deny.returncode, 1)
            deny_payload = json.loads(proc_deny.stdout.decode("utf-8"))
            self.assertEqual(deny_payload["decision"], "deny")
            self.assertEqual(deny_payload["code"], "READONLY")

            stderr_lines = proc_deny.stderr.decode("utf-8").strip().splitlines()
            self.assertTrue(stderr_lines)
            match = ISO_LOG_RE.match(stderr_lines[0])
            self.assertIsNotNone(match)
            if match is not None:
                self.assertIsNotNone(datetime.fromisoformat(match.group(1)).tzinfo)

            proc_allow = _run_cli(
                ["check", "github", "list_issues", "--cwd", str(cwd), "--json"],
                tdq_log="0",
            )
            self.assertEqual(proc_allow.returncode, 0)
            self.assertEqual(proc_allow.stderr, b"")
            self.assertEqual(json.loads(proc_allow.stdout.decode("utf-8"))["decision"], "allow")

            cfg_path = cwd / "docs" / "tdq" / "config.json"
            cfg_path.parent.mkdir(parents=True, exist_ok=True)
            cfg_path.write_text("{corrupt-cfg", encoding="utf-8")
            (cwd / "docs" / "tdq" / "mcp-policy.json").write_text("{corrupt", encoding="utf-8")
            proc_silent = _run_cli(
                ["check", "github", "create_issue", "--cwd", str(cwd), "--json"],
                tdq_log="0",
            )
            self.assertEqual(proc_silent.returncode, 1)
            self.assertEqual(proc_silent.stderr, b"")

            proc_bad_json = _run_cli(
                ["check", "github", "create_issue", "--cwd", str(cwd), "--schema-json", "{bad"],
                tdq_log="0",
            )
            self.assertEqual(proc_bad_json.returncode, 2)

    def test_split_eager_mcp_name_trusted_and_lsp_guards(self) -> None:
        mcp_policy = _load_module()
        with tempfile.TemporaryDirectory() as tmp:
            policy, _corrupt = mcp_policy.load_policy(tmp)
            self.assertEqual(
                mcp_policy.split_eager_mcp_name("mcp_other_lsp_start_lsp", policy),
                ("other_lsp", "start_lsp"),
            )
            self.assertEqual(
                mcp_policy.split_eager_mcp_name(
                    "mcp_tdq-workflow-agy_tavily-primary_tavily_search", policy
                ),
                ("tdq-workflow-agy_tavily-primary", "tavily_search"),
            )
            self.assertEqual(
                mcp_policy.split_eager_mcp_name(
                    "mcp_gemini-api_gemini-api-docs_gemini_search_docs", policy
                ),
                ("gemini-api_gemini-api-docs", "gemini_search_docs"),
            )
            self.assertEqual(
                mcp_policy.split_eager_mcp_name("mcp_evil_delete_lsp_entry", policy),
                ("evil", "delete_lsp_entry"),
            )
            bypass = mcp_policy.evaluate_tool_call(tmp, "evil", "delete_lsp_entry")
            self.assertTrue(mcp_policy.is_denied(bypass))
            self.assertEqual(bypass["code"], "READONLY")


if __name__ == "__main__":
    unittest.main()
