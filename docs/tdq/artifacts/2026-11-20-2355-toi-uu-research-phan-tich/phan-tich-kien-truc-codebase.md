# Phân tích Kiến trúc Codebase & Google Antigravity 2.0 Audit (T1.2)

Request: `2026-11-20-2355-toi-uu-research-phan-tich`
Soul: chất lượng > runtime > context cost · luật gốc: `skills/tdq-conventions/references/soul.md`

> Toàn bộ `path:line` và số liệu trong tài liệu này đã được kiểm chứng trực tiếp trên đĩa tại phiên thực thi T1.2; không chỉnh sửa bất kỳ mã nguồn, hook, skill, agent hay state nào.

---

## 1. State & Phase Routing (`scripts/tdq_state.py`, `skills/tdq-conventions/references/phases.md`, `tests/test_phase_table.py`)

### 1.1. Các neo hàm & hằng số cốt lõi trong `scripts/tdq_state.py` (3,252 dòng)

| Thành phần | Vị trí (`path:line`) | Chức năng & Ràng buộc thực tế |
|---|---|---|
| `VALID_LANES`, `LANE_LABELS`, `LANE_ALIASES` | `scripts/tdq_state.py:42-61` | `VALID_LANES = {"quick", "full", None}`. Alias hợp lệ: `nhanh/express/quick` → `quick`; `chuyen-sau/deep/full` → `full`. |
| `VALID_MODES`, `MODE_LABELS`, `MODE_ALIASES` | `scripts/tdq_state.py:40, 65-81` | `VALID_MODES = ("main", "subagent", "codex")`. Nhãn hiển thị: `inline implement`, `sub-agent implement`, `codex implement`. |
| `VALID_PHASES` | `scripts/tdq_state.py:82` | `{"idle", "analyze", "spec", "plan", "mode", "implement", "qc", "report"}` (8 pha hợp lệ). |
| `CONG_THEO_LANE`, `cong_dang_cho` | `scripts/tdq_state.py:1287-1308` | Tra cổng duyệt còn thiếu theo lane (`quick`: `("quick",)`; `full`: `("spec", "plan")`; `None`: `("spec", "plan", "quick")`). Dùng chung cho `edit_gate.py` và `stop_gate.py`. |
| `effective_phase` | `scripts/tdq_state.py:1311-1318` | Kiểm tra `phase in VALID_PHASES`; không hợp lệ → cảnh báo stderr và fallback về `"idle"`. |
| `PHASE_TABLE` | `scripts/tdq_state.py:1334-1538` | Nguồn sự thật duy nhất gồm **11 keys**: `no_state`, `analyze`, `spec`, `plan`, `mode`, `implement`, `qc`, `report`, `idle`, `quick_analyze`, `quick`. Mỗi key có đủ 6 field: `entry`, `action`, `cmd`, `checklist`, `done_when`, `forbidden`. |
| `IMPLEMENT_SUBAGENT_ROW`, `IMPLEMENT_CODEX_ROW` | `scripts/tdq_state.py:1546-1564`, `1674-1700` | Nằm ngoài `PHASE_TABLE` để không sinh thêm hàng trong `phases.md`. Được trả về qua `phase_row(state)` khi `implement_mode` là `subagent` / `codex`. |
| `MODE_ROWS`, `kiem_bang_mode` | `scripts/tdq_state.py:1707-1726` | `{"main": None, "subagent": IMPLEMENT_SUBAGENT_ROW, "codex": IMPLEMENT_CODEX_ROW}`. `kiem_bang_mode(VALID_MODES, MODE_ROWS)` chạy ngay lúc import module để fail-fast nếu thiếu mode. |
| `phase_key`, `phase_row` | `scripts/tdq_state.py:1650-1668`, `1779-1793` | `phase_key` ánh xạ `quick` chưa `quick_approved` ở `phase=analyze` → `"quick_analyze"`, `quick` ở các pha khác chưa duyệt → `"quick"`, `quick_approved=True` tại `report`/`idle` → giữ `"report"`/`"idle"`. `phase_row` rẽ nhánh `implement` qua `MODE_ROWS`. |
| `render_phases_md` | `scripts/tdq_state.py:1605-1647` | Sinh `skills/tdq-conventions/references/phases.md` từ `PHASE_TABLE` + `PHASE_ORDER` (`L1567-1568`). Với `--plugin-root`, chuyển `python3 scripts/` → `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/"`. |
| `next_headline`, `render_next` | `scripts/tdq_state.py:1837-1844`, `1888-1929` | `next_headline` in dòng `[TDQ:NEXT] <slug> · lane <lane> · phase <phase_key> · Project: ...`. `render_next` gắn `Lean level`, `QC level`, `Next`, `Command`, `Checklist` (bỏ khi `compact=True`), `Done when`, `_tron_bo_vuot`, `_lech_block`. |
| `render_state_md` | `scripts/tdq_state.py:1932-1974` | Sinh `docs/tdq/STATE.md` (mirror read-only `<= 30` dòng) mỗi lần `save()` (`L533-551`). |
| `cli` (`init`, `set`, `_cli_approve`, `_cli_hotfix`) | `scripts/tdq_state.py:3010-3249`, `2311-2432` | `init` (`L3073-3116`) bắt buộc slug `YYYY-MM-DD-HHMM-...`, kiểm `_cong_lsp` (`L2764-2793`), đóng timing request cũ, reset state. `set` (`L3118-3182`) kiểm gate `plan` (`_chan_spec_chua_duyet` L2434), `qc` (`_chan_worktree_con_mo` L2448), `idle` (`_chan_report_thieu` L2668), `implement` (`_chan_eval_plan_chua_co` L2574), `report` (`_chan_eval_evidence_chua_co` L2607), và `plan_file` (`_kiem_r15_plan` L2487). `_cli_approve` (`L2311-2432`) kiểm `_r15_gate_approve`, `_r14_gate`, `_archify_gate`, cập nhật `<target>_sha256` bằng `sha256_noi_dung` (`L592`). |

### 1.2. Những điểm bị ghim bởi `tests/test_phase_table.py` (191 dòng) & `phases.md` (37 dòng)

- `test_all_phases_covered` (`tests/test_phase_table.py:15-24`): ghim cứng `len(PHASE_TABLE) == 11`, bắt buộc đủ `VALID_PHASES` + `no_state` + `quick` + `quick_analyze`.
- `test_every_row_complete` (`L26-34`): ghim `REQUIRED_KEYS == {"entry", "action", "cmd", "checklist", "done_when", "forbidden"}`, không key nào rỗng.
- `test_quick_analyze_khong_nhay_implement_truoc_duyet` (`L72-82`): `PHASE_TABLE["quick_analyze"]["cmd"]` không được chứa `phase=implement`, phải chứa `approve quick`.
- `test_render_no_regex_escape_artifact` (`L83-100`): cấm sinh mục `## analyze` và ghim khối `The commands verbatim`.
- `test_docs_match_constant` (`L124-137`): kiểm tra `skills/tdq-conventions/references/phases.md` chứa mọi tên phase và **đúng từng chuỗi `cmd`** sau khi qua `plugin_root_cmd()`. Do đó, sửa bất kỳ `cmd` nào trong `PHASE_TABLE` bắt buộc phải regenerate `phases.md` (và chạy compiler `build_agy_plugin.py` để đồng bộ `${PLUGIN_ROOT}` trong bản plugin).
- `ModeRowsTest` (`L144-191`): ghim `MODE_ROWS` có hàng riêng biệt cho từng mode trong `VALID_MODES`.

