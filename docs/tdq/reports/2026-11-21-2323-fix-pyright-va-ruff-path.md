# BÁO CÁO — Bổ sung tools/ vào Pyright và tự thêm User PATH cho ruff

Ngày: 2026-11-21 · Mã yêu cầu: 2026-11-21-2323-fix-pyright-va-ruff-path (2 task tick đủ)
Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

> **Tóm tắt dễ hiểu:** Trước khi sửa, công cụ dò mã Python bỏ sót thư mục công cụ hỗ trợ nên bài kiểm tra đầu phiên báo trượt giả. Ngoài ra, công cụ kiểm mã đã cài sẵn không gọi trực tiếp được vì nằm ngoài đường dẫn người dùng. Sau khi cập nhật cấu hình quét mã và tự nạp thư mục công cụ sẵn có vào đường dẫn người dùng, cả hai giới hạn đều đã thông và chạy trực tiếp.

## 1. Trước request (trạng thái/flow)

Trước khi sửa, `pyrightconfig.json` chỉ liệt kê `scripts`, `hooks` và `tests` trong `include`, nên khi kịch bản kiểm tra LSP chọn biểu tượng `generate_manifest_and_readme` thuộc `tools/patches/`, Pyright chỉ thấy 1 tham chiếu nội tệp và kết luận `python:. → TRUOT`. Song song đó, `ruff.exe` (`0.17.3`) đã cài ở `C:\Users\admin\AppData\Roaming\Python\Python313\Scripts\ruff.exe`, nhưng cơ chế tự sửa môi trường mới kiểm tra shim `python3` chứ chưa tự động thêm thư mục Scripts mức người dùng vào User `PATH`.

## 2. Sau request (trạng thái/flow)

Hai điểm nghẽn đã được xử lý triệt để theo quyền người dùng mà không cài thêm gói ngoài:

- **T1 (`pyrightconfig.json`):** Bổ sung `tools` vào cả `include` và `extraPaths`, đồng thời thêm `plugins` vào `exclude` để Pyright quét đủ `tools/` nhưng không đếm trùng bản biên dịch. Kết quả kiểm tra thực tế `find_references` trên `tools/patches/agy_manifests.py:259` trả `symbols=2` và `tdq_lsp.py ghi-kiem python:. 2` đạt `ĐẠT`.
- **T2 (tự thêm User `PATH` cho công cụ Scripts người dùng):** Bổ sung `dam_bao_user_scripts_tren_path()` (và các hàm kiểm tra phụ `_thu_muc_user_scripts_mac_dinh`, `_co_binary_thuc_thi`, `_co_nam_trong_path`, `_la_thu_muc_bo_qua`, `_broadcast_env_change_windows`) vào `scripts/tdq_checkportable.py`. Khi tồn tại thư mục Scripts/bin mức người dùng có công cụ thực thi (như `ruff.exe`) mà chưa nằm trong `PATH`, hàm tự thêm vào `os.environ["PATH"]` và `HKCU\Environment\Path`, bỏ qua thư mục rỗng, chỉ có file văn bản, `WindowsApps` hoặc thư mục tạm (`Temp`/`fnm_multishells`), tôn trọng `TDQ_LOG=0/1` và `TDQ_KHONG_CHAM_MAY=1`.
- **Tích hợp & đồng bộ luật:** Gắn `kiem_va_them_user_scripts_path()` vào `kiem_va_cai_shim_python3()` trong `scripts/tdq_setup.py`, đồng bộ câu luật tự phục hồi tại `docs/claude-md-mau.md` (`12139 <= 12500` byte) cùng `scripts/tdq_setup.py`, kích hoạt thật cho `C:\Users\admin\AppData\Roaming\Python\Python313\Scripts` và đóng gói lại `plugins/tdq-workflow-agy/`.

## 3. Đã test gì

