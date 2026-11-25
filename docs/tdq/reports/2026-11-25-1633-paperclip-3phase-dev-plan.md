# BÁO CÁO — Bộ Development Plan Chi tiết `3` Pha Tích hợp Paperclip (`P0`–`P2`)

Ngày: 2026-11-25 · Request: `2026-11-25-1633-paperclip-3phase-dev-plan`
Loại: `docs` (`investigate`) · Nhánh: `docs/paperclip-3phase-dev-plan`

> **Tóm tắt dễ hiểu:** Trước khi sửa code thật, chúng tôi đã rà soát sâu mã nguồn Python và Rust để lập bộ kế hoạch thi công chi tiết. Kết quả gồm một lộ trình tổng và ba bản kế hoạch cho từng pha. Kèm theo là script tự kiểm chứng đường dẫn và chữ ký hàm trên đĩa. Mọi mã nguồn sản phẩm được giữ nguyên và bộ kế hoạch vượt qua bảy lớp kiểm tra tự động.

---

## 1. Trước request

Trước lúc mở request này, dự án mới có bản thiết kế tổng quát [integration-blueprint.md](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/artifacts/2026-11-25-1439-paperclip-tdq-integration-sim/integration-blueprint.md) ở mức ý tưởng cao và chưa đối chiếu chéo toàn bộ điểm nghẽn trên mã nguồn thật. Khi bước vào điều tra sâu (`s1`–`s3`), bốn nút thắt thực tế đã lộ rõ:

- Hàm lưu state chưa có khóa sidecar liên tiến trình ở ngoài hook và vẫn để cảnh báo ghi đè.
- Danh sách xuất nhánh phát hành đang chặn sẵn bộ định tuyến kỹ năng BM25, còn trình kiểm tra ngôn ngữ lại quét cả các file cấu hình JSON.
- Hai mươi ba mã cổng phản hồi của Antigravity đang bị khóa cứng trong bộ kiểm thử parity Python và Rust.
- Chưa có máy kiểm tra tự động để xác nhận bản kế hoạch không đụng file nóng hoặc gán nhầm hàm giữa các tệp.

---

## 2. Sau request

Request đã xuất đủ `3` hồ sơ khảo sát (`s1`–`s3`), sổ `26` bằng chứng thật (`evidence.jsonl`), trọn bộ `4` tài liệu kế hoạch và script tự kiểm `verify_plans.py` với `0` dòng mã nguồn sản phẩm bị sửa:

| Hạng mục đầu ra | Tác dụng & Nội dung chính | Liên kết |
|---|---|---|
| Sổ bằng chứng `s1`–`s3` | Khóa `26` vị trí thật (`file:line`) trên Python, Rust, bộ test và dây chuyền đóng gói | [evidence-log.md](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/artifacts/2026-11-25-1633-paperclip-3phase-dev-plan/evidence-log.md) |
| Lộ trình tổng thể `P0`–`P2` | Khóa quyết định `1abcd 2a 3a 4a 5a` + `1c 2a 3a 4a 5c`, giả thuyết `H1`–`H4`, luật `docs/kien-truc.md`, quy trình `dev`/`main` và đủ `6` mục CẤM copy | [master-roadmap.md](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/artifacts/2026-11-25-1633-paperclip-3phase-dev-plan/master-roadmap.md) |
| Kế hoạch `P0` (`1` request `feature`) | Chia `4` wave tách file nóng (`0` phụ thuộc cùng wave): `tdq_lease.py`, `state.json` v6 additive, `tdq_team` queue + `blocked_by`, `tdq_timing` budget, `mcp_policy.py` cân bằng, mở matcher `hooks/hooks.json:76` & `agy_manifests.py:72`, gắn `edit_gate`/`bash_gate`/`lsp_gate` & `pre_tool_use.rs` tái dụng `READONLY` giữ đủ `23` AGY code | [dev-plan-p0.md](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/artifacts/2026-11-25-1633-paperclip-3phase-dev-plan/dev-plan-p0.md) |
| Kế hoạch `P1` (`1` request `feature`) | Chia `4` wave tách file nóng cho `4` gói domain JSON ASCII không dấu dưới `scripts/defaults/domains/`, nối `KhoBM25`, gỡ loại trừ `skill_router.py` ở `RELEASE_EXCLUDE_SCRIPTS`, khóa `Zero-Downgrade` (`escalate-to-build`) và giữ `TRAN_TOKEN <= 3500` | [dev-plan-p1.md](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/artifacts/2026-11-25-1633-paperclip-3phase-dev-plan/dev-plan-p1.md) |
| Kế hoạch `P2` (Add-on tắt mặc định) | Chia `3` wave tách rời cho CLI `1` chiều `scripts/tdq_paperclip_bridge.py` (`enabled: false`, thuần stdlib, gọi `tdq_state.py init`, test mock stdlib, xóa sạch nếu cần rollback) | [dev-plan-p2.md](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/artifacts/2026-11-25-1633-paperclip-3phase-dev-plan/dev-plan-p2.md) |
| Script kiểm chứng & trang HTML | Tự kiểm tra AST symbol, JSON, luật import, wave và xuất trang Archify HTML trực quan | [verify_plans.py](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/artifacts/2026-11-25-1633-paperclip-3phase-dev-plan/verify_plans.py) · [HTML](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/reports/2026-11-25-1633-paperclip-3phase-dev-plan.html) |
| Biên bản QC mức `ultra` | Ghi nhận đủ `6/6` cổng `Q1`–`Q6` PASS qua `3` vòng thẩm định độc lập (`Verdict: PASS`, `DEFECTS: None`) và `15/15` neo mã nguồn thật | [qc.md](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/qc/2026-11-25-1633-paperclip-3phase-dev-plan.md) |

