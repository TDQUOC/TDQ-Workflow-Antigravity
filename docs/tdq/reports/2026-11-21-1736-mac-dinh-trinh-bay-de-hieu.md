# BÁO CÁO ĐIỀU TRA — TẠI SAO TDQ-WORKFLOW VẪN DÀY THUẬT NGỮ VÀ KIẾN TRÚC MẶC ĐỊNH 2 TẦNG

Ngày: 2026-11-21 · Mã yêu cầu: `2026-11-21-1736-mac-dinh-trinh-bay-de-hieu` · Chế độ: Điều tra (`work_kind=investigate`)

> **Tóm tắt dễ hiểu:** Dù hệ thống đã có luật viết tự nhiên, câu trả lời và tài liệu vẫn hay dài và dày ký hiệu kỹ thuật vì luật dễ hiểu bị đẩy xuống cuối tệp tham chiếu, còn lệnh bọc code quanh con số và nhắc nhở kỹ thuật lại xuất hiện ngay lúc viết. Khi tách phần tóm tắt lợi ích ra khỏi tên tệp và hàm bên dưới, tin nhắn chat ngắn đi gần 40 phần trăm và lượng ký hiệu kỹ thuật giảm gần 80 phần trăm. Giải pháp đề xuất chia đầu ra thành hai lớp cho chat, tài liệu và web, kèm nhắc nhở đúng lúc viết và kiểm tra tự động.

**Tệp liên quan:** Hồ sơ research ngoài [2026-11-21-1736-mac-dinh-trinh-bay-de-hieu.md](../research/2026-11-21-1736-mac-dinh-trinh-bay-de-hieu.md) · Sổ bằng chứng [evidence-log.md](../artifacts/2026-11-21-1736-mac-dinh-trinh-bay-de-hieu/evidence-log.md) · Trang web trực quan [2026-11-21-1736-mac-dinh-trinh-bay-de-hieu.html](2026-11-21-1736-mac-dinh-trinh-bay-de-hieu.html)

---

## 1. Trước request — Chẩn đoán nguyên nhân & phản chứng `H1`–`H4`

### 1a. Bức tranh gốc: "Đồng hồ xe hơi" bị in chung với "cổng chẩn đoán thợ máy"

Hãy hình dung bảng đồng hồ xe hơi: người lái chỉ cần thấy tốc độ, mức xăng và đèn báo lỗi trong ba giây, còn toàn bộ mã lỗi kỹ thuật nằm sau cổng OBD dành cho thợ sửa xe. Hiện tại TDQ-Workflow đang ép mô hình in cả hai lớp dữ liệu đó lên cùng một màn hình ngay từ dòng đầu tiên.

Qua rà soát `14.096` dòng lịch sử phiên làm việc từ 2026-11-19 đến 2026-11-21, người dùng phải nhắn nhắc giải thích lại cho dễ hiểu ít nhất `5` lần (`L5225`, `L8348`, `L8868`, `L10388` và `L13978`) `[EV-f4a4e8dfdddd]`. Đáng chú ý nhất, lần nhắc lúc `17:33` ngày 2026-11-21 xảy ra **sau khi** bản cập nhật dễ hiểu `2026-11-21-0917` đã được cài đặt hoàn chỉnh ngoài môi trường chạy thật `[EV-304180bb7005]`.

### 1b. Tách Triệu chứng bề mặt (Manifestation) và Điểm cam kết gốc (Point-of-Commitment)

