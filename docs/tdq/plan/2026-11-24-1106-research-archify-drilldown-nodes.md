# PLAN — Nghiên cứu cải tiến Archify đa tầng drill-down và tái sử dụng Logic Node

Ngày: 2026-11-24 · Spec: ../spec/2026-11-24-1106-research-archify-drilldown-nodes.md (bản 1.0, ĐÃ DUYỆT)
Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md
Mode thực thi: main — simulate thắng sát nút với chênh lệch 0.0 phút (`main` 12.2 phút vs `team` 12.3 phút ở hệ số 1.5, leader giữ `T1.2` có nhãn `(mcp)` và chuỗi `P2`–`P3` nối tiếp); nếu chọn `subagent` vẫn chạy song song được `T1.1` và `T1.3` ở đợt 1 (ĐỀ XUẤT, user chốt lúc duyệt)
Trạng thái plan: HOÀN THÀNH · Work kind: investigate

> **Tóm tắt dễ hiểu:** Kế hoạch chia cuộc nghiên cứu thành ba đợt gọn nhẹ và hoàn toàn chỉ đọc mã nguồn. Đợt một chạy song song ba luồng kiểm chứng engine gốc, hạ tầng TDQ hiện có và mô hình kho Logic Node tiết kiệm token. Đợt hai và ba tổng hợp ma trận so sánh, dựng mẫu chuỗi đăng nhập nhiều tầng, chạy đủ cổng kiểm chứng bằng chứng và xuất báo cáo trực quan.

## Mục lục

- Phân bổ Model & Effort
- Quy tắc thi hành (áp cho mọi task)
- Thiết kế Trước vs Sau
- Ràng buộc toàn cục & Bản đồ Sở hữu Hợp đồng (Ownership Map)
- P1 — Khảo sát sâu và thu thập bằng chứng thực nghiệm (H1–H4)
- P2 — Tổng hợp kiến trúc, Schema JSON + Chuỗi Login mẫu & Bản thảo Báo cáo
- P3 — Log & kiểm chứng bắt buộc (`QC-I1..I4`)
- Cụm song song
- Luật file nóng (một file, nhiều task chạm)
- Definition of Done

## Phân bổ Model & Effort

> User được quyền đổi `type model` hoặc `effort` lúc duyệt plan. Thang model: [subagent-tuning.md](../../tdq-conventions/references/subagent-tuning.md).

| Pha | Vai trò | Model | Effort | Ghi chú |
|---|---|---|---|---|
| `implement` (`T1.1`, `T1.3`) | `tdq-explorer` (điều tra read-only + shard artifact) | `inherit` | `high` | Không cần worktree (`Worktree: none`), chỉ ghi vào shard được giao |
| `implement` (`T1.2`, `T2.1`, `T2.2`) | Leader (MCP Chrome DevTools + tổng hợp kiến trúc & schema) | `inherit` | `xhigh` | Giữ nhiệm vụ `(mcp)` và tổng hợp hệ thống trên main thread |
| `qc` (`T3.1`) | Leader (`muc_qc=full`, `QC-I1..I4`) | `inherit` | `high` | Chạy đối chiếu tự động `L1/L4/L2`, `doc_lint` và kiểm phạm vi `0` code |
| `report` | Leader (Archify HTML + Tailscale verify) | `inherit` | `medium` | Xuất cặp báo cáo MD + HTML một lần duy nhất |

## Quy tắc thi hành (áp cho mọi task)

1. Thứ tự phase là thứ tự phụ thuộc — không đảo (`P1` → `P2` → `P3`).
2. Mỗi task: đánh `[~]` (hoặc `[>]` khi giao subagent) trước khi bắt đầu; đổi sang `[x]` ngay khi tiêu chí kiểm đạt, cấm gộp tick cuối lượt.
3. Mọi task chỉ đọc mã nguồn sản phẩm và chỉ ghi vào file shard/tài liệu được khai ở `Chạm:`; tuyệt đối không sửa file trong `scripts/`, `hooks/`, `plugins/`, `tools/`, `tests/`.
4. Mọi phát hiện kỹ thuật phải lưu bằng chứng vào `docs/tdq/artifacts/2026-11-24-1106-research-archify-drilldown-nodes/` qua `py -3 -X utf8 scripts/tdq_team.py evidence add --shard <id> ...`.
5. QC FAIL → thêm task fix `QCn.x` vào mục QC của file này, sửa xong kiểm lại đến khi PASS.
6. Không commit hoặc push cho đến khi user yêu cầu rõ.
7. Tuân thủ đủ 6 mã cấm cơ học (`ANTI-1` đến `ANTI-6`), `doc_lint.py` exit `0` và `Work kind: investigate`.

