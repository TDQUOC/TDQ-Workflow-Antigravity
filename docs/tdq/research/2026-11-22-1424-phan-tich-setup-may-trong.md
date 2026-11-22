# HỒ SƠ NGHIÊN CỨU & ĐỀ XUẤT KIẾN TRÚC — Quy trình `tdq-setup` Zero-to-Full từ máy trống kèm kiểm chứng tự động sau Restart

Ngày: 2026-11-22 · Mã yêu cầu: `2026-11-22-1424-phan-tich-setup-may-trong` · Chế độ: `investigate` · Sổ bằng chứng: `docs/tdq/artifacts/2026-11-22-1424-phan-tich-setup-may-trong/evidence.jsonl` (`20` bản ghi `EV-A01..A08`, `EV-B01..B08`, `EV-C01..C04`).

---

## 1. Tóm tắt điều hành & Mức độ tin cậy nhận định

Để biến `tdq-setup` thành quy trình cài đặt trọn vẹn từ một chiếc máy trắng tinh trên **Windows**, **macOS** và **Linux** (từ lúc chưa có `Git`, `Python`, `Node` tới lúc mọi tầng tìm kiếm, add-ons, hooks, MCP và subagents chạy ổn định), cần giải quyết triệt để **4 lỗ hổng gốc** phát hiện trong đợt kiểm toán này:

| Lỗ hổng hiện tại (`EV-*`) | Rủi ro trên máy mới tinh | Đề xuất giải quyết trong kiến trúc v2 | Nhãn tin cậy (`QC-I4`) |
|---|---|---|---|
| **1. Định vị sai hệ thống đích:** `tdq_setup.py`, `tdq_lsp.py`, `setup_status.py`, `tdq_devtool_mcp.py`, `SKILL.md` còn trỏ `~/.claude.json`, `~/.claude/settings.json`, `~/.claude/CLAUDE.md` và đường dẫn sai `~/.gemini/antigravity/mcp_config.json` `[EV-B01]`, `[EV-B02]`, `[EV-B03]`, `[EV-B08]` | Cài xong vẫn báo nợ giả hoặc ghi nhầm vào `~/.claude*` thay vì `~/.gemini/config/` và `~/.gemini/antigravity-cli/settings.json` `[EV-A05]` | Tách `HostAdapter` cho Google Antigravity, chỉ đọc/ghi chuẩn `~/.gemini/config/`, `~/.gemini/GEMINI.md`, `~/.gemini/antigravity-cli/settings.json` và dùng `agy plugin list/validate` `[EV-A01]`, `[EV-A05]` | **Verified** |
| **2. Thiếu tầng Bootstrap máy trống & kẹt `WindowsApps` / `sudo` / Sandbox:** chưa dựng được `Git`, `Node.js`, `Python 3`, `uv`; Antigravity Sandbox mặc định khóa ghi ngoài workspace & khóa mạng `[EV-A06]`, `[EV-C03]` | Chưa có `Git` thì không cài được plugin từ GitHub; thiếu `uv`/`Node`/`Python` thì `tdq_setup.py` và Node launchers đều đứng hình | Mô hình **Dual-Entry (`1a`)**: Bootstrap one-liner ngoài terminal + Pha 1 trong `tdq-setup` ưu tiên user-space (`uv python install --default`, `fnm`, static binaries) chỉ đòi `unsandboxed` đúng 1 lần `[EV-A08]` | **Verified** |
| **3. Phân mảnh Add-ons & phá tính đa OS ở Caveman / Tavily:** `caveman_config.py` ghi đè `"command": sys.executable` làm hỏng Node launcher `[EV-B04]`; `tavily-primary` chưa có đường nạp key an toàn `[EV-B06]`; thiếu bảng duyệt gom 1 lần | Cài nhiều bước rải rác; bật `--with-caveman` làm gãy tính portable khi đổi user/OS; thêm `variables` vào `mcp_config.json` lại làm `agy plugin install` khóa plugin `[EV-A04]` | Giao thức **One-Shot Manifest Consent (`2a`)**: quét 1 lần → duyệt 1 bảng kê cho toàn bộ Core + Add-ons; thêm mode `caveman` vào `tdq_mcp_launcher.mjs` và nạp mềm `${PLUGIN_DATA}/secrets.env` cho Tavily `[EV-B04]`, `[EV-B06]` | **Verified** |
| **4. Mất dấu qua Restart & thiếu bộ Simulate độc lập workspace:** không có state bền vững; nhầm tên `plugin-data` với `plugin_data`; không phân biệt mở tab mới vs restart thật `[EV-C01]`, `[EV-C02]`, `[EV-C04]` | Người dùng mở lại IDE nhưng quên kiểm chứng; hoặc gõ tiếp trong phiên cũ mà hook tưởng đã restart; hoặc không test được trên workspace rỗng | Máy trạng thái tại **`${PLUGIN_DATA}/setup-state.json`** + cờ `setup-pending.flag` (`O(1)` `<0.1ms` `[EV-B07]`) + `Host Session Fingerprint` `[EV-C01]` tự kích hoạt **Sandbox Simulate Test 6 tầng** bằng `Popen` interactive MCP pipes `[EV-C03]`, `[EV-C04]` | **Verified** |

---

## 2. Trụ cột 1 (`1a`) — Kiến trúc Dual-Entry Bootstrap cho Máy Trống Đa OS

### 2.1. Hai cửa vào nối tiếp (Zero-to-Full không phụ thuộc thứ tự)

