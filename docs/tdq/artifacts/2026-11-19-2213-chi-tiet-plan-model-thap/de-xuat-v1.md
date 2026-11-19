# Bản Đề xuất Thiết kế Kiến trúc 3 Lớp — Phiên bản V1 (End-to-End cho Model Tier Thấp)

Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

> **Mục tiêu thiết kế (`1a` + `2b` + `3a`):** Nâng cấp quy trình `tdq-workflow` để đạt chất lượng thực thi cao ngay cả khi **cả hai đầu** (**Weak Planner** viết plan lẫn **Weak Executor** viết code/test) chạy trên model tier thấp (`Flash`/`Haiku`/`Mini`/local nhỏ). Trọng tâm là thay văn xuôi mơ hồ và "Task Block Theater" bằng **Structural Contract + Phân rã cơ học + Công cụ tự trích sự thật + Cổng chặn cấu trúc R15**.

---

## 1. Tổng quan Kiến trúc 3 Lớp (V1)

| Lớp | Thành phần chạm (khi triển khai sau này) | Vai trò cho **Weak Planner** | Vai trò cho **Weak Executor** |
|---|---|---|---|
| **Lớp 1: Skill, Template & Agents** | `skills/tdq-plan/**`, `skills/tdq-spec/references/spec-template.md`, `skills/tdq-intake/references/quick-lane-mini.md`, `skills/tdq-build/SKILL.md`, `skills/tdq-build/references/team-mode.md`, `qc.md`, `agents/tdq-implementer.md`, `agents/tdq-reviewer.md` | Quy trình `3` bước cơ học, giới hạn cắt lát mỏng `<= 3` file/task, khuôn **Executable Task Card** chống bỏ sót `Trước → Sau` & `Test Oracle`, phủ luôn `quick-lane` và `QC fix task` | Loại bỏ mơ hồ về input→output, chữ ký/API và tiêu chí kiểm thử; đồng bộ 1 chuẩn giao việc và bổ sung tiêu chí soi cho reviewer |
| **Lớp 2: Tooling & Automation** | `scripts/tdq_team.py`, `scripts/tdq_state.py`, script mới `scripts/tdq_plan_scaffold.py`, `plugins/tdq-workflow-agy/hooks/scripts/subagent_dispatch_gate.py`, `tools/patches/skills_and_agents.py` | **Symbol/AST Scaffolder** trích sẵn symbol thật, vị trí neo lân cận và caller (cấm Planner tự nhớ/bịa) | Vá bug parser `tdq_team.py` cô lập `Chạm:` khỏi tham chiếu; **Auto Task Packet Builder** bơm sẵn snippet neo + bất biến kiến trúc cho `flash` không có LSP |
| **Lớp 3: Hard Gates & Linter** | `scripts/doc_lint.py` (`rule_r15`, `pair`, `SKILL_LINE_LIMITS`), `scripts/tdq_state.py` (`approve plan`), `docs/tdq/token-budget.json` | Chặn **Task Block Theater**, mega-task `> 3` file và `ANTI-2` ngay tại cổng `approve plan` & `--pair` (có mốc `R15_MOC`) | Bảo đảm mọi task đưa vào pha `implement` đều có neo, Trước → Sau, thuật toán và oracle kiểm thử thực sự |

---

## 2. Lớp 1 — Chuẩn hóa Skill, Template & Agent Contracts

### 2.1. Quy trình 3 Bước Cơ học cho Weak Planner (`tdq-plan`)

Để một model tier thấp không bị quá tải hay bịa tên hàm/schema khi lập plan, V1 chia thao tác viết plan thành `3` bước tuần tự mang tính cơ học:

1. **Bước A — Trích sự thật từ ổ đĩa trước khi viết (Zero-Guessing Grounding):**
   - Bắt buộc chạy `tdq_plan_scaffold.py` (Lớp 2) trên các file đích lấy từ `spec §2b` để nhận về khung AST/symbol thật (tên hàm, chữ ký tham số, `2` symbol liền kề trên/dưới, danh sách hàm dùng lại và callers).
   - Nghiêm cấm Weak Planner tự nhớ tên file hoặc số dòng từ trí nhớ hay từ tóm tắt hội thoại.
