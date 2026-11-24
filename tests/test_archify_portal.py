"""Unit tests for scripts/archify_portal.py."""
from __future__ import annotations

import contextlib
import io
import json
import os
import re
import sys
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
    depth: int = 1,
    evidence_kind: str = "working-tree",
    slice_id: str | None = None,
    steps: list[dict] | None = None,
    edges: list[dict] | None = None,
    reused_by: list[str] | None = None,
    summary: str | None = None,
) -> dict:
    """Create a canonical Logic Node fixture for portal tests."""
    tier = "eager_l1_l2" if depth <= 2 else "lazy_l3_plus"
    node: dict = {
        "node_id": node_id,
        "title": f"Title {node_id}",
        "depth": depth,
        "node_kind": "flow_root" if depth == 1 else "decision_branch",
        "hydration_tier": tier,
        "evidence_kind": evidence_kind,
        "fingerprint": {
            "symbol_ref": f"src/app.py::{node_id}",
            "ast_symbol_sha256": "a" * 64 if evidence_kind != "planned" else None,
            "span_binding": {"path": "src/app.py", "line": 10, "end_line": 25},
            "render_slice_sha256": f"hash-{slice_id}" if slice_id else None,
            "cache_status": "planned_draft" if evidence_kind == "planned" else "clean",
            "hash_mode": "tree_sitter_ast",
        },
        "natural_explanation": {
            "summary": summary or f"Explains {node_id} responsibility clearly.",
            "what_goes_where": "Validates input payload and passes clean data downstream.",
            "why_it_exists": "Isolates decision logic for reuse and fast incremental caching.",
            "edge_cases": ["Empty payload fails closed"],
        },
        "io_contract": {
            "inputs": ["payload: dict"],
            "outputs": ["result: dict"],
            "side_effects": ["Writes ISO stderr log"],
        },
        "sources": [{"path": "src/app.py", "line": 10, "end_line": 25}],
        "reused_by": reused_by or ["flow-root"],
    }
    if slice_id and steps is not None:
        node["sub_flow"] = {"slice_id": slice_id, "max_cols": 4, "steps": steps, "edges": edges or []}
    return node


def _make_svg(slice_id: str, node_ids: list[str], pad_bytes: int = 0) -> str:
    """Build a native Archify-like SVG fragment with data-node-id groups and zero onclick."""
    groups = []
    for idx, nid in enumerate(node_ids):
        x = 24 + idx * 170
        groups.append(
            f'<g id="node-{nid}" data-node-id="{nid}" data-node-label="{nid}" '
            f'tabindex="0" role="button">'
            f'<rect x="{x}" y="30" width="140" height="56" rx="8" class="c-mask"/>'
            f'<rect x="{x}" y="30" width="140" height="56" rx="8" class="c-backend"/>'
            f'<text x="{x + 70}" y="62" class="t-primary" text-anchor="middle">{nid}</text>'
            f"</g>"
        )
    padding = f"<!-- {'p' * pad_bytes} -->" if pad_bytes > 0 else ""
    return (
        f'<svg viewBox="0 0 800 180" data-slice-id="{slice_id}" data-node-ui="">'
        f"{padding}{''.join(groups)}</svg>"
    )


def _add_branch(nodes: dict[str, dict], slices: dict[str, str], b_idx: int, pad_per_slice: int) -> None:
    """Populate one 4-level branch with a cycle back-edge on branch 0."""
    l2_id, l3_id, l4_id, l4_leaf = f"n2-{b_idx}", f"n3-{b_idx}", f"n4-{b_idx}", f"n4-leaf-{b_idx}"
    nodes[l2_id] = _make_node(
        l2_id, depth=2, slice_id=f"s-{l2_id}",
        steps=[{"step_id": "s1", "label": l3_id, "col": 0, "lane": "main", "target_node_id": l3_id}],
        reused_by=["flow-root", "flow-secondary"] if b_idx == 0 else ["flow-root"],
    )
    slices[f"s-{l2_id}"] = _make_svg(f"s-{l2_id}", [l3_id], pad_bytes=pad_per_slice)
    nodes[l3_id] = _make_node(
        l3_id, depth=3, evidence_kind="planned" if b_idx == 1 else "working-tree", slice_id=f"s-{l3_id}",
        steps=[
            {"step_id": "s1", "label": l4_id, "col": 0, "lane": "main", "target_node_id": l4_id},
            {"step_id": "s2", "label": l4_leaf, "col": 1, "lane": "branch", "target_node_id": l4_leaf},
        ],
        edges=[{"from": "s1", "to": "s2"}],
    )
    slices[f"s-{l3_id}"] = _make_svg(f"s-{l3_id}", [l4_id, l4_leaf], pad_bytes=pad_per_slice)
    cyc_steps = [
        {"step_id": "back", "label": "Retry root", "col": 0, "lane": "error", "target_node_id": "flow-root", "cycle_back_to": "flow-root"}
    ]
    nodes[l4_id] = _make_node(l4_id, depth=4, slice_id=f"s-{l4_id}" if b_idx == 0 else None, steps=cyc_steps if b_idx == 0 else None)
    if b_idx == 0:
        slices[f"s-{l4_id}"] = _make_svg(f"s-{l4_id}", ["flow-root"], pad_bytes=pad_per_slice)
    nodes[l4_leaf] = _make_node(l4_leaf, depth=4)


