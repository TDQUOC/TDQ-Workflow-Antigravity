# BÁO CÁO — Triển khai kiến trúc mặc định trình bày 2 tầng cho TDQ-Workflow

Ngày: 2026-11-21 · Mã yêu cầu: 2026-11-21-1819-trien-khai-trinh-bay-2-tang
Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

> **Tóm tắt dễ hiểu:** Trước nâng cấp, phần mở đầu tài liệu và tin nhắn chat hay dồn nhiều ký hiệu kỹ thuật nên khó nắm nhanh. Ngoài ra, trang web HTML mặc định dễ rơi về chữ Trung khi thiếu khai báo ngôn ngữ. Sau nâng cấp, luồng làm việc tách rõ hai tầng trình bày, thêm nhắc nhở lúc viết và bật luật kiểm tự động. Trang web báo cáo cũng tự động Việt hóa toàn bộ giao diện lẫn nhãn sơ đồ. Toàn bộ kiểm thử nền, đóng gói bản phát hành mới và kiểm tra độc lập hai vòng đều đạt yêu cầu.

## 1. Trước request (trạng thái/flow)

Trước khi triển khai, bảng `Two-Tier Presentation` chưa đứng ở đầu quy chuẩn hiển thị và khuôn mẫu báo cáo vẫn đặt định dạng nén `1` dòng kèm dấu `·`. Báo cáo thực tế có thể mở đầu bằng mật độ lớn hơn `25` backtick mỗi `100` từ, làm người đọc mất nhịp khi xem nhanh. Ở tầng hook, danh sách `ALL_AGY_CODES` mới có `22` mã `[TDQ:*]` và không phát nhắc nhở trình bày gọn ở các pha viết `spec`, `plan`, `report`. Ở tầng lint, `doc_lint.py` bỏ qua kiểm tra mật độ Lớp 1 trên các thư mục đầu ra như `spec/` và `reports/`. Khi xuất Archify HTML, `tdq_archify.py` ép `locale: "en"` cho bản tổng hợp, còn nhánh vẽ đa hàng từ công cụ gốc tự chèn nhãn `分支 1` tiếng Trung vào SVG và dữ liệu nén.

## 2. Sau request (trạng thái/flow)

Hệ thống sau nâng cấp khóa chặt kiến trúc trình bày `2` tầng xuyên suốt từ khuôn mẫu tới kiểm chứng thực tế trên phiên bản `0.105.0`:

- **M1 — Khuôn mẫu & chuẩn `2` tầng:** Đưa bảng `Two-Tier Presentation Standard` lên đầu `skills/tdq-conventions/references/user-facing-block.md`, cấm bọc backtick quanh số thường, bổ sung ví dụ đối chiếu ở `user-facing-block-vi-du.md`, cập nhật `spec-template.md`, `plan-template.md`, `report-template.md`, `qc.md`, `skills/tdq-build/SKILL.md` và đồng bộ khối `TDQ:TOOLS` trong `docs/claude-md-mau.md` cùng `scripts/tdq_setup.py`. Mọi file luật vẫn giữ trần dưới `3.500` token (`67/67` tệp đạt chuẩn, cao nhất `3.481`).
- **M2 — Hook nhắc lúc viết `[TDQ:PLAIN]`:** Bổ sung mã `PLAIN` (`23` mã `[TDQ:*]`) vào `tools/patches/gate_guidance.py`, `tools/patches/gate_guidance.json`, `hooks/scripts/_common.py`, `hooks/scripts/prompt_context.py`, `tools/patches/agy_hooks.py` và biên dịch lại binary Rust `tdq-dispatch`. Thẻ nhắc `[TDQ:PLAIN]` (`154–156 <= 240` ký tự) xuất hiện đúng ở pha `spec`, `plan`, `report` trên cả Claude Code lẫn Antigravity.
- **M3 — Luật `R16` trong `scripts/doc_lint.py`:** Áp dụng từ mốc `R16_MOC = "2026-11-21-1819"` (miễn hồi tố tài liệu cũ và bỏ qua `brief/`) để chặn phần mở đầu thiếu `> **Tóm tắt dễ hiểu:**`, dài quá `120` từ, câu quá `35` từ, quá `6` backtick mỗi `100` từ, lộ đường dẫn thô hay `:line` và header quá `2` dấu `·`.
- **M4 — Việt hóa Archify HTML toàn diện:** `scripts/tdq_archify.py` tự đọc `doc_lang`, tiêm `@meta locale=en` vào bản tạm khi cần để tránh nhánh rơi về `zh-CN`, rồi dịch chrome HTML, JSON `#explainer-reader-words`, nhãn `分支 <N>` trong SVG, JSON `#archify-explainer-prepared` và từng payload `htmlGzip` sang `Nhánh <N>` trước khi băm manifest.
- **M5 — Đóng gói `0.105.0` & kiểm thử hành vi:** Bổ sung `tests/test_doc_lint_r16.py`, `tests/test_archify_vi.py`, mở rộng `tests/test_report_visual.py`, `tests/test_gate_guidance.py`, `tests/test_token_budget.py`, `tests/test_rust_dispatch_parity.py`, cập nhật `CHANGELOG.md`, `README.md` và biên dịch sạch `plugins/tdq-workflow-agy/`.

