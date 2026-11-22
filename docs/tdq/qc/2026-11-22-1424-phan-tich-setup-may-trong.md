# QC — Nghiên cứu và thiết kế quy trình setup zero-to-full từ máy trống kèm tự động kiểm chứng sau restart
Ngày: 2026-11-22 · Plan: ../plan/2026-11-22-1424-phan-tich-setup-may-trong.md (Vòng 1 + fix `QC1.1`)
Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

## Dev Behavior QC Card
- Auto Meta-Gate: PASS (`2/2 checks, 0.19s` sau vòng fix `QC1.1`; `doc_lint` checked `12` file, `0` errors; `git_co_author` `0` errors)
- Luồng đổi: Thiết kế quy trình `tdq-setup` v2 hai cửa vào cho máy trống đa OS (`Windows`/`macOS`/`Linux`) kèm One-Shot Manifest Consent, state machine `${PLUGIN_DATA}/setup-state.json`, nhận diện restart qua `Host Session Fingerprint` ở `PreInvocation` và `Sandbox Simulate Test` 6 tầng (`work_kind=investigate`, không sửa mã nguồn).
- Chạy thử thật (Before → After + Bằng chứng tươi): Trước khi chạy `QC1.1`, `tdq_meta_gate.py` FAIL `1` lỗi `[R12]` ở `raw/EV-A02_hooks.md` do lưu docs tiếng Anh dưới đuôi `.md`. Sau khi sửa đổi 10 tệp `raw/EV-A*.txt`, `tdq_meta_gate.py` trả `PASS (2/2 checks, 0.19s)`; kiểm toàn vẹn `evidence.jsonl` (`20/20` bản ghi, `0` lỗi dòng biên, `0` mã mồ côi), thực nghiệm cô lập `TEMP` giữ nguyên `371/371` tệp `~/.gemini/config/` và `git diff dev...HEAD` có `0` tệp ngoài `docs/tdq/`.
- Rủi ro còn lại: Đây là request `investigate` chưa viết code sản phẩm; phép đo cây `Win32_Process` (`EV-C01`) chạy trực tiếp trên Windows 11, còn nhánh POSIX `/proc/<pid>/stat` và `ps` cần kiểm chứng thêm khi sang request triển khai code (`build`).

| # | Hạng mục | Lệnh đã chạy | Kết quả | PASS/FAIL |
|---|---|---|---|---|
| Q1 | Độ phủ 4 trụ cột thiết kế (`1a`, `2a`, `3a`, `4a`) & lộ trình triển khai | `py -3 -X utf8 -c "..."` kiểm `research/2026-11-22-1424-phan-tich-setup-may-trong.md` | Đủ 8 từ khóa kiến trúc + 4 đợt lộ trình triển khai | PASS |
| Q2 | Thực nghiệm cô lập dấu phiên & bảo toàn 100% `~/.gemini/config/` | Chạy probe `TEMP` + kiểm `axis-c-probes.md` và đếm tệp `~/.gemini/config/` | `Q2=True`, `cfg_before=371 == cfg_after=371`, `equal=True` | PASS |
| Q3 | Toàn vẹn `QC-I1` & `QC-I2`: `evidence.jsonl` & kiểm tra giới hạn dòng đĩa | Kiểm `20/20` mục `evidence.jsonl`, `raw_file`, `lines`, và tham chiếu `[EV-xxx]` | `20` bản ghi, `missing_raw=0`, `bad_bounds=0`, `orphan_refs=0` | PASS |
| Q4 | Phản biện `QC-I3` & gắn nhãn `QC-I4` (`4` góc khuất counterfactual) | Kiểm `Góc khuất 4` và nhãn `Verified`/`Inferred` trong `research/<slug>.md` | Đủ 4 góc khuất đối nghịch và gắn nhãn tin cậy tường minh | PASS |
| Q5 | Ranh giới kho sạch (`work_kind=investigate`) | `git diff --name-only dev...HEAD` & `git status --porcelain` | `0` tệp sửa ngoài `docs/tdq/` + `docs/workinglog/`, nhánh `main` giữ nguyên | PASS |
| Q6 | Chuẩn tài liệu 5 tệp & `Archify HTML` qua Tailscale Serve | `doc_lint.py` 5 tệp + `tdq_archify.py verify` + kiểm `HTTP 200` Tailscale HTTPS | `doc_lint` 0 lỗi; `binding.valid=True` (`status=current`); Tailscale `HTTP 200` (`SHA d47ec0f82c326a24`, `893673` bytes) | PASS |

## QC Cố định (`QC-F1`..`QC-F4`) & Hợp đồng skill
- **`QC-F1` (Meta-Gate & Suite):** `Auto Meta-Gate` **PASS** (`2/2 checks, 0.19s` sau `QC1.1`). Miễn `tdq_test.py tron-bo` theo `investigate-mode.md:15,58` vì `0` tệp code bị chạm ngoài `docs/tdq/`.
- **`QC-F2` (Hồi quy vùng chạm):** `KHÔNG CÓ CODE SỬA` — mọi tệp chạm đều là tài liệu/bằng chứng mới dưới `docs/tdq/`.
- **`QC-F3` (Ràng buộc kiến trúc `docs/kien-truc.md`):** ĐẠT — `0` tệp sửa ngoài `docs/tdq/` + `docs/workinglog/`; mọi đề xuất thiết kế giữ nguyên luật phân tầng `skills/` chỉ gọi `scripts/` và lưu state máy ở `${PLUGIN_DATA}` tách biệt `docs/tdq/state.json`.
- **`QC-F4` (Clean code):** `KHÔNG ÁP DỤNG — không sửa file code`.
- **Hợp đồng skill (`Kiểm:` trên `Dùng:`):** ĐẠT — `axis-a-lifecycle-os.md` (`7,502` bytes), `axis-c-probes.md` (`4,266` bytes), `axis-b-code-audit.md` (`7,424` bytes) đều tồn tại và vượt ngưỡng kích thước.

## Lệch spec chờ duyệt
không có

## Kết luận
PASS toàn bộ `Q1`–`Q6` (gồm `QC-I1`–`QC-I4` và `Auto Meta-Gate` 2/2 PASS sau vòng fix `QC1.1`). Báo cáo `Archify HTML` đã kiểm định `status=current` và phục vụ `HTTP 200` qua Tailscale Serve.
