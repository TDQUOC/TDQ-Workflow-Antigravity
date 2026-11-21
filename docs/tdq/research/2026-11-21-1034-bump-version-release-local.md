# RESEARCH — Bump Version, Phát hành (Release) & Cập nhật Antigravity User-Level

Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

- Ngày thực hiện: 2026-11-21
- Nguồn: Khảo sát trực tiếp mã nguồn, script đóng gói/cài đặt, bộ test toàn vẹn và hiện trạng cài đặt local trên máy (không cần tìm kiếm web ngoài vì toàn bộ quy trình phát hành nằm nội bộ repo).

---

## 1. Bản đồ các điểm ghim phiên bản (Version Pins)

Qua đối chiếu `rg`, `tdq-workflow-agy_lsp:find_symbol`/`find_references`, và `graphify query`, các vị trí ghim phiên bản hiện tại trên nhánh `dev` như sau:

| Thành phần | Giá trị hiện tại | Đường dẫn & Dòng | Ghi chú đồng bộ |
|---|---|---|---|
| Manifest Claude | `0.102.0` | `.claude-plugin/plugin.json:4` | Khóa bởi `tests/test_docs_consistency.py:23-39` |
| Manifest Codex | `0.102.0` | `.codex-plugin/plugin.json:3` | Phải trùng với Claude manifest (`test_adapter_host.py:71`, `test_docs_consistency.py:39`) |
| Compiler AGY (constant) | `0.102.0` | `tools/patches/agy_manifests.py:11` (`PLUGIN_VERSION`) | Sinh `plugins/tdq-workflow-agy/{plugin.json,manifest.json,README.md}` |
| Compiler AGY (docstring/CLI) | `0.102.0` | `tools/patches/__init__.py:1`, `tools/build_agy_plugin.py:2,275` | Mô tả phiên bản đang biên dịch |
| Badge & bảng Host README | `0.102.0` | `README.md:3,144` | Ngoài ra badge tests đang ghi `4525 passed` (`README.md:4`) và bảng §7 ghi `scripts/ (43)` trong khi thư mục thực tế có `73` file `.py`, `11` skill, `8` agent, `17` hook, và đợt test gần nhất đạt `4.602 passed` |
| Tài liệu truy vết Upstream | `v0.102.0` | `UPSTREAM-TRACE.md:24` | Mục `Release Tag` |
| Lịch sử phát hành | `0.102.0` | `CHANGELOG.md:5` | Phải khớp đỉnh `plugin.json` (`test_docs_consistency.py:28-30`) và dài `<= 500` dòng (`scripts/doc_lint.py:127`) |
| Bundle AGY biên dịch sẵn | `0.102.0` | `plugins/tdq-workflow-agy/{plugin.json,manifest.json,README.md}` | Tự động tái sinh hoàn toàn khi chạy `py -3 -X utf8 tools/build_agy_plugin.py --upstream .` |
| Crate Rust dispatcher | `0.101.0` | `hooks/rust/tdq-dispatch/Cargo.toml:3` | `tdq-dispatch.exe` Windows đã biên dịch mới ngày `2026-11-21` trong `investigate V2`; nhị phân Linux/macOS giữ bản prebuilt ngày `2026-11-19`; máy có `cargo 1.99.0` |

## 2. Ràng buộc `CHANGELOG.md` và nội dung sau `0.102.0`

- `scripts/doc_lint.py:127` khóa cứng `MAX_LINES_ANY = 500`. `CHANGELOG.md` hiện có **480 dòng**, chỉ còn dư `20` dòng trước ngưỡng báo lỗi `doc_lint`.
- Tệp `docs/CHANGELOG-archive-3.md` (hiện `82` dòng, lưu `0.59.0` đến `0.57.0`) được tạo riêng cho việc tách mục cũ ở đáy `CHANGELOG.md` nhằm giữ file chính `< 500` dòng (`CHANGELOG.md:477-480`). Tách thêm `0.61.0`–`0.60.0` (khoảng `29` dòng từ `CHANGELOG.md:449-476`) sang đầu `docs/CHANGELOG-archive-3.md` giúp `CHANGELOG.md` còn ~`451` dòng trước khi thêm đầu mục `0.103.0`.
- Sau commit `2c1fb7b0` (bump `v0.102.0`, `Plan V2+`), nhánh `dev` đã gộp **3 đợt nâng cấp lớn** cần ghi vào release notes tiếp theo:
  1. `2026-11-20-1230-trien-khai-4-de-xuat-agent`: Cấu hình `tdq-config.json` + Gemini tier, đội hình `8` agent (`6+2`) kèm `Auto-Clarity`, `handoff-schema.json` + Packet V2+ đa ngôn ngữ + Shared Blackboard, quote-aware shell guard Python+Rust, `subagent_stop.py`, telemetry theo `agent_role`.
  2. `2026-11-21-0217-trien-khai-investigate-v2`: Kiến trúc `work_kind=investigate` V2 tách luồng `build`/`investigate`, engine `evidence add|merge|render` khóa đa nền tảng không phụ thuộc `fcntl`, bảo mật `scoped-write` `5` lớp đồng bộ Python+Rust, Rust Weighted Burden guard (`tdq-dispatch.exe` median ~`14.35 ms`).
  3. `2026-11-21-0917-mac-dinh-trinh-bay-ngan`: Chuẩn trình bày ngắn gọn, tự nhiên, dễ hiểu cho `spec`/`plan`/`report` (`Plain-Language Narrative Rule`, gỡ ép nén `·` trong `report`, thêm `Tóm tắt nhanh`/`Tóm tắt dễ hiểu` dưới trần `3.500` token), cập nhật `scripts/tdq_setup.py`, `docs/claude-md-mau.md` và `tools/patches/agy_manifests.py`.

