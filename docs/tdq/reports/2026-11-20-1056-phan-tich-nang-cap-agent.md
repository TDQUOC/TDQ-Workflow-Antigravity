# REPORT — Phân tích hạn chế & Phương án nâng cấp hệ thống Agent TDQ Workflow (`2026-11-20-1056-phan-tich-nang-cap-agent` · lane full · mode main · 3/3 task tick đủ)

Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

> **Ghi chú phạm vi:** Đây là báo cáo phân tích và đề xuất thiết kế thuộc loại `docs`. Toàn bộ mã nguồn thực thi (`agents/`, `hooks/`, `scripts/`, `tools/`, `plugins/`) và cấu hình ngoài repo chưa bị chỉnh sửa trong request này.

## Phần 1 — Bức tranh nhanh hệ thống 6 Agent hiện tại

Hãy hình dung hệ thống agent trong TDQ Workflow giống như một **xưởng phần mềm chuyên môn hóa** gồm `6` kỹ sư. Trên giấy tờ (`agents/tdq-*.md`), mỗi người có chức danh và nội quy riêng rất bài bản. Tuy nhiên, khi đưa vào vận hành thực tế trên `4` nền tảng (đặc biệt là Google Antigravity 2.0), bảng phân công ngoài cổng chỉ mới gọi đúng `1` kỹ sư lập trình đi làm thường xuyên. Ba kỹ sư sửa lỗi nhanh, dọn mã thừa và kiểm toán bảo mật gần như chưa được nối dây gọi tự động, còn người kiểm định chất lượng chỉ xuất hiện ở mức `ultra`.

Bảng đối chiếu thực trạng `6` subagent tại phiên bản `v0.102.0` (so sánh giữa nguồn gốc, quy chuẩn `skills/tdq-conventions/references/subagent-tuning.md:19-24` và bản biên dịch Antigravity tại `tools/patches/skills_and_agents.py:44-81`):

| Agent | Vai trò thiết kế | Quy chuẩn gốc (`model` / `effort`) | Thực chạy trên Antigravity (`tools` & `model`) | Điểm gọi thật trong `skills/` | Trạng thái vận hành thực tế |
|---|---|---|---|---|---|
| `tdq-implementer` | Code `1` task theo Red→Green trong worktree | `inherit` / `high` | `flash` (bỏ `effort`), `read/edit/write/run_command/send_message` | `tdq-build/SKILL.md:86`, `team-mode.md:89`, `quick-lane.md:91` | **Hoạt động chính** (chỉ định cho `mode=subagent`) |
| `tdq-qc-tester` | Kiểm thử độc lập theo bảng DoD | `inherit` / `high` | `inherit` (bỏ `effort`), `read_file/run_command/send_message` | `qc.md:34,69` (mức `ultra`), `vision-test-loop.md:109` | **Bỏ trống ở mức `full`** và `lite` |
| `tdq-reviewer` | Soi lỗ hổng spec và plan trước khi chạy | `inherit` / `high` | `inherit` (bỏ `effort`), `read_file/run_command/send_message` | `tdq-spec/SKILL.md:48`, `tdq-plan/SKILL.md:70` | **Tùy chọn**, ít được gọi chủ động |
| `tdq-build-resolver` | Vá lỗi biên dịch/kiểu bằng diff `< 5` dòng | `inherit` / `high` | `flash` (bỏ `effort`), giữ cả `write_file` | `0` điểm gọi trong toàn bộ `skills/` | **Mồ côi** (chưa nối vào vòng sửa lỗi) |
| `tdq-refactor-cleaner` | Dọn mã chết, chống trùng lặp, giữ logic | `inherit` / `high` | `inherit` (bỏ `effort`), thiếu LSP dù prompt bắt gọi | `0` điểm gọi trong toàn bộ `skills/` | **Mồ côi** (không gắn với `tdq-lean`) |
| `tdq-security-reviewer` | Kiểm toán OWASP, lộ bí mật, đặc quyền | `inherit` / `high` | `pro` (bỏ `effort`), `read_file/run_command/send_message` | `0` điểm gọi trong toàn bộ `skills/` | **Mồ côi** (chưa có chốt kích hoạt) |

---

## Phần 2 — 14 điểm hạn chế cốt lõi xếp theo 4 trụ cột

Dưới đây là `14` điểm hạn chế kiểm chứng trực tiếp trên đĩa mã nguồn. Các mục được gom vào `4` trụ cột kiến trúc để dễ theo dõi từ lớp giao tiếp đến tầng thực thi bên dưới.

### Trụ cột 1 — Vai trò, Kích hoạt & Hợp đồng Prompt

### HC-01: Ba agent gần như "mồ côi" và điểm mù ở QC mức full

- **Chuyện gì đang xảy ra:** Ba tệp `agents/tdq-build-resolver.md:1-45`, `agents/tdq-refactor-cleaner.md:1-41` và `agents/tdq-security-reviewer.md:1-52` được khai báo đầy đủ nhưng có `0` lệnh gọi thật trong `skills/tdq-build/SKILL.md`, `skills/tdq-lean/SKILL.md:1-40` hay `skills/tdq-build/references/team-mode.md`. Chúng chỉ nằm trong bảng danh mục `skills/tdq-conventions/references/subagent-tuning.md:22-24` và mảng nhận diện tên của hook (`hooks/scripts/_common.py:864-865`, `hooks/rust/tdq-dispatch/src/events/pre_tool_use.rs:23-28`). Tương tự, `tdq-qc-tester` chỉ chạy tại `muc_qc=ultra` (`skills/tdq-build/references/qc.md:34,69`), còn mức `full` và `lite` đặt giá trị `KHÔNG`.
- **Hậu quả thực tế:** Khi `tdq-implementer` vấp lỗi build lặt vặt hoặc gặp mã nguồn nhạy cảm bảo mật, leader phải tự sửa tay hoặc bỏ qua rà soát chuyên sâu. Request chọn mức `full` mặc định hoàn toàn không có kiểm định độc lập trước khi đóng vòng.
- **Mức độ nghiêm trọng:** **Cao** — làm lãng phí `50%` đội hình agent đã xây sẵn.

### HC-02: Thiếu vai trò cốt lõi và chồng chéo ranh giới kiểm định

