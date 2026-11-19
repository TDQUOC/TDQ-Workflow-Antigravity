# Báo cáo Kiểm định Chất lượng (QC Ultra) — Hybrid 2 tầng Hook + Smart Hardening

- **Mã yêu cầu (`Request Slug`)**: `2026-11-19-1632-hybrid-hook-smart-hardening`
- **Nhánh phát triển**: `feature/hybrid-hook-smart-hardening` (nền `dev`)
- **Mức QC**: `ultra` · **Làn**: `full`
- **Đặc tả**: [2026-11-19-1632-hybrid-hook-smart-hardening.md](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/spec/2026-11-19-1632-hybrid-hook-smart-hardening.md)
- **Kế hoạch**: [2026-11-19-1632-hybrid-hook-smart-hardening.md](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/plan/2026-11-19-1632-hybrid-hook-smart-hardening.md)

---

## 1. Tổng hợp các vòng sửa lỗi QC (`QC vòng 1` & `QC vòng 2`)

| Vòng / Tác vụ | Phát hiện thực tế | Khắc phục đã áp dụng | Kiểm chứng sau sửa |
|---|---|---|---|
| **QC1.1** | Live smoke trên `mbair` (`Python 3.9.6`) văng `TypeError` ở `scripts/tdq_state.py:669` (`str \| None`) khi nhánh Cold-path gọi `dispatch.py`. | Thêm `from __future__ import annotations` tại `scripts/tdq_state.py`, `scripts/search_rules.py`, `scripts/tdq_ccr.py`, `tools/patches/agy_dispatch.py` và đóng gói lại `plugins/tdq-workflow-agy/` qua `tools/build_agy_plugin.py`. | `172 passed, 8 subtests` (`test_state.py`, `test_search_rules.py`, `test_tdq_ccr.py`, `test_agy_plugin_validate.py`); `cross_os_smoke.py`: `8/8 PASS` cả `ubuntu-100-95` & `mbair`; `agy validate` `findings: []`. |
| **QC1.2** | 5 tệp test di sản còn kỳ vọng đường dẫn `.tdq-runtime` cũ, cơ chế nới lỏng R1–R3 cũ hoặc lệnh `dispatch.py`. | Đồng bộ `tests/test_rust_lock_safety.py`, `tests/test_hooks_dual_protocol.py`, `tests/test_command_gate.py`, `tests/test_remote_linux_simulation.py`, `tests/test_remote_mac_simulation.py` theo chuẩn Q2 + Smart Hardening + AGY 2.0. | `15 passed` (`0 failed, 0 skipped` lúc `20:15` với `ubuntu-100-95` & `mbair` sống), `ruff F,B` pass, `i18n_check.py` `0` dòng Việt, `kiem_no_marker.py` `6 marker, 0 thiếu`. |
| **QC1.3** | `.claude-plugin/plugin.json` và `.codex-plugin/plugin.json` sót bản `0.100.0` từ commit `72f1e2e9` khiến `test_docs_consistency.py` báo lệch `0.101.0` trong `CHANGELOG.md`. | Đồng bộ `"version": "0.101.0"` ở `.claude-plugin/plugin.json` và `.codex-plugin/plugin.json`. | `py -3 -m pytest tests/test_docs_consistency.py -q` → `9 passed, 19 subtests passed`. |
| **QC2.1** | `tron-bo` lượt 1 phát hiện `test_build_portable.py` fail `178 <= 161` do `hooks/rust/tdq-dispatch/**` (17 file) chưa bị loại khỏi `la_duong_dan_release`. | Bổ sung loại trừ `parts[0] == "hooks" and len(parts) > 2 and parts[1] == "rust"` ở `scripts/build_portable.py`. | `ruff F,B` pass; `tests/test_build_portable.py` → `38 passed, 4 subtests passed in 8.10s`. |
| **QC2.2** | `tron-bo` lượt 1 phát hiện `test_ma_hoa_subprocess.py` thiếu `encoding=` và `test_tdq_test.py` (`ban_kinh` `ask_gate` 11 > 10) do `rglob` trên `"hooks/scripts"` ở 2 file remote simulation. | Thêm `encoding="utf-8", errors="replace"` và quét `PLUGIN_DIR.rglob("*")` rồi lọc prefix trong `test_remote_{linux,mac}_simulation.py`. | `ruff F,B` pass; `i18n_check.py` `0` dòng Việt; `tests/test_ma_hoa_subprocess.py tests/test_tdq_test.py tests/test_remote_linux_simulation.py tests/test_remote_mac_simulation.py` → `104 passed, 9 subtests passed in 91.24s`. |

