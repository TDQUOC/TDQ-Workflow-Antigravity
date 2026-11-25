# PLAN — Phân tích kiến trúc & Bộ Development Plan chi tiết tối ưu cho 3 pha tích hợp Paperclip (P0–P2)

Ngày: 2026-11-25 · Spec: ../spec/2026-11-25-1633-paperclip-3phase-dev-plan.md (bản 1.0, ĐÃ DUYỆT)
Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md
Mode thực thi: main — simulate thắng với chênh lệch 2.1 phút (`main` 16.3 phút vs `team` 18.4 phút ở hệ số agent 1.5, 8 task qua 6 đợt); nếu chọn `subagent` vẫn tách song song được `T1.1`–`T1.3` ở Đợt 1 (ĐỀ XUẤT, user chốt lúc duyệt)
Trạng thái plan: HOÀN THÀNH · Work kind: investigate

> **Tóm tắt dễ hiểu:** Kế hoạch chia đợt phân tích và soạn bộ bản vẽ thi công cho ba pha nâng cấp thành ba chặng tách bạch và an toàn. Chặng một khảo sát song song ba trục mã nguồn thật bằng Python và Rust. Chặng hai hợp nhất bằng chứng, viết một lộ trình tổng và ba kế hoạch pha cùng script tự kiểm. Chặng ba chạy kiểm chứng độc lập mức cao nhất và xuất báo cáo trực quan.

## Mục lục

- Phân bổ Model & Effort
- Quy tắc thi hành (áp cho mọi task)
- Thiết kế Trước vs Sau
- Ràng buộc toàn cục & Bản đồ Sở hữu Hợp đồng (Ownership Map)
- P1 — Khảo sát mã nguồn sâu 3 trục (s1–s3)
- P2 — Hợp nhất chứng cứ, bộ Development Plan P0–P2, verify_plans.py & báo cáo
- P3 — Log & kiểm chứng bắt buộc mức ultra (Q1–Q6)
- Cụm song song
- Luật file nóng (một file, nhiều task chạm)
- Definition of Done

## Phân bổ Model & Effort

> User được quyền đổi `type model` hoặc `effort` lúc duyệt plan. Thang model: [subagent-tuning.md](../../tdq-conventions/references/subagent-tuning.md).

| Pha | Vai trò | Model | Effort | Ghi chú |
|---|---|---|---|---|
| `implement` (`T1.1`, `T1.2`, `T1.3`) | `tdq-explorer` (khảo sát mã nguồn sâu + ghi shard artifact) | `inherit` | `high` | Chạy `Worktree: none`, chỉ ghi đúng file shard được giao |
| `implement` (`T2.1`, `T2.2`, `T2.3`, `T2.4`) | Leader (hợp nhất chứng cứ, soạn bộ 4 plan, `verify_plans.py`, báo cáo) | `inherit` | `xhigh` | Soạn hợp đồng JSON/CLI, wave không đụng file nóng và script kiểm chứng |
| `qc` (`T3.1`) | Leader + `tdq-qc-tester` độc lập (`muc_qc=ultra`) | `inherit` | `high` | Kiểm `Q1`–`Q6`, `QC-I1..I4`, chạy `verify_plans.py` và phản biện độc lập |
| `report` | Leader (Archify HTML + Tailscale verify) | `inherit` | `medium` | Dựng Archify HTML `current` và kiểm Tailscale HTTP `200` |

## Quy tắc thi hành (áp cho mọi task)

1. Thứ tự phase là thứ tự phụ thuộc — không đảo.
2. Mỗi task: đánh `[~]` khi bắt đầu → chạy kiểm tra trước (hoặc đối chiếu bằng chứng trước) → viết xong → chạy lệnh test → đổi sang `[x]` NGAY vào file này.
3. Không sửa bất kỳ file mã nguồn sản phẩm nào (`scripts/`, `hooks/`, `plugins/`, `tools/`, `tests/`); mọi file viết ra đều nằm dưới `docs/tdq/`.
4. Mọi lệnh phụ trợ không chạm state của project hiện tại hoặc chạy cô lập trong thư mục tạm.
5. QC FAIL → thêm task fix vào `## QC vòng N — fix` trong file này (không cần duyệt lại), lặp đến khi pass (tối đa `3` vòng).
6. Không commit/push cho đến khi user yêu cầu.
7. Tuân thủ `6` mã cấm cơ học (`ANTI-1` Fake Red, `ANTI-2` Blind Assertion, `ANTI-3` Dirty State Git, `ANTI-4` Late Tick, `ANTI-5` Raw Dump, `ANTI-6` Broad Area).

