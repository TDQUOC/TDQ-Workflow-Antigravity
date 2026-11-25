# BRIEF — Triển khai Pha P0: Lõi An toàn Runtime, Khóa NTFS/Rust & Cửa ngõ MCP

Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

## Nguyên văn

> 1a vvaf mở request tiến hành develop theo dev plan

- **Yêu cầu gốc & bản thiết kế nền vừa merge vào `dev` (`bc5e9b19`):** [master-roadmap.md](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/artifacts/2026-11-25-1633-paperclip-3phase-dev-plan/master-roadmap.md) và [dev-plan-p0.md](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/artifacts/2026-11-25-1633-paperclip-3phase-dev-plan/dev-plan-p0.md).
- **Mục tiêu ban đầu:** Triển khai trọn vẹn pha **`P0`** thành **`1` request `feature` thống nhất** (theo lựa chọn `1c` đã chốt trong roadmap), gồm `4` wave nội bộ không đụng file nóng (`P0-W1`–`P0-W4`):
  - `P0-W1`: `scripts/tdq_lease.py`, `scripts/defaults/mcp-policy.default.json`, `scripts/tdq_config.py`, `hooks/rust/tdq-dispatch/src/lock.rs`, `tests/test_tdq_lease.py`.
  - `P0-W2`: `scripts/tdq_state.py` (`schema_version=6` additive + sidecar lock `save()`), `scripts/tdq_team.py` (hàng đợi 3 tầng + aging `OLDEST_DISPATCH_SHARE=4` + `blocked_by` + `idempotency_key`), `scripts/tdq_timing.py` (ngưỡng ngân sách `80%` / `hard_stop`), `scripts/mcp_policy.py` (`evaluate_tool_call` cân bằng `3a`), kèm unit test `tests/test_tdq_queue.py`, `tests/test_tdq_timing_budget.py`, `tests/test_mcp_policy.py`.
  - `P0-W3`: Nối Python hooks (`hooks/scripts/lsp_gate.py`, `hooks/scripts/edit_gate.py`, `hooks/scripts/bash_gate.py` — tránh `agy_pretooluse_gate.py` bị `common_utils.py:26` loại khỏi bundle AGY), mở matcher non-LSP MCP tại `hooks/hooks.json:76` và `tools/patches/agy_manifests.py:72`, đồng bộ Rust `hooks/rust/tdq-dispatch/src/events/pre_tool_use.rs` (tái dụng `READONLY` giữ đủ `23` AGY code), và cập nhật `APPROVED_RUNTIME_MODULES` trong `tests/test_build_portable.py`.
  - `P0-W4`: Biên dịch `tdq-dispatch.exe`, chạy `tools/build_agy_plugin.py`, `tests/test_rust_dispatch_parity.py`, `tools/run_full_verification.py`, `scripts/tdq_test.py tron-bo` và dry-run `scripts/build_portable.py --sinh-main --dry-run`.
- **Trình tự liên pha:** Sau khi `P0` hoàn tất và merge về `dev`, mới mở tiếp các request riêng cho `P1` (`Domain Pack` + `KhoBM25`) và `P2` (`Paperclip CLI Bridge` tắt mặc định).
- **Điểm cần làm rõ khi vào `analyze`:** Chốt lại nếu có điều chỉnh nào cho ngưỡng mặc định `P0` (`docs/tdq/config.json` ghi đè `tdq-config.json`), xác nhận cài/bù bậc LSP `python:.` và `rust:hooks/rust/tdq-dispatch` (do đây là request `feature` sửa code thật cả Python lẫn Rust), và rà soát phạm vi parity trên Windows Antigravity.
- **Ghi chú tầng tìm kiếm (Step 1b — `tdq_lsp.py check` lúc `2026-11-25T18:34`):** `6/8` bậc ĐẠT (`Bậc 1` `0.19.2`, `Bậc 2` `4` server, `Bậc 3` `HTML/JS/Python/Rust`, `Bậc 4` ĐẠT, `Bậc 5` ĐẠT, `Bậc 7` đồ thị Graphify mới hơn mọi mã nguồn), smoke `3/3` tầng (`grep`, `LSP`, `graphify`) đều ĐẠT; `Bậc 6` thiếu `jsconfig.json`/`Cargo.toml` ở gốc repo (`Cargo.toml` nằm tại `hooks/rust/tdq-dispatch/Cargo.toml`), `Bậc 8` `3` module `HET_HAN` (`javascript:.`, `python:.`, `rust:hooks/rust/tdq-dispatch`). Không tự chạy `tdq_setup.py`; sẽ xử lý hiệu ứng LSP `Bậc 8` sau khi mở request.

## Hiểu & kiến thức

### Năng lực dùng được

