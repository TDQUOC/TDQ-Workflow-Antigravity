# BÁO CÁO — Khả thi, Simulate Test và Đề xuất Tích hợp Paperclip vào `TDQ-Workflow`

Ngày: 2026-11-25 · Mã yêu cầu: 2026-11-25-1439-paperclip-tdq-integration-sim · Mức QC: ultra
Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

> **Tóm tắt dễ hiểu:** Trước khi kiểm chứng, chưa có số liệu thật cho thấy cơ chế Paperclip giúp TDQ Workflow ổn định hơn hay không. Chúng tôi đã đối chiếu 27 bằng chứng từ hai mã nguồn và chạy sáu kịch bản mô phỏng trong sandbox Python cô lập. Kết quả chứng minh mô hình giữ nguyên lõi TDQ và mượn chọn lọc cơ chế Paperclip đạt độ trễ p95 chỉ 0.428 mili-giây. Bạn nên tích hợp theo lộ trình ba pha và tuyệt đối tránh mang cơ sở dữ liệu nặng về máy.

## Tầng 1 — Câu trả lời Trực diện & Khuyến nghị Cho Bạn

**Trước request (trạng thái/flow):** Đã hiểu Paperclip và `TDQ-Workflow` ở mức riêng lẻ, nhưng chưa kiểm chứng bằng mã nguồn và `simulate test` xem có ghép được cơ chế điều hành `phase`/`task` và mở rộng đa lĩnh vực vào TDQ mà không làm giảm chất lượng gốc (`5b`) hay không.
**Sau request (trạng thái/flow):** Đã đối chiếu `27` bằng chứng mã nguồn hai repo (`evidence.jsonl`), lập và chạy `6/6` kịch bản mô phỏng Python stdlib (`SIM-1..SIM-6`) và hoàn thiện bản thiết kế tối ưu `3` pha:

- **1. Có tích hợp để điều hành `phase`/`task` ổn hơn không? — CÓ (`P0`, `SIM-1..SIM-3`):** Không cần PostgreSQL. Bổ sung khóa `os.O_EXCL` + Lease TTL, xếp hàng 3 tầng có aging (`OLDEST_DISPATCH_SHARE = 4`) + `blockedBy`, cầu dao 3 pha (`closed/open/half_open`) và ngưỡng chi phí `hard_stop` bằng Python thuần đủ diệt race claim (`61 -> 0`), cứu `2/2` worker chết, đưa task cũ từ lượt `20` lên `4` và chặn lố ngân sách về `$0.00`.
- **2. Có xử lý tốt nhiều lĩnh vực hơn mà không đổi chất lượng TDQ không? — CÓ (`P1`, `SIM-4..SIM-5`):** Kế thừa cách tách `INVESTIGATE_PHASE_ROWS` khỏi `PHASE_TABLE` của TDQ, bộ khung `Domain Pack` (`code-build`, `research-rca`, `pm-ba-content`, `ops-checklist`) kết hợp `KhoBM25` định tuyến đúng `8/8` prompt. Nhánh `code-build` giữ nguyên `100%` (`12/12` bất biến và `5/5` cổng kiểm trên đĩa, `0` hồi quy).
- **3. Chọn hướng nào tối ưu cho Windows + Antigravity (`2a+c`, `SIM-6`)?** Chọn **`Pattern-Native` làm lõi (`P0`–`P1`)** và chỉ giữ **`Hybrid Bridge` (Docker/WSL2) làm add-on tắt mặc định (`P2`)**. Đo `200` vòng trên Windows cho `p50 = 0.367 ms`, `p95 = 0.428 ms`, thêm `0` thư viện ngoài — trong khi Bridge kéo theo Node `>= 24.11`, PostgreSQL và `11` bản vá `pnpm` (`a22d6a034353`), đồng thời Antigravity bên Paperclip đang khóa `darwin-arm64` (`342b3fd669d4`).
- **4. Tuyệt đối không sao chép gì từ Paperclip?** Không đem PostgreSQL nhúng (`a22d6a034353`), không chạy Plugin UI `same-origin JS` (`642dbc026abe`), không bật `local_trusted` trên Windows (`e79c1da5f2ab`), không chạy cron heartbeat rỗng (`320ec188d2a9`) và không gỡ bỏ AST TCAS hay `Verify-by-Effect` SHA-256 của TDQ (`8592d1befc8d`, `d76883f3ba1a`).