- **Chuyện gì đang xảy ra:** Thư mục `agents/` chưa có agent chuyên trách khám phá codebase (`Explorer`), gỡ lỗi phân rã nguyên nhân (`Debugger`) hay cập nhật tài liệu. Tài liệu `skills/tdq-conventions/references/subagent-tuning.md:25,60` phải dùng tạm loại chung `general-purpose`, `Explore` hoặc `Plan` thiếu chuẩn handoff TDQ. Ở chiều ngược lại, `skills/tdq-build/references/vision-test-loop.md:109` viết `tdq-reviewer or tdq-qc-tester`, còn `agents/tdq-reviewer.md:13-17` ôm cả kiểm tra testability và parity trùng lặp với `doc_lint.py` cùng `qc.md`.
- **Hậu quả thực tế:** Trong phiên phân tích codebase lớn trên Antigravity, subagent khám phá tự do trả về tóm tắt thiếu cấu trúc `file:line`, buộc agent chính đọc lại. Vùng giao thoa giữa `reviewer` và `qc-tester` dễ dẫn đến gọi nhầm vai trò khi kiểm thử giao diện.
- **Mức độ nghiêm trọng:** **Trung bình** — giảm độ ổn định định tuyến ở bước `analyze` và kiểm thử giao diện.

### HC-03: Mâu thuẫn hợp đồng commit worktree và tick plan của implementer

- **Chuyện gì đang xảy ra:** Mục rule 4 trong `agents/tdq-implementer.md:18` yêu cầu `Tick Own Sub-Boxes Only` (tự đánh dấu sub-box trong plan), nhưng `skills/tdq-build/references/team-mode.md:135` cấm tuyệt đối subagent sửa file `plan/spec/state`. Ngoài ra, cả `agents/tdq-implementer.md:22-31` lẫn `skills/tdq-build/references/team-mode.md:130-138` đều không bắt buộc subagent chạy `git commit` trong worktree trước khi trả `BRANCH` và `MERGE-READY: yes`.
- **Hậu quả thực tế:** Nếu subagent làm đúng `tdq-implementer.md:18`, nó sẽ chạm ngoài vùng `VÙNG FILE` và bị `edit_gate` chặn. Nếu nó làm xong nhưng quên commit vào nhánh worktree, bước `merge` ở leader chỉ gộp nhánh rỗng hoặc sót toàn bộ code nằm ngoài vùng commit.
- **Mức độ nghiêm trọng:** **Nghiêm trọng** — gây kẹt trực tiếp chế độ `subagent` trên worktree.

### HC-04: Rà soát bảo mật còn chung chung và thiếu kiểm chứng liên module

- **Chuyện gì đang xảy ra:** Khung kiểm toán của `agents/tdq-security-reviewer.md:15-35` mới liệt kê 4 nhóm nguyên tắc OWASP tổng quát mà thiếu bước soi mục tiêu theo `git diff` hay kiểm tra lỗ hổng thư viện phụ thuộc (SCA). Cùng lúc, `agents/tdq-implementer.md:16` chỉ khóa TDD trên phạm vi 1 task đơn lẻ, không kiểm tra hợp đồng giao tiếp giữa các module trước khi trả `MERGE-READY: yes`.
- **Hậu quả thực tế:** Nếu sau này kích hoạt `tdq-security-reviewer`, agent dễ quét dàn trải tốn token mà vẫn sót gói thư viện lỗi thời. Trong các plan nhiều wave, mỗi worktree đều pass đơn lẻ nhưng lại gãy khớp nối khi leader gộp nhánh.
- **Mức độ nghiêm trọng:** **Trung bình** — làm tăng rủi ro hỏng tích hợp sau khi merge nhiều task.

---

### Trụ cột 2 — Phân quyền Tool, Model/Effort & Hạ tầng Hook/Rust

### HC-05: Quyền "chỉ đọc" hở qua shell và chặn nhầm chính báo cáo QC

- **Chuyện gì đang xảy ra:** Ba agent chỉ đọc (`tdq-reviewer`, `tdq-qc-tester`, `tdq-security-reviewer`) không khai báo `disallowedTools` ở gốc và đều được cấp `run_command` khi biên dịch sang Antigravity (`tools/patches/skills_and_agents.py:51-68`). Bộ lọc shell `hooks/scripts/bash_gate.py:130-150` và `hooks/rust/tdq-dispatch/src/command_parser.rs:90-134` lại bỏ sót các lệnh ghi gián tiếp như `python3 -c "...write_text(...)"`, `node -e` hay `git -C`. Ngược lại, biểu thức `RE_RED` ở `command_parser.rs:106` lại nhận nhầm toán tử so sánh `>=` thành lệnh ghi file `>`. Đáng chú ý nhất, `agents/tdq-qc-tester.md:16` yêu cầu ghi báo cáo dài vào `docs/tdq/qc/<slug>.md`, nhưng cả `hooks/scripts/edit_gate.py:83-86` lẫn `hooks/rust/tdq-dispatch/src/events/pre_tool_use.rs:245-252` đều chặn thẳng `READONLY` đối với mọi vai trò chứa `qc-tester`.
- **Hậu quả thực tế:** Kẻ kiểm định mang tiếng "chỉ đọc" vẫn có thể sửa code qua `python -c`, trong khi lệnh kiểm định chứa `>=` bị báo giả chặn oan. Bản thân `tdq-qc-tester` cũng không thể ghi biên bản QC dài xuống đúng tệp quy định vì bị hook chặn cửa.
- **Mức độ nghiêm trọng:** **Nghiêm trọng** — vừa hở tường bảo vệ ghi shell, vừa tự khóa chân quy trình QC.

### HC-06: Bản Antigravity tự đổi model, đánh rơi effort và khóa cứng nhịp nghĩ

- **Chuyện gì đang xảy ra:** Quy chuẩn `skills/tdq-conventions/references/subagent-tuning.md:19-24` quy định cả `6` agent dùng `model: inherit` và `effort: high`. Tuy nhiên, bảng `AGENT_FRONTMATTERS` trong `tools/patches/skills_and_agents.py:44-81` và hàm `transform_agents` (`lines 102-169`) tự động bỏ trường `effort`, hạ `tdq-implementer` và `tdq-build-resolver` xuống `model: flash`, đồng thời ép `tdq-security-reviewer` lên `model: pro`. Trong khi đó, bản gốc `agents/tdq-*.md` lại ghim cứng `effort: high`, không cho phép giảm xuống `medium` ở các task đơn giản.
- **Hậu quả thực tế:** Trên Antigravity 2.0, ngay cả khi người dùng bật model đầu bảng ở phiên chính, `tdq-implementer` vẫn bị hạ xuống `flash` để viết code logic cốt lõi, còn sửa 1 lỗi chính tả vẫn phải chịu tải cấu hình gốc cố định.
- **Mức độ nghiêm trọng:** **Cao** — làm tụt chất lượng code subagent trên Antigravity và sai lệch kỳ vọng từ `subagent-tuning.md`.

