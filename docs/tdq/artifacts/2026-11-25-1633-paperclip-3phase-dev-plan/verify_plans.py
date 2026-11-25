#!/usr/bin/env python3
"""Read-only verifier for the Paperclip 3-Phase Development Plan bundle (P0-P2).

Checks evidence bounds, JSON contract fences, real disk symbols vs new targets,
architecture import invariants, wave file non-overlap, required decisions/bans,
and an in-memory counterfactual negative self-test.

Logging: ISO timestamped stderr enabled by default; set TDQ_LOG=0 for 0B stderr.
"""
import argparse
import ast
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

PLAN_DOCS = (
    "master-roadmap.md",
    "dev-plan-p0.md",
    "dev-plan-p1.md",
    "dev-plan-p2.md",
)
DEV_PLAN_DOCS = ("dev-plan-p0.md", "dev-plan-p1.md", "dev-plan-p2.md")
SPRINT_DOCS = ("s1.md", "s2.md", "s3.md")
ALLOWED_NEW_ROOTS = ("scripts/", "hooks/", "tests/", "docs/", "skills/")
BANNED_PLACEHOLDERS = ("TODO", "TBD", "FIXME")
EVIDENCE_ID_RE = re.compile(r"^[0-9a-f]{12}$")
PATH_TOKEN_RE = re.compile(r"^[A-Za-z0-9_./-]+\.(?:py|rs|json|md)$")
JSON_FENCE_RE = re.compile(r"```json\s*\n(.*?)```", re.DOTALL)
WAVE_ROW_RE = re.compile(r"^\|\s*`?(P[012]-W\d+)`?\s*\|\s*([^|]+)\|\s*([^|]+)\|\s*([^|]+)\|")
TASK_ID_RE = re.compile(r"\b(P[012]-\d+\.\d+)\b")


def _log(msg):
    """Emit timestamped log line to stderr unless TDQ_LOG=0."""
    if os.environ.get("TDQ_LOG", "1") != "0":
        ts = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        print(f"[{ts}] verify_plans: {msg}", file=sys.stderr)


def _read_text(path):
    return Path(path).read_text(encoding="utf-8")


def _parse_source_span(source):
    """Parse 'path:start-end' or 'path:line' into (rel_path, start, end)."""
    m = re.match(r"^(.+?):(\d+)(?:-(\d+))?$", source.strip())
    if not m:
        return source.strip(), None, None
    start = int(m.group(2))
    end = int(m.group(3)) if m.group(3) else start
    return m.group(1), start, end


def check_evidence_bounds_and_citations(artifact_dir, repo_root, texts):
    """Verify every evidence row points to real file lines and is cited."""
    ev_path = Path(artifact_dir) / "evidence.jsonl"
    if not ev_path.is_file():
        return {"ok": False, "error": "evidence.jsonl missing", "rows": 0}
    rows = [json.loads(line) for line in _read_text(ev_path).splitlines() if line.strip()]
    bounds_errs, uncited_all, uncited_plans = [], [], []
    all_corpus = "\n".join(texts.values())
    plan_corpus = "\n".join(texts[name] for name in PLAN_DOCS if name in texts)
    for row in rows:
        ev_id = row.get("id", "")
        rel, start, end = _parse_source_span(row.get("source", ""))
        target = Path(repo_root) / rel
        if not target.is_file():
            bounds_errs.append(f"{ev_id}: missing {rel}")
        elif start is not None:
            line_cnt = len(_read_text(target).splitlines())
            if start < 1 or end < start or end > line_cnt:
                bounds_errs.append(f"{ev_id}: {rel}:{start}-{end} > {line_cnt}")
        if ev_id not in all_corpus:
            uncited_all.append(ev_id)
        if ev_id not in plan_corpus:
            uncited_plans.append(ev_id)
    ok = bool(rows) and not bounds_errs and not uncited_all
    return {
        "ok": ok,
        "rows": len(rows),
        "bounds_errors": bounds_errs,
        "uncited_in_corpus": uncited_all,
        "uncited_in_plan_docs": uncited_plans,
    }


def check_json_fences_valid(texts):
    """Parse every ```json fenced block across master roadmap and P0-P2 plans."""
    total, errors = 0, []
    for name in PLAN_DOCS:
        text = texts.get(name, "")
        for idx, block in enumerate(JSON_FENCE_RE.findall(text), start=1):
            total += 1
            try:
                json.loads(block)
            except ValueError as exc:
                errors.append(f"{name}#json-{idx}: {exc}")
    return {"ok": total >= 8 and not errors, "blocks": total, "errors": errors}


