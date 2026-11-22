# BÁO CÁO — Nghiên cứu và thiết kế quy trình setup zero-to-full từ máy trống kèm tự động kiểm chứng sau restart

Ngày: 2026-11-22 · Mã yêu cầu: 2026-11-22-1424-phan-tich-setup-may-trong (6/6 task tick đủ)
Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

> **Tóm tắt dễ hiểu:** Bộ cài đặt hiện tại vẫn trỏ nhiều đường dẫn cũ của Claude Code, chưa dựng môi trường gốc trên máy mới tinh và thiếu lưu vết qua lúc khởi động lại. Đợt nghiên cứu đã kiểm toán toàn bộ mã nguồn, tài liệu chính thức của Antigravity và chạy thử nghiệm cô lập không chạm cấu hình thật. Bản đề xuất thiết kế hai cửa vào cho máy trống, duyệt một lần, tự đối chiếu dấu phiên sau khởi động lại và giả lập sáu tầng trên thư mục tạm. Toàn bộ bằng chứng đã khóa sạch trong hồ sơ nghiên cứu, không chỉnh sửa mã nguồn sản phẩm.

## 1. Trước request (trạng thái/flow)

Trước khi thực hiện nghiên cứu, quy trình `tdq-setup` khi đưa sang một máy Antigravity mới tinh gặp 4 rào cản lớn:

- **Lệch đường dẫn nền tảng (`[EV-B01]`–`[EV-B03]`, `[EV-B08]`):** `scripts/tdq_setup.py`, `scripts/tdq_lsp.py`, `scripts/setup_status.py`, `scripts/tdq_devtool_mcp.py` và `skills/tdq-setup/SKILL.md` vẫn trỏ nhiều tệp của Claude Code (`~/.claude.json`, `~/.claude/settings.json`, `~/.claude/CLAUDE.md`) và đường dẫn cũ `~/.gemini/antigravity/mcp_config.json`, chưa bám chuẩn thật `~/.gemini/config/` và `~/.gemini/antigravity-cli/settings.json`.
- **Chưa bao phủ máy trống tinh & bẫy `WindowsApps` / `sudo` / Sandbox (`[EV-A06]`, `[EV-C03]`):** Máy mới chưa có `Git`, `Node.js`, `Python 3` hoặc `uv` không thể tự chạy `tdq_setup.py` hay tải plugin; Antigravity Terminal Sandbox mặc định cũng chặn mạng và ghi ngoài workspace.
- **Add-ons phân mảnh & lỗi portable (`[EV-B04]`, `[EV-B06]`):** `caveman_config.py` ghi đè `"command": sys.executable` làm hỏng launcher Node đa OS trong `mcp_config.json`; `tavily-primary` chưa có đường nạp API key mềm ngoài cơ chế `"variables"` (vốn khiến `agy plugin install` tắt plugin cho tới khi điền đủ biến `[EV-A04]`).
- **Mất dấu qua Restart & thiếu Simulate Test độc lập (`[EV-C01]`, `[EV-C02]`, `[EV-C04]`):** Chưa có tệp trạng thái bền vững qua lần khởi động lại IDE, chưa phân biệt mở chat mới với restart thật, và chưa có bài giả lập tự dựng dự án tạm để kiểm tra toàn trình trên kho trống.

## 2. Sau request (trạng thái/flow)

Đã hoàn thành trọn vẹn bản Thiết kế Kiến trúc (`Blueprint v2`) lưu tại [research/2026-11-22-1424-phan-tich-setup-may-trong.md](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/research/2026-11-22-1424-phan-tich-setup-may-trong.md) với `20` bằng chứng `Verified` và `1` phân tích `Inferred`, gồm 4 trụ cột đề xuất:

- **Trụ cột 1 (`1a`) — Dual-Entry Bootstrap đa OS không đòi quyền Admin (`[EV-A07]`, `[EV-A08]`):**
  - *Cửa 0 (ngoài terminal):* `scripts/bootstrap.ps1` / `scripts/bootstrap.sh` dựng `Git`, `Node.js` LTS (`winget` / `fnm` / `brew`), `uv` + `Python 3` thực (`uv python install --default`, tránh stub `WindowsApps`), cài `agy` CLI và cài plugin `release/antigravity`.
  - *Cửa 1 (`tdq-setup`):* tự dò thiếu runtime ngay từ đầu (có fallback Node), vá `PATH` ngay trong phiên chạy để gom hết cài đặt về **đúng 1 lần Restart duy nhất** ở cuối Pha 1.
