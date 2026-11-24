# BÁO CÁO — Nghiên cứu cải thiện Archify theo hướng drill-down nhiều tầng và tái sử dụng Logic Node

Ngày: 2026-11-24 · Mã yêu cầu: `2026-11-24-1106-research-archify-drilldown-nodes` (`6/6` task tick đủ, `5/5` DoD đạt PASS)
Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

> **Tóm tắt dễ hiểu:** Trước đây Archify vẽ toàn bộ một luồng lớn vào một khung phẳng, nên sơ đồ vừa dễ tràn màn hình vừa tốn nhiều token vẽ lại. Sau khảo sát, hướng tối ưu là giữ nguyên công cụ gốc để vẽ từng lát cắt nhỏ và bọc thêm kho Logic Node tái sử dụng. Bấm vào từng bước sẽ mở giải thích dễ hiểu cùng sơ đồ con nhiều tầng. Cách làm này giảm khoảng 95% lượng token cập nhật mà trang HTML vẫn nhẹ.

**Trước request (trạng thái/flow):** Hiện tại `master.model.json` chỉ mô tả `1` tầng phẳng (`overview -> flows -> steps`), bị `_validate_master` khóa schema và `_build_master_explainer` trải phẳng thành chữ không liên kết được sơ đồ con. Trong `docs/architecture/`, tổng dung lượng đã lên `9,268,027` bytes dù chỉ có `6` view (`2,622,525` bytes ở `index.html` do nhúng lặp `~276 KB` `htmlGzip` mỗi view; `1,222,506` bytes ở `manifest.json` băm SHA-256 toàn tệp trên `5,804` file), đồng thời trình duyệt ghi nhận `4/6` view không hiển thị vừa khung đọc inline.
**Sau request (trạng thái/flow):** Chưa thay đổi bất kỳ tệp mã nguồn TDQ nào (`0` file code sửa theo đúng phạm vi); đã hoàn thành báo cáo phân tích, chứng minh `4/4` giả thuyết (`H1`–`H4`) và đề xuất **Phương án A — No-Fork Hybrid**:
- **Không fork `tt-a1i/archify`:** Giữ nguyên engine gốc làm trình dựng SVG từng lát cắt `<= 5` node qua `finalize` (`data-node-id` giữ ổn định ngay cả sau `staticSvg()`), còn TDQ bọc lớp Interactive Drill-Down Shell bên ngoài để mở giải thích tự nhiên + mini-flowchart con + breadcrumb + chống chu trình.
- **Kho Logic Node tái sử dụng (`Logic Node Registry`) & Hash 2 lớp:** Tách từng node ra tệp mảnh `nodes/<id>.json` + mục lục `index.json`; dùng `ast_symbol_sha256` chống false-dirty khi dịch dòng kết hợp `span_binding` tự cập nhật `line..end_line` bằng `0` LLM tokens, áp dụng Incremental cho Tầng 1–2 và Lazy Depth cho Tầng 3–5+ (tiết kiệm ước tính `~94–95%` token và `~91%` thời gian khi cập nhật `2` hàm trong dự án `> 100` node).
- **Hai chế độ phân phối HTML:** Portal tổng hợp `docs/architecture/` chuyển sang `1` shell nhẹ + lazy load qua HTTP/Tailscale (có `<script>` fallback cho `file://`), còn Spec/Report từng request giữ dạng `1` file HTML tự chứa nhỏ gọn (`<= 4` tầng).
**Đã test gì:** Khảo sát trực tiếp mã nguồn `C:\Users\admin\Documents\archify` (v3.2), `4` module `scripts/*archify*.py` và `docs/tdq/models/*.json`; mở và click kiểm tra trực tiếp `docs/architecture/index.html` trên Chrome DevTools MCP (`Accessibility Tree` + modal `iframe` + console log); hợp nhất chứng cứ qua `tdq_team.py evidence merge`; kiểm tra tệp `logic-node-schema-and-login-example.json` bằng Python `json.loads`; kiểm định định dạng bằng `doc_lint.py` và rà soát đối chiếu `QC-I1..I4`.
**Kết quả test:** `14/14` chứng cứ nguồn (`s1`–`s3`) được xác nhận độ tin cậy `high` trong `evidence.jsonl`; Chrome DevTools xác nhận `4/6` view ở `index.html` rơi về cảnh báo quá khổ inline và `0` console error/warning; kiểm tra kịch bản JSON Schema đạt với `12` Logic Nodes, `max_depth = 5`, `6` node tái sử dụng (`len(reused_by) >= 2`), có nhánh lỗi `401/429` và neo chống chu trình; `0` thay đổi mã nguồn ngoài `docs/tdq/`; `doc_lint.py` đạt exit `0`.
**Đầu ra:** `docs/tdq/reports/2026-11-24-1106-research-archify-drilldown-nodes.md`, `docs/tdq/artifacts/2026-11-24-1106-research-archify-drilldown-nodes/{s1.md,s2.md,s3.md,s4.md,logic-node-schema-and-login-example.json,evidence.jsonl}` · **Archify HTML:** `docs/tdq/reports/2026-11-24-1106-research-archify-drilldown-nodes.html`
**Giới hạn:** Yêu cầu dạng nghiên cứu (`work_kind=investigate`), chưa sửa mã nguồn TDQ Workflow; mở khóa cổng LSP ban đầu với `ly_do`: `"nghiên cứu sâu và đề xuất kiến trúc Archify (work_kind=investigate), không sửa mã nguồn TDQ Workflow"` trên `module`: `["javascript:. → HET_HAN (kết quả cũ hơn 24 giờ)", "python:. → HET_HAN (kết quả cũ hơn 24 giờ)", "rust:hooks/rust/tdq-dispatch → HET_HAN (kết quả cũ hơn 24 giờ)"]`; số liệu tiết kiệm token và thời gian cho quy mô `120` node / `5` tầng là ngoại suy có kiểm soát (`Inferred`) từ mặt bằng đo thực tế (`~2.83s`/view `finalize`, `~2.62 MB` `index.html`, `5,804` file trong `manifest.json`).
**Lệch spec chờ duyệt:** không có
**Git:** chưa commit (đang trên nhánh `docs/research-archify-drilldown-nodes`)

