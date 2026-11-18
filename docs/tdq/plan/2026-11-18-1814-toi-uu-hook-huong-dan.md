# PLAN — Tối ưu hiệu năng lõi hook, chuyển sang chỉ dẫn 4 phần & dọn cổng (R1+R2+R3)

Ngày: 2026-11-18 · Spec: ../spec/2026-11-18-1814-toi-uu-hook-huong-dan.md (bản 1.1, ĐÃ DUYỆT) · Lane: full
Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md
Mode thực thi: subagent — `tdq_bench.py simulate --he-so-agent 1.5` cho Winner: đội (nhanh hơn 6,1 phút: 18,3 → 12,3 phút model; 9 task, giao 6/9, chia đợt song song) (ĐÃ CHỐT)
Trạng thái plan: HOÀN THÀNH

## Mục lục

- Quy tắc thi hành (áp cho mọi task)
- Thiết kế Trước vs Sau
- P1 — Tối ưu lõi chung & dữ liệu chỉ dẫn 4 phần
- P2 — Dispatcher & cổng R1/R2/R3 trên Antigravity 2.0
- P3 — Biên dịch gói plugin & bộ kiểm thử R1–R3
- Cụm song song
- Luật file nóng
- Px — Log & test bắt buộc
- Definition of Done

## Quy tắc thi hành (áp cho mọi task)

1. Thứ tự phase là thứ tự phụ thuộc — không đảo.
2. Mỗi task: đánh `[~]` (hoặc `[>]` khi giao subagent) → viết/chạy test đỏ trước → code → test xanh → đổi `[x]` NGAY vào file này.
3. Mỗi bước: `py -3 scripts/tdq_test.py vung-cham`; trọn bộ `tron-bo` chạy 1 lần ở cổng QC-F1.
4. Lệnh chạm state của workflow trong test phải có `TDQ_PROJECT_DIR=<thư mục tạm>`.
5. Tuyệt đối KHÔNG ghi đè lên `~/.gemini/config/plugins/tdq-workflow-agy` (`4b`).
6. Tuân thủ 6 mã cấm cơ học (ANTI-1 Fake Red, ANTI-2 Blind Assertion, ANTI-3 Dirty State Git, ANTI-4 Late Tick, ANTI-5 Raw Dump, ANTI-6 Broad Area) và `i18n_check.py`.

## Thiết kế Trước vs Sau

| Khía cạnh | Hiện trạng (Trước) | Thiết kế mới (Sau) |
|---|---|---|
| Luồng thực thi | `2–3` tiến trình `py -3` mỗi sự kiện (`PreInvocation` `449,5 ms`), xóa `turns-<sid>.jsonl` và gọi `3` lệnh `git` ở mọi bước model; `PostToolUse` chạy cả `run_command`/`read_file` | `1` tiến trình `python -X utf8 hooks/scripts/dispatch.py`; phát hiện lượt mới qua `transcriptPath`/`turn_closed` (`0` git & giữ sổ ở bước giữa lượt); `PostToolUse` chỉ bắt tìm kiếm & MCP |
| Thành phần chạm | `hooks.json` gọi 9 script rời; `remind()` cắt tại `200` ký tự; `overwrite` làm vỡ `call_mcp_tool`; còn `7` mã thừa + `3` script mồ côi | `scripts/tdq_state.py`, `scripts/search_rules.py`, `tools/patches/gate_guidance.py`, `tools/patches/agy_dispatch.py`, `tools/patches/agy_hooks.py`, `tools/patches/agy_manifests.py`, `tools/patches/common_utils.py`, `tools/build_agy_plugin.py`, `tools/install_agy_plugin.py` |

*Đối chiếu sơ đồ kiến trúc:* Tham chiếu `docs/tdq/spec/2026-11-18-1814-toi-uu-hook-huong-dan-preview.html` và manifest đã duyệt (`current`). Đợt 1 xây `core-cache-search` + `guidance-4part`; Đợt 2 xây `agy-dispatcher-gates`; Đợt 3 biên dịch sang `plugins/tdq-workflow-agy/`; Đợt 4 khóa bộ kiểm thử `plugin-compile-tests`.

## P1 — Tối ưu lõi chung & dữ liệu chỉ dẫn 4 phần

