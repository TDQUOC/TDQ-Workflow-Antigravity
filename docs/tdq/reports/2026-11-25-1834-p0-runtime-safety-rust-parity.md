# BÁO CÁO — Triển khai Pha P0: An toàn Runtime và Đồng bộ Python–Rust

Ngày: 2026-11-26 · Mã yêu cầu: `2026-11-25-1834-p0-runtime-safety-rust-parity` (14/14 task kế hoạch + 5 task QC1 + 2 task QC2 tick đủ)
Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

> **Tóm tắt dễ hiểu:** Trước khi làm, lệnh lưu trạng thái dễ tranh chấp khóa trên Windows và thiếu khóa thuê cho tác vụ. Công cụ ngoài tìm kiếm mã chạy tự do, còn Rust chưa chặn ngắt mạch hay vượt ngân sách. Nay hệ thống giữ neo khóa cố định trên cả Python và Rust, thêm hàng đợi ba tầng và kiểm tra ngân sách trực tiếp. Các công cụ ghi mới bị chặn bằng mã READONLY cho đến khi được duyệt. Sau hai vòng kiểm chéo, toàn bộ 5,005 bài test hệ thống, 41 test Rust và 24 kiểm chứng đóng gói đều đạt 100%.

**Trước request (trạng thái/flow):**
- Hàm `tdq_state.save()` chỉ giữ khóa ghi trong ngữ cảnh hook mà thiếu khóa sidecar NTFS cố định từ CLI bên ngoài, dễ đua tạo và xóa file khóa trên Windows, đồng thời chưa có cơ chế lease `O_EXCL` TTL tự thu hồi khi worker treo.
- `hooks/hooks.json`, `tools/patches/agy_manifests.py` và `hooks/scripts/lsp_gate.py` thoát êm (`exit 0`) với mọi công cụ MCP ngoài `tdq-lsp`, khiến các công cụ ghi hoặc xóa chưa được rà chữ ký.
- Các cổng Python (`edit_gate.py`, `bash_gate.py`) và nhị phân Rust (`tdq-dispatch.exe`) chưa có Circuit Breaker khi lỗi liên tiếp hay kiểm tra ngưỡng ngân sách; hàng đợi `tdq_team.py` chưa có chia tầng ưu tiên và chống bỏ đói tác vụ chờ lâu.

**Sau request (trạng thái/flow):**
- **Khóa bền Sidecar & Lease TTL (`T1.1`, `T1.3`, `T2.1`):** Thêm `scripts/tdq_lease.py` (giữ file neo `.lock` không bao giờ unlink khi mở khóa, lease `O_EXCL` có TTL và tự thu hồi bản ghi hết hạn) đồng bộ với `hooks/rust/tdq-dispatch/src/lock.rs` (`is_lease_expired`, `cleanup_expired_leases`). Bọc `tdq_state.save()` trong sidecar lock, giữ nguyên `schema_version=6`, tự backfill `p0_runtime` (`breaker`, `budget`, `quarantined_tools`) và thêm lệnh `reset-breaker`.
- **Cấu hình cân bằng, Ngân sách & Hàng đợi 3 tầng (`T1.2`, `T2.2`, `T2.3`):** Thêm khối mặc định `p0` trong `scripts/tdq_config.py` + `tdq-config.json` (kèm 3 công tắc `lease_enabled`, `breaker_enabled`, `mcp_quarantine_enabled`; trần ngân sách mặc định `null`). `scripts/tdq_timing.py` bổ sung `check_budget_status()` trả `ok`, `soft_warn` (>= 80%), `hard_stop` (>= 100% khi đặt trần dương). `scripts/tdq_team.py` hỗ trợ hàng đợi 3 tầng (`P0`/`P1`/`P2`) với nhịp aging `OLDEST_DISPATCH_SHARE=4`, `blocked_by`, `idempotency_key` và `dispatch_ready_waves()`.
- **Kiểm soát MCP chọn lọc & Parity Python–Rust (`T2.4`, `T3.1`–`T3.4`, `T4.1`, `QC1.1`–`QC2.2`):** Thêm `scripts/mcp_policy.py` và `scripts/defaults/mcp-policy.default.json` (chế độ cân bằng cho phép nhanh công cụ đọc, `lsp` và các máy chủ đi kèm như `chrome-devtools`, `tavily-primary`; cách ly công cụ ghi/xóa mới xuất hiện hoặc đổi SHA-256 schema bằng mã sẵn có `READONLY` kèm lệnh mở `approve`). Nối cổng kiểm soát MCP và Breaker/Budget vào `lsp_gate.py`, `edit_gate.py`, `bash_gate.py` cùng bản đối ứng trong Rust `pre_tool_use.rs` (kèm kiểm tra lệnh mở khóa theo token `argv` và đọc trực tiếp `.tdq-agent-telemetry.jsonl`). Giữ nguyên tròn `23` mã cổng AGY (`_common.CODES`).

