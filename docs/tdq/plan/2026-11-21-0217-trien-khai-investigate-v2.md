# PLAN — Triển khai Trọn bộ 3 Đợt Kiến trúc `work_kind=investigate` V2

Ngày: 2026-11-21 · Spec: ../spec/2026-11-21-0217-trien-khai-investigate-v2.md (ĐÃ DUYỆT) · Lane: full · Loại: feature
Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md
Mode thực thi: subagent — đo thực tế bằng `tdq_bench.py simulate` (`--he-so-agent 1.5`): đội thắng `main` `6.1` phút (`22.4` phút vs `28.5` phút; giao `3` task `T1.1`/`T1.2`/`T4.1`, leader giữ `5` task `file-luat` + `6` DoD)
Trạng thái plan: ĐÃ DUYỆT

## Mục lục

- Phân bổ Model & Effort
- Quy tắc thi hành
- Thiết kế Trước vs Sau
- Ràng buộc toàn cục & Bản đồ Sở hữu Hợp đồng (Ownership Map)
- P1 — Đợt 1: State, Telemetry, Linter/Scaffold/Bench & Quy chuẩn `skills/`
- P2 — Đợt 2: Evidence Shard-Merge, Bảo mật `scoped-write` Python & Rust Burden Checkpoint
- P3 — Đợt 3: Agent Prompts, Compiler AGY & Rebuild Plugin
- P4 — Bộ Kiểm thử Đối kháng Python ↔ Rust, Mô phỏng 4 Ca Lịch sử & Log
- Cụm song song
- Luật file nóng
- Definition of Done

## Phân bổ Model & Effort
<!-- i18n-allow: canonical model/effort plan allocation table -->
> **Quyền chỉnh sửa của người dùng:** Bạn có quyền đổi `type model` hoặc `effort` cho bất kỳ pha/vai trò nào dưới đây ngay khi duyệt plan (nhắn trực tiếp cùng lệnh `"duyệt plan"`). Thang model: [subagent-tuning.md](../../skills/tdq-conventions/references/subagent-tuning.md) (`gemini-3.8-flash` → `gemini-4-hydrogen` → `gemini-4-neon` → `gemini-4-carbon`).

| Pha | Vai trò / Tác vụ | Model đề xuất (`invoke_subagent` / `swarm`) | Effort | Ghi chú |
|---|---|---|---|---|
| `implement` | Đợt 1 (`T1.1` `tdq_state`, `T1.2` `doc_lint`/`scaffold`/`bench`, `T1.3` `skills/` + `investigate-mode.md`) | `inherit` (`gemini-4-neon-xhigh`) | `high` | 3 nhánh song song độc lập hoàn toàn, đụng test pinning & trần token `3,500`. |
| `implement` | Đợt 2 (`T2.1` `tdq_team`/NTFS lock, `T2.2` Python hooks, `T2.3` Rust `tdq-dispatch`) | `inherit` (`gemini-4-neon-xhigh`) | `xhigh` | Bảo mật `scoped-write` 5 tầng, `cmd /c` + `[IO.File]`, Weighted Burden Rust giữ `<0.5ms`. |
| `implement` | Đợt 3 & 4 (`T3.1` Agents/Compiler/Rebuild AGY, `T4.1` Parity tests + Mô phỏng `4` ca) | `inherit` (`gemini-4-neon-xhigh`) | `high` | Biên dịch plugin AGY, validate `--strict` và kiểm thử đối kháng Python ↔ Rust. |
| `implement` | Escalation nếu 1 task vấp lỗi compile/test quá `2` lần (`tdq-build-resolver`) | `pro` (`gemini-4-carbon-high`) | `high` | Sửa surgical lỗi kiểu/Rust borrow checker hoặc parity drift. |
| `qc` (`full`) | `tdq-qc-tester` kiểm độc lập DoD `Q1`–`Q6`, `QC-F1`–`QC-F4` & `tdq_test.py tron-bo` | `inherit` (`gemini-4-neon-high`) | `high` | Chạy trọn suite, kiểm `cargo test`/`clippy`, `agy plugin validate --strict` và `4` ca mẫu. |
| `report` | Tổng hợp báo cáo `4` phần + `Archify HTML` (leader chính) | `inherit` | Theo phiên | Soạn thẳng báo cáo Markdown, render Archify HTML `current` & kiểm Tailscale HTTP `200`. |

## Quy tắc thi hành

- Mọi task thực hiện Red → Green; chạy `tdq_test.py vung-cham` giữa các đợt và chỉ chạy `tdq_test.py tron-bo` tại cổng QC (`QC-F1`).
- Không chỉnh sửa `~/.gemini/config/plugins/tdq-workflow-agy` trong lúc triển khai (`2a`: chỉ chạy `--dry-run`, chờ user duyệt sau QC).
- Trên Windows biên dịch `tdq-dispatch.exe` (`1a`), giữ nguyên `tdq-dispatch-linux-x86_64` và `tdq-dispatch-darwin-arm64` trong `plugins/tdq-workflow-agy/bin/`.
- Mọi CLI/hook thêm mới giữ log timestamp ISO mặc định ra `stderr`, tắt sạch khi `TDQ_LOG=0`.

## Thiết kế Trước vs Sau

Bản xem trước Trước/Sau đã khóa với Spec tại `docs/tdq/spec/2026-11-21-0217-trien-khai-investigate-v2-preview.html` (manifest `docs/tdq/spec/2026-11-21-0217-trien-khai-investigate-v2-preview.manifest.json`, trạng thái `current`, Tailscale HTTP `200`).

