"""Unit tests for scripts/archify_registry.py."""
from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_TESTS_DIR = Path(__file__).resolve().parent
_SCRIPTS_DIR = _TESTS_DIR.parent / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))


def _make_node(
    node_id: str,
    *,
    path: str = "src/app.py",
    symbol_ref: str = "src/app.py::compute",
    line: int = 1,
    end_line: int = 5,
    depth: int = 1,
    evidence_kind: str = "working-tree",
    ast_hash: str | None = None,
    slice_id: str | None = None,
    steps: list[dict] | None = None,
    edges: list[dict] | None = None,
    reused_by: list[str] | None = None,
) -> dict:
    """Create a valid Logic Node fixture dictionary."""
    tier = "eager_l1_l2" if depth <= 2 else "lazy_l3_plus"
    cache_status = "planned_draft" if evidence_kind == "planned" else "clean"
    node: dict = {
        "node_id": node_id,
        "title": f"Node {node_id}",
        "depth": depth,
        "node_kind": "flow_root" if depth == 1 else "decision_branch",
        "hydration_tier": tier,
        "evidence_kind": evidence_kind,
        "fingerprint": {
            "symbol_ref": symbol_ref,
            "ast_symbol_sha256": ast_hash,
            "span_binding": {"path": path, "line": line, "end_line": end_line},
            "render_slice_sha256": f"slice-hash-{node_id}" if slice_id else None,
            "cache_status": cache_status,
        },
        "natural_explanation": {
            "summary": f"Executes {node_id} step.",
            "what_goes_where": "Reads input and writes verified state.",
            "why_it_exists": "Keeps pipeline checks modular.",
            "edge_cases": ["Missing input fails closed"],
        },
        "io_contract": {
            "inputs": ["request_payload"],
            "outputs": ["result_dict"],
            "side_effects": ["Writes stderr log"],
        },
        "sources": [{"path": path, "line": line, "end_line": end_line}],
        "reused_by": reused_by or ["flow-root"],
    }
    if slice_id and steps is not None:
        node["sub_flow"] = {
            "slice_id": slice_id,
            "max_cols": 4,
            "steps": steps,
            "edges": edges or [],
        }
    return node


