# Hồ sơ yêu cầu — `2026-11-22-1521-trien-khai-setup-fully-agy`
Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

- **Ngày mở:** 2026-11-22
- **Pipeline:** `full` (chế độ chuyên sâu) · **Loại request:** `feature` · **Nhánh:** `feature/trien-khai-setup-fully-agy` (từ `dev`)
- **Tài liệu kiến trúc gốc:** `docs/tdq/research/2026-11-22-1424-phan-tich-setup-may-trong.md`
- **Hồ sơ khảo sát chi tiết:** `docs/tdq/artifacts/2026-11-22-1521-trien-khai-setup-fully-agy/explore-codebase.md`

## Nguyên văn

> commit và mở request thực hiện  đề xuất mới triệt để để có thể setup triệt để chỉ bằng lệnh kêu setupfully tdq-workflow cho antigravity máy này sẽ tự setup và check fully và toàn quyền simulate test để đảm bảo hoạt động fully và hoàn hảo và ổn định cho tdq-workflow và tất cả các dependency và add on và extension có liên quan đc nhắc đến

### Đọc hiểu bước đầu

- **Mục tiêu cốt lõi:** Hiện thực hóa trọn vẹn kiến trúc Zero-to-Full (`docs/tdq/research/2026-11-22-1424-phan-tich-setup-may-trong.md`) trên Google Antigravity để chỉ bằng một lệnh kích hoạt (`"setupfully tdq-workflow"` / `/tdq-setup`), hệ thống tự động cài đặt triệt để từ máy trống (hoặc tự vá máy đang chạy thiếu/lệch cấu hình), lưu trạng thái bền vững qua bước khởi động lại Antigravity, rồi tự kích hoạt bộ `Simulate Test` 6 tầng độc lập workspace để chứng minh toàn bộ `tdq-workflow`, các dependency tìm kiếm, add-ons và các companion extensions liên quan hoạt động ổn định.
- **Phạm vi bao phủ:** Cửa 0 Bootstrap (`bootstrap.ps1` / `bootstrap.sh`), Cửa 1 Skill `/tdq-setup` & chế độ `"setupfully tdq-workflow"`, `HostAdapter` chuẩn Antigravity (`~/.gemini/config/`, `~/.gemini/GEMINI.md`, `agy plugin`), Launcher Node đa OS cho `lsp` / `caveman` / `tavily` / `chrome-devtools`, cài đặt `Archify` engine cho báo cáo HTML, trạng thái bền vững `${PLUGIN_DATA}/setup-state.json` + `setup-pending.flag` + `Host Session Fingerprint` trong hook `PreInvocation` / `SessionStart`, và bộ `tdq_simulate_verify.py` 6 tầng.

## Hiểu & kiến thức

Vòng scope: BỎ — kiến trúc tổng thể 4 trụ cột, các mặt hiệu năng/tương thích/bảo mật và 3 hệ điều hành đích (`Windows`, `macOS`, `Linux`) đã được người dùng chốt ở yêu cầu nghiên cứu tiền nhiệm `2026-11-22-1424-phan-tich-setup-may-trong`; vòng phỏng vấn bên dưới chốt thẳng các điểm hành vi mới của bản triển khai.

### Năng lực dùng được

Phân vân → DÙNG. Kiểm kê ngày 2026-11-22: 42 skill trên đĩa, cộng skill built-in trong context. Không xoá bảng này kể cả khi không có dòng DÙNG nào.

