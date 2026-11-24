# Trước vs Sau — Nâng cấp Archify Drill-Down Đa tầng & Logic Node Registry {#truoc-sau}
@meta locale=en

Đặc tả kiến trúc chuyển đổi Archify từ sơ đồ một tầng phẳng sang hệ thống lát cắt nhiều tầng có kho Logic Node băm bằng tree-sitter và vỏ tải lười. Toàn bộ engine gốc giữ nguyên không fork.

## 1. Luồng Đồng bộ Master Map (Trước vs Sau) {#luong-dong-bo}

@workflow id=wf-sync-before title="Trước: Băm toàn tệp và render lại tất cả"
| m_flat | Model 1 tầng | database |
| h_file | Băm 5804 file | backend |
| r_all | Render lại cả 6 | external |
| h_big | Index 2.62 MB | security |
| m_flat > h_file | Đổi nhỏ bẩn hết |
| h_file > r_all | Mất 20.3 giây |
| r_all > h_big | 4/6 view bị tràn |

Mô hình phẳng hiện tại quét cả thư mục build Rust và nhúng lặp sáu bản runtime nén. Chỉ cần thay đổi một dòng không liên quan cũng kích hoạt dựng lại toàn bộ.

@workflow id=wf-sync-after title="Sau: Hash AST tree-sitter và Incremental"
| ts_ast | Tree-sitter AST | backend |
| reg_db | Kho Logic Node | database |
| slice_d | Chỉ vẽ D lát bẩn | external |
| portal | Vỏ nhẹ <300KB | frontend |
| ts_ast > reg_db | Dịch dòng 0 bẩn |
| reg_db > slice_d | Giữ nguyên gốc |
| slice_d > portal | Lazy HTTP & file |

Bộ phân tích cây cú pháp bỏ qua comment và vị trí dòng tuyệt đối để tránh bẩn nhầm. Hệ thống chỉ dựng lại đúng lát cắt có thân hàm thay đổi rồi đẩy vào vỏ điều hướng chung.

## 2. Trải nghiệm Bấm Xem & Tích hợp Setup {#trai-nghiem-va-setup}

@workflow id=wf-ui-before title="Trước: Modal tĩnh một tầng và thiếu parser"
| click1 | Bấm thẻ luồng | frontend |
| modal1 | Modal 1 cấp tĩnh | backend |
| no_ts | Chưa cài parser | security |
| click1 > modal1 | Không mở tầng con |
| modal1 > no_ts | Không tái dùng node |

Người đọc chỉ phóng to được một sơ đồ tĩnh mà không đào sâu xuống logic bên trong từng bước. Môi trường cài đặt cũng chưa tự kiểm tra phụ thuộc phân tích cú pháp.

@workflow id=wf-ui-after title="Sau: Drill-down 4+ tầng và Setup đủ gói"
| click_n | Bấm data-node-id | frontend |
| drawer | Giải thích + Mini | backend |
| bread | Breadcrumb & Neo | database |
| setup_ts | Setup tree-sitter | security |
| click_n > drawer | Sâu 4+ tầng thật |
| drawer > bread | Chặn vòng lặp |
| bread > setup_ts | Đủ 5 gói tự động |

Lớp vỏ lắng nghe sự kiện ngoài SVG để mở giải thích tự nhiên, sơ đồ con và thanh quay ngược an toàn. Bộ cài đặt tự kiểm tra năm gói tree-sitter và hỗ trợ cả lệnh serve cục bộ.
