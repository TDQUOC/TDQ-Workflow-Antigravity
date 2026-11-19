# PLAN — Triển khai Kiến trúc Hook Hybrid 2 tầng + Smart Hardening (P0 + P1 + P2)

Ngày: 2026-11-19 · Spec: ../spec/2026-11-19-1632-hybrid-hook-smart-hardening.md (bản 1.0, ĐÃ DUYỆT) · Lane: full
Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md
Mode thực thi: subagent — mô phỏng trên thực đo cho thấy chia 4 đợt song song (giao 5 task, leader giữ 5) nhanh hơn inline 8,1 phút ở hệ số agent 1,5x (12,3 vs 20,4 phút). (ĐỀ XUẤT, user chốt lúc duyệt)
Trạng thái plan: ĐÃ DUYỆT

## Mục lục

- Quy tắc thi hành (áp cho mọi task)
- Thiết kế Trước vs Sau
- P1 — Tầng Core Rust: Schema AGY 2.0, Runtime Dir thống nhất & Hybrid Router
- P2 — Tầng Hot-path Rust, Python Smart Hardening & Multi-OS Build Guard
- P3 — Build 3 OS (Windows + SSH Linux/macOS) & Đóng gói Plugin
- P4 — Golden Parity Test Suite 22/22 Mã, Benchmark & Validator
- P5 — Log service, Rà soát Clean Code & Kiểm chứng Trọn bộ
- Cụm song song
- Luật file nóng
- Definition of Done

## Quy tắc thi hành (áp cho mọi task)

1. Thứ tự phase là thứ tự phụ thuộc — không đảo.
2. Mỗi task: đánh `[~]` khi bắt đầu → viết test trước (đỏ) → code → test xanh → đổi sang `[x]` NGAY vào file này. Trạng thái checkbox: `[ ]` chưa làm · `[~]` đang làm · `[x]` xong.
3. Mỗi bước: `tdq_test.py vung-cham`; trọn bộ chỉ ở QC.
4. Lệnh nào chạm state của workflow phải có `TDQ_PROJECT_DIR=<thư mục tạm>` ngay trên chính lệnh đó.
5. QC FAIL → thêm task fix vào mục QC của file này (không cần duyệt lại), loop đến khi pass.
6. Không commit/push cho đến khi user yêu cầu.
7. Tuân thủ 6 mã cấm cơ học (ANTI-1 Fake Red, ANTI-2 Blind Assertion, ANTI-3 Dirty State Git, ANTI-4 Late Tick, ANTI-5 Raw Dump, ANTI-6 Broad Area).

## Thiết kế Trước vs Sau

| Khía cạnh | Hiện trạng (Trước) | Thiết kế mới (Sau) |
|---|---|---|
| Luồng thực thi | Rust `main.rs` thiếu `PreInvocation`/`PostInvocation` (`_ => allow()`); thiếu 14/22 cổng không fallback | Hybrid 2 tầng: Rust xử lý ~91% `Hot-path` (`<= 28 ms`), delegate ~9% `Cold-path` về `dispatch.py` qua `PLUGIN_ROOT` |
| Sổ & 6 quy tắc cổng | Rust ghi `<root>/.tdq-runtime` lệch Python; mềm hóa `TICK`/`LOG`/`UNFINISHED`; hở `qc-tester` & shell write | Duy nhất `docs/tdq/.tdq-runtime/`; Smart Hardening 6 quy tắc (`TICK=8`, `LOG` trừ staging, `MAX_STREAK=2` gắn `plan_sha`) |
| Đóng gói đa nền tảng | `build_agy_plugin.py` copy `.exe` Windows đè lên Linux và macOS (`1.747.968` bytes giống hệt nhau) | Bảo toàn bản ELF/Mach-O với Magic-Byte Guard + rebuild & test thật trên Windows, `ubuntu-100-95` và `mbair` |

*Đối chiếu sơ đồ kiến trúc:* Tham chiếu Archify BA Preview `docs/tdq/spec/2026-11-19-1632-hybrid-hook-smart-hardening-preview.html` và manifest `docs/tdq/spec/2026-11-19-1632-hybrid-hook-smart-hardening-preview.manifest.json` (`binding=current`); mọi task dưới đây ánh xạ trực tiếp tới 4 module `M1`–`M4` và 8 tiêu chí `Q1`–`Q8` của spec đã duyệt.

## P1 — Tầng Core Rust: Schema AGY 2.0, Runtime Dir thống nhất & Hybrid Router (M1)

