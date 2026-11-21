# QC — Triển khai Trọn bộ 3 Đợt Kiến trúc `work_kind=investigate` V2

Ngày: 2026-11-21 · Spec: ../spec/2026-11-21-0217-trien-khai-investigate-v2.md · Plan: ../plan/2026-11-21-0217-trien-khai-investigate-v2.md · Vòng: 1 (`muc_qc=full`, kiểm độc lập `tdq-qc-tester`)
Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

| # | Hạng mục | Lệnh đã chạy | Kết quả | PASS/FAIL |
|---|---|---|---|---|
| Q1 | Đợt 1 State, Telemetry, Lint & Docs (`work_kind`, `PHASE_TABLE==11`, `R10`/`R14`, token caps, `investigate-mode.md <=3,000`, `i18n_check`) | `token_budget.py --kiem`, `doc_index.py --tat-ca --kiem`, `doc_lint.py --pair`, `i18n_check.py`, `pytest` 7 modules (`test_state`..`test_skill_shape`) | `211 passed, 131 subtests` (`108.27s`); `PHASE_TABLE=11`; `investigate-mode.md=1783` tok; `66` file `<=3500`; `0` lỗi lint/`i18n` | PASS |
| Q2 | Đợt 2 Evidence Shard-Merge, NTFS Lock & Bảo mật `scoped-write` 5 tầng (`cmd /c`, `[IO.File]`, `tdq-security-reviewer` đọc 100%) Python ↔ Rust | `pytest tests/test_team_packet_v2.py tests/test_bash_gate.py tests/test_investigate_workflow.py -q` + 18 vector đối kháng `qc_probe.py` (`edit_gate`/`bash_gate` vs `tdq-dispatch.exe`) | `99 passed, 1 skipped` (`WinError 1314` symlink OS); `18/18` vector (`..`, `mklink /J`, `evidence*`, `cmd /c`, `[IO.File]`, `tdq-security-reviewer`) khớp `100%` | PASS |
| Q3 | Đợt 2 Weighted Burden Rust theo `sid`, fast-path `has_range` (`<= 25.0 ms` hot-direct) & giữ `22` mã AGY | `pytest tests/test_read_gate.py tests/test_gate_guidance.py tests/test_hooks_dual_protocol.py tests/test_rust_dispatch_parity.py tests/test_rust_latency_benchmark.py -q -s` + probe `sidA`/`sidB` | `89 passed, 25 subtests` (`104.96s`); `Hot PreToolUse (Direct)` median `14.76 ms` (`<=25.0`); `all_agy_codes=22`; Burden `sidA` `42 -> DOC -> 0` độc lập `sidB` | PASS |
| Q4 | Đợt 3 Agents, Rust `cargo test && clippy`, Rebuild `plugins/tdq-workflow-agy/`, `agy plugin validate --strict`, `--dry-run` | `rtk bypass cargo test`, `rtk bypass cargo clippy --all-targets -- -D warnings`, `install_agy_plugin.py --dry-run`, `agy.exe plugin validate --strict --json`, `pytest` frontmatter/validate | `cargo test` `29 passed` (`0.07s`); `clippy` `0` warning; `dry_run: true` exit `0`; `agy.exe` `findings: []`; `14 passed, 51 subtests`; đủ `3` binary trong `bin/` | PASS |
| Q5 | Nghiệm thu `tdq_test.py so`, receipt `tron-bo` tươi, harness `4` ca mẫu (`1056`/`1457`/`1346`/`1953`), `TDQ_LOG=0` | `tdq_test.py so`, kiểm `result.json` tại `9dca47f0a68453e4/ac8522b147444f5b961d616e44d6a412`, `qc_log_probe.py` trên 5 CLI + `tdq-dispatch.exe` | `tron_bo=2/3`, `bo_sot=0`, `radius misses: 0`; `result.json` `PASS` (`tests_run=4632`, `skipped=36`, `0` fail); `TDQ_LOG=0` im `stderr` 100%, mặc định có ISO | PASS |
| Q6 | Sạch Hiến pháp & Zero-Side-Effect ngoài phạm vi (`~/.gemini/` không bị ghi đè, không có TODO/stub) | Kiểm `Get-Item` `~/.gemini/config/plugins/tdq-workflow-agy`, `git diff dev --stat`, quét AST & từ khóa `TODO/FIXME/eval(` | `~/.gemini/` `LastWriteTime=11/19/2026` (không bị ghi đè); `0` stub/placeholder thực; báo cáo `phase=report` chưa sinh ở pha `qc` (đúng trình tự) | PASS |
| QC-F1 | Chạy trọn suite (`full`) / kiểm chứng receipt sau sửa cuối | `py -3 -X utf8 scripts/tdq_test.py so` & đọc `docs/tdq/cache/test-runs/9dca47f0a68453e4/ac8522b147444f5b961d616e44d6a412/result.json` | Receipt cập nhật `11/21/2026 5:33:58 AM`: `status=PASS`, `tests_run=4632`, `skipped=36`, `failures=[]`, `wall_seconds=1291.13`, `bo_sot=0` | PASS |
| QC-F2 | Hồi quy vùng chạm theo mọi dòng `Chạm:` trong plan | `pytest` 10 module `QC1.2` + `test_ten_lenh_he`, `test_lsp_module`, `test_tdq_state_cong_lsp`, `test_subagent_start`, `test_plan_scaffold`, `test_rust_lock_safety`, `test_context_hooks` | `228 passed` (`118.43s`) + `164 passed` (`65.75s`) + `78 passed` (`4.26s`) + `84 passed` (`17.12s`); không có node `KHÔNG CÓ TEST` | PASS |
| QC-F3 | Ràng buộc kiến trúc phải giữ (5 điều trong Spec §5) | Quét AST `scripts/*.py -> hooks/`, `rg` bảng `qc.md`, chạy `test_approve_do_truoc`, `test_archify_gate`, `test_kien_truc`, `test_build_portable` | `AST_HOOKS_IMPORTS=[]`; duy nhất 1 bảng tại `qc.md`; R14/LSP/`dev`–`main` giữ nguyên `100%` | PASS |
| QC-F4 | Clean Code Self-check (5 câu hỏi SOLID trên file đã sửa) | Đọc trực tiếp diff ở `scripts/`, `hooks/scripts/`, `hooks/rust/tdq-dispatch/src/`, `tools/patches/` | Đạt cả 5 tiêu chí `SRP / OCP / LSP / ISP / DIP` | PASS |

