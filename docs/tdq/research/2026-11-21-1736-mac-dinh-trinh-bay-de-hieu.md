# Hồ sơ Research — Thiết kế Mặc định Trực quan, Dễ hiểu cho TDQ-Workflow

Ngày: 2026-11-21 · Request: `2026-11-21-1736-mac-dinh-trinh-bay-de-hieu` · Kênh: `tavily-primary` + `search_web` + kiểm HTTP 200 trực tiếp

## 1. Bảng tổng hợp truy vấn và nguồn sống (`6` nguồn chính thức, đều đạt `HTTP 200`)

| # | Truy vấn / Góc nhìn | Nguồn & URL trực tiếp (verified `HTTP 200`) | Kết quả chính rút ra |
|---|---|---|---|
| 1 | UX đọc trên màn hình & viết cô đọng | **Nielsen Norman Group** — `https://www.nngroup.com/articles/concise-scannable-and-objective-how-to-write-for-the-web/` | Người đọc lướt nhanh chứ không đọc từng chữ; văn bản cô đọng tăng `+58%` khả dụng, dễ quét mắt tăng `+47%`, khách quan tăng `+27%` |
| 2 | Progressive Disclosure & giảm tải nhận thức | **Nielsen Norman Group** — `https://www.nngroup.com/articles/progressive-disclosure/` và `https://www.nngroup.com/articles/4-principles-reduce-cognitive-load/` | Chỉ đưa ý thiết yếu lên lớp đầu và cất chi tiết nâng cao sang lớp phụ; tách rõ lớp đầu/lớp hai giảm nhầm lẫn và tăng tốc đọc |
| 3 | Thiên lệch vị trí đầu–cuối trong LLM (Primacy & Recency) | **IntuitionLabs** — `https://intuitionlabs.ai/articles/llm-position-bias-primacy-recency-effects` | Luật đặt ở giữa ngữ cảnh dễ bị bỏ qua; đặt quy tắc định dạng ở cuối prompt trước khi sinh chữ tận dụng recency bias (kèm lưu ý hướng dẫn GPT-4.1 ưu tiên lệnh sau) |
| 4 | Điểm mù giữa prompt dài (`Lost in the Middle`) | **ByteByteGo** & **arXiv:2601.03269v1** — `https://blog.bytebytego.com/p/the-llm-blindspot-why-models-forget` và `https://arxiv.org/html/2601.03269v1` | Cửa sổ ngữ cảnh lớn không tự hết rớt luật ở giữa; chỉ dẫn trình bày cạnh tranh chú ý với tri thức dày đặc; cắt bớt ngữ cảnh thừa hiệu quả hơn ép trần từ tùy tiện |
| 5 | Viết rõ ràng chuẩn Anthropic (`Clear & Direct + Examples`) | **Anthropic / PromptLayer / AWS** — tổng hợp từ truy vấn `Anthropic prompt engineering be clear direct use multishot examples XML tags` | Từ khóa mơ hồ như "ngắn gọn, dễ hiểu" kém hiệu quả hơn ràng buộc số cụ thể (`3` gạch đầu dòng, tối đa `15` từ) kèm cặp ví dụ `Trước/Sau` đặt gần điểm xuất |
| 6 | Cấu trúc Kim tự tháp ngược (`BLUF`) & số đo Plain Language | **Digital.gov / PlainLanguage** — tổng hợp từ `plainlanguage.gov organize inverted pyramid concise sentences metrics` | Đưa kết luận chính lên đỉnh, câu ngắn (`< 20–25` từ), chủ ngữ sát động từ, chủ động; đo bằng thời gian nắm ý và số lần người dùng phải hỏi lại |

## 2. Nguyên tắc áp dụng trực tiếp vào `3` bề mặt của TDQ-Workflow

1. **Progressive Disclosure chặt cho cả Chat, `.md` và HTML (NN/g + Inverted Pyramid):**
   - Lớp mặt tiền (chat và hộp `Tóm tắt dễ hiểu` của `.md`) chỉ trả lời đúng `3` câu hỏi của người ra quyết định: *Trước sao? Sau đổi gì? Test ra sao?*, không rải SHA git, đường dẫn dài hay danh sách hàm trong câu văn.
   - Toàn bộ chứng cứ kỹ thuật (`path:line`, hash, tên module test, lệnh CLI) đẩy xuống Lớp 2 (bảng dưới của `.md`, biên bản `qc/*.md`, và biểu đồ HTML Archify).
2. **Tận dụng Recency Bias đặt "thẻ nhắc định dạng + ví dụ đối chiếu" ngay tại điểm xuất (`IntuitionLabs` + `arXiv:2601.03269v1`):**
   - Luật dễ hiểu nằm sâu trong file `references/` tầng `2` sẽ thua các hook `[TDQ:*]` và nhắc nhở bằng chứng xuất hiện gần cuối ngữ cảnh (`phase=spec`, `phase=report`, Stop gate).
   - Giải pháp kiến trúc không chỉ ghi luật ở `user-facing-block.md`, mà cần cài con trỏ mẫu `Trước/Sau` + số đo cứng ngay ở `next_headline` / bước cuối trước khi model gõ `spec`, `plan`, `report` và câu trả lời chat.
3. **Thay tính từ chung chung bằng trần số học đo được (`Anthropic` + `PlainLanguage` + NN/g):**
   - Thay cụm `"ngắn gọn, dễ hiểu"` bằng ngưỡng cụ thể cho lớp mặt tiền: tối đa `12`–`15` dòng phần thân chat tóm tắt, tối đa `<= 25` từ mỗi gạch đầu dòng mặt tiền, tối đa `<= 2` backtick kỹ thuật trên mỗi câu văn xuôi mở đầu, và `0` đường dẫn file trần nằm xen giữa câu văn.
   - Bổ sung kiểm định tự động mức độ dễ đọc ngay trong pipeline lint (bên cạnh `R5 <= 40` từ/câu) để máy tự bắt trước khi trình người dùng.
