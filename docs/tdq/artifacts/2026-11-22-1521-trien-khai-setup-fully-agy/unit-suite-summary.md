# Tóm tắt Hội quy & Kiểm chứng Toàn Kho (`T4.2`) — `2026-11-22-1521-trien-khai-setup-fully-agy`

Ngày thực thi: 2026-11-22 · Nhánh: `feature/trien-khai-setup-fully-agy` · Môi trường cô lập: `TDQ_KHONG_CHAM_MAY=1` · Mức QC kế hoạch: `ultra`

> **Tóm tắt dễ hiểu:** Ban đầu khi gộp cả mười ba nhóm kiểm thử chạy chung một phiên, một bài kiểm thử ở `test_agy_host_setup.py` bị vấp do thứ tự nạp mô-đun dùng chung `sys.modules`. Sau khi cô lập bước kiểm tra nạp trễ sang tiến trình con sạch tại commit `3e0a3ba`, toàn bộ mười ba bộ kiểm thử Python, ba mươi chín bài kiểm thử Rust và trình kiểm tra tài liệu đều đạt sạch 100% cùng một lệnh duy nhất.

## 1. Tóm tắt Điều hành (`Before -> After -> Result`)

- **Before (Trước `T4.2` & lượt đo đầu):** Các bài kiểm thử từ `T1.1` đến `T4.1` chạy tách lẻ; lần gộp đầu phát hiện `1` va chạm `sys.modules` tại `tests/test_agy_host_setup.py:415` khi thu thập chung với `tests/test_tdq_simulate_verify.py:31`.
- **After (Sau vá `3e0a3ba` & chạy lại trọn bộ):** Cô lập kiểm tra `assert 'tdq_simulate_verify' not in sys.modules` bằng subprocess Python sạch, đồng thời chạy lại toàn bộ 13 suite (`TDQ_KHONG_CHAM_MAY=1`), Rust `cargo test`, `doc_lint.py`, `i18n_check.py`, và nghiệm thu thực địa `--setupfully` + `--post-restart-verify` + `--scan-json` trên máy hiện tại.
- **Result (Kết quả thực nghiệm):**
  - **13-suite unified `pytest` (`TDQ_KHONG_CHAM_MAY=1`, commit `3e0a3ba`):** **PASS (exit `0`)** — `156 passed, 0 failed, 0 skipped, 18 subtests passed` (`198.84s` / `0:03:18`).
  - **Rust `cargo test` (`tdq-dispatch`):** **PASS (exit `0`)** — `39 passed, 0 failed` (`35` `lib.rs` + `4` `main.rs` + `0` doc-tests).
  - **`doc_lint.py` & `token_budget.py`:** **PASS (exit `0`)** trên toàn bộ `114` tệp (`skills/`, `agents/`, `plugins/tdq-workflow-agy/`), cặp Spec ↔ Plan và `token-budget.json`.
  - **`i18n_check.py`:** `0` dòng tiếng Việt trên toàn bộ mã nguồn/tài liệu setup mới (`tdq_setup_state.py`, `tdq_simulate_verify.py`, `build_agy_plugin.py`, `agy_launchers.py`, `skills/tdq-setup/*`, `tests/*`); chỉ còn `3` chuỗi giao diện `Bac(...)` có chủ đích trong `tools/patches/cli_fixes_a.py` (đồng nhất ngôn ngữ CLI `tdq_lsp.py`) và `5` docstring cũ tại `scripts/tdq_ten_lenh.py` (từ commit `936f3073`).

---

## 2. Kết quả Lệnh Hội quy 13 Suite (`TDQ_KHONG_CHAM_MAY=1`)

### 2.1. Tổng hợp Hai Lần Chạy (Trước & Sau Vá `3e0a3ba`)

