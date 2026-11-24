"""Integration and pipeline tests for Archify CLI orchestration (T3.1).

Covers:
- render CLI: with/without document, staging & rollback (last-good preservation on missing doc, engine failure, bind failure)
- fail injection tests: transactional rollback with pre-existing bundle and fresh failure
- bridge CLI: candidate generation + coverage sidecar (.coverage.json) and error handling on empty nodes / invalid scalar
- sync-master CLI:
  * Master model validation (empty, invalid envelope, views)
  * Candidate confinement relative to model parent
  * Git revision and dirty verification for committed evidence (including raw Unicode paths and directory prefixes)
  * Model lacking explicit source_paths derives stable sources without staging self-stale
  * Multi-view native rendering via delivery
  * Safe index.html generation (escaped labels, relative links, revision, coverage)
  * Manifest final-path rebasing (no temp paths leaked, honest receipts)
  * Preserving previous good bundle on failure (no loss/corruption)
  * Child file binding and tampering detection
- status CLI: freshness inspection, child tampering detection
- verify CLI: document binding and manifest freshness verification
- Local Archify real engine smoke: real bound explainer render then verify immediately current
"""
from __future__ import annotations

import html
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

# Ensure scripts dir of current worktree is on sys.path
WORKTREE_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = WORKTREE_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import archify_artifacts
import archify_delivery
import tdq_archify


def _init_git_repo(repo_dir: Path) -> str:
    """Initialize a git repo with a commit and return HEAD revision."""
    subprocess.run(["git", "init"], cwd=str(repo_dir), capture_output=True, timeout=15, check=True)
    subprocess.run(["git", "config", "user.name", "Tester"], cwd=str(repo_dir), capture_output=True, timeout=15, check=True)
    subprocess.run(["git", "config", "user.email", "tester@example.com"], cwd=str(repo_dir), capture_output=True, timeout=15, check=True)
    src_file = repo_dir / "src" / "main.py"
    src_file.parent.mkdir(parents=True, exist_ok=True)
    src_file.write_text("print('hello')\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=str(repo_dir), capture_output=True, timeout=15, check=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=str(repo_dir), capture_output=True, timeout=15, check=True)
    proc = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(repo_dir), capture_output=True, text=True, encoding="utf-8", timeout=15, check=True)
    return proc.stdout.strip()


