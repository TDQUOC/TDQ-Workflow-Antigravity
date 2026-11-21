# Đề xuất cải thiện quy trình QC và kiểm thử TDQ theo hướng Dev-First, E2E-First

> **Tóm tắt nhanh:**
> - **Phản ánh của người dùng là đúng và được chứng minh bằng số liệu:** Gần một nửa số hạng mục QC (`48.8%`, `40/82` mục) kiểm giấy tờ và nghi thức nội bộ, gấp `4` lần mục kiểm hành vi E2E sống (`12.2%`) `[EV-001]`. Bộ `tron-bo` mặc định ép chạy `1` luồng mất trung vị `19.8` phút nhưng lại tắt kiểm thử `smoke` và `runtime` ở mức mặc định `full` `[EV-006]`, `[EV-007]`, `[EV-008]`.
> - **Nguyên nhân gốc nằm ở cơ chế gộp sai tầng:** TDQ đang trộn kiểm tra hành chính vào báo cáo cho người đọc, chưa tách tầng *Changed-Flow E2E Smoke* `<60` giây, và có `2` lỗi cấu hình ở `tdq_test.py` (`--workers 1` mặc định, thiếu `.ruff_cache` và `.html`) `[EV-011]`, `[EV-013]`.
> - **Đề xuất mô hình mới:** Không xóa kỷ luật lõi của TDQ mà đẩy xuống **Auto Meta-Gate** chạy ngầm (`1` dòng `PASS/FAIL`), thay mặt tiền QC bằng **Dev Behavior QC Card** đọc trong `10` giây, và chạy kiểm thử theo `3` tầng tốc độ với trọng tâm **Changed-Flow E2E Smoke**.

- **Request:** `2026-11-21-1438-cai-thien-qc-test-e2e` · **Loại:** `investigate` / `docs` · **Nhánh:** `docs/cai-thien-qc-test-e2e` · **Trạng thái sửa mã nguồn:** `Zero-Code-Touch` (không sửa code sản phẩm).

---

## 1. Trước request

Quy trình QC mặc định (`muc_qc = full`) chạy toàn bộ hơn `4.600` bài test tuần tự mất khoảng `20` phút `[EV-007]`, `[EV-008]` nhưng bỏ qua kiểm tra `smoke` và `runtime` sống `[EV-006]`. Biên bản QC trung bình dài `82.4` dòng (`~2,754` token) chứa tới `48.8%` hạng mục hành chính, câu hỏi OOP SOLID và bảng telemetry V2 `[unavailable]` `[EV-001]`, `[EV-003]`, `[EV-004]`. Kết quả là dev khó thấy luồng người dùng chạy ra sao và từng lọt lỗi runtime `v0.103.0` (`4,603` unit test xanh nhưng `8/8` subagent vỡ khi gọi thật) `[EV-010]`.

## 2. Sau request

Báo cáo hoàn tất kiểm toán `3` lớp quy trình TDQ, mổ xẻ toàn bộ `33` tệp của `C:\Users\admin\Documents\terterarmy-cli` và đối chiếu chuẩn ngành từ Playwright, Testing Trophy, Instawork TIA, `obra/superpowers` và `agent-browser` `[EV-014]`, `[EV-017]`, `[EV-019]`, `[EV-020]`, `[EV-022]`. Từ đó xác lập kiến trúc đề xuất **Dev-First, E2E-First** gồm `Auto Meta-Gate`, `Dev Behavior QC Card`, kiến trúc kiểm thử `3` tầng tốc độ, mẫu kịch bản plain-language và lộ trình `3` đợt triển khai kèm KPI đo được `[EV-024]`.

## 3. Đã test và kiểm chứng gì

- **Kiểm toán nội bộ TDQ (`T1.1`):** Đọc và phân loại `82` mục trong `8` biên bản `docs/tdq/qc/*.md` (`2026-11-20` đến `2026-11-21`), phân tích `179` bản ghi `docs/tdq/timing.jsonl`, `38` lượt chạy `docs/tdq/.tdq-test.jsonl`, và quét marker trên `222` tệp `tests/test_*.py` `[EV-001]`, `[EV-008]`, `[EV-009]`, `[EV-013]`.
- **Phân tích đối chuẩn `terterarmy-cli` (`T1.2`):** Đọc đủ `33` tệp ngoài `.git`, đối chiếu mẫu test `7–19` dòng, debug trace `4` lớp, bug board và script đồng bộ manifest `[EV-014]`, `[EV-015]`, `[EV-016]`.
- **Nghiên cứu chuẩn ngành (`T1.3`):** Truy vấn và trích xuất văn bản gốc vào `raw/01..04*.txt` từ `22` URL thuộc `4` nhóm chuẩn ngành lớn `[EV-017]`–`[EV-023]`.
- **Cổng bằng chứng & chuẩn tài liệu (`T3.1`):** Kiểm `100%` `[EV-001]`..`[EV-024]` khớp `evidence.jsonl` (`QC-I1`), đối chiếu phát ngôn với trích đoạn gốc (`QC-I2`), gắn nhãn độ tin cậy (`QC-I4`), chạy `doc_lint.py`, kiểm tra `Zero-Code-Touch` qua `git diff --name-only dev..HEAD` và xác thực Archify HTML.

## 4. Kết quả test và kiểm chứng