### HC-07: Bản Antigravity tước công cụ tìm kiếm và test chỉ kiểm một nửa số agent

- **Chuyện gì đang xảy ra:** Mảng `"tools"` trong `tools/patches/skills_and_agents.py:45-80` chỉ cấp cho các agent đọc `read_file`, `run_command`, `send_message` và bỏ sạch công cụ tìm kiếm (`grep_search`, `find_by_name`, LSP). Điều này đi ngược thẳng yêu cầu trong `agents/tdq-refactor-cleaner.md:20` bắt buộc phải gọi `mcp__lsp__find_references` trước khi xóa symbol. Về kiểm thử, `tests/test_agent_frontmatter.py:56` chỉ kiểm tra `3/6` agent ở thư mục gốc (`tdq-implementer`, `tdq-qc-tester`, `tdq-reviewer`), hoàn toàn bỏ qua `3` agent còn lại và chưa đối chiếu tính nhất quán với `plugins/tdq-workflow-agy/agents/`.
- **Hậu quả thực tế:** Khi chạy trên Antigravity, `tdq-refactor-cleaner` không có tool LSP trong frontmatter nên phải chạy lệnh shell tìm thủ công chậm hơn và dễ bỏ sót caller. Các lỗi lệch model hay thiếu tool ở bản build AGY cũng dễ lọt qua vòng test tự động.
- **Mức độ nghiêm trọng:** **Cao** — làm gãy quy trình 3 tầng tìm kiếm (`LSP -> Grep -> Graphify`) của subagent trên AGY.

### HC-08: Thiếu hoàn toàn hook `SubagentStop` trên cả Python lẫn Rust

- **Chuyện gì đang xảy ra:** Cấu hình `hooks/hooks.json:1-60` chỉ đăng ký `SessionStart` và `SubagentStart`, không có bất kỳ handler nào cho `SubagentStop`. Ở phía nhị phân tăng tốc cho Windows và Antigravity, hàm `route_event` trong `hooks/rust/tdq-dispatch/src/main.rs:187-200` cũng xử lý tới `Stop` cho phiên chính nhưng bỏ trống nhánh `SubagentStop`.
- **Hậu quả thực tế:** Khi một subagent kết thúc lượt, hệ thống không có chốt hậu kiểm tự động để xác minh cấu trúc handoff, kiểm tra nó đã chạy lệnh test hay chưa, hoặc kiểm tra xem worktree đã commit sạch chưa. Đây chính là nguyên nhân sinh ra lỗi **"đã làm nhưng chưa ghi nhận"** (`real-but-unrecorded done`).
- **Mức độ nghiêm trọng:** **Nghiêm trọng** — mất tuyến phòng thủ cuối cùng khi bàn giao giữa agent con và agent cha.

### HC-09: Nhận diện vai trò mong manh và kênh `SubagentStart` dễ bị cắt ngữ cảnh

- **Chuyện gì đang xảy ra:** Hàm `register_subagent_role` trong `hooks/scripts/_common.py:818-837` được thiết kế để ghi vai trò vào `.tdq-runtime/sessions.json`, nhưng hiện tại chưa có hook lúc dispatch nào gọi tới nó (kể cả `plugins/tdq-workflow-agy/hooks/scripts/subagent_dispatch_gate.py:1-53`). Do đó, cả `detect_subagent` (`_common.py:840-872`) lẫn `detect_subagent_role` (`hooks/rust/tdq-dispatch/src/events/pre_tool_use.rs:31-57`) phải mở dòng đầu tiên của file `transcriptPath` để đoán tên role. Bên cạnh đó, `hooks/scripts/subagent_start.py:4-7` thừa nhận kênh `additionalContext` bị prune mất `40–60%` tuân thủ (`issue #23885`), và tệp này còn bị loại khỏi bản AGY qua danh sách `EXCLUDED_AGY_HOOKS` (`tools/patches/common_utils.py:22-30`).
- **Hậu quả thực tế:** Nếu prompt gọi subagent hoặc dòng 1 transcript viết tắt mà không chứa đúng chuỗi `tdq-...`, cổng `READONLY` trong Rust và Python rơi về danh tính chung và mất khả năng khóa quyền theo vai trò.
- **Mức độ nghiêm trọng:** **Cao** — làm vô hiệu hóa nhận diện bảo vệ đặc quyền theo role trên Antigravity và Claude Code.

### HC-10: Đứt gãy đồng bộ hạ tầng agent trên bốn nền tảng host

- **Chuyện gì đang xảy ra:** Kiến trúc đa host dùng chung đang chênh lệch mạnh ở lớp agent và hook. Cổng `plugins/tdq-workflow-agy/hooks/scripts/subagent_dispatch_gate.py:1-53` (`tools/patches/agy_hooks.py:1325`) chặn điều phối swarm/worktree chỉ tồn tại cho Antigravity mà không có bản tương ứng ở `hooks/hooks.json`. Ngược lại, `.codex-plugin/plugin.json:19-20` khai báo `"skills": "./skills/"` và `"hooks": {}` (bỏ trống hooks và không ánh xạ `agents/`), còn `.opencode/plugins/tdq-workflow.js:32` chỉ đọc `../../skills` nên thiếu hoàn toàn tầng agent và cổng hook.
- **Hậu quả thực tế:** Cùng một quy tắc điều phối subagent nhưng chạy trên Antigravity một kiểu, Claude Code một kiểu, còn Codex và OpenCode hầu như không nhận được bảng định nghĩa `6` agent. Mọi nỗ lực siết chất lượng ở `agents/` dễ mất tác dụng khi người dùng đổi công cụ.
- **Mức độ nghiêm trọng:** **Trung bình–Cao** — tạo nợ bảo trì khi duy trì `4` host từ `1` repo.

---

### Trụ cột 3 — Handoff JSON Schema, Context Packet & Shared Blackboard

### HC-11: Hai bản `handoff-schema.json` tự mâu thuẫn và chưa có bộ đọc tự động

- **Chuyện gì đang xảy ra:** Trong cùng một repo tồn tại `2` tệp lược đồ mang chung tiêu đề `TDQ_HANDOFF_PAYLOAD` nhưng khác hẳn tên trường:
  - Bản gốc `skills/tdq-conventions/references/handoff-schema.json:11-48` bắt buộc `task_id`, `status` (`completed`/`failed`/`blocked`), `modified_files`, `test_verdict` (`pass`/`fail`), `summary`.
  - Bản sinh cho AGY từ `tools/patches/skills_and_agents.py:115-136` (`plugins/tdq-workflow-agy/skills/tdq-conventions/references/handoff-schema.json:5-50`) lại bắt buộc `files`, `test_result`, `branch`, `merge_ready`, `tick_ready` và thêm giá trị `"done"`.
  - Trong khi đó, cả `6` agent (`agents/tdq-*.md`) đều xuất kết quả dạng text key-value tự do, thậm chí `agents/tdq-build-resolver.md:30,39-45` còn gọi là `TDQ_HANDOFF_PAYLOAD` nhưng lại in ra `ERROR_RESOLVED` và `DIFF_LINES`. Repo cũng không có hàm nào parse hay validate JSON này lúc subagent trả lời.
