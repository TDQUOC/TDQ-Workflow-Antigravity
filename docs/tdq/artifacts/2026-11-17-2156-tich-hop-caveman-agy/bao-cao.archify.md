# Báo cáo — Tích hợp Caveman 5 hướng tối ưu ngữ cảnh và xin quyền vào TDQ-Workflow-Antigravity {#bao-cao}

@meta locale=en

Hoàn tất trọn bộ `5` module `Python stdlib` (`M1`–`M5`), vượt qua `4.350` bài kiểm thử toàn kho (`0` lỗi), xác thực `agy.EXE plugin validate` (`0 findings`), và nghiệm thu E2E sống trên bản cài cục bộ `~/.gemini/config/plugins/tdq-workflow-agy`.

## 1. Trước request và Sau request {#truoc-sau}

@workflow id=truoc-sau-ket-qua title="Chuyển đổi kiến trúc trước và sau tích hợp M1–M5"
| truoc | Trước: 99.968 ký tự MCP thô | external |
| m5_optin | M5: tdq_setup --with-caveman | security |
| m1_m2 | M1 Proxy (-26.4%) + M2 Clarity | messagebus |
| m3_m4 | M3 CCR SHA-256 + M4 Audit 3 host | database |
| truoc > m5_optin | opt-in |
| m5_optin > m1_m2 | bọc 3 MCP |
| m1_m2 > m3_m4 | đo & lưu gốc |

- **Trước request:** `108` tool MCP nạp thô `99.968` ký tự mỗi phiên; chưa có chuẩn `Compact Handoff` cho `6` subagent; thiếu kho khôi phục `CCR` `SHA-256`; `token_audit.py` chỉ đọc Claude Code; và chỉ có trigger xin quyền cho `RTK`.
- **Sau request:** Proxy `M1` cắt `26,4%` bề mặt schema (live `agent-lsp` giảm `61.106 B → 44.662 B` trong `11,8 ms`); `M2` chuẩn hóa `6` subagent & browser skill; `M3` lưu nguyên bản khớp `100%` `SHA-256` kèm nhắc không chặn ở `read_gate.py`; `M4` kiểm toán `5` phiên trên Antigravity/Codex/Claude; `M5` quản lý quyền tại `~/.tdq/caveman.json`.

## 2. Đã test gì và Kết quả đo thực tế {#ket-qua-test}

| Hạng mục | Phạm vi kiểm tra | Kết quả thực đo | Trạng thái |
|---|---|---|---|
| `Q1` Proxy `M1` | Unit + live `agent-lsp` pipe | Giảm `40,02%` (fixture) và `26,9%` (`11,8 ms` live) | {good:PASS} |
| `Q2` Surface & `M2` | `context_surface` + `subagent_start` | `99.968 → 73.578` ký tự (`-26,4%`), `12/12` xanh | {good:PASS} |
| `Q3` Kho `CCR` & Gate | `test_tdq_ccr` + `read_gate` + live `36 KB` | `8/8` + `21/21` xanh, khôi phục `SHA-256` `100%` | {good:PASS} |
| `Q4` Audit đa host | `test_transcript` + `token_audit` + live | `54/54` + `27/36` (`9` skip tokenizer), quét `8` phiên | {good:PASS} |
| `Q5` Setup & Trọn bộ | `build_agy_plugin` + `validate` + `tron-bo` | `4.350` tests xanh (`35` skip, `0` fail, `346,29s`) | {good:PASS} |
| `Q6` E2E cục bộ | Cài `--with-caveman` lên `~/.gemini/...` | `229` file, bọc `3` MCP server, `--check-caveman` xanh | {good:PASS} |
