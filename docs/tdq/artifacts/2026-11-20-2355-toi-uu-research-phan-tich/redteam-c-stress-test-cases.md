# Red-Team C — Walkthrough End-to-End & Stress-Test V1 trên `4` Ca Lịch sử Thật

Ngày: 2026-11-21 · Task: `T3.3` · Request: `2026-11-20-2355-toi-uu-research-phan-tich`
Soul: chất lượng > runtime > context cost · luật gốc: `skills/tdq-conventions/references/soul.md`
Đối tượng kiểm định: `docs/tdq/artifacts/2026-11-20-2355-toi-uu-research-phan-tich/de-xuat-kien-truc-v1.md` (`M1`–`M6`)

---

## 1. Tổng quan `4` Ca Thử nghiệm & Kết quả Stress-Test

Phân tích mô phỏng từng pha (`intake → analyze → spec → plan → implement → qc → report`) bằng cách đối chiếu trực tiếp hồ sơ lịch sử trong `docs/tdq/` với các ràng buộc thực thi đang tồn tại trong `scripts/tdq_state.py`, `scripts/tdq_team.py`, `scripts/doc_lint.py`, `hooks/scripts/{edit_gate,bash_gate}.py`, `hooks/rust/tdq-dispatch/src/` và `skills/*/references/*.md`.

| Ca | Request Slug (`idx`, `lane`) | Hiện trạng Trước (`Pre-Impl` vs `Impl`, Docs tiền-impl, Archify, QC) | Kết quả dưới V1 (Mức giảm đạt được) | Điểm gãy / Ma sát mới phát hiện (`ND-C*`) |
|---|---|---|---|---|
| **Ca 1** (Research/Analysis `full`) | `2026-11-20-1056-phan-tich-nang-cap-agent` (`idx=172`, `full`) | `Pre-Impl` `2,498s` (**`49.9%`**) vs `Impl` `483s` (`9.6%`); `515L / 67.9 KB` (`brief+research+spec+plan`); `2×` Archify (`2.88 MB + 2.87 MB`); `QC-F1` chạy `4,525` tests (`1,227.94s`) dù `0` code sửa. | Chuyển `4` subagent audit + research (`113L`) sang `implement`; cắt `QC-F1` (`-1,228s`), cắt `§2b` giả & Mini-Spec code (`~45–55%` tiền-impl). | **`ND-C2`**, **`ND-C3`**, **`ND-C6`**: `_archify_gate` vẫn ép render preview ở `spec`; `doc_lint R10` vẫn đòi `§2b`; `R14` chặn ngưỡng số chưa đo ở `§6`; vẫn dừng `3` cổng (`spec`, `plan`, `mode`). |
| **Ca 2** (Research/Audit `quick`) | `2026-11-19-1457-audit-sai-sot-noi-hook` (`idx=167`, `quick`) | `analyze` `2,413s` (**`99.7%`**) vs `Impl` `0s` (`0.0%`); `74L / 8.2 KB` (`brief+plan`, `QC.1` dùng `assert True`); `2×` Archify (`2.02 MB + 2.02 MB`, HTML cùng đúng `1,241,473B`). | Triage nhẹ đưa toàn bộ audit Python↔Rust sang `implement`; sửa bug `_cli_approve` hết `0s` giả; `doc_lint` bắt chết `assert True`. | **`ND-C2`**, **`ND-C3`**, **`ND-C5`**: `archify-quick.md` + `_archify_gate` vẫn ép Double Archify ở `quick`; trần `<= 40` dòng `quick-lane-mini.md` nghẹt khi thêm `Work kind`/`Sinh ra:`/`QC-I`; `SHELL_MUTATOR` chặn trích đoạn code trong `evidence add`. |
| **Ca 3** (Debug/Scan `full` + RCA) | `2026-11-18-1346-scan-hook-anh-huong-runtime` (`idx=164`, `full`) · đối chứng `2026-11-08-1141` (`idx=155`, `full`) | `1346`: `Pre-Impl` `2,640s` (`16.4%`, `444L / 40.3 KB`) vs `Impl` `1,919s` (`11.9%`); tạo `7` script `.py` (`2,738L`) + `8` JSON (`278.5 KB`) ở `docs/tdq/bench/`; `QC-F1` chạy `4,315` tests (`1,283s`); `report` `10,240s`. `1141`: `Pre-Impl` `578s` (`47.0%`) vs `Impl` `18s` (`1.5%`), sót tick `[~]`/`[ ]`. | `1141` chuyển RCA sang `tdq-debugger` (`CAR` + counterfactual); `1346` tránh viết `scratch/` ngay trong `analyze`; `no_worktree` tránh `7` commit branch rỗng. | **`ND-C4`**, **`ND-C5`**, **`ND-C6`**: V1 cấm `.py` và cấm `docs/tdq/bench/` khỏi `scoped-write`/`no_worktree`; chạm `.py` ở `docs/tdq/bench/` kích hoạt lại `R15-Full` & **`QC-F1` (`4,315` tests)**; `evidence.jsonl` song song ở `no_worktree` gây race ghi file. |
| **Ca 4** (Bugfix sửa code `build`) | `2026-11-16-1953-fix-lsp-gate-mcp-routing` (`idx=161`, `full`) | `Pre-Impl` `7,482s` (`28.9%` — `569L / 72.9 KB` + `1.03 MB` preview) + chờ `mode` `5,574s` (`21.6%`) vs `Impl` `5,836s` (`22.6%`) + `QC ultra` `5,187s` (`2` vòng). RCA chạm `6+1` file (`search_replay.py` lòi ra ở `QC` vòng 1). | Triage nhẹ giảm thời gian kẹt ở `analyze` khi lỗi còn mờ; đẩy Deep RCA + Red Repro sang `P1.1` đầu `implement`. | **`ND-C1` (Nghiêm trọng nhất)**: **Nghịch lý Bugfix** — đẩy RCA sang `P1.1` trong `implement` làm `spec §2b/§3c/§6`, `spec-preview`, `plan R15-Full` (`Chạm:`, `Neo`, `Logic`, `Ownership Map`) và `tdq_team.py assign` không thể lập hợp lệ trước khi biết root cause; sửa sau `P1.1` làm lệch `sha256` và nổ lại cổng duyệt. |

