# REPORT — Bump Version `0.103.0`, Build 3-OS Rust, Release `main` & Cập nhật Antigravity Local (`2026-11-21-1034-bump-version-release-local` · lane full · mode main · `8/9` task xong, `T5.2` chờ commit)

Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

> **Tóm tắt nhanh:** Trước đây nhánh `dev` ghi phiên bản `0.102.0` dù đã gộp `3` đợt nâng cấp lớn (`4 trụ cột agent`, `investigate V2`, `trình bày ngắn gọn`), `CHANGELOG.md` đã chạm `480/500` dòng, nhị phân Rust 3 OS và bản plugin live `~/.gemini/` dừng ở `0.101.0`, còn máy Ubuntu test dư thư mục build cũ. Sau khi thực hiện, toàn bộ manifest, crate Rust, `3` nhị phân native thật (`Windows`, `Linux musl`, `macOS ARM64`) và gói `plugins/tdq-workflow-agy/` đã đồng bộ lên `0.103.0`, `CHANGELOG.md` rút gọn còn `461` dòng, `2` máy SSH `ubuntu-100-95` và `mbair` dọn sạch `0` tàn dư, bản Antigravity user-level `~/.gemini/` + `GEMINI.md` đã nâng cấp lên `0.103.0` (giữ nguyên Caveman/RTK và không chạm `~/.claude/`), và trọn bộ `222` module vượt qua **PASS** (`4.603 passed, 36 skipped, 0 failed`). Chỉ còn `T5.2` (`--sinh-main` từ `dev` + tag local `v0.103.0`) sẵn sàng chạy ngay sau khi bạn chốt `"commit"`.

**Trước request (trạng thái/flow):** Phiên bản bị lệch qua `4` tầng: `.claude-plugin/plugin.json`, `.codex-plugin/plugin.json`, `README.md`, `UPSTREAM-TRACE.md` và `tools/patches/agy_manifests.py` ghi `0.102.0` nhưng thiếu release notes cho `3` đợt sau `0.102.0`; `CHANGELOG.md` dài `480/500` dòng; `hooks/rust/tdq-dispatch/Cargo.toml` và plugin user-level `C:\Users\admin\.gemini\config\plugins\tdq-workflow-agy` dừng ở `0.101.0` (hai nhị phân Linux/macOS mốc `11/19`, máy `ubuntu-100-95` còn sót `/home/ubuntu/tdq-dispatch` và `/tmp/tdq_dispatch.tar.gz`); `C:\Users\admin\.gemini\GEMINI.md` thiếu dòng chuẩn trình bày mặc định `Mặc định cho cả spec, plan và report...`; còn nhánh `main` ở `v0.100.0` và tag mới nhất là `v0.99.0`.

**Sau request (trạng thái/flow):**
- **Đồng bộ `0.103.0` & tách archive (`M1`):** Chuyển `0.61.0`–`0.60.0` từ `CHANGELOG.md` sang đầu [docs/CHANGELOG-archive-3.md](../../CHANGELOG-archive-3.md) (`110` dòng), chèn mục `## 0.103.0 — 2026-11-21` đưa `CHANGELOG.md` về `461` dòng; nâng `.claude-plugin/plugin.json`, `.codex-plugin/plugin.json`, [README.md](../../../README.md) (`0.103.0`, badge `4602 passed`, `scripts/ (73)`) và [UPSTREAM-TRACE.md](../../../UPSTREAM-TRACE.md) (`Release Tag: v0.103.0`).
- **Biên dịch Rust `0.103.0` thật trên 3 OS & dọn sạch SSH (`M2`):** Nâng `Cargo.toml` lên `0.103.0`, build và test thành công trên Windows (`tdq-dispatch.exe`), Ubuntu qua SSH `ubuntu-100-95` (`tdq-dispatch-linux-x86_64` static `musl`) và macOS qua SSH `mbair` (`tdq-dispatch-darwin-arm64` Mach-O), đồng thời dọn sạch `100%` thư mục build tạm và tàn dư cũ (`/home/ubuntu/tdq-dispatch`, `/tmp/tdq_dispatch.tar.gz`).
- **Đóng gói plugin AGY repo (`M3`):** Nâng compiler (`tools/patches/agy_manifests.py`, `tools/patches/__init__.py`, `tools/build_agy_plugin.py`), thêm test khóa `test_v2_version_synced_with_claude_plugin` (`tests/test_agy_plugin_validate.py:244-256`) và build lại [plugins/tdq-workflow-agy](../../../plugins/tdq-workflow-agy/manifest.json) (`253` tệp, `"upstream_sha": "c3b2a0a3"`).
- **Cập nhật Antigravity User-Level riêng lẻ (`M4`):** Chạy `install.py` cài `253` tệp `0.103.0` ra `C:\Users\admin\.gemini\config\plugins\tdq-workflow-agy` (giữ nguyên bọc Caveman `tdq_mcp_shrink.py` cho `lsp`, `chrome-devtools`, `tavily-primary` và `rtk 1.2.0`) và cập nhật `C:\Users\admin\.gemini\GEMINI.md` (giữ nguyên tool Antigravity `start_lsp`/`/plan`/`ask_question`, Tailscale Serve và mục `Ngôn ngữ trong chat`, không chạm `~/.claude/` hay `~/.codex/`).
- **Xuất bản local `main` & tag `v0.103.0` (`M5` / `T5.2`):** Đã kiểm khô `build_portable.py --sinh-main --nguon HEAD --dry-run` (`kept=190 dropped=6944`), chờ bạn chốt `"commit"` để commit trên `chore/bump-version-release-local`, merge `--no-ff` về `dev`, sinh nhánh local `main` và gắn annotated tag `v0.103.0` (tuyệt đối không `git push`).

