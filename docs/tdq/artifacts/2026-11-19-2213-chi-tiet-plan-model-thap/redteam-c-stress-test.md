# Red-Team C — Stress-Test Thực Chiến Viết Lại 3 Ca Thất Bại Thật Theo V1 (Vòng 2)

Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

> **Kết luận ngắn:** Khuôn V1 đẩy điểm sẵn sàng của cả `3` ca thất bại lịch sử từ **`0–8/14`** lên **`12–14/14`**, nhưng phát sinh **bùng nổ task (`1 → 6` ở `1632:T2.1`, `1 → 3` ở `QC1.1`, `1 → 3` ở `0046:T2.3`)**, phình token **`3.5×–9.5×`**, sinh **`HOT FILE` giả** trên file đa hàm, lộ **mâu thuẫn cứng giữa §2.3 và §4.1 (`R15-Strict`)**, và **bỏ lọt hoàn toàn quick-lane không đụng `EXT_MA_NGUON`** (`11-19-1457`).

---

## 1. Bảng Tổng Hợp Số Đo & Chấm Điểm 7 Chiều (`0..14`)

Thang 7 chiều: `(a)` Neo vị trí, `(b)` Trước → Sau, `(c)` Thuật toán/Nhánh rẽ, `(d)` Công nghệ/Chữ ký, `(e)` Ràng buộc/Ca hiểm, `(f)` Đầu ra kỳ vọng, `(g)` Test Oracle `input → assert`. Ước lượng token = `chars / 4`.

| Ca thực chiến | Số Task (Trước → Sau) | Số dòng (Trước → Sau) | Est. Token `~chars/4` (Trước → Sau) | Điểm Trước (`a..g`) | Điểm Sau (`a..g`) | Ghi chú ma sát phát sinh |
|---|---|---|---|---|---|---|
| **Ca 1:** `11-19-0046:T2.3` (`pre_tool_use.rs` 9 cổng, `632` dòng) | `1` → `3` (`T2.3a..c`) | `17` → `78` (**`4.59×`**) | `~408` → `~1,738` (**`4.26×`**) | **`5/14`** (`1,0,1,1,1,1,0`) | **`14/14`** (`2,2,2,2,2,2,2`) | `pre_tool_use.rs` tự biến thành **`HOT FILE`**; `T2.3a` vẫn chạm `9` hàm (`> 3` symbol); file tạo mới khiến Scaffolder trên `Chạm:` rỗng |
| **Ca 2A:** `11-19-1632:T2.1` (`8` file Rust Hot-path) | `1` → `6` (`T2.1a..f`) | `16` → `149` (**`9.31×`**) | `~621` → `~2,850` (**`4.59×`**) | **`8/14`** (`1,0,1,2,1,2,1`) | **`14/14`** (`2,2,2,2,2,2,2`) | Sinh `2` **`HOT FILE`** (`events/mod.rs`, `pre_tool_use.rs`); cả plan gốc `263` dòng có nguy cơ phình lên `~550–650` dòng |
| **Ca 2B:** `11-19-1632:QC1.1` (Fix `from __future__` + rebuild) | `1` → `3` (`QC1.1a..c`) | `3` → `45` (**`15.0×`**) | `~98` → `~930` (**`9.49×`**) | **`2/14`** (`1,0,0,0,0,1,0`) | **`12–13/14`** (`1–2,2,2,2,2,2,1`) | Xé oan sweeping 1 dòng; **đụng độ §2.3 (5 trường) vs §4.1 (đòi `Đặc tả`)**; `QC1.1c` phải giấu `.py` build lại khỏi `Chạm:` để né `R15` |
| **Ca 3A:** `11-19-1457` (Quick Audit + `ANTI-2`, toàn file L1–34) | `3+1 QC` → `3+1 QC` | `34` → `34` *(§2.3a)* / `50` *(ép Card)* | `~798` → `~810` *(§2.3a)* / `~1,420` *(ép Card)* | **`0/14`** (`T1`/`QC.1`) | **`4/14`** *(§2.3a)* / **`12/14`** *(ép Card)* | Theo §2.3(a) thì **lọt lưới `R15` & `ANTI-2`**; nếu ép dùng Compact Card để đạt `12/14` thì **vượt trần `40` dòng** non-code! |
| **Ca 3B:** `11-16-0058` (Quick Code `muc_gat=full`, toàn file L1–32) | `2` → `3` (`T1a,T1b,T2`) | `32` → `61` (**`1.91×`**, task `6→37`) | `~688` → `~1,330` (task `~253→~880`) | **`6.5/14`** (`T1=7`, `T2=6`) | **`13/14`** (`2,2,2,2,2,2,1`) | Đổi `1` hằng số đã tốn `61/80` dòng; nếu `T2` khai báo `.py` trong `plugins/` sẽ thành `3` task code và bị **ép nhảy sang lane `full`** |

---

## 2. Viết Lại Thực Chiến Ca 1 & Ca 2 Theo Khuôn V1

### Ca 1: `docs/tdq/plan/2026-11-19-0046-dong-rust-binary-hook.md:155-171` (`T2.3`)

**Trước (nguyên bản — `17` dòng, `~408` tokens, `5/14`):**