1. **Cửa 0 — Terminal One-Liner (`scripts/bootstrap.ps1` cho Windows, `scripts/bootstrap.sh` cho macOS/Linux):**
   - Dùng cho máy **trắng tinh hoàn toàn** chưa có cả `Git`, `Node.js`, `Python` hoặc `agy` CLI:
     - **Windows (PowerShell):** `irm https://raw.githubusercontent.com/TDQUOC/TDQ-Workflow-Antigravity/dev/scripts/bootstrap.ps1 | iex` (hoặc bản phát hành gắn tag/branch ổn định).
     - **macOS / Linux:** `curl -fsSL https://raw.githubusercontent.com/TDQUOC/TDQ-Workflow-Antigravity/dev/scripts/bootstrap.sh | bash`.
   - Việc làm của Cửa 0:
     1. Kiểm tra & cài **Git** + **Node.js LTS** + **`uv`** + **`Python 3` thực** (`uv python install --default`) bằng công cụ chuẩn từng OS `[EV-A08]`.
     2. Kiểm tra/cài **`agy` CLI** qua trình cài chính thức của Google (`antigravity.google/cli/install.ps1` hoặc `install.sh` `[EV-A07]`) nếu chưa có.
     3. Chạy luôn `agy plugin install https://github.com/TDQUOC/TDQ-Workflow-Antigravity/tree/release/antigravity` `[EV-A01]` (hoặc kéo về rồi `install` từ thư mục cục bộ nếu `Git` vừa được cài trong cùng shell bằng cách bổ sung trực tiếp thư mục bin vào `$env:PATH` / `$PATH` tức thì!).
     4. Ghi đánh dấu sơ bộ vào `plugin_data/tdq-workflow-agy/setup-state.json` với `bootstrap_done: true` và hướng dẫn người dùng mở Antigravity IDE/CLI và gọi `/tdq-setup`.

2. **Cửa 1 — Gọi `/tdq-setup` trực tiếp trong Antigravity:**
   - Khi người dùng đã có Antigravity và đã cài plugin (hoặc đang chạy trên máy mới chỉ có Node/Antigravity, chưa có `uv`/`Python`/`agent-lsp`/`rg`/`rtk`/Language Servers/Add-ons):
   - Bước đầu tiên (`Stage 0`) của `tdq-setup` tự động chạy **Pre-flight Runtime & Toolchain Probe** (có nhánh fallback bằng thuần `node scripts/tdq_setup_probe.mjs` phòng trường hợp máy thậm chí chưa có `Python 3` thực ngoài `WindowsApps` stub!) để liệt kê toàn bộ thứ còn thiếu vào một bảng kê duy nhất.

### 2.2. Ma trận lệnh cài đặt user-space chuẩn trên 3 OS (ưu tiên `0 sudo`) `[EV-A07]`, `[EV-A08]`, `[EV-B05]`

| Gói / Công cụ | Windows 10/11 (PowerShell / `tdq_setup`) | macOS (Apple Silicon & Intel) | Linux (Debian/Ubuntu, Fedora, Arch — **0 sudo trước**) | Đường fallback nếu thiếu quyền/mạng |
|---|---|---|---|---|
| **Antigravity CLI (`agy`)** | `irm https://antigravity.google/cli/install.ps1 \| iex` → `%LOCALAPPDATA%\agy\bin` | `curl -fsSL https://antigravity.google/cli/install.sh \| bash` → `~/.local/bin/agy` | Như macOS | Tải bộ cài App/IDE từ `antigravity.google/download` |
| **`Git`** | `winget install --id Git.Git --exact --silent --accept-package-agreements --accept-source-agreements` (thêm `C:\Program Files\Git\cmd` vào PATH phiên hiện tại) | `brew install git` hoặc `xcode-select --install` | `git --version`; thiếu → phát hiện `apt-get`/`dnf`/`pacman` in lệnh cần `sudo` rõ ràng nếu `geteuid() != 0` | Hỏi user chạy duy nhất 1 lệnh cài `git` nếu hệ điều hành tối giản |
| **`uv` + `Python 3` thực** | `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 \| iex"` (hoặc `winget ... astral-sh.uv`) → `%USERPROFILE%\.local\bin\uv.exe python install --default` | `curl -LsSf https://astral.sh/uv/install.sh \| sh` (hoặc `brew install uv`) → `~/.local/bin/uv python install --default` | `curl -LsSf https://astral.sh/uv/install.sh \| sh` → `~/.local/bin/uv python install --default` | Tránh tuyệt đối `/usr/bin/python` Apple và `WindowsApps\python.exe` stub `[EV-B01]` |
| **`Node.js >= 18` LTS + `npm`** | `winget install --id OpenJS.NodeJS.LTS --exact --silent --accept-package-agreements --accept-source-agreements` (rơi về `Schniz.fnm`) | `brew install node` hoặc `curl -fsSL https://fnm.vercel.app/install \| bash` → `fnm install --lts` | **User-space:** `curl -fsSL https://fnm.vercel.app/install \| bash -s -- --skip-shell` → `fnm install --lts`; ghim đường dẫn tĩnh ổn định vào `~/.local/bin` hoặc `fnm/aliases/default` | Tránh `npm -g` đòi `sudo` trên Linux bằng `npm config set prefix ~/.npm-global` |
| **`agent-lsp` Binary** | `tdq_setup.cai_agent_lsp()` tải zip Release GitHub + **kiểm SHA256** → `~/.local/bin/agent-lsp.exe` | Tarball Darwin `arm64`/`amd64` + SHA256 → `~/.local/bin/agent-lsp` (`chmod 0755`) | Tarball Linux `amd64`/`arm64` + SHA256 → `~/.local/bin/agent-lsp` (`chmod 0755`) | Cho phép bản mirror proxy nếu `api.github.com` bị giới hạn |
| **Language Servers cốt lõi** | `npm i -g pyright typescript-language-server typescript@5` (tuỳ chọn theo project: `gopls`, `rust-analyzer`, `csharp-ls`) | Như Windows | `~/.npm-global/bin` hoặc `fnm` npm prefix user-space (`0 sudo`) | Báo rõ lệnh riêng nếu project có ngôn ngữ đặc thù (`languages.md`) |
| **`graphifyy` (Bậc 7)** | `uv tool install graphifyy` (kế thừa Python từ `uv`) | `uv tool install graphifyy` | `uv tool install graphifyy` | Nếu chỉ có `pipx`, fallback sang `pipx install graphifyy` |
| **`rtk` + `ripgrep (rg)`** | `rtk_integration.install_rtk_and_rg(approve=True)` kiểm SHA256 + collision guard `[EV-B05]` → `~/.local/bin/` | Như Windows (`darwin` asset) hoặc `brew install rtk ripgrep` | Static tarball GitHub Release + SHA256 → `~/.local/bin/{rtk,rg}` | Tự động vá Windows User PATH; cảnh báo shell RC trên POSIX |

