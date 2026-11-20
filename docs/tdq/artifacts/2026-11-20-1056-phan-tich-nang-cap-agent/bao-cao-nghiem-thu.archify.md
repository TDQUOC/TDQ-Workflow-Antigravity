# Báo cáo Phân tích & Phương án Nâng cấp Agent TDQ Workflow {#tong-quan}

@meta locale=en

Báo cáo chẩn đoán `14` hạn chế thực chứng trên `6` subagent của `TDQ-Workflow v0.102.0` và đề xuất lộ trình nâng cấp `4` trụ cột ưu tiên Google Antigravity 2.0.

## 1. Trước Request: Hiện trạng 6 Agent & Đứt gãy Ngầm {#truoc-request}

@workflow id=wf-before title="Trước request: 3/6 agent mồ côi, lệch model AGY và thiếu SubagentStop"
| dispatch | Gọi subagent | external |
| compile | AGY flash/pro | security |
| guard | Thiếu chặn ghi | messagebus |
| stop | Không Stop | backend |
| dispatch > compile | Mất effort/LSP |
| compile > guard | Hở shell inline |
| guard > stop | Lệch 2 schema |

Trước request, hệ thống chỉ gọi đều đặn `tdq-implementer`, còn `3/6` agent (`build-resolver`, `refactor-cleaner`, `security-reviewer`) chưa có caller và `tdq-qc-tester` bị bỏ trống ở mức `full`.

## 2. Sau Request: Kiến trúc Đích 4 Trụ cột Antigravity 2.0 {#sau-request}

@workflow id=wf-after title="Sau request: Đủ 6+2 vai trò, khóa tool AGY, JSON & Blackboard"
| role_wire | Gọi 6+2 agent | backend |
| agy_sync | Giữ inherit+LSP | security |
| hook_gate | Có SubagentStop | messagebus |
| data_eval | JSON+Board+KPI | external |
| role_wire > agy_sync | Sửa commit |
| agy_sync > hook_gate | Vá parser.rs |
| hook_gate > data_eval | Đo pass / role |

Phương án mới giữ quy mô gọn `6 + 2` vai trò (`explorer`, `debugger`). Quyền chỉ đọc mở hẹp cho QC, đăng ký role lúc spawn và thống nhất một `handoff-schema.json`.

## 3. Đã Kiểm Chứng & Kết Quả Thực Tế Trong Phiên {#kiem-chung}

@workflow id=wf-verified title="Đã kiểm chứng: 4 subagent, 49 file:line, 8 nguồn ngoài, doc_lint 0"
| fanout | 4 subagent audit | external |
| disk_chk | Soát 49 file:line | backend |
| ext_res | 8 nguồn + ECC | messagebus |
| gate_ok | Lint 0 + HTTP 200 | security |
| fanout > disk_chk | Chốt 14 HC |
| disk_chk > ext_res | Rõ quota 2/6 |
| ext_res > gate_ok | 0 code bị sửa |

Kết quả thực tế xác nhận đủ `14` hạn chế `HC-01`–`HC-14` có trích dẫn tồn tại thật trên đĩa, `0` vi phạm `doc_lint.py` và `0` thay đổi mã nguồn runtime.

## 4. Lộ trình Triển khai 4 Chặng An Toàn (P0–P3) {#lo-trinh}

@workflow id=wf-roadmap title="Lộ trình 4 chặng: Vá cấu hình P0 -> Hook P1 -> Schema P2 -> Eval P3"
| p0_cfg | P0: Hợp đồng | security |
| p1_hook | P1: Hook & Rust | backend |
| p2_flow | P2: Packet+6+2 | messagebus |
| p3_eval | P3: Eval đa host | external |
| p0_cfg > p1_hook | Khớp inherit |
| p1_hook > p2_flow | Đăng ký role |
| p2_flow > p3_eval | Nối Blackboard |

Tách nâng cấp thành `4` chặng nối tiếp (`P0` → `P1` → `P2` → `P3`) giúp triển khai từng bước an toàn trên Google Antigravity 2.0 mà không phá tương thích Claude Code, Codex và OpenCode.
