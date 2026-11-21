# PLAN — Mặc định Trình bày Report, Spec & Plan Ngắn gọn, Tự nhiên, Dễ hiểu

Ngày: 2026-11-21 · Spec: ../spec/2026-11-21-0917-mac-dinh-trinh-bay-ngan.md · Lane: full · Work kind: build · QC: `full`
Trạng thái plan: HOÀN THÀNH
Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

> **Tóm tắt dễ hiểu:** Kế hoạch gồm 3 đợt với 7 công việc rõ ràng: Đợt 1 bổ sung chuẩn kể chuyện ngắn gọn theo mẫu `1.jpg` và bỏ lệnh ép nén dấu `·` trong `report`; Đợt 2 thêm ô tóm tắt dễ hiểu vào đầu `spec`, `plan`, `quick` cùng lời nhắc prompt toàn cục mà không làm phồng vượt trần `3.500` token; Đợt 3 khóa lại ngân sách token, kiểm tra bảng luật và đóng gói mới gói `plugins/tdq-workflow-agy/` trong repo (không cài đè ra máy).

## Ràng buộc toàn cục

- Tài liệu `docs/tdq/` viết tiếng Việt (`doc_lang=vi`); các file hướng dẫn trong `skills/` giữ ngôn ngữ gốc tiếng Anh, bọc thẻ `<!-- i18n-allow: ... -->` cho mẫu tiếng Việt.
- Mọi file reference trong `skills/` phải giữ `<= 3.500` token sau khi sửa (`docs/tdq/token-budget.json`); `skills/tdq-spec/SKILL.md` giữ `<= 100` dòng và `skills/tdq-plan/SKILL.md` giữ `<= 132` dòng.
- Mọi khối chat mẫu giữ nguyên 6 thành phần, 8 luật trang trí, 6 ký tự ngoài ASCII (`➤`, `·`, `—`, `→`, `–`, `…`), 0 emoji, không chèn `#` heading trong mẫu chat.
- Mọi luật đã khóa trong `docs/tdq/audit/luat-hien-co.md` bảo toàn 40 ký tự neo đầu và giữ độ lệch số dòng toàn bảng `< 5%`.
- Chỉ build gói `plugins/tdq-workflow-agy/` trong repo và kiểm `--dry-run`; tuyệt đối không ghi đè `~/.gemini/config/plugins/` hay file cấu hình user ngoài repo.
- Log service: BỎ theo `spec §4` (không tạo runtime service mới; các script build và kiểm thử dùng cơ chế `TDQ_LOG` hiện hữu).

## Ownership Map

| Contract | Owner Task & File | Consumers |
|---|---|---|
| Plain-Language Narrative Rule (Trước → Sau → Kết quả) & mẫu `1.jpg` | `T1.1` (`skills/tdq-conventions/references/user-facing-block.md`, `user-facing-block-vi-du.md`) | `T1.2`, `T2.1`, `T2.2`, `T2.3`, `T3.2` |
| Khuôn `report` không ép nén `·` & ô `Tóm tắt nhanh` | `T1.2` (`skills/tdq-build/references/report-template.md`) | `T3.1`, `T3.2` |
| Khuôn `spec` kèm `Tóm tắt dễ hiểu` & khung chat tự nhiên | `T2.1` (`skills/tdq-spec/SKILL.md`, `spec-template.md`, `spec-template-huong-dan.md`) | `T3.1`, `T3.2` |
| Khuôn `plan` & `quick` kèm `Tóm tắt dễ hiểu` & khung chat | `T2.2` (`skills/tdq-plan/SKILL.md`, `plan-template.md`, `plan-template-huong-dan.md`, `quick-lane-mini.md`) | `T3.1`, `T3.2` |
| Chuẩn trình bày trong prompt toàn cục & `AGENTS.md` | `T2.3` (`scripts/tdq_setup.py`, `docs/claude-md-mau.md`, `tools/patches/agy_manifests.py`) | `T3.1`, `T3.2` |
| Khóa ngân sách token (`<= 3500`) & bảng luật `luat-hien-co.md` | `T3.1` (`docs/tdq/token-budget.json`, `docs/tdq/audit/luat-hien-co.md`) | `T3.2` |
| Gói plugin biên dịch trong repo | `T3.2` (`plugins/tdq-workflow-agy/`) | QC (`Q3`, `Q6`) |

