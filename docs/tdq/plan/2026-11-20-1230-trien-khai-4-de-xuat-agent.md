# PLAN — Triển khai 4 trụ cột nâng cấp hệ thống Agent TDQ Workflow (Antigravity-first MVP)

Ngày: 2026-11-20 · Spec: ../spec/2026-11-20-1230-trien-khai-4-de-xuat-agent.md (bản 1.1, ĐÃ DUYỆT) · Lane: full
Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md
Mode thực thi: subagent — tdq_bench.py simulate thắng nhánh đội (12.3 phút so với main 20.4 phút, nhanh hơn 8.1 phút ở hệ số agent 1.5 trên 4 đợt: giao 4, leader giữ 6)
Trạng thái plan: ĐÃ DUYỆT

## Mục lục

- Phân bổ Model & Effort
- Quy tắc thi hành
- Thiết kế Trước vs Sau
- Ràng buộc toàn cục & Bản đồ Sở hữu Hợp đồng (Ownership Map)
- P1 — Cấu hình Plugin, Thang Gemini 4 & Đội hình 6+2 Agent
- P2 — Handoff JSON duy nhất, Packet V2+ đa ngôn ngữ & Shared Blackboard
- P3 — Bảo mật Hook Python, SubagentStop & Telemetry theo Role
- P4 — Vá & Biên dịch Rust Dispatcher tdq-dispatch
- P5 — Biên dịch Plugin Antigravity, Log & Kiểm định Parity
- Cụm song song
- Luật file nóng
- Definition of Done

## Phân bổ Model & Effort

> **Quyền chỉnh sửa của người dùng:** Bạn có quyền đổi `type model` hoặc `effort` cho bất kỳ pha/vai trò nào dưới đây ngay khi duyệt plan (nhắn trực tiếp cùng lệnh `"duyệt plan"`). Mọi thay đổi sẽ được cập nhật vào bảng này trước khi chạy `implement`.

| Pha | Vai trò / Tác vụ | Model đề xuất (`swarm` / `invoke_subagent`) | Effort | Ghi chú |
|---|---|---|---|---|
| `implement` | Wave 1–2 (`T1.1`–`T1.3`, `T2.1`: config, agents, skills, `tdq_team.py`) | `gemini-4-hydrogen-high` / `inherit` | `high` | Cân bằng tốc độ và độ chính xác cấu trúc Python/YAML. |
| `implement` | Wave 3–5 (`T1.4`, `T3.1`–`T3.2`, `T4.1`, `T5.1`–`T5.2`: Rust, hooks bảo mật, build AGY, tests) | `gemini-4-neon-xhigh` / `inherit` | `xhigh` | Bảo mật `command_parser.rs`, parity AGY và test đối kháng. |
| `implement` | Escalation nếu 1 task vấp lỗi biên dịch/kiểu quá `2` lần (`tdq-build-resolver`) | `gemini-3.8-flash-high` → `gemini-4-carbon-high` / `pro` | `high` | Sửa diff nhỏ nhanh bằng `3.8 Flash`, leo thang `4 Carbon` nếu kẹt sâu. |
| `qc` (`ultra`) | `tdq-qc-tester` song song (**không giới hạn số subagent** theo ủy quyền `5c`; mặc định plugin mới = `5`) | `gemini-4-neon-high` (mảng bảo mật dùng `gemini-4-carbon-high`) / `inherit` hoặc `pro` | `high` | Chia shard độc lập: Config/Agents, Packet/Blackboard, Python+Rust Security, AGY Build Parity, Smoke/Runtime. |
| `report` | Tổng hợp báo cáo `4` phần + `Archify HTML` (leader chính) | `inherit` (model phiên hiện tại) | Theo phiên | Không cần spawn subagent riêng cho pha `report`. |

## Quy tắc thi hành

- Ngôn ngữ tài liệu là tiếng Việt (`doc_lang = vi`). Mọi file mã nguồn mới giữ log timestamp mặc định ra `stderr` (`TDQ_LOG=0` tắt).
- Thực hiện Red → Green trên từng task. Không sửa `.codex/hooks.json` và không chạm tệp ngoài repo `~/.gemini/config/plugins/`.
- Giữ toàn bộ `rules/*.md` và `skills/*/SKILL.md` trong bản build AGY dưới `24,000` bytes và `qc.md` gọn trong ngân sách token.
- Sau mỗi module chạy `tdq_test.py vung-cham`; sau Rust chạy `cargo test` và `cargo build --release`.

## Thiết kế Trước vs Sau

Bản xem trước Trước/Sau đã khóa gắn với Spec v1.1 tại `docs/tdq/spec/2026-11-20-1230-trien-khai-4-de-xuat-agent-preview.html` (manifest `docs/tdq/spec/2026-11-20-1230-trien-khai-4-de-xuat-agent-preview.manifest.json`, trạng thái `current`).

