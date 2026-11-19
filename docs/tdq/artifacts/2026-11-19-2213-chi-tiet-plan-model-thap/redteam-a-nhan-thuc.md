# Red-Team A — Phản biện Nhận thức Model Nhỏ & Rủi ro Weak Planner (Vòng 2)

Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

> **Vai trò & Phương pháp:** Kiểm định đối kháng độc lập bản đề xuất V1 (`de-xuat-v1.md`) dưới lăng kính tải nhận thức (`IFScale arXiv:2507.11538v1`, `Context Rot Chroma 2025`, `ProjDevBench arXiv:2602.01655v1`, `LLMKube`) khi **cả Weak Planner lẫn Weak Executor (`2b`)** đều chạy trên model tier thấp (`Flash`/`Haiku`/`Mini`).

---

### Nhược điểm A-1: Nghịch lý IFScale — V1 bảo vệ Executor nhưng làm chính Weak Planner "ngộ độc ngữ cảnh" và nổ quy mô plan 2–3× ngay lúc viết

- **Mức độ nghiêm trọng:** `Cao`
- **Bằng chứng cụ thể:**
  - `de-xuat-v1.md` ép Weak Planner vừa chẻ task theo trần `<= 2` file mã nguồn chính + `<= 3` hàm/symbol (`11-19-1632:T2.1` tách thành `3–4` task), vừa tự điền khuôn `Executable Task Card` gồm `8` nhóm trường (`~16–20` dòng/task). Một plan `10` task sẽ phình lên **`20–25+` task (`360–450` dòng, `~4,000–5,500` token chỉ riêng thân card)**.
  - Trong cùng `1` lượt viết (`Bước A → B → C`), Weak Planner phải giữ đồng thời `spec.md`, output JSON/Markdown của `tdq_plan_scaffold.py`, `plan-template.md`, `task-card-guide.md`, `tdq-plan/SKILL.md`, luật thụt lề `2` vs `4` khoảng trắng, và chạy `tdq_bench.py`.
  - Theo **IFScale** (`arXiv:2507.11538v1`), model nhỏ chịu **Exponential Decay** (rơi xuống `7–15%` qua *omission* + *primacy bias*); theo **Context Rot**, vùng giữa tụt `> 30%`. Thực chứng `phan-tich-vong-1.md` đã ghi nhận tỷ lệ rơi chi tiết từ Spec sang Plan là `~25%`. Khi tự viết tới task thứ `14–25`, chính Weak Planner sẽ viết sắc nét ở `T1.x` nhưng **bỏ sót `Cần:`, rớt đầu ra `spec §2`, hoặc thoái hóa thành văn xuôi rỗng ở các wave sau**.
- **Cơ chế sửa V2:**
  - Áp dụng **Two-Pass Skeleton-then-Card Authoring** trong `tdq-plan`:
    - *Pass 1 (DAG nhẹ):* Weak Planner chỉ sinh khung đồ thị task (`Tx.y`, `eNm`, `Chạm:`, `Cần:`, `Test:`), đối chiếu 1–1 với `spec §2` và chạy `tdq_team.py assign` để chốt ranh giới wave trước.
    - *Pass 2 (Scaffold-Prepopulated Card Expansion):* Bổ sung `tdq_plan_scaffold.py --emit-cards <plan.md>` tự đổ sẵn khung `Chạm:`, `Tham chiếu:`, `Vị trí neo:` và chữ ký hiện hữu từ đĩa vào từng Task Block; Weak Planner chỉ điền phần biến đổi (`Trước → Sau`, `Logic`, `Tiêu chí`) **từng phase một** bằng `edit_file`.

---

### Nhược điểm A-2: `tdq_plan_scaffold.py` mù hoàn toàn với file tạo mới (Greenfield), parser regex `.rs`/`.ts`/`.js` dễ sinh neo sai, và `rg` bỏ lọt dynamic dispatch

