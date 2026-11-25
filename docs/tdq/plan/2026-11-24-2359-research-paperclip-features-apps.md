# PLAN — Phân tích, nghiên cứu chức năng và ứng dụng của Paperclip

Ngày: 2026-11-25 · Spec: ../spec/2026-11-24-2359-research-paperclip-features-apps.md (bản 1.0, ĐÃ DUYỆT)
Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md
Mode thực thi: main — simulate thắng với chênh lệch 0.0 phút (`main` 12.2 phút vs `team` 12.3 phút ở hệ số agent 1.5, chuỗi Đợt 2–3 nối tiếp trên Leader); nếu chọn `subagent` vẫn chạy song song được `T1.1`–`T1.3` ở Đợt 1 (ĐỀ XUẤT, user chốt lúc duyệt)
Trạng thái plan: HOÀN THÀNH · Work kind: investigate

> **Tóm tắt dễ hiểu:** Kế hoạch chia cuộc nghiên cứu Paperclip thành ba đợt hoàn toàn chỉ đọc mã nguồn để bảo đảm khách quan. Đợt một chạy song song ba nhánh khảo sát bốn trụ cột, bảo mật với sáu công cụ agent ưu tiên, và hệ sinh thái triển khai thực tế. Đợt hai và ba đối chiếu với TDQ Workflow, chấm điểm ba hướng ứng dụng, kiểm định đầy đủ bằng chứng rồi xuất báo cáo hai tầng kèm sơ đồ trực quan.

## Mục lục

- Phân bổ Model & Effort
- Quy tắc thi hành (áp cho mọi task)
- Thiết kế Trước vs Sau
- Ràng buộc toàn cục & Bản đồ Sở hữu Hợp đồng (Ownership Map)
- P1 — Khảo sát sâu mã nguồn Paperclip theo 3 trục song song (H1–H3)
- P2 — Hợp nhất chứng cứ, đối chiếu TDQ, ma trận ứng dụng và bản thảo báo cáo 2 tầng (H4)
- P3 — Log & kiểm chứng bắt buộc (`QC-I1..I4`)
- Cụm song song
- Luật file nóng (một file, nhiều task chạm)
- Definition of Done

## Phân bổ Model & Effort

> User được quyền đổi `type model` hoặc `effort` lúc duyệt plan. Thang model: [subagent-tuning.md](../../tdq-conventions/references/subagent-tuning.md).

| Pha | Vai trò | Model | Effort | Ghi chú |
|---|---|---|---|---|
| `implement` (`T1.1`, `T1.2`, `T1.3`) | `tdq-explorer` (điều tra read-only + ghi shard artifact) | `inherit` | `high` | Không cần worktree (`Worktree: none`), chỉ ghi vào đúng file shard được giao |
| `implement` (`T2.1`, `T2.2`) | Leader (hợp nhất chứng cứ, đối chiếu web/TDQ & soạn báo cáo 2 tầng) | `inherit` | `xhigh` | Tổng hợp toàn cục, lập bảng chấm điểm 3 hướng và viết báo cáo chuẩn `R16` |
| `qc` (`T3.1`) | Leader (`muc_qc=full`, `QC-I1..I4`) | `inherit` | `high` | Chạy đối chiếu tự động `L1/L4/L2`, `doc_lint` và kiểm phạm vi `0` code sửa |
| `report` | Leader (Archify HTML + Tailscale verify) | `inherit` | `medium` | Xuất cặp báo cáo MD + Archify HTML một lần duy nhất |

## Quy tắc thi hành (áp cho mọi task)

1. Thứ tự phase là thứ tự phụ thuộc — không đảo (`P1` → `P2` → `P3`).
2. Mỗi task: đánh `[~]` (hoặc `[>]` khi giao subagent) trước khi bắt đầu; đổi sang `[x]` ngay khi tiêu chí kiểm đạt, cấm gộp tick cuối lượt.
3. Mọi task chỉ đọc kho `C:/Users/admin/Documents/paperclip` và mã nguồn `TDQ-Workflow-Antigravity`; chỉ ghi vào file tài liệu khai tại `Chạm:`.
4. Mọi phát hiện kỹ thuật phải lưu bằng chứng vào `docs/tdq/artifacts/2026-11-24-2359-research-paperclip-features-apps/` qua `py -3 -X utf8 scripts/tdq_team.py evidence add --shard <id> ...`.
5. QC FAIL → thêm task fix `QCn.x` vào mục QC của file này, sửa xong kiểm lại đến khi PASS.
6. Không commit hoặc push cho đến khi user yêu cầu rõ.
7. Tuân thủ đủ 6 mã cấm cơ học (`ANTI-1` đến `ANTI-6`), `doc_lint.py` exit `0` và `Work kind: investigate`.

