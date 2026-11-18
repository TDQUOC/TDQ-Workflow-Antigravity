# QC — Tích hợp Caveman 5 hướng tối ưu ngữ cảnh và xin quyền vào TDQ-Workflow-Antigravity

Ngày: 2026-11-18 · Plan: ../plan/2026-11-17-2156-tich-hop-caveman-agy.md · Vòng: 1
Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

| # | Hạng mục | Lệnh đã chạy | Kết quả | PASS/FAIL |
|---|---|---|---|---|
| Q1 | Bảo toàn bất biến Proxy MCP (`M1`: khóa schema, từ phủ định, `tools/call`, trễ `<= 100 ms`) | `py -3 -m unittest tests/test_tdq_mcp_shrink.py -v` + E2E live `agent-lsp` | `10/10` pass (`40,02%` giảm trên fixture `50` tool trong `3,50 ms`); live `agent-lsp` `65` tool `61.106 B → 44.662 B` (`-26,9%`, `11,8 ms`) | PASS |
| Q2 | Giảm thuế schema `>= 15%` & `6` subagent chuẩn `Auto-Clarity` (`M1` + `M2`) | `py -3 -m unittest discover -s tests -p "test_subagent_start.py" -v` + `py -3 scripts/context_surface.py --mcp-prefix --quiet` | `12/12` pass; `108` tool MCP `99.968 → 73.578` ký tự (giảm `26,4%`, vượt ngưỡng `>= 15%`) | PASS |
| Q3 | Kho `CCR` `> 32 KB` / `>= 200` dòng, trần `128 MB`, khôi phục `100%` `SHA-256` & `read_gate.py` nhắc không chặn (`M3`) | `py -3 -m unittest tests/test_tdq_ccr.py -v` + `py -3 -m unittest discover -s tests -p "test_read_gate.py" -v` | `8/8` + `21/21` pass; live `36.010 B` khôi phục `SHA-256` khớp `100%`; `read_gate.py` trả `allow` không chặn | PASS |
| Q4 | Kiểm toán token đa host (`Antigravity`, `Codex`, `Claude Code`) mặc định `5` phiên với nhãn `measured`/`inferred` (`M4`) | `py -3 -m unittest tests/test_transcript.py -v` + `discover -p "test_token_audit.py"` + `token_audit.py --host all --sessions 5 --top 5` | `54/54` + `27/36` pass (`9` skipped do thiếu `anthropic-tokenizer`, `0` fail); live quét `5 agy + 3 codex` với nhãn `inferred` | PASS |
| Q5 | Xin quyền `M5`, `--nen` không bật ngầm, build & validate plugin `0` lỗi và trọn suite xanh | `py -3 -m unittest tests/test_caveman_setup.py -v` + `build_agy_plugin.py` + `token_budget.py --kiem` + `agy.EXE plugin validate --strict --json` + `tdq_test.py tron-bo` | `9/9` pass; `62` lock budget OK; `agy.EXE` `0 findings`; `4.350` test suite xanh (`35` skipped, `0` fail) | PASS |
| Q6 | Nghiệm thu E2E sống trên bản cài cục bộ `~/.gemini/config/plugins/tdq-workflow-agy` | `install_agy_plugin.py --sync-local-mcp --with-caveman` + `tdq_setup.py --check-caveman` + `tdq_lsp.py check` | Cài `229` file, bọc `3` server MCP, `enabled=True \| active=True`, `tdq_lsp.py` báo `đã bật (bọc 3 server MCP)` | PASS |
| QC-F1 | Trọn bộ test sau lần sửa cuối (`muc_qc = full`) | `py -3 scripts/tdq_test.py tron-bo --workers 4 --fresh --reuse off` + `py -3 scripts/tdq_test.py so` | `status=PASS`, `4.350` cases (`35` skipped, `0` failed) trong `346,29s`; `full-suite runs: 2 of budget 3`; `radius misses: 0` | PASS |
| QC-F2 | Hồi quy vùng chạm (`Chạm:` trong plan) | Chạy toàn bộ test của từng module đã sửa và bổ sung (`tests/test_build_portable.py` `38/38`, `test_tdq_setup*`, `test_tdq_lsp`, `test_agy_plugin_validate`) | Tất cả module vùng chạm đều xanh; không có module thiếu test | PASS |
| QC-F3 | Ràng buộc kiến trúc (Spec §5) | Kiểm phân tầng `scripts/` vs `hooks/`, `i18n_check.py`, `doc_lint.py` | `0` vi phạm phân tầng; `i18n_check.py` `0` dòng tiếng Việt ở `9` file mã/skill mới; `doc_lint.py` `0` lỗi; `ruff` trên PATH máy: chưa kiểm tra do thiếu binary toàn cục (ghi chú theo rule) | PASS |
| QC-F4 | Clean Code — 5 câu hỏi SOLID (`clean-code.md`) | Tự rà soát theo `## Self-check` trên `M1`–`M5` | Trả lời `Có` cả 5 tiêu chí SRP/OCP/LSP/ISP/DIP (chi tiết bên dưới) | PASS |

