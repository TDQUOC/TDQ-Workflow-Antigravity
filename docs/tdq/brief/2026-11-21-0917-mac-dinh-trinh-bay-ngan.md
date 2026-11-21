# BRIEF — Mặc định Trình bày Report, Spec & Plan Ngắn gọn, Natural, Dễ hiểu

Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

## Nguyên văn

> okay vậy commit và merge, sau đó mở requestt handle là report và spec plan sẽ mặc định trình bày ngắn gọn natural dễ hiểu để bất kì ai cũng có thể hiểu mà không cần phải nhán thêm 1 lượt như trên

Ảnh ví dụ phong cách trình bày mong muốn đã lưu từ phiên đóng trước: [1.jpg](../workinglog/assets/2026-11-21-0217-trien-khai-investigate-v2/1.jpg)

**Đọc hiểu ban đầu:**
- **Mục tiêu:** Điều chỉnh quy chuẩn và mẫu trình bày trong TDQ Workflow để mọi `report`, `spec` và `plan` (cả phần trình bày trong chat lẫn/hoặc phần tóm tắt mở đầu file) mặc định viết **ngắn gọn, tự nhiên (natural), dễ hiểu** với mọi người đọc — nắm ngay điểm chính, thay đổi trước/sau và kết quả mà không cần user phải nhắn hỏi lại một lượt `"tóm tắt lại dễ hiểu hơn"`.
- **Phạm vi dự kiến:** Nhóm tài liệu quy chuẩn & template (`skills/tdq-conventions/references/user-facing-block.md`, `user-facing-block-vi-du.md`, `skills/tdq-build/references/report-template.md`, `skills/tdq-spec/references/spec-template*.md`, `skills/tdq-plan/references/plan-template*.md`, `skills/*/SKILL.md` liên quan), đồng bộ `docs/tdq/audit/luat-hien-co.md`, `docs/tdq/token-budget.json`, bộ test khóa chuỗi (`test_user_facing_block.py`, `test_luat_skill.py`, `test_doc_index.py`, `test_reference_mot_tang.py`), và rebuild `plugins/tdq-workflow-agy/`.
- **Điểm cần làm rõ sau khi chọn pipeline:**
  1. Phạm vi áp dụng: ưu tiên cách trình bày trong **khối chat trình bày** với user, hay cả **cấu trúc phần Tóm tắt đầu file** `.md` của `spec` / `plan` / `report`?
  2. Mức cân bằng với kỹ thuật: giữ nguyên số liệu/file/path chi tiết ở file `.md` (hoặc mục chi tiết phía dưới) còn phần đầu nói ngôn ngữ đời thường cho bất kỳ ai cũng hiểu?
  3. Có áp dụng đồng thời cập nhật live plugin vào `~/.gemini/config/plugins/` sau khi xong hay giữ nguyên build trong repo trước?

## Hiểu & kiến thức

### Năng lực dùng được

| Nguồn | Khớp với việc gì | Quyết định | Lý do |
|---|---|---|---|
| `tdq-conventions` (`plugin:tdq-workflow-agy` / repo) | Bộ quy chuẩn `user-facing-block.md`, ví dụ và bảng ký tự được phép | NỀN | Đọc để sửa trực tiếp quy tắc trình bày tự nhiên và khóa cấu trúc khối chat |
| `tdq-spec` (`plugin:tdq-workflow-agy` / repo) | Khuôn mẫu `spec-template.md`, hướng dẫn viết và khối trình bày `SKILL.md` | NỀN | Đọc để bổ sung cách viết `spec` dễ hiểu mà không vượt trần 3.500 token |
| `tdq-plan` (`plugin:tdq-workflow-agy` / repo) | Khuôn mẫu `plan-template.md`, hướng dẫn và khối trình bày `SKILL.md` | NỀN | Đọc để bổ sung cách viết `plan` dễ hiểu ngay ở khối chat và tóm tắt đầu |
| `tdq-build` (`plugin:tdq-workflow-agy` / repo) | Khuôn mẫu `report-template.md` và phần báo cáo cuối `SKILL.md` | NỀN | Đọc để thay dòng nén toàn `·` bằng kể chuyện Trước → Sau → Kết quả như `1.jpg` |
| `tdq-intake` (`plugin:tdq-workflow-agy` / repo) | Chuẩn trình bày nhanh `quick-lane-mini.md` và phỏng vấn `interview.md` | NỀN | Đọc để đồng bộ phong cách gọn, tự nhiên cho cả luồng `quick` |
| Đã xét 48 skill khác (37 mục trên đĩa trừ 5 nhóm TDQ trên và 11 skill built-in trong context) | Chạy trình duyệt, Google Workspace, design, MCP plugin ngoài | KHÔNG | khác lĩnh vực |