- Chạy kiểm thử đơn vị mới `tests/test_user_scripts_path.py` (từ RED 6 fail sang GREEN) kết hợp `tests/test_tdq_lsp.py`, `tests/test_build_portable.py`, `tests/test_claude_md_core.py`, `tests/test_auto_update_setup.py`, `tests/test_agy_plugin_validate.py`, `tests/test_tdq_setup.py`, `tests/test_auto_fix_python3_hook.py`, `tests/test_shim_python3.py`.
- Chạy chứng minh LSP thực tế qua `tdq-workflow-agy_lsp` (`start_lsp`, `open_document`, `find_references` tại `tools/patches/agy_manifests.py:259`) và `tdq_lsp.py ghi-kiem python:. 2`.
- Kiểm `doc_lint.py` trên `docs/claude-md-mau.md`, `brief`, `plan`, kiểm delta `i18n_check.py` so với `dev` trên `tdq_checkportable.py` và `tdq_setup.py`, dựng plugin `tools/build_agy_plugin.py --upstream .` + `agy plugin validate --strict --json`, và thử thực tế `dam_bao_user_scripts_tren_path()` 2 lần (lần đầu cập nhật Registry + lần 2 xác nhận idempotent), `where.exe ruff` và `ruff --version` với `PATH` nạp từ Registry.

## 4. Kết quả test

Toàn bộ hạng mục QC `Q1`–`Q4` cho `2` task và `3` tiêu chí DoD trong [mini-plan](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/plan/2026-11-21-2323-fix-pyright-va-ruff-path.md) đều đạt `PASS`:

- **QC `Q1` (test từng task sau lần sửa cuối):** `py -3 -X utf8 -m pytest tests/test_tdq_lsp.py tests/test_build_portable.py tests/test_user_scripts_path.py tests/test_claude_md_core.py tests/test_auto_update_setup.py tests/test_agy_plugin_validate.py -q` → `140 passed, 146 subtests passed in 19.43s`. (Lần chạy trước đó thêm `test_tdq_setup.py`, `test_auto_fix_python3_hook.py`, `test_shim_python3.py` đạt `202 passed, 174 subtests passed in 16.02s`.)
- **QC `Q2` (D1 — Pyright `tools/` & LSP):** `find_references` trên `generate_manifest_and_readme` trả `symbols=2`, `tdq_lsp.py ghi-kiem python:. 2` → `python:. → DAT · 2 tham chiếu LSP so với 1 lần trong file định nghĩa`.
- **QC `Q3` (D2 — lint, byte cap & `i18n`):** `doc_lint.py` sạch `0 violation(s)`; `docs/claude-md-mau.md` dài `12139 <= 12500` byte; `tdq_checkportable.py` (`22 → 22`) và `tdq_setup.py` (`324 → 324`) đều giữ `delta = +0` so với `dev`.
- **QC `Q4` (D3 — plugin & `ruff` thực tế):** `tools/build_agy_plugin.py` trả `"status": "OK"`, `agy plugin validate plugins/tdq-workflow-agy --strict --json` trả `"findings": []`; lần chạy thật trả `added C:\Users\admin\AppData\Roaming\Python\Python313\Scripts to User PATH`, chạy lại trả `([], [])`, `HKCU\Environment\Path` có sẵn đường dẫn, `where.exe ruff` → `C:\Users\admin\AppData\Roaming\Python\Python313\Scripts\ruff.exe`, `ruff --version` → `ruff 0.17.3`.

## Đầu ra & Giao thức Git

- **Đầu ra chính:** `pyrightconfig.json`, `scripts/tdq_checkportable.py`, `scripts/tdq_setup.py`, `docs/claude-md-mau.md`, `tests/test_user_scripts_path.py`, bản dựng đồng bộ `plugins/tdq-workflow-agy/`, cùng `brief`, `plan` và `report` của request `2026-11-21-2323-fix-pyright-va-ruff-path`.
- **Archify HTML:** `docs/tdq/reports/2026-11-21-2323-fix-pyright-va-ruff-path.html` (và bản luồng Trước/Sau tại `docs/tdq/plan/2026-11-21-2323-fix-pyright-va-ruff-path-flow.html`).
- **Git:** Đang làm việc trên nhánh `chore/fix-pyright-va-ruff-path` tách từ `dev`, chưa commit cuối và sẽ gộp về `dev` khi bạn đồng ý commit.

