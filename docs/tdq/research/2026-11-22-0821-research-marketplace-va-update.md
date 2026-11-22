# NGHIÊN CỨU — Custom Marketplace GitHub, Sẵn sàng Git Đa Hệ Điều Hành và Cơ chế Auto-Update của Google Antigravity

Ngày: 2026-11-22 · Mã yêu cầu: `2026-11-22-0821-research-marketplace-va-update` · Work kind: `investigate` · Nhánh: `docs/research-marketplace-va-update`
Soul: chất lượng > runtime > context cost · luật gốc: `skills/tdq-conventions/references/soul.md`
Sổ bằng chứng hợp nhất: `docs/tdq/artifacts/2026-11-22-0821-research-marketplace-va-update/evidence.jsonl` (19 mục `EV-A01`–`EV-A12`, `EV-B01`–`EV-B07`)

---

## 1. Tổng hợp kết luận cho 3 câu hỏi gốc

| # | Câu hỏi | Kết luận ngắn | Độ tin cậy | Bằng chứng chính |
|---|---|---|---|---|
| 1 | Google Antigravity có hỗ trợ Custom Marketplace từ GitHub không? | **Không hỗ trợ custom marketplace registry từ GitHub** (`@ten-marketplace` chỉ chấp nhận `antigravity-plugins-official`); nhưng **CÓ hỗ trợ cài trực tiếp URL GitHub** (`https://github.com/<owner>/<repo>[/tree/<branch>/<path>]`) và **nạp tự động cấp Workspace** qua `.agents/plugins/` hoặc `.agents/plugins.json`. Phát hành trên tab Marketplace công khai bắt buộc nộp form đối tác Google để xét duyệt. | `Verified` | `[EV-A01]`, `[EV-A02]`, `[EV-A03]`, `[EV-A05]`, `[EV-A08]` |
| 2 | Project hiện tại đã setup đủ để đưa lên GitHub phát hành cộng đồng đa OS (`Windows`/`macOS`/`Linux`) chưa? | **Chưa sẵn sàng phát hành cộng đồng đa OS hay cài trực tiếp từ URL gốc GitHub.** Gói `plugins/tdq-workflow-agy/` đã vượt `agy plugin validate --strict` với `0` lỗi trên Windows máy `admin`, nhưng đang dính 6 khoảng trống nghiêm trọng (hardcode `C:\Users\admin\...` trong `mcp_config.json`, `bin\tdq-dispatch.exe` trong `hooks.json`, binary macOS/Linux bị cũ, `main` xóa mất `plugins/` làm URL gốc rơi sang Claude Code, adapter 3 host lẫn tên, remote `origin` tụt 25–62 commit). | `Verified` | `[EV-A10]`, `[EV-A11]`, `[EV-A12]`, `[EV-B01]`, `[EV-B02]`, `[EV-B03]`, `[EV-B04]`, `[EV-B05]`, `[EV-B06]`, `[EV-B07]` |
| 3 | Khi plugin trỏ về Git remote, Antigravity có tự động check & auto-update khi có version mới không? | **Không.** Cơ chế auto-check/auto-update của Antigravity chỉ hoạt động cho **Marketplace plugin** (`antigravity-plugins-official` / `antigravity-plugins-partners`) thông qua `"installedFrom"` trong `config.json` và archive `.zip` có `sha256` trên `gstatic.com`. Khi cài từ GitHub URL, `agy` clone nông vào `%TEMP%`, chép bản tĩnh không giữ `.git`, và không lưu Git URL/branch/SHA vào `config.json` hay `import_manifest.json` nên không thể tự poll hay tự nâng cấp từ remote. | `Verified` | `[EV-A06]`, `[EV-A08]`, `[EV-A09]`, `[EV-A10]` |

---

## 2. Phân tích chi tiết từng câu hỏi

### 2.1. Câu hỏi 1 — Antigravity có hỗ trợ Custom Marketplace từ GitHub không? (`Verified`)

