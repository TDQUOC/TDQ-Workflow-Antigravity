# Báo cáo — Triển khai Trọn bộ 3 Đợt Kiến trúc `work_kind=investigate` V2

Ngày: 2026-11-21 · Spec: [spec](../spec/2026-11-21-0217-trien-khai-investigate-v2.md) · Plan: [plan](../plan/2026-11-21-0217-trien-khai-investigate-v2.md) · QC: [qc](../qc/2026-11-21-0217-trien-khai-investigate-v2.md)
Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

## Tóm tắt

- **Trước request:** TDQ Workflow chỉ có một luồng `build` duy nhất (`scripts/tdq_state.py`), ép mọi tác vụ nghiên cứu/phân tích/điều tra lỗi đi qua cấu trúc §2b giả định module code, Double Archify, rule `R10`/`R14` cứng (`scripts/doc_lint.py`), và dính bug `_cli_approve` làm `implement = 0s`; `scripts/tdq_team.py` thiếu engine `evidence` shard-merge và khóa cho `blackboard_record`; `edit_gate`/`pre_tool_use.rs` chưa tách `tdq-security-reviewer` khỏi nhóm điều tra `scoped-write`, còn hở canonicalize 1 cấp và bypass `cmd /c`/`[IO.File]`; Rust `tdq-dispatch` bỏ qua đọc theo dải dòng (`has_range`) và chưa theo dõi Weighted Burden theo `sid`, cũng chưa có bộ test đối kháng Python ↔ Rust + harness `4` ca lịch sử.
- **Sau request:** Đã triển khai đồng bộ toàn bộ `3` đợt (`M1`–`M6`) vào mã nguồn thật trên nhánh `feat/trien-khai-investigate-v2`: bổ sung `work_kind = "build" | "investigate"` fail-closed, `INVESTIGATE_PHASE_ROWS` giữ nguyên `len(PHASE_TABLE) == 11`, vá `ghi_moc_phase`, `escalate-to-build --by`, miễn có điều kiện R10/R14 & Double Archify, cô lập script chẩn đoán `docs/tdq/bench/<slug>/*.py`; dựng `evidence add|merge|render` (`--claim-file`, khóa NTFS `msvcrt` + POSIX `O_EXCL` không dùng `fcntl`) và biến thể `no_worktree`; đồng bộ bảo mật `scoped-write` `5` tầng Deny-first Python ↔ Rust + Weighted Burden theo `sid` (`>=40` điểm phát `[TDQ:DOC]`, giữ `22` mã AGY) giữ nguyên `has_range` fast-path; thêm `skills/tdq-conventions/references/investigate-mode.md` (`1,783` tokens), cập nhật `agents/` & `tools/patches/`, biên dịch `tdq-dispatch.exe`, rebuild `plugins/tdq-workflow-agy/` (`66` file `<= 3,500` tokens) và bổ sung `tests/test_investigate_workflow.py`.
- **Đã test gì:** Xử lý 2 vòng sửa `QC1.1` (cô lập `sys.path`/`sys.modules` giữa `test_read_gate.py`, `test_investigate_workflow.py` và `test_hooks_dual_protocol.py`) và `QC1.2` (sửa `10` module đỏ phát hiện ở lượt `tron-bo` đầu: bỏ `import fcntl`, chỉ ghi `worktree_required: false`, giữ chuỗi neo O10/MCP-First `<600` chars trong `session_start.py`, cập nhật `doc_index.py`/`luat-hien-co.md`, `SubagentStop` ở `test_agent_upgrade_mvp.py`, và `APPROVED_RELEASE_DOCS` ở `test_build_portable.py`). Sau commit `5e513558`, chạy trọn bộ `scripts/tdq_test.py tron-bo --workers 1 --fresh --reuse off` (`2/3`), `cargo test && cargo clippy -- -D warnings`, `agy.exe plugin validate --strict --json`, `install_agy_plugin.py --dry-run`, đo độ trễ Rust, `token_budget.py --kiem`, `i18n_check.py`, `doc_lint.py`, và nghiệm thu độc lập `tdq-qc-tester` (`18` probe đối kháng + `TDQ_LOG=0`).
- **Kết quả test:**
  - `scripts/tdq_test.py tron-bo`: **PASS** `4,596 passed, 36 skipped, 2,891 subtests passed` (`0` failed, `4,632` tests collected trong `1,279.01s`, `bo_sot = 0`).
  - `Q1`: `211 passed, 131 subtests` (`108.27s`), `PHASE_TABLE == 11`, `investigate-mode.md = 1,783` tokens (`<= 3,000`), `66` file `<= 3,500` tokens, `doc_index`/`doc_lint`/`i18n_check` `0` lỗi.
  - `Q2`: `99 passed, 1 skipped` (`WinError 1314` symlink; `mklink /J` NTFS junction PASS), `18/18` probe bảo mật `py == rust` (`100%`).
  - `Q3`: `89 passed, 25 subtests` (`104.96s`), `Hot PreToolUse (Direct)` median **`14.35 ms`** (`tdq-qc-tester` đo `14.76 ms`, đạt `<= 25.0 ms`), `all_agy_codes == 22`.
  - `Q4`: `cargo test` `29 passed` (`0.07s`), `cargo clippy --all-targets -- -D warnings` `0` warning, `agy.exe plugin validate plugins/tdq-workflow-agy --strict --json` `findings: []`, `install_agy_plugin.py --dry-run` exit `0`.
  - `Q5` & `Q6`: Harness `4` ca (`1056`, `1457`, `1346`, `1953`) PASS, `TDQ_LOG=0` im `stderr` `100%`, `C:\Users\admin\.gemini\config\plugins\tdq-workflow-agy` nguyên `mtime` `11/19/2026`, `tdq-qc-tester` ký **PASS everything** (`Q1`–`Q6`, `QC-F1`–`QC-F4`).

