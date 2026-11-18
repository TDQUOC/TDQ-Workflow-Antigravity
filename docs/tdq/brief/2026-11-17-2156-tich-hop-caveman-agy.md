# BRIEF — Tích hợp tinh hoa Caveman 4 hướng vào TDQ-Workflow-Antigravity
Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

## Nguyên văn

> Okay lập plan phân tích để tích hợp cả  4 hướng đề xuất và verify lại và trunhf bày cho toi duyệt

**Đọc bước đầu:**
- **Mục tiêu:** Thiết kế, tích hợp chọn lọc cả 4 hướng tối ưu ngữ cảnh và token học từ `Caveman` vào `TDQ-Workflow-Antigravity` mà vẫn giữ sạch 100% giấy phép `MIT`. Toàn bộ giải pháp phải cộng sinh mượt với `RTK v0.98.0`, không phụ thuộc bắt buộc vào Node `22.13+` hay Cloud ngoài, và được kiểm chứng thực nghiệm đầy đủ.
- **Phạm vi 4 hướng tích hợp kỹ thuật (`M1`–`M4`):**
  1. **M1 — Thu gọn MCP Tool Schema & Đo thuế tiền tố (`tdq_mcp_shrink.py` + `token_budget.py`):** Xây dựng stdio proxy Python stdlib rút gọn văn xuôi trong `tools/list`, `prompts/list`, `resources/list` nhưng giữ nguyên tên hàm, tham số, `enum`, `required` và không chạm `tools/call`. Mở rộng `token_budget.py` / `context_surface.py` đo định lượng trọng lượng prefix từ `rules/`, `skills/`, `agents/` và thư mục schema MCP của Antigravity.
  2. **M2 — Hợp đồng Subagent Gọn (`Compact Handoff`) & Giọng gọn `Auto-Clarity`:** Chuẩn hóa khuôn trả về `path:line — symbol — note` cho 6 subagent trong `agents/tdq-*.md`, `subagent_dispatch_gate.py` và `tools/patches/skills_and_agents.py`. Áp dụng quy tắc câu ngắn `ASD-STE100` cho luồng nội bộ nhưng tự động giữ tiếng Việt đầy đủ ở 7 cổng hỏi người dùng, cảnh báo an ninh và báo cáo cuối.
  3. **M3 — Nén dữ liệu có cấu trúc & DOM kèm Kho khôi phục nguyên bản (`tdq_ccr.py`):** Lưu nguyên bản byte gốc kèm `SHA-256` vào `.tdq-runtime/ccr/` trước khi tóm tắt file `.json`, `.jsonl`, `.csv`, `.log`, `.yaml` lớn hoặc snapshot `chrome-devtools`. Tích hợp nhắc thông minh tại `read_gate.py` và cung cấp lệnh `tdq_ccr.py retrieve <id>` khôi phục chính xác 100% dữ liệu gốc.
  4. **M4 — Kiểm toán rò rỉ token từ lịch sử phiên (`tdq_token_audit.py`):** Mở rộng trên nền `tdq_transcript.py` để quét `transcript.jsonl` của Antigravity, Claude Code và Codex ngay trên đĩa cục bộ. Báo cáo xếp hạng các tool call, file đọc lặp và subagent tốn nhiều token nhất kèm nhãn minh bạch `measured` hoặc `inferred`.
- **Kế hoạch kiểm chứng 5 tầng (`V1`–`V5`):**
  - `V1` (Bảo toàn bất biến): Unit test chứng minh `tdq_mcp_shrink.py` không làm đổi schema tham số hay `tools/call`, và `tdq_ccr.py` khôi phục khớp 100% `SHA-256`.
  - `V2` (Benchmark Trước/Sau): Đo tỷ lệ giảm byte/token thật trên schema 3 MCP server của plugin, tập mẫu JSON/CSV/Log/DOM và digest subagent.
  - `V3` (Hợp đồng Antigravity & Linter): Kiểm độ trễ hook, chạy `build_agy_plugin.py`, `agy.EXE plugin validate --strict --json` (`0 findings`), `token_budget.py --kiem`, `doc_lint.py`, `i18n_check.py`, `ruff`.
  - `V4` (E2E sống trên máy thật): Chạy thử proxy MCP thật, khôi phục CCR thật và kiểm toán trực tiếp `transcript.jsonl` của phiên Antigravity hiện tại.
  - `V5` (Full Regression & QC độc lập): Chạy trọn bộ `tdq_test.py tron-bo` (`0 failed`), rà soát qua `tdq-security-reviewer` và kiểm định qua `tdq-qc-tester` kèm báo cáo Archify HTML.
