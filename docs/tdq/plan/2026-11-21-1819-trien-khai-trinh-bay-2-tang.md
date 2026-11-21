# PLAN — Triển khai kiến trúc mặc định trình bày 2 tầng vào TDQ-Workflow

Ngày: 2026-11-21 · Spec: [2026-11-21-1819-trien-khai-trinh-bay-2-tang.md](../spec/2026-11-21-1819-trien-khai-trinh-bay-2-tang.md) (bản 1.0, ĐÃ DUYỆT)
Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md
Mode thực thi: subagent (ĐÃ CHỐT) — Winner: đội (gap 4.0 minutes: team 8.2p vs main 12.2p qua 6 task theo tdq_bench.py simulate)
Trạng thái plan: HOÀN THÀNH

> **Tóm tắt dễ hiểu:** Kế hoạch chia làm ba đợt nối tiếp để sửa hệ thống mà không đụng tệp chéo nhau. Đợt đầu chạy song song bốn phần gồm sửa quy chuẩn và mẫu tài liệu, thêm thẻ nhắc đúng lúc viết, bật luật kiểm tự động và Việt hóa trang web. Đợt hai chạy kiểm thử hành vi, nâng phiên bản mới trong repo và đóng gói plugin, còn đợt ba chạy toàn bộ kiểm thử và duyệt giao diện web.

## Mục lục

- Phân bổ Model & Effort
- Quy tắc thi hành (áp cho mọi task)
- Thiết kế Trước vs Sau
- Ràng buộc toàn cục & Bản đồ Sở hữu Hợp đồng (Ownership Map)
- P1 — Wave 1: Nâng cấp `4` phân hệ cốt lõi song song
- P2 — Wave 2: Test hành vi, Khóa ngân sách token & Đóng gói `0.105.0`
- P3 — Wave 3: Kiểm chứng toàn hệ thống, Báo cáo `2` tầng & Web HTML tiếng Việt
- Cụm song song
- Luật file nóng
- Definition of Done

## Phân bổ Model & Effort

| Pha | Vai trò | Model | Effort | Ghi chú |
|---|---|---|---|---|
| `implement` (`P1`) | `tdq-implementer` (hoặc Leader nếu chạy `main`) | `inherit` | `high` | `4` cụm file tách biệt hoàn toàn, hỗ trợ isolation worktree |
| `implement` (`P2`) | `tdq-implementer` / Leader | `inherit` | `high` | Gộp kết quả P1, cập nhật test tích hợp, khóa token & build plugin |
| `qc` & `report` (`P3`) | `tdq-qc-tester` + Leader `(mcp)` | `inherit` | `high` | Chạy `tron-bo`, viết QC Card và kiểm tra HTML tiếng Việt bằng trình duyệt |

## Quy tắc thi hành (áp cho mọi task)

1. Tuân thủ TDD đỏ–xanh cho từng task: viết/chạy test thấy đỏ đúng chỗ trước khi sửa, rồi chạy lại cho tới khi xanh `0` lỗi.
2. Không tạo file hay ký hiệu ngoài phạm vi `Chạm:` đã chốt; giữ net token `<= 3.500` cho mọi tệp reference.
3. Không sửa `skills/tdq-conventions/references/soul.md`, không sửa mã ngoài `C:\Users\admin\Documents\archify`, không chạm `~/.gemini/` hay `main`.
4. Mọi task hoàn tất phải đổi `[ ]` / `[>]` sang `[x]` trong file plan này ngay khi chạy test pass.
5. Tự thực hành văn phong Lớp 1 chuẩn `R16` ngay trên các tệp đầu ra của chính request này.

## Thiết kế Trước vs Sau

