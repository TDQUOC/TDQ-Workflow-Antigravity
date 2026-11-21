# PLAN — Điều tra & thiết kế chuẩn mặc định trình bày trực quan, dễ hiểu cho TDQ-Workflow

Ngày: 2026-11-21 · Spec: ../spec/2026-11-21-1736-mac-dinh-trinh-bay-de-hieu.md (bản 1.0, ĐÃ DUYỆT) · Lane: full · Work kind: investigate
Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md
Mode thực thi: subagent — Winner: đội (gap 3.0 minutes: subagent 9.2p vs main 12.2p qua 6 task / 3 wave với hệ số 1.5x theo tdq_bench.py simulate) (ĐÃ CHỐT)
Trạng thái plan: HOÀN THÀNH

> **Tóm tắt dễ hiểu:** Chia điều tra thành `3` đợt không đụng mã nguồn (`no_worktree`): Đợt `1` chạy `3` mũi song song gồm kiểm nguồn trong repo, soi transcript các phiên gần đây và research UX báo cáo AI bên ngoài; Đợt `2` tổng hợp bằng chứng, phản chứng `4` giả thuyết `H1`–`H4`, thiết kế kiến trúc mặc định kèm mẫu Trước–Sau và dựng báo cáo trực quan HTML; Đợt `3` kiểm chứng chéo `QC-I1..I4`.

## Mục lục

- Phân bổ Model & Effort
- Quy tắc thi hành (áp cho mọi task)
- Thiết kế Trước vs Sau
- Ràng buộc toàn cục & Bản đồ Sở hữu Hợp đồng (Ownership Map)
- P1 — Wave 1: Thu thập bằng chứng nội bộ, Transcript & Research ngoài (`no_worktree`)
- P2 — Wave 2: Gộp chứng cứ, Phản chứng `H1`–`H4`, Thiết kế & Báo cáo HTML
- P3 — Log & kiểm chứng bắt buộc (`QC-I1..I4`)
- Cụm song song
- Luật file nóng
- Definition of Done

## Phân bổ Model & Effort

| Pha | Vai trò | Model | Effort | Ghi chú |
|---|---|---|---|---|
| `implement` (`P1`) | `tdq-explorer` / `tdq-debugger` / Leader `(mcp)` | `inherit` | `high` | Có thể đổi sang `pro`/`flash`; nhánh `T1.3 (mcp)` do Leader giữ |
| `implement` (`P2`) | Leader tổng hợp & dựng Archify HTML `(mcp)` | `inherit` | `high` | Giữ `inherit` để giữ mạch phản chứng và nhất quán `3` bề mặt |
| `qc` (`P3`) | `tdq-reviewer` / Leader (`QC-I1..I4`) | `inherit` | `high` | Kiểm chéo `100%` `[EV-xxx]` và phản biện `QC-I3` không bỏ sót |
| `report` | Leader xuất HTML & Tailscale | `inherit` | `medium` | Xuất `1` bản cuối sau khi `QC-I1..I4` xanh |

## Quy tắc thi hành (áp cho mọi task)

1. Thứ tự phase là thứ tự phụ thuộc — không đảo.
2. Mỗi task: đánh `[~]` (hoặc `[>]`) khi bắt đầu → chạy kiểm tra nguồn thật → đổi sang `[x]` NGAY vào file này.
3. Mọi task dùng `no_worktree`; tuyệt đối không mở git worktree cho shard tài liệu.
4. Giữ `0` sửa đổi ngoài thư mục `docs/`; phát hiện cần sửa code thì báo user qua `escalate-to-build` hoặc mở request sau.
5. Không commit/push cho đến khi user yêu cầu.
6. Tuân thủ `6` mã cấm (`ANTI-1`..`ANTI-6`) và chuẩn dẫn chứng `[EV-xxx]`.

## Thiết kế Trước vs Sau

| Khía cạnh | Hiện trạng (Trước) | Thiết kế điều tra (Sau) |
|---|---|---|
| Cách tìm nguyên nhân | Đọc lướt rule và vá thêm câu nhắc ở `0917` | Đo số liệu thật từ repo + transcript (`0917`, `1536`) + research ngoài |
| Tổ chức bằng chứng | Ghi rải rác trong chat, thiếu mã truy vết | Chuẩn hóa shard `.ev.jsonl` + gộp `evidence.jsonl` theo `[EV-xxx]` |
| Kiểm soát sai lệch | Chưa có vòng phản chứng | Phản chứng `H1`–`H4` + kiểm chứng `QC-I1..I4` trước khi xuất báo cáo |