Phân vân → DÙNG. Kiểm kê ngày 2026-11-25: 42 skill trên đĩa (23 khớp lọc, 19 ẩn), cộng skill built-in trong context. Không xoá bảng này kể cả khi không có dòng DÙNG nào.

| Skill | Nguồn | Phán quyết | Dùng ở đâu / Lý do loại |
|---|---|---|---|
| `tdq-conventions`, `tdq-intake`, `tdq-spec`, `tdq-plan`, `tdq-build`, `tdq-setup`, `tdq-lean`, `tdq-status`, `tdq-check-status`, `tdq-checkportable` | `plugin:tdq-workflow` / `plugin:tdq-workflow-agy` | NỀN | Bộ khung điều phối cho request `feature` `P0` trên nhánh `feat/p0-runtime-safety-rust-parity` |
| Đã xét 19 skill đĩa khác + skill built-in (`frontend-design`, `illustrator-preflight`, ...) | user/plugin/built-in | KHÔNG | khác lĩnh vực |

### Hồ sơ mã nguồn & Bảng đối chiếu vùng chạm (`B1 Triangulation`)

- **Kiểm tầng tìm kiếm:** Rust LSP (`rust-analyzer` tại `hooks/rust/tdq-dispatch`) chạy được (`find_references` trên `handle_mcp_tool` trả `symbols=2` — định nghĩa `pre_tool_use.rs:723` + 1 điểm gọi). Do `python:.` chưa cấu hình Python LSP server trong phiên MCP và `collect_git_policy_violations` (`command_parser.rs:417`) chỉ có tham chiếu nội tệp (`3/3`), request mở qua `--bo-qua-lsp` kèm đối chiếu `Graphify`, `rg` và `AST`.
- **Phát hiện điểm neo đóng gói quan trọng (`tools/patches/agy_hooks.py`):**
  - `_patch_lsp_gate` (`2202-2265`) dùng `replace_exact` lên hàm `_phan_xu_lenh()` của `lsp_gate.py`, KHÔNG đụng hàm `main()` — nên gắn `mcp_policy.evaluate_tool_call()` vào nhánh `op is None` trong `main()` để `tools/build_agy_plugin.py` giữ nguyên `100%` độ khớp.
  - `_patch_bash_gate` (`1923-2010`) và `_patch_edit_gate` (`2045-2135`) dùng `replace_exact` lên phần mở đầu `main()`, dòng import `_common`, và chuỗi `block` cụ thể — nên phần `Circuit Breaker` / `Budget` phải móc gọn vào helper tách riêng sau đoạn neo thay vì sửa chữ ký import/dòng đầu `main()`.
- **Số đo test nền trước khi sửa (`dev` nguyên bản):**
  - Python baseline (`PYTHONPATH=tests`): `tests/test_state.py`, `tests/test_ntfs_concurrency.py`, `tests/test_build_portable.py`, `tests/test_rust_dispatch_parity.py` → **`106` tests PASS (`147.923s`)**.
  - Rust baseline (`cargo test --manifest-path hooks/rust/tdq-dispatch/Cargo.toml`): **`39` tests PASS** (`35` lib + `4` bin, `0` fail).

| Vùng mã nguồn chạm (`P0-W1`–`W4`) | Điểm neo đã đọc trực tiếp | Tác động & Ràng buộc |
|---|---|---|
| `scripts/tdq_lease.py` (mới), `hooks/rust/tdq-dispatch/src/lock.rs:1-95` | `SidecarLockGuard`, `acquire_sidecar_lock` (`Keep anchor .lock`) | Python sidecar lock KHÔNG unlink `.lock` để khớp `lock.rs` tránh race trên NTFS |
| `scripts/tdq_state.py:560-645` | `save()`, `_atomic_write()` (`"overwriting anyway"`) | Bọc `acquire_sidecar_lock` trước `os.replace`, giữ nguyên `schema_version=6` |
| `scripts/tdq_config.py:30-100` | `DEFAULT_CONFIG` (`qc`, `agents`) | Thêm khối `p0` mặc định cân bằng, ghi đè qua `docs/tdq/config.json` |
| `hooks/scripts/{lsp_gate,edit_gate,bash_gate}.py`, `hooks/hooks.json:76`, `tools/patches/agy_manifests.py:72` | `_patch_{lsp,edit,bash}_gate`, `EXCLUDED_SCRIPTS` loại `agy_pretooluse_gate.py` | Gắn rào Python vào `lsp_gate`/`edit_gate`/`bash_gate` và mở matcher non-LSP MCP |
| `hooks/rust/tdq-dispatch/src/events/pre_tool_use.rs:720-815` | `handle_mcp_tool()`, `handle_pre_tool_use()` | Tái dụng mã `READONLY` giữ tròn `23` mã `all_agy_codes`, fast-path `< 0.5ms` cho tool đọc |

### Kiến thức đã chốt

