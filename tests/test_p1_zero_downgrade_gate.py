"""Tests for T3.1: P1 Zero-Downgrade Lock in hooks/scripts/edit_gate.py and intake routing."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from helper import tdq_state

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = ROOT / "scripts"
EDIT_GATE = ROOT / "hooks" / "scripts" / "edit_gate.py"
TDQ_STATE = SCRIPTS_DIR / "tdq_state.py"


def _run_cmd(args: list[str], cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    return subprocess.run(
        [sys.executable, "-X", "utf8", *args],
        cwd=str(cwd),
        env=merged_env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
        check=False,
    )


def _setup_repo(
    tmp: Path,
    *,
    domain_id: str | None = "research-rca",
    work_kind: str = "build",
    downgrade_locked: bool = False,
) -> Path:
    subprocess.run(["git", "init", "-q"], cwd=str(tmp), check=True, timeout=15)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=str(tmp), check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=str(tmp), check=True)
    plan_rel = "docs/tdq/plan/p1-gate-test.md"
    plan_path = tmp / plan_rel
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text("# Plan\n\n- [~] **T1** Sample task — Test: `echo ok`\n", encoding="utf-8")
    state = tdq_state.default_state()
    state.update({
        "active_request": "2026-11-26-0210-p1-gate-test",
        "work_kind": work_kind,
        "domain_id": domain_id,
        "downgrade_locked": downgrade_locked,
        "lane": "quick",
        "phase": "implement",
        "quick_approved": True,
        "implement_mode": "main",
        "plan_file": plan_rel,
        "doc_lang": "en",
        "updated_at": tdq_state.now_iso(),
    })
    state_file = tmp / "docs" / "tdq" / "state.json"
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(json.dumps(state, indent=2), encoding="utf-8")
    log_path = tmp / tdq_state.today_log_rel()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text("# Log\n\n## 01:00 — setup\n", encoding="utf-8")
    (tmp / "src").mkdir(exist_ok=True)
    (tmp / "src" / "app.py").write_text("x = 1\n", encoding="utf-8")
    (tmp / "docs" / "tdq" / "research").mkdir(parents=True, exist_ok=True)
    (tmp / "docs" / "tdq" / "research" / "note.md").write_text("# Note\n", encoding="utf-8")
    return tmp


def _run_edit_gate(
    repo: Path,
    target_rel: str,
    *,
    env: dict[str, str] | None = None,
    agy: bool = False,
) -> dict:
    payload: dict[str, object]
    if agy:
        payload = {
            "agent_action": "PreToolUse",
            "toolName": "replace_file_content",
            "workingDirectory": str(repo),
            "conversationId": "conv-p1-gate-test",
            "toolInput": {"TargetFile": str(repo / target_rel)},
        }
    else:
        payload = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Edit",
            "cwd": str(repo),
            "session_id": "sess-p1-gate-test",
            "tool_input": {"file_path": str(repo / target_rel)},
        }
    merged_env = os.environ.copy()
    merged_env.setdefault("TDQ_PROJECT_DIR", str(repo))
    if env:
        merged_env.update(env)
    proc = subprocess.run(
        [sys.executable, "-X", "utf8", str(EDIT_GATE)],
        cwd=str(repo),
        env=merged_env,
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
        check=False,
    )
    assert proc.returncode == 0, f"edit_gate exited {proc.returncode}: {proc.stderr}"
    raw = proc.stdout.strip()
    return json.loads(raw) if raw else {}


def _is_denied(out: dict) -> tuple[bool, str]:
    hook_out = out.get("hookSpecificOutput")
    if isinstance(hook_out, dict):
        return (
            hook_out.get("permissionDecision") == "deny",
            str(hook_out.get("permissionDecisionReason") or ""),
        )
    return (
        out.get("decision") == "deny",
        str(out.get("reason") or ""),
    )


class P1ZeroDowngradeGateTest(unittest.TestCase):
    def test_blocks_source_edit_for_escalate_on_code_edit_domains(self):
        for dom in ("research-rca", "pm-ba-content"):
            with self.subTest(domain_id=dom), tempfile.TemporaryDirectory() as td:
                repo = _setup_repo(Path(td), domain_id=dom, work_kind="build")
                out = _run_edit_gate(repo, "src/app.py")
                denied, reason = _is_denied(out)
                self.assertTrue(denied, f"{dom} must deny source edits: {out}")
                self.assertIn("TDQ:APPROVE", reason)
                self.assertIn("escalate-to-build", reason)

    def test_blocks_legacy_investigate_without_domain_id_and_agy_parity(self):
        with tempfile.TemporaryDirectory() as td:
            repo = _setup_repo(Path(td), domain_id=None, work_kind="investigate")
            for agy_mode in (False, True):
                out = _run_edit_gate(repo, "src/app.py", agy=agy_mode)
                denied, reason = _is_denied(out)
                self.assertTrue(denied, f"agy={agy_mode} must deny legacy investigate: {out}")
                self.assertIn("TDQ:APPROVE", reason)
                self.assertIn("escalate-to-build", reason)

    def test_allows_docs_edit_even_when_domain_locked(self):
        with tempfile.TemporaryDirectory() as td:
            repo = _setup_repo(Path(td), domain_id="research-rca", work_kind="investigate")
            out = _run_edit_gate(repo, "docs/tdq/research/note.md")
            denied, _reason = _is_denied(out)
            self.assertFalse(denied, f"docs/** edits must remain allowed: {out}")

    def test_escalate_to_build_unlocks_edits_and_locks_downgrade(self):
        with tempfile.TemporaryDirectory() as td:
            repo = _setup_repo(Path(td), domain_id="research-rca", work_kind="investigate")
            esc = _run_cmd(
                [str(TDQ_STATE), "escalate-to-build", "--by", "fix bug", "--inline-fix"],
                cwd=repo,
            )
            self.assertEqual(esc.returncode, 0, esc.stderr or esc.stdout)
            state = json.loads((repo / "docs" / "tdq" / "state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["work_kind"], "build")
            self.assertEqual(state["domain_id"], "code-build")
            self.assertTrue(state["downgrade_locked"])

            out = _run_edit_gate(repo, "src/app.py")
            denied, _reason = _is_denied(out)
            self.assertFalse(denied, f"Escalated code-build must allow src edits: {out}")

            down_dom = _run_cmd([str(TDQ_STATE), "set", "domain_id=research-rca"], cwd=repo)
            self.assertNotEqual(down_dom.returncode, 0)
            down_wk = _run_cmd([str(TDQ_STATE), "set", "work_kind=investigate"], cwd=repo)
            self.assertNotEqual(down_wk.returncode, 0)

    def test_zero_downgrade_kill_switch_env_and_config_allow_edits(self):
        with tempfile.TemporaryDirectory() as td:
            repo = _setup_repo(Path(td), domain_id="research-rca", work_kind="investigate")
            out_env = _run_edit_gate(repo, "src/app.py", env={"TDQ_ZERO_DOWNGRADE_ENABLED": "0"})
            denied_env, _ = _is_denied(out_env)
            self.assertFalse(denied_env, f"TDQ_ZERO_DOWNGRADE_ENABLED=0 should bypass: {out_env}")

            (repo / "docs" / "tdq" / "config.json").write_text(
                json.dumps({"p1": {"zero_downgrade_enabled": False}}),
                encoding="utf-8",
            )
            out_cfg = _run_edit_gate(repo, "src/app.py")
            denied_cfg, _ = _is_denied(out_cfg)
            self.assertFalse(denied_cfg, f"p1.zero_downgrade_enabled=false should bypass: {out_cfg}")

    def test_intake_skill_contains_p1_router_pointers(self):
        text = (ROOT / "skills" / "tdq-intake" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("tdq_domains.py", text)
        self.assertIn("skill_router.py", text)
        self.assertLessEqual(len(text.splitlines()), 148)


if __name__ == "__main__":
    unittest.main()