---

## 2. Walkthrough Chi tiết từng Ca

### Ca 1 — Research/Analysis `full`: `2026-11-20-1056-phan-tich-nang-cap-agent`

#### (a) Trước (Thực tế ghi nhận) vs Mô phỏng dưới V1
- **Trước (`timing.jsonl` `idx=172`, non-idle `5,010.0s`):**
  1. `analyze` (`910s`, `18.2%`): Ngay trước khi viết `spec`, leader đã fan-out `4` subagent kiểm toán đủ `6` tệp `agents/tdq-*.md`, `tools/patches/skills_and_agents.py`, `scripts/tdq_team.py`, `hooks/scripts/*`, `hooks/rust/tdq-dispatch/`, chạy `tavily-primary` (`2/6`) + `search_web` + đối chiếu `ECC v2.2.3`, ghi `docs/tdq/research/2026-11-20-1056-phan-tich-nang-cap-agent.md` (`113L / 13,300B`) và chốt sạch **`14` hạn chế kèm `file:line`** ngay trong `docs/tdq/brief/2026-11-20-1056-phan-tich-nang-cap-agent.md:44-68` (`105L / 16,512B`).
  2. `spec` (`1,033s`, `20.6%`): Viết `183L / 23,560B` để lặp lại bảng `4` trụ cột, tự dựng `§2b Ranh giới module` giả tạo (`M1-report-md`, `M2-archify-html`, `M3-qc-verify` chỉ cho `1` bài báo cáo, `L52-56`), và phải render `spec-preview.html` (`1,610,204B` + `1,235,590B` manifest + `32,076B` JSONs = `2.88 MB`) từ `truoc-sau.archify.md` (`57L`).
  3. `plan` (`555s`, `11.1%`): Viết `114L / 14,543B` bọc `3` task tuần tự (`T1.1`, `T2.1`, `T3.1`) với đủ Per-Task Mini-Spec (`Req`, `EARS`, `Logic cốt lõi`, `Ca góc hiểm & Assert`), chạy `tdq_bench.py simulate`.
  4. `implement` (`483s`, `9.6%`): Chỉ còn biên tập lại `14` phát hiện sẵn có sang `reports/2026-11-20-1056-phan-tich-nang-cap-agent.md` (`265L / 44,904B`) và render Archify HTML **lần thứ hai** (`1,599,032B` + `1,235,596B` manifest = `2.87 MB`).
  5. `qc` (`1,191s`, `23.8%`): Dù `0` tệp code bị sửa (`Q5_OK: 0 paths outside docs/`), `QC-F1` vẫn ép chạy `tdq_test.py tron-bo` **`4,525` tests trong `1,227.94s`** (`docs/tdq/qc/2026-11-20-1056-phan-tich-nang-cap-agent.md:13,58`).
  6. `report` (`838s`, `16.7%`): Chốt báo cáo và trình merge.
- **Dưới V1 (`work_kind=investigate`, `lane=full`):**
  1. `intake` + `analyze`: Chạy `tdq_state.py init ... full --kind investigate --bo-qua-lsp "..."`. Chỉ đọc bề mặt `agents/` + entry points (`1–2` lượt), lập `2–4` giả thuyết (H1: agent mồ côi; H2: lệch `skills_and_agents.py`; H3: lỗ hổng `READONLY`/`SubagentStop`; H4: lệch `handoff-schema.json`) và phỏng vấn `4` câu scope (`1a 2abc 3... 4a 5a`). **Cấm** fan-out `4` subagent và cấm chạy research ngoài trong `analyze`.
  2. `spec` + `plan`: Viết `spec` câu hỏi nghiên cứu + ma trận giả thuyết + `§6` tiêu chí bằng chứng (`QC-I1..I4`), bỏ `§2b` module code và bỏ `Log service`; `plan` dùng `R15` bản nhẹ (không ép `Ownership Map` / `EARS` code), chia nhánh qua Breakeven Gate (`4` nhánh audit độc lập thuộc Effort Tier `Deep`), đánh dấu `no_worktree`.
  3. `implement`: Pha **Collect** fan-out `4` `tdq-explorer` song song (`Workspace="inherit"`, `no_worktree`) trên `agents/`, `tools/patches/`, `scripts/tdq_team.py`, `hooks/` và `1` nhánh research ngoài → đổ raw findings vào `docs/tdq/artifacts/<slug>/<task>.md` + `evidence-log`, nhắc `[TDQ:CHECKPOINT]` sau mỗi `12` lượt đọc; pha **Write** tổng hợp báo cáo đối chiếu `[EV-xxx]`.
  4. `qc`: Chạy `QC-I1` (0 LLM kiểm `EV-xxx` + `path:line` tồn tại, `< 2s`), `QC-I2` (`tdq-reviewer`/`tdq-qc-tester` đối chiếu claim ↔ snippet), `QC-I3` (counterfactual), `QC-I4` (gắn nhãn tin cậy). Bỏ hoàn toàn `4,525` tests của `QC-F1`.