class TestArchifyRegistryTreeSitter(unittest.TestCase):
    """Tests for tree-sitter availability checks and AST symbol hashing."""

    def setUp(self) -> None:
        self.tmp_dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp_dir, True)

    def test_tree_sitter_packages_and_support(self) -> None:
        import archify_registry

        self.assertEqual(
            archify_registry.TREE_SITTER_PACKAGES,
            (
                "tree-sitter",
                "tree-sitter-python",
                "tree-sitter-javascript",
                "tree-sitter-typescript",
                "tree-sitter-rust",
            ),
        )
        info = archify_registry.check_tree_sitter_support()
        self.assertTrue(info["available"])
        self.assertEqual(info["missing"], [])
        self.assertIn("python", info["languages"])
        self.assertIn("rust", info["languages"])
        self.assertTrue(info["modules"]["tree_sitter_typescript"])

    def test_check_tree_sitter_support_detects_missing_package(self) -> None:
        import archify_registry

        with mock.patch.dict(sys.modules, {"tree_sitter_rust": None}):
            info = archify_registry.check_tree_sitter_support()
        self.assertFalse(info["available"])
        self.assertEqual(info["missing"], ["tree-sitter-rust"])

    def test_extract_symbol_ast_hash_python_js_ts_tsx_rust(self) -> None:
        import archify_registry

        py_file = self.tmp_dir / "calc.py"
        py_file.write_text(
            "class Calc:\n    def add(self, x: int) -> int:\n        return x + 1\n",
            encoding="utf-8",
        )
        js_file = self.tmp_dir / "calc.js"
        js_file.write_text(
            "export function add(x) {\n  return x + 1;\n}\n",
            encoding="utf-8",
        )
        ts_file = self.tmp_dir / "calc.ts"
        ts_file.write_text(
            "class Calc {\n  add(x: number): number {\n    return x + 1;\n  }\n}\n",
            encoding="utf-8",
        )
        tsx_file = self.tmp_dir / "view.tsx"
        tsx_file.write_text(
            "export function Badge() {\n  return <span>ok</span>;\n}\n",
            encoding="utf-8",
        )
        rs_file = self.tmp_dir / "calc.rs"
        rs_file.write_text(
            "pub struct Calc;\nimpl Calc {\n    pub fn add(&self, x: i32) -> i32 {\n        x + 1\n    }\n}\n",
            encoding="utf-8",
        )

        checks = [
            (py_file, "Calc.add", 2, 3),
            (js_file, "add", 1, 3),
            (ts_file, "Calc.add", 2, 4),
            (tsx_file, "Badge", 1, 3),
            (rs_file, "Calc.add", 3, 5),
        ]
        for path, sym, exp_start, exp_end in checks:
            with self.subTest(path=path.name, symbol=sym):
                res = archify_registry.extract_symbol_ast_hash(path, sym)
                self.assertEqual(res["hash_mode"], "tree_sitter_ast")
                self.assertRegex(res["ast_symbol_sha256"], r"^[a-f0-9]{64}$")
                self.assertEqual(res["span_binding"]["line"], exp_start)
                self.assertEqual(res["span_binding"]["end_line"], exp_end)
                self.assertEqual(res["symbol"], sym)

    def test_ast_hash_ignores_comments_docstrings_and_line_shifts(self) -> None:
        import archify_registry

        py_file = self.tmp_dir / "service.py"
        py_file.write_text(
            "def compute(val):\n    return val * 2\n",
            encoding="utf-8",
        )
        orig = archify_registry.extract_symbol_ast_hash(py_file, "compute")

        shifted_lines = "\n" * 18
        py_file.write_text(
            f"{shifted_lines}# Leading comment\ndef compute(val):\n"
            '    """Added docstring."""\n'
            "    # Inline comment\n"
            "    return val * 2  # trailing\n",
            encoding="utf-8",
        )
        shifted = archify_registry.extract_symbol_ast_hash(py_file, "compute")
        self.assertEqual(shifted["hash_mode"], "tree_sitter_ast")
        self.assertEqual(shifted["ast_symbol_sha256"], orig["ast_symbol_sha256"])
        self.assertEqual(shifted["span_binding"]["line"], 20)
        self.assertEqual(shifted["span_binding"]["end_line"], 23)

        py_file.write_text(
            f"{shifted_lines}def compute(val):\n    if val > 0:\n        'branch_a'\n    return val * 2\n",
            encoding="utf-8",
        )
        branch_a = archify_registry.extract_symbol_ast_hash(py_file, "compute")
        py_file.write_text(
            f"{shifted_lines}def compute(val):\n    if val > 0:\n        'branch_b'\n    return val * 2\n",
            encoding="utf-8",
        )
        branch_b = archify_registry.extract_symbol_ast_hash(py_file, "compute")
        self.assertNotEqual(branch_a["ast_symbol_sha256"], branch_b["ast_symbol_sha256"])

        py_file.write_text(
            f"{shifted_lines}def compute(val):\n    return val * 3\n",
            encoding="utf-8",
        )
        modified = archify_registry.extract_symbol_ast_hash(py_file, "compute")
        self.assertNotEqual(modified["ast_symbol_sha256"], orig["ast_symbol_sha256"])

        js_arrow = self.tmp_dir / "arrow.js"
        js_arrow.write_text("export const calcArrow = (a) => a + 1;\n", encoding="utf-8")
        arrow_res = archify_registry.extract_symbol_ast_hash(js_arrow, "calcArrow")
        self.assertEqual(arrow_res["hash_mode"], "tree_sitter_ast")
        self.assertEqual(arrow_res["span_binding"]["line"], 1)

        rs_file = self.tmp_dir / "lib.rs"
        rs_file.write_text("pub fn gate(v: i32) -> i32 {\n    v + 1\n}\n", encoding="utf-8")
        rs_orig = archify_registry.extract_symbol_ast_hash(rs_file, "gate")
        rs_file.write_text(
            "\n" * 15 + "// header\npub fn gate(v: i32) -> i32 {\n    /* block */\n    v + 1 // tail\n}\n",
            encoding="utf-8",
        )
        rs_shifted = archify_registry.extract_symbol_ast_hash(rs_file, "gate")
        self.assertEqual(rs_shifted["ast_symbol_sha256"], rs_orig["ast_symbol_sha256"])
        self.assertEqual(rs_shifted["span_binding"]["line"], 17)

    def test_python_ast_fallback_and_file_fallback(self) -> None:
        import archify_registry

        py_file = self.tmp_dir / "mod.py"
        py_file.write_text("def alpha(a):\n    return a + 10\n", encoding="utf-8")

        with mock.patch.dict(sys.modules, {"tree_sitter": None, "tree_sitter_python": None}):
            res1 = archify_registry.extract_symbol_ast_hash(py_file, "alpha")
            self.assertEqual(res1["hash_mode"], "python_ast")
            self.assertEqual(res1["span_binding"]["line"], 1)

            py_file.write_text(
                "\n" * 5 + '# shifted\ndef alpha(a):\n    """Doc."""\n    return a + 10\n',
                encoding="utf-8",
            )
            res2 = archify_registry.extract_symbol_ast_hash(py_file, "alpha")
            self.assertEqual(res2["hash_mode"], "python_ast")
            self.assertEqual(res2["ast_symbol_sha256"], res1["ast_symbol_sha256"])
            self.assertEqual(res2["span_binding"]["line"], 7)

        missing_sym = archify_registry.extract_symbol_ast_hash(py_file, "nonexistent_fn")
        self.assertEqual(missing_sym["hash_mode"], "file_fallback")
        self.assertRegex(missing_sym["ast_symbol_sha256"], r"^[a-f0-9]{64}$")

        txt_file = self.tmp_dir / "notes.txt"
        txt_file.write_text("plain text\nline 2\n", encoding="utf-8")
        other_ext = archify_registry.extract_symbol_ast_hash(txt_file, "alpha")
        self.assertEqual(other_ext["hash_mode"], "file_fallback")

        with self.assertRaises(FileNotFoundError):
            archify_registry.extract_symbol_ast_hash(self.tmp_dir / "missing.py", "alpha")


