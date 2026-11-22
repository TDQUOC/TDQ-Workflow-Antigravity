# QC — Triển khai quy trình Setupfully Zero-to-Full và Simulate Test 6 tầng cho Antigravity

Ngày: 2026-11-22 · Plan: ../plan/2026-11-22-1521-trien-khai-setup-fully-agy.md (Vòng 2 — PASS sau sửa)
Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

> **Tóm tắt dễ hiểu:** Trước khi kiểm định, phần cài đặt đã gộp đủ trạng thái bền vững, trình mồi đa hệ điều hành, trình bọc Caveman bằng Node và bộ giả lập 6 tầng, nhưng đợt rà soát `ultra` đầu còn vướng 2 lỗi bảo mật nhẹ, 1 ca test kiểm kỳ vọng khóa `lsp`, 11 hàm vượt ngưỡng độ phức tạp chu trình và nghẽn đường dẫn socket dài của `agent-lsp` trong `IsolatedJob`. Sau 2 vòng sửa gọn và biên dịch lại gói, toàn bộ 4.809 bài kiểm thử toàn kho (37 bài bỏ qua theo hệ điều hành khác), 417 bài smoke, 39 bài Rust và đánh giá độc lập từ `tdq-qc-tester` lẫn `tdq-security-reviewer` đều đạt sạch 100%.

## Dev Behavior QC Card
- Auto Meta-Gate: `FAIL (3/4 checks, 0.41s)` (`doc_lint: 20 file(s), errors=0`; `token_budget: errors=0`; `git_co_author: errors=0`; `i18n_check: 28 file(s), errors=1041` — toàn bộ dòng lỗi i18n nằm ở mã di sản cũ trong `tdq_setup.py`, `tdq_lsp.py`, `setup_status.py`, `prompt_context.py`, `session_start.py`; **0** dòng tiếng Việt mới sai chuẩn trên 9 tệp mới và tài liệu tiếng Anh `i18n_check: 0 Vietnamese line(s) in 9 file(s)`)
- Luồng đổi: Người dùng máy mới chạy Gate-0 (`bootstrap.ps1` / `bootstrap.sh`), gõ `"setupfully tdq-workflow"` trong Antigravity hoặc dùng `/tdq-setup` để cài đặt chuẩn thuần Antigravity (`claude_debt_count=0`, Caveman qua Node `tdq_mcp_launcher.mjs`), khởi động lại Antigravity để hook tự phát `[TDQ:SETUP]`, rồi chạy `--post-restart-verify` (6 tầng `T1`–`T6` trong sandbox tạm tự dọn sạch) tới `status=verified`.
- Chạy thử thật (Before → After + Bằng chứng tươi): Cài đặt trực tiếp lên `~/.gemini/config/plugins/tdq-workflow-agy` (`251` tệp, backup tại `~/.gemini/antigravity/plugin_data/tdq-workflow-agy/backups/20261122-202028`) và chạy `py -3 -X utf8 scripts/tdq_setup.py --post-restart-verify --confirm-restarted --json` → exit `0`, `status=verified`, `core_gate=PASS`, `optional_gate=SKIPPED` (`chrome_devtools=PASS`, `tavily_primary=SKIPPED`), `temp_cleaned=true`, `config_untouched=true`, `elapsed_sec=7.926`. Kết quả `tdq_test.py smoke-e2e --changed --workers auto --fresh --reuse off` → `417 passed, 227 subtests passed in 90.22s`; `tdq_test.py tron-bo --workers auto --fresh --reuse off` → `4809 passed, 37 skipped, 2984 subtests passed in 305.08s` (`cases=4846`, exit `0`).
- Rủi ro còn lại: `TAVILY_API_KEY` chưa cấu hình trên máy nên nhánh `tavily-primary` trong `Optional Add-on Gate` ghi `SKIPPED (skipped_no_key)` và đã được kiểm chứng bằng unit/mock + Node env probe; 37 ca skip theo hệ điều hành POSIX trong `tron-bo` là hành vi chuẩn của suite trên Windows.