| Skill | Nguồn | Phán quyết | Dùng ở đâu / Lý do loại |
|---|---|---|---|
| agy-customizations | built-in | DÙNG | đối chiếu chuẩn cấu hình `~/.gemini/config/`, `hooks.json`, `mcp_config.json`, `rules/AGENTS.md` và giới hạn byte của Antigravity |
| plugin | built-in | DÙNG | kiểm chứng cấu trúc đóng gói `plugin.json`, `agy plugin validate --strict --json` và vòng đời cài/bật plugin ở `~/.gemini/config/plugins/` |
| tdq-intake | plugin:tdq-workflow-agy | NỀN | mở request, khảo sát 3 chiều và phỏng vấn chốt phạm vi |
| tdq-spec | plugin:tdq-workflow-agy | NỀN | viết và khóa đặc tả kỹ thuật ở pha `spec` |
| tdq-plan | plugin:tdq-workflow-agy | NỀN | tách đợt công việc và hợp đồng kiểm thử ở pha `plan` |
| tdq-build | plugin:tdq-workflow-agy | NỀN | điều phối triển khai `red -> green`, QC và xuất báo cáo |
| tdq-setup | plugin:tdq-workflow-agy | NỀN | đối tượng trực tiếp được nâng cấp lên kiến trúc Zero-to-Full v2 |
| tdq-conventions | plugin:tdq-workflow-agy | NỀN | luật chung về trình bày 2 lớp, git safety, nhật ký và cổng duyệt |
| tdq-checkportable | plugin:tdq-workflow-agy | NỀN | chia sẻ hạ tầng cài shim `python3` và vá `PATH` mức người dùng trên Windows |
| tdq-browser-research | plugin:tdq-workflow-agy | NỀN | skill đồng hành kiểm tra tương thích với `chrome-devtools` MCP |
| tdq-browser-test | plugin:tdq-workflow-agy | NỀN | skill đồng hành kiểm tra tương thích với `chrome-devtools` MCP |
| tdq-check-status | plugin:tdq-workflow-agy | NỀN | hồi phục trạng thái phiên làm việc khi cần |
| tdq-lean | plugin:tdq-workflow-agy | NỀN | rà soát chống phình mã và giữ hàm gọn `<= 50` dòng |
| tdq-status | plugin:tdq-workflow-agy | NỀN | tra cứu trạng thái workflow |
| Đã xét 30 skill khác | user/plugin/built-in | KHÔNG | khác lĩnh vực |

### Khảo sát mã nguồn 3 chiều (Triangulation)

Phiên bản công cụ & nền tảng đo thực tế trên máy: `agy 1.4.12`, `Python 3` (stdlib), `Node.js >= 18` ESM, `cargo 1.99.0` / `rustc 1.99.0` (`x86_64-pc-windows-msvc`), `agent-lsp 0.19.2`, `rtk 1.2.0`, `Archify 3.2.0` (`https://github.com/tt-a1i/archify.git`, repo public nhánh `main`).