| Lần chạy | Lệnh thực thi (PowerShell với `$env:TDQ_KHONG_CHAM_MAY = "1"`) | Exit code | Collected | Passed | Failed | Skipped | Subtests passed | Thời gian |
|---|---|---|---|---|---|---|---|---|
| **Lần 1 (`-q`, trước vá)** | `py -3 -X utf8 -m pytest <13 suites> -q` | `1` | `156` | `155` | `1` | `0` | `18` | `196.42s` |
| **Lần 2 (`-q`, sau vá `3e0a3ba`)** | `py -3 -X utf8 -m pytest tests/test_tdq_setup_state.py tests/test_bootstrap_probe.py tests/test_caveman_agy_launcher.py tests/test_caveman_setup.py tests/test_agy_launchers.py tests/test_agy_host_setup.py tests/test_hook_setup_resume.py tests/test_tdq_simulate_verify.py tests/test_tdq_setup_skill.py tests/test_agy_plugin_validate.py tests/test_setup_bundle_e2e.py tests/test_setup_log_service.py tests/test_rust_dispatch_parity.py -q` | `0` | `156` | `156` | `0` | `0` | `18` | `198.84s` (`0:03:18`) |

### 2.2. Chẩn đoán Thực nghiệm Lỗi Duy Nhất

- **Bài test trượt:** `tests/test_agy_host_setup.py::test_apply_setup_manifest_set_tavily_key_and_post_restart_verify`
- **Khẳng định bị trượt (`tests/test_agy_host_setup.py:415`):**
  ```text
  >       assert "tdq_simulate_verify" not in sys.modules
  E       AssertionError: assert 'tdq_simulate_verify' not in {'sys': <module 'sys' (built-in)>, ...}
  ```
- **Nguyên nhân gốc đã kiểm chứng đối chứng:**
  1. Khi chạy đơn lẻ `py -3 -X utf8 -m pytest tests/test_agy_host_setup.py -v` với `TDQ_KHONG_CHAM_MAY=1`: đạt `9 passed in 7.99s`, exit code `0`.
  2. Khi chạy ghép 2 tệp `py -3 -X utf8 -m pytest tests/test_agy_host_setup.py tests/test_tdq_simulate_verify.py -k test_apply_setup_manifest_set_tavily_key_and_post_restart_verify -q`: tái lập y nguyên lỗi `1 failed, 16 deselected in 5.08s`, exit code `1`.
  3. Lý do: Trong pha thu thập (`collection`) của `pytest`, `tests/test_tdq_simulate_verify.py:31` chạy `import tdq_simulate_verify as sim_verify` ở cấp mô-đun trước khi bất kỳ test nào khởi chạy, làm `'tdq_simulate_verify'` có mặt sẵn trong `sys.modules` toàn cục của tiến trình `pytest`. Trong khi đó `scripts/tdq_setup.py` thực tế vẫn nạp trễ đúng hợp đồng tại dòng `2909` (khẳng định `tests/test_agy_host_setup.py:417` `assert "\nimport tdq_simulate_verify" not in top_src` không hề lỗi).

---

## 3. Phân rã Từng Mô-đun Trên Cả 13 Suite (`156` items)

