# QC — Nghiên cứu cải thiện Archify theo hướng drill-down nhiều tầng và tái sử dụng Logic Node
Ngày: 2026-11-24 · Plan: ../plan/2026-11-24-1106-research-archify-drilldown-nodes.md (Vòng 1)
Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

## Dev Behavior QC Card
- Auto Meta-Gate: PASS (2/2 checks, 0.19s — `doc_lint` 0 lỗi, `git_co_author` 0 lỗi)
- Luồng đổi: Nghiên cứu kiến trúc (`work_kind=investigate`) phân tích năng lực `tt-a1i/archify`, lớp wrapper `scripts/*archify*.py`, DOM thực tế `docs/architecture/index.html` và đề xuất kiến trúc No-Fork Hybrid + Logic Node Registry (`0` file mã nguồn TDQ bị sửa).
- Chạy thử thật (Before → After + Bằng chứng tươi): `14/14` chứng cứ trong `evidence.jsonl` trích dẫn đủ trong báo cáo (`0` orphan, `0` ID thiếu); `23/23` mốc `path:line` tồn tại khớp dòng trên đĩa; `logic-node-schema-and-login-example.json` parse sạch (`12` nodes, `max_depth=5`, `6` node `reused_by >= 2`, có cycle anchor); `doc_lint.py` (kèm `--pair`) exit `0`; `git diff --name-only dev -- scripts/ hooks/ plugins/ tools/ tests/` rỗng; `tdq_archify.py verify` trả `status=current`; Tailscale Serve `https://unity-pc-rtx3060.tail99896.ts.net/vlog/tdq-workflow-agy/reports/2026-11-24-1106-research-archify-drilldown-nodes.html` trả HTTP `200`; Chrome DevTools audit xác nhận `0` console error/warning trên cả `docs/architecture/index.html` lẫn HTML báo cáo.
- Rủi ro còn lại: Yêu cầu không sửa code nên chưa triển khai Pilot; các con số tiết kiệm token/thời gian cho kịch bản `120` nodes là ngoại suy có kiểm soát (`Inferred`) từ số liệu đo nền (`~2.83s`/view `finalize`, `9.27 MB` `docs/architecture/`); `chrome-devtools` ghi nhận ở viewport hiện tại bảng explainer vẫn thu các sơ đồ ngang rộng (`4/6` view trên `index.html`) sang modal nên request code sau cần dùng shell/SVG tối ưu khung đọc.

| # | Hạng mục | Lệnh đã chạy | Kết quả | PASS/FAIL |
|---|---|---|---|---|
| Q1 | `QC-I1` Grounding tự động (`evidence.jsonl`, `path:line`, `0` placeholder, scope) | Script Python đối chiếu `evidence.jsonl` + quét regex `path:line` + `git diff --name-only dev -- scripts/ hooks/ plugins/ tools/ tests/` | `ev_total=14, cited=14, missing=0, uncited=0`; `path_line_checked=23, failures=[]`; `git_diff=''` | PASS |
| Q2 | `QC-I2` Đối chiếu nguyên văn (`L2` `tt-a1i/archify` & `scripts/*archify*.py`) | Đối chiếu từng claim trong `s1.md`–`s3.md` với dòng đọc trực tiếp trong phiên + Chrome DevTools snapshot `index.html` | Toàn bộ số byte (`2,622,525` B `index.html`, `5,804` files `manifest.json`), `durationMs` (`2,833 ms` mean) và `focusNodeAttrs` khớp nguyên văn | PASS |
| Q3 | `QC-I3` Kiểm chứng đủ `4` giả thuyết `H1`–`H4` kèm điểm nghẽn thực tế | Kiểm tra hiện diện `H1`–`H4` + phản ví dụ (`4/6` view tràn width, `_hash_file` false-dirty, `file://` CORS) trong `s1..s4` & report | Đủ `4/4` kết luận rõ (`H1`, `H2`, `H3`, `H4`) kèm bằng chứng thực nghiệm và ca biên | PASS |
| Q4 | `QC-I4` Nhãn tin cậy, Schema JSON hợp lệ & `doc_lint.py` exit `0` | `py -3 -c "... json.loads(...)"` + `py -3 -X utf8 scripts/doc_lint.py ...` + `--pair` | `nodes=12, max_depth=5, reused=6`; `doc_lint` `0 violation(s) total, exit 0`; nhãn `Verified`/`Inferred` đầy đủ | PASS |
| Q5 | `0` code diff + Archify HTML `current` + Tailscale Serve HTTP `200` | `tdq_archify.py render` + `verify` + `urllib` GET Tailscale URL + Chrome DevTools `pageId=21` | `status="current"`, `durationMs=2294`, `HTTP_STATUS: 200 TITLE_OK: True`, `0` console error | PASS |
| QC-F1 | Auto Meta-Gate & Smoke/Unit Suite | `py -3 -X utf8 scripts/tdq_meta_gate.py` (miễn suite code vì `work_kind=investigate` & `0` file code đổi) | `Auto Meta-Gate: PASS (2/2 checks, 0.19s)` | PASS |
| QC-F2 | Hồi quy vùng chạm (`Chạm:`) | Kiểm tra không có mô-đun mã nguồn nào trong danh sách `Chạm:` | Toàn bộ tệp tạo mới nằm trong `docs/tdq/` (`KHÔNG CÓ CODE SỬA`) | PASS |
| QC-F3 | Ràng buộc kiến trúc (`spec §5` / `docs/kien-truc.md`) | Kiểm `s4.md` & Schema JSON đối chiếu với 3 ràng buộc (`scripts/` độc lập `hooks/`, `skills/` gọi CLI, tách khỏi `state.json`) | Không vi phạm ranh giới tầng; Registry đặt tại `docs/tdq/models/registry/` tách khỏi `state.json` | PASS |
| QC-F4 | Clean code invariants | Kiểm tra `git status --porcelain -- scripts/ hooks/ plugins/ tools/ tests/` | `KHÔNG ÁP DỤNG — không sửa file code` | PASS |

