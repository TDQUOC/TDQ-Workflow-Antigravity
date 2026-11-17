# QC — Tích hợp cộng sinh RTK tối ưu token và tự động kiểm/cài cho Antigravity
Ngày: 2026-11-17 · Plan: ../plan/2026-11-17-0325-tich-hop-rtk-antigravity.md · Vòng: 2 (`muc_qc = ultra` · `tdq-qc-tester` 2 vòng + `tdq-security-reviewer`)
Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

| # | Hạng mục | Lệnh đã chạy | Kết quả | PASS/FAIL |
|---|---|---|---|---|
| Q1 | Hiệu năng `PreToolUse` collapse `command_gate.py` | `py -3 -X utf8 -m pytest tests/test_command_gate.py -q` + 7x live `command_gate.py` (`git status`) | `7 passed in 0.79s`; live median `TDQ_RTK=0` = `71.50 ms` (`tdq-qc-tester`: `73.22 ms`, `<= 110 ms`), `TDQ_RTK=1` = `126.52 ms` (`tdq-qc-tester`: `128.63 ms`, `<= 150 ms`) + `overwrite.CommandLine` `rtk git status` | PASS |
| Q2 | Chặn lách `[TDQ:SEARCH]` & giữ thuần `search_rules.py` | `py -3 -X utf8 -m pytest tests/test_search_rules.py -q` + `test_log_module_thuan_khong_tu_in` + `phan_loai` variants | `101 passed` (`stdout = 0B`, ngân sách `rtk read` = `32768`); chặn đủ `rtk grep`, `rtk bypass rg`, `rtk proxy findstr`, `rtk.exe rg`, `rtk.cmd bypass rg`, `rtk.bat rg` | PASS |
| Q3 | Collapse `command_gate`, API cũ & cài `SHA256` | `py -3 -X utf8 -m pytest tests/test_rtk_integration.py tests/test_hook_windows.py tests/test_bash_gate.py tests/test_installer_rtk_trigger.py tests/test_tdq_setup_rtk.py tests/test_setup_status.py -q` + live ISO stderr & `TDQ_LOG=0` | `138 passed, 48 subtests passed in 21.08s`; API `bash_gate`/`search_gate` giữ nguyên cho Codex/test; `TDQ_KHONG_CHAM_MAY=1` chặn chạm máy; `install.sh` LF (`CR=0`, `bash -n` rc=0) | PASS |
| Q4 | Biên dịch `plugins/tdq-workflow-agy/`, `agy validate`, `token_budget` & parity | `py -3 -X utf8 tools/build_agy_plugin.py` + `agy.EXE plugin validate plugins/tdq-workflow-agy --strict --json` + `scripts/token_budget.py --kiem` + `test_agy_plugin_validate` + `test_hooks_dual_protocol` | `build_agy_plugin` `status=OK` (`ast_checked_py=83`, `md_checked_budget=22`); `agy validate` `"findings": []` (`12 skills, 6 agents, 10 rules, 3 mcpServers, 6 hooks`); `token_budget --kiem` exit `0`; `9 passed`; parity local `188` files `BYTE_DIFFS=[]` (`182/182` `sha256` qua `tdq-qc-tester`) | PASS |
| Q5 | Nghiệm thu sống `rtk` + `rg` (`2a`), trọn bộ `tron-bo` & QC `ultra` | `rtk --version` + `rtk gain` + `tdq_setup.py --check-rtk` + `tdq_test.py tron-bo --workers 1 --fresh --reuse off --timeout 1800` + `tdq_test.py so --json` + `tdq-qc-tester` Vòng 2 + `tdq-security-reviewer` | `rtk 1.2.0` (`>= 0.25.0`), `rg 15.2.0`, `rtk gain` exit `0` (`Total commands: 23`); `tron-bo` (`task-3991`): `4313` cases collected, `4278 passed`, `35 skipped`, `0 failed` trong `1167.36s` (`status=PASS`, `bo_sot=0`); `tdq-qc-tester`: `DEFECTS: none · VERDICT: PASS everything`; `tdq-security-reviewer`: `VERDICT: SAFE (0 finding(s))` | PASS |
| QC-F1 | Receipt `tron-bo` & `tdq_test.py so` khớp byte cuối | `docs/tdq/cache/test-runs/b890454302b8b40d/43efc6370f3342e0ba0340d7c6179214/result.json` + `py -3 -X utf8 scripts/tdq_test.py so --json` | `status=PASS`, `tests_run=4313`, `skipped=35`, `details_complete=True`, `tron_bo=5`, `bo_sot=0`, `0` file mới hơn receipt; `sha256: b1baf5745a6a599650ccffb993942cfe5248aa6e9a5bca673f029d8f96fc4f24` | PASS |
| QC-F2 | Hồi quy vùng chạm & kiểm hợp đồng tích hợp | `tests/test_installer_rtk_trigger.py` + `tests/test_rtk_integration.py` + `tests/test_command_gate.py` + `tests/test_search_rules.py` + `tests/test_agy_plugin_validate.py` + `tests/test_hooks_dual_protocol.py` | `154 passed in 16.87s` sau bản vá cuối (`install.py`, `rtk_integration.py`, `cli_fixes_a.py`, `install_agy_plugin.py`); không có binary/source GPL/AGPL của `rtk`/`rg` trong repo hay plugin (`MIT` sạch) | PASS |
| QC-F3 | Ràng buộc kiến trúc, tài liệu & bảo mật | `py -3 -X utf8 scripts/doc_lint.py --pair ...` + `scripts/i18n_check.py` + kiểm tra an toàn `tdq-security-reviewer` | `doc_lint --pair` `0` violation(s) exit `0`; `0` dòng tiếng Việt mới trong `install.py`/`rtk_integration.py`/`command_gate.py`/`install_agy_plugin.py`/`common_utils.py`; `.tdq-runtime/` trong `.gitignore`; `0` lỗ hổng bảo mật (`SAFE`) | PASS |
| QC-F4 | Clean Code Invariants (`clean-code.md` Self-check + McCabe `C901`) | `py -3 -X utf8 -m ruff check --no-cache --select F,E,B,C901 --config "lint.mccabe.max-complexity=10"` trên các module mới/sửa & kiểm số dòng AST | 5/5 câu trả lời ĐẠT (`C901 <= 10` và độ dài `<= 50` cho toàn bộ hàm mới/tách; `0` lỗi `F,E,B,C901` trên `rtk_integration.py`, `command_gate.py`, `install_agy_plugin.py`, `test_command_gate.py`) | PASS |

