# PLAN — Báo cáo phân tích hạn chế & phương án nâng cấp hệ thống agent TDQ Workflow

Ngày: 2026-11-20 · Spec: ../spec/2026-11-20-1056-phan-tich-nang-cap-agent.md (bản 1.0, ĐÃ DUYỆT) · Lane: full
Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md
Mode thực thi: main — tdq_bench.py simulate thắng nhánh main (6.1 phút so với team 9.2 phút, chênh 3.1 phút trên 3 wave tuyến tính)
Trạng thái plan: HOÀN THÀNH

## Mục lục

- Quy tắc thi hành
- Thiết kế Trước vs Sau
- Ràng buộc toàn cục & Bản đồ Sở hữu Hợp đồng (Ownership Map)
- P1 — Tổng hợp chứng cứ & Soạn báo cáo Markdown
- P2 — Trực quan hóa Archify HTML & Phục vụ Tailscale
- P3 — Log & Kiểm chứng toàn diện (QC full)
- Cụm song song
- Luật file nóng
- Definition of Done

## Quy tắc thi hành

- Ngôn ngữ tài liệu là tiếng Việt (`doc_lang = vi`), trình bày tự nhiên và dễ hiểu cho kỹ sư phần mềm.
- Đây là request loại `docs` ở mức kiểm định `full`. Mọi tác vụ tuyệt đối không sửa mã nguồn trong `agents/`, `scripts/`, `hooks/`, `tools/` hay `plugins/`.
- Toàn bộ nội dung báo cáo và biên bản QC chỉ trích dẫn các tệp, dòng mã và URL đã kiểm chứng trực tiếp trên đĩa.
- Chạy hết các kiểm tra tự động sau mỗi chặng và hoàn tất `Q1`–`Q5` trước khi xuất khối báo cáo cuối cùng.

## Thiết kế Trước vs Sau

Bản xem trước tương tác Trước/Sau đã được khóa gắn với spec tại `docs/tdq/spec/2026-11-20-1056-phan-tich-nang-cap-agent-preview.html` (manifest `docs/tdq/spec/2026-11-20-1056-phan-tich-nang-cap-agent-preview.manifest.json`, trạng thái `current`).

| Khía cạnh | Hiện trạng (Trước) | Thiết kế mới (Sau — Đề xuất trong Báo cáo) |
|---|---|---|
| Kích hoạt & Vai trò | `3/6` agent mồ côi; `tdq-qc-tester` chỉ chạy `ultra`; thiếu Explorer và Debugger. | Gắn điểm gọi mặc định theo sự kiện; thêm `tdq-explorer` và `tdq-debugger` dùng chung. |
| Quyền Tool & Model | `skills_and_agents.py` bỏ `effort`, đổi `flash`/`pro`, cấp `run_command` cho reviewer, thiếu tool tìm kiếm. | Đồng nhất chuẩn `inherit`/`high`, siết `disallowedTools`, khôi phục LSP/Grep và sửa hợp đồng commit. |
| Hook & Bảo vệ thực thi | Không có `SubagentStop`; `register_subagent_role` bỏ trống; `command_parser.rs` sót `python -c`/`node -e`. | Bổ sung `SubagentStop` Python và Rust; ghi role lúc spawn; bịt lỗ hổng shell inline. |
| Handoff, Packet & Eval | Hai `handoff-schema.json` lệch nhau; trả text tự do; Packet thiếu Mini-Spec; thiếu telemetry từng agent. | Thống nhất `1` JSON schema; Packet kèm Mini-Spec đa ngôn ngữ; thêm Blackboard và KPI từng role. |

## Ràng buộc toàn cục & Bản đồ Sở hữu Hợp đồng (Ownership Map)

- Quy chuẩn văn bản: Mọi câu trong báo cáo và biên bản QC giữ độ dài `<= 35` từ để luôn qua sạch `doc_lint.py` (`0` lỗi R5).
- Quy chuẩn chứng cứ: Mọi trích dẫn dạng `path:line` phải tồn tại thật trên đĩa của nhánh `docs/phan-tich-nang-cap-agent` và khớp tên symbol gốc.
- Minh bạch giới hạn ngoài: Ghi rõ `tavily-primary` đạt `2/6` truy vấn trước khi chạm hạn mức keyless; không suy diễn chi tiết từ repo chưa đọc.
- Thứ tự khóa SHA: Chỉ kết xuất `Archify HTML` (`T2.1`) sau khi báo cáo Markdown (`T1.1`) hoàn thiện để manifest không bị `stale`.

