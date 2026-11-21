#!/usr/bin/env python3
"""Auto Meta-Gate: aggregate doc_lint, i18n_check, token_budget, git & CLI checks into 1 line.

Usage:
    python3 scripts/tdq_meta_gate.py
    python3 scripts/tdq_meta_gate.py --files docs/tdq/spec/example.md
    python3 scripts/tdq_meta_gate.py --repo . --all --check-cli --git-msg-file .git/COMMIT_EDITMSG

Output:
    PASS: exactly one line `Auto Meta-Gate: PASS (<N>/<N> checks, <t:.2f>s)` and exit 0.
    FAIL: `Auto Meta-Gate: FAIL (<passed>/<total> checks, <t:.2f>s)` plus error lines and exit 1.

Env: TDQ_LOG=0 silences ISO-timestamped stderr logs (enabled by default).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import doc_lint
import i18n_check
import token_budget
import utf8_io  # noqa: F401 — imported for its side effect: stdout/stderr become UTF-8

I18N_DIRS = ("skills", "agents", "scripts")
CLI_DOC_DIRS = (os.path.join("docs", "tdq", "scenarios"), os.path.join("docs", "tdq", "bugs"))
CO_AUTHOR_RE = re.compile(r"(?im)^\s*Co-Authored-By\s*:")
SKIP_WALK_DIRS = {".git", "__pycache__", ".venv", "node_modules", ".ruff_cache"}


def _log(message: str) -> None:
    """Emit one ISO-timestamped log line to stderr unless TDQ_LOG=0."""
    if os.environ.get("TDQ_LOG", "1") != "0":
        stamp = datetime.now().astimezone().isoformat(timespec="seconds")
        print(f"[{stamp}] tdq_meta_gate: {message}", file=sys.stderr)


def _find_repo_root(repo: str | None) -> str:
    """Resolve the repository root from `--repo`, `TDQ_PROJECT_DIR`, `.git` ancestor, or cwd."""
    if repo is not None:
        return os.path.abspath(repo)
    env_dir = os.environ.get("TDQ_PROJECT_DIR")
    if env_dir:
        return os.path.abspath(env_dir)
    current = start = os.path.abspath(os.getcwd())
    while True:
        if os.path.exists(os.path.join(current, ".git")):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            return start
        current = parent


def _run_git(repo_root: str, args: list[str], text: bool = True):
    """Run a git command safely without opening a console window on Windows."""
    kw: dict = {"cwd": repo_root, "capture_output": True, "timeout": 15}
    if text:
        kw.update({"encoding": "utf-8", "errors": "replace", "text": True})
    if os.name == "nt":
        kw["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
    try:
        return subprocess.run(["git", "-c", "core.quotepath=false", *args], check=False, **kw)
    except (OSError, subprocess.SubprocessError):
        return None


def _parse_porcelain_z(raw: bytes, repo_root: str) -> list[str]:
    """Decode `git status --porcelain -z` output into existing absolute file paths."""
    entries = raw.decode("utf-8", errors="replace").split("\0")
    found: list[str] = []
    idx = 0
    while idx < len(entries):
        rec = entries[idx]
        idx += 1
        if len(rec) < 4:
            continue
        status_xy, rel_path = rec[:2], rec[3:]
        if status_xy[0] in ("R", "C") and idx < len(entries):
            idx += 1
        if status_xy.strip() == "D":
            continue
        abs_path = os.path.abspath(os.path.join(repo_root, rel_path))
        if os.path.isfile(abs_path):
            found.append(abs_path)
    return found


def _base_branch(repo_root: str) -> str | None:
    """Read `nhanh_goc` from `docs/tdq/state.json` when available."""
    state_path = os.path.join(repo_root, "docs", "tdq", "state.json")
    if not os.path.isfile(state_path):
        return None
    try:
        with open(state_path, encoding="utf-8") as fh:
            data = json.load(fh)
        val = data.get("nhanh_goc")
        return val.strip() if isinstance(val, str) and val.strip() else None
    except (OSError, ValueError, AttributeError):
        return None


def _git_changed_files(repo_root: str) -> list[str]:
    """Collect modified/untracked files via git status plus branch diff against `nhanh_goc`."""
    if not os.path.exists(os.path.join(repo_root, ".git")):
        return []
    found: set[str] = set()
    status = _run_git(repo_root, ["status", "--porcelain", "-z", "-u"], text=False)
    if status and status.returncode == 0:
        found.update(_parse_porcelain_z(status.stdout, repo_root))
    base = _base_branch(repo_root)
    if base:
        diff = _run_git(repo_root, ["diff", "--name-only", f"{base}...HEAD"])
        if diff and diff.returncode == 0:
            for rel in diff.stdout.splitlines():
                abs_path = os.path.abspath(os.path.join(repo_root, rel.strip()))
                if os.path.isfile(abs_path):
                    found.add(abs_path)
    return sorted(found)


def _walk_repo_targets(repo_root: str) -> list[str]:
    """Collect all lintable files under standard TDQ code/doc directories for `--all`."""
    roots = [os.path.join(repo_root, d) for d in (*I18N_DIRS, *CLI_DOC_DIRS)]
    collected: list[str] = []
    for base in roots:
        if not os.path.isdir(base):
            continue
        for dirpath, dirs, names in os.walk(base):
            dirs[:] = sorted(d for d in dirs if d not in SKIP_WALK_DIRS)
            for name in sorted(names):
                collected.append(os.path.join(dirpath, name))
    return sorted(set(collected))


def _resolve_target_files(
    files: list[str] | None, repo_root: str, run_all: bool
) -> tuple[list[str], list[str]]:
    """Resolve explicit `--files`, `--all` tree, or git-changed files; fail-closed on missing."""
    if files is None:
        return (_walk_repo_targets(repo_root) if run_all else _git_changed_files(repo_root)), []
    resolved: list[str] = []
    missing: list[str] = []
    for item in files:
        if os.path.exists(item):
            resolved.append(os.path.abspath(item))
            continue
        joined = os.path.abspath(os.path.join(repo_root, item))
        if os.path.exists(joined):
            resolved.append(joined)
        else:
            missing.append(f"not found: {item}")
    return sorted(set(resolved)), missing


def _under_subdir(abs_path: str, repo_root: str, subdir: str) -> bool:
    """Return True when `abs_path` lies inside `<repo_root>/<subdir>/` or `/<subdir>/`."""
    norm = os.path.abspath(abs_path).replace("\\", "/")
    root_prefix = os.path.abspath(repo_root).replace("\\", "/").rstrip("/") + f"/{subdir}/"
    return norm.startswith(root_prefix) or f"/{subdir}/" in norm


def _check_doc_lint(md_files: list[str]) -> tuple[str, bool, list[str]] | None:
    """Run `doc_lint.lint_file` over `.md` targets; skip when none are present."""
    if not md_files:
        _log("doc_lint: skip (no .md files)")
        return None
    errors: list[str] = []
    for path in md_files:
        errors.extend(doc_lint.lint_file(path))
    _log(f"doc_lint: checked {len(md_files)} file(s), errors={len(errors)}")
    return "doc_lint", not errors, errors


def _check_i18n(
    target_files: list[str], repo_root: str, run_all: bool
) -> tuple[str, bool, list[str]] | None:
    """Run `i18n_check.scan_file` on targets under `skills/`, `agents/`, or `scripts/`."""
    if run_all and not target_files:
        dirs = [os.path.join(repo_root, d) for d in I18N_DIRS if os.path.isdir(os.path.join(repo_root, d))]
        scan_files = i18n_check.collect(dirs) if dirs else []
    else:
        scan_files = [
            p for p in target_files
            if p.endswith(i18n_check.SCAN_SUFFIXES)
            and any(_under_subdir(p, repo_root, d) for d in I18N_DIRS)
        ]
    if not scan_files:
        _log("i18n_check: skip (no skills/agents/scripts files)")
        return None
    errors: list[str] = []
    for path in scan_files:
        for finding in i18n_check.scan_file(path):
            errors.append(f"{finding['file']}:{finding['line']}: [{finding['kind']}] {finding['text']}")
    _log(f"i18n_check: checked {len(scan_files)} file(s), errors={len(errors)}")
    return "i18n_check", not errors, errors


def _infer_skills_root(skill_files: list[str], fallback_root: str) -> str:
    """Infer enclosing project root from a path containing `/skills/`."""
    for path in skill_files:
        norm = os.path.abspath(path).replace("\\", "/")
        if "/skills/" in norm:
            return norm[:norm.index("/skills/")] or fallback_root
    return fallback_root


def _check_token_budget(
    target_files: list[str], repo_root: str, explicit_repo: bool, run_all: bool
) -> tuple[str, bool, list[str]] | None:
    """Run `token_budget.kiem_khoa` when `skills/` files are in scope or `--all` is set."""
    skill_files = [p for p in target_files if _under_subdir(p, repo_root, "skills")]
    if not run_all and not skill_files:
        _log("token_budget: skip (no skills/ files)")
        return None
    tb_root = repo_root if explicit_repo else _infer_skills_root(skill_files, repo_root)
    errors = token_budget.kiem_khoa(tb_root)
    _log(f"token_budget: checked root={tb_root}, errors={len(errors)}")
    return "token_budget", not errors, errors


def _collect_cli_doc_files(target_files: list[str], repo_root: str, check_cli: bool) -> list[str]:
    """Collect `.md` files under `docs/tdq/{scenarios,bugs}/` when relevant or `--check-cli`."""
    found = {
        p for p in target_files
        if p.endswith(".md") and (
            _under_subdir(p, repo_root, "docs/tdq/scenarios")
            or _under_subdir(p, repo_root, "docs/tdq/bugs")
        )
    }
    if check_cli:
        for rel_dir in CLI_DOC_DIRS:
            full_dir = os.path.join(repo_root, rel_dir)
            if os.path.isdir(full_dir):
                found.update(doc_lint.collect([full_dir]))
    return sorted(found)


def _check_cli_docs(
    target_files: list[str], repo_root: str, check_cli: bool
) -> tuple[str, bool, list[str]] | None:
    """Validate scenario/Bug Board CLI commands and flags via `doc_lint.validate_cli_flags`."""
    cli_docs = _collect_cli_doc_files(target_files, repo_root, check_cli)
    if not cli_docs:
        _log("cli_flags: skip (no scenario/bug files)")
        return None
    errors: list[str] = []
    for path in cli_docs:
        doc = doc_lint.Doc(path)
        errors.extend(doc_lint.validate_cli_flags(doc, repo_root=repo_root))
    _log(f"cli_flags: checked {len(cli_docs)} file(s), errors={len(errors)}")
    return "cli_flags", not errors, errors


def _check_co_authored_by(repo_root: str, git_msg_file: str | None) -> tuple[str, bool, list[str]]:
    """Reject `Co-Authored-By:` trailers in `--git-msg-file` or latest git HEAD commit."""
    errors: list[str] = []
    if git_msg_file is not None:
        msg_path = git_msg_file if os.path.exists(git_msg_file) else os.path.join(repo_root, git_msg_file)
        if not os.path.isfile(msg_path):
            return "git_co_author", False, [f"git message file not found: {git_msg_file}"]
        with open(msg_path, encoding="utf-8", errors="replace") as fh:
            for idx, line in enumerate(fh, start=1):
                if CO_AUTHOR_RE.search(line):
                    errors.append(f"{msg_path}:{idx}: forbidden Co-Authored-By trailer")
    elif os.path.exists(os.path.join(repo_root, ".git")):
        head = _run_git(repo_root, ["log", "-1", "--pretty=%B"])
        if head and head.returncode == 0 and CO_AUTHOR_RE.search(head.stdout):
            errors.append("HEAD commit message contains forbidden Co-Authored-By trailer")
    _log(f"git_co_author: errors={len(errors)}")
    return "git_co_author", not errors, errors


def _format_and_print(results: list[tuple[str, bool, list[str]]], elapsed: float) -> int:
    """Print the 1-line PASS summary or FAIL summary + error details; return 0/1."""
    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    all_ok = passed == total and total > 0
    if all_ok:
        print(f"Auto Meta-Gate: PASS ({passed}/{total} checks, {elapsed:.2f}s)")
        return 0
    print(f"Auto Meta-Gate: FAIL ({passed}/{total} checks, {elapsed:.2f}s)")
    for name, ok, errors in results:
        if ok:
            continue
        for err in errors:
            print(f"  [{name}] {err}")
    return 1


def run_meta_gate(
    files: list[str] | None = None,
    check_cli: bool = False,
    repo: str | None = None,
    run_all: bool = False,
    git_msg_file: str | None = None,
) -> int:
    """Run all applicable Meta-Gate checks fail-closed and return 0 on PASS, 1 on FAIL."""
    started = time.perf_counter()
    explicit_repo = repo is not None
    repo_root = _find_repo_root(repo)
    if explicit_repo and not os.path.isdir(repo_root):
        elapsed = time.perf_counter() - started
        _log(f"fail repo missing: {repo_root}")
        return _format_and_print([("input", False, [f"repo not found: {repo}"])], elapsed)

    target_files, missing_errors = _resolve_target_files(files, repo_root, run_all)
    if missing_errors:
        elapsed = time.perf_counter() - started
        _log(f"fail missing files: {len(missing_errors)}")
        return _format_and_print([("input", False, missing_errors)], elapsed)

    _log(f"start repo={repo_root} files={len(target_files)} all={run_all} check_cli={check_cli}")
    md_files = [p for p in target_files if p.endswith(".md")]
    candidates = [
        _check_doc_lint(md_files),
        _check_i18n(target_files, repo_root, run_all),
        _check_token_budget(target_files, repo_root, explicit_repo, run_all),
        _check_cli_docs(target_files, repo_root, check_cli),
        _check_co_authored_by(repo_root, git_msg_file),
    ]
    results = [item for item in candidates if item is not None]
    elapsed = time.perf_counter() - started
    rc = _format_and_print(results, elapsed)
    _log(f"done status={'PASS' if rc == 0 else 'FAIL'} checks={len(results)} elapsed={elapsed:.2f}s")
    return rc


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Build and parse CLI arguments for Auto Meta-Gate."""
    parser = argparse.ArgumentParser(
        prog="tdq_meta_gate.py",
        description="Run doc_lint, i18n_check, token_budget, git & CLI guards in one fail-closed gate.",
    )
    parser.add_argument("--repo", default=None, help="target repository root (default: auto-detect)")
    parser.add_argument("--files", nargs="*", default=None, help="explicit files to inspect")
    parser.add_argument("--all", action="store_true", help="enforce token_budget and i18n across repo")
    parser.add_argument("--check-cli", action="store_true", help="validate docs/tdq/{scenarios,bugs}/ CLI flags")
    parser.add_argument("--git-msg-file", default=None, help="commit message file to check for Co-Authored-By")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for `scripts/tdq_meta_gate.py`."""
    args = parse_args(argv)
    return run_meta_gate(
        files=args.files,
        check_cli=args.check_cli,
        repo=args.repo,
        run_all=args.all,
        git_msg_file=args.git_msg_file,
    )


if __name__ == "__main__":
    sys.exit(main())
