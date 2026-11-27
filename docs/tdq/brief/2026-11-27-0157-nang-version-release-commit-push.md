# Brief — Nâng version, phát hành release, commit và push

Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

## Nguyên văn

> okay hãy nang version và relaese và commit và push

- **Mục tiêu:** Nâng số phiên bản đồng bộ sau khi hoàn tất 3 pha `P0`–`P2`, cập nhật `CHANGELOG.md`, biên dịch lại gói `plugins/tdq-workflow-agy/`, xuất bản nhánh phát hành sạch `main` và `release/antigravity`, tạo commit chốt trên `dev`, gắn tag phát hành (nếu chọn) và đẩy các nhánh tương ứng lên remote `origin`.
- **Phạm vi dự kiến (đối chiếu từ commit phát hành `89c99384` — `v0.107.0`):**
  - Nhóm tệp khai báo phiên bản gốc & host: `.claude-plugin/plugin.json`, `.codex-plugin/plugin.json`, `docs/tdq/.tdq-phat-hanh.json`, `README.md`, `README-Antigravity.md`, `CHANGELOG.md` (kèm archive nếu vượt trần R6 `500` dòng).
  - Nhóm biên dịch & plugin Antigravity: `tools/build_agy_plugin.py`, `tools/patches/__init__.py`, `tools/patches/agy_manifests.py` và gói biên dịch `plugins/tdq-workflow-agy/` (`plugin.json`, `manifest.json`, `README.md`).
  - Nhánh phát hành & remote: xuất bản `main` (`--sinh-main`), `release/antigravity` (`--sinh-release-agy`), kiểm định `agy plugin validate --strict`, gắn tag phiên bản và `git push origin`.
- **Kết quả bước 1b (định tuyến & tìm kiếm):**
  - `tdq_domains.py route` trả `code-build` (`work_kind=build`, `reason=ambiguous_tie_fallback`).
  - `skill_router.py --tra "nang version release commit push"` gợi ý `#1 tdq-build` (`7.07`).
  - `tdq_lsp.py check` đạt `5/8` bậc, smoke `3/3` tầng (`grep`, `LSP`, `graphify`) ĐẠT; Bậc 8 `python:.` `CHUA_KIEM`, `javascript:.` và `rust:hooks/rust/tdq-dispatch` `HET_HAN` (xử lý khi `tdq_state.py init` sau khi chốt pipeline).
- **Điểm cần chốt ở pha phân tích:**
  - Chọn số phiên bản mới (`0.108.0` hay `0.110.0` / số khác) và xử lý `hooks/rust/tdq-dispatch/Cargo.toml` (đang ở `0.105.0`).
  - Cập nhật badge kiểm thử trong `README.md` (`4602 passed` → `5012 passed`) và archive `CHANGELOG.md` (hiện `417` dòng).
  - Phạm vi phát hành và đẩy remote: đẩy lên `origin` những nhánh nào (`dev`, `main`, `release/antigravity`) và có đẩy kèm tag `v...` hay không, kèm xác nhận cài thử cục bộ (`install_agy_plugin.py`) nếu cần.

## Hiểu & kiến thức

### Năng lực dùng được

Phân vân → DÙNG. Kiểm kê ngày 2026-11-27: 42 mục skill trên đĩa (`23` giữ qua `--loc`, `19` ẩn thuộc nhóm ngoài phạm vi), cộng skill built-in trong context. Không xoá bảng này kể cả khi không có dòng DÙNG nào.

| Skill | Nguồn | Phán quyết | Dùng ở đâu / Lý do loại |
|---|---|---|---|
| `tdq-intake`, `tdq-spec`, `tdq-plan`, `tdq-build`, `tdq-conventions`, `tdq-setup`, `tdq-lean`, `tdq-status`, `tdq-check-status`, `tdq-checkportable` | `plugin:tdq-workflow` / `plugin:tdq-workflow-agy` | NỀN | Quy trình lõi `analyze` → `spec` → `plan` → `implement` → `qc` → `report` và kiểm tra gói portable |
| `tdq-browser-research`, `tdq-browser-test` | `plugin:tdq-workflow` / `plugin:tdq-workflow-agy` | KHÔNG | khác lĩnh vực — yêu cầu phát hành CLI/git nội bộ, không kiểm thử trang web |
| Đã xét 19 skill khác trên đĩa | user/plugin | KHÔNG | khác lĩnh vực |
| `chrome-devtools`, `a11y-debugging`, `cookie-debugging`, `debug-optimize-lcp`, `memory-leak-debugging`, `gdocs`, `gdrive`, `gsheets`, `gslides`, `gemini-api-*`, `generative_ui`, `mcp-app-development`, `automation`, `conversations`, `plugin`, `run-workflow`, `migrate-*`, `agy-customizations`, `antigravity-guide`, `google-antigravity-sdk`, `ui-plugin-navigation` | built-in/plugins | KHÔNG | khác lĩnh vực |

