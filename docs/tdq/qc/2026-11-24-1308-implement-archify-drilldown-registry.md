# QC — Triển khai trọn bộ cải thiện Archify (Drill-down nhiều tầng, Logic Node Registry và Tree-sitter Setup)
Ngày: 2026-11-24 · Plan: ../plan/2026-11-24-1308-implement-archify-drilldown-registry.md (Vòng 1)
Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

> **Tóm tắt dễ hiểu:** Toàn bộ cụm tính năng Archify mới (kho Logic Node 4 tầng băm bằng `tree-sitter`, vỏ HTML Portal dưới 300 KB, đồng bộ `--incremental`, `serve` cục bộ, cài đặt `tree-sitter` và kiểm thử Chrome sống) đã vượt qua kiểm chứng với `431 passed` trên cụm Archify + Setup, `417 passed` trên `smoke-e2e` và `depth=4 · console_errors=0 · file_fallback=PASS` trên Chrome. Một lỗi rò biến `TDQ_LOG=0` giữa các file test đã được bắt tại vòng QC 1 và sửa sạch (`QC1.1`). Các lỗi còn lại trên toàn bộ `tron-bo` (3 ca lệch phiên bản `0.106.0` vs `0.105.0`) và `i18n_check` toàn file (`740` dòng cũ/từ khóa hợp đồng) đều thuộc nền `dev` có sẵn trước request.

## Dev Behavior QC Card
- Auto Meta-Gate: FAIL nền (3/4 checks, 0.46s) — `doc_lint` 0 lỗi (25 file), `token_budget` 0 lỗi, `git_co_author` 0 lỗi; `i18n_check` 740 dòng đều là chú thích cũ ở `tdq_setup.py` và chuỗi hợp đồng bắt buộc ở `archify_model.py`/`skills/`, nhánh hiện tại thêm `0` dòng tiếng Việt mới.
- Luồng đổi: Từ `docs/architecture/index.html` nặng `2.62 MB` 1 tầng bị ẩn SVG sang Portal phân cấp 4 tầng (`206,297` bytes) hỗ trợ click SVG, breadcrumb, neo chu trình, tìm kiếm, `file://` fallback và `sync-master --incremental`.
- Chạy thử thật (Before → After + Bằng chứng tươi): `pytest` Q1–Q3 `202 passed, 4 skipped` (`19.39s`), Q4 `151 passed` (`31.25s`), `test_archify_logging.py` `33 passed` (`2.94s`), `smoke-e2e --changed --workers 4` `417 passed` (`118.14s`), `tdq_archify.py status` = `current`, Chrome MCP `depth=4 · console_errors=0 · file_fallback=PASS`, `tron-bo` `4,920 passed / 4 failed` (3 ca lệch version nền `dev` + 1 ca contention ở `test_tdq_simulate_verify.py` đạt `9/9` khi chạy riêng).
- Rủi ro còn lại: `build_portable.py --sinh-agy` gặp `WinError 32` do tiến trình Antigravity đang mở giữ khóa thư mục user-level `~/.gemini/config/plugins/tdq-workflow`; 4 test symlink Windows non-elevated bị skip như trước; 3 test lệch phiên bản `0.106.0` vs `0.105.0` trên `dev` chưa sửa do ngoài phạm vi request.

## Bảng kết quả DoD và QC cố định