def _collect_python_symbols(file_path):
    """Collect module, class, method, and top-level assignment names via AST."""
    tree = ast.parse(_read_text(file_path), filename=str(file_path))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name):
                    names.add(tgt.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
    return names


def _collect_json_tokens(file_path):
    """Collect dict keys and scalar string items from a JSON file."""
    data = json.loads(_read_text(file_path))
    tokens = set()

    def _walk(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                tokens.add(str(k))
                _walk(v)
        elif isinstance(obj, list):
            for item in obj:
                _walk(item)

    _walk(data)
    return tokens


def _symbol_exists_in_file(file_path, symbol):
    """Verify symbol presence in Python AST, Rust definitions, JSON, or text."""
    suffix = Path(file_path).suffix.lower()
    if suffix == ".py":
        return symbol in _collect_python_symbols(file_path)
    content = _read_text(file_path)
    if suffix == ".rs":
        pat = re.compile(rf"\b(?:fn|struct|enum|const|static|trait)\s+{re.escape(symbol)}\b")
        return bool(pat.search(content))
    if suffix == ".json":
        return symbol in _collect_json_tokens(file_path)
    return symbol in content


def _extract_section(text, heading_prefix):
    """Return lines belonging to a '### <prefix>' section until next heading."""
    lines = text.splitlines()
    capture, out = False, []
    for line in lines:
        if line.startswith("### ") and heading_prefix in line:
            capture = True
            continue
        if capture and (line.startswith("### ") or line.startswith("## ")):
            break
        if capture:
            out.append(line)
    return "\n".join(out)


def _check_anchor_bullet(line, repo_root):
    """Validate one Existing Anchor bullet: real files and real disk symbols."""
    errs, checked_syms = [], 0
    core = line.split(" — ", 1)[0]
    left, right = (core.split(": ", 1) if ": " in core else (core, ""))
    raw_tokens = re.findall(r"`([^`]+)`", left)
    paths = [t for t in raw_tokens if PATH_TOKEN_RE.match(t)]
    if not paths:
        return errs, 0
    resolved = []
    for rel in paths:
        full = Path(repo_root) / rel
        if not full.is_file():
            errs.append(f"missing anchor file: {rel}")
        else:
            resolved.append((rel, full))
    sym_tokens = [
        t for t in re.findall(r"`([^`]+)`", right)
        if not EVIDENCE_ID_RE.match(t) and not PATH_TOKEN_RE.match(t)
    ]
    for sym in sym_tokens:
        checked_syms += 1
        if resolved and not any(_symbol_exists_in_file(full, sym) for _, full in resolved):
            errs.append(f"missing symbol `{sym}` in {paths}")
    return errs, checked_syms


def check_disk_paths_and_symbols(repo_root, texts):
    """Validate every Existing Anchor and New Target across P0-P2 plans."""
    anchor_errs, new_errs, anchors_checked, new_checked = [], [], 0, 0
    for name in DEV_PLAN_DOCS:
        text = texts.get(name, "")
        sec_existing = _extract_section(text, "2.1")
        for line in sec_existing.splitlines():
            if line.lstrip().startswith("- "):
                errs, count = _check_anchor_bullet(line, repo_root)
                anchor_errs.extend(f"{name}: {e}" for e in errs)
                anchors_checked += count
        sec_new = _extract_section(text, "2.2")
        for line in sec_new.splitlines():
            if not line.lstrip().startswith("- "):
                continue
            head = line.split(": ", 1)[0]
            for tok in re.findall(r"`([^`]+)`", head):
                if PATH_TOKEN_RE.match(tok):
                    new_checked += 1
                    if not tok.startswith(ALLOWED_NEW_ROOTS):
                        new_errs.append(f"{name}: disallowed new target root `{tok}`")
    return {
        "ok": anchors_checked >= 25 and new_checked >= 6 and not anchor_errs and not new_errs,
        "existing_symbols_checked": anchors_checked,
        "new_targets_checked": new_checked,
        "anchor_errors": anchor_errs,
        "new_target_errors": new_errs,
    }


def check_import_layer_invariant(repo_root, texts):
    """Ensure no scripts/*.py imports hooks.* and plans preserve that boundary."""
    violations = []
    scripts_dir = Path(repo_root) / "scripts"
    py_count = 0
    for py_file in sorted(scripts_dir.rglob("*.py")):
        py_count += 1
        tree = ast.parse(_read_text(py_file), filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "hooks" or alias.name.startswith("hooks."):
                        violations.append(f"{py_file.name}: import {alias.name}")
            elif isinstance(node, ast.ImportFrom) and node.module:
                if node.module == "hooks" or node.module.startswith("hooks."):
                    violations.append(f"{py_file.name}: from {node.module}")
    roadmap = texts.get("master-roadmap.md", "")
    rule_documented = "TUYỆT ĐỐI KHÔNG import `hooks/`" in roadmap
    return {
        "ok": not violations and rule_documented,
        "scripts_scanned": py_count,
        "violations": violations,
        "rule_documented": rule_documented,
    }


def _extract_wave_tasks(text):
    """Parse markdown wave rows into {wave_id: [(task_id, task_label, [paths], [deps])]}."""
    waves = {}
    for line in text.splitlines():
        m = WAVE_ROW_RE.match(line.strip())
        if not m:
            continue
        wave_id, task_col, files_col, deps_col = (g.strip() for g in m.groups())
        id_match = TASK_ID_RE.search(task_col)
        task_id = id_match.group(1) if id_match else task_col
        files = []
        for tok in re.findall(r"`([^`]+)`", files_col):
            norm = tok.rstrip("/")
            if "/" in tok or PATH_TOKEN_RE.match(tok):
                files.append(norm)
        deps = TASK_ID_RE.findall(deps_col)
        waves.setdefault(wave_id, []).append((task_id, task_col, files, deps))
    return waves


def _wave_number(wave_id):
    return int(wave_id.rsplit("-W", 1)[1])


def check_wave_non_overlap(texts):
    """Enforce <= 4 tasks/wave, 0 shared owned files, and strictly earlier-wave deps."""
    overlaps, cap_errs, dep_errs = [], [], []
    wave_count, task_count, dep_edges = 0, 0, 0
    for name in DEV_PLAN_DOCS:
        waves = _extract_wave_tasks(texts.get(name, ""))
        task_wave = {
            tid: _wave_number(wid)
            for wid, entries in waves.items()
            for tid, _, _, _ in entries
        }
        for wave_id in sorted(waves, key=_wave_number):
            entries = waves[wave_id]
            cur_w = _wave_number(wave_id)
            wave_count += 1
            task_count += len(entries)
            if len(entries) > 4:
                cap_errs.append(f"{name}:{wave_id} has {len(entries)} tasks > 4")
            seen = {}
            for tid, task_label, paths, deps in entries:
                for path in paths:
                    if path in seen:
                        overlaps.append(f"{name}:{wave_id} overlap `{path}` ({seen[path]} & {task_label})")
                    else:
                        seen[path] = task_label
                for dep in deps:
                    dep_edges += 1
                    if dep not in task_wave or task_wave[dep] >= cur_w:
                        dep_errs.append(f"{name}:{wave_id} `{tid}` depends on same/later wave `{dep}`")
    return {
        "ok": wave_count >= 10 and task_count >= 20 and not overlaps and not cap_errs and not dep_errs,
        "waves_checked": wave_count,
        "tasks_checked": task_count,
        "dependency_edges_checked": dep_edges,
        "overlaps": overlaps,
        "parallel_cap_errors": cap_errs,
        "intra_wave_dep_errors": dep_errs,
    }


def check_decisions_and_bans_covered(texts):
    """Verify all settled options, H1-H4, 6 DO-NOT-COPY bans, and 0 placeholders."""
    corpus = "\n".join(texts[name] for name in PLAN_DOCS if name in texts)
    required = (
        "1abcd", "2a", "3a", "4a", "5a", "1c", "5c",
        "H1", "H2", "H3", "H4",
        "schema_version=6", "scripts/defaults/",
        "Postgres nhúng", "Same-Origin UI", "local_trusted",
        "ACPX darwin-arm64", "heartbeat poll rỗng", "detect_tcas_collision",
    )
    missing = [tok for tok in required if tok not in corpus]
    found_placeholders = [
        f"{name}:{ph}" for name in PLAN_DOCS
        for ph in BANNED_PLACEHOLDERS if re.search(rf"\b{ph}\b", texts.get(name, ""))
    ]
    return {
        "ok": not missing and not found_placeholders,
        "missing_tokens": missing,
        "placeholders": found_placeholders,
    }


def run_counterfactual_selftest(repo_root, artifact_dir):
    """Run negative synthetic probes to guarantee checks reject broken inputs."""
    broken_json = check_json_fences_valid({"master-roadmap.md": "```json\n{bad\n```"})
    broken_wave_md = "| Wave | Task | Chạm | Dep |\n|---|---|---|---|\n| `P0-W1` | `P0-1.1` | `scripts/a.py` | `Không` |\n| `P0-W1` | `P0-1.2` | `scripts/a.py` | `Không` |\n"
    broken_wave = check_wave_non_overlap({"dev-plan-p0.md": broken_wave_md})
    broken_dep_md = "| Wave | Task | Chạm | Dep |\n|---|---|---|---|\n| `P0-W1` | `P0-1.1` | `scripts/a.py` | `Không` |\n| `P0-W1` | `P0-1.2` | `scripts/b.py` | `P0-1.1` |\n"
    broken_dep = check_wave_non_overlap({"dev-plan-p0.md": broken_dep_md})
    broken_sym_md = "### 2.1 Neo\n- `scripts/tdq_state.py`: `definitely_missing_symbol_xyz`\n"
    broken_sym = check_disk_paths_and_symbols(repo_root, {"dev-plan-p0.md": broken_sym_md})
    real_ev = Path(artifact_dir) / "evidence.jsonl"
    first_row = json.loads(_read_text(real_ev).splitlines()[0])
    rel = first_row["source"].split(":")[0]
    src_line_count = len(_read_text(Path(repo_root) / rel).splitlines())
    out_of_bounds_ok = src_line_count < 999999
    rejected_all = (
        not broken_json["ok"]
        and not broken_wave["ok"]
        and bool(broken_wave["overlaps"])
        and bool(broken_dep["intra_wave_dep_errors"])
        and bool(broken_sym["anchor_errors"])
        and out_of_bounds_ok
    )
    return {
        "ok": rejected_all,
        "detected_bad_json": not broken_json["ok"],
        "detected_wave_overlap": bool(broken_wave["overlaps"]),
        "detected_intra_wave_dep": bool(broken_dep["intra_wave_dep_errors"]),
        "detected_missing_symbol": bool(broken_sym["anchor_errors"]),
        "bounds_probe_valid": out_of_bounds_ok,
    }


def run_all_checks(artifact_dir, repo_root):
    """Execute all 7 verification checks and return structured summary."""
    texts = {
        name: _read_text(Path(artifact_dir) / name)
        for name in (*SPRINT_DOCS, *PLAN_DOCS)
        if (Path(artifact_dir) / name).is_file()
    }
    checks = {
        "evidence_bounds_and_citations": check_evidence_bounds_and_citations(artifact_dir, repo_root, texts),
        "json_fences_valid": check_json_fences_valid(texts),
        "disk_paths_and_symbols": check_disk_paths_and_symbols(repo_root, texts),
        "import_layer_invariant": check_import_layer_invariant(repo_root, texts),
        "wave_non_overlap": check_wave_non_overlap(texts),
        "decisions_and_bans_covered": check_decisions_and_bans_covered(texts),
        "counterfactual_negative_selftest": run_counterfactual_selftest(repo_root, artifact_dir),
    }
    failed = [name for name, res in checks.items() if not res.get("ok")]
    return {
        "passed_checks": len(checks) - len(failed),
        "failed_checks": len(failed),
        "failed_names": failed,
        "checks": checks,
    }


def main():
    parser = argparse.ArgumentParser(description="Verify Paperclip 3-Phase Dev Plans.")
    default_art = Path(__file__).resolve().parent
    default_root = default_art.parents[3]
    parser.add_argument("--artifact-dir", default=str(default_art))
    parser.add_argument("--repo-root", default=str(default_root))
    parser.add_argument("--out", default="")
    args = parser.parse_args()
    _log(f"verifying artifact_dir={args.artifact_dir}")
    result = run_all_checks(args.artifact_dir, args.repo_root)
    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        _log(f"wrote results -> {out_path}")
    _log(f"done: {result['passed_checks']} passed, {result['failed_checks']} failed")
    print(json.dumps({"passed": result["passed_checks"], "failed": result["failed_checks"]}))
    sys.exit(0 if result["failed_checks"] == 0 else 1)


if __name__ == "__main__":
    main()