### Khảo sát mã nguồn 3 chiều (Triangulation)

- **Lý do bỏ qua LSP Python ở bước tra cứu:** `mcp_tdq-workflow-agy_lsp_start_lsp(language_id="python")` báo `no server configured for language "python"` (Bậc 8 đang `CHUA_KIEM`), nên áp dụng ngoại lệ theo `skills/tdq-setup/references/uu-tien-tim-kiem.md` để rơi về Graphify + Grep + đọc trực tiếp.

| Vùng file chạm | Phát hiện qua lớp nào (Grep/LSP/Graphify) | Tác động & quan hệ |
|---|---|---|
| `.claude-plugin/plugin.json`, `.codex-plugin/plugin.json`, `docs/tdq/.tdq-phat-hanh.json` | Grep (`git grep "0\.107\.0"`) + Read (`plugin_version()`) | Khai báo version cấp host Claude/Codex và mốc phát hành TDQ (`docs/tdq/.tdq-phat-hanh.json` dùng chống hạ cấp trong `tdq_setup.py`) |
| `tools/patches/agy_manifests.py` (`PLUGIN_VERSION`), `tools/patches/__init__.py`, `tools/build_agy_plugin.py`, `plugins/tdq-workflow-agy/` | Grep (`PLUGIN_VERSION`, `0\.107\.0`) + Read (`build_agy_plugin.py`) | Nguồn sinh `plugins/tdq-workflow-agy/{plugin.json,manifest.json,README.md}`; `sinh_nhanh_release_agy()` đọc version trực tiếp từ `plugins/tdq-workflow-agy/plugin.json` |
| `scripts/build_portable.py` (`sinh_nhanh_main`, `sinh_nhanh_release_agy`), `scripts/claude_export.py` (`plugin_version`) | Graphify (`query`) + Grep + Read | Xuất bản sạch `main` (từ `plugin_version(repo)` = `.claude-plugin/plugin.json`) và `release/antigravity` qua git plumbing không chạm working tree |
| `README.md`, `README-Antigravity.md`, `CHANGELOG.md`, `docs/CHANGELOG-archive-*.md`, `docs/architecture/` | Grep + Read (`doc_lint.py` R6, `status.json`) | `README.md` mang badge version + `tests-4602%20passed`; `CHANGELOG.md` đang `417` dòng (giới hạn R6 `<= 500` dòng); `docs/architecture/status.json` đang `stale` (`24` thay đổi từ `P0`–`P2`) |
| `hooks/rust/tdq-dispatch/Cargo.toml` | Read (`Cargo.toml`) | Đang giữ `version = "0.105.0"` từ đợt 0.105/0.106/0.107; cần hỏi user giữ nguyên hay bump + rebuild Rust |
| `tools/install_agy_plugin.py` | Grep + Read + `--dry-run` | Đồng bộ bản build mới sang `~/.gemini/config/plugins/tdq-workflow-agy` nếu user muốn cập nhật luôn máy hiện tại |

Vòng scope: BỎ — yêu cầu `chore` nâng phiên bản và phát hành bám theo khuôn mẫu sẵn có từ bản `v0.107.0` (`89c99384`), không thêm hành vi hay API công khai mới; mọi tham số phạm vi được hỏi thẳng ở các câu hỏi chi tiết.

### Quyết định đã chốt