## Bảng Hiện trạng (Trước) vs Thiết kế mới (Sau)

| Khu vực | Hiện trạng (Trước) | Thiết kế mới (Sau) |
|---|---|---|
| `user-facing-block.md` & `vi-du.md` | Chỉ kiểm 6 phần và 8 luật cú pháp, chưa khóa văn phong kể chuyện đời thường | Thêm mục văn phong kể chuyện Trước → Sau → Kết quả và cặp đối chiếu thực tế theo mẫu `1.jpg` |
| `report-template.md` | Dòng 101 & 110–115 ép nén mỗi mục vào một dòng nối `·`, khung chat chỉ liệt kê đề mục khô | Gỡ ép nén `·`, thêm `> **Tóm tắt nhanh:**` và khung chat `1. Trước và sau request có gì khác?` tách ý con thoáng |
| `spec` / `plan` / `quick` | Mở đầu trực tiếp bằng bảng kỹ thuật; khung chat chỉ có nhãn ngắn; template gần chạm trần `3.500` tok | Thêm neo `> **Tóm tắt dễ hiểu:**` ở đầu file (`<= 3.500` tok), hướng dẫn chi tiết dời sang `*-huong-dan.md`, nâng cấp khung chat |
| `tdq_setup.py`, `claude-md-mau.md`, `agy_manifests.py` | Mới nhắc ngắn gọn cho `report` 4 phần, chưa nhắc mặc định kể chuyện cho cả `spec` và `plan` | Ghim chuẩn trình bày tự nhiên cho cả `spec`, `plan`, `report` và đồng bộ qua `build_agy_plugin.py` vào `plugins/tdq-workflow-agy/` |

## Luật file nóng

- Không có file nào bị hai task chạy song song cùng ghi: `T1.1` và `T1.2` có tập `Chạm:` rời nhau hoàn toàn; `T2.1`, `T2.2` và `T2.3` có tập `Chạm:` rời nhau hoàn toàn.
- `docs/tdq/token-budget.json`, `docs/tdq/audit/luat-hien-co.md` (`T3.1`) và thư mục build `plugins/tdq-workflow-agy/` (`T3.2`) là file/thư mục đích tổng hợp nên được tuần tự hóa ở Đợt 3 sau khi toàn bộ Đợt 1 và Đợt 2 hoàn tất.

## Cụm song song

- **Cụm 1 (Wave 1):** `T1.1`, `T1.2` — hai nhánh độc lập hoàn toàn (`tdq-conventions` và `tdq-build/report-template`).
- **Cụm 2 (Wave 2 — sau `T1.1`):** `T2.1`, `T2.2`, `T2.3` — ba nhánh độc lập hoàn toàn (`tdq-spec`, `tdq-plan` + `quick-lane-mini`, và `tdq_setup`/`claude-md-mau`/`agy_manifests`).
- **Cụm 3 (Wave 3 — tuần tự sau Cụm 1 & Cụm 2):** `T3.1` → `T3.2` — khóa tập trung `token-budget.json`/`luat-hien-co.md` rồi build `plugins/tdq-workflow-agy/`.

## Phân bổ Model & Effort

| Pha | Model khuyến nghị | Effort | Lý do |
|---|---|---|---|
| `implement` (`T1.1–T2.3`) | Model mặc định phiên (`inherit`) | Trung bình | Sửa quy chuẩn, khuôn mẫu và viết test khóa chính xác theo hợp đồng token và chuỗi neo |
| `implement` (`T3.1–T3.2`) | Model mặc định phiên (`inherit`) | Trung bình | Khóa lại SHA-256 token budget, rà lệch dòng `luat-hien-co.md` và build kiểm chứng plugin |
| `qc` | `tdq-qc-tester` (`inherit`) | Cao | Kiểm chứng độc lập toàn bộ `Q1–Q6` với mức `full` và chạy trọn bộ test hồi quy |
| `report` | Model mặc định phiên (`inherit`) | Thấp | Tổng hợp bằng chứng thực chạy và xuất cặp `report` theo đúng chuẩn kể chuyện mới |

