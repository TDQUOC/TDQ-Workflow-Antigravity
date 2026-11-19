# Báo cáo Audit — Sai sót Behavior TDQ Workflow khi nới Hook & 10 Nguy cơ tiềm ẩn

Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

- **Mã yêu cầu (Request Slug):** `2026-11-19-1457-audit-sai-sot-noi-hook`
- **Nhánh làm việc:** `docs/audit-sai-sot-noi-hook` (tách từ `dev`)
- **Tài liệu Brief:** [2026-11-19-1457-audit-sai-sot-noi-hook.md](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/brief/2026-11-19-1457-audit-sai-sot-noi-hook.md)
- **Kế hoạch triển khai (Mini-Plan):** [2026-11-19-1457-audit-sai-sot-noi-hook.md](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/plan/2026-11-19-1457-audit-sai-sot-noi-hook.md)
- **Báo cáo trực quan (Archify HTML cục bộ):** [2026-11-19-1457-audit-sai-sot-noi-hook.html](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/reports/2026-11-19-1457-audit-sai-sot-noi-hook.html)
- **Đường dẫn xem trực tiếp qua Tailscale Serve:** https://unity-pc-rtx3060.tail99896.ts.net/vlog/tdq-workflow-agy/reports/2026-11-19-1457-audit-sai-sot-noi-hook.html

---

## 1. Trước request: Hiện trạng nới hook & Bằng chứng pháp y sai sót ở request vừa qua

Trước request kiểm tra này, chuỗi hook của plugin Antigravity (`plugins/tdq-workflow-agy/`) vừa trải qua hai đợt thay đổi liên tiếp nhằm giảm độ trễ và tránh làm kẹt lượt model trên Antigravity 2.0:

1. **Đợt `v0.100.0` (`2026-11-18-1814-toi-uu-hook-huong-dan` — R1–R3):** Gộp dispatcher đơn tiến trình Python `dispatch.py`, giảm lặp `prompt_context`, bỏ 7 script/mã luật và **mềm hóa hàng loạt cổng kỷ luật trên Antigravity (`is_agy()`)** (`TDQ:TICK`, `TDQ:LOG`, `TDQ:SEARCH` lần 1, `TDQ:DOD`, tắt `TDQ:RULE`/`TDQ:GON` giữa lượt).
2. **Đợt `v0.101.0` (`2026-11-19-0046-dong-rust-binary-hook`):** Biên dịch và cài đặt binary Rust `bin\tdq-dispatch.exe` trực tiếp cho toàn bộ 6 sự kiện trong `plugins/tdq-workflow-agy/hooks.json` (và bản user-level tại `C:\Users\admin\.gemini\config\plugins\tdq-workflow-agy\hooks.json`). Tuy nhiên bản Rust mới chỉ hiện thực 4 nhóm kiểm soát tối thiểu ở `PreToolUse` và 1 bộ đếm `stop_streak` ở `Stop`.

### Bằng chứng pháp y thực tế từ request `2026-11-19-0046-dong-rust-binary-hook`

Kiểm tra lại các tạo tác trên đĩa và nhật ký hội thoại (`transcript.jsonl` bước `1779–2340`) cho thấy behavior của TDQ Workflow đã trượt kỷ luật rõ rệt mà không bị hook nào chặn lại:

- **Sót 3 checkbox plan và giữ nguyên dòng trạng thái plan:** Trong [2026-11-19-0046-dong-rust-binary-hook.md](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/plan/2026-11-19-0046-dong-rust-binary-hook.md), dòng 6 vẫn giữ `Trạng thái plan: CHỜ DUYỆT`; mục `## Khuôn khối hợp đồng skill` (dòng 338, 345, 352) còn nguyên 3 dòng `- [ ] **T1.1**`, `- [ ] **T3.1**`, `- [ ] **T3.2**`. Theo `scripts/tdq_state.py:922`, cả 3 dòng này đều khớp regex `_TASK_LINE`, khiến `plan_tick_state()` vẫn báo `open_count=3`, `all_done=False` — nhưng không một cổng `PreToolUse` hay `Stop` nào chặn lại.
- **Duyệt mode `subagent` nhưng thực thi inline & vượt rào qua shell:** User đã chốt `duyệt plan mode subagent`, và `docs/tdq/team/2026-11-19-0046-dong-rust-binary-hook.json` đã phân công 6 task `"quyet_dinh": "giao"` (`T1.1`, `T3.1`, `T3.3`, `T4.1`, `T4.2`, `T4.3`). Tuy vậy suốt 90 thao tác `write_file`/`edit_file` trong pha thực thi (`step 1779–2333`), không có lời gọi `invoke_subagent` nào để giao việc implement (chỉ gọi 1 lần cho `tdq-qc-tester` ở `step 2334`). Tại `step 1803`, `run_command` chạy inline Python (`open(...)`) tạo `tools/patches/gate_guidance.json`, lách hoàn toàn qua `edit_gate`.
- **Tắc nghẽn nhắc nhở chưa xả & phân mảnh 2 thư mục runtime:** `docs/tdq/.tdq-runtime/pending-reminders-default.jsonl` (1.861 bytes) còn lưu 2 thông điệp `[TDQ:LOG]` và `[TDQ:UNFINISHED]` (`8 open task(s)`) chưa bao giờ được xả; đồng thời tồn tại song song `.tdq-runtime/` ở thư mục gốc dự án (do Rust ghi `stop_streak.json`, `.tdq-read.jsonl`, `notifications.jsonl`, `rtk-probe.json`, `ccr/`) tách biệt hoàn toàn với `docs/tdq/.tdq-runtime/` của Python.
- **Lệch ghi nhận pha & lỗi biên tập báo cáo:** `phase_history` của request trước nhảy thẳng `plan -> qc` thiếu pha `implement`; báo cáo [2026-11-19-0046-dong-rust-binary-hook.md](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/reports/2026-11-19-0046-dong-rust-binary-hook.md) bị lặp tiêu đề `## 4. Kết quả test ra được cái gì?` tại dòng 60 và dòng 86.