- **Phương án chọn:** Nâng đồng bộ lên `0.108.0` bao gồm cả `hooks/rust/tdq-dispatch/Cargo.toml` + `cargo build --release`; cập nhật `CHANGELOG.md` (giữ `<= 500` dòng theo R6, chỉ xoay phần cũ sang `docs/CHANGELOG-archive-4.md` nếu chạm trần), cập nhật badge `README.md` (`4602 passed` → `5012 passed`) và chạy `tdq_archify.py sync-master` làm mới Master Map; biên dịch `plugins/tdq-workflow-agy/` kèm đồng bộ cài đặt cục bộ `~/.gemini/config/plugins/tdq-workflow-agy`; merge về `dev`, xuất bản `main` (`--sinh-main`) và `release/antigravity` (`--sinh-release-agy`), gắn annotated tag `v0.108.0` trên `main`, rồi push đủ `dev`, `main`, `release/antigravity` và tag `v0.108.0` lên `origin`.
- **Đã loại:** Bỏ giữ `Cargo.toml` ở `0.105.0`; bỏ giữ nguyên badge cũ/Master Map stale; bỏ đẩy sang `local-upstream` hay bỏ qua tag; bỏ không đồng bộ máy local `~/.gemini/`.

### Lộ trình

| Bước/phase | Chạy? | Vì sao |
|---|---|---|
| Research web | BỎ | Toàn bộ cấu trúc phiên bản, kịch bản đóng gói và nhánh phát hành đã xác minh trực tiếp trong mã nguồn repo (`89c99384`, `build_portable.py`, `build_agy_plugin.py`, `README-Antigravity.md`). |
| Interview | CÓ | Đã hoàn tất chốt 6 câu hỏi chi tiết (`1b 2a 3a 4a 5a 6a`) và khóa `muc_qc=full`. |
| Spec & Plan | CÓ | Chế độ chuyên sâu (`full`): lập spec + HTML Trước/Sau Archify → user duyệt spec → lập plan kiểm chứng → user duyệt plan. |
| Implement & Build | CÓ | Nâng version `0.108.0` đa host + Rust, build lại `tdq-dispatch.exe` và `plugins/tdq-workflow-agy/`, đồng bộ docs & Master Map, cài local `~/.gemini/`, chạy đầy đủ test + `agy validate`, xuất bản `main` + `release/antigravity` + tag `v0.108.0` và push `origin`. |
| QC độc lập (agent) | BỎ | User chọn `muc_qc=full` (`5a`): thực thi đủ DoD + full suite `tron-bo` + `smoke-e2e --changed` + hồi quy vùng chạm + kiểm tra kiến trúc + clean code (không gọi subagent `tdq-qc-tester` vốn chỉ bật ở `ultra`). |
| Report & Archify HTML | CÓ | Xuất báo cáo Markdown + Archify HTML, cập nhật sổ `workinglog` và đóng `state.json` về `idle`. |

## Hỏi đáp

1. **Số phiên bản mới (`0.108.0` đa host + `Cargo.toml` hay giữ nguyên Rust `0.105.0`):** User chọn **1b** — nâng đồng bộ `0.108.0` cả host/plugin/docs lẫn `hooks/rust/tdq-dispatch/Cargo.toml` và chạy `cargo build --release`.
2. **Tài liệu & Master Map (`CHANGELOG.md`, `README.md`, `docs/architecture/`):** User chọn **2a** — thêm `## 0.108.0` tổng hợp `P0`–`P2` vào `CHANGELOG.md` (giữ `<= 500` dòng, xoay sang archive nếu vượt trần), nâng badge `README.md` lên `5012 passed` và chạy `sync-master` làm mới Master Map.
3. **Nhánh phát hành, tag và phạm vi `git push`:** User chọn **3a** — merge về `dev`, xuất bản `main` (`--sinh-main`) và `release/antigravity` (`--sinh-release-agy`), gắn annotated tag `v0.108.0` trên `main`, rồi push `dev`, `main`, `release/antigravity` và tag `v0.108.0` lên `origin`.
4. **Cài đồng bộ plugin cục bộ (`~/.gemini/config/plugins/tdq-workflow-agy`):** User chọn **4a** — chạy `tools/install_agy_plugin.py` sau khi build xong.
5. **Mức QC (`muc_qc`):** User chọn **5a** — `full` (đã ghi `tdq_state.py set muc_qc=full`).
6. **Bổ sung thêm:** User chọn **6a** — không bổ sung thêm.

