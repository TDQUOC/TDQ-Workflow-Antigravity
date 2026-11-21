# Brief — Đánh giá & Đề xuất Cải thiện Quy trình QC và Kiểm thử E2E
Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

## Nguyên văn

> okay bây giơ tôi muốn check tiếp là hiện tại tôi thấy quá trình Qc và test nó mang tính hàn lâm quá khiến dev khó hiểu đôi lúc cảm thaasy nó test như không vào trọng tâm nữa, hyax giúp tôi check lại xem có đúng không? và resreach từ "C:\Users\admin\Documents\terterarmy-cli" hoặc các plugin, project lớn trên network và cho tôi đề xuất cải thiện qc nhanh hơn, chính xác hơn đảm bảo chất lượng và đúng trọng tâm e2e hơn và trình tôi báo cáo đề xuất

### Đọc hiểu ban đầu

- **Mục tiêu:** Kiểm chứng thực tế xem quy trình QC & kiểm thử hiện tại của TDQ-Workflow có đang quá hàn lâm, khó hiểu cho dev và lệch trọng tâm hay không; nghiên cứu tham chiếu từ `C:\Users\admin\Documents\terterarmy-cli` (đã xác nhận tồn tại trên máy, chứa `.claude-plugin`, `.codex-plugin`, `.cursor-plugin`, `skills`, `scripts`, `docs`, `mcp.json`) và các plugin/project lớn trên mạng; lập báo cáo đề xuất cải thiện QC nhanh hơn, chính xác hơn, giữ vững chất lượng và bám sát E2E hơn.
- **Phạm vi dự kiến:** `work_kind=investigate` (`loai_request=docs`) — chỉ kiểm tra, nghiên cứu, phân tích và xuất báo cáo đề xuất (chưa sửa mã nguồn sản phẩm trong đợt này trừ khi người dùng duyệt chuyển sang build).
- **Điểm cần làm rõ sau khi chọn pipeline:** phạm vi chấm điểm hiện trạng (toàn bộ skill/gate QC + biên bản QC gần đây hay tập trung vào một lớp cụ thể), mức độ ưu tiên cân bằng giữa tốc độ vs độ phủ E2E thực tế, và cấu trúc/độ sâu báo cáo đề xuất (có kèm lộ trình chia đợt áp dụng hay không).

## Hiểu & kiến thức

### Năng lực dùng được

Phân vân → DÙNG. Kiểm kê ngày 2026-11-21: `42` skill trên đĩa (`23` giữ theo bộ lọc + `19` ẩn), cộng skill built-in trong context. Không xóa bảng này kể cả khi không có dòng DÙNG nào.

| Skill | Nguồn | Phán quyết | Dùng ở đâu / Lý do loại |
|---|---|---|---|
| `tdq-intake` | `plugin:tdq-workflow / plugin:tdq-workflow-agy` | NỀN | kỹ năng nền của TDQ Workflow đang chạy |
| `tdq-spec` | `plugin:tdq-workflow / plugin:tdq-workflow-agy` | NỀN | kỹ năng nền của TDQ Workflow đang chạy |
| `tdq-plan` | `plugin:tdq-workflow / plugin:tdq-workflow-agy` | NỀN | kỹ năng nền của TDQ Workflow đang chạy |
| `tdq-build` | `plugin:tdq-workflow / plugin:tdq-workflow-agy` | NỀN | kỹ năng nền của TDQ Workflow đang chạy |
| `tdq-conventions` | `plugin:tdq-workflow / plugin:tdq-workflow-agy` | NỀN | kỹ năng nền của TDQ Workflow đang chạy |
| `tdq-setup` | `plugin:tdq-workflow / plugin:tdq-workflow-agy` | NỀN | kỹ năng nền của TDQ Workflow đang chạy |
| `tdq-status` | `plugin:tdq-workflow / plugin:tdq-workflow-agy` | NỀN | kỹ năng nền của TDQ Workflow đang chạy |
| `tdq-check-status` | `plugin:tdq-workflow / plugin:tdq-workflow-agy` | NỀN | kỹ năng nền của TDQ Workflow đang chạy |
| `tdq-checkportable` | `plugin:tdq-workflow-agy` | NỀN | kỹ năng nền của TDQ Workflow đang chạy |
| `tdq-lean` | `plugin:tdq-workflow / plugin:tdq-workflow-agy` | NỀN | kỹ năng nền của TDQ Workflow đang chạy |
| `tdq-browser-test` | `plugin:tdq-workflow / plugin:tdq-workflow-agy` | NỀN | kỹ năng nền của TDQ Workflow đang chạy |
| `tdq-browser-research` | `plugin:tdq-workflow / plugin:tdq-workflow-agy` | NỀN | kỹ năng nền của TDQ Workflow đang chạy |
| Đã xét 19 skill khác trên đĩa và các skill built-in trong context | user/plugin/built-in | KHÔNG | khác lĩnh vực |

