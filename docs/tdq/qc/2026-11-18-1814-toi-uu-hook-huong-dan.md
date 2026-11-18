# QC — Tối ưu hiệu năng lõi hook, chuyển sang chỉ dẫn 4 phần & dọn cổng (R1+R2+R3)

Ngày: 2026-11-18 · Plan: ../plan/2026-11-18-1814-toi-uu-hook-huong-dan.md · Vòng: 2 (Mức `ultra`)
Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

| # | Hạng mục | Lệnh đã chạy | Kết quả | PASS/FAIL |
|---|---|---|---|---|
| Q1 | Độ trễ `PreInvocation` (`<= 150 ms`), `PreToolUse` (`<= 100 ms`, `command_gate <= 130 ms`), `Stop` (`<= 100 ms`), `PostToolUse` thu hẹp | `py -3 docs/tdq/bench/2026-11-18-1814-toi-uu-hook-huong-dan/bench_dispatch.py --n 12` | `PreInvocation` `126,1 ms` (`141,9 ms` ở lần đo `tdq-qc-tester`); mọi `PreToolUse` `69,5–78,2 ms`; `run_command (git status)` `93,4 ms` (`94,3 ms` `qc-tester`); `Stop` `77,3 ms` (`75,9 ms` `qc-tester`); `PostToolUse` bỏ `run_command`/`read_file` | PASS |
| Q2 | Triệt tiêu `0/8` `search_malformed`, `0/2` `tick_loop`, `SEARCH` Hướng A + `rtk bypass grep` + dedup malformed | `py -3 -m pytest tests/test_hook_dispatch_r1_r3.py -k "search or tick or malformed"` | `3 passed` (`0/8` malformed, `0/2` tick deny, Hướng A ân xá 1 / chặn 2, malformed dedup 1x/lượt) | PASS |
| Q3 | Tự sửa `overwrite` (`call_mcp_tool` `Arguments` cả `args`/`arguments`, `LSP` `O(1)`, `SUBAGENT` `Workspace="inherit"`) | `py -3 -m pytest tests/test_hook_dispatch_r1_r3.py -k "overwrite"` | `1 passed` (giữ nguyên `ServerName`/`ToolName`, hỗ trợ cả `dict` & `str`) | PASS |
| Q4 | Thẻ `metadata.user_markdown` 4 phần `22/22` mã, tách `model_line <= 160` và `user_card <= 1.200`, khử lặp | `py -3 -m pytest tests/test_gate_guidance.py tests/test_hook_dispatch_r1_r3.py -k "user_markdown or guidance"` | `11 passed` (`22/22` mã AGY đủ 4 phần) | PASS |
| Q5 | Bảo toàn `9/9` cổng cứng, `"1a"` lặp mở `[TDQ:APPROVE]`, `Stop` `continuationActive` 1x, `LOG` mềm, dọn > 7 ngày | `py -3 -m pytest tests/test_hook_dispatch_r1_r3.py -k "hard or stop or repeated_1a or cleanup"` | `2 passed` (bao gồm `TDQ:GIT` + `TDQ:TEAM` `detect_subagent`) | PASS |
| Q6 | `hooks.json` `dispatch.py`, loại `7` script thừa khỏi gói AGY (`3` R3 + `4` QC2.2), giữ nguyên `~/.gemini`, `validate --strict` | `py -3 -m pytest tests/test_agy_plugin_validate.py tests/test_command_gate.py -q` & `agy.EXE plugin validate --strict --json plugins/tdq-workflow-agy` | `11 passed`; `findings: []`; `7/7` file thừa vắng ở plugin (`ast_checked_py=81`) nhưng còn ở `hooks/scripts/`; `~/.gemini/.../hooks.json` giữ mtime `2026-11-18 13:39:48` | PASS |
| Q7 | Linter, `doc_lint`, `token_budget`, Smoke, Runtime (`<= 120s`), `tron-bo`, `tdq-qc-tester` vòng 2 | `py -3 scripts/tdq_test.py tron-bo --workers 4 --fresh --reuse off` + `tdq_test.py so` + `tdq-qc-tester` | **`4,399` test PASS** (`0` fail, `35` skipped, `350.31s`, `tron_bo=2/2`, `radius misses: 0`); `tdq-qc-tester` (`dbadc3aa`): `VERDICT: PASS everything` | PASS |
| QC2.1 | Vá `TDQ:GIT` (nhánh `/`, `worktree add`, `Co-Authored-By`), `TDQ:TEAM` `detect_subagent`, dedup `malformed`, `return` `TDQ:STATE`, `prompt_sha` > `64 KB`, lock `repo_root` cache | `py -3 -m pytest tests/test_core_hook_perf_search.py tests/test_hook_dispatch_r1_r3.py tests/test_bash_gate.py tests/test_edit_gate.py -q` | Nằm trong `274 passed, 40 subtests` (`61.4s`) của `tdq-qc-tester` + test đơn vị `tdq_state` lock | PASS |
| QC2.2 | Tối ưu `Stop` (`1` `git status`, bỏ `diff HEAD` khi sạch/untracked), `rtk` skip builtin + cache mtime (`93,4 ms`), loại `4` script AGY thừa + `bench_dispatch.py` | `py -3 -m pytest tests/test_command_gate.py tests/test_rtk_integration.py tests/test_agy_plugin_validate.py tests/test_stop_gate.py -q` + `bench_dispatch.py --n 12` | Pass 100% trong `80 passed` & `274 passed, 40 subtests`; `Stop` `235,1 ms` → `77,3 ms`; `git status` `132,3 ms` → `93,4 ms` | PASS |
| QC-F1 | Trọn bộ `tron-bo` sau lần sửa code cuối + `tdq_test.py so` | `py -3 scripts/tdq_test.py tron-bo --workers 4 --fresh --reuse off` & `py -3 scripts/tdq_test.py so` | `cases=4399` PASS (`0` fail, `35` skipped), `tron_bo=2`, `budget=2`, `radius misses: 0` | PASS |
| QC-F2 | Hồi quy toàn bộ vùng `Chạm:` trong plan | `tron-bo` 210 module + 9 module trọng tâm (`274 passed, 40 subtests`) | `100%` node chạm có test và đều xanh (`0` node `KHÔNG CÓ TEST`) | PASS |
| QC-F3 | Ràng buộc kiến trúc §5 (`scripts/` không import `hooks/`, `state.json` 1 nguồn ghi, `i18n_check` 3 tầng) | AST check `scripts/*.py`, kiểm writer `state.json`, `py -3 scripts/i18n_check.py <15 touched/new files>` | `0` vi phạm import `hooks/`; `state.json` chỉ ghi bởi `tdq_state.py`; `0` dòng tiếng Việt mới trên `15/15` file (còn 9 dòng legacy kế thừa trong `hooks/scripts/` khi quét trực tiếp bản biên dịch) | PASS |
| QC-F4 | Clean code (5 câu hỏi SOLID + `ruff C901 <= 10`) | `py -3 -m ruff check --select C901 --config "lint.mccabe.max-complexity=10" ...` + rà soát 5 nguyên tắc | `ruff` trả `rc=0: All checks passed!`; `5/5` câu hỏi SOLID đạt | PASS |
| Smoke | Vòng đời đầy đủ 6 sự kiện qua `dispatch.py` đã biên dịch (`timeout <= 120s`) | `qc_smoke_runtime.py::run_smoke_test()` | `SessionStart -> PreInvocation -> PreToolUse(lsp overwrite) -> PostToolUse -> PostInvocation -> Stop(continue -> continuationActive allow)` PASS trong `3.30s` (trần `120s`) | PASS |
| Runtime | Cạnh tranh NTFS 6 luồng, lặp `"1a"`, dọn `.tdq-runtime` > 7 ngày, `TDQ_LOG` bật/tắt (`timeout <= 120s`) | `qc_smoke_runtime.py::run_runtime_test()` | `6` tiến trình song song không hỏng JSONL, `"1a"` lặp reset lượt, xóa rác 9 ngày, `TDQ_LOG=0` tắt log stderr; PASS trong `3.24s` (trần `120s`) | PASS |
| Skills | Kiểm 3 skill `Dùng:` (`tdq-conventions`, `agy-customizations`, `tdq-lean`) + `install_agy_plugin.py --dry-run` | `qc_smoke_runtime.py::run_skill_contracts()` | `4/4` `exit 0`; `python_probe` `C:\...\Python313\python.EXE ok=True` | PASS |
| `tdq-qc-tester` | Agent QC độc lập kiểm lại vòng 2 (`Q1, QC2.1, QC2.2, Q7`) | Subagent `tdq-qc-tester` (`dbadc3aa-9964-41c7-8fbc-09b99883c2e1`) | `Q1/QC2.1/QC2.2/Q7` PASS, `DEFECTS`: chỉ `1` lưu ý Low legacy `i18n`, `VERDICT: PASS everything` | PASS |

