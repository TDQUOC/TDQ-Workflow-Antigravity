# PLAN — Đánh giá Quy trình QC/Test Hiện tại & Đề xuất Mô hình QC Nhanh, Dễ hiểu, Trọng tâm E2E

Ngày: 2026-11-21 · Spec: ../spec/2026-11-21-1438-cai-thien-qc-test-e2e.md (bản 1.0, ĐÃ DUYỆT) · Lane: full · Loại: docs (Work kind: investigate, Zero-Code-Touch)
Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md
Mode thực thi: subagent — chạy song song Wave 1 (T1.1, T1.2, T1.3, Worktree: none) theo lựa chọn của người dùng
Trạng thái plan: HOÀN THÀNH

> **Tóm tắt dễ hiểu:** Đợt triển khai sẽ thu thập đồng thời `3` luồng bằng chứng độc lập trong Wave 1 (kiểm toán `3` lớp TDQ nội bộ, mổ xẻ `33` tệp của `C:\Users\admin\Documents\terterarmy-cli`, và research `4`–`6` framework/plugin QA/E2E lớn qua `tavily-primary`), sau đó hợp nhất vào sổ cái bằng chứng `[EV-xxx]` ở Wave 2 để viết báo cáo đề xuất `4` phần cho dev, rồi kiểm chứng chéo `QC-I1`/`QC-I2`/`QC-I4` và `Zero-Code-Touch` ở Wave 3 trước khi render Archify HTML.

## Mục lục

- Phân bổ Model & Effort
- Quy tắc thi hành (áp cho mọi task)
- Thiết kế Trước vs Sau
- Ràng buộc toàn cục & Bản đồ Sở hữu Hợp đồng (Ownership Map)
- P1 — Wave 1 Thu thập Đa chiều song song
- P2 — Wave 2 Hợp nhất Bằng chứng & Soạn Báo cáo Đề xuất 4 phần
- P3 — Wave 3 Kiểm chứng Bằng chứng & Zero-Code-Touch
- Cụm song song
- Luật file nóng
- Definition of Done

## Phân bổ Model & Effort
<!-- i18n-allow: canonical model/effort plan allocation table -->
> Người dùng được quyền đổi `model` hoặc `effort` khi duyệt plan. Thang mặc định tham chiếu `skills/tdq-conventions/references/subagent-tuning.md`.

| Pha | Vai trò | Model | Effort | Ghi chú |
|---|---|---|---|---|
| `implement` | Wave 1 `T1.1` Kiểm toán `3` lớp TDQ (`tdq-explorer`) | `inherit` | `high` | `Worktree: none`, đọc thẳng kho mã nguồn và ghi ra shard riêng, digest `<= 1.500` ký tự |
| `implement` | Wave 1 `T1.2` Mổ xẻ `terterarmy-cli` (`tdq-explorer`) | `inherit` | `high` | `Worktree: none`, đọc toàn bộ `33` tệp tại `C:\Users\admin\Documents\terterarmy-cli`, digest `<= 1.500` ký tự |
| `implement` | Wave 1 `T1.3` Research mạng `tavily-primary` (`self`) | `inherit` | `high` | Dùng MCP `tavily-primary` (`tavily_search` + `tavily_extract`), lưu raw vào `raw/`, digest `<= 1.500` ký tự |
| `implement` | Wave 2 Leader (`T2.1` Evidence Ledger · `T2.2` Báo cáo `4` phần) | `inherit` | `xhigh` | Hợp nhất `[EV-xxx]`, đối chứng `H1`–`H4`, thiết kế kiến trúc QC/E2E mới & lộ trình KPI |
| `implement` | Wave 3 `T3.1` Kiểm chứng chéo (`QC-I1`/`QC-I2`/`QC-I4` & Zero-Code-Touch) | `inherit` | `high` | Kiểm khớp `100%` `[EV-xxx]`, rà chống bịa đặt `F6`, chạy `doc_lint.py` và xuất biên bản QC |
| `report` | Leader (Archify HTML + Tailscale `HTTP 200`) | `inherit` | `high` | Render `docs/tdq/reports/2026-11-21-1438-cai-thien-qc-test-e2e.html` và kiểm truy cập Tailscale |

## Quy tắc thi hành (áp cho mọi task)