| Vùng file chạm | Phát hiện qua lớp nào (Grep/LSP/Graphify) | Tác động & quan hệ |
|---|---|---|
| `scripts/tdq_setup_state.py` _(mới)_ | Thiết kế từ Blueprint v2 + khảo sát `PLUGIN_DATA` qua Grep | Quản lý `${PLUGIN_DATA}/setup-state.json`, cờ `O(1)` `setup-pending.flag`, TTL 24h, nạp/lưu an toàn `${PLUGIN_DATA}/secrets.env` (`0600` / user ACL) và đo `Host Session Fingerprint` đa OS (`CreateToolhelp32Snapshot`+`GetProcessTimes` trên Win32, `/proc` trên Linux, `ps` trên macOS, `< 2 ms`). Cô lập sạch khi `TDQ_KHONG_CHAM_MAY=1` hoặc `TDQ_SETUP_STATE_DIR` được đặt. |
| `scripts/tdq_simulate_verify.py` _(mới)_ + `scripts/tdq_setup_probe.mjs` _(mới)_ + `scripts/bootstrap.{ps1,sh}` _(mới)_ | Grep + kiểm tra pipeline `tools/build_agy_plugin.py:229,276` & `scripts/build_portable.py:753` | Mọi file trong `scripts/` tự động được copy vào `plugins/tdq-workflow-agy/scripts/` và kiểm `node --check` cho `*.mjs`. Cần cập nhật `build_portable.py:753` và `install_agy_plugin.py:92` / `install.py:79` để gắn `0755` cho `*.sh` cạnh `*.mjs`. Không thêm vào `agy_launchers.generate_launchers()` để giữ nguyên hợp đồng `tests/test_agy_launchers.py:41` (`2` file launcher). |
| `scripts/tdq_setup.py`, `scripts/tdq_lsp.py`, `scripts/setup_status.py`, `scripts/tdq_devtool_mcp.py`, `scripts/archify_delivery.py` | LSP (`list_symbols`, `blast_radius`) + Graphify (`affected`, `8096` nodes) + Grep `.claude` | Gỡ lệch đường dẫn Claude sang Antigravity: (1) `tdq_setup.py:72,368,706,1508` bổ sung nhánh Antigravity đọc `plugin.json` gốc, kiểm/bật qua `agy plugin list/enable`, ghim `<!-- TDQ:TOOLS -->` chuẩn Antigravity vào `~/.gemini/GEMINI.md`, cài `Archify` từ `tt-a1i/archify` vào `~/.local/share/archify` (hoặc `~/Documents/archify`) và thêm cờ `--scan-json`, `--apply-manifest`, `--setupfully`, `--post-restart-verify`, `--confirm-restarted`, `--set-tavily-key`; (2) `tdq_lsp.py:299,411,444,469,535` sửa `~/.gemini/config/mcp_config.json`, lọc tham số `.mjs` khỏi `agent-lsp doctor`, nhận diện mode `"lsp"` của Node launcher ở Bậc 3, quét hook xung đột ở `~/.gemini/config/`; (3) `archify_delivery.py:100` bổ sung `~/.local/share/archify` vào danh sách tìm kiếm mặc định. |
| `scripts/caveman_config.py` + `tools/patches/agy_launchers.py` (`tdq_mcp_launcher.mjs`) | LSP (`find_references` trên `probe_caveman`, `wrap_mcp_config`) + đọc `tests/test_caveman_setup.py:152` & `tests/test_agy_plugin_validate.py:79` | Mở rộng `MCP_LAUNCHER_MJS` trong `tools/patches/agy_launchers.py` hỗ trợ: (a) mode `"caveman"` tự dò Python 3 thực (bỏ qua `WindowsApps` stub) chạy `-u tdq_mcp_shrink.py -- ...`; (b) tự nạp mềm `${PLUGIN_DATA}/secrets.env` (cho `TAVILY_API_KEY`) và mở rộng `PATH` chuẩn user-space (`~/.local/bin`, `fnm`, `~/.npm-global/bin`, `/opt/homebrew/bin`). Trong `caveman_config.py`, nếu entry dùng `tdq_mcp_launcher.mjs` thì bọc thành `node` + `["${PLUGIN_ROOT}/scripts/tdq_mcp_launcher.mjs", "caveman", "--", ...]` (`0` lộ `sys.executable`), còn entry kiểu Claude cũ vẫn giữ nguyên định dạng cũ để xanh `test_caveman_setup.py`. |
| `hooks/rust/tdq-dispatch/src/{main.rs,events/pre_invocation.rs}` + `hooks/scripts/{prompt_context.py,session_start.py}` + `tools/patches/{agy_hooks.py,cli_fixes_a.py}` | Grep + đọc trực tiếp Rust/Python dispatcher + `tests/test_rust_dispatch_parity.py:50,57` | `main.rs:189` đã `DelegatePython` cho `SessionStart`; `pre_invocation.rs:189` thêm kiểm tra `O(1)` `<plugin_data>/setup-pending.flag` -> `DelegatePython` và vá `main.rs:174` fallback sang `py -3` khi `python` trên Windows là `WindowsApps` stub (`exit != 0` và `stdout` rỗng). Toàn bộ máy trạng thái `Host Session Fingerprint` + nhận diện câu lệnh `"setupfully tdq-workflow"` chạy tập trung tại `prompt_context.py` / `session_start.py` (đồng bộ neo `replace_exact` trong `tools/patches/agy_hooks.py` & `cli_fixes_a.py`). Dùng mã chuẩn `[TDQ:SETUP]` (đã nằm trong `23` mã khóa cứng của `gate_guidance.json` và `test_rust_dispatch_parity.py:50`). Cô lập `PLUGIN_DATA` trong `_isolated_env` của `test_rust_dispatch_parity.py`. |
| `skills/tdq-setup/SKILL.md` + `skills/tdq-setup/references/{zero-to-full-agy.md,chrome-devtools-mcp-guide.md}` | Đọc `scripts/doc_lint.py:83` + `tests/test_tdq_setup_skill.py` + `tests/test_agy_plugin_validate.py:34,153` | `SKILL.md` viết bằng tiếng Anh (theo luật ngôn ngữ tầng 1 `i18n_check.py`), giữ `<= 132` dòng (`SKILL_LINE_LIMITS["tdq-setup"]`), giữ liên kết `uu-tien-tim-kiem-chi-tiet.md`, không lặp câu luật tìm kiếm gốc, xóa path cá nhân cũ `~/Documents/Add_on_for_claude/agent-lsp`, tách chi tiết quy trình Zero-to-Full / `"setupfully tdq-workflow"` / Simulate 6 tầng sang `references/zero-to-full-agy.md` (giữ nguyên `skills: 12`, `rules: 10`, `md_count == 22`). |
| `README.md`, `README-Antigravity.md` + `tests/test_setup_fully_agy.py` _(mới)_ | Grep tài liệu & danh sách test hiện hữu | Cập nhật hướng dẫn Cửa 0 One-Liner + lệnh `"setupfully tdq-workflow"` trong tài liệu; viết bộ unit + integration test đầy đủ kiểm khóa máy trạng thái `setup-state.json`, `Host Session Fingerprint`, Caveman Node wrapper, Tavily `secrets.env`, Bootstrap/Manifest, và bộ `Simulate Test` 6 tầng. |

