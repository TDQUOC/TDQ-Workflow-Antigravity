#!/usr/bin/env python3
"""TDQ Archify Adapter Module.

Facade and CLI orchestration module for diagram generation, model bridge,
document binding, master bundle publishing, incremental registry portal sync,
standalone drill-down rendering, local loopback serve, status, and verification.

Strictly stdlib-only (+ sibling archify_* modules). Env: TDQ_LOG=0 disables stderr logs.
All functions have <= 50 lines and cyclomatic complexity <= 10.
"""
from __future__ import annotations

import argparse
import base64
import contextlib
import datetime
import gzip
import hashlib
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import uuid
from pathlib import Path
from typing import Any

import archify_portal
import archify_registry
import utf8_io  # noqa: F401 - Force UTF-8 on entrypoints
from archify_artifacts import (
    BINDING_END,
    BINDING_START,
    _hash_file,
    _is_within,
    bind_document,
    build_manifest,
    check_binding,
    check_manifest,
    document_digest,
    mark_stale,
    publish_bundle,
    source_fingerprint,
)
from archify_delivery import (
    FinalizeResult,
    atomic_delivery,
    build_finalize_command,
    check_environment,
    execute_finalize,
    find_archify_root,
    get_archify_bin,
    open_artifact,
    run_finalize,
    serve_directory,
)
from archify_model import (
    VALID_COMPONENT_TYPES,
    VALID_EVIDENCE_KINDS,
    VALID_VIEW_TYPES,
    graph_coverage,
    graphify_to_archify,
    validate_model,
)

__all__ = [
    "BINDING_END",
    "BINDING_START",
    "VALID_COMPONENT_TYPES",
    "VALID_EVIDENCE_KINDS",
    "VALID_VIEW_TYPES",
    "FinalizeResult",
    "atomic_delivery",
    "bind_document",
    "build_finalize_command",
    "build_manifest",
    "check_binding",
    "check_environment",
    "check_manifest",
    "check_master_status",
    "document_digest",
    "execute_finalize",
    "find_archify_root",
    "get_archify_bin",
    "graph_coverage",
    "graphify_to_archify",
    "handle_bridge",
    "handle_check",
    "handle_open",
    "handle_render",
    "handle_serve",
    "handle_status",
    "handle_sync_master",
    "handle_test_bridge",
    "handle_verify",
    "main",
    "mark_stale",
    "open_artifact",
    "publish_bundle",
    "run_finalize",
    "serve_directory",
    "source_fingerprint",
    "sync_master",
    "test_bridge",
    "validate_model",
    "verify_document_and_manifest",
]

