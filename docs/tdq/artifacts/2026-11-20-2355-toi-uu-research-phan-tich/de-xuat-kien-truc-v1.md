# Đề xuất Kiến trúc Phiên bản V1 — Tối ưu luồng Research, Phân tích, Debug & Báo cáo (`work_kind=investigate`)

Ngày: 2026-11-21 · Task: `T2.2` · Request: `2026-11-20-2355-toi-uu-research-phan-tich`
Soul: chất lượng > runtime > context cost · luật gốc: `skills/tdq-conventions/references/soul.md`
Kho bằng chứng tham chiếu: `docs/tdq/artifacts/2026-11-20-2355-toi-uu-research-phan-tich/evidence-log.md` (`EV-001`–`EV-018`)

---

## 0. Tóm tắt Chẩn đoán Thực nghiệm Trước thiết kế (`EV-001`–`EV-005`)

1. **Tỷ trọng công việc thực tế bị đảo ngược:** Trong kho `174` request (`171` slug duy nhất), nhóm thuần điều tra (`investigate`: `33` research/analysis/audit + `9` debug/scan = `42/174 = 24.1%`) đang bị ép chạy trên pipeline xây code (`build`). Ở `investigate — full` (`N=25`), `Pre-Implement` chiếm median **`1,888s` (`49.9%`**, mean `51.4%`, P90 `97.4%`) so với `implement` **`780s` (`12.7%`)**, và **`20/25` (`80.0%`)** tốn tiền-implement nhiều hơn `implement`. Trên thời gian compute thực (`model_giay`, không tính chờ duyệt), `Pure investigate` vẫn dành `43.0%` pooled (`46.9%` med) cho tiền-impl > `38.1%` impl (`EV-003`).
2. **Bốn lãng phí cấu trúc trực tiếp:** (i) Đóng gói lặp `424` dòng / `38.3 KB` (med) tiền-impl cho report chỉ `49` dòng; (ii) Dựng `§2b`/`Mini-Spec` nhân tạo cho tài liệu; (iii) Kết xuất Archify HTML 2 lần (`1.61 MB` + `1.60 MB`); (iv) Ép `QC-F1` chạy `4,315` unit tests (`1,283s`) dù `0` dòng code sửa (`2026-11-18-1346`, `EV-005`).
3. **Lỗi đo lường phụ trợ phát hiện trong lúc kiểm tra:** `scripts/tdq_state.py:2335,2417,2422` (`_cli_approve`) đặt `state["phase"] = "implement"` nhưng thiếu `ghi_moc_phase(state, "implement")`, gây `im=0s` giả ở `18` ca `build-full` và cộng dồn phần đầu `implement` vào `plan`/`analyze` (`EV-004`).

---

## 1. Mục tiêu Thiết kế Kiến trúc V1 (6 Trụ cột `M1`–`M6`)

Chuyển dịch toàn bộ trọng tâm thực thi sâu của task Research, Phân tích, Debug-RCA và Báo cáo sang pha **`implement`**, giữ `analyze → spec → plan` ở mức **Scoping/Triage nhẹ**, hỗ trợ fan-out không cần Git Worktree khi chỉ đọc/ghi kho bằng chứng, bảo toàn `100%` dữ kiện qua nhiều lần `/compact`, và thay kiểm thử code thừa bằng kiểm chứng bằng chứng chống lỗi **F6**.

---

## 2. Đặc tả Kỹ thuật từng Module (`M1`–`M6`)

### M1 — Hồ sơ Công việc `work_kind` & Sửa Lỗi Ghi Mốc Telemetry (`scripts/tdq_state.py`, `phases.md`)

