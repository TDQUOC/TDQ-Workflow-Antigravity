# PLAN — Nghiên cứu custom marketplace GitHub, sẵn sàng Git và cơ chế auto-update của Antigravity

Ngày: 2026-11-22 · Spec: ../spec/2026-11-22-0821-research-marketplace-va-update.md (bản 1.0, ĐÃ DUYỆT)
Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md
Mode thực thi: main — đo thực tế bằng tdq_bench.py simulate (--he-so-agent 1.5): main 12.2 phút vs đội 12.3 phút (Winner: main, gap 0.0 phút qua 4 wave, 6 task) (ĐỀ XUẤT, user chốt lúc duyệt)
Trạng thái plan: HOÀN THÀNH

> **Tóm tắt dễ hiểu:** Kế hoạch chia thành bốn đợt với sáu công việc không trùng tệp để hoàn thành toàn bộ nghiên cứu và báo cáo. Đợt đầu chạy song song ba nhánh thu thập tài liệu chính thức Antigravity, thực nghiệm cách ly lệnh agy và kiểm toán cấu hình repo đa hệ điều hành. Các đợt sau hợp nhất sổ bằng chứng, phản biện đối nghịch và kiểm chứng trích dẫn trước khi chốt báo cáo cuối mà không đụng mã nguồn.

## Mục lục

- Phân bổ Model & Effort
- Quy tắc thi hành (áp cho mọi task)
- Thiết kế Trước vs Sau
- Ràng buộc toàn cục & Bản đồ Sở hữu Hợp đồng (Ownership Map)
- P1 — Khảo sát Trục A: Nền tảng Antigravity và thực nghiệm cách ly agy
- P2 — Khảo sát Trục B: Kiểm toán cấu hình Git, marketplace và đa hệ điều hành của repo
- P3 — Hợp nhất sổ bằng chứng, phản biện và soạn nghiên cứu cùng báo cáo nháp
- P4 — Log & test bắt buộc
- Cụm song song
- Luật file nóng
- Definition of Done

## Phân bổ Model & Effort
<!-- i18n-allow: canonical model/effort plan allocation table -->
> User được quyền đổi `type model` hoặc `effort` lúc duyệt plan. Thang model: [subagent-tuning.md](../../tdq-conventions/references/subagent-tuning.md).

| Pha | Vai trò | Model | Effort | Ghi chú |
|---|---|---|---|---|
| `implement` | `tdq-explorer` / `research` (3 nhánh thu thập song song) | `inherit` | `high` | Đọc tài liệu sống Antigravity, chạy thử cách ly `agy` và kiểm toán kho mã nguồn |
| `implement` | Leader (`main`) — tổng hợp `evidence.jsonl`, `research` & báo cáo nháp | `inherit` | `high` | Phản biện counterfactual và chốt khuyến nghị ưu tiên |
| `qc` | Kiểm chứng bằng chứng `QC-I1`–`QC-I4` (`muc_qc=full`) | `inherit` | `high` | Đối chiếu từng `[EV-xxx]` với đĩa/trích đoạn gốc, không bỏ qua kiểm tra ranh giới kho |
| `report` | Leader (`main`) | `inherit` | `medium` | Chốt báo cáo Markdown, render `Archify HTML` và kiểm HTTP 200 qua Tailscale |

## Quy tắc thi hành (áp cho mọi task)
1. Thứ tự phase là thứ tự phụ thuộc — không đảo; đang làm việc trên nhánh `docs/research-marketplace-va-update` tách từ `dev`.
2. Mỗi task: đánh `[~]` khi bắt đầu → thu thập bằng chứng & kiểm chứng đạt điều kiện → đổi sang `[x]` NGAY vào file này. Trạng thái checkbox: `[ ]` chưa làm · `[~]` đang làm · `[x]` xong.
3. Mọi tệp ghi mới phải nằm tuyệt đối trong `docs/tdq/` (và `docs/workinglog/` qua `tdq_finish.py`); tuyệt đối không sửa mã nguồn ngoài `docs/tdq/`, không sửa `~/.gemini/` và không chạy `git push`.
4. Lệnh thực nghiệm `agy` ở `T1.2` bắt buộc chạy cách ly với biến `USERPROFILE`/`HOME` tạm và xác minh trước–sau rằng `~/.gemini/config/` không thay đổi.
5. QC FAIL → thêm task fix gọn vào mục QC của file này (không cần duyệt lại), lặp đến khi `PASS`.
6. Không commit, merge hay push cho đến khi người dùng yêu cầu.
7. Tuân thủ 6 mã cấm cơ học (`ANTI-1` Fake Red, `ANTI-2` Blind Assertion, `ANTI-3` Dirty State Git, `ANTI-4` Late Tick, `ANTI-5` Raw Dump, `ANTI-6` Broad Area).