| Hạng mục | Hiện trạng (`v0.104.0`) | Thiết kế áp dụng (`v0.105.0`) |
|---|---|---|
| Quy chuẩn & Mẫu | Luật văn phong nằm `L127`, luật #4 bọc backtick số, `report` cho dán `verbatim` | Trần Lớp 1 ở `L1–40`, luật #4 cấm bọc backtick số, thống nhất `Tóm tắt dễ hiểu:` |
| Hook nhắc lúc viết | Không có hook ở `spec`, `plan`, `report`; bảng mã giữ `22` mã | Bổ sung `[TDQ:PLAIN]` (`23` mã) bơm nhắc `<= 240` ký tự ngay trước lúc viết |
| Lint tài liệu xuất | `OUTPUT_DIRS` miễn `R1–R7`, chưa có kiểm mật độ mở đầu | Luật `R16` (`R16_MOC = "2026-11-21-1819"`) chặn lỗi Lớp 1, miễn tài liệu cũ |
| Trang Archify HTML | Rơi về `zh-CN` nếu thiếu `@meta`, hoặc cố định tiếng Anh | Tự động dịch thanh công cụ & JSON `explainer-reader-words` sang tiếng Việt |

## Ràng buộc toàn cục & Bản đồ Sở hữu Hợp đồng (Ownership Map)

- Giới hạn trần token (`3.500` tok/reference) kiểm lại bằng `py -3 -X utf8 scripts/token_budget.py` và khóa bằng `--ghi` ở `P2`.
- Ranh giới ngôn ngữ (`doc_lint.py` `R12`): quy tắc `skills/` và docstring/comment trong `scripts/`, `hooks/`, `tools/` viết tiếng Anh; chuỗi mẫu người dùng cuối viết tiếng Việt có nhãn `i18n-allow`.

| Hợp đồng / Giao diện | File & Task sở hữu | Task tiêu thụ |
|---|---|---|
| Luật #4 & Nhãn `Tóm tắt dễ hiểu:` | `user-facing-block.md`, `report-template.md` (`T1.1`) | `T1.3` (`R16`), `T2.1` (`test_report_visual.py`), `T3.1` |
| Mã `"PLAIN"` & `_agy_phase_anchor` | `tools/patches/gate_guidance.py`, `agy_hooks.py`, `prompt_context.py` (`T1.2`) | `T2.1` (`test_hooks_dual_protocol.py`, `build_agy_plugin.py`) |
| Hàm `r16_loi(text, ten_file)` & `R16_MOC` | `scripts/doc_lint.py` (`T1.3`) | `T2.1` (`test_report_visual.py`), `T3.1` (`doc_lint` toàn repo) |
| `_localize_explainer_html_vi` | `scripts/tdq_archify.py` (`T1.4`) | `T2.1` (`build_agy_plugin.py`), `T3.1` (HTML báo cáo cuối) |

## P1 — Wave 1: Nâng cấp `4` phân hệ cốt lõi song song