1. **Zero-Code-Touch:** Tuyệt đối không sửa tệp nào ngoài `docs/tdq/` và `docs/workinglog/` (`scripts/`, `hooks/`, `skills/`, `agents/`, `tools/`, `plugins/`, `tests/` giữ nguyên `0` diff).
2. **Thứ tự wave:** Wave 1 phải hoàn tất đủ `T1.1`, `T1.2`, `T1.3` và ghi checkpoint vào working log trước khi chạy Wave 2 (`T2.1`, `T2.2`) và Wave 3 (`T3.1`).
3. **Tick tức thì:** Đánh `[~]` (hoặc `[>]` khi giao subagent) lúc bắt đầu task, chuyển `[x]` ngay sau khi lệnh `Test:` của task đạt xanh.
4. **Chống tràn ngữ cảnh:** Mọi dữ liệu web thô (`tavily_search`/`tavily_extract`) ghi ra `docs/tdq/research/` và `docs/tdq/artifacts/.../raw/`, chỉ đưa digest `<= 1.500` ký tự vào luồng tổng hợp.
5. **Độ trung thực bằng chứng:** Không gán `path:line`, số liệu, hay tên tính năng ngoài nếu chưa đọc trực tiếp trên đĩa/nguồn trích; mọi nhận định chính trong báo cáo phải mang nhãn độ tin cậy `QC-I4`.

## Thiết kế Trước vs Sau

| Khía cạnh | Hiện trạng (Trước) | Sau hoàn tất điều tra |
|---|---|---|
| Cơ sở đánh giá QC | Cảm nhận định tính ("hơi hàn lâm", "thiếu E2E") chưa có số đo | Bảng đối chứng định lượng meta vs behavior trên `8` biên bản QC + `timing.jsonl` + sự cố `0.103.0` |
| Tham chiếu thực chiến ngoài TDQ | Chưa khai thác `terterarmy-cli` và các chuẩn AI QA mới | Tổng hợp đối xứng từ `33` tệp `terterarmy-cli` và `4`–`6` nguồn chuẩn ngành (`Playwright Agents/MCP`, `Testing Trophy`, `Risk-Based E2E`) |
| Khả năng áp dụng ngay | Chưa có mẫu QC mới cho dev dễ đọc | Đề xuất hoàn chỉnh *Dev Behavior QC Card*, *3 tầng tốc độ Changed-Flow E2E* và lộ trình KPI sẵn sàng mở đợt build nếu user duyệt |

## Ràng buộc toàn cục & Bản đồ Sở hữu Hợp đồng (Ownership Map)

- Ngôn ngữ hồ sơ: tiếng Việt (`doc_lang=vi`), giữ nguyên tên tệp, lệnh, ký hiệu kỹ thuật.

| Khối đầu ra (Spec §2) | Tệp sở hữu & Task | Task tiêu thụ |
|---|---|---|
| `D1` — Kiểm toán nội bộ TDQ | `docs/tdq/artifacts/2026-11-21-1438-cai-thien-qc-test-e2e/audit-tdq-qc-test.md` (`T1.1`) | `T2.1`, `T2.2`, `T3.1` |
| `D2` — Phân tích `terterarmy-cli` | `docs/tdq/artifacts/2026-11-21-1438-cai-thien-qc-test-e2e/phan-tich-terterarmy-cli.md` (`T1.2`) | `T2.1`, `T2.2`, `T3.1` |
| `D3` — Research mạng `tavily-primary` | `docs/tdq/research/2026-11-21-1438-cai-thien-qc-test-e2e.md` + `raw/` (`T1.3`) | `T2.1`, `T2.2`, `T3.1` |
| `D4` — Sổ bằng chứng & Báo cáo `4` phần | `evidence-log.md` + `evidence.jsonl` (`T2.1`) · `docs/tdq/reports/2026-11-21-1438-cai-thien-qc-test-e2e.md` (`T2.2`) | `T3.1`, pha `qc`, pha `report` |
| `D5` — Biên bản QC đối chứng | `docs/tdq/qc/2026-11-21-1438-cai-thien-qc-test-e2e.md` (`T3.1`) | Pha `qc` & nghiệm thu cuối |

## P1 — Wave 1 Thu thập Đa chiều song song

