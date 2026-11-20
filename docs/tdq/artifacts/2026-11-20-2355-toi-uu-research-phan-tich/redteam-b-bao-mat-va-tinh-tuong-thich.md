# Kiểm Toán Red-Team B — Bảo Mật `scoped-write`, Tương Hợp `Python ↔ Rust`, Test Pinning & Linter/Budget (V1)

> **Phạm vi kiểm toán:** Phản biện đối kháng bản đề xuất `docs/tdq/artifacts/2026-11-20-2355-toi-uu-research-phan-tich/de-xuat-kien-truc-v1.md` (M1–M6) trực tiếp trên mã nguồn, hook, trình biên dịch plugin AGY, Rust dispatcher (`tdq-dispatch`), linter và bộ test hiện hành trên đĩa.
> **Mục tiêu:** Bắt trọn các lỗ hổng leo thang đặc quyền, bypass đường dẫn Windows, bẫy False-Positive/Race ở `run_command`, test pinning bị gãy, xung đột trần dòng/token/i18n và sập hiệu năng hot-path trước khi chốt V2.

---

## Tóm tắt Điều hành

Phiên bản V1 giải quyết đúng điểm nghẽn chi phí cho luồng nghiên cứu/phân tích (`work_kind=investigate`, `no_worktree`, `scoped-write`, `evidence-log`), nhưng **sẽ làm gãy hàng loạt test đang pin chặt**, **mở 3 lỗ hổng bảo mật/toàn vẹn nghiêm trọng trên Windows** và **đánh sập tốc độ hot-path Rust ở `pre_tool_use.rs:444`** nếu triển khai nguyên trạng:

| Mã | Mức độ | Trụ cột xung đột / Lỗ hổng cốt lõi | Tác động nếu giữ V1 |
|---|---|---|---|
| **ND-B1** | **Cao** | Bề mặt `scoped-write`: substring `"reviewer" in "tdq-security-reviewer"`, `canonical_or_ancestor` 1 cấp + Windows 8.3/symlink, wildcard đè `evidence.jsonl`/`eval`, lệch khóa target & fallback `DelegatePython` | Leo thang đặc quyền ghi cho `tdq-security-reviewer`, bypass ra ngoài `artifacts/`, hỏng toàn vẹn bằng chứng & rơi hot-path |
| **ND-B2** | **Cao** | `run_command` chặn oan `tdq_team.py evidence add` (`--claim` chứa `rm`/`mv`/`write_text`), thiếu `cmd /c` & `[IO.File]` ở `bash_gate`/`command_parser.rs`, race condition `blackboard_record` | Worker bị chặn `[TDQ:READONLY]` khi ghi bằng chứng, cửa sau ghi file trên Windows, mất cập nhật khi 4–5 worker chạy song song |
| **ND-B3** | **Cao** | 6 nhóm / 8 tệp test pin cứng bị gãy (`READONLY_AGENTS`, `ReadOnlyAgentToolsTest`, bộ 22 mã AGY, `test_reviewer_is_optional_only`, `qc.md`, `R10Test`/`rule_r10`) | Bộ kiểm thử đơn vị và parity `Python ↔ Rust` đỏ rực ngay sau khi sửa M1–M6 |
| **ND-B4** | **Cao** | Cạn trần `SKILL_LINE_LIMITS` (0 dòng ở `tdq-conventions`/`tdq-intake`), cạn trần 3,500 token `R13` (chỉ còn 14–28 token), `i18n_check`, `tdq_plan_scaffold.py --verify-plan` & bẫy `no_worktree` | Gãy `doc_lint` (`R6`, `R10`, `R13`), `i18n_check`, `--verify-plan` và bị `subagent_dispatch_gate`/`canh_bao_lach_luat` tuýt còi giả |
| **ND-B5** | **Cao** | Bỏ early-return ranged reads ở `pre_tool_use.rs:444` ép mọi `read_file`/`view_file` qua Python; `_dem_lap_doan` & lệch schema `post_tool_use.rs` vs `read_gate.py` | Mất hiệu năng `<0.5ms` thành ~80–150ms/lần đọc, tranh chấp `.tdq-read.jsonl.lock`, sai bộ đếm checkpoint giữa nhiều worker |
| **ND-B6** | **TB** | Tràn ngưỡng `MAX_CHARS = 600` của `SessionStart` (`next_headline`), `handoff-schema.json` từ chối `no_worktree`, lệch `PHASE_TABLE` & thiếu đồng bộ `tools/patches/` | Cắt cụt `Done when:` khi khởi động phiên, `subagent_stop.py` chặn handoff của `tdq-explorer`, plugin compiled lệch bản gốc |

---

## Chi tiết các Phát hiện Kiểm toán (`ND-B1` → `ND-B6`)

### ND-B1 [Cao] — Bề mặt bảo mật `scoped-write`, Leo thang `tdq-security-reviewer`, Symlink/8.3 Windows & Rơi hot-path

1. **Vị trí xác minh trên đĩa:**
   - `hooks/scripts/edit_gate.py:84, 91-101, 110` và `plugins/tdq-workflow-agy/hooks/scripts/edit_gate.py:98-108`
   - `plugins/tdq-workflow-agy/hooks/scripts/_common.py:332-336, 926`
   - `hooks/rust/tdq-dispatch/src/protocol.rs:280-296`
   - `hooks/rust/tdq-dispatch/src/events/pre_tool_use.rs:58-72, 110-122, 162-178, 290-302, 333-335`
   - `scripts/tdq_state.py:2645` (receipt `eval`)

