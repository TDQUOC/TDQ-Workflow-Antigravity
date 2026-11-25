# QC — Khả thi, Simulate Test và Đề xuất Tích hợp Paperclip vào TDQ-Workflow

Ngày: 2026-11-25 · Plan: ../plan/2026-11-25-1439-paperclip-tdq-integration-sim.md (Vòng 2 — PASS sau fix QC1.1–QC1.2)
Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

> **Tóm tắt dễ hiểu:** Vòng kiểm thử đầu tiên phát hiện nhánh nhường lượt cho công việc cũ chưa được kích hoạt thật và hai bằng chứng còn gộp chung nguồn. Sau khi sửa script mô phỏng, tách đủ bằng chứng và dựng lại giao diện HTML, cả nhóm tự kiểm lẫn chuyên viên QC độc lập đều chấm đạt toàn bộ 6 trên 6 hạng mục với 0 lỗi tồn đọng.

## Dev Behavior QC Card

- Auto Meta-Gate: PASS (`6/6` checks vòng 2, `0` lỗi)
- Luồng đổi: Nghiên cứu đối chiếu mã nguồn hai repo, xây dựng bộ mô phỏng cô lập `SIM-1..SIM-6`, sổ bằng chứng `27` dòng và bản thiết kế `3` pha trong `docs/tdq/` (`0` chỉnh sửa mã nguồn sản phẩm)
- Chạy thử thật (Before → After + Bằng chứng tươi): Vòng 1 `FAIL` với `3` khiếm khuyết (`SIM-2` nhánh `step_idx % 4 == 0` không kích hoạt, `a22d6a034353` gộp `PLUGIN_SPEC.md`, Archify `stale`) → Khắc phục `QC1.1`–`QC1.2` → Vòng 2 chạy lại `run_simulations.py` (`TDQ_LOG=1` ra logs + exit `0`; `TDQ_LOG=0` ra `0B` stderr + exit `0`), `27/27` bằng chứng hợp lệ biên, `tdq-qc-tester` độc lập trả `Verdict: PASS` (`DEFECTS: None`), `doc_lint.py` exit `0`, `tdq_archify.py verify` trả `"status": "current"` (`0` diagnostics) và Tailscale HTTP `200`
- Rủi ro còn lại: Chưa dựng live Paperclip server (PostgreSQL + `pnpm`) nên đánh giá `Hybrid Bridge` ở `P2` dựa trên kiểm chứng tĩnh mã nguồn (`Verified`)

| # | Hạng mục | Lệnh đã chạy | Kết quả | PASS/FAIL |
|---|---|---|---|---|
| Q1 | `QC-I1` Grounding `27/27` chứng cứ & `0` placeholder | Python check `evidence.jsonl` + corpus `s1..s4`, `integration-blueprint.md`, `report.md` | `27/27` dòng hợp lệ biên (`line_errs=0`), `27/27` ID được trích dẫn, `0` placeholder | PASS |
| Q2 | `QC-I2` Đối chiếu nguyên văn `L2` (`a22d6a034353`, `642dbc026abe`, `320ec188d2a9`) | `read_file` trực tiếp `package.json:109-128`, `PLUGIN_SPEC.md:15-35`, `SKILL.md:10-31` | `100%` khớp nguyên văn, không trộn nguồn đa tệp | PASS |
| Q3 | Thực thi tái lập `SIM-1..SIM-6` (`TDQ_LOG=1/0`) | `py -3 -X utf8 .../sim/run_simulations.py` cả bản gốc lẫn sandbox `$env:TEMP` của QC | `TDQ_LOG=1` exit `0` + log đủ; `TDQ_LOG=0` exit `0` + `0B` stderr; `6/6` kịch bản PASS | PASS |
| Q4 | Kiểm nhánh `SIM-2..5` & khớp `H1`–`H4`, `2a+c`, `5b` | Đối chiếu `sim-results.json`, `sim-summary.md`, `s4.md`, `integration-blueprint.md`, `report.md` | `SIM-2` `aging_share_hits=1` (`20 -> 4`), chặn `1` chạy sớm, `3 -> 1` wake; `SIM-4` `12/12` bất biến; `SIM-5` `8/8` BM25 + `5/5` disk gates | PASS |
| Q5 | `doc_lint.py`, ranh giới git & Archify HTML + Tailscale | `doc_lint.py`; `tdq_archify.py verify`; HTTP HEAD Tailscale; `git status` hai repo | `doc_lint` `0` lỗi; `status=current` (`0` diagnostics); HTTP `200`; `0` file code ngoài `docs/` bị chạm | PASS |
| Q6 | QC độc lập vòng 2 (`tdq-qc-tester`, `e22042a3`) | Subagent `tdq-qc-tester` đọc chéo mã mô phỏng, chạy sandbox `$env:TEMP` và soi L2/bounds | `Verdict: PASS`, `DEFECTS: None` ở cả `6/6` hạng mục `Q1`–`Q6` | PASS |

