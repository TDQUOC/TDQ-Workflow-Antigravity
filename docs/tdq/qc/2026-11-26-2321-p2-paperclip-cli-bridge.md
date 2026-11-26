# QC — Triển khai Pha P2: Cầu nối CLI 1 chiều Paperclip Bridge
Ngày: 2026-11-27 · Plan: ../plan/2026-11-26-2321-p2-paperclip-cli-bridge.md (Vòng 1)
Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

## Dev Behavior QC Card
- Auto Meta-Gate: PASS (2/2 checks, 0.06s) trên 7 tệp P2 (`--files`); khi chạy không lọc (`tdq_meta_gate.py`) báo FAIL (3/4 checks, 0.25s) với `11` dòng tiếng Việt có sẵn trong bản gốc được đồng bộ lại ở `plugins/tdq-workflow-agy/hooks/scripts/edit_gate.py:346,355` và `plugins/tdq-workflow-agy/skills/tdq-intake/SKILL.md:8,56,57,59,62,82,85,86,95` (`0` lỗi trên các tệp P2 tạo mới/sửa).
- Đủ 5-step Fresh Evidence Gate? Đạt (`TDQ_LOG=1/0` đo thật; `pull`/`push-report` chạy thật qua `tdq_state.py init/set/get` trong thư mục tạm; `build_agy_plugin.py` + `run_full_verification.py` `24/24`; `tron-bo` `5.012 pass / 37 skip`; `tdq-qc-tester` độc lập chốt `Verdict: PASS`, `DEFECTS: None`).
- Luồng đổi: Trước đây TDQ chỉ có `P0` và `P1`, chưa có công cụ CLI kéo issue hay gửi báo cáo về Paperclip. Nay người dùng Docker/WSL2 có cầu nối 1 chiều tắt mặc định `scripts/tdq_paperclip_bridge.py` (`status`, `pull`, `push-report`) dùng thuần Python stdlib; người dùng Windows giữ nguyên `enabled=false` (thoát mã `3`, `0` socket mở).
- Chạy thử thật (Before → After + Bằng chứng tươi): Trước request có `0` test bridge và `kept=209`; nay `tests/test_paperclip_bridge.py` đạt `12 passed, 3 subtests`, cụm 6 file P2 đạt `218 passed, 74 subtests` (`89.49s`), `tools/run_full_verification.py` đạt `24/24` (`0` finding AGY), `tron-bo --workers auto --fresh --reuse off` đạt `PASS` (`5012 passed, 37 skipped, 3090 subtests passed` trong `361.29s` execution / `383.33s` wrapper, `radius misses: 0`).
- Rủi ro còn lại: `smoke-e2e --changed` khi không truyền `--workers auto` (`-n 0`) vượt trần `120s` và bị ngắt ở lượt đầu; khi chạy `--workers auto --fresh` đạt `418 passed, 239 subtests` (`111.24s` execution / `125.87s` tổng wrapper). `tests/test_build_portable.py` còn `7` cảnh báo ruff có sẵn trên `HEAD@24acb575` (phần P2 `+6/-0` sạch `0` lỗi). `eval: chưa kích hoạt (opt-in)`.