## Ràng buộc toàn cục & Bản đồ Sở hữu Hợp đồng (Ownership Map)

- Không sửa bất kỳ file nào ngoài `docs/`; mỗi digest shard trả về tối đa `1.500` ký tự; giữ `doc_lint.py` `0` lỗi (`R5 <= 40` từ/câu).
- Sổ `evidence.jsonl` giữ chuẩn `Claim + Source + Verbatim Excerpt` theo `tdq_team.py evidence add|merge`.

| Hợp đồng / Ký hiệu (§3c) | File & Task sở hữu | Task / File tiêu thụ |
|---|---|---|
| `t1.1.ev.jsonl` + bảng đếm rule (`H1`–`H3`) | `docs/tdq/artifacts/2026-11-21-1736-mac-dinh-trinh-bay-de-hieu/t1.1-repo-audit.md` (`T1.1`) | `T2.1` (`evidence.jsonl`, báo cáo cuối) |
| `t1.2.ev.jsonl` + đối chiếu transcript (`0917`, `1536`) | `docs/tdq/artifacts/2026-11-21-1736-mac-dinh-trinh-bay-de-hieu/t1.2-transcript-rca.md` (`T1.2`) | `T2.1` (`evidence.jsonl`, mẫu Trước–Sau) |
| `t1.3.ev.jsonl` + hồ sơ research nguồn ngoài | `docs/tdq/research/2026-11-21-1736-mac-dinh-trinh-bay-de-hieu.md` (`T1.3`) | `T2.1` (`evidence.jsonl`, thiết kế giải pháp) |
| `evidence.jsonl` + báo cáo cuối `.md` | `docs/tdq/reports/2026-11-21-1736-mac-dinh-trinh-bay-de-hieu.md` (`T2.1`) | `T2.2` (Archify HTML), `T3.1` (`QC-I1..I4`) |
| `bao-cao.archify.md` + báo cáo `.html` | `docs/tdq/reports/2026-11-21-1736-mac-dinh-trinh-bay-de-hieu.html` (`T2.2`) | `T3.1` (`Q5`), Tailscale Serve |

## P1 — Wave 1: Thu thập bằng chứng nội bộ, Transcript & Research ngoài (`no_worktree`)

- [x] **T1.1** (e8m) Audit toàn bộ chuỗi rule, skill, template, hook và `doc_lint.py` (`rules/AGENTS.md`, `docs/claude-md-mau.md`, `user-facing-block.md`, `spec-template.md`, `plan-template.md`, `report-template.md`, `qc.md`, `agy_stop_gate.py`) kiểm `H1`–`H3` — Test: `py -3 -X utf8 scripts/doc_lint.py docs/tdq/artifacts/2026-11-21-1736-mac-dinh-trinh-bay-de-hieu/t1.1-repo-audit.md`
  - Req: `§1, §2#1, §3c#1, Q1` · Ngoài phạm vi: `KHÔNG` sửa mã nguồn trong `skills/`, `hooks/`, `scripts/`, `agents/` · Worktree: `no_worktree`
  - Chạm: `docs/tdq/artifacts/2026-11-21-1736-mac-dinh-trinh-bay-de-hieu/t1.1-repo-audit.md`, `docs/tdq/artifacts/2026-11-21-1736-mac-dinh-trinh-bay-de-hieu/t1.1.ev.jsonl`
  - Sinh ra: `docs/tdq/artifacts/2026-11-21-1736-mac-dinh-trinh-bay-de-hieu/t1.1-repo-audit.md`, `docs/tdq/artifacts/2026-11-21-1736-mac-dinh-trinh-bay-de-hieu/t1.1.ev.jsonl`
  - Cần: Không
  - Giao tiếp: Consumes: `rules/`, `skills/`, `hooks/`, `scripts/doc_lint.py`, `docs/tdq/token-budget.json` | Produces: bảng đối chiếu độ sâu nạp rule, token trọng số và luật `doc_lint.py` vào `t1.1-repo-audit.md` + `t1.1.ev.jsonl`
  - Neo & Công cụ: Đọc tuần tự bằng `read_file` và đối chiếu caller qua `rg`/`LSP`, ghi shard bằng `write_file` + `tdq_team.py evidence add`
  - Trước → Sau: chưa biết điểm gãy nào trong chuỗi rule/hook làm chữ dễ hiểu bị chìm → có bảng định lượng token, mức ưu tiên và lỗ hổng lint kèm `path:line` thật
  - Tiêu chí chấp nhận (EARS): KHI hoàn tất `T1.1`, TẤT CẢ file luật trình bày cốt lõi PHẢI được đo token thực, kiểm vị trí nạp và gắn mã `[EV-xxx]` hợp lệ trên đĩa
  - Logic cốt lõi: liệt kê chuỗi prompt khởi đầu và lúc viết `spec`/`report`/`chat`, đếm tỷ lệ nhắc bằng chứng vs nhắc dễ hiểu, kiểm `doc_lint.py` (`R5`, `R12`, `R13`) đang kiểm và bỏ sót gì
  - Ca góc hiểm & Assert: mọi đường dẫn trích dẫn phải tồn tại (`os.path.isfile`); `assert doc_lint == 0` và số bản ghi trong `t1.1.ev.jsonl` `>= 4`

