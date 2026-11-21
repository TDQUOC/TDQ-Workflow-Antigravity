# QC — Sửa Lỗi Registry Tool 8 Subagent Antigravity, Build Rust 3 OS & Phát hành `0.103.1`

Ngày: 2026-11-21 · Spec: ../spec/2026-11-21-1253-fix-subagent-tools-bump.md · Plan: ../plan/2026-11-21-1253-fix-subagent-tools-bump.md · Vòng: 1 (`muc_qc=full`)
Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

| # | Hạng mục | Lệnh đã chạy | Kết quả | PASS/FAIL |
|---|---|---|---|---|
| T4.1 | Log service mặc định ISO (`TDQ_LOG=1` / unset) vs im lặng (`TDQ_LOG=0`) trên `build_agy_plugin.py`, `build_portable.py`, `tdq-dispatch.exe` & test `test_build_portable.py` + `test_rust_dispatch_parity.py` | Probe `TDQ_LOG` (unset/`1`/`0`) + `py -3 -X utf8 -m pytest tests/test_build_portable.py tests/test_rust_dispatch_parity.py -q` | Cả `3` công cụ đều exit `0`, có ISO timestamp trên `stderr` khi mặc định/`TDQ_LOG=1` và `stderr == ""` (`len=0`) khi `TDQ_LOG=0`; pytest `84 passed, 4 subtests passed in 78.85s` | PASS |
| T4.2 | Trọn bộ toàn repo `--workers 6 --fresh --reuse off`, `tdq_test.py so`, `token_budget.py --kiem`, `doc_lint.py`, hậu kiểm SSH `COUNT=0` & `cargo test` | `tron-bo --workers 6` (`task-12432`), `tdq_test.py so`, `token_budget.py --kiem`, `doc_lint.py`, `ssh_rust_build.py --verify-clean` (`ubuntu-100-95`, `mbair`), `cargo test` | `tron-bo` exit `0` (`PASS`, `4.605` passed, `36` skipped, `0` failed, `314.31s`, `bo_sot=0`, `details_complete=True`); `cargo test` `29` passed; `token_budget --kiem` & `doc_lint` `0` lỗi; `COUNT=0` trên cả `2` host SSH | PASS |
| Q1 | Vá `_READONLY_TOOLS` / `_WRITER_TOOLS`, `tdq-explorer.md` & test âm tính (`8/8` agents sạch tool cấm, không lặp `write_file`) | `py -3 -X utf8 -m pytest tests/test_agent_frontmatter.py -q` + quét `8/8` `agents/tdq-*.md` (`plugins/` & `~/.gemini/`) | `10 passed, 59 subtests`; `0/8` tool cấm & `0` lặp `write_file` (xác nhận độc lập `tdq-qc-tester` `d12387d8`) | PASS |
| Q2 | Manifest, `README.md`, `UPSTREAM-TRACE.md` & `CHANGELOG.md` (`<= 500` dòng) đồng bộ `0.103.1` | `pytest tests/test_docs_consistency.py tests/test_adapter_host.py -q` + `doc_lint.py` | `22 passed`; `0 violation(s)`; `CHANGELOG.md` `469/500` dòng (xác nhận độc lập `tdq-qc-tester` `d12387d8`) | PASS |
| Q3 | Crate Rust `0.103.1` & `3` nhị phân native thật (`Windows`, `Linux musl`, `macOS ARM64`), parity/lock, mô phỏng SSH & `2` máy SSH sạch `0` tàn dư | `cargo test/clippy`, `pytest` Rust/SSH (`49` pass + `test_rust_dispatch_parity.py` `46` cases), `ssh_rust_build.py --verify-clean` | `29` Cargo PASS, `0` warn, MZ/ELF/Mach-O khớp `0.103.1`, `COUNT=0` trên `ubuntu-100-95` & `mbair` (`d12387d8`) | PASS |
| Q4 | Compiler & gói plugin `plugins/tdq-workflow-agy/` (`v0.103.1`) đạt chuẩn nghiêm ngặt | `agy.EXE plugin validate plugins/tdq-workflow-agy --strict --json`, `token_budget.py --kiem`, build `--output tmp` | `findings: []`, exit `0`, parity `--output tmp` khớp `0.103.1` (`d12387d8`) | PASS |
| Q5 | Bộ kiểm thử toàn repo `muc_qc = full` (`--workers 6`) & QC độc lập | `py -3 -X utf8 scripts/tdq_test.py tron-bo --workers 6 --fresh --reuse off` + `tdq_test.py so` + `tdq-qc-tester` | `PASS` (`4.605` passed, `36` skipped, `0` failed, `314.31s`, `bo_sot=0`, `details_complete=True`) + biên bản `d12387d8` | PASS |
| Q6 | Cài Antigravity user-level `0.103.1` (`~/.gemini/`), kiểm gọi `invoke_subagent` & giữ nguyên `~/.claude/` | `py -3 -X utf8 install.py`, `agy.EXE plugin validate ~/.gemini/... --strict --json`, `agy.EXE plugin list`, `invoke_subagent(tdq-explorer)` (`4b121235`) | `0.103.1 enabled`, `findings: []`, `0/8` tool cấm, Caveman `3` MCP + `rtk 1.2.0` + `GEMINI.md` giữ nguyên, `~/.claude/` `mtime=1795000633.190871`, live probe `4b121235` PASS (`d12387d8`) | PASS |
| Q7 | Nhánh phát hành local `main` (`--sinh-main` từ `dev`) & annotated tag `v0.103.1` (không `git push`) | `build_portable.py --sinh-main --nguon dev --nhanh-dich main`, `git tag -a v0.103.1 main`, `git show main:.claude-plugin/plugin.json`, `git rev-parse main` | `dev@35a75e32` (`merge --no-ff`), `main@91db304635f142b457284d55accf82c28a813239` (`kept=190`, `version=0.103.1`), tag `v0.103.1` khớp `main` HEAD 40 ký tự, không `git push` | PASS |
| QC-F1 | Trọn bộ `tron-bo --workers 6 --fresh --reuse off` sau sửa code cuối | `tdq_test.py tron-bo --workers 6 --fresh --reuse off` (`receipt=908d60074c52418b9197d175329a8919`) | `PASS` · `4.605 passed, 36 skipped, 0 failed` trong `314.31s` (`details_complete=True`) | PASS |
| QC-F2 | Hồi quy vùng chạm theo mọi dòng `Chạm:` trong plan | `test_agent_frontmatter.py`, `test_docs_consistency.py`, `test_adapter_host.py`, `test_build_portable.py`, `test_rust_*`, `test_remote_*_simulation.py` | Toàn bộ vùng chạm PASS độc lập lẫn trong `tron-bo` (`0` failed) | PASS |
| QC-F3 | Ràng buộc kiến trúc phải giữ (Spec §5: `skills/` dùng chung, `CHANGELOG.md <= 500` dòng, `main` chỉ giữ phần lõi qua `--sinh-main`) | `git diff dev..HEAD -- skills/ scripts/ .agents/ .opencode/`, `rg` `hooks/`, đếm dòng `CHANGELOG.md` | `skills/` & `scripts/` diff=0; `hooks/` giữ nguyên `call_mcp_tool`/`grep_search`; `CHANGELOG.md` `469/500` dòng; `T5.2` chờ duyệt `"commit"` | PASS |
| QC-F4 | Clean Code Self-check (`clean-code.md`, `5` câu hỏi SOLID) | Rà `git diff dev..HEAD -- tools/ agents/ tests/ hooks/rust/tdq-dispatch/Cargo.toml` + `TDQ_LOG=1/0` + skill contracts | `5/5` câu hỏi SOLID Đạt; hợp đồng `6` skill (`migrate-agent-settings`, `tdq-checkportable`, `tdq-setup`, `agy-customizations`, `antigravity-guide`, `plugin`) khớp (`d12387d8`) | PASS |

