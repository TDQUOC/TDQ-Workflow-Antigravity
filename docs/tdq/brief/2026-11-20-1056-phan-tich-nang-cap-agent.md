# Brief: Phân tích hạn chế & đề xuất nâng cấp hệ thống agent TDQ Workflow

Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

## Nguyên văn

> okay hãy fanout sub agent để phân tích các loại agent trong tdq-workflow và chỉ ra ít nhất 10 điểm hạn chế của nó. và dựa trên những điểm đó hãy phân tích, resreach từ những workflow, packeage lớn trên github cũng như trên internet để mà resreach và đưa ra phương án đề xuất upgrade và trình bày đầy đủ trong report giúp tôi, dùng ngôn từ natural dễ hiểu mở request để phân tích và xử lí giúp tôi

Ảnh đính kèm của người dùng liệt kê `6` subagent hiện có trong `agents/`: `tdq-build-resolver`, `tdq-implementer`, `tdq-qc-tester`, `tdq-refactor-cleaner`, `tdq-reviewer`, `tdq-security-reviewer`.

### Đọc hiểu ban đầu

- **Mục tiêu:** Fan-out subagent kiểm toán toàn diện `6` loại agent trong TDQ Workflow và chỉ ra ít nhất `10` điểm hạn chế có bằng chứng mã nguồn. Nghiên cứu các workflow và package mã nguồn mở lớn trên GitHub/internet để đề xuất phương án nâng cấp, trình bày tự nhiên, dễ hiểu trong báo cáo đầy đủ (Markdown + Archify HTML).
- **Phạm vi dự kiến:** Khảo sát `6` tệp `agents/tdq-*.md`, cơ chế gọi/nhắc subagent trong `skills/`, `scripts/tdq_team.py`, `tools/patches/`, `hooks/scripts/`; nghiên cứu ngoài qua `tavily-primary`; tổng hợp báo cáo phân tích và phương án nâng cấp.
- **Điểm cần làm rõ sau khi chọn pipeline:** Request này dừng ở báo cáo phân tích + đề xuất nâng cấp (`docs`) hay triển khai thẳng nâng cấp vào mã nguồn và plugin (`feature`), cùng nhóm ưu tiên nâng cấp chính.

## Hiểu & kiến thức

### Năng lực dùng được

Phân vân → DÙNG. Kiểm kê ngày 2026-11-20: `42` skill trên đĩa (`27` giữ + `15` ẩn theo `skill_inventory.py --loc "agent"`), cộng skill built-in trong context. Không xoá bảng này kể cả khi không có dòng DÙNG nào.

| Skill | Nguồn | Phán quyết | Dùng ở đâu / Lý do loại |
|---|---|---|---|
| tdq-intake | plugin:tdq-workflow | NỀN | Mở request, kiểm kê B0, khảo sát 3 chiều, research và phỏng vấn chốt phạm vi |
| tdq-spec | plugin:tdq-workflow | NỀN | Viết spec §1–§6 và Archify preview trước khi lập plan |
| tdq-plan | plugin:tdq-workflow | NỀN | Viết plan chi tiết theo phase, kiểm `--pair`, trình duyệt |
| tdq-build | plugin:tdq-workflow | NỀN | Thực thi plan, chạy QC theo mức chọn và xuất báo cáo Markdown + Archify HTML |
| tdq-conventions | plugin:tdq-workflow | NỀN | Quy định giao thức 1 lượt, state, approval, workinglog và khuôn khối chat |
| tdq-setup / tdq-status / tdq-lean | plugin:tdq-workflow | NỀN | Đảm bảo tìm kiếm 3 tầng (LSP → Grep → Graphify) và soát trạng thái workflow |
| Đã xét 36 skill khác (google-antigravity-sdk, cdesktop, gemini-api-*, tdq-browser-*, built-in) | user/plugin/built-in | KHÔNG | khác lĩnh vực |

### Khảo sát mã nguồn 3 chiều (Triangulation)

Đã đọc `docs/kien-truc.md`, bật LSP Python (`tdq_lsp.py check` ĐẠT `6/8` bậc, smoke `3/3` tầng), chạy `list_symbols`, `find_symbol`, `find_references`, `graphify query/explain` và grep toàn repo:

| Vùng file chạm | Phát hiện qua lớp nào (Grep/LSP/Graphify) | Tác động & quan hệ |
|---|---|---|
| `agents/tdq-*.md` (`6` tệp) | Grep tên agent toàn `skills/`, `scripts/`, `hooks/`, `tools/` | Xác định `3/6` agent mồ côi không có caller tự động và ghim cứng `effort: high`. |
| `tools/patches/skills_and_agents.py` | LSP (`list_symbols`, `find_references` `AGENT_FRONTMATTERS`, `transform_agents`) | Lệch `model` (`flash`/`pro` vs `inherit`), rơi `effort`, lệch `handoff-schema.json`, thiếu tool tìm kiếm. |
| `scripts/tdq_team.py` & `skills/tdq-build/` | LSP (`find_symbol` `lenh_packet`, `canh_bao_lach_luat`) + đọc trực tiếp | Packet 1 chiều thiếu Mini-Spec và `RANH GIỚI:`, `_render_target_spans` chỉ đọc `.py`, thiếu parser JSON handoff. |
| `hooks/scripts/*`, `hooks/rust/tdq-dispatch/`, `.codex-*`, `.opencode/` | Graphify (`query`, `explain subagent_dispatch_gate`) + Grep + đọc trực tiếp | Thiếu `SubagentStop`, `register_subagent_role` bị bỏ không, shell inline qua mặt `READONLY`, lệch giữa `4` host. |

### 14 Điểm hạn chế cốt lõi của hệ thống Agent TDQ