| Lớp kiến trúc | Hiện trạng (Trước) | Thiết kế Đích sau 3 Đợt (Sau) |
|---|---|---|
| State & Telemetry (`M1`) | Chỉ có `build`; `_cli_approve` quên `ghi_moc_phase`; `_archify_gate` ép preview mọi ca. | Có `work_kind`, `INVESTIGATE_PHASE_ROWS`, `escalate-to-build`, vá `ghi_moc_phase`, miễn preview khi `investigate`, hậu tố `· kind:inv` `<600c`. |
| Evidence, Lint & Bench (`M2`) | Thiếu `evidence` CLI; `blackboard_record` thiếu lock; `R10`/`R14` chặn `investigate`; `bench` đẩy artifact về `tu_lam`. | Shard + `evidence add/merge/render` (`--claim-file`, `with_ntfs_lock`), `no_worktree` 4 chốt + `handoff-schema.json`, miễn `R10`/`R14` & cô lập `bench/*.py`. |
| Hooks Python & Rust (`M3`–`M4`) | `"reviewer"` substring lọt `security-reviewer`; `canonical_or_ancestor` 1 cấp; sót `cmd /c`/`[IO.File]`; mù MCP & bỏ qua `resume`/`mode`. | Bảo mật `scoped-write` 5 tầng + Allow trực tiếp tại Rust; giữ `<0.5ms` `has_range` + Weighted Burden `sid` tái sử dụng `"DOC"` (`22` mã AGY). |
| Skills, Agents & AGY (`M5`–`M6`) | Thiếu `investigate-mode.md`; `spec-template`/`qc`/`team-mode` sát trần `3,500`; `tools/patches` ép `4` role đọc `100%`. | Có `investigate-mode.md` EN (`<=3,000` tok); tỉa `40–60` tok trước pointer; `tdq-debugger` có `Point-of-Commitment`; rebuild + validate AGY plugin. |

## Ràng buộc toàn cục & Bản đồ Sở hữu Hợp đồng (Ownership Map)

- Luật import (`docs/kien-truc.md`): `scripts/` tuyệt đối không `import` từ `hooks/scripts/`; chỉ đọc AST nếu cần.
- Bất biến Test Pinning: giữ `len(PHASE_TABLE) == 11`, giữ `22` mã ở `tools/patches/gate_guidance.json`, giữ nguyên bảng `lite/full/ultra` trong `qc.md`, giữ `tdq-reviewer` `<= 1` dòng tùy chọn trong `tdq-spec`/`tdq-plan`, giữ trần `SKILL_LINE_LIMITS` và `<= 3,500` tokens trên toàn bộ `docs/tdq/token-budget.json`.

| Hợp đồng / Giao diện | Định nghĩa cốt lõi | Task sở hữu | Task tiêu thụ |
|---|---|---|---|
| `WorkKindStateContract` | `work_kind` (`build\|investigate`), `work_kind_hieu_luc()`, `INVESTIGATE_PHASE_ROWS`, `escalate-to-build`, `ghi_moc_phase` ở `_cli_approve`, `_archify_gate` waiver, `· kind:inv`. | `T1.1` | `T1.2`, `T2.1`, `T2.2`, `T2.3`, `T4.1` |
| `InvestigateLintScaffoldContract` | `rule_r10`/`r14_loi` exemption, tách `docs/tdq/{artifacts,bench}/<slug>/*.py` khỏi code sản phẩm, `is_created` cho `Sinh ra:`, `t_hop=0.0` cho `no_worktree`. | `T1.2` | `T1.3`, `T2.1`, `T4.1` |
| `InvestigateDocsContract` | `investigate-mode.md` EN (`<=3,000` tok), pruning `spec-template`/`qc`/`team-mode`, `quick-lane-mini.md` (`<=65L`), `issue-triage.md` Two-Stage Bugfix. | `T1.3` | `T3.1`, `T4.1` |
| `EvidenceAndNoWorktreeContract` | `evidence add\|merge\|render` (`--claim-file`, `with_ntfs_lock`), `blackboard_record` NTFS lock, `worktree_required: false`, `handoff-schema.json`. | `T2.1` | `T3.1`, `T4.1` |
| `ScopedSecurityAndBurdenContract` | 5 tầng `scoped-write` Python & Rust (`security-reviewer` đọc `100%`, `ancestors()`, denylist, `cmd /c`, `[IO.File]`), Weighted Burden `sid` giữ `has_range` `<0.5ms` & tái dùng `"DOC"`. | `T2.2`, `T2.3` | `T3.1`, `T4.1` |
| `AgyPluginV2BundleContract` | `agents/tdq-{explorer,debugger,reviewer}.md`, `tools/patches/*`, `plugins/tdq-workflow-agy/` (`tdq-dispatch.exe`), `agy.EXE plugin validate --strict`. | `T3.1` | `T4.1` |

## P1 — Đợt 1: State, Telemetry, Linter/Scaffold/Bench & Quy chuẩn `skills/`