- **Đóng gói `P0` thống nhất (`1c` + `dev-plan-p0.md`):** Toàn bộ pha `P0` chạy trong `1` request `feature` (`feat/p0-runtime-safety-rust-parity`, `work_kind=build`), tách `4` wave không trùng file nóng (`P0-W1`–`P0-W4`), giữ `schema_version=6` ở `state.json`, mẫu chuẩn đặt trong `scripts/defaults/`, override dự án ở `docs/tdq/config.json`, giữ nguyên `_patch_{lsp,bash,edit}_gate` trong `tools/patches/agy_hooks.py`.
- **Chốt `1a` (`MCP Quarantine` cân bằng + CLI mở khóa):** Khi xuất hiện tool MCP `write`/`destructive` mới hoặc bị đổi SHA-256 mô tả, cả Python (`lsp_gate.py:main` nhánh `op is None`) lẫn Rust (`handle_mcp_tool`) block đồng bộ bằng mã sẵn có `[TDQ:READONLY]` (giữ tròn `23` mã `all_agy_codes`) kèm lệnh `py -3 scripts/mcp_policy.py approve <server> <tool>` lưu SHA-256 vào `docs/tdq/mcp-policy.json`; tool đọc và `tdq-lsp` vẫn đi qua ở fast-path.
- **Chốt `2a` (`Circuit Breaker` & `Budget hard_stop` đa tầng):** Lưu bộ đếm `p0_runtime` (tương thích ngược `schema_version=6`) trong `docs/tdq/state.json` và cưỡng chế đồng bộ tại `edit_gate.py`, `bash_gate.py`, `lsp_gate.py` (tránh `agy_pretooluse_gate.py` bị `common_utils.py:26` loại khỏi bundle AGY) cùng `pre_tool_use.rs`, đi kèm CLI reset nhanh và kill-switch trong `docs/tdq/config.json`.
- **Chốt `3a` (Mức QC `ultra`):** Áp dụng đầy đủ DoD + unit test `Red -> Green` + `test_ntfs_concurrency` + `test_build_portable` + `test_rust_dispatch_parity` + `run_full_verification.py` + `tdq-qc-tester` độc lập kiểm chứng cuối (`muc_qc=ultra`).

### Lộ trình

| Bước/phase | Chạy? | Vì sao |
|---|---|---|
| Research web | BỎ | Toàn bộ mã nguồn TDQ-Workflow-Antigravity và [dev-plan-p0.md](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/artifacts/2026-11-25-1633-paperclip-3phase-dev-plan/dev-plan-p0.md) đã kiểm chứng sẵn trong repo |
| Interview | CÓ | Đã hoàn tất xác nhận kỹ thuật (`1a 2a`) và chốt `muc_qc=ultra` (`3a`) |
| Spec + Archify BA preview | CÓ | `work_kind=build`: bắt buộc lập `§2b` ranh giới module và HTML preview Trước/Sau bound manifest trước cổng duyệt spec |
| Plan (`4` wave tách file nóng) | CÓ | Tổ chức `4` wave (`P0-W1`–`P0-W4`) không phụ thuộc cùng wave, `Red -> Green` từng task |
| Implement Python + Rust parity | CÓ | Nâng cấp lõi `scripts/`, hooks Python, Rust `tdq-dispatch`, sync `build_agy_plugin.py` |
| QC độc lập (`tdq-qc-tester`, mức `ultra`) | CÓ | Người dùng chốt `3a` (`muc_qc=ultra`): chạy đủ bộ test, parity, `run_full_verification.py` và `tdq-qc-tester` |
| Report + Archify HTML | CÓ | Xuất báo cáo 2 tầng kèm trang Archify HTML + Tailscale HTTP `200` trước khi hỏi merge `dev` |

## Hỏi đáp

1. **Cơ chế mở khóa khi `MCP Quarantine` chặn tool `write`/`destructive` mới:** **A (`1a`)** — Block bằng mã `[TDQ:READONLY]` kèm lệnh `py -3 scripts/mcp_policy.py approve <server> <tool>` lưu SHA-256 vào `docs/tdq/mcp-policy.json`, giữ tròn `23` mã cổng AGY và parity Python/Rust.
2. **Phạm vi thực thi `Circuit Breaker` & `Budget hard_stop`:** **A (`2a`)** — Lưu vào nhánh tùy chọn `p0_runtime` của `state.json` (`v6`) và chặn đồng bộ tại `edit_gate.py`, `bash_gate.py`, `lsp_gate.py` + `pre_tool_use.rs` kèm lệnh reset nhanh.
3. **Mức QC cho request `feature` `P0`:** **A (`3a`)** — **`ultra`** (DoD + trọn bộ test `Red -> Green` + `test_ntfs_concurrency` + `test_build_portable` + `test_rust_dispatch_parity` + `run_full_verification.py` + `tdq-qc-tester` độc lập).