- **Triệu chứng bề mặt (Manifestation):** Tin nhắn trả lời chạm gần `3.800` ký tự (như `L13977` đạt `3.779` ký tự, `109` cặp backtick, trung bình `52,67` từ mỗi gạch đầu dòng và có ý dài tới `99` từ), phần mở đầu file `.md` dày đường dẫn file và trang Archify HTML gắn nhiều tên hàm nội bộ `[EV-b9c225beffb9]`, `[EV-95bf58ffc46d]`, `[EV-aa0c2788eee9]`.
- **Ba Điểm cam kết gốc (Point-of-Commitment) diễn ra từ trước khi viết:**
  1. **Đọc thiếu phần cuối vì luật nằm sai chỗ:** Luật viết dễ hiểu nằm ở dòng `127–143` của `skills/tdq-conventions/references/user-facing-block.md`, nhưng khi chạy phiên `1536`, agent chỉ đọc `L1..50` (`L13511`) nên bỏ lọt hoàn toàn luật văn xuôi `[EV-1552ea0d38a1]`.
  2. **Viết ngược từ nhật ký kỹ thuật ra chat:** Khi sang pha báo cáo (`L13948`), agent chỉ đọc `report-template.md` đoạn `L100–170` (bỏ qua mẫu chat ở `L50–71`), viết bản báo cáo `.md` chi chít `207` backtick ở `34` dòng đầu (`L13952`) rồi sao chép chính khung kỹ thuật đó gửi ra chat lúc `17:30` (`L13977`) `[EV-95bf58ffc46d]`. Ngay cả báo cáo của chính đợt `0917` cũng tự tái nghiện ở `L7–15` vì agent vừa đọc mẫu báo cáo cũ `0217` trước khi viết `[EV-098dc22fe5f5]`.
  3. **Bị lực kéo trái chiều ép từ lúc tạo chữ:** Dòng `72` của `user-facing-block.md` vẫn bắt bọc backtick mọi con số, tên file và lệnh trong thân bài, đồng thời không có hook hay công cụ kiểm tự động nào ngăn hành vi này ở lúc xuất `[EV-1552ea0d38a1]`, `[EV-c67e6df1ce2b]`, `[EV-4ca445b684fb]`.

### 1c. Bảng phản chứng `4` giả thuyết (`H1`–`H4`) và giả thuyết đối thủ

| Giả thuyết | Kết luận | Độ tin cậy | Bằng chứng gốc trên đĩa & lịch sử phiên |
|---|---|---|---|
| **H1:** Luật dễ hiểu bị chìm ở tầng sâu, thiếu hook neo đúng lúc viết `spec`, `plan`, `report` | **Xác nhận** (`Confirmed`) | `Verified` | Trong `AGENTS.md`, câu viết dễ hiểu chỉ chiếm `1/29` dòng có chữ (`167/3.848` byte = `4,3%`) `[EV-0857c224bbdc]`; `session_start.py` bơm `133–139` dòng kỹ thuật nhưng `0` dòng văn phong; `_agy_phase_anchor` và `gate_guidance.py` (`22` mã) không kích hoạt ở pha `spec`, `plan`, `report` `[EV-c67e6df1ce2b]`; `tdq-spec` và `tdq-plan` chỉ trỏ `user-facing-block.md` ở bước trình bày sau khi file `.md` đã viết xong `[EV-abb98896c985]`. |
| **H2:** Khuôn mẫu và tiêu chí bằng chứng mâu thuẫn, kéo thuật ngữ tràn lên mặt tiền | **Xác nhận** (`Confirmed`) | `Verified` | `report-template.md:44` cho phép dán `verbatim` nguyên văn báo cáo kỹ thuật ra chat, đồng thời `L28–29` ép chèn bảng thời gian và `L112, 124, 126` làm mẫu nhồi dấu `·` làm report thật dài `82–252` dòng thay vì `10–20` dòng `[EV-8a19ef325a87]`. Nhãn đầu bị tách đôi (`Tóm tắt dễ hiểu` ở `spec` vs `Tóm tắt nhanh` ở `report`), còn `qc.md` đẩy số liệu thô lên đầu `[EV-8e0c98a92671]`. |
| **H3:** Bộ kiểm tra tự động mù trước độ dễ đọc trên đầu ra thật | **Xác nhận** (`Confirmed`) | `Verified` | `scripts/doc_lint.py:1511–1522` miễn toàn bộ `R1–R7` (kể cả `R5 <= 40` từ/câu) cho `OUTPUT_DIRS` (`docs/tdq/**`), xóa nội dung trong backtick và tách theo `[·;]` trước khi đếm từ `[EV-4ca445b684fb]`. Chạy thử `R5` bắt ngay `3` câu vượt `40` từ trong báo cáo `0917` và `5` câu trong `spec` `1536`. Cả `doc_lint.py` lẫn `test_report_visual.py` đều chưa kiểm `Tóm tắt`, mật độ backtick hay độ dài gạch đầu dòng `[EV-940404cdbfec]`. |
| **H4:** Luật dùng tính từ cảm tính thay vì ngưỡng số kèm bộ kiểm cơ học | **Xác nhận** (`Confirmed`) | `Verified` | Luật trình bày dùng cụm `"đọc hiểu trong 10–15 giây"`, `"lồng số liệu nhẹ nhàng"`, `"không có trần cứng dòng"` `[EV-996f5681b44f]`, ngược hẳn với các luật chạy ổn định trong TDQ như `MAX_SENTENCE_WORDS=40`, `R15<=35`, `TRAN_TOKEN=3500`, hook `240` ký tự. |
| **Giả thuyết đối thủ `H_alt`:** *Do quên đồng bộ gói `0917` ra bản cài thật `~/.gemini/`?* | **Bác bỏ** (`Refuted`) | `Verified` | Thư mục cài thật `~/.gemini/config/plugins/tdq-workflow-agy/` đã chứa đủ bản `0917` (`user-facing-block.md` `9.909` byte có mục `Plain-Language Narrative Rule` tại `L127`) trước khi chạy `1438` và `1536` `[EV-304180bb7005]`. Việc chỉ thêm đoạn văn khuyên ở file tham chiếu không đổi được hành vi thực tế. |