class TestRenderCliBinding(unittest.TestCase):
    """Test render CLI sub-command with and without document binding and staging rollback."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.temp_dir, True)
        self.project_dir = Path(self.temp_dir)
        self.candidate = self.project_dir / "cand.json"
        self.candidate.write_text(json.dumps({"schema_version": 1, "components": []}), encoding="utf-8")
        self.out_html = self.project_dir / "output.html"

    def test_render_without_document_returns_unbound(self):
        """Render without --document reports artifact_unbound and does not claim registered."""
        fake_receipt = {
            "ok": True,
            "status": "pass",
            "artifact": str(self.out_html),
            "gates": {"validate": "pass", "deliver": "pass", "check": "pass", "browser-check": "pass"},
        }
        fake_res = archify_delivery.FinalizeResult(status=True, receipt=fake_receipt)

        def mock_finalize(diagram_type, candidate_path, output_path, **kwargs):
            Path(output_path).write_text("<html>Staged</html>", encoding="utf-8")
            return fake_res

        with (
            mock.patch("tdq_archify.run_finalize", side_effect=mock_finalize),
            mock.patch.object(
                sys,
                "argv",
                [
                    "tdq_archify.py",
                    "render",
                    "--type", "architecture",
                    "--candidate", str(self.candidate),
                    "--out", str(self.out_html),
                ],
            ),
            mock.patch("sys.stdout") as mock_out,
        ):
            code = tdq_archify.main()
            self.assertEqual(code, 0)
            output = "".join(call.args[0] for call in mock_out.write.call_args_list)
            data = json.loads(output)
            self.assertIn("binding", data)
            self.assertEqual(data["binding"], "unbound")
            self.assertTrue(self.out_html.is_file())

    def test_render_with_document_creates_manifest_and_binds(self):
        """Render with --document creates manifest beside output and binds document."""
        doc = self.project_dir / "SPEC.md"
        doc.write_text("# Spec Title\n\nSome spec content.\n", encoding="utf-8")

        fake_receipt = {
            "ok": True,
            "status": "pass",
            "artifact": str(self.out_html),
            "gates": {"validate": "pass", "deliver": "pass", "check": "pass", "browser-check": "pass"},
        }
        fake_res = archify_delivery.FinalizeResult(status=True, receipt=fake_receipt)

        def mock_finalize(diagram_type, candidate_path, output_path, **kwargs):
            Path(output_path).write_text("<html>Preview Content</html>", encoding="utf-8")
            return fake_res

        with (
            mock.patch("tdq_archify.run_finalize", side_effect=mock_finalize),
            mock.patch.object(
                sys,
                "argv",
                [
                    "tdq_archify.py",
                    "render",
                    "--type", "architecture",
                    "--candidate", str(self.candidate),
                    "--out", str(self.out_html),
                    "--document", str(doc),
                    "--request", "req-123",
                    "--lane", "full",
                    "--repo-root", str(self.project_dir),
                ],
            ),
        ):
            code = tdq_archify.main()
            self.assertEqual(code, 0)

        manifest_path = self.out_html.with_suffix(".manifest.json")
        self.assertTrue(manifest_path.is_file(), f"Manifest expected at {manifest_path}")

        bound_doc_content = doc.read_text(encoding="utf-8")
        self.assertIn(archify_artifacts.BINDING_START, bound_doc_content)
        self.assertIn(archify_artifacts.BINDING_END, bound_doc_content)

        b_check = archify_artifacts.check_binding(doc, manifest_path)
        self.assertTrue(b_check.get("valid"))
        self.assertEqual(b_check.get("status"), "current")

    def test_render_staging_preserves_previous_artifact_on_missing_doc(self):
        """Missing --document fails before running finalize and preserves existing artifact."""
        self.out_html.write_text("<html>ORIGINAL_GOOD</html>", encoding="utf-8")
        missing_doc = self.project_dir / "nonexistent.md"

        with mock.patch.object(
            sys,
            "argv",
            [
                "tdq_archify.py",
                "render",
                "--type", "architecture",
                "--candidate", str(self.candidate),
                "--out", str(self.out_html),
                "--document", str(missing_doc),
            ],
        ):
            code = tdq_archify.main()
            self.assertNotEqual(code, 0)
            self.assertEqual(self.out_html.read_text(encoding="utf-8"), "<html>ORIGINAL_GOOD</html>")

    def test_render_staging_preserves_previous_artifact_on_engine_failure(self):
        """Engine failure during finalize preserves previous artifact without corruption."""
        self.out_html.write_text("<html>ORIGINAL_GOOD</html>", encoding="utf-8")
        doc = self.project_dir / "SPEC.md"
        doc.write_text("# Title\n", encoding="utf-8")

        failing_res = archify_delivery.FinalizeResult(status=False, receipt={"ok": False, "status": "fail"})
        with (
            mock.patch("tdq_archify.run_finalize", return_value=failing_res),
            mock.patch.object(
                sys,
                "argv",
                [
                    "tdq_archify.py",
                    "render",
                    "--type", "architecture",
                    "--candidate", str(self.candidate),
                    "--out", str(self.out_html),
                    "--document", str(doc),
                ],
            ),
        ):
            code = tdq_archify.main()
            self.assertNotEqual(code, 0)
            self.assertEqual(self.out_html.read_text(encoding="utf-8"), "<html>ORIGINAL_GOOD</html>")

    def test_render_rollback_on_bind_failure_with_existing_bundle(self):
        """Fail injection: if bind_document fails, restores previous HTML, manifest, and document bytes."""
        orig_html_bytes = b"<html>ORIGINAL_PREVIEW_V1</html>"
        orig_manifest_bytes = b'{"version": 1, "status": "old"}'
        orig_doc_bytes = b"# Spec Title\n\nOriginal document text before render.\n"

        self.out_html.write_bytes(orig_html_bytes)
        manifest_path = self.out_html.with_suffix(".manifest.json")
        manifest_path.write_bytes(orig_manifest_bytes)
        doc = self.project_dir / "SPEC.md"
        doc.write_bytes(orig_doc_bytes)

        fake_res = archify_delivery.FinalizeResult(
            status=True,
            receipt={"ok": True, "status": "pass", "artifact": str(self.out_html)},
        )

        def mock_finalize(diagram_type, candidate_path, output_path, **kwargs):
            Path(output_path).write_text("<html>NEW_PREVIEW_V2</html>", encoding="utf-8")
            return fake_res

        with (
            mock.patch("tdq_archify.run_finalize", side_effect=mock_finalize),
            mock.patch("tdq_archify.bind_document", side_effect=RuntimeError("Simulated bind failure")),
            mock.patch.object(
                sys,
                "argv",
                [
                    "tdq_archify.py",
                    "render",
                    "--type", "architecture",
                    "--candidate", str(self.candidate),
                    "--out", str(self.out_html),
                    "--document", str(doc),
                    "--repo-root", str(self.project_dir),
                ],
            ),
        ):
            code = tdq_archify.main()
            self.assertNotEqual(code, 0)

        self.assertEqual(self.out_html.read_bytes(), orig_html_bytes, "Previous HTML artifact must be restored")
        self.assertEqual(manifest_path.read_bytes(), orig_manifest_bytes, "Previous manifest must be restored")
        self.assertEqual(doc.read_bytes(), orig_doc_bytes, "Original document bytes must be restored")

    def test_render_rollback_on_fresh_failure_leaves_no_artifacts(self):
        """Fail injection: on fresh render failure, leaves no dangling HTML or manifest and restores doc."""
        orig_doc_bytes = b"# Fresh Spec\n\nFresh doc text.\n"
        doc = self.project_dir / "FRESH_SPEC.md"
        doc.write_bytes(orig_doc_bytes)

        manifest_path = self.out_html.with_suffix(".manifest.json")
        self.assertFalse(self.out_html.exists())
        self.assertFalse(manifest_path.exists())

        fake_res = archify_delivery.FinalizeResult(
            status=True,
            receipt={"ok": True, "status": "pass", "artifact": str(self.out_html)},
        )

        def mock_finalize(diagram_type, candidate_path, output_path, **kwargs):
            Path(output_path).write_text("<html>DANGLING_HTML</html>", encoding="utf-8")
            return fake_res

        with (
            mock.patch("tdq_archify.run_finalize", side_effect=mock_finalize),
            mock.patch("tdq_archify.bind_document", side_effect=RuntimeError("Simulated bind failure")),
            mock.patch.object(
                sys,
                "argv",
                [
                    "tdq_archify.py",
                    "render",
                    "--type", "architecture",
                    "--candidate", str(self.candidate),
                    "--out", str(self.out_html),
                    "--document", str(doc),
                    "--repo-root", str(self.project_dir),
                ],
            ),
        ):
            code = tdq_archify.main()
            self.assertNotEqual(code, 0)

        self.assertFalse(self.out_html.exists(), "Newly created HTML must be deleted on failure")
        self.assertFalse(manifest_path.exists(), "Newly created manifest must be deleted on failure")
        self.assertEqual(doc.read_bytes(), orig_doc_bytes, "Document bytes must be restored")



    def test_render_restore_failure_retains_backup(self):
        """If restoring from backup fails during rollback, backup file is NOT deleted and recovery is logged."""
        orig_html = b"<html>ORIGINAL_GOOD_V1</html>"
        self.out_html.write_bytes(orig_html)
        doc = self.project_dir / "SPEC.md"
        doc.write_text("# Title\n", encoding="utf-8")

        fake_res = archify_delivery.FinalizeResult(
            status=True,
            receipt={"ok": True, "status": "pass", "artifact": str(self.out_html)},
        )

        def mock_finalize(diagram_type, candidate_path, output_path, **kwargs):
            Path(output_path).write_text("<html>STAGED_FAIL</html>", encoding="utf-8")
            return fake_res

        real_replace = os.replace
        def failing_replace(src, dst):
            # Fail only when attempting to restore backup to out_html
            if ".bak." in str(src):
                raise OSError("Simulated filesystem lock during backup restoration")
            return real_replace(src, dst)

        with (
            mock.patch("tdq_archify.run_finalize", side_effect=mock_finalize),
            mock.patch("tdq_archify.bind_document", side_effect=RuntimeError("Bind failed")),
            mock.patch("os.replace", side_effect=failing_replace),
            mock.patch("sys.stderr") as mock_err,
            mock.patch.object(
                sys,
                "argv",
                [
                    "tdq_archify.py",
                    "render",
                    "--type", "architecture",
                    "--candidate", str(self.candidate),
                    "--out", str(self.out_html),
                    "--document", str(doc),
                    "--repo-root", str(self.project_dir),
                ],
            ),
        ):
            code = tdq_archify.main()
            self.assertNotEqual(code, 0)
            err_output = "".join(call.args[0] for call in mock_err.write.call_args_list)
            self.assertIn("Backup preserved at:", err_output)

        # Backup file must be preserved on disk
        backup_files = list(self.project_dir.glob(f".bak.{self.out_html.stem}.*.html"))
        self.assertTrue(len(backup_files) >= 1, "Backup file must be preserved on disk when restore fails")
        self.assertEqual(backup_files[0].read_bytes(), orig_html)

    def test_render_receipt_provenance_and_sidecar(self):
        """Successful render produces receipt sidecar, preserves provenance, and provides published path metadata."""
        doc = self.project_dir / "SPEC.md"
        doc.write_text("# Spec\n", encoding="utf-8")
        staged_temp = self.project_dir / "some_temp_staged.html"

        fake_res = archify_delivery.FinalizeResult(
            status=True,
            receipt={
                "ok": True,
                "status": "pass",
                "artifact": {"path": str(staged_temp), "sha256": "abc123"},
                "specification": {"sha256": "cand456"},
                "gates": {"validate": "pass", "deliver": "pass", "check": "pass", "browser-check": "pass"},
            },
        )

        def mock_finalize(diagram_type, candidate_path, output_path, **kwargs):
            Path(output_path).write_text("<html>Final content</html>", encoding="utf-8")
            return fake_res

        with (
            mock.patch("tdq_archify.run_finalize", side_effect=mock_finalize),
            mock.patch.object(
                sys,
                "argv",
                [
                    "tdq_archify.py",
                    "render",
                    "--type", "architecture",
                    "--candidate", str(self.candidate),
                    "--out", str(self.out_html),
                    "--document", str(doc),
                    "--repo-root", str(self.project_dir),
                ],
            ),
            mock.patch("sys.stdout") as mock_out,
        ):
            code = tdq_archify.main()
            self.assertEqual(code, 0)
            out_json = json.loads("".join(call.args[0] for call in mock_out.write.call_args_list))

        # Receipt sidecar on disk
        receipt_path = self.out_html.with_suffix(".receipt.json")
        self.assertTrue(receipt_path.is_file(), f"Receipt sidecar must exist at {receipt_path}")
        receipt_data = json.loads(receipt_path.read_text(encoding="utf-8"))
        # Honest engine receipt preserved (shows actual staging output)
        self.assertEqual(receipt_data["artifact"]["path"], str(staged_temp))

        # Response contains explicit published path metadata
        self.assertEqual(out_json["published_artifact"], str(self.out_html))
        self.assertEqual(out_json["receipt_path"], str(receipt_path))

        # Manifest contains honest receipt provenance
        manifest_path = self.out_html.with_suffix(".manifest.json")
        man_data = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(man_data["receipt"]["artifact"]["path"], str(staged_temp))
        self.assertEqual(man_data["artifact_path"], self.out_html.name)


class TestBridgeCliSidecar(unittest.TestCase):
    """Test bridge CLI creates candidate IR, coverage sidecar, and handles errors."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.temp_dir, True)
        self.graph_file = Path(self.temp_dir) / "graph.json"
        self.out_cand = Path(self.temp_dir) / "candidate.json"
        sample_graph = {
            "directed": True,
            "nodes": [
                {"id": "api", "label": "API Gateway", "type": "security"},
                {"id": "db", "label": "Database", "type": "database"},
                {"id": "worker", "label": "Worker", "type": "backend"},
            ],
            "links": [
                {"source": "api", "target": "db", "relation": "reads"},
            ],
        }
        self.graph_file.write_text(json.dumps(sample_graph), encoding="utf-8")

    def test_bridge_creates_candidate_and_coverage_sidecar(self):
        """CLI bridge writes candidate JSON and .coverage.json sidecar."""
        with mock.patch.object(
            sys,
            "argv",
            [
                "tdq_archify.py",
                "bridge",
                "--graph", str(self.graph_file),
                "--out", str(self.out_cand),
                "--max-nodes", "2",
            ],
        ):
            code = tdq_archify.main()
            self.assertEqual(code, 0)

        self.assertTrue(self.out_cand.is_file())
        cand_data = json.loads(self.out_cand.read_text(encoding="utf-8"))
        self.assertEqual(cand_data["schema_version"], 1)

        sidecar_path = self.out_cand.with_suffix(".coverage.json")
        self.assertTrue(sidecar_path.is_file(), f"Coverage sidecar expected at {sidecar_path}")
        coverage_data = json.loads(sidecar_path.read_text(encoding="utf-8"))
        self.assertIn("total", coverage_data)
        self.assertIn("selected", coverage_data)
        self.assertIn("excluded", coverage_data)
        self.assertIn("inventory", coverage_data)
        self.assertEqual(coverage_data["total"], 3)

    def test_bridge_cli_empty_nodes_fails_without_traceback(self):
        """Bridge with empty nodes exits non-zero without unhandled traceback."""
        empty_graph = Path(self.temp_dir) / "empty.json"
        empty_graph.write_text(json.dumps({"nodes": [], "links": []}), encoding="utf-8")
        out_cand = Path(self.temp_dir) / "out_empty.json"

        with mock.patch.object(
            sys,
            "argv",
            ["tdq_archify.py", "bridge", "--graph", str(empty_graph), "--out", str(out_cand)],
        ):
            code = tdq_archify.main()
            self.assertNotEqual(code, 0)
            self.assertFalse(out_cand.exists())

    def test_bridge_cli_invalid_scalar_fails_without_traceback(self):
        """Bridge with invalid JSON scalar exits non-zero without unhandled traceback."""
        scalar_graph = Path(self.temp_dir) / "scalar.json"
        scalar_graph.write_text(json.dumps("invalid scalar string"), encoding="utf-8")
        out_cand = Path(self.temp_dir) / "out_scalar.json"

        with mock.patch.object(
            sys,
            "argv",
            ["tdq_archify.py", "bridge", "--graph", str(scalar_graph), "--out", str(out_cand)],
        ):
            code = tdq_archify.main()
            self.assertNotEqual(code, 0)
            self.assertFalse(out_cand.exists())