- [x] **T1.1** (e18m) Đồng bộ schema AGY 2.0 ở protocol.rs và hợp nhất docs/tdq/.tdq-runtime/ ở storage.rs — Test: `cargo test --manifest-path hooks/rust/tdq-dispatch/Cargo.toml --lib protocol`
  - Dùng: `agy-customizations`
  - Để: đối chiếu schema payload và response 6 sự kiện Antigravity 2.0 trong `docs/hooks.md` trước bước đỏ.
  - Ra: `hooks/rust/tdq-dispatch/src/protocol.rs` và `hooks/rust/tdq-dispatch/src/storage.rs` đạt parity schema AGY 2.0.
  - Kiểm: `cargo test --manifest-path hooks/rust/tdq-dispatch/Cargo.toml protocol:: storage::`
  - Không dùng cho: sửa patcher Python hay sinh gói plugin.
  - Chạm: `hooks/rust/tdq-dispatch/src/protocol.rs`, `hooks/rust/tdq-dispatch/src/storage.rs`, `hooks/rust/tdq-dispatch/src/lock.rs`
  - Cần: không
  - Mục tiêu: Chuẩn hóa JSON Input/Output AGY 2.0 và thống nhất duy nhất thư mục `docs/tdq/.tdq-runtime/` giữa Rust và Python.
  - Vị trí neo: `protocol.rs` tại `HookDecision`, `HookPayload`, `GuidanceRepo`; `storage.rs` tại `get_runtime_dir` và sau `reset_stop_streak`; `lock.rs` tương thích `.lock`.
  - Công cụ: Dùng `edit_file`; cấm `write_file` đè toàn tệp có sẵn.
  - Ràng buộc: Chỉ dùng crate sẵn trong `Cargo.toml` (`serde`, `serde_json`, `regex`, `sha2`); không `.unwrap()` trong luồng chính; mỗi hàm `<= 50` dòng.
  - Đặc tả kỹ thuật:
    `HookDecision` xuất `decision`, `reason`, `injectSteps: Option<Vec<InjectStep>>`, `overwrite`, `metadata.user_markdown`, kèm `empty_json()` trả `{}` và `inject_steps()`. `HookPayload` nhận đủ `conversationId`, `workspacePaths`, `workingDirectory`, `toolName`, `toolCall`, `arguments`/`toolInput`, `lastUserInput`, `continuationActive`, `terminationReason`, `transcriptPath`, hỗ trợ `target_file_path()` (`Path`, `TargetFile`, `file_path`, `AbsolutePath`) và `wrap_call_mcp_overwrite()`. `storage::get_runtime_dir(root)` trỏ `root/docs/tdq/.tdq-runtime`, bổ sung `read_turn_meta`, `write_turn_meta`, `mark_turn_closed`, `pop_pending_reminders`, `read_sessions_role`, `read_plan_tick_state`, `count_code_edits_for_sha`.
  - Logic cốt lõi:
    1. Bước 1: Mở rộng struct serde trong `protocol.rs`, viết helper unwrap `call_mcp_tool` giữ nguyên kiểu object hoặc JSON string cho `Arguments`.
    2. Bước 2: Chuyển `get_runtime_dir` sang `docs/tdq/.tdq-runtime`, cài các helper đọc/ghi ledger, `turn-meta` và `pending-reminders` dùng chung sidecar `.lock` trong `storage.rs`.
    3. Bước 3: Viết unit test đỏ → xanh kiểm chứng serialize `injectSteps`/`reason`, parse `workspacePaths`, và đọc/ghi chung `.tdq-runtime`.
  - Ca góc hiểm & TDD:
    - Ca hiểm: `Arguments` lồng dưới dạng chuỗi JSON; `workspacePaths` dạng URI `file:///C:/...` trên Windows.
    - Tiêu chí: `assert!(json.contains("\"injectSteps\""))`, `assert!(!json.contains("\"explanation\""))`, `assert!(get_runtime_dir(&tmp).ends_with("docs/tdq/.tdq-runtime"))`.