1. **Ba agent gần như "mồ côi" (Orphan Agents):** `tdq-build-resolver.md`, `tdq-refactor-cleaner.md` và `tdq-security-reviewer.md` không có lệnh gọi mặc định nào trong `skills/tdq-build/`, `team-mode.md`, `qc.md`, `qc-vong-fix.md` hay `tdq-lean/`. Chúng chỉ nằm trên bảng `subagent-tuning.md:22-24` và danh sách chuỗi hook. Riêng `tdq-qc-tester` chỉ chạy ở `muc_qc=ultra` (`qc.md:34,69`), khiến mọi request `full` bỏ qua thẩm định độc lập.
2. **Thiếu vai trò cốt lõi & chồng chéo ranh giới:** Hệ thống chưa có agent chuyên trách Explorer/Researcher, Architect, Debugger, Performance hay Docs, nên `subagent-tuning.md:25,60` phải mượn tạm `general-purpose`, `Explore`, `Plan`. Ngược lại, `vision-test-loop.md:109` gọi nhập nhằng `tdq-reviewer or tdq-qc-tester`, còn `tdq-reviewer.md:13-17` ôm cả phần kiểm định trùng với `doc_lint.py` và `qc.md`.
3. **Mâu thuẫn hợp đồng Commit & Tick checkbox:** `agents/tdq-implementer.md:18` yêu cầu implementer tự tick sub-box trong plan, nhưng `team-mode.md:135` và `tdq_team.py` cấm sửa ngoài `VÙNG FILE`. Cả `tdq-implementer.md:22-31` lẫn `team-mode.md` đều quên bắt buộc commit trong worktree trước khi trả `BRANCH`, dù `lenh_hop` chỉ merge các commit đã lưu.
4. **Quyền "Read-Only" dễ bị qua mặt qua shell inline:** Ba agent chỉ đọc thiếu trường `disallowedTools` ở nguồn và lại được cấp `run_command` trong bản AGY (`tools/patches/skills_and_agents.py:51-68`). Cả Python `bash_gate.py:130-150` và Rust `is_shell_mutator` (`command_parser.rs:90-134`) chưa chặn hết cách ghi bằng `python3 -c`, `node -e` hay `git -C`. Thậm chí `tdq-qc-tester.md:15-16` yêu cầu ghi kết quả dài vào `docs/tdq/qc/<slug>.md` nhưng `edit_gate.py:83-86` chặn thẳng tay.
5. **Xung đột `model` & đánh rơi `effort` khi build Antigravity:** Nguồn `agents/tdq-*.md:4-6` đặt `model: inherit` và `effort: high` (`subagent-tuning.md:19-24`). Tuy nhiên `skills_and_agents.py:45-80,156-162` xóa mất `effort`, hạ `tdq-implementer` và `tdq-build-resolver` xuống `flash`, nâng `tdq-security-reviewer` lên `pro`. Ngoài ra, `effort: high` ở gốc bị khóa cứng, không điều chỉnh được theo độ khó từng task.
6. **Thiếu hẳn hook `SubagentStop` (Python & Rust):** Cả `hooks.json` lẫn Rust `main.rs:187-200` (`route_event`) đều chưa xử lý sự kiện `SubagentStop`. Hệ thống không có chốt hậu kiểm khi subagent thoát để xác minh schema handoff, chứng cứ test hay trạng thái commit sạch (nguy cơ lỗi "đã làm nhưng quên ghi nhận").
7. **Đứt gãy đồng bộ trên `4` host:** `subagent_dispatch_gate.py` (`tools/patches/agy_hooks.py`) chỉ chạy trên AGY, còn Claude Code không có cổng này. `.codex-plugin/plugin.json:20` để `hooks: {}` và thiếu `agents/`; `.opencode/` chỉ bọc `skills/`. Hàm `scripts/build_portable.py` cũng bỏ qua `agents/` khi dựng bundle chung.
8. **Nhận diện vai trò mong manh & kênh `SubagentStart` yếu (`#23885`):** `register_subagent_role` (`_common.py:818`) chưa được gọi khi dispatch, khiến hook Python/Rust (`pre_tool_use.rs:31-57`) phải dò chuỗi ở dòng đầu `transcriptPath`. `subagent_start.py:4-7` nhắc luật fail-open bị cắt 40–60% `additionalContext` và bị loại khỏi `plugins/tdq-workflow-agy/` (`common_utils.py:29`).
9. **Hai bản `handoff-schema.json` lệch nhau & không có parser:** Bản gốc `skills/tdq-conventions/references/handoff-schema.json` dùng `modified_files`, `test_verdict`, `summary`, khác hoàn toàn bản do `skills_and_agents.py:115-136` sinh ra (`files`, `test_result`, `merge_ready`, `tick_ready`). Toàn bộ `6` agent vẫn trả text tự do và `tdq-build-resolver.md` ghi nhầm tên chuẩn `TDQ_HANDOFF_PAYLOAD` với mẫu `ERROR_RESOLVED`.
10. **Context Packet (`tdq_team.py packet`) thiếu Mini-Spec & chỉ hỗ trợ `.py`:** `_build_packet_payload` (`scripts/tdq_team.py:2206-2230`) chưa truyền khối Per-Task Mini-Spec mới (`Req:`, `GIỮ NGUYÊN`, `EARS`, `Logic cốt lõi`) hay `RANH GIỚI:`/`TỰ KIỂM:`. Hàm `_render_target_spans` chỉ phân tích AST cho file Python.
11. **Thiếu Shared Blackboard, Auto-Escalation & Bộ nhớ liên vòng:** Không có bảng trạng thái dùng chung (blackboard) hoặc event stream chuẩn để nối `implementer -> resolver -> qc -> reviewer`. Giới hạn `<= 2 retries` (`tdq-implementer.md:19`) chỉ là lời dặn bằng chữ, chưa tự leo thang sang `tdq-build-resolver` hay model mạnh hơn. Các vòng review/QC cũng chưa lưu vết hoặc trí nhớ dài hạn giữa các vòng.
12. **Thiếu Telemetry & Eval đo lường riêng từng loại agent:** Các công cụ `tdq_timing.py`, `token_audit.py`, `step_audit.py` chỉ phân tích sau khi xong phiên cho cả request. Hệ thống chưa đo tỷ lệ pass lượt đầu, số lần retry, chi phí token hoặc tỷ lệ báo giả theo từng role agent.
13. **Bản AGY tước công cụ tìm kiếm của agent & hở vùng test:** `skills_and_agents.py:45-80` bỏ mất công cụ tìm kiếm/LSP (`Grep`, `Glob`, `find_references`) khỏi `tools:` dù prompt `tdq-refactor-cleaner.md:20` bắt buộc gọi LSP. Bộ `tests/test_agent_frontmatter.py` chỉ kiểm 3/6 agent ở root (`line 56`), chưa kiểm chéo parity với `plugins/tdq-workflow-agy/agents/` và `handoff-schema.json`.
14. **Thiếu kiểm chứng diff mục tiêu & quét sâu bảo mật/liên module:** `tdq-security-reviewer.md:14-35` mới liệt kê đầu mục tổng quát, chưa gắn kiểm tra diff `git` hay SCA thư viện. Trong khi đó `tdq-implementer.md:16` chỉ khóa TDD trên 1 task đơn lẻ, chưa có kiểm chứng hợp đồng liên module trước khi chốt `MERGE-READY: yes`.