### Bề mặt khảo sát nông (Entry Points & Hiện trạng)

- **Nội bộ TDQ QC & Test:** `skills/tdq-build/references/qc.md` (`190` dòng), `skills/tdq-build/references/qc-vong-fix.md` (`25` dòng), `skills/tdq-build/references/report-template.md` (`165` dòng), `skills/tdq-browser-test/SKILL.md` (`77` dòng), `agents/tdq-qc-tester.md` (`31` dòng), `scripts/tdq_test.py` (`1.533` dòng) và `8` biên bản QC gần nhất tại `docs/tdq/qc/*.md`.
- **Tham chiếu cục bộ `C:\Users\admin\Documents\terterarmy-cli`:** Dự án `TesterArmy CLI` (`testerarmy` / `ta` — *"Agents that test your app like real users"*), gồm `33` tệp ngoài `.git/`: `README.md`, `skills/testerarmy-cli/SKILL.md`, `skills/testerarmy-cli/references/reporting-template.md`, `examples/TESTER.md`, `examples/prompts/ad-hoc-regression.md`, `examples/tests/01-landing-page.md`, `02-auth-smoke.md`, `03-project-create.md`, `docs/BUG_BOARD.md`, và `.github/ISSUE_TEMPLATE/{bug_report,regression_report}.yml`.
- **Môi trường tìm kiếm:** `tdq_lsp.py check` đạt `5/8` bậc, `smoke 3/3 tầng trả lời được`, `tavily-primary` và `tdq-workflow-agy_lsp` khả dụng.

### 4 Giả thuyết kiểm chứng (Candidate Hypotheses H1–H4)

- **H1 (Hàn lâm hóa & nặng nghi thức):** QC hiện tập trung nhiều vào tự kiểm meta-compliance (`Q1..Qn`, `QC-F1..F4`, `5` câu SOLID, `bo_sot`, `details_complete`, `receipt sha256`, `doc_lint`) khiến dev khó nắm nhanh hành vi thực tế của tính năng.
- **H2 (Unit-heavy, E2E-light):** Mức mặc định `muc_qc=full` chạy trọn `tron-bo` (`~4.641` cases / `~5` phút) nhưng mặc định không chạy runtime/E2E test (chỉ bật ở `ultra`), dẫn tới vừa tốn thời gian vừa có nguy cơ lọt lỗi tích hợp thực tế (như sự cố `v0.103.0` pass `4.603` unit/integration tests nhưng vỡ runtime khi gọi `invoke_subagent`).
- **H3 (Thiếu tầng kịch bản người dùng plain-language & triage lặp lại):** Các công cụ QA/E2E thực dụng (`terterarmy-cli`, Playwright MCP, Testing Trophy / Risk-Based E2E) tách rõ kịch bản người dùng thực tế dễ đọc, báo cáo lỗi tái hiện từng bước (`BUG_BOARD`, `reporting-template`) và kiểm hồi quy theo luồng thay đổi.
- **H4 (Thiếu phân tầng tốc độ theo rủi ro):** Chưa có tầng **Changed-Flow E2E Smoke** chạy nhanh trước full regression, khiến vòng phản hồi cho dev dài mà độ tin cậy E2E chưa tăng tương xứng.

### Ghi chú vòng phạm vi

Áp dụng `investigate-mode.md` (giữ scoping nông trước pha `implement`, chưa đọc sâu toàn bộ tài liệu hay gọi web search ở pha `analyze`), gộp câu hỏi phạm vi kiểm chứng, mức khai thác `terterarmy-cli`/nguồn ngoài, cấu trúc báo cáo đề xuất và mức `muc_qc` (bước 5c) vào **1 vòng phỏng vấn duy nhất**.

