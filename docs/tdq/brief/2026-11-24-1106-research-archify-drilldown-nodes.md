# BRIEF — Nghiên cứu cải tiến Archify đa tầng drill-down và tái sử dụng logic node

Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

## Nguyên văn

> okay bây giờ tôi muốn check và resreach để cải thiện archify. tôi muôn archify sẽ detail hơn ví dụ flow login sẽ là nhập username + pass nhấn login => check xem có nhớ login ko => gửi username+pass mã hoá về server => nhận lại access token,… và khi bấm vào mỗi cái sẽ có giải thích ví dụ bấm vào check xem có nhớ login: trong đó sẽ giải thích và có mini flow chart là sẽ ghi gì vào đâu. và tương tự như vậy một flow tổng sẽ có thể chứ thêm nhiều sub flow và giải thích dễ hiểu (natural) cho từng node nhỏ để khi đọc archify thì có thể hiểu từ flow và từng node và nếu trong node có logic thì có thể dùng flow graph để có thể hiểu và cứ đi sâu nhiều tầng. Những cái đã có và ko thay đổi có thể tái sử dụng là logic node để hạn chế đốt token để vẽ đi vẽ lại 1 node. Hãy phân tích yêu cầu và deep reseeach và tổng hợp lại show cho tôi đề xuất tối ưu . Chưa thay đổi tdq workflow ở request này

**Đọc hiểu ban đầu (`work_kind=investigate`):**
- **Mục tiêu:** Kiểm tra và nghiên cứu sâu năng lực hiện tại của công cụ `archify` (upstream `~/.local/share/archify`) cùng lớp tích hợp TDQ (`scripts/tdq_archify.py`, `scripts/archify_model.py`, `scripts/archify_artifacts.py`, `scripts/archify_delivery.py`) để thiết kế phương án tối ưu cho 4 yêu cầu cốt lõi:
  1. Flow chi tiết theo từng bước thực tế (ví dụ Login: nhập user/pass → kiểm tra nhớ đăng nhập → mã hóa gửi server → nhận access token…).
  2. Click trực tiếp vào từng node để mở giải thích bằng ngôn ngữ tự nhiên kèm mini flowchart / sub-flow graph của riêng logic trong node đó.
  3. Hỗ trợ đào sâu đa tầng (recursive drill-down: Flow tổng → Sub-flow → Node logic → Mini-flow tầng sâu hơn) mà vẫn dễ đọc, không vỡ bố cục và qua kiểm định Archify.
  4. Cơ chế tái sử dụng **Logic Node** (cache / registry định danh theo nội dung + dấu vân tay mã nguồn) để các node không đổi được dùng lại, tránh đốt token LLM vẽ lại từ đầu.
- **Phạm vi:** Nghiên cứu sâu, phân tích kỹ thuật, đánh giá ràng buộc thực tế của engine `archify` hiện tại và đề xuất kiến trúc tối ưu. **Chưa thay đổi mã nguồn TDQ Workflow trong request này.**
- **Điểm cần làm rõ sau khi chọn lane:** Mức độ ưu tiên giữa (a) giữ nguyên engine `archify` upstream kèm lớp mở rộng/viewer phía TDQ vs (b) đề xuất nâng cấp cả bộ sinh HTML/tương tác; phạm vi áp dụng (chỉ Master Architecture Map, chỉ Báo cáo/Spec, hay cả hai); và giới hạn độ sâu tầng drill-down mục tiêu.

## Hiểu & kiến thức

### Năng lực dùng được

Phân vân → DÙNG. Kiểm kê ngày 2026-11-24: `42` skill trên đĩa (`23` giữ qua `--loc`, `19` ẩn), cộng skill built-in trong context. Không xoá bảng này kể cả khi không có dòng DÙNG nào.