| Hợp đồng / Giao diện | Định nghĩa cốt lõi | Task sở hữu | Task tiêu thụ |
|---|---|---|---|
| `ReportContract` | Cấu trúc `6` phần báo cáo (`Phan 1`–`Phan 6`), `14` mục `### HC-01`–`### HC-14` và `4` phần nghiệm thu. | `T1.1` | `T2.1`, `T3.1` |
| `ExplainerHTML` | Kịch bản `@workflow` tuyến tính, tệp `.html` tại `docs/tdq/reports/`, manifest `current` và HTTP `200`. | `T2.1` | `T3.1` |
| `QCReportFull` | Biên bản `docs/tdq/qc/<slug>.md` đối chứng `file:line`, `5` cổng `Q1`–`Q5` và kết luận `PASS`. | `T3.1` | Cổng đóng request |

## P1 — Tổng hợp chứng cứ & Soạn báo cáo Markdown

- [x] **T1.1** (e14m) Tổng hợp `14` hạn chế trên `6` agent, đối chiếu nguồn ngoài/nội bộ và viết báo cáo hoàn chỉnh theo `ReportContract` — Test: `py -3 -X utf8 scripts/doc_lint.py docs/tdq/reports/2026-11-20-1056-phan-tich-nang-cap-agent.md`
  - Req: `§2#1`, `§2b(M1-report-md)`, `§3c(ReportContract)` · Ngoài phạm vi: `GIỮ NGUYÊN` toàn bộ mã nguồn runtime và `spec.md`.
  - Chạm: `docs/tdq/reports/2026-11-20-1056-phan-tich-nang-cap-agent.md`
  - Cần: Không
  - Tham chiếu: `docs/tdq/brief/2026-11-20-1056-phan-tich-nang-cap-agent.md`, `docs/tdq/research/2026-11-20-1056-phan-tich-nang-cap-agent.md`, `agents/tdq-implementer.md`, `agents/tdq-reviewer.md`, `tools/patches/skills_and_agents.py`, `scripts/tdq_team.py`
  - Giao tiếp: Consumes: `brief` + `research` + đối chứng đĩa | Produces: `docs/tdq/reports/2026-11-20-1056-phan-tich-nang-cap-agent.md` (`Phan 1`–`Phan 6`)
  - Neo & Công cụ: `Write` `docs/tdq/reports/2026-11-20-1056-phan-tich-nang-cap-agent.md` · đọc bảng thời gian từ `py -3 -X utf8 scripts/tdq_timing.py show`
  - Trước → Sau: Chưa có báo cáo hợp nhất → Có đủ `14` mục `### HC-01`..`### HC-14`, giải pháp `4` trụ cột Antigravity 2.0, lộ trình `P0`–`P3` và `Thân PR`.
  - Tiêu chí chấp nhận (EARS): KHI chạy `doc_lint.py` trên báo cáo, HỆ THỐNG PHẢI trả mã thoát `0` với đủ `14` mục `### HC-xx`.
  - Logic cốt lõi: Viết `6` phần theo `ReportContract` bằng tiếng Việt tự nhiên, kèm ẩn dụ xưởng phần mềm, bảng so sánh `8` nguồn ngoài/`ECC` và khối nghiệm thu `4` phần.
  - Ca góc hiểm & Assert: Kiểm tra mọi đường dẫn `path:line` trước khi ghi và giữ `<= 35` từ mỗi câu · `assert len(re.findall(r'^### HC-\d+', text, re.M)) == 14`

## P2 — Trực quan hóa Archify HTML & Phục vụ Tailscale

- [x] **T2.1** (e8m) Tạo kịch bản Archify explainer từ báo cáo Markdown, kết xuất HTML, khóa SHA manifest và kiểm tra URL Tailscale — Test: `py -3 -X utf8 scripts/tdq_archify.py verify --document docs/tdq/reports/2026-11-20-1056-phan-tich-nang-cap-agent.md --manifest docs/tdq/reports/2026-11-20-1056-phan-tich-nang-cap-agent.manifest.json`
  - Req: `§2#2`, `§2b(M2-archify-html)` · Ngoài phạm vi: `GIỮ NGUYÊN` nội dung `Phan 1`–`Phan 5` trong báo cáo Markdown.
  - Chạm: `docs/tdq/artifacts/2026-11-20-1056-phan-tich-nang-cap-agent/bao-cao-nghiem-thu.archify.md`, `docs/tdq/reports/2026-11-20-1056-phan-tich-nang-cap-agent.html`, `docs/tdq/reports/2026-11-20-1056-phan-tich-nang-cap-agent.manifest.json`, `docs/tdq/reports/2026-11-20-1056-phan-tich-nang-cap-agent.md`
  - Cần: T1.1
  - Tham chiếu: `docs/tdq/artifacts/2026-11-20-1056-phan-tich-nang-cap-agent/truoc-sau.archify.md`, `scripts/tdq_archify.py`
  - Giao tiếp: Consumes: `ReportContract` | Produces: `ExplainerHTML` + block `tdq-archify-binding` trong báo cáo Markdown
  - Neo & Công cụ: `Write` `docs/tdq/artifacts/2026-11-20-1056-phan-tich-nang-cap-agent/bao-cao-nghiem-thu.archify.md`, `docs/tdq/reports/2026-11-20-1056-phan-tich-nang-cap-agent.html`, `docs/tdq/reports/2026-11-20-1056-phan-tich-nang-cap-agent.manifest.json`
  - Trước → Sau: Chỉ có spec preview HTML → Có Archify explainer báo cáo chính thức chạy sống tại URL Tailscale HTTPS.
  - Tiêu chí chấp nhận (EARS): KHI kiểm định qua `tdq_archify.py verify` và HTTP Tailscale, HỆ THỐNG PHẢI báo `status=current`, `valid=true` và HTTP `200`.
  - Logic cốt lõi: Dựng `4` panel `@workflow` tuyến tính (nhãn nút `<= 22` ký tự, không quạt hình thoi) tóm tắt Hiện trạng, `4` Trụ cột, Antigravity Flow và Lộ trình `P0`–`P3`.
  - Ca góc hiểm & Assert: Tránh sửa báo cáo Markdown sau lúc `render` để không làm `stale` SHA · `assert verify_json["status"] == "current" and verify_json["valid"] is True`