## Thiết kế Trước vs Sau

| Khía cạnh | Hiện trạng (Trước) | Thiết kế mới (Sau) |
|---|---|---|
| Độ chi tiết lộ trình `P0`–`P2` | Mới có phác thảo 1 trang `integration-blueprint.md` mức ý tưởng | Có `1` Master Roadmap + `3` Development Plan (`dev-plan-p0/p1/p2.md`) bám symbol, wave, test matrix và rollback thật |
| Kiểm chứng trước thi công | Chưa kiểm khớp `with_ntfs_lock`, Rust `lock.rs`/`pre_tool_use.rs`, `TRAN_TOKEN=3500`, `i18n_check.py`, `--sinh-main` | Script `verify_plans.py` đối chiếu tự động mọi symbol trên đĩa, JSON schema và wave không đụng file nóng |

## Ràng buộc toàn cục & Bản đồ Sở hữu Hợp đồng (Ownership Map)

- Quy ước `5b` + `docs/kien-truc.md`: `scripts/` không import `hooks/`; chỉ `tdq_state.py` ghi `state.json` (`schema_version=6`); file code mới thuộc `scripts/` hoặc `hooks/`; `verify_plans.py` thuần stdlib Python (`utf-8`, `TDQ_LOG=0` tắt log); giữ 2 nhánh `dev`/`main` (`build_portable.py --sinh-main`).

| Hợp đồng / Ký hiệu (§3c) | File & Task sở hữu | Task / File tiêu thụ |
|---|---|---|
| Shard `s1` (`P0` lõi + Rust `lock.rs`/`pre_tool_use.rs`) | `docs/tdq/artifacts/2026-11-25-1633-paperclip-3phase-dev-plan/s1.md` (`T1.1`) | `T2.1`, `T2.3`, `T2.4` |
| Shard `s2` (`P1` `Domain Pack` + `KhoBM25` + đóng gói) | `docs/tdq/artifacts/2026-11-25-1633-paperclip-3phase-dev-plan/s2.md` (`T1.2`) | `T2.1`, `T2.2`, `T2.3` |
| Shard `s3` (`P2` CLI Bridge + test harness + bất biến) | `docs/tdq/artifacts/2026-11-25-1633-paperclip-3phase-dev-plan/s3.md` (`T1.3`) | `T2.1`, `T2.2`, `T2.3` |
| Sổ `evidence.jsonl` & `master-roadmap.md` + `dev-plan-p0.md` | `docs/tdq/artifacts/2026-11-25-1633-paperclip-3phase-dev-plan/dev-plan-p0.md` (`T2.1`) | `T2.2`, `T2.3`, `T2.4`, `T3.1` |
| `dev-plan-p1.md` & `dev-plan-p2.md` | `docs/tdq/artifacts/2026-11-25-1633-paperclip-3phase-dev-plan/{dev-plan-p1.md,dev-plan-p2.md}` (`T2.2`) | `T2.3`, `T2.4`, `T3.1` |
| Bộ kiểm tự động `verify_plans.py` & `verify-results.json` | `docs/tdq/artifacts/2026-11-25-1633-paperclip-3phase-dev-plan/verify_plans.py` (`T2.3`) | `T2.4`, `T3.1` |

---

## P1 — Khảo sát mã nguồn sâu 3 trục (`s1`–`s3`)

