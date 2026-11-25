# QC — Triển khai Pha P0: An toàn Runtime và Đồng bộ Python–Rust

Ngày: 2026-11-26 · Plan: ../plan/2026-11-25-1834-p0-runtime-safety-rust-parity.md (Vòng 2 — PASS)
Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

> **Tóm tắt dễ hiểu:** Pha P0 bổ sung neo khóa file bền trên Windows, thuê tác vụ có hạn giờ, kiểm soát công cụ ngoài LSP, ngắt mạch tự động khi lỗi lặp và giới hạn ngân sách trên cả Python lẫn Rust. Qua hai vòng kiểm chéo độc lập mức ultra, toàn bộ năm bài test hỏng ở vòng một và ba lỗ hổng bảo mật giữa Python với Rust đã được vá dứt điểm. Toàn bộ 5,005 bài test hệ thống, 41 test Rust và bộ kiểm định đóng gói Antigravity đều đạt 100%, sẵn sàng chuyển sang pha báo cáo.

## Dev Behavior QC Card
- Auto Meta-Gate: `doc_lint` 0 lỗi (7 file báo cáo/plan ở lần quét đầu), `git_co_author` 0 lỗi, `i18n_check` 0 dòng tiếng Việt mới trên toàn bộ code P0 (200 dòng cảnh báo thuộc mã nền cũ của `tdq_state.py`, `tdq_team.py`, `edit_gate.py`, `lsp_gate.py`).
- Luồng đổi: Từ `tdq_state.save()` ghi đè không khóa sidecar bền, bỏ lọt MCP ngoài LSP và thiếu ngắt mạch/ngân sách sang cơ chế khóa `.lock` không xóa neo, lease `O_EXCL` TTL, cách ly MCP mới bằng mã `READONLY` kèm đồng bộ Rust `tdq-dispatch.exe` giữ nguyên 23 mã cổng AGY và `schema_version=6`.
- Chạy thử thật (Before → After + Bằng chứng tươi trên `d32b911b`):
  - Vòng 1 phát hiện 5 module test đỏ (`test_hooks_dual_protocol`, `test_lsp_gate`, `test_bao_cao_da_nen_tang`, `test_compliance_protocol`, `test_utf8_io`) — đã vá tại `QC1.1`–`QC1.5` (`80ce4f69`), đưa `tron-bo` lên `5,004/5,004` (`0` lỗi).
  - `tdq-qc-tester` vòng 1 (`91980224-99aa-4d3b-9859-5216b97a70f3`) bắt 3 lỗ hổng thật (`Q3`/`Q6`): `&`/`\r` lọt ở Python `_is_p0_unlock_cmd`, `#`/`>`/đối số giả lọt qua lệnh mở khóa ở cả Python và Rust, và Rust thiếu đọc trực tiếp `.tdq-agent-telemetry.jsonl` cho `hard_stop_tokens`/`hard_stop_usd` — đã vá dứt điểm tại `QC2.1`–`QC2.2` (`d32b911b`).
  - Sau `d32b911b`: `tools/run_full_verification.py` đạt `24/24` (`agy plugin validate --strict` 0 findings), `tdq_test.py tron-bo` đạt `5,005` collected (`37` skip sẵn có, `0` lỗi trong `336.99s`), và `tdq-qc-tester` vòng 2 (`f93c6a21-e0e6-4534-a73d-17eb10dd8903`) xác nhận `Verdict: PASS` (`DEFECTS: None`).
- Rủi ro còn lại: `TDQ_LOG=1/0` chạy 0B stderr trên toàn bộ module P0; file `docs/tdq/spec/2026-11-25-1834-p0-runtime-safety-rust-parity-preview.manifest.json` giữ nguyên `binding.status=current` (phần source fingerprint đánh dấu `stale` là hợp lệ vì source đã phát triển sau spec); `tdq_test.py so` ghi nhận `3/3` lượt `tron-bo`, `0` ca bỏ sót vùng chạm.

## Bảng kết quả DoD và QC cố định

