# Trước/Sau — Hợp nhất cổng PreToolUse với RTK và tự động kiểm/cài công cụ cho Antigravity {#tong-quan}

@meta locale=vi

Hiện trạng: Mỗi lệnh `run_command` trên Antigravity khởi chạy tuần tự hai tiến trình Python riêng (`bash_gate.py` và `search_gate.py`, đo trung vị `136.29 ms`), đầu ra CLI trả thô toàn bộ tốn ngữ cảnh, `_chuan_hoa` chưa bóc tiền tố `rtk`, và chưa có cơ chế phát hiện hay xin quyền cài `rtk` + `rg`. Thiết kế mới hợp nhất luồng `run_command` vào một tiến trình `command_gate.py` duy nhất (`68.85 ms` nền khi gộp), bóc vỏ `rtk` giữ chặt `[TDQ:SEARCH]`, gọi `rtk rewrite` xuất `overwrite.CommandLine` kèm kho SQLite recall lossless, bảo vệ `.venv` và diff QC, đồng thời bổ sung trigger kiểm và xin quyền cài đặt xác thực `SHA256`.

## Trước: Hai tiến trình hook rời, đầu ra CLI thô và chưa có kiểm/cài RTK {#truoc}

@workflow id=luong-truoc title="Trước: Chạy 2 tiến trình Python rời và trả đầu ra CLI chưa nén"
| run_cmd | Lệnh run_command từ agent | frontend |
| bash_gate_proc | Tiến trình 1: bash_gate kiểm tra quy ước | backend |
| search_gate_proc | Tiến trình 2: search_gate kiểm 3 tầng tìm kiếm | messagebus |
| raw_cli_out | Thực thi trực tiếp và trả đầu ra thô tốn token | database |
| run_cmd > bash_gate_proc |
| bash_gate_proc > search_gate_proc |
| search_gate_proc > raw_cli_out |

Hai tiến trình Python chạy nối tiếp gây dư độ trễ khởi tạo trên từng lệnh shell, chưa tận dụng `rtk` nén log test/build/git, và thiếu cơ chế nhắc xin quyền cài đặt công cụ trên máy mới.

## Sau: Cổng command_gate hợp nhất, nén RTK an toàn và trigger xin quyền cài đặt {#sau}

@workflow id=luong-sau title="Sau: 1 tiến trình command_gate hợp nhất + RTK rewrite + Trigger cài đặt"
| install_setup_trigger | Trigger install.py và SessionStart xin quyền cài RTK + rg (SHA256) | security |
| command_gate_unified | 1 tiến trình command_gate: bóc vỏ rtk, kiểm search_gate và bash_gate | messagebus |
| rtk_rewrite_overwrite | Tiền lọc an toàn (.venv / QC diff) và gọi rtk rewrite qua overwrite | backend |
| compressed_recall_out | Đầu ra nén gọn kèm kho lossless rtk recall hash | database |
| install_setup_trigger > command_gate_unified |
| command_gate_unified > rtk_rewrite_overwrite |
| rtk_rewrite_overwrite > compressed_recall_out |

Một tiến trình hợp nhất xử lý cả cổng luật lẫn tối ưu token thông qua `PreToolUse overwrite.CommandLine`, giữ repo sạch giấy phép MIT, chống lách `[TDQ:SEARCH]` bằng `rtk grep`/`rtk bypass`, bảo toàn môi trường `.venv pytest` và diff thô cho subagent kiểm định QC, còn bước cài `rtk` + `rg` chỉ chạy vào `~/.local/bin` khi có sự đồng ý rõ của người dùng.
