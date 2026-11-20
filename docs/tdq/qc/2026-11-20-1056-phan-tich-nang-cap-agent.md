# QC — Báo cáo phân tích hạn chế & phương án nâng cấp hệ thống agent TDQ Workflow

Ngày: 2026-11-20 · Plan: ../plan/2026-11-20-1056-phan-tich-nang-cap-agent.md · Vòng: 1
Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

| # | Hạng mục | Lệnh đã chạy | Kết quả | PASS/FAIL |
|---|---|---|---|---|
| Q1 | Đủ `14` hạn chế `4` trụ cột & khớp `file:line` trên đĩa | Python regex kiểm `^### HC-\d+` và `49` trích dẫn + `qc_deep_check.py` | `Q1_OK 14 49` (`BAD_CITES=[]`, `16/16` symbol tồn tại) | PASS |
| Q2 | Độ phủ nghiên cứu ngoài (`Claude Code`, `superpowers`, `BMAD`, `OpenHands`, `SWE-agent`, `MAST`, `ECC`), minh bạch `2/6` và ưu tiên Antigravity | Python kiểm đủ `9` từ khóa bắt buộc + đối chiếu `11` URL từ `research.md` | `Q2_OK 9` (`UNVERIFIED=[]`) | PASS |
| Q3 | Kiểm chuẩn `doc_lint.py` toàn bộ bộ tài liệu và ghép cặp `--pair` | `py -3 -X utf8 scripts/doc_lint.py <5 file> --pair <spec> <plan>` | `0` vi phạm toàn bộ (`exit 0`) | PASS |
| Q4 | Kết xuất Archify HTML báo cáo, manifest `current` (`valid=true`) và Tailscale HTTP `200` | `tdq_archify.py verify --document ... --manifest ...` & `urllib.request` | `status=current`, `valid=true`, `Q4_HTTP 200`, `1.599.032` byte | PASS |
| Q5 | Bảo toàn phạm vi `docs`: `0` tệp code runtime bị sửa trên nhánh | Python kiểm `git diff --name-only dev...HEAD` và `git status --porcelain` | `Q5_OK 27` (`0` tệp ngoài `docs/`) | PASS |
| QC-F1 | Chạy trọn bộ unit suite (`full`) và kiểm sổ `tdq_test.py so` | `py -3 -X utf8 scripts/tdq_test.py tron-bo --workers 1 --fresh --reuse off` | `4525` tests, `skipped=36`, `0` fail trong `1227.94s`; `tron_bo=1/2`, `bo_sot=0` | PASS |
| QC-F2 | Kiểm tra hồi quy vùng chạm `Chạm:` (`docs/tdq/**`) | Không có module code bị chạm; kiểm cặp `--verify-plan`, `--check-wave`, `doc_lint` | `verify_plan errors=0`, `check_wave errors=0`, `0` lỗi lint | PASS |
| QC-F3 | Ràng buộc kiến trúc phải giữ từ Spec `§5` | `git diff` kiểm `skills/`, `scripts/`, `hooks/`, `agents/`, `tools/`, `plugins/` | `CODE_OR_SKILL_TOUCHED: []`; `doc_lang=vi`; state qua `tdq_state.py` | PASS |
| QC-F4 | Clean code self-check trên file mã nguồn sửa đổi | Kiểm phạm vi diff thực tế của request | `KHÔNG ÁP DỤNG — không sửa file code` | PASS |

## Bằng chứng

### Q1
```
HC_COUNT=14
CITE_COUNT=53
BAD_CITES=[]
SYMBOLS_CHECKED=16 MISSING=[]
Q1_OK 14 49
```

### Q2
```
URLS_IN_REPORT=11 UNVERIFIED=[]
Q2_OK 9
```

### Q3
```
doc_lint: 0 violation(s) total, exit 0 (brief, research, spec, plan, reports, qc)
doc_lint --pair spec plan: exit 0
tdq_plan_scaffold verify_plan -> tasks=3 errors=0
tdq_plan_scaffold check_wave -> tasks=3 errors=0
```

### Q4
```
status=pass · diagnosticSummary: total=0
binding: status=current · valid=true
TAILSCALE_HTTP 200 1599032
```

### Q5
```
Q5_OK 27 (0 paths outside docs/)
CODE_OR_SKILL_TOUCHED: []
```

### QC-F1
```
[TDQ:TEST] PASS — scope=full backend=pytest tests=4525 skipped=36 in 1227.94s.
full-suite runs: 1 of budget 2
radius misses: 0
```

### QC-F2 & QC-F3 & QC-F4
```
verify_plan -> tasks=3 errors=0 · check_wave -> tasks=3 errors=0
spec §5: 0 thay đổi trong skills/, scripts/, hooks/, agents/, tools/, plugins/
QC-F4: KHÔNG ÁP DỤNG — không sửa file code
```

## Lệch spec chờ duyệt
không có

## Kết luận
PASS toàn bộ `5/5` hạng mục DoD (`Q1`–`Q5`) và `4/4` mục cố định (`QC-F1`–`QC-F4`); `0` khiếm khuyết còn tồn tại.
