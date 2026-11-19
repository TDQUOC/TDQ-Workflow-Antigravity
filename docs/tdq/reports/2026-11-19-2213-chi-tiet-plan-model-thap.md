# REPORT — Phân tích Độ chi tiết của Plan cho Model Tier Thấp (`End-to-End`) & Đề xuất Cải thiện V2 (`2026-11-19-2213-chi-tiet-plan-model-thap` · lane `full` · mode `main` + `fanout` Red-Team · `9` task tick đủ)

Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

> **Tổng kết trực quan (1 câu):** Nhận định của bạn **ĐÚNG 100%** trên thực chứng `236` plan (`2,699` task): ngay cả sau bản vá `2026-11-11`, mới chỉ **`20.8%` (`5/24`)** task đạt chuẩn cho model tier thấp (`>= 12/14`); qua **`2` vòng phân tích & `3` luồng Red-Team phản biện độc lập**, báo cáo chốt **Kiến trúc Cải thiện 3 Lớp Phiên bản V2** khắc phục triệt để **`12/12` nhược điểm (`ND-1`..`ND-12`)** cho cả **Weak Planner** lẫn **Weak Executor (`2b`)**.

- **Liên kết hồ sơ đầy đủ:**
  - Khảo sát nền & Vòng 1: [brief](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/brief/2026-11-19-2213-chi-tiet-plan-model-thap.md) · [research](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/research/2026-11-19-2213-chi-tiet-plan-model-thap.md) · [phan-tich-vong-1.md](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/artifacts/2026-11-19-2213-chi-tiet-plan-model-thap/phan-tich-vong-1.md) · [de-xuat-v1.md](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/artifacts/2026-11-19-2213-chi-tiet-plan-model-thap/de-xuat-v1.md)
  - Phản biện Red-Team Vòng 2: [redteam-a-nhan-thuc.md](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/artifacts/2026-11-19-2213-chi-tiet-plan-model-thap/redteam-a-nhan-thuc.md) · [redteam-b-rang-buoc-tdq.md](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/artifacts/2026-11-19-2213-chi-tiet-plan-model-thap/redteam-b-rang-buoc-tdq.md) · [redteam-c-stress-test.md](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/artifacts/2026-11-19-2213-chi-tiet-plan-model-thap/redteam-c-stress-test.md) · [phan-bien-vong-2.md](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/artifacts/2026-11-19-2213-chi-tiet-plan-model-thap/phan-bien-vong-2.md)
  - Báo cáo trực quan Archify HTML: [2026-11-19-2213-chi-tiet-plan-model-thap.html](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/reports/2026-11-19-2213-chi-tiet-plan-model-thap.html) · Tailscale Serve: https://unity-pc-rtx3060.tail99896.ts.net/vlog/tdq-workflow-agy/reports/2026-11-19-2213-chi-tiet-plan-model-thap.html

---

## 1. Trước request (trạng thái/flow)

1. **Thực trạng chất lượng Plan trên kho `236` plan (`2,699` task):** Chấm sâu `48` task mẫu theo `7` chiều (`0..14`) cho thấy trước mốc `2026-11-11` đạt `0%` chuẩn (`5.08/14`), sau `11-11` tăng lên **`20.8%` (`5/24` task; `7.42/14`)**. Ba chiều yếu nhất ngay cả sau `R15` là: thiếu **Trước → Sau mức từng task (`58.3%` vắng mặt; toàn bộ `117` task sau `11-11` chỉ có `0.9%`)**, thiếu **neo dòng/vùng neo cụ thể (`60.9%` task code thiếu)**, và thiếu **Test Oracle `input → assert` (`37.5%` vắng mặt)**. Ngoài ra `76.5%` task sửa QC (`13/17`) chỉ là `1` dòng trần, `100%` quick-lane bỏ qua Task Block, và tỉ lệ **mega-task chạm `>= 4` file tăng `2.8×`** (`4.9% → 13.7%`).
2. **Bảy điểm gãy gốc trong quy trình TDQ:**
   - `skills/tdq-plan/SKILL.md` (`121/121` dòng, hết chỗ) không nhắc Self-Contained Task Block và 4 chốt an toàn (`plan-template-huong-dan.md:40-53`).
   - `scripts/doc_lint.py:526-567` (`rule_r15`) chỉ kiểm `1` từ khóa (`logic`), bỏ sót `**QCn.x**`, không chạy ở `--pair`, không nối vào cổng duyệt, tạo ra hiện tượng **"Task Block Theater"** (`11-19-0046:T2.3`).
   - `scripts/tdq_team.py:175-179` quét `_PATH` trên mọi dòng task thay vì riêng `Chạm:` nên việc ghi nhiều tham chiếu làm nhiễm `vung_file` và nổ `HOT FILE` giả.
   - `tools/patches/skills_and_agents.py:45-50` ép `tdq-implementer` của AGY chạy `model: flash` và tước sạch tool `LSP`/`grep`, trong khi packet giao việc ghép tay không bơm snippet neo và mâu thuẫn với `agents/tdq-implementer.md:12-38`.
   - Ngược lại, nghiên cứu ngoài (`Skeleton Coding arXiv:2610.38214v1`, `IFScale arXiv:2507.11538v1`, `Context Rot`, `Böckeler & Heym`) cảnh báo nếu giải pháp chỉ ép nhồi văn xuôi dài, code body nguyên văn hoặc số dòng cứng dễ trượt sẽ làm chính model nhỏ (`Flash`/`Haiku`/`Mini`) tụt hiệu năng theo hàm mũ.