## Phase 1 — Quy chuẩn văn phong lõi & Khuôn Report

- [x] **T1.1** (e12m) Bổ sung quy chuẩn văn phong tự nhiên trong `user-facing-block.md`, đối chiếu `1.jpg` trong `user-facing-block-vi-du.md` và khóa test — Test: `py -3 -X utf8 -m unittest tests/test_user_facing_block.py tests/test_luat_gate_chat.py`
  - Req: `§1`, `§2`, `§3#1` · Ngoài phạm vi: `GIỮ NGUYÊN` bảng 6 thành phần, danh sách đánh số `1..8`, danh sách 7 điểm chạm, câu cấm `AskUserQuestion` và 3 bước `Self-check before sending`
  - Chạm: `skills/tdq-conventions/references/user-facing-block.md`, `skills/tdq-conventions/references/user-facing-block-vi-du.md`, `tests/test_user_facing_block.py` · Cần: Không
  - Giao tiếp: Consumes: chuẩn 6 ký tự trong `scripts/scan_block_symbols.py` | Produces: mục `Plain-Language Narrative Rule` trong `user-facing-block.md` và ví dụ đối chiếu `1.jpg` trong `user-facing-block-vi-du.md`
  - Neo & Công cụ: `Edit` `skills/tdq-conventions/references/user-facing-block.md` (`L55-120`), `skills/tdq-conventions/references/user-facing-block-vi-du.md` (`L28-76`), `tests/test_user_facing_block.py` (`UserFacingBlockTest` `L162-345`)
  - Trước → Sau: chỉ kiểm cấu trúc/ký tự → bổ sung luật kể chuyện Trước → Sau → Kết quả, lồng số liệu gọn, đẩy path/lệnh dài về link
  - Tiêu chí chấp nhận (EARS): KHI chạy `test_user_facing_block.py` và `scan_block_symbols.py --chi-khoi`, HỆ THỐNG PHẢI trả về exit `0`, `0` ký tự ngoài whitelist, `0` emoji và khớp số khối `SO_KHOI`
  - Logic cốt lõi: thêm mục quy tắc văn phong tự nhiên vào `user-facing-block.md` (giữ `<= 3500` tok), thêm ví dụ đối chiếu report & spec/plan trong `user-facing-block-vi-du.md` kèm thẻ `i18n-allow`, cập nhật assertion khóa luật mới trong `UserFacingBlockTest`
  - Ca góc hiểm & Assert: mẫu tiếng Việt thiếu `i18n-allow` hoặc thêm khối `➤` lệch `SO_KHOI` → `assertIn("Plain-Language Narrative", block_text)` và kiểm đếm `SO_KHOI` chính xác trên từng file

- [x] **T1.2** (e12m) Nâng cấp `report-template.md` bỏ ép nén dấu `·`, thêm `Tóm tắt nhanh` và khung chat kể chuyện mẫu `1.jpg` — Test: `py -3 -X utf8 -m unittest tests/test_report_visual.py tests/test_luat_dung.py tests/test_timing.py tests/test_user_facing_block.py`
  - Req: `§1`, `§2`, `§3#2` · Ngoài phạm vi: `GIỮ NGUYÊN` 4 đề mục bắt buộc (`Trước request (trạng thái/flow)`, `Sau request (trạng thái/flow)`, `Đã test gì`, `Kết quả test`), phần `Lệch spec chờ duyệt`, bảng `Thời gian` và `SO_KHOI = 1`
  - Chạm: `skills/tdq-build/references/report-template.md`, `tests/test_report_visual.py` · Cần: Không
  - Giao tiếp: Consumes: bộ 4 mục kiểm của `scripts/tdq_state.py` (`L2874-2879`) | Produces: mẫu `report` có `> **Tóm tắt nhanh:**` và khung chat kể chuyện `1. Trước và sau request có gì khác?`
  - Neo & Công cụ: `Edit` `skills/tdq-build/references/report-template.md` (`L51-155`), `tests/test_report_visual.py` (`ReportVisualContract` `L12-59`)
  - Trước → Sau: dòng 101 & 110–115 ép nén 1 dòng nối `·` → bỏ lệnh ép nén `·`, cho phép tách ý con có nhãn ngắn dễ hiểu như ảnh `1.jpg`
  - Tiêu chí chấp nhận (EARS): KHI chạy `test_report_visual.py` và `test_user_facing_block.py`, HỆ THỐNG PHẢI xác nhận có `Tóm tắt nhanh`, có 4 đề mục bắt buộc và không còn cụm `"compress each item into ONE line"`
  - Logic cốt lõi: gỡ chỉ dẫn nén dòng `·`, bổ sung ô `> **Tóm tắt nhanh:**` đầu khuôn `.md`, viết lại khối chat báo cáo & hỏi commit thoáng mắt giữ đúng 1 dấu `➤`, thêm test khóa trong `ReportVisualContract`
  - Ca góc hiểm & Assert: giữ nguyên toàn bộ từ khóa kiểm của `tdq_state.py`, `test_luat_dung.py`, `test_timing.py` → `assertNotIn("compress each item into ONE line", template)` và `assertIn("Tóm tắt nhanh", template)`