> **Xử lý thông minh khi cài mới xong trong Pha 1:** Ngay sau khi cài đặt `Git`/`Node`/`uv`/`Python`/`agent-lsp`/`rg`/`rtk`, script Pha 1 tự ghép các đường dẫn vừa cài (`~/.local/bin`, `%LOCALAPPDATA%\agy\bin`, `C:\Program Files\Git\cmd`, `C:\Program Files\nodejs`, `fnm` active dir, `~/.npm-global/bin`) vào `os.environ["PATH"]` nội bộ của tiến trình cài đặt VÀ ghi bền vững vào hệ thống (Windows Registry `HKCU\Environment` / shell profile `~/.zshrc`, `~/.bashrc`, `~/.profile`). Nhờ vậy Pha 1 hoàn thành mạch lạc **chỉ với 1 lần Restart duy nhất ở cuối Pha 1**!

---

## 3. Trụ cột 2 (`2a`) — One-Shot Manifest Consent, Add-ons & Bảng lệch `Claude -> Antigravity`

### 3.1. Giao thức Duyệt Một Lần (`One-Shot Manifest Consent`)

Thay vì hỏi từng bậc `agent-lsp`, rồi hỏi `pyright`, rồi hỏi `rtk`, rồi hỏi `caveman`, rồi hỏi `chrome-devtools`:
1. **Bước `scan` (Chỉ đọc, < 2s):** `py -3 -X utf8 "${PLUGIN_ROOT}/scripts/tdq_setup.py" --scan-json` xuất 1 JSON Inventory phân làm 3 nhóm:
   - `Runtime & Core` (`Git`, `Node`, `uv`, `Python 3`, `agent-lsp`, Language Servers theo project hoặc bộ tối thiểu `python+ts/js`, `graphifyy`, `agy`).
   - `Add-ons` (`rtk` + `rg`, `caveman` MCP shrink proxy, `chrome-devtools` MCP + Chrome binary check, `tavily-primary` API key check).
   - `Antigravity Configs` (Plugin enable check, `~/.gemini/GEMINI.md` global rules check, CLI `settings.json` allowlist nếu có `agy` CLI, `~/.gemini/config/hooks.json` conflict scan).
2. **Bước `present` (1 block chat duy nhất theo `user-facing-block.md`):**
   - Liệt kê bảng "ĐÃ CÓ (ĐẠT) vs CẦN CÀI (THIẾU) vs CẦN KHÓA API (TÙY CHỌN)".
   - Ghi rõ scope cài đặt (**user-level** trong `~/.local/bin`, `~/.gemini/`, không quyền Admin trừ gói Linux tối giản thiếu `git`), tác dụng và lệnh gỡ (`--uninstall-addons` / `uv tool uninstall` / `npm uninstall -g`).
   - Cảnh báo 1 dòng nếu Antigravity Terminal Sandbox đang bật: bước cài ở lượt kế cần quyền chạy ngoài sandbox (`unsandboxed`) một lần để tải mạng & ghi `~/.local/bin` `[EV-A06]`.
   - Hỏi **duy nhất 1 câu** (kèm lựa chọn điền hoặc bỏ qua `TAVILY_API_KEY`).
3. **Bước `install-all` (Chạy 1 mạch sau khi user duyệt):**
   - Thực thi tuần tự có log chi tiết vào `${PLUGIN_DATA}/logs/setup.log` (`TDQ_LOG=0` tắt được).
   - Xử lý riêng từng add-on như bên dưới.

### 3.2. Thiết kế chuẩn cho từng Add-on (`EV-B03`–`EV-B06`)

