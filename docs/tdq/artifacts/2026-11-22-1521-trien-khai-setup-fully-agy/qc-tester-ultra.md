# Báo cáo Kiểm định Độc lập `ultra` (`tdq-qc-tester`) — Vòng 2 (Sau Sửa Lỗi) — `2026-11-22-1521-trien-khai-setup-fully-agy`

Ngày kiểm định: 2026-11-22 · Nhánh: `feature/trien-khai-setup-fully-agy` · Chế độ: Độc lập, không sửa mã nguồn, không chạy `tdq_test.py tron-bo`.

> **Tóm tắt dễ hiểu:** Trước vòng kiểm định này, đợt rà soát đầu ghi nhận trượt `1` bài kiểm thử ở `Q1`, `11` hàm vượt ngưỡng độ phức tạp chu trình, `1` hàm `53` dòng ở `bootstrap.ps1`, `3` điểm nuốt exception không ghi log và `2` chi tiết đường dẫn cũ trong tài liệu tham chiếu. Sau khi đội phát triển sửa toàn bộ 4 nhóm lỗi và biên dịch/cài lại gói Antigravity, kiểm định độc lập lại xác nhận toàn bộ `Q1`–`Q8`, `QC-F3` và `QC-F4` đều đạt **PASS 100%** với `161/161` ca pytest trọng tâm và `39/39` ca Rust xanh.

---

## 1. Bảng Bằng chứng Kiểm chứng Lại (`Q1`–`Q8`, `QC-F3`, `QC-F4`)