- **Trụ cột 2 (`2a`) — One-Shot Manifest Consent, Add-ons & Chuyển chuẩn Antigravity (`[EV-B01]`–`[EV-B06]`):**
  - Quét 1 lần (`--scan-json`) → trình bày 1 bảng kê duy nhất → user duyệt 1 lần → cài tuần tự toàn bộ Core + Add-ons (chỉ xin phép chạy ngoài sandbox 1 lần nếu Terminal Sandbox đang bật `[EV-A06]`).
  - Bổ sung mode `"caveman"` vào `tdq_mcp_launcher.mjs` để bọc `tdq_mcp_shrink.py` hoàn toàn bằng Node launcher đa OS (sửa lỗi `sys.executable` `[EV-B04]`); nạp mềm `TAVILY_API_KEY` qua `${PLUGIN_DATA}/secrets.env` (`0600`) hoặc đánh dấu `skipped_no_key` không khóa plugin `[EV-B06]`; tái sử dụng `rtk_integration.py` cho `rtk`/`rg` `[EV-B05]` và đồng bộ `HostAdapter` Antigravity cho `tdq_setup`, `tdq_lsp`, `setup_status`, `tdq_devtool_mcp`.
- **Trụ cột 3 (`3a`) — State Machine tại `${PLUGIN_DATA}` & Hook Auto-Resume (`[EV-A04]`, `[EV-B07]`, `[EV-C01]`, `[EV-C02]`):**
  - Lưu trạng thái vào `${PLUGIN_DATA}/setup-state.json` (fallback `<ANTIGRAVITY_APP_DATA_DIR>/plugin_data/tdq-workflow-agy/`) kèm cờ rỗng `setup-pending.flag`.
  - `PreInvocation` trong `tdq-dispatch` Rust và Python fallback chỉ mất `1` phép `stat()` (`< 0.05 ms`) ở lượt thường; chỉ khi có `setup-pending.flag` mới đo `Host Session Fingerprint` (`ancestor_pid + created_at + ANTIGRAVITY_LS_ADDRESS`, `< 2 ms`), tự phát `[TDQ:SETUP-RESUME]` ngay khi thấy tiến trình Antigravity mới sau restart thật và khóa chống chạy nhầm nếu người dùng chỉ mở tab mới.
- **Trụ cột 4 (`4a`) — Bộ `Simulate Test` 6 tầng trên Sandbox tạm (`[EV-C03]`, `[EV-C04]`):**
  - Chạy qua `--post-restart-verify` trên `TemporaryDirectory` tự xóa: (1) `agy plugin validate --strict --json` + quyền `+x`, (2) bắn thật 6 events qua `tdq_hook_launcher.mjs`, (3) bắt tay MCP stdio sống dùng `Popen` giữ `stdin` mở `[EV-C04]`, (4) probe thật `rg` + `agent-lsp` + `graphify` trên 2 file `.py`/`.js` tạm, (5) kiểm `rtk` + `caveman` + rule size `<= 24KB`, (6) probe subagent + MCP namespace. Phân rạch rõ `Core Gate` vs `Optional Add-on Gate`.
- **Lộ trình triển khai kế tiếp:** Đề xuất 4 đợt tách gọn (`Đợt B1` State & HostAdapter → `Đợt B2` Bootstrap & Launcher đa OS → `Đợt B3` Hook `PreInvocation` Auto-Resume → `Đợt B4` `tdq_simulate_verify.py` & `SKILL.md` + test cô lập).

## 3. Đã test gì

- Thu thập và lưu trữ 10 trang tài liệu chính thức từ `https://antigravity.google/docs/` (`plugins.md`, `hooks.md`, `mcp.md`, `cli/reference.md`, `rules.md`, `build-plugins.md`, `settings.md`, `install.md`, `getting-started.md`, `sandbox.md`) và các built-in skills (`antigravity-guide`, `plugin`, `agy-customizations`).
- Chạy thực nghiệm cô lập kiểm tra cây `Win32_Process` (`ppid` + `CreationDate` + biến môi trường `ANTIGRAVITY_*`), kiểm tra cấu trúc đĩa `~/.gemini/` (tìm ra đường dẫn thật `plugin_data`), và chạy thử khung `Sandbox Simulate` trong `TemporaryDirectory` (`agy plugin validate --strict --json`, `tdq_hook_launcher.mjs PreInvocation`, `tdq_mcp_launcher.mjs lsp`).
- Kiểm toán sâu toàn bộ mã nguồn setup, add-ons, installers và `tdq-dispatch` Rust/Python; đối chiếu trích dẫn `[EV-xxx]` và kiểm tra `doc_lint.py` cùng ranh giới sạch Git.

## 4. Kết quả test

- **`T1.1` (Vòng đời Antigravity & Bootstrap 3 OS):** `PASS` (`8` bằng chứng `EV-A01`–`EV-A08`, xác nhận quy tắc `PLUGIN_DATA`, `settings.json`, `Terminal Sandbox`, `uv python install --default` và `fnm`).
- **`T1.2` (Thực nghiệm cô lập dấu phiên & khung Sandbox):** `PASS` (`4` bằng chứng `EV-C01`–`EV-C04`, xác định cây `language_server.exe (23192) -> Antigravity.exe (9872)`, `validate_ec=0` `189.8ms`, `hook_preinv_ec=0` `267.1ms`, tìm ra cơ chế giữ `stdin` mở cho `agent-lsp` `Popen` và bảo toàn nguyên vẹn `371 == 371` tệp `~/.gemini/config/`).
- **`T2.1` (Kiểm toán mã nguồn nội bộ):** `PASS` (`8` bằng chứng `EV-B01`–`EV-B08`, chỉ chính xác `path:line` của toàn bộ điểm lệch `~/.claude*`, bug `caveman_config.py:189` và đường nóng `pre_invocation.rs:189-224`).
- **`T3.1` & `T4.1` (Hợp nhất sổ bằng chứng, Blueprint & Kiểm tra tổng hợp):** `PASS` (`20/20` bằng chứng hợp nhất vào `evidence.jsonl`, `0` trích dẫn mồ côi, `0` đường dẫn sai, `0` lỗi `doc_lint.py`, `0` tệp chạm ngoài `docs/tdq/` + `docs/workinglog/`).

