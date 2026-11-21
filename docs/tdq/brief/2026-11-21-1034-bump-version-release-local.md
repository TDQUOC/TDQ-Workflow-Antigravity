# BRIEF — Bump Version, Phát hành (Release) & Cập nhật Antigravity User-Level Local

Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

## Nguyên văn

> okay hãy bump version và release và update cho user-lelvel local giúp tôi đi

Xác nhận từ người dùng qua 2 lượt: `1a và chỉ update cho antigravity` (chọn luồng `full`), và chốt chi tiết `1a 2a và xử lí luôn linux và mac dựa trên các máy qua ssh, nhớ dọn kĩ trên máy test linux và mac sau build và test 3a 4a 5 không`.

**Đọc hiểu ban đầu:**
- **Mục tiêu:** Nâng đồng bộ hệ thống TDQ Workflow lên **`0.103.0`** trên nhánh `dev`, tổng hợp đầy đủ 3 đợt nâng cấp sau `0.102.0`, biên dịch lại đủ **3 nhị phân Rust native** (`Windows`, `Linux musl` qua SSH `ubuntu-100-95`, `macOS ARM64` qua SSH `mbair`) kèm dọn sạch tuyệt đối các máy test sau build/test, đóng gói `plugins/tdq-workflow-agy/`, xuất bản nhánh `main` sạch tại local + tag `v0.103.0`, và cập nhật trọn bộ Antigravity user-level trên máy (`~/.gemini/config/plugins/tdq-workflow-agy` + khối `<!-- TDQ:TOOLS -->` trong `~/.gemini/GEMINI.md`, giữ nguyên Caveman/RTK, không chạm `~/.claude/` hay `~/.codex/`).

## Hiểu & kiến thức

### Bảng năng lực (Capability Inventory B0)

Đối chiếu `scripts/skill_inventory.py` (`41` mục trên đĩa) cùng nhóm skill built-in trong context phiên:

| Nguồn | Khớp với việc gì | Quyết định | Lý do |
|---|---|---|---|
| `tdq-conventions` (`repo` / `agy`) | Chuẩn trình bày, git/branch safety, quy tắc `doc_lint` | NỀN | Đọc để tuân thủ gate phát hành và định dạng báo cáo/chat |
| `tdq-setup` (`repo` / `agy`) | Đồng bộ khối `<!-- TDQ:TOOLS -->` trong `~/.gemini/GEMINI.md` | NỀN | Tham chiếu `ghim_huong_dan_tool` và cấu trúc block dòng `1145` |
| `tdq-checkportable` (`agy`) | Tự kiểm tính khả chuyển sau khi cài plugin | NỀN | Tham khảo kiểm tra bundle/plugin sau cài đặt |
| `tdq-spec`, `tdq-plan`, `tdq-build`, `tdq-intake`, `tdq-status`, `tdq-check-status`, `tdq-lean` (`repo` / `agy`) | Chạy quy trình spec/plan/implement/QC/report TDQ | NỀN | Khung làm việc bắt buộc của phiên hiện tại |
| `agy-customizations`, `antigravity-guide`, `plugin` (`builtin`) | Cấu trúc rule/plugin user-level `~/.gemini/` | THAM KHẢO | Kiểm chứng quy ước `~/.gemini/config/plugins/` và `GEMINI.md` |
| Các skill còn lại (`tdq-browser-*`, `chrome-devtools-plugin`, `gdocs`/`gdrive`/`gsheets`/`gslides`, `gemini-api*`, `google-antigravity-sdk`, `mcp-app-development`, `generative_ui`, `run-workflow`, `automation`, `migrate-*`, `swarm_monitor`, `9router-image`, `cdesktop`, `frontend-design`, `illustrator-preflight`) | Tác vụ trình duyệt, Google Workspace, API media/SDK, thiết kế, tự động hóa ngoài | KHÔNG | Khác lĩnh vực |

### Khảo sát mã nguồn & Tam giác tìm kiếm (LSP / Graphify / Grep)

