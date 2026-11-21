# Sổ bằng chứng kiểm toán & đối chiếu giả thuyết (`T2.1`)

- **Request:** `2026-11-21-1438-cai-thien-qc-test-e2e` · **Trạng thái:** Đã hợp nhất đủ 3 luồng kiểm chứng (`T1.1` audit TDQ + `T1.2` `terterarmy-cli` + `T1.3` chuẩn ngành) · **Tổng số bằng chứng:** `24` mục (`EV-001`–`EV-024`) khớp 1-1 với `evidence.jsonl`.

> **Tóm tắt dễ hiểu**
>
> Phản ánh của người dùng hoàn toàn có cơ sở định lượng: gần một nửa số hạng mục trong biên bản QC hiện tại (`48.8%`) kiểm tra giấy tờ/quy chuẩn nội bộ thay vì hành vi người dùng cuối (`12.2%`), trong khi bộ suite `tron-bo` mặc định chạy 1 luồng mất gần `20 phút` nhưng lại tắt kiểm tra `smoke` và `runtime` ở mức mặc định `full`. Tuy nhiên TDQ không nên xóa bỏ kỷ luật cốt lõi — giải pháp đúng là đẩy toàn bộ kiểm tra thủ tục xuống **Auto Meta-Gate chạy ngầm** và chuyển mặt tiền QC sang **hành vi E2E theo luồng vừa sửa** với thẻ QC ngắn gọn cho dev.

---

## 1. Bảng kết luận giả thuyết (`H1`–`H4`)

| Giả thuyết | Phán quyết | Độ tin cậy | Bằng chứng gốc & lập luận định lượng |
| :--- | :--- | :--- | :--- |
| **H1:** QC nặng tính hàn lâm, checklist giấy tờ che lấp trọng tâm cho dev | **Đúng** | `Verified` | `40/82` mục (`48.8%`) ở `8` biên bản QC gần nhất là `meta-compliance/doc`, gấp 4 lần mục `true E2E/runtime` (`10/82` = `12.2%`) `[EV-001]`. Biên bản TB `82.4` dòng (~`2,754` token), ép `QC-F4` 5 câu hỏi OOP SOLID trên repo chủ yếu viết hàm `[EV-002]`, `[EV-003]` và in `5` cột V2 `[unavailable]` gây nhiễu mắt `[EV-004]`. Ngay cả request chỉnh hiển thị (`0917`) cũng đánh `6/9` mục giấy tờ và `0` mục render người dùng `[EV-005]`. **Giới hạn công bằng:** Các request chạm nhị phân/runtime (`1230`, `0217`, `1034`, `1253`) vẫn có probe thật (`10/82`), nên TDQ không thiếu kiểm kỹ thuật, mà bị ngộp bởi lớp thủ tục trình bày quanh nó. |
| **H2:** Thiên về unit test mock-heavy, thiếu E2E thật, chạy chậm và dễ lọt lỗi tích hợp | **Đúng (nặng hơn dự đoán)** | `Verified` | Bảng `muc_qc` ở `qc.md` tắt sẵn `smoke test` và `runtime test` tại mức mặc định `full` `[EV-006]`, đồng thời ép `--workers 1` `[EV-007]`. Số đo thực từ `28` lượt `tron-bo` trong `.tdq-test.jsonl` cho trung vị **`1,190.11s` (~19.8 phút)** (gần 4 lần mức `~5 phút` dự đoán ban đầu), với **`6/28` (`21.4%`)** bị `INCOMPLETE` `[EV-008]`; pha `qc` chiếm trung vị **`1,518.0s` (~25.3 phút)** `[EV-009]`. Ca `v0.103.0` (`4,603 passed` trong `1,332.27s`) nhưng vỡ `8/8` subagent live `[EV-010]` chứng minh unit pass không thay được runtime smoke; sang `v0.103.1`, bật `--workers 6` rút xuống `314.31s` nhưng mất thêm `325.82s` `INCOMPLETE` do `.ruff_cache` thiếu trong `EXCLUDED_DIRS` `[EV-011]`. |
| **H3:** Thiếu lớp kịch bản người dùng plain-language & Bug Board tái hiện rõ ràng | **Đúng một phần** | `Verified` | TDQ **không thiếu hoàn toàn**: `vision-test-loop.md` đã có khung `Given - When - Then` 3 tầng và `tdq-browser-test` đã có quy trình 5 lớp Chrome DevTools MCP `[EV-012]`. **Nhưng lệch trọng tâm triển khai:** chỉ kích hoạt *"when the DoD reaches them"* nên `0/8` biên bản gần nhất chạy browser test `[EV-001]`, còn khuôn báo cáo vẫn là bảng CLI thô (`qc.md`) thay vì kịch bản 7–19 dòng đọc 10 giây hiểu ngay như `terterarmy-cli` `[EV-014]` hay quy trình Playwright Planner → Generator dùng Accessibility Tree Snapshot `[EV-017]`, `[EV-018]`. Ngoài ra nếu bỏ lint cho tài liệu như `BUG_BOARD.md` của `terterarmy-cli`, tài liệu hướng dẫn sẽ trượt khỏi code thực tế `[EV-016]`. |
| **H4:** Thiếu phân tầng tốc độ theo rủi ro / `Changed-Flow E2E Smoke` | **Đúng** | `Verified` | Trong `222` file `tests/test_*.py`, chỉ `15` file có `pytest.mark` và **`0` file gắn `@pytest.mark.smoke` / `e2e` / `slow`** `[EV-013]`. Lệnh `vung-cham` mới chỉ lọc unit test theo đồ thị AST (rất nhanh ở `7/10` lượt `5.47s`–`64.73s`, nhưng `3/10` lượt rơi về `full` tới `1,386.3s` vì `DATA_EXTS` thiếu `.html`) `[EV-013]`, chứ chưa có đường chạy `Changed-Flow E2E Smoke <60s` theo luồng hành vi hay Test Impact Analysis như chuẩn `Testmon` / `pytest -m smoke` `[EV-020]`, `[EV-021]`. |