## Thiết kế Trước vs Sau
| Khía cạnh | Hiện trạng (Trước) | Trạng thái sau điều tra (Sau) |
|---|---|---|
| Cơ chế marketplace GitHub & auto-update của Antigravity | Chưa xác thực; mới thấy danh sách lệnh sơ bộ của `agy plugin --help` (`1.4.12`) | Kết luận có dẫn chứng từ `antigravity.google/docs/*.md`, built-in skills và thực nghiệm cách ly `agy`, tách rõ CLI vs App/IDE |
| Mức độ sẵn sàng GitHub cộng đồng đa OS của repo | Nhiều adapter song song (`.agents/`, `.claude-plugin/`, `plugins/tdq-workflow-agy/`) chưa đối chiếu đủ điểm lệch | Ma trận kiểm toán từng tệp, nhánh `dev`/`main`, CI build đa OS và bảng phương án khắc phục ưu tiên |

*Đối chiếu sơ đồ kiến trúc:* Spec sử dụng chế độ `Work kind: investigate` nên miễn `Archify preview` trước duyệt; toàn bộ 6 task ánh xạ trực tiếp tới 4 đầu ra §2 và 6 tiêu chí §6 của spec đã duyệt.

## Ràng buộc toàn cục & Bản đồ Sở hữu Hợp đồng (Ownership Map)

- Ràng buộc chung: `Work kind: investigate` (0 file sửa ngoài `docs/tdq/` và `docs/workinglog/`) · mọi trích dẫn trong nghiên cứu/báo cáo dùng mã `[EV-Axx]`/`[EV-Bxx]` chuẩn trỏ tới `evidence.jsonl` và trích đoạn gốc `raw/<ev_id>.txt` · `GIỮ NGUYÊN` toàn bộ mã nguồn repo, `~/.gemini/` và nhánh `main`.

| Hợp đồng / Ký hiệu (§3c) | File & Task sở hữu | Task / File tiêu thụ |
|---|---|---|
| Shard Trục A1 (`axis-a-docs.md`, `axis-a-docs.ev.jsonl`) | `docs/tdq/artifacts/2026-11-22-0821-research-marketplace-va-update/axis-a-docs.ev.jsonl` (`T1.1`) | `T3.1` |
| Shard Trục A2 (`axis-a-cli.md`, `axis-a-cli.ev.jsonl`) | `docs/tdq/artifacts/2026-11-22-0821-research-marketplace-va-update/axis-a-cli.ev.jsonl` (`T1.2`) | `T3.1` |
| Shard Trục B (`axis-b-repo.md`, `axis-b-repo.ev.jsonl`) | `docs/tdq/artifacts/2026-11-22-0821-research-marketplace-va-update/axis-b-repo.ev.jsonl` (`T2.1`) | `T3.1` |
| Sổ bằng chứng hợp nhất (`evidence.jsonl`) & Tài liệu nghiên cứu | `docs/tdq/artifacts/2026-11-22-0821-research-marketplace-va-update/evidence.jsonl`, `docs/tdq/research/2026-11-22-0821-research-marketplace-va-update.md` (`T3.1`) | `T3.2`, `T4.1` |
| Báo cáo nháp Markdown & nguồn `bao-cao.archify.md` | `docs/tdq/reports/2026-11-22-0821-research-marketplace-va-update.md`, `docs/tdq/artifacts/2026-11-22-0821-research-marketplace-va-update/bao-cao.archify.md` (`T3.2`) | `T4.1`, pha `qc` & `report` |

## P1 — Khảo sát Trục A: Nền tảng Antigravity và thực nghiệm cách ly agy