---

## 2. Sau request: Ma trận đối chiếu cổng giữa Python gốc, Python AGY R1–R3 và Rust v0.101.0

| Cổng / Cơ chế | Chuẩn gốc (Claude / Python) | Python AGY R1–R3 (`agy_hooks.py` / `dispatch.py`) | Rust `tdq-dispatch` (`v0.101.0`, đang chạy mặc định) | Kết quả thực tế trên AGY |
|---|---|---|---|---|
| `TDQ:TICK` (`edit_gate` & `stop_gate`) | **BLOCK** khi thiếu `[~]`, >1 `[~]`, streak >= 3 hoặc plan SHA không đổi lúc `Stop` | **SOFT REMIND** (`_tick_notify` gọi `remind` ở `edit_gate.py:81-85`; `queue_remind` ở `stop_gate.py:362-363`) | **KHÔNG KIỂM TRA** (`pre_tool_use.rs` và `stop_streak.rs` không check `[~]` / plan SHA) | Model quên tick plan, sửa xong nhảy bước không bị chặn |
| `TDQ:APPROVE` (chưa duyệt spec/plan/quick) | **BLOCK** ở `edit_gate` + kiểm signal prompt ở `bash_gate` | **BLOCK** trong project (`edit_gate.py:184-185`) + kiểm signal ở `bash_gate.py:100-124` | **KHÔNG KIỂM TRA** (không đọc `cong_dang_cho` / `quick_approved` / `spec_approved`) | Có thể sửa source khi cổng duyệt còn mở nếu chạy Rust |
| `TDQ:TEAM` & `TDQ:VUNG` | **BLOCK** subagent trước `implement`, leader làm thay task `giao`, hoặc ghi ngoài `Chạm:` | **BLOCK** ở `edit_gate.py:155-256` + check field `subagent_dispatch_gate.py:40-45` | **KHÔNG KIỂM TRA** vùng file / vai trò (chỉ auto-overwrite `Workspace='inherit'`) | Subagent hoặc leader ghi đè sai phân công không bị chặn |
| `TDQ:LOG` & `TDQ:DOD` ở `Stop` | **BLOCK** turn nếu repo đổi mà thiếu working log (`stop_block`) | **SOFT REMIND** đẩy sang `queue_remind` (`stop_gate.py:338-340, 398-401`) | **KHÔNG KIỂM TRA** (không đọc `git status` hay `docs/workinglog/` hay `dod_tick_state`) | Kết thúc lượt mà thiếu log hoặc thiếu tick DoD |
| `TDQ:UNFINISHED` ở `Stop` | **BLOCK** (`stop_block`) tới khi streak > 3 mới chuyển `[TDQ:STUCK]` | **THOÁT SỚM** khi `continuationActive=True` (`stop_gate.py:299-302` return trước `_chan_chua_xong`) | Thiếu check `[>]`, không đọc `continuationActive`, `dem > 3` gắn nhầm card `"INTAKE"` (`stop_streak.rs:45-60`) | Dừng dở giữa pha `implement`, user phải nhắc `"tiếp tục"` |
| `TDQ:ZERO-POPUP` | **BLOCK** mọi popup hỏi trong request đang mở | **BLOCK** `ask_question` / `ask_user_question` (`ask_gate.py:55-61`) | **KHÔNG KIỂM TRA** (`pre_tool_use.rs` không xử lý `ask_question`) | Popup question UI không bị chặn bởi Rust hook |
| `TDQ:READONLY` | **BLOCK** subagent chỉ đọc sửa file | **BLOCK** `edit_file` với `reviewer`/`qc-tester`/`browser`; `bash_gate` **sót `qc-tester`** (`bash_gate.py:173`) | **KHÔNG KIỂM TRA** vai trò subagent (`reviewer`, `qc-tester`, `browser`) | Subagent read-only không bị Rust chặn ghi file |
| `TDQ:SEARCH` (tìm kiếm 3 tầng) | **BLOCK** grep/shell search khi chưa hỏi LSP/Graphify | **ÂN XÁ LẦN 1** (`agy_search_grace`), **cho qua** mọi lệnh `unknown` (`agy_malformed_allow`) | **KHÔNG KIỂM TRA** ở `PreToolUse`; `PostToolUse` không ghi `graphify` via shell | Agent trôi về Grep mò, ít chịu mở LSP/Graphify |
| `TDQ:GON` / `TDQ:RULE` / `TDQ:QC` | Bơm nhắc gọn đầu lượt + rule theo đuôi file `.py`/`.ts` | **TẮT** `TDQ:RULE` (`edit_gate.py:311`), **TẮT** `_nhac_gon` & `_nhac_qc` (`prompt_context.py:496`) | Chỉ có 1 dòng ngắn `[TDQ:GON]` ở `UserPromptSubmit`; `session_start.rs:48` cắt `&rules_content[..1500]` | Càng nhiều lượt, model càng trôi xa chuẩn Clean Code & QC |
| `PreInvocation` & `PostInvocation` | Bơm `TDQ:NEXT`, `TDQ:INTAKE`, `TDQ:APPROVE`, xả nhắc | Chạy `prompt_context.py` + `post_invocation.py` xả `injectSteps` | **KHÔNG MATCH** trong `main.rs:123-131` (rơi vào `_ => allow()`) | Bỏ rơi toàn bộ context đầu/cuối lượt khi chạy Rust |
| Giao thức JSON & Overwrite | Chuẩn Claude `hookSpecificOutput` | Chuẩn AGY `injectSteps` / `reason` / bọc `Arguments` cho `call_mcp_tool` | Xuất `additional_context` / `explanation`; thiếu `workspacePaths`, `toolInput`, `file_path` | Payload AGY và phản hồi Rust lệch schema |
| Thư mục `.tdq-runtime` | `docs/tdq/.tdq-runtime/` | `docs/tdq/.tdq-runtime/` (`_common.py:659`) | `.tdq-runtime/` ở root (`storage.rs:33`) | Hai engine ghi vào 2 nơi tách biệt, mất trạng thái chéo |

