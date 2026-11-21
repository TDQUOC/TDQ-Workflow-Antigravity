# QC — Triển khai kiến trúc mặc định trình bày 2 tầng

Ngày: 2026-11-21 · Plan: [2026-11-21-1819-trien-khai-trinh-bay-2-tang.md](../plan/2026-11-21-1819-trien-khai-trinh-bay-2-tang.md) (Vòng 2)
Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

> **Tóm tắt dễ hiểu:** Kiểm thử độc lập vòng hai xác nhận cả hai lỗi của vòng trước đã được vá dứt điểm. Trang web xuất trực tiếp đã chuyển toàn bộ nhãn nhánh từ chữ Trung sang tiếng Việt ở cả hình vẽ lẫn dữ liệu nén. Cổng kiểm tra ngôn ngữ cũng sạch dòng mới phát sinh trên mã nguồn và tài liệu hướng dẫn. Toàn bộ bộ kiểm thử nền, ngân sách từ khóa và gói cài đặt đều đạt chuẩn để chuyển sang bước viết báo cáo cuối.

## Dev Behavior QC Card

- **Auto Meta-Gate:** `PASS (3/3 checks, 0.08s)` khi chạy `--files scripts/tdq_archify.py docs/claude-md-mau.md docs/tdq/spec/2026-11-21-1819-trien-khai-trinh-bay-2-tang.md docs/tdq/plan/2026-11-21-1819-trien-khai-trinh-bay-2-tang.md CHANGELOG.md` và `i18n_check` = `0` lỗi trên `scripts/tdq_archify.py`; kiểm `i18n_check` delta so với `dev` trên từng tệp nguồn đã chạm ở `scripts/`, `hooks/scripts/`, `skills/` đạt `delta = -3 <= 0` (`428 → 425`, `0` dòng tiếng Việt mới thiếu `i18n-allow`). Ghi chú kỹ thuật: `tdq_meta_gate.py` mặc định (`FAIL 3/4, 0.37s`) và `--all` (`FAIL 3/4, 0.50s`) vẫn báo `946` / `1.053` dòng tiếng Việt cũ có sẵn từ nhánh `dev` cộng bản đóng gói `plugins/tdq-workflow-agy/` (`519` findings gồm `gate_guidance.json` không hỗ trợ comment `i18n-allow`, và `427` dòng tồn đọng sẵn trong `scripts/`/`hooks/`/`skills/`).
- **Luồng đổi:** Hoàn tất cả `2` task vá `QC1.1` và `QC1.2` trên nền `0.105.0`: `scripts/tdq_archify.py` dịch `_VI_BRANCH_RE` (`分支 (\d+)` → `Nhánh \1`) xuyên suốt SVG ngoài script, JSON `#archify-explainer-prepared` và từng payload `htmlGzip` sau `gzip.decompress`; đồng thời thêm `<!-- i18n-allow -->` cho `10` dòng mới ở `qc.md`, `report-template.md`, `user-facing-block.md`, khóa lại `token-budget.json` và biên dịch lại `plugins/tdq-workflow-agy/`.
- **Chạy thử thật (Before → After + Bằng chứng tươi):** `test_archify_vi.py` (`8/8` passed, gồm `2` test mới `SVG`/`htmlGzip`/`@workflow` nhiều hàng); probe render thật `truoc-sau.archify.md` ra thư mục tạm (`<html lang="vi"`, `0` `[\u4e00-\u9fff]` ngoài `<script>`, `0` `分支` trong `#archify-explainer-prepared` và `3/3` `htmlGzip`, `21` nhãn `Nhánh 1`, `answer="Tóm tắt"`); `64 passed, 398 subtests` cụm `Q5`; `94 passed, 50 subtests` cụm `Q1`–`Q3`; `225 passed, 149 subtests` vùng chạm `QC-F2`; `105 passed, 1 skipped, 142 subtests` cụm còn lại; `cargo test` (`29 passed`); `token_budget.py --kiem` (`67/67 <= 3.500` ở cả root lẫn plugin, max `3.481`); `agy plugin validate --strict --json` (`"findings": []`, `0.105.0`); `doc_lint.py` (`437` tệp `0` lỗi); `smoke-e2e --changed --workers auto` (`386/386, 162 subtests, 87.51s`); receipt `tron-bo` `3/3` mới nhất (`SHA256 09972ee4f4b46506cd057c28ba20a795cecd918f2fd395f1b17c2f9b446f34b0`, `4.700 passed, 36 skipped, 2.913 subtests, 306.14s <= 420s`, `bo_sot=0`).
- **Rủi ro còn lại:** Bản preview spec `2026-11-21-1819-trien-khai-trinh-bay-2-tang-preview.html` dựng trước khi làm `M4` sẽ được dựng lại ngay sau khi chuyển pha về `idle` để giữ toàn vẹn hash của spec; `tdq_meta_gate.py` chạy không cờ vẫn vướng chuỗi tiếng Việt có sẵn từ `dev` và `plugins/` do `_under_subdir` khớp nhánh con.

