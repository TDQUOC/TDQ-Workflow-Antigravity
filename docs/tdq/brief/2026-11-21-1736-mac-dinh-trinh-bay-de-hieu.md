# BRIEF — Điều tra và nghiên cứu chuẩn mặc định trình bày trực quan, dễ hiểu cho TDQ-Workflow
Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

## Nguyên văn

> okay commit và mở request xử lí cho tôi một vấn đề là bạn có tháy mỗi lần bạn soạn report hay spec tôi hay phải báo là trình bày dễ hiểu hơn đi, thì bây giờ tôi muốn bạn mở request phân tích và kiểm tra issue và resreach làm sao để default của tdq-workflow luôn là trình bay trực quan và dễ hiểu nhất sẵn để tôi khỏi phải gửi trình bày dễ hiểu trực quan hơn như vậy nữa. mở reqesst check và phân tích và báo cáo cho tôi

Đọc hiểu ban đầu:
- **Mục tiêu:** Tìm tận gốc lý do agent vẫn hay viết `spec` và `report` (cùng bản tin trong chat) quá dày thuật ngữ kỹ thuật, dù đã từng có rule trình bày dễ hiểu; đồng thời nghiên cứu chuẩn trình bày trực quan tự nhiên mặc định.
- **Phạm vi (`work_kind=investigate`):** Chỉ kiểm tra mã nguồn/rule/skill/hook/template trong repo, nghiên cứu bên ngoài và xuất báo cáo phân tích kèm khuyến nghị hành động; chưa chỉnh sửa mã nguồn sản phẩm trừ khi người dùng yêu cầu nâng cấp sang `build`.
- **Điểm cần kiểm tra ở pha phân tích:** Vì sao luật cũ ở `user-facing-block.md`, `spec-template.md`, `report-template.md` hoặc `AGENTS.md` vẫn bị lấn át bởi các khung bảng/checklist dài dòng hoặc mật độ nhồi thông tin ở từng phase.

## Hiểu & kiến thức

### Năng lực dùng được

Phân vân → DÙNG. Kiểm kê ngày 2026-11-21: `42` skill trên đĩa (`plugin:tdq-workflow` và `plugin:tdq-workflow-agy`), cộng bộ skill built-in trong ngữ cảnh. Không xoá bảng này kể cả khi rỗng dòng DÙNG.

| Skill | Nguồn | Phán quyết | Dùng ở đâu / Lý do loại |
|---|---|---|---|
| `tdq-intake` | `plugin:tdq-workflow-agy` | NỀN | Đã dùng để mở request, khảo sát nông và phỏng vấn |
| `tdq-spec` | `plugin:tdq-workflow-agy` | NỀN | Khung lập spec chuẩn chế độ `investigate` |
| `tdq-plan` | `plugin:tdq-workflow-agy` | NỀN | Khung chia nhánh điều tra `no_worktree` |
| `tdq-build` | `plugin:tdq-workflow-agy` | NỀN | Khung tổng hợp báo cáo và kiểm chứng `QC-I1..I4` |
| `tdq-conventions` | `plugin:tdq-workflow-agy` | NỀN | Khung quy tắc lõi, ngôn ngữ và đối chiếu trình bày |
| `tdq-browser-research` | `plugin:tdq-workflow-agy` | DÙNG | Dùng ở Đầu ra #2: nghiên cứu nguồn ngoài (kèm MCP `tavily-primary`) về UX báo cáo AI và cognitive load |
| `tdq-browser-test` | `plugin:tdq-workflow-agy` | DÙNG | Dùng ở Đầu ra #4: kiểm Accessibility Tree và `0` lỗi console trên Archify HTML báo cáo |
| `generative_ui` | `built-in` | KHÔNG | spec §3 đã chọn cách khác tốt hơn (dùng Archify HTML mặc định của TDQ) |
| Đã xét `19` skill đĩa khác và `15+` skill built-in khác | `plugin` / `built-in` | KHÔNG | khác lĩnh vực |

### Hiện trạng & điểm vào đã xác nhận

- Hồ sơ kiến trúc `docs/kien-truc.md` quy định phân tầng `3` ngôn ngữ, `soul.md` ở đầu file, ngưỡng `doc_lint.py` (`R5 <= 40` từ/câu, `R12`, `R13`) và trần `3.500` token cho file reference.
- Request trước `2026-11-21-0917-mac-dinh-trinh-bay-ngan` đã bổ sung `Plain-Language Narrative Rule` trong `user-facing-block.md`, hộp `Tóm tắt dễ hiểu` ở `spec`/`plan`/`report` và viết lại `report-template.md`, nhưng các phiên thực tế sau đó (`0917` lẫn `1536`) vẫn bị dày thuật ngữ và đòi tóm tắt lại.
- Các điểm vào ứng viên sẽ đọc sâu ở pha `implement`: `skills/tdq-conventions/references/user-facing-block.md`, `user-facing-block-vi-du.md`, `skills/tdq-spec/references/spec-template.md`, `skills/tdq-plan/references/plan-template.md`, `skills/tdq-build/references/report-template.md`, `qc.md`, `rules/AGENTS.md`, `docs/claude-md-mau.md`, `scripts/doc_lint.py`, `hooks/scripts/agy_stop_gate.py` và các report/transcript gần đây.

