# Báo cáo Nâng cấp QC, Tester & E2E Smoke (`v0.104.0`) {#bao-cao}

@meta locale=en

Hoàn tất cả `3` Wave (`11` task + `QC1.1`), tăng tốc toàn suite lên `313.9` giây với `--workers auto`, đóng gói `plugins/tdq-workflow-agy/` bản `0.104.0` đạt `0` findings và pass `4,693/4,704` test (`0` fail).

## 1. Trước và Sau yêu cầu: Từ tuần tự `19.8` phút sang `3` tầng Dev-First {#truoc-vs-sau}

@workflow id=wf-before-after title="Đối chiếu quy trình QC v0.103.1 và v0.104.0"
| old_serial | v0.103.1: 1 worker 19.8p | external |
| new_meta | Auto Meta-Gate 0.08s | security |
| new_smoke | smoke-e2e 19.42s ở full | backend |
| new_full | tron-bo --workers auto 313.9s | backend |
| new_a11y | A11y Snapshot + QC Card | messagebus |
| old_serial > new_meta | Tách kiểm tài liệu 1 dòng |
| new_meta > new_smoke | Mở smoke ở full giữ 2026-09-23 |
| new_smoke > new_full | 4,704 test dưới ngưỡng 420s |
| new_full > new_a11y | Bắt 0 console errors Chrome |

Thay thế chuỗi kiểm tuần tự chậm và 5 cột `tdq_timing` `[unavailable]` bằng bảng 3 cột gọn, `Changed-Flow E2E Smoke`, và Accessibility Tree Snapshot mặc định.

## 2. Đã test gì và Kết quả thực tế trên nhánh `feature/nang-cap-qc-tester-e2e` {#ket-qua-test}

@workflow id=wf-verified title="Chuỗi kiểm chứng tươi Q1-Q8 + QC1.1 sau bản 0.104.0"
| gate_meta | Q4 Meta-Gate + ruff + i18n | security |
| gate_smoke | Q3 smoke-e2e 70/70 (19.42s) | backend |
| gate_vung | QC1.1 + vung-cham 470/470 | backend |
| gate_tronbo | Q8 tron-bo 4704 (313.9s) | backend |
| gate_mcp | Q6 Chrome MCP + Q7 agy 0 err | external |
| gate_meta > gate_smoke | Auto Meta-Gate PASS 4/4 (0.08s) |
| gate_smoke > gate_vung | Sửa 3 hồi quy luật & Next step |
| gate_vung > gate_tronbo | 4693 pass, 11 skip, 0 fail, bo_sot=0 |
| gate_tronbo > gate_mcp | agy validate 0 findings · 0 JS err |

Lần chạy `tron-bo` đầu (`329.6s`) phát hiện `3` hồi quy chữ neo (`L024`, `never raise`, `Ultracode`, `Next step`), đã vá ở `QC1.1` và chạy tươi lại cả `vung-cham` lẫn `tron-bo` đạt `0` fail.

## 3. Đóng gói `0.104.0` và Phạm vi an toàn đã giữ {#pham-vi-an-toan}

@workflow id=wf-release title="Kiến trúc 5 module đồng bộ source -> plugins/tdq-workflow-agy v0.104.0"
| src_scripts | M1-M2 Scripts + Release Fix | backend |
| src_markers | M3 15+ smoke/e2e modules | security |
| src_skills | M4 Skills, QC Card, A11y UI | external |
| agy_build | build_agy_plugin v0.104.0 | messagebus |
| safe_scope | Giữ nguyên ~/.gemini & main | security |
| src_scripts > src_markers | smoke-e2e + optional i18n_check |
| src_markers > src_skills | Khóa v0.103.0 call_mcp_tool |
| src_skills > agy_build | token-budget 67 files · CHANGELOG 477 |
| agy_build > safe_scope | 0 findings strict · chờ user commit |

Mọi thay đổi chỉ nằm trên nhánh `feature/nang-cap-qc-tester-e2e` (các commit checkpoint + working tree hiện tại), chưa chạm `~/.gemini/`, `main` hay `git push`.
