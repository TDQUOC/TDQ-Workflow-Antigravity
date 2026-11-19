# Báo cáo nghiệm thu — Kiến trúc Hook Hybrid 2 tầng + Smart Hardening

- **Mã yêu cầu (`Request Slug`)**: `2026-11-19-1632-hybrid-hook-smart-hardening`
- **Nhánh phát triển**: `feature/hybrid-hook-smart-hardening` (nền `dev`)
- **Đặc tả (Spec)**: [2026-11-19-1632-hybrid-hook-smart-hardening.md](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/spec/2026-11-19-1632-hybrid-hook-smart-hardening.md)
- **Kế hoạch (Plan)**: [2026-11-19-1632-hybrid-hook-smart-hardening.md](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/plan/2026-11-19-1632-hybrid-hook-smart-hardening.md)
- **Kiểm định chất lượng (QC Ultra)**: [2026-11-19-1632-hybrid-hook-smart-hardening.md](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/qc/2026-11-19-1632-hybrid-hook-smart-hardening.md)
- **Báo cáo trực quan (Archify HTML cục bộ)**: [2026-11-19-1632-hybrid-hook-smart-hardening.html](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/reports/2026-11-19-1632-hybrid-hook-smart-hardening.html)
- **Liên kết Tailscale Serve**: https://unity-pc-rtx3060.tail99896.ts.net/vlog/tdq-workflow-agy/reports/2026-11-19-1632-hybrid-hook-smart-hardening.html

---

## 1. Trước request: Trạng thái & Vấn đề tồn tại

- **Bỏ sót vòng đời Antigravity 2.0**: Binary Rust `tdq-dispatch` ở `v0.101.0` mới dừng ở bản nguyên mẫu `allow()` cho `PreInvocation` và `PostInvocation`, đồng thời chưa khớp đủ khóa schema AGY 2.0 (`injectSteps`, `reason`, `toolCall`, `workspacePaths` dạng `file:///`).
- **Lệch sổ runtime & rò rỉ `22` mã cổng**: Tầng Rust đọc/ghi `.tdq-runtime` ở gốc repo thay vì `docs/tdq/.tdq-runtime/` của Python; một số quy tắc R1–R3 làm mềm quá tay (`TICK` không chặn khi 0 `[~]`, `LOG` mềm, `UNFINISHED` xả sau 1 lần `continuationActive`, `qc-tester` thiếu chặn ghi qua shell), làm suy giảm kỷ luật quy trình TDQ.
- **Lỗi đóng gói đa nền tảng**: `tools/build_agy_plugin.py` có nguy cơ ghi đè binary Windows PE (`.exe`) lên binary Linux/macOS nếu thiếu guard magic bytes; phía Cold-path Python dùng cú pháp type annotation `X | Y` (`Python 3.10+`) khiến máy macOS chạy `/usr/bin/python3` (`3.9.6`) lỗi `TypeError` khi Rust ủy quyền `dispatch.py`.
- **Lệch ngân sách release & manifest**: Thư mục nguồn `hooks/rust/**` chưa được loại khỏi nhánh portable Claude/Codex (`178 > 161`), và `.claude-plugin/plugin.json` / `.codex-plugin/plugin.json` còn ghi `"0.100.0"` lệch với `CHANGELOG.md` (`0.101.0`).

---

## 2. Sau request: Kiến trúc Hybrid 2 tầng + Smart Hardening

- **Chặng 1 — Giao thức AGY 2.0, 1 sổ thống nhất & Khóa an toàn (`hooks/rust/tdq-dispatch/src/`)**:
  - `protocol.rs`: Chuẩn hóa trọn bộ schema AGY 2.0 cho 6 sự kiện (`SessionStart`, `PreInvocation`, `PreToolUse`, `PostToolUse`, `PostInvocation`, `Stop`), nhúng `unwrap_mcp_tool_call` và `gate_guidance.json` đủ `22/22` mã TDQ.
  - `storage.rs`, `lock.rs`, `main.rs`: Thống nhất đường dẫn duy nhất `docs/tdq/.tdq-runtime/`, dùng `std::fs::File::try_lock()` trong `lock.rs` chống lỗi NTFS `ERROR_LOCK_VIOLATION`, phân giải `PLUGIN_ROOT` ngoài repo và giải mã URI `file:///` trong `workspacePaths`.
