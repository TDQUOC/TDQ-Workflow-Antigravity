# Báo cáo Nghiệm thu — Nâng cấp Plan V2+ & Per-Task Spec {#tong-quan}

@meta locale=en

Hệ thống lập plan TDQ được nâng cấp toàn diện theo kiến trúc 2 lượt (`Scaffold -> Emit Cards -> Fill -> Verify -> Lint`), chuẩn hóa Per-Task Mini-Spec (`R15-Full`/`R15-Compact`), tách riêng sổ tay `planner-rules.md`/`plan-examples.md`, cô lập vùng `Chạm:`/`Tham chiếu:`/`Sinh ra:` trong `tdq_team.py`, thêm gói lệnh `packet`, cổng `tdq_state.py`/`doc_lint.py` theo mốc `R15_MOC=2026-11-20`, và đồng bộ `plugins/tdq-workflow-agy/`.

## 1. Trước request: Lỗi gộp Chạm, R15 yếu & Quá tải Planner {#truoc-request}

@workflow id=report-planv2-truoc title="Hiện trạng cũ: Rò vùng file, thiếu Mini-Spec, vượt trần chữ"
| legacy_team | Tham chiếu rò vào Chạm | backend |
| legacy_plan | Thiếu Per-Task Spec | messagebus |
| no_scaf | Nhẩm tay dễ bịa symbol | external |
| gate_gap | Không chặn ở approve | security |
| legacy_team > legacy_plan | Lỗi chia đợt giả |
| legacy_plan > no_scaf | Subagent thiếu ngữ cảnh |
| no_scaf > gate_gap | Plan rỗng vẫn qua cổng |

Trước nâng cấp, `tdq_team.doc_plan` quét backtick lẫn cả `Tham chiếu:` và fence, `tdq-plan/SKILL.md` phình to thiếu bộ ví dụ đối chiếu, subagent phải tự tìm toàn file tốn context, `R15` chỉ đòi vài dòng sơ sài (hoặc bỏ sót `ANTI-2`/placeholder cấm) và `tdq_state approve` chưa khóa `doc_lint R15`.

## 2. Sau request: Kiến trúc Plan V2+ Two-Pass, Mini-Spec & Packet {#sau-request}

@workflow id=report-planv2-sau title="Kiến trúc mới: Scaffold 2 Lượt -> R15 Gate -> Packet -> AGY Plugin"
| scaf | tdq_plan_scaffold.py (AST+Wave) | backend |
| lint | doc_lint R15 V2+ & tdq_state Gate | security |
| rules | planner-rules + plan-examples + Mini-Spec | messagebus |
| pkg | tdq_team packet + AGY hooks & plugin | external |
| scaf > rules | Đọc thật trước khi điền |
| rules > lint | Chặn chặt sau R15_MOC 2026-11-20 |
| lint > pkg | Bơm Packet 7 trường cho Subagent |

`tdq_plan_scaffold.py` trích symbol bằng Python AST + spec parser rồi sinh thẻ khuyết `--emit-cards` và kiểm tra `--verify-plan`/`--check-wave`; `tdq_team.py` cô lập `Chạm:`/`Tham chiếu:`/`Sinh ra:` (hỗ trợ cả đường dẫn thường lẫn backtick), ổn định SHA phân công, cung cấp lệnh `packet`; `doc_lint` + `tdq_state` gác `R15-Full`/`R15-Compact`, `ANTI-2` và ngưỡng chữ/token; toàn bộ gói được đóng mới vào `plugins/tdq-workflow-agy/`.

## 3. Đã test gì: 5 Mô-đun Mới, 5 Sửa Hồi quy & 220 Mô-đun Toàn Repo {#da-test-gi}

@workflow id=report-planv2-kiem-thu title="Chuỗi kiểm chứng DoD Q1–Q6 & QC Full"
| u_new | 5 Suite Mới (67 cases) | backend |
| u_reg | Phá 5 Hồi quy cũ (vung-cham) | security |
| gate | doc_lint + token_budget + i18n + AST | messagebus |
| e2e | agy validate + portable + parity | external |
| full | tron-bo 220 Module (4,525 cases) | security |
| u_new > u_reg | Bắt 5 lỗi ở vung-cham |
| u_reg > gate | Sửa red -> green 100% |
| gate > e2e | Rebuild AGY Plugin & Lock Budget |
| e2e > full | Kiểm tra sạch 0 bỏ sót |

Quá trình QC (`muc_qc=full`) lần lượt chạy `tdq_test.py vung-cham` (bắt được `5` lỗi hồi quy trên `4` mô-đun và đã sửa dứt điểm `red -> green`), chạy từng lệnh DoD `Q1..Q6`, kiểm tĩnh AST/`doc_lint`/`token_budget`/`i18n_check`/`agy.EXE plugin validate --strict`, và chạy lại trọn bộ `tdq_test.py tron-bo --workers 1 --fresh --reuse off` trên toàn bộ `220` mô-đun test.

## 4. Kết quả test: 4,525/4,525 Xanh, 67/67 Suite Mới PASS & Budget Đạt Trần {#ket-qua-test}

@workflow id=report-planv2-ket-qua title="Kết quả Nghiệm thu: Đạt 6/6 DoD & 0 Thất bại"
| suite | 4,525 Cases (0 Fail / 35 Skip) | security |
| pkg5 | 67/67 Unit+E2E Mới PASS | backend |
| cap | SKILL 120L / Ex 1,281 tok / Impl 31L | messagebus |
| agy | Validate strict 0 findings / Parity OK | external |
| suite > pkg5 | bo-sot = 0 (tron-bo 1370.06s) |
| pkg5 > cap | Tất cả skill <= 3,500 tok |
| cap > agy | Plugin ~/.gemini giữ nguyên 100% |

Trọn bộ `tdq_test.py tron-bo` đạt `4,525` test thu thập, `35` bỏ qua theo nền tảng, `0` lỗi (`1370.06s`, `bo_sot=0`); nhóm `5` mô-đun mới đạt `67/67` OK; `Q1+Q3` đạt `326 passed, 2 skipped`; `Q5` (`portable + agy validate + rust parity`) đạt `90 passed`; `tdq-plan/SKILL.md` còn `120` dòng, `plan-examples.md` `1,281` tokens, `tdq-implementer.md` `31` dòng, plugin cục bộ `~/.gemini` hoàn toàn không bị đụng.
