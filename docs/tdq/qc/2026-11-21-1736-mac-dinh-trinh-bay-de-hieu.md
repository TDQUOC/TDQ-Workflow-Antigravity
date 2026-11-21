# BIÊN BẢN KIỂM CHỨNG CHẤT LƯỢNG (`QC-I1..I4`) — ĐIỀU TRA TRÌNH BÀY DỄ HIỂU

Ngày: 2026-11-21 · Mã yêu cầu: `2026-11-21-1736-mac-dinh-trinh-bay-de-hieu` · Nhánh: `docs/mac-dinh-trinh-bay-de-hieu` · Chế độ: Điều tra (`work_kind=investigate` · `muc_qc=full`)

> **Tóm tắt dễ hiểu:** Tất cả 21 bằng chứng trong báo cáo đều khớp với dòng tệp thật trên đĩa và đường dẫn web đang sống. Không có tệp mã nguồn nào ngoài thư mục tài liệu bị sửa đổi. Nhờ tách bạch phần mặt tiền dễ đọc với phần chi tiết kỹ thuật bên dưới, giải pháp giữ được 100 phần trăm độ trung thực bằng chứng mà không đụng trần ngân sách token.

## Dev Behavior QC Card

| Hạng mục hành vi | Giá trị thực tế | Trạng thái | Ghi chú kiểm chứng |
|---|---|---|---|
| Phạm vi sửa file (`git diff` & `git status`) | Chỉ `docs/**` (`0` file code ngoài `docs/`) | `PASS` | `git diff --name-only dev...HEAD` = `0`; `18` file untracked/dirty đều dưới `docs/` |
| Tự kiểm chứng nguồn thật (`QC-I1`, `QC-I2`) | `21/21` `[EV-xxx]` khớp `evidence.jsonl` & đĩa | `PASS` | `32` lượt trích (đủ `21` ID duy nhất), `0` ID thiếu, `0` đường dẫn hỏng |
| Đối trọng phản biện (`QC-I3`) | Soát `2` rủi ro mất chứng cứ & trần `3.500` token | `PASS` | Tách `Lớp 1/Lớp 2` bảo toàn `100%` `[EV-xxx]`; dọn chỗ trước khi neo giữ net `<= 0` |
| Gắn nhãn độ tin cậy (`QC-I4`) | `100%` kết luận có nhãn `Verified` / `Refuted` | `PASS` | Kiểm đủ `4` giả thuyết `H1`–`H4` + giả thuyết đối thủ `H_alt` |
| Tự thực hành văn phong mới | Ô tóm tắt `<= 120` từ, `0` cặp backtick | `PASS` | Ô `Tóm tắt dễ hiểu` trong báo cáo đạt `0` backtick và sạch `doc_lint` |

## Kiểm chứng `4` lớp điều tra (`QC-I1..I4`)

### `QC-I1` — Khớp mã `[EV-xxx]` và không còn nội dung giữ chỗ (`PASS`)
- Script đối chiếu trực tiếp `docs/tdq/artifacts/2026-11-21-1736-mac-dinh-trinh-bay-de-hieu/evidence.jsonl` (`21` bản ghi từ `4` shard `t1.1`, `t1.2`, `t1.3`, `t2-html`) với báo cáo `docs/tdq/reports/2026-11-21-1736-mac-dinh-trinh-bay-de-hieu.md`: khớp `32/32` lượt trích (`21/21` ID duy nhất), `missing_ids = []`.
- Toàn bộ đường dẫn nội bộ trích trong `evidence.jsonl` đều tồn tại trên đĩa (`bad_disk_paths = []`); toàn bộ `6` URL research ngoài kiểm trả `HTTP 200` trực tiếp.
- Số chuỗi giữ chỗ (`TODO`, `TBD`, `[placeholder]`): `0`.

### `QC-I2` — Đối chiếu trực tiếp Claim ↔ Dòng đĩa thật (`PASS`)
- Đối chiếu trực tiếp hai đường trên file nguồn cho thấy khớp chính xác:
  - `tools/patches/agy_hooks.py:2434` (`if not req or pha not in ("implement", "qc"):`) xác nhận pha `spec`, `plan` và `report` không có hook neo `[EV-c67e6df1ce2b]`.
  - `plugins/tdq-workflow-agy/rules/AGENTS.md:31` xác nhận luật kể chuyện chỉ chiếm `1/29` dòng có chữ (`167/3.848` byte) `[EV-0857c224bbdc]`.
  - `docs/tdq/token-budget.json:232, 268` xác nhận `plan-template.md` đạt `3.472` token và `spec-template.md` đạt `3.372` token `[EV-cd00642b350c]`.
  - `scripts/tdq_archify.py:451` xác nhận trường `"locale": "en"` bị gán cứng `[EV-aa0c2788eee9]`.

