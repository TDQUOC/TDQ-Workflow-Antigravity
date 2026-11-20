# Brief: Triển khai trọn bộ 3 đợt Kiến trúc V2 (`work_kind=investigate`)

Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

## Nguyên văn

> okay mở request lên kế hoạch thực hiện cả 3 đợt trong 1 request giúp tôi

### Đọc hiểu ban đầu

- **Mục tiêu:** Lên kế hoạch chi tiết và triển khai trọn vẹn cả `3` đợt theo bản **Đề xuất Kiến trúc Hoàn chỉnh V2** ([de-xuat-kien-truc-v2.md](../../artifacts/2026-11-20-2355-toi-uu-research-phan-tich/de-xuat-kien-truc-v2.md)) trong một request `feature` thống nhất — bảo đảm tách luồng `work_kind=investigate`, vá `100%` `9` cụm nhược điểm Red-Team (`ND-1`–`ND-9`), giữ hiệu năng Rust `<0.5ms`, đạt `100%` parity Python ↔ Rust ↔ AGY Plugin và vượt qua trọn bộ test hồi quy.
- **Đầu vào nền đã có từ request `2026-11-20-2355-toi-uu-research-phan-tich`:**
  - Hồ sơ kiến trúc V2: `docs/tdq/artifacts/2026-11-20-2355-toi-uu-research-phan-tich/de-xuat-kien-truc-v2.md` (`M1`–`M6`, lộ trình `3` đợt, truy vết `ND-1`–`ND-9`).
  - Kho bằng chứng `29` `EV-xxx`: `docs/tdq/artifacts/2026-11-20-2355-toi-uu-research-phan-tich/evidence-log.md`.
- **Phạm vi dự kiến (`3` đợt trong `1` request):**
  - **Đợt 1 — Core State, Lint, Archify & Docs Foundation:** `scripts/tdq_state.py`, `scripts/doc_lint.py`, `scripts/tdq_plan_scaffold.py`, `scripts/tdq_bench.py`, `skills/tdq-conventions/references/investigate-mode.md` (EN `<3,000` tok), tỉa nhẹ `spec-template.md`/`qc.md`/`team-mode.md` + pointer `SKILL.md`, cập nhật `quick-lane-mini.md` & `issue-triage.md`, `tests/test_doc_lint.py` (`R10Test`).
  - **Đợt 2 — Evidence Engine, Security `scoped-write` & Rust Burden Checkpoint:** `scripts/tdq_team.py` (`evidence add/merge/render`, `--claim-file`, `with_ntfs_lock`, `no_worktree`), `handoff-schema.json`, `hooks/scripts/{_common,edit_gate,bash_gate,prompt_context,session_start,subagent_stop,read_gate}.py`, `hooks/rust/tdq-dispatch/src/{storage,protocol,command_parser}.rs` & `events/{pre_tool_use,post_tool_use,pre_invocation}.rs`, plus ma trận test đối kháng Python ↔ Rust `tests/test_investigate_workflow.py`.
  - **Đợt 3 — Agent Prompts, Compiler AGY & Validate E2E:** `agents/tdq-{explorer,debugger,reviewer}.md`, `tools/patches/{skills_and_agents,agy_hooks}.py`, `hooks/hooks.json` (`search_web`), `tests/test_agent_frontmatter.py` (tách `_STRICT_READONLY_AGENTS`), tái khóa `docs/tdq/token-budget.json`, biên dịch lại `plugins/tdq-workflow-agy/` & chạy `agy.EXE plugin validate --strict`, kiểm hồi quy trọn bộ test + benchmark kiểm chứng `4` ca mẫu.
- **Điểm cần làm rõ sau khi chọn pipeline (ở pha phân tích & phỏng vấn):**
  - Chi tiết phạm vi test/build Rust (`cargo build --release` trên Windows và đồng bộ `dist/`/`plugins/` nếu cần), cài đặt bản plugin ra `~/.gemini/config/plugins/` hay chỉ build trong repo, và mức kiểm chứng E2E mong muốn (`muc_qc`).

