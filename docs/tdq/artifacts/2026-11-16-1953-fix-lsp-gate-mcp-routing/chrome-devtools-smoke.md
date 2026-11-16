# Chrome DevTools MCP Smoke — `2026-11-16-1953-fix-lsp-gate-mcp-routing`

## 1. Pre-flight probe `chrome-devtools` MCP runtime

- Gọi trực tiếp `call_mcp_tool(ServerName="chrome-devtools", ToolName="list_pages", Arguments={})` → **Kết nối thành công**, trả về 5 trang đang mở trong Chrome DevTools.
- Theo chốt `3b`, bản cài cục bộ `C:/Users/admin/.gemini/config/plugins/tdq-workflow-agy` chưa bị ghi đè nên các lời gọi có `Arguments` thực tế được kiểm chứng trực tiếp qua hook đã biên dịch trong repo (`plugins/tdq-workflow-agy/hooks/scripts/lsp_gate.py --event PreToolUse`).

## 2. Kết quả kiểm chứng trên `plugins/tdq-workflow-agy/hooks/scripts/lsp_gate.py`

| Tool gọi qua `call_mcp_tool` | Tham số `Arguments` | Output `stdout` | Log `stderr` (`TDQ_LOG=1`) | Thời gian |
|---|---|---|---|---|
| `chrome-devtools/select_page` | `{"bringToFront": true, "pageId": 1}` | `{"decision": "allow"}` | `[2026-11-17T00:57:22] lsp_gate: non-tdq-lsp tool='mcp__chrome-devtools__select_page' — allow` | `70.2 ms` |
| `chrome-devtools/list_pages` | `{}` | `{"decision": "allow"}` | `[2026-11-17T00:57:22] lsp_gate: non-tdq-lsp tool='mcp__chrome-devtools__list_pages' — allow` | `67.7 ms` |
| `chrome-devtools/click` | `{"pageId": 1, "uid": "btn-1", "dblClick": false}` | `{"decision": "allow"}` | `[2026-11-17T00:57:23] lsp_gate: non-tdq-lsp tool='mcp__chrome-devtools__click' — allow` | `68.5 ms` |
| `chrome-devtools/navigate_page` | `{"pageId": 1, "type": "url", "url": "https://example.com"}` | `{"decision": "allow"}` | `[2026-11-17T00:57:23] lsp_gate: non-tdq-lsp tool='mcp__chrome-devtools__navigate_page' — allow` | `64.9 ms` |
| `tdq-workflow-agy_lsp/start_lsp` (kiểm đối chứng `2a`) | `{}` | `{"decision": "deny", "reason": "[TDQ:LSP] start_lsp without language_id..."}` | `[2026-11-17T00:57:23] lsp_gate: language_id=None root=None · deny` | `69.0 ms` |