| Khía cạnh | Hiện trạng (Trước) | Thiết kế mới (Sau) |
|---|---|---|
| Model, Effort & Plan | AGY ép `flash`/`pro`, mất `effort`; Plan không báo model/effort. | Mặc định `inherit`; thang `3.8 Flash → 4 Hydrogen → 4 Neon → 4 Carbon`; Plan khai báo `Model & Effort` và user đổi được khi duyệt. |
| Vai trò & `ultra` QC | `3/6` agent mồ côi; `ultra` chỉ `1` QC; `full` không kiểm độc lập. | Đủ `8` agent (`6+2`) có caller rõ; `full` kiểm nhẹ; `ultra` mặc định tối đa `5` QC song song (cấu hình trong `tdq-config.json`, hỗ trợ `unlimited`). |
| Hook AGY & Rust | Chưa có hậu kiểm thoát; `command_parser.rs` báo giả `>=` và sót `python -c`; chặn nhầm QC ghi `docs/tdq/qc/`. | Bắt `PostToolUse`/`Stop` (AGY) + `SubagentStop` (Claude); vá `>=` & shell bypass; mở quyền ghi hẹp `docs/tdq/qc/*.md` cho QC. |
| Schema, Packet & Eval | Hai `handoff-schema.json` lệch nhau; `packet` thiếu Mini-Spec và chỉ đọc `.py`; thiếu đo theo role. | Một `handoff-schema.json` + validator; Packet V2+ đa ngôn ngữ; thêm Blackboard, auto-escalation và telemetry theo `agent_role`. |

## Ràng buộc toàn cục & Bản đồ Sở hữu Hợp đồng (Ownership Map)

- Quy chuẩn kiến trúc (`docs/kien-truc.md`): `skills/` chỉ nhắc tên lệnh của `scripts/`; chỉ `tdq_state.py` ghi `docs/tdq/state.json`; `.codex/hooks.json` giữ nguyên `PreToolUse`.
- Quy chuẩn Antigravity (`agy-customizations/docs/hooks.md`): `plugins/tdq-workflow-agy/hooks.json` chỉ đăng ký `6` sự kiện gốc (`SessionStart`, `PreToolUse`, `PostToolUse`, `PreInvocation`, `PostInvocation`, `Stop`).
- Quy chuẩn ngân sách: `plugins/tdq-workflow-agy/` đạt `0` lỗi AST và `< 24,000` bytes cho mỗi `rules/*.md` và `skills/*/SKILL.md`.

| Hợp đồng / Giao diện | Định nghĩa cốt lõi | Task sở hữu | Task tiêu thụ |
|---|---|---|---|
| `TdqConfigContract` | `tdq-config.json` + `scripts/tdq_config.py` (`load_config`, `max_qc_subagents`, `model_ladder`). | `T1.1` | `T1.3`, `T1.4`, `T2.1`, `T3.1`, `T5.1`, `T5.2` |
| `AgentRoster8Contract` | `8` tệp `agents/tdq-*.md` (`6+2`) đồng nhất commit worktree, diff/SCA và digest `<= 1500`. | `T1.2`, `T1.3` | `T1.4`, `T4.1`, `T5.1`, `T5.2` |
| `HandoffAndPacketContract` | `1` `handoff-schema.json`, `validate_handoff_payload`, `parse_handoff_from_text`, Packet V2+, Blackboard. | `T2.1` | `T3.1`, `T4.1`, `T5.1`, `T5.2` |
| `SecurityAndStopContract` | Allowlist `docs/tdq/qc/*.md`, vá `>=` & shell bypass, `register_subagent_role`, `subagent_stop.py`, Rust `tdq-dispatch`. | `T3.1`, `T4.1` | `T3.2`, `T5.1`, `T5.2` |
| `AgyBundleParityContract` | `plugins/tdq-workflow-agy/` đồng bộ `8` agent `inherit` + LSP/Grep, `tdq-config.json`, `tdq-dispatch.exe`. | `T5.1` | `T5.2` |

## P1 — Cấu hình Plugin, Thang Gemini 4 & Đội hình 6+2 Agent

- [x] **T1.1** (e10m) Tạo `tdq-config.json` và `scripts/tdq_config.py` đọc cấu hình ưu tiên `env > project > plugin` — Test: `py -3 -X utf8 -m unittest tests.test_agent_upgrade_mvp.TestTdqConfig`
  - Req: `§2#1`, `§2b(M1-config-agents-skills)`, `§3c(TdqConfigContract)` · Ngoài phạm vi: `GIỮ NGUYÊN` `plugin.json` không nhét `userConfig`.
  - Chạm: `tdq-config.json`, `scripts/tdq_config.py`, `tests/test_agent_upgrade_mvp.py`
  - Cần: Không
  - Tham chiếu: `scripts/tdq_state.py`, `tools/patches/agy_manifests.py`
  - Giao tiếp: Consumes: `TDQ_MAX_QC_SUBAGENTS` env & JSON files | Produces: `load_config(cwd)`, `max_qc_subagents(cwd)`, `model_ladder(cwd)`
  - Neo & Công cụ: `Write` `tdq-config.json`, `scripts/tdq_config.py`, `tests/test_agent_upgrade_mvp.py`
  - Trước → Sau: Chưa có cấu hình plugin cho QC/model → Có `tdq-config.json` (`ultra_max_subagents=5`, `0`/`unlimited`, thang `3.8 Flash → 4 Carbon`).
  - Tiêu chí chấp nhận (EARS): KHI đặt `TDQ_MAX_QC_SUBAGENTS=unlimited` hoặc `0`, HỆ THỐNG PHẢI trả về `None` (không giới hạn), mặc định trả `5`.
  - Logic cốt lõi: Đọc hợp nhất `tdq-config.json`, `docs/tdq/config.json`, env; fail-safe về mặc định khi JSON hỏng kèm log timestamp `TDQ_LOG=0`.
  - Ca góc hiểm & Assert: JSON lỗi hoặc số âm rơi về `5` · `assert max_qc_subagents(tmp_dir) == 5`