## Lịch sử 2 vòng QC (`muc_qc = ultra`)

- **Vòng 1 (`tdq-qc-tester` + `tdq-security-reviewer`):** `tdq-qc-tester` chỉ ra `QC1.1`–`QC1.3` (hàm dài/phức tạp ở `bash_gate._check_bash_reminders`, `search_rules._chuan_hoa`, `cli_fixes_a._sync_rtk_search_rules`; trùng lặp `import_rtk_integration` và `hooks.json` CRLF ở `install.py`; thiếu ISO stderr `_log` ở `tdq_setup.py` + `session_start.py`) và `QC1.4` (biên dịch/chạy lại `tron-bo`). Song song `tdq-security-reviewer` chỉ ra 4+2 phát hiện bảo mật (`CWD`/`.cmd` shim hijacking trong `rtk_integration.py` + `setup_status.py`, biến thể lách `rtk bypass --`/wrapper/subshell `(C:\...)` trong `search_rules.py` + `cli_fixes_a.py`, CRLF ở `install.sh`, `.tdq-runtime/` trong `.gitignore`).
- **Sửa vòng 1 (`QC1.1`–`QC1.5`) & lần chạy giữa (`task-3864`):** Tách nhỏ hàm, hợp nhất `import_rtk_integration` vào `tools/patches/common_utils.py`, thêm ISO stderr `_log` (tắt qua `TDQ_LOG=0`/`--khong-log`), vá toàn bộ 4+2 điểm bảo mật và nâng shim test `test_command_gate.py` sang `rtk.exe` zipapp cô lập `PATH`/`HOME`; `tron-bo` `task-3864` đạt `PASS` `4313` cases (`0` failed).
- **Vòng 2 (`tdq-qc-tester` + `tdq-security-reviewer`) & chốt sạch cuối (`task-3991`):** Lượt quét đầu Vòng 2 xác nhận `Q1`–`Q5` PASS nhưng bắt 2 điểm `ruff` còn sót ở `QC1` (`install._handle_rtk_trigger` `C901=11`, `install_agy_plugin.py#L14` `E402`, `rtk_integration.py#L557` `E501`, `_sync_rtk_search_rules` 39 dòng). Sau khi tách `_prompt_rtk_install` (`17` dòng), gán `# noqa: E402`, xuống dòng chữ ký và đưa `_sync_rtk_search_rules` về `7` dòng (`_RTK_SEARCH_RULE_STEPS`), chạy lại `tron-bo` sạch (`task-3991`: `4313` cases, `0` failed trong `1167.36s`), cả `tdq-security-reviewer` (`VERDICT: SAFE · 0 finding(s)`) lẫn `tdq-qc-tester` Vòng 2 (`DEFECTS: none · VERDICT: PASS everything`) đều PASS toàn diện.

## Bằng chứng

### Q1
```text
py -3 -X utf8 -m pytest tests/test_command_gate.py -q -> 7 passed in 0.79s
Live command_gate.py --event PreToolUse (7-run median, git status):
- TDQ_RTK=0: 71.50 ms (runs=[70.87, 74.18, 74.25, 71.56, 71.5, 70.63, 71.46], tdq-qc-tester=73.22 ms <= 110 ms)
- TDQ_RTK=1: 126.52 ms (runs=[2248.85, 126.91, 124.75, 123.3, 124.17, 126.52, 131.22], tdq-qc-tester=128.63 ms <= 150 ms)
stdout={"decision": "allow", "overwrite": {"CommandLine": "rtk git status"}}
```

