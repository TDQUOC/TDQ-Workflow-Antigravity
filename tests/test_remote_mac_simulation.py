"""Simulation tests on remote macOS Apple Silicon (ARM64) host via SSH."""
import json
import subprocess
import time
from pathlib import Path

SSH_HOST = "mbair"
REMOTE_BIN = "/Users/tdq/repo_pure/hooks/rust/tdq-dispatch/target/release/tdq-dispatch"


def run_remote_hook(event: str, payload: dict) -> dict:
    cmd = [
        "ssh",
        SSH_HOST,
        f"{REMOTE_BIN} --event {event}",
    ]
    proc = subprocess.run(
        cmd,
        input=json.dumps(payload, ensure_ascii=False),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=15,
    )
    assert proc.returncode == 0, f"Remote Mac binary failed: {proc.stderr}"
    out_lines = [l for l in proc.stdout.strip().splitlines() if l.strip().startswith("{")]
    assert out_lines, f"No JSON output from remote Mac: {proc.stdout} (stderr: {proc.stderr})"
    return json.loads(out_lines[-1])


def test_mac_simulation_all_events():
    # 1. SessionStart
    res = run_remote_hook("SessionStart", {})
    assert res.get("decision") == "allow"
    print("macOS SessionStart: PASS")

    # 2. UserPromptSubmit
    res = run_remote_hook("UserPromptSubmit", {"userPrompt": "Tiếp tục công việc"})
    assert res.get("decision") == "allow"
    print("macOS UserPromptSubmit: PASS")

    # 3. PreToolUse - normal command
    res = run_remote_hook("PreToolUse", {"toolName": "run_command", "arguments": {"CommandLine": "ls -la"}})
    assert res.get("decision") == "allow"
    print("macOS PreToolUse (normal command): PASS")

    # 4. PreToolUse - git push block
    res = run_remote_hook("PreToolUse", {"toolName": "run_command", "arguments": {"CommandLine": "git push origin dev"}})
    assert res.get("decision") == "deny"
    assert "TDQ:GIT" in json.dumps(res, ensure_ascii=False)
    print("macOS PreToolUse (git push block): PASS")

    # 5. PreToolUse - git reset --hard block
    res = run_remote_hook("PreToolUse", {"toolName": "run_command", "arguments": {"CommandLine": "git reset --hard HEAD~1"}})
    assert res.get("decision") == "deny"
    assert "TDQ:GIT" in json.dumps(res, ensure_ascii=False)
    print("macOS PreToolUse (git reset block): PASS")

    # 6. PreToolUse - state.json block
    res = run_remote_hook("PreToolUse", {"toolName": "write_file", "arguments": {"Path": "/Users/tdq/repo_pure/docs/tdq/state.json"}})
    assert res.get("decision") == "deny"
    assert "TDQ:STATE" in json.dumps(res, ensure_ascii=False)
    print("macOS PreToolUse (state.json block): PASS")

    # 7. PostToolUse
    res = run_remote_hook("PostToolUse", {"toolName": "read_file", "arguments": {"Path": "/etc/hosts"}})
    assert res.get("decision") == "allow"
    print("macOS PostToolUse: PASS")

    # 8. Notification
    res = run_remote_hook("Notification", {"message": "background build complete"})
    assert res.get("decision") == "allow"
    print("macOS Notification: PASS")

    # 9. Stop
    res = run_remote_hook("Stop", {})
    assert res.get("decision") in ("allow", "continue")
    print("macOS Stop: PASS")


def test_mac_benchmark():
    runs = 10
    latencies = []
    for _ in range(runs):
        t0 = time.perf_counter()
        res = run_remote_hook("SessionStart", {})
        t1 = time.perf_counter()
        assert res.get("decision") == "allow"
        latencies.append((t1 - t0) * 1000.0)

    import statistics
    med = statistics.median(latencies)
    print(f"\nmacOS Simulation Roundtrip Median Latency (over SSH): {med:.2f} ms")


if __name__ == "__main__":
    test_mac_simulation_all_events()
    test_mac_benchmark()
    print("\nALL MACOS ARM64 SIMULATION TESTS PASSED!")