class TestArchifyRegistryValidationAndCycles(unittest.TestCase):
    """Tests for Logic Node validation and DFS cycle detection."""

    def test_validate_logic_node_accepts_valid_and_rejects_invalid(self) -> None:
        import archify_registry

        valid = _make_node(
            "gate-root",
            slice_id="slice-gate-root",
            steps=[
                {"step_id": "s1", "label": "Check command", "col": 0, "lane": "main", "target_node_id": "gate-sub"},
                {"step_id": "s2", "label": "Allow or deny", "col": 1, "lane": "error", "target_node_id": None},
            ],
            edges=[{"from": "s1", "to": "s2", "condition": "evaluated"}],
        )
        self.assertEqual(archify_registry.validate_logic_node(valid)["node_id"], "gate-root")

        bad_path = _make_node("bad-path", path="../outside/evil.py")
        with self.assertRaises(ValueError):
            archify_registry.validate_logic_node(bad_path)

        bad_depth = _make_node("bad-depth", depth=0)
        with self.assertRaises(ValueError):
            archify_registry.validate_logic_node(bad_depth)

        bad_range = _make_node("bad-range", line=10, end_line=4)
        with self.assertRaises(ValueError):
            archify_registry.validate_logic_node(bad_range)

        bad_hash = _make_node("bad-hash", ast_hash="not-a-sha256")
        with self.assertRaises(ValueError):
            archify_registry.validate_logic_node(bad_hash)

    def test_detect_cycles_catches_cycle_and_allows_dag_reuse(self) -> None:
        import archify_registry

        node_a = _make_node(
            "node-a",
            depth=1,
            slice_id="slice-a",
            steps=[
                {"step_id": "a1", "label": "Go B", "col": 0, "lane": "main", "target_node_id": "node-b"},
            ],
        )
        node_b = _make_node(
            "node-b",
            depth=2,
            slice_id="slice-b",
            steps=[
                {"step_id": "b1", "label": "Back to A", "col": 0, "lane": "error", "target_node_id": "node-a"},
            ],
        )
        cycles = archify_registry.detect_cycles({"node-a": node_a, "node-b": node_b}, "node-a", max_depth=6)
        self.assertEqual(len(cycles), 1)
        self.assertEqual(cycles[0]["from_node"], "node-b")
        self.assertEqual(cycles[0]["to_node"], "node-a")
        self.assertEqual(cycles[0]["handling"], "anchor-back-to-breadcrumb")

        shared = _make_node("shared-leaf", depth=3, reused_by=["branch-1", "branch-2"])
        b1 = _make_node(
            "branch-1",
            depth=2,
            slice_id="slice-b1",
            steps=[{"step_id": "s1", "label": "Use shared", "col": 0, "lane": "main", "target_node_id": "shared-leaf"}],
        )
        b2 = _make_node(
            "branch-2",
            depth=2,
            slice_id="slice-b2",
            steps=[{"step_id": "s2", "label": "Also use shared", "col": 0, "lane": "main", "target_node_id": "shared-leaf"}],
        )
        root = _make_node(
            "dag-root",
            depth=1,
            slice_id="slice-dag",
            steps=[
                {"step_id": "r1", "label": "B1", "col": 0, "lane": "main", "target_node_id": "branch-1"},
                {"step_id": "r2", "label": "B2", "col": 1, "lane": "branch", "target_node_id": "branch-2"},
            ],
            edges=[{"from": "r1", "to": "r2", "condition": "parallel"}],
        )
        dag_cycles = archify_registry.detect_cycles(
            {"dag-root": root, "branch-1": b1, "branch-2": b2, "shared-leaf": shared},
            "dag-root",
            max_depth=6,
        )
        self.assertEqual(dag_cycles, [])

        anchor_node = _make_node(
            "anchor-leaf",
            depth=3,
            slice_id="slice-anchor",
            steps=[
                {
                    "step_id": "x1",
                    "label": "Replay -> Login",
                    "col": 0,
                    "lane": "error",
                    "target_node_id": None,
                    "cycle_back_to": "dag-root",
                },
            ],
        )
        anchored = archify_registry.detect_cycles(
            {"dag-root": root, "branch-1": b1, "branch-2": b2, "shared-leaf": anchor_node},
            "dag-root",
            max_depth=2,
        )
        self.assertEqual(anchored, [])
        anchored_deep = archify_registry.detect_cycles(
            {"dag-root": root, "branch-1": b1, "branch-2": b2, "shared-leaf": anchor_node},
            "dag-root",
            max_depth=6,
        )
        self.assertEqual(len(anchored_deep), 1)
        self.assertEqual(anchored_deep[0]["to_node"], "dag-root")
        self.assertEqual(anchored_deep[0]["via"], "cycle_back_to")