| Hạng mục đối chiếu | Thực tế đo được tại TDQ | Phán quyết & độ tin cậy |
| :--- | :--- | :--- |
| Mục kiểm hành chính vs E2E (`H1`) | `40/82` (`48.8%`) meta/doc vs `10/82` (`12.2%`) E2E; `0/8` dùng browser test `[EV-001]` | **Đúng** (`Verified`) |
| Tốc độ & độ lọt lỗi tích hợp (`H2`) | `tron-bo` trung vị `1,190.11s` (`19.8p`); `6/28` (`21.4%`) `INCOMPLETE`; ca `v0.103.0` pass `4,603` test vẫn vỡ `8/8` subagent `[EV-008]`, `[EV-010]` | **Đúng — nặng hơn dự đoán** (`Verified`) |
| Kịch bản plain-language (`H3`) | Đã có `Given-When-Then` trong `vision-test-loop.md` nhưng ẩn sau điều kiện DoD và thiếu mặt tiền cho dev `[EV-012]`, `[EV-014]` | **Đúng một phần** (`Verified`) |
| Phân tầng tốc độ theo rủi ro (`H4`) | `0/222` `tests/` có marker `smoke/e2e`; `vung-cham` chỉ lọc unit AST và `3/10` lượt rơi về full vì thiếu `.html` `[EV-013]` | **Đúng** (`Verified`) |

---

# Phần I — Chẩn đoán thực chứng TDQ (`H1`–`H4`) và phần lõi cần giữ

## I.1. Giải đáp trực diện: QC của TDQ có hàn lâm và lệch trọng tâm không?

Câu trả lời dựa trên số liệu đo thật là **CÓ**, đặc biệt ở phần trình bày báo cáo và cách cấu hình lệnh kiểm thử mặc định (`Verified`):

1. **Quá nhiều thủ tục hành chính che mất kết quả chạy thật (`H1` — Đúng, `Verified`):**
   - Trong `8` biên bản QC gần nhất (`659` dòng, trung bình `82.4` dòng / `~2,754` token mỗi file), **`40/82` hạng mục (`48.8%`)** chỉ xác minh giấy tờ, quy trình, `doc_lint`, `token_budget`, hoặc tự vấn lý thuyết, trong khi chỉ **`10/82` (`12.2%`)** kiểm hành vi sống trên runtime thật `[EV-001]`.
   - `QC-F4` bắt buộc trả lời `5` câu hỏi SOLID hướng đối tượng (`SRP`, `OCP`, `LSP`, `ISP`, `DIP`) trong `clean-code.md` sau mỗi lần sửa mã nguồn, dù đa phần script TDQ viết theo hàm `[EV-002]`, `[EV-003]`.
   - Mẫu `report-template.md` hiện đẩy thêm bảng telemetry V2 mà trên Antigravity 2.0 cả `5` cột đều in `— [unavailable]`, làm người đọc phải lướt qua nhiều bảng rỗng trước khi thấy kết quả chính `[EV-004]`.
   - Ví dụ điển hình: request chỉnh định dạng hiển thị (`0917`) tốn `1,327.59s` chạy `tron-bo`, gán `6/9` mục kiểm giấy tờ nhưng `0/9` mục kiểm thử cách người dùng nhìn thấy output `[EV-005]`.
   - **Điểm giới hạn công bằng:** Ở các request sửa lõi nặng (`1230`, `0217`, `1034`, `1253`), TDQ vẫn tự chạy `10` probe runtime thật (`SSH`, binary, subagent) `[EV-001]`. Như vậy đội ngũ không bỏ kiểm kỹ thuật, mà đang để **lớp thủ tục bọc dày đặc che mất trọng tâm**.

2. **Chậm vì chạy tuần tự và mù tích hợp sống ở mức mặc định (`H2` — Đúng, `Verified`):**
   - Bảng `muc_qc` ở `skills/tdq-build/references/qc.md` tắt cả `smoke test = KHÔNG` lẫn `runtime test = KHÔNG` ở mức mặc định `full`, chỉ mở khi người dùng chọn `ultra` `[EV-006]`.
   - Đồng thời `qc.md:99` ép lệnh `tdq_test.py tron-bo --workers 1 --fresh --reuse off` `[EV-007]`. Số liệu `28` lượt `tron-bo` cho thấy trung vị lên tới **`1,190.11s` (`~19.8` phút)** — nặng gấp gần `4` lần ước tính ban đầu (`~5` phút) — với pha `qc` tiêu chuẩn tốn trung vị **`1,518.0s` (`~25.3` phút)** `[EV-008]`, `[EV-009]`.
   - Đáng chú ý, tỷ lệ `tron-bo` bị hủy thành `INCOMPLETE` là **`6/28` (`21.4%`)** `[EV-008]`. Ở đợt `v0.103.1`, bật `--workers 6` rút được thời gian chạy xuống **`314.31s`** (nhanh hơn `4.2x`), nhưng lượt trước đó chạy đủ `4,605` bài test vẫn mất oan `325.82s` bị gắn `INCOMPLETE` vì `.ruff_cache` không nằm trong `EXCLUDED_DIRS` `[EV-011]`.
   - Hệ quả thực tế rõ nhất là sự cố **`v0.103.0`**: bộ `tron-bo` pass **`4,603` bài trong `1,332.27s`** và `agy validate` trả `0` lỗi, nhưng ngay sau khi cài plugin thì **`8/8` subagent vỡ lập tức** khi gọi `invoke_subagent` thật vì unit test tự khóa theo danh sách tool cũ và `tdq-qc-tester` đọc từ cache cũ `[EV-010]`.