---

## 2. Sổ cái bằng chứng chi tiết (`EV-001`–`EV-024`)

| Mã | Luồng | Giả thuyết | Khẳng định chính | Nguồn gốc (`path:line` / URL) | Độ tin cậy |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `EV-001` | `tdq-audit` | `H1` | 8 biên bản QC: 40/82 (`48.8%`) meta/doc vs 10/82 (`12.2%`) E2E/runtime; 0/8 dùng `tdq-browser-test` | [audit-tdq-qc-test.md](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/artifacts/2026-11-21-1438-cai-thien-qc-test-e2e/audit-tdq-qc-test.md#L42) | `Verified` |
| `EV-002` | `tdq-audit` | `H1` | `QC-F4` bắt trả lời 5 câu OOP SOLID mọi lần sửa source | [qc.md](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/skills/tdq-build/references/qc.md#L105-L108) | `Verified` |
| `EV-003` | `tdq-audit` | `H1` | 5 câu hỏi OOP (`SRP`, `OCP`, `LSP`, `ISP`, `DIP`) trong `clean-code.md` | [clean-code.md](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/skills/tdq-conventions/references/clean-code.md#L112-L121) | `Verified` |
| `EV-004` | `tdq-audit` | `H1` | `report-template.md` in 5 cột V2 `— [unavailable]` trên Antigravity 2.0 | [2026-11-21-1253-fix-subagent-tools-bump.md](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/reports/2026-11-21-1253-fix-subagent-tools-bump.md#L96-L105) | `Verified` |
| `EV-005` | `tdq-audit` | `H1` | Request sửa template UX (`0917`) tốn `1,327.59s` `tron-bo`, 0 check render người dùng | [2026-11-21-0917-mac-dinh-trinh-bay-ngan.md](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/qc/2026-11-21-0917-mac-dinh-trinh-bay-ngan.md#L13) | `Verified` |
| `EV-006` | `tdq-audit` | `H2` | Bảng `muc_qc` tắt `smoke` & `runtime test` ở `lite` và `full` | [qc.md](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/skills/tdq-build/references/qc.md#L36-L58) | `Verified` |
| `EV-007` | `tdq-audit` | `H2` | `qc.md:99` ép `--workers 1 --fresh --reuse off` cho `tron-bo` | [qc.md](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/skills/tdq-build/references/qc.md#L99) | `Verified` |
| `EV-008` | `tdq-audit` | `H2` | `28` lượt `tron-bo`: trung vị `1,190.11s` (~19.8p), `6/28` (`21.4%`) `INCOMPLETE` | [audit-tdq-qc-test.md](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/artifacts/2026-11-21-1438-cai-thien-qc-test-e2e/audit-tdq-qc-test.md#L51-L52) | `Verified` |
| `EV-009` | `tdq-audit` | `H2` | `17` request `full` trong `timing.jsonl`: trung vị `implement=2,998.5s`, `qc=1,518.0s` | [audit-tdq-qc-test.md](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/artifacts/2026-11-21-1438-cai-thien-qc-test-e2e/audit-tdq-qc-test.md#L48) | `Verified` |
| `EV-010` | `tdq-audit` | `H2` | Sự cố `v0.103.0`: `4,603 passed` (`1,332.27s`), vẫn vỡ `8/8` subagent live vì cache cũ | [2026-11-21-1034-bump-version-release-local.md](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/qc/2026-11-21-1034-bump-version-release-local.md#L12) | `Verified` |
| `EV-011` | `tdq-audit` | `H2` | `v0.103.1` dùng `--workers 6` (`314.31s`), bị `INCOMPLETE` `325.82s` do thiếu `.ruff_cache` | [tdq_test_receipt.py](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/scripts/tdq_test_receipt.py#L29-L30) | `Verified` |
| `EV-012` | `tdq-audit` | `H3` | TDQ đã có sẵn `Given-When-Then` 3 tầng và `tdq-browser-test` 5 lớp | [vision-test-loop.md](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/skills/tdq-build/references/vision-test-loop.md#L38-L62) | `Verified` |
| `EV-013` | `tdq-audit` | `H4` | `0/222` `tests/` có marker `smoke/e2e`; `DATA_EXTS` thiếu `.html` khiến `vung-cham` fallback full | [tdq_test.py](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/scripts/tdq_test.py#L104-L105) | `Verified` |
| `EV-014` | `terterarmy-cli` | `H3` | Mẫu test `terterarmy-cli` dài 7–19 dòng (1 Goal + act/assert) đọc 10 giây hiểu | [phan-tich-terterarmy-cli.md](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/artifacts/2026-11-21-1438-cai-thien-qc-test-e2e/phan-tich-terterarmy-cli.md#L33-L42) | `Verified` |
| `EV-015` | `terterarmy-cli` | `H3` | Debug trace 4 lớp và báo cáo lỗi 26 dòng gắn Severity + Repro steps tức thì | [phan-tich-terterarmy-cli.md](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/artifacts/2026-11-21-1438-cai-thien-qc-test-e2e/phan-tich-terterarmy-cli.md#L45-L62) | `Verified` |
| `EV-016` | `terterarmy-cli` | `H1` | `BUG_BOARD.md` trôi lệnh so với `bug_report.yml` chứng minh vẫn cần lint tài liệu ngầm | [BUG_BOARD.md](file:///C:/Users/admin/Documents/terterarmy-cli/docs/BUG_BOARD.md#L20) | `Verified` |
| `EV-017` | `industry-research` | `H3` | Playwright Test Agents tách Planner / Generator (`getByRole` sống) / Healer | https://playwright.dev/docs/test-agents | `Verified` |
| `EV-018` | `industry-research` | `H3` | Playwright MCP dùng `browser_snapshot` (Accessibility Tree + ref) tiết kiệm token | https://bug0.com/blog/playwright-mcp-changes-ai-testing-2026 | `Verified` |
| `EV-019` | `industry-research` | `H2` | Testing Trophy ưu tiên Integration ít mock + ít Critical E2E để tránh "cry wolf" | https://kentcdodds.com/blog/the-testing-trophy-and-testing-classifications | `Verified` |
| `EV-020` | `industry-research` | `H4` | Instawork dùng TIA (`pytest` + `Testmon`) giảm một nửa thời gian chạy test PR | https://engineering.instawork.com/test-impact-analysis-the-secret-to-faster-pytest-runs-e44021306603 | `Single-source` |
| `EV-021` | `industry-research` | `H4` | Giữ `smoke` suite tinh gọn fail-fast (`pytest -m smoke --tb=short`), loại check thừa | https://realpython.com/ref/software-engineering-glossary/smoke-test | `Verified` |
| `EV-022` | `industry-research` | `H1` | `obra/superpowers` dùng Iron Law + Gate 5 bước thay cho checklist thủ tục | https://github.com/obra/superpowers/blob/main/skills/verification-before-completion/SKILL.md | `Verified` |
| `EV-023` | `industry-research` | `H3` | `agent-browser` fail-closed click + đọc `console`/`errors` & Stagehand action cache | https://github.com/vercel-labs/agent-browser | `Verified` |
| `EV-024` | `tdq-audit` | `keep` | 5 chốt lõi TDQ cần giữ dưới dạng tự động hóa ngầm (`TDQ_LOG`, receipt, guard, Rust, AST) | [audit-tdq-qc-test.md](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/artifacts/2026-11-21-1438-cai-thien-qc-test-e2e/audit-tdq-qc-test.md#L100-L118) | `Verified` |

---

## 3. Quy chuẩn cốt lõi của TDQ CẦN GIỮ LẠI (chuyển vào tự động hóa ngầm)

1. **`TDQ_LOG=1/0` & nhận diện log theo phiên** (`EV-024`): Giữ ở tầng CLI/test parity để debug khi gãy; bỏ việc chép 40–50 dòng raw log vào biên bản QC cho dev đọc.
2. **Receipt SHA-256 + `bo_sot` + `source_before/after` trong `tdq_test.py` (`EV-024`)**: Giữ làm chốt chống báo PASS giả, nhưng vá ngay `.ruff_cache` (`EV-011`) và `.html` trong `DATA_EXTS` (`EV-013`).
3. **Runtime hooks `[TDQ:GIT]`, `[TDQ:STATE]`, `[TDQ:READONLY]` (`EV-024`)**: Giữ cơ chế chặn tự động ở runtime; chỉ hiển thị cảnh báo trong QC khi vi phạm, không viết thành mục đọc tay mỗi lượt.
4. **Rust `tdq-dispatch` parity + latency (`~14.8ms`) (`EV-024`)**: Chạy chọn lọc theo `Changed-Flow` khi diff chạm `hooks/` hoặc `tools/patches/`.
5. **Bán kính AST `vung-cham`, `ANTI-1..6`, & `doc_lint.py` (`EV-013`, `EV-016`, `EV-024`)**: Gom kiểm tra tĩnh tài liệu vào **Auto Meta-Gate** trả về đúng `1` dòng trạng thái, tránh lặp `doc drift` như trường hợp `BUG_BOARD.md`.
