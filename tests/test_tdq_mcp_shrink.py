"""Unit and benchmark tests for scripts/tdq_mcp_shrink.py."""

from __future__ import annotations

import copy
import io
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

WORKTREE_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = WORKTREE_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import tdq_mcp_shrink


def _build_realistic_mcp_tools() -> list[dict]:
    """Build a realistic lsp + chrome-devtools tools/list payload."""
    lsp_tools = [
        {
            "name": "activate_skill",
            "description": (
                "Activate phase enforcement for a skill workflow. Once active, "
                "tool calls are checked against the skill's phase permissions. "
                "Phases advance automatically as you call tools from later phases. "
                "Use this at the start of a skill workflow to enable safety "
                "guardrails that prevent out-of-order operations (e.g., applying "
                "edits before completing blast-radius analysis)."
            ),
            "inputSchema": {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "title": "ActivateSkillArgs",
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "skill_name": {
                        "type": "string",
                        "title": "Skill Name",
                        "description": (
                            "Name of the skill to activate (e.g. lsp-rename, "
                            "lsp-refactor). This field is required."
                        ),
                        "examples": ["lsp-rename"],
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["warn", "block"],
                        "default": "warn",
                        "description": (
                            "Enforcement mode: warn or block. Default: warn."
                        ),
                    },
                },
                "required": ["skill_name"],
            },
        },
        {
            "name": "find_references",
            "description": (
                "Find all usages of a symbol across the codebase. Use before "
                "renaming, deleting, or changing any symbol to understand who "
                "calls it. Zero references means the symbol may be dead code; "
                "use safe_delete_symbol to remove it safely. For blast-radius "
                "analysis with test/non-test partitioning, use blast_radius instead."
            ),
            "inputSchema": {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "title": "FindReferencesArgs",
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Absolute path to the source file.",
                    },
                    "line": {
                        "type": "integer",
                        "description": (
                            "1-indexed line number in the file. Optional when "
                            "position_pattern is provided."
                        ),
                    },
                },
                "required": ["file_path"],
            },
        },
        {
            "name": "safe_delete_symbol",
            "description": (
                "Safely delete a symbol definition from a file. This tool checks "
                "references before removal. Never delete exported symbols without "
                "checking callers first."
            ),
            "inputSchema": {
                "$comment": "Internal LSP safe delete schema",
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Target file path to modify.",
                    },
                    "symbol": {
                        "type": "string",
                        "description": "Exact symbol name to remove.",
                    },
                },
                "required": ["path", "symbol"],
            },
        },
    ]
    devtools_tools = [
        {
            "name": "emulate",
            "description": (
                "Emulates various features on the target page. Each call replaces "
                "all emulation settings (except extraHttpHeaders), so pass all "
                "desired settings in a single call."
            ),
            "inputSchema": {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "title": "EmulateArgs",
                "type": "object",
                "properties": {
                    "pageId": {
                        "type": "number",
                        "description": "Targets a specific page by ID.",
                    },
                    "colorScheme": {
                        "type": "string",
                        "enum": ["dark", "light", "auto"],
                        "description": (
                            "Emulate the dark or light mode. Omit or set to auto "
                            "to reset to the default."
                        ),
                    },
                    "cpuThrottlingRate": {
                        "type": "number",
                        "description": (
                            "Represents the CPU slowdown factor. Must be between "
                            "1 and 20."
                        ),
                    },
                },
                "required": ["pageId"],
            },
        },
        {
            "name": "close_page",
            "description": (
                "Closes the page by its index. The last open page cannot be closed."
            ),
            "inputSchema": {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "type": "object",
                "properties": {
                    "pageIdx": {
                        "type": "integer",
                        "description": (
                            "The index of the page to close. Call list_pages to "
                            "inspect open pages."
                        ),
                    }
                },
                "required": ["pageIdx"],
            },
        },
    ]
    return (lsp_tools + devtools_tools) * 10