## Thiết kế Trước vs Sau

| Khía cạnh | Hiện trạng (Trước) | Đích nghiên cứu đề xuất (Sau) |
|---|---|---|
| Luồng thực thi | `1` tầng phẳng: Overview → thẻ Flow → `1` modal diagram tĩnh (`master.model.json`) | `>= 5` tầng đệ quy: Flow tổng → click node → giải thích tự nhiên + mini flowchart + breadcrumb |
| Thành phần khảo sát | `C:\Users\admin\Documents\archify`, `scripts/*archify*.py`, `docs/architecture/index.html` | Báo cáo đề xuất kiến trúc lai (không fork upstream) + Logic Node Registry + Schema JSON & mẫu Login |

*Đối chiếu sơ đồ kiến trúc:* Spec `2026-11-24-1106-research-archify-drilldown-nodes.md` miễn bản xem trước Archify trước duyệt theo `investigate-mode.md:13`; WBS dưới đây ánh xạ 1–1 tới 4 đầu ra §2 và 5 cổng kiểm §6 của spec đã duyệt.

## Ràng buộc toàn cục & Bản đồ Sở hữu Hợp đồng (Ownership Map)

- Ràng buộc chung: Chỉ đọc mã nguồn sản phẩm (`0` file code sửa) · Mọi dẫn chứng ghi `path:line` thật hoặc lệnh kiểm thật · Ngôn ngữ báo cáo tiếng Việt (`doc_lang=vi`), tên riêng kỹ thuật giữ nguyên · File JSON parse chuẩn UTF-8.

| Hợp đồng / Ký hiệu (§2 & §3c) | File & Task sở hữu | Task / File tiêu thụ |
|---|---|---|
| Bằng chứng `S1` (năng lực upstream `tt-a1i/archify`) | `docs/tdq/artifacts/2026-11-24-1106-research-archify-drilldown-nodes/s1.md` (`T1.1`) | `T2.1`, `T2.2` |
| Bằng chứng `S2` (TDQ wrapper + DOM thực tế) | `docs/tdq/artifacts/2026-11-24-1106-research-archify-drilldown-nodes/s2.md` (`T1.2`) | `T2.1`, `T2.2` |
| Mô hình `S3` (Logic Node Registry, hash AST/symbol, token/latency) | `docs/tdq/artifacts/2026-11-24-1106-research-archify-drilldown-nodes/s3.md` (`T1.3`) | `T2.1`, `T2.2` |
| Schema JSON chuẩn + chuỗi Login `4–5` tầng + ma trận `S4` | `docs/tdq/artifacts/2026-11-24-1106-research-archify-drilldown-nodes/logic-node-schema-and-login-example.json`, `s4.md` (`T2.1`) | `T2.2`, `T3.1` |
| Báo cáo cuối + Archify HTML | `docs/tdq/reports/2026-11-24-1106-research-archify-drilldown-nodes.md`, `.html` (`T2.2`, `T3.1`) | User & cổng `Q1`–`Q5` |

## P1 — Khảo sát sâu và thu thập bằng chứng thực nghiệm (H1–H4)

