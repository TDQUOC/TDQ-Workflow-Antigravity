"""Unit tests for scripts/tdq_domains.py and scripts/defaults/domains/*.json."""

from __future__ import annotations

import ast
import importlib
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
DEFAULTS_DIR = SCRIPTS_DIR / "defaults" / "domains"
DOMAIN_IDS = ("code-build", "research-rca", "pm-ba-content", "ops-checklist")
REQUIRED_PACK_KEYS = (
    "schema_version",
    "domain_id",
    "title",
    "default_work_kind",
    "allow_downgrade",
    "escalate_on_code_edit",
    "preferred_lane",
    "default_muc_qc",
    "preferred_skills",
    "keywords_en",
    "keywords_vi_ascii",
)
ISO_LOG_RE = re.compile(r"^\[([^\]]+)\]\s+tdq_domains:\s+")

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


def _load_module() -> Any:
    return importlib.import_module("tdq_domains")


def _run_cli(
    args: list[str],
    tdq_log: str = "1",
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[bytes]:
    env = dict(os.environ)
    env["TDQ_LOG"] = tdq_log
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        [sys.executable, "-X", "utf8", str(SCRIPTS_DIR / "tdq_domains.py"), *args],
        check=False,
        capture_output=True,
        env=env,
        timeout=15,
    )


class TestDomainPacksContracts(unittest.TestCase):
    def test_isolation_utf8_io_and_lazy_skill_router(self) -> None:
        src = (SCRIPTS_DIR / "tdq_domains.py").read_text(encoding="utf-8")
        tree = ast.parse(src)
        top_imports: set[str] = set()
        for node in tree.body:
            if isinstance(node, ast.Import):
                top_imports.update(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                top_imports.add(node.module.split(".")[0])
        self.assertIn("utf8_io", top_imports)
        self.assertNotIn("skill_router", top_imports)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertNotIn("hooks", alias.name)
            elif isinstance(node, ast.ImportFrom):
                self.assertNotIn("hooks", node.module or "")

    def test_function_line_lengths_stay_under_cap(self) -> None:
        src = (SCRIPTS_DIR / "tdq_domains.py").read_text(encoding="utf-8")
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self.assertIsNotNone(node.end_lineno)
                span = (node.end_lineno or node.lineno) - node.lineno + 1
                self.assertLessEqual(span, 50, f"{node.name} is {span} lines (> 50)")

    def test_default_json_packs_schema_and_ascii(self) -> None:
        for did in DOMAIN_IDS:
            path = DEFAULTS_DIR / f"{did}.json"
            self.assertTrue(path.is_file(), f"Missing default pack: {path}")
            raw = path.read_text(encoding="utf-8")
            self.assertTrue(raw.isascii(), f"Non-ASCII character found in {path.name}")
            data = json.loads(raw)
            self.assertEqual(data.get("domain_id"), did)
            for key in REQUIRED_PACK_KEYS:
                self.assertIn(key, data, f"Missing {key} in {path.name}")


class TestLoadDomainPacks(unittest.TestCase):
    def test_loads_all_four_default_packs(self) -> None:
        tdq_domains = _load_module()
        with tempfile.TemporaryDirectory() as tmp:
            packs = tdq_domains.load_domain_packs(tmp)
        self.assertEqual(set(packs.keys()), set(DOMAIN_IDS))
        self.assertEqual(packs["code-build"]["default_work_kind"], "build")
        self.assertFalse(packs["code-build"]["escalate_on_code_edit"])
        self.assertEqual(packs["research-rca"]["default_work_kind"], "investigate")
        self.assertTrue(packs["research-rca"]["escalate_on_code_edit"])
        self.assertEqual(packs["ops-checklist"]["preferred_lane"], "quick")

    def test_project_override_merges_and_adds_custom_pack(self) -> None:
        tdq_domains = _load_module()
        with tempfile.TemporaryDirectory() as tmp:
            override_dir = Path(tmp) / "docs" / "tdq" / "domains"
            override_dir.mkdir(parents=True, exist_ok=True)
            (override_dir / "research-rca.json").write_text(
                json.dumps(
                    {
                        "domain_id": "research-rca",
                        "default_muc_qc": "standard",
                        "keywords_en": ["investigate", "forensics"],
                    }
                ),
                encoding="utf-8",
            )
            (override_dir / "security-audit.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "domain_id": "security-audit",
                        "title": "Security Audit",
                        "default_work_kind": "investigate",
                        "allow_downgrade": False,
                        "escalate_on_code_edit": True,
                        "preferred_lane": "full",
                        "default_muc_qc": "ultra",
                        "preferred_skills": ["tdq-security-reviewer"],
                        "keywords_en": ["threatmodel", "owasp"],
                        "keywords_vi_ascii": ["bao mat"],
                    }
                ),
                encoding="utf-8",
            )
            packs = tdq_domains.load_domain_packs(tmp)
            self.assertEqual(packs["research-rca"]["default_muc_qc"], "standard")
            self.assertEqual(packs["research-rca"]["default_work_kind"], "investigate")
            self.assertIn("security-audit", packs)
            self.assertEqual(tdq_domains.route_domain(tmp, "owasp check")["domain_id"], "security-audit")
            self.assertEqual(tdq_domains.route_domain(tmp, "forensics")["domain_id"], "research-rca")

    def test_corrupt_or_missing_id_override_warns_and_keeps_defaults(self) -> None:
        tdq_domains = _load_module()
        with tempfile.TemporaryDirectory() as tmp:
            override_dir = Path(tmp) / "docs" / "tdq" / "domains"
            override_dir.mkdir(parents=True, exist_ok=True)
            (override_dir / "bad.json").write_text("{not-valid", encoding="utf-8")
            (override_dir / "noid.json").write_text(json.dumps({"title": "No ID"}), encoding="utf-8")
            with mock.patch.dict(os.environ, {"TDQ_LOG": "0"}):
                self.assertEqual(set(tdq_domains.load_domain_packs(tmp).keys()), set(DOMAIN_IDS))

            proc = _run_cli(["list", "--cwd", tmp, "--json"], tdq_log="1")
            self.assertEqual(proc.returncode, 0)
            self.assertIn(b"WARN", proc.stderr)
            loaded = json.loads(proc.stdout.decode("utf-8"))
            self.assertEqual(set(loaded.keys()), set(DOMAIN_IDS))

            silent = _run_cli(["list", "--cwd", tmp, "--json"], tdq_log="0")
            self.assertEqual(silent.returncode, 0)
            self.assertEqual(silent.stderr, b"")


