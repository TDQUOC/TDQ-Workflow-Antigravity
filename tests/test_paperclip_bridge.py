"""Offline unit tests for scripts/tdq_paperclip_bridge.py and default bridge JSON."""

from __future__ import annotations

import ast
import importlib
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
import urllib.error
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime
from pathlib import Path
from typing import Any
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = ROOT / "scripts"
DEFAULT_BRIDGE_JSON = SCRIPTS_DIR / "defaults" / "paperclip-bridge.default.json"
BRIDGE_SCRIPT = SCRIPTS_DIR / "tdq_paperclip_bridge.py"
ISO_LOG_RE = re.compile(r"^\[([^\]]+)\]\s+tdq_paperclip_bridge:\s+")

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


def _load_bridge() -> Any:
    return importlib.import_module("tdq_paperclip_bridge")


def _clean_env(**updates: str) -> dict[str, str]:
    env = dict(os.environ)
    for key in (
        "PAPERCLIP_BRIDGE_ENABLED",
        "TDQ_PAPERCLIP_BRIDGE_ENABLED",
        "PAPERCLIP_API_URL",
        "PAPERCLIP_TOKEN_ENV",
        "PAPERCLIP_TIMEOUT_SEC",
        "PAPERCLIP_API_TOKEN",
        "TDQ_PROJECT_DIR",
        "TDQ_LOG",
    ):
        env.pop(key, None)
    env.update(updates)
    return env


class _FakeHttpResponse:
    """Minimal context-manager mock for urllib.request.urlopen responses."""

    def __init__(self, body: dict[str, Any], status: int = 200) -> None:
        self._raw = json.dumps(body).encode("utf-8")
        self.status = status

    def read(self) -> bytes:
        return self._raw

    def __enter__(self):
        return self

    def __exit__(self, *args: object) -> bool:
        return False


def _enable_project_bridge(project_dir: Path, overrides: dict[str, Any] | None = None) -> None:
    cfg_path = project_dir / "docs" / "tdq" / "paperclip-bridge.json"
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {"enabled": True}
    if overrides:
        payload.update(overrides)
    cfg_path.write_text(json.dumps(payload), encoding="utf-8")


class TestBridgeStaticContracts(unittest.TestCase):
    def test_default_config_schema_and_pure_ascii(self) -> None:
        self.assertTrue(DEFAULT_BRIDGE_JSON.is_file(), "Missing default bridge JSON")
        raw = DEFAULT_BRIDGE_JSON.read_text(encoding="utf-8")
        self.assertTrue(raw.isascii(), "Default bridge JSON must remain pure ASCII")
        data = json.loads(raw)
        self.assertEqual(data["schema_version"], 1)
        self.assertFalse(data["enabled"])
        self.assertEqual(data["transport"], "cli-one-way")
        self.assertEqual(data["timeout_sec"], 5)
        self.assertEqual(data["default_lane"], "full")
        self.assertEqual(
            set(data["endpoints"].keys()),
            {"health", "issue", "comments"},
        )

    def test_bridge_script_isolation_ascii_and_function_caps(self) -> None:
        src = BRIDGE_SCRIPT.read_text(encoding="utf-8")
        self.assertTrue(src.isascii(), "tdq_paperclip_bridge.py must stay pure ASCII")
        tree = ast.parse(src)
        top_imports: set[str] = set()
        for node in tree.body:
            if isinstance(node, ast.Import):
                top_imports.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                top_imports.add(node.module.split(".")[0])
        self.assertIn("utf8_io", top_imports)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertNotIn("hooks", alias.name)
            elif isinstance(node, ast.ImportFrom):
                self.assertNotIn("hooks", node.module or "")
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                span = (node.end_lineno or node.lineno) - node.lineno + 1
                self.assertLessEqual(span, 50, f"{node.name} is {span} lines (> 50)")