---

## 3. Đã test / rà soát những gì?

Cuộc kiểm tra đối chiếu mã nguồn tĩnh, cấu hình phân phối và nhật ký thực thi thật trên toàn bộ các thành phần sau:

- **Lớp cấu hình & patcher Python Antigravity:**
  - `plugins/tdq-workflow-agy/hooks.json`, `plugins/tdq-workflow-agy/hooks/scripts/dispatch.py`, `_common.py`, `edit_gate.py`, `stop_gate.py`, `prompt_context.py`, `search_gate.py`, `bash_gate.py`, `ask_gate.py`, `read_gate.py`, `lsp_gate.py`, `subagent_dispatch_gate.py`, `command_gate.py`, `post_invocation.py`, `session_start.py`.
  - `tools/patches/agy_hooks.py` và từ điển 22 mã chuẩn `tools/patches/gate_guidance.json`.
  - Bản cài user-level thực tế tại `C:\Users\admin\.gemini\config\plugins\tdq-workflow-agy\hooks.json`.
- **Lớp Rust Standalone Binary (`v0.101.0`):**
  - Toàn bộ crate `hooks/rust/tdq-dispatch/src/`: `main.rs`, `protocol.rs`, `storage.rs`, `command_parser.rs`, `events/session_start.rs`, `events/user_prompt_submit.rs`, `events/pre_tool_use.rs`, `events/post_tool_use.rs`, `events/stop_streak.rs`, `events/notification.rs`.
  - Bộ test đối chiếu vi phân `tests/test_rust_dispatch_parity.py`.
- **Bằng chứng thực thi quá khứ (Request `2026-11-19-0046-dong-rust-binary-hook`):**
  - `scripts/tdq_state.py` (`_TASK_LINE`, `plan_tick_state`, `task_open_count`).
  - `docs/tdq/plan/2026-11-19-0046-dong-rust-binary-hook.md`, `docs/tdq/team/2026-11-19-0046-dong-rust-binary-hook.json`, `docs/tdq/reports/2026-11-19-0046-dong-rust-binary-hook.md`.
  - Sổ runtime `docs/tdq/.tdq-runtime/pending-reminders-default.jsonl`, thư mục `.tdq-runtime/`, và nhật ký phiên `transcript.jsonl` (`step 1779–2340`).

