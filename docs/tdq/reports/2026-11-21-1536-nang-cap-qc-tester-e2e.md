# Báo cáo — Nâng cấp QC, Tester và E2E Smoke (`v0.104.0`)

Ngày: 2026-11-21 · Spec: `../spec/2026-11-21-1536-nang-cap-qc-tester-e2e.md` · Plan: `../plan/2026-11-21-1536-nang-cap-qc-tester-e2e.md` · QC: `../qc/2026-11-21-1536-nang-cap-qc-tester-e2e.md`

## Tóm tắt dễ hiểu

> Toàn bộ hệ thống kiểm thử, QC và đóng gói `tdq-workflow-agy` đã lên bản `0.104.0` với `11/11` task (`Wave 1`–`4` và `T5.1`) hoàn tất. Thay cho cách chạy tuần tự gần `20` phút và kiểm thủ tục rườm rà, bản mới dùng `--workers auto`, tách kiểm tài liệu thành `Auto Meta-Gate` `1` dòng, mở `Changed-Flow E2E Smoke` dưới `20` giây, thêm `Dev Behavior QC Card`, ưu tiên Accessibility Tree Snapshot và đạt `4,693/4,704` test xanh (`0` fail) trong `313.9` giây.

## 1. Trước request (trạng thái/flow)

Trước khi sửa, luồng QC `v0.103.1` chậm vì `tron-bo` mặc định ép `--workers 1` mất `19.8` phút. Hai thư mục `.ruff_cache` và file `.html` làm sai lệch đếm cache hoặc quét sót test khi đổi giao diện. Lệnh `tdq_timing.py show` in thêm `5` cột máy `[unavailable]` làm bảng dài và khó đọc.

Mức `muc_qc=full` mặc định tắt `smoke test`, chưa có tuyến `smoke-e2e` theo vùng đổi hay test khóa lỗi `call_mcp_tool` của bản `v0.103.0`. Khi chạy QC, người làm phải gõ nhiều lệnh rời để kiểm lint/i18n/token, đọc toàn bộ `5` câu SOLID OOP cả với script thủ tục, và `tdq-browser-test` mặc định chụp ảnh so pixel nặng thay vì Accessibility Tree.

## 2. Sau request (trạng thái/flow)

Sau `3` Wave triển khai và vòng sửa `QC1.1`, luồng kiểm thử mới vận hành theo `3` tầng Dev-First, E2E-First:

- **Runner & Timing (`scripts/tdq_test.py`, `scripts/tdq_test_receipt.py`, `scripts/tdq_timing.py`, `pytest.ini`):** Hỗ trợ `--workers auto` (`min(6, cpu_count)`), thêm `.html`/`.htm` vào `DATA_EXTS`, bỏ qua `.ruff_cache` ở `EXCLUDED_DIRS`, thêm `SMOKE_ROUTES` / `smoke-e2e`, ẩn `5` cột host khi toàn bộ đều `[unavailable]` nhưng vẫn giữ nguyên JSON v2.
- **Auto Meta-Gate & Bug Board CLI (`scripts/tdq_meta_gate.py`, `scripts/doc_lint.py`, `scripts/build_portable.py`):** Gom `doc_lint`, `i18n_check` (nạp tùy chọn để an toàn khi đóng gói release), `token_budget`, kiểm `Co-Authored-By:` và kiểm cờ `--flag` trong `docs/tdq/{scenarios,bugs}/` thành `1` dòng tóm tắt gọn.
- **Marker `smoke`/`e2e` & Khóa lỗi `v0.103.0` (`15+` module `tests/test_*.py`, `tests/test_v01030_regression_smoke.py`):** Tách tầng kiểm nhanh để `smoke-e2e` chạy vùng đổi `< 60s` và chặn cứng tool cấm (`call_mcp_tool`, `grep_search`…) trên bundle compile.
- **Quy tắc QC & Browser (`skills/tdq-build/references/qc.md`, `report-template.md`, `vision-test-loop.md`, `skills/tdq-browser-test/**`, `agents/tdq-qc-tester.md`):** Mức `full` bật `smoke test = CÓ` (`--workers auto`), giữ `runtime test = KHÔNG` và `tdq-qc-tester = KHÔNG`. Bổ sung `Dev Behavior QC Card`, giới hạn `5` SOLID OOP cho class/tầng, mặc định `take_snapshot` + `uid` fail-closed + `list_console_messages` kèm `scenario-template.md` (`7–19` dòng, Bug Board, `e2e_adapter: none`).
- **Đóng gói `0.104.0` (`.claude-plugin/plugin.json`, `.codex-plugin/plugin.json`, `Cargo.toml`, `tools/`, `README.md`, `CHANGELOG.md`, `UPSTREAM-TRACE.md`, `plugins/tdq-workflow-agy/`):** Đồng bộ `0.104.0`, cập nhật `token-budget.json` (`67` tệp) và biên dịch `plugins/tdq-workflow-agy/` sạch `0` findings.