```markdown
- [x] **T2.3** (e25m) Hiện thực sự kiện `PreToolUse` trong Rust — Test: `cargo test --manifest-path hooks/rust/tdq-dispatch/Cargo.toml --lib pre_tool_use`
  - Chạm: `hooks/rust/tdq-dispatch/src/events/pre_tool_use.rs`
  - Cần: T2.1
  - Mục tiêu: kiểm tra và thực thi 9 cổng chặn an toàn, phân tích câu lệnh dòng lệnh, cơ chế ân xá lần 1 cho tìm kiếm và tự động ghi đè tham số thiếu (`overwrite` cho LSP và Subagent Workspace).
  - Vị trí neo: tệp mới `hooks/rust/tdq-dispatch/src/events/pre_tool_use.rs`.
  - Công cụ: Dùng Write cho `pre_tool_use.rs`.
  - Ràng buộc: bám sát hành vi của 9 cổng chặn an toàn (`APPROVE`, `GIT`, `TEAM`, `STATE`, `READONLY`, `VUNG`, `ZERO-POPUP`, `SUBAGENT`, `UNFINISHED`), tự điền `language_id` thiếu cho `start_lsp`.
  - Đặc tả kỹ thuật:
    `fn handle_pre_tool_use(payload: &HookPayload, workspace_root: &Path) -> HookDecision`.
  - Logic cốt lõi:
    1. Bước 1: Trích xuất tên công cụ và đối số. Kiểm tra danh sách lệnh cấm phá hủy git (`git push`, `git reset --hard`) hoặc vượt sandbox.
    2. Bước 2: Kiểm tra công cụ `start_lsp`. Nếu thiếu `language_id`, tự động dò ngôn ngữ và trả về quyết định `overwrite`.
    3. Bước 3: Nếu gọi subagent, tự động điền `Workspace="inherit"` nếu chưa được thiết lập.
    4. Bước 4: Kiểm tra hành vi tìm kiếm mã nguồn; nếu vi phạm tầng tìm kiếm lần 1 thì xuất thẻ hướng dẫn 4 phần, nếu vi phạm liên tiếp lần 2 thì trả về `deny`.
  - Ca góc hiểm & TDD:
    - Ca hiểm: đối số công cụ là chuỗi JSON lồng nhau, lệnh PowerShell alias (`curl`, `wget`, `cat`), công cụ không xác định.
    - Tiêu chí: chặn đúng 100% các câu lệnh nguy hiểm trong bộ kiểm thử chuẩn.
```

Lỗi thực tế của bản Trước: gán nhầm `UNFINISHED` (cổng `Stop`) vào `PreToolUse`; liệt kê `9` cổng nhưng `Logic` chỉ viết `4` bước (bỏ trống `APPROVE`, `TEAM`, `STATE`, `READONLY`, `ZERO-POPUP`); sai kiểu trả về (`HookDecision` thay vì `RouteOutcome`); bịa logic `"vi phạm lần 1 xuất thẻ 4 phần"`; `Tiêu chí` `0` câu assert.

**Sau (viết theo V1 — buộc tách `T2.3a..T2.3c` để giữ `<= 5` bước/`Logic` & `<= 150` dòng, tổng `78` dòng, `~1,738` tokens, `14/14`):**