- **`RTK + ripgrep` (`scripts/rtk_integration.py`):** Tái sử dụng `install_rtk_and_rg(approve=True)` (`[EV-B05]`) đã có sẵn SHA256 verification, `Rust Type Kit` collision guard và `ensure_rtk_config()` ghi `~/.config/rtk/config.toml` (tắt telemetry, bật SQLite retriever, exclude `grep`/`rg` tránh vòng lặp).
- **`Caveman MCP Shrink Proxy` (Sửa thiết kế `scripts/caveman_config.py` `[EV-B04]`):**
  - Hiện tại `_wrap_server_entry` (`scripts/caveman_config.py:189`) ghi đè `"command": sys.executable`, làm vỡ cấu hình `"command": "node"` đa OS trong `plugins/tdq-workflow-agy/mcp_config.json`.
  - **Thiết kế sửa:** Mở rộng `plugins/tdq-workflow-agy/scripts/tdq_mcp_launcher.mjs` hỗ trợ tham số mode mới `"caveman"`:
    ```json
    "command": "node",
    "args": [
      "${PLUGIN_ROOT}/scripts/tdq_mcp_launcher.mjs",
      "caveman",
      "--",
      "node",
      "${PLUGIN_ROOT}/scripts/tdq_mcp_launcher.mjs",
      "lsp"
    ]
    ```
  - Khi nhận mode `"caveman"`, `tdq_mcp_launcher.mjs` tự tìm Python 3 hợp lệ (bỏ qua `WindowsApps` stub, giống hệt logic đã kiểm chứng ở `tdq_hook_launcher.mjs`!), chạy `-u ${PLUGIN_ROOT}/scripts/tdq_mcp_shrink.py -- ...` với `PYTHONUTF8=1`, `PYTHONUNBUFFERED=1`. Nhờ vậy **100% file `mcp_config.json` không bao giờ chứa đường dẫn cứng của máy cá nhân** kể cả khi đã bật Caveman! (Và khi chạy cho Claude Code ở `~/.claude.json` vẫn giữ tương thích ngược).
- **`Tavily` (`tavily-primary` `[EV-A04]`, `[EV-B06]`):**
  - **Không bao giờ** khai báo trường `"variables"` trong `plugins/tdq-workflow-agy/mcp_config.json`, vì theo tài liệu chính thức `[EV-A04]` làm vậy sẽ khiến `agy plugin install` **tắt toàn bộ plugin `tdq-workflow-agy`** cho tới khi điền biến!
  - Thay vào đó, `tdq-setup` xử lý mềm:
    - Nếu người dùng cung cấp `TAVILY_API_KEY` (hoặc đã có sẵn trong OS env): lưu an toàn vào `${PLUGIN_DATA}/secrets.env` (chế độ file `0600` trên POSIX, ACL user-only trên Windows; **không bao giờ in key ra stdout/log/brief**) → `tdq_mcp_launcher.mjs` tự đọc nạp `TAVILY_API_KEY` (nếu chưa có trong `process.env`) trước khi spawn `tavily-mcp@latest`.
    - Nếu người dùng bỏ qua: ghi `tavily_status: "skipped_no_key"` vào `setup-state.json`, nhắc trong báo cáo dùng tạm `search_web` built-in và cách bổ sung sau (`tdq_setup.py --set-tavily-key`).
- **`Chrome DevTools MCP` (`scripts/tdq_devtool_mcp.py` `[EV-B03]`):**
  - Plugin `mcp_config.json` đã gắn sẵn `"chrome-devtools"` chạy qua `tdq_mcp_launcher.mjs` với `--userDataDir=${PLUGIN_DATA}/chrome-devtools-profile`.
  - Mở rộng `tdq_devtool_mcp.py` hỗ trợ chế độ Antigravity: kiểm tra trình duyệt Chromium/Chrome/Edge thực tế trên 3 OS (nếu chưa có trên máy Linux/macOS/Windows thì báo ở mục Optional, không cài ép buộc hoặc đánh dấu `optional_pending`), tạo sẵn profile `${PLUGIN_DATA}/chrome-devtools-profile`, và kiểm tra kết nối CDP không chặn Core Gate.

### 3.3. Bảng kiểm toán đầy đủ điểm lệch `Claude Code -> Antigravity` cần đồng bộ (`EV-B01`–`EV-B08`)

| Thành phần cần nâng cấp | Điểm lệch hiện tại (`path:line`) | Mục tiêu Antigravity mới |
|---|---|---|
| `scripts/tdq_setup.py` | `DUONG_INSTRUCTION = "~/.claude/CLAUDE.md"` (L72), `khai_server_mcp` → `~/.claude.json` (L368), `kiem_plugin_user` → `~/.claude/plugins/` (L554, L706), `_cap_nhat_permissions_allow` → `~/.claude/settings.json` (L637), `doc_phien_ban_plugin` thiếu `plugin.json` AGY (L1508), `la_project_that` thiếu `.agents/` (L755) | Tách `HostAdapter`: hỗ trợ `--host antigravity|claude|auto`, kiểm/cài rule ở plugin `rules/AGENTS.md` + optional sync `~/.gemini/GEMINI.md` (`<= 24KB`), đọc `agy plugin list --json`, kiểm `~/.gemini/config/mcp_config.json` + CLI `~/.gemini/antigravity-cli/settings.json`, lưu trạng thái ở `${PLUGIN_DATA}/setup-state.json` |
| `scripts/tdq_lsp.py` | `_all_mcp_configs` kiểm `~/.claude.json` và path sai `~/.gemini/antigravity/mcp_config.json` (L299-303); `bac4_quyen_tool` đọc `~/.claude/settings.json` (L472); `hook_xung_dot` quét `~/.claude/plugins/` (L547-583) | Sửa đúng đường dẫn `~/.gemini/config/mcp_config.json`; hỗ trợ Antigravity plugin `mcp_config.json` ở Bậc 4; quét xung đột hook ở `~/.gemini/config/plugins/*/hooks.json`, `~/.gemini/config/hooks.json` và `.agents/hooks.json` |
| `scripts/setup_status.py` | `CAU_HINH_CLAUDE = "~/.claude.json"` (L41), `claude mcp list` (L117, L329-357) | Bổ sung `antigravity` collector đọc `agy plugin list --json`, `agy plugin validate --json` và đọc đọc kết quả `Simulate Test` từ `${PLUGIN_DATA}/setup-state.json` |
| `scripts/tdq_devtool_mcp.py` | `setup_devtool_mcp` ghi raw `npx` vào `~/.claude.json` & `~/.claude/settings.json` (L139-256) | Thêm `check_devtool_setup(host="antigravity")` kiểm trực tiếp `${PLUGIN_ROOT}/mcp_config.json`, `${PLUGIN_DATA}/chrome-devtools-profile` và binary Chrome/Edge/Chromium |
| `scripts/caveman_config.py` | `_wrap_server_entry` ghi `"command": sys.executable` (L189) | Trên Antigravity plugin, bọc qua `"command": "node"` + `tdq_mcp_launcher.mjs caveman -- ...` giữ nguyên 100% tính đa OS |
| `plugins/tdq-workflow-agy/skills/tdq-setup/` | `SKILL.md:54-56,110-122` và `chrome-devtools-mcp-guide.md:11,27` còn nhắc `~/.claude*` và chưa có luồng 2 pha trước/sau restart | Viết lại thành Runbook 2 pha rõ ràng (Pha 1 Bootstrap + One-Shot Manifest → Restart → Pha 2 Auto-Resume + 6-Layer Simulate Test); không nhúng logic Python vào `.md` |

