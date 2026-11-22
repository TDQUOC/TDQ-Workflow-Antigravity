# Báo cáo Nhánh Release Antigravity Đa Hệ Điều Hành {#bao-cao}

Gói Antigravity không còn đường dẫn cá nhân Windows và sẵn sàng cài trên máy khác từ nhánh phát hành riêng.

## 1. Luồng cài đặt và thực thi trước với sau nâng cấp {#truoc-va-sau-release}

@workflow id=wf-release-flow title="Chuyển đổi sang nhánh release sạch và launcher đa nền tảng"
| dev_bld | Biên dịch gói dev | backend |
| rel_agy | Nhánh release riêng | messagebus |
| agy_get | Máy khác cài agy | external |
| hk_node | Hook launcher Node | security |
| mcp_node | MCP launcher Node | database |
| dev_bld > rel_agy | Git plumbing |
| rel_agy > agy_get | Gốc plugin.json |
| agy_get > hk_node | Rust hay Python |
| agy_get > mcp_node | Auto-detect OS |

Nhánh `release/antigravity` tách riêng từ `dev` để giữ nguyên nhánh `main` của Claude Code và tự cấp quyền thực thi cho binary Rust đa OS.

## 2. Cơ chế dự phòng và kiểm chứng 3 hệ điều hành {#da-he-dieu-hanh}

@workflow id=wf-multi-os-runtime title="Thực thi đồng bộ Windows, Linux và macOS"
| win_bin | Win exe f1e7fcfb | frontend |
| unx_bin | Linux musl và Mac | backend |
| py_fb | Dự phòng Python | database |
| qc_ok | 4777 test xanh | security |
| win_bin > qc_ok | Cmd /c đạt |
| unx_bin > qc_ok | SSH test sống |
| py_fb > qc_ok | Bỏ stub Windows |

Cả hai bản Rust trên Ubuntu Linux và macOS Apple Silicon đều đã được biên dịch đồng bộ qua SSH và chạy kiểm chứng trực tiếp trước khi đóng gói.