### Kiến thức nền, ràng buộc & phương án dự kiến

- **Bất biến kiến trúc bắt buộc giữ vững (`docs/kien-truc.md` & test suite):**
  1. `scripts/` không import `hooks/`; mọi script mới trong `scripts/` dùng Python stdlib thuần, bật log ISO-8601 ra `stderr` mặc định và tắt sạch khi `TDQ_LOG=0`.
  2. Mọi thao tác chạm máy ngoài repo (`~/.local/bin`, `~/.gemini/`, Registry User `PATH`, shell RC, tải mạng) bắt buộc đứng im tuyệt đối khi `TDQ_KHONG_CHAM_MAY=1`.
  3. `plugins/tdq-workflow-agy/` phải được sinh sạch qua `py -3 -X utf8 tools/build_agy_plugin.py` (không sửa tay rời rạc), đạt `0` lỗi trên `agy plugin validate --strict --json`, `doc_lint.py`, `i18n_check.py` và `token_budget.py --kiem`.
  4. Không bao giờ đặt `userConfig` trong `plugin.json` hay `variables` hoặc đường dẫn cá nhân trong `mcp_config.json`; mọi state, log cài đặt và `secrets.env` đặt tại `${PLUGIN_DATA}` (`~/.gemini/antigravity/plugin_data/tdq-workflow-agy`).
- **Phương án đã chọn vs Phương án loại bỏ:**
  - **Chọn:** Hybrid Rust `O(1)` flag check (`setup-pending.flag` -> `DelegatePython`) + 1 nguồn sự thật `tdq_setup_state.py` ở tầng Python cho `Host Session Fingerprint` & state transitions. **Loại bỏ:** Viết song song 2 bản Win32/POSIX process-tree parser trong cả Rust và Python (tốn gấp đôi mã nguồn và dễ lệch hành vi trên Linux/macOS khi chưa cross-compile lại binary trên máy Windows).
  - **Chọn:** Dùng lại mã cổng chuẩn `[TDQ:SETUP]` kết hợp `emit_user_markdown` cho thông báo hậu Restart và kích hoạt `"setupfully"`. **Loại bỏ:** Tạo mã thứ 24 `[TDQ:SETUP-RESUME]` làm vỡ hợp đồng `len(all_agy_codes) == 23` trên toàn bộ suite parity.
  - **Chọn:** Bọc Caveman trên Antigravity qua `"node"` + `"${PLUGIN_ROOT}/scripts/tdq_mcp_launcher.mjs", "caveman", "--", ...`, đồng thời giữ nhánh `sys.executable` cho file cấu hình kiểu Claude cũ. **Loại bỏ:** Ép 1 kiểu bọc duy nhất làm hỏng tính đa OS của Antigravity hoặc làm gãy unit test tương thích ngược của Claude Code.

### Lộ trình