---

## 4. Trụ cột 3 (`3a`) — Máy Trạng Thái qua Restart & Auto-Resume Hook `PreInvocation`

### 4.1. Nơi lưu bền vững (`${PLUGIN_DATA}`) & Schema JSON

Dựa trên thực nghiệm đĩa `[EV-C02]` và tài liệu chính thức `[EV-A04]`:
- Thư mục gốc bền vững `resolve_plugin_data_dir()`:
  1. `os.environ.get("PLUGIN_DATA")` (nếu khác rỗng — Antigravity truyền cho cả plugin command hooks lẫn plugin MCP servers `[EV-A04]`).
  2. `<ANTIGRAVITY_APP_DATA_DIR>/plugin_data/tdq-workflow-agy/` (như `C:\Users\<user>\.gemini\antigravity\plugin_data\tdq-workflow-agy` `[EV-C02]`).
  3. `~/.gemini/antigravity/plugin_data/tdq-workflow-agy/` (fallback khi chạy ngoài IDE/CLI).
- Hai tệp được quản lý nguyên tử (`tempfile + os.replace`):
  1. **`setup-pending.flag`** (tệp cờ rỗng 0 byte): CHỈ tồn tại khi máy đang chờ restart hoặc đang chạy xác minh hậu restart; bị **xóa ngay** khi Pha 2 hoàn tất (`status = "verified"` hoặc TTL hết hạn / user hủy `--reset-setup`).
  2. **`setup-state.json`**: lưu toàn bộ trạng thái thiết lập đa pha:

```json
{
  "schema_version": 1,
  "status": "awaiting_restart",
  "plugin_version": "0.105.0",
  "platform": "win32",
  "arch": "x64",
  "created_at": "2026-11-22T15:10:00+07:00",
  "ttl_expires_at": "2026-11-23T15:10:00+07:00",
  "host_fingerprint": {
    "ancestor_pid": 9872,
    "ancestor_name": "Antigravity.exe",
    "ancestor_created_at": "2026-11-21T21:55:08+07:00",
    "ls_pid": 23192,
    "ls_address": "localhost:56861",
    "surface": "ide_or_app"
  },
  "phase1_installed": {
    "runtime": ["uv", "python3", "node", "git"],
    "core": ["agent-lsp", "pyright", "typescript-language-server", "graphifyy"],
    "addons": {
      "rtk": "installed",
      "caveman": "wrapped",
      "chrome-devtools": "ready",
      "tavily-primary": "skipped_no_key"
    },
    "needs_restart_reasons": ["path_updated", "mcp_caveman_wrapped", "hooks_registered"]
  },
  "resume_attempts": 0,
  "last_resume_fingerprint": null,
  "verify_result": null
}
```

### 4.2. Giải thuật `Host Session Fingerprint` & Máy trạng thái trong `PreInvocation`

```
Mọi lượt chạy PreInvocation (hooks/rust/tdq-dispatch & dispatch.py fallback)
  │
  ├── [Kiểm nhanh O(1): setup-pending.flag có tồn tại?]
  │     └── KHÔNG → Rẽ vào đường nóng TDQ bình thường (< 0.05 ms, 0 parse JSON)
  │
  └── CÓ → Đọc setup-state.json + kiểm tra TTL (24h)
        │
        ├── status == "awaiting_restart":
        │     ├── Đo current_fp (tìm ancestor Antigravity/language_server/agy PID + start_time + ANTIGRAVITY_LS_ADDRESS)
        │     ├── Nếu current_fp == state.host_fingerprint:
        │     │     └── [CHƯA RESTART THẬT] Bơm systemMessage nhẹ nhắc tắt/mở lại Antigravity
        │     │         (hoặc dùng `py -3 .../tdq_setup.py --confirm-restarted` nếu chạy trên CLI môi trường đặc biệt)
        │     └── Nếu current_fp != state.host_fingerprint (và chưa hết TTL):
        │           └── [ĐÃ RESTART THẬT] Đổi status = "validating_after_restart",
        │               lưu last_resume_fingerprint = current_fp, tăng resume_attempts += 1,
        │               BƠM [TDQ:SETUP-RESUME] (kèm metadata.user_markdown) lệnh cho Agent chạy ngay:
        │               `python3 "${PLUGIN_ROOT}/scripts/tdq_setup.py" --post-restart-verify`
        │
        ├── status == "validating_after_restart":
        │     └── Nếu current_fp == last_resume_fingerprint trong CÙNG lượt → KHÔNG bơm lặp lại tránh vòng lặp
        │         Nếu là cuộc chat MỚI khác và chưa verify xong → nhắc chạy tiếp `--post-restart-verify` (tối đa 3 lần trước khi tự hạ sang manual)
        │
        └── Hoàn tất verified / degraded → XÓA `setup-pending.flag`, giữ `setup-state.json` làm hồ sơ sức khỏe máy
```