2. **Cơ chế khai thác & Xung đột:**
   - **Leo thang đặc quyền do so khớp chuỗi con (Substring Spoofing):**
     Cả Python (`hooks/scripts/edit_gate.py:96`: `any(r in role for r in ("reviewer", "qc-tester", "browser", "explorer", "debugger"))`) lẫn Rust (`pre_tool_use.rs:65-72`: `low.contains("reviewer") || ...`) đều kiểm tra vai trò bằng `in` / `contains`. Do `"reviewer"` là chuỗi con của `"tdq-security-reviewer"`, nếu V1 nới quyền `scoped-write` cho nhóm `"reviewer"` mà vẫn dùng kiểu so khớp này (hoặc không đặt nhánh từ chối `security-reviewer` lên trước), `tdq-security-reviewer` sẽ **vô tình nhận quyền ghi tệp**, vi phạm nghiêm trọng nguyên tắc tối thiểu đặc quyền của kiểm toán bảo mật độc lập.
   - **Vượt rào đường dẫn qua Symlink/Junction nhiều tầng & Windows 8.3 Short Path:**
     Tại `pre_tool_use.rs:110-122` (`canonical_or_ancestor`), khi `path` chưa tồn tại, hàm chỉ gọi `fs::canonicalize(parent)` đúng **1 cấp**. Nếu subagent ghi vào đường dẫn sâu nhiều thư mục con chưa tồn tại xuyên qua một symlink hoặc NTFS junction (ví dụ `docs/tdq/artifacts/<slug>/link_out/sub/evil.md`), `fs::canonicalize(parent)` thất bại và rơi vào nhánh `unwrap_or_else(|_| path.to_path_buf())`, giữ nguyên chuỗi chưa giải phân giải. Tương tự trên Windows dùng tên ngắn 8.3 (như `ADMINI~1`), khi thư mục `docs/tdq/artifacts/<active_slug>/` chưa tạo, chuỗi trả về sẽ không chuẩn hóa khớp với `workspace_root`. Đồng thời ở `pre_tool_use.rs:171-173` (`is_qc_report_target`), `normalize_lexical(&abs_raw)` chạy **trước** `resolve_rel_in_project(&lexical_str, workspace_root)`, tạo kẽ hở lệch giữa đường dẫn từ vựng và đường dẫn vật lý qua symlink.
   - **Wildcard `.md`/`.json`/`.jsonl` quá rộng phá hoại tính toàn vẹn bằng chứng & cô lập agent:**
     Nếu V1 cho phép `scoped-write` ghi trực tiếp mọi tệp dưới `docs/tdq/artifacts/<active_slug>/...` và `docs/tdq/research/<active_slug>-*.md`:
     1. Một worker có thể dùng `write_file`/`edit_file` ghi đè hoặc sửa lén các tệp nhật ký/receipt nhạy cảm nằm cùng vùng hoặc vùng con: `evidence.jsonl`, `evidence.json`, `evidence-log.md`, `trial_*.json`, `rec_*.json` (`scripts/tdq_state.py:2645`).
     2. Mẫu `docs/tdq/research/<slug>-*.md` nếu không khóa chặt dấu `/` sau `research/` sẽ cho phép tạo nhánh con hoặc ghi đè báo cáo không thuộc phạm vi task.
   - **Lệch chuẩn hóa khóa đường dẫn & bẫy `DelegatePython` ở `pre_tool_use.rs:333`:**
     `hooks/scripts/edit_gate.py:84, 110` ở gốc repo chưa có `_normalize_tool_aliases` như plugin (`_common.py:332-336`) và Rust (`protocol.rs:280-296`), dễ lệch khi nhận `TargetFile` vs `Path` vs `file_path`. Quan trọng hơn, ở `pre_tool_use.rs:333-335` (`if role_opt.is_some() || state.implement_mode.as_deref() == Some("subagent") { return RouteOutcome::DelegatePython; }`), nếu nhánh `scoped-write` chỉ "không chặn" rồi rơi xuống sau dòng `296`, mọi lượt ghi artifact hợp lệ của `tdq-explorer`/`tdq-debugger`/`tdq-reviewer` đều bị đẩy về Python subprocess thay vì chốt ngay tại Rust. Ngoài ra khi `role` rơi về chuỗi mặc định `"subagent"` (`pre_tool_use.rs:58-62` vs `_common.py:926`), không thể tự động suy diễn quyền `scoped-write`.