### 1d. Số đo thực nghiệm trên cả `3` bề mặt (`Chat`, `.md`, `Archify HTML`)

1. **Bề mặt Chat — Đối chứng trực tiếp `17:30` vs `17:33` trên cùng nội dung `v0.104.0` (`[EV-b9c225beffb9]`):**

| Chỉ số đo trên tin nhắn chat | Lượt `17:30` trước góp ý (`L13977`) | Lượt `17:33` sau góp ý (`L13980`) | Mức thay đổi |
|---|---|---|---|
| Tổng ký tự toàn tin (Thân chính) | `3.779` (`2.575`) | `2.301` (`1.574`) | **-39,1%** |
| Tổng cặp backtick (Thân chính) | `109` (`98`) | `40` (`39`) | **-63,3%** |
| Mật độ backtick trên `100` từ thân | `26,56` | `13,64` | **-48,6%** |
| Backtick tên kỹ thuật thân bài | `76` | `16` | **-78,9%** |
| Backtick bọc chữ số thường | `22` | `23` | Giữ nguyên do luật `L72` `[EV-1552ea0d38a1]` |
| Độ dài TB mỗi bullet (Dài nhất) | `52,67` từ (`99`) | `22,82` từ (`48`) | **-56,7%** (`-51,5%`) |
| Số cặp ngoặc đơn mở/đóng (Chân) | `29` (`5` link) | `13` (`3` link) | **-55,2%** |

2. **Bề mặt Tài liệu Markdown (`spec`, `report`) (`[EV-098dc22fe5f5]`, `[EV-95bf58ffc46d]`, `[EV-d9cfaef62018]`):**
   - Trước `0917` (`0217_report` phần mở đầu `L1–25`): `27,12` backtick/`100` từ, bullet dài tối đa `119` từ.
   - Đợt `0917` (`0917_report` `L5–21`): ô `L5` giảm còn `6,67` backtick/`100` từ nhưng phần mở đầu ngay dưới (`L7–15`) nhảy lên `17,00` backtick/`100` từ và trung bình `48,57` từ/bullet.
   - Đợt `1438` (`1438_report` `L3–6`): ô tóm tắt vẫn chứa `26` backtick trên `181` từ (`14,36`/`100` từ).
   - Đợt `1536`: `1536_spec` ô tóm tắt `L7` nhét `18` backtick trong `96` từ (`18,75`/`100` từ), còn `1536_report` `L5–39` lên tới `207` backtick/`741` từ (`27,94`/`100` từ), dày hơn cả trước khi sửa ở `0917`.