- **Điểm cần làm rõ/chốt thêm trong pha phân tích (`analyze`):**
  - Phạm vi bọc mặc định của `tdq_mcp_shrink.py` trong `mcp_config.json` (bọc tự động `chrome-devtools` + `tavily-primary` + `lsp`, hay bật theo cờ cấu hình).
  - Mức bật mặc định của quy tắc giọng gọn `Auto-Clarity` (chỉ áp cho subagent + bước trung gian, hay áp thêm cho chat thường ngoài 7 cổng duyệt).
  - Ngưỡng kích thước kích hoạt tóm tắt `CCR` (`> 32 KB` hay cấu hình khác) và giới hạn dung lượng kho `.tdq-runtime/ccr/` (ví dụ `128 MB`).
  - Quyền cập nhật bản cài plugin cục bộ tại `~/.gemini/config/plugins/tdq-workflow-agy` để nghiệm thu E2E sống và mức `muc_qc` (`full` hay `ultra`).

## Hiểu & kiến thức

### Phạm vi đã chốt

- **Mặt CHỌN (từ Vòng 1):**
  - `A` Đúng & An toàn dữ liệu: khóa cứng bất biến schema MCP (`enum`, `required`, `default`, `const`), giữ nguyên `tools/call`, khôi phục byte gốc CCR khớp 100% `SHA-256`.
  - `B` Hiệu năng & Tiết kiệm token: đo định lượng trước/sau trên `3` MCP server, tệp dữ liệu/DOM lớn và digest subagent.
  - `C` Tương thích Antigravity & Bảo trì: biên dịch sạch qua `build_agy_plugin.py`, giữ chuẩn mã sạch/ngôn ngữ và vượt `agy.EXE plugin validate`.
  - `D` Trải nghiệm hội thoại (`Auto-Clarity`): rút gọn luồng nội bộ/subagent nhưng tự động giữ tiếng Việt đầy đủ ở `7` cổng duyệt và báo cáo cuối.
  - **Mở rộng theo yêu cầu bổ sung (`M5` — Cài đặt xin quyền qua `tdq_setup` tương tự `RTK`):** Tích hợp cơ chế kiểm tra, nhắc `1` dòng `[TDQ:SETUP]` ở `SessionStart`, dòng chẩn đoán bổ trợ ở `tdq_lsp.py check` và cờ xin quyền tường minh (`--with-caveman`, `--without-caveman`, `--check-caveman`, `--mute-caveman-prompt`, `--unmute-caveman-prompt`) trong `tdq_setup.py`, `install_agy_plugin.py`, `install.py`, `install.ps1`, `install.sh` — tuyệt đối không tự cài/bật ngầm trong `--nen`.
- **Mặt LOẠI:** Phương án tối giản `E`, dịch vụ Cloud ngoài, telemetry ẩn, hoặc tự cài/bật công cụ ngoài/proxy khi chưa có sự đồng ý của người dùng.
- **Ngưỡng vận hành & Hành vi chi tiết đã khóa (Vòng 1 + Vòng 2):**
  - `M1` Proxy MCP (`tdq_mcp_shrink.py`): bật theo cơ chế xin quyền `--with-caveman` cho cả `3` server (`lsp`, `chrome-devtools`, `tavily-primary`); `mcp_config.json` mặc định giữ nguyên bản gốc; hỗ trợ gỡ qua `--without-caveman` và tắt nhanh qua `TDQ_CAVEMAN=0`; proxy thêm `<= 100 ms` cho danh sách tool.
  - `M2` Giọng gọn `Auto-Clarity`: chỉ áp cho `6` subagent (`agents/tdq-*.md`) và digest bàn giao `Compact Handoff` (`path:line — symbol — note`); toàn bộ chat thường, `7` cổng duyệt và báo cáo cuối giữ tiếng Việt đầy đủ.
  - `M3` Kho `CCR` (`tdq_ccr.py` + `.tdq-runtime/ccr/`): kích hoạt từ `> 32 KB` (hoặc `>= 200` dòng), trần dung lượng `128 MB` tự xoay vòng bản cũ nhất; tích hợp nhắc `1` dòng ở `read_gate.py` (giữ nguyên luật "nhắc, không chặn") và hướng dẫn trong `tdq-browser-research`; lệnh `retrieve <id>` khôi phục chính xác `100%` `SHA-256`.
  - `M4` Kiểm toán lịch sử (`token_audit.py` + `tdq_transcript.py`): quét mặc định `5` phiên mới nhất trên Antigravity, Codex và Claude Code.
  - `M5` Quản lý cấu hình & xin quyền: lưu trạng thái user-level riêng (cạnh cấu hình `RTK`, tại `~/.tdq/caveman.json`), dùng chung mọi repo, hỗ trợ bộ cờ độc lập và dòng nhắc `[TDQ:SETUP]` ở `SessionStart` + dòng chẩn đoán ở `tdq_lsp.py check`.
  - Triển khai & QC: cập nhật bản cài plugin cục bộ (`~/.gemini/config/plugins/tdq-workflow-agy`) để nghiệm thu E2E sống và áp dụng mức QC `full` (`muc_qc = full`).

