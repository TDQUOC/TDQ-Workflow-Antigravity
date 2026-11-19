# Vòng 1 — Kiểm chứng Nhận định & Giải phẫu Nguyên nhân gốc (Model Tier Thấp End-to-End)

Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

> **Kết luận ngắn:** Nhận định của người dùng **ĐÚNG 100%** trên dữ liệu thực nghiệm (`236` plan / `2,699` task). Ngay cả sau đợt nâng cấp ngày `2026-11-11` (`Self-Contained Task Block` + Rule `R15`), mới chỉ **`20.8%` (`5/24`)** task được chấm sâu đạt chuẩn sẵn sàng cho model tier thấp (`>= 12/14`). Quan trọng hơn, giải phẫu cho thấy vấn đề tồn tại ở **cả 2 đầu (`2b` End-to-End)**: **Weak Planner** thiếu công cụ neo/phân rã nên viết "Task Block Theater" hoặc mega-task `>= 4` file, còn **Weak Executor** (`model: flash` không có LSP trên AGY) nhận task thiếu Trước → Sau, thiếu chữ ký/schema và thiếu Test Oracle cụ thể nên phải đoán mò.

---

## 1. Bằng chứng Thực nghiệm trên Toàn kho 236 Plan (2,699 Task)

Mốc chuyển lịch sử trong kho là request `2026-11-11-0230-task-block-va-model-tier-thap`, bổ sung khối 9 trường (`plan-template.md:50-66`), 4 chốt an toàn (`plan-template-huong-dan.md:47-53`) và Rule `R15` (`scripts/doc_lint.py:526-567`). Toàn bộ `236` file trong `docs/tdq/plan/*.md` chia làm `2` kỷ nguyên rõ rệt:

| Chỉ dấu cấu trúc (toàn kho `236` plan / `2,699` task) | Trước `2026-11-11` (`225` plan, `2,582` task) | Sau `2026-11-11` (`11` plan, `117` task) | Sau `11-11` — Chỉ task code (`n = 69`) | Độ hụt đáng chú ý |
|---|---|---|---|---|
| Có trường `Vị trí neo:` | `0.0%` (`0/2,582`) | `55.6%` (`65/117`) | `81.2%` (`56/69`) | **`18.8%`** task code vẫn thiếu |
| Có neo dòng / vùng dòng cụ thể (`dòng N`, `:N`) | `3.6%` (`94/2,582`) | `23.9%` (`28/117`) | `39.1%` (`27/69`) | **`60.9%`** task code vẫn thiếu |
| Có `Đặc tả kỹ thuật` / `Đặc tả logic` | `0.0%` (`0/2,582`) | `62.4%` (`73/117`) | — | Lọt ở quick-lane & QC |
| Có `Logic cốt lõi` | `0.0%` (`0/2,582`) | `62.4%` (`73/117`) | `91.3%` (`63/69`) | **`8.7%`** task code vẫn thiếu |
| Có khối `Tiêu chí:` assertion | `0.0%` (`0/2,582`) | `50.4%` (`59/117`) | `78.3%` (`54/69`) | **`21.7%`** task code vẫn thiếu |
| Có **Trước → Sau mức từng task** | `2.8%` (`72/2,582`) | **`0.9%` (`1/117`)** | — | Hầu như vắng mặt (`99.1%`) |
| **Mega-task chạm `>= 4` file** ở `Chạm:` | `4.9%` (`126/2,582`) | **`13.7%` (`16/117`)** | — | **Tăng `2.8×` sau `R15`** |
| Task sửa `QC` có Task Block chi tiết | `0.0%` (`0/151`) | **`23.5%` (`4/17`)** | — | **`76.5%`** vẫn là 1 dòng trần |

### 1.1. Chấm điểm sâu 7 chiều trên 48 Task đại diện (12 Plan × 2 Kỷ nguyên)

Thang chấm mỗi chiều: `2` = Tường minh / Đủ chạy độc lập trên model nhỏ · `1` = Mơ hồ / Mới đủ khung · `0` = Vắng mặt. Tổng tối đa `14`; ngưỡng sẵn sàng cho model tier thấp là `>= 12/14`.

