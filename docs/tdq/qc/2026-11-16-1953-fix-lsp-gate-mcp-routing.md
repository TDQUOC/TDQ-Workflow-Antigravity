# QC — Fix triệt để lỗi lsp_gate chặn nhầm call_mcp_tool và chuẩn hoá phân luồng MCP/LSP
Ngày: 2026-11-17 · Plan: ../plan/2026-11-16-1953-fix-lsp-gate-mcp-routing.md · Vòng: 2 (`muc_qc = ultra` · `tdq-qc-tester` 2 vòng)
Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

| # | Hạng mục | Lệnh đã chạy | Kết quả | PASS/FAIL |
|---|---|---|---|---|
| Q1 | Định tuyến `lsp_gate.py` & rút gọn `main()` (`QC1.3`) | `py -3 -X utf8 -m pytest tests/test_lsp_gate.py tests/test_hooks_dual_protocol.py -q` + 6x AGY probe | `21 passed in 8.80s`; `main=24` dòng / `_phan_xu_lenh=15` dòng; 6/6 probe khớp (`chrome-devtools`/`tavily`/`find_references`/`other_lsp` = `allow`, `start_lsp` `{}` = `deny`) | PASS |
| Q2 | Hợp nhất `search_rules.py` & `QC1.1`/`QC1.2`/`QC1.3` | `py -3 -X utf8 -m pytest tests/test_search_rules.py tests/test_search_observe.py tests/test_hook_windows.py tests/test_cli_fixes_new01_28.py tests/test_common.py tests/test_search_replay.py -q` + edge `COMMON_PY` | `171 passed, 68 subtests passed in 9.58s`; `29 passed` (`test_agy_hooks.py`); `81 passed, 168 subtests` cô lập `_RUNTIME_STATE`; `COMMON_PY` `tool_input=None` fallback `toolCall.args` đạt `True` | PASS |
| Q3 | Fail-open thiếu khoá / JSON hỏng & độ trễ `<= 200 ms` | `py -3 -X utf8 -m pytest tests/test_lsp_gate.py -k "payload_hong or duoi_200ms" -q` + 5x probe `TDQ_LOG=0` | `2 passed, 15 deselected in 0.55s`; 5 lần đo thực tế `[68.48, 69.68, 67.92, 66.23, 67.68] ms` (min `66.23 ms <= 200 ms`, `decisions: {'allow'}`) | PASS |
| Q4 | Biên dịch `plugins/tdq-workflow-agy/`, `agy validate`, giữ local `3b` | `py -3 -X utf8 tools/build_agy_plugin.py` + `agy.EXE plugin validate --strict --json plugins/tdq-workflow-agy` + kiểm `3b` | `status: OK` (`ast_checked_py: 81`, `md_checked_budget: 22`); `"findings": []`; `BYTE_DIFFS=[]`; bản cài cục bộ `bf3788315fad` còn nguyên chưa ghi đè (`repo_built=d47677fb59ae`) | PASS |
| Q5 | Thuần I/O, linter (`ruff`/`doc_lint`/`i18n`/`token_budget`), `tron-bo`, QC `ultra` | `py -3 -X utf8 scripts/tdq_test.py tron-bo --workers 1 --fresh --reuse off --timeout 1800` + linter + `tdq-qc-tester` Vòng 2 | `4246` tests collected, `4246 passed` (`35 skipped`, `0 failed` in `948.55s`); `ruff F,B` 0 lỗi; `i18n_check` 0 dòng ở 6 file cốt lõi; `token_budget` exit 0; `tdq-qc-tester` Vòng 2: `VERDICT: PASS everything` | PASS |
| QC-F1 | Trọn bộ `tron-bo` & `tdq_test.py so` sau lần sửa cuối (`QC1.4`) | `py -3 -X utf8 scripts/tdq_test.py tron-bo --workers 1 --fresh --reuse off --timeout 1800` + `scripts/tdq_test.py so --json` | `status=PASS`, `tests_run=4246`, `skipped=35`, `details_complete=True`; `tron_bo=4`, `bo_sot=0` (`radius_complete=false` do một phần `vung-cham` trước đó INCOMPLETE/timeout); `result.json` sha256 `60e28583…` | PASS |
| QC-F2 | Hồi quy vùng chạm & kiểm hợp đồng skill §3b | `tdq_test.py vung-cham --files ... --khong-ep-tron-bo` + kiểm `chrome-devtools-smoke.md` | `180 passed` (`20.28s`, `tdq-qc-tester`); `chrome-devtools-smoke.md` tồn tại đủ `allow` và `select_page` (`0` mục `KHÔNG CÓ TEST`) | PASS |
| QC-F3 | Ràng buộc kiến trúc (spec §5) | Kiểm tra AST import `scripts/` vs `hooks/` vs `tests/`, `doc_lint.py` | `Arch import boundaries OK (scripts & hooks clean)`; ngôn ngữ log tiếng Anh đạt; chỉ sửa gốc + `tools/patches/` rồi biên dịch `plugins/tdq-workflow-agy/` | PASS |
| QC-F4 | Clean Code Invariants (`clean-code.md` Self-check + McCabe `C901`) | `py -3 -X utf8 -m ruff check --select C901 --config "lint.mccabe.max-complexity=10"` trên các hàm mới/sửa | 5/5 câu trả lời ĐẠT (`C901 <= 10` cho mọi hàm mới/tách; không thêm dư thừa; lỗi fail-open/closed bảo toàn; đủ test) | PASS |

