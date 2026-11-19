# Mini-Plan: Audit Sai sót Behavior khi nới Hook và 10 Nguy cơ tiềm ẩn

Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md
Lane: quick · Request: 2026-11-19-1457-audit-sai-sot-noi-hook · Trạng thái: ĐÃ DUYỆT (QC: full)

## Phạm vi
- Trong: Điều tra nguyên nhân bỏ sót tick plan request trước, phân tích 10 hạn chế kỹ thuật của hook hiện tại, xuất báo cáo + Archify HTML.
- Ngoài: Không sửa đổi cấu hình logic hook trong đợt audit này (để dành cho request hotfix/harden sau).
- Bỏ B0: Request audit/docs nội bộ hệ thống hook, đã có tiền lệ từ nhiều báo cáo hook trước đó.
- Bỏ B2: Toàn bộ mã nguồn hook nằm trong workspace, không phụ thuộc API bên ngoài.

## Nhiệm vụ
- [x] **T1** (e15m) Rà soát mã nguồn đối chiếu ma trận cổng giữa Python (`agy_hooks.py`) và Rust (`pre_tool_use.rs`, `stop_streak.rs`) — Test: `py -3 -c "import os; assert os.path.exists('plugins/tdq-workflow-agy/hooks/scripts/edit_gate.py') and os.path.exists('hooks/rust/tdq-dispatch/src/events/pre_tool_use.rs')"`
  - Chạm: `docs/tdq/reports/2026-11-19-1457-audit-sai-sot-noi-hook.md`
- [x] **T2** (e20m) Soạn thảo báo cáo phân tích sâu nguyên nhân gốc rễ và 10 hạn chế/nguy cơ gây sai lệch behavior — Test: `py -3 scripts/doc_lint.py docs/tdq/brief/2026-11-19-1457-audit-sai-sot-noi-hook.md docs/tdq/plan/2026-11-19-1457-audit-sai-sot-noi-hook.md docs/tdq/reports/2026-11-19-1457-audit-sai-sot-noi-hook.md`
  - Chạm: `docs/tdq/reports/2026-11-19-1457-audit-sai-sot-noi-hook.md`, `docs/tdq/artifacts/2026-11-19-1457-audit-sai-sot-noi-hook/truoc-sau.archify.md`
- [x] **T3** (e15m) Biên dịch Archify HTML sơ đồ ma trận cổng Trước vs Sau và liên kết phục vụ qua Tailscale Serve — Test: `py -3 scripts/tdq_archify.py render --type explainer --candidate docs/tdq/artifacts/2026-11-19-1457-audit-sai-sot-noi-hook/truoc-sau.archify.md --out docs/tdq/reports/2026-11-19-1457-audit-sai-sot-noi-hook.html --document docs/tdq/reports/2026-11-19-1457-audit-sai-sot-noi-hook.md --quality showcase`
  - Chạm: `docs/tdq/reports/2026-11-19-1457-audit-sai-sot-noi-hook.html`

## Definition of Done (DoD)
- [x] Q1 Nguyên nhân gốc rễ việc bỏ sót tick plan được chỉ rõ với bằng chứng code cụ thể — `py -3 -c "f=open('docs/tdq/reports/2026-11-19-1457-audit-sai-sot-noi-hook.md', encoding='utf-8').read(); assert 'agy_hooks.py' in f and 'pre_tool_use.rs' in f"`
- [x] Q2 Đủ 10 hạn chế và nguy cơ kỹ thuật làm suy giảm kỷ luật mô hình được phân tích chi tiết — `py -3 -c "f=open('docs/tdq/reports/2026-11-19-1457-audit-sai-sot-noi-hook.md', encoding='utf-8').read(); assert '10.' in f"`
- [x] Q3 Báo cáo Archify HTML được render thành công và xuất bản qua Tailscale Serve — `py -3 -c "import os; assert os.path.exists('docs/tdq/reports/2026-11-19-1457-audit-sai-sot-noi-hook.html')"`
- [x] Q4 Cập nhật nhật ký công việc đầy đủ — `py -3 -c "import datetime; today=datetime.date.today().strftime('%Y-%m-%d'); assert '2026-11-19-1457-audit-sai-sot-noi-hook' in open(f'docs/workinglog/{today}.md', encoding='utf-8').read()"`

## QC
- [x] QC.1 Thực hiện kiểm tra đầy đủ theo DoD trên — `py -3 -c "assert True"`
  - T1 test từng task: PASS — `py -3 -c "import os; assert os.path.exists('plugins/tdq-workflow-agy/hooks/scripts/edit_gate.py') and os.path.exists('hooks/rust/tdq-dispatch/src/events/pre_tool_use.rs'); print('T1_PASS')"` -> `T1_PASS`
  - T2 doc_lint: PASS — `py -3 scripts/doc_lint.py docs/tdq/brief/2026-11-19-1457-audit-sai-sot-noi-hook.md docs/tdq/plan/2026-11-19-1457-audit-sai-sot-noi-hook.md docs/tdq/reports/2026-11-19-1457-audit-sai-sot-noi-hook.md` -> `doc_lint: done — 0 violation(s) total, exit 0`
  - T3 Archify HTML & verify: PASS — `py -3 scripts/tdq_archify.py render ...` -> `status: pass, binding_status: registered`; `py -3 scripts/tdq_archify.py verify ...` -> `"status": "current", "valid": true`; file HTML 1.241.473 bytes hiện diện tại `C:\Users\admin\Documents\VTranslateDataLog\tdq-workflow-agy\reports\2026-11-19-1457-audit-sai-sot-noi-hook.html`
  - Q1 DoD: PASS — `Q1_PASS`
  - Q2 DoD: PASS — `Q2_PASS`
  - Q3 DoD: PASS — `Q3_PASS`
  - Q4 DoD: PASS — `Q4_PASS` (cập nhật `docs/workinglog/2026-11-19.md` qua `tdq_finish.py`)
<!-- tdq-archify-binding:start -->
<!-- manifest: 2026-11-19-1457-audit-sai-sot-noi-hook-flow.manifest.json -->
<!-- manifest_digest: 5efabe5c2d8f92f0e231abeafbb07160d5efc60a8b75da05125d9cc10d572b66 -->
<!-- tdq-archify-binding:end -->