| Chiều đánh giá độ rõ thực thi | Tất cả `48` task (`2`/`1`/`0`, TB) | Sau `11-11` (`n=24`, TB) | Sau `11-11` Core `full` (`n=19`, TB) | Trước `11-11` (`n=24`, TB) |
|---|---|---|---|---|
| **(a) Vị trí sửa chính xác** (file + symbol + neo) | `25.0%` / `47.9%` / `27.1%` (`0.98`) | `37.5%` / `37.5%` / `25.0%` (`1.12`) | `47.4%` / `42.1%` / `10.5%` (`1.37`) | `12.5%` / `58.3%` / `29.2%` (`0.83`) |
| **(b) Chuyển đổi Trước → Sau mức task** | **`16.7%`** / `29.2%` / **`54.2%`** (`0.62`) | **`20.8%`** / `20.8%` / **`58.3%`** (`0.62`) | `26.3%` / `26.3%` / **`47.4%`** (`0.79`) | `12.5%` / `37.5%` / `50.0%` (`0.62`) |
| **(c) Thuật toán / nhánh rẽ tường minh** | **`16.7%`** / `56.2%` / `27.1%` (`0.90`) | **`25.0%`** / `50.0%` / `25.0%` (`1.00`) | `31.6%` / `57.9%` / `10.5%` (`1.21`) | `8.3%` / `62.5%` / `29.2%` (`0.79`) |
| **(d) Công nghệ / API / chữ ký hàm chuẩn** | **`16.7%`** / `58.3%` / `25.0%` (`0.92`) | `33.3%` / `50.0%` / `16.7%` (`1.17`) | `42.1%` / `52.6%` / `5.3%` (`1.37`) | `0.0%` / `66.7%` / `33.3%` (`0.67`) |
| **(e) Ca góc hiểm / ràng buộc / bất biến** | `20.8%` / `52.1%` / `27.1%` (`0.94`) | `41.7%` / `33.3%` / `25.0%` (`1.17`) | `52.6%` / `42.1%` / `5.3%` (`1.47`) | `0.0%` / `70.8%` / `29.2%` (`0.71`) |
| **(f) Kỳ vọng đầu ra sau task** | `25.0%` / `68.8%` / `6.2%` (`1.19`) | `50.0%` / `45.8%` / `4.2%` (`1.46`) | `63.2%` / `36.8%` / `0.0%` (`1.63`) | `0.0%` / `91.7%` / `8.3%` (`0.92`) |
| **(g) Test Oracle cụ thể (`input → assert`)** | **`14.6%`** / `41.7%` / **`43.8%`** (`0.71`) | **`25.0%`** / `37.5%` / **`37.5%`** (`0.88`) | `31.6%` / `47.4%` / **`21.1%`** (`1.11`) | `4.2%` / `45.8%` / `50.0%` (`0.54`) |
| **Tổng điểm trung bình (`/14`)** | **`6.25 / 14` (`44.6%`)** | **`7.42 / 14` (`53.0%`)** | **`8.95 / 14` (`63.9%`)** | **`5.08 / 14` (`36.3%`)** |
| **Tỉ lệ đạt chuẩn (`>=12`) / Khá (`7–11`) / Thiếu (`0–6`)** | **`10.4%`** / `29.2%` / **`60.4%`** | **`20.8%`** (`5/24`) / `33.3%` / `45.8%` | **`26.3%`** (`5/19`) / `42.1%` / `31.6%` | **`0.0%`** / `25.0%` / **`75.0%`** |

### 1.2. Đối chiếu Spec ↔ Plan trên 4 cặp thực tế

Khảo sát chéo `docs/tdq/spec/<slug>.md` và `docs/tdq/plan/<slug>.md` cho thấy phần chi tiết bị thiếu phân bổ làm `3` nhóm:

1. **Thiếu ở cả Spec lẫn Plan (`~60%`):** Chữ ký hàm trung gian, JSON/struct schema của state và file phụ trợ (vd `turn-meta-<sid>.json`, `pending-reminders-<sid>.jsonl`, `.tdq-lsp-module.json`), thứ tự ưu tiên giữa nhiều nhánh `if/elif`, và bộ test `input → assert` phủ đủ mọi nhánh (`2026-11-19-1632`, `2026-10-07-2225`).
2. **Có trong Spec nhưng bị đánh rơi khi viết Plan (`~25%`):** Spec §2b/§2c có số dòng (`storage.rs:39`, `agy_hooks.py:1715`) hoặc §3c có danh sách trường JSONL (`PLANNER_RESPONSE`, `ERROR_MESSAGE`), nhưng sang Plan lại viết tắt `"theo spec §3c"` (`2026-11-18-1346`) hoặc bỏ mất neo dòng (`2026-11-19-1632`, `2026-11-08-1207`).
3. **Ảo giác trong Spec truyền nguyên vào Plan (`~15%`):** Ở cặp `2026-11-19-0046-dong-rust-binary-hook`, Spec tự bịa tên sự kiện kiểu Claude (`UserPromptSubmit`, `StopStreak`) và khóa JSON sai (`explanation`), rồi Plan chép y nguyên sang `T2.3` và `T4.1`, dẫn thẳng tới sự cố bỏ sót `14/22` mã cổng và `2/6` sự kiện mà `2026-11-19-1457` phải đi điều tra lại.

---

## 2. Sáu Mẫu Lỗi Thực tế Đối xứng với Ba Mẫu Đạt Chuẩn

### 2.1. Sáu mẫu task thiếu đặc tả hoặc tạo "Task Block Theater"

1. **"Task Block Theater" — đủ 9 đầu mục nhưng rỗng logic (`2026-11-19-0046-dong-rust-binary-hook.md:155-171`, `5/14`):** `T2.3` kê `9` mã cổng (`APPROVE`, `GIT`, `TEAM`, `STATE`, `READONLY`, `VUNG`, `ZERO-POPUP`, `SUBAGENT`, `UNFINISHED`) trong `Ràng buộc:`, nhưng `Logic cốt lõi` chỉ viết `4` bước cho đúng `2` cổng cộng lệnh git/search, bỏ trắng cơ chế dò `language_id`, bỏ trắng JSON `overwrite`, và đặt `Tiêu chí: chặn đúng 100% các câu lệnh nguy hiểm` (không 1 câu `assert`).
2. **Mega-task nén `8` file vào `1` ô (`2026-11-19-1632-hybrid-hook-smart-hardening.md:86-101`, `8/14`):** `T2.1` chạm tới `8` file Rust + ~`12` cổng hành vi trong `1` task duy nhất; phần `Logic cốt lõi` rút gọn thành 3 câu liệt kê tên file (`Viết pre_invocation.rs, post_invocation.rs...`), thiếu chữ ký chi tiết của 2 file mới và chỉ có test assertion cho `2/12` cổng.
3. **Task sửa QC bỏ qua toàn bộ Task Block (`2026-11-19-1632-hybrid-hook-smart-hardening.md:219-221`, `2/14`):** `QC1.1` sửa tới `4` file `.py` + đóng gói plugin nhưng chỉ có dòng tiêu đề và `Chạm:`, không neo dòng, không phân biệt annotation vs `isinstance(x, A | B)` trên Python `3.9`, và chạy pytest bằng Python `3.13` cục bộ.
4. **Task sửa đa lỗi QC chỉ 1 dòng không có `Chạm:` (`2026-11-18-1814-toi-uu-hook-huong-dan.md:195`, `1/14`):** `QC2.1` gộp `6` bản vá bảo mật/concurrency (`TDQ:GIT`, `TDQ:TEAM`, `search_gate`, `TDQ:STATE`, fallback `> 64 KB`, khóa file) vào đúng `1` dòng không liệt kê `1` file chạm nào.
5. **Quick-lane bỏ qua Task Block & dính `ANTI-2` (`2026-11-19-1457-audit-sai-sot-noi-hook.md:13-14,27`, `0/14`):** Dòng `Test:` kiểm `os.path.exists(...)` và `QC.1` chạy `assert True`; ngoài ra plan quick sửa code `2026-11-16-0058-dat-mac-dinh-ponytail-full.md:17-19` chạm `5` file `.py` nhưng lách qua `R15` chỉ bằng `1` dòng `- Đặc tả logic:`.
6. **Plan cũ 1 dòng giấu phụ thuộc xuyên tầng (`2026-10-19-1630-an-cua-so-popup-cmd-windows.md:18-21`, `0/14` & `3/14`):** `T3` chạm `3` file ở cả `scripts/` lẫn `hooks/scripts/` nhưng không nêu tên hàm, không nhắc quy tắc `sys.path` từ `hooks/` sang `scripts/`, và `T4` chỉ viết `"Viết bộ unit test..."` không 1 kịch bản cụ thể.