---

## 2. Team, Bench & Lint (`scripts/tdq_team.py`, `scripts/tdq_bench.py`, `scripts/doc_lint.py`)

### 2.1. `scripts/tdq_team.py` (2,873 dòng)

| Thành phần | Vị trí (`path:line`) | Chi tiết cơ chế |
|---|---|---|
| `LY_DO_GIU`, `TIEN_TO_FILE_LUAT`, `TRAN_SONG_SONG` | `scripts/tdq_team.py:78-98` | Tập đóng 5 lý do giữ: `phu-thuoc`, `vung-khoa`, `mcp`, `file-luat`, `hop-dong`. `TRAN_SONG_SONG = 4` nhánh song song tối đa. |
| `_classify_section`, `_record_section_items`, `_finalize_tasks` | `scripts/tdq_team.py:172-187`, `221-237`, `302-312` | `_classify_section` tách `cham`, `tham_chieu`, `sinh_ra`, `neo`, `contract_delta`, `progress`. **Lưu ý:** `- Sinh ra:` đổ vào `task.sinh_ra`, không tự đổ vào `task.vung_file`. Khi `not t._has_cham`, `_finalize_tasks` chỉ lấy path backtick từ `t.text[0]` (dòng tiêu đề task). |
| `quyet_dinh_task` | `scripts/tdq_team.py:546-564` | Thứ tự kiểm: `task.can_mcp` → `("tu_lam", "mcp")`; `not task.vung_file` → `("tu_lam", "vung-khoa")`; `_la_file_luat(d)` (`skills/`, `hooks/`, `agents/`, `rules/`, `.claude/`, `.codex/`, `.agents/`, `CLAUDE.md`, `AGENTS.md`) → `("tu_lam", "file-luat")`; nếu có `Cần:` thì trả `"giao"`; ngược lại nếu tham chiếu task chưa xong → `("tu_lam", "phu-thuoc")`. |
| `lenh_phan_cong` (`assign`) | `scripts/tdq_team.py:775-815` | Đọc `doc_plan(plan)` (`L314`), tính `quyet_dinh_task`, chia đợt `chia_dot` (`L566`), tính projection SHA v1 (`tinh_sha_projection` L445), ghi atomic vào `docs/tdq/team/<slug>.json`. |
| `lenh_kiem_ke` (`audit`) | `scripts/tdq_team.py:833-871` | Kiểm map: task `giao` không được rỗng `vung_file`; task `tu_lam` phải mang 1 trong 5 khóa `LY_DO_GIU`. |
| `lenh_cum` (`wave`) | `scripts/tdq_team.py:899-956` | Sắp xếp theo critical path `b_level` (`L514-539`) giảm dần, tránh đụng vùng khóa đang bay `[>]` và TCAS AST collision (`detect_tcas_collision` L626), giới hạn `TRAN_SONG_SONG = 4`. |
| `lenh_mo` (`open`) | `scripts/tdq_team.py:1257-1293` | Tạo branch từ integration branch + `git worktree add`, ghi sổ `tdq_worktree_registry` (`so_wt.mo_dong`), tạo NTFS junctions (`_tao_ntfs_junction_sharing` L1226). |
| `lenh_kiem` (`check`) | `scripts/tdq_team.py:1406-1431` | Chạy `_do_xung_dot` (`git merge-tree`, không chạm index/working tree, L1303) và `_kiem_test_cua_task` (`chay_test_task`, L1364-1403) trong worktree của task. |
| `lenh_hop` (`merge`) | `scripts/tdq_team.py:1456-1524` | Kiểm working tree sạch (tracked), rebase lên integration tip (`_rebase_len_tich_hop` L1434), check conflict, chạy lại `Test:` của task, `git merge --no-ff`, dọn worktree (`_thu_don` L1197). |
| Blackboard & Dispatch Packet | `scripts/tdq_team.py:2459-2553`, `2611-2784` | `blackboard_path` (`.tdq-runtime/blackboard/<slug>.json`), `blackboard_read` (`L2463`), `blackboard_record` (`L2480`), `suggest_escalation` (`L2527` escalate sang `tdq-build-resolver` khi failures >= `auto_escalate_retries`), `lenh_packet` (`L2704`), `lenh_validate_handoff` (`L2721`), `lenh_blackboard` (`L2747`). |
| `LENH` | `scripts/tdq_team.py:2788-2801` | 12 subcommands chính thức: `assign`, `audit`, `wave`, `open`, `check`, `merge`, `sweep`, `clean`, `resolve`, `packet`, `validate-handoff`, `blackboard` (alias tiếng Việt cũ ánh xạ qua `scripts/tdq_ten_lenh.py:26-40`). |

### 2.2. `scripts/tdq_bench.py` (823 dòng)

- `mo_phong_tasks` (`scripts/tdq_bench.py:257-303`): gọi trực tiếp `tdq_team.quyet_dinh_task(t, tasks)` (`L267`) và `tdq_team.chia_dot(tasks, quyet)` (`L268` — lưu ý không truyền `project_root`).
- **Hành vi với task thiếu `Chạm:` hoặc task artifact (`- Sinh ra:`):**
  - Do `tdq_team._finalize_tasks` không đưa `Sinh ra:` vào `vung_file`, mọi task chỉ ghi `- Sinh ra: docs/...` (hoặc không có `- Chạm:` và không đặt path backtick ở dòng tiêu đề task) đều có `task.vung_file == []`.
  - `quyet_dinh_task` trả về `("tu_lam", "vung-khoa")` (`tdq_team.py:550-551`).
  - Trong `mo_phong_tasks` (`tdq_bench.py:270, 285`), các task này rơi vào `tu_lam` (bị loại khỏi `dot` song song và cộng vào thời gian tuần tự của leader `chen = max(0.0, len(tu_lam) * hs["t_task"] - tong_max)`), làm mô phỏng đánh giá sai khả năng chạy song song của các task research/artifact.
- `LENH` (`L743-748`): `gen-plan`, `calibrate`, `simulate`, `scan`.

### 2.3. `scripts/doc_lint.py` (1,277 dòng)