## Thời gian

```text
Request `2026-11-21-2323-fix-pyright-va-ruff-path` · lane quick · opened at 2026-11-21T23:40:42+07:00

| Phase | Wall clock | Times entered |
|---|---|---|
| idle | 0s | 1 |
| analyze | 4 min | 1 |
| implement | 6 min | 1 |
| report | 1s | 1 |
| Total | 11 min |  |

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

- **Cổng LSP mở đầu (`lsp_bo_qua` từ `docs/tdq/state.json`):** `{"ly_do": "LSP module python:. dang TRUOT chinh vi pyrightconfig.json chua bao gom tools/ — day la loi duoc sua trong chinh request nay", "at": "2026-11-21T23:40:27+07:00", "module": ["python:. → CHUA_KIEM (chưa chạy kịch bản)", "rust:hooks/rust/tdq-dispatch → CHUA_KIEM (chưa chạy kịch bản)"]}`. Sau khi hoàn thành `T1`, module `python:.` đã được chạy lại `find_references` và ghi kết quả `ĐẠT` (`2` tham chiếu); mô-đun `rust:hooks/rust/tdq-dispatch` không đụng mã Rust nên không chạy lại kịch bản ở request này.
- **Mục 3 và mục 4:** Bỏ qua có chủ đích theo yêu cầu trực tiếp của người dùng (`eval` opt-in giữ tắt, nợ `i18n_check` cũ trên nhánh `dev` giữ nguyên).
- **Cảnh báo phiên shell cũ:** Các shell đã mở *trước* thời điểm ghi `HKCU\Environment\Path` cần mở shell mới hoặc nạp lại biến `Path` từ Registry mới thấy `ruff`.

## Lệch spec chờ duyệt

không có

## Thân PR (soạn sẵn)

**Tóm tắt:** Bổ sung `tools/` vào phạm vi `pyrightconfig.json` (loại trừ `plugins/`) giúp Python LSP kiểm đạt module `python:.` với `2` tham chiếu thật, đồng thời thêm cơ chế tự động thêm thư mục Scripts/bin mức người dùng có sẵn công cụ thực thi vào User `PATH` (`dam_bao_user_scripts_tren_path`).

**Trước/Sau:** Xem luồng Trước/Sau ở `docs/tdq/plan/2026-11-21-2323-fix-pyright-va-ruff-path-flow.html` và báo cáo ở `docs/tdq/reports/2026-11-21-2323-fix-pyright-va-ruff-path.html`.

**Đã kiểm:**
- `py -3 -X utf8 -m pytest tests/test_tdq_lsp.py tests/test_build_portable.py tests/test_user_scripts_path.py tests/test_claude_md_core.py tests/test_auto_update_setup.py tests/test_agy_plugin_validate.py -q` → `140 passed, 146 subtests passed in 19.43s`
- LSP `find_references(tools/patches/agy_manifests.py:259)` → `symbols=2`, `tdq_lsp.py ghi-kiem python:. 2` → `DAT`
- `agy plugin validate plugins/tdq-workflow-agy --strict --json` → `"findings": []`
- `ruff --version` từ User `PATH` → `ruff 0.17.3`

**Rủi ro hồi quy:** Thay đổi ở `tdq_checkportable.py` và `tdq_setup.py` chạm nhánh tự động sửa môi trường Windows và bản mẫu `KHOI_HUONG_DAN`; đã giữ bảo vệ `TDQ_KHONG_CHAM_MAY=1` và kiểm sạch `test_claude_md_core.py`, `test_auto_update_setup.py`, `test_shim_python3.py` cùng `test_user_scripts_path.py`.
<!-- tdq-archify-binding:start -->
<!-- manifest: 2026-11-21-2323-fix-pyright-va-ruff-path.manifest.json -->
<!-- manifest_digest: 9695a0b589c9cc489d287adab9d0fe529383f74662ebc904c435ad35338b4dd9 -->
<!-- tdq-archify-binding:end -->