---

## Phân tích kỹ thuật chi tiết (`H1`–`H4`)

### 1. Bảng kết luận các giả thuyết nghiên cứu

| Giả thuyết | Kết luận | Độ tin cậy | Bằng chứng chính (`evidence.jsonl`) |
|---|---|---|---|
| **H1:** Năng lực click node gốc của `tt-a1i/archify` vs drill-down nhiều tầng | **Xác nhận có điều kiện:** Đã có click node `1` tầng (Passport `#focus-chip` + modal `#diagram-dialog`), chưa hỗ trợ drill-down đệ quy và schema khóa `col 0..5`, rộng `1100–1240px` | Cao (`Verified`) | `[b3d9f1b42470]`, `[46c9823abe29]`, `[7fc1103ff631]`, `[67447fa43e41]` |
| **H2:** Nguyên nhân phình HTML & Rebuild toàn phần ở lớp TDQ wrapper | **Xác nhận hoàn toàn:** `_validate_master` khóa `1` tầng, `_build_master_explainer` bỏ target link, `manifest.json` băm `5,804` file toàn phần, `index.html` lặp `6 × ~276 KB` `htmlGzip` (`9.27 MB` thư mục), `4/6` view không vừa inline | Cao (`Verified`) | `[bbdbffdb86ae]`, `[0f12aafb46ef]`, `[68f61ff815f2]`, `[edc738ecb1c8]` |
| **H3:** Logic Node Registry + Hash AST/Symbol + Lazy Depth tiết kiệm token/thời gian | **Xác nhận nền tảng + Ngoại suy hợp lệ:** Dữ liệu nền (`_hash_file` gây false-dirty, `finalize` `~2.83s`/view, `file://` CORS) đã đo; mô hình cắt giảm `~94–95%` token cập nhật & `~91%` thời gian | Trung bình–Cao (`Verified` nền / `Inferred` định lượng) | `[d6a4b677f4dc]`, `[d51c5900101f]`, `[ea1686057f92]`, `[dc201b7feeec]` |
| **H4:** Không cần fork `tt-a1i/archify` để triển khai drill-down đa tầng | **Xác nhận hoàn toàn:** `staticSvg()` bảo toàn `data-node-id` và `data-edge-id`; tuân thủ `archify-lifecycle.md:27` (không tiêm `onclick` vào native node) nhờ listener vỏ ngoài | Cao (`Verified`) | `[46c9823abe29]`, `[125ad2d912c9]`, `[206d2c41cd00]` |