3. **Mảnh ghép E2E đã có nhưng bị giấu và khó đọc với dev (`H3` — Đúng một phần, `Verified`):**
   - TDQ không hề thiếu lý thuyết kiểm thử hành vi: `vision-test-loop.md` đã viết sẵn mô hình `Given - When - Then` `3` tầng và `tdq-browser-test` có quy trình `5` lớp qua Chrome DevTools MCP `[EV-012]`.
   - Tuy nhiên, cả hai chỉ kích hoạt *"when the DoD reaches them"*, dẫn tới **`0/8` biên bản gần nhất chạy browser test** `[EV-001]`, `[EV-012]`. Giao diện QC (`qc.md`) vẫn là log CLI và bảng ký hiệu agent, thay vì kịch bản người dùng đọc `10` giây là hiểu `[EV-014]`.

4. **Chưa có tầng kiểm thử theo luồng thay đổi (`H4` — Đúng, `Verified`):**
   - Toàn bộ `222` tệp `tests/test_*.py` chỉ có `15` tệp dùng `pytest.mark` (`parametrize`/`skipif`), và **`0` tệp phân tầng `smoke` hay `e2e`** `[EV-013]`.
   - Lệnh `vung-cham` rất hiệu quả khi trúng vùng ảnh hưởng (`7/10` lượt chỉ mất `5.47s`–`64.73s`), nhưng `3/10` lượt bị rơi về `tron-bo` (tới `1,386.3s`) một phần vì `DATA_EXTS` trong `tdq_test.py` bỏ sót `.html` `[EV-013]`. Quan trọng hơn, `vung-cham` chỉ lọc file unit theo đồ thị AST, chưa có khái niệm chạy **Changed-Flow E2E Smoke `<60s`** theo rủi ro hành vi.

## I.2. Năm chốt bảo vệ cốt lõi của TDQ CẦN GIỮ LẠI (chuyển sang tự động hóa ngầm)

Việc cải tổ QC không được phép làm tụt chất lượng. `5` cơ chế đã chứng minh hiệu quả chặn lỗi của TDQ cần **giữ nguyên 100% logic chặn**, chỉ rút khỏi văn bản báo cáo cho dev đọc `[EV-024]` (`Verified`):

- **`TDQ_LOG=1/0` trên `stderr`:** Giữ cơ chế log ISO để truy vết khi có lỗi; thay vì dán `50` dòng dump log vào biên bản QC, chỉ trích `5–10` dòng lỗi khi fail `[EV-024]`.
- **Khóa toàn vẹn receipt `tdq_test.py` (`SHA-256`, `bo_sot`, `source_before/after`):** Giữ nguyên cơ chế chống báo xanh giả khi mã nguồn bị sửa giữa chừng, đồng thời vá ngay `.ruff_cache` vào `EXCLUDED_DIRS` và `.html` vào `DATA_EXTS` `[EV-011]`, `[EV-013]`, `[EV-024]`.
- **Guards runtime `[TDQ:GIT]`, `[TDQ:STATE]`, `[TDQ:READONLY]`:** Để Rust hook và CLI chặn tự động ở tầng thực thi; chỉ hiện cảnh báo trong QC nếu có vi phạm `[EV-024]`.
- **Rust `tdq-dispatch` parity + latency (`~14.8ms`):** Chỉ tự kích hoạt test parity và benchmark khi git diff chạm `hooks/` hoặc `tools/patches/` `[EV-024]`.
- **Bán kính AST `vung-cham` + `doc_lint.py` + `ANTI-1..6`:** Đóng gói kiểm tra tĩnh vào `1` dòng trạng thái của **Auto Meta-Gate** để vừa ngăn trôi tài liệu `[EV-016]` vừa giữ giao diện QC gọn sạch `[EV-024]`.

---

# Phần II — Đối chiếu TDQ với `terterarmy-cli` và chuẩn ngành quốc tế

Để tìm lời giải vừa nhanh vừa chính xác, đội kiểm toán đối chiếu TDQ trực tiếp với cấu trúc thực dụng của `C:\Users\admin\Documents\terterarmy-cli` và `4` nhóm chuẩn ngành đang dẫn đầu giai đoạn 2025–2026 (`Verified`):

