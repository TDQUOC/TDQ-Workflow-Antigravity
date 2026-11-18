"""Reproducible wall-clock latency benchmark for Antigravity hooks.json dispatch.py."""
import argparse
import glob
import json
import os
import statistics
import subprocess
import tempfile
import time
from pathlib import Path

DEFAULT_PLUGIN_DIR = Path(__file__).resolve().parents[4] / "plugins" / "tdq-workflow-agy"
DEFAULT_PROJECT_DIR = Path(__file__).resolve().parents[4]
BENCH_SESSION_ID = "bench-dispatch-r1-r3"


def _build_cases(project_dir: str, transcript_path: str) -> list[tuple[str, str, str | None, dict | None]]:
    """Return hook scenarios wired through plugins/tdq-workflow-agy/hooks.json."""
    return [
        ("PreInvocation (mid-turn 0-git)", "PreInvocation", None, None),
        ("PreToolUse read_file", "PreToolUse", "read_file", {"Path": os.path.join(project_dir, "README.md")}),
        ("PreToolUse edit_file", "PreToolUse", "edit_file", {
            "Path": os.path.join(project_dir, "docs", "tdq", "brief", "x.md"),
            "Target": "a", "Replacement": "b",
        }),
        ("PreToolUse run_command (echo)", "PreToolUse", "run_command", {"CommandLine": "echo ok"}),
        ("PreToolUse run_command (git status)", "PreToolUse", "run_command", {"CommandLine": "git status"}),
        ("PreToolUse grep_search", "PreToolUse", "grep_search", {"Query": "foo", "SearchPath": project_dir}),
        ("PreToolUse call_mcp_tool (lsp)", "PreToolUse", "call_mcp_tool", {
            "ServerName": "lsp", "ToolName": "start_lsp", "Arguments": {"root_dir": project_dir},
        }),
        ("PreToolUse invoke_subagent", "PreToolUse", "invoke_subagent", {
            "Role": "tdq-implementer", "Workspace": "branch", "Prompt": "TASK: X\nWORKTREE: C:/tmp/w",
        }),
        ("PostToolUse grep_search", "PostToolUse", "grep_search", {"Query": "foo", "SearchPath": project_dir}),
        ("PostInvocation", "PostInvocation", None, None),
        ("Stop", "Stop", None, None),
    ]


def _cleanup(project_dir: str) -> None:
    pattern = os.path.join(project_dir, "docs", "tdq", ".tdq-runtime", f"*{BENCH_SESSION_ID}*")
    for path in glob.glob(pattern):
        try:
            os.remove(path)
        except OSError:
            pass


def run_benchmark(n_runs: int, plugin_dir: Path, project_dir: Path) -> list[dict]:
    """Run all dispatch.py cases n_runs times after 1 warmup and print summary."""
    proj_str = str(project_dir)
    env = dict(os.environ, TDQ_LOG="0", TDQ_PROJECT_DIR=proj_str)
    rows: list[dict] = []
    try:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as td:
            tr = Path(td) / "transcript.jsonl"
            tr.write_text(
                json.dumps({
                    "step_index": 1,
                    "type": "USER_INPUT",
                    "created_at": "2026-11-18T21:00:00Z",
                    "content": "bench",
                }) + "\n",
                encoding="utf-8",
            )
            for name, ev, tool, args in _build_cases(proj_str, str(tr)):
                pl: dict = {
                    "cwd": proj_str,
                    "workingDirectory": proj_str,
                    "conversationId": BENCH_SESSION_ID,
                    "hookEventName": ev,
                    "transcriptPath": str(tr),
                }
                if tool:
                    pl["toolCall"] = {"name": tool, "args": args or {}}
                raw = json.dumps(pl).encode("utf-8")
                cmd = ["python", "-X", "utf8", "hooks/scripts/dispatch.py", "--event", ev]
                subprocess.run(cmd, input=raw, cwd=str(plugin_dir), capture_output=True, env=env, timeout=30)
                timings: list[float] = []
                last_rc = 0
                for _ in range(n_runs):
                    t0 = time.perf_counter()
                    proc = subprocess.run(cmd, input=raw, cwd=str(plugin_dir), capture_output=True, env=env, timeout=30)
                    timings.append((time.perf_counter() - t0) * 1000.0)
                    last_rc = proc.returncode
                timings.sort()
                p90 = timings[max(0, int(n_runs * 0.9) - 1)]
                med = statistics.median(timings)
                rows.append({"name": name, "median_ms": med, "p90_ms": p90, "rc": last_rc})
                print(f"{name:38s} median={med:6.1f}ms p90={p90:6.1f}ms rc={last_rc}")
    finally:
        _cleanup(proj_str)
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description="Benchmark compiled AGY dispatch.py hook latency.")
    ap.add_argument("--n", type=int, default=12)
    ap.add_argument("--plugin-dir", type=Path, default=DEFAULT_PLUGIN_DIR)
    ap.add_argument("--project-dir", type=Path, default=DEFAULT_PROJECT_DIR)
    args = ap.parse_args()
    run_benchmark(args.n, args.plugin_dir, args.project_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
