# Báo cáo Cơ chế GitHub Marketplace, Auto-Update và Mức sẵn sàng của Repo trên Antigravity {#bao-cao}

Antigravity chỉ tự cập nhật plugin từ kho chính hãng, còn plugin cài từ URL GitHub chỉ là bản sao tĩnh và kho hiện tại cần sửa cấu hình đa hệ điều hành trước khi phát hành cộng đồng.

## 1. Luồng cài từ GitHub URL so với Official Marketplace {#git-vs-marketplace-update}

@workflow id=wf-agy-git-lifecycle title="Khác biệt lưu nguồn và cập nhật giữa GitHub URL với Marketplace"
| g_url | URL GitHub hay subpath | external |
| g_tmp | Clone nông, chép tĩnh | backend |
| g_cfg | Mất URL trong config | database |
| g_end | Phải cài tay để update | security |
| m_off | Official Marketplace | messagebus |
| m_auto | Lưu version, auto-update | security |
| g_url > g_tmp | Xóa gốc .git |
| g_tmp > g_cfg | Chỉ lưu name |
| g_cfg > g_end | Thiếu lệnh update |
| m_off > m_auto | Qua gstatic zip |

Thực nghiệm cách ly chứng minh chỉ plugin từ kho chính hãng mới có trường `installedFrom` để tự động so khớp phiên bản mới khi khởi động.

## 2. Sáu khoảng trống khi đưa repo lên GitHub cộng đồng đa OS {#repo-readiness-gaps}

@workflow id=wf-repo-readiness-gaps title="Chuỗi lỗi cản trở phát hành GitHub đa hệ điều hành"
| p_ok | plugin.json chuẩn gốc | messagebus |
| p_mcp | mcp_config cứng admin | security |
| p_hk | hooks.json cứng .exe | security |
| p_git | main thiếu plugins/ | security |
| p_fix | Khử path cứng và sync | backend |
| p_ok > p_mcp | Lỗi ngoài máy admin |
| p_mcp > p_hk | Lỗi trên Mac/Linux |
| p_hk > p_git | Root tải nhầm Claude |
| p_git > p_fix | Sẵn sàng đa OS |

Khử đường dẫn cá nhân Windows, thay hook bằng wrapper đa nền tảng trong `scripts/` và đồng bộ nhánh phát hành là các bước ưu tiên đầu tiên.
