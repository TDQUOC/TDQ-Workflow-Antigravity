# BRIEF — Fix Subagent Tools Registry & Bump Version Update

Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

## Nguyên văn

> okqy mở request fix triệt để và bump verupdate cho tôi

**Đọc hiểu ban đầu (triage từ mô phỏng live sau restart Antigravity `0.103.0`):**
- **Mục tiêu:** Sửa triệt để lỗi runtime khiến cả `8/8` subagent của plugin `tdq-workflow-agy` (`tdq-build-resolver`, `tdq-debugger`, `tdq-explorer`, `tdq-implementer`, `tdq-qc-tester`, `tdq-refactor-cleaner`, `tdq-reviewer`, `tdq-security-reviewer`) không khởi tạo được executor trên Antigravity 2.0, kèm test khóa chống hồi quy, bump version (`patch`/`minor`), release và cập nhật lại bản cài đặt local.
- **Triệu chứng & bằng chứng đã tái hiện:** Khi gọi `invoke_subagent(TypeName="tdq-explorer")` sau restart Antigravity, runtime trả lỗi nguyên văn `failed to construct executor: failed to resolve components: unknown component: tool "call_mcp_tool" not found in registry`. Toàn bộ `8/8` file trong `plugins/tdq-workflow-agy/agents/` và `C:\Users\admin\.gemini\config\plugins\tdq-workflow-agy\agents\` do `tools/patches/skills_and_agents.py:28-47` sinh ra đều chứa `"call_mcp_tool"` cùng các tên tool chưa khớp registry (`grep_search`, `find_by_name`, `list_dir`), cộng lỗi lặp chuỗi `write_file` ở `tdq-explorer.md:14`.
- **Phạm vi dự kiến:**
  - Đối chiếu danh sách tool thực tế trong registry Antigravity 2.0 và chuẩn hóa `_READONLY_TOOLS` / `_WRITER_TOOLS` (và `tdq-explorer.md`) trong `tools/patches/skills_and_agents.py`, cập nhật bộ test `tests/test_agent_frontmatter.py` + `tests/test_agy_plugin_validate.py`.
  - Rebuild `plugins/tdq-workflow-agy/`, kiểm chứng gọi thật subagent trên Antigravity, bump version mới, đồng bộ tài liệu/release local và cập nhật user-level `~/.gemini/`.
- **Điểm cần chốt rõ ở pha phân tích/phỏng vấn:**
  - Số phiên bản đích (`0.103.1` patch hay `0.104.0`), có cần biên dịch lại Rust 3 OS qua SSH nếu không đổi code Rust hay không, phạm vi xuất nhánh `main` + tag local và chỉ cập nhật Antigravity user-level hay thêm host khác.

## Hiểu & kiến thức

- **Nguyên nhân gốc (Point-of-Commitment):** Tại commit `4859058b` (`2026-11-20`), `tools/patches/skills_and_agents.py:28-47` đổi cấu hình `tools` của `8/8` subagent Antigravity sang `_READONLY_TOOLS` / `_WRITER_TOOLS` có thêm `call_mcp_tool`, `grep_search`, `find_by_name`, `list_dir`, đồng thời `tests/test_agent_frontmatter.py:34` khóa `AGY_DISCOVERY_TOOLS = {"read_file", "grep_search", "find_by_name", "list_dir"}`. Trên Antigravity 2.0, `call_mcp_tool` không có trong registry executor của subagent (`unknown component: tool "call_mcp_tool" not found in registry`), còn `grep_search` / `find_by_name` / `list_dir` cũng không tồn tại trên runtime Antigravity 2.0 (`docs/AUDIT-AND-PORTING-PLAN.md:102`, `migrate-agent-settings/SKILL.md:157-161`).
- **Lỗi phụ đi kèm:** `agents/tdq-explorer.md:15` viết ``(`Write`/`Edit`/`write_file`)`` nên khi `_rewrite_skill_text` dịch `` `Write` `` thành `` `write_file` `` đã sinh chuỗi lặp ``(`write_file`/`edit_file`/`write_file`)`` trong bản build AGY.
- **Lý do bỏ qua Tier-1 Scope round (`scope-round.md`):** Phạm vi đã khu trú rõ ngay từ lỗi runtime tái hiện thực tế (`invoke_subagent`) và yêu cầu rõ của người dùng (fix triệt để + bump version update), nên đi thẳng vào vòng hỏi chi tiết chốt phương án.

### Năng lực dùng được

Kiểm kê ngày 2026-11-21: `42` skill trên đĩa (`23` khớp bộ lọc từ khóa, ẩn `19` skill khác lĩnh vực), cộng `12` skill built-in trong context.

| Skill | Nguồn | Phán quyết | Dùng ở đâu / Lý do loại |
|---|---|---|---|
| `tdq-conventions`, `tdq-intake`, `tdq-spec`, `tdq-plan`, `tdq-build`, `tdq-status`, `tdq-check-status`, `tdq-lean` | `plugin:tdq-workflow-agy` | `NỀN` | Luật định dạng, pipeline `full` `bugfix`, git safety, `doc_lint` và kiểm chứng |
| `tdq-setup`, `tdq-checkportable` | `plugin:tdq-workflow-agy` | `DÙNG` | Kiểm chứng bậc tìm kiếm và tính toàn vẹn gói plugin sau cài đặt |
| `agy-customizations`, `migrate-agent-settings`, `antigravity-guide`, `plugin` | `built-in` | `DÙNG` | Chuẩn frontmatter subagent, bảng ánh xạ tên tool hợp lệ và cấu trúc plugin `~/.gemini/` |
| Đã xét các skill còn lại (`tdq-browser-*`, `19` skill ẩn trên đĩa và `8` skill built-in khác) | `user` / `plugin` / `built-in` | `KHÔNG` | khác lĩnh vực |

### Khảo sát 3 chiều (Grep · LSP · Graphify)

| Vùng file chạm | Phát hiện qua lớp nào (Grep/LSP/Graphify) | Tác động & quan hệ |
|---|---|---|
| `tools/patches/skills_and_agents.py` (`L28-47`, `AGENT_FRONTMATTERS`, `transform_agents`) | Grep + LSP `find_references` (`3` refs) + Graphify `affected` (`tools/build_agy_plugin.py:242,279`) | Nơi sinh `8/8` file `agents/tdq-*.md` cho `plugins/tdq-workflow-agy/`; cần giữ nguyên notice `[TDQ:READONLY]` / `[TDQ:SCOPED-WRITE]` / `[TDQ:QC-SCOPED]` |
| `agents/tdq-explorer.md` (`L15`) | Grep + đọc trực tiếp | Sửa ``(`Write`/`Edit`/`write_file`)`` để bản biên dịch AGY không lặp `write_file` |
| `tests/test_agent_frontmatter.py` (`L34`, `L120-144`) & `tests/test_agy_plugin_validate.py` | Grep + đọc trực tiếp | Cập nhật `AGY_DISCOVERY_TOOLS` theo registry Antigravity và thêm test âm tính cấm `call_mcp_tool` / `grep_search` / `find_by_name` / `list_dir` trong `tools:` của agent |
| `plugins/tdq-workflow-agy/` & cụm manifest/version (`.claude-plugin/plugin.json`, `.codex-plugin/plugin.json`, `tools/patches/agy_manifests.py`, `tools/patches/__init__.py`, `tools/build_agy_plugin.py`, `CHANGELOG.md`, `README.md`, `UPSTREAM-TRACE.md`) | Grep + đọc trực tiếp | Build lại gói `tdq-workflow-agy`, đồng bộ version phát hành mới (`CHANGELOG.md <= 500` dòng theo `docs/kien-truc.md`), giữ nguyên `skills/` dùng chung 4 host và tách riêng khỏi `hooks/` (vẫn giữ `call_mcp_tool`/`grep_search` cho hook của agent chính) |

### Lộ trình

| Bước/phase | Chạy? | Vì sao |
|---|---|---|
| Phỏng vấn chi tiết (Vòng 1) | CÓ | Chốt phương án danh sách tool chuẩn, version bump/Rust 3 OS, phạm vi release/user-level và `muc_qc` |
| Nghiên cứu web bổ sung | BỎ | Đã hoàn tất xác minh root cause, `migrate-agent-settings/SKILL.md` và web Antigravity ngay trong pha `analyze` |
| QC & Kiểm chứng thực thi | CÓ | Xác nhận mọi test + gọi thật `invoke_subagent` sau khi build & cài `~/.gemini/` không còn lỗi `unknown component` |

## Hỏi đáp

### Vòng 1 (đã chốt)

> Nguyên văn trả lời: `1a 2b 3a 5a có thể nhiều worker 5a`

1. Chuẩn hóa danh sách tool cho `8` subagent Antigravity → **`1a` (Chuẩn Antigravity chính thức):** Bỏ `call_mcp_tool`, `grep_search`, `find_by_name`, `list_dir`; cấp `["read_file", "run_command", "manage_task", "send_message"]` cho `tdq-security-reviewer` và `["read_file", "edit_file", "write_file", "run_command", "manage_task", "search_web", "send_message"]` cho `7` agent còn lại; sửa lặp `write_file` ở `agents/tdq-explorer.md:15`; thêm test khóa cấm tool ngoài registry.
2. Phiên bản đích & Rust 3 OS → **`2b` (`0.103.1` + rebuild 3 OS):** Nâng đồng bộ `Cargo.toml` và toàn bộ manifest/tài liệu lên `0.103.1`, biên dịch + test + dọn sạch lại `0` tàn dư cả `3` OS thật (Windows local + SSH song song `ubuntu-100-95` Linux `musl` & `mbair` macOS `arm64`).
3. Phạm vi xuất bản Git & local → **`3a` (`~/.gemini/` + local `main`/tag `v0.103.1`):** Cập nhật chỉ Antigravity user-level (`C:\Users\admin\.gemini\config\plugins\tdq-workflow-agy`, giữ nguyên Caveman/RTK, không chạm `~/.claude/` hay `~/.codex/`); sau khi duyệt commit + merge `dev` sẽ xuất nhánh local `main` (`--sinh-main`) + gắn tag local `v0.103.1` (tuyệt đối không `git push`).
4. Mức QC (`muc_qc`) → **`full` + nhiều worker:** Người dùng giữ mặc định `full`, bổ sung test gọi thật subagent trên Antigravity và chạy `tdq_test.py tron-bo` nhiều worker (`--workers 6 --fresh --reuse off`, phương án dự phòng `--workers 2`/`1` nếu có va chạm lock).
5. Bổ sung thêm → **`5a`:** Không bổ sung thêm.
