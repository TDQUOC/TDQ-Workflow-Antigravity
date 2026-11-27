# Thiết kế Trước và Sau Nâng cấp Phát hành v0.108.0 {#truoc-sau-v0108}

@meta locale=en

Bản vẽ tổng quan luồng nâng cấp phiên bản `0.108.0`, đồng bộ tài liệu/Master Map và xuất bản đa nhánh sau 3 pha `P0`–`P2`.

## 1. Đồng bộ Phiên bản, Rust Binary và Tài liệu trên `dev` {#sync-version-dev}

@workflow id=v0108-dev-before title="Trước: Nền dev@42467fe9 mang 3 pha mới nhưng metadata còn 0.107.0"
| hosts | Manifest Claude/Codex/AGY còn 0.107.0 | cloud |
| rust | Cargo.toml còn 0.105.0 từ đợt trước | backend |
| docs | CHANGELOG chưa có P0-P2 và README ghi 4602 | database |
| map | Master Map stale vì 24 thay đổi P0-P2 | security |
| hosts > rust | |
| rust > docs | |
| docs > map | |

Code 3 pha P0–P2 đã qua QC và hợp nhất trên nhánh `dev`, nhưng nhãn phiên bản, `CHANGELOG.md`, badge README và Master Map chưa được chốt đồng bộ.

@workflow id=v0108-dev-after title="Sau: Đồng nhất 0.108.0 đa host, Rust release mới và Master Map current"
| bump | Đồng bộ 0.108.0 ở host và Cargo.toml | cloud |
| rustbuild | cargo test và cargo build --release ra exe mới | backend |
| agybuild | build_agy_plugin dựng plugins/tdq-workflow-agy | database |
| syncdoc | CHANGELOG, README 5012 và sync-master current | security |
| bump > rustbuild | |
| rustbuild > agybuild | |
| agybuild > syncdoc | |

Tất cả điểm khai báo từ root plugin tới gói Antigravity và binary `tdq-dispatch.exe` thống nhất mốc `0.108.0`, kèm kiểm thử toàn kho xác nhận trước khi hợp nhất.

## 2. Xuất bản Nhánh Sạch, Cài Cục bộ và Đẩy Remote GitHub {#release-and-push}

@workflow id=v0108-push-before title="Trước: Nhánh dev đi trước origin 73 commit, bản release còn v0.107.0"
| localdev | dev local đi trước origin 73 commit | backend |
| oldmain | main và release/antigravity đang dừng ở 0.107.0 | cloud |
| localagy | Máy local còn lệch phiên bản cũ | external |
| localdev > oldmain | |
| oldmain > localagy | |

Trên GitHub `origin`, cả `dev`, `main` và `release/antigravity` đều đang dừng ở mốc `0.107.0`, còn thư mục cài đặt cục bộ chưa nhận gói `0.108.0`.

@workflow id=v0108-push-after title="Sau: Hợp nhất dev, sinh main + release/antigravity, tag v0.108.0 và push"
| mergedev | Merge chore về dev và giữ working tree sạch | backend |
| buildbranch | Sinh main và release/antigravity bằng build_portable | cloud |
| installlocal | Cài đặt 0.108.0 vào ~/.gemini/config/plugins | external |
| pushorigin | Tag v0.108.0 trên main và push đủ lên origin | security |
| mergedev > buildbranch | |
| buildbranch > installlocal | |
| installlocal > pushorigin | |

Nhánh `main` phục vụ Claude Code, nhánh `release/antigravity` phục vụ cài đặt một lệnh Antigravity và tag `v0.108.0` được đẩy đồng bộ lên `origin`.