> Bỏ qua Scope Round vì người dùng đã chốt rõ phạm vi triển khai trọn bộ `3` đợt theo Đề xuất Kiến trúc Hoàn chỉnh V2 (`2026-11-20-2355`).

## Hiểu & kiến thức

### Năng lực dùng được (B0 — `skill_inventory.py`)

| Skill / Công cụ | Nguồn | Phán quyết | Dùng ở đâu / Lý do loại |
|---|---|---|---|
| `tdq-intake` / `tdq-spec` / `tdq-plan` / `tdq-build` / `tdq-conventions` / `tdq-setup` / `tdq-lean` | plugin:tdq-workflow / agy | NỀN | Khung quy trình chuẩn `deep` (`analyze → spec → plan → implement → qc → report`), 3 tầng tìm kiếm, clean code |
| `agy-customizations` / `antigravity-guide` / `plugin` | built-in | DÙNG | Đối chiếu chuẩn plugin, frontmatter, tool Antigravity 2.0 khi cập nhật `tools/patches/*` & validate `plugins/tdq-workflow-agy` |
| Đã xét 19 skill ẩn & các skill built-in khác (`gdocs`, `gsheets`, `gemini-api-*`, `chrome-devtools`…) | disk / built-in | KHÔNG | Khác lĩnh vực hoặc không cần cho triển khai mã nguồn Python/Rust/Plugin |

### Khảo sát 3 chiều & Vùng ảnh hưởng Thực tế (B1)

- **Nguồn kiến trúc V2 & 29 bằng chứng gốc:** `docs/tdq/artifacts/2026-11-20-2355-toi-uu-research-phan-tich/de-xuat-kien-truc-v2.md` (`M1`–`M6`, `ND-1`–`ND-9`) và `evidence-log.md` (`EV-001`–`EV-029`).
- **Kết quả LSP & Grep mở rộng cho kế hoạch triển khai:**
  - **Rust `hooks/rust/tdq-dispatch`:** `tdq_lsp.py` ĐẠT (`needs_python_command_gate`: `3` refs; `cong_dang_cho` tại `storage.rs:52`: `10` LSP refs). `Cargo.toml` nằm ở `hooks/rust/tdq-dispatch/Cargo.toml` (`edition = 2021`). Trên Windows, `tools/build_agy_plugin.py:94-160` tự gọi `cargo build --release` tạo `tdq-dispatch.exe` và giữ/copy `tdq-dispatch-linux-x86_64` + `tdq-dispatch-darwin-arm64` từ `plugins/tdq-workflow-agy/bin/` (`prebuilt/` không có trên đĩa).
  - **Python callers & test pinning bổ sung ngoài hồ sơ V2:** `validate_handoff_payload` và `blackboard_record` được test tại `tests/test_agent_upgrade_mvp.py:587-612` & `tests/test_team_packet_v2.py:491-588`; `effective_phase` / `phase_row` / `cong_dang_cho` trải trên `ask_gate.py`, `agy_stop_gate.py`, `search_gate.py`, `stop_streak.rs`, `tests/test_state.py:454-490`, `tests/test_team_mode.py:124-129`. Toàn bộ test parity/E2E (`test_rust_dispatch_parity.py`, `test_e2e_workflow.py`, `test_hook_dispatch_r1_r3.py`, `test_rust_latency_benchmark.py`, `test_agent_upgrade_mvp.py`, `test_agy_plugin_validate.py`) chạy thẳng trên `plugins/tdq-workflow-agy/`, nên **bắt buộc chạy `tools/build_agy_plugin.py --upstream .` trước khi chạy test Đợt 2–3**.
  - **Cơ chế cài đặt người dùng:** `tools/install_agy_plugin.py` đồng bộ `plugins/tdq-workflow-agy/` sang `~/.gemini/config/plugins/tdq-workflow-agy` (có hỗ trợ `--dry-run`, RTK & Caveman).

### Lộ trình