def _build_16_node_graph(pad_per_slice: int = 0) -> tuple[dict, dict[str, str], dict[str, dict]]:
    """Build a 16-node, 4-depth fixture with reuse and a cycle back-edge."""
    nodes: dict[str, dict] = {}
    slices: dict[str, str] = {}
    for b_idx in range(4):
        _add_branch(nodes, slices, b_idx, pad_per_slice)
    root_steps = [{"step_id": f"r{i}", "label": f"Branch {i}", "col": i, "lane": "main", "target_node_id": f"n2-{i}"} for i in range(4)]
    nodes["flow-root"] = _make_node("flow-root", depth=1, slice_id="s-root", steps=root_steps, edges=[{"from": "r0", "to": "r1"}])
    slices["s-root"] = _make_svg("s-root", [f"n2-{i}" for i in range(4)], pad_bytes=pad_per_slice)
    index_nodes = [
        {
            "node_id": nid, "title": n["title"], "depth": n["depth"], "node_kind": n["node_kind"],
            "hydration_tier": n["hydration_tier"], "evidence_kind": n["evidence_kind"],
            "symbol_ref": n["fingerprint"]["symbol_ref"], "span_binding": n["fingerprint"]["span_binding"],
            "sub_flow_slice_id": n.get("sub_flow", {}).get("slice_id"),
            "reused_by": n["reused_by"], "cache_status": n["fingerprint"]["cache_status"], "file_path": f"nodes/{nid}.json",
        }
        for nid, n in sorted(nodes.items())
    ]
    registry_index = {
        "schema_version": "1.0", "max_depth": 6, "root_flows": ["flow-root"], "node_count": len(nodes),
        "cycles_detected": [{"from_node": "n4-0", "to_node": "flow-root", "detected_at_depth": 4, "handling": "anchor-back-to-breadcrumb", "step_id": "back", "via": "cycle_back_to"}],
        "nodes": index_nodes,
    }
    return registry_index, slices, nodes