class ShrinkDescriptionTest(unittest.TestCase):
    """Tests for shrink_description constraint preservation."""

    def test_preserves_negative_and_constraint_tokens_verbatim(self) -> None:
        raw = (
            "Deletes unused helper functions from the module. "
            "You should never delete public API entry points. "
            "Please simply review the diff afterward. "
            "This operation must run inside a clean git worktree."
        )
        out_desc = tdq_mcp_shrink.shrink_description(raw)
        self.assertIn("never delete", out_desc)
        self.assertIn("You should never delete public API entry points.", out_desc)
        self.assertIn("This operation must run inside a clean git worktree.", out_desc)
        self.assertNotIn("Please simply review", out_desc)

    def test_preserves_all_specified_constraint_keywords(self) -> None:
        tokens = [
            "not",
            "never",
            "only",
            "must",
            "cannot",
            "required",
            "default",
            "const",
            "$ref",
            "warning",
            "deprecated",
        ]
        for token in tokens:
            with self.subTest(token=token):
                text = (
                    f"Reads the configuration file. "
                    f"Constraint check: {token} applies here. "
                    f"Useful when working across repositories."
                )
                out_desc = tdq_mcp_shrink.shrink_description(text)
                self.assertIn(f"Constraint check: {token} applies here.", out_desc)
                self.assertNotIn("Useful when working", out_desc)

    def test_strips_filler_and_parenthetical_examples_from_lead_sentence(self) -> None:
        raw = (
            "This tool allows you to simply inspect symbol definitions "
            "(e.g., functions, classes) in the workspace. "
            "It can help you explore unfamiliar codebases."
        )
        out_desc = tdq_mcp_shrink.shrink_description(raw)
        self.assertIn("Inspect symbol definitions", out_desc)
        self.assertNotIn("(e.g.", out_desc)
        self.assertNotIn("explore unfamiliar", out_desc)

    def test_empty_and_whitespace_input(self) -> None:
        self.assertEqual(tdq_mcp_shrink.shrink_description(""), "")
        self.assertEqual(tdq_mcp_shrink.shrink_description("   \n "), "")


class ShrinkSchemaNodeTest(unittest.TestCase):
    """Tests for shrink_schema_node metadata stripping and key preservation."""

    def test_strips_metadata_and_keeps_structural_keys(self) -> None:
        raw_schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$comment": "Generated schema",
            "title": "ReadFileInput",
            "examples": [{"path": "a.py"}],
            "example": {"path": "b.py"},
            "type": "object",
            "required": ["path"],
            "properties": {
                "path": {
                    "type": "string",
                    "title": "File Path",
                    "description": (
                        "Absolute path to the file. "
                        "Never delete files via this reader."
                    ),
                    "examples": ["/tmp/demo.txt"],
                },
                "mode": {
                    "type": "string",
                    "enum": ["text", "binary"],
                    "default": "text",
                },
                "version": {
                    "const": 2,
                },
                "nested": {
                    "$ref": "#/$defs/Target",
                },
            },
            "$defs": {
                "Target": {
                    "title": "TargetDef",
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "Document title field.",
                        }
                    },
                }
            },
        }
        out_schema = tdq_mcp_shrink.shrink_schema_node(raw_schema)
        self.assertNotIn("$schema", out_schema)
        self.assertNotIn("$comment", out_schema)
        self.assertNotIn("title", out_schema)
        self.assertNotIn("examples", out_schema)
        self.assertNotIn("example", out_schema)
        self.assertEqual(out_schema["required"], ["path"])
        self.assertEqual(out_schema["properties"]["mode"]["enum"], ["text", "binary"])
        self.assertEqual(out_schema["properties"]["mode"]["default"], "text")
        self.assertEqual(out_schema["properties"]["version"]["const"], 2)
        self.assertEqual(out_schema["properties"]["nested"]["$ref"], "#/$defs/Target")
        self.assertIn("Never delete", out_schema["properties"]["path"]["description"])
        # Property literally named "title" inside properties map must survive.
        self.assertIn("title", out_schema["$defs"]["Target"]["properties"])
        self.assertNotIn("title", out_schema["$defs"]["Target"])

    def test_preserves_default_and_const_dict_payloads_verbatim(self) -> None:
        raw_schema = {
            "type": "object",
            "properties": {
                "meta": {
                    "type": "object",
                    "default": {"title": "Untitled", "example": 1},
                    "const": {"title": "Fixed"},
                }
            },
        }
        out_schema = tdq_mcp_shrink.shrink_schema_node(raw_schema)
        self.assertEqual(
            out_schema["properties"]["meta"]["default"],
            {"title": "Untitled", "example": 1},
        )
        self.assertEqual(
            out_schema["properties"]["meta"]["const"],
            {"title": "Fixed"},
        )