- [x] **T1.1** (e12m) Kiểm toán sâu `3` lớp QC & kiểm thử nội bộ TDQ (`skills/tdq-build/references/qc.md`, `qc-vong-fix.md`, `report-template.md`, `skills/tdq-browser-test/SKILL.md`, `agents/tdq-qc-tester.md`, `scripts/tdq_test.py`, `8` biên bản `docs/tdq/qc/*.md` và `docs/tdq/timing.jsonl`): đo tỷ lệ mục kiểm meta-compliance vs hành vi E2E người dùng, thời lượng pha `implement`/`qc`/`tron-bo`, đối chiếu ca lọt lỗi runtime `v0.103.0` (`4.603` unit pass nhưng vỡ `8/8` subagent) và chỉ rõ quy chuẩn nào của TDQ có giá trị giữ lại — Test: `py -3 -X utf8 -c "from pathlib import Path; t = Path('docs/tdq/artifacts/2026-11-21-1438-cai-thien-qc-test-e2e/audit-tdq-qc-test.md').read_text(encoding='utf-8'); assert all(k in t for k in ('qc.md:', 'tdq_test.py:', 'timing.jsonl', 'H1', 'H2')) and len(t) > 1500"`
  - Req: `§1, §2#1, Q1` · Ngoài phạm vi: chỉ đọc, không chỉnh sửa bất kỳ tệp kỹ năng hay mã nguồn nào
  - Chạm: `docs/tdq/artifacts/2026-11-21-1438-cai-thien-qc-test-e2e/audit-tdq-qc-test.md` (tạo mới)
  - Cần: `Không`
  - Worktree: `none` (`scoped-write` trong `docs/tdq/artifacts/2026-11-21-1438-cai-thien-qc-test-e2e/`)

- [x] **T1.2** (e10m) Mổ xẻ chi tiết dự án `C:\Users\admin\Documents\terterarmy-cli` (`README.md`, `skills/testerarmy-cli/SKILL.md`, `skills/testerarmy-cli/references/reporting-template.md`, `examples/TESTER.md`, `examples/prompts/ad-hoc-regression.md`, `examples/tests/01-landing-page.md`, `02-auth-smoke.md`, `03-project-create.md`, `docs/BUG_BOARD.md`, `.github/ISSUE_TEMPLATE/*.yml`, `mcp.json`, `plugin.json`): rút ra các pattern hay về viết kịch bản plain-language, báo lỗi tái hiện cho dev, vòng hồi quy ad-hoc, cùng điểm giới hạn (phụ thuộc cloud/API key) khi so với TDQ — Test: `py -3 -X utf8 -c "from pathlib import Path; t = Path('docs/tdq/artifacts/2026-11-21-1438-cai-thien-qc-test-e2e/phan-tich-terterarmy-cli.md').read_text(encoding='utf-8'); assert all(k in t for k in ('SKILL.md', 'reporting-template.md', 'TESTER.md', 'BUG_BOARD.md', '01-landing-page.md')) and len(t) > 1200"`
  - Req: `§1, §2#1, Q2` · Ngoài phạm vi: không sửa kho `C:\Users\admin\Documents\terterarmy-cli`, không gọi API cloud
  - Chạm: `docs/tdq/artifacts/2026-11-21-1438-cai-thien-qc-test-e2e/phan-tich-terterarmy-cli.md` (tạo mới)
  - Cần: `Không`
  - Worktree: `none` (`scoped-write` trong `docs/tdq/artifacts/2026-11-21-1438-cai-thien-qc-test-e2e/`)

- [x] **T1.3** (e12m) Research `4`–`6` chuẩn/plugin QA & E2E lớn trên mạng bằng `tavily-primary` (`tavily_search` + `tavily_extract`): (1) Playwright Test Agents (`planner` / `generator` / `healer`) & Playwright MCP, (2) Testing Trophy (Kent C. Dodds) & Google Test Sizes / Practical Test Pyramid, (3) Risk-Based Testing & Test Impact Analysis / Changed-Flow Smoke, (4) `1`–`2` AI E2E/browser testing frameworks thực chiến (như Stagehand / Browser-Use / Claude Code testing workflows); ghi đầy đủ query, URL nguồn và trích đoạn gốc vào `docs/tdq/research/2026-11-21-1438-cai-thien-qc-test-e2e.md` và `raw/` — Test: `py -3 -X utf8 -c "from pathlib import Path; t = Path('docs/tdq/research/2026-11-21-1438-cai-thien-qc-test-e2e.md').read_text(encoding='utf-8'); raw = list(Path('docs/tdq/artifacts/2026-11-21-1438-cai-thien-qc-test-e2e/raw').glob('*.txt')); assert t.count('https://') >= 4 and ('Playwright' in t or 'playwright' in t) and len(raw) >= 2 and len(t) > 1500"`
  - Req: `§1, §2#2, Q2` · Ngoài phạm vi: ghi dữ liệu web vào file research/raw, không xả dữ liệu thô ra chat
  - Chạm: `docs/tdq/research/2026-11-21-1438-cai-thien-qc-test-e2e.md`, `docs/tdq/artifacts/2026-11-21-1438-cai-thien-qc-test-e2e/raw/*.txt` (tạo mới)
  - Cần: `Không`
  - Worktree: `none`

**Xong P1 khi**: Cả `3` tệp thu thập Wave 1 có mặt trên đĩa với trích dẫn `path:line` thật và `>= 4` URL đã kiểm xuất.

