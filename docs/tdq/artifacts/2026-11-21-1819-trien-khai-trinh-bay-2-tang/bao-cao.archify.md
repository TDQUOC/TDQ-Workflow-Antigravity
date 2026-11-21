# Báo cáo Triển khai Kiến trúc Trình bày 2 Tầng v0.105.0 {#bao-cao}

Báo cáo tổng kết `5` module nâng cấp từ điều tra sang cơ chế mặc định trên TDQ-Workflow. Toàn bộ đầu ra tách rõ Lớp 1 dễ hiểu ở phần đầu, Lớp 2 lưu bằng chứng đầy đủ phía sau, kèm trang web tiếng Việt sạch ký tự Trung.

## 1. Luồng Trình bày 2 Tầng và Kết quả Kiểm chứng {#luong-hai-tang}

@workflow id=wf-two-tier title="Chuyển đổi đầu ra TDQ sang chuẩn hai tầng"
| b_wall | Tường dấu chấm và bọc số | external |
| b_blind | Thiếu thẻ nhắc và lint Lớp 1 | messagebus |
| a_front | Mặt tiền 10 giây dễ nắm | backend |
| a_obd | Bằng chứng và lệnh ở Lớp 2 | security |
| b_wall > b_blind | Mở đầu dày 28 ký hiệu / 100 từ |
| a_front > a_obd | Sạch R16 trên 437 tệp |

Thước đo đọc nhanh giới hạn mặt tiền không vượt `120` từ và `6` cặp backtick mỗi `100` từ. Mọi số liệu chi tiết, nhật ký thời gian và biên bản kiểm thử nằm ở phần dưới tài liệu Markdown.

## 2. Cơ chế Nhắc lúc viết `[TDQ:PLAIN]` và Bộ kiểm tra `R16` {#plain-va-r16}

@workflow id=wf-plain-r16 title="Vận hành hook nhắc và cổng kiểm đọc tài liệu"
| phase_hook | Hook đọc pha hiện tại | external |
| plain_hint | Chèn thẻ TDQ PLAIN 23 mã | messagebus |
| r16_lint | Cổng R16 chặn tệp từ mốc | backend |
| clean_doc | Tài liệu đạt chuẩn qua cổng | security |
| phase_hook > plain_hint | Nhắc dưới 240 ký tự lúc viết |
| r16_lint > clean_doc | 4700 test nền pass sạch |

Cổng kiểm tra mới chỉ kích hoạt trên tài liệu sinh từ mốc hiện tại trở đi để toàn bộ kho tài liệu cũ vẫn giữ ổn định. Cả hai môi trường Claude Code và Antigravity dùng chung tập `23` mã qua bộ test đối xứng Rust và Python.

## 3. Việt hóa Trang Web Archify HTML và Nghiệm thu Thực tế {#archify-vi-qc}

@workflow id=wf-archify-report title="Chuỗi dựng và khóa chữ ký báo cáo HTML tiếng Việt"
| read_lang | Đọc doc_lang từ state | external |
| render_safe | Bơm locale en tránh mặc định | messagebus |
| vi_pack | Dịch giao diện và Nhánh SVG | backend |
| lock_sha | Khóa manifest kiểm HTTP 200 | security |
| read_lang > render_safe | Không đụng công cụ gốc ngoài |
| vi_pack > lock_sha | Diệt sạch nhãn Trung trong gzip |

Quá trình Việt hóa xử lý cả DOM ngoài trang, từ điển JSON của trình đọc, và payload `htmlGzip` giải nén bên trong nút mở sơ đồ tương tác. Sau đó bước đóng dấu manifest bảo đảm trang HTML gắn khớp tài liệu báo cáo gốc.