#### (b) Giảm tải đo được
- **Thời gian tiền-implement:** Giảm từ `2,498s` (`49.9%` non-idle: `analyze 910s + spec 1,033s + plan 555s`) xuống mức scoping nhẹ (~`400–600s` dự phóng, ~`10–15%`); toàn bộ ~`1,000–1,400s` kiểm toán `4` nhánh + research ngoài chuyển đúng về `implement` (nâng `implement` từ `9.6%` lên thành trọng tâm thực thi).
- **Dung lượng tài liệu tiền-implement:** Loại bỏ `113L / 13.3 KB` `research.md` tiền-impl, loại `§2b` module giả (`9L`) và Mini-Spec code trong `plan` (`~40–60L`), giảm tài liệu tiền-impl từ **`515L / 67.9 KB` xuống ~`220–270L`** (`~45–55%`).
- **Chi phí QC vô ích:** Tiết kiệm trọn **`1,227.94s` (~`20.5` phút)** chạy `4,525` unit tests (`QC-F1`).

#### (c) Điểm gãy / Ma sát khi áp V1 trên Ca 1
1. **Ép render Archify Preview vô nghĩa tại `spec` (`ND-C2`):** V1 không chỉnh `scripts/tdq_state.py:2254-2308` (`_archify_gate`). Vì `lane == "full"`, `approve spec` **từ chối exit 1** nếu thiếu `docs/tdq/spec/<slug>-preview.manifest.json`. Ở V1, tác tử chưa audit `14` hạn chế lúc ở `spec`, nên không có sự thật để vẽ `truoc-sau.archify.md` (`archify-ba.md:15` đòi *"from code you read"*). Giữ gate này buộc agent bịa sơ đồ preview `1.61 MB` rồi render lại `1.60 MB` ở `report` (giữ nguyên lãng phí `2.88 MB` Double Archify), hoặc phải xin user `--bo-qua-archify`.
2. **Đụng trần `doc_lint` `rule_r10` và `r14_loi` (`ND-C3`):** V1 M5 (`L102`) bỏ `§2b` giả tạo ở `spec`, nhưng V1 M2 quên sửa `scripts/doc_lint.py:441-458` (`rule_r10`), vốn vẫn báo lỗi **`[R10] lane-full spec is missing the section ## 2b. Ranh giới module`**. Đồng thời `r14_loi` (`doc_lint.py:1144`, gọi bởi `approve spec` ở `tdq_state.py:2225`) phạt mọi ngưỡng số trong `§6` (như `>= 10` hạn chế, `<= 15 calls/nhánh`, `>= 20 EV-xxx`) nếu `Đo trước` chưa có số — dù chưa thu thập!
3. **Vẫn dừng `3` lần duyệt trên một request thuần nghiên cứu (`ND-C2`):** `approve spec` → `approve plan` → `phase="mode"` (`tdq_state.py:2422` khi user chỉ nhắn `"duyệt plan"`). `liet_ke_modes` vẫn liệt kê cả `codex` (vốn thiết kế cho TDD code ở `tdq_state.py:1674`), gây thêm `1` lượt hỏi không cần thiết.
4. **Hở pha `report` (`ND-C6`):** Pha `implement (Write)` tạo `reports/<slug>.md` (`265L / 44.9 KB`), rồi pha `report` (`838s`) lại rà lại và đóng gói `4` phần + Archify, dễ gây viết trùng nếu không quy định ranh giới tạo draft report trong `implement`.

---

### Ca 2 — Research/Audit `quick`: `2026-11-19-1457-audit-sai-sot-noi-hook`

#### (a) Trước (Thực tế ghi nhận) vs Mô phỏng dưới V1
- **Trước (`timing.jsonl` `idx=167`, non-idle `2,421.0s`):**
  1. `analyze` (`quick_analyze`, `2,413s`, **`99.7%`**): Ngay trong `brief/2026-11-19-1457-audit-sai-sot-noi-hook.md` (`36L / 3,477B`), agent đã khám nghiệm xong `transcript.jsonl` (`step 1779–2340`) của `2026-11-19-0046`, xác định xong `Nguyên nhân gốc rễ 1` (`agy_hooks.py` mềm hóa gate) và `Nguyên nhân gốc rễ 2` (`tdq-dispatch` thiếu gate) (`brief:21-33`).
  2. `plan` (`38L / 4,764B`): Đặt `T1..T3` hợp thức hóa việc viết `reports/2026-11-19-1457.md` (`155L / 29,667B`), dính lỗi **`ANTI-2` tại dòng 27** (`QC.1 ... py -3 -c "assert True"`), và bắt buộc render **`plan/<slug>-flow.html`** (`1,241,473B` + `736,013B` manifest + `42,289B` JSONs = **`2.02 MB`**) theo `archify-quick.md` trước khi chạy `approve quick`.
  3. `implement` (**`0.0s`, `0.0%`**): Do `tdq_state.py:2417` thiếu `ghi_moc_phase(state, "implement")` nên toàn bộ việc viết `155L` báo cáo + render Archify **lần thứ hai** (`reports/<slug>.html` cũng nặng đúng **`1,241,473B`**, y hệt bản `plan-flow.html` từ cùng `1` file `truoc-sau.archify.md` `44L`) bị cộng hết vào `analyze`, rồi nhảy thẳng `report` (`8s`).
- **Dưới V1 (`work_kind=investigate`, `lane=quick`):**
  1. `quick_analyze`: Chỉ kiểm bề mặt xác nhận `3` ô `[ ]` sót trong `2026-11-19-0046` + định vị `edit_gate.py`/`pre_tool_use.rs`, nêu `3` giả thuyết (`H1` mềm hóa Python, `H2` thiếu gate Rust, `H3` lệch schema JSON), chưa đọc `transcript.jsonl` `step 1779–2340`.
  2. `mini-plan` (`plan/<slug>.md`): Chia `T1` (soi transcript + ma trận Python↔Rust → `artifacts/<slug>/evidence-log.md`), `T2` (viết báo cáo 10 hạn chế), `QC` (`QC-I1` kiểm `EV-xxx` + `path:line` + `doc_lint`). `doc_lint` dưới V1 bắt lỗi `assert True` ngay tại cổng `approve quick` (`_r15_gate_approve`).
  3. `approve quick` (đã vá `ghi_moc_phase` ở V1 M1): Chuyển sang `phase=implement` và bắt đầu ghi giờ thật cho `implement`. Nếu qua Breakeven Gate, có thể gọi `2–3` `tdq-explorer` (`no_worktree`) chạy song song soi Python vs Rust vs transcript.

