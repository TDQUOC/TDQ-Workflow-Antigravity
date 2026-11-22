# BÁO CÁO — Nhánh release Antigravity đa hệ điều hành và đồng bộ remote

Ngày: 2026-11-22 · Mã yêu cầu: 2026-11-22-1033-nhanh-release-agy-da-os (6/6 task + 2/2 fix QC tick đủ, Q1–Q6 PASS)
Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

> **Tóm tắt dễ hiểu:** Gói plugin Antigravity trước đây thiếu nhánh phát hành riêng trên GitHub và còn dính đường dẫn máy cá nhân Windows nên máy khác cài bị lỗi. Sau khi hoàn tất, kho đã có nhánh phát hành sạch đặt trực tiếp plugin ở thư mục gốc cùng cặp khởi chạy Node chạy đồng nhất trên Windows, macOS và Linux. Trọn bộ kiểm thử, kiểm định nghiêm ngặt Antigravity và lượt cài thử trực tiếp từ URL GitHub đều đạt xanh hoàn toàn. Nhánh phát triển và nhánh phát hành đã được đẩy đồng bộ lên kho GitHub từ xa.

## 1. Trước request (trạng thái/flow)

Trước khi thực thi, việc cài đặt TDQ Workflow trên máy Antigravity khác qua GitHub gặp ba rào cản lớn:
- Trên remote `origin`, nhánh mặc định `main` chỉ chứa bản Claude Code (`v0.98.0`), còn `origin/dev` tụt sau `dev` cục bộ và chứa toàn bộ `docs/`/`tests/`.
- `plugins/tdq-workflow-agy/mcp_config.json` đóng cứng đường dẫn cá nhân Windows `C:\Users\admin\.local\bin\agent-lsp.exe`, `npx.cmd` và `--userDataDir=C:/Users/admin/...` (lỗi trên máy khác user hoặc OS khác).
- `plugins/tdq-workflow-agy/hooks.json` đóng cứng `bin\tdq-dispatch.exe --event ...` và nhị phân Linux/macOS kẹt ở bản cũ `d74393da`, gây lỗi toàn bộ 6 lifecycle hooks trên macOS/Linux.

## 2. Sau request (trạng thái/flow)

Toàn bộ cấu hình, bộ đóng gói, nhị phân đa OS và quy trình sinh nhánh phát hành đã được nâng cấp và hợp nhất sạch về `dev`:

- **Cặp launcher Node đa hệ điều hành (`tools/patches/agy_launchers.py`):** Sinh ra `plugins/tdq-workflow-agy/scripts/tdq_hook_launcher.mjs` và `plugins/tdq-workflow-agy/scripts/tdq_mcp_launcher.mjs` (thuần Node stdlib, `0` dependency ngoài, `TDQ_LOG=0` tắt log `stderr`).
  - `hooks.json` chuyển hoàn toàn sang `node scripts/tdq_hook_launcher.mjs --event <Event>` (`0` dấu `"`, `0` chuỗi `.exe`), tự chọn nhị phân Rust theo `(platform, arch)`, tự đặt `chmod 0o755` trên POSIX, truyền `PLUGIN_ROOT`, và tự rơi về `dispatch.py` nếu thiếu nhị phân (bỏ qua stub `WindowsApps` trên Windows).
  - `mcp_config.json` chuyển hoàn toàn sang `"command": "node"`, `"args": ["${PLUGIN_ROOT}/scripts/tdq_mcp_launcher.mjs", ...]` và `--userDataDir=${PLUGIN_DATA}/chrome-devtools-profile` (`0` đường dẫn máy cá nhân `admin`, `0` `npx.cmd` trực tiếp).
