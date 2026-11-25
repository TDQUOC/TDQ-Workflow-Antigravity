# Bộ Development Plan 3 Pha Tích hợp Paperclip vào TDQ-Workflow (`P0`–`P2`) {#tong-quan}

@meta locale=en

Yêu cầu này hoàn tất khảo sát mã nguồn thật và lập bộ kế hoạch thi công chi tiết. Toàn bộ gồm bốn tài liệu cho ba pha nâng cấp và không sửa tệp mã nguồn sản phẩm nào.

- Thu thập đủ `26` bằng chứng dòng code từ Python, Rust và bộ đóng gói phát hành trên đĩa.
- Kiểm chứng `90` symbol neo thật, `11` khối JSON, `11` wave tách file và `32` cạnh phụ thuộc (`7/7` xanh).
- Đáp ứng trọn vẹn phương án đã chốt `1abcd 2a 3a 4a 5a` và `1c 2a 3a 4a 5c` cho Windows Antigravity cá nhân.
- Bảo toàn bất biến `docs/kien-truc.md`: `78` script đều không import ngược `hooks/`, giữ nguyên `schema_version=6` và `23` mã cổng AGY.

## 1. Pha `P0` — Lõi An toàn Runtime & Parity Rust (`1` Request Thống nhất) {#pha-p0}

@workflow id=p0-unified-feature title="P0: 4 Wave tách file nóng trong 1 Request Feature"
| w1 | P0-W1: Lease Lock + Config + lock.rs | backend |
| w2 | P0-W2: State v6 + Queue + Budget | backend |
| w3 | P0-W3: MCP Policy + Python/Rust Gate | security |
| w4 | P0-W4: Plugin Build + Parity + Full Verify | backend |
| w1 > w2 | |
| w2 > w3 | |
| w3 > w4 | |

Tất cả thay đổi lõi gom vào một request `feature` với bốn đợt nối tiếp không trùng tệp nóng. Chính sách MCP cân bằng mặc định chỉ chặn tool ghi mới và tái dụng mã cổng sẵn có để giữ tròn hai mươi ba mã AGY.

## 2. Pha `P1` — `4` `Domain Pack`, `KhoBM25` & Khóa Chống Hạ Cấp {#pha-p1}

@workflow id=p1-domain-bm25 title="P1: Đóng gói scripts/defaults/domains và Zero-Downgrade"
| json | 4 Domain JSON (ASCII) + tdq_domains | backend |
| bm25 | KhoBM25 + bỏ loại trừ skill_router | backend |
| lock | Zero-Downgrade: escalate-to-build + Rust | security |
| pack | Token <= 3500 + i18n + sinh-main | security |
| json > bm25 | |
| bm25 > lock | |
| lock > pack | |

Bốn gói lĩnh vực đặt trong `scripts/defaults/domains/` dùng từ khóa không dấu để vừa qua `i18n_check.py` vừa khớp tiếng Việt qua `bo_dau()`. Gỡ bỏ `skill_router.py` khỏi `RELEASE_EXCLUDE_SCRIPTS` giúp nhánh `main` và plugin Antigravity mang đủ bộ định tuyến kỹ năng.

## 3. Pha `P2` & Bộ Tự Kiểm `verify_plans.py` {#pha-p2-verify}

@workflow id=p2-bridge-verify title="P2 Tắt Mặc định & Máy Tự Kiểm Trước Khi Code"
| cli | P2-W1: tdq_paperclip_bridge (enabled=false) | external |
| mock | P2-W2: stdlib mock + APPROVED_RUNTIME_MODULES | backend |
| vp | verify_plans.py: 7/7 checks + TDQ_LOG=1/0 | security |
| qc | Ultra QC: tdq-qc-tester + Archify 200 | security |
| cli > mock | |
| mock > vp | |
| vp > qc | |

Cầu nối CLI một chiều ở `P2` mặc định tắt hoàn toàn cho người dùng Windows hằng ngày và giữ `state.json` làm chân lý duy nhất. Script `verify_plans.py` chạy tự kiểm đối chiếu cả ca lỗi giả lập và xuất `0B` stderr khi tắt log.
