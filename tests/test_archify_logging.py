"""Parity tests for ISO-8601 stderr logging and TDQ_LOG=0 silence across Archify & Setup."""
from __future__ import annotations

import argparse
import datetime
import http.client
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import archify_delivery
import archify_portal
import archify_registry
import tdq_archify
import tdq_setup

SECRET = "archify-logging-secret-fixture-7c91e"
ISO_LINE_RE = re.compile(r"^\[(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[^\]]*)\]\s+\S")


@pytest.fixture(params=[None, "1", "0"], ids=["default-unset", "explicit-on", "muted-zero"])
def tdq_log_mode(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> bool:
    """Toggle TDQ_LOG across unset (default on), '1' (on), and '0' (muted)."""
    val = request.param
    if val is None:
        monkeypatch.delenv("TDQ_LOG", raising=False)
        return True
    monkeypatch.setenv("TDQ_LOG", val)
    return val != "0"


def _assert_logged_stderr(stderr: str, enabled: bool, required_tokens: tuple[str, ...]) -> None:
    """Assert ISO-8601 stderr formatting when enabled, 100% silence when disabled, no leaks."""
    assert SECRET not in stderr
    assert "Traceback (most recent call last):" not in stderr
    if not enabled:
        assert stderr == "", f"Expected completely silent stderr under TDQ_LOG=0, got: {stderr!r}"
        return
    lines = [line for line in stderr.splitlines() if line.strip()]
    assert lines, "Expected at least one ISO-8601 stderr log line, got empty stderr"
    for line in lines:
        match = ISO_LINE_RE.match(line)
        assert match is not None, f"Log line missing ISO-8601 timestamp prefix: {line!r}"
        datetime.datetime.fromisoformat(match.group(1))
    for token in required_tokens:
        assert token in stderr, f"Missing expected log token {token!r} in stderr:\n{stderr}"


def _make_logic_node(
    node_id: str,
    *,
    depth: int = 1,
    slice_id: str | None = None,
    steps: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build a schema-valid Logic Node fixture containing a secret summary string."""
    node: dict[str, Any] = {
        "node_id": node_id,
        "title": f"Node {node_id}",
        "depth": depth,
        "node_kind": "flow_root" if depth == 1 else "decision_branch",
        "hydration_tier": "eager_l1_l2" if depth <= 2 else "lazy_l3_plus",
        "evidence_kind": "working-tree",
        "fingerprint": {
            "symbol_ref": "src/app.py::run_flow",
            "ast_symbol_sha256": None,
            "span_binding": {"path": "src/app.py", "line": 1, "end_line": 3},
            "render_slice_sha256": f"slice-hash-{node_id}" if slice_id else None,
            "cache_status": "clean",
        },
        "natural_explanation": {
            "summary": f"Executes {node_id} with {SECRET}.",
            "what_goes_where": "Validates input and returns structured output.",
            "why_it_exists": "Keeps flow boundaries modular.",
            "edge_cases": ["Missing input fails closed"],
        },
        "io_contract": {
            "inputs": ["payload"],
            "outputs": ["result"],
            "side_effects": ["Emits ISO stderr diagnostics"],
        },
        "sources": [{"path": "src/app.py", "line": 1, "end_line": 3}],
        "reused_by": ["flow-root"],
    }
    if slice_id and steps is not None:
        node["sub_flow"] = {"slice_id": slice_id, "max_cols": 4, "steps": steps, "edges": []}
    return node


def _make_registry_project(
    base_dir: Path, reg_rel: str = "docs/tdq/models/registry"
) -> tuple[Path, Path]:
    """Create a temp project and Logic Node registry on disk."""
    src_dir = base_dir / "src"
    src_dir.mkdir(parents=True, exist_ok=True)
    (src_dir / "app.py").write_text(
        f'def run_flow(payload):\n    token = "{SECRET}"\n    return payload or token\n',
        encoding="utf-8",
    )
    reg_dir = base_dir / reg_rel
    (reg_dir / "nodes").mkdir(parents=True, exist_ok=True)
    node = _make_logic_node("flow-root")
    (reg_dir / "nodes" / "flow-root.json").write_text(
        json.dumps(node, indent=2), encoding="utf-8"
    )
    return base_dir, reg_dir


def _make_portal_bundle() -> tuple[dict[str, Any], dict[str, str], dict[str, dict[str, Any]]]:
    """Create minimal portal index, SVG slices, and Logic Nodes with embedded secret data."""
    node = _make_logic_node(
        "flow-root",
        slice_id="slice-root",
        steps=[{"step_id": "s1", "label": "Run", "col": 0, "lane": "main", "target_node_id": None}],
    )
    nodes = {"flow-root": node}
    slices = {
        "slice-root": (
            f'<svg viewBox="0 0 320 120" data-slice-id="slice-root"><!-- {SECRET} -->'
            '<g id="node-flow-root" data-node-id="flow-root"><rect x="10" y="10" '
            'width="100" height="40"/></g></svg>'
        )
    }
    index = {
        "schema_version": "1.0",
        "max_depth": 4,
        "root_flows": ["flow-root"],
        "node_count": 1,
        "cycles_detected": [],
        "nodes": [
            {
                "node_id": "flow-root",
                "title": node["title"],
                "depth": 1,
                "node_kind": "flow_root",
                "hydration_tier": "eager_l1_l2",
                "evidence_kind": "working-tree",
                "symbol_ref": "src/app.py::run_flow",
                "span_binding": {"path": "src/app.py", "line": 1, "end_line": 3},
                "sub_flow_slice_id": "slice-root",
                "reused_by": ["flow-root"],
                "cache_status": "clean",
                "file_path": "nodes/flow-root.json",
            }
        ],
    }
    return index, slices, nodes


def _write_drilldown_candidate(cand_path: Path) -> Path:
    """Write a standalone <= 4 level drilldown candidate JSON to cand_path."""
    _, slices, nodes = _make_portal_bundle()
    payload = {
        "title": "Drilldown Logging Fixture",
        "evidence_kind": "planned",
        "root_flows": ["flow-root"],
        "nodes": nodes,
        "slices": slices,
    }
    cand_path.parent.mkdir(parents=True, exist_ok=True)
    cand_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return cand_path


def _make_sync_master_project(base_dir: Path) -> tuple[Path, Path, Path]:
    """Create a temp project with master.model.json, overview view, and Logic Node registry."""
    project_root, _ = _make_registry_project(base_dir)
    models_dir = project_root / "docs" / "tdq" / "models"
    models_dir.mkdir(parents=True, exist_ok=True)
    overview_payload = {
        "schema_version": 1,
        "diagram_type": "architecture",
        "meta": {"id": "overview", "title": "Overview"},
        "components": [{"id": "svc", "label": "Service", "type": "backend"}],
        "connections": [],
    }
    (models_dir / "overview.json").write_text(json.dumps(overview_payload), encoding="utf-8")
    model_payload = {
        "schema_version": 1,
        "title": "Master Portal Fixture",
        "evidence_kind": "working-tree",
        "source_paths": ["src/app.py"],
        "coverage": {"modules": [{"id": "app", "status": "selected"}], "unknown": [], "excluded": []},
        "views": [{"id": "overview", "type": "architecture", "candidate": "overview.json", "summary": "Overview"}],
        "master": {
            "overview": "overview",
            "flows": [],
            "registry": {"path": "docs/tdq/models/registry", "root_flows": ["flow-root"], "max_depth": 4},
        },
    }
    model_file = models_dir / "master.model.json"
    model_file.write_text(json.dumps(model_payload), encoding="utf-8")
    return project_root, model_file, project_root / "docs" / "architecture"


def _child_env(tdq_log: str | None) -> dict[str, str]:
    """Build an isolated subprocess environment without touching host state."""
    env = dict(os.environ)
    env["TDQ_KHONG_CHAM_MAY"] = "1"
    env["TDQ_KHOI_TAO_NEN"] = "0"
    env["ARCHIFY_UPDATE_CHECK_DISABLED"] = "1"
    env["TDQ_TEST_SECRET"] = SECRET
    env["TAVILY_API_KEY"] = SECRET
    if tdq_log is None:
        env.pop("TDQ_LOG", None)
    else:
        env["TDQ_LOG"] = tdq_log
    return env


def _run_child_py(code: str, cwd: Path, tdq_log: str | None) -> subprocess.CompletedProcess[str]:
    """Run isolated Python -c inside cwd with explicit TDQ_LOG setting."""
    proc = subprocess.run(
        [sys.executable, "-X", "utf8", "-c", code],
        cwd=str(cwd),
        env=_child_env(tdq_log),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
        check=False,
    )
    assert proc.returncode == 0, f"Child failed ({proc.returncode}): {proc.stdout}\n{proc.stderr}"
    return proc


def test_archify_registry_in_process_logging(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], tdq_log_mode: bool
) -> None:
    """Verify archify_registry logs ISO lines on stderr and goes silent on TDQ_LOG=0."""
    project_root, reg_dir = _make_registry_project(tmp_path)
    info = archify_registry.check_tree_sitter_support()
    synced = archify_registry.sync_registry_index(reg_dir, project_root)
    dirty = archify_registry.compute_dirty_set(reg_dir, project_root)
    assert isinstance(info, dict) and synced["node_count"] == 1 and dirty["clean_nodes"] == ["flow-root"]
    err = capsys.readouterr().err
    _assert_logged_stderr(
        err,
        tdq_log_mode,
        (
            "archify_registry: checked tree-sitter support:",
            "archify_registry: synced registry index:",
            "archify_registry: dirty set computed:",
        ),
    )


def test_archify_portal_in_process_logging(
    capsys: pytest.CaptureFixture[str], tdq_log_mode: bool
) -> None:
    """Verify archify_portal bundle, shell, and standalone builders honor TDQ_LOG."""
    index, slices, nodes = _make_portal_bundle()
    bundle_js = archify_portal.build_registry_bundle_js(index, slices, nodes)
    lazy_html = archify_portal.build_portal_shell(index, slices, nodes, mode="lazy")
    standalone_html = archify_portal.render_drilldown_standalone({"nodes": nodes}, slices)
    assert "window.__TDQ_ARCHIFY_REGISTRY__" in bundle_js
    assert "<html" in lazy_html and "<html" in standalone_html
    err = capsys.readouterr().err
    _assert_logged_stderr(
        err,
        tdq_log_mode,
        (
            "archify_portal: built registry-bundle.js:",
            "archify_portal: built portal shell:",
            "archify_portal: rendered standalone drilldown:",
        ),
    )


def test_archify_delivery_in_process_logging(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tdq_log_mode: bool,
) -> None:
    """Verify archify_delivery.serve_directory and _log honor TDQ_LOG and clean shutdown."""
    serve_dir = tmp_path / "portal"
    serve_dir.mkdir(parents=True)
    (serve_dir / "index.html").write_text(f"<html><body>{SECRET}</body></html>", encoding="utf-8")
    monkeypatch.setenv("TDQ_TEST_SECRET", SECRET)

    server, url = archify_delivery.serve_directory(serve_dir, host="127.0.0.1", port=0, open_browser=False)
    try:
        host_port = url.removeprefix("http://").rstrip("/")
        conn = http.client.HTTPConnection(host_port, timeout=5)
        try:
            conn.request("GET", "/index.html")
            resp = conn.getresponse()
            assert resp.status == 200
            resp.read()
        finally:
            conn.close()
        archify_delivery._log("delivery diagnostic check")
    finally:
        server.shutdown()
        server.server_close()

    err = capsys.readouterr().err
    _assert_logged_stderr(
        err,
        tdq_log_mode,
        (
            "archify_delivery: Serving ",
            "archify_delivery: HTTP ",
            "archify_delivery: delivery diagnostic check",
        ),
    )


def test_tdq_archify_render_and_serve_in_process_logging(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tdq_log_mode: bool,
) -> None:
    """Verify tdq_archify handle_render (drilldown), handle_serve, and _log honor TDQ_LOG."""
    cand_path = _write_drilldown_candidate(tmp_path / "cand.json")
    out_html = tmp_path / "out" / "drilldown.html"
    render_args = argparse.Namespace(
        type="drilldown",
        candidate=str(cand_path),
        out=str(out_html),
        quality="standard",
        repo_root=str(tmp_path),
        document=None,
        request=None,
        lane=None,
        evidence_kind="planned",
    )
    rc_render = tdq_archify.handle_render(render_args)
    assert rc_render == 0 and out_html.is_file()

    serve_dir = tmp_path / "out"
    (serve_dir / "index.html").write_text("<html><body>ok</body></html>", encoding="utf-8")
    monkeypatch.setattr(tdq_archify, "_wait_for_serve_exit", lambda: None)
    serve_args = argparse.Namespace(directory=str(serve_dir), host="127.0.0.1", port=0, open=False)
    rc_serve = tdq_archify.handle_serve(serve_args)
    assert rc_serve == 0

    tdq_archify._log("adapter probe")
    captured = capsys.readouterr()
    _assert_logged_stderr(
        captured.err,
        tdq_log_mode,
        (
            "tdq_archify: rendered standalone drilldown",
            "tdq_archify: serving directory=",
            "tdq_archify: adapter probe",
        ),
    )


def test_tdq_archify_sync_master_in_process_logging(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tdq_log_mode: bool,
) -> None:
    """Verify tdq_archify.sync_master logs registry pre-sync and publish under TDQ_LOG."""
    project_root, model_file, out_dir = _make_sync_master_project(tmp_path)

    def _fake_finalize(**kwargs: Any) -> archify_delivery.FinalizeResult:
        out_path = Path(kwargs["output_path"])
        out_path.write_text('<html><svg viewBox="0 0 100 40"></svg></html>', encoding="utf-8")
        return archify_delivery.FinalizeResult(
            status=True, receipt={"ok": True, "status": "pass", "engine": "archify"}
        )

    monkeypatch.setattr(tdq_archify, "run_finalize", _fake_finalize)
    ok = tdq_archify.sync_master(model=model_file, project=project_root, out=out_dir)
    assert ok is True
    err = capsys.readouterr().err
    _assert_logged_stderr(
        err,
        tdq_log_mode,
        (
            "tdq_archify: registry pre-sync:",
            "tdq_archify: sync_master published index=",
        ),
    )


def test_tdq_setup_in_process_logging(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tdq_log_mode: bool
) -> None:
    """Verify tdq_setup tree-sitter diagnostics log ISO lines and mute cleanly on TDQ_LOG=0."""
    monkeypatch.setenv("TDQ_KHONG_CHAM_MAY", "1")
    monkeypatch.setenv("TDQ_TEST_SECRET", SECRET)

    ok_check, _ = tdq_setup.kiem_tra_tree_sitter()
    ok_ensure, _ = tdq_setup.ensure_tree_sitter_installed(allow_network=False)
    assert isinstance(ok_check, bool) and isinstance(ok_ensure, bool)

    monkeypatch.setattr(
        tdq_setup,
        "_probe_tree_sitter_support",
        lambda: {"available": False, "missing": ["tree-sitter-rust"], "installed": [], "languages": [], "version": None},
    )
    ok_miss, detail_miss = tdq_setup.ensure_tree_sitter_installed(allow_network=False)
    assert ok_miss is False and "tree-sitter-rust" in detail_miss

    err = capsys.readouterr().err
    _assert_logged_stderr(
        err,
        tdq_log_mode,
        (
            "kiem_tra_tree_sitter",
            "ensure_tree_sitter_installed",
        ),
    )


@pytest.mark.parametrize("tdq_log", [None, "1", "0"], ids=["default-unset", "explicit-on", "muted-zero"])
def test_archify_registry_subprocess_logging(tmp_path: Path, tdq_log: str | None) -> None:
    """Verify archify_registry logging in an isolated child Python process."""
    project_root, reg_dir = _make_registry_project(tmp_path)
    code = (
        "import sys; from pathlib import Path; "
        f"sys.path.insert(0, {str(SCRIPTS_DIR)!r}); "
        "import archify_registry; "
        "archify_registry.check_tree_sitter_support(); "
        f"archify_registry.sync_registry_index(Path({str(reg_dir)!r}), Path({str(project_root)!r})); "
        f"archify_registry.compute_dirty_set(Path({str(reg_dir)!r}), Path({str(project_root)!r}))"
    )
    proc = _run_child_py(code, tmp_path, tdq_log)
    _assert_logged_stderr(
        proc.stderr,
        tdq_log != "0",
        (
            "archify_registry: checked tree-sitter support:",
            "archify_registry: synced registry index:",
            "archify_registry: dirty set computed:",
        ),
    )


@pytest.mark.parametrize("tdq_log", [None, "1", "0"], ids=["default-unset", "explicit-on", "muted-zero"])
def test_archify_portal_subprocess_logging(tmp_path: Path, tdq_log: str | None) -> None:
    """Verify archify_portal logging in an isolated child Python process."""
    index, slices, nodes = _make_portal_bundle()
    fixture_file = tmp_path / "portal_fixture.json"
    fixture_file.write_text(json.dumps({"index": index, "slices": slices, "nodes": nodes}), encoding="utf-8")
    code = (
        "import json, sys; from pathlib import Path; "
        f"sys.path.insert(0, {str(SCRIPTS_DIR)!r}); "
        "import archify_portal; "
        f"data = json.loads(Path({str(fixture_file)!r}).read_text(encoding='utf-8')); "
        "archify_portal.build_registry_bundle_js(data['index'], data['slices'], data['nodes']); "
        "archify_portal.build_portal_shell(data['index'], data['slices'], data['nodes'], mode='lazy'); "
        "archify_portal.render_drilldown_standalone({'nodes': data['nodes']}, data['slices'])"
    )
    proc = _run_child_py(code, tmp_path, tdq_log)
    _assert_logged_stderr(
        proc.stderr,
        tdq_log != "0",
        (
            "archify_portal: built registry-bundle.js:",
            "archify_portal: built portal shell:",
            "archify_portal: rendered standalone drilldown:",
        ),
    )


@pytest.mark.parametrize("tdq_log", [None, "1", "0"], ids=["default-unset", "explicit-on", "muted-zero"])
def test_archify_delivery_subprocess_logging(tmp_path: Path, tdq_log: str | None) -> None:
    """Verify archify_delivery.serve_directory logs cleanly and shuts down in child Python."""
    serve_dir = tmp_path / "portal"
    serve_dir.mkdir(parents=True)
    (serve_dir / "index.html").write_text(f"<html><body>{SECRET}</body></html>", encoding="utf-8")
    code = (
        "import http.client, sys; from pathlib import Path; "
        f"sys.path.insert(0, {str(SCRIPTS_DIR)!r}); "
        "import archify_delivery; "
        f"srv, url = archify_delivery.serve_directory(Path({str(serve_dir)!r}), host='127.0.0.1', port=0, open_browser=False)\n"
        "try:\n"
        "    hp = url.removeprefix('http://').rstrip('/')\n"
        "    conn = http.client.HTTPConnection(hp, timeout=5)\n"
        "    try:\n"
        "        conn.request('GET', '/index.html')\n"
        "        r = conn.getresponse()\n"
        "        assert r.status == 200\n"
        "        r.read()\n"
        "    finally:\n"
        "        conn.close()\n"
        "    archify_delivery._log('subprocess delivery ok')\n"
        "finally:\n"
        "    srv.shutdown()\n"
        "    srv.server_close()\n"
    )
    proc = _run_child_py(code, tmp_path, tdq_log)
    _assert_logged_stderr(
        proc.stderr,
        tdq_log != "0",
        (
            "archify_delivery: Serving ",
            "archify_delivery: HTTP ",
            "archify_delivery: subprocess delivery ok",
        ),
    )


@pytest.mark.parametrize("tdq_log", [None, "1", "0"], ids=["default-unset", "explicit-on", "muted-zero"])
def test_tdq_archify_subprocess_logging(tmp_path: Path, tdq_log: str | None) -> None:
    """Verify tdq_archify CLI render --type drilldown logging and clean stdout JSON."""
    cand_path = _write_drilldown_candidate(tmp_path / "cand.json")
    out_html = tmp_path / "out" / "drilldown.html"
    proc = subprocess.run(
        [
            sys.executable,
            "-X",
            "utf8",
            str(SCRIPTS_DIR / "tdq_archify.py"),
            "render",
            "--type",
            "drilldown",
            "--candidate",
            str(cand_path),
            "--out",
            str(out_html),
            "--repo-root",
            str(tmp_path),
        ],
        cwd=str(tmp_path),
        env=_child_env(tdq_log),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
        check=False,
    )
    assert proc.returncode == 0, f"CLI failed: {proc.stdout}\n{proc.stderr}"
    receipt = json.loads(proc.stdout)
    assert receipt.get("ok") is True and out_html.is_file()
    _assert_logged_stderr(
        proc.stderr,
        tdq_log != "0",
        (
            "archify_portal: rendered standalone drilldown:",
            "tdq_archify: rendered standalone drilldown",
        ),
    )


@pytest.mark.parametrize("tdq_log", [None, "1", "0"], ids=["default-unset", "explicit-on", "muted-zero"])
def test_tdq_setup_subprocess_logging(tmp_path: Path, tdq_log: str | None) -> None:
    """Verify tdq_setup tree-sitter checks honor TDQ_LOG in an isolated child process."""
    code = (
        "import sys; "
        f"sys.path.insert(0, {str(SCRIPTS_DIR)!r}); "
        "import tdq_setup; "
        "tdq_setup.kiem_tra_tree_sitter(); "
        "tdq_setup.ensure_tree_sitter_installed(allow_network=False)"
    )
    proc = _run_child_py(code, tmp_path, tdq_log)
    _assert_logged_stderr(
        proc.stderr,
        tdq_log != "0",
        (
            "kiem_tra_tree_sitter",
            "ensure_tree_sitter_installed",
        ),
    )
