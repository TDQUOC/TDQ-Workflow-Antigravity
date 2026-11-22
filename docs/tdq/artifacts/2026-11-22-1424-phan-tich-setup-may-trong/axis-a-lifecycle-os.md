# Shard Trục A — Vòng đời Antigravity, ranh giới Restart và Bootstrap đa hệ điều hành

Ngày: 2026-11-22 · Task: `T1.1` · Nguồn chính: tài liệu `.md` chính thức từ `https://antigravity.google/docs/` (đã lưu bản thô vào `raw/EV-A01..A10*.txt`), built-in skills (`antigravity-guide`, `plugin`, `agy-customizations`) và tra cứu chuẩn gói đa OS qua `tavily-primary`.

## 1. Kiến thức cốt lõi về cấu hình & ranh giới Restart của Google Antigravity

| Thành phần | Đường dẫn Antigravity chuẩn (`EV-*`) | Khi sửa trong phiên đang chạy thì sao? | Có cần Restart IDE/CLI không? |
|---|---|---|---|
| **Installed Plugins** | `~/.gemini/config/plugins/<dir>/` và `.agents/plugins/` `[EV-A01]` | Skill mới (`SKILL.md`) có `/skills reload` trên CLI hoặc tự nhận ở lượt sau `[EV-A01]`, `[EV-A04]` (`A04_cli_ref:52`), nhưng plugin bundle thêm `hooks.json` / `mcp_config.json` mới | **Nên Restart** để nạp đồng bộ hooks, MCP servers và biến `${PLUGIN_DATA}` |
| **Lifecycle Hooks** | `<plugin>/hooks.json`, `~/.gemini/config/hooks.json`, `.agents/hooks.json` `[EV-A02]` | Đọc `stdin` JSON (`camelCase`), trả `stdout` JSON; lệnh hook plugin chạy ở `cwd = <plugin-root>` và nhận env `PLUGIN_ROOT` + `PLUGIN_DATA` `[EV-A04]` | **CÓ (Restart hoặc phiên mới)** nếu đăng ký hook mới/sửa `hooks.json` |
| **MCP Servers** | `<plugin>/mcp_config.json`, `~/.gemini/config/mcp_config.json`, `.agents/mcp_config.json` `[EV-A03]` | Language Server quản lý process stdio con; tool schema cache tại `<app-data-dir>/mcp/<server>/`. Nếu trùng tên, server đang chạy giữ chỗ (`EV-A07:141`) | **CÓ (Restart IDE hoặc `/mcp` reconnect)** để process MCP mới chạy với `PATH` / env mới (`TAVILY_API_KEY`, wrapper `caveman`) |
| **User Global Rules** | `~/.gemini/GEMINI.md`, `~/.gemini/AGENTS.md`, `~/.gemini/config/GEMINI.md`, `~/.gemini/config/rules/*.md` `[EV-A05]` | Giới hạn `24,000` bytes/file và tổng `20,000` tokens; đọc lại theo phiên / prompt | Tải ở phiên chat mới; **Restart** bảo đảm nạp sạch sau khi ghi từ setup |
| **Environment `PATH` OS** | Registry Windows (`HKCU\Environment`), `~/.zshrc`, `~/.bashrc`, `~/.profile` | Tiến trình cha Antigravity (Electron IDE/App hoặc terminal mở trước) giữ nguyên bảng env lúc khởi động | **BẮT BUỘC Restart Antigravity hoàn toàn** (tắt hẳn tiến trình IDE/App rồi mở lại) để tiến trình cha nhận `PATH` mới (`node`, `python3`, `uv`, `agent-lsp`, `rg`, `rtk`) `[EV-A06]` |

### Phát hiện đặc biệt ảnh hưởng thiết kế
1. **`PLUGIN_DATA` và ranh giới thay thế trong `hooks.json` vs `mcp_config.json` `[EV-A04]`:**
   - Trong `mcp_config.json`, Antigravity **tự nội suy** `${PLUGIN_ROOT}`, `${PLUGIN_DATA}` và `${VAR}` bên trong `args`, `cwd`, `env` **lẫn** export env vars `PLUGIN_ROOT`, `PLUGIN_DATA`.
   - Trong `hooks.json`, Antigravity **KHÔNG nội suy** chuỗi `${PLUGIN_ROOT}` hay `${PLUGIN_DATA}` trong trường `"command"`, nhưng **có export sẵn biến môi trường** `PLUGIN_ROOT` và `PLUGIN_DATA` cho tiến trình con (riêng `PLUGIN_DATA` chỉ guaranteed cho plugin đã cài chính thức, nên hook/script cần fallback sang `~/.gemini/config/plugin-data/tdq-workflow-agy/` khi chạy ở chế độ dev/local symlink!).