### Năng lực dùng được

Tổng kết từ `scripts/skill_inventory.py --tat-ca` (`42` skill trên đĩa) và `11` skill dựng sẵn trong ngữ cảnh:

| Skill / Công cụ | Nguồn | Vai trò trong request này | Dự kiến |
|---|---|---|---|
| `tdq-intake`, `tdq-spec`, `tdq-plan`, `tdq-build`, `tdq-conventions` | `plugin:tdq-workflow-agy` | Điều phối luồng sâu full lane, viết spec/plan/report và giữ chuẩn ngôn ngữ | DÙNG |
| `tdq-setup`, `tdq-check-status`, `tdq-status`, `tdq-lean` | `plugin:tdq-workflow-agy` | Kiểm bậc tìm kiếm 3 tầng, kiểm phình mã (`tdq-lean`), đọc trạng thái | DÙNG |
| `tdq-browser-research` | `plugin:tdq-workflow-agy` | Nhận hướng dẫn nén / thu gọn snapshot `chrome-devtools` kết hợp `CCR` | DÙNG |
| `tdq-browser-test`, `a11y-debugging`, `chrome-devtools`, `cookie-debugging`, `debug-optimize-lcp`, `memory-leak-debugging`, `troubleshooting` | `plugin:tdq-workflow-agy` / `chrome-devtools-plugin` | Không test ứng dụng web ngoài; chỉ dùng schema MCP của `chrome-devtools` làm đầu vào benchmark M1/M3 | KHÔNG DÙNG (chỉ đọc schema) |
| `tdq-checkportable` | `plugin:tdq-workflow-agy` | Kiểm tra tính di động gói plugin sau build nếu chạm tệp phân phối | CHỜ QUYẾT |
| `tdq-workflow` (nhóm `plugin:tdq-workflow` gốc Claude), `frontend-design`, `illustrator-preflight`, `gdocs`, `gdrive`, `gsheets`, `gslides`, `gemini-api-*`, `google-antigravity-sdk`, `9router-image`, `cdesktop` | plugin khác / user | Ngoài phạm vi tích hợp core của `TDQ-Workflow-Antigravity` | KHÔNG DÙNG |
| Nhóm dựng sẵn (`self`, `research`, `browser`, `image-generator`, `run-workflow`, `swarm`, `agent-creator`, `ui-plugin-navigation`, `plugin`, `automation`, `antigravity-guide`) | built-in | Dùng `research`/`self` tra cứu ngoài; giữ `tdq-*` subagent cho thực thi plan | DÙNG chọn lọc (`self`, `tdq-*`) |

### Nghiên cứu ngoài & Tham chiếu nguồn gốc

- **Tài liệu nghiên cứu ngoài:** `docs/tdq/research/2026-11-17-2156-tich-hop-caveman-agy.md` (xác minh bằng `search_web` vì `tavily-primary` vượt hạn mức gói):
  1. **MCP stdio JSON-RPC 2.0:** Mỗi thông điệp UTF-8 nằm trên 1 dòng kết thúc `\n`, không xuống dòng lồng bên trong; `stdout` chỉ phát JSON-RPC, mọi log đẩy sang `stderr`; giữ nguyên bắt tay `initialize` → server response → `initialized`, chỉ rút gọn phản hồi danh sách (`tools/list`, `prompts/list`, `resources/list`) và giữ nguyên `tools/call`.
  2. **An toàn Windows pipe:** Antigravity / Gemini CLI chạy Python qua pipe cần `-u`, `PYTHONUNBUFFERED=1`, `PYTHONUTF8=1`, và `creationflags=subprocess.CREATE_NO_WINDOW` (`0x08000000`) khi spawn server con `.cmd`/binary để tránh treo buffer, lỗi `cp1252`, và nháy cửa sổ console.
  3. **ASD-STE100 & Ràng buộc schema:** Nén mất dữ liệu dễ xóa từ phủ định (`not`, `never`, `only`) hoặc khóa schema (`const`, `$ref`, `default`, `required`). Bộ nén chỉ rút gọn văn xuôi mô tả không chứa ràng buộc, giữ nguyên nguyên văn mọi câu chứa từ khóa ràng buộc và mọi khóa cấu trúc.