### 4 giả thuyết cần kiểm chứng ở pha implement

- **`H1` (Chìm ở tầng reference phụ & thiếu nhắc lúc viết):** `user-facing-block.md` (`~2.863` tok) ít được nạp đúng thời điểm model viết `spec`, `report` hay câu trả lời chat, trong khi hook/prompt chính lại liên tục ép kiểm số liệu.
- **`H2` (Xung đột giữa "chứng minh đầy đủ" và "tóm tắt dễ hiểu"):** Các câu nhắc chống bịa và đòi bằng chứng chi tiết ở `qc.md`, `report-template.md`, `AGENTS.md` kéo model đổ tên file, SHA và số test vào ngay phần tóm tắt của người dùng.
- **`H3` (Thiếu cổng đo tự động độ dễ đọc):** `doc_lint.py` mới kiểm độ dài câu (`R5 <= 40` từ) và `6` ký tự whitelist, chưa kiểm mật độ thuật ngữ/backtick, số dòng khối chat hay cấu trúc tách lớp cho người đọc không chuyên kỹ thuật.
- **`H4` (Luật thiếu trần cứng & ví dụ Đối/Chiếu ngắn gọn):** Khẩu hiệu "ngắn gọn, dễ hiểu" thiếu giới hạn dòng/mục rõ ràng cho phần mở đầu và thiếu cơ chế tách 2 lớp (mặt tiền kể chuyện 10 giây, phần bằng chứng kỹ thuật nằm gọn bên dưới hoặc trong file/HTML).

### Lý do bỏ qua scope-round

Đã có sẵn yêu cầu rõ từ người dùng (`work_kind=investigate`: chỉ kiểm tra, phân tích, research và báo cáo về chuẩn trình bày mặc định trực quan, dễ hiểu, chưa sửa mã nguồn).

### Lộ trình dự kiến

| Bước / phase | CÓ / BỎ | Vì sao |
|---|---|---|
| `analyze` | CÓ | Khảo sát nông điểm vào, lập `4` giả thuyết và chốt phạm vi điều tra qua phỏng vấn |
| `spec` | CÓ | Chốt câu hỏi điều tra, mục tiêu cần đo và ngưỡng chứng cứ `QC-I1..I4` (miễn `§2b`/`R14`/`Archify preview` vì `investigate`) |
| `plan` | CÓ | Chia nhánh điều tra độc lập theo `no_worktree` và chọn chế độ `main` hay `subagent` |
| `implement` | CÓ | Đọc sâu nội bộ, đối chiếu transcript, research ngoài và soạn bản nháp báo cáo kèm bằng chứng `[EV-xxx]` |
| `qc` | CÓ | Kiểm chứng hai đường `QC-I1..I4` (giữ `100%` bằng chứng tồn tại thật trên đĩa và URL thật) |
| `report` | CÓ | Hoàn thiện báo cáo Markdown + Archify HTML trực quan trên Tailscale |

### Quyết định đã chốt

- **Phạm vi bề mặt (`1a`):** Kiểm tra và thiết kế chuẩn cho cả `3` nơi — tin nhắn chat, tài liệu `.md` (`spec`/`plan`/`report`) và báo cáo Archify HTML.
- **Nguồn đối chiếu (`2a`):** Kiểm tận gốc mã nguồn/luật/hook trong repo, các phiên transcript vừa chạy và research bên ngoài về UX báo cáo AI, cognitive load và kỹ thuật prompt.
- **Mức chi tiết báo cáo (`3a`):** Đầy đủ `3` phần — chẩn đoán nguyên nhân kèm bằng chứng, kiến trúc giải pháp khả thi và mẫu đối chiếu Trước–Sau cho chat/`spec`/`report`.
- **Mức QC (`4a`):** `muc_qc = full` (`QC-I1..I4`).

## Hỏi đáp

### Vòng 1 (`1a 2a 3a 4a` — user đã chốt)
1. Phạm vi bề mặt cần chuẩn mặc định dễ hiểu, trực quan → **A**: cả `3` nơi (chat, `.md`, HTML).
2. Nguồn kiểm chứng → **A**: nội bộ repo + transcript gần đây + research ngoài.
3. Mức chi tiết báo cáo cuối → **A**: chẩn đoán + giải pháp kiến trúc + bộ mẫu Trước–Sau cho chat/`spec`/`report`.
4. Mức QC (`muc_qc`) → **A**: `full` (`QC-I1..I4`).