- [x] **T1.1** (e12m) Cache bền vững `repo_root(cwd)` trong `tdq_state.py` & sửa parser PowerShell trong `search_rules.py` — Test: `py -3 -m pytest tests/test_core_hook_perf_search.py -q`
  - Chạm: `scripts/tdq_state.py`, `scripts/search_rules.py`, `tests/test_core_hook_perf_search.py`
  - Mục tiêu: cắt `git rev-parse` lặp lại giữa các lần spawn hook và triệt tiêu lỗi gán cờ `malformed` cho lệnh PowerShell `@'...'@`/backtick.
  - Vị trí neo: sau `_ROOT_CACHE = {}` và hàm `repo_root(cwd)` (`tdq_state.py:636-674`); trong `_bo_heredoc` (`search_rules.py:639-653`) và `_tach_script` (`search_rules.py:255-315`).
  - Công cụ: Dùng Edit cho `tdq_state.py`/`search_rules.py`; Write cho file test mới `tests/test_core_hook_perf_search.py`.
  - Ràng buộc: thuần stdlib, không import `hooks/`, chuỗi & comment tiếng Anh sạch `i18n_check.py`, cyclomatic <= 10.
  - Đặc tả kỹ thuật: `_find_git_head(cwd: str, max_depth: int = 8) -> str | None`; `repo_root(cwd: str) -> str | None`; `_strip_ps_herestrings(script: str) -> str`; cập nhật `_bo_heredoc(script: str) -> str` và `_tach_script(s: str, do_sau: int = 0, ngan_sach=None) -> list[list[str]]`.
  - Logic cốt lõi:
    1. Bước 1 (`repo_root`): kiểm tra `_ROOT_CACHE`; trượt thì dò `.git/HEAD` tối đa `8` bậc cha lấy `(abspath(cwd), mtime_ns)`, tra cache JSON `<tempdir>/tdq-repo-roots.json`; nếu khớp `head_mtime_ns` và `root` tồn tại trả ngay (`0` subprocess), trượt mới gọi `_git` và ghi atomic.
    2. Bước 2 (`_bo_heredoc`): dùng regex/scanner thay phần thân PowerShell `@'...\n'@` và `@"...\n"@` bằng khoảng trắng giữ dòng trước khi kiểm tra `<<`.
    3. Bước 3 (`_tach_script`): xử lý `ngoac == '"'` TRƯỚC nhánh `c == "\`"` và trong `ngoac == '"'` nếu gặp `` `n ``, `` `r ``, `` `t ``, `` `" ``, `` `$ `` hoặc backtick nằm trong nháy kép PowerShell thì giữ nguyên ký tự thường thay vì đánh dấu `ngan_sach.la_malformed = True`.
  - Ca góc hiểm & TDD:
    - Ca hiểm: thư mục không phải git repo, file cache JSON hỏng, chuỗi `py -3 -c "... \`..."`, `@'...'@` có chứa `rg`/`grep` bên trong, `\`n` ở cuối chuỗi.
    - Tiêu chí: `assert repo_root(tmp_repo)` lần 2 không gọi subprocess (`mock` `_git` assert call_count == 0); `phan_loai("Bash", cmd)` trả `status != "unknown"` (`reason != "malformed"`) trên cả `7` mẫu PowerShell/`py -c`.

- [x] **T1.2** (e10m) Tạo module chỉ dẫn 4 phần `tools/patches/gate_guidance.py` + unit test — Test: `py -3 -m pytest tests/test_gate_guidance.py -q`
  - Chạm: `tools/patches/gate_guidance.py`, `tests/test_gate_guidance.py`
  - Mục tiêu: cung cấp dữ liệu & bộ định dạng chuẩn 4 phần (*Chuyện gì · Vì sao · Làm gì · Bỏ qua*) + `model_line` <= 160 ký tự + thẻ `user_markdown` cho đúng `22` mã AGY giữ lại và danh sách `7` mã xóa (`LEAN_REMOVED_CODES`).
  - Vị trí neo: module mới dưới `tools/patches/gate_guidance.py` và `tests/test_gate_guidance.py`.
  - Công cụ: Dùng Write cho 2 file mới.
  - Ràng buộc: thuần stdlib, `i18n_check.py` sạch (đặt `# i18n-allow` hợp lệ cho chuỗi user-facing tiếng Việt trong bảng từ điển hoặc nạp qua cấu trúc `USER_CARDS`), không chỉnh sửa file khác.
  - Đặc tả kỹ thuật: `HARD_DENY_CODES: tuple[str, ...]`; `OVERWRITE_CODES: tuple[str, ...]`; `GUIDANCE_CODES: tuple[str, ...]`; `LEAN_REMOVED_CODES: tuple[str, ...]`; `format_deny_4part(code: str, detail: str = "") -> str`; `build_reminder_entry(code: str, detail: str = "") -> dict`; `format_user_markdown(entries: list[dict]) -> str`; `format_model_summary(entries: list[dict]) -> str`.
  - Logic cốt lõi:
    1. Bước 1: Định nghĩa đủ `22` mã (`9` cứng: `APPROVE, GIT, TEAM, STATE, READONLY, VUNG, ZERO-POPUP, SUBAGENT, UNFINISHED`; `1` tự sửa chính + `SUBAGENT`: `LSP`; `12` mềm: `SEARCH, TICK, DOC, LOG, OUTPUT, SETUP, GON, NEXT, WORKTREE, ANCHOR, DOD, INTAKE`) và `7` mã xóa (`ASK, DEVTOOL, FEEDBACK, GATE, QC, RULE, STUCK`).
    2. Bước 2: Mỗi mã trong `22` mã có đủ `chuyen_gi`, `vi_sao`, `lam_gi`, `bo_qua` không rỗng (`<= 1.200` ký tự khi xuất thẻ) và `model_hint` tiếng Anh `<= 160` ký tự.
    3. Bước 3: `format_user_markdown` gom danh sách thẻ chưa trùng trong lượt thành `1` bảng/khối Markdown rõ ràng; `format_model_summary` nối các `model_hint` ngắn `<= 200` ký tự tổng.
  - Ca góc hiểm & TDD:
    - Ca hiểm: mã thiếu `[TDQ:` prefix, `entries` rỗng, danh sách nhiều thẻ vượt `1.200` ký tự.
    - Tiêu chí: `assert len(HARD_DENY_CODES | OVERWRITE_CODES | GUIDANCE_CODES) == 22` (loại trùng hợp), `len(LEAN_REMOVED_CODES) == 7`, `100%` mã đủ 4 trường không rỗng.
  - Dùng: `tdq-conventions`
  - Để: tuân thủ chuẩn 3 tầng `i18n_check.py`, `# i18n-allow` cho văn bản thẻ người dùng và giữ chuỗi máy tiếng Anh, nạp skill TRƯỚC bước đỏ
  - Ra: `tools/patches/gate_guidance.py` sạch `i18n_check.py` và xuất thẻ 4 phần tiếng Việt gọn gàng
  - Kiểm: `py -3 scripts/i18n_check.py tools/patches/gate_guidance.py`
  - Không dùng cho: chỉnh sửa skill/rule Markdown trong `skills/`