class TransformRpcResponseTest(unittest.TestCase):
    """Tests for transform_rpc_response across MCP methods."""

    def test_transforms_tools_prompts_resources_and_keeps_tools_call_exact(self) -> None:
        raw_call = {
            "jsonrpc": "2.0",
            "id": 9,
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(
                            {
                                "$schema": "keep-me",
                                "title": "keep-me",
                                "description": "Do not alter tool output prose.",
                            }
                        ),
                    }
                ],
                "structuredContent": {
                    "$schema": "https://example.com/s",
                    "title": "ExactPayload",
                    "description": "This tool allows you to keep exact bytes.",
                },
                "isError": False,
            },
        }
        out_call = tdq_mcp_shrink.transform_rpc_response(
            copy.deepcopy(raw_call), "tools/call"
        )
        self.assertEqual(out_call, raw_call)
        self.assertEqual(
            tdq_mcp_shrink.transform_rpc_response(copy.deepcopy(raw_call), None),
            raw_call,
        )

        prompts_msg = {
            "jsonrpc": "2.0",
            "id": 2,
            "result": {
                "prompts": [
                    {
                        "name": "review",
                        "description": (
                            "This tool allows you to run a code review. "
                            "It supports multiple files."
                        ),
                        "arguments": [
                            {
                                "name": "path",
                                "description": (
                                    "Target path. Required for single file."
                                ),
                                "required": True,
                            }
                        ],
                    }
                ]
            },
        }
        out_prompts = tdq_mcp_shrink.transform_rpc_response(prompts_msg, "prompts/list")
        self.assertNotIn("multiple files", out_prompts["result"]["prompts"][0]["description"])
        self.assertIn(
            "Required for single file.",
            out_prompts["result"]["prompts"][0]["arguments"][0]["description"],
        )

        resources_msg = {
            "jsonrpc": "2.0",
            "id": 3,
            "result": {
                "resources": [
                    {
                        "uri": "file:///README.md",
                        "name": "readme",
                        "description": (
                            "This tool allows you to read project docs. "
                            "Updated on every release."
                        ),
                    }
                ]
            },
        }
        out_resources = tdq_mcp_shrink.transform_rpc_response(
            resources_msg, "resources/list"
        )
        self.assertNotIn(
            "Updated on every release.",
            out_resources["result"]["resources"][0]["description"],
        )


class BenchmarkTest(unittest.TestCase):
    """Benchmark reduction percentage and processing latency."""

    def test_benchmark_realistic_lsp_and_devtools_schemas(self) -> None:
        tools = _build_realistic_mcp_tools()
        rpc_msg = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {"tools": tools},
        }
        raw_bytes = len(
            json.dumps(rpc_msg, ensure_ascii=False, separators=(",", ":")).encode(
                "utf-8"
            )
        )
        t0 = time.perf_counter()
        out_msg = tdq_mcp_shrink.transform_rpc_response(rpc_msg, "tools/list")
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        shrunk_bytes = len(
            json.dumps(out_msg, ensure_ascii=False, separators=(",", ":")).encode(
                "utf-8"
            )
        )
        reduction_pct = ((raw_bytes - shrunk_bytes) / raw_bytes) * 100.0
        self.assertGreaterEqual(reduction_pct, 15.0)
        self.assertLessEqual(elapsed_ms, 100.0)