| # | Hạng mục | Lệnh đã chạy | Kết quả | PASS/FAIL |
|---|---|---|---|---|
| Q1 | Cấu hình tắt mặc định & sync `tdq-config.json` | `pytest -q tests/test_agent_upgrade_mvp.py tests/test_paperclip_bridge.py -k "config or paperclip"` + kiểm SHA-256 parity | `22 passed, 14 deselected, 16 subtests passed in 1.42s`; SHA-256 `tdq-config.json` gốc = plugin (`5D79010A...`); `paperclip_bridge.enabled == False` | PASS |
| Q2 | CLI `status`, `pull`, `push-report` & tích hợp P1/state (`1a`, `2a`) | `pytest -q tests/test_paperclip_bridge.py` + chạy thật `TDQ_LOG=0/1` + probe `(e)` `pull` thật `tdq_state.py init/set` | `12 passed, 3 subtests passed in 0.58s`; `TDQ_LOG=0` `rc=3`, `0B` stderr; `TDQ_LOG=1` `260B` ISO timestamp stderr; `pull` tạo đúng `schema_version=6`, `domain_id`, `brief_file` | PASS |
| Q3 | Bảo mật HTTP & Bộ kiểm thử mock ngoại tuyến `100%` | Probes adversarial `(a)`–`(d)` + `tests/test_paperclip_bridge.py` | `(a)` mặc định `exit 3`, `0` socket; `(b)` file hỏng JSON `exit 3` dù `env=1`; `(c)` `file://` `exit 2`, `A/../B` quote thành `A%2F..%2FB`; `(d)` `401`/timeout `exit 4`, che token `***`, không ghi `state.json`/brief | PASS |
| Q4 | Đóng gói đa host (`main`, AGY), `i18n_check` & `token_budget` | `build_agy_plugin.py`, `test_build_portable.py`, `--sinh-main --dry-run`, `token_budget.py --kiem`, `i18n_check.py`, `run_full_verification.py` | `39 passed, 4 subtests passed in 11.84s`; dry-run `HEAD` `kept=209` + working-tree giữ đủ 2 tệp P2; `token_budget` `rc=0`; `i18n_check` `0 VI`; AGY `24/24`, `0` findings | PASS |
| Q5 | Hồi quy toàn kho (`tron-bo`), Ruff, AST `0` import `hooks` & `tdq-qc-tester` | `tron-bo --workers auto --fresh --reuse off`, `ruff check` 3 file P2, AST 82 `scripts/*.py`, `tdq-qc-tester` độc lập (`3d439881`) | `tron-bo` `PASS`: `5012 passed, 37 skipped, 3090 subtests passed in 361.29s`; `ruff` 3 file P2 `All checks passed!`; `0` import `hooks/`; `tdq-qc-tester` `218 passed, 74 subtests`, `Verdict: PASS`, `DEFECTS: None` | PASS |
| Q6 | Sạch Clean Code (`<= 50` dòng), `schema_version=6`, `23` AGY & Rollback | AST đếm dòng + cyclomatic, kiểm `default_state()`, `gate_guidance.json`, giả lập xóa 3 file P2 ở tempdir | Max `46` dòng (`run_pull`), max cyclomatic `10` (`map_issue_to_tdq_init`), `0` stub/TODO, `schema_version == 6`, `all_agy_codes == 23`, rollback P0/P1 `init/route/max-qc` `rc=0` | PASS |
| Q7 | Báo cáo, working log & Archify HTML (`current`, HTTP `200`) | `doc_lint.py` (`plan`, `qc`, `report`), `tdq_archify.py render/verify`, `tdq_finish.py`, `curl.exe -sI` | `doc_lint` `0` vi phạm (`R16=0`); Archify HTML `1,594,837` bytes (`diagnosticSummary.total=0`, `status=current`, `binding.valid=true`); Tailscale `HTTP/1.1 200 OK` | PASS |
| QC-F1 | Auto Meta-Gate, `smoke-e2e --changed` & `tron-bo` cuối | `tdq_meta_gate.py --files`, `smoke-e2e --changed --workers auto --fresh`, `tron-bo`, `tdq_test.py so` | Meta-Gate `--files` `PASS (2/2 checks, 0.06s)`; `smoke-e2e` `418 passed` (`111.24s` exec / `125.87s` wrapper; `-n 0` trước đó ngắt ở `120s`); `tron-bo` lượt 2 `PASS` (`5012 passed, 37 skipped`); `tron_bo=2/3`, `radius misses: 0` | PASS |
| QC-F2 | Hồi quy vùng chạm (`T1.1`–`T3.1`) | `tdq_test.py vung-cham --plan-only --files ...` + `pytest -q -n auto` 6 module vùng P2 | `vung-cham` báo `185/249` vượt 60% (`249/249`); cụm 6 module P2 đạt `218 passed, 74 subtests passed in 89.49s`, cộng `tron-bo` `249/249` `PASS` | PASS |
| QC-F3 | Ràng buộc kiến trúc §5 | AST `scripts/*.py`, `rg` `hooks/`, đọc `tdq_paperclip_bridge.py` & probe `(e)` | Giữ nguyên `0` import `hooks/` và `0` phụ thuộc ngoài stdlib; chỉ gọi CLI `tdq_state.py init/set/get` (`schema_version=6`); `0` sửa `hooks/` hay Rust (`23` mã AGY) | PASS |
| QC-F4 | Clean code (fail-closed, chống trùng lặp, `<= 50` dòng) | Kiểm code thủ công + ruff + AST + `clean-code.md` (mục hàm/module tuần tự) | `0` class mới/sửa trong mã nguồn chạy thật; mọi hàm `<= 46` dòng (`<= 50`), cyclomatic `<= 10`; `tdq_config` dùng chung bảng `_SECTION_BOOL_KEYS`; lỗi HTTP/config fail-closed mã `2/3/4` kèm `redact_secrets` | PASS |

## Bằng chứng