- [x] **T1.1** (e14m) Triển khai `work_kind`, `INVESTIGATE_PHASE_ROWS`, `escalate-to-build`, vá `_cli_approve` (`ghi_moc_phase`) & `_archify_gate` trong `scripts/tdq_state.py` — Test: `py -3 -X utf8 -m pytest tests/test_state.py tests/test_phase_table.py -q`
  - Req: `§2#1`, `§2b(M1)`, `Q1` · Ngoài phạm vi: `GIỮ NGUYÊN` `len(PHASE_TABLE) == 11`, object identity trong `PHASE_TABLE` cho `build`, và `schema_version = 6`.
  - Chạm: `scripts/tdq_state.py`, `tests/test_state.py`, `tests/test_phase_table.py`
  - Cần: Không
  - Tham chiếu: `docs/tdq/artifacts/2026-11-20-2355-toi-uu-research-phan-tich/de-xuat-kien-truc-v2.md`
  - Giao tiếp: Consumes: CLI args & `docs/tdq/state.json` | Produces: `VALID_WORK_KINDS`, `work_kind_hieu_luc()`, `INVESTIGATE_PHASE_ROWS`, `_cli_escalate_to_build()`, fixed `_cli_approve` & `_archify_gate`
  - Neo & Công cụ: `Edit` `scripts/tdq_state.py` (`default_state`, `cong_dang_cho`, `phase_row`, `next_headline`, `render_state_md`, `_archify_gate`, `_cli_approve`, `cli`); `Edit` `tests/test_state.py`, `tests/test_phase_table.py`
  - Trước → Sau: Thiếu `work_kind`, `_cli_approve` quên `ghi_moc_phase`, `_archify_gate` ép preview mọi ca, `set` cho đổi tự do → Đủ `work_kind`, vá `im=0s`, miễn preview khi `investigate`, khóa đổi qua `escalate-to-build --by`, hậu tố `· kind:inv` giữ `Done when:` `<600c`.
  - Tiêu chí chấp nhận (EARS): KHI duyệt `plan`/`quick` hoặc chạy `init --kind investigate`, HỆ THỐNG PHẢI ghi `ghi_moc_phase(state, "implement")`, miễn `_archify_gate` preview cho `investigate`, từ chối `set work_kind=build` nếu không qua `escalate-to-build --by`, và kiểm `spec_sha256` drift.
  - Logic cốt lõi: Thêm `normalize_work_kind` fail-closed về `"build"`; rẽ `phase_row` sang `INVESTIGATE_PHASE_ROWS` khi `investigate`; thêm `ghi_moc_phase` sau `state["phase"] = "implement"` tại `_cli_approve`; thêm subcommand `escalate-to-build --by`.
  - Ca góc hiểm & Assert: Giá trị `work_kind` rác hoặc `None` rơi về `"build"` kèm `_warn`; `len(PHASE_TABLE) == 11` · `assert tdq_state.work_kind_hieu_luc({"work_kind": "invalid"}) == "build" and len(tdq_state.PHASE_TABLE) == 11`

- [x] **T1.2** (e12m) Cập nhật `scripts/doc_lint.py` (`rule_r10`/`r14_loi`/cô lập `bench/*.py`), `scripts/tdq_plan_scaffold.py` (`is_created`) & `scripts/tdq_bench.py` (`no_worktree`) — Test: `py -3 -X utf8 -m pytest tests/test_doc_lint.py tests/test_plan_v2_linter.py -q`
  - Req: `§2#1`, `§2b(M2)`, `Q1` · Ngoài phạm vi: `GIỮ NGUYÊN` `SKILL_LINE_LIMITS["tdq-plan"] == 132` và mọi fixture test `build` hiện hành.
  - Chạm: `scripts/doc_lint.py`, `scripts/tdq_plan_scaffold.py`, `scripts/tdq_bench.py`, `tests/test_doc_lint.py`, `tests/test_plan_v2_linter.py`
  - Cần: `T1.1`
  - Tham chiếu: `scripts/tdq_state.py`, `docs/tdq/artifacts/2026-11-20-2355-toi-uu-research-phan-tich/de-xuat-kien-truc-v2.md`
  - Giao tiếp: Consumes: Spec/Plan Markdown & task dict | Produces: `_is_investigate_doc()`, `is_product_source_path()`, per-path `is_created` tracking, `t_hop=0.0` cho `no_worktree`
  - Neo & Công cụ: `Edit` `scripts/doc_lint.py` (`rule_r10`, `_check_code_or_config`, `r15_loi`, `r14_loi`), `scripts/tdq_plan_scaffold.py` (`_is_new_file_in_task`, `_build_created_files_by_task`, `_verify_single_task`), `scripts/tdq_bench.py` (`mo_phong_tasks`), `tests/test_doc_lint.py` (`R10Test`), `tests/test_plan_v2_linter.py`
  - Trước → Sau: `rule_r10` & `r14_loi` chặn spec `investigate`; `docs/tdq/bench/<slug>/*.py` bị coi là code sản phẩm; `--verify-plan` báo thiếu file trên đĩa với `Sinh ra:`; `tdq_bench` tính `t_hop` cho `no_worktree` → Xử lý chính xác toàn bộ `4` điểm.
  - Tiêu chí chấp nhận (EARS): KHI spec có header `Work kind: investigate`, HỆ THỐNG PHẢI miễn `§2b` ở `rule_r10` và ngưỡng benchmark phi-code ở `r14_loi`, bỏ qua kiểm tra có sẵn trên đĩa cho đường dẫn `Sinh ra:` ở `--verify-plan`, và không ép `R15-Full` với script tạm dưới `docs/tdq/bench/`.
  - Logic cốt lõi: Nhận diện header `Work kind: investigate` trong 15 dòng đầu; thêm `is_product_source_path(rel)` loại trừ `docs/tdq/{artifacts,bench}/`; tách tập `created_paths` từ `Sinh ra:` ở `_build_created_files_by_task`; kiểm `worktree_required is False` ở `tdq_bench`.
  - Ca góc hiểm & Assert: Spec `build` thiếu `§2b` vẫn bị `R10` chặn; script ngoài `docs/tdq/` vẫn kích hoạt `R15-Full` · `assert any("[R10]" in e for e in build_err) and not inv_err`

