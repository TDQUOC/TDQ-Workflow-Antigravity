"""Behavioral tests for Vietnamese Archify HTML chrome localization (M4)."""
import argparse
import base64
import gzip
import json
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from helper import ROOT  # noqa: F401 — ensures scripts/ is on sys.path
import tdq_archify
from archify_delivery import FinalizeResult

SAMPLE_WORDS = {
    "answer": "Answer",
    "answerMark": "A",
    "scope": "Applies to",
    "sources": "Sources",
    "print": "Print / PDF",
    "image": "Long image",
    "imageHints": ["Sharpest", "Smallest", "Opens anywhere"],
    "export": "Export",
    "style": "Style",
    "styles": {"clean": "Clean", "editorial": "Editorial", "product": "Product", "swiss": "Swiss"},
    "auto": "System",
    "light": "Light",
    "dark": "Dark",
    "typical": "Typical value",
    "explore": "Open interactive view",
    "exploreTitle": "Zoom, find nodes, trace paths, upstream and downstream, export images or motion",
    "close": "Close",
    "loading": "Opening diagram…",
    "graph": "Diagram structure",
    "changes": "Structure changes",
    "added": "Added",
    "removed": "Removed",
    "modified": "Modified",
    "copy": "Copy",
    "copied": "Copied",
    "walk": "Step through",
    "walkMessages": "Play messages",
    "walkFlow": "Walk the flow",
    "prev": "Back",
    "next": "Next",
    "end": "Done",
    "ask": "Ask",
    "askQuote": "Ask about this",
    "askPlaceholder": "What is unclear, or what should this part cover?",
    "askCopy": "Copy question",
    "askCopied": "Copied. Paste it to your agent.",
    "askCancel": "Cancel",
    "askChips": [
        "I do not follow this part",
        "Go deeper",
        "Give an example",
        "What is this based on?",
    ],
    "askPage": "Page",
    "askFile": "File",
    "askWhere": "Where",
    "askQuoteLabel": "Quote",
    "askQuestion": "Question",
    "askNote": "Copies the page, the panel and its ID, so your agent can revise just this part.",
    "askPatch": "Revise only this panel with Archify panel replacement (patch explainer), keeping its ID.",
    "tagline": "Turn anything you want to understand, plan, or share into an interactive visual.",
    "facts": {},
}

