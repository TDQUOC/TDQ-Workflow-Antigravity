# BRIEF — Nâng cấp QC và Tester TDQ theo 3 Wave (Dev-First, E2E-First)

Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

## Nguyên văn

> `commmit và mở request handle cả 3 wave update cho tdq-workflow để có tester và qc phase chuẩn và tối ưu hơn`

### Đọc hiểu bước đầu

- **Mục tiêu:** Triển khai đồng bộ cả `3` đợt nâng cấp (`Wave 1`, `Wave 2`, `Wave 3`) từ báo cáo đề xuất vừa nghiệm thu để biến quy trình QC và kiểm thử của `tdq-workflow` thành mô hình **Dev-First, E2E-First** — nhanh hơn, ít thủ tục chữ nghĩa, đọc `10` giây hiểu ngay và bắt đúng lỗi tích hợp/E2E sống.
- **Tài liệu đầu vào tham chiếu:**
  - [Báo cáo đề xuất 4 phần](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/reports/2026-11-21-1438-cai-thien-qc-test-e2e.md)
  - [Sổ cái bằng chứng EV-001–EV-024](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/artifacts/2026-11-21-1438-cai-thien-qc-test-e2e/evidence-log.md)
  - [Kiểm toán nội bộ TDQ T1.1](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/artifacts/2026-11-21-1438-cai-thien-qc-test-e2e/audit-tdq-qc-test.md)
  - [Phân tích đối chuẩn terterarmy-cli T1.2](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/artifacts/2026-11-21-1438-cai-thien-qc-test-e2e/phan-tich-terterarmy-cli.md)
- **Phạm vi dự kiến cả `3` Wave:**
  1. **Wave 1 (Quick Wins — Runner, Tốc độ & Dev Behavior QC Card):** Vá `DATA_EXTS` (thêm `.html`/`.htm` trong `scripts/tdq_test.py`) và `EXCLUDED_DIRS` (thêm `.ruff_cache` trong `scripts/tdq_test_receipt.py`); đổi mặc định `qc.md` từ `--workers 1` sang `--workers auto` (giới hạn an toàn); mở mặc định `smoke test` ở `muc_qc = full`; áp dụng `Dev Behavior QC Card` cho mặt tiền báo cáo QC (`qc.md`, `agents/tdq-qc-tester.md`); ẩn `5` cột V2 `[unavailable]` ở `tdq_timing.py`/`report-template.md` khi host chưa cấp nguồn; giới hạn `QC-F4` OOP SOLID chỉ chạy khi diff thực sự tạo/đổi cấu trúc OOP.
  2. **Wave 2 (Changed-Flow E2E Smoke `<60s` & Auto Meta-Gate):** Phân tầng `tests/` với `@pytest.mark.smoke` và `@pytest.mark.e2e` cho các luồng sống còn (build bundle, frontmatter/live probe subagent, hooks Rust `tdq-dispatch`, CLI E2E); bổ sung đường chạy `smoke-e2e --changed` ánh xạ vùng code sửa sang luồng E2E; gom `doc_lint` + `token_budget` + `i18n_check` + guard thành `1` lệnh **Auto Meta-Gate** kết hợp cổng bằng chứng `5` bước kiểu `obra/superpowers`.
  3. **Wave 3 (Browser Accessibility Snapshot, Plain-Language Scenarios & Opt-in Adapter):** Chuyển mặc định `skills/tdq-browser-test/SKILL.md` và `vision-test-loop.md` ưu tiên **Accessibility Tree Snapshot (`ref`) + kiểm `console`/`errors` fail-closed** thay vì ép pixel visual diff cho mọi case; thêm mẫu kịch bản `docs/tdq/scenarios/*.md` (`7–19` dòng) + `Live Bug Board` có rule `doc_lint` chống trôi lệnh CLI; mở cổng adapter opt-in cho Playwright MCP / TesterArmy CLI với các dự án ngoài.
