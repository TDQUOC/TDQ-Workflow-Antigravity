# Đối chiếu Trước và Sau — Quy trình Setupfully Zero-to-Full trên Antigravity {#truoc-sau-setupfully}
@meta locale=en

Bản thiết kế đối chiếu lệnh cài đặt cũ với kiến trúc hai pha tự động qua ranh giới khởi động lại Antigravity.

## 1. Hiện trạng Trước Nâng cấp — Lệch Đường dẫn & Đứt Mạch Sau Restart {#panel-before-setup}

@workflow id=wf-before-setup title="Hiện trạng: Cài đặt Rời rạc & Bám Đường dẫn Claude Code"
| b_cmd | Gọi setup rời từng cờ | external |
| b_claude | Ghi nhầm ~/.claude* | messagebus |
| b_cave | Caveman cứng sys.executable | backend |
| b_arch | Thiếu tự cài Archify | database |
| b_rst | Sau Restart mất dấu | security |
| b_cmd > b_claude | Thiếu HostAdapter AGY |
| b_claude > b_cave | Báo nợ giả trên máy mới |
| b_cave > b_arch | Vỡ cấu hình đa OS |
| b_arch > b_rst | Không có cờ bền vững |

Hiện tại bộ lệnh setup mặc định đọc ghi cấu hình Claude Code, chèn đường dẫn cá nhân và mất dấu sau khi tắt ứng dụng.

## 2. Thiết kế Sau Nâng cấp — Một Lệnh Setupfully & Tự Kiểm Thử 6 Tầng {#panel-after-setup}

@workflow id=wf-after-setup title="Thiết kế mới: Một lệnh Setupfully → Restart → Simulate Test 6 Tầng"
| a_trig | Gõ setupfully tdq-workflow | external |
| a_hook1 | Hook kích hoạt --setupfully | messagebus |
| a_p1 | Cài Core + Add-ons + Archify | backend |
| a_state | Lưu setup-state & pending flag | database |
| a_rst | Restart Antigravity nạp PATH | security |
| a_sim | Tự chạy Simulate Test 6 tầng | security |
| a_trig > a_hook1 | Đồng ý trọn gói user-space |
| a_hook1 > a_p1 | Bọc Caveman Node & secrets |
| a_p1 > a_state | Ghi dấu phiên cha PID |
| a_state > a_rst | Khóa chờ phiên IDE mới |
| a_rst > a_sim | Tự phát [TDQ:SETUP] kiểm thử |

Câu lệnh `"setupfully tdq-workflow"` tự cài trọn gói Pha 1, lưu dấu phiên và tự chạy kiểm thử 6 tầng ngay sau khi khởi động lại.

## 3. Kiến trúc Thành phần Sau Nâng cấp {#panel-arch-modules}

@workflow id=wf-arch-modules title="Chuỗi Phối hợp Module Đa Hệ Điều Hành cho Google Antigravity"
| mod_boot | Bootstrap & Probe (ps1/sh/mjs) | external |
| mod_setup | HostAdapter (tdq_setup.py) | backend |
| mod_mcp | Launcher (tdq_mcp_launcher.mjs) | messagebus |
| mod_state | State & PID (tdq_setup_state.py) | database |
| mod_sim | Verifier (tdq_simulate_verify.py) | security |
| mod_boot > mod_setup | Cấp Git, Node, uv, Python, agy |
| mod_setup > mod_mcp | Cấu hình lsp, caveman, tavily |
| mod_mcp > mod_state | Nạp mềm secrets.env 0600 |
| mod_state > mod_sim | Mở cổng --post-restart-verify |

Mọi cấu hình MCP chỉ dùng biến tương đối `${PLUGIN_ROOT}` và `${PLUGIN_DATA}`, vượt qua cổng kiểm tra nghiêm ngặt trên cả ba hệ điều hành.