2. **Bước B — Cắt Lát Mỏng Nguyên tử (Anti-Mega-Task Rule):**
   - Mỗi task sửa mã nguồn chỉ được chạm tối đa **`<= 2` file mã nguồn chính** (cộng tối đa `1` file test đi kèm — tổng đường dẫn trong `Chạm:` **tối đa `<= 3` file**), tác động **`<= 3` hàm/symbol** hoặc **`<= 150` dòng sửa đổi**.
   - Nếu `spec §2` có đầu ra đụng `8` file (như `11-19-1632:T2.1`), BẮT BUỘC chẻ thành `3–4` task nhỏ (`T2.1a`, `T2.1b`, `T2.1c`…) theo ranh giới file/module.
3. **Bước C — Điền khuôn Executable Task Card & Tự kiểm 3 đường:**
   - Điền đủ các trường Structural Contract (mục `2.2`), kiểm tra phụ thuộc `Cần:`, giữ toàn bộ dòng con thụt lề `2` khoảng trắng (mã/fence thụt lề `4` khoảng trắng), rồi chạy `doc_lint.py --pair <spec> <plan>` trước khi trình duyệt.

### 2.2. Khuôn "Executable Task Card" (V1) cho Task Mã nguồn & QC Fix Task

Bảo toàn bất biến cột 0 `- [ ] **Tx.y** (eNm) <việc> — Test: \`<lệnh>\`` (để giữ nguyên tương thích với `tdq_state.py:_TASK_LINE`, `storage.rs`, `stop_gate.py:_next_task`, `tdq_eval.py`, `tdq_bench.py`), đồng thời tái cấu trúc thân con thành **Structural Contract** chặt chẽ:

```markdown
- [ ] **T1.1** (e10m) <1 dòng tóm tắt hành vi đích> — Test: `<lệnh pytest/cargo/cli chạy được>`
  - Chạm: `<file_dich_1.py>`, `<tests/test_file_1.py>`
  - Tham chiếu: `<file_chi_doc.py:ten_symbol>`, `<spec §3c:ten_schema>`
  - Cần: <mã task trước, hoặc "không">
  - Vị trí neo: `<file_dich_1.py>` :: <tạo mới | ngay trước `sym_sau` / sau `sym_truoc` | thay thế thân `def ham_x`> (tham khảo ~dòng N)
  - Trước → Sau:
    - Trước: <trạng thái/hành vi/schema đầu vào hiện tại — ví dụ: nhận raw str, trả None hoặc crash TypeError>
    - Sau: <hành vi/trạng thái/đầu ra mới — ví dụ: decode tối đa 3 vòng json.loads -> trả tuple[dict, bool]>
  - Công nghệ & Đặc tả: <stdlib/crate cố định; dùng edit_file/write_file; chữ ký hàm, kiểu dữ liệu, struct/JSON schema đầy đủ>
  - Logic & Ràng buộc (<= 5 bước, <= 5 luật cục bộ):
    1. Bước 1: <kiểm tra đầu vào / guard condition>
    2. Bước 2: <xử lý chính / nhánh rẽ if-elif theo thứ tự ưu tiên rõ ràng>
    3. Bước 3: <trả về / ghi state / fail-closed khi lỗi>
    - Luật cục bộ: <tối đa 5 luật kiểm ngay tại chỗ, không chép prose luật toàn cục; ví dụ: cấm print() để giữ pure stdout, tái dùng `_doc()`>
  - Test Oracle (Red → Green):
    - Ca hiểm: <input biên / rỗng / sai kiểu / lồng JSON / Unicode / concurrency>
    - Tiêu chí: `<assert 1 (happy path)>` · `<assert 2 (edge/negative case)>` · `<assert 3 (invariant/security)>`
```

