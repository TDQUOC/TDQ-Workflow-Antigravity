# PLAN — Phân tích độ chi tiết của Plan cho Model Tier Thấp (End-to-End) và Đề xuất Cải thiện TDQ Workflow

Ngày: 2026-11-19 · Spec: ../spec/2026-11-19-2213-chi-tiet-plan-model-thap.md (bản 1.0, ĐÃ DUYỆT) · Lane: full
Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md
Mode thực thi: main — tdq_bench.py simulate thắng 3.1 phút trên 9 task / 7 đợt (chỉ Đợt 3 có 3 luồng Red-Team chạy song song; lưu ý user có thể chọn subagent ở mode gate theo yêu cầu fanout) (ĐỀ XUẤT, user chốt lúc duyệt)
Trạng thái plan: HOÀN THÀNH

## Mục lục

- Quy tắc thi hành (áp cho mọi task)
- Thiết kế Trước vs Sau
- P1 — Vòng 1: Kiểm chứng Thực nghiệm & Giải phẫu Nguyên nhân gốc
- P2 — Vòng 1: Thiết kế Đề xuất Kiến trúc 3 Lớp Phiên bản V1
- P3 — Vòng 2: Fanout 3 Luồng Red-Team Độc lập & Tổng hợp Phản biện
- P4 — Chốt Đề xuất V2, Báo cáo 4 Phần & Archify HTML
- P5 — Log & kiểm định bắt buộc
- Cụm song song
- Luật file nóng
- Definition of Done

## Quy tắc thi hành (áp cho mọi task)

1. Thứ tự phase và khóa `Cần:` là thứ tự phụ thuộc — không đảo.
2. Mỗi task: đánh `[~]` khi bắt đầu → thực hiện kiểm chứng / viết nội dung → chạy lệnh Test ở cuối dòng tiêu đề → đổi sang `[x]` NGAY vào file này. Trạng thái checkbox: `[ ]` chưa làm · `[~]` đang làm · `[x]` xong.
3. Không sửa bất kỳ file mã nguồn, skill, agent, hook, test hoặc plugin cục bộ nào ngoài thư mục tài liệu (`loai_request=docs`).
4. Mọi trích dẫn đường dẫn mã nguồn `path:line` phải đối chiếu trực tiếp với file thật trên nhánh `docs/chi-tiet-plan-model-thap`.
5. QC FAIL → thêm task fix vào mục QC của file này (không cần duyệt lại), loop đến khi pass.
6. Không commit/push cho đến khi user yêu cầu.
7. Tuân thủ 6 mã cấm cơ học (ANTI-1 Fake Red, ANTI-2 Blind Assertion, ANTI-3 Dirty State Git, ANTI-4 Late Tick, ANTI-5 Raw Dump, ANTI-6 Broad Area).

## Thiết kế Trước vs Sau

*Đối chiếu sơ đồ kiến trúc:* Tham chiếu Archify preview đã duyệt và gắn SHA-256 tại `docs/tdq/spec/2026-11-19-2213-chi-tiet-plan-model-thap-preview.html` và manifest `docs/tdq/spec/2026-11-19-2213-chi-tiet-plan-model-thap-preview.manifest.json`. Toàn bộ phân tích và đề xuất đều chiếu theo `spec` §2c, §3c, §6 đã duyệt.