**Đã test gì:** Chạy chu trình Red → Green ở `T3.1`, kiểm nhất quán tài liệu & adapter 4 nền tảng, `doc_lint.py`, `token_budget.py --kiem`, `cargo test` trên Windows/Ubuntu/macOS, `cargo clippy --all-targets -- -D warnings`, parity & lock đa tiến trình Rust, mô phỏng SSH Linux & macOS, hậu kiểm SSH cleanup `0` file sót, kiểm `TDQ_LOG=1` vs `TDQ_LOG=0`, kiểm kiến trúc `docs/kien-truc.md`, `py_compile`, `agy.EXE plugin validate --strict --json` cả trong repo lẫn bản cài `~/.gemini/`, chạy trọn bộ `py -3 -X utf8 scripts/tdq_test.py tron-bo --workers 1 --fresh --reuse off` (`222` module) và cử subagent độc lập `tdq-qc-tester` đối soát `Q1`–`Q5`.

**Kết quả test:**
- Trọn bộ `scripts/tdq_test.py tron-bo`: **PASS** `4.603 passed, 36 skipped, 2.892 subtests passed in 1332.27s (0:22:12)` (`tests_run=4.639`, `0` failed, `tron_bo=1/2`, `bo_sot=0`).
- Rust 3 OS (`Q2`) & SSH cleanup (`Q3`): `cargo test` đạt `29 passed` trên mỗi hệ điều hành (Windows `0.06s`, Linux `0.05s`, macOS `0.07s`), `cargo clippy` `0` warning, `test_remote_linux_simulation.py` `1 passed`, `test_remote_mac_simulation.py` `1 passed`, `test_build_portable.py` + `test_rust_dispatch_parity.py` `84 passed, 4 subtests passed`, SSH `ubuntu-100-95` & `mbair` cùng trả `0` tệp sót.
- Tài liệu, AGY plugin & User-Level (`Q1`, `Q4`, `Q7`, `QC-F2..F4`): `test_docs_consistency` + `test_adapter_host` `22 passed, 24 subtests`; `test_agy_plugin_validate` + parity/lock `55 passed`; `test_kien_truc` + `muc_qc` + `approve` `29 passed, 23 subtests`; `doc_lint.py` `0` lỗi (`CHANGELOG.md` `461` dòng, `archive-3` `110` dòng); `token_budget.py --kiem` `0` lỗi; `agy.EXE plugin validate --strict --json` đạt `findings: []` ở cả repo lẫn `~/.gemini/` (`tdq-workflow-agy enabled, 0.103.0`); `~/.claude/plugins/installed_plugins.json` giữ nguyên `mtime 2026-11-18T18:17:13.1908711+07:00`; `tdq-qc-tester` (`37328511`) xác nhận `VERDICT: PASS everything` cho `Q1`–`Q5`.

