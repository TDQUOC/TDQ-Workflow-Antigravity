# Kiến trúc Đề xuất Quy trình Setup Máy Trống & Kiểm chứng Hậu Restart {#bao-cao}

Thiết kế mới nâng cấp skill setup thành quy trình hai cửa vào với một lần duyệt trọn gói, tự đối chiếu dấu phiên sau khởi động lại Antigravity và chạy giả lập sáu tầng trên thư mục tạm.

## 1. Luồng Cài đặt Hai Pha Qua Ranh Giới Restart {#setup-two-phase-flow}

@workflow id=wf-setup-two-phase title="Quy trình Setup Máy Trống Qua Ranh Giới Restart Antigravity"
| s_boot | Bootstrap máy trống (Git/Node/uv) | external |
| s_scan | Quét 1 lần → Duyệt Manifest | messagebus |
| s_inst | Cài Core + Add-ons & ghi State | backend |
| s_rst | Restart Antigravity (nạp PATH/MCP) | security |
| s_hook | Hook PreInvocation đối chiếu PID | messagebus |
| s_sim | Validate + Sandbox Simulate 6 tầng | security |
| s_boot > s_scan | Chưa có Git/Plugin |
| s_scan > s_inst | 1 lần duyệt trọn gói |
| s_inst > s_rst | Tạo cờ setup-pending |
| s_rst > s_hook | PID gốc đổi sang phiên mới |
| s_hook > s_sim | Tự phát [TDQ:SETUP-RESUME] |

Cờ nhẹ trong `${PLUGIN_DATA}` kết hợp dấu tiến trình cha (`Antigravity` và `language_server`) bảo đảm chỉ kích hoạt Pha 2 khi người dùng thực sự tắt và mở lại ứng dụng.

## 2. Chuyển đổi Lõi Cài đặt từ Claude Code sang Antigravity {#claude-to-antigravity-map}

@workflow id=wf-setup-migration title="Khắc phục Điểm lệch Cấu hình và Add-ons Đa Hệ Điều Hành"
| m_old | Trỏ ~/.claude* & sys.executable | security |
| m_path | Chuyển sang ~/.gemini/config/ | backend |
| m_cave | Node launcher mode caveman | backend |
| m_tav | Nạp mềm secrets.env 0600 | database |
| m_ok | Sandbox 6 tầng cô lập 0 rác | security |
| m_old > m_path | Khớp agy plugin & GEMINI.md |
| m_path > m_cave | Hết cứng Python máy cá nhân |
| m_cave > m_tav | Không bị variables khóa plugin |
| m_tav > m_ok | Core Gate + Optional Gate |

Tách riêng cổng kiểm cốt lõi và cổng add-on tùy chọn giúp máy headless hoặc chưa có khóa API vẫn xác minh xanh toàn bộ workflow chính.