| Trục thiết kế | Thực trạng TDQ hiện nay | `terterarmy-cli` (`33` tệp) | Chuẩn ngành (`Playwright`, `Testing Trophy`, `TIA`, `Superpowers`) | Định hướng áp dụng cho TDQ |
| :--- | :--- | :--- | :--- | :--- |
| **Cách viết kịch bản test** | Bảng DoD + cụm `R15-Compact` hướng tới agent `[EV-001]` | Kịch bản plain-language **`7–19` dòng** (`1 Goal` + `3–10` bước `act`/`assert`), đọc `10s` hiểu `[EV-014]` | **Playwright Test Agents** tách `Planner` (viết plan hành vi trên app thật) khỏi `Generator` (xác minh selector sống trước khi ghi code test) `[EV-017]` | Giữ kế hoạch kỹ thuật cho implementer, nhưng xuất kèm **kịch bản hành vi ngắn** làm đầu vào cho QC và dev |
| **Định dạng báo cáo cho dev** | Trung bình `82.4` dòng lặp lại 3–4 tầng + `5` cột V2 `[unavailable]` `[EV-004]` | Mẫu `reporting-template.md` **`26` dòng**: `Verdict`, `Failures` (kèm Severity + `Repro steps`), `Pass/Skip` `[EV-015]` | **`obra/superpowers`** thay checklist bằng **Iron Law + 5-step Gate Function** (`IDENTIFY → RUN → READ → VERIFY → CLAIM`) `[EV-022]` | Gom meta-check vào **Auto Meta-Gate** `1` dòng; mặt tiền hiển thị **Dev Behavior QC Card** gọn `1` màn hình |
| **Tỷ trọng các tầng test** | Nặng `tron-bo` unit/static (`4,600+` cases), tắt `smoke`/`runtime` ở `full` `[EV-006]`, `[EV-008]` | Tập trung `100%` vào luồng dùng thật trên browser + debug trace `4` lớp (`console`, `network`, `DOM`, `trace`) `[EV-015]` | **Testing Trophy & Google Test Sizes** giảm mock nặng, ưu tiên **Integration (`Medium`)** + **Critical E2E (`Large`)** hermetic `[EV-019]` | Bật mặc định **Changed-Flow E2E Smoke** ở `muc_qc = full`; test unit phải ghép với probe thật của luồng thay đổi |
| **Chọn vùng chạy & tốc độ** | `--workers 1` (`~19.8p`); `vung-cham` chỉ lọc unit AST; `0` marker `smoke/e2e` `[EV-007]`, `[EV-013]` | Script bash `check-plugin-manifests.sh` kiểm `9` manifest trong `~1s` `[EV-016]` | **Instawork Testmon TIA** giảm **2x** thời gian test PR (`Single-source` `[EV-020]`); `pytest -m smoke --tb=short` fail-fast; loại test thừa/flaky khỏi smoke `[EV-021]` | Vá `--workers auto` (`~5p` thay `20p`), gắn `@pytest.mark.smoke` / `e2e`, chạy `<60s` theo luồng chạm trước |
| **Kiểm thử giao diện (Browser)** | `tdq-browser-test` & `vision-test-loop` đòi so pixel nặng nhưng `0/8` ca được dùng `[EV-001]`, `[EV-012]` | Bắt đầu từ snapshot cấu trúc trang trước khi click, chụp trace khi fail `[EV-014]`, `[EV-015]` | **Playwright MCP** & **`agent-browser`** dùng **Accessibility Tree Snapshot + ref**, fail-closed khi phần tử bị che và đọc `console`/`errors` `[EV-018]`, `[EV-023]` | Đổi mặc định `tdq-browser-test` sang **Accessibility Snapshot** (nhẹ token, ít flaky), chỉ chụp ảnh/diff khi debug fail |
| **Chống trôi tài liệu & gian lận** | Mạnh ở `doc_lint.py`, SHA-256 receipt và hooks `[EV-024]` | **Điểm yếu của `terterarmy-cli`:** `BUG_BOARD.md` bị ghi sai cờ CLI vì không có lint tài liệu `[EV-016]` | Không cho AI healer tự sửa assertion để pass giả `[EV-017]`; đối chiếu VCS diff thật `[EV-022]` | **Giữ nguyên `doc_lint.py` và receipt TDQ** làm hàng rào bắt buộc mà ngay cả dự án ngoài đang thiếu |

---

# Phần III — Thiết kế mô hình QC/E2E mới "Dev-First, E2E-First"

Mô hình đề xuất giữ nguyên xương sống kỷ luật của TDQ (`QC-I1/I2/I4`, `TDQ_LOG`, receipt, hooks), nhưng đảo ngược trải nghiệm sang **thấy hành vi thật trước, thủ tục tự động chạy sau**.

1. **Dev Diff** → **Tầng 0: Auto Meta-Gate** (`<10s`, ẩn khi PASS) → **Tầng 1: Fast Loop** (`<15s`, AST `vung-cham`).
2. **Tầng 2: Changed-Flow E2E Smoke** (`<60s`, live probe + Accessibility Tree Snapshot) → xuất **Dev Behavior QC Card** (`10s` đọc hiểu).
3. **Tầng 3: Full Regression Gate** (`--workers auto`, `<=5–6p`) → chỉ kích hoạt khi chạm lõi dùng chung, compiler hoặc trước khi merge/release.

## III.1. Tầng 0 — Auto Meta-Gate (ẩn thủ tục vào 1 dòng PASS/FAIL)

1. **Tự động hóa `doc_lint`, `token_budget`, `i18n_check`, `git` guard và `manifest sync`:**
   - Thay vì chiếm `48.8%` hạng mục trong biên bản QC `[EV-001]`, các kiểm tra này chạy thành `1` lệnh gate tự động và xuất đúng `1` dòng trạng thái (`Auto Meta-Gate: PASS (6/6 checks, 3.2s)`). Chỉ khi `FAIL` mới bung chi tiết lỗi.
2. **Xóa `QC-F4` OOP cứng nhắc cho tác vụ phi OOP (`Inferred` từ `[EV-002]`, `[EV-003]`):**
   - Chỉ kích hoạt câu hỏi thiết kế khi diff thêm module kiến trúc mới hoặc tạo class mới; thay `5` câu hỏi OOP bằng `3` câu kiểm thực dụng cho script/plugin: *(1) Không nuốt lỗi âm thầm (fail-closed), (2) Không trùng lặp logic, (3) Hàm mới không phình quá ngưỡng*.