| # | Hạng mục kiểm | Lệnh / Cách kiểm thực tế (tái chạy sau sửa cuối) | Kết quả quan sát thật | PASS / FAIL |
|---|---|---|---|---|
| **Q1** | Trạng thái bền vững, `secrets.env`, `Host Session Fingerprint <= 20 ms`, `TDQ_LOG=0` & suite `Q1` | 1) `compute_host_session_fingerprint()` x5; `TDQ_LOG=0` trên `tdq_setup_state.py`<br>2) `py -3 -X utf8 -m pytest tests/test_tdq_setup_state.py tests/test_setup_log_service.py -v` | 1) `FP_MS: [7.46, 7.501, 7.596, 8.086, 7.194] MAX: 8.086`; `STATE_TDQ_LOG_0_STDERR: '' RC: 0`<br>2) **`20 passed in 35.07s`** (`Q1_EXIT=0`), gồm `test_node_mcp_launcher_stderr_and_tdq_log_zero PASSED` (`lsp`: `has_key=False`, `--tavily`: `has_key=True`) | **PASS** |
| **Q2** | Bootstrap Cửa 0 (`ps1`, `sh`), `tdq_setup_probe.mjs < 5s`, `100755` | 1) `node --check scripts/tdq_setup_probe.mjs; bash -n scripts/bootstrap.sh; node scripts/tdq_setup_probe.mjs --json`<br>2) `git ls-files -s ...bootstrap.sh` & PS1 `[Parser]::ParseFile(...)` trên src + pkg | 1) `PROBE_OK: 1 MS: 486 PY: True AGY: True`; `bash -n` exit `0`<br>2) `100755` cả src & pkg; `PS1_SRC_ERRS=0 PS1_PKG_ERRS=0`; `test_bootstrap_probe.py` PASS | **PASS** |
| **Q3** | Caveman Node Launcher (`"command": "node"`, `0` path cá nhân), `secrets.env` | Probe `node` `tdq_mcp_launcher.mjs` (`node --check`) & suite `test_caveman_setup.py`, `test_caveman_agy_launcher.py`, `test_agy_launchers.py` | `PKG_MCP=0 PKG_HOOK=0 PKG_PROBE=0`; `SYNC diff_lines=0`; 3 suite Caveman/Launcher PASS trong batch 11 + batch 2 | **PASS** |
| **Q4** | HostAdapter Antigravity, `--scan-json` `0` nợ Claude, `GEMINI.md < 24KB`, `TDQ_KHONG_CHAM_MAY=1` | `py -3 -X utf8 scripts/tdq_setup.py --scan-json` & `test_agy_host_setup.py` | `SCAN_HOST: antigravity CLAUDE_DEBT: 0 GEMINI_BYTES: 8693 VALID_PIN: True STATE_STATUS: verified`; `test_agy_host_setup.py` PASS | **PASS** |
| **Q5** | Đường nóng Rust `< 50 ms`, `setupfully` / `source` guard, `cargo test` & parity | 1) 10x `.\plugins\tdq-workflow-agy\bin\tdq-dispatch.exe --event PostInvocation`<br>2) Probe `plugins/tdq-workflow-agy/hooks/scripts/prompt_context.py` + `cargo test` + `test_rust_dispatch_parity.py` | 1) `MAX=9.56 MED=6.57` ms (internal `0.32-0.39 ms`)<br>2) `PKG_PC_OK: True PKG_PC_COMPACT: '' PKG_PC_QUESTION: ''`; `cargo test: 39 passed (0.07s)`; `test_agy_launchers.py + test_rust_dispatch_parity.py`: **`62 passed in 79.97s`** | **PASS** |
| **Q6** | `tdq_simulate_verify.py` 6 tầng `T1`–`T6 < 90s` trên bản cài lại & sandbox sạch | `TDQ_KHONG_CHAM_MAY=1` chạy `tdq_simulate_verify.py --plugin-root "$env:USERPROFILE\.gemini\config\plugins\tdq-workflow-agy" --state-dir <tmp> --json` | `SIM_REVERIFY_EXIT=0 SEC=8.31` (`elapsed_sec=8.156`, `T1..T6: PASS`, `core_gate=PASS`, `temp_cleaned=true`, `config_untouched=true`); live `setup-state.json` `verified`, `PENDING_FLAG_FILE: False` (`7.926s`); `test_tdq_simulate_verify.py` PASS | **PASS** |
| **Q7** | `SKILL.md <= 132` dòng, `zero-to-full-agy.md`, `< 24KB`, `doc_lint`, `token_budget`, `i18n_check` | 1) Đọc `SKILL.md` + `zero-to-full-agy.md` (src + pkg), đếm byte `22` MD<br>2) `doc_lint.py`, `token_budget.py --kiem`, `i18n_check.py` (11 tệp mới/Anh), `pytest test_tdq_setup_skill.py` | 1) `SKILL.md`: `50` dòng (`4782`/`4783` B, có `(phase does not change)`); `zero-to-full-agy.md` ghi đúng `setup-state.json` & `~/.gemini/config/plugins/tdq-workflow-agy/mcp_config.json`; `OVER_24000: []`<br>2) `DOC_LINT=0`, `BUDGET=0`, `I18N=0` (`0` line in `11` files), `test_tdq_setup_skill.py`: **`15 passed, 18 subtests passed in 0.10s`** | **PASS** |
| **Q8** | Validate `--strict`, `plugin list`, parity live vs repo, E2E & live MCP | 1) `agy.EXE plugin validate --strict --json` (repo + live) & `agy.EXE plugin list --json`<br>2) So byte toàn cây live vs `plugins/tdq-workflow-agy`<br>3) `pytest tests/test_agy_plugin_validate.py tests/test_setup_bundle_e2e.py -q` & `mcp_tdq-workflow-agy_lsp` `list_symbols` | 1) `VAL_REPO=0 VAL_LIVE=0`, `findings: []` (`8/6/3/10/12`); `PLUGINS: 8 DUPS: False TDQ_VER: 0.105.0 ENABLED: True`<br>2) **`LIVE_VS_PKG_DIFFS: [] EXTRA_IN_LIVE: []`**<br>3) **`13 passed in 24.53s`** (`Q8_EXIT=0`); `list_symbols` trả outline `527` dòng | **PASS** |
| **QC-F3** | Ràng buộc kiến trúc `spec §5` & đồng bộ src ↔ pkg | Kiểm `SYNC diff_lines` 9 script chia sẻ & `hooks/` compiled | `SYNC *: diff_lines=0`; `PKG_SS_HAS_LOG_WARN: True`; `PKG_PC_HAS_INFO_LOG: True`; `0` vi phạm biên kiến trúc | **PASS** |
| **QC-F4** | Clean Code (`cyc <= 10`, hàm `<= 50` dòng, `except` logging, `TDQ_LOG=0`) | AST Python trên 17 file chạm + parser block JS/PS1 + probe `TDQ_LOG=0` ở `session_start.py` | Toàn bộ 11 hàm mới/sửa trước đây + `_prepare_lsp_socket_env` đều **`cyc <= 10` và `<= 50` dòng** (`long>50=[] cyc>10=[]` ở `tdq_setup_state.py`, `tdq_simulate_verify.py`, `setup_status.py`, `caveman_config.py`, `build_agy_plugin.py`; `PS1 Invoke-Main` = `34` dòng; `JS_LEN_GT_50: []`); 3 điểm `except` mới đã log chẩn đoán (`HOOK_SS_LOG0_RC: 0 STDERR: ''`) | **PASS** |