## Đầu ra

- **Đợt 1 (State, Lint, Scaffold, Bench & Skills):**
  - [scripts/tdq_state.py](../../../scripts/tdq_state.py) — `work_kind` fail-closed, `INVESTIGATE_PHASE_ROWS`, vá `ghi_moc_phase`, `_archify_gate`, `escalate-to-build`, `spec_sha256` drift, `next_headline`.
  - [scripts/doc_lint.py](../../../scripts/doc_lint.py), [scripts/tdq_plan_scaffold.py](../../../scripts/tdq_plan_scaffold.py), [scripts/tdq_bench.py](../../../scripts/tdq_bench.py) — miễn điều kiện `R10`/`R14`, `docs/tdq/bench/<slug>/`, `is_created`, `t_hop=0.0` cho `no_worktree`.
  - [investigate-mode.md](../../../skills/tdq-conventions/references/investigate-mode.md) (`1,783` tokens) cùng cập nhật [tdq-conventions SKILL.md](../../../skills/tdq-conventions/SKILL.md), [tdq-intake SKILL.md](../../../skills/tdq-intake/SKILL.md), [tdq-build SKILL.md](../../../skills/tdq-build/SKILL.md), [tdq-spec SKILL.md](../../../skills/tdq-spec/SKILL.md), [spec-template.md](../../../skills/tdq-spec/references/spec-template.md), [qc.md](../../../skills/tdq-build/references/qc.md), [team-mode.md](../../../skills/tdq-build/references/team-mode.md), [quick-lane-mini.md](../../../skills/tdq-intake/references/quick-lane-mini.md), [issue-triage.md](../../../skills/tdq-intake/references/issue-triage.md), [docs/tdq/audit/luat-hien-co.md](../audit/luat-hien-co.md) và [docs/tdq/token-budget.json](../token-budget.json).
- **Đợt 2 (Evidence Engine, Python Hooks & Rust Burden Dispatcher):**
  - [scripts/tdq_team.py](../../../scripts/tdq_team.py), [scripts/tdq_ten_lenh.py](../../../scripts/tdq_ten_lenh.py), [handoff-schema.json](../../../skills/tdq-conventions/references/handoff-schema.json) — `evidence add|merge|render`, `--claim-file`/`--excerpt-file`, `_ntfs_lock` + POSIX `O_EXCL`, `no_worktree`.
  - [hooks/scripts/_common.py](../../../hooks/scripts/_common.py), [edit_gate.py](../../../hooks/scripts/edit_gate.py), [bash_gate.py](../../../hooks/scripts/bash_gate.py), [prompt_context.py](../../../hooks/scripts/prompt_context.py), [session_start.py](../../../hooks/scripts/session_start.py), [subagent_stop.py](../../../hooks/scripts/subagent_stop.py), [hooks/hooks.json](../../../hooks/hooks.json).
  - [storage.rs](../../../hooks/rust/tdq-dispatch/src/storage.rs), [protocol.rs](../../../hooks/rust/tdq-dispatch/src/protocol.rs), [command_parser.rs](../../../hooks/rust/tdq-dispatch/src/command_parser.rs), [pre_tool_use.rs](../../../hooks/rust/tdq-dispatch/src/events/pre_tool_use.rs), [post_tool_use.rs](../../../hooks/rust/tdq-dispatch/src/events/post_tool_use.rs), [pre_invocation.rs](../../../hooks/rust/tdq-dispatch/src/events/pre_invocation.rs), [session_start.rs](../../../hooks/rust/tdq-dispatch/src/events/session_start.rs), [user_prompt_submit.rs](../../../hooks/rust/tdq-dispatch/src/events/user_prompt_submit.rs).