class TestArchifyPortalShell(unittest.TestCase):
    """Tests for build_portal_shell lazy/embedded generation and security."""

    def test_lazy_portal_size_under_300kb_with_15_plus_nodes_and_4_depths(self) -> None:
        import archify_portal

        index, slices, nodes = _build_16_node_graph(pad_per_slice=34_000)
        self.assertGreaterEqual(len(nodes), 15)
        self.assertGreater(sum(len(s.encode("utf-8")) for s in slices.values()), 300_000)

        html_out = archify_portal.build_portal_shell(index, slices, nodes, mode="lazy")
        size_bytes = len(html_out.encode("utf-8"))
        self.assertLess(size_bytes, 300_000)
        self.assertNotIn("s-n3-1", _extract_inline_slices_keys(html_out))

    def test_event_delegation_no_svg_onclick_and_lazy_fallbacks(self) -> None:
        import archify_portal

        index, slices, nodes = _build_16_node_graph()
        html_out = archify_portal.build_portal_shell(index, slices, nodes, mode="lazy")

        normalized = html_out.replace('"', "'")
        self.assertIn("closest('[data-node-id]')", normalized)
        self.assertIn('<script src="registry-bundle.js"></script>', html_out)
        self.assertIn("window.__TDQ_ARCHIFY_REGISTRY__", html_out)
        self.assertIn("fetch(", html_out)
        self.assertNotIn("onclick=", html_out.lower())
        for slice_svg in slices.values():
            self.assertNotIn("onclick=", slice_svg.lower())

    def test_xss_script_breakout_is_safely_escaped(self) -> None:
        import archify_portal

        payload = "</script><img src=x onerror=alert(1)>"
        index, slices, nodes = _build_16_node_graph()
        nodes["flow-root"]["title"] = f"Root {payload}"
        nodes["flow-root"]["natural_explanation"]["summary"] = f"Summary {payload}"
        nodes["flow-root"]["io_contract"]["inputs"] = [f"in:{payload}"]
        index["nodes"][0]["title"] = f"Root {payload}"

        for mode in ("lazy", "embedded"):
            with self.subTest(mode=mode):
                html_out = archify_portal.build_portal_shell(
                    index, slices, nodes, mode=mode, title=f"Title {payload}"
                )
                self.assertNotIn("<img src=x onerror=alert(1)>", html_out)
                scripts = re.findall(r"<script\b[^>]*>(.*?)</script>", html_out, flags=re.DOTALL)
                for block in scripts:
                    self.assertNotIn("</script>", block.lower())
                    self.assertNotIn("<img", block.lower())
                self.assertIn("textContent", html_out)

    def test_cycle_protection_and_badges_present(self) -> None:
        import archify_portal

        index, slices, nodes = _build_16_node_graph()
        html_out = archify_portal.build_portal_shell(index, slices, nodes, mode="embedded")
        self.assertIn("cycles_detected", html_out)
        self.assertIn("cycle_back_to", html_out)
        self.assertIn("reused_by", html_out)
        self.assertIn("evidence_kind", html_out)
        self.assertIn("planned", html_out)
        self.assertIn("working-tree", html_out)

    def test_invalid_mode_raises_value_error(self) -> None:
        import archify_portal

        index, slices, nodes = _build_16_node_graph()
        with self.assertRaises(ValueError):
            archify_portal.build_portal_shell(index, slices, nodes, mode="invalid")

    def test_doc_lang_switching_vi_and_en(self) -> None:
        import archify_portal

        index, slices, nodes = _build_16_node_graph()
        vi_html = archify_portal.build_portal_shell(index, slices, nodes, mode="lazy", doc_lang="vi")
        en_html = archify_portal.build_portal_shell(index, slices, nodes, mode="lazy", doc_lang="en")
        self.assertIn('<html lang="vi"', vi_html)
        self.assertIn('<html lang="en"', en_html)


