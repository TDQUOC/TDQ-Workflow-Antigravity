# QC — Scan ảnh hưởng của hook TDQ tới runtime & đề xuất hook dạng hướng dẫn

Ngày: 2026-11-18 · Plan: ../plan/2026-11-18-1346-scan-hook-anh-huong-runtime.md · Mức QC: `lite` · Vòng: 1
Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

| # | Hạng mục | Lệnh đã chạy | Kết quả | PASS/FAIL |
|---|---|---|---|---|
| Q1 | Số đo tái lập (<= 20%) | `bench_hooks.py --n 12` & `hook_impact.py` | Chênh max bench `3,2%`, deny `12,8%` (`<= 20%`) | PASS |
| Q2 | Kiểm kê cổng 100% mã | AST scan `gate_inventory.json` vs `hooks/scripts/*.py` | `grepped_count=29 == len(cong)=29`; `lean_ok=True` | PASS |
| Q3 | Không sửa mã sản phẩm | `git diff --stat dev` & `git status --short` | 100% file dưới `docs/` (`0` file ngoài `docs/`) | PASS |
| Q4 | Tài liệu sạch (`doc_lint`) | `py -3 scripts/doc_lint.py` (sau sửa R15 trên plan) | `0` vi phạm trên brief, spec, plan, research | PASS |
| Q5 | Ca chặn nhầm có bằng chứng | Kiểm `false_positive_repro.json` | 14 ca + đối chứng (`7/8` search, `2/2` tick, `0/4` lsp + lý do) | PASS |
| Q6 | Ước tính truy được | Đối chiếu công thức mục `(e)` với JSON | 7/7 hàng có công thức `= (hiện_tại − mục_tiêu) × tần_suất` | PASS |
| Q7 | Trả lời "tại sao lâu" | Kiểm `long_turns.json` | `60` lượt (`40` `do_phu >= 0.9`, `20` ghi chú `subagent/compaction`) | PASS |
| Q8 | Lời chỉ dẫn đủ 4 phần | Kiểm khóa `loi_de_xuat` trong `gate_inventory.json` | `29/29` mã đủ `chuyen_gi`, `vi_sao`, `lam_gi`, `bo_qua` | PASS |
| Q9 | Thử commit/merge (N >= 5) | Kiểm `commit_merge_trial.json` | `N=5`, `git_only=1240,3ms`, `git_with_hook=4327,02ms`, `pre+post=4948,02ms` | PASS |
| Hợp đồng | 3 khối `Dùng:` trong plan | Chạy lệnh `Kiểm` của `tdq-lean`, `agy-customizations`, `tdq-conventions` | `lean_ok=True`, `21` match hợp đồng hook, `Soul` ở L2 | PASS |
| QC-F1 | Unit test (`lite`) | `py -3 scripts/tdq_test.py vung-cham` | `PASS` `4.315` pass, `35` skip, `0` fail (`207` module) | PASS |
| QC-F2 | Hồi quy vùng chạm | `git diff --stat dev` + `tdq_test.py so` | `0` file mã sản phẩm chạm; `radius misses: 0` | PASS |
| QC-F3 | Ràng buộc kiến trúc (spec §5) | Đối chiếu `git diff --stat dev` với spec §5 | Không chạm mã sản phẩm nào ngoài `docs/` | PASS |
| QC-F4 | Clean code | Soát theo `clean-code.md` | KHÔNG ÁP DỤNG — không sửa file code sản phẩm | PASS |

## Bằng chứng

### Q1 & Tx.2
```text
BENCH_DIFF_%: {'baseline py -3 -c pass': 0.5, 'baseline python.exe -c pass': 1.6, 'PreInvocation prompt_context': 0.8, 'PreInvocation search_observe': 1.9, 'PreToolUse read_gate': 1.0, 'PreToolUse edit_gate': 1.8, 'PreToolUse command_gate': 0.2, 'PreToolUse search_gate': 0.1, 'PreToolUse lsp_gate (call_mcp_tool)': 1.1, 'PreToolUse search_observe (call_mcp_tool)': 3.2, 'PostToolUse search_observe (run_command)': 1.9, 'PostInvocation post_invocation': 2.7, 'Stop stop_gate': 0.5}
DENY_DIFF_%: 12.8 (196 -> 221 trên 122 transcript)
```

### Q2, Q5, Q7, Q8, Q9
```text
Q2: grepped= 29 cong= 29 q8_ok= True lean_ok= True (chan_cung=9, huong_dan=12, tu_sua=1, xoa=7)
Q5: Q5_groups= {'lsp_non_lsp', 'tick_loop', 'search_malformed'} total= 14
Q7: Q7_turns= 60 cov_ge_0.9= 40 all_annotated= True (f9e21752 "1 commit": dur=1575.0s, api_err_s=1210.0s, do_phu=0.9882)
Q9: Q9_n= 5 git_only= 1240.3 git_with_hook= 4327.02 pre_post= 4948.02
```

### Q4 (sửa R15 trên plan trong QC vòng 1)
Ban đầu `doc_lint.py` báo 4 lỗi `[R15]` trên T1.2, T1.3, T1.4, T2.1 vì có `*.py` trong `Chạm:` nhưng thiếu dòng `Đặc tả kỹ thuật & Logic cốt lõi:`. Đã bổ sung vào `plan` và chạy lại:
```text
doc_lint: lint 1 file: 2026-11-18-1346-scan-hook-anh-huong-runtime.md -> 0 violation(s) total, exit 0
doc_lint: pairing spec <-> plan -> 0 violation(s)
doc_lint: brief, spec, research -> 0 violation(s) total, exit 0
```

### QC-F1 & QC-F2
```text
status: PASS, exit_code: 0, action: executed, provenance: current_job
modules: 207, tests_run: 4350 (pass: 4315, fail: 0, error: 0, skip: 35)
tdq_test.py so -> full-suite runs: 0 of budget 2, radius misses: 0
```

## Lệch spec chờ duyệt
không có

## Kết luận
PASS toàn bộ (14/14 hạng mục, gồm 9 DoD + hợp đồng skill + QC-F1..F4). Không có defect mở.