- **Đợt 3 & Kiểm thử (Agents, AGY Compiler, Plugin Bundle & Test Suite):**
  - [tdq-explorer.md](../../../agents/tdq-explorer.md), [tdq-debugger.md](../../../agents/tdq-debugger.md), [tdq-reviewer.md](../../../agents/tdq-reviewer.md), [tools/patches/skills_and_agents.py](../../../tools/patches/skills_and_agents.py), [tools/patches/agy_hooks.py](../../../tools/patches/agy_hooks.py).
  - [plugins/tdq-workflow-agy/](../../../plugins/tdq-workflow-agy/manifest.json) + `tdq-dispatch.exe` (`1,967,104` B).
  - [tests/test_investigate_workflow.py](../../../tests/test_investigate_workflow.py) cùng mở rộng/sửa hồi quy tại [test_state.py](../../../tests/test_state.py), [test_phase_table.py](../../../tests/test_phase_table.py), [test_doc_lint.py](../../../tests/test_doc_lint.py), [test_plan_v2_linter.py](../../../tests/test_plan_v2_linter.py), [test_team_packet_v2.py](../../../tests/test_team_packet_v2.py), [test_bash_gate.py](../../../tests/test_bash_gate.py), [test_read_gate.py](../../../tests/test_read_gate.py), [test_rust_lock_safety.py](../../../tests/test_rust_lock_safety.py), [test_agent_frontmatter.py](../../../tests/test_agent_frontmatter.py), [test_agent_upgrade_mvp.py](../../../tests/test_agent_upgrade_mvp.py), [test_build_portable.py](../../../tests/test_build_portable.py).
- **Tỉ lệ giao team (`tdq_team.py`):** `4/16` task trong bản đồ (`T1.1`, `T1.2`, `T4.1` chạy worktree subagent độc lập + `QC1.1`), `12/16` giữ ở leader đúng bảng tra (`file-luat` cho `T1.3`, `T2.1`, `T2.2`, `T2.3`, `T3.1`, `QC1.2` và `vung-khoa` cho `Q1`–`Q6`); cộng thêm `1` subagent `tdq-qc-tester` (`6d8cff4d`) kiểm chứng độc lập toàn bộ DoD.

## Archify HTML

- Báo cáo trực quan: [2026-11-21-0217-trien-khai-investigate-v2.html](2026-11-21-0217-trien-khai-investigate-v2.html)
- Tailscale Serve URL: https://unity-pc-rtx3060.tail99896.ts.net/vlog/tdq-workflow-agy/reports/2026-11-21-0217-trien-khai-investigate-v2.html
- Biểu đồ nguồn: [bao-cao.archify.md](../artifacts/2026-11-21-0217-trien-khai-investigate-v2/bao-cao.archify.md)

## Giới hạn

- **Biên dịch đa nền tảng Rust (`1a`):** Chỉ biên dịch mới `plugins/tdq-workflow-agy/bin/tdq-dispatch.exe` trên Windows (`1,967,104` B). Hai binary `tdq-dispatch-linux-x86_64` (`2,268,768` B) và `tdq-dispatch-darwin-arm64` (`1,812,432` B) ngày `11/19/2026` được giữ nguyên trong `plugins/tdq-workflow-agy/bin/` nên tính năng native Rust V2 (Weighted Burden, `resume`/`mode`, `scoped-write`) trên Linux/macOS cần build lại từ `hooks/rust/tdq-dispatch` trên máy đích trước khi phát hành.
- **Cài đặt plugin trực tiếp (`2a`):** Chưa ghi đè `C:\Users\admin\.gemini\config\plugins\tdq-workflow-agy` (`LastWriteTime 11/19/2026 1:21:43 PM`); mới chạy `tools/install_agy_plugin.py --dry-run` (`exit 0`) và `agy.exe plugin validate --strict` (`findings: []`) để giữ nguyên plugin đang chạy tới khi bạn duyệt sau QC.
- **Skip nền tảng trong suite:** Trên Windows không nâng quyền thiếu `SeCreateSymbolicLinkPrivilege` (`WinError 1314`), test `test_scoped_write_symlink_escape_denied` skip (`36/4,632` toàn suite `tron-bo` đều là skip theo nền tảng/môi trường); hành vi thoát ra ngoài qua liên kết NTFS đã được kiểm chứng thật và PASS qua `test_scoped_write_windows_ntfs_junction_escape_denied` (`mklink /J`).