### Khảo sát mã nguồn & Vùng file chạm (Tam giác Grep / LSP / Graphify)

- **LSP & khóa luật:** Đã kiểm `tdq_setup.py` và `tdq_lsp.py check` (5/8 bậc đạt, 3/3 lượt tìm kiếm đạt; Rung 8 `python:.` lỗi tại `tools/patches/agy_manifests.py:258` ngoài cấu hình pyright), bật `--bo-qua-lsp` hợp lệ cho tác vụ tài liệu/quy chuẩn TDQ.
- **Graphify:** `graphify explain "scripts_tdq_state_archify_gate"` cho thấy mọi chỉnh sửa ở `scripts/` đều có bản đối ứng biên dịch tại `plugins/tdq-workflow-agy/scripts/`, gắn trực tiếp với `_cli_approve()` và gate báo cáo (`scripts/tdq_state.py:2874-2879`).
- **Grep vùng chạm (`scripts`, `tools`, `tests`, `skills`):**

| Lớp | Thành phần chính | Vai trò & Ràng buộc hiện tại |
|---|---|---|
| Quy chuẩn chung | `skills/tdq-conventions/references/user-facing-block.md` (`2392/3500` tok) & `user-facing-block-vi-du.md` (`1085/3500` tok) | Khóa cú pháp 6 phần, 8 luật trang trí, cấm emoji và giữ 6 ký tự cho phép; chưa có luật văn phong kể chuyện dễ hiểu |
| Khuôn `spec` | `skills/tdq-spec/SKILL.md`, `references/spec-template.md` (`3458/3500` tok), `spec-template-huong-dan.md` (`3000/3500` tok) | Trần token gần chạm nóc `3500`, khối chat `<=50` dòng mới liệt kê nhãn kỹ thuật |
| Khuôn `plan` | `skills/tdq-plan/SKILL.md`, `references/plan-template.md` (`3420/3500` tok), `plan-template-huong-dan.md` (`1222/3500` tok) | Trần token còn `80` tok, khối chat `<=14` dòng chưa hướng dẫn diễn giải mục tiêu cho người ngoài hiểu |
| Khuôn `report` & `quick` | `skills/tdq-build/references/report-template.md` (`3123/3500` tok), `skills/tdq-intake/references/quick-lane-mini.md` (`1006/3500` tok) | Dòng 101 & 110–115 của `report-template.md` ép nén mỗi mục vào MỘT dòng nối bằng `·` nên câu đọc khô và dày thuật ngữ |
| Prompt & Build AGY | `scripts/tdq_setup.py:1145`, `tools/patches/agy_manifests.py:208`, `tools/build_agy_plugin.py`, `tools/install_agy_plugin.py` | Sinh `KHOI_HUONG_DAN` toàn cục, `plugins/tdq-workflow-agy/rules/AGENTS.md` và gói plugin cài ra `~/.gemini/config/plugins/` |
| Bộ test khóa chuỗi | `tests/test_user_facing_block.py`, `tests/test_report_visual.py`, `tests/test_spec_template.py`, `tests/test_khao_sat_3_chieu.py`, `tests/test_luat_dung.py`, `tests/test_luat_gate_chat.py`, `tests/test_soul_rules.py`, `tests/test_claude_md_core.py`, `docs/tdq/audit/luat-hien-co.md`, `docs/tdq/token-budget.json` | Khóa cứng số khối `➤`, `1..8` luật trang trí, đề mục `"Trước request"`/`"Sau request"`/`"Đã test gì"`/`"Kết quả test"`, chữ ký prefix 40 ký tự và ngân sách `3500` token |

### Quyết định vòng phạm vi & Nghiên cứu ngoài

