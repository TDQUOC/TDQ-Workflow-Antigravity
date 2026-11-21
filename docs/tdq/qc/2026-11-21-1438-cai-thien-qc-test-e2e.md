# Biên bản QC & Kiểm chứng Bằng chứng (`2026-11-21-1438-cai-thien-qc-test-e2e`)

- **Request:** `2026-11-21-1438-cai-thien-qc-test-e2e` · **Lane:** `full` · **Loại:** `investigate` / `docs` · **Phạm vi:** `Zero-Code-Touch`

> **Tóm tắt kiểm chứng nhanh (`Dev-First QC Card`)**
> - **Auto Meta-Gate:** `doc_lint.py` đạt `0 violation(s)`, `Zero-Code-Touch` sạch `0` tệp mã nguồn bị sửa ngoài `docs/tdq/` và `docs/workinglog/`.
> - **Chứng cứ đa luồng (`QC-I1` / `QC-I2` / `QC-I4`):** `24/24` mã `[EV-001]`–`[EV-024]` trong báo cáo khớp `100%` với `evidence.jsonl`, đường dẫn `path:line` có thật trên đĩa, và `7` trích dẫn URL khớp nguyên văn tài liệu trích xuất thô tại `raw/01..04*.txt`.
> - **Trạng thái hiện tại:** `Q1`–`Q6` đạt **`PASS`** (`6/6`); Archify HTML đã xác thực `status="current"`, `valid=true` và phản hồi `HTTP 200` (`1,247,087` bytes) qua Tailscale Serve.

---

## 1. Bảng kiểm Definition of Done (`Q1`–`Q6`)

| Hạng mục | Tiêu chí kiểm | Kết quả kiểm thực tế | Trạng thái |
| :--- | :--- | :--- | :--- |
| `Q1` | Chẩn đoán thực chứng `H1`–`H4` trên `3` lớp TDQ với `>= 10` `[EV-xxx]` trỏ `path:line` | Kiểm trực tiếp trên `audit-tdq-qc-test.md`, `qc.md`, `tdq_test.py`, `timing.jsonl`, `.tdq-test.jsonl` — đủ `15` mục `EV` cho TDQ (`EV-001`..`EV-013`, `EV-024`) | `PASS` |
| `Q2` | Phân tích `33` tệp `terterarmy-cli` và `4`–`6` chuẩn ngành qua `tavily-primary` | `phan-tich-terterarmy-cli.md` (`114` dòng, `33` tệp) + `research/2026-11-21-1438-cai-thien-qc-test-e2e.md` (`162` dòng, `22` URL, `4` tệp `raw/01..04*.txt`) | `PASS` |
| `Q3` | Báo cáo đề xuất `4` phần + mô hình mới + KPI | `docs/tdq/reports/2026-11-21-1438-cai-thien-qc-test-e2e.md` dài `220` dòng (`28,213` ký tự), đủ `> Tóm tắt nhanh`, `4` phần chuẩn và `4` phần đề xuất (`T2.2 PASS`) | `PASS` |
| `Q4` | Đạt cổng bằng chứng `QC-I1`, `QC-I2`, `QC-I4` | `QC-I1`: `24/24` khớp (`missing=0`, `src_errs=0`); `QC-I2`: `24/24` kiểm trích đoạn; `QC-I4`: `Verified` (`14`), `Single-source` (`1`), `Inferred` (`7`) | `PASS` |
| `Q5` | `py -3 -X utf8 scripts/doc_lint.py` thoát `0` & `Zero-Code-Touch` | `doc_lint.py` trả `0 violation(s)`; `git diff --name-only dev..HEAD` trả `[]`; `bad_wt` chỉ có timestamp `checked_at` tự động của `docs/architecture/status.json` (không sửa code) | `PASS` |
| `Q6` | Archify HTML `verify` (`current`, `valid=true`) + Tailscale `HTTP 200` | `tdq_archify.py render` đạt `showcase`/`pass`, `verify` trả `status="current"`, `valid=true`; Tailscale URL trả `HTTP 200` (`1,247,087` bytes) | `PASS` |

---

## 2. Chi tiết cổng bằng chứng (`QC-I1`, `QC-I2`, `QC-I4`)

- **`QC-I1` (Khớp trích dẫn 100%):**
  - Lệnh kiểm tự động xác nhận `24` mã duy nhất `[EV-001]`..`[EV-024]` xuất hiện trong `docs/tdq/reports/2026-11-21-1438-cai-thien-qc-test-e2e.md`, khớp `100%` với `24` bản ghi trong `evidence.jsonl` (`missing_ev=[]`, `uncited_ev=[]`, `src_errs=[]`).
  - Tất cả `17` nguồn nội bộ và `terterarmy-cli` (`path:line`) đều nằm trong số dòng thật của file trên đĩa; tất cả `7` URL nguồn ngoài đều xuất hiện và khớp trích đoạn trong `research/2026-11-21-1438-cai-thien-qc-test-e2e.md` hoặc `raw/*.txt`.
- **`QC-I2` (Kiểm chéo `Claim <-> Source` chống `F6`):**
  - Đã đối chiếu trực tiếp toàn bộ con số định lượng trọng yếu trên đĩa trước khi khóa sổ: `8` biên bản (`659` dòng, `77,126` ký tự, `40/82` = `48.8%` meta/doc vs `10/82` = `12.2%` E2E), `28` lượt `tron-bo` (trung vị `1,190.11s`, `6/28` `INCOMPLETE`), `timing.jsonl` (`179` dòng; `17` lượt `full` có trung vị `implement=2,998.5s`, `qc=1,518.0s`), `222` `tests/` (`0` marker `smoke/e2e`), `scripts/tdq_test.py:104-105` và `scripts/tdq_test_receipt.py:29-30`.
- **`QC-I4` (Phân tầng độ tin cậy):**
  - `Verified`: `23` bản ghi bằng chứng gốc và `14` cụm khẳng định đo trực tiếp trong báo cáo.
  - `Single-source`: `1` bản ghi case study đơn lẻ (`EV-020` Instawork Testmon TIA `2x faster`) được gắn nhãn riêng trong `evidence.jsonl` và báo cáo.
  - `Inferred`: `7` vị trí gắn nhãn rõ cho phần suy luận thiết kế (`Auto Meta-Gate`, ẩn cột V2, dự phóng KPI mục tiêu trong Phần IV).

## 3. Kiểm tra `Zero-Code-Touch` & mục cố định `QC-F*`

- **`git diff --name-only dev..HEAD`:** `[]` (`0` tệp ngoài `docs/tdq/` & `docs/workinglog/`).
- **`git status --short`:** Toàn bộ tệp mới thuộc `docs/tdq/` và `docs/workinglog/2026-11-21.md`; riêng `docs/architecture/status.json` chỉ thay đổi dòng `"checked_at"` do hook archify kiểm từ đầu phiên, không thuộc chỉnh sửa mã nguồn của request.
- **`QC-F1` / `QC-F2` / `QC-F4`:** `KHÔNG ÁP DỤNG — không sửa file code` (request `work_kind = investigate`, `loai_request = docs`).
- **`QC-F3` (Ràng buộc Spec §5):** Giữ nguyên `Zero-Code-Touch`, gắn đủ `QC-I1`/`I2`/`I4`, giữ `5` chốt lõi TDQ dưới dạng tự động hóa ngầm (`EV-024`), báo cáo trung thực `lsp_bo_qua` và hạn mức `tavily-primary`.