## Bằng chứng

### Q1 — Benchmark `bench_dispatch.py --n 12` (Vòng 2 sau tối ưu)
```text
PreInvocation (mid-turn 0-git)         median= 126.1ms p90= 127.8ms rc=0  (tdq-qc-tester: 141.9ms)
PreToolUse read_file                   median=  74.8ms p90=  76.5ms rc=0
PreToolUse edit_file                   median=  69.5ms p90=  69.9ms rc=0
PreToolUse run_command (echo)          median=  78.2ms p90=  80.7ms rc=0
PreToolUse run_command (git status)    median=  93.4ms p90=  96.2ms rc=0  (tdq-qc-tester: 94.3ms)
PreToolUse grep_search                 median=  75.6ms p90=  77.5ms rc=0
PreToolUse call_mcp_tool (lsp)         median=  71.1ms p90=  73.2ms rc=0
PreToolUse invoke_subagent             median=  72.5ms p90=  73.9ms rc=0
PostToolUse grep_search                median=  73.3ms p90=  75.5ms rc=0
PostInvocation                         median=  71.5ms p90=  73.1ms rc=0
Stop                                   median=  77.3ms p90=  79.3ms rc=0  (tdq-qc-tester: 75.9ms)
```

### Q7, Smoke/Runtime, Lint & `tdq-qc-tester` (Vòng 2)
```text
[TDQ:TEST] PASS — scope=full backend=pytest tests=4399 skipped=35 in 350.31s.
receipt: docs/tdq/cache/test-runs/60973b827e4bb0d6/836788aac4b3411ebcbefffb144db054/result.json
[2026-11-18T22:57:44+07:00] tdq_test: so request=2026-11-18-1814-toi-uu-hook-huong-dan tron_bo=2 bo_sot=0 budget=2
Smoke: 3.30s (cap 120s) · Runtime: 3.24s (cap 120s) · ruff C901<=10: rc=0 · i18n_check (15 touched/new): 0 line(s)
agy.EXE plugin validate --strict --json plugins/tdq-workflow-agy -> findings: [] · ast_checked_py=81 · hooks=13 copied (17 total .py in hooks/scripts/)
tdq-qc-tester (dbadc3aa) vòng 2: Q1, QC2.1, QC2.2, Q7 PASS (274 passed, 40 subtests in 61.4s), VERDICT: PASS everything
```

