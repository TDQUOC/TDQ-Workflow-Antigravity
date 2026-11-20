# QC — Đề xuất Kiến trúc `work_kind=investigate` (Phân tích, Red-Team 3 Chiều & Báo cáo V2)

Ngày: 2026-11-21 · Spec: ../spec/2026-11-20-2355-toi-uu-research-phan-tich.md · Plan: ../plan/2026-11-20-2355-toi-uu-research-phan-tich.md · Vòng: 1 (Độc lập `tdq-qc-tester`)
Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

| # | Hạng mục | Lệnh đã chạy | Kết quả | PASS/FAIL |
|---|---|---|---|---|
| Q1 | Kho bằng chứng `evidence-log.md` có `>= 20` mục `EV-xxx` đủ timestamp, nguồn, trích đoạn thật và nhãn độ tin cậy | Python kiểm regex `EV-\d{3}`, parse 29 dòng bảng, check `path:line` trên đĩa | `29` mục duy nhất (`EV-001`..`EV-029`), `missing_fields: []`, `105/105` specs hợp lệ | PASS |
| Q2 | Đủ `4` tệp V1 (`>1500` chars), phủ `173` bản ghi `timing.jsonl`, đủ `M1`–`M6`, `0` placeholder | Python kiểm độ dài, `173`, `M1`–`M6`, unbackticked `TBD/TODO/FIXME/XXX` | `42,142 / 39,138 / 37,526 / 22,978` chars; `173` & `M1`–`M6` đủ; `placeholders=[]` | PASS |
| Q3 | Đủ `3` tệp Red-Team A/B/C độc lập, mỗi tệp `>= 3` `ND-[ABC]\d+`, phủ `4` ca thật (`1056`, `1457`, `1346`, `1953`) | Python kiểm regex `ND-[ABC]\d+` và đối chiếu thư mục thật dưới `docs/tdq/` | `5` `ND-A1..A5`, `6` `ND-B1..B6`, `6` `ND-C1..C6`; `4/4` ca khớp `20/17/23/21` tệp thật | PASS |
| Q4 | Kiểm tự động `100%` `path:line` trong V1/V2/Report tồn tại trên đĩa, spot-check `>=5` nguồn gốc chống F6, truy vết `100%` `ND-*` & nhãn tin cậy | Python kiểm mọi `path:line` (cả dấu phẩy + bare file) + đọc trực tiếp nguồn đĩa & `timing.jsonl` | V2 `77+35` (`bad=0`), Report `9+25` (`bad=0`), V1 `7+11` (`bad=0`); `5/5` spot-check khớp `0` F6; `17/17` & `9/9` `ND-*` đủ | PASS |
| Q5 | Báo cáo V2 vá `100%` `ND-*`, `0` lỗi `doc_lint.py`, Archify manifest `current` (`valid=true`), Tailscale HTTP `200` | `doc_lint.py`, `tdq_archify.py verify` (+ probe âm tính manifest thiếu), `urllib.request` Tailscale URL | `doc_lint` `0` vi phạm (`exit 0`); `status=current`, `valid=true`; probe thiếu manifest `invalid` (`exit 1`); HTTP `200` (`1,612,572` B) | PASS |
| Q6 | Zero-Code-Touch: `0` tệp ngoài `docs/` bị chạm so với `dev`; `~/.gemini/config/plugins/` nguyên `mtime` | `git status --porcelain`, `git diff --name-only dev`, `os.walk` `~/.gemini/config/plugins/tdq-workflow-agy` | `git_status=27` (`non_docs=[]`), `git_diff_dev=4` (`non_docs=[]`), newest plugin mtime `2026-11-20T14:57:00` | PASS |
| QC-F1 | Kiểm tra unit suite theo `loai_request=docs` (không sửa code sản phẩm) | Kiểm `git diff --name-only dev` xác nhận `0` file mã nguồn thay đổi | Không áp dụng chạy `tron-bo` vì `loai_request=docs` & `0` tệp ngoài `docs/` chạm (`EV-005`/`ND-8`) | PASS |
| QC-F2 | Kiểm tra hồ sơ vùng chạm (`docs/tdq/**`) | `doc_lint.py` 5 hồ sơ + `--pair spec plan`; `tdq_plan_scaffold.py --verify-plan` & `--check-wave` | `0` lỗi lint (`exit 0`); `verify_plan tasks=16 errors=0`; `check_wave tasks=16 errors=0` | PASS |
| QC-F3 | Ràng buộc kiến trúc phải giữ từ Spec `§5` | Đối chiếu `git status` & `git diff` trên `scripts/`, `hooks/`, `skills/`, `agents/`, `tools/`, `plugins/`, `tests/` | `0` tệp code/hook/skill/agent/test/config sửa; giữ chuẩn phụ thuộc & bất biến | PASS |
| QC-F4 | Clean code self-check trên file mã nguồn sửa đổi | Kiểm phạm vi diff thực tế | `KHÔNG ÁP DỤNG — không sửa file code` | PASS |