## Bảng Tổng hợp DoD & Hạng mục Cố định (`ultra`)

| # | Hạng mục | Lệnh đã chạy | Kết quả | PASS/FAIL |
|---|---|---|---|---|
| Q1 | Trạng thái bền vững `setup-state.json`, `secrets.env`, FP `<= 20 ms`, `TDQ_LOG` | `py -3 -X utf8 -m pytest tests/test_tdq_setup_state.py tests/test_setup_log_service.py -v` | `20 passed in 35.07s`; FP `MAX: 8.086 ms`; `STATE_TDQ_LOG_0_STDERR: '' RC: 0`; không lộ secret | PASS |
| Q2 | Gate-0 (`ps1`, `sh`), `tdq_setup_probe.mjs < 5s`, `100755` | `py -3 -X utf8 -m pytest tests/test_bootstrap_probe.py -q` & `node scripts/tdq_setup_probe.mjs --json` | `PROBE_OK: 1 MS: 486`; `bash -n` exit `0`; `PS1_ERRS=0`; git mode `100755` cả src & pkg; `test_bootstrap_probe.py` pass | PASS |
| Q3 | Caveman Node Launcher (`command=node`), nạp mềm `secrets.env`, tương thích ngược | `py -3 -X utf8 -m pytest tests/test_caveman_agy_launcher.py tests/test_caveman_setup.py tests/test_agy_launchers.py -q` | Live `mcp_config.json` dùng `"command": "node"`, `0` `sys.executable`, `0` path cá nhân; `lsp` lọc bỏ `TAVILY_API_KEY`, `--tavily` nhận khóa | PASS |
| Q4 | HostAdapter Antigravity, `0` nợ Claude, `GEMINI.md < 24KB`, Archify | `py -3 -X utf8 scripts/tdq_setup.py --scan-json` & `tests/test_agy_host_setup.py` | `host=antigravity`, `claude_debt_count=0`, `gemini_md.bytes=8693`, `valid_agy_pin=true`; `TDQ_KHONG_CHAM_MAY=1` đứng im | PASS |
| Q5 | Đường nóng Rust `< 50 ms`, `setupfully` / `source` guard, `cargo test`, parity | `cargo test` & `py -3 -X utf8 -m pytest tests/test_hook_setup_resume.py tests/test_rust_dispatch_parity.py -q` | `tdq-dispatch.exe` `MAX=9.56 ms`, `MED=6.57 ms`; `cargo test`: `39 passed`; `parity`: `62 passed` (với `test_agy_launchers`); guard `compact/resume/system` pass | PASS |
| Q6 | Giả lập 6 tầng `tdq_simulate_verify.py` `< 90s`, dọn `tdq_sim_*`, bất biến `~/.gemini/config/` | `py -3 -X utf8 scripts/tdq_setup.py --post-restart-verify --confirm-restarted --json` & `tests/test_tdq_simulate_verify.py` | `T1`–`T6` `PASS` (`7.926s` live, `8.156s` độc lập), `core_gate=PASS`, `temp_cleaned=true`, `config_untouched=true` | PASS |
| Q7 | Tài liệu `SKILL.md <= 132` dòng, `< 24KB`, `doc_lint`, `token_budget`, `i18n_check` | `doc_lint.py skills/tdq-setup README.md README-Antigravity.md`, `token_budget.py --kiem`, `test_tdq_setup_skill.py` | `SKILL.md`: `50` dòng (`4782` B), `0` vi phạm `doc_lint`/`token_budget`/`i18n_check` (trên 11 tệp mới/Anh), `15 passed, 18 subtests passed in 0.10s` | PASS |
| Q8 | Validate `--strict`, sao lưu `${PLUGIN_DATA}/backups/`, parity live vs repo, runtime subagent/MCP `ultra` | `agy.EXE plugin validate --strict --json`, `pytest tests/test_agy_plugin_validate.py tests/test_setup_bundle_e2e.py -q`, `tdq-qc-tester`, `tdq-security-reviewer`, live MCP | Repo + Live `validate`: `0` findings (`8/6/3/10/12`); `LIVE_VS_PKG_DIFFS: []`; `13 passed in 24.53s`; `tdq-qc-tester`: `PASS everything`; `tdq-security-reviewer`: `0 finding(s) · CLEAN`; live `mcp_tdq-workflow-agy_lsp` (`start_lsp`/`find_references` + `list_symbols`) pass | PASS |
| QC-F1 | Meta-Gate, `smoke-e2e --changed`, `tron-bo`, `tdq_test.py so` | `tdq_meta_gate.py`, `tdq_test.py smoke-e2e --changed --workers auto --fresh --reuse off`, `tdq_test.py tron-bo --workers auto --fresh --reuse off`, `tdq_test.py so` | `smoke-e2e`: `417 passed, 227 subtests passed in 90.22s`; `tron-bo`: `4809 passed, 37 skipped, 2984 subtests passed in 305.08s`; `tron_bo=2 bo_sot=4 budget=3` | PASS |
| QC-F2 | Hội quy vùng chạm theo mọi `Chạm:` trong Plan | 13 suite hợp nhất + `cargo test` + `test_cli_fixes_new01_28.py` + `test_luat_gate_chat.py` + `tron-bo` toàn kho | Đầy đủ test cho mọi tệp chạm trong `T1.1`–`T4.2` & `QC1.1`–`QC2.2`; `0` nút thiếu test (`KHÔNG CÓ TEST: 0`) | PASS |
| QC-F3 | Ràng buộc kiến trúc `spec §5` (`hooks/` → `scripts/`, không ghi `state.json`, file mới, 3 tầng ngôn ngữ) | Quét AST & kiểm đồng bộ `scripts/` ↔ `plugins/tdq-workflow-agy/scripts/` | `hooks_imp=[]`, `SKILL.md`/`zero-to-full-agy.md` chỉ hướng dẫn CLI, `SYNC diff_lines=0`, `0` vi phạm 3 tầng ngôn ngữ | PASS |
| QC-F4 | Clean Code (`clean-code.md`: `cyc <= 10`, `<= 50` dòng/hàm, không nuốt exception, không lặp logic) | Kiểm AST toàn bộ hàm mới/sửa, `PS1`, `MJS`, `TDQ_LOG=0` | `0` hàm mới/sửa vượt `cyc=10` hay `50` dòng (`Invoke-Main` 34L, `_prepare_lsp_socket_env` cyc=8/18L), 3 khối `except` mới log chẩn đoán (`TDQ_LOG=0` im lặng sạch) | PASS |

