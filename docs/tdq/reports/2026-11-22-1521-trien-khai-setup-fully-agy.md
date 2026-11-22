# BÁO CÁO — Triển khai quy trình Setupfully Zero-to-Full và Simulate Test 6 tầng cho Antigravity

Ngày: 2026-11-22 · Mã yêu cầu: 2026-11-22-1521-trien-khai-setup-fully-agy (10/10 task + 5/5 fix QC tick đủ, Q1–Q8 PASS)
Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

> **Tóm tắt dễ hiểu:** Trước khi làm, lệnh setup trên Antigravity vẫn đụng vào cấu hình Claude cũ và thiếu bước mồi máy trắng. Hệ thống cũng thiếu dấu nối tiếp sau khi khởi động lại IDE lẫn bài kiểm thử giả lập tổng thể trên sandbox sạch. Nay quy trình mới tách riêng cho Antigravity với bộ mồi đa nền tảng, dấu phiên Host Session Fingerprint, bọc Caveman thuần Node và bộ kiểm thử 6 tầng tự dọn dẹp. Gói mới đã biên dịch, cài trực tiếp lên máy thật và đạt xanh toàn bộ kiểm định độc lập lẫn 4.809 bài kiểm thử toàn kho.

## 1. Trước request (trạng thái/flow)

Trước khi triển khai, quy trình thiết lập TDQ Workflow trên Google Antigravity còn các khoảng trống lớn:
- Chưa có bộ khởi động Cửa 0 (`Windows`/`macOS`/`Linux`) thuần không phụ thuộc Python/Node có sẵn, nên máy trắng khó chạy `tdq-setup` một mạch.
- `scripts/tdq_setup.py` kiểm tra nợ theo lối Claude (`~/.claude.json`, `~/.claude/settings.json`), dễ tạo nợ giả khi chạy thuần trên Antigravity.
- Chưa có trạng thái bền vững `${PLUGIN_DATA}/setup-state.json` và cờ `setup-pending.flag` trong tầng hook Rust/Python để phân biệt cùng tiến trình IDE hay đã khởi động lại thật sự sau lệnh `"setupfully tdq-workflow"`.
- Khi bật Caveman, `caveman_config.py` bọc `mcp_config.json` qua `sys.executable` thay vì Node launcher, và chưa tách `TAVILY_API_KEY` vào `secrets.env` riêng tư theo máy chủ đích.
- Chưa có trình nghiệm thu tự động 6 tầng chạy trên sandbox tạm độc lập trước khi xác nhận sẵn sàng.

## 2. Sau request (trạng thái/flow)

Toàn bộ kiến trúc Zero-to-Full cho Antigravity đã hoàn chỉnh, biên dịch sang `plugins/tdq-workflow-agy/` và đồng bộ trực tiếp lên máy thật:

- **Tầng Trạng thái & Bí mật (`scripts/tdq_setup_state.py`):** Lưu nguyên tử `setup-state.json` + `setup-pending.flag`, đo `Host Session Fingerprint` trên cây tiến trình gốc dưới `9 ms`, tự hết hạn TTL sau `24` giờ và cất khóa `TAVILY_API_KEY` vào `${PLUGIN_DATA}/secrets.env` (quyền `0600` / `icacls` fail-closed, nạp ngầm trong bộ nhớ, không echo ra stdout/log).
- **Bộ Bootstrap Cửa 0 & Pre-flight Probe (`scripts/tdq_setup_probe.mjs`, `scripts/bootstrap.ps1`, `scripts/bootstrap.sh`):** Kiểm kê đa hệ điều hành (`git`, `node`, `python`, `agy`, `agent-lsp`, `rtk`, `rg`, `chrome`, `archify`) dưới `0,5 giây`, kiểm URL repo GitHub chính thức, ép `TLS 1.2+`, và giữ quyền thực thi `100755` / LF sạch cho bản Unix.
- **Node Caveman Launcher & Tương thích ngược (`tools/patches/agy_launchers.py`, `scripts/caveman_config.py`, `plugins/tdq-workflow-agy/scripts/tdq_mcp_launcher.mjs`):** Mọi server bọc Caveman trên Antigravity giữ nguyên `"command": "node"`, `0` đường dẫn cá nhân, `0` `sys.executable`, chỉ truyền `TAVILY_API_KEY` cho máy chủ đích `tavily` và gỡ/bọc idempotent cả định dạng Antigravity lẫn Claude Code.
- **HostAdapter thuần Antigravity & Ghim `GEMINI.md` (`scripts/tdq_setup.py`, `scripts/tdq_lsp.py`, `scripts/setup_status.py`):** Cài đặt 1 chạm với `"setupfully tdq-workflow"` (`--setupfully`) hoặc bảng kê `/tdq-setup` (`--scan-json` → `--apply-manifest`), `claude_debt_count == 0`, tự ghim khối `TDQ:TOOLS` chuẩn Antigravity vào `~/.gemini/GEMINI.md` (`8.693` bytes `< 24.000` bytes), cài/kiểm Archify kèm kiểm remote `origin`, và tôn trọng `TDQ_KHONG_CHAM_MAY=1`.
- **Điểm móc Hook Rust + Python hậu Restart (`hooks/rust/tdq-dispatch/`, `hooks/scripts/prompt_context.py`, `hooks/scripts/session_start.py`, `tools/patches/agy_hooks.py`):** Đường nóng Rust kiểm cờ `setup-pending.flag` mức `O(1)` (`<= 9,56 ms` thực đo), lọc chặt `"setupfully tdq-workflow"` (từ chối câu hỏi, phủ định, trích dẫn, subagent và `compact`/`resume`/`system`), tự tiêm `[TDQ:SETUP]` + `user_markdown` kích hoạt `--post-restart-verify` đúng khi sang phiên IDE mới.
- **Trình Kiểm thử Giả lập 6 tầng (`scripts/tdq_simulate_verify.py`):** Chạy trọn vẹn `T1` (`agy plugin validate` + `probeToolchain`), `T2` (6 sự kiện hook `< 50 ms`), `T3` (JSON-RPC MCP `lsp` + `caveman`), `T4` (LSP `start_lsp`/`find_symbol` + `graphify`), `T5` (`rtk`/`rg` + dựng thử `Archify HTML`), `T6` (8 agents + subagent hook) trên sandbox tạm tự dọn sạch (`~8s`, bất biến `~/.gemini/config/`), xử lý an toàn giới hạn socket `AF_UNIX <= 107` byte của Windows.
- **Tài liệu & Đóng gói (`skills/tdq-setup/SKILL.md`, `skills/tdq-setup/references/zero-to-full-agy.md`, `tools/build_agy_plugin.py`, `tools/install_agy_plugin.py`, `README.md`, `README-Antigravity.md`):** Rút gọn `SKILL.md` xuống `50` dòng (`<= 132` dòng), khóa ngân sách `docs/tdq/token-budget.json`, biên dịch đồng bộ `plugins/tdq-workflow-agy/`, sao lưu sang `${PLUGIN_DATA}/backups/20261122-202028` và cài sống lên `~/.gemini/config/plugins/tdq-workflow-agy`.

## 3. Đã test gì

- Chạy kiểm chứng toàn repo sau lần sửa cuối: `py -3 -X utf8 scripts/tdq_test.py smoke-e2e --changed --workers auto --fresh --reuse off` (`417` cases), `py -3 -X utf8 scripts/tdq_test.py tron-bo --workers auto --fresh --reuse off` (`4846` cases trên `239` module) và `py -3 -X utf8 scripts/tdq_test.py so`.
- Chạy `cargo test --manifest-path hooks/rust/tdq-dispatch/Cargo.toml --quiet`, `agy.EXE plugin validate --strict --json`, `doc_lint.py`, `token_budget.py --kiem` và `i18n_check.py`.
- Chạy cài đặt thật và kiểm chứng sống `py -3 -X utf8 tools/install_agy_plugin.py --backup --with-rtk --with-caveman` + `py -3 -X utf8 scripts/tdq_setup.py --post-restart-verify --confirm-restarted --json` + `tdq_setup.py --scan-json` + gọi `mcp_tdq-workflow-agy_lsp` (`start_lsp`, `find_references`, `list_symbols`) và subagent `tdq-explorer`.
- Thực hiện kiểm định độc lập `ultra` ở 2 vai trò `tdq-security-reviewer` và `tdq-qc-tester`.