## 3. Cơ chế Phát hành (`main` & Tag) vs Cập nhật Antigravity User-Level

- **Xuất bản nhánh `main`:** `scripts/build_portable.py:738-780` (`sinh_nhanh_main`) đọc `git ls-tree` trên `dev`, lọc qua `la_duong_dan_release` (giữ runtime + `plugins/tdq-workflow-agy/`, loại `docs/tdq/`, `tests/`, `hooks/rust/`, `CHANGELOG-archive*.md`, `scripts/` dev-only), dựng cây sạch qua `GIT_INDEX_FILE` tạm và tạo commit trên `refs/heads/main` không làm bẩn working tree. Hiện `main` đang ở `51e24801` (`Release v0.100.0`), còn tag local mới nhất là `v0.99.0`.
- **Cài đặt Antigravity user-level (`~/.gemini/config/plugins/tdq-workflow-agy`):**
  - Bản đang chạy trên máy ở version **`0.101.0`** (`upstream_commit: 51e24801`, `agy plugin list` báo `enabled`).
  - `install.py` đồng bộ in-place từ `plugins/tdq-workflow-agy/` sang `~/.gemini/config/plugins/tdq-workflow-agy` (tránh `WinError 32`), tự chỉnh `hooks.json` thành `bin\tdq-dispatch.exe --event ...`, chạy `agy.EXE plugin validate ... --strict --json`, chạy `agy.EXE plugin enable tdq-workflow-agy`, đồng thời kiểm RTK + Caveman.
  - Trên máy hiện có `~/.tdq/caveman.json` (`"enabled": true`, bọc `lsp`, `chrome-devtools`, `tavily-primary`), nên cả `install.py` lẫn `tools/install_agy_plugin.py` đều tự nhận `preserved_opt_in` và bọc lại `mcp_config.json` với `tdq_mcp_shrink.py` sau khi copy. So sánh `mcp_config.json` của `plugins/tdq-workflow-agy/` với bản live `~/.gemini/config/plugins/tdq-workflow-agy/mcp_config.json` cho thấy danh sách `7` language server (`typescript`, `python`, `json`, `html`, `css`, `rust`, `csharp`), `chrome-devtools` và `tavily-primary` trùng khớp hoàn toàn.
- **Đồng bộ quy tắc toàn cục `~/.gemini/GEMINI.md`:**
  - `~/.gemini/GEMINI.md` đang ghim khối `<!-- TDQ:TOOLS --> ... <!-- /TDQ:TOOLS -->` ở phiên bản trước `2026-11-21-0917` (chưa có dòng mới `- Mặc định cho cả spec, plan và report...` tại `scripts/tdq_setup.py:1145`).
  - Trong `scripts/tdq_setup.py`, `DUONG_INSTRUCTION` mặc định trỏ `~/.claude/CLAUDE.md` (và `_sync_agy_guard_ghim` chặn ghi `~/.claude/` khi chạy từ context AGY), nhưng gọi `ghim_huong_dan_tool(os.path.expanduser("~/.gemini/GEMINI.md"), goc=os.path.expanduser("~/.gemini/config/plugins/tdq-workflow-agy"))` sẽ cập nhật đúng block `<!-- TDQ:TOOLS -->` trong `~/.gemini/GEMINI.md` mà vẫn giữ nguyên phần ngoài block (`## Ngôn ngữ trong chat`) và không chạm `~/.claude/`.
- **Phạm vi loại trừ đã chốt với người dùng:** `"chỉ update cho antigravity"` — không cập nhật cache `~/.claude/` hay `~/.codex/` trên máy local.
