# Changelog — bản lưu trữ 4

Bản 0.70.0 đến 0.62.0, tách khỏi `CHANGELOG.md` để giữ file chính dưới trần R6 500 dòng. Mới nhất trên cùng, chữ nghĩa copy nguyên văn.

## 0.70.0 — 2026-10-15

Tối ưu hóa toàn diện instruction và kiến trúc Lazy Loading ngữ cảnh cho model tier thấp.
Kế hoạch: `docs/tdq/plan/2026-10-15-1425-cap-nhat-full-de-xuat-instruction.md`.

- **Bộ mã cấm tường minh (`ANTI-1` .. `ANTI-6`).** Tích hợp chuẩn hóa bộ 6 mã cấm cơ học (Fake Red, Blind Assertion, Dirty State Git, Late Tick, Raw Dump, Broad Area) vào các tài liệu hướng dẫn và agent. Giúp các mô hình nhỏ tránh lỗi cú pháp, assertion rỗng và vi phạm checklist.
- **Thư viện Cookbooks thực chiến (Tầng 3).** Xây dựng thư viện Cookbooks tại `skills/tdq-build/references/rules/cookbooks/` với các giải pháp thực chiến cho Python và TypeScript/JS (async concurrency, database transaction context manager, domain error handling, clean architecture dependency injection, structured ISO logging).
- **JIT Micro-injection & Neo Phục Hồi sau Compaction.** Hook `edit_gate.py` tự động mớm 3 dòng quy tắc vàng khi sửa code lần đầu; hook `session_start.py` trang bị Khối Neo Phục Hồi `[TDQ:ANCHOR]` ngắn gọn (< 200 tokens) trỏ lại state, plan và mã cấm khi phiên bị nén (compaction); hook `prompt_context.py` tự mớm DoD checklist khi vào phase `qc`.
- **Chế độ Silent CLI trong `tdq_test.py`.** Hỗ trợ cờ `--silent` ghi log chi tiết ra `docs/tdq/.tdq-test.log`, terminal chỉ in `≤ 2` dòng tóm tắt và lỗi chính, bảo vệ context window khỏi rác log kiểm thử.
- **Bảo toàn hàng rào Codex.** Tinh chỉnh `_la_repo_plugin` trong `scripts/tdq_codex_mcp.py` bảo đảm `.codex/hooks.json` của repo TDQ Workflow luôn giữ đúng hàng rào 2 cổng viết tay.

## 0.69.0 — 2026-10-15

Khắc phục lỗi CLI `tdq_team clean <task>`, tự động phát hiện ngôn ngữ dự án trong search gate và ghim hướng dẫn 3 bước LSP.
Kế hoạch: `docs/tdq/plan/2026-10-15-0958-dieu-tra-loi-lsp-search-team-clean.md`.

- **Hỗ trợ tham số cho lệnh clean.** `scripts/tdq_team.py clean [task]` hỗ trợ tham số task tùy chọn; báo `already cleaned` và thoát `0` nếu task đã được dọn bởi `merge`, tránh văng lỗi CLI cú pháp `exit 2`.
- **Phát hiện ngôn ngữ tự động trong search gate.** `hooks/scripts/search_gate.py` và `scripts/search_rules.py` tự động phát hiện ngôn ngữ dự án (`typescript`, `python`, `go`, `rust`...). Câu thông báo in đúng `language_id` thực tế thay vì gán cứng `e.g. python`, đồng thời tự gợi ý `mcp__lsp__list_symbols` khi grep trong file cụ thể.
- **Hướng dẫn cơ học 3 bước khởi tạo LSP.** `KHOI_HUONG_DAN` trong `scripts/tdq_setup.py`, `CLAUDE.md` và tài liệu tìm kiếm nêu rõ quy trình: gọi `start_lsp` đầu phiên kèm `language_id`. Đối với TypeScript/JS cần mở file bằng `open_document` để tránh bẫy "No Project" trước khi tra cứu symbol.

## 0.68.0 — 2026-10-15

Tách 2 nhánh `dev` (phát triển) và `main` (release sạch), tích hợp khung mindset kiểm thử thực tế và Vision Test Loop.
Kế hoạch: `docs/tdq/plan/2026-10-14-1713-tach-nhanh-dev-main-release.md`.

- **Mô hình 2 nhánh `dev` và `main`.** Nhánh `dev` là nhánh phát triển chính lưu giữ đầy đủ mã nguồn, tài liệu, test và công cụ nội bộ; nhánh `main` là nhánh phát hành gọn sạch (~135 files, giảm 90.8% số file và 93.5% dung lượng).
- **Lệnh phát hành Git plumbing.** Mở rộng `scripts/build_portable.py` với cờ `--sinh-main [--nguon] [--nhanh-dich] [--dry-run]` tự động tạo commit snapshot release độc lập trên `main` qua Git plumbing (`commit-tree` trên `GIT_INDEX_FILE` tạm), tránh xung đột merge `modify/delete` và không làm bẩn working tree hiện tại.
- **Tự động nhận diện nhánh gốc.** `scripts/tdq_test.py` tự động nhận diện nhánh `dev` làm `nhanh_goc` mặc định khi tồn tại trong repo để tính vùng chạm chính xác.
- **Vision Test Loop & Mindset kiểm thử thực tế.** Công cụ `scripts/tdq_vision_diff.py` và hướng dẫn `skills/tdq-build/references/vision-test-loop.md` hỗ trợ đối chiếu giao diện hình ảnh, Canvas Padding, Masking, Bounding Box đánh số, xuất báo cáo `.md`/`.html` và tích hợp Figma.