class TestArchifyRegistryBundleAndStandalone(unittest.TestCase):
    """Tests for build_registry_bundle_js and render_drilldown_standalone."""

    def test_build_registry_bundle_js_roundtrip_and_escaping(self) -> None:
        import archify_portal

        index, slices, nodes = _build_16_node_graph()
        xss = "</script><script>alert(1)</script>"
        nodes["flow-root"]["natural_explanation"]["summary"] = xss

        js_text = archify_portal.build_registry_bundle_js(index, slices, nodes)
        self.assertTrue(js_text.startswith("window.__TDQ_ARCHIFY_REGISTRY__ = "))
        self.assertTrue(js_text.rstrip().endswith(";"))
        self.assertNotIn("</script>", js_text.lower())
        self.assertNotIn("<", js_text)

        raw_json = js_text[len("window.__TDQ_ARCHIFY_REGISTRY__ = "):].strip().rstrip(";")
        parsed = json.loads(raw_json)
        self.assertEqual(parsed["index"]["root_flows"], ["flow-root"])
        self.assertEqual(parsed["slices"]["s-root"], slices["s-root"])
        self.assertEqual(parsed["nodes"]["flow-root"]["natural_explanation"]["summary"], xss)

    def test_render_drilldown_standalone_self_contained_depth4_dict_and_list(self) -> None:
        import archify_portal

        index, slices, nodes = _build_16_node_graph()
        cand_dict = {
            "title": "Spec Preview Drilldown",
            "evidence_kind": "planned",
            "root_flows": ["flow-root"],
            "nodes": nodes,
        }
        cand_list = {
            "title": "Report Drilldown",
            "evidence_kind": "working-tree",
            "registry_index": index,
            "nodes": list(nodes.values()),
            "slices": slices,
        }
        for label, cand, sl in [("dict", cand_dict, slices), ("list", cand_list, None)]:
            with self.subTest(label=label):
                out = archify_portal.render_drilldown_standalone(cand, sl, doc_lang="en")
                self.assertNotIn("<script src=", out.lower())
                self.assertIn("window.__TDQ_ARCHIFY_REGISTRY__", out)
                self.assertIn("Spec Preview Drilldown" if label == "dict" else "Report Drilldown", out)
                self.assertIn("closest(", out)

    def test_render_drilldown_standalone_accepts_light_nodes_and_cycles(self) -> None:
        import archify_portal

        light_nodes = [
            {
                "node_id": "r1",
                "title": "Root",
                "depth": 1,
                "sub_flow": {
                    "slice_id": "sr1",
                    "max_cols": 2,
                    "steps": [{"step_id": "s1", "label": "Next", "col": 0, "target_node_id": "r2"}],
                    "edges": [],
                },
            },
            {
                "node_id": "r2",
                "title": "Child",
                "depth": 2,
                "sub_flow": {
                    "slice_id": "sr2",
                    "max_cols": 2,
                    "steps": [
                        {
                            "step_id": "s2",
                            "label": "Back",
                            "col": 0,
                            "target_node_id": "r1",
                            "cycle_back_to": "r1",
                        }
                    ],
                    "edges": [],
                },
            },
        ]
        out = archify_portal.render_drilldown_standalone({"nodes": light_nodes}, {})
        self.assertIn("cycles_detected", out)
        self.assertIn("r1", out)

    def test_render_drilldown_standalone_rejects_depth_above_4(self) -> None:
        import archify_portal

        _, slices, nodes = _build_16_node_graph()
        deep_node = _make_node("n5-deep", depth=5)
        nodes["n5-deep"] = deep_node
        with self.assertRaises(ValueError):
            archify_portal.render_drilldown_standalone({"nodes": nodes}, slices)

        _, slices_ok, nodes_ok = _build_16_node_graph()
        with self.assertRaises(ValueError):
            archify_portal.render_drilldown_standalone({"max_depth": 5, "nodes": nodes_ok}, slices_ok)

        # Graph path depth > 4 is rejected even if node.depth metadata says <= 4.
        chain_nodes = {
            f"c{i}": _make_node(
                f"c{i}",
                depth=min(i, 4),
                slice_id=f"sc{i}" if i < 5 else None,
                steps=[{"step_id": "s1", "label": f"c{i+1}", "col": 0, "lane": "main", "target_node_id": f"c{i+1}"}]
                if i < 5
                else None,
            )
            for i in range(1, 6)
        }
        with self.assertRaises(ValueError):
            archify_portal.render_drilldown_standalone({"nodes": chain_nodes}, {})

    def test_render_drilldown_standalone_rejects_unsafe_source_path(self) -> None:
        import archify_portal

        bad_node = _make_node("n1-bad", depth=1)
        bad_node["sources"] = [{"path": "../outside.py", "line": 1, "end_line": 2}]
        with self.assertRaises(ValueError):
            archify_portal.render_drilldown_standalone({"nodes": [bad_node]}, {})


class TestArchifyPortalLogging(unittest.TestCase):
    """Tests for default-on ISO stderr logging and TDQ_LOG=0 mute."""

    def test_tdq_log_toggle(self) -> None:
        import archify_portal

        index, slices, nodes = _build_16_node_graph()
        buf_on = io.StringIO()
        with mock.patch.dict(os.environ, {"TDQ_LOG": "1"}), contextlib.redirect_stderr(buf_on):
            archify_portal.build_portal_shell(index, slices, nodes, mode="lazy")
            archify_portal.build_registry_bundle_js(index, slices, nodes)
            archify_portal.render_drilldown_standalone({"nodes": nodes}, slices)
        err_on = buf_on.getvalue()
        self.assertRegex(err_on, r"\[\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\] archify_portal:")

        buf_off = io.StringIO()
        with mock.patch.dict(os.environ, {"TDQ_LOG": "0"}), contextlib.redirect_stderr(buf_off):
            archify_portal.build_portal_shell(index, slices, nodes, mode="lazy")
            archify_portal.build_registry_bundle_js(index, slices, nodes)
            archify_portal.render_drilldown_standalone({"nodes": nodes}, slices)
        self.assertEqual(buf_off.getvalue(), "")


def _extract_inline_slices_keys(html_text: str) -> set[str]:
    """Extract slice keys embedded inside the lazy bootstrap JSON script."""
    match = re.search(
        r'<script[^>]*id="tdq-portal-bootstrap"[^>]*>(.*?)</script>',
        html_text,
        flags=re.DOTALL,
    )
    if not match:
        return set()
    data = json.loads(match.group(1))
    return set((data.get("slices") or {}).keys())


if __name__ == "__main__":
    unittest.main()