**4 điểm nâng cấp cốt lõi so với Task Block ngày `2026-11-11`:**
1. **Tách riêng `Chạm:` và `Tham chiếu:`:** `Chạm:` chỉ liệt kê file được quyền **sửa/tạo mới** (`<= 3` file), còn mọi file đọc đối chiếu, helper tái sử dụng, tài liệu spec đưa sang `Tham chiếu:` — giúp `tdq_team.py` không bao giờ biến file đọc thành `HOT FILE`.
2. **Bắt buộc cặp `Trước → Sau` ở cấp từng task:** Giải quyết trực tiếp lỗ hổng `58.3%` vắng mặt, ép Planner chốt ranh giới biến đổi I/O & state trước khi code.
3. **Neo theo Symbol + Hàm lân cận thay vì số dòng cứng:** Số dòng chỉ giữ làm tham khảo phụ; điểm neo thật là tên symbol (`ngay trước LSP = re.compile(...)`, `bên trong def main()`), ngăn gãy plan drift khi wave trước sửa file.
4. **Cấm chép full body hàm dài, siết `<= 5` luật cục bộ:** Khớp trực tiếp phát hiện từ `Skeleton Coding` (+23–58 pp) và `IFScale` (chống suy giảm hàm mũ trên `Flash`/`Haiku`/`Mini`). Đẩy luật toàn cục (`<= 50` dòng/hàm, complexity `<= 10`, format, `i18n`) sang linter và bước QC.

### 2.3. Vá Lỗ hổng `quick-lane` & `QC fix task` và Cải tiến `tdq-spec`

- **Phủ `QC fix task` (`skills/tdq-build/references/qc.md`):** Khi QC phát hiện lỗi chạm mã nguồn (`**QCn.1**`), cấm viết 1 dòng trần. Bắt buộc điền tối thiểu **5 trường rút gọn** (`Chạm:`, `Vị trí neo:`, `Trước → Sau:`, `Logic:`, `Tiêu chí:`) để `R15` kiểm soát được `100%` fix task (`2026-11-19-1632:QC1.1`, `2026-11-18-1814:QC2.1`).
- **Phủ `quick-lane` (`skills/tdq-intake/references/quick-lane-mini.md`):** Tách `2` khuôn cho mini-plan: (a) việc chỉ sửa `docs`/config giữ dạng 1 dòng; (b) **việc sửa mã nguồn** bắt buộc dùng **Compact Code Card** (`Chạm:`, `Vị trí neo:`, `Trước → Sau:`, `Logic:`, `Tiêu chí:`) và nâng trần mini-plan khi có task code lên **`80` dòng** (hoặc chuyển sang lane `full` nếu có `>= 3` task code).
- **Chống thiếu/ảo giác từ đầu nguồn (`skills/tdq-spec/references/spec-template.md`):** Thêm tiểu mục bắt buộc trong `§3c`: **Bảng Hợp đồng Dữ liệu & Chữ ký Dùng chung** (liệt kê mọi JSON schema/struct mới và hàm giao tiếp liên module đã xác minh từ code thật), đồng thời ghi quy tắc trong `tdq-plan` cấm dùng câu trỏ mù `"theo spec §3c"`.

### 2.4. Thoát Trần Dòng & Token + Đồng bộ `agents/` & `team-mode.md`

- **Giải bài toán `121/121` dòng ở `skills/tdq-plan/SKILL.md` và `3,279/3,500` token ở `plan-template.md`:**
  - Tách phần giải thích quy trình Weak Planner (`3` bước cơ học), hướng dẫn điền `Executable Task Card`, quy tắc chống mega-task `<= 3` file, và `1` ví dụ Trước/Sau chuẩn sang file sibling Tier-1 mới: `skills/tdq-plan/references/task-card-guide.md` (`<= 2,500` token, có `<!-- muc-luc-dong: -->`).
  - Rút gọn mẫu lặp trong `plan-template.md` (giữ khung copy `100%` gọn dưới `2,900` token), trỏ tới `task-card-guide.md`.
  - Cập nhật `skills/tdq-plan/SKILL.md` (thêm `2–3` dòng nhắc thẳng Weak Planner quy trình 3 bước, `R15` và link `task-card-guide.md` cho đúng luật reference 1 tầng) và nâng `SKILL_LINE_LIMITS["tdq-plan"]` trong `scripts/doc_lint.py:63` từ `121` → `128` dòng theo đúng `soul.md` (`đừng nén luật để khớp trần`).
  - Nhớ chạy `scripts/token_budget.py` và `scripts/doc_index.py` sau khi sửa `skills/tdq-plan/**`.
