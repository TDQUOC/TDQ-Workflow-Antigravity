# Báo cáo — Scan ảnh hưởng hook TDQ tới runtime & đề xuất hook dạng hướng dẫn {#bao-cao}

@meta locale=vi

Không sửa mã sản phẩm (user chọn `1c`), hoàn tất bộ bằng chứng định lượng (`8` file JSON + `6` script đo) từ `120` transcript và bản cài `~/.gemini/config/plugins/tdq-workflow-agy`, kèm báo cáo `9` mục và kiểm kê `29/29` mã cổng `[TDQ:*]` theo phương án hướng dẫn thay vì chặn.

## 1. Trước request và Sau request (luồng thực nghiệm & đề xuất) {#truoc-sau}

@workflow id=truoc-sau-hook-runtime title="Phân rã nguyên nhân lượt chậm và kiến trúc hook đề xuất (R1–R3)"
| luot_cham | Trước: 196 deny | external |
| phan_ra | Đo: API 440m | backend |
| de_xuat_hook | R1: Dispatcher | messagebus |
| chi_dan_4_phan | R2-R3: 4 phần | security |
| luot_cham > phan_ra | P1 đo 120 log |
| phan_ra > de_xuat_hook | R1 cache git |
| de_xuat_hook > chi_dan_4_phan | R2-R3 thẻ nhắc |

- **Trước request:** Phiên `"1 commit"` kéo dài `26,25` phút và nhiều phiên khác chậm bất thường; bản cài chạy đồng bộ `2` tiến trình `PreInvocation` (`prompt_context` `363,48 ms` + `search_observe` `85,98 ms`) + `PostInvocation` (`84,06 ms`) mỗi lần gọi model và `1–2` `PreToolUse` + `PostToolUse` mỗi bước tool qua `py -3`, kèm `196` lần `PreToolUse deny` và `60` `Stop block` lời nhắn cộc lốc.
- **Sau request (bằng chứng & thiết kế đề xuất):** Chứng minh `"1 commit"` mất `20,17 phút (76,83%)` do `4` lỗi `stream idle timeout (5m0s)` và `5,51 phút` cho model trên ngữ cảnh `420k` token (`hook` chỉ mất `2,15 s`, `commit_merge_trial` chỉ cộng `+3,71 s` trên `200` file); đồng thời thiết kế lộ trình `3` request (`R1`–`R3`) ước tính tiết kiệm `111,92` phút/4 ngày ở hook và `311,43` phút/4 ngày ngoài hook.

## 2. Đã test gì và Kết quả đo thực tế {#ket-qua-test}

| Hạng mục | Phạm vi kiểm tra | Kết quả thực đo | Trạng thái |
|---|---|---|---|
| `Q1 / Tx.2` Tái lập bench | `bench_hooks.py` (`N=12`) & `hook_impact.py` | Chênh lệch bench max `3,2%`, deny `12,8%` (`<= 20%`) | {good:PASS} |
| `Q2 / Q8` Kiểm kê cổng | AST `hooks/scripts/*.py` vs `gate_inventory.json` | `29/29` mã đủ `4` phần chỉ dẫn (`9/1/12/7`), `tdq-lean` khớp | {good:PASS} |
| `Q5` Ca chặn nhầm | `false_positive_repro.py` (`14` ca + đối chứng) | `SEARCH malformed` `7/8`, `TICK` `2/2`, `LSP non-LSP` `0/4` (vá ở `4c5d5fd5`) | {good:PASS} |
| `Q7 / Q9` Lượt dài & Git | `long_turns.json` (`60` lượt) & `commit_merge_trial.py` | `40/60 >= 0,9` (`f9e21752=0,988`), git thuần `1.240 ms` vs hook `4.948 ms` | {good:PASS} |
| `Q3 / Q4` Sạch & Lint | `git diff --stat dev` & `doc_lint.py` | `0` file ngoài `docs/`, `0` vi phạm lint (đã vá `[R15]` trên plan) | {good:PASS} |
| `QC-F1..F4` Hồi quy | `tdq_test.py vung-cham` (`207` module) | `4.315` pass, `35` skip, `0` fail, `radius misses: 0` | {good:PASS} |