3. **Bề mặt Web trực quan Archify HTML (`[EV-aa0c2788eee9]`):**
   - Trong `1536/bao-cao.archify.md` (`50` dòng, `507` từ, `33` cặp backtick), đầu file gắn `@meta locale=en` dù báo cáo tiếng Việt vì `scripts/tdq_archify.py:451` gán cứng `"locale": "en"`.
   - Các nút trong sơ đồ `@workflow` vẫn mang nguyên tên lệnh và thuật ngữ kỹ thuật cho lập trình viên (`Auto Meta-Gate 0.08s`, `tron-bo --workers auto`, `build_agy_plugin v0.104.0`, nhãn vai trò `backend`, `messagebus`) thay vì ý nghĩa luồng công việc cho người đọc.

---

## 2. Sau request — Kiến trúc mặc định `2` tầng & Bộ mẫu Trước–Sau

### 2a. Nền tảng khoa học từ Research ngoài (`6` nguồn, đạt `HTTP 200`)

Thiết kế mới dựa trên bốn nguyên lý thực chứng từ [hồ sơ research](../research/2026-11-21-1736-mac-dinh-trinh-bay-de-hieu.md):
- **NN/g Concise & Progressive Disclosure (`[EV-78919ba36616]`, `[EV-c11abbaa14da]`):** Văn bản cô đọng tăng `+58%` khả dụng, dễ quét tăng `+47%`, khách quan tăng `+27%`; chỉ đặt phần người dùng hay cần lên tầng đầu và đưa chi tiết chuyên sâu sang tầng phụ.
- **LLM Primacy/Recency & Lost-in-the-Middle (`[EV-58d2e3fd49a9]`):** Cửa sổ ngữ cảnh lớn không tự ngăn mô hình quên luật nằm giữa tài liệu tham chiếu; mệnh lệnh đặt ở cuối ngữ cảnh (hook ngay trước khi viết) thắng mệnh lệnh chôn sâu ở file tham chiếu.
- **Anthropic Numeric Caps + Few-shot Examples & PlainLanguage BLUF (`[EV-f1236853977d]`):** Ràng buộc bằng con số đếm được kèm cặp ví dụ `Trước/Sau` gần điểm xuất và cắt ngữ cảnh cạnh tranh hiệu quả hơn tính từ chung chung; câu văn xuôi chuẩn Plain Language nên dưới `20–25` từ và đi thẳng vào kết luận (`BLUF`).

### 2b. Kiến trúc mặc định `2` tầng áp dụng đồng bộ `3` bề mặt

Nguyên tắc cốt lõi là tách mọi đầu ra thành hai tầng không trộn lẫn: **Lớp 1 (Mặt tiền người đọc)** chỉ trả lời `3` ý (*Trước ra sao → Sau đổi gì → Đã kiểm chứng thế nào*) bằng tiếng Việt tự nhiên, còn **Lớp 2 (Cổng OBD kỹ thuật)** giữ nguyên `100%` bằng chứng (`path:line`, `[EV-xxx]`, lệnh chạy, bảng số liệu).

| Bề mặt | Lớp 1 — Mặt tiền người đọc (Trần số đo mới) | Lớp 2 — Cổng OBD lưu chứng cứ đầy đủ |
|---|---|---|
| **1. Tin nhắn Chat** | Dài `8–16` dòng, mỗi ý `<= 25` từ; mật độ backtick `<= 6/100` từ; **0** số thường bọc backtick; **0** path/hàm thô xen giữa câu; `<= 3` link mở xem chi tiết ở cuối. | Đường dẫn click mở thẳng sang báo cáo `.md`, biên bản `qc/*.md`, và trang web Archify HTML trên Tailscale. |
| **2. Tài liệu `.md` (`spec`, `plan`, `report`)** | Hợp nhất `1` nhãn duy nhất `> **Tóm tắt dễ hiểu:**` (`<= 4` câu, `<= 3` backtick/`100` từ, `<= 2` dấu `·` trên dòng tiêu đề, `0` chuỗi `path:line` ở ô mở đầu). | Các mục sâu (`§2–§4`, bảng `Evidence`, bảng `Thời gian`, `QC Card`) vẫn giữ đủ `100%` mã `[EV-xxx]`, `path:line` và số test thật để phục vụ audit. |
| **3. Trang Archify HTML** | Tự động bật `locale: "vi"` theo `doc_lang`; nhãn mỗi nút và cạnh sơ đồ ghi hành động dễ hiểu cho người quản lý/người dùng (không in cờ CLI thô). | Giữ nguyên chi tiết kỹ thuật bên trong phần `detail` khi bấm vào từng nút hoặc đối chiếu chéo về tệp `.md` gốc. |