- **Đồng bộ `agents/tdq-implementer.md`, `agents/tdq-reviewer.md`, `skills/tdq-build/references/team-mode.md`:**
  - Xóa mâu thuẫn giữa `team-mode.md:126-138` (`9` trường) và `agents/tdq-implementer.md:12-38` (`7` trường, nhãn `(nN)` cũ, lệnh tự tick `- [~]`/`- [x]` trong worktree gây đụng hook). Dùng chung 1 chuẩn **Auto Task Packet** có `(eNm)` và quy tắc rõ: leader giữ toàn quyền tick file plan ở nhánh chính, worker chỉ viết code/test trong `VÙNG FILE` và trả `TICK-READY: yes`.
  - Sửa hướng dẫn `tdq-implementer` để tương thích với môi trường AGY `model: flash` (nơi tool LSP/Grep bị tước): đọc trực tiếp `NGỮ CẢNH NEO` + `Tham chiếu` được bơm sẵn trong packet trước khi `read_file`/`edit_file`.
  - Nâng cấp `agents/tdq-reviewer.md`: thêm hạng mục kiểm số `6. Execution Readiness (Low-Tier)` — chặn cứng (`>= 0.80`) mọi task sửa code chạm `> 3` file, thiếu `Trước → Sau`, thiếu neo symbol, thiếu `Test Oracle`, hoặc có trỏ mù `"theo spec §..."`.

---

## 3. Lớp 2 — Tooling & Automation (Vá Parser + Scaffolder + Auto Packet)

### 3.1. Vá triệt để Parser trong `scripts/tdq_team.py` & `scripts/tdq_state.py`

1. **Cô lập nguồn đọc `t.vung_file` (`scripts/tdq_team.py:175-182`):**
   - **Trước:** `for dong in t.text: for duong in _PATH.findall(dong): ...` — quét bừa mọi dòng trong task, làm mọi đường dẫn trong `Tham chiếu:`, `Vị trí neo:`, `Logic:`, `Test:` bị đẩy vào `t.vung_file`.
   - **Sau:** Chỉ quét `_PATH` trên các phần tử thuộc **`Chạm:`** (nhận diện `dong.lstrip().startswith(("Chạm:", "Touch:"))` — kể cả dòng continuation đã được `:167-172` nối vào). Mọi path trong `Tham chiếu:` được lưu vào thuộc tính mới `t.tham_chieu` (chỉ dùng để trích context cho worker, **không** tham gia kiểm collision `HOT FILE`, **không** kích hoạt `file-luat`, và **không** mở quyền ghi trong `ngoai_vung_khai`).
2. **Sửa fallback `_TASK_REF` (`scripts/tdq_team.py:395-400`):**
   - Trong `quyet_dinh_task`, khi xác định phụ thuộc giữa các task, ưu tiên 100% nhãn `Cần:` (`doc_phu_thuoc`); nếu toàn plan không có `Cần:`, chỉ quét `_TASK_REF` ở dòng mô tả tiêu đề task (`t.text[0]`) chứ không quét phần `Logic:`/`Tham chiếu:` (tránh nhầm câu `"tương tự T1.1"`).
3. **Hỗ trợ `Chạm:` nhiều dòng ở `scripts/tdq_state.py:2487` (`_extract_plan_targets`):**
   - Nếu `Chạm:` xuống dòng theo sub-bullet thụt lề sâu hơn, gom tiếp các path thuộc khối `Chạm:` cho tới khi gặp nhãn con khác.
