# Brief: Triển khai 4 đề xuất nâng cấp hệ thống Agent TDQ Workflow

Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

## Nguyên văn

> commit và mở request handle cả 4 đề xuất, và tôi muốn liệu có thể để agy tự phân bổ model / effort của các subagent không?

### Đọc hiểu ban đầu

- **Mục tiêu:** Triển khai trọn bộ `4` trụ cột nâng cấp (`14` hạn chế, lộ trình `P0`–`P3`) đã chẩn đoán tại `docs/tdq/reports/2026-11-20-1056-phan-tich-nang-cap-agent.md`, ưu tiên vận hành ổn định trên Google Antigravity 2.0 và giữ tương thích Claude Code, Codex, OpenCode.
- **Phạm vi dự kiến:**
  - Trụ cột 1: Nối caller cho `3` agent mồ côi (`tdq-build-resolver`, `tdq-refactor-cleaner`, `tdq-security-reviewer`), bổ sung `tdq-explorer`/`tdq-debugger`, mở QC nhẹ mức `full` và sửa hợp đồng commit worktree của `tdq-implementer`.
  - Trụ cột 2: Điều chỉnh `tools/patches/skills_and_agents.py`, quyền chỉ đọc có điều kiện cho QC, vá `command_parser.rs` và `bash_gate.py`, thêm hậu kiểm kết thúc subagent Rust+Python, gọi `register_subagent_role` lúc dispatch và kiểm parity `tests/`.
  - Trụ cột 3 & 4: Hợp nhất `1` `handoff-schema.json` + parser, nâng cấp `scripts/tdq_team.py packet` (Mini-Spec, đa ngôn ngữ), thêm `.tdq-runtime/blackboard/<slug>.json`, auto-escalation và telemetry/eval từng role.
- **Câu hỏi kỹ thuật kèm theo:** Kiểm chứng khả năng Antigravity 2.0 tự phân bổ `model` (`inherit` / `flash_lite` / `flash` / `pro` / `swarm`) và giới hạn không có tham số `effort` trên `invoke_subagent`/`swarm`/frontmatter AGY.
- **Điểm cần làm rõ sau khi chọn pipeline:** Chốt chiến lược phân bổ `model` AGY, phạm vi triển khai gộp hay tách đợt `P0`–`P3`, phạm vi quyền ghi `docs/tdq/qc/` của `tdq-qc-tester`, quyền đồng bộ plugin ngoài repo và mức QC.

## Hiểu & kiến thức

### Năng lực dùng được

Phân vân → DÙNG. Kiểm kê ngày 2026-11-20: `42` skill trên đĩa (`23` giữ + `19` ẩn theo `skill_inventory.py --loc "agent hook rust subagent handoff packet"`), cộng các skill built-in trong context.

| Skill | Nguồn | Phán quyết | Dùng ở đâu / Lý do loại |
|---|---|---|---|
| tdq-intake / tdq-spec / tdq-plan / tdq-build / tdq-conventions | plugin:tdq-workflow | NỀN | Vận hành trọn chuỗi pipeline deep, cổng duyệt, QC và workinglog |
| tdq-setup / tdq-status / tdq-lean | plugin:tdq-workflow | NỀN | Kiểm định tầng tìm kiếm LSP/Graphify và soát mã thừa trong pha implement |
| agy-customizations / antigravity-guide | built-in | DÙNG | Đối chiếu chính xác 6 lifecycle hook gốc của Antigravity 2.0 (`hooks.md`, `plugins.md`) |
| Đã xét 37 skill khác (google-antigravity-sdk, cdesktop, gemini-api-*, tdq-browser-*, built-in) | user/plugin/built-in | KHÔNG | khác lĩnh vực |

### Khảo sát mã nguồn 3 chiều (Triangulation) & Phát hiện kỹ thuật trọng yếu

Đã chạy Python LSP (`start_lsp`, `find_symbol`, `find_references`), `graphify query`, `graphify god-nodes`, `rg` diện rộng và kiểm tra công cụ biên dịch Rust (`cargo 1.99.0`, `rustc 1.99.0` sẵn sàng trên Windows):

