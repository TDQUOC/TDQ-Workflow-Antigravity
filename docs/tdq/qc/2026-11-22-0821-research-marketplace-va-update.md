# QC — Nghiên cứu custom marketplace GitHub, sẵn sàng Git và cơ chế auto-update của Antigravity

Ngày: 2026-11-22 · Request: `2026-11-22-0821-research-marketplace-va-update` · Work kind: `investigate` · Mức QC: `full` · Nhánh: `docs/research-marketplace-va-update`

> **Tóm tắt dễ hiểu:** Toàn bộ sáu tiêu chí định nghĩa hoàn thành và bốn cổng bằng chứng điều tra đều đạt sạch trong pha kiểm soát chất lượng. Mười chín chứng cứ gốc đều khớp dòng đĩa, các phép thử cô lập không đụng cấu hình thật của máy, và mã nguồn sản phẩm hoàn toàn nguyên vẹn. Sơ đồ HTML xuất bản xác minh khớp bản gốc và mở thông suốt qua địa chỉ mạng Tailscale.

## Dev Behavior QC Card

- **Trình tự pha:** `analyze -> spec -> plan -> implement -> qc` đúng luồng điều tra, không nhảy cóc và chưa tự đóng về `idle`.
- **Phạm vi chạm (Code-Failsafe):** Không sửa tệp nào ngoài thư mục tài liệu; `docs/architecture/status.json` chỉ tự cập nhật dấu thời gian kiểm tra từ trước.
- **Bảo toàn `~/.gemini/config/`:** Số tệp thông thường giữ nguyên mức gốc sau mọi phép thử `agy`.
- **An toàn nhánh phát hành:** Nhánh `main` giữ nguyên không đổi, chưa chạy lệnh đẩy từ xa và chưa đụng mã nguồn runtime.
- **Chất lượng suy luận:** Ba phản biện đối nghịch đều đã kiểm chứng lại trên tài liệu gốc và nhật ký chạy thật.

## Bảng đối chiếu cổng QC điều tra & toàn vẹn (`QC-I1`–`QC-I4`, `QC-F3`–`QC-F4`)

| Cổng | Mô tả kiểm tra | Kết quả | Bằng chứng đo thực tế |
|---|---|---|---|
| `QC-I1` | Sổ `evidence.jsonl` đủ dòng, 100% `[EV-xxx]` có `raw_file:lines` hợp lệ và khớp trích dẫn trong `research`/`reports` | `PASS` | `19/19` mã (`EV-A01`..`EV-A12`, `EV-B01`..`EV-B07`), `0` lỗi cận dòng, `0` mã mồ côi, `0` đường dẫn `path:line` lỗi |
| `QC-I2` | Kiểm tra ngẫu nhiên nội dung Claim khớp đúng từng vùng dòng `raw/` và mã nguồn đĩa | `PASS` | `12/12` assertion khớp chính xác nội dung trên `EV-A01..A05`, `EV-A08`, `EV-A10..A12`, `EV-B01`, `EV-B03`, `EV-B06` |
| `QC-I3` | Phản biện giả thuyết đối nghịch cho cả 3 kết luận chính | `PASS` | Cả `Phản biện 1`, `Phản biện 2`, `Phản biện 3` đều có đối chiếu tài liệu `v1.5.12`/`v2.34.0` và log `agy_probe_3.txt` |
| `QC-I4` | Mọi kết luận chính gắn nhãn độ tin cậy | `PASS` | Toàn bộ nhận định ở `research/<slug>.md` và `reports/<slug>.md` đều gắn `Verified` hoặc `Inferred` |
| `QC-F3` | Ranh giới kiến trúc & `git diff` không chạm mã nguồn ngoài `docs/` | `PASS` | `git diff --name-only dev...HEAD` trả `0` tệp code; `git status` có `0` tệp ngoài `docs/` (`docs/architecture/status.json` chỉ đổi `checked_at`) |
| `QC-F4` | Tác động mã nguồn / runtime | `KHÔNG ÁP DỤNG` | Yêu cầu `work_kind=investigate`, không thêm/sửa mã thực thi hay tệp cấu hình sản phẩm |

## Kiểm chứng Definition of Done (`Q1`–`Q6`)

| Hạng mục | Mô tả | Trạng thái | Kết quả chạy thực tế |
|---|---|---|---|
| `Q1` | Trả lời đủ 3 câu hỏi + ma trận khoảng trống + phương án đề xuất (`Windows`/`macOS`/`Linux`) | `PASS` | Từ khóa & 3 kết luận đầy đủ trong `reports/2026-11-22-0821-research-marketplace-va-update.md` |
| `Q2` | Thực nghiệm cách ly `agy` CLI có log và giữ nguyên `~/.gemini/config/` | `PASS` | `axis-a-cli.md` đạt chuẩn; tổng tệp thường `~/.gemini/config/` giữ nguyên ở `371` |
| `Q3` | Đạt `QC-I1` & `QC-I2` (100% `[EV-xxx]` và `path:line` hợp lệ) | `PASS` | `19/19` `EV-xxx`, `0` lỗi dòng, `12/12` `Claim <-> raw/` assertion `PASS` |
| `Q4` | Đạt `QC-I3` & `QC-I4` (3 phản biện counterfactual + nhãn tin cậy) | `PASS` | Cả 3 phản biện và nhãn `Verified`/`Inferred` xuất hiện đầy đủ trong `research/<slug>.md` |
| `Q5` | Ranh giới sạch `investigate`, `main` nguyên vẹn, không `git push` | `PASS` | `head=4b3eae4a`, `dev=4b3eae4a`, `main=91db3046`; `0` tệp ngoài `docs/` |
| `Q6` | `doc_lint.py` 0 lỗi, `tdq_archify.py verify` = `current`, Tailscale HTTP 200 | `PASS` | `tdq_meta_gate.py` `PASS`; `tdq_archify.py verify` = `current` (`valid=true`); Tailscale HTTPS trả HTTP `200`; `doc_lint.py` `0` lỗi trên `brief`/`spec`/`plan`/`qc`/`reports` |

## Kết luận QC

`PASS` — toàn bộ `6/6` task và `6/6` mục DoD (`Q1`–`Q6`) đều đạt sạch sau lần sửa cuối, báo cáo đã gắn `tdq_timing.py show` nguyên văn và xuất bản `Archify HTML` qua Tailscale HTTP `200`.