## Thiết kế Trước vs Sau

| Khía cạnh | Hiện trạng (Trước) | Đích nghiên cứu đề xuất (Sau) |
|---|---|---|
| Hiểu biết về Paperclip | Mới có thư mục local và phần giới thiệu bề mặt `README.md`/`ROADMAP.md` | Có bản đồ đầy đủ 4 trụ cột đã đối chiếu trên mã nguồn thật, phân rõ phần hoàn chỉnh và thử nghiệm |
| Hỗ trợ nhóm agent & định hướng ứng dụng | Chưa rõ mức hỗ trợ `Antigravity` và 5 công cụ còn lại; chưa có tiêu chí chọn | Có ma trận tương thích 6 agent ưu tiên và bảng chấm điểm ưu tiên cho cả 3 hướng ứng dụng |

*Đối chiếu sơ đồ kiến trúc:* Spec `2026-11-24-2359-research-paperclip-features-apps.md` miễn bản xem trước Archify trước duyệt theo `investigate-mode.md:13`; WBS ánh xạ 1–1 tới 4 đầu ra §2 và 5 cổng kiểm §6 của spec đã duyệt.

## Ràng buộc toàn cục & Bản đồ Sở hữu Hợp đồng (Ownership Map)

- Ràng buộc chung: `0` sửa đổi trong `C:/Users/admin/Documents/paperclip` và `0` sửa đổi ngoài `docs/` trong `TDQ-Workflow-Antigravity` · Mọi trích dẫn gắn `path:line` thật · Báo cáo tiếng Việt (`doc_lang=vi`), tên riêng kỹ thuật giữ nguyên.

| Hợp đồng / Ký hiệu (§2 & §3c) | File & Task sở hữu | Task / File tiêu thụ |
|---|---|---|
| Bằng chứng `S1` (kiến trúc 4 trụ cột, Task Manager, Org Chart, code vs README) | `docs/tdq/artifacts/2026-11-24-2359-research-paperclip-features-apps/s1.md` (`T1.1`) | `T2.1`, `T2.2` |
| Bằng chứng `S2` (Control Plane runtime, 6 agent ưu tiên, bảo mật, ngân sách) | `docs/tdq/artifacts/2026-11-24-2359-research-paperclip-features-apps/s2.md` (`T1.2`) | `T2.1`, `T2.2` |
| Bằng chứng `S3` (Plugin SDK, Skill Studio, Eval, Sandbox, triển khai thực chiến) | `docs/tdq/artifacts/2026-11-24-2359-research-paperclip-features-apps/s3.md` (`T1.3`) | `T2.1`, `T2.2` |
| Đối chiếu `S4` + Phụ lục ma trận tính năng, 6 agent và bảng chấm điểm 3 hướng | `docs/tdq/artifacts/2026-11-24-2359-research-paperclip-features-apps/s4.md`, `feature-and-application-matrix.md` (`T2.1`) | `T2.2`, `T3.1` |
| Báo cáo 2 tầng + Archify HTML + biên bản QC | `docs/tdq/reports/2026-11-24-2359-research-paperclip-features-apps.md`, `.html`, `docs/tdq/qc/2026-11-24-2359-research-paperclip-features-apps.md` (`T2.2`, `T3.1`) | User & cổng `Q1`–`Q5` |

## P1 — Khảo sát sâu mã nguồn Paperclip theo 3 trục song song (H1–H3)