| Rule / Hàm | Vị trí (`path:line`) | Quy tắc kiểm tra |
|---|---|---|
| `SKILL_LINE_LIMITS` | `scripts/doc_lint.py:36-125` | Bảng trần số dòng cho 11 file `SKILL.md` (chốt bởi `rule_r6` L304-314; mọi file `<= 500` dòng). |
| `rule_r8`, `pair` | `scripts/doc_lint.py:330-384`, `963-1000` | `R8`: `spec/` phải có `## 3b. Năng lực & công cụ` với verdict chỉ gồm `DÙNG`, `KHÔNG`, `NỀN`; `KHÔNG` phải bắt đầu bằng 1 trong 4 `CLOSED_REASONS`. `pair`: plan phải có `## Cụm song song`, mọi skill `DÙNG` phải có đủ 5 field `Dùng/Để/Ra/Kiểm/Không dùng cho` (`L337`), và gọi `r15_loi(plan_doc, check_dir=False)` (`L997`). |
| `rule_r11` | `scripts/doc_lint.py:466-496` | `R11_MOC = "2026-08-19"`. Cấm đưa path file test (`tests/.../test_*.py`) hoặc flag `-k` vào `spec/` (chỉ giữ điều kiện PASS). |
| `kiem_tran_token` (`R13`) | `scripts/doc_lint.py:500-524` | Khi lint bất kỳ file nào trong `skills/`, gọi `token_budget.kiem_khoa(goc)` kiểm sha256 + ngưỡng `3,500` tokens trong `docs/tdq/token-budget.json`. |
| `r14_loi`, `rule_r14` (`R14`) | `scripts/doc_lint.py:1087-1212` | `R14_MOC = "2026-10-03-0732"`. Mọi hàng `Qn` trong `spec §6` có ngưỡng số học (trừ `0`/`1`) phải có cột `Đo trước` (chứa chữ số) và `Dự phòng nếu trượt` khác rỗng. |
| `rule_r15` / `r15_loi` (`R15`) | `scripts/doc_lint.py:528-928` | `R15_MOC = "2026-11-20"`. Trước mốc chạy `_legacy_r15` (`L652`). Từ mốc trở đi: kiểm `BANNED_PLACEHOLDERS` (`L535`), `ANTI2_PATTERNS` (`L553`: cấm `assert True`, `assert 1==1`, `len >= 0`, `os.path.exists` / `Test-Path` trần), `_is_quick_plan` (`L771-777`: bắt `# QUICK` hoặc `Lane: quick` trong 15 dòng đầu), `_check_task_v2` (`L818-834`: `R15-Full` 8 field + `<= 35` dòng cho code task; `R15-Compact` 5 field cho quick/QC/sweep/sync; trần sweep `<= 6` file, sync-sig `<= 5` file), `_has_ownership_map` (`L856`: bắt buộc nếu `>= 2` contract tasks), và `_check_model_effort_section` (`L879-903`: từ `2026-11-20-1230` trở đi cho non-quick plan, bắt buộc `## Phân bổ Model & Effort` nhắc đủ `implement`, `qc`, `report`). |

---

## 3. Python Hooks (`hooks/scripts/` vs `plugins/tdq-workflow-agy/hooks/scripts/`)

> Repo tồn tại **hai lớp Python hooks**: bản gốc/dev tại `hooks/scripts/` và bản đã qua compiler `tools/patches/agy_hooks.py` tại `plugins/tdq-workflow-agy/hooks/scripts/`. Bảng dưới ghi rõ neo dòng của cả hai nơi khi có khác biệt.