| Skill | Nguồn | Phán quyết | Dùng ở đâu / Lý do loại |
|---|---|---|---|
| `tdq-intake`, `tdq-conventions`, `tdq-spec`, `tdq-plan`, `tdq-build`, `tdq-status`, `tdq-setup`, `tdq-check-status`, `tdq-lean`, `tdq-checkportable` | `plugin:tdq-workflow-agy` | NỀN | Khung vận hành workflow TDQ (`full` + `investigate`) |
| `tdq-browser-test` / `chrome-devtools` | `plugin:tdq-workflow-agy` / `built-in` | DÙNG | Kiểm tra trực quan DOM/SVG tương tác thực tế của `docs/architecture/index.html` khi cần xác minh hành vi click/modal hiện hữu trong pha `implement` |
| Đã xét 40+ skill khác (`tdq-browser-research`, Google Workspace, Gemini API, `a11y-debugging`, `generative_ui`, `plugin`…) | `user/plugin/built-in` | KHÔNG | khác lĩnh vực |

### Phạm vi đã chốt

- Mặt CHỌN: `UX ĐÀO SÂU ĐA TẦNG` (flow chi tiết, click node mở giải thích tự nhiên + mini flowchart nhiều tầng), `TÁI SỬ DỤNG LOGIC NODE` (tối ưu token & thời gian agent xử lý), `TƯƠNG THÍCH ENGINE UPSTREAM` (ưu tiên không fork `tt-a1i/archify`), `BÁM NGUỒN CHỐNG BỊA (GROUNDING)`, `ĐO CHI PHÍ TOKEN & THỜI GIAN XỬ LÝ`, `TRẢI NGHIỆM ĐỌC & KIỂM ĐỊNH TRÌNH DUYỆT`.
- Mặt LOẠI: Chỉnh sửa mã nguồn TDQ Workflow trong request này (chỉ nghiên cứu & đề xuất tối ưu); fork trực tiếp engine `tt-a1i/archify` (trừ khi chứng minh engine gốc bị chặn cứng).
- Bối cảnh: Áp dụng cho cả 2 tầng (Master Architecture Map `docs/architecture/` lẫn Spec Trước/Sau và Báo cáo từng request); quy mô lớn (`> 100` Logic Node, đào sâu `>= 5` tầng, nhiều người bảo trì); cân bằng đồng thời 3 mục tiêu: đầy đủ thông tin, tối ưu token + thời gian agent xử lý, và dễ đọc dễ hiểu.
- Mức đầu tư suy ra: đầy đủ — vì quy mô lớn (`> 100` node, `>= 5` tầng), phủ cả Master Map lẫn Spec/Report và cần đồng thời tối ưu token, độ trễ xử lý, bám nguồn lẫn độ dễ đọc.

### Khảo sát nông điểm vào & giả thuyết (B1)

**Hồ sơ kiến trúc (`docs/kien-truc.md`):** Đã đọc toàn bộ bản nháp (`NHÁP — chờ user chốt`), ghi nhận luật phân tầng (`scripts/` không import `hooks/`, `skills/` chỉ nhắc lệnh CLI, chỉ `tdq_state.py` ghi state).

**Bảng đối chiếu vùng khảo sát 3 chiều (nông trước spec — chi tiết đào sâu để sang `implement`):**

| Vùng file khảo sát (chỉ đọc) | Phát hiện qua lớp nào | Tác động & quan hệ |
|---|---|---|
| `scripts/tdq_archify.py`, `scripts/archify_model.py`, `scripts/archify_artifacts.py`, `scripts/archify_delivery.py` | Grep/Dir + Graphify (`sync_master`, `check_manifest`, `run_finalize`, `build_manifest`) | 4 module lõi của TDQ-Archify: chuyển đổi mô hình, tạo fingerprint/manifest, gọi engine gốc và xuất bản nguyên tử |
| `docs/tdq/models/master.model.json` + 6 view JSON (`overview.json`, `hooks-and-gates.json`, …) | Dir + Read | Cấu trúc mô hình Master hiện tại: 1 tầng phẳng (`overview` → `flows[]` → `target.diagram` + `steps[]` gắn `sources[path, line, end_line]`) |
| `skills/tdq-build/references/archify-lifecycle.md` | Read | Ghi nhận luật cứng hiện tại: không chèn `onclick` vào node native; flow card mở 1 modal chi tiết |
| `C:\Users\admin\Documents\archify` (`https://github.com/tt-a1i/archify.git`, commit `25cf3708`) | `tdq_archify.py check` + Dir | Engine Archify gốc có đủ mã nguồn `archify/`, `viewer/`, `docs/`, `DESIGN.md`, `PRODUCT.md`, `ROADMAP.md` chạy trên Node `v24.21.0` |