## 0.67.0 — 2026-10-14

Bổ sung chế độ kích hoạt nhanh `_tdq_direct` tự động phân tích mã nguồn và chỉ có 1 cổng duyệt mini-plan.
Kế hoạch: `docs/tdq/plan/2026-10-14-1022-che-do-tdq-direct.md`.

- **Nhận diện `_tdq_direct` trong prompt.** Hook `prompt_context.py` nhận diện từ khóa `_tdq_direct` (không phân biệt hoa thường) khi chưa có request mở hoặc phase idle, phát tín hiệu `[TDQ:INTAKE]` chạy thẳng chế độ direct.
- **Tự động hóa luồng tiếp nhận.** Skill `tdq-intake` và `quick-lane.md` bỏ qua hỏi chọn pipeline & phỏng vấn, tự động `init <slug> quick`, mở git branch và chuyển thẳng Part C; chạy tìm kiếm 3 tầng (LSP, graphify, grep), lập mini-plan ≤ 40 dòng trong `docs/tdq/plan/<slug>.md`, chỉ dừng đúng 1 cổng duyệt `quick_approved` rồi implement.
- **Đồng bộ khối ghim instruction.** Bổ sung nguyên tắc `_tdq_direct` vào `KHOI_HUONG_DAN` của `tdq_setup.py` và mẫu `docs/claude-md-mau.md`.

## 0.66.0 — 2026-10-11

Khắc phục lỗi Unknown skill tdq-intake do thiếu namespace plugin `tdq-workflow:`.
Kế hoạch: `docs/tdq/plan/2026-10-11-1539-fix-plugin-skill-namespace.md`.

- **Namespace đầy đủ cho skill.** Hướng dẫn trong `KHOI_HUONG_DAN`, `~/.claude/CLAUDE.md` và tài liệu ghi rõ `tdq-workflow:tdq-intake`. Giữ dự phòng `(hoặc tdq-intake nếu cài cục bộ)`.
- **Chuẩn hóa hook prompt_context.** Dòng nhắc `[TDQ:INTAKE]` dùng `tdq-workflow:tdq-intake`, đảm bảo độ dài không vượt trần test.

## 0.65.0 — 2026-10-11

Cấm attribution trailer `Co-Authored-By`, chuẩn hóa đường dẫn script plugin trong toàn bộ skills.
Kế hoạch: `docs/tdq/plan/2026-10-11-1346-cam-co-author-fix-path-script.md`.

- **Cấm Co-Authored-By.** Thêm điều luật vào `KHOI_HUONG_DAN` của `tdq_setup.py`; đồng bộ `~/.claude/CLAUDE.md`, conventions và mẫu report.
- **Chuẩn hóa đường dẫn script.** Các lệnh nội bộ trong `skills/` dùng `${CLAUDE_PLUGIN_ROOT}` để chạy đúng khi working directory là project khác.

## 0.64.0 — 2026-10-11

Siết chặt cổng duyệt: yêu cầu lệnh chính thức hoặc đủ động từ + tân ngữ, gỡ bỏ duyệt tự nhiên trần.
Kế hoạch: `docs/tdq/plan/2026-10-11-1327-siet-chat-cong-duyet-lenh.md`.

- **Siết cổng duyệt.** Xóa `ACTION_APPROVAL` và gỡ mục "Natural action phrases" trong `approval.md`. Các câu mệnh lệnh trần ("làm đi", "tiến hành đi", "go ahead") không còn được chấp nhận nếu thiếu đối tượng hoặc đại từ (`spec`, `plan`, `quick`, `cái này`).

## 0.63.0 — 2026-10-11

Tự động mang theo các file docs/log khi mở request branch.
Kế hoạch: `docs/tdq/plan/2026-10-11-1300-tu-dong-mo-nhanh-doc-log.md`.

- **Mở branch không ngắt quãng cho docs/log.** Ở bước 3b của `tdq-intake`, nếu working tree chỉ có tài liệu, log hoặc cache (`docs/**`, `*.md`, `logs/**`, `*.log`), hệ thống tự động tạo branch và mang file theo. Có file code thì dừng hỏi người dùng.

## 0.62.0 — 2026-10-11

Tự động cập nhật setup, dependencies và instruction user-level (`CLAUDE.md`) khi phát hiện version mới
qua hook `SessionStart`, không đòi hỏi chạy thủ công lại lệnh setup, áp dụng cho cả Claude Code và Codex.
Kèm bộ rào chắn cấm đổi mode harness (`EnterPlanMode`) và ép bắt buộc mở request bằng `tdq-intake`.
Kế hoạch: `docs/tdq/plan/2026-10-11-0932-auto-update-setup-version.md`.

- **Tự động đồng bộ khi đổi version.** `hooks/scripts/session_start.py` và `scripts/tdq_setup.py` kiểm tra
  phiên bản plugin hiện tại; nếu chưa có mốc hoặc có version mới hơn, tự động đồng bộ instruction vào
  `~/.claude/CLAUDE.md`, khai báo MCP/hook cho Codex và dọn tiến trình broker thừa, sau đó ghi mốc
  `docs/tdq/.tdq-phat-hanh.json`.
- **Rào chắn mode và intake.** Cấm tự ý đổi mode làm việc, cấm gọi `EnterPlanMode` hoặc popup UI `AskUserQuestion`,
  bắt buộc mọi yêu cầu mới mở qua `tdq-intake` và trao đổi trong chat.
- **Áp dụng đa nền tảng.** Hoạt động đồng bộ êm dịu trên cả Claude Code và Codex.