4. **An toàn thụt lề cho code fence trong task:**
   - Quy chuẩn mọi block schema/code trong thân task đều thụt lề tối thiểu `4` khoảng trắng (`    ``` `) để cả `tdq_team.doc_plan` (`:173-174`) lẫn `doc_lint.rule_r15` (`:548-550`) không kết thúc task sớm.

### 3.2. Weak-Planner Symbol & Anchor Scaffolder (`scripts/tdq_plan_scaffold.py`)

Công cụ CLI thuần Python stdlib chạy nhanh (`< 1s`) trước bước viết plan:
- **Đầu vào:** `--files <danh sách path từ spec §2b>` hoặc `--plan-targets`.
- **Thuật toán:**
  1. Với mỗi file `.py` (dùng `ast.parse`) hoặc `.rs`/`.ts`/`.js` (dùng bộ parser regex/heading cấu trúc hoặc gọi `lsp_module` cache có sẵn nếu chạy ngoài hook):
     - Trích danh sách top-level constants, classes, methods, functions kèm **dòng bắt đầu–kết thúc**, **chữ ký đầy đủ** (`def name(args) -> ret:`), và **neighbor symbols** (`prev_sym`, `next_sym`).
  2. Chạy quét tham chiếu chéo nhanh trong repo (`rg`/`grep` trên danh sách file sản phẩm) để gắn `callers_sample` cho các symbol công khai.
  3. Lọc các quy tắc trong `docs/kien-truc.md` khớp thư mục của file đích (`hooks/`, `scripts/`, `skills/`, `plugins/`).
- **Đầu ra:** In ra Markdown/JSON thu gọn (theo nguyên lý AST compression giảm ~`91%` token) để Weak Planner **copy nguyên chữ ký + `prev_sym`/`next_sym` thật** vào Task Card — triệt tiêu bịa tên hàm và sai neo.

### 3.3. Auto Task Packet Builder (`scripts/tdq_team.py packet <task_id>`)

Thay vì bắt leader ghép tay prompt `9` trường và quên gửi context cho `tdq-implementer` (`model: flash` không có LSP trên AGY), bổ sung subcommand `tdq_team.py packet <task_id> [--plan ...]`:

1. Đọc đúng **1 Task Block** của `task_id` (lọc bỏ toàn bộ các task khác và bỏ phần `spec.md` thừa để tránh *Context Rot*).
2. Đọc `t.tham_chieu` và `Vị trí neo`: tự động trích từ đĩa tối đa `+-25` dòng quanh symbol neo ở mỗi file `Chạm:` + chữ ký AST của các symbol ghi trong `Tham chiếu:` (nén tổng snippet `<= 80` dòng).
3. Đính kèm tối đa **`<= 3` bất biến kiến trúc cục bộ** khớp vùng file (ví dụ: đụng `hooks/` → nhắc không để `scripts/` import ngược; đụng `scripts/` → nhắc `i18n` English cho comment/print và không tự mở `state.json`), cộng khuôn `RANH GIỚI` (`Always / Ask First / Never`), `WORKTREE`, `VÙNG FILE`, `TEST`, `TỰ KIỂM`, `TRẢ VỀ`.
4. **Cập nhật hook `plugins/tdq-workflow-agy/hooks/scripts/subagent_dispatch_gate.py:8,40-45`:**
   - Mở rộng kiểm tra prompt gửi `tdq-implementer`: ngoài `5` nhãn cũ, yêu cầu trong `TASK:` phải có `VỊ TRÍ NEO` (hoặc `Vị trí neo:`), `TRƯỚC`→`SAU` (hoặc `Trước:`), và `TIÊU CHÍ` (hoặc `Tiêu chí:`); nếu thiếu thì phát cảnh báo `[TDQ:SUBAGENT]` (hoặc `block` khi `strict`) nhắc dùng `tdq_team.py packet <task_id>`.

### 3.4. Just-In-Time (JIT) Wave Check giữa các Đợt

Trước khi mở đợt $k+1$ trong `tdq_team.py wave` / `open`, thực hiện kiểm nhanh các `Vị trí neo:` của task đợt $k+1$: nếu đợt $k$ vừa đổi tên hoặc dời symbol neo, báo cho leader cập nhật Task Card trước khi phát `packet` sang worker (hiện thực hóa cơ chế *Sprint Contract* chống plan drift).

---

## 4. Lớp 3 — Hard Gates & Kiểm định Cưỡng chế (`doc_lint.py` R15 + `approve plan`)

### 4.1. Nâng cấp `rule_r15` trong `scripts/doc_lint.py:526-567`

Giữ nguyên triết lý `R14_MOC` để **không làm gãy 236 plan lịch sử và seed test trong `evals/tuan-thu/`**:

- **Mốc kích hoạt nghiêm ngặt:** `R15_MOC = "2026-11-20-0000"` (hoặc kích hoạt ngày triển khai feature). Trước `R15_MOC`, giữ nguyên hành vi kiểm 1 từ khóa cũ; từ `R15_MOC` trở đi áp dụng **R15-Strict (5 điểm kiểm cấu trúc)**:
  1. **Mở rộng diện quét task:** Bắt cả `**T...**` lẫn `**QC...**` (regex `^\s*-\s*\[( |~|x|>)\]\s*\*\*((?:T|QC)[A-Za-z0-9.]*)\*\*`) khi trong khối `Chạm:` (hỗ trợ cả nhiều dòng con của `Chạm:`) có file thuộc `EXT_MA_NGUON`, hoặc trong `Chạm:` ở `docs/tdq/plan/` thuộc mini-plan `quick` có đuôi code.
  2. **Kiểm đủ 5 cấu phần thay vì 1 từ khóa:**
     - *(i) Neo vị trí (`Vị trí neo:` / `Anchor:`):* Bắt buộc tồn tại và phải chứa ít nhất `1` chỉ dấu kỹ thuật (`tạo mới`, `new file`, backtick symbol `` `...` ``, tên hàm `()`, `::`, hoặc cụm `trước`/`sau`/`trong`) — từ chối nếu chỉ ghi trơn mỗi `"dòng 45"`.
     - *(ii) Trước → Sau (`Trước:` & `Sau:`, hoặc `Before:` & `After:`):* Bắt buộc có cả vế trước và vế sau không rỗng (`> 3` từ mỗi vế hoặc có chữ ký/giá trị).
     - *(iii) Đặc tả & Giải thuật:* Có `Công nghệ & Đặc tả:` (hoặc `Đặc tả kỹ thuật:`) + `Logic` có ít nhất `>= 2` bước (`1.`, `2.` hoặc `- ` rẽ nhánh) và không dùng cụm trỏ mù (`theo spec §`, `xem spec`, `như cũ`).
     - *(iv) Test Oracle (`Tiêu chí:` / `Test Oracle:`):* Phải tồn tại và chứa ít nhất `1` khẳng định có giá trị kiểm chứng (`assert `, `assert_eq!`, `expect`, `raises`, `==`, `!=`, `->`, `exit `); từ chối mẫu `ANTI-2` trần (`assert True`, `assert len(...) >= 0`, `os.path.exists(...)` đứng một mình cho task logic).
     - *(v) Chống Mega-task:* Đếm số file code (ngoại trừ file test `*test*`) trong khối `Chạm:` — nếu `> 2` file code (hoặc tổng `Chạm: > 4` file cả code + test) thì báo lỗi R15 yêu cầu tách task nguyên tử.
  3. **Bảo toàn ràng buộc `doc_lint` hiện hữu (`R8`, `R12`, `R13`):**
     - Nếu task vừa có khối hợp đồng skill `Dùng:`...`Không dùng cho:` (R8 chỉ quét `CONTRACT_SCAN = 8` dòng dưới `- Dùng:`) vừa có Task Block, bắt buộc đặt khối `Dùng:` **ngay dưới dòng tiêu đề task hoặc tách hẳn sau `Chạm:`** sao cho 5 dòng `- Dùng/- Để/- Ra/- Kiểm/- Không dùng cho` đứng liền kề nhau trong `<= 8` dòng.
     - Mọi khối pseudo-code/signature dài không dấu tiếng Việt `>= 3` dòng phải bọc trong code fence thụt lề (`    ``` `) để không kích hoạt `rule_r12` (`doc_lang=vi`).