### Quyết định đã chốt

- **Phạm vi kiểm tra (`1a`):** Kiểm tra toàn diện cả `3` lớp của TDQ (`tài liệu/skill QC` + `biên bản QC gần đây` + `hạ tầng chạy test tdq_test.py và E2E`).
- **Nghiên cứu tham chiếu (`2a`):** Khai thác chi tiết cấu trúc/mẫu tại `C:\Users\admin\Documents\terterarmy-cli`, kết hợp nghiên cứu mạng `4`–`6` plugin/project QA & E2E lớn (`Playwright MCP / Playwright Agents`, `Testing Trophy`, `Risk-Based E2E`, AI QA plugins) và đề xuất phương án tích hợp nếu phù hợp.
- **Đầu ra báo cáo (`3a`):** Báo cáo đề xuất `4` phần đầy đủ (chẩn đoán thực chứng có/không hàn lâm, đối chiếu TDQ vs `terterarmy-cli` & chuẩn ngành, thiết kế mô hình QC/E2E mới dễ hiểu với dev, lộ trình áp dụng chia đợt kèm KPI) + Archify HTML — **giữ Zero-Code-Touch**, chưa sửa code sản phẩm trong request này.
- **Mức QC (`4a`):** `muc_qc = full` (`QC-I1`, `QC-I2`, `QC-I4` + Zero-Code-Touch, không chạy Red-Team `QC-I3` của mức `ultra`).
- **Bổ sung (`5a`):** Không bổ sung thêm, chốt kiến thức sang pha `spec`.

### Lộ trình

| Bước/phase | Chạy? | Vì sao |
|---|---|---|
| Khảo sát nội bộ 3 lớp TDQ QC/Test (pha `implement`) | CÓ | Kiểm chứng thực tế `H1`–`H4` trên `qc.md`, biên bản `docs/tdq/qc/*.md`, `timing.jsonl` và `tdq_test.py` |
| Mổ xẻ cục bộ `C:\Users\admin\Documents\terterarmy-cli` | CÓ | Rút pattern kịch bản plain-language, `TESTER.md`, `BUG_BOARD.md`, `reporting-template.md` |
| Research mạng `4`–`6` framework/plugin lớn (`tavily-primary`) | CÓ | Đối chiếu chuẩn ngành (`Playwright Agents/MCP`, `Testing Trophy`, `Risk-Based E2E`, AI QA plugins) |
| Archify preview ở pha `spec` | BỎ | Miễn theo `investigate-mode.md`; chỉ render Archify HTML `1` lần ở pha `report` sau khi có kết quả thực tế |
| Vòng Red-Team phản biện riêng (`QC-I3`) | BỎ | Người dùng chọn `muc_qc=full` (`4a`), không chạy vòng Red-Team bổ sung của mức `ultra` |
| QC bằng chứng (`QC-I1`, `QC-I2`, `QC-I4` + Zero-Code-Touch) | CÓ | Xác minh `100%` `[EV-xxx]`, `path:line`, nguồn web trích xuất và `0` sửa code ngoài `docs/tdq/` |

## Hỏi đáp

### Vòng 1 (`2026-11-21 14:46`)

- **Trả lời nguyên văn của user:** `1a 2a 3a 4a 5a`
- **Nội dung đã chốt:**
  1. Phạm vi kiểm chứng TDQ → `A`: Toàn diện cả `3` lớp (`tài liệu/skill QC` + `biên bản QC gần đây` + `hạ tầng tdq_test.py / E2E`).
  2. Mức khai thác nguồn tham chiếu → `A`: Rút pattern từ `C:\Users\admin\Documents\terterarmy-cli` + đối chiếu `4`–`6` plugin/project lớn trên mạng + nêu tùy chọn tích hợp.
  3. Cấu trúc & độ sâu báo cáo đề xuất → `A`: Báo cáo đầy đủ `4` phần + lộ trình KPI, giữ nguyên chưa sửa code (`work_kind=investigate`).
  4. Mức QC → `A`: `full` (`DoD` + đối chiếu chéo toàn bộ trích dẫn `path:line` & nguồn web qua `QC-I1`, `QC-I2`, `QC-I4`; không chạy Red-Team riêng).
  5. Bổ sung thêm → `A`: Không, đủ rồi — làm tiếp đi.

