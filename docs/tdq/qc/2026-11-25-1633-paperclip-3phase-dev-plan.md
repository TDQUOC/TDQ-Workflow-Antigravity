# BIÊN BẢN QC — Bộ Development Plan Chi tiết `3` Pha Tích hợp Paperclip (`P0`–`P2`)

Ngày: 2026-11-25 · Request: `2026-11-25-1633-paperclip-3phase-dev-plan`
Loại: `docs` (`investigate`) · Mức QC: `ultra` (`Q1`–`Q6`) · Verdict cuối: **PASS (`DEFECTS: None`)**

> **Tóm tắt dễ hiểu:** Quá trình kiểm chứng độc lập mức `ultra` qua ba vòng đã xác nhận toàn bộ sáu cổng chất lượng đều đạt. Những lỗi phụ thuộc cùng wave, phạm vi matcher hook ở Antigravity và độ khớp đường dẫn cấu hình đều đã được xử lý triệt để trước khi chốt bản cuối. Kết quả bảo đảm bộ kế hoạch an toàn tuyệt đối để thi công các pha sau và giữ sạch hoàn toàn mã nguồn hiện hành.

---

## 1. Bảng Kết quả `6/6` Cổng Kiểm chứng (`Q1`–`Q6`)

| Hạng mục | Tiêu chí kiểm | Lệnh & Phương pháp xác minh | Kết quả quan sát thực tế | Trạng thái |
|---|---|---|---|---|
| `Q1` | `QC-I1` Grounding & không placeholder | `verify_plans.py` + `Select-String` kiểm toàn bộ `evidence.jsonl`, `s1..s3`, `master-roadmap.md`, `dev-plan-p0..p2.md`, `report.md` | `26/26` bằng chứng đúng biên dòng trên đĩa (`bounds_errors=[]`), `100%` được trích dẫn, `0` placeholder (`TODO`/`TBD`/`FIXME`) | **PASS** |
| `Q2` | `QC-I2` Đối chiếu nguyên văn `L2` (`>= 10` neo) & clean code verifier | Đọc trực tiếp `15` tệp nguồn trên đĩa và kiểm AST `verify_plans.py` | `15/15` điểm neo khớp nguyên văn chữ ký/dòng; `90/90` symbol đĩa + `16` đường dẫn mới hợp lệ; hàm `verify_plans.py` thuần stdlib, dài nhất `<= 38` dòng (`<= 50`) | **PASS** |
| `Q3` | Script tự kiểm `verify_plans.py` (`TDQ_LOG=1/0` + ca phủ định) | Chạy `TDQ_LOG=1` xuất ra `$env:TEMP\qc3_verify_plans.json` và `TDQ_LOG=0` đo byte stderr | `TDQ_LOG=1`: exit `0`, **`7/7` pass**; `TDQ_LOG=0`: exit `0`, **`0B` stderr**; ca phủ định giả lập `5/5` đều phát hiện lỗi (`NEG_EXIT=1`) | **PASS** |
| `Q4` | Phủ quyết định `1abcd..5c`, `H1`–`H4`, `docs/kien-truc.md`, `6` mục CẤM & wave rời | Đối chiếu chéo `spec.md`, `master-roadmap.md`, `dev-plan-p0/p1/p2.md` & `verify-results.json` | Đủ quyết định vòng 1 & 2, `H1`–`H4`, `78` script `0` import `hooks/`, đủ `6` mục CẤM Paperclip; `11` wave (`24` task, `32` cạnh phụ thuộc) `0` trùng file nóng, `0` phụ thuộc cùng/sau wave | **PASS** |
| `Q5` | `doc_lint.py`, biên `git diff`, Archify `current` & Tailscale HTTP `200` | `doc_lint.py` trên toàn bộ markdown + `git diff --name-only dev -- scripts/ hooks/ plugins/ tools/ tests/` + `tdq_archify.py verify` + `Invoke-WebRequest` | `0` vi phạm lint (kể cả `R16`); `git diff` mã nguồn sản phẩm rỗng (`0` byte đổi); Archify `status=current` (`0` diagnostics); Tailscale HTTP `200` | **PASS** |
| `Q6` | Thẩm định độc lập `tdq-qc-tester` (`muc_qc=ultra`) | `3` vòng kiểm chéo độc lập bằng subagent `tdq-qc-tester` | Vòng 1 (`a83215c4`) bắt `3` lỗi -> sửa xong; Vòng 2 (`ce108928`) bắt `2` lỗi nhỏ Q5 -> sửa xong; Vòng 3 (`1bdd8bde`) chốt **`Verdict: PASS`**, **`DEFECTS: None`** | **PASS** |

---

## 2. Lịch sử Thẩm định Độc lập `3` Vòng (`tdq-qc-tester`)