SAMPLE_HTML = (
    '<!doctype html>\n<html lang="en" data-style="clean" data-archify-artifact="explainer">'
    "<head><title>Báo cáo · Archify</title></head><body>"
    '<a class="skip-link" href="#board">Skip to content</a>'
    '<div class="tools interactive"><div class="theme-controls" role="group" aria-label="Theme">'
    '<button type="button" data-theme-choice="auto" aria-pressed="true">System</button>'
    '<button type="button" data-theme-choice="light" aria-pressed="false">Light</button>'
    '<button type="button" data-theme-choice="dark" aria-pressed="false">Dark</button>'
    '</div><div class="tool-menu style-menu">'
    '<button type="button" class="tool-button" data-style-toggle aria-label="Style">'
    '<span data-style-label>Clean</span></button>'
    '<div class="menu-options style-options" role="menu" aria-label="Style" hidden>'
    '<button data-style-choice="clean"><span>Clean</span></button>'
    '<button data-style-choice="editorial"><span>Editorial</span></button>'
    '<button data-style-choice="product"><span>Product</span></button>'
    '<button data-style-choice="swiss"><span>Swiss</span></button>'
    '</div></div><div class="tool-menu export-menu">'
    '<button type="button" class="tool-button" data-export-toggle><span>Export</span></button>'
    '<div class="menu-options" role="menu" aria-label="Export" hidden>'
    '<p class="menu-label" role="presentation">Long image</p>'
    '<button data-export-image="png" aria-label="Long image PNG"><span>PNG</span><small>Sharpest</small></button>'
    '<button data-export-image="webp" aria-label="Long image WebP"><span>WebP</span><small>Smallest</small></button>'
    '<button data-export-image="jpeg" aria-label="Long image JPG"><span>JPG</span><small>Opens anywhere</small></button>'
    '<button data-print><span>Print / PDF</span></button></div></div></div>'
    '<section id="answer"><header class="panel-head">'
    '<span class="panel-id answer-id" aria-hidden="true">A</span><h2>Answer</h2></header>'
    '<p class="answer-scope"><span class="scope-label">Applies to</span><span>doc</span></p></section>'
    '<figure class="diagram"><button class="tool-button explore-button" '
    'title="Zoom, find nodes, trace paths, upstream and downstream, export images or motion">'
    '<span>Open interactive view</span></button></figure>'
    '<details class="diagram-semantics" open><summary>Diagram structure</summary></details>'
    '<dl class="changes"><dt>Structure changes</dt>'
    '<dd><span class="chip added">Added</span></dd>'
    '<dd><span class="chip removed">Removed</span></dd>'
    '<dd><span class="chip modified">Modified</span></dd></dl>'
    '<button class="text-button interactive" type="button" data-copy>Copy</button>'
    '<span class="typical">Typical value</span>'
    '<span class="assessment good"><b>Favorable</b></span>'
    '<span class="assessment caution"><b>Tradeoff</b></span>'
    '<span class="assessment bad"><b>Unfavorable</b></span>'
    '<table class="diff-code" aria-label="Code changes"><thead><tr>'
    '<th scope="col">Old</th><th scope="col">New</th><th scope="col">Change</th>'
    "</tr></thead></table>"
    '<section class="typical-footnotes"><h2>Typical value notes</h2></section>'
    '<section class="sources"><h2>Sources</h2></section>'
    '<span class="colophon-tagline">Turn anything you want to understand, plan, or share into an interactive visual.</span>'
    '<p class="colophon-facts"><span>3 panels</span><span>2 diagrams validated</span>'
    "<span>4 sources</span><span>code pinned to abc1234</span></p>"
    '<dialog id="diagram-dialog"><button data-close-diagram><span>Close</span></button>'
    '<p class="dialog-loading" role="status">Opening diagram…</p></dialog>'
    '<script type="application/json" id="explainer-reader-words">'
    f"{json.dumps(SAMPLE_WORDS)}"
    "</script></body></html>"
)


