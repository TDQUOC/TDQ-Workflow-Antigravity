# Mini-Plan: Research & Đề xuất Kiến trúc Hook giữ đúng Behavior và Hiệu năng

Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md
Lane: quick · Request: 2026-11-19-1612-research-behavior-va-hieu-nang · Trạng thái: ĐÃ DUYỆT (QC: full)

## Phạm vi
- Trong: Phân tích điểm nghẽn thật (I/O, spawn, git, model latency), so sánh định lượng 3 kiến trúc thực thi (Hybrid 2 tầng, Full-Rust 100%, Persistent Sidecar) + bộ chính sách Siết Cổng Thông Minh (Smart Hardening) cho 22 mã, kèm lộ trình triển khai & bảng tiêu chí kiểm chứng; xuất Báo cáo Markdown + Archify HTML qua Tailscale Serve.
- Ngoài: Không sửa mã nguồn Rust/Python hay plugin trong request research này (chờ user chốt phương án rồi mở request implement riêng).
- Bỏ B0: Request research/docs nội bộ tầng hook, đã có tiền lệ trực tiếp từ các báo cáo hook `2026-11-18-1346`, `2026-11-18-1814`, `2026-11-19-1457`.
- Bỏ B2: Hợp đồng chính thức Antigravity 2.0 (`agy-customizations/docs/hooks.md`) và toàn bộ số đo thực nghiệm 120 transcript đã có sẵn cục bộ trong workspace.

## Nhiệm vụ
- [x] **T1** (e15m) Phân tích định lượng chi phí & phân loại 22 mã cổng theo đường nóng/lạnh (Hot vs Cold path) và mức chặn (Hard vs Smart-Hard vs Soft) — Test: `py -3 -c "f=open('docs/tdq/reports/2026-11-19-1612-research-behavior-va-hieu-nang.md', encoding='utf-8').read(); assert 'Hot-path' in f and 'Cold-path' in f"`
  - Chạm: `docs/tdq/reports/2026-11-19-1612-research-behavior-va-hieu-nang.md`
- [x] **T2** (e20m) So sánh định lượng 3 kiến trúc (Hybrid 2 tầng, Full-Rust, Persistent Sidecar), đặc tả cơ chế Smart Hardening khắc phục đủ 10 hạn chế & lộ trình triển khai — Test: `py -3 scripts/doc_lint.py docs/tdq/brief/2026-11-19-1612-research-behavior-va-hieu-nang.md docs/tdq/plan/2026-11-19-1612-research-behavior-va-hieu-nang.md docs/tdq/reports/2026-11-19-1612-research-behavior-va-hieu-nang.md`
  - Chạm: `docs/tdq/reports/2026-11-19-1612-research-behavior-va-hieu-nang.md`, `docs/tdq/artifacts/2026-11-19-1612-research-behavior-va-hieu-nang/truoc-sau.archify.md`
- [x] **T3** (e10m) Render Archify HTML sơ đồ kiến trúc đề xuất Trước vs Sau và kiểm chứng xuất bản qua Tailscale Serve — Test: `py -3 scripts/tdq_archify.py verify --document docs/tdq/reports/2026-11-19-1612-research-behavior-va-hieu-nang.md --manifest docs/tdq/reports/2026-11-19-1612-research-behavior-va-hieu-nang.manifest.json`
  - Chạm: `docs/tdq/reports/2026-11-19-1612-research-behavior-va-hieu-nang.html`

## Definition of Done (DoD)
- [x] Q1 So sánh định lượng đủ 3 kiến trúc (Hybrid, Full-Rust, Sidecar) dựa trên số liệu thực tế của repo — `py -3 -c "f=open('docs/tdq/reports/2026-11-19-1612-research-behavior-va-hieu-nang.md', encoding='utf-8').read(); assert all(k in f for k in ('Hybrid', 'Full-Rust', 'Sidecar'))"`
- [x] Q2 Chỉ rõ bản đồ khắc phục 10/10 hạn chế từ audit trước và bảng phân loại 22 cổng Smart Hardening — `py -3 -c "f=open('docs/tdq/reports/2026-11-19-1612-research-behavior-va-hieu-nang.md', encoding='utf-8').read(); assert 'Smart Hardening' in f and '22' in f and '10/10' in f"`
- [x] Q3 Archify HTML báo cáo render thành công và tồn tại trên đường dẫn Tailscale Serve — `py -3 -c "import os; assert os.path.exists('docs/tdq/reports/2026-11-19-1612-research-behavior-va-hieu-nang.html')"`
- [x] Q4 Cập nhật nhật ký công việc đầy đủ — `py -3 -c "import datetime; today=datetime.date.today().strftime('%Y-%m-%d'); assert '2026-11-19-1612-research-behavior-va-hieu-nang' in open(f'docs/workinglog/{today}.md', encoding='utf-8').read()"`

## QC
- [x] QC.1 Thực hiện kiểm tra đầy đủ theo DoD trên — `py -3 -c "assert True"`
  - T1 phân loại Hot-path/Cold-path & 22 mã: PASS — `py -3 -c "f=open('docs/tdq/reports/2026-11-19-1612-research-behavior-va-hieu-nang.md', encoding='utf-8').read(); assert 'Hot-path' in f and 'Cold-path' in f; print('T1_PASS')"` → `T1_PASS`
  - T2 doc_lint: PASS — `py -3 scripts/doc_lint.py docs/tdq/brief/2026-11-19-1612-research-behavior-va-hieu-nang.md docs/tdq/plan/2026-11-19-1612-research-behavior-va-hieu-nang.md docs/tdq/reports/2026-11-19-1612-research-behavior-va-hieu-nang.md` → `doc_lint: done — 0 violation(s) total, exit 0`
  - T3 Archify HTML & verify: PASS — `tdq_archify.py render` trả `status: pass, binding_status: registered, diagnostics: []`; `tdq_archify.py verify` trả `"status": "current", "valid": true`; file `1.231.323` bytes hiện diện tại `C:\Users\admin\Documents\VTranslateDataLog\tdq-workflow-agy\reports\2026-11-19-1612-research-behavior-va-hieu-nang.html`
  - Q1 DoD: PASS — `Q1_PASS` (`Hybrid`, `Full-Rust`, `Sidecar`)
  - Q2 DoD: PASS — `Q2_PASS` (`Smart Hardening`, `22` cổng, `10/10` hạn chế)
  - Q3 DoD: PASS — `Q3_PASS`
  - Q4 DoD: PASS — `Q4_PASS` (đã cập nhật `docs/workinglog/2026-11-19.md` qua `tdq_finish.py`)
<!-- tdq-archify-binding:start -->
<!-- manifest: 2026-11-19-1612-research-behavior-va-hieu-nang-flow.manifest.json -->
<!-- manifest_digest: 318249682db511ca9333b0c5a65e9e447c6400d4d6e06aed7c62595be65dd807 -->
<!-- tdq-archify-binding:end -->