1. **Tài liệu chính thức và CLI đều khóa chặt `@marketplace` về kho chính hãng:**
   - Trong `https://antigravity.google/docs/plugins.md` (L108, L132) và `https://antigravity.google/docs/marketplace.md` (L127, L156), tham số `<marketplace-name>` của `/plugin install <plugin>@<marketplace>` và `agy plugin install <plugin>@<marketplace>` chỉ hỗ trợ duy nhất `antigravity-plugins-official` (`[EV-A01]`).
   - Kiểm chứng thực tế trên `agy.exe` (`v1.4.12`) trong môi trường tạm cô lập:
     - `agy plugin install tdq-workflow-agy@custom-mp` thất bại với mã thoát `1`: `Error: unknown marketplace: custom-mp` (`[EV-A08]`).
     - Không có lệnh `agy plugin marketplace add/update/list` như Claude Code (`[EV-A08]`). Lệnh `agy plugin link <mp> <target>` là tiện ích sinh liên kết sâu tới danh mục marketplace chứ không phải đăng ký custom remote registry (thực nghiệm thậm chí báo `Error: unknown marketplace: antigravity-plugins-official` trên CLI `1.4.12` khi thiếu target catalog cục bộ) (`[EV-A08]`).
2. **Ba con đường cài/phân phối từ Git được Antigravity hỗ trợ thực sự:**
   - **Đường A — Cài trực tiếp từ URL GitHub (`agy plugin install`):** Tài liệu `raw/ag_marketplace.md:169-174` và `raw/ag_changelog.md:4177,4238` (từ CLI `v1.0.7`) xác nhận Antigravity hỗ trợ `agy plugin install https://github.com/<owner>/<repo>` và subpath theo nhánh `https://github.com/<owner>/<repo>/tree/<branch>/<path>`, đồng thời tự giải quyết Git submodules. Trong thử nghiệm cô lập, lệnh `agy plugin install https://github.com/TDQUOC/TDQ-Workflow-Antigravity/tree/dev/plugins/tdq-workflow-agy` đã clone nhánh `dev` và cài đủ `12 skills, 8 agents, 10 rules, 3 mcpServers, 6 hooks` (`[EV-A02]`, `[EV-A10]`). Từ CLI `v1.5.11` (2026-11-18), `agy plugin validate` cũng hỗ trợ trực tiếp URL GitHub và `.zip` (`[EV-A02]`, `[EV-A07]`).
   - **Đường B — Chia sẻ cấp Workspace qua VCS (`.agents/`):** Theo `raw/ag_discovery.md:7-25,77-127`, bất kỳ ai `git clone` repo có `.agents/plugins/` hoặc `.agents/plugins.json` trỏ tới thư mục plugin nằm bên trong repo (ví dụ `{"entries": [{"path": "./plugins"}]}`) đều tự động nạp plugin ở phạm vi workspace mà không cần sửa `~/.gemini/`. Lưu ý bản vá bảo mật ở `raw/ag_changelog.md:2072` cấm tuyệt đối đường dẫn tuyệt đối, `../` hoặc symlink trỏ ra ngoài repo trong `.agents/plugins.json` (`[EV-A05]`).
   - **Đường C — Đăng lên Antigravity Official / Partner Marketplace công khai:** Để xuất hiện trong UI **Customizations > Marketplace** (cùng shelf với `antigravity-plugins-official` và `antigravity-plugins-partners`), tác giả phải đáp ứng bộ checklist `raw/ag_build_plugins.md:563-580` (`name` lowercase `kebab-case`, không đặt tiền tố `"Antigravity"`/`"Gemini"`/`"Claude"`/`"Cursor"`, đầy đủ `displayName`, `description`, `version`, `logo` nội bộ 1:1, `suggestedPrompts` <= 3, `author`, `README.md`, file thực thi nằm dưới `scripts/` để giữ quyền `0755`) và nộp qua form đối tác Google (`https://forms.gle/2EX5RFYPoJe1UgxR9`), không phải đặt `marketplace.json` tự host trên GitHub (`[EV-A03]`, `[EV-A04]`).

#### Bảng tách biệt 3 hệ sinh thái host (tránh nhầm lẫn tính năng)

| Tiêu chí | Google Antigravity (`agy` CLI / App / IDE) | Claude Code | OpenAI Codex CLI |
|---|---|---|---|
| Cài từ Custom Marketplace GitHub (`marketplace.json`) | **Không** — chỉ nhận `antigravity-plugins-official` (`[EV-A01]`, `[EV-A08]`) | **Có** — `.claude-plugin/marketplace.json` + `/plugin marketplace add <owner/repo>` | **Có (adapter nội bộ)** — `.agents/plugins/marketplace.json` (`[EV-B05]`) |
| Cài trực tiếp 1 URL repo/subpath GitHub | **Có** — `agy plugin install https://github.com/...[/tree/<branch>/<path>]` (`[EV-A02]`, `[EV-A10]`) | Cần qua marketplace add hoặc git clone thủ công | Cài qua marketplace URL |
| Manifest nhận diện plugin gốc của Antigravity | `<plugin-root>/plugin.json` hoặc `<plugin-root>/.antigravity-plugin/plugin.json` (`[EV-A04]`, `[EV-A11]`) | `.claude-plugin/plugin.json` (khi dùng `agy` trên root repo chỉ có `.claude-plugin/`, `agy` sẽ chuyển đổi sang định dạng `claude-code` và mất `rules`/`mcp_config.json` Antigravity `[EV-A11]`) | `.codex-plugin/plugin.json` (`[EV-B05]`) |
| Auto-update plugin trỏ GitHub | **Không** (`[EV-A09]`, `[EV-A10]`) | Có tùy chọn auto-update theo marketplace đã đăng ký (`/plugin marketplace update`) | Theo cơ chế marketplace host |