### 2c. Sáu cơ chế neo giữ mặc định dưới trần `3.500` token (`[EV-cd00642b350c]`)

Do các khuôn mẫu đang sát trần `3.500` token (`plan-template.md` `3.472`, `spec-template.md` `3.372`, `report-template.md` `3.333`, `qc.md` `3.328`), thiết kế dùng chiến lược **"dọn chỗ trước khi neo"** để giữ biến động token `<= 0`:

1. **Đảo trật tự và dọn luật gốc trong `user-facing-block.md` (giảm/giữ `< 2.900` token):**
   - Gỡ bỏ quy tắc #4 tại `L72` về việc bọc backtick chữ số và tên file trong thân bài dễ hiểu; chỉ giữ backtick cho mã lệnh hoặc tên file khi nằm ở Lớp 2.
   - Đưa bảng **Trần số đo Lớp 1** và `1` cặp ví dụ `Trước/Sau` lên ngay `40` dòng đầu (`L1–40`) để lần đọc ngắn `L1..50` không thể bỏ lỡ như phiên `1536` `[EV-1552ea0d38a1]`.
2. **Làm sạch mẫu đầu vào (`spec-template.md`, `report-template.md`, `plan-template.md` — giữ net token `<= 0`):**
   - Xóa tùy chọn `"verbatim"` tại `report-template.md:44`; thay các đoạn văn khuyên dài dòng bằng `3` ngưỡng số gọn.
   - Thống nhất nhãn mở đầu thành `> **Tóm tắt dễ hiểu:**` trên cả `spec`, `plan` và `report` (xóa nhãn `Tóm tắt nhanh:` tại `report-template.md:116`).
   - Dọn các dòng mẫu nhồi `3–5` dấu `·` ở đầu `spec-template.md:13`, `report-template.md:112, 124, 126` để template không làm gương xấu.
3. **Cài hook nhắc đúng lúc xuất `[TDQ:PLAIN]` (`<= 240` ký tự, Recency Anchor):**
   - Bổ sung mã `PLAIN` vào `tools/patches/gate_guidance.py` và mở rộng `_agy_phase_anchor` tại `tools/patches/agy_hooks.py:2430–2451` cho `3` pha `spec`, `plan`, `report`.
   - Khi mô hình chuẩn bị viết `spec` hay `report`, hook bơm đúng `1` thẻ `<= 240` ký tự ngay cuối ngữ cảnh: nhắc soạn Lớp 1 theo ngôn ngữ lợi ích trước, giữ `<= 6` backtick/`100` từ ở chat, và cấm copy nhật ký kỹ thuật `.md` ra chat.
4. **Thêm luật lint cơ học `R16` trong `scripts/doc_lint.py` và test hành vi thật:**
   - Thay vì giữ `OUTPUT_DIRS` mù toàn phần (`L1516–1522`), thêm hàm `rule_r16` chỉ kiểm **Lớp 1** của `docs/tdq/{spec,plan,reports}/*.md` (vùng từ dòng `1` đến trước `## 1.` hoặc `## Mục lục`, bỏ qua bảng `|`, khối code và log `Thời gian`):
     - Bắt buộc có đúng dòng `> **Tóm tắt dễ hiểu:**`;
     - Ô tóm tắt dài `<= 120` từ, câu `<= 30` từ, mật độ backtick `<= 6/100` từ và `0` đường dẫn có dấu `/` hay `:line`;
     - Toàn vùng mở đầu trước `## 2` có `<= 2` dấu `·` trên mỗi dòng không phải bảng.
   - Chuyển `tests/test_report_visual.py` từ kiểm chuỗi con tĩnh sang test trên mẫu báo cáo giả lập vi phạm (`25` backtick/`100` từ, thiếu tóm tắt) và mẫu đạt chuẩn để khóa hồi quy thật.