| Khía cạnh | Hiện trạng (Trước) | Thiết kế đề xuất mục tiêu (Sau — End-to-End `2b` + `3a`) |
|---|---|---|
| Đầu viết Plan (Planner) | Hướng dẫn ở thân `SKILL.md` (`121/121` dòng) không nhắc Task Block; model tự viết `9` trường theo trí nhớ → `20.8%` đạt chuẩn, mega-task `>= 4` file tăng `2.8×` | Phân rã cơ học `3` bước cho Weak Planner (Trích symbol/AST tự động → Khung task nguyên tử `<= 3` file → Điền Structural Contract có kiểm chứng) |
| Cấu trúc Task Block | Thiếu Trước → Sau mức task (`58.3%`), thiếu Test Oracle (`37.5%`), thiếu neo dòng (`60.9%`); dễ rơi vào "Task Block Theater" | Executable Task Card chuẩn **Structural Contract**: Neo theo Symbol + Công nghệ/Signature + Trước → Sau (Input/State → Output/State) + Giải thuật `<= 5–7` bước + Ca hiểm + Locked Test Oracle (`input → assert`), cấm chép body dài |
| Parser & Giao việc | Bug parser ở `tdq_team.py` quét đường dẫn mọi dòng làm nhiễm vùng ghi; leader tự ghép tay packet cho `flash` không có LSP | Sửa parser cô lập riêng `Chạm:` khỏi tham chiếu; Auto Task Packet Builder bơm đủ contract + trích đoạn vùng neo + bất biến `kien-truc.md` |
| Cổng kiểm soát | `R15` chỉ dò `1` từ khóa (`logic`), bỏ sót `QCn.x`/`quick-lane`/`doc_lang=en`, không chạy ở `--pair`, không chặn ở `approve plan` | Nâng cấp `R15` kiểm cấu trúc + giới hạn mega-task + mốc `R15_MOC`; gắn hard-gate tại `--pair` và `approve plan`; cập nhật checklist cho reviewer |

## P1 — Vòng 1: Kiểm chứng Thực nghiệm & Giải phẫu Nguyên nhân gốc

- [x] **T1.1** (e12m) Tổng hợp Báo cáo Kiểm chứng Nhận định & Giải phẫu Nguyên nhân gốc (Vòng 1) — Test: `py -3 -X utf8 scripts/doc_lint.py docs/tdq/artifacts/2026-11-19-2213-chi-tiet-plan-model-thap/phan-tich-vong-1.md && py -3 -c "import pathlib; t=pathlib.Path('docs/tdq/artifacts/2026-11-19-2213-chi-tiet-plan-model-thap/phan-tich-vong-1.md').read_text(encoding='utf-8'); assert all(k in t for k in ['236','20.8%','58.3%','Weak Planner','Weak Executor','Skeleton Coding','IFScale'])"`
  - Chạm: `docs/tdq/artifacts/2026-11-19-2213-chi-tiet-plan-model-thap/phan-tich-vong-1.md`
  - Mục tiêu: Đóng gói trọn vẹn bằng chứng thực nghiệm Vòng 1 khẳng định nhận định của người dùng và giải phẫu ranh giới ảnh hưởng lên cả 2 đầu Weak Planner lẫn Weak Executor.
  - Yêu cầu nội dung: Đủ bảng điểm 7 chiều trên `48` task / `236` plan (trước và sau `2026-11-11`), tổng hợp đối chiếu `4` cặp spec–plan (`60%` thiếu ở cả hai, `25%` rơi rớt khi sang plan, `15%` ảo giác từ spec truyền sang), `>= 7` nguyên nhân gốc kèm trích dẫn đường dẫn và số dòng đã xác minh, `6` mẫu trích dẫn lỗi thực tế đối xứng với `3` mẫu đạt chuẩn (`14/14`), và đối chiếu bằng chứng khoa học ngoài.

**Xong P1 khi**: File `phan-tich-vong-1.md` đạt `doc_lint.py` 0 lỗi và kiểm Python đủ 7 chỉ dấu thực nghiệm + khoa học.

## P2 — Vòng 1: Thiết kế Đề xuất Kiến trúc 3 Lớp Phiên bản V1