## Bảng tổng hợp `Q1`–`Q7` và `QC-F1`–`QC-F4`

| # | Hạng mục | Lệnh đã chạy | Kết quả | PASS/FAIL |
|---|---|---|---|---|
| Q1 | Quy chuẩn `user-facing-block*.md` và khuôn mẫu dưới `3.500` token | `pytest tests/test_user_facing_block.py ... -q` + `token_budget.py --kiem` + `doc_index.py --tat-ca --kiem` | `94 passed` cụm Q1–Q3; `67/67 <= 3.500` tok (max `3.481`, `user-facing-block=3.307`, `report-template=3.422`, `qc=3.344`); `doc_index` exit `0` | PASS |
| Q2 | Hook `[TDQ:PLAIN]` (`23` mã) ở `spec`/`plan`/`report` hai môi trường | `pytest tests/test_gate_guidance.py tests/test_hooks_dual_protocol.py tests/test_rust_dispatch_parity.py -q` + `cargo test` | Rust `29 passed`; Python cụm Q1–Q3 `94 passed, 50 subtests` | PASS |
| Q3 | Luật `R16` (`2026-11-21-1819`) và `doc_lint` | `pytest tests/test_doc_lint_r16.py -q` + `doc_lint.py` 437 tệp + `doc_lint.py --pair` | `20` test `R16` pass; `437` tệp `0` lỗi; `--pair` exit `0`; `r16_loi(spec/plan)` = `[]` | PASS |
| Q4 | `tdq_archify.py` Việt hóa UI HTML, `explainer-reader-words`, SVG & `htmlGzip` (`QC1.1`) | `pytest tests/test_archify_vi.py -v` + probe render thật `truoc-sau.archify.md` + `i18n_check.py scripts/tdq_archify.py` + AST | `8/8` pass; `<html lang="vi"`, `0` CJK ngoài `<script>`, `0` `分支` ở SVG/JSON/`3` `htmlGzip`, `answer="Tóm tắt"`; `i18n_check` exit `0`; hàm mới `<= 33` dòng | PASS |
| Q5 | `test_report_visual.py`, `token-budget`, plugin `0.105.0`, `i18n_check` delta (`QC1.2`) | `tdq_meta_gate.py --files ...` + kiểm `i18n_check` delta `dev` + `token_budget.py --kiem` + `agy plugin validate` + `pytest` `7` module | `--files` `PASS (3/3, 0.08s)`; nguồn `delta = -3 <= 0`; `67/67 <= 3.500` (root & plugin); `validate` `"findings": []`; `64 passed, 398 subtests` | PASS |
| Q6 | `doc_lint`, `smoke-e2e` và `tron-bo --workers auto` (`<= 420s`) | `doc_lint.py` 437 tệp + `smoke-e2e --changed --workers auto` + `tdq_test.py so` + kiểm receipt `result.json` | `doc_lint` `0` lỗi; `smoke-e2e` `386/386` (`87.51s`); `tron-bo` `3/3`, `bo_sot=0`, `4.700 passed, 36 skipped, 2.913 subtests, 306.14s` | PASS |
| Q7 | Báo cáo cuối `.md` + HTML tiếng Việt Tailscale `HTTP 200`, `0` console | `tdq_archify.py render/verify` + Tailscale GET + Chrome DevTools `navigate_page`/`take_snapshot`/`click`/`list_console_messages` | `verify` `status=current`, `valid=true`; `0` CJK ngoài `<script>`, `0` `分支` ở SVG/JSON/`3/3` `htmlGzip`; Tailscale `HTTP 200` (`1.238.152` byte); Chrome hiện `Tóm tắt`/`Hệ thống`/`Sáng`/`Tối`/`Giao diện`/`Xuất tệp`/`Mở sơ đồ tương tác`/`Đóng`/`Nhánh 1`, `0` lỗi console | PASS |
| QC-F1 | `Meta-Gate`, `smoke-e2e --changed`, `tron-bo` | `tdq_meta_gate.py --files ...` (`delta <= 0` so với `dev`) + `smoke-e2e --changed --workers auto` + `tdq_test.py so` | `--files` `PASS (3/3)`; nguồn `delta = -3 <= 0` (ghi chú `946` lỗi tồn đọng `dev` + `plugins/`); `smoke-e2e` PASS (`87.51s`); `tron-bo` PASS (`306.14s`) | PASS |
| QC-F2 | Hồi quy vùng chạm theo `Chạm:` | `pytest tests/test_doc_lint.py tests/test_tdq_archify.py tests/test_tdq_setup.py tests/test_prompt_context.py tests/test_muc_qc_qc_md.py tests/test_dev_qc_card_rules.py -q` | `225 passed, 149 subtests passed in 16.34s` | PASS |
| QC-F3 | Ràng buộc kiến trúc spec §5 & an toàn hệ thống | Kiểm import AST `hooks/`, `git rev-parse`, `~/.gemini/`, `soul.md`, `archify`, `git log` | `0` import chéo `hooks/`; `main` `91db3046...`; `~/.gemini` giữ `0.103.1`; `soul.md` & `archify` sạch; `0` trailer AI | PASS |
| QC-F4 | Clean Code (hàm/lỗi/stub), `TDQ_LOG=0/1`, `ruff` | Kiểm AST hàm chạm, `git diff dev` placeholder, `TDQ_LOG=0/1`, `py -3 -m ruff check` | `0` class mới, `0` TODO/stub, hàm mới `<= 33` dòng; `TDQ_LOG=0` tắt `stderr` (`doc_lint`, `tdq_meta_gate`, `tdq-dispatch.exe`); `ruff` `130` cảnh báo có sẵn ngoài dòng mới | PASS |