- **Trình cài cục bộ & biên dịch sạch (`tools/patches/agy_manifests.py`, `tools/build_agy_plugin.py`, `tools/install_agy_plugin.py`, `install.py`):** Bỏ hẳn đường dẫn cứng `C:\Users\admin` khỏi `_EXTERNAL_UPSTREAM` và `generate_mcp_config`, giữ `--sync-local-mcp` cho tùy biến cục bộ khi cài tay, đồng bộ quy tắc Python đa OS trong `rules/AGENTS.md`.
- **Nhánh release riêng `release/antigravity` (`scripts/build_portable.py --sinh-release-agy`):** Dùng Git plumbing xuất bản cây `plugins/tdq-workflow-agy/` sạch (`198` tệp runtime, bỏ `__pycache__`, nâng quyền `100755` cho `bin/*` và `scripts/*.mjs`) trực tiếp tại gốc nhánh `release/antigravity` (`441435ce`, idempotent, không chạm `main`).
- **Đồng bộ nhị phân Rust & CI (`.github/workflows/build-rust-hooks.yml`, `README-Antigravity.md`):** Thêm target `x86_64-apple-darwin` vào workflow CI (đủ 4 target); biên dịch và chạy kiểm chứng trực tiếp qua SSH trên Ubuntu Linux `musl` (`tdq-dispatch-linux-x86_64`, `2472088` bytes) và macOS Apple Silicon (`tdq-dispatch-darwin-arm64`, `1895696` bytes) đồng bộ nguồn mới nhất `f1e7fcfb`.

## 3. Đã test gì

- Chạy trọn bộ kiểm thử đơn vị toàn repo sau vòng sửa QC `QC1.1`–`QC1.2`: `py -3 -X utf8 scripts/tdq_test.py tron-bo --workers auto --fresh --reuse off` trên đủ `231` module.
- Chạy kiểm định chính chủ Antigravity: `agy.EXE plugin validate plugins/tdq-workflow-agy --strict --json`.
- Chạy bộ kiểm thử riêng cho launcher, installer, nhánh release, live MCP JSON-RPC qua launcher và cài cô lập vào `HOME`/`USERPROFILE` tạm (`tests/test_agy_launchers.py`, `tests/test_agy_plugin_validate.py`, `tests/test_agy_release_e2e.py`, `tests/test_build_portable.py`, `tests/test_command_gate.py`, `tests/test_e2e_workflow.py`, `tests/test_ma_hoa_subprocess.py`).
- Chạy mô phỏng thực thi thật qua SSH trên máy Linux (`ubuntu-100-95`) và macOS (`mbair`) bằng nhị phân vừa build (`tests/test_remote_linux_simulation.py`, `tests/test_remote_mac_simulation.py`).

## 4. Kết quả test

- **`QC-F1` trọn bộ (`tron-bo`):** `PASS` — `4777` tests xanh (`skipped=36`, `0` fail trong `316.99s`), `tron_bo=2/3`, `radius misses=0`; `tdq_meta_gate` `PASS` trên toàn bộ tài liệu yêu cầu (`0` lỗi `doc_lint` và `git_co_author`).
- **Kiểm định Antigravity & cài cô lập (`Q1`–`Q4`):** `agy.EXE plugin validate --strict --json` trả `0 findings` (`12` skills, `8` agents, `10` rules, `3` mcpServers, `6` hooks); `tests/test_agy_release_e2e.py` clone nhánh `release/antigravity`, cài bằng `agy plugin install` vào môi trường cô lập thành công với mã thoát `0`, giữ nguyên `371` tệp ở `~/.gemini/config/`.
- **Kiểm chứng live MCP JSON-RPC (`test_e2e_workflow.py`) & `tdq_mcp_launcher.mjs`:** Đạt `9 passed` (`node ${PLUGIN_ROOT}/scripts/tdq_mcp_launcher.mjs lsp` bắt tay `initialize` + `tools/list` trả đủ tools thật).
- **Mô phỏng SSH Linux & macOS (`Q5`):** Đạt `3 passed in 8.34s` (`tests/test_agy_release_e2e.py`, `tests/test_remote_linux_simulation.py`, `tests/test_remote_mac_simulation.py`), magic bytes 3 nền tảng (`2 passed`).
- **Tài liệu, Archify HTML & đồng bộ `origin` (`Q6` PASS):** `doc_lint` đạt `0` lỗi trên trọn bộ `brief`, `spec`, `plan`, `qc`, `reports`; đã đẩy `dev` (`cba2bb37..6514db1e`) và tạo mới `origin/release/antigravity` (`441435ce`); kiểm thử cài sống `agy.EXE plugin install https://github.com/TDQUOC/TDQ-Workflow-Antigravity/tree/release/antigravity` trong `HOME` tạm đạt mã thoát `0` (`12` skills, `8` agents, `10` rules, `3` mcpServers, `6` hooks), kích hoạt `tdq_hook_launcher.mjs` thoát `0` và giữ nguyên `371` tệp `~/.gemini/config/`.

## Đầu ra

