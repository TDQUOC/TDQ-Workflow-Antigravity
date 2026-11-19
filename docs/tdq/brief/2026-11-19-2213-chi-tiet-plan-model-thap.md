# Brief: Phân tích độ chi tiết của plan cho model tier thấp và đề xuất cải thiện TDQ Workflow

Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

## Nguyên văn

> bây giờ mở request fanout sub agent để phân tích nhận định sau: tôi thấy hiện tại plan đang chưa cụ thể, có chỉ sửa gì,làm gì nhưng không ghi rõ là ví dụ script đó chỗ đó cần làm gì ở đó, thuật toán công nghệ ứng dụng thế nào, cho từng task, có thể gây hiệu quả thấp ở model tỉer thấp. hãy nhận định xem có đúng không? và cho tôi đề xuất cải thiện tdq-workflow để trong plan từng task có chi tiết mô tả, thuật toán, công nghệ.... để dù chạy bằng model tier thấp vẫn làm tốt và có chất lượng cao, do plan đã rất chi tiết và mô tả rõ làm từ gì thành gì, sẽ làm gì trong từng task, và expect sau làm sẽ được gì ở task đó. hãy phân tích thiệt kĩ và tái phân tích thêm 1 round tìm những nhược điểm và cải thiện r tình bày đề xuất với tôi

### Đọc hiểu ban đầu

- **Mục tiêu**: Kiểm chứng nhận định về việc `plan` hiện tại của `tdq-workflow` chưa đủ cụ thể (thiếu chi tiết sửa gì ở đâu trong script, thuật toán/công nghệ áp dụng, chuyển đổi trước → sau và kỳ vọng đầu ra của từng task) gây giảm hiệu quả khi chạy trên model tier thấp; đề xuất phương án cải thiện `tdq-workflow`, sau đó tái phân tích thêm 1 vòng phản biện (Round 2) để tìm nhược điểm, trade-off và tinh chỉnh đề xuất cuối cùng.
- **Đầu ra kỳ vọng**: Báo cáo phân tích kiểm chứng nhận định có bằng chứng thực nghiệm + tài liệu đề xuất cải thiện `tdq-workflow` đã qua 2 vòng phân tích & phản biện chéo (+ Archify HTML), dừng ở tài liệu thiết kế `docs` (chưa sửa code/skill).

## Hiểu & kiến thức

### Năng lực dùng được

Phân vân → DÙNG. Kiểm kê ngày 2026-11-19: `42` skill trên đĩa (`23` hiển thị qua `--loc`, `19` ẩn khác lĩnh vực), cộng skill built-in trong context. Không xoá bảng này kể cả khi không có dòng DÙNG nào.

| Skill | Nguồn | Phán quyết | Dùng ở đâu / Lý do loại |
|---|---|---|---|
| `tdq-intake`, `tdq-spec`, `tdq-plan`, `tdq-build`, `tdq-conventions`, `tdq-setup`, `tdq-status`, `tdq-check-status`, `tdq-lean`, `tdq-checkportable` | `plugin:tdq-workflow-agy` | NỀN | Khung quy trình đang chạy |
| `tdq-browser-research`, `tdq-browser-test` | `plugin:tdq-workflow-agy` | KHÔNG | khác lĩnh vực |
| Đã xét 55 skill khác (19 ẩn trên đĩa + 36 built-in/plugin ngoài trong context) | user/plugin/built-in | KHÔNG | khác lĩnh vực |

### Bảng đối chiếu vùng chạm (Tam giác khảo sát 3 chiều)

