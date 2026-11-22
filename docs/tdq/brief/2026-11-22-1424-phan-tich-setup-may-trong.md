# BRIEF — Nghiên cứu và thiết kế quy trình setup zero-to-full từ máy trống kèm tự động kiểm chứng sau restart
Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

Ngày: 2026-11-22 · Mã yêu cầu: 2026-11-22-1424-phan-tich-setup-may-trong · Lane: full · Work kind: investigate · Nhánh đích: docs/phan-tich-setup-may-trong (tách từ dev)

## Nguyên văn

> okay hỹa mở request phân tích cho phase setup để khi gọi skill setup thì sẽ từ một máy trống hết trơn chưa có gì cả cũng có thể setup fully tdq-workflow cũng như các dependency và các add on của nó, và có yêu cầu restart, sau restart sẽ có validate và check simulate test tự động để đảm bảo mọi thứ work ổn, hỹa resrerach và pgaan tích và cho tôi đề xuất

### Đọc hiểu bước đầu

- **Mục tiêu:** Nghiên cứu toàn diện và lập đề xuất kiến trúc nâng cấp cho skill `tdq-setup` để từ một máy mới tinh chưa cài đặt công cụ phụ trợ vẫn có thể thiết lập trọn bộ `tdq-workflow`, toàn bộ dependency cốt lõi (bộ tìm kiếm 3 tầng `agent-lsp`, các Language Server theo ngôn ngữ, `graphify`, `ripgrep`, môi trường nền `Python 3` / `Node.js` / `uv` / `Git`) cùng toàn bộ add-on vệ tinh (`rtk`, `caveman` MCP wrapper, `tavily-primary`, `chrome-devtools` MCP, cấu hình user rules), quản lý chặt chẽ điểm dừng yêu cầu khởi động lại (`restart`), và ngay sau khi restart sẽ tự động chạy kiểm định (`validate`) kèm kiểm thử giả lập (`simulate test`) toàn trình để chứng minh mọi thành phần hoạt động ổn định.
- **Phạm vi dự kiến:** Khảo sát hệ sinh thái cài đặt hiện tại (`skills/tdq-setup/`, `scripts/tdq_setup.py`, `scripts/tdq_lsp.py`, `scripts/setup_status.py`, `scripts/rtk_integration.py`, `scripts/caveman_config.py`, `scripts/tdq_devtool_mcp.py`, `tools/install_agy_plugin.py`, `install.py`) kết hợp nghiên cứu vòng đời nạp plugin, MCP, hooks và biến môi trường `PATH` của Google Antigravity qua ranh giới restart trên cả ba hệ điều hành (`Windows`, `macOS`, `Linux`). Yêu cầu mở ở chế độ phân tích và đề xuất (`work_kind=investigate`, nhánh `docs/phan-tich-setup-may-trong`).
- **Điểm cần chốt qua phỏng vấn:** Đã hoàn tất 100% ở mục `## Hỏi đáp` (`1a 2a 3a 4a 5a 6a`).

## Hiểu & kiến thức

### Năng lực dùng được

Phân vân → DÙNG. Kiểm kê ngày 2026-11-22: 42 skill trên đĩa, cộng các skill built-in trong context. Không xoá bảng này kể cả khi không có dòng DÙNG nào.

| Skill | Nguồn | Phán quyết | Dùng ở đâu / Lý do loại |
|---|---|---|---|
| tdq-intake, tdq-spec, tdq-plan, tdq-build, tdq-conventions, tdq-setup, tdq-status, tdq-check-status, tdq-lean, tdq-checkportable | plugin:tdq-workflow / plugin:tdq-workflow-agy | NỀN | Luồng TDQ Workflow đang vận hành (`investigate`) và chính đối tượng nghiên cứu `tdq-setup` |
| antigravity-guide | built-in | DÙNG | Tra cứu tài liệu chính thức của Google Antigravity (`plugins.md`, `hooks.md`, `mcp.md`, `cli/reference.md`) về vòng đời nạp lại sau restart |
| plugin | built-in | DÙNG | Đối chiếu cơ chế cài đặt, bật/tắt, `plugin.json`, `${PLUGIN_ROOT}`, `${PLUGIN_DATA}` và kiểm định `agy plugin validate` |
| agy-customizations | built-in | DÙNG | Đối chiếu discovery roots (`~/.gemini/config/`, `.agents/`, `~/.gemini/GEMINI.md`) và thứ tự nạp rules/skills/hooks/MCP |
| tdq-browser-research, tdq-browser-test | plugin:tdq-workflow / plugin:tdq-workflow-agy | KHÔNG | spec §3 đã chọn cách khác tốt hơn |
| Đã xét 31 skill khác | user/plugin/built-in | KHÔNG | khác lĩnh vực |