## Lịch sử 2 vòng QC (`muc_qc = ultra`)

- **Vòng 1 (`tdq-qc-tester`):** `Q1`–`Q4` PASS, `Q5` FAIL (3 khuyết điểm: `COMMON_PY` chưa dùng `_extract_raw_tool_container`, `lsp_gate.py:main()` 40 dòng vượt trần 35, `scripts/search_replay.py` dòng 183 còn `"lsp" in name.lower()`, cùng biên nhận `tron-bo` timeout tại `900s`) và lỗi rò `_RUNTIME_STATE["is_agy"] = True` ở `TestCommonMcpNormalization`.
- **Sửa vòng 1 (`QC1.1`–`QC1.4`):** Cô lập `_common._RUNTIME_STATE` (`tests/test_hook_windows.py`), đồng bộ `_extract_raw_tool_container` vào `tools/patches/agy_hooks.py`, tách `_phan_xu_lenh` đưa `lsp_gate.main()` xuống `24` dòng, chuyển `scripts/search_replay.py` sang `chuan_hoa_cong_cu_mcp` + `la_tool_tdq_lsp`, biên dịch lại plugin và chạy `scripts/tdq_test.py tron-bo --timeout 1800` đạt `4246` passed (`0` fail).
- **Vòng 2 (`tdq-qc-tester`):** Kiểm chứng độc lập toàn bộ `QC1.1`–`QC1.4` và `Q1`–`Q5`, chạy `180` test `vung-cham` (`20.28s`), đối chiếu hash biên dịch, xác nhận `DEFECTS: (không có)` và kết luận **`VERDICT: PASS everything`**.

## Bằng chứng

### Q1
```
py -3 -X utf8 -m pytest tests/test_lsp_gate.py tests/test_hooks_dual_protocol.py -q
.....................                                                    [100%]
21 passed in 8.80s
hooks/scripts/lsp_gate.py:_phan_xu_lenh cc=6 lines=15
hooks/scripts/lsp_gate.py:main cc=8 lines=24
```

### Q2
```
py -3 -X utf8 -m pytest tests/test_search_rules.py tests/test_search_observe.py tests/test_hook_windows.py tests/test_cli_fixes_new01_28.py tests/test_common.py tests/test_search_replay.py -q
171 passed, 68 subtests passed in 9.58s
py -3 -X utf8 -m pytest tests/test_agy_hooks.py -q
29 passed in 3.95s
COMMON_PY edge OK: mcp__chrome-devtools__select_page True
```