| Vùng file chạm / khảo sát | Phát hiện qua lớp nào (Grep / LSP / Graphify) | Tác động & quan hệ |
|---|---|---|
| `skills/tdq-plan/SKILL.md` (`121/121` dòng), `skills/tdq-plan/references/plan-template*.md`, `skills/tdq-spec/references/spec-template*.md`, `skills/tdq-build/references/team-mode.md`, `agents/tdq-implementer.md`, `agents/tdq-reviewer.md` | Grep + Đọc trực tiếp (Subagent 1) | Chứa toàn bộ luật viết plan, Self-Contained Task Block 9 trường (đã thêm ngày `2026-11-11`), mẫu ghép packet 9 trường vs 7 trường bị lệch, và `SKILL.md` hết dư địa dòng (`121/121`). |
| `scripts/doc_lint.py` (`rule_r15:526`, `pair:602`, `rule_r12:694`, `lint_file:851`, `SKILL_LINE_LIMITS:63`) | LSP (`list_symbols`, `find_references` — `3` refs cho `rule_r15`, `8` refs cho `lint_file`) + Graphify (`Doc`, `lint_file()`, `rule_r15()`) + Grep | Cưỡng chế R8/R12/R13/R15; phát hiện R15 chỉ kiểm 1 từ khóa (`logic`), không chạy ở `--pair`, không chặn ở `approve plan`, và cắt cụt task ở cột 0. |
| `scripts/tdq_team.py` (`Task:128`, `doc_plan:148-235`, `quyet_dinh_task:383-416`) | Graphify (`Task`, `doc_plan()`, `lenh_mo()`, `lenh_hop()`) + Grep (Subagent 3) | **Bug nghiêm trọng (`:176-179`)**: quét `_PATH` trên mọi dòng `t.text` thay vì riêng `Chạm:` → ghi đường dẫn tham chiếu trong đặc tả chi tiết sẽ làm nhiễm `vung_file`, nổ `HOT FILE` giả và phá song song (`file-luat`). |
| `hooks/scripts/edit_gate.py`, `stop_gate.py`, `hooks/rust/tdq-dispatch/src/storage.rs:307`, `tools/patches/skills_and_agents.py:45-50`, `plugins/tdq-workflow-agy/hooks/scripts/subagent_dispatch_gate.py` | Graphify (`edit_gate.py`, `_common.py`) + Grep (Subagent 1 & 3) | Khóa bất biến regex `- [ ] **Tx.y**` ở cột 0; AGY plugin ép `tdq-implementer` chạy **`model: flash` không có tool LSP/grep**; `subagent_dispatch_gate.py` mới chỉ kiểm 5 nhãn tối thiểu. |
| `docs/tdq/plan/*.md` (`236` file, `2,699` task) & `docs/tdq/spec/*.md` (`319` file) | Quét thực nghiệm toàn bộ corpus + chấm điểm 7 chiều trên `12` plan / `48` task (Subagent 2) | Bằng chứng thực nghiệm trực tiếp kiểm chứng nhận định người dùng trước và sau mốc `2026-11-11`. |
| `docs/tdq/research/2026-11-19-2213-chi-tiet-plan-model-thap.md` | Tavily MCP (`tavily_search`, Subagent 4) | Đối chiếu khoa học: Skeleton Coding (`arXiv:2610.38214v1`), Aider Architect/Editor, IFScale (`arXiv:2507.11538v1`), Context Rot (Chroma 2025), Böckeler & Heym (`1,133` commits). |

### Phát hiện cốt lõi từ khảo sát nền

1. **Nhận định của bạn ĐÚNG — ngay cả sau khi TDQ từng thử vá ở mốc `2026-11-11` (`2026-11-11-0230-task-block-va-model-tier-thap.md`):**
   - Toàn kho `236` plan (`2,699` task), chấm sâu `48` task mẫu theo 7 tiêu chí sẵn sàng cho model tier thấp (`>= 12/14`): trước `11-11` đạt `0%` (`5.08/14`), sau `11-11` tăng lên nhưng **vẫn chỉ `20.8%` (`5/24` task)** (và `3/5` task đạt chuẩn đến từ duy nhất 1 plan ngoại lệ `2026-11-16-1953`).
   - 3 chiều yếu nhất ngay cả sau R15: **(b) Trước → Sau ở mức từng task** (`58.3%` vắng mặt hoàn toàn, toàn bộ `117` task sau `11-11` chỉ có `0.9%` ghi rõ), **(g) Test Oracle cụ thể `input → assert`** (`37.5%` vắng mặt), và **(c) Thuật toán / nhánh rẽ tường minh** (`25%` đạt chuẩn). Ngoài ra `60.9%` task code sau `11-11` thiếu số dòng/neo cụ thể, `76.5%` task sửa QC (`13/17`) là 1 dòng trần, và `100%` quick-lane bỏ qua Task Block.
   - **Nghịch lý phát hiện:** tỉ lệ **mega-task chạm `>= 4` file tăng gấp `2.8×`** sau R15 (`4.9% → 13.7%`), vì mẫu 9 trường rườm rà khiến planner nén 8–10 file vào 1 task (`11-19-1632:T2.1`, `11-18-1814:T2.1`) → model tier thấp bị drop ngầm.
   - **Tác động cực lớn riêng trên Antigravity:** `tools/patches/skills_and_agents.py:45-50` đang ép `tdq-implementer` chạy **`model: flash` và tước sạch tool LSP/Grep** — nếu plan không tự đủ, subagent `flash` buộc phải mò bằng `read_file`/`run_command` hoặc bịa schema (sự cố thật `11-19-0046` → mất `14/22` mã cổng và `2/6` sự kiện).