3. **Đề xuất sửa V2 cho ND-B1:**
   - **Allowlist tên vai trò chuẩn hóa chính xác + Deny-first:** Dùng tập khớp chính xác sau khi `strip().lower()`: `_SCOPED_ARTIFACT_ROLES = frozenset({"tdq-explorer", "explorer", "tdq-debugger", "debugger", "tdq-reviewer", "reviewer"})`, và **kiểm tra chặn trước** đối với `"security-reviewer"`, `"browser"`, và fallback `"subagent"` không xác định.
   - **Canonicalize đệ quy ngược tổ tiên trước khi đối chiếu prefix:** Trong cả Rust (`canonical_or_ancestor`) và Python, leo vòng lặp `ancestors()` lên tới thành phần đầu tiên thực sự tồn tại trên đĩa để gọi `fs::canonicalize` / `os.path.realpath` (xử lý triệt để Windows 8.3 short paths & NTFS junction ở mọi độ sâu), kiểm tra không có reparse point/symlink trỏ ra ngoài `workspace_root` trên mọi thành phần, rồi mới ghép đuôi phần tử mới và đối chiếu prefix `docs/tdq/artifacts/<active_slug>/` (hoặc `docs/tdq/research/`).
   - **Denylist bất khả xâm phạm trong vùng `scoped-write`:** Cấm tuyệt đối `write_file`/`edit_file` trực tiếp vào `evidence.jsonl`, `evidence.json`, `evidence-log.md`, `trial_*.json`, `rec_*.json` (các tệp này chỉ được ghi gián tiếp qua CLI có khóa của `tdq_team.py evidence add`). Khóa mẫu `docs/tdq/research/` chỉ chấp nhận file phẳng một cấp `docs/tdq/research/<active_slug>.md` hoặc `docs/tdq/research/<active_slug>-<basename>.md` (cấm `/` trong `<basename>`).
   - **Đồng bộ alias + Allow trực tiếp tại Rust:** Bổ sung `_normalize_tool_aliases` đồng nhất giữa root và plugin; tại `pre_tool_use.rs`, khi `role` thuộc nhóm `scoped-write` và đích vượt qua mọi kiểm tra trên, trả về `RouteOutcome::Decided(HookDecision::allow())` trực tiếp ở Rust (sau khi cập nhật log quan sát tương ứng nếu cần), không rơi xuống `L333` `DelegatePython`.

---

### ND-B2 [Cao] — Bẫy `run_command` trên `tdq_team.py evidence add`, Cửa sau `cmd /c` / `[IO.File]` & Race `blackboard_record`

1. **Vị trí xác minh trên đĩa:**
   - `hooks/scripts/bash_gate.py:80, 87-90, 235-257, 387`
   - `plugins/tdq-workflow-agy/hooks/scripts/bash_gate.py:280-430`
   - `hooks/rust/tdq-dispatch/src/command_parser.rs:161-221, 280, 395-406`
   - `scripts/tdq_team.py:2480-2524` (`blackboard_record`)
   - `plugins/tdq-workflow-agy/hooks/scripts/_common.py` (`with_ntfs_lock`)

2. **Cơ chế khai thác & Xung đột:**
   - **False-Positive `[TDQ:READONLY]` khi ghi bằng chứng qua CLI:**
     Tại `hooks/scripts/bash_gate.py:238`, bộ lọc chạy `if _PS_WRITE_PATTERN.search(cmd) or re.search(r"\b(?:tee|rm|mv)\b|\bsed\s+-i\b", cmd): return True` **trước khi** tách phân đoạn (`_split_shell_segments`) và **trước khi** che chuỗi trong ngoặc (`_mask_quoted_shell_ops`). Đồng thời `bash_gate.py:80` và `command_parser.rs:205` dùng regex `\b(?:python3?|py)\b.*\b(?:open\([^)]*['"](?:w|a|x)['"]|write_text\b|...)`.
     Khi `tdq-explorer` hoặc `tdq-debugger` thực thi:
     `py -3 scripts/tdq_team.py evidence add --claim "... xử lý write_text / rm file ..."`
     chỉ cần đoạn mô tả trong `--claim` hoặc `--excerpt` nhắc tên hàm `write_text`, `open(..., 'w')`, `Set-Content`, `rm`, `mv`, `tee`, lệnh sẽ bị nhận diện nhầm là shell mutator và bị chặn bởi `[TDQ:READONLY]`! Thêm vào đó, nếu chạy ở phase `analyze`/`spec`/`plan` (trước `implement`), `bash_gate.py:387` / `command_parser.rs:280` còn nguy cơ kích `[TDQ:TEAM]` không đáng có; và khi RTK bật, `command_parser.rs:398-404` (`RE_RTK_CLI`) đẩy mọi lệnh `py`/`python` sang Python qua `needs_python_command_gate`.
   - **Lỗ hổng Bypass ghi file trên Windows trong `bash_gate` & `command_parser.rs`:**
     - `_SHELL_WRAPPER_RE` (`bash_gate.py:88`, `command_parser.rs:165`) kiểm tra `bash|sh|zsh|dash|ksh|pwsh|powershell(?:\.exe)?` nhưng **bỏ sót `cmd` / `cmd.exe`** (ví dụ `cmd /c "echo hacked > src/main.py"` hoặc lồng biến/dấu nháy).
     - `_PS_WRITE_PATTERN` không bắt các API .NET ghi trực tiếp như `[System.IO.File]::WriteAllText(...)` hoặc `[IO.File]::WriteAllBytes(...)`.
     - Nếu `scoped-write` hoặc read-only subagent có quyền chạy `run_command` (ví dụ để gọi `tdq_team.py evidence add` hoặc `doc_lint.py`), tin tặc hoặc prompt-injection có thể dùng 2 vector trên để ghi file bất kỳ ngoài vùng kiểm soát.
   - **Race condition mất dữ liệu ở `blackboard_record` (`scripts/tdq_team.py:2480-2524`):**
     `blackboard_record` đọc-sửa-ghi tệp `.tdq-runtime/blackboard/<slug>.json` **không có khóa NTFS** (`with_ntfs_lock` có trong `_common.py` nhưng không được dùng ở đây). Khi V1 cho 4–5 worker `no_worktree` chạy song song trong cùng một workspace và đồng loạt gọi `tdq_team.py evidence add`, các lượt cập nhật blackboard và `evidence-log.md` sẽ ghi đè lẫn nhau hoặc làm hỏng JSON.

