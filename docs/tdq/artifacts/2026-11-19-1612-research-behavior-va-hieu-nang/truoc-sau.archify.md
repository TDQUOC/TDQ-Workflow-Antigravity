# Trước/Sau — Kiến trúc Hook giữ đúng Behavior và Hiệu năng {#tong-quan}

@meta locale=en

Phân tích thực nghiệm cho thấy hook chỉ chiếm 2,7% thời lượng lượt dài nhưng quyết định 100% kỷ luật TDQ. Kiến trúc Hybrid 2 tầng kết hợp Smart Hardening giữ tốc độ dưới 25 ms trên 90% đường nóng. Đồng thời hệ thống bảo toàn trọn vẹn 22 cổng hành vi qua đường lạnh Python.

## Trước: Đánh đổi cực đoan giữa Tốc độ và Kỷ luật {#truoc}

@workflow id=hook-res-truoc title="Hiện trạng: Python 126ms vs Rust thiếu cổng"
| py_core | Python 126ms | external |
| agy_soft | R1-R3 mềm | messagebus |
| rust_thin | Rust thiếu | security |
| drift | Lệch 14 cổng | backend |
| py_core > agy_soft | Nới gate |
| agy_soft > rust_thin | Bỏ PreInv |
| rust_thin > drift | Rơi behavior |

Gói Python AGY R1–R3 chịu độ trễ cao ở mọi lần gọi và hạ cấp nhiều cổng chặn. Sang v0.101.0, binary Rust chạy nhanh dưới 25 ms nhưng thiếu 14 cổng và bỏ rơi `PreInvocation`. Người dùng buộc phải đánh đổi giữa tốc độ thực thi và sự chính xác của workflow.

## Đề xuất: Kiến trúc Hybrid 2 tầng (Rust Router + Python Cold-Path) {#sau}

@workflow id=hook-res-sau title="Đề xuất: Rust xử lý 92% đường nóng, Python xử lý 8% ca lạnh"
| agy_hook | AGY Event | external |
| rust_rt | Rust Router | messagebus |
| hot_path | Hot 92% <25m | backend |
| cold_py | Cold 8% Py | security |
| agy_hook > rust_rt | Schema v2 |
| rust_rt > hot_path | Nhanh, đủ |
| rust_rt > cold_py | Ca phức tạp |

Rust đóng vai trò bộ định tuyến chuẩn Antigravity 2.0 cho mọi sự kiện. Hơn 90% tác vụ lặp dày (`PostToolUse`, `PostInvocation`, `PreInvocation` giữa lượt, `PreToolUse` cơ bản) chạy thuần Rust ở 20–28 ms. Các ca hiếm và phức tạp (`SessionStart`, `Stop` mở, `tdq_team`) tự động chuyển xuống `dispatch.py`.

## Kiểm soát kỷ luật: Smart Hardening & Golden Parity {#kiem-chung}

@workflow id=hook-res-kiemchung title="Siết Cổng Thông Minh + Chung Sổ + Parity Test 22 Mã"
| smart_g | Smart Gates | security |
| one_dir | 1 .tdq-rt | messagebus |
| parity | Parity 22 mã | backend |
| rollout | Lộ trình 3 | external |
| smart_g > one_dir | TICK, LOG |
| one_dir > parity | Chung ledger |
| parity > rollout | Khóa hồi quy |

Chính sách Smart Hardening khôi phục chặn cứng cho `TICK` (`0` hoặc `>1` `[~]`) và `LOG` (trừ staging). Toàn bộ dữ liệu phiên được hợp nhất vào một thư mục `docs/tdq/.tdq-runtime/`. Bộ test vi phân kiểm phủ đủ 22 mã cổng và 6 sự kiện ngăn sai lệch tái diễn.