## Phase 2 — Nâng cấp khuôn Spec, Plan, Quick & Prompt hệ thống

- [x] **T2.1** (e14m) Thêm `Tóm tắt dễ hiểu` cho `spec` và nâng cấp khung chat trình spec không vượt trần token — Test: `py -3 -X utf8 -m unittest tests/test_spec_template.py tests/test_khao_sat_3_chieu.py tests/test_luat_dung.py tests/test_user_facing_block.py`
  - Req: `§1`, `§2`, `§3#3` · Ngoài phạm vi: `GIỮ NGUYÊN` toàn bộ mục `2c`, `3c`, `3d`, bảng `R14` ở `§6`, nhãn `**Luồng & Giải thuật:**` và giới hạn `<= 100` dòng của `tdq-spec/SKILL.md`
  - Chạm: `skills/tdq-spec/SKILL.md`, `skills/tdq-spec/references/spec-template.md`, `skills/tdq-spec/references/spec-template-huong-dan.md`, `tests/test_spec_template.py` · Cần: `T1.1`
  - Giao tiếp: Consumes: `Plain-Language Narrative Rule` từ `T1.1` | Produces: ô `> **Tóm tắt dễ hiểu:**` trong `spec-template.md`, checklist đọc 10 giây trong `spec-template-huong-dan.md`, khung chat tự nhiên trong `tdq-spec/SKILL.md`
  - Neo & Công cụ: `Edit` `skills/tdq-spec/SKILL.md` (`L56-90`), `skills/tdq-spec/references/spec-template.md` (`L1-40`), `skills/tdq-spec/references/spec-template-huong-dan.md` (`L75-104`), `tests/test_spec_template.py` (`TestSpecTemplateStructure` `L22-96`)
  - Trước → Sau: đầu spec vào thẳng mục lục và khung chat liệt kê nhãn khô → mở bằng ô `Tóm tắt dễ hiểu` và khung chat kể mạch Trước → Sau → Lợi ích
  - Tiêu chí chấp nhận (EARS): KHI chạy `test_spec_template.py` và `doc_lint.py`, HỆ THỐNG PHẢI xác nhận `spec-template.md` có `Tóm tắt dễ hiểu`, `tdq-spec/SKILL.md` `<= 100` dòng và không rơi bất kỳ neo nào của `R14` hay `2c/3c/3d`
  - Logic cốt lõi: chèn dòng neo ngắn trong `spec-template.md` (tỉa chú thích lặp để giữ `<= 3500` tok), thêm hướng dẫn viết dễ hiểu vào `spec-template-huong-dan.md`, nâng cấp mẫu chat trong `tdq-spec/SKILL.md`, khóa bằng unit test mới
  - Ca góc hiểm & Assert: `spec-template.md` hiện ở `3458/3500` tok nên chỉ dư `42` tok → giữ phần diễn giải dài ở `spec-template-huong-dan.md` và `assertIn("Tóm tắt dễ hiểu", template_text)`