---

### 2.2. Câu hỏi 2 — Đánh giá mức độ sẵn sàng GitHub cộng đồng đa OS của project (`Verified`)

1. **Điểm đã làm tốt:**
   - Gói `plugins/tdq-workflow-agy/` vượt `agy plugin validate --strict --json` với `0 findings`, nhận đủ `12 skills, 8 agents, 10 rules, 3 mcpServers, 6 hooks` (`[EV-A12]`).
   - `plugins/tdq-workflow-agy/plugin.json:1-27` (v`0.105.0`) chuẩn cấu trúc `name: "tdq-workflow-agy"` (không bắt đầu bằng `"Antigravity"`, `"Gemini"`, `"Claude"`, `"Cursor"`), có `displayName`, `logo: "assets/logo.svg"`, 3 `suggestedPrompts`, `author`, `repository`, `license: "MIT"`, `keywords` (`[EV-B07]`).
   - Repo đã có CI workflow `.github/workflows/build-rust-hooks.yml` build 3 nền tảng `windows-latest`, `ubuntu-latest`, `macos-latest` (`[EV-B03]`) và `.agents/plugins.json` trỏ `./plugins` cho chế độ workspace (`[EV-B05]`).

2. **6 khoảng trống cản trở phát hành GitHub cộng đồng & đa hệ điều hành (`1a`, `2b`):**

| Mã | Mức độ | Tệp & Dòng nguồn | Hiện trạng gây lỗi khi đưa lên GitHub cho cộng đồng đa OS | Bằng chứng |
|---|---|---|---|---|
| **G1** | Nghiêm trọng | `plugins/tdq-workflow-agy/mcp_config.json:1-31` & `tools/patches/agy_manifests.py:14-44,151-171` | Đóng cứng đường dẫn tuyệt đối của máy `admin` trên Windows (`C:\\Users\\admin\\.local\\bin\\agent-lsp.exe`, `C:\\Users\\admin\\AppData\\Roaming\\fnm\\...*.cmd`, `npx.cmd`, `--userDataDir=C:/Users/admin/.gemini/chrome-devtools-profile`). Cài trên máy Windows khác hoặc macOS/Linux sẽ lỗi toàn bộ 3 MCP server. | `[EV-B01]` |
| **G2** | Nghiêm trọng | `plugins/tdq-workflow-agy/hooks.json:7..116` & `tools/patches/agy_manifests.py:90-100,188` | Đóng cứng lệnh Windows `bin\\tdq-dispatch.exe --event ...` trên mọi hook. Trên macOS/Linux (`sh -c`), toàn bộ 6 lifecycle hooks lỗi ngay lập tức khi cài qua `agy plugin install`. Ngoài ra binary nằm ở `bin/` thay vì `scripts/` (Marketplace yêu cầu `scripts/` để giữ quyền `0755`), và `rules/AGENTS.md` gợi ý `py -3` vốn chỉ có trên Windows. | `[EV-A04]`, `[EV-B02]` |
| **G3** | Cao | `scripts/build_portable.py:69-70`, `git ls-remote origin HEAD`, `git ls-tree main` | Remote `origin` mặc định `HEAD` về `main`, nhưng `build_portable.py --sinh-main` xóa bỏ `plugins/`, `tools/`, `.agents/plugins.json` khỏi `main`. Người dùng chạy lệnh chuẩn `agy plugin install https://github.com/TDQUOC/TDQ-Workflow-Antigravity` sẽ kéo nhầm `.claude-plugin/plugin.json` thành `tdq-workflow` (`claude-code`), mất sạch `10 rules`, `3 mcpServers` và hỏng `hooks` (`["description", "hooks"]`). | `[EV-A11]`, `[EV-B04]` |
| **G4** | Cao | `plugins/tdq-workflow-agy/bin/*`, `.github/workflows/build-rust-hooks.yml:20-55` | `tdq-dispatch.exe` đã ở `f1e7fcfb` (`2026-11-22`, có QC1–QC3 `git_grants`), nhưng `tdq-dispatch-linux-x86_64` và `tdq-dispatch-darwin-arm64` vẫn kẹt ở `d74393da` (`2026-11-21`). CI chưa tự đóng gói binary mới vào repo/release và thiếu target `x86_64-apple-darwin` (Mac Intel). | `[EV-B03]` |
| **G5** | Cao | `git rev-list dev...origin/dev` & `main...origin/main` | Nhánh cục bộ chưa đẩy lên `origin`: `dev` đi trước `origin/dev` `25` commit, `main` (`0.103.1`) đi trước `origin/main` (`0.98.0`) `62` commit và còn tụt sau `dev` (`0.105.0`). | `[EV-B06]` |
| **G6** | Trung bình | `.agents/plugins/marketplace.json:1-20`, `.claude-plugin/marketplace.json:1-13`, `.codex-plugin/plugin.json:8-9`, `tools/build_agy_plugin.py:25`, `README-Antigravity.md:3` | Manifest Codex nằm trong `.agents/plugins/marketplace.json` khai tên `tdq-workflow` với URL `./`; adapter `.claude-plugin/` và `.codex-plugin/` vẫn trỏ `TDQUOC/TDQ-Workflow`; `plugin.json` thiếu `$schema` và `homepage`; `README-Antigravity.md` ghi `v0.97.0`; `build_agy_plugin.py` còn hardcode đường dẫn `_EXTERNAL_UPSTREAM` của `admin`. | `[EV-B05]`, `[EV-B07]` |

