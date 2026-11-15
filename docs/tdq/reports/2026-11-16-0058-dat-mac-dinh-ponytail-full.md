# REPORT — Đặt lại mặc định mức gắt Ponytail (muc_gat) về full (`2026-11-16-0058-dat-mac-dinh-ponytail-full` · lane quick · mode inline · 2 task tick đủ)

Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

**Trước request (trạng thái/flow):** Từ commit `cf2389f5` (`0.85.1`), hằng mặc định và mức dự phòng fail-closed của luật tinh gọn Ponytail (`muc_gat`) bị đặt ở `ultra` trong `scripts/tdq_state.py`, `hooks/scripts/luat_gon.py` và bảng cường độ `skills/tdq-build/references/rules/chung.md`, khiến mọi phiên mới đều nạp ví dụ dài và bắt buộc khai báo bậc thang trên từng tạo mới.
**Sau request (trạng thái/flow):** Mặc định và fallback `muc_gat` được đưa về lại `full` đồng bộ trên mã nguồn gốc, khóa `docs/tdq/token-budget.json`, bản biên dịch `plugins/tdq-workflow-agy/` và bản cài người dùng `~/.gemini/config/plugins/tdq-workflow-agy`; giữ nguyên các mức đặt tường minh `lite|full|ultra|off` và `muc_qc = full`; thang 7 bậc dừng ở bậc 2 (sửa hằng và bảng đã có sẵn). · **Đã làm:** T1 (đổi mặc định/fallback và unit test `tdq_state.py`, `luat_gon.py`) · T2 (cập nhật `chung.md`, tái tạo khóa token, biên dịch & đồng bộ plugin AGY).
**Đã test gì:** Unit test red→green (`tests.test_state_muc_gat`, `tests.test_luat_gon`, `tests.test_state_muc_qc`), test hồi quy thư viện luật & context hooks (`tests.test_rules_library`, `tests.test_context_hooks`), lint Python `ruff` (`--select F,E,B --ignore E501`), linter `doc_lint.py`, kiểm khóa `token_budget.py --kiem`, kiểm đồng bộ plugin AGY tại repo và `~/.gemini/config/plugins/tdq-workflow-agy`.
**Kết quả test:** 38/38 unit test `muc_gat`/`luat_gon`/`muc_qc` PASS (2.192s · `default_muc_gat=full`) · 54/54 hồi quy `test_rules_library` + `test_context_hooks` PASS (11.929s) · `ruff` nhóm F/E/B (bỏ qua E501 sẵn có) sạch 0 lỗi · `doc_lint.py` 0 vi phạm (`exit 0`) · `token_budget.py --kiem` 62 file sạch `exit 0` · plugin AGY `SYNC_OK` · **Kiểm:** QC mức `full` PASS 4/4 mục Q1–Q4.
**Đầu ra:** `scripts/tdq_state.py` · `hooks/scripts/luat_gon.py` · `skills/tdq-build/references/rules/chung.md` · `docs/tdq/token-budget.json` · `tests/test_state_muc_gat.py` · `tests/test_luat_gon.py` · `plugins/tdq-workflow-agy/` (đồng bộ sang `~/.gemini/config/plugins/tdq-workflow-agy`, 186 file) · **Archify HTML:** `docs/tdq/reports/2026-11-16-0058-dat-mac-dinh-ponytail-full.html` · Backup: không có
**Giới hạn:** Request mở qua `--bo-qua-lsp` (`module`: `python:. → TRUOT (generate_manifest_and_readme: 1 tham chiếu LSP so với 1 lần trong file định nghĩa)`, `ly_do`: `pyrightconfig.json chỉ include scripts/hooks/tests nên symbol mẫu ở tools/patches/agy_manifests.py trả symbols=1; LSP Python trên scripts/hooks/tests đã xác nhận hoạt động (symbols=4 và symbols=12)`) · Sinh khóa token dùng `TDQ_TOKENS_VENV=C:\Users\admin\Documents\Projects\ForAgentCode\TDQ-Workflow\.venv-tokens\Scripts\python.exe` · `ruff` mặc định chưa bật `E501` trên file có sẵn dài >88 ký tự · eval: chưa kích hoạt (opt-in).
**Lệch spec chờ duyệt:** không có
**Git:** Nhánh `chore/dat-mac-dinh-ponytail-full` (gốc `dev`) giữ thay đổi chưa commit, chờ xác nhận từ người dùng.

## Thời gian

Request `2026-11-16-0058-dat-mac-dinh-ponytail-full` · lane quick · opened at 2026-11-16T01:11:41+07:00

| Phase | Wall clock | API request | Tool wait | Background job | Observed union | Unattributed | Times entered |
|---|---|---|---|---|---|---|---|
| idle | 1s | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | 1 |
| analyze | 12 min | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | 1 |
| implement | 3 min | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | 1 |
| report | 0s | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | 1 |
| Total | 15 min | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] |  |

Model compute time is unavailable (`model_giay=null`). API includes network/provider latency; tool time is host wait. Observed metrics may overlap; unattributed time is not assumed user/model time.
Transcript attribution: project_window. Complete covers selected supported observations only.
- api_request_seconds: no_usable_source
- tool_call_seconds: no_usable_source
- background_job_seconds: no_usable_source
- observed_union_seconds: no_usable_observations
- unattributed_seconds: wall_minus_observed_union;no_usable_observations

## Thân PR (soạn sẵn)

**Tóm tắt:** Đưa mặc định và mức dự phòng fail-closed của luật tinh gọn Ponytail (`muc_gat`) từ `ultra` trở về `full` trong `tdq_state.py`, `luat_gon.py` và `chung.md`, đồng thời tái tạo khóa token và biên dịch đồng bộ plugin Antigravity.
**Trước/Sau:** `docs/tdq/plan/2026-11-16-0058-dat-mac-dinh-ponytail-full-flow.html` và `docs/tdq/reports/2026-11-16-0058-dat-mac-dinh-ponytail-full.html`.
**Đã kiểm:**
- `PYTHONPATH=tests py -3 -m unittest tests.test_state_muc_gat tests.test_luat_gon tests.test_state_muc_qc`: 38 passed in 2.192s
- `PYTHONPATH=tests py -3 -m unittest tests.test_rules_library tests.test_context_hooks`: 54 passed in 11.929s
- `py -3 -X utf8 scripts/doc_lint.py skills/tdq-build/references/rules/chung.md` và `py -3 -X utf8 scripts/token_budget.py --kiem`: exit 0 (62 file, cap 3500)
- Kiểm đồng bộ `plugins/tdq-workflow-agy/` & `~/.gemini/config/plugins/tdq-workflow-agy`: `SYNC_OK`
**Rủi ro hồi quy:** Thấp — chỉ đổi giá trị mặc định/fallback `muc_gat` sang `full`; bốn mức tường minh `lite|full|ultra|off` và mặc định `muc_qc=full` được giữ độc lập qua `test_state_muc_gat` và `test_state_muc_qc`.
<!-- tdq-archify-binding:start -->
<!-- manifest: 2026-11-16-0058-dat-mac-dinh-ponytail-full.manifest.json -->
<!-- manifest_digest: d23c3ad02a834252ebc9fc0aea9d0c2f372678f59523f484ff86784afe7f8d87 -->
<!-- tdq-archify-binding:end -->