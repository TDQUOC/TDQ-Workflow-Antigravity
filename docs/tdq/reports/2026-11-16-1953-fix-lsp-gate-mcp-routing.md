# REPORT — Fix triệt để lỗi lsp_gate chặn nhầm call_mcp_tool và chuẩn hoá phân luồng MCP/LSP (`2026-11-16-1953-fix-lsp-gate-mcp-routing` · lane full · mode subagent · 15/15 task tick đủ)

Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

**Trước request (trạng thái/flow):** `hooks.json` gắn `lsp_gate.py` lên toàn bộ `call_mcp_tool`, nhưng `lsp_gate.py` chỉ rẽ nhánh `"blast_radius" in tool_name` rồi đẩy tất cả phần còn lại vào `phan_xu()` của `start_lsp`; thêm nữa `_common.py`, `search_rules.py`, `search_observe.py`, `search_replay.py` và `tools/patches/` tự kiểm lỏng `"lsp" in srv` / `"_lsp_" in tname` nên gom nhầm server ngoài (`other_lsp`), còn điều kiện `if not tool_input:` bỏ lọt `start_lsp` gửi tường minh `Arguments: {}` rỗng. Kết quả là mọi `call_mcp_tool` có tham số (`chrome-devtools -> select_page`, `click`, `navigate_page`, `tavily_search`, `find_references`) đều bị chặn oan bởi `[TDQ:LSP] start_lsp without language_id`.
**Sau request (trạng thái/flow):** Đưa toàn bộ giải gói `call_mcp_tool` / eager AGY (`_decode_json_dict`, `chuan_hoa_cong_cu_mcp`) và tập đóng `TDQ_LSP_SERVER_RE` / `_AGY_TDQ_LSP_PREFIX_RE` / `TDQ_LSP_TOOL_RE` / `ten_lenh_tdq_lsp` / `la_tool_tdq_lsp` về một nguồn thuần duy nhất tại `scripts/search_rules.py`; `_common.py` giữ cờ hiện diện tham số trong `_RUNTIME_STATE["tool_args_present"]` (`has_tool_args()`) để phân biệt thiếu khoá/JSON hỏng (fail-open) với `Arguments: {}` rỗng trên `start_lsp` (fail-closed `[TDQ:LSP]`); `lsp_gate.py` tách `_phan_xu_lenh` định tuyến chặt 3 nhánh (`start_lsp` → `phan_xu`, `blast_radius` → `phan_xu_blast_radius`, công cụ ngoài hoặc op LSP khác → `allow`), `search_observe.py` và `search_replay.py` lọc bằng `la_tool_tdq_lsp`; biên dịch sạch sang `plugins/tdq-workflow-agy/`. · **Đã làm:** P1–P5 (`T1.1`–`T5.2`; đội subagent `3/11` task `T1.1`, `T1.2`, `T2.2` trên worktree + leader `8/11` theo luật file/MCP/vùng khoá) và 4/4 task sửa vòng 1 `QC1.1`–`QC1.4` (`test_hook_windows.py` cô lập `_RUNTIME_STATE`, `agy_hooks.py` dùng `_extract_raw_tool_container`, tách `_phan_xu_lenh` đưa `lsp_gate.main()` còn `24` dòng, chuẩn hoá `search_replay.py` và chạy lại `tron-bo`).
**Đã test gì:** Unit test red→green (`test_search_rules.py`, `test_hook_windows.py`, `test_common.py`, `test_search_observe.py`, `test_search_replay.py`, `test_lsp_gate.py`, `test_agy_hooks.py`, `test_kenh_luat_dedupe.py`, `test_prompt_context.py`, `test_reminder_contract.py`), E2E dual-protocol `cmd /c py -3` + tương thích `chrome-devtools` (`test_hooks_dual_protocol.py`, `test_cli_fixes_new01_28.py`, `chrome-devtools-smoke.md`), biên dịch `tools/build_agy_plugin.py` + `agy.EXE plugin validate --strict --json`, linter (`ruff`, `doc_lint.py`, `i18n_check.py`, `token_budget.py`, kiểm AST ranh giới import & độ phức tạp `C901`), trọn bộ `scripts/tdq_test.py tron-bo` và 2 vòng kiểm chứng độc lập bởi `tdq-qc-tester` (`muc_qc = ultra`).
**Kết quả test:** Q1 (`test_lsp_gate` + `test_hooks_dual_protocol`) `21 passed in 8.80s` (`main=24` dòng) · Q2 (`test_search_rules`, `test_search_observe`, `test_hook_windows`, `test_cli_fixes_new01_28`, `test_common`, `test_search_replay`) `171 passed, 68 subtests passed in 9.58s` và `test_agy_hooks.py` `29 passed in 3.95s` · cô lập tiến trình 4 file hook `81 passed, 168 subtests passed in 15.52s` · Q3 (`payload_hong or duoi_200ms`) `2 passed` + 5x probe `TDQ_LOG=0` `[68.48, 69.68, 67.92, 66.23, 67.68] ms` (min `66.23 ms <= 200 ms`, từ chối oan `4/5 -> 0/5`) · Q4 `build_agy_plugin` `status=OK` (`ast_checked_py=81`), `agy plugin validate` `"findings": []`, bản cài cục bộ `3b` nguyên vẹn (`bf3788315fad != d47677fb59ae`) · Q5 trọn bộ `scripts/tdq_test.py tron-bo` `4246` cases collected, `4246 passed` (`35 skipped`, `0 failed` trong `948.55s`, `status=PASS`, `bo_sot=0`) · `ruff F,B` & `C901 <= 10` hàm mới sạch, `i18n_check` 6 file cốt lõi `0` dòng Việt, `token_budget` exit `0`, `doc_lint` 0 vi phạm · `tdq-qc-tester` Vòng 2: `PASS 5/5` DoD + `4/4` fixed items (`VERDICT: PASS everything`).
**Đầu ra:** `scripts/search_rules.py` · `scripts/search_replay.py` · `hooks/scripts/_common.py` · `hooks/scripts/lsp_gate.py` · `hooks/scripts/search_observe.py` · `tools/patches/cli_fixes_a.py` · `tools/patches/agy_hooks.py` · `plugins/tdq-workflow-agy/` · `tests/{test_search_rules,test_hook_windows,test_search_observe,test_search_replay,test_lsp_gate,test_hooks_dual_protocol,test_cli_fixes_new01_28}.py` · `docs/tdq/artifacts/2026-11-16-1953-fix-lsp-gate-mcp-routing/chrome-devtools-smoke.md` · **Archify HTML:** `docs/tdq/reports/2026-11-16-1953-fix-lsp-gate-mcp-routing.html` · Backup: không có
**Giới hạn:** Request mở qua `--bo-qua-lsp` tại pha `analyze` (`module`: `python:. → TRUOT (generate_manifest_and_readme: 1 tham chiếu LSP so với 1 lần trong file định nghĩa — LSP không thấy tham chiếu từ file khác)`, `ly_do`: `pyrightconfig.json chỉ include scripts/hooks/tests nên symbol mẫu ở tools/patches/agy_manifests.py trả symbols=1; LSP Python trên scripts/hooks/tests đã xác nhận hoạt động`) · Theo lựa chọn `3b`, bản cài plugin cục bộ tại `C:/Users/admin/.gemini/config/plugins/tdq-workflow-agy` chưa bị ghi đè nên thao tác runtime từ plugin cài đặt vẫn giữ hành vi cũ cho tới khi user commit/release & cập nhật local · Khi chạy trọn bộ với `scripts/tdq_test.py` (dài `948.55s` với `--workers 1`, cần `--timeout 1800`; nếu gọi nhầm qua `plugins/tdq-workflow-agy/scripts/tdq_test.py` sẽ làm lệch `PYTHONPATH` của `--worker` trong `test_tdq_test_receipt.py`) · `scripts/search_replay.py` còn 2 comment tiếng Việt cũ ngoài phạm vi thay đổi tại dòng `167` và `209` (giữ nguyên theo nguyên tắc bảo toàn comment không liên quan) · `radius_complete=false` trong `tdq_test.py so` do một lượt `vung-cham` trước khi phát hiện khác biệt `PYTHONPATH` bị fail 8 ca `test_tdq_test_receipt.py` · `eval: chưa kích hoạt (opt-in)`.
**Lệch spec chờ duyệt:** không có
**Git:** Nhánh `bugfix/fix-lsp-gate-mcp-routing` (gốc `dev`) đã gộp 3 cụm commit từ worktree `T1.1`, `T1.2`, `T2.2` (`35eb9509`, `a76e5175`, `e4d20dd0`, `68cfb9f5`, `644a1017`, `b30cc0bd`), các thay đổi còn lại (`hooks/scripts/`, `scripts/search_replay.py`, `tools/patches/agy_hooks.py`, `plugins/tdq-workflow-agy/`, `tests/`, `docs/`) nằm tại working tree chờ user xác nhận commit.