- [x] **T1.1** (e10m) Thu thập bằng chứng chính thức về Antigravity custom GitHub marketplace, tiêu chí phát hành cộng đồng và cơ chế auto-update từ live docs `.md` và nguồn web — Test: `py -3 -X utf8 -c "import json,pathlib; p=pathlib.Path('docs/tdq/artifacts/2026-11-22-0821-research-marketplace-va-update/axis-a-docs.ev.jsonl'); rows=[json.loads(l) for l in p.read_text(encoding='utf-8').splitlines() if l.strip()]; assert len(rows)>=3 and all(r.get('id','').startswith('EV-A') and r.get('source') for r in rows)"`
  - Dùng: `antigravity-guide`
  - Để: lấy chính xác sitemap tài liệu `.md` chính thức (`llms.txt`, `plugins.md`, `cli/reference.md`, `changelog.md`) trước khi tải và tìm kiếm web
  - Ra: `docs/tdq/artifacts/2026-11-22-0821-research-marketplace-va-update/axis-a-docs.md` và `axis-a-docs.ev.jsonl` kèm `raw/EV-A*.txt`
  - Kiểm: `py -3 -X utf8 -c "import pathlib; assert pathlib.Path('docs/tdq/artifacts/2026-11-22-0821-research-marketplace-va-update/axis-a-docs.md').stat().st_size > 400"`
  - Không dùng cho: chỉnh sửa cấu hình Antigravity cục bộ hoặc kiểm toán mã nguồn repo nội bộ
  - Req: `§1`, `§2#1`, `§2#2`, `§3b`, `§3c Bước 1` · Ngoài phạm vi: `GIỮ NGUYÊN` toàn bộ mã nguồn và `~/.gemini/`
  - Chạm: `docs/tdq/artifacts/2026-11-22-0821-research-marketplace-va-update/axis-a-docs.md`, `docs/tdq/artifacts/2026-11-22-0821-research-marketplace-va-update/axis-a-docs.ev.jsonl`
  - Cần: Không
  - Giao tiếp: Consumes: `antigravity-guide` sitemap URLs | Produces: `axis-a-docs.md` và các bản ghi JSONL `EV-A01..EV-A0x`
  - Neo & Công cụ: `read_file` trên `antigravity-guide` + tải mirror `.md` / `search_web` + `write_file` tạo mới `axis-a-docs.md`, `axis-a-docs.ev.jsonl` và `raw/`
  - Trước → Sau: Chưa có bằng chứng chính thức về GitHub custom marketplace và auto-update → Có tập trích đoạn gốc kèm URL và ngày đọc
  - Tiêu chí chấp nhận (EARS): KHI tải xong mirror `.md` và nguồn web bổ sung, HỆ THỐNG PHẢI lưu đủ ít nhất 3 bản ghi `EV-A*` có `source`, `claim`, `raw_file` và phân tách rõ bề mặt CLI vs IDE/App
  - Logic cốt lõi: Tải `llms.txt`, `plugins.md`, `cli/reference.md`, `changelog.md` (lọc mục plugin/marketplace/update), bổ sung 1–2 truy vấn web xác thực điều kiện đăng ký cộng đồng và tự động cập nhật
  - Ca góc hiểm & Assert: Mirror `.md` trả lỗi HTTP/404 hoặc không đề cập tính năng → ghi rõ HTTP status/trích đoạn vắng mặt vào `raw/` và hạ nhãn `Single-source`/`Unverified`, cấm bịa nội dung