- [x] **T2.2** (e12m) Thêm `Tóm tắt dễ hiểu` cho `plan` & `quick-lane-mini` và nâng cấp khung chat trình plan — Test: `py -3 -X utf8 -m unittest tests/test_khao_sat_3_chieu.py tests/test_plan_v2_linter.py tests/test_user_facing_block.py`
  - Req: `§1`, `§2`, `§3#3` · Ngoài phạm vi: `GIỮ NGUYÊN` cấu trúc task `R15`, bảng `Hiện trạng (Trước) vs Thiết kế mới (Sau)`, `mode` gate `tdq_bench.py` và giới hạn `<= 132` dòng của `tdq-plan/SKILL.md`
  - Chạm: `skills/tdq-plan/SKILL.md`, `skills/tdq-plan/references/plan-template.md`, `skills/tdq-plan/references/plan-template-huong-dan.md`, `skills/tdq-intake/references/quick-lane-mini.md`, `tests/test_khao_sat_3_chieu.py` · Cần: `T1.1`
  - Giao tiếp: Consumes: `Plain-Language Narrative Rule` từ `T1.1` | Produces: ô `> **Tóm tắt dễ hiểu:**` trong `plan-template.md` và `quick-lane-mini.md`, hướng dẫn viết tự nhiên trong `plan-template-huong-dan.md`, khung chat gọn trong `tdq-plan/SKILL.md`
  - Neo & Công cụ: `Edit` `skills/tdq-plan/SKILL.md` (`L80-105`), `skills/tdq-plan/references/plan-template.md` (`L1-35`), `skills/tdq-plan/references/plan-template-huong-dan.md` (`L1-52`), `skills/tdq-intake/references/quick-lane-mini.md` (`L1-50`), `tests/test_khao_sat_3_chieu.py` (`L99-120`)
  - Trước → Sau: plan và quick-mini mở đầu thẳng bằng danh sách task kỹ thuật → có ô tóm tắt đời thường ở đầu và khung chat nêu rõ từng đợt làm được gì
  - Tiêu chí chấp nhận (EARS): KHI chạy `test_khao_sat_3_chieu.py` và `test_plan_v2_linter.py`, HỆ THỐNG PHẢI xác nhận `plan-template.md` và `quick-lane-mini.md` chứa `Tóm tắt dễ hiểu`, `tdq-plan/SKILL.md` `<= 132` dòng
  - Logic cốt lõi: chèn neo gọn vào `plan-template.md` (`3420/3500` tok) và `quick-lane-mini.md` (`1006/3500` tok), thêm hướng dẫn tóm tắt đời thường vào `plan-template-huong-dan.md`, cập nhật mẫu chat trình plan, khóa test trong `test_khao_sat_3_chieu.py`
  - Ca góc hiểm & Assert: `plan-template.md` chỉ còn `80` tok dư và khóa số khối `SO_KHOI` ở `tdq-plan/SKILL.md` = `1` → kiểm `assertIn("Tóm tắt dễ hiểu", plan_nd)` và `assertIn("Tóm tắt dễ hiểu", quick_nd)`