| # | Hạng mục | Lệnh đã chạy | Kết quả | PASS/FAIL |
|---|---|---|---|---|
| Q1 | Logic Node Registry + `tree-sitter` 2 lớp + chống chu trình | `py -3 -X utf8 -m pytest tests/test_archify_registry.py -q` (và Q1–Q3 sau `0d26c4f9`) | `10 passed, 5 subtests passed` (`0.17s`), cụm Q1–Q3 `202 passed, 4 skipped` | PASS |
| Q2 | Portal HTML `< 300 KB`, 0 `onclick` SVG, `file://`, `render --type drilldown` | `py -3 -X utf8 -m pytest tests/test_archify_portal.py tests/test_archify_pipeline.py -q` + kiểm kích thước HTML | `55 passed, 7 subtests passed`; `index.html = 206,297` bytes (`< 300,000`); `0` SVG `onclick=` | PASS |
| Q3 | `--incremental`, loại `target`/`.pytest_cache`, `serve` `127.0.0.1` | `py -3 -X utf8 -m pytest tests/test_archify_artifacts.py tests/test_archify_delivery.py tests/test_tdq_archify.py -q` | `137 passed, 4 skipped` (`7.85s`, skip đều do Windows symlink non-elevated) | PASS |
| Q4 | `tree-sitter` trong `tdq_setup.py`, đồng bộ AGY, skill & `i18n` | `py -3 -X utf8 -m pytest tests/test_tdq_setup.py tests/test_agy_host_setup.py ... tests/test_sinh_agy.py -q` + `i18n_check.py` | Sau `QC1.1`: `151 passed, 203 subtests passed` (`31.25s`), `0` dòng tiếng Việt mới | PASS (ghi nhận `WinError 32` lúc `--sinh-agy` khóa thư mục IDE) |
| Q5 | Cụm Pilot 4 tầng (`>= 12` nodes) + Chrome DevTools E2E | `py -3 -X utf8 scripts/tdq_archify.py status` + kiểm `browser-e2e-audit.md` | `status=current`, `pilot_nodes=20`, `reused_ge2=3`, `cycles=2`, `depth=4 · console_errors=0 · file_fallback=PASS` | PASS |
| Q6 | Hồi quy `>= 218`, `tron-bo`, `Auto Meta-Gate`, `TDQ_LOG=1/0`, sạch `archify` | `test_archify_logging.py`, `tron-bo --workers auto --fresh --reuse off`, `tdq_meta_gate.py`, `git status` trên `archify` | `33 passed` logging; `431 passed` Archify+Setup (`362` Archify); `tron-bo` `4,920/4,961` (`3` lỗi version `dev`, `1` contention đạt `9/9` riêng); `archify` `0` sửa đổi tracked | PASS (ghi nhận 3 lỗi version nền `dev` + `i18n_check` toàn file) |
| QC-F1 | Meta-Gate + `smoke-e2e` + `tron-bo` trọn suite | `tdq_meta_gate.py`, `smoke-e2e --changed --workers 4`, `tron-bo` | `smoke-e2e`: `417 passed, 0 failed` (`118.14s`); `tdq_test so`: `tron_bo=1/3`, `bo_sot=0` | PASS (ghi nhận nền `dev` như Q6) |
| QC-F2 | Độ phủ kiểm thử từng file ở dòng `Chạm:` | Rà soát từng module thuộc `T1.1`–`T4.2` qua test file riêng | Đủ test cho cả 12 task (`0` module `KHÔNG CÓ TEST`) | PASS |
| QC-F3 | Ràng buộc kiến trúc `docs/kien-truc.md` & Spec §5 | Kiểm AST import chéo `hooks/` + rà khóa `state.json` + tách skill/script | `hooks_imports_in_scripts=[]`; không chạm `state.json`; skill chỉ gọi tên lệnh CLI | PASS |
| QC-F4 | Clean Code, SOLID, độ dài hàm `<= 50` và `TDQ_LOG=1/0` | Kiểm AST mọi hàm mới + `ruff check` + test SOLID/error fail-closed | `fn_over_50_in_new_mods=[]`; `ruff check` sạch trên 5 file mới/log | PASS |

## Bằng chứng

### Vòng QC 1 — Fix (`QC1.1`)
- Lỗi phát hiện khi chạy gộp `Q4`: `TestCLI::test_log_tat_duoc_bang_bien_moi_truong` và 2 ca `TDQ_LOG` tại `tests/test_build_portable.py` thất bại (`stderr=''`) khi chạy ngay sau `tests/test_agy_host_setup.py`. Nguyên nhân: `_isolate_agy_env` không khôi phục `TDQ_LOG` sau khi `tdq_setup.main(["--khong-log", ...])` gán `os.environ["TDQ_LOG"] = "0"`.
- Sửa tại `tests/test_agy_host_setup.py` bằng `monkeypatch.setenv("TDQ_LOG", os.environ.get("TDQ_LOG", "1"))`, tick `[x] QC1.1`, commit `0d26c4f9`. Chạy lại gộp `test_agy_host_setup.py + test_build_portable.py` đạt `50 passed, 4 subtests passed in 26.57s`.

### Q1–Q3 sau commit cuối `0d26c4f9`
```
py -3 -X utf8 -m pytest tests/test_archify_registry.py tests/test_archify_portal.py tests/test_archify_pipeline.py tests/test_archify_artifacts.py tests/test_archify_delivery.py tests/test_tdq_archify.py -q
202 passed, 4 skipped, 12 subtests passed in 19.39s
Q123_EXIT=0
```
- Kích thước & bảo mật SVG: `docs/architecture/index.html` đạt `206,297` bytes (`< 300,000`), `15` slice SVG, `svg_onclicks=[]`.

### Q4–Q6, QC-F1 và Upstream Cleanliness
```
Q4 full (7 modules): 151 passed, 203 subtests passed in 31.25s
Logging (test_archify_logging.py): 33 passed in 2.94s
Archify status: {"status": "current", "reasons": [], "manifest_path": "docs/architecture/manifest.json"}
Pilot registry: pilot_nodes=20 cycles=2 reused_ge2=3 ['arch_lsp_ladder', 'gate_deny_handler', 'gate_search_order']
smoke-e2e --changed --workers 4: 417 passed, 227 subtests passed in 104.18s (118.14s wrapper)
tron-bo --workers auto --fresh --reuse off: 4920 passed, 37 skipped, 3034 subtests passed, 4 failed in 345.56s
  - 3 pre-existing dev drift (git diff dev empty): test_codex_ban_khop_plugin_claude, test_changelog_documents_current_version, test_hai_manifest_mo_ta_giong_nhau ('0.106.0' vs '0.105.0')
  - 1 transient xdist contention: test_integration_tdq_setup_post_restart_verify_clears_pending_flag -> re-run solo PASSED (9/9 in test_tdq_simulate_verify.py)
tdq_test so: tron_bo=1/3, radius misses=0 (no vung-cham recorded because team/subagent checks replaced by direct pytest per wave)
git -C C:\Users\admin\Documents\archify status --porcelain --untracked-files=no -> "" (0 modified/staged tracked files; 7 pre-existing 2026-10-24 untracked paths untouched)
```