- [x] **T1.1** (e12m) Tinh gọn quy chuẩn `user-facing-block.md` (đưa trần Lớp 1 & ví dụ lên `L1–40`, đổi luật #4 không bọc backtick số, giữ `8` luật + `3` câu tự kiểm), thống nhất `> **Tóm tắt dễ hiểu:**` và xóa `"verbatim"`/`·` nhồi ở `spec`/`plan`/`report`/`qc` dưới trần `3.500` token — Test: `py -3 -X utf8 -m pytest tests/test_user_facing_block.py -q`
  - Req: `§2#1, §2b-M1, Q1` · Ngoài phạm vi: không sửa `soul.md`, không sửa `tests/test_report_visual.py` (`T2.1`) · Worktree: `worktree`
  - Chạm: `skills/tdq-conventions/references/user-facing-block.md`, `skills/tdq-conventions/references/user-facing-block-vi-du.md`, `skills/tdq-spec/references/spec-template.md`, `skills/tdq-plan/references/plan-template.md`, `skills/tdq-build/references/report-template.md`, `skills/tdq-build/references/qc.md`, `skills/tdq-build/SKILL.md`, `docs/claude-md-mau.md`, `scripts/tdq_setup.py`
  - Sinh ra: `skills/tdq-conventions/references/user-facing-block.md`, `skills/tdq-build/references/report-template.md`
  - Cần: Không
  - Giao tiếp: Consumes: `docs/tdq/token-budget.json` | Produces: chuẩn `> **Tóm tắt dễ hiểu:**`, luật #4 mới và mọi template `<= 3.500` token
  - Neo & Công cụ: Sửa cân đối trừ bù chữ thừa trước khi chèn ngưỡng; chạy `token_budget.py` và `pytest tests/test_user_facing_block.py` (đã cập nhật và đang gọt gọn dưới baseline byte cũ)
  - Trước → Sau: luật dễ hiểu ở `L127` + ép bọc backtick số → ngưỡng Lớp 1 ở `L1–40` + bỏ dán `verbatim` và nhồi `·`
  - Tiêu chí chấp nhận (EARS): KHI kiểm định `user-facing-block.md` và các template, số luật giữ đúng `1–8`, self-check giữ `1–3`, và toàn bộ tệp đạt `<= 3.500` token
  - Logic cốt lõi: nâng trần Lớp 1 lên đầu, thay thế nội dung luật #4, gỡ `"verbatim"` và chuẩn hóa `Tóm tắt dễ hiểu:`
  - Ca góc hiểm & Assert: bảo đảm `SO_KHOI` khớp số khối mẫu và `assert max(tokens) <= 3500`

- [x] **T1.2** (e10m) Thêm mã `"PLAIN"` vào `GUIDANCE_CODES`/`ALL_AGY_CODES`/`AGY_CODES`/`GUIDANCE_TABLE` (`22 → 23` mã) và mở rộng `_agy_phase_anchor` + `prompt_context.py` bơm thẻ `[TDQ:PLAIN]` (`<= 240` ký tự) khi vào pha `spec`, `plan`, `report` — Test: `py -3 -X utf8 -m pytest tests/test_gate_guidance.py -q`
  - Req: `§2#2, §2b-M2, Q2` · Ngoài phạm vi: không sửa `hooks/rust/tdq-dispatch/` và `tests/test_hooks_dual_protocol.py` (`T2.1`) · Worktree: `worktree`
  - Chạm: `tools/patches/gate_guidance.py`, `tools/patches/agy_hooks.py`, `hooks/scripts/_common.py`, `hooks/scripts/prompt_context.py`, `tests/test_gate_guidance.py`
  - Sinh ra: `tools/patches/gate_guidance.py`, `tools/patches/agy_hooks.py`, `hooks/scripts/prompt_context.py`, `tests/test_gate_guidance.py`
  - Cần: Không
  - Giao tiếp: Consumes: `effective_phase`, `read_turn_meta` | Produces: thẻ `[TDQ:PLAIN]` tối đa `240` ký tự cho pha `spec`/`plan`/`report`
  - Neo & Công cụ: Khớp `test_gate_guidance.py` trước khi viết code mới; dùng LSP kiểm call sites của `GUIDANCE_CODES`
  - Trước → Sau: `_agy_phase_anchor` bỏ qua `spec`/`plan`/`report` → phát `[TDQ:PLAIN]` đúng lúc vào pha hoặc sau compact
  - Tiêu chí chấp nhận (EARS): KHI vào `spec`, `plan` hoặc `report` (hoặc resume/compact), hook PHẢI phát `[TDQ:PLAIN]` `<= 240` ký tự mà không ảnh hưởng `[TDQ:GON]`/`[TDQ:QC]`
  - Logic cốt lõi: cập nhật bảng 4 phần cho `PLAIN`, mở điều kiện pha trong `_agy_phase_anchor` và `prompt_context.py`
  - Ca góc hiểm & Assert: dedupe `phase_anchor` chống lặp giữa chừng; `assert len(all_codes) == 23` và `assert len(hint) <= 240`

- [x] **T1.3** (e10m) Bổ sung luật lint `R16` (`r16_loi`, `rule_r16`, `R16_MOC = "2026-11-21-1819"`) vào `scripts/doc_lint.py` cho `OUTPUT_DIRS` (`spec/`, `plan/`, `reports/`) kiểm `> **Tóm tắt dễ hiểu:**`, mật độ backtick, độ dài câu/ô và chống nhồi `·` — Test: `py -3 -X utf8 -m pytest tests/test_doc_lint_r16.py -q`
  - Req: `§2#3, §2b-M3, Q3` · Ngoài phạm vi: không làm gãy tài liệu cũ trước `2026-11-21-1819` · Worktree: `worktree`
  - Chạm: `scripts/doc_lint.py`, `tests/test_doc_lint_r16.py`
  - Sinh ra: `scripts/doc_lint.py`, `tests/test_doc_lint_r16.py`
  - Cần: Không
  - Giao tiếp: Consumes: `Doc`, `OUTPUT_DIRS`, `R14_SLUG` | Produces: hàm thuần `r16_loi(text, ten_file)` và `rule_r16(doc, out)`
  - Neo & Công cụ: Viết `tests/test_doc_lint_r16.py` đỏ trước (ca thiếu tóm tắt, dày backtick, câu dài, nhiều `·`, miễn lịch sử, miễn Lớp 2)
  - Trước → Sau: `OUTPUT_DIRS` bỏ qua `R1–R7` → `R16` khóa Lớp 1 cho mọi tài liệu mới từ mốc `2026-11-21-1819`
  - Tiêu chí chấp nhận (EARS): KHI chạy `doc_lint` trên tài liệu mới `>= 2026-11-21-1819`, `R16` PHẢI bắt đủ `5` loại lỗi Lớp 1 và giữ `0` lỗi trên toàn bộ `docs/tdq/**` cũ
  - Logic cốt lõi: bóc vùng Lớp 1 trước `## 1.`/`## Mục lục`, tách khối blockquote tóm tắt và đo đếm cơ học tách riêng bảng/code
  - Ca góc hiểm & Assert: bỏ qua dòng `Soul:`, dòng header 1 `·` và mọi bảng `|`; `assert len(r16_loi(old_file)) == 0`

- [x] **T1.4** (e12m) Việt hóa giao diện Archify HTML khi `doc_lang=vi` (`@meta locale=en` chống rơi về `zh-CN`, hàm `_localize_explainer_html_vi` dịch thanh công cụ & JSON `#explainer-reader-words` trước bước băm manifest, cập nhật `_build_master_explainer` + tài liệu `archify-ba.md`/`archify-lifecycle.md`) — Test: `py -3 -X utf8 -m pytest tests/test_archify_vi.py -q`
  - Req: `§2#4, §2b-M4, Q4` · Ngoài phạm vi: không chỉnh sửa mã nguồn ngoài tại `C:\Users\admin\Documents\archify` · Worktree: `worktree`
  - Chạm: `scripts/tdq_archify.py`, `skills/tdq-spec/references/archify-ba.md`, `skills/tdq-build/references/archify-lifecycle.md`, `tests/test_archify_vi.py`
  - Sinh ra: `scripts/tdq_archify.py`, `tests/test_archify_vi.py`
  - Cần: Không
  - Giao tiếp: Consumes: `docs/tdq/state.json` (`doc_lang`) | Produces: helper `_localize_explainer_html_vi` và nhãn tiếng Việt hợp lệ JSON
  - Neo & Công cụ: Test giả lập HTML có `#explainer-reader-words` + Chrome tags trước, sau đó triển khai dịch trước băm manifest (220/220 test_archify*.py pass, 6/6 test_archify_vi pass)
  - Trước → Sau: thiếu `@meta` rơi về tiếng Trung hoặc cố định tiếng Anh → tự động xuất giao diện tiếng Việt chuẩn xác
  - Tiêu chí chấp nhận (EARS): KHI render HTML ở project `doc_lang=vi`, UI chrome + JSON reader PHẢI là tiếng Việt hợp lệ và `tdq_archify.py verify` đạt `current`/`valid=true`
  - Logic cốt lõi: đọc `doc_lang`, giữ nguyên fallback tiếng Anh cho engine rồi thay thế map tiếng Việt trước lúc ghi artifact cuối & băm SHA-256
  - Ca góc hiểm & Assert: parse lại bằng `json.loads` bảo đảm không vỡ cú pháp JS; `assert "zh-CN" not in html`

**Xong P1 khi**: cả `4` task Wave 1 pass unit test riêng, không sửa trùng file giữa `4` nhánh và `git diff` sạch cấu trúc.

## P2 — Wave 2: Test hành vi, Khóa ngân sách token & Đóng gói `0.105.0`

- [x] **T2.1** (e10m) Nâng cấp `tests/test_report_visual.py` kiểm chứng hành vi thật (đổi `"Tóm tắt nhanh:"` → `"Tóm tắt dễ hiểu:"` + fixture xấu/tốt gọi `r16_loi`), rà `tests/test_user_facing_block.py`, đồng bộ `tests/test_hooks_dual_protocol.py` (`22 → 23` mã), nâng `0.104.0 → 0.105.0` toàn repo, khóa `token-budget.json`, biên dịch lại `plugins/tdq-workflow-agy/` và kiểm `agy plugin validate` (`0` findings) — Test: `py -3 -X utf8 -m pytest tests/test_report_visual.py tests/test_hooks_dual_protocol.py -q`
  - Dùng: `plugin`
  - Để: đối chiếu quy chuẩn đóng gói và kiểm định cấu trúc plugin Antigravity `0.105.0`
  - Ra: gói `plugins/tdq-workflow-agy/` hợp lệ sạch findings
  - Kiểm: `py -3 -X utf8 tools/build_agy_plugin.py`
  - Không dùng cho: ghi đè `~/.gemini/` ngoài hệ thống hay sửa mã Python của `T1.2`–`T1.4`
  - Req: `§2#5, §2b-M5, Q5` · Ngoài phạm vi: giữ nguyên `~/.gemini/` và `main` · Worktree: `no_worktree`
  - Chạm: `tests/test_report_visual.py`, `tests/test_user_facing_block.py`, `tests/test_hooks_dual_protocol.py`, `.claude-plugin/plugin.json`, `tools/build_agy_plugin.py`, `tools/patches/__init__.py`, `tools/patches/agy_manifests.py`, `README.md`, `CHANGELOG.md`, `docs/tdq/token-budget.json`, `plugins/tdq-workflow-agy/`
  - Sinh ra: `plugins/tdq-workflow-agy/`, `docs/tdq/token-budget.json`, `CHANGELOG.md`
  - Cần: `T1.1`, `T1.2`, `T1.3`, `T1.4`
  - Giao tiếp: Consumes: đầu ra `4` module ở Wave 1 | Produces: gói plugin `0.105.0` đã biên dịch và bảng ngân sách token đã khóa
  - Neo & Công cụ: Chạy `scripts/doc_index.py --tat-ca`, `scripts/token_budget.py --ghi`, `tools/build_agy_plugin.py`, `agy plugin validate` (`105 passed, 398 subtests passed`; `67/67` token files `<= 3500`; `agy plugin validate` `"findings": []`)
  - Trước → Sau: bản đóng gói `0.104.0` + test tĩnh cũ → gói `0.105.0` sạch findings kèm test hành vi thật
  - Tiêu chí chấp nhận (EARS): KHI đóng gói xong, `token_budget.py` báo `0` file vượt `3.500` token và `agy plugin validate` báo `0` findings
  - Logic cốt lõi: gộp thay đổi `P1`, nâng cấp integration/visual test, bump `0.104.0 → 0.105.0` và build plugin Antigravity
  - Ca góc hiểm & Assert: kiểm `plugins/tdq-workflow-agy/hooks/scripts/prompt_context.py` khớp đồng bộ với nguồn; `assert validate == 0`

**Xong P2 khi**: `plugins/tdq-workflow-agy/` mang phiên bản `0.105.0`, khóa token sạch và mọi test tích hợp pass.

## P3 — Wave 3: Kiểm chứng toàn hệ thống, Báo cáo `2` tầng & Web HTML tiếng Việt

Log: giữ ghi chép theo chuẩn TDQ qua `tdq_finish.py --files ... --log ...` khi chốt pha.

- [x] **T3.1** (e10m) Chạy kiểm chứng toàn bộ (`tdq_meta_gate.py`, `doc_lint.py` toàn repo, `tdq_test.py --smoke-e2e`, `tdq_test.py --tron-bo --workers auto`), ghi biên bản `qc.md`, xuất báo cáo cuối `2` tầng `.md` + Archify HTML tiếng Việt, xác thực Tailscale `HTTP 200` và kiểm giao diện web bằng Chrome DevTools `take_snapshot` (`0` lỗi console) — Test: `py -3 -X utf8 scripts/tdq_meta_gate.py`
  - Dùng: `tdq-browser-test` (mcp)
  - Để: nghiệm thu trang web báo cáo tiếng Việt thật qua Accessibility Tree và bắt `0` lỗi console JS
  - Ra: `docs/tdq/reports/2026-11-21-1819-trien-khai-trinh-bay-2-tang.html` và bằng chứng `QC Card`
  - Kiểm: `py -3 -X utf8 scripts/tdq_archify.py verify --document docs/tdq/reports/2026-11-21-1819-trien-khai-trinh-bay-2-tang.md --manifest docs/tdq/reports/2026-11-21-1819-trien-khai-trinh-bay-2-tang.manifest.json --project .`
  - Không dùng cho: sửa mã nguồn sản phẩm hay chạy thay test suite Python
  - Req: `§4, §6, Q6, Q7` · Ngoài phạm vi: không tự ý commit/push trước khi user gật đầu · Worktree: `no_worktree`
  - Chạm: `docs/tdq/qc/2026-11-21-1819-trien-khai-trinh-bay-2-tang.md`, `docs/tdq/reports/2026-11-21-1819-trien-khai-trinh-bay-2-tang.md`, `docs/tdq/reports/2026-11-21-1819-trien-khai-trinh-bay-2-tang.html`, `docs/tdq/artifacts/2026-11-21-1819-trien-khai-trinh-bay-2-tang/bao-cao.archify.md`
  - Sinh ra: `docs/tdq/qc/2026-11-21-1819-trien-khai-trinh-bay-2-tang.md`, `docs/tdq/reports/2026-11-21-1819-trien-khai-trinh-bay-2-tang.md`, `docs/tdq/reports/2026-11-21-1819-trien-khai-trinh-bay-2-tang.html`, `docs/tdq/artifacts/2026-11-21-1819-trien-khai-trinh-bay-2-tang/bao-cao.archify.md`
  - Cần: `T2.1`
  - Giao tiếp: Consumes: toàn bộ repo và plugin `0.105.0` | Produces: `Dev Behavior QC Card`, báo cáo `.md` sạch `R16` và HTML tiếng Việt sống trên Tailscale
  - Neo & Công cụ: Nạp `skills/tdq-browser-test/SKILL.md` trước khi kiểm Chrome MCP; chạy `tdq_timing.py show` nguyên văn trước khi render HTML cuối
  - Trước → Sau: chưa kiểm chứng toàn suite sau `0.105.0` → toàn suite pass `0` fail và giao diện web hiển thị tiếng Việt trực quan
  - Tiêu chí chấp nhận (EARS): KHI chạy toàn bộ kiểm chứng `Q6–Q7`, `tron-bo` PHẢI pass `0` fail trong `<= 420` giây, `doc_lint` toàn repo = `0` lỗi và Chrome `take_snapshot` hiện UI tiếng Việt `0` lỗi console
  - Logic cốt lõi: chạy meta-gate + lint + smoke + full suite → viết QC Card → viết báo cáo + timing → dựng & kiểm HTML tiếng Việt trên Tailscale
  - Ca góc hiểm & Assert: chỉnh báo cáo `.md` TRƯỚC khi `render` lần cuối; `assert console_errors == 0 and http_status == 200`

## Cụm song song

- **Wave 1 (chạy song song `4` task độc lập, mỗi nhánh dùng `worktree` riêng nếu chạy `subagent`):** `T1.1` (quy chuẩn & khuôn mẫu), `T1.2` (hook `[TDQ:PLAIN]`), `T1.3` (luật `R16`), `T1.4` (Việt hóa Archify HTML). Không có tệp nào trùng ở trường `Chạm:`.
- **Wave 2 (tuần tự sau Wave 1):** `T2.1` gộp và chạy test tích hợp, khóa token budget, bump `0.105.0` và biên dịch `plugins/tdq-workflow-agy/`.
- **Wave 3 (tuần tự sau Wave 2):** `T3.1` kiểm full suite, viết QC, dựng báo cáo cuối và kiểm duyệt web thực tế bằng Chrome DevTools `(mcp)`.

## Luật file nóng

Bốn nhánh ở Wave 1 sở hữu danh sách tệp hoàn toàn tách rời nhau dưới `skills/`, `tools/patches/` + `hooks/`, `scripts/doc_lint.py`, và `scripts/tdq_archify.py`. Toàn bộ thư mục biên dịch `plugins/tdq-workflow-agy/` và hai bài test tích hợp `tests/test_report_visual.py`, `tests/test_hooks_dual_protocol.py` chỉ được chạm tập trung tại Wave 2 (`T2.1`) để triệt tiêu xung đột gộp nhánh.

## QC vòng 1 — fix

- [x] **QC1.1** (e5m) Vá `Q4` trong `scripts/tdq_archify.py`: dịch `分支 (\d+)` → `Nhánh \1` trên SVG, JSON `#archify-explainer-prepared` và cả `diagram.htmlGzip` giải nén, kèm test hồi quy trong `tests/test_archify_vi.py` (unit + render thật `@workflow` nhiều hàng) — Test: `py -3 -X utf8 -m pytest tests/test_archify_vi.py -q`
- [x] **QC1.2** (e5m) Vá `Q5`: thêm `<!-- i18n-allow -->` cho `10` dòng tiếng Việt chuẩn mới thêm ở `qc.md`, `report-template.md`, `user-facing-block.md` (`delta <= 0` so với `dev`), khóa `token-budget.json`, dựng lại `plugins/tdq-workflow-agy/` (`0.105.0`) và chạy `tron-bo` lần cuối (`3/3`) — Test: `py -3 -X utf8 scripts/tdq_test.py tron-bo --workers auto`

## Definition of Done

- [x] Q1 Quy chuẩn `user-facing-block*.md` và khuôn mẫu `spec`/`plan`/`report`/`qc` dưới `3.500` token thống nhất chuẩn `2` tầng và bỏ bọc backtick số — Test: `py -3 -X utf8 -m pytest tests/test_user_facing_block.py -q`
- [x] Q2 Hook `[TDQ:PLAIN]` (`23` mã `[TDQ:*]`) hoạt động ở `spec`, `plan`, `report` cả hai môi trường — Test: `py -3 -X utf8 -m pytest tests/test_gate_guidance.py tests/test_hooks_dual_protocol.py -q`
- [x] Q3 Luật `R16` (`R16_MOC = "2026-11-21-1819"`) chặn đúng vi phạm Lớp 1 mới và pass `doc_lint` toàn repo — Test: `py -3 -X utf8 -m pytest tests/test_doc_lint_r16.py -q`
- [x] Q4 `scripts/tdq_archify.py` Việt hóa chuẩn xác HTML và `explainer-reader-words` khi `doc_lang=vi` — Test: `py -3 -X utf8 -m pytest tests/test_archify_vi.py -q`
- [x] Q5 Nâng cấp `test_report_visual.py`, khóa `token-budget.json`, đóng gói `plugins/tdq-workflow-agy/` bản `0.105.0` sạch findings — Test: `py -3 -X utf8 scripts/tdq_meta_gate.py`
- [x] Q6 Chạy sạch `doc_lint.py` toàn repo, `smoke-e2e` và `tron-bo --workers auto` (`0` fail, `<= 420s`) — Test: `py -3 -X utf8 scripts/tdq_test.py --tron-bo --workers auto`
- [x] Q7 Báo cáo cuối `.md` + Archify HTML tiếng Việt đạt `status=current`, Tailscale `HTTP 200`, `0` lỗi console qua `take_snapshot` — Test: `py -3 -X utf8 scripts/tdq_archify.py verify --document docs/tdq/reports/2026-11-21-1819-trien-khai-trinh-bay-2-tang.md --manifest docs/tdq/reports/2026-11-21-1819-trien-khai-trinh-bay-2-tang.manifest.json --project .`