---

### 2.3. Câu hỏi 3 — Khi trỏ về Git remote, Antigravity có auto-check & auto-update theo version mới không? (`Verified`)

Câu trả lời dứt khoát là **KHÔNG** — dựa trên cả tài liệu phát hành lẫn bằng chứng cấu hình thực tế trên đĩa (`[EV-A06]`, `[EV-A09]`, `[EV-A10]`):

1. **Vì sao Official Marketplace auto-update được:**
   - Trong `~/.gemini/config/config.json`, 7 plugin cài từ Marketplace (`chrome-devtools-plugin`, `gdocs`, `gdrive`, `gemini-api`, `google-antigravity-sdk`, `gsheets`, `gslides`) đều mang trường `"installedFrom": {"id": "antigravity-plugins-official/plugin/<name>", "marketplace": "antigravity-plugins-official", "version": "<x.y.z>"}` (`[EV-A09]`).
   - Antigravity lưu cache catalog tại `~/.gemini/antigravity-cli/cache/marketplaces/{antigravity-plugins-official,antigravity-plugins-partners}/{marketplace.json,meta.json}` (mỗi entry trỏ tới `.zip` trên `gstatic.com` kèm `sha256`). Khi khởi động hoặc mở UI, client đối chiếu `version` trong cache Marketplace để tự tải bản mới và dọn bản cũ (`[EV-A06]`, `[EV-A09]`).
2. **Vì sao cài từ GitHub URL không auto-check / auto-update:**
   - Thực nghiệm `agy plugin install https://github.com/TDQUOC/TDQ-Workflow-Antigravity/tree/dev/plugins/tdq-workflow-agy` chứng minh CLI chạy `git clone --depth 1 --branch dev ...` vào `%TEMP%\plugin-install-*`, chép các tệp thành phần vào `~/.gemini/config/plugins/tdq-workflow-agy/` (xóa bỏ/không giữ `.git`), không ghi `installedFrom` vào `config.json`, và chỉ ghi `{name, source: "antigravity", importedAt, components}` vào `import_manifest.json` (`[EV-A10]`).
   - Toàn bộ thông tin **URL GitHub**, **nhánh Git** và **commit SHA** bị loại bỏ sau khi cài xong. Trường `"repository"` trong `plugin.json` chỉ dùng để hiển thị liên kết trên thẻ chi tiết UI chứ không được bộ auto-updater sử dụng (`[EV-A06]`, `[EV-A10]`).
   - CLI không có lệnh `agy plugin update` (`[EV-A08]`). Cách duy nhất để cập nhật bản từ GitHub là người dùng tự chạy lại `agy plugin install <url-github>` (lệnh sẽ ghi đè bản cũ và báo `(replaced existing installation)` `[EV-A10]`).
   - **Ngoại lệ cấp Workspace (`Inferred` từ `[EV-A05]`):** Nếu người dùng không cài toàn cục mà mở trực tiếp bản clone repo chứa `.agents/plugins.json`, bản mới sẽ có hiệu lực ngay sau khi người dùng tự chạy `git pull` (vì Antigravity đọc đĩa theo từng phiên/lượt), nhưng Antigravity cũng không tự động chạy `git fetch`/`git pull` ngầm thay người dùng.