- [x] **T1.2** (e8m) Chuẩn hóa hợp đồng commit worktree, handoff JSON, diff/SCA trên `5` agent hiện có — Test: `py -3 -X utf8 -m pytest tests/test_agent_frontmatter.py`
  - Req: `§2#1`, `§2b(M1-config-agents-skills)` · Ngoài phạm vi: `GIỮ NGUYÊN` `model: inherit` và `effort: high` ở YAML gốc.
  - Chạm: `agents/tdq-implementer.md`, `agents/tdq-build-resolver.md`, `agents/tdq-qc-tester.md`, `agents/tdq-reviewer.md`, `agents/tdq-security-reviewer.md`
  - Cần: Không
  - Tham chiếu: `skills/tdq-build/references/team-mode.md`, `tests/test_agent_frontmatter.py`
  - Giao tiếp: Consumes: `team-mode.md` worktree rules | Produces: `5` tệp agent đồng nhất hợp đồng commit, shard QC và diff/SCA
  - Neo & Công cụ: `Edit` `agents/tdq-implementer.md` (`L14-31`), `tdq-build-resolver.md` (`L29-45`), `tdq-qc-tester.md` (`L11-31`), `tdq-reviewer.md` (`L11-28`), `tdq-security-reviewer.md` (`L15-52`)
  - Trước → Sau: `implementer` tự tick plan & quên commit; `build-resolver` lệch tên payload; `security-reviewer` thiếu `git diff`/SCA → Khớp chuẩn duy nhất.
  - Tiêu chí chấp nhận (EARS): KHI chạy `test_agent_frontmatter`, HỆ THỐNG PHẢI pass đủ digest `<= 1500` và kiểm tra quy tắc commit/handoff.
  - Logic cốt lõi: Xóa rule tự tick sub-box, ép `git commit` worktree, thêm `git diff`/SCA cho security, thêm hướng dẫn shard song song cho QC.
  - Ca góc hiểm & Assert: Giữ nguyên cụm ngưỡng `1,500` ký tự để không phá `AgentDigestLimitTest` · `assert "git commit" in impl_text and "Tick Own Sub-Boxes" not in impl_text`

- [x] **T1.3** (e8m) Tạo `tdq-explorer.md`, `tdq-debugger.md` và cập nhật thang Gemini 3.8/4 + mục `Model & Effort` của Plan — Test: `py -3 -X utf8 scripts/doc_lint.py skills/tdq-conventions/references/subagent-tuning.md skills/tdq-plan/references/plan-template.md skills/tdq-plan/SKILL.md`
  - Req: `§2#1`, `§3c(PlanModelEffortContract)` · Ngoài phạm vi: `GIỮ NGUYÊN` cấu trúc cổng duyệt 1 bước của `tdq-plan/SKILL.md` và ngân sách `< 24KB`.
  - Chạm: `agents/tdq-explorer.md`, `agents/tdq-debugger.md`, `skills/tdq-conventions/references/subagent-tuning.md`, `skills/tdq-plan/references/plan-template.md`, `skills/tdq-plan/SKILL.md`
  - Cần: T1.1
  - Tham chiếu: `agents/tdq-reviewer.md`, `tdq-config.json`
  - Giao tiếp: Consumes: `TdqConfigContract` | Produces: `agents/tdq-explorer.md`, `agents/tdq-debugger.md`, thang Gemini 3.8/4 và mẫu bảng Plan `Model & Effort`
  - Neo & Công cụ: `Write` `agents/tdq-explorer.md`, `agents/tdq-debugger.md`; `Edit` `subagent-tuning.md` (`L18-65`), `plan-template.md`, `skills/tdq-plan/SKILL.md` (`L39-100`)
  - Trước → Sau: Thiếu `Explorer`/`Debugger`; `subagent-tuning` chỉ nêu Claude; Plan chưa báo model/effort → Có đủ `8` agent, thang Gemini 3.8/4 và quyền user đổi model ở Plan.
  - Tiêu chí chấp nhận (EARS): KHI trình duyệt Plan mới, HỆ THỐNG PHẢI hiển thị bảng `## Phân bổ Model & Effort` và ghi rõ quyền user đổi `type model`.
  - Logic cốt lõi: Thêm `tdq-explorer` (read-only) và `tdq-debugger` (read-only); cập nhật bảng 4 bậc `3.8 Flash → 4 Hydrogen → 4 Neon → 4 Carbon` + hậu tố `swarm`.
  - Ca góc hiểm & Assert: Giữ `skills/tdq-plan/SKILL.md` dưới `24,000` bytes · `assert len(Path("skills/tdq-plan/SKILL.md").read_bytes()) < 24000` (đang tách phần chi tiết sang `plan-template-co-che.md` để giữ trần 3,500 token)

