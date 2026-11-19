"""Differential testing: verify 1-1 behavioral parity between Rust binary and Python hook dispatcher."""
import json
import os
import subprocess
import sys
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
PLUGIN_DIR = REPO_ROOT / "plugins" / "tdq-workflow-agy"
RUST_BIN = PLUGIN_DIR / "bin" / ("tdq-dispatch.exe" if os.name == "nt" else "tdq-dispatch")
PYTHON_DISPATCH = PLUGIN_DIR / "hooks" / "scripts" / "dispatch.py"


def run_rust_hook(event: str, payload: dict) -> dict:
    assert RUST_BIN.is_file(), f"Rust binary not found at {RUST_BIN}"
    cmd = [str(RUST_BIN), "--event", event]
    kw = {
        "input": json.dumps(payload, ensure_ascii=False),
        "capture_output": True,
        "text": True,
        "encoding": "utf-8",
        "cwd": str(REPO_ROOT),
        "timeout": 10,
    }
    if os.name == "nt":
        kw["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
    proc = subprocess.run(cmd, **kw)
    assert proc.returncode == 0, f"Rust binary exited with {proc.returncode}: {proc.stderr}"
    out_lines = [l for l in proc.stdout.strip().splitlines() if l.strip().startswith("{")]
    assert out_lines, f"Rust binary produced no JSON output: {proc.stdout}"
    return json.loads(out_lines[-1])


def run_python_hook(event: str, payload: dict) -> dict:
    assert PYTHON_DISPATCH.is_file(), f"Python dispatch not found at {PYTHON_DISPATCH}"
    cmd = [sys.executable, "-X", "utf8", str(PYTHON_DISPATCH), "--event", event]
    kw = {
        "input": json.dumps(payload, ensure_ascii=False),
        "capture_output": True,
        "text": True,
        "encoding": "utf-8",
        "cwd": str(REPO_ROOT),
        "timeout": 10,
    }
    if os.name == "nt":
        kw["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
    proc = subprocess.run(cmd, **kw)
    assert proc.returncode == 0, f"Python dispatch exited with {proc.returncode}: {proc.stderr}"
    out_lines = [l for l in proc.stdout.strip().splitlines() if l.strip().startswith("{")]
    assert out_lines, f"Python dispatch produced no JSON output: {proc.stdout}"
    return json.loads(out_lines[-1])


def _extract_decision_kind(resp: dict) -> str:
    """Normalize Antigravity hook decision kind across formats."""
    if "decision" in resp:
        return str(resp["decision"]).lower()
    # Check Antigravity injectSteps or permissionDecision
    if "permissionDecision" in resp:
        return str(resp["permissionDecision"]).lower()
    return "allow"


CASES = [
    ("SessionStart", {}, "allow"),
    ("UserPromptSubmit", {"userPrompt": "Tiếp tục công việc"}, "allow"),
    ("PreToolUse", {"toolName": "run_command", "arguments": {"CommandLine": "git status"}}, "allow"),
    ("PreToolUse", {"toolName": "run_command", "arguments": {"CommandLine": "git push origin dev"}}, "deny"),
    ("PreToolUse", {"toolName": "run_command", "arguments": {"CommandLine": "git reset --hard HEAD~1"}}, "deny"),
    ("PreToolUse", {"toolName": "write_file", "arguments": {"Path": str(REPO_ROOT / "docs/tdq/state.json"), "Content": "{}"}}, "deny"),
    ("PostToolUse", {"toolName": "read_file", "arguments": {"Path": str(REPO_ROOT / "README.md")}}, "allow"),
    ("Notification", {"message": "background build complete"}, "allow"),
    ("Stop", {}, None),
]


@pytest.mark.parametrize("event,payload,expected_decision", CASES)
def test_differential_event_parity(event, payload, expected_decision):
    rust_res = run_rust_hook(event, payload)
    py_res = run_python_hook(event, payload)

    rust_dec = _extract_decision_kind(rust_res)
    py_dec = _extract_decision_kind(py_res)

    assert rust_dec == py_dec, f"Divergence detected: Rust={rust_dec} vs Python={py_dec}"
    if expected_decision is not None:
        assert rust_dec == expected_decision, f"Rust decision {rust_dec} != expected {expected_decision}"
        assert py_dec == expected_decision, f"Python decision {py_dec} != expected {expected_decision}"

    if expected_decision == "deny":
        # Both must include guidance or explanation
        rust_text = json.dumps(rust_res, ensure_ascii=False)
        py_text = json.dumps(py_res, ensure_ascii=False)
        assert "[TDQ:" in rust_text or "forbidden" in rust_text.lower()
        assert "[TDQ:" in py_text or "deny" in py_text.lower()


def test_rust_fallback_to_python():
    """Verify that setting TDQ_HOOK_ENGINE=python delegates to python dispatch."""
    env = dict(os.environ, TDQ_HOOK_ENGINE="python")
    cmd = [str(RUST_BIN), "--event", "SessionStart"]
    kw = {
        "input": "{}",
        "capture_output": True,
        "text": True,
        "encoding": "utf-8",
        "cwd": str(REPO_ROOT),
        "timeout": 10,
        "env": env,
    }
    if os.name == "nt":
        kw["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
    proc = subprocess.run(cmd, **kw)
    assert proc.returncode == 0
    out_lines = [l for l in proc.stdout.strip().splitlines() if l.strip().startswith("{")]
    assert out_lines
    res = json.loads(out_lines[-1])
    assert _extract_decision_kind(res) == "allow"
