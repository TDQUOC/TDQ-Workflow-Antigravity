# Phân tích chuyên sâu, Red-Team & Đề xuất Kiến trúc `work_kind=investigate` (Thuần `docs`) {#tong-quan}

@meta locale=en

So sánh hiện trạng luồng Research/Phân tích/Debug của TDQ Workflow với quy trình thực thi điều tra 2 vòng + Red-Team 3 chiều (không sửa mã nguồn) để xuất Đề xuất Kiến trúc Hoàn chỉnh V2.

## 1. Hiện trạng: Tiền-Implement Phình To & Rủi Ro Mất Data Khi `/compact` {#truoc-cap-nhat}

@workflow id=wf-before title="Trước cập nhật: Analyze làm hết việc, Implement rỗng 0s và thiếu kho chống compact"
| intake_old | Chỉ có luồng build | external |
| analyze_old | Ép B1 sâu + B2 + RCA | backend |
| impl_old | Chép lại báo cáo / 0s | messagebus |
| qc_old | Ép tron-bo 4563 tests | security |
| intake_old > analyze_old | 64.7% thời gian tiền-impl |
| analyze_old > impl_old | READONLY chặn explorer/debugger |
| impl_old > qc_old | Mất dữ kiện khi /compact |

Trên 30 request gần nhất, tiền-implement chiếm `64.7%` tổng thời gian; task research/audit `quick` tốn `99.6%–99.7%` ở `analyze` rồi `implement` rỗng `0s`.

## 2. Cách Thực Thi Request Này (Wave 1–2): Collect Đa Chiều & Đề Xuất V1 {#vong-1-collect}

@workflow id=wf-vong1 title="Wave 1-2 trong Implement: 3 nhánh điều tra song song -> evidence-log.md -> Đề xuất V1"
| exp_data | Thực nghiệm 173 requests | external |
| aud_code | Kiểm toán Codebase 3 tầng | backend |
| res_deep | Research ngoài nâng cao | messagebus |
| prop_v1 | evidence-log + Đề xuất V1 | security |
| exp_data > prop_v1 | Ghi EV-xxx định lượng |
| aud_code > prop_v1 | Khóa path:line & token |
| res_deep > prop_v1 | Compact & F6 patterns |

Toàn bộ hoạt động điều tra sâu chạy trong `implement` (thuần `docs`, `0` tệp mã nguồn bị sửa) và ghi checkpoint liên tục vào `evidence-log.md`.

## 3. Phản Biện Độc Lập (Wave 3): Red-Team 3 Chiều A · B · C {#vong-2-redteam}

@workflow id=wf-redteam title="Wave 3 trong Implement: Red-Team A (Compact/Token), B (Bảo mật/Lint), C (4 ca thật)"
| v1_in | Bản Đề Xuất V1 | backend |
| rt_a | Red-Team A: Compact/Token | external |
| rt_b | Red-Team B: Bảo mật/Lint | security |
| rt_c | Red-Team C: 4 ca thật | messagebus |
| v1_in > rt_a | Soi compact nhiều lần |
| v1_in > rt_b | Soi traversal & token-budget |
| v1_in > rt_c | Stress-test quick/full/RCA |

Ba luồng phản biện độc lập tấn công V1 từ 3 góc độ khác nhau và ghi mọi nhược điểm định danh `ND-1..ND-k` kèm bằng chứng vào `evidence-log.md`.

## 4. Hội Tụ V2, QC Bằng Chứng & Báo Cáo Trực Quan (Zero-Code-Touch) {#v2-qc-report}

@workflow id=wf-v2-qc title="Wave 4 -> QC -> Report: Vá 100% ND-*, kiểm FActScore/F6 và xuất Báo cáo V2"
| nd_list | Mã nhược điểm ND-* | messagebus |
| prop_v2 | Đề xuất Kiến trúc V2 | backend |
| qc_ev | QC FActScore + F6 + 0 code | security |
| rep_v2 | Report MD + Archify HTML | external |
| nd_list > prop_v2 | Truy vết vá 100% ND-* |
| prop_v2 > qc_ev | Xác minh path:line trên đĩa |
| qc_ev > rep_v2 | Tailscale HTTP 200 |

Người dùng nhận Báo cáo Đề xuất Kiến trúc Hoàn chỉnh V2 đã qua phản biện Red-Team & QC bằng chứng trước khi quyết định mở request code riêng.