**Xong P1 khi**: cả `tests/test_core_hook_perf_search.py` và `tests/test_gate_guidance.py` xanh, `i18n_check.py` sạch 0 lỗi.

## P2 — Dispatcher & cổng R1/R2/R3 trên Antigravity 2.0

- [x] **T2.1** (e22m) Xây `tools/patches/agy_dispatch.py` & nâng cấp `tools/patches/agy_hooks.py` (R1+R2+R3) — Test: `py -3 -c "import ast,pathlib,sys; sys.path.insert(0,'tools'); from patches import agy_hooks, agy_dispatch; assert hasattr(agy_dispatch,'DISPATCH_PY') and ast.parse(agy_dispatch.DISPATCH_PY) and ast.parse(agy_hooks.COMMON_PY)"`
  - Chạm: `tools/patches/agy_dispatch.py`, `tools/patches/agy_hooks.py`
  - Cần: T1.1, T1.2
  - Mục tiêu: đóng gói toàn bộ logic `dispatch.py` (1 tiến trình/sự kiện), bọc `Arguments` cho `overwrite` `call_mcp_tool`, nhận diện lượt mới qua `transcriptPath`/`turn_closed`, tách 2 kênh hàng đợi `user_markdown` 4 phần, Hướng A cho `SEARCH`, `O(1)` cho `LSP`, bỏ chặn `TICK`/`LOG`, `Stop` tối đa 1 lần bằng `continuationActive`, dọn `.tdq-runtime` > 7 ngày, và cắt `7` mã thừa trên bản AGY.
  - Vị trí neo: module mới `tools/patches/agy_dispatch.py` + trong `tools/patches/agy_hooks.py:8-737,744-1014` (`COMMON_PY`, `SUBAGENT_DISPATCH_GATE_PY`, `POST_INVOCATION_PY`, `apply_all`).
  - Công cụ: Dùng Write cho `agy_dispatch.py`; Edit cho `agy_hooks.py`.
  - Ràng buộc: thuần stdlib trong mọi mã sinh ra, mỗi hàm cyclomatic <= 10, `i18n_check.py` sạch, không phá hàm public mà test cũ đang import (`normalize_payload`, `read_payload`, `payload_cwd`, `session_id`, `turn_rows`, `block`, `stop_block`, `remind`, `queue_remind`, `flush_pending_reminders`, `set_overwrite`).
  - Đặc tả kỹ thuật:
    - `agy_dispatch.py`: `DISPATCH_PY: str`, `apply_dispatch(hooks_scripts_dir: Path) -> None` (ghi file `dispatch.py` và sao chép `gate_guidance.py` từ `patches` sang thư mục `hooks_scripts_dir` của `stage`).
    - `COMMON_PY`: thêm `raw_tool_name`, `raw_args_is_str` vào `_RUNTIME_STATE`; sửa `set_overwrite(fields)` tự bọc vào `{"Arguments": json.dumps(...) | dict}` khi `raw_tool_name == "call_mcp_tool"`; cập nhật `queue_remind(cwd, payload, code, model_line, user_card="")` + `flush_pending_reminders(cwd, conv_id)` trả `(model_text, user_markdown)`; cập nhật `_flush_agy_stdout()` xuất `injectSteps[0].systemMessage.metadata.user_markdown` khi có `user_markdown` (với `systemMessage` `<= 200` chars).
    - `dispatch.py`: hàm `route_event(event: str, payload: dict)` gọi in-process `session_start`, `prompt_context` (dùng `_detect_new_user_turn` qua đuôi `64 KB` của `transcriptPath` + `turn-meta-<sid>.json` + `turn_closed`, tắt lặp `"same as last turn"` & `TDQ:GON` giữa lượt, xóa rác `> 7` ngày ở `SessionStart`), các gate `PreToolUse` (`lsp_gate` dò ngôn ngữ `O(1)` từ `.tdq-lsp-module.json` hoặc `FILE_MOC_NGON_NGU` + `overwrite`, `subagent_dispatch_gate` `overwrite` `Workspace="inherit"`, `search_gate`/`command_gate` Hướng A ân xá lần 1 + `malformed` fail-open, `edit_gate` bỏ chặn `TICK`, `read_gate` giữ `DOC` nhắc nhẹ), `PostToolUse` `search_observe`, `PostInvocation` flush, `Stop` (`continuationActive` -> `allow` + `turn_closed=True`, `LOG` trừ `.staging*` & `DOD` thành nhắc mềm).
  - Logic cốt lõi:
    1. Bước 1: Ghi module `gate_guidance.py` và `dispatch.py` vào thư mục đích `hooks_scripts_dir` trong `apply_dispatch`.
    2. Bước 2: Sửa `COMMON_PY` hỗ trợ 2 kênh `model_line`/`user_card`, khử lặp theo `code`, bọc `Arguments` cho `call_mcp_tool`, và hàm `_format_hard_block_4part` cho `9` cổng cứng.
    3. Bước 3: Patch `prompt_context.py`, `stop_gate.py`, `lsp_gate.py`, `search_gate.py`, `command_gate.py`, `edit_gate.py`, `read_gate.py`, `bash_gate.py`, `subagent_dispatch_gate.py`, `session_start.py` trong `stage/hooks/scripts` bỏ `FEEDBACK`, `ASK` thừa (giữ `ZERO-POPUP` ở `ask_gate`), `GATE` (gộp về `STATE`), `RULE`, `QC`, `DEVTOOL`, `STUCK`.
  - Ca góc hiểm & TDD:
    - Ca hiểm: payload `call_mcp_tool` có `Arguments` là JSON string `"{}"` (như `EC-16`), `transcriptPath` không tồn tại ở unit test synthetic, nhiều nhắc mềm xếp hàng cùng lúc, `prompt_context` ở bước `mode`/`approve` khi user gõ lặp `"1a"`.
    - Tiêu chí: `ast.parse` sạch trên cả `DISPATCH_PY`, `COMMON_PY`; `i18n_check.py tools/patches/agy_dispatch.py tools/patches/agy_hooks.py` exit `0`.
  - Dùng: `agy-customizations (docs/hooks.md)`
  - Để: bám chuẩn trường `transcriptPath`, shallow `overwrite` với `call_mcp_tool`, `metadata.user_markdown`, `continuationActive`, nạp skill TRƯỚC bước đỏ
  - Ra: `tools/patches/agy_dispatch.py` và `tools/patches/agy_hooks.py` xuất đúng JSON giao thức Antigravity 2.0
  - Kiểm: `py -3 -c "import sys; sys.path.insert(0,'tools'); from patches import agy_hooks, agy_dispatch; assert 'user_markdown' in agy_hooks.COMMON_PY and 'continuationActive' in agy_dispatch.DISPATCH_PY"`
  - Không dùng cho: sửa file `.gemini/` bên ngoài repo (`4b`)