- [x] **T1.2** (e8m) Soi thực nghiệm các phiên và báo cáo gần đây (`2026-11-21-0917`, `2026-11-21-1536`, lịch sử user nhắc "dễ hiểu hơn") tách `Manifestation` vs `Point-of-Commitment` — Test: `py -3 -X utf8 scripts/doc_lint.py docs/tdq/artifacts/2026-11-21-1736-mac-dinh-trinh-bay-de-hieu/t1.2-transcript-rca.md`
  - Req: `§1, §2#1, §3c#1, Q1` · Ngoài phạm vi: `KHÔNG` chỉnh sửa các file report/spec cũ hay transcript nguồn · Worktree: `no_worktree`
  - Chạm: `docs/tdq/artifacts/2026-11-21-1736-mac-dinh-trinh-bay-de-hieu/t1.2-transcript-rca.md`, `docs/tdq/artifacts/2026-11-21-1736-mac-dinh-trinh-bay-de-hieu/t1.2.ev.jsonl`
  - Sinh ra: `docs/tdq/artifacts/2026-11-21-1736-mac-dinh-trinh-bay-de-hieu/t1.2-transcript-rca.md`, `docs/tdq/artifacts/2026-11-21-1736-mac-dinh-trinh-bay-de-hieu/t1.2.ev.jsonl`
  - Cần: Không
  - Giao tiếp: Consumes: `docs/tdq/reports/2026-11-21-0917-*`, `docs/tdq/reports/2026-11-21-1536-*`, `docs/tdq/spec/2026-11-21-1536-*`, transcript phiên hiện tại `abe6cf12` | Produces: phân tích `Manifestation` vs `Point-of-Commitment` kèm chỉ số mật độ từ/backtick trong `t1.2-transcript-rca.md` + `t1.2.ev.jsonl`
  - Neo & Công cụ: Phân tích nội dung thực bằng Python đếm số từ, số cụm `` ` ``, độ dài đoạn mở đầu chat và đối chiếu thời điểm model chuyển từ mạch dễ hiểu sang nhồi kỹ thuật
  - Trước → Sau: chỉ cảm nhận bằng mắt là "dài và khó hiểu" → có số đo cụ thể trên từng sản phẩm `0917` và `1536` chỉ rõ chỗ trượt về jargon
  - Tiêu chí chấp nhận (EARS): KHI đo `spec`/`report`/chat của `0917` và `1536`, HỆ THỐNG PHẢI trích xuất được số từ/đoạn, tỷ lệ ký hiệu kỹ thuật (backtick, SHA, path) và chỉ ra điểm kích hoạt đầu tiên
  - Logic cốt lõi: tách `3` nhóm mẫu (`spec`, `report`, phản hồi chat trước/sau khi user nhắc "ngắn gọn, dễ hiểu hơn"), chạy đo mật độ bằng Python trên đúng các file thật, tìm `Point-of-Commitment`
  - Ca góc hiểm & Assert: không suy diễn từ trí nhớ; số từ/mật độ in ra phải khớp kết quả script đo trực tiếp và `assert doc_lint == 0`

- [x] **T1.3** (e10m) Research nguồn ngoài (`>= 3` nguồn uy tín/khác góc nhìn kèm URL sống) về progressive disclosure, cognitive load cho người đọc không chuyên và kỹ thuật ép LLM giữ văn phong — Test: `py -3 -X utf8 scripts/doc_lint.py docs/tdq/research/2026-11-21-1736-mac-dinh-trinh-bay-de-hieu.md`
  - Dùng: `tdq-browser-research` (mcp)
  - Để: thu thập và trích dẫn nguồn ngoài chất lượng cao (Anthropic/OpenAI prompt engineering, Nielsen Norman Group, nghiên cứu LLM instruction hierarchy / lost-in-the-middle), nạp skill TRƯỚC bước thu thập
  - Ra: `docs/tdq/research/2026-11-21-1736-mac-dinh-trinh-bay-de-hieu.md` và `docs/tdq/artifacts/2026-11-21-1736-mac-dinh-trinh-bay-de-hieu/t1.3.ev.jsonl`
  - Kiểm: `py -3 -X utf8 scripts/doc_lint.py docs/tdq/research/2026-11-21-1736-mac-dinh-trinh-bay-de-hieu.md`
  - Không dùng cho: kiểm tra mã nguồn nội bộ TDQ hay nghiệm thu giao diện HTML (`T2.2`)
  - Req: `§1, §2#2, §3c#2, Q2` · Ngoài phạm vi: `KHÔNG` bịa URL hoặc sao chép cả trang web dài vào ngữ cảnh chính · Worktree: `no_worktree`
  - Chạm: `docs/tdq/research/2026-11-21-1736-mac-dinh-trinh-bay-de-hieu.md`, `docs/tdq/artifacts/2026-11-21-1736-mac-dinh-trinh-bay-de-hieu/t1.3.ev.jsonl`
  - Sinh ra: `docs/tdq/research/2026-11-21-1736-mac-dinh-trinh-bay-de-hieu.md`, `docs/tdq/artifacts/2026-11-21-1736-mac-dinh-trinh-bay-de-hieu/t1.3.ev.jsonl`
  - Cần: Không
  - Giao tiếp: Consumes: `tavily-primary` (`tavily_search`/`tavily_extract`), Chrome MCP nếu trang SPA | Produces: `>= 3` nguồn thực có URL sống + quy tắc áp dụng vào TDQ
  - Neo & Công cụ: Chạy `tavily_search` đa góc nhìn (`progressive disclosure UX AI reports`, `LLM instruction placement recency prompt compliance`, `plain language readability lint`) và ghi kết quả có lọc qua `write_file` + `tdq_team.py evidence add`
  - Trước → Sau: chỉ dựa vào kinh nghiệm nội bộ → có `>= 3` bằng chứng chuẩn quốc tế về cấu trúc `BLUF`/progressive disclosure và cơ chế chống trôi phong cách LLM
  - Tiêu chí chấp nhận (EARS): KHI hoàn tất `T1.3`, file research PHẢI liệt kê đủ `Query → URL sống → Bài học áp dụng cho TDQ` và pass `doc_lint.py`
  - Logic cốt lõi: chạy `3` truy vấn bổ sung nhau, kiểm trạng thái truy cập URL nguồn chính thức, tóm tắt gọn và ánh xạ trực tiếp sang `3` bề mặt của TDQ
  - Ca góc hiểm & Assert: nếu một nguồn bị chặn hoặc lỗi timeout thì chuyển nhánh khác qua `tdq-browser-research`; `assert doc_lint == 0` và số nguồn URL thật `>= 3`