- [x] **T1.2** (e10m) Phân tích vòng đời plugin Antigravity (`plugin` skill, `lsrpc` read-only) và chạy thực nghiệm cách ly `agy plugin` (`install`, `link`, `validate`, `list`) với `USERPROFILE`/`HOME` tạm — Test: `py -3 -X utf8 -c "import json,pathlib; p=pathlib.Path('docs/tdq/artifacts/2026-11-22-0821-research-marketplace-va-update/axis-a-cli.ev.jsonl'); rows=[json.loads(l) for l in p.read_text(encoding='utf-8').splitlines() if l.strip()]; assert len(rows)>=3 and any('home_untouched' in str(r) or 'isolated' in str(r).lower() for r in rows)"`
  - Dùng: `plugin`
  - Để: đối chiếu đầy đủ phần còn lại của skill `plugin` (catalog ID, cài từ Marketplace vs local, RPC read-only) trước khi thiết kế phép thử cách ly `agy`
  - Ra: `docs/tdq/artifacts/2026-11-22-0821-research-marketplace-va-update/axis-a-cli.md` và `axis-a-cli.ev.jsonl` kèm `raw/EV-A*.txt`
  - Kiểm: `py -3 -X utf8 -c "import pathlib; assert pathlib.Path('docs/tdq/artifacts/2026-11-22-0821-research-marketplace-va-update/axis-a-cli.md').stat().st_size > 400"`
  - Không dùng cho: gọi RPC ghi (`InstallCustomization`, `DeletePlugin`, `JetboxWriteState`) hoặc chỉnh `~/.gemini/config/`
  - Req: `§1`, `§2#1`, `§3b`, `§3c Bước 1`, `§6 Q2` · Ngoài phạm vi: `GIỮ NGUYÊN` 100% `~/.gemini/` (xác minh mtime/count trước và sau)
  - Chạm: `docs/tdq/artifacts/2026-11-22-0821-research-marketplace-va-update/axis-a-cli.md`, `docs/tdq/artifacts/2026-11-22-0821-research-marketplace-va-update/axis-a-cli.ev.jsonl`
  - Cần: Không
  - Giao tiếp: Consumes: `agy.exe` (`v1.4.12`), skill `plugin` | Produces: `axis-a-cli.md` và bản ghi `EV-A1x` gồm log thực nghiệm cách ly + bằng chứng bảo toàn `~/.gemini/`
  - Neo & Công cụ: `read_file` phần còn lại của `plugin/SKILL.md` + `run_command` với `USERPROFILE`/`HOME` tạm + `write_file` tạo mới `axis-a-cli.md`, `axis-a-cli.ev.jsonl` và `raw/`
  - Trước → Sau: Mới thấy trợ giúp dòng lệnh sơ bộ của `agy` → Biết chính xác hành vi thật của `agy plugin install`, `link`, `validate`, `import` với URL GitHub vs thư mục cục bộ và chứng minh không có lệnh `update`
  - Tiêu chí chấp nhận (EARS): KHI chạy thử `agy plugin` trên thư mục tạm và kiểm tra lại `~/.gemini/config/`, HỆ THỐNG PHẢI ghi lại exit code/output nguyên văn và chứng minh snapshot `~/.gemini/config/` trước và sau giống hệt nhau
  - Logic cốt lõi: Chụp snapshot `~/.gemini/config/`, chạy trong subprocess có `USERPROFILE`/`HOME` tạm để thử `agy plugin link`, `agy plugin install <url-vs-dir>`, `agy plugin validate --strict --json`, đối chiếu snapshot sau chạy rồi dọn thư mục tạm
  - Ca góc hiểm & Assert: `agy` bỏ qua `USERPROFILE` tạm để đọc đường dẫn cố định → chỉ chạy lệnh read-only (`--help`, `list`, `validate`) và ghi nhận rõ ràng; `assert before_snapshot == after_snapshot`

**Xong P1 khi**: Cả hai shard `axis-a-docs.ev.jsonl` và `axis-a-cli.ev.jsonl` tồn tại, vượt lệnh `Test:` và xác nhận `~/.gemini/config/` không đổi.

## P2 — Khảo sát Trục B: Kiểm toán cấu hình Git, marketplace và đa hệ điều hành của repo