---

## 2. Sau request (trạng thái/flow) — Đề xuất Hoàn chỉnh V2 (`2b` + `3a`)

Qua `2` vòng phân tích và `3` luồng Red-Team phản biện độc lập (`18` phát hiện → **`12` mã nhược điểm `ND-1`..`ND-12`**), đề xuất cuối cùng **V2** giữ đúng khung `3` lớp (`3a`) cho kịch bản **Full Low-Tier End-to-End** (`2b`) nhưng vá kín toàn bộ `12` nhược điểm của V1:

### 2.1. Bảng Truy vết 100% Nhược điểm V1 (`ND-1`..`ND-12`) → Giải pháp Vá V2

| Mã | Mức | Nhược điểm V1 được Red-Team bắt | Giải pháp đã vá trong Thiết kế V2 |
|---|---|---|---|
| **ND-1** | `Cao` | **IFScale trên Weak Planner & `HOT FILE` trên file đa hàm:** viết `8` trường × `25` task trong `1` lượt làm Planner quá tải; `1632:T2.1` nổ `1 → 6` task và `0046:T2.3` biến `pre_tool_use.rs` thành `HOT FILE`. | **Two-Pass Skeleton-then-Card:** Pass 1 chỉ viết DAG nhẹ (`Tx.y`, `Chạm:`, `Cần:`, `Test:`) + chạy `tdq_team assign`; Pass 2 chạy `tdq_plan_scaffold.py --emit-cards` đổ sẵn neo/signature để Planner chỉ điền `Trước → Sau`, `Logic`, `Tiêu chí` từng phase. Cảnh báo `> 4` symbol mới trong `1` file; gom sửa `mod.rs`/`manifest` lên wave hợp đồng sớm. |
| **ND-2** | `Cao` | **Scaffolder mù Greenfield & regex `.rs`/`.ts` ảo giác:** chạy mỗi trên `Chạm:` trả rỗng khi tạo file mới; regex cắt sai Rust/TS; `--files` từ `§2b` bỏ lọt caller động toàn repo. | Thêm `--refs` (đọc AST module `Tham chiếu:`/đối chứng) và `--from-spec <spec.md>` (trích hợp đồng `spec §3c` cho file tạo mới, fail `exit 1` nếu `§3c` thiếu); quét callers toàn repo + bảng dispatch; đọc cache LSP trước, fallback regex phải gắn cờ `ANCHOR_CONFIDENCE: LOW`. |
| **ND-3** | `Cao` | **Quá tải `35–40` chỉ thị & cắt cụt hàm ở Packet:** cộng `~20` luật `tdq-implementer.md` + `9` trường packet + cắt cứng `80` dòng bẫy `Flash` vào vòng retry mù (`9→6/10`). | Gọt `tdq-implementer.md` còn `<= 30` dòng (`<= 6` luật cốt lõi); trích ngữ cảnh theo **Symbol-Span** (trọn thân hàm đích + `3` dòng biên cho tối đa `2` file, `Tham chiếu:` chỉ lấy `1` dòng signature, vượt ngưỡng xuất `READ-EXACT`); đặt **Circuit Breaker `<= 2` lần retry** trên `Flash`. |
| **ND-4** | `Cao` | **R15 dễ lách ("Theater 2.0"), mâu thuẫn §2.3 vs §4.1, sai pha `approve plan`, hở `quick` & non-code `ANTI-2`:** §2.3 đòi 5 trường nhưng §4.1 ép `Công nghệ & Đặc tả:`; `approve plan` chạy sau khi user duyệt; `quick` gọi `approve quick`; `11-19-1457` lọt lưới `ANTI-2`. | Tách **`2` profile R15** (`R15-Full` cho code `full`, `R15-Compact` `5` trường cho `QCn.x` & `quick` code); tách kiểm **`ANTI-2` độc lập cho 100% task/QC/DoD** + thêm `EXT_CAU_HINH`; dịch cổng chặn về **TRƯỚC trình duyệt** (`set plan_file`, `tdq_finish`, `--pair`; `approve plan`/`approve quick` chỉ kiểm sạch và fail-open nếu `quick` không có file); xác minh symbol thật & `assert` AST qua `--verify-plan`. |
| **ND-5** | `Cao` | **Bẻ vụn "Uniform Mechanical Sweep", thiếu `Sinh ra:` & ép nén `quick-lane`:** `QC1.1` xé `15×`; build `plugins/` đụng `ANTI-6` / `> 2` file; ngưỡng `>= 3` task code ép nén file. | Thêm ngoại lệ **Uniform Mechanical Sweep** (`<= 6` file đồng nhất `1` phép biến đổi + `1` neo); thêm nhãn **`Sinh ra:`** (artifact từ build) tách khỏi `Chạm:`; neo ngưỡng nâng cấp `quick → full` theo **tổng file sửa gốc (`> 4` file code)**. |
| **ND-6** | `Cao` | **Đâm trần R13 (`3,500` token) ở `qc.md` (`3,496`), `spec-template.md` (`3,486`), `team-mode.md` (`3,390`), bẫy `tiktoken` & sót `plan-template-huong-dan.md`.** | Đẩy chi tiết sang sibling (`qc-vong-fix.md`, `spec-template-huong-dan.md`, `team-mode-tra-cuu.md`, `task-card-guide.md`); cập nhật `plan-template-huong-dan.md`; đo lại bằng `anthropic-tokenizer` (`<= 3,350` token); chạy `doc_index.py`, `token_budget.py`, nâng `SKILL_LINE_LIMITS["tdq-plan"]` → `128`. |
| **ND-7** | `Cao` | **Bug parser `tdq_team.py` & `doc_lint.py` với sub-bullet `Chạm:`, `Tham chiếu:`, `t.text[0]`, `in_fence`.** | Theo dõi `indent` và `in_fence` đồng bộ ở `doc_plan()`, `tdq_state._extract_plan_targets()`, `doc_lint.rule_r15`; giữ fallback `t.text[0]` khi không có `Chạm:`; chuẩn hóa `Tham chiếu:` dạng `` `path/file.py` (`sym`) ``; hỗ trợ whitelist file gốc (`CLAUDE.md`, `AGENTS.md`, `Cargo.toml`). |
| **ND-8** | `Cao` | **`JIT Wave Check` tự kích nổ khóa STALE kép (`plan_assignment_sha` & `sha_file` ở `canh_bao_lach_luat`) & gãy compile worktree.** | Loại `Vị trí neo:` / `Tham chiếu:` / ghi chú delta khỏi `plan_assignment_sha`; sửa `canh_bao_lach_luat` dùng `kiem_tra_stale`; thêm `CONTRACT-DELTA:` + `--check-wave`; ngoại lệ `<= 5` file cho `dong-bo-chu-ky` hoặc wave shim sớm. |
| **ND-9** | `Cao` | **Bẫy `R12` trên bước `1. Bước 1:` & signature Rust, lệch `--pair`, gãy `RE_TICK`/`_TASK_REF` trên `QC1.1`/`T2.1a`/`T1`.** | Vá `_r12_van_xuoi` miễn `\d+\.\s` trong thân task hoặc buộc fence cho signature; skip `doc.in_fence[i]` trong `rule_r15`; tách `r15_loi(..., check_dir=...)`; đồng bộ `RE_TICK` & `_TASK_REF`. |
| **ND-10** | `Cao` | **Sửa nhầm file generated `subagent_dispatch_gate.py`, vỡ test Parity/Dual-Protocol, rò tool AGY & thiếu `LENH`.** | Đặt đích sửa hook tại `tools/patches/agy_hooks.py` (giữ `remind` tương thích parity); giữ `` `Edit` ``/`` `Write` `` trong `skills/` gốc để `skills_and_agents.py` tự biên dịch sang AGY; đăng ký `"packet"` vào `tdq_team.LENH` & `tdq_ten_lenh.py`. |
| **ND-11** | `TB` | **Điểm mù "Đồng cấp yếu" ở `tdq-reviewer` / `tdq-qc-tester` (`model: inherit` trên `2b`).** | Chốt chặn bằng kiểm định xác định (`tdq_plan_scaffold.py --verify-plan` + `doc_lint` + AST `Tiêu chí:`), giữ `tdq-reviewer` soi đối chiếu 1–1 `spec §3c ↔ plan`, khuyến nghị pin tier cao hơn cho reviewer/QC khi host hỗ trợ. |
| **ND-12** | `TB` | **Bẫy Windows popup, `i18n`, `build_portable.py:346` & `tdq_bench.py`.** | Áp chuẩn `utf8_io`, `TDQ_LOG`, `tdq_ten_lenh.chay_subprocess`, `i18n-allow`, thuần AST + cache tĩnh cho `tdq_plan_scaffold.py`; ví dụ trong `task-card-guide.md` dùng `src/foo.py`; khóa `R15-Strict` theo `docs/tdq/plan/` + `R15_MOC`. |

