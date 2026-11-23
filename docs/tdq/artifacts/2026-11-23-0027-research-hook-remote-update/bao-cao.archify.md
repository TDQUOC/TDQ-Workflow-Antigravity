# Báo cáo Khả thi Hook Kiểm tra Bản mới Git Remote {#bao-cao}

Việc bổ sung hook tự kiểm tra phiên bản mới trên nhánh Git remote, nhắc trong chat xin quyền cập nhật và chạy nối tiếp `setupfully` hoàn toàn khả thi. Kết luận dựa trên kiểm chứng mã nguồn hiện hữu và đo đạc thực tế trên Antigravity Windows.

## 1. Chặng Kiểm tra Nền (0 ms Hot-Path) {#chang-kiem-tra-nen}

@workflow id=wf-bg-check title="Chặng 1: Dò bản mới chạy nền theo TTL"
| cold_hook | SessionStart Python | backend |
| ttl_stamp | Cache TTL PLUGIN_DATA | database |
| git_ls | git ls-remote 696ms | external |
| raw_ver | plugin.json gốc 426ms | external |
| cold_hook > ttl_stamp | Quá hạn TTL |
| ttl_stamp > git_ls | Popen tách biệt |
| git_ls > raw_ver | Đổi SHA mới tải |

Luồng kiểm tra tách việc gọi mạng sang tiến trình nền không chặn hot-path Rust. Chỉ khi mã commit trên nhánh phát hành thay đổi thì mới tải tệp phiên bản và lưu vào bộ nhớ đệm cục bộ.

## 2. Chặng Nhắc Chat, Xin Quyền & Nối Setupfully {#chang-nhac-cap-nhat}

@workflow id=wf-consent-update title="Chặng 2: Nhắc trong chat và cập nhật nối setupfully"
| chat_card | Thẻ user_markdown | frontend |
| consent | Lọc xác nhận chặt | security |
| stage_sync | Clone tạm + os.replace | backend |
| setup_chain | setupfully + verify | messagebus |
| chat_card > consent | Đồng ý hoặc hoãn |
| consent > stage_sync | Tránh khóa file exe |
| stage_sync > setup_chain | Hậu kiểm 6 tầng |

Khi có phiên bản cao hơn, lượt hỏi mới hiện một thẻ ngắn qua `user_markdown` và chống lặp nếu người dùng từ chối. Chỉ sau xác nhận rõ, bộ cài tải nhánh về thư mục tạm, sao lưu bản cũ, cập nhật an toàn trên Windows và nối tiếp `setupfully`.

## 3. Kết quả Kiểm chứng 4 Giả thuyết {#ket-qua-kiem-chung}

@workflow id=wf-hypothesis-matrix title="Tổng hợp kết quả kiểm chứng H1 đến H4"
| h1_hook | H1 Hook + Chat OK | backend |
| h2_probe | H2 Hai bước Git OK | external |
| h3_cli | H3 Lệch agy URL | security |
| h4_lock | H4 Khóa exe Windows | database |
| h1_hook > h2_probe | Giữ đủ 23 mã |
| h2_probe > h3_cli | plugin.json ở gốc |
| h3_cli > h4_lock | Staging thay URL |

Phép đo thực tế bác bỏ hai giả định ban đầu về vị trí tệp kê khai trên nhánh phát hành và cú pháp cài từ URL của lệnh dòng lệnh. Phương án staging cục bộ giúp kiểm soát khóa tệp và giữ nguyên trạng thái người dùng.