### 4.2. Gắn Cưỡng chế vào `--pair` và `tdq_state.py approve plan`

1. **Nối vào `doc_lint.py --pair` (`scripts/doc_lint.py:602-637`):** Khi chạy `--pair <spec> <plan>`, ngoài kiểm `R8` (khớp skill `DÙNG` & `## Cụm song song`), tự động chạy `rule_r15` trên `<plan>` để mọi lệnh kiểm cặp ở cuối pha viết plan đều bắt đủ lỗi Task Card.
2. **Cổng chặn ở `tdq_state.py approve plan`:**
   - Thêm hàm `_r15_gate(cwd, state, target, bo_qua_r15)` (thiết kế đối xứng 1–1 với `_r14_gate` ở `scripts/tdq_state.py:2213-2238`).
   - Khi `target == "plan"` (và lane `full` hoặc `quick` có sửa code): gọi `doc_lint.r15_loi(...)`. Nếu còn vi phạm R15 → in từng dòng lỗi ra `stderr`, từ chối ghi `plan_approved = true` và thoát mã `1`!
   - Dự phòng khẩn cấp cho người dùng: chỉ khi người dùng chủ động đồng ý bỏ qua mới dùng `--bo-qua-r15 "<lý do>"` (ghi vết vào `state["plan_bo_qua_r15"]`).

