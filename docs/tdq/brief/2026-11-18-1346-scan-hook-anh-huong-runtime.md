# BRIEF — Scan ảnh hưởng của hook tới runtime & chuyển hook sang dạng hướng dẫn
Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

## Nguyên văn

> hi hãy giúp tôi check và scan xem bộ workflow này có bị ảnh hưởng bởi hook ko. gần đây có rất nhiều case chạy rất lâu thấy bump hook rất nhiều hãy check kĩ và report cho tôi là liệu hook có gây ảnh hưởng tới runtime time ko và có cách nào xử lí lại hook trực quan hơn mang tính hướng dẫn hơn thay vì cứ block hoài không

**Đọc lần đầu:**
- Mục tiêu: (1) đo/chứng minh hook TDQ có làm chậm runtime không (chi phí mỗi lần gọi × tần suất, số lần block → agent phải thử lại); (2) đề xuất cách xử lý hook "hướng dẫn" thay vì "chặn" (soft-gate/advisory, gợi ý lệnh đúng, giảm lặp block).
- Phạm vi: bản cài Antigravity `~/.gemini/config/plugins/tdq-workflow-agy/hooks.json` (6 nhóm: SessionStart, PreInvocation ×2, PreToolUse ×7 matcher, PostToolUse, PostInvocation, Stop) và nguồn `hooks/scripts/*.py`, `tools/patches/agy_hooks.py`.
- Chỗ chưa rõ: chỉ cần report (research) hay report + sửa hook luôn; ngưỡng "chậm" user cảm nhận; giữ cứng (block) những cổng nào (an toàn/approval) và mềm hoá cổng nào.

## Hiểu & kiến thức

### Năng lực dùng được

| Năng lực | Nguồn | Phán quyết |
|---|---|---|
| `agy-customizations` (docs/hooks.md) | builtin | DÙNG — hợp đồng hook chính thức của Antigravity |
| `tdq-lean` | plugin:tdq-workflow-agy | DÙNG ở spec — cắt hook/nhắc thừa |
| `tdq-setup`, `tdq-conventions` | plugin:tdq-workflow-agy | DÙNG — luật tìm kiếm, block format |
| `tdq-browser-test`, `tdq-browser-research` | plugin | BỎ — không có UI/web để kiểm |
| `tavily-primary` | MCP | BỎ — tài liệu hook chính thức đã có cục bộ, không còn ẩn số ngoài |

### Bằng chứng đo (4 ngày gần nhất · 120 transcript Antigravity · script ở `brain/.../scratch/`)

**Hợp đồng nền (docs/hooks.md L426-429):** "Hooks run synchronously and block the agent loop (no async execution)" — mọi ms của hook cộng thẳng vào runtime. `PreInvocation` chạy **trước mỗi lần gọi model**, không phải mỗi lượt user.

| Đo | Số liệu |
|---|---|
| Hoạt động | 11.159 lần gọi model · 17.193 bước tool · ~60,5 giờ vòng agent · bước model median 11,0s |
| Spawn rỗng | `py -3 -c pass` 44,4 ms · `python.exe -c pass` 25,5 ms (launcher `py` tốn ~19 ms/lần) |
| `prompt_context.py` (PreInvocation) | **307,6 ms** — 212 ms là `turn_snapshot` gọi 3 lệnh `git` (`repo_status_digest` 111 ms, `repo_root` 50 ms) mỗi lần gọi model |
| `command_gate.py` | 145,1 ms |
| Các hook còn lại | 84–93 ms/lần (`read_gate`, `edit_gate`, `search_gate`, `lsp_gate`, `search_observe`, `post_invocation`, `stop_gate`) |
| Chi phí cố định ước tính | mỗi lần gọi model ≈ 308+86+85 ≈ 480 ms; mỗi tool ≈ 175–230 ms (Pre+Post); `call_mcp_tool` 3 hook ≈ 260 ms |
| Tổng hook trực tiếp (4 ngày) | ≈ 89 phút (Invocation) + ≈ 52 phút (tool) ≈ **2,35 giờ ≈ 3,9%** thời gian vòng agent; ≈ 7% của một bước median |
| Deny `PreToolUse` | ~190 lần thật (SEARCH 85, LSP 49, TICK 30, TEAM 16, GIT 4, APPROVE 2) ≈ 1,1% bước tool; deny→tool kế tiếp OK median 7s, p90 27s, tổng **36 phút** |
| Stop block | 60 (UNFINISHED 53, LOG 7) |
| Ngữ cảnh bơm vào | PreInvocation 9.743 lần × TB 240 ký tự = 2,33 M ký tự; SessionStart 105 × TB 3.963; system message **lưu vĩnh viễn trong trajectory** → hội thoại dài phình prompt |