## P2 — Wave 2 Hợp nhất Bằng chứng & Soạn Báo cáo Đề xuất 4 phần

- [x] **T2.1** (e8m) Hợp nhất toàn bộ bằng chứng từ Wave 1 vào `evidence-log.md` và `evidence.jsonl` (tối thiểu `15` mục `[EV-001]`..`[EV-015+]`), đối chiếu định lượng từng giả thuyết `H1`–`H4` (xác nhận đúng phần nào, bác bỏ hoặc giới hạn phần nào kèm các quy chuẩn cốt lõi của TDQ cần giữ lại dưới dạng tự động hóa ẩn) — Test: `py -3 -X utf8 -c "import json, re; from pathlib import Path; md = Path('docs/tdq/artifacts/2026-11-21-1438-cai-thien-qc-test-e2e/evidence-log.md').read_text(encoding='utf-8'); rows = [json.loads(l) for l in Path('docs/tdq/artifacts/2026-11-21-1438-cai-thien-qc-test-e2e/evidence.jsonl').read_text(encoding='utf-8').splitlines() if l.strip()]; assert len(set(re.findall(r'\bEV-\d{3}\b', md))) >= 15 and len(rows) >= 15 and all(h in md for h in ('H1', 'H2', 'H3', 'H4'))"`
  - Req: `§1, §2#1, Q1, Q4` · Ngoài phạm vi: chỉ tổng hợp từ bằng chứng thật đã kiểm ở Wave 1
  - Chạm: `docs/tdq/artifacts/2026-11-21-1438-cai-thien-qc-test-e2e/evidence-log.md`, `docs/tdq/artifacts/2026-11-21-1438-cai-thien-qc-test-e2e/evidence.jsonl` (tạo mới)
  - Cần: `T1.1`, `T1.2`, `T1.3`

- [x] **T2.2** (e14m) Soạn hoàn chỉnh báo cáo đề xuất `4` phần tại `docs/tdq/reports/2026-11-21-1438-cai-thien-qc-test-e2e.md` theo mạch dễ đọc cho dev (`> Tóm tắt nhanh`, kèm `4` phần bắt buộc: (1) Chẩn đoán thực chứng có/không hàn lâm ở TDQ, (2) Đối chiếu TDQ vs `terterarmy-cli` & `4`–`6` chuẩn ngành, (3) Thiết kế mô hình QC/E2E mới gồm Auto Meta-Gate + Dev Behavior QC Card + `3` tầng tốc độ với *Changed-Flow E2E Smoke* + mẫu kịch bản plain-language + phương án giữ lại phần lõi tốt của TDQ, (4) Lộ trình chia đợt áp dụng & KPI đo được; mọi luận điểm gắn `[EV-xxx]` và nhãn độ tin cậy `Verified`/`Single-source`/`Inferred`) — Test: `py -3 -X utf8 -c "from pathlib import Path; t = Path('docs/tdq/reports/2026-11-21-1438-cai-thien-qc-test-e2e.md').read_text(encoding='utf-8'); assert all(k in t for k in ('Tóm tắt nhanh', 'EV-', 'Verified', 'terterarmy-cli', 'Changed-Flow', 'KPI')) and len(t) > 3500"`
  - Req: `§1, §2#3, §3c, Q3` · Ngoài phạm vi: chưa sửa mã nguồn sản phẩm hay chạy `render` Archify HTML (để Wave 3 chốt kiểm chứng trước pha `report`)
  - Chạm: `docs/tdq/reports/2026-11-21-1438-cai-thien-qc-test-e2e.md` (tạo mới)
  - Cần: `T2.1`

**Xong P2 khi**: `evidence-log.md`, `evidence.jsonl` và bản thảo đầy đủ báo cáo `4` phần hoàn tất với truy vết `[EV-xxx]` đầy đủ.

## P3 — Wave 3 Kiểm chứng Bằng chứng & Zero-Code-Touch