## 3. Đã test gì

Quá trình nghiệm thu gồm tự kiểm và `tdq-qc-tester` độc lập qua `2` vòng, trong đó Vòng 1 bắt lỗi `分支 1` trong SVG và `i18n_check` trên dòng mới rồi được vá dứt điểm trước khi chạy lại Vòng 2:

- Cụm `Q1–Q3`: `py -3 -X utf8 -m pytest tests/test_user_facing_block.py tests/test_gate_guidance.py tests/test_hooks_dual_protocol.py tests/test_rust_dispatch_parity.py tests/test_doc_lint_r16.py -q`, `cargo test --manifest-path hooks/rust/tdq-dispatch/Cargo.toml`, kiểm probe `R16` và hook `spec`/`plan`/`report`/`compact`.
- Cụm `Q4` (`QC1.1`): `py -3 -X utf8 -m pytest tests/test_archify_vi.py -v`, probe render thật `truoc-sau.archify.md` (soát SVG ngoài `<script>`, JSON `#archify-explainer-prepared`, giải nén từng `htmlGzip`), `py -3 -X utf8 scripts/i18n_check.py scripts/tdq_archify.py` và kiểm AST độ dài hàm mới.
- Cụm `Q5` (`QC1.2`): kiểm `i18n_check` delta so với nhánh `dev` trên mọi tệp nguồn chạm, `token_budget.py --kiem` (ở cả root và `plugins/tdq-workflow-agy/`), `doc_index.py --tat-ca --kiem`, `doc_lint.py` toàn bộ `skills/`, `spec/`, `reports/`, `agy plugin validate plugins/tdq-workflow-agy --strict --json`, `tdq_meta_gate.py --files ...`, và `7` module test tương thích plugin.
- Cụm `Q6` & vùng chạm: `py -3 -X utf8 scripts/tdq_test.py smoke-e2e --changed --workers auto`, `py -3 -X utf8 scripts/tdq_test.py tron-bo --workers auto` (`3/3` sau vá cuối), `6` module `QC-F2`, kiểm an toàn hệ thống (`~/.gemini/`, `main`, `soul.md`, `C:\Users\admin\Documents\archify`, `git log dev..HEAD`), và bật/tắt `TDQ_LOG=0`.
- Cụm `Q7` (tiếp nối ngay sau khi xuất tệp `.md` này): render `docs/tdq/reports/2026-11-21-1819-trien-khai-trinh-bay-2-tang.html`, xác thực `tdq_archify.py verify`, kiểm Tailscale `HTTP 200` và kiểm giao diện bằng Chrome DevTools `take_snapshot`; kết quả chốt cuối ghi vào [biên bản QC](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/qc/2026-11-21-1819-trien-khai-trinh-bay-2-tang.md).

## 4. Kết quả test

Toàn bộ hạng mục `Q1–Q6` và `QC-F1`–`QC-F4` đều đạt `PASS` tại Vòng 2 trong biên bản QC:

- **Full suite (`tron-bo --workers auto`, lượt `3/3`):** `4700 passed, 36 skipped, 2913 subtests passed` trong `291.78` giây pytest (thời gian bọc `tdq_test.py` là `306.14` giây `<= 420` giây, `bo_sot=0`, receipt `docs/tdq/cache/test-runs/b397f484b6a31ef6/bfc53d9a050f42bf88f667e8451aac77/result.json`, SHA256 `09972ee4f4b46506cd057c28ba20a795cecd918f2fd395f1b17c2f9b446f34b0`).
- **Smoke E2E (`smoke-e2e --changed --workers auto`):** `386 passed, 162 subtests passed` trong `87.51` giây (`0` failed, `0` skipped).
- **Cụm chuyên biệt & vùng chạm:** `Q1–Q3` (`94 passed, 50 subtests`), Rust `cargo test` (`29 passed`), `Q4` `test_archify_vi.py` (`8 passed` gồm test SVG/JSON/`htmlGzip`), `Q5` cụm `7` module (`64 passed, 398 subtests`), vùng chạm `QC-F2` (`225 passed, 149 subtests`), cụm hồi quy còn lại (`105 passed, 1 skipped` Windows symlink tại `tests/test_investigate_workflow.py:335`).
- **Probe render thật Archify tiếng Việt (`truoc-sau.archify.md`):** `<html lang="vi">`, `0` ký tự CJK ngoài `<script>`, `0` chuỗi `分支` trong JSON `#archify-explainer-prepared` và cả `3/3` payload `htmlGzip`, `21` nhãn `Nhánh 1`, từ điển `answer="Tóm tắt"`.
- **Lint, ngân sách token & đóng gói plugin:** `doc_lint.py` trên `437` tệp (`skills/`, `docs/claude-md-mau.md`, `spec/`, `reports/`, `plan`, `brief`) đạt `0` lỗi; `token_budget.py --kiem` đạt `67/67 <= 3.500` (cao nhất `3.481`); `agy plugin validate plugins/tdq-workflow-agy --strict --json` trả `"findings": []` bản `0.105.0`; `i18n_check` trên toàn bộ tệp nguồn chạm đạt `delta = -3 <= 0` so với `dev` (`428 → 425`).

## Đầu ra & Giao thức Git

- **Đầu ra chính:** [biên bản QC](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/qc/2026-11-21-1819-trien-khai-trinh-bay-2-tang.md), `docs/tdq/reports/2026-11-21-1819-trien-khai-trinh-bay-2-tang.md`, cùng cặp gói `plugins/tdq-workflow-agy/` (`0.105.0`) và mã nguồn `scripts/`/`hooks/`/`skills/`/`tests/`.
- **Archify HTML:** `docs/tdq/reports/2026-11-21-1819-trien-khai-trinh-bay-2-tang.html` (sẽ dựng và xác thực Chrome ngay sau bước lưu `.md` này).
- **Git:** Đang ở nhánh `feature/trien-khai-trinh-bay-2-tang` (tách từ `dev`), chưa tạo commit cuối và chưa chạy `git push`.

## Thời gian

```text
Request `2026-11-21-1819-trien-khai-trinh-bay-2-tang` · lane full · opened at 2026-11-21T18:25:54+07:00

| Phase | Wall clock | Times entered |
|---|---|---|
| idle | 0s | 1 |
| analyze | 6 min | 1 |
| spec | 6 min | 1 |
| plan | 25 min | 1 |
| implement | 2h 58min | 1 |
| qc | 1h 06min | 1 |
| report | 0s | 1 |
| Total | 4h 42min |  |

Model compute time is unavailable (`model_giay=null`). API includes network/provider latency; tool time is host wait. Observed metrics may overlap; unattributed time is not assumed user/model time.
Transcript attribution: project_window. Complete covers selected supported observations only.
Host metrics unavailable (5 hidden: api_request_seconds, tool_call_seconds, background_job_seconds, observed_union_seconds, unattributed_seconds): no_usable_source, no_usable_observations, wall_minus_observed_union;no_usable_observations

## Agent Role Telemetry

| Role | Runs | First pass | Rate | Retries | Avg elapsed | Models |
|---|---|---|---|---|---|---|
| self | 7 | 7 | 100% | 0 | — | — |
| tdq-qc-tester | 6 | 6 | 100% | 0 | — | — |
| tdq-implementer | 2 | 2 | 100% | 0 | — | — |
```

## Giới hạn