class TestSyncMasterPipeline(unittest.TestCase):
    """Test sync-master CLI pipeline with model validation, views, index HTML, and publish."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.temp_dir, True)
        self.repo_dir = Path(self.temp_dir)
        self.rev = _init_git_repo(self.repo_dir)

        self.models_dir = self.repo_dir / "models"
        self.models_dir.mkdir(parents=True, exist_ok=True)

        self.cand1 = self.models_dir / "overview.json"
        self.cand1.write_text(json.dumps({"schema_version": 1, "diagram_type": "architecture", "components": []}), encoding="utf-8")

        self.cand2 = self.models_dir / "flow.json"
        self.cand2.write_text(json.dumps({"schema_version": 1, "diagram_type": "workflow", "steps": []}), encoding="utf-8")

        self.model_path = self.models_dir / "master.model.json"
        self.model_data = {
            "schema_version": 1,
            "title": "Master Architecture <Test & Escape>",
            "evidence_kind": "committed",
            "revision": self.rev,
            "repository": {
                "url": "https://example.invalid/repo.git",
                "revision": self.rev,
                "link_mode": "local-only",
            },
            "source_paths": ["src/main.py"],
            "coverage": {
                "modules": [{"id": "main", "status": "verified"}],
                "unknown": [],
                "excluded": [],
            },
            "views": [
                {"id": "overview", "type": "architecture", "candidate": "overview.json", "summary": "Overview View <Escaped>"},
                {"id": "flow", "type": "workflow", "candidate": "flow.json", "summary": "Workflow View"},
            ],
        }
        self.model_path.write_text(json.dumps(self.model_data), encoding="utf-8")

    def _mock_run_finalize_builder(self):
        """Helper to create a run_finalize mock that writes HTML output."""
        def fake_run_finalize(diagram_type, candidate_path, output_path, **kwargs):
            out_p = Path(output_path)
            out_p.parent.mkdir(parents=True, exist_ok=True)
            if diagram_type == "explainer":
                cand = json.loads(Path(candidate_path).read_text(encoding="utf-8"))
                links = []
                for panel in cand.get("panels", []):
                    for block in panel.get("blocks", []):
                        for item in block.get("items", []):
                            diag = (item.get("target") or {}).get("diagram", "")
                            links.append(f'<a data-diagram-link="{diag}">{item.get("text", "")}</a>')
                out_p.write_text(
                    f"<html>{''.join(links)}<dialog id=\"diagram-dialog\"></dialog></html>",
                    encoding="utf-8",
                )
            else:
                out_p.write_text(f"<html>{diagram_type} content</html>", encoding="utf-8")
            return archify_delivery.FinalizeResult(
                status=True,
                receipt={
                    "ok": True,
                    "status": "pass",
                    "artifact": str(out_p),
                    "gates": {"validate": "pass", "deliver": "pass", "check": "pass", "browser-check": "pass"},
                },
            )
        return fake_run_finalize

    def test_master_flow_evidence_checked_before_render(self):
        self.model_data["evidence_kind"] = "working-tree"
        source = {"path": "src/main.py", "line": 1}
        self.model_data["master"] = {"overview": "overview", "flows": [{
            "id": "read_flow", "text": "Read", "target": {"diagram": "flow"},
            "steps": [{"id": "read_step", "text": "Read source", "sources": [source]}],
        }]}
        out_dir = self.repo_dir / "docs" / "architecture"
        out_dir.mkdir(parents=True)
        last_good = out_dir / "index.html"
        last_good.write_text("LAST_GOOD", encoding="utf-8")
        for path, line in (("src/missing.py", 1), ("src/main.py", 2), ("../outside.py", 1)):
            with self.subTest(path=path, line=line):
                source.update(path=path, line=line)
                self.model_path.write_text(json.dumps(self.model_data), encoding="utf-8")
                with mock.patch("tdq_archify.run_finalize", side_effect=self._mock_run_finalize_builder()) as render:
                    self.assertFalse(tdq_archify.sync_master(model=self.model_path, project=self.repo_dir))
                    render.assert_not_called()
                self.assertEqual(last_good.read_text(encoding="utf-8"), "LAST_GOOD")
        source.update(path="src/main.py", line=1)
        self.model_path.write_text(json.dumps(self.model_data), encoding="utf-8")
        with mock.patch("tdq_archify.run_finalize", side_effect=self._mock_run_finalize_builder()) as render:
            self.assertTrue(tdq_archify.sync_master(model=self.model_path, project=self.repo_dir))
            self.assertEqual(render.call_count, 3)

    def test_master_source_resolved_path_cannot_escape_project(self):
        model = {"master": {"flows": [{"steps": [{"sources": [
            {"path": "src/main.py", "line": 1},
        ]}]}]}}
        outside = self.repo_dir.parent / "outside.py"
        # Emulate a symlink/junction resolution without requiring Windows symlink privileges.
        with mock.patch.object(Path, "resolve", side_effect=[self.repo_dir, outside]):
            self.assertFalse(tdq_archify._verify_master_sources(model, self.repo_dir))

    def test_master_source_end_line_must_exist(self):
        model = {"master": {"flows": [{"steps": [{"sources": [
            {"path": "src/main.py", "line": 1, "end_line": 2},
        ]}]}]}}
        self.assertFalse(tdq_archify._verify_master_sources(model, self.repo_dir))

    def test_master_dangling_target_preserves_last_good(self):
        self.model_data["evidence_kind"] = "working-tree"
        self.model_data["master"] = {"overview": "overview", "flows": [{
            "id": "read_flow", "text": "Read", "target": {"diagram": "missing"},
            "steps": [{"id": "read_step", "text": "Read", "detail": "chưa xác minh"}],
        }]}
        self.model_path.write_text(json.dumps(self.model_data), encoding="utf-8")
        with mock.patch("tdq_archify.run_finalize", side_effect=self._mock_run_finalize_builder()) as render:
            self.assertFalse(tdq_archify.sync_master(model=self.model_path, project=self.repo_dir))
            render.assert_not_called()

    def test_master_card_opens_detail_in_same_html(self):
        self.model_data["evidence_kind"] = "working-tree"
        self.model_data["master"] = {"overview": "overview", "flows": [{
            "id": "read_flow", "text": "Read flow", "target": {"diagram": "flow"},
            "steps": [{"id": "read_step", "text": "Read source",
                       "sources": [{"path": "src/main.py", "line": 1}]}],
        }]}
        self.model_path.write_text(json.dumps(self.model_data), encoding="utf-8")
        with mock.patch("tdq_archify.run_finalize", side_effect=self._mock_run_finalize_builder()) as render:
            self.assertTrue(tdq_archify.sync_master(model=self.model_path, project=self.repo_dir))
        index = (self.repo_dir / "docs" / "architecture" / "index.html").read_text(encoding="utf-8")
        self.assertIn("Read flow", index)
        self.assertIn("data-diagram-link=\"flow\"", index)
        self.assertIn("diagram-dialog", index)
        self.assertEqual(render.call_count, 3)

    def test_sync_master_empty_or_invalid_model_fails(self):
        """Empty or invalid model file must fail and not publish."""
        empty_model = self.models_dir / "empty.json"
        empty_model.write_text("", encoding="utf-8")
        out_dir = self.repo_dir / "docs" / "architecture"

        with mock.patch.object(
            sys,
            "argv",
            ["tdq_archify.py", "sync-master", "--model", str(empty_model), "--project", str(self.repo_dir)],
        ):
            code = tdq_archify.main()
            self.assertNotEqual(code, 0)
            self.assertFalse(out_dir.exists())

    def test_sync_master_candidate_confinement_relative_to_model_parent(self):
        """Candidate path escaping model parent directory must fail."""
        bad_model = self.models_dir / "bad_confinement.model.json"
        bad_data = dict(self.model_data)
        bad_data["views"] = [
            {"id": "escaped", "type": "architecture", "candidate": "../outside.json", "summary": "Escaped"}
        ]
        bad_model.write_text(json.dumps(bad_data), encoding="utf-8")

        with mock.patch.object(
            sys,
            "argv",
            ["tdq_archify.py", "sync-master", "--model", str(bad_model), "--project", str(self.repo_dir)],
        ):
            code = tdq_archify.main()
            self.assertNotEqual(code, 0)

    def test_sync_master_committed_fails_when_git_dirty(self):
        """When evidence_kind is committed, dirty working tree on sources must fail."""
        (self.repo_dir / "src" / "main.py").write_text("print('dirty')\n", encoding="utf-8")

        with mock.patch.object(
            sys,
            "argv",
            ["tdq_archify.py", "sync-master", "--model", str(self.model_path), "--project", str(self.repo_dir)],
        ):
            code = tdq_archify.main()
            self.assertNotEqual(code, 0)

    def test_sync_master_committed_fails_when_repo_revision_mismatches(self):
        """When evidence_kind is committed, mismatch between revision and repository.revision must fail."""
        bad_model = self.models_dir / "mismatch_rev.model.json"
        bad_data = dict(self.model_data)
        bad_data["repository"] = dict(self.model_data["repository"])
        bad_data["repository"]["revision"] = "0000000000000000000000000000000000000000"
        bad_model.write_text(json.dumps(bad_data), encoding="utf-8")

        with mock.patch.object(
            sys,
            "argv",
            ["tdq_archify.py", "sync-master", "--model", str(bad_model), "--project", str(self.repo_dir)],
        ):
            code = tdq_archify.main()
            self.assertNotEqual(code, 0)

    def test_sync_master_unicode_source_path_and_source_dir_dirty(self):
        """Dirty checking detects modifications on Unicode source paths and directory prefix."""
        unicode_src = self.repo_dir / "src" / "kiến_trúc.py"
        unicode_src.write_text("print('arch')\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=str(self.repo_dir), capture_output=True, timeout=15, check=True)
        subprocess.run(["git", "commit", "-m", "add unicode src"], cwd=str(self.repo_dir), capture_output=True, timeout=15, check=True)
        rev = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(self.repo_dir), capture_output=True, text=True, encoding="utf-8", timeout=15, check=True).stdout.strip()

        model_data = dict(self.model_data)
        model_data["revision"] = rev
        model_data["repository"] = {"url": "https://example.invalid/repo.git", "revision": rev, "link_mode": "local-only"}
        model_data["source_paths"] = ["src"]
        model_file = self.models_dir / "unicode.model.json"
        model_file.write_text(json.dumps(model_data), encoding="utf-8")

        # Dirty modification on Unicode file
        unicode_src.write_text("print('modified arch')\n", encoding="utf-8")

        with mock.patch.object(
            sys,
            "argv",
            ["tdq_archify.py", "sync-master", "--model", str(model_file), "--project", str(self.repo_dir)],
        ):
            code = tdq_archify.main()
            self.assertNotEqual(code, 0, "Dirty Unicode file in source directory 'src' must trigger failure")

    def test_sync_master_model_lacking_source_paths_status_current(self):
        """Model lacking source_paths derives stable sources without staging directory self-stale."""
        out_dir = self.repo_dir / "docs" / "architecture"
        model_data = dict(self.model_data)
        model_data["evidence_kind"] = "working-tree"
        del model_data["source_paths"]
        model_data.pop("revision", None)
        model_data.pop("repository", None)

        model_file = self.models_dir / "no_source_paths.model.json"
        model_file.write_text(json.dumps(model_data), encoding="utf-8")

        with (
            mock.patch("tdq_archify.run_finalize", side_effect=self._mock_run_finalize_builder()),
            mock.patch.object(
                sys,
                "argv",
                ["tdq_archify.py", "sync-master", "--model", str(model_file), "--project", str(self.repo_dir), "--out", str(out_dir)],
            ),
        ):
            code = tdq_archify.main()
            self.assertEqual(code, 0)

        # Status CLI must report current immediately (no self-stale from staging)
        with mock.patch.object(sys, "argv", ["tdq_archify.py", "status", "--project", str(self.repo_dir)]):
            self.assertEqual(tdq_archify.main(), 0)

    def test_sync_master_builds_all_views_index_and_manifest(self):
        """sync-master renders all views, builds index HTML with escaped labels, and rebases manifest."""
        out_dir = self.repo_dir / "docs" / "architecture"

        with (
            mock.patch("tdq_archify.run_finalize", side_effect=self._mock_run_finalize_builder()),
            mock.patch.object(
                sys,
                "argv",
                [
                    "tdq_archify.py",
                    "sync-master",
                    "--model", str(self.model_path),
                    "--project", str(self.repo_dir),
                    "--out", str(out_dir),
                ],
            ),
        ):
            code = tdq_archify.main()
            self.assertEqual(code, 0)

        index_html = out_dir / "index.html"
        manifest_json = out_dir / "manifest.json"
        self.assertTrue(index_html.is_file())
        self.assertTrue(manifest_json.is_file())

        self.assertTrue((out_dir / "overview.html").is_file())
        self.assertTrue((out_dir / "flow.html").is_file())

        content = index_html.read_text(encoding="utf-8")
        self.assertIn("overview.html", content)
        self.assertIn("flow.html", content)
        self.assertIn(html.escape("Master Architecture <Test & Escape>"), content)
        self.assertIn(html.escape("Overview View <Escaped>"), content)
        self.assertNotIn("<Test & Escape>", content)
        self.assertIn("portal-header", content)
        self.assertIn("meta-grid", content)
        self.assertIn("view-btn", content)

        manifest_data = json.loads(manifest_json.read_text(encoding="utf-8"))
        self.assertNotIn("tmp", manifest_data["artifact_path"])
        self.assertNotIn("staging", manifest_data["artifact_path"])
        self.assertEqual(manifest_data["artifact_path"], "docs/architecture/index.html")

        self.assertIn("child_files", manifest_data)
        self.assertIn("overview.html", manifest_data["child_files"])
        self.assertIn("flow.html", manifest_data["child_files"])

        res = archify_artifacts.check_manifest(self.repo_dir, manifest_json)
        self.assertEqual(res["status"], "current")

    def test_sync_master_preserves_previous_good_bundle_on_failure(self):
        """Failure during sync-master retains existing good bundle at destination."""
        out_dir = self.repo_dir / "docs" / "architecture"

        with (
            mock.patch("tdq_archify.run_finalize", side_effect=self._mock_run_finalize_builder()),
            mock.patch.object(
                sys,
                "argv",
                ["tdq_archify.py", "sync-master", "--model", str(self.model_path), "--project", str(self.repo_dir)],
            ),
        ):
            self.assertEqual(tdq_archify.main(), 0)

        initial_index_content = (out_dir / "index.html").read_text(encoding="utf-8")

        failing_finalize = mock.Mock(return_value=archify_delivery.FinalizeResult(status=False, receipt={"ok": False, "status": "fail"}))
        with (
            mock.patch("tdq_archify.run_finalize", failing_finalize),
            mock.patch.object(
                sys,
                "argv",
                ["tdq_archify.py", "sync-master", "--model", str(self.model_path), "--project", str(self.repo_dir)],
            ),
        ):
            code = tdq_archify.main()
            self.assertNotEqual(code, 0)

        self.assertTrue((out_dir / "index.html").is_file())
        self.assertEqual((out_dir / "index.html").read_text(encoding="utf-8"), initial_index_content)

    def test_sync_master_tracks_child_candidates_and_step_sources(self):
        tdq_models = self.repo_dir / "docs" / "tdq" / "models"
        tdq_models.mkdir(parents=True, exist_ok=True)
        shutil.copy2(self.cand1, tdq_models / "overview.json")
        shutil.copy2(self.cand2, tdq_models / "flow.json")
        extra_src = self.repo_dir / "docs" / "notes.md"
        extra_src.parent.mkdir(parents=True, exist_ok=True)
        extra_src.write_text("# Line 1\n", encoding="utf-8")

        model_data = dict(self.model_data, evidence_kind="working-tree")
        model_data["master"] = {
            "overview": "overview",
            "flows": [{
                "id": "read_flow",
                "text": "Read flow",
                "target": {"diagram": "flow"},
                "steps": [{"id": "s1", "text": "Step", "sources": [{"path": "docs/notes.md", "line": 1}]}],
            }],
        }
        tdq_model_path = tdq_models / "master.model.json"
        tdq_model_path.write_text(json.dumps(model_data), encoding="utf-8")

        with mock.patch("tdq_archify.run_finalize", side_effect=self._mock_run_finalize_builder()):
            self.assertTrue(tdq_archify.sync_master(model=tdq_model_path, project=self.repo_dir))
        self.assertEqual(tdq_archify.check_master_status(self.repo_dir)["status"], "current")

        (tdq_models / "flow.json").write_text(json.dumps({"schema_version": 1, "diagram_type": "workflow", "steps": [{"id": "new"}]}), encoding="utf-8")
        stale_cand = tdq_archify.check_master_status(self.repo_dir)
        self.assertEqual(stale_cand["status"], "stale")
        self.assertTrue(any("docs/tdq/models/flow.json" in r for r in stale_cand["reasons"]))

        shutil.copy2(self.cand2, tdq_models / "flow.json")
        self.assertEqual(tdq_archify.check_master_status(self.repo_dir)["status"], "current")

        extra_src.write_text("# Line 1 changed\n", encoding="utf-8")
        stale_src = tdq_archify.check_master_status(self.repo_dir)
        self.assertEqual(stale_src["status"], "stale")
        self.assertTrue(any("docs/notes.md" in r for r in stale_src["reasons"]))

    def test_sync_master_concurrent_edit_during_render_rejects_and_keeps_last_good(self):
        self.model_data["evidence_kind"] = "working-tree"
        self.model_path.write_text(json.dumps(self.model_data), encoding="utf-8")
        out_dir = self.repo_dir / "docs" / "architecture"

        with mock.patch("tdq_archify.run_finalize", side_effect=self._mock_run_finalize_builder()):
            self.assertTrue(tdq_archify.sync_master(model=self.model_path, project=self.repo_dir))
        last_good_html = (out_dir / "index.html").read_text(encoding="utf-8")
        last_good_manifest = (out_dir / "manifest.json").read_text(encoding="utf-8")

        base_finalize = self._mock_run_finalize_builder()
        def mutating_finalize(diagram_type, candidate_path, output_path, **kwargs):
            res = base_finalize(diagram_type, candidate_path, output_path, **kwargs)
            (self.repo_dir / "src" / "main.py").write_text("print('mutated mid-render')\n", encoding="utf-8")
            return res

        with mock.patch("tdq_archify.run_finalize", side_effect=mutating_finalize):
            self.assertFalse(tdq_archify.sync_master(model=self.model_path, project=self.repo_dir))

        self.assertEqual((out_dir / "index.html").read_text(encoding="utf-8"), last_good_html)
        self.assertEqual((out_dir / "manifest.json").read_text(encoding="utf-8"), last_good_manifest)
        self.assertEqual(tdq_archify.check_master_status(self.repo_dir)["status"], "stale")



class TestStatusAndVerifyCli(unittest.TestCase):
    """Test status and verify CLI sub-commands and child tampering detection."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.temp_dir, True)
        self.repo_dir = Path(self.temp_dir)
        self.rev = _init_git_repo(self.repo_dir)

        self.models_dir = self.repo_dir / "models"
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.cand1 = self.models_dir / "overview.json"
        self.cand1.write_text(json.dumps({"schema_version": 1, "diagram_type": "architecture", "components": []}), encoding="utf-8")
        self.model_path = self.models_dir / "master.model.json"
        self.model_data = {
            "schema_version": 1,
            "title": "Master",
            "evidence_kind": "working-tree",
            "source_paths": ["src/main.py"],
            "coverage": {"modules": []},
            "views": [{"id": "overview", "type": "architecture", "candidate": "overview.json"}],
        }
        self.model_path.write_text(json.dumps(self.model_data), encoding="utf-8")

        def fake_finalize(diagram_type, candidate_path, output_path, **kwargs):
            out_p = Path(output_path)
            out_p.parent.mkdir(parents=True, exist_ok=True)
            out_p.write_text("<html>view content</html>", encoding="utf-8")
            return archify_delivery.FinalizeResult(status=True, receipt={"ok": True, "status": "pass"})

        with (
            mock.patch("tdq_archify.run_finalize", side_effect=fake_finalize),
            mock.patch.object(
                sys,
                "argv",
                ["tdq_archify.py", "sync-master", "--model", str(self.model_path), "--project", str(self.repo_dir)],
            ),
        ):
            self.assertEqual(tdq_archify.main(), 0)

    def test_status_cli_current(self):
        """CLI status reports current and exits 0 when bundle is unmodified."""
        with mock.patch.object(sys, "argv", ["tdq_archify.py", "status", "--project", str(self.repo_dir)]):
            code = tdq_archify.main()
            self.assertEqual(code, 0)

    def test_status_cli_detects_child_tampering(self):
        """Modifying a child file causes status to detect tampering and return non-zero."""
        child_view = self.repo_dir / "docs" / "architecture" / "overview.html"
        child_view.write_text("<html>TAMPERED</html>", encoding="utf-8")

        with mock.patch.object(sys, "argv", ["tdq_archify.py", "status", "--project", str(self.repo_dir)]):
            code = tdq_archify.main()
            self.assertNotEqual(code, 0)

    def test_status_cli_detects_child_missing(self):
        """Deleting a child file causes status to report missing and return non-zero."""
        child_view = self.repo_dir / "docs" / "architecture" / "overview.html"
        child_view.unlink()

        with mock.patch.object(sys, "argv", ["tdq_archify.py", "status", "--project", str(self.repo_dir)]):
            code = tdq_archify.main()
            self.assertNotEqual(code, 0)

    def test_verify_cli_success_and_stale(self):
        """CLI verify checks binding and manifest, exiting non-zero when stale."""
        spec_dir = self.repo_dir / "docs" / "tdq" / "spec"
        spec_dir.mkdir(parents=True, exist_ok=True)
        doc = spec_dir / "SPEC.md"
        doc.write_text("# Spec Content\n", encoding="utf-8")
        out_html = spec_dir / "preview.html"

        fake_res = archify_delivery.FinalizeResult(
            status=True,
            receipt={
                "ok": True,
                "status": "pass",
                "artifact": str(out_html),
                "gates": {"validate": "pass", "deliver": "pass", "check": "pass", "browser-check": "pass"},
            },
        )

        def mock_finalize(diagram_type, candidate_path, output_path, **kwargs):
            Path(output_path).write_text("<html>preview</html>", encoding="utf-8")
            return fake_res

        with (
            mock.patch("tdq_archify.run_finalize", side_effect=mock_finalize),
            mock.patch.object(
                sys,
                "argv",
                [
                    "tdq_archify.py",
                    "render",
                    "--type", "architecture",
                    "--candidate", str(self.cand1),
                    "--out", str(out_html),
                    "--document", str(doc),
                    "--project", str(self.repo_dir),
                ],
            ),
        ):
            code_render = tdq_archify.main()
            self.assertEqual(code_render, 0)

        manifest_path = out_html.with_suffix(".manifest.json")
        self.assertTrue(manifest_path.is_file())

        with mock.patch.object(
            sys,
            "argv",
            ["tdq_archify.py", "verify", "--document", str(doc), "--manifest", str(manifest_path), "--project", str(self.repo_dir)],
        ):
            code = tdq_archify.main()
            self.assertEqual(code, 0)

        doc.write_text("# Corrupted Content\n" + doc.read_text(encoding="utf-8"), encoding="utf-8")
        with mock.patch.object(
            sys,
            "argv",
            ["tdq_archify.py", "verify", "--document", str(doc), "--manifest", str(manifest_path), "--project", str(self.repo_dir)],
        ):
            code = tdq_archify.main()
            self.assertNotEqual(code, 0)