#### (b) Giảm tải đo được
- **Cân bằng pha:** `analyze` giảm từ **`2,413s` (`99.7%`)** xuống ~`150–250s` scoping, chuyển toàn bộ `~2,150s+` điều tra ma trận `12` cổng + transcript `560` bước về đúng pha `implement` và đo đúng thời lượng trong `timing.jsonl` nhờ vá `_cli_approve`.
- **Chất lượng kiểm chứng:** Loại bỏ hoàn toàn bẫy `ANTI-2` (`assert True`) bằng cổng `R15` + `QC-I1/I2`.

#### (c) Điểm gãy / Ma sát khi áp V1 trên Ca 2
1. **Double Archify `quick` vẫn nguyên vẹn (`ND-C2`):** `skills/tdq-intake/references/archify-quick.md:17-18` và `scripts/tdq_state.py:2272-2308` (`_archify_gate`) vẫn bắt buộc `plan/<slug>-flow.manifest.json` đạt `current` lúc `approve quick` — ép dựng `2.02 MB` `plan-flow.html` khi `implement` chưa điều tra ra 10 hạn chế, rồi dựng lại đúng `1,241,473B` HTML đó ở `report`! V1 hoàn toàn chưa đụng tới `archify-quick.md`.
2. **Nghẹt trần `<= 40` dòng của `quick-lane-mini.md` (`ND-C3`):** File `plan/2026-11-19-1457.md` đã dài **`38/40` dòng** dù thiếu `Work kind: investigate` (V1 M2 cần để bật `_is_investigate_doc`), thiếu `Effort Tier` / `Breakeven` (V1 M5 `L103`), thiếu `Sinh ra:`/`Tiêu chí:` (`R15`), và dồn QC vào `1` dòng. Ngoại lệ `<= 80` dòng tại `quick-lane-mini.md:29` chỉ mở cho **code** `R15-Compact`, **không mở cho `investigate`** — khiến `quick` + `investigate` dễ chạm ngưỡng `> 40` dòng và bị đẩy oan lên `full`!
3. **Vướng `quick-lane.md` + `SHELL_MUTATOR` khi kiểm chứng hook (`ND-C5`):**
   - `skills/tdq-intake/references/quick-lane.md:89-96` vẫn cứng nhắc: `>= 3` task không giao nhau thì giao `tdq-implementer` kèm **worktree**, không có đường định tuyến sang `tdq-explorer` (`no_worktree`).
   - Quan trọng hơn: Trong Ca 2, các trích đoạn lỗi của `bash_gate.py`/`command_parser.rs` chứa chính chuỗi `write_text`, `Set-Content`, `git commit`. Khi worker `explorer` gọi `py -3 scripts/tdq_team.py evidence add --excerpt "... write_text(...) ..."` qua `run_command` (V1 M5 `L105`), `bash_gate.py:241` và `command_parser.rs:207` chạy `SHELL_MUTATOR` trên chuỗi **chưa mask ngoặc kép**, dẫn tới **chặn oan `[TDQ:READONLY]`** ngay lệnh ghi bằng chứng!

---

### Ca 3 — Debug/Scan `full`: `2026-11-18-1346-scan-hook-anh-huong-runtime` (+ Đối chứng RCA `2026-11-08-1141`)

#### (a) Trước (Thực tế ghi nhận) vs Mô phỏng dưới V1
- **Trước (`1346`, `timing.jsonl` `idx=164`, non-idle `16,082.0s`):**
  1. `analyze` (`578s`, `3.6%`): Đã viết sẵn `scratch/long_turns.py`, `model_latency.py`, quét `120` transcript (`11,159` calls, `17,193` tool steps, `117` lỗi API), `cProfile` `prompt_context.py` (`307.6 ms`), và ghi luôn **kết luận nguyên nhân** ngay trong `brief/2026-11-18-1346.md:49,91` (`111L`).
  2. `spec` (`577s`, `3.6%`, `217L`): Dùng `--bo-qua-archify` (chỉ vẽ 2 Mermaid) và mở bằng `--bo-qua-lsp`.
  3. `plan` (`1,485s`, `9.2%`, `116L`): Thiết kế `7` task tạo **`7` script `.py` (`2,738L / 127.7 KB`) + `8` tệp JSON (`4,119L / 150.8 KB`)** trong `docs/tdq/bench/2026-11-18-1346-hook-runtime/`, bị `doc_lint` báo **`4` lỗi `[R15]`** ở QC vòng 1 vì `Chạm:` chứa `.py` (`qc/2026-11-18-1346.md:40`).
  4. `implement` (`1,919s`, `11.9%`): `tdq_team.py` giữ `T1.1` và `Tx.2` (`vung-khoa` vì ghi thư mục/trống `Chạm:`), giao `5` task còn lại qua **Git worktrees**, tạo `7` commit nhánh (`0ac756f7..da6944bf`) chỉ để ghi file JSON/MD/bench!
  5. `qc` (`1,283s`, `8.0%`): Dù `muc_qc=lite` và `0` dòng mã sản phẩm bị sửa, `QC-F1` vẫn chạy `tdq_test.py vung-cham` fallback ra **`207` modules / `4,315` pass (`35` skip)**!
  6. `report` (`10,240s`, `63.7%`): Xuất `reports/*.md` (`49L`) + `reports/*.html` (`508,105B`).