### 2.2. Kiến trúc Cuối cùng Phiên bản V2 (3 Lớp, End-to-End `2b`)

1. **Lớp 1 — Quy trình Weak Planner Two-Pass + 2 Profile Task Card + Sibling Sạch R13:**
   - **Pass 1 (DAG nhẹ):** Viết khung task (`Tx.y`, `eNm`, `Chạm:`, `Sinh ra:`, `Cần:`, `Test:`), đối chiếu `1–1` với `spec §2`, chạy `tdq_team assign` phát hiện `HOT FILE` sớm (gom `mod.rs`/`manifest` lên đợt đầu) và chạy `tdq_bench.py simulate`.
   - **Pass 2 (Scaffold-Prepopulated Card):** Chạy `tdq_plan_scaffold.py --emit-cards <plan.md> --refs ... --from-spec <spec.md>` đổ sẵn neo symbol thật & chữ ký hiện hữu/hợp đồng `spec §3c` vào từng task; Weak Planner chỉ điền phần biến đổi theo **từng phase một**:
     - **`R15-Full` (task code `full`):** `Chạm:` (`<= 2` file logic chính hoặc ngoại lệ `dong-bo-chu-ky` `<= 5` / `Uniform Sweep` `<= 6`), `Tham chiếu:` (dạng `` `path` (`sym`) ``), `Sinh ra:` (nếu chạy build), `Vị trí neo:` (theo symbol + `ANCHOR_CONFIDENCE`), `Trước → Sau:`, `Công nghệ & Đặc tả:` (gồm `Edit`/`Write`, chữ ký bọc trong code fence thụt `4` spaces), `Logic & Ràng buộc (<= 5 bước, <= 5 luật cục bộ):`, `Test Oracle (Ca hiểm + >= 2 assert thực chất)`.
     - **`R15-Compact` (task `QCn.x` và `quick-lane` code):** `5` trường gọn (`Chạm:`/`Sinh ra:`, `Vị trí neo:`, `Trước → Sau:` kèm chữ ký gọn, `Logic:`, `Tiêu chí:`) — giữ mini-plan `<= 65–80` dòng và chỉ nâng sang `full` khi sửa gốc `> 4` file code.
   - **Tổ chức tài liệu chuẩn `<= 3,350` token:** `tdq-plan/SKILL.md` (`128` dòng) trỏ tới sibling mới `task-card-guide.md` (dùng đường dẫn ví dụ `src/foo.py`); cập nhật `plan-template.md`, `plan-template-huong-dan.md`, `quick-lane-mini.md`; tách chi tiết mới từ `qc.md` → `qc-vong-fix.md`, `spec-template.md` → `spec-template-huong-dan.md`, `team-mode.md` → `team-mode-tra-cuu.md`; gọt `agents/tdq-implementer.md` xuống `<= 30` dòng (`<= 6` luật + circuit breaker `2` retry).