### Tổng hợp nghiên cứu ngoài (GitHub & Internet)

Toàn văn nguồn nghiên cứu được ghi tại `docs/tdq/research/2026-11-20-1056-phan-tich-nang-cap-agent.md` (kết hợp `2/6` truy vấn `tavily-primary` trước khi chạm giới hạn keyless ngày, failover 1 lần `search_web` và đối chiếu thêm kho nội bộ `ECC v2.2.3`). Một số điểm chính áp dụng trực tiếp:

- **Anthropic Claude Code Subagents & Teams (`code.claude.com`):** Siết quyền bằng `disallowedTools`, cô lập ở tầng hệ thống tệp bằng `isolation: worktree`, dùng task list dùng chung ở Agent Teams để chống mất trạng thái.
- **`obra/superpowers` & `BMAD-METHOD v6`:** Cưỡng chế quy trình TDD + review gắn theo từng task (`superpowers`); định tuyến thích ứng `Quick Flow` vs `Full Method` và dùng file story sống chống trôi ngữ cảnh (`BMAD`).
- **`OpenHands / SWE-agent / Aider / Roo Code / Cline`:** Nhật ký sự kiện append-only, trace JSON tái lập được để chạy eval, bản đồ AST/Tree-sitter kèm commit nguyên tử (`Aider`), tách mode quyền và chốt ngưỡng bước auto-approve (`Roo Code`).
- **Nghiên cứu học thuật & thực chiến (`MAST arXiv:2503.13657`, Anthropic, Cognition, `ECC v2.2.3`):** Phân loại 3 nhóm lỗi (`41,8%` từ Spec/Design, `36,9%` từ Lệch giao tiếp/handoff, `21,3%` từ Kiểm chứng); ưu tiên **JSON Handoff + `SubagentStop` + Adversarial Skeptic Verify (`>= 0.80`) + Least-Privilege Tools** và đo bằng eval đối chứng trước khi tăng số agent.

### Phạm vi đã chốt

- Mặt CHỌN: Báo cáo phân tích ít nhất `10` (thực tế `14`) hạn chế + đề xuất nâng cấp `4` trụ cột (Vai trò & Prompt, Phân quyền Tool & Hook/Rust, Handoff/Packet/Blackboard, Telemetry & Eval), ưu tiên ổn định trên Google Antigravity 2.0.
- Mặt LOẠI: Không sửa mã nguồn runtime, không sửa tệp `agents/tdq-*.md` hay `hooks/` trực tiếp, không cài đè plugin ngoài repo trong request `docs` này.
- Bối cảnh: Hệ thống `6` agent trong TDQ Workflow `v0.102.0` chạy chính trên Google Antigravity 2.0 (Windows/multi-OS), giữ tương thích không gãy với Claude Code, Codex, OpenCode.
- Mức đầu tư suy ra: đầy đủ — vì phạm vi bao phủ trọn `4` trụ cột kiến trúc, cần đối chiếu bằng chứng mã nguồn thật và lộ trình nâng cấp khả thi nhiều chặng.

### Quyết định đã chốt