## Bằng chứng

### Vòng 1 FAIL và quá trình sửa (`QC1.1`–`QC1.2`)

- **Vòng 1 (`tdq-qc-tester` `d54a944e`):** `Verdict: FAIL` do: (1) `P_AGED` ở `SIM-2` mang `tier="person"` nên vượt trước khi `step_idx % 4 == 0` chạy + các baseline ở `SIM-2`/`SIM-4`/`SIM-5` còn gán tĩnh; (2) `a22d6a034353` gộp `package.json` và `PLUGIN_SPEC`; (3) Archify HTML bị `stale` sau khi cập nhật `## Thời gian`.
- **Khắc phục:** Sửa `QC1.1` (`run_simulations.py`: đặt `W_AGED` ở `tier="work"` để nhánh `step_idx % 4 == 0` kích hoạt thật ở lượt `4` với `aging_share_hits=1`, viết hàm đối chứng thực thi thật `dispatch_baseline`, `execute_baseline`, `eval_mcp_baseline`, `route_binary_baseline` và kiểm `5/5` cổng `code-build` trực tiếp từ file trên đĩa) và `QC1.2` (tách `a22d6a034353` chỉ còn `package.json:109-128`, bổ sung `642dbc026abe` cho `PLUGIN_SPEC.md:15-35` và `320ec188d2a9` cho `SKILL.md:10-31`, hợp nhất đủ `27/27` dòng và dựng lại Archify HTML).

### Vòng 2 `SIM-1..SIM-6` (bản đã commit trong `sim-results.json`)

```text
TDQ_LOG=1 rc=0 (8 log lines to stderr); TDQ_LOG=0 rc=0 stderr_lines=0
SIM-1: duplicate_race_claims 61 -> 0 active, 12/12 tasks_completed, 2/2 recovered (avg 0.328 ms)
SIM-2: aged_task_dispatch_slot 20 -> 4 (aging_share_hits=1), premature 1 -> 0, wakes 3 -> 1
SIM-3: burst tripped_at_run=12, refusal_streak=5, final_spend_usd=4.8 (overshoot +2.2 -> 0.0)
SIM-4: tdq_invariants_intact=12/12 (0 regressions), quarantined=2/2 (0.0009 ms)
SIM-5: domain_packs=4, bm25_routing=8/8, disk_code_gates_verified=5, non_code_mismatches 4 -> 0
SIM-6: 200-iter Pattern-Native p50=0.367 ms, p95=0.428 ms, mean=0.374 ms, 0 new deps
EV_CHECK: rows=27 line_errs=0 | CITE_CHECK: total=27 cited=27 missing=[] placeholders=[]
DOC_LINT_RC=0 | archify verify: status=current, diagnostics=0 | TAILSCALE_HTTP=200
```

### Kết quả `tdq-qc-tester` vòng 2 (`e22042a3-bce6-4ece-be05-e374af94e7d3`)

```text
Verdict: PASS | Q1-Q6 PASS | DEFECTS: None
Q1: 27/27 rows valid, 0 OOB, 0 missing; 27/27 IDs cited; 0 placeholders -> PASS
Q2: a22d6a034353=package.json:109-128 only; PLUGIN_SPEC:15-35 & SKILL:10-31 match verbatim -> PASS
Q3: py -3 run_simulations.py -> $env:TEMP (TDQ_LOG=1 exit 0, 876B stderr; TDQ_LOG=0 exit 0, 0B stderr, 6/6 PASS) -> PASS
Q4: SIM-2 aging_share_hits=1 slot 20->4, premature 1->0, wakes 3->1; match=True -> PASS
Q5: doc_lint 0 violations; tdq_archify verify status=current; paperclip=0 dirty, TDQ code diff=0 -> PASS
Q6: execute_baseline, eval_mcp_baseline, route_binary_baseline + 12/12 inv + 5/5 disk gates real -> PASS
```

## Lệch spec chờ duyệt

không có

## Kết luận

PASS toàn bộ (`6/6` hạng mục `Q1`–`Q6` đạt `PASS` ở QC vòng 2, `tdq-qc-tester` xác nhận `Verdict: PASS`, `DEFECTS: None`). Sẵn sàng chuyển pha `report` và xin ý kiến người dùng về commit và merge nhánh `docs/paperclip-tdq-integration-sim`.