- [x] **T1.3** (e14m) Tạo `skills/tdq-conventions/references/investigate-mode.md` (EN `<=3,000` tok) và tỉa/gắn pointer trên `skills/` đảm bảo trần token & dòng — Test: `py -3 -X utf8 -c "import subprocess, sys; [subprocess.run([sys.executable, '-X', 'utf8', *c], check=True) for c in (['scripts/token_budget.py', '--kiem'], ['scripts/i18n_check.py', 'skills/tdq-conventions/references/investigate-mode.md'], ['-m', 'pytest', 'tests/test_muc_qc_qc_md.py', 'tests/test_gate_merge.py', 'tests/test_skill_shape.py', '-q'])]"`
  - Req: `§2#1`, `§2b(M5)`, `Q1` · Ngoài phạm vi: `GIỮ NGUYÊN` bảng `lite/full/ultra` trong `qc.md`, giữ `"tdq-reviewer"` `<=1` dòng tùy chọn ở `tdq-spec`/`tdq-plan`, giữ `SKILL_LINE_LIMITS`.
  - Chạm: `skills/tdq-conventions/SKILL.md`, `skills/tdq-intake/SKILL.md`, `skills/tdq-spec/SKILL.md`, `skills/tdq-build/SKILL.md`, `skills/tdq-spec/references/spec-template.md`, `skills/tdq-build/references/qc.md`, `skills/tdq-build/references/team-mode.md`, `skills/tdq-intake/references/quick-lane-mini.md`, `skills/tdq-intake/references/issue-triage.md`, `docs/tdq/token-budget.json`
  - Sinh ra: `skills/tdq-conventions/references/investigate-mode.md`
  - Cần: Không
  - Tham chiếu: `docs/tdq/artifacts/2026-11-20-2355-toi-uu-research-phan-tich/de-xuat-kien-truc-v2.md`, `skills/tdq-build/references/qc-vong-fix.md`
  - Giao tiếp: Consumes: `docs/tdq/token-budget.json` & `doc_lint` R5/R6/R13 | Produces: `investigate-mode.md` EN (`<=3,000` tok) + các pointer 1 dòng sạch ngân sách
  - Neo & Công cụ: `Write` `skills/tdq-conventions/references/investigate-mode.md`; `Edit` `tdq-conventions/SKILL.md`, `tdq-intake/SKILL.md`, `tdq-spec/SKILL.md`, `tdq-build/SKILL.md`, `spec-template.md`, `qc.md`, `team-mode.md`, `quick-lane-mini.md`, `issue-triage.md`; chạy `scripts/token_budget.py --khoa`
  - Trước → Sau: Chưa có chuẩn `investigate-mode.md`; `spec-template`/`qc`/`team-mode` chỉ dư `14/21/28` tok; `quick-lane-mini.md` khóa `40` dòng → Có `investigate-mode.md` EN đầy đủ Tier 0 SAS + `QC-I1..I4` + Two-Stage Bugfix; mọi file dưới trần `3,500` tok và `0` lỗi `i18n_check`.
  - Tiêu chí chấp nhận (EARS): KHI chạy `token_budget.py --kiem`, `i18n_check.py`, `test_muc_qc_qc_md.py`, `test_gate_merge.py`, HỆ THỐNG PHẢI đạt `0` vi phạm và mọi file `skills/` giữ `<= 3,500` tokens.
  - Logic cốt lõi: Soạn `investigate-mode.md` tiếng Anh câu `<=40` từ; tỉa `40–60` tok văn xuôi thừa ngoài vùng pin ở `spec-template.md`/`qc.md`/`team-mode.md` trước khi thêm 1 dòng link; tỉa ví dụ lặp trong 4 `SKILL.md` để không vượt trần dòng; nâng `quick-lane-mini.md` lên `<=65L` cho `quick+investigate`; cập nhật `issue-triage.md` Two-Stage Bugfix.
  - Ca góc hiểm & Assert: Không sửa ô bảng `lite/full/ultra` trong `qc.md`; chạy `token_budget.py --khoa` để khớp `sha256` · `assert tb["skills/tdq-conventions/references/investigate-mode.md"]["token"] <= 3000`

**Xong P1 khi**: Cả `T1.1`, `T1.2`, `T1.3` xanh sạch, `token_budget.py --kiem` & `i18n_check.py` `exit 0`.

## P2 — Đợt 2: Evidence Shard-Merge, Bảo mật `scoped-write` Python & Rust Burden Checkpoint

- [x] **T2.1** (e14m) Triển khai `evidence add|merge|render` (`--claim-file`, NTFS lock), bọc khóa `blackboard_record`, hỗ trợ `no_worktree` & mở rộng `handoff-schema.json` — Test: `py -3 -X utf8 -m unittest tests.test_team_packet_v2`
  - Req: `§2#2`, `§2b(M2)`, `Q2` · Ngoài phạm vi: `GIỮ NGUYÊN` toàn bộ lệnh `assign`, `wave`, `open`, `check`, `merge` cho task `build` có worktree.
  - Chạm: `scripts/tdq_team.py`, `scripts/tdq_ten_lenh.py`, `skills/tdq-conventions/references/handoff-schema.json`, `tests/test_team_packet_v2.py`
  - Cần: `T1.1`, `T1.2`
  - Tham chiếu: `hooks/scripts/_common.py`, `scripts/tdq_state.py`
  - Giao tiếp: Consumes: `WorkKindStateContract` | Produces: CLI `evidence add|merge|render`, `_ntfs_lock` nội bộ trong `tdq_team.py`, `is_artifact_only_paths()`, `worktree_required: false`, schema `handoff-schema.json` mở rộng
  - Neo & Công cụ: `Edit` `scripts/tdq_team.py` (`_finalize_tasks`, `quyet_dinh_task`, `lenh_phan_cong`, `canh_bao_lach_luat`, `validate_handoff_payload`, `blackboard_record`, `_build_packet_payload`, `main`), `skills/tdq-conventions/references/handoff-schema.json`, `tests/test_team_packet_v2.py` (evidence engine written; finishing parser CLI)
  - Trước → Sau: Chưa có `evidence` CLI; `blackboard_record` không có khóa NTFS; `no_worktree` bị `canh_bao_lach_luat` và `handoff-schema.json` chặn → Có Shard + Leader-Merge khóa NTFS, `--claim-file` sạch shell, `no_worktree` thông suốt.
  - Tiêu chí chấp nhận (EARS): KHI chạy đồng thời nhiều worker ghi shard `.ev.jsonl` + gọi `blackboard_record` và `evidence merge`, HỆ THỐNG PHẢI bảo toàn `100%` bản ghi không mất dòng/hỏng JSON, chấp nhận handoff `no_worktree` và từ chối trường lạ.
  - Logic cốt lõi: Cài helper khóa tệp cục bộ `msvcrt.locking`/`fcntl.flock` ngay trong `tdq_team.py` (giữ luật không import từ `hooks/scripts/`); đọc `--claim-file`/`--excerpt-file` UTF-8; append nguyên tử vào `evidence.jsonl` và render tất định `evidence-log.md`; gắn `worktree_required: false` cho đích thuần `docs/tdq/{artifacts,research}/`.
  - Ca góc hiểm & Assert: Từ chối đường dẫn `..` trong `is_artifact_only_paths`; `validate_handoff_payload` vẫn bác payload thiếu trường hoặc vượt `1,500` chars · `assert tdq_team.is_artifact_only_paths(["docs/tdq/artifacts/s/../state.json"]) is False`

