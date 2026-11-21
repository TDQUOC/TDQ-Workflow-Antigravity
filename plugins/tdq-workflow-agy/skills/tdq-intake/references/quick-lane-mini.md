# Mini spec/plan and approval block

The mini spec/plan is written in the default document language; when `doc_lang` is not `vi`,
translate headings and labels while preserving the shape. <!-- i18n-allow: canonical Vietnamese section name below -->

```markdown
# QUICK — <tên việc>

**Ngày:** YYYY-MM-DD · Brief: ../brief/<slug>.md · Lane: quick
**Trạng thái:** CHỜ DUYỆT
**Ước tính sẽ dùng skill:** <skill sẽ DÙNG, hoặc "không có">

> **Tóm tắt dễ hiểu:** <1–2 câu đời thường: trước vướng gì → nay sửa gì → xong ra kết quả gì>.

## Phạm vi
- Trong: <gạch đầu dòng>
- NGOÀI: <gạch đầu dòng>

## Task
- [ ] **T1** (e6m) <việc cụ thể> — Test: <lệnh hoặc tiêu chí pass>
  - Chạm: `<src/file.py>` (code task dùng `R15-Compact`; nếu `> 4` file nguồn → lên `full`)
  - Neo & Công cụ: `edit_file` trên `<file>` tại `<hàm neo()>` (hoặc `write_file` tạo file mới)
  - Trước → Sau: `<trạng thái cũ> → <trạng thái mới>`
  - Tiêu chí & Assert: `<cụ thể> · assert <thực_tế> == <kỳ_vọng>` (cấm `ANTI-2`)
- [ ] **T2** <việc cụ thể> — Test: <lệnh>

## Definition of Done
- <điều kiện đo được, có lệnh kiểm>
```

Going past 40 lines (`<= 65` lines for `work_kind=investigate` mini-plans, `<= 80` lines for `R15-Compact` code mini-plans, or `> 4` source files) means this work is no longer quick — say so to the user and propose moving to the deep pipeline. Notice `work_kind=investigate` follows Tier 0–3 fan-out & waives pre-approval Archify per [investigate-mode.md](../../tdq-conventions/references/investigate-mode.md).

Per [user-facing-block.md](../../tdq-conventions/references/user-facing-block.md), present it with
all 5 components, the approval block at the end of the message, and no emoji:

<!-- i18n-allow: sample block written in the default language -->
```
Mình đã lên kế hoạch gọn cho yêu cầu của bạn. Tóm tắt dễ hiểu:

**Trước đây → Sau khi làm xong:** <1–2 câu đời thường nêu thay đổi cốt lõi và kết quả mong đợi>.
**Sẽ làm:** <gạch đầu dòng ngắn theo việc thực tế làm được>.
**Đụng tới & Kiểm:** <khu vực/file> — kiểm bằng <lệnh hoặc tiêu chí đo>.
**Ước tính sẽ dùng skill:** <skill sẽ DÙNG, hoặc "không có">.

Xem đầy đủ tại: `docs/tdq/plan/<slug>.md`

---

**Bạn duyệt để mình làm luôn chứ?**

➤ Duyệt: nhắn "duyệt nhanh" kèm mức QC (vd "duyệt nhanh, QC full"); "duyệt quick" vẫn chạy — duyệt xong mình làm ngay · Góp ý: nhắn trực tiếp

---
```