- **Luồng 1 (Đợt 1 — State, Telemetry, Lint & Docs Foundation):** Bổ sung `work_kind` (`build | investigate`), `INVESTIGATE_PHASE_ROWS`, `escalate-to-build`, vá bug `_cli_approve` (`ghi_moc_phase`), miễn Archify preview trong `_archify_gate`, hỗ trợ `rule_r10`/`r14_loi`/bench `.py` trong `doc_lint.py` và `is_created` trong `tdq_plan_scaffold.py`, soạn `investigate-mode.md` (EN `<3,000` tok) và tỉa gọn template/pointer tuân thủ `token-budget.json` & `SKILL_LINE_LIMITS`.
- **Luồng 2 (Đợt 2 — Evidence Shard-Merge, Security `scoped-write` & Rust Burden Checkpoint):** Bổ sung `evidence add/merge/render` (`--claim-file`, `with_ntfs_lock` cho `evidence.jsonl` & `blackboard_record`), mở `no_worktree` xuyên 4 chốt + `handoff-schema.json`, vá `scoped-write` 5 tầng bảo vệ (Deny-first + exact roles + recursive `ancestors()` + denylist + `cmd /c` & `[IO.File]`) song song Python & Rust, giữ fast-path `<0.5ms` `has_range` tại `pre_tool_use.rs:444` kết hợp Weighted Burden `sid` tái sử dụng mã `"DOC"` (`22` mã AGY), và khóa `tests/test_investigate_workflow.py`.
- **Luồng 3 (Đợt 3 — Agent Prompts, Compiler AGY, Rebuild & Validate E2E):** Nâng cấp prompt `agents/tdq-{explorer,debugger,reviewer}.md` (kèm `Point-of-Commitment` vs `Manifestation`), cập nhật `tools/patches/{skills_and_agents,agy_hooks}.py` và `hooks/hooks.json` (`search_web`), phân tách `_STRICT_READONLY_AGENTS` trong `tests/test_agent_frontmatter.py`, tái khóa `token-budget.json`, biên dịch `tools/build_agy_plugin.py --upstream .`, kiểm `agy.EXE plugin validate --strict`, chạy test hồi quy toàn suite & benchmark mô phỏng `4` ca lịch sử.

## Hỏi đáp

1. Xử lý binary Rust đa nền tảng (`tdq-dispatch-linux-x86_64`, `tdq-dispatch-darwin-arm64`) khi build trên Windows (`Đợt 2–3`)?
   - **User chọn `1a`:** Compile & kiểm thử đầy đủ `tdq-dispatch.exe` trên Windows (`cargo test && cargo clippy && cargo build --release`); giữ nguyên 2 binary Linux/macOS hiện hữu trong `plugins/tdq-workflow-agy/bin/` và ghi rõ trong báo cáo để build bổ sung trên host Linux/macOS khi phát hành.
2. Đồng bộ cài đặt ra plugin người dùng (`~/.gemini/config/plugins/tdq-workflow-agy`) ở cuối Đợt 3?
   - **User chọn `2a`:** Build sạch `plugins/tdq-workflow-agy/` trong repo kèm `tools/install_agy_plugin.py --dry-run`; **chưa ghi đè** `~/.gemini/config/plugins/tdq-workflow-agy` cho đến khi người dùng xác nhận sau pha `qc`.
3. Phạm vi kiểm thử mô phỏng `4` ca lịch sử (`1056`, `1457`, `1346`, `1953`) ở cuối Đợt 3?
   - **User chọn `3a`:** Chạy trọn bộ test tự động cộng thêm harness mô phỏng `4` ca mẫu trong `tmp_path` cô lập để đo Trước → Sau thực tế mà không sửa dữ liệu lịch sử trong `docs/tdq/`.
4. Mức QC (`muc_qc`) cho request triển khai cả `3` đợt này?
   - **User chọn `4a`:** `full` — chạy trọn bộ test suite (`tdq_test.py tron-bo` + `cargo test` + `cargo clippy` + `agy.EXE plugin validate --strict`), `tdq-qc-tester` đối chứng từng mục DoD, và tái khóa `docs/tdq/token-budget.json`.