---

## Bằng chứng

### T4.1 — Kiểm chứng Log Service (`TDQ_LOG=1` vs `TDQ_LOG=0`) & Bộ test Portable/Parity

#### 1. `tools/build_agy_plugin.py` (build ra thư mục tạm ngoài repo qua `--output <tmp>`)

- Lưu ý: cờ `--help` thoát ở bước phân tích tham số của `argparse` trước khi gọi `_log()` (`rc=0`, `stderr=''`, dòng đầu `usage: build_agy_plugin.py [-h] [--upstream UPSTREAM] [--output OUTPUT]`). Chạy build ra `TemporaryDirectory` ngoài repo kích hoạt `_log()` thật mà giữ worktree sạch `0` file bẩn:

```text
# TDQ_LOG unset (mặc định): rc=0, 4 dòng ISO trên stderr (1 dòng cargo build lần đầu + 3 dòng staged binary)
[2026-11-21T13:47:21] build_agy_plugin: building native windows binary via cargo build --release

# TDQ_LOG=1: rc=0, 3 dòng ISO trên stderr
[2026-11-21T13:48:36] build_agy_plugin: staged windows binary tdq-dispatch.exe from hooks\rust\tdq-dispatch\target\release\tdq-dispatch.exe
[2026-11-21T13:48:36] build_agy_plugin: staged linux binary tdq-dispatch-linux-x86_64 from plugins\tdq-workflow-agy\bin\tdq-dispatch-linux-x86_64
[2026-11-21T13:48:36] build_agy_plugin: staged darwin binary tdq-dispatch-darwin-arm64 from plugins\tdq-workflow-agy\bin\tdq-dispatch-darwin-arm64

# TDQ_LOG=0: rc=0, stderr rỗng hoàn toàn (len=0), stdout JSON status="OK"
```