---

## Bằng chứng

### Q1 — Đợt 1: State, Telemetry, Lint & Docs

- Đặt `$env:TDQ_TOKENS_VENV='C:\Users\admin\Documents\Projects\ForAgentCode\TDQ-Workflow\.venv-tokens\Scripts\python.exe'` và chạy tuần tự:
  - `py -3 -X utf8 scripts/token_budget.py --kiem` → exit `0` (`TOTAL_FILES= 66`, `OVER_3500= {}`, `investigate-mode.md`: `1783` tokens `<= 3000`).
  - `py -3 -X utf8 scripts/doc_index.py --tat-ca --kiem` → exit `0` (lưu ý: gọi trần `doc_index.py --kiem` thiếu `--tat-ca` trả exit `2`: `doc_index.py: needs a path, or --tat-ca` đúng thiết kế parser).
  - `py -3 -X utf8 scripts/doc_lint.py --pair docs/tdq/spec/2026-11-21-0217-trien-khai-investigate-v2.md docs/tdq/plan/2026-11-21-0217-trien-khai-investigate-v2.md` → exit `0`.
  - `py -3 -X utf8 scripts/i18n_check.py skills/tdq-conventions/references/investigate-mode.md tests/test_investigate_workflow.py` → exit `0` (`0 Vietnamese line(s) in 2 file(s)`).
  - `py -3 -X utf8 -m pytest tests/test_state.py tests/test_phase_table.py tests/test_doc_lint.py tests/test_plan_v2_linter.py tests/test_muc_qc_qc_md.py tests/test_gate_merge.py tests/test_skill_shape.py -q` → `211 passed, 131 subtests passed in 108.27s`.
- Kiểm trực tiếp bất biến & góc hiểm `M1`:
  - `len(tdq_state.PHASE_TABLE) == 11`, `tdq_state.work_kind_hieu_luc({"work_kind": "garbage"}) == "build"` (kèm cảnh báo ISO trên stderr).
  - Trên `tmp_path`: `tdq_state.py set work_kind=build` bị chặn (exit `2`), `escalate-to-build` thiếu/rỗng `--by` bị chặn (exit `2`), `escalate-to-build --by "user approved build"` chuyển thành công `investigate -> build` (exit `0`).

### Q2 — Đợt 2: Evidence Engine & Bảo mật `scoped-write` Python ↔ Rust

```text
py -3 -X utf8 -m pytest tests/test_team_packet_v2.py tests/test_bash_gate.py tests/test_investigate_workflow.py -q
99 passed, 1 skipped, 19 subtests passed in 35.11s
```