- [x] **T1.1** (e12m) Khảo sát sâu trục `P0` Lõi điều phối, Hook & Rust parity (`tdq_state.py`, `tdq_team.py`, `tdq_config.py`, `tdq_timing.py`, `_common.py`, `agy_pretooluse_gate.py`, `bash_gate.py`, `lock.rs`, `pre_tool_use.rs`, `test_rust_dispatch_parity.py`, `test_ntfs_concurrency.py`) rồi xuất `s1.md` + `s1.ev.jsonl` (`>= 8` chứng cứ) — Test: `py -3 -X utf8 scripts/doc_lint.py docs/tdq/artifacts/2026-11-25-1633-paperclip-3phase-dev-plan/s1.md`
  - Req: `§1, §2#1, §6 Q1-Q2` · Ngoài phạm vi: `GIỮ NGUYÊN` mã nguồn `scripts/`, `hooks/`, `tests/`
  - Chạm: `docs/tdq/artifacts/2026-11-25-1633-paperclip-3phase-dev-plan/s1.md`, `docs/tdq/artifacts/2026-11-25-1633-paperclip-3phase-dev-plan/s1.ev.jsonl` (tạo mới)
  - Cần: `Không`
  - Giao tiếp: Consumes: `scripts/{tdq_state,tdq_team,tdq_config,tdq_timing}.py`, `hooks/scripts/{_common,agy_pretooluse_gate,bash_gate}.py`, `hooks/rust/tdq-dispatch/src/**`, `tests/test_{rust_dispatch_parity,ntfs_concurrency}.py` | Produces: `s1.md` + `s1.ev.jsonl`
  - Neo & Công cụ: `read_file` khoảng dòng cụ thể + `tdq_team.py evidence add --shard s1`
  - Trước → Sau: Mới biết tên file từ B1 nông → Có chữ ký hàm, dòng chính xác, schema `state.json` v6, điểm nối `with_ntfs_lock` và hợp đồng Rust `PreToolUse`
  - Tiêu chí chấp nhận (EARS): KHI `T1.1` hoàn tất, `s1.ev.jsonl` PHẢI chứa `>= 8` bằng chứng `file:line` khớp nguyên văn trên đĩa và `doc_lint.py` exit `0`
  - Logic cốt lõi: Đọc các hàm lõi `save()`, `with_ntfs_lock`, `chia_dot`, `detect_tcas_collision`, `lock.rs`, `handle_pre_tool_use` và bộ test parity để chốt mọi ràng buộc cho `P0`
  - Ca góc hiểm & Assert: Kiểm tra mọi đường dẫn `file:start-end` đều nằm trong tổng số dòng thật · `assert len(s1_ev_rows) >= 8`

- [x] **T1.2** (e10m) Khảo sát sâu trục `P1` Đa lĩnh vực, Token & Đóng gói (`skill_router.py`, `token_budget.py`, `i18n_check.py`, `build_portable.py`, `tools/build_agy_plugin.py`, `tools/patches/`, `skills/tdq-intake/SKILL.md`, `tests/test_{investigate_workflow,build_portable,sinh_agy}.py`) rồi xuất `s2.md` + `s2.ev.jsonl` (`>= 7` chứng cứ) — Test: `py -3 -X utf8 scripts/doc_lint.py docs/tdq/artifacts/2026-11-25-1633-paperclip-3phase-dev-plan/s2.md`
  - Req: `§1, §2#1, §6 Q1-Q2` · Ngoài phạm vi: `GIỮ NGUYÊN` mã nguồn `scripts/`, `tools/`, `plugins/`, `tests/`
  - Chạm: `docs/tdq/artifacts/2026-11-25-1633-paperclip-3phase-dev-plan/s2.md`, `docs/tdq/artifacts/2026-11-25-1633-paperclip-3phase-dev-plan/s2.ev.jsonl` (tạo mới)
  - Cần: `Không`
  - Giao tiếp: Consumes: `scripts/{skill_router,token_budget,i18n_check,build_portable}.py`, `tools/build_agy_plugin.py`, `tools/patches/*`, `skills/tdq-intake/SKILL.md`, `tests/test_{investigate_workflow,build_portable,sinh_agy}.py` | Produces: `s2.md` + `s2.ev.jsonl`
  - Neo & Công cụ: `read_file` khoảng dòng cụ thể + `tdq_team.py evidence add --shard s2`
  - Trước → Sau: Mới biết tên module đóng gói → Có cơ chế lọc file của `--sinh-main`, mapping patch của `build_agy_plugin.py`, API `KhoBM25` và giới hạn `TRAN_TOKEN = 3500`
  - Tiêu chí chấp nhận (EARS): KHI `T1.2` hoàn tất, `s2.ev.jsonl` PHẢI chứa `>= 7` bằng chứng giải rõ cách `scripts/defaults/` đi qua cả `--sinh-main` và `build_agy_plugin.py`
  - Logic cốt lõi: Đọc dây chuyền build plugin/main, bộ lọc asset của `build_portable.py`, cách tính token và rule `i18n_check.py` + `escalate-to-build`
  - Ca góc hiểm & Assert: Kiểm xem `--sinh-main` có whitelist/blacklist thư mục con dưới `scripts/` không · `assert len(s2_ev_rows) >= 7`