- [x] **T1.4** (e10m) Nối caller cho `3` agent mồ côi, cập nhật `qc.md` (`full` nhẹ + `ultra` tối đa `5` QC song song) và thêm kiểm `Model & Effort` trong `doc_lint.py` — Test: `py -3 -X utf8 -m pytest tests/test_doc_lint.py`
  - Req: `§2#1`, `§3c(PlanModelEffortContract)` · Ngoài phạm vi: `GIỮ NGUYÊN` các test `doc_lint` cho plan cũ trước `2026-11-20` không bị gãy ngược.
  - Chạm: `skills/tdq-build/SKILL.md`, `skills/tdq-build/references/qc.md`, `skills/tdq-build/references/team-mode.md`, `skills/tdq-build/references/vision-test-loop.md`, `skills/tdq-lean/SKILL.md`, `scripts/doc_lint.py`
  - Cần: T1.1, T1.2, T1.3
  - Tham chiếu: `tdq-config.json`, `agents/tdq-build-resolver.md`, `agents/tdq-refactor-cleaner.md`, `agents/tdq-security-reviewer.md`
  - Giao tiếp: Consumes: `AgentRoster8Contract`, `TdqConfigContract` | Produces: Điểm gọi `8` agent trong `skills/` và kiểm định `## Phân bổ Model & Effort`
  - Neo & Công cụ: `Edit` `skills/tdq-build/SKILL.md` (`L82-159`), `qc.md` (`L31-75`), `team-mode.md` (`L81-145`), `vision-test-loop.md` (`L105-114`), `tdq-lean/SKILL.md` (`L30-45`), `scripts/doc_lint.py` (`r15_loi`, `L869`)
  - Trước → Sau: `3/6` agent mồ côi và `ultra` chỉ `1` QC → Đủ `8` agent được gọi theo sự kiện, `ultra` hỗ trợ song song theo `tdq-config.json` (mặc định `5`).
  - Tiêu chí chấp nhận (EARS): KHI chạy `test_doc_lint` và kiểm `qc.md`, HỆ THỐNG PHẢI giữ `qc.md <= 3,500` tokens và phát hiện thiếu `## Phân bổ Model & Effort` ở plan mới.
  - Logic cốt lõi: Thêm nhánh gọi `tdq-build-resolver` sau `2` lỗi, `tdq-refactor-cleaner` sau wave/`tdq-lean`, `tdq-security-reviewer` ở file nhạy cảm, chuẩn hóa `vision-test-loop` dùng `tdq-qc-tester`.
  - Ca góc hiểm & Assert: Không làm vỡ fixture plan cũ trong `tests/test_doc_lint.py` · `assert "tdq-build-resolver" in team_md and "tdq-security-reviewer" in build_md`

## P2 — Handoff JSON duy nhất, Packet V2+ đa ngôn ngữ & Shared Blackboard

- [x] **T2.1** (e14m) Hợp nhất `1` `handoff-schema.json`, nâng `tdq_team.py packet` (Mini-Spec + đa ngôn ngữ) và thêm `validate-handoff` + `blackboard` — Test: `py -3 -X utf8 -m unittest tests.test_team_packet_v2`
  - Req: `§2#2`, `§2b(M2-handoff-packet-blackboard)`, `§3c(HandoffContract, PacketV2Contract, BlackboardContract)` · Ngoài phạm vi: `GIỮ NGUYÊN` các lệnh `assign`, `wave`, `open`, `check`, `merge` tương thích ngược.
  - Chạm: `skills/tdq-conventions/references/handoff-schema.json`, `scripts/tdq_team.py`, `tests/test_team_packet_v2.py`
  - Cần: T1.1
  - Tham chiếu: `scripts/tdq_config.py`, `skills/tdq-build/references/team-mode.md`
  - Giao tiếp: Consumes: `TdqConfigContract` | Produces: `validate_handoff_payload()`, `parse_handoff_from_text()`, `blackboard_record()`, `blackboard_read()`, `suggest_escalation()`, Packet V2+ đa ngôn ngữ
  - Neo & Công cụ: `Edit` `handoff-schema.json` (`L1-50`), `scripts/tdq_team.py` (`_render_target_spans` `L2093`, `_build_packet_payload` `L2206`, `lenh_packet` `L2269`, `main` `L2325`), `tests/test_team_packet_v2.py`
  - Trước → Sau: Hai schema lệch, Packet thiếu Mini-Spec & chỉ đọc `.py`, thiếu Blackboard → `1` schema chuẩn, Packet đủ Mini-Spec + `.ts`/`.rs`/`.ps1`, có Blackboard + auto-escalation.
  - Tiêu chí chấp nhận (EARS): KHI chạy `tdq_team.py packet` trên task có `.rs`/`.ts` và Mini-Spec, HỆ THỐNG PHẢI xuất đủ `Req:`, `GIỮ NGUYÊN:`, `EARS`, `RANH GIỚI:`, `TỰ KIỂM:` và symbol spans.
  - Logic cốt lõi: Hợp nhất JSON schema; bổ sung regex cấu trúc cho `.ts`/`.tsx`/`.js`/`.rs`/`.ps1`; lưu Blackboard ở `.tdq-runtime/blackboard/<slug>.json`; gợi ý leo thang sau `2` lỗi.
  - Ca góc hiểm & Assert: Payload vượt `1,500` ký tự hoặc thiếu trường bắt buộc trả `ok=False` · `assert validate_handoff_payload(bad_payload)[0] is False`