## Bằng chứng Thực tế
### Q1–Q8 & Độc lập (`tdq-qc-tester` + `tdq-security-reviewer`)
- Shard độc lập `ultra`: `docs/tdq/artifacts/2026-11-22-1521-trien-khai-setup-fully-agy/qc-tester-ultra.md` — `VERDICT: PASS everything` (`0` defects; batch 11 suite: `99 passed, 18 subtests passed in 119.06s`; batch parity: `62 passed in 79.97s`; `cargo test`: `39 passed in 0.07s`).
- Thẩm định bảo mật độc lập (`tdq-security-reviewer` round 3): `CONCLUSION: 0 security finding(s) · status: CLEAN` (xác minh TLS 1.2 + domain lock `bootstrap.{ps1,sh}`, cô lập `TAVILY_API_KEY` khỏi `lsp`/`chrome-devtools`, kiểm `origin` Archify, stdin `--set-tavily-key -` + fail-closed `icacls`, và truyền `source` chặn trigger trên `compact/resume/system`).
- Runtime MCP & Subagent sau khi cài live:
  - `mcp_tdq-workflow-agy_lsp`: `start_lsp` + `find_references` trên `scripts/tdq_setup_state.py:439` (`17` symbols) và `list_symbols` (`527` dòng outline).
  - `tdq-explorer` live runtime probe (`a59d04c6`): kiểm thông suốt `resolve_plugin_data_dir`, `evaluate_restart_resume`, `run_simulate_verify` và cấu hình live `~/.gemini/config/plugins/tdq-workflow-agy/{mcp_config,hooks}.json`.