- [x] **T1.1** (e12m) Shard `S1`: Khảo sát tổng thể kiến trúc, 4 trụ cột, Task Manager, Org Chart và kiểm chứng Code thật so với `README.md`/`ROADMAP.md` (`H1`) — Test: `py -3 -c "import pathlib; t=pathlib.Path('docs/tdq/artifacts/2026-11-24-2359-research-paperclip-features-apps/s1.md').read_text(encoding='utf-8'); assert 'H1' in t and 'Implemented' in t and 'Verified' in t"`
  - Req: `§1, §2#1-2, §5` · Ngoài phạm vi: `GIỮ NGUYÊN` toàn bộ kho `C:/Users/admin/Documents/paperclip` (chỉ đọc)
  - Chạm: `docs/tdq/artifacts/2026-11-24-2359-research-paperclip-features-apps/s1.md` (tạo mới)
  - Cần: Không
  - Giao tiếp: Consumes: `C:/Users/admin/Documents/paperclip/{README.md,ROADMAP.md,DESIGN.md,doc/PRODUCT.md,packages/db,packages/shared,server/src,ui/src}` | Produces: `s1.md` + shard chứng cứ `s1.ev.jsonl`
  - Neo & Công cụ: `read_file` có dải dòng và lệnh chỉ đọc trên `C:/Users/admin/Documents/paperclip`; `write_file` tạo `s1.md`; `tdq_team.py evidence add --shard s1`
  - Trước → Sau: Mới biết tên 4 trụ cột trên README → Có bản đồ kiến trúc tầng (`server`/`ui`/`cli`/`db`), danh mục chức năng Task Manager/Org Chart/Approvals/Routines/Artifacts và phân loại `Implemented`/`Partial`/`Planned` kèm `path:line`
  - Tiêu chí chấp nhận (EARS): KHI hoàn tất `S1`, HỆ THỐNG PHẢI ghi tối thiểu `6` bằng chứng `path:line` vào `s1.ev.jsonl` làm rõ kiến trúc DB/API/UI và đối chiếu độ hoàn thiện thật của từng mục lớn trong `ROADMAP.md`
  - Logic cốt lõi: Đọc `packages/db` schema cốt lõi; rà nhóm service/route chính trong `server/src/`; kiểm các trang chính trong `ui/src/pages/`; đối chiếu từng mục `ROADMAP.md` để tìm điểm còn experimental hoặc giới hạn
  - Ca góc hiểm & Assert: Không tin nhãn tick trong `ROADMAP.md` nếu thiếu code thực thi tương ứng · `assert len(s1_ev_rows) >= 6 and 'H1' in s1_text`

- [x] **T1.2** (e12m) Shard `S2`: Khảo sát Control Plane runtime, 6 công cụ BYO Agent ưu tiên, Bảo mật (Secrets, MCP Gateway, RBAC, Audit) và Ngân sách hard-stop (`H2`) — Test: `py -3 -c "import pathlib; t=pathlib.Path('docs/tdq/artifacts/2026-11-24-2359-research-paperclip-features-apps/s2.md').read_text(encoding='utf-8'); assert 'H2' in t and 'Antigravity' in t and 'MCP' in t and ('Budget' in t or 'ngân sách' in t.lower())"`
  - Req: `§1, §2#1-2, §3c, §5` · Ngoài phạm vi: `GIỮ NGUYÊN` toàn bộ kho `C:/Users/admin/Documents/paperclip` (chỉ đọc)
  - Chạm: `docs/tdq/artifacts/2026-11-24-2359-research-paperclip-features-apps/s2.md` (tạo mới)
  - Cần: Không
  - Giao tiếp: Consumes: `C:/Users/admin/Documents/paperclip/{packages/adapters,packages/adapter-utils,packages/paperclip-runner,packages/mcp-server,server/src/auth,server/src/adapters,server/src/services,doc/MCP-ACCESS-GOVERNANCE.md,doc/AGENT-LIFECYCLE.md}` | Produces: `s2.md` + shard chứng cứ `s2.ev.jsonl`
  - Neo & Công cụ: `read_file` và tìm kiếm chỉ đọc trên `packages/adapters` + `server/src`; `write_file` tạo `s2.md`; `tdq_team.py evidence add --shard s2`
  - Trước → Sau: Chưa rõ cơ chế heartbeat/recovery, bảo mật và hỗ trợ 6 agent đang dùng → Có luồng kỹ thuật chi tiết và bảng tương thích thật cho `Antigravity`, `Claude Code`, `Codex`, `Gemini CLI`, `OpenCode`, `OpenClaw`
  - Tiêu chí chấp nhận (EARS): KHI hoàn tất `S2`, HỆ THỐNG PHẢI ghi tối thiểu `6` bằng chứng `path:line` vào `s2.ev.jsonl` kiểm chứng rõ từng công cụ trong nhóm 6 agent ưu tiên, cơ chế MCP `Allowed/Ask first/Off`, Secrets per-agent, ngân sách hard-stop và bounded run recovery
  - Logic cốt lõi: Liệt kê toàn bộ adapter trong `packages/adapters/`; kiểm tra trực tiếp xem có adapter `Antigravity` hay chỉ có custom/HTTP/CLI; đọc logic heartbeat/recovery, MCP governance, secrets và budget enforcement trong `server/src/`
  - Ca góc hiểm & Assert: Phân tách tuyệt đối giữa adapter native đã code sẵn và khả năng nối gián tiếp qua HTTP/CLI cho `Antigravity` · `assert len(s2_ev_rows) >= 6 and all(k in s2_text for k in ('Antigravity', 'Claude Code', 'Codex', 'Gemini CLI', 'OpenCode', 'OpenClaw'))`