**Đảm bảo hiệu năng & an toàn cho đường nóng `tdq-dispatch` `[EV-B07]`, `[EV-C01]`:**
- Ở 99,99% lượt chat bình thường sau cài đặt, `setup-pending.flag` không tồn tại nên Rust `tdq-dispatch` chỉ tốn đúng **1 lời gọi syscall `stat()` (`< 0.05 ms`)**; không bao giờ chạy PowerShell hay đọc JSON.
- Ngay trong giai đoạn `awaiting_restart`, việc đọc PID tổ tiên (`CreateToolhelp32Snapshot` + `GetProcessTimes` trong Rust/Python `ctypes` trên Windows; `/proc/<pid>/stat` trên Linux; `ps -o ppid=,lstart=` chỉ 1–3 tiến trình trên macOS) mất **`< 2 ms`**, tuyệt đối không gọi `Get-CimInstance` (`~300 ms`).

---

## 5. Trụ cột 4 (`4a`) — Đặc tả Bộ `Simulate Test` 6 Tầng trên Sandbox Tạm

### 5.1. Nguyên tắc bất biến của `tdq_simulate_verify.py` (chạy bởi `--post-restart-verify`)
1. **Không phụ thuộc thư mục đang mở:** Dù người dùng vừa mở lại Antigravity ở màn hình trống (`Home`, chưa chọn project) hay mở 1 kho code trống, bộ kiểm thử tự dựng sandbox trong `tempfile.TemporaryDirectory(prefix="tdq_sim_")` và xóa sạch trong khối `finally:` (`O(1)` rác sau khi xong) `[EV-C03]`.
2. **Bảo toàn tuyệt đối cài đặt cá nhân:** Tạo bản chụp kiểm chứng danh sách tệp của `~/.gemini/config/` (và biến `TDQ_PROJECT_DIR=<sandbox>`) để các lượt bắn thử hooks không làm bẩn bất kỳ project hay cấu hình thật nào `[EV-C03]`.
3. **Log service bật mặc định:** Ghi chi tiết có timestamp ISO-8601 vào `${PLUGIN_DATA}/logs/setup-verify.log` và `stderr` (`TDQ_LOG=0` tắt được).
4. **Phân tách 2 hạng Cổng kiểm:** **`Core Gate`** (bắt buộc 100% PASS mới gắn `verified`) vs **`Optional Add-on Gate`** (`chrome-devtools` khi không có trình duyệt, `tavily-primary` khi `skipped_no_key` → ghi `SKIPPED` kèm hướng dẫn, không đánh trượt Core).

### 5.2. Đặc tả chi tiết 6 Tầng Kiểm Thử Giả Lập (`H4`)