3. **Ẩn cột `[unavailable]` theo host (`Inferred` từ `[EV-004]`):**
   - Trên Antigravity 2.0, `tdq_timing.py` tự ẩn `5` cột telemetry chưa có nguồn dữ liệu thay vì in `— [unavailable]` trên mọi dòng báo cáo.

## III.2. Dev Behavior QC Card — Chuẩn báo cáo đọc 10 giây hiểu ngay

Mọi biên bản QC cho người đọc sẽ đặt **Thẻ Hành Vi (Dev Behavior QC Card)** ngay đầu tệp, thay cho việc mở đầu bằng bảng ký hiệu quy trình (`Verified` về nguyên lý `obra/superpowers` `[EV-022]` + `reporting-template.md` `[EV-015]`):

- **4 câu hỏi bắt buộc trong Card:**
  1. **Luồng người dùng nào vừa thay đổi?** (mô tả bằng ngôn ngữ đời thường, không dùng mã nội bộ)
  2. **Đã chạy thử thật như thế nào?** (`Before → After` lệnh thực thi trên môi trường thật, không chấp nhận kết luận từ mock hoặc cache cũ) `[EV-010]`
  3. **Kết quả & bằng chứng tươi ngay trong lượt này là gì?** (`Exit code`, con số thật, hoặc kết quả snapshot/console/errors theo Iron Law `5` bước `[EV-022]`)
  4. **Rủi ro hoặc luồng nào CHƯA kiểm chứng?** (ghi rõ vùng ngoài phạm vi để dev biết ngay)

### Ví dụ minh họa `Trước → Sau` trên chính sự cố `v0.103.0` → `v0.103.1`

- **TRƯỚC (Kiểu cũ trong `v0.103.0` `[EV-010]`):**
  - Bảng ghi `11` dòng dài gồm `Q1..Q7` + `QC-F1..F4`, `tron-bo --workers 1` báo `4,603 passed (1332.27s)`, `agy plugin validate --strict` sạch, `QC-F4` `5/5` SOLID đạt → chốt `PASS everything`. Kết quả thực tế: **`8/8` subagent vỡ ngay khi bật chat thật**.
- **SAU (Dev Behavior QC Card đề xuất):**
```markdown
## Dev Behavior QC Card — Fix subagent tool allowlist (v0.103.1)
- Meta-Gate: PASS (doc_lint, token-budget, TDQ_LOG, clean git — chạy ngầm 4.1s)
- Luồng người dùng đổi: Mở gói plugin vừa cài -> gọi live `invoke_subagent` tới 8 role subagent.
- Chạy thử thật (Fresh Runtime Evidence):
  - Trước fix (v0.103.0): `invoke_subagent(tdq-explorer)` -> FAIL (`unknown component: call_mcp_tool`).
  - Sau fix (v0.103.1): Build bundle mới -> gọi live `invoke_subagent(tdq-explorer)` -> PASS (session `4b121235` đọc file & nhắn trả về trong 8s).
  - Rà toàn bộ 8/8 file `plugins/tdq-workflow-agy/agents/tdq-*.md` sau compile -> 0 tool lạ.
- Suite tự động: Changed-Flow E2E Smoke PASS (24s) · Full Suite `--workers 6` PASS (4,641 passed, 314.31s).
- Rủi ro còn lại: Chưa thử live đồng thời cả 7 role còn lại sau v0.103.1 (chỉ kiểm tĩnh frontmatter).
```
Chỉ mất **10 giây** để bất kỳ dev nào nhìn thấy giá trị kiểm chứng thật và điểm rủi ro còn lại.

## III.3. Kiến trúc kiểm thử `3` tầng tốc độ & Changed-Flow E2E Smoke

| Tầng kiểm thử | Mục tiêu & thời lượng | Phạm vi chạy | Cài đặt kỹ thuật cụ thể |
| :--- | :--- | :--- | :--- |
| **Tầng 1: Fast Inner Loop** | Phản hồi ngay trong lúc dev/agent sửa từng task (**`< 15 giây`**) `[EV-013]`, `[EV-020]` | Chạy ngay sau mỗi thay đổi code cục bộ | Dùng `tdq_test.py vung-cham` + **bản vá bắt buộc**: thêm `.html`/`.htm` vào `DATA_EXTS` để không rơi nhầm về full `[EV-013]`, và thêm `.ruff_cache` vào `EXCLUDED_DIRS` để không hủy nhầm receipt thành `INCOMPLETE` `[EV-011]`. |
| **Tầng 2: Changed-Flow E2E Smoke** *(trọng tâm mới)* | Khóa lỗi tích hợp sống & UI/CLI theo **đúng luồng vừa sửa** (**`< 60 giây`**) `[EV-010]`, `[EV-021]` | **Bật mặc định ở `muc_qc = full`** (không còn tắt như hiện tại `[EV-006]`) | (1) Gắn `@pytest.mark.smoke` / `@pytest.mark.e2e` phân tách với `tests/` (`0/222` hiện tại `[EV-013]`); (2) Bảng map **Thư mục chạm → E2E Smoke bắt buộc**: ví dụ sửa `agents/` hoặc `tools/patches/` phải chạy probe `invoke_subagent` / compiler output thật; sửa `hooks/` chạy `tdq-dispatch.exe` live; sửa HTML/UI chạy `tdq-browser-test` bằng **Accessibility Tree Snapshot (`ref`) + `console`/`errors` fail-closed** `[EV-018]`, `[EV-023]`; (3) Tuân thủ kỷ luật *Deletion* `[EV-021]`: bài test flaky bị loại ngay khỏi gói smoke. |
| **Tầng 3: Full Regression & Release Gate** | Toàn bộ regression suite (`4,600+` tests) (**`~5–6 phút`**) `[EV-011]` | **Chỉ bắt buộc** khi: (a) chạm lõi dùng chung (`tdq_state`, `tdq_test`, `hooks/rust`), (b) sửa công thức compiler, hoặc (c) trước merge/bump version release | Bỏ ép `--workers 1` trong `qc.md:99` `[EV-007]`, đổi sang `--workers auto` (giới hạn an toàn `min(6, cpu_count)`), giữ nguyên `TDQ_LOG` và receipt SHA-256 `[EV-024]`. |