- [x] **T2.2** (e16m) Triển khai bảo mật `scoped-write` `5` tầng, vá `cmd /c` & `[IO.File]`, sửa `subagent_stop`, anchor tĩnh + `TDQ:GON` investigation trên Python hooks — Test: `py -3 -X utf8 -m pytest tests/test_bash_gate.py tests/test_read_gate.py tests/test_hooks_dual_protocol.py -q`
  - Req: `§2#2`, `§2b(M3)`, `§2b(M4)`, `Q2`, `Q3` · Ngoài phạm vi: `GIỮ NGUYÊN` `22` mã AGY trong `gate_guidance.json` và `.codex/hooks.json`.
  - Chạm: `hooks/scripts/_common.py`, `hooks/scripts/edit_gate.py`, `hooks/scripts/bash_gate.py`, `hooks/scripts/prompt_context.py`, `hooks/scripts/session_start.py`, `hooks/scripts/subagent_stop.py`, `hooks/scripts/read_gate.py`, `hooks/hooks.json`, `tests/test_bash_gate.py`, `tests/test_read_gate.py`
  - Cần: `T1.1`
  - Tham chiếu: `scripts/tdq_state.py`, `tools/patches/gate_guidance.json`
  - Giao tiếp: Consumes: `WorkKindStateContract` | Produces: `is_investigation_artifact_target()`, `_normalize_tool_aliases()`, bảo vệ `cmd /c` + `[IO.File]`, tách đăng ký `PostToolUse` ở `subagent_stop.py`, anchor tĩnh `<600c` + `TDQ:GON` gọn
  - Neo & Công cụ: `Edit` `hooks/scripts/_common.py`, `edit_gate.py`, `bash_gate.py`, `prompt_context.py`, `session_start.py`, `subagent_stop.py`, `read_gate.py`, `hooks/hooks.json`; `Edit` `tests/test_bash_gate.py`, `tests/test_read_gate.py` (step 1 done: `_common`/`edit_gate`/`bash_gate`/`subagent_stop`/`hooks.json`)
  - Trước → Sau: `"reviewer"` substring lọt `tdq-security-reviewer`; `bash_gate` sót `cmd /c` & `[IO.File]`; `subagent_stop` chấm sớm tại `PostToolUse`; `prompt_context` bỏ qua subagent; `TDQ:GON` bơm `7KB` vào điều tra → Vá kín cả 5 lỗ hổng trên Python.
  - Tiêu chí chấp nhận (EARS): KHI `tdq-security-reviewer` hoặc `tdq-explorer` ghi vào `evidence.jsonl`, `trial_1.json`, symlink thoát gốc, hay chạy `cmd /c` / `[IO.File]::WriteAllText`, HỆ THỐNG PHẢI chặn `[TDQ:READONLY]`; KHI `tdq-explorer` ghi đúng `<active_slug>/t1.md`, PHẢI cho phép và ghi `observe("edit")`.
  - Logic cốt lõi: Deny-first + exact allowlist `_SCOPED_ARTIFACT_ROLES`; leo `ancestors()` + `os.path.realpath` chống junction/8.3; denylist `evidence*`/`trial_*.json`/`rec_*.json`; thêm `cmd(?:\.exe)?\b\s+/c` & `\[(?:System\.)?IO\.File\]::`; chỉ đăng ký metadata ở `PostToolUse(invoke_subagent)`; bơm pointer tĩnh không timestamp giây cho cả main & subagent; thêm matcher `search_web` ở `hooks/hooks.json`.
  - Ca góc hiểm & Assert: `tdq-security-reviewer` luôn bị chặn kể cả trong `docs/tdq/artifacts/<slug>/` · `assert is_investigation_artifact_target("docs/tdq/artifacts/s/evidence.jsonl", cwd, "s") is False`

