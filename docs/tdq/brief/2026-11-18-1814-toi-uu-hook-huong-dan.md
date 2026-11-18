# BRIEF — Tối ưu hiệu năng lõi hook, chuyển sang chỉ dẫn 4 phần & dọn cổng (R1+R2+R3)
Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

## Nguyên văn

> okay hãy lập request làm R1 + R2 + R3

**Đọc lần đầu (kế thừa từ báo cáo nghiên cứu `docs/tdq/research/2026-11-18-1346-scan-hook-anh-huong-runtime.md`):**
- **Mục tiêu:** Triển khai trọn bộ 3 cụm cải tiến hook TDQ (`R1 + R2 + R3`) đã đo đạc ở request `2026-11-18-1346-scan-hook-anh-huong-runtime`:
  - **R1 (Hiệu năng lõi & cache lượt):** Hợp nhất thành 1 tiến trình điều phối / sự kiện (`hooks/scripts/dispatch.py`), cấu hình `hooks.json` gọi trực tiếp đường dẫn `python.exe` (có fallback `py -3`), cache `git status` & `repo_root` theo `mtime_ns`/`size` của `.git/index` & `.git/HEAD` trong `turn_snapshot`, và tắt bơm lặp dòng `"[TDQ:NEXT] (same as last turn — unchanged)"` + `[TDQ:GON]` ở `PreInvocation`. Mục tiêu: `PreInvocation <= 150 ms`, `PreToolUse <= 100 ms`.
  - **R2 (Làm mềm cổng & thẻ `metadata.user_markdown` 4 phần):** Giữ `9` cổng chặn cứng an toàn/duyệt (`APPROVE`, `GIT`, `TEAM`, `STATE`, `READONLY`, `VUNG`, `ZERO-POPUP`, `SUBAGENT`, `UNFINISHED`); bật `allow` + `overwrite` tự điền `language_id` / `scope="exported"` cho `TDQ:LSP` (và xem xét `Workspace="inherit"` cho `SUBAGENT`); chuyển `12` cổng (`SEARCH` fail-open khi `malformed`, `TICK` bỏ chặn `STREAK_NGUONG=3`, `DOC`, `LOG` trừ `docs/.staging*`, `OUTPUT`, `SETUP`, `GON`, `NEXT`, `WORKTREE`, `ANCHOR`, `DOD`, `INTAKE`) sang hàng đợi nhắc mỗi lượt, gom thành `1` thẻ `metadata.user_markdown` theo khung 4 phần (*Chuyện gì · Vì sao · Làm gì tiếp · Bỏ qua hợp lệ*) cho user + `1` dòng ngắn cho model.
  - **R3 (`Stop` 1 lần & dọn `tdq-lean`):** Dùng cờ `continuationActive` của Antigravity trong `stop_gate.py` để ép tiếp tối đa `1` lần/lượt; xóa `7` mã thừa (`ASK`, `DEVTOOL`, `FEEDBACK`, `GATE`, `QC`, `RULE`, `STUCK`) và `3` script mồ côi (`doc_file_gate.py`, `strategic_compact_gate.py`, `stop_batch_checker.py`); biên dịch lại `plugins/tdq-workflow-agy/`, cập nhật `token-budget.json` / `APPROVED_RUNTIME_MODULES` và kiểm chứng hồi quy.
- **Phạm vi:** `hooks/scripts/*.py`, `hooks/hooks.json`, `scripts/tdq_state.py`, `scripts/search_rules.py`, `tools/patches/agy_hooks.py`, `tools/patches/agy_manifests.py`, `tools/install_agy_plugin.py`, `plugins/tdq-workflow-agy/**`, `tests/test_*`.
- **Chỗ chưa rõ cần chốt ở phỏng vấn:** (1) Giữ tương thích song song cho Claude Code / Codex (`hooks/hooks.json` & `.codex/hooks.json`) thế nào khi xóa 7 mã & thêm `dispatch.py`; (2) `SUBAGENT` có tự `overwrite` `Workspace="inherit"` hay giữ chặn; (3) Có cập nhật luôn bản cài local `~/.gemini/config/plugins/tdq-workflow-agy` và chạy lại `bench_hooks.py` + `false_positive_repro.py` đối chứng trước/sau không.