- [x] **T1.3** (e12m) Shard `S3`: Khảo sát hệ sinh thái mở rộng (Plugin SDK, Skill Studio, Catalog, `companies.sh`, Eval kernel, Connected Apps, Cloud Sandbox) và đánh giá triển khai thực chiến Windows/local vs Docker/cloud (`H3`) — Test: `py -3 -c "import pathlib; t=pathlib.Path('docs/tdq/artifacts/2026-11-24-2359-research-paperclip-features-apps/s3.md').read_text(encoding='utf-8'); assert 'H3' in t and 'Plugin' in t and 'Windows' in t"`
  - Req: `§1, §2#1-2, §5` · Ngoài phạm vi: `GIỮ NGUYÊN` toàn bộ kho `C:/Users/admin/Documents/paperclip`; KHÔNG chạy cài đặt hay khởi chạy server
  - Chạm: `docs/tdq/artifacts/2026-11-24-2359-research-paperclip-features-apps/s3.md` (tạo mới)
  - Cần: Không
  - Giao tiếp: Consumes: `C:/Users/admin/Documents/paperclip/{packages/plugins,packages/paperclip-eval-kernel,packages/skills-catalog,packages/teams-catalog,skills,cli/src,docker,doc/plugins/PLUGIN_SPEC.md,doc/DEPLOYMENT-MODES.md,doc/DOCKER.md,doc/INSTALLING.md}` | Produces: `s3.md` + shard chứng cứ `s3.ev.jsonl`
  - Neo & Công cụ: `read_file` và tìm kiếm chỉ đọc trên `packages/` + `cli/` + `doc/` + `docker/`; `write_file` tạo `s3.md`; `tdq_team.py evidence add --shard s3`
  - Trước → Sau: Mới biết danh sách tên tính năng mở rộng → Nắm rõ kiến trúc Plugin SDK, Skill Studio/Eval, sandbox provider (E2B/Cloudflare/Daytona/Modal/Novita/K8s) và rào cản cài đặt/vận hành thực tế trên Windows so với Linux/Docker
  - Tiêu chí chấp nhận (EARS): KHI hoàn tất `S3`, HỆ THỐNG PHẢI ghi tối thiểu `6` bằng chứng `path:line` vào `s3.ev.jsonl` làm rõ khả năng mở rộng thực tế và yêu cầu hạ tầng/chi phí/rủi ro triển khai cục bộ lẫn cloud
  - Logic cốt lõi: Đọc `doc/plugins/PLUGIN_SPEC.md` và `packages/plugins`; kiểm `packages/paperclip-eval-kernel` + `skills-catalog` + `teams-catalog` + 9 built-in `skills/`; rà `cli/src/checks/`, `embedded-postgres-supervisor.ts`, `docker/` và `doc/DEPLOYMENT-MODES.md`
  - Ca góc hiểm & Assert: Gắn nhãn trung thực `Single-source`/`Inferred` cho các rủi ro runtime trên Windows vì không khởi chạy server sống · `assert len(s3_ev_rows) >= 6 and 'H3' in s3_text`