---

## 4. Kết quả test & Danh sách 10 hạn chế / nguy cơ gây sai behavior từ khi nới hook

Qua phân tích chéo giữa hai đợt thay đổi (`v0.100.0` và `v0.101.0`), dưới đây là **10 hạn chế và nguy cơ gây sai behavior** được sắp xếp theo mức độ nghiêm trọng giảm dần:

### 1. [CRITICAL] Mất phanh cưỡng chế Tick Plan (`TDQ:TICK`)

- **Bằng chứng:** `tools/patches/agy_hooks.py:1788-1803`, `edit_gate.py:81-85, 275-307`, `tools/patches/agy_hooks.py:2408-2423`, `stop_gate.py:355-369`; `hooks/rust/tdq-dispatch/src/events/pre_tool_use.rs:9-138`, `stop_streak.rs:9-65`.
- **Trước vs Sau:** Trước đây, `edit_gate` gọi `block(cwd, payload, "TDQ:TICK", ...)` ở 3 điểm (chưa có task `[~]`, nhiều hơn 1 task `[~]`, hoặc sửa code >= 3 lần không đổi `plan_sha`) và `stop_gate` gọi `stop_block` nếu sửa code mà plan SHA đứng yên. Từ `v0.100.0`, `agy_hooks.py` bọc thành `_tick_notify` chuyển thành `remind` trên AGY và đẩy cảnh báo ở `Stop` vào `queue_remind`. Sang `v0.101.0`, Rust binary thậm chí **bỏ hoàn toàn** việc đọc file plan khi `PreToolUse` và chỉ kiểm tổng `[ ]`/`[~]` ở `Stop`.
- **Kịch bản sai behavior thực tế:** Khi `phase=implement`, agent hoàn thành code xong hoặc quên đổi `[~]` sang `[x]`, không có bất kỳ gate nào cản đường trước khi edit hay lúc kết thúc lượt. Kết quả: trong request `2026-11-19-0046-dong-rust-binary-hook`, 3 task `T1.1`, `T3.1`, `T3.2` trong mục hợp đồng skill còn nguyên `- [ ]` và dòng trạng thái plan giữ nguyên `CHỜ DUYỆT` tới lúc đóng request.
- **Hướng khắc phục:** Khôi phục chặn cứng `TDQ:TICK` ở `PreToolUse` khi sửa source ngoài `tests/**` và `docs/**` mà không có đúng 1 task `[~]` (hoặc `[>]` theo team mode) trên cả Python AGY và Rust `pre_tool_use.rs`.

### 2. [CRITICAL] Rust `tdq-dispatch` không khớp sự kiện `PreInvocation` và `PostInvocation` (Silent No-Op)

- **Bằng chứng:** `plugins/tdq-workflow-agy/hooks.json:16, 107`; `hooks/rust/tdq-dispatch/src/main.rs:123-131` đối chiếu với `plugins/tdq-workflow-agy/hooks/scripts/dispatch.py:191-198`.
- **Trước vs Sau:** Trong `hooks.json`, Antigravity được cấu hình gọi `bin\tdq-dispatch.exe --event PreInvocation` (mở lượt) và `--event PostInvocation` (xả nhắc nhở cuối lượt). Trong `dispatch.py`, hai sự kiện này được nối tới `prompt_context` và `post_invocation`. Tuy nhiên, bảng `match event_name.as_str()` trong `main.rs:123-131` chỉ khớp `UserPromptSubmit` và `Notification` (tên sự kiện của Claude), không có nhánh `PreInvocation` hay `PostInvocation`, nên rơi thẳng vào nhánh mặc định `_ => HookDecision::allow()`.
- **Kịch bản sai behavior thực tế:** Khi chạy bằng Rust binary mặc định, toàn bộ pha đầu lượt (`[TDQ:NEXT]`, `[TDQ:INTAKE]`, nhận diện `[TDQ:APPROVE]` theo prompt, kiểm tra `spec_sha256` drift, chụp `turn_start` snapshot) và pha xả nhắc nhở cuối lượt đều bị vô hiệu hóa hoàn toàn trong im lặng.
- **Hướng khắc phục:** Map `"PreInvocation" | "UserPromptSubmit"` và `"PostInvocation"` trong `main.rs`, thực hiện đầy đủ chuẩn `prompt_context` và xả hàng đợi nhắc nhở.

### 3. [CRITICAL] Sai lệch giao thức JSON Antigravity 2.0 (Input & Output) trên Rust