- **Chặng 2 — Bộ định tuyến Hybrid 2 tầng, Smart Hardening 6 quy tắc & Python 3.9**:
  - **Tuyến Hot-path thuần Rust (~91% lưu lượng)**: Xử lý trực tiếp trong `tdq-dispatch` (< 26 ms qua `cmd /c`) các thao tác `allow`/`deny`/`overwrite`, bảo vệ `TDQ:STATE`, `TDQ:GIT`, `TDQ:VUNG` (`curl|bash`), `TDQ:READONLY` (kể cả subagent `qc-tester` trong `hooks/scripts/bash_gate.py`), `TDQ:ZERO-POPUP`, `PostToolUse` (`docs/tdq/.tdq-read.jsonl`, `search_grace`), `PostInvocation` flush, và `PreInvocation` lặp giữa lượt.
  - **Tuyến Cold-path (~9% lưu lượng)**: Chuyển tiếp sạch qua `dispatch.py` cho `SessionStart`, `PreInvocation` lượt mới, `edit_file`, `run_command` đầu chuỗi hoặc lệnh phức tạp, và `Stop` khi có request đang mở.
  - **Smart Hardening 6 quy tắc (`tools/patches/agy_hooks.py` & `hooks/scripts/bash_gate.py`)**: Chặn cứng `TDQ:TICK` ở `0 [~]` / ngưỡng streak `8` (nhắc từ `4`), chặn cứng `TDQ:LOG` ở `Stop` khi sửa mã thật chưa cập nhật working log, `TDQ:UNFINISHED` chịu `2` vòng `continuationActive` trước khi hạ mức + `turn_closed`, giữ `TDQ:SEARCH` + `TDQ:GON` 1 dòng theo pha và chặn ghi `qc-tester`.
  - **Tương thích Python 3.9 macOS**: Bổ sung `from __future__ import annotations` tại `scripts/tdq_state.py`, `scripts/search_rules.py`, `scripts/tdq_ccr.py`, `tools/patches/agy_dispatch.py`.
- **Chặng 3 — Guard 3 OS, Golden Parity & Đồng bộ Toàn Repo**:
  - `tools/build_agy_plugin.py`: Xác thực magic bytes riêng cho PE (`4d5a9000`), Linux ELF (`7f454c46`), Mach-O ARM64 (`cffaedfe`), tuyệt đối không chép chéo OS và không để `hooks/rust/tdq-dispatch/prebuilt/`.
  - `scripts/build_portable.py` & Manifests: Loại `hooks/rust/**` khỏi nhánh release portable (`la_duong_dan_release`) và đồng bộ `"version": "0.101.0"` ở `.claude-plugin/plugin.json` và `.codex-plugin/plugin.json`.
  - Bộ test mới/cập nhật: `tests/test_rust_dispatch_parity.py` (`46` ca Golden Parity `22/22` mã × `6` sự kiện), `tests/test_rust_latency_benchmark.py`, `tests/test_agy_plugin_validate.py`, `tests/test_hook_dispatch_r1_r3.py`, cùng 5 file test đồng bộ (`test_rust_lock_safety.py`, `test_hooks_dual_protocol.py`, `test_command_gate.py`, `test_remote_linux_simulation.py`, `test_remote_mac_simulation.py`).

---

## 3. Đã test những gì?