- **Đối chứng Pure Debug-RCA `2026-11-08-1141-dieu-tra-gate-chua-duyet-tu-dong-edit` (`idx=155`, non-idle `1,231.0s`):**
  - `analyze` (`273s`) + `spec` (`221s`) + `plan` (`84s`) = **`578s` (`47.0%`)**, đã bóc xong toàn bộ `5` mốc vi phạm từ log `play3clone` và `edit_gate.py:135-145`. `implement` chỉ còn **`18s` (`1.5%`)**, thậm chí bỏ sót tick `T2.1` (`[~]`) và `Q1–Q4` (`[ ]`) trong `plan/2026-11-08-1141.md:40,59-62`, và `T1.2` khai nhầm `Chạm: hooks/scripts/edit_gate.py, _common.py` trên một request chỉ đọc! `report` ngốn `632s` (`51.3%`).
- **Dưới V1 (`work_kind=investigate`):**
  - Với `1141` (pure RCA): Giữ `analyze` là check log tối thiểu, chuyển điều tra `play3clone` sang `tdq-debugger` trong `implement` (bắt buộc tách `Manifestation Step` dòng `6911` `Edit server/index.js` khỏi `Point-of-Commitment Step` dòng `6856` tự `approve` & `edit_gate.py:135-145` dùng `remind` thay `block`, kèm counterfactual test), không khai nhầm `Chạm:` vào `hooks/scripts/`, và chạy `QC-I` kiểm DoD.
  - Với `1346` (benchmark/scan): Cấm viết `scratch/*.py` và đo toàn bộ `120` transcript ngay trong `analyze`; giữ `T1.1` đo bench thực nghiệm nằm gọn trong `implement`.

#### (b) Giảm tải đo được
- **Với `1346`:** Nếu không vướng bẫy đuôi `.py` (xem mục c bên dưới), cắt bỏ **`1,283s` (`21` phút)** chạy `4,315` tests ở `QC-F1`, tránh chuyển `2` lượt viết script (`scratch/` ở `analyze` rồi chép lại ở `T1.1` của `implement`), và loại bỏ `5` Git worktree + `7` branch commits thừa.
- **Với `1141`:** Rút tiền-implement từ `578s` (`47.0%`) xuống scoping nhẹ (~`120s`), đưa `implement` từ `18s` (`1.5%`) lên làm pha RCA chính, chống sót tick DoD bằng `QC-I1`.

#### (c) Điểm gãy / Ma sát nghiêm trọng khi áp V1 trên Ca 3 (`1346`)
1. **V1 làm sập hoàn toàn quy trình điều tra viết script đo `.py` / `docs/tdq/bench/` (`ND-C4`):**
   - Look at `1346`: Toàn bộ giá trị của ca này đến từ `7` script đo `.py` (`2,738L`) đặt trong `docs/tdq/bench/2026-11-18-1346-hook-runtime/`. (Kho lịch sử còn `4` ca tương tự như `doc_dup.py`, `dem_da_nen_tang.py`, `test_bao_cao_gitflow.py`, `test_report_kien_truc_ecc.py`).
   - V1 thiết kế đóng cứng theo `3` lớp trùng nhau:
     - **M3 (`L72-75`):** `is_investigation_artifact_target` chỉ cấp `scoped-write` cho đuôi `{".md", ".json", ".jsonl"}` trong `docs/tdq/artifacts/<slug>/` hoặc `docs/tdq/research/` → **`tdq-explorer`/`tdq-debugger` bị chặn `[TDQ:READONLY]` khi tạo `.py` đo đạc hoặc ghi vào `docs/tdq/bench/`**.
     - **M2 (`L48, 63`):** `is_artifact_only_paths` trả `False` cho `docs/tdq/bench/` và `.py` → ép mở worktree cho task bench; `doc_lint.py` bật lại `R15-Full` khi thấy `.py` trong `Chạm:` (lặp lại y nguyên `4` lỗi `[R15]` ở `qc/2026-11-18-1346.md:40`).
     - **M5 (`L116`):** Chốt fail-safe *"Nếu `git diff --name-only` phát hiện bất kỳ thay đổi tệp mã nguồn (`EXT_MA_NGUON`), `qc` BẮT BUỘC tự động bật lại `QC-F1` + `QC-F4`"* không loại trừ `docs/tdq/`! Vậy chỉ cần viết `1` script đo `.py` tạm dưới `docs/tdq/artifacts/` hoặc `docs/tdq/bench/`, **V1 tự động kích nổ lại `QC-F1` chạy `4,315`–`4,525` tests (`1,283s`)**!
2. **Xung đột ghi song song `evidence.jsonl` / `evidence-log.md` ở chế độ `no_worktree` (`ND-C5`):** Khi `4` worker (`T1.2`, `T1.3`, `T1.4` + shard bổ sung) cùng chạy `Workspace="inherit"` trên 1 thư mục làm việc của Windows và cùng gọi `tdq_team.py evidence add` (V1 M5 `L105`), nhiều tiến trình đồng thời nối dòng vào `evidence.jsonl` và `evidence-log.md` dễ gây race condition/lỗi lock file trên Windows và trái luật V1 M2 (`L51`: cấm 2 task cùng đợt ghi chung 1 file).

---

### Ca 4 — Bugfix có sửa code (`work_kind=build`): `2026-11-16-1953-fix-lsp-gate-mcp-routing`

