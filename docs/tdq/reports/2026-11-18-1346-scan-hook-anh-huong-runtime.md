# REPORT — Scan ảnh hưởng hook TDQ tới runtime & đề xuất hook dạng hướng dẫn (`2026-11-18-1346-scan-hook-anh-huong-runtime` · lane full · mode subagent · 7/7 task tick đủ · giao sub-agent 5/7 task)

Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

**Trước request (trạng thái/flow):** User gặp nhiều lượt chạy kéo dài bất thường (`"1 commit"` mất `26,25` phút) và thấy hook TDQ xuất hiện dày đặc nên nghi ngờ hook gây chậm và cộc lốc khi chặn. Trong bản cài Antigravity `~/.gemini/config/plugins/tdq-workflow-agy`, mỗi lần gọi model chạy đồng bộ `2` tiến trình `PreInvocation` (`prompt_context.py` + `search_observe.py`) và `1` `PostInvocation`, còn mỗi tool chạy `1–2` `PreToolUse` + `1` `PostToolUse` qua `py -3`; chưa có số đo định lượng chi phí hook so với các nguyên nhân khác, và cổng vẫn dùng `deny` cứng thay vì hướng dẫn.
**Sau request (trạng thái/flow):** Không sửa mã sản phẩm (user chọn `1c`), hoàn thành bộ bằng chứng thực nghiệm tái chạy được (`8` file JSON + `6` script đo) và báo cáo nghiên cứu 9 mục `docs/tdq/research/2026-11-18-1346-scan-hook-anh-huong-runtime.md` · **Đã làm:** `P1` đo wall-clock `11` hook trên bản cài (`N=12`), quét `120` transcript `4` ngày (`11.241` model calls, `17.429` tool steps), phân rã `60` lượt dài `>= 10` phút (`long_turns.json`), đối chứng repo tạm `200` file git thuần vs qua hook (`N=5`), tái hiện `14` ca chặn nhầm (`false_positive_repro.json`) · `P2` kiểm kê AST `29/29` mã `[TDQ:*]` theo `tdq-lean` (`9` giữ chặn cứng, `1` tự sửa `overwrite`, `12` hướng dẫn qua hàng đợi + thẻ `user_markdown`, `7` xóa cùng `3` script mồ côi) và soạn đủ lời chỉ dẫn `4` phần cho `29/29` mã · `P3` viết báo cáo 9 mục kèm công thức ước tính tiết kiệm và lộ trình `3` request (`R1` hiệu năng lõi, `R2` làm mềm cổng + `user_markdown`, `R3` Stop 1 lần + dọn `tdq-lean`).
**Đã test gì:** Tái chạy `bench_hooks.py --n 12` & `hook_impact.py` đối chiếu sai lệch (`Tx.2`, `Q1`); kiểm tra lược đồ JSON và tỷ lệ khớp AST `29/29` mã (`Q2`, `Q8`); tái hiện `search_malformed`, `lsp_non_lsp`, `tick_loop` (`Q5`); thử `commit_merge_trial.py` `N=5` (`Q9`); chạy `doc_lint.py` trên `brief`, `spec`, `plan` (đã sửa 4 lỗi `[R15]`), `research`, `qc` (`Q4`); kiểm `git diff --stat dev` (`Q3`, spec §5); và chạy `tdq_test.py vung-cham` (`QC-F1` fallback sang trọn `207` module).
**Kết quả test:** Lượt dài `15–26` phút chủ yếu do **chờ lỗi API (`118` lỗi = `439,85` phút; ca `"1 commit"` mất `20,17/26,25` phút = `76,83%` cho `4` lần `stream idle timeout (5m0s)`) và model sinh chậm khi ngữ cảnh phình `>= 200k` token** (`0–50k` median `6,0 s` vs `400k+` median `53,0 s`); lệnh git + hook trong `commit_merge_trial.json` chỉ thêm **3,71 s** (`1.240,3 ms` → `4.948,02 ms`) · Hook vẫn góp chi phí thực: **~153,13 phút** đồng bộ (`prompt_context` `363,48 ms` vì `3` lệnh git, launcher `py -3` tốn `+17,62 ms/spawn`) + **`34,12` phút** chờ deny (`196` thô / `190` chuẩn hóa; `search_malformed` tái hiện `7/8`, `tick_loop` `2/2`, `lsp_non_lsp` `0/4` vì đã vá ở `4c5d5fd5` nhưng `call_mcp_tool` vẫn tốn `171,77 ms`), đề xuất mới ước tính cắt **~111,92 phút/4 ngày** ở hook và **~311,43 phút/4 ngày** ngoài hook · **Kiểm:** `Q1–Q9` & `QC-F1..F4` **PASS `14/14`**, `Tx.2` chênh bench max `3,2%` / deny `12,8%` (`<= 20%`), `tdq_test.py vung-cham` `PASS` `4.315` pass / `35` skip / `0` fail (`207` module, `radius misses: 0`), `doc_lint` `0` vi phạm.
**Đầu ra:** `docs/tdq/research/2026-11-18-1346-scan-hook-anh-huong-runtime.md`, `docs/tdq/bench/2026-11-18-1346-hook-runtime/*.py|*.json`, `docs/tdq/qc/2026-11-18-1346-scan-hook-anh-huong-runtime.md` · **Archify HTML:** `docs/tdq/reports/2026-11-18-1346-scan-hook-anh-huong-runtime.html` · Backup: không có
**Giới hạn:** Mở request bằng `--bo-qua-lsp` (`Request do dac/phan tich hook (doc transcript, do latency script Python), khong refactor symbol cheo module; grep + graphify du` · `python:.`) và duyệt spec bằng `--bo-qua-archify` (preview chỉ có Mermaid ở spec §2c, Archify HTML dựng ở report); `ruff` chưa có binary trên PATH Windows (`chưa kiểm tra` trên `6` script đo, riêng `long_turns.py` được kiểm thủ công ở `T1.4`); không sửa mã sản phẩm (user chọn `1c`); `eval: chưa kích hoạt (opt-in)`.
**Lệch spec chờ duyệt:** không có
**Git:** Nhánh `bugfix/hook-runtime-huong-dan` có `7` commit tài liệu/bằng chứng từ `0ac756f7`..`da6944bf` (để hợp nhánh worktree đội theo quy tắc `docs/**`, chưa push), cùng cập nhật cuối `plan`, `qc`, `reports` chờ bạn xác nhận commit & gộp về `dev`.