| Vùng file chạm | Phát hiện qua lớp nào (Grep/LSP/Graphify) | Tác động & quan hệ |
|---|---|---|
| `agents/tdq-*.md` & `skills/tdq-*/` | Grep + đọc trực tiếp (`subagent-tuning.md`, `team-mode.md`, `qc.md`, `vision-test-loop.md`) | Bổ sung `tdq-explorer.md`, `tdq-debugger.md`, nối caller cho `3` agent mồ côi, sửa hợp đồng commit worktree và xóa rule tự tick plan. |
| `tools/patches/skills_and_agents.py`, `agy_manifests.py`, `agy_hooks.py`, `tools/build_agy_plugin.py` | LSP (`find_references` `AGENT_FRONTMATTERS`) + đọc trực tiếp | Giữ `model: inherit` + khôi phục `grep_search`/`find_by_name`/LSP tools; mở `PostToolUse` matcher `invoke_subagent\|swarm\|define_subagent` trong `agy_manifests.py`; kiểm tra giới hạn `24KB` cho `rules/*.md` và `skills/*/SKILL.md`. |
| `hooks/hooks.json`, `hooks/scripts/{_common.py,edit_gate.py,bash_gate.py,stop_gate.py,subagent_stop.py}` | LSP (`find_references` `register_subagent_role`) + Grep (`test_codex_hooks_json.py`) | Gọi `register_subagent_role` tại Pre/Post dispatch; thêm `subagent_stop.py` dùng chung; mở quyền ghi hẹp `docs/tdq/qc/` cho `tdq-qc-tester`; giữ nguyên `.codex/hooks.json` chỉ có `PreToolUse` (`TestHooksJsonGocRepo`). |
| `hooks/rust/tdq-dispatch/src/{main.rs,command_parser.rs,events/pre_tool_use.rs,events/post_tool_use.rs,events/stop_streak.rs}` | Graphify (`HookPayload` god-node `29` edges) + đọc trực tiếp | Vá `command_parser.rs` (phân biệt `>=` với `>`, chặn `python -c`/`node -e`/`git -C`); cho phép `tdq-qc-tester` ghi `docs/tdq/qc/`; thêm nhánh `SubagentStop` + ghi role & hậu kiểm trên AGY `PostToolUse`/`Stop`; build lại `tdq-dispatch.exe` cho Windows. |
| `skills/tdq-conventions/references/handoff-schema.json`, `scripts/tdq_team.py`, `scripts/tdq_timing.py`, `scripts/token_audit.py` | LSP (`find_references` `_build_packet_payload`) + Graphify (`tdq_timing.py`, `tdq_team.py`) | Hợp nhất `1` `handoff-schema.json` + parser; nâng `_build_packet_payload` & `_render_target_spans` (Mini-Spec + đa ngôn ngữ); thêm `.tdq-runtime/blackboard/<slug>.json`; ghi telemetry theo `agent_role`. |
| `.codex-plugin/plugin.json`, `.opencode/plugins/tdq-workflow.js`, `tests/test_agent_frontmatter.py` | Grep + đọc trực tiếp (`tests/test_codex_hooks_json.py`) | Mở rộng `test_agent_frontmatter.py` kiểm toàn bộ `8` agent + parity AGY + schema + shell bypass; bổ sung lớp đọc danh mục `agents/` an toàn cho OpenCode/Codex mà không phá `TestHooksJsonGocRepo`. |

**Phát hiện quan trọng từ tài liệu Antigravity 2.0 (`agy-customizations/docs/hooks.md`):**
- Antigravity 2.0 chỉ có `6` lifecycle event gốc: `SessionStart`, `PreToolUse`, `PostToolUse`, `PreInvocation`, `PostInvocation`, `Stop` — **không có tên sự kiện `SubagentStop` riêng**.
- Thiết kế đúng cho Antigravity 2.0 là: ghi `register_subagent_role` và start telemetry tại `PreToolUse`/`PostToolUse` (`invoke_subagent|swarm|define_subagent`), đồng thời chạy bộ hậu kiểm subagent thống nhất tại **`Stop` (khi phiên có `role_opt`) + `PostToolUse` trên `invoke_subagent|swarm`**, trong khi Claude Code dùng sự kiện gốc `SubagentStop` gọi chung một hàm kiểm tra.
- Không cần gọi thêm research ngoài vì `docs/tdq/research/2026-11-20-1056-phan-tich-nang-cap-agent.md` và tài liệu Antigravity nội bộ đã phủ đủ cơ sở thiết kế.
- Đã gọi `swarm(action="models", all=True)` trực tiếp trên Antigravity 2.0 và ghi nhận bộ định danh model+effort thực tế: `gemini-3.8-flash-{low,medium,high}`, `gemini-4-hydrogen-{low,medium,high,xhigh}`, `gemini-4-neon-{low,medium,high,xhigh}`, `gemini-4-carbon-{low,medium,high}` (trong khi `invoke_subagent` dùng `inherit | flash_lite | flash | pro`).