- **Đầu ra & loại request (`1a`):** Giữ `loai_request=docs`; xuất báo cáo phân tích và đề xuất nâng cấp trọn vẹn (`Markdown` + `Archify HTML`), kèm kiến trúc mục tiêu và roadmap từng chặng để sẵn sàng mở request triển khai riêng sau này.
- **Trụ cột chiều sâu (`2abc`):** Đào sâu cả `4` trụ cột gồm thiết kế Vai trò/Prompt/Phối hợp, phân quyền Tool/Hook/Rust, chuẩn hóa Handoff/Packet/Blackboard và Telemetry/Eval từng agent.
- **Nền tảng ưu tiên (`3`):** Tối ưu chạy ổn định nhất trên **Google Antigravity 2.0** (`plugins/tdq-workflow-agy/`, tool name bản địa AGY, `tdq-dispatch` Rust, `skills_and_agents.py`, `agy_hooks.py`, `invoke_subagent`/`swarm`), đồng thời giữ tương thích an toàn với Claude Code, Codex, OpenCode.
- **Mức QC (`4a`):** `muc_qc=full` — kiểm chứng DoD, toàn bộ dẫn chứng `file:line`, nguồn nghiên cứu ngoài, `doc_lint`, binding Archify HTML và Tailscale Serve (không cần `tdq-qc-tester`).

### Lộ trình

| Bước/phase | Chạy? | Vì sao |
|---|---|---|
| Analyze & Fan-out 4 Subagent | CÓ | Đã hoàn tất kiểm toán `6` agent + hooks + 4-host và research ngoài (`14` điểm hạn chế có dẫn chứng). |
| Spec & Archify Preview | CÓ | Chốt cấu trúc báo cáo `4` trụ cột, tiêu chí QC `full` và sơ đồ Trước/Sau trước khi viết báo cáo. |
| Plan | CÓ | Lập danh sách task cụ thể (`doc_lint --pair` xanh) cho từng phần báo cáo, Archify HTML và vòng đối chiếu chứng cứ. |
| Implement (soạn báo cáo) | CÓ | Viết báo cáo đầy đủ bằng ngôn từ tự nhiên, dễ hiểu (`Markdown` + `Archify HTML`), kèm roadmap nâng cấp chia chặng. |
| QC mức full | CÓ | Kiểm chứng toàn bộ dẫn chứng `file:line`, URL nguồn, `doc_lint`, binding Archify HTML và Tailscale Serve (không cần `tdq-qc-tester` vì user chọn `full`, không phải `ultra`). |
| Report & Merge | CÓ | Xuất báo cáo nghiệm thu `4` phần + Archify HTML qua Tailscale Serve và hỏi duyệt commit/merge về `dev`. |

## Hỏi đáp

- **Câu hỏi mở request (11:03 · 2026-11-20):** Chọn pipeline cho `2026-11-20-1056-phan-tich-nang-cap-agent` (`A: deep / B: express`) và loại request (`docs` / `feature`).
  - **Trả lời của user:** `1a` (`deep` / `full`, mặc định `loai_request=docs`).
- **Vòng phỏng vấn phạm vi, trụ cột, nền tảng & mức QC (11:18 · 2026-11-20):**
  - Câu 1 (Đầu ra): `A: Chỉ báo cáo phân tích + phương án nâng cấp (Markdown + Archify HTML, docs)` vs `B: Triển khai luôn Chặng 1 (feature)`.
  - Câu 2 (Trụ cột chiều sâu): `A: Trọn gói 4 trụ cột` · `B: Vai trò, Prompt & Phối hợp` · `C: Hạ tầng Tool, Hook & 4-host` · `D: Tối giản top 5 lỗi`.
  - Câu 3 (Nền tảng ưu tiên): `A: AGY + Claude` · `B: Chuẩn chung tối giản` · `C: Tự nhập ràng buộc`.
  - Câu 4 (Mức QC): `A: full` · `B: lite` · `C: ultra`.
  - Câu 5 (Bổ sung thêm): `A: Không, đủ rồi` · `B: Có`.
  - **Trả lời của user (nguyên văn):** `1a 2abc 3ưu tiên chạy ổn trên antigravity 4a 5a` (`2026-11-20T11:18:15+07:00`).
