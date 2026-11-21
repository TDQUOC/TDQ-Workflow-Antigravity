# Đề xuất Nâng cấp Mặc định Trình bày 2 Tầng cho TDQ-Workflow {#bao-cao}

@meta locale=en

Bản thiết kế chuyển kết quả điều tra thành cơ chế mặc định. Gồm quy chuẩn đầu tệp, thẻ nhắc lúc viết, kiểm tự động và trang web tiếng Việt.

## 1. Luồng soạn Chat và Tài liệu Markdown {#luong-chat-md}

@workflow id=wf-chat-md title="So sánh trước và sau khi tách hai lớp"
| b_rule | Luật nằm cuối, ép bọc số | external |
| b_draft | Cho dán báo cáo dài ra chat | messagebus |
| a_top | Đưa trần Lớp 1 lên đầu | backend |
| a_tpl | Bỏ dán thô, thống nhất nhãn | security |
| b_rule > b_draft | Mở đầu 28 ký hiệu / 100 từ |
| a_top > a_tpl | Giảm gần 80% ký hiệu thừa |

Số đo và đường dẫn lùi xuống nửa sau tài liệu để đối chiếu. Phần mở đầu chỉ giữ ý chính dễ đọc.

## 2. Cơ chế Nhắc lúc viết và Kiểm tra tự động `R16` {#hook-va-lint}

@workflow id=wf-hook-lint title="Trước và sau khi có thẻ nhắc và kiểm tự động"
| old_none | Thiếu nhắc ở pha viết | external |
| old_blind | Lint bỏ qua tài liệu đầu ra | messagebus |
| new_hook | Thẻ TDQ PLAIN nhắc lúc viết | backend |
| new_lint | Luật R16 chặn từ mốc hôm nay | security |
| old_none > old_blind | Lọt lỗi nhồi thuật ngữ mới |
| new_hook > new_lint | Khóa chất lượng không vỡ cũ |

Ngưỡng đặt tại điểm xuất giúp vượt qua giới hạn 3.500 token mỗi tệp khuôn mẫu.

## 3. Việt hóa Giao diện Trang Web Archify HTML {#viet-hoa-html}

@workflow id=wf-archify-vi title="Trước và sau khi Việt hóa thanh công cụ web"
| html_old | Thiếu gói Việt, dễ ra Trung | external |
| html_en | Hoặc cố định thanh tiếng Anh | messagebus |
| html_new | Dịch thanh công cụ sang Việt | backend |
| html_verify | Đóng dấu trước băm manifest | security |
| html_old > html_en | Giữ nguyên công cụ gốc ngoài |
| html_new > html_verify | Mở trình duyệt 0 lỗi hiển thị |

Bản dịch được chèn trước bước băm chữ ký nên quá trình xác thực tài liệu vẫn đạt toàn vẹn.