- [x] **T1.1** (e10m) Shard `S1`: Khảo sát mã nguồn engine gốc `tt-a1i/archify` để kiểm chứng `H1` và `H4` — Test: `py -3 -c "import pathlib; p=pathlib.Path('docs/tdq/artifacts/2026-11-24-1106-research-archify-drilldown-nodes/s1.md'); assert p.is_file() and 'H1' in p.read_text(encoding='utf-8') and 'H4' in p.read_text(encoding='utf-8')"`
  - Req: `§1, §2#1-2, §5` · Ngoài phạm vi: `GIỮ NGUYÊN` toàn bộ thư mục `C:\Users\admin\Documents\archify` (chỉ đọc)
  - Chạm: `docs/tdq/artifacts/2026-11-24-1106-research-archify-drilldown-nodes/s1.md` (tạo mới)
  - Cần: Không
  - Giao tiếp: Consumes: `C:\Users\admin\Documents\archify\{viewer,archify,docs,DESIGN.md,PRODUCT.md,ROADMAP.md}` | Produces: `s1.md` + shard chứng cứ `s1.ev.jsonl`
  - Neo & Công cụ: `read_file` và lệnh chỉ đọc trên `C:\Users\admin\Documents\archify`; `write_file` tạo `s1.md`; `tdq_team.py evidence add --shard s1`
  - Trước → Sau: Chưa biết năng lực click/drill-down nội tại của `tt-a1i/archify` → Có bản đồ chính xác điểm hỗ trợ và điểm chặn cứng kèm `path:line`
  - Tiêu chí chấp nhận (EARS): KHI khảo sát xong `viewer/` và schema của `tt-a1i/archify`, HỆ THỐNG PHẢI ghi tối thiểu `4` chứng cứ `path:line` vào shard `s1` trả lời rõ cơ chế sự kiện click node, modal/panel, quy tắc `desktop-readability` và khả năng mở rộng không cần fork
  - Logic cốt lõi: Kiểm tra danh sách diagram types hỗ trợ trong `archify/`; đọc mã nguồn `viewer/` xem sự kiện `click`/overlay trên SVG node; đối chiếu `DESIGN.md` và `ROADMAP.md` về drill-down đa tầng
  - Ca góc hiểm & Assert: Kiểm tra xem SVG sinh ra có `data-node-id` hoặc attribute định danh ổn định để lớp vỏ TDQ gắn sự kiện ngoài không · `assert 'Verified' in s1_text and len(s1_ev_rows) >= 4`

- [x] **T1.2** (e10m) Shard `S2`: Khảo sát 4 module `scripts/*archify*.py`, `master.model.json` và kiểm chứng DOM/SVG thực tế của `docs/architecture/index.html` — Test: `py -3 -c "import pathlib; p=pathlib.Path('docs/tdq/artifacts/2026-11-24-1106-research-archify-drilldown-nodes/s2.md'); assert p.is_file() and 'H2' in p.read_text(encoding='utf-8') and 'index.html' in p.read_text(encoding='utf-8')"`
  - Dùng: `tdq-browser-test` / `chrome-devtools` (mcp)
  - Để: Kiểm chứng hành vi click/modal và cấu trúc SVG thực tế của `docs/architecture/index.html` (pre-flight Chrome DevTools trước; fallback đọc trực tiếp HTML/JS tĩnh nếu không có CDP sống)
  - Ra: `docs/tdq/artifacts/2026-11-24-1106-research-archify-drilldown-nodes/s2.md`
  - Kiểm: `py -3 -c "import pathlib; t=pathlib.Path('docs/tdq/artifacts/2026-11-24-1106-research-archify-drilldown-nodes/s2.md').read_text(encoding='utf-8'); assert 'DOM' in t and 'master.model.json' in t"`
  - Không dùng cho: Không tự sửa `docs/architecture/index.html` hay chạy E2E trên các trang ngoài phạm vi Archify
  - Req: `§1, §2#1-2, §3b, §5` · Ngoài phạm vi: `GIỮ NGUYÊN` toàn bộ `scripts/*archify*.py` và `docs/architecture/`
  - Chạm: `docs/tdq/artifacts/2026-11-24-1106-research-archify-drilldown-nodes/s2.md` (tạo mới)
  - Cần: Không
  - Giao tiếp: Consumes: `scripts/{tdq_archify,archify_model,archify_artifacts,archify_delivery}.py`, `docs/tdq/models/master.model.json`, `docs/architecture/index.html` | Produces: `s2.md` + shard `s2.ev.jsonl`
  - Neo & Công cụ: `read_file` trên 4 module TDQ + Chrome DevTools MCP pre-flight check (`list_pages`) hoặc phân tích HTML tĩnh; `write_file` tạo `s2.md`
  - Trước → Sau: Mới biết sơ bộ 4 file wrapper → Nắm trọn đường đi từ `master.model.json` tới modal hiện tại, giới hạn 1 tầng và chi phí kích thước thực tế của `index.html`
  - Tiêu chí chấp nhận (EARS): KHI hoàn tất `S2`, HỆ THỐNG PHẢI ghi tối thiểu `4` chứng cứ vào shard `s2` nêu rõ dung lượng `docs/architecture/index.html`, cách `tdq_archify.py` tạo modal flow card hiện tại và lý do luật `archify-lifecycle.md:27` cấm chèn `onclick` vào native node
  - Logic cốt lõi: Đọc `sync_master` và hàm dựng HTML modal trong `scripts/tdq_archify.py`; kiểm tra kích thước các file trong `docs/architecture/`; kiểm thực tế DOM/SVG của `index.html`
  - Ca góc hiểm & Assert: Nếu Chrome CDP chưa bật thì ghi rõ kết quả pre-flight và chuyển sang phân tích tĩnh DOM/JS trong `index.html` (không bịa kết quả browser) · `assert len(s2_ev_rows) >= 4`