- **Chốt lõi TDQ bắt buộc giữ nguyên (chuyển sang chạy ngầm):** `TDQ_LOG=1/0`, khóa toàn vẹn SHA-256 + `bo_sot` của `tdq_test.py`, runtime hooks `[TDQ:GIT]` / `[TDQ:STATE]` / `[TDQ:READONLY]`, Rust parity/latency, và AST `vung-cham` + `doc_lint.py`.
- **Điểm sẽ làm rõ ở pha phân tích (sau khi chọn pipeline):** Phạm vi build/cài đồng bộ plugin `tdq-workflow-agy` local (`~/.gemini/config/plugins/`), chiến lược sinh test E2E không flaky trên Windows, ngưỡng song song an toàn cho `--workers auto`, và mức độ ưu tiên/tách batch triển khai.

## Hiểu & kiến thức

### Năng lực dùng được

Phân vân → DÙNG. Kiểm kê ngày 2026-11-21: `42` skill trên đĩa (`23` khớp từ khóa `qc test e2e browser smoke pytest`, `19` ẩn khác lĩnh vực từ `skill_inventory.py`), cộng skill built-in trong context. Không xóa bảng này kể cả khi không có dòng DÙNG nào.

| Skill | Nguồn | Phán quyết | Dùng ở đâu / Lý do loại |
|---|---|---|---|
| `tdq-intake`, `tdq-spec`, `tdq-plan`, `tdq-build`, `tdq-conventions`, `tdq-setup`, `tdq-status`, `tdq-check-status`, `tdq-lean` | `plugin:tdq-workflow-agy` / `project` | NỀN | Luồng điều phối lõi đang chạy |
| `tdq-browser-test` | `project` / `plugin:tdq-workflow-agy` | DÙNG | Wave 3: đổi mặc định sang Accessibility Tree Snapshot + kiểm E2E giao diện HTML |
| `chrome-devtools` | `plugin` / `built-in` | DÙNG | Hỗ trợ kiểm thử E2E trình duyệt sống (`snapshot`, `console`, `network`) ở Wave 3 |
| Đã xét `25+` skill khác (`19` ẩn + built-in) | user / plugin / built-in | KHÔNG | khác lĩnh vực |

### Khảo sát mã nguồn `3` chiều (Triangulation)

| Vùng file chạm | Phát hiện qua lớp nào (Grep / LSP / Graphify) | Tác động & quan hệ |
|---|---|---|
| `scripts/tdq_test.py`, `scripts/tdq_test_receipt.py` | Grep (`DATA_EXTS`, `EXCLUDED_DIRS`, `_worker_count`), LSP (`_worker_count` → `3` refs), Graphify (`tdq_runtime_bench.py:L28`) | Chứa `DATA_EXTS` (thiếu `.html`/`.htm`), `EXCLUDED_DIRS` (thiếu `.ruff_cache`), `_worker_count` mặc định `1` và đường chạy `vung-cham`/`tron-bo`. Bắt buộc giữ nguyên receipt SHA-256 + `bo_sot` |
| `scripts/tdq_timing.py` | Grep (`bang_markdown`), LSP (`bang_markdown` → `4` refs: `2` scripts + `2` tests), Graphify (`token_audit.py:L43`, `step_audit.py:L38`) | Render bảng V2 in `5` cột `[unavailable]` trên Antigravity 2.0; sửa markdown cần giữ nguyên JSON v2 và kiểm chéo `test_timing.py` + `test_phase1_contract.py` |
| `scripts/doc_lint.py`, `scripts/tdq_finish.py`, `scripts/token_budget.py`, `scripts/i18n_check.py` | Grep (`R1..R15`), Graphify (`tdq_state.py:L2663`, `doc_dup.py`, `tdq_test.py:L88`, `plugins/tdq-workflow-agy/scripts/*`) | Khung đóng gói **Auto Meta-Gate** (`1` dòng PASS/FAIL), giữ `token-budget.json` SHA-256 (`R13`), quy tắc English ở `skills/`/`agents/` (`i18n_check.py`) và thêm rule kiểm Bug Board/Scenario |
| `skills/tdq-build/references/{qc.md,report-template.md,vision-test-loop.md}`, `skills/tdq-browser-test/SKILL.md`, `skills/tdq-conventions/references/clean-code.md`, `agents/tdq-qc-tester.md` | Grep + đọc trực tiếp | Sửa `muc_qc` & `--workers`, khuôn `Dev Behavior QC Card`, phạm vi `QC-F4`, mặc định Accessibility Tree Snapshot ở `tdq-browser-test`, mẫu kịch bản `7–19` dòng & adapter opt-in |
| `tests/test_muc_qc_qc_md.py`, `tests/test_timing.py`, `tests/test_tdq_test*.py`, `tests/test_agent_frontmatter.py`, `tests/test_devtool_mcp_integration.py`, `tests/test_token_budget*.py`, `tests/test_i18n_check.py` | Grep (`222` files, `15` marked, `0` smoke/e2e) + LSP (`tests/test_phase1_contract.py:180`, `tests/test_timing.py:627,650`) | `test_muc_qc_qc_md.py:62-69` khóa cứng `full` `runtime test = KHÔNG` (`2026-09-23`); toàn bộ `222` tệp test chưa có `@pytest.mark.smoke` / `e2e` |
| `tools/build_agy_plugin.py`, `tools/patches/skills_and_agents.py`, `plugins/tdq-workflow-agy/` | Grep (`qc.md`, `tdq-qc-tester.md`) + `tdq_lsp` inventory | Bắt buộc tính toán việc đồng bộ bản build `plugins/tdq-workflow-agy/` và khóa `token-budget.json` khi đổi `skills/` / `agents/` / `scripts/` |

