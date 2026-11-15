# QUICK — Đặt lại mặc định mức gắt Ponytail (muc_gat) về full

Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

**Ngày:** 2026-11-16 · Brief: ../brief/2026-11-16-0058-dat-mac-dinh-ponytail-full.md · Lane: quick
**Trạng thái:** HOÀN THÀNH
**Ước tính sẽ dùng skill:** không có

## Phạm vi
- Trong: Đổi mặc định và fallback `muc_gat` từ `ultra` về `full` ở state, hook lọc luật, bảng cường độ `chung.md`, khóa token, bản biên dịch `plugins/tdq-workflow-agy/` và bộ test hồi quy.
- NGOÀI: Không đổi `muc_qc` (giữ mặc định `full`), không ép đổi các project đã đặt tường minh `lite|full|ultra|off`.
- Bỏ vòng scope: yêu cầu đã chỉ định đích danh đổi mặc định `muc_gat` về `full`, không có miền mở cần chọn.
- Bỏ B0: đã có tiền lệ trực tiếp tại `docs/tdq/reports/2026-11-01-ponytail-ultra-0.85.1.md` trên cùng nhóm thư mục.
- Bỏ B2: thay đổi thuần nội bộ trong codebase hiện có, không có ẩn số hay thư viện ngoài.

## Task
- [x] **T1** (e5m) Đổi mặc định `muc_gat` về `full` trong `tdq_state.py`, `luat_gon.py` kèm unit test — Test: `py -3 -m unittest tests.test_state_muc_gat tests.test_luat_gon tests.test_state_muc_qc`
  - Chạm: `scripts/tdq_state.py`, `hooks/scripts/luat_gon.py`, `tests/test_state_muc_gat.py`, `tests/test_luat_gon.py`, `tests/test_state_muc_qc.py`
  - Đặc tả logic: đặt `MUC_GAT_MAC_DINH = "full"` và `MUC_MAC_DINH = "full"` (fail-closed giữ nguyên `lite|full|ultra|off`, giữ `muc_qc = "full"`); cập nhật docstring và test đỏ trước xanh sau.
- [x] **T2** (e5m) Cập nhật bảng cường độ ở `chung.md`, tái tạo khóa token và biên dịch đồng bộ `plugins/tdq-workflow-agy/` — Test: `py -3 scripts/doc_lint.py skills/tdq-build/references/rules/chung.md`
  - Chạm: `skills/tdq-build/references/rules/chung.md`, `docs/tdq/token-budget.json`, `plugins/tdq-workflow-agy/scripts/tdq_state.py`, `plugins/tdq-workflow-agy/hooks/scripts/luat_gon.py`, `plugins/tdq-workflow-agy/skills/tdq-build/references/rules/chung.md`
  - Đặc tả logic: chuyển nhãn `(the default)` và dòng fallback trong `chung.md` từ `ultra` sang `full`; chạy `scripts/token_budget.py`, `tools/build_agy_plugin.py` và `tools/install_agy_plugin.py` để đồng bộ bản cài.

## Definition of Done
- [x] `py -3 -m unittest tests.test_state_muc_gat tests.test_luat_gon tests.test_state_muc_qc` chạy xanh 100% và xác nhận `default_state()["muc_gat"] == "full"`.
- [x] `py -3 scripts/doc_lint.py skills/tdq-build/references/rules/chung.md` và `py -3 scripts/token_budget.py --kiem` đều exit `0`.
- [x] Bản biên dịch `plugins/tdq-workflow-agy/scripts/tdq_state.py` và `plugins/tdq-workflow-agy/hooks/scripts/luat_gon.py` đồng bộ `full` với nguồn gốc.
## QC
- Q1 test từng task: PASS — `PYTHONPATH=tests py -3 -m unittest tests.test_state_muc_gat tests.test_luat_gon tests.test_state_muc_qc` (38 tests, 2.192s OK) & `py -3 -X utf8 scripts/doc_lint.py skills/tdq-build/references/rules/chung.md` (0 violation(s), exit 0)
- Q2 DoD "`py -3 -m unittest tests.test_state_muc_gat tests.test_luat_gon tests.test_state_muc_qc` chạy xanh 100% và xác nhận `default_state()[\"muc_gat\"] == \"full\"`.": PASS — Ran 38 tests OK, `default_muc_gat=full`
- Q3 DoD "`py -3 scripts/doc_lint.py skills/tdq-build/references/rules/chung.md` và `py -3 scripts/token_budget.py --kiem` đều exit `0`.": PASS — `DOC_LINT=0`, `TB_KIEM=0`
- Q4 DoD "Bản biên dịch `plugins/tdq-workflow-agy/scripts/tdq_state.py` và `plugins/tdq-workflow-agy/hooks/scripts/luat_gon.py` đồng bộ `full` với nguồn gốc.": PASS — `plugin_sync=full` (`SYNC_OK` cả bản cài `~/.gemini/config/plugins/tdq-workflow-agy`)
<!-- tdq-archify-binding:start -->
<!-- manifest: 2026-11-16-0058-dat-mac-dinh-ponytail-full-flow.manifest.json -->
<!-- manifest_digest: 5efccce366d7998d51e32486aa036bfd16c873dd2ca4c4af406b164c9da82997 -->
<!-- tdq-archify-binding:end -->