**Giả thuyết cần kiểm chứng sâu trong pha `implement` (có thể bác bỏ):**
- **H1 (Năng lực tương tác gốc của `tt-a1i/archify`):** Cần kiểm chứng xem `viewer/` và schema của `archify` gốc hiện đã hỗ trợ click trực tiếp vào từng node để mở panel giải thích + sub-flow đa tầng chưa, hay chỉ dừng ở tooltip/highlight/1 tầng modal; và giới hạn `composition/desktop-readability` (4–5 node mỗi hàng) ràng buộc độ chi tiết flow ra sao.
- **H2 (Kiến trúc đào sâu đa tầng N-level không vỡ chất lượng đọc):** Có thể mô hình hóa **Flow Tổng → Node chi tiết → Sub-flow / Mini Flowchart đệ quy nhiều tầng** bằng đồ thị phân cấp (hierarchical DAG/tree kèm chống chu trình, breadcrumb, giải thích ngôn ngữ tự nhiên từng node) theo mô hình lai (Master Map `index.html` + lazy-load mảnh qua HTTP/Tailscale; Spec/Report tự chứa gọn) mà vẫn vượt được cổng kiểm tra bố cục/browser-check.
- **H3 (Kho tái sử dụng Logic Node theo dấu vân tay nguồn — giảm đốt token và thời gian agent):** Có thể tách mô tả mỗi Logic Node thành đơn vị độc lập định danh bằng `(node_id, source_fingerprint_sha256, content_hash)` kế thừa cơ chế `source_fingerprint` của `archify_artifacts.py`, kết hợp **Incremental Dirty-Only** (tầng 1–2) và **Lazy Depth** (tầng 3–5+), giúp mỗi lần đồng bộ chỉ gọi AI cập nhật đúng node có mã nguồn đổi và tái dùng 100% node không đổi (như `check nhớ login`, `xác thực JWT`…).
- **H4 (Ranh giới tích hợp TDQ vs Upstream Archify):** Cần so sánh rõ chi phí kỹ thuật, rủi ro bảo trì và khả năng nâng cấp giữa 3 phương án với ưu tiên **KHÔNG fork `tt-a1i/archify`** (chỉ xét fork nếu chứng minh engine gốc bị chặn cứng).

### Quyết định đã chốt

- **Đóng gói lai theo mục đích (`1a`):** Master Architecture Map (`docs/architecture/`) hướng tới `index.html` nhẹ + tải lười mảnh JSON/SVG qua HTTP/Tailscale Serve để xử lý `> 100` node và `>= 5` tầng; Spec Trước/Sau và Báo cáo từng request vẫn tự chứa gọn.
- **Chiến lược cập nhật tối ưu token & độ trễ (`2a`):** Kết hợp Incremental Dirty-Only (máy tự đối chiếu hash mã nguồn cho tầng 1–2 với `0` token LLM, chỉ gọi agent cập nhật node bẩn) + Lazy Depth (tầng 3–5+ sinh dần theo vùng chạm của request rồi lưu cache vĩnh viễn vào Logic Node Registry).
- **Đầu ra minh họa bắt buộc (`3a`):** Ngoài báo cáo phân tích và ma trận so sánh, bắt buộc kèm Schema JSON chuẩn của Logic Node Registry, ví dụ trọn vẹn chuỗi Login đa tầng (`4–5` tầng), và bảng ước tính tiết kiệm token + thời gian agent xử lý trước/sau.
- **Phương án đã loại:** (1) Sửa mã nguồn TDQ Workflow trong request này — user cấm rõ ràng; (2) Nhồi toàn bộ `> 100` node / `>= 5` tầng vào 1 file `file://` khổng lồ cho Master Map — gây nặng trình duyệt và render lại tốn thời gian; (3) Fork ngay `tt-a1i/archify` — loại ưu tiên để giữ khả năng `git pull` upstream, chỉ giữ làm phương án dự phòng nếu H1 chứng minh bị chặn cứng.

### Lộ trình