- [x] **T2.3** (e10m) Đồng bộ chuẩn trình bày tự nhiên cho `spec`, `plan`, `report` trong `tdq_setup.py`, `claude-md-mau.md` và `agy_manifests.py` — Test: `py -3 -X utf8 -m unittest tests/test_claude_md_core.py`
  - Req: `§1`, `§2`, `§3#4` · Ngoài phạm vi: `GIỮ NGUYÊN` toàn bộ từ khóa bất biến trong `INVARIANTS`, trần `MAX_BYTES = 12500` của `test_claude_md_core.py`, không ghi đè file ngoài repo
  - Chạm: `scripts/tdq_setup.py`, `docs/claude-md-mau.md`, `tools/patches/agy_manifests.py`, `tests/test_claude_md_core.py` · Cần: `T1.1`
  - Giao tiếp: Consumes: `Plain-Language Narrative Rule` từ `T1.1` | Produces: câu luật tầng 1 trong `khoi_huong_dan()`, `docs/claude-md-mau.md` và `generate_two_tier_rules()`
  - Neo & Công cụ: `Edit` `scripts/tdq_setup.py` (`khoi_huong_dan` `L1138-1159`), `docs/claude-md-mau.md` (`L100-104`), `tools/patches/agy_manifests.py` (`generate_two_tier_rules` `L174-220`), `tests/test_claude_md_core.py` (`L208-221`)
  - Trước → Sau: lời nhắc tầng 1 mới nêu quy chuẩn 4 phần cho `report` → mở rộng rõ mặc định kể chuyện ngắn gọn, tự nhiên cho cả `spec`, `plan` và `report`
  - Tiêu chí chấp nhận (EARS): KHI chạy `test_claude_md_core.py`, HỆ THỐNG PHẢI PASS 100%, giữ kích thước `docs/claude-md-mau.md` `<= 12500` byte và `khoi_huong_dan()` nêu đủ `spec`, `plan`, `report` tự nhiên dễ hiểu
  - Logic cốt lõi: cập nhật đồng bộ mục `Chuẩn Trình bày & Báo cáo` trong `tdq_setup.py` và `docs/claude-md-mau.md`, bổ sung 1 gạch đầu dòng ở mục 4 của `AGENTS.md` trong `generate_two_tier_rules()`, thêm assertion vào `test_claude_md_core.py`
  - Ca góc hiểm & Assert: đồng bộ sai lệch giữa `tdq_setup.py` và `docs/claude-md-mau.md` sẽ làm đỏ `CoreFileTest` → kiểm đồng bộ exact substring cả hai nguồn cùng `assertIn("spec", khoi.lower())` và `assertIn("plan", khoi.lower())`

## Phase 3 — Khóa ngân sách, Đồng bộ bảng luật & Đóng gói plugin repo

- [x] **T3.1** (e12m) Cập nhật `doc_index.py`, khóa `token-budget.json` (`<= 3500` tok) và đồng bộ `luat-hien-co.md` + kiểm `i18n` & `doc_lint` — Test: `py -3 -X utf8 -m unittest tests/test_token_budget.py tests/test_token_budget_lock.py tests/test_luat_skill.py tests/test_doc_index.py tests/test_user_facing_block.py`
  - Req: `§3#4`, `§6#Q4` · Ngoài phạm vi: `GIỮ NGUYÊN` mọi neo `user-facing` trong `docs/tdq/audit/ranh-gioi-luat.md` và không nâng trần `3.500` token trừ khi thật sự không còn câu chú thích dư
  - Chạm: `docs/tdq/token-budget.json`, `docs/tdq/audit/luat-hien-co.md` · Cần: `T1.1`, `T1.2`, `T2.1`, `T2.2`, `T2.3`
  - Giao tiếp: Consumes: toàn bộ file `skills/` đã sửa từ `T1.1–T2.2` | Produces: khóa SHA-256 hợp lệ trong `token-budget.json` và số dòng chuẩn `< 5%` lệch trong `luat-hien-co.md`
  - Neo & Công cụ: `Bash` `scripts/doc_index.py --sync`, `scripts/token_budget.py --update`, `scripts/doc_lint.py`, `scripts/scan_block_symbols.py --chi-khoi`
  - Trước → Sau: hash SHA-256 và số dòng cũ lệch sau khi sửa skill → đồng bộ sạch `token-budget.json`, TOC và `luat-hien-co.md`
  - Tiêu chí chấp nhận (EARS): KHI chạy toàn bộ bộ test khóa token, bảng luật, mục lục và `doc_lint.py` trên các file sửa, HỆ THỐNG PHẢI trả về exit `0` với mọi file reference `<= 3500` token và độ lệch dòng `< 5.0%`
  - Logic cốt lõi: chạy cập nhật mục lục động cho các file thay đổi, chạy đo token thật bằng venv `TDQ_TOKENS_VENV` để ghi khóa mới, rà lại bảng `luat-hien-co.md` nếu có neo dịch dòng và xác minh toàn bộ test khóa xanh
  - Ca góc hiểm & Assert: thiếu `TDQ_TOKENS_VENV` hoặc một file `spec-template.md` / `plan-template.md` vượt `3500` tok → chạy với `$env:TDQ_TOKENS_VENV` thật và xác nhận mọi entry khóa đều `token <= 3500`

