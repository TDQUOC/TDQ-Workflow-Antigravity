# Báo cáo Archify — Tối ưu hiệu năng hook & chỉ dẫn 4 phần (R1+R2+R3) {#bao-cao-tong-quan}

@meta locale=en

Yêu cầu đã triển khai ba nhóm tối ưu R1+R2+R3 và hoàn tất vá QC hai vòng cho gói plugin. Lõi Claude Code (1a) giữ nguyên tương thích và thư mục `~/.gemini` không bị ghi đè (4b). Toàn bộ 4.399 kiểm thử `tron-bo`, Smoke/Runtime dưới 120s và `tdq-qc-tester` đều đạt `PASS`.

## Trước request: đa tiến trình py -3, git lặp và chặn cứng cộc lốc {#truoc-request}

@workflow id=bao-cao-truoc title="Trạng thái và luồng trước request (v0.99.0)"
| old_spawn | 2-3 tiến trình py -3 | messagebus |
| old_turn | Xóa sổ + 3 git/bước | backend |
| old_deny | Chặn cộc lốc + lệch cổng | security |
| old_spawn > old_turn | 449.5ms PreInv |
| old_turn > old_deny | 196 deny + 235ms Stop |

Trước khi sửa, mỗi sự kiện phải mở `py -3`, xóa `turns-<sid>.jsonl` và gọi `git` nhiều lần. Độ trễ `PreInvocation` đạt `449,5 ms` và `Stop` đạt `235,1 ms` khi chốt lượt. Ngoài ra `search_rules.py` báo nhầm PowerShell, còn `overwrite` làm mất khóa `Arguments` của `call_mcp_tool`.

## Sau request: 1 dispatcher python -X utf8, mốc lượt transcriptPath và 22 cổng 4 phần {#sau-request}

@workflow id=bao-cao-sau title="Trạng thái và luồng sau request (R1+R2+R3 + QC2)"
| new_disp | 1 dispatch.py (python) | messagebus |
| new_turn | transcriptPath + cache + lock | backend |
| new_gate | 9 cứng · 2 overwrite · 12 mềm | security |
| new_disp > new_turn | 126.1ms PreInv |
| new_turn > new_gate | 77.3ms Stop + 4 phần |

Nay `hooks.json` chạy duy nhất `python -X utf8 hooks/scripts/dispatch.py` và cache `repo_root` có khóa ghi. Cổng AGY dùng `transcriptPath` kèm `prompt_sha`, bỏ 7 script thừa (`EXCLUDED_AGY_HOOKS`) và tái dùng 1 `git status` ở `Stop`. `rtk` bỏ qua builtin cộng cache `mtime`, còn `gate_guidance.py` xuất đồng thời dòng model ngắn và thẻ `user_markdown` 4 phần.

## Đã test gì & kết quả kiểm chứng thực tế (`ultra`) {#da-test-va-ket-qua}

@workflow id=bao-cao-qc title="Hành trình kiểm thử Vòng 2 từ Unit, Benchmark đến tron-bo"
| ut_gate | Benchmark & Unit QC2 | frontend |
| smoke_rt | Smoke 3.30s · RT 3.24s | messagebus |
| full_suite | tron-bo 4.399 test | backend |
| qc_indep | tdq-qc-tester (ultra) | security |
| ut_gate > smoke_rt | 80/274 pass 0 fail |
| smoke_rt > full_suite | PreInv 126.1ms Stop 77.3ms |
| full_suite > qc_indep | 0 miss PASS |

Benchmark `bench_dispatch.py` đo `PreInvocation` `126,1 ms`, `run_command (git status)` `93,4 ms` và `Stop` `77,3 ms`. Toàn bộ 4.399 test `tron-bo` (`350,31s`), `validate --strict` (`0` findings), `ruff C901` và Smoke/Runtime đều đạt `PASS`. Agent `tdq-qc-tester` Vòng 2 chạy 274 test, xác nhận `PASS` toàn bộ và còn 3 ghi chú nhỏ không chặn.