- [x] **T1.2** (e15m) Nâng cấp Hybrid 2 tầng Router và phân giải PLUGIN_ROOT trong main.rs + lib.rs — Test: `cargo test --manifest-path hooks/rust/tdq-dispatch/Cargo.toml --bin tdq-dispatch`
  - Chạm: `hooks/rust/tdq-dispatch/src/main.rs`, `hooks/rust/tdq-dispatch/src/lib.rs`
  - Cần: `T1.1`
  - Mục tiêu: Đón đủ 6 sự kiện AGY 2.0, phân loại `Hot-path` vs `Cold-path` và tìm đúng `dispatch.py` khi chạy từ mọi project ngoài repo TDQ.
  - Vị trí neo: `main.rs` trong `resolve_workspace_root`, `execute_python_fallback`, `main()`; `lib.rs` khai báo module sự kiện mới.
  - Công cụ: Dùng `edit_file`.
  - Ràng buộc: Log timestamp ISO ra `stderr` khi `TDQ_DEBUG=1`, tắt khi `TDQ_LOG=0`; cấm in lẫn ký tự ngoài JSON ra `stdout`.
  - Đặc tả kỹ thuật:
    `resolve_workspace_root(payload)` xét `cwd` → `workingDirectory` → `workspacePaths[0]` → `current_dir`. `resolve_dispatch_script(workspace_root)` xét `$PLUGIN_ROOT/hooks/scripts/dispatch.py` → `current_exe()/../hooks/scripts/dispatch.py` → `<workspace_root>/plugins/tdq-workflow-agy/hooks/scripts/dispatch.py` → `<workspace_root>/hooks/scripts/dispatch.py`. Định nghĩa `enum RouteOutcome { Decided(HookDecision), DelegatePython }` cho 6 nhánh sự kiện.
  - Logic cốt lõi:
    1. Bước 1: Thêm match nhánh `"PreInvocation"` và `"PostInvocation"` trong `main()`; chuyển `"SessionStart"` trả `DelegatePython`.
    2. Bước 2: Viết `resolve_dispatch_script` ưu tiên `PLUGIN_ROOT` và `current_exe()` trước khi fallback vào `workspace_root`.
    3. Bước 3: Chạy `execute_python_fallback` truyền nguyên `raw_stdin` + `--event` qua `python -X utf8` (Win) hoặc `python3 -X utf8` (Unix).
  - Ca góc hiểm & TDD:
    - Ca hiểm: Chạy binary trong `tmp_path` không chứa thư mục `plugins/`, chỉ có biến môi trường `PLUGIN_ROOT`.
    - Tiêu chí: `assert_eq!(resolve_dispatch_script(&tmp_other), Some(expected_from_plugin_root))` và test match `PreInvocation`/`PostInvocation` PASS.

**Xong P1 khi**: Toàn bộ test `protocol::`, `storage::`, `lock::`, `--bin tdq-dispatch` xanh, khớp schema AGY 2.0 và phân giải được `dispatch.py` ngoài repo.

## P2 — Tầng Hot-path Rust, Python Smart Hardening & Multi-OS Build Guard (M2 + M3)

- [x] **T2.1** (e22m) Hoàn thiện Rust Hot-path cho 6 sự kiện, Shell Mutator Guard và sửa cắt UTF-8 — Test: `cargo test --manifest-path hooks/rust/tdq-dispatch/Cargo.toml`
  - Chạm: `hooks/rust/tdq-dispatch/src/command_parser.rs`, `hooks/rust/tdq-dispatch/src/events/mod.rs`, `hooks/rust/tdq-dispatch/src/events/pre_tool_use.rs`, `hooks/rust/tdq-dispatch/src/events/post_tool_use.rs`, `hooks/rust/tdq-dispatch/src/events/pre_invocation.rs`, `hooks/rust/tdq-dispatch/src/events/post_invocation.rs`, `hooks/rust/tdq-dispatch/src/events/session_start.rs`, `hooks/rust/tdq-dispatch/src/events/stop_streak.rs`
  - Cần: `T1.1`, `T1.2`
  - Mục tiêu: Đảm nhận ~91% lưu lượng `Hot-path` bằng Rust thuần và giữ an toàn UTF-8 + đồng bộ Smart Hardening với Python.
  - Vị trí neo: Tạo mới `events/pre_invocation.rs`, `events/post_invocation.rs`; sửa `events/mod.rs`, `command_parser.rs` (sau `inspect_command_safety`), `pre_tool_use.rs`, `post_tool_use.rs`, `session_start.rs` (đoạn cắt `rules_content`), `stop_streak.rs` (`get_plan_info`, `handle_stop_streak`).
  - Công cụ: Dùng `write_file` chỉ cho 2 tệp mới `pre_invocation.rs`/`post_invocation.rs`; dùng `edit_file` cho các tệp hiện hữu.
  - Ràng buộc: Không thêm dependency; các ca `PreInvocation` đầu lượt mới, `Stop` có `active_request` mở, `implement_mode=subagent` sửa file, hoặc `run_command` cần `rtk`/`search_rules` sâu phải trả `DelegatePython`.
  - Đặc tả kỹ thuật:
    `command_parser::is_shell_mutator(cmd)` nhận diện `Set-Content`, `Add-Content`, `Out-File`, `Copy-Item`, `Move-Item`, `Remove-Item`, `New-Item`, `tee `, `sed -i`, `>`, `open(...,'w'|'a'|'x')`. `post_invocation` `stat` `pending-reminders-<sid>.jsonl`; `pre_invocation` kiểm `turn-meta-<sid>.json` (giữa lượt xả hàng đợi, đầu lượt trả `DelegatePython`); `pre_tool_use` phủ đủ `write_to_file`/`replace_file_content`/`multi_replace_file_content`, `STATE`, `GIT`, `READONLY` (gồm `"qc-tester"`), `ZERO-POPUP`, `APPROVE` (kèm shell mutator), `TICK` (`0`/`>1` `[~]`, ngưỡng `8`), `LSP` bọc `Arguments`, `SUBAGENT`; `post_tool_use` ghi nhận `graphify`; `session_start` dùng `char_indices().nth(1500)`; `stop_streak` nhận `[>]` và mã `"UNFINISHED"`.
  - Logic cốt lõi:
    1. Bước 1: Viết `pre_invocation.rs`, `post_invocation.rs`, và `is_shell_mutator` trong `command_parser.rs`.
    2. Bước 2: Mở rộng `pre_tool_use.rs`, `post_tool_use.rs`, `stop_streak.rs` và sửa cắt UTF-8 trong `session_start.rs`.
    3. Bước 3: Chạy `cargo test` toàn crate xác minh các ca tiếng Việt, `qc-tester`, `TICK=8`, `call_mcp_tool` `Arguments`.
  - Ca góc hiểm & TDD:
    - Ca hiểm: Chuỗi tiếng Việt 3 byte cắt tại vị trí 1500 trong `session_start.rs`; `write_to_file` truyền `TargetFile` vào `docs/tdq/state.json`.
    - Tiêu chí: `assert_eq!(res.decision, DecisionKind::Deny)` cho `qc-tester` shell mutator và `TICK` 0 `[~]`, không panic khi cắt chuỗi UTF-8.