**Đầu ra:**
- Manifest & Tài liệu `0.103.0`: [.claude-plugin/plugin.json](../../../.claude-plugin/plugin.json), [.codex-plugin/plugin.json](../../../.codex-plugin/plugin.json), [CHANGELOG.md](../../../CHANGELOG.md), [docs/CHANGELOG-archive-3.md](../../CHANGELOG-archive-3.md), [README.md](../../../README.md), [UPSTREAM-TRACE.md](../../../UPSTREAM-TRACE.md).
- Rust 3 OS & Compiler AGY: [Cargo.toml](../../../hooks/rust/tdq-dispatch/Cargo.toml), [Cargo.lock](../../../hooks/rust/tdq-dispatch/Cargo.lock), `plugins/tdq-workflow-agy/bin/{tdq-dispatch.exe,tdq-dispatch-linux-x86_64,tdq-dispatch-darwin-arm64}`, [tools/patches/agy_manifests.py](../../../tools/patches/agy_manifests.py), [tools/patches/__init__.py](../../../tools/patches/__init__.py), [tools/build_agy_plugin.py](../../../tools/build_agy_plugin.py), [plugins/tdq-workflow-agy/manifest.json](../../../plugins/tdq-workflow-agy/manifest.json), [tests/test_agy_plugin_validate.py](../../../tests/test_agy_plugin_validate.py).
- User-Level Antigravity (ngoài git repo): `C:\Users\admin\.gemini\config\plugins\tdq-workflow-agy` (`253` tệp, Caveman 3 server + `0.103.0` enabled) và [GEMINI.md](file:///C:/Users/admin/.gemini/GEMINI.md).
- Hồ sơ QC & Kế hoạch: [2026-11-21-1034-bump-version-release-local.md](../qc/2026-11-21-1034-bump-version-release-local.md), [plan](../plan/2026-11-21-1034-bump-version-release-local.md).

**Archify HTML:**
- Báo cáo trực quan: [2026-11-21-1034-bump-version-release-local.html](2026-11-21-1034-bump-version-release-local.html)
- Tailscale Serve URL: https://unity-pc-rtx3060.tail99896.ts.net/vlog/tdq-workflow-agy/reports/2026-11-21-1034-bump-version-release-local.html
- Biểu đồ nguồn: [bao-cao.archify.md](../artifacts/2026-11-21-1034-bump-version-release-local/bao-cao.archify.md)

**Giới hạn:**
- **Cổng commit trước khi xuất `main` (`T5.2` / `Q6`):** Chưa chạy `build_portable.py --sinh-main --nguon dev --nhanh-dich main` và `git tag v0.103.0` vì `sinh_nhanh_main` đọc cây đã commit của `dev` và quy tắc TDQ cấm tự commit trước khi bạn chốt `"commit"`; thao tác này sẽ chạy ngay lập tức ngay khi bạn xác nhận `"commit"`.
- **Áp dụng `--bo-qua-lsp` khi khởi tạo request:** `ly_do`: `"Rung 8 python:. truot do tham chieu noi tep generate_manifest_and_readme tai tools/patches/agy_manifests.py:258; da bat start_lsp va find_symbol binh thuong"` · `module`: `["python:. → TRUOT (\`generate_manifest_and_readme\`: 1 tham chiếu LSP so với 1 lần trong file định nghĩa — LSP không thấy tham chiếu từ file khác)"]`.
- **Lỗi pre-existing ở frontmatter agent AGY (từ `0.102.0`, ngoài phạm vi bump version):** `tdq-qc-tester` & thực nghiệm runtime ghi nhận `tools/patches/skills_and_agents.py:28-47` khai báo `call_mcp_tool`, `grep_search`, `find_by_name`, `list_dir` trong `plugins/tdq-workflow-agy/agents/tdq-*.md` (khi gọi trực tiếp agent chưa cache như `tdq-security-reviewer`, Antigravity runtime báo `unknown component: tool "call_mcp_tool" not found in registry`, còn `tdq-explorer.md` lặp `write_file`). Không tự sửa ngoài spec trong đợt phát hành này; nên mở 1 task fix riêng ngay sau release.
- **Công cụ hệ thống & chênh `1` test `README.md`:** Máy chưa cài `ruff` (`ruff: not checked yet`, đã kiểm thay thế bằng `cargo clippy` và `py_compile`); `README.md` giữ `4602 passed` (mốc nền `dev` trước khi thêm `1` test khóa `test_v2_version_synced_with_claude_plugin` ở `T3.1`, còn thực chạy sau sửa là `4.603 passed`).

**Lệch spec chờ duyệt:** không có

**Git:** Chưa commit trên nhánh `chore/bump-version-release-local` (mở từ `dev` @ `c3b2a0a3`); chờ xác nhận `"commit"` để commit, merge `--no-ff` vào `dev`, sinh local `main` + tag `v0.103.0` (chưa push).

## Thời gian

Request `2026-11-21-1034-bump-version-release-local` · lane full · opened at 2026-11-21T10:37:04+07:00

| Phase | Wall clock | API request | Tool wait | Background job | Observed union | Unattributed | Times entered |
|---|---|---|---|---|---|---|---|
| idle | 20s | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | 1 |
| analyze | 7 min | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | 1 |
| spec | 4 min | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | 1 |
| plan | 5 min | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | 1 |
| mode | 36s | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | 1 |
| implement | 43 min | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | 1 |
| qc | 1 min | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | 1 |
| report | 1s | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | 1 |
| Total | 1h 01min | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] |  |