---

### 2. Vì sao sơ đồ chi tiết hiện tại bị vỡ hoặc đốt token (`S1`, `S2`)

1. **Ràng buộc đọc của `tt-a1i/archify` ép buộc phải chia nhỏ theo tầng (`[b3d9f1b42470]`):**
   Tại `C:/Users/admin/Documents/archify/archify/schemas/workflow.schema.json:267-318`, schema bật `additionalProperties: false`, giới hạn trục cột `col: 0..5` và `sources: 1..3`. Trong `archify/explainer/diagrams.mjs:68-69`, ngưỡng chiều rộng đọc là `READABLE_WORKFLOW_WIDTH = 1100` (trần cứng `1240px`) để nhãn cạnh `8px` không rơi dưới `6px` trên khung đọc `930px`. Do đó, nếu nhồi `15–20` bước chi tiết của luồng Login vào `1` sơ đồ phẳng chắc chắn sẽ bị từ chối hoặc sập về cảnh báo quá khổ.
2. **Bằng chứng sống trên Chrome DevTools (`[edc738ecb1c8]`, `[68f61ff815f2]`):**
   Khi mở trực tiếp `docs/architecture/index.html` trên Chrome DevTools, **4/6 view** (`overview`, `pipeline-lifecycle`, `search-and-archify`, `hooks-and-gates`) đều không vẽ được SVG inline mà hiển thị `"This diagram cannot fit this page width with readable text. Open the interactive view to inspect it."`. Bấm mở modal cho thấy `<iframe>` (`0` console errors) chỉ dừng ở `1` tầng phóng to/tìm node và Passport `#focus-chip` (`viewer/focus.js:330-386`) (`[7fc1103ff631]`).
3. **Bản chất phình dung lượng từ `packPageBundle` (`[125ad2d912c9]`, `[68f61ff815f2]`):**
   Mỗi view chỉ tốn **`23.7–29.4 KB`** cho đồ họa `svg` thật, nhưng trình đóng gói nhúng kèm bản nén `htmlGzip` nặng **`275.7–276.9 KB` cho mỗi view** (gói lại `template.html` `786,886` bytes) bên trong `#archify-explainer-prepared` (`2,005,872` bytes). Nếu mở rộng lên `30` sơ đồ con (`> 100` node), chỉ riêng `index.html` sẽ vọt lên **`~10.5 MB`** và cả thư mục vượt **`~34 MB`**.
4. **Lớp TDQ wrapper khóa 1 cấp & băm toàn tệp (`[bbdbffdb86ae]`, `[0f12aafb46ef]`, `[d6a4b677f4dc]`, `[d51c5900101f]`):**
   `_validate_master` (`scripts/archify_model.py:728-767`) từ chối trường con lồng nhau; `_build_master_explainer` (`scripts/tdq_archify.py:665-735`) làm phẳng bước thành văn bản; còn `_derive_stable_source_paths` (`scripts/tdq_archify.py:738-768`) + `_hash_file` (`scripts/archify_artifacts.py:120-126`) băm cả file trên `5,804` tệp trong `manifest.json`, khiến sửa `1` comment ở hàm không liên quan cũng kéo chuỗi `sync_master` chạy lại tốn `~20.3s` (`~2.83s`/view) [`ea1686057f92`].