| File | Vị trí & Chi tiết thực tế (`path:line`) |
|---|---|
| `_common.py` | **Root** (`940` dòng): `AGY_CODES` (`L94-99`, 24 mã), `CODES` (`L100-101`, 10 mã `TDQ:*`), `stop_block` (`L802-815`), `is_qc_report_target` (`L818-831`: dùng `os.path.realpath` + `commonpath` cho phép ghi `.md` trong `docs/tdq/qc/`), `register_subagent_role` (`L858-882`), `detect_subagent` (`L885-926`: đọc `sessions.json` → `agent_type/agentType` → dòng đầu `transcriptPath` quét 8 tên role `tdq-*` và ghi vào `sessions.json`).<br>**Plugin** (`1,335` dòng): `AGY_CODES` = `CODES` (`L36-60`, **22 mã**; đổi `GATE`→gộp `STATE`, bỏ `EDIT/TEST/DIRTY/PAUSE/LECH/SCOPE/FEEDBACK/LSP-WAIT/COMPACT/NO-PLAN-MODE`, thêm `TEAM/DOC/DOD/INTAKE/WORKTREE/NEXT`), `_normalize_tool_aliases` (`L330-345` map `TargetFile/Path/AbsolutePath`→`file_path`, `CommandLine/cmd`→`command`), `_normalize_read_ranges` (`L348-361`), `is_qc_report_target` (`L1222-1235`), `detect_subagent` (`L1289-1335`). |
| `edit_gate.py` | **Root** (`319` dòng) vs **Plugin** (`333` dòng):<br>- `_enforce_agy_readonly_subagent` (root `L78-101`; plugin `L85-108`): chặn `reviewer`, `qc-tester`, `browser`, `explorer`, `debugger` với mã `READONLY`, ngoại trừ `qc-tester` khi `is_qc_report_target(target, cwd)` đúng.<br>- `within(abs_target, docs)` (root `L146-147`; plugin `L154-155`): trả về sớm cho toàn bộ `docs/**` trước các gate `TDQ:TEAM`, `TDQ:APPROVE`, `TDQ:LOG`, `TDQ:TICK`.<br>- `TDQ:TEAM`: chặn subagent sửa trước `implement`/`qc` (root `L153-160`; plugin `L161-169` kiểm thêm `is_agy() and detect_subagent`), chặn leader vi phạm `canh_bao_lach_luat` (`L207-240` / `L216-249`) và `ngoai_vung_khai` (`L245-253` / `L254-262`).<br>- `TDQ:TICK`: chặn `0 [~]` hoặc `> 1 [~]` (miễn `tests/**` và `.tdq-worktrees/**`). Streak trần: **root** dùng `STREAK_NGUONG = 3` (`L30, L298`), còn **plugin** dùng `streak_limit = 8 if is_agy() else STREAK_NGUONG` + `remind("TICK")` tại `streak >= 4` (`L307-318`). **Plugin** cũng tắt `TDQ:RULE:*` trên AGY (`if not is_agy()` tại `L322`). |
| `bash_gate.py` | **Root** (`371` dòng) vs **Plugin** (`430` dòng):<br>- `DOCS_ARTIFACT = re.compile(r"docs[\\/]tdq[\\/]artifacts[\\/]", re.IGNORECASE)` (`L92`).<br>- `_is_shell_write` (`L235-245` / `L242-252`): kiểm PowerShell write cmdlets, `tee/rm/mv/sed -i`, `SHELL_MUTATOR`, `_part_stdout_targets`, đệ quy subcommand tới depth 2.<br>- `_enforce_agy_bash_guards` (`L248-265` / `L291-311`): chặn 5 role read-only (`reviewer`, `qc-tester`, `browser`, `explorer`, `debugger`) nếu `_is_shell_write(cmd)` (`READONLY`), chặn sửa `docs/tdq/state.json|STATE.md` (`STATE`), và trong **plugin** còn có `_has_banned_agy_git` (`L257-288`) chặn nhánh AI, trailer `Co-Authored-By`, `git push`, `git reset --hard`, `git clean -f`, `curl|bash`, `-ExecutionPolicy Bypass`.<br>- `eval_bash` (root `L330-363`; plugin `L376-422`): chặn subagent pre-implement ghi ngoài `docs/tdq/artifacts/` (`TDQ:TEAM`). **Plugin** bổ sung chặn cả main-agent ghi shell ngoài `docs/` khi còn gate chờ duyệt (`TDQ:APPROVE`, `L399-411`); root chưa có guard này. |
| `read_gate.py` | **Root** (`275` dòng) vs **Plugin** (`282` dòng):<br>- `SO_SACH = "docs/tdq/.tdq-read.jsonl"` (root `L42`; plugin `L49`), `HAN_GIAY = 21600`, `TRAN_DONG = 400`, `NGUONG_BYTE = 2048`, `CCR_MIN_BYTES = 32768`.<br>- Schema mỗi dòng trong `.tdq-read.jsonl` (`L246-247` / `L253-254`): `{"ts", "session", "path", "dau", "cuoi", "byte", "mtime", "da_nhac"}`.<br>- Hiện kiểm 3 case (`L232-251` / `L239-258`): đọc lại nguyên file không đổi (`_da_doc_tron`), đọc dải chồng lặp >= 70% từ lần 3 (`_dem_lap_doan >= 2`), và gợi ý CCR cho file dữ liệu > 32 KB (`_should_hint_ccr`). **Root** phát code `"READ"` (`L261`), **plugin** phát `"DOC"` (`L268`).<br>- **Vị trí gắn checkpoint reminder (nếu mở rộng):** ngay tại `main()` (`L226-269` trong plugin `read_gate.py`) sau khi đọc `rows = _doc_so(cwd, phien)` — lưu ý hiện tại `rows` chỉ lọc theo `session == phien` và `HAN_GIAY`, chưa đếm tích lũy bytes/tokens để nhắc checkpoint, và cần chú ý Rust `handle_read_tool` đang bypass toàn bộ đọc có range. |
| `session_start.py` | **Root** (`443` dòng) vs **Plugin** (`452` dòng):<br>- Inject `RULE` + `render_next(..., compact=True)` (head cap `12` dòng / `600` chars), notices, `TDQ:GON` lazy-load (chỉ tải toàn văn `chung.md` khi `pha == "implement"`, các pha khác chỉ 1 dòng pointer, `L338-346` / `L347-355`).<br>- **Compact/Resume recovery `[TDQ:ANCHOR]`** (root `L349-410`; plugin `L358-410`): kích hoạt khi `has_active` và `source in ("compact", "resume")`. Các field exact của `[TDQ:ANCHOR]`: `request={req}`, `phase={pha}`, `source={src}`, `owner={owner}`, `plan={plan_f}`, `doing={doing_str}`, `dispatched={dispatched_str}`, tùy chọn `resume_task={resume_task}; check tool/receipt before retry` (khi `phase=implement`), `next={next_hint}`, `worktree={wt_str}`, kèm dòng `MCP-First` + `LSP-Autonomy` và `Core anti-patterns: ANTI-1..ANTI-6`. Capping hậu xử lý (`L414-432` / `L423-441`) bảo vệ `[TDQ:ANCHOR]` không bị cắt đuôi. **Plugin** gọi thêm `cleanup_stale_runtime(cwd)` (`L218`) và tắt `tdq_devtool_mcp` (`if not is_agy()` tại `L262`). |
| `stop_gate.py` | **Root** (`391` dòng) vs **Plugin** (`441` dòng):<br>- Kiểm `_maybe_subagent_stop`, `TERMINAL_STOP_REASONS`, `TDQ:LOG` (so turn ledger + git fingerprint `turn_start`), `TDQ:TICK` (code sửa mà `plan_sha` không đổi), `_chan_chua_xong` (`TDQ:UNFINISHED` với `MAX_STREAK = 3` ở root, hạ xuống `2` ở plugin khi `is_agy()`, `stop_gate.py` plugin qua `_patch_stop_gate`).<br>- **Plugin** bổ sung `_is_agy_log_exempt` miễn kiểm `TDQ:LOG` cho `docs/.staging`, `docs/tdq/`, `graphify-out/`, `*.tmp`, bỏ `[TDQ:STUCK]` đổi thành `queue_remind(..., "UNFINISHED")`, nhận `continuationActive`, và gọi `mark_turn_closed(cwd, sid)` (`agy_hooks.py:2441-2660`). |
| `prompt_context.py` | **Root** (`461` dòng) vs **Plugin** (`584` dòng):<br>- Phân tích prompt theo regex `AGREE`, `OBJECT`, `APPROVE_FAST`, `QUESTION`, `MODE`, `LETTER`, ghi row `signal` (`approve_pending`), cảnh báo `TDQ:APPROVE` / `TDQ:INTAKE` (`_tdq_direct`), `TDQ:WORKTREE`, `TDQ:GON`, `TDQ:QC`.<br>- **Plugin** nâng cấp `_agy_pre_invocation_hook` (`L341-363`): flush `pending-reminders` (`model_text` + `user_markdown`), phân biệt mid-turn vs new-user-turn bằng `_detect_new_user_turn` (`transcriptPath` tail 64 KB + `turn-meta-<sid>.json`), chỉ clear turn ledger khi `is_new_turn`, bỏ `TDQ:FEEDBACK` và `"same as last turn"`, thêm `_agy_phase_anchor` (`L366-385`) inject `[TDQ:GON]` hoặc `[TDQ:QC]` 1 lần mỗi pha hoặc khi `source == "compact"`. |
| `search_gate.py` | **Root** (`207` dòng) vs **Plugin** (`289` dòng):<br>- `quyet` (`L132-164`) gọi `search_rules.phan_loai` + `search_rules.quyet_dinh`, stand-down qua `ly_do_dung_xuong` (`L105-129`, circuit breaker `BREAKER_CHAN = 3` khi thiếu readiness stamp). **Plugin** (`_patch_search_gate` tại `agy_hooks.py:2079-2186`) vá thêm `_is_rtk_bypass`, `_search_grace_state` (`turns-<sid>.jsonl`), `_has_search_leak` cho chuỗi lệnh shell lỗi cú pháp. |

---

## 4. Rust Hook Binary (`hooks/rust/tdq-dispatch/src/`) & So sánh Parity Python ↔ Rust

### 4.1. Kiến trúc Hybrid Hot-Path / Cold-Path (`main.rs` 361 dòng)