5. **Tham số hóa ngôn ngữ và nhãn Archify HTML (`scripts/tdq_archify.py`):**
   - Sửa `scripts/tdq_archify.py:451` lấy `locale` từ `doc_lang` của request (`vi` khi tài liệu tiếng Việt) thay vì gán cứng `"en"`.
   - Khi sinh `bao-cao.archify.md`, đặt tên nút sơ đồ theo hành động nghiệp vụ (Lớp 1) và đẩy lệnh/cờ kỹ thuật vào `detail` ẩn (Lớp 2).
6. **Ranh giới an toàn với `soul.md` (`Spec §5`):** Kiến trúc trên chỉ chỉnh luật hướng dẫn, template, hook nhắc và bộ lint; **không cần sửa** `skills/tdq-conventions/references/soul.md` (mọi sửa đổi `soul.md` nếu nảy sinh về sau phải hỏi người dùng duyệt riêng).

### 2d. Bộ mẫu Trước–Sau áp dụng ngay cho `3` bề mặt

*(Lưu ý: toàn bộ các đoạn trong bảng dưới đây là **mẫu minh họa — không phải câu hỏi lượt này**.)*

#### Mẫu 1 — Tin nhắn Chat sau khi hoàn thành báo cáo (`17:30` vs Chuẩn mới 2 tầng)

| Trước đây (dày chữ, mẫu `L13977` — `3.779` ký tự, `109` backtick) | Chuẩn mặc định mới (Lớp 1 dễ đọc — ~`1.150` ký tự, `< 5` backtick) |
|---|---|
| Đã hoàn tất đóng gói phát hành local `v0.104.0` cho `tdq-workflow-agy`:<br>- **Wave 1 (`tdq_test.py`, `tdq_test_receipt.py`, `tdq_timing.py`, `tdq_meta_gate.py`, `doc_lint.py`, `pytest.ini`):** Thêm `--workers auto` (`min(6, cpu_count)`), thêm `.html`/`.htm` vào `DATA_EXTS`, loại `.ruff_cache` ở `EXCLUDED_DIRS`... (`99` từ tiếp tục liệt kê tên hàm & cờ CLI). | **Bản nâng cấp kiểm thử E2E (v0.104.0) đã hoàn tất và chạy thông trên toàn bộ hệ thống.**<br><br>**Điểm mới chính:**<br>- **Kiểm tra nhanh và đúng phần vừa sửa:** Tự chọn đúng bài test theo phạm vi thay đổi, có thêm kiểm tra giao diện web trực quan trên trình duyệt thật.<br>- **Đóng gói sẵn sàng kiểm chứng:** Bản cài mới gọn sạch, không còn lỗi đếm nhầm thư mục rác hay bỏ sót trang web báo cáo.<br><br>**Kết quả chạy thử:**<br>- Toàn bộ 4.693 bài kiểm tra tự động và mở trang xem trước trên Tailscale đều đạt, không phát sinh lỗi trình duyệt.<br><br>**Xem chi tiết kỹ thuật tại:** [Báo cáo .md](...) · [Trang trực quan HTML](...) |

#### Mẫu 2 — Phần mở đầu `Spec` (`.md`)

| Trước đây (mẫu `1536_spec` — nhồi `18` backtick trong `96` từ ở `L7`) | Chuẩn mặc định mới (Lớp 1 mở đầu + Lớp 2 chi tiết bên dưới) |
|---|---|
| `# SPEC — Nâng cấp bộ kiểm thử` <br>`Ngày: 2026-11-21 · Bản: 1.0 · Brief: ... · Lane: full · Work kind: build`<br>`> **Tóm tắt dễ hiểu:**` Đợt nâng cấp bổ sung `Auto Meta-Gate`, chạy `smoke-e2e` với `--workers auto`, đồng bộ `agents/tdq-qc-tester.md`, `skills/tdq-browser-test/SKILL.md` và `build_agy_plugin.py` nâng lên `v0.104.0`... | `# SPEC — Nâng cấp bộ kiểm thử tự động và giao diện web`<br>Ngày: 2026-11-21 · Chế độ: Triển khai đầy đủ<br><br>`> **Tóm tắt dễ hiểu:**` Bộ kiểm tra hiện tại chạy tuần tự nên mất gần 20 phút và chủ yếu soi giấy tờ thay vì bấm thử giao diện thật. Đợt sửa này tự động chạy song song để rút ngắn thời gian xuống khoảng 5 phút, đồng thời bổ sung bước mở trang web kiểm tra trực tiếp trên trình duyệt trước khi báo xong. Toàn bộ tên tệp, mã test và ngưỡng kỹ thuật nằm ở các mục bên dưới. |