#### (a) Trước (Thực tế ghi nhận) vs Mô phỏng dưới V1
- **Trước (`timing.jsonl` `idx=161`, non-idle `25,844.0s`):**
  1. `analyze` (`1,140s`, `4.4%`): Nhận ảnh chụp lỗi `[TDQ:LSP] start_lsp without language_id` trên `chrome-devtools -> select_page`. Để trả lời được câu hỏi phạm vi `"fix triệt để"`, agent đã tự làm RCA toàn diện ngay trong `analyze`: truy vết qua **6 nhóm file** (`lsp_gate.py`, `_common.py`, `search_observe.py`, `search_rules.py`, `tools/patches/{agy_hooks,cli_fixes_a}.py`, `tests/`), chạy phỏng vấn 5 câu (`1a 2a 3b 4c 5a`).
  2. `spec` (`1,208s`, `4.7%`, `196L / 25.7 KB` + `1.03 MB` `spec-preview`): Khai đủ `5` module `§2b` (`M1`–`M5`), từng hàm và chữ ký trong `§3c`, đo trước latency `66.4–72.2 ms` cho `§6 Q3`.
  3. `plan` (`5,134s`, `19.9%`, `309L / 40.1 KB`): Lập `11` task `T1.1`–`T5.2` theo chuẩn `R15-Full` với số dòng neo chính xác (`"dòng 894"`, `"dòng 1154–1186"`, `"dòng 129–163"`), `Ownership Map`, `Cụm song song`, và `tdq_bench.py simulate`.
  4. `mode` (`5,574s`, `21.6%`): Dừng chờ user chọn `subagent`.
  5. `implement` (`5,836s`, `22.6%`) + `qc` (`5,187s`, `20.1%`): `tdq_team.py assign` khóa `vung_file` cho `11` task (chỉ `3` task `giao`, `8` task `tu_lam` vì `file-luat`/`mcp`/`vung-khoa`); `tdq-qc-tester` vòng 1 (`ultra`) phát hiện thêm `scripts/search_replay.py:183` cũng dính `"lsp" in name.lower()` + `main()` vượt 35 dòng + leak `_RUNTIME_STATE`, mở `QC1.1`–`QC1.4` sửa và pass vòng 2 (`4,246` tests, `948.55s`).
  6. `report` (`1,765s`, `6.8%`): Xuất `53L / 11.0 KB` + `1.41 MB` Archify bundle.
- **Dưới V1 (`work_kind=build`, `issue-triage.md` cập nhật ở M5 `L108-109`):**
  - Giả sử agent làm đúng khuyến nghị mới của V1: giữ triage nhẹ ở `analyze` (xem ảnh báo lỗi, tái hiện `select_page` qua `lsp_gate.py`, ghi 2–4 giả thuyết: `H1` chỉ rẽ nhánh sai ở `lsp_gate.py`; `H2` lỗi unwrap lặp ở `_common.py` + `search_rules.py` + `tools/patches/`; `H3` lỗi lan sang telemetry `search_observe.py` & `search_replay.py`), rồi **đẩy `P1.1 Deep RCA + Red Regression Test` vào đầu `implement`**.

#### (b) Giảm tải lý thuyết nếu không bị nghẽn
- Về mặt ý tưởng, nếu `analyze` không phải cày hết 6 file để chốt sâu từng dòng neo trước khi người dùng chọn hướng, `analyze` có thể nhẹ hơn (`1,140s → ~300–400s`) và giảm rủi ro tốn 1 giờ phân tích sai hướng trước khi user chốt scope.
- Thực tế trên Ca 4, tổng thời gian tiền-implement (`7,482s`) có phần lớn nằm ở **`plan` (`5,134s` = `68.6%` tiền-impl!)** để viết `309L` `R15-Full` + `5,574s` chờ `mode`, chứ không chỉ nằm ở `analyze` (`1,140s`).

#### (c) Điểm gãy chí mạng: "Nghịch lý Bugfix" (`ND-C1`)
Khi thử áp V1 (`P1.1 Deep RCA` trong `implement` của `work_kind=build`) lên đúng Ca 4 (`1953`), toàn bộ hệ thống kiểm soát chất lượng hiện hành của TDQ **đánh nhau trực diện và bế tắc ở `4` chốt liên hoàn**:
1. **Bế tắc tại Interview (`analyze` bước 4):** Người dùng hỏi `"fix triệt để"` (`1a`: sửa cả `search_rules.py` + `tools/patches/` vs chỉ vá `lsp_gate.py`?). Nếu chưa mở `_common.py`, `search_rules.py`, `search_observe.py`, `tools/patches/` để RCA, tác tử **không biết có bản sao thứ 2 và thứ 3 đang lệch nhau** nên không thể đặt đúng câu hỏi lựa chọn `1a` và `2a` (`Arguments: {}`)!
2. **Bế tắc tại `spec` (`R10`, `R14`, `_archify_gate`, `spec_sha256`):**
   - Ca 4 thuộc `work_kind=build`, nên `spec` vẫn phải tuân thủ `doc_lint R10` (`§2b Ranh giới module`), `R14` (`§6 Đo trước` + `Dự phòng`), `§3c Giải thuật`, và `_archify_gate` (`tdq_state.py:2254`) ép render `spec-preview.html` Trước/Sau trước `approve spec`!
   - Trước khi `P1.1` chạy xong, tác tử chưa biết `M1..M5` chạm file nào hay giải thuật `chuan_hoa_cong_cu_mcp` có cần tách sang `scripts/search_rules.py` không. Ghi lấp liếm `"TBD"` vi phạm `BANNED_PLACEHOLDERS`; đoán đại vào `§2b`/`§2c` thì sau khi `P1.1` hoàn tất, cập nhật lại `spec` làm thay đổi `spec_sha256` và làm `spec-preview.manifest.json` thành `stale` → **nổ lại cổng `approve spec` giữa pha `implement`** (`qc.md:119-121`)!