#### 2. `scripts/build_portable.py --sinh-main --nguon HEAD --dry-run`

```text
# TDQ_LOG unset (mặc định): rc=0
[2026-11-21T13:47:41+07:00] build_portable: dry-run HEAD@74f953f -> main · kept=190 dropped=6976

# TDQ_LOG=1: rc=0
[2026-11-21T13:47:41+07:00] build_portable: dry-run HEAD@74f953f -> main · kept=190 dropped=6976

# TDQ_LOG=0: rc=0, stderr rỗng hoàn toàn (len=0)
```

#### 3. `plugins/tdq-workflow-agy/bin/tdq-dispatch.exe` (môi trường cô lập `TemporaryDirectory`)

- Chạy qua Python `subprocess.run` với `TDQ_PROJECT_DIR`, `HOME`, `USERPROFILE`, `GEMINI_CONFIG_DIR` trỏ vào `TemporaryDirectory` cô lập, `PLUGIN_ROOT=plugins/tdq-workflow-agy`, `TDQ_KHONG_CHAM_MAY=1`, `TDQ_KHOI_TAO_NEN=0`, `TDQ_RTK=0`, `RTK_DISABLED=1`:

```text
# Stdin EOF thuần (input="", mặc định SessionStart):
# - TDQ_LOG unset: rc=0, out_len=1169
[2026-11-21T13:48:52] rtk_integration: probe_rtk: verified rtk 1.2.0 at C:\Users\admin\.local\bin\rtk.EXE
[2026-11-21T13:48:52] session_start: SETUP-CAVEMAN opt-in disabled
[2026-11-21T13:48:52] dispatch event=SessionStart tool=- decision=inject ms=2187.3
[2026-11-21T06:48:52Z] tdq-dispatch: event=SessionStart route=cold sid=default ms=2277.09
# - TDQ_LOG=1: rc=0, out_len=865
[2026-11-21T13:48:52] dispatch event=SessionStart tool=- decision=inject ms=77.7
[2026-11-21T06:48:52Z] tdq-dispatch: event=SessionStart route=cold sid=default ms=162.68
# - TDQ_LOG=0: rc=0, stderr="" (len=0), out_len=865

# Stdin EOF với --event PostInvocation (hot path):
# - TDQ_LOG unset: rc=0, stderr=[2026-11-21T06:47:41Z] tdq-dispatch: event=PostInvocation route=hot sid=default ms=0.79, stdout={}
# - TDQ_LOG=1:     rc=0, stderr=[2026-11-21T06:47:41Z] tdq-dispatch: event=PostInvocation route=hot sid=default ms=0.24, stdout={}
# - TDQ_LOG=0:     rc=0, stderr="" (len=0), stdout={}

# Payload JSON mẫu {"cwd": "<tmp_repo>", "conversationId": "t41-probe"}:
# - PostInvocation TDQ_LOG=1: rc=0, stderr=[2026-11-21T06:47:41Z] tdq-dispatch: event=PostInvocation route=hot sid=t41-probe ms=0.25, stdout={}
# - PostInvocation TDQ_LOG=0: rc=0, stderr="" (len=0), stdout={}
# - SessionStart   TDQ_LOG=1: rc=0, stderr=[2026-11-21T13:47:44] dispatch ... + [2026-11-21T06:47:44Z] tdq-dispatch: event=SessionStart route=cold sid=t41-probe ms=149.84
# - SessionStart   TDQ_LOG=0: rc=0, stderr="" (len=0), stdout={"injectSteps": ...}
```

