# Kiến trúc Hệ thống Agent TDQ — Hiện trạng vs Đề xuất Nâng cấp (Antigravity 2.0) {#tong-quan}

@meta locale=en

Đối chiếu `6` subagent của `TDQ-Workflow v0.102.0` (`14` hạn chế có dẫn chứng) với phương án nâng cấp `4` trụ cột cho Google Antigravity 2.0.

## 1. Hiện trạng v0.102.0: Mồ côi, Lệch Model & Hở Cổng Thoát {#hien-trang}

@workflow id=wf-before title="Hiện trạng: 3/6 agent mồ côi, lệch model AGY và thiếu SubagentStop"
| dispatch | Gọi invoke_subagent | external |
| compile | AGY đổi flash/pro | security |
| orphan | 3/6 mồ côi | messagebus |
| stop | Thiếu SubagentStop | backend |
| dispatch > compile | Mất effort & LSP |
| compile > orphan | Mò transcript dòng 1 |
| orphan > stop | 2 schema lệch nhau |

Hiện trạng có `3/6` agent không có caller mặc định, bản build AGY đổi `model`/`tools` trái quy chuẩn gốc, thiếu `SubagentStop` và lệch tên trường `handoff-schema.json`.

## 2. Trụ cột 1: Tái cấu trúc Vai trò, Kích hoạt & Leo thang {#tru-cot-vai-tro}

@workflow id=wf-after-roles title="Trụ cột 1: Gắn caller rõ ràng, thêm Explorer/Debugger và tự leo thang"
| route | Định tuyến theo pha | external |
| core6 | Gọi 6 agent theo ngưỡng | backend |
| explore | Thêm Explorer & Debugger | messagebus |
| contract | Commit & Auto-Escalate | security |
| route > core6 | Gắn caller chuẩn |
| core6 > explore | Dừng mượn agent ngoài |
| explore > contract | Vượt 2 retry leo thang |

Mỗi agent đều có điểm gọi mặc định trong `skills/`, tách gọn đúng vai trò còn thiếu và khép kín quy tắc commit trước khi trả về.

## 3. Trụ cột 2: Khớp Quyền Tool, Model/Effort & Cổng SubagentStop {#tru-cot-runtime}

@workflow id=wf-after-runtime title="Trụ cột 2: Đồng bộ AGY, siết disallowedTools và SubagentStop Rust+Python"
| ir_sync | Đồng bộ AGY & 3 host | backend |
| least_priv | Siết disallowedTools | security |
| spawn_reg | Đăng ký role + parser.rs | messagebus |
| stop_gate | SubagentStop Rust+Py | security |
| ir_sync > least_priv | Khôi phục LSP/Grep |
| least_priv > spawn_reg | Hết né bằng python -c |
| spawn_reg > stop_gate | Chặn trả thiếu chứng cứ |

Đồng bộ `model`/`effort` và tool từ nguồn gốc xuống Antigravity 2.0, siết role chỉ đọc bằng `disallowedTools` và bổ sung cổng `SubagentStop`.

## 4. Trụ cột 3 & 4: Handoff JSON, Packet V2+, Blackboard & Eval {#tru-cot-du-lieu}

@workflow id=wf-after-data title="Trụ cột 3-4: 1 Schema JSON + Packet Mini-Spec + Blackboard + Eval"
| packet | Packet + Mini-Spec | backend |
| board | Blackboard append-only | messagebus |
| json_out | 1 Schema JSON + parser | security |
| eval_kpi | KPI pass & cost / role | external |
| packet > board | AST đa ngôn ngữ |
| board > json_out | Chia sẻ state chung |
| json_out > eval_kpi | Đo trước/sau mỗi chặng |

Thống nhất một `handoff-schema.json` kèm parser, nâng cấp `tdq_team.py packet` chở đủ Per-Task Mini-Spec, nối chuỗi qua Blackboard và đo KPI từng agent.