- [x] **T2.3** (e18m) Đồng bộ Rust `tdq-dispatch`: `scoped-write` `5` tầng + Allow trực tiếp, vá `cmd /c` & `[IO.File]`, Weighted Burden `sid` giữ `<0.5ms` `has_range` & `resume`/`mode` — Test: `cargo test --manifest-path hooks/rust/tdq-dispatch/Cargo.toml`
  - Req: `§2#2`, `§2b(M3)`, `§2b(M4)`, `Q2`, `Q3`, `Q4` · Ngoài phạm vi: `GIỮ NGUYÊN` fast-path `<0.5ms` `has_range` tại `pre_tool_use.rs:444` và đúng `22` mã AGY (tái dùng `"DOC"`).
  - Chạm: `hooks/rust/tdq-dispatch/src/storage.rs`, `hooks/rust/tdq-dispatch/src/protocol.rs`, `hooks/rust/tdq-dispatch/src/command_parser.rs`, `hooks/rust/tdq-dispatch/src/events/pre_tool_use.rs`, `hooks/rust/tdq-dispatch/src/events/post_tool_use.rs`, `hooks/rust/tdq-dispatch/src/events/pre_invocation.rs`, `hooks/rust/tdq-dispatch/src/events/session_start.rs`, `hooks/rust/tdq-dispatch/src/events/user_prompt_submit.rs`, `hooks/rust/tdq-dispatch/src/events/stop_streak.rs`, `tests/test_rust_lock_safety.py`
  - Cần: `T1.1`
  - Tham chiếu: `hooks/scripts/_common.py`, `hooks/scripts/edit_gate.py`, `hooks/scripts/bash_gate.py`
  - Giao tiếp: Consumes: `HookPayload` & `docs/tdq/state.json` | Produces: `target/release/tdq-dispatch.exe` xanh `cargo test` & `cargo clippy -- -D warnings`
  - Neo & Công cụ: `Edit` `hooks/rust/tdq-dispatch/src/storage.rs` (`L19-55`), `hooks/rust/tdq-dispatch/src/protocol.rs` (`L280-296`), `hooks/rust/tdq-dispatch/src/command_parser.rs` (`L161-221`), `hooks/rust/tdq-dispatch/src/events/pre_tool_use.rs` (`L58-178`, `L290-335`, `L444-463`), `hooks/rust/tdq-dispatch/src/events/post_tool_use.rs` (`L70-95`), `hooks/rust/tdq-dispatch/src/events/pre_invocation.rs` (`L135-170`); chạy `cargo test`, `cargo clippy -- -D warnings`, `cargo build --release` (Batch 2 events in progress)
  - Trước → Sau: `storage.rs` thiếu `work_kind`/`"mode"`; `pre_invocation.rs` sót `"resume"` & subagent; `pre_tool_use.rs` lọt `security-reviewer`, resolve 1 cấp, rơi `DelegatePython` (`L333`) & mù MCP/range; `post_tool_use.rs:76` ghi schema chết → Đồng bộ 100% Python, Allow trực tiếp tại Rust, Weighted Burden `sid` phát `[TDQ:DOC]` ở `>=40` điểm mà không làm chậm `has_range`.
  - Tiêu chí chấp nhận (EARS): KHI chạy `cargo test` và `cargo clippy -- -D warnings`, HỆ THỐNG PHẢI pass `100%` test Rust với `0` warning, chặn mọi vector bypass `scoped-write`/`cmd /c`/`[IO.File]`, và phát nhắc `[TDQ:DOC]` ở `score >= 40` theo đúng từng `sid`.
  - Logic cốt lõi: Leo vòng lặp `Path::ancestors()` tới gốc tồn tại để `fs::canonicalize` trước prefix; trả `RouteOutcome::Decided(HookDecision::allow())` trực tiếp kèm `observe("edit")` cho `scoped-write` hợp lệ; cập nhật gọn `docs/tdq/.tdq-runtime/checkpoint-<sid>.json` (`+3/+2/+1`, ngưỡng `40`, reset theo `sid`) trong Rust; dọn `{ts, khoa, path}` ở `post_tool_use.rs:76`.
  - Ca góc hiểm & Assert: Worker B ghi file không được phép reset bộ đếm `checkpoint-<sidA>.json` của Worker A · Rust unit tests cho `is_scoped_artifact_role("tdq-security-reviewer") == false` và `burden_threshold_triggers_doc_once`

**Xong P2 khi**: `T2.1`, `T2.2`, `T2.3` xanh sạch, `cargo test && cargo clippy -- -D warnings && cargo build --release` `0` lỗi/warning.

## P3 — Đợt 3: Agent Prompts, Compiler AGY & Rebuild Plugin

- [x] **T3.1** (e12m) Cập nhật `3` agent prompt, compiler `tools/patches/*`, tách test `READONLY_AGENTS`, biên dịch `plugins/tdq-workflow-agy/` & kiểm `agy plugin validate --strict` — Test: `py -3 -X utf8 -m pytest tests/test_agent_frontmatter.py tests/test_agy_plugin_validate.py tests/test_gate_guidance.py tests/test_rust_dispatch_parity.py -q`
  - Req: `§2#3`, `§2b(M6)`, `§3b`, `Q4`, `Q6` · Ngoài phạm vi: `GIỮ NGUYÊN` bản cài ngoài repo `~/.gemini/config/plugins/tdq-workflow-agy` (chỉ chạy `--dry-run`) và giữ prebuilt Linux/macOS hiện hữu (`1a`, `2a`).
  - Chạm: `agents/tdq-explorer.md`, `agents/tdq-debugger.md`, `agents/tdq-reviewer.md`, `tools/patches/skills_and_agents.py`, `tools/patches/agy_hooks.py`, `tests/test_agent_frontmatter.py`, `docs/tdq/token-budget.json`
  - Cần: `T1.3`, `T2.1`, `T2.2`, `T2.3`
  - Dùng: `agy-customizations` / `antigravity-guide` / `plugin`
    - Để: Đối chiếu chuẩn frontmatter `tools`, lifecycle `6` sự kiện và bộ kiểm tra `agy.EXE plugin validate --strict` của Google Antigravity 2.0 khi chuyển 3 role điều tra sang `scoped-write` và dọn fallback ở `tools/patches/`.
    - Ra: `plugins/tdq-workflow-agy/` đã biên dịch mới (kèm `tdq-dispatch.exe` Windows vừa build), `agents/tdq-{explorer,debugger,reviewer}.md` mang `[TDQ:SCOPED-WRITE]` & `tdq-security-reviewer.md` giữ `100%` `[TDQ:READONLY]`, `agy.EXE plugin validate --strict --json` trả `findings: []`.
    - Kiểm: `py -3 -X utf8 tools/build_agy_plugin.py --upstream .`
    - Không dùng cho: Không ghi đè `~/.gemini/config/plugins/` (chỉ `--dry-run`) và không cross-compile Linux/macOS.
  - Tham chiếu: `tools/patches/gate_guidance.json`, `tools/build_agy_plugin.py`, `tools/install_agy_plugin.py`
  - Giao tiếp: Consumes: `M1`–`M5` + `target/release/tdq-dispatch.exe` | Produces: `plugins/tdq-workflow-agy/` hoàn chỉnh + `install_agy_plugin.py --dry-run` `exit 0`
  - Neo & Công cụ: `Edit` `agents/tdq-explorer.md`, `agents/tdq-debugger.md`, `agents/tdq-reviewer.md`, `tools/patches/skills_and_agents.py` (`L48-180`), `tools/patches/agy_hooks.py` (`L1455-1475`, `L1720-1755`, `L1870-1890`), `tests/test_agent_frontmatter.py` (`L25-145`); chạy `token_budget.py --khoa`, `tools/build_agy_plugin.py --upstream .`, `tools/install_agy_plugin.py --dry-run` (agents/skills_and_agents done; updating agy_hooks)
  - Trước → Sau: Compiler ép cả `4` role read-only, còn nhánh fallback legacy, `subagent_dispatch_gate` đòi `WORKTREE:` cho mọi `TASK:` → Tách `_STRICT_READONLY_AGENTS` (`tdq-security-reviewer`) vs `_SCOPED_INVESTIGATION_AGENTS`, `tdq-debugger` có `Point-of-Commitment` + Counterfactual Falsification Test, plugin AGY biên dịch sạch `findings: []`.
  - Tiêu chí chấp nhận (EARS): KHI chạy `tools/build_agy_plugin.py --upstream .` và `agy.EXE plugin validate plugins/tdq-workflow-agy --strict --json`, HỆ THỐNG PHẢI trả `"status": "OK"`, `findings: []`, `0` lỗi parity 22 mã AGY và `install_agy_plugin.py --dry-run` thoát `0`.
  - Logic cốt lõi: Chỉ cấp `_WRITER_TOOLS` ở bản build AGY cho 3 role điều tra kèm `[TDQ:SCOPED-WRITE]` (giữ file gốc `agents/tdq-reviewer.md` tương thích `ReadOnlyAgentToolsTest`); bỏ đòi `WORKTREE:` khi prompt/packet có `WORKTREE: none` hoặc `worktree_required: false`; khóa `token-budget.json`.
  - Ca góc hiểm & Assert: `tdq-security-reviewer.md` ở bản compiled có `0` write tools & giữ `[TDQ:READONLY]` · `assert "write_file" not in sec_fm["tools"] and "write_file" in exp_fm["tools"]`