- [x] **T2.1** (e15m) Xây dựng Bản Đề xuất Thiết kế Kiến trúc 3 Lớp Phiên bản V1 cho mô hình End-to-End (`2b` + `3a`) — Test: `py -3 -X utf8 scripts/doc_lint.py docs/tdq/artifacts/2026-11-19-2213-chi-tiet-plan-model-thap/de-xuat-v1.md && py -3 -c "import pathlib; t=pathlib.Path('docs/tdq/artifacts/2026-11-19-2213-chi-tiet-plan-model-thap/de-xuat-v1.md').read_text(encoding='utf-8'); assert all(k in t for k in ['Lớp 1','Lớp 2','Lớp 3','Weak Planner','Weak Executor','R15_MOC'])"`
  - Chạm: `docs/tdq/artifacts/2026-11-19-2213-chi-tiet-plan-model-thap/de-xuat-v1.md`
  - Cần: T1.1
  - Mục tiêu: Đề xuất bản thiết kế V1 hoàn chỉnh để Red-Team Vòng 2 phản biện, giải quyết cả 2 đầu Weak Planner và Weak Executor trên 3 lớp theo `1a 2b 3a`.
  - Yêu cầu nội dung: Đặc tả rõ **Lớp 1 (Skill/Template/Agent)**: quy trình `3` bước cơ học cho Weak Planner, schema **Executable Task Card** (giữ cột 0 `- [ ] **Tx.y**`, giới hạn `<= 3` file/task, `<= 5–7` luật cục bộ, bắt buộc Trước → Sau, Công nghệ/Signature, Giải thuật, Ca hiểm, Locked Test Oracle, cấm chép body dài), phương án thoát trần `121` dòng / `3,500` token (`R6`/`R13`), phủ cả `quick-lane` lẫn `QC fix task`; **Lớp 2 (Tooling & Automation)**: thuật toán vá `tdq_team.py` cô lập `Chạm:` khỏi `Tham chiếu:`, Weak-Planner Symbol Scaffolder, và Auto Task Packet Builder cho `flash` không LSP; **Lớp 3 (Hard Gates)**: nâng cấp `R15` kiểm cấu trúc + chống mega-task + mốc `R15_MOC` + cổng `doc_lint --pair` + `approve plan`, đồng bộ checklist reviewer và implementer.

**Xong P2 khi**: File `de-xuat-v1.md` đạt `doc_lint.py` 0 lỗi và chứa đầy đủ đặc tả 3 lớp cho cả 2 đầu `2b`.

## P3 — Vòng 2: Fanout 3 Luồng Red-Team Độc lập & Tổng hợp Phản biện

- [x] **T3.1** (e12m) Chạy Red-Team A (subagent đọc-chỉ): Phản biện Nhận thức Model Nhỏ & Rủi ro Weak Planner — Test: `py -3 -X utf8 scripts/doc_lint.py docs/tdq/artifacts/2026-11-19-2213-chi-tiet-plan-model-thap/redteam-a-nhan-thuc.md && py -3 -c "import pathlib; t=pathlib.Path('docs/tdq/artifacts/2026-11-19-2213-chi-tiet-plan-model-thap/redteam-a-nhan-thuc.md').read_text(encoding='utf-8'); assert t.count('### Nhược điểm') >= 3"`
  - Chạm: `docs/tdq/artifacts/2026-11-19-2213-chi-tiet-plan-model-thap/redteam-a-nhan-thuc.md`
  - Cần: T2.1
  - Mục tiêu: Đánh giá đối kháng bản V1 dưới góc độ ngân sách chú ý (IFScale exponential decay, Context Rot), rủi ro plan drift giữa các wave và khả năng tự điền sai/bỏ sót của Weak Planner.
  - Yêu cầu nội dung: Chỉ ra tối thiểu `3` nhược điểm cụ thể của V1 (kèm trích dẫn từ `de-xuat-v1.md` và nghiên cứu khoa học ngoài), phân loại mức độ nghiêm trọng (`Cao`/`Trung bình`/`Thấp`) và đề xuất cơ chế giảm tải nhận thức.

- [x] **T3.2** (e12m) Chạy Red-Team B (subagent đọc-chỉ): Phản biện Xung đột Hệ thống, Linter, Parser & Tương thích Ngược TDQ — Test: `py -3 -X utf8 scripts/doc_lint.py docs/tdq/artifacts/2026-11-19-2213-chi-tiet-plan-model-thap/redteam-b-rang-buoc-tdq.md && py -3 -c "import pathlib; t=pathlib.Path('docs/tdq/artifacts/2026-11-19-2213-chi-tiet-plan-model-thap/redteam-b-rang-buoc-tdq.md').read_text(encoding='utf-8'); assert t.count('### Nhược điểm') >= 3"`
  - Chạm: `docs/tdq/artifacts/2026-11-19-2213-chi-tiet-plan-model-thap/redteam-b-rang-buoc-tdq.md`
  - Cần: T2.1
  - Mục tiêu: Soi từng hạng mục trong V1 đối chiếu với toàn bộ luật cứng, parser và ràng buộc biên dịch của TDQ Workflow hiện tại để bắt lỗi gãy ngầm trước khi triển khai.
  - Yêu cầu nội dung: Kiểm tra V1 qua R1–R15 (đặc biệt R6 `121` dòng, R13 `3,500` token, R8 `8` dòng, R12 văn xuôi tiếng Việt), `tdq_team.py` (projection v1, `canh_bao_lach_luat`, cột 0), `storage.rs` của Rust, `tdq_eval.py`, và pipeline build plugin AGY (`tools/patches/`), chỉ ra tối thiểu `3` xung đột thực tế có trích dẫn mã nguồn.