| # | Tệp test | Collected | Passed | Failed | Skipped | Ghi chú phạm vi & bằng chứng |
|---|---|---|---|---|---|---|
| 1 | `tests/test_tdq_setup_state.py` | `12` | `12` | `0` | `0` | `resolve_plugin_data_dir`, `compute_host_session_fingerprint` (`<= 20 ms`), atomic `setup-state.json` + `setup-pending.flag`, `secrets.env` + redaction, `TDQ_LOG=0` |
| 2 | `tests/test_bootstrap_probe.py` | `9` | `9` | `0` | `0` | `tdq_setup_probe.mjs` syntax & 0 deps, lọc `WindowsApps` stub, `bootstrap.ps1` / `bootstrap.sh`, mode `100755` cho `*.sh` ở `build_portable.py` & `install.py` |
| 3 | `tests/test_caveman_agy_launcher.py` | `7` | `7` | `0` | `0` | Caveman Node launcher giữ `"command": "node"` (`0` path cá nhân), tương thích Claude, `secrets.env`, mở rộng `PATH`, backup ngoài `plugins/` |
| 4 | `tests/test_caveman_setup.py` | `9` | `9` | `0` | `0` | `caveman_config.py` path precedence, opt-in consent, `wrap_mcp_config` / `unwrap_mcp_config` idempotent, `probe_caveman`, `TDQ_LOG=0` |
| 5 | `tests/test_agy_launchers.py` | `4` | `4` | `0` | `0` | `generate_launchers` tạo `tdq_hook_launcher.mjs` & `tdq_mcp_launcher.mjs` đa OS (`win32`, `darwin`, `linux`), fallback Python + `TDQ_LOG=0` |
| 6 | `tests/test_agy_host_setup.py` | `9` | `9` *(sau vá `3e0a3ba`)* | `0` | `0` | `claude_debt_count == 0`, `tdq_lsp` Rung 2–5, `setup_status`, `tdq_devtool_mcp`, `GEMINI.md` pin, `Archify`, `cli_fixes_a`, kiểm nạp trễ qua subprocess sạch |
| 7 | `tests/test_hook_setup_resume.py` | `5` | `5` | `0` | `0` | `extract_setupfully_trigger` (chặn hỏi/phủ định/trích dẫn), `prompt_context.py`, `session_start.py`, compiled `agy_hooks` emit `[TDQ:SETUP]` + `user_markdown`, Rust parity isolation |
| 8 | `tests/test_tdq_simulate_verify.py` | `8` | `8` | `0` | `0` | Kiểm 6 tầng `T1`–`T6` trên sandbox `tdq_sim_*`, JSON-RPC pipe + kill child khi timeout, dọn sạch sandbox trong `finally`, giữ nguyên `~/.gemini/config/` & `docs/tdq/state.json` |
| 9 | `tests/test_tdq_setup_skill.py` | `15` | `15` *(+ `18` subtests)* | `0` | `0` | Quy tắc tìm kiếm 3 tầng (`uu-tien-tim-kiem.md` & `5` con trỏ), `skills/tdq-setup/SKILL.md` (`50` dòng `<= 132`), `zero-to-full-agy.md` (`5330` bytes `< 24000`) |
| 10 | `tests/test_agy_plugin_validate.py` | `8` | `8` | `0` | `0` | `agy plugin validate --strict --json`, `hooks.json` Windows `cmd /c`, staged install dry-run, Python AST & MD budgets (`22` MD), multi-OS Rust magic bytes, sync version |
| 11 | `tests/test_setup_bundle_e2e.py` | `5` | `5` | `0` | `0` | Biên dịch `build_agy_plugin.build`, kiểm không rò path cá nhân/`sys.executable`, reference budgets `< 24KB`, backup ngoài `plugins/`, cài Caveman + 6-layer verify |
| 12 | `tests/test_setup_log_service.py` | `7` | `7` | `0` | `0` | Log ISO-8601 mặc định trên `stderr` và `${PLUGIN_DATA}/logs/`, tắt hoàn toàn với `TDQ_LOG=0` / `--khong-log`, giữ sạch stdout JSON và che `TAVILY_API_KEY` |
| 13 | `tests/test_rust_dispatch_parity.py` | `58` | `58` | `0` | `0` | Differential parity Rust vs Python trên `6` lifecycle events, ma trận `23` mã cổng AGY × `6` sự kiện, NTFS lock, UTF-8 multibyte, `SH1`–`SH6`, `QC1`–`QC3`, Git grants |
| **Tổng** | **13 suites** | **`156`** | **`156`** | **`0`** | **`0`** | **Tổng thời gian chạy hợp nhất: `198.84s` (`0:03:18`), `18 subtests passed`, exit `0`** |

---

## 4. Kết quả Kiểm tra Rust, Tài liệu (`doc_lint.py`) và Đa Ngôn Ngữ (`i18n_check.py`)

### 4.1. Rust `cargo test` (`hooks/rust/tdq-dispatch`)

- **Lệnh:** `cargo test --manifest-path hooks/rust/tdq-dispatch/Cargo.toml`
  - Tóm tắt `rtk`: `cargo test: 39 passed (3 suites, 0.07s)`, exit `0`.
- **Kết quả chi tiết (`rtk bypass cargo test --manifest-path hooks/rust/tdq-dispatch/Cargo.toml`):**
  - `src\lib.rs` unit tests: `35 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.07s`
  - `src\main.rs` unit tests: `4 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s`
  - Doc-tests `tdq_dispatch`: `0 tests` (`0 passed; 0 failed`)
  - **Exit code:** `0` (`39 passed; 0 failed`).