## Bằng chứng

### `Q4` (`QC1.1`) — Test `test_archify_vi.py`, probe render thật `truoc-sau.archify.md` và AST

```text
py -3 -X utf8 -m pytest tests/test_archify_vi.py -v
→ 8 passed in 2.50s (gồm test_localize_explainer_html_vi_replaces_chinese_branch_in_svg_json_and_gzip và test_render_real_multi_row_workflow_has_zero_chinese_in_svg_and_gzip)

Probe render thật docs/tdq/artifacts/2026-11-21-1819-trien-khai-trinh-bay-2-tang/truoc-sau.archify.md → %TEMP%/qc2_archify_*/truoc-sau.html (--repo-root .):
→ RENDER_RC=0 · has_lang_vi=True · cjk_outside_script_count=0 · nhanh_1_outside_script=21
→ prep_branch_count=0 · htmlGzip_items: 3 payload [(809054, br=0, cjk_out=0, Nhánh 1=True), (809368, 0, 0, True), (809404, 0, 0, True)]
→ reader_words_answer="Tóm tắt" · export="Xuất tệp"

py -3 -X utf8 scripts/i18n_check.py scripts/tdq_archify.py
→ 0 Vietnamese line(s) in 1 file(s), exit 0

AST hàm mới trong scripts/tdq_archify.py (mọi hàm mới <= 50 dòng):
→ _read_doc_lang=11, _ensure_explainer_locale_candidate=33, _localize_html_gzip_vi=11, _replace_branch_in_json=20, _localize_prepared_diagrams_vi=14, _localize_reader_words_json=16, _localize_explainer_html_vi=8, _run_localized_finalize=28
```

### `Q5` (`QC1.2`) — Delta `i18n_check` so với `dev`, `token_budget`, `agy plugin validate` và kiểm thử hành vi

