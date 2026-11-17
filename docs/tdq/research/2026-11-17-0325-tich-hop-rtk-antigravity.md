# RESEARCH — Tích hợp cộng sinh RTK tối ưu token và tự động kiểm/cài cho Antigravity
Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

## Góc 1 — GitHub Releases chính thức, biến thể OSS & kiểm tra SHA256

- **Truy vấn API ngày `2026-11-17`:**
  - `https://api.github.com/repos/rtk-ai/rtk/releases/latest` → tag **`v1.2.0`**.
  - `https://api.github.com/repos/BurntSushi/ripgrep/releases/latest` → tag **`15.2.0`**.
- **Tài sản phát hành của `rtk-ai/rtk` (`v1.2.0`):**
  - Cung cấp sẵn `checksums.txt` và trường `digest` (`SHA256`) trên từng asset để kiểm toàn vẹn trước khi ghi binary ra đĩa (khớp với mẫu `cai_agent_lsp` của `scripts/tdq_setup.py`).
  - Có hai biến thể binary chính thức song song:
    - Biến thể đầy đủ `rtk-*` (`rtk-x86_64-pc-windows-msvc.zip`, `rtk-aarch64-apple-darwin.tar.gz`, `rtk-x86_64-apple-darwin.tar.gz`, `rtk-x86_64-unknown-linux-musl.tar.gz`, `rtk-aarch64-unknown-linux-musl.tar.gz`).
    - Biến thể mã nguồn mở thuần **`rtk-oss-*`** (`rtk-oss-x86_64-pc-windows-msvc.zip`, `rtk-oss-aarch64-apple-darwin.tar.gz`, `rtk-oss-x86_64-apple-darwin.tar.gz`, `rtk-oss-x86_64-unknown-linux-musl.tar.gz`, `rtk-oss-aarch64-unknown-linux-musl.tar.gz`) biên dịch không kèm engine BUSL-1.1 (`Apache-2.0` thuần), giữ trọn hook rewrite, mọi bộ lọc CLI và kho SQLite recall ([installation.md](C:/Users/admin/Documents/rtk/docs/guide/getting-started/installation.md)).
  - **Cảnh báo trùng tên (`Name collision`):** Trên crates.io tồn tại gói *Rust Type Kit* dùng chung tên lệnh `rtk`. Do đó mọi phép kiểm tra cài đặt bắt buộc chạy cả `rtk --version` (yêu cầu `>= 0.25.0` để có `rtk rewrite`) lẫn `rtk gain` (`returncode == 0`), tuyệt đối không chỉ dựa vào `shutil.which("rtk")`.
- **Tài sản phát hành của `BurntSushi/ripgrep` (`15.2.0`) & hiện trạng máy:**
  - Một số bộ lọc của `rtk` gọi `rg` (`ripgrep`) ([installation.md](C:/Users/admin/Documents/rtk/docs/guide/getting-started/installation.md)). Kiểm tra thực tế trên máy Windows hiện tại bằng PowerShell `Get-ChildItem` cho thấy chưa có `rg.exe` trên `PATH` hay trong `%LOCALAPPDATA%\Programs\Antigravity`, `%USERPROFILE%\.cargo`, `%USERPROFILE%\.local`.
  - Release `15.2.0` cung cấp file `.sha256` đi kèm và `digest` cho từng gói (`ripgrep-15.2.0-x86_64-pc-windows-msvc.zip`, `ripgrep-15.2.0-aarch64-pc-windows-msvc.zip`, `ripgrep-15.2.0-x86_64-apple-darwin.tar.gz`, `ripgrep-15.2.0-aarch64-apple-darwin.tar.gz`, `ripgrep-15.2.0-x86_64-unknown-linux-musl.tar.gz`).

## Góc 2 — Hợp đồng Hook Antigravity & Giao thức nhúng `rtk rewrite`

