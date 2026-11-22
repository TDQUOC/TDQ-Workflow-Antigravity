# QC — Nhánh release Antigravity đa hệ điều hành và đồng bộ remote

Ngày: 2026-11-22 · Plan: ../plan/2026-11-22-1033-nhanh-release-agy-da-os.md (Vòng 1 + Vòng fix 1)
Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

## Dev Behavior QC Card

- **Auto Meta-Gate:** `PASS` trên tài liệu yêu cầu (`doc_lint` 0 lỗi, `git_co_author` 0 lỗi; lưu ý trên `scripts/build_portable.py:658` và `gate_guidance.json` chỉ có cảnh báo `i18n_check` tiền tồn từ trước, `0` lỗi ở mã nguồn mới viết).
- **Luồng đổi:** Thay đường dẫn cứng Windows `C:\Users\admin\...`, `npx.cmd` và `bin\tdq-dispatch.exe` sang bộ đôi khởi chạy Node đa nền tảng (`tdq_hook_launcher.mjs`, `tdq_mcp_launcher.mjs`), đồng bộ lại nhị phân Rust trên Ubuntu Linux (`musl`) và macOS Apple Silicon qua SSH, và bổ sung `build_portable.py --sinh-release-agy` tạo nhánh sạch `release/antigravity`.
- **Chạy thử thật (Before → After + Bằng chứng tươi):** Sau vòng sửa `QC1.1`–`QC1.2`, chạy `tdq_test.py tron-bo --workers auto --fresh --reuse off` đạt `4777` tests PASS (`skipped=36`, `0` fail, `0` radius misses); `agy.EXE plugin validate plugins/tdq-workflow-agy --strict --json` trả `0 findings`; `tests/test_agy_release_e2e.py`, `tests/test_remote_linux_simulation.py` và `tests/test_remote_mac_simulation.py` đạt `3 passed`; số tệp `~/.gemini/config/` giữ nguyên `371`.
- **Rủi ro còn lại:** Máy Intel Mac (`x86_64-apple-darwin`) chưa có runner trực tiếp trên mạng nội bộ để build trước nhị phân `tdq-dispatch-darwin-x64`; workflow CI đã khai đủ 4 target và máy Intel Mac cài mới sẽ tự rơi về Python `dispatch.py` qua launcher cho tới khi GitHub Actions chạy.

| # | Hạng mục | Lệnh đã chạy | Kết quả | PASS/FAIL |
|---|---|---|---|---|
| `Q1` | Hook launcher đa OS & `hooks.json` | `py -3 -X utf8 -m pytest tests/test_agy_launchers.py tests/test_agy_plugin_validate.py tests/test_command_gate.py -q` | `19 passed` (`cmd /c` chạy đủ 6 sự kiện, `0` dấu `"`, `0` `bin\tdq-dispatch.exe`) | PASS |
| `Q2` | MCP launcher đa OS & `mcp_config.json` | `py -3 -X utf8 -c "... Users\\admin / npx.cmd / PLUGIN_ROOT / PLUGIN_DATA ..."` + `tests/test_e2e_workflow.py` | `Q2 PASS`, bắt tay live JSON-RPC `agent-lsp` qua `tdq_mcp_launcher.mjs` (`>= 20` tools), `--sync-local-mcp` giữ nguyên repo sạch | PASS |
| `Q3` | Đóng gói sạch & `agy plugin validate --strict` | `agy.EXE plugin validate plugins/tdq-workflow-agy --strict --json` + `tdq_test.py tron-bo` | `findings: []` (`12` skills, `8` agents, `10` rules, `3` mcpServers, `6` hooks), `4777 passed` | PASS |
| `Q4` | Nhánh `release/antigravity` & cài cô lập `agy` | `py -3 -X utf8 -m pytest tests/test_build_portable.py tests/test_agy_release_e2e.py -q -k release` | `8 passed, 4 subtests passed` (`release/antigravity` idempotent, `~/.gemini/config/` giữ `371` tệp) | PASS |
| `Q5` | CI 4 nền tảng, magic bytes & SSH build | `py -3 -X utf8 -m pytest tests/test_agy_plugin_validate.py -q -k magic` + SSH `ubuntu-100-95`/`mbair` | `2 passed`; đã build & test live `tdq-dispatch-linux-x86_64` (`2472088 B`, `7f454c46`) và `tdq-dispatch-darwin-arm64` (`1895696 B`, `cffaedfe`); CI đủ 4 target gồm `x86_64-apple-darwin` | PASS |
| `Q6` | `TDQ_LOG`, `README`, `doc_lint` & đồng bộ `origin` | `py -3 -X utf8 scripts/doc_lint.py brief spec plan qc` | `doc_lint` 0 lỗi, `TDQ_LOG=1/0` PASS; đẩy `origin/dev` + `origin/release/antigravity` thực hiện cuối pha `report` sau khi gộp về `dev` (chờ xác nhận push hoàn tất) | CHỜ PUSH Ở REPORT |
| `QC-F1` | Meta-gate, `smoke-e2e --changed`, `tron-bo --fresh --reuse off` | `tdq_test.py tron-bo --workers auto --fresh --reuse off` + `tdq_test.py so` | `4777 passed`, `skipped=36`, `0` fail, `tron_bo=2/3`, `radius misses=0` | PASS |
| `QC-F2` | Hồi quy vùng chạm (`tests/` của mọi file `Chạm:`) | Chạy kèm toàn suite + riêng `test_agy_*`, `test_build_portable.py`, `test_command_gate.py`, `test_e2e_workflow.py`, `test_remote_*`, `test_ma_hoa_subprocess.py` | Mọi module chạm đều có test và đều `PASS` (`0` mục `KHÔNG CÓ TEST`) | PASS |
| `QC-F3` | Ràng buộc kiến trúc (`docs/kien-truc.md`) | Kiểm AST `build_portable.py` + `git status` + tách nhánh `release/antigravity` | `scripts/` không import `hooks/` (`[]`), mô hình `dev`/`main` giữ nguyên vẹn, `tdq_hook_launcher.mjs` không ghi tay `state.json` | PASS |
| `QC-F4` | Clean Code & SOLID | Kiểm AST độ dài hàm và cấu trúc hàm thuần mới/sửa | 100% hàm mới và sửa (`agy_launchers.py`, `_publish_filtered_branch`, `sinh_nhanh_release_agy`, `_hook_cmd`, `generate_mcp_config`, `_ensure_binary_executable_and_hooks`, `_adjust_hooks_for_platform`) đều `<= 50` dòng, không lặp logic Plumbing, không nuốt lỗi | PASS |