**Deny sai/đáng nghi:**
- `[TDQ:SEARCH] Command could not be parsed safely (malformed)` (85) bắn vào lệnh KHÔNG phải tìm code: `py -3 -c "..."` đọc file, here-string `@'...'@`, `curl.exe ... -split` → cổng fail-closed khi parse lỗi.
- `[TDQ:LSP] start_lsp without language_id` bắn trong lượt có `call_mcp_tool` tới `chrome-devtools` (`navigate_page`, `new_page`) — matcher `mcp_.*lsp_.*|call_mcp_tool` gom mọi MCP; bench hiện tại `list_pages` → allow, cần tái hiện với lượt nhiều lời gọi song song.
- `[TDQ:TICK]` 30 lần, 16 lần lặp liên tiếp cùng mã → agent kẹt vòng sửa-bị-chặn.

**Kênh "hướng dẫn" có sẵn trong Antigravity (docs/hooks.md):** PreToolUse `decision: allow` + `overwrite` (tự sửa tham số, agent được báo đã sửa) · `injectSteps.systemMessage` + `metadata.user_markdown` (thẻ markdown hiện cho user, model chỉ đọc bản ngắn) · Stop có `continuationActive` để không ép tiếp tục lặp.

**Kết luận sơ bộ:** hook CÓ ảnh hưởng runtime thật nhưng không phải thủ phạm chính (~5% gồm deny); điểm nóng rõ: git ở `prompt_context` mỗi lần gọi model, 2–3 spawn/tool, `py -3` launcher, deny fail-closed SEARCH/LSP, vòng TICK, và system message tích lũy.

### Vùng chạm

| Vùng file chạm | Phát hiện qua lớp | Tác động & quan hệ |
|---|---|---|
| `hooks/scripts/prompt_context.py` → `scripts/tdq_state.py:turn_snapshot/_git` | cProfile + grep | điểm nóng 212 ms/lần gọi model |
| `tools/patches/agy_hooks.py` → `plugins/.../hooks.json` | grep + đọc bản cài | matcher, số spawn, `py -3` |
| `hooks/scripts/search_gate.py` + `scripts/search_rules.py` (`la_malformed`) | grep | deny fail-closed |
| `hooks/scripts/lsp_gate.py` (`ten_lenh_tdq_lsp`, `_common.chuan_hoa_cong_cu_mcp`) | đọc code | deny LSP / unwrap `call_mcp_tool` |
| `hooks/scripts/edit_gate.py` (TICK), `stop_gate.py`, `_common.block` | transcript | vòng deny lặp, định dạng lời chặn |

Graphify/LSP: bỏ qua có lý do (`--bo-qua-lsp`): bước này là đo đạc; LSP/graphify sẽ chạy ở plan khi chốt symbol sửa.

Vòng phạm vi: BỎ — phạm vi đã rõ (một vùng: hook TDQ trên Antigravity), số liệu bối cảnh đã đo ở trên.

### Quyết định đã chốt (2026-11-18 13:57)

- Đầu ra: **chỉ report + đề xuất, KHÔNG sửa code** (1c). Mọi thiết kế ở câu 2–5 đi vào report dưới dạng phương án khuyến nghị có số đo, để mở request riêng khi user duyệt triển khai.
- Phương án khuyến nghị trong report: chỉ chặn cứng cổng an toàn/duyệt (`APPROVE`, `GIT`, `TEAM` sửa trên main, lệnh phá hủy); `SEARCH`/`LSP`/`TICK`/`DOC` → hướng dẫn hoặc tự sửa (`allow` + `overwrite`), parse lỗi → fail-open kèm nhắc (2a).
- Hiển thị: gom nhắc mỗi lượt thành 1 thẻ `metadata.user_markdown` cho user, model nhận 1 dòng ngắn, không lặp trong lượt (3a).
- Hiệu năng: cache git theo lượt, gọi `python.exe` trực tiếp, 1 tiến trình điều phối/sự kiện; mục tiêu ≤ 150 ms/lần gọi model, ≤ 100 ms/tool (4a) — report phải có ước tính tiết kiệm từ số đo.
- Stop: ép tiếp tục tối đa 1 lần/lượt nhờ `continuationActive` (5a).
- QC: `lite` (6b).
- Phương án loại: sửa code ngay (user chọn 1c); giữ chặn cứng toàn bộ (gây 36 phút deny + chặn nhầm); bỏ chặn toàn bộ (mất bảo vệ duyệt/an toàn).