- [x] **T1.3** (e10m) Shard `S3`: Thiết kế và thẩm định Logic Node Registry, chiến lược hash chống false-dirty, Incremental + Lazy Depth và ước lượng định lượng token/thời gian agent (`H2`, `H3`) — Test: `py -3 -c "import pathlib; p=pathlib.Path('docs/tdq/artifacts/2026-11-24-1106-research-archify-drilldown-nodes/s3.md'); assert p.is_file() and 'H3' in p.read_text(encoding='utf-8') and 'token' in p.read_text(encoding='utf-8').lower()"`
  - Req: `§1, §2#1-2, §3c, §5` · Ngoài phạm vi: `GIỮ NGUYÊN` toàn bộ `scripts/archify_artifacts.py` và `graphify-out/`
  - Chạm: `docs/tdq/artifacts/2026-11-24-1106-research-archify-drilldown-nodes/s3.md` (tạo mới)
  - Cần: Không
  - Giao tiếp: Consumes: `scripts/archify_artifacts.py` (`source_fingerprint`), `scripts/archify_model.py`, `docs/tdq/models/*.json` | Produces: `s3.md` + shard `s3.ev.jsonl`
  - Neo & Công cụ: `read_file` trên `archify_artifacts.py` + `docs/tdq/models/`; `write_file` tạo `s3.md`; `tdq_team.py evidence add --shard s3`
  - Trước → Sau: Chưa có thiết kế kho node tái dùng và số đo tiết kiệm token → Có thuật toán hash cấp symbol/AST + truyền bẩn + bảng ước lượng token và thời gian agent trên kịch bản `120` node, `5` tầng
  - Tiêu chí chấp nhận (EARS): KHI hoàn tất `S3`, HỆ THỐNG PHẢI chứng minh được công thức so sánh chi phí token và thời gian xử lý giữa vẽ lại toàn phần ($O(N)$) so với Incremental + Lazy Depth ($O(D)$), cùng cơ chế chống chu trình, chống false-dirty và phân tách node `planned` với `working-tree`
  - Logic cốt lõi: Phân tích `source_fingerprint` hiện có; thiết kế cấu trúc kho mảnh `nodes/<id>.json` + `index.json`; tính định lượng token đọc/sinh và thời gian render khi sửa `1–3` hàm trong dự án `> 100` node; phân tích fallback CORS khi mở `file://`
  - Ca góc hiểm & Assert: Phải bao phủ đủ 3 ca biên: vòng lặp đệ quy `A -> B -> A`, sửa dòng dịch số nhưng không đổi thân hàm (`symbol_hash`), và node Spec `planned` chưa có file nguồn · `assert 'symbol' in s3_text and 'cycle' in s3_text.lower() or 'chu trình' in s3_text.lower()`