### `QC-I3` — Phản biện & Thử thách đánh đổi (`PASS`)
- **Câu hỏi phản biện 1:** *Ép chat và phần đầu `.md` ngắn lại, bỏ thuật ngữ kỹ thuật liệu có làm rơi mất bằng chứng QC hay che giấu tên tệp sai?*
  - **Phản hồi có chứng cứ:** Không mất, vì thiết kế `2` tầng không xóa bằng chứng mà dời `100%` `[EV-xxx]`, `path:line` và số test sang **Lớp 2** (từ `§1b` trở đi của `.md`, biên bản QC và phần chi tiết ẩn của HTML). Phép thử đối chứng `17:30` vs `17:33` (`[EV-b9c225beffb9]`) cho thấy vẫn cùng dữ liệu phát hành `v0.104.0`, khi chuyển tên biến xuống file báo cáo, chat giảm `78,9%` backtick kỹ thuật mà không mất kết quả nào.
- **Câu hỏi phản biện 2:** *Thêm ngưỡng đo vào `spec-template.md` (`3.372` token) hay `report-template.md` (`3.333` token) có làm vỡ trần `3.500` token?*
  - **Phản hồi có chứng cứ:** Có nguy cơ vỡ nếu nhồi thêm đoạn văn dài (`plan-template.md` chỉ còn trống `28` token `[EV-cd00642b350c]`). Vì vậy giải pháp bắt buộc cắt câu khuyên thừa trước khi chèn ngưỡng số ngắn và đẩy phần nhắc đúng lúc viết ra hook runtime `[TDQ:PLAIN]` (`<= 240` ký tự) thay vì tăng dung lượng template tĩnh.

### `QC-I4` — Nhãn độ tin cậy & Giới hạn (`PASS`)
- Mọi kết luận `H1`, `H2`, `H3`, `H4` (`Confirmed`) và giả thuyết đối thủ `H_alt` (`Refuted`) đều gắn nhãn `Verified` vì đối chiếu chéo từ cả mã nguồn lẫn số đo transcript/file thật.
- Ghi rõ giới hạn `lsp_bo_qua` (chế độ điều tra tài liệu/luật không sửa code sản phẩm) và chưa chạm nhánh `main` hay `~/.gemini/`.

## Đối chiếu `5` mốc Definition of Done (`Q1`–`Q5`)

| Mốc DoD | Yêu cầu trong Spec/Plan | Bằng chứng & Lệnh kiểm | Trạng thái |
|---|---|---|---|
| **Q1** | Kiểm `H1`–`H4` đủ `3` bề mặt (chat, `.md`, HTML) trong `evidence.jsonl` | `21` bản ghi hợp lệ qua `4` shard (`len >= 8` đạt), `100%` trích trong báo cáo | `PASS` |
| **Q2** | Hồ sơ research `>= 3` nguồn sống kèm quy tắc áp dụng | `docs/tdq/research/2026-11-21-1736-mac-dinh-trinh-bay-de-hieu.md` có `6` nguồn `HTTP 200`, `doc_lint` = `0` | `PASS` |
| **Q3** | Báo cáo đủ `3` phần (chẩn đoán, kiến trúc, mẫu Trước–Sau) & sạch lint | `docs/tdq/reports/2026-11-21-1736-mac-dinh-trinh-bay-de-hieu.md`, `doc_lint` = `0` lỗi | `PASS` |
| **Q4** | Đạt `QC-I1..I4` và giữ `0` thay đổi ngoài `docs/` | Script `QC-I1` + `git diff --name-only dev...HEAD` xác nhận `outside_docs = []` | `PASS` |
| **Q5** | Archify HTML hợp lệ (`current`, `valid=true`), Tailscale `HTTP 200`, `0` lỗi console | `tdq_archify.py verify` = `current`/`valid=true`, Tailscale `HTTP 200` (`1.270.566` B), `take_snapshot` `3` panel, `0` console error | `PASS` |
