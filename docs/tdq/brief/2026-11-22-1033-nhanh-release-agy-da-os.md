# BRIEF — Nhánh release Antigravity đa hệ điều hành và đồng bộ remote

Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

> **Tóm tắt dễ hiểu:** Yêu cầu này xây dựng nhánh phát hành sạch cho Antigravity để máy khác cài trực tiếp từ GitHub mà không lỗi. Công việc xử lý đồng thời hai điểm nghẽn chính là khử đường dẫn cứng máy cá nhân trong cấu hình MCP cùng hook đa hệ điều hành và đồng bộ nhánh phát triển với kho từ xa. Mục tiêu là mọi máy Windows, macOS và Linux đều cài đặt trọn vẹn chỉ bằng lệnh chính thức của Antigravity.

## Nguyên văn

> okay hãy giúp tôi mở request handle một nhánh release để có thể cài từ máy khác và xử lí cả 2 cái này {Đang tụt 25 commit so với dev cục bộ của bạn.
> Vẫn đóng cứng đường dẫn máy cá nhân C:\Users\admin\... và npx.cmd trong mcp_config.json, cũng như bin\tdq-dispatch.exe trong hooks.json — sang máy Windows khác user admin hoặc sang macOS/Linux là lỗi MCP và hooks.}

### Đọc hiểu bước đầu

- **Mục tiêu:**
  1. Thiết lập quy trình sinh và xuất bản **nhánh release Antigravity** để máy khác cài trực tiếp từ GitHub qua `agy plugin install` không lỗi.
  2. Khử toàn bộ đường dẫn cứng Windows `C:\Users\admin\...`, `npx.cmd` trong `mcp_config.json` và `bin\tdq-dispatch.exe` trong `hooks.json` để chạy đa hệ điều hành (`Windows`, `macOS`, `Linux`).
  3. Đồng bộ phần lệch commit giữa `dev` cục bộ và `origin/dev` (hiện đi trước 27 commit sau khi gộp báo cáo nghiên cứu) cùng nhánh release lên `origin`.

## Hiểu & kiến thức

### Năng lực dùng được

Phân vân → DÙNG. Kiểm kê ngày 2026-11-22: 42 skill trên đĩa, cộng skill built-in trong context. Không xoá bảng này kể cả khi không có dòng DÙNG nào.

| Skill | Nguồn | Phán quyết | Dùng ở đâu / Lý do loại |
|---|---|---|---|
| `tdq-intake` | `plugin:tdq-workflow-agy` | NỀN | Mở yêu cầu, phân tích và phỏng vấn đầu vào |
| `tdq-spec` | `plugin:tdq-workflow-agy` | NỀN | Soạn đặc tả kỹ thuật và dựng sơ đồ Archify Trước/Sau |
| `tdq-plan` | `plugin:tdq-workflow-agy` | NỀN | Lập kế hoạch thực thi chia đợt và kiểm tra hợp đồng |
| `tdq-build` | `plugin:tdq-workflow-agy` | NỀN | Thực thi đỏ–xanh, QC mức full và xuất báo cáo |
| `tdq-conventions` | `plugin:tdq-workflow-agy` | NỀN | Luật chung về trạng thái, Git, nhật ký và trình bày |
| `tdq-setup` | `plugin:tdq-workflow-agy` | NỀN | Kiểm chứng bộ tìm kiếm 3 tầng (LSP, Graphify, Grep) |
| `tdq-lean` | `plugin:tdq-workflow-agy` | NỀN | Kiểm soát mã gọn nhẹ, tránh viết thừa vòng |
| `tdq-status` | `plugin:tdq-workflow-agy` | NỀN | Đọc trạng thái yêu cầu khi cần kiểm tra tiến độ |
| `tdq-check-status` | `plugin:tdq-workflow-agy` | NỀN | Phục hồi trạng thái trên đĩa nếu gián đoạn phiên |
| `tdq-checkportable` | `plugin:tdq-workflow-agy` | NỀN | Đối chiếu tính di động của gói plugin khi chuyển máy |
| `plugin` | `built-in` | DÙNG | Đối chiếu cấu trúc chuẩn gói Antigravity (`plugin.json`, `hooks.json`, `mcp_config.json`, `${PLUGIN_ROOT}`, `${PLUGIN_DATA}`) ở đầu ra #1, #2, #3 |
| `agy-customizations` | `built-in` | DÙNG | Đối chiếu quy tắc discovery, rules, hooks và tương thích đường dẫn đa OS của Antigravity ở đầu ra #1, #2 |
| Đã xét 32 skill khác | `plugin` / `built-in` | KHÔNG | khác lĩnh vực |

### Bảng đối chiếu vùng chạm (Tam giác khảo sát 3 chiều)