2. **Cảnh báo phản biện sớm (Trade-off khoa học — tránh "chữa lợn lành thành lợn què"):**
   - Nghiên cứu ngoài (`IFScale arXiv:2507.11538v1`, `Context Rot`, `Skeleton Coding arXiv:2610.38214v1`, `Böckeler & Heym`) chứng minh: nhồi **văn xuôi dài dòng, code body chép nguyên văn, hoặc số dòng cứng dễ trượt** làm model nhỏ (`Flash/Haiku/Mini`) tụt hiệu năng theo hàm mũ (**Exponential Decay**) và gây lỗi dây chuyền (**plan drift**).
   - Thứ kéo model nhỏ từ `21.1% → 79.5%` (`+58.4 pp`) là **Structural Contract** (chữ ký hàm/struct/JSON schema + trạng thái Trước → Sau + bất biến cục bộ `<= 5–7` luật + neo theo tên symbol + Locked Test Oracle `input → assert` + tách task nguyên tử `<= 3` file), chứ **không phải** văn xuôi giải thích dài dòng.

### Quyết định đã chốt

- **Phạm vi đầu ra (`1a`, `loai_request=docs`):** Dừng ở báo cáo phân tích kiểm chứng + đề xuất thiết kế hoàn chỉnh qua `2` vòng phân tích & phản biện kèm ví dụ Task Card mẫu Trước/Sau và lộ trình triển khai chi tiết; KHÔNG chỉnh sửa `skills/`, `scripts/`, `hooks/`, `agents/` trong request này.
- **Mô hình vận hành mục tiêu (`2b` — Full Low-Tier End-to-End):** Thiết kế cải thiện PHẢI hoạt động vững cho cả `2` đầu đều có thể là model tier thấp — **Weak Planner** (viết spec/plan bằng phân rã cơ học từng bước + trích sự thật từ LSP/AST/scaffolder thay vì tự nhớ, tránh bịa schema & mega-task) VÀ **Weak Executor** (thực thi từ Executable Task Card / Auto Packet dạng Structural Contract, tránh IFScale decay & context rot), đồng thời vẫn chạy gọn khi người dùng dùng model mạnh.
- **Mức độ siết bằng công cụ (`3a` — Đủ `3` lớp):**
  1. Lớp 1 — Skill/Template/Agents (`tdq-plan`, `tdq-spec`, `tdq-build`, `quick-lane`, `tdq-reviewer`, `tdq-implementer`) tôn trọng ngân sách dòng & `3,500` token (`R6`, `R13`).
  2. Lớp 2 — Tooling & Automation: sửa bug parser `scripts/tdq_team.py:176-179` (tách biệt `Chạm:` và đường dẫn tham chiếu), bổ sung công cụ tự động hỗ trợ Weak Planner (trích neo symbol/skeleton) và Auto Task Packet Builder cho Weak Executor.
  3. Lớp 3 — Hard Gates: nâng cấp `scripts/doc_lint.py` R15 sang kiểm cấu trúc (kèm mốc ngày `R15_MOC`, quét cả `QCn.x` và `doc_lang=en/vi`, giới hạn mega-task) + gắn vào `doc_lint.py --pair` và cổng `tdq_state.py approve plan`.
- **Mức QC (`4a`):** `muc_qc = full` (DoD + kiểm chéo toàn bộ trích dẫn/số liệu + `doc_lint` + kiểm ràng buộc kiến trúc + đối chiếu sạch).
- **Phương án đã loại:**
  - Loại `1b`/`1c` (chèn sẵn patch raw hoặc sửa code trực tiếp): dễ vội vàng trước khi người dùng chốt thiết kế cuối sau 2 vòng phản biện.
  - Loại `2a`/`2c` (chỉ tối ưu Executor yếu hoặc tách 2 chế độ phức tạp): không giải quyết được kịch bản người dùng chạy toàn bộ phiên TDQ bằng model tier thấp (`2b`).
  - Loại `3b`/`3c` (chỉ sửa text/prompt không có hard-gate và không vá `tdq_team.py`): thực nghiệm sau `2026-11-11` đã chứng minh quy tắc mềm bị "Task Block Theater" (`20.8%` đạt chuẩn) và bị bug parser `tdq_team.py` phá song song.