- [x] **T1.3** (e8m) Khảo sát sâu trục `P2` Bridge, Test Matrix & Bất biến (`tdq_test.py`, `tdq_finish.py`, `tools/run_full_verification.py`, `docs/kien-truc.md`, `integration-blueprint.md`, `tests/test_{state,skill_router,token_budget_lock}.py`) rồi xuất `s3.md` + `s3.ev.jsonl` (`>= 6` chứng cứ) — Test: `py -3 -X utf8 scripts/doc_lint.py docs/tdq/artifacts/2026-11-25-1633-paperclip-3phase-dev-plan/s3.md`
  - Req: `§1, §2#1, §6 Q1-Q2` · Ngoài phạm vi: `GIỮ NGUYÊN` mã nguồn `scripts/`, `tools/`, `tests/`
  - Chạm: `docs/tdq/artifacts/2026-11-25-1633-paperclip-3phase-dev-plan/s3.md`, `docs/tdq/artifacts/2026-11-25-1633-paperclip-3phase-dev-plan/s3.ev.jsonl` (tạo mới)
  - Cần: `Không`
  - Giao tiếp: Consumes: `scripts/{tdq_test,tdq_finish}.py`, `tools/run_full_verification.py`, `docs/kien-truc.md`, `docs/tdq/artifacts/2026-11-25-1439-paperclip-tdq-integration-sim/integration-blueprint.md`, `tests/test_{state,skill_router,token_budget_lock}.py` | Produces: `s3.md` + `s3.ev.jsonl`
  - Neo & Công cụ: `read_file` khoảng dòng cụ thể + `tdq_team.py evidence add --shard s3`
  - Trước → Sau: Mới nắm bất biến tổng quát → Có đủ map từ thay đổi hub tới tập test chạy bởi `tdq_test.py vung-cham`/`tron-bo` và giao diện chuẩn cho `tdq_paperclip_bridge.py` (`P2`)
  - Tiêu chí chấp nhận (EARS): KHI `T1.3` hoàn tất, `s3.ev.jsonl` PHẢI chứa `>= 6` bằng chứng thật về bất biến TDQ, test bán kính và hợp đồng đầu vào cho `P2`
  - Logic cốt lõi: Đọc cơ chế `vung-cham`/`tron-bo`, `run_full_verification.py` và cấu trúc CLI `tdq_state.py init` mà `P2` Bridge sẽ gọi 1 chiều
  - Ca góc hiểm & Assert: Không dẫn nhầm các dòng kiểm tra cũ đã bị xóa · `assert len(s3_ev_rows) >= 6`

**Xong P1 khi**: `3/3` shard `s1`–`s3` lint pass `0` lỗi và thu đủ `>= 21` bằng chứng mã nguồn hợp lệ biên.

---

## P2 — Hợp nhất chứng cứ, bộ Development Plan `P0`–`P2`, `verify_plans.py` & báo cáo

- [x] **T2.1** (e14m) Hợp nhất `evidence.jsonl` + `evidence-log.md`, viết `master-roadmap.md` và `dev-plan-p0.md` (`1` request `feature` thống nhất theo `1c`, `4` wave nội bộ, `tdq_lease.py`, `tdq_state` v6, `tdq_team`, `mcp-policy.json` dưới `scripts/defaults/`, Rust `lock.rs`/`pre_tool_use.rs`, bật cân bằng `3a`, rollback & test `Red -> Green` + parity) — Test: `py -3 -X utf8 scripts/doc_lint.py docs/tdq/artifacts/2026-11-25-1633-paperclip-3phase-dev-plan/master-roadmap.md docs/tdq/artifacts/2026-11-25-1633-paperclip-3phase-dev-plan/dev-plan-p0.md`
  - Req: `§1, §2#2-3, §3c, §5, §6 Q4` · Ngoài phạm vi: Không tách `P0` nhiều PR (`1c`), không nâng `schema_version=7` (`2a`)
  - Chạm: `docs/tdq/artifacts/2026-11-25-1633-paperclip-3phase-dev-plan/evidence.jsonl`, `docs/tdq/artifacts/2026-11-25-1633-paperclip-3phase-dev-plan/evidence-log.md`, `docs/tdq/artifacts/2026-11-25-1633-paperclip-3phase-dev-plan/master-roadmap.md`, `docs/tdq/artifacts/2026-11-25-1633-paperclip-3phase-dev-plan/dev-plan-p0.md` (tạo mới)
  - Cần: `T1.1, T1.2, T1.3`
  - Giao tiếp: Consumes: `s1..s3`, `*.ev.jsonl` | Produces: `evidence.jsonl`, `evidence-log.md`, `master-roadmap.md`, `dev-plan-p0.md`
  - Neo & Công cụ: `tdq_team.py evidence merge`, `tdq_team.py evidence render`, `write_file`
  - Trước → Sau: Mới có ý tưởng cấp cao → Có `master-roadmap.md` kèm đồ thị `P0`–`P2` + `6` mục CẤM copy, và `dev-plan-p0.md` sẵn sàng mở `1` request `feature` hoàn chỉnh với `4` wave tách file nóng + Rust parity
  - Tiêu chí chấp nhận (EARS): KHI `T2.1` xong, `dev-plan-p0.md` PHẢI có đủ chữ ký hàm, JSON schema v6, bảng `4` wave, cờ mặc định `3a`, quy trình rollback và bộ test `Red -> Green` + `test_rust_dispatch_parity.py`
  - Logic cốt lõi: Chạy `evidence merge` trước, dựng `master-roadmap.md` rồi bóc chi tiết từng wave của `P0` theo đúng bằng chứng `s1`–`s3`
  - Ca góc hiểm & Assert: Gắn rõ ràng ràng buộc tuần tự cho hub `tdq_state.py` và đường dẫn sync `tools/build_agy_plugin.py` · `assert evidence_rows >= 21`