**Xong P1 khi**: Đủ 3 shard `s1.md`, `s2.md`, `s3.md` và `s1..s3.ev.jsonl`, tổng cộng `>= 18` bằng chứng `path:line` thật.

## P2 — Hợp nhất chứng cứ, đối chiếu TDQ, ma trận ứng dụng và bản thảo báo cáo 2 tầng (H4)

- [x] **T2.1** (e12m) Hợp nhất `evidence.jsonl`, đối chiếu nhanh tài liệu/release web chính thức (nếu cần), soạn shard `S4` (đối chiếu TDQ Workflow + `H4`) và xuất phụ lục `feature-and-application-matrix.md` — Test: `py -3 -X utf8 scripts/doc_lint.py docs/tdq/artifacts/2026-11-24-2359-research-paperclip-features-apps/feature-and-application-matrix.md`
  - Req: `§1, §2#1-3, §3, §3c` · Ngoài phạm vi: `GIỮ NGUYÊN` toàn bộ mã nguồn sản phẩm
  - Chạm: `docs/tdq/artifacts/2026-11-24-2359-research-paperclip-features-apps/s4.md` (tạo mới), `docs/tdq/artifacts/2026-11-24-2359-research-paperclip-features-apps/feature-and-application-matrix.md` (tạo mới)
  - Cần: `T1.1`, `T1.2`, `T1.3`
  - Giao tiếp: Consumes: `s1.md..s3.md`, `s1..s3.ev.jsonl`, `docs/kien-truc.md`, `README.md`, `README-Antigravity.md` | Produces: `evidence.jsonl`, `evidence-log.md`, `s4.md`, `feature-and-application-matrix.md`
  - Neo & Công cụ: `tdq_team.py evidence merge`; kiểm tra web chính thức gọn qua `tavily-primary` (hoặc `search_web` nếu MCP không sẵn); `write_file` tạo `s4.md` và `feature-and-application-matrix.md`
  - Trước → Sau: Bằng chứng còn rời rạc ở 3 shard → Hợp nhất thành sổ bằng chứng duy nhất và bộ ma trận đối chiếu hoàn chỉnh (4 trụ cột code vs README, 6 agent ưu tiên, Paperclip vs TDQ, chấm điểm Giá trị/Độ khó/Rủi ro với 3 nhóm hành động cho 3 hướng)
  - Tiêu chí chấp nhận (EARS): KHI hoàn tất `T2.1`, HỆ THỐNG PHẢI hợp nhất sạch `evidence.jsonl`, có đủ kết luận `H4` trong `s4.md` và bảng chấm điểm ưu tiên đủ 3 nhóm (Nên áp dụng ngay / Cân nhắc sau / Không nên học theo kèm lý do) trong `feature-and-application-matrix.md` qua `doc_lint.py` exit `0`
  - Logic cốt lõi: Chạy `evidence merge`; đối chiếu các trụ cột TDQ Workflow hiện có (`hooks`, `tdq_team`, `tdq_setup`, `archify`, `secrets.env`) với Paperclip; chấm điểm công bằng cả điểm nên học lẫn điểm không nên sao chép (tránh phình hệ thống)
  - Ca góc hiểm & Assert: Tách rõ mốc dữ liệu local (`2026-11-17`) và ghi chú nếu web có bản phát hành mới hơn · `assert rc == 0 and 'Không nên học theo' in matrix_text`