| # | Hạng mục | Lệnh đã chạy | Kết quả | PASS/FAIL |
|---|---|---|---|---|
| Q1 | Unit test mới (`T1.1`, `T2.2`, `T2.3`, `T2.4`) & `TDQ_LOG=1/0` | `py -3 -X utf8 -m pytest -q tests/test_tdq_lease.py tests/test_tdq_queue.py tests/test_tdq_timing_budget.py tests/test_mcp_policy.py` | `43 passed, 12 subtests passed`; `TDQ_LOG=0` ra `0B` stderr, `TDQ_LOG=1` có ISO timestamp; neo `.lock` giữ nguyên khi unlock | PASS |
| Q2 | Khóa NTFS, `schema_version=6` & `reset-breaker` | `py -3 -X utf8 -m pytest -q tests/test_state.py tests/test_ntfs_concurrency.py tests/test_build_portable.py` | `108 passed, 34 subtests passed in 151.61s`; `schema_version=6`; `reset-breaker --json` exit `0` | PASS |
| Q3 | Rust build/test/clippy & Parity Python–Rust (`23` mã AGY) | `cargo test/clippy`; `pytest -q tests/test_bash_gate.py tests/test_rust_dispatch_parity.py ...`; kiểm tra bypass | Cargo `41 passed` (`0` cảnh báo Clippy ở `lock.rs`/`pre_tool_use.rs`); Python–Rust combo `148 passed, 93 subtests passed`; `6/6` + `9` ca bypass đều bị chặn `READONLY`; live telemetry `200 > 100` chặn `4/4` `READONLY` | PASS |
| Q4 | Đóng gói đa host (`build_agy_plugin`, `--sinh-main --dry-run`, `token`, `i18n`) | `build_portable.py --sinh-main --dry-run`; `token_budget.py --kiem`; `agy validate --strict`; `test_agent_upgrade_mvp.py` | `kept=200`; `token_budget` exit `0`; `i18n_new=0`; `findings=[]`; `len(_common.CODES)==23`; `mcp_.*\|call_mcp_tool` và `mcp-policy.default.json` đã đồng bộ vào plugin | PASS |
| Q5 | Hồi quy toàn dự án, Ruff, AST `0` import chéo | `ruff check`; quét AST `80` scripts; `tools/run_full_verification.py`; `tdq_test.py tron-bo` | Ruff `All checks passed!`; `hooks_imports_in_scripts=0`; `run_full_verification.py` `24/24` (`0` finding); `tron-bo` `5,005` test (`37` skip, `0` lỗi trong `336.99s`) | PASS |
| Q6 | Thẩm định độc lập `ultra` (`tdq-qc-tester`) | Subagent `tdq-qc-tester` vòng 2 (`f93c6a21-e0e6-4534-a73d-17eb10dd8903`) trên `d32b911b` | Kiểm độc lập `D1-2`, `D3`, `Q1`–`Q5`, `QC-F1`–`QC-F4` → `Verdict: PASS`, `DEFECTS: None` | PASS |
| Q7 | Báo cáo, working log & Archify HTML `current` | `tdq_archify.py render --type explainer` + `verify` + Tailscale HEAD `200` | `status=current`, `binding.valid=true`, `1,588,574` bytes HTML, Tailscale HTTP `200` | PASS |
| QC-F1 | Binding spec, worktree, commit sạch trailer & `23` mã | `tdq_archify.py verify` trên `spec.md`; `git worktree list`; `git log bc5e9b19..HEAD` | Spec `binding.status=current`; 1 worktree gốc; `0` dòng `Co-Authored-By:`; `23` mã AGY; `schema_version=6` | PASS |
| QC-F2 | Độ phủ kiểm thử từng vùng file ở dòng `Chạm:` | Đối chiếu unit/integration test cho `T1.1`–`T5.2` + `QC1.1`–`QC2.2` | Đủ kiểm thử cho mọi module mới và sửa (`0` module bỏ trống) | PASS |
| QC-F3 | Ràng buộc kiến trúc `scripts/` vs `hooks/`, `TDQ_LOG=1/0` | AST `80` file `scripts/*.py`; kiểm `TDQ_LOG=1/0` thực tế | `0` import ngược `scripts/` → `hooks/`; `TDQ_LOG=0` xuất `0B` stderr | PASS |
| QC-F4 | Clean Code, SOLID, độ dài hàm `<= 50` dòng | Rà AST + đọc chéo toàn bộ hàm Python và Rust P0 | `0` hàm mới quá `50` dòng, `0` stub/TODO, fail-closed nhất quán | PASS |

## Bằng chứng

### Vòng QC 1 — Fix (`QC1.1`–`QC1.5`, commit `80ce4f69`)
- `QC1.1`: Bổ sung `chrome-devtools`, `tdq-workflow-agy_chrome-devtools`, `tavily-primary`, `tdq-workflow-agy_tavily-primary` vào `trusted_servers` và `select_` vào `read_prefixes` ở `scripts/defaults/mcp-policy.default.json` + `scripts/mcp_policy.py`. Đóng 3 ca lỗi EC-16 và `test_lsp_gate.py`.
- `QC1.2`: Thay `importlib.import_module("utf8_io")` bằng nạp tĩnh `import utf8_io` ở `scripts/tdq_lease.py` và `scripts/mcp_policy.py` (`test_utf8_io.py` PASS).
- `QC1.3`: Thêm helper `is_denied()` trong `scripts/mcp_policy.py`, dùng tại `hooks/scripts/lsp_gate.py` để xóa chuỗi `"deny"` khỏi hook, đồng thời ghi chú ngoại lệ thư viện `scripts/mcp_policy.py` trong `tests/test_compliance_protocol.py` (`test_no_transcript_no_deny` PASS).
- `QC1.4`: Gộp `_lock_fd`/`_unlock_fd` qua `_flock_fd` trong `scripts/tdq_lease.py` còn 1 nhánh `import fcntl` có guard OS và cập nhật mốc báo cáo nền tảng `1` → `2` (`test_bao_cao_da_nen_tang.py` PASS).
- `QC1.5`: Thêm `split_eager_mcp_name()` ở `scripts/mcp_policy.py` và đồng bộ `extract_mcp_server_and_tool()` ở `pre_tool_use.rs` theo longest-match `trusted_servers` + single-segment `_lsp_` (cho phép `mcp_other_lsp_start_lsp`, vẫn chặn `mcp_evil_delete_lsp_entry`).