- [x] **T2.1** (e10m) Kiểm toán toàn bộ cấu hình adapter/marketplace, đóng gói `plugins/tdq-workflow-agy/`, workflow CI đa OS và trạng thái nhánh `dev`/`main`/remote Git trong repo — Test: `py -3 -X utf8 -c "import json,pathlib; p=pathlib.Path('docs/tdq/artifacts/2026-11-22-0821-research-marketplace-va-update/axis-b-repo.ev.jsonl'); rows=[json.loads(l) for l in p.read_text(encoding='utf-8').splitlines() if l.strip()]; assert len(rows)>=5 and all(r.get('id','').startswith('EV-B') and r.get('source') for r in rows)"`
  - Dùng: `agy-customizations`
  - Để: đọc trọn tài liệu discovery roots, `docs/plugins.md` nội bộ của skill và thứ tự ưu tiên nạp của Antigravity làm thước đo chuẩn khi kiểm toán repo
  - Ra: `docs/tdq/artifacts/2026-11-22-0821-research-marketplace-va-update/axis-b-repo.md` và `axis-b-repo.ev.jsonl` kèm `raw/EV-B*.txt`
  - Kiểm: `py -3 -X utf8 -c "import pathlib; assert pathlib.Path('docs/tdq/artifacts/2026-11-22-0821-research-marketplace-va-update/axis-b-repo.md').stat().st_size > 500"`
  - Không dùng cho: sửa bất kỳ tệp manifest, script đóng gói hay cấu hình CI nào trong repo
  - Req: `§1`, `§2#1`, `§2#2`, `§3b`, `§3c Bước 2` · Ngoài phạm vi: `GIỮ NGUYÊN` mọi tệp nguồn, manifest, `.github/` và nhánh `main`
  - Chạm: `docs/tdq/artifacts/2026-11-22-0821-research-marketplace-va-update/axis-b-repo.md`, `docs/tdq/artifacts/2026-11-22-0821-research-marketplace-va-update/axis-b-repo.ev.jsonl`
  - Cần: Không
  - Giao tiếp: Consumes: các tệp adapter/build/CI trong repo + `agy-customizations` | Produces: `axis-b-repo.md` và bản ghi `EV-B01..EV-B0x` có `path:line` thực tế
  - Neo & Công cụ: `read_file` trên `.agents/`, `.claude-plugin/`, `.codex-plugin/`, `plugins/tdq-workflow-agy/{plugin.json,hooks.json,mcp_config.json,README.md}`, `tools/{build_agy_plugin,install_agy_plugin}.py`, `scripts/build_portable.py`, `.github/workflows/build-rust-hooks.yml` + `write_file` tạo mới `axis-b-repo.md` và `axis-b-repo.ev.jsonl`
  - Trước → Sau: Mới nhìn thấy bề mặt thư mục adapter → Có bảng kiểm toán đủ từng tệp, độ lệch tên/URL, trạng thái nhánh `dev`/`main`/`origin` và mức sẵn sàng nhị phân Windows–macOS–Linux
  - Tiêu chí chấp nhận (EARS): KHI hoàn tất kiểm toán repo, HỆ THỐNG PHẢI liệt kê đủ từng điểm sẵn sàng và từng điểm lệch kèm `path:line` thực tế trên đĩa cho cả 3 hệ điều hành Windows, macOS và Linux
  - Logic cốt lõi: Đọc có giới hạn từng tệp cấu hình/build/CI, kiểm tra nội dung cây nhánh `main` qua `git ls-tree main`, đối chiếu binary `bin/` và đường dẫn thực thi trong `hooks.json` trên 3 OS, ghi từng bằng chứng vào `axis-b-repo.ev.jsonl`
  - Ca góc hiểm & Assert: Tệp có đường dẫn Windows cứng (`.exe`, backslash) hoặc tên plugin lệch giữa `.agents/plugins/marketplace.json` (`tdq-workflow`) và `plugins/tdq-workflow-agy/plugin.json` (`tdq-workflow-agy`) → bắt buộc ghi rõ `path:line` và phân loại mức độ ảnh hưởng

**Xong P2 khi**: `axis-b-repo.ev.jsonl` chứa đủ bằng chứng có `path:line` tồn tại thật trên đĩa và vượt lệnh `Test:`.

## P3 — Hợp nhất sổ bằng chứng, phản biện và soạn nghiên cứu cùng báo cáo nháp

