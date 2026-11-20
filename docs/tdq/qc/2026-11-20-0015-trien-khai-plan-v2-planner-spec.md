# QC — Triển khai Plan V2+ & Per-Task Spec (`2026-11-20-0015-trien-khai-plan-v2-planner-spec`)

Ngày: 2026-11-20 · Mức QC: `full` (`DoD + tron-bo + QC-F1..F4`) · Nhánh: `feature/trien-khai-plan-v2-planner-spec` · Tham chiếu: `docs/tdq/spec/2026-11-20-0015-trien-khai-plan-v2-planner-spec.md`, `docs/tdq/plan/2026-11-20-0015-trien-khai-plan-v2-planner-spec.md`

## Hạng mục

- [x] **Q1 — Cô lập `Chạm:`/`Tham chiếu:`/`Sinh ra:`, ổn định `plan_assignment_sha` & `tdq_team.py packet`** → PASS
  - Lệnh: `py -3 -X utf8 -m pytest tests/test_team_packet_v2.py tests/test_team_mode.py tests/test_team_chong_conflict.py tests/test_plan_v2_linter.py tests/test_state_plan_v2_gate.py tests/test_doc_lint.py tests/test_quick_qc.py tests/test_hooks_dual_protocol.py -q` (`326 passed, 2 skipped, 59 subtests passed`, exit `0`) + `py -3 -X utf8 -m unittest tests/test_team_packet_v2.py -v` (`17 tests OK`, bao gồm regression test bare path trong `- Chạm:` và không rò URL/`Test:` backtick).
- [x] **Q2 — `scripts/tdq_plan_scaffold.py` thuần stdlib có `TDQ_LOG`** → PASS
  - Lệnh: `py -3 -X utf8 -m unittest tests/test_plan_scaffold.py -v` (`17 tests OK in 1.223s`) + `tdq_plan_scaffold.py --verify-plan` (`tasks=10 errors=0`) + `--check-wave` (`tasks=10 errors=0`) + AST check (`0` hàm `> 50` dòng, `0` import `hooks`).
- [x] **Q3 — `doc_lint.py` (`R15-Full`/`R15-Compact`, Per-Task Spec, `ANTI-2`, `R15_MOC`) & cổng `tdq_state.py`/`tdq_eval.py`** → PASS
  - Lệnh: 8-module pytest ở trên (`326 passed`, `0` lỗi) + `doc_lint.py --pair` (`0` vi phạm) + toàn bộ các plan từ `2026-11-11` đến `2026-11-20` đạt `0` vi phạm mới; `tdq_eval.py` chỉ cập nhật regex khớp `[ >~x]` / `QC` mà vẫn giữ toàn bộ logic đánh giá thực.
- [x] **Q4 — Ngưỡng token (`<= 3,500`), dòng/ref (`<= 235`), `tdq-plan/SKILL.md <= 132L`, `plan-examples.md <= 1,300` tok, `tdq-implementer.md <= 42L`, `doc_lint`/`i18n_check`/`doc_index`** → PASS
  - Đo thực tế: `tdq-plan/SKILL.md` = `120` dòng (`<= 132`), `plan-examples.md` = `70` dòng & `1,281` tokens (`<= 1,300`), `tdq-implementer.md` = `31` dòng (`<= 42`), `qc.md` = `192` dòng & `3,444` tokens (`<= 3,500`), `refs_over_235: []`.
  - Lệnh: `doc_lint.py skills agents` (`82` files, `0` vi phạm), `token_budget.py --kiem` (`65` files `<= 3,500` tok, exit `0`), `i18n_check.py` trên `10` tệp mới/viết lại (`0 Vietnamese line(s)`), `doc_index.py --tat-ca --kiem` (exit `0`), `pytest tests/test_token_budget.py tests/test_reference_mot_tang.py tests/test_agent_frontmatter.py -q` (`17 passed, 21 subtests passed`).
- [x] **Q5 — Đóng gói `plugins/tdq-workflow-agy/`, Parity Rust–Python & không chạm plugin ngoài repo** → PASS
  - Lệnh: `build_portable.py --sinh-main --dry-run` (`kept=180 dropped=6757`, exit `0`) + `py -3 -X utf8 -m pytest tests/test_build_portable.py tests/test_agy_plugin_validate.py tests/test_rust_dispatch_parity.py -q` (`90 passed, 4 subtests passed in 82.35s`) + `C:\Users\admin\.gemini\config\plugins\tdq-workflow-agy\manifest.json` mtime `1795069294.2559528` (`2026-11-19T13:21:34+07:00`, giữ nguyên bất biến theo `3A`).