- **Antigravity Hooks (`hooks.md`):**
  - `PreToolUse` nhận `stdin` chứa `toolCall.name`, `toolCall.args` (`CommandLine` cho `run_command`), hỗ trợ trả `"decision": "allow"` kèm `"overwrite": {"CommandLine": "..."}` (shallow merge vào `toolCall.args` trước khi thực thi; kết quả tool có tiền tố thông báo hook đã viết lại tham số).
  - Các hook cùng sự kiện chạy **tuần tự (sequentially)**; `PostToolUse` chỉ chấp nhận `{}` (không sửa được output sau khi chạy xong). Vì vậy tối ưu đầu ra shell nằm ở `PreToolUse` (`run_command` + `rtk`), còn kiểm soát đọc file/tìm kiếm nằm ở `read_gate.py`, `lsp_gate.py`, `search_gate.py` và `tdq_test.py`.
- **Giao thức `rtk rewrite` ([embedding.md](C:/Users/admin/Documents/rtk/docs/guide/getting-started/embedding.md), `rewrite_cmd.rs`):**
  - Gọi `rtk rewrite -- "<command>"`: exit `0` và `3` đều nghĩa là có lệnh viết lại trên `stdout` (ngoài Claude Code exit `3` là trường hợp bình thường khi không có rule allow); exit `1` (không có filter / passthrough) và exit `2` (deny rule) giữ nguyên lệnh gốc, luôn fail-open.
  - Tài liệu `embedding.md` khuyến nghị kiểm `RTK_DISABLED=1` trước khi spawn `rtk rewrite`, đặt timeout an toàn `2 s` (bình thường phản hồi `< 20 ms`), và cache probe `rtk --version` theo tiến trình/phiên.
- **Đường dẫn cấu hình & recall trên Windows ([configuration.md](C:/Users/admin/Documents/rtk/docs/guide/getting-started/configuration.md), `user_dirs.rs`, `config.rs`):**
  - Cấu hình Windows đặt ở `%APPDATA%\rtk\config.toml` (`dirs::config_dir()`), kho lưu trữ SQLite recall lossless đặt ở `%LOCALAPPDATA%\rtk\` (`dirs::data_local_dir()`).
  - Các khóa cần hòa hợp với TDQ: `[telemetry] enabled = false`, `[display] pro_hint = false`, `emoji = false`, `[hooks] suppress_hook_warning = true`, `exclude_commands = ["grep", "rg", ...]`, `[retriever] mode = "sqlite"`, `[awareness] level = "default"`.

## Góc 3 — Số đo nền Dispatcher Collapse trên Windows

- **Đo trực tiếp bằng `scripts/context_surface.py` (`measure_dispatcher_parity(runs=5)`):**
  - `baseline_median_ms`: **`136.29 ms`** (chạy tuần tự 2 tiến trình Python riêng `bash_gate.py` + `search_gate.py`).
  - `candidate_median_ms`: **`68.85 ms`** (chạy gộp 1 tiến trình Python duy nhất).
  - `speedup_pct`: **`49.48%`** (giảm `67.44 ms` chi phí khởi tạo mỗi lệnh `run_command`).
- **Rủi ro phát hiện ngay từ phép đo (`equivalent: false` ở harness mẫu):**
  - `hooks/scripts/_common.py` định nghĩa `read_payload()` đọc thẳng `sys.stdin`, nên lần gọi thứ hai trong cùng 1 tiến trình đọc phải chuỗi rỗng. Khi collapse `bash_gate` + `search_gate` + `rtk` vào cổng thống nhất, bắt buộc cache kết quả `read_payload()` vào `_RUNTIME_STATE` hoặc truyền `payload` đã chuẩn hóa trực tiếp vào các hàm đánh giá thuần (`quyet_dinh` / đánh giá rule), đồng thời giữ nguyên interface của `bash_gate.py` và `search_gate.py` để không làm gãy các caller/test đang import trực tiếp.
