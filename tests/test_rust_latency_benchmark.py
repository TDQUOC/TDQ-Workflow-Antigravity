"""Latency benchmark: measure real Hot-path, Cold-path, and weighted Hybrid latencies."""
import json
import os
import shlex
import statistics
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PLUGIN_DIR = REPO_ROOT / "plugins" / "tdq-workflow-agy"
RUST_BIN = PLUGIN_DIR / "bin" / ("tdq-dispatch.exe" if os.name == "nt" else "tdq-dispatch")
PYTHON_DISPATCH = PLUGIN_DIR / "hooks" / "scripts" / "dispatch.py"


def _shell_wrap(cmd: list[str]) -> list[str]:
    """Wrap command in native OS shell matching hooks.json invocation overhead."""
    if os.name == "nt":
        return ["cmd.exe", "/c", *cmd]
    return ["sh", "-c", shlex.join(cmd)]


def _setup_bench_env(tmp_path: Path) -> dict[str, str]:
    """Create isolated TDQ project state in tmp_path and return clean env."""
    plan_rel = "docs/tdq/plan/bench.md"
    plan_file = tmp_path / plan_rel
    plan_file.parent.mkdir(parents=True, exist_ok=True)
    plan_file.write_text("- [~] **T1.1** Active benchmark task — Test: `pytest`\n", encoding="utf-8")
    (tmp_path / "docs" / "tdq" / "state.json").write_text(
        json.dumps({
            "active_request": "2026-11-19-bench",
            "phase": "implement",
            "lane": "full",
            "spec_approved": True,
            "plan_approved": True,
            "plan_file": plan_rel,
        }),
        encoding="utf-8",
    )
    (tmp_path / "docs" / "tdq" / ".tdq-san-sang.json").write_text(
        json.dumps({"tang": {"lsp": {"san_sang": True}, "graphify": {"san_sang": True}}}),
        encoding="utf-8",
    )
    env = dict(os.environ)
    env.update({
        "TDQ_PROJECT_DIR": str(tmp_path),
        "PLUGIN_ROOT": str(PLUGIN_DIR),
        "TDQ_LOG": "0",
        "TDQ_KHOI_TAO_NEN": "0",
        "TDQ_KHONG_CHAM_MAY": "1",
        "TDQ_RTK": "0",
        "RTK_DISABLED": "1",
    })
    return env