## Hiểu & kiến thức

### Năng lực dùng được

| Năng lực | Nguồn | Phán quyết |
|---|---|---|
| `agy-customizations (docs/hooks.md)` | built-in | DÙNG — hợp đồng `overwrite`, `metadata.user_markdown`, `continuationActive`, `invocationNum` |
| `tdq-lean` | plugin:tdq-workflow-agy | DÙNG — cắt 7 mã thừa & loại 3 script mồ côi khỏi gói AGY |
| `tdq-conventions` | plugin:tdq-workflow-agy | DÙNG — i18n (code/chuỗi máy tiếng Anh, tài liệu user tiếng Việt), Soul, Archify |
| `tdq-browser-test`, `tdq-browser-research` | plugin | BỎ — không có UI web |
| `tavily-primary` | MCP | BỎ — nghiên cứu & tài liệu chính thức đã đầy đủ tại `docs/tdq/research/2026-11-18-1346-scan-hook-anh-huong-runtime.md` |

### Khảo sát 3 chiều & Phát hiện kỹ thuật cốt lõi

1. **Nguyên nhân sâu hơn ở `prompt_context.py` (`hooks/scripts/prompt_context.py:277-281`):**
   Trên Claude Code, `prompt_context.py` gắn `UserPromptSubmit` (1 lần / tin nhắn user). Khi gắn sang `PreInvocation` của Antigravity, nó chạy **trước mọi lần gọi model trong cùng 1 lượt** (`invocationNum = 1, 2, 3...`), vừa gọi `turn_snapshot(cwd)` (`3` lệnh `git`, `212 ms`) lặp lại hàng chục lần, vừa gọi `turn_log_clear(cwd, sid)` xóa sổ giữa lượt! Chỉ chạy `turn_log_clear` + `turn_snapshot` ở đầu lượt (`invocationNum <= 1` hoặc `lastUserInput` đổi) kết hợp cache `.git/index` + `.git/HEAD` theo `mtime_ns`/`size` sẽ kéo `PreInvocation` ở các bước tiếp theo xuống ~`40–50 ms` và sửa luôn lỗi xóa sổ giữa lượt.
2. **Ràng buộc test hiện có (tránh vỡ suite `4.350` ca):**
   - `tests/test_agy_plugin_validate.py:30-37`: khóa `components["hooks"] == 6` (giữ nguyên 6 nhóm top-level trong `hooks.json`, nhưng mỗi nhóm chỉ gọi `dispatch.py --event <Event>` -> 1 tiến trình/sự kiện) và `L60` cấm dấu `"` trong chuỗi `command` (`cmd /c` làm vỡ nháy). Đo trên máy: `cmd /c python -X utf8 -c pass` mất `39,0 ms` vs `py -3` `56,3 ms` (`-17,3 ms`, không cần dấu nháy).
   - `tests/test_stop_batching.py`, `test_an_cua_so_windows.py`, `test_tcas_ast.py`: đang import trực tiếp `stop_batch_checker.py`, `strategic_compact_gate.py`, `doc_file_gate.py` từ `hooks/scripts/`. Nếu loại 3 script này khỏi bản biên dịch `plugins/tdq-workflow-agy/` (hoặc hỏi user có xóa cả test cũ ở upstream không) sẽ tránh làm đỏ test ngoài ý muốn.
   - `docs/kien-truc.md:52-56`: `scripts/i18n_check.py` bắt buộc code/chuỗi máy trong `hooks/` & `scripts/` viết bằng tiếng Anh (trừ dòng có `# i18n-allow`); riêng thẻ `metadata.user_markdown` hiển thị cho user có thể định dạng theo `doc_lang` hoặc gắn `# i18n-allow` đúng quy ước.
   - `tools/patches/agy_hooks.py` đã có sẵn `begin_collapsed_session`, `set_overwrite`, `queue_remind`, `flush_pending_reminders` — `dispatch.py` có thể nạp in-process đúng gate cần thiết theo `event` & `tool_name` mà không spawn tiến trình con.

### Bảng đối chiếu vùng chạm (Triangulation)