## Bằng chứng

### Q1 & Q2 — Proxy MCP & Bề mặt ngữ cảnh
```text
Ran 10 tests in 0.243s — OK (test_tdq_mcp_shrink.py: 40.02% reduction on 50-tool fixture, 3.50ms)
LIVE-M1-LSP PASS: init_id= 1 tools= 65 shrunk_bytes= 44662 elapsed_ms=11.8 (61106B -> 44662B, -26.9%)
TOTAL MCP (108 tools): 99.968 chars (~24.992 tokens) -> 73.578 chars (~18.394 tokens), saved 26.390 chars (26.4%)
test_subagent_start.py: Ran 12 tests in 0.849s — OK
```

### Q3 — Kho CCR & Nhắc không chặn `read_gate.py`
```text
test_tdq_ccr.py: Ran 8 tests — OK
test_read_gate.py: Ran 21 tests — OK
LIVE-CCR PASS: 369531fab422 36010 bytes (SHA-256 round-trip exact)
```

### Q4 — Kiểm toán đa host
```text
test_transcript.py: Ran 54 tests — OK
test_token_audit.py: Ran 36 tests — OK (skipped=9 do thiếu anthropic-tokenizer trong env test mặc định)
token_audit.py --host all --sessions 5 --top 5 -> scanned 8 sessions (5 agy, 3 codex) with [agy|inferred] / [codex|inferred]
```

### Q5, Q6 & QC-F1 — Build, Validate, Setup & Trọn bộ 207 module
```text
test_caveman_setup.py: Ran 9 tests — OK
test_build_portable.py: 38 passed, 4 subtests passed in 8.61s (sau khi đăng ký 3 module runtime mới vào APPROVED_RUNTIME_MODULES)
agy.EXE plugin validate --strict --json plugins/tdq-workflow-agy -> "findings": [] (agents=6, hooks=6, mcpServers=3, rules=10, skills=12)
caveman · enabled=True | active=True | wrapped=['lsp', 'chrome-devtools', 'tavily-primary'] | muted=False | cfg=C:\Users\admin\.tdq\caveman.json
[TDQ:TEST] PASS — scope=full backend=pytest tests=4350 skipped=35 in 346.29s.
tdq_test: so request=2026-11-17-2156-tich-hop-caveman-agy tron_bo=2 bo_sot=0 budget=3
```

### QC-F4 — Kiểm tra Clean Code (5 câu hỏi SOLID)
- **SRP:** Có — mỗi hàm/module giữ đúng một trách nhiệm (`tdq_mcp_shrink.py` chỉ lọc JSON-RPC schema; `tdq_ccr.py` chỉ lưu/tóm tắt/khôi phục byte; `caveman_config.py` chỉ đọc/ghi `~/.tdq/caveman.json` và bọc `mcp_config.json`; `token_audit.py` tách phần đọc adapter khỏi tính carry-cost).
- **OCP:** Có — bảng từ khóa ràng buộc (`CONSTRAINT_TOKENS`), bảng metadata bị cắt (`STRIP_SCHEMA_KEYS`), đuôi tệp dữ liệu `CCR` (`CCR_DATA_EXTS`), danh sách server bọc (`CAVEMAN_MCP_SERVERS`) đều là hằng dữ liệu mở rộng không cần sửa logic vòng lặp.
- **LSP:** Có — mọi hàm trả về kiểu và hợp đồng lỗi nhất quán trên tất cả nhánh (`None` hoặc danh sách rỗng khi thiếu tệp, `ValueError` tường minh khi sai `SHA-256`).
- **ISP:** Có — các hàm nhận đúng đường dẫn (`mcp_file`, `store_dir`, `home`) hoặc dict cấu hình cần thiết, không ép truyền cả đối tượng `state` hay `args` khổng lồ.
- **DIP:** Có — `session_start.py`, `tdq_setup.py`, `tdq_lsp.py`, `install_agy_plugin.py` và `install.py` đều gọi qua một điểm vào chung là `scripts/caveman_config.py`; `context_surface.py` gọi trực tiếp `tdq_mcp_shrink.shrink_schema_node` thay vì viết lại bộ lọc.

## Lệch spec chờ duyệt

không có

## Kết luận

PASS toàn bộ (`10/10` hạng mục `Q1`–`Q6` và `QC-F1`–`QC-F4` đạt; đã sửa xong lỗi đăng ký `APPROVED_RUNTIME_MODULES` ở lượt chạy `tron-bo` đầu tiên và chạy lại trọn `4.350` test xanh `100%`).