## III.4. Mẫu kịch bản Plain-Language, Bug Board có lint & tích hợp opt-in

- **Kịch bản E2E Plain-Language (học `terterarmy-cli` `[EV-014]` + Playwright Planner `[EV-017]`):**
  - Với mọi request có giao diện web hoặc CLI đa bước, lập sẵn file kịch bản `7–19` dòng gồm `1 Goal` + `3–10` bước `Thao tác (act) → Kết quả mong đợi (assert)` tại `docs/tdq/scenarios/<slug>.md`, tách rời bước lập kịch bản (`Planner`) khỏi bước chạy xác minh (`Runner`).
- **Live Bug Board có kiểm lint chống trôi tài liệu (`Inferred` từ `[EV-016]`):**
  - Lưu lỗi lặp lại trong quá trình E2E tại `docs/tdq/bugs/<slug>.md` theo `Repro steps` + `Severity` của `terterarmy-cli` `[EV-015]`, **nhưng bắt buộc đi qua rule kiểm tra CLI của `doc_lint.py`** để không lặp lại tình trạng `BUG_BOARD.md` ghi sai cờ lệnh như `terterarmy-cli` `[EV-016]`.
- **Cổng mở opt-in cho Playwright MCP / TesterArmy CLI (`Inferred` từ `[EV-014]`, `[EV-018]`):**
  - TDQ giữ lõi độc lập trên Chrome DevTools MCP sẵn có (`Accessibility Snapshot` làm mặc định, tắt chụp ảnh diff toàn trang trừ khi test UI pixel), và mở tùy chọn cấu hình `e2e_adapter` trong tương lai cho các dự án web nặng cần `Playwright MCP` (`getByRole`) hoặc `TesterArmy` (`report` + `bug board`).

---

# Phần IV — Lộ trình triển khai chia đợt và KPI đo được

Để tránh đập đi làm lại gây xáo trộn hệ thống, đề xuất tách kế hoạch triển khai thực tế thành `3` đợt (trong các request cài đặt kế tiếp, giữ nguyên `Zero-Code-Touch` ở báo cáo đề xuất này):

| Đợt triển khai | Thời gian ước tính | Hạng mục cụ thể | Rủi ro & cách kiểm chứng |
| :--- | :--- | :--- | :--- |
| **Wave 1: Quick Wins (Giảm ngay thời gian chờ `~4x`)** | `1–2` ngày | 1. Vá `DATA_EXTS` thêm `.html`/`.htm` (`scripts/tdq_test.py`) `[EV-013]` và `.ruff_cache` vào `EXCLUDED_DIRS` (`scripts/tdq_test_receipt.py`) `[EV-011]`.<br>2. Đổi mặc định `qc.md:99` từ `--workers 1` sang `--workers auto` (trần `6`) `[EV-007]`, `[EV-011]`.<br>3. Cập nhật `report-template.md` ẩn cột `[unavailable]` `[EV-004]` và áp dụng khung **Dev Behavior QC Card** + giới hạn `QC-F4` OOP chỉ cho task chạm kiến trúc/class `[EV-002]`, `[EV-003]`.<br>4. Sửa bảng `muc_qc`: mở `smoke test` mặc định cho `full` `[EV-006]`. | **Rủi ro:** Xung đột ghi file tạm khi test chạy song song.<br>**Kiểm chứng:** Chạy `tron-bo --workers 6` `2` lần liên tiếp, đạt `0` lỗi flaky và `0` lỗi `INCOMPLETE` do cache. |
| **Wave 2: Changed-Flow E2E Smoke & Auto Meta-Gate** | `3–5` ngày | 1. Gắn marker `@pytest.mark.smoke` và `@pytest.mark.e2e` cho ~`25–40` kịch bản luồng chính (build bundle, hook dispatch parity, CLI E2E, probe subagent frontmatter/runtime) `[EV-010]`, `[EV-013]`, `[EV-021]`.<br>2. Viết lệnh `tdq_test.py smoke-e2e --changed` ánh xạ từ vùng sửa sang luồng E2E `<60s` (`Changed-Flow`) `[EV-020]`.<br>3. Gom `doc_lint` + `token_budget` + `i18n_check` + `git` thành `1` lệnh **Auto Meta-Gate** kết hợp cổng `5` bước kiểu `obra/superpowers` `[EV-022]`. | **Rủi ro:** Bỏ sót phụ thuộc chéo khi chỉ chạy theo vùng sửa.<br>**Kiểm chứng:** Giả lập lại ca lỗi `v0.103.0` (`tools/patches/` sai tên tool) — `Changed-Flow E2E Smoke` phải bắt được lỗi `<60s`. |
| **Wave 3: Browser Accessibility Snapshot & Plain-Language Ecosystem** | `5–7` ngày | 1. Chuyển `tdq-browser-test` mặc định dùng **Accessibility Tree Snapshot (`ref`) + `console`/`errors` fail-closed**, chỉ bật pixel vision diff khi sửa CSS/layout `[EV-012]`, `[EV-018]`, `[EV-023]`.<br>2. Thêm mẫu `docs/tdq/scenarios/*.md` (`7–19` dòng) `[EV-014]` và rule `doc_lint` kiểm lệnh CLI trong Bug Board `[EV-016]`.<br>3. Khai báo adapter opt-in cho Playwright MCP (`--caps`) / TesterArmy cho project web ngoài repo TDQ `[EV-017]`. | **Rủi ro:** Flakiness trên giao diện động SPA.<br>**Kiểm chứng:** Thử nghiệm E2E trên chính Archify HTML dashboard hoặc app web mẫu với `<5%` biến động và `0` console error lọt lưới. |