### Q2
```text
py -3 -X utf8 -m pytest tests/test_search_rules.py -q -> 101 passed
test_log_module_thuan_khong_tu_in PASSED · stdout=0B
phan_loai: rtk grep / rtk bypass rg / rtk proxy findstr / rtk.exe rg / rtk.cmd bypass rg / rtk.bat rg -> [TDQ:SEARCH], rtk read -> doc_file (32768 cap)
```

### Q3
```text
py -3 -X utf8 -m pytest tests/test_rtk_integration.py tests/test_hook_windows.py tests/test_bash_gate.py tests/test_installer_rtk_trigger.py tests/test_tdq_setup_rtk.py tests/test_setup_status.py -q
-> 138 passed, 48 subtests passed in 21.08s
TDQ_LOG=0 -> stderr rỗng; mặc định -> [YYYY-MM-DDTHH:MM:SS] ISO stderr; install.sh CR=0 (bash -n rc=0)
```

### Q4
```text
py -3 -X utf8 tools/build_agy_plugin.py -> status=OK, ast_checked_py=83, md_checked_budget=22
agy.EXE plugin validate plugins/tdq-workflow-agy --strict --json -> findings=[], components={agents:6, hooks:6, mcpServers:3, rules:10, sidecars:0, skills:12}
py -3 -X utf8 scripts/token_budget.py --kiem -> exit 0
py -3 -X utf8 -m pytest tests/test_agy_plugin_validate.py tests/test_hooks_dual_protocol.py -q -> 9 passed
local parity (C:\Users\admin\.gemini\config\plugins\tdq-workflow-agy): 188 files installed, BYTE_DIFFS=[] (tdq-qc-tester: 182/182 sha256 match)
```

### Q5 & QC-F1
```text
rtk --version -> rtk 1.2.0
rg --version -> ripgrep 15.2.0
rtk gain -> exit 0 (Total commands: 23, Total exec time: 982ms, avg 81ms)
py -3 -X utf8 scripts/tdq_setup.py --check-rtk --khong-log -> rtk · valid=True (1.2.0) | rg=C:\Users\admin\.local\bin\rg.EXE | muted=False
py -3 -X utf8 scripts/tdq_test.py so --json -> {"request": "2026-11-17-0325-tich-hop-rtk-antigravity", "tron_bo": 5, "bo_sot": 0, "modules_bo_sot": [], "ngan_sach": 3, "radius_complete": false}
task-3991 tron-bo: cases=4313, passed=4278, skipped=35, failed=0, status=PASS, wall=1167.36s
TDQ_RESULT sha256: b1baf5745a6a599650ccffb993942cfe5248aa6e9a5bca673f029d8f96fc4f24
```

### QC-F2 & QC-F3
```text
Post-final-edit focused suite: 154 passed in 16.87s (6 core suites) + 16 passed in 4.40s (installer + validate)
doc_lint --pair docs/tdq/spec/2026-11-17-0325-tich-hop-rtk-antigravity.md docs/tdq/plan/2026-11-17-0325-tich-hop-rtk-antigravity.md -> 0 violation(s), exit 0
tdq-security-reviewer -> VERDICT: SAFE (0 finding(s)) · status: CLEAN
MIT hygiene -> 0 embedded rtk/rg binary or source inside repo or plugins/tdq-workflow-agy/
```

### QC-F4
```text
1. Có thêm file/class/hàm/hằng số/config nào không được yêu cầu không? -> KHÔNG (chỉ tách helper thuần trong phạm vi M1–M5 và các bản vá QC1.1–QC1.5).
2. Có tạo interface cho 1 implement duy nhất không? -> KHÔNG (dùng hàm thuần phẳng dùng chung qua scripts/rtk_integration.py, tools/patches/common_utils.py, scripts/search_rules.py).
3. Có giữ nguyên xử lý lỗi và an toàn dữ liệu không? -> CÓ (timeout <= 2s fail-open, CWD/.cmd shim rejected, SHA256 fail-closed, TDQ_KHONG_CHAM_MAY=1 và non-TTY không tự chạm máy, atomic os.replace cho config/stamp).
4. Mọi hàm mới đều có test kiểm thử? -> CÓ (red -> green đủ các test đơn vị và E2E trong 7 file test mới/mở rộng, toàn bộ 4313 ca trong tron-bo đạt PASS).
5. Cyclomatic complexity <= 10 & chiều dài <= 50? -> CÓ (ruff C901 <= 10 trên mọi hàm mới/sửa; install._prompt_rtk_install=17L, install._handle_rtk_trigger=43L, cli_fixes_a._sync_rtk_search_rules=7L; 0 lỗi F,E,B,C901 trên rtk_integration.py, command_gate.py, install_agy_plugin.py, test_command_gate.py; riêng repo cũ còn E501/C901 legacy ngoài phạm vi sửa).
```

## Lệch spec chờ duyệt
không có

## Kết luận
PASS toàn bộ 5/5 hạng mục Definition of Done (`Q1`–`Q5`) và 4/4 fixed items (`QC-F1`–`QC-F4`) với `DEFECTS: none` (`tdq-qc-tester` Vòng 2) và `SAFE · 0 finding(s)` (`tdq-security-reviewer`).