- Kiểm lý do 1 test skip (`pytest tests/test_investigate_workflow.py -rs -q`): `test_scoped_write_symlink_escape_denied` skip do Windows không nâng quyền thiếu `SeCreateSymbolicLinkPrivilege` (`WinError 1314`); bù lại `test_scoped_write_windows_ntfs_junction_escape_denied` (`mklink /J`) chạy thật và PASS trên cả Python lẫn Rust.
- Probe độc lập `qc_probe.py` (trong `TemporaryDirectory`, đối chiếu trực tiếp `hooks/scripts/{edit_gate,bash_gate}.py --event PreToolUse` với `plugins/tdq-workflow-agy/bin/tdq-dispatch.exe --event PreToolUse`):
  - `12/12` vector ghi file (`tdq-security-reviewer` ghi `artifacts/<slug>/t1.md` & `research/<slug>.md` → `deny`; traversal `..`, NTFS junction `mklink /J`, `evidence.jsonl`, `evidence_foo.md`, `trial_1.json`, `rec_1.json`, `research/<slug>-sub/note.md`, `.py` → `deny`; `artifacts/<slug>/t1.md` & `research/<slug>-part1.md` cho `tdq-explorer` → `allow`) khớp `100%` `py == rust`.
  - `6/6` vector shell (`cmd /c`, `cmd.exe /c`, `[IO.File]::WriteAllText`, `[System.IO.File]::WriteAllText`, shell write của `tdq-security-reviewer` → `deny`; `git status` của `tdq-security-reviewer` → `allow`) khớp `100%` `py == rust`.
  - `tdq_team.py evidence add` với `--claim-file` không tồn tại thoát lỗi `ec=1` (`--claim-file file not found`), `is_artifact_only_paths` từ chối `..` và danh sách rỗng.

### Q3 — Đợt 2: Weighted Burden Counter Rust, Hot-Path `read_file` & `22` Mã AGY

```text
py -3 -X utf8 -m pytest tests/test_read_gate.py tests/test_gate_guidance.py tests/test_hooks_dual_protocol.py tests/test_rust_dispatch_parity.py tests/test_rust_latency_benchmark.py -q -s
Hot PreToolUse (Direct)            |       14.76 |     15.98
Hot PreToolUse (cmd /c)            |       22.57 |     24.18
89 passed, 25 subtests passed in 104.96s (0:01:44)
```

- `Hot PreToolUse (Direct)` median **`14.76 ms`** (P95 `15.98 ms`), đạt ngưỡng `<= 25.0 ms`.
- `tools/patches/gate_guidance.json`: `len(all_agy_codes) == 22`, giữ nguyên `22` mã AGY (tái sử dụng `"DOC"`).
- Probe độc lập `sidA`/`sidB` trên `tdq-dispatch.exe`: sau 14 lượt `read_file` có dải dòng của `sidA`, `checkpoint-sidA.json` đạt `score=42`, `PreInvocation` phát `[TDQ:DOC]`; lượt ghi shard của `sidB` giữ nguyên `checkpoint-sidA.json` (`score=42`); lượt ghi shard của `sidA` reset `checkpoint-sidA.json` về `{'score': 0, 'reminded_at_score': 0}`.

### Q4 — Đợt 3: Agents, Rust Cargo, Plugin Validate & Dry-Run Install

- `rtk bypass cargo test --manifest-path hooks/rust/tdq-dispatch/Cargo.toml`: `25 passed` (lib) + `4 passed` (bin) = **`29 passed; 0 failed`** (`0.07s`).
- `rtk bypass cargo clippy --manifest-path hooks/rust/tdq-dispatch/Cargo.toml --all-targets -- -D warnings`: `0` warning, `0` error.
- `py -3 -X utf8 tools/install_agy_plugin.py --dry-run`: exit `0`, JSON `"dry_run": true`, target `C:\Users\admin\.gemini\config\plugins\tdq-workflow-agy`.
- Đường dẫn `agy.exe`: `C:\Users\admin\AppData\Local\Programs\Antigravity\bin\agy.EXE` không tồn tại trên máy; binary thật trên `PATH` là `C:\Users\admin\AppData\Local\agy\bin\agy.exe`. Chạy `agy.exe plugin validate plugins/tdq-workflow-agy --strict --json`: exit `0`, `"findings": []` (`agents: 8, hooks: 6, mcpServers: 3, rules: 10, skills: 12`).
- `py -3 -X utf8 -m pytest tests/test_agent_frontmatter.py tests/test_agy_plugin_validate.py -q` → `14 passed, 51 subtests passed in 3.03s`.
- `plugins/tdq-workflow-agy/bin/` có đủ 3 binary: `tdq-dispatch.exe` (`1,967,104` B, `11/21/2026 3:48:32 AM`), `tdq-dispatch-linux-x86_64` (`2,268,768` B, `11/19/2026`), `tdq-dispatch-darwin-arm64` (`1,812,432` B, `11/19/2026`).
- Kiểm tra file compiled: `plugins/tdq-workflow-agy/agents/tdq-security-reviewer.md` giữ `[TDQ:READONLY]` và không chứa `write_file`/`edit_file`; `tdq-{explorer,debugger,reviewer}.md` mang `[TDQ:SCOPED-WRITE]`; `tdq-debugger.md` có `Point-of-Commitment` và `Counterfactual Falsification Test`.