- **Đối chiếu giấy phép & kỹ thuật từ `C:\Users\admin\Documents\caveman` (`v4.1.0`, Apache-2.0):** Không sao chép mã nguồn Go/JS sang repo `MIT`; tự viết lại 100% bằng Python stdlib dựa trên nguyên lý kỹ thuật đã đối chiếu (`engine/compressors/toolschema.go`, `engine/compressors/{tabular,json,log,axtree}.go`, `engine/ccr/store.go`, `skills/caveman/SKILL.md` quy tắc `Auto-Clarity`).

### Khảo sát mã nguồn 3 chiều (Grep · LSP · Graphify)

| Thành phần đích | Grep (lượt tham chiếu) | LSP (`list_symbols` · `find_references` · `blast_radius`) | Graphify (`graphify-out/graph.json` · 6.134 nút) |
|---|---|---|---|
| `scripts/token_audit.py` + `scripts/tdq_transcript.py` | Xuất hiện ở `step_audit.py`, `tdq_transcript.py`, `cli_fixes_b.py`, `test_token_audit.py`, `test_transcript.py` | `default_transcript_dir` (6 refs), `usage_totals` (6 refs); tổng cụm `token_audit` + `context_surface` + `agy_manifests`: `591` symbols / `240` edges | Nằm trong vùng BFS độ sâu 2 (`492` nút liên quan) cùng `step_audit.py`, `skill_tokens.py`, `tdq_transcript_cache.py` |
| `scripts/context_surface.py` + `scripts/token_budget.py` | Tham chiếu chéo với `skill_tokens.py`, `setup_status.py`, `doc_lint.py`, `doc_index.py`, `tools/patches/skills_and_agents.py`, `test_agy_plugin_validate.py` | `scan` (2 refs); `relock_token_budget` khóa hash qua `.venv-tokens` | Liên kết trực tiếp với `doc_lint.py` R13 và quy trình `tdq_finish.py` |
| `hooks/scripts/read_gate.py` | Tham chiếu tại `tools/patches/agy_hooks.py`, `tools/patches/agy_manifests.py`, `tests/test_read_gate.py` | `126` symbols / `46` edges; gồm 3 test gắn với `SO_SACH`, `TRAN_DONG`, `test_so_bi_gitignore` | Nối vào `hooks.json` `PreToolUse` matcher `read_file\|view_file` |
| `tools/patches/agy_manifests.py` + `tools/patches/agy_hooks.py` + `tools/patches/skills_and_agents.py` | Tham chiếu tại `tools/build_agy_plugin.py`, `tools/run_full_verification.py`, `tests/test_agy_plugin_validate.py` | `generate_mcp_config` (12 refs); `subagent_dispatch_gate.py` được sinh tự động vào `plugins/tdq-workflow-agy/hooks/scripts/` khi build | Cụm community `105` cùng `common_utils.py` và `build_agy_plugin.py` |
| `agents/tdq-*.md` (`6` tệp) + `hooks/scripts/subagent_start.py` | Khai báo frontmatter & khuôn trả về tại `skills_and_agents.py`, `subagent_dispatch_gate.py`, `test_subagent_start.py` | Thuộc cụm cấu hình subagent; biên tập tại `agents/*.md` và đồng bộ qua `transform_agents()` | Cụm tài liệu điều phối được kiểm tra ngân sách byte khi `build_agy_plugin.py` chạy |