2. **Lớp 2 — Tooling & Automation (`tdq_plan_scaffold.py` + Vá `tdq_team.py` + `Auto Task Packet`):**
   - `scripts/tdq_plan_scaffold.py` (thuần stdlib, `tdq_ten_lenh.chay_subprocess`, không spawn LSP mới): hỗ trợ `--files`, `--refs`, `--from-spec` (Greenfield), `--emit-cards`, `--verify-plan` (kiểm tồn tại symbol + `assert` AST), và `--check-wave` (kiểm `CONTRACT-DELTA`).
   - Vá `scripts/tdq_team.py`: `doc_plan()` theo dõi `indent` & `in_fence`, cô lập `t.vung_file` theo `Chạm:` (fallback `t.text[0]` chỉ khi thiếu `Chạm:`), bổ sung `t.tham_chieu` & `t.sinh_ra`; loại `Vị trí neo:`/`Tham chiếu:` khỏi `plan_assignment_sha` và sửa `canh_bao_lach_luat` dùng `kiem_tra_stale`; đồng bộ `RE_TICK` & `_TASK_REF`; thêm lệnh `tdq_team.py packet <task_id>` (trích **Symbol-Span** trọn hàm + `1` dòng signature cho `Tham chiếu:` + `<= 3` bất biến `docs/kien-truc.md`, đăng ký vào `LENH` & `tdq_ten_lenh.py`).
   - Cập nhật `SUBAGENT_DISPATCH_GATE_PY` tại `tools/patches/agy_hooks.py` ở mức `remind` tương thích 100% Parity.