- [x] **T2.2** (e12m) Viết `dev-plan-p1.md` (`4` `Domain Pack` dưới `scripts/defaults/domains/` + override `docs/tdq/domains/`, `KhoBM25`, Zero-Downgrade Lock nối `escalate-to-build`, khóa `TRAN_TOKEN <= 3500`, `i18n_check.py`, `--sinh-main`/`--sinh-agy`) và `dev-plan-p2.md` (cầu nối CLI `1` chiều `scripts/tdq_paperclip_bridge.py` tắt mặc định Docker/WSL2, mock unit test stdlib) — Test: `py -3 -X utf8 scripts/doc_lint.py docs/tdq/artifacts/2026-11-25-1633-paperclip-3phase-dev-plan/dev-plan-p1.md docs/tdq/artifacts/2026-11-25-1633-paperclip-3phase-dev-plan/dev-plan-p2.md`
  - Req: `§1, §2#4, §3c, §5, §6 Q4` · Ngoài phạm vi: Không dùng daemon webhook 2 chiều cho `P2` (`4a`)
  - Chạm: `docs/tdq/artifacts/2026-11-25-1633-paperclip-3phase-dev-plan/dev-plan-p1.md`, `docs/tdq/artifacts/2026-11-25-1633-paperclip-3phase-dev-plan/dev-plan-p2.md` (tạo mới)
  - Cần: `T2.1`
  - Giao tiếp: Consumes: `s2.md`, `s3.md`, `master-roadmap.md`, `dev-plan-p0.md` | Produces: `dev-plan-p1.md`, `dev-plan-p2.md`
  - Neo & Công cụ: `write_file` + đối chiếu từng ID trong `evidence.jsonl`
  - Trước → Sau: Chưa có thiết kế chi tiết cho Domain Pack và cầu nối P2 → Có đủ plan từng wave cho `P1` (`scripts/defaults/domains/`, `KhoBM25`, Zero-Downgrade Lock) và `P2` (CLI 1 chiều tắt mặc định)
  - Tiêu chí chấp nhận (EARS): KHI `T2.2` xong, `dev-plan-p1.md` PHẢI chứng minh đủ lộ trình bảo toàn `TRAN_TOKEN <= 3500` và đóng gói `--sinh-main`; `dev-plan-p2.md` PHẢI giữ `state.json` làm chân lý duy nhất
  - Logic cốt lõi: Thiết kế chi tiết `P1` bám sát phụ thuộc với `P0` và tách gọn `P2` thành add-on độc lập kèm danh sách test stdlib mock
  - Ca góc hiểm & Assert: Chỉ rõ cơ chế override an toàn giữa `scripts/defaults/domains/` và `docs/tdq/domains/` · `assert "webhook_daemon" not in p2_chosen`