| Tầng | Đối tượng kiểm | Cách giả lập thật trên Sandbox | Điều kiện PASS & Ngưỡng thời gian | Hạng cổng |
|---|---|---|---|---|
| **T1 — Plugin & Quyền Thực Thi** | Gói plugin đang chạy (`${PLUGIN_ROOT}`) | Chạy `agy plugin validate --strict --json "${PLUGIN_ROOT}"`, `agy plugin list --json`, kiểm quyền `0755` cho `bin/*` & `scripts/*.mjs` trên POSIX, kiểm `python`/`node`/`uv`/`git` trên `PATH` thật hậu restart | `0` error/warning; plugin `enabled: true`, đủ `skills/agents/rules/mcpServers/hooks`; `< 5s` `[EV-A01]`, `[EV-C03]` | **Core** |
| **T2 — Hooks 6 Events E2E** | `tdq_hook_launcher.mjs` + `tdq-dispatch` Rust/Python | Tạo `docs/tdq/state.json` mẫu trong `<sandbox>`, bắn thật JSON `stdin` qua cả 6 events (`SessionStart`, `PreInvocation`, `PreToolUse`, `PostToolUse`, `PostInvocation`, `Stop`) | Toàn bộ `exit 0`, stdout là JSON hợp lệ (`injectSteps` / `decision` / `{}`); có log `route=hot` nếu dùng Rust binary hoặc fallback Python sạch; `< 5s` `[EV-A02]`, `[EV-B07]` | **Core** |
| **T3 — Live MCP JSON-RPC Stdio** | `tdq_mcp_launcher.mjs` (`lsp`, `caveman`, `chrome-devtools`, `tavily`) | **Dùng `subprocess.Popen` giữ `stdin` mở `[EV-C04]`**: gửi `initialize` → chờ `result.capabilities` → gửi `notifications/initialized` + `tools/list` → đọc kết quả rồi đóng pipe cleanly | `lsp` trả danh sách tools chứa `start_lsp`, `find_references`, `list_symbols`; nếu bật `caveman`, verify proxy trả về output gọn hợp lệ qua Node launcher; `< 15s` / server | **Core** (`lsp`/`caveman`) · **Optional** (`chrome-devtools`/`tavily`) |
| **T4 — 3-Layer Search Effect Real Probe** | `rg` + `agent-lsp` + `graphify` trên 2 file thật `.py` & `.js` trong sandbox | Đặt sẵn `app.py`, `caller.py`, `index.js`, `pyrightconfig.json`, `jsconfig.json` vào `<sandbox>`: (a) chạy `rg` tìm token; (b) gọi `start_lsp` + `find_references` thực tế trên `app.py`/`index.js` qua MCP pipe; (c) chạy `graphify extract . --code-only` + `graphify query` | `rg` trả đúng dòng (`>= 1` hit); `agent-lsp` `find_references` trả đúng số tham chiếu chéo file (`>= 2` locations, chứng minh `pyright` + `typescript-language-server` chạy thật!); `graphify` sinh `graph.json` và trả node; `< 30s` `[EV-C04]` | **Core** |
| **T5 — Add-on RTK & User Rules** | `rtk` + `config.toml` + `GEMINI.md` / `rules/AGENTS.md` | Chạy `rtk --version` (xác nhận không phải Rust Type Kit), `rtk ls` trên sandbox; đọc kiểm `rules/AGENTS.md` (và `~/.gemini/GEMINI.md` nếu có) đạt `<= 24,000` bytes `[EV-A05]` | `rtk` trả output hợp lệ; `probe_caveman` khớp trạng thái user chọn; rule size dưới ngưỡng Antigravity; `< 5s` `[EV-B05]` | **Core** |
| **T6 — Subagent & Full Readiness Probe** | Chuỗi kết thúc Pha 2 của Agent | Sau khi script CLI trả JSON `Core Gate PASS`, Agent (hoặc bài test tự động khi `POST_RESTART_PROBE_SUBAGENT=1`) thực hiện **1 lời gọi thật `mcp_tdq-workflow-agy_lsp_*`** (nếu MCP đã load trong phiên IDE mới) và **1 lời gọi subagent `tdq-explorer`** nhẹ kiểm đọc `<sandbox>/app.py` (hoặc tệp trạng thái `setup-state.json`) | Xác nhận trên chính tiến trình Antigravity sau Restart cả **MCP tool namespace thật** lẫn **Subagent** đều gọi được không vướng allow-list/timeout; `< 20s` | **Core** |

---

## 6. Phản biện Counterfactual 4 Góc Khuất Lớn (`QC-I3` & `§6 Q4`)

| Góc khuất đối nghịch (Giả định làm hỏng thiết kế) | Kịch bản sự cố thực tế nếu chủ quan | Cách thiết kế phản biện và xử lý dứt điểm | Nhãn tin cậy |
|---|---|---|---|
| **Góc khuất 1 — Người dùng chỉ bấm "New Chat" hoặc gõ tiếp trong tab hiện tại chứ KHÔNG restart IDE thật `[EV-C01]`** | Nếu `PreInvocation` chỉ check cờ `setup-pending.flag` rồi chạy ngay Pha 2, biến `PATH` cũ ở tiến trình cha khiến `agent-lsp`/`node`/`pyright` vừa cài vẫn `not found` và MCP server vẫn giữ env cũ chưa có `TAVILY_API_KEY`/Caveman → `Simulate Test` lỗi giả | Dùng **`Host Session Fingerprint`** (`ancestor_pid + created_at + ls_address`): trong cùng tiến trình IDE, dù mở tab chat mới thì các giá trị này vẫn GIỐNG hệt lúc kết thúc Pha 1 → hook **khóa cứng**, chỉ nhắc user đóng hẳn và mở lại Antigravity IDE. Chỉ cho mở tay bằng cờ rõ ràng `--confirm-restarted` khi user chạy môi trường container đặc biệt tái dùng PID 1 | **Verified** |
| **Góc khuất 2 — Bẫy `WindowsApps\python.exe` + trễ lan truyền `PATH` Windows sau `winget`/`uv` `[EV-B01]`, `[EV-C03]`** | Máy Windows 11 sạch bật sẵn App Execution Alias trỏ `python.exe` tới Microsoft Store; hoặc vừa chạy xong `winget install OpenJS.NodeJS.LTS` / `uv` thì tiến trình shell đang mở vẫn giữ `%PATH%` cũ chưa cập nhật Registry mới | Script bootstrap & Pha 1 luôn kiểm `WindowsApps` trong `shutil.which` (`isWindowsAppsStub`), đọc trực tiếp `HKCU\Environment` + `HKLM\...\Environment` và ghép đường dẫn cài mặc định (`%USERPROFILE%\.local\bin`, `C:\Program Files\nodejs`, `C:\Program Files\Git\cmd`, `fnm`) vào `PATH` của phiên chạy hiện tại, đồng thời ghi sạch thứ tự ưu tiên vào đầu User `PATH` để sau 1 lần Restart mọi công cụ đều đứng trên `WindowsApps` | **Verified** |
| **Góc khuất 3 — Máy Linux tối giản không có `sudo` hoặc headless không có trình duyệt Chrome `[EV-A06]`, `[EV-A08]`** | Chạy `apt-get install nodejs` hay cài `google-chrome` bị kẹt hỏi mật khẩu `sudo` hoặc fail trong Docker/WSL/cloud VM; hoặc `chrome-devtools` làm đỏ toàn bộ `Simulate Test` trên server SSH | Toàn bộ toolchain cốt lõi (`uv` + `Python 3`, `fnm` + `Node LTS`, `agent-lsp`, `rg`, `rtk`, `graphifyy`) được thiết kế đi 100% **user-space (`~/.local/`) không cần `sudo`**. Chỉ `git` trên máy quá trắng mới kiểm xem thiếu thì báo 1 lệnh gọn. Riêng `chrome-devtools` được tách xuống `Optional Add-on Gate`: thiếu binary Chrome chỉ báo `SKIPPED` có hướng dẫn, không làm rớt `Core Gate` | **Verified** |
| **Góc khuất 4 — Sửa `hooks.json` / `mcp_config.json` trực tiếp trong `~/.gemini/config/plugins/` bị ghi đè khi update plugin hoặc vi phạm `agy plugin validate` `[EV-A04]`** | Nếu `setup` ghi state (`setup-state.json`) hoặc mật khẩu (`TAVILY_API_KEY`) hay bật Caveman bằng đường dẫn tuyệt đối trực tiếp vào thư mục `~/.gemini/config/plugins/tdq-workflow-agy/`, lúc `agy plugin install` cập nhật bản mới sẽ bị xóa sạch state/secrets hoặc rớt `agy plugin validate` | State, logs, Chrome profile và `secrets.env` được đặt 100% ở **`${PLUGIN_DATA}`** (bền vững qua mọi lần nâng cấp plugin `[EV-A04]`). File `mcp_config.json` của plugin khi bật Caveman chỉ dùng biến `${PLUGIN_ROOT}` + launcher `node` đa OS, giữ `0 findings` trên `agy plugin validate --strict --json`, và tự ghi ý định bật add-on (`caveman: true`) vào `setup-state.json` để có thể tự khôi phục lại chỉ với 1 lệnh sau mỗi lần cập nhật plugin | **Verified** (riêng tính năng auto-reapply sau update là **Inferred** dựa trên `[EV-A04]`) |

