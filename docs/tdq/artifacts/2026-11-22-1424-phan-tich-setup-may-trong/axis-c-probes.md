# Shard Trục C — Thực nghiệm cô lập dấu phiên tiến trình & khung Sandbox Simulate Test

Ngày: 2026-11-22 · Task: `T1.2` · Nguyên tắc an toàn: chỉ chạy lệnh đọc và dựng tệp mẫu trong `TEMP` tự xóa; ảnh chụp `~/.gemini/config/` xác minh trước và sau `cfg_before=371 == cfg_after=371`, `equal=True` (`0` thay đổi) `[EV-C03]`.

## 1. Xác thực dấu phiên Antigravity (`H2` — Host Session Fingerprint) `[EV-C01]`

Đo trực tiếp chuỗi tiến trình cha từ công cụ đang chạy cho thấy cấu trúc lồng thực sự của Antigravity:
- Tầng ngắn hạn (đổi theo từng lệnh / từng lượt gọi tool): `powershell.exe` -> `python.exe` -> `powershell.exe`.
- **Tầng bền vững suốt phiên ứng dụng:** `language_server.exe` (`pid=23192`, `created=2026-11-21T21:55:09.1527940+07:00`) -> `Antigravity.exe` (`pid=9872`, `created=2026-11-21T21:55:08.1901410+07:00`).
- **Biến môi trường đặc trưng Antigravity export cho cả tiến trình con:** `ANTIGRAVITY_LS_ADDRESS` (`localhost:56861`), `ANTIGRAVITY_APP_DATA_DIR`, `ANTIGRAVITY_CONVERSATION_ID`, `PLUGIN_ROOT`, `PLUGIN_DATA` `[EV-C01]`, `[EV-A04]`.

**Hệ quả thiết kế trực tiếp cho chống báo nhầm Restart:**
1. Nếu người dùng mở cuộc trò chuyện mới (`conversationId` đổi) trong **cùng** phiên Antigravity IDE chưa tắt: `Antigravity.exe` + `language_server.exe` `(pid, created)` và `ANTIGRAVITY_LS_ADDRESS` **không đổi** → Hook biết chắc **chưa restart**, chỉ nhắc lại yêu cầu khởi động lại.
2. Khi người dùng tắt hẳn Antigravity và mở lại: cả `pid` lẫn `created` timestamp (và cổng `ANTIGRAVITY_LS_ADDRESS`) đều đổi → Hook khẳng định **đã restart thật** và kích hoạt Pha 2 ngay lượt chat đầu tiên.
3. Lưu ý hiệu năng cực quan trọng: truy vấn `Get-CimInstance` qua PowerShell mất tới ~`200–300ms`, KHÔNG được chạy ở mọi lượt chat. Thiết kế chuẩn chỉ kiểm tra `stat()` một tệp cờ nhẹ; chỉ khi cờ `awaiting_restart` đang bật mới đo Host Fingerprint bằng Win32 API / `/proc/<pid>/stat` / `ps` (`< 2ms` trong Rust/Ctypes)!

## 2. Phát hiện vị trí thực của `PLUGIN_DATA` `[EV-C02]`

- Trên hệ thống thật, thư mục dữ liệu bền vững dùng tên **`plugin_data`** (gạch dưới) dưới `<ANTIGRAVITY_APP_DATA_DIR>` (`~/.gemini/antigravity/plugin_data/` hoặc `~/.gemini/antigravity-cli/plugin_data/`), không phải `~/.gemini/config/plugin-data/` (`~/.gemini/config/` chỉ chứa `plugins/`, `mcp_config.json`, `config.json`, `projects/`, `sidecars/`).
- Vì vậy trình quản lý `setup-state.json` phải dùng quy tắc độ ưu tiên:
  1. `os.environ["PLUGIN_DATA"]` (khi Antigravity cấp sẵn cho plugin hook / MCP server đã cài).
  2. `<ANTIGRAVITY_APP_DATA_DIR>/plugin_data/tdq-workflow-agy/` (khi chạy từ CLI/tool con không có `PLUGIN_DATA`).
  3. `~/.gemini/antigravity/plugin_data/tdq-workflow-agy/` (fallback mặc định).

## 3. Thực nghiệm khung `Sandbox Simulate Test` (`H4`) `[EV-C03]`, `[EV-C04]`

Chạy thử trong `TemporaryDirectory` cô lập (dọn sạch tức thì khi thoát):
- `agy plugin validate plugins/tdq-workflow-agy --strict --json`: **189.8 ms**, `ec=0`, kết quả JSON hợp lệ.
- `node plugins/tdq-workflow-agy/scripts/tdq_hook_launcher.mjs --event PreInvocation` với `TDQ_PROJECT_DIR=<temp>`: **267.1 ms**, `ec=0`, trả đúng JSON `injectSteps` chuẩn Antigravity (`[TDQ:INTAKE]`).
- Thử nghiệm `tdq_mcp_launcher.mjs lsp`: phát hiện thực tế cực giá trị (`[EV-C04]`) — khi `subprocess.run(input=...)` đóng `stdin` quá sớm trước lúc nhận phản hồi, `agent-lsp.exe` thoát `ec=1` với `[error] server error: server is closing: EOF` dù đã tự dò được `pyright-langserver`, `typescript-language-server`, `gopls`, `rust-analyzer`. Do đó bộ `Simulate Test` tương lai bắt buộc dùng `subprocess.Popen` giữ `stdin` mở tới khi đọc đủ response JSON-RPC `initialize` + `tools/list` rồi mới đóng pipe!
- Toàn bộ `~/.gemini/config/` bảo toàn nguyên vẹn (`371 == 371`, `equal=True`).