### Phạm vi đã chốt

- Mặt CHỌN: Triển khai trọn bộ `4` trụ cột nâng cấp (`P0`–`P3`) theo hướng **MVP ưu tiên Google Antigravity 2.0** trong request này, kèm: (1) thang phân bổ `model`/`effort` động theo `Gemini 3.8 Flash → 4 Hydrogen → 4 Neon → 4 Carbon`, (2) nâng mức `ultra` QC từ `1` lên **tối đa `5` subagent QC song song mặc định** và cho phép cấu hình trong plugin (`tdq-config.json`, hỗ trợ `0`/`unlimited`), (3) mở quyền ghi hẹp `docs/tdq/qc/<slug>.md` cho `tdq-qc-tester` + kiểm nhẹ ở `full`, (4) bổ sung mục khai báo `Model & Effort` bắt buộc trong Plan cho `implement`, `qc` và `report` (nếu có).
- Mặt LOẠI: Chưa xây lại adapter runtime sâu cho Codex/OpenCode ở MVP này (chỉ giữ tương thích không gãy); không tự ghi đè plugin ngoài repo `~/.gemini/config/plugins/tdq-workflow-agy`; không tạo binary Linux/macOS giả (chỉ build thật `tdq-dispatch.exe` trên Windows và giữ bản prebuilt đa OS hợp lệ).
- Bối cảnh: Kho `TDQ-Workflow-Antigravity v0.102.0` trên Windows (`Python 3`, `cargo 1.99.0`, `rustc 1.99.0`), kiểm thử toàn bộ bằng `tdq_test.py` (`4525` tests gốc + test mới) và `cargo test`.
- Mức đầu tư suy ra: đầy đủ (MVP hoàn chỉnh, chạy thật và kiểm chứng độc lập mức `ultra` với QC song song không giới hạn cho chính request này).

### Quyết định đã chốt

- **Chiến lược phân bổ `model` & `effort` (`1a` mở rộng Gemini 4):** Trả toàn bộ `AGENT_FRONTMATTERS` về `model: inherit` (bỏ ghim cứng `flash`/`pro`). Cập nhật `subagent-tuning.md` và `tdq-config.json` theo thang 4 bậc: `Tier 1: Gemini 3.8 Flash` (`flash_lite`/`flash`), `Tier 2: Gemini 4 Hydrogen` (`inherit` chuẩn), `Tier 3: Gemini 4 Neon` (`inherit`/`pro` suy luận sâu), `Tier 4: Gemini 4 Carbon` (`pro` bảo mật/leo thang ca khó), kèm cách chọn hậu tố `-low`/`-medium`/`-high`/`-xhigh` khi chạy `swarm` và kế thừa `inherit` khi gọi `invoke_subagent`.
- **Phạm vi Antigravity-first MVP (`2a`):** Hoàn thiện toàn bộ `4` trụ cột cho Antigravity 2.0 + giữ tương thích sạch Claude Code (`hooks/hooks.json` có `SubagentStop`), không phá `.codex/hooks.json` (`TestHooksJsonGocRepo`) hay `.opencode/`.
- **Quyền `tdq-qc-tester` & `ultra` QC song song (`3a` + `5c`):** Mở quyền ghi hẹp duy nhất vào `docs/tdq/qc/<slug>.md` trong cả Python `edit_gate.py` và Rust `pre_tool_use.rs`. Nâng `ultra` QC hỗ trợ chạy song song nhiều `tdq-qc-tester` (mặc định tối đa `5`, cấu hình tại `tdq-config.json` / `docs/tdq/config.json` / `TDQ_MAX_QC_SUBAGENTS`, đặt `0` hoặc `unlimited` để không giới hạn). Bật thêm bước kiểm đối chứng gọn ở mức `full`.
- **Khai báo `Model & Effort` trong Plan:** Bổ sung khối `## Phân bổ Model & Effort` vào `plan-template.md`, `tdq-plan/SKILL.md` và kiểm soát trong `doc_lint.py`/`tdq_plan_scaffold.py` cho `implement`, `qc` và `report` (nếu có).
- **Đồng bộ bản build plugin (`4a`):** Chạy `cargo build --release` và `tools/build_agy_plugin.py --upstream .` cập nhật `plugins/tdq-workflow-agy/` trong repo; không đụng `~/.gemini/config/plugins/tdq-workflow-agy`.
- **Mức QC cho request này (`5c`):** `muc_qc = ultra` (đã ghi vào state), được người dùng cho phép dùng không giới hạn subagent QC song song để kiểm độc lập từng mảng.