- **Cấu trúc State (`schema_version = 6` giữ nguyên tương thích ngược):**
  - Thêm khóa `"work_kind": "build"` vào `default_state()` (`scripts/tdq_state.py:215-298`).
  - Hằng số & chuẩn hóa fail-closed (kiểu `normalize_muc_qc` tại `L196-212`):
    - `VALID_WORK_KINDS = ("build", "investigate")`
    - `WORK_KIND_MAC_DINH = "build"`
    - `WORK_KIND_ALIASES`: `"research"`, `"analysis"`, `"audit"`, `"debug-rca"`, `"rca"`, `"report"`, `"phan-tich"`, `"dieu-tra"`, `"nghien-cuu"`, `"investigate"` → `"investigate"`; `"build"`, `"code"`, `"dev"`, `"feature"` → `"build"`. Mọi giá trị rác/rỗng/`None` trả về `"build"` kèm `_warn()`.
    - Thêm `work_kind_hieu_luc(state) -> str`.
- **CLI & Hiển thị:**
  - `tdq_state.py init <slug> <lane> [--kind build|investigate] [--lang <code>]`: cho phép đặt ngay khi mở request (mặc định `build`), và `set work_kind=<val>` (`L3118+`).
  - `render_state_md` (`L1932-1974`): bổ sung dòng `| Work kind | {work_kind_hieu_luc(state)} |` (vẫn nằm gọn dưới ngưỡng `<= 30` dòng của `STATE.md`).
  - `next_headline` (`L1837-1844`) hoặc dòng 2 `render_next` (`L1888-1929`): khi `work_kind == "investigate"`, in rõ `Work kind: investigate` để cả leader lẫn subagent/compact anchor nhìn thấy ngay.
- **Định tuyến `PHASE_TABLE` không phá `tests/test_phase_table.py` (`EV-006`):**
  - **Không sửa `len(PHASE_TABLE) == 11` hay `VALID_LANES`:** Giữ nguyên `PHASE_TABLE`, `PHASE_ORDER` và `skills/tdq-conventions/references/phases.md` (giữ xanh `test_all_phases_covered`, `test_docs_match_constant`).
  - Áp dụng đúng pattern `MODE_ROWS` (`tdq_state.py:1707`): bổ sung bảng **`INVESTIGATE_PHASE_ROWS`** nằm ngoài `PHASE_TABLE`, phủ các khóa `"analyze"`, `"spec"`, `"plan"`, `"implement"`, `"qc"`, `"quick_analyze"`, `"quick"`.
  - Tại `phase_row(state)` (`L1779-1793`): nếu `work_kind_hieu_luc(state) == "investigate"` và `key in INVESTIGATE_PHASE_ROWS`, trả hàng điều tra tương ứng (nếu `key == "implement"` và `mode == "subagent"` → giữ checklist điều phối subagent/wave không ép worktree).
- **Sửa lỗi ghi mốc phase ở `_cli_approve` (`EV-004`):**
  - Bổ sung `ghi_moc_phase(state, state["phase"])` ngay sau khi chuyển `phase` tại `scripts/tdq_state.py:2335`, `2417`, `2422` để `implement` không bị ghi nhầm thời gian bằng `0s` vào `timing.jsonl`.

### M2 — Điều phối `no_worktree`, Kho Bằng chứng `evidence` CLI & Lint (`tdq_team.py`, `tdq_bench.py`, `doc_lint.py`)

- **Mở rộng phân công cho task artifact trong `scripts/tdq_team.py`:**
  - Hàm `is_artifact_only_paths(paths: list[str], active_slug: str = "") -> bool`: trả `True` chỉ khi danh sách `paths` không rỗng và mọi đường dẫn chuẩn hóa `/` nằm strictly trong `docs/tdq/artifacts/` hoặc `docs/tdq/research/` (cấm `..`).
  - Cập nhật `_finalize_tasks` (`L302-312`) và `quyet_dinh_task` (`L546-564`): nếu `task.vung_file` rỗng nhưng `task.sinh_ra` không rỗng và `is_artifact_only_paths(task.sinh_ra)` đúng, dùng `task.sinh_ra` làm tập đường dẫn kiểm va chạm (`vung_file`) để tránh rơi giả vào `("tu_lam", "vung-khoa")` (`EV-007`).
  - Trong `lenh_phan_cong` (`L775-815`): ghi thêm trường `"worktree_required": not is_artifact_only_paths(vung)` vào từng bản ghi task của `docs/tdq/team/<slug>.json`.
  - Trong `lenh_cum` (`wave`, `L899-956`) và `canh_bao_lach_luat`: các task có `"worktree_required": false` được gắn nhãn `[no-worktree]`, chạy song song qua `Workspace="inherit"` ngay trên nhánh request mà không cần gọi `tdq_team.py open <task>` tạo Git Worktree; leader vẫn gọi `detect_tcas_collision` / kiểm trùng file đích để cấm hai task cùng đợt ghi vào 1 file artifact.
