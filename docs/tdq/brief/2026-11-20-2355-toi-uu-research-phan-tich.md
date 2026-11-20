# Brief: Tối ưu luồng cho task Research và Phân tích

Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

## Nguyên văn

> okay bây giờ tôi muốn mở request để handle tối ưu cho những task resreach và phân tích, do bây giờ tôi thấy đa phần nó sẽ đi resreach và phân tích trước cả khi vào phase implement hãy check lại xem nhận định có đang đúng ko?

### Đọc hiểu ban đầu

- **Mục tiêu:** Kiểm chứng thực trạng thời gian/luồng xử lý của các task research và phân tích trong TDQ Workflow, sau đó thiết kế và triển khai cơ chế tối ưu cho nhóm task này để loại bỏ việc làm lặp (double-work), cắt thủ tục dư thừa (nhiều vòng spec/plan/implement trống) mà vẫn giữ chất lượng phân tích, phản biện và đầu ra trực quan.
- **Kiểm chứng nhanh nhận định của người dùng (dữ liệu thật trên `docs/tdq/timing.jsonl`, `173` request):**
  - **Toàn bộ `173` request:** Thời gian trước `implement` (`analyze + spec + plan`) chiếm `37.5%` tổng thời gian phi-idle (so với `implement` `27.0%`); có `89/173` (`51.4%`) request tốn thời gian tiền-implement lớn hơn `implement`.
  - **`30` request gần nhất:** Thời gian trước `implement` tăng lên **`64.7%`** (`analyze` `27.4%` · `spec` `7.2%` · `plan` `30.1%`), trong khi `implement` chỉ còn **`7.0%`**; có **`23/30` (`76.7%`)** request tốn thời gian tiền-implement nhiều hơn `implement`.
  - **Nhóm task thuần research / phân tích / audit (`27/173` slug khớp từ khóa `phan-tich|research|audit|scan|chi-tiet-plan|...`):**
    - `2026-11-20-1056-phan-tich-nang-cap-agent` (`lane=full`, thuần `docs`): `49.9%` thời gian (`2,498s`) nằm ở `analyze`/`spec`/`plan` trước khi vào `implement` (`483s`, `9.6%`) rồi `qc` (`1,191s`) + `report` (`838s`).
    - `2026-11-19-2213-chi-tiet-plan-model-thap` (`lane=full`, thuần phân tích + Red-Team): `46.5%` (`3,502s`) ở `analyze`/`spec`/`plan` so với `implement` (`1,322s`, `17.6%`).
    - `2026-11-19-1457-audit-sai-sot-noi-hook` (`lane=quick`): `99.7%` (`2,413s`) ở `analyze`, `0s` ở `implement`, `8s` ở `report`.
    - `2026-11-19-1612-research-behavior-va-hieu-nang` (`lane=quick`): `99.6%` (`568s`) ở `analyze`, `0s` ở `implement`, `2s` ở `report`.
  - **Nguyên nhân cấu trúc:** TDQ Workflow hiện chỉ có `2` lane (`quick` và `full`), cả hai đều ép vào khung phát triển code (`analyze → spec/mini-plan → implement → qc → report`) và đặt bước đọc code 3 chiều + subagent research + phỏng vấn ngay trong `analyze`. Vì vậy với task thuần research/phân tích, lõi công việc đã diễn ra gần hết ngay trước `implement`, khiến các bước sau hoặc lặp việc (`full`) hoặc rỗng `0s` (`quick`).
- **Phạm vi dự kiến:** Thiết kế lại luồng/lane hoặc chế độ chuyên biệt cho task research & phân tích (chạm `skills/tdq-intake`, `skills/tdq-conventions`, `scripts/tdq_state.py`, `scripts/doc_lint.py`, `hooks/`, và đồng bộ bản build `plugins/tdq-workflow-agy/`).
- **Điểm cần làm rõ sau khi chọn pipeline:**
  - Nên tách hẳn một **lane thứ 3** chuyên cho Research/Phân tích (ví dụ `research`/`analysis`: `intake → scope → research/analyze → verify/red-team → report`, không qua `spec`/`plan`/`implement` code) hay bổ sung cơ chế chuyển nhánh/rút gọn trong `full`/`quick`?
  - Tiêu chuẩn đầu ra bắt buộc của task research/phân tích (Markdown + Archify HTML, bắt buộc trích nguồn/dòng code, tùy chọn Red-Team/phản biện độc lập, có mở nhánh git hay không, cách chuyển tiếp sang request implement sau khi chốt đề xuất).
  - Tối ưu luôn cả phần research/phân tích trước `implement` của các task code thông thường (cắt trùng lặp giữa `analyze` → `spec` → `plan`) hay tập trung trước vào nhóm task thuần research/phân tích.

