# RESEARCH — Root Cause Lỗi Registry Tool `call_mcp_tool` & Chuẩn Hóa 8 Subagent Antigravity

Ngày: 2026-11-21 · Request: `2026-11-21-1253-fix-subagent-tools-bump` · Nhánh: `bugfix/fix-subagent-tools-bump`
Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

## 1. Triệu chứng & Tái hiện (Repro)

- Gọi thật `invoke_subagent(TypeName="tdq-explorer")` (`94f8068b-6315-411e-82b4-241e4370759d`) sau khi khởi động lại Antigravity `0.103.0`, hoặc `invoke_subagent(TypeName="tdq-security-reviewer")` (`38de6c64-70ac-47de-93be-b0517e4fb6c8`), hệ thống đều từ chối khởi tạo ngay trước lượt đầu tiên với lỗi nguyên văn:
  `failed to construct executor: failed to resolve components: unknown component: tool "call_mcp_tool" not found in registry`.
- Quét `8/8` tệp tại `plugins/tdq-workflow-agy/agents/tdq-*.md` và `C:\Users\admin\.gemini\config\plugins\tdq-workflow-agy\agents\tdq-*.md` cho thấy cả `8/8` đều liệt kê `call_mcp_tool`, `grep_search`, `find_by_name`, `list_dir` ở dòng `tools:` trong YAML frontmatter.
- Lệnh `agy.EXE plugin validate --strict --json` chỉ kiểm tra cú pháp tệp & schema manifest nên trả `"findings": []`, khiến lỗi này lọt qua bước đóng gói và chỉ nổ ở runtime khi bộ dựng executor của Antigravity ánh xạ từng tên trong `tools:` với registry thật.
- Trước đây `tdq-qc-tester` trong cuộc hội thoại cũ chạy được là do dùng bản lưu cũ tại `.agents/agents/tdq-qc-tester/agent.md` tạo ngày `2026-11-18` (khai báo `[send_message, view_file, search_web, schedule, generate_image, write_file, edit_file, run_command, manage_task]`, không chứa `call_mcp_tool` hay `grep_search`).

## 2. Điểm phát sinh lỗi (Point-of-Commitment)

- Tại commit `4859058b` (`2026-11-20`, `feat(agy-compiler): upgrade AGY plugin compiler for 8 agents, subagent telemetry, and tdq-config`), tác giả thay cặp danh sách hoạt động ở `0.101.0` (`["read_file", "run_command", "send_message"]` và `["read_file", "edit_file", "write_file", "run_command", "send_message"]`) trong `tools/patches/skills_and_agents.py:28-47` bằng `_READONLY_TOOLS` và `_WRITER_TOOLS` có thêm `"grep_search"`, `"find_by_name"`, `"list_dir"`, `"call_mcp_tool"`.
- Cùng lúc, `tests/test_agent_frontmatter.py:34` gán cứng `AGY_DISCOVERY_TOOLS = {"read_file", "grep_search", "find_by_name", "list_dir"}` để khóa hợp đồng ngược, biến tên tool lỗi registry thành điều kiện PASS bắt buộc trong test.
- Lỗi phụ đi kèm: `agents/tdq-explorer.md:15` ghi ``(`Write`/`Edit`/`write_file`)`` nên khi `_rewrite_skill_text()` (`tools/patches/skills_and_agents.py:111-128`) thay `` `Write` `` → `` `write_file` `` và `` `Edit` `` → `` `edit_file` `` đã sinh chuỗi lặp ``(`write_file`/`edit_file`/`write_file`)`` tại `plugins/tdq-workflow-agy/agents/tdq-explorer.md:14`.

## 3. Bằng chứng Danh sách Tool Hợp lệ trên Antigravity 2.0

- **Tài liệu built-in chính thức (`migrate-agent-settings/SKILL.md:146-163`):** Quy định chuẩn ánh xạ `tools:` cho subagent `agents/<name>.md` trên Antigravity 2.0 gồm `[read_file, edit_file, write_file, run_command, manage_task, search_web]` (`Read`/`Glob`/`Grep` → `read_file`, `Edit`/`MultiEdit` → `edit_file`, `Write` → `write_file`, `Bash` → `run_command` và `manage_task`, `WebSearch`/`WebFetch` → `search_web`; thêm `send_message` để subagent trả kết quả cho agent gọi).
- **Đối chiếu thực nghiệm lịch sử (`docs/AUDIT-AND-PORTING-PLAN.md:102`):** Đã chứng minh trên `835` lời gọi tool thật ở `16` `transcript.jsonl` rằng `grep_search`, `find_by_name`, `list_dir` không tồn tại trên Antigravity 2.0.
- **Tài liệu web Antigravity (`antigravity.google` & tham chiếu cộng đồng về lazy MCP):** `call_mcp_tool` là cầu nối MCP ở agent chính, không nằm trong allowlist executor mặc định của subagent; thao tác MCP giữ ở agent chính hoặc chạy CLI chuẩn (`tdq_lsp.py`, `graphify`) qua `run_command`.
- **Kiểm chứng trên thực thể chạy thật (`<subagents>` trong `.agents/agents/`):** Các tên được executor nhận và chạy bình thường gồm `read_file`, `view_file`, `edit_file`, `write_file`, `run_command`, `manage_task`, `search_web`, `send_message`.

## 4. Ranh giới Phạm vi Sửa & Khóa Hồi quy

- **CẦN SỬA:**
  - `tools/patches/skills_and_agents.py:28-47`: Chuẩn hóa `_READONLY_TOOLS` (`["read_file", "run_command", "manage_task", "send_message"]`) và `_WRITER_TOOLS` (`["read_file", "edit_file", "write_file", "run_command", "manage_task", "search_web", "send_message"]`), giữ nguyên `model: inherit` và các notice `[TDQ:READONLY]` / `[TDQ:SCOPED-WRITE]` / `[TDQ:QC-SCOPED]`.
  - `agents/tdq-explorer.md:15`: Gọn thành ``(`Write`/`Edit`)`` để khi biên dịch sang AGY trở thành ``(`write_file`/`edit_file`)`` không lặp `write_file`.
  - `tests/test_agent_frontmatter.py:34, 120-144`: Cập nhật `AGY_DISCOVERY_TOOLS` phù hợp registry thật và bổ sung test âm tính (`test_built_agy_agents_forbid_unregistered_tools`) cấm tuyệt đối `call_mcp_tool`, `grep_search`, `find_by_name`, `list_dir` xuất hiện trong `tools:` của bất kỳ `plugins/tdq-workflow-agy/agents/tdq-*.md` nào.
  - Rebuild `plugins/tdq-workflow-agy/`, kiểm gọi thật subagent qua `invoke_subagent` ngay sau khi build/cài, nâng version mới (`0.103.1` hoặc `0.104.0` theo lựa chọn user) và đồng bộ cài đặt user-level `~/.gemini/`.
- **GIỮ NGUYÊN (KHÔNG SỬA):**
  - `hooks.json`, `tools/patches/agy_hooks.py`, `hooks/rust/tdq-dispatch/`: vẫn giữ matcher và parser cho `call_mcp_tool` và `grep_search` để bảo vệ agent chính (nơi `call_mcp_tool` tồn tại) và giữ nguyên toàn bộ bộ kiểm thử parity Python–Rust hiện có (`test_search_rules.py`, `test_lsp_gate.py`, `test_rust_dispatch_parity.py`).
