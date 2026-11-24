# BRIEF — Triển khai trọn bộ đề xuất cải thiện Archify (Drill-down nhiều tầng & Logic Node Registry)

Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

## Nguyên văn

> Okay hãy mở request implement all đề xuất trong 1 request đi

- **Đọc ban đầu — Mục tiêu:** Triển khai toàn bộ **Phương án A (No-Fork Hybrid)** từ báo cáo nghiên cứu `docs/tdq/reports/2026-11-24-1106-research-archify-drilldown-nodes.md` trong một request duy nhất — giữ nguyên `tt-a1i/archify` (không fork) và bổ sung đầy đủ hệ thống **Logic Node Registry**, băm 2 lớp chống false-dirty (`ast_symbol_sha256` + `span_binding`), chiến lược Incremental (Tầng 1–2) + Lazy Depth (Tầng 3–5+), vỏ HTML tương tác đa tầng (`docs/architecture/` tải lười qua HTTP/Tailscale + `tdq_archify.py serve` + fallback `file://`, Spec/Report tự chứa gọn), thí điểm chuyển đổi cụm thật của TDQ (`hooks-and-gates` + `search-and-archify`) sang cây 4 tầng, cập nhật hướng dẫn skill (`tdq-spec`/`tdq-build`/`archify-lifecycle.md`) và kiểm chứng tự động (unit/E2E + Chrome DevTools).

## Hiểu & kiến thức

### Năng lực dùng được

Phân vân → DÙNG. Kiểm kê ngày 2026-11-24: 42 skill trên đĩa (`skill_inventory.py --loc "archify browser test html diagram python"` giữ 23, ẩn 19), cộng skill built-in trong context. Không xoá bảng này kể cả khi không có dòng DÙNG nào.

| Skill | Nguồn | Phán quyết | Dùng ở đâu / Lý do loại |
|---|---|---|---|
| `tdq-intake`, `tdq-conventions`, `tdq-spec`, `tdq-plan`, `tdq-build`, `tdq-status`, `tdq-setup`, `tdq-check-status`, `tdq-lean`, `tdq-checkportable` | `plugin:tdq-workflow` / `plugin:tdq-workflow-agy` | NỀN | Khung vận hành workflow TDQ (`full` + `build`) |
| `tdq-browser-test` / `chrome-devtools` | `plugin:tdq-workflow-agy` / `built-in` | DÙNG | Kiểm thử trình duyệt thật ở Pha 4: mở Portal `docs/architecture/index.html` và Spec/Report drill-down, bấm kiểm tra đào sâu `>= 4` tầng, breadcrumb, cycle guard, fallback offline và xác nhận `0` console error |
| Đã xét 40+ skill khác (`tdq-browser-research`, Google Workspace, Gemini API, `a11y-debugging`, `generative_ui`, `plugin`…) | user/plugin/built-in | KHÔNG | khác lĩnh vực |

### Bản đồ vùng chạm (Tam Giác Khảo Sát 3 Chiều)