## Bằng chứng

### `QC-F1` & `Q3` — `tdq_test.py tron-bo --workers auto --fresh --reuse off` + `agy plugin validate`
```text
[2026-11-22T13:20:52+07:00] tdq_test: tron-bo backend=pytest scope=full status=PASS tests_run=4777 details_complete=True fallback=none seconds=316.99 reason=Executed tests completed successfully
[TDQ:TEST] PASS — scope=full backend=pytest tests=4777 skipped=36 in 316.99s.
request: 2026-11-22-1033-nhanh-release-agy-da-os (phase qc) · full-suite runs: 2 of budget 3 · radius misses: 0
agy.EXE plugin validate plugins/tdq-workflow-agy --strict --json -> findings: [] (agents: 8, hooks: 6, mcpServers: 3, rules: 10, skills: 12)
```

### `Q1`, `Q2`, `Q4`, `Q5` & SSH đa OS
```text
pytest tests/test_agy_launchers.py tests/test_agy_plugin_validate.py tests/test_command_gate.py -q -> 19 passed in 5.00s
pytest tests/test_build_portable.py tests/test_agy_release_e2e.py -q -k release -> 8 passed, 32 deselected, 4 subtests passed in 10.98s
pytest tests/test_ma_hoa_subprocess.py tests/test_agy_launchers.py tests/test_e2e_workflow.py -v -> 9 passed in 12.42s
pytest tests/test_agy_release_e2e.py tests/test_remote_linux_simulation.py tests/test_remote_mac_simulation.py -v -> 3 passed in 8.34s
REAL_CFG_COUNT: 371 (unchanged)
```

### Hợp đồng Skill (`T1.1`, `T2.1`) & `QC-F4`
- `T1.1` (`agy-customizations`): đã nạp skill; `Ra:` `tools/patches/agy_launchers.py` & `tests/test_agy_launchers.py` tồn tại; `Kiểm:` `4 passed in 0.79s`.
- `T2.1` (`plugin`): đã nạp skill; `Ra:` `plugins/tdq-workflow-agy/{hooks.json,mcp_config.json,scripts/tdq_hook_launcher.mjs,scripts/tdq_mcp_launcher.mjs}` tồn tại; `Kiểm:` `agy plugin validate --strict --json` trả `findings: []`.

## Lệch spec chờ duyệt

không có

## Kết luận

`PASS` các hạng mục thực thi & kiểm thử phần mềm (`Q1`–`Q5`, `QC-F1`–`QC-F4`, `4777 passed`); chuyển pha `report` để xuất bản nhánh `release/antigravity` từ `dev` đã gộp, chạy `git push origin dev` và `git push origin release/antigravity` theo chấp thuận `5b`, kiểm cài trực tiếp từ URL GitHub để chốt `Q6` và dựng báo cáo + `Archify HTML`.