## Hiểu & kiến thức

### Năng lực dùng được

Phân vân → DÙNG. Kiểm kê ngày 2026-11-21: `42` skill trên đĩa (`23` giữ + `19` ẩn qua `skill_inventory.py --loc "research analyze debug workflow intake spec plan build"`), cộng skill built-in trong context.

| Skill | Nguồn | Phán quyết | Dùng ở đâu / Lý do loại |
|---|---|---|---|
| `tdq-intake` / `tdq-spec` / `tdq-plan` / `tdq-build` / `tdq-conventions` | plugin:tdq-workflow | NỀN | Khung pipeline deep/express, trạng thái, cổng duyệt, QC và báo cáo |
| `tdq-setup` / `tdq-status` / `tdq-lean` | plugin:tdq-workflow | NỀN | Kiểm định tầng tìm kiếm 3 lớp và rà soát tinh gọn mã nguồn |
| `agy-customizations` / `antigravity-guide` | built-in | DÙNG | Đối chiếu cấu trúc plugin/hook/subagent Antigravity 2.0 khi đồng bộ `plugins/tdq-workflow-agy/` |
| Đã xét 38 skill khác | user/plugin/built-in | KHÔNG | khác lĩnh vực |

### Khảo sát mã nguồn 3 chiều (Grep · LSP · Graphify)

| Vùng file chạm | Phát hiện qua lớp nào (Grep/LSP/Graphify) | Tác động & quan hệ |
|---|---|---|
| `scripts/tdq_state.py` (`VALID_LANES`, `default_state`, `PHASE_TABLE`, `phase_row`, `render_phases_md`) | LSP `find_references` (`3` refs) · Graphify `affected` (`50+` nodes) · Grep | Trung tâm state & bảng phase. Hiện chưa có trường phân loại bản chất công việc (`build` vs `investigate`), nên mọi phase từ `analyze` → `qc` đều hiển thị checklist định hướng viết code. |
| `skills/tdq-intake/` (`SKILL.md`, `analyze-full.md`, `quick-lane.md`, `lane-decision.md`, `issue-triage.md`, `nhanh-request.md`) | Grep `quick_analyze`/`loai_request` · Đọc trực tiếp | Bắt buộc B1 sâu (Tam Giác 3 Chiều) + B2 subagent research ra `docs/tdq/research/<slug>.md` + `issue-triage` tái hiện/tìm root cause ngay trong `analyze`/`quick_analyze`, gây dồn toàn bộ lõi công việc ra trước `implement`. |
| `skills/tdq-spec/` & `skills/tdq-plan/` (`SKILL.md`, `spec-template.md`, `plan-template.md`, `planner-rules.md`) | Grep `Chạm:`/`R15` · Đọc trực tiếp | Ép mẫu phần mềm chạy được (`§2b` LSP boundary, `§3c` giải thuật, `§4` log service, `Chạm:` trỏ file code, `Test:` unit test). |
| `skills/tdq-build/` (`SKILL.md`, `references/qc.md`, `references/team-mode.md`, `references/report-template.md`) | Grep `QC-F1` · Đọc trực tiếp | `implement` ép `red → green` + `tdq_test.py vung-cham` + `tdq-implementer` trong Git Worktree; `qc.md` ép `QC-F1` (`tdq_test.py tron-bo` `4,563` test) dù không sửa dòng code nào. |
| `scripts/tdq_team.py`, `scripts/tdq_bench.py`, `scripts/doc_lint.py`, `scripts/tdq_plan_scaffold.py` | Grep `rule_r15` · Graphify `r15_loi`/`pair` · Đọc trực tiếp | `tdq_team.py:550` giữ `tu_lam` (`vung-khoa`) nếu task không có `Chạm:` và ép mở worktree cho mọi task `giao`; `tdq_bench.py` lỗi nếu thiếu `Chạm:`; `doc_lint.py` R15 kiểm cấu trúc task & `## Phân bổ Model & Effort`. |
| `hooks/scripts/{edit_gate.py,bash_gate.py,stop_gate.py,_common.py}` & `hooks/rust/tdq-dispatch/src/{storage.rs,events/pre_tool_use.rs}` | Grep `READONLY`/`explorer`/`debugger`/`is_qc_report_target` · Đọc trực tiếp | Chặn ghi `READONLY` hoàn toàn với `tdq-explorer`, `tdq-debugger`, `tdq-reviewer` (chỉ `tdq-qc-tester` được ghi `docs/tdq/qc/*.md`); chưa cho ghi kho bằng chứng cô lập (`docs/tdq/artifacts/<slug>/` hoặc `docs/tdq/research/`) nếu bật fan-out điều tra. |
| `tools/build_agy_plugin.py`, `tools/patches/*`, `plugins/tdq-workflow-agy/`, `tests/*` | Grep `loai_request`/`quick_analyze` · Đọc trực tiếp | Biên dịch đồng bộ bản AGY và khóa hồi quy qua test suite (`test_phase_table.py`, `test_doc_lint.py`, `test_agent_upgrade_mvp.py`, `test_team_*`, Rust `cargo test`). |