**Xong P3 khi**: `plugins/tdq-workflow-agy/` build mới sạch, `agy.EXE plugin validate --strict` trả `findings: []`, `test_agent_frontmatter` & `test_rust_dispatch_parity` PASS.

## P4 — Bộ Kiểm thử Đối kháng Python ↔ Rust, Mô phỏng 4 Ca Lịch sử & Log

Log: BẮT BUỘC — mọi hàm CLI/hook mới và chỉnh sửa trong `scripts/tdq_state.py`, `scripts/tdq_team.py`, `scripts/doc_lint.py`, `hooks/scripts/*.py` và Rust `tdq-dispatch` đều mặc định ghi log kèm ISO timestamp ra `stderr`, tắt hoàn toàn khi đặt `TDQ_LOG=0`.

- [>] **T4.1** (e16m) Viết bộ kiểm thử tích hợp & đối kháng `tests/test_investigate_workflow.py` (parity Python ↔ `tdq-dispatch.exe`, Weighted Burden `sid`, `TDQ_LOG=0` & harness mô phỏng `4` ca `1056`/`1457`/`1346`/`1953` trong `tmp_path`) — Test: `py -3 -X utf8 -m pytest tests/test_investigate_workflow.py tests/test_rust_latency_benchmark.py -q`
  - Req: `§2#3`, `§4`, `Q2`, `Q3`, `Q5` · Ngoài phạm vi: `GIỮ NGUYÊN` mọi dữ liệu lịch sử dưới `docs/tdq/` (chỉ tạo fixture mô phỏng trong `tmp_path`).
  - Chạm: `tests/test_investigate_workflow.py` (tạo mới)
  - Sinh ra: `tests/test_investigate_workflow.py`
  - Cần: `T3.1`
  - Tham chiếu: `plugins/tdq-workflow-agy/bin/tdq-dispatch.exe`, `tests/test_rust_latency_benchmark.py`, `docs/tdq/artifacts/2026-11-20-2355-toi-uu-research-phan-tich/redteam-c-stress-test-cases.md`
  - Giao tiếp: Consumes: `M1`–`M6` & `plugins/tdq-workflow-agy/` | Produces: `tests/test_investigate_workflow.py` chứng minh `100%` parity & hồi quy `4` ca mẫu
  - Neo & Công cụ: `Write` `tests/test_investigate_workflow.py`
  - Trước → Sau: Chưa có bộ test đối kháng hợp nhất Python ↔ Rust cho `investigate` và chưa có harness `4` ca mẫu → Có bộ test đơn lệnh chứng minh bảo mật 5 tầng, tốc độ `<25ms`, `TDQ_LOG=0` và cải thiện trên `4` kịch bản `1056`, `1457`, `1346`, `1953`.
  - Tiêu chí chấp nhận (EARS): KHI chạy `pytest tests/test_investigate_workflow.py tests/test_rust_latency_benchmark.py -q`, HỆ THỐNG PHẢI pass `100%` mọi vector đối kháng trên cả Python lẫn `tdq-dispatch.exe`, đo `PreToolUse(read_file+range)` median `<= 25.0 ms`, xác nhận `TDQ_LOG=0` im lặng `stderr`, và PASS cả `4` ca mô phỏng.
  - Logic cốt lõi: Tham số hóa ma trận vector bảo mật chạy song song trên `edit_gate`/`bash_gate` Python và subprocess `tdq-dispatch.exe`; kiểm concurrency nhiều thread ghi `evidence` + `blackboard_record`; mô phỏng end-to-end Ca 1 (`1056` miễn preview/§2b), Ca 2 (`1457` quick `<=65L` Tier 0), Ca 3 (`1346` script ở `docs/tdq/bench/<slug>/` không bật `QC-F1`), Ca 4 (`1953` Two-Stage `escalate-to-build`).
  - Ca góc hiểm & Assert: Test Windows 8.3/junction/symlink tạo trực tiếp trong `tmp_path` (skip có kiểm soát chỉ nếu OS chặn tạo symlink không nâng quyền, luôn test junction `mklink /J` trên Windows) · `assert py_decision == rust_decision`

