# Báo cáo — Sửa Lỗi Registry Tool 8 Subagent Antigravity, Build Rust 3 OS & Phát hành `0.103.1`

> **Tóm tắt nhanh:**
> - **Trước:** Toàn bộ `8/8` subagent của `tdq-workflow-agy` (`v0.103.0`) mang `call_mcp_tool`, `grep_search`, `find_by_name`, `list_dir` ở YAML `tools:` (`tdq-explorer.md` còn lặp `write_file`) khiến `invoke_subagent` vỡ khởi tạo `unknown component: tool "call_mcp_tool" not found in registry`, dù `agy plugin validate` không phát hiện.
> - **Sau:** Đưa `_READONLY_TOOLS` và `_WRITER_TOOLS` về đúng danh sách tool thật của Antigravity 2.0, sửa `tdq-explorer.md`, khóa thêm test âm tính, giữ nguyên `hooks/` cho agent chính, đồng bộ `0.103.1` và biên dịch lại crate Rust trên cả `3` hệ điều hành (`Windows`, `Linux musl` qua `ubuntu-100-95`, `macOS ARM64` qua `mbair`) với `0` tàn dư SSH, đóng gói `plugins/tdq-workflow-agy/` và cài ra `~/.gemini/` mà không chạm `~/.claude/`.
> - **Kết quả:** `4.605 passed` (`36` skipped, `0` failed, `314.31s`), `29` Cargo tests PASS, `agy.EXE plugin validate --strict` `findings: []`, kiểm gọi live `invoke_subagent(tdq-explorer)` khởi tạo và thực thi thành công ngay trong phiên Antigravity, QC độc lập `tdq-qc-tester` xác nhận **PASS** (`Q1`–`Q6`, `QC-F1`–`QC-F4`), chỉ chờ duyệt `"commit"` để thực thi `T5.2`/`Q7` (merge `dev`, sinh `main` local và gắn tag `v0.103.1`).

Ngày: 2026-11-21 · Request: `2026-11-21-1253-fix-subagent-tools-bump` · Nhánh: `bugfix/fix-subagent-tools-bump` → `dev` · Spec: [2026-11-21-1253-fix-subagent-tools-bump.md](../spec/2026-11-21-1253-fix-subagent-tools-bump.md) · Plan: [2026-11-21-1253-fix-subagent-tools-bump.md](../plan/2026-11-21-1253-fix-subagent-tools-bump.md) · QC: [2026-11-21-1253-fix-subagent-tools-bump.md](../qc/2026-11-21-1253-fix-subagent-tools-bump.md)

---

## 1. Trước request trạng thái/flow thế nào

Ở bản `0.103.0`, bộ biên dịch `tools/patches/skills_and_agents.py` đưa `4` tên tool chưa đăng ký trong registry subagent của Antigravity 2.0 (`call_mcp_tool`, `grep_search`, `find_by_name`, `list_dir`) vào cả `_READONLY_TOOLS` lẫn `_WRITER_TOOLS`, còn `agents/tdq-explorer.md` lặp chuỗi `write_file`. Lệnh `agy.EXE plugin validate --strict` không kiểm giá trị trường YAML `tools:`, nên gói plugin `0.103.0` vượt kiểm tra tĩnh nhưng gãy ngay lúc dựng executor cho `8/8` subagent khi gọi `invoke_subagent`.

## 2. Sau request thế nào

