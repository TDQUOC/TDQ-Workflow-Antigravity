# Báo cáo Xử lý Pyright tools/ và Tự thêm User PATH cho ruff {#bao-cao}

Xử lý dứt điểm hai giới hạn kỹ thuật sau đợt phát hành 0.105.0 mà không cài thêm gói ngoài. Hệ thống đã mở rộng phạm vi dò mã Python cho thư mục công cụ và tự nạp thư mục lệnh người dùng vào PATH.

## 1. Mở rộng Pyright quét tools/ {#pyright-tools-ket-qua}

@workflow id=wf-pyright-after title="Kết quả sau khi thêm tools vào pyrightconfig.json"
| b_skip | Pyright thiếu thư mục tools | external |
| b_err | Kiểm tra LSP đầu phiên trượt giả | messagebus |
| a_inc | Thêm tools và loại trừ plugins | backend |
| a_ok | Tìm được hai tham chiếu, đạt ĐẠT | security |
| b_skip > b_err | Chỉ thấy 1 nơi định nghĩa |
| a_inc > a_ok | Hết cảnh báo ngoài phạm vi |

Bộ test cổng LSP và đóng gói di động vượt qua toàn phần sau khi cấu hình mới được áp dụng.

## 2. Tự động thêm User Scripts vào PATH {#user-path-ket-qua}

@workflow id=wf-user-path-after title="Kết quả cơ chế tự nạp User Scripts và chạy ruff trực tiếp"
| u_old | ruff 0.17.3 kẹt ngoài PATH | external |
| u_scan | Kiểm tra thư mục có tệp thực thi | messagebus |
| u_add | Ghi User PATH và báo shell mới | backend |
| u_run | Lệnh ruff chạy trực tiếp exit 0 | security |
| u_old > u_scan | Bỏ qua thư mục rỗng và temp |
| u_add > u_run | Chạy lặp lại giữ nguyên idempotent |

Cơ chế mới đi cùng bản đồng bộ luật tự phục hồi, giữ vững giới hạn kích thước bản mẫu và sạch kiểm tra plugin.