**Đã test gì:** Chạy bộ `run_simulations.py` (`TDQ_LOG=1` và `TDQ_LOG=0`) qua `6/6` kịch bản cô lập, kiểm biên `27` dòng `evidence.jsonl`, kiểm chứng mức `ultra` vòng 2 (`Q1`–`Q6`) gồm `tdq-qc-tester` độc lập (`e22042a3`), `doc_lint.py`, `tdq_archify.py verify` và Tailscale HTTP probe.
**Kết quả test:** Đạt `6/6` hạng mục `Q1`–`Q6` (`tdq-qc-tester` vòng 2 xác nhận `Verdict: PASS`, `DEFECTS: None`): `SIM-1..SIM-6` `6/6` PASS (`0` claim trùng, `2/2` crash hồi phục, slot cũ `20 -> 4` với `aging_share_hits=1`, ngân sách lố `+$2.20 -> $0.00`, `12/12` bất biến TDQ giữ nguyên, cách ly `2/2` tool MCP mới, `8/8` BM25 với `5/5` cổng code trên đĩa, `p95 = 0.428 ms`, `TDQ_LOG=0` ra `0B` stderr), `27/27` bằng chứng hợp lệ (`line_errs=0`), `doc_lint.py` `0` lỗi, Archify HTML `current` (`0` diagnostics) và Tailscale HTTP `200`.
**Đầu ra:** Báo cáo này, biên bản `docs/tdq/qc/2026-11-25-1439-paperclip-tdq-integration-sim.md`, phụ lục thiết kế `integration-blueprint.md`, bộ script `sim/run_simulations.py` + `sim-results.json` + `sim-summary.md`, `4` shard `s1`–`s4` và sổ `evidence.jsonl` (`27` dòng). · **Archify HTML:** `docs/tdq/reports/2026-11-25-1439-paperclip-tdq-integration-sim.html` (`current`, HTTP `200`)
**Giới hạn:** Chỉ kiểm chứng tĩnh mã nguồn hai repo và chạy mô phỏng Python cô lập trong sandbox (chưa chạy live Paperclip server nên đánh giá `Hybrid Bridge` dựa trên mã nguồn `Verified`). Request mở qua cổng `--bo-qua-lsp` (`ly_do`: `"Nghien cuu kha thi tich hop co che Paperclip vao TDQ-Workflow kem simulate test co lap trong docs/tdq/artifacts, khong sua code san pham"`; `module`: `javascript:. -> HET_HAN`, `python:. -> HET_HAN`, `rust:hooks/rust/tdq-dispatch -> HET_HAN`).
**Lệch spec chờ duyệt:** không có
**Git:** chưa commit (đang trên nhánh `docs/paperclip-tdq-integration-sim`, `0` thay đổi mã nguồn sản phẩm ở cả hai repository)

---

## Tầng 2 — Hồ sơ Kiểm chứng Kỹ thuật & Số liệu Thực nghiệm

### 1. Kết luận 4 giả thuyết (`H1`–`H4`)