#### Mẫu 3 — Phần mở đầu `Report` (`.md`) & Nhãn `Archify HTML`

| Bề mặt | Trước đây (dày kỹ thuật, `L5–39` đạt `27,94` backtick/`100` từ) | Chuẩn mặc định mới (Lớp 1 cho người đọc ở trên) |
|---|---|---|
| **Report `.md` (`L1–12`)** | `# REPORT — Nâng cấp (\`slug\` · lane \`full\` · mode \`subagent\` · 11 task tick đủ)`<br>`> **Tóm tắt nhanh:**` Hoàn tất cả \`3\` Wave (`11` task + `QC1.1`), chạy `pytest` `4,693/4,704`, đóng gói `v0.104.0`... rồi liệt kê `14` bullet chép tên biến `SMOKE_ROUTES`, `DATA_EXTS`. | `# BÁO CÁO — Nâng cấp kiểm thử nhanh và giao diện web`<br>Ngày: 2026-11-21 · Mã yêu cầu: `2026-11-21-1536-nang-cap-qc-tester-e2e`<br><br>`> **Tóm tắt dễ hiểu:**` Sau khi sửa, thời gian chạy toàn bộ bài kiểm tra giảm từ gần 20 phút xuống hơn 5 phút. Bộ kiểm tra mới tự mở trang web trên trình duyệt để phát hiện lỗi hiển thị trước khi bàn giao. Chi tiết kỹ thuật và bảng thời gian xem ở Mục 3 và Mục 4 bên dưới. |
| **Archify HTML (`@workflow`)** | `@meta locale=en`<br>`\| new_meta \| Auto Meta-Gate 0.08s \| security \|`<br>`\| new_full \| tron-bo --workers auto 313.9s \| backend \|` | `@meta locale=vi`<br>`\| kiem_tai_lieu \| Tự kiểm soát lỗi tài liệu dưới 1 giây \| BuocKiem \|`<br>`\| chay_song_song \| Chạy kiểm tra song song hoàn tất trong 5 phút \| HeThong \|` |

---

## 3. Đã test gì (kiểm tra & đối chứng)

- **Kiểm toán mã nguồn nội bộ (`T1.1`):** Đo dòng, byte, ngân sách token (`token-budget.json`) và đọc trực tiếp logic nạp/kiểm trong `AGENTS.md`, `docs/claude-md-mau.md`, `tdq_setup.py`, `session_start.py`, `agy_hooks.py`, `gate_guidance.py`, `user-facing-block.md`, các template `spec/plan/report/qc`, `doc_lint.py` và bộ test visual (`t1.1-repo-audit.md` sạch `doc_lint`, `8` bản ghi bằng chứng).
- **Đo đạc thực nghiệm lịch sử phiên & đầu ra thật (`T1.2` + `t2-html`):** Quét `14.096` dòng của `transcript.jsonl`, đo đếm ký tự/từ/backtick/ngoặc đơn/bullet trên `5` file `spec`/`report` (`0217`, `0917`, `1438`, `1536`), `6` tin nhắn chat (kèm đối chiếu trực tiếp `17:30` vs `17:33`), bản live `~/.gemini/config/plugins/` và `2` bộ Archify HTML (`t1.2-transcript-rca.md` sạch `doc_lint`, `9` bản ghi bằng chứng tổng hợp).
- **Nghiên cứu chuẩn UX & LLM bên ngoài (`T1.3`):** Truy vấn qua `tavily-primary` và `search_web`, đồng thời kiểm trạng thái sống `HTTP 200` trực tiếp cho `6` nguồn từ Nielsen Norman Group, IntuitionLabs, ByteByteGo, arXiv, Anthropic và Digital.gov (`4` bản ghi bằng chứng).