class TestRouteDomain(unittest.TestCase):
    def test_routes_english_and_accented_vietnamese_prompts(self) -> None:
        tdq_domains = _load_module()
        cases = [
            ("implement api bug fix", "code-build"),
            ("sửa lỗi tính năng đăng nhập", "code-build"),  # i18n-allow
            ("investigate root cause benchmark", "research-rca"),
            ("phan tich nguyen nhan loi", "research-rca"),
            ("phân tích nguyên nhân lỗi", "research-rca"),  # i18n-allow
            ("đánh giá kiến trúc", "research-rca"),  # i18n-allow
            ("write prd roadmap spec", "pm-ba-content"),
            ("viết tài liệu đặc tả kế hoạch", "pm-ba-content"),  # i18n-allow
            ("verify release packaging runbook", "ops-checklist"),
            ("kiểm tra đóng gói phát hành cài đặt", "ops-checklist"),  # i18n-allow
        ]
        with tempfile.TemporaryDirectory() as tmp:
            for prompt, expected in cases:
                with self.subTest(prompt=prompt):
                    routed = tdq_domains.route_domain(prompt, cwd=tmp)
                    self.assertEqual(routed["domain_id"], expected)

    def test_supports_cwd_first_and_prompt_first_signatures(self) -> None:
        tdq_domains = _load_module()
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(
                tdq_domains.route_domain(tmp, "phân tích nguyên nhân lỗi")["domain_id"],  # i18n-allow
                "research-rca",
            )
            self.assertEqual(
                tdq_domains.route_domain("phân tích nguyên nhân lỗi", tmp)["domain_id"],  # i18n-allow
                "research-rca",
            )
            self.assertEqual(
                tdq_domains.route_domain(cwd=tmp, prompt_text="verify release")["domain_id"],
                "ops-checklist",
            )
            self.assertEqual(tdq_domains.route_domain(tmp, "")["domain_id"], "code-build")

    def test_explicit_and_ambiguous_fallback_to_code_build(self) -> None:
        tdq_domains = _load_module()
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(tdq_domains.route_domain("", cwd=tmp)["domain_id"], "code-build")
            self.assertEqual(tdq_domains.route_domain("hello world", cwd=tmp)["domain_id"], "code-build")
            self.assertEqual(tdq_domains.route_domain("investigate bug", cwd=tmp)["domain_id"], "code-build")
            self.assertEqual(
                tdq_domains.route_domain("anything", cwd=tmp, explicit="ops-checklist")["domain_id"],
                "ops-checklist",
            )
            self.assertEqual(
                tdq_domains.route_domain("anything", cwd=tmp, explicit="unknown-pack")["domain_id"],
                "code-build",
            )

    def test_router_rollback_env_and_flat_config_fallback(self) -> None:
        tdq_domains = _load_module()
        prompt = "phân tích nguyên nhân lỗi"  # i18n-allow
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.dict(os.environ, {"TDQ_DOMAIN_ROUTER_ENABLED": "0"}):
                self.assertEqual(tdq_domains.route_domain(prompt, cwd=tmp)["domain_id"], "code-build")

            cfg_path = Path(tmp) / "docs" / "tdq" / "config.json"
            cfg_path.parent.mkdir(parents=True, exist_ok=True)
            cfg_path.write_text(json.dumps({"p1": {"domain_router_enabled": False}}), encoding="utf-8")
            self.assertEqual(tdq_domains.route_domain(prompt, cwd=tmp)["domain_id"], "code-build")

            cfg_path.write_text(json.dumps({"domain_router_enabled": False}), encoding="utf-8")
            self.assertEqual(tdq_domains.route_domain(prompt, cwd=tmp)["domain_id"], "code-build")

            with mock.patch.object(
                tdq_domains.tdq_config,
                "load_config",
                return_value={"domain_router_enabled": False},
            ):
                self.assertEqual(tdq_domains.route_domain(prompt, cwd=tmp)["domain_id"], "code-build")