- **Mức độ nghiêm trọng:** `Cao`
- **Bằng chứng cụ thể:**
  - `de-xuat-v1.md` cấm Weak Planner tự nhớ tên/dòng, giao toàn quyền trích sự thật cho `tdq_plan_scaffold.py` bằng `--files <từ spec §2b>`, `ast.parse` (`.py`), regex/heading parser (`.rs`/`.ts`/`.js`), và `rg`/`grep`.
  - **Lỗ hổng 1 — Greenfield (`tạo mới`):** Theo **ProjDevBench**, agent sụp đổ mạnh nhất khi xây file mới chưa có trên đĩa (`Sonnet 4.5: 71.10 → 36.63`, `Gemini CLI: 74.57 → 35.53`). Với file chưa tồn tại (vd `pre_invocation.rs` ở `11-19-1632`), `ast.parse` và regex trả về **rỗng** — đúng điểm gây `~60%` thiếu schema trung gian.
  - **Lỗ hổng 2 — Regex `.rs/.ts/.js` tạo ảo giác có chứng nhận:** Regex không xử lý nổi `impl Trait<T>` nhiều dòng, macro `macro_rules!`, `#[cfg(...)]`, TS arrow/overloaded exports; khi regex cắt cụt chữ ký hoặc lệch `prev_sym`/`next_sym`, Weak Planner chép nguyên **neo hỏng** vào Task Card.
  - **Lỗ hổng 3 — Bỏ sót caller ngoài `§2b` & Dynamic Dispatch:** Truyền `--files <từ spec §2b>` bỏ lọt caller nằm ngoài `spec §2b` (trái với `find_references` toàn repo ở `tdq-plan/SKILL.md:58`), còn `rg` bỏ lọt bảng điều phối động (`hooks/scripts/dispatch.py`, `importlib`, dict mapping).
- **Cơ chế sửa V2:**
  - Ưu tiên đọc từ **LSP (`mcp_tdq-workflow-agy_lsp_*` / `lsp_module`)** hoặc AST; nếu rơi về regex fallback, gắn cờ bắt buộc `ANCHOR_CONFIDENCE: LOW` yêu cầu xác minh bằng `read_file`.
  - Quét callers trên **toàn bộ thư mục mã nguồn repo** và trích luôn các bảng dispatch/registry; với đường dẫn `tạo mới` (Greenfield), bắt buộc chạy `--from-spec <spec.md>` lấy hợp đồng chữ ký/schema từ `spec §3c` (báo lỗi thoát mã `1` nếu thiếu).

---

### Nhược điểm A-3: `Auto Task Packet` + `tdq-implementer.md` nhồi ~35–40 chỉ thị & snippet cắt cụt vượt ngưỡng IFScale của `Flash`, bẫy `edit_file` vào vòng retry mù

- **Mức độ nghiêm trọng:** `Cao`
- **Bằng chứng cụ thể:**
  - `plugins/tdq-workflow-agy/agents/tdq-implementer.md:1-70` (đã ép `model: flash` và tước sạch `LSP`, `grep_search`, `find_by_name` trong `tools/patches/skills_and_agents.py:45-50`) hiện đã chứa **~20 luật hành vi & mã ANTI riêng**.
  - V1 giữ nguyên khối này và **chồng thêm** vào `Auto Task Packet`: `9` trường giao việc + `<= 3` bất biến kiến trúc + `Executable Task Card` (`<= 5` bước `Logic` + `<= 5` `Luật cục bộ` + `3` `Test Oracle`) + **`<= 80` dòng snippet** trích `+-25` dòng quanh symbol neo → tổng cộng **~35–40 ràng buộc đồng thời**, rơi thẳng vào đường cong **Exponential Decay** (`IFScale`) và **Lost-in-the-Middle (`-30%`)**.
  - Hơn nữa, một task chạm `2` file code + `1` file test + `2` `Tham chiếu:` cần tối thiểu `150+` dòng nếu trích `+-25` dòng; trần `<= 80` dòng ép `tdq_team.py packet` **cắt cụt giữa thân hàm**. Theo **LLMKube**, model nhỏ tụt `20×` khi lỗi edit format → thiếu ngữ cảnh làm `Flash` kẹt vào vòng **retry mù** (`9/10 → 6/10`, chi phí `2×`).