- [x] **T2.2** (e22m) Áp dụng 6 quy tắc Smart Hardening trên agy_hooks.py, agy_dispatch.py, agy_manifests.py và thêm qc-tester ở bash_gate.py — Test: `py -3 -m pytest tests/test_hook_dispatch_r1_r3.py tests/test_bash_gate.py tests/test_edit_gate.py tests/test_stop_gate.py tests/test_search_gate.py -q`
  - Chạm: `tools/patches/agy_hooks.py`, `tools/patches/agy_dispatch.py`, `tools/patches/agy_manifests.py`, `hooks/scripts/bash_gate.py`
  - Cần: `T1.1`
  - Mục tiêu: Áp dụng trọn 6 quy tắc Smart Hardening cho tầng Antigravity và giữ nguyên 0 hồi quy cho `hooks/scripts/` gốc Claude/Codex (`3a`).
  - Vị trí neo: `bash_gate.py` tại `_enforce_agy_bash_guards`; `agy_hooks.py` tại `_patch_bash_gate`, `_patch_edit_gate`, `_patch_search_gate`, `_patch_prompt_context`, `_patch_stop_gate`; `agy_dispatch.py` tại `_route_pre_tool_use`.
  - Công cụ: Dùng `edit_file`.
  - Ràng buộc: Thuần stdlib Python; giữ `STREAK_NGUONG=3` nguyên trạng trong `hooks/scripts/edit_gate.py` gốc; chuỗi máy & comment tuân thủ `i18n_check.py`.
  - Đặc tả kỹ thuật:
    `_patch_edit_gate`: chỉ nhắc nhẹ khi `streak` trong `4..7`, `block("TDQ:TICK")` cho `0`/`>1` `[~]` và `streak >= 8`. `_patch_stop_gate`: thay `return` mù `continuationActive` bằng `MAX_STREAK=2` gắn `plan_sha` (reset khi `plan_sha` đổi, giữ `[>]`/`pause`); khôi phục `stop_block` cho `TDQ:LOG` (trừ `docs/.staging*`, `docs/tdq/`, `graphify-out/`, `*.tmp`) và `TDQ:TICK` (`plan_sha` đứng yên). `_patch_search_gate`: cấm shell chứa `\brg\b|\bgrep\b|Select-String|findstr` lọt `agy_malformed_allow`, ghi nhận `graphify`. `bash_gate.py` + `_patch_bash_gate`: thêm `"qc-tester"` vào tuple read-only và chặn shell mutator khi khóa `APPROVE`/`TEAM`. `_patch_prompt_context`: bơm 1 dòng neo `[TDQ:GON]`/`[TDQ:QC]` đầu pha & sau compaction.
  - Logic cốt lõi:
    1. Bước 1: Cập nhật `"qc-tester"` ở `_enforce_agy_bash_guards` trong `hooks/scripts/bash_gate.py`.
    2. Bước 2: Cập nhật các hàm `_patch_*` trong `tools/patches/agy_hooks.py` và định tuyến `graphify` trong `tools/patches/agy_dispatch.py`.
    3. Bước 3: Chạy `pytest` trên nhóm test gate gốc và test R1–R3 xác minh `replace_exact` sạch lỗi và hành vi Smart Hardening hoạt động.
  - Ca góc hiểm & TDD:
    - Ca hiểm: Tệp `docs/.staging/x.md` hay `graphify-out/x.json` sửa trong lượt không kích hoạt `TDQ:LOG`; `continuationActive=True` với `plan_sha` đổi vẫn giữ gate `UNFINISHED`.
    - Tiêu chí: `assert resp["decision"] == "continue"` khi sửa code thiếu log ở `Stop` và `assert resp["decision"] == "deny"` cho `qc-tester` dùng `Set-Content`.