| Giả thuyết | Kết luận | Độ tin cậy | Bằng chứng gốc & Điểm giới hạn / Phản chứng |
|---|---|---|---|
| **H1 (Ổn định điều hành `phase`/`task` không cần PG)** | **Xác nhận có điều kiện** | `Verified` | `tdq_state.py save()` hiện ghi đè `"overwriting anyway"` (`596107efb02e`); `issues.ts` (`b55f0ac994d7`), 4-tier aging (`44fcdddd506d`), `automaticRunBrakes` (`8daca69ba8c6`) chuyển thể được sang stdlib Python (`SIM-1..SIM-3` PASS: `9fdc25e30293`). **Giới hạn:** Không thay `tdq_team` TCAS AST (`8592d1befc8d`) hay `Verify-by-Effect` (`d76883f3ba1a`). |
| **H2 (Đa lĩnh vực `Domain Pack` giữ đủ `5b`)** | **Xác nhận** | `Verified` | Dựa trên tách lớp `INVESTIGATE_PHASE_ROWS` (`25e4451bc94f`), `KhoBM25` (`b5890600c7f6`), role tách quyền (`3ee5c0f3f917`, `e81989a5e51c`), `trust_level` catalog (`0377c980f231`). `SIM-4..SIM-5` chứng minh `12/12` bất biến TDQ không suy giảm, `5/5` cổng code kiểm trên đĩa và `8/8` định tuyến đúng (`981a164cf0ca`). |
| **H3 (`Pattern-Native` vs `Hybrid Bridge` Windows)** | **Xác nhận** | `Verified` | `SIM-6` đo `Pattern-Native` `p50=0.367 ms`, `p95=0.428 ms`, `0` dep mới (`981a164cf0ca`); `Hybrid Bridge` đòi `Node >= 24.11` + `11` patch `pnpm` (`a22d6a034353`), Plugin UI `same-origin JS` (`642dbc026abe`), mất chặn loopback `local_trusted` Windows (`e79c1da5f2ab`) và khóa `Antigravity` trên `darwin-arm64` (`342b3fd669d4`). |
| **H4 (Đề xuất tối ưu & Danh mục CẤM copy)** | **Xác nhận** | `Verified` | Lọc qua `4` tiêu chí + add-on (`2a+c`): gom `5` cơ chế vào `P0`, `Domain Pack` + `KhoBM25` vào `P1`, `Bridge` vào `P2` tắt mặc định, và khóa `6` hạng mục `CẤM` sao chép trong `s4.md` và `integration-blueprint.md` (gồm UI `642dbc026abe` và heartbeat rỗng `320ec188d2a9`). |

### 2. Tổng hợp số đo thực nghiệm `SIM-1..SIM-6` (`9fdc25e30293`, `981a164cf0ca`)

| Kịch bản | Baseline (Hiện trạng TDQ) | Proposed (Paperclip Pattern) | Độ tin cậy |
|---|---|---|---|
| **SIM-1 (8 worker, 2 crash)** | `61` claim trùng · `2` task kẹt chết | `0` claim trùng · `2/2` crash hồi phục (`0.328 ms`) | `Verified` (chạy thật) |
| **SIM-2 (20 task DAG + blockedBy)** | Task cũ đợi lượt `20` · `1` chạy sớm · `3` wake trùng | Task cũ lên lượt `4` (`aging_share_hits=1`) · `1` wake · `0` chạy sớm | `Verified` (chạy thật) |
| **SIM-3 (Burst lỗi + Budget $5)** | Đốt `21` lượt lỗi · lố trần `+$2.20` | Ngắt lượt `12`, streak `5` · dừng ở `$4.80` (`+$0.00`) | `Verified` (chạy thật) |
| **SIM-4 (12 bất biến + MCP mới)** | `12/12` bất biến · `0/2` tool lạ bị chặn | `12/12` bất biến (`0` hồi quy) · cách ly `2/2` (`0.0009 ms`) | `Verified` (đĩa + mô phỏng) |
| **SIM-5 (4 Domain Packs + BM25)** | `2` kind nhị phân · `4/4` phi-code lệch | `4` gói · `8/8` khớp prompt · `code-build` giữ `5/5` cổng đĩa | `Verified` (đĩa + chạy thật) |
| **SIM-6 (200 vòng trên Windows)** | Chưa có lớp đo chuỗi lock+budget+policy | `p50=0.367 ms`, `p95=0.428 ms`, `0` dep vs PG + `11` patch | `Verified` (bench thật) |