### Q5 & QC-F1 — Receipt `tron-bo`, Mô phỏng `4` Ca & `TDQ_LOG=0`

- `py -3 -X utf8 scripts/tdq_test.py so`: `full-suite runs: 2 of budget 3`, `radius misses: 0`, `bo_sot=0`.
- Kiểm `docs/tdq/cache/test-runs/9dca47f0a68453e4/ac8522b147444f5b961d616e44d6a412/result.json` (`LastWriteTime: 11/21/2026 5:33:58 AM`, `7,996,939` B): `status="PASS"`, `tests_run=4632`, `skipped=36`, `failed_modules=[]`, `failures=[]`, `unmapped_failures=[]`, `details_complete=True`, `exit_code=0`, `wall_seconds=1291.13`.
- Harness mô phỏng `4` ca mẫu (`test_sim_ca1_1056`, `test_sim_ca2_1457`, `test_sim_ca3_1346`, `test_sim_ca4_1953` trong `tests/test_investigate_workflow.py`) đã chạy và PASS trong Q2.
- Kiểm độc lập `TDQ_LOG=0` vs mặc định (`qc_log_probe.py`) trên đủ `5` CLI Python (`tdq_state.py escalate-to-build`, `doc_lint.py --pair`, `tdq_team.py evidence add`, `tdq_plan_scaffold.py --verify-plan`, `tdq_bench.py simulate`) và `tdq-dispatch.exe`: mặc định 100% có timestamp ISO trên `stderr`; `TDQ_LOG=0` cho `stderr == ""` sạch hoàn toàn.

### Q6, QC-F2 & QC-F3 — Hiến pháp, Zero-Side-Effect & Vùng chạm

- `C:\Users\admin\.gemini\config\plugins\tdq-workflow-agy`: `LastWriteTime = 11/19/2026 1:21:43 PM` (không có tệp nào sửa ngày `2026-11-21` — giữ nguyên an toàn đúng chọn `2a`).
- Quét `git diff dev -- scripts/ hooks/ agents/ skills/ tools/`: `0` nhánh `TODO`/`FIXME`/`TBD`/`NotImplementedError`/`eval(` bỏ sót (2 chuỗi `"placeholder"` khớp từ khóa đều nằm trong mô tả kiểm `QC-I1`).
- **QC-F2 (Hồi quy vùng chạm)**: Đã chạy kiểm chứng toàn bộ các nhóm test phủ hết `Chạm:` trong plan:
  - `test_agent_upgrade_mvp`, `test_bao_cao_da_nen_tang`, `test_bench`, `test_build_portable`, `test_context_hooks`, `test_doc_index`, `test_luat_skill`, `test_luat_subagent_pr`, `test_mcp_first_auto_setup`, `test_reference_mot_tang`: `228 passed, 444 subtests passed in 118.43s`.
  - `test_doc_lint`, `test_plan_v2_linter`, `test_muc_qc_qc_md`, `test_rust_lock_safety`, `test_skill_shape`, `test_context_hooks`: `164 passed, 67 subtests passed in 65.75s`.
  - `test_approve_do_truoc`, `test_archify_gate`, `test_kien_truc`, `test_prompt_context`, `test_lane_label`: `84 passed, 168 subtests passed in 17.12s`.
  - `test_ten_lenh_he`, `test_lsp_module`, `test_tdq_state_cong_lsp`, `test_subagent_start`, `test_plan_scaffold`: `78 passed, 15 subtests passed in 4.26s`.