---

## 2. Kết quả `QC-F1`..`QC-F4` (Chạy trên bộ mã cuối)

- **`QC-F1` (`tdq_test.py tron-bo` lượt 2 / ngân sách `3`)**:
  - Lệnh: `py -3 -X utf8 scripts/tdq_test.py tron-bo --workers 1 --fresh --reuse off`
  - Kết quả (`exit 0`, `status=PASS`, `215` module): **`4,458` ca thu thập → `4,422 passed`, `36 skipped`, `2,721 subtests passed`, `0 failed` trong `1303.23s`** (wall `1314.88s`).
  - `tdq_test.py so`: `full-suite runs: 2 of budget 3`, `radius misses: 0`.
  - Ghi chú trung thực về `36 skipped`: gồm `35` ca skip điều kiện nền tảng có sẵn và `1` ca `tests/test_remote_mac_simulation.py::test_mac_simulation_all_events` skip sau `5.038s` (`ConnectTimeout=5`) do máy `mbair` (`100.78.55.36`) ngủ từ ~`20:25`; trước đó ở lúc `19:43` (`cross_os_smoke.py` `8/8 PASS`) và `20:15` (`task-4647`, `104 passed, 0 skipped`) máy `mbair` đã kiểm thử trực tiếp và PASS trên cùng bộ nhị phân/mã Python 3.9 cuối cùng (`ubuntu-100-95` PASS trực tiếp xuyên suốt).
- **`QC-F2` (Lệch spec / sửa từ QC)**: Đã rà soát và khóa sạch ở `QC vòng 1` & `QC vòng 2`; `tdq_archify.py verify` xác nhận spec `current`.
- **`QC-F3` (Kiểm biên kiến trúc & sạch mã)**:
  - AST `scripts/` import `hooks/`: `[]` (`0` vi phạm).
  - Ghi trực tiếp `docs/tdq/state.json` ngoài `tdq_state.py`: `0` điểm ghi ở mã sản phẩm (`storage.rs:624` và `pre_tool_use.rs:603` là unit test `#[cfg(test)]`).
  - `cargo fmt --check`: thoát `0`; `cargo clippy --bins --tests -- -D warnings`: `No issues found`.
  - `scripts/kiem_no_marker.py`: `6 marker(s), 0 missing an upgrade path`.
- **`QC-F4` (Giữ nguyên local plugin rule `2b`)**:
  - SHA-256 `C:\Users\admin\.gemini\config\plugins\tdq-workflow-agy\manifest.json`: `2D84E63E65A5F670CC0A61A41A8ACD5A5D36086436EAE25F18A690037B7DC617` (không đổi).
  - Thư mục `hooks/rust/tdq-dispatch/prebuilt/` xác nhận đã dọn (`exists=False`).

---

## 3. Bảng kiểm chứng Definition of Done (`Q1`–`Q8`)