### Ràng buộc kiến trúc (từ `docs/kien-truc.md`)

- **Phân tầng `3` ngôn ngữ (`2026-08-22`):** Toàn bộ nội dung luật trong `skills/`, `agents/`, và docstring/chuỗi máy của `scripts/`/`hooks/` viết **TIẾNG ANH** (hoặc bọc `i18n-allow` cho chuỗi Việt cố định) theo kiểm soát của `scripts/i18n_check.py`.
- **Luật import một chiều:** `hooks/` gọi `scripts/`; `scripts/` tuyệt đối không import `hooks/`. Module Python sản phẩm mới phải đặt trong `scripts/`.
- **Khóa ngân sách token (`R13`) & giới hạn dòng (`R6`):** Mọi thay đổi trong `skills/` hoặc `agents/` phải đồng bộ `token-budget.json` qua cơ chế chuẩn, không vượt trần dòng/token của skill.
- **Hai cổng `tron-bo` (`2026-10-03`) & quyết định `muc_qc` (`2026-09-23`):** Giữ cơ chế `vung-cham` + `bo_sot`; mọi điều chỉnh bảng `muc_qc` phải xử lý minh bạch khóa test tại `tests/test_muc_qc_qc_md.py`.

### Ghi chú phạm vi nghiên cứu & vòng phỏng vấn

- **Bỏ qua bước `B2` (research ngoài) và vòng Tier 1 Scope Round:** Sử dụng trực tiếp dữ liệu điều tra vừa hoàn tất cùng ngày (`2026-11-21`) gồm `22` URL chuẩn ngành ([research/2026-11-21-1438-cai-thien-qc-test-e2e.md](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/research/2026-11-21-1438-cai-thien-qc-test-e2e.md)), `33` tệp `terterarmy-cli`, và `24` bằng chứng `[EV-001]`–`[EV-024]`; phạm vi cả `3` Wave đã được người dùng chỉ định trực tiếp khi mở request.

### Quyết định đã chốt