1. **Vòng 1 ([`a83215c4`](conversation://a83215c4-b83a-4e29-9f11-a2beffb97355)) — `FAIL` ở `Q4`:** Phát hiện `3` khiếm khuyết: (a) phụ thuộc cùng wave (`P0-W3`, `P1-W2/W3`, `P2-W2`) và `verify_plans.py` chưa kiểm cột phụ thuộc; (b) `hooks/hooks.json:76` và `tools/patches/agy_manifests.py:72` mới khớp `lsp` mà chưa khớp non-LSP MCP, đồng thời `tools/patches/common_utils.py:26` loại trừ `agy_pretooluse_gate.py` khỏi bundle AGY; (c) lệch tên `evaluate_tool()` vs `evaluate_tool_call()` ở `dev-plan-p0.md` và `excerpt` của `6f8f80aeae90` (`scripts/tdq_config.py`). Đã sửa triệt để toàn bộ, chia lại thành `11` wave sạch phụ thuộc và nâng `verify_plans.py` thêm khóa phụ thuộc wave + self-test phủ định.
2. **Vòng 2 ([`ce108928`](conversation://ce108928-f775-4f82-8e12-948e4b927303)) — `Q1`–`Q4` PASS, `FAIL` ở `Q5` (`2` lỗi Low):** Phát hiện số liệu cũ (`83` symbols, `9` wave, `25` task) sót trong `## Thân PR` ở dòng 81 của báo cáo và nhầm lẫn giữa `tdq-config.json` (cấp plugin) với `docs/tdq/config.json` (override cấp dự án tại `scripts/tdq_config.py:177-189`). Đã cập nhật đồng bộ cả `report.md` lẫn các plan/shard.
3. **Vòng 3 ([`1bdd8bde`](conversation://1bdd8bde-c440-4aa8-96ee-d6b33eda2d5d)) — `VERDICT: PASS`, `DEFECTS: None`:** Xác nhận toàn bộ sửa lỗi vòng 1 và vòng 2 đạt chuẩn, tái chạy độc lập `verify_plans.py` (`7/7` pass, `0B` khi `TDQ_LOG=0`) và toàn bộ kiểm tra `Q1`–`Q5`.

---

## 3. Bảng `15/15` Điểm Neo Mã nguồn Thật Đã Đối chiếu (`L2`)

| # | Tệp & Dòng trên đĩa | Symbol / Cấu trúc xác nhận nguyên văn | Liên hệ sang Plan |
|---|---|---|---|
| 1 | `scripts/tdq_state.py:259,579` | `default_state` (`schema_version: 6`), `save` (`overwriting anyway`) | `dev-plan-p0.md`, `P0-W2` |
| 2 | `scripts/tdq_state.py:3026-3101` | `_validate_work_kind_set`, `_cli_escalate_to_build` | `dev-plan-p1.md`, `P1-W2` |
| 3 | `hooks/scripts/_common.py:466-519` | `with_ntfs_lock` (`msvcrt.locking`, `LK_NBLCK`, `200` lần thử) | `dev-plan-p0.md`, `s1.md` |
| 4 | `scripts/tdq_team.py:594,654` | `chia_dot`, `detect_tcas_collision`, `TRAN_SONG_SONG` | `dev-plan-p0.md`, `P0-W2` |
| 5 | `scripts/tdq_config.py:35,177-189` | `DEFAULT_CONFIG`, `PLUGIN_ROOT / "tdq-config.json"`, `docs/tdq/config.json` | `dev-plan-p0/p1/p2.md` |
| 6 | `hooks/scripts/edit_gate.py:74,80` | `within`, `_enforce_agy_readonly_subagent`, `main` | `dev-plan-p0.md`, `dev-plan-p1.md` |
| 7 | `hooks/rust/tdq-dispatch/src/events/pre_tool_use.rs:723-797` | `handle_mcp_tool`, `handle_pre_tool_use` | `P0-W3`, `P1-W3` |
| 8 | `hooks/rust/tdq-dispatch/src/lock.rs:11,31,89` | `SidecarLockGuard`, `acquire_sidecar_lock`, `atomic_write_file` | `dev-plan-p0.md`, `P0-W1` |
| 9 | `scripts/skill_router.py:141-205` | `KhoBM25`, `tach_tu`, `bo_dau` | `dev-plan-p1.md`, `P1-W1` |
| 10 | `scripts/token_budget.py:45,49` | `TRAN_TOKEN = 3500`, `VUNG` | `dev-plan-p1.md`, `P1-W4` |
| 11 | `scripts/build_portable.py:76,635` | `RELEASE_EXCLUDE_SCRIPTS`, `la_duong_dan_release` | `dev-plan-p1.md`, `P1-W1` |
| 12 | `tools/build_agy_plugin.py:301,322` | `_copy_upstream_assets`, `_verify_staged_bundle` | `master-roadmap.md`, `P0-W4`, `P1-W4` |
| 13 | `hooks/hooks.json:76` | `PreToolUse` matcher `mcp__(plugin_tdq-workflow_)?lsp__(start_lsp\|blast_radius)` | `dev-plan-p0.md`, `P0-3.3` |
| 14 | `tools/patches/agy_manifests.py:65,72` | `generate_hooks_json`, `mcp_.*lsp_.*\|call_mcp_tool` | `dev-plan-p0.md`, `P0-3.3` |
| 15 | `tools/patches/common_utils.py:12,26` & `tools/patches/gate_guidance.json:32-56` | `EXCLUDED_SCRIPTS` (`agy_pretooluse_gate.py`), `all_agy_codes` (`23` mã) | `dev-plan-p0.md`, `P0-3.1`, `P0-3.2` |