- `route_event` (`hooks/rust/tdq-dispatch/src/main.rs:187-202`):
  - `SessionStart`, `SubagentStop` → luôn `RouteOutcome::DelegatePython` (`dispatch.py`).
  - `PreInvocation`, `PreToolUse`, `PostToolUse`, `Stop` → chạy hot-path Rust trước, trả JSON trực tiếp nếu `Decided`, hoặc spawn `python -X utf8 dispatch.py --event <ev>` nếu `DelegatePython` (hoặc `TDQ_HOOK_ENGINE=python`).

### 4.2. Các module cốt lõi đã kiểm chứng

- **`storage.rs` (757 dòng):**
  - `TdqState` (`L19-34`): 14 fields (`active_request`, `lane`, `phase`, `spec_approved`, `plan_approved`, `quick_approved`, `muc_gat`, `muc_qc`, `loai_request`, `plan_file`, `implement_mode`, `implement_pause`, `doc_lang`, `updated_at`).
  - `effective_phase` (`L44-49`): chỉ match `"idle" | "analyze" | "spec" | "plan" | "implement" | "qc" | "report"`.
  - `cong_dang_cho` (`L52-83`): parity với `tdq_state.py`.
  - `TurnMeta` (`L137-146`): `last_user_sig`, `turn_closed`, `prompt_sha`, `phase_anchor`.
  - `read_plan_tick_state` (`L337-380`), `check_and_store_ccr` (`L551-576`: `32 KB` / `200` dòng), `record_stop_streak` (`L588-612`).
- **`events/pre_tool_use.rs` (714 dòng):**
  - `SUBAGENT_ROLES` (`L22-31`): 8 role `tdq-*`. `detect_subagent_role` (`L33-63`) kiểm `sessions.json` → `agent_type` → dòng đầu `transcript_path` → `agent_id` fallback `"subagent"`.
  - `is_readonly_role` (`L65-72`): `reviewer`, `qc-tester`, `browser`, `explorer`, `debugger`.
  - `normalize_lexical` (`L145-160`), `resolve_rel_in_project` (`L124-143`), `is_qc_report_target` (`L162-178`: ghép `normalize_lexical` + `resolve_rel_in_project`, kiểm `docs/tdq/qc/*.md`).
  - `handle_edit_tool` (`L281-355`): kiểm readonly (`qc-tester` allow nếu `is_qc_report_target`), kiểm `is_state_target` (`STATE`), fallback Python nếu ngoài project hoặc `role_opt.is_some()` hoặc `implement_mode == "subagent"`, kiểm `cong_dang_cho` (`APPROVE`), kiểm `check_tick_gates` (`L185-236`: deny tại `streak >= 8`, queue remind `TICK` tại `4..7`).
  - `handle_command_tool` (`L357-442`): kiểm readonly shell mutator, `mutates_tdq_state`, `inspect_command_safety`, `has_banned_ai_branch`, subagent pre-implement `mutates_outside_docs` → `DelegatePython`, main-agent `mutates_outside_docs_any` khi pending `cong_dang_cho` → `APPROVE` deny, `needs_python_command_gate` → `DelegatePython`.
  - `handle_read_tool` (`L444-463`): allow ngay nếu có `StartLine/EndLine/offset/limit/ByteOffset` hoặc file `<= 2048` bytes; ngược lại `DelegatePython`.
  - `handle_mcp_tool` (`L492-553`): `blast_radius` → `DelegatePython`; `start_lsp` thiếu `language_id` → O(1) `detect_unique_language_o1` (`L465-490`, thiếu `java`/`csharp` so với `_LSP_O1_HELPER` Python) để overwrite hoặc `DelegatePython`; tool concept → ghi `khai_niem` vào `.tdq-search.jsonl` + reset `search_grace`.
- **`events/pre_invocation.rs` (207 dòng):**
  - `handle_pre_invocation` (`L127-162`): subagent → chạy `handle_post_invocation`; leader mid-turn → kiểm `TurnMeta`, `state_newer_than_meta`, `scan_tail_user_input` (`TAIL_BYTES = 65_536`), và `source == "compact"` (`L157`) để quyết định `DelegatePython` vs mid-turn flush.
- **`command_parser.rs` (501 dòng):**
  - `mutates_outside_docs` (`L280-290`): cho phép ghi trong `docs/tdq/artifacts/` (cho subagent pre-implement).
  - `mutates_outside_docs_any` (`L293-305`): cho phép ghi trong toàn bộ `docs/` (cho main agent `TDQ:APPROVE` guard).

### 4.3. Bảng sai lệch Parity Python ↔ Rust ↔ Plugin hiện hữu (Đã xác minh)

