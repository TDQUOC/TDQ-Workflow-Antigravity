# TDQ-Workflow-Antigravity

Hệ sinh thái đóng gói và phân phối **TDQ-Workflow (`v0.106.0` — nhánh phát hành `release/antigravity`)** chạy **Native** trên **Google Antigravity** (`Windows`, `macOS`, `Linux`) với MCP, 6 Lifecycle Hooks, 8 Subagents, 12 Skills và 10 Two-Tier Rules.

## Cài đặt 1 lệnh từ GitHub (Windows / macOS / Linux)

Trên bất kỳ máy nào đã cài `agy` (Antigravity CLI) và `Node.js`:

```bash
agy plugin install https://github.com/TDQUOC/TDQ-Workflow-Antigravity/tree/release/antigravity
```

- **Hooks & MCP đa nền tảng:** `hooks.json` chạy qua `node scripts/tdq_hook_launcher.mjs` để tự chọn binary Rust theo OS/arch kèm fallback Python và hỗ trợ `setup-pending.flag`. `mcp_config.json` chạy qua `node ${PLUGIN_ROOT}/scripts/tdq_mcp_launcher.mjs` tích hợp bọc Caveman thuần Node (không dùng `sys.executable`) cùng `${PLUGIN_DATA}/chrome-devtools-profile`, không còn đường dẫn cứng máy cá nhân.
- **Thiết lập Zero-to-Full (`setupfully tdq-workflow` & `/tdq-setup`):** Trên máy mới chạy Gate-0 (`.\scripts\bootstrap.ps1` hoặc `./scripts/bootstrap.sh`), sau đó gõ `setupfully tdq-workflow` trong Antigravity hoặc chạy `tdq_setup.py --setupfully` / `--scan-json` → restart Antigravity → `--post-restart-verify` để kiểm chứng 6 tầng `T1`–`T6` (`scripts/tdq_simulate_verify.py`, tách `Core Gate` và `Optional Add-on Gate`).
- **Khởi tạo tìm kiếm 3 tầng & bí mật:** Chạy `py -3 scripts/tdq_lsp.py check` cho LSP/Graphify và `py -3 scripts/tdq_setup.py --set-tavily-key "<key>"` để lưu `TAVILY_API_KEY` vào `secrets.env` riêng tư.
- **Cập nhật phiên bản mới:** Antigravity không tự kiểm tra hay tự cập nhật plugin cài từ GitHub URL; khi có phiên bản mới trên `release/antigravity`, chạy lại đúng lệnh `agy plugin install` ở trên để ghi đè bản mới.

## Cấu Trúc Workspace & Công Cụ Dành Cho Nhà Phát Triển

- **`plugins/tdq-workflow-agy/`** — Gói plugin Antigravity (`tdq-workflow-agy`) biên dịch từ `dev` (`plugin.json`, `hooks.json`, `mcp_config.json`, `manifest.json`, `rules/`, `skills/`, `agents/`, `hooks/scripts/`, `scripts/`).
- **`.agents/plugins.json`** — Cấu hình discovery cục bộ trỏ `./plugins` khi phát triển trực tiếp trong repo.
- **`tools/build_agy_plugin.py`** — Biên dịch sang `plugins/tdq-workflow-agy/` kèm bản vá đa OS (`tools/patches/`, trong đó có `agy_launchers.py` & `agy_manifests.py`).
- **`scripts/build_portable.py --sinh-release-agy`** — Xuất bản nhánh sạch `release/antigravity` trực tiếp từ `plugins/tdq-workflow-agy/` bằng Git plumbing mà không chạm thư mục làm việc hoặc nhánh `main` (Claude Code).
- **`tools/install_agy_plugin.py`** — Trình cài đặt cục bộ vào `~/.gemini/config/plugins/tdq-workflow-agy` (hỗ trợ `--dry-run`, `--target`, `--sync-local-mcp`).
- **`tools/run_full_verification.py`** & **`tests/`** — Bộ kiểm chứng tổng lực, kiểm định `agy plugin validate --strict --json`, launcher đa OS và E2E xuất bản/cài đặt nhánh release.

## Lệnh Build, Xuất Bản & Kiểm Chứng (PowerShell)

```powershell
# 1. Biên dịch lại plugin sạch từ mã nguồn hiện tại
$env:PYTHONDONTWRITEBYTECODE='1'; py -3 -B tools/build_agy_plugin.py

# 2. Sinh / cập nhật nhánh release Antigravity sạch (không đổi working tree)
py -3 -X utf8 scripts/build_portable.py --sinh-release-agy --nguon dev --nhanh-dich release/antigravity

# 3. Kiểm định nghiêm ngặt Antigravity & chạy bộ test đa OS
agy.EXE plugin validate plugins/tdq-workflow-agy --strict --json
py -3 -B -m pytest tests/test_agy_launchers.py tests/test_agy_plugin_validate.py tests/test_agy_release_e2e.py tests/test_build_portable.py -v --basetemp=.pytest_tmp

# 4. Cài đặt cục bộ có tùy chọn đồng bộ MCP cá nhân
py -3 tools/install_agy_plugin.py --dry-run
# py -3 tools/install_agy_plugin.py --sync-local-mcp
```