## P3 — Bảo mật Hook Python, SubagentStop & Telemetry theo Role

- [x] **T3.1** (e14m) Vá `bash_gate.py`, mở allowlist hẹp `docs/tdq/qc/*.md` trong `edit_gate.py`, tạo `subagent_stop.py` và nối `hooks/hooks.json` — Test: `py -3 -X utf8 -m unittest tests.test_agent_upgrade_mvp.TestPythonHooksSecurity`
  - Req: `§2#3`, `§2b(M3-python-hooks-telemetry)`, `§3c(SecurityAndLifecycleContract)` · Ngoài phạm vi: `GIỮ NGUYÊN` `.codex/hooks.json` chỉ có `PreToolUse`.
  - Chạm: `hooks/scripts/_common.py`, `hooks/scripts/edit_gate.py`, `hooks/scripts/bash_gate.py`, `hooks/scripts/subagent_stop.py`, `hooks/hooks.json`
  - Cần: T2.1
  - Tham chiếu: `scripts/tdq_team.py`, `scripts/tdq_config.py`
  - Giao tiếp: Consumes: `HandoffAndPacketContract` | Produces: `is_qc_report_target()`, `append_agent_telemetry()`, `hooks/scripts/subagent_stop.py`, đăng ký role trong `hooks.json`
  - Neo & Công cụ: `Write` `hooks/scripts/subagent_stop.py`; `Edit` `_common.py` (`L818-872`), `edit_gate.py` (`L78-90`), `bash_gate.py` (`L130-158`), `hooks/hooks.json` (`L100-136`)
  - Trước → Sau: `edit_gate` chặn `tdq-qc-tester` ghi `docs/tdq/qc/`; `bash_gate` lọt `python -c`/`node -e`; thiếu `subagent_stop.py` → Allowlist hẹp QC, bịt shell bypass, có hậu kiểm `SubagentStop` + telemetry role.
  - Tiêu chí chấp nhận (EARS): KHI `tdq-qc-tester` ghi `docs/tdq/qc/a.md` thì cho phép; KHI ghi `docs/tdq/qc/../../a.py` hoặc chạy `python -c "...write_text..."` thì HỆ THỐNG PHẢI chặn `READONLY`.
  - Logic cốt lõi: Chuẩn hóa `realpath` chống path traversal cho `docs/tdq/qc/*.md`; lọc bỏ `>=`/`<=` trước kiểm `>`; `subagent_stop.py` kiểm worktree dirty, validate handoff, ghi telemetry + Blackboard.
  - Ca góc hiểm & Assert: Lệnh chứa `>=` không bị chặn nhầm · `assert _is_shell_write("py -3 -c \"assert x >= 1\"") is False and _is_shell_write("py -3 -c \"Path('a').write_text('x')\"") is True`
  - Tiến độ inline: đã cập nhật `_common`/`bash_gate`/`edit_gate`/`subagent_stop`/`stop_gate`/`hooks.json`, đang vá 2 kiểm thử hồi quy `edit_gate` anchor và `ProtocolTest`.

- [x] **T3.2** (e10m) Bổ sung tổng hợp telemetry theo `agent_role` vào `scripts/tdq_timing.py` và `scripts/token_audit.py` — Test: `py -3 -X utf8 -m pytest tests/test_timing.py tests/test_agent_upgrade_mvp.py -k "timing or RoleTelemetry"`
  - Req: `§2#3`, `§2b(M3-python-hooks-telemetry)` · Ngoài phạm vi: `GIỮ NGUYÊN` bảng Timing V2 (`model_giay=null`) và ngữ nghĩa carry-cost của `token_audit.py`.
  - Chạm: `scripts/tdq_timing.py`, `scripts/token_audit.py`
  - Cần: T3.1
  - Tham chiếu: `hooks/scripts/_common.py`, `hooks/scripts/subagent_stop.py`
  - Giao tiếp: Consumes: `docs/tdq/.tdq-agent-telemetry.jsonl` | Produces: `role_summary(project, slug)` trong `tdq_timing.py` và bảng phân bổ theo role trong `token_audit.py`
  - Neo & Công cụ: `Edit` `scripts/tdq_timing.py` (`bang_markdown` `L265`, `main` `L356`), `scripts/token_audit.py` (`L53-65`, `main` `L874`)
  - Trước → Sau: Chỉ tổng hợp cả phiên → Hiển thị thêm số lượt chạy, `first_pass_rate`, số retry và thời gian trung bình theo từng `agent_role` khi có dữ liệu.
  - Tiêu chí chấp nhận (EARS): KHI có bản ghi telemetry của `tdq-implementer` và `tdq-qc-tester`, HỆ THỐNG PHẢI in bảng đúng theo role; KHI rỗng PHẢI ghi rõ chưa có dữ liệu.
  - Logic cốt lõi: Đọc JSONL an toàn (bỏ qua dòng hỏng có log stderr), nhóm theo `agent_role`, tuyệt đối không bịa số mặc định.
  - Ca góc hiểm & Assert: File telemetry rỗng không làm crash `tdq_timing.py show` · `assert summary == []`