| # | Điểm lệch / Gap | Python (`scripts/` / `hooks/scripts/` / plugin) | Rust (`hooks/rust/tdq-dispatch/src/`) | Tác động thực tế |
|---|---|---|---|---|
| 1 | **Phase `"mode"` bị rơi về `"idle"`** | `tdq_state.py:82` có `"mode"` trong `VALID_PHASES`. | `storage.rs:44-49` (`effective_phase`) **thiếu `"mode"`**, rơi về `"idle"`. | Trong lúc đang ở pha `mode`, `khoa_hien_tai` (`storage.rs:178-189`) ghi scope `phien:<sid>` thay vì `yc:<req>`; `stop_streak.rs:80` cho stop ngay như `idle`. |
| 2 | **`PreInvocation` `compact` vs `resume`** | `session_start.py:352` kích `[TDQ:ANCHOR]` cho cả `compact` lẫn `resume`. | `pre_invocation.rs:157` chỉ check `source == "compact"`, **bỏ qua `"resume"`**. | Nếu host gọi `PreInvocation` với `source="resume"` khi `TurnMeta` chưa đóng, Rust nuốt luôn không delegate sang Python `prompt_context.py`. |
| 3 | **`handle_read_tool` nuốt kiểm tra đọc lặp dải dòng** | `read_gate.py:242-250` đếm `_dem_lap_doan` (trùng >= 70% từ 2 lần trước trở lên) kể cả khi có `offset/limit`. | `pre_tool_use.rs:444-450` trả `Allow` ngay nếu có `StartLine/EndLine/offset/limit/ByteOffset`. | Mọi lệnh `read_file`/`view_file` có range trên AGY không bao giờ tới `read_gate.py`, làm vô hiệu hóa cảnh báo đọc lặp dải dòng (và mọi checkpoint gắn vào `read_gate.py` nếu không bỏ qua bypass). |
| 4 | **`qc-tester` ghi `docs/tdq/qc/*.md` không được `observe("edit")`** | `edit_gate.py:91-95, 124` (`_enforce_agy_readonly_subagent` trả `False`) vẫn chạy `observe("edit")` xuống turn ledger. | `pre_tool_use.rs:290-295` trả `Allow` sớm trước `record_edit_observations`. | Thiếu audit `observe("edit")` trong `turns-<sid>.jsonl` khi `tdq-qc-tester` ghi báo cáo QC (dù AGY không chạy `stop_gate` của subagent qua `edit` ledger). |
| 5 | **Kiểm tra `docs/**` và `check_tick_gates`** | `edit_gate.py:146-147` return ngay sau `observe` nếu file thuộc `docs/**`. | `pre_tool_use.rs:337-354` vẫn gọi `check_tick_gates` (trong đó mới check `if in_docs { return Ok(None); }`) rồi gọi `record_edit_observations` (ghi thêm `observe` thứ hai? Không, chỉ ghi 1 lần ở L246). | Hành vi tương đương nhưng luồng khác; riêng `detect_subagent_role` fallback `agent_id -> "subagent"` (`pre_tool_use.rs:58-62`) rộng hơn Python (`_common.py:885-926` bỏ qua bare `agent_id`), làm Rust delegate Python khi có bare `agent_id`. |
| 6 | **O(1) language detection cho `start_lsp`** | Plugin `lsp_gate.py` (`agy_hooks.py:1481-1539`) nhận cả `java` (`pom.xml`, `build.gradle*`) và `csharp` (`*.csproj`, `*.sln`), plus `.tdq-lsp-module.json`. | `pre_tool_use.rs:465-490` chỉ nhận `rust`, `python`, `typescript`, `go` (thiếu `java`, `csharp` và chưa đọc `.tdq-lsp-module.json`). | Repo Java/C# hoặc đa ngôn ngữ có `.tdq-lsp-module.json` bị rơi về cold-path Python `lsp_gate.py`. |
| 7 | **`PostToolUse` `read_file` dead-code & schema mismatch** | `read_gate.py:246-247` ghi `{"ts", "session", "path", "dau", "cuoi", "byte", "mtime", "da_nhac"}`. | `post_tool_use.rs:76-85` ghi `{"ts", "khoa", "path"}` khi `tool_name` là `read_file`; nhưng `hooks.json:92` **không match** `read_file`. | Dead path trong Rust; nếu matcher mở ra, `.tdq-read.jsonl` sẽ trộn 2 schema khác nhau (`session` vs `khoa`). |
| 8 | **Root `hooks/scripts/` vs `plugins/tdq-workflow-agy/hooks/scripts/`** | Root `edit_gate.py:30` giữ `STREAK_NGUONG = 3`, root `read_gate.py:261` dùng code `"READ"`, root `bash_gate.py` không chặn shell write của main-agent khi pending `APPROVE`. | Bản plugin (qua `agy_hooks.py`) nâng streak lên `8` (cảnh báo `4..7`), đổi `"READ"` → `"DOC"`, chặn main-agent shell mutator khi pending `APPROVE`, thêm `post_invocation.py` & `subagent_dispatch_gate.py`. | Sửa nhầm chỉ ở root mà không chạy `build_agy_plugin.py` (hoặc ngược lại) sẽ gây lệch hành vi runtime thật của plugin AGY. |

---

## 5. Skills, Agents & Token Budget (`docs/tdq/token-budget.json`, `scripts/token_budget.py`, `skills/`, `agents/`)

### 5.1. Trạng thái khóa Token Budget (`TRAN_TOKEN = 3500`, `scripts/token_budget.py:45`)

- Kết quả `token_budget.kiem_khoa(".")` và `token_budget.kiem_khoa("plugins/tdq-workflow-agy")`: **0 findings** trên cả **65/65 file** `skills/*/references/**/*.md`.
- **Điểm nóng headroom thấp nhất (Root vs Plugin compiled):**
  - `skills/tdq-spec/references/spec-template.md`: Root **`3486 / 3500` (còn 14 tokens)** · Plugin `2679 / 3500` (còn 821).
  - `skills/tdq-build/references/qc.md`: Root **`3479 / 3500` (còn 21 tokens)** · Plugin `3194 / 3500` (còn 306). *(Cực kỳ chật — mọi bổ sung vào `qc.md` ở root vượt 21 tokens sẽ làm `doc_lint` R13 fail trừ khi tách sang sibling như `qc-vong-fix.md`!)*
  - `skills/tdq-build/references/team-mode.md`: Root **`3472 / 3500` (còn 28 tokens)** · Plugin `3114 / 3500`.
  - `skills/tdq-build/references/vision-test-loop.md`: Root **`3461 / 3500` (còn 39 tokens)** · Plugin `3198 / 3500`.
  - `skills/tdq-setup/references/uu-tien-tim-kiem.md`: Root **`3439 / 3500` (còn 61 tokens)** · Plugin `3182 / 3500`.
  - `skills/tdq-plan/references/plan-template.md`: Root **`3420 / 3500` (còn 80 tokens)** · Plugin `2656 / 3500`.
  - `skills/tdq-build/references/rules/chung.md`: Root **`3352 / 3500` (còn 148 tokens)** · Plugin `3160 / 3500`.
  - `skills/tdq-plan/references/plan-template-co-che.md`: Root **`3266 / 3500` (còn 234 tokens)** · Plugin `2406 / 3500`.

<details>
<summary>Bảng đầy đủ 65 reference files trong docs/tdq/token-budget.json (Cap = 3500)</summary>