```markdown
- [ ] **T2.3a** (e10m) Tạo mới `pre_tool_use.rs` phần helper vai trò/path và cổng Edit (`READONLY`, `STATE`, `APPROVE`, `TICK`, `LOG`) — Test: `cargo test --manifest-path hooks/rust/tdq-dispatch/Cargo.toml --lib pre_tool_use`
  - Chạm: `hooks/rust/tdq-dispatch/src/events/pre_tool_use.rs`
  - Tham chiếu: `hooks/rust/tdq-dispatch/src/protocol.rs` (`HookPayload`, `NormalizedToolCall`, `GuidanceRepo`), `hooks/rust/tdq-dispatch/src/storage.rs` (`read_tdq_state`, `cong_dang_cho`, `read_plan_tick_state`, `count_code_edits_for_sha`, `read_sessions_role`, `queue_pending_reminder`)
  - Cần: `T1.3`, `T1.4`, `T2.1`
  - Vị trí neo: `hooks/rust/tdq-dispatch/src/events/pre_tool_use.rs` :: tạo mới (đã khai báo `pub mod pre_tool_use;` trong `events/mod.rs`)
  - Trước → Sau:
    - Trước: Chưa có xử lý `PreToolUse` trong Rust; sửa `state.json`, sửa code khi chưa duyệt/chưa tick `[~]`, hoặc subagent chỉ đọc sửa file không bị chặn ở tầng native.
    - Sau: `handle_edit_tool` chặn cứng (`Deny`) với thẻ 4 phần `[TDQ:READONLY]`, `[TDQ:STATE]`, `[TDQ:APPROVE]`, `[TDQ:TICK]` (`0`/`>1` `[~]`, streak `>= 8`), nhắc hàng đợi ở `4..7`, ghi `turns-<sid>.jsonl` và trả `DelegatePython` khi có subagent.
  - Công nghệ & Đặc tả: stdlib + `serde_json` (`Cargo.toml`); dùng `Write` tạo mới; chữ ký: `fn detect_subagent_role(payload: &HookPayload, root: &Path, sid: &str) -> Option<String>`, `fn is_readonly_role(role: &str) -> bool`, `fn check_tick_gates(root: &Path, sid: &str, state: &TdqState, rel: &str, in_docs: bool) -> Result<Option<String>, RouteOutcome>`, `fn handle_edit_tool(root: &Path, norm: &NormalizedToolCall, sid: &str, role: Option<&str>) -> RouteOutcome`.
  - Logic & Ràng buộc (<= 5 bước, <= 5 luật cục bộ):
    1. Bước 1: Trích `target_path()` (`Path`, `TargetFile`, `file_path`, `AbsolutePath`); thiếu path trả `Allow`.
    2. Bước 2: Nếu `is_readonly_role` (`reviewer|qc-tester|browser`) → `Deny` `READONLY`; nếu `is_state_target` (`docs/tdq/state.json` | `STATE.md`) → `Deny` `STATE`.
    3. Bước 3: Ngoài project trả `DelegatePython`; thiếu `state`/`active_request` trả `Allow`; có `role_opt` hoặc `implement_mode == "subagent"` trả `DelegatePython`.
    4. Bước 4: Ngoài `docs/` kiểm `cong_dang_cho` → `Deny` `APPROVE`; ngoài `docs/`/`tests/`/`.tdq-worktrees/` khi `implement`/`qc` chạy `check_tick_gates` (`0`/`>1` `[~]` hoặc `streak >= 8` → `Deny` `TICK`; `4..7` → `queue_remind_once`).
    5. Bước 5: Ghi `record_edit_observations` (`edit`, `log_written`/`LOG` remind, `code_edit` gắn `plan_sha`) và trả `Allow`.
    - Luật cục bộ: Cấm `.unwrap()` ở luồng chính; path Windows chuẩn hóa bỏ `\\?\` và đổi `\` → `/`; tái dùng `GuidanceRepo::format_4part_card`; chỉ đọc `state.json`.
  - Test Oracle (Red → Green):
    - Ca hiểm: `write_to_file` truyền `TargetFile` vào `docs/tdq/state.json`; plan có `0` `[~]` khi sửa `src.py`; sửa file trong `tests/` không kích hoạt `TICK`.
    - Tiêu chí: `assert_eq!(res.decision, DecisionKind::Deny)` + `reason.contains("[TDQ:STATE]")` · `reason.contains("[TDQ:TICK]")` · `assert_eq!(edit_in_tests.decision, DecisionKind::Allow)`.

- [ ] **T2.3b** (e10m) Hiện thực cổng lệnh shell (`handle_command_tool`) và đọc file (`handle_read_tool`) trong `pre_tool_use.rs` — Test: `cargo test --manifest-path hooks/rust/tdq-dispatch/Cargo.toml --lib pre_tool_use`
  - Chạm: `hooks/rust/tdq-dispatch/src/events/pre_tool_use.rs`
  - Tham chiếu: `hooks/rust/tdq-dispatch/src/command_parser.rs` (`is_shell_mutator`, `mutates_tdq_state`, `inspect_command_safety`, `has_banned_ai_branch`, `mutates_outside_docs`, `mutates_outside_docs_any`, `needs_python_command_gate`)
  - Cần: `T2.3a`
  - Vị trí neo: `hooks/rust/tdq-dispatch/src/events/pre_tool_use.rs` :: ngay sau `fn handle_edit_tool` (tham khảo ~dòng `306`)
  - Trước → Sau:
    - Trước: Chưa phân tích `run_command` / `read_file` trong `pre_tool_use.rs`; `git push`, `Set-Content` từ `qc-tester`, ghi `state.json` qua shell và nhánh `claude-*` không bị Rust chặn.
    - Sau: `handle_command_tool` chặn cứng `READONLY`/`STATE`/`GIT`/`VUNG`/`APPROVE` theo thứ tự ưu tiên, ủy quyền `DelegatePython` khi `needs_python_command_gate`; `handle_read_tool` trả `Allow` khi có range hoặc file `<= 2048` B, ngược lại `DelegatePython`.
  - Công nghệ & Đặc tả: stdlib + `command_parser`; dùng `Edit`; chữ ký: `fn handle_command_tool(payload: &HookPayload, root: &Path, sid: &str, role: Option<&str>) -> RouteOutcome`, `fn handle_read_tool(norm: &NormalizedToolCall, root: &Path) -> RouteOutcome`.
  - Logic & Ràng buộc (<= 5 bước, <= 5 luật cục bộ):
    1. Bước 1: Gọi `payload.get_command()` (`CommandLine`/`command`/`cmd`/`script`); thiếu lệnh trả `Allow`.
    2. Bước 2: Kiểm lần lượt `is_readonly_role && is_shell_mutator` (`READONLY`), `mutates_tdq_state` (`STATE`), `inspect_command_safety` (`GIT`/`VUNG`), `has_banned_ai_branch` (`GIT`).
    3. Bước 3: Khi `active_request` mở: subagent ngoài `implement`/`qc` chạy `mutates_outside_docs` → `DelegatePython`; leader chạy `mutates_outside_docs_any` khi còn `cong_dang_cho` → `Deny` `APPROVE`.
    4. Bước 4: `needs_python_command_gate(&cmd)` → `DelegatePython`, ngược lại `Allow`.
    5. Bước 5: Trong `handle_read_tool`, có `StartLine`/`EndLine`/`offset`/`limit`/`ByteOffset` hoặc `fs::metadata(full).len() <= 2048` → `Allow`, ngược lại `DelegatePython`.
    - Luật cục bộ: Giữ thứ tự guard `READONLY → STATE → safety → branch → APPROVE → python_gate`; cấm `.unwrap()`; tái dùng `command_parser`.
  - Test Oracle (Red → Green):
    - Ca hiểm: `tdq-qc-tester` chạy `Set-Content app.py bad`; lệnh `git push origin dev`; `read_file` không range trên file `> 2048` B.
    - Tiêu chí: `reason.contains("[TDQ:READONLY]")` · `reason.contains("[TDQ:GIT]")` · `matches!(read_big, RouteOutcome::DelegatePython)`.

- [ ] **T2.3c** (e10m) Hiện thực bộ định tuyến `handle_pre_tool_use`, `handle_mcp_tool` (`start_lsp` overwrite + concept ledger), `ZERO-POPUP` và unit test trong `pre_tool_use.rs` — Test: `cargo test --manifest-path hooks/rust/tdq-dispatch/Cargo.toml --lib pre_tool_use`
  - Chạm: `hooks/rust/tdq-dispatch/src/events/pre_tool_use.rs`
  - Tham chiếu: `hooks/rust/tdq-dispatch/src/events/post_tool_use.rs` (`extract_concept_label`), `hooks/rust/tdq-dispatch/src/protocol.rs` (`NormalizedToolCall::wrap_overwrite`), `hooks/rust/tdq-dispatch/src/storage.rs` (`search_ledger_path`, `khoa_hien_tai`)
  - Cần: `T2.3b`
  - Vị trí neo: `hooks/rust/tdq-dispatch/src/events/pre_tool_use.rs` :: ngay sau `fn handle_read_tool` (tham khảo ~dòng `414`)
  - Trước → Sau:
    - Trước: Chưa có entrypoint `handle_pre_tool_use`, chưa chặn `ask_question`, chưa auto-fill `language_id`/`root_dir` cho `call_mcp_tool` `start_lsp`, và chưa ghi `search_grace` trước LSP.
    - Sau: `handle_pre_tool_use` điều phối `ZERO-POPUP`, Edit, Command, Read, Grep (`DelegatePython`), Subagent (`DelegatePython`) và MCP (`start_lsp` bọc `Arguments` đúng kiểu + ghi `.tdq-search.jsonl`).
  - Công nghệ & Đặc tả: stdlib + `serde_json`; dùng `Edit`; chữ ký: `fn detect_unique_language_o1(dir: &Path) -> Option<&'static str>`, `fn handle_mcp_tool(root: &Path, norm: &NormalizedToolCall, sid: &str) -> RouteOutcome`, `pub fn handle_pre_tool_use(payload: &HookPayload, workspace_root: &Path) -> RouteOutcome`.
  - Logic & Ràng buộc (<= 5 bước, <= 5 luật cục bộ):
    1. Bước 1: Chuẩn hóa `norm = payload.normalize_tool_call()`, lấy `sid`, `role_opt = detect_subagent_role(...)`.
    2. Bước 2: `ask_question`/`ask_user_question`/`AskUserQuestion` → `Deny` `ZERO-POPUP`.
    3. Bước 3: Định tuyến các tool edit → `handle_edit_tool`; tool shell → `handle_command_tool`; tool read → `handle_read_tool`; tool grep/subagent → `DelegatePython`.
    4. Bước 4: Trong `handle_mcp_tool`, `blast_radius` → `DelegatePython`; `start_lsp` thiếu `language_id` gọi `detect_unique_language_o1` (`Cargo.toml`/`pyproject.toml`/`tsconfig.json`/`go.mod` có đúng `1` ngôn ngữ → `Allow.with_overwrite(norm.wrap_overwrite(patch))`, mơ hồ → `DelegatePython`).
    5. Bước 5: `extract_concept_label(norm, None)` khớp → ghi `.tdq-search.jsonl` (`PreToolUse`) + `search_grace` vào `turns-<sid>.jsonl`; mặc định `Allow`.
    - Luật cục bộ: Cấm overwrite khi `langs.len() != 1`; giữ kiểu `Arguments` string/object qua `wrap_overwrite`; viết `#[cfg(test)] mod tests`.
  - Test Oracle (Red → Green):
    - Ca hiểm: `call_mcp_tool` `start_lsp` với `Arguments` là JSON string không có `language_id`; `ask_question`; `grep_search`.
    - Tiêu chí: `assert!(ov["Arguments"].as_str().unwrap_or("").contains("rust"))` · `assert!(matches!(ask_res, RouteOutcome::Decided(d) if d.reason.unwrap().contains("[TDQ:ZERO-POPUP]")))` · `assert!(matches!(grep_res, RouteOutcome::DelegatePython))`.