**Xong P1 khi**: cả `3` shard `t1.1`, `t1.2`, `t1.3` đều tồn tại, sạch `doc_lint` và mỗi shard có bản ghi `.ev.jsonl`.

## P2 — Wave 2: Gộp chứng cứ, Phản chứng `H1`–`H4`, Thiết kế & Báo cáo HTML

- [x] **T2.1** (e12m) Gộp `evidence.jsonl` qua `tdq_team.py evidence merge`, phản chứng `4` giả thuyết `H1`–`H4`, thiết kế kiến trúc mặc định `2` tầng (chat, `.md`, HTML + cơ chế nhắc/lint dưới trần `3.500` token) và soạn báo cáo + bộ mẫu Trước–Sau — Test: `py -3 -X utf8 scripts/doc_lint.py docs/tdq/reports/2026-11-21-1736-mac-dinh-trinh-bay-de-hieu.md`
  - Req: `§1, §2#1, §2#3, §3c#3-4, Q1, Q3` · Ngoài phạm vi: `KHÔNG` sửa `skills/`, `hooks/`, `scripts/`, `AGENTS.md` hay `soul.md` trong request này · Worktree: `no_worktree`
  - Chạm: `docs/tdq/artifacts/2026-11-21-1736-mac-dinh-trinh-bay-de-hieu/evidence.jsonl`, `docs/tdq/reports/2026-11-21-1736-mac-dinh-trinh-bay-de-hieu.md`
  - Sinh ra: `docs/tdq/artifacts/2026-11-21-1736-mac-dinh-trinh-bay-de-hieu/evidence.jsonl`, `docs/tdq/reports/2026-11-21-1736-mac-dinh-trinh-bay-de-hieu.md`
  - Cần: `T1.1`, `T1.2`, `T1.3`
  - Giao tiếp: Consumes: `t1.1-repo-audit.md`, `t1.2-transcript-rca.md`, `research/2026-11-21-1736-*.md`, `t1.*.ev.jsonl` | Produces: sổ `evidence.jsonl` hợp nhất và báo cáo `reports/2026-11-21-1736-mac-dinh-trinh-bay-de-hieu.md` hoàn chỉnh
  - Neo & Công cụ: Chạy `tdq_team.py evidence merge --slug 2026-11-21-1736-mac-dinh-trinh-bay-de-hieu`, đối chiếu từng `H1`–`H4` bằng bằng chứng thuận/nghịch, soạn báo cáo theo `report-template.md` + `Tóm tắt dễ hiểu` + `4` phần + `tdq_timing.py show`
  - Trước → Sau: các mảnh bằng chứng nằm rời ở `3` nhánh → tổng hợp thành chẩn đoán thống nhất, giải pháp kiến trúc mặc định kèm mẫu Trước–Sau cho chat, `spec`, `report`
  - Tiêu chí chấp nhận (EARS): KHI đọc báo cáo cuối, người dùng không chuyên kỹ thuật PHẢI hiểu nguyên nhân trong `15` giây ở phần mở đầu, còn kỹ sư kiểm được đủ `[EV-xxx]`, nhãn độ tin cậy và mẫu Trước–Sau cụ thể
  - Logic cốt lõi: tổng hợp kết quả phản chứng `H1`–`H4`, thiết kế khung `2` tầng + đặt lại trọng số nhắc tại điểm xuất + đề xuất metric đo dễ đọc khả thi, kiểm `doc_lint` `0` lỗi
  - Ca góc hiểm & Assert: toàn bộ `[EV-xxx]` trích trong báo cáo phải tồn tại trong `evidence.jsonl`; `assert doc_lint == 0`