- **Cơ chế sửa V2:**
  - Cắt gọt `tdq-implementer.md` xuống `<= 30` dòng (`<= 6` luật cốt lõi), xóa mọi chỉ thị trùng lặp với `RANH GIỚI` và phần tự tick plan.
  - Đổi cơ chế trích ngữ cảnh sang **Symbol-Span Extraction**: trích **trọn vẹn thân hàm/class đích** (`start_line..end_line` từ AST) + `3` dòng lân cận cho tối đa `2` file code, và các file `Tham chiếu:` **chỉ gửi `1` dòng signature**. Nếu vượt ngưỡng, xuất chỉ dẫn `READ-EXACT: read_file(path, StartLine, EndLine)`.
  - Đặt **Ngắt mạch Retry `<= 2` lần** trên `Flash`: lỗi test/edit liên tiếp `2` lần không tự viết lại toàn file mà trả `STATUS: blocked` để Leader chuyển `tdq-build-resolver` hoặc nâng bậc model.

---

### Nhược điểm A-4: `R15-Strict` & `ANTI-2` bằng regex vừa dễ bị "lách bằng văn bản giả", vừa đặt sai pha ở `approve plan` (gây sửa plan hậu duyệt và hở cổng `quick`)

- **Mức độ nghiêm trọng:** `Cao`
- **Bằng chứng cụ thể:**
  - **1. Lách regex ("R15 Theater 2.0"):** Chỉ cần chứa `` `...` `` hay `"trong"` là đạt neo (`trong main.py`), viết `"chưa xử lý đầu vào"` → `"đã xử lý đầu vào"` (`> 3` từ) là đạt `Trước → Sau`, viết `"theo tài liệu đặc tả đã duyệt"` thay cho `"theo spec §"` là né được từ khóa cấm, và viết `assert res is not None` là vượt kiểm `ANTI-2`; ngược lại bản vá `1–3` dòng bị ép `>= 2` bước `Logic` thừa thãi.
  - **2. Đặt sai pha tại `approve plan`:** Theo `tdq-plan/SKILL.md:103-106` và `tdq_state.py:2343, 2392-2394`, `approve plan` chạy **SAU KHI user đã chốt duyệt**. Chặn cứng lúc này buộc model sửa ngầm file plan sau khi user vừa duyệt xong.
  - **3. Hở cổng `quick-lane`:** Ở `scripts/tdq_state.py:2343, 2349`, lane `quick` chạy **`target == "quick"`** (`approve quick`), không dùng `target == "plan"` và không đặt `plan_file`, nên điều kiện `if target == "plan"` trong V1 **bỏ lọt 100% mini-plan sửa code**.
- **Cơ chế sửa V2:**
  - Dịch cổng R15 về **TRƯỚC lúc trình duyệt** (chạy tại `tdq_state.py set plan_file=...`, `doc_lint.py --pair` và chặn tiền duyệt nếu mini-plan/plan chưa sạch); ở `approve plan` lẫn `approve quick` (`target in ("plan", "quick")`), nếu phát hiện sửa trộm sau lúc trình thì từ chối rõ ràng.
  - Nâng cấp kiểm định bằng **`tdq_plan_scaffold.py --verify-plan`**: đối chiếu tồn tại symbol trên đĩa thật + phân tích cú pháp biểu thức `assert` (cấm `is not None`, `!= None`, `bool(x)` đơn độc) + miễn `>= 2` bước `Logic` cho task vá nhỏ `1` file (`<= 15` LOC).

---

### Nhược điểm A-5: Cắt lát cứng `<= 2` file code/task gây gãy biên dịch trong worktree, còn `JIT Wave Check` tự kích nổ khóa stale `plan_assignment_sha`