3. **Lớp 3 — Hard Gates Pre-Approval (`doc_lint.py` + `tdq_state.py`):**
   - Nâng cấp `rule_r15` (sau `R15_MOC`, áp riêng cho `docs/tdq/plan/` và `--pair` qua `check_dir=False`, skip `doc.in_fence[i]`, đọc `Chạm:` nhiều dòng): kiểm `R15-Full` / `R15-Compact`, kiểm `EXT_CAU_HINH` tối thiểu, và tách luật **`ANTI-2` áp dụng cho 100% task/QC/DoD (cả non-code)**.
   - Vá `_r12_van_xuoi` miễn dòng `\d+\.\s` trong thân task.
   - Kích hoạt kiểm `R15` + `ANTI-2` **TRƯỚC trình duyệt** (`tdq_state set plan_file`, `tdq_finish`, `--pair`) và kiểm sạch (không chặn sửa sau duyệt) tại `approve plan` lẫn `approve quick` (fail-open khi `quick` không tạo file plan).

### 2.3. Ba Ví dụ Trước / Sau Đạt Chuẩn V2 (`>= 12/14` — Đã Khắc phục Toàn bộ Ma sát Red-Team C)

*(Chi tiết trọn vẹn `3` bản viết lại V1 nằm ở [redteam-c-stress-test.md](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/artifacts/2026-11-19-2213-chi-tiet-plan-model-thap/redteam-c-stress-test.md); dưới đây là bản tinh chỉnh theo V2 đã giải quyết `HOT FILE`, mâu thuẫn `QC1.1` và `ANTI-2` non-code.)*

1. **Ví dụ 1 — `11-19-0046:T2.3` (`pre_tool_use.rs` 9 cổng, `632` dòng) · `5/14` → `14/14`:**
   - **Trước (`17` dòng, `~408` tok, `5/14`):** `1` task nhồi `9` cổng (gắn nhầm `UNFINISHED` vào `PreToolUse`), sai return type `HookDecision`, `0` assert.
   - **Sau theo V2 (`T2.3a..c` đặt cùng file với `R15-Full`, `~78` dòng, `~1,700` tok, `14/14`):** Scaffolder chạy với `--from-spec <spec.md> --refs hooks/rust/tdq-dispatch/src/protocol.rs,storage.rs,command_parser.rs` (vượt bẫy Greenfield `ND-2`), ghi rõ `Trước → Sau` từng nhóm cổng (`handle_edit_tool`, `handle_command_tool` giữ đúng thứ tự ưu tiên `READONLY → STATE → safety → branch → APPROVE → python_gate`, `handle_mcp_tool` bọc `Arguments` với `wrap_overwrite`), kèm `>= 3` `assert_eq!`/`matches!` mỗi task. Vì cùng chạm `pre_tool_use.rs`, cảnh báo `> 4` symbol mới báo từ Pass 1 để gom vào tuần tự sạch.
2. **Ví dụ 2 — `11-19-1632:T2.1` + `QC1.1` (8 file Rust + Python 3.9 fix) · `8/14` & `2/14` → `14/14` & `13/14`:**
   - **Trước:** `T2.1` nhồi `8` file vào `1` task (`8/14`); `QC1.1` viết `3` dòng trần không neo (`2/14`), chạy test trên Python `3.13` thay vì kiểm AST `3.9`.
   - **Sau theo V2:**
     - `T2.1`: Pass 1 tách việc thêm `pub mod pre_invocation; pub mod post_invocation;` vào task hợp đồng `events/mod.rs` ở Wave sớm (`ND-1`), nhờ đó `T2.1a` (`post_invocation.rs`), `T2.1b` (`pre_invocation.rs`), `T2.1c` (`command_parser.rs` + `post_tool_use.rs`), `T2.1d` (`session_start.rs` + `stop_streak.rs`), và `T2.1e..f` (`pre_tool_use.rs`) không còn nổ `HOT FILE` ở `events/mod.rs`, đạt `14/14`.
     - `QC1.1`: Nhờ ngoại lệ **Uniform Mechanical Sweep** (`ND-5`) + profile **`R15-Compact` (`5` trường, `ND-4`)** + nhãn **`Sinh ra:`** cho `plugins/tdq-workflow-agy/`, toàn bộ `QC1.1` chỉ gói gọn thành **`1` task sweep (`14` dòng thay vì bị xé thành `45` dòng / `3` task!)** mà vẫn có đủ neo dòng docstring/import `4` file, kiểm `ast.walk` không có `isinstance(..., A | B)`, tái build AGY ở `Sinh ra:` và đạt **`13/14`**.