### Lộ trình

| Bước/phase | Chạy? | Vì sao |
|---|---|---|
| Analyze & Kiểm chứng nền | CÓ | Đã kiểm kê `skill_inventory`, khảo sát 3 chiều LSP/Graphify/Grep, xác nhận `6` hook AGY thật và bộ model `swarm` Gemini 3.8/4. |
| Spec & Archify Preview | CÓ | Chốt hợp đồng `6` module cốt lõi (`M1`–`M6`), thang model Gemini 4, `tdq-config.json`, `SubagentStop`/AGY hooks, Plan Model/Effort và `Q1`–`Q6`. |
| Plan (có bảng Model & Effort) | CÓ | Lập Plan V2+ chia wave song song/tuần tự cho `M1`–`M6`, khai báo rõ `Model & Effort` cho `implement`, `qc` và `report`. |
| Implement | CÓ | Triển khai lần lượt theo TDD Red→Green trên Python, Rust (`cargo test` + `cargo build --release`), Markdown agents/skills và rebuild `plugins/tdq-workflow-agy/`. |
| QC mức ultra (QC song song) | CÓ | Chạy trọn bộ `tdq_test.py tron-bo`, `cargo test`, smoke/runtime hooks, và fan-out nhiều `tdq-qc-tester` độc lập kiểm chứng từng mảng (`Q1`–`Q6`). |
| Report & Merge | CÓ | Xuất báo cáo nghiệm thu `4` phần + `Archify HTML` qua Tailscale Serve (kèm lệnh đồng bộ plugin nếu user cần) rồi hỏi duyệt commit/merge về `dev`. |

## Hỏi đáp

- **Câu hỏi mở request (12:31 · 2026-11-20):** Chọn pipeline cho `2026-11-20-1230-trien-khai-4-de-xuat-agent` (`A: deep / B: express`) và loại request (`feature`).
  - **Trả lời của user:** `1a` (`deep` / `full`, `loai_request=feature`).
- **Vòng phỏng vấn thiết kế 5 điểm & mức QC (12:37 · 2026-11-20):**
  - Câu 1: Chiến lược phân bổ `model` AGY (`A: inherit + tự phân bổ động` / `B: ghim cứng` / `C: 100% inherit`).
  - Câu 2: Phạm vi triển khai (`A: trọn 4 trụ cột P0–P3` / `B: P0–P2 trước`).
  - Câu 3: Quyền ghi `docs/tdq/qc/<slug>.md` cho `tdq-qc-tester` & QC nhẹ mức `full` (`A: mở hẹp + full nhẹ` / `B: giữ read-only tuyệt đối`).
  - Câu 4: Rebuild `plugins/tdq-workflow-agy/` (`A: chỉ trong repo` / `B: sync luôn ~/.gemini`).
  - Câu 5: Mức QC (`A: full` / `B: lite` / `C: ultra`).
  - **Trả lời của user (nguyên văn):** `1a nhưng bữa nay có gemini 4 thì xếp theo 3.8 flash, 4 hydrogen, neon, cacbon 2a và mvp cho antigravity trước ở request này 3a 4a 5c cho phép unlimited agent QC song song và update luôn là ultra sẽ limit max 5 subagent QC thay vì 1 và có thể config trong plugin, và ở plan sẽ có báo type model và effort sẽ dùng trong plan cho implement và qc và report (nếu có)` (`2026-11-20T12:42:25+07:00`).
