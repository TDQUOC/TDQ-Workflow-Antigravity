# Trước/Sau — Phân tích sai sót behavior TDQ Workflow khi nới hook & Lộ trình cân bằng {#tong-quan}

@meta locale=en

Hiện trạng Audit: Sau 2 đợt nâng cấp `v0.100.0` (R1–R3 mềm hóa gate trên Antigravity) và `v0.101.0` (đóng gói native Rust binary `tdq-dispatch`), độ trễ hook giảm mạnh nhưng hệ thống phát sinh 10 hạn chế nghiêm trọng gây sai lệch hành vi (Behavior Drift), điển hình là bỏ sót không tick checkbox plan, bỏ qua `PreInvocation`/`PostInvocation` trên Rust và phân mảnh thư mục runtime.

## Trước: Luồng chặn cứng chuẩn gốc trên Claude / Python Core {#truoc}

@workflow id=hook-audit-truoc title="Chuẩn gốc: Chặn cứng đa tầng cưỡng chế kỷ luật"
| edit_ev | Edit/Write | external |
| edit_gate | edit_gate.py | security |
| stop_gate | stop_gate.py | backend |
| prompt_ctx | prompt_context.py | messagebus |
| edit_ev > edit_gate | Chặn APPROVE, TICK |
| edit_gate > stop_gate | Khớp Ledger & SHA |
| stop_gate > prompt_ctx | Bắt tick trước dừng |

Ở kiến trúc chuẩn gốc, mọi hành vi vi phạm kỷ luật (sửa code khi chưa `[~]`, chưa duyệt gate, sai vùng subagent, hoặc kết thúc lượt khi chưa ghi working log/tick plan) đều bị `block` hoặc `stop_block` ngay lập tức, buộc LLM tự sửa trong cùng lượt trước khi trả lời người dùng.

## Hiện trạng: Luồng rò rỉ sau nới hook R1–R3 & Rust v0.101.0 {#hien-trang}

@workflow id=hook-audit-hientrang title="Hiện trạng v0.101.0: Mềm hóa gate + Sót event trên Rust"
| agy_ev | Hook AGY 2.0 | external |
| rust_main | tdq-dispatch | backend |
| rust_gates | pre_tool_use.rs | security |
| soft_agy | AGY Python R1-R3 | messagebus |
| agy_ev > rust_main | Sót Pre/PostInvoc |
| rust_main > rust_gates | Thiếu 14/22 cổng |
| rust_gates > soft_agy | Sai JSON, lệch dir |

Do `main.rs` chưa định tuyến `PreInvocation`/`PostInvocation`, `protocol.rs` xuất sai trường JSON của Antigravity, và `pre_tool_use.rs`/`stop_streak.rs` bỏ qua 14/22 cổng kỷ luật (trong đó có `TDQ:TICK`, `TDQ:APPROVE`, `TDQ:TEAM`, `TDQ:LOG`), kết hợp với việc Python R1–R3 đã mềm hóa `TICK`/`LOG`/`DOD` sang `queue_remind`, agent không nhận được áp lực hay nhắc nhở kịp thời nên phát sinh sai sót hành vi.

## Lộ trình cân bằng: Tốc độ Native Rust + Kỷ luật Hard Gates {#lo-trinh}

@workflow id=hook-audit-lotrinh title="Đề xuất khắc phục: Khôi phục Schema & Core Gates"
| fix_p0 | P0: Schema AGY | security |
| fix_p1 | P1: Core Gates | backend |
| sync_rt | 1 .tdq-runtime | messagebus |
| parity_22 | Parity 22 mã | external |
| fix_p0 > fix_p1 | Event & JSON |
| fix_p1 > sync_rt | TICK, APPROVE |
| sync_rt > parity_22 | Khóa hồi quy |

Giải pháp chuẩn hóa giữ nguyên lợi thế độ trễ dưới 25 ms của Rust binary nhưng khôi phục đầy đủ hợp đồng giao tiếp Antigravity 2.0, siết chặt lại `TDQ:TICK` / `TDQ:APPROVE` / `TDQ:TEAM`, hợp nhất thư mục runtime và khóa bằng bộ kiểm thử vi phân 22 mã cổng.