- [x] **T2.3** (e10m) Xây dựng và chạy `verify_plans.py` (stdlib Python, mặc định bật timestamp log stderr, hỗ trợ `TDQ_LOG=0` ra `0B` stderr) xuất `verify-results.json` kiểm chứng tự động mọi đường dẫn/symbol trên đĩa, cú pháp khối JSON hợp đồng, không vi phạm `scripts/` ↔ `hooks/`, không trùng file nóng trong cùng wave và đối chiếu `evidence.jsonl` — Test: `py -3 -X utf8 docs/tdq/artifacts/2026-11-25-1633-paperclip-3phase-dev-plan/verify_plans.py --out docs/tdq/artifacts/2026-11-25-1633-paperclip-3phase-dev-plan/verify-results.json`
  - Req: `§2#5, §3c, §4, §6 Q1, Q3` · Ngoài phạm vi: Script chỉ chạy read-only trên repo gốc và chỉ xuất kết quả vào thư mục artifact của request
  - Chạm: `docs/tdq/artifacts/2026-11-25-1633-paperclip-3phase-dev-plan/verify_plans.py`, `docs/tdq/artifacts/2026-11-25-1633-paperclip-3phase-dev-plan/verify-results.json` (tạo mới)
  - Cần: `T2.1, T2.2`
  - Giao tiếp: Consumes: `evidence.jsonl`, `master-roadmap.md`, `dev-plan-p{0,1,2}.md`, file nguồn repo thật | Produces: `verify_plans.py`, `verify-results.json`
  - Neo & Công cụ: `write_file` + chạy `TDQ_LOG=1` và `TDQ_LOG=0` + `read_file` kết quả JSON
  - Trước → Sau: Chưa có máy kiểm chéo độ khớp plan với repo thật → Có bộ kiểm tự động chạy 1 lệnh xác nhận `100%` symbol/đường dẫn/JSON/wave/evidence đều đúng
  - Tiêu chí chấp nhận (EARS): KHI chạy `verify_plans.py`, script PHẢI kiểm thật tất cả mục (không assert rỗng), exit `0`, và phát `0B` stderr khi `TDQ_LOG=0`
  - Logic cốt lõi: Phân tích cấu trúc JSON fences trong 4 file plan, kiểm regex trích symbol/path đối chiếu file thật trên đĩa, kiểm wave non-overlap và kiểm bounds `evidence.jsonl`
  - Ca góc hiểm & Assert: Test cả nhánh FAIL (tự kiểm `verify_plans.py` phát hiện lỗi giả định trong memory/tmp) để tránh `ANTI-2` · `assert failed_checks == 0 and ev_line_errs == 0`

- [x] **T2.4** (e8m) Soạn báo cáo `2` tầng `docs/tdq/reports/2026-11-25-1633-paperclip-3phase-dev-plan.md` (kèm `## Thời gian` từ `tdq_timing.py show` và `## Thân PR`) và file nguồn `bao-cao.archify.md` — Test: `py -3 -X utf8 scripts/doc_lint.py docs/tdq/reports/2026-11-25-1633-paperclip-3phase-dev-plan.md`
  - Req: `§2#6, §6 Q5` · Ngoài phạm vi: `GIỮ NGUYÊN` toàn bộ file ngoài `docs/tdq/`
  - Chạm: `docs/tdq/reports/2026-11-25-1633-paperclip-3phase-dev-plan.md`, `docs/tdq/artifacts/2026-11-25-1633-paperclip-3phase-dev-plan/bao-cao.archify.md` (tạo mới)
  - Cần: `T2.3`
  - Giao tiếp: Consumes: `master-roadmap.md`, `dev-plan-p{0,1,2}.md`, `verify-results.json`, `evidence.jsonl` | Produces: `report.md`, `bao-cao.archify.md`
  - Neo & Công cụ: `write_file` + `tdq_timing.py show` + `doc_lint.py`
  - Trước → Sau: Kết quả nằm rải rác ở 4 file plan → Có báo cáo 2 tầng súc tích dễ hiểu (`Trước -> Sau -> Kết quả -> Đã test -> Kết quả test`) và nguồn Archify chuẩn showcase
  - Tiêu chí chấp nhận (EARS): KHI `T2.4` hoàn tất, `report.md` PHẢI đạt `0` lỗi `doc_lint.py` (kể cả `R16`), `0` placeholder và dẫn đủ `100%` số liệu thật từ `verify-results.json`
  - Logic cốt lõi: Tổng hợp `4` quyết định kiến trúc + bảng lộ trình `P0`–`P2` + số liệu `verify_plans.py`, chèn bảng `tdq_timing.py show`
  - Ca góc hiểm & Assert: Giữ câu trong `bao-cao.archify.md` ngắn gọn (`<= 28` reading units) để Archify render đạt `0` diagnostics · `assert doc_lint_rc == 0`

**Xong P2 khi**: `master-roadmap.md`, `dev-plan-p0/p1/p2.md`, `verify_plans.py`, `report.md` hoàn chỉnh, `verify_plans.py` pass `100%` và `doc_lint.py` exit `0`.

---

## P3 — Log & kiểm chứng bắt buộc mức `ultra` (`Q1`–`Q6`)