## Thời gian

Request `2026-11-16-1953-fix-lsp-gate-mcp-routing` · lane full · opened at 2026-11-16T19:54:53+07:00

| Phase | Wall clock | API request | Tool wait | Background job | Observed union | Unattributed | Times entered |
|---|---|---|---|---|---|---|---|
| idle | 1s | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | 1 |
| analyze | 19 min | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | 1 |
| spec | 20 min | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | 1 |
| plan | 1h 25min | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | 1 |
| mode | 1h 32min | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | 1 |
| implement | 1h 37min | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | 1 |
| qc | 1h 26min | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | 1 |
| report | 1s | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | 1 |
| Total | 6h 41min | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] |  |

Model compute time is unavailable (`model_giay=null`). API includes network/provider latency; tool time is host wait. Observed metrics may overlap; unattributed time is not assumed user/model time.
Transcript attribution: project_window. Complete covers selected supported observations only.
- api_request_seconds: no_usable_source
- tool_call_seconds: no_usable_source
- background_job_seconds: no_usable_source
- observed_union_seconds: no_usable_observations
- unattributed_seconds: wall_minus_observed_union;no_usable_observations

## Thân PR (soạn sẵn)

**Tóm tắt:** Chuẩn hoá logic giải gói `call_mcp_tool` / eager Antigravity và bộ nhận diện chặt TDQ LSP (`TDQ_LSP_SERVER_RE`, `TDQ_LSP_TOOL_RE`) về một nguồn thuần tại `scripts/search_rules.py`, dùng chung tại `_common.py`, `lsp_gate.py`, `search_observe.py`, `search_replay.py` và `tools/patches/{cli_fixes_a,agy_hooks}.py`; rẽ chặt 3 nhánh trong `lsp_gate.py` và phân biệt payload thiếu khoá (fail-open) với `start_lsp` gửi `Arguments: {}` rỗng tường minh (fail-closed `[TDQ:LSP]`).
**Trước/Sau:** `docs/tdq/spec/2026-11-16-1953-fix-lsp-gate-mcp-routing-preview.html` và `docs/tdq/reports/2026-11-16-1953-fix-lsp-gate-mcp-routing.html`.
**Đã kiểm:**
- `py -3 -X utf8 -m pytest tests/test_lsp_gate.py tests/test_hooks_dual_protocol.py -q`: 21 passed in 8.80s
- `py -3 -X utf8 -m pytest tests/test_search_rules.py tests/test_search_observe.py tests/test_hook_windows.py tests/test_cli_fixes_new01_28.py tests/test_common.py tests/test_search_replay.py -q`: 171 passed, 68 subtests passed in 9.58s
- `py -3 -X utf8 -m pytest tests/test_agy_hooks.py -q`: 29 passed in 3.95s
- `py -3 -X utf8 tools/build_agy_plugin.py` + `agy.EXE plugin validate --strict --json plugins/tdq-workflow-agy`: `status=OK`, `findings=[]`
- `py -3 -X utf8 scripts/tdq_test.py tron-bo --workers 1 --fresh --reuse off --timeout 1800`: 4246 collected, 4246 passed (35 skipped, 0 failed) in 948.55s (`status=PASS`)
- `tdq-qc-tester` Vòng 2 (`muc_qc = ultra`): `VERDICT: PASS everything` (0 defects)
**Rủi ro hồi quy:** Thấp — matcher `hooks.json` giữ nguyên để không bỏ lọt `call_mcp_tool`, fail-open khi thiếu khoá hoặc JSON hỏng vẫn được giữ nguyên qua `test_common.py` và `test_lsp_gate.py` (`payload_hong`), toàn bộ hàm mới đều đạt `C901 <= 10` và độ trễ hook đo thực tế `66.23–69.68 ms <= 200 ms`.
<!-- tdq-archify-binding:start -->
<!-- manifest: 2026-11-16-1953-fix-lsp-gate-mcp-routing.manifest.json -->
<!-- manifest_digest: f0c5a6392dc8f734683b64205aa75c88f3edb7a3526ff64ad345445e1d32d503 -->
<!-- tdq-archify-binding:end -->