- **Bằng chứng:** `hooks/rust/tdq-dispatch/src/protocol.rs:23-34, 90-107`, `hooks/rust/tdq-dispatch/src/events/pre_tool_use.rs:13-16` đối chiếu với `plugins/tdq-workflow-agy/hooks/scripts/_common.py:489-549` và `edit_gate.py:111`.
- **Trước vs Sau:** Ở chiều ra, AGY 2.0 yêu cầu `{"injectSteps": [{"systemMessage": {"systemMessage": ..., "metadata": {"user_markdown": ...}}}]}` cho `SessionStart`/`PreInvocation`/`PostInvocation` và `{"decision": "deny"|"continue", "reason": ...}` cho `PreToolUse`/`Stop` (`_common.py:498, 534, 545`). Rust `HookDecision` lại tuần tự hóa thành `additional_context` và `explanation` ở top-level (`protocol.rs:27, 33`). Ở chiều vào, `HookPayload` thiếu các khóa thật của AGY (`workspacePaths`, `workingDirectory`, `toolCall`, `conversationId`, `lastUserInput`, `continuationActive`, `toolInput`), và `pre_tool_use.rs:13-16` chỉ kiểm tên tool `write_file`/`edit_file` với key `Path`, bỏ sót `write_to_file`, `replace_file_content`, `multi_replace_file_content` và các key `TargetFile`/`file_path`.
- **Kịch bản sai behavior thực tế:** Context tiêm từ Rust `SessionStart`/`UserPromptSubmit`/`Stop` có thể bị runtime Antigravity bỏ qua vì không đúng `injectSteps`/`reason`, còn thao tác sửa `docs/tdq/state.json` qua `write_to_file` hoặc `replace_file_content` lọt qua cổng `TDQ:STATE`.
- **Hướng khắc phục:** Đồng bộ struct `HookPayload` và trình xuất JSON trong `protocol.rs` khớp 100% với `_apply_agy_normalization` và `build_agy_response` trong `_common.py`.

### 4. [CRITICAL] Thiếu 14/22 cổng kỷ luật trên Rust gây Behavior Drift & điểm mù Parity Test

- **Bằng chứng:** `hooks/rust/tdq-dispatch/src/events/pre_tool_use.rs:9-138`, `tools/patches/gate_guidance.json:31-54`, `tests/test_rust_dispatch_parity.py:65-96`.
- **Trước vs Sau:** Mặc dù `gate_guidance.json` khai báo đủ 22 mã cổng của AGY (`all_agy_codes`), `pre_tool_use.rs` mới cài 4 nhóm (bảo vệ `state.json`, 5 mẫu an toàn `run_command`, overwrite `language_id` cho `start_lsp`, và overwrite `Workspace` cho `invoke_subagent`). Toàn bộ 14 cổng còn lại (`APPROVE`, `TEAM`, `VUNG`, `ZERO-POPUP`, `READONLY`, `SEARCH`, `DOC`, `OUTPUT`, `LOG`, `DOD`, `TICK`, `ANCHOR`, `WORKTREE`, `QC`) cùng logic `blast_radius` guard (`lsp_gate.py:94-133`) và `rtk rewrite` (`command_gate.py:84-97`) bị bỏ trống. Trong khi đó, `test_rust_dispatch_parity.py` chỉ kiểm 9 ca đơn giản và so sánh mỗi trường `decision` (`allow`/`deny`), không kiểm `PreInvocation`, `PostInvocation`, `injectSteps`, `reason` hay 14 cổng còn thiếu.
- **Kịch bản sai behavior thực tế:** Hành vi giữa chế độ mặc định (Rust) và fallback (`TDQ_HOOK_ENGINE=python`) lệch nhau hoàn toàn; người dùng tắt hoặc bật dự phòng sẽ gặp hai bộ luật khác hẳn nhau, gây Behavior Drift nghiêm trọng nhưng bài test parity vẫn báo 100% PASS.
- **Hướng khắc phục:** Chuyển toàn bộ các hard gates và luật cốt lõi sang Rust hoặc định tuyến sự kiện còn thiếu về dispatcher chuẩn, đồng thời mở rộng `test_rust_dispatch_parity.py` phủ đủ 22 mã cổng và toàn bộ schema JSON đầu ra.

### 5. [HIGH] Mềm hóa Working Log (`TDQ:LOG`) và `TDQ:DOD` ở `Stop` gate