- **Vòng chốt mảng (Scope round):** Bỏ qua vòng tách mảng vì yêu cầu chỉ chạm đúng một mảng thống nhất là chuẩn trình bày tự nhiên cho `spec`, `plan`, `report` và đồng bộ đóng gói plugin TDQ.
- **Nghiên cứu ngoài:** Bỏ qua tìm kiếm ngoài vì đây là quy chuẩn văn phong và khuôn mẫu nội bộ TDQ, đã có mẫu đối chiếu trực quan do người dùng gửi kèm trong `1.jpg`.

### Đánh đổi & Điểm đã chốt

1. **Phạm vi áp dụng (`1a`):** Đổi đồng thời cả hai mặt — (a) nâng cấp văn phong kể chuyện ngắn gọn, tự nhiên cho khối chat trình bày `spec`, `plan`, `report`; (b) thêm mục tóm tắt đời thường ngay đầu các file `.md` (và mẫu đầu ra nhanh `quick`), giữ nguyên bảng kỹ thuật và các mục bắt buộc bên dưới để `doc_lint.py` và `tdq_state.py` kiểm tra bình thường.
2. **Độ chi tiết kỹ thuật (`2a`):** Mặc định kể theo mạch `"Trước đây → Sau khi làm xong → Kết quả"` bằng ngôn ngữ đời thường như ảnh `1.jpg`. Số liệu và thành phần chính lồng gọn vào câu văn tự nhiên; đường dẫn dài hoặc câu lệnh chi tiết đẩy xuống link mở file/bảng kỹ thuật.
3. **Đóng gói plugin (`3b`):** Sửa bộ nguồn trong repo và build lại gói `plugins/tdq-workflow-agy/` (kèm đồng bộ cấu hình sinh `AGENTS.md` / `tdq_setup.py`), **không** cài đè ra thư mục plugin live `~/.gemini/config/plugins/` (chỉ kiểm chứng `--dry-run` nếu cần).
4. **Mức QC (`4a`):** `full` — chạy đầy đủ unit test khóa luật/ký tự/mẫu, token budget, `doc_lint.py`, build plugin và QC độc lập.

## Hỏi đáp

### Vòng 1 (Đã chốt)

Trả lời của người dùng: `1a 2a 3b 4a 5 không?`

1. **Phạm vi áp dụng:** Chọn `A` — Áp dụng cả khối chat trình bày lẫn phần tóm tắt đời thường đầu file `.md`, giữ nguyên bảng kỹ thuật bên dưới.
2. **Cách xử lý chi tiết kỹ thuật:** Chọn `A` — Kể mạch Trước → Sau → Kết quả dễ hiểu như `1.jpg`, lồng số liệu chính nhẹ nhàng, đẩy path/lệnh dài về link.
3. **Phạm vi đóng gói plugin:** Chọn `B` — Sửa repo và build lại `plugins/tdq-workflow-agy/`, không cài đè ra thư mục `~/.gemini/config/plugins/`.
4. **Mức QC:** Chọn `A` — `full`.
5. **Bổ sung:** Không có yêu cầu bổ sung.

### Lộ trình

| Bước | Pha | Trạng thái | Việc chính |
|---|---|---|---|
| 1 | `analyze` | Xong | Chốt bài toán 1 vòng (phạm vi 2 mặt, giọng kể `1.jpg`, chỉ build repo, `muc_qc=full`) và lập bản đồ vùng chạm |
| 2 | `spec` | Kế tiếp (Chờ duyệt) | Thiết kế luật văn phong tự nhiên trong `user-facing-block.md`, cách lồng tóm tắt đầu file không vượt trần `3.500` token, cập nhật bản vẽ Trước/Sau Archify |
| 3 | `plan` | Chờ | Chia task theo từng nhóm luật/template, test khóa chuỗi/ngân sách, build & kiểm `plugins/tdq-workflow-agy/` |
| 4 | `implement` | Chờ | Thực hiện từng task (Red → Green), cập nhật `luat-hien-co.md`, `token-budget.json`, build plugin trong repo |
| 5 | `qc` | Chờ | QC độc lập kiểm `Q1–Q6` với mức `full` trên toàn bộ test và sản phẩm đóng gói |
| 6 | `report` | Chờ | Xuất cặp `report` (`.md` + Archify HTML) theo đúng phong cách mới, hỏi commit & merge về `dev` |
| 7 | `idle` | Chờ | Đóng request và dọn nhánh |

