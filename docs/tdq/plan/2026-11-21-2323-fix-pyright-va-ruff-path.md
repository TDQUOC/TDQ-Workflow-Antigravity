# QUICK — Bổ sung tools/ vào Pyright và tự thêm User PATH cho công cụ Python sẵn có

**Ngày:** 2026-11-21 · Brief: ../brief/2026-11-21-2323-fix-pyright-va-ruff-path.md · Lane: quick
**Trạng thái:** HOÀN THÀNH
**Ước tính sẽ dùng skill:** tdq-intake, tdq-build

> **Tóm tắt dễ hiểu:** Trước khi sửa, công cụ dò mã Python bỏ sót thư mục công cụ hỗ trợ nên bài kiểm tra đầu phiên báo trượt giả. Ngoài ra, công cụ kiểm mã đã cài sẵn không gọi trực tiếp được vì thiếu đường dẫn người dùng. Sau khi cập nhật cấu hình quét mã và tự thêm thư mục sẵn có vào đường dẫn người dùng, cả hai kiểm tra đều chạy trơn tru.

## Phạm vi

- **Trong:** (1) Cập nhật `pyrightconfig.json` quét `tools/` (bỏ qua `plugins/`), kiểm chứng LSP thật `find_references` + `tdq_lsp.py ghi-kiem`. (2) Thêm `dam_bao_user_scripts_tren_path()` trong `scripts/tdq_checkportable.py`, nối vào `scripts/tdq_setup.py`, đồng bộ luật tự phục hồi ở `docs/claude-md-mau.md` và `scripts/tdq_setup.py`. (3) Viết `tests/test_user_scripts_path.py`, dựng lại `plugins/tdq-workflow-agy/`, kích hoạt thật `ruff --version` từ `PATH`.
- **NGOÀI:** Bỏ qua mục 3 (`eval` opt-in) và mục 4 (nợ `i18n_check` có sẵn trên `dev`). Không sửa `~/.gemini/`, `main`, `soul.md`; không tự cài gói mới hay đụng HKLM.
- **Bỏ B0:** Thư mục `scripts/`, `docs/` và `pyrightconfig.json` đã có báo cáo tiền lệ trong `docs/tdq/reports/`.
- **Bỏ B2:** Không dùng API mới ngoài stdlib (`sysconfig`, `winreg`) đã có sẵn ở `scripts/tdq_checkportable.py`.
- **Bỏ vòng chốt phạm vi:** Người dùng đã chọn rõ xử lý mục 1–2, bỏ 3–4 và đồng ý auto-add User `PATH`.

## Task

- [x] **T1** (e5m) Cập nhật `pyrightconfig.json` thêm `tools` vào `include`/`extraPaths` và `plugins` vào `exclude`; kiểm chứng `find_references` trên `tools/patches/agy_manifests.py:259` trả `N > 1` để `tdq_lsp.py ghi-kiem python:. <N>` đạt `ĐẠT` — Test: `py -3 -X utf8 -m pytest tests/test_tdq_lsp.py tests/test_build_portable.py -q` + `tdq_lsp.py ghi-kiem python:. <N>`
  - Chạm: `pyrightconfig.json`
  - Neo & Công cụ: `edit_file` trên `pyrightconfig.json` + MCP `start_lsp`, `open_document`, `find_references`
  - Trước → Sau: Pyright bỏ qua `tools/` nên `python:.` bị `TRUOT` (`1` ref) → quét đủ `tools/`, đạt `ĐẠT` (`N > 1` ref)
  - Logic: cập nhật `include`, `extraPaths` và `exclude` trong `pyrightconfig.json` → chạy LSP `find_references` và `tdq_lsp.py ghi-kiem`
  - Tiêu chí & Assert: JSON hợp lệ; `"tools"` thuộc `include` & `extraPaths`, `"plugins"` thuộc `exclude`; `tdq_lsp.py ghi-kiem python:. <N>` trả `ĐẠT`

