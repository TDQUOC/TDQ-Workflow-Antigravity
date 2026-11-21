# QC — Nâng cấp QC, Tester và E2E Smoke (`v0.104.0`)

Ngày: 2026-11-21 · Plan: ../plan/2026-11-21-1536-nang-cap-qc-tester-e2e.md · Vòng: 1 (đã vá `QC1.1`)
Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

## Dev Behavior QC Card

- **Auto Meta-Gate:** `PASS (4/4 checks, 0.08s)` trên tệp thuần Anh + spec (`tdq_meta_gate.py`). Quét rộng có kèm `scripts/doc_lint.py`, `scripts/tdq_test.py` và bảng `muc_qc` của `qc.md` giữ nguyên các chuỗi tiếng Việt cũ ngoài diff (`30` findings cũ đã ghi nhận rõ).
- **Luồng đổi:** Nâng cấp chuỗi QC/Tester `v0.104.0` theo hướng Dev-First, E2E-First (`--workers auto`, `Changed-Flow E2E Smoke`, `Auto Meta-Gate`, `tdq_timing.py` ẩn 5 cột `[unavailable]`, `Dev Behavior QC Card`, Accessibility Tree Snapshot mặc định).
- **Chạy thử thật (Before → After + Bằng chứng tươi):** `tron-bo` giảm từ `19.8` phút tuần tự xuống `313.9s` (`~5.2` phút) ở `--workers auto` (`4,704` collected, `4,693` passed, `11` skipped baseline, `0` failed, `0` INCOMPLETE, `bo_sot=0`). `smoke-e2e` đạt `70/70` (`19.42s`). `agy plugin validate --strict` đạt `"findings": []`.
- **Rủi ro còn lại:** `11` case baseline skipped theo hệ điều hành/môi trường trong `tron-bo`; cài đặt người dùng `~/.gemini/`, nhánh `main` và remote git cố tình giữ nguyên chưa chạm.

## Bảng tổng hợp `Q1`–`Q8` và `QC-F1..F4`

| # | Hạng mục | Lệnh đã chạy | Kết quả | PASS/FAIL |
|---|---|---|---|---|
| Q1 | Wave 1 runner (`--workers auto`, `.html`, `.ruff_cache`) | `py -3 -X utf8 -m pytest tests/test_tdq_test.py tests/test_tdq_test_receipt.py tests/test_smoke_e2e_routing.py -q` | `224 passed, 19 subtests passed (154.03s)` | PASS |
| Q2 | `tdq_timing.py` ẩn 5 cột V2 rỗng & giữ JSON v2 | `py -3 -X utf8 -m pytest tests/test_timing.py tests/test_phase1_contract.py -q` + `tdq_timing.py show` | `77 passed, 9 subtests passed (117.57s)`; bảng 3 cột `Phase`, `Wall clock`, `Times entered` | PASS |
| Q3 | Wave 2 `Changed-Flow E2E Smoke` & khóa `v0.103.0` | `py -3 -X utf8 scripts/tdq_test.py smoke-e2e --files agents/tdq-explorer.md tools/patches/skills_and_agents.py --fail-fast` | `70 passed, 0 skipped (19.42s <= 60s)`; `365/4704` smoke collected across `>= 15` modules | PASS |
| Q4 | `Auto Meta-Gate` & `doc_lint.py` CLI Bug Board | `py -3 -X utf8 scripts/tdq_meta_gate.py --files ...` + `tests/test_meta_gate.py` | `Auto Meta-Gate: PASS (4/4 checks, 0.08s)` trên tệp đích (`doc_lint`/`test_doc_lint` pass) | PASS |
| Q5 | Wave 1–3 hợp đồng `skills/` & `agents/` + `i18n` | `i18n_check.py` + `pytest test_muc_qc_qc_md test_dev_qc_card_rules test_clean_code_rule test_vision_test_loop_doc test_luat_skill` | `0 Vietnamese line(s)` trên 6 tệp mới/thuần Anh; sau vá `QC1.1` `115 passed, 374 subtests (12.22s)` | PASS |
| Q6 | Wave 3 Accessibility Tree Snapshot E2E (`take_snapshot`) | `pytest test_vision_test_loop_doc test_devtool_mcp_integration` + live Chrome DevTools MCP | `13 passed (1.03s)`; `navigate_page` + `take_snapshot` + `click uid=1_6` + `0` console errors | PASS |
| Q7 | Version `0.104.0`, `CHANGELOG <= 500`, `token-budget`, `agy validate` | `token_budget.py --kiem` + `build_agy_plugin.py` + `agy plugin validate --strict --json` + pytest | `CHANGELOG` `477` dòng; `67` files token lock OK; `"findings": []`; `21 passed (7.17s)` | PASS |
| Q8 | `QC-F1`: `tron-bo --workers auto --fresh --reuse off` & `TDQ_LOG` | `tdq_test.py tron-bo --workers auto --fresh --reuse off` + `tdq_test.py so` + `tests/test_meta_gate.py` | `4704` tests (`4693` passed, `11` skipped baseline, `0` failed, `bo_sot=0`, `313.9s <= 420s`); `TDQ_LOG=1/0` OK | PASS |
| QC-F2 | Hồi quy vùng chạm (`vung-cham`) | `tdq_test.py vung-cham --files skills/tdq-build/references/qc.md skills/tdq-browser-test/SKILL.md` | `23/226` modules, `470 passed, 197 subtests (121.81s)`, `exit 0` | PASS |
| QC-F3 | `6` ràng buộc kiến trúc spec §5 | Đối chiếu trực tiếp từng dòng spec §5 trên mã nguồn và cấu trúc repo | Bảo toàn phân tầng 3 ngôn ngữ, gọi 1 chiều `hooks->scripts`, token lock, 2 cổng `tron-bo`, `muc_qc`, nhánh `dev` | PASS |
| QC-F4 | Clean Code (nhánh procedural/script vs OOP) & `ruff` | `py -3 -m ruff check --select E,F,W --ignore E501 ...` + rà từng module `.py` đổi | Không tạo class OOP mới; `ruff` `All checks passed!`; xử lý fail-closed, không trùng logic, hàm gọn | PASS |