## P4 — Vá & Biên dịch Rust Dispatcher tdq-dispatch

- [x] **T4.1** (e16m) Vá `command_parser.rs`, mở quyền ghi hẹp QC & `8` role trong `pre_tool_use.rs`, bắt `PostToolUse` role và `Stop`/`SubagentStop` rồi chạy `cargo test` + `cargo build --release` — Test: `cargo test --manifest-path hooks/rust/tdq-dispatch/Cargo.toml`
  - Req: `§2#4`, `§2b(M4-rust-dispatcher)`, `§3c(SecurityAndLifecycleContract)` · Ngoài phạm vi: `GIỮ NGUYÊN` định dạng JSON quyết định và tốc độ hot-path Rust `< 5 ms`.
  - Chạm: `hooks/rust/tdq-dispatch/src/command_parser.rs`, `hooks/rust/tdq-dispatch/src/events/pre_tool_use.rs`, `hooks/rust/tdq-dispatch/src/events/post_tool_use.rs`, `hooks/rust/tdq-dispatch/src/events/stop_streak.rs`, `hooks/rust/tdq-dispatch/src/main.rs`
  - Cần: T2.1
  - Tham chiếu: `hooks/scripts/_common.py`, `hooks/scripts/edit_gate.py`, `hooks/scripts/bash_gate.py`
  - Giao tiếp: Consumes: `HookPayload` | Produces: Binary `target/release/tdq-dispatch.exe` và unit tests Rust xanh `100%`
  - Neo & Công cụ: `Edit` `command_parser.rs` (`L90-134`), `pre_tool_use.rs` (`L22-62`, `L240-325`), `post_tool_use.rs` (`L64-113`), `stop_streak.rs` (`L61-80`), `main.rs` (`L187-201`)
  - Trước → Sau: `command_parser.rs` báo giả `>=` và sót `python -c`/`node -e`; thiếu `tdq-explorer`/`tdq-debugger`; không đăng ký role ở `PostToolUse`; thiếu `SubagentStop` → Đồng nhất hoàn toàn với Python hooks.
  - Tiêu chí chấp nhận (EARS): KHI chạy `cargo test` và `cargo build --release`, HỆ THỐNG PHẢI pass `100%` unit test Rust (gồm ca `>=`, `python -c`, `docs/tdq/qc/*.md`, traversal, `SubagentStop`).
  - Logic cốt lõi: Sửa `part_stdout_targets` bỏ qua `>=`/`<=`/`=>`/`->`; thêm pattern shell mutator cho `python -c`/`node -e`/`git -C`; lưu `sessions.json` tại `Pre/PostToolUse` (`invoke_subagent|swarm`); ủy quyền `SubagentStop` và `Stop` của subagent sang `subagent_stop.py`.
  - Ca góc hiểm & Assert: `is_shell_mutator("py -3 -c 'assert x >= 10'") == false` và `is_shell_mutator("node -e \"fs.writeFileSync('a','b')\"") == true`
  - Tiến độ inline: đã cập nhật `command_parser.rs`, `storage.rs`, `pre_tool_use.rs`, đang nối `post_tool_use.rs`/`stop_streak.rs`/`main.rs`.

## P5 — Biên dịch Plugin Antigravity, Log & Kiểm định Parity

Log: BẮT BUỘC — `scripts/tdq_config.py`, `hooks/scripts/subagent_stop.py`, các hàm mới trong `scripts/tdq_team.py`, `scripts/tdq_timing.py` và Rust `tdq-dispatch` đều mặc định ghi log kèm ISO timestamp ra `stderr` và tắt sạch bằng `TDQ_LOG=0`.