- [x] **T2.2** (e6m) Dựng `bao-cao.archify.md`, biên dịch `docs/tdq/reports/2026-11-21-1736-mac-dinh-trinh-bay-de-hieu.html`, xác thực manifest (`status=current`, `valid=true`), kiểm Tailscale `HTTP 200` và kiểm giao diện bằng `take_snapshot` (`0` lỗi console) — Test: `py -3 -X utf8 scripts/tdq_archify.py verify --document docs/tdq/reports/2026-11-21-1736-mac-dinh-trinh-bay-de-hieu.md --manifest docs/tdq/reports/2026-11-21-1736-mac-dinh-trinh-bay-de-hieu.manifest.json --project .`
  - Dùng: `tdq-browser-test` (mcp)
  - Để: nghiệm thu giao diện HTML trực quan của báo cáo điều tra qua Accessibility Tree Snapshot (`take_snapshot` + `list_console_messages` fail-closed), nạp skill TRƯỚC khi kiểm tra trình duyệt
  - Ra: `docs/tdq/reports/2026-11-21-1736-mac-dinh-trinh-bay-de-hieu.html` và bằng chứng snapshot `0` lỗi console
  - Kiểm: `py -3 -X utf8 scripts/tdq_archify.py verify --document docs/tdq/reports/2026-11-21-1736-mac-dinh-trinh-bay-de-hieu.md --manifest docs/tdq/reports/2026-11-21-1736-mac-dinh-trinh-bay-de-hieu.manifest.json --project .`
  - Không dùng cho: thu thập dữ liệu web bên ngoài (`tdq-browser-research`) hay sửa file JS của Archify
  - Req: `§2#4, Q5` · Ngoài phạm vi: `KHÔNG` chỉnh sửa mã nguồn của `scripts/tdq_archify.py` hay `tdq-workflow-agy` · Worktree: `no_worktree`
  - Chạm: `docs/tdq/artifacts/2026-11-21-1736-mac-dinh-trinh-bay-de-hieu/bao-cao.archify.md`, `docs/tdq/reports/2026-11-21-1736-mac-dinh-trinh-bay-de-hieu.html`
  - Sinh ra: `docs/tdq/artifacts/2026-11-21-1736-mac-dinh-trinh-bay-de-hieu/bao-cao.archify.md`, `docs/tdq/reports/2026-11-21-1736-mac-dinh-trinh-bay-de-hieu.html`
  - Cần: `T2.1`
  - Giao tiếp: Consumes: `docs/tdq/reports/2026-11-21-1736-mac-dinh-trinh-bay-de-hieu.md` | Produces: HTML trực quan đối chiếu Hiện trạng lực kéo jargon ↔ Kiến trúc mặc định 2 tầng mới
  - Neo & Công cụ: Gọi `tdq_archify.py render --type explainer --quality showcase --evidence-kind working-tree`, kiểm `tdq_archify.py verify`, kiểm URL Tailscale `HTTP 200` và mở qua Chrome DevTools MCP (`navigate_page`, `take_snapshot`, `list_console_messages`)
  - Trước → Sau: chỉ có báo cáo chữ dài → có thêm sơ đồ trực quan so sánh luồng cũ vs giải pháp mặc định mới xem ngay trên trình duyệt/Tailscale
  - Tiêu chí chấp nhận (EARS): KHI xác thực manifest và mở URL Tailscale thật, `tdq_archify.py verify` PHẢI báo `status=current`, `valid=true`, URL trả `HTTP 200` và console có `0` lỗi JS
  - Logic cốt lõi: biên dịch `3` panel sơ đồ (Nguyên nhân lực kéo kỹ thuật, Kiến trúc mặc định 2 tầng & Cổng kiểm, Lộ trình Trước–Sau cho chat/`.md`/HTML), chạy kiểm chứng HTML và trình duyệt thật
  - Ca góc hiểm & Assert: mọi chỉnh sửa ở `.md` báo cáo phải thực hiện TRƯỚC khi `render` lần cuối để `document_digest` khớp; `assert status == "current" and valid is True`