### Khảo sát điểm vào hiện trạng và giả thuyết kiểm chứng (`investigate` mức nông)

Đã đọc đầy đủ `docs/kien-truc.md` và thực hiện Tam Giác Khảo Sát 3 Chiều ở mức điểm vào theo `investigate-mode.md` (`rg --files`, `mcp_tdq-workflow-agy_lsp_start_lsp` + `list_symbols`, `graphify query`). Bỏ qua vòng hỏi phạm vi tổng quát riêng (`scope-round.md`) vì yêu cầu đã xác định rõ mục tiêu thiết kế quy trình `tdq-setup` zero-to-full đa tầng kèm kiểm chứng hậu restart.

**Sự thật bước đầu đã xác nhận trên đĩa:**
- **Độ lệch nền tảng trong `tdq-setup` hiện tại:** `plugins/tdq-workflow-agy/skills/tdq-setup/SKILL.md`, `scripts/tdq_setup.py` (`2,183` dòng, `DUONG_INSTRUCTION = "~/.claude/CLAUDE.md"`) và `scripts/setup_status.py` (`CAU_HINH_CLAUDE = "~/.claude.json"`) vẫn đang neo phần lớn logic đăng ký MCP, quyền allow-list và kiểm tra trạng thái vào cấu hình của Claude Code (`~/.claude.json`, `~/.claude/settings.json`), chưa chuyển sang chuẩn native của Google Antigravity (`~/.gemini/config/plugins/tdq-workflow-agy/`, `${PLUGIN_DATA}`, `~/.gemini/GEMINI.md`, `agy plugin validate`).
- **Phân mảnh công cụ & add-ons:** Các trình cài phụ trợ đã tồn tại rải rác (`scripts/rtk_integration.py`, `scripts/caveman_config.py`, `scripts/tdq_devtool_mcp.py`, `tools/install_agy_plugin.py`, `install.py`), nhưng chưa được thống nhất dưới một kịch bản điều phối duy nhất khi người dùng trên máy mới cài plugin từ nhánh `release/antigravity` rồi gọi skill `tdq-setup`.
- **Thiếu tầng Bootstrap máy trống và Máy trạng thái qua Restart:** Chưa có bước kiểm tra/cài đặt runtime gốc (`Node.js`, `Python 3` thực tránh stub `WindowsApps`, `uv`, `Git`, `ripgrep`) cho máy mới tinh; chưa có file trạng thái lưu vết qua restart (như `${PLUGIN_DATA}/setup-state.json`); và chưa có bộ kiểm thử giả lập (`simulate test`) hậu restart chạy độc lập trên sandbox tạm khi người dùng đang mở thư mục trống.

| Vùng file chạm (điểm vào) | Phát hiện qua lớp nào (Grep/LSP/Graphify) | Tác động & quan hệ cần đào sâu ở `implement` |
|---|---|---|
| `plugins/tdq-workflow-agy/skills/tdq-setup/SKILL.md` & `references/*` | Grep + `read_file` nông | Tài liệu điều phối skill `tdq-setup` đang trỏ `claude mcp add` và thiếu quy trình 2 pha trước/sau restart |
| `scripts/tdq_setup.py`, `scripts/tdq_lsp.py`, `scripts/lsp_module.py`, `scripts/setup_status.py` | Grep + LSP (`list_symbols`) + Graphify | Lõi kiểm tra 8 bậc tìm kiếm, tự cài allow-list và xuất báo cáo trạng thái máy; cần tách lớp adapter Antigravity khỏi Claude Code |
| `scripts/rtk_integration.py`, `scripts/caveman_config.py`, `scripts/tdq_devtool_mcp.py`, `scripts/tdq_checkportable.py` | Grep + Graphify (`484` nodes liên kết) | Các module cài đặt và bọc cấu hình cho add-ons (`rtk`, `rg`, `caveman`, `chrome-devtools` MCP) cần gom vào pipeline thống nhất |
| `tools/install_agy_plugin.py`, `install.py`, `plugins/tdq-workflow-agy/scripts/tdq_{hook,mcp}_launcher.mjs` | Grep + Graphify | Trình cài plugin, dò `WindowsApps` Python stub, Node launchers cho hooks & MCP servers cần đồng bộ với pha validate hậu restart |
| `hooks/rust/tdq-dispatch/` & `hooks/scripts/session_start.py` (`PreInvocation`) | Kiến trúc `docs/kien-truc.md` + Graphify | Điểm móc tiềm năng để nhận diện phiên mới sau khi restart Antigravity IDE và kích hoạt tự động pha validate + simulate test |