- [x] **T5.1** (e12m) Cập nhật trình biên dịch `tools/patches/*` & `tools/build_agy_plugin.py` (`8` agent `inherit` + LSP/Grep, `tdq-config.json`, `PostToolUse` matcher, `1` schema) và rebuild `plugins/tdq-workflow-agy/` — Test: `py -3 -X utf8 tools/build_agy_plugin.py --upstream .`
  - Req: `§2#5`, `§2b(M5-agy-plugin-compiler)` · Ngoài phạm vi: `GIỮ NGUYÊN` plugin ngoài repo `~/.gemini/config/plugins/` không bị ghi đè.
  - Chạm: `tools/patches/skills_and_agents.py`, `tools/patches/agy_manifests.py`, `tools/patches/agy_dispatch.py`, `tools/patches/agy_hooks.py`, `tools/build_agy_plugin.py`, `docs/tdq/token-budget.json`
  - Cần: T1.4, T3.1, T3.2, T4.1
  - Dùng: `agy-customizations / antigravity-guide`
    - Để: Đối chiếu `6` sự kiện lifecycle hợp lệ của Antigravity 2.0 trước khi sinh `plugins/tdq-workflow-agy/hooks.json`.
    - Ra: `plugins/tdq-workflow-agy/hooks.json` có matcher `PostToolUse` cho `invoke_subagent|swarm|define_subagent` và chỉ dùng `6` sự kiện hợp lệ.
    - Kiểm: `py -3 -X utf8 -c "import json, pathlib; h = json.loads(pathlib.Path('plugins/tdq-workflow-agy/hooks.json').read_text(encoding='utf-8')); evs = {k for v in h.values() for k in v if k != 'enabled'}; assert evs.issubset({'SessionStart','PreToolUse','PostToolUse','PreInvocation','PostInvocation','Stop'}) and any('invoke_subagent' in g.get('matcher','') for g in h['tdq-post-tool-observe']['PostToolUse']); print('HOOKS_OK', sorted(evs))"`
    - Không dùng cho: Không sửa `.codex/hooks.json` hay ghi đè plugin ngoài repo `~/.gemini/`.
  - Tham chiếu: `tdq-config.json`, `skills/tdq-conventions/references/handoff-schema.json`, `hooks/scripts/subagent_stop.py`
  - Giao tiếp: Consumes: `M1`–`M4` + Windows `target/release/tdq-dispatch.exe` | Produces: `plugins/tdq-workflow-agy/` sạch AST và `< 24KB`
  - Neo & Công cụ: `Edit` `skills_and_agents.py` (`L42-169`), `agy_manifests.py` (`L46-149`), `agy_hooks.py` (`L1325-1380`), `build_agy_plugin.py` (`L190-240`); chạy `token_budget.py` và `build_agy_plugin.py --upstream .`
  - Trước → Sau: Bản AGY ép `flash`/`pro`, thiếu LSP/Grep, lệch schema, thiếu `tdq-config.json` → Bản AGY đồng bộ `100%` `8` agent `inherit`, đủ tool, `1` schema, nhị phân Windows mới.
  - Tiêu chí chấp nhận (EARS): KHI chạy `tools/build_agy_plugin.py --upstream .`, HỆ THỐNG PHẢI trả JSON `"status": "OK"` với `0` lỗi AST và `0` vi phạm `24KB`.
  - Logic cốt lõi: Xóa khối ghi đè `handoff_schema` lệch trong `transform_skills`; thêm `tdq-explorer` và `tdq-debugger` vào `AGENT_FRONTMATTERS` (`model: inherit` + LSP/Grep); gọi `register_subagent_role` trong `SUBAGENT_DISPATCH_GATE_PY`; chép `tdq-config.json` vào stage.
  - Ca góc hiểm & Assert: Giữ nguyên magic-byte hợp lệ cho `linux`/`darwin` prebuilt · `assert json.loads(out)["status"] == "OK"`

- [ ] **T5.2** (e14m) Mở rộng `tests/test_agent_frontmatter.py` (parity đủ `8` agent + schema) và hoàn thiện `tests/test_agent_upgrade_mvp.py` (config, shell bypass, QC allowlist, `subagent_stop`, telemetry, Plan `Model & Effort`, smoke/runtime) — Test: `py -3 -X utf8 -m pytest tests/test_agent_frontmatter.py tests/test_agent_upgrade_mvp.py tests/test_team_packet_v2.py tests/test_codex_hooks_json.py`
  - Req: `§2#6`, `§2b(M6-tests-and-verification)` · Ngoài phạm vi: `GIỮ NGUYÊN` toàn bộ các test hiện hữu không bị xóa hay làm yếu.
  - Chạm: `tests/test_agent_frontmatter.py`, `tests/test_agent_upgrade_mvp.py`, `tests/test_build_portable.py`, `tests/test_agy_plugin_validate.py`
  - Cần: T5.1
  - Tham chiếu: `tdq-config.json`, `plugins/tdq-workflow-agy/plugin.json`, `plugins/tdq-workflow-agy/hooks.json`
  - Giao tiếp: Consumes: `AgyBundleParityContract` | Produces: Bộ kiểm thử tự động đầy đủ + smoke/runtime kiểm `tdq-dispatch.exe`
  - Neo & Công cụ: `Edit` `tests/test_agent_frontmatter.py` (`L40-103`), `tests/test_agent_upgrade_mvp.py`; chạy `tdq_test.py vung-cham`
  - Trước → Sau: Chỉ kiểm `3/6` agent ở root → Kiểm đủ `8/8` agent gốc + parity `plugins/tdq-workflow-agy/`, `1` schema, shell bypass, `>=`, scoped QC, telemetry và runtime `tdq-dispatch.exe`.
  - Tiêu chí chấp nhận (EARS): KHI chạy bộ test mới cùng `test_codex_hooks_json`, HỆ THỐNG PHẢI pass `100%` với `0` fail và `0` skip ngoài dự kiến.
  - Logic cốt lõi: Thêm test parity SHA `handoff-schema.json`, test đủ `8` agent AGY (`model: inherit`, LSP/Grep), test runtime gọi subprocess `plugins/tdq-workflow-agy/bin/tdq-dispatch.exe` với stdin payload thật (timeout `< 30s`).
  - Ca góc hiểm & Assert: Test runtime đọc quyết định JSON thật từ `tdq-dispatch.exe` · `assert res.returncode == 0 and "READONLY" in res.stdout`

## Cụm song song