3. **Ví dụ 3 — `11-19-1457` (Quick Audit `ANTI-2`) & `11-16-0058` (Quick Code `muc_gat=full`) · `0/14` & `6.5/14` → `12/14` & `13/14`:**
   - **Trước:** `11-19-1457` viết `os.path.exists` cho file đầu vào, `assert True` ở `QC.1`, và đụng chung `Chạm:` ở `T1`/`T2` (`0/14`); `11-16-0058` lách `R15` bằng `1` dòng `- Đặc tả logic:` (`6.5/14`).
   - **Sau theo V2:** `11-19-1457` giữ `<= 36` dòng gọn gàng (`T1` tách sang `truoc-sau.archify.md`), bộ kiểm `ANTI-2` độc lập (`ND-4`) chặn ngay `assert True` & `os.path.exists`, ép `Test:` kiểm chữ ký/từ khóa thực chất (`12/14`). `11-16-0058` áp `R15-Compact` + `Sinh ra:` (`plugins/tdq-workflow-agy/**`) cho `T1a`, `T1b`, `T2` — gói gọn `~52` dòng (`<= 80` trần quick code), không bị ép nhảy sang `full` vì chỉ sửa gốc `3` file nguồn (`<= 4` file, `ND-5`), đạt **`13/14`**.

### 2.4. Lộ trình Triển khai Đề xuất V2 (3 Chặng cho Request `feature` Kế tiếp)

| Chặng | Phạm vi & File chạm chính | Kiểm định mở khóa |
|---|---|---|
| **Chặng 1 — Nền Parser, Scaffolder & R15 (`3a` Lớp 2 & 3)** | Vá `scripts/tdq_team.py` (`indent`, `in_fence`, cô lập `Chạm:`/`Tham chiếu:`/`Sinh ra:`, loại neo khỏi `plan_assignment_sha`, `canh_bao_lach_luat`, `_TASK_REF`, thêm `packet` + `tdq_ten_lenh.py`); tạo `scripts/tdq_plan_scaffold.py` (`--refs`, `--from-spec`, `--emit-cards`, `--verify-plan`, `--check-wave`); nâng `scripts/doc_lint.py` (`R15-Full/Compact`, `ANTI-2`, `EXT_CAU_HINH`, `R15_MOC`, `_r12_van_xuoi`, `--pair`, `SKILL_LINE_LIMITS["tdq-plan"]=128`) & `scripts/tdq_state.py` (`set plan_file`, `approve plan/quick`) & `tdq_eval.py` (`RE_TICK`). | Bộ test unit mới cho `tdq_plan_scaffold`, `doc_lint` R15-Strict/Compact/ANTI-2, `tdq_team packet`, `tdq_state`, cộng toàn bộ test cũ (`test_team_mode`, `test_rust_dispatch_parity`, `test_hooks_dual_protocol`) xanh 100%. |
| **Chặng 2 — Skill, Templates & Agents (`3a` Lớp 1)** | Tách sibling `qc-vong-fix.md`, `task-card-guide.md`; cập nhật `tdq-plan/SKILL.md`, `plan-template.md`, `plan-template-huong-dan.md`, `spec-template-huong-dan.md`, `quick-lane-mini.md`, `team-mode.md`, `team-mode-tra-cuu.md`, `qc.md`; gọt `agents/tdq-implementer.md`, nâng checklist `agents/tdq-reviewer.md`; cập nhật `tools/patches/agy_hooks.py` (`SUBAGENT_DISPATCH_GATE_PY`) & `tools/patches/skills_and_agents.py`. | `doc_lint.py skills` exit 0, `token_budget.py --kiem` (đo trên `anthropic-tokenizer`) exit 0 (`<= 3,500`), `doc_index.py`, `test_reference_mot_tang.py`, `test_agent_frontmatter.py`, `build_agy_plugin.py` + `agy.EXE plugin validate --strict` `findings: []`. |
| **Chặng 3 — Nghiệm thu E2E giả lập `2b` & Đóng gói** | Chạy nghiệm thu thử nghiệm `Two-Pass + --emit-cards + packet` trên `3` kịch bản mẫu (Greenfield, Multi-file Rust, Quick Code + Sweep), đồng bộ `build_portable.py --kiem`, chạy `tdq_test.py tron-bo` mức `full`/`ultra`. | `0` failed trên toàn repo, `doc_lint` & `i18n_check` sạch, `tdq_bench`/`evals` không hồi quy. |

---

## 3. Đã test gì