- **Hậu quả thực tế:** Khi Antigravity hoặc leader cần đọc tự động trạng thái để quyết định merge hay retry, hai định dạng xung đột nhau khiến tự động hóa không tin cậy được, cuối cùng leader vẫn phải đọc chữ thủ công.
- **Mức độ nghiêm trọng:** **Cao** — phá vỡ chuẩn hóa giao tiếp giữa subagent và hệ điều phối.

### HC-12: Gói giao việc Packet bỏ rơi Mini-Spec mới và chỉ đọc được file Python

- **Chuyện gì đang xảy ra:** Hàm `_build_packet_payload` và `_format_packet_md` trong `scripts/tdq_team.py:2206-2265` chỉ xuất `7` trường cơ bản (`TASK`, `CỤM`, `BASE`, `WORKTREE`, `VÙNG FILE`, `TEST`, `TRẢ VỀ`) kèm `symbol_spans`. Nó chưa trích xuất các trường chất lượng cao của Plan V2+ (`Req:`, `Ngoài phạm vi`, `GIỮ NGUYÊN`, `EARS`, `Logic cốt lõi`) và cũng bỏ quên 2 mục `RANH GIỚI:` và `TỰ KIỂM:` trong mẫu prompt của `skills/tdq-build/references/team-mode.md:133-136`. Ngoài ra, hàm `_render_target_spans` phân tích AST chủ yếu cho file `.py`, còn file ngôn ngữ khác rơi về đọc thô.
- **Hậu quả thực tế:** Subagent trên Antigravity (vốn bị `skills_and_agents.py` hạ xuống model nhẹ hơn) không nhận được đủ tiêu chí chấp nhận EARS hay danh sách hàm `GIỮ NGUYÊN`, làm tăng xác suất phá hợp đồng cũ khi sửa code TypeScript, Rust hay PowerShell.
- **Mức độ nghiêm trọng:** **Cao** — làm suy giảm lợi ích của chuẩn Plan V2+ khi chia việc xuống subagent.

### HC-13: Thiếu Shared Blackboard, tự leo thang lỗi và trí nhớ liên vòng

- **Chuyện gì đang xảy ra:** Quy tắc ngắt mạch `Circuit Breaker (<= 2 retries)` tại `agents/tdq-implementer.md:19` mới là lời nhắc bằng văn bản. Hệ thống chưa có cơ chế điều phối tự động chuyển task bị nghẽn sang `tdq-build-resolver` (khi lỗi syntax/type) hoặc nâng cấp lên tier model cao hơn như khuyến nghị của `skills/tdq-conventions/references/subagent-tuning.md:40`. Giữa `implementer`, `resolver`, `reviewer` và `qc-tester` cũng chưa có bảng trạng thái dùng chung (Shared Blackboard) hay nhật ký lỗi giữa các vòng sửa `QCn.x`.
- **Hậu quả thực tế:** Khi một vòng sửa lỗi kéo dài qua 2–3 lượt, từng subagent mới được gọi lại thường khởi đầu với bộ nhớ trắng tinh, dễ dẫm lại đúng vết sai mà subagent trước vừa thử thất bại (`vòng lặp FM-1.3`).
- **Mức độ nghiêm trọng:** **Trung bình–Cao** — gây lặp lỗi và đội chi phí token khi xử lý ca khó.

---

### Trụ cột 4 — Telemetry & Eval đo lường riêng từng Agent

### HC-14: Chỉ đo thời gian cả phiên, mù hoàn toàn hiệu suất từng vai trò

- **Chuyện gì đang xảy ra:** Hiện repo đã có `tdq_timing.py`, `token_audit.py` và `step_audit.py`, nhưng mọi số liệu đều tổng hợp ở mức toàn bộ request hoặc từng phase (`analyze`/`spec`/`implement`). Chưa có trường telemetry nào gắn chặt theo từng agent role (`tdq-implementer`, `tdq-qc-tester`, `tdq-reviewer`…) để thống kê tỷ lệ thành công lượt đầu, số lần retry, thời gian chạy, lượng token hay tỷ lệ cảnh báo giả của `reviewer`.
- **Hậu quả thực tế:** Quyết định hạ `tdq-implementer` xuống `model: flash` trong `tools/patches/skills_and_agents.py:49` hay quy định `effort: high` trong `subagent-tuning.md:19` hiện đều dựa trên phán đoán định tính. Nhóm phát triển không có dữ liệu A/B để biết nâng cấp prompt nào thực sự làm tăng chất lượng hay giảm chi phí.
- **Mức độ nghiêm trọng:** **Trung bình** — khiến việc tối ưu agent sau này thiếu thước đo định lượng.

---

## Phần 3 — Bài học từ GitHub, nghiên cứu khoa học & đối chiếu nội bộ

### Minh bạch giới hạn tìm kiếm ngoài trong phiên phân tích

Để bảo đảm tính trung thực tuyệt đối theo chuẩn TDQ, báo cáo ghi rõ giới hạn thu thập dữ liệu thực tế:

- Công cụ `tavily-primary` trả về thành công **`2/6` truy vấn** (`BMAD-METHOD / OpenHands / SWE-agent / Aider / Cline / Roo Code` và `MAST / multi-agent failures`), còn `4/6` truy vấn sau bị chặn bởi hạn mức keyless ngày (`Retry after: 2112s / 734s / 1453s / 725s`).
- Hệ thống đã kích hoạt **đúng `1` lượt failover `search_web`** để phủ phần tài liệu chính thức của Claude Code, `obra/superpowers`, Anthropic và Cognition.
- Ba chủ đề **`CrewAI`, `LangGraph` và `OpenAI Codex` chưa thu thập được từ web** do chạm hạn mức trên, nên báo cáo không suy diễn chi tiết từ các khung đó. Phần đối chiếu với `Everything Claude Code` (`ECC v2.2.3`) được đọc trực tiếp từ báo cáo phân tích nội bộ `docs/tdq/de-xuat-nang-cap-toan-dien-tu-everything-claude-code.md:1-80`.

### Bảng tổng hợp mẫu thiết kế đáng học từ các nguồn đã kiểm chứng