class TestLocalArchifyRealEngineSmoke(unittest.TestCase):
    """Smoke test against real local Archify installation at ~/Documents/archify if available."""

    def test_local_archify_explainer_smoke(self):
        """If real Archify is installed, run explainer finalize smoke without mocking."""
        env = archify_delivery.check_environment()
        if not env.get("ready"):
            self.skipTest(f"Real Archify not ready: {env.get('error')}")

        temp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, temp_dir, True)
        cand_path = Path(temp_dir) / "explainer.candidate.json"
        out_html = Path(temp_dir) / "explainer.html"

        candidate_ir = {
            "schema_version": 1,
            "diagram_type": "explainer",
            "meta": {
                "id": "explainer_smoke",
                "title": "Explainer Smoke",
            },
            "answer": {
                "summary": "This is a smoke test explainer summary.",
            },
            "panels": [
                {
                    "id": "panel_1",
                    "title": "Panel 1",
                    "blocks": [
                        {
                            "id": "block_1",
                            "type": "prose",
                            "text": "Detailed text content for block 1.",
                        }
                    ],
                }
            ],
            "sources": [],
        }
        cand_path.write_text(json.dumps(candidate_ir), encoding="utf-8")

        result = archify_delivery.run_finalize(
            diagram_type="explainer",
            candidate_path=cand_path,
            output_path=out_html,
            quality="showcase",
            timeout=120,
        )

        self.assertTrue(result.status, f"Explainer smoke failed: {result.receipt}")
        self.assertTrue(out_html.is_file(), f"Output HTML not generated: {out_html}")
        receipt = result.receipt
        self.assertEqual(receipt.get("status"), "pass")
        self.assertEqual(receipt.get("gates", {}).get("validate"), "pass")
        self.assertEqual(receipt.get("gates", {}).get("deliver"), "pass")
        self.assertEqual(receipt.get("gates", {}).get("check"), "pass")

    def test_real_bound_explainer_render_then_verify_current(self):
        """Real Archify engine explainer render with document binding then verify immediately current."""
        env = archify_delivery.check_environment()
        if not env.get("ready"):
            self.skipTest(f"Real Archify not ready: {env.get('error')}")

        temp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, temp_dir, True)
        project_root = Path(temp_dir)
        _init_git_repo(project_root)

        spec_dir = project_root / "docs" / "tdq" / "spec"
        spec_dir.mkdir(parents=True, exist_ok=True)
        doc_path = spec_dir / "sample.spec.md"
        doc_path.write_text("# Sample Spec\n\nExplainer preview specification.\n", encoding="utf-8")

        cand_path = spec_dir / "sample.explainer.candidate.json"
        candidate_ir = {
            "schema_version": 1,
            "diagram_type": "explainer",
            "meta": {
                "id": "explainer_bound",
                "title": "Explainer Bound Preview",
            },
            "answer": {
                "summary": "Bound explainer preview for project architecture.",
            },
            "panels": [
                {
                    "id": "panel_bound",
                    "title": "Overview Panel",
                    "blocks": [
                        {
                            "id": "block_bound",
                            "type": "prose",
                            "text": "Detailed explanation of architecture components.",
                        }
                    ],
                }
            ],
            "sources": [],
        }
        cand_path.write_text(json.dumps(candidate_ir), encoding="utf-8")
        out_html = spec_dir / "sample-preview.html"

        # 1. Render real explainer diagram with document binding
        with mock.patch.object(
            sys,
            "argv",
            [
                "tdq_archify.py",
                "render",
                "--type", "explainer",
                "--candidate", str(cand_path),
                "--out", str(out_html),
                "--document", str(doc_path),
                "--project", str(project_root),
            ],
        ):
            code_render = tdq_archify.main()
            self.assertEqual(code_render, 0)

        self.assertTrue(out_html.is_file())
        manifest_path = out_html.with_suffix(".manifest.json")
        self.assertTrue(manifest_path.is_file())

        # 2. Verify document and manifest immediately current
        with mock.patch.object(
            sys,
            "argv",
            [
                "tdq_archify.py",
                "verify",
                "--document", str(doc_path),
                "--manifest", str(manifest_path),
                "--project", str(project_root),
            ],
        ):
            code_verify = tdq_archify.main()
            self.assertEqual(code_verify, 0, "Real bound explainer must verify as current immediately")