---

### 3. Đề xuất Kiến trúc Tối ưu: Phương án A — No-Fork Hybrid (`S3`, `S4`)

| Tiêu chí | **Phương án A (Đề xuất): Bọc TDQ + Logic Registry + Lazy Portal** | Phương án B: Fork `tt-a1i/archify` | Phương án C: Engine ngoài (D2/Mermaid) |
|---|---|---|---|
| **Giữ upstream `tt-a1i/archify`** | **100% không fork**, chỉ dùng để render SVG lát cắt `3–5` node + kiểm readability | Mất tương thích sau `v3.2`, vỡ `test:generated` (`15` mảnh `viewer/`) | Loại bỏ toàn bộ hệ thống kiểm định Archify hiện có |
| **Drill-down `>= 5` tầng + văn bản tự nhiên** | **Đạt trọn vẹn** qua listener `[data-node-id]` ngoài SVG (`archify-lifecycle.md:27` hợp lệ) | Phải viết lại `reader.js`, `focus.js` và nới chặt hàng loạt JSON schema | Phải tự xây mới layout engine, focus, trace reachability |
| **Tiết kiệm Token & Thời gian (`> 100` node)** | **Cắt `~94–95%` token** (cập nhật 2 hàm) & `~91%` thời gian nhờ hash AST/symbol + Lazy Depth | Vẫn thiếu Logic Registry & hash AST/symbol | Tự viết toàn bộ từ đầu |
| **Dung lượng HTML cho `> 100` node** | **Nhẹ (`~1.2 MB` kho / `< 250 KB` tải đầu)** qua 1 shell + SVG mảnh `~26 KB` | Vẫn phình hàng chục MB nếu giữ cấu trúc `pageBundle` | Nặng runtime JS client (`0.4–1.5 MB`) + không kiểm readability tĩnh |
| **Chi phí & Rủi ro** | **Thấp–Trung bình:** Tận dụng nguyên `archify_delivery.py` & kiểm chứng sẵn | **Cao:** Hai nhánh song song khó bảo trì | **Rất cao:** Đập bỏ và viết lại toàn bộ adapter & test |

#### Ba trụ cột của Phương án A

1. **Tách Kho Logic Node Tái Sử Dụng (`docs/tdq/models/registry/`):**
   Mỗi hành động/khối nghiệp vụ là `1` **Logic Node** chuẩn chứa: giải thích tự nhiên (*làm gì, ghi cái gì vào đâu, vì sao cần, ca lỗi biên*), hợp đồng `io_contract`, tối đa `3` neo `sources[{path, line, end_line}]`, `reused_by[]`, và tùy chọn `sub_flow` (`<= 5` node, `col 0..5`) trỏ sang node sâu hơn (`max_depth` mặc định `5–6`, chặn chu trình bằng `visited_stack` + thẻ neo quay lại breadcrumb).
2. **Chiến lược Hash 2 lớp + Incremental Tầng 1–2 / Lazy Depth Tầng 3–5+ (`S3`):**
   - **Lớp 1 (`ast_symbol_sha256`):** Băm phần thân AST/symbol thay vì toàn tệp (`_hash_file`). Sửa comment hay thêm hàm mới khiến số dòng dịch chuyển **không gây false-dirty** (`0` token LLM).
   - **Lớp 2 (`span_binding`):** Khi AST khớp nhưng file gốc dịch dòng, script Python tự cập nhật `[line, end_line]` (`0` LLM tokens, `0` Node render).
   - **Tầng 1–2 đồng bộ Incremental (`O(D)`), Tầng 3–5+ Lazy Depth:** Chỉ dựng sâu chi tiết vi mô lần đầu khi request chạm tới rồi lưu vĩnh viễn vào Registry cho mọi flow sau dùng lại.
   - **Tách rạch ròi `planned` vs `working-tree`/`committed`:** Spec chỉ tạo node `planned` ở vùng nháp, tuyệt đối không trộn vào Master chính thức cho tới khi Build + QC xác minh file thật.