**Bốn giả thuyết ứng viên cần kiểm chứng ở pha `implement`:**
- **H1 (Ranh giới Restart của Antigravity IDE/CLI):** Khi cài mới binary vào `PATH` hệ điều hành, sửa `mcp_config.json` (như bọc `caveman` hoặc điền env `TAVILY_API_KEY`), hoặc cập nhật `hooks.json` / `GEMINI.md`, tiến trình Antigravity hiện tại không tự cập nhật `PATH` của tiến trình cha và không tự khởi động lại các MCP stdio process đang sống — bắt buộc phải có bước restart IDE/window hoặc reconnect rõ ràng.
- **H2 (Chống nhận diện nhầm "đã restart"):** Có thể phân biệt chính xác người dùng đã thực sự khởi động lại Antigravity so với việc chỉ mở cuộc trò chuyện mới hoặc gõ tiếp trong cùng phiên chưa restart thông qua việc ghi dấu PID tiến trình cha / session marker / boot timestamp vào `${PLUGIN_DATA}/setup-state.json` ở cuối Pha 1.
- **H3 (Bootstrap máy trắng tinh không phụ thuộc Python có sẵn):** Trên máy mới tinh chỉ vừa cài Antigravity (chưa có `Python 3` hoặc `Node.js`), skill `tdq-setup` có thể hướng dẫn Agent dùng trực tiếp trình quản lý gói bản địa của từng OS (`winget` trên Windows, `brew` trên macOS, `apt`/`dnf`/`pacman` + `uv` standalone installer trên Linux) kết hợp script one-liner ngoài terminal cho máy chưa có `Git` để dựng `Node.js` + `Python 3` + `uv` + `Git` trước khi gọi sang `tdq_setup.py`.
- **H4 (Simulate Test cô lập không làm bẩn dự án):** Một kịch bản `simulate test` tạo workspace mẫu đa ngôn ngữ siêu nhỏ trong thư mục tạm (`tempfile.TemporaryDirectory`), bắn thật JSON qua `tdq_hook_launcher.mjs`, bắt tay JSON-RPC thật qua `tdq_mcp_launcher.mjs`, chạy thật `rg` + `agent-lsp` + `graphify` + `rtk` + `caveman` sẽ phát hiện được mọi lỗi ngầm (quyền thực thi, thiếu thư viện động, sai PATH, kẹt port/profile) mà lệnh kiểm tra tĩnh bỏ sót.

### Quyết định thiết kế đã chốt & Phương án đã loại

- **Chọn Dual-Entry cho máy trống (`1a`):** Thiết kế đồng bộ 2 cửa vào nối tiếp — cửa ngoài là one-liner bootstrap (`bootstrap.ps1` / `bootstrap.sh`) lo máy chưa có cả `Git` hoặc plugin; cửa trong là skill `tdq-setup` tự dò/cài từ `Python 3`, `Node.js`, `uv`, `Git` trở lên. *Đã loại:* chỉ làm trong Antigravity (`1b`, kẹt khi máy mới chưa có `Git` để chạy `agy plugin install`) và dồn hết ra CLI ngoài (`1c`, mất trải nghiệm gọi skill một chạm).
- **Chọn One-Shot Manifest Consent + tách khóa API tùy chọn (`2a`):** Quét toàn bộ máy một lần, xuất bảng kê trọn gói để người dùng duyệt một lần duy nhất trước khi cài liền mạch toàn bộ Core & Add-ons (`agent-lsp`, Language Servers, `graphify`, `rg`, `rtk`, `caveman`, `chrome-devtools` MCP, `GEMINI.md`); riêng add-on cần khóa như `tavily-primary` sẽ hướng dẫn nhập hoặc đánh dấu `skipped_no_key` không chặn luồng. *Đã loại:* tự cài ngầm không hỏi (`2b`, trái luật quyền người dùng) và hỏi lẻ từng bậc (`2c`, đứt mạch trên máy trống).
- **Chọn Auto-Resume qua Hook `PreInvocation` có kiểm dấu phiên mới (`3a`):** Lưu trạng thái `awaiting_restart` cùng dấu tiến trình/phiên vào `${PLUGIN_DATA}/setup-state.json`; ngay lượt chat đầu tiên sau khi mở lại Antigravity, hook đối chiếu dấu tiến trình mới để xác nhận đã thực sự restart rồi bơm mã nhắc kích hoạt tự động Pha 2 (vẫn giữ lệnh gọi tay `tdq-setup --resume` làm đường dự phòng). *Đã loại:* chỉ chờ người dùng nhớ gọi tay (`3b`).
- **Chọn E2E Simulate Test đa tầng trên Sandbox tạm + Live MCP/Subagent Probe (`4a`):** Dựng dự án mẫu tạm (Python + JS/TS) để chạy thật cả 6 hook events, bắt tay JSON-RPC sống với MCP servers, chạy thật 3 tầng tìm kiếm + `rtk` + `caveman`, kiểm định `agy plugin validate --strict` và thăm dò subagent rồi tự dọn sạch. *Đã loại:* chỉ kiểm tra phiên bản/cấu hình tĩnh (`4b`).
- **Chọn đầu ra Nghiên cứu & Đề xuất Kiến trúc (`5a`, `work_kind=investigate`, `muc_qc=full` `6a`):** Hoàn thiện hồ sơ nghiên cứu sâu, sơ đồ máy trạng thái, ma trận đa hệ điều hành, đặc tả kịch bản `simulate test`, lộ trình tách task triển khai và báo cáo `Archify HTML`, không sửa mã nguồn sản phẩm trong request này.