| Vùng file chạm | Phát hiện qua lớp nào (Grep/LSP/Graphify) | Tác động & quan hệ |
|---|---|---|
| `scripts/tdq_state.py` (`turn_snapshot`, `repo_status_digest`) | Graphify (`community=99/24`) + Grep | Thêm cache theo `mtime_ns`/`size` của `.git/index` & `.git/HEAD` (hub — bán kính test lớn) |
| `scripts/search_rules.py` (`_tach_script`, `_bo_heredoc`) | Grep + T1.3 repro | Sửa parse PowerShell `@'...'@`, escape `` `n `` và backtick trong nháy kép để hết `85` ca `malformed` |
| `hooks/scripts/prompt_context.py`, `stop_gate.py`, `lsp_gate.py`, `edit_gate.py`, `read_gate.py`, `_common.py` | Graphify (`community=5/40/91/111`) + Grep | Phân biệt `invocationNum`, cờ `continuationActive`, `overwrite` `LSP`, bỏ chặn `STREAK_NGUONG=3`, khung 4 phần |
| `tools/patches/agy_hooks.py`, `tools/patches/agy_manifests.py`, `tools/build_agy_plugin.py`, `tools/install_agy_plugin.py` | Grep + đọc trực tiếp | Sinh `hooks/scripts/dispatch.py`, gộp `hooks.json` 1 tiến trình/sự kiện (`python -X utf8`), xuất `metadata.user_markdown`, lọc bỏ 3 script mồ côi & 7 mã thừa trên AGY |
| `plugins/tdq-workflow-agy/**`, `docs/tdq/token-budget.json` | Grep (`test_agy_plugin_validate.py`) | Bản biên dịch plugin Antigravity 2.0 + khóa token budget |
| `tests/test_agy_hooks.py`, `tests/test_agy_plugin_validate.py`, `tests/test_build_portable.py` (+ test mới `test_hook_dispatch_r1_r3.py`) | Grep | Kiểm chứng R1+R2+R3, `APPROVED_RUNTIME_MODULES`, giữ xanh suite hiện hữu |

Vòng phạm vi (`scope-round.md`): BỎ — phạm vi R1 + R2 + R3 đã được định lượng và chốt rõ từ báo cáo nghiên cứu trước; đi thẳng vào câu hỏi chi tiết thiết kế.

### Quyết định đã chốt (2026-11-18 18:49)

- **Phạm vi host (1a):** Sửa lỗi/tối ưu dùng chung ở lõi (`scripts/tdq_state.py` cache `.git/index` & `.git/HEAD`, `scripts/search_rules.py` sửa PowerShell `@'...'@`/escape `` `n ``/backtick trong chuỗi) và áp trọn bộ `dispatch.py` + làm mềm `12` cổng + `metadata.user_markdown` 4 phần + `Stop` `continuationActive` + loại bỏ `7` mã & `3` script mồ côi trên **gói plugin Antigravity 2.0** (`tools/patches/` → `plugins/tdq-workflow-agy/`), giữ nguyên tương thích ngược cho các unit test Claude Code / Codex cũ; cập nhật `tests/test_hooks_dual_protocol.py` khớp hợp đồng AGY mới.
- **Lệnh gọi Python trong `hooks.json` (2b):** Dùng thống nhất `python -X utf8 hooks/scripts/dispatch.py --event <Event>` (không nháy kép, portable, không ghi đường dẫn riêng của máy).
- **Tự sửa `allow` + `overwrite` (3a):** Áp dụng cho cả `TDQ:LSP` (tự điền `language_id` theo project, ép `scope="exported"`, `include_transitive=False`) và `TDQ:SUBAGENT` (khi prompt có `WORKTREE:` mà truyền `Workspace="branch"|"share"` thì tự đổi sang `Workspace="inherit"`).
- **Bản cài local (4b):** Chỉ biên dịch và kiểm chứng trong repo (`plugins/tdq-workflow-agy/`) + thư mục tạm; **không cài đè lên `~/.gemini/config/plugins/tdq-workflow-agy`** cho tới khi user yêu cầu. Đo đối chứng Trước/Sau chạy thẳng trên `plugins/tdq-workflow-agy/`.
- **Mức QC (5c):** `ultra` — DoD + trọn bộ unit test (`tdq_test.py tron-bo`) + hồi quy vùng chạm + ràng buộc kiến trúc + clean code + smoke test + runtime test (cap `120s`) + agent `tdq-qc-tester` độc lập soi lại.
- **Vá từ self-recheck trước khi duyệt spec (`vá hết + A`, 2026-11-18 19:21):**
  - Chốt **Hướng A** cho `TDQ:SEARCH`: `malformed` và pha `analyze`/`spec` cho chạy 100%; ở `implement`/`qc`, lần tìm kiếm chưa qua LSP/Graphify đầu tiên cho `allow` + đẩy thẻ 4 phần ("ân xá 1 lần"), lần 2 liên tiếp vẫn grep mù hoặc `rtk bypass grep` mới chặn `deny`.
  - Nhận diện lượt user mới bằng vị trí dòng `USER_INPUT` cuối trong `transcriptPath` / cờ `turn_closed` từ `Stop` (không dùng `invocationNum <= 1` + prompt cũ để tránh nuốt `[TDQ:APPROVE]` khi user gõ lặp `"1a"`).
  - Đóng gói `overwrite` cho `call_mcp_tool` bọc đúng vào `Arguments` theo kiểu gốc; chỉ dò ngôn ngữ `O(1)` `< 1 ms` ở thư mục gốc (`lsp_gate`); giữ `turns-<sid>.jsonl` suốt lượt (không xóa giữa lượt) và thu hẹp matcher `PostToolUse` bỏ `run_command|read_file|view_file`; tách `model_line <= 160` và `user_card <= 1.200` ký tự; thêm fallback kiểm tra stub WindowsApps Python lúc cài và dọn rác `.tdq-runtime` > 7 ngày ở `SessionStart`.
- **Phương án đã loại:** xóa thẳng `hooks/scripts/` gốc làm vỡ >400 unit test Claude/Codex cũ (trái 1a); tiêm đường dẫn máy vào `hooks.json` (trái 2b); đổi hook sang Bash/CMD/PowerShell (đã đo chậm hơn `python.exe` `1,6–5,7×` và vỡ JSON).

### Lộ trình

| Bước/phase | CÓ-BỎ | Vì sao |
|---|---|---|
| Research web (`tavily`) | BỎ | Nghiên cứu định lượng & hợp đồng `agy-customizations/docs/hooks.md` đã đầy đủ |
| Interview | CÓ (đã xong) | 5 câu chốt ranh giới host, lệnh `python`, `overwrite`, bản cài local, `muc_qc=ultra` |
| Spec + Archify BA Preview | CÓ | Khung bất biến; có sửa luồng hiện có nên dựng `truoc-sau.archify.md` → `*-preview.html` |
| Plan + chia đợt subagent | CÓ | Khung bất biến; tách vùng file rõ để chạy đội song song |
| Implement + biên dịch `plugins/tdq-workflow-agy` | CÓ | R1 + R2 + R3 trong repo, không đụng `~/.gemini/...` (4b) |
| QC độc lập (`tdq-qc-tester`) + smoke/runtime + `tron-bo` | CÓ | User chọn `muc_qc=ultra` (5c) |
| Report md + Archify HTML | CÓ | Khung bất biến |

## Hỏi đáp

- **1. Phạm vi áp dụng giữa Antigravity 2.0 và Claude/Codex gốc?** → `1a`: tối ưu lõi chung (`tdq_state`, `search_rules`) + áp trọn R1–R3 trên gói Antigravity 2.0, giữ tương thích bộ test Claude/Codex cũ.
- **2. Lệnh gọi Python trong `hooks.json`?** → `2b`: dùng thống nhất `python -X utf8 hooks/scripts/dispatch.py --event ...`.
- **3. Phạm vi `allow` + `overwrite`?** → `3a`: cả `TDQ:LSP` và `TDQ:SUBAGENT`.
- **4. Cài lên máy local?** → `4b`: chỉ build & kiểm trong repo/thư mục tạm, chưa cài đè lên `~/.gemini/config/plugins/tdq-workflow-agy`.
- **5. Mức QC?** → `5c`: `ultra`.