2. **Định danh lệch từ Claude Code (`EV-A05` vs hiện trạng):**
   - Toàn bộ cấu hình của Antigravity dùng `~/.gemini/config/` (rules ở `~/.gemini/GEMINI.md` hoặc `~/.gemini/config/rules/*.md`, hooks ở `~/.gemini/config/hooks.json`, MCP ở `~/.gemini/config/mcp_config.json`, CLI settings/permissions ở `~/.gemini/antigravity-cli/settings.json`), tuyệt đối không dùng `~/.claude.json` hay `~/.claude/settings.json`.
   - Plugin Antigravity cấm chỉnh tay `~/.gemini/config/config.json` (tệp `0600` dễ clobber); thay vào đó dùng `agy plugin enable/disable/validate` hoặc link UI `customization://<dir>` `[EV-A05]`.
3. **Cảnh báo Terminal Sandbox (`EV-A06`):**
   - Ở chế độ `Default`/`Auto`, Antigravity chạy `run_command` trong OS sandbox (chỉ cho ghi workspace + `TEMP`, khóa mạng). Việc cài đặt `winget`, `uv`, `npm -g`, `curl` ở Pha 1 cần ghi ra ngoài workspace và tải mạng → thiết kế `tdq-setup` phải chủ động gom lệnh vào pha chạy được đánh dấu cần cấp quyền `unsandboxed` một lần rõ ràng.

## 2. Ma trận Bootstrap đa hệ điều hành cho Máy Trống Tinh (`EV-A07`, `EV-A08`)

Nguyên tắc vàng: **Ưu tiên user-space không cần quyền Admin/sudo**, chuẩn hóa đường dẫn cứng dự phòng ngay trong phiên cài đầu để **chỉ cần Restart 1 lần duy nhất ở cuối Pha 1**.

| Thành phần | Windows 10/11 | macOS (Apple Silicon / Intel) | Linux (Ubuntu/Debian/Fedora/Arch, không cần sudo ở đường chính) |
|---|---|---|---|
| **Cửa 0: Antigravity (`agy`)** | `irm https://antigravity.google/cli/install.ps1 \| iex` (hoặc Antigravity App/IDE từ `antigravity.google/download`) | `curl -fsSL https://antigravity.google/cli/install.sh \| bash` (hoặc `.dmg`) | `curl -fsSL https://antigravity.google/cli/install.sh \| bash` (hoặc `.tar.gz`/AppImage) |
| **Git** | `winget install --id Git.Git --exact --silent --accept-package-agreements --accept-source-agreements` | `xcode-select --install` (hoặc `brew install git`) | `sudo apt-get install -y git` / `dnf install -y git` / `pacman -S --noconfirm git` (chỉ bước này cần root nếu máy tối giản chưa có `git`) |
| **`uv` + `Python 3` thực (không root, tránh stub WindowsApps)** | `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 \| iex"` (hoặc `winget ... astral-sh.uv`) → `uv python install --default` | `curl -LsSf https://astral.sh/uv/install.sh \| sh` (hoặc `brew install uv`) → `uv python install --default` | `curl -LsSf https://astral.sh/uv/install.sh \| sh` → `~/.local/bin/uv python install --default` (đặt `python` & `python3` vào `~/.local/bin`) |
| **`Node.js` LTS + `npm`** | `winget install --id OpenJS.NodeJS.LTS --exact --silent --accept-package-agreements --accept-source-agreements` (rơi về `Schniz.fnm` nếu không cần admin) | `brew install node` (nếu có brew) hoặc user-space `curl -fsSL https://fnm.vercel.app/install \| bash` → `fnm install --lts` | **User-space ưu tiên (0 sudo):** `curl -fsSL https://fnm.vercel.app/install \| bash -s -- --skip-shell && ~/.local/share/fnm/fnm install --lts` (symlink/copy vào `~/.local/bin` hoặc export PATH); fallback `apt`/`dnf` |
| **TDQ-Workflow Plugin** | `agy plugin install https://github.com/TDQUOC/TDQ-Workflow-Antigravity/tree/release/antigravity` | Tương tự | Tương tự |
| **Core Search & Add-on Binaries** | `agent-lsp` (Go release `.zip`), `pyright` + `typescript-language-server` (`npm i -g`), `graphifyy` (`uv tool install`), `rg` + `rtk` (GitHub Release `.zip` / `winget BurntSushi.ripgrep.MSVC`), `caveman` (wrap MCP qua script) | `agent-lsp` (tarball), `npm i -g pyright typescript-language-server typescript`, `uv tool install graphifyy`, `brew install ripgrep rtk` (hoặc release tarball), `caveman` | `agent-lsp` (tarball), `fnm exec ... npm i -g` / prefix `~/.npm-global` (`0 sudo`), `uv tool install graphifyy`, static tarball `rg` + `rtk` vào `~/.local/bin` |