---

## 3. Đã test gì

1. Kiểm tra định dạng tài liệu TDQ (`doc_lint.py`) cho toàn bộ `s1.md`–`s3.md`, `master-roadmap.md`, `dev-plan-p0/p1/p2.md` và báo cáo hiện tại.
2. Hợp nhất sổ bằng chứng từ `3` shard qua `tdq_team.py evidence merge` và `render`.
3. Chạy [verify_plans.py](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/artifacts/2026-11-25-1633-paperclip-3phase-dev-plan/verify_plans.py) ở cả hai chế độ `TDQ_LOG=1` (xuất [verify-results.json](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/artifacts/2026-11-25-1633-paperclip-3phase-dev-plan/verify-results.json)) và `TDQ_LOG=0` (đo trực tiếp dung lượng luồng `stderr`).
4. Ở lượt tự kiểm đầu và đợt QC vòng `1` của `tdq-qc-tester`, các công cụ kiểm chéo đã phát hiện ba nhóm lỗi thực tế: gán nhầm tệp symbol giữa `agy_dispatch.py`/`command_gate.py`/`command_parser.rs`/`common_utils.py`, phụ thuộc nội bộ cùng một wave trong bảng wave, và thiếu điểm mở matcher non-LSP MCP ở `hooks/hooks.json:76` cùng `tools/patches/agy_manifests.py:72` trong khi `common_utils.py:26` loại trừ `agy_pretooluse_gate.py`. Toàn bộ đã được khắc phục đồng bộ và kiểm chứng lại.
5. Kiểm tra trình bày Archify HTML (`tdq_archify.py render --type explainer --quality showcase` + `verify`) và thăm dò liên kết Tailscale HTTP `200`, sau đó tái thẩm định độc lập vòng `2` qua `tdq-qc-tester`.

---

## 4. Kết quả test

| Hạng mục kiểm | Lệnh chạy | Kết quả thực tế quan sát |
|---|---|---|
| Lint `s1`–`s3`, `4` plan & báo cáo | `py -3 -X utf8 scripts/doc_lint.py ...` | `0 violation(s) total, exit 0` cho toàn bộ tệp kiểm |
| Hợp nhất bằng chứng | `py -3 -X utf8 scripts/tdq_team.py evidence merge` | `26 row(s)` hợp lệ biên dòng, `100%` được trích dẫn trong `4` plan (`0` lỗi biên, `0` bỏ sót) |
| Kiểm tự động `TDQ_LOG=1` | `verify_plans.py --out .../verify-results.json` | **`7 passed, 0 failed`** (`exit 0`): `26/26` evidence, `11/11` khối JSON hợp lệ, `90` symbol đĩa + `16` file mới hợp lệ, `78` script đều `0` vi phạm import `hooks/`, `11` wave (`24` task, `32` cạnh phụ thuộc) có `0` trùng file nóng và `0` phụ thuộc cùng/sau wave, `100%` quyết định + `6` mục cấm phủ đủ, self-test phủ định `5/5` `True` |
| Kiểm im lặng `TDQ_LOG=0` | `TDQ_LOG=0` + chạy `verify_plans.py` | `exit 0`, `err0_bytes=0` (`0B` stderr) |
| Nghiệm thu `ultra` (`Q6`) | `3` vòng `tdq-qc-tester` + `15/15` neo đĩa + `tdq_archify.py verify` + Tailscale HTTP `200` | **`PASS` (`6/6` cổng `Q1`–`Q6`, `DEFECTS: None`)** tại vòng 3 (`1bdd8bde`); Archify `status=current` (`0` diagnostics), Tailscale HTTP `200`, `0` thay đổi ngoài `docs/tdq/` — xem [qc.md](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/qc/2026-11-25-1633-paperclip-3phase-dev-plan.md) |

---

## Thời gian

Request `2026-11-25-1633-paperclip-3phase-dev-plan` · lane full · opened at 2026-11-25T16:38:55+07:00

| Phase | Wall clock | Times entered |
|---|---|---|
| idle | 0s | 1 |
| analyze | 10 min | 1 |
| spec | 5 min | 1 |
| plan | 4 min | 1 |
| mode | 6 min | 1 |
| implement | 16 min | 1 |
| qc | 25 min | 1 |
| Total | 1h 05min |  |

---

## Thân PR

```markdown
docs(tdq): add detailed 3-phase Paperclip integration dev plans (P0-P2)

- Conduct read-only deep source audit across Python scripts, hooks, Rust tdq-dispatch, and packaging pipelines (`s1`–`s3`, `26` grounded line-bounded evidence rows).
- Publish `master-roadmap.md` and `dev-plan-p0/p1/p2.md` covering unified `P0` feature request (`1c`), `scripts/defaults/` + `schema_version=6` (`2a`), balanced P0 defaults (`3a`), opt-in 1-way `P2` CLI bridge (`4a`), Rust parity, and `6` banned Paperclip anti-patterns.
- Add `verify_plans.py` confirming `7/7` automated checks (`26` evidence rows, `11` valid JSON contracts, `90` disk symbols, `78` scripts import-clean, `11` disjoint waves across `24` tasks and `32` dependency edges, counterfactual negative tests, and `0B` stderr on `TDQ_LOG=0`).
```
<!-- tdq-archify-binding:start -->
<!-- manifest: 2026-11-25-1633-paperclip-3phase-dev-plan.manifest.json -->
<!-- manifest_digest: b6417f81444ad45ca604a3c638365f07730ef392846d36643f697ebed03cf61a -->
<!-- tdq-archify-binding:end -->