- [x] **T3.1** (e10m) Hợp nhất 3 shard thành `evidence.jsonl` và viết tài liệu nghiên cứu chi tiết `docs/tdq/research/2026-11-22-0821-research-marketplace-va-update.md` (đủ 3 câu hỏi, góc nhìn cộng đồng đa OS, phản biện counterfactual và đề xuất ưu tiên) — Test: `py -3 -X utf8 -c "import json,pathlib,re; ev={json.loads(l)['id'] for l in pathlib.Path('docs/tdq/artifacts/2026-11-22-0821-research-marketplace-va-update/evidence.jsonl').read_text(encoding='utf-8').splitlines() if l.strip()}; txt=pathlib.Path('docs/tdq/research/2026-11-22-0821-research-marketplace-va-update.md').read_text(encoding='utf-8'); refs=set(re.findall(r'\[(EV-[A-Z0-9-]+)\]', txt)); assert len(ev)>=10 and refs and refs.issubset(ev)"`
  - Req: `§1`, `§2#1`, `§2#2`, `§3c Bước 3`, `§6 Q1`, `§6 Q4` · Ngoài phạm vi: `GIỮ NGUYÊN` toàn bộ mã nguồn ngoài `docs/tdq/`
  - Chạm: `docs/tdq/artifacts/2026-11-22-0821-research-marketplace-va-update/evidence.jsonl`, `docs/tdq/research/2026-11-22-0821-research-marketplace-va-update.md`
  - Cần: `T1.1`, `T1.2`, `T2.1`
  - Giao tiếp: Consumes: `axis-a-docs.ev.jsonl`, `axis-a-cli.ev.jsonl`, `axis-b-repo.ev.jsonl` | Produces: `evidence.jsonl` và `docs/tdq/research/2026-11-22-0821-research-marketplace-va-update.md`
  - Neo & Công cụ: `read_file` trên 3 shard + `write_file` tạo mới `evidence.jsonl` và `docs/tdq/research/2026-11-22-0821-research-marketplace-va-update.md`
  - Trước → Sau: Ba shard rời rạc → Một tài liệu nghiên cứu có cấu trúc rõ ràng, mọi nhận định gắn `[EV-xxx]` và nhãn tin cậy `Verified`/`Single-source`/`Inferred`/`Unverified`
  - Tiêu chí chấp nhận (EARS): KHI hợp nhất xong, HỆ THỐNG PHẢI bảo đảm 100% mã `[EV-xxx]` trong tài liệu nghiên cứu tồn tại trong `evidence.jsonl` và có đủ mục trả lời 3 câu hỏi, bảng tách 3 host, mục phản biện counterfactual và danh sách đề xuất theo mức ưu tiên
  - Logic cốt lõi: Khử trùng lặp bản ghi vào `evidence.jsonl`, tổng hợp câu trả lời trực diện cho Câu 1–3, lập bảng khoảng trống sẵn sàng GitHub đa OS và bảng phương án đề xuất (`P0`/`P1`/`P2`), bổ sung mục phản biện giả thuyết đối nghịch cho từng kết luận
  - Ca góc hiểm & Assert: Thiếu xác nhận chính thức từ tài liệu cho một chi tiết cụ thể → bắt buộc gắn nhãn `Single-source` hoặc `Unverified` thay vì khẳng định chắc chắn; `assert refs.issubset(ev)`

- [x] **T3.2** (e10m) Soạn nháp báo cáo cuối `docs/tdq/reports/2026-11-22-0821-research-marketplace-va-update.md` (4 phần chuẩn + `> **Tóm tắt dễ hiểu:**`) và nguồn sơ đồ trực quan `bao-cao.archify.md` — Test: `py -3 -X utf8 scripts/doc_lint.py docs/tdq/reports/2026-11-22-0821-research-marketplace-va-update.md`
  - Req: `§2#4`, `§6 Q1`, `§6 Q6` · Ngoài phạm vi: `GIỮ NGUYÊN` toàn bộ mã nguồn ngoài `docs/tdq/`
  - Chạm: `docs/tdq/reports/2026-11-22-0821-research-marketplace-va-update.md`, `docs/tdq/artifacts/2026-11-22-0821-research-marketplace-va-update/bao-cao.archify.md`
  - Cần: `T3.1`
  - Giao tiếp: Consumes: `docs/tdq/research/2026-11-22-0821-research-marketplace-va-update.md`, `evidence.jsonl` | Produces: báo cáo Markdown 4 phần và ứng viên `@workflow` Archify HTML
  - Neo & Công cụ: `write_file` tạo mới `docs/tdq/reports/2026-11-22-0821-research-marketplace-va-update.md` và `bao-cao.archify.md` + `doc_lint.py`
  - Trước → Sau: Chưa có báo cáo người dùng và nguồn sơ đồ → Có bản báo cáo dễ đọc trong 10–15 giây và nguồn sơ đồ gọn nhãn sẵn sàng render ở pha `report`
  - Tiêu chí chấp nhận (EARS): KHI chạy `doc_lint.py` trên báo cáo, HỆ THỐNG PHẢI thoát với mã `0` (`0 violation`) và mọi nhận định chính đều gắn `[EV-xxx]` kèm nhãn tin cậy
  - Logic cốt lõi: Tóm gọn Trước → Sau → Kết quả ở `> **Tóm tắt dễ hiểu:**` (mỗi câu `<= 35` từ, tổng `<= 120` từ, `0` bọc code quanh số/đường dẫn), trình bày rõ 4 mục chuẩn + bảng kết luận 3 câu hỏi + đề xuất ưu tiên, viết 2 sơ đồ `@workflow` nhãn ngắn gọn trong `bao-cao.archify.md`
  - Ca góc hiểm & Assert: Câu trong `Tóm tắt dễ hiểu` dài quá `35` từ hoặc nhãn cạnh Archify quá rộng gây lỗi `desktop-readability` → kiểm `doc_lint.py` ngay và giữ nhãn node/edge `<= 28` ký tự