| Vùng file chạm | Phát hiện qua lớp nào (Grep/LSP/Graphify) | Tác động & quan hệ |
|---|---|---|
| `tools/patches/agy_manifests.py` | Grep + LSP (`find_references` cho `generate_mcp_config`, `generate_hooks_json`) | Nguồn sinh `mcp_config.json`, `hooks.json`, `plugin.json`, `rules/AGENTS.md`; chuyển từ đọc `~/.claude.json` & nhánh `os.name == "nt"` sang sinh cấu hình đa hệ điều hành chuẩn |
| `tools/build_agy_plugin.py` | Grep + LSP (`generate_mcp_config`/`generate_hooks_json` caller) | Biên dịch `plugins/tdq-workflow-agy/`, đóng gói 2 launcher `.mjs` dưới `scripts/` và binary Rust dưới `bin/` kèm kiểm tra AST/cú pháp/budget |
| `tools/install_agy_plugin.py` & `install.py` | Grep (`tdq-dispatch`, `install_agy_plugin`) | Giữ tương thích trình cài cục bộ (`--sync-local-mcp`, `--with-caveman`, xử lý binary thực thi & hooks.json) với bố cục launcher mới |
| `scripts/build_portable.py` | Grep + LSP (`find_references` `sinh_nhanh_main` → 6 refs) + Graphify (`affected` → `main()`) | Bổ sung cờ `--sinh-release-agy` tái sử dụng Git plumbing (`_tao_tree_release`) để xuất bản nhánh `release/antigravity` sạch từ `plugins/tdq-workflow-agy/` không chạm working tree và không ảnh hưởng `main` |
| `plugins/tdq-workflow-agy/{hooks.json,mcp_config.json,scripts/*,rules/AGENTS.md}` | Grep + `agy plugin validate` | Bản đóng gói thực tế mà máy khác tải qua `agy plugin install`; 0 đường dẫn cá nhân, 0 dấu ngoặc kép trong `hooks.json`, đạt `agy plugin validate --strict --json` |
| `.github/workflows/build-rust-hooks.yml` | Grep (`tdq-dispatch`) | Mở rộng matrix đủ 4 mục tiêu (`win-x64`, `linux-x64-musl`, `darwin-arm64`, `darwin-x64`) và đồng bộ binary mới nhất (thử build qua SSH `ubuntu-100-95`/`mbair` nếu online) |
| `hooks/rust/tdq-dispatch/src/main.rs` | Read trực tiếp (`resolve_dispatch_script`) | Ưu tiên đọc biến môi trường `PLUGIN_ROOT` nên launcher chỉ cần truyền `PLUGIN_ROOT` là binary tìm đúng `hooks/scripts/dispatch.py` không cần sửa mã Rust trừ khi cần thiết |
| `tests/test_agy_plugin_validate.py`, `tests/test_build_portable.py`, `tests/test_command_gate.py`, `tests/test_remote_*_simulation.py` | Grep + LSP (`find_references`) | Cập nhật/bổ sung test khóa launcher đa OS (hook + MCP), nhánh `release/antigravity` idempotent, thử nghiệm cài cô lập và kiểm magic bytes |
| `README-Antigravity.md` | Grep + Read | Cập nhật hướng dẫn cài 1 lệnh từ nhánh `release/antigravity` và phiên bản hiện hành |

### Quyết định đã chốt & phương án đã loại

- **Nhánh release (`1a`):** Chọn tạo nhánh riêng `release/antigravity` qua `scripts/build_portable.py --sinh-release-agy` (giữ `main` cho Claude Code). Loại phương án thay nội dung `main` (`1b` — phá tương thích Claude Code và bộ test `main`) và cài trực tiếp từ `dev` (`1c` — lộ `docs/`/`tests/` và chịu ảnh hưởng commit WIP).
- **Hook đa OS (`2a`):** Chọn launcher Node.js mỏng `node scripts/tdq_hook_launcher.mjs --event <Event>` (tự phát hiện OS/arch, `chmod +x` trên Unix, truyền `PLUGIN_ROOT`, gọi binary Rust và fallback sang `python3`/`py -3`/`python` `hooks/scripts/dispatch.py`). Loại phương án chạy thuần Python (`2b` — dính bẫy `WindowsApps\python.exe` stub và chậm hơn Rust) và vá tay sau cài (`2c`).
- **MCP đa OS (`3a`):** Chọn launcher Node.js mỏng `node "${PLUGIN_ROOT}/scripts/tdq_mcp_launcher.mjs"` cho cả 3 server (`lsp` tự tìm `agent-lsp` auto-detect; `chrome-devtools` chạy `npx`/`npx.cmd` đúng OS với `--userDataDir=${PLUGIN_DATA}/chrome-devtools-profile`; `tavily-primary` chạy `npx`/`npx.cmd` đúng OS), giữ `--sync-local-mcp` cho tùy biến máy cục bộ. Loại phương án ghi thẳng `"npx"` (`3b` — rủi ro `ENOENT` trên Windows không qua shell và macOS GUI App thiếu `~/.local/bin` trên `PATH`).
- **Binary Rust đa OS (`4a`):** Cập nhật `.github/workflows/build-rust-hooks.yml` thêm `x86_64-apple-darwin` và thử build đồng bộ binary Linux/macOS qua SSH (`ubuntu-100-95`, `mbair`) nếu đang online; nếu offline thì launcher fallback sang Python `dispatch.py` an toàn và ghi chú rõ trong báo cáo.
- **Đồng bộ remote (`5b`):** Được user duyệt trước cho phép tự động chạy `git push origin dev` và `git push origin release/antigravity` sau khi toàn bộ QC `full` đạt xanh và hợp nhất cục bộ xong.
- **Mức QC (`6a`):** `full` (ghi `muc_qc=full` trong state).
- **Lý do bỏ qua scope round riêng:** Yêu cầu cùng báo cáo nghiên cứu tiền đề `2026-11-22-0821-research-marketplace-va-update` đã khoanh rõ toàn bộ 3 hạng mục kỹ thuật cần xử lý.