```text
So sánh i18n_check.scan_file() hiện tại so với `git show dev:<file>` trên toàn bộ tệp nguồn đã chạm:
→ hooks/scripts/_common.py: 0→0 (+0) · hooks/scripts/prompt_context.py: 7→7 (+0)
→ scripts/doc_lint.py: 7→7 (+0) · scripts/tdq_archify.py: 0→0 (+0) · scripts/tdq_setup.py: 324→324 (+0, thay 3 dòng mẫu có sẵn)
→ skills/tdq-build/SKILL.md: 2→2 (+0) · archify-lifecycle.md: 2→2 (+0) · qc.md: 10→10 (+0) · report-template.md: 11→8 (-3)
→ user-facing-block-vi-du.md: 2→2 (+0) · user-facing-block.md: 7→7 (+0) · plan-template.md: 0→0 (+0) · archify-ba.md: 2→2 (+0) · spec-template.md: 56→56 (+0)
→ Tổng delta trên nguồn (scripts/ + hooks/ + skills/): dev=428 → cur=425 (delta = -3 <= 0, 0 dòng tiếng Việt mới thiếu i18n-allow).
→ (Ghi chú: `tools/patches/gate_guidance.json` thêm 4 trường tiếng Việt cho mã `"PLAIN"` theo định dạng JSON không hỗ trợ comment; `plugins/tdq-workflow-agy/` là bản build mang theo 519 dòng gồm `gate_guidance.json` 92 dòng và bản sao `scripts/`/`skills/` từ nguồn, nên `tdq_meta_gate.py` mặc định báo 946 dòng và `--all` báo 1.053 dòng trên chuỗi cũ từ `dev`.)

py -3 -X utf8 scripts/tdq_meta_gate.py --files scripts/tdq_archify.py docs/claude-md-mau.md docs/tdq/spec/2026-11-21-1819-trien-khai-trinh-bay-2-tang.md docs/tdq/plan/2026-11-21-1819-trien-khai-trinh-bay-2-tang.md CHANGELOG.md
→ Auto Meta-Gate: PASS (3/3 checks, 0.08s), exit 0

$env:TDQ_TOKENS_VENV='...\TDQ-Workflow\.venv-tokens\Scripts\python.exe'; py -3 -X utf8 scripts/token_budget.py --kiem
→ exit 0 (67/67 <= 3.500; cao nhất team-mode=3.481, plan-template=3.465, uu-tien-tim-kiem=3.439, report-template=3.422, spec-template=3.381, qc=3.344, user-facing-block=3.307, user-facing-block-vi-du=2.086)
py -3 -X utf8 plugins/tdq-workflow-agy/scripts/token_budget.py --kiem → exit 0

agy plugin validate plugins/tdq-workflow-agy --strict --json
→ "findings": [], "version": "0.105.0", exit 0 (khớp .claude-plugin/plugin.json, .codex-plugin/plugin.json, CHANGELOG.md)

py -3 -X utf8 scripts/doc_lint.py skills docs/claude-md-mau.md docs/tdq/spec docs/tdq/reports docs/tdq/plan/2026-11-21-1819-trien-khai-trinh-bay-2-tang.md docs/tdq/brief/2026-11-21-1819-trien-khai-trinh-bay-2-tang.md
→ [2026-11-21T23:01:59] doc_lint: done — 0 violation(s) total, exit 0 (437 files)

py -3 -X utf8 -m pytest tests/test_archify_vi.py tests/test_user_facing_block.py tests/test_report_visual.py tests/test_luat_skill.py tests/test_agy_plugin_validate.py tests/test_token_budget.py tests/test_docs_consistency.py -q
→ 64 passed, 398 subtests passed in 14.11s
```

### `Q1`–`Q3`, `Q6`, `QC-F2`–`QC-F4` — Kết quả kiểm chứng Vòng 2

```text
# Q1–Q3 (5 module cốt lõi) + phần còn lại của cụm 12 module + Rust:
py -3 -X utf8 -m pytest tests/test_user_facing_block.py tests/test_gate_guidance.py tests/test_hooks_dual_protocol.py tests/test_rust_dispatch_parity.py tests/test_doc_lint_r16.py -q
→ 94 passed, 50 subtests passed in 86.74s
py -3 -X utf8 -m pytest tests/test_auto_update_setup.py tests/test_claude_md_core.py tests/test_investigate_workflow.py tests/test_meta_gate.py -rs -q
→ 105 passed, 1 skipped (Windows symlink privilege ở test_investigate_workflow.py:335), 142 subtests passed in 28.80s
cargo test --manifest-path hooks/rust/tdq-dispatch/Cargo.toml
→ 29 passed (3 suites, 0.07s)

# QC-F2 (6 module vùng chạm):
py -3 -X utf8 -m pytest tests/test_doc_lint.py tests/test_tdq_archify.py tests/test_tdq_setup.py tests/test_prompt_context.py tests/test_muc_qc_qc_md.py tests/test_dev_qc_card_rules.py -q
→ 225 passed, 149 subtests passed in 16.34s

# Q6 — smoke-e2e mới & đối chiếu receipt tron-bo 3/3 (không chạy lại tron-bo):
py -3 -X utf8 scripts/tdq_test.py smoke-e2e --changed --workers auto
→ [TDQ:TEST] PASS — scope=smoke-e2e backend=pytest tests=386 skipped=0 in 87.51s (386 passed, 162 subtests passed; TDQ_RESULT sha256=adca14a8625128ee71046b3177b139d76ab7a47257c508b3f968f288b70f7f9d)

py -3 -X utf8 scripts/tdq_test.py so
→ full-suite runs: 3 of budget 3 · radius misses: 0 · radius statistics: partial or unavailable
Receipt: docs/tdq/cache/test-runs/b397f484b6a31ef6/bfc53d9a050f42bf88f667e8451aac77/result.json
→ SHA256: 09972ee4f4b46506cd057c28ba20a795cecd918f2fd395f1b17c2f9b446f34b0
→ status=PASS, exit_code=0, tests_run=4736, skipped=36 (4700 passed, 36 skipped, 2913 subtests passed), wall_seconds=305.99s (ledger seconds=306.14s <= 420s)
→ Thời gian tạo receipt (2026-11-21T22:59:18+07:00) nằm SAU toàn bộ lần sửa QC1.1/QC1.2 (22:49:56–22:52:57+07:00).

# QC-F3 & QC-F4 (an toàn hệ thống, log toggle, clean code):
→ ~/.gemini/config/plugins/tdq-workflow-agy/plugin.json = 0.103.1; main = 91db304635f142b457284d55accf82c28a813239; soul.md diff = 0; C:\Users\admin\Documents\archify sạch mã nguồn; 0 commit chứa trailer AI; 0 import chéo từ hooks/ sang scripts/tools/.
→ TDQ_LOG=0 tắt sạch stderr trên doc_lint.py, tdq_meta_gate.py, tdq-dispatch.exe; TDQ_LOG=1 in timestamp ISO-8601.
→ py -3 -m ruff check trên 4 tệp Python chạm báo 130 cảnh báo có sẵn ngoài phần mới (0 TODO/FIXME/stub trong git diff dev).
```

