# Báo cáo — Tích hợp cộng sinh RTK và tự động kiểm/cài cho Antigravity {#tong-quan}

@meta locale=vi

Tổng quan kết quả: Cộng sinh RTK user-level (`C:\Users\admin\.local\bin\rtk.exe` + `rg.exe`) và gộp `search_gate` + `bash_gate` thành `command_gate.py` trên `PreToolUse`. Bổ sung trigger kiểm/xin quyền cài `SHA256` ở installer, `tdq_setup.py`, `setup_status.py` và `session_start.py` trong khi giữ sạch `MIT`.

## Trước request: Hai hook tuần tự, chưa có nén RTK và thiếu trigger cài đặt {#truoc-request}

@workflow id=bao-cao-truoc title="1. Trước request: Hai cổng PreToolUse rời rạc, chưa tích hợp RTK"
| seq_hooks | Chạy tuần tự search_gate rồi bash_gate | frontend |
| grep_gap | search_rules chưa bóc tiền tố rtk bypass proxy | security |
| no_rewrite | Chưa có rtk_integration và overwrite CommandLine | backend |
| no_trigger | Installer và tdq_setup chưa tự phát hiện rtk/rg | messagebus |
| seq_hooks > grep_gap |
| grep_gap > no_rewrite |
| no_rewrite > no_trigger |

Trước khi tích hợp, Antigravity chạy 2 tiến trình Python nối tiếp cho mỗi lệnh `run_command` và đưa thẳng đầu ra `git`/`pytest` chưa nén vào context. `search_rules` cũng chưa nhận diện tiền tố lách `rtk` (`rtk grep`, `rtk bypass rg`, `rtk proxy findstr`). Các bộ cài và `tdq_setup.py` chưa tự phát hiện `rtk`/`rg`, chưa cảnh báo trùng tên Rust Type Kit hay xin quyền cài bằng `SHA256`.

## Sau request: Cổng gộp command_gate, RTK cộng sinh và trigger xin quyền {#sau-request}

@workflow id=bao-cao-sau title="2. Sau request: Gộp command_gate.py, chuẩn hóa RTK và trigger xin quyền"
| single_gate | command_gate gộp search + bash trong 1 tiến trình | security |
| rtk_core | rtk_integration probe Collision Guard + rewrite <= 2s | backend |
| bypass_lock | search_rules chặn lách rtk trước khi viết lại lệnh | messagebus |
| consent_flow | Trigger installer, tdq_setup, session_start xin quyền | frontend |
| single_gate > bypass_lock |
| bypass_lock > rtk_core |
| rtk_core > consent_flow |

Sau khi tích hợp, `hooks/scripts/command_gate.py` gộp kiểm tra an toàn và gọi `rtk rewrite -- <cmd>` (timeout `<= 2 s` fail-open, xuất `overwrite.CommandLine`). `rtk_integration.py` loại trừ CWD/shim `.cmd` và miễn nén `git diff`/`log`/`show` cho subagent QC/reviewer/security. Mọi bước cài đặt đều tắt mặc định (`--with-rtk`, `TDQ_KHONG_CHAM_MAY=1`), xác thực `SHA256` từ GitHub Release mà không nhúng mã vào repo `MIT`.

## Kiểm thử: Bộ test 4313 ca, hiệu năng live và QC Vòng 2 {#kiem-thu}

@workflow id=bao-cao-kiem-thu title="3–4. Đã test và Kết quả kiểm chứng thực tế"
| live_gate | command_gate 71.50 ms và 126.52 ms + overwrite OK | security |
| plugin_parity | build OK, agy validate 0 findings, BYTE_DIFFS rỗng | messagebus |
| full_tron_bo | tdq_test tron-bo 4313 cases PASS trong 1167.36s | backend |
| ultra_qc | tdq-security SAFE + tdq-qc-tester Vòng 2 PASS | frontend |
| live_gate > plugin_parity |
| plugin_parity > full_tron_bo |
| full_tron_bo > ultra_qc |

Kết quả live cho thấy trung vị 7 lần chạy `command_gate.py` đạt `71.50 ms` (`TDQ_RTK=0`) và `126.52 ms` (`TDQ_RTK=1`, `tdq-qc-tester`: `73.22 ms` / `128.63 ms`). Bộ kiểm `Q1`–`Q4`, `token_budget --kiem` (`exit 0`), `agy.EXE plugin validate` (`0 findings`) và parity cục bộ (`BYTE_DIFFS: []`) đều đạt. Trọn bộ `tron-bo` (`task-3991`) PASS `4313` ca (`0` failed trong `1167.36s`), `tdq-security-reviewer` kết luận `SAFE` và `tdq-qc-tester` Vòng 2 kết luận `PASS everything`.