3. **Hai chế độ đóng gói HTML thông minh (`S3`):**
   - **Master Portal (`docs/architecture/`):** Phát hành **1 shell runtime duy nhất** (`< 250 KB`) + các lát cắt SVG thuần (`~26 KB`/lát cắt) và `nodes/*.json`. Mặc định tải lười qua HTTP/Tailscale (kèm lệnh mới đề xuất `tdq_archify.py serve` mở HTTP `127.0.0.1` khi xem cục bộ) và hỗ trợ `<script>` bundle fallback (`window.__TDQ_REGISTRY__`) để vượt rào CORS `file://` [`dc201b7feeec`].
   - **Spec / Report HTML (`docs/tdq/reports/<slug>.html`):** Giữ `1` file HTML tự chứa gọn nhẹ (`<= 4` tầng) nhưng loại bỏ bản sao `htmlGzip` dư thừa cho các lớp con.

---

### 4. Bảng ước lượng định lượng Token & Thời gian (`120` Logic Nodes, `5` tầng, `30` lát cắt)

> Phần đo nền (`finalize` `2,833 ms`/view, `29,502 B` / `6` view JSON, `index.html` `2.62 MB`) là số liệu thật [`Verified`]; phần kịch bản `120` node được ngoại suy nhất quán từ mặt bằng này (`Inferred`, xem đầy đủ giả định trong `s3.md`).

| Kịch bản vận hành | Vẽ lại toàn phần hiện tại (`O(N)`) | **Phương án A (Registry + Incremental + Lazy)** (`O(D)`) | Mức tối ưu |
|---|---|---|---|
| **Dựng lần đầu (`Cold Build`)** | `~160K–210K` tokens · `~85s` render + `~180–240s` LLM | Dựng sẵn Tầng 1–2 (`~24` nodes): `~32K–45K` tokens · `~17s` render + `~40–55s` LLM | **`~78%` tokens · `~76%` thời gian** |
| **Sửa `2` hàm trong `1` request (`D = 2`)** | `~60K–110K` tokens · `~85s` render + `~90–140s` LLM | Hash Python `< 0.2s` tìm `2` node bẩn → `~3.5K–5K` tokens · `~5.7s` render + `~8–12s` LLM | **`~94–95%` tokens · `~91%` thời gian** |
| **Dịch số dòng / sửa comment ngoài hàm** | `~60K+` tokens · `~85s+` (false-dirty toàn tệp) | Script Python relink `span_binding` (`< 0.3s`, `0` Node render, `0` LLM) | **`100%` tokens · `> 99%` thời gian** |
| **Node dùng chung (`Verify JWT` ở `3` flow)** | Sinh & kiểm lặp `3` lần (`~3.6K–4.5K` tokens) | Sinh `1` lần trong Registry, `3` nơi trỏ `ref_node_id` (`~80` tokens) | **`~65–85%` tokens/node trùng** |
| **Tổng dung lượng trên đĩa (`docs/architecture/`)** | `~34 MB` tổng (`~10.5 MB` riêng `index.html`) | `~1.2 MB` tổng (`< 250 KB` tải lần đầu) | **`~96%` dung lượng** |

---

### 5. Minh họa Schema chuẩn & Chuỗi Login `5` tầng (`logic-node-schema-and-login-example.json`)

Tệp `docs/tdq/artifacts/2026-11-24-1106-research-archify-drilldown-nodes/logic-node-schema-and-login-example.json` định nghĩa đầy đủ JSON Schema (Draft `2020-12`) kèm mẫu **`12` Logic Nodes xuyên suốt `5` tầng** cho luồng đăng nhập thực tế:

1. **Tầng 1 (`flow-auth-login-root`):** `Nhập User/Pass` → `Kiểm tra Nhớ đăng nhập` → `Mã hóa & Gửi POST` → `Nhận Access Token` (hoặc rẽ nhánh lỗi `401/429`).
2. **Tầng 2 (`auth-ui-submit`, `auth-check-remember`, `auth-encrypt-send`, `auth-error-reject`):** Người đọc bấm vào `Kiểm tra xem có Nhớ đăng nhập không` thấy rõ quyết định: bật Remember → cấp phiên `30` ngày, tắt Remember → giữ phiên tạm trong RAM; kèm nhánh lỗi chống brute-force (`fail_count >= 5` → `HTTP 429`). Nút `auth-encrypt-send` được tái sử dụng (`reused_by`) ở cả `flow-change-password` và `flow-stepup-mfa`.
3. **Tầng 3 (`storage-persist-session`, `storage-memory-session`, `crypto-tls-envelope`, `server-verify-and-issue`):** Bấm tiếp vào nhánh *Nhớ đăng nhập* mở ra **mini-flowchart ghi gì vào đâu**: `Refresh Token` → Cookie `HttpOnly + Secure + SameSite=Strict`; `Access Token` (`15m`) → chỉ giữ trong biến **RAM JavaScript** (tuyệt đối không để token nhạy cảm ở `localStorage`); chỉ metadata hiển thị (tên, avatar) → `localStorage`. Nút `server-verify-and-issue` tái sử dụng cho `3` luồng khác nhau (`flow-auth-login-root`, `flow-token-refresh`, `flow-sso-exchange`).
4. **Tầng 4 (`cookie-write-policy`, `jwt-sign-and-store-jti`):** Bấm sâu tiếp thấy chính sách header `Set-Cookie` chống XSS/CSRF và quy trình ký JWT `RS256` kèm lưu `JTI` + `family_id` vào Redis để hỗ trợ thu hồi phiên từ xa.
5. **Tầng 5 (`session-rotation-guard`):** Mô tả cơ chế xoay vòng Refresh Token: nếu phát hiện token cũ bị dùng lại (Replay Attack), thu hồi toàn bộ `family_id` trong Redis và kích hoạt neo chống chu trình `cycle_back_to: "auth-ui-submit"` đưa người dùng về màn hình đăng nhập mà không làm UI đệ quy vô tận.

---

### 6. Lộ trình triển khai đề xuất & Kiểm soát rủi ro (Dành cho request code tiếp theo)

1. **Pha 1 — Core Registry & AST Hash Engine:** Tạo `scripts/archify_registry.py` (hỗ trợ `ast` Python + parser/LSP range JS/TS), mở rộng `archify_model.py` kiểm định `LogicNode` và phân tách `planned` vs `working-tree`.
2. **Pha 2 — Shared Portal Shell & Lazy Slices:** Nâng cấp `tdq_archify.py` (`sync-master --incremental`, xuất lát cắt SVG thuần `<= 5` node, lệnh `tdq_archify.py serve` + `<script>` bundle fallback cho `file://`) thay thế kiểu nhúng lặp `htmlGzip`.
3. **Pha 3 — Nối vào Spec / Build & Thí điểm (`Pilot`):** Chạy thí điểm chuyển đổi cụm `hooks-and-gates` + `search-and-archify` sang cây `4` tầng (`~18` nodes) rồi đo thực nghiệm số token và thời gian `durationMs` trước/sau.
4. **Pha 4 — Automated Browser & Readability Gate:** Dùng Chrome DevTools MCP kiểm tự động `click >= 4` tầng, neo chu trình, chế độ fallback offline và `0` lỗi console trong CI test (`test_archify_pipeline.py`).