class TestTransitionAndZeroDowngrade(unittest.TestCase):
    def test_can_transition_domain_lock_rules(self) -> None:
        tdq_domains = _load_module()
        with tempfile.TemporaryDirectory() as tmp:
            packs = tdq_domains.load_domain_packs(tmp)

        for target in ("research-rca", "pm-ba-content", "ops-checklist"):
            allowed, reason = tdq_domains.can_transition_domain("code-build", target, packs)
            self.assertFalse(allowed, target)
            self.assertTrue(reason)

        for source in ("research-rca", "pm-ba-content", "ops-checklist"):
            allowed, _reason = tdq_domains.can_transition_domain(source, "code-build", packs)
            self.assertTrue(allowed, source)

        peer_ok, _ = tdq_domains.can_transition_domain("research-rca", "pm-ba-content", packs)
        self.assertTrue(peer_ok)

        locked_ok, locked_reason = tdq_domains.can_transition_domain(
            "research-rca", "pm-ba-content", packs, downgrade_locked=True
        )
        self.assertFalse(locked_ok)
        self.assertIn("lock", locked_reason.lower())

        bad_ok, _ = tdq_domains.can_transition_domain("research-rca", "unknown-pack", packs)
        self.assertFalse(bad_ok)

    def test_should_block_code_edit_states_and_kill_switch(self) -> None:
        tdq_domains = _load_module()
        with tempfile.TemporaryDirectory() as tmp:
            self.assertFalse(tdq_domains.should_block_code_edit(tmp, None)[0])
            self.assertFalse(tdq_domains.should_block_code_edit(tmp, {"work_kind": "investigate"})[0])

            inv_state = {"active_request": "2026-11-26-0001-a", "work_kind": "investigate"}
            blocked_inv, reason_inv = tdq_domains.should_block_code_edit(tmp, inv_state)
            self.assertTrue(blocked_inv)
            self.assertIn("escalate-to-build", reason_inv)

            rca_state = {
                "active_request": "2026-11-26-0001-a",
                "work_kind": "build",
                "domain_id": "research-rca",
            }
            self.assertTrue(tdq_domains.should_block_code_edit(tmp, rca_state)[0])

            build_state = {
                "active_request": "2026-11-26-0001-a",
                "work_kind": "build",
                "domain_id": "code-build",
            }
            self.assertFalse(tdq_domains.should_block_code_edit(tmp, build_state)[0])

            legacy_build = {"active_request": "2026-11-26-0001-a", "work_kind": "build"}
            self.assertFalse(tdq_domains.should_block_code_edit(tmp, legacy_build)[0])

            with mock.patch.dict(os.environ, {"TDQ_ZERO_DOWNGRADE_ENABLED": "0"}):
                self.assertFalse(tdq_domains.should_block_code_edit(tmp, rca_state)[0])

            cfg_path = Path(tmp) / "docs" / "tdq" / "config.json"
            cfg_path.parent.mkdir(parents=True, exist_ok=True)
            cfg_path.write_text(json.dumps({"p1": {"zero_downgrade_enabled": False}}), encoding="utf-8")
            self.assertFalse(tdq_domains.should_block_code_edit(tmp, inv_state)[0])


