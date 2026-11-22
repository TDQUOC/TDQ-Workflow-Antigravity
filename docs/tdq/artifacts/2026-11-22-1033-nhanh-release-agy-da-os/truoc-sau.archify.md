# Thiết kế Trước và Sau: Nhánh Release Antigravity Đa Hệ Điều Hành {#truoc-sau-release-agy}

Cấu hình plugin chuyển sang bộ khởi chạy Node đa nền tảng. Kho mã xuất bản nhánh release sạch riêng cho Antigravity.

## 1. Hiện trạng (Trước) — Cài từ GitHub bị lỗi ngoài máy cá nhân {#hien-trang-truoc}

@workflow id=wf-truoc-release title="Hiện trạng cài plugin từ GitHub trên máy khác"
| gh_old | origin dev cũ | external |
| cfg_win | mcp cứng admin | security |
| hk_exe | hook cứng .exe | security |
| err_os | Lỗi đa OS | backend |
| gh_old > cfg_win | Tụt 27 commit |
| gh_old > hk_exe | Cứng Windows |
| cfg_win > err_os | Lỗi npx.cmd |
| hk_exe > err_os | Hỏng Mac/Linux |

Hiện `tools/patches/agy_manifests.py` đọc trực tiếp `~/.claude.json` và `os.name`, còn `scripts/build_portable.py` chỉ xuất bản nhánh `main` cho Claude Code.

## 2. Thiết kế mới (Sau) — Nhánh release/antigravity và launcher đa OS {#thiet-ke-sau}

@workflow id=wf-sau-release title="Luồng phát hành và cài đặt đa nền tảng sau nâng cấp"
| dev_src | Nhánh dev sạch | backend |
| rel_br | release/antigravity | messagebus |
| agy_in | agy install | external |
| run_hk | hook launcher | security |
| run_mcp | mcp launcher | database |
| dev_src > rel_br | Git plumbing |
| rel_br > agy_in | Gốc plugin.json |
| agy_in > run_hk | Rust hay Python |
| agy_in > run_mcp | Auto-detect OS |

Nhánh `release/antigravity` đặt trực tiếp gói `tdq-workflow-agy` ở thư mục gốc và giữ nguyên nhánh `main` cho Claude Code. Cả hai launcher dùng thuần Node.js nên chạy đồng nhất trên Windows, macOS và Linux.