_SVG_BLOCK_RE = re.compile(r"<svg\b[^>]*>.*?</svg>", re.IGNORECASE | re.DOTALL)
_WORKFLOW_ID_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9_-]*")
_LEGACY_INDEX_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escaped_title}</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 0; background: #f8fafc; color: #0f172a; line-height: 1.6; }}
    .portal-header {{ background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); color: #f8fafc; padding: 3rem 2rem; border-bottom: 1px solid #334155; }}
    .container {{ max-width: 1160px; margin: 0 auto; padding: 2rem; }}
    h1 {{ margin: 0 0 0.5rem 0; font-size: 2.25rem; letter-spacing: -0.02em; }}
    .subtitle {{ color: #94a3b8; margin: 0; font-size: 1.05rem; }}
    .meta-box {{ background: #ffffff; padding: 1.5rem; border-radius: 12px; border: 1px solid #e2e8f0; box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04); margin-bottom: 2rem; }}
    .meta-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 1rem; }}
    .meta-item {{ background: #f8fafc; padding: 0.85rem 1rem; border-radius: 8px; border: 1px solid #e2e8f0; font-size: 0.95rem; }}
    .module-bar {{ margin-top: 1rem; display: flex; flex-wrap: wrap; gap: 0.5rem; }}
    .module-pill {{ background: #eff6ff; color: #1d4ed8; border: 1px solid #bfdbfe; padding: 0.25rem 0.65rem; border-radius: 999px; font-size: 0.82rem; font-weight: 600; }}
    h2 {{ font-size: 1.4rem; margin: 1.5rem 0 1rem 0; color: #0f172a; }}
    table {{ border-collapse: collapse; width: 100%; background: #ffffff; border-radius: 12px; overflow: hidden; border: 1px solid #e2e8f0; box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04); }}
    th, td {{ border-bottom: 1px solid #e2e8f0; padding: 1rem 1.25rem; text-align: left; }}
    th {{ background: #f1f5f9; font-weight: 600; color: #334155; font-size: 0.9rem; }}
    tr:last-child td {{ border-bottom: none; }}
    .type-badge {{ background: #f1f5f9; color: #334155; padding: 0.2rem 0.6rem; border-radius: 6px; font-size: 0.85rem; font-weight: 500; }}
    .view-btn {{ display: inline-block; background: #2563eb; color: #ffffff; padding: 0.45rem 0.95rem; border-radius: 8px; text-decoration: none; font-weight: 600; font-size: 0.9rem; }}
    .view-btn:hover {{ background: #1d4ed8; text-decoration: none; }}
  </style>
</head>
<body>
  <header class="portal-header">
    <div class="container" style="padding: 0;">
      <h1>{escaped_title}</h1>
      <p class="subtitle">Interactive Master Architecture Portal · Verified by TDQ-Workflow &amp; Archify</p>
    </div>
  </header>
  <main class="container">
    <div class="meta-box">
      <div class="meta-grid">
        <div class="meta-item"><strong>Evidence Kind:</strong> {escaped_kind}</div>
        <div class="meta-item"><strong>Revision:</strong> {escaped_rev}</div>
        <div class="meta-item"><strong>Repository:</strong> {repo_display}</div>
        <div class="meta-item"><strong>Coverage:</strong> {mod_count} modules, {excl_count} excluded, {unk_count} unknown</div>
      </div>
      <div class="module-bar">{module_pills}</div>
    </div>
    <h2>Views Inventory</h2>
    <table>
      <thead>
        <tr>
          <th>ID</th>
          <th>Type</th>
          <th>Summary</th>
          <th>Artifact</th>
        </tr>
      </thead>
      <tbody>
        {inventory_html}
      </tbody>
    </table>
  </main>
</body>
</html>"""


def _log_enabled() -> bool:
    """Return True unless stderr logging is muted via TDQ_LOG=0."""
    return os.environ.get("TDQ_LOG", "1") != "0"


def _log(message: str) -> None:
    """Emit one ISO-timestamped diagnostic line to stderr."""
    if _log_enabled():
        stamp = datetime.datetime.now().replace(microsecond=0).isoformat()
        print(f"[{stamp}] tdq_archify: {message}", file=sys.stderr)


def test_bridge() -> bool:
    """Self-test graphify_to_archify conversion."""
    sample = {"directed": True, "nodes": [{"id": "n1", "label": "Node 1"}], "links": []}
    ir = graphify_to_archify(sample)
    assert ir.get("schema_version") == 1, "schema_version must be 1"
    assert ir.get("diagram_type") == "architecture", "diagram_type must be architecture"
    return True


def _get_git_dirty_files(project_root: Path) -> list[str]:
    """Parse git status --porcelain -z safely handling raw Unicode and rename tokens."""
    proc = subprocess.run(
        ["git", "status", "--porcelain", "-z"],
        cwd=str(project_root),
        capture_output=True,
        timeout=15,
        check=False,
    )
    if proc.returncode != 0:
        err = proc.stderr.decode("utf-8", errors="replace")
        raise RuntimeError(f"git status failed: {err}")

    parts = proc.stdout.split(b"\0")
    dirty_files: list[str] = []
    i = 0
    while i < len(parts):
        token = parts[i]
        if len(token) > 3:
            status_code = token[:2]
            path_str = token[3:].decode("utf-8", errors="surrogateescape").replace("\\", "/")
            dirty_files.append(path_str)
            if b"R" in status_code or b"C" in status_code:
                i += 1
        i += 1
    return dirty_files


def _is_path_matched(file_rel: str, source_paths: list[str]) -> bool:
    """Check if a relative file path matches any source path or directory prefix."""
    for sp in source_paths:
        sp_norm = sp.rstrip("/\\").replace("\\", "/")
        if file_rel == sp_norm or file_rel.startswith(sp_norm + "/"):
            return True
    return False


def _verify_repo_head(project_root: Path, expected_rev: str) -> bool:
    """Verify git rev-parse HEAD matches expected_rev."""
    try:
        rev_proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        sys.stderr.write(f"Error checking git revision: {exc}\n")
        return False
    if rev_proc.returncode != 0:
        sys.stderr.write(f"Error: git rev-parse HEAD failed: {rev_proc.stderr}\n")
        return False
    actual_rev = rev_proc.stdout.strip()
    if actual_rev.lower() != expected_rev.lower():
        sys.stderr.write(
            f"Error: Git revision mismatch: model asserts {expected_rev} but HEAD is {actual_rev}\n"
        )
        return False
    return True


def _filter_relevant_dirty(dirty_files: list[str], source_paths: list[str], model_rel: str) -> list[str]:
    """Filter dirty files to source_paths or non-output project files."""
    if source_paths:
        return [fp for fp in dirty_files if _is_path_matched(fp, source_paths)]
    ignored = ("docs/architecture", "docs/tdq", "logs")
    return [
        fp for fp in dirty_files
        if not (fp.startswith(ignored) or fp == model_rel or fp.endswith(".lock"))
    ]


def _verify_committed_revision(project_root: Path, validated_model: dict, model_file: Path) -> bool:
    """Validate git HEAD revision and dirty working tree for committed evidence."""
    if validated_model.get("evidence_kind", "working-tree") != "committed":
        return True
    expected_rev = validated_model.get("revision", "")
    repo_rev = validated_model.get("repository", {}).get("revision", "")
    if repo_rev and expected_rev.lower() != repo_rev.lower():
        sys.stderr.write(
            f"Error: Master committed revision '{expected_rev}' mismatch repository.revision '{repo_rev}'\n"
        )
        return False
    if not _verify_repo_head(project_root, expected_rev):
        return False
    try:
        dirty_files = _get_git_dirty_files(project_root)
    except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
        sys.stderr.write(f"Error checking git dirty status: {exc}\n")
        return False
    model_rel = model_file.relative_to(project_root).as_posix() if _is_within(model_file, project_root) else ""
    relevant_dirty = _filter_relevant_dirty(dirty_files, validated_model.get("source_paths") or [], model_rel)
    if relevant_dirty:
        sys.stderr.write(
            f"Error: Working tree is dirty ({len(relevant_dirty)} source files modified: {relevant_dirty[:3]}). "
            "Committed evidence requires a clean git status.\n"
        )
        return False
    return True


def _verify_candidate_confinement(model_file: Path, views: list[dict]) -> bool:
    """Ensure all view candidates are confined within model parent directory and exist."""
    model_parent = model_file.parent.resolve()
    for v in views:
        cand_rel = v.get("candidate", "")
        cand_abs = (model_parent / cand_rel).resolve()
        try:
            cand_abs.relative_to(model_parent)
        except ValueError:
            sys.stderr.write(
                f"Error: View '{v.get('id')}' candidate escapes model parent directory: {cand_rel}\n"
            )
            return False
        if not cand_abs.is_file():
            sys.stderr.write(
                f"Error: Candidate file for view '{v.get('id')}' not found: {cand_abs}\n"
            )
            return False
    return True


def _verify_master_sources(model: dict, project_root: Path) -> bool:
    """Reject missing, escaping or out-of-range flow evidence before rendering."""
    root = project_root.resolve()
    try:
        for flow in model.get("master", {}).get("flows", []):
            for step in flow.get("steps", []):
                for source in step.get("sources", []):
                    path = (root / source["path"].replace("\\", "/")).resolve()
                    path.relative_to(root)
                    with path.open("r", encoding="utf-8") as stream:
                        line_count = sum(1 for _ in stream)
                    if source.get("end_line", source["line"]) > line_count:
                        raise ValueError(f"Source line range exceeds file: {source['path']}")
    except (OSError, ValueError) as exc:
        sys.stderr.write(f"Error: Master flow evidence invalid: {exc}\n")
        return False
    return True


def _load_prior_manifest(dest_dir: Path) -> dict[str, Any] | None:
    """Load existing dest_dir/manifest.json if present and valid."""
    manifest_path = dest_dir / "manifest.json"
    if not manifest_path.is_file():
        return None
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except (OSError, ValueError):
        return None


def _extract_json_source_paths(node: Any, out: set[str]) -> None:
    """Collect normalized source file paths from nested 'sources' lists in candidate JSON."""
    if isinstance(node, list):
        for item in node:
            _extract_json_source_paths(item, out)
        return
    if not isinstance(node, dict):
        return
    sources = node.get("sources")
    if isinstance(sources, list):
        for src in sources:
            if isinstance(src, dict) and isinstance(src.get("path"), str) and src["path"].strip():
                out.add(src["path"].replace("\\", "/").strip())
    for key, val in node.items():
        if key != "sources":
            _extract_json_source_paths(val, out)


def _collect_view_source_paths(
    view: dict[str, Any],
    cand_abs: Path,
    model: dict[str, Any] | None,
    project_root: Path,
) -> list[str]:
    """Collect relative POSIX source paths associated with one native view."""
    paths: set[str] = set()
    if _is_within(cand_abs, project_root):
        paths.add(cand_abs.resolve().relative_to(project_root.resolve()).as_posix())
    try:
        cand_data = json.loads(cand_abs.read_text(encoding="utf-8"))
        _extract_json_source_paths(cand_data, paths)
    except (OSError, ValueError):
        pass
    for flow in (model or {}).get("master", {}).get("flows", []):
        if (flow.get("target") or {}).get("diagram") != view["id"]:
            continue
        for step in flow.get("steps", []):
            for src in step.get("sources", []):
                if isinstance(src, dict) and isinstance(src.get("path"), str):
                    paths.add(src["path"].replace("\\", "/").strip())
    return sorted(paths)


def _view_files_match_prior(
    vid: str,
    cand_abs: Path,
    dest_dir: Path,
    prior_child: dict[str, Any],
) -> bool:
    """Return True if dest HTML/candidate exist and match prior child_files and live candidate."""
    html_name, cand_name = f"{vid}.html", f"{vid}.candidate.json"
    dest_html, dest_cand = dest_dir / html_name, dest_dir / cand_name
    if not dest_html.is_file() or not dest_cand.is_file():
        return False
    exp_html = str(prior_child.get(html_name) or "").lower()
    exp_cand = str(prior_child.get(cand_name) or "").lower()
    if not exp_html or not exp_cand:
        return False
    return (
        _hash_file(dest_html).lower() == exp_html
        and _hash_file(dest_cand).lower() == exp_cand
        and _hash_file(cand_abs).lower() == exp_cand
    )


def _can_reuse_view(
    view: dict[str, Any],
    cand_abs: Path,
    dest_dir: Path,
    prior: dict[str, Any] | None,
    pre_sources: dict[str, str],
    model: dict[str, Any] | None,
    project_root: Path,
) -> bool:
    """Return True when cached view artifacts in dest_dir are fresh and reusable."""
    if not isinstance(prior, dict):
        return False
    vid = view["id"]
    if not _view_files_match_prior(vid, cand_abs, dest_dir, prior.get("child_files") or {}):
        return False
    prior_views = {
        pv["id"]: pv for pv in prior.get("views", []) if isinstance(pv, dict) and "id" in pv
    }
    pv = prior_views.get(vid)
    if pv is None or pv.get("type") != view["type"] or pv.get("summary", "") != view.get("summary", ""):
        return False
    prior_sources = prior.get("source_files") or {}
    for rel_p in _collect_view_source_paths(view, cand_abs, model, project_root):
        if pre_sources.get(rel_p) != prior_sources.get(rel_p):
            return False
    return True


def _reuse_cached_view(
    view: dict[str, Any],
    dest_dir: Path,
    staging_dir: Path,
    prior: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, str], Any]:
    """Copy clean cached view HTML and candidate JSON from dest_dir to staging_dir."""
    vid = view["id"]
    html_name, cand_name = f"{vid}.html", f"{vid}.candidate.json"
    shutil.copy2(dest_dir / html_name, staging_dir / html_name)
    shutil.copy2(dest_dir / cand_name, staging_dir / cand_name)
    v_hash = _hash_file(staging_dir / html_name)
    c_hash = _hash_file(staging_dir / cand_name)
    receipt = (prior.get("view_receipts") or {}).get(vid, {"ok": True, "status": "pass", "cached": True})
    _log(f"reused cached view id={vid}")
    return (
        {
            "id": vid,
            "type": view["type"],
            "summary": view.get("summary", ""),
            "file": html_name,
            "hash": v_hash,
        },
        {html_name: v_hash, cand_name: c_hash},
        receipt,
    )


def _render_single_view_to_staging(
    v: dict[str, Any],
    model_parent: Path,
    staging_dir: Path,
    project_root: Path,
    quality: str,
) -> tuple[dict[str, Any], dict[str, str], Any]:
    """Render one native view into staging directory via run_finalize."""
    vid, vtype = v["id"], v["type"]
    cand_abs = (model_parent / v["candidate"]).resolve()
    view_filename = f"{vid}.html"
    view_out = staging_dir / view_filename

    res = run_finalize(
        diagram_type=vtype,
        candidate_path=cand_abs,
        output_path=view_out,
        quality=quality,
        repo_root=project_root,
    )
    if not res.status or not view_out.is_file():
        raise RuntimeError(f"Failed to finalize view '{vid}': {res.receipt}")

    v_hash = _hash_file(view_out)
    cand_bundle_name = f"{vid}.candidate.json"
    cand_bundle_path = staging_dir / cand_bundle_name
    cand_bundle_path.write_text(cand_abs.read_text(encoding="utf-8"), encoding="utf-8")
    return (
        {
            "id": vid,
            "type": vtype,
            "summary": v.get("summary", ""),
            "file": view_filename,
            "hash": v_hash,
        },
        {view_filename: v_hash, cand_bundle_name: _hash_file(cand_bundle_path)},
        res.receipt,
    )


def _render_views_to_staging(
    views: list[dict],
    model_parent: Path,
    staging_dir: Path,
    project_root: Path,
    quality: str = "showcase",
    *,
    dest_dir: Path | None = None,
    prior_manifest: dict[str, Any] | None = None,
    pre_sources: dict[str, str] | None = None,
    validated_model: dict[str, Any] | None = None,
    incremental: bool = False,
) -> tuple[list[dict], dict[str, str], dict[str, Any]]:
    """Render or reuse native views into staging directory."""
    rendered_views: list[dict] = []
    child_files: dict[str, str] = {}
    receipts: dict[str, Any] = {}

    for v in views:
        cand_abs = (model_parent / v["candidate"]).resolve()
        can_reuse = (
            incremental
            and dest_dir is not None
            and prior_manifest is not None
            and pre_sources is not None
            and _can_reuse_view(v, cand_abs, dest_dir, prior_manifest, pre_sources, validated_model, project_root)
        )
        if can_reuse and dest_dir is not None and prior_manifest is not None:
            rv, cf, rec = _reuse_cached_view(v, dest_dir, staging_dir, prior_manifest)
        else:
            rv, cf, rec = _render_single_view_to_staging(v, model_parent, staging_dir, project_root, quality)
        rendered_views.append(rv)
        child_files.update(cf)
        receipts[v["id"]] = rec
    return rendered_views, child_files, receipts


def _generate_index_html(validated_model: dict, rendered_views: list[dict]) -> str:
    """Generate legacy index HTML with escaped text labels, dashboard layout, and relative links."""
    coverage = validated_model.get("coverage", {})
    repo_info = validated_model.get("repository") or {}
    modules_list = coverage.get("modules", [])
    module_pills = " ".join(
        f'<span class="module-pill">{html.escape(str(m.get("id", "")))} · '
        f'{html.escape(str(m.get("status", "selected")))}</span>'
        for m in modules_list if isinstance(m, dict)
    )
    table_rows = [
        f"<tr><td><strong>{html.escape(rv['id'])}</strong></td>"
        f"<td><span class=\"type-badge\">{html.escape(rv['type'])}</span></td>"
        f"<td>{html.escape(rv['summary'])}</td>"
        f"<td><a class=\"view-btn\" href=\"{html.escape(rv['file'])}\">View Diagram</a></td></tr>"
        for rv in rendered_views
    ]
    return _LEGACY_INDEX_TEMPLATE.format(
        escaped_title=html.escape(str(validated_model.get("title", "Master Architecture"))),
        escaped_rev=html.escape(str(validated_model.get("revision", "N/A"))),
        escaped_kind=html.escape(str(validated_model.get("evidence_kind", "unknown"))),
        repo_display=html.escape(str(repo_info.get("url", ""))) or "N/A",
        mod_count=len(coverage.get("modules", [])),
        excl_count=len(coverage.get("excluded", [])),
        unk_count=len(coverage.get("unknown", [])),
        module_pills=module_pills,
        inventory_html="\n".join(table_rows),
    )


def _alloc_id(base: str, used: set[str]) -> str:
    cand = "".join(c if c.isalnum() or c in "_-" else "-" for c in base).strip("-") or "item"
    if not cand[0].isalpha() or cand.startswith("explainer-"):
        cand = f"m-{cand}"
    out, idx = cand[:90], 1
    while out in used:
        out, idx = f"{cand[:84]}-{idx}", idx + 1
    used.add(out)
    return out


def _step_detail_text(step: dict[str, Any]) -> str:
    refs = [
        f"`{s['path']}:{s['line']}" + (f"-{s['end_line']}`" if s.get("end_line", s["line"]) != s["line"] else "`")
        for s in step.get("sources", [])
    ]
    detail = step.get("detail", "").strip()
    return f"{detail} ({', '.join(refs)})" if detail and refs else (detail or ", ".join(refs))


_META_LOCALE_RE = re.compile(r"(?im)^@meta\b[^\n]*\blocale\s*=")
_HTML_LANG_RE = re.compile(r"<html\b([^>]*?)\blang=([\"'])(?:en|zh(?:-[A-Za-z0-9]+)?)\2", re.IGNORECASE)
_READER_WORDS_RE = re.compile(
    r'(<script\b[^>]*id="explainer-reader-words"[^>]*>)(.*?)(</script>)',
    re.DOTALL,
)
_PREPARED_BUNDLE_RE = re.compile(
    r'(<script\s+type="application/json"\s+id="archify-explainer-prepared">)(.*?)(</script>)',
    re.DOTALL,
)
_VI_BRANCH_RE = re.compile(r"分支\s+(\d+)")

# i18n-allow: Vietnamese UI dictionary mirroring Archify explainer/render.mjs keys
_VI_READER_WORDS: dict[str, Any] = {
    "answer": "Tóm tắt",  # i18n-allow
    "answerMark": "Đ",  # i18n-allow
    "scope": "Phạm vi áp dụng",  # i18n-allow
    "sources": "Nguồn đối chiếu",  # i18n-allow
    "print": "In / PDF",  # i18n-allow
    "image": "Ảnh dài",  # i18n-allow
    "imageHints": ["Nét nhất", "Nhẹ nhất", "Mở mọi nơi"],  # i18n-allow
    "export": "Xuất tệp",  # i18n-allow
    "style": "Giao diện",  # i18n-allow
    "styles": {
        "clean": "Gọn sạch",  # i18n-allow
        "editorial": "Tạp chí",  # i18n-allow
        "product": "Sản phẩm",  # i18n-allow
        "swiss": "Lưới chuẩn",  # i18n-allow
    },
    "auto": "Hệ thống",  # i18n-allow
    "light": "Sáng",  # i18n-allow
    "dark": "Tối",  # i18n-allow
    "typical": "Giá trị điển hình",  # i18n-allow
    "explore": "Mở sơ đồ tương tác",  # i18n-allow
    "exploreTitle": "Phóng to, tìm nút, lần luồng dữ liệu và xuất ảnh",  # i18n-allow
    "close": "Đóng",  # i18n-allow
    "loading": "Đang mở sơ đồ…",  # i18n-allow
    "graph": "Cấu trúc sơ đồ",  # i18n-allow
    "changes": "Thay đổi cấu trúc",  # i18n-allow
    "added": "Thêm mới",  # i18n-allow
    "removed": "Đã xóa",  # i18n-allow
    "modified": "Đã sửa",  # i18n-allow
    "copy": "Sao chép",  # i18n-allow
    "copied": "Đã sao chép",  # i18n-allow
    "walk": "Xem từng bước",  # i18n-allow
    "walkMessages": "Chạy từng thông điệp",  # i18n-allow
    "walkFlow": "Đi theo luồng",  # i18n-allow
    "prev": "Quay lại",  # i18n-allow
    "next": "Tiếp theo",  # i18n-allow
    "end": "Xong",  # i18n-allow
    "ask": "Hỏi thêm",  # i18n-allow
    "askQuote": "Hỏi về đoạn này",  # i18n-allow
    "askPlaceholder": "Chỗ nào chưa rõ hoặc muốn bổ sung gì?",  # i18n-allow
    "askCopy": "Sao chép câu hỏi",  # i18n-allow
    "askCopied": "Đã sao chép. Dán câu hỏi cho agent.",  # i18n-allow
    "askCancel": "Hủy",  # i18n-allow
    "askChips": [
        "Tôi chưa hiểu phần này",  # i18n-allow
        "Giải thích sâu hơn",  # i18n-allow
        "Cho ví dụ cụ thể",  # i18n-allow
        "Dựa trên bằng chứng nào?",  # i18n-allow
    ],
    "askPage": "Trang",  # i18n-allow
    "askFile": "Tệp",  # i18n-allow
    "askWhere": "Vị trí",  # i18n-allow
    "askQuoteLabel": "Trích dẫn",  # i18n-allow
    "askQuestion": "Câu hỏi",  # i18n-allow
    "askNote": "Sao chép trang, khung và mã ID để agent sửa đúng phần này.",  # i18n-allow
    "askPatch": "Chỉ sửa khung này qua Archify patch explainer và giữ nguyên ID.",  # i18n-allow
    "tagline": "Biến mọi nội dung cần hiểu, lên kế hoạch hay chia sẻ thành trang trực quan tương tác.",  # i18n-allow
}

_VI_STATIC_REPLACEMENTS: tuple[tuple[str, str], ...] = (
    ('<a class="skip-link" href="#board">Skip to content</a>', '<a class="skip-link" href="#board">Chuyển tới nội dung</a>'),  # i18n-allow
    ('aria-label="Theme"', 'aria-label="Chế độ màu"'),  # i18n-allow
    ('>System</button>', '>Hệ thống</button>'),  # i18n-allow
    ('>Light</button>', '>Sáng</button>'),  # i18n-allow
    ('>Dark</button>', '>Tối</button>'),  # i18n-allow
    ('aria-label="Style"', 'aria-label="Giao diện"'),  # i18n-allow
    ('<span data-style-label>Clean</span>', '<span data-style-label>Gọn sạch</span>'),  # i18n-allow
    ('<span data-style-label>Editorial</span>', '<span data-style-label>Tạp chí</span>'),  # i18n-allow
    ('<span data-style-label>Product</span>', '<span data-style-label>Sản phẩm</span>'),  # i18n-allow
    ('<span data-style-label>Swiss</span>', '<span data-style-label>Lưới chuẩn</span>'),  # i18n-allow
    ('<span>Export</span>', '<span>Xuất tệp</span>'),  # i18n-allow
    ('aria-label="Export"', 'aria-label="Xuất tệp"'),  # i18n-allow
    ('>Long image</p>', '>Ảnh dài</p>'),  # i18n-allow
    ('aria-label="Long image ', 'aria-label="Ảnh dài '),  # i18n-allow
    ('<small>Sharpest</small>', '<small>Nét nhất</small>'),  # i18n-allow
    ('<small>Smallest</small>', '<small>Nhẹ nhất</small>'),  # i18n-allow
    ('<small>Opens anywhere</small>', '<small>Mở mọi nơi</small>'),  # i18n-allow
    ('<span>Print / PDF</span>', '<span>In / PDF</span>'),  # i18n-allow
    ('>A</span><h2>Answer</h2>', '>Đ</span><h2>Tóm tắt</h2>'),  # i18n-allow
    ('<span class="scope-label">Applies to</span>', '<span class="scope-label">Phạm vi áp dụng</span>'),  # i18n-allow
    (
        'title="Zoom, find nodes, trace paths, upstream and downstream, export images or motion"',
        'title="Phóng to, tìm nút, lần luồng dữ liệu và xuất ảnh"',  # i18n-allow
    ),
    ('<span>Open interactive view</span>', '<span>Mở sơ đồ tương tác</span>'),  # i18n-allow
    ('<summary>Diagram structure</summary>', '<summary>Cấu trúc sơ đồ</summary>'),  # i18n-allow
    ('<dt>Structure changes</dt>', '<dt>Thay đổi cấu trúc</dt>'),  # i18n-allow
    ('<span class="chip added">Added</span>', '<span class="chip added">Thêm mới</span>'),  # i18n-allow
    ('<span class="chip removed">Removed</span>', '<span class="chip removed">Đã xóa</span>'),  # i18n-allow
    ('<span class="chip modified">Modified</span>', '<span class="chip modified">Đã sửa</span>'),  # i18n-allow
    ('>Copy</button>', '>Sao chép</button>'),  # i18n-allow
    ('<span class="typical">Typical value</span>', '<span class="typical">Giá trị điển hình</span>'),  # i18n-allow
    ('<h2>Typical value notes</h2>', '<h2>Ghi chú giá trị điển hình</h2>'),  # i18n-allow
    ('aria-label="Code changes"', 'aria-label="Thay đổi mã"'),  # i18n-allow
    (
        '<th scope="col">Old</th><th scope="col">New</th><th scope="col">Change</th>',
        '<th scope="col">Cũ</th><th scope="col">Mới</th><th scope="col">Thay đổi</th>',  # i18n-allow
    ),
    ('<section class="sources"><h2>Sources</h2>', '<section class="sources"><h2>Nguồn đối chiếu</h2>'),  # i18n-allow
    (
        '<span class="colophon-tagline">Turn anything you want to understand, plan, or share into an interactive visual.</span>',
        '<span class="colophon-tagline">Biến mọi nội dung cần hiểu, lên kế hoạch hay chia sẻ thành trang trực quan tương tác.</span>',  # i18n-allow
    ),
    ('<span>Close</span>', '<span>Đóng</span>'),  # i18n-allow
    ('role="status">Opening diagram…</p>', 'role="status">Đang mở sơ đồ…</p>'),  # i18n-allow
)

_VI_REGEX_REPLACEMENTS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r'(<button\b[^>]*data-style-choice="clean"[^>]*>(?:<span[^>]*></span>)?<span>)Clean(</span>)'), r'\1Gọn sạch\2'),  # i18n-allow
    (re.compile(r'(<button\b[^>]*data-style-choice="editorial"[^>]*>(?:<span[^>]*></span>)?<span>)Editorial(</span>)'), r'\1Tạp chí\2'),  # i18n-allow
    (re.compile(r'(<button\b[^>]*data-style-choice="product"[^>]*>(?:<span[^>]*></span>)?<span>)Product(</span>)'), r'\1Sản phẩm\2'),  # i18n-allow
    (re.compile(r'(<button\b[^>]*data-style-choice="swiss"[^>]*>(?:<span[^>]*></span>)?<span>)Swiss(</span>)'), r'\1Lưới chuẩn\2'),  # i18n-allow
    (re.compile(r'(<span class="assessment good"[^>]*>(?:<span[^>]*>(?:<i></i>)*</span>)?<b>)Favorable(</b>)'), r'\1Tích cực\2'),  # i18n-allow
    (re.compile(r'(<span class="assessment caution"[^>]*>(?:<span[^>]*>(?:<i></i>)*</span>)?<b>)Tradeoff(</b>)'), r'\1Cần cân nhắc\2'),  # i18n-allow
    (re.compile(r'(<span class="assessment bad"[^>]*>(?:<span[^>]*>(?:<i></i>)*</span>)?<b>)Unfavorable(</b>)'), r'\1Bất lợi\2'),  # i18n-allow
    (re.compile(r"<span>(\d+)\s+panels?</span>"), r"<span>\1 bảng</span>"),  # i18n-allow
    (re.compile(r"<span>(\d+)\s+diagrams?\s+validated</span>"), r"<span>\1 sơ đồ đã kiểm chuẩn</span>"),  # i18n-allow
    (re.compile(r"<span>(\d+)\s+sources?</span>"), r"<span>\1 nguồn</span>"),  # i18n-allow
    (re.compile(r"<span>code pinned to ([^<]+)</span>"), r"<span>mã cố định ở \1</span>"),  # i18n-allow
    (_VI_BRANCH_RE, r"Nhánh \1"),  # i18n-allow
    (re.compile(r'(<p class="metric-value">)Limit '), r"\1Giới hạn "),  # i18n-allow
    (re.compile(r'(<p class="metric-overflow">)Over limit by '), r"\1Vượt mức "),  # i18n-allow
)


def _read_doc_lang(project_root: Path) -> str:
    """Read `doc_lang` from docs/tdq/state.json; default to 'vi' when absent or unreadable."""
    state_file = project_root / "docs" / "tdq" / "state.json"
    if not state_file.is_file():
        return "vi"
    try:
        data = json.loads(state_file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return "vi"
    lang = str(data.get("doc_lang") or "vi").strip().lower()
    return lang or "vi"


def _ensure_explainer_locale_candidate(
    cand_path: Path,
    temp_dir: Path | None = None,
) -> tuple[Path, Path | None]:
    """Inject English fallback locale into a transient candidate copy when omitted."""
    raw = cand_path.read_text(encoding="utf-8")
    target_dir = temp_dir or cand_path.parent
    tmp_name = f".tmp.{cand_path.stem}.{uuid.uuid4().hex}{cand_path.suffix}"
    if cand_path.suffix.lower() == ".json":
        try:
            payload = json.loads(raw)
        except ValueError:
            return cand_path, None
        meta = payload.get("meta") if isinstance(payload, dict) else None
        if not isinstance(meta, dict) or meta.get("locale"):
            return cand_path, None
        meta["locale"] = "en"
        tmp_path = target_dir / tmp_name
        tmp_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return tmp_path, tmp_path

    if _META_LOCALE_RE.search(raw):
        return cand_path, None
    lines = raw.splitlines(keepends=True)
    insert_at = 1 if lines and re.match(r"^#{1,2}\s+", lines[0]) else 0
    lines.insert(insert_at, "\n@meta locale=en\n")
    tmp_path = target_dir / tmp_name
    tmp_path.write_text("".join(lines), encoding="utf-8")
    return tmp_path, tmp_path


def _serialize_script_json(payload: dict[str, Any]) -> str:
    """Serialize JSON safely for inline `<script type="application/json">` embedding."""
    serialized = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    for ch, esc in (("<", "\\u003c"), (">", "\\u003e"), ("&", "\\u0026"), ("\u2028", "\\u2028"), ("\u2029", "\\u2029")):
        serialized = serialized.replace(ch, esc)
    return serialized


def _localize_html_gzip_vi(encoded: str) -> tuple[str, bool]:
    """Localize auto-generated Chinese branch labels inside a gzipped child diagram."""
    try:
        raw = gzip.decompress(base64.b64decode(encoded)).decode("utf-8")
    except (ValueError, OSError, UnicodeDecodeError):
        return encoded, False
    updated = _VI_BRANCH_RE.sub(r"Nhánh \1", raw)  # i18n-allow
    if updated == raw:
        return encoded, False
    repacked = base64.b64encode(gzip.compress(updated.encode("utf-8"), compresslevel=6)).decode("ascii")
    return repacked, True


def _replace_branch_in_json(node: Any) -> tuple[Any, bool]:
    """Recursively localize workflow branch labels in prepared-bundle JSON and `htmlGzip`."""
    if isinstance(node, str):
        updated = _VI_BRANCH_RE.sub(r"Nhánh \1", node)  # i18n-allow
        return updated, updated != node
    if isinstance(node, list):
        items = [_replace_branch_in_json(item) for item in node]
        return ([item for item, _ in items], any(changed for _, changed in items))
    if isinstance(node, dict):
        out: dict[str, Any] = {}
        any_changed = False
        for key, val in node.items():
            if key == "htmlGzip" and isinstance(val, str):
                new_val, changed = _localize_html_gzip_vi(val)
            else:
                new_val, changed = _replace_branch_in_json(val)
            out[key] = new_val
            any_changed = any_changed or changed
        return out, any_changed
    return node, False


def _localize_prepared_diagrams_vi(html_text: str) -> str:
    """Translate auto-generated Chinese lane/branch labels inside `#archify-explainer-prepared`."""
    def _replace(match: re.Match[str]) -> str:
        prefix, body, suffix = match.group(1), match.group(2), match.group(3)
        try:
            data = json.loads(body)
        except ValueError:
            return match.group(0)
        updated, changed = _replace_branch_in_json(data)
        if not changed or not isinstance(updated, dict):
            return match.group(0)
        return f"{prefix}{_serialize_script_json(updated)}{suffix}"

    return _PREPARED_BUNDLE_RE.sub(_replace, html_text, count=1)


def _localize_reader_words_json(html_text: str) -> str:
    """Translate embedded `#explainer-reader-words` JSON safely for browser JS controls."""
    def _replace(match: re.Match[str]) -> str:
        prefix, body, suffix = match.group(1), match.group(2), match.group(3)
        try:
            words = json.loads(body)
        except ValueError:
            return match.group(0)
        if not isinstance(words, dict):
            return match.group(0)
        merged = dict(words)
        for key, val in _VI_READER_WORDS.items():
            merged[key] = dict(val) if isinstance(val, dict) else list(val) if isinstance(val, list) else val
        return f"{prefix}{_serialize_script_json(merged)}{suffix}"

    return _READER_WORDS_RE.sub(_replace, html_text, count=1)


def _localize_explainer_html_vi(html_text: str) -> str:
    """Localize rendered Archify explainer HTML chrome and JS word table to Vietnamese."""
    out = _HTML_LANG_RE.sub(lambda m: f"<html{m.group(1)}lang={m.group(2)}vi{m.group(2)}", html_text, count=1)
    for src, dst in _VI_STATIC_REPLACEMENTS:
        out = out.replace(src, dst)
    for pat, repl in _VI_REGEX_REPLACEMENTS:
        out = pat.sub(repl, out)
    return _localize_prepared_diagrams_vi(_localize_reader_words_json(out))


def _build_detail_panels(views: list[dict[str, Any]], overview_id: str, flows: list[dict[str, Any]], used: set[str]) -> list[dict[str, Any]]:
    """Build per-view explainer panels and matching step blocks."""
    panels: list[dict[str, Any]] = []
    for v in views:
        vid = v["id"]
        if vid == overview_id or v["type"] == "explainer":
            continue
        blocks: list[dict[str, Any]] = [{
            "id": vid, "type": "diagram", "diagramType": v["type"], "source": f"{vid}.candidate.json",
        }]
        for f in (fl for fl in flows if (fl.get("target") or {}).get("diagram") == vid):
            blocks.append({
                "id": _alloc_id(f"{f['id']}-steps", used),
                "type": "steps",
                "items": [{"id": s["id"], "text": s["text"], "detail": _step_detail_text(s)} for s in f.get("steps", [])],
            })
        panels.append({"id": _alloc_id(f"{vid}-panel", used), "title": v.get("summary") or vid, "blocks": blocks})
    return panels


def _build_master_explainer(validated_model: dict[str, Any], quality: str, doc_lang: str = "en") -> dict[str, Any]:
    """Assemble master explainer candidate JSON for legacy master.flows models."""
    master = validated_model["master"]
    views = validated_model["views"]
    views_by_id = {v["id"]: v for v in views}
    overview_id, flows = master["overview"], master["flows"]
    used = {"answer", "diagram-dialog", "diagram-dialog-title", "toast"} | set(views_by_id)
    used.update(f["id"] for f in flows)
    used.update(s["id"] for f in flows for s in f.get("steps", []))

    overview_view = views_by_id[overview_id]
    overview_blocks: list[dict[str, Any]] = [{
        "id": overview_id, "type": "diagram", "diagramType": overview_view["type"], "source": f"{overview_id}.candidate.json",
    }]
    if flows:
        overview_blocks.append({
            "id": _alloc_id("master-flows", used),
            "type": "steps",
            "items": [{k: f[k] for k in ("id", "text", "detail", "target") if f.get(k)} for f in flows],
        })
    panels = [{
        "id": _alloc_id(f"{overview_id}-panel", used),
        "title": overview_view.get("summary") or "Overview",
        "blocks": overview_blocks,
    }]
    panels.extend(_build_detail_panels(views, overview_id, flows, used))
    title = str(validated_model.get("title", "Master Architecture"))
    locale = "vi" if str(doc_lang).strip().lower().startswith("vi") else "en"
    return {
        "schema_version": 1,
        "diagram_type": "explainer",
        "meta": {"id": _alloc_id("master-architecture", used), "title": title, "locale": locale, "output": "index.html", "quality_profile": quality},
        "answer": {"summary": f"{title} ({validated_model.get('evidence_kind', 'working-tree')})."},
        "panels": panels,
        "sources": [],
    }


def _collect_registry_extra_paths(reg_dir: Path | None) -> list[Path]:
    """Collect registry index.json and nodes/*.json paths when registry is configured."""
    if reg_dir is None or not reg_dir.is_dir():
        return []
    paths: list[Path] = []
    idx_file = reg_dir / "index.json"
    if idx_file.is_file():
        paths.append(idx_file.resolve())
    nodes_dir = reg_dir / "nodes"
    if nodes_dir.is_dir():
        paths.extend(p.resolve() for p in sorted(nodes_dir.glob("*.json")))
    return paths


def _derive_stable_source_paths(
    project_root: Path,
    dest_dir: Path,
    model_file: Path,
    validated_model: dict,
    *,
    reg_dir: Path | None = None,
) -> list[str]:
    """Derive stable project source_paths excluding outputs, dest, and staging directories."""
    dest_rel = dest_dir.resolve().relative_to(project_root).as_posix() if _is_within(dest_dir, project_root) else ""
    model_rel = model_file.resolve().relative_to(project_root).as_posix() if _is_within(model_file, project_root) else ""
    declared = validated_model.get("source_paths")
    base_paths = list(declared) if declared is not None else list(source_fingerprint(project_root).keys())
    model_parent = model_file.parent.resolve()
    extra_abs = [
        *((model_parent / v.get("candidate", "")).resolve() for v in validated_model.get("views", [])),
        *(
            (project_root / src["path"].replace("\\", "/")).resolve()
            for flow in validated_model.get("master", {}).get("flows", [])
            for step in flow.get("steps", [])
            for src in step.get("sources", [])
        ),
        *_collect_registry_extra_paths(reg_dir),
    ]
    for p_abs in extra_abs:
        if _is_within(p_abs, project_root):
            base_paths.append(p_abs.relative_to(project_root).as_posix())

    clean = list(dict.fromkeys(
        p for p in base_paths
        if p != model_rel and ".staging" not in p and "staging." not in p
        and not (dest_rel and (p == dest_rel or p.startswith(dest_rel + "/")))
    ))
    return clean if declared is not None else sorted(clean)


def _assemble_master_manifest(
    project_root: Path,
    dest_dir: Path,
    staging_dir: Path,
    model_file: Path,
    validated_model: dict,
    rendered_views: list[dict],
    child_files: dict[str, str],
    receipts: dict[str, Any],
    source_paths: list[str],
    pre_sources: dict[str, str] | None,
    slice_cache: dict[str, dict[str, str]] | None,
) -> dict[str, Any]:
    """Build aggregate master manifest with rebased artifact path and optional slice cache."""
    aggregate_receipt = {
        "ok": True, "status": "pass", "engine": "archify", "views_count": len(rendered_views), "index": "index.html",
    }
    raw_manifest = build_manifest(
        project=project_root, document=model_file, candidate=model_file,
        artifact=staging_dir / "index.html", receipt=aggregate_receipt,
        evidence_kind=validated_model.get("evidence_kind", "working-tree"),
        revision=validated_model.get("revision"), coverage=validated_model.get("coverage", {}),
        source_paths=source_paths, source_files=pre_sources,
    )
    raw_manifest["artifact_path"] = (dest_dir / "index.html").resolve().relative_to(project_root).as_posix()
    raw_manifest["child_files"] = child_files
    raw_manifest["views"] = rendered_views
    raw_manifest["view_receipts"] = receipts
    if slice_cache is not None:
        raw_manifest["slice_cache"] = slice_cache
    return raw_manifest


def _build_and_publish_manifest(
    project_root: Path,
    dest_dir: Path,
    staging_dir: Path,
    model_file: Path,
    validated_model: dict,
    rendered_views: list[dict],
    child_files: dict[str, str],
    receipts: dict[str, Any],
    source_paths: list[str] | None = None,
    pre_sources: dict[str, str] | None = None,
    pre_model_hash: str | None = None,
    slice_cache: dict[str, dict[str, str]] | None = None,
) -> Path:
    """Construct aggregate manifest, rebase final paths, and publish bundle atomically."""
    if source_paths is None:
        source_paths = _derive_stable_source_paths(project_root, dest_dir, model_file, validated_model)
    if pre_model_hash is not None and _hash_file(model_file) != pre_model_hash:
        raise RuntimeError("Master model modified during render")
    if pre_sources is not None and source_fingerprint(project_root, paths=source_paths) != pre_sources:
        raise RuntimeError("Source or candidate modified during render")

    raw_manifest = _assemble_master_manifest(
        project_root, dest_dir, staging_dir, model_file, validated_model,
        rendered_views, child_files, receipts, source_paths, pre_sources, slice_cache,
    )
    (staging_dir / "manifest.json").write_text(
        json.dumps(raw_manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    published_index = publish_bundle(staging=staging_dir, destination=dest_dir)
    readback = check_manifest(project_root, dest_dir / "manifest.json")
    if readback.get("status") != "current":
        raise RuntimeError(f"Post-publish readback not current: {readback.get('reasons')}")
    return published_index


def _sync_legacy_graph(graph_path: str | Path, out_path: str | Path | None, max_nodes: int) -> bool:
    """Fallback sync for legacy graph.json conversion calls."""
    target_graph = Path(graph_path)
    if not target_graph.is_file():
        sys.stderr.write(f"Warning: Graph file not found: {target_graph}, skipping sync.\n")
        return False

    if out_path:
        target_out = Path(out_path)
    else:
        repo_root = Path(__file__).resolve().parent.parent
        target_out = repo_root / "docs" / "architecture" / "master.architecture.json"

    ir = graphify_to_archify(target_graph, max_nodes=max_nodes)
    atomic_delivery(target_out, json.dumps(ir, indent=2, ensure_ascii=False))
    print(f"Master architecture JSON synchronized: {target_out}")
    return True


def _resolve_sync_paths(
    model: str | Path | None,
    project: str | Path | None,
    out: str | Path | None,
) -> tuple[Path, Path, Path] | None:
    """Resolve project_root, dest_dir, and model_file paths safely."""
    project_root = Path(project).resolve() if project else Path.cwd().resolve()
    if not project_root.is_dir():
        sys.stderr.write(f"Error: Project root directory not found: {project_root}\n")
        return None
    raw_out = Path(out) if out is not None else Path("docs") / "architecture"
    dest_dir = raw_out.resolve() if raw_out.is_absolute() else (project_root / raw_out).resolve()
    raw_m = Path(model) if model is not None else Path("docs") / "architecture" / "master.model.json"
    model_file = raw_m.resolve() if raw_m.is_absolute() else (project_root / raw_m).resolve()
    if not model_file.is_file():
        sys.stderr.write(f"Error: Master model file not found: {model_file}\n")
        return None
    return project_root, dest_dir, model_file


def _load_and_validate_model(model_file: Path) -> dict | None:
    """Read and validate Master model file."""
    try:
        content = model_file.read_text(encoding="utf-8")
        if not content.strip():
            sys.stderr.write(f"Error: Master model file is empty: {model_file}\n")
            return None
        return validate_model(json.loads(content))
    except (OSError, ValueError, TypeError) as exc:
        sys.stderr.write(f"Error: Master model validation failed: {exc}\n")
        return None


def _resolve_registry_config(
    validated_model: dict[str, Any],
    project_root: Path,
) -> tuple[Path, dict[str, Any]] | None:
    """Return confined (registry_dir, registry_cfg) when master.registry is configured."""
    master = validated_model.get("master")
    if not isinstance(master, dict) or "registry" not in master:
        return None
    reg_cfg = master["registry"]
    reg_rel = str(reg_cfg["path"]).replace("\\", "/")
    raw_dir = project_root / reg_rel
    if raw_dir.is_symlink():
        raise ValueError(f"Registry path cannot be a symlink: {reg_rel}")
    reg_dir = raw_dir.resolve()
    if not _is_within(reg_dir, project_root) or reg_dir == project_root.resolve():
        raise ValueError(f"Registry path escapes project root: {reg_rel}")
    if not reg_dir.is_dir():
        raise FileNotFoundError(f"Registry directory not found: {reg_dir}")
    return reg_dir, reg_cfg


def _verify_node_sources_confined(nodes: dict[str, dict[str, Any]], project_root: Path) -> None:
    """Verify every Logic Node source path stays within project_root."""
    root = project_root.resolve()
    for nid, node in nodes.items():
        for src in node.get("sources", []):
            src_abs = (root / str(src["path"]).replace("\\", "/")).resolve()
            if not _is_within(src_abs, root):
                raise ValueError(f"Node '{nid}' source escapes project root: {src['path']}")


def _sync_registry_context(
    reg_dir: Path,
    reg_cfg: dict[str, Any],
    project_root: Path,
) -> dict[str, Any]:
    """Compute dirty slices and sync registry index BEFORE source fingerprinting."""
    dirty_info = archify_registry.compute_dirty_set(reg_dir, project_root)
    reg_index = archify_registry.sync_registry_index(reg_dir, project_root, include_planned=False)
    nodes, node_paths, _ = archify_registry._load_registry_nodes(reg_dir)
    _verify_node_sources_confined(nodes, project_root)
    if reg_cfg.get("root_flows"):
        missing = [rf for rf in reg_cfg["root_flows"] if rf not in nodes]
        if missing:
            raise ValueError(f"master.registry.root_flows references unknown node(s): {missing}")
        reg_index["root_flows"] = list(reg_cfg["root_flows"])
    if reg_cfg.get("max_depth") is not None:
        reg_index["max_depth"] = int(reg_cfg["max_depth"])
    _log(f"registry pre-sync: nodes={len(nodes)} dirty_slices={dirty_info['dirty_slices']}")
    return {
        "reg_dir": reg_dir,
        "reg_cfg": reg_cfg,
        "dirty_info": dirty_info,
        "reg_index": reg_index,
        "nodes": nodes,
        "node_paths": node_paths,
    }


def _compute_slice_hash(owner_nodes: list[dict[str, Any]]) -> str:
    """Compute deterministic combined AST + sub_flow hash for a slice."""
    payload = [
        {
            "node_id": n["node_id"],
            "ast_symbol_sha256": n["fingerprint"].get("ast_symbol_sha256"),
            "sub_flow": n.get("sub_flow"),
        }
        for n in sorted(owner_nodes, key=lambda item: item["node_id"])
    ]
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _wf_node_id(step: dict[str, Any], used_ids: set[str]) -> str:
    """Choose a schema-safe workflow node id preserving target_node_id when unique."""
    target = step.get("target_node_id")
    if isinstance(target, str) and _WORKFLOW_ID_RE.fullmatch(target) and target not in used_ids:
        used_ids.add(target)
        return target
    raw = str(step.get("step_id") or "step")
    cleaned = re.sub(r"[^a-zA-Z0-9_-]", "_", raw)
    if not cleaned or not cleaned[0].isalpha():
        cleaned = f"s_{cleaned}"
    cand, idx = cleaned, 2
    while cand in used_ids:
        cand, idx = f"{cleaned}_{idx}", idx + 1
    used_ids.add(cand)
    return cand


def _build_slice_workflow_candidate(
    owner_nodes: list[dict[str, Any]],
    slice_id: str,
    quality: str,
    doc_lang: str,
) -> dict[str, Any]:
    """Build valid workflow v2 candidate JSON from owning node sub_flow."""
    primary = owner_nodes[0]
    sub_flow = primary.get("sub_flow") or {}
    lane_defs = {
        "main": {"id": "main", "label": "Main Flow", "variant": "normal"},
        "branch": {"id": "branch", "label": "Branch", "variant": "normal"},
        "error": {"id": "error", "label": "Error Path", "variant": "exception"},
    }
    used_ids: set[str] = set()
    step_to_wf: dict[str, str] = {}
    lanes_seen: list[str] = []
    wf_nodes: list[dict[str, Any]] = []
    for idx, step in enumerate(sub_flow.get("steps", [])):
        lane = str(step.get("lane") or "main")
        if lane not in lane_defs:
            lane = "main"
        if lane not in lanes_seen:
            lanes_seen.append(lane)
        wf_id = _wf_node_id(step, used_ids)
        step_to_wf[str(step["step_id"])] = wf_id
        ntype = "security" if lane == "error" else ("cloud" if lane == "branch" else "backend")
        entry: dict[str, Any] = {
            "id": wf_id,
            "lane": lane,
            "col": max(0, min(5, int(step.get("col", idx)))),
            "type": ntype,
            "label": str(step.get("label") or step["step_id"]),
        }
        if step.get("cycle_back_to"):
            entry["sublabel"] = f"cycle -> {step['cycle_back_to']}"
        wf_nodes.append(entry)
    wf_edges = _build_slice_workflow_edges(sub_flow.get("edges", []), step_to_wf)
    locale = "vi" if str(doc_lang).strip().lower().startswith("vi") else "en"
    return {
        "schema_version": 2,
        "diagram_type": "workflow",
        "meta": {"title": str(primary.get("title") or slice_id), "output": f"{slice_id}.html", "locale": locale, "quality_profile": quality},
        "lanes": [lane_defs[ln] for ln in (lanes_seen or ["main"])],
        "nodes": wf_nodes,
        "edges": wf_edges,
    }


def _build_slice_workflow_edges(raw_edges: list[dict[str, Any]], step_to_wf: dict[str, str]) -> list[dict[str, Any]]:
    """Map sub_flow edges to schema-valid workflow edges."""
    edges: list[dict[str, Any]] = []
    for idx, edge in enumerate(raw_edges):
        src = step_to_wf.get(str(edge.get("from", "")))
        dst = step_to_wf.get(str(edge.get("to", "")))
        if not src or not dst or src == dst:
            continue
        item: dict[str, Any] = {"id": f"e_{idx}", "from": src, "to": dst, "variant": "default"}
        if isinstance(edge.get("label"), str) and edge["label"].strip():
            item["label"] = edge["label"].strip()
        edges.append(item)
    return edges


def _build_placeholder_svg(owner_nodes: list[dict[str, Any]], slice_id: str) -> str:
    """Build clean fallback SVG without inline handlers when rendered HTML lacks <svg>."""
    steps = (owner_nodes[0].get("sub_flow") or {}).get("steps", [])
    groups: list[str] = []
    for idx, step in enumerate(steps):
        target_id = str(step.get("target_node_id") or step.get("step_id") or f"step-{idx}")
        label = str(step.get("label") or target_id)
        x = 24 + idx * 172
        groups.append(
            f'<g id="node-{html.escape(target_id, quote=True)}" '
            f'data-node-id="{html.escape(target_id, quote=True)}" '
            f'data-node-label="{html.escape(label, quote=True)}" tabindex="0" role="button">'
            f'<rect x="{x}" y="30" width="144" height="56" rx="8" class="c-backend"/>'
            f'<text x="{x + 72}" y="62" class="t-primary" text-anchor="middle">{html.escape(label)}</text>'
            f"</g>"
        )
    width = max(420, len(steps) * 172 + 48)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} 140" '
        f'data-slice-id="{html.escape(slice_id, quote=True)}">{"".join(groups)}</svg>'
    )


def _extract_svg_from_html(html_text: str, owner_nodes: list[dict[str, Any]], slice_id: str) -> str:
    """Extract verbatim <svg>...</svg> from HTML or return clean placeholder SVG."""
    matches = _SVG_BLOCK_RE.findall(html_text)
    if matches:
        return max(matches, key=lambda m: (1 if "data-node-id" in m else 0, len(m)))
    return _build_placeholder_svg(owner_nodes, slice_id)


def _render_single_slice(
    slice_id: str,
    owner_nodes: list[dict[str, Any]],
    staging_dir: Path,
    project_root: Path,
    quality: str,
    doc_lang: str,
) -> str:
    """Render one dirty or missing sub-flow slice to clean SVG text."""
    view_html = staging_dir / f"{slice_id}.html"
    if view_html.is_file():
        _log(f"extracting slice svg from view html slice_id={slice_id}")
        return _extract_svg_from_html(view_html.read_text(encoding="utf-8"), owner_nodes, slice_id)

    cand_payload = _build_slice_workflow_candidate(owner_nodes, slice_id, quality, doc_lang)
    with tempfile.TemporaryDirectory(prefix="tdq-slice-") as tmp_dir:
        tmp_root = Path(tmp_dir)
        tmp_cand = tmp_root / "cand.json"
        tmp_html = tmp_root / "slice.html"
        tmp_cand.write_text(json.dumps(cand_payload, indent=2, ensure_ascii=False), encoding="utf-8")
        res = run_finalize(
            diagram_type="workflow",
            candidate_path=tmp_cand,
            output_path=tmp_html,
            quality=quality,
            repo_root=project_root,
        )
        if not res.status or not tmp_html.is_file():
            raise RuntimeError(f"Failed to finalize slice '{slice_id}': {res.receipt}")
        _log(f"rendered dirty slice_id={slice_id}")
        return _extract_svg_from_html(tmp_html.read_text(encoding="utf-8"), owner_nodes, slice_id)


def _should_render_slice(
    slice_id: str,
    slice_hash: str,
    dirty_slices: set[str],
    dest_dir: Path,
    prior_manifest: dict[str, Any] | None,
    incremental: bool,
) -> bool:
    """Decide whether slice_id must be rendered or can be reused from dest_dir/slices."""
    if not incremental or slice_id in dirty_slices or prior_manifest is None:
        return True
    dest_svg = dest_dir / "slices" / f"{slice_id}.svg"
    if not dest_svg.is_file():
        return True
    prior_cache = (prior_manifest.get("slice_cache") or {}).get(slice_id)
    if not isinstance(prior_cache, dict) or prior_cache.get("hash") != slice_hash:
        return True
    exp_child = str((prior_manifest.get("child_files") or {}).get(f"slices/{slice_id}.svg") or "").lower()
    return not exp_child or _hash_file(dest_svg).lower() != exp_child


def _stage_registry_slices(
    slice_owners: dict[str, list[dict[str, Any]]],
    staging_dir: Path,
    dest_dir: Path,
    prior_manifest: dict[str, Any] | None,
    dirty_slices: set[str],
    project_root: Path,
    quality: str,
    doc_lang: str,
    incremental: bool,
) -> tuple[dict[str, str], dict[str, str], dict[str, dict[str, str]]]:
    """Render dirty/missing slices and reuse clean slices into staging_dir/slices."""
    slices_dir = staging_dir / "slices"
    slices_dir.mkdir(parents=True, exist_ok=True)
    slices_map: dict[str, str] = {}
    slice_children: dict[str, str] = {}
    slice_cache: dict[str, dict[str, str]] = {}

    for sid in sorted(slice_owners):
        owners = slice_owners[sid]
        s_hash = _compute_slice_hash(owners)
        out_svg = slices_dir / f"{sid}.svg"
        if _should_render_slice(sid, s_hash, dirty_slices, dest_dir, prior_manifest, incremental):
            svg_text = _render_single_slice(sid, owners, staging_dir, project_root, quality, doc_lang)
            out_svg.write_text(svg_text, encoding="utf-8")
        else:
            svg_text = (dest_dir / "slices" / f"{sid}.svg").read_text(encoding="utf-8")
            out_svg.write_text(svg_text, encoding="utf-8")
            _log(f"reused clean slice_id={sid}")
        slices_map[sid] = svg_text
        slice_children[f"slices/{sid}.svg"] = _hash_file(out_svg)
        slice_cache[sid] = {"hash": s_hash}
    return slices_map, slice_children, slice_cache


def _populate_registry_staging(
    reg_ctx: dict[str, Any],
    validated_model: dict[str, Any],
    staging_dir: Path,
    dest_dir: Path,
    prior_manifest: dict[str, Any] | None,
    child_files: dict[str, str],
    project_root: Path,
    quality: str,
    doc_lang: str,
    incremental: bool,
) -> dict[str, dict[str, str]]:
    """Stage slices, nodes JSON, registry-bundle.js, and lazy portal index.html."""
    nodes = reg_ctx["nodes"]
    slice_owners: dict[str, list[dict[str, Any]]] = {}
    for nid in sorted(nodes):
        sf = nodes[nid].get("sub_flow")
        if isinstance(sf, dict) and sf.get("slice_id"):
            slice_owners.setdefault(str(sf["slice_id"]), []).append(nodes[nid])

    slices_map, slice_children, slice_cache = _stage_registry_slices(
        slice_owners, staging_dir, dest_dir, prior_manifest,
        set(reg_ctx["dirty_info"].get("dirty_slices", [])), project_root, quality, doc_lang, incremental,
    )
    child_files.update(slice_children)

    nodes_dir = staging_dir / "nodes"
    nodes_dir.mkdir(parents=True, exist_ok=True)
    for nid in sorted(nodes):
        dst_node = nodes_dir / f"{nid}.json"
        dst_node.write_text(reg_ctx["node_paths"][nid].read_text(encoding="utf-8"), encoding="utf-8")
        child_files[f"nodes/{nid}.json"] = _hash_file(dst_node)

    bundle_path = staging_dir / "registry-bundle.js"
    bundle_path.write_text(
        archify_portal.build_registry_bundle_js(reg_ctx["reg_index"], slices_map, nodes), encoding="utf-8"
    )
    child_files["registry-bundle.js"] = _hash_file(bundle_path)

    shell_html = archify_portal.build_portal_shell(
        reg_ctx["reg_index"], slices_map, nodes,
        mode="lazy", title=str(validated_model.get("title") or "Archify Portal"), doc_lang=doc_lang,
    )
    if len(shell_html.encode("utf-8")) >= 300_000:
        raise RuntimeError("Portal shell index.html exceeded 300_000 byte lazy budget")
    (staging_dir / "index.html").write_text(shell_html, encoding="utf-8")
    return slice_cache


def _build_legacy_index_to_staging(
    validated_model: dict[str, Any],
    rendered_views: list[dict],
    staging_dir: Path,
    project_root: Path,
    quality: str,
    doc_lang: str,
    child_files: dict[str, str],
    receipts: dict[str, Any],
) -> None:
    """Build index.html via explainer finalize or legacy HTML table when registry is absent."""
    index_out = staging_dir / "index.html"
    if "master" not in validated_model:
        index_out.write_text(_generate_index_html(validated_model, rendered_views), encoding="utf-8")
        return
    master_cand = staging_dir / "master.candidate.json"
    master_cand.write_text(
        json.dumps(_build_master_explainer(validated_model, quality, doc_lang=doc_lang), indent=2),
        encoding="utf-8",
    )
    res = run_finalize(
        diagram_type="explainer", candidate_path=master_cand, output_path=index_out,
        quality=quality, repo_root=project_root,
    )
    if not res.status or not index_out.is_file():
        raise RuntimeError(f"Failed to finalize master explainer: {res.receipt}")
    if doc_lang.startswith("vi"):
        index_out.write_text(_localize_explainer_html_vi(index_out.read_text(encoding="utf-8")), encoding="utf-8")
    child_files["master.candidate.json"] = _hash_file(master_cand)
    receipts["master"] = res.receipt


def _execute_sync_staging(
    project_root: Path,
    dest_dir: Path,
    staging_dir: Path,
    model_file: Path,
    validated_model: dict[str, Any],
    reg_ctx: dict[str, Any] | None,
    quality: str,
    incremental: bool,
    full: bool,
) -> Path:
    """Execute staging build and atomic publication for master sync."""
    use_incremental = bool(incremental) and not bool(full) and (reg_ctx is not None)
    reg_dir = reg_ctx["reg_dir"] if reg_ctx is not None else None
    source_paths = _derive_stable_source_paths(
        project_root, dest_dir, model_file, validated_model, reg_dir=reg_dir
    )
    pre_sources = source_fingerprint(project_root, paths=source_paths)
    pre_model_hash = _hash_file(model_file)
    prior_manifest = _load_prior_manifest(dest_dir) if use_incremental else None

    rendered_views, child_files, receipts = _render_views_to_staging(
        validated_model.get("views", []), model_file.parent.resolve(), staging_dir, project_root, quality,
        dest_dir=dest_dir, prior_manifest=prior_manifest, pre_sources=pre_sources,
        validated_model=validated_model, incremental=use_incremental,
    )
    doc_lang = _read_doc_lang(project_root)
    slice_cache: dict[str, dict[str, str]] | None = None
    if reg_ctx is not None:
        slice_cache = _populate_registry_staging(
            reg_ctx, validated_model, staging_dir, dest_dir, prior_manifest,
            child_files, project_root, quality, doc_lang, use_incremental,
        )
    else:
        _build_legacy_index_to_staging(
            validated_model, rendered_views, staging_dir, project_root, quality, doc_lang, child_files, receipts
        )
    return _build_and_publish_manifest(
        project_root, dest_dir, staging_dir, model_file, validated_model,
        rendered_views, child_files, receipts,
        source_paths=source_paths, pre_sources=pre_sources, pre_model_hash=pre_model_hash, slice_cache=slice_cache,
    )


def sync_master(
    model: str | Path | None = None,
    project: str | Path | None = None,
    out: str | Path | None = None,
    *,
    graph_path: str | Path | None = None,
    out_path: str | Path | None = None,
    max_nodes: int = 25,
    quality: str = "showcase",
    incremental: bool = True,
    full: bool = False,
) -> bool:
    """Synchronize Master architecture bundle (legacy or incremental portal registry)."""
    if graph_path is not None and model is None:
        return _sync_legacy_graph(graph_path, out_path, max_nodes)
    paths = _resolve_sync_paths(model, project, out)
    if paths is None:
        return False
    project_root, dest_dir, model_file = paths
    validated_model = _load_and_validate_model(model_file)
    if validated_model is None or not _verify_committed_revision(project_root, validated_model, model_file):
        return False
    if not _verify_candidate_confinement(model_file, validated_model.get("views", [])):
        return False
    if not _verify_master_sources(validated_model, project_root):
        return False

    dest_dir.parent.mkdir(parents=True, exist_ok=True)
    staging_dir = dest_dir.parent / f".staging.{uuid.uuid4().hex}"
    staging_dir.mkdir(parents=True, exist_ok=True)
    try:
        reg_pair = _resolve_registry_config(validated_model, project_root)
        reg_ctx = _sync_registry_context(reg_pair[0], reg_pair[1], project_root) if reg_pair else None
        published_index = _execute_sync_staging(
            project_root, dest_dir, staging_dir, model_file, validated_model, reg_ctx, quality, incremental, full
        )
        _log(f"sync_master published index={published_index} incremental={bool(incremental and not full)}")
        print(f"Master architecture published: {published_index}")
        return True
    except (OSError, ValueError, RuntimeError, TypeError, LookupError, subprocess.SubprocessError) as exc:
        sys.stderr.write(f"Error during sync_master: {exc}\n")
        return False
    finally:
        if staging_dir.exists():
            shutil.rmtree(staging_dir, ignore_errors=True)


def check_master_status(project: str | Path | None = None) -> dict:
    """Inspect status of Master architecture bundle, freshness, and child tampering."""
    project_root = Path(project).resolve() if project else Path.cwd().resolve()
    manifest_path = project_root / "docs" / "architecture" / "manifest.json"
    if not manifest_path.is_file():
        return {"status": "absent", "reasons": [f"Master manifest not found: {manifest_path}"]}

    res = check_manifest(project_root, manifest_path)
    status_val = res.get("status", "invalid")
    reasons = list(res.get("reasons", []))
    try:
        man_data = json.loads(manifest_path.read_text(encoding="utf-8"))
        bundle_dir = manifest_path.parent
        for child_name, exp_hash in man_data.get("child_files", {}).items():
            child_file = bundle_dir / child_name
            if not child_file.is_file():
                reasons.append(f"Child file missing: {child_name}")
                status_val = "stale" if status_val == "current" else status_val
            elif _hash_file(child_file).lower() != exp_hash.lower():
                reasons.append(f"Child file tampered: {child_name}")
                status_val = "stale" if status_val == "current" else status_val
    except (OSError, ValueError, TypeError) as exc:
        reasons.append(f"Error reading manifest child files: {exc}")
        status_val = "invalid"
    return {
        "status": status_val,
        "reasons": reasons,
        "manifest_path": manifest_path.relative_to(project_root).as_posix(),
    }


def _check_bundle_child_tampering(man_path: Path) -> list[str]:
    """Return list of missing or tampered child_files declared in manifest."""
    tamper_reasons: list[str] = []
    try:
        man_data = json.loads(man_path.read_text(encoding="utf-8"))
        bundle_dir = man_path.parent
        for child_name, exp_hash in man_data.get("child_files", {}).items():
            child_file = bundle_dir / child_name
            if not child_file.is_file():
                tamper_reasons.append(f"Child file missing: {child_name}")
            elif _hash_file(child_file).lower() != exp_hash.lower():
                tamper_reasons.append(f"Child file tampered: {child_name}")
    except (OSError, ValueError, TypeError) as exc:
        _log(f"skipped child check while reading {man_path}: {exc}")
    return tamper_reasons


def verify_document_and_manifest(
    document: str | Path,
    manifest: str | Path,
    project: str | Path | None = None,
) -> dict:
    """Verify document binding and manifest freshness."""
    project_root = Path(project).resolve() if project else Path.cwd().resolve()
    doc_path = Path(document) if Path(document).is_absolute() else (project_root / document).resolve()
    man_path = Path(manifest) if Path(manifest).is_absolute() else (project_root / manifest).resolve()
    if not doc_path.is_file():
        return {"status": "invalid", "reasons": [f"Document not found: {doc_path}"]}
    if not man_path.is_file():
        return {"status": "invalid", "reasons": [f"Manifest not found: {man_path}"]}

    b_res = check_binding(doc_path, man_path)
    m_res = check_manifest(project_root, man_path)
    reasons: list[str] = []
    if not b_res.get("valid") or b_res.get("status") != "current":
        reasons.extend(b_res.get("reasons", []))
    if m_res.get("status") != "current":
        reasons.extend(m_res.get("reasons", []))
    reasons.extend(_check_bundle_child_tampering(man_path))

    if "invalid" in (b_res.get("status"), m_res.get("status")):
        status_val = "invalid"
    elif reasons:
        status_val = "stale"
    else:
        status_val = "current"
    return {"status": status_val, "reasons": reasons, "binding": b_res, "manifest": m_res}


def handle_check(_args: argparse.Namespace) -> int:
    """Handle CLI check sub-command."""
    try:
        res = check_environment()
        print(json.dumps(res, indent=2))
        return 0 if res.get("ready") else 1
    except (OSError, RuntimeError, ValueError) as exc:
        sys.stderr.write(f"Error checking environment: {exc}\n")
        return 1


def _prepare_render_paths(args: argparse.Namespace) -> tuple[Path, Path, Path, Path | None, bytes | None]:
    """Validate inputs and resolve project_root, cand_path, out_path, doc_path."""
    project_root = Path(args.repo_root).resolve() if args.repo_root else Path.cwd().resolve()
    if not project_root.is_dir():
        raise FileNotFoundError(f"Project root not found: {project_root}")

    cand_path = Path(args.candidate) if Path(args.candidate).is_absolute() else (project_root / args.candidate).resolve()
    if not cand_path.is_file():
        raise FileNotFoundError(f"Candidate file not found: {cand_path}")
    out_path = Path(args.out) if Path(args.out).is_absolute() else (project_root / args.out).resolve()

    doc_path: Path | None = None
    doc_original_bytes: bytes | None = None
    if args.document:
        doc_path = Path(args.document) if Path(args.document).is_absolute() else (project_root / args.document).resolve()
        if not doc_path.is_file():
            raise FileNotFoundError(f"Document file not found: {doc_path}")
        doc_original_bytes = doc_path.read_bytes()
    return project_root, cand_path, out_path, doc_path, doc_original_bytes


def _promote_staged_artifacts(temp_out: Path, out_path: Path) -> list[Path]:
    """Promote staged HTML artifact and any matching engine sidecars to final destination."""
    promoted: list[Path] = []
    temp_dir = temp_out.parent
    temp_prefix = temp_out.stem
    os.replace(temp_out, out_path)
    promoted.append(out_path)

    for item in temp_dir.glob(f"{temp_prefix}*"):
        if item.is_file() and item != temp_out:
            suffix = item.name[len(temp_prefix):]
            dest_item = out_path.parent / f"{out_path.stem}{suffix}"
            try:
                os.replace(item, dest_item)
                promoted.append(dest_item)
            except OSError as exc:
                _log(f"failed promoting sidecar {item.name}: {exc}")
    return promoted


def _deliver_render_manifest(
    project_root: Path,
    doc_path: Path,
    cand_path: Path,
    out_path: Path,
    manifest_path: Path,
    receipt: dict,
    evidence_kind: str,
    request: str | None,
    lane: str | None,
) -> None:
    """Build manifest with outputs excluded from source_paths, deliver atomically, and bind doc."""
    all_sources = source_fingerprint(project_root)
    excluded_rel: set[str] = set()
    for p in (out_path, manifest_path, cand_path, doc_path, out_path.with_suffix(".receipt.json")):
        if _is_within(p, project_root):
            excluded_rel.add(p.resolve().relative_to(project_root).as_posix())
    clean_sources = [s for s in all_sources if s not in excluded_rel]
    manifest = build_manifest(
        project=project_root, document=doc_path, candidate=cand_path, artifact=out_path,
        receipt=receipt, evidence_kind=evidence_kind, request=request, lane=lane, source_paths=clean_sources,
    )
    atomic_delivery(manifest_path, json.dumps(manifest, indent=2, ensure_ascii=False))
    bind_document(doc_path, manifest_path)


def _restore_or_unlink(had_orig: bool, backup_path: Path, target_path: Path) -> None:
    """Restore target_path from backup_path if it existed, else unlink newly created target."""
    if had_orig:
        if backup_path.is_file():
            try:
                os.replace(backup_path, target_path)
            except OSError as exc:
                sys.stderr.write(
                    f"Warning: Failed to restore {target_path} from backup. "
                    f"Backup preserved at: {backup_path} (error: {exc})\n"
                )
        return
    if target_path.exists():
        try:
            target_path.unlink()
        except OSError as exc:
            _log(f"failed cleanup of {target_path}: {exc}")


def _rollback_render_transaction(
    had_out: bool,
    backup_out: Path,
    out_path: Path,
    had_manifest: bool,
    backup_manifest: Path,
    manifest_path: Path,
    had_receipt: bool,
    backup_receipt: Path,
    receipt_path: Path,
    doc_path: Path | None,
    doc_original_bytes: bytes | None,
    temp_out: Path,
) -> None:
    """Full transactional rollback preserving backup if restore fails."""
    _restore_or_unlink(had_out, backup_out, out_path)
    _restore_or_unlink(had_manifest, backup_manifest, manifest_path)
    _restore_or_unlink(had_receipt, backup_receipt, receipt_path)
    if doc_path and doc_original_bytes is not None:
        try:
            doc_path.write_bytes(doc_original_bytes)
        except OSError as exc:
            sys.stderr.write(f"Warning: Failed to restore document content: {exc}\n")
    if temp_out.exists():
        try:
            temp_out.unlink()
        except OSError as exc:
            _log(f"failed removing temp output {temp_out}: {exc}")


def _render_drilldown_to_temp(cand_path: Path, temp_out: Path, project_root: Path) -> FinalizeResult:
    """Render standalone <= 4 level drill-down HTML via archify_portal without calling node."""
    try:
        candidate = json.loads(cand_path.read_text(encoding="utf-8"))
        doc_lang = _read_doc_lang(project_root)
        html_text = archify_portal.render_drilldown_standalone(candidate, doc_lang=doc_lang)
        temp_out.write_text(html_text, encoding="utf-8")
        _log(f"rendered standalone drilldown candidate={cand_path.name} bytes={len(html_text.encode('utf-8'))}")
        return FinalizeResult(
            status=True,
            receipt={"ok": True, "status": "pass", "engine": "archify-portal", "diagram_type": "drilldown"},
        )
    except (OSError, ValueError, TypeError) as exc:
        temp_out.unlink(missing_ok=True)
        _log(f"drilldown render failed: {exc}")
        sys.stderr.write(f"Error: Drilldown render failed: {exc}\n")
        return FinalizeResult(
            status=False,
            receipt={"ok": False, "status": "fail", "engine": "archify-portal", "diagram_type": "drilldown", "error": str(exc)},
        )


def _run_localized_finalize(
    diagram_type: str,
    cand_path: Path,
    temp_out: Path,
    quality: str,
    project_root: Path,
) -> FinalizeResult:
    """Dispatch drilldown to archify_portal or run finalize with explainer locale handling."""
    if diagram_type == "drilldown":
        return _render_drilldown_to_temp(cand_path, temp_out, project_root)
    effective_cand, temp_cand = (cand_path, None)
    if diagram_type == "explainer":
        effective_cand, temp_cand = _ensure_explainer_locale_candidate(cand_path, cand_path.parent)
    try:
        result = run_finalize(
            diagram_type=diagram_type,
            candidate_path=effective_cand,
            output_path=temp_out,
            quality=quality,
            repo_root=project_root,
        )
    finally:
        if temp_cand and temp_cand.exists():
            with contextlib.suppress(OSError):
                temp_cand.unlink()
    if result.status and temp_out.is_file() and diagram_type == "explainer" and _read_doc_lang(project_root).startswith("vi"):
        temp_out.write_text(_localize_explainer_html_vi(temp_out.read_text(encoding="utf-8")), encoding="utf-8")
    return result


def _publish_render_outputs(
    args: argparse.Namespace,
    project_root: Path,
    cand_path: Path,
    out_path: Path,
    doc_path: Path | None,
    temp_out: Path,
    receipt: dict,
    backups: tuple[Path, Path, Path],
    hads: tuple[bool, bool, bool],
) -> dict[str, Any]:
    """Promote staged outputs, write receipt/manifest, bind document, and prune backups."""
    backup_out, backup_manifest, backup_receipt = backups
    had_out, had_manifest, had_receipt = hads
    manifest_path = out_path.with_suffix(".manifest.json")
    receipt_path = out_path.with_suffix(".receipt.json")
    if had_out:
        shutil.copy2(out_path, backup_out)
    if had_manifest:
        shutil.copy2(manifest_path, backup_manifest)
    if had_receipt:
        shutil.copy2(receipt_path, backup_receipt)
    _promote_staged_artifacts(temp_out, out_path)
    atomic_delivery(receipt_path, json.dumps(receipt, indent=2, ensure_ascii=False))
    response: dict[str, Any] = {
        **receipt, "published_artifact": str(out_path), "artifact_path": str(out_path), "receipt_path": str(receipt_path),
    }
    if not doc_path:
        response.update({"binding": "unbound", "binding_status": "artifact_unbound"})
        if had_out and backup_out.exists():
            backup_out.unlink()
        return response
    _deliver_render_manifest(
        project_root, doc_path, cand_path, out_path, manifest_path,
        receipt, args.evidence_kind or "planned", args.request, args.lane,
    )
    for had, bpath in zip(hads, backups, strict=True):
        if had and bpath.exists():
            bpath.unlink()
    response.update({
        "binding": "bound", "binding_status": "registered", "manifest_path": str(manifest_path), "document_bound": str(doc_path),
    })
    return response


def handle_render(args: argparse.Namespace) -> int:
    """Handle CLI render sub-command with staging and transactional rollback."""
    try:
        project_root, cand_path, out_path, doc_path, doc_original_bytes = _prepare_render_paths(args)
    except FileNotFoundError as fnf:
        sys.stderr.write(f"Error: {fnf}\n")
        return 1
    except (OSError, ValueError, TypeError) as exc:
        sys.stderr.write(f"Error validating render arguments: {exc}\n")
        return 1

    out_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path = out_path.with_suffix(".manifest.json")
    receipt_path = out_path.with_suffix(".receipt.json")
    temp_out = out_path.parent / f".tmp.{out_path.stem}.{uuid.uuid4().hex}.html"
    backups = (
        out_path.parent / f".bak.{out_path.stem}.{uuid.uuid4().hex}.html",
        out_path.parent / f".bak.{manifest_path.stem}.{uuid.uuid4().hex}.json",
        out_path.parent / f".bak.{receipt_path.stem}.{uuid.uuid4().hex}.json",
    )
    hads = (out_path.is_file(), manifest_path.is_file(), receipt_path.is_file())

    try:
        result = _run_localized_finalize(args.type, cand_path, temp_out, args.quality, project_root)
        if not result.status or not temp_out.is_file():
            temp_out.unlink(missing_ok=True)
            print(json.dumps(result.receipt if isinstance(result.receipt, dict) else {"ok": False}, indent=2))
            return 1
        receipt = dict(result.receipt) if isinstance(result.receipt, dict) else {}
        response = _publish_render_outputs(args, project_root, cand_path, out_path, doc_path, temp_out, receipt, backups, hads)
        print(json.dumps(response, indent=2))
        return 0
    except (OSError, ValueError, RuntimeError, TypeError, subprocess.SubprocessError) as proc_exc:
        _rollback_render_transaction(
            hads[0], backups[0], out_path, hads[1], backups[1], manifest_path,
            hads[2], backups[2], receipt_path, doc_path, doc_original_bytes, temp_out,
        )
        sys.stderr.write(f"Error during render publication: {proc_exc}\n")
        return 1


def handle_open(args: argparse.Namespace) -> int:
    """Handle CLI open sub-command."""
    try:
        return 0 if open_artifact(args.file_path) else 1
    except (OSError, ValueError, RuntimeError) as exc:
        sys.stderr.write(f"Error opening artifact: {exc}\n")
        return 1


def handle_bridge(args: argparse.Namespace) -> int:
    """Handle CLI bridge sub-command with structured error handling."""
    try:
        ir = graphify_to_archify(
            graph_json_path=args.graph,
            focus_community=args.community,
            max_nodes=args.max_nodes,
            evidence_kind=args.evidence_kind,
        )
        atomic_delivery(args.out, json.dumps(ir, indent=2, ensure_ascii=False))
        selected_ids = [c["id"] for c in ir.get("components", []) if c.get("id")]
        cov = graph_coverage(args.graph, selected_ids=selected_ids)
        sidecar_path = Path(args.out).with_suffix(".coverage.json")
        atomic_delivery(sidecar_path, json.dumps(cov, indent=2, ensure_ascii=False))
        print(f"Archify JSON-IR generated: {args.out}")
        print(f"Coverage sidecar generated: {sidecar_path}")
        return 0
    except (ValueError, OSError, json.JSONDecodeError, FileNotFoundError, TypeError) as exc:
        sys.stderr.write(f"Error during bridge conversion: {exc}\n")
        return 1


def handle_test_bridge(_args: argparse.Namespace) -> int:
    """Handle CLI test-bridge sub-command."""
    try:
        return 0 if test_bridge() else 1
    except (AssertionError, ValueError, KeyError) as exc:
        sys.stderr.write(f"Test failed: {exc}\n")
        return 1


def handle_sync_master(args: argparse.Namespace) -> int:
    """Handle CLI sync-master sub-command with structured error handling."""
    full_flag = bool(getattr(args, "full", False))
    inc_flag = bool(getattr(args, "incremental", True)) and not full_flag
    try:
        ok = sync_master(
            model=args.model,
            project=args.project,
            out=args.out,
            graph_path=args.graph,
            max_nodes=args.max_nodes,
            quality=args.quality,
            incremental=inc_flag,
            full=full_flag,
        )
        return 0 if ok else 1
    except (ValueError, OSError, json.JSONDecodeError, FileNotFoundError, TypeError) as exc:
        sys.stderr.write(f"Error during sync-master: {exc}\n")
        return 1


def handle_status(args: argparse.Namespace) -> int:
    """Handle CLI status sub-command."""
    try:
        res = check_master_status(project=args.project)
        print(json.dumps(res, indent=2))
        return 0 if res.get("status") == "current" else 1
    except (OSError, ValueError, TypeError) as exc:
        sys.stderr.write(f"Error inspecting status: {exc}\n")
        return 1


def handle_verify(args: argparse.Namespace) -> int:
    """Handle CLI verify sub-command."""
    try:
        res = verify_document_and_manifest(
            document=args.document, manifest=args.manifest, project=args.project
        )
        print(json.dumps(res, indent=2))
        return 0 if res.get("status") == "current" else 1
    except (OSError, ValueError, TypeError) as exc:
        sys.stderr.write(f"Error during verify: {exc}\n")
        return 1


def _wait_for_serve_exit() -> None:
    """Block until KeyboardInterrupt/SIGINT wakes the loop."""
    stop_event = threading.Event()
    while not stop_event.wait(0.25):
        pass


def handle_serve(args: argparse.Namespace) -> int:
    """Handle CLI serve sub-command over loopback HTTP."""
    raw_dir = Path(args.directory)
    target_dir = raw_dir if raw_dir.is_absolute() else (Path.cwd() / raw_dir)
    server = None
    try:
        server, url = serve_directory(
            target_dir, host=args.host, port=args.port, open_browser=args.open
        )
        _log(f"serving directory={target_dir.resolve()} url={url}")
        print(json.dumps({"url": url, "directory": str(target_dir.resolve())}, indent=2))
        sys.stdout.flush()
        _wait_for_serve_exit()
        return 0
    except KeyboardInterrupt:
        _log("serve stopped by interrupt")
        return 0
    except (ValueError, FileNotFoundError, OSError) as exc:
        sys.stderr.write(f"Error serving directory: {exc}\n")
        return 1
    finally:
        if server is not None:
            with contextlib.suppress(OSError, RuntimeError):
                server.shutdown()
                server.server_close()


def _add_render_and_bridge_parsers(subparsers: Any) -> None:
    """Register render, open, bridge, and test-bridge subparsers."""
    rp = subparsers.add_parser("render", help="Render diagram to standalone HTML via finalize or drilldown portal")
    rp.add_argument("--type", required=True, help="Diagram type (workflow, architecture, sequence, drilldown, ...)")
    rp.add_argument("--candidate", required=True, help="Path to input candidate JSON")
    rp.add_argument("--out", required=True, help="Path to output HTML artifact")
    rp.add_argument("--quality", default="showcase", choices=["standard", "showcase"], help="Rendering quality")
    rp.add_argument("--repo-root", "--project", dest="repo_root", default=None, help="Root path of target repository")
    rp.add_argument("--document", default=None, help="Path to document to bind (markdown)")
    rp.add_argument("--request", default=None, help="Request slug")
    rp.add_argument("--lane", default=None, help="Lane identifier (full, quick)")
    rp.add_argument("--evidence-kind", default="planned", help="Evidence kind (planned, working-tree, committed, partial)")

    op = subparsers.add_parser("open", help="Open artifact safely in default browser")
    op.add_argument("file_path", help="Path to file to open")

    bp = subparsers.add_parser("bridge", help="Convert Graphify graph.json to Archify JSON-IR and coverage sidecar")
    bp.add_argument("--graph", required=True, help="Path to input graph.json")
    bp.add_argument("--out", required=True, help="Path to output architecture JSON-IR")
    bp.add_argument("--community", default=None, help="Filter by community id")
    bp.add_argument("--max-nodes", type=int, default=25, help="Maximum number of nodes (default: 25)")
    bp.add_argument("--evidence-kind", default="working-tree", help="Evidence kind (default: working-tree)")

    subparsers.add_parser("test-bridge", help="Self-test graphify-to-archify conversion logic")


def _add_sync_and_lifecycle_parsers(subparsers: Any) -> None:
    """Register sync-master, status, verify, and serve subparsers."""
    sp = subparsers.add_parser("sync-master", help="Synchronize master architecture bundle")
    sp.add_argument("--model", default=None, help="Path to master model JSON (default: docs/architecture/master.model.json)")
    sp.add_argument("--project", default=None, help="Target project root directory")
    sp.add_argument("--out", default=None, help="Output destination directory (default: docs/architecture)")
    sp.add_argument("--quality", default="showcase", choices=["standard", "showcase"], help="Rendering quality")
    sp.add_argument("--graph", default=None, help="Path to input graph.json (legacy mode)")
    sp.add_argument("--max-nodes", type=int, default=25, help="Maximum number of nodes (legacy mode)")
    sp.add_argument("--incremental", action="store_true", default=True, help="Reuse clean slices when registry is present")
    sp.add_argument("--full", action="store_true", default=False, help="Force full rebuild of all views and slices")

    stp = subparsers.add_parser("status", help="Inspect status and freshness of master architecture")
    stp.add_argument("--project", default=None, help="Target project root directory")

    vp = subparsers.add_parser("verify", help="Verify document binding and manifest integrity")
    vp.add_argument("--document", required=True, help="Path to document file (markdown)")
    vp.add_argument("--manifest", required=True, help="Path to manifest JSON file")
    vp.add_argument("--project", default=None, help="Target project root directory")

    svp = subparsers.add_parser("serve", help="Serve a local Archify portal directory over loopback HTTP")
    svp.add_argument("directory", nargs="?", default="docs/architecture", help="Directory to serve (default: docs/architecture)")
    svp.add_argument("--host", default="127.0.0.1", help="Loopback host to bind (127.0.0.1 or localhost)")
    svp.add_argument("--port", type=int, default=0, help="TCP port (0 selects a free port)")
    svp.add_argument("--open", action="store_true", help="Open index.html in default browser")


def _build_cli_parser() -> argparse.ArgumentParser:
    """Build TDQ Archify CLI parser with all supported subcommands."""
    parser = argparse.ArgumentParser(
        description="TDQ Archify Adapter CLI — orchestrate diagram generation, model bridge, and bundle lifecycle."
    )
    subparsers = parser.add_subparsers(dest="command", help="Sub-commands")
    subparsers.add_parser("check", help="Check Node.js and Archify environment")
    _add_render_and_bridge_parsers(subparsers)
    _add_sync_and_lifecycle_parsers(subparsers)
    return parser


def main() -> int:
    """CLI entrypoint for tdq_archify."""
    parser = _build_cli_parser()
    args = parser.parse_args()
    handlers = {
        "check": handle_check,
        "render": handle_render,
        "open": handle_open,
        "bridge": handle_bridge,
        "test-bridge": handle_test_bridge,
        "sync-master": handle_sync_master,
        "status": handle_status,
        "verify": handle_verify,
        "serve": handle_serve,
    }
    handler = handlers.get(args.command)
    if handler is not None:
        return handler(args)
    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