## Bằng chứng

### Q1 (`QC-I1`) & Phạm vi không sửa code
```text
ev_total=14, cited_in_report=14, missing_ids=set(), uncited_ids=set()
path_line_checked=23, failures=[]
git_diff_code_files: ''
git_status_code_files: ''
```

### Q2 (`QC-I2`) & Skill `chrome-devtools` `Kiểm`
- Mở trực tiếp `docs/architecture/index.html` trên Chrome DevTools (`pageId=19`): Accessibility Tree ghi nhận `4/6` view (`overview`, `pipeline-lifecycle`, `search-and-archify`, `hooks-and-gates`) hiện `"This diagram cannot fit this page width with readable text. Open the interactive view to inspect it."`; click nút `"Mở sơ đồ tương tác"` (`uid=1_19`) mở modal `<dialog>` + `<iframe srcdoc>` và `list_console_messages` trả `<no console messages found>`.
- Đo thực tế bằng Python trên `docs/architecture/index.html` và `manifest.json`: `disk_bytes=2622525`, `#archify-explainer-prepared=2005872`, `manifest_bytes=1222506`, `manifest_source_files_count=5804`, `docs_architecture_total_bytes=9268027`.
- Kiểm tra hợp đồng `S2`: `assert 'DOM' in t2 and 'master.model.json' in t2` PASS.

### Q3 (`QC-I3`) & Q4 (`QC-I4`)
```text
T2.1_GREEN_OK nodes=12 max_depth=5 reused=['auth-encrypt-send', 'storage-persist-session', 'server-verify-and-issue', 'cookie-write-policy', 'jwt-sign-and-store-jti', 'session-rotation-guard']
QC_AUTO_CHECKS_OK
[2026-11-24T12:50:39] doc_lint: done — 0 violation(s) total, exit 0
```

### Q5 — Archify HTML, Manifest Verify, Tailscale Serve & Live Chrome Check
```text
finalize: status="pass", diagnostics=[], durationMs=2294, bytes=1231504
verify: "status": "current", "valid": true, "document_digest": "ca5af6303d9ec83f55b426a8e7c3e88657d6883862b2fcb2224f798222f530d4"
doc_lint post-binding: 0 violation(s) total, exit 0
HTTP_STATUS: 200 TITLE_OK: True URL: https://unity-pc-rtx3060.tail99896.ts.net/vlog/tdq-workflow-agy/reports/2026-11-24-1106-research-archify-drilldown-nodes.html
Chrome DevTools pageId=21: 3 sơ đồ đã kiểm chuẩn, <no console messages found>
```

## Lệch spec chờ duyệt
không có

## Kết luận
PASS toàn bộ (`5/5` hạng mục `Q1`–`Q5` và `QC-F1`..`F4` đạt `PASS`; `0` lỗi). Sẵn sàng chuyển `phase=report` chốt tài liệu và hỏi user xác nhận commit.