```

### Ca 2A: `docs/tdq/plan/2026-11-19-1632-hybrid-hook-smart-hardening.md:86-101` (`T2.1`)

Bản gốc nhồi **8 file Rust** vào `1` task (`16` dòng, `~621` tokens, `8/14`), phần `Logic cốt lõi` chỉ nêu tên file và chỉ assert `2/12` cổng. Khi viết lại đúng theo trần V1 (`<= 2` file code & `<= 150` dòng sửa), `T2.1` buộc phải xé thành **`6` subtask (`T2.1a..T2.1f`, tổng `149` dòng, `~2,850` tokens, đạt `14/14`)**:

- `T2.1a` (e8m): Tạo mới `events/post_invocation.rs` + đăng ký `events/mod.rs` (`handle_post_invocation` O(1) stat `pending-reminders-<sid>.jsonl` → `HookDecision::inject`, `3` assert cho `"{}"`, `"injectSteps"`, idempotent pop).
- `T2.1b` (e12m): Tạo mới `events/pre_invocation.rs` + đăng ký `events/mod.rs` (`scan_tail_user_input` `65_536` B, `compute_user_turn_sig`, `handle_pre_invocation`, `3` assert cho `no_meta`, `mid_turn`, `turn_closed=true`).
- `T2.1c` (e12m): Sửa `command_parser.rs` (`5` hàm guard sau `has_banned_ai_branch`) + `post_tool_use.rs` (`is_graphify_shell_query`, `.tdq-search.jsonl`, `search_grace`, `3` assert phân biệt `Set-Content` vs `ls > /dev/null` vs `graphify query`).
- `T2.1d` (e10m): Sửa `session_start.rs` (`cap_markdown` cắt an toàn UTF-8 ở byte `1500`) + `stop_streak.rs` (`evaluate_open_plan_stop`, `handle_stop_streak`, `3` assert cho chuỗi `"ệ"` 3 byte, `[>]`, chuỗi `3` lần stop với `MAX_STREAK=2`).
- `T2.1e` (e12m): Sửa `pre_tool_use.rs` phần `handle_edit_tool` + `check_tick_gates` (`qc-tester`, `write_to_file`, `TICK` streak `8`, `3` assert cho `STATE`, `TICK`, miễn `tests/`).
- `T2.1f` (e12m): Sửa `pre_tool_use.rs` phần `handle_command_tool` (`is_shell_mutator`) + `handle_mcp_tool` (`wrap_overwrite`) + dispatch AGY 2.0 (`3` assert cho `qc-tester` shell mutator và `Arguments` dạng chuỗi).

*(Lưu ý thực chiến: cả `T2.1a..b` lẫn `T2.1e..f` đều tạo ra cặp task chạm chung file `events/mod.rs` và `pre_tool_use.rs` — tức tạo `2` **`HOT FILE`** mới chỉ từ 1 task gốc!)*

### Ca 2B: `docs/tdq/plan/2026-11-19-1632-hybrid-hook-smart-hardening.md:219-221` (`QC1.1`)

**Trước (`3` dòng, `~98` tokens, `2/14`):** `1` task liệt kê `5` mục (`tdq_state.py`, `search_rules.py`, `tdq_ccr.py`, `agy_dispatch.py`, `plugins/tdq-workflow-agy/`), không neo, không Trước → Sau, chạy test trên Python 3.13 cục bộ.

**Sau (viết theo V1 — buộc tách `QC1.1a..QC1.1c`, `45` dòng, `~930` tokens, `12–13/14`):**

```markdown
- [ ] **QC1.1a** (e2m) Bổ sung `from __future__ import annotations` và rà union runtime tại `tdq_state.py`, `search_rules.py` — Test: `py -3 -m pytest tests/test_state.py tests/test_search_rules.py -q`
  - Chạm: `scripts/tdq_state.py`, `scripts/search_rules.py`
  - Vị trí neo: `scripts/tdq_state.py` :: ngay sau docstring đầu tệp, trước `import hashlib` (~dòng `14`); `scripts/search_rules.py` :: ngay sau docstring, trước `import json` (~dòng `16`)
  - Trước → Sau:
    - Trước: Chú thích PEP 604 `str | None` được Python `3.9.6` trên `mbair` đánh giá lúc import và văng `TypeError`.
    - Sau: Cả `2` file có `from __future__ import annotations` ở đầu module và `0` lời gọi `isinstance(..., A | B)` runtime.
  - Công nghệ & Đặc tả: Python stdlib `ast` / future directive; dùng `Edit` chèn trước mọi `import`.
  - Logic:
    1. Bước 1: Chèn `from __future__ import annotations` ngay sau docstring ở `2` file.
    2. Bước 2: Quét `ast.walk` xác nhận `0` `BinOp(BitOr)` trong `isinstance`/`issubclass`.
  - Tiêu chí: `assert "from __future__ import annotations" in Path("scripts/tdq_state.py").read_text()` · `pytest` 2 file xanh và AST check `0` lỗi PEP 604 runtime.