- [x] **T2.2** (e10m) Soạn bản thảo báo cáo tổng hợp 2 tầng (`docs/tdq/reports/2026-11-24-2359-research-paperclip-features-apps.md`) và tệp ứng viên Archify (`bao-cao.archify.md`) — Test: `py -3 -X utf8 scripts/doc_lint.py docs/tdq/reports/2026-11-24-2359-research-paperclip-features-apps.md`
  - Req: `§2#4, §4, §6` · Ngoài phạm vi: `GIỮ NGUYÊN` toàn bộ mã nguồn sản phẩm
  - Chạm: `docs/tdq/reports/2026-11-24-2359-research-paperclip-features-apps.md` (tạo mới), `docs/tdq/artifacts/2026-11-24-2359-research-paperclip-features-apps/bao-cao.archify.md` (tạo mới)
  - Cần: `T2.1`
  - Giao tiếp: Consumes: `s1.md..s4.md`, `evidence.jsonl`, `feature-and-application-matrix.md`, `tdq_timing.py show` | Produces: báo cáo MD 2 tầng + candidate Archify MD
  - Neo & Công cụ: `write_file` tạo report MD và `bao-cao.archify.md`; `doc_lint.py` kiểm định
  - Trước → Sau: Chưa có tài liệu báo cáo tổng hợp cho người dùng → Có báo cáo 2 tầng dễ hiểu (Tầng 1 tóm tắt đời thường + bức tranh 4 trụ cột + tóm lược 3 hướng ứng dụng; Tầng 2 đầy đủ dẫn chứng `[EV-xxx]`, kết luận `H1`–`H4`, nhãn tin cậy và 4 mục Trước/Sau/Đã kiểm/Kết quả)
  - Tiêu chí chấp nhận (EARS): KHI chạy `doc_lint.py` trên báo cáo, HỆ THỐNG PHẢI trả `0` vi phạm (bao gồm `R16` và `R12`), giữ độ dài dưới `500` dòng (đẩy bảng lớn sang phụ lục `feature-and-application-matrix.md`) và gắn nhãn tin cậy cho mọi phát hiện lớn
  - Logic cốt lõi: Viết Tầng 1 cực kỳ dễ hiểu không nhồi thuật ngữ; tóm lược đủ 4 trụ cột, 6 agent ưu tiên, bảo mật/ngân sách, ưu/nhược điểm và bảng khuyến nghị 3 hướng ứng dụng; soạn `bao-cao.archify.md` với mỗi sơ đồ `<= 5` node/hàng đạt `desktop-readability`
  - Ca góc hiểm & Assert: Bọc nguyên đầu ra `tdq_timing.py show` trong khối fenced code để đạt luật `R12`; đảm bảo báo cáo `< 500` dòng (`R6`) · `assert rc == 0 and line_count <= 500`

**Xong P2 khi**: Báo cáo MD và phụ lục ma trận đều qua `doc_lint.py` exit `0`, `evidence.jsonl` đầy đủ và `bao-cao.archify.md` sẵn sàng render.

## P3 — Log & kiểm chứng bắt buộc (`QC-I1..I4`)

Log: BỎ — Request này thuộc `work_kind=investigate`, không tạo hoặc sửa mã nguồn chạy được.

- [x] **T3.1** (e6m) Chạy kiểm chứng toàn diện `QC-I1..I4` (`Q1`–`Q5`), xuất biên bản QC, dựng Archify HTML báo cáo và xác nhận HTTP `200` trên Tailscale Serve — Test: `py -3 -X utf8 scripts/tdq_archify.py verify --document docs/tdq/reports/2026-11-24-2359-research-paperclip-features-apps.md --manifest docs/tdq/reports/2026-11-24-2359-research-paperclip-features-apps.manifest.json`
  - Req: `§2#4, §6 Q1-Q5` · Ngoài phạm vi: `GIỮ NGUYÊN` toàn bộ mã nguồn sản phẩm
  - Chạm: `docs/tdq/reports/2026-11-24-2359-research-paperclip-features-apps.html` (tạo mới), `docs/tdq/qc/2026-11-24-2359-research-paperclip-features-apps.md` (tạo mới)
  - Cần: `T2.2`
  - Giao tiếp: Consumes: `bao-cao.archify.md`, report MD, `feature-and-application-matrix.md`, `evidence.jsonl` | Produces: report HTML + manifest + biên bản `docs/tdq/qc/2026-11-24-2359-research-paperclip-features-apps.md`
  - Neo & Công cụ: Script Python kiểm `QC-I1` (ID `[EV]` + biên dòng `path:line` trên cả 2 repo + `git diff`); rà L2 nguyên văn; `tdq_archify.py render --type explainer` + `verify`; kiểm HTTP `200` trên Tailscale Serve
  - Trước → Sau: Chưa có kiểm định máy toàn bộ trích dẫn và bản HTML trực quan → Xác nhận `100%` `[EV]` và `path:line` tồn tại thật, `0` file mã nguồn bị sửa, Archify `current` và HTTP `200`
  - Tiêu chí chấp nhận (EARS): KHI hoàn tất `T3.1`, HỆ THỐNG PHẢI ghi biên bản QC với `5/5` cổng `Q1`–`Q5` đạt `PASS`, `tdq_archify.py verify` trả `"status": "current"` và URL Tailscale Serve trả mã `200`
  - Logic cốt lõi: Chạy script đối chiếu `QC-I1` trên báo cáo và phụ lục; rà `L2` trực tiếp cho các nhận định cốt lõi; kiểm `git status` sạch trên `paperclip` và `git diff` mã nguồn rỗng trên TDQ; render + verify Archify HTML và probe HTTP `200`
  - Ca góc hiểm & Assert: Nếu `bao-cao.archify.md` gặp cảnh báo `desktop-readability`, rút gọn sơ đồ xuống `<= 4` node/hàng rồi render lại trước khi verify · `assert verify_json['status'] == 'current' and http_status == 200`