3. **Đề xuất sửa V2 cho ND-B2:**
   - **Tách dữ liệu trích dẫn khỏi dòng lệnh:** Sửa `tdq_team.py evidence add` hỗ trợ `--claim-file` / `--excerpt-file` (đọc nội dung từ tệp artifact `.md` mà worker vừa viết qua `write_file` đã qua `scoped-write`) hoặc `--stdin-json`. Khi worker không truyền chuỗi tự do vào command line, lệnh gọi trở nên sạch 100%, loại bỏ triệt để false-positive của `rm`/`mv`/`write_text` mà **tuyệt đối không phải nới lỏng cho `py`/`python` tổng quát**.
   - **Whitelist hẹp cho `evidence add` + Vá 2 vector bypass Windows:** Nếu cho phép `tdq-explorer`/`debugger`/`reviewer` gọi `evidence add` qua `run_command`, chỉ cho phép khớp regex nguyên khối không có toán tử chuỗi shell (`;`, `&&`, `||`, `|`, `>`, `>>`, `` ` ``, `$()`), và từ chối mọi `cmd` wrapper. Song song đó, bổ sung `cmd(?:\.exe)?\b\s+/c` vào `_SHELL_WRAPPER_RE` và `\[(?:System\.)?IO\.File\]::` vào `_PS_WRITE_PATTERN` ở **cả** `hooks/scripts/bash_gate.py` và `hooks/rust/tdq-dispatch/src/command_parser.rs`.
   - **Khóa NTFS cho `evidence.jsonl` & `blackboard_record`:** Bọc khóa `msvcrt.locking` (tương đương `with_ntfs_lock`) cho mọi thao tác cập nhật `.tdq-runtime/blackboard/<slug>.json` tại `scripts/tdq_team.py:2480-2524`, thực hiện append nguyên tử từng dòng vào `evidence.jsonl`, và dựng lại `evidence-log.md` một cách tất định ngay bên trong vùng khóa.

---

### ND-B3 [Cao] — Hàng loạt Unit Test hiện hữu bị gãy trực tiếp bởi V1 (`tests/`)

1. **Vị trí xác minh trên đĩa:**
   - `tests/test_agent_frontmatter.py:27-32, 119-139`
   - `tests/test_skill_shape.py:29-43`
   - `tests/test_gate_guidance.py:28-41, 55-86`
   - `tests/test_hooks_dual_protocol.py:28-32, 71-76`
   - `tests/test_rust_dispatch_parity.py:43-51, 679-685`
   - `tests/test_gate_merge.py:44-55`
   - `tests/test_muc_qc_qc_md.py:46-85`
   - `tests/test_doc_lint.py:173-175, 361-376` & `scripts/doc_lint.py:441-458`

2. **Các Test bị gãy & Nguyên nhân cụ thể:**

| File & Hàm test bị gãy | Dòng pin cứng hiện tại | Lý do V1 làm gãy test |
|---|---|---|
| `tests/test_agent_frontmatter.py` (`test_built_agy_agents_tools_and_readonly_notices`) | `L27-32`, `L119-139` | Pin `READONLY_AGENTS = ("tdq-reviewer.md", "tdq-security-reviewer.md", "tdq-explorer.md", "tdq-debugger.md")` phải có `tools & AGY_WRITE_TOOLS == set()` và chứa `"[TDQ:READONLY]"` trong body. V1 M2/M6 cấp quyền ghi artifact / đổi nhãn sẽ làm assert thất bại ngay |
| `tests/test_skill_shape.py` (`ReadOnlyAgentToolsTest`) | `L29-43` | Pin `NAMES = ("tdq-qc-tester.md", "tdq-reviewer.md")` không được khai báo `Edit`/`Write` trong frontmatter `tools:` của tệp gốc `agents/<name>` |
| `tests/test_gate_guidance.py`, `tests/test_hooks_dual_protocol.py`, `tests/test_rust_dispatch_parity.py` | `L28-86`, `L28-76`, `L43-51` & `L679-685` | Cả 3 bộ test đều pin cứng **đúng 22 mã AGY** (`ALL_AGY_CODES`, `EXPECTED_22_CODES`, `MATRIX_CASES`). Đề xuất thêm mã thứ 23 `"CHECKPOINT"` trong V1 M3 làm sập toàn bộ 3 bộ test đồng bộ hóa Python/JSON/Rust |
| `tests/test_gate_merge.py` (`test_reviewer_is_optional_only`) | `L44-55` | Khóa tối đa `<= 1` dòng nhắc `"tdq-reviewer"` trong `tdq-spec/SKILL.md` và `tdq-plan/SKILL.md`, bắt buộc khớp regex tùy chọn (`user asks\|optional\|when needed\|user yêu cầu\|tùy chọn\|khi cần`). Nếu V1 biến `tdq-reviewer` thành mặc định/bắt buộc hoặc chèn >1 dòng vào 2 skill này, test gãy ngay |
| `tests/test_muc_qc_qc_md.py` | `L46-85` | Khóa chính xác tập giá trị cột của bảng QC (`lite`, `full`, `ultra` với `{"CÓ", "KHÔNG", "CÓ (vùng chạm)", "CÓ (trọn suite)"}`). Mọi biến đổi bảng để gài `investigate` vào bảng đó sẽ gãy test |
| `tests/test_doc_lint.py` (`R10Test`, `test_repo_docs_clean`) & `scripts/doc_lint.py` (`rule_r10`) | `L173-175`, `L361-376`; `doc_lint.py:441-458` | `rule_r10` ép mọi spec `Lane: full` phải có mục `## 2b. Ranh giới module`. V1 M5 bỏ `§2b` cho `Work kind: investigate` nhưng quên không đề cập sửa `rule_r10`, khiến mọi spec `investigate` ở `Lane: full` bị `doc_lint` từ chối |

3. **Đề xuất sửa V2 cho ND-B3:**
   - **Phân tách nhóm `agent_frontmatter` rõ ràng:** Trong `tests/test_agent_frontmatter.py`, tách `READONLY_AGENTS` thành `_STRICT_READONLY_AGENTS = ("tdq-security-reviewer.md",)` (giữ nguyên `[TDQ:READONLY]` và 0 write tools) và `_SCOPED_INVESTIGATION_AGENTS = ("tdq-explorer.md", "tdq-debugger.md", "tdq-reviewer.md")` (kiểm định chỉ có quyền `scoped-write` vào artifact + research và mang notice `[TDQ:SCOPED-WRITE]`). Với `agents/<name>` gốc ở `ReadOnlyAgentToolsTest`, cập nhật có chủ đích hoặc giữ nguyên frontmatter nếu dùng cấu hình scoped riêng cho AGY build trong `tools/patches/skills_and_agents.py`.
   - **Loại bỏ mã thừa `"CHECKPOINT"` (Phương án A khuyến nghị):** Tái sử dụng mã `"DOC"` hiện có kèm nội dung thông điệp chỉ rõ checkpoint (ví dụ `[TDQ:DOC] Checkpoint: ghi bằng chứng sau N lượt đọc...`) để bảo toàn nguyên vẹn 22 mã AGY trên cả JSON, Python, Rust và 3 bộ test parity. Nếu V2 vẫn quyết định thêm mã `"CHECKPOINT"` (Phương án B), bắt buộc lập task riêng đồng bộ cả 6 tệp (`tools/patches/gate_guidance.json`, `_common.py`, `gate_guidance.py`, `test_gate_guidance.py`, `test_hooks_dual_protocol.py`, `test_rust_dispatch_parity.py`).
   - **Bảo vệ `test_reviewer_is_optional_only` & `test_muc_qc_qc_md.py`:** Giữ nhắc nhở về `tdq-reviewer` trong `tdq-spec/SKILL.md` và `tdq-plan/SKILL.md` đúng `<= 1` dòng kèm từ khóa `khi cần` / `tùy chọn`; đẩy hướng dẫn chi tiết sang `references/`. Trong `qc.md`, **không chạm vào bảng `lite/full/ultra`**, tách phần QC cho `investigate` (đối chiếu `path:line`, kiểm định không sửa code) thành một tiểu mục riêng bên dưới hoặc liên kết tới `investigate-mode.md`.
   - **Cập nhật `doc_lint.rule_r10`:** Sửa `scripts/doc_lint.py:441-458` nhận diện spec có `Work kind: investigate` để miễn yêu cầu `## 2b. Ranh giới module` có điều kiện (chỉ miễn khi có dòng đầu mục khai báo hợp lệ `Work kind: investigate`), đồng thời bổ sung test dương/âm tương ứng vào `R10Test` (`tests/test_doc_lint.py:361-376`).

---

### ND-B4 [Cao] — Cạn trần `SKILL_LINE_LIMITS`, `token-budget` (`R13`), `i18n_check.py`, `--verify-plan` & Xung đột `no_worktree`

1. **Vị trí xác minh trên đĩa:**
   - `scripts/doc_lint.py:36-125, 441-458` (`SKILL_LINE_LIMITS`, `R6`, `R10`, `R13`)
   - `docs/tdq/artifacts/2026-11-20-2355-toi-uu-research-phan-tich/phan-tich-kien-truc-codebase.md` (§5 về số dòng & token budget)
   - `tests/test_plan_v2_linter.py:119` (`SKILL_LINE_LIMITS["tdq-plan"] == 132`)
   - `scripts/i18n_check.py`, `scripts/token_budget.py`, `tests/test_agy_plugin_validate.py:135`
   - `scripts/tdq_plan_scaffold.py:659-668, 885-894, 913-925` (`_is_new_file_in_task`, `_finalize_tasks`, `_verify_single_task`)
   - `tools/patches/agy_hooks.py:1463-1469` (`subagent_dispatch_gate.py`)
   - `scripts/tdq_team.py:1788-1797` (`canh_bao_lach_luat`), `2625-2633` (`_build_packet_payload`)
   - `scripts/tdq_bench.py:283`

2. **Cơ chế xung đột & Hậu quả:**
   - **Hết sạch khoảng trống `SKILL_LINE_LIMITS` (`R6`):**
     - `skills/tdq-conventions/SKILL.md`: **209 / 209** dòng (dư **0** dòng).
     - `skills/tdq-intake/SKILL.md`: **148 / 148** dòng (dư **0** dòng).
     - `skills/tdq-build/SKILL.md`: **172 / 174** dòng (dư **2** dòng).
     - `skills/tdq-spec/SKILL.md`: **97 / 100** dòng (dư **3** dòng).
     - `tests/test_plan_v2_linter.py:119` khóa cứng `SKILL_LINE_LIMITS["tdq-plan"] == 132`.
     V1 đòi cập nhật quy trình vào các `SKILL.md` này (Work kind, gating, checkpoint, review/qc) nhưng không chỉ rõ phần nào phải cắt/dời sang `references/` -> chắc chắn gãy `R6` ngay lập tức.
   - **Ngấp nghé trần `3,500` tokens (`R13` — `token_budget.py` & `test_agy_plugin_validate.py:135`):**
     - `skills/tdq-spec/references/spec-template.md`: **3,486 / 3,500** tokens (chỉ còn **14 tokens**).
     - `skills/tdq-build/references/qc.md`: **3,479 / 3,500** tokens (chỉ còn **21 tokens**).
     - `skills/tdq-build/references/team-mode.md`: **3,472 / 3,500** tokens (chỉ còn **28 tokens**).
     Chỉ cần thêm **1 dòng link** trỏ tới `investigate-mode.md` kèm chú thích `<!-- i18n-allow: ... -->` là đủ làm một trong ba tệp trên vượt 3,500 tokens, đánh sập `R13` và lệnh validate plugin AGY!
   - **Xung đột `i18n_check.py` & Luật văn bản (`R5`, `R6`, `R13`) với `investigate-mode.md`:**
     `scripts/i18n_check.py` bắt lỗi mọi dòng tiếng Việt không được `i18n-allow` bên trong `skills/**`. Nếu `investigate-mode.md` hoặc các dòng chèn thêm vào `SKILL.md`/`references/` viết tiếng Việt tự do, `i18n_check.py` sẽ báo lỗi. Ngoài ra tệp reference mới phải giữ câu `<= 40` từ (`R5`), `<= 500` dòng (`R6`) và `<= 3,500` tokens (`R13`).
   - **`tdq_plan_scaffold.py --verify-plan` lỗi oan trên task `investigate`:**
     Tại `scripts/tdq_plan_scaffold.py:659-668, 885-894, 913-925`, `_finalize_tasks` hợp nhất `sinh_ra` vào `task.vung_file`, rồi `_verify_single_task` kiểm tra `for rel in task.vung_file`. Nếu một task `investigate` vừa ghi nhận một tệp tạo mới trong `Sinh ra:` (như `docs/tdq/artifacts/<slug>/<task>.md`) vừa có ngữ cảnh `Edit` trong cùng task mà phân đoạn `;` của `Sinh ra:` không khớp chặt điều kiện `_is_new_file_in_task`, `--verify-plan` sẽ ném lỗi `Chạm file not found on disk`.
   - **Chuỗi 4 cổng xung đột với `no_worktree`:**
     1. `tools/patches/agy_hooks.py:1463-1469` (`subagent_dispatch_gate.py`) ép bắt buộc trường `WORKTREE:` mỗi khi prompt chứa `"TASK:"`.
     2. `scripts/tdq_team.py:2625-2633` (`_build_packet_payload`) tự tiêm/đòi `WORKTREE:` khi xuất packet.
     3. `scripts/tdq_team.py:1788-1797` (`canh_bao_lach_luat`) cảnh báo thiếu mở nhánh (`chua-mo-nhanh`) với task triển khai không có worktree.
     4. `scripts/tdq_bench.py:283` giả định mọi wave đều tốn `t_kiem + t_hop` (`phi_dot`), tính sai chi phí cho wave `no_worktree`.

3. **Đề xuất sửa V2 cho ND-B4:**
   - **Dọn trần trước khi thêm:** Rút gọn các đoạn trùng lặp trong `tdq-conventions/SKILL.md`, `tdq-intake/SKILL.md`, `tdq-build/SKILL.md`, `tdq-spec/SKILL.md` (giữ nguyên `SKILL_LINE_LIMITS["tdq-plan"] == 132`), đẩy ví dụ/chi tiết dài sang `references/phases.md` hoặc file mới `investigate-mode.md` (viết bằng tiếng Anh chuẩn `<= 3,000` tokens, câu `<= 40` từ, không dính lỗi `i18n_check.py`). Với `spec-template.md`, `qc.md`, `team-mode.md`, **bắt buộc tỉa bớt tối thiểu 40–60 tokens** câu chữ thừa (ngoài vùng bị `test_muc_qc_qc_md.py` / `test_soul_rules.py` khóa) trước khi chèn link pointer 1 dòng.
   - **Sửa `tdq_plan_scaffold.py`:** Theo dõi tường minh tập đường dẫn xuất phát từ `Sinh ra:` (gắn cờ `is_created` riêng cho từng đường dẫn thay vì suy luận chung cho cả task qua keyword `Edit`/`Write`), để `--verify-plan` luôn bỏ qua kiểm tra "phải có sẵn trên đĩa" đối với đầu ra `Sinh ra:` của task `investigate`.
   - **Hỗ trợ cờ `worktree_required: false` xuyên suốt 4 điểm:** Cập nhật `subagent_dispatch_gate.py` (`tools/patches/agy_hooks.py:1463-1469`), `_build_packet_payload` (`tdq_team.py:2625-2633`), `canh_bao_lach_luat` (`tdq_team.py:1788-1797`), và `tdq_bench.py:283` để bỏ qua đòi hỏi `WORKTREE:`, bỏ cảnh báo `chua-mo-nhanh`, và đặt `t_hop = 0` khi task/wave mang cờ `no_worktree`.

---

### ND-B5 [Cao] — Đánh sập Hot-Path Rust ở `pre_tool_use.rs:444` (`handle_read_tool`) & Xung đột Schema/Session của Checkpoint

1. **Vị trí xác minh trên đĩa:**
   - `hooks/rust/tdq-dispatch/src/events/pre_tool_use.rs:444-463` (`handle_read_tool`)
   - `hooks/rust/tdq-dispatch/src/events/post_tool_use.rs:76-85`
   - `hooks/scripts/read_gate.py:228, 242, 246` & `plugins/tdq-workflow-agy/hooks/scripts/read_gate.py:200-282`
   - `tests/test_read_gate.py:175`

2. **Cơ chế xung đột & Hệ quả hiệu năng:**
   - **Thắt cổ chai nghiêm trọng khi tắt early-return `has_range`:**
     Tại `pre_tool_use.rs:444-450`, `handle_read_tool` kiểm tra `StartLine`, `EndLine`, `offset`, `limit`, `ByteOffset` và trả `RouteOutcome::Decided(HookDecision::allow())` tức thì (`< 0.5 ms`).
     Trong môi trường Google Antigravity, công cụ `read_file` / `view_file` **luôn truyền `StartLine`/`EndLine`**. Nếu V1 sửa `handle_read_tool` thành không early-return mà trả về `DelegatePython` trong `work_kind=investigate` + `implement`, **100% lượt đọc trong AGY** sẽ phải khởi tạo Python subprocess (~80–150 ms/lượt), biến 20 lượt đọc nghiên cứu thành ~2–3 giây trễ thuần túy trên hot-path, tạo điểm nghẽn tranh chấp khóa `docs/tdq/.tdq-read.jsonl.lock` giữa 4–5 worker song song và đi ngược lại giả định hiệu năng được bảo vệ bởi `tests/test_read_gate.py:175`.
   - **False-positive của `_dem_lap_doan` & Loạn reset `evidence-log.md` dùng chung:**
     - `read_gate.py:242` (`_dem_lap_doan`) dễ đếm nhầm thành cảnh báo lặp `[TDQ:DOC]` khi subagent đọc nối dài vùng ngữ cảnh gối đầu (ví dụ `1-100` → `20-120` → `10-110`).
     - `read_gate.py:228` lọc `.tdq-read.jsonl` theo `session_id`; nếu V1 reset ngưỡng checkpoint dựa theo `mtime` của một tệp `evidence-log.md` dùng chung toàn cục, Worker B vừa ghi log sẽ vô tình reset bộ đếm của Worker A đang đọc tràn lan không chịu checkpoint (hoặc ngược lại).
     - Ngoài ra `post_tool_use.rs:76-85` đang ghi cấu trúc `{ts, khoa, path}` hoàn toàn lệch với schema `{ts, session, path, dau, cuoi, byte, mtime, da_nhac}` của `read_gate.py:246`.

3. **Đề xuất sửa V2 cho ND-B5:**
   - **Giữ nguyên 100% fast-path Rust cho ranged reads (`< 0.5 ms`, 0 Python subprocess)** tại `pre_tool_use.rs:444`.
   - **Đếm Checkpoint thuần Rust theo từng `sid`:** Trong Rust (`pre_tool_use.rs` / `post_tool_use.rs`), cập nhật bộ đếm siêu nhẹ theo riêng từng session tại `docs/tdq/.tdq-runtime/checkpoint-<sid>.json` (hoặc đếm các event đọc/tìm kiếm trong `turns-<sid>.jsonl` kể từ lần append `evidence.jsonl` mang đúng `sid` đó hoặc `mtime` artifact `<task>.md` riêng của `sid`). Khi vượt ngưỡng `N` lượt đọc/tìm kiếm chưa ghi nhận bằng chứng, Rust gọi thẳng `queue_pending_reminder` để phát nhắc nhở ở `PostInvocation` mà không tốn một lần gọi Python nào.
   - Xóa bỏ hoặc hợp nhất schema chết `{ts, khoa, path}` tại `post_tool_use.rs:76-85` cho khớp mô hình mới.

---

### ND-B6 [TB] — Tràn ngưỡng `600` ký tự `SessionStart` (`next_headline`), `handoff-schema.json` & Đồng bộ Compiler / `PHASE_TABLE`

1. **Vị trí xác minh trên đĩa:**
   - `hooks/scripts/session_start.py` & `plugins/tdq-workflow-agy/hooks/scripts/session_start.py:335-452` (`MAX_LINES=12`, `MAX_CHARS=600`, `TOAN_MAX_CHARS=8200`)
   - `scripts/tdq_state.py:1804-1844, 1944-1973` (`render_state_md`, `next_headline`, `duong_hien_thi`)
   - `scripts/tdq_team.py:2286-2350` & `hooks/scripts/subagent_stop.py:189` (`validate_handoff_payload`, `handoff-schema.json`)
   - `tests/test_phase_table.py:165-171`
   - `tools/patches/agy_hooks.py:1725-1751, 1873-1884` & `tools/patches/skills_and_agents.py`

2. **Cơ chế xung đột:**
   - **Tràn `MAX_CHARS = 600` cắt cụt `Done when:`:** Trong `render_state_md` (`scripts/tdq_state.py:1944-1973`), bảng hiện có 27 dòng không rỗng (`<= 30`), thêm hàng `Work kind` lên 28 (29 dòng cả khoảng trắng) vẫn an toàn cho giới hạn 30 dòng. Nhưng `next_headline` (`L1804-1844`) đã rất sát trần `MAX_CHARS = 600` của `session_start.py`; nếu V1 nhét thêm chuỗi dài `Work kind: investigate` vào đầu anchor/headline, `session_start.py` sẽ cắt phần đuôi làm mất thông tin `Done when:`!
   - **`handoff-schema.json` (`additionalProperties: False`) từ chối `no_worktree`:** `subagent_stop.py:189` xác thực payload qua schema đóng yêu cầu `branch`, `merge_ready`, `tick_ready`. Worker `no_worktree` (`tdq-explorer`, `tdq-debugger`, `tdq-reviewer`) không có branch/merge nên nếu nộp thiếu trường hoặc tự thêm `artifact_path`/`evidence_ids` sẽ bị từ chối khi dừng subagent.
   - **Đồng bộ `PHASE_TABLE` & Compiler `tools/patches/`:** `tests/test_phase_table.py:165-171` assert tính đồng nhất tham chiếu (`assertIs(row, khai)`) ở chế độ `build`; đồng thời `tools/patches/agy_hooks.py:1725-1751, 1873-1884` vẫn còn nhánh fallback cũ và `tools/patches/skills_and_agents.py` biên dịch lại toàn bộ plugin từ nguồn.

3. **Đề xuất sửa V2 cho ND-B6:**
   - Trong `next_headline`, chỉ gắn hậu tố siêu gọn `· kind:inv` (`10` ký tự) đặt sau phần tóm tắt cốt lõi hoặc giữ nguyên trường đầy đủ `| Work kind | investigate |` trong bảng `state.md`, kèm 1 con trỏ gọn trong `[TDQ:ANCHOR]` đảm bảo tổng dung lượng không chạm ngưỡng `600` ký tự làm rơi `Done when:`.
   - Mở rộng `handoff-schema.json` hỗ trợ biến thể `worktree_required: false` (cho phép `branch: null` / tùy chọn `merge_ready`, `tick_ready`, và khai báo hợp lệ `artifact_path`, `evidence_count` dưới `additionalProperties: False`).
   - Giữ nguyên tham chiếu object gốc của `PHASE_TABLE` trong `tdq_state.py` cho `work_kind == "build"`, chỉ chuyển sang bảng `INVESTIGATE_PHASE_ROWS` khi `work_kind == "investigate"`. Mọi thay đổi hook/agent/guidance trong V2 phải sửa đồng bộ ở `tools/patches/` (`skills_and_agents.py`, `agy_hooks.py`, `gate_guidance.json`) và build lại plugin để qua sạch `test_agy_plugin_validate.py`.

---

## Ma trận Chuẩn bị Vá V2 (Tóm tắt Hành động Khuyến nghị)

1. **Bảo mật `scoped-write` & Shell (`ND-B1`, `ND-B2`):** Khớp vai trò chính xác + chặn trước `security-reviewer` → leo tổ tiên canonicalize đa cấp trước prefix check + cấm reparse/8.3 → khóa cứng denylist đối với `evidence.jsonl`/`evidence-log.md`/`trial_*.json`/`rec_*.json` → chuyển `evidence add` sang `--claim-file`/`--excerpt-file` + vá `cmd /c` & `[IO.File]` song song ở Python/Rust + thêm NTFS lock cho `blackboard_record`.
2. **Đường nóng Rust Checkpoint (`ND-B5`):** Tuyệt đối giữ nguyên fast-path `pre_tool_use.rs:444` cho ranged reads; đếm checkpoint thuần Rust theo từng `sid` qua tệp trạng thái riêng `checkpoint-<sid>.json` hoặc `turns-<sid>.jsonl`, không spawn Python subprocess khi `read_file`.
3. **Ổn định Test, Linter & Compiler (`ND-B3`, `ND-B4`, `ND-B6`):** Ưu tiên tái dùng mã `"DOC"` thay vì đẻ thêm `"CHECKPOINT"` (hoặc sửa đủ 6 tệp parity lên 23 mã); tỉa gọn `qc.md`/`spec-template.md`/`team-mode.md` trước khi thêm pointer để không vượt `3,500` tokens (`R13`); viết `investigate-mode.md` bằng tiếng Anh `< 3,000` tokens để thỏa `i18n_check` & giải phóng trần dòng cho `SKILL.md`; vá `rule_r10` (miễn `§2b` cho `investigate`), `tdq_plan_scaffold.py --verify-plan`, `handoff-schema.json`, `subagent_dispatch_gate.py`, `canh_bao_lach_luat` và `tools/patches/` đồng bộ.