---

## 3. Phản biện giả thuyết đối nghịch (Counterfactual Verification — `QC-I3`)

1. **Phản biện 1 ("Liệu bản Antigravity CLI mới hơn `v1.5.12` hoặc Antigravity App `v2.34.0` có thêm custom GitHub marketplace mà `v1.4.12` chưa có không?"):**
   - **Kiểm chứng:** Tài liệu trực tuyến sống tải ngày 2026-11-22 đã phản ánh tới CLI `v1.5.12` (2026-11-19) và App `v2.34.0` (2026-11-20) (`[EV-A07]`). Cả `raw/ag_plugins.md:108,132`, `raw/ag_marketplace.md:127,156` lẫn toàn bộ `raw/ag_changelog.md` (dòng 1745–4405) đều khẳng định `<marketplace-name>` chỉ hỗ trợ `antigravity-plugins-official` và điểm mới ở `v1.5.11` là mở rộng `agy plugin validate` nhận URL GitHub/`.zip`, không có lệnh hay tính năng custom marketplace từ GitHub (`[EV-A01]`, `[EV-A02]`). **Kết luận đứng vững (`Verified`).**
2. **Phản biện 2 ("Có thể `agy` lưu GitHub URL ở một tệp cache ẩn khác ngoài `config.json` và `import_manifest.json` để App auto-update không?"):**
   - **Kiểm chứng:** Ở thực nghiệm cô lập `T1.2` trên `USERPROFILE`/`HOME` rỗng, danh sách tệp tạo mới dưới `.gemini/` chỉ gồm `cache/marketplaces/*` (catalog của Google), `config/import_manifest.json`, `config/config.json`, và `config/plugins/tdq-workflow-agy/` (`raw/agy_probe_3.txt:211-236`). Không có bất kỳ file tracking remote URL nào được sinh ra sau `install_gh_subpath_dev`. Ngoài ra mọi bugfix auto-update trong `raw/ag_changelog.md` (`L353`, `L2139`, `L2344`, `L2404`, `L2954`) đều gắn đích danh với **Marketplace plugin** (`[EV-A06]`, `[EV-A09]`, `[EV-A10]`). **Kết luận đứng vững (`Verified`).**
3. **Phản biện 3 ("Nếu đẩy `dev` lên `origin/dev` thì cộng đồng có cài ngay được bằng lệnh URL ngắn không?"):**
   - **Kiểm chứng:** Kể cả khi đẩy `dev`, URL ngắn `https://github.com/TDQUOC/TDQ-Workflow-Antigravity` vẫn trỏ `origin HEAD` là `main` (chứa `.claude-plugin/plugin.json`), khiến `agy plugin install` convert nhầm sang `claude-code` và làm hỏng `hooks`/`rules`/`mcpServers` trên mọi máy cũng như hỏng đa OS vì `mcp_config.json` và `hooks.json` đóng cứng Windows `C:\Users\admin` (`[EV-A11]`, `[EV-B01]`, `[EV-B02]`, `[EV-B04]`). **Kết luận đứng vững (`Verified`).**

---

## 4. Phương án đề xuất xử lý theo thứ tự ưu tiên (`1a` + `2b`)

> Lưu ý: Theo phạm vi `work_kind=investigate`, mục này chỉ lập phương án khuyến nghị để bạn xem xét mở request triển khai riêng.