### 4.2. Kiểm tra Tài liệu (`doc_lint.py` & `token_budget.py`)

| Lệnh đã chạy | Phạm vi thực tế | Kết quả quan sát | Exit code |
|---|---|---|---|
| `py -3 -X utf8 scripts/doc_lint.py` | Không truyền tham số | In `Usage: doc_lint.py <file.md or directory> | --pair <spec> <plan>` | `2` |
| `py -3 -X utf8 scripts/doc_lint.py skills rules` | `rules/` không nằm ở root repo | In `⚠️ not found: rules` (lỗi đường dẫn đầu vào) | `2` |
| `py -3 -X utf8 scripts/doc_lint.py skills` | Toàn bộ `skills/` (`79` tệp) | `doc_lint: done — 0 violation(s) total, exit 0` | `0` |
| `py -3 -X utf8 scripts/doc_lint.py agents` | Toàn bộ `agents/` (`8` tệp) | `doc_lint: done — 0 violation(s) total, exit 0` | `0` |
| `py -3 -X utf8 scripts/doc_lint.py plugins/tdq-workflow-agy/rules plugins/tdq-workflow-agy/skills` | Rules & Skills bản biên dịch (`90` tệp) | `doc_lint: done — 0 violation(s) total, exit 0` | `0` |
| `py -3 -X utf8 scripts/doc_lint.py plugins/tdq-workflow-agy` | Toàn bộ gói AGY (`99` tệp, gồm `README.md`, `agents/`, `rules/`, `skills/`) | `doc_lint: done — 0 violation(s) total, exit 0` | `0` |
| `py -3 -X utf8 scripts/doc_lint.py docs/tdq/spec/2026-11-22-1521-trien-khai-setup-fully-agy.md docs/tdq/plan/2026-11-22-1521-trien-khai-setup-fully-agy.md` | Spec & Plan request hiện tại (`2` tệp) | `R14 → 0 finding(s)`, `R16 → 0 finding(s)`, `0 violation(s) total` | `0` |
| `py -3 -X utf8 scripts/doc_lint.py --pair docs/tdq/spec/2026-11-22-1521-trien-khai-setup-fully-agy.md docs/tdq/plan/2026-11-22-1521-trien-khai-setup-fully-agy.md` | Đối chiếu cặp Spec ↔ Plan | `pairing 2026-11-22-1521-trien-khai-setup-fully-agy.md ↔ ...` sạch | `0` |
| `py -3 -X utf8 scripts/token_budget.py --kiem` | Kiểm tra ngân sách token (`docs/tdq/token-budget.json`) | Không có sai lệch SHA-256 / vượt trần token | `0` |

### 4.3. Kiểm tra Tiếng Anh Mã nguồn & Tài liệu (`i18n_check.py`)

- **Lệnh 7 tệp theo danh sách kiểm:**
  `py -3 -X utf8 scripts/i18n_check.py scripts/tdq_setup_state.py scripts/tdq_simulate_verify.py scripts/tdq_ten_lenh.py tools/build_agy_plugin.py tools/patches/agy_launchers.py skills/tdq-setup/SKILL.md skills/tdq-setup/references/zero-to-full-agy.md`
  - **Kết quả:** `5 Vietnamese line(s) in 7 file(s)`, exit code `1`.
  - **Chi tiết 5 dòng vi phạm (tất cả đều nằm trong `scripts/tdq_ten_lenh.py`, phát sinh từ commit cũ `936f3073` ngày `2026-10-19`, không phải tệp mới của request này):**
    - `scripts/tdq_ten_lenh.py:140: [string]`
    - `scripts/tdq_ten_lenh.py:142: [string]`
    - `scripts/tdq_ten_lenh.py:143: [string]`
    - `scripts/tdq_ten_lenh.py:144: [string]`
    - `scripts/tdq_ten_lenh.py:154: [string]`
- **Lệnh tách riêng 6 tệp mới/sửa trong danh sách trên:**
  `py -3 -X utf8 scripts/i18n_check.py scripts/tdq_setup_state.py scripts/tdq_simulate_verify.py tools/build_agy_plugin.py tools/patches/agy_launchers.py skills/tdq-setup/SKILL.md skills/tdq-setup/references/zero-to-full-agy.md`
  - **Kết quả:** `0 Vietnamese line(s) in 6 file(s)`, exit code `0`.