| Bước/phase | CÓ-BỎ | Vì sao |
|---|---|---|
| Research ngoài bổ sung (`Step B2`) | BỎ | Toàn bộ tài liệu chính thức của Google Antigravity (`EV-A01..A10`), cơ chế `agy 1.4.12` và kho `tt-a1i/archify` đã được xác minh trực tiếp bằng thực nghiệm |
| Viết & duyệt `spec` (`tdq-spec`) | CÓ | Khóa chặt hợp đồng CLI flags, schema `setup-state.json`, 6 tầng `Simulate Test`, bảo mật `secrets.env` và ngưỡng đo trước ở `§6` |
| Subagent `tdq-reviewer` soi `spec`/`plan` | CÓ | Rà chéo chống sót neo `replace_exact` trong `tools/patches/` và kiểm tra tính tương thích đa OS trước khi viết code |
| Lập & duyệt `plan` (`tdq-plan`) | CÓ | Chia thành các đợt độc lập có 1 bài test `red -> green` rõ ràng cho mỗi task và khai đủ `Chạm:` cho các hub |
| Triển khai `implement` + Build plugin (`tdq-build`) | CÓ | Viết code Python/Node/Rust/Shell, chạy `build_agy_plugin.py`, kiểm tra trên sandbox & máy thật (theo phạm vi user chốt) |
| Kiểm định `qc` + `tdq-security-reviewer` | CÓ | Đối chiếu từng dòng DoD, chạy suite test, kiểm tra phân quyền `secrets.env` / chống shell injection và chạy QC theo `muc_qc` |
| Xuất báo cáo `report` + `Archify HTML` | CÓ | Tổng hợp kết quả Trước → Sau → Đã test gì → Kết quả test kèm sơ đồ trực quan phục vụ qua Tailscale Serve |

## Hỏi đáp

### Vòng 0 — Chọn pipeline (`2026-11-22T15:24:21+07:00`)
- **Câu hỏi:** `1. Bạn muốn chạy pipeline nào?` (`A`: chế độ chuyên sâu `deep`, `B`: chế độ nhanh `express`; đề xuất loại request: `feature`).
- **Trả lời nguyên văn:** `1a`
- **Chốt:** Chạy pipeline `full` (`deep`), `loai_request = feature`, mở nhánh `feature/trien-khai-setup-fully-agy` từ `dev`.

### Vòng 1 — Chốt hành vi chi tiết & mức QC (`2026-11-22T15:48:30+07:00`)
- **Các câu hỏi & lựa chọn đề xuất (`A`):**
  1. Cơ chế tự động khi gọi `"setupfully tdq-workflow"`: `A` — chạy thẳng một mạch không dừng hỏi lại (coi chính câu lệnh `"setupfully tdq-workflow"` là đồng ý cài trọn gói user-space, tự cài xong Pha 1 đến bước nhắc khởi động lại và tự chạy kiểm thử giả lập sau khi mở lại; lệnh `/tdq-setup` thường vẫn hiện bảng kê chờ duyệt 1 lần).
  2. Danh mục dependency, add-on và extension liên quan: `A` — trọn bộ hệ sinh thái TDQ trên Antigravity (Core 3-tier `Git`/`Node`/`uv`/`Python 3`+shim/`agy`/`agent-lsp`/Language Servers/`Graphify` + Add-ons `RTK`/`ripgrep`/`Caveman` Node proxy/`GEMINI.md` + tự tải `Archify` từ `tt-a1i/archify` nếu thiếu + kiểm trình duyệt cho `chrome-devtools` MCP + nạp mềm `secrets.env` cho Tavily + kiểm/bật plugin đồng hành `chrome-devtools-plugin`).
  3. Phạm vi triển khai và kiểm chứng trên máy Windows hiện tại: `A` — triển khai thật lên `~/.gemini/config/plugins/tdq-workflow-agy` (có sao lưu trước), chạy thật `Simulate Test` 6 tầng + kết xuất thử `Archify` trên máy này, đồng thời chạy trọn bộ test cô lập mô phỏng máy trắng tinh cho cả `Windows`, `macOS`, `Linux`.
  4. Mức QC: `A` — `ultra` (DoD + trọn bộ unit test + smoke test + runtime test trực tiếp + subagent `tdq-qc-tester` độc lập).
  5. Bổ sung thêm: `A` — Không, đủ rồi — làm tiếp đi.
- **Trả lời nguyên văn:** `1a 2a 3a 4a 5a`
- **Đã khóa toàn bộ câu hỏi mở:** Chuyển sang pha `spec` (`muc_qc = ultra`).