- Wave 1 (song song `2` luồng): `T1.1`, `T1.2` (vùng file hoàn toàn rời nhau).
- Wave 2 (song song `2` luồng): `T1.3`, `T2.1` (cùng đọc `T1.1`, sửa hai vùng file tách biệt).
- Wave 3 (song song `3` luồng): `T1.4`, `T3.1`, `T4.1` (Skills/doc_lint, Python hooks, và Rust dispatcher không chung file nào).
- Wave 4 (tuần tự `1` luồng): `T3.2` (tiêu thụ telemetry từ `T3.1`).
- Wave 5 (tuần tự `1` luồng): `T5.1` (biên dịch hợp nhất `plugins/tdq-workflow-agy/` sau khi `M1`–`M4` xong).
- Wave 6 (tuần tự `1` luồng): `T5.2` (kiểm chứng parity tổng thể, smoke & runtime).

## Luật file nóng

- `tests/test_agent_upgrade_mvp.py` được tạo ở `T1.1` và mở rộng kiểm chứng tổng hợp ở `T5.2` (cách nhau `4` wave nên không xung đột).
- `docs/tdq/token-budget.json` chỉ được relock duy nhất ở `T5.1` sau khi toàn bộ `skills/` và `agents/` đã hoàn thiện.
- `plugins/tdq-workflow-agy/` chỉ được biên dịch duy nhất ở `T5.1` qua `tools/build_agy_plugin.py --upstream .`; tuyệt đối không sửa tay file đã biên dịch trong `plugins/tdq-workflow-agy/`.

## Definition of Done

- [ ] `Q1` Cấu hình `tdq-config.json`, đội hình `8` agent (`6+2`), thang Gemini 3.8/4 và mục `## Phân bổ Model & Effort` hoạt động chuẩn — Lệnh kiểm: `py -3 -X utf8 -m pytest tests/test_agent_frontmatter.py tests/test_doc_lint.py -q; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }; py -3 -X utf8 -m unittest tests.test_agent_upgrade_mvp.TestTdqConfig`
- [ ] `Q2` Một `handoff-schema.json` khớp SHA root/AGY, Packet V2+ đa ngôn ngữ, `validate-handoff` và Shared Blackboard pass — Lệnh kiểm: `py -3 -X utf8 -m unittest tests.test_team_packet_v2 tests.test_agent_upgrade_mvp.TestHandoffAndBlackboard`
- [ ] `Q3` Bảo mật Python + Rust (`>=` không báo giả, chặn `python -c`/`node -e`/`git -C`), quyền ghi hẹp `docs/tdq/qc/*.md` và `subagent_stop.py` pass — Lệnh kiểm: `cargo test --manifest-path hooks/rust/tdq-dispatch/Cargo.toml; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }; py -3 -X utf8 -m unittest tests.test_agent_upgrade_mvp.TestPythonHooksSecurity`
- [ ] `Q4` Telemetry theo `agent_role` và build `plugins/tdq-workflow-agy/` (`status=OK`, `8` agent `inherit` + LSP/Grep, `6` sự kiện AGY, `< 24KB`, `0` lỗi AST) pass — Lệnh kiểm: `py -3 -X utf8 tools/build_agy_plugin.py --upstream .; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }; py -3 -X utf8 -m pytest tests/test_timing.py tests/test_agent_upgrade_mvp.py -k "timing or RoleTelemetry or AgyBundleParity"`
- [ ] `Q5` Trọn bộ hồi quy hệ thống (`tdq_test.py tron-bo`), `TestHooksJsonGocRepo`, smoke CLI và runtime `tdq-dispatch.exe` đều xanh dưới `120s` — Lệnh kiểm: `py -3 -X utf8 scripts/tdq_test.py tron-bo --workers 1 --fresh --reuse off; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }; py -3 -X utf8 -m pytest tests/test_codex_hooks_json.py tests/test_agent_upgrade_mvp.py -k "SmokeAndRuntime or TestHooksJsonGocRepo"`
- [ ] `Q6` Kiểm định độc lập song song `ultra` (`tdq-qc-tester` nhiều shard), `doc_lint.py` + `--pair` đạt `0` lỗi, Archify HTML báo cáo `current` + Tailscale HTTP `200`, `0` sửa đổi ngoài repo — Lệnh kiểm: `py -3 -X utf8 scripts/doc_lint.py docs/tdq/spec/2026-11-20-1230-trien-khai-4-de-xuat-agent.md docs/tdq/plan/2026-11-20-1230-trien-khai-4-de-xuat-agent.md docs/tdq/qc/2026-11-20-1230-trien-khai-4-de-xuat-agent.md docs/tdq/reports/2026-11-20-1230-trien-khai-4-de-xuat-agent.md; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }; py -3 -X utf8 scripts/doc_lint.py --pair docs/tdq/spec/2026-11-20-1230-trien-khai-4-de-xuat-agent.md docs/tdq/plan/2026-11-20-1230-trien-khai-4-de-xuat-agent.md; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }; py -3 -X utf8 scripts/tdq_archify.py verify --document docs/tdq/reports/2026-11-20-1230-trien-khai-4-de-xuat-agent.md --manifest docs/tdq/reports/2026-11-20-1230-trien-khai-4-de-xuat-agent.manifest.json`