### Vòng QC 2 — Fix (`QC2.1`–`QC2.2`, commit `d32b911b`)
- `QC2.1`: Thay so khớp chuỗi con ở `hooks/scripts/bash_gate.py` (`_is_p0_unlock_cmd`) và `hooks/rust/tdq-dispatch/src/events/pre_tool_use.rs` (`is_p0_unlock_command`) bằng phân tích token `argv` (`py`/`python`/`python3` + `tdq_state.py reset-breaker` hoặc `mcp_policy.py approve|reset`) và từ chối `&`, `\r`, `\n`, `|`, `` ` ``, `$(`, `<`, `>`, `#`, `-c`.
- `QC2.2`: Bổ sung `load_budget_caps_rust()`, `sum_telemetry_usage_rust()`, `is_budget_hard_stop_reached()` vào `check_p0_runtime_guard()` trong `pre_tool_use.rs`, đồng bộ công thức đọc `.tdq-agent-telemetry.jsonl` và `p0.budget_caps` giống hệt `tdq_timing.check_budget_status()`.

### Bằng chứng hậu `d32b911b`
```
tdq-qc-tester Round 2 (f93c6a21-e0e6-4534-a73d-17eb10dd8903):
- D1-2 Unlock bypass/allow parity (Py src + AGY Py + tdq-dispatch.exe): 6/6 malicious + 9 extra -> [TDQ:READONLY]; 3/3 valid -> allow
- D3 Live telemetry hard_stop parity (edit_gate + bash_gate + tdq-dispatch.exe): tokens=200 > cap=100 -> 4/4 [TDQ:READONLY]; 50/null -> allow
- Cargo test: 41 passed (37 lib + 4 bin), 0 failed; clippy --tests: 0 warnings in lock.rs & pre_tool_use.rs
- Q1: 43 passed, 12 subtests passed; Q2 + portable: 108 passed, 34 subtests passed in 151.61s; Q3 parity combo: 148 passed, 93 subtests passed
- tools/run_full_verification.py: pytest 24/24 passed (36.03s), agy plugin validate --strict findings=[], status OK
- scripts/tdq_test.py tron-bo --workers auto --fresh --reuse off: PASS — tests=5005 skipped=37 failed=0 in 336.99s
- scripts/tdq_test.py so: full-suite runs=3/3, radius misses=0
Verdict: PASS | DEFECTS: None
```

### QC-F3 & QC-F4 — Ràng buộc kiến trúc & 5 câu hỏi SOLID
- **SRP:** Tách rõ `tdq_lease.py` (lock/TTL lease), `mcp_policy.py` (phân loại/baseline MCP), `tdq_timing.py` (đo ngân sách telemetry), `tdq_team.py` (hàng đợi ưu tiên 3 tầng & DAG wave), còn 3 hook Python và Rust `pre_tool_use.rs`/`lock.rs` chỉ thi hành cổng.
- **OCP:** Mọi tiền tố đọc/ghi MCP, `trusted_servers`, `p0` config defaults và cấp độ lỗi đều đặt trong JSON/dict cấu hình để mở rộng không sửa logic cốt lõi.
- **LSP:** Đường dẫn Python `evaluate_tool_call` và Rust `evaluate_non_lsp_mcp_rust` trả cùng ngữ nghĩa `READONLY` + gợi ý lệnh CLI `approve`; `tdq_state.load()` lấp tương thích bản ghi v6 thiếu `p0_runtime`.
- **ISP:** Các hàm guard chỉ nhận `cwd`/`workspace_root` hoặc cấu trúc `NormalizedToolCall`/`state`, không ép phụ thuộc chéo (`0` import ngược `scripts/` → `hooks/`).
- **DIP:** `lsp_gate.py`, `edit_gate.py`, `bash_gate.py` đều gọi qua giao diện công khai của `mcp_policy`, `tdq_config`, `tdq_timing`, `tdq_state`; `lock.rs` giữ nguyên bất biến neo sidecar `.lock` độc lập nền HĐH.

## Lệch spec chờ duyệt
không có

## Kết luận
PASS (vòng 2 — `tdq-qc-tester` xác nhận `Verdict: PASS`, `DEFECTS: None`; toàn bộ `5,005` test `tron-bo`, `24/24` kiểm chứng đóng gói Antigravity và `7/7` DoD `Q1`–`Q7` đều đạt PASS kèm Archify HTML `current` HTTP `200`).