### 2.2. Ba mẫu task đạt chuẩn thực thi (`14/14` & `13/14`)

Ngược lại, `2026-11-16-1953-fix-lsp-gate-mcp-routing.md:45-71` (`T1.1`, `14/14`), `:134-150` (`T3.1`, `14/14`) và `2026-11-18-1814-toi-uu-hook-huong-dan.md:40-53` (`T1.1`, `14/14`) chứng minh **model nhỏ làm tốt được nếu Task Card hội tụ 4 yếu tố**: (1) Neo chính xác tới tên hàm/biến liền kề (`Ngay trước LSP = re.compile(...)`), (2) Chữ ký/regex chuẩn kiểu `Structural Contract`, (3) Giải thuật rẽ nhánh tường minh theo thứ tự `if/elif`, và (4) Ít nhất `3–4` câu `assert` cụ thể có cả ca âm lẫn ca dương.

---

## 3. Giải phẫu 7 Nguyên nhân gốc (Gắn mã nguồn & Phân tách 2 Đầu `2b`)

| Mã | Nguyên nhân gốc (trích dẫn `path:line` đã xác minh) | Tác động lên **Weak Planner** | Tác động lên **Weak Executor** |
|---|---|---|---|
| **RC-1** | **Điểm mù nạp luật ở `tdq-plan/SKILL.md:39-67`:** thân `SKILL.md` (`121/121` dòng, hết chỗ) chỉ trỏ `plan-template-huong-dan.md` cho `eNm`, `Mode thực thi`, tự soát — **không hề nhắc** Self-Contained Task Block hay 4 chốt an toàn (`plan-template-huong-dan.md:40-53`). | Planner model nhỏ chỉ đọc `SKILL.md` nên bỏ qua hoàn toàn quy tắc phân tầng và 4 chốt an toàn, nhất là ở quick-lane & QC fix task (`76.5%` thiếu). | Nhận bản plan thô từ Planner mà không biết các chốt an toàn buộc phải tuân thủ. |
| **RC-2** | **Lỏng lẻo trong cấu trúc mẫu `plan-template.md:50-66`:** thiếu hẳn trường **Trước → Sau** (`0.9%` sau `11-11`), khuyến khích neo cứng thiếu symbol chuẩn, mặc định `Ràng buộc` theo kiểu toàn cục (`<= 40 dòng`, lệch chuẩn `<= 50` ở `soul.md:126`), và để mở `Logic cốt lõi` dạng văn xuôi mơ hồ. | Dễ sinh "Task Block Theater": điền đủ nhãn bằng chữ chung chung hoặc chép câu `"theo spec §..."`. Bị `mega-task` vì mẫu quá dài nên Planner gom `8` file vào `1` task. | Phải tự suy diễn input→output transform, tự đặt tên symbol mới, hoặc rơi vào drop ngầm khi task vượt quá `3` file. |
| **RC-3** | **Bug parser ở `scripts/tdq_team.py:175-179` & thiếu công cụ tự động:** `doc_plan()` quét regex `_PATH` trên **toàn bộ dòng `t.text`** (không riêng `Chạm:`), và `doc_plan` (`:173-174`) lẫn `doc_lint` (`:548-550`) cắt đứt task ngay nếu có dòng cột `0` (như code fence). | Planner muốn viết chi tiết tham chiếu file đọc hoặc đặt khối code/schema không thụt lề là lập tức làm nổ `HOT FILE` giả, bị ép `file-luat`, hoặc gãy `R15`. | Bị chuyển sang `tu_lam` mất song song hoặc nhận `VÙNG FILE` bị nhiễm file chỉ đọc. |
| **RC-4** | **R15 dễ lách và không nối cổng chặn (`scripts/doc_lint.py:526-567,602-637`; `scripts/tdq_state.py:2213-2238`):** R15 chỉ kiểm sự có mặt của `1/5` từ khóa (`đặc tả|logic|giải thuật|thuật toán|pseudo-code`), **bỏ sót `QCn.x`** (hướng dẫn `qc.md:78` bảo viết `**QCn.1**` không bắt buộc `Đặc tả`), không chạy ở `--pair`, và `approve plan` không chạy cổng R15. | Không có phanh máy kiểm lại bản nháp của Weak Planner; Task Block rỗng hay `1` dòng `- Đặc tả logic:` vẫn qua trót lọt. | Lĩnh trọn các plan rỗng ruột nhưng mang nhãn "đã pass lint". |
| **RC-5** | **AGY Plugin ép Executor chạy `model: flash` và tước sạch tool tìm kiếm (`tools/patches/skills_and_agents.py:45-50`):** bản AGY gán `model: "flash"` cho `tdq-implementer` và chỉ cấp `5` tool (`read_file`, `edit_file`, `write_file`, `run_command`, `send_message`), **tước `LSP`, `grep_search`, `find_by_name`** trong khi `tdq-build/SKILL.md:119-124` yêu cầu `find_symbol`. | Nếu Planner không chép sẵn bảng symbol tồn tại và chữ ký thật vào Task Card, Executor gần như bị "bịt mắt". | Subagent `flash` không tra được caller hay signature chéo file, phải chạy shell grep thủ công hoặc tự bịa API. |
| **RC-6** | **Thiếu Auto Task Packet & Mâu thuẫn giao việc (`team-mode.md:123-140` vs `agents/tdq-implementer.md:12-38` vs `subagent_dispatch_gate.py:8`):** `team-mode.md` đòi `9` trường (nhưng lại quên liệt kê `Mục tiêu` và `Cần`, cũng không truyền `docs/kien-truc.md` hay `Dùng/Để/Ra/Kiểm`), `agents/tdq-implementer.md` vẫn giữ khuôn `7` trường + tag cũ `(nN)` + lệnh tự tick trong worktree, còn hook AGY mới kiểm `5` nhãn tối thiểu. | Weak Planner làm leader rất dễ ghép thiếu ngữ cảnh hoặc truyền lệnh mâu thuẫn cho worker. | Mất 1–2 lượt hỏi/sửa lỗi vùng file, lỗi bất biến kiến trúc (`scripts/` không import `hooks/`), hoặc quên luật ngôn ngữ. |
| **RC-7** | **Lỗ hổng ở Quick-lane (`skills/tdq-intake/references/quick-lane-mini.md:17-26`):** `quick-lane-mini.md` chỉ có mẫu task `1` dòng + trần cứng `40` dòng cả file mini-plan, mâu thuẫn trực tiếp với yêu cầu Task Block đầy đủ khi quick-lane sửa code (`11-16-0058`). | Weak Planner chọn quick-lane cho sửa code sẽ mặc nhiên bỏ Task Block để khỏi vượt `40` dòng. | Weak Executor nhận task 1 dòng sửa `3–5` file code, tỉ lệ tạo test mù `ANTI-2` rất cao. |