- [x] **T2** (e15m) Thêm `dam_bao_user_scripts_tren_path()` vào `scripts/tdq_checkportable.py` (tự thêm thư mục user Scripts có sẵn binary vào `PATH` & User `PATH`, log theo `TDQ_LOG=0/1`), nối vào `scripts/tdq_setup.py`, đồng bộ câu luật tự phục hồi tại `docs/claude-md-mau.md` và `scripts/tdq_setup.py`, viết `tests/test_user_scripts_path.py` (red→green), dựng lại plugin và kích hoạt `ruff` vào `PATH` — Test: `py -3 -X utf8 -m pytest tests/test_user_scripts_path.py tests/test_claude_md_core.py tests/test_auto_update_setup.py tests/test_agy_plugin_validate.py -q`
  - Chạm: `scripts/tdq_checkportable.py`, `scripts/tdq_setup.py`, `docs/claude-md-mau.md`, `tests/test_user_scripts_path.py`
  - Neo & Công cụ: `edit_file` tại `them_thu_muc_user_path_windows()` (`tdq_checkportable.py:492`), `kiem_va_cai_shim_python3()` + `KHOI_HUONG_DAN` (`tdq_setup.py:1001,1115`), `docs/claude-md-mau.md:73`; `write_file` tạo `tests/test_user_scripts_path.py`; `tools/build_agy_plugin.py --upstream .`
  - Trước → Sau: `ruff.exe` ở `Roaming\Python\Python313\Scripts` nằm ngoài `PATH` → tự phát hiện, tự thêm User `PATH` an toàn (idempotent, tôn trọng `TDQ_KHONG_CHAM_MAY=1`), `ruff --version` chạy trực tiếp
  - Logic: tìm thư mục user Scripts chứa công cụ thực thi → thêm đầu `os.environ["PATH"]` và `HKCU\Environment\Path` → gắn vào luồng setup + cập nhật câu luật
  - Tiêu chí & Assert: Test pass (auto-add, idempotent, bỏ qua thư mục rỗng, tôn trọng `TDQ_KHONG_CHAM_MAY=1`), `claude-md-mau.md <= 12500` byte, `agy plugin validate --strict` `0` findings, `shutil.which("ruff")` khác `None` và `ruff --version` exit `0`

## Definition of Done

- **D1:** `pyrightconfig.json` quét đủ `tools/`; `find_references` cho `generate_manifest_and_readme` trả `N > 1` và `tdq_lsp.py ghi-kiem python:. <N>` đạt `ĐẠT`.
- **D2:** `tests/test_user_scripts_path.py`, `test_claude_md_core.py`, `test_auto_update_setup.py`, `test_tdq_lsp.py`, `test_agy_plugin_validate.py` pass `0` lỗi; `doc_lint.py` `0` lỗi.
- **D3:** `plugins/tdq-workflow-agy/` biên dịch sạch (`agy plugin validate --strict` `0` findings); `shutil.which("ruff")` trả đúng `ruff.exe` và `ruff --version` exit `0`.

## QC

- Q1 test từng task (`T1` + `T2`): PASS — `py -3 -X utf8 -m pytest tests/test_tdq_lsp.py tests/test_build_portable.py tests/test_user_scripts_path.py tests/test_claude_md_core.py tests/test_auto_update_setup.py tests/test_agy_plugin_validate.py -q` → `140 passed, 146 subtests passed in 19.43s`
- Q2 DoD `D1` (`pyrightconfig.json` & LSP `tools/`): PASS — MCP `find_references(tools/patches/agy_manifests.py:259)` → `symbols=2`, `tdq_lsp.py ghi-kiem python:. 2` → `python:. → DAT · 2 tham chiếu LSP`
- Q3 DoD `D2` (`tests` + `doc_lint` + `i18n` delta): PASS — `doc_lint.py` 3 tệp → `0 violation(s)`, `claude-md-mau.md` `12139 <= 12500` byte, `tdq_checkportable.py` & `tdq_setup.py` giữ `i18n_check` delta `+0`
- Q4 DoD `D3` (plugin + `ruff` trong User `PATH`): PASS — `agy plugin validate plugins/tdq-workflow-agy --strict --json` → `"findings": []`; `where.exe ruff` → `C:\Users\admin\AppData\Roaming\Python\Python313\Scripts\ruff.exe`, `ruff --version` → `ruff 0.17.3`
<!-- tdq-archify-binding:start -->
<!-- manifest: 2026-11-21-2323-fix-pyright-va-ruff-path-flow.manifest.json -->
<!-- manifest_digest: fe111592baec82f25aa798958c5a178a017680e337d6af7fa79794bf631bfbf9 -->
<!-- tdq-archify-binding:end -->