# BRIEF — Triển khai kiến trúc mặc định trình bày 2 tầng vào TDQ-Workflow
Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

## Nguyên văn

> commit và mở request triển khai đề xuất này vào tdq-workflow giúp tôi

Đọc hiểu ban đầu:
- **Mục tiêu:** Đưa trọn bộ `6` cải tiến từ báo cáo điều tra [2026-11-21-1736-mac-dinh-trinh-bay-de-hieu.md](../reports/2026-11-21-1736-mac-dinh-trinh-bay-de-hieu.md) vào mã nguồn `tdq-workflow` để mọi câu trả lời chat, tài liệu `.md` (`spec`/`plan`/`report`) và trang web Archify HTML mặc định theo kiến trúc `2` tầng rõ ràng, dễ hiểu ngay lần đầu.
- **Phạm vi dự kiến:** Quy chuẩn `user-facing-block.md`, các khuôn mẫu `spec`/`plan`/`report`/`qc`, hook nhắc đúng lúc viết (`[TDQ:PLAIN]`), luật lint đọc dễ `R16` trong `doc_lint.py`, bản đồ tiếng Việt cho Archify HTML, bộ test hồi quy và đóng gói đồng bộ sang plugin `plugins/tdq-workflow-agy/`.
- **Mở rộng câu hỏi chốt:** Xác nhận phạm vi trọn gói hay làm từng phần, cơ chế cắt ngày của luật `R16` trên tài liệu cũ, phạm vi hook giữa Antigravity và Claude Code, nâng phiên bản (`0.104.0` → `0.105.0`), và mức QC.

## Hiểu & kiến thức

### Năng lực dùng được

Kiểm kê ngày 2026-11-21 bằng `scripts/skill_inventory.py`: `42` skill trên đĩa (thuộc `tdq-workflow`, `tdq-workflow-agy`, `chrome-devtools-plugin`, `gemini-api`, `gdocs`/`gdrive`/`gsheets`/`gslides`, `google-antigravity-sdk`, `frontend-design`, `ie3-design-bridge` và user skills) cùng bộ skill built-in trong ngữ cảnh.

| Skill | Nguồn | Phán quyết | Dùng ở đâu / Lý do loại |
|---|---|---|---|
| `tdq-intake` | `plugin:tdq-workflow-agy` | NỀN | Mở request, kiểm tra LSP, khảo sát `3` chiều và phỏng vấn |
| `tdq-spec` | `plugin:tdq-workflow-agy` | NỀN | Lập đặc tả kỹ thuật, ranh giới module và bản xem trước BA |
| `tdq-plan` | `plugin:tdq-workflow-agy` | NỀN | Chia task song song/tuần tự kèm bench chế độ thực thi |
| `tdq-build` | `plugin:tdq-workflow-agy` | NỀN | Thực thi TDD đỏ–xanh, QC đa tầng và viết báo cáo cuối |
| `tdq-conventions` | `plugin:tdq-workflow-agy` | NỀN | Luật cốt lõi, token budget, git hai nhánh và văn phong trình bày |
| `tdq-browser-test` | `plugin:tdq-workflow-agy` | DÙNG | Kiểm chứng giao diện web Archify HTML tiếng Việt qua trình duyệt và `0` lỗi console |
| `plugin` | `built-in` | DÙNG | Chuẩn đóng gói và kiểm định hợp lệ `plugins/tdq-workflow-agy/` |
| Đã xét `34` skill đĩa khác và `15+` skill built-in | `plugin` / `built-in` | KHÔNG | khác lĩnh vực |

### Bảng đối chiếu vùng chạm (khảo sát 3 chiều)