1. **Khảo sát & chấm điểm thực nghiệm nội bộ (`236` plan / `2,699` task):** Quét cấu trúc toàn bộ `docs/tdq/plan/*.md` (`225` plan trước `11-11` và `11` plan sau `11-11`), chấm sâu `7` chiều trên `48` task từ `12` plan đại diện, và đối chiếu `4` cặp `spec ↔ plan`.
2. **Kiểm toán mã nguồn trực tiếp (`skills/`, `agents/`, `scripts/`, `hooks/`, `tools/patches/`, `tests/`, `docs/tdq/token-budget.json`):** Xác minh chính xác từng dòng code, regex, token budget thực tế (`anthropic-tokenizer` vs `tiktoken`), và hành vi hook Python + Rust.
3. **Nghiên cứu đối chiếu khoa học ngoài (`Tavily`):** Đọc đối chiếu `4` góc nguồn ngoài (`Skeleton Coding`, `Aider`, `IFScale`, `Context Rot`, `Laban 2025`, `Anthropic Harness`, `Heym 1,133 commits`, `Superpowers #1120`).
4. **Fanout `3` luồng Red-Team độc lập (Vòng 2):** Chạy `3` subagent đọc-chỉ phản biện V1 về nhận thức (`A`), ràng buộc hệ thống/linter (`B`), và viết lại thực chiến `3` ca thất bại thật (`C`).
5. **Kiểm định linter & xác minh toàn vẹn tài liệu (`Q5`):** Chạy `scripts/doc_lint.py` trên toàn bộ tài liệu mới, kiểm `git status --porcelain` xác nhận `0` file mã nguồn ngoài `docs/` bị sửa, kiểm `tdq_archify.py verify` và truy vấn HTTP trực tiếp qua Tailscale Serve.
6. **Chạy trọn bộ test toàn repo (`QC-F1`..`QC-F4`, mức `full`):** Chạy `py -3 -X utf8 scripts/tdq_test.py tron-bo --workers 1 --fresh --reuse off` trên toàn bộ `215` module và kiểm `tdq_test.py so`.

---

## 4. Kết quả test

| Hạng mục kiểm | Công cụ / Phạm vi | Kết quả thực tế | Trạng thái |
|---|---|---|---|
| **Đo kiểm định lượng corpus (`Q1`)** | Quét `236` plan (`2,699` task) · chấm sâu `48` task × `7` chiều · `4` cặp `spec ↔ plan` | Khẳng định `20.8%` đạt chuẩn sau `11-11`, `58.3%` thiếu Trước→Sau, `60.9%` thiếu neo dòng, mega-task tăng `2.8×`; xác định `7` nguyên nhân gốc gắn `path:line` | **PASS** |
| **Kiểm phủ thiết kế V1 (`Q2`)** | `de-xuat-v1.md` cho `2b` (Weak Planner + Weak Executor) và `3a` (3 lớp) | Đủ `3` lớp (`Skill/Template/Agents`, `tdq_team.py`/`Scaffolder`/`Auto-Packet`, `R15-Strict`/`approve plan`) + `doc_lint` exit `0` | **PASS** |
| **Phản biện Red-Team Vòng 2 (`Q3`)** | `3` báo cáo độc lập `A`, `B`, `C` → tổng hợp `phan-bien-vong-2.md` | Thu `18` phát hiện cụ thể → hội tụ **`12` mã `ND-1`..`ND-12`** (`10` Cao, `2` TB), ánh xạ vá `100%` sang V2; tất cả file đạt `doc_lint` exit `0` | **PASS** |
| **Stress-test 3 ca Trước/Sau (`Q4`)** | `11-19-0046:T2.3`, `11-19-1632:T2.1`+`QC1.1`, `11-19-1457` & `11-16-0058` | Cả `3/3` ca chính nâng điểm từ **`5/14` → `14/14`**, **`8/14` & `2/14` → `14/14` & `13/14`**, **`0/14` & `6.5/14` → `12/14` & `13/14`** | **PASS** |
| **Linter, toàn vẹn repo & Archify (`Q5`)** | `doc_lint.py` trên toàn bộ tài liệu · `git status` · `tdq_archify.py verify` · Tailscale Serve | Mọi file `.md` mới đạt `0 violation(s), exit 0`; `0` sửa đổi ngoài `docs/`; bản Archify HTML ở trạng thái `current` (`valid=true`) và truy cập Tailscale `HTTP 200` | **PASS** |
| **Trọn bộ test toàn repo (`QC-F1..F4`)** | `py -3 -X utf8 scripts/tdq_test.py tron-bo --workers 1 --fresh --reuse off` (`215` module) · `tdq_test.py so` · `spec §5` | **`4,423 passed, 35 skipped, 2,721 subtests passed, 0 failed`** (`1305.73s` exec, wall `1317.93s`, `exit 0`); `tron_bo=1/2`, `bo_sot=0`; `0` vi phạm kiến trúc | **PASS** |