## 3. Đã test gì

- Chạy kiểm thử đơn vị + tích hợp theo từng Wave (`Q1` `test_tdq_test*`, `Q2` `test_timing`/`test_phase1_contract`, `Q3` `smoke-e2e`, `Q4` `tdq_meta_gate`, `Q5`–`Q7` hợp đồng skill, `i18n_check`, `token_budget`, `test_v01030_regression_smoke`, `test_build_portable`).
- Chạy `ruff check --select E,F,W --ignore E501` trên các tệp Python đã sửa/tạo và `doc_lint.py` trên các tệp Markdown đã cập nhật.
- Kiểm tra `TDQ_LOG=1/0` qua `tests/test_meta_gate.py` và chạy trực tiếp `tdq_timing.py show` với `TDQ_LOG=0`.
- Kiểm thử giao diện Archify HTML preview trực tiếp qua Chrome DevTools MCP (`navigate_page`, `take_snapshot`, `click uid=1_6`, `list_console_messages`).
- Chạy `agy plugin validate plugins/tdq-workflow-agy --strict --json`, `tdq_test.py vung-cham` (`23/226` module sau vá `QC1.1`) và `tdq_test.py tron-bo --workers auto --fresh --reuse off` kèm `tdq_test.py so`.

## 4. Kết quả test

- **`Q1`–`Q2` & `Q4`–`Q7`:** `Q1` đạt `224 passed, 19 subtests` (`154.03s`). `Q2` đạt `77 passed, 9 subtests` (`117.57s`) và bảng `tdq_timing.py show` còn `3` cột sạch `[unavailable]`. `Auto Meta-Gate` đạt `PASS (4/4 checks, 0.08s)` trên spec + tệp thuần Anh. `Q5`/`Q6`/`Q7` sau vá `QC1.1` đạt `115 passed, 374 subtests` (`12.22s`), `21/21` test khóa token (`7.17s`), `ruff check` sạch `All checks passed!`, `agy plugin validate --strict` đạt `"findings": []`, `CHANGELOG.md` dài `477` dòng (`<= 500`).
- **`Q3` (`Changed-Flow E2E Smoke`):** `365/4704` case mang marker `smoke` trên `>= 15` module; `tdq_test.py smoke-e2e --files agents/tdq-explorer.md tools/patches/skills_and_agents.py --fail-fast` đạt `70 passed, 0 skipped` trong `19.42s` (`<= 60s`).
- **`Q6` (Chrome DevTools MCP thực tế):** `take_snapshot` đọc đủ Accessibility Tree (`uid=1_0`..`uid=1_81`, `3 panels`), tương tác `click(uid="1_6")` bật nút `"Light"` thành `focused pressed`, `list_console_messages` báo `0` console error.
- **`Q8` / `QC-F1` (`tron-bo --workers auto --fresh --reuse off`):** Lần 1 (`329.6s`) phát hiện `3` hồi quy hợp đồng chữ neo (`L024`, `never raise`, `Ultracode`, `Next step`), đã sửa ở `QC1.1`. Chạy `vung-cham` đạt `470/470` (`121.81s`), rồi chạy `tron-bo` lần `2/3` đạt `PASS`: **`4,704` tests (`4,693` passed, `11` skipped baseline, `0` failed, `0` INCOMPLETE, `bo_sot=0`) trong `313.9s`** (`~5.2` phút, `<= 420s`).