---

## 4. Đối chiếu Nghiên cứu Khoa học Ngoài (`docs/tdq/research/2026-11-19-2213-chi-tiet-plan-model-thap.md`)

Bằng chứng từ các benchmark độc lập cảnh báo **hai thái cực đều chết người** khi tối ưu cho model tier thấp:

1. **Thứ thực sự kéo model nhỏ tăng vọt (`+23` đến `+58.4 pp`) là *Structural Contract*, KHÔNG phải văn xuôi dài:**
   - **Skeleton Coding** (`arXiv:2610.38214v1`): cung cấp bố cục file + chữ ký hàm + local contract + global invariants đẩy `GPT-5.6 Luna` từ `67% → 90%` (`SCBench`) và `21.1% → 79.5%` (`SDDBench`), chỉ kém model đầu bảng `5.0–8.2` pp nhưng rẻ hơn `15–26×` — trong khi đặc tả hành vi dạng văn xuôi (*behavioral prose*) chỉ tăng tối đa `9.4` pp và làm tăng code erosion (`0.41 → 0.43`).
   - **Aider Architect/Editor & 52 AI Coding Benchmarks:** viết **Contract trước** cho task `>= 3` file tiết kiệm `47–54%` chi phí; nén context bằng **AST signature extraction** giảm `91%` token với `0%` tụt chất lượng; còn **retry mù** làm chất lượng rơi `9/10 → 6/10` với chi phí `2×`.