- [ ] **QC1.1b** (e2m) Bổ sung `from __future__ import annotations` tại `tdq_ccr.py` và chuỗi `DISPATCH_PY` ở `agy_dispatch.py` — Test: `py -3 -m pytest tests/test_tdq_ccr.py tests/test_agy_plugin_validate.py -q`
  - Chạm: `scripts/tdq_ccr.py`, `tools/patches/agy_dispatch.py`
  - Vị trí neo: `scripts/tdq_ccr.py` :: sau docstring đầu tệp (~dòng `19`); `tools/patches/agy_dispatch.py` :: bên trong `DISPATCH_PY` trước `import importlib` (~dòng `14`)
  - Trước → Sau:
    - Trước: `DISPATCH_PY` và `tdq_ccr.py` có `list[str] | None` làm gãy Cold-path `dispatch.py` trên Python `3.9.6`.
    - Sau: Cả `2` vị trí mang `from __future__ import annotations` ở đầu module.
  - Công nghệ & Đặc tả: Python stdlib; dùng `Edit` giữ nguyên raw string `DISPATCH_PY`.
  - Logic: Chèn dòng future annotation ngay sau docstring ở `tdq_ccr.py` và trong chuỗi `DISPATCH_PY`, chạy test xác nhận.
  - Tiêu chí: `assert "from __future__ import annotations" in agy_dispatch.DISPATCH_PY` · `pytest` xanh `0` failed.