class SubprocessAndProxyTest(unittest.TestCase):
    """Tests for Windows flags, real subprocess pipe, passthrough, and TDQ_LOG."""

    @patch("subprocess.Popen")
    def test_windows_spawn_sets_create_no_window_and_utf8_env(
        self, mock_popen: MagicMock
    ) -> None:
        proc = MagicMock()
        proc.stdin = io.BytesIO()
        proc.stdout = io.BytesIO(b"")
        proc.wait.return_value = 0
        proc.returncode = 0
        mock_popen.return_value = proc

        with patch.object(tdq_mcp_shrink.sys, "platform", "win32"):
            rc = tdq_mcp_shrink.run_proxy(
                ["python", "-u", "server.py"],
                stdin=io.BytesIO(b""),
                stdout=io.BytesIO(),
            )
        self.assertEqual(rc, 0)
        _, kwargs = mock_popen.call_args
        self.assertEqual(kwargs.get("creationflags"), 0x08000000)
        self.assertEqual(kwargs["env"]["PYTHONUTF8"], "1")
        self.assertEqual(kwargs["env"]["PYTHONUNBUFFERED"], "1")

    def test_real_subprocess_pipe_and_passthrough_and_tdq_log(self) -> None:
        server_code = (
            "import json, sys\n"
            "for line in sys.stdin:\n"
            "    raw = line.rstrip('\\r\\n')\n"
            "    if not raw.strip():\n"
            "        sys.stdout.write(line)\n"
            "        sys.stdout.flush()\n"
            "        continue\n"
            "    try:\n"
            "        msg = json.loads(raw)\n"
            "    except Exception:\n"
            "        sys.stdout.write(raw + '\\n')\n"
            "        sys.stdout.flush()\n"
            "        continue\n"
            "    method = msg.get('method')\n"
            "    mid = msg.get('id')\n"
            "    if method == 'initialize':\n"
            "        resp = {'jsonrpc': '2.0', 'id': mid, 'result': {'protocolVersion': '2025-03-26'}}\n"
            "    elif method == 'tools/list':\n"
            "        resp = {'jsonrpc': '2.0', 'id': mid, 'result': {'tools': [\n"
            "            {'name': 'delete_item', 'description': 'This tool allows you to remove entries. Never delete active root entries. Useful during cleanup.',\n"
            "             'inputSchema': {'$schema': 'https://json-schema.org/draft/2020-12/schema', 'title': 'DeleteItem', 'type': 'object',\n"
            "                             'properties': {'path': {'type': 'string', 'description': 'Target path.'}}, 'required': ['path']}}\n"
            "        ]}}\n"
            "    elif method == 'tools/call':\n"
            "        resp = {'jsonrpc': '2.0', 'id': mid, 'result': {'content': [{'type': 'text', 'text': 'ok'}], 'meta': {'title': 'unchanged', '$schema': 'keep'}}}\n"
            "    else:\n"
            "        resp = {'jsonrpc': '2.0', 'id': mid, 'result': {}}\n"
            "    sys.stdout.write(json.dumps(resp) + '\\n')\n"
            "    sys.stdout.flush()\n"
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            srv_path = Path(tmpdir) / "mock_mcp.py"
            srv_path.write_text(server_code, encoding="utf-8")

            requests = "\n".join(
                [
                    json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize"}),
                    json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}),
                    json.dumps({"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "delete_item"}}),
                    "{not-valid-json",
                    "",
                ]
            ) + "\n"

            proxy_path = SCRIPTS_DIR / "tdq_mcp_shrink.py"
            env_normal = dict(os.environ, PYTHONUTF8="1", PYTHONUNBUFFERED="1")
            env_normal.pop("TDQ_CAVEMAN", None)
            env_normal.pop("TDQ_LOG", None)

            proc = subprocess.run(
                [sys.executable, "-u", str(proxy_path), "--", sys.executable, "-u", str(srv_path)],
                input=requests.encode("utf-8"),
                capture_output=True,
                check=False,
                env=env_normal,
                timeout=15,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr.decode("utf-8", errors="replace"))
            self.assertNotIn(b"\r\n", proc.stdout)
            out_lines = proc.stdout.decode("utf-8").splitlines()
            self.assertEqual(len(out_lines), 5)

            tools_resp = json.loads(out_lines[1])
            tool = tools_resp["result"]["tools"][0]
            self.assertIn("Never delete active root entries.", tool["description"])
            self.assertNotIn("Useful during cleanup.", tool["description"])
            self.assertEqual(tool["inputSchema"]["required"], ["path"])
            self.assertNotIn("$schema", tool["inputSchema"])
            self.assertNotIn("title", tool["inputSchema"])

            call_resp = json.loads(out_lines[2])
            self.assertEqual(
                call_resp["result"]["meta"],
                {"title": "unchanged", "$schema": "keep"},
            )
            self.assertEqual(out_lines[3], "{not-valid-json")
            self.assertEqual(out_lines[4], "")

            stderr_text = proc.stderr.decode("utf-8", errors="replace")
            self.assertIn("tdq_mcp_shrink:", stderr_text)

            # Check TDQ_LOG=0 silences stderr and TDQ_CAVEMAN=0 passes through raw.
            env_muted = dict(env_normal, TDQ_LOG="0", TDQ_CAVEMAN="0")
            proc_muted = subprocess.run(
                [sys.executable, "-u", str(proxy_path), "--cmd", f"{sys.executable} -u {srv_path}"],
                input=requests.encode("utf-8"),
                capture_output=True,
                check=False,
                env=env_muted,
                timeout=15,
            )
            self.assertEqual(proc_muted.returncode, 0)
            self.assertEqual(proc_muted.stderr, b"")
            raw_tools_resp = json.loads(proc_muted.stdout.decode("utf-8").splitlines()[1])
            self.assertIn("$schema", raw_tools_resp["result"]["tools"][0]["inputSchema"])
            self.assertIn("Useful during cleanup.", raw_tools_resp["result"]["tools"][0]["description"])


if __name__ == "__main__":
    unittest.main()
