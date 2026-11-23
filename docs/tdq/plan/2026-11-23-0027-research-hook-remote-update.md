# QUICK — Nghiên cứu tính khả thi hook kiểm tra bản mới từ Git remote

**Ngày:** 2026-11-23 · Brief: ../brief/2026-11-23-0027-research-hook-remote-update.md · Lane: quick
**Trạng thái:** HOÀN THÀNH · Work kind: investigate
**Ước tính sẽ dùng skill:** plugin (kiểm tra quy ước cài/cập nhật plugin của Antigravity khi cần)

> **Tóm tắt dễ hiểu:** Hiện tại Antigravity không tự kiểm tra hay báo khi có bản mới trên Git remote. Nghiên cứu này sẽ đối chiếu cơ chế hook, lệnh `agy plugin`, và luồng `setupfully` hiện có trong repo. Kết quả sẽ trả lời rõ có khả thi không, kèm kiến trúc an toàn và danh sách rủi ro trước khi code.

## Phạm vi
- **Trong:** Phân tích mã nguồn hiện có (`hooks/`, `scripts/tdq_setup.py`, `scripts/tdq_setup_state.py`, `tools/install_agy_plugin.py`, `hooks/rust/tdq-dispatch/`), kiểm chứng hành vi CLI `agy plugin`, so sánh cách đọc phiên bản nhánh remote, đánh giá rủi ro Windows/bảo mật/UX, và xuất báo cáo kèm Archify HTML.
- **NGOÀI:** Không sửa mã nguồn sản phẩm, không tạo hook mới, không cài đè plugin thật đang chạy, và không push lên Git remote.
- **Bỏ B0:** Nghiên cứu khả thi kỹ thuật không sửa UI hay mã sản phẩm nên không cần mockup/browser baseline.
- **B2 (ngoài repo):** Kiểm tra tài liệu builtin `plugin` skill và chạy thử đọc-chỉ (`git ls-remote`, `agy plugin list --json`) để xác minh thực tế trên máy Windows.

## Task
- [x] **T1** (e6m) Kiểm chứng giả thuyết H1 về hook nền và kênh nhắc trong chat trên Antigravity — Kiểm: ghi đủ chứng cứ `path:line` vào `evidence.jsonl`.
  - Khảo sát: `hooks/scripts/session_start.py`, `hooks/scripts/prompt_context.py`, `hooks/rust/tdq-dispatch/src/events/{session_start,pre_invocation}.rs`, `tools/patches/agy_hooks.py`, `scripts/tdq_hook_launcher.mjs`.
  - Câu hỏi trả lời: `SessionStart` Rust có gọi được background probe không, hay cần trigger ở `tdq_hook_launcher.mjs`/`PreInvocation`, và kênh nào hiện nhắc rõ nhất (`injectSteps` vs `user_markdown`).
- [x] **T2** (e6m) Kiểm chứng giả thuyết H2 về cơ chế kiểm tra bản mới trên nhánh Git remote — Kiểm: bảng so sánh phương án kèm kết quả đo thực tế `git ls-remote` / raw URL trên repo hiện tại vào `evidence.jsonl`.
  - Khảo sát: `scripts/tdq_setup.py:772-1003`, `plugins/tdq-workflow-agy/plugin.json`, `README-Antigravity.md`, đo thời gian thật `git ls-remote --heads` và phân tích raw `plugin.json` / GitHub API / offline / TTL / repo private.
- [x] **T3** (e6m) Kiểm chứng giả thuyết H3 & H4 về luồng xin quyền, cài đè bản mới trên Windows và nối tiếp `setupfully` — Kiểm: ghi kết quả kiểm chứng CLI `agy plugin`, cơ chế khóa file và bảo toàn state/backup vào `evidence.jsonl`.
  - Khảo sát: `scripts/tdq_setup_state.py`, `tools/install_agy_plugin.py`, `tools/sync_plugin_bundle.py`, tài liệu `plugin` skill, và lệnh đọc-chỉ `agy plugin list --json`.
  - Trọng tâm: xác minh cách cập nhật bản mới (GitHub URL vs clone tạm + `install_agy_plugin.py`), xử lý khóa file `.exe`/`agent-lsp` trên Windows, giữ `caveman` wrap, sao lưu `${PLUGIN_DATA}/backups/`, và chống lặp nhắc/kích hoạt nhầm.
- [x] **T4** (e5m) Tổng hợp kết luận khả thi, kiến trúc đề xuất, kiểm chứng `QC-I1..I4` và xuất báo cáo — Kiểm: `doc_lint.py` PASS, `QC-I1..I4` PASS, Archify HTML phục vụ HTTP 200.
  - Đầu ra: `docs/tdq/reports/2026-11-23-0027-research-hook-remote-update.md` và `docs/tdq/reports/2026-11-23-0027-research-hook-remote-update.html`.

## Definition of Done
- Toàn bộ 4 giả thuyết H1–H4 đều có kết luận rõ ràng (Xác nhận / Xác nhận có điều kiện / Bác bỏ) kèm nhãn độ tin cậy và dẫn chứng `path:line` hoặc đầu ra lệnh thật trong `docs/tdq/artifacts/2026-11-23-0027-research-hook-remote-update/evidence.jsonl`.
- Đạt đủ 4 tiêu chí `QC-I1..I4` (grounding, kiểm chứng giả thuyết, không để sót nguồn quan trọng, không khẳng định không có nguồn).
- Không sửa bất kỳ file mã nguồn sản phẩm nào (`git diff --name-only dev -- scripts/ hooks/ plugins/ tools/ tests/` rỗng).
- Báo cáo cuối trình bày rõ kết luận khả thi, 2–3 phương án so sánh, kiến trúc khuyến nghị và danh sách rủi ro trước khi code; qua `py -3 -X utf8 scripts/doc_lint.py` và xác nhận HTTP 200 trên Archify HTML.

## QC
- **Q1 T1–T4 kiểm tra từng task:** PASS — `tdq_team.py evidence merge` hợp nhất `13` bằng chứng qua `4` shard (`t1`–`t4`), `0` khoảng mù chưa kiểm.
- **Q2 DoD "4 giả thuyết H1–H4 có kết luận + dẫn chứng trong evidence.jsonl":** PASS — `13/13` ID đối chiếu khớp `evidence.jsonl` (`QC-I1_IDs: 13 missing: []`), `20/20` cặp `path:line` khớp dòng thật trên đĩa (`QC-I1_Paths: 20 bad: []`).
- **Q3 DoD "QC-I1..I4 (grounding, bác bỏ giả thuyết, không bỏ sót nguồn, nhãn tin cậy)":** PASS — bác bỏ 2 giả định (đường dẫn `plugin.json` trên `release/antigravity` trả HTTP 404 tại subpath và `agy plugin install --help` báo `must be a directory`); kiểm trực tiếp L2 `prompt_context.py:625` & `test_hook_setup_resume.py:233-285`; gắn nhãn `Verified`/`Conditional`/`Inferred` rõ từng mục (`QC-I4`).
- **Q4 DoD "0 file mã nguồn bị sửa":** PASS — `git diff --name-only dev -- scripts/ hooks/ plugins/ tools/ tests/` trả rỗng (`0` file).
- **Q5 DoD "doc_lint.py & Archify HTML HTTP 200":** PASS — `doc_lint.py` đạt `0 violation(s), exit 0`; Archify render + verify + HTTP 200 trên Tailscale Serve.