## P3 — Log & Kiểm chứng toàn diện (QC full)

Log: BỎ — request loại docs không tạo hoặc sửa mã nguồn chạy được.

- [x] **T3.1** (e12m) Đối chứng toàn bộ trích dẫn `file:line` và nguồn ngoài trên đĩa, chạy đủ `Q1`–`Q5` và viết biên bản QC mức `full` — Test: `py -3 -X utf8 scripts/doc_lint.py docs/tdq/qc/2026-11-20-1056-phan-tich-nang-cap-agent.md`
  - Req: `§2#3`, `§2b(M3-qc-verify)`, `§6(Q1–Q5)` · Ngoài phạm vi: `GIỮ NGUYÊN` toàn bộ mã nguồn và nhánh `dev`.
  - Chạm: `docs/tdq/qc/2026-11-20-1056-phan-tich-nang-cap-agent.md`, `docs/tdq/plan/2026-11-20-1056-phan-tich-nang-cap-agent.md`
  - Cần: T2.1
  - Tham chiếu: `docs/tdq/reports/2026-11-20-1056-phan-tich-nang-cap-agent.md`, `docs/tdq/spec/2026-11-20-1056-phan-tich-nang-cap-agent.md`
  - Giao tiếp: Consumes: `ReportContract`, `ExplainerHTML` | Produces: `QCReportFull` tại `docs/tdq/qc/2026-11-20-1056-phan-tich-nang-cap-agent.md`
  - Neo & Công cụ: `Write` `docs/tdq/qc/2026-11-20-1056-phan-tich-nang-cap-agent.md` · chạy `doc_lint.py`, `doc_lint.py --pair` và các lệnh `Q1`–`Q5`
  - Trước → Sau: Chưa có biên bản nghiệm thu độc lập → Đầy đủ bằng chứng pass cho `14` hạn chế, Archify HTML, Tailscale HTTP `200` và git diff sạch.
  - Tiêu chí chấp nhận (EARS): KHI chạy đủ `Q1`–`Q5`, HỆ THỐNG PHẢI trả về trạng thái `PASS` ở cả `5` cổng và cập nhật plan sang `HOÀN THÀNH`.
  - Logic cốt lõi: Chạy kiểm tra tự động từng dòng `path:line` trên đĩa, kiểm `doc_lint.py --pair`, xác nhận `git diff dev...HEAD` chỉ có `docs/**`, rồi đánh dấu `[x]` các task.
  - Ca góc hiểm & Assert: Nếu phát hiện lệch dòng trên báo cáo phải sửa báo cáo rồi chạy lại `T2.1` và `T3.1` · `assert bad_git_paths == [] and lint_exit_code == 0`

## Cụm song song

- Wave 1 (tuần tự): `T1.1` (sở hữu `ReportContract` — soạn báo cáo Markdown hoàn chỉnh).
- Wave 2 (tuần tự): `T2.1` (phụ thuộc `T1.1` — kết xuất `ExplainerHTML`, bind SHA manifest và xác minh Tailscale HTTP `200`).
- Wave 3 (tuần tự): `T3.1` (phụ thuộc `T1.1` và `T2.1` — đối chứng `file:line`, chạy `Q1`–`Q5` và xuất `QCReportFull`).
- Toàn bộ `3` task tạo thành chuỗi phụ thuộc tuyến tính chặt (`T1.1 → T2.1 → T3.1`) nên chỉ cần `1` luồng thực thi nối tiếp.