- [x] **Q6 — Nghiệm thu E2E `3` kịch bản & trọn bộ toàn repo (`muc_qc=full`)** → PASS
  - Lệnh: `py -3 -X utf8 -m unittest tests/test_team_packet_v2.py tests/test_plan_scaffold.py tests/test_plan_v2_linter.py tests/test_state_plan_v2_gate.py tests/test_plan_v2_e2e.py -v` (`67 tests in 24.409s -> OK`) + `py -3 -X utf8 scripts/tdq_test.py tron-bo --workers 1 --fresh --reuse off` (`220` mô-đun, `4525` collected, `35` skipped, `0` failed, `[TDQ:TEST] PASS` trong `1370.06s`) + `tdq_test.py so` (`tron_bo=1`, `bo_sot=0`, `budget=2`).

## Hạng mục `full` (`QC-F1..F4`) & `§3b`

- **QC-F1 (trọn bộ fresh):** `tdq_test.py tron-bo --workers 1 --fresh --reuse off` → PASS (`4525` cases, `35` platform/optional skips, `0` failed), `tdq_test.py so` → `bo_sot=0`. (Ở lần chạy `vung-cham` trước đó đã bắt `5` hồi quy trên `4` mô-đun: đường dẫn không backtick ở `- Chạm:` trong `test_e2e_workflow.py`, thiếu `Auto-Clarity` trong `agents/tdq-implementer.md`, thiếu `(BẮT BUỘC)` trong `skills/tdq-plan/SKILL.md`, mất neo `L027` trong `qc.md`, lệch `26/329` số dòng trong `docs/tdq/audit/luat-hien-co.md`; cả `5` đã sửa red → green trước vòng `tron-bo` cuối.)
- **QC-F2 (căn cứ phủ test nút chạm):** Tất cả hàm mới/sửa trong `scripts/tdq_team.py`, `scripts/tdq_plan_scaffold.py`, `scripts/doc_lint.py`, `scripts/tdq_state.py`, `scripts/tdq_eval.py`, `tools/patches/agy_hooks.py` đều có unit + E2E test phủ (`test_team_packet_v2.py`, `test_plan_scaffold.py`, `test_plan_v2_linter.py`, `test_state_plan_v2_gate.py`, `test_plan_v2_e2e.py`, `test_agy_plugin_validate.py`, `test_rust_dispatch_parity.py`).
- **QC-F3 (kiến trúc `docs/kien-truc.md`):**
  1. `scripts/` không import `hooks/` hoặc `tests/` (`hooks_import=0`, `tests_import=0`).
  2. `skills/` chỉ tham chiếu tên lệnh `scripts/`, không nhúng mã CLI.
  3. Chỉ `scripts/tdq_state.py` ghi `docs/tdq/state.json`.
  4. Code runtime mới nằm gọn trong `scripts/` (`tdq_plan_scaffold.py`, mở rộng `tdq_team.py`/`doc_lint.py`/`tdq_state.py`/`tdq_eval.py`) và adapter `tools/patches/`.
  5. `tests/` không bị tầng runtime import.
- **QC-F4 (Clean Code Self-Check 5 câu):**
  1. Có thể hiểu hàm mới/sửa trong <= 30 giây? **YES** (`tdq_plan_scaffold.py` 0 hàm `> 50` dòng; `_extract_paths` trong `tdq_team.py` ~15 dòng, lồng nông).
  2. Mỗi hàm mới có phạm vi <= 50 dòng & không lặp khối giống nhau? **YES**.
  3. Đã xử lý rõ ràng lỗi I/O, tham số rỗng và phân nhánh fail-closed? **YES** (`--from-spec` exit `1`, `--verify-plan` exit `1`, `approve` chặn `R15` đỏ nhưng fail-open chỉ khi thiếu module/cũ trước `2026-11-20`).
  4. Không giữ `bare except: pass` nuốt lỗi im lặng ở code mới? **YES** (`bare_except_pass=[]` trên `doc_lint.py`, `tdq_plan_scaffold.py`, `tdq_eval.py`, `tdq_ten_lenh.py`, `agy_hooks.py`; `ImportError` ở `tdq_state.py` là fail-open chủ đích có test khoá).
  5. Mọi tệp thực thi mới có dịch vụ log bật mặc định (`TDQ_LOG=0` để tắt)? **YES** (đã xác minh CLI thực trên `tdq_plan_scaffold.py` và `tdq_team.py packet`).
- **Đối chiếu `§3b` (`DÙNG:`):** `0` hàng `DÙNG:` ngoài bộ kỹ năng TDQ chuẩn trong spec (`§3b` toàn bộ là `NỀN`/`KHÔNG`).
- **Lệch spec (`tdq_state.py lech list`):** `0` item, `0` pending.

## Kết luận
PASS toàn bộ (`6/6` mục DoD `Q1..Q6`, `QC-F1..F4`, `4525/4525` test suite `tron-bo` `0` failed, `0` bỏ sót). Sẵn sàng chuyển pha `report`.