### Kiến thức nghiên cứu ngoài (`docs/tdq/research/2026-11-20-2355-toi-uu-research-phan-tich.md`)

1. **Tách Lightweight Scoping khỏi Heavy Execution (Anthropic, OpenAI Deep Research, Gemini Unified Intent-Planning, LangGraph Open Deep Research):**
   - `analyze → spec → plan` chỉ chạy probe nhẹ đủ khoanh phạm vi, hỏi làm rõ (clarifying questions), khóa `Research/Investigation Brief` + ngân sách (`budget`, `max 3 error-reflection loops`, `completion criteria`), rồi **STOP chờ user duyệt** trước khi vào pha thực thi nặng.
2. **Tách `Collect` khỏi `Write` & Kho Bằng chứng ngoài (External Evidence Store):**
   - Trong `implement`, chia các nhánh độc lập cho subagent (chỉ fan-out khi `>= 2` nhánh độc lập để tránh đốt `~15x` token vô ích cho việc tuyến tính). Worker ghi raw evidence kèm `evidence_id` / URL / `file:line` ra disk và trả digest `<= 1,500` ký tự để diệt lỗi "tam sao thất bản". Bước tổng hợp/viết báo cáo chạy riêng trên kho bằng chứng sạch.
3. **Debug/RCA tách Triage nhẹ khỏi Deep RCA (Augment Code, Databricks AI SRE, ChipAgents, Resolve AI):**
   - `analyze` = Triage nhẹ (triệu chứng, check nhanh infra loại red herrings, lập *Confirmed Facts vs 2–4 Candidate Hypotheses*).
   - `implement` = Deep RCA song song (thu bằng chứng ủng hộ **và tiêu chí bác bỏ** từng giả thuyết, lưu evidence log bấm-mở-được, hội tụ nguyên nhân gốc kèm mức độ tin cậy).
4. **Evidence & Red-Team QC cho đầu ra phi-code (Anthropic CitationAgent, FActScore, ALCE, Dataiku, MADR):**
   - Thay `tdq_test.py tron-bo` bằng kiểm chứng bằng chứng: (a) tách mệnh đề nguyên tử (FActScore) sửa phẫu thuật câu lỗi, (b) kiểm **Citation Precision & Recall** chặn lỗi **F6** (link/file thật nhưng không chứng minh mệnh đề), (c) pass **Red-Team / phản chứng** độc lập từ raw evidence + draft, (d) gán nhãn độ chắc chắn (`Verified` / `Single-source` / `Unverified`, fail-closed).

### Phạm vi đã chốt

- Mặt CHỌN: Đổi trọn vòng đời `analyze → spec → plan → implement → qc → report` cho `work_kind=investigate` (`1A`); nâng cấp tầng điều phối `tdq_team.py` & quyền subagent Python/Rust `tdq-dispatch` (`1B`); áp dụng đồng bộ cho cả `quick` và `full` (`1C`); thuộc tính `work_kind` (`build | investigate`) trong state (`2A`); tách ranh giới Debug-RCA vs Bugfix có sửa code (`3A`); bổ sung chế độ đi sâu research/tổng hợp và ghi log/checkpoint định kỳ chống mất dữ liệu khi `/compact` (`5B`).
- Mặt LOẠI: Không tách lane thứ 3 (`2B`); không gộp lẫn vào `loai_request` (`2C`); không bỏ qua tầng hook/Rust (`1D`, `4B`); không chỉnh sửa plugin cấp người dùng ngoài repo (`~/.gemini/config/plugins/`).
- Bối cảnh: Sản phẩm vận hành thật ưu tiên Google Antigravity 2.0 + giữ tương thích ngược Claude Code / Codex / OpenCode (Python + Rust `tdq-dispatch` + rebuild `plugins/tdq-workflow-agy/`, toàn bộ test hiện có xanh `100%`).
- Mức đầu tư suy ra: đầy đủ — vì đây là sản phẩm vận hành thật đa nền tảng có tầng hook bảo mật Python + Rust và ràng buộc tương thích ngược toàn bộ bộ test.