- [x] **T2.2** (e10m) Cập nhật `agy_manifests.py`, `common_utils.py`, `build_agy_plugin.py`, `install_agy_plugin.py` (R1+R3+2b) — Test: `py -3 -c "import tempfile,sys; from pathlib import Path; sys.path.insert(0,'tools'); from patches import agy_manifests, common_utils; d=Path(tempfile.mkdtemp()); (d/'hooks').mkdir(); agy_manifests.generate_hooks_json(d); s=(d/'hooks.json').read_text(encoding='utf-8'); assert 'dispatch.py' in s and 'python -X utf8' in s and '\"' not in s.replace('\"','') or '\"dispatch.py\"' not in s; assert len(common_utils.EXCLUDED_AGY_HOOKS)==3"`
  - Chạm: `tools/patches/common_utils.py`, `tools/patches/agy_manifests.py`, `tools/build_agy_plugin.py`, `tools/install_agy_plugin.py`
  - Cần: T1.1
  - Mục tiêu: trỏ toàn bộ `hooks.json` về `python -X utf8 hooks/scripts/dispatch.py --event <Event>`, thu hẹp `PostToolUse`, loại 3 script mồ côi khỏi gói AGY (`build_agy_plugin.py`), và thêm probe kiểm tra stub WindowsApps Python vào `install_agy_plugin.py`.
  - Vị trí neo: `EXCLUDED_SCRIPTS` (`common_utils.py:12-20`), `_hook_cmd` & `generate_hooks_json` (`agy_manifests.py:90-140`), bước copy hooks (`build_agy_plugin.py:47,68`), `main`/`_probe` (`install_agy_plugin.py:30-110,165-295`).
  - Công cụ: Dùng Edit trên 4 file.
  - Ràng buộc: giữ nguyên `6` khóa top-level trong `hooks.json` (`test_agy_plugin_validate.py:32`), không dấu `"` trong bất kỳ `command` nào (`L60`), không tự ghi `~/.gemini/...` khi chạy unit test.
  - Đặc tả kỹ thuật:
    - `common_utils.EXCLUDED_AGY_HOOKS = {"doc_file_gate.py", "strategic_compact_gate.py", "stop_batch_checker.py"}`.
    - `agy_manifests._hook_cmd(script_name: str, event_name: str) -> Dict[str, str]` sinh `"python -X utf8 hooks/scripts/dispatch.py --event {event_name}"` (1 handler mỗi sự kiện trong `PreInvocation`, 1 handler cho mỗi matcher `PreToolUse`, `PostToolUse` bỏ `run_command|read_file|view_file`).
    - `build_agy_plugin.py`: truyền `exclude_names=common_utils.EXCLUDED_AGY_HOOKS` khi copy `hooks/scripts` và gọi `agy_dispatch.apply_dispatch(stage / "hooks" / "scripts")` sau `agy_hooks.apply_all`.
    - `install_agy_plugin.py`: thêm `probe_python_path_command() -> dict` (kiểm `python -X utf8 -c pass`, cảnh báo nếu là WindowsApps stub `rc != 0` hoặc đường dẫn chứa `WindowsApps`).
  - Logic cốt lõi:
    1. Bước 1: Thêm `EXCLUDED_AGY_HOOKS` vào `common_utils.py` và nối vào `build_agy_plugin.py` cùng `agy_dispatch.apply_dispatch`.
    2. Bước 2: Cập nhật `generate_hooks_json` dùng `python -X utf8 hooks/scripts/dispatch.py --event <Event>`, hợp nhất `PreInvocation` còn `1` entry và `mcp_.*lsp_.*|call_mcp_tool` còn `1` entry, rút gọn `PostToolUse` matcher.
    3. Bước 3: Thêm `probe_python_path_command()` vào `install_agy_plugin.py` và in trạng thái trong kết quả JSON cài đặt.
  - Ca góc hiểm & TDD:
    - Ca hiểm: `install_agy_plugin.py --dry-run` vẫn an toàn, không chạm mạng hay ghi ngoài `--target`.
    - Tiêu chí: `hooks.json` sinh ra có 6 nhóm, `0` chuỗi chứa `py -3`, `0` dấu `"` trong trường `command`, `PostToolUse` không chứa `run_command` hay `read_file`.
  - Dùng: `tdq-lean`
  - Để: loại bỏ 3 script mồ côi khỏi gói biên dịch Antigravity 2.0 nhưng bảo toàn file gốc cho test Claude/Codex, nạp skill TRƯỚC bước đỏ
  - Ra: `common_utils.EXCLUDED_AGY_HOOKS` và `build_agy_plugin.py` lọc sạch 3 script khỏi `plugins/tdq-workflow-agy/hooks/scripts/`
  - Kiểm: `py -3 -c "import sys; sys.path.insert(0,'tools'); from patches import common_utils; assert common_utils.EXCLUDED_AGY_HOOKS == {'doc_file_gate.py','strategic_compact_gate.py','stop_batch_checker.py'}"`
  - Không dùng cho: xóa file gốc dưới `hooks/scripts/` (`1a`)