## Bảng KPI đo lường hiệu quả (`Trước` thực đo vs `Mục tiêu Sau`)

Lưu ý minh bạch theo `QC-I4`: cột **Trước** là số đo `Verified` trực tiếp từ hệ thống; cột **Mục tiêu Sau** là mức kỳ vọng `Inferred` dựa trên kết quả `--workers 6` thực đo của TDQ `[EV-011]` và chuẩn ngành `Testmon`/`Risk-Based` `[EV-020]`, `[EV-021]`.

| Chỉ số KPI | Trước (TDQ hiện tại — `Verified`) | Mục tiêu Sau (`Inferred`) | Cơ sở suy luận |
| :--- | :--- | :--- | :--- |
| Thời lượng chạy `tron-bo` (Full Suite) | Trung vị **`1,190.11s` (`19.8p`)** `[EV-008]` | **`<= 330s` (`~5.5p`)** (giảm `~72%`) | Kết quả thực đo `v0.103.1` với `--workers 6`: `314.31s` `[EV-011]` |
| Tỷ lệ hủy nhầm `INCOMPLETE` của runner | **`21.4%` (`6/28` lượt)** `[EV-008]` | **`< 3%`** | Vá `.ruff_cache` và `.html` loại nguyên nhân nhiễu chính `[EV-011]`, `[EV-013]` |
| Vòng lặp kiểm thử cho thay đổi thông thường | Tắt `smoke`, `3/10` `vung-cham` rơi về full (`<= 1,386s`) `[EV-006]`, `[EV-013]` | **`< 60s`** (`Fast Loop` + `Changed-Flow E2E Smoke`) | Kết hợp `vung-cham` `13.09s` và gói smoke tách marker `[EV-013]`, `[EV-020]`, `[EV-021]` |
| Tỷ trọng mục kiểm thủ tục / giấy tờ trong QC | **`48.8%` (`40/82` mục)** `[EV-001]` | **`<= 10%`** (gộp vào `1` dòng Auto Meta-Gate) | Rút toàn bộ `doc_lint`/SOLID/V2 table ra khỏi thẻ QC chính `[EV-001]`, `[EV-022]` |
| Tỷ lệ biên bản QC có bằng chứng hành vi/E2E sống | `12.2%` mục; **`4/8` biên bản có `0` mục E2E** `[EV-001]` | **`100%`** request `full` đổi behavior có **Dev Behavior QC Card** + smoke tươi | Mở mặc định `smoke` & `runtime` ở `muc_qc = full` thay cho chỉ mở ở `ultra` `[EV-006]`, `[EV-010]` |
| Thời gian dev đọc hiểu `1` biên bản QC | Trung bình `82.4` dòng (~`2,754` token), tối đa `17,029` ký tự `[EV-001]` | **`<= 30` dòng (`~10–15` giây đọc)** | Theo chuẩn thẻ ngắn `26` dòng của `terterarmy-cli` `[EV-014]`, `[EV-015]` |

---

## Đầu ra

- [Báo cáo đề xuất chính (file Markdown này)](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/reports/2026-11-21-1438-cai-thien-qc-test-e2e.md)
- [Báo cáo kiểm toán nội bộ 3 lớp TDQ (`T1.1`)](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/artifacts/2026-11-21-1438-cai-thien-qc-test-e2e/audit-tdq-qc-test.md)
- [Phân tích chi tiết `terterarmy-cli` (`T1.2`)](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/artifacts/2026-11-21-1438-cai-thien-qc-test-e2e/phan-tich-terterarmy-cli.md)
- [Nghiên cứu chuẩn ngành & plugin QA (`T1.3`)](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/research/2026-11-21-1438-cai-thien-qc-test-e2e.md)
- [Sổ cái bằng chứng & đối chiếu giả thuyết (`T2.1`)](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/artifacts/2026-11-21-1438-cai-thien-qc-test-e2e/evidence-log.md)
- [Dữ liệu bằng chứng chuẩn hóa JSONL](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/artifacts/2026-11-21-1438-cai-thien-qc-test-e2e/evidence.jsonl)
- [Biên bản kiểm chứng bằng chứng QC (`T3.1`)](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/qc/2026-11-21-1438-cai-thien-qc-test-e2e.md)

## Archify HTML