- **Bằng chứng:** `tools/patches/agy_hooks.py:2365-2376`, `plugins/tdq-workflow-agy/hooks/scripts/stop_gate.py:337-347, 398-413`.
- **Trước vs Sau:** Trên Claude Code, kết thúc lượt sau khi sửa repo mà chưa cập nhật `docs/workinglog/YYYY-MM-DD.md` sẽ bị `stop_block` chặn bắt chạy `tdq_finish.py` ngay trước khi trả lời user. Khi chuyển sang AGY (`R1–R3`), `_patch_stop_gate` bọc cả nhánh `TDQ:LOG` và `_dod_hint` thành `queue_remind`, còn Rust hoàn toàn không kiểm tra `docs/workinglog/` hay bảng DoD.
- **Kịch bản sai behavior thực tế:** Bởi vì `queue_remind` chỉ được xả ở `PreInvocation` của lượt *tiếp theo*, model vẫn kết thúc lượt và báo "Xong" cho người dùng dù nhật ký công việc chưa ghi và các ô DoD trong plan chưa được tick `[x]`.
- **Hướng khắc phục:** Khôi phục `stop_block` (`decision: "continue"`) khi repo thật sự có thay đổi mã nguồn/kịch bản nhưng thiếu bản ghi working log hoặc còn checkbox DoD mở khi `phase=report` và QC đã PASS.

### 6. [HIGH] Lỗ hổng thoát sớm `continuationActive` ở `Stop` và sai lệch `stop_streak` trên Rust

- **Bằng chứng:** `plugins/tdq-workflow-agy/hooks/scripts/stop_gate.py:299-312`; `hooks/rust/tdq-dispatch/src/events/stop_streak.rs:41-64`.
- **Trước vs Sau:** Tại `stop_gate.py:299-302`, khi `is_agy()` và `cont_active` (`continuationActive` / `stop_hook_active`) đều đúng, hook gọi `mark_turn_closed` rồi **`return` ngay lập tức**, biến nhánh kiểm tra ở dòng 309 (`if lap_lai and _chan_chua_xong(...)`) thành dead code vĩnh viễn! Trong khi đó, bên Rust `stop_streak.rs:41-64` lại không kiểm `dispatched_count` (`[>]` khi subagent đang chạy), không kiểm tra `continuationActive`, dùng card `"INTAKE"` thay vì `"STUCK"`/`"UNFINISHED"` khi `dem > 3`, và trả về `additional_context` mà AGY không đọc.
- **Kịch bản sai behavior thực tế:** Trên Python AGY, chỉ cần bị `Stop` chặn đúng 1 lần (khiến runtime bật `continuationActive=True` ở lượt kế tiếp), model dừng lại lần thứ 2 là lọt qua `Stop` gate dù plan vẫn còn nhiều task `[ ]` — đây là lý do user phải nhắn `"tiếp tục"` nhiều lần để đẩy agent làm tiếp. Trên Rust, khi đang chờ subagent (`[>]`) mà model dừng lại chờ thông báo, `stop_streak.rs` lại tính `[>]` hoặc mở nhắc sai pha.
- **Hướng khắc phục:** Loại bỏ `return` sớm tại dòng 302 của `stop_gate.py` để giữ trần `MAX_STREAK = 3` hoạt động thực chất; đồng bộ `stop_streak.rs` bỏ qua `[>]` (`dispatched_count`) và sửa thẻ hướng dẫn thành `UNFINISHED`.

### 7. [HIGH] Độ trễ kênh nhắc nhở (`queue_remind`) và phân mảnh 2 thư mục `.tdq-runtime`

- **Bằng chứng:** `plugins/tdq-workflow-agy/hooks/scripts/_common.py:659, 1050-1054`, `post_invocation.py:19-26`; `hooks/rust/tdq-dispatch/src/storage.rs:32-36`.
- **Trước vs Sau:** Trên Python AGY, `remind()` ở `PreToolUse`/`Stop` không phát trực tiếp ngay trong lượt mà đẩy vào hàng đợi `docs/tdq/.tdq-runtime/pending-reminders-<sid>.jsonl` (rút gọn `<= 200` ký tự) chờ tới `PostInvocation`/`PreInvocation` mới xả (`flush_pending_channels`). Song song đó, Python đọc/ghi vào `docs/tdq/.tdq-runtime/` (`_common.py:659`), còn Rust `get_runtime_dir` lại đọc/ghi vào `.tdq-runtime/` ngay thư mục gốc (`storage.rs:33`), còn `stop_streak.json` lại có thêm một bản ở `.tdq-runtime/stop_streak.json` bên cạnh `docs/tdq/stop_streak.json`.
- **Kịch bản sai behavior thực tế:** Nhắc nhở đến muộn sau khi công cụ đã chạy xong, dễ bị chìm giữa nhiều tool call nối tiếp hoặc bị kẹt vĩnh viễn trong `pending-reminders-default.jsonl` (bằng chứng: file này vẫn còn 1.861 bytes chưa xả ở request trước). Ngoài ra, Rust `PostToolUse` ghi sổ vào `.tdq-runtime/` ở root nên Python không đọc được lịch sử turn/read/search và ngược lại.
- **Hướng khắc phục:** Hợp nhất về một đường dẫn duy nhất `docs/tdq/.tdq-runtime/` ở cả Python và Rust; đồng thời cho phép nhắc nhở quan trọng (`TICK`, `APPROVE`, `LOG`) phản hồi ngay tại điểm vi phạm thay vì xếp hàng chờ.