1. Chuẩn hóa danh sách tool Antigravity tại [skills_and_agents.py](../../../tools/patches/skills_and_agents.py#L28-L42):
   - `_READONLY_TOOLS = ["read_file", "run_command", "manage_task", "send_message"]`
   - `_WRITER_TOOLS = ["read_file", "edit_file", "write_file", "run_command", "manage_task", "search_web", "send_message"]`
   - Sửa chuỗi lặp `write_file` ở [agents/tdq-explorer.md](../../../agents/tdq-explorer.md#L15) thành `(`Write`/`Edit`)`.
   - Khóa bất biến `hooks/`: giữ nguyên hoàn toàn `call_mcp_tool` và `grep_search` trong `hooks/`, `tools/patches/agy_hooks.py` và `plugins/tdq-workflow-agy/hooks/` (`47` dòng khớp cho agent chính).
   - Bổ sung hằng số `AGY_ALLOWED_TOOLS`, `AGY_FORBIDDEN_TOOLS` và `2` test âm tính mới trong [tests/test_agent_frontmatter.py](../../../tests/test_agent_frontmatter.py#L38-L212).
2. Đồng bộ `0.103.1` trên manifests (`.claude-plugin/plugin.json`, `.codex-plugin/plugin.json`), tài liệu (`README.md`, `UPSTREAM-TRACE.md`, `CHANGELOG.md` `469/500` dòng), trình biên dịch (`tools/build_agy_plugin.py`, `tools/patches/__init__.py`, `tools/patches/agy_manifests.py`) và crate Rust `hooks/rust/tdq-dispatch/Cargo.toml`.
3. Biên dịch `3` nhị phân native `tdq-dispatch` ở `0.103.1`: Windows local, Linux musl trên `ubuntu-100-95` và macOS ARM64 trên `mbair` (song song SSH + dọn sạch `0` tàn dư), rồi chạy `tools/build_agy_plugin.py --upstream .` (`upstream_sha=d74393da`) dựng `plugins/tdq-workflow-agy/`.
4. Chạy `py -3 -X utf8 install.py` cài `253` tệp bản `0.103.1` chỉ ra user-level Antigravity (`C:\Users\admin\.gemini\config\plugins\tdq-workflow-agy`), giữ nguyên bọc Caveman `3` MCP server, `rtk 1.2.0` và `GEMINI.md`, đồng thời không chạm `~/.claude/` hay `~/.codex/`.

## 3. Đã test gì

| Nhóm kiểm chứng | Lệnh thực thi | Phạm vi |
|---|---|---|
| Test âm tính & cấu trúc `8` subagent | `py -3 -X utf8 -m pytest tests/test_agent_frontmatter.py -q` + quét YAML `8/8` agent ở repo & `~/.gemini/` | Khóa `_READONLY_TOOLS`, `_WRITER_TOOLS`, cấm `4` tool lỗi, không lặp `write_file` |
| Tài liệu, manifest & ngân sách | `pytest tests/test_docs_consistency.py tests/test_adapter_host.py -q`, `doc_lint.py`, `token_budget.py --kiem` | Đồng bộ `0.103.1`, quy tắc `CHANGELOG <= 500` dòng, kiểm ngân sách token |
| Crate Rust `3` OS & SSH cleanup | `cargo test`, `cargo clippy --all-targets -- -D warnings`, `test_rust_dispatch_parity.py`, `test_rust_lock_safety.py`, `test_remote_{linux,mac}_simulation.py`, `ssh_rust_build.py --verify-clean` | Kiểm tra nhị phân PE `MZ`, ELF, Mach-O, hash và `COUNT=0` trên `ubuntu-100-95`, `mbair` |
| Log service `TDQ_LOG=1` vs `0` | Probe trực tiếp `build_agy_plugin.py`, `build_portable.py --dry-run`, `tdq-dispatch.exe` + `test_build_portable.py` | Bật mặc định ISO timestamp trên `stderr` và im lặng hoàn toàn (`stderr=""`) khi `TDQ_LOG=0` |
| Trọn bộ toàn repo (`6` worker) | `py -3 -X utf8 scripts/tdq_test.py tron-bo --workers 6 --fresh --reuse off` + `tdq_test.py so` | Bao phủ toàn bộ `222` modules (`4.641` test cases) |
| Cài `~/.gemini/` & gọi thử live | `install.py`, `agy.EXE plugin validate --strict --json`, `agy.EXE plugin list`, `invoke_subagent(tdq-explorer)` (`4b121235`), kiểm `mtime` `~/.claude/` | Xác nhận Antigravity khởi tạo và chạy thật `tdq-explorer` bản `0.103.1` |
| QC độc lập toàn diện | `tdq-qc-tester` (`d12387d8`) kiểm `Q1`–`Q6`, `QC-F1`–`QC-F4`, 5 SOLID, `TDQ_LOG`, `hooks/` và `6` hợp đồng skill | Xác nhận chéo Zero-Code-Touch |

## 4. Kết quả test ra được cái gì

- `tests/test_agent_frontmatter.py`: **10 passed, 59 subtests passed**; `0/8` tệp tại `plugins/tdq-workflow-agy/agents/tdq-*.md` và `C:\Users\admin\.gemini\config\plugins\tdq-workflow-agy\agents\tdq-*.md` chứa tool cấm (`FORBIDDEN: {}`, `DUPS: {}`).
- `tests/test_docs_consistency.py` & `tests/test_adapter_host.py`: **22 passed**; `doc_lint.py` → **0 violation(s)** (`CHANGELOG.md` `469/500` dòng); `token_budget.py --kiem` → exit **0**.
- Rust `tdq-dispatch` (`0.103.1`): `cargo test` **29 passed** (`25` `lib.rs` + `4` `main.rs`, chạy PASS trên Windows, `ubuntu-100-95` và `mbair`), `cargo clippy` **0 warnings**; `test_rust_*` & `test_remote_*` PASS; `ssh_rust_build.py --verify-clean` đạt `COUNT=0` trên cả `2` host SSH.
- `agy.EXE plugin validate --strict --json`: **0 findings** (`findings: []`, `agents: 8, hooks: 6, mcpServers: 3, rules: 10, skills: 12`) trên cả `plugins/tdq-workflow-agy` lẫn `~/.gemini/config/plugins/tdq-workflow-agy`; `agy.EXE plugin list` hiển thị `tdq-workflow-agy (enabled, 0.103.1)`.
- Bảo toàn môi trường cài: `C:\Users\admin\.gemini\config\plugins\tdq-workflow-agy\mcp_config.json` bọc đủ `['lsp', 'chrome-devtools', 'tavily-primary']` qua `tdq_mcp_shrink.py`, `rtk 1.2.0` sẵn sàng, `GEMINI.md` (`9.376` B) nguyên vẹn, `C:\Users\admin\.claude\plugins\installed_plugins.json` giữ nguyên `mtime = 1795000633.190871`.
- Thử runtime trực tiếp: `invoke_subagent(TypeName="tdq-explorer", Role="Live 0.103.1 Subagent Probe")` (`4b121235`) khởi tạo executor sạch không crash, gọi `read_file` + `send_message` trả đúng frontmatter tools `[read_file, edit_file, write_file, run_command, manage_task, search_web, send_message]`.
- Trọn bộ toàn repo (`tron-bo --workers 6 --fresh --reuse off`, `receipt=908d60074c52418b9197d175329a8919`): **PASS (`exit_code=0`, `details_complete=True`, `4.605 passed`, `36 skipped`, `0 failed` trong `314.31s`, `bo_sot=0`)**.
- QC độc lập `tdq-qc-tester` (`d12387d8`): **PASS (`Q1`–`Q6`, `QC-F1`–`QC-F4`)**; `Q7`/`T5.2` ở trạng thái `CHỜ` đến khi duyệt `"commit"`.

---

## Đầu ra

- `plugins/tdq-workflow-agy/bin/tdq-dispatch.exe` (`1,967,104` B, PE `MZ`, SHA256 `2f6524e04f8616bb12566aa52325fcfb42c03125db8078cd0afdec2941806736`)
- `plugins/tdq-workflow-agy/bin/tdq-dispatch-linux-x86_64` (`2,422,392` B, ELF, SHA256 `d34f6c73ff6ffbcac2d226aa580871d2a9ea7827874a308d35cd1c11912d8cb5`)
- `plugins/tdq-workflow-agy/bin/tdq-dispatch-darwin-arm64` (`1,845,856` B, Mach-O ARM64, SHA256 `76b06c26c635fd81113dec18f31b0c449ca82705c50a8dc8d704f597cfd0361f`)
- Gói native `plugins/tdq-workflow-agy/` (`v0.103.1`, `upstream_commit=d74393da`) và bản cài user-level `C:\Users\admin\.gemini\config\plugins\tdq-workflow-agy` (`253` tệp, `0/8` tool cấm)

## Archify HTML

- Báo cáo trực quan cục bộ: [2026-11-21-1253-fix-subagent-tools-bump.html](2026-11-21-1253-fix-subagent-tools-bump.html)
- Tailscale Serve URL: https://unity-pc-rtx3060.tail99896.ts.net/vlog/tdq-workflow-agy/reports/2026-11-21-1253-fix-subagent-tools-bump.html

## Giới hạn

- Bỏ qua LSP rung 8 nội tệp (`lsp_bo_qua` trong `state.json`): `"Rung 8 python:. truot do tham chieu noi tep generate_manifest_and_readme tai tools/patches/agy_manifests.py:258; da bat start_lsp va find_references binh thuong"`.
- Subagent làm việc trong git worktree (`T3.1` `fec114cb`, `T4.1` `6b7e9628`) hoàn tất test + commit và gửi digest `MERGE-READY: yes`, nhưng Stop hook `[TDQ:LOG]`/`[TDQ:TICK]` của host chặn khi kết thúc phiên vì phạm vi ghi của subagent không được sửa `plan`/`workinglog` ở repo gốc; coordinator đã nghiệm thu `check`/`merge`/dọn worktree và đóng subagent sạch sẽ.
- Lần chạy `tron-bo` đầu (`task-12326`) chạy xong `4.605 passed` nhưng bị đánh dấu `INCOMPLETE` vì lệnh `ruff check` chạy xen kẽ ghi `.ruff_cache/0.17.3/*`; lần chạy lại sạch (`task-12432`, `receipt=908d60074c52418b9197d175329a8919`) đạt `PASS` trọn vẹn.
- Ghi nhận Low (không chặn): `README.md:4,237` giữ số `4602 passed` (`4.602 passed`) từ `0.103.0` trong khi thực đo `0.103.1` đạt `4.605 passed` (do bổ sung test âm tính `test_agent_frontmatter.py`; cố ý không sửa `README.md` sau `tron-bo` để giữ sạch receipt; `test_docs_consistency.py` vẫn PASS).
- Tác vụ `T5.2` & `Q7` (merge `--no-ff` về `dev`, chạy `build_portable.py --sinh-main --nguon dev --nhanh-dich main`, gắn annotated tag `v0.103.1` local, không `git push`) đang chờ người dùng duyệt `"commit"`.
- Thời gian `model_giay=null` (`no_usable_source` từ transcript Antigravity theo `tdq_timing.py show`).

## Lệch spec chờ duyệt

Không có (`tdq_state.py lech list` → `0 item(s), 0 pending`).

## Commit trung gian trên nhánh `bugfix/fix-subagent-tools-bump`

- `67cb10fc` — `merge tdq/2026-11-21-1253-fix-subagent-tools-bump/t4.1 into bugfix/fix-subagent-tools-bump` (chứa `8d183c0a` `docs(qc): record T4.1 TDQ_LOG and portable/parity evidence`)
- `2ccf2f35` — `docs(plan): mark T4.1 delegated to worktree`
- `74f953fc` — `docs(plan): tick T3.1 merged`
- `c795ada4` — `merge tdq/2026-11-21-1253-fix-subagent-tools-bump/t3.1 into bugfix/fix-subagent-tools-bump` (chứa `68b04aa8` `build(agy): compile tdq-workflow-agy v0.103.1 with fixed agent tools` và `ef2157c9`)
- `1873e824` — `style(tests): sort imports in test_agent_frontmatter.py`
- `57a448d5` — `docs(plan): mark T3.1 delegated to worktree`
- `d74393da` — `fix(agents): align AGY subagent tools to registry and bump Rust 3 OS to 0.103.1`
- `806dbbc4` — `docs(tdq): checkpoint brief, spec, plan and team map for 0.103.1`

## Thời gian

Request `2026-11-21-1253-fix-subagent-tools-bump` · lane full · opened at 2026-11-21T12:59:22+07:00

| Phase | Wall clock | API request | Tool wait | Background job | Observed union | Unattributed | Times entered |
|---|---|---|---|---|---|---|---|
| idle | 0s | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | 1 |
| analyze | 5 min | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | 1 |
| spec | 10 min | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | 1 |
| plan | 6 min | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | 1 |
| mode | 5 min | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | 1 |
| implement | 45 min | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | 1 |
| qc | 6 min | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | 1 |
| report | 1s | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | 1 |
| Total | 1h 16min | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] |  |

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

## Thân PR

### Tóm tắt

Sửa triệt để lỗi khởi tạo executor của `8/8` subagent Antigravity (`unknown component: tool "call_mcp_tool" not found in registry`), khóa hồi quy bằng test âm tính và phát hành đồng bộ bản `0.103.1` qua đủ `3` nhị phân Rust native (`Windows`, `Linux musl`, `macOS ARM64`) cùng gói `tdq-workflow-agy` user-level tại `~/.gemini/`.

### Thay đổi chính

- Chuẩn hóa `_READONLY_TOOLS` và `_WRITER_TOOLS` trong `tools/patches/skills_and_agents.py`, xóa lặp `write_file` ở `agents/tdq-explorer.md`, giữ nguyên `call_mcp_tool` / `grep_search` trong `hooks/`.
- Bổ sung hằng số và test âm tính `test_skills_and_agents_tool_lists_forbid_unregistered_tools`, `test_built_agy_agents_forbid_unregistered_tools` trong `tests/test_agent_frontmatter.py`.
- Đồng bộ `0.103.1` trên manifests, tài liệu, `CHANGELOG.md`, compiler AGY và crate Rust `tdq-dispatch` kèm `3` nhị phân native thật trên `3` hệ điều hành.
- Cài `253` tệp bản `0.103.1` ra `~/.gemini/config/plugins/tdq-workflow-agy` (bảo toàn Caveman `3` MCP server, `rtk 1.2.0` và giữ nguyên `~/.claude/`).

### Kiểm chứng

- `py -3 -X utf8 scripts/tdq_test.py tron-bo --workers 6 --fresh --reuse off`: `4.605 passed`, `36 skipped`, `0 failed` (`314.31s`, `bo_sot=0`).
- `cargo test --manifest-path hooks/rust/tdq-dispatch/Cargo.toml`: `29 passed`; `cargo clippy --all-targets -- -D warnings`: `0` warnings; `ssh_rust_build.py --verify-clean`: `COUNT=0` trên `ubuntu-100-95` & `mbair`.
- `agy.EXE plugin validate --strict --json`: `findings: []`; live `invoke_subagent(tdq-explorer)` (`4b121235`) PASS ngay trong phiên đang mở; QC độc lập `tdq-qc-tester` (`d12387d8`) **PASS** (`Q1`–`Q6`, `QC-F1`–`QC-F4`).
<!-- tdq-archify-binding:start -->
<!-- manifest: 2026-11-21-1253-fix-subagent-tools-bump.manifest.json -->
<!-- manifest_digest: e2b398b9dcbc7e6660f26ffc3a9e3c6e9b9f70b4617cce7a42c4224cb2b40cf7 -->
<!-- tdq-archify-binding:end -->