**Xong P3 khi**: `5/5` hạng mục `Q1`–`Q5` đạt `PASS` trong biên bản QC và Archify HTML đạt `current` + HTTP `200`.

## Cụm song song

- **Đợt 1 (chạy song song 3 luồng đọc-chỉ, `Chạm:` hoàn toàn tách rời):**
  - `T1.1` (`tdq-explorer`, `Worktree: none`) → `s1.md`
  - `T1.2` (`tdq-explorer`, `Worktree: none`) → `s2.md`
  - `T1.3` (`tdq-explorer`, `Worktree: none`) → `s3.md`
- **Đợt 2 (tuần tự tổng hợp và kiểm định trên Leader sau khi Đợt 1 hội tụ):** `T2.1` → `T2.2` → `T3.1`.

## Luật file nóng (một file, nhiều task chạm)

Không có file nóng trong toàn bộ kế hoạch: cả 6 task `T1.1`–`T3.1` đều có đường dẫn `Chạm:` tách rời 100%, không xảy ra xung đột ghi song song. Sổ bằng chứng `evidence.jsonl` chỉ được ghi qua `tdq_team.py evidence add --shard <id>` (khóa file an toàn) và hợp nhất một lần ở `T2.1`.

## Definition of Done

Trỏ về §6 của spec `2026-11-24-2359-research-paperclip-features-apps.md` (`muc_qc=full`):

- [x] Q1 `QC-I1` Grounding tự động (`100%` `[EV]` ID trong `evidence.jsonl`, `100%` `path:line` tồn tại trên đĩa, `0` placeholder) — chạy script Python kiểm tra `evidence.jsonl` và biên dòng trên `docs/tdq/reports/2026-11-24-2359-research-paperclip-features-apps.md` và `feature-and-application-matrix.md`
- [x] Q2 `QC-I2` Đối chiếu nguyên văn (`L2` xác minh trực tiếp mã nguồn `C:/Users/admin/Documents/paperclip` và `TDQ-Workflow-Antigravity`) — ghi nhận đối chiếu trong `docs/tdq/qc/2026-11-24-2359-research-paperclip-features-apps.md`
- [x] Q3 `QC-I3` Kiểm chứng đủ `4` giả thuyết `H1`–`H4` kèm phản ví dụ / giới hạn thực tế — kiểm tra đủ 4 kết luận rõ ràng trong báo cáo và 4 shard `s1`–`s4`
- [x] Q4 `QC-I4` Nhãn độ tin cậy (`Verified`/`Single-source`/`Inferred`) và tài liệu sạch lỗi — `py -3 -X utf8 scripts/doc_lint.py docs/tdq/reports/2026-11-24-2359-research-paperclip-features-apps.md docs/tdq/artifacts/2026-11-24-2359-research-paperclip-features-apps/feature-and-application-matrix.md`
- [x] Q5 Ranh giới phạm vi `0` file mã nguồn sửa & Archify HTML xác minh trực quan — `git -C C:/Users/admin/Documents/paperclip status --porcelain` rỗng, `git diff --name-only dev -- scripts/ hooks/ plugins/ tools/ tests/` rỗng, `py -3 -X utf8 scripts/tdq_archify.py verify --document docs/tdq/reports/2026-11-24-2359-research-paperclip-features-apps.md --manifest docs/tdq/reports/2026-11-24-2359-research-paperclip-features-apps.manifest.json` trả `current`, và kiểm HTTP `200` trên Tailscale Serve