- [x] **T3.1** (e8m) Thực hiện kiểm chứng bằng chứng theo `muc_qc = full` (`QC-I1` kiểm `100%` `[EV-xxx]` trong báo cáo khớp `evidence.jsonl` & tệp/URL tồn tại; `QC-I2` kiểm chéo `Claim <-> Source` không sai lệch `F6`; `QC-I4` kiểm nhãn `Verified`/`Single-source`/`Inferred`; `doc_lint.py` thoát `0` và `git diff --name-only dev..HEAD` chỉ gồm tệp trong `docs/tdq/` & `docs/workinglog/`) rồi ghi kết quả vào `docs/tdq/qc/2026-11-21-1438-cai-thien-qc-test-e2e.md` — Test: `py -3 -X utf8 scripts/doc_lint.py docs/tdq/reports/2026-11-21-1438-cai-thien-qc-test-e2e.md docs/tdq/qc/2026-11-21-1438-cai-thien-qc-test-e2e.md && py -3 -X utf8 -c "import subprocess; from pathlib import Path; files = [f.strip() for f in subprocess.check_output(['git', 'diff', '--name-only', 'dev..HEAD'], text=True).splitlines() if f.strip()]; bad = [f for f in files if not f.startswith(('docs/tdq/', 'docs/workinglog/'))]; qc = Path('docs/tdq/qc/2026-11-21-1438-cai-thien-qc-test-e2e.md').read_text(encoding='utf-8'); assert not bad and 'QC-I1' in qc and 'QC-I2' in qc and 'QC-I4' in qc and 'PASS' in qc"`
  - Req: `§2#5, §5, Q4, Q5` · Ngoài phạm vi: không sửa mã nguồn; mọi sai sót tìm thấy trong báo cáo phải sửa trực tiếp trong P2/P3 trước khi chốt PASS
  - Chạm: `docs/tdq/qc/2026-11-21-1438-cai-thien-qc-test-e2e.md` (tạo mới)
  - Cần: `T2.2`

**Xong P3 khi**: `doc_lint.py` báo `0 violation(s)`, `100%` `[EV-xxx]` khớp nguồn thật, Zero-Code-Touch sạch `0` file ngoài `docs/`, sẵn sàng sang `qc` & `report` (Archify HTML + Tailscale `HTTP 200`).

## Cụm song song

- **Wave 1 (chạy song song không đụng tệp):** `T1.1`, `T1.2`, `T1.3` — mỗi nhiệm vụ đọc nguồn khác nhau và ghi ra tệp riêng biệt dưới `docs/tdq/artifacts/2026-11-21-1438-cai-thien-qc-test-e2e/` và `docs/tdq/research/`.
- **Wave 2 (tuần tự sau Wave 1):** `T2.1` → `T2.2`.
- **Wave 3 (tuần tự sau Wave 2):** `T3.1`.

## Luật file nóng

Không có tệp nóng chia sẻ giữa các task chạy song song (`T1.1`, `T1.2`, `T1.3` ghi tệp riêng biệt). Mọi cập nhật lên `docs/tdq/plan/...` và `docs/workinglog/2026-11-21.md` do Leader thực hiện.

## Definition of Done

- [x] Q1 Chẩn đoán thực chứng `H1`–`H4` trên `3` lớp TDQ với `>= 10` `[EV-xxx]` trỏ đúng `path:line` — Kiểm tra qua `evidence-log.md` và đối chứng `T1.1` (`QC-I1`)
- [x] Q2 Phân tích đầy đủ `33` tệp của `C:\Users\admin\Documents\terterarmy-cli` và `4`–`6` nguồn chuẩn ngành qua `tavily-primary` tại `docs/tdq/research/2026-11-21-1438-cai-thien-qc-test-e2e.md` — Kiểm tra trích xuất URL và file phân tích `T1.2`/`T1.3`
- [x] Q3 Báo cáo đề xuất `4` phần hoàn chỉnh kèm thiết kế mô hình QC/E2E mới (*Auto Meta-Gate*, *Dev Behavior QC Card*, *Changed-Flow E2E Smoke*) và lộ trình KPI tại `docs/tdq/reports/2026-11-21-1438-cai-thien-qc-test-e2e.md` — Đọc trực tiếp và kiểm tra cấu trúc ở `T2.2`
- [x] Q4 Đạt cổng bằng chứng `QC-I1` (`100%` `[EV-xxx]` khớp `evidence.jsonl`), `QC-I2` (`0` hallucination đối chiếu nguồn thô) và `QC-I4` (nhãn `Verified`/`Single-source`/`Inferred`) — Ghi tại `docs/tdq/qc/2026-11-21-1438-cai-thien-qc-test-e2e.md`
- [x] Q5 `py -3 -X utf8 scripts/doc_lint.py` thoát `0` (`0 violation(s)`) trên báo cáo/QC và `git diff --name-only dev..HEAD` giữ `Zero-Code-Touch` (`0` file ngoài `docs/tdq/` & `docs/workinglog/`)
- [x] Q6 Archify HTML `docs/tdq/reports/2026-11-21-1438-cai-thien-qc-test-e2e.html` đạt `tdq_archify.py verify` (`status="current"`, `valid=true`) và truy cập qua Tailscale URL trả `HTTP 200`