Log: BỎ cho mã nguồn sản phẩm (`work_kind=investigate`, `0` file code sản phẩm sửa); riêng script `verify_plans.py` bật timestamp log mặc định và hỗ trợ `TDQ_LOG=0`.

- [x] **T3.1** (e12m) Chạy trọn bộ kiểm chứng mức `ultra` (`Q1`–`Q6`): kiểm grounding `QC-I1..I4`, đối chiếu nguyên văn `L2` (`>= 10` điểm neo), tái chạy `verify_plans.py` (`TDQ_LOG=1/0`), gọi `tdq-qc-tester` độc lập soi chéo, xuất `docs/tdq/qc/2026-11-25-1633-paperclip-3phase-dev-plan.md`, dựng Archify HTML `current` (`0` diagnostics) và xác nhận Tailscale HTTP `200` — Test: `py -3 -X utf8 scripts/tdq_archify.py verify --document docs/tdq/reports/2026-11-25-1633-paperclip-3phase-dev-plan.md --manifest docs/tdq/reports/2026-11-25-1633-paperclip-3phase-dev-plan.manifest.json`
  - Req: `§2#6, §6 Q1-Q6` · Ngoài phạm vi: `GIỮ NGUYÊN` mọi file ngoài `docs/tdq/`
  - Chạm: `docs/tdq/reports/2026-11-25-1633-paperclip-3phase-dev-plan.html`, `docs/tdq/qc/2026-11-25-1633-paperclip-3phase-dev-plan.md` (tạo mới)
  - Cần: `T2.4`
  - Giao tiếp: Consumes: `verify_plans.py`, `verify-results.json`, `evidence.jsonl`, `master-roadmap.md`, `dev-plan-p{0,1,2}.md`, `bao-cao.archify.md`, `report.md` | Produces: HTML + manifest + biên bản `qc.md`
  - Neo & Công cụ: `verify_plans.py`, `tdq-qc-tester` (độc lập), `doc_lint.py`, `tdq_archify.py render/verify`, Tailscale HTTP probe
  - Trước → Sau: Mới có bản thảo tự kiểm → Có xác nhận độc lập từ `tdq-qc-tester` (`Verdict: PASS`), `6/6` cổng `Q1`–`Q6` xanh, Archify HTML `current` và HTTP `200`
  - Tiêu chí chấp nhận (EARS): KHI hoàn tất `T3.1`, `6/6` mục `Q1`–`Q6` PHẢI PASS trong `qc.md`, `tdq_archify.py verify` trả `"status": "current"` (`0` diagnostics) và Tailscale trả HTTP `200`
  - Logic cốt lõi: Xác minh `L1/L4/L2`, render Archify HTML sau sửa cuối cùng của `report.md`, giao `tdq-qc-tester` kiểm độc lập mọi claim & script rồi chốt biên bản QC
  - Ca góc hiểm & Assert: Bắt buộc render lại Archify HTML nếu chỉnh dù 1 dòng trong `report.md` để manifest không bao giờ `stale` · `assert verify['status'] == 'current' and http == 200`

**Xong P3 khi**: `6/6` hạng mục `Q1`–`Q6` đạt `PASS`, `tdq-qc-tester` ký xác nhận độc lập và Archify HTML trả `current` + HTTP `200`.

## QC vòng 1 — fix

Bám phản hồi kiểm thử độc lập `tdq-qc-tester` (`a83215c4-b83a-4e29-9f11-a2beffb97355`, Verdict: FAIL ở `Q4`):

1. **Defect 1 (High — Intra-wave deps):** Tách mọi task phụ thuộc nhau ra khác wave trong `dev-plan-p0.md` (`P0-W1..W4`), `dev-plan-p1.md` (`P1-W1..W4`), `dev-plan-p2.md` (`P2-W1..W3`), cập nhật `master-roadmap.md`, và nâng cấp `verify_plans.py` kiểm tra chặn phụ thuộc cùng/sau wave kèm ca phủ định tự kiểm.
2. **Defect 2 (Med — Hook matcher & packaging blind spots):** Bổ sung `hooks/hooks.json:76` và `tools/patches/agy_manifests.py:72` vào `P0-W3` để mở matcher non-LSP MCP, ghi nhận `tools/patches/common_utils.py:26` loại trừ `agy_pretooluse_gate.py` nên gắn rào `P0` trực tiếp vào `edit_gate.py`, `bash_gate.py`, `lsp_gate.py`.
3. **Defect 3 (Low — Exact signature & evidence excerpt):** Chuẩn hóa `mcp_policy.evaluate_tool_call()` xuyên suốt `dev-plan-p0.md` và cập nhật excerpt dòng `6f8f80aeae90` (`scripts/tdq_config.py:30-94`) trong `s1.ev.jsonl` + tái hợp nhất `evidence.jsonl`.