**Số đo nền thực tế trên máy (đã đo trước khi sửa mã):**
- **Thuế schema MCP thực tế (`C:\Users\admin\.gemini\antigravity\mcp\tdq-workflow-agy_*`):** `3` server chủ lực gồm `103` tool tốn `92.172 B` (~`23.043` est. tokens): `lsp` `65` tools = `54.271 B` (`desc 61%`), `chrome-devtools` `33` tools = `30.218 B` (`desc 52%`, `anno 2.103 B`), `tavily-primary` `5` tools = `7.683 B` (`desc 53%`, `anno 512 B`).
- **Thử nghiệm mô phỏng bộ lọc `M1` trên `3` server MCP:** Nếu chỉ xóa filler words tiếng Anh (cách của `caveman-shrink` Node), tiết kiệm rất thấp (`-2,5%` đến `-3,7%`). Khi kết hợp loại metadata thừa (`$schema`, `title`, `examples`, `example`, `$comment`) + rút gọn câu dẫn giữ nguyên mọi câu chứa từ khóa ràng buộc (`not`, `never`, `only`, `must`, `default`, `const`, `required`), mức giảm đạt **`-24,8%` cho `lsp`**, **`-19,9%` cho `chrome-devtools`** và **`-8,5%` cho `tavily-primary`** (tiết kiệm ~`20.126 B` ≈ `5.032` tokens mà không làm rơi tham số hay ràng buộc).
- **Bề mặt tải ngữ cảnh hiện tại (`scripts/context_surface.py`):**
  - Kho gốc: `always loaded = 15.939 chars (~3.985 tok)` · `loaded on skill call = 82.197 chars (~20.549 tok)` · `read on demand = 524.098 chars (~131.024 tok)`.
  - Plugin biên dịch `plugins/tdq-workflow-agy/`: `always loaded = 4.366 chars (~1.092 tok)` · `rules/*.md = 6.452 B (~1.613 tok)` · `agents/*.md = 16.500 B (~4.125 tok)`.
- **Cấu trúc nhật ký thực tế cho `M4`:** `transcript.jsonl` của phiên Antigravity hiện tại (`4.477` dòng) chứa sự kiện `PLANNER_RESPONSE` mang số đo API thật (`input_tokens`, `cache_read_tokens`, `output_tokens`, `tool_calls`) và `GENERIC` mang `content`/`truncated_fields`; thư mục `~/.codex/sessions` có `3` phiên mang `response_item` (`custom_tool_call`, `custom_tool_call_output`) và `event_msg` (`token_count`). `scripts/token_audit.py` (`528` dòng) đã có sẵn bộ tính carry-cost cho Claude Code, nên theo luật tái sử dụng `TDQ:GON` cần mở rộng trực tiếp `scripts/token_audit.py` + `scripts/tdq_transcript.py` thay vì tạo một script trùng lặp.
- **Baseline test kiểm định hiện tại:** `unittest` (`test_token_audit`, `test_read_gate`, `test_transcript`, `test_agy_plugin_validate`) chạy `102` test trong `2,871s` (`OK`, `9` test tokenizer ở `test_token_audit` skip do thiếu `TDQ_TOKENS_VENV` mặc định khi gọi trần).

### Kiến trúc & Ràng buộc luật khóa

- **Phân tầng từ `docs/kien-truc.md`:** Toàn bộ CLI/thư viện mới (`tdq_mcp_shrink.py`, `tdq_ccr.py`, phần mở rộng `token_audit.py` và `context_surface.py`) đặt trong `scripts/`; logic chặn/nhắc công cụ đặt trong `hooks/scripts/read_gate.py` và `tools/patches/agy_hooks.py`; `scripts/` tuyệt đối không `import` từ `hooks/`.
- **Kiến trúc 2 lớp của `TDQ-Workflow-Antigravity`:** Mọi thay đổi ở nguồn gốc (`scripts/`, `hooks/scripts/`, `agents/`, `skills/`, `tools/patches/*`) đều phải biên dịch qua `tools/build_agy_plugin.py` sang `plugins/tdq-workflow-agy/`, khóa lại `docs/tdq/token-budget.json` và vượt qua `agy.EXE plugin validate --strict --json`.
- **Chuẩn ngôn ngữ 3 tầng (`i18n_check.py`) & Đóng gói `MIT`:** Mã Python, docstring, comment, stdout/stderr thông báo máy giữ 100% tiếng Anh; tài liệu TDQ (`docs/tdq/**`) và hội thoại người dùng viết tiếng Việt; chỉ dùng thư viện chuẩn Python (`stdlib`), không kéo runtime Node mới hay phụ thuộc giấy phép ngoài vào mã nguồn.

### Lộ trình