3. **Bế tắc tại `plan` (`doc_lint R15-Full` + `_r15_gate_approve` + `tdq_team.py assign`):**
   - `tdq_state.py:2500` chạy `doc_lint.r15_loi` **chặn `approve plan` (exit 1)** nếu các task sửa code (`T1.2..T4.1`) thiếu bất kỳ trường nào trong `8` trường `R15-Full` (`Req`, `GIỮ NGUYÊN`, `Chạm:`, `Neo & Công cụ:`, `Trước → Sau:`, `EARS`, `Logic cốt lõi`, `Ca góc hiểm & Assert`) hoặc thiếu `Ownership Map` (`doc_lint.py:918`)!
   - Nhưng trước `P1.1` trong `implement`, không ai có thể điền `Vị trí neo:` (`dòng 894`, `dòng 1154–1186`), `Logic cốt lõi` hay `Chạm:` chính xác cho `T1.2..T4.1`!
   - Hơn nữa, `IMPLEMENT_SUBAGENT_ROW` (`tdq_state.py:1553`) bắt chạy `tdq_team.py assign` ở Step 0 trên **toàn bộ plan** để khóa `vung_file` vào `docs/tdq/team/<slug>.json`. Sau khi `P1.1` tìm ra nguyên nhân thật nằm ở `scripts/search_rules.py` + `scripts/search_replay.py` (ngoài giả thuyết `lsp_gate.py` ban đầu), việc sửa `plan` và chạm file ngoài `vung_file` khiến `edit_gate.py:210` (`canh_bao_lach_luat`) báo `TDQ:TEAM` / `ban-do-hong` và làm trượt `plan_sha256`!
4. **Kết luận trên Ca 4:** V1 đã sửa `issue-triage.md` trên giấy nhưng chưa gỡ/đổi cơ chế khóa cứng `R10`/`R14`/`R15-Full`/`_archify_gate`/`tdq_team.py assign` cho các bugfix chưa rõ root cause. Với bugfix phức tạp như Ca 4 (`1953`), `issue-triage.md:21-22` bản cũ (*"Settle the evidence before writing the spec"*) thực ra phản ánh đúng bản chất phụ thuộc nhân quả — muốn chuyển RCA sang `implement` mà không vỡ pipeline thì **bắt buộc phải tách pha RCA thành 1 chặng/micro-request `investigate` trước khi đóng băng `spec`/`plan` `build`**, hoặc thiết kế **Two-Stage Plan Unlock** tường minh.

---

## 3. Tổng hợp Mã Nhược điểm (`ND-C1`..`ND-C6`) & Phương án Vá cho V2

