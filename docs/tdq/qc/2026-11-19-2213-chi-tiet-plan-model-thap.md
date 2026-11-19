# QC — Phân tích Độ chi tiết của Plan cho Model Tier Thấp (`End-to-End`) và Đề xuất Cải thiện TDQ Workflow

Ngày: 2026-11-19 · Plan: ../plan/2026-11-19-2213-chi-tiet-plan-model-thap.md · Mức QC: `full` · Vòng: 1
Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

| # | Hạng mục | Lệnh đã chạy | Kết quả | PASS/FAIL |
|---|---|---|---|---|
| Q1 | Bằng chứng thực nghiệm Vòng 1 | `doc_lint.py` + kiểm chỉ dấu & `70/70` trích dẫn `path:line` trên `phan-tich-vong-1.md` | `0` lỗi lint, `48` task / `236` plan, `7` nguyên nhân gốc `RC-1..RC-7`, `70/70` `path:line` tồn tại & đúng biên dòng | PASS |
| Q2 | Độ phủ thiết kế 3 lớp V1 cho `2b` | `doc_lint.py` + kiểm `Lớp 1..3`, `Weak Planner`, `Weak Executor`, `quick-lane`, `QC fix` trên `de-xuat-v1.md` | `0` lỗi lint, phủ đủ `3` lớp (`3a`) + `2` đầu (`2b`) + `R15_MOC` | PASS |
| Q3 | Phản biện Red-Team độc lập Vòng 2 | `doc_lint.py` trên `redteam-a/b/c.md`, `phan-bien-vong-2.md` + đếm `\| ND-` | `18` phát hiện độc lập (`6` A + `6` B + `6` C) → `12` mã `ND-1..ND-12` ánh xạ `100%` sang V2 | PASS |
| Q4 | Kiểm chứng 3 cặp ví dụ Trước/Sau | Chấm `7` chiều trên `redteam-c-stress-test.md` & V2 ở báo cáo `reports/2026-11-19-2213-...md` | Cả `3/3` ca nâng lên `14/14` (`0046:T2.3`), `14/14` & `13/14` (`1632:T2.1`+`QC1.1`), `12/14` & `13/14` (`1457`+`0058`) | PASS |
| Q5 | Tài liệu sạch, 0 sửa ngoài `docs/`, Archify & Tailscale | `doc_lint.py` `11` file + `--pair`, `git status --porcelain`, `tdq_archify.py verify`, Tailscale `HTTP 200` | `0 violation(s)`, `non-docs: []`, Archify `status=current`, Tailscale `HTTP 200` (`1,613,090` bytes) | PASS |
| QC-F1 | Trọn bộ test repo (`muc_qc=full`) | `py -3 -X utf8 scripts/tdq_test.py tron-bo --workers 1 --fresh --reuse off` (`215` module) | **`4,423 passed, 35 skipped, 2,721 subtests passed, 0 failed`** (`1305.73s` exec, wall `1317.93s`, `exit 0`); `tdq_test.py so`: `tron_bo=1/2`, `bo_sot=0` | PASS |
| QC-F2 | Hồi quy vùng chạm | `git status --porcelain` + `tdq_test.py so` | `0` file mã nguồn ngoài `docs/` bị chạm; `radius misses: 0` | PASS |
| QC-F3 | Ràng buộc kiến trúc (spec §5) | Đối chiếu `git status --porcelain` & kiểm nội dung thiết kế V2 với `5` luật `docs/kien-truc.md` | `0` vi phạm vào `scripts/`, `hooks/`, `skills/`, `state.json`; thiết kế V2 tôn trọng `5/5` ràng buộc | PASS |
| QC-F4 | Clean code | Kiểm theo `skills/tdq-conventions/references/clean-code.md` | KHÔNG ÁP DỤNG — không sửa file code sản phẩm | PASS |

## Bằng chứng

### Q1–Q5 (`doc_lint`, `path:line` integrity, `git status`, `tdq_archify verify`)

```text
doc_lint: lint 11 file -> done — 0 violation(s) total, exit 0
doc_lint: pairing spec <-> plan -> 0 violation(s) total, exit 0
cited path:line checked: 70 missing/oob: []
git modified/untracked count: 22 non-docs: []
Q1..Q4_CHECKS_PASS
tdq_archify verify: status=current, valid=true
Tailscale HTTP 200: 1613090 bytes (https://unity-pc-rtx3060.tail99896.ts.net/vlog/tdq-workflow-agy/reports/2026-11-19-2213-chi-tiet-plan-model-thap.html)
```

### QC-F1 & QC-F2 (`tdq_test.py tron-bo` + `tdq_test.py so`)

```text
4423 passed, 35 skipped, 2721 subtests passed in 1305.73s (0:21:45)
[TDQ:TEST] PASS — scope=full backend=pytest tests=4458 skipped=35 in 1317.93s.
TDQ_RESULT {"path": "C:\\Users\\admin\\Documents\\Projects\\TDQ-Workflow-Antigravity\\docs\\tdq\\cache\\test-runs\\4afcf766ce18df54\\84ddee52d1d949388e24ea1f6989a77e\\result.json", "sha256": "f03afa1d45e42f0a533fee15ecbbae83aeab3480c69ef0c96fc08f7b6a146f20"}
full-suite runs: 1 of budget 2 · radius misses: 0
```

## Lệch spec chờ duyệt

không có

## Kết luận

PASS toàn bộ (`5/5` DoD `Q1–Q5` + `4/4` `QC-F1..F4`, `4,423 passed`, `0 failed`).