## QC vòng 2 — fix

Bám phản hồi `tdq-qc-tester` vòng 2 (`ce108928-f775-4f82-8e12-948e4b927303`, Q1–Q4 PASS, `2` Low ở Q5):

1. **Defect 1 (Low — PR body ở `report.md:81`):** Cập nhật số liệu trong `## Thân PR` khớp với `verify-results.json` (`90` disk symbols, `11` disjoint waves, `24` tasks, `32` dependency edges).
2. **Defect 2 (Low — Đường dẫn cấu hình dự án `docs/tdq/config.json` vs `tdq-config.json`):** Phân biệt rõ override dự án nằm tại `docs/tdq/config.json` (ghi đè lên `tdq-config.json` của plugin theo `tdq_config.py:177-189`) trong `dev-plan-p0.md`, `dev-plan-p1.md`, `master-roadmap.md` và `s1.md`.

## Cụm song song

- **Đợt 1 (chạy song song 3 luồng đọc-chỉ, `Worktree: none`, `Chạm:` tách rời):**
  - `T1.1` → `s1.md`, `s1.ev.jsonl`
  - `T1.2` → `s2.md`, `s2.ev.jsonl`
  - `T1.3` → `s3.md`, `s3.ev.jsonl`
- **Đợt 2 (tuần tự trên Leader + subagent QC độc lập ở cuối):** `T2.1` → `T2.2` → `T2.3` → `T2.4` → `T3.1` (kèm `tdq-qc-tester`).

## Luật file nóng (một file, nhiều task chạm)

Không có file nóng trong request lập plan này: cả `8` task `T1.1`–`T3.1` sở hữu đường dẫn `Chạm:` hoàn toàn tách rời, không xung đột ghi. Riêng trong bộ Development Plan đầu ra (`dev-plan-p0.md` và `dev-plan-p1.md`), `scripts/tdq_state.py`, `scripts/build_portable.py` và `tools/build_agy_plugin.py` được khai báo là file nóng của các wave thi công về sau và bắt buộc khóa tuần tự hoặc một chủ ghi duy nhất.

## Definition of Done

Trỏ về §6 của spec `2026-11-25-1633-paperclip-3phase-dev-plan.md` (`muc_qc=ultra`):

- [x] Q1 `QC-I1` Grounding & không placeholder — `py -3 -X utf8 docs/tdq/artifacts/2026-11-25-1633-paperclip-3phase-dev-plan/verify_plans.py --out docs/tdq/artifacts/2026-11-25-1633-paperclip-3phase-dev-plan/verify-results.json`
- [x] Q2 `QC-I2` Đối chiếu nguyên văn `L2` (`>= 10` điểm neo mã nguồn cốt lõi khớp đĩa) — đối chiếu trực tiếp bằng `read_file` và ghi bảng đối khớp trong `docs/tdq/qc/2026-11-25-1633-paperclip-3phase-dev-plan.md`
- [x] Q3 Script kiểm chứng `verify_plans.py` (`TDQ_LOG=1/0`, JSON schema, wave, import law) — chạy kiểm hai biến môi trường `TDQ_LOG=1` và `TDQ_LOG=0` (đòi hỏi `0B` stderr khi `TDQ_LOG=0`, exit `0`)
- [x] Q4 Đủ quyết định `1abcd 2a 3a 4a 5a`, `1c 2a 3a 4a 5c`, `H1`–`H4` & `6` mục CẤM copy — kiểm tra đối khớp toàn bộ trong `master-roadmap.md` và `dev-plan-p0/p1/p2.md`
- [x] Q5 `doc_lint.py` exit `0`, ranh giới `0` code diff, Archify HTML `current` & Tailscale HTTP `200` — `py -3 -X utf8 scripts/tdq_archify.py verify --document docs/tdq/reports/2026-11-25-1633-paperclip-3phase-dev-plan.md --manifest docs/tdq/reports/2026-11-25-1633-paperclip-3phase-dev-plan.manifest.json`
- [x] Q6 QC độc lập `tdq-qc-tester` (`muc_qc=ultra`) — subagent `tdq-qc-tester` đọc chéo mã nguồn, tái chạy `verify_plans.py` và chấm `Verdict: PASS`, `DEFECTS: None`