- **Mức độ nghiêm trọng:** `Cao`
- **Bằng chứng cụ thể:**
  - **1. Gãy test worktree ở module liên kết chặt:** Khi refactor chữ ký hàm có `3+` file caller (hoặc Rust crate kiểm type toàn cục như `11-19-1632:T2.1`), `edit_gate.py:242` (`ngoai_vung_khai`) cấm subagent Wave 1 sửa caller thứ 3 → worktree của Wave 1 không compile nổi / đỏ `tdq_test.py vung-cham` → `tdq_team.py merge` từ chối gộp! Weak Planner không tự nghĩ ra *compatibility shim* trung gian nếu không có luật hướng dẫn.
  - **2. `JIT Wave Check` xung đột với `plan_assignment_sha`:** Trong `scripts/tdq_team.py:260-285, 334-343`, `chieu_phan_cong()` băm **mọi dòng `t.text[1:]`** vào `plan_assignment_sha` (chỉ trừ `tiến độ:`/`status:`). Cập nhật `Vị trí neo:` giữa các wave theo V1 sẽ tự làm bản đồ phân công bị đánh dấu **STALE** và khóa lệnh `tdq_team.py wave` / `open`.
  - **3. Bỏ sót trôi chữ ký (Semantic Drift):** Chỉ kiểm tên symbol trong `Vị trí neo:` không bắt được việc Wave $k$ đổi tham số hoặc tên khóa JSON của Wave $k+1$.
- **Cơ chế sửa V2:**
  - Cho phép ngoại lệ rõ: giữ `<= 2` file code cho logic mới, nhưng mở lên **`<= 5` file** cho task đồng bộ caller thuần cơ học (`Loại: dong-bo-chu-ky`), hoặc bắt buộc Wave 1 giữ interface/shim tương thích ngược.
  - Loại trừ `Vị trí neo:` khỏi hàm băm `plan_assignment_sha` trong `tdq_team.py`; bổ sung trường `CONTRACT-DELTA:` ở output `tdq-implementer` để tự động đối chiếu lại cả chữ ký cho wave sau.

---

### Nhược điểm A-6: Điểm mù "Đồng cấp yếu" ở `tdq-reviewer` / `tdq-qc-tester` (`model: inherit`) và động lực nén task ở `quick-lane`

- **Mức độ nghiêm trọng:** `Trung bình`
- **Bằng chứng cụ thể:**
  - `tools/patches/skills_and_agents.py:55, 61` đặt `model: inherit` cho cả `tdq-reviewer.md` lẫn `tdq-qc-tester.md`. Trong chế độ End-to-End `2b`, model yếu tự viết plan rồi `tdq-reviewer` cũng chạy chính model yếu đó đánh giá chủ quan mức độ rõ ràng (`>= 0.80`) → dễ phê duyệt chéo lẫn nhau (rubber-stamping).
  - Ngưỡng `>= 3` task code trong `quick-lane` (`de-xuat-v1.md`) tạo động lực ngược cho Weak Planner **dồn 3–4 file vào 2 task** để khỏi phải chuyển sang quy trình `full` dài dòng.
- **Cơ chế sửa V2:**
  - Tầng chặn chất lượng ở `2b` phải dựa vào kiểm định xác định (`tdq_plan_scaffold.py --verify-plan` + `doc_lint` AST), không phụ thuộc vào đánh giá cảm tính của `tdq-reviewer` khi `model: inherit`; ghi nhận chính sách tách/nâng bậc model cho Reviewer & QC khi host cho phép (giống `tdq-security-reviewer: pro`).
  - Neo ngưỡng chuyển từ `quick` sang `full` theo **tổng số file code sửa (`> 4` file)** hoặc đụng kiến trúc liên module thay vì số lượng task code (`>= 3`), tránh phạt Planner khi chia nhỏ task đúng luật.