#### 4. Bộ test `tests/test_build_portable.py` & `tests/test_rust_dispatch_parity.py`

```text
py -3 -X utf8 -m pytest tests/test_build_portable.py tests/test_rust_dispatch_parity.py -q
.................................................................... [ 80%]
................                                                         [100%]
84 passed, 4 subtests passed in 78.85s (0:01:18)
```

### T4.2 — Trọn bộ toàn repo `--workers 6`, Cargo Test, Hygiene & SSH `COUNT=0`

- `py -3 -X utf8 scripts/tdq_test.py tron-bo --workers 6 --fresh --reuse off`:
  - Lần chạy 1 (`task-12326`): toàn bộ `4.641` cases chạy xong (`4.605 passed, 36 skipped, 0 failed`), nhưng bị `tdq_test.py` đánh dấu `INCOMPLETE` do kiểm tra `ruff check` chạy song song làm đổi `.ruff_cache/0.17.3/*` (`Source/environment changed during runner job`).
  - Lần chạy 2 sạch (`task-12432`, `receipt=908d60074c52418b9197d175329a8919`, SHA256 `37aff54fefd6516a849c585c3605c9ad544bb3d0a06fa2661ea998e094e5e7f8`): `exit_code=0`, `status=PASS`, `details_complete=True`, **`4.605 passed, 36 skipped, 0 failed`** trong `314.31s`.
- `py -3 -X utf8 scripts/tdq_test.py so`: `tron_bo=2`, `bo_sot=0`, `budget=3`, `radius misses: 0`.
- `cargo test --manifest-path hooks/rust/tdq-dispatch/Cargo.toml`: `25 passed` (`lib.rs`) + `4 passed` (`main.rs`) = `29 passed, 0 failed`.
- Hygiene & bất biến bản dựng:
  - `py -3 -X utf8 scripts/token_budget.py --kiem` → exit `0`.
  - `py -3 -X utf8 scripts/doc_lint.py CHANGELOG.md docs/tdq/spec/... docs/tdq/plan/... docs/tdq/qc/...` → `0 violation(s), exit 0` (`CHANGELOG.md` = `469/500` dòng).
  - `agy.EXE plugin validate plugins/tdq-workflow-agy --strict --json` → `findings: []` (`agents: 8, hooks: 6, mcpServers: 3, rules: 10, skills: 12`).
  - Quét `8/8` tệp `plugins/tdq-workflow-agy/agents/tdq-*.md`: `FORBIDDEN: {}`, `DUP_WRITE: {}`.
  - `hooks/`, `tools/patches/agy_hooks.py`, `plugins/tdq-workflow-agy/hooks/` giữ nguyên `47` dòng `call_mcp_tool|grep_search`; `skills/`, `scripts/`, `.agents/`, `.opencode/` có `0` diff so với `dev`.
  - `ssh_rust_build.py --host ubuntu-100-95 --verify-clean` → `COUNT=0`; `--host mbair --verify-clean` → `COUNT=0`.
  - Hash `3` nhị phân native hiện hành tại `plugins/tdq-workflow-agy/bin/`: `tdq-dispatch.exe` (`1,967,104` B, SHA256 `2f6524e04f8616bb12566aa52325fcfb42c03125db8078cd0afdec2941806736`), `tdq-dispatch-linux-x86_64` (`2,422,392` B, SHA256 `d34f6c73ff6ffbcac2d226aa580871d2a9ea7827874a308d35cd1c11912d8cb5`), `tdq-dispatch-darwin-arm64` (`1,845,856` B, SHA256 `76b06c26c635fd81113dec18f31b0c449ca82705c50a8dc8d704f597cfd0361f`).