**Đã test gì:**
- Kiểm thử đơn vị và tích hợp theo từng cụm (`test_tdq_lease.py`, `test_tdq_queue.py`, `test_tdq_timing_budget.py`, `test_mcp_policy.py`, `test_state.py`, `test_ntfs_concurrency.py`, `test_bash_gate.py`).
- Kiểm chứng biên dịch Rust và parity Python–Rust (`cargo test`, `cargo clippy --tests`, `cargo build --release`, `tools/build_agy_plugin.py`, `test_rust_dispatch_parity.py`, `test_build_portable.py`, `test_agent_upgrade_mvp.py`, `build_portable.py --sinh-main --dry-run`).
- Kiểm tra tĩnh & dịch vụ log (`log-verify.json` của `T5.1`, `ruff check`, quét AST `0` import ngược `scripts/` → `hooks/`, `i18n_check.py`, `token_budget.py --kiem`, `TDQ_LOG=1/0`).
- Nghiệm thu toàn hệ thống mức `ultra` hậu commit sửa cuối `d32b911b`: `tools/run_full_verification.py`, `scripts/tdq_test.py tron-bo --workers auto --fresh --reuse off`, `scripts/tdq_test.py so` và 2 vòng thẩm định độc lập của `tdq-qc-tester` (gồm probe đối kháng bypass `&`, `\r`, `#`, `>`, `-c` và ngân sách telemetry thực).

**Kết quả test:**
- `tests/test_tdq_lease.py` + `test_tdq_queue.py` + `test_tdq_timing_budget.py` + `test_mcp_policy.py`: `43 passed, 12 subtests passed`; xác minh neo `.lock` còn nguyên khi unlock và `TDQ_LOG=0` ra đúng `0B` stderr trên các module P0 (`TDQ_LOG=1` có ISO timestamp).
- `tests/test_state.py` + `test_ntfs_concurrency.py` + `test_build_portable.py`: `108 passed, 34 subtests passed in 151.61s`; `schema_version=6` và CLI `reset-breaker` xanh.
- Rust `cargo test`: `41 passed` (`37` lib + `4` bin, `0` failed); `cargo clippy --tests`: `0` cảnh báo trong `lock.rs` và `pre_tool_use.rs`.
- Cụm parity `tests/test_bash_gate.py` + `test_rust_dispatch_parity.py` (+ `test_hooks_dual_protocol` / `test_lsp_gate`): `148 passed, 93 subtests passed`; `6/6` kịch bản bypass do `tdq-qc-tester` tạo và `9` ca bổ sung đều bị chặn `READONLY` đồng nhất trên Python nguồn, bundle AGY và `tdq-dispatch.exe`; live telemetry (`200 > 100` token cap) chặn `4/4` `READONLY`.
- Đóng gói & tĩnh: `build_agy_plugin.py` `OK` (`py=91, mjs=3, md=22, ref_md=68`); `build_portable.py --sinh-main --dry-run` `kept=200`; `token_budget.py --kiem` exit `0`; `i18n_check.py` `0` dòng tiếng Việt mới; Ruff `0` lỗi ở 7 file mới và `--select E,F --ignore E501,E741` trên 6 file cũ; AST `80` file `scripts/*.py` có `0` import `hooks`/`_common`; `len(_common.CODES) == 23`.
- `tools/run_full_verification.py` (trên `d32b911b`): `pytest` `24/24` passed (`36.03s`), `agy plugin validate --strict` `0` findings (cả local và staged).
- `tdq_test.py tron-bo --workers auto --fresh --reuse off` (trên `d32b911b`): `PASS — 5,005 tests collected, 37 skipped, 0 failed in 336.99s` (`246` module, `result.json` sha256 `2bd8fcbc...`); `tdq_test.py so`: `full-suite runs=3/3`, `radius misses=0`.
- `tdq-qc-tester` vòng 2 (`f93c6a21-e0e6-4534-a73d-17eb10dd8903`): `Verdict: PASS`, `DEFECTS: None`. · **Eval:** `eval: chưa kích hoạt (opt-in)` · **Phân rã đội:** `9/14` task giao `tdq-implementer`/`tdq-qc-tester` (`5` task `tu_lam` giữ trên Leader vì chạm file luật/vùng khóa).