## Bằng chứng

### Vòng 1 & Vòng sửa `QC1.1`
- Lần chạy `tron-bo` đầu (`329.6s`) phát hiện `3` hồi quy hợp đồng chéo: `test_luat_gate_chat.py` (thiếu cụm `the phase does not change` ở dòng `Next step:` trong `skills/tdq-browser-test/SKILL.md`), `test_luat_skill.py` (`L021`–`L026`), `test_ultracode_contract.py` (`Ultracode`) và `test_muc_qc_qc_md.py` (`never raise`) trong `skills/tdq-build/references/qc.md`.
- Đã sửa gọn trong `QC1.1`, cập nhật `token-budget.json` (`67` tệp), biên dịch lại `plugins/tdq-workflow-agy/` (`"findings": []`), kiểm lại `11` module hợp đồng (`115 passed, 374 subtests in 12.22s`), chạy `vung-cham` (`470 passed in 121.81s`) và chạy lại `tron-bo --workers auto` lần cuối (`2/3` budget) đạt `PASS` (`4704` tests, `11` skipped baseline, `0` failed, `313.9s`, `bo_sot=0`).

### `Q6` Chrome DevTools MCP (`Archify HTML preview`)
- URL kiểm thật qua Tailscale: `https://unity-pc-rtx3060.tail99896.ts.net/vlog/tdq-workflow-agy/spec/2026-11-21-1536-nang-cap-qc-tester-e2e-preview.html`.
- `take_snapshot` đọc đủ Accessibility Tree (`uid=1_0`..`uid=1_81`, `3 panels`, `3 diagrams validated`), tương tác thật `click(uid="1_6")` chuyển trạng thái nút `"Light"` sang `focused pressed`, `list_console_messages(types=["error","warn"])` trả rỗng (`0` console errors).

### `QC-F3` Ràng buộc kiến trúc spec §5 & `QC-F4` Clean Code
- Toàn bộ file mới trong `scripts/` (`tdq_meta_gate.py`) không import `hooks/` và nạp `i18n_check` tùy chọn để không vỡ đóng gói release `build_portable.py` (`test_build_portable.py` + `test_v01030_regression_smoke.py` đều xanh).
- Nhánh `full` giữ đúng `runtime test = KHÔNG` và `tdq-qc-tester = KHÔNG`, chỉ mở `smoke test = CÓ` (`--workers auto`).
- Không mở rộng `clean-code.md`; phần sửa `tdq_test.py`, `tdq_timing.py`, `tdq_meta_gate.py`, `doc_lint.py`, `build_portable.py` dùng cấu trúc hàm thủ tục gọn, fail-closed rõ ràng, kiểm `ruff check` sạch `0` lỗi mới.

## Lệch spec chờ duyệt

không có

## Kết luận

PASS toàn bộ — đạt đủ `Q1`–`Q8` và `QC-F1`–`QC-F4` (sau `1` vòng vá `QC1.1`), sẵn sàng chuyển sang pha `report`.
