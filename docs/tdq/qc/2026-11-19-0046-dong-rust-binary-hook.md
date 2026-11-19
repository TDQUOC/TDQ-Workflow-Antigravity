# QC — Đóng Rust binary thay dispatch.py cho hook Antigravity

Ngày: 2026-11-19 · Plan: ../plan/2026-11-19-0046-dong-rust-binary-hook.md · Mức QC: `full` · Vòng: 1
Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

| # | Hạng mục | Lệnh đã chạy | Kết quả | PASS/FAIL |
|---|---|---|---|---|
| Q1 | Cú pháp tài liệu doc_lint | `py -3 scripts/doc_lint.py docs/tdq/brief/... docs/tdq/spec/... docs/tdq/plan/...` | 0 vi phạm trên brief, spec, plan | PASS |
| Q2 | Biên dịch crate Rust trên Windows | `cargo build --manifest-path hooks/rust/tdq-dispatch/Cargo.toml --release` | Hoàn thành trong 0.04s, 0 cảnh báo, sinh `tdq-dispatch.exe` (1.65 MB, static CRT) | PASS |
| Q3 | Tương thích chuẩn hook Antigravity | `agy plugin validate plugins/tdq-workflow-agy --strict` | `✔ Validation passed` (0 errors, 0 warnings) | PASS |
| Q4 | Kiểm thử đối chiếu vi phân 1-1 | `py -3 -m pytest tests/test_rust_dispatch_parity.py -q` | 10/10 passed trong 1.30s (khớp 100% quyết định trên 6 sự kiện hook) | PASS |
| Q5 | An toàn khóa tệp đa tiến trình | `py -3 -m pytest tests/test_rust_lock_safety.py -q` | 1/1 passed trong 0.20s (20 tiến trình ghi đồng thời, 0 lỗi `os error 33`, đủ 20 dòng) | PASS |
| Q6 | Cơ chế dự phòng khi thiếu binary | `py -3 -c "import os, subprocess; env=dict(os.environ, TDQ_HOOK_ENGINE='python'); ..."` | Chuyển tiếp thành công sang Python dispatch, returncode=0, kết quả hợp lệ | PASS |
| Q7 | Mục tiêu độ trễ hook đường nóng | `py -3 -m pytest tests/test_rust_latency_benchmark.py -q -s` | Rust trực tiếp đạt trung vị 19.90 ms (nhanh hơn Python 9.6 lần, <= 25 ms) | PASS |
| Hợp đồng | 3 khối kỹ năng trong plan | `tdq-conventions`, `agy-customizations`, `tdq-checkportable` | `i18n_check.py` 0 lỗi, `tdq_checkportable.py` exit code 0 | PASS |
| QC-F1 | Unit test nội bộ Crate Rust | `cargo test --manifest-path hooks/rust/tdq-dispatch/Cargo.toml -q` | 20/20 test passed trong 0.06s | PASS |
| QC-F2 | Trọn bộ bài kiểm thử hook | `py -3 -m pytest tests/test_rust_*.py -q` | 12/12 passed trong 16s | PASS |
| QC-F3 | Ràng buộc kiến trúc (spec §5) | Đối chiếu thay đổi với spec §5 | Mã Rust nằm trong `hooks/rust/tdq-dispatch/`, target loại trừ khỏi git | PASS |
| QC-F4 | Clean code & Defender safe | Soát theo `Cargo.toml` và `.cargo/config.toml` | `lto = "thin"`, `panic = "abort"`, `strip = "symbols"`, static CRT | PASS |

## Bằng chứng thực nghiệm

### Bằng chứng Q1 (doc_lint)
```text
[2026-11-19T11:30:18] doc_lint: lint 3 file: 2026-11-19-0046-dong-rust-binary-hook.md, 2026-11-19-0046-dong-rust-binary-hook.md, 2026-11-19-0046-dong-rust-binary-hook.md
[2026-11-19T11:30:18] doc_lint: R14 2026-11-19-0046-dong-rust-binary-hook.md → 0 finding(s)
[2026-11-19T11:30:18] doc_lint: done — 0 violation(s) total, exit 0
```

### Bằng chứng Q3 (agy plugin validate --strict)
```text
Validating tdq-workflow-agy (plugins\tdq-workflow-agy\plugin.json)
  skills 12 · agents 6 · rules 10 · hooks 6 · mcpServers 3 · sidecars 0
✔ Validation passed
```

### Bằng chứng Q4 & Q5 (Differential parity & Concurrent lock safety)
```text
tests/test_rust_dispatch_parity.py: 10 passed in 1.30s
tests/test_rust_lock_safety.py: 1 passed in 0.20s (20 concurrent subprocesses, 0 lock violations)
```

### Bằng chứng Q7 (Latency benchmark N=30 runs)
```text
=================================================================
           TDQ HOOK DISPATCH LATENCY BENCHMARK REPORT          
=================================================================
Sample size: 30 iterations per configuration
-----------------------------------------------------------------
Engine & Mode                  | Median (ms)  | P95 (ms)  
-----------------------------------------------------------------
Rust Binary (Direct)           |       19.90 |     21.19
Rust Binary (cmd /c wrapper)   |       28.37 |     30.14
Python Dispatch (Direct)       |      190.21 |    195.96
Python Dispatch (cmd /c)       |      199.36 |    206.92
-----------------------------------------------------------------
Speedup Direct: 9.6x faster
Speedup Shell Wrapper: 7.0x faster
=================================================================
```

## Xác nhận từ Subagent QC độc lập (`tdq-qc-tester`)
Subagent `tdq-qc-tester` (id `3429247e-6ff4-40a1-99c3-3e38391ea452`) đã chạy lại độc lập và xác nhận:
- Toàn bộ 7 hạng mục Q1–Q7: **PASS 100%**.
- Defect minor quan sát được (thiếu timestamp khi `TDQ_DEBUG=1`): đã khắc phục ngay tại `hooks/rust/tdq-dispatch/src/main.rs:102`, biên dịch và kiểm chứng lại có timestamp `[<timestamp>Z]`.
- **VERDICT: PASS everything**.

## Lệch spec chờ duyệt
Không có. Tất cả các yêu cầu kỹ thuật và hợp đồng dữ liệu đều được đáp ứng đầy đủ.

## Kết luận
PASS toàn bộ (12/12 hạng mục kiểm định, gồm 7 DoD Q1–Q7, 3 hợp đồng skill và các tiêu chuẩn kiến trúc). Sẵn sàng chuyển sang Phase Report.
