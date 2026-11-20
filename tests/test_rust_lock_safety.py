"""Concurrency and lock safety test: verify sidecar lock prevents ERROR_LOCK_VIOLATION under load."""
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PLUGIN_DIR = REPO_ROOT / "plugins" / "tdq-workflow-agy"
RUST_BIN = PLUGIN_DIR / "bin" / ("tdq-dispatch.exe" if os.name == "nt" else "tdq-dispatch")


def test_concurrent_sidecar_locks():
    assert RUST_BIN.is_file(), f"Rust binary not found at {RUST_BIN}"

    # Create temporary isolated workspace
    temp_dir = Path(tempfile.mkdtemp(prefix="tdq_lock_test_"))
    try:
        docs_dir = temp_dir / "docs" / "tdq"
        docs_dir.mkdir(parents=True, exist_ok=True)
        (docs_dir / "state.json").write_text(
            json.dumps({"active_request": "lock-test", "phase": "implement"}),
            encoding="utf-8",
        )

        num_processes = 20
        processes = []
        payload = {
            "sessionId": "lock-session-42",
            "toolName": "mcp__lsp__find_symbol",
            "arguments": {"query": "concurrent_lock_check"},
        }
        input_data = json.dumps(payload, ensure_ascii=False)

        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000) if os.name == "nt" else 0

        # Launch 20 concurrent processes
        for _ in range(num_processes):
            p = subprocess.Popen(
                [str(RUST_BIN), "--event", "PostToolUse"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                cwd=str(temp_dir),
                creationflags=creationflags,
            )
            processes.append(p)

        # Send input and wait for completion
        stderrs = []
        for idx, p in enumerate(processes):
            stdout_data, stderr_data = p.communicate(input=input_data, timeout=15)
            assert p.returncode == 0, f"Process {idx} failed with code {p.returncode}: {stderr_data}"
            stderrs.append(stderr_data)

        # Verify no lock violations in stderr
        for idx, err in enumerate(stderrs):
            assert "os error 33" not in err, f"Process {idx} experienced ERROR_LOCK_VIOLATION: {err}"
            assert "LOCK_VIOLATION" not in err, f"Process {idx} experienced LOCK_VIOLATION: {err}"

        # Verify canonical Q2 output ledger integrity without creating root .tdq-runtime
        assert not (temp_dir / ".tdq-runtime").exists(), "Legacy root .tdq-runtime must not be created"
        assert not (docs_dir / ".tdq-read.jsonl").exists(), "PostToolUse(read_file) must not pollute .tdq-read.jsonl"
        search_ledger = docs_dir / ".tdq-search.jsonl"
        assert search_ledger.is_file(), "Search ledger docs/tdq/.tdq-search.jsonl was not created"

        lines = [line.strip() for line in search_ledger.read_text(encoding="utf-8").splitlines() if line.strip()]
        assert len(lines) == num_processes, f"Expected {num_processes} lines in .tdq-search.jsonl, got {len(lines)}"
        for line in lines:
            parsed = json.loads(line)
            assert parsed.get("cong_cu") == "lsp:find_symbol"
            assert parsed.get("khoa") == "yc:lock-test"

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
