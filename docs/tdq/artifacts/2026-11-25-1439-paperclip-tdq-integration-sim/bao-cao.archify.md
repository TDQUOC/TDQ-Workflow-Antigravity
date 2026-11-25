# Có tích hợp được Paperclip vào TDQ-Workflow không? {#tong-quan}

@meta locale=en

Có thể tích hợp theo mô hình Pattern-Native cho lõi. Kỷ luật code TDQ giữ nguyên 100%, không kéo PostgreSQL nặng máy.

- Đối chiếu 27 bằng chứng mã nguồn thật từ Paperclip và TDQ-Workflow-Antigravity.
- Chạy thực nghiệm 6 kịch bản mô phỏng trong sandbox Python cô lập trên Windows.
- Toàn bộ 12 bất biến hành vi TDQ giữ nguyên 100% với độ trễ p95 chỉ 0.428 ms.
- Đề xuất lộ trình 3 pha từ ổn định lõi, mở rộng đa lĩnh vực đến add-on Docker tùy chọn.

## 1. Ổn định điều hành Phase và Task {#on-dinh-phase-task}

@workflow id=phase-task-stability title="P0: Bốn mảnh ghép ổn định bằng Python thuần"
| lease | Atomic Lock O_EXCL + TTL | backend |
| queue | 3-Tier Priority + blockedBy | backend |
| brake | Circuit Breaker 3 pha | backend |
| cap | Budget hard_stop $5 | security |
| lease > queue | |
| queue > brake | |
| brake > cap | |

Mô phỏng SIM-1 đến SIM-3 giảm tranh chấp ghi đè từ 61 xuống 0 và thu hồi toàn bộ task treo. Cơ chế aging đưa task cũ lên lượt 4 và chặn vượt ngân sách.

## 2. Mở rộng đa lĩnh vực giữ kỷ luật code {#da-linh-vuc}

@workflow id=multi-domain-packs title="P1: Domain Pack tách rạch ròi Code và Phi-code"
| router | BM25 Router (8/8) | external |
| code | Code Build (QC-F1..F4) | backend |
| noncode | Research, BA, Ops | backend |
| guard | Khóa Zero-Downgrade | security |
| router > code | |
| code > noncode | |
| noncode > guard | |

Nhánh Code Build giữ nguyên toàn bộ LSP, TCAS AST và Red-Green trong khi ba nhánh phi-code dùng tiêu chí kiểm riêng.

## 3. Lộ trình tích hợp tối ưu ba pha {#lo-trinh-toi-uu}

@workflow id=three-phase-roadmap title="Pattern-Native làm lõi và Hybrid Bridge tùy chọn"
| p0 | P0: Lock, Brake, MCP | backend |
| p1 | P1: 4 Domain Packs | backend |
| p2 | P2: Bridge Docker/WSL2 | external |
| ban | Cấm: PG nhúng, same-origin | security |
| p0 > p1 | |
| p1 > p2 | |
| p2 > ban | |

Trên Windows và Antigravity, hướng Pattern-Native đạt 0 dependency mới nên thắng tuyệt đối làm lõi cho P0 và P1.