class TestBridgeConfigAndLogging(unittest.TestCase):
    def test_disabled_by_default_exits_3_without_opening_sockets(self) -> None:
        bridge = _load_bridge()
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp)
            env = _clean_env(TDQ_LOG="0")
            with (
                mock.patch.dict(os.environ, env, clear=True),
                mock.patch("urllib.request.urlopen") as mock_open,
            ):
                for subcmd in (
                    ["--cwd", str(project_dir), "status"],
                    ["--cwd", str(project_dir), "pull", "--issue", "PAP-42"],
                    [
                        "--cwd",
                        str(project_dir),
                        "push-report",
                        "--slug",
                        "2026-11-26-2340-pap-42",
                        "--issue",
                        "PAP-42",
                    ],
                ):
                    with self.subTest(subcmd=subcmd[2]):
                        buf_out, buf_err = io.StringIO(), io.StringIO()
                        with redirect_stdout(buf_out), redirect_stderr(buf_err):
                            rc = bridge.main(subcmd)
                        self.assertEqual(rc, 3)
                        self.assertEqual(buf_err.getvalue(), "")
                mock_open.assert_not_called()

    def test_corrupt_project_bridge_json_fails_closed_to_disabled(self) -> None:
        bridge = _load_bridge()
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp)
            bad = project_dir / "docs" / "tdq" / "paperclip-bridge.json"
            bad.parent.mkdir(parents=True, exist_ok=True)
            bad.write_text("{corrupt", encoding="utf-8")
            env = _clean_env(TDQ_LOG="1", PAPERCLIP_BRIDGE_ENABLED="1")
            with (
                mock.patch.dict(os.environ, env, clear=True),
                mock.patch("urllib.request.urlopen") as mock_open,
            ):
                buf_err = io.StringIO()
                with redirect_stderr(buf_err):
                    rc = bridge.main(["--cwd", str(project_dir), "status"])
                self.assertEqual(rc, 3)
                self.assertIn("tdq_paperclip_bridge:", buf_err.getvalue())
                mock_open.assert_not_called()

    def test_cli_tdq_log_one_vs_zero_subprocess(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            proc_on = subprocess.run(
                [sys.executable, "-X", "utf8", str(BRIDGE_SCRIPT), "--cwd", tmp, "status"],
                env=_clean_env(TDQ_LOG="1"),
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=15,
                check=False,
            )
            self.assertEqual(proc_on.returncode, 3)
            lines = [ln for ln in proc_on.stderr.splitlines() if ln.strip()]
            self.assertTrue(lines)
            match = ISO_LOG_RE.match(lines[0])
            self.assertIsNotNone(match, f"Unexpected stderr log: {lines[0]!r}")
            self.assertIsNotNone(datetime.fromisoformat(match.group(1)).utcoffset())

            proc_off = subprocess.run(
                [sys.executable, "-X", "utf8", str(BRIDGE_SCRIPT), "--cwd", tmp, "status"],
                env=_clean_env(TDQ_LOG="0"),
                capture_output=True,
                timeout=15,
                check=False,
            )
            self.assertEqual(proc_off.returncode, 3)
            self.assertEqual(proc_off.stderr, b"")


class TestBridgeSecurityAndActions(unittest.TestCase):
    def test_status_optional_token_and_custom_endpoint(self) -> None:
        bridge = _load_bridge()
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp)
            _enable_project_bridge(
                project_dir,
                {"base_url": "https://paperclip.local/api/", "endpoints": {"health": "/v1/ping"}},
            )
            seen: dict[str, Any] = {}

            def fake_open(req: Any, timeout: float = 0.0) -> _FakeHttpResponse:
                seen["url"] = req.full_url
                seen["auth"] = req.get_header("Authorization")
                seen["timeout"] = timeout
                return _FakeHttpResponse({"ok": True, "version": "1.2"})

            with (
                mock.patch.dict(os.environ, _clean_env(TDQ_LOG="0"), clear=True),
                mock.patch("urllib.request.urlopen", side_effect=fake_open),
            ):
                out = io.StringIO()
                with redirect_stdout(out):
                    rc = bridge.main(["--cwd", str(project_dir), "status", "--json"])
                self.assertEqual(rc, 0)
                self.assertEqual(seen["url"], "https://paperclip.local/api/v1/ping")
                self.assertIsNone(seen["auth"])
                self.assertTrue(json.loads(out.getvalue())["ok"])

    def test_rejects_unsafe_url_and_quotes_issue_path_traversal(self) -> None:
        bridge = _load_bridge()
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp)
            _enable_project_bridge(project_dir, {"base_url": "file:///etc/passwd"})
            env = _clean_env(TDQ_LOG="0", PAPERCLIP_API_TOKEN="tok-safe")
            with (
                mock.patch.dict(os.environ, env, clear=True),
                mock.patch("urllib.request.urlopen") as mock_open,
            ):
                err = io.StringIO()
                with redirect_stderr(err):
                    rc = bridge.main(["--cwd", str(project_dir), "status"])
                self.assertEqual(rc, 2)
                mock_open.assert_not_called()

        quoted = bridge.build_endpoint_url(
            "http://127.0.0.1:3100/api",
            "/issues/{issue_id}",
            "PAP/../../secret",
        )
        self.assertEqual(quoted, "http://127.0.0.1:3100/api/issues/PAP%2F..%2F..%2Fsecret")

    def test_pull_requires_token_and_redacts_secrets_on_http_error(self) -> None:
        bridge = _load_bridge()
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp)
            _enable_project_bridge(project_dir)

            with (
                mock.patch.dict(os.environ, _clean_env(TDQ_LOG="0"), clear=True),
                mock.patch("urllib.request.urlopen") as mock_open,
            ):
                rc = bridge.main(["--cwd", str(project_dir), "pull", "--issue", "PAP-42"])
                self.assertEqual(rc, 4)
                mock_open.assert_not_called()

            secret = "super-secret-token-999"
            http_err = urllib.error.HTTPError(
                url="http://127.0.0.1:3100/api/issues/PAP-42",
                code=401,
                msg=f"Unauthorized token {secret}",
                hdrs=None,  # type: ignore[arg-type]
                fp=io.BytesIO(f"bad token {secret}".encode()),
            )
            env = _clean_env(TDQ_LOG="1", PAPERCLIP_API_TOKEN=secret)
            with (
                mock.patch.dict(os.environ, env, clear=True),
                mock.patch("urllib.request.urlopen", side_effect=http_err),
            ):
                out, err = io.StringIO(), io.StringIO()
                with redirect_stdout(out), redirect_stderr(err):
                    rc_err = bridge.main(["--cwd", str(project_dir), "pull", "--issue", "PAP-42"])
                self.assertEqual(rc_err, 4)
                self.assertNotIn(secret, err.getvalue())
                self.assertNotIn(secret, out.getvalue())
                self.assertFalse((project_dir / "docs" / "tdq" / "state.json").exists())

    def test_pull_routes_domain_runs_tdq_state_init_and_creates_brief(self) -> None:
        bridge = _load_bridge()
        import tdq_state

        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp)
            _enable_project_bridge(project_dir)

            def fake_open(req: Any, timeout: float = 0.0) -> _FakeHttpResponse:
                self.assertEqual(req.get_header("Authorization"), "Bearer tok-pull")
                return _FakeHttpResponse({
                    "id": "PAP-42",
                    "title": "Investigate root cause SQL bug",
                    "description": "Analyze failure trace without editing source code",
                })

            calls: list[list[str]] = []

            def fake_subproc(cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
                calls.append(list(cmd))
                return subprocess.CompletedProcess(cmd, 0, "ok", "")

            env = _clean_env(TDQ_LOG="0", PAPERCLIP_API_TOKEN="tok-pull")
            with (
                mock.patch.dict(os.environ, env, clear=True),
                mock.patch("urllib.request.urlopen", side_effect=fake_open),
                mock.patch("subprocess.run", side_effect=fake_subproc),
            ):
                out = io.StringIO()
                with redirect_stdout(out):
                    rc = bridge.main(
                        ["--cwd", str(project_dir), "pull", "--issue", "PAP-42", "--json"]
                    )
            self.assertEqual(rc, 0)
            res = json.loads(out.getvalue())
            self.assertEqual(res["authority"], "tdq_state.py")
            self.assertEqual(res["tdq_domain_id"], "research-rca")
            self.assertEqual(res["tdq_work_kind"], "investigate")
            parsed_slug = tdq_state.parse_slug(res["tdq_slug"])
            self.assertIsNotNone(parsed_slug)
            self.assertIsNotNone(parsed_slug[1], "Slug must contain valid HHMM")
            self.assertGreaterEqual(len(calls), 2)
            self.assertIn("init", calls[0])
            self.assertIn("--kind", calls[0])
            self.assertIn("set", calls[1])
            brief_path = project_dir / res["brief_file"]
            self.assertTrue(brief_path.is_file())
            brief_txt = brief_path.read_text(encoding="utf-8")
            self.assertIn("Soul:", brief_txt)
            self.assertIn("## Nguy\u00ean v\u0103n", brief_txt)
            self.assertIn("PAP-42", brief_txt)

    def test_pull_subprocess_failure_writes_no_orphan_brief(self) -> None:
        bridge = _load_bridge()
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp)
            _enable_project_bridge(project_dir)

            def fake_open(req: Any, timeout: float = 0.0) -> _FakeHttpResponse:
                return _FakeHttpResponse({"id": "PAP-99", "title": "Fix bug"})

            fail_proc = subprocess.CompletedProcess(["tdq_state.py"], 2, "", "init rejected")
            env = _clean_env(TDQ_LOG="0", PAPERCLIP_API_TOKEN="tok-pull")
            with (
                mock.patch.dict(os.environ, env, clear=True),
                mock.patch("urllib.request.urlopen", side_effect=fake_open),
                mock.patch("subprocess.run", return_value=fail_proc),
            ):
                rc = bridge.main(["--cwd", str(project_dir), "pull", "--issue", "PAP-99"])
            self.assertEqual(rc, 4)
            brief_dir = project_dir / "docs" / "tdq" / "brief"
            self.assertFalse(brief_dir.exists() and any(brief_dir.iterdir()))

    def test_push_report_extracts_summary_and_posts_comment(self) -> None:
        bridge = _load_bridge()
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp)
            _enable_project_bridge(project_dir)
            slug = "2026-11-26-2340-pap-42"

            env = _clean_env(TDQ_LOG="0", PAPERCLIP_API_TOKEN="tok-push")
            with (
                mock.patch.dict(os.environ, env, clear=True),
                mock.patch("urllib.request.urlopen") as mock_open,
            ):
                rc_missing = bridge.main([
                    "--cwd",
                    str(project_dir),
                    "push-report",
                    "--slug",
                    slug,
                    "--issue",
                    "PAP-42",
                ])
                self.assertEqual(rc_missing, 2)
                mock_open.assert_not_called()

            report_file = project_dir / "docs" / "tdq" / "reports" / f"{slug}.md"
            report_file.parent.mkdir(parents=True, exist_ok=True)
            report_file.write_text(
                "# REPORT\n\n> **T\u00f3m t\u1eaft d\u1ec5 hi\u1ec3u:** Done all checks clean.\n",
                encoding="utf-8",
            )
            posted: dict[str, Any] = {}

            def fake_open(req: Any, timeout: float = 0.0) -> _FakeHttpResponse:
                posted["url"] = req.full_url
                posted["method"] = req.get_method()
                posted["body"] = json.loads(req.data.decode("utf-8"))
                return _FakeHttpResponse({"comment_id": "c-100"})

            state_proc = subprocess.CompletedProcess(
                ["tdq_state.py", "get"],
                0,
                json.dumps({"active_request": slug, "phase": "report"}),
                "",
            )
            with (
                mock.patch.dict(os.environ, env, clear=True),
                mock.patch("urllib.request.urlopen", side_effect=fake_open),
                mock.patch("subprocess.run", return_value=state_proc),
            ):
                out = io.StringIO()
                with redirect_stdout(out):
                    rc_ok = bridge.main([
                        "--cwd",
                        str(project_dir),
                        "push-report",
                        "--slug",
                        slug,
                        "--issue",
                        "PAP-42",
                        "--json",
                    ])
            self.assertEqual(rc_ok, 0)
            self.assertEqual(posted["method"], "POST")
            self.assertEqual(posted["url"], "http://127.0.0.1:3100/api/issues/PAP-42/comments")
            self.assertEqual(posted["body"]["bridge_action"], "push-report")
            self.assertEqual(posted["body"]["tdq_phase"], "report")
            self.assertIn("Done all checks clean.", posted["body"]["summary"])

    def test_pull_real_tdq_state_subprocess_e2e(self) -> None:
        bridge = _load_bridge()
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp)
            _enable_project_bridge(project_dir)

            def fake_open(req: Any, timeout: float = 0.0) -> _FakeHttpResponse:
                return _FakeHttpResponse({
                    "id": "PAP-7",
                    "title": "Implement bridge feature CLI",
                    "description": "Build CLI script and unit tests",
                })

            env = _clean_env(TDQ_LOG="0", PAPERCLIP_API_TOKEN="tok-e2e")
            with (
                mock.patch.dict(os.environ, env, clear=True),
                mock.patch("urllib.request.urlopen", side_effect=fake_open),
            ):
                out = io.StringIO()
                with redirect_stdout(out):
                    rc = bridge.main([
                        "--cwd",
                        str(project_dir),
                        "pull",
                        "--issue",
                        "PAP-7",
                        "--bo-qua-lsp",
                        "offline e2e bridge test",
                        "--json",
                    ])
            self.assertEqual(rc, 0)
            res = json.loads(out.getvalue())
            state_path = project_dir / "docs" / "tdq" / "state.json"
            self.assertTrue(state_path.is_file())
            st = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(st["schema_version"], 6)
            self.assertEqual(st["active_request"], res["tdq_slug"])
            self.assertEqual(st["domain_id"], "code-build")
            self.assertEqual(st["brief_file"], res["brief_file"])
            self.assertTrue((project_dir / res["brief_file"]).is_file())


if __name__ == "__main__":
    unittest.main()