- [ ] **QC1.1c** (e2m) Đóng gói lại `plugins/tdq-workflow-agy/` sau vá Python `3.9` và kiểm định `--strict` — Test: `py -3 tools/build_agy_plugin.py && agy.EXE plugin validate plugins/tdq-workflow-agy --strict --json`
  - Chạm: `plugins/tdq-workflow-agy/manifest.json`
  - Cần: `QC1.1a`, `QC1.1b`
  - Vị trí neo: `tools/build_agy_plugin.py` :: hàm `build()` (tái sinh gói `plugins/tdq-workflow-agy/`)
  - Trước → Sau:
    - Trước: Gói đã build trong `plugins/tdq-workflow-agy/` giữ bản cũ thiếu `__future__`.
    - Sau: Gói được build lại đồng bộ, `agy validate --strict` trả `findings == []`, sẵn sàng smoke trên Python `3.9.6`.
  - Công nghệ & Đặc tả: CLI `build_agy_plugin.py` + `agy.EXE plugin validate`; cấm đụng plugin cài cục bộ (`2b`).
  - Logic: Chạy `build_agy_plugin.py`, rồi kiểm tra `dispatch.py` đích và `agy.EXE plugin validate`.
  - Tiêu chí: `assert data["findings"] == []` · `assert "from __future__ import annotations" in Path("plugins/tdq-workflow-agy/hooks/scripts/dispatch.py").read_text()`.