| Vùng file chạm | Phát hiện qua lớp nào (Grep/LSP/Graphify) | Tác động & quan hệ |
|---|---|---|
| `scripts/archify_registry.py` (mới) | Kiến trúc từ báo cáo `2026-11-24-1106` | Quản lý Logic Node Registry (`index.json` + `nodes/<id>.json`), hash 2 lớp (`ast_symbol_sha256` + `span_binding`), cycle guard (`visited_stack`), tách `planned` vs `working-tree`/`committed` |
| `scripts/archify_portal.py` (mới) | Tách clean architecture từ `tdq_archify.py` | Dựng vỏ HTML Drill-Down Portal dùng chung (`< 250 KB`), nhúng lát cắt SVG (`~26 KB`), giải thích tự nhiên + mini-flowchart + breadcrumb + cycle anchor, hỗ trợ tải lười HTTP + `<script>` fallback `file://`, và chế độ tự chứa gọn cho Spec/Report |
| `scripts/archify_model.py` | Grep + LSP (`validate_model` có `39` tham chiếu) + Graphify (`tdq_archify.py:41`) | Mở rộng validator chấp nhận cấu trúc `registry` / `nodes` tùy chọn nhưng giữ 100% tương thích ngược với `master.model.json` v1 |
| `scripts/archify_artifacts.py` | Grep + LSP (`mark_stale` có `7` tham chiếu) + Graphify (`tdq_archify.py:51`) | Cập nhật `EXCLUDED_DIR_NAMES` (bỏ `target`, `.pytest_cache` tránh false-dirty từ Rust build), hỗ trợ manifest cho bundle lát cắt `slices/` + `nodes/` |
| `scripts/archify_delivery.py` | Grep (`test_archify_delivery.py`, `tdq_setup.py`, `tdq_simulate_verify.py`) | Giữ nguyên `run_finalize`, bổ sung helper khởi chạy HTTP server cục bộ an toàn (`127.0.0.1`) cho `tdq_archify.py serve` |
| `scripts/tdq_archify.py` | Grep + LSP (`sync_master` có `11` tham chiếu) | Thêm `sync-master --incremental`, tích hợp Logic Node Registry & Shared Portal Shell, hỗ trợ `render --type drilldown` (tự chứa `<= 4` tầng) và subcommand `serve` |
| `scripts/tdq_setup.py` | Grep (`kiem_tra_archify`, `_apply_addons_agy`, `ensure_archify_installed`) | Khai báo `tree-sitter` + 4 gói grammar lõi (`python`, `javascript`, `typescript`, `rust`) thành dependency chính thức trong setup (`_inspect_tree_sitter`, `ensure_tree_sitter_installed`, tôn trọng `TDQ_KHONG_CHAM_MAY=1`) |
| `docs/tdq/models/` & `docs/architecture/` | Grep (`master.model.json`) | Lưu kho `docs/tdq/models/registry/` cho cụm Pilot (`hooks-and-gates` + `search-and-archify` 4 tầng) và tái sinh `docs/architecture/` gọn nhẹ |
| `skills/tdq-build/references/archify-lifecycle.md`, `skills/tdq-spec/references/archify-ba.md`, `skills/tdq-intake/references/archify-quick.md` | Grep + `test_archify_workflow_contract.py` | Bổ sung quy trình Logic Node Registry, Incremental + Lazy Depth và lệnh `serve` — giữ nguyên vẹn 17 cụm từ hợp đồng mà `test_archify_workflow_contract.py` đang khóa |
| `scripts/build_portable.py` & `plugins/tdq-workflow-agy/` | Grep (`test_archify_distribution.py:345`) | Đảm bảo module mới (`archify_registry.py`, `archify_portal.py`) tự động đóng gói trong release closure và chạy `build_portable.py --sinh-agy` đồng bộ bản AGY |
| `tests/test_archify_*.py`, `tests/test_tdq_archify.py`, `tests/test_tdq_setup.py`, `tests/test_agy_host_setup.py` | Grep (`218` test archify nền + bộ test setup) | Giữ xanh toàn bộ test cũ + bổ sung test mới cho `tree-sitter` AST hash, dịch dòng `0` false-dirty, cycle guard, incremental sync, `serve`/fallback, setup dependency `tree-sitter`, phân phối module và E2E trình duyệt |

### Hồ sơ kiến trúc, Ràng buộc & Bỏ qua có điều kiện

- Đã đọc trọn `docs/kien-truc.md` (`118` dòng): tuân thủ tuyệt đối `scripts/` không import `hooks/`, `skills/` chỉ nhắc tên lệnh của `scripts/`, chỉ `tdq_state.py` ghi `docs/tdq/state.json`, không sửa engine gốc `C:\Users\admin\Documents\archify` (`0` fork), và không làm vỡ bộ hợp đồng `test_archify_workflow_contract.py` / `test_archify_distribution.py` / `tdq_state.py` gate.
- `Vòng scope: BỎ — các mảng phạm vi (tương thích upstream không fork, căn cứ mã nguồn, tối ưu token/thời gian, kiểm duyệt trình duyệt, cả hai bề mặt Master Map & Spec/Report, quy mô >100 node / >=5 tầng) đã được người dùng chốt đầy đủ ở request nghiên cứu 2026-11-24-1106-research-archify-drilldown-nodes và yêu cầu triển khai trọn bộ.`
- **Nghiên cứu nguồn ngoài (B3): BỎ** — toàn bộ kiến trúc dựa trên `tree-sitter 0.25.2` (đã có sẵn cùng `graphifyy` trong môi trường Python và kiểm chứng trực tiếp API `Language`/`Parser` trên 5 grammar), Python stdlib, vanilla HTML/CSS/JS và engine `tt-a1i/archify` v3.2 đã kiểm chứng thực nghiệm (`14/14` bằng chứng) ngay ở request trước.
- **LSP & Graphify:** Đã làm mới Graphify (`8,852` nodes, `23,035` edges) và xác minh đạt bậc 8 qua MCP cho cả `python:.` (`N=2`) và `rust:hooks/rust/tdq-dispatch` (`N=5`); nhánh làm việc `feature/implement-archify-drilldown-registry` mở từ `dev`.
- **Đo nền test hiện có (`Đo trước`):** `$env:PYTHONPATH='tests'; py -3 -X utf8 -m unittest discover -s tests -p "test_*archify*.py"` đạt `218` tests (`OK`, `1` skipped) trong `52.494s`; `tree-sitter 0.25.2` + `tree-sitter-{python,javascript,typescript,rust}` đều đã cài và chạy chuẩn trên máy.
- **Quyết định chốt (2026-11-24T13:28+07:00):** `1b` (`tree-sitter` làm parser AST chính và đưa vào dependency chính thức của `tdq_setup.py`, giữ fallback an toàn sang Python `ast` / `file_fallback` khi thiếu grammar), `2a` (tương thích ngược 100% + Pilot trực tiếp `hooks-and-gates` & `search-and-archify` 4 tầng vào `docs/architecture/index.html`), `3a` (cả Master Portal + `render --type drilldown` tự chứa `<= 4` tầng + `serve` HTTP `127.0.0.1` + fallback `<script>` cho `file://`), `4a` (loại `target`/`.pytest_cache` khỏi `EXCLUDED_DIR_NAMES` + đồng bộ `plugins/tdq-workflow-agy/`), `5a` (`muc_qc=full`), `6a` (đủ rồi).