2. **Nếu giải pháp V1 chỉ đơn thuần "ép viết càng dài càng tốt", model tier thấp sẽ sụp đổ vì 3 cơ chế:**
   - **IFScale Exponential Decay (`arXiv:2507.11538v1`):** khác với model reasoning (`Threshold Decay` tới `~150–200` chỉ thị), các model nhỏ (`Haiku`, `Flash`, `Mini`) rơi theo **đường cong hàm mũ** xuống `7–15%` khi nhồi nhiều chỉ thị đồng thời (quên bỏ sót và primacy bias). Giới hạn cứng cần thiết cho 1 Worker là **`<= 5–7` luật cục bộ** + tách task mỏng `1–2` file.
   - **Context Rot & Multi-Turn Degradation (Chroma 2025; Laban et al. 2025):** phần giữa ngữ cảnh dài tụt `> 30%`; thiếu contract ngay từ đầu gây mất trung bình `39%` hiệu năng (`+112%` unreliability).
   - **Cascade Error & Rule Rot (Anthropic Harness; Böckeler; Heym `1,133` commits):** chép code nguyên văn hoặc khóa số dòng tĩnh dễ trượt (*plan drift*) khiến lỗi ở Wave 1 lan dây chuyền xuống Wave 3; luật toàn cục dạng prose bị vi phạm `31%`, trong khi luật cục bộ **chỉ rõ file + nơi đặt thay thế + kiểm chứng tại chỗ** đạt **`100%` tuân thủ**.

---

## 5. Ma trận Tác động Đặc thù cho Mô hình `2b` (Cả Weak Planner & Weak Executor)

| Nút thắt | Với **Weak Planner** (không được tự bịa) | Với **Weak Executor** (không được tự đoán) |
|---|---|---|
| **Tìm kiếm & Neo vị trí** | Không được nhớ bằng trí nhớ hay đoán dòng → cần **Symbol/Anchor Scaffolder** chạy AST/LSP trích sẵn đường dẫn thật, chữ ký hiện hữu, danh sách callers. | Không có LSP trên AGY (`flash`) → cần nhận **tên symbol chính xác + snippet trích đoạn neo** ngay trong Task Packet. |
| **Phân rã & Dung lượng Task** | Dễ dồn nhiều file hoặc quên nhánh rẽ → cần quy trình `3` bước cơ học và **trần `<= 3` file/task** (vượt trần bị linter từ chối hoặc phải tách). | Dính `IFScale` & `omission` khi task `>= 4` file → giới hạn lát cắt mỏng (`1–2` file, `1–3` hàm) + khóa trạng thái **Trước → Sau**. |
| **Đặc tả Logic & Công nghệ** | Dễ sa vào văn xuôi trống rỗng → chỉ cần điền **Structural Contract** (chữ ký, schema I/O, cặp Trước → Sau, bảng `<= 5` bước nhánh rẽ) theo khuôn mẫu sẵn. | Dễ dính lỗi format/thư viện lạ → khóa sẵn **Công nghệ/API tái sử dụng** + **Cấm chép body dài**, tập trung vào biên hàm và edge cases. |
| **Kiểm thử & Giao việc** | Thường quên `Tiêu chí` hoặc viết `assert True` → cần **mục Test Oracle bắt buộc `input → expected` (cấm `ANTI-2`)** và cổng `approve plan` tự chấm trước khi chạy. | Không tự bịa test xuôi chiều code (`self-confirming tests`) → chạy đúng **Locked Test Oracle** theo chu kỳ `Red → Green` kèm luật giữ nguyên assertion. |