1. **Crate Rust (`cargo fmt`, `clippy`, `test`)**: Kiểm tra định dạng, cảnh báo `clippy -D warnings`, `protocol::` (`Q1`) và toàn bộ 27 unit test Rust trên Windows, Linux và macOS.
2. **Biên dịch native 3 hệ điều hành & kiểm định plugin nghiêm ngặt (`Q6`, `Q7`)**: Build và kiểm tra magic bytes của `tdq-dispatch.exe` (Windows x64), `tdq-dispatch-linux-x86_64` (Ubuntu `ubuntu-100-95` ELF x64), `tdq-dispatch-darwin-arm64` (MacBook Air `mbair` Mach-O ARM64); xác thực `agy.EXE plugin validate plugins/tdq-workflow-agy --strict --json`; kiểm tra bất biến local plugin (`2b`).
3. **Golden Parity, Smart Hardening R1–R3 & Python 3.9 (`Q2`, `Q3`, `Q4`, `Q8`)**: Chạy `test_rust_dispatch_parity.py`, `test_hook_dispatch_r1_r3.py`, `test_agy_hooks.py`, 5 test di sản đồng bộ và smoke test vòng đời 6 sự kiện qua SSH thật lên `ubuntu-100-95` & `mbair` (`cross_os_smoke.py` `8` kịch bản + `test_remote_{linux,mac}_simulation.py`).
4. **Đo kiểm hiệu năng solo `N=30` (`Q5`)**: Chạy độc lập `tests/test_rust_latency_benchmark.py -s -q` tách riêng Direct, `cmd /c`, Hot-path, Cold-path và Weighted Hybrid (`0.91*hot + 0.085*cold_mid + 0.005*cold_ss`).
5. **Kiểm thử toàn repo lượt cuối (`QC-F1`) & Kiểm toán độc lập (`Q8`)**: Chạy `py -3 -X utf8 scripts/tdq_test.py tron-bo --workers 1 --fresh --reuse off` trên toàn bộ `215` module, kiểm tra `tdq_test.py so`, `doc_lint.py --pair`, `i18n_check.py`, `kiem_no_marker.py`, và gọi subagent `tdq-qc-tester` đọc-chỉ kiểm chứng lại độc lập.

---

## 4. Kết quả test ra được cái gì?

### 4.1. Tổng hợp kiểm thử chức năng & toàn repo

| Hạng mục | Lệnh / Công cụ | Kết quả thực tế (mới nhất) | Trạng thái |
|---|---|---|---|
| **Trọn bộ repo (`QC-F1` lượt 2)** | `py -3 -X utf8 scripts/tdq_test.py tron-bo --workers 1 --fresh --reuse off` (`215` module) | **`4,458` ca → `4,422 passed`, `36 skipped`, `2,721 subtests passed`, `0 failed`** (`1303.23s`, wall `1314.88s`, `exit 0`); `tdq_test.py so`: `tron_bo=2/3`, `bo_sot=0` *(ghi chú: trong `36 skipped` có `test_remote_mac_simulation.py` skip `5.038s` do máy `mbair` ngủ từ ~`20:25`, sau khi đã pass trực tiếp `8/8` lúc `19:43` & `20:15` trên cùng bản build cuối; `ubuntu-100-95` pass trực tiếp)* | **PASS** |
| **Crate Rust** | `cargo fmt --check`, `clippy -- -D warnings`, `cargo test` | `23 lib + 4 bin = 27 passed` (`protocol::` `3 passed`), `0` cảnh báo `clippy`, `0` lỗi `fmt` (trên Win/Linux/macOS đều `27 passed`) | **PASS** |
| **Parity `22/22` & R1–R3** | `py -3 -m pytest tests/test_rust_dispatch_parity.py tests/test_hook_dispatch_r1_r3.py -q` | **`57 passed in 88.85s`** (`46` ca Parity `22` mã × `6` sự kiện + `11` ca R1–R3, `Q2/Q8` `runtime\|plugin_root\|smoke` `3 passed`) | **PASS** |
| **Tương thích Python 3.9 & Plugin** | `tests/test_state.py tests/test_search_rules.py tests/test_tdq_ccr.py tests/test_agy_plugin_validate.py` + `agy.EXE plugin validate --strict --json` | **`172 passed, 8 subtests passed in 33.29s`**; `agy validate`: **`findings: []`** (`6` agents, `6` hooks, `3` mcpServers, `10` rules, `12` skills); `magic`: `2 passed` | **PASS** |
| **Release budget & Đồng bộ test di sản** | `test_build_portable.py`, `test_docs_consistency.py`, `QC1.2`/`QC2.2` suites | `test_build_portable.py` **`38 passed`**; `test_docs_consistency.py` **`9 passed`**; `test_ma_hoa_subprocess.py` + `test_tdq_test.py` + `remote` **`104 passed`**; `QC1.2` **`15 passed, 0 skipped`** (`20:15`) | **PASS** |
| **Live Smoke Linux & macOS** | `cross_os_smoke.py` trên `ubuntu-100-95` & `mbair` (trên build cuối) | `[ubuntu-100-95]` **`ALL 8/8 smoke cases PASS`**; `[mbair]` **`ALL 8/8 smoke cases PASS`** (`CROSS-OS SMOKE VERIFIED`) | **PASS** |
| **Rà soát tài liệu, `i18n` & Biến biên** | `doc_lint.py --pair`, `i18n_check.py` (12 file sửa), `kiem_no_marker.py`, `scripts->hooks` | `doc_lint` exit `0`; `i18n_check` **`0 Vietnamese line(s)`**; `kiem_no_marker` **`6 marker(s), 0 missing`**; `scripts->hooks`: `[]`; `state.json` writers: `0` | **PASS** |
| **Kiểm toán độc lập (`tdq-qc-tester`)** | Subagent `d144bf50-2657-4e6b-8b8c-ded6b7aa5e28` | **`VERDICT: PASS everything`** cho đủ `Q1`–`Q8` (gồm `10/10` probe biên/ISO/`TDQ_LOG=0`, `0` stub) | **PASS** |