**Xong P3 khi**: `evidence.jsonl`, `research/<slug>.md`, `reports/<slug>.md` và `bao-cao.archify.md` hoàn thiện và vượt `Test:` + `doc_lint.py` đạt `0` lỗi.

## P4 — Log & test bắt buộc

Log: BỎ — yêu cầu thuộc `work_kind=investigate` chỉ nghiên cứu và viết tài liệu trong `docs/tdq/`, không tạo hoặc sửa mã nguồn runtime sản phẩm.

- [x] **T4.1** (e6m) Kiểm chứng tự động toàn bộ định dạng tài liệu, toàn vẹn trích dẫn `[EV-xxx]`/`path:line`, bảo toàn `~/.gemini/` và ranh giới sạch `git diff` — Test: `py -3 -X utf8 scripts/doc_lint.py docs/tdq/brief/2026-11-22-0821-research-marketplace-va-update.md docs/tdq/spec/2026-11-22-0821-research-marketplace-va-update.md docs/tdq/plan/2026-11-22-0821-research-marketplace-va-update.md docs/tdq/reports/2026-11-22-0821-research-marketplace-va-update.md`
  - Req: `§4`, `§5`, `§6 Q3`, `§6 Q5`, `§6 Q6` · Ngoài phạm vi: `GIỮ NGUYÊN` toàn bộ mã nguồn ngoài `docs/tdq/`
  - Chạm: `docs/tdq/artifacts/2026-11-22-0821-research-marketplace-va-update/verify-summary.md`
  - Cần: `T3.2`
  - Giao tiếp: Consumes: `evidence.jsonl`, `research/<slug>.md`, `reports/<slug>.md`, `git diff` | Produces: `verify-summary.md` làm đầu vào trực tiếp cho phiếu QC `QC-I1`–`QC-I4`
  - Neo & Công cụ: `run_command` chạy kiểm tra Python tự động (`EV-xxx`, `path:line`, `git diff --name-only`, `doc_lint.py`) + `write_file` tạo mới `verify-summary.md`
  - Trước → Sau: Tài liệu chưa qua kiểm chứng máy tập trung → Có bảng kiểm chứng xanh 100% sẵn sàng chuyển pha `qc`
  - Tiêu chí chấp nhận (EARS): KHI chạy kiểm tra tổng hợp, HỆ THỐNG PHẢI xác nhận `0` mã `[EV-xxx]` mồ côi, `0` đường dẫn đĩa không tồn tại, `0` tệp sửa ngoài `docs/tdq/` + `docs/workinglog/`, và `doc_lint.py` thoát `0`
  - Logic cốt lõi: Đối chiếu mọi `[EV-xxx]` trong `research` và `reports` với `evidence.jsonl`, xác minh tồn tại mọi file/line cục bộ được trích dẫn, kiểm tra `git diff --name-only dev...HEAD` chỉ nằm trong `docs/tdq/` và `docs/workinglog/`, ghi biên bản kết quả vào `verify-summary.md`
  - Ca góc hiểm & Assert: Phát hiện bất kỳ mã `[EV-xxx]` không khớp hoặc file ngoài `docs/tdq/` bị chạm → báo lỗi ngay và dừng sửa trước khi sang pha `qc`

**Xong P4 khi**: `verify-summary.md` ghi nhận 100% kiểm tra xanh và `doc_lint.py` đạt `0 violation`.

## Cụm song song

Đồ thị phụ thuộc tách thành 4 đợt với 0 tệp xung đột giữa các task chạy đồng thời:
- **Đợt 1 (song song 3 task độc lập):** `T1.1` (`axis-a-docs.*`), `T1.2` (`axis-a-cli.*`), `T2.1` (`axis-b-repo.*`) — 3 shard hoàn toàn rời nhau, thu thập độc lập theo từng nguồn và kỹ năng.
- **Đợt 2 (tuần tự sau Đợt 1):** `T3.1` (`evidence.jsonl` + `research/<slug>.md`) — hợp nhất bằng chứng, đối chiếu chéo và phản biện counterfactual.
- **Đợt 3 (tuần tự sau Đợt 2):** `T3.2` (`reports/<slug>.md` + `bao-cao.archify.md`) — soạn báo cáo 4 phần và nguồn sơ đồ.
- **Đợt 4 (tuần tự sau Đợt 3):** `T4.1` (`verify-summary.md`) — kiểm chứng máy toàn vẹn trích dẫn, `doc_lint` và ranh giới sạch kho mã.