## Luật file nóng

- Không có tệp mã nguồn chạy được nằm trong vùng sửa đổi của request này.
- Tệp `docs/tdq/reports/2026-11-20-1056-phan-tich-nang-cap-agent.md` chỉ được viết nội dung chính trong `T1.1` và được `tdq_archify.py render` gắn khối binding trong `T2.1`.
- Nếu `T3.1` phát hiện trích dẫn lệch dòng cần chỉnh báo cáo, tác nhân phải sửa xong rồi chạy lại `T2.1` để cập nhật SHA manifest trước khi đóng QC.

## Definition of Done

- [x] `Q1` Báo cáo có đủ `14` điểm hạn chế `### HC-01`..`### HC-14` phủ `4` trụ cột và mọi trích dẫn `file:line` tồn tại hợp lệ trên đĩa — Lệnh kiểm: `py -3 -X utf8 -c "import pathlib, re; t = pathlib.Path('docs/tdq/reports/2026-11-20-1056-phan-tich-nang-cap-agent.md').read_text(encoding='utf-8'); h = re.findall(r'^### HC-\d+', t, re.M); c = re.findall(r'((?:agents|hooks|scripts|tools|skills|plugins|tests)/[\w./-]+\.(?:py|md|rs|json|sh|ps1)):(\d+)', t); bad = [(p, n) for p, n in c if not pathlib.Path(p).exists() or int(n) not in range(1, len(pathlib.Path(p).read_text(encoding='utf-8').splitlines()) + 1)]; assert len(h) == 14 and not bad, (len(h), bad); print('Q1_OK', len(h), len(c))"`
- [x] `Q2` Báo cáo đối chiếu đầy đủ các nguồn nghiên cứu đã đọc, ghi minh bạch giới hạn quota `tavily-primary` (`2/6`) và ưu tiên Antigravity 2.0 — Lệnh kiểm: `py -3 -X utf8 -c "import pathlib; t = pathlib.Path('docs/tdq/reports/2026-11-20-1056-phan-tich-nang-cap-agent.md').read_text(encoding='utf-8'); req = ['Claude Code', 'obra/superpowers', 'BMAD', 'OpenHands', 'SWE-agent', 'MAST', 'ECC', '2/6', 'Antigravity']; miss = [k for k in req if k not in t]; assert not miss, miss; print('Q2_OK', len(req))"`
- [x] `Q3` Toàn bộ bộ tài liệu `spec`, `plan`, `reports`, `qc` sạch vi phạm `doc_lint.py` và ghép cặp `--pair` hợp lệ — Lệnh kiểm: `py -3 -X utf8 scripts/doc_lint.py docs/tdq/spec/2026-11-20-1056-phan-tich-nang-cap-agent.md docs/tdq/plan/2026-11-20-1056-phan-tich-nang-cap-agent.md docs/tdq/reports/2026-11-20-1056-phan-tich-nang-cap-agent.md docs/tdq/qc/2026-11-20-1056-phan-tich-nang-cap-agent.md; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }; py -3 -X utf8 scripts/doc_lint.py --pair docs/tdq/spec/2026-11-20-1056-phan-tich-nang-cap-agent.md docs/tdq/plan/2026-11-20-1056-phan-tich-nang-cap-agent.md`
- [x] `Q4` Tệp Archify HTML kết xuất thành công, manifest ở trạng thái `current` (`valid=true`) và truy cập Tailscale trả HTTP `200` — Lệnh kiểm: `py -3 -X utf8 scripts/tdq_archify.py verify --document docs/tdq/reports/2026-11-20-1056-phan-tich-nang-cap-agent.md --manifest docs/tdq/reports/2026-11-20-1056-phan-tich-nang-cap-agent.manifest.json; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }; py -3 -X utf8 -c "import urllib.request; r = urllib.request.urlopen('https://unity-pc-rtx3060.tail99896.ts.net/vlog/tdq-workflow-agy/reports/2026-11-20-1056-phan-tich-nang-cap-agent.html', timeout=10); assert r.status == 200; print('Q4_HTTP', r.status)"`
- [x] `Q5` Bảo toàn tuyệt đối phạm vi `docs`: `0` tệp mã nguồn runtime bị thêm hoặc sửa trên nhánh làm việc — Lệnh kiểm: `py -3 -X utf8 -c "import subprocess; out = subprocess.check_output(['git', 'diff', '--name-only', 'dev...HEAD'], text=True).splitlines() + subprocess.check_output(['git', 'status', '--porcelain'], text=True).splitlines(); bad = [x for x in out if x.strip() and not any(x.strip().lstrip('?!MADRCU ').startswith(p) for p in ('docs/', chr(34) + 'docs/'))]; assert not bad, bad; print('Q5_OK', len(out))"`