| Nhóm công việc | Tệp chạm thực tế | Hiện trạng & Ràng buộc phát hiện từ mã nguồn |
|---|---|---|
| **1. Quy chuẩn & Ví dụ trình bày** | `skills/tdq-conventions/references/user-facing-block.md`, `user-facing-block-vi-du.md`, `tests/test_user_facing_block.py` | Hiện tại `user-facing-block.md` đạt `2.863/3.500` token (còn trống `637` token). Test `test_rules_table_and_seven_rules` khóa cứng đúng `8` luật đánh số `1–8` và `3` câu tự kiểm; `SO_KHOI` khóa số khối mẫu trong file. Vì vậy phải **giữ nguyên cấu trúc đánh số `1–8`** và viết lại luật số `4` (từ ép bọc backtick số sang cấm bọc backtick số/thuật ngữ Lớp 1) thay vì xóa bớt dòng đánh số. |
| **2. Khuôn mẫu `Spec`/`Plan`/`Report`** | `skills/tdq-spec/references/spec-template.md`, `skills/tdq-plan/references/plan-template.md`, `skills/tdq-build/references/report-template.md`, `SKILL.md` (`tdq-spec`/`tdq-plan`/`tdq-build`), `tests/test_report_visual.py` | Các file đã sát trần `3.500` token (`plan` `3.472`, `spec` `3.372`, `report` `3.333`) nên sửa chữ theo nguyên tắc bù trừ giữ ròng `<= 0` token. Xóa tùy chọn `"verbatim"` ở `report-template.md:44`; thống nhất nhãn `Tóm tắt dễ hiểu:` (đồng thời cập nhật `tests/test_report_visual.py:66` vốn đang khóa chuỗi `"Tóm tắt nhanh:"`). |
| **3. Hook nhắc lúc viết `[TDQ:PLAIN]`** | `tools/patches/gate_guidance.py`, `tools/patches/agy_hooks.py`, `hooks/scripts/prompt_context.py`, `tests/test_gate_guidance.py`, `tests/test_hooks_dual_protocol.py` | `gate_guidance.py` có `22` mã (`ALL_AGY_CODES`, `GUIDANCE_CODES` = `12`) bị khóa cứng trong `test_gate_guidance.py:63,72`, `test_hooks_dual_protocol.py:75` và chuỗi mô tả `"24 [TDQ:*]"` trong `plugins/tdq-workflow-agy/plugin.json:6`. `plugins/tdq-workflow-agy/hooks.json` gọi `tdq-dispatch.exe --event PreInvocation` (Rust), nhưng `pre_invocation.rs` tự động đẩy lượt mới hoặc đổi pha sang Python `prompt_context.py` (tạo từ `agy_hooks.py`), nên cập nhật `_agy_phase_anchor` ở Python phủ được ngay pha `spec`, `plan`, `report`. |
| **4. Luật lint dễ đọc `R16`** | `scripts/doc_lint.py`, `tests/test_doc_lint.py` (hoặc `test_doc_lint_r16.py`) | `doc_lint.py:1516` đang miễn toàn bộ `R1–R7` cho `OUTPUT_DIRS` (`docs/tdq/**`). Cần thêm `rule_r16` dùng mốc cắt slug (`R16_MOC = "2026-11-21-1819"`) giống `R14_MOC` (`L1369`) để chỉ kiểm Lớp 1 mở đầu trên các tài liệu mới, không làm gãy tài liệu lịch sử trước đây. |
| **5. Archify HTML tiếng Việt** | `scripts/tdq_archify.py`, `skills/tdq-spec/references/archify-ba.md` | Khảo sát công cụ Archify ngoài (`locales/manifest.json`) cho thấy engine **không có gói ngôn ngữ `vi` dựng sẵn** (chỉ có `en`, `zh-CN`, `zh-TW`, `es`, `ko`, `ar`), nếu bỏ trống sẽ tự rơi về tiếng Trung (`zh-CN`). Tuy nhiên `i18n.mjs:157` hỗ trợ ghi đè `meta.translations` trên nền `"locale": "en"`, nên `tdq_archify.py` có thể tự động bơm từ điển UI tiếng Việt khi `doc_lang=vi` mà không phải sửa engine ngoài. |
| **6. Đóng gói plugin & Version** | `plugins/tdq-workflow-agy/**`, `tools/build_agy_plugin.py`, `docs/tdq/token-budget.json`, `.claude-plugin/plugin.json`, `docs/claude-md-mau.md` | Theo quy tắc build: `tools/build_agy_plugin.py` biên dịch sang `plugins/tdq-workflow-agy/` (nhớ chạy lại `scripts/token_budget.py` / `doc_index.py` để khóa SHA + ngân sách `<= 3.500` token). |

*Ghi chú kiểm tra LSP:* Đã chạy kiểm tra 3 tầng; `rust:hooks/rust/tdq-dispatch` đạt `3` tham chiếu LSP, riêng script mẫu `python:.` chọn `generate_manifest_and_readme` ngoài vùng `include` của `pyrightconfig.json` (`scripts`, `hooks`, `tests`) trong khi `find_references` trên `scripts/doc_lint.py:r14_loi` trả về `26` tham chiếu sống bình thường, nên đã áp dụng `--bo-qua-lsp` hợp lệ để mở request. Không chỉnh sửa `skills/tdq-conventions/references/soul.md` trừ khi có duyệt riêng.

## Hỏi đáp

1. Phạm vi triển khai? → **A (`1a`):** Trọn bộ `6` hạng mục (quy chuẩn và mẫu `2` tầng, bỏ bọc code quanh số, hook `[TDQ:PLAIN]`, luật kiểm `R16`, Việt hóa Archify HTML và nâng cấp test).
2. Mức kiểm soát luật `R16`? → **A (`2a`):** Chặn lỗi cho tài liệu mới từ mốc `2026-11-21-1819` (bỏ qua tài liệu cũ, không làm gãy lịch sử).
3. Cơ chế nhắc lúc viết? → **A (`3a`):** Thêm mã `[TDQ:PLAIN]` vào bảng mã hook để bơm thẻ nhắc ngắn vào `spec`, `plan`, `report` trên cả hai môi trường và cập nhật test đếm mã.
4. Đóng gói & Phiên bản? → **A (`4a`):** Đóng gói lại `plugins/tdq-workflow-agy/`, khóa lại `token-budget.json`, đồng bộ mẫu cấu hình người dùng và nâng bản `0.104.0` → `0.105.0` trong repo (chưa đụng `~/.gemini/` hay `main`).
5. Mức kiểm chứng QC? → **A (`5a`):** Đầy đủ (`full`) gồm test vùng chạm, test smoke E2E, toàn bộ bộ test tự động và kiểm trang HTML báo cáo trên trình duyệt.