## 4. Kết quả test

- **`smoke-e2e --changed`:** `PASS` — `417 passed, 227 subtests passed in 90.22s` (`0` failed, `0` skipped).
- **`tron-bo` toàn kho (`239` module):** `PASS` — `4809 passed, 37 skipped, 2984 subtests passed in 305.08s` (`exit=0`, `321.31s` tổng runner); `tdq_test.py so`: `tron_bo=2/3`, `bo_sot=4` (4 module lệch bán kính ban đầu `test_agy_host_setup.py`, `test_cli_fixes_new01_28.py`, `test_hook_setup_resume.py`, `test_luat_gate_chat.py` đều đã chạy xanh trong `tron-bo` #2).
- **Rust & Cài đặt Live:** `cargo test` đạt `39 passed` (`0.07s`); `agy.EXE plugin validate --strict --json` đạt `0` findings (`8/6/3/10/12`) và `LIVE_VS_PKG_DIFFS: []`; `--post-restart-verify` đạt `status=verified`, `core_gate=PASS`, `temp_cleaned=true`, `config_untouched=true`, `elapsed_sec=7.926`.
- **Kiểm định Độc lập `ultra`:**
  - `tdq-security-reviewer` (vòng 3): `CONCLUSION: 0 security finding(s) · status: CLEAN`.
  - `tdq-qc-tester` (vòng 2): `VERDICT: PASS everything` (`Q1`–`Q8`, `QC-F3`, `QC-F4`: `PASS 100%`, `161/161` ca pytest setup/parity + `39/39` Rust + `0` defects).
  - Phiếu QC chính thức: [qc](../qc/2026-11-22-1521-trien-khai-setup-fully-agy.md) (`PASS toàn bộ`).

## Đầu ra

- **Mã nguồn & Bundle chính:** `scripts/tdq_setup_state.py`, `scripts/tdq_setup_probe.mjs`, `scripts/bootstrap.ps1`, `scripts/bootstrap.sh`, `scripts/caveman_config.py`, `scripts/tdq_setup.py`, `scripts/tdq_lsp.py`, `scripts/setup_status.py`, `scripts/tdq_simulate_verify.py`, `tools/patches/agy_launchers.py`, `tools/patches/agy_hooks.py`, `tools/build_agy_plugin.py`, `tools/install_agy_plugin.py`, `hooks/rust/tdq-dispatch/`, `hooks/scripts/{prompt_context,session_start}.py`, `skills/tdq-setup/`, `README.md`, `README-Antigravity.md`, `plugins/tdq-workflow-agy/`.
- **Kiểm thử & Hồ sơ:** `tests/test_{tdq_setup_state,bootstrap_probe,caveman_agy_launcher,caveman_setup,agy_host_setup,hook_setup_resume,tdq_simulate_verify,setup_bundle_e2e,setup_log_service}.py`, [brief](../brief/2026-11-22-1521-trien-khai-setup-fully-agy.md), [spec](../spec/2026-11-22-1521-trien-khai-setup-fully-agy.md), [plan](../plan/2026-11-22-1521-trien-khai-setup-fully-agy.md), [qc](../qc/2026-11-22-1521-trien-khai-setup-fully-agy.md) · **Archify HTML:** `docs/tdq/reports/2026-11-22-1521-trien-khai-setup-fully-agy.html`.
- **Giới hạn:**
  1. Máy kiểm thử chưa cấu hình khóa `TAVILY_API_KEY` thật nên nhánh `tavily-primary` trong `Optional Add-on Gate` trả `SKIPPED (skipped_no_key)` khi chạy thật (đã kiểm chứng logic bằng mock & `tdq_mcp_launcher.mjs` probe); các ca `37 skipped` trong `tron-bo` là kiểm thử đặc thù macOS/Linux trên Windows.
  2. `tdq_meta_gate.py` báo `3/4` do `i18n_check` quét toàn tệp di sản cũ ở `tdq_setup.py`, `tdq_lsp.py`, `setup_status.py`, `prompt_context.py`, `session_start.py` (`0` vi phạm ở toàn bộ `9` tệp mới và tài liệu tiếng Anh); nhánh `feature/trien-khai-setup-fully-agy` hiện có thay đổi chưa commit chờ bạn quyết định.
- **Lệch spec chờ duyệt:** không có
- **Git:** chưa commit (đang ở nhánh `feature/trien-khai-setup-fully-agy`, sẵn sàng hỏi người dùng để commit và hợp nhất về `dev`).

## Thời gian

```text
Request `2026-11-22-1521-trien-khai-setup-fully-agy` · lane full · opened at 2026-11-22T15:26:21+07:00

| Phase | Wall clock | Times entered |
|---|---|---|
| idle | 0s | 1 |
| analyze | 24 min | 1 |
| spec | 27 min | 1 |
| plan | 36 min | 1 |
| mode | 50s | 1 |
| implement | 2h 10min | 1 |
| qc | 1h 31min | 1 |
| report | 56s | 1 |
| Total | 5h 11min |  |

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

**Tóm tắt:** Triển khai trọn vẹn luồng `setupfully tdq-workflow` Zero-to-Full thuần Google Antigravity (`tdq_setup_state`, `bootstrap.{ps1,sh}`, `tdq_setup_probe.mjs`, Node Caveman launcher cô lập `TAVILY_API_KEY`, HostAdapter `0` nợ giả Claude, hook Rust+Python nối tiếp hậu restart và trình kiểm thử giả lập 6 tầng `tdq_simulate_verify`), đồng bộ `plugins/tdq-workflow-agy/` và cài kiểm chứng trên máy thật.
**Trước/Sau:** Xem báo cáo trực quan tại `docs/tdq/reports/2026-11-22-1521-trien-khai-setup-fully-agy.html` (bản xem trước spec tại `docs/tdq/spec/2026-11-22-1521-trien-khai-setup-fully-agy-preview.html`).
**Đã kiểm:**
- `py -3 -X utf8 scripts/tdq_test.py smoke-e2e --changed --workers auto --fresh --reuse off` → `417 passed, 227 subtests passed in 90.22s`
- `py -3 -X utf8 scripts/tdq_test.py tron-bo --workers auto --fresh --reuse off` → `4809 passed, 37 skipped, 2984 subtests passed in 305.08s` (`cases=4846`, exit `0`)
- `cargo test --manifest-path hooks/rust/tdq-dispatch/Cargo.toml --quiet` → `39 passed in 0.07s`
- `agy.EXE plugin validate plugins/tdq-workflow-agy --strict --json` & bản cài live → `0 findings` (`8/6/3/10/12`), `LIVE_VS_PKG_DIFFS: []`
- `py -3 -X utf8 scripts/tdq_setup.py --post-restart-verify --confirm-restarted --json` → `status=verified`, `core_gate=PASS`, `temp_cleaned=true`, `config_untouched=true` (`7.926s`)
**Rủi ro hồi quy:** Chạm vào luồng setup đa nền tảng, Caveman wrapper và hooks khởi động phiên; mọi đường cũ của Claude Code (`~/.claude.json`, proxy Python dự phòng, `legacy` test suites) được kiểm giữ nguyên qua `4.809` ca hồi quy toàn kho và `62` ca parity Rust/Python.
<!-- tdq-archify-binding:start -->
<!-- manifest: 2026-11-22-1521-trien-khai-setup-fully-agy.manifest.json -->
<!-- manifest_digest: f399ed68920faccdb468467f3b4ce6fc6db39c14ae7fd7450026326100c73bef -->
<!-- tdq-archify-binding:end -->