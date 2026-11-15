# Changelog — bản lưu trữ 3

Bản 0.57.0, tách khỏi `CHANGELOG.md` để giữ file chính dưới trần R6 500 dòng (`docs/CHANGELOG-archive-2.md` đã chạm 496 dòng). Mới nhất trên cùng, chữ nghĩa copy nguyên văn.

## 0.57.0 — 2026-10-05

Một luật chạy test, một nguồn. Bước trung gian chỉ chạy test trong vùng chạm, trọn bộ dồn về
hai cổng. Trước bản này `tdq-build` ("EXACTLY ONCE"), khuôn plan ("sau mỗi phase chạy toàn bộ")
và `qc.md` (mỗi vòng sửa) nói ba kiểu khác nhau. Báo cáo:
`docs/tdq/reports/2026-10-03-1907-test-vung-cham-buoc-trung-gian.md`.

- **Bước trung gian chạy `scripts/tdq_test.py vung-cham`.** Nó chọn vùng chạm cộng bán kính ảnh
  hưởng: test nhắc đường dẫn/tên file, import bắc cầu đọc bằng AST, test quét thư mục cha. Trọn
  bộ chỉ ở 2 cổng: QC-F1 (thay lần "xong implement") và sau vòng sửa QC cuối nếu có sửa.
- **Không chắc thì chạy hết.** Bán kính ≥ 60% số module, hoặc file mã/loại không rõ ngoài
  `scripts/ hooks/ skills/ tests/ agents/` → trọn bộ trong một tiến trình. File dữ liệu (.md,
  .json…) chỉ kéo theo test nhắc đường dẫn của nó.
- **Đo trên repo này.** Sửa `stop_gate.py` → 16/129 module, 51,6 s (trọn bộ ~420 s). Sửa hub
  `tdq_state.py` → 98/129 module → trọn bộ.
- **Sổ sách.** `tdq_test.py tron-bo` ghi sổ, và có sổ bán kính bỏ sót (QC-F1 đỏ ở module bán kính
  chưa chọn); report in số lần, xem bằng `tdq_test.py so`. `next` nhắc khi số lần trọn bộ vượt
  ngân sách 2 (3 sau một lần trọn bộ đỏ) — chỉ nhắc, không chặn.
- **Test chạy được từ PowerShell.** Bỏ lệnh shell `true` khỏi 5 module test (trước: 26 fail +
  1 error).
- **Trung thực về tiết kiệm.** Nền cũ trung bình 7,4 lần trọn bộ/request (59 lần/8 request). Hai
  request gần nhất đã chỉ 2–3 lần, nên lợi chính là khoá luật cho khỏi trôi ngược.