## Bằng chứng Chi tiết

### Q1 — Kho bằng chứng `evidence-log.md`
```
total_mentions=29, unique=29, ids=EV-001..EV-029
table_rows=29, missing_fields=[]
evidence-log.md: specs=105 (full path), bare=46, bad=[]
```

### Q2 — Bộ hồ sơ V1 & Thực nghiệm `timing.jsonl`
```
phan-tich-thuc-nghiem-timing.md: chars=42142, has_173=True, placeholders=[]
phan-tich-kien-truc-codebase.md: chars=39138, has_173=True, placeholders=[]
phan-tich-research-ngoai-sau.md: chars=37526, has_173=True, placeholders=[]
de-xuat-kien-truc-v1.md: chars=22978, M1..M6 + work_kind/no_worktree/scoped-write/QC-I1..I4=True, placeholders=[]
```

### Q3 — Phản biện Red-Team 3 chiều (A · B · C)
```
redteam-a-luong-va-compact.md: chars=27535, unique_ND=5 -> ['ND-A1', 'ND-A2', 'ND-A3', 'ND-A4', 'ND-A5']
redteam-b-bao-mat-va-tinh-tuong-thich.md: chars=29557, unique_ND=6 -> ['ND-B1', 'ND-B2', 'ND-B3', 'ND-B4', 'ND-B5', 'ND-B6']
redteam-c-stress-test-cases.md: chars=30928, unique_ND=6 -> ['ND-C1', 'ND-C2', 'ND-C3', 'ND-C4', 'ND-C5', 'ND-C6']
case 1056/1457/1346/1953: in_redteam_c=True, real_repo_files=20 / 17 / 23 / 21
```

### Q4 — Kiểm chứng `path:line`, Spot-Check Chống F6, Nhãn Tin cậy & Truy vết
```
de-xuat-kien-truc-v2.md: specs=77, bare=35, bad=[]
2026-11-20-2355-toi-uu-research-phan-tich.md (Report): specs=9, bare=25, bad=[]
de-xuat-kien-truc-v1.md: specs=7, bare=11, bad=[]
Traceability V2 & Report: Missing ND-A/B/C=[], Missing ND-1..9=[]
Confidence labels V2: {'Verified': 5, 'Single-source': 2, 'Inferred': 3} · Report: {'Verified': 11, 'Inferred': 1}
```