## Thời gian

Request `2026-11-18-1346-scan-hook-anh-huong-runtime` · lane full · opened at 2026-11-18T13:47:56+07:00

| Phase | Wall clock | API request | Tool wait | Background job | Observed union | Unattributed | Times entered |
|---|---|---|---|---|---|---|---|
| idle | 5s | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | 1 |
| analyze | 10 min | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | 1 |
| spec | 10 min | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | 1 |
| plan | 25 min | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | 1 |
| implement | 32 min | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | 1 |
| qc | 21 min | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | 1 |
| report | 0s | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | 1 |
| Total | 1h 37min | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] |  |

Model compute time is unavailable (`model_giay=null`). API includes network/provider latency; tool time is host wait. Observed metrics may overlap; unattributed time is not assumed user/model time.
Transcript attribution: project_window. Complete covers selected supported observations only.
- api_request_seconds: no_usable_source
- tool_call_seconds: no_usable_source
- background_job_seconds: no_usable_source
- observed_union_seconds: no_usable_observations
- unattributed_seconds: wall_minus_observed_union;no_usable_observations

## Thân PR (soạn sẵn)

**Tóm tắt:** Khảo sát thực nghiệm tác động runtime của hệ thống hook TDQ trên Antigravity (`120` transcript, `60` lượt dài, `11` hook, thử nghiệm `200`-file commit/merge) và đề xuất tái thiết kế theo hướng **hướng dẫn thay vì chặn** (`29/29` mã kiểm kê, ước tính cắt `111,92` phút/4 ngày ở hook và `311,43` phút/4 ngày ngoài hook).
**Trước/Sau:** `docs/tdq/reports/2026-11-18-1346-scan-hook-anh-huong-runtime.html`
**Đã kiểm:**
`py -3 docs/tdq/bench/2026-11-18-1346-hook-runtime/bench_hooks.py --n 12` & `hook_impact.py` → chênh tái lập max `3,2%` / `12,8%` (`<= 20%`)
`py -3 scripts/tdq_test.py vung-cham` → `PASS (4315 pass, 35 skipped, 0 failed across 207 modules, radius misses: 0)`
`py -3 scripts/doc_lint.py` (`brief`, `spec`, `plan`, `research`, `qc`) → `0 violation(s)`
**Rủi ro hồi quy:** Không sửa mã nguồn sản phẩm (`git diff --stat dev` chỉ có file dưới `docs/`); mọi đề xuất triển khai chia thành `3` request độc lập (`R1`–`R3`) kèm tiêu chí hồi quy rõ ràng.
<!-- tdq-archify-binding:start -->
<!-- manifest: 2026-11-18-1346-scan-hook-anh-huong-runtime.manifest.json -->
<!-- manifest_digest: 3557dce59789c1702d97063c19241c979c394ad8e4cce78dd22ea694a0dcd7d9 -->
<!-- tdq-archify-binding:end -->