**Xong P1 khi**: Cả 3 shard `s1.md`, `s2.md`, `s3.md` và `s1..s3.ev.jsonl` tồn tại trên đĩa, `tdq_team.py evidence merge` hợp nhất đủ `>= 12` chứng cứ với `0` lỗi.

## P2 — Tổng hợp kiến trúc, Schema JSON + Chuỗi Login mẫu & Bản thảo Báo cáo

- [x] **T2.1** (e12m) Hợp nhất `evidence.jsonl`, soạn shard `S4` (ma trận 3 phương án + lộ trình triển khai) và tạo file Schema JSON Logic Node Registry kèm ví dụ chuỗi Login `4–5` tầng — Test: `py -3 -c "import json, pathlib; d=json.loads(pathlib.Path('docs/tdq/artifacts/2026-11-24-1106-research-archify-drilldown-nodes/logic-node-schema-and-login-example.json').read_text(encoding='utf-8')); assert len(d['example_login_registry']['nodes']) >= 8 and d['example_login_registry']['max_depth'] >= 4"`
  - Req: `§1, §2#1-3, §3, §3c` · Ngoài phạm vi: `GIỮ NGUYÊN` mã nguồn sản phẩm
  - Chạm: `docs/tdq/artifacts/2026-11-24-1106-research-archify-drilldown-nodes/s4.md` (tạo mới), `docs/tdq/artifacts/2026-11-24-1106-research-archify-drilldown-nodes/logic-node-schema-and-login-example.json` (tạo mới)
  - Cần: `T1.1`, `T1.2`, `T1.3`
  - Giao tiếp: Consumes: `s1.md`, `s2.md`, `s3.md`, `evidence.jsonl` | Produces: `s4.md`, `logic-node-schema-and-login-example.json`
  - Neo & Công cụ: `tdq_team.py evidence merge`; `write_file` tạo `s4.md` và `logic-node-schema-and-login-example.json`
  - Trước → Sau: Dữ liệu bằng chứng còn rời rạc ở 3 shard → Hợp nhất thành 1 đề xuất kiến trúc tối ưu (so sánh 3 phương án), lộ trình triển khai từng pha và mẫu dữ liệu Login `4–5` tầng chạy kiểm được bằng `json.loads`
  - Tiêu chí chấp nhận (EARS): KHI chạy `json.loads` trên `logic-node-schema-and-login-example.json`, HỆ THỐNG PHẢI trả mã `0`, có đủ định nghĩa JSON Schema của Logic Node và ví dụ chuỗi Login `>= 4` tầng (nhập user/pass → kiểm tra nhớ login → ghi token/storage → mã hóa gửi server → nhận access token) thể hiện ít nhất `2` node tái sử dụng (`reused_by`)
  - Logic cốt lõi: Merge bằng chứng; lập ma trận so sánh Phương án 1 (Bọc TDQ giữ nguyên upstream + Lazy Shell), Phương án 2 (Fork viewer upstream), Phương án 3 (Engine ngoài hoàn toàn); viết JSON Schema + cây Login `4–5` tầng đầy đủ giải thích tự nhiên và mini-flow
  - Ca góc hiểm & Assert: Ví dụ Login phải có ít nhất `1` nhánh lỗi (sai mật khẩu / token hết hạn) và `1` node tái sử dụng chung giữa 2 flow khác nhau · `assert any(len(n.get('reused_by', [])) >= 2 for n in d['example_login_registry']['nodes'])`