- **Bảng `muc_qc` (`1a`):** Mức `full` mở `smoke test = CÓ` (`Changed-Flow E2E Smoke <60s`), vẫn giữ `runtime test = KHÔNG` (`120s` cap) và `tdq-qc-tester = KHÔNG` ở `full` (chỉ bật ở `ultra`). Cập nhật tường minh ràng buộc trong `tests/test_muc_qc_qc_md.py`.
- **`QC-F4` SOLID & Telemetry V2 (`2a`):** Chỉ áp dụng `5` câu SOLID OOP khi diff tạo/đổi class hoặc tầng kiến trúc; tác vụ script thường kiểm `3` tiêu chí thực dụng (`fail-closed`, không lặp logic, hàm gọn). Ở `scripts/tdq_timing.py`, bảng markdown tự ẩn `5` cột `[unavailable]` khi cả `5` cột đều không khả dụng trên tất cả các dòng, giữ nguyên JSON schema v2 và cập nhật `tests/test_timing.py`.
- **Song song hóa `--workers auto` (`3a`):** Bổ sung `--workers auto` (trần an toàn `min(6, cpu_count)`) vào `scripts/tdq_test.py` và đổi lệnh chuẩn ở `qc.md` sang `--workers auto`; giữ mặc định nội bộ `1` khi không truyền cờ để tương thích 100% test cũ.
- **Đóng gói plugin & Bump version (`4a bump ver luôn`):** Bump phiên bản từ `0.103.1` → `0.104.0` đồng bộ trên manifests, `Cargo.toml`, `README.md`, `UPSTREAM-TRACE.md`, `tools/`, `CHANGELOG.md` (`<= 500` dòng), đồng bộ `token-budget.json`, build lại `plugins/tdq-workflow-agy/` và chạy `agy plugin validate --strict` (không cài đè `~/.gemini/`).
- **Mức QC cho request này (`5a`, `6a`):** `muc_qc = full`; không bổ sung thêm ngoài `3` Wave + bump version `0.104.0`.

### Lộ trình

| Bước/phase | Chạy? | Vì sao |
|---|---|---|
| Research ngoài | BỎ | Đã hoàn tất cùng ngày ở `2026-11-21-1438-cai-thien-qc-test-e2e` (`22` URL + `33` tệp `terterarmy-cli`) |
| Interview | CÓ | Đã chốt đủ `6` câu trong `1` vòng (`1a 2a 3a 4a bump ver luôn 5a 6a`) |
| Spec & Archify BA | CÓ | Khóa hợp đồng `M1`–`M5`, ràng buộc R14 (`Đo trước` / `Dự phòng`), và sơ đồ Trước/Sau |
| Plan (`subagent`/wave) | CÓ | Chia `5` module `M1`–`M5` theo `3` Wave triển khai không chồng lấn vùng file |
| Implement | CÓ | Cài đặt `Wave 1` → `Wave 2` → `Wave 3` + bump `0.104.0` + build `plugins/tdq-workflow-agy/` |
| QC mức `full` | CÓ | `DoD` (`Q1`–`Q8`) + `tron-bo --workers auto` + `smoke-e2e --changed` + `agy plugin validate --strict` |
| QC độc lập (agent) | BỎ | Theo mức `muc_qc = full` đã chốt (`5a`: giữ agent `tdq-qc-tester` riêng cho `ultra`) |
| Report & Archify HTML | CÓ | Xuất báo cáo `4` phần + Archify HTML (`Tailscale HTTP 200`), chờ user duyệt commit/merge về `dev` |

## Hỏi đáp

- **Câu 1 (Cập nhật `muc_qc`):** Chọn **`A` (`1a`)** — Mở `smoke test = CÓ` (`Changed-Flow E2E Smoke <60s`) ở `full`, giữ `runtime test` nặng và `tdq-qc-tester` độc lập ở `ultra`.
- **Câu 2 (`QC-F4` & `5` cột `[unavailable]`):** Chọn **`A` (`2a`)** — Giới hạn `5` câu SOLID OOP cho diff tạo/đổi class hoặc tầng; ẩn `5` cột `[unavailable]` trên bảng markdown `tdq_timing.py show` khi vắng nguồn dữ liệu, giữ nguyên JSON v2.
- **Câu 3 (`--workers auto`):** Chọn **`A` (`3a`)** — Bổ sung `--workers auto` (`min(6, cpu_count)`) và dùng trong `qc.md`, giữ mặc định nội bộ `1`.
- **Câu 4 (Build plugin & phiên bản):** Chọn **`A` + bổ sung (`4a bump ver luôn`)** — Bump `0.103.1` → `0.104.0`, đồng bộ `token-budget.json`, build `plugins/tdq-workflow-agy/` và chạy `agy plugin validate --strict` (chưa cài đè `~/.gemini/`).
- **Câu 5 (`muc_qc` của request này):** Chọn **`A` (`5a`)** — `full`.
- **Câu 6 (Bổ sung thêm):** Chọn **`A` (`6a`)** — Không, đủ rồi — làm tiếp đi.
- **Nguyên văn phản hồi của user:** `1a 2a 3a 4a bump ver luôn 5a 6a`