| File (`skills/...`) | Root Tokens | Headroom | Plugin Tokens |
|---|---:|---:|---:|
| `skills/tdq-spec/references/spec-template.md` | 3486 | 14 | 2679 |
| `skills/tdq-build/references/qc.md` | 3479 | 21 | 3194 |
| `skills/tdq-build/references/team-mode.md` | 3472 | 28 | 3114 |
| `skills/tdq-build/references/vision-test-loop.md` | 3461 | 39 | 3198 |
| `skills/tdq-setup/references/uu-tien-tim-kiem.md` | 3439 | 61 | 3182 |
| `skills/tdq-plan/references/plan-template.md` | 3420 | 80 | 2656 |
| `skills/tdq-build/references/rules/chung.md` | 3352 | 148 | 3160 |
| `skills/tdq-plan/references/plan-template-co-che.md` | 3266 | 234 | 2406 |
| `skills/tdq-plan/references/mode-gate.md` | 3149 | 351 | 2682 |
| `skills/tdq-build/references/report-template.md` | 3123 | 377 | 2738 |
| `skills/tdq-spec/references/spec-template-huong-dan.md` | 3000 | 500 | 2459 |
| `skills/tdq-intake/references/quick-lane.md` | 2923 | 577 | 2683 |
| `skills/tdq-intake/references/analyze-full.md` | 2822 | 678 | 2607 |
| `skills/tdq-build/references/codex-mode.md` | 2582 | 918 | 2371 |
| `skills/tdq-conventions/references/user-facing-block.md` | 2392 | 1108 | 2243 |
| `skills/tdq-conventions/references/soul.md` | 2310 | 1190 | 2082 |
| `skills/tdq-check-status/references/bang-lech.md` | 2136 | 1364 | 1778 |
| `skills/tdq-intake/references/scope-round.md` | 2066 | 1434 | 1901 |
| `skills/tdq-conventions/references/context-budget.md` | 2025 | 1475 | 1952 |
| `skills/tdq-conventions/references/phases.md` | 1872 | 1628 | 1633 |
| `skills/tdq-conventions/references/clean-code.md` | 1852 | 1648 | 1705 |
| `skills/tdq-conventions/references/reminder-codes.md` | 1767 | 1733 | 1718 |
| `skills/tdq-conventions/references/plugin-routing.md` | 1711 | 1789 | 1530 |
| `skills/tdq-conventions/references/subagent-tuning.md` | 1654 | 1846 | 1568 |
| `skills/tdq-intake/references/interview.md` | 1652 | 1848 | 1494 |
| `skills/tdq-intake/references/skill-inventory.md` | 1483 | 2017 | 1320 |
| `skills/tdq-plan/references/planner-rules.md` | 1470 | 2030 | 1375 |
| `skills/tdq-intake/references/quick-lane-qc.md` | 1437 | 2063 | 1308 |
| `skills/tdq-conventions/references/knowledge-template.md` | 1422 | 2078 | 1021 |
| `skills/tdq-setup/references/languages.md` | 1367 | 2133 | 1195 |
| `skills/tdq-conventions/references/approval.md` | 1351 | 2149 | 1237 |
| `skills/tdq-build/references/team-mode-tra-cuu.md` | 1346 | 2154 | 1262 |
| `skills/tdq-intake/references/kiem-lsp-hieu-ung.md` | 1324 | 2176 | 1178 |
| `skills/tdq-build/references/skill-eval.md` | 1322 | 2178 | 1240 |
| `skills/tdq-check-status/references/report-template.md` | 1317 | 2183 | 1151 |
| `skills/tdq-plan/references/plan-examples.md` | 1281 | 2219 | 1160 |
| `skills/tdq-build/references/rules/cookbooks/typescript-js-cookbook.md` | 1262 | 2238 | 1110 |
| `skills/tdq-intake/references/lane-decision.md` | 1253 | 2247 | 1087 |
| `skills/tdq-setup/references/uu-tien-tim-kiem-chi-tiet.md` | 1244 | 2256 | 1182 |
| `skills/tdq-build/references/rules/cookbooks/python-cookbook.md` | 1241 | 2259 | 1133 |
| `skills/tdq-build/references/runtime-speed.md` | 1239 | 2261 | 1188 |
| `skills/tdq-plan/references/plan-template-huong-dan.md` | 1222 | 2278 | 1130 |
| `skills/tdq-spec/references/archify-ba.md` | 1203 | 2297 | 1094 |
| `skills/tdq-conventions/references/user-facing-block-vi-du.md` | 1085 | 2415 | 910 |
| `skills/tdq-build/references/rules/index.md` | 1055 | 2445 | 943 |
| `skills/tdq-build/references/archify-lifecycle.md` | 960 | 2540 | 876 |
| `skills/tdq-build/references/rules/typescript-js.md` | 958 | 2542 | 859 |
| `skills/tdq-intake/references/nhanh-request.md` | 952 | 2548 | 819 |
| `skills/tdq-intake/references/quick-lane-mini.md` | 937 | 2563 | 760 |
| `skills/tdq-build/references/rules/html.md` | 927 | 2573 | 849 |
| `skills/tdq-setup/references/mcp-first-guide.md` | 908 | 2592 | 850 |
| `skills/tdq-build/references/rules/go.md` | 901 | 2599 | 831 |
| `skills/tdq-build/references/rules/cpp.md` | 894 | 2606 | 822 |
| `skills/tdq-build/references/rules/rust.md` | 844 | 2656 | 773 |
| `skills/tdq-build/references/rules/them-ngon-ngu.md` | 838 | 2662 | 800 |
| `skills/tdq-build/references/rules/csharp.md` | 831 | 2669 | 767 |
| `skills/tdq-build/references/rules/python.md` | 823 | 2677 | 785 |
| `skills/tdq-conventions/references/ultracode.md` | 816 | 2684 | 752 |
| `skills/tdq-setup/references/chrome-devtools-mcp-guide.md` | 773 | 2727 | 635 |
| `skills/tdq-intake/references/archify-quick.md` | 569 | 2931 | 510 |
| `skills/tdq-conventions/references/measure-scenario.md` | 541 | 2959 | 491 |
| `skills/tdq-build/references/qc-vong-fix.md` | 536 | 2964 | 475 |
| `skills/tdq-conventions/references/tavily.md` | 507 | 2993 | 469 |
| `skills/tdq-intake/references/issue-triage.md` | 458 | 3042 | 448 |
| `skills/tdq-conventions/references/worklog-images.md` | 300 | 3200 | 287 |

</details>

### 5.2. Số dòng & Headroom của 11 `SKILL.md` (`doc_lint.SKILL_LINE_LIMITS`)

| Skill | Dòng thực tế | Cap (`doc_lint.py:36-125`) | Headroom (dòng) | Ghi chú cấu trúc |
|---|---:|---:|---:|---|
| `tdq-conventions` | **209** | 209 | **0** | Kịch trần; giữ §0-§11 (`L18-209`). |
| `tdq-intake` | **148** | 148 | **0** | Kịch trần; gồm Tier nhỏ + Part A/B/C + Tam Giác Khảo Sát 3 Chiều (`L62`). |
| `tdq-setup` | **132** | 132 | **0** | Kịch trần. |
| `tdq-build` | **172** | 174 | **2** | Chỉ còn 2 dòng; Part A/B/C trỏ sang `team-mode.md`, `qc.md`, `report-template.md`. |
| `tdq-spec` | **97** | 100 | **3** | Còn 3 dòng; bước 1 yêu cầu §2b (LSP), §2c (Archify), §3b (R8), §3c (thuật toán), §3d (fresher), kiểm R8+R14. |
| `tdq-status` | 55 | 60 | 5 | — |
| `tdq-lean` | 74 | 80 | 6 | — |
| `tdq-browser-research` | 52 | 60 | 8 | — |
| `tdq-browser-test` | 77 | 85 | 8 | — |
| `tdq-check-status` | 71 | 80 | 9 | — |
| `tdq-plan` | 121 | 132 | 11 | Còn 11 dòng; bước 1 chạy `tdq_bench.py simulate --he-so-agent 1.5`, bước 2 Two-Pass Draft + `Phân bổ Model & Effort`, bước 3 `doc_lint --pair` + `tdq_plan_scaffold.py`. |

### 5.3. Subagents (`agents/tdq-*.md` vs `plugins/tdq-workflow-agy/agents/tdq-*.md`)