### Lộ trình

| Bước/phase | Chạy? | Vì sao |
|---|---|---|
| Research web | BỎ | Đã thu thập đầy đủ 11 tài liệu sống `antigravity.google` và thực nghiệm cách ly `agy v1.4.12` ngay trước request này |
| Interview chi tiết | CÓ | Đã chốt đủ 7 quyết định đổi đầu ra (`1a 2a 3a 4a 5b 6a 7a`) |
| Spec + Archify preview Trước/Sau | CÓ | Sửa luồng đóng gói và phát hành đang hoạt động, cần bản vẽ trực quan trước khi duyệt |
| Plan + kiểm hợp đồng | CÓ | Chia task không trùng file nóng, gắn kiểm chứng từng bước |
| Implement (đỏ → xanh) | CÓ | Xây launcher hook/MCP, bộ sinh nhánh release, cập nhật CI/docs và đồng bộ binary |
| QC mức `full` | CÓ | User chọn `6a` (`full`): DoD + trọn unit test + hồi quy vùng chạm + kiểm cài cô lập `agy` + ranh giới kiến trúc |
| QC độc lập (subagent) | BỎ | Mức QC đã chốt là `full` (chưa yêu cầu `ultra`) |
| Report + Archify HTML + đồng bộ `origin` | CÓ | Xuất báo cáo 4 phần, sơ đồ HTML qua Tailscale và đẩy `dev` + `release/antigravity` lên `origin` theo chấp thuận `5b` |

## Hỏi đáp

Ghi nhận vòng phỏng vấn ngày `2026-11-22T10:44:28+07:00` — user trả lời nguyên văn: `1a 2a 3a 4a 5b 6a 7a`.

1. **Tổ chức nhánh release Antigravity trên `origin`:** A (tạo nhánh riêng `release/antigravity` qua Git plumbing, giữ `main` cho Claude Code) / B (thay `main`) / C (dùng subpath `dev`) → Chọn **1a**.
2. **Xử lý `hooks.json` đa OS khi cài qua `agy plugin install`:** A (launcher `node scripts/tdq_hook_launcher.mjs` tự chọn Rust binary + fallback Python) / B (chạy thuần Python) / C (vá tay sau cài) → Chọn **2a**.
3. **Khử đường dẫn cứng trong `mcp_config.json`:** A (launcher `node "${PLUGIN_ROOT}/scripts/tdq_mcp_launcher.mjs"` + `${PLUGIN_DATA}` + giữ `--sync-local-mcp`) / B (ghi thẳng `agent-lsp` và `npx`) → Chọn **3a**.
4. **Đồng bộ binary Rust macOS/Linux (đang chậm 7 commit so với `f1e7fcfb`):** A (cập nhật CI workflow thêm `x86_64-apple-darwin` + thử SSH build `ubuntu-100-95`/`mbair` nếu online) / B (chỉ cập nhật CI, không SSH) → Chọn **4a**.
5. **Quyền `git push` đồng bộ `origin`:** A (dừng hỏi cuối request) / B (duyệt trước tự động `git push origin dev` và `git push origin release/antigravity` sau khi toàn bộ QC xanh) / C (chỉ làm cục bộ) → Chọn **5b**.
6. **Mức QC:** A (`full`) / B (`lite`) / C (`ultra`) → Chọn **6a (`full`)**.
7. **Bổ sung thêm:** A (Không, đủ rồi) / B (Có) → Chọn **7a**.