### `Q7` — Nghiệm thu Báo cáo cuối `.md`, Archify HTML tiếng Việt và Chrome DevTools thực tế

```text
py -3 -X utf8 scripts/doc_lint.py docs/tdq/reports/2026-11-21-1819-trien-khai-trinh-bay-2-tang.md
→ R16 → 0 finding(s); done — 0 violation(s) total, exit 0

py -3 -X utf8 scripts/tdq_archify.py render --type explainer --candidate docs/tdq/artifacts/2026-11-21-1819-trien-khai-trinh-bay-2-tang/bao-cao.archify.md --out docs/tdq/reports/2026-11-21-1819-trien-khai-trinh-bay-2-tang.html --document docs/tdq/reports/2026-11-21-1819-trien-khai-trinh-bay-2-tang.md --request 2026-11-21-1819-trien-khai-trinh-bay-2-tang --lane full --evidence-kind working-tree --repo-root .
py -3 -X utf8 scripts/tdq_archify.py verify --document docs/tdq/reports/2026-11-21-1819-trien-khai-trinh-bay-2-tang.md --manifest docs/tdq/reports/2026-11-21-1819-trien-khai-trinh-bay-2-tang.manifest.json --project .
→ gates validate/deliver/check = pass · status="current", binding.valid=true · html_lang_vi=True · bytes=1234682 · cjk_outside_script=0 · json_branch=0 · gz_hits={'wf-two-tier':(0,0), 'wf-plain-r16':(0,0), 'wf-archify-report':(0,0)} · reader_answer="Tóm tắt"

Tailscale Serve HTTPS check + Chrome DevTools (pageId=1):
→ URL: https://unity-pc-rtx3060.tail99896.ts.net/vlog/tdq-workflow-agy/reports/2026-11-21-1819-trien-khai-trinh-bay-2-tang.html → HTTP 200 (1238152 bytes, lang="vi")
→ take_snapshot (trang chính): banner tiếng Việt ("Hệ thống", "Sáng", "Tối", "Giao diện", "Xuất tệp"), "Tóm tắt", "Hỏi thêm", "▶ Đi theo luồng", "Mở sơ đồ tương tác", "3 bảng · 3 sơ đồ đã kiểm chuẩn"
→ click("1_7" Tối) + click("1_22" Mở sơ đồ tương tác) → take_snapshot (modal): button "Đóng Esc", iframe about:srcdoc hiện nút "Nhánh 1" sạch tiếng Việt, 0 chữ Trung
→ list_console_messages(types=["error","warn"]) → <no console messages found> (0 errors, 0 warnings)
```

## Lệch spec chờ duyệt

không có (`tdq_state.py lech list` → `0 item(s), 0 pending`)

## Kết luận

PASS toàn bộ `Q1`–`Q7` và `QC-F1`–`QC-F4` (Vòng 2). Báo cáo `2` tầng `.md` sạch `doc_lint` và trang Archify HTML tiếng Việt đạt `status=current`, Tailscale `HTTP 200` và `0` lỗi console qua kiểm thử Chrome DevTools thực tế.