### QC-F4 — Trả lời 5 câu hỏi Clean Code (`clean-code.md`)
- **SRP**: Đạt (`_find_git_head`, `repo_root`, `_has_tracked_git_changes`, `_has_banned_agy_git`, `_shell_change_check`, `gate_guidance`, `dispatch`, `_all_segments_non_rtk`).
- **OCP**: Đạt (`GUIDANCE_TABLE`, `NON_RTK_BUILTINS`, `EXCLUDED_AGY_HOOKS`, `_PRETOOL_TABLE`, `BRANCH_PATTERNS` + `WORKTREE` + `BAD_MSG` dùng chung).
- **LSP**: Đạt (cùng kiểu trả về và hợp đồng fail-open/tuần tự trên mọi nhánh).
- **ISP**: Đạt (chỉ truyền đường dẫn/chuỗi/payload cần thiết; `_shell_change_check` dùng chung 1 biến `status` giữa `repo_status_digest` và `repo_status_paths`).
- **DIP**: Đạt (dùng chung helper `BRANCH_PATTERNS`/`WORKTREE`/`BAD_MSG` của `bash_gate`, `_common.detect_subagent`, `gate_guidance`, CLI `tdq_state.py`).

## Lệch spec chờ duyệt
không có

## Kết luận
PASS toàn bộ (Vòng 2: `Q1–Q7`, `QC1.1`, `QC2.1`, `QC2.2`, `QC-F1..QC-F4`, 3 skill, Smoke `3.30s`, Runtime `3.24s`, `tron-bo` `4,399` test xanh và xác nhận độc lập bởi `tdq-qc-tester`). Sẵn sàng chuyển sang pha `report`.