### Kiến thức đã chốt

- **Mô hình biểu diễn (`work_kind`):** Thêm trường `work_kind` (`build` | `investigate`, mặc định `build`) vào `docs/tdq/state.json` và `tdq_state.py` (`init --kind`, `set work_kind=...`), áp dụng thống nhất cho cả `quick` và `full`. Không thêm lane thứ 3 để giữ tương thích `100%` `VALID_LANES`, `PHASE_TABLE` và toàn bộ test hiện có.
- **Dịch chuyển trọng tâm sang `implement`:** Khi `work_kind=investigate`, `analyze`/`quick_analyze` chỉ làm **Scoping/Triage nhẹ** (đọc bề mặt, xác nhận *Confirmed Facts vs 2–4 Hypotheses*, câu hỏi làm đổi kết quả, cấm research sâu / tái hiện dài trước plan); toàn bộ công việc điều tra sâu, tái hiện debug, fan-out nhiều vòng và tổng hợp nằm trong `implement` (tách pha `Collect` khỏi pha `Write`). Với `bugfix` sửa code (`work_kind=build`), `issue-triage.md` giữ triage nhẹ và cho phép đưa deep RCA vào task đầu `P1` của `implement`.
- **Fan-out không cần Git Worktree & quyền ghi hẹp (`scoped-write`):** `tdq_team.py` hỗ trợ task điều tra `no_worktree` khi vùng ghi chỉ nằm trong `docs/tdq/artifacts/<slug>/` hoặc `docs/tdq/research/`. Python (`edit_gate.py`/`bash_gate.py`) và Rust (`tdq-dispatch/src/events/pre_tool_use.rs`) đồng bộ cấp quyền ghi `.md`/`.json` strictly trong `docs/tdq/artifacts/<active_slug>/` và `docs/tdq/research/<active_slug>*.md` cho `tdq-explorer`, `tdq-debugger`, `tdq-reviewer` (chặn tuyệt đối `..` traversal, mã nguồn, state và shell mutator).
- **Chống mất dữ liệu khi `/compact` (2 lớp):** (1) CLI `tdq_team.py evidence add|list|summary` ghi atomic vào `docs/tdq/artifacts/<slug>/evidence-log.md` (cộng shard `<task>.md` và đồng bộ `.tdq-runtime/blackboard/<slug>.json`), kèm nhắc nhẹ `[TDQ:CHECKPOINT]` ở `read_gate.py` khi đọc quá `12` lượt trong `implement` mà chưa ghi checkpoint; (2) `[TDQ:ANCHOR] Compact recovery` (`session_start.py` + Rust `pre_invocation.rs` delegation) tự động bơm `work_kind`, đường dẫn `evidence-log.md`, số lượng artifact và checkpoint mới nhất ngay sau `/compact`.
- **Chuẩn QC bằng chứng (`QC-I1..I4`):** Khi `work_kind=investigate` không chạm mã nguồn, thay `QC-F1..F4` bằng `QC-I1` (FActScore grounding `file:line`/số đo/lệnh tái hiện), `QC-I2` (Citation Precision/Recall chặn lỗi F6 trên `evidence-log.md`), `QC-I3` (pass Red-Team/phản chứng độc lập `tdq-reviewer`/`tdq-qc-tester`), `QC-I4` (gắn nhãn độ tin cậy `Verified`/`Single-source`/`Unverified` & phủ đủ câu hỏi spec). Tự động bật lại `QC-F1` nếu có sửa mã nguồn thật.
- **Mức QC cho request này:** `full` (chốt bởi user ở câu `5a`).

### Lộ trình