Model compute time is unavailable (`model_giay=null`). API includes network/provider latency; tool time is host wait. Observed metrics may overlap; unattributed time is not assumed user/model time.
Transcript attribution: project_window. Complete covers selected supported observations only.
- api_request_seconds: no_usable_source
- tool_call_seconds: no_usable_source
- background_job_seconds: no_usable_source
- observed_union_seconds: no_usable_observations
- unattributed_seconds: wall_minus_observed_union;no_usable_observations

## Agent Role Telemetry

| Role | Runs | First pass | Rate | Retries | Avg elapsed | Models |
|---|---|---|---|---|---|---|
| self | 7 | 7 | 100% | 0 | — | — |
| tdq-qc-tester | 6 | 6 | 100% | 0 | — | — |
| tdq-implementer | 2 | 2 | 100% | 0 | — | — |

## Thân PR (soạn sẵn)

```markdown
## Summary
- Bump TDQ-Workflow version to `0.103.0` across manifests, docs (`README.md`, `UPSTREAM-TRACE.md`), compiler patches (`tools/patches/agy_manifests.py`, `tools/build_agy_plugin.py`), and Rust dispatcher crate (`hooks/rust/tdq-dispatch/Cargo.toml`), while archiving `0.60.0`–`0.61.0` to `docs/CHANGELOG-archive-3.md` (`CHANGELOG.md` 461 lines).
- Natively compile and test `tdq-dispatch` `0.103.0` across Windows, Linux (`ubuntu-100-95` static musl), and macOS (`mbair` ARM64 Mach-O), leaving `0` leftovers on SSH test hosts and packaging `plugins/tdq-workflow-agy/` (`253` files, `0` strict validation findings).
- Sync Google Antigravity user-level installation (`~/.gemini/config/plugins/tdq-workflow-agy` with Caveman MCP shrink + `rtk` preserved, plus `~/.gemini/GEMINI.md`) without modifying `~/.claude/` or `~/.codex/`, and prepare local `main` + tag `v0.103.0` release via `--sinh-main`.

## Test plan
- [x] `py -3 -X utf8 scripts/tdq_test.py tron-bo --workers 1 --fresh --reuse off` → `4,603 passed, 36 skipped, 2,892 subtests passed` (`0` failed, `bo_sot=0`)
- [x] `cargo test --manifest-path hooks/rust/tdq-dispatch/Cargo.toml` (`29 passed` each on Windows, Linux, macOS) + `cargo clippy --all-targets -- -D warnings` (`0` warnings) + SSH simulation tests (`test_remote_linux_simulation.py`, `test_remote_mac_simulation.py` PASS) & `0` SSH leftovers verified
- [x] `agy.EXE plugin validate plugins/tdq-workflow-agy --strict --json` & `agy.EXE plugin validate C:\Users\admin\.gemini\config\plugins\tdq-workflow-agy --strict --json` → `findings: []` (`0.103.0` enabled), `doc_lint.py` (`0` violations), `token_budget.py --kiem` (`exit 0`)
```
<!-- tdq-archify-binding:start -->
<!-- manifest: 2026-11-21-1034-bump-version-release-local.manifest.json -->
<!-- manifest_digest: 9113a159c8bac4917aed45a1cf334d8d064de28336ebd6e62851185e47578a8d -->
<!-- tdq-archify-binding:end -->