### Q1
PASS (`tdq-qc-tester` `d12387d8`: `pytest tests/test_agent_frontmatter.py -q` → `10 passed, 59 subtests`; `8/8` tệp tại `plugins/tdq-workflow-agy/agents/tdq-*.md` và `~/.gemini/config/plugins/tdq-workflow-agy/agents/tdq-*.md` sạch `call_mcp_tool`, `grep_search`, `find_by_name`, `list_dir` và không lặp `write_file`).

### Q2
PASS (`tdq-qc-tester` `d12387d8`: `pytest tests/test_docs_consistency.py tests/test_adapter_host.py -q` → `22 passed`; `doc_lint.py` `0 violation(s)`; `CHANGELOG.md` `469/500` dòng đồng bộ `0.103.1`).

### Q3
PASS (`tdq-qc-tester` `d12387d8`: `cargo test` `29 passed`, `clippy` `0` warning, `pytest` Rust/SSH `49 passed` + `test_rust_dispatch_parity.py` `46` cases, `3` nhị phân PE `MZ`/ELF/Mach-O đúng `0.103.1`, `ssh_rust_build.py --verify-clean` `COUNT=0` trên `ubuntu-100-95` & `mbair`).

### Q4
PASS (`tdq-qc-tester` `d12387d8`: `agy.EXE plugin validate plugins/tdq-workflow-agy --strict --json` → `findings: []`; `token_budget.py --kiem` → exit `0`; kiểm build `--output tmp` khớp `0.103.1`).

### Q5
PASS (`tdq-qc-tester` `d12387d8`: `tdq_test.py so` + `result.json` `908d60074c52418b9197d175329a8919` → `PASS`, `4.605` passed, `36` skipped, `0` failed, `bo_sot=0`, `details_complete=True`).

### T5.1 & Q6 — Cài user-level `~/.gemini/` (`0.103.1`), bảo toàn Caveman/RTK & `~/.claude/`, kiểm gọi live `tdq-explorer`

- Trước cài (`0.103.0`): `PRE_T51_FORBIDDEN=8` (`8/8` tệp tại `C:\Users\admin\.gemini\config\plugins\tdq-workflow-agy\agents\tdq-*.md` còn `call_mcp_tool`), `CLAUDE_MTIME=1795000633.190871`.
- Chạy `py -3 -X utf8 install.py`: cài `253` tệp ra `C:\Users\admin\.gemini\config\plugins\tdq-workflow-agy`, giữ nguyên `rtk (1.2.0) & rg ready` và `Caveman MCP shrink active (wrapped: lsp, chrome-devtools, tavily-primary)`.
- Hậu kiểm `~/.gemini/` & `~/.claude/`:
  - `agy.EXE plugin validate C:\Users\admin\.gemini\config\plugins\tdq-workflow-agy --strict --json` → `findings: []` (`agents: 8, hooks: 6, mcpServers: 3, rules: 10, skills: 12`).
  - `agy.EXE plugin list` → `tdq-workflow-agy (enabled, 0.103.1)`.
  - `VER: 0.103.1 AGENTS: 8 FORBIDDEN: {} DUPS: {} MCP_SHRINK: {'lsp': True, 'chrome-devtools': True, 'tavily-primary': True} GEMINI_MD: (True, 9376) CLAUDE_MTIME: 1795000633.190871`.
- Thử thực tế `invoke_subagent(TypeName="tdq-explorer", Role="Live 0.103.1 Subagent Probe")` (`4b121235-1734-476f-8de1-d3fc46e1edc2`): khởi tạo registry sạch không crash (`read_file` dòng 1-20 và `send_message` trả kết quả tức thì ngay trong phiên đang mở: `frontmatter tools: [read_file, edit_file, write_file, run_command, manage_task, search_web, send_message]`).