### Lộ trình

| Bước/phase | Chạy? | Vì sao |
|---|---|---|
| Phân tích nông & phỏng vấn (`analyze`) | CÓ | Đã hoàn tất kiểm kê năng lực, khảo sát điểm vào 3 chiều và chốt đủ 6 câu hỏi (`1a 2a 3a 4a 5a 6a`, `muc_qc=full`) |
| Đặc tả (`spec` — `investigate`) | CÓ | Khóa phạm vi 4 trụ cột thiết kế, đầu ra báo cáo đề xuất và tiêu chí kiểm chứng bằng chứng `QC-I1`–`QC-I4` (miễn `§2b` và Archify preview theo `investigate-mode.md`) |
| Lập kế hoạch (`plan`) | CÓ | Chia các trục điều tra độc lập (vòng đời Antigravity & đa OS, kiểm toán mã nguồn setup/add-ons/hooks, tổng hợp kiến trúc & thực nghiệm cô lập) kèm hợp đồng 5 trường cho 3 skill `DÙNG` |
| Thực thi nghiên cứu (`implement`) | CÓ | Đọc sâu tài liệu chính thức Antigravity và mã nguồn, chạy thử nghiệm cô lập không chạm `~/.gemini/`, ghi `evidence.jsonl` và viết bản đề xuất kiến trúc + nháp báo cáo |
| Kiểm chứng bằng chứng (`qc` — `full`) | CÓ | Chạy đủ `QC-I1`–`QC-I4` (đối chiếu trích dẫn đĩa/tài liệu, phản biện counterfactual đa OS, gắn nhãn độ tin cậy, khóa phạm vi sạch kho) |
| Báo cáo cuối (`report` + `Archify HTML`) | CÓ | Xuất báo cáo Markdown 4 phần và render `Archify HTML` một lần phục vụ qua Tailscale HTTPS `200`, hỏi commit/merge về `dev` |

## Hỏi đáp

### Vòng 1 (2026-11-22)

1. **Điểm xuất phát của máy trống bao phủ tới đâu?** → **1A:** Hai cửa vào nối tiếp (skill `tdq-setup` tự cài từ `Python`/`Node`/`Git` trở lên + kèm lệnh bootstrap ngoài terminal cho máy chưa có `Git` hay plugin).
2. **Cơ chế xin phép cài đặt và xử lý add-ons cần khóa API?** → **2A:** Duyệt trọn gói một lần duy nhất (One-Shot Manifest Consent); tiện ích thiếu khóa API (như `Tavily`) hướng dẫn điền hoặc tạm bỏ qua không chặn luồng chính.
3. **Cách kích hoạt bước kiểm định và giả lập sau khi khởi động lại?** → **3A:** Tự động qua hook đầu lượt chat (`PreInvocation`) kèm đối chiếu dấu phiên/tiến trình mới từ tệp trạng thái bền vững, chống báo nhầm khi chưa thực sự khởi động lại.
4. **Độ sâu của bộ kiểm thử giả lập sau khởi động lại?** → **4A:** Giả lập toàn trình trên thư mục tạm cô lập kết hợp gọi thật MCP, 6 sự kiện hook, 3 tầng tìm kiếm, bộ nén ngữ cảnh và subagent rồi tự dọn sạch.
5. **Phạm vi đầu ra của request hiện tại?** → **5A:** Bản nghiên cứu và đề xuất kiến trúc toàn diện kèm báo cáo trực quan `Archify HTML` (`work_kind=investigate`), chốt sạch thiết kế trước khi mở request triển khai code.
6. **Mức QC (`muc_qc`)?** → **6A:** `full`.