- [x] **T3.3** (e14m) Chạy Red-Team C (subagent stress-test): Viết lại Trước → Sau 3 Ca Thất bại Thật theo V1 & Chấm Điểm Thực chiến — Test: `py -3 -X utf8 scripts/doc_lint.py docs/tdq/artifacts/2026-11-19-2213-chi-tiet-plan-model-thap/redteam-c-stress-test.md && py -3 -c "import pathlib; t=pathlib.Path('docs/tdq/artifacts/2026-11-19-2213-chi-tiet-plan-model-thap/redteam-c-stress-test.md').read_text(encoding='utf-8'); assert all(k in t for k in ['11-19-0046','11-19-1632','11-19-1457']) and t.count('### Ma sát') >= 3"`
  - Chạm: `docs/tdq/artifacts/2026-11-19-2213-chi-tiet-plan-model-thap/redteam-c-stress-test.md`
  - Cần: T2.1
  - Mục tiêu: Kiểm chứng thực chiến xem mẫu Task Card của V1 có viết được mượt trên chính `3` ca thất bại thật hay gây rườm rà, vỡ cột 0 hoặc tụt điểm 7 chiều.
  - Yêu cầu nội dung: Viết lại Trước → Sau đầy đủ `3` ca (`2026-11-19-0046:T2.3`, `2026-11-19-1632:T2.1` + `QC1.1`, `2026-11-19-1457`), đo số dòng & ước lượng token mỗi thẻ, chấm lại bảng điểm `7` chiều (`0..14`), và ghi tối thiểu `3` ma sát/nhược điểm phát sinh khi viết thật.

- [x] **T3.4** (e8m) Tổng hợp Báo cáo Phản biện Red-Team Vòng 2 & Ma trận Nhược điểm V1 → Vá V2 — Test: `py -3 -X utf8 scripts/doc_lint.py docs/tdq/artifacts/2026-11-19-2213-chi-tiet-plan-model-thap/phan-bien-vong-2.md && py -3 -c "import pathlib; t=pathlib.Path('docs/tdq/artifacts/2026-11-19-2213-chi-tiet-plan-model-thap/phan-bien-vong-2.md').read_text(encoding='utf-8'); assert t.count('| ND-') >= 6"`
  - Chạm: `docs/tdq/artifacts/2026-11-19-2213-chi-tiet-plan-model-thap/phan-bien-vong-2.md`
  - Cần: T3.1, T3.2, T3.3
  - Mục tiêu: Hội tụ kết quả của cả `3` luồng Red-Team A/B/C, khử trùng lặp, xếp hạng ưu tiên và chốt bảng truy vết tối thiểu `6` nhược điểm V1 sang phương án vá V2.
  - Yêu cầu nội dung: Bảng hợp nhất các phát hiện `ND-1`..`ND-N` (`>= 6` nhược điểm thực chất có mức độ nghiêm trọng và bằng chứng nguồn từ A/B/C), kèm đặc tả phương án khắc phục cụ thể cho từng mã `ND-i`.

**Xong P3 khi**: Toàn bộ `4` tài liệu Vòng 2 đạt `doc_lint.py` 0 lỗi, có đủ `>= 6` nhược điểm `ND-i` đã đối chiếu và `3/3` ca stress-test Trước/Sau hoàn chỉnh.

## P4 — Chốt Đề xuất V2, Báo cáo 4 Phần & Archify HTML

