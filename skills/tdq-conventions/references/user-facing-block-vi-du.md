# The user-facing block: the symbol table and a BEFORE/AFTER example
<!-- muc-luc-dong:
  The symbols allowed=12-30 · Examples=31-36 · Before (`Trước`)=37-56 · After (`Sau`)=57-81 ·
  Plain Narrative Report Contrast (1.jpg Style)=82
-->

Split out of `user-facing-block.md` on 2026-10-02 (965 tokens). Both parts are lookup material: the
symbol table is opened when you are unsure whether a mark is allowed; the example when you want to
compare the block you just wrote against a correct one. The rules themselves — the six components,
the eight laws, the hard rules — stay in the parent file.

## The symbols allowed

A block printed for the user may use exactly six non-ASCII symbols:

| Character | Codepoint | Used for |
|---|---|---|
| `➤` | U+27A4 | opens the answer-guidance line, always the last line |
| `·` | U+00B7 | separates two equal halves on one line |
| `—` | U+2014 | separates an explanation from the thing explained |
| `→` | U+2192 | points from one state to the next |
| `–` | U+2013 | joins the two ends of a range |
| `…` | U+2026 | cuts short a repeated part in an example |

A character outside the table must not be added, however harmless it looks. `▸` is excluded for
exactly that reason. It has never appeared in any string of this codebase, so there is no evidence
it renders correctly on all three surfaces. Box-drawing characters
(`─` `│` `├` `└` `┌` `┬` `┐`) are banned too: they demand column alignment, and terminal width
varies. The machine checks this with `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/scan_block_symbols.py" --chi-khoi`.

## Examples

The same content, differing only in decoration. The `Sau` version changes not one word of the
`Truoc` version — it only adds bold markers, backticks and line breaks. Both samples are written
in the default language (`doc_lang = vi`).

### Before (`Trước`) <!-- i18n-allow -->

<!-- i18n-allow — the "Trước" block is deliberately off-shape: it is the counter-example, not a template to copy. -->

```
Tôi đã viết xong spec cho yêu cầu của bạn.

Mục tiêu: <1–2 câu>.
Đầu ra chính: <gạch đầu dòng ngắn>.
Rủi ro đáng chú ý: <gạch đầu dòng ngắn>.

Xem đầy đủ tại: docs/tdq/spec/<slug>.md

---

**Bạn duyệt spec này chứ?**

➤ Duyệt: nhắn "duyệt spec" (duyệt xong tôi viết plan ngay) · Góp ý: nhắn trực tiếp
```

### After (`Sau`) <!-- i18n-allow -->

<!-- i18n-allow: khuôn mẫu viết bằng ngôn ngữ mặc định, chép nguyên văn khi doc_lang = vi -->

```
Tôi đã viết xong spec cho yêu cầu của bạn.

**Mục tiêu:** <1–2 câu>.
**Đầu ra chính:** <gạch đầu dòng ngắn>.
**Rủi ro đáng chú ý:** <gạch đầu dòng ngắn>.

Xem đầy đủ tại: `docs/tdq/spec/<slug>.md`

---

**Bạn duyệt spec này chứ?**

➤ Duyệt: nhắn "duyệt spec" (duyệt xong tôi viết plan ngay) · Góp ý: nhắn trực tiếp

---
```

The second `---` is component 6, the closing rule of the turn. The `Trước` version has only the
first one, which is part of what makes it the counter-example.

### Plain Narrative Report Contrast (1.jpg Style)

#### Compressed Counter-Example (Avoid)

<!-- i18n-allow: counter-example showing why middle-dot wall compression fails plain readability, not a template to copy -->
```
Đã xong request.
Trước request: mọi thứ chạy chung luồng build · dư R10/R14 · không có chốt team · mất telemetry khi approve.
Sau request: thêm work_kind · investigate-mode.md · evidence add/merge/render · khóa fcntl/NTFS · TDQ:DOC ở 40 điểm.
Đã test: tdq_test.py tron-bo · 4596 passed · 36 skipped · Q1-Q6 PASS.
➤ Duyệt: nhắn "commit"
```

#### Natural Narrative Showcase (Default)

<!-- i18n-allow: khuôn mẫu báo cáo tự nhiên viết bằng ngôn ngữ mặc định khi doc_lang = vi -->
```
Mọi thứ đã hoàn tất, test sạch toàn bộ hệ thống và sẵn sàng để bạn chốt merge. Tóm tắt ngắn gọn để bạn dễ nắm:

1. Trước và sau request có gì khác?

- **Trước đây:** Mọi việc điều tra lỗi đều bị ép đi chung quy trình dựng code nên dư nhiều bảng mẫu không cần thiết và thiếu chỗ gom bằng chứng an toàn.
- **Sau khi làm xong:** Hệ thống tách rạch ròi hai luồng xử lý ngay từ khâu mở request:
  - **Nhẹ ở đầu, sâu ở bước làm:** Giảm thủ tục thừa cho tác vụ điều tra, vẫn giữ lối nâng cấp khi chuyển sang vá lỗi.
  - **Giữ ngữ cảnh và an toàn:** Đồng bộ khóa ghi chép và giữ nguyên tốc độ đọc theo dải dòng (`14,35 ms`).
- **Kiểm tra & Kết quả:** Đã chạy toàn bộ bộ kiểm thử nền (`4.596` test đạt, `0` lỗi) và kiểm chứng độc lập đạt toàn bộ tiêu chuẩn.

Xem đầy đủ tại: `docs/tdq/reports/<slug>.md`

---

**Bạn muốn mình commit kết quả này không?**

➤ Trả lời: nhắn "commit" (hoặc "duyệt commit") nếu đồng ý · Chỉnh sửa: nhắn trực tiếp

---
```