- **Mở rộng `scripts/tdq_bench.py` (`EV-007`):**
  - `mo_phong_tasks` (`L257-303`) nhận biết task có `worktree_required == False`: được tính vào các wave song song thay vì bị cộng dồn vào hàng chờ tuần tự `tu_lam` của leader (`t_hop`/`t_don` worktree đặt về `0.0` cho nhánh `no_worktree`, vẫn giữ `t_phat`/`t_kiem`).
- **Kho Bằng chứng Bền vững (`evidence` CLI trong `scripts/tdq_team.py`) (`EV-013`):**
  - Lưu song song 2 tệp (cùng một hàm atomic ghi):
    1. **`docs/tdq/artifacts/<slug>/evidence-log.json` (hoặc `evidence.jsonl` — append-only event log bất biến)** gồm: `id` (`EV-001`, tăng dần), `ts`, `task_id`, `hypothesis`, `status` (`verified | single-source | inferred | refuted`), `source` (`URL` hoặc `path:line`), `excerpt`, `raw_artifact_path`. Không bao giờ ghi đè sự kiện cũ — muốn bác bỏ chỉ nối thêm bản ghi `"status": "refuted"` (`EV-013`, mô hình OpenHands).
    2. **`docs/tdq/artifacts/<slug>/evidence-log.md`** (bảng Markdown tự kết xuất/nối để con người và QC agent đọc ngay không cần script), kèm gọi `blackboard_record(...)` (`tdq_team.py:2480`) đồng bộ tóm tắt sang `.tdq-runtime/blackboard/<slug>.json`.
  - Lệnh CLI: `tdq_team.py evidence add --task <id> --claim "<...>" --source "<url|path:line>" [--excerpt "<...>"] [--hypothesis H1] [--status verified] [--raw <path>]` · `tdq_team.py evidence list [--json]` · `tdq_team.py evidence summary [--json]`.
- **Thích ứng `scripts/doc_lint.py` cho tài liệu `investigate` (`EV-008`):**
  - Thêm `_is_investigate_doc(doc)` nhận diện header `Work kind: investigate` / `Loại việc: investigate` trong 15 dòng đầu (hoặc qua `tdq_state`).
  - Trong `r15_loi` (`L905-923`):
    - Khi doc là `investigate` và task KHÔNG chạm `EXT_MA_NGUON`: không ép `Ownership Map` kiểu code contract, không ép cấu trúc 8 trường code (`Req`/`Giao tiếp`/`EARS` code), nhưng **VẪN BẮT BUỘC**: `Chạm:`/`Sinh ra:` rõ tệp artifact (tách biệt theo wave), `Test:`/`Kiểm:` đo được (chặn `ANTI-2`!), cấm `BANNED_PLACEHOLDERS` (`TBD`/`TODO`/`...`), và giữ `## Phân bổ Model & Effort` (`implement`, `qc`, `report`) cho lane `full`.
    - Khi 1 task của plan `investigate` có chạm `EXT_MA_NGUON` (ví dụ viết script đo tạm hoặc vô tình đụng code): tự động kích hoạt lại `R15-Full`/`R15-Compact` trên task đó (fail-closed).
    - **Track 1 Evidence Lint (mở rộng tùy chọn hoặc trong `check-evidence`):** kiểm định cấu trúc `0` LLM cho báo cáo `investigate` — đối chiếu mọi tag `[EV-xxx]` có mặt trong `evidence-log` và đường dẫn `path:line` tồn tại thật trên đĩa (`EV-017`).

### M3 & M4 — Scoped-Write Python + Rust, Nhắc Checkpoint & Compact Recovery (`hooks/`)

