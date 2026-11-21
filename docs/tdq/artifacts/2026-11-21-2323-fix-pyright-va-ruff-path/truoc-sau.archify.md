# Kế hoạch Bổ sung Pyright tools/ và Auto-Add User PATH {#ke-hoach}

Gỡ hai giới hạn đã ghi nhận sau bản 0.105.0 mà không cài thêm gói ngoài. Thay đổi gồm mở rộng phạm vi quét Python cho LSP và tự nạp thư mục công cụ người dùng sẵn có vào PATH.

## 1. Cấu hình Pyright quét thư mục tools/ {#pyright-tools}

@workflow id=wf-pyright-tools title="Trước và sau khi thêm tools vào pyrightconfig.json"
| b_cfg | Chỉ quét scripts hooks tests | external |
| b_fail | Bốc trúng tools thì TRUOT 1 ref | messagebus |
| a_cfg | Thêm tools, chặn trùng plugins | backend |
| a_pass | Dò đủ tham chiếu đạt ĐẠT | security |
| b_cfg > b_fail | LSP chạy nhưng thiếu phạm vi |
| a_cfg > a_pass | Kịch bản python:. hết trượt giả |

Cấu hình `exclude` thêm `plugins` giúp Pyright không đếm trùng mã nguồn đã sao chép sang gói Antigravity.

## 2. Tự động thêm User Scripts vào PATH {#user-scripts-path}

@workflow id=wf-user-path title="Trước và sau khi tự thêm User Scripts sẵn có vào PATH"
| u_missing | ruff.exe nằm ở Roaming Scripts | external |
| u_err | Gọi ruff trong PATH báo thiếu | messagebus |
| u_scan | Kiểm tra thư mục Scripts có exe | backend |
| u_winreg | Nạp os.environ và HKCU Path | security |
| u_missing > u_err | Không tự sửa dù đã cài sẵn |
| u_scan > u_winreg | ruff chạy ngay theo quyền user |

Cơ chế chỉ nạp thư mục đang tồn tại, chứa công cụ thực thi hợp lệ, chạy idempotent và bỏ qua khi bật cờ khóa máy thử nghiệm.
