# Trước/Sau — Kiến trúc Hook Hybrid 2 tầng + Smart Hardening {#tong-quan}

@meta locale=en

Đặc tả chuẩn hóa đường chạy hai tầng giữa Rust và Python để đạt đủ 22 mã cổng. Đồng thời hệ thống giữ tốc độ đường nóng dưới 28 ms và bảo vệ gói đa nền tảng.

## Trước: Thiếu cổng, Lệch Sổ và Đè Binary {#truoc}

@workflow id=hybrid-spec-truoc title="Hiện trạng: Bỏ PreInv, Lệch .tdq-runtime và Đè .exe"
| agy_ev | AGY Event | external |
| rs_gap | Rust thiếu | security |
| rt_two | 2 .tdq-rt | messagebus |
| exe_ow | Đè PE .exe | backend |
| agy_ev > rs_gap | Bỏ PreInv |
| rs_gap > rt_two | Lệch 14 mã |
| rt_two > exe_ow | Phá Linux |

Ở `v0.101.0`, `main.rs` bỏ rơi `PreInvocation` và `PostInvocation` về `allow()`. Rust dùng `.tdq-runtime` lệch với `docs/tdq/.tdq-runtime` của Python. Ngoài ra, `build_agy_plugin.py` đang chép đè `.exe` Windows lên bản Linux và macOS.

## Sau: Kiến trúc Hybrid 2 tầng qua `PLUGIN_ROOT` {#sau}

@workflow id=hybrid-spec-sau title="Thiết kế mới: Rust Hot-path 91% + Python Cold-path 9%"
| ev_v2 | AGY 2.0 | external |
| router | Rust Router | messagebus |
| hot_rs | Hot 91% | backend |
| cold_p | Cold 9% | security |
| ev_v2 > router | Schema v2 |
| router > hot_rs | Dưới 28 ms |
| router > cold_p | PLUGIN_ROOT |

Router Rust đọc chuẩn schema AGY 2.0 gồm `injectSteps`, `reason`, `toolCall` và `workspacePaths`. Nhánh `Hot-path` chạy thuần Rust dưới 28 ms trên cùng sổ `docs/tdq/.tdq-runtime/`. Nhánh `Cold-path` định tuyến về `dispatch.py` qua `PLUGIN_ROOT` và vị trí binary.

## Kiểm soát: Smart Hardening, 3 OS & Parity 22 Mã {#hardening}

@workflow id=hybrid-spec-hardening title="6 Quy tắc Cứng + Magic Bytes 3 OS + Parity 22 Mã"
| smart6 | 6 Smart Gate | security |
| magic3 | Guard 3 OS | messagebus |
| par22 | Parity 22 | backend |
| qc_u | QC Ultra | external |
| smart6 > magic3 | TICK, LOG |
| magic3 > par22 | ELF/MachO |
| par22 > qc_u | Khớp 100% |

Sáu quy tắc Smart Hardening siết lại `TICK` (ngưỡng `8`), `LOG`, `continuationActive`, `SEARCH` và `qc-tester`. Bộ bảo vệ magic bytes xác thực PE, ELF và Mach-O cho cả 3 hệ điều hành. Bộ Parity Test khóa khớp 22 mã cổng qua 6 sự kiện trước QC mức `ultra`.