**Xong P2 khi**: cả `T2.1` và `T2.2` PASS và `i18n_check.py tools/` exit 0.

## P3 — Biên dịch gói plugin & bộ kiểm thử R1–R3

- [x] **T3.1** (e10m) Biên dịch `plugins/tdq-workflow-agy/` + xác thực `agy.EXE plugin validate --strict --json` + kiểm `~/.gemini` nguyên vẹn (`4b`) — Test: `py -3 tools/build_agy_plugin.py && agy.EXE plugin validate --strict --json plugins/tdq-workflow-agy`
  - Cần: T2.1, T2.2
  - Mục tiêu: sinh bản `plugins/tdq-workflow-agy/` đầy đủ R1+R2+R3, khóa `token-budget.json`, kiểm `0 findings` từ `agy.EXE`, và xác nhận `C:\Users\admin\.gemini\config\plugins\tdq-workflow-agy` chưa bị ghi đè.
  - Đặc tả kỹ thuật & Logic cốt lõi: chạy `py -3 tools/build_agy_plugin.py`, kiểm tra không tồn tại `doc_file_gate.py`/`strategic_compact_gate.py`/`stop_batch_checker.py` trong `plugins/tdq-workflow-agy/hooks/scripts/`, tồn tại `dispatch.py` & `gate_guidance.py`, và kiểm `agy.EXE plugin validate --strict --json plugins/tdq-workflow-agy`.