def _make_logic_node(
    node_id: str,
    *,
    src_path: str,
    symbol_ref: str,
    abs_src: Path,
    depth: int = 1,
    evidence_kind: str = "working-tree",
    slice_id: str | None = None,
    steps: list[dict] | None = None,
) -> dict:
    """Create a validated Logic Node JSON fixture using real AST hashing."""
    import archify_registry

    sym_name = symbol_ref.split("::")[-1]
    if evidence_kind == "planned":
        ast_hash = None
        span = {"path": src_path, "line": 1, "end_line": 2}
    else:
        extracted = archify_registry.extract_symbol_ast_hash(abs_src, sym_name)
        ast_hash = extracted["ast_symbol_sha256"]
        span = {**extracted["span_binding"], "path": src_path}
    node: dict = {
        "node_id": node_id,
        "title": f"Title {node_id}",
        "depth": depth,
        "node_kind": "flow_root" if depth == 1 else "storage_io",
        "hydration_tier": "eager_l1_l2" if depth <= 2 else "lazy_l3_plus",
        "evidence_kind": evidence_kind,
        "fingerprint": {
            "symbol_ref": symbol_ref,
            "ast_symbol_sha256": ast_hash,
            "span_binding": span,
            "render_slice_sha256": None,
            "cache_status": "planned_draft" if evidence_kind == "planned" else "clean",
        },
        "natural_explanation": {
            "summary": f"Summary for {node_id}.",
            "what_goes_where": "Passes structured data downstream.",
            "why_it_exists": "Keeps module boundaries testable.",
            "edge_cases": ["Invalid input fails closed"],
        },
        "io_contract": {
            "inputs": ["payload: dict"],
            "outputs": ["ok: bool"],
            "side_effects": ["Emits stderr log"],
        },
        "sources": [dict(span)],
        "reused_by": ["flow-auth"],
    }
    if slice_id and steps is not None:
        node["sub_flow"] = {
            "slice_id": slice_id,
            "max_cols": 3,
            "steps": steps,
            "edges": [],
        }
    return node


