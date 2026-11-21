# Thiết kế mặc định Trình bày Trực quan, Dễ hiểu cho TDQ-Workflow {#bao-cao}

Khi tách phần tóm tắt lợi ích cho người đọc khỏi chi tiết kỹ thuật bên dưới, tin nhắn chat ngắn đi gần 40 phần trăm. Lượng ký hiệu code thừa cũng giảm gần 80 phần trăm mà vẫn giữ đủ bằng chứng kiểm chứng.

## 1. Vì sao báo cáo và chat vẫn dày thuật ngữ sau đợt sửa trước {#nguyen-nhan-goc}

@workflow id=wf-root-cause title="Bốn điểm nghẽn kéo ký hiệu kỹ thuật lên mặt tiền"
| old_rule | Luật dễ hiểu nằm cuối tệp tham chiếu | external |
| old_wrap | Quy tắc ép bọc code quanh mọi con số | backend |
| old_copy | Viết nhật ký kỹ thuật trước rồi chép ra chat | messagebus |
| old_blind | Bộ kiểm tự động bỏ qua đầu ra báo cáo | security |
| old_relapse | Báo cáo dài và dày 27 ký hiệu mỗi trăm từ | external |
| old_rule > old_wrap | Đọc thiếu 50 dòng đầu là bỏ sót văn phong |
| old_wrap > old_copy | Cho phép dán nguyên báo cáo dài ra chat |
| old_copy > old_blind | Không có hook nhắc hay ngưỡng số chặn |
| old_blind > old_relapse | Người dùng phải nhắc giải thích lại 5 lần |

Bốn yếu tố cộng hưởng khiến tác nhân luôn quay về thói quen liệt kê tên hàm và đường dẫn ngay ở những dòng đầu tiên.

## 2. Kiến trúc mặc định 2 tầng và Sáu chốt giữ văn phong mới {#kien-truc-2-tang}

@workflow id=wf-two-tier title="Mô hình Mặt tiền cho người đọc tách khỏi Cổng chứng cứ kỹ thuật"
| new_top | Đưa trần số dễ đọc lên 40 dòng đầu | external |
| new_hook | Hook nhắc ngắn gọn ngay trước lúc viết | messagebus |
| new_layer1 | Lớp 1 Mặt tiền chỉ nêu giá trị 15 giây | backend |
| new_layer2 | Lớp 2 giữ 100 phần trăm mã bằng chứng | security |
| new_lint | Kiểm tự động mật độ ký hiệu khi duyệt | security |
| new_top > new_hook | Bỏ quy tắc bọc code quanh con số |
| new_hook > new_layer1 | Cấm chép nhật ký kỹ thuật lên đầu |
| new_layer1 > new_layer2 | Đầy đủ dòng tệp và kết quả cho QC |
| new_layer2 > new_lint | Khóa chất lượng mà không vượt trần token |

Cơ chế mới tận dụng độ chú ý ở cuối ngữ cảnh trước khi viết chữ. Toàn bộ gói hướng dẫn vẫn giữ nguyên trần 3.500 token và không mất dữ liệu đối chiếu.

## 3. Áp dụng đồng bộ Trước và Sau trên cả 3 bề mặt hiển thị {#lo-trinh-3-be-mat}

@workflow id=wf-surfaces title="Thay đổi cụ thể trên Chat, Tài liệu Markdown và Web trực quan"
| surf_chat | Chat ngắn 8 đến 16 dòng lợi ích | external |
| surf_md | Hợp nhất một khung Tóm tắt dễ hiểu | backend |
| surf_html | Trang web dùng tiếng Việt dễ nắm bắt | messagebus |
| surf_out | Giảm 79 phần trăm ký hiệu kỹ thuật thừa | security |
| surf_chat > surf_md | Dưới 6 ký hiệu code mỗi trăm từ mở đầu |
| surf_md > surf_html | Thống nhất nhãn ở Spec, Plan và Report |
| surf_html > surf_out | Người đọc hiểu ngay trong 10 đến 15 giây |

Thay vì viết dài thêm quy tắc khuyên nhủ, toàn bộ Chat, tài liệu và Web trực quan cùng tuân thủ ranh giới giữa lớp đọc nhanh và lớp tra cứu sâu.