### QC-F2 — Bảng phủ kiểm thử vùng chạm
- `scripts/archify_registry.py` → `tests/test_archify_registry.py`, `tests/test_archify_logging.py`
- `scripts/archify_artifacts.py` → `tests/test_archify_artifacts.py`, `tests/test_archify_pipeline.py`
- `scripts/archify_delivery.py` → `tests/test_archify_delivery.py`, `tests/test_archify_logging.py`
- `scripts/tdq_setup.py` → `tests/test_tdq_setup.py`, `tests/test_agy_host_setup.py`, `tests/test_archify_logging.py`
- `scripts/archify_portal.py` → `tests/test_archify_portal.py`, `tests/test_archify_pipeline.py`, `tests/test_archify_logging.py`
- `scripts/archify_model.py` → `tests/test_archify_model.py`
- `scripts/tdq_archify.py` → `tests/test_tdq_archify.py`, `tests/test_archify_pipeline.py`, `tests/test_archify_logging.py`
- `skills/*/references/archify-*.md` & `plugins/tdq-workflow-agy/` → `tests/test_archify_workflow_contract.py`, `tests/test_archify_distribution.py`, `tests/test_build_portable.py`, `tests/test_agy_plugin_validate.py`, `tests/test_sinh_agy.py`
- `docs/architecture/` & `docs/tdq/models/registry/` → `tdq_archify.py status` (`current`) + `browser-e2e-audit.md` (`depth=4`, `console_errors=0`, `file_fallback=PASS`)

### QC-F3 & QC-F4 — Ràng buộc kiến trúc & 5 câu hỏi SOLID
- **Kiến trúc (`QC-F3`):** Kiểm tra AST xác nhận `hooks_imports_in_scripts=[]`; không module mới nào ghi `docs/tdq/state.json`; 3 file skill chỉ ghi tham chiếu lệnh CLI (`doc_lint` 0 lỗi).
- **Clean Code (`QC-F4`):** AST kiểm tra `fn_over_50_in_new_mods=[]`; `ruff check` sạch lỗi trên 5 file mới/log (`archify_registry.py`, `archify_portal.py`, `test_archify_logging.py`, `test_archify_portal.py`, `test_archify_registry.py`).
- **5 câu hỏi SOLID:**
  1. **SRP:** `archify_registry.py` tách rõ băm AST (`extract_symbol_ast_hash`), kiểm định node (`validate_logic_node`), DFS chu trình (`detect_cycles`) và đồng bộ index (`sync_registry_index`); `archify_portal.py` tách riêng gom bundle JS, dựng shell HTML `< 300 KB` và render standalone drill-down.
  2. **OCP:** Bảng `TREE_SITTER_PACKAGES` và `DEFAULT_SUB_EXTENSIONS` khai báo cấu hình theo map ngôn ngữ để mở rộng ngôn ngữ mới không phải thêm chuỗi `if/elif` vào logic băm.
  3. **LSP:** Mọi hàm fallback AST (`_extract_via_tree_sitter`, `_extract_via_python_ast`, `_fallback_file_hash`) đều trả cùng schema hash + span; `_validate_master_registry` cùng hợp đồng ngoại lệ `ValueError` với `_validate_master`.
  4. **ISP:** Mỗi hàm chỉ nhận đúng đường dẫn (`registry_dir`, `project_root`) hoặc từ điển node thay vì nhận toàn bộ `state` hay model lớn.
  5. **DIP:** `tdq_archify.py` và `tdq_setup.py` đều gọi qua điểm vào công khai của `archify_registry` và `archify_portal`, không tự sao chép logic phân tích AST hay HTML.

## Lệch spec chờ duyệt
không có (tất cả ngưỡng định lượng do spec mới đặt ra đều đạt hoặc vượt: `index.html = 206,297 < 300,000`, `362 >= 250` test Archify, `20 >= 12` Logic Nodes, `reused_by>=2 = 3 >= 2`, `depth=4`, `console_errors=0`, `file_fallback=PASS`, `0` sửa đổi `archify` upstream; các lỗi nền `dev` về phiên bản `0.106.0` vs `0.105.0` và `i18n_check` toàn file đã được tách bạch nguyên trạng).

## Kết luận
PASS toàn bộ (sau 1 vòng sửa `QC1.1`; các lỗi nền có sẵn trên `dev` và khóa `WinError 32` lúc `--sinh-agy` đã được ghi nhận rõ để báo cáo minh bạch).