### 3. Hồ sơ tham chiếu chi tiết

- Phụ lục thiết kế tối ưu `P0`–`P2` & hợp đồng mẫu: `docs/tdq/artifacts/2026-11-25-1439-paperclip-tdq-integration-sim/integration-blueprint.md`
- Mã kiểm thử & kết quả thô: `docs/tdq/artifacts/2026-11-25-1439-paperclip-tdq-integration-sim/sim/run_simulations.py`, `sim-results.json`, `sim-summary.md`
- `4` shard đối chiếu & sổ bằng chứng: `s1.md`, `s2.md`, `s3.md`, `s4.md`, `evidence.jsonl`, `evidence-log.md`

## Thời gian

```text
Request `2026-11-25-1439-paperclip-tdq-integration-sim` · lane full · opened at 2026-11-25T14:44:40+07:00

| Phase | Wall clock | Times entered |
|---|---|---|
| idle | 1s | 1 |
| analyze | 50 min | 1 |
| spec | 4 min | 1 |
| plan | 3 min | 1 |
| mode | 4 min | 1 |
| implement | 9 min | 1 |
| qc | 17 min | 1 |
| Total | 1h 27min |  |

Model compute time is unavailable (`model_giay=null`). API includes network/provider latency; tool time is host wait. Observed metrics may overlap; unattributed time is not assumed user/model time.
Transcript attribution: project_window. Complete covers selected supported observations only.
Host metrics unavailable (5 hidden: api_request_seconds, tool_call_seconds, background_job_seconds, observed_union_seconds, unattributed_seconds): no_usable_source, no_usable_observations, wall_minus_observed_union;no_usable_observations

## Agent Role Telemetry

| Role | Runs | First pass | Rate | Retries | Avg elapsed | Models |
|---|---|---|---|---|---|---|
| self | 7 | 7 | 100% | 0 | — | — |
| tdq-qc-tester | 6 | 6 | 100% | 0 | — | — |
| tdq-implementer | 2 | 2 | 100% | 0 | — | — |
```

## Thân PR (soạn sẵn)

**Tóm tắt:** Nghiên cứu khả thi, chạy `6` kịch bản mô phỏng Python cô lập (`SIM-1..SIM-6`) và xuất bản thiết kế tích hợp `3` pha (`P0`–`P2`) đưa các cơ chế điều hành cốt lõi của Paperclip vào `TDQ-Workflow` mà giữ nguyên `100%` hành vi chất lượng gốc.
**Trước/Sau:** https://unity-pc-rtx3060.tail99896.ts.net/vlog/tdq-workflow-agy/reports/2026-11-25-1439-paperclip-tdq-integration-sim.html
**Đã kiểm:**
- `py -3 -X utf8 docs/tdq/artifacts/2026-11-25-1439-paperclip-tdq-integration-sim/sim/run_simulations.py` (`6/6` PASS, `TDQ_LOG=1/0` đạt chuẩn).
- `py -3 -X utf8 scripts/doc_lint.py`, kiểm chứng mức `ultra` vòng 2 (`Q1`–`Q6` đạt `6/6` PASS, `tdq-qc-tester` xác nhận `Verdict: PASS`), Archify HTML `current` + Tailscale HTTP `200`.
**Rủi ro hồi quy:** không có — chỉ tạo tài liệu và script mô phỏng cô lập trong `docs/tdq/`, `0` thay đổi mã nguồn ở cả hai repository.
<!-- tdq-archify-binding:start -->
<!-- manifest: 2026-11-25-1439-paperclip-tdq-integration-sim.manifest.json -->
<!-- manifest_digest: d43096d69a098238b2b6c44e183cd25f2bc44ec4d3ff2d83804a72319dff5550 -->
<!-- tdq-archify-binding:end -->