### Q1 — Cấu hình tắt mặc định & sync `tdq-config.json`
```text
pytest -q tests/test_agent_upgrade_mvp.py tests/test_paperclip_bridge.py -k "config or paperclip"
-> 22 passed, 14 deselected, 16 subtests passed in 1.42s
SHA256 root vs plugins/tdq-workflow-agy/:
- tdq-config.json: 5D79010A36569125DC9A94659D43D46EFF7D7168CBEF9228C17BF1938CD8ADEB (khớp)
- scripts/tdq_paperclip_bridge.py: B7E9351FC3E8402BF75A49815300B43499FA24C71DB98E9004FEAA502446C559 (khớp)
- scripts/defaults/paperclip-bridge.default.json: 8CA48FA5E85FE9FAEDFCAFB990D07EA23DA52F11B58C0DBAAC29C3816D55378C (khớp)
keys: ['qc', 'agents', 'p0', 'p1', 'paperclip_bridge'] · paperclip_bridge={'enabled': False}
```

### Q2 — CLI `status`, `pull`, `push-report` & `TDQ_LOG=1/0`
```text
pytest -q tests/test_paperclip_bridge.py -> 12 passed, 3 subtests passed in 0.58s
TDQ_LOG=0 scripts/tdq_paperclip_bridge.py status -> rc=3, stdout=0B, stderr=0B
TDQ_LOG=1 scripts/tdq_paperclip_bridge.py status -> rc=3, stdout=0B, stderr=260B:
  [2026-11-27T01:19:23+07:00] tdq_paperclip_bridge: command=status cwd=C:\Users\admin\Documents\Projects\TDQ-Workflow-Antigravity enabled=False
  [2026-11-27T01:19:23+07:00] tdq_paperclip_bridge: bridge disabled (enabled=false); exiting 3 without network access
TDQ_LOG=0 scripts/tdq_config.py show --json -> rc=0, stdout=2277B, stderr=0B
TDQ_LOG=1 scripts/tdq_config.py show --json -> rc=0, stdout=2277B, stderr=117B
Probe (e) pull thật qua tdq_state.py init/set (tempdir, urlopen mocked):
  rc=0, schema_version=6, domain_id=research-rca, work_kind=investigate, brief_exists=True
```

### Q3 — Bảo mật HTTP & Adversarial probes
```text
(a) enabled=false -> a_rc=3, a_socket_calls=0, a_urlopen_calls=0
(b) docs/tdq/paperclip-bridge.json='{bad json' + PAPERCLIP_BRIDGE_ENABLED=1 -> b_rc=3, b_urlopen_calls=0, b_has_warn=True
(c) base_url='file:///...' -> c_rc=2, c_urlopen_calls=0; build_endpoint_url(..., 'PAP/../../sec') -> http://127.0.0.1:3100/api/issues/PAP%2F..%2F..%2Fsec
(d) missing token/HTTP 401/timeout -> rc=4, sec_in_401=False, masked_401=True (***), sec_in_timeout=False, state_exists=False, brief_exists=False
```

### Q4 — Đóng gói `main`, AGY, `i18n_check` & `token_budget`
```text
pytest -q tests/test_build_portable.py -> 39 passed, 4 subtests passed in 11.84s
scripts/i18n_check.py 5 files root + 3 files plugins -> 0 Vietnamese line(s), exit 0
scripts/token_budget.py --kiem -> exit 0
scripts/build_portable.py --sinh-main --dry-run -> kept=209 dropped=7763, exit 0 (HEAD@24acb57; test_build_portable kiểm trực tiếp working-tree giữ cả tdq_paperclip_bridge.py & paperclip-bridge.default.json)
tools/run_full_verification.py -> pytest_passed="24/24", agy_validate_findings=0, status="OK"
```

### Q5 & QC-F1/F2 — Toàn kho `tron-bo`, `smoke-e2e`, `tdq-qc-tester`
```text
tdq-qc-tester (3d439881-2bcd-4300-8ff7-2dd46dd6c2fb) doc lap:
  pytest -q -n auto 6 modules P2 -> 218 passed, 74 subtests, 0 skip, 0 fail in 89.49s
  DEFECTS: None
  VERDICT: PASS everything

tdq_meta_gate.py --files <7 files P2> -> Auto Meta-Gate: PASS (2/2 checks, 0.06s)
tdq_meta_gate.py (khong loc) -> Auto Meta-Gate: FAIL (3/4 checks, 0.25s) — 11 dong VI co san trong edit_gate.py:346,355 va tdq-intake/SKILL.md:8-95
tdq_test.py vung-cham --plan-only --files ... -> scope=full selected=249/249 reason=radius 185/249 modules reaches the 60% threshold
tdq_test.py smoke-e2e --changed (-n 0 truoc comp) -> bi ngat o tran 120s; voi --workers auto --fresh -> 418 passed, 239 subtests passed (111.24s exec / 125.87s tong wrapper)
tdq_test.py tron-bo --workers auto --fresh --reuse off:
  - Luot 1 (task-27071): pytest 5012 passed, 37 skipped, 3090 subtests passed (362.66s) nhung wrapper bao INCOMPLETE vi tdq_finish ghi workinglog/2026-11-27.md luc 01:12:31 trong khi suite dang chay.
  - Luot 2 (task-27334, khong cham file nao trong luc chay):
    5012 passed, 37 skipped, 3090 subtests passed in 361.29s (0:06:01)
    [TDQ:TEST] PASS — scope=full backend=pytest tests=5049 skipped=37 in 383.33s.
    status=PASS details_complete=True reason=Executed tests completed successfully
tdq_test.py so -> full-suite runs: 2 of budget 3 · radius misses: 0
```