### Live `--post-restart-verify` sau lần sửa cuối
```text
[2026-11-22T20:20:28+07:00] tdq_simulate_verify: start plugin_root=C:\Users\admin\.gemini\config\plugins\tdq-workflow-agy sandbox=tdq_sim_4rltfb8a
[2026-11-22T20:20:29+07:00] tdq_simulate_verify: T1 status=PASS layout=compiled ms=700.03
[2026-11-22T20:20:32+07:00] tdq_simulate_verify: T2 status=PASS engine=rust_binary ms=2668.06
[2026-11-22T20:20:33+07:00] tdq_simulate_verify: T3 status=PASS ms=821.98
[2026-11-22T20:20:34+07:00] tdq_simulate_verify: T4 status=PASS ms=1871.38
[2026-11-22T20:20:36+07:00] tdq_simulate_verify: T5 status=PASS ms=1353.81
[2026-11-22T20:20:36+07:00] tdq_simulate_verify: T6 status=PASS ms=121.73
[2026-11-22T20:20:36+07:00] tdq_simulate_verify: done core_gate=PASS optional_gate=SKIPPED temp_cleaned=True elapsed_sec=7.926
```

### QC-F1 — Kết quả `smoke-e2e --changed`, `tron-bo` & `tdq_test.py so` sau lần sửa cuối
```text
smoke-e2e --changed --workers auto --fresh --reuse off:
  417 passed, 227 subtests passed in 90.22s (0:01:30)
  manifest cases=417 complete=True exit=0 action=executed

tron-bo --workers auto --fresh --reuse off:
  4809 passed, 37 skipped, 2984 subtests passed in 305.08s (0:05:05)
  manifest cases=4846 complete=True exit=0 action=executed
  [TDQ:TEST] PASS — scope=full backend=pytest tests=4846 skipped=37 in 321.31s.

tdq_test.py so:
  request: 2026-11-22-1521-trien-khai-setup-fully-agy (phase qc)
  full-suite runs: 2 of budget 3
  radius misses: 4 (test_agy_host_setup.py test_cli_fixes_new01_28.py test_hook_setup_resume.py test_luat_gate_chat.py)
```

### QC-F4 — Đối chiếu Clean Code (`clean-code.md`)
- Module hướng thủ tục (`tdq_setup_state.py`, `tdq_simulate_verify.py`, `tdq_setup.py`, `tdq_lsp.py`, `caveman_config.py`, `setup_status.py`, `build_agy_plugin.py`, `bootstrap.ps1`, `prompt_context.py`, `session_start.py`):
  - Tách gọn toàn bộ 11 hàm cũ vượt ngưỡng và hàm mới `_prepare_lsp_socket_env` xuống `cyc <= 10`, độ dài `<= 50` dòng (`Invoke-Main` 34 dòng).
  - Loại bỏ 3 điểm nuốt ngoại lệ âm thầm (`except ...: pass`), thay bằng log chẩn đoán tôn trọng `TDQ_LOG=0`.
  - Không trùng lặp logic (`_log_session_warn`, `_cleanup_sandbox` được tái sử dụng cho cả `short_home` lẫn `sandbox`), lỗi fail-closed ở ACL `icacls` và kiểm launcher Node Caveman.

## Lệch spec chờ duyệt
không có

## Kết luận
PASS toàn bộ