```

*(Ghi chú thực chiến: `QC1.1c` buộc phải giấu `plugins/tdq-workflow-agy/scripts/*.py` khỏi `Chạm:` để không đâm vào giới hạn `> 2` file code của V1!)*

---

## 3. Viết Lại Thực Chiến Ca 3 (Quick-Lane Audit & Quick-Lane Code)

### Ca 3A: `docs/tdq/plan/2026-11-19-1457-audit-sai-sot-noi-hook.md:1-34` (Quick Audit + `ANTI-2`)

Bản gốc gồm `T1..T3` + `QC.1` (`34` dòng, `~798` tokens): `T1` kiểm `os.path.exists` trên 2 file có sẵn; `QC.1` chạy `assert True` (`ANTI-2`); `T1` và `T2` đụng chung `Chạm:` vào cùng file report (`HOT FILE`), đạt **`0/14`**.

- **Kịch bản 1 — Theo đúng chữ nghĩa V1 §2.3(a):** V1 miễn thẻ chi tiết & `R15` cho mọi task không chứa `EXT_MA_NGUON`. Kết quả bản Sau vẫn giữ `34` dòng, **toàn bộ `T1` (`os.path.exists`) và `QC.1` (`assert True`) vẫn vượt `R15-Strict` nguyên vẹn**, chỉ đạt `4/14` nếu Planner không tự giác sửa!
- **Kịch bản 2 — Nếu ép áp Compact Card để đẩy điểm lên `12/14` (`~50` dòng, `~1,420` tokens):** Tách `T1` ghi ma trận vào `truoc-sau.archify.md` (hết `HOT FILE` với `T2`), thay `os.path.exists` bằng `assert 'TDQ:TICK' in t and 'PreInvocation' in t` và thay `QC.1` bằng kiểm assertion thật trên báo cáo — nhưng tổng số dòng lên **`50` dòng, phá vỡ trần `40` dòng** hiện giữ cho non-code quick-lane!

### Ca 3B: `docs/tdq/plan/2026-11-16-0058-dat-mac-dinh-ponytail-full.md:17-22` (Quick Code `muc_gat=full`)

**Trước (`32` dòng toàn file, task `6` dòng, `~688` tokens, `6.5/14`):** `T1` chạm `5` file (`.py`), lách `R15` bằng `1` dòng `- Đặc tả logic:`; `T2` chạm `5` file (`chung.md`, `token-budget.json`, `plugins/...`).

**Sau (viết theo V1 — tách `T1` thành `T1a` + `T1b` và thêm `Công nghệ & Đặc tả:` theo R15, toàn file tăng `32 → 61/80` dòng, `~1,330` tokens, đạt `13/14`):**

```markdown
## Task
- [ ] **T1a** (e4m) Đặt mặc định `MUC_GAT_MAC_DINH = "full"` trong `scripts/tdq_state.py` kèm unit test — Test: `py -3 -m unittest tests.test_state_muc_gat tests.test_state_muc_qc`
  - Chạm: `scripts/tdq_state.py`, `tests/test_state_muc_gat.py`, `tests/test_state_muc_qc.py`
  - Vị trí neo: `scripts/tdq_state.py` :: `MUC_GAT_MAC_DINH` & `normalize_muc_gat` (ngay sau `normalize_doc_lang`, tham khảo ~dòng `168–186`)
  - Trước → Sau:
    - Trước: `MUC_GAT_MAC_DINH = "ultra"`; `default_state()["muc_gat"]` và input rác rơi về `"ultra"`.
    - Sau: `MUC_GAT_MAC_DINH = "full"`; `normalize_muc_gat(None|"invalid")` trả `"full"`, giữ nguyên `MUC_QC_MAC_DINH = "full"` và giá trị tường minh `lite|full|ultra|off`.
  - Công nghệ & Đặc tả: Python stdlib; `Edit`; giữ nguyên chữ ký `normalize_muc_gat(raw) -> str` và `muc_gat_hieu_luc(state) -> str`.
  - Logic:
    1. Bước 1: Đổi `MUC_GAT_MAC_DINH = "full"` và cập nhật docstring tại `scripts/tdq_state.py`.
    2. Bước 2: Sửa assertion trong `tests/test_state_muc_gat.py` (đỏ → xanh), kiểm `test_state_muc_qc.py` giữ `"full"`.
  - Tiêu chí: `assert default_state()["muc_gat"] == "full"` · `assert normalize_muc_gat("bogus") == "full"` · `assert normalize_muc_gat("off") == "off"`.

- [ ] **T1b** (e3m) Đặt mặc định `MUC_MAC_DINH = "full"` trong `hooks/scripts/luat_gon.py` kèm unit test — Test: `py -3 -m unittest tests.test_luat_gon`
  - Chạm: `hooks/scripts/luat_gon.py`, `tests/test_luat_gon.py`
  - Vị trí neo: `hooks/scripts/luat_gon.py` :: `MUC_MAC_DINH` (ngay sau `CAT_THEO_MUC` và trước `def doc_than_luat`, tham khảo ~dòng `33`)
  - Trước → Sau:
    - Trước: `MUC_MAC_DINH = "ultra"` khiến `luat_gon` nạp phần `Extra at level ultra` khi thiếu `muc_gat`.
    - Sau: `MUC_MAC_DINH = "full"` (`loc_than_luat` cắt mục `RIGHT / WRONG` theo bảng `"full"`).
  - Công nghệ & Đặc tả: Python stdlib; `Edit`; giữ nguyên chữ ký `loc_than_luat(than, muc_gat)`.
  - Logic: Đổi `MUC_MAC_DINH = "full"` và docstring đầu file `luat_gon.py`, cập nhật `tests/test_luat_gon.py` đỏ → xanh.
  - Tiêu chí: `assert luat_gon.MUC_MAC_DINH == "full"` · `assert "Extra at level ultra" not in loc_than_luat(body, None)`.

- [ ] **T2** (e5m) Cập nhật bảng cường độ ở `chung.md`, relock `token-budget.json` và build lại gói AGY — Test: `py -3 scripts/doc_lint.py skills/tdq-build/references/rules/chung.md && py -3 scripts/token_budget.py --kiem`
  - Chạm: `skills/tdq-build/references/rules/chung.md`, `docs/tdq/token-budget.json`
  - Cần: `T1a`, `T1b`
  - Vị trí neo: `skills/tdq-build/references/rules/chung.md` :: bảng `Intensity table` (~dòng `141–150`)
  - Trước → Sau:
    - Trước: Dòng `ultra` mang nhãn `(the default)` trong `chung.md`; bản build `plugins/tdq-workflow-agy/` chưa đồng bộ.
    - Sau: Dòng `full` mang nhãn `(the default)`, `token-budget.json` được relock và gói AGY đồng bộ `MUC_GAT_MAC_DINH = "full"`.
  - Logic: Cập nhật bảng `chung.md`, chạy `token_budget.py`, rồi chạy `build_agy_plugin.py` và `install_agy_plugin.py`.
  - Tiêu chí: `doc_lint.py` exit `0` · `token_budget.py --kiem` exit `0` · bản build chứa `MUC_GAT_MAC_DINH = "full"`.
```

---

## 4. Sáu Ma Sát Thực Chiến Phát Hiện Khi Viết Thử (`C-1` .. `C-6`)

### Ma sát C-1: Bùng nổ task ở multi-file (`1 → 6`) VÀ tự tạo `HOT FILE` trên file đơn đa hàm (`pre_tool_use.rs`)
- **Bằng chứng:** `1632:T2.1` phình `1 → 6` subtask (`16 → 149` dòng, `9.31×`); nếu tách toàn bộ `1632`, cả plan phình từ `13` lên `~25–28` task (`~550–650` dòng). Ngược lại `0046:T2.3` chỉ có `1` file (`pre_tool_use.rs`, `632` dòng, `15` hàm) nên lọt kiểm file `<= 2`, và khi tách thành `T2.3a..c` thì chính nó thành `HOT FILE` khóa song song (tương tự `events/mod.rs` ở `T2.1a..b`).
- **Hướng vá V2:** Giới hạn kích thước theo **file-unit** kết hợp đếm **số hàm/nhánh rẽ trong cùng file** (`> 4` symbol cần tách), đồng thời nâng việc sửa file đăng ký (`mod.rs`, `manifest.json`) lên wave hợp đồng sớm.

### Ma sát C-2: Mâu thuẫn spec nội tại giữa §2.3 (khuôn rút gọn 5 trường) và §4.1 (`R15-Strict` đòi `Công nghệ & Đặc tả:`)
- **Bằng chứng:** `de-xuat-v1.md` §2.3 quy định `QC fix` và `quick-lane` chỉ cần `5` trường (`Chạm:`, `Vị trí neo:`, `Trước → Sau:`, `Logic:`, `Tiêu chí:`), nhưng §4.1 `R15-Strict` ép mọi task có `EXT_MA_NGUON` phải có `Công nghệ & Đặc tả:` — nếu viết đúng §2.3 thì trượt `R15`; nếu thêm để qua `R15` thì `11-16-0058` chạm `61/80` dòng dù chỉ đổi `1` hằng số.
- **Hướng vá V2:** Tách `2` profile chính thức trong `R15`: `R15-Full` (cho task code lane `full`) và `R15-Compact` (`5` trường cho `QCn.x` và `quick-lane` code, cho phép gộp chữ ký vào `Trước → Sau`).

### Ma sát C-3: Luật `<= 2` file code bẻ vụn "Mechanical Sweep" và không biểu diễn được lệnh Build/Sync nguyên tử (`QC1.1`, `11-16-0058:T2`)
- **Bằng chứng:** Thêm cùng `1` dòng `from __future__ import annotations` vào `4` file bị ép xé `3` task giống hệt nhau (`3 → 45` dòng, `15×`). Còn `build_agy_plugin.py` sinh lại ~50 file trong `plugins/tdq-workflow-agy/` — liệt kê file build vào `Chạm:` vi phạm trần `<= 2` file, còn ghi thư mục lại vi phạm `ANTI-6`, ép người viết `QC1.1c`/`T2` phải ẩn đường dẫn build.
- **Hướng vá V2:** Thêm ngoại lệ **Uniform Mechanical Sweep** (`<= 6` file cho cùng `1` phép biến đổi đồng nhất tại `1` neo cố định), và bổ sung trường **`Sinh ra:`** (generated outputs từ lệnh build) tách khỏi `Chạm:`.

### Ma sát C-4: Điểm mù `tdq_plan_scaffold.py` với file Tạo mới (Greenfield) khi thiếu `--refs` (`0046:T2.3`, `1632:T2.1a,b`)
- **Bằng chứng:** Khi tạo file mới (`pre_tool_use.rs`, `pre_invocation.rs`, `post_invocation.rs`), chạy Scaffolder trên `--files <spec §2b>` của file đích chỉ trả về rỗng. Toàn bộ chữ ký bắt buộc (`RouteOutcome`, `HookPayload`, `wrap_overwrite`, `is_shell_mutator`, `cong_dang_cho`) lại nằm ở file **`Tham chiếu:`**.
- **Hướng vá V2:** Thêm `--refs <module1,module2>` cho `tdq_plan_scaffold.py` để trích chữ ký AST của cả module phụ thuộc và bản đối chứng ngôn ngữ.

### Ma sát C-5: Bỏ lọt hoàn toàn Quick-lane Non-Code, Config/Shell (`11-19-1457`) và `ANTI-2` ngoài mã nguồn
- **Bằng chứng:** Vì V1 chỉ kích hoạt `R15-Strict` cho `EXT_MA_NGUON` (bỏ sót `.md`, `.json`, `.toml`, `.yml`, `.sh`, `.ps1`), toàn bộ `T1` (`os.path.exists`) và `QC.1` (`assert True`) trong `11-19-1457` lọt sạch qua `R15`. Nhưng ép Compact Card vào non-code lại đẩy file vượt trần `40` dòng.
- **Hướng vá V2:** Tách kiểm **`ANTI-2`** chạy độc lập trên **100% task/QC/DoD** (kể cả non-code), đưa nhóm cấu hình/shell (`EXT_CAU_HINH`) vào kiểm neo + oracle tối thiểu, và chỉ giữ rule chống trùng `Chạm:` + `Test:` có nghĩa cho non-code `quick-lane` (`<= 40` dòng).

### Ma sát C-6: Nguy cơ gãy `R12` tiếng Việt, rò `in_fence` trong `tdq_team.doc_plan` và thiếu đọc `Chạm:` nhiều dòng ở `doc_lint.py`
- **Bằng chứng:** Viết chữ ký nhiều dòng không dấu tiếng Việt ngoài code fence dễ dính `R12` (`doc_lint.py:663-716`); ngay cả khi bọc code fence thụt lề `4` khoảng trắng đúng V1, `tdq_team.doc_plan` (`:162-174`) không có cờ `in_fence` nên vẫn nhầm dòng ví dụ `- Chạm:` trong fence thành `Chạm:` thật; và `doc_lint.rule_r15` (`:558`) mới đọc `Chạm:` trên đúng `1` dòng đơn nên sẽ trượt nếu path bọc xuống sub-bullet.
- **Hướng vá V2:** Bổ sung theo dõi `in_fence` vào `tdq_team.doc_plan`, nâng cấp gom khối `Chạm:` nhiều dòng đồng bộ giữa `tdq_team.py`, `tdq_state.py`, và `doc_lint.rule_r15`.