- [x] **T3.2** (e14m) Viết bộ test mới `tests/test_hook_dispatch_r1_r3.py` kiểm chứng trọn vẹn `Q1–Q5` & log service — Test: `py -3 -m pytest tests/test_hook_dispatch_r1_r3.py -v`
  - Chạm: `tests/test_hook_dispatch_r1_r3.py`
  - Cần: T3.1
  - Mục tiêu: khóa bằng test tự động các yêu cầu R1–R3 trên `plugins/tdq-workflow-agy/` đã biên dịch: phát hiện lượt mới khi gõ lặp `"1a"`, `0` lệnh git giữa lượt, `overwrite` `call_mcp_tool` + `SUBAGENT`, `SEARCH` Hướng A (`malformed` 0 deny, lần 1 allow + nhắc, lần 2 deny), `TICK`/`LOG` mềm, `Stop` `continuationActive` 1 lần, `user_markdown` 4 phần, dọn `.tdq-runtime` > 7 ngày, và `TDQ_LOG` mặc định/tắt.
  - Vị trí neo: file mới `tests/test_hook_dispatch_r1_r3.py`.
  - Công cụ: Dùng Write.
  - Ràng buộc: `TDQ_PROJECT_DIR` / repo tạm cô lập trong `tmp_path`, không chạm `~/.gemini`, mỗi test case chạy < 5s.
  - Đặc tả kỹ thuật: các hàm `test_r1_turn_detection_repeated_1a_and_no_midturn_git`, `test_r2_call_mcp_tool_lsp_overwrite_and_subagent_overwrite`, `test_r2_search_huong_a_and_malformed_allow`, `test_r2_user_markdown_4part_and_tick_log_soft`, `test_r3_stop_continuation_active_once_and_cleanup_7d`, `test_tdq_log_default_and_disabled`.
  - Logic cốt lõi:
    1. Bước 1: Dựng git repo tạm + `transcript.jsonl` mẫu trong `tmp_path`, chạy `dispatch.py` trong gói plugin đã biên dịch qua `python -X utf8`.
    2. Bước 2: Kiểm tra từng quyết định JSON stdout (`injectSteps[0].systemMessage.metadata.user_markdown`, `overwrite.Arguments`, `decision`), nội dung `.tdq-runtime/` và `stderr` log timestamp.
  - Ca góc hiểm & TDD:
    - Ca hiểm: JSON string trong `Arguments` của `call_mcp_tool`, payload rỗng `{}` fail-open, file cũ 8 ngày bị dọn còn file mới 1 ngày giữ nguyên.
    - Tiêu chí: mọi assert đều kiểm giá trị cụ thể (không `assert True`), toàn bộ pass trên `plugins/tdq-workflow-agy/`.