- **LSP & công cụ:** Đã chạy `start_lsp` (Python), `find_symbol` (`sinh_nhanh_main`, `plugin_version`, `PLUGIN_VERSION`), `find_references` (`agy_manifests.py:11`); mở khóa `--bo-qua-lsp` hợp lệ vì `python:.` lỗi tham chiếu nội tệp tại `generate_manifest_and_readme`.
- **Graphify:** `graphify query "bump version release sinh_nhanh_main build_agy_plugin install_agy_plugin"` định vị đầy đủ cụm phụ thuộc `sinh_nhanh_main` (`scripts/build_portable.py:738`), `build()` (`tools/build_agy_plugin.py:202`), `install.py` (`1–400`), `tools/install_agy_plugin.py` (`1–376`) và `agy_manifests.py` (`11, 259`).
- **Máy build từ xa qua SSH:** `ubuntu-100-95` (Ubuntu x86_64, `rustc 1.100.0`, đã có `x86_64-unknown-linux-musl`, hiện có tàn dư cũ `/home/ubuntu/tdq-dispatch` và `/tmp/tdq_dispatch.tar.gz`) và `mbair` (macOS Apple Silicon ARM64, `rustc 1.100.0`, đã có `aarch64-apple-darwin`, `/Users/tdq/tdq*` đang sạch).
- **Tổng hợp nghiên cứu chi tiết:** [research/2026-11-21-1034-bump-version-release-local.md](../research/2026-11-21-1034-bump-version-release-local.md).

### Vòng phạm vi (Scope Round)

Vòng scope: BỎ — Đã chốt host đích là Antigravity (`chỉ update cho antigravity`) và mọi mặt kỹ thuật phát hành (giữ `CHANGELOG < 500` dòng, `test_docs_consistency`, `build_agy_plugin`, `--sinh-main`, bảo toàn Caveman/RTK) đều suy ra trực tiếp từ mã nguồn và bộ test repo; 5 điểm chốt cụ thể đã được xác nhận ở Vòng 1.

### Đánh đổi & Điểm đã chốt

1. **Phiên bản `0.103.0` & tài liệu (`1a`):** Bump tất cả manifest và tài liệu phát hành lên `0.103.0`, gộp đủ 3 đợt nâng cấp sau `0.102.0` (`4 trụ cột agent`, `investigate V2`, `trình bày ngắn gọn tự nhiên`) vào `CHANGELOG.md`, tách `0.61.0`–`0.60.0` sang `docs/CHANGELOG-archive-3.md` giữ `CHANGELOG.md < 500` dòng (luật R6), đồng bộ badge + số đếm thật trên `README.md` (`scripts/` `73`, `tests/` `4.602 passed`, giữ `skills/`/`agents/`/`hooks/` khớp `test_docs_consistency`) và `UPSTREAM-TRACE.md` (`Release Tag: v0.103.0`).
2. **Nhị phân Rust 3 nền tảng (`2a + SSH Linux/Mac + dọn kỹ`):** Nâng `hooks/rust/tdq-dispatch/Cargo.toml` lên `0.103.0`; build mới `tdq-dispatch.exe` trên Windows (`cargo 1.99.0`), build qua SSH `tdq-dispatch-linux-x86_64` trên `ubuntu-100-95` (`x86_64-unknown-linux-musl` static-pie) và `tdq-dispatch-darwin-arm64` trên `mbair` (`aarch64-apple-darwin`), tải về `plugins/tdq-workflow-agy/bin/`, chạy `cargo test` + `test_remote_linux_simulation.py` + `test_remote_mac_simulation.py`, và dọn sạch tuyệt đối cả thư mục tạm lần này lẫn tàn dư cũ trên 2 máy SSH sau build & test.
3. **Phạm vi Phát hành local (`3a`):** Commit & merge `--no-ff` vào `dev`, chạy `scripts/build_portable.py --sinh-main --nguon dev --nhanh-dich main` để xuất bản nhánh `main` sạch và tạo tag annotated `v0.103.0` trên `main` tại local, không tự `git push`.
4. **Cập nhật Antigravity user-level (`4a + chỉ update cho antigravity`):** Cài đặt `plugins/tdq-workflow-agy/` (`0.103.0`) ra `C:\Users\admin\.gemini\config\plugins\tdq-workflow-agy` bằng `install.py` (giữ nguyên Caveman + RTK và kích hoạt `agy`) ĐỒNG THỜI đồng bộ khối `<!-- TDQ:TOOLS -->` trong `C:\Users\admin\.gemini\GEMINI.md` theo chuẩn mới `tdq_setup.py:1145`. Tuyệt đối không chạm `~/.claude/` hay `~/.codex/`.
5. **Mức QC & Bổ sung (`5 không`):** Không có yêu cầu bổ sung; chạy QC đầy đủ mức `full` (bao gồm `tdq_test.py tron-bo`, Rust tests Windows/Linux/macOS, remote SSH simulation, `agy plugin validate --strict`, kiểm sạch tàn dư SSH, và xác minh bản live `~/.gemini/`).

