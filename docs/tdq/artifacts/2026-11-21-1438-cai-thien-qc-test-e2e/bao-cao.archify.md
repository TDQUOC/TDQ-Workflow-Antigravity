# Cải thiện QC và Kiểm thử TDQ theo hướng Dev-First, E2E-First {#tong-quan}

@meta locale=en

Đối chiếu thực trạng quy trình QC hiện tại (nặng `48.8%` thủ tục, `tron-bo` `19.8` phút, tắt `smoke`/`runtime` ở mức `full`) với mô hình `3` tầng tốc độ, `Auto Meta-Gate` và `Dev Behavior QC Card`.

## 1. Hiện trạng TDQ: Nặng thủ tục và chậm tích hợp sống {#hien-trang}

@workflow id=wf-hien-trang title="Hiện trạng QC TDQ: 48.8% giấy tờ, 19.8p tuần tự, lọt lỗi v0.103.0"
| dev_edit | Dev sửa mã nguồn | external |
| serial_run | tron-bo 1 worker 19.8p | backend |
| smoke_off | Tắt smoke ở mức full | security |
| doc_heavy | 48.8% kiểm thủ tục | messagebus |
| dev_edit > serial_run | Thiếu html ruff_cache |
| serial_run > smoke_off | 4603 unit pass vẫn lọt |
| smoke_off > doc_heavy | Khó đọc · V2 [unavailable] |

Kết quả kiểm toán `8` biên bản QC (`82` mục) và `38` lượt `.tdq-test.jsonl` xác nhận `40/82` mục kiểm giấy tờ/SOLID, `tron-bo --workers 1` mất trung vị `1,190.11s`, `21.4%` bị hủy `INCOMPLETE`, và `v0.103.0` vẫn vỡ `8/8` subagent live.

## 2. Mô hình Mới: Auto Meta-Gate + Changed-Flow E2E Smoke {#mo-hinh-moi}

@workflow id=wf-mo-hinh-moi title="Kiến trúc QC mới: Auto Meta-Gate chạy ngầm, E2E Smoke theo luồng đổi"
| dev_diff | Diff vùng sửa | external |
| meta_gate | Auto Meta-Gate 1 dòng | security |
| fast_loop | Tầng 1 Fast Loop 15s | backend |
| flow_smoke | Tầng 2 E2E Smoke 60s | backend |
| qc_card | Dev QC Card đọc 10s | messagebus |
| dev_diff > meta_gate | lint hooks receipt |
| dev_diff > fast_loop | AST vung-cham + fix |
| fast_loop > flow_smoke | Probe live + a11y tree |
| flow_smoke > qc_card | Iron Law 5 bước thật |

Đẩy `5` chốt lõi TDQ (`TDQ_LOG`, SHA-256 receipt, guards runtime, Rust parity, `doc_lint`) vào `Auto Meta-Gate` ngầm, bật mặc định *Changed-Flow E2E Smoke* `<60s` ở mức `full` và xuất `Dev Behavior QC Card` dễ đọc.

## 3. Lộ trình Wave 1–3 & Kiểm chứng Đề xuất {#lo-trinh-kpi}

@workflow id=wf-lo-trinh title="Lộ trình 3 Wave & KPI mục tiêu (giảm ~72% thời gian suite)"
| wave1 | W1 Quick Wins 1-2d | backend |
| wave2 | W2 E2E Smoke Meta-Gate | security |
| wave3 | W3 A11y Tree + Scenario | external |
| kpi_out | KPI Suite 5.5p · Smoke 60s | messagebus |
| wave1 > wave2 | workers auto + ruff_cache |
| wave2 > wave3 | pytest.mark.smoke + TIA |
| wave3 > kpi_out | Thẻ 10s · 100% live E2E |

Chia làm `3` đợt không gây sốc: Wave 1 vá runner rút `tron-bo` còn `~5.5` phút (`--workers auto`); Wave 2 gắn `@pytest.mark.smoke`/`e2e` bắt lỗi luồng chạm `<60s`; Wave 3 chuẩn hóa Accessibility Tree Snapshot và kịch bản `7–19` dòng.