- **QC-F3 (5 ràng buộc kiến trúc Spec §5)**:
  1. `scripts/` không import `hooks/scripts/`: quét AST toàn bộ `scripts/*.py` trả `AST_HOOKS_IMPORTS: []`.
  2. Bảng `"Mức nào chạy loại kiểm nào"` chỉ có đúng 1 bản tại `skills/tdq-build/references/qc.md` (xác minh qua `rg` và `test_muc_qc_qc_md.py`).
  3. `approve spec` giữ nguyên R14 (`r14_loi` chỉ miễn `Work kind: investigate`; `test_approve_do_truoc.py` + `test_doc_lint.py` PASS).
  4. `tdq_state.py init` giữ nguyên cổng LSP (`test_lsp_module.py` + `test_tdq_state_cong_lsp.py` PASS).
  5. Mô hình 2 nhánh `dev`/`main` & `build_portable.py --sinh-main`: `test_build_portable.py` + `test_kien_truc.py` PASS.
- **Lưu ý phạm vi `phase=qc` (Q6)**: File `docs/tdq/reports/2026-11-21-0217-trien-khai-investigate-v2.md` và Archify HTML báo cáo cuối chưa tồn tại ở thời điểm QC (`REPORT_EXISTS=False`) vì chúng thuộc pha `report` tiếp sau cổng QC.

## Clean Code Self-check (QC-F4)

Kiểm tra đối chiếu 5 câu hỏi SOLID (`skills/tdq-conventions/references/clean-code.md`) trên các tệp mã đã sửa (`scripts/`, `hooks/scripts/`, `hooks/rust/tdq-dispatch/src/`):

1. **SRP (Single Responsibility)**: **Có** — Các hàm mới tách rạch ròi phân tích/nhận diện (`_is_investigate_doc`, `_first_15_with_fences`, `_parse_escalate_args`, `_canonicalize_with_tail`), khóa & lưu trữ (`_ntfs_lock`, `maybe_bump_burden`, `reset_burden_checkpoint`), và hợp nhất/hiển thị (`evidence_add`, `evidence_merge`, `evidence_render`).
2. **OCP (Open/Closed)**: **Có** — Rẽ nhánh `investigate` dùng bảng dữ liệu `INVESTIGATE_PHASE_ROWS` tương tự `MODE_ROWS` mà không đụng `PHASE_TABLE`; bảo mật đọc từ bảng hằng `_SCOPED_ARTIFACT_ROLES`, `_SCOPED_ARTIFACT_EXTS`, `_DIAGNOSTIC_PREFIXES`, `_STRICT_READONLY_AGENTS`, `_SCOPED_INVESTIGATION_AGENTS`, `LENH`/`BANG_DOI_TEN`.
3. **LSP (Liskov / Contract Parity)**: **Có** — Mọi nhánh return của `work_kind_hieu_luc`, `cong_dang_cho`, `is_investigation_artifact_target`, `is_scoped_artifact_role`, `is_product_source_path`, và các `handle_*` Rust giữ đồng nhất kiểu trả về và hợp đồng fail-closed/chặn `[TDQ:READONLY]`.
4. **ISP (Interface Segregation)**: **Có** — Hàm chỉ nhận tham số cần dùng (`is_product_source_path(rel)`, `_ntfs_lock(lock_path)`, `maybe_bump_burden(workspace_root, sid, points)`, `evidence_add` nhận tham số đích thay vì nuốt trọn `state`).
5. **DIP (Dependency Inversion / Shared Entry Point)**: **Có** — Hook không ghi thẳng `state.json`; `scripts/` không import `hooks/scripts/`; `edit_gate.py` gọi qua `_common.is_investigation_artifact_target`; mọi ghi `evidence.jsonl`/`blackboard` đi qua khóa NTFS thống nhất và cổng CLI `tdq_team.py`.

## Lệch spec chờ duyệt

không có (kiểm `py -3 -X utf8 scripts/tdq_state.py lech list` → `0 item(s), 0 pending`).

## DEFECTS

Không phát hiện lỗi chức năng hoặc hồi quy (`None`).
Ghi chú vận hành môi trường (không phải lỗi code):
1. `doc_index.py` yêu cầu `--tat-ca` hoặc đường dẫn file (gọi trần `--kiem` thoát mã `2` theo thiết kế parser tại `scripts/doc_index.py:292`).
2. `agy.exe` nằm tại `C:\Users\admin\AppData\Local\agy\bin\agy.exe` trên `PATH`, không nằm dưới `AppData\Local\Programs\Antigravity\bin\agy.EXE`.
3. `docs/tdq/reports/2026-11-21-0217-trien-khai-investigate-v2.md` chưa được tạo vì đang ở pha `qc` (sẽ sinh ở pha `report` sau khi QC PASS).

## Kết luận

VERDICT: PASS everything (`Q1`–`Q6`, `QC-F1`–`QC-F4`)
