"""Benchmark git commit/merge workflow on a 200-file temp repo: git only vs TDQ hooks."""
import argparse
from datetime import datetime
import glob
import json
import os
from pathlib import Path
import shutil
import stat
import statistics
import subprocess
import sys
import tempfile
import time

DEFAULT_PLUGIN_DIR = Path(r"~\.gemini\config\plugins\tdq-workflow-agy").expanduser()
DEFAULT_PROJECT_DIR = Path(__file__).resolve().parents[4]
SESSION_ID = "bench-commit-trial"
DEFAULT_N = 5
DEFAULT_FILES = 200
GIT_IDENTITY = ("-c", "user.name=Bench", "-c", "user.email=bench@local")


def _log(message: str) -> None:
    """Emit an ISO-timestamped log line to stderr unless TDQ_LOG=0."""
    if os.environ.get("TDQ_LOG", "1") != "0":
        stamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        print(f"[{stamp}] commit_merge_trial: {message}", file=sys.stderr)


def _force_remove_readonly(func, path: str, _exc_info) -> None:
    """Clear read-only bits on Windows .git objects before retrying deletion."""
    os.chmod(path, stat.S_IWRITE)
    func(path)


def _rmtree_force(path: Path) -> None:
    """Remove a directory tree cleanly, handling read-only git files on Windows."""
    if not path.exists():
        return
    if sys.version_info >= (3, 12):
        shutil.rmtree(path, onexc=_force_remove_readonly)
    else:
        shutil.rmtree(path, onerror=_force_remove_readonly)


def build_payload(repo_dir: Path, event: str, command: str) -> bytes:
    """Build an Antigravity-shaped hook payload for a run_command call."""
    repo_str = str(repo_dir)
    payload = {
        "workingDirectory": repo_str,
        "cwd": repo_str,
        "session_id": SESSION_ID,
        "conversationId": SESSION_ID,
        "hook_event_name": event,
        "toolName": "run_command",
        "toolInput": {"CommandLine": command},
    }
    return json.dumps(payload).encode("utf-8")


def run_git(repo_dir: Path, git_args: list[str]) -> float:
    """Execute one git command with local bench identity and return elapsed ms."""
    argv = ["git", *GIT_IDENTITY, *git_args]
    t0 = time.perf_counter()
    proc = subprocess.run(argv, cwd=str(repo_dir), capture_output=True, text=True)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    if proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(git_args)} failed ({proc.returncode}): {proc.stderr}")
    return elapsed_ms


def run_hook(plugin_dir: Path, script_name: str, event: str,
             repo_dir: Path, command: str, env: dict[str, str]) -> float:
    """Spawn an installed TDQ hook script and return elapsed wall-clock ms."""
    argv = [
        "py", "-3", "-X", "utf8",
        os.path.join("hooks", "scripts", script_name),
        "--event", event,
    ]
    stdin_bytes = build_payload(repo_dir, event, command)
    t0 = time.perf_counter()
    proc = subprocess.run(argv, input=stdin_bytes, cwd=str(plugin_dir),
                          capture_output=True, env=env)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    if proc.returncode != 0:
        raise RuntimeError(f"{script_name} failed ({proc.returncode}): {proc.stderr.decode('utf-8', 'replace')}")
    return elapsed_ms


def populate_files(repo_dir: Path, file_count: int) -> None:
    """Create file_count synthetic source files across subdirectories."""
    src_dir = repo_dir / "src"
    src_dir.mkdir(parents=True, exist_ok=True)
    body = "\n".join(f"line_{i} = {i}" for i in range(20)) + "\n"
    for idx in range(file_count):
        sub = src_dir / f"pkg_{idx // 25:02d}"
        sub.mkdir(exist_ok=True)
        (sub / f"mod_{idx:03d}.py").write_text(f"# module {idx}\n{body}", encoding="utf-8")


def mutate_branch_files(repo_dir: Path, count: int = 10) -> None:
    """Modify a small slice of files on the feature branch before merging."""
    src_dir = repo_dir / "src" / "pkg_00"
    for idx in range(count):
        target = src_dir / f"mod_{idx:03d}.py"
        if target.exists():
            target.write_text(target.read_text(encoding="utf-8") + "# branch edit\n",
                              encoding="utf-8")


def setup_temp_repo(base_dir: Path, file_count: int) -> Path:
    """Create a fresh temporary git repository with an initial commit and untracked files."""
    repo_dir = base_dir / "repo"
    repo_dir.mkdir(parents=True, exist_ok=True)
    run_git(repo_dir, ["init"])
    run_git(repo_dir, ["branch", "-M", "main"])
    (repo_dir / "README.md").write_text("# Bench Repo\n", encoding="utf-8")
    run_git(repo_dir, ["add", "README.md"])
    run_git(repo_dir, ["commit", "-m", "chore: initial commit"])
    populate_files(repo_dir, file_count)
    return repo_dir


def trial_steps() -> list[tuple[str, list[str], bool]]:
    """Return ordered git steps for a commit/branch/merge workflow."""
    return [
        ("git_add_all", ["add", "-A"], False),
        ("git_commit_all", ["commit", "-m", "feat: add 200 files"], False),
        ("git_switch_c", ["switch", "-c", "feat/trial-branch"], True),
        ("git_add_branch", ["add", "-A"], False),
        ("git_commit_branch", ["commit", "-m", "feat: update branch files"], False),
        ("git_switch_main", ["switch", "main"], False),
        ("git_merge_no_ff", ["merge", "--no-ff", "feat/trial-branch", "-m", "merge feat/trial-branch"], False),
    ]