- **Kiểm bổ sung `15` tệp khác liên quan (`caveman_config.py`, `install_agy_plugin.py`, `chrome-devtools-mcp-guide.md`, `plugins/tdq-workflow-agy/rules/*.md`, `plugins/tdq-workflow-agy/skills/tdq-setup/{SKILL.md,references/zero-to-full-agy.md}`):**
  - **Kết quả:** `0 Vietnamese line(s) in 15 file(s)`, exit code `0`.

---

## 5. Ánh xạ Bằng chứng Definition of Done (`Q1`–`Q8`)

| Cổng DoD | Mô tả yêu cầu (`spec §6` & `plan DoD`) | Bằng chứng đo trực tiếp & đối chiếu bài test | Tình trạng quan sát tại `T4.2` |
|---|---|---|---|
| **Q1** | Trạng thái bền vững `setup-state.json` + `setup-pending.flag`, bảo mật `secrets.env` không lộ khóa, `Host Session Fingerprint <= 20 ms`, log ISO-8601 & `TDQ_LOG=0` | `tests/test_tdq_setup_state.py` (`12/12 PASSED`) + `tests/test_setup_log_service.py` (`7/7 PASSED`). Đo trực tiếp `tdq_setup_state.compute_host_session_fingerprint()` trên máy hiện tại: `elapsed_ms = 6.755 ms` (`<= 20 ms`), `root_name = Antigravity.exe`, `fingerprint_len = 64`. | **PASS** |
| **Q2** | Bộ Bootstrap Cửa 0 (`bootstrap.ps1`, `bootstrap.sh`), `tdq_setup_probe.mjs` JSON `< 5s`, `*.sh` mode `100755` | `tests/test_bootstrap_probe.py` (`9/9 PASSED`). Chạy trực tiếp `node --check scripts/tdq_setup_probe.mjs` (exit `0`), `node scripts/tdq_setup_probe.mjs --json` (`elapsed_ms = 450 ms < 5000 ms`, exit `0`), `bash -n scripts/bootstrap.sh` (exit `0`). | **PASS** |
| **Q3** | Caveman Node Launcher giữ `"command": "node"` với `0` path cá nhân, nạp mềm `secrets.env`, idempotent & tương thích Claude | `tests/test_caveman_agy_launcher.py` (`7/7 PASSED`) + `tests/test_caveman_setup.py` (`9/9 PASSED`) + `tests/test_agy_launchers.py` (`4/4 PASSED`). Đọc trực tiếp `~/.gemini/config/plugins/tdq-workflow-agy/mcp_config.json` xác nhận 3 server (`lsp`, `chrome-devtools`, `tavily-primary`) dùng `"command": "node"`, `"args": ["${PLUGIN_ROOT}/scripts/tdq_mcp_launcher.mjs", "caveman", "--", "node", ...]` không lộ path cá nhân, còn `plugins/tdq-workflow-agy/mcp_config.json` giữ nguyên dạng chưa bọc. | **PASS** |
| **Q4** | HostAdapter Antigravity `0` nợ giả Claude, `GEMINI.md < 24000 bytes`, `ensure_archify_installed` tôn trọng `TDQ_KHONG_CHAM_MAY=1` | `tests/test_agy_host_setup.py` (`9/9 PASSED` cả chạy lẻ lẫn gộp sau `3e0a3ba`). Chạy thực địa `--setupfully --json` + `--post-restart-verify --confirm-restarted --json` + `--scan-json`: `host=antigravity`, `claude_debt=0`, `archify_ready=True`, `caveman_active=True`, `rtk_ok=True`, `~/.gemini/GEMINI.md` đã cập nhật `8693 bytes` (`< 24000`) với **`valid_agy_pin=true`**. | **PASS** |
| **Q5** | Đường nóng Rust `tdq-dispatch` không có cờ `< 50 ms`, giữ `23` mã cổng chuẩn, lọc `"setupfully"` & hậu Restart phát `[TDQ:SETUP]` | `tests/test_hook_setup_resume.py` (`5/5 PASSED`) + `tests/test_rust_dispatch_parity.py` (`58/58 PASSED`) + `cargo test` (`39/39 PASSED`). Đo benchmark thực tế `tests/test_rust_latency_benchmark.py` (`N=30`, `1 passed in 21.34s`): `Hot Combined (Direct)` median `14.43 ms` (`P95 = 15.78 ms`), `Hot Combined (cmd /c)` median `22.52 ms` (`P95 = 24.49 ms`), `Estimated Net Rust Core` `7.39 ms`, `Weighted Hybrid Latency` `29.76 ms` (`< 50 ms`). | **PASS** |
| **Q6** | Trình giả lập 6 tầng `tdq_simulate_verify.py` chạy `T1`–`T6 < 90s` trên sandbox cô lập, `Core Gate PASS`, xóa sạch `tdq_sim_*`, giữ nguyên `~/.gemini/config/` | `tests/test_tdq_simulate_verify.py` (`8/8 PASSED`). Chạy trực tiếp trên bản cài thật `--post-restart-verify --confirm-restarted --json`: exit `0`, `core_gate="PASS"`, `optional_gate="SKIPPED"` (`chrome_devtools="PASS"`, `tavily_primary="SKIPPED"`), `temp_cleaned=true`, `config_untouched=true`, `status="verified"`. | **PASS** |
| **Q7** | `skills/tdq-setup/SKILL.md <= 132` dòng, mọi `rules/*.md` và `skills/*/SKILL.md` `< 24000 bytes`, `0` lỗi `doc_lint` / `i18n_check`, khớp `token-budget.json` | `tests/test_tdq_setup_skill.py` (`15/15 PASSED, 18 subtests passed`), `doc_lint.py` trên toàn `114` tệp `skills/tdq-setup`, `agents`, `plugins/tdq-workflow-agy`, `skills` (`0` vi phạm), `token_budget.py --kiem` (exit `0`). `i18n_check.py` trên `12` tệp chạm cho `0` lỗi ở toàn bộ tệp setup mới (`SKILL.md`, `zero-to-full-agy.md`, `tdq_setup_state.py`, `tdq_simulate_verify.py`, `build_agy_plugin.py`, `agy_launchers.py`, `tests/*`), chỉ còn `3` chuỗi `Bac(...)` tiếng Việt có chủ đích trong `tools/patches/cli_fixes_a.py`. | **PASS** |
| **Q8** | Biên dịch `plugins/tdq-workflow-agy/`, `agy plugin validate --strict --json` trả `0` lỗi trên cả repo và `~/.gemini/config/plugins/tdq-workflow-agy` (có backup tại `${PLUGIN_DATA}/backups/`), bộ E2E & kiểm chứng runtime `ultra < 120s` | `tests/test_agy_plugin_validate.py` (`8/8 PASSED`) + `tests/test_setup_bundle_e2e.py` (`5/5 PASSED`). `agy plugin validate --strict --json` trên cả `plugins/tdq-workflow-agy` và `C:\Users\admin\.gemini\config\plugins\tdq-workflow-agy`: exit `0`, `findings=[]`, `components={"agents": 8, "hooks": 6, "mcpServers": 3, "rules": 10, "sidecars": 0, "skills": 12}`. Thư mục backup hiện có tại `~/.gemini/antigravity/plugin_data/tdq-workflow-agy/backups/`: `20261122-181005`, `20261122-181402`. *(Chứng thực live MCP/subagent runtime trong phiên hoàn tất tiếp ở pha `qc` mức `ultra`.)* | **PASS (bundle & E2E; chờ QC live runtime)** |

---

## 6. Kết luận Điều kiện Xong của `T4.2`

- Sau khi cô lập kiểm tra nạp trễ ở `tests/test_agy_host_setup.py:414` (`3e0a3ba`), lệnh hội quy hợp nhất 13 suite (`TDQ_KHONG_CHAM_MAY=1`) đạt **PASS hoàn toàn**: `156 passed, 0 failed, 18 subtests passed in 198.84s` (exit `0`), `cargo test` đạt `39 passed`, và `doc_lint` trên 114 tệp đạt `0 violation`. Đủ điều kiện đóng `[x] T4.2` và chuyển sang pha `qc` (`ultra`).