**Xong P2 khi**: báo cáo `.md` và `.html` hoàn chỉnh, khớp digest và xem trực tiếp qua Tailscale `HTTP 200`.

## P3 — Log & kiểm chứng bắt buộc (`QC-I1..I4`)

Log: BỎ — request chế độ điều tra (`work_kind=investigate`) không tạo hay sửa mã nguồn runtime.

- [x] **T3.1** (e6m) Thực thi kiểm chứng hai đường `QC-I1..I4` (`100%` `[EV-xxx]` khớp đĩa/URL, đối chiếu nhãn độ tin cậy, phản biện `QC-I3`) và xác nhận `git diff --name-only dev...HEAD` giữ `0` file sửa ngoài `docs/` — Test: `py -3 -X utf8 scripts/doc_lint.py docs/tdq/qc/2026-11-21-1736-mac-dinh-trinh-bay-de-hieu.md`
  - Req: `§4, §6, Q4` · Ngoài phạm vi: `KHÔNG` chạy hay sửa code để kích hoạt `QC-F1` vô ích trừ khi phát hiện diff ngoài `docs/` · Worktree: `no_worktree`
  - Chạm: `docs/tdq/qc/2026-11-21-1736-mac-dinh-trinh-bay-de-hieu.md`
  - Sinh ra: `docs/tdq/qc/2026-11-21-1736-mac-dinh-trinh-bay-de-hieu.md`
  - Cần: `T2.1`, `T2.2`
  - Giao tiếp: Consumes: `evidence.jsonl`, `research/2026-11-21-1736-*.md`, `reports/2026-11-21-1736-*.md`, `reports/2026-11-21-1736-*.html` | Produces: biên bản `docs/tdq/qc/2026-11-21-1736-mac-dinh-trinh-bay-de-hieu.md`
  - Neo & Công cụ: Đối chiếu tự động `100%` `[EV-xxx]` trong báo cáo với `evidence.jsonl` và file thật trên đĩa, rà phản biện `QC-I3`, kiểm `git diff --name-only dev...HEAD`, ghi `Dev Behavior QC Card`
  - Trước → Sau: chưa khóa độ tin cậy cho từng kết luận → mỗi khẳng định chính được kiểm chứng 4 lớp `QC-I1..I4` rõ ràng trước khi trình user
  - Tiêu chí chấp nhận (EARS): KHI hoàn tất `T3.1`, tỷ lệ `[EV-xxx]` mồ côi PHẢI bằng `0`, `0` file sửa ngoài `docs/`, mọi `Q1`–`Q5` đạt `PASS` và `doc_lint.py` thoát `0`
  - Logic cốt lõi: chạy kiểm tự động khớp ID/path:line + `git diff`, rà tay các cặp Claim-Excerpt (`QC-I2`) và ghi `QC-I3` đối trọng vào biên bản QC
  - Ca góc hiểm & Assert: phát hiện khẳng định `Unverified` hoặc `path:line` sai → hạ nhãn hoặc sửa lại báo cáo + dựng lại HTML ngay; `assert doc_lint == 0`