| Mã | Mức độ | Ca lộ lỗi | Mô tả ngắn điểm gãy của V1 | Vá cụ thể bắt buộc cho V2 |
|---|---|---|---|---|
| **`ND-C1`** | **Cao** | Ca 4 (`1953`) | **Nghịch lý Bugfix (`issue-triage.md` vs `R10`/`R14`/`R15-Full`/`assign`/`_archify_gate`):** Cho phép hoãn Deep RCA sang `P1.1` đầu `implement` của request `build`, nhưng giữ nguyên yêu cầu khóa trước `§2b`, `spec-preview`, `8` trường `R15-Full` (`Chạm:`, `Neo:`, `Logic:`) và `tdq_team.py assign` cho các task `T1.2+` trước khi `P1.1` chạy. | Áp dụng **Two-Stage Bugfix Routing** tại `issue-triage.md`: (a) nếu RCA đã rõ ở triage (`<= 2` file, repro trực tiếp chỉ đúng symbol) → đi `build` thẳng; (b) nếu RCA chưa rõ / đa nghi vấn (`> 2` lớp như `1953`) → **chạy micro-spike `work_kind=investigate` trước** (hoặc dùng nhánh `plan` 2-đợt: đợt 1 chỉ khóa `P1.1 RCA + Red Repro` không ép `R15-Full` cho `T2+`, sau khi `P1.1` chốt mới hoàn thiện `T2+` và chạy lại `tdq_team.py assign`). |
| **`ND-C2`** | **Cao** | Ca 1 (`1056`), Ca 2 (`1457`) | **Sót `_archify_gate` (`tdq_state.py:2254`), `archify-quick.md` & 3 điểm dừng duyệt:** V1 quên miễn Archify preview cho `investigate` tại `approve spec` (`full`) và `approve quick` (`quick`), giữ nguyên lãng phí Double Archify (`2.88 MB` ở `1056`, `2.02 MB` ở `1457`) dù `implement` chưa thu thập xong sự thật; `approve plan` vẫn rơi vào `phase=mode` và liệt kê cả `codex`. | Miễn `_archify_gate` ở `spec` và `quick` khi `work_kind_hieu_luc(state) == "investigate"` (chỉ giữ bắt buộc **1 lần** render Archify HTML ở `report` trước `idle` qua `_chan_report_thieu`); cập nhật `archify-ba.md` & `archify-quick.md`. Với `investigate`, loại `codex` khỏi `liet_ke_modes` và gom câu chọn `main`/`subagent` theo Effort Tier vào bước chốt `plan` để giảm còn `1–2` điểm dừng. |
| **`ND-C3`** | **Cao** | Ca 1 (`1056`), Ca 2 (`1457`) | **Sót `doc_lint` (`rule_r10`, `r14_loi`) & trần `40` dòng `quick-lane-mini.md`:** V1 bỏ `§2b` giả nhưng quên mở `rule_r10` (`doc_lint.py:441`), làm `spec` `investigate` `full` fail `[R10]`; `r14_loi` (`L1144`) chặn các ngưỡng số điều tra (`>= 10`, `<= 15 calls`) chưa có `Đo trước`; trần `40` dòng ở `quick-lane-mini.md:29` chỉ nâng lên `80` cho *code*, làm nghẹt `investigate` `quick` (vốn đã `38/40` dòng ở `1457`). | Cập nhật `doc_lint.py`: với `_is_investigate_doc(doc)`, `rule_r10` chấp nhận `## 2b. Trục điều tra` / miễn khi đã có bảng câu hỏi & nhánh ở `§2`/`§3c`; `r14_loi` chấp nhận `Đo trước: 0 (thu thập ở implement)` kèm `Dự phòng`. Trong `quick-lane-mini.md` & `quick-lane.md`, nâng trần mini-plan cho `work_kind=investigate` lên `<= 65` dòng và hướng dẫn `tdq-explorer` (`no_worktree`). |
| **`ND-C4`** | **Cao** | Ca 3 (`1346`) | **Đụng độ quy trình với Script Đo `.py` & `docs/tdq/bench/`:** Ca điều tra thực nghiệm sinh `7` script `.py` (`2,738L`) ở `docs/tdq/bench/<slug>/` với `0` code sản phẩm đổi. V1 chỉ cho `{".md", ".json", ".jsonl"}` trong `artifacts/` & `research/`, khiến script đo trong `docs/tdq/` bị chặn `READONLY`, bị ép worktree, bị `R15-Full` và bị chốt fail-safe M5 (`L116`) **kích nổ lại `QC-F1` (`4,315`–`4,525` tests = `21` phút)**! | Tách **Mã sản phẩm** khỏi **Script chẩn đoán/bench** nằm trong `docs/tdq/{artifacts,bench}/<active_slug>/`: (a) `QC-F1` & `QC-F4` failsafe chỉ bật khi `git diff --name-only` chạm `EXT_MA_NGUON` **ngoài `docs/tdq/`** (script bench dùng `Q`-check tái chạy như Ca 3); (b) `doc_lint R15` giữ `R15-Compact` (không ép `R15-Full` / `Ownership Map`) cho script nằm dưới `docs/tdq/{artifacts,bench}/`; (c) mở `is_artifact_only_paths` cho `docs/tdq/bench/<slug>/` để dùng `no_worktree` cho file JSON/MD bench (giữ `scoped-write` của subagent read-only hoặc chỉ cho tạo `.py` bench qua leader/worktree kiểm soát). |
| **`ND-C5`** | **Trung bình-Cao** | Ca 2 (`1457`), Ca 3 (`1346`) | **Xung đột `SHELL_MUTATOR` khi gọi `evidence add` & Race Condition ghi song song `evidence.jsonl`:** `bash_gate.py:241` và `command_parser.rs:207` quét `SHELL_MUTATOR` trên chuỗi **chưa mask ngoặc kép**, nên lệnh `tdq_team.py evidence add --excerpt "... write_text / Set-Content ..."` của `explorer`/`debugger` bị chặn oan `[TDQ:READONLY]`. Đồng thời nhiều worker `no_worktree` cùng Wave 1 gọi `evidence add` ghi chung 1 file `evidence.jsonl` / `evidence-log.md` gây race condition trên Windows. | Đổi kiến trúc ghi kho bằng chứng sang **Shard + Leader Merge**: subagent chỉ ghi trực tiếp vào shard riêng `docs/tdq/artifacts/<slug>/<task_id>.md` (hoặc `<task_id>.ev.jsonl`) qua `write_file`/`edit_file` (`scoped-write`), **không** gọi `tdq_team.py evidence add` đồng thời từ worker; **Leader** hợp nhất tuần tự bằng `tdq_team.py evidence merge` cuối mỗi wave. Cập nhật `edit_gate.py:210` (`canh_bao_lach_luat`) miễn `[TDQ:TEAM]`/`[TDQ:TICK]` cho đường dẫn `scoped-write` hợp lệ. |
| **`ND-C6`** | **Trung bình** | Ca 1 (`1056`), Ca 3 (`1346`), `1141` | **Phình & lặp pha `report` (`838s` ở `1056`, `10,240s` ở `1346`, `632s` ở `1141`):** V1 chưa tách rõ sản phẩm `Write` cuối `implement` với pha `report`, dễ dẫn tới viết `research.md` (`187L`) / `synthesis.md` trong `implement` rồi viết lại `reports/<slug>.md` (`265L`) trong `report`. | Chuẩn hóa trong `investigate-mode.md`: Ở `investigate`, bước `Write` của `implement` xuất thẳng bản hoàn chỉnh vào `docs/tdq/reports/<slug>.md` (để `qc` `QC-I1..I4` thẩm định đúng bản báo cáo cuối cùng), và pha `report` chỉ bổ sung đúng khung `4` phần tóm tắt + `tdq_timing.py show` + render **1 lần** Archify HTML + kiểm Tailscale HTTP `200`. |

---

## 4. Kết luận Red-Team C

Áp dụng V1 giúp cắt rõ rệt **2 điểm lãng phí lớn nhất** ở các ca `investigate`: kéo nghiên cứu/điều tra ra khỏi `analyze` (`99.7% → ~10%` ở Ca 2; `49.9% → ~12%` ở Ca 1) và xóa bỏ `1,228s–1,283s` chạy `4,315–4,525` unit tests thừa ở `QC-F1`. Tuy nhiên, V1 **chưa chạy thông suốt trọn vòng** trên cả `4` ca thật nếu không vá `6` điểm gãy `ND-C1`–`ND-C6` cho V2 — trong đó `ND-C1` (nghịch lý bugfix `build`), `ND-C2` (cổng `_archify_gate` & `archify-quick.md` ép Double Archify), `ND-C3` (`doc_lint R10/R14` & trần `40` dòng `quick`), và `ND-C4` (đụng độ script đo `.py` / `docs/tdq/bench/`) là `4` chốt chặn kỹ thuật bắt buộc phải sửa đồng bộ ở V2 trước khi mở request triển khai mã nguồn.