## Cụm song song

- **Wave 1 (`2` nhánh song song độc lập hoàn toàn, tránh TCAS AST collision `tdq_bench → tdq_state`):** `T1.1` (`tdq_state.py`) · `T1.3` (`skills/` + `investigate-mode.md`).
- **Wave 2 (`3` nhánh song song độc lập hoàn toàn sau `T1.1`):** `T1.2` (`doc_lint.py`/`scaffold`/`bench`) · `T2.2` (`hooks/scripts/*` + `hooks.json`) · `T2.3` (`hooks/rust/tdq-dispatch/src/*`).
- **Wave 3 (tuần tự sau `T1.1` + `T1.2`):** `T2.1` (`tdq_team.py` + `handoff-schema.json`).
- **Wave 4 (tuần tự tích hợp & biên dịch plugin sau `T1.3`, `T2.1`, `T2.2`, `T2.3`):** `T3.1` (`agents/`, `tools/patches/*`, rebuild `plugins/tdq-workflow-agy/`).
- **Wave 5 (tuần tự kiểm thử đối kháng & mô phỏng `4` ca sau `T3.1`):** `T4.1` (`tests/test_investigate_workflow.py` + benchmark latency).

## Luật file nóng

- Không có tệp mã nguồn nào bị `2` task trong cùng một đợt sửa chung. Duy nhất `docs/tdq/token-budget.json` được khóa sau `T1.3` (Đợt 1) và tái khóa cuối cùng ở `T3.1` (Đợt 3 — tuần tự, không chạy song song).

## Definition of Done

Trỏ về §6 của spec `docs/tdq/spec/2026-11-21-0217-trien-khai-investigate-v2.md` (`muc_qc=full`):

- [ ] **Q1** Đợt 1 State, Telemetry, Lint & Docs (`work_kind`, `PHASE_TABLE == 11`, `_cli_approve`, `_archify_gate`, `R10`/`R14`, `token-budget <= 3,500`, `investigate-mode.md <= 3,000` tok, `i18n_check 0` lỗi) — `py -3 -X utf8 -c "import subprocess, sys; [subprocess.run([sys.executable, '-X', 'utf8', *c], check=True) for c in (['scripts/token_budget.py', '--kiem'], ['scripts/i18n_check.py', 'skills/tdq-conventions/references/investigate-mode.md'], ['-m', 'pytest', 'tests/test_state.py', 'tests/test_phase_table.py', 'tests/test_doc_lint.py', 'tests/test_plan_v2_linter.py', 'tests/test_muc_qc_qc_md.py', 'tests/test_gate_merge.py', '-q'])]"`
- [ ] **Q2** Đợt 2 Evidence Shard-Merge, NTFS Lock & Bảo mật `scoped-write` 5 tầng (`cmd /c`, `[IO.File]`, `tdq-security-reviewer` đọc 100%) đồng nhất Python ↔ Rust — `py -3 -X utf8 -m pytest tests/test_team_packet_v2.py tests/test_bash_gate.py tests/test_investigate_workflow.py -q`
- [ ] **Q3** Đợt 2 Weighted Burden Rust theo `sid` (`>=40` điểm phát `[TDQ:DOC]`), bảo toàn fast-path `has_range` (`<= 25.0 ms` hot-direct) và giữ nguyên `22` mã AGY — `py -3 -X utf8 -m pytest tests/test_read_gate.py tests/test_gate_guidance.py tests/test_hooks_dual_protocol.py tests/test_rust_dispatch_parity.py tests/test_rust_latency_benchmark.py -q`
- [ ] **Q4** Đợt 3 Agents, Rust `cargo test && cargo clippy`, Rebuild `plugins/tdq-workflow-agy/`, `agy.EXE plugin validate --strict` (`findings: []`) & `install_agy_plugin.py --dry-run` — `py -3 -X utf8 -c "import json, shutil, subprocess, sys; subprocess.run(['cargo', 'test', '--manifest-path', 'hooks/rust/tdq-dispatch/Cargo.toml'], check=True); subprocess.run(['cargo', 'clippy', '--manifest-path', 'hooks/rust/tdq-dispatch/Cargo.toml', '--', '-D', 'warnings'], check=True); subprocess.run([sys.executable, '-X', 'utf8', 'tools/build_agy_plugin.py', '--upstream', '.'], check=True); subprocess.run([sys.executable, '-X', 'utf8', 'tools/install_agy_plugin.py', '--dry-run'], check=True); agy = shutil.which('agy.EXE') or shutil.which('agy') or r'C:\Users\admin\AppData\Local\Programs\Antigravity\bin\agy.EXE'; out = subprocess.check_output([agy, 'plugin', 'validate', 'plugins/tdq-workflow-agy', '--strict', '--json'], text=True); assert json.loads(out).get('findings') == [], out; print('Q4_PASS')"`
- [ ] **Q5** Nghiệm thu trọn bộ `scripts/tdq_test.py tron-bo` (`bo_sot == 0`), harness mô phỏng `4` ca lịch sử (`1056`, `1457`, `1346`, `1953`) trong `tmp_path`, `TDQ_LOG=0` — `py -3 -X utf8 scripts/tdq_test.py tron-bo --workers 1 --fresh --reuse off`
- [ ] **Q6** Sạch Hiến pháp & Zero-Side-Effect ngoài phạm vi (`~/.gemini/` chưa bị ghi đè, `doc_lint` 0 lỗi, Archify HTML báo cáo `current` & Tailscale HTTP `200`, `tdq-qc-tester` ký PASS `Q1`–`Q6` & `QC-F1`–`QC-F4`) — `py -3 -X utf8 scripts/doc_lint.py docs/tdq/reports/2026-11-21-0217-trien-khai-investigate-v2.md`