- **Cổng LSP mở đầu (`lsp_bo_qua` từ `docs/tdq/state.json`):** `{"ly_do": "Python LSP da hoat dong (26 refs cho r14_loi); kich-ban chon generate_manifest_and_readme thuoc tools/patches nam ngoai pyrightconfig.json nen chi thay 1 ref noi tep", "at": "2026-11-21T18:25:40+07:00", "module": ["python:. → TRUOT (`generate_manifest_and_readme`: 1 tham chiếu LSP so với 1 lần trong file định nghĩa — LSP không thấy tham chiếu từ file khác)"]}`
- **Công cụ `ruff`:** `ruff: not checked (not installed in PATH)` (không tự ý cài đặt; kiểm tra phụ của QC bằng `py -3 -m ruff check` trên 4 tệp Python chạm ghi nhận `130` cảnh báo có sẵn ngoài các dòng mới).
- **Eval chất lượng:** `eval: chưa kích hoạt (opt-in)` (`eval_enabled: null` trong `docs/tdq/state.json`).
- **Phạm vi bỏ qua khi chạy test (`tron-bo` `3/3`):** `36 skipped` trên tổng `4736` test (các skip phụ thuộc điều kiện môi trường, ví dụ Windows symlink privilege ở `tests/test_investigate_workflow.py:335`).
- **Cổng `tdq_meta_gate.py` mặc định / `--all`:** Lệnh `--files` đạt `PASS (3/3 checks)` và `i18n_check` trên toàn bộ tệp nguồn chạm đạt `delta = -3 <= 0` so với `dev` (`428 → 425`, `0` dòng tiếng Việt mới thiếu `i18n-allow`). Tuy nhiên, chạy không cờ hoặc `--all` vẫn báo `FAIL (3/4)` do `946` / `1.053` dòng tiếng Việt tồn đọng có sẵn trên nhánh `dev` và trong bản đóng gói `plugins/tdq-workflow-agy/` (`gate_guidance.json`).
- **Nghiệm thu `Q7` và preview spec:** Kết quả render + Tailscale `HTTP 200` + Chrome DevTools cho trang HTML báo cáo sẽ được chốt trong biên bản QC sau bước render ngay kế tiếp; bản `spec-preview.html` được làm mới lại chỉ sau khi `phase` chuyển về `idle` để không làm lệch hash spec trong lúc kiểm.

## Lệch spec chờ duyệt

không có (`tdq_state.py lech list` → `0 item(s), 0 pending`)

## Thân PR (soạn sẵn)

**Tóm tắt:** Triển khai trọn bộ `5` module nâng cấp kiến trúc trình bày `2` tầng (`M1`–`M5`) lên bản `0.105.0`: chuẩn hóa đầu ra Lớp 1/Lớp 2, thêm hook `[TDQ:PLAIN]` (`23` mã `[TDQ:*]`), bật luật kiểm `R16` (`R16_MOC = "2026-11-21-1819"`) và Việt hóa hoàn toàn Archify HTML (kể cả nhãn `Nhánh` trong SVG và `htmlGzip`).

**Trước/Sau:** Xem sơ đồ đối chiếu Trước/Sau trong `docs/tdq/spec/2026-11-21-1819-trien-khai-trinh-bay-2-tang-preview.html` và báo cáo trực quan tại `docs/tdq/reports/2026-11-21-1819-trien-khai-trinh-bay-2-tang.html`.

**Đã kiểm:**
- `py -3 -X utf8 scripts/tdq_test.py tron-bo --workers auto` → `4700 passed, 36 skipped, 2913 subtests passed` (`306.14s`)
- `py -3 -X utf8 scripts/tdq_test.py smoke-e2e --changed --workers auto` → `386 passed, 162 subtests passed` (`87.51s`)
- `cargo test --manifest-path hooks/rust/tdq-dispatch/Cargo.toml` → `29 passed`
- `agy plugin validate plugins/tdq-workflow-agy --strict --json` → `"findings": []` (`0.105.0`)
- `py -3 -X utf8 scripts/doc_lint.py skills docs/claude-md-mau.md docs/tdq/spec docs/tdq/reports ...` → `437` file, `0` lỗi
- `$env:TDQ_TOKENS_VENV=...; py -3 -X utf8 scripts/token_budget.py --kiem` → `67/67 <= 3500` token (max `3481`)

**Rủi ro hồi quy:** Thay đổi khuôn mẫu `Two-Tier` và số mã `[TDQ:*]` (`22 → 23`) ảnh hưởng tới `test_user_facing_block.py`, `test_gate_guidance.py`, `test_hooks_dual_protocol.py`, `test_rust_dispatch_parity.py`, `test_claude_md_core.py`, `test_auto_update_setup.py`, `test_agy_plugin_validate.py`; toàn bộ các bộ test khóa và parity hai môi trường đều đang pass đồng bộ.
<!-- tdq-archify-binding:start -->
<!-- manifest: 2026-11-21-1819-trien-khai-trinh-bay-2-tang.manifest.json -->
<!-- manifest_digest: 95c7f2ac58ecb9be7a71c6b6298ecd02eb4041d469d6fcaacab33daa1a1e046f -->
<!-- tdq-archify-binding:end -->