**Đầu ra:** `scripts/tdq_lease.py`, `scripts/mcp_policy.py`, `scripts/defaults/mcp-policy.default.json`, `scripts/tdq_config.py`, `scripts/tdq_state.py`, `scripts/tdq_timing.py`, `scripts/tdq_team.py`, `tdq-config.json`, `hooks/scripts/lsp_gate.py`, `hooks/scripts/edit_gate.py`, `hooks/scripts/bash_gate.py`, `hooks/hooks.json`, `tools/patches/agy_manifests.py`, `hooks/rust/tdq-dispatch/src/lock.rs`, `hooks/rust/tdq-dispatch/src/events/pre_tool_use.rs`, `plugins/tdq-workflow-agy/`, `tests/test_tdq_lease.py`, `tests/test_mcp_policy.py`, `tests/test_tdq_queue.py`, `tests/test_tdq_timing_budget.py`, [qc.md](file:///C:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/qc/2026-11-25-1834-p0-runtime-safety-rust-parity.md) · **Archify HTML:** [2026-11-25-1834-p0-runtime-safety-rust-parity.html](file:///C:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/reports/2026-11-25-1834-p0-runtime-safety-rust-parity.html) (Tailscale Serve: `https://unity-pc-rtx3060.tail99896.ts.net/vlog/tdq-workflow-agy/reports/2026-11-25-1834-p0-runtime-safety-rust-parity.html`)

**Giới hạn:**
- `37` bài test bị `skipped` trong `tron-bo` thuộc các kiểm tra phụ thuộc đặc thù hệ điều hành (symlink Windows không chạy quyền admin hoặc nhánh POSIX-only), hoàn toàn không có test thất bại.
- `i18n_check` quét toàn file vẫn ghi nhận các dòng mô tả/chú thích tiếng Việt có sẵn trên nền `dev` trong các file cũ (`tdq_state.py`, `tdq_team.py`, `edit_gate.py`, `lsp_gate.py`); phần mã P0 viết mới có `0` dòng tiếng Việt.
- Tệp `plugins/tdq-workflow-agy/manifest.json` và `docs/verification_evidence.json` cập nhật tự động khi chạy `run_full_verification.py` hậu `d32b911b`; sẽ đi cùng phần tài liệu báo cáo nếu người dùng chốt commit cuối.

**Lệch spec chờ duyệt:** không có

**Git:** Chưa tạo commit chốt cuối và chưa merge về `dev`; đã có 20 commit trung gian (cộng các commit hợp nhất worktree nhánh phụ) trên nhánh `feat/p0-runtime-safety-rust-parity`:
- `68b38e73` chore(p0): checkpoint request state and docs before wave merges
- `cf06912a` feat(T1.3): add lease TTL expiration and cleanup helpers to lock.rs
- `1b01f42b` chore(p0): sync worklog and graphify after T1.3
- `f9a16739` feat(lease): add sidecar lock, TTL lease manager, and default mcp policy
- `d7062c46` feat(p0): add balanced p0 default config block
- `2acc9dc6` feat(mcp-policy): add SHA-256 baseline classifier and balanced quarantine CLI
- `762432db` feat(T3.3): widen non-LSP MCP PreToolUse matchers
- `af8699e8` chore(p0): sync worklog and graphify after T3.3
- `6a6da101` feat(p0): wrap state save in sidecar lock and add v6 p0_runtime
- `f2616846` feat(T3.2): add P0 MCP quarantine and circuit breaker parity in pre_tool_use.rs
- `ffe354a3` chore(p0): sync worklog and graphify after T3.2
- `eda57ffd` test(T3.4): approve tdq_lease, mcp_policy, and default MCP policy in release budget
- `e9d423f3` chore(p0): sync docs before T2.3 merge
- `ad8d63ea` feat(T2.3): add soft_warn and hard_stop budget tracking in tdq_timing
- `2228fc89` feat(T2.2): add 3-tier queue with aging, blocked_by, and idempotency_key
- `7f2c3d63` feat(T3.1): wire P0 MCP policy and circuit breaker guards into Python hooks
- `c2aadfac` feat(T4.1): sync tdq-config.json, release Rust binary, and Antigravity bundle
- `e5bf0171` fix(p0): harden Rust is_p0_unlock_command against chained shell bypass
- `80ce4f69` fix(qc1): fix eager MCP parsing parity, trust bundled MCP servers, add static utf8_io, dedupe fcntl, and pass compliance audit
- `d32b911b` fix(qc2): enforce tokenized P0 unlock validation and live telemetry budget guard parity

## Thời gian

```
Request `2026-11-25-1834-p0-runtime-safety-rust-parity` · lane full · opened at 2026-11-25T18:42:50+07:00

| Phase | Wall clock | Times entered |
|---|---|---|
| idle | 0s | 1 |
| analyze | 60 min | 1 |
| spec | 3h 15min | 1 |
| plan | 5 min | 1 |
| mode | 8 min | 1 |
| implement | 1h 03min | 1 |
| qc | 59 min | 1 |
| report | 1s | 1 |
| Total | 6h 30min |  |

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

**Tóm tắt:** Triển khai trọn vẹn Pha P0 cho TDQ Workflow gồm sidecar `.lock` bền và lease `O_EXCL` TTL (Python + Rust `lock.rs`), hàng đợi ưu tiên 3 tầng chống bỏ đói tác vụ cũ, kiểm soát ngân sách soft-warn/hard-stop từ `.tdq-agent-telemetry.jsonl`, Circuit Breaker, kiểm soát công cụ MCP ngoài LSP ở chế độ cân bằng mã `READONLY`, đồng bộ đầy đủ với Rust `tdq-dispatch.exe` giữ tròn 23 mã cổng AGY và `schema_version=6`.
**Trước/Sau:** [truoc-sau.html](file:///C:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/spec/2026-11-25-1834-p0-runtime-safety-rust-parity-preview.html) và [bao-cao.html](file:///C:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/reports/2026-11-25-1834-p0-runtime-safety-rust-parity.html)
**Đã kiểm:**
- `py -3 -X utf8 -m pytest -q tests/test_tdq_lease.py tests/test_tdq_queue.py tests/test_tdq_timing_budget.py tests/test_mcp_policy.py` → `43 passed, 12 subtests passed`
- `py -3 -X utf8 -m pytest -q tests/test_state.py tests/test_ntfs_concurrency.py tests/test_build_portable.py` → `108 passed, 34 subtests passed`
- `cargo test --manifest-path hooks/rust/tdq-dispatch/Cargo.toml` → `41 passed, 0 failed` (`cargo clippy --tests`: `0` warnings ở `lock.rs`, `pre_tool_use.rs`)
- `py -3 -X utf8 tools/run_full_verification.py` → `24/24` passed, `agy plugin validate --strict` `0` findings
- `py -3 -X utf8 scripts/tdq_test.py tron-bo --workers auto --fresh --reuse off` → `5,005` tests collected, `37` skipped, `0` failed in `336.99s`
- `tdq-qc-tester` vòng 2 (`f93c6a21-e0e6-4534-a73d-17eb10dd8903`) → `Verdict: PASS`, `DEFECTS: None`
**Rủi ro hồi quy:** Điểm chạm rộng nhất là cổng `PreToolUse` MCP/Breaker trên cả Python và Rust cùng bộ mặc định `mcp-policy.default.json`. Rủi ro được khóa bởi `5,005` bài test toàn kho, `41` test Rust và kiểm chéo đối kháng độc lập ở vòng 2, giữ nguyên tương thích `schema_version=6` và `23` mã cổng AGY.
<!-- tdq-archify-binding:start -->
<!-- manifest: 2026-11-25-1834-p0-runtime-safety-rust-parity.manifest.json -->
<!-- manifest_digest: 6d51989cd23984859a0186a410bf4c5d4676475ae88042c0f3c46d6c0324b28e -->
<!-- tdq-archify-binding:end -->