## Thời gian

Request `2026-11-21-1536-nang-cap-qc-tester-e2e` · lane full · opened at 2026-11-21T15:49:05+07:00

| Phase | Wall clock | Times entered |
|---|---|---|
| idle | 0s | 1 |
| analyze | 6 min | 1 |
| spec | 6 min | 1 |
| plan | 6 min | 1 |
| mode | 2 min | 1 |
| implement | 55 min | 1 |
| qc | 24 min | 1 |
| report | 1s | 1 |
| Total | 1h 38min |  |

Ghi chú trực tiếp từ `tdq_timing.py show`:

```text
Model compute time is unavailable (`model_giay=null`). API includes network/provider latency; tool time is host wait. Observed metrics may overlap; unattributed time is not assumed user/model time.
Transcript attribution: project_window. Complete covers selected supported observations only.
Host metrics unavailable (5 hidden: api_request_seconds, tool_call_seconds, background_job_seconds, observed_union_seconds, unattributed_seconds): no_usable_source, no_usable_observations, wall_minus_observed_union;no_usable_observations
```

## Agent Role Telemetry

| Role | Runs | First pass | Rate | Retries | Avg elapsed | Models |
|---|---|---|---|---|---|---|
| self | 7 | 7 | 100% | 0 | — | — |
| tdq-qc-tester | 6 | 6 | 100% | 0 | — | — |
| tdq-implementer | 2 | 2 | 100% | 0 | — | — |

## Giới hạn

- **Bỏ qua LSP (`lsp_bo_qua`):** `"python:. probe symbol tools/patches/agy_manifests.py:generate_manifest_and_readme nam ngoai pyrightconfig.json include [scripts, hooks, tests]; rust:hooks/rust/tdq-dispatch khong cham trong request Py"` (chính sách có sẵn trên nhánh `python` và `rust`).
- **Commit gỡ block / checkpoint nội bộ trong pha implement:** `94cf2e45`, `78de275a`, `806ad1c1` (Wave 1 + `pytest.ini`), `1762cb94` (Wave 3 `T3.1`/`T3.2`), `8c0cf077` (gộp Wave 2 `0bf5697d`, `424f7b74`, `afe229d1`, `3192063e` + vá đóng gói release `tdq_meta_gate`/`build_portable`). Wave 4 (`0.104.0`), vá `QC1.1`, file QC và Report vẫn giữ ở working tree chờ bạn xác nhận commit.
- **Quét `i18n_check` trên tệp cũ ngoài diff:** Các chuỗi tiếng Việt sẵn có trước request trong `scripts/doc_lint.py` (`L59`–`L62`, `L961`, `L967`, `L1377`), `scripts/tdq_test.py` (`L1809`, `L1811`) và bảng `muc_qc` của `skills/tdq-build/references/qc.md` (`L35`–`L38`) được giữ nguyên tương thích.
- **Test skipped baseline:** `11` case skipped trong `tron-bo` thuộc điều kiện nền tảng POSIX/công cụ tùy chọn có sẵn của kho mã nguồn.
- **Ranh giới môi trường:** Không ghi đè cài đặt người dùng `~/.gemini/config/plugins/`, không chỉnh nhánh `main` và không chạy `git push`.
<!-- tdq-archify-binding:start -->
<!-- manifest: 2026-11-21-1536-nang-cap-qc-tester-e2e.manifest.json -->
<!-- manifest_digest: 2110c12febd0dc183faf6c8bf22a3b8d2c051c72375f8374e6d3b3e67e13c309 -->
<!-- tdq-archify-binding:end -->