## Hỏi đáp

### Vòng 1 (Đã chốt)

Trả lời của người dùng: `1a 2a và xử lí luôn linux và mac dựa trên các máy qua ssh, nhớ dọn kĩ trên máy test linux và mac sau build và test 3a 4a 5 không`

1. **Phiên bản & tài liệu (`1a`):** Chọn `A` — Bump `0.103.0`, gộp đủ 3 đợt nâng cấp sau `0.102.0`, tách `0.61.0`–`0.60.0` sang `docs/CHANGELOG-archive-3.md`, đồng bộ `README.md` và `UPSTREAM-TRACE.md`.
2. **Rust dispatcher 3 OS (`2a` + mở rộng SSH Linux/Mac):** Chọn `A` + build & test đủ cả Windows, Linux (`ubuntu-100-95`) và macOS (`mbair`) qua SSH, dọn sạch máy test Linux & Mac sau build/test.
3. **Phát hành local (`3a`):** Chọn `A` — Xuất bản `main` qua `--sinh-main` và gắn tag `v0.103.0` ở local, không tự `git push`.
4. **Antigravity user-level (`4a` + đã chốt chỉ Antigravity):** Chọn `A` — Cập nhật cả plugin `~/.gemini/config/plugins/tdq-workflow-agy` lẫn khối `<!-- TDQ:TOOLS -->` trong `~/.gemini/GEMINI.md`, không chạm Claude/Codex.
5. **Bổ sung (`5 không`):** Không có bổ sung ngoài yêu cầu dọn kỹ máy SSH Linux/Mac.

### Lộ trình

| Bước | Pha | Trạng thái | Việc chính |
|---|---|---|---|
| 1 | `analyze` | Xong | Chốt `0.103.0`, 3-OS Rust (Win + SSH Linux/Mac kèm dọn sạch), phát hành local `main`/tag, cài Antigravity + `GEMINI.md`, `muc_qc=full` |
| 2 | `spec` | Đang làm (Chờ duyệt) | Viết đặc tả đầy đủ 5 module và xuất bản Archify preview HTML Trước/Sau |
| 3 | `plan` | Chờ | Chia task theo module `M1–M5`, viết đủ bước kiểm & dọn sạch máy SSH |
| 4 | `implement` | Chờ | Bump version, build 3-OS Rust (Win/Linux/Mac) + simulation + dọn máy SSH, đóng gói plugin AGY |
| 5 | `qc` | Chờ | Chạy toàn bộ test (`tron-bo`), kiểm sạch SSH, validate `--strict`, kiểm chứng độc lập |
| 6 | `report` | Chờ | Xuất cặp report (`.md` + Archify HTML), hỏi commit/merge `dev`, chạy `--sinh-main` + tag `v0.103.0`, cài user-level AGY + sync `GEMINI.md` và chốt kiểm tra cuối |
| 7 | `idle` | Chờ | Đóng request và dọn nhánh tạm |