---

## 5. Tổng hợp Điểm cần Red-Team Ở Vòng 2 Săn Lỗi (Giả thuyết Rủi ro của V1)

Bản V1 trên cần được `3` luồng Red-Team độc lập trong Đợt 3 tấn công vào các câu hỏi gai góc sau:
1. *(Cho Red-Team A — Nhận thức model nhỏ):* Việc bắt buộc **Weak Planner** vừa tự điền `Chạm:`, `Tham chiếu:`, `Trước → Sau`, `Đặc tả`, `Logic <= 5 bước`, `Test Oracle` vừa giữ `<= 2` file code/task có làm tổng số task nổ tung (`10` task thành `25` task), làm chính Weak Planner dính **IFScale Decay** khi viết hoặc khi tổng hợp toàn plan không? Và `5` trường con này cộng lại có còn nhét quá nhiều thông tin vào 1 Task Packet cho `Flash`/`Haiku`?
2. *(Cho Red-Team B — Ràng buộc kỹ thuật TDQ):* Những chỗ nào trong V1 va chạm ngầm với `doc_lint.py` (R5 câu 40 từ, R6 121 dòng, R8 8 dòng, R12 dòng đánh số tiếng Việt `1. Bước 1:`, R13 3500 token), `tdq_team.py` (projection sha `v1`, `canh_bao_lach_luat`, `TDQ_PATH` trong `Test:`, `Chạm:` nhiều dòng), `tdq_eval.py` (`RE_TICK`, seed plans), hay `tools/patches/skills_and_agents.py` (ANCHOR replace)?
3. *(Cho Red-Team C — Stress-Test thực chiến):* Khi áp thẳng khuôn V1 viết lại `11-19-0046:T2.3` (9 cổng Rust), `11-19-1632:T2.1` + `QC1.1` (8 file Rust + fix Python 3.9), và `11-19-1457` (quick-lane): thực tế phải tách thành mấy task, tốn bao nhiêu dòng/token, chỗ nào viết cực gượng hoặc vẫn bỏ sót chi tiết?