- Tệp cục bộ: [2026-11-21-1438-cai-thien-qc-test-e2e.html](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/reports/2026-11-21-1438-cai-thien-qc-test-e2e.html)
- Liên kết Tailscale Serve: https://unity-pc-rtx3060.tail99896.ts.net/vlog/tdq-workflow-agy/reports/2026-11-21-1438-cai-thien-qc-test-e2e.html

## Thời gian

Request `2026-11-21-1438-cai-thien-qc-test-e2e` · lane full · opened at 2026-11-21T14:42:28+07:00

| Phase | Wall clock | API request | Tool wait | Background job | Observed union | Unattributed | Times entered |
|---|---|---|---|---|---|---|---|
| idle | 0s | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | 1 |
| analyze | 6 min | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | 1 |
| spec | 5 min | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | 1 |
| plan | 19 min | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | 1 |
| mode | 0s | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | 1 |
| implement | 15 min | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | 1 |
| qc | 11s | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | 1 |
| report | 0s | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | 1 |
| Total | 45 min | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] |  |

Model compute time is unavailable (`model_giay=null`). API includes network/provider latency; tool time is host wait. Observed metrics may overlap; unattributed time is not assumed user/model time.
Transcript attribution: project_window. Complete covers selected supported observations only.
- api_request_seconds: no_usable_source
- tool_call_seconds: no_usable_source
- background_job_seconds: no_usable_source
- observed_union_seconds: no_usable_observations
- unattributed_seconds: wall_minus_observed_union;no_usable_observations

### Agent Role Telemetry (`tdq_timing.py roles`)

| Role | Runs | First pass | Rate | Retries | Avg elapsed | Models |
|---|---|---|---|---|---|---|
| self | 7 | 7 | 100% | 0 | — | — |
| tdq-qc-tester | 6 | 6 | 100% | 0 | — | — |
| tdq-implementer | 2 | 2 | 100% | 0 | — | — |

## Giới hạn

- **Bỏ qua đồng bộ LSP (`--bo-qua-lsp`):** `"Request docs/investigate danh gia quy trinh QC va nghien cuu de xuat E2E (khong sua ma nguon san pham); da kiem tdq_lsp.py check 5/8 bac DAT va smoke 3/3 tang tra loi duoc"` (ghi nhận lúc `2026-11-21T14:42:14+07:00`).
- **Hạn mức công cụ tìm kiếm ngoài ở `T1.3`:** `tavily-primary` chạy được `4` truy vấn `tavily_search` và trích xuất thẳng từ `playwright.dev`, `kentcdodds.com`, `vercel-labs/agent-browser` trước khi chạm hạn mức keyless theo ngày (`Retry after: 329s`/`1010s`); các trích đoạn bổ sung cho `martinfowler.com`, `testing.googleblog.com`, `obra/superpowers`, `stagehand` và `browser-use` được thu thập qua `search_web` và lưu nguyên văn trong `raw/01..04*.txt`.
- **Phạm vi thực thi (`Zero-Code-Touch`):** Đợt này chỉ điều tra và lập đề xuất ở `docs/tdq/`; hiệu quả giảm thời gian và độ nhạy bắt lỗi của Wave 1–3 đang ở mức `Inferred` chờ triển khai và đo kiểm thực tế ở các request code kế tiếp.

## Lệch spec chờ duyệt

Không có.

## Thân PR (soạn sẵn)

### Mục đích
Hoàn tất điều tra thực chứng quy trình QC/kiểm thử nội bộ của TDQ, đối chuẩn với `terterarmy-cli` và các chuẩn ngành (`Playwright Test Agents/MCP`, `Testing Trophy`, `Google Test Sizes`, `Instawork TIA/Smoke`, `obra/superpowers`, `agent-browser`), và đề xuất kiến trúc QC/E2E `Dev-First, E2E-First` chia làm `3` đợt triển khai.

### Tóm tắt kết quả chính
- Định lượng `8` biên bản QC gần nhất (`48.8%` meta/doc vs `12.2%` E2E/runtime), `179` bản ghi `timing.jsonl` và `38` lượt `.tdq-test.jsonl` (`tron-bo --workers 1` trung vị `1,190.11s`, `21.4%` `INCOMPLETE`; ca `v0.103.0` pass `4,603` unit test vẫn vỡ `8/8` subagent live).
- Đề xuất `Auto Meta-Gate` (ẩn thủ tục vào `1` dòng kiểm tự động, giữ nguyên `5` chốt lõi `TDQ_LOG`/receipt/hooks/Rust/AST), `Dev Behavior QC Card` đọc `10` giây, kiến trúc `3` tầng với **Changed-Flow E2E Smoke `<60s`**, bản vá `--workers auto` + `.ruff_cache` + `.html`, và lộ trình Wave 1–3 kèm KPI.

### Phạm vi tệp thay đổi
- Chỉ thêm tài liệu điều tra, bằng chứng, báo cáo đề xuất, QC và Archify HTML trong `docs/tdq/` và nhật ký trong `docs/workinglog/` (`Zero-Code-Touch`: `0` chỉnh sửa mã nguồn sản phẩm).
<!-- tdq-archify-binding:start -->
<!-- manifest: 2026-11-21-1438-cai-thien-qc-test-e2e.manifest.json -->
<!-- manifest_digest: 688cc558d8361115f3105d99d64f9ee7a1b21071024ca99c8bb58657d9ddd56f -->
<!-- tdq-archify-binding:end -->