"""Latency benchmark: measure and compare execution time between Rust binary and Python hook."""
import json
import os
import statistics
import subprocess
import sys
import time
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
PLUGIN_DIR = REPO_ROOT / "plugins" / "tdq-workflow-agy"
RUST_BIN = PLUGIN_DIR / "bin" / ("tdq-dispatch.exe" if os.name == "nt" else "tdq-dispatch")
PYTHON_DISPATCH = PLUGIN_DIR / "hooks" / "scripts" / "dispatch.py"


def _measure_command_latencies(cmd: list[str], runs: int = 30) -> list[float]:
    latencies = []
    kw = {
        "input": "{}",
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "text": True,
        "cwd": str(REPO_ROOT),
        "timeout": 10,
    }
    if os.name == "nt":
        kw["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)

    # Warmup 3 runs
    for _ in range(3):
        subprocess.run(cmd, **kw)

    # Measure runs
    for _ in range(runs):
        start = time.perf_counter()
        proc = subprocess.run(cmd, **kw)
        end = time.perf_counter()
        assert proc.returncode == 0
        latencies.append((end - start) * 1000.0)  # ms

    return latencies


def test_measure_hook_latency():
    assert RUST_BIN.is_file(), f"Rust binary not found at {RUST_BIN}"
    assert PYTHON_DISPATCH.is_file(), f"Python dispatch not found at {PYTHON_DISPATCH}"

    runs = 30

    # 1. Rust direct
    rust_cmd = [str(RUST_BIN), "--event", "SessionStart"]
    rust_latencies = _measure_command_latencies(rust_cmd, runs=runs)

    # 2. Rust via shell / cmd wrapper
    if os.name == "nt":
        rust_shell_cmd = ["cmd.exe", "/c", str(RUST_BIN), "--event", "SessionStart"]
    else:
        rust_shell_cmd = ["sh", "-c", f"{RUST_BIN} --event SessionStart"]
    rust_shell_latencies = _measure_command_latencies(rust_shell_cmd, runs=runs)

    # 3. Python direct
    py_cmd = [sys.executable, "-X", "utf8", str(PYTHON_DISPATCH), "--event", "SessionStart"]
    py_latencies = _measure_command_latencies(py_cmd, runs=runs)

    # 4. Python via shell / cmd wrapper
    if os.name == "nt":
        py_shell_cmd = ["cmd.exe", "/c", sys.executable, "-X", "utf8", str(PYTHON_DISPATCH), "--event", "SessionStart"]
    else:
        py_shell_cmd = ["sh", "-c", f"{sys.executable} -X utf8 {PYTHON_DISPATCH} --event SessionStart"]
    py_shell_latencies = _measure_command_latencies(py_shell_cmd, runs=runs)

    # Compute statistics
    r_med = statistics.median(rust_latencies)
    r_shell_med = statistics.median(rust_shell_latencies)
    py_med = statistics.median(py_latencies)
    py_shell_med = statistics.median(py_shell_latencies)

    r_p95 = sorted(rust_latencies)[int(runs * 0.95)]
    r_shell_p95 = sorted(rust_shell_latencies)[int(runs * 0.95)]
    py_p95 = sorted(py_latencies)[int(runs * 0.95)]
    py_shell_p95 = sorted(py_shell_latencies)[int(runs * 0.95)]

    speedup_direct = py_med / r_med if r_med > 0 else 0
    speedup_shell = py_shell_med / r_shell_med if r_shell_med > 0 else 0

    print("\n" + "=" * 65)
    print("           TDQ HOOK DISPATCH LATENCY BENCHMARK REPORT          ")
    print("=" * 65)
    print(f"Sample size: {runs} iterations per configuration")
    print("-" * 65)
    print(f"{'Engine & Mode':<30} | {'Median (ms)':<12} | {'P95 (ms)':<10}")
    print("-" * 65)
    print(f"{'Rust Binary (Direct)':<30} | {r_med:>11.2f} | {r_p95:>9.2f}")
    print(f"{'Rust Binary (cmd /c wrapper)':<30} | {r_shell_med:>11.2f} | {r_shell_p95:>9.2f}")
    print(f"{'Python Dispatch (Direct)':<30} | {py_med:>11.2f} | {py_p95:>9.2f}")
    print(f"{'Python Dispatch (cmd /c)':<30} | {py_shell_med:>11.2f} | {py_shell_p95:>9.2f}")
    print("-" * 65)
    print(f"Speedup Direct: {speedup_direct:.1f}x faster")
    print(f"Speedup Shell Wrapper: {speedup_shell:.1f}x faster")
    print("=" * 65)

    # Verify significant speedup and soft target
    assert r_med < py_med, f"Rust ({r_med:.2f} ms) must be faster than Python ({py_med:.2f} ms)"
    assert r_shell_med < py_shell_med, f"Rust shell ({r_shell_med:.2f} ms) must be faster than Python shell ({py_shell_med:.2f} ms)"
    assert r_med <= 25.0, f"Rust direct median {r_med:.2f} ms exceeds 25 ms soft target"