class TestIncrementalRegistrySyncPipeline(unittest.TestCase):
    """Test incremental vs full sync-master when master.registry is configured."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.temp_dir, True)
        self.repo_dir = Path(self.temp_dir)
        self.auth_src = self.repo_dir / "src" / "auth.py"
        self.billing_src = self.repo_dir / "src" / "billing.py"
        self.auth_src.parent.mkdir(parents=True, exist_ok=True)
        self.auth_src.write_text(
            "def verify_token(token: str) -> bool:\n    return len(token) > 3\n",
            encoding="utf-8",
        )
        self.billing_src.write_text(
            "def charge(amount: int) -> int:\n    return amount * 100\n",
            encoding="utf-8",
        )

        self.models_dir = self.repo_dir / "models"
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.overview_cand = self.models_dir / "overview.json"
        self.overview_cand.write_text(
            json.dumps({
                "schema_version": 1,
                "diagram_type": "architecture",
                "components": [{"id": "flow-auth", "type": "security", "label": "Auth"}],
            }),
            encoding="utf-8",
        )

        self.reg_dir = self.repo_dir / "docs" / "tdq" / "models" / "registry"
        nodes_dir = self.reg_dir / "nodes"
        nodes_dir.mkdir(parents=True, exist_ok=True)
        self.flow_auth_path = nodes_dir / "flow-auth.json"
        self.node_billing_path = nodes_dir / "node-billing.json"

        self.flow_auth_path.write_text(
            json.dumps(_make_logic_node(
                "flow-auth",
                src_path="src/auth.py",
                symbol_ref="src/auth.py::verify_token",
                abs_src=self.auth_src,
                depth=1,
                slice_id="slice-auth",
                steps=[{"step_id": "s1", "label": "Verify", "col": 0, "lane": "main", "target_node_id": "node-billing"}],
            ), indent=2),
            encoding="utf-8",
        )
        self.node_billing_path.write_text(
            json.dumps(_make_logic_node(
                "node-billing",
                src_path="src/billing.py",
                symbol_ref="src/billing.py::charge",
                abs_src=self.billing_src,
                depth=2,
                slice_id="slice-billing",
                steps=[{"step_id": "b1", "label": "Charge", "col": 0, "lane": "main"}],
            ), indent=2),
            encoding="utf-8",
        )

        self.model_path = self.models_dir / "master.model.json"
        self.model_data = {
            "schema_version": 1,
            "title": "Registry Master Portal",
            "evidence_kind": "working-tree",
            "source_paths": ["src/auth.py", "src/billing.py"],
            "coverage": {"modules": [{"id": "auth", "status": "selected"}]},
            "views": [{"id": "overview", "type": "architecture", "candidate": "overview.json"}],
            "master": {
                "overview": "overview",
                "flows": [],
                "registry": {
                    "path": "docs/tdq/models/registry",
                    "root_flows": ["flow-auth"],
                    "max_depth": 4,
                },
            },
        }
        self.model_path.write_text(json.dumps(self.model_data, indent=2), encoding="utf-8")

    def _spy_finalize(self, calls: list[tuple[str, str]], *, with_svg: bool = True):
        def fake_finalize(diagram_type, candidate_path, output_path, **kwargs):
            calls.append((diagram_type, Path(candidate_path).name))
            out_p = Path(output_path)
            out_p.parent.mkdir(parents=True, exist_ok=True)
            if with_svg:
                nid = "flow-auth" if diagram_type == "architecture" else "node-billing"
                out_p.write_text(
                    f'<html><svg viewBox="0 0 640 180"><g data-node-id="{nid}"></g></svg></html>',
                    encoding="utf-8",
                )
            else:
                out_p.write_text(f"<html>{diagram_type} content</html>", encoding="utf-8")
            return archify_delivery.FinalizeResult(
                status=True,
                receipt={
                    "ok": True,
                    "status": "pass",
                    "artifact": str(out_p),
                    "gates": {"validate": "pass", "deliver": "pass", "check": "pass", "browser-check": "pass"},
                },
            )
        return fake_finalize

    def test_incremental_sync_reuses_clean_and_span_shifted_slices(self):
        """Run 1 builds portal + slices; run 2 (unchanged & line-shifted) invokes run_finalize 0 times."""
        calls: list[tuple[str, str]] = []
        with (
            mock.patch("tdq_archify.run_finalize", side_effect=self._spy_finalize(calls)),
            mock.patch.object(
                sys, "argv",
                ["tdq_archify.py", "sync-master", "--model", str(self.model_path), "--project", str(self.repo_dir), "--incremental"],
            ),
        ):
            self.assertEqual(tdq_archify.main(), 0)

        self.assertEqual(len(calls), 3)
        out_dir = self.repo_dir / "docs" / "architecture"
        index_bytes = (out_dir / "index.html").read_bytes()
        self.assertLess(len(index_bytes), 300_000)
        self.assertIn(b"registry-bundle.js", index_bytes)
        self.assertTrue((out_dir / "registry-bundle.js").is_file())
        self.assertTrue((out_dir / "slices" / "slice-auth.svg").is_file())
        self.assertTrue((out_dir / "slices" / "slice-billing.svg").is_file())
        self.assertTrue((out_dir / "nodes" / "flow-auth.json").is_file())
        self.assertNotIn("onclick=", (out_dir / "slices" / "slice-auth.svg").read_text(encoding="utf-8"))

        manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
        self.assertIn("slice_cache", manifest)
        for key in ("slices/slice-auth.svg", "slices/slice-billing.svg", "nodes/flow-auth.json", "registry-bundle.js"):
            self.assertIn(key, manifest["child_files"])
        self.assertEqual(tdq_archify.check_master_status(self.repo_dir)["status"], "current")

        calls.clear()
        with (
            mock.patch("tdq_archify.run_finalize", side_effect=self._spy_finalize(calls)),
            mock.patch.object(
                sys, "argv",
                ["tdq_archify.py", "sync-master", "--model", str(self.model_path), "--project", str(self.repo_dir), "--incremental"],
            ),
        ):
            self.assertEqual(tdq_archify.main(), 0)
        self.assertEqual(calls, [])
        self.assertEqual(tdq_archify.check_master_status(self.repo_dir)["status"], "current")

        # Shift function down 10 lines + add comments/docstring (same AST!)
        shifted_src = "\n".join(["# top comment"] * 10) + (
            '\ndef verify_token(token: str) -> bool:\n    """Docstring ignored by AST."""\n'
            "    # inline comment\n    return len(token) > 3\n"
        )
        self.auth_src.write_text(shifted_src, encoding="utf-8")
        calls.clear()
        with (
            mock.patch("tdq_archify.run_finalize", side_effect=self._spy_finalize(calls)),
            mock.patch.object(
                sys, "argv",
                ["tdq_archify.py", "sync-master", "--model", str(self.model_path), "--project", str(self.repo_dir), "--incremental"],
            ),
        ):
            self.assertEqual(tdq_archify.main(), 0)
        self.assertEqual(calls, [])
        updated_node = json.loads((out_dir / "nodes" / "flow-auth.json").read_text(encoding="utf-8"))
        self.assertGreaterEqual(updated_node["fingerprint"]["span_binding"]["line"], 11)
        self.assertEqual(tdq_archify.check_master_status(self.repo_dir)["status"], "current")

    def test_incremental_sync_rerenders_only_dirty_slice_and_full_rebuilds_all(self):
        """Editing one node body re-renders only that node's slice; --full rebuilds all."""
        calls: list[tuple[str, str]] = []
        with mock.patch("tdq_archify.run_finalize", side_effect=self._spy_finalize(calls)):
            self.assertTrue(tdq_archify.sync_master(model=self.model_path, project=self.repo_dir, incremental=True))
        self.assertEqual(len(calls), 3)

        self.auth_src.write_text(
            "def verify_token(token: str) -> bool:\n    return len(token) > 8\n",
            encoding="utf-8",
        )
        calls.clear()
        with mock.patch("tdq_archify.run_finalize", side_effect=self._spy_finalize(calls)):
            self.assertTrue(tdq_archify.sync_master(model=self.model_path, project=self.repo_dir, incremental=True))
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][0], "workflow")
        self.assertEqual(tdq_archify.check_master_status(self.repo_dir)["status"], "current")

        calls.clear()
        with (
            mock.patch("tdq_archify.run_finalize", side_effect=self._spy_finalize(calls)),
            mock.patch.object(
                sys, "argv",
                ["tdq_archify.py", "sync-master", "--model", str(self.model_path), "--project", str(self.repo_dir), "--incremental", "--full"],
            ),
        ):
            self.assertEqual(tdq_archify.main(), 0)
        self.assertEqual(len(calls), 3)

    def test_incremental_sync_rollback_on_dirty_slice_failure(self):
        """Failure during dirty slice finalize preserves previous bundle untouched."""
        calls: list[tuple[str, str]] = []
        with mock.patch("tdq_archify.run_finalize", side_effect=self._spy_finalize(calls)):
            self.assertTrue(tdq_archify.sync_master(model=self.model_path, project=self.repo_dir, incremental=True))

        out_dir = self.repo_dir / "docs" / "architecture"
        prev_index = (out_dir / "index.html").read_bytes()
        prev_manifest = (out_dir / "manifest.json").read_bytes()
        prev_slice = (out_dir / "slices" / "slice-auth.svg").read_bytes()

        self.auth_src.write_text(
            "def verify_token(token: str) -> bool:\n    return len(token) > 12\n",
            encoding="utf-8",
        )
        fail_res = archify_delivery.FinalizeResult(status=False, receipt={"ok": False, "status": "fail"})
        with mock.patch("tdq_archify.run_finalize", return_value=fail_res):
            self.assertFalse(tdq_archify.sync_master(model=self.model_path, project=self.repo_dir, incremental=True))

        self.assertEqual((out_dir / "index.html").read_bytes(), prev_index)
        self.assertEqual((out_dir / "manifest.json").read_bytes(), prev_manifest)
        self.assertEqual((out_dir / "slices" / "slice-auth.svg").read_bytes(), prev_slice)

        calls.clear()
        with mock.patch("tdq_archify.run_finalize", side_effect=self._spy_finalize(calls)):
            self.assertTrue(tdq_archify.sync_master(model=self.model_path, project=self.repo_dir, incremental=True))
        self.assertEqual(len(calls), 1)
        self.assertEqual(tdq_archify.check_master_status(self.repo_dir)["status"], "current")

    def test_sync_master_rejects_planned_node_in_registry(self):
        """Master sync fails closed when any Logic Node in registry has evidence_kind='planned'."""
        planned_path = self.reg_dir / "nodes" / "planned-draft.json"
        planned_path.write_text(
            json.dumps(_make_logic_node(
                "planned-draft",
                src_path="src/auth.py",
                symbol_ref="src/auth.py::verify_token",
                abs_src=self.auth_src,
                depth=2,
                evidence_kind="planned",
            ), indent=2),
            encoding="utf-8",
        )
        with mock.patch("tdq_archify.run_finalize") as mock_fin:
            self.assertFalse(tdq_archify.sync_master(model=self.model_path, project=self.repo_dir, incremental=True))
            mock_fin.assert_not_called()

    def test_incremental_sync_placeholder_svg_when_no_svg_returned(self):
        """Generates clean data-node-id placeholder SVG without onclick when mock returns plain HTML."""
        calls: list[tuple[str, str]] = []
        with mock.patch("tdq_archify.run_finalize", side_effect=self._spy_finalize(calls, with_svg=False)):
            self.assertTrue(tdq_archify.sync_master(model=self.model_path, project=self.repo_dir, incremental=True))
        svg_text = (self.repo_dir / "docs" / "architecture" / "slices" / "slice-auth.svg").read_text(encoding="utf-8")
        self.assertIn("<svg", svg_text)
        self.assertIn('data-node-id="node-billing"', svg_text)
        self.assertNotIn("onclick=", svg_text)

    def test_incremental_sync_repairs_only_missing_slice_svg(self):
        """Deleting one published slice SVG re-renders only that missing slice on incremental sync."""
        calls: list[tuple[str, str]] = []
        with mock.patch("tdq_archify.run_finalize", side_effect=self._spy_finalize(calls)):
            self.assertTrue(tdq_archify.sync_master(model=self.model_path, project=self.repo_dir, incremental=True))
        (self.repo_dir / "docs" / "architecture" / "slices" / "slice-billing.svg").unlink()

        calls.clear()
        with mock.patch("tdq_archify.run_finalize", side_effect=self._spy_finalize(calls)):
            self.assertTrue(tdq_archify.sync_master(model=self.model_path, project=self.repo_dir, incremental=True))
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][0], "workflow")
        self.assertEqual(tdq_archify.check_master_status(self.repo_dir)["status"], "current")

    def test_sync_master_rejects_escaping_registry_path(self):
        """Registry path resolving outside project_root fails closed before rendering."""
        bad_model = self.models_dir / "escape_reg.model.json"
        bad_data = json.loads(self.model_path.read_text(encoding="utf-8"))
        bad_data["master"]["registry"]["path"] = "../outside_registry"
        bad_model.write_text(json.dumps(bad_data), encoding="utf-8")
        with mock.patch("tdq_archify.run_finalize") as mock_fin:
            self.assertFalse(tdq_archify.sync_master(model=bad_model, project=self.repo_dir, incremental=True))
            mock_fin.assert_not_called()