- **Đầu ra chính:** `phan-tich-vong-1.md`, `de-xuat-v1.md`, `redteam-a/b/c`, `phan-bien-vong-2.md`, báo cáo V2 này và `docs/tdq/qc/2026-11-19-2213-chi-tiet-plan-model-thap.md` · **Archify HTML:** `docs/tdq/reports/2026-11-19-2213-chi-tiet-plan-model-thap.html`
- **Giới hạn:** Request thuộc loại `docs` (`1a`) nên **chưa** sửa mã nguồn thật trong `skills/`, `scripts/`, `hooks/`, `agents/` và chưa chạy eval gọi LLM trả phí; hiệu quả thực tế của thiết kế V2 đã được chứng minh bằng thực nghiệm đối chiếu + stress-test cấu trúc `3` ca và sẽ được kiểm thử code/regression đầy đủ khi bạn mở request `feature` triển khai theo Lộ trình 3 Chặng ở mục `2.4`.
- **Lệch spec chờ duyệt:** không có.
- **Git:** đang ở nhánh `docs/chi-tiet-plan-model-thap` (chưa commit, chờ hỏi sau báo cáo).

## Thời gian

Request `2026-11-19-2213-chi-tiet-plan-model-thap` · lane full · opened at 2026-11-19T22:16:04+07:00

| Phase | Wall clock | API request | Tool wait | Background job | Observed union | Unattributed | Times entered |
|---|---|---|---|---|---|---|---|
| idle | 24s | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | 1 |
| analyze | 20 min | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | 1 |
| spec | 24 min | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | 1 |
| plan | 15 min | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | 1 |
| implement | 22 min | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | 1 |
| qc | 23 min | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | 1 |
| Total | 1h 43min | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] |  |

Model compute time is unavailable (`model_giay=null`). API includes network/provider latency; tool time is host wait. Observed metrics may overlap; unattributed time is not assumed user/model time.
Transcript attribution: project_window. Complete covers selected supported observations only.
- api_request_seconds: no_usable_source
- tool_call_seconds: no_usable_source
- background_job_seconds: no_usable_source
- observed_union_seconds: no_usable_observations
- unattributed_seconds: wall_minus_observed_union;no_usable_observations

## Thân PR (soạn sẵn)

**Tóm tắt:** Hoàn tất phân tích thực chứng `236` plan (`48` task × `7` chiều) kiểm chứng nhận định về độ thiếu cụ thể của TDQ plan cho model tier thấp, đề xuất kiến trúc `3` lớp cho mô hình End-to-End (`2b`), và chạy `3` luồng Red-Team phản biện độc lập (Vòng 2) chốt bản thiết kế V2 vá kín `12/12` nhược điểm kèm `3` ví dụ Trước/Sau và lộ trình triển khai `3` chặng.
**Trước/Sau:** [2026-11-19-2213-chi-tiet-plan-model-thap.html](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/reports/2026-11-19-2213-chi-tiet-plan-model-thap.html) (và preview spec [2026-11-19-2213-chi-tiet-plan-model-thap-preview.html](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/spec/2026-11-19-2213-chi-tiet-plan-model-thap-preview.html)).
**Đã kiểm:**
- `py -3 -X utf8 scripts/doc_lint.py` trên toàn bộ tài liệu mới (`brief`, `spec`, `plan`, `phan-tich-vong-1`, `de-xuat-v1`, `redteam-a/b/c`, `phan-bien-vong-2`, `report`, `qc`) → `0 violation(s), exit 0`.
- `py -3 -X utf8 scripts/tdq_test.py tron-bo --workers 1 --fresh --reuse off` (`215` module) → `4,423 passed, 35 skipped, 2,721 subtests passed, 0 failed` (`1317.93s`).
- `py -3 -X utf8 scripts/tdq_archify.py verify` + Tailscale Serve probe → `status=current`, `valid=true`, `HTTP 200`.
- `git diff --name-only` → chỉ phát sinh tệp trong `docs/` (`0` sửa đổi code/skill).
**Rủi ro hồi quy:** `0` rủi ro hồi quy runtime vì request này chỉ dừng ở tài liệu thiết kế `docs/`; toàn bộ `12` điểm gãy kỹ thuật tiềm ẩn khi hiện thực sang `skills/`, `scripts/`, `hooks/` và `agents/` đã được khoanh vùng sẵn trong bảng `ND-1`..`ND-12` và Chặng 1–3 của Lộ trình V2.
<!-- tdq-archify-binding:start -->
<!-- manifest: 2026-11-19-2213-chi-tiet-plan-model-thap.manifest.json -->
<!-- manifest_digest: d32aa17d3b924e813f4ad335eb667232052810fcfbb928dfc138958226dadab5 -->
<!-- tdq-archify-binding:end -->