### Q3
```
py -3 -X utf8 -m pytest tests/test_lsp_gate.py -k "payload_hong or duoi_200ms" -q
2 passed, 15 deselected in 0.55s
latencies ms: [68.48, 69.68, 67.92, 66.23, 67.68] min: 66.23 decisions: {'allow'}
```

### Q4
```json
{
  "output": "...\\plugins\\tdq-workflow-agy",
  "ast_checked_py": 81,
  "md_checked_budget": 22,
  "status": "OK"
}
agy validate: "findings": []
3b intact: local= bf3788315fad repo_built= d47677fb59ae
```

### Q5 & QC-F1
```
[2026-11-17T02:28:43+07:00] tdq_test: tron-bo backend=pytest scope=full status=PASS tests_run=4246 details_complete=True fallback=none seconds=948.55 reason=Executed tests completed successfully
[TDQ:TEST] PASS — scope=full backend=pytest tests=4246 skipped=35 in 948.55s.
{"request": "2026-11-16-1953-fix-lsp-gate-mcp-routing", "tron_bo": 4, "bo_sot": 0, "modules_bo_sot": [], "ngan_sach": 3, "radius_complete": false, "radius_reason": "Radius misses are partial or unavailable"}
TDQ_RESULT sha256: 60e2858375e3f942df908a196c14b8fe99cf4a672b2866811cb7339d53936485
ruff F,B (7 files): All checks passed!
i18n_check (6 core/patch files): 0 Vietnamese line(s)
token_budget --kiem: exit 0
tdq-qc-tester Round 2: Q1-Q5 PASS · DEFECTS: (không có) · VERDICT: PASS everything
```

### QC-F2
```
tdq-qc-tester vung-cham (--files --khong-ep-tron-bo): 180 passed in 20.28s
chrome-devtools-smoke.md verified OK (allow + select_page + start_lsp {} deny)
Hợp đồng skill §3b: tdq-setup, tdq-browser-research, tdq-browser-test đều đủ đầu ra `Ra` và lệnh `Kiểm` đạt.
```

### QC-F3
```
Arch import boundaries OK (scripts & hooks clean)
doc_lint --pair spec plan: 0 violation(s), exit 0
```

### QC-F4
```
1. Có thêm file/class/hàm/hằng số/config nào không được yêu cầu không? -> KHÔNG (chỉ tách helper thuần trong phạm vi M1-M3 + QC1.3).
2. Có tạo interface cho 1 implement duy nhất không? -> KHÔNG (hàm phẳng dùng chung qua module).
3. Có giữ nguyên xử lý lỗi và an toàn dữ liệu không? -> CÓ (fail-open khi thiếu khoá/JSON hỏng, fail-closed trên start_lsp rỗng `{}`).
4. Mọi hàm mới đều có test kiểm thử? -> CÓ (red -> green đủ mọi hàm & nhánh mới).
5. Cyclomatic complexity <= 10? -> CÓ (`ruff C901`: `_decode_json_dict` / `ten_lenh_tdq_lsp` / `la_tool_tdq_lsp` / `_extract_raw_tool_container` / `_phan_xu_lenh` cc=6 / `main` cc=8 / `cli_fixes_a.py` đều `<= 10`; riêng `normalize_payload` và `phan_tich_lsp_telemetry` được rút gọn thêm so với bản gốc).
```

## Lệch spec chờ duyệt
không có

## Kết luận
PASS toàn bộ 5/5 hạng mục Definition of Done (`Q1`–`Q5`) và 4/4 fixed items (`QC-F1`–`QC-F4`) sau 2 vòng `tdq-qc-tester` (`muc_qc = ultra`).