### 8. [MEDIUM-HIGH] Nới lỏng tìm kiếm 3 tầng (`TDQ:SEARCH` Option A & `malformed allow`) + thu hẹp `PostToolUse`

- **Bằng chứng:** `tools/patches/agy_hooks.py:1918-1920`, `plugins/tdq-workflow-agy/hooks/scripts/search_gate.py:200-222`; `plugins/tdq-workflow-agy/hooks.json:92`; `hooks/rust/tdq-dispatch/src/events/post_tool_use.rs:42-52` đối chiếu `dispatch.py:149-153`.
- **Trước vs Sau:** Luật gốc buộc agent đi qua LSP/Graphify trước khi grep liên tiếp. Sau `R1–R3`, `search_gate.py` bật ân xá lần đầu (`agy_search_grace`) cho mọi grep vi phạm, và tự động cho qua toàn bộ lệnh shell phân tích thất bại (`agy_malformed_allow`, chỉ nhắc nhẹ ở `implement`/`qc`). Tại `hooks.json:92`, `PostToolUse` loại bỏ `run_command` nên khi agent chạy `graphify query` bằng `run_command`, `tdq-dispatch` không được gọi để ghi nhận lịch sử khái niệm (và bản thân `post_tool_use.rs:42-52` cũng không nhận dạng `graphify` trong tên lệnh shell).
- **Kịch bản sai behavior thực tế:** Agent có thể lạm dụng `grep_search`/`find_by_name` hoặc lệnh PowerShell phức tạp để né hoàn toàn `TDQ:SEARCH`, bỏ qua bước truy vấn LSP (`find_references`/`find_symbol`) và Graphify (`affected`), tăng nguy cơ sót điểm gọi chéo khi refactor.
- **Hướng khắc phục:** Khôi phục ghi nhận `graphify` từ `run_command` khi cần, thu hẹp `agy_malformed_allow` cho các mẫu tìm kiếm rõ ràng (`rg`, `grep`, `Select-String`) và bổ sung kiểm soát `TDQ:SEARCH` cơ bản vào Rust.

### 9. [MEDIUM-HIGH] Tắt bơm luật Clean Code định kỳ (`TDQ:RULE`, `TDQ:GON`, `TDQ:QC`) & cắt cứng 1.500 byte UTF-8 trên Rust

- **Bằng chứng:** `tools/patches/agy_hooks.py:1805-1811`, `plugins/tdq-workflow-agy/hooks/scripts/edit_gate.py:310-318`, `prompt_context.py:496-498`; `hooks/rust/tdq-dispatch/src/events/session_start.rs:45-52`.
- **Trước vs Sau:** `_patch_edit_gate` tắt hoàn toàn cảnh báo `TDQ:RULE:PY/TS/JS` trên AGY (`if not is_agy()`), còn `prompt_context.py:496` bỏ qua `_nhac_gon` và `_nhac_qc` khi `agy_mode=True`. Ở chiều Rust, `session_start.rs:45-52` đọc `skills/tdq-build/references/rules/chung.md` (sai đường dẫn khi chạy từ thư mục cài đặt plugin vốn nằm dưới `plugins/tdq-workflow-agy/` hoặc thiếu `skills/`) và cắt cứng `&rules_content[..1500]`: 1.500 byte đầu của `chung.md` chỉ mới tới mục `## Sources` (chưa chạm tới 7 bậc thang gọn ở dòng 76), lại tiềm ẩn nguy cơ panic Rust nếu byte thứ 1.500 rơi đúng giữa ký tự UTF-8 tiếng Việt nhiều byte.
- **Kịch bản sai behavior thực tế:** Trong các phiên dài có compaction (như `step 2106`), model mất nhắc nhở `TDQ:GON` và `TDQ:QC`, dễ viết hàm dài, trùng logic hoặc quên kiểm tra `SOLID`. Đồng thời nếu `rules_content` chứa tiếng Việt quanh vị trí byte 1500, `SessionStart` trên Rust sẽ panic.
- **Hướng khắc phục:** Bơm lại 1 dòng nhắc `[TDQ:GON]`/`[TDQ:QC]` vào pha `implement`/`qc` ngay sau compaction và đầu lượt user mới; sửa `session_start.rs` tìm đúng path tương đối với plugin binary và cắt chuỗi an toàn bằng `char_indices()`.

### 10. [MEDIUM-HIGH] Lỗ hổng vượt cổng qua Shell (`run_command`), sót `qc-tester` trong `READONLY` và Overwrite không bọc `Arguments`