### Q6 & QC-F3/F4 — Sạch Clean Code, AST, Ràng buộc §5 & Rollback
```text
ruff check scripts/tdq_paperclip_bridge.py scripts/tdq_config.py tests/test_paperclip_bridge.py -> All checks passed! (exit 0)
ruff check tests/test_build_portable.py -> 7 loi pre-existing tren HEAD@24acb575 (L20, L94, L102, L379, L733, L735, L760); 6 dong P2 them moi sach 0 loi; --select E4,E7,E9,F -> All checks passed!
AST scripts/*.py (82 files): hook_imports = 0; rg hooks/ & plugins/.../hooks/ -> 0 ket qua Paperclip
tdq_paperclip_bridge.py: 25 ham, max 46 dong (run_pull), max cyclomatic 10 (map_issue_to_tdq_init), 0 stub/TODO
tdq_config.py: max 36 dong (resolve_model_for_role), max cyclomatic 8 (_pick_swarm_model)
default schema_version = 6 · all_agy_codes = 23
Rollback tempdir (xoa tdq_paperclip_bridge.py + paperclip-bridge.default.json): state_init_rc=0, domains_route_rc=0, config_rc=0
SOLID/Clean Code tuần tự (`clean-code.md`):
- SRP: tách riêng config (`load_bridge_config`), bảo vệ URL (`validate_base_url`, `build_endpoint_url`), request (`http_json_request`), ánh xạ domain (`map_issue_to_tdq_init`), lệnh con (`run_status`, `run_pull`, `run_push_report`).
- OCP: `tdq_config` dùng chung bảng `_SECTION_BOOL_KEYS` và `_SECTION_BOOL_ENV_OVERRIDES` cho cả `p1` và `paperclip_bridge` thay vì nhân bản vòng `if`.
- LSP (suy diễn hàm đồng nhất): hàm cấu hình trả chuẩn `(parsed, ok)` hoặc `dict`, CLI trả cố định mã `0/2/3/4` và nâng lỗi `ValueError`/`FileNotFoundError`/`RuntimeError` đồng nhất tại `main`.
- ISP: helper chỉ nhận đúng `cwd`/`cfg`/`issue_id`/`report_md_path` thay vì truyền nguyên khối state khổng lồ.
- DIP: ghi/đọc state đi duy nhất qua cửa `scripts/tdq_state.py` (`init`/`set`/`get`), không tự mở ghi `state.json`.
```

### Q7 — Báo cáo & Archify HTML
```text
doc_lint.py plan.md qc.md report.md -> 0 violation(s) total, exit 0 (R16 -> 0 finding(s))
tdq_archify.py render --type explainer --quality showcase --evidence-kind working-tree -> status=pass, diagnosticSummary.total=0, HTML_BYTES=1594837, binding=bound
tdq_archify.py verify --document docs/tdq/reports/2026-11-26-2321-p2-paperclip-cli-bridge.md --manifest docs/tdq/reports/2026-11-26-2321-p2-paperclip-cli-bridge.manifest.json
-> status=current, binding.valid=true, reasons=[]
curl.exe -sI https://unity-pc-rtx3060.tail99896.ts.net/vlog/tdq-workflow-agy/reports/2026-11-26-2321-p2-paperclip-cli-bridge.html
-> HTTP/1.1 200 OK · Content-Length: 1594837
```

## Lệch spec chờ duyệt
không có

## Kết luận
PASS toàn bộ (`7/7` hạng mục DoD `Q1`–`Q7` và `4/4` hạng mục cố định `QC-F1`–`QC-F4`). `tdq-qc-tester` độc lập chốt `Verdict: PASS`, `DEFECTS: None`.