### Nguồn & tài liệu đối chiếu

- Báo cáo nghiên cứu ngoài (Tavily): `docs/tdq/research/2026-11-19-2213-chi-tiet-plan-model-thap.md`
- Kiểm toán mã nguồn nội bộ: `skills/tdq-plan/**`, `skills/tdq-spec/**`, `skills/tdq-build/**`, `agents/**`, `scripts/doc_lint.py`, `scripts/tdq_team.py`, `scripts/tdq_state.py`, `scripts/token_budget.py`, `tools/patches/skills_and_agents.py`, `hooks/rust/tdq-dispatch/src/storage.rs`
- Dữ liệu thực nghiệm nội bộ: `236` plan trong `docs/tdq/plan/*.md` (`2,699` task; chấm sâu `12` plan / `48` task) và `4` cặp `spec ↔ plan`.

### Lý do bỏ qua vòng phạm vi riêng (Scope round)

Bỏ qua vòng phạm vi sơ bộ riêng lẻ vì `## Nguyên văn` đã khoanh rõ đối tượng (`plan` của `tdq-workflow` cho model tier thấp) và phương pháp (fanout subagent 2 vòng phân tích + phản biện tìm nhược điểm → trình bày đề xuất); toàn bộ các nút quyết định đã được chốt trong vòng phỏng vấn 1.

### Lộ trình

| Bước/phase | Chạy? | Vì sao |
|---|---|---|
| Research web (Tavily) | CÓ | Đã hoàn tất ở `analyze` (`docs/tdq/research/2026-11-19-2213-chi-tiet-plan-model-thap.md`) để tránh bẫy over-specification / IFScale decay |
| Interview | CÓ | Đã hoàn tất 1 vòng (`1a 2b 3a 4a 5a`), chốt đủ phạm vi, mô hình `2b` end-to-end, 3 lớp kỹ thuật và `muc_qc=full` |
| Spec + Archify BA Preview | CÓ | Khóa rõ đầu ra, tiêu chí đo 2 vòng và ranh giới phân công fanout trước khi triển khai |
| Plan (Checkbox từng chặng fanout) | CÓ | Chia rõ Chặng Vòng 1 (Phân tích & Đề xuất V1) và Chặng Vòng 2 (Phản biện Red-Team & Tinh chỉnh V2) |
| Implement (Fanout Subagent 2 vòng) | CÓ | Trực tiếp đáp ứng yêu cầu fanout subagent phân tích kỹ vòng 1 + tái phân tích phản biện vòng 2 tìm nhược điểm và cải thiện |
| QC mức `full` | CÓ | Kiểm chứng chéo 100% trích dẫn `path:line`, số liệu, `doc_lint.py`, tính khớp giữa Vòng 1 → Nhược điểm Vòng 2 → Bản vá V2 và chấm lại ví dụ Trước/Sau |
| Report + Archify HTML (Tailscale) | CÓ | Xuất báo cáo nghiệm thu 4 phần + Archify HTML trực quan hóa giải pháp Trước/Sau qua Tailscale Serve |

## Hỏi đáp

### Vòng 1 (`2026-11-19T22:35:48+07:00`)

- **Câu 1 (Phạm vi đầu ra):** A (đề xuất — docs báo cáo 2 vòng + đề xuất + ví dụ Trước/Sau + lộ trình) / B (kèm patch chi tiết) / C (đổi `feature` sửa code luôn).
  - **Người dùng chọn:** `1a`
- **Câu 2 (Mô hình vận hành model):** A (đề xuất — Architect mạnh + Executor yếu) / B (Full Low-Tier End-to-End cả pha plan lẫn pha implement) / C (Adaptive 2 chế độ).
  - **Người dùng chọn:** `2b`
- **Câu 3 (Mức độ siết công cụ):** A (đề xuất — kết hợp đủ 3 lớp Skill/Template + Parser/Auto-Packet + Hard Gate R15/`approve plan`) / B (không hard-gate) / C (chỉ sửa text).
  - **Người dùng chọn:** `3a`
- **Câu 4 (Mức QC `muc_qc`):** A (`full`, đề xuất) / B (`lite`) / C (`ultra`).
  - **Người dùng chọn:** `4a` (`muc_qc=full`)
- **Câu 5 (Bổ sung thêm):** A (Không, đủ rồi) / B (Có — tôi nói thêm).
  - **Người dùng chọn:** `5a`