def run_single_trial(plugin_dir: Path, with_pre: bool, with_post: bool,
                     file_count: int, env: dict[str, str]) -> dict:
    """Run one end-to-end commit/merge trial in an isolated temporary directory."""
    tmp_root = Path(tempfile.mkdtemp(prefix="tdq-commit-trial-"))
    try:
        repo_dir = setup_temp_repo(tmp_root, file_count)
        git_total = 0.0
        pre_total = 0.0
        post_total = 0.0
        step_ms: dict[str, float] = {}
        for name, git_args, do_mutate in trial_steps():
            cmd_str = "git " + " ".join(GIT_IDENTITY + tuple(git_args))
            pre_ms = run_hook(plugin_dir, "command_gate.py", "PreToolUse",
                              repo_dir, cmd_str, env) if with_pre else 0.0
            git_ms = run_git(repo_dir, git_args)
            post_ms = run_hook(plugin_dir, "search_observe.py", "PostToolUse",
                               repo_dir, cmd_str, env) if with_post else 0.0
            if do_mutate:
                mutate_branch_files(repo_dir)
            git_total += git_ms
            pre_total += pre_ms
            post_total += post_ms
            step_ms[name] = round(pre_ms + git_ms + post_ms, 2)
        return {
            "total_ms": git_total + pre_total + post_total,
            "git_ms": git_total,
            "pre_hook_ms": pre_total,
            "post_hook_ms": post_total,
            "steps_ms": step_ms,
        }
    finally:
        _rmtree_force(tmp_root)


def summarize_trials(trials: list[dict], baseline_median_ms: float | None = None) -> dict:
    """Compute median/p90/min/max and per-step medians across trial runs."""
    totals = sorted(t["total_ms"] for t in trials)
    p90_idx = max(0, int(len(totals) * 0.9) - 1)
    median_ms = round(statistics.median(totals), 2)
    step_names = list(trials[0]["steps_ms"].keys())
    per_step = {
        name: round(statistics.median(t["steps_ms"][name] for t in trials), 2)
        for name in step_names
    }
    summary = {
        "median_ms": median_ms,
        "p90_ms": round(totals[p90_idx], 2),
        "min_ms": round(totals[0], 2),
        "max_ms": round(totals[-1], 2),
        "git_median_ms": round(statistics.median(t["git_ms"] for t in trials), 2),
        "pre_hook_median_ms": round(statistics.median(t["pre_hook_ms"] for t in trials), 2),
        "post_hook_median_ms": round(statistics.median(t["post_hook_ms"] for t in trials), 2),
        "per_step_median_ms": per_step,
    }
    if baseline_median_ms and baseline_median_ms > 0:
        overhead = round(median_ms - baseline_median_ms, 2)
        summary["hook_overhead_ms"] = overhead
        summary["hook_overhead_pct"] = round((overhead / baseline_median_ms) * 100.0, 1)
    return summary


def cleanup_bench_artifacts(project_dir: Path) -> None:
    """Remove any bench runtime scratch files from .tdq-runtime."""
    runtime_dir = project_dir / "docs" / "tdq" / ".tdq-runtime"
    for path in glob.glob(str(runtime_dir / "*bench*")):
        try:
            os.remove(path)
        except OSError:
            pass


def run_benchmark(n_runs: int, plugin_dir: Path, project_dir: Path, file_count: int) -> dict:
    """Run N paired commit/merge trials across git-only, PreToolUse, and Pre+Post hooks."""
    env = dict(os.environ, TDQ_LOG="0")
    env.pop("TDQ_PROJECT_DIR", None)
    git_only_runs: list[dict] = []
    pre_hook_runs: list[dict] = []
    full_hook_runs: list[dict] = []
    try:
        for idx in range(n_runs):
            _log(f"trial {idx + 1}/{n_runs}")
            git_only_runs.append(run_single_trial(plugin_dir, False, False, file_count, env))
            pre_hook_runs.append(run_single_trial(plugin_dir, True, False, file_count, env))
            full_hook_runs.append(run_single_trial(plugin_dir, True, True, file_count, env))
    finally:
        cleanup_bench_artifacts(project_dir)

    git_only_sum = summarize_trials(git_only_runs)
    base_ms = git_only_sum["median_ms"]
    return {
        "schema": "tdq-commit-merge-trial/v1",
        "n": n_runs,
        "file_count": file_count,
        "session_id": SESSION_ID,
        "plugin_dir": str(plugin_dir),
        "git_only": git_only_sum,
        "git_with_hook": summarize_trials(pre_hook_runs, baseline_median_ms=base_ms),
        "git_with_pre_and_post_hook": summarize_trials(full_hook_runs, baseline_median_ms=base_ms),
    }


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description="Benchmark git commit/merge vs TDQ command hooks.")
    parser.add_argument("--n", type=int, default=DEFAULT_N, help="Number of trials (default 5).")
    parser.add_argument("--files", type=int, default=DEFAULT_FILES, help="Files in temp repo (default 200).")
    parser.add_argument("--plugin-dir", default=str(DEFAULT_PLUGIN_DIR))
    parser.add_argument("--project-dir", default=str(DEFAULT_PROJECT_DIR))
    parser.add_argument("--json", dest="json_out", help="Write JSON output to file.")
    args = parser.parse_args(argv)

    if args.n < 1:
        parser.error("--n must be >= 1")
    report = run_benchmark(args.n, Path(args.plugin_dir), Path(args.project_dir), args.files)
    for key in ("git_only", "git_with_hook", "git_with_pre_and_post_hook"):
        row = report[key]
        print(f"{key:28s} median={row['median_ms']:7.1f}ms p90={row['p90_ms']:7.1f}ms")
    if args.json_out:
        out_path = Path(args.json_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