---

## 7. Lộ trình Đề xuất Triển Khai (`Build Roadmap` cho Request kế tiếp)

Nếu người dùng duyệt đề xuất này và mở request triển khai (`feature`), đề xuất chia thành **4 đợt gọn sạch** kế thừa trực tiếp mã nguồn đang có:

1. **Đợt B1 — Lõi Trạng Thái Bền Vững & Antigravity Host Adapter (~2 task):**
   - Tạo `scripts/tdq_setup_state.py` quản lý `${PLUGIN_DATA}/setup-state.json`, `setup-pending.flag`, TTL 24h và `Host Session Fingerprint` đa OS (Win32 API / `/proc` / `ps`).
   - Refactor/tách adapter trong `scripts/tdq_lsp.py`, `scripts/tdq_setup.py`, `scripts/setup_status.py` và `scripts/tdq_devtool_mcp.py` để dùng đúng đường dẫn Antigravity (`~/.gemini/config/`, `~/.gemini/antigravity-cli/settings.json`, `~/.gemini/GEMINI.md`, `agy plugin list/validate`) mà vẫn giữ tương thích ngược cho nhánh `main` (Claude Code).
2. **Đợt B2 — Bootstrap Cửa 0 & Sửa Launcher Đa OS cho Caveman / Tavily (~2 task):**
   - Bổ sung mode `"caveman"` và đọc mềm `${PLUGIN_DATA}/secrets.env` vào `plugins/tdq-workflow-agy/scripts/tdq_mcp_launcher.mjs`, cập nhật `scripts/caveman_config.py` để bọc Caveman không dùng `sys.executable`.
   - Thêm `scripts/bootstrap.ps1` + `scripts/bootstrap.sh` (tải qua `release/antigravity` hoặc `dev`) kèm cờ `--scan-json`, `--apply-manifest`, `--set-tavily-key` vào `scripts/tdq_setup.py` + `scripts/tdq_setup_probe.mjs` (fallback khi máy mới chưa có Python).
3. **Đợt B3 — Điểm Móc Auto-Resume Sau Restart (`PreInvocation` + `SessionStart`) (~1 task):**
   - Bổ sung kiểm tra `O(1)` `setup-pending.flag` và đối chiếu `Host Session Fingerprint` vào `hooks/rust/tdq-dispatch/src/events/pre_invocation.rs` (cùng Python fallback trong `hooks/scripts/prompt_context.py`) để phát `[TDQ:SETUP-RESUME]` có `metadata.user_markdown`, và cập nhật `SessionStart` nhắc setup máy khi chưa verified.
   - Build lại bộ nhị phân Rust đa OS (`Windows`, `macOS`, `Linux`) và đồng bộ `plugins/tdq-workflow-agy/`.
4. **Đợt B4 — Bộ `Simulate Test` 6 Tầng & Cập nhật Skill `tdq-setup` (~2 task):**
   - Tạo `scripts/tdq_simulate_verify.py` (gắn vào `tdq_setup.py --post-restart-verify`) chạy đủ 6 tầng trên sandbox tạm bằng interactive `Popen` JSON-RPC pipes + tự dọn rác + phân hạng `Core Gate` / `Optional Add-on Gate`.
   - Cập nhật `skills/tdq-setup/SKILL.md` (và build sang `plugins/tdq-workflow-agy/skills/tdq-setup/SKILL.md`) theo quy trình One-Shot Manifest → Restart → Auto-Resume + Subagent live probe cuối phiên, kèm bộ unit test cô lập (`TDQ_KHONG_CHAM_MAY=1` + mock Win/macOS/Linux + `agy plugin validate --strict`).