## Đầu ra

- **Sổ bằng chứng & shard:** `docs/tdq/artifacts/2026-11-22-1424-phan-tich-setup-may-trong/{evidence.jsonl,axis-a-lifecycle-os.*,axis-b-code-audit.*,axis-c-probes.*,raw/*,bao-cao.archify.md,verify-summary.md}`
- **Hồ sơ thiết kế kiến trúc (Blueprint v2):** [research/2026-11-22-1424-phan-tich-setup-may-trong.md](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/research/2026-11-22-1424-phan-tich-setup-may-trong.md)
- **Tài liệu quy trình & QC:** [brief](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/brief/2026-11-22-1424-phan-tich-setup-may-trong.md), [spec](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/spec/2026-11-22-1424-phan-tich-setup-may-trong.md), [plan](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/plan/2026-11-22-1424-phan-tich-setup-may-trong.md), [phiếu QC](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/qc/2026-11-22-1424-phan-tich-setup-may-trong.md)
- **Archify HTML:** `docs/tdq/reports/2026-11-22-1424-phan-tich-setup-may-trong.html`
- **Giới hạn:** Request đang ở chế độ nghiên cứu và đề xuất (`work_kind=investigate`), chưa viết code triển khai thật (`scripts/`, `hooks/`, `skills/`); phép đo cây tiến trình cha `EV-C01` thực hiện trực tiếp trên Windows 11, còn hành vi cây `/proc/<pid>/stat` (Linux) và `ps` (macOS) được suy luận chuẩn POSIX và cần test trực tiếp qua SSH/VM khi sang pha `build`. `eval: chưa kích hoạt (opt-in)`.
- **Lệch spec chờ duyệt:** không có
- **Git:** Nhánh `docs/phan-tich-setup-may-trong` (tách từ `dev`), chỉ chứa tài liệu/bằng chứng mới trong `docs/tdq/` và `docs/workinglog/`.

## Thời gian

```text
Request `2026-11-22-1424-phan-tich-setup-may-trong` · lane full · opened at 2026-11-22T14:41:28+07:00

| Phase | Wall clock | Times entered |
|---|---|---|
| idle | 0s | 1 |
| analyze | 12 min | 1 |
| spec | 2 min | 1 |
| plan | 5 min | 1 |
| mode | 32s | 1 |
| implement | 12 min | 1 |
| qc | 1 min | 1 |
| report | 15s | 1 |
| Total | 34 min |  |

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

**Tóm tắt:** Nghiên cứu và đề xuất kiến trúc quy trình `tdq-setup` v2 hỗ trợ máy mới tinh đa hệ điều hành (`Windows`, `macOS`, `Linux`) theo mô hình hai cửa vào, duyệt trọn gói một lần (bao gồm Core + `RTK` + `Caveman` + `Chrome DevTools` + `Tavily`), lưu vết qua lúc khởi động lại Antigravity bằng `${PLUGIN_DATA}/setup-state.json` + `Host Session Fingerprint` trên hook `PreInvocation`, và tự động chạy bộ kiểm thử giả lập 6 tầng trên sandbox tạm.

**Trước/Sau:** Xem sơ đồ trực quan tại `docs/tdq/reports/2026-11-22-1424-phan-tich-setup-may-trong.html`.

**Đã kiểm:**
- Thu thập `20` bằng chứng xác thực từ tài liệu sống Antigravity, kiểm toán mã nguồn nội bộ và thử nghiệm cô lập `TEMP` (bảo toàn 100% `371` tệp `~/.gemini/config/`)
- Đối chiếu toàn vẹn `evidence.jsonl`, phản biện `4` góc khuất counterfactual (`QC-I1`–`QC-I4`), `doc_lint.py` `0` lỗi và `git diff` không chạm ngoài `docs/tdq/`

**Rủi ro hồi quy:** Không có rủi ro hồi quy mã nguồn vì yêu cầu thuộc `work_kind=investigate`, hoàn toàn không chỉnh sửa mã sản phẩm, cấu hình `~/.gemini/` hay nhánh `main`/`release/antigravity`.
<!-- tdq-archify-binding:start -->
<!-- manifest: 2026-11-22-1424-phan-tich-setup-may-trong.manifest.json -->
<!-- manifest_digest: 40b84421f5527b19cf3fba887d1debba23fec27983c5726fe77cebcb3bdce7d3 -->
<!-- tdq-archify-binding:end -->