- **Quyền ghi hẹp `scoped-write` đồng bộ Python (`_common.py`, `edit_gate.py`, `bash_gate.py`) & Rust (`storage.rs`, `pre_tool_use.rs`) (`EV-009`, `EV-012`):**
  - Hàm dùng chung `is_investigation_artifact_target(target_path, cwd, active_slug)` ở cả Python (`hooks/scripts/_common.py`) và Rust (`hooks/rust/tdq-dispatch/src/events/pre_tool_use.rs`):
    - Fail-closed nếu `active_slug` rỗng/None hoặc chứa `/`, `\`, `..`.
    - Chuẩn hóa đường dẫn lexical (`normalize_lexical`) + canonical (`realpath`/`canonical_or_ancestor`) trên toàn bộ Windows/Unix case-insensitivity.
    - Chỉ trả `True` khi phần mở rộng nằm trong `{".md", ".json", ".jsonl"}` VÀ đường dẫn tương đối thuộc strictly:
      - `docs/tdq/artifacts/<active_slug>/...`, HOẶC
      - `docs/tdq/research/<active_slug>.md` hoặc `docs/tdq/research/<active_slug>-*.md`.
    - Loại trừ `docs/tdq/state.json`, `docs/tdq/STATE.md`, `docs/tdq/qc/**` (chỉ riêng `tdq-qc-tester`), `docs/tdq/spec/**`, `docs/tdq/plan/**`, và `100%` mã nguồn.
  - Danh sách role được cấp `scoped-write`: `explorer`, `debugger`, `reviewer` (giữ nguyên **`tdq-security-reviewer` chỉ đọc `100%`**, `tdq-qc-tester` chỉ ghi `docs/tdq/qc/*.md`, `browser` chỉ đọc).
  - Trong `edit_gate.py:91-101` & `pre_tool_use.rs:290-302`: cho phép edit khi thỏa `is_investigation_artifact_target`, và **ghi luôn `observe("edit")`** (vá đồng thời Gap #4 ở `EV-010`).
  - Trong `bash_gate.py` & `pre_tool_use.rs:handle_command_tool`: giữ **CHẶN TUYỆT ĐỐI `[TDQ:READONLY]`** đối với mọi shell mutator cho các role điều tra (chỉ cho ghi qua tool `Write`/`Edit` vào đúng vùng `scoped-write`, không mở lỗ hổng shell redirect).
  - Vá Gap #8 (`EV-012`): dọn nhánh legacy fallback của `tools/patches/agy_hooks.py:1725-1751, 1873-1884` để compiler luôn sinh/giữ đồng nhất bản mới, đồng thời đồng bộ root `bash_gate.py` & `edit_gate.py`.
- **Nhắc Checkpoint định kỳ chống mất dữ liệu khi `/compact` (`read_gate.py` + vá Rust `pre_tool_use.rs:444`) (`EV-010`, `EV-013`):**
  - *Vá nút thắt `pre_tool_use.rs:444-463` (Gap #3 `EV-010`):* Hiện Rust cho qua `Allow` ngay mọi `read_file` có `StartLine`/`EndLine`/`offset`/`limit`, khiến `read_gate.py` mù hoàn toàn với đọc theo dải dòng! Trong V1:
    - Ở `work_kind == "investigate"` & `effective_phase == "implement"`, hoặc theo đếm đọc tích luỹ ngay trong Rust/session ledger: bỏ qua fast-allow mù để đếm lượt đọc tích luỹ (nhẹ `< 1ms`), vẫn chỉ REMIND (`allow`) chứ không block.
  - Thêm hằng `CHECKPOINT_READ_THRESHOLD = 12` và `_maybe_remind_checkpoint(cwd, payload, state, rows)` trong `hooks/scripts/read_gate.py`:
    - Chỉ kích hoạt khi `work_kind_hieu_luc(state) == "investigate"` và `effective_phase(state) == "implement"`.
    - Đọc `mtime` của `docs/tdq/artifacts/<slug>/evidence-log.md` (hoặc `evidence.jsonl`; `0` nếu chưa tồn tại).
    - Đếm số lần đọc/truy xuất sau mốc `mtime` đó; khi đạt `>= 12` lần chưa cập nhật kho bằng chứng → queue/emit **nhắc nhẹ `[TDQ:CHECKPOINT]`** (tối đa 1 lần cho mỗi mốc `mtime`, chỉ REMIND với `permissionDecision="allow"`). Ngay khi cập nhật `evidence-log`, bộ đếm reset về `0`.
- **Hồi phục sau nhiều lần `/compact` (`session_start.py` + Rust `storage.rs` & `pre_invocation.rs`) (`EV-010`, `EV-013`, `EV-014`):**
  - Trong `storage.rs`: thêm `pub work_kind: Option<String>` vào `TdqState` (`L19`) và bổ sung `"mode"` vào `effective_phase` (`L44-49`, vá Gap #1).
  - Trong `pre_invocation.rs:157`: mở rộng điều kiện từ `source == "compact"` sang `source in ("compact", "resume")` → `RouteOutcome::DelegatePython` (vá Gap #2).
  - Trong `session_start.py:349-410`: giữ chặt **Pointer-Only `[TDQ:ANCHOR]` (`<= 600 chars`)** theo bài học Cursor/OpenHands (`EV-013`, `EV-014`), **không nhồi văn xuôi bằng chứng** làm phình anchor:
    - Chỉ nối 1 dòng con trỏ khi `work_kind == "investigate"` hoặc tồn tại `evidence-log`:
      `work_kind={work_kind} ledger=docs/tdq/artifacts/{req}/evidence.jsonl md=docs/tdq/artifacts/{req}/evidence-log.md checkpoints={count} artifacts={artifacts_count} last={last_id}`
    - Khi sau `/compact`, agent đọc 1 phát `evidence-log.md` và danh sách file trong `docs/tdq/artifacts/{req}/` là phục hồi trọn vẹn trạng thái nghiên cứu qua `2–3` lần compact liên tiếp.

### M5 — Quy chuẩn Vòng đời `investigate-mode.md`, Tách Debug-RCA vs Bugfix & Bộ `QC-I1..I4`

- **Bảo vệ trần Token Budget (`EV-011`) bằng kiến trúc 1-Tier Reference sạch:**
  - Vì `spec-template.md` (`14` tok headroom), `qc.md` (`21` tok headroom), `team-mode.md` (`28` tok), `tdq-conventions/SKILL.md` (`0` dòng), `tdq-intake/SKILL.md` (`0` dòng), `tdq-build/SKILL.md` (`2` dòng) đều cực kỳ chật:
  - Tạo **`1` file chân lý mới**: `skills/tdq-conventions/references/investigate-mode.md` (~`1,800–2,400` tokens, an toàn dưới trần `3,500`) chứa toàn bộ quy trình 4 chặng:
    1. **Scoping & Triage nhẹ (`analyze` / `quick_analyze`):** Chỉ đọc bề mặt (entry points, `1–2` truy vấn định danh thuật ngữ, check infra loại red herrings), lập **Confirmed Facts vs 2–4 Candidate Hypotheses (kèm falsification criteria)**, hỏi câu làm đổi phạm vi/định dạng. **Cấm** chạy research đa vòng, cấm đọc sâu hàng chục file hay giải xong RCA trước khi plan được duyệt.
    2. **Spec & Plan Điều tra (Unified Intent-Planning):**
       - `spec` (với `full`) bỏ yêu cầu tạo `§2b` module code giả tạo (`EV-005`) và bỏ `Log service` bắt buộc nếu `0` code chạy được; thay bằng câu hỏi nghiên cứu, ma trận giả thuyết, nguồn/công cụ dự kiến và `§6` tiêu chí bằng chứng.
       - `plan` (và `quick` mini-plan) khai báo nhánh độc lập, **3 câu hỏi Fan-Out Breakeven Gate** (từ Google/MIT `45%` saturation & `17.2x` vs `4.4x` error amplification, `EV-015`), và **định mức Effort Tier** (`Straightforward`: 1 nhánh, `<= 5` calls; `Standard`: 2–3 nhánh, `<= 10` calls/nhánh; `Deep`: 3–4 nhánh, `<= 15` calls/nhánh, hard stop khi `2` lượt liên tiếp không ra fact mới = diminishing returns, `EV-016`).
    3. **Implement Sâu (`Collect` tách khỏi `Write` + Multi-Pass + Log thường xuyên):**
       - Pha **Collect:** Fan-out Centralized hub-and-spoke (`TRAN_SONG_SONG = 4`) khi qua Breakeven Gate; pin model gọn (`flash` cho quét thô có schema, `inherit`/`pro` cho RCA/tổng hợp/Red-Team); mỗi worker ghi thẳng raw evidence vào `docs/tdq/artifacts/<slug>/<task>.md`, gọi `tdq_team.py evidence add` (tối đa `3` vòng sửa truy vấn/error-reflection mỗi nhánh), chỉ trả digest `<= 1,500` ký tự về leader.
       - Với **Debug-RCA (`work_kind=investigate`):** Bắt buộc `tdq-debugger` tách **Manifestation Step** với **Point-of-Commitment Step** (`CAR`, `EV-018`) và thực thi ít nhất 1 **Counterfactual Falsification Test** trước khi xếp hạng nguyên nhân gốc.
       - Pha **Write / Hội tụ V2:** Tách riêng sau Collect; tổng hợp báo cáo đối chiếu trực tiếp `evidence.jsonl` (mọi luận điểm gắn tag `[EV-xxx]` và nhãn độ tin cậy `Verified` / `Single-source` / `Inferred` / `Unverified`).
    4. **Tách ranh giới Bugfix có sửa code (`work_kind=build`):**
       - Cập nhật `skills/tdq-intake/references/issue-triage.md` (đang còn `3,042` tokens headroom!): giữ triage nhẹ ở `analyze` (log + triệu chứng + repro tối thiểu + 2–4 giả thuyết), cho phép đặt task **P1.1 Deep RCA + Red Regression Test** vào đầu `implement` nếu nguyên nhân gốc chưa lộ rõ ở bước triage (`EV-018`), tránh đẩy cả debug 1 tiếng ra tiền-implement.
    5. **Chuẩn QC Bằng chứng (`QC-I1..I4`) thay cho `QC-F1` (`EV-017`):**
       - **Mức chi tiết `QC-I1..I4` đặt trong `skills/tdq-build/references/qc-vong-fix.md`** (đang `536/3500`, còn dư **`2,964` tokens!**) hoặc `investigate-mode.md`, và chỉ thêm đúng **1 dòng con trỏ (< 21 tokens)** vào `qc.md` (`EV-011`) để tuyệt đối không vỡ R13!
       - `QC-I1` (**L1 Deterministic + L4 Tool Oracle, `0` LLM):** kiểm toàn bộ `[EV-xxx]` tồn tại trong `evidence.jsonl`, `100%` `path:line` tồn tại trên đĩa và `0` code touched (`git diff --name-only` nếu thuần `docs`).
       - `QC-I2` (**L2 Focused Grounding chống F6 kiểu MiniCheck):** `tdq-qc-tester` (hoặc `tdq-reviewer` ở `full`) đối chiếu trực tiếp cặp **(Claim trọng yếu ↔ Raw snippet của `EV-xxx`)** để xác nhận nguồn *thực sự chứng minh* mệnh đề (Citation Precision + Recall).
       - `QC-I3` (**Red-Team / Counterfactual Pass độc lập):** kiểm bằng chứng bỏ sót, nguồn đối nghịch, giả thuyết thay thế chưa bác bỏ; với `ultra` chia song song tối đa `5` shard theo `tdq-config.json`.
       - `QC-I4` (**Nhãn tin cậy & Surgical Repair):** mọi claim dưới ngưỡng grounding phải sửa phẫu thuật tại chỗ hoặc hạ cấp thành `Single-source` / `Unverified`.
       - **Chốt an toàn fail-safe:** Nếu `git diff --name-only` phát hiện bất kỳ thay đổi tệp mã nguồn (`EXT_MA_NGUON`), `qc` BẮT BUỘC tự động bật lại `QC-F1` + `QC-F4`.
- **Gắn con trỏ 1 tầng tại `SKILL.md` & 3 agent prompts:**
  - Rà soát rút gọn nhẹ 1–2 câu trùng trong `tdq-conventions/SKILL.md` (`209/209`), `tdq-intake/SKILL.md` (`148/148`), `tdq-build/SKILL.md` (`172/174`) hoặc tăng nhẹ `SKILL_LINE_LIMITS` tương ứng (`<= 5` dòng) với sự đồng thuận khi triển khai để giữ `doc_lint` xanh.
  - Cập nhật `agents/tdq-explorer.md`, `agents/tdq-debugger.md`, `agents/tdq-reviewer.md`: ghi rõ quyền `scoped-write` vào `docs/tdq/artifacts/<active_slug>/` + `docs/tdq/research/<active_slug>*.md`, giữ nguyên `model: inherit`, `Auto-Clarity`, digest `<= 1,500` chars, và bổ sung bước `Point-of-Commitment vs Manifestation` cho `tdq-debugger.md`.

### M6 — Đồng bộ Compiler AGY, Token Lock & Chiến lược Kiểm thử (`tools/patches/`, `tests/`)

- **Cập nhật `tools/patches/skills_and_agents.py` (`EV-012`):**
  - Rút `tdq-explorer.md`, `tdq-debugger.md`, `tdq-reviewer.md` khỏi `_STRICT_READONLY_AGENTS` (chỉ giữ `tdq-security-reviewer.md` strictly read-only 100%); chuyển `tools` của 3 agent này sang `_WRITER_TOOLS` để AGY cho phép gọi `write_file`/`edit_file` vào vùng `scoped-write` (và hook Python+Rust `READONLY` tự khóa chặt mọi đích ghi ngoài vùng artifact/research).
  - Thêm block `> **Scoped Artifact Write:** ...` rõ ràng trong transform agent của `skills_and_agents.py:142-180`.
- **Cập nhật `tools/patches/agy_hooks.py`:**
  - Đồng bộ `_patch_read_gate` cho thông báo `[TDQ:CHECKPOINT]` dùng dual-channel `remind` tương thích AGY (`DOC`/`CHECKPOINT`), kiểm `_patch_edit_gate` & `_patch_session_start` sạch, bỏ fallback legacy lệch nhịp.
- **Biên dịch & Kiểm thử:**
  - Chạy `token_budget.py --khoa` khóa `docs/tdq/token-budget.json` sau khi đo mọi file dưới `3,500` tokens.
  - Biên dịch Rust `cargo test && cargo clippy -- -D warnings && cargo build --release`, sau đó chạy `tools/build_agy_plugin.py --upstream .` và `agy.EXE plugin validate plugins/tdq-workflow-agy --strict --json` (`findings: []`).
  - Viết `tests/test_investigate_workflow.py` phủ: `work_kind` normalization/state/rows, `_cli_approve` phase milestone bugfix, `evidence add|list|summary`, `no_worktree` assignment + `tdq_bench`, `doc_lint` cho plan `investigate` + track L1 `[EV-xxx]`, bảng vector đối kháng `scoped-write` (hợp lệ vs `..`, symlink, Windows case, slug khác, `qc/`, `scripts/`, `security-reviewer`, shell mutator) chạy song song trên CẢ Python gate VÀ `tdq-dispatch.exe`, `read_gate` checkpoint ở lượt `12` (bao gồm ranged reads), `session_start` compact & resume recovery (`<= 600` char anchor), và `TDQ_LOG=0`.

---

## 3. Các Điểm Giả định & Rủi ro cần Red-Team A · B · C Tấn công ở Wave 3

1. **Cho Red-Team A (Nhận thức, `/compact` nhiều vòng & Chi phí Token):**
   - Trong `investigate`, nhiều lượt tìm kiếm gọi **`grep_search`, `run_command`, `call_mcp_tool` (`tavily`/`chrome-devtools`/`lsp`)** chứ không chỉ gọi `read_file`! Nếu `read_gate.py` chỉ đếm lượt đọc file (`Read`) tới mốc `12` để nhắc `[TDQ:CHECKPOINT]`, liệu tác tử gọi 25 lượt `tavily_extract` hoặc `run_command` mà chỉ 3 lượt `Read` có bị **bỏ lọt hoàn toàn không bao giờ thấy `[TDQ:CHECKPOINT]`** trước khi `/compact` nổ ra không?
   - Kịch bản `/compact` 2–3 lần liên tiếp: `session_start.py` chỉ bơm pointer `evidence.jsonl`, vậy nếu một sub-task điều tra đang làm dở (`doing=T1.2`) nhưng chưa ghi vào `evidence-log` và `read_file` có range từng đọc nhiều đoạn, khôi phục có bị mất mạch giả thuyết đang kiểm chứng hay không? Liệu việc ghi đồng thời `evidence.jsonl` + `evidence-log.md` + `blackboard` + shard `<task>.md` có tạo lại "bẫy chi phí `todo.md` 1/3 actions" mà Manus cảnh báo (`EV-013`) hay không?
2. **Cho Red-Team B (Bảo mật `scoped-write`, Parity Python↔Rust & Xung đột Linter/Tests):**
   - Mở `_WRITER_TOOLS` (`write_file`, `edit_file`) cho `tdq-explorer`/`tdq-debugger`/`tdq-reviewer` trên AGY và cho phép `scoped-write`: kiểm tra lại `tests/test_agent_frontmatter.py`, `tests/test_agent_upgrade_mvp.py`, `tests/test_doc_lint.py` xem test nào ghim cứng read-only `tools` trên 3 agent này!
   - Xem `pre_tool_use.rs:33`: `detect_subagent_role` có thể fallback sang `"subagent"` hoặc `role_opt` tùy host truyền `agent_type`/`sessions.json` — chuyện gì xảy ra nếu 1 subagent mang role `Explorer Agent` hay `tdq-explorer` gọi tool có alias đường dẫn (`TargetFile` vs `file_path` vs `target_path`) hoặc `run_command` tạo file qua PowerShell trong `docs/tdq/artifacts/`?
   - Kiểm tra trần dòng `SKILL_LINE_LIMITS` (`tdq-conventions 209/209`, `tdq-intake 148/148`, `tdq-build 172/174`) và trần `token-budget.json` (`qc.md 3479/3500`, `spec-template.md 3486/3500`, `team-mode.md 3472/3500`): chèn thêm con trỏ ở M5 có bẻ gãy `doc_lint R6`/`R13` hoặc `test_phase_table.py` không? Và sửa `pre_tool_use.rs:444` (ranged read bypass) có làm chậm hoặc kích nổ sai cảnh báo đọc lặp khi agent đang đọc file từng dải `100` dòng (`read_gate.py` hợp lệ) hay không?
3. **Cho Red-Team C (Stress-Test trên `4` ca thật trong kho `docs/tdq/`):**
   - Mô phỏng áp V1 lên đúng `4` ca thực tế:
     1. Research/Analysis `full`: `2026-11-20-1056-phan-tich-nang-cap-agent` (`49.9%` tiền-impl, `515L` tiền-impl, double Archify, `3` module `§2b` giả).
     2. Research/Audit `quick`: `2026-11-19-1457-audit-sai-sot-noi-hook` (`99.7%` `analyze`, `0s` `implement`, `ANTI-2` `assert True` trong mini-plan).
     3. Debug/Scan `full`: `2026-11-18-1346-scan-hook-anh-huong-runtime` (`0` code sửa, `QC-F1` ép chạy `4,315` tests `1,283s`, kết hợp mẫu bug `2026-11-08-1141`).
     4. Bugfix có sửa code (`build`): `2026-11-16-1953-fix-lsp-gate-mcp-routing` (`7,482s` / `28.9%` tiền-impl vs `5,836s` `implement`).
   - Soi xem khi áp V1 trên 4 ca này, bước nào bị vướng `approve spec` / `approve plan`, ca `quick` có giữ gọn trong `1` lần duyệt không, và phần `implement` có thật sự nhận trọng tâm mà không bị rụng chất lượng hay không.