| Bước/phase | CÓ/BỎ | Vì sao |
|---|---|---|
| Research ngoài (B2) | CÓ | Đã hoàn tất 4 truy vấn Tavily + 4 extract về Anthropic Multi-Agent, Deep Research, SWE RCA, FActScore/ALCE tại `docs/tdq/research/2026-11-20-2355-toi-uu-research-phan-tich.md` |
| Interview (2 vòng) | CÓ | Đã chốt đủ phạm vi, kiến trúc `work_kind`, quyền ghi hẹp, checkpoint chống compact, QC-I1..I4 và `muc_qc=full` |
| Spec + Archify HTML Before/After Preview | CÓ | Chạm kiến trúc cốt lõi của TDQ Workflow (state, team, hooks Python+Rust, skills, plugin AGY), cần chốt hợp đồng & sơ đồ Trước/Sau trước khi code |
| Plan (Two-Pass + `## Phân bổ Model & Effort`) | CÓ | Chia 6 module độc lập theo DAG, khai báo bảng Model & Effort cho user duyệt |
| Implement (chia wave `tdq-implementer` + leader giữ `file-luat`) | CÓ | Các module code (`scripts/`, `tests/`, Rust) tách ranh giới sạch theo `§2b`; leader giữ trực tiếp `skills/` & `hooks/` theo luật `file-luat` |
| QC mức `full` | CÓ | Chạy DoD + `tdq_test.py tron-bo` + hồi quy vùng chạm + `cargo test`/`clippy` + `agy plugin validate --strict` + clean code |
| Report (Markdown + Archify HTML) | CÓ | Bắt buộc theo quy trình chuẩn kèm số liệu trước/sau và URL Tailscale Serve |

## Hỏi đáp

### Vòng 1 — Phạm vi & Kiến trúc cốt lõi (2026-11-21 00:12)

- **Câu hỏi đã nêu:** (1) Các mặt bao quanh (`A/B/C/D`, chọn nhiều được); (2) Mô hình biểu diễn trong TDQ (`A: work_kind`, `B: lane thứ 3`, `C: loai_request`); (3) Ranh giới nhóm Debug (`A: tách Debug-RCA vs Bugfix`, `B: chỉ thuần đọc`, `C: mọi debug`); (4) Bối cảnh triển khai & host (`A: production AGY + đa nền tảng Python/Rust`, `B: MVP skills/scripts`, `C: tự nhập`); (5) Bổ sung thêm (`A/B`).
- **Người dùng trả lời (nguyên văn):** `1abc 2a 3a 4a 5b tôi muốn với những task theo dạng phân tích resreach và debug thì sẽ đi rất sâu vào resreach và tổng hợp thông tin, có ghi log thường xuyên để tránh mất data khi compact nữa`

### Vòng 2 — Chi tiết triển khai, Chống mất dữ liệu khi Compact & Mức QC (2026-11-21 00:22)

- **Câu hỏi đã nêu:** (1) Quyền ghi hẹp `scoped-write` cho `tdq-explorer`/`tdq-debugger`/`tdq-reviewer` (`A` đồng bộ Python+Rust trong `artifacts/<slug>/` & `research/<slug>*.md` vs `B` giữ read-only); (2) Cơ chế chống mất dữ liệu khi `/compact` (`A` 2 lớp CLI `evidence-log.md` + nhắc checkpoint + `Compact recovery` vs `B` ghi tay); (3) Độ sâu Research & Fan-out `no-worktree` trong `implement` (`A` Deep Multi-Pass + `tdq_team.py` `no-worktree` vs `B` tuần tự); (4) Chuẩn QC phi-code (`A` bộ `QC-I1..I4` kèm Red-Team vs `B` bỏ Red-Team ở `full`); (5) Mức QC cho request này (`A: full`, `B: lite`, `C: ultra`); (6) Bổ sung (`A/B`).
- **Người dùng trả lời (nguyên văn):** `1a 2a 3a 4a 5a 6a`


### Vòng 3 — Chốt lại phạm vi thuần Phân tích & Báo cáo Đề xuất (2026-11-21 00:46)

- **Câu hỏi xác nhận:** Triển khai sửa mã nguồn luôn theo plan code (`1A`) hay đổi request này thành chỉ phân tích sâu, phản biện Red-Team và xuất báo cáo đề xuất thiết kế thuần `docs`, không sửa mã nguồn (`1B`).
- **Người dùng trả lời (nguyên văn):** `1b`
- **Cập nhật phạm vi:** Đổi nhánh sang `docs/toi-uu-research-phan-tich` (`loai_request=docs`); tuyệt đối không sửa mã nguồn thực thi (`scripts/`, `hooks/`, `skills/`, `agents/`, `tools/`, `plugins/`, `tests/`). Toàn bộ trọng tâm đi sâu nghiên cứu, đo đạc thực nghiệm, phân tích mã nguồn, phản biện Red-Team 3 góc nhìn, ghi checkpoint `evidence-log.md` chống mất dữ liệu khi `/compact` và tổng hợp Đề xuất Kiến trúc Hoàn chỉnh V2 được đặt trọn vẹn vào pha `implement`, tiếp nối bằng `qc` kiểm chứng bằng chứng (`FActScore` + chống lỗi F6 + Zero-Code-Touch) và `report` Markdown + Archify HTML.