1. **Ưu tiên `P0` — Sửa cổng đa máy & đa OS bên trong `plugins/tdq-workflow-agy/` (bắt buộc trước khi share GitHub):**
   - **Khử đường dẫn máy `admin` trong `mcp_config.json` (`tools/patches/agy_manifests.py`):** Sinh cấu hình mặc định dùng lệnh portable trên `PATH` (`agent-lsp`, `npx`, `${PLUGIN_DATA}/chrome-devtools-profile` thay vì `C:\\Users\\admin\\...` và `npx.cmd` cứng), để `tools/install_agy_plugin.py --sync-local-mcp` chỉ làm bước bổ sung cục bộ cho người chạy script cài trên máy cá nhân.
   - **Wrapper đa OS + tuân thủ `scripts/` cho hook (`hooks.json` & `scripts/`):** Đặt các binary `tdq-dispatch*` (kể cả `x86_64-apple-darwin` nếu hỗ trợ Intel Mac) dưới `scripts/bin/` để giữ quyền `0755` trong Marketplace (`[EV-A04]`), dùng một wrapper script tương đối đa OS (ví dụ `python3 ./scripts/tdq_dispatch_wrap.py --event ...` hoặc `sh`/`cmd` polyglot) chọn đúng binary OS/arch và tự fallback về `hooks/scripts/dispatch.py` nếu thiếu binary; tránh viết cứng `bin\\tdq-dispatch.exe` và `py -3` trong `rules/AGENTS.md`.
2. **Ưu tiên `P0` — Đồng bộ CI 3 OS & hỗ trợ cài trực tiếp từ GitHub root:**
   - Cập nhật `.github/workflows/build-rust-hooks.yml` (hoặc workflow release) để đồng bộ lại đủ binary OS mới nhất vào bản đóng gói mỗi lần sửa `hooks/rust/tdq-dispatch/` (xóa lệch `d74393da` vs `f1e7fcfb` `[EV-B03]`).
   - Hỗ trợ cài đúng khi người dùng gõ `agy plugin install https://github.com/TDQUOC/TDQ-Workflow-Antigravity`: hoặc (a) đưa cấu trúc Antigravity plugin/manifest (`.antigravity-plugin/plugin.json` + component Antigravity) lên nhánh release mặc định phù hợp (`scripts/build_portable.py` hoặc tách repo/nhánh riêng cho Antigravity nếu muốn giữ `main` thuần Claude Code `[EV-B04]`), hoặc (b) tài liệu hóa rõ lệnh cài subpath `.../tree/dev/plugins/tdq-workflow-agy` kèm cảnh báo không dùng root URL nếu vẫn giữ `.claude-plugin/` làm chính trên `main`.
3. **Ưu tiên `P1` — Giải quyết bài toán cập nhật phiên bản (Auto-check / Update) khi phân phối từ GitHub:**
   - **Phương án 3A (Chuẩn chính thống — có auto-update thật từ Antigravity):** Hoàn thiện checklist `raw/ag_build_plugins.md:563-580` (`$schema`, `homepage`, bỏ đường dẫn cá nhân, kiểm `agy plugin validate --json` multi-tool clean) và nộp vào **Antigravity Marketplace** qua form đối tác Google (`https://forms.gle/2EX5RFYPoJe1UgxR9`) (`[EV-A03]`). Khi được duyệt vào `antigravity-plugins-official`/`partners`, người dùng chỉ cần tăng `version` là nhận auto-update chính chủ (`[EV-A09]`).
   - **Phương án 3B (Tự chủ qua GitHub — nhắc nhẹ không làm treo phiên):** Vì Antigravity không tự cập nhật plugin GitHub (`[EV-A10]`), có thể bổ sung cơ chế **kiểm tra phiên bản bất đồng bộ có cache TTL** (ví dụ check 1 lần/ngày tại `SessionStart` hoặc subcommand `tdq-check-update` nhẹ đọc GitHub Release/API với timeout ngắn `<= 1.5s`, failsafe im lặng khi offline) để chỉ **hiển thị thông báo phiên bản mới** kèm lệnh chạy lại `agy plugin install <url>` hoặc trình cập nhật riêng, thay vì đòi Antigravity tự auto-update.
4. **Ưu tiên `P2` — Dọn sạch metadata adapter đa host & đồng bộ remote:**
   - Đồng bộ URL `TDQUOC/TDQ-Workflow-Antigravity` vào `.claude-plugin/marketplace.json`, `.codex-plugin/plugin.json`, `README-Antigravity.md` (`0.105.0`), `tools/build_agy_plugin.py` (loại hardcode `_EXTERNAL_UPSTREAM` máy cá nhân hoặc chuyển sang biến môi trường/tùy chọn CLI), dọn/định vị lại `.agents/plugins/marketplace.json` để tránh nhầm lẫn với Antigravity Marketplace (`[EV-B05]`, `[EV-B07]`), rồi push cập nhật đồng bộ `dev` và `main` lên `origin` khi người dùng chốt phát hành (`[EV-B06]`).