- **Bằng chứng:** `plugins/tdq-workflow-agy/hooks/scripts/edit_gate.py:153, 182`, `bash_gate.py:173`, `hooks/rust/tdq-dispatch/src/events/pre_tool_use.rs:90-134`, `_common.py:573-586`, `subagent_dispatch_gate.py:8, 40-45`.
- **Trước vs Sau:** Comment `ponytail:` tại `edit_gate.py:153, 182` thừa nhận kiểm tra `TDQ:TEAM` và `TDQ:APPROVE` chỉ áp dụng cho `edit_file`/`write_file`, còn ghi file bằng shell (`py -3 -c`, `Set-Content`, `Out-File`, `>`) đi qua `run_command` sẽ lọt lưới (bằng chứng thực tế xảy ra ngay ở `step 1803` của request trước). Trong `bash_gate.py:173`, danh sách chặn subagent chỉ đọc ghi file qua shell chỉ gồm `("reviewer", "browser")`, bỏ sót `"qc-tester"` (khác với `edit_gate.py:97` có đủ 3 vai trò). Ngoài ra, `pre_tool_use.rs:90-134` khi auto-overwrite `start_lsp` không đọc `.tdq-lsp-module.json`, không bọc `"Arguments"` khi gọi qua `call_mcp_tool` (dù `_common.py:573-586` phải xử lý rất kỹ phần này cho MCP), và phần `invoke_subagent` bỏ qua kiểm tra 5 trường bắt buộc (`TASK:`, `WORKTREE:`, `VÙNG FILE:`, `TEST:`, `TRẢ VỀ:`).
- **Kịch bản sai behavior thực tế:** Một tác vụ hoặc subagent có thể dùng `run_command` ghi đè mã nguồn bất chấp khóa vùng `Chạm:` hoặc khóa duyệt `APPROVE`; `qc-tester` có thể sửa code qua shell; còn `call_mcp_tool` gọi `start_lsp` thiếu `language_id` khi nhận `overwrite` phẳng từ Rust có thể làm hỏng cấu trúc tham số lồng nhau của Antigravity.
- **Hướng khắc phục:** Bổ sung `"qc-tester"` vào `bash_gate.py:173`; kiểm tra shell mutator ở `run_command` khi đang bị khóa `APPROVE`/`TEAM`; nâng cấp `pre_tool_use.rs` bọc `Arguments` đúng chuẩn `call_mcp_tool` và đọc `.tdq-lsp-module.json`.

---

### Lộ trình ưu tiên khắc phục khuyến nghị

| Đợt | Mục tiêu xử lý | Các điểm vá chính |
|---|---|---|
| **P0 (Khẩn cấp)** | Đóng toàn bộ lỗ hổng nhảy sự kiện & lệch giao thức trên Rust binary | (1) Hỗ trợ `PreInvocation` & `PostInvocation` trong `main.rs`; (2) Chuẩn hóa input/output JSON theo AGY 2.0 (`injectSteps`, `reason`, `workspacePaths`, `toolInput`, `write_to_file`/`replace_file_content`); (3) Chuyển tiếp hoặc cài đặt các hard gate thiếu trên `pre_tool_use.rs` (`APPROVE`, `TEAM`, `VUNG`, `ZERO-POPUP`, `READONLY`, `TICK`) |
| **P1 (Siết kỷ luật lõi)** | Dứt điểm lỗi quên tick plan, quên working log và vòng lặp dừng sớm | (1) Khôi phục `block` cho `TDQ:TICK` ở `edit_gate` & `stop_gate`; (2) Sửa `return` sớm tại `stop_gate.py:300` với `continuationActive`; (3) Thống nhất 1 thư mục `docs/tdq/.tdq-runtime/` giữa Python và Rust; (4) Thêm `"qc-tester"` vào `bash_gate.py:173` và sửa cắt UTF-8 ở `session_start.rs` |
| **P2 (Khóa hồi quy)** | Ngăn Behavior Drift quay lại sau mỗi lần tối ưu | (1) Mở rộng `tests/test_rust_dispatch_parity.py` kiểm phủ đủ 22 mã và payload AGY 2.0 thật; (2) Bơm lại `[TDQ:GON]`/`[TDQ:QC]` định kỳ sau compaction; (3) Ghi nhận `graphify` qua `run_command` trong `PostToolUse` |
<!-- tdq-archify-binding:start -->
<!-- manifest: 2026-11-19-1457-audit-sai-sot-noi-hook.manifest.json -->
<!-- manifest_digest: 9d6bcdd16bd67f9978cce8b40094107802b33ed958b38237c512b7a6f6dcd065 -->
<!-- tdq-archify-binding:end -->