- **Tệp thay đổi chính:** `tools/patches/agy_launchers.py`, `tools/patches/agy_manifests.py`, `tools/build_agy_plugin.py`, `tools/install_agy_plugin.py`, `install.py`, `scripts/build_portable.py`, `.github/workflows/build-rust-hooks.yml`, `README-Antigravity.md`, `plugins/tdq-workflow-agy/`, `tests/test_{agy_launchers,agy_release_e2e,agy_plugin_validate,build_portable,command_gate,e2e_workflow}.py`.
- **Nhánh Git & remote `origin`:** `dev` (`6514db1e`) và `release/antigravity` (`441435ce`) đã đẩy đồng bộ lên `origin`; `main` giữ nguyên tại `91db3046`.
- **Tài liệu & Báo cáo:** [brief](../brief/2026-11-22-1033-nhanh-release-agy-da-os.md), [spec](../spec/2026-11-22-1033-nhanh-release-agy-da-os.md), [plan](../plan/2026-11-22-1033-nhanh-release-agy-da-os.md), [qc](../qc/2026-11-22-1033-nhanh-release-agy-da-os.md), **Archify HTML:** `docs/tdq/reports/2026-11-22-1033-nhanh-release-agy-da-os.html`.
- **Giới hạn:**
  1. Máy Intel Mac (`x86_64-apple-darwin`) không có sẵn runner nội bộ nên chưa build sẵn `tdq-dispatch-darwin-x64`; khi chạy trên Intel Mac, hook launcher sẽ tự fallback về `dispatch.py` cho tới khi CI GitHub Actions hoàn tất.
  2. Bản đồ kiến trúc tổng của repo (`docs/architecture/status.json`) báo stale ở tệp tiền tồn `agents/tdq-build-resolver.md`; `eval: chưa kích hoạt (opt-in)`.
- **Lệch spec chờ duyệt:** không có

## Thời gian

```text
Request `2026-11-22-1033-nhanh-release-agy-da-os` · lane full · opened at 2026-11-22T10:37:31+07:00

| Phase | Wall clock | Times entered |
|---|---|---|
| idle | 1s | 1 |
| analyze | 10 min | 1 |
| spec | 5 min | 1 |
| plan | 1h 51min | 1 |
| mode | 8 min | 1 |
| implement | 11 min | 1 |
| qc | 19 min | 1 |
| report | 28s | 1 |
| Total | 2h 44min |  |

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

**Tóm tắt:** Thêm nhánh phát hành sạch `release/antigravity` (`scripts/build_portable.py --sinh-release-agy`) cùng bộ đôi launcher Node.js đa hệ điều hành cho hooks và MCP (`tdq_hook_launcher.mjs`, `tdq_mcp_launcher.mjs`), khử toàn bộ đường dẫn cứng Windows (`C:\Users\admin`, `npx.cmd`, `bin\tdq-dispatch.exe`), mở rộng CI Rust 4 target và đồng bộ nhị phân Linux/macOS qua SSH.

**Trước/Sau:** Xem sơ đồ trực quan tại `docs/tdq/reports/2026-11-22-1033-nhanh-release-agy-da-os.html`.

**Đã kiểm:**
- `py -3 -X utf8 scripts/tdq_test.py tron-bo --workers auto --fresh --reuse off` → `4777 passed (skipped=36)`
- `agy.EXE plugin validate plugins/tdq-workflow-agy --strict --json` → `0 findings` (`12 skills, 8 agents, 10 rules, 3 mcpServers, 6 hooks`)
- `py -3 -X utf8 -m pytest tests/test_agy_release_e2e.py tests/test_remote_linux_simulation.py tests/test_remote_mac_simulation.py -v` → `3 passed` (giữ nguyên `371` tệp `~/.gemini/config/`)

**Rủi ro hồi quy:** Thấp — giữ nguyên hoàn toàn chữ ký và hành vi nhánh `main` của Claude Code cùng tùy chọn `--sync-local-mcp`; rủi ro duy nhất là thiếu nhị phân `tdq-dispatch-darwin-x64` trước lần chạy CI GitHub Actions kế tiếp và đã có fallback Python tự động.
<!-- tdq-archify-binding:start -->
<!-- manifest: 2026-11-22-1033-nhanh-release-agy-da-os.manifest.json -->
<!-- manifest_digest: 5eacba63fbf552500d997ff3cec5d75733424a298bcae1ef957fc4f790a76ad0 -->
<!-- tdq-archify-binding:end -->