- [x] **T2.2** (e10m) Soạn bản thảo báo cáo tổng hợp (`docs/tdq/reports/2026-11-24-1106-research-archify-drilldown-nodes.md`) và tệp ứng viên Archify (`bao-cao.archify.md`) — Test: `py -3 -X utf8 scripts/doc_lint.py docs/tdq/reports/2026-11-24-1106-research-archify-drilldown-nodes.md`
  - Req: `§2#4, §4, §6` · Ngoài phạm vi: `GIỮ NGUYÊN` mã nguồn sản phẩm
  - Chạm: `docs/tdq/reports/2026-11-24-1106-research-archify-drilldown-nodes.md` (tạo mới), `docs/tdq/artifacts/2026-11-24-1106-research-archify-drilldown-nodes/bao-cao.archify.md` (tạo mới)
  - Cần: `T2.1`
  - Giao tiếp: Consumes: `s1.md..s4.md`, `evidence.jsonl`, `logic-node-schema-and-login-example.json`, `tdq_timing.py show` | Produces: báo cáo MD + candidate Archify MD
  - Neo & Công cụ: `write_file` tạo report MD và `bao-cao.archify.md`; `doc_lint.py` kiểm định
  - Trước → Sau: Chưa có tài liệu báo cáo tổng hợp cho user → Có báo cáo đầy đủ Layer-1 dễ đọc (10–15 giây) + Layer-2 chi tiết kỹ thuật, 4 mục Trước/Sau/Đã test/Kết quả, bảng kết luận `H1`–`H4`, nhãn tin cậy và thân PR soạn sẵn
  - Tiêu chí chấp nhận (EARS): KHI chạy `doc_lint.py` trên báo cáo, HỆ THỐNG PHẢI trả `0` vi phạm (exit `0`), trích dẫn đầy đủ ID bằng chứng từ `evidence.jsonl` và gắn nhãn tin cậy (`Verified`/`Single-source`/`Inferred`) cho mọi phát hiện lớn
  - Logic cốt lõi: Tổng hợp súc tích đề xuất tối ưu, bảng ước lượng token/thời gian agent, minh họa chuỗi Login nhiều tầng, rủi ro & lộ trình triển khai cho request code sau; soạn `bao-cao.archify.md` với mỗi sơ đồ `<= 5` node/hàng đạt `desktop-readability`
  - Ca góc hiểm & Assert: Bọc nguyên đầu ra `tdq_timing.py show` trong khối fenced code để đạt luật `R12` tiếng Việt của `doc_lint.py` · `assert rc == 0`

**Xong P2 khi**: Báo cáo MD qua `doc_lint.py` exit `0`, file JSON mẫu parse hợp lệ và `bao-cao.archify.md` sẵn sàng render.

## P3 — Log & kiểm chứng bắt buộc (`QC-I1..I4`)

Log: BỎ — Request này thuộc `work_kind=investigate`, không thêm hoặc sửa mã nguồn chạy được trong TDQ Workflow.

- [x] **T3.1** (e5m) Chạy kiểm chứng toàn diện `QC-I1..I4` (`Q1`–`Q5`), xuất bản Archify HTML báo cáo và xác nhận HTTP `200` trên Tailscale Serve — Test: `py -3 -X utf8 scripts/tdq_archify.py verify --document docs/tdq/reports/2026-11-24-1106-research-archify-drilldown-nodes.md --manifest docs/tdq/reports/2026-11-24-1106-research-archify-drilldown-nodes.manifest.json`
  - Req: `§2#4, §6 Q1-Q5` · Ngoài phạm vi: `GIỮ NGUYÊN` toàn bộ mã nguồn sản phẩm
  - Chạm: `docs/tdq/reports/2026-11-24-1106-research-archify-drilldown-nodes.html` (tạo mới)
  - Cần: `T2.2`
  - Giao tiếp: Consumes: `bao-cao.archify.md`, report MD, `evidence.jsonl` | Produces: report HTML + manifest + biên bản `docs/tdq/qc/2026-11-24-1106-research-archify-drilldown-nodes.md`
  - Neo & Công cụ: `tdq_archify.py render` + `verify`; script Python kiểm tự động `QC-I1` (ID + `path:line` + `git diff`) và `urllib` kiểm HTTP `200`
  - Trước → Sau: Chưa xác minh máy toàn bộ trích dẫn và bản HTML trực quan → Xác nhận `100%` `[EV]` và `path:line` tồn tại thật, `0` file mã nguồn sửa, Archify `current` và HTTP `200`
  - Tiêu chí chấp nhận (EARS): KHI chạy xong `T3.1`, HỆ THỐNG PHẢI ghi biên bản QC với `5/5` mục `Q1`–`Q5` đạt `PASS`, `tdq_archify.py verify` trả `"status": "current"` và URL Tailscale Serve trả mã `200`
  - Logic cốt lõi: Chạy script đối chiếu `QC-I1`; rà L2 từng phát hiện chính; kiểm `git diff --name-only dev -- scripts/ hooks/ plugins/ tools/ tests/` rỗng; render + verify Archify HTML và probe HTTP `200`
  - Ca góc hiểm & Assert: Nếu `bao-cao.archify.md` gặp lỗi `desktop-readability`, chia nhỏ sơ đồ xuống `<= 4` node/hàng rồi dựng lại trước khi verify · `assert verify_json['status'] == 'current' and http_status == 200`

