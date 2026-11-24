# Đề xuất Cải thiện Archify: Drill-down Nhiều tầng & Tái sử dụng Node {#bao-cao}

Nghiên cứu xác nhận TDQ có thể giữ nguyên engine gốc không cần fork, chỉ bọc thêm kho Logic Node và vỏ điều hướng nhiều tầng. Cách làm này giải quyết tình trạng tràn khung đọc và tiết kiệm tới chín mươi lăm phần trăm lượng token khi cập nhật.

## 1. Hiện trạng Phẳng & Nút thắt Phình Dung lượng {#hien-trang}

@workflow id=wf-before-bottleneck title="Trước: Sơ đồ phẳng 1 tầng và đóng gói lặp"
| model_flat | Model 1 tầng | database |
| hash_5804 | Băm 5804 file | backend |
| zip_loop | Gói zip 276KB | external |
| ui_overflow | 4/6 View tràn | security |
| model_flat > hash_5804 | Bẩn cả tệp |
| hash_5804 > zip_loop | Render 2.83s |
| zip_loop > ui_overflow | Kho 9.27 MB |

Kiểm tra trình duyệt thực tế cho thấy bốn trên sáu sơ đồ hiện bị ẩn bản xem trước vì quá rộng so với khung đọc. Đồng thời mỗi sơ đồ con lại gói lặp một bản chạy riêng khiến dung lượng tăng nhanh.

## 2. Kiến trúc Đề xuất: No-Fork Hybrid & Logic Registry {#kien-truc-sau}

@workflow id=wf-after-hybrid title="Sau: Kho Logic Node AST và Vỏ Lười Đa tầng"
| ast_scan | Hash AST/Symbol | backend |
| node_reg | Kho Logic Node | database |
| slice_svg | Lát SVG <=5 node | external |
| portal_ui | Vỏ Drill-down | frontend |
| ast_scan > node_reg | Đổi mới cập |
| node_reg > slice_svg | Không fork gốc |
| slice_svg > portal_ui | Lazy HTTP/fallback |

Hệ thống chỉ cập nhật lại đúng những node có thân hàm thay đổi và giữ nguyên node sạch để tái sử dụng chéo. Các tầng sâu từ ba đến năm chỉ được dựng chi tiết lần đầu khi có yêu cầu chạm tới.

## 3. Minh họa Chuỗi Login 5 tầng & Bảo vệ Chu trình {#vi-du-login}

@workflow id=wf-login-5layers title="Mẫu 5 Tầng: Đăng nhập & Chống Chu trình"
| l1_entry | T1: Đăng nhập | frontend |
| l2_rem | T2: Nhớ Login? | backend |
| l3_store | T3: Cookie/RAM | database |
| l4_jwt_cyc | T4-5: JWT & Neo | security |
| l1_entry > l2_rem | Click xem tiếp |
| l2_rem > l3_store | Ghi vào đâu |
| l3_store > l4_jwt_cyc | Replay + Error |

Người đọc đi từ bức tranh tổng quan rồi bấm sâu từng bước để xem giải thích tự nhiên và nơi lưu token an toàn. Các node dùng chung như ký JWT được tham chiếu lại nhiều nơi mà không phải vẽ lại.