### Bổ sung của user (14:03) & bằng chứng mới

User: "hôm qua gặp nhiều case kéo dài bất thường, ví dụ chỉ commit và merge mà kéo dài gần 15 phút… check, có thể thử nếu cần, cho biết tại sao, đề xuất cải thiện hiệu suất, và hook nên cho chỉ dẫn chứ đang cộc lốc".

Phân rã lượt dài (2 ngày, `scratch/long_turns.py --summary`, `model_latency.py`):

| Lượt | Tổng | Chờ lỗi API | Model sinh | Deny/Stop | Ngữ cảnh max |
|---|---|---|---|---|---|
| `f9e21752` "1 commit" | 26,2 phút | **20,2 phút** (4× `stream idle timeout (5m0s)`) | 5,5 phút | 0/0 | 420k token, `cache_read_tokens=0` |
| `15919377` "duyệt spec" | 42,0 phút | **35,8 phút** (7 lỗi) | 5,9 phút | 0/0 | 64k |
| `b717d25b` "check và đọc lại…" | 35,2 phút | **31,7 phút** (6 lỗi) | 3,5 phút | 0/0 | 22k |
| `15919377` "1a" | 258 phút | 20,0 phút | 212 phút | 5/1 | 524k, 49 lần cache miss |

- 4 ngày: 117 lỗi API (79 `stream idle timeout (5m0s)` các lần thử 1–6, 503 `No capacity`), ~**434,8 phút** chờ trước lỗi.
- Thời gian model theo ngữ cảnh chưa cache: < 50k median 6s/p90 30s · 300k+ median 35s/p90 173s · 400k+ median 55s/p90 225s.
- 3 hội thoại dài nhất: 4.427–6.660 bước, 8–12 lần compaction; nội dung hook bơm vào chiếm **5,2% / 8,2% / 12,9%** tổng ký tự (`PreInvocation`, kể cả dòng "same as last turn — unchanged" vẫn bơm mỗi lần gọi model); output tool chiếm 48–68%.
- Kết luận nguyên nhân: lượt "commit 15–26 phút" do **lỗi timeout API + ngữ cảnh hội thoại khổng lồ, cache miss**, không phải hook chạy chậm. Hook góp: ~4% trực tiếp, 5–13% ngữ cảnh, ~36 phút deny/4 ngày.

### Lộ trình

| Bước/phase | CÓ-BỎ | Vì sao |
|---|---|---|
| spec (thiết kế đề xuất + tiêu chí report) | CÓ | khung bất biến; chốt nội dung & số đo report phải có |
| plan | CÓ | khung bất biến; liệt kê việc đo bổ sung & viết report |
| implement = đo bổ sung + viết report nghiên cứu, không sửa code sản phẩm | CÓ | user chọn 1c |
| research tavily | BỎ | tài liệu hook chính thức đã có cục bộ |
| QC agent độc lập | BỎ | QC `lite`, không có code sản phẩm đổi |
| report md + Archify HTML | CÓ | khung bất biến |

## Hỏi đáp

- **Đầu ra tới đâu?** → C: chỉ report + đề xuất, không sửa code.
- **Cổng nào chặn cứng?** → A: chỉ an toàn/duyệt; còn lại hướng dẫn/tự sửa, parse lỗi fail-open.
- **Hiển thị hướng dẫn?** → A: 1 thẻ markdown/lượt cho user, model 1 dòng, không lặp.
- **Mục tiêu hiệu năng?** → A: cache git, python trực tiếp, 1 tiến trình điều phối; ≤150 ms/model, ≤100 ms/tool.
- **Stop ép tiếp?** → A: tối đa 1 lần/lượt (`continuationActive`).
- **Mức QC?** → B: `lite`.