- [x] **T4.1** (e12m) Biên soạn Báo cáo Nghiệm thu 4 Phần & Đề xuất Hoàn chỉnh V2 (kèm 3 Ví dụ Trước/Sau đạt `>= 12/14` & Lộ trình Triển khai) — Test: `py -3 -X utf8 scripts/doc_lint.py docs/tdq/reports/2026-11-19-2213-chi-tiet-plan-model-thap.md && py -3 -c "import pathlib; t=pathlib.Path('docs/tdq/reports/2026-11-19-2213-chi-tiet-plan-model-thap.md').read_text(encoding='utf-8'); assert all(k in t for k in ['Trước request','Sau request','Đã test','Kết quả test','ND-1'])"`
  - Chạm: `docs/tdq/reports/2026-11-19-2213-chi-tiet-plan-model-thap.md`
  - Cần: T3.4
  - Mục tiêu: Hoàn thiện tài liệu đầu ra chính phục vụ người dùng duyệt kiến trúc: kết hợp đầy đủ kết luận kiểm chứng, thiết kế V2 đã vá 100% nhược điểm Vòng 2, `3` cặp ví dụ Trước/Sau đạt `>= 12/14`, lộ trình triển khai phân chặng và `4` phần báo cáo chuẩn TDQ.

- [x] **T4.2** (e6m) Soạn Đặc tả Archify và Xuất bản Báo cáo Archify HTML qua Tailscale Serve — Test: `py -3 -X utf8 scripts/tdq_archify.py verify --document docs/tdq/reports/2026-11-19-2213-chi-tiet-plan-model-thap.md --manifest docs/tdq/reports/2026-11-19-2213-chi-tiet-plan-model-thap.manifest.json && py -3 -c "import urllib.request; assert urllib.request.urlopen('https://unity-pc-rtx3060.tail99896.ts.net/vlog/tdq-workflow-agy/reports/2026-11-19-2213-chi-tiet-plan-model-thap.html', timeout=5).status == 200"`
  - Chạm: `docs/tdq/artifacts/2026-11-19-2213-chi-tiet-plan-model-thap/bao-cao.archify.md`, `docs/tdq/reports/2026-11-19-2213-chi-tiet-plan-model-thap.html`
  - Cần: T4.1
  - Mục tiêu: Render trực quan hóa kiến trúc 3 lớp V2 (Weak Planner + Weak Executor) và luồng 2 vòng phản biện sang Archify HTML sạch lỗi, gắn manifest `current` và xác minh HTTP `200` qua Tailscale Serve.

**Xong P4 khi**: Báo cáo Markdown đạt `doc_lint.py` 0 lỗi, Archify manifest ở trạng thái `current` (`valid=true`) và liên kết Tailscale Serve trả về `HTTP 200`.

## P5 — Log & kiểm định bắt buộc

Log: BỎ — yêu cầu này thuộc loại docs (chỉ tạo tài liệu phân tích 2 vòng, đề xuất thiết kế và báo cáo Archify HTML, không tạo hoặc sửa mã nguồn chạy được).

- [x] **T5.1** (e6m) Chạy Kiểm định QC mức `full` Toàn diện (Lint, Integrity đường dẫn, 0 code ngoài `docs/`, Kiểm chéo `Q1–Q5`) — Test: `py -3 -X utf8 scripts/doc_lint.py docs/tdq/qc/2026-11-19-2213-chi-tiet-plan-model-thap.md docs/tdq/reports/2026-11-19-2213-chi-tiet-plan-model-thap.md`
  - Chạm: `docs/tdq/qc/2026-11-19-2213-chi-tiet-plan-model-thap.md`
  - Cần: T4.2
  - Mục tiêu: Đóng dấu kiểm định `full` xác nhận `Q1–Q5` đều đạt PASS với bằng chứng chạy thật trên đĩa (không có thay đổi code/skill ngoài `docs/`, mọi trích dẫn `path:line` hợp lệ, toàn bộ `.md` mới pass `doc_lint.py`).

**Xong P5 khi**: Biên bản QC `docs/tdq/qc/2026-11-19-2213-chi-tiet-plan-model-thap.md` xác nhận `5/5` tiêu chí `Q1–Q5` PASS và `git status` chỉ có thay đổi trong `docs/`.