---

## 4. Kết quả test & kiểm chứng

- **Kết quả tổng hợp bằng chứng:** Đã gộp đủ `21` bản ghi bằng chứng qua `4` shard (`t1.1`, `t1.2`, `t1.3`, `t2-html`) vào `docs/tdq/artifacts/2026-11-21-1736-mac-dinh-trinh-bay-de-hieu/evidence.jsonl`; toàn bộ đường dẫn `docs/tdq/**` không ghi nhận bất kỳ chỉnh sửa nào ở mã nguồn sản phẩm.
- **Phản biện đánh đổi kỹ thuật (`QC-I3` — Bớt chữ có làm mất bằng chứng hoặc vượt trần `3.500` token không?):**
  - *Nguy cơ mất trung thực:* Nếu chỉ cắt ngắn mù quáng, agent dễ giấu số đo test hoặc không gắn được `[EV-xxx]` (vi phạm quy định QC). Cách giải quyết bằng kiến trúc `2` tầng không cắt bớt chứng cứ mà **chuyển vị trí**: Lớp 1 chỉ nói giá trị đời thường cho con người, Lớp 2 giữ đủ `100%` `[EV-xxx]` và `path:line` cho QC và `doc_lint`.
  - *Nguy cơ phình vượt `3.500` token:* Do `plan-template.md` (`3.472`) và `spec-template.md` (`3.372`) đã sát trần, không thể nhồi thêm đoạn hướng dẫn mới vào template. Thay vào đó, hook ngắn `[TDQ:PLAIN]` (`<= 240` ký tự) chuyển trọng lượng nhắc sang đúng thời điểm xuất, còn các template chỉ xóa chữ rườm và sửa luật sai chỗ nên tổng token ròng giảm chứ không tăng.

---

## Thời gian

Request `2026-11-21-1736-mac-dinh-trinh-bay-de-hieu` · lane full · opened at 2026-11-21T17:41:09+07:00

| Phase | Wall clock | Times entered |
|---|---|---|
| idle | 1s | 1 |
| analyze | 6 min | 1 |
| spec | 3 min | 1 |
| plan | 6 min | 1 |
| implement | 12 min | 1 |
| qc | 1 min | 1 |
| report | 0s | 1 |
| Total | 28 min |  |

```text
Model compute time is unavailable (`model_giay=null`). API includes network/provider latency; tool time is host wait. Observed metrics may overlap; unattributed time is not assumed user/model time.
Transcript attribution: project_window. Complete covers selected supported observations only.
Host metrics unavailable (5 hidden: api_request_seconds, tool_call_seconds, background_job_seconds, observed_union_seconds, unattributed_seconds): no_usable_source, no_usable_observations, wall_minus_observed_union;no_usable_observations
```

---

## Giới hạn & Bước tiếp theo

- **Phạm vi an toàn đã giữ:** Thực hiện nghiêm chế độ điều tra (`work_kind=investigate`, bỏ qua LSP với lý do nghiên cứu tài liệu/luật `lsp_bo_qua`), chỉ tạo tài liệu điều tra dưới nhánh `docs/mac-dinh-trinh-bay-de-hieu` và giữ `0` thay đổi trong mã nguồn sản phẩm (`skills/`, `hooks/`, `scripts/`, `agents/`, `~/.gemini/`).
- **Bước tiếp theo nếu muốn áp dụng ngay:** Nếu bạn đồng ý triển khai `6` thay đổi ở Mục 2c vào mã nguồn `tdq-workflow`, bạn chỉ cần mở một request triển khai mới (hoặc yêu cầu chuyển sang `build`) dựa thẳng trên báo cáo này.
<!-- tdq-archify-binding:start -->
<!-- manifest: 2026-11-21-1736-mac-dinh-trinh-bay-de-hieu.manifest.json -->
<!-- manifest_digest: 3cedc7e46a8ec3559c25269b9d1ae3b6b524d372180782719dc99cee949c99a6 -->
<!-- tdq-archify-binding:end -->