class TestDrilldownRenderCli(unittest.TestCase):
    """Test render --type drilldown and verify integration."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.temp_dir, True)
        self.repo_dir = Path(self.temp_dir)
        self.doc_path = self.repo_dir / "SPEC.md"
        self.doc_path.write_text("# Drilldown Spec\n\nArchitecture preview.\n", encoding="utf-8")
        self.out_html = self.repo_dir / "preview.html"

    def test_render_drilldown_valid_binds_and_verifies_current(self):
        """render --type drilldown generates standalone HTML, binds doc, and verifies current."""
        cand_path = self.repo_dir / "drilldown.candidate.json"
        cand = {
            "title": "Auth Drilldown Preview",
            "evidence_kind": "planned",
            "root_flows": ["n1"],
            "nodes": {
                "n1": {
                    "node_id": "n1", "title": "Root", "depth": 1,
                    "sub_flow": {"slice_id": "s1", "max_cols": 2, "steps": [{"step_id": "st1", "label": "Next", "col": 0, "lane": "main", "target_node_id": "n2"}], "edges": []},
                },
                "n2": {
                    "node_id": "n2", "title": "Branch", "depth": 2,
                    "sub_flow": {"slice_id": "s2", "max_cols": 2, "steps": [{"step_id": "st2", "label": "Leaf", "col": 0, "lane": "main", "target_node_id": "n3"}], "edges": []},
                },
                "n3": {"node_id": "n3", "title": "Leaf", "depth": 3},
            },
        }
        cand_path.write_text(json.dumps(cand), encoding="utf-8")

        with (
            mock.patch("sys.stdout", new_callable=io.StringIO) as out_buf,
            mock.patch.object(
                sys,
                "argv",
                [
                    "tdq_archify.py", "render", "--type", "drilldown",
                    "--candidate", str(cand_path), "--out", str(self.out_html),
                    "--document", str(self.doc_path), "--project", str(self.repo_dir),
                ],
            ),
        ):
            self.assertEqual(tdq_archify.main(), 0)

        res_json = json.loads(out_buf.getvalue())
        self.assertEqual(res_json["engine"], "archify-portal")
        self.assertEqual(res_json["diagram_type"], "drilldown")
        self.assertIn("window.__TDQ_ARCHIFY_REGISTRY__", self.out_html.read_text(encoding="utf-8"))

        manifest_path = self.out_html.with_suffix(".manifest.json")
        with mock.patch.object(
            sys,
            "argv",
            ["tdq_archify.py", "verify", "--document", str(self.doc_path), "--manifest", str(manifest_path), "--project", str(self.repo_dir)],
        ):
            self.assertEqual(tdq_archify.main(), 0)

    def test_render_drilldown_depth_gt_4_fails_closed_preserving_previous(self):
        """render --type drilldown fails closed when depth > 4 and preserves previous HTML."""
        self.out_html.write_text("<html>PREVIOUS_DRILLDOWN</html>", encoding="utf-8")
        bad_cand = self.repo_dir / "too_deep.candidate.json"
        bad_cand.write_text(json.dumps({
            "title": "Too Deep",
            "evidence_kind": "planned",
            "root_flows": ["n1"],
            "nodes": {
                "n1": {"node_id": "n1", "title": "L1", "depth": 1, "sub_flow": {"slice_id": "s1", "max_cols": 2, "steps": [{"step_id": "a", "label": "N2", "col": 0, "target_node_id": "n2"}], "edges": []}},
                "n2": {"node_id": "n2", "title": "L2", "depth": 2, "sub_flow": {"slice_id": "s2", "max_cols": 2, "steps": [{"step_id": "b", "label": "N3", "col": 0, "target_node_id": "n3"}], "edges": []}},
                "n3": {"node_id": "n3", "title": "L3", "depth": 3, "sub_flow": {"slice_id": "s3", "max_cols": 2, "steps": [{"step_id": "c", "label": "N4", "col": 0, "target_node_id": "n4"}], "edges": []}},
                "n4": {"node_id": "n4", "title": "L4", "depth": 4, "sub_flow": {"slice_id": "s4", "max_cols": 2, "steps": [{"step_id": "d", "label": "N5", "col": 0, "target_node_id": "n5"}], "edges": []}},
                "n5": {"node_id": "n5", "title": "L5", "depth": 5},
            },
        }), encoding="utf-8")

        with (
            mock.patch("tdq_archify.run_finalize") as mock_fin,
            mock.patch.object(
                sys,
                "argv",
                [
                    "tdq_archify.py", "render", "--type", "drilldown",
                    "--candidate", str(bad_cand), "--out", str(self.out_html),
                    "--document", str(self.doc_path), "--project", str(self.repo_dir),
                ],
            ),
        ):
            self.assertNotEqual(tdq_archify.main(), 0)
            mock_fin.assert_not_called()
        self.assertEqual(self.out_html.read_text(encoding="utf-8"), "<html>PREVIOUS_DRILLDOWN</html>")

    def test_render_single_slice_isolates_archify_sidecars_from_staging(self):
        """_render_single_slice isolates temporary files and sidecars outside staging_dir."""
        staging_dir = self.repo_dir / ".staging-slice-test"
        staging_dir.mkdir(parents=True, exist_ok=True)
        captured_paths: list[Path] = []

        def fake_finalize(diagram_type, candidate_path, output_path, **kwargs):
            out_p = Path(output_path)
            cand_p = Path(candidate_path)
            captured_paths.extend([cand_p, out_p])
            out_p.write_text('<html><svg viewBox="0 0 200 80"><g data-node-id="s1"></g></svg></html>', encoding="utf-8")
            for ext in (".manifest.json", ".receipt.json", ".finalize.json", ".finalize-summary.json", ".delivery.json"):
                out_p.with_suffix(ext).write_text("{}", encoding="utf-8")
            return archify_delivery.FinalizeResult(
                status=True,
                receipt={
                    "ok": True, "status": "pass", "artifact": str(out_p),
                    "gates": {"validate": "pass", "deliver": "pass", "check": "pass", "browser-check": "pass"},
                },
            )

        owner_nodes = [{
            "node_id": "n-slice", "title": "Slice",
            "sub_flow": {
                "slice_id": "slice-very-long-pilot-name",
                "max_cols": 2,
                "steps": [{"step_id": "s1", "label": "One", "col": 0}],
                "edges": [],
            },
        }]
        with mock.patch("tdq_archify.run_finalize", side_effect=fake_finalize):
            svg = tdq_archify._render_single_slice(
                "slice-very-long-pilot-name", owner_nodes, staging_dir, self.repo_dir, "showcase", "en",
            )
        self.assertIn("<svg", svg)
        self.assertEqual(list(staging_dir.iterdir()), [])
        self.assertTrue(all(p.parent != staging_dir for p in captured_paths))
        self.assertTrue(all(not p.exists() for p in captured_paths))

    def test_atomic_swap_directory_cleans_temp_dest_on_copytree_failure(self):
        """_atomic_swap_directory removes partial temp_dest if shutil.copytree fails."""
        import archify_artifacts

        dest_dir = self.repo_dir / "dest_bundle"
        dest_dir.mkdir(parents=True, exist_ok=True)
        staging_dir = self.repo_dir / "staging_fail"
        staging_dir.mkdir(parents=True, exist_ok=True)

        def fail_copytree(src, dst, **kwargs):
            Path(dst).mkdir(parents=True, exist_ok=True)
            raise OSError("Simulated WinError 3 MAX_PATH failure")

        with (
            mock.patch.object(archify_artifacts.shutil, "copytree", side_effect=fail_copytree),
            self.assertRaises(OSError),
        ):
            archify_artifacts._atomic_swap_directory(staging_dir, dest_dir)
        leaked = [p for p in self.repo_dir.iterdir() if p.name.startswith(f".{dest_dir.name}.tmp.")]
        self.assertEqual(leaked, [])


if __name__ == "__main__":
    unittest.main()