- [x] **T3.3** (e12m) Cập nhật `tests/test_hooks_dual_protocol.py`, `tests/test_command_gate.py`, `tests/test_agy_plugin_validate.py` khớp hợp đồng R1–R3 — Test: `py -3 -m pytest tests/test_hooks_dual_protocol.py tests/test_command_gate.py tests/test_agy_plugin_validate.py -q`
  - Chạm: `tests/test_hooks_dual_protocol.py`, `tests/test_command_gate.py`, `tests/test_agy_plugin_validate.py`
  - Cần: T3.1
  - Mục tiêu: đồng bộ 3 bộ test giao thức Antigravity với `22` mã AGY (thay 24 cũ vì bỏ 7 mã trùng/thừa và gộp/thêm `TICK`/`DOD`/`DOC`), hành vi mềm mới (`TICK` không deny ở `edit_gate`, `SUBAGENT` `overwrite`, `LOG` không chặn `Stop`, `FEEDBACK` không còn phát ở `prompt_context`), và `hooks.json` dùng `python -X utf8 ... dispatch.py`.
  - Vị trí neo: `EXPECTED_24_CODES` & `test_ec01_to_ec14` (`test_hooks_dual_protocol.py:24-348`), `test_agy_manifests_collapse_and_agents_rtk_rules` (`test_command_gate.py:196-220`), `test_v1_hooks_json_...` (`test_agy_plugin_validate.py:40-77`).
  - Công cụ: Dùng Edit.
  - Ràng buộc: giữ nguyên mọi test cho Claude Code backward-compat và `TDQ_VUNG` / `ZERO-POPUP` / `READONLY` / `GIT` / `TEAM` / `rtk` `overwrite` / `uninstall_stale` / `validate --strict`.
  - Đặc tả kỹ thuật: cập nhật `EXPECTED_CODES` (22 mã AGY), cập nhật assertion `decision="allow"` + `overwrite` ở `test_hooks_dual_protocol.py`, kiểm `"dispatch.py"` & `"python -X utf8"` ở `test_command_gate.py`, và kiểm `not (PLUGIN_DIR / "hooks" / "scripts" / "stop_batch_checker.py").exists()` ở `test_agy_plugin_validate.py`.
  - Logic cốt lõi:
    1. Bước 1: Đọc kỹ từng sub-assertion trong `EC-01..EC-17` của `test_hooks_dual_protocol.py`, đổi kỳ vọng ở các cổng đã chuyển sang hướng dẫn/`overwrite` (như `SUBAGENT` `Workspace` -> `overwrite`, `TICK` -> queued `user_markdown`, `LOG` -> nhắc mềm ở `Stop`, `FEEDBACK` -> không phát).
    2. Bước 2: Cập nhật `test_command_gate.py:213` kiểm `dispatch.py` & `python -X utf8`, và giữ test `command_gate.process_payload` chạy xanh.
    3. Bước 3: Bổ sung assertion xác nhận 3 script mồ côi không có trong `plugins/tdq-workflow-agy/` ở `test_agy_plugin_validate.py`.
  - Ca góc hiểm & TDD:
    - Ca hiểm: `_run_hook` gọi `cmd /c python -X utf8 ...` không vướng Windows Store stub.
    - Tiêu chí: cả 3 module pytest pass 100% và `test_v1_install_dry_run_and_staged_validate` xanh với `agy.EXE plugin validate`.

**Xong P3 khi**: `plugins/tdq-workflow-agy/` biên dịch sạch `0 findings` và toàn bộ 5 module test (`test_core_hook_perf_search`, `test_gate_guidance`, `test_hook_dispatch_r1_r3`, `test_hooks_dual_protocol`, `test_command_gate`, `test_agy_plugin_validate`) đều xanh.

## Cụm song song

- Đợt 1 (song song): `T1.1`, `T1.2` — vùng file tách biệt (`scripts/` vs `tools/patches/gate_guidance.py`).
- Đợt 2 (song song sau Đợt 1): `T2.1`, `T2.2` — vùng file tách biệt (`agy_dispatch.py`+`agy_hooks.py` vs `common_utils.py`+`agy_manifests.py`+`build_agy_plugin.py`+`install_agy_plugin.py`).
- Đợt 3 (`tu_lam`, nối tiếp Đợt 2): `T3.1` — biên dịch `plugins/tdq-workflow-agy/` (`vung-khoa`, chạy trực tiếp bởi leader để đồng bộ toàn cây).
- Đợt 4 (song song sau Đợt 3): `T3.2`, `T3.3` — 2 vùng test tách biệt.
- Đợt 5 (`tu_lam`, sau Đợt 4): `Tx.1`, `Tx.2` — kiểm tra log service + hồi quy tổng hợp.

## Luật file nóng

Không có file nào bị từ `2` task trở lên khai ở `Chạm:` — mỗi module/file chỉ có đúng `1` chủ ghi duy nhất trong toàn plan.

## Px — Log & test bắt buộc

- [x] **Tx.1** (e4m) Kiểm tra `TDQ_LOG` trên `dispatch.py` bản biên dịch (bật mặc định có timestamp ISO, tắt khi `TDQ_LOG=0`) — Test: `py -3 -c "import subprocess,os,json; p='plugins/tdq-workflow-agy'; on=subprocess.run(['python','-X','utf8','hooks/scripts/dispatch.py','--event','PreInvocation'],input='{}',cwd=p,capture_output=True,text=True); off=subprocess.run(['python','-X','utf8','hooks/scripts/dispatch.py','--event','PreInvocation'],input='{}',cwd=p,capture_output=True,text=True,env=dict(os.environ,TDQ_LOG='0')); assert on.returncode==0 and off.returncode==0 and off.stderr.strip()==''"`
  - Cần: T3.1, T3.2