- **Source `agents/tdq-*.md`**: dùng định dạng tools Claude (`Read, Grep, Glob[, Bash]`), `model: inherit`, và `effort: high`.
  - `tdq-explorer.md` (`32` dòng): `tools: Read, Grep, Glob`, 3-tier search, digest `<= 1,500` chars.
  - `tdq-debugger.md` (`29` dòng): `tools: Read, Grep, Glob, Bash`, reproduce + minimal fix plan, digest `<= 1,500` chars.
  - `tdq-reviewer.md` (`37` dòng): `tools: Read, Grep, Glob`, adversarial skeptic `>= 0.80` fail-closed, kiểm parity `§3c`, `Phân bổ Model & Effort`, digest `<= 1,500` chars.
  - `tdq-security-reviewer.md` (`56` dòng): `tools: Read, Grep, Glob`, OWASP Top 10 + dependency audit, digest `<= 1,500` chars.
  - `tdq-qc-tester.md` (`31` dòng): `tools: Bash, Read, Grep, Glob`, cho phép ghi duy nhất `docs/tdq/qc/*.md` (shard/final), digest `<= 1,500` chars.
  - Các agent còn lại: `tdq-implementer.md` (`31` dòng), `tdq-refactor-cleaner.md` (`41` dòng), `tdq-build-resolver.md` (`43` dòng).
- **Compiled `plugins/tdq-workflow-agy/agents/tdq-*.md`** (`tools/patches/skills_and_agents.py:28-106, 142-180`): chuyển thành YAML list AGY `_READONLY_TOOLS` (`[read_file, grep_search, find_by_name, list_dir, call_mcp_tool, run_command, send_message]`) hoặc `_WRITER_TOOLS` (thêm `edit_file`, `write_file`), `model: inherit`, **loại bỏ `effort`**, và chèn blockquote `> **Host Enforcement:** ...`.

---

## 6. Google Antigravity 2.0 & AGY Compiler (`tools/patches/*`, `plugins/tdq-workflow-agy/`)

### 6.1. Đặc tả Google Antigravity 2.0 đã xác minh từ builtin docs

- **6 Lifecycle Hook Events hỗ trợ** (`agy-customizations/docs/hooks.md:65-107`): `SessionStart`, `PreToolUse` (matcher theo tool name), `PostToolUse` (matcher theo tool name), `PreInvocation` (chạy trước mỗi lần gọi model), `PostInvocation` (chạy sau tool calls, hỗ trợ `force_continue`/`terminate`), `Stop` (nhận `continuationActive`, trả `decision: "continue"` để đẩy tiếp). Không có event `SubagentStart` hay `SubagentStop` riêng.
- **I/O Contract (`hooks.md:144-429`):** stdin camelCase protojson (`conversationId`, `workspacePaths`, `transcriptPath`, `artifactDirectoryPath`, `modelName`, `lastUserInput`, `hookEventName`, `cwd`, `toolCall`). `PreToolUse` hỗ trợ `decision` (`allow`/`deny`/`ask`/`force_ask`) và shallow `overwrite` merge vào args. `PreInvocation`/`PostInvocation` hỗ trợ `injectSteps` (`systemMessage` với `metadata.user_markdown`). Plugin native phải đặt `hooks.json` ở **root plugin** (`agy-customizations/docs/plugins.md:61-70`) và nhận env `PLUGIN_ROOT`, `PLUGIN_DATA`.
- **Subagent invocation (`invoke_subagent`):** Model chỉ chấp nhận `inherit | flash_lite | flash | pro` (không có trường `effort` trong frontmatter agent hay `invoke_subagent`).

### 6.2. AGY Compiler (`tools/build_agy_plugin.py`, `tools/patches/*`, `plugins/tdq-workflow-agy/`)

- `tools/patches/agy_manifests.py` (`287` dòng):
  - `generate_hooks_json` (`L103-148`) sinh `plugins/tdq-workflow-agy/hooks.json` (`120` dòng) nối cả 6 events tới `bin\tdq-dispatch.exe --event <EventName>` (Windows) hoặc `./bin/tdq-dispatch --event <EventName>`.
  - `generate_mcp_config` (`L151-171`) cấu hình 3 MCP servers: `lsp` (`agent-lsp`), `chrome-devtools`, `tavily-primary`.
  - `generate_two_tier_rules` (`L174-255`) sinh `rules/AGENTS.md` (Tier-1) + `rules/lang-*.md` (`trigger: glob`) + `rules/domain-*.md` (`trigger: model_decision`).
- `tools/patches/skills_and_agents.py` (`199` dòng):
  - `M01_M20_REPLACEMENTS` (`L12-26`): đổi `${CLAUDE_PLUGIN_ROOT}` → `${PLUGIN_ROOT}`, `CLAUDE.md` → `AGENTS.md`, `EnterPlanMode`/`AskUserQuestion`/`UserPromptSubmit` → AGY tools/events, MCP prefix `mcp__lsp__` → `mcp_tdq-workflow-agy_lsp_`, đổi backticked tool names (`L115-123`), transform 8 agents (`L142-180`), chạy `relock_token_budget` (`L183-199`).
- `tools/patches/agy_hooks.py` (`2,784` dòng):
  - Ghi đè `_common.py` (`COMMON_PY`), tạo `post_invocation.py` (`L1350-1377`), `subagent_dispatch_gate.py` (`L1380-1477`), cùng `dispatch.py` (`259` dòng — nhận event, chuẩn hóa payload, dispatch in-process tới các gate).
  - Các patch chính: `_patch_ask_gate` (`L1684`, giữ `ZERO-POPUP`, tắt `TDQ:ASK`), `_patch_bash_gate` (`L1721`, thêm `_has_banned_agy_git` và chặn shell write ngoài `docs/` khi chưa approve), `_patch_edit_gate` (`L1869`, nâng streak lên 8 + remind ở 4, return ngay sau `STATE` block, tắt `TDQ:RULE`), `_patch_read_gate` (`L1975`, đổi `"READ"` → `"DOC"`), `_patch_lsp_gate` (`L2013`, O(1) language detection), `_patch_search_gate` (`L2079`, rtk bypass + `search_grace`), `_patch_prompt_context` (`L2267`, `turn-meta` + `_agy_phase_anchor` + bỏ `TDQ:FEEDBACK`), `_patch_stop_gate` (`L2441`, `MAX_STREAK=2`, `_is_agy_log_exempt`, `mark_turn_closed`), `_patch_session_start` (`L2662`, `cleanup_stale_runtime` 7 ngày, tắt `tdq_devtool_mcp`).
  - **Cảnh báo bảo trì ở `_patch_edit_gate` (`L1873-1884`) & `_patch_bash_gate` (`L1725-1751`):** `agy_hooks.py` vẫn giữ nhánh fallback legacy (chỉ check `reviewer, qc-tester, browser`), may mắn được bypass nhờ root `edit_gate.py`/`bash_gate.py` đã có sẵn `detect_subagent`/`_PS_WRITE_PATTERN` nên block `if ... not in ...` không kích hoạt — nhưng `patch` fallback đã lệch với code root thực tế.