**Xong P3 khi**: `5/5` hạng mục `Q1`–`Q5` đạt `PASS` trong biên bản QC và Archify HTML phục vụ HTTP `200`.

## Cụm song song

- **Đợt 1 (chạy song song 3 luồng, `Chạm:` hoàn toàn tách rời):**
  - `T1.1` (`tdq-explorer`, `Worktree: none`) → `s1.md`
  - `T1.2` (Leader giữ trực tiếp vì mang nhãn `(mcp)`) → `s2.md`
  - `T1.3` (`tdq-explorer`, `Worktree: none`) → `s3.md`
- **Đợt 2 (tuần tự tổng hợp trên Leader sau khi Đợt 1 hội tụ):** `T2.1` → `T2.2` → `T3.1`.

## Luật file nóng (một file, nhiều task chạm)

Không có file nóng trong toàn bộ kế hoạch: 6 task `T1.1`–`T3.1` đều có đường dẫn `Chạm:` tách rời 100%, không xảy ra xung đột ghi song song. Sổ bằng chứng trung tâm `evidence.jsonl` chỉ được ghi qua lệnh `tdq_team.py evidence add --shard <id>` (khóa NTFS lock) và hợp nhất một lần ở `T2.1`.

## Definition of Done

Trỏ về §6 của spec `2026-11-24-1106-research-archify-drilldown-nodes.md` (`muc_qc=full`):

- [x] Q1 `QC-I1` Grounding tự động (`100%` `[EV]` ID trong `evidence.jsonl`, `100%` `path:line` tồn tại trên đĩa, `0` placeholder) — chạy script Python kiểm tra `evidence.jsonl` và biên dòng trên `docs/tdq/reports/2026-11-24-1106-research-archify-drilldown-nodes.md`
- [x] Q2 `QC-I2` Đối chiếu nguyên văn (`L2` xác minh trực tiếp nguồn `tt-a1i/archify` và `scripts/*archify*.py`) — ghi nhận đối chiếu trong `docs/tdq/qc/2026-11-24-1106-research-archify-drilldown-nodes.md`
- [x] Q3 `QC-I3` Kiểm chứng đủ `4` giả thuyết `H1`–`H4` kèm phản ví dụ / điểm nghẽn thực tế — kiểm tra đủ 4 kết luận rõ ràng trong báo cáo và 4 shard `s1`–`s4`
- [x] Q4 `QC-I4` Nhãn độ tin cậy (`Verified`/`Single-source`/`Inferred`), Schema JSON mẫu hợp lệ và tài liệu sạch lỗi — `py -3 -c "import json, pathlib; json.loads(pathlib.Path('docs/tdq/artifacts/2026-11-24-1106-research-archify-drilldown-nodes/logic-node-schema-and-login-example.json').read_text(encoding='utf-8'))"` và `py -3 -X utf8 scripts/doc_lint.py docs/tdq/reports/2026-11-24-1106-research-archify-drilldown-nodes.md`
- [x] Q5 Ranh giới phạm vi `0` file mã nguồn sửa & Archify HTML xác minh trực quan — `git diff --name-only dev -- scripts/ hooks/ plugins/ tools/ tests/` rỗng, `py -3 -X utf8 scripts/tdq_archify.py verify --document docs/tdq/reports/2026-11-24-1106-research-archify-drilldown-nodes.md --manifest docs/tdq/reports/2026-11-24-1106-research-archify-drilldown-nodes.manifest.json` trả `current`, và kiểm HTTP `200` trên Tailscale Serve