### Q6
PASS (`tdq-qc-tester` `d12387d8` xác nhận độc lập toàn bộ `agy validate/list`, `mcp_config.json` Caveman 3 server, `GEMINI.md`, `~/.claude/` `mtime=1795000633.190871` & live probe `4b121235`).

### Q7
PASS (đã chạy `T5.2`: commit `13e52f20`, merge `--no-ff` về `dev@35a75e32`, xóa nhánh `bugfix/fix-subagent-tools-bump`, chạy `py -3 -X utf8 scripts/build_portable.py --sinh-main --nguon dev --nhanh-dich main` → `main@91db304635f142b457284d55accf82c28a813239` với `kept=190` / `version=0.103.1`, gắn annotated tag `v0.103.1` khớp `main` HEAD 40 ký tự; chỉ local, không `git push`).

### QC-F1
PASS (`tron-bo --workers 6 --fresh --reuse off` sau sửa code cuối đạt `4.605 passed, 36 skipped, 0 failed` trong `314.31s`, `bo_sot=0`, `details_complete=True`).

### QC-F2
PASS (mọi module vùng chạm theo `Chạm:` trong plan — `test_agent_frontmatter.py`, `test_docs_consistency.py`, `test_adapter_host.py`, `test_build_portable.py`, `test_rust_dispatch_parity.py`, `test_rust_lock_safety.py`, `test_remote_linux_simulation.py`, `test_remote_mac_simulation.py` — đều PASS độc lập lẫn trong `tron-bo`).

### QC-F3
PASS (`git diff dev..HEAD -- skills/ scripts/ .agents/ .opencode/` rỗng giữ nguyên `skills/` dùng chung; `hooks/`, `agy_hooks.py`, `plugins/tdq-workflow-agy/hooks/` giữ nguyên `call_mcp_tool` & `grep_search`; `CHANGELOG.md` `469/500` dòng; `main` qua `--sinh-main` giữ sang `T5.2`).

### QC-F4
PASS (`5/5` câu hỏi SOLID Đạt theo đối chiếu của `tdq-qc-tester` `d12387d8`: (S) mỗi sửa đổi gọn `1` trách nhiệm tại `_READONLY_TOOLS`/`_WRITER_TOOLS`, `tdq-explorer.md`, test âm tính & manifest; (O) `AGY_ALLOWED_TOOLS`/`AGY_FORBIDDEN_TOOLS` mở rộng qua hằng số không sửa logic lõi; (L) toàn bộ `8` subagent giữ hợp đồng `model: inherit` & chia read-only vs writer nhất quán; (I) tách sạch tool danh sách subagent với tool hook của agent chính; (D) phụ thuộc cấu hình qua `AGENT_FRONTMATTERS` & `Cargo.toml`, kèm `TDQ_LOG=1/0` và hợp đồng `6` skill khớp).

### Ghi nhận phụ từ QC độc lập (`d12387d8`)
- Low (không chặn phát hành): `README.md:4,237` hiện vẫn ghi badge/chữ `4602 passed` (`4.602 passed`) trong khi thực đo `tron-bo` bản `0.103.1` tăng lên `4.605 passed` do thêm negative test `test_agent_frontmatter.py` (`T4.2` chủ động không sửa `README.md` sau `tron-bo` để giữ sạch receipt; `test_docs_consistency.py` vẫn PASS `22 passed`).

---

## Lệch spec chờ duyệt

Không có (`tdq_state.py lech list` → `0 item(s), 0 pending`).

## Kết luận

PASS (`Q1`–`Q7` & `QC-F1`–`QC-F4` ĐẠT trọn vẹn `muc_qc=full`: `4.605 passed` / `0 failed`, `29` Cargo pass trên `3` OS + `COUNT=0` SSH, `~/.gemini/` chạy `0.103.1` với `invoke_subagent(tdq-explorer)` PASS, `dev@35a75e32` và `main@91db3046` + tag `v0.103.1` local).