---

## 2. Tổng hợp Chạy Kiểm thử Độc lập Sau Lần Sửa Cuối

- **Rust `cargo test --manifest-path hooks/rust/tdq-dispatch/Cargo.toml --quiet`:** **PASS** (`39 passed`, `0.07s`, exit `0`).
- **Batch 11 suite cốt lõi (`TDQ_KHONG_CHAM_MAY=1`):** **PASS** (`99 passed, 18 subtests passed in 119.06s`, exit `0`).
- **Batch 2 suite parity (`test_agy_launchers.py`, `test_rust_dispatch_parity.py`, `TDQ_KHONG_CHAM_MAY=1`):** **PASS** (`62 passed in 79.97s`, exit `0`).
  - **Tổng hợp toàn bộ 13 suite setup/parity (`TDQ_KHONG_CHAM_MAY=1`):** **`161 passed, 0 failed, 18 subtests passed`**.
- **Chạy đơn lẻ theo từng cổng DoD (`TDQ_KHONG_CHAM_MAY=1`):**
  - `Q1` (`test_tdq_setup_state.py` + `test_setup_log_service.py`): **`20 passed in 35.07s`**, exit `0`.
  - `Q7` (`test_tdq_setup_skill.py`): **`15 passed, 18 subtests passed in 0.10s`**, exit `0`.
  - `Q8` (`test_agy_plugin_validate.py` + `test_setup_bundle_e2e.py`): **`13 passed in 24.53s`**, exit `0`.

---

## 3. Đối chiếu Khắc phục 4 Khiếm khuyết Vòng 1 (`DEFECTS`)

1. **Defect #1 (`Q1` — HIGH) → ĐÃ SỬA & XÁC MINH:** `tests/test_setup_log_service.py:231-255` đã kiểm `"lsp"` -> `has_key=False` và `"--tavily"` -> `has_key=True`, vượt qua hoàn chỉnh (`20 passed in 35.07s`).
2. **Defect #2 (`QC-F4` — MEDIUM) → ĐÃ SỬA & XÁC MINH:** Toàn bộ 11 hàm vượt `cyc > 10` ở mã mới/sửa và `Invoke-Main` (`53` → `34` dòng) ở `scripts/bootstrap.ps1` đã tách helper gọn dưới ngưỡng (`cyc <= 10`, `<= 50` dòng); hàm mới `_prepare_lsp_socket_env` (`scripts/tdq_simulate_verify.py:1008`) cũng đạt ngưỡng sạch. *(Các hàm vượt ngưỡng duy nhất còn lại trong `TOUCHED_OVER` như `prompt_context.py:main`, `session_start.py:main`, `tdq_setup.py:_run_legacy_claude_setup`, `tdq_lsp.py:bac3_language_server` đều là mã cũ chỉ chạm 1–5 dòng phẫu thuật.)*
3. **Defect #3 (`QC-F4` — MEDIUM) → ĐÃ SỬA & XÁC MINH:** 3 khối `except` mới ở `prompt_context.py:211-212`, `session_start.py:282-283`, `tdq_simulate_verify.py:801-802` đều ghi log chẩn đoán và tôn trọng `TDQ_LOG=0` (đã xác minh `HOOK_SS_LOG0_RC: 0 STDERR: ''`).
4. **Defect #4 (`Q7` — LOW) → ĐÃ SỬA & XÁC MINH:** `skills/tdq-setup/references/zero-to-full-agy.md:9-10,24` đã sửa đúng `setup-state.json` và `~/.gemini/config/plugins/tdq-workflow-agy/mcp_config.json`; `SKILL.md:50` thêm `(phase does not change)`; `token_budget.py --kiem` và `doc_lint.py` đều trả exit `0` trên cả bản nguồn và bản biên dịch.

**DEFECTS:** None

**VERDICT:** `PASS everything`