- [x] **T2.3** (e12m) Sửa lỗi ghi đè binary đa nền tảng và thêm Magic-Byte Guard ở tools/build_agy_plugin.py — Test: `py -3 -c "import sys; sys.path.insert(0, 'tools'); import build_agy_plugin as b; assert callable(b.verify_binary_magic)"`
  - Chạm: `tools/build_agy_plugin.py`
  - Cần: không
  - Mục tiêu: Chấm dứt lỗi copy đè `.exe` Windows thành binary Linux/macOS trong `stage/bin/` và xác thực magic bytes trước khi đóng gói.
  - Vị trí neo: `tools/build_agy_plugin.py` bước `# 4b. Embed standalone Rust binaries in bin/` trước `# 5. Emit final manifest.json`.
  - Công cụ: Dùng `edit_file`.
  - Ràng buộc: Thuần Python stdlib; fail-closed (`RuntimeError`) nếu thiếu hoặc sai magic bytes ở bất kỳ binary nào trong 3 OS.
  - Đặc tả kỹ thuật:
    Thêm `verify_binary_magic(path: Path, target: str) -> bool` kiểm tra header bytes (`windows`: `b"MZ"`, `linux`: `b"\x7fELF"`, `darwin`: `b"\xcf\xfa\xed\xfe"` / `b"\xfe\xed\xfa\xcf"` / `b"\xca\xfe\xba\xbe"`) và `_stage_rust_binaries(upstream, stage_bin, existing_output_bin)` chỉ nạp binary Unix từ `prebuilt/` hoặc `existing_output_bin/` nếu hợp lệ, cấm copy chéo từ `rust_exe`.
  - Logic cốt lõi:
    1. Bước 1: Cài hàm `verify_binary_magic` với map magic bytes theo target OS.
    2. Bước 2: Viết `_stage_rust_binaries` thay thế các lệnh `shutil.copy2(rust_exe, linux_bin|darwin_bin)` lỗi.
    3. Bước 3: Kiểm chứng đơn vị `verify_binary_magic` từ chối tệp PE gắn nhãn Linux/macOS và nhận đúng tệp ELF/Mach-O.
  - Ca góc hiểm & TDD:
    - Ca hiểm: File cũ trong `output/bin/tdq-dispatch-linux-x86_64` vẫn là bản PE bị lỗi từ đợt trước → phải ném `RuntimeError`.
    - Tiêu chí: `assert not verify_binary_magic(win_exe, "linux")` và `assert verify_binary_magic(win_exe, "windows")`.

**Xong P2 khi**: `cargo test` toàn crate Rust xanh, bộ test gate Python + R1–R3 xanh, và `verify_binary_magic` chặn thành công copy chéo OS.

## P3 — Build 3 OS (Windows + SSH Linux/macOS) & Đóng gói Plugin (M3)

- [x] **T3.1** (e18m) Rebuild và test Rust trên đủ 3 OS (Windows, Linux ubuntu-100-95, macOS mbair) rồi build gói plugins/tdq-workflow-agy/ — Test: `agy.EXE plugin validate plugins/tdq-workflow-agy --strict --json`
  - Dùng: `tdq-checkportable`
  - Để: kiểm tra tính toàn vẹn manifest, cấu trúc thư mục và yêu cầu runtime của gói `plugins/tdq-workflow-agy/` sau khi build.
  - Ra: `plugins/tdq-workflow-agy/manifest.json` và 3 binary native trong `plugins/tdq-workflow-agy/bin/` đạt `--strict`.
  - Kiểm: `agy.EXE plugin validate plugins/tdq-workflow-agy --strict --json`
  - Không dùng cho: chạy `install.py` cài đặt đè lên local plugin ở máy người dùng (`2b`).
  - Chạm: `plugins/tdq-workflow-agy/bin/tdq-dispatch.exe`, `plugins/tdq-workflow-agy/bin/tdq-dispatch-linux-x86_64`, `plugins/tdq-workflow-agy/bin/tdq-dispatch-darwin-arm64`, `plugins/tdq-workflow-agy/hooks/scripts/dispatch.py`, `plugins/tdq-workflow-agy/hooks/scripts/_common.py`, `plugins/tdq-workflow-agy/hooks/scripts/edit_gate.py`, `plugins/tdq-workflow-agy/hooks/scripts/stop_gate.py`, `plugins/tdq-workflow-agy/hooks/scripts/bash_gate.py`, `plugins/tdq-workflow-agy/hooks/scripts/search_gate.py`, `plugins/tdq-workflow-agy/hooks/scripts/prompt_context.py`, `plugins/tdq-workflow-agy/hooks.json`, `plugins/tdq-workflow-agy/manifest.json`
  - Cần: `T2.1`, `T2.2`, `T2.3`
  - Mục tiêu: Tạo đủ 3 binary native PE/ELF/Mach-O từ cùng mã nguồn Hybrid và đóng gói sạch `plugins/tdq-workflow-agy/`.
  - Vị trí neo: Thư mục `hooks/rust/tdq-dispatch/prebuilt/` và đích đóng gói `plugins/tdq-workflow-agy/`.
  - Công cụ: `cargo build --release`, `ssh`/`scp ubuntu-100-95`, `ssh`/`scp mbair`, `py -3 tools/build_agy_plugin.py`, `agy.EXE`.
  - Ràng buộc: TUYỆT ĐỐI không chạy `install.py` (`2b`); nếu mất kết nối SSH tới host Unix phải dùng `tdq_state.py pause --loai mat-truy-cap`, cấm copy chéo OS.
  - Đặc tả kỹ thuật:
    Biên dịch `--release` trên Windows, đồng bộ crate sang `ubuntu-100-95` chạy `cargo test && cargo build --release` rồi thu binary Linux x86_64 ELF, đồng bộ crate sang `mbair` chạy `cargo test && cargo build --release` rồi thu binary macOS ARM64 Mach-O; đặt vào `prebuilt/` và chạy `tools/build_agy_plugin.py`.
  - Logic cốt lõi:
    1. Bước 1: Chạy `cargo build --release` + `cargo test` tại Windows.
    2. Bước 2: Gửi mã nguồn crate và build + test qua SSH trên `ubuntu-100-95` và `mbair`, kéo 2 binary native về `prebuilt/`.
    3. Bước 3: Chạy `py -3 tools/build_agy_plugin.py` tạo `plugins/tdq-workflow-agy/` và kiểm bằng `agy.EXE plugin validate --strict --json`.
  - Ca góc hiểm & TDD:
    - Ca hiểm: Sai quyền thực thi `+x` trên binary Unix hoặc sai CRLF khi gửi qua SSH → dùng archive `tar` giữ chuẩn LF.
    - Tiêu chí: `findings == []` và 3 file trong `plugins/tdq-workflow-agy/bin/` có 3 magic bytes & dung lượng riêng biệt.

**Xong P3 khi**: Cả 3 binary PE/ELF/Mach-O chạy pass `cargo test` trên 3 máy thật và `agy.EXE plugin validate plugins/tdq-workflow-agy --strict --json` đạt `findings = []`.

## P4 — Golden Parity Test Suite 22/22 Mã, Benchmark & Validator (M4)

- [ ] **T4.1** (e25m) Viết bộ Golden Parity Test Suite 22/22 mã cổng x 6 sự kiện và Smoke Test vòng đời — Test: `py -3 -m pytest tests/test_rust_dispatch_parity.py -q`
  - Chạm: `tests/test_rust_dispatch_parity.py`
  - Cần: `T3.1`
  - Mục tiêu: Khóa 100% tương đương hành vi giữa mặc định Hybrid và `TDQ_HOOK_ENGINE=python` trên đủ 22 mã cổng và 6 sự kiện AGY 2.0.
  - Vị trí neo: `tests/test_rust_dispatch_parity.py` mở rộng sau `test_rust_fallback_to_python`.
  - Công cụ: Dùng `edit_file`.
  - Ràng buộc: Mọi ca dùng `tmp_path` + `TDQ_PROJECT_DIR=tmp_path` (không chạm state repo thật); kiểm đủ `22/22` mã `AGY_CODES` kèm smoke test end-to-end 6 sự kiện.
  - Đặc tả kỹ thuật:
    Hàm `assert_full_json_parity(rust_res, py_res)` so khớp `decision`, khóa `reason` (`[TDQ:<CODE>]`), `injectSteps`, `overwrite` (gồm `Arguments`), `metadata.user_markdown`; parametrize đủ 22 mã cổng × 6 sự kiện, cộng thêm ca `PLUGIN_ROOT` ngoài repo, UTF-8 `session_start`, `TICK` (`0`/`>1`/`8`/`Stop` `plan_sha`), `LOG` trừ staging, `UNFINISHED` `continuationActive`, `qc-tester` shell write và smoke test 1 vòng đời đầy đủ.
  - Logic cốt lõi:
    1. Bước 1: Viết fixture tạo `tmp_path` có git repo, `state.json`, `plan.md`, `turns`/`turn-meta` độc lập.
    2. Bước 2: Chạy ma trận 22 mã × 6 sự kiện so sánh `tdq-dispatch.exe` mặc định vs `TDQ_HOOK_ENGINE=python`.
    3. Bước 3: Bổ sung ca `smoke` end-to-end 6 sự kiện và chạy `pytest` xác nhận 100% PASS.
  - Ca góc hiểm & TDD:
    - Ca hiểm: Ghi/xóa đồng thời trên Windows NTFS với file `.lock` và URI `file:///C:/...` trong `workspacePaths`.
    - Tiêu chí: `assert set(covered_codes) == set(AGY_CODES)` và 100% assertion JSON parity pass.

- [ ] **T4.2** (e12m) Cập nhật Benchmark Hot/Cold/Trọng số, Validator Magic Bytes 3 OS và test Smart Hardening R1–R3 — Test: `py -3 -m pytest tests/test_rust_latency_benchmark.py tests/test_agy_plugin_validate.py tests/test_hook_dispatch_r1_r3.py -q`
  - Chạm: `tests/test_rust_latency_benchmark.py`, `tests/test_agy_plugin_validate.py`, `tests/test_hook_dispatch_r1_r3.py`
  - Cần: `T3.1`
  - Mục tiêu: Đo thực nghiệm hiệu năng Hot-path/Cold-path/trọng số, khóa kiểm magic bytes 3 binary trong validator và cập nhật test R1–R3 theo Smart Hardening.
  - Vị trí neo: `test_rust_latency_benchmark.py` tại `test_measure_hook_latency`; `test_agy_plugin_validate.py` sau `test_v2_python_ast_and_md_budgets_and_no_traps`; `test_hook_dispatch_r1_r3.py` ở các ca `TICK`/`LOG`/`continuationActive`.
  - Công cụ: Dùng `edit_file`.
  - Ràng buộc: Đo thực nghiệm `runs = 30`, không giả lập đồng hồ.
  - Đặc tả kỹ thuật:
    Benchmark đo riêng `Hot-path` (`PostInvocation`, `PreToolUse` direct `<= 25 ms`, `cmd /c <= 32 ms`), `Cold-path` (`SessionStart`) và trọng số `0.91*hot + 0.09*cold <= 40 ms`; `test_agy_plugin_validate.py` thêm `test_v2_multiplatform_binary_magic_bytes`; `test_hook_dispatch_r1_r3.py` cập nhật kỳ vọng `Smart Hardening`.
  - Logic cốt lõi:
    1. Bước 1: Mở rộng `test_rust_latency_benchmark.py` đo Hot/Cold và tính trung bình có trọng số.
    2. Bước 2: Thêm `test_v2_multiplatform_binary_magic_bytes` và đồng bộ `test_hook_dispatch_r1_r3.py`.
    3. Bước 3: Chạy `pytest -s` thu bảng số đo thực tế và xác nhận ngưỡng PASS.
  - Ca góc hiểm & TDD:
    - Ca hiểm: Tải nền CPU Windows làm `cmd /c` dao động → ghi rõ median + p95 tách biệt chi phí vỏ shell.
    - Tiêu chí: `assert hot_direct <= 25.0`, `assert hot_shell <= 32.0`, `assert weighted_ms <= 40.0`, `assert len(distinct_sizes) == 3`.

**Xong P4 khi**: Golden Parity 22 mã × 6 sự kiện, benchmark và validator magic bytes 3 OS đều PASS 100%.

## P5 — Log service, Rà soát Clean Code & Kiểm chứng Trọn bộ (M4 / QC Ultra)

- [ ] **T5.1** (e8m) Xác minh Log service bật mặc định (Rust + Python) và rà soát tối giản (tdq-lean) trên toàn bộ diff — Test: `py -3 -m pytest tests/test_rust_dispatch_parity.py -q -k "log or fallback"`
  - Dùng: `tdq-lean`
  - Để: soát thừa, trùng lặp logic hoặc hàm vượt 50 dòng trong toàn bộ diff Rust và Python sau implement.
  - Ra: danh sách rà soát sạch (0 mục thừa hoặc đã xử lý gọn trước QC ultra).
  - Kiểm: `git diff --stat dev`
  - Không dùng cho: thay đổi thiết kế đã duyệt hoặc bỏ bớt cổng Smart Hardening.
  - Cần: `T4.1`, `T4.2`

- [ ] **T5.2** (e10m) Chạy trọn bộ test toàn repo, kiểm i18n/doc_lint, cross-OS smoke check và chuẩn bị QC ultra — Test: `py -3 -m pytest tests/test_rust_dispatch_parity.py tests/test_agy_plugin_validate.py -q`
  - Chạm: `docs/tdq/qc/2026-11-19-1632-hybrid-hook-smart-hardening.md`
  - Cần: `T5.1`

## Cụm song song

- Đợt 1: `T1.1`, `T2.3` (`protocol.rs`/`storage.rs`/`lock.rs` độc lập hoàn toàn với `build_agy_plugin.py`).
- Đợt 2: `T1.2` (cần `T1.1`), `T2.2` (cần `T1.1`, không chạm file Rust).
- Đợt 3: `T2.1` (cần `T1.1`, `T1.2`).
- Đợt 4: `T3.1` (cần `T2.1`, `T2.2`, `T2.3` — build 3 OS và đóng gói `plugins/tdq-workflow-agy/`).
- Đợt 5: `T4.1`, `T4.2` (cần `T3.1`, hai file test tách biệt nhau).
- Đợt 6: `T5.1` → `T5.2` (rà soát clean code `tdq-lean`, chạy trọn suite + chuẩn bị thẩm định `tdq-qc-tester` mức `ultra`).

## Luật file nóng

Không có tệp mã nguồn nào bị từ 2 task trở lên khai chung ở `Chạm:` (`0` HOT FILE): tầng core Rust (`T1.1`) tách riêng khỏi router (`T1.2`) và tầng event (`T2.1`), tầng Python patcher (`T2.2`) tách khỏi build script (`T2.3`), gói xuất bản gom duy nhất vào `T3.1`, và hai cụm kiểm thử `T4.1`/`T4.2` tách tệp hoàn toàn.

## Definition of Done

- [ ] Q1 Schema AGY 2.0 & đủ 6 sự kiện (0 khóa sai tên) — `cargo test --manifest-path hooks/rust/tdq-dispatch/Cargo.toml protocol::`
- [ ] Q2 Thống nhất docs/tdq/.tdq-runtime/ & phân giải PLUGIN_ROOT ngoài repo — `py -3 -m pytest tests/test_rust_dispatch_parity.py -q -k "runtime or plugin_root"`
- [ ] Q3 Golden Parity 22/22 mã cổng x 6 sự kiện khớp 100% — `py -3 -m pytest tests/test_rust_dispatch_parity.py -q`
- [ ] Q4 Đủ 6 quy tắc Smart Hardening & an toàn UTF-8 — `py -3 -m pytest tests/test_rust_dispatch_parity.py tests/test_hook_dispatch_r1_r3.py -q`
- [ ] Q5 Hiệu năng Hot-path <= 25 ms direct, <= 32 ms cmd /c, trọng số <= 40 ms — `py -3 -m pytest tests/test_rust_latency_benchmark.py -s -q`
- [ ] Q6 Magic Bytes PE/ELF/Mach-O 3 OS & test thật Windows/Linux/macOS — `py -3 -m pytest tests/test_agy_plugin_validate.py -q -k magic`
- [ ] Q7 Trọn bộ unit test hồi quy Claude/Codex, strict validator & giữ nguyên local plugin — `py -3 -m pytest -q && agy.EXE plugin validate plugins/tdq-workflow-agy --strict --json && py -3 scripts/i18n_check.py`
- [ ] Q8 QC mức ultra: Smoke test vòng đời 6 sự kiện & báo cáo PASS từ agent tdq-qc-tester độc lập — `py -3 -m pytest tests/test_rust_dispatch_parity.py -q -k smoke`