### 4.2. Số đo hiệu năng Solo (`Q5`, `N=30` lượt) & Nhị phân 3 hệ điều hành

| Tuyến đo / Thành phần | Kết quả thực tế | Ngưỡng mục tiêu | Đánh giá |
|---|---|---|---|
| **Hot Combined (Direct)** | Median **`17.01 ms`** (`p95 19.73 ms`) | `<= 25.00 ms` | **Đạt** |
| **Hot Combined (`cmd /c`)** | Median **`25.85 ms`** (`p95 30.50 ms`) · Vỏ `cmd /c`: `17.86 ms` · Lõi Rust ròng: **`7.98 ms`** | `<= 32.00 ms` | **Đạt** |
| **Cold Mid-Turn (`cmd /c`) / SessionStart (`cmd /c`)** | `106.40 ms` / `218.09 ms` (Python chuẩn: `200.64 ms`) | Ủy quyền Cold-path ~9% | **Đạt** |
| **Weighted Hybrid (`0.91*hot + 0.085*mid + 0.005*ss`)** | **`33.65 ms`** (**nhanh gấp `7.8x`** so với Python `SessionStart`) | `<= 40.00 ms` | **Đạt** |
| **Binary Windows PE (`tdq-dispatch.exe`)** | `1,914,368` bytes · magic `4d5a9000` (`MZ`) | Đúng chuẩn PE64 | **Đạt** |
| **Binary Linux ELF (`tdq-dispatch-linux-x86_64`)** | `2,268,768` bytes · magic `7f454c46` (`\x7fELF`) | Đúng chuẩn ELF x86-64 | **Đạt** |
| **Binary macOS Mach-O (`tdq-dispatch-darwin-arm64`)** | `1,812,432` bytes · magic `cffaedfe` (`Mach-O arm64`) | Đúng chuẩn Mach-O ARM64 | **Đạt** |
| **Local plugin (`2b`) & `prebuilt/`** | SHA-256 `2D84E63E65A5F670CC0A61A41A8ACD5A5D36086436EAE25F18A690037B7DC617` không đổi; `prebuilt/` vắng mặt (`False`) | Nguyên vẹn tuyệt đối | **Đạt** |

- **Thời gian thực thi theo `tdq_timing.py show`** (tính hết phase `qc`): tổng wall `3h 53min` (`analyze` `8 min` · `spec` `12 min` · `plan` `14 min` · `implement` `2h 02min` · `qc` `1h 16min`).
<!-- tdq-archify-binding:start -->
<!-- manifest: 2026-11-19-1632-hybrid-hook-smart-hardening.manifest.json -->
<!-- manifest_digest: d5c2b9b34acb865d27ce251a406050ac5c2318fd10b57e012afbef737e854789 -->
<!-- tdq-archify-binding:end -->