class TestArchifyRegistryDirtySetAndSync(unittest.TestCase):
    """Tests for compute_dirty_set, span_binding relink, and planned isolation."""

    def setUp(self) -> None:
        self.project_root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.project_root, True)
        (self.project_root / "src").mkdir()
        self.src_py = self.project_root / "src" / "app.py"
        self.src_py.write_text(
            "def compute(x):\n    return x + 1\n\ndef other():\n    return 99\n",
            encoding="utf-8",
        )
        self.registry_dir = self.project_root / "docs" / "tdq" / "models" / "registry"
        (self.registry_dir / "nodes").mkdir(parents=True)

        self.node_compute = _make_node(
            "node-compute",
            path="src/app.py",
            symbol_ref="src/app.py::compute",
            line=1,
            end_line=2,
            depth=1,
            slice_id="slice-compute",
            steps=[
                {"step_id": "c1", "label": "Compute", "col": 0, "lane": "main", "target_node_id": "node-other"},
            ],
        )
        self.node_other = _make_node(
            "node-other",
            path="src/app.py",
            symbol_ref="src/app.py::other",
            line=4,
            end_line=5,
            depth=2,
            slice_id="slice-other",
            steps=[
                {"step_id": "o1", "label": "Other", "col": 0, "lane": "main", "target_node_id": None},
            ],
        )
        (self.registry_dir / "nodes" / "node-compute.json").write_text(
            json.dumps(self.node_compute, indent=2), encoding="utf-8"
        )
        (self.registry_dir / "nodes" / "node-other.json").write_text(
            json.dumps(self.node_other, indent=2), encoding="utf-8"
        )

    def test_sync_dirty_relink_and_ast_change(self) -> None:
        import archify_registry

        synced = archify_registry.sync_registry_index(self.registry_dir, self.project_root)
        self.assertEqual(synced["node_count"], 2)
        self.assertTrue((self.registry_dir / "index.json").is_file())

        clean_res = archify_registry.compute_dirty_set(self.registry_dir, self.project_root)
        self.assertEqual(clean_res["dirty_nodes"], [])
        self.assertEqual(clean_res["dirty_slices"], [])
        self.assertEqual(clean_res["span_shifted_nodes"], [])

        # Shift compute down 15 lines and add comments -> 0 dirty, span relinked
        self.src_py.write_text(
            "\n" * 15
            + "# New header comment\ndef compute(x):\n"
            + '    """Docstring."""\n'
            + "    return x + 1\n\ndef other():\n    return 99\n",
            encoding="utf-8",
        )
        shifted_res = archify_registry.compute_dirty_set(self.registry_dir, self.project_root)
        self.assertEqual(shifted_res["dirty_nodes"], [])
        self.assertEqual(shifted_res["dirty_slices"], [])
        self.assertEqual(set(shifted_res["span_shifted_nodes"]), {"node-compute", "node-other"})

        reloaded_node = json.loads((self.registry_dir / "nodes" / "node-compute.json").read_text(encoding="utf-8"))
        self.assertEqual(reloaded_node["fingerprint"]["span_binding"]["line"], 17)
        self.assertEqual(reloaded_node["fingerprint"]["cache_status"], "span_shifted_only")

        # Mutate only `compute` body -> only `node-compute` / `slice-compute` becomes dirty
        self.src_py.write_text(
            "\n" * 15
            + "# New header comment\ndef compute(x):\n"
            + '    """Docstring."""\n'
            + "    return x + 42\n\ndef other():\n    return 99\n",
            encoding="utf-8",
        )
        dirty_res = archify_registry.compute_dirty_set(self.registry_dir, self.project_root)
        self.assertEqual(dirty_res["dirty_nodes"], ["node-compute"])
        self.assertEqual(dirty_res["dirty_slices"], ["slice-compute"])
        self.assertIn("node-other", dirty_res["clean_nodes"])

    def test_sync_registry_index_rejects_planned_unless_explicit(self) -> None:
        import archify_registry

        planned = _make_node(
            "planned-feature",
            path="docs/planned/feature.py",
            symbol_ref="planned:feature.run",
            evidence_kind="planned",
        )
        (self.registry_dir / "nodes" / "planned-feature.json").write_text(
            json.dumps(planned, indent=2), encoding="utf-8"
        )
        with self.assertRaises(ValueError) as ctx:
            archify_registry.sync_registry_index(self.registry_dir, self.project_root, include_planned=False)
        self.assertIn("planned-feature", str(ctx.exception))

        res_ok = archify_registry.sync_registry_index(self.registry_dir, self.project_root, include_planned=True)
        self.assertEqual(res_ok["node_count"], 3)

    def test_tdq_log_toggle(self) -> None:
        import archify_registry

        buf_on = io.StringIO()
        with mock.patch.dict(os.environ, {"TDQ_LOG": "1"}), contextlib.redirect_stderr(buf_on):
            archify_registry.check_tree_sitter_support()
        self.assertRegex(buf_on.getvalue(), r"\[\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\] archify_registry:")

        buf_off = io.StringIO()
        with mock.patch.dict(os.environ, {"TDQ_LOG": "0"}), contextlib.redirect_stderr(buf_off):
            archify_registry.check_tree_sitter_support()
        self.assertEqual(buf_off.getvalue(), "")

        self.src_py.unlink()
        missing_res = archify_registry.compute_dirty_set(self.registry_dir, self.project_root)
        self.assertEqual(set(missing_res["dirty_nodes"]), {"node-compute", "node-other"})
        self.assertEqual(missing_res["node_statuses"]["node-compute"]["reason"], "missing_or_unsafe_source")


if __name__ == "__main__":
    unittest.main()