class ArchifyVietnameseTest(unittest.TestCase):
    def test_read_doc_lang_defaults_and_reads_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(tdq_archify._read_doc_lang(root), "vi")
            state_dir = root / "docs" / "tdq"
            state_dir.mkdir(parents=True)
            (state_dir / "state.json").write_text('{"doc_lang": "en"}', encoding="utf-8")
            self.assertEqual(tdq_archify._read_doc_lang(root), "en")
            (state_dir / "state.json").write_text("{corrupt", encoding="utf-8")
            self.assertEqual(tdq_archify._read_doc_lang(root), "vi")

    def test_ensure_explainer_locale_candidate_injects_without_mutating_original(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            md_no_meta = root / "bao-cao.archify.md"
            original_text = "# Báo cáo {#bao-cao}\n\nTóm tắt kết quả.\n"
            md_no_meta.write_text(original_text, encoding="utf-8")

            effective, temp_cand = tdq_archify._ensure_explainer_locale_candidate(md_no_meta, root)
            try:
                self.assertIsNotNone(temp_cand)
                self.assertNotEqual(effective, md_no_meta)
                self.assertIn("@meta locale=en", effective.read_text(encoding="utf-8"))
                self.assertEqual(md_no_meta.read_text(encoding="utf-8"), original_text)
            finally:
                if temp_cand and temp_cand.exists():
                    temp_cand.unlink()

            md_with_meta = root / "with-meta.archify.md"
            md_with_meta.write_text("# Tiêu đề {#t}\n\n@meta locale=en\n\nNội dung.\n", encoding="utf-8")
            eff2, tmp2 = tdq_archify._ensure_explainer_locale_candidate(md_with_meta, root)
            self.assertIsNone(tmp2)
            self.assertEqual(eff2, md_with_meta)

    def test_localize_explainer_html_vi_chrome_json_and_idempotency(self):
        out = tdq_archify._localize_explainer_html_vi(SAMPLE_HTML)
        self.assertIn('<html lang="vi"', out)
        self.assertNotIn("zh-CN", out)
        self.assertNotIn("结论", out)
        self.assertNotIn("系统", out)
        for vi_label in (
            "Chuyển tới nội dung",
            'aria-label="Chế độ màu"',
            ">Hệ thống</button>",
            ">Sáng</button>",
            ">Tối</button>",
            'aria-label="Giao diện"',
            ">Gọn sạch<",
            ">Xuất tệp</span>",
            ">Ảnh dài</p>",
            ">Nét nhất</small>",
            ">In / PDF</span>",
            "<h2>Tóm tắt</h2>",
            ">Phạm vi áp dụng</span>",
            ">Mở sơ đồ tương tác</span>",
            "<summary>Cấu trúc sơ đồ</summary>",
            "<dt>Thay đổi cấu trúc</dt>",
            ">Sao chép</button>",
            ">Giá trị điển hình</span>",
            "<h2>Ghi chú giá trị điển hình</h2>",
            ">Cũ</th>",
            ">Mới</th>",
            ">Thay đổi</th>",
            "<h2>Nguồn đối chiếu</h2>",
            "<span>3 bảng</span>",
            "<span>2 sơ đồ đã kiểm chuẩn</span>",
            "<span>4 nguồn</span>",
            "<span>mã cố định ở abc1234</span>",
            ">Đóng</span>",
            "Đang mở sơ đồ…",
        ):
            self.assertIn(vi_label, out)

        match = re.search(
            r'<script type="application/json" id="explainer-reader-words">(.*?)</script>',
            out,
            re.S,
        )
        self.assertIsNotNone(match)
        parsed = json.loads(match.group(1))
        self.assertEqual(parsed["answer"], "Tóm tắt")
        self.assertEqual(parsed["sources"], "Nguồn đối chiếu")
        self.assertEqual(parsed["export"], "Xuất tệp")
        self.assertEqual(parsed["auto"], "Hệ thống")
        self.assertEqual(parsed["explore"], "Mở sơ đồ tương tác")
        self.assertEqual(parsed["close"], "Đóng")
        self.assertEqual(parsed["copied"], "Đã sao chép")
        self.assertEqual(parsed["styles"]["clean"], "Gọn sạch")
        self.assertEqual(tdq_archify._localize_explainer_html_vi(out), out)

    def test_build_master_explainer_sets_locale_without_invalid_meta_keys(self):
        model = {
            "title": "Kiến trúc TDQ",
            "evidence_kind": "working-tree",
            "views": [{"id": "ov", "type": "architecture", "summary": "Tổng quan", "candidate": "ov.json"}],
            "master": {"overview": "ov", "flows": []},
        }
        res_vi = tdq_archify._build_master_explainer(model, "showcase", doc_lang="vi")
        self.assertEqual(res_vi["meta"]["locale"], "vi")
        self.assertNotIn("translations", res_vi["meta"])
        res_default = tdq_archify._build_master_explainer(model, "showcase")
        self.assertEqual(res_default["meta"]["locale"], "en")

    def test_handle_render_localizes_before_manifest_and_preserves_current_verify(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "docs" / "tdq" / "artifacts" / "demo").mkdir(parents=True)
            (root / "docs" / "tdq" / "reports").mkdir(parents=True)
            (root / "docs" / "tdq" / "state.json").write_text('{"doc_lang": "vi"}', encoding="utf-8")

            doc_path = root / "docs" / "tdq" / "reports" / "2026-11-21-1900-demo.md"
            doc_path.write_text("# Báo cáo\n\nNội dung.\n", encoding="utf-8")

            cand_path = root / "docs" / "tdq" / "artifacts" / "demo" / "bao-cao.archify.md"
            cand_raw = "# Báo cáo {#bao-cao}\n\nTóm tắt thử nghiệm.\n"
            cand_path.write_text(cand_raw, encoding="utf-8")
            out_path = root / "docs" / "tdq" / "reports" / "2026-11-21-1900-demo.html"

            seen_candidate_texts = []

            def fake_run_finalize(diagram_type, candidate_path, output_path, quality, repo_root):
                seen_candidate_texts.append(Path(candidate_path).read_text(encoding="utf-8"))
                Path(output_path).write_text(SAMPLE_HTML, encoding="utf-8")
                return FinalizeResult(status=True, receipt={"ok": True, "status": "pass"})

            args = argparse.Namespace(
                type="explainer",
                candidate=str(cand_path),
                out=str(out_path),
                quality="showcase",
                repo_root=str(root),
                document=str(doc_path),
                request="2026-11-21-1900-demo",
                lane="full",
                evidence_kind="working-tree",
            )
            with mock.patch.object(tdq_archify, "run_finalize", side_effect=fake_run_finalize):
                rc = tdq_archify.handle_render(args)

            self.assertEqual(rc, 0)
            self.assertTrue(seen_candidate_texts and "@meta locale=en" in seen_candidate_texts[0])
            self.assertEqual(cand_path.read_text(encoding="utf-8"), cand_raw)
            leftovers = [p for p in cand_path.parent.glob(".tmp.*")]
            self.assertEqual(leftovers, [])
            rendered = out_path.read_text(encoding="utf-8")
            self.assertIn('<html lang="vi"', rendered)
            self.assertIn("<h2>Tóm tắt</h2>", rendered)
            ver = tdq_archify.verify_document_and_manifest(
                document=doc_path,
                manifest=out_path.with_suffix(".manifest.json"),
                project=root,
            )
            self.assertEqual(ver["status"], "current", ver.get("reasons"))
            self.assertTrue(ver["binding"]["valid"])

    def test_handle_render_preserves_english_when_doc_lang_is_en(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "docs" / "tdq" / "artifacts" / "demo").mkdir(parents=True)
            (root / "docs" / "tdq" / "reports").mkdir(parents=True)
            (root / "docs" / "tdq" / "state.json").write_text('{"doc_lang": "en"}', encoding="utf-8")

            doc_path = root / "docs" / "tdq" / "reports" / "2026-11-21-1900-en.md"
            doc_path.write_text("# Report\n\nBody.\n", encoding="utf-8")
            cand_path = root / "docs" / "tdq" / "artifacts" / "demo" / "en.archify.md"
            cand_path.write_text("# Report {#rep}\n\n@meta locale=en\n\nSummary.\n", encoding="utf-8")
            out_path = root / "docs" / "tdq" / "reports" / "2026-11-21-1900-en.html"

            def fake_run_finalize(diagram_type, candidate_path, output_path, quality, repo_root):
                Path(output_path).write_text(SAMPLE_HTML, encoding="utf-8")
                return FinalizeResult(status=True, receipt={"ok": True, "status": "pass"})

            args = argparse.Namespace(
                type="explainer",
                candidate=str(cand_path),
                out=str(out_path),
                quality="showcase",
                repo_root=str(root),
                document=str(doc_path),
                request="2026-11-21-1900-en",
                lane="full",
                evidence_kind="working-tree",
            )
            with mock.patch.object(tdq_archify, "run_finalize", side_effect=fake_run_finalize):
                rc = tdq_archify.handle_render(args)

            self.assertEqual(rc, 0)
            rendered = out_path.read_text(encoding="utf-8")
            self.assertIn('<html lang="en"', rendered)
            self.assertIn("<h2>Answer</h2>", rendered)
            self.assertNotIn("<h2>Tóm tắt</h2>", rendered)

    def test_localize_explainer_html_vi_replaces_chinese_branch_in_svg_json_and_gzip(self):
        inner_svg = (
            '<svg><text>02 / 分支 1</text>'
            '<g data-node-context="分支 2"><title>Step · 分支 1</title></g></svg>'
        )
        gz = base64.b64encode(gzip.compress(inner_svg.encode("utf-8"))).decode("ascii")
        bundle = {
            "preparedDiagrams": {
                "diagrams": {
                    "d1": {
                        "diagramType": "workflow",
                        "htmlGzip": gz,
                        "spec": {"lanes": [{"id": "lane-1", "label": "分支 1"}]},
                    }
                }
            }
        }
        fixture = (
            SAMPLE_HTML
            + '<div class="diagram-preview"><svg><text>02 / 分支 1</text>'
            + '<g data-node-context="分支 1"><title>Demo · 分支 1</title></g></svg></div>'
            + '<script type="application/json" id="archify-explainer-prepared">'
            + json.dumps(bundle, ensure_ascii=False)
            + "</script>"
        )
        out = tdq_archify._localize_explainer_html_vi(fixture)
        outside_scripts = re.sub(r"<script\b[^>]*>.*?</script>", "", out, flags=re.DOTALL)
        self.assertNotIn("分支", outside_scripts)
        self.assertIn("02 / Nhánh 1", outside_scripts)
        self.assertIn('data-node-context="Nhánh 1"', outside_scripts)
        self.assertIn("Demo · Nhánh 1", outside_scripts)

        match = re.search(
            r'<script\s+type="application/json"\s+id="archify-explainer-prepared">(.*?)</script>',
            out,
            re.DOTALL,
        )
        self.assertIsNotNone(match)
        parsed = json.loads(match.group(1))
        self.assertNotIn("分支", json.dumps(parsed, ensure_ascii=False))
        d1 = parsed["preparedDiagrams"]["diagrams"]["d1"]
        self.assertEqual(d1["spec"]["lanes"][0]["label"], "Nhánh 1")
        decompressed = gzip.decompress(base64.b64decode(d1["htmlGzip"])).decode("utf-8")
        self.assertNotIn("分支", decompressed)
        self.assertIn("02 / Nhánh 1", decompressed)
        self.assertIn('data-node-context="Nhánh 2"', decompressed)

    def test_render_real_multi_row_workflow_has_zero_chinese_in_svg_and_gzip(self):
        if not tdq_archify.check_environment().get("ready"):
            self.skipTest("Archify CLI/Node runtime unavailable")
        candidate_md = (
            "# Demo {#demo}\n\n"
            "Tóm tắt.\n\n"
            "## Luồng {#luong}\n\n"
            '@workflow id=wf-demo title="Quy trình nhiều hàng"\n'
            "| a | Lớp vào cũ | external |\n"
            "| b | Xử lý cũ | messagebus |\n"
            "| c | Mặt tiền mới | backend |\n"
            "| d | Lưu bằng chứng | security |\n"
            "| a > b | Mật độ dày |\n"
            "| c > d | Dễ đọc nhanh |\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "docs" / "tdq" / "artifacts" / "demo").mkdir(parents=True)
            (root / "docs" / "tdq" / "reports").mkdir(parents=True)
            (root / "docs" / "tdq" / "state.json").write_text('{"doc_lang": "vi"}', encoding="utf-8")
            doc_path = root / "docs" / "tdq" / "reports" / "2026-11-21-2250-wf.md"
            doc_path.write_text("# Demo\n\nNội dung.\n", encoding="utf-8")
            cand_path = root / "docs" / "tdq" / "artifacts" / "demo" / "wf.archify.md"
            cand_path.write_text(candidate_md, encoding="utf-8")
            out_path = root / "docs" / "tdq" / "reports" / "2026-11-21-2250-wf.html"

            args = argparse.Namespace(
                type="explainer",
                candidate=str(cand_path),
                out=str(out_path),
                quality="showcase",
                repo_root=str(root),
                document=str(doc_path),
                request="2026-11-21-2250-wf",
                lane="full",
                evidence_kind="working-tree",
            )
            rc = tdq_archify.handle_render(args)
            self.assertEqual(rc, 0)
            rendered = out_path.read_text(encoding="utf-8")
            self.assertIn('<html lang="vi"', rendered)
            outside_scripts = re.sub(r"<script\b[^>]*>.*?</script>", "", rendered, flags=re.DOTALL)
            self.assertIsNone(re.search(r"[\u4e00-\u9fff]", outside_scripts))

            words_m = re.search(
                r'<script\b[^>]*id="explainer-reader-words"[^>]*>(.*?)</script>',
                rendered,
                re.DOTALL,
            )
            self.assertIsNotNone(words_m)
            words = json.loads(words_m.group(1))
            self.assertEqual(words["answer"], "Tóm tắt")

            prep_m = re.search(
                r'<script\s+type="application/json"\s+id="archify-explainer-prepared">(.*?)</script>',
                rendered,
                re.DOTALL,
            )
            self.assertIsNotNone(prep_m)
            prep = json.loads(prep_m.group(1))
            self.assertNotIn("分支", json.dumps(prep, ensure_ascii=False))
            diagrams = (prep.get("preparedDiagrams") or {}).get("diagrams") or {}
            self.assertTrue(diagrams)
            for diag in diagrams.values():
                if isinstance(diag, dict) and isinstance(diag.get("htmlGzip"), str):
                    raw_child = gzip.decompress(base64.b64decode(diag["htmlGzip"])).decode("utf-8")
                    self.assertNotIn("分支", raw_child)


if __name__ == "__main__":
    unittest.main()
