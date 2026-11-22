# Shard Trục A1 — Tài liệu chính thức Antigravity & nguồn web (T1.1)

Ngày thu thập: 2026-11-22 · Skill nạp: `antigravity-guide`

## Nguồn gốc đã tải và lưu cục bộ (`raw/`)

- `ag_llms.txt` (`https://antigravity.google/llms.txt`, HTTP 200, 15.705 ký tự)
- `ag_plugins.md` (`https://antigravity.google/docs/plugins.md`, HTTP 200, 14.535 ký tự)
- `ag_marketplace.md` (`https://antigravity.google/docs/marketplace.md`, HTTP 200, 11.054 ký tự)
- `ag_build_plugins.md` (`https://antigravity.google/docs/build-plugins.md`, HTTP 200, 33.241 ký tự)
- `ag_discovery.md` (`https://antigravity.google/docs/customization-discovery.md`, HTTP 200, 15.925 ký tự)
- `ag_hooks.md` (`https://antigravity.google/docs/hooks.md`, HTTP 200, 20.756 ký tự)
- `ag_cli_ref.md`, `ag_cli_using.md`, `ag_settings.md`, `ag_enterprise.md`, `ag_changelog.md`, `ag_plugin_schema.json` (HTTP 200 toàn bộ)

## Phát hiện chính theo từng bằng chứng

1. **[EV-A01] Không có khái niệm Custom GitHub Marketplace trong Antigravity:** Tài liệu `plugins.md` (L108, L132) và `marketplace.md` (L127, L156) khẳng định tham số `<marketplace-name>` chỉ hỗ trợ duy nhất `antigravity-plugins-official`. Không tồn tại lệnh thêm/cập nhật custom marketplace (lưu ý một số tóm tắt search bên thứ ba trộn nhầm lệnh `/plugin marketplace update` của Claude Code).
2. **[EV-A02] Có hỗ trợ cài trực tiếp từ URL GitHub & subpath:** `marketplace.md` (L169–174) và `changelog.md` (L4177, L4238 từ v1.0.7) cho phép chạy `agy plugin install https://github.com/<owner>/<repo>` kể cả subpath dạng `https://github.com/<owner>/<repo>/tree/<branch>/<path>` và tự xử lý Git submodules. Từ CLI v1.5.11 (L1751), `agy plugin validate` cũng nhận URL GitHub và file `.zip`.
3. **[EV-A03] Phân phối công khai qua Official Marketplace đòi hỏi xét duyệt Google:** Muốn plugin xuất hiện trên tab **Customizations > Marketplace** công khai của cộng đồng phải đáp ứng bộ checklist `build-plugins.md` (L563–580) và nộp qua form đối tác Google (`https://forms.gle/2EX5RFYPoJe1UgxR9`), không phải tự host file `marketplace.json` trên GitHub để Antigravity tự quét.
4. **[EV-A04] Yêu cầu schema, branding và đa nền tảng để phát hành cộng đồng:**
   - `plugin.json` (tại gốc plugin hoặc `.antigravity-plugin/plugin.json` trong repo đa công cụ) kiểm theo `schemas/v1/plugin.json`: `name` phải `kebab-case`, không đặt tiền tố `"Antigravity"`, `"Gemini"`, `"Claude"`, `"Cursor"` ở `name`/`displayName` (`build-plugins.md:570`); cần `displayName`, `description`, `version` (semver để client nhận bản mới), `logo` (ảnh vuông nội bộ hoặc host Google), `suggestedPrompts` (<= 3), `author` (`url` `https://`).
   - `hooks.json` chạy với `cwd=<plugin-root>`, tài liệu mới (`L255`, `L574`, CLI `v1.5.6` `L1936`) khuyến cáo dùng đường dẫn tương đối (`./scripts/...`) thay vì `${PLUGIN_ROOT}` trong hook command và đặt file thực thi dưới `scripts/` để giữ quyền `0755` khi đóng gói Marketplace; `mcp_config.json` ưu tiên HTTPS hoặc Node/chạy đa OS (`L317`).
5. **[EV-A05] Chia sẻ cấp dự án qua Git repo:** Người dùng clone bất kỳ Git repo nào chứa `.agents/plugins/` hoặc `.agents/plugins.json` (với `path` nội bộ trong workspace, không trỏ `../`, symlink ngoài hay URL từ xa per `changelog.md:2072`) sẽ tự động được Antigravity App/IDE/CLI phát hiện ở cấp Workspace.
6. **[EV-A06] Cơ chế auto-check & auto-update theo tài liệu chính thức:** Tất cả các mục trong `changelog.md` (`L353`, `L500`, `L541`, `L2139`, `L2344`, `L2404`, `L2954`) đều mô tả cơ chế tự động cập nhật (`automatic updates`) và dọn cache khi khởi động dành riêng cho **Marketplace plugin** (`antigravity-plugins-official`) so sánh theo `version`. Không có lệnh `agy plugin update` hay tài liệu chính thức nào xác nhận Antigravity tự poll `git remote`/GitHub định kỳ để auto-update plugin cài qua URL GitHub (cần kiểm chứng thêm hành vi lưu metadata thực tế của `agy` ở `T1.2`).
7. **[EV-A07] Độ lệch phiên bản tài liệu vs máy cục bộ:** Docs trực tuyến phản ánh CLI tới `v1.5.12` (2026-11-19) và App `v2.34.0` (2026-11-20), trong khi máy kiểm chứng đang cài CLI `v1.4.12` (2026-10-30).