**Rủi ro cần khóa sớm khi viết code:** (a) Bảo đảm parser lấy đúng phạm vi hàm cho cả Python lẫn TypeScript/Rust (tránh rơi về băm toàn file khi thiếu parser ngôn ngữ lạ — khi rơi fallback thì ghi rõ cờ `"hash_mode": "file_fallback"`), (b) Chặn tuyệt đối trộn node `planned` chưa kiểm chứng vào `docs/architecture/`, (c) Đảm bảo mọi file HTML vẫn hoạt động tối thiểu ở chế độ offline `file://` qua fallback JS bundle.

---

## Thời gian

```text
Request `2026-11-24-1106-research-archify-drilldown-nodes` · lane full · opened at 2026-11-24T11:18:09+07:00

| Phase | Wall clock | Times entered |
|---|---|---|
| idle | 1s | 1 |
| analyze | 47 min | 1 |
| spec | 3 min | 1 |
| plan | 22 min | 1 |
| mode | 6 min | 1 |
| implement | 16 min | 1 |
| qc | 3 min | 1 |
| report | 26s | 1 |
| Total | 1h 37min |  |

Model compute time is unavailable (`model_giay=null`). API includes network/provider latency; tool time is host wait. Observed metrics may overlap; unattributed time is not assumed user/model time.
Transcript attribution: project_window. Complete covers selected supported observations only.
Host metrics unavailable (5 hidden: api_request_seconds, tool_call_seconds, background_job_seconds, observed_union_seconds, unattributed_seconds): no_usable_source, no_usable_observations, wall_minus_observed_union;no_usable_observations

## Agent Role Telemetry

| Role | Runs | First pass | Rate | Retries | Avg elapsed | Models |
|---|---|---|---|---|---|---|
| self | 7 | 7 | 100% | 0 | — | — |
| tdq-qc-tester | 6 | 6 | 100% | 0 | — | — |
| tdq-implementer | 2 | 2 | 100% | 0 | — | — |
```

## Thân PR (soạn sẵn)

**Tóm tắt:** Hoàn thành nghiên cứu sâu và đề xuất kiến trúc tối ưu (No-Fork Hybrid + Logic Node Registry băm theo AST/Symbol + Lazy Depth) giúp Archify hỗ trợ sơ đồ chi tiết nhiều tầng, click xem giải thích tự nhiên/mini-flowchart và tái sử dụng node để tiết kiệm token lẫn thời gian agent (`0` thay đổi mã nguồn TDQ Workflow).
**Trước/Sau:** [docs/tdq/reports/2026-11-24-1106-research-archify-drilldown-nodes.html](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/reports/2026-11-24-1106-research-archify-drilldown-nodes.html)
**Đã kiểm:**
- Khảo sát và hợp nhất `14` chứng cứ mã nguồn + đo thực nghiệm vào `docs/tdq/artifacts/2026-11-24-1106-research-archify-drilldown-nodes/evidence.jsonl`
- Kiểm chứng live Chrome DevTools DOM/Accessibility Tree trên `docs/architecture/index.html` (`4/6` view lỗi inline fit, `0` lỗi console)
- Kiểm chứng `logic-node-schema-and-login-example.json` (`12` nodes, `5` tầng, `6` node tái sử dụng, chống chu trình) bằng Python `json.loads`
- Kiểm định toàn bộ tài liệu `QC-I1..I4`, `doc_lint.py` exit `0`, và `git diff --name-only dev -- scripts/ hooks/ plugins/ tools/ tests/` (`0` file mã nguồn bị sửa)
**Rủi ro hồi quy:** Không có (request `work_kind=investigate`, toàn bộ phát hiện và tài liệu đề xuất nằm cô lập trong `docs/tdq/`).
<!-- tdq-archify-binding:start -->
<!-- manifest: 2026-11-24-1106-research-archify-drilldown-nodes.manifest.json -->
<!-- manifest_digest: fb9cee10cbc6126f04162984fab78ccc102e2718bada5dddc9bd4fb18fa4caaf -->
<!-- tdq-archify-binding:end -->