class TestCliAndLogService(unittest.TestCase):
    def test_cli_route_transition_check_edit_and_tdq_log_toggle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            proc_log1 = _run_cli(
                ["route", "--prompt", "phân tích nguyên nhân lỗi", "--cwd", tmp, "--json"],  # i18n-allow
                tdq_log="1",
            )
            self.assertEqual(proc_log1.returncode, 0, proc_log1.stderr.decode("utf-8", "replace"))
            routed = json.loads(proc_log1.stdout.decode("utf-8"))
            self.assertEqual(routed["domain_id"], "research-rca")

            err_lines = proc_log1.stderr.decode("utf-8").strip().splitlines()
            self.assertTrue(err_lines)
            match = ISO_LOG_RE.match(err_lines[0])
            self.assertIsNotNone(match)
            if match is not None:
                self.assertIsNotNone(datetime.fromisoformat(match.group(1)).tzinfo)

            proc_log0 = _run_cli(
                ["route", "--prompt", "phân tích nguyên nhân lỗi", "--cwd", tmp, "--json"],  # i18n-allow
                tdq_log="0",
            )
            self.assertEqual(proc_log0.returncode, 0)
            self.assertEqual(proc_log0.stderr, b"")

            deny_tr = _run_cli(
                ["check-transition", "--from", "code-build", "--to", "research-rca", "--cwd", tmp, "--json"],
                tdq_log="0",
            )
            self.assertEqual(deny_tr.returncode, 1)
            self.assertFalse(json.loads(deny_tr.stdout.decode("utf-8"))["allowed"])
            self.assertEqual(deny_tr.stderr, b"")

            allow_tr = _run_cli(
                ["check-transition", "--from", "research-rca", "--to", "code-build", "--cwd", tmp, "--json"],
                tdq_log="0",
            )
            self.assertEqual(allow_tr.returncode, 0)
            self.assertTrue(json.loads(allow_tr.stdout.decode("utf-8"))["allowed"])

            state_path = Path(tmp) / "docs" / "tdq" / "state.json"
            state_path.parent.mkdir(parents=True, exist_ok=True)
            state_path.write_text(
                json.dumps({"active_request": "2026-11-26-0001-a", "domain_id": "research-rca"}),
                encoding="utf-8",
            )
            blk = _run_cli(["check-edit", "--cwd", tmp, "--json"], tdq_log="0")
            self.assertEqual(blk.returncode, 1)
            self.assertTrue(json.loads(blk.stdout.decode("utf-8"))["blocked"])
            self.assertEqual(blk.stderr, b"")


if __name__ == "__main__":
    unittest.main()