**Spot-check trực tiếp trên tệp nguồn đĩa (chống ALCE F6):**
1. `docs/tdq/timing.jsonl`: `174` dòng JSON hợp lệ (`171` slug duy nhất; `idx=173` đóng lúc `2026-11-21T00:00:04+07:00`), `nz=156`, `sum_non_idle=3,288,169.1s`, `pooled pre=37.1%` vs `imp=26.9%`, `investigate — full` (`N=25`): `med_pre=1,888.0s (49.9%)` vs `med_imp=780.0s (12.7%)`, `pre > imp = 20/25`.
2. `scripts/tdq_state.py:2334-2336, 2414-2423`: Xác nhận gán trực tiếp `state["phase"] = "implement"` cho `quick` (`L2417`) và `plan` (`L2335, L2422`) mà không gọi `ghi_moc_phase(state, "implement")` (`L497`).
3. `hooks/rust/tdq-dispatch/src/events/pre_tool_use.rs:65-72, 110-122, 171-178, 290-302, 333-335, 444-450`: Xác nhận `is_readonly_role` dùng `low.contains("reviewer")`, `canonical_or_ancestor` chỉ resolve `1` cấp parent, `is_qc_report_target` chạy `normalize_lexical` trước `resolve_rel_in_project`, `qc-tester` allow không `observe`, `role_opt.is_some()` đẩy xuống `DelegatePython`, và `has_range` trả `Allow` ở `L448-449`.
4. `scripts/tdq_team.py:2480-2524`: Xác nhận `blackboard_record` dùng `tempfile.mkstemp` + `os.replace` không bọc khóa NTFS.
5. `tools/patches/gate_guidance.json:31-54` & `docs/tdq/token-budget.json`: Xác nhận `all_agy_codes` có `22` mã (`L32-53`); `qc.md=3479`, `team-mode.md=3472`, `vision-test-loop.md=3461` tokens.

### Q5 — Lint, Archify Verify & Tailscale HTTP
```
doc_lint (report): 0 violation(s) total, exit 0
doc_lint (5 docs) & --pair spec plan: 0 violation(s), exit 0
tdq_archify.py verify: status=current, binding.valid=true, manifest.status=current, exit 0
tdq_archify.py verify (negative missing manifest): status=invalid, exit 1
TAILSCALE_HTTP=200, bytes=1612572
```

### Q6 — Zero-Code-Touch & Plugin ngoài repo
```
branch: docs/toi-uu-research-phan-tich
git status --porcelain: 27 paths, non_docs=[]
git diff --name-only dev: 4 paths, non_docs=[]
~/.gemini/config/plugins/tdq-workflow-agy newest mtime: 2026-11-20T14:57:00.063061
```

## Khiếm khuyết ghi nhận (`DEFECTS`)
1. **Minor** — Báo cáo `docs/tdq/reports/2026-11-20-2355-toi-uu-research-phan-tich.md:1,8` được soạn/render trước lúc đóng QC nên ghi `(7/7 task + 6/6 DoD tick đủ)` và `QC PASS 6/6 DoD`, trong khi `docs/tdq/plan/2026-11-20-2355-toi-uu-research-phan-tich.md` thực tế có **`10` task** (`T1.1`–`T5.1`) và `Q1`–`Q6` (`L153-158`) còn đang `[ ]` chờ bước `report` hoàn tất — repro: đối chiếu `plan.md:65-158` với `report.md:1,8` (leader cần sửa `7/7 task` → `10/10 task`, tick `Q1`–`Q6`, rồi re-verify Archify khi vào pha `report`).
2. **Minor** — Tệp trung gian Wave 3 `docs/tdq/artifacts/2026-11-20-2355-toi-uu-research-phan-tich/redteam-b-bao-mat-va-tinh-tuong-thich.md:57,68` còn nhắc `hooks/scripts/bash_gate.py:387` (`max=371` dòng; dòng `387` nằm ở bản compiled `plugins/tdq-workflow-agy/hooks/scripts/bash_gate.py:387`, bản gốc tương ứng `L345-352`) — repro: kiểm tra `len(open('hooks/scripts/bash_gate.py').readlines()) == 371` (đã được bắt và sửa sạch tại `EV-029`, `de-xuat-kien-truc-v2.md` và `report.md`).

## Kết luận
VERDICT: **PASS everything** (`6/6` DoD `Q1`–`Q6` PASS thực chứng; `QC-F4`: `KHÔNG ÁP DỤNG — không sửa file code`; `2` lưu ý Minor cần leader đồng bộ metadata trong pha `report`).
