# Thiết kế Trước và Sau Nâng cấp Pha P2 {#truoc-sau-p2}

@meta locale=en

Bản vẽ giải thích luồng cầu nối CLI một chiều Pha P2. Công cụ tắt mặc định và nối thẳng với định tuyến P1 cùng bộ khởi tạo state duy nhất.

## 1. Cầu nối CLI 1 chiều tắt mặc định (Docker/WSL2) {#cli-bridge-p2}

@workflow id=p2-cli-before title="Trước: Chưa có cầu nối kéo ticket Paperclip vào TDQ"
| user | Người dùng Docker hoặc WSL2 | external |
| missing | Chưa có CLI kết nối Paperclip API | backend |
| manual | Phải tự đặt slug HHMM và gõ lệnh | database |
| norpt | Không có lệnh đẩy báo cáo về ticket | cloud |
| user > missing | |
| missing > manual | |
| manual > norpt | |

Trước đây người dùng muốn đưa ticket Paperclip sang TDQ phải chép nội dung thủ công. Chưa có lệnh nào kiểm sức khỏe API hay gửi báo cáo ngược lại.

@workflow id=p2-cli-after title="Sau: CLI 1 chiều stdlib tắt mặc định (status, pull, push-report)"
| cli | tdq_paperclip_bridge CLI 1 chiều | external |
| cfg | Đọc defaults + env (enabled=false thoát 3) | security |
| api | Gọi http/https REST + che token | backend |
| repo | Kết nối P1 + tdq_state init + report | database |
| cli > cfg | |
| cfg > api | |
| api > repo | |

Khi công tắc tắt, cầu nối thoát mã 3 và không mở kết nối mạng. Khi bật, ba lệnh con chạy thuần thư viện chuẩn Python và giữ nguyên luồng Windows.

## 2. Kết nối P1 Domain, Single-Writer State & Đóng gói An toàn {#state-packaging-p2}

@workflow id=p2-pack-before title="Trước: Config và danh sách release thiếu phần bridge"
| config | tdq-config chưa có khối paperclip_bridge | database |
| pull | Chưa tự gắn domain_id và tạo brief | backend |
| pack | Danh sách release chưa mở bridge | cloud |
| test | Chưa có bộ mock test ngoại tuyến | security |
| config > pull | |
| pull > pack | |
| pack > test | |

Bản phát hành và cấu hình gốc chỉ mới chứa khối P0 và P1. Chưa có bài kiểm thử giả lập ngoại tuyến nào bảo vệ luồng tích hợp mới.

@workflow id=p2-pack-after title="Sau: Pull nối domain P1, State v6 và Mock 100% Offline"
| pull | pull lấy issue + kiểm Bearer token | backend |
| domain | tdq_domains + tdq_state init + brief | database |
| mock | Bộ test mock HTTP và lỗi 401/timeout | security |
| bundle | Cập nhật whitelist + sync AGY và main | cloud |
| pull > domain | |
| domain > mock | |
| mock > bundle | |

Lệnh kéo ticket luôn đi qua cửa `tdq_state.py init` để giữ đúng một chủ ghi state. Việc xóa ba tệp mới giúp hoàn nguyên sạch sẽ hai pha trước.