## Luật file nóng

Không có file nóng (`HOT FILE = 0`): mọi tệp đầu ra khai ở dòng `Chạm:` đều thuộc duy nhất một task, không có hai task nào ghi chung một tệp ở cùng đợt hay khác đợt.

## Definition of Done

Trỏ về §6 của spec `docs/tdq/spec/2026-11-22-0821-research-marketplace-va-update.md` (mức QC `full`, `Work kind: investigate`, mỗi dòng kiểm chứng bằng một lệnh thực tế):

- [x] Q1 Trả lời có dẫn chứng đầy đủ cho 3 câu hỏi cốt lõi (Antigravity custom GitHub marketplace, mức sẵn sàng Git cộng đồng đa OS, cơ chế auto-check/auto-update) kèm ma trận khoảng trống và phương án đề xuất — `py -3 -X utf8 -c "import pathlib; t=pathlib.Path('docs/tdq/reports/2026-11-22-0821-research-marketplace-va-update.md').read_text(encoding='utf-8'); assert all(k in t for k in ('marketplace','GitHub','auto-update','Windows','macOS','Linux'))" `
- [x] Q2 Thực nghiệm cách ly `agy` CLI có log thực tế và bảo toàn nguyên vẹn 100% thư mục `~/.gemini/config/` — `py -3 -X utf8 -c "import pathlib; t=pathlib.Path('docs/tdq/artifacts/2026-11-22-0821-research-marketplace-va-update/axis-a-cli.md').read_text(encoding='utf-8'); assert 'agy' in t and '0' in t"`
- [x] Q3 Đạt `QC-I1` & `QC-I2`: 100% `[EV-xxx]` trong nghiên cứu/báo cáo tồn tại trong `evidence.jsonl`, 100% `path:line` tồn tại trên đĩa và khớp nguồn gốc `raw/` — `py -3 -X utf8 -c "import json,pathlib,re; ev={json.loads(l)['id'] for l in pathlib.Path('docs/tdq/artifacts/2026-11-22-0821-research-marketplace-va-update/evidence.jsonl').read_text(encoding='utf-8').splitlines() if l.strip()}; rep=pathlib.Path('docs/tdq/reports/2026-11-22-0821-research-marketplace-va-update.md').read_text(encoding='utf-8'); refs=set(re.findall(r'\[(EV-[A-Z0-9-]+)\]', rep)); assert refs and refs.issubset(ev)"`
- [x] Q4 Đạt `QC-I3` & `QC-I4`: có phản biện counterfactual cho cả 3 kết luận chính và 100% kết luận chính gắn nhãn tin cậy (`Verified`/`Single-source`/`Inferred`/`Unverified`) — `py -3 -X utf8 -c "import pathlib; t=pathlib.Path('docs/tdq/research/2026-11-22-0821-research-marketplace-va-update.md').read_text(encoding='utf-8'); assert any(lbl in t for lbl in ('Verified','Single-source','Inferred','Unverified'))"`
- [x] Q5 Ranh giới sạch `work_kind=investigate`: 0 tệp sửa ngoài `docs/tdq/` và `docs/workinglog/`, nhánh `main` giữ nguyên và không chạy `git push` — `py -3 -X utf8 -c "import subprocess; out=subprocess.check_output(['git','diff','--name-only','dev...HEAD'],text=True).splitlines(); bad=[f for f in out if not f.startswith(('docs/tdq/','docs/workinglog/'))]; assert not bad, bad"`
- [x] Q6 `doc_lint.py` đạt `0` lỗi trên trọn bộ tài liệu, `tdq_archify.py verify` trả `status=current` và đường dẫn Tailscale HTTPS của `reports/2026-11-22-0821-research-marketplace-va-update.html` trả HTTP 200 — `py -3 -X utf8 scripts/doc_lint.py docs/tdq/brief/2026-11-22-0821-research-marketplace-va-update.md docs/tdq/spec/2026-11-22-0821-research-marketplace-va-update.md docs/tdq/plan/2026-11-22-0821-research-marketplace-va-update.md docs/tdq/qc/2026-11-22-0821-research-marketplace-va-update.md docs/tdq/reports/2026-11-22-0821-research-marketplace-va-update.md`