## Cụm song song

- **Wave 1 (chạy song song tối đa `3` mũi độc lập `no_worktree`):** `T1.1` (audit nội bộ repo), `T1.2` (soi transcript `0917` & `1536`), `T1.3` (research nguồn ngoài `(mcp)` do Leader giữ). Không mũi nào dùng chung tệp ghi ra.
- **Wave 2 (tuần tự sau Wave 1):** `T2.1` gộp `evidence.jsonl` và viết báo cáo `.md`, tiếp nối `T2.2` dựng và kiểm Archify HTML `(mcp)`.
- **Wave 3 (sau Wave 2):** `T3.1` chốt kiểm chứng `QC-I1..I4` và biên bản QC.

## Luật file nóng

Không có file nóng chồng lấn: cả `6` task đều sở hữu danh sách `Chạm:` hoàn toàn rời nhau dưới `docs/tdq/` (`no_worktree`). Các nhiệm vụ mang nhãn `(mcp)` (`T1.3`, `T2.2`) do Leader trực tiếp chạy trong phiên chính.

## Definition of Done

- [x] Q1 Kiểm chứng đủ `4` giả thuyết `H1`–`H4` trên cả `3` bề mặt (chat, `.md`, HTML) với dẫn chứng `path:line` và transcript trong `docs/tdq/artifacts/2026-11-21-1736-mac-dinh-trinh-bay-de-hieu/evidence.jsonl` — Test: `py -3 -X utf8 -c "import json; rows=[json.loads(l) for l in open('docs/tdq/artifacts/2026-11-21-1736-mac-dinh-trinh-bay-de-hieu/evidence.jsonl', encoding='utf-8') if l.strip()]; assert len(rows) >= 8"`
- [x] Q2 Hồ sơ research ngoài (`docs/tdq/research/2026-11-21-1736-mac-dinh-trinh-bay-de-hieu.md`) có `>= 3` nguồn uy tín kèm URL sống và rút ra quy tắc áp dụng — Test: `py -3 -X utf8 scripts/doc_lint.py docs/tdq/research/2026-11-21-1736-mac-dinh-trinh-bay-de-hieu.md`
- [x] Q3 Báo cáo cuối (`docs/tdq/reports/2026-11-21-1736-mac-dinh-trinh-bay-de-hieu.md`) có đủ `3` phần (chẩn đoán, giải pháp kiến trúc, mẫu Trước–Sau cho chat/`spec`/`report`) và sạch lint — Test: `py -3 -X utf8 scripts/doc_lint.py docs/tdq/reports/2026-11-21-1736-mac-dinh-trinh-bay-de-hieu.md`
- [x] Q4 Đạt đủ `QC-I1..I4` (`100%` `[EV-xxx]` hợp lệ, gắn nhãn độ tin cậy, phản biện `QC-I3`) và `0` thay đổi ngoài `docs/` — Test: `py -3 -X utf8 -c "import subprocess; out=subprocess.check_output(['git','diff','--name-only','dev...HEAD'], text=True).splitlines(); assert all(p.startswith('docs/') for p in out)"`
- [x] Q5 Báo cáo Archify HTML (`docs/tdq/reports/2026-11-21-1736-mac-dinh-trinh-bay-de-hieu.html`) hợp lệ và kiểm qua Tailscale — Test: `py -3 -X utf8 scripts/tdq_archify.py verify --document docs/tdq/reports/2026-11-21-1736-mac-dinh-trinh-bay-de-hieu.md --manifest docs/tdq/reports/2026-11-21-1736-mac-dinh-trinh-bay-de-hieu.manifest.json --project .`