| Bước/phase | Chạy? | Vì sao |
|---|---|---|
| Research web | CÓ | Đã hoàn thành 3 truy vấn (`stdio` JSON-RPC 2.0, pipe Windows, `ASD-STE100`) tại `docs/tdq/research/2026-11-17-2156-tich-hop-caveman-agy.md` |
| Interview | CÓ | Đã hoàn thành đủ 2 vòng (Vòng 1 phạm vi/ngưỡng + Vòng 2 hành vi `M1`–`M5` & `muc_qc = full`) |
| Spec + Archify BA preview | CÓ | Lane `full` bắt buộc viết spec kèm HTML Trước/Sau (`tdq_archify.py`) trước cổng duyệt |
| Plan + Implement | CÓ | Chia batch tách vùng file không chồng lấn, biên dịch `build_agy_plugin.py` và đồng bộ bản cài cục bộ |
| QC (`full`) + E2E cục bộ | CÓ | Chạy trọn unit test (`tdq_test.py tron-bo`), linter (`doc_lint`, `i18n_check`, `token_budget`, `ruff`), `agy.EXE plugin validate` và kiểm tra thực nghiệm proxy/CCR/audit trên bản cài cục bộ |
| QC độc lập (agent) | BỎ | Người dùng chọn mức QC `5a = full` (không yêu cầu agent QC độc lập của mức `ultra`) |
| Report + Archify HTML | CÓ | Xuất cặp `docs/tdq/reports/<slug>.md` và `.html` tổng kết trước/sau kèm số đo thực nghiệm |

## Hỏi đáp

### Vòng 1 — Chốt phạm vi chất lượng & ngưỡng nền

- **Câu hỏi:** (1) Chọn các mặt chất lượng `A/B/C/D/E`; (2) Ngưỡng kích hoạt và trần kho `CCR`; (3) Độ trễ proxy MCP và số phiên kiểm toán mặc định; (4) Cập nhật bản cài cục bộ để chạy E2E sống.
- **Người dùng trả lời:** `1 abcd 2a 3a 4a và bổ sung vào tdq setup sẽ xin quyền cài như rtk ở sau này luôn`
- **Ghi nhận chốt:** Chọn đủ `4` mặt `A, B, C, D`; `CCR > 32 KB` (hoặc `>= 200` dòng) và trần `128 MB`; proxy `<= 100 ms` và kiểm toán mặc định `5` phiên trên Antigravity/Codex/Claude; cập nhật bản cài cục bộ chạy E2E sống; bổ sung thêm hạng mục `M5` vào `tdq_setup.py` + bộ cài `install.*` + `SessionStart` + `tdq_lsp.py check` theo đúng mô hình xin quyền của `RTK`.

### Vòng 2 — Chốt hành vi chi tiết (`M1`–`M5`) và mức QC (`2026-11-18T11:26:07+07:00`)

- **Câu hỏi:**
  1. Phạm vi bọc mặc định của proxy thu gọn schema MCP `tdq_mcp_shrink.py` (`A`: opt-in `--with-caveman` cho cả `3` server / `B`: bọc sẵn sau build / `C`: chỉ bọc `chrome-devtools` + `tavily-primary`).
  2. Phạm vi áp dụng quy tắc giọng gọn `Auto-Clarity` (`A`: chỉ `6` subagent + `Compact Handoff` / `B`: cả chat thường trừ `7` cổng / `C`: chỉ khi bật `TDQ_CAVEMAN=1`).
  3. Cơ chế hoạt động của `CCR` trong `read_gate.py` (`A`: CLI `tdq_ccr.py` + nhắc `1` dòng không chặn / `B`: chặn `deny` file dữ liệu `> 32 KB` / `C`: CLI độc lập không chạm `read_gate.py`).
  4. Cách lưu cấu hình và bộ cờ `M5` (`A`: user-level `~/.tdq/caveman.json` với cờ độc lập + `SessionStart` + `tdq_lsp.py check` / `B`: gộp chung `--with-token-savers` / `C`: lưu theo từng repo).
  5. Mức QC cho request (`A`: `full` / `B`: `lite` / `C`: `ultra`).
  6. Bổ sung thêm gì không (`A`: Không, đủ rồi — làm tiếp đi / `B`: Có).
- **Người dùng trả lời:** `1a 2a 3a 4a 5a 6a`
- **Ghi nhận chốt:** Bật proxy `M1` opt-in qua `--with-caveman` cho `3` server; `Auto-Clarity` `M2` chỉ cho `6` subagent + `Compact Handoff`; `CCR` `M3` dùng CLI + nhắc không chặn ở `read_gate.py`; `M5` lưu cấu hình user-level `~/.tdq/caveman.json` độc lập với `RTK`; khóa `muc_qc = full`.