| Bước/phase | CÓ-BỎ | Vì sao |
|---|---|---|
| `analyze` (B0 + B1 nông + phỏng vấn 2 vòng) | CÓ | Khung bất biến — chốt đủ phạm vi, quy mô lớn, ưu tiên không fork và mức `muc_qc=full` |
| `spec` (Spec nghiên cứu, miễn Archify preview) | CÓ | Khung bất biến — chốt câu hỏi nghiên cứu, 4 giả thuyết H1–H4, cấu trúc đề xuất và tiêu chí đo; miễn preview trước duyệt theo `investigate-mode.md:13` |
| `plan` (Kế hoạch shard điều tra độc lập) | CÓ | Khung bất biến — chia 4 shard song song (`tdq-explorer` / `research`) với `Worktree: none` và ngân sách tool rõ ràng |
| `implement` (Thu thập bằng chứng + phân tích sâu + mẫu Login) | CÓ | Khung bất biến — khảo sát sâu `C:\Users\admin\Documents\archify`, 4 module `scripts/*archify*.py`, kiểm DOM thực tế và tổng hợp kiến trúc + schema + ước lượng token |
| `qc` (`QC-I1..I4` mức `full`) | CÓ | Theo lựa chọn `4a` (`muc_qc=full`) — kiểm grounding `100%` `[EV]` và `path:line`, bác bỏ giả thuyết, nhãn độ tin cậy và phạm vi 0 file code sửa |
| `qc` Red-Team độc lập (`ultra`) | BỎ | User chọn `full` (`4a`), không chọn `ultra` (`4c`) |
| `report` (Báo cáo MD + Archify HTML + Tailscale verify) | CÓ | Khung bất biến — xuất cặp tài liệu báo cáo trực quan và hỏi commit/merge |

## Hỏi đáp

- **Chọn pipeline (2026-11-24 11:17):** Hỏi `1. Bạn muốn chạy pipeline nào?` (`A` chuyên sâu `deep` / `B` nhanh `express`, loại `docs`) → Người dùng chọn: `1a` (`full`, `work_kind=investigate`, nhánh `docs/research-archify-drilldown-nodes` tách từ `dev`).
- **Vòng 1 — Phạm vi & Bối cảnh (2026-11-24 11:27):**
  - Câu hỏi: (1) Mặt bổ sung (`A` tương thích upstream, `B` bám nguồn grounding, `C` đo token/cache, `D` trải nghiệm đọc & browser-check, `E` chỉ luồng chính); (2) Loại tài liệu áp dụng (`A` cả 2 tầng, `B` chỉ Master Map, `C` chỉ Spec/Report); (3) Quy mô (`A` vừa 20–80 node/2–4 tầng, `B` lớn >100 node/>=5 tầng, `C` nhỏ <20 node/2 tầng); (4) Can thiệp upstream (`A` ưu tiên không fork, `B` sẵn sàng fork/viewer riêng, `C` so sánh ngang hàng); (5) Bổ sung.
  - Người dùng trả lời nguyên văn: `"1abcd 2a 3b 4a 5b tôi muốn đầy đủ thông tin nhưng tối ưu token và cả thời gian agent xử lí nhưng vẫn đảm bảo dễ đọc dễ hiểu"`.
- **Vòng 2 — Chi tiết & Mức QC (2026-11-24 12:03):**
  - Câu hỏi: (1) Hình thức xuất bản HTML cho `> 100` node & `>= 5` tầng (`A` lai theo mục đích: Master Map tải lười mảnh qua HTTP/Tailscale + Spec/Report tự chứa gọn; `B` 1 file `file://` duy nhất; `C` so sánh cả hai); (2) Nhịp sinh & cập nhật Logic Node (`A` kết hợp gia tăng vùng chạm tầng 1–2 + độ sâu lười lưu cache tầng 3–5+; `B` gia tăng toàn bộ tầng; `C` sinh lười hoàn toàn); (3) Kèm mẫu thiết kế minh họa (`A` kèm Schema JSON chuẩn + chuỗi Login đa tầng mẫu + ước lượng token/thời gian; `B` chỉ phân tích phương án); (4) Mức QC (`A` `full`, `B` `lite`, `C` `ultra`); (5) Bổ sung (`A` không / `B` có).
  - Người dùng trả lời nguyên văn: `"1a2a3a4a5a"` (chọn `A` cho cả 5 câu, chốt `muc_qc=full`).