## Lệch spec chờ duyệt

không có

## Git

Nhánh làm việc: `feat/trien-khai-investigate-v2` (nhánh gốc: `dev`), trạng thái: chưa merge về `dev` (đợi xác nhận `commit` của bạn; đồng thời giữ nguyên cấu hình live tại `~/.gemini/config/plugins/` theo `2a`).

## Thời gian

Request `2026-11-21-0217-trien-khai-investigate-v2` · lane full · opened at 2026-11-21T02:19:38+07:00

| Phase | Wall clock | API request | Tool wait | Background job | Observed union | Unattributed | Times entered |
|---|---|---|---|---|---|---|---|
| idle | 0s | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | 1 |
| analyze | 4 min | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | 1 |
| spec | 10 min | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | 1 |
| plan | 1h 50min | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | 1 |
| qc | 1h 25min | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | 1 |
| report | 0s | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | 1 |
| Total | 3h 29min | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] |  |

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

Quality: wall-clock `3h 29min` theo đồng hồ phiên từ `02:19:38+07:00`; các công việc implement qua subagent/nhóm nằm trong khoảng `plan → qc` trước khi chuyển `set phase=qc`.

## Thân PR (soạn sẵn)

```markdown
## Summary
- Implement full V2 `work_kind=investigate` architecture (`M1`–`M6`) across `scripts/`, `hooks/`, `hooks/rust/tdq-dispatch/`, `skills/`, `agents/`, `tools/patches/`, and compiled `plugins/tdq-workflow-agy/`.
- Separate `work_kind = "build" | "investigate"` in `tdq_state.py` (`INVESTIGATE_PHASE_ROWS`, `_cli_approve` `ghi_moc_phase`, `_archify_gate`, `escalate-to-build --by`), add conditional R10/R14 waivers and `docs/tdq/bench/<slug>/` diagnostic isolation in `doc_lint.py` / `tdq_bench.py`, and publish `skills/tdq-conventions/references/investigate-mode.md` within the 3,500-token budget.
- Add Shard + Leader-Merge `evidence add|merge|render` with NTFS/POSIX lock (`O_EXCL`) & `worktree_required: false` in `tdq_team.py`, align 5-layer Deny-first `scoped-write` parity (`cmd /c`, `[IO.File]`, multi-ancestor realpath) and Weighted Burden per `sid` (`>=40` -> `[TDQ:DOC]`) while preserving `<25ms` ranged-read fast-path in Rust `tdq-dispatch.exe`.
- Add `tests/test_investigate_workflow.py` covering Python ↔ Rust adversarial parity, burden isolation, `TDQ_LOG=0`, and 4 historical simulation cases (`1056`, `1457`, `1346`, `1953`).

## Test plan
- [x] `py -3 -X utf8 scripts/tdq_test.py tron-bo --workers 1 --fresh --reuse off` → `4,596 passed, 36 skipped, 2,891 subtests passed` (`0` failed, `bo_sot=0`)
- [x] `cargo test` (`29 passed`) & `cargo clippy --all-targets -- -D warnings` (`0` warning)
- [x] `agy.exe plugin validate plugins/tdq-workflow-agy --strict --json` (`findings: []`) & `tools/install_agy_plugin.py --dry-run` (`exit 0`)
- [x] `tests/test_rust_latency_benchmark.py` (`Hot PreToolUse (Direct)` median `14.35 ms <= 25.0 ms`) & independent `tdq-qc-tester` sign-off (`PASS everything`)
```
<!-- tdq-archify-binding:start -->
<!-- manifest: 2026-11-21-0217-trien-khai-investigate-v2.manifest.json -->
<!-- manifest_digest: cb7abc674409c9efa42f5f633081c8548f80953e8436c46ac2a3c6ecb1888fff -->
<!-- tdq-archify-binding:end -->