| Dự án / Nghiên cứu | Nguồn tham chiếu kiểm chứng | Con số / Cơ chế nổi bật | Giải quyết trực tiếp hạn chế nào của TDQ? |
|---|---|---|---|
| **Claude Code Subagents & Teams** | https://code.claude.com/docs/en/sub-agents & https://code.claude.com/docs/en/agent-teams | Khai báo `disallowedTools`; `isolation: worktree`; Agent Teams chia sẻ task list chung và nhắn trực tiếp. | `HC-05` (chặt quyền read-only), `HC-03` (cô lập ghi), `HC-13` (Shared Blackboard). |
| **`obra/superpowers`** | https://github.com/obra/superpowers | Quy trình skill tự kích hoạt (`brainstorming → spec → TDD`); review gắn ngay sau mỗi task nhỏ. | `HC-01`, `HC-04` (kích hoạt review/clean tự động gắn vào vòng đời từng task). |
| **`BMAD-METHOD` (v6)** | https://www.augmentcode.com/guides/bmad-method-ai-development & https://diegorodrigo.dev/en/2026/04/06/bmad-in-practice-the-complete-ai-agent-development-workflow | Tách rõ `Full Method` và `Quick Flow`; đóng gói quyết định kiến trúc vào *story file* tự đủ ngữ cảnh. | `HC-12` (đưa Mini-Spec, `EARS`, `GIỮ NGUYÊN` vào thẳng `Packet` bàn giao). |
| **`OpenHands / SWE-agent / Aider`** | https://www.llms.blog/posts/autonomous-coding-agent-harnesses-in-production-comparing-openhands-swe-agent-aider-and-cline | Nhật ký sự kiện append-only (`OpenHands`); JSON trace tái lập để chạy eval (`SWE-agent`); bản đồ Tree-sitter & commit nguyên tử (`Aider`). | `HC-03` (commit nguyên tử worktree), `HC-12` (AST đa ngôn ngữ), `HC-13`, `HC-14`. |
| **`Roo Code / Cline`** | https://openweightthoughts.com/top-open-source-ai-coding-agents-2026-openhands-aider-cline-roo-code-swe-agent-p | Tách mode quyền (`Code`/`Architect`/`Ask`/`Debug`) và chốt cứng ngưỡng dừng auto-approve. | `HC-05` (tách rạch ròi tập công cụ), `HC-13` (ngắt vòng thử và leo thang có kiểm soát). |
| **MAST Taxonomy** | https://www.alphaxiv.org/abs/2503.13657 (`arXiv:2503.13657`) | Phân tích `1.642` trace chỉ ra `14` lỗi: Spec/Design `41,77%` (`FM-1.3` lặp bước `17,14%`), Misalignment `36,94%`, Verification `21,30%` (`FM-3.1` dừng non `6,2%`, kiểm sai `9,1%`). | `HC-01` (QC mức `full`), `HC-08` (`SubagentStop`), `HC-11` (chuẩn JSON chống rơi ngữ cảnh). |
| **Anthropic, Cognition & Splunk** | https://www.anthropic.com/research/building-effective-agents · https://cognition.com/blog/dont-build-multi-agents · https://www.splunk.com/en_us/blog/artificial-intelligence/multi-agent-system-failures.html | Không tách agent tràn lan làm đứt context; chuỗi 20 bước @ `95%` rơi độ tin cậy còn `~36%`; mỗi lần handoff tốn thêm `100–500 ms`. | Giữ bộ máy tinh gọn (`6 + 2` agent thay vì `19+`/`71`); rút ngắn chuỗi handoff bằng chốt kiểm trung gian. |
| **`ECC v2.2.3` (nội bộ TDQ)** | `docs/tdq/de-xuat-nang-cap-toan-dien-tu-everything-claude-code.md:36-75` | `Stop-Batching`, `Fact-Forcing Gate`, `Denial Deduplication`, `Static AST Closure`, `Adversarial Skeptic >= 0.80`; bác bỏ `71` agent phình to. | `HC-07`, `HC-08` (kiểm chứng `Input -> State -> Actual Output` ở `SubagentStop` & test bao đóng phát hành). |

---

## Phần 4 — Phương án nâng cấp 4 trụ cột ưu tiên ổn định trên Google Antigravity 2.0

Chiến lược cốt lõi là **không chạy theo số lượng agent phình to**, mà biến đội hình `6` agent hiện tại (cộng thêm tối đa `2` vai trò dùng chung là `tdq-explorer` và `tdq-debugger`) thành một dây chuyền **rõ đầu vào, cứng phân quyền, sạch đầu ra JSON và có camera nghiệm thu lúc giao ca (`SubagentStop`)**, tối ưu riêng cho cơ chế của **Google Antigravity 2.0**.

### 4.1. Trụ cột 1 — Kích hoạt 3 agent mồ côi, tinh gọn 6+2 vai trò & chốt hợp đồng worktree

1. **Nối dây kích hoạt tự động cho `3` agent mồ côi (`HC-01`, `HC-04`, `HC-13`):**
   - `tdq-build-resolver`: Tự động gọi ngay khi `tdq-implementer` hoặc bước test xanh bị lỗi biên dịch/kiểu qua `2` vòng sửa mà nguyên nhân nằm ở syntax/type/import nhỏ (`<= 5` dòng), thay vì để `implementer` xoay vòng.
   - `tdq-refactor-cleaner`: Gắn thành bước dọn tùy chọn sau khi wave code pass xanh trên nhóm file nóng, hoặc khi `tdq-lean` phát hiện mã chết/hàm vượt `50` dòng.
   - `tdq-security-reviewer`: Kích hoạt có điều kiện ở cuối pha `implement` khi `Chạm:` đụng các vùng nhạy cảm (`hooks/`, xác thực, shell, biến môi trường, đường dẫn tệp người dùng), kèm danh sách thay đổi lấy từ `git diff <base>...HEAD` và kiểm tra gói phụ thuộc (SCA).
2. **Đóng điểm mù QC ở mức `full` (`HC-01`):** Thay vì để mức `full` hoàn toàn `KHÔNG` có thẩm định độc lập, bổ sung bước kiểm nhanh nhẹ (`tdq-qc-tester` đọc diff + chạy lại DoD đã ghi) hoặc phân tách rõ mức `ultra` chạy thêm smoke/runtime để mọi request chuẩn vẫn có cặp mắt thứ hai.
3. **Bổ sung đúng `2` vai trò thiếu thực sự (`6 + 2`) và tách ranh giới `reviewer` (`HC-02`):**
   - Thêm `tdq-explorer` (đọc codebase bằng LSP/Grep/Graphify, trả về bản đồ `file:line — symbol` chuẩn hóa thay thế cho `general-purpose`/`Explore` rời rạc).
   - Thêm `tdq-debugger` (chuyên tái lập lỗi, khoanh vùng root-cause trong pha sửa lỗi `QCn.x`).
   - Giới hạn `tdq-reviewer` chỉ soi lỗi logic, lỗ hổng spec và độ phình kiến trúc (những thứ `doc_lint.py` và `tdq_plan_scaffold.py` không bắt được), bỏ kiểm tra trùng công cụ lint, và chuẩn hóa riêng `vision-test-loop.md` dùng `tdq-qc-tester`.
4. **Sửa hợp đồng `tdq-implementer` (`HC-03`):** Xóa bỏ yêu cầu tự tick sub-box ở `agents/tdq-implementer.md:18` (giữ nguyên tắc chỉ leader tick plan). Bổ sung bước bắt buộc `git add` và `git commit` vào nhánh worktree trước khi trả `BRANCH` và `MERGE-READY: yes`.

### 4.2. Trụ cột 2 — Tối ưu hóa Tool, Model/Effort & Hook/Rust cho Google Antigravity 2.0

Trên Google Antigravity 2.0, `tools/patches/skills_and_agents.py` biên dịch YAML gốc sang tên công cụ bản địa (`read_file`, `edit_file`, `write_file`, `run_command`, `send_message`), còn Rust binary `tdq-dispatch` đóng vai trò chốt chặn tốc độ cao trên Windows. Đây là trọng tâm nâng cấp ổn định nhất:

| Thành phần Antigravity 2.0 | Hiện trạng gây lỗi | Phương án nâng cấp đề xuất | Khả năng tương thích 3 host còn lại |
|---|---|---|---|
| **Bảng `AGENT_FRONTMATTERS` (`skills_and_agents.py`)** | Ép `implementer` và `build-resolver` về `model: flash`; nâng `security-reviewer` lên `pro`; bỏ `effort` và bỏ toàn bộ tool tìm kiếm/LSP. | Đặt mặc định `inherit` cho tác nhân code/chất lượng (giữ `flash` tùy chọn ở tầng caller cho task cực nhỏ); khôi phục `grep_search`, `find_by_name` và bộ tool MCP LSP (`find_symbol`, `find_references`, `go_to_definition`) cho mọi agent; mở `agent_tuning` hỗ trợ cấu hình effort theo độ khó task. | Nguồn gốc `agents/*.md` vẫn giữ YAML chuẩn (`Read`, `Grep`, `Glob`, `model`, `effort`) cho Claude Code. |
| **Phân quyền đọc/ghi (`edit_gate.py` & Rust `pre_tool_use.rs`)** | `qc-tester`, `reviewer`, `security-reviewer` giữ `run_command` toàn phần nhưng `tdq-qc-tester` lại bị `READONLY` cấm ghi `docs/tdq/qc/<slug>.md`. | Cho phép `write_file`/`edit_file` **có điều kiện (scoped allowlist)** riêng cho `tdq-qc-tester` vào đúng tệp `docs/tdq/qc/<slug>.md`; giữ chặn tuyệt đối mọi file code khác. Ở tầng tool bản địa AGY, tách `tdq-reviewer` không cần shell nặng và siết allowlist lệnh kiểm cho auditor. | Áp dụng đồng nhất trong Python (`edit_gate.py`, `bash_gate.py`) và Rust (`pre_tool_use.rs`) nên Claude Code được hưởng lợi chung. |
| **Bộ phân tích lệnh shell (`command_parser.rs` & `bash_gate.py`)** | Bỏ sót `python -c Path.write_text`, `node -e fs.writeFileSync`, `git -C`; nhưng lại báo giả lỗi `>` trên toán tử `>=`. | Vá `part_stdout_targets` trong Rust để phân biệt `>` chuyển hướng tệp với toán tử `>=`/`<=` bên trong chuỗi Python/PowerShell; bổ sung mẫu nhận diện ghi gián tiếp (`write_text`, `open(..., 'w')`, `fs.writeFile`, `git -C <path>`). | Logic Python `bash_gate.py` được đồng bộ quy tắc từ cùng bảng mẫu test. |
| **Ghi sổ role & `SubagentStart` (`subagent_dispatch_gate.py`, `_common.py`, `main.rs`)** | Chưa gọi `register_subagent_role` lúc dispatch nên phải đọc mò dòng 1 transcript; `subagent_start.py` bị cắt 40–60% ở Claude Code và bị loại ở AGY. | Khi `PreToolUse` bắt `invoke_subagent`/`swarm`/`Task`/`Agent`, gọi ngay `register_subagent_role(cwd, id_or_token, role, task)` ghi vào `.tdq-runtime/sessions.json`. Trên AGY, bơm nhắc gọn `< 300` ký tự và cho `subagent_dispatch_gate.py` kiểm trường bắt buộc + ghi sổ vai trò ngay từ bước dispatch. | Bổ sung `hooks/scripts/` đăng ký role cho `Task`/`Agent` trên Claude Code để cả 2 host không cần đọc mò transcript. |
| **Chốt hậu kiểm `SubagentStop` (Rust + Python)** | Cả `hooks.json` lẫn `main.rs` đều bỏ trống `SubagentStop`. | Bổ sung nhánh `"SubagentStop"` vào `hooks/hooks.json` và `route_event` trong `hooks/rust/tdq-dispatch/src/main.rs`: kiểm tra worktree đã commit hết thay đổi chưa, payload trả về đúng `handoff-schema.json` chưa, và log chứng cứ `Test:` có phải output thật không (`Fact-Forcing Gate`). | Chạy đồng thời qua Rust dispatcher trên Windows/AGY và Python fallback trên Linux/macOS/Claude Code. |
| **Đồng bộ 4 host & bộ test parity (`test_agent_frontmatter.py`)** | `.codex-plugin/plugin.json` để `"hooks": {}`; `.opencode/` chỉ bọc `skills/`; test chỉ soi `3/6` agent gốc. | Mở rộng `tests/test_agent_frontmatter.py` thành bộ kiểm định bắt buộc cho cả `6` (hoặc `6+2`) agent gốc **lẫn parity** với `plugins/tdq-workflow-agy/agents/` và `handoff-schema.json`. Thêm phần ánh xạ adapter agent cho `.codex-plugin/` và `.opencode/` ở mức đọc file định nghĩa chung để không gãy khi mở rộng. | Không ép `.codex`/`.opencode` chạy hook Antigravity nếu host chưa hỗ trợ, giữ an toàn `graceful degradation`. |

### 4.3. Trụ cột 3 — Thống nhất JSON Handoff, nâng cấp Context Packet & Shared Blackboard

1. **Hợp nhất một chuẩn `handoff-schema.json` duy nhất (`HC-11`):** Hợp nhất hai tệp schema đang xung đột thành **một hợp đồng JSON dùng chung** (giữ tên trường `status` thống nhất `done | blocked | failed`, `files`, `test_command`, `test_verdict`, `branch`, `commit_sha`, `merge_ready`, `tick_ready`, `digest <= 1500`). Bổ sung parser nhỏ trong `scripts/tdq_team.py check` và hook `SubagentStop` để kiểm tra schema, sửa luôn mẫu output cũ ở `tdq-build-resolver.md` và tất cả `agents/tdq-*.md`.
2. **Nâng cấp `tdq_team.py packet` theo chuẩn Plan V2+ (`HC-12`):** Mở rộng `_build_packet_payload` và `_format_packet_md` để bơm thêm tối thiểu `Req:`, `GIỮ NGUYÊN:`, `Tiêu chí chấp nhận (EARS):`, `RANH GIỚI:` và `TỰ KIỂM:` từ từng task của plan. Mở rộng `_render_target_spans` dùng biểu thức cấu trúc/LSP cho TypeScript/JS, Rust và PowerShell thay vì chỉ trích AST Python.
3. **Bảng trạng thái dùng chung (Shared Blackboard) & Auto-Escalation (`HC-13`):** Tạo tệp ledger gọn theo request tại `.tdq-runtime/blackboard/<slug>.json` ghi kết quả từng lượt chạy (`implementer → resolver → reviewer → qc`), vết lỗi đã thử (`failed_attempts`) để vòng sau không lặp sai lầm cũ. Khi `implementer` trả `blocked` với lỗi biên dịch/type sau `2` lần thử, leader có quy tắc định tuyến thẳng sang `tdq-build-resolver` hoặc tự động nâng `model` thêm 1 bậc thay vì lặp mù.

### 4.4. Trụ cột 4 — Telemetry & Eval đo lường từng Agent Role

1. **Telemetry chi tiết theo vai trò (`HC-14`):** Mở rộng schema bản ghi của `timing.jsonl` / `turn-ledger` thêm trường `agent_role`, `task_id`, `attempt`, `first_pass` và `model_used` (khớp dữ liệu thu thập tại `SubagentStart` và `SubagentStop`). `tdq_timing.py show` và `token_audit.py` có thêm mục tổng hợp gọn theo từng vai trò.
2. **Bộ Eval hồi quy có đối chứng trước khi giữ thay đổi:** Học tập mô hình JSON trace tái lập của `SWE-agent` và khuyến nghị của Anthropic, mọi thay đổi lớn về prompt agent hay hạ model (ví dụ chọn `flash` vs `inherit` cho `tdq-implementer`) phải chạy đối chứng trên bộ kịch bản mẫu (`tdq_eval.py`) về tỷ lệ pass lượt đầu, độ tuân thủ `Chạm:` và tổng chi phí token trước khi chốt vào `AGENT_FRONTMATTERS`.

---

## Phần 5 — Lộ trình triển khai 4 chặng & KPI kỳ vọng

Toàn bộ phương án được chia thành `4` chặng rõ ranh giới để dễ mở thành các request triển khai (`feature`) nhỏ, ít rủi ro hồi quy:

| Chặng | Nội dung triển khai trọng tâm | Độ ưu tiên trên Antigravity 2.0 | Tiêu chuẩn xong |
|---|---|---|---|
| **P0 — Vá lệch cấu hình & hợp đồng ngay** | Hợp nhất `1` file `handoff-schema.json`; sửa xung đột tick sub-box & ép commit worktree ở `tdq-implementer.md`; khôi phục `inherit` và công cụ tìm kiếm/LSP trong `AGENT_FRONTMATTERS`; mở rộng `test_agent_frontmatter.py` kiểm đủ `6` agent + parity AGY. | **Cao nhất** (sửa đứt gãy ngầm, `0` rủi ro phá flow chính) | Parity AGY/gốc `100%`, `test_agent_frontmatter.py` xanh hết. |
| **P1 — Siết bảo vệ Tool & Hook AGY/Rust** | Thêm `SubagentStop` (Rust `main.rs` + Python); gọi `register_subagent_role` lúc dispatch (`subagent_dispatch_gate.py` + `Task`/`Agent`); vá `command_parser.rs` & `bash_gate.py` (chặn `python -c`/`node -e`/`git -C`, bỏ báo giả `>=`); mở quyền ghi hẹp `docs/tdq/qc/<slug>.md` cho `tdq-qc-tester`. | **Rất cao** (bịt lỗ hổng shell & sửa kẹt QC) | `100%` test Rust + Python cho `READONLY` và `SubagentStop` pass. |
| **P2 — Kích hoạt đội hình `6+2`, Packet V2 & Blackboard** | Bật điểm gọi cho `3` agent mồ côi (`resolver`, `cleaner`, `security`) + bổ sung `explorer`/`debugger`; mở QC nhẹ ở mức `full`; nâng `tdq_team.py packet` kèm Mini-Spec/EARS & đa ngôn ngữ; thêm `.tdq-runtime/blackboard/<slug>.json` và rule leo thang `2` lần thử. | **Cao** (nâng năng lực thực chiến của `mode=subagent`) | Giảm lặp lỗi nhiều lượt, handoff đọc máy được `100%`. |
| **P3 — Telemetry từng role, Eval & Đồng bộ Codex/OpenCode** | Gắn `agent_role`/`first_pass`/`attempt` vào `timing.jsonl`; đo A/B model (`flash` vs `inherit`) qua `tdq_eval.py`; bổ sung lớp adapter đọc định nghĩa agent cho `.codex-plugin/` và `.opencode/` (giữ degrade an toàn). | **Trung bình** (tối ưu dài hạn dựa trên số liệu) | Có bảng KPI theo từng role và test parity đa host. |

> **Bảng KPI kỳ vọng (đặt làm mục tiêu đo khi triển khai, chưa phải số liệu chạy thật hiện tại):**
> - Số agent có điểm kích hoạt rõ ràng trong quy trình: `3/6` (hiện tại) → **`8/8` (`6+2` agent)**.
> - Độ chuẩn xác nhận diện role & hậu kiểm thoát subagent (`SubagentStop`): đoán từ dòng 1 transcript → **`100%` đăng ký ID lúc dispatch + kiểm tra khi thoát**.
> - Số schema handoff chuẩn được kiểm máy tự động: `2` bản lệch nhau, parse `0%` → **`1` bản duy nhất, validate tự động tại `SubagentStop`**.
> - Độ phủ kiểm thử tự động agent & parity Antigravity: `3/6` agent gốc → **`100%` toàn bộ agent gốc + parity AGY + test bypass shell**.

---

## Phần 6 — Nghiệm thu kết quả thực hiện Request

**Trước request (trạng thái/flow):** Thư mục `agents/` có `6` subagent chưa được kiểm toán tập trung. Hạ tầng chạy trên Antigravity 2.0 (`skills_and_agents.py`, `agy_hooks.py`, Rust `tdq-dispatch`) có nhiều độ vênh ngầm về `model`, `effort`, quyền `run_command`, nhận diện role và `handoff-schema.json`.
**Sau request (trạng thái/flow):** Đã hoàn tất fan-out `4` subagent kiểm toán toàn diện `6` agent, đối chứng mã nguồn trên đĩa, chốt `14` hạn chế theo `4` trụ cột và thiết kế lộ trình `P0`–`P3` ưu tiên Antigravity 2.0. · **Đã làm:** P1 hoàn chỉnh báo cáo Markdown (`reports/<slug>.md`) · P2 kết xuất Archify HTML (`reports/<slug>.html`) phục vụ qua Tailscale · P3 đối chứng đĩa và hoàn tất biên bản QC `full` (`qc/<slug>.md`).
**Đã test gì:** Đã chạy kiểm tra môi trường LSP (`tdq_lsp.py check`), kiểm tra toàn bộ `53` trích dẫn `file:line`, `16` symbol, `11` URL, `doc_lint.py` + `--pair`, `tdq_plan_scaffold.py`, `tdq_archify.py verify`, Tailscale HTTP, `git diff` và trọn bộ `tdq_test.py tron-bo` (`220` module).
**Kết quả test:** `tron-bo` đạt `PASS` (`4525` tests, `skipped=36`, `0` fail trong `1227.94s`; `tron_bo=1/2`, `bo_sot=0`) · `Q1`–`Q5` đạt `5/5 PASS` (`14/14` mục HC, `0` lỗi trích dẫn, `doc_lint` `0` lỗi, Archify `current` `valid=true`, Tailscale HTTP `200` `1.599.032` byte, `0` file code runtime bị sửa).
**Đầu ra:** `docs/tdq/reports/2026-11-20-1056-phan-tich-nang-cap-agent.md` · **Archify HTML:** `docs/tdq/reports/2026-11-20-1056-phan-tich-nang-cap-agent.html` (Tailscale: https://unity-pc-rtx3060.tail99896.ts.net/vlog/tdq-workflow-agy/reports/2026-11-20-1056-phan-tich-nang-cap-agent.html) · **Biên bản QC:** `docs/tdq/qc/2026-11-20-1056-phan-tich-nang-cap-agent.md`
**Giới hạn:** Request thuộc loại `docs` nên chưa sửa mã nguồn thực thi (`0` tệp trong `agents/`, `hooks/`, `scripts/`, `tools/`, `plugins/` bị chạm). Ngoài ra, `tavily-primary` đạt `2/6` truy vấn trước khi chạm hạn mức keyless ngày nên `CrewAI`, `LangGraph`, `OpenAI Codex` chưa trích xuất web trực tiếp và không bị suy diễn.
**Lệch spec chờ duyệt:** không có
**Git:** chưa commit trên nhánh `docs/phan-tich-nang-cap-agent` (chờ bạn duyệt commit và merge về `dev`).

## Thời gian

Request `2026-11-20-1056-phan-tich-nang-cap-agent` · lane full · opened at 2026-11-20T11:06:25+07:00

| Phase | Wall clock | API request | Tool wait | Background job | Observed union | Unattributed | Times entered |
|---|---|---|---|---|---|---|---|
| idle | 13s | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | 1 |
| analyze | 15 min | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | 1 |
| spec | 17 min | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | 1 |
| plan | 9 min | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | 1 |
| implement | 8 min | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | 1 |
| qc | 20 min | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | 1 |
| report | 1s | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | 1 |
| Total | 1h 09min | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] |  |

Model compute time is unavailable (`model_giay=null`). API includes network/provider latency; tool time is host wait. Observed metrics may overlap; unattributed time is not assumed user/model time.
Transcript attribution: project_window. Complete covers selected supported observations only.
- api_request_seconds: no_usable_source
- tool_call_seconds: no_usable_source
- background_job_seconds: no_usable_source
- observed_union_seconds: no_usable_observations
- unattributed_seconds: wall_minus_observed_union;no_usable_observations

## Thân PR (soạn sẵn)

**Tóm tắt:** Bổ sung báo cáo phân tích `14` điểm hạn chế có dẫn chứng mã nguồn trên hệ thống `6` agent của TDQ Workflow và đề xuất lộ trình nâng cấp `4` trụ cột (`P0`–`P3`) ưu tiên độ ổn định cho Google Antigravity 2.0.
**Trước/Sau:** Bản xem trước Trước/Sau tại `docs/tdq/spec/2026-11-20-1056-phan-tich-nang-cap-agent-preview.html` và báo cáo trực quan đầy đủ tại `docs/tdq/reports/2026-11-20-1056-phan-tich-nang-cap-agent.html`.
**Đã kiểm:**
- `py -3 -X utf8 scripts/tdq_test.py tron-bo --workers 1 --fresh --reuse off` -> `PASS` (`4525` tests, `skipped=36`, `0` fail, `1227.94s`).
- `Q1`–`Q5` DoD + `qc_deep_check.py` -> `5/5 PASS` (`14/14` hạn chế, `53` trích dẫn `file:line`, `16/16` symbol, `11/11` URL, `0` lỗi ngoài `docs/`).
- `py -3 -X utf8 scripts/doc_lint.py ... --pair ...` -> `0` vi phạm trên tất cả `6` tài liệu (`brief`, `research`, `spec`, `plan`, `reports`, `qc`).
- `py -3 -X utf8 scripts/tdq_archify.py verify ...` + Tailscale HTTPS -> `status=current`, `valid=true`, `HTTP 200`.
**Rủi ro hồi quy:** Không có rủi ro hồi quy runtime vì request thuộc loại `docs`, toàn bộ thay đổi chỉ nằm trong `docs/tdq/`.
<!-- tdq-archify-binding:start -->
<!-- manifest: 2026-11-20-1056-phan-tich-nang-cap-agent.manifest.json -->
<!-- manifest_digest: 9683f0566e217d500e37fb6bfb3ee0d6b017bc8c0b3d9d17e0d82d569e8e2605 -->
<!-- tdq-archify-binding:end -->