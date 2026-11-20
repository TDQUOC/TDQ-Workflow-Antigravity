# Trước/Sau — Triển khai 3 Chặng TDQ Plan V2+ (Per-Task Mini-Spec & Planner Rules/Examples) {#tong-quan}

@meta locale=en

Hiện thực trọn bộ `3` chặng của Kiến trúc Plan V2 kết hợp `3` nâng cấp học từ `10` Coding Planner hàng đầu: Per-Task Mini-Spec tự chứa, bộ Planner Rules (`<= 30` chỉ thị) + Contrastive Few-Shot Examples (`3` cặp ĐẠT/HỎNG), và hệ thống Parser/Scaffolder/R15 tiền-duyệt.

## Trước: Task Rời Rạc, Parser Rò Đường Dẫn và Linter Dễ Lách {#truoc}

@workflow id=v2plus-truoc title="Hiện trạng: Plan Thiếu Mini-Spec, doc_plan Rò vung_file, R15 Lỏng"
| planner | Planner (không Rules/Examples) | external |
| task_card | Task Block V1 (chỉ kỹ thuật) | messagebus |
| parser | tdq_team doc_plan + R15 cũ | security |
| executor | Implementer 70L (~20 luật) | backend |
| planner > task_card | Không Two-Pass |
| task_card > parser | Rò Tham chiếu |
| parser > executor | Không Packet |

Ở hiện trạng, `skills/tdq-plan/SKILL.md` (`121/121` dòng) thiếu luật và ví dụ cho Planner; task thiếu `Req:`, `Ngoài phạm vi:`, `EARS`, `Ownership Map`; `scripts/tdq_team.py` gom mọi đường dẫn vào `vung_file` gây `HOT FILE` giả; `scripts/doc_lint.py` (`rule_r15`) chỉ kiểm `1` từ khóa và bỏ lọt `QCn.x`/`quick`/non-code `ANTI-2`.

## Sau: Luồng Two-Pass V2+ Có Per-Task Mini-Spec, Scaffolder và Cổng Cứng {#sau}

@workflow id=v2plus-sau title="Mục tiêu V2+: Two-Pass + Scaffolder + Per-Task Spec + R15 & Packet"
| planner | Planner (Rules + 3 Few-Shot) | external |
| scaf | tdq_plan_scaffold.py | messagebus |
| task_card | Per-Task Mini-Spec + Ownership | messagebus |
| parser | doc_lint R15 + tdq_state Gate | security |
| executor | packet (Symbol-Span) -> Impl 6L | backend |
| planner > scaf | Pass 1 DAG |
| scaf > task_card | --emit-cards |
| task_card > parser | --verify-plan |
| parser > executor | Pre-Approve OK |

Pass 1 chốt DAG, `Global Constraints` và `Ownership Map`; `scripts/tdq_plan_scaffold.py` đổ neo symbol thật (`--emit-cards`, `--from-spec`) để Pass 2 điền Per-Task Mini-Spec theo `planner-rules.md` và `plan-examples.md`; `doc_lint` + `tdq_state` chặn placeholder/thiếu trường/`ANTI-2` trước khi trình duyệt; `tdq_team.py packet` trích trọn Symbol-Span cho `tdq-implementer` (`<= 6` luật, circuit breaker `2` retry).

## Kiến trúc 3 Chặng & 6 Module Độc Lập {#kien-truc}

@architecture id=v2plus-arch title="Phân tầng 6 Module Độc Lập Cho 3 Chặng Triển Khai"
| m1 | M1: tdq_team + tdq_ten_lenh | backend |
| m2 | M2: tdq_plan_scaffold.py | backend |
| m3 | M3: doc_lint + tdq_state + eval | security |
| m4 | M4: skills/tdq-plan + Rules/Ex | external |
| m5 | M5: spec/quick/build + Agents | external |
| m6 | M6: agy_hooks + Bundle + Tests | messagebus |
| m2 > m1 | doc_plan() |
| m3 > m1 | Task & Targets |
| m4 > m2 | Two-Pass CLI |
| m4 > m3 | R15 & Token Cap |
| m5 > m1 | packet + 7 fields |
| m6 > m3 | Parity & Validate |
| m6 > m4 | Bundle & E2E |

Chặng 1 hoàn thiện lõi chạy (`M1`–`M3`) theo `docs/kien-truc.md` (`scripts/` không import `hooks/`); Chặng 2 nâng cấp toàn bộ tầng luật/agent (`M4`–`M5`) dưới trần `3,500` token (`anthropic-tokenizer`); Chặng 3 vá `tools/patches/agy_hooks.py`, tái đóng gói `plugins/tdq-workflow-agy/` và kiểm định E2E + toàn bộ suite (`M6`).