- [x] **Tx.2** (e6m) Kiểm tra liên thông unit test + `i18n_check.py` + `token_budget.py` toàn vùng chạm — Test: `py -3 -m pytest tests/test_core_hook_perf_search.py tests/test_gate_guidance.py tests/test_hook_dispatch_r1_r3.py tests/test_hooks_dual_protocol.py tests/test_command_gate.py tests/test_agy_plugin_validate.py tests/test_context_hooks.py tests/test_edit_gate.py tests/test_stop_gate.py tests/test_search_gate.py tests/test_lsp_gate.py -q`
  - Cần: T3.2, T3.3

## QC vòng 1 — fix

- [x] **QC1.1** (e4m) Hỗ trợ đồng thời `toolCall.args` và `toolCall.arguments` trong `tools/patches/agy_hooks.py` (`_extract_raw_tool_container`), biên dịch lại `plugins/tdq-workflow-agy/` — Test: `py -3 -m pytest tests/test_hook_dispatch_r1_r3.py -q`

## QC vòng 2 — fix

- [x] **QC2.1** (e8m) Vá 3 lỗ hổng `TDQ:GIT`, `TDQ:TEAM` dùng `detect_subagent`, dedup `search_gate` malformed, `return` `TDQ:STATE`, fallback prompt > 64 KB và khóa file cache `repo_root` — Test: `py -3 -m pytest tests/test_core_hook_perf_search.py tests/test_hook_dispatch_r1_r3.py tests/test_bash_gate.py tests/test_edit_gate.py -q`
- [x] **QC2.2** (e8m) Tối ưu `Stop` (dùng chung `status` + bỏ `diff HEAD` khi không có file tracked đổi) & `command_gate` RTK (bỏ qua builtin + cache `rtk rewrite` theo mtime), lọc `4` script AGY thừa (`agy_pretooluse_gate.py`, `agy_stop_gate.py`, `codex_edit_gate.py`, `subagent_start.py`) & tạo `bench_dispatch.py`, biên dịch lại `plugins/tdq-workflow-agy/` — Test: `py -3 -m pytest tests/test_command_gate.py tests/test_rtk_integration.py tests/test_agy_plugin_validate.py tests/test_stop_gate.py -q`

## Definition of Done

- [x] Q1 Độ trễ `PreInvocation` giữa lượt `<= 150 ms` và `PreToolUse` `<= 100 ms` (`command_gate <= 130 ms`); `PostToolUse` bỏ `run_command`/`read_file` — `py -3 docs/tdq/bench/2026-11-18-1346-hook-runtime/bench_hooks.py --n 12 --plugin-dir plugins/tdq-workflow-agy`
- [x] Q2 Triệt tiêu `0/8` `search_malformed`, `0/2` `tick_loop` deny, `TDQ:SEARCH` Hướng A ân xá lần 1 / chặn tái phạm lần 2 + `rtk bypass grep` — `py -3 -m pytest tests/test_hook_dispatch_r1_r3.py -k "search or tick"`
- [x] Q3 Tự sửa `overwrite` an toàn cho `call_mcp_tool` (`Arguments`, `O(1)` `< 1 ms`) và `TDQ:SUBAGENT` (`Workspace="inherit"`) — `py -3 -m pytest tests/test_hook_dispatch_r1_r3.py -k "overwrite"`
- [x] Q4 Thẻ `metadata.user_markdown` đủ 4 phần cho `22/22` mã AGY, tách `model_line <= 160` và `user_card <= 1.200` không lặp — `py -3 -m pytest tests/test_gate_guidance.py tests/test_hook_dispatch_r1_r3.py -k "user_markdown or guidance"`
- [x] Q5 Giữ nguyên `9/9` cổng cứng, `"1a"` lặp mở được `[TDQ:APPROVE]`, `Stop` `continuationActive=True` trả `allow`, `LOG` không chặn `Stop`, dọn `.tdq-runtime` > 7 ngày — `py -3 -m pytest tests/test_hook_dispatch_r1_r3.py -k "hard or stop or repeated_1a or cleanup"`
- [x] Q6 `plugins/tdq-workflow-agy/hooks.json` hợp nhất `python -X utf8 hooks/scripts/dispatch.py`, lọc 3 script mồ côi (giữ ở gốc `hooks/scripts/`), `~/.gemini/config/plugins/tdq-workflow-agy` nguyên vẹn, `agy.EXE plugin validate` `0 findings` — `py -3 -m pytest tests/test_agy_plugin_validate.py tests/test_command_gate.py -q`
- [x] Q7 `i18n_check.py scripts/ hooks/ tools/patches/`, `doc_lint.py`, `token_budget.py --kiem` exit `0`; `tdq_test.py tron-bo` xanh; smoke test + runtime test (`<= 120s`) + biên bản `tdq-qc-tester` độc lập (`ultra`) PASS — `py -3 scripts/tdq_test.py tron-bo --workers 4 --fresh --reuse off`
