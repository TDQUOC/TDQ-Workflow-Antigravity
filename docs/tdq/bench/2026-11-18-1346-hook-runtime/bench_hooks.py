"""Benchmark wall-clock latency of installed TDQ Antigravity hooks."""
import argparse
import glob
import json
import os
import statistics
import subprocess
import sys
import time
from pathlib import Path

DEFAULT_PLUGIN_DIR = Path(r"~\.gemini\config\plugins\tdq-workflow-agy").expanduser()
DEFAULT_PROJECT_DIR = Path(__file__).resolve().parents[4]
BENCH_SESSION_ID = "bench-hook-latency"


def build_payload(project_dir: str, event: str, tool: str | None = None,
                  tool_input: dict | None = None) -> bytes:
    """Build an Antigravity-shaped JSON payload for hook stdin."""
    data = {
        "workingDirectory": project_dir,
        "cwd": project_dir,
        "session_id": BENCH_SESSION_ID,
        "conversationId": BENCH_SESSION_ID,
        "hook_event_name": event,
    }
    if tool:
        data["toolName"] = tool
        data["toolInput"] = tool_input or {}
    return json.dumps(data).encode("utf-8")


def build_cases(project_dir: str) -> list[tuple[str, list[str] | str, tuple | None]]:
    """Return benchmark scenarios matching installed hooks.json matchers."""
    return [
        ("baseline py -3 -c pass", ["py", "-3", "-X", "utf8", "-c", "pass"], None),
        ("baseline python.exe -c pass", [sys.executable, "-X", "utf8", "-c", "pass"], None),
        ("PreInvocation prompt_context", "prompt_context.py", ("PreInvocation", None, None)),
        ("PreInvocation search_observe", "search_observe.py", ("PreInvocation", None, None)),
        ("PreToolUse read_gate", "read_gate.py",
         ("PreToolUse", "read_file", {"Path": os.path.join(project_dir, "README.md")})),
        ("PreToolUse edit_gate", "edit_gate.py",
         ("PreToolUse", "edit_file", {
             "Path": os.path.join(project_dir, "docs", "tdq", "brief", "x.md"),
             "Target": "a", "Replacement": "b",
         })),
        ("PreToolUse command_gate", "command_gate.py",
         ("PreToolUse", "run_command", {"CommandLine": "git status --short"})),
        ("PreToolUse search_gate", "search_gate.py",
         ("PreToolUse", "grep_search", {"Query": "foo", "SearchPath": project_dir})),
        ("PreToolUse lsp_gate (call_mcp_tool)", "lsp_gate.py",
         ("PreToolUse", "call_mcp_tool",
          {"ServerName": "chrome-devtools", "ToolName": "list_pages", "Arguments": {}})),
        ("PreToolUse search_observe (call_mcp_tool)", "search_observe.py",
         ("PreToolUse", "call_mcp_tool",
          {"ServerName": "chrome-devtools", "ToolName": "list_pages", "Arguments": {}})),
        ("PostToolUse search_observe (run_command)", "search_observe.py",
         ("PostToolUse", "run_command", {"CommandLine": "git status"})),
        ("PostInvocation post_invocation", "post_invocation.py", ("PostInvocation", None, None)),
        ("Stop stop_gate", "stop_gate.py", ("Stop", None, None)),
    ]


def cleanup_bench_artifacts(project_dir: str) -> None:
    """Remove per-session runtime scratch files created during benchmarking."""
    pattern = os.path.join(project_dir, "docs", "tdq", ".tdq-runtime", f"*{BENCH_SESSION_ID}*")
    for path in glob.glob(pattern):
        try:
            os.remove(path)
        except OSError:
            pass


def run_benchmark(n_runs: int, plugin_dir: Path, project_dir: Path) -> dict:
    """Run all hook latency cases n_runs times and return summary metrics."""
    proj_str = str(project_dir)
    env = dict(os.environ, TDQ_LOG="0")
    results = []
    try:
        for name, target, pl in build_cases(proj_str):
            if isinstance(target, str):
                argv = ["py", "-3", "-X", "utf8",
                        os.path.join("hooks", "scripts", target), "--event", pl[0]]
                stdin_bytes = build_payload(proj_str, *pl)
            else:
                argv = target
                stdin_bytes = b""
            timings_ms = []
            last_proc = None
            for _ in range(n_runs):
                t0 = time.perf_counter()
                last_proc = subprocess.run(
                    argv, input=stdin_bytes, cwd=str(plugin_dir),
                    capture_output=True, env=env,
                )
                timings_ms.append((time.perf_counter() - t0) * 1000.0)
            timings_ms.sort()
            p90_idx = max(0, int(len(timings_ms) * 0.9) - 1)
            results.append({
                "name": name,
                "n": n_runs,
                "median_ms": round(statistics.median(timings_ms), 2),
                "p90_ms": round(timings_ms[p90_idx], 2),
                "min_ms": round(timings_ms[0], 2),
                "max_ms": round(timings_ms[-1], 2),
                "rc": last_proc.returncode if last_proc else -1,
                "stdout_bytes": len(last_proc.stdout) if last_proc else 0,
            })
    finally:
        cleanup_bench_artifacts(proj_str)
    return {
        "schema": "tdq-hook-bench/v1",
        "plugin_dir": str(plugin_dir),
        "project_dir": proj_str,
        "n_runs": n_runs,
        "cases": results,
    }


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description="Benchmark installed TDQ Antigravity hooks.")
    parser.add_argument("--n", type=int, default=12, help="Iterations per case (default 12).")
    parser.add_argument("--plugin-dir", default=str(DEFAULT_PLUGIN_DIR))
    parser.add_argument("--project-dir", default=str(DEFAULT_PROJECT_DIR))
    parser.add_argument("--json", dest="json_out", help="Write JSON output to file.")
    args = parser.parse_args(argv)

    report = run_benchmark(args.n, Path(args.plugin_dir), Path(args.project_dir))
    for row in report["cases"]:
        print(f"{row['name']:45s} median={row['median_ms']:7.1f}ms "
              f"p90={row['p90_ms']:7.1f}ms rc={row['rc']} stdout={row['stdout_bytes']}B")
    if args.json_out:
        out_path = Path(args.json_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