## Cụm song song

- **Đợt 1 (`T1.1`):** Viết báo cáo phân tích & giải phẫu nguyên nhân gốc Vòng 1.
- **Đợt 2 (`T2.1`, sau `T1.1`):** Xây dựng bản đề xuất thiết kế 3 lớp V1 cho mô hình End-to-End `2b`.
- **Đợt 3 (`T3.1 || T3.2 || T3.3`, sau `T2.1` — `3` cụm song song hoàn toàn không giao vùng ghi):**
  - Nhánh A (`T3.1`): Red-Team A phản biện nhận thức model nhỏ & Weak Planner.
  - Nhánh B (`T3.2`): Red-Team B phản biện ràng buộc kỹ thuật & tương thích ngược TDQ.
  - Nhánh C (`T3.3`): Red-Team C stress-test thực chiến `3` ca thất bại thật Trước → Sau.
- **Đợt 4 (`T3.4`, sau `T3.1, T3.2, T3.3`):** Hợp nhất Vòng 2 & chốt ma trận `ND-i` → V2.
- **Đợt 5 (`T4.1`, sau `T3.4`):** Biên soạn báo cáo & Đề xuất Hoàn chỉnh V2.
- **Đợt 6 (`T4.2`, sau `T4.1`):** Render & xác minh Archify HTML + Tailscale Serve.
- **Đợt 7 (`T5.1`, sau `T4.2`):** Chạy kiểm định QC mức `full` và ghi biên bản QC.

## Luật file nóng

Không có FILE NÓNG nào trong plan này — tất cả `9` task ghi vào `10` đường dẫn hoàn toàn tách biệt (mỗi file dưới `docs/tdq/` có đúng `1` chủ ghi duy nhất).

## Definition of Done

- [x] Q1 Bằng chứng thực nghiệm Vòng 1: `phan-tich-vong-1.md` có đủ bảng 7 chiều trên 48 task / 236 plan và >= 7 nguyên nhân gốc kèm trích dẫn xác minh trên đĩa — `py -3 -X utf8 scripts/doc_lint.py docs/tdq/artifacts/2026-11-19-2213-chi-tiet-plan-model-thap/phan-tich-vong-1.md`
- [x] Q2 Độ phủ thiết kế 3 lớp V1 cho 2b: `de-xuat-v1.md` đặc tả đủ 2 đầu (Weak Planner + Weak Executor) và đủ 3 lớp (Skill/Template/Agent + vá parser/Scaffolder/Auto-Packet + R15/approve plan) — `py -3 -X utf8 scripts/doc_lint.py docs/tdq/artifacts/2026-11-19-2213-chi-tiet-plan-model-thap/de-xuat-v1.md`
- [x] Q3 Phản biện độc lập Vòng 2: đủ 3 báo cáo Red-Team A/B/C độc lập và bảng tổng hợp >= 6 nhược điểm V1 ánh xạ 100% sang bản vá V2 — `py -3 -X utf8 scripts/doc_lint.py docs/tdq/artifacts/2026-11-19-2213-chi-tiet-plan-model-thap/phan-bien-vong-2.md`
- [x] Q4 Kiểm chứng 3 cặp ví dụ Trước/Sau: cả 3/3 bản Sau đạt >= 12/14 trên bảng 7 chiều và tuân thủ cấu trúc cột 0 + thụt lề — `py -3 -c "import pathlib; t=pathlib.Path('docs/tdq/reports/2026-11-19-2213-chi-tiet-plan-model-thap.md').read_text(encoding='utf-8'); assert all(k in t for k in ['11-19-0046','11-19-1632','11-19-1457','12/14'])"`
- [x] Q5 Tài liệu sạch, 0 sửa ngoài docs/ và Archify HTML current qua Tailscale: kiểm toàn bộ `.md` mới, kiểm `git diff --name-only` và xác minh Archify + HTTP 200 — `py -3 -X utf8 scripts/tdq_archify.py verify --document docs/tdq/reports/2026-11-19-2213-chi-tiet-plan-model-thap.md --manifest docs/tdq/reports/2026-11-19-2213-chi-tiet-plan-model-thap.manifest.json`