def _measure_command_latencies(
    cmd: list[str],
    payload: dict,
    env: dict[str, str],
    cwd: Path,
    runs: int = 30,
) -> list[float]:
    """Execute cmd 3 warmup + runs timed iterations using real wall-clock perf_counter."""
    raw_input = json.dumps(payload, ensure_ascii=False)
    kw: dict[str, object] = {
        "input": raw_input,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "text": True,
        "encoding": "utf-8",
        "cwd": str(cwd),
        "env": env,
        "timeout": 10,
    }
    if os.name == "nt":
        kw["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)

    for _ in range(3):
        proc = subprocess.run(cmd, check=False, **kw)
        assert proc.returncode == 0

    latencies: list[float] = []
    for _ in range(runs):
        start = time.perf_counter()
        proc = subprocess.run(cmd, check=False, **kw)
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        assert proc.returncode == 0
        latencies.append(elapsed_ms)
    return latencies


def _summarize(latencies: list[float]) -> tuple[float, float]:
    """Return (median_ms, p95_ms) for measured latencies."""
    ordered = sorted(latencies)
    p95_idx = min(len(ordered) - 1, int(len(ordered) * 0.95))
    return statistics.median(ordered), ordered[p95_idx]


def test_measure_hook_latency(tmp_path: Path) -> None:
    """Measure Hot-path direct/shell, Cold-path shell, and weighted Hybrid latency (N=30)."""
    assert RUST_BIN.is_file(), f"Rust binary not found at {RUST_BIN}"
    assert PYTHON_DISPATCH.is_file(), f"Python dispatch not found at {PYTHON_DISPATCH}"

    runs = 30
    env = _setup_bench_env(tmp_path)
    hot_post_payload = {"cwd": str(tmp_path), "conversationId": "bench-hot"}
    hot_pre_payload = {
        "cwd": str(tmp_path),
        "conversationId": "bench-hot",
        "toolName": "edit_file",
        "toolInput": {"TargetFile": str(tmp_path / "docs" / "bench_note.md")},
    }
    cold_mid_payload = {
        "cwd": str(tmp_path),
        "conversationId": "bench-cold-mid",
        "toolName": "grep_search",
        "toolInput": {"Query": "T1", "SearchPath": str(tmp_path / "docs")},
    }
    cold_ss_payload = {"cwd": str(tmp_path), "conversationId": "bench-ss"}
    shell_noop_cmd = ["cmd.exe", "/c", "exit", "0"] if os.name == "nt" else ["sh", "-c", ":"]

    shell_only_lats = _measure_command_latencies(
        shell_noop_cmd, {}, env, tmp_path, runs=runs
    )
    post_direct = _measure_command_latencies(
        [str(RUST_BIN), "--event", "PostInvocation"], hot_post_payload, env, tmp_path, runs=runs
    )
    pre_direct = _measure_command_latencies(
        [str(RUST_BIN), "--event", "PreToolUse"], hot_pre_payload, env, tmp_path, runs=runs
    )
    post_shell = _measure_command_latencies(
        _shell_wrap([str(RUST_BIN), "--event", "PostInvocation"]),
        hot_post_payload,
        env,
        tmp_path,
        runs=runs,
    )
    pre_shell = _measure_command_latencies(
        _shell_wrap([str(RUST_BIN), "--event", "PreToolUse"]),
        hot_pre_payload,
        env,
        tmp_path,
        runs=runs,
    )
    cold_mid_shell_lats = _measure_command_latencies(
        _shell_wrap([str(RUST_BIN), "--event", "PreToolUse"]),
        cold_mid_payload,
        env,
        tmp_path,
        runs=runs,
    )
    cold_ss_shell_lats = _measure_command_latencies(
        _shell_wrap([str(RUST_BIN), "--event", "SessionStart"]),
        cold_ss_payload,
        env,
        tmp_path,
        runs=runs,
    )
    py_ss_shell_lats = _measure_command_latencies(
        _shell_wrap([sys.executable, "-X", "utf8", str(PYTHON_DISPATCH), "--event", "SessionStart"]),
        cold_ss_payload,
        env,
        tmp_path,
        runs=runs,
    )

    shell_only_med, shell_only_p95 = _summarize(shell_only_lats)
    hot_post_dir_med, hot_post_dir_p95 = _summarize(post_direct)
    hot_pre_dir_med, hot_pre_dir_p95 = _summarize(pre_direct)
    hot_direct, hot_direct_p95 = _summarize(post_direct + pre_direct)

    hot_post_sh_med, hot_post_sh_p95 = _summarize(post_shell)
    hot_pre_sh_med, hot_pre_sh_p95 = _summarize(pre_shell)
    hot_shell, hot_shell_p95 = _summarize(post_shell + pre_shell)

    cold_mid_shell, cold_mid_p95 = _summarize(cold_mid_shell_lats)
    cold_ss_shell, cold_ss_p95 = _summarize(cold_ss_shell_lats)
    py_ss_shell, py_ss_p95 = _summarize(py_ss_shell_lats)

    weighted_ms = 0.91 * hot_shell + 0.085 * cold_mid_shell + 0.005 * cold_ss_shell
    net_rust_ms = max(0.0, hot_shell - shell_only_med)
    speedup_shell = py_ss_shell / hot_shell if hot_shell > 0 else 0.0

    rows = [
        ("Shell Wrapper Only (cmd /c)", shell_only_med, shell_only_p95),
        ("Hot PostInvocation (Direct)", hot_post_dir_med, hot_post_dir_p95),
        ("Hot PreToolUse (Direct)", hot_pre_dir_med, hot_pre_dir_p95),
        ("Hot Combined (Direct)", hot_direct, hot_direct_p95),
        ("Hot PostInvocation (cmd /c)", hot_post_sh_med, hot_post_sh_p95),
        ("Hot PreToolUse (cmd /c)", hot_pre_sh_med, hot_pre_sh_p95),
        ("Hot Combined (cmd /c)", hot_shell, hot_shell_p95),
        ("Cold Mid-Turn grep (cmd /c)", cold_mid_shell, cold_mid_p95),
        ("Cold SessionStart (cmd /c)", cold_ss_shell, cold_ss_p95),
        ("Python SessionStart (cmd /c)", py_ss_shell, py_ss_p95),
    ]

    print("\n" + "=" * 68)
    print("       TDQ HYBRID HOOK DISPATCH LATENCY BENCHMARK REPORT            ")
    print("=" * 68)
    print(f"Sample size: {runs} timed runs per configuration (3 warmup runs)")
    print("-" * 68)
    print(f"{'Route & Mode':<34} | {'Median (ms)':<12} | {'P95 (ms)':<10}")
    print("-" * 68)
    for label, med, p95 in rows:
        print(f"{label:<34} | {med:>11.2f} | {p95:>9.2f}")
    print("-" * 68)
    print(f"Estimated Net Rust Core (Hot Shell - Shell Wrapper): {net_rust_ms:.2f} ms")
    print(f"Weighted Hybrid Latency (0.91*hot + 0.085*cold_mid + 0.005*cold_ss): {weighted_ms:.2f} ms")
    print(f"Hot-path Shell Speedup vs Python SessionStart: {speedup_shell:.1f}x faster")
    print("=" * 68)

    assert hot_direct <= 25.0, f"Hot direct median {hot_direct:.2f} ms exceeds 25.0 ms"
    assert hot_shell <= 32.0, f"Hot shell median {hot_shell:.2f} ms exceeds 32.0 ms"
    assert hot_shell < cold_mid_shell, f"Hot shell ({hot_shell:.2f}) must beat Cold mid ({cold_mid_shell:.2f})"
    assert hot_shell < py_ss_shell, f"Hot shell ({hot_shell:.2f}) must beat Python ({py_ss_shell:.2f})"
    assert weighted_ms <= 40.0, f"Weighted latency {weighted_ms:.2f} ms exceeds 40.0 ms budget"
