# The plan shape
<!-- muc-luc-dong:
  The minute estimate `(eNm)`=122
-->

Copy the whole block into `docs/tdq/plan/<slug>.md` and fill it in. File em:
Read [planner-rules.md](planner-rules.md) (`<= 30` invariants) and [plan-examples.md](plan-examples.md) before drafting.
Read [plan-template-co-che.md](plan-template-co-che.md) (conditional sections) and
[plan-template-huong-dan.md](plan-template-huong-dan.md) (`eNm`, Adaptive 3-Tier, `Mode thực thi`). <!-- i18n-allow -->

<!-- i18n-allow: plan template written in the default document language -->
```markdown
# PLAN — <tên việc>

Ngày: YYYY-MM-DD · Spec: ../spec/<slug>.md (bản 1.0, ĐÃ DUYỆT) · Lane: full
Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md
Mode thực thi: <main|subagent|codex> — <lý do 1–2 câu> (ĐỀ XUẤT, user chốt lúc duyệt)
Trạng thái plan: CHỜ DUYỆT

## Mục lục

- Phân bổ Model & Effort
- Quy tắc thi hành (áp cho mọi task)
- Thiết kế Trước vs Sau (khi bổ sung hoặc refactor)
- P1 — <tên phase>
- P2 — <tên phase>
- Cụm song song
- Luật file nóng (một file, nhiều task chạm)
- Khuôn khối hợp đồng skill (đặt NGAY DƯỚI dòng task dùng skill đó, ≤6 dòng)
- Px — Log & test bắt buộc
- Definition of Done

## Phân bổ Model & Effort
<!-- i18n-allow: canonical model/effort plan allocation table -->
> User được quyền đổi `type model` hoặc `effort` lúc duyệt plan. Thang model: [subagent-tuning.md](../../tdq-conventions/references/subagent-tuning.md).

| Pha | Vai trò | Model | Effort | Ghi chú |
|---|---|---|---|---|
| `implement / qc / report` | `<vai trò>` | `<gemini-3.8-flash..4-carbon / inherit>` | `<low..xhigh>` | `<quyền đổi / leo thang>` |

## Quy tắc thi hành (áp cho mọi task)
1. Thứ tự phase là thứ tự phụ thuộc — không đảo.
2. Mỗi task: đánh `[~]` khi bắt đầu → viết test trước (đỏ) → code → test xanh → đổi sang
   `[x]` NGAY vào file này. Trạng thái checkbox: `[ ]` chưa làm · `[~]` đang làm · `[x]` xong.
3. Mỗi bước: `tdq_test.py vung-cham`; trọn bộ chỉ ở QC.
4. Lệnh nào chạm state của workflow phải có `TDQ_PROJECT_DIR=<thư mục tạm>` ngay trên chính lệnh đó.
5. QC FAIL → thêm task fix vào mục QC của file này (không cần duyệt lại), loop đến khi pass.
6. Không commit/push cho đến khi user yêu cầu.
7. Tuân thủ 6 mã cấm cơ học (ANTI-1 Fake Red, ANTI-2 Blind Assertion, ANTI-3 Dirty State Git, ANTI-4 Late Tick, ANTI-5 Raw Dump, ANTI-6 Broad Area).

## Thiết kế Trước vs Sau (áp dụng khi Refactor hoặc bổ sung tính năng)
| Khía cạnh | Hiện trạng (Trước) | Thiết kế mới (Sau) |
|---|---|---|
| Luồng thực thi | <mô tả luồng cũ> | <mô tả luồng mới tối ưu> |
| Thành phần chạm | <danh sách thành phần cũ> | <thành phần mới / thay thế> |

*Đối chiếu sơ đồ kiến trúc:* Khi spec có Archify preview, tham chiếu lại HTML và manifest đã duyệt. WBS ánh xạ task tới node, boundary, quy tắc và tiêu chí nghiệm thu; không sinh bản thiết kế khác trong plan. Kiểm binding trước code; thay đổi thiết kế thì dùng lại cổng duyệt spec hiện có.

## Ràng buộc toàn cục & Bản đồ Sở hữu Hợp đồng (Ownership Map)

- Ngôn ngữ: English comments/CLI · `utf8_io` · `TDQ_LOG=0` tắt log · hàm `<= 50` dòng (`cyc <= 10`, `cog <= 15`) · `GIỮ NGUYÊN` chữ ký cũ trừ khi task nêu rõ.

| Hợp đồng / Ký hiệu (§3c) | File & Task sở hữu | Task / File tiêu thụ |
|---|---|---|
| `<symbol_or_schema>` | `<owner_file>` (`T1.1`) | `<consumers>` |

## P1 — <tên phase>
<!-- i18n-allow: mẫu Per-Task Mini-Spec (tối đa 30 dòng/task, cứng 35) -->
- [ ] **T1.1** (e6m) <việc cụ thể> — Test: `<lệnh test đích>`
  - Req: `<§mục spec>` · Ngoài phạm vi: `GIỮ NGUYÊN` `<bất biến>`
  - Chạm: `<src/file.py>`
  - Cần: `<mã task hoặc Không>`
  - Giao tiếp: Consumes: `<input/hợp đồng>` | Produces: `<hàm/schema>`
  - Neo & Công cụ: `Edit` trên `<file>` tại `<hàm neo()>` (hoặc `Write` cho file mới)
  - Trước → Sau: `<trạng thái cũ> → <trạng thái mới>`
  - Tiêu chí chấp nhận (EARS): KHI `<điều kiện>`, HỆ THỐNG PHẢI `<kết quả>`
  - Logic cốt lõi: <1–3 gạch đầu dòng ngắn hoặc pseudo-code>
  - Ca góc hiểm & Assert: `<biên null/rỗng/lỗi>` · `assert <thực_tế> == <kỳ_vọng>` (cấm `ANTI-2`)
- [ ] **T1.2** (e12m) <việc cụ thể> — Test: <...>

**Xong P1 khi**: <điều kiện đo được>

## P2 — <tên phase>
- [ ] **T2.1** (e20m) <...> — Test: <...>

## Cụm song song

Mục này BẮT BUỘC có trong mọi plan (kể cả một cụm: ghi rõ lý do). Chi tiết: [plan-template-co-che.md](plan-template-co-che.md).

## Luật file nóng (một file, nhiều task chạm)

Đường dẫn bị từ 2 task trở lên khai ở `Chạm:` là FILE NÓNG. Chọn một trong hai cách: **nâng lên đợt sớm** (mặc định) hoặc **một chủ ghi duy nhất**. Chi tiết: [plan-template-co-che.md](plan-template-co-che.md).

## Khuôn khối hợp đồng skill (đặt NGAY DƯỚI dòng task dùng skill đó, ≤6 dòng)
- [ ] **T<x.y>** <việc của task> — Test: <...>
  - Dùng: `<tên skill>`
  - Để: <việc cụ thể skill lo>, nạp skill TRƯỚC bước đỏ
  - Ra: <artifact phải tồn tại sau task, có đường dẫn>
  - Kiểm: <một lệnh chạy được, PASS đo được>
  - Không dùng cho: <việc kề bên mà skill này KHÔNG được lan sang>

Skill cần MCP tool lúc chạy → dòng `Dùng:` phải kết thúc bằng nhãn ` (mcp)` NGOÀI backtick. Năm
trường và luật nhãn đầy đủ (gồm MCP-First): mục `Khuôn khối hợp đồng skill` của
[plan-template-co-che.md](plan-template-co-che.md).
## Px — Log & test bắt buộc
Phase này bắt buộc **chỉ khi việc này có runtime** — tức có ít nhất một task tạo hoặc sửa
file mã nguồn chạy được. Không có runtime (chỉ sửa tài liệu, khuôn mẫu, cấu hình) → bỏ
task log, giữ task test, và ghi đúng một dòng `Log: BỎ — <lý do một câu>`.

- [ ] **Tx.1** Log service bật mặc định (timestamp, mức log, tắt được qua config) — Test: <...>
- [ ] **Tx.2** Unit test cho từng thành phần, chạy bằng một lệnh — Test: <lệnh>

## Definition of Done
Trỏ về §6 của spec. Liệt kê lại từng hạng mục QC + lệnh kiểm, MỖI DÒNG MỘT Ô TICK:

- [ ] Q1 <điều kiện đủ> — <lệnh kiểm>
- [ ] Q2 <điều kiện đủ> — <lệnh kiểm>
```

Mark `[x]` when that item PASSes and evidence sits in the qc file. Hook `Stop` checks these boxes via `[TDQ:DOD]`.

## The minute estimate `(eNm)`

Goes **right after the task code**: `- [ ] **T2.1** (e12m) <work> — Test: ...`. `eNm` = estimated minutes to execute (integer 1–999). Details in [plan-template-huong-dan.md](plan-template-huong-dan.md).
