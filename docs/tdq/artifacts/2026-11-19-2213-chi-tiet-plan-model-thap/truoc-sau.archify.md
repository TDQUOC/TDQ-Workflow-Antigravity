# Trước/Sau — Cải thiện Độ chi tiết Plan TDQ cho Model Tier Thấp (End-to-End) {#tong-quan}

@meta locale=en

Phân tích thực chứng từ `236` plan và thiết kế kiến trúc `3` lớp cho cả Weak Planner lẫn Weak Executor. Quy trình thực hiện theo `2` vòng fanout đối kháng để chốt bản V2 hoàn chỉnh.

## Trước: R15 Rỗng, Bug tdq_team và Flash Thiếu LSP {#truoc}

@workflow id=plan-spec-truoc title="Hiện trạng: Task Mơ Hồ, Nhiễm vung_file và Flash Thiếu Neo"
| planner_old | Planner cũ | external |
| theater | Task Theater | security |
| team_bug | Bug tdq_team | messagebus |
| flash_blind | Flash Mò Code | backend |
| planner_old > theater | Đủ tên mục |
| theater > team_bug | Nhiễm _PATH |
| team_bug > flash_blind | Mất song song |

Ở hiện trạng, `SKILL.md` chạm trần `121` dòng và không nhắc Task Block. Luật `R15` chỉ dò `1` từ khóa nên chỉ `20.8%` task đạt chuẩn. Parser `tdq_team.py` quét đường dẫn trên mọi dòng nên dễ nổ `HOT FILE` giả. Subagent `flash` không có LSP buộc phải đoán schema hoặc sửa nhầm vị trí.

## Sau: Kiến trúc 3 Lớp cho Weak Planner + Weak Executor {#sau}

@workflow id=plan-spec-sau title="Thiết kế Mục tiêu: Phân rã Cơ học + Structural Contract + Hard-Gate"
| scaf | Weak Planner | external |
| card | Task Card | messagebus |
| packet | Auto Packet | backend |
| gate | R15 & Approve | security |
| scaf > card | Trích AST/LSP |
| card > packet | Cô lập Chạm: |
| packet > gate | Chặn Theater |

Lớp 1 chuẩn hóa quy trình `3` bước cơ học và Task Card dạng Structural Contract. Lớp 2 vá `tdq_team.py` và bổ sung Auto Task Packet cho `flash`. Lớp 3 nâng cấp `R15` kiểm cấu trúc và gắn hard-gate tại `approve plan`.

## Quy trình Request: Fanout 2 Vòng & Red-Team {#vong2}

@workflow id=plan-spec-vong2 title="Luồng Request: Vòng 1 Xây V1 → Vòng 2 Red-Team → Chốt V2"
| audit | Khảo sát V1 | external |
| prop_v1 | Đề xuất V1 | messagebus |
| red3 | 3 Red-Team | security |
| report_v2 | Chốt V2 + HTML | backend |
| audit > prop_v1 | Chứng cứ 236 |
| prop_v1 > red3 | Soi nhược điểm |
| red3 > report_v2 | Vá 100% lỗi |

Vòng 1 hợp nhất bằng chứng nội bộ và nghiên cứu ngoài thành kiến trúc V1. Vòng 2 tách `3` luồng Red-Team phản biện nhận thức, ngân sách TDQ và viết lại `3` ca thật. Sau cùng toàn bộ phát hiện được hội tụ thành đề xuất V2 và báo cáo Archify HTML.