### Lộ trình

| Bước / Phase | CÓ / BỎ | Vì sao |
|---|---|---|
| Research web ngoài (`B3`) | BỎ | Triển khai thuần nội bộ trên `tree-sitter 0.25.2` (có sẵn theo `graphifyy`), Python stdlib và `tt-a1i/archify` v3.2 đã kiểm chứng ở request trước |
| Phỏng vấn chi tiết (`B4`) | CÓ (ĐÃ XONG) | Đã chốt đủ 6 câu (`1b + tree-sitter setup`, `2a`, `3a`, `4a`, `5a muc_qc=full`, `6a`) |
| Đặc tả + Bản xem trước Archify BA (`spec`) | CÓ | Request `work_kind=build` chạm hạ tầng Archify → bắt buộc dựng và bind `spec-preview.html` trước duyệt spec |
| Kế hoạch chia pha + Chọn chế độ thực thi (`plan`, `mode`) | CÓ | Chia rõ 4 pha + tích hợp `tdq_setup.py` + phân rã task kiểm thử độc lập; user chọn `main` hoặc `subagent` |
| Triển khai TDD Red → Green (`implement`) | CÓ | Viết code sạch `<= 50` dòng/hàm, test thật từng bước, Pilot 2 luồng thật và đồng bộ `plugins/tdq-workflow-agy/` |
| Kiểm chứng `muc_qc=full` + Chrome DevTools (`qc`) | CÓ | DoD + trọn bộ unit test + `tdq_meta_gate.py` + hồi quy vùng chạm + ràng buộc kiến trúc + clean code + kiểm thử click `>= 4` tầng trên Chrome DevTools (không chạy independent `tdq-qc-tester` vì user chọn `full`, không chọn `ultra`) |
| Báo cáo + Archify HTML (`report`) | CÓ | Đo thực tế Trước → Sau (dung lượng, thời gian render, `0` false-dirty, `218+` tests xanh) và hỏi commit |

## Hỏi đáp

### Đợt 1 — Chốt quyết định triển khai & mức QC (2026-11-24T13:28+07:00)

- **Câu 1 (AST/Symbol parser):** A (Python `ast` + nhẹ JS/TS/Rust) / B (`tree-sitter`) → User chọn: **`1b và cho tree siíter vào thành dependecycuar tdq workflow để khi setup sẽ setup đủ`**.
- **Câu 2 (Tương thích ngược & vị trí Pilot):** A (Tương thích 100% + Pilot trực tiếp `hooks-and-gates` & `search-and-archify` 4 tầng vào `docs/architecture/index.html`) / B (Thư mục riêng) / C (Cả 6 view) → User chọn: **`2a`**.
- **Câu 3 (Bề mặt Spec/Report & `serve`):** A (Cả 2 bề mặt: `render --type drilldown` tự chứa + `serve` HTTP `127.0.0.1` + fallback `<script>` `file://`) / B (Chỉ `sync-master`) → User chọn: **`3a`**.
- **Câu 4 (Đồng bộ AGY plugin & `EXCLUDED_DIR_NAMES`):** A (Làm luôn cả hai: loại `target`/`.pytest_cache` + `build_portable.py --sinh-agy`) / B (Chỉ sửa mã nguồn gốc) → User chọn: **`4a`**.
- **Câu 5 (Mức QC `muc_qc`):** A (`full`) / B (`lite`) / C (`ultra`) → User chọn: **`5a`** (`muc_qc=full` đã ghi vào `state.json`).
- **Câu 6 (Bổ sung thêm):** A (Không, đủ rồi) / B (Có) → User chọn: **`6a`**.
