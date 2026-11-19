# Báo cáo Nghiệm thu — Kiến trúc Hook Hybrid 2 tầng + Smart Hardening {#tong-quan}

@meta locale=en

Kiến trúc điều phối hook Antigravity 2.0 kết hợp tuyến Hot-path thuần Rust (91% lưu lượng, 25.85 ms qua cmd /c), tuyến Cold-path Python 3.9+ qua PLUGIN_ROOT (9%) cùng Smart Hardening 6 quy tắc và 3 nhị phân native kiểm chứng magic bytes.

## 1. Trước request: Lỗi giao thức & Độ trễ khởi tạo {#truoc-request}

@workflow id=report-hybrid-truoc title="Hiện trạng v0.101.0: Thiếu PreInv, Lệch Sổ và Python 3.9"
| agy2 | AGY 2.0 Host | external |
| miss | Bỏ Pre/PostInv | security |
| split_rt | 2 .tdq-runtime | messagebus |
| py39 | macOS Py3.9 Lỗi | backend |
| agy2 > miss | Schema lệch |
| miss > split_rt | Hở cổng TICK/LOG |
| split_rt > py39 | Đứt Cold-path |

Phiên bản trước còn thiếu khóa giao thức `injectSteps` cho `PreInvocation`/`PostInvocation`, dùng lệch `.tdq-runtime`, nới lỏng quá tay một số quy tắc (`TICK`, `LOG`, `UNFINISHED`), có rủi ro ghi đè nhầm binary khi đóng gói và lỗi annotation `X | Y` trên Apple Python `3.9.6`.

## 2. Sau request: Hybrid 2 tầng + Smart Hardening 6 Quy tắc {#sau-request}

@workflow id=report-hybrid-sau title="Kiến trúc mới: Hot-path Rust 91% + Cold-path Python 9%"
| ev | 6 Sự kiện AGY | external |
| hot | Hot Rust 91% | backend |
| cold | Cold Python 9% | messagebus |
| guard | Smart + 3OS Guard | security |
| ev > hot | 17.01ms Direct |
| ev > cold | PLUGIN_ROOT |
| hot > guard | 22 Mã Cổng |
| cold > guard | Py3.9 Annotations |

Router Rust đọc chuẩn 6 sự kiện, chia sẻ chung sổ `docs/tdq/.tdq-runtime/` qua sidecar `File::try_lock()`, giữ `Hot-path` dưới 26 ms và chuyển `Cold-path` về `dispatch.py`. Sáu quy tắc Smart Hardening siết kỷ luật `TICK` (ngưỡng 8), `LOG`, `UNFINISHED`, `SEARCH`, `GON`, `qc-tester` kèm guard magic bytes 3 hệ điều hành.

## 3. Đã test gì: Từ Unit Rust tới Live 3 Hệ điều hành {#da-test-gi}

@workflow id=report-hybrid-kiem-thu title="Chuỗi kiểm chứng QC Ultra 5 Tầng"
| unit | Cargo + Clippy | backend |
| parity | Parity 22x6 & R1-R3 | messagebus |
| bench | Benchmark Solo N=30 | backend |
| cross | Win + Ubuntu + Mac | external |
| full | Tron-bo 215 Module | security |
| unit > parity | 27 Cargo Tests |
| parity > bench | 57 Pytest Cases |
| bench > cross | Magic PE/ELF/MachO |
| cross > full | Subagent tdq-qc-tester |

Hệ thống kiểm tra từ tầng crate Rust (`cargo fmt`/`clippy`/`test`), Golden Parity `22/22` mã × `6` sự kiện, đo hiệu năng solo `N=30`, strict validator (`agy plugin validate`), smoke SSH thực tế trên `ubuntu-100-95` và `mbair`, đến trọn bộ `215` module qua `tdq_test.py tron-bo` và thẩm định đọc-chỉ `tdq-qc-tester`.

## 4. Kết quả test: 4,422 Passed & Tăng tốc 7.8x {#ket-qua-test}

@workflow id=report-hybrid-ket-qua title="Kết quả Nghiệm thu: Đạt 100% DoD Q1–Q8"
| perf | Weighted 33.65ms | backend |
| suite | 4,422/4,458 Pass | security |
| bin3 | PE + ELF + MachO | messagebus |
| qct | tdq-qc-tester PASS | external |
| perf > suite | 7.8x vs Python |
| suite > bin3 | 0 Failed / 36 Skip |
| bin3 > qct | Local Plugin Giữ |

`Hot Combined Direct` đạt `17.01 ms`, `cmd /c` `25.85 ms`, lõi Rust `7.98 ms`, trung bình trọng số `33.65 ms` (nhanh `7.8x`). Trọn bộ `tdq_test.py tron-bo` đạt `4,422 passed, 36 skipped, 0 failed`; cả 3 nhị phân PE/ELF/MachO (`1.91 MB`/`2.27 MB`/`1.81 MB`) đều vượt `8/8` smoke, `agy validate` 0 lỗi, SHA-256 local plugin nguyên vẹn.