- [x] **T3.2** (e12m) Biên dịch lại `plugins/tdq-workflow-agy/` trong repo, kiểm `--dry-run` cài đặt và chạy kiểm chứng plugin — Test: `py -3 -X utf8 -m unittest tests/test_agy_plugin_validate.py`
  - Req: `§1`, `§2`, `§3#4`, `§6#Q3` · Ngoài phạm vi: `KHÔNG` chạy cài đặt live ghi đè `~/.gemini/config/plugins/tdq-workflow-agy` theo quyết định `3b`
  - Chạm: `plugins/tdq-workflow-agy/rules/AGENTS.md`, `plugins/tdq-workflow-agy/skills/tdq-conventions/references/user-facing-block.md`, `plugins/tdq-workflow-agy/skills/tdq-conventions/references/user-facing-block-vi-du.md`, `plugins/tdq-workflow-agy/skills/tdq-build/references/report-template.md`, `plugins/tdq-workflow-agy/skills/tdq-spec/SKILL.md`, `plugins/tdq-workflow-agy/skills/tdq-plan/SKILL.md` · Cần: `T3.1`
  - Giao tiếp: Consumes: nguồn `skills/`, `scripts/tdq_setup.py`, `tools/patches/agy_manifests.py` đã xanh từ `T3.1` | Produces: bản build mới trong `plugins/tdq-workflow-agy/`
  - Neo & Công cụ: `Bash` `py -3 -X utf8 tools/build_agy_plugin.py`, `py -3 -X utf8 tools/install_agy_plugin.py --dry-run`
  - Trước → Sau: bản build trong `plugins/tdq-workflow-agy/` còn mang quy chuẩn cũ → mang trọn chuẩn văn phong tự nhiên, mẫu `1.jpg` và `AGENTS.md` cập nhật
  - Tiêu chí chấp nhận (EARS): KHI chạy `tools/build_agy_plugin.py`, `tools/install_agy_plugin.py --dry-run` và `tests/test_agy_plugin_validate.py`, HỆ THỐNG PHẢI thoát exit `0`, phản ánh đúng nội dung mới trong `plugins/tdq-workflow-agy/` và không thay đổi mtime của `~/.gemini/config/plugins/tdq-workflow-agy`
  - Logic cốt lõi: biên dịch lại plugin bằng `tools/build_agy_plugin.py`, xác minh `AGENTS.md` và các file skill biên dịch khớp thay đổi nguồn, chạy `--dry-run` để kiểm chứng gói sẵn sàng cài khi người dùng cần
  - Ca góc hiểm & Assert: bản dịch M01–M20 trong `skills_and_agents.py` không được làm vượt trần token trong bản build hoặc sai ký tự whitelist → kiểm chứng nội dung `plugins/tdq-workflow-agy/rules/AGENTS.md` và `test_agy_plugin_validate.py` PASS `0` lỗi

## Definition of Done

- [x] Toàn bộ 7 task (`T1.1` → `T3.2`) hoàn thành theo chu trình Red → Green và được đánh dấu `[x]` đầy đủ trong plan này.
- [x] `user-facing-block.md`, `user-facing-block-vi-du.md`, `report-template.md`, `spec-template*.md`, `plan-template*.md`, `quick-lane-mini.md`, `tdq-spec/SKILL.md`, `tdq-plan/SKILL.md`, `scripts/tdq_setup.py`, `docs/claude-md-mau.md`, `tools/patches/agy_manifests.py` đều áp dụng chuẩn kể chuyện tự nhiên, giữ nguyên mọi bảng/mục kỹ thuật bắt buộc và `<= 3500` token.
- [x] `scan_block_symbols.py --chi-khoi` trả `0` ký tự lạ, `doc_lint.py` trả `0` lỗi, `tools/build_agy_plugin.py` và `tools/install_agy_plugin.py --dry-run` thoát `0`, thư mục live `~/.gemini/config/plugins/` nguyên trạng.
- [x] Toàn bộ bộ kiểm thử `py -3 -X utf8 scripts/tdq_test.py tron-bo` và QC độc lập mức `full` (`Q1–Q6`) đạt PASS trước khi xuất báo cáo cuối.