| Tiêu chí | Lệnh kiểm chứng | Kết quả thực tế | Trạng thái |
|---|---|---|---|
| **Q1** Schema AGY 2.0 & 6 sự kiện | `cargo test --manifest-path hooks/rust/tdq-dispatch/Cargo.toml protocol::` & toàn crate | `protocol::` `3 passed` (`0.00s`); toàn crate `23 lib + 4 bin = 27 passed`; `clippy` 0 cảnh báo. | **PASS** |
| **Q2** Thống nhất `docs/tdq/.tdq-runtime/` & `PLUGIN_ROOT` ngoài repo | `py -3 -m pytest tests/test_rust_dispatch_parity.py -q -k "runtime or plugin_root"` | `2 passed` (trong cụm `-k "runtime or plugin_root or smoke"`: `3 passed`). | **PASS** |
| **Q3** Golden Parity 22/22 mã × 6 sự kiện | `py -3 -m pytest tests/test_rust_dispatch_parity.py tests/test_hook_dispatch_r1_r3.py -q` | `57 passed in 88.85s` (`46` ca parity + `11` ca R1–R3). | **PASS** |
| **Q4** Đủ 6 quy tắc Smart Hardening, UTF-8 & Python 3.9 | Kết hợp `Q3` + `tests/test_agy_hooks.py` + `tests/test_{bash,edit,stop,search}_gate.py` | Toàn bộ xanh (`35` agy_hooks, `229` gate gốc, `15` test di sản đồng bộ). | **PASS** |
| **Q5** Hiệu năng Hybrid (`Hot <= 25 / 32 ms`, `Weighted <= 40 ms`) | `py -3 -m pytest tests/test_rust_latency_benchmark.py -s -q` (chạy solo `N=30`) | `Hot Combined Direct = 17.01 ms`, `cmd /c = 25.85 ms`, `Weighted = 33.65 ms` (chi tiết mục 4). | **PASS** |
| **Q6** Magic Bytes 3 OS & test thật Win/Linux/macOS | `py -3 -m pytest tests/test_agy_plugin_validate.py -q -k magic` + smoke SSH | `2 passed`; Windows `4d5a9000` (`1,914,368` B), Linux `7f454c46` (`2,268,768` B), macOS `cffaedfe` (`1,812,432` B); Linux & macOS đều đạt `8/8 PASS` trên bản build cuối. | **PASS** |
| **Q7** Hồi quy toàn repo, `agy plugin validate --strict`, `i18n` & `doc_lint` | `tdq_test.py tron-bo` + `agy.EXE plugin validate plugins/tdq-workflow-agy --strict --json` + `i18n_check.py` + `doc_lint.py` | `4422 passed, 36 skipped, 0 failed`; `findings: []` (`6` agents, `6` hooks, `3` mcpServers, `10` rules, `12` skills); `0` dòng Việt trong 12 file `.py` chạm; `doc_lint` exit 0. | **PASS** |
| **Q8** Smoke test & kiểm định độc lập `tdq-qc-tester` | `-k smoke` (`1 passed`) + subagent `tdq-qc-tester` (`d144bf50-2657-4e6b-8b8c-ded6b7aa5e28`) | `VERDICT: PASS everything` trên đủ `Q1`–`Q8` (gồm `10/10` probe biên/ISO/`TDQ_LOG=0`, `0` stub). | **PASS** |

---

## 4. Số đo hiệu năng thực nghiệm (`Q5` Solo Benchmark, `N=30` lượt + 3 warmup)

| Tuyến & Chế độ | Trung vị (`ms`) | P95 (`ms`) | Ngưỡng Spec | Đánh giá |
|---|---|---|---|---|
| Vỏ `cmd /c` rỗng (`Shell Wrapper Only`) | `17.86` | `20.42` | — | Mức nền OS |
| Hot `PostInvocation` (Direct) | `16.57` | `19.43` | `<= 25.00 ms` | **Đạt** |
| Hot `PreToolUse` (Direct) | `17.35` | `19.90` | `<= 25.00 ms` | **Đạt** |
| **Hot Combined (Direct)** | **`17.01`** | `19.73` | **`<= 25.00 ms`** | **Đạt** |
| Hot `PostInvocation` (`cmd /c`) | `25.45` | `29.42` | `<= 32.00 ms` | **Đạt** |
| Hot `PreToolUse` (`cmd /c`) | `26.09` | `30.50` | `<= 32.00 ms` | **Đạt** |
| **Hot Combined (`cmd /c`)** | **`25.85`** | `30.50` | **`<= 32.00 ms`** | **Đạt** |
| Lõi Rust ròng (`Hot Shell - Shell Wrapper`) | `7.98` | — | `< 10 ms` | **Đạt** |
| Cold Mid-Turn `grep` (`cmd /c`) | `106.40` | `115.68` | — | Ủy quyền Python |
| Cold `SessionStart` (`cmd /c`) | `218.09` | `227.74` | — | Ủy quyền Python |
| Python `SessionStart` chuẩn (`cmd /c`) | `200.64` | `217.52` | — | Đối chứng |
| **Weighted Hybrid (`0.91*hot + 0.085*mid + 0.005*ss`)** | **`33.65`** | — | **`<= 40.00 ms`** | **Đạt (`7.8x` nhanh hơn Python `SessionStart`)** |

---

## 5. Phán quyết của Subagent Độc lập (`tdq-qc-tester`)

- **Phiên kiểm định**: `d144bf50-2657-4e6b-8b8c-ded6b7aa5e28` — **`VERDICT: PASS everything`**.
- **Ghi chú nhẹ (minor, không chặn)**: Một số hàm Rust có sẵn từ trước `T5.1` (`hooks/rust/tdq-dispatch/src/events/pre_tool_use.rs:307` 52–86 dòng do xuống dòng `rustfmt`, và `main.rs:main` 65 dòng) vượt nhẹ 50 dòng nhưng sạch `.unwrap()` và đã đạt `cargo clippy -D warnings` = `0`.
