# Kiến trúc QC và Tester TDQ `v0.104.0`: Trước và Sau 3 Wave {#tong-quan}

@meta locale=en

Đối chiếu luồng QC `v0.103.1` chạy `1` worker mất `19.8` phút với mô hình `3` tầng tốc độ, `Auto Meta-Gate`, `Changed-Flow E2E Smoke`, và đóng gói `v0.104.0`.

## 1. Hiện trạng `v0.103.1`: Chậm tuần tự và nặng thủ tục {#truoc}

@workflow id=wf-truoc title="Hiện trạng v0.103.1: 48.8% giấy tờ, 19.8p tuần tự, full tắt smoke"
| dev_change | Dev sửa code | external |
| meta_paper | 48.8% mục kiểm thủ tục | security |
| serial_full | tron-bo 1 worker 19.8p | backend |
| miss_e2e | Tắt smoke ở mức full | messagebus |
| dev_change > meta_paper | Đọc V2 [unavailable] · SOLID |
| meta_paper > serial_full | Lỗi ruff_cache gây INCOMPLETE |
| serial_full > miss_e2e | Chậm nhưng lọt live runtime |

Gần một nửa mục QC kiểm thủ tục, `tron-bo` chạy tuần tự mất gần `20` phút, và mức `full` mặc định tắt `smoke`/`runtime`.

## 2. Sau nâng cấp `v0.104.0`: Dev-First, E2E-First `3` tầng {#sau-3-tang}

@workflow id=wf-sau title="Thiết kế mới v0.104.0: Meta-Gate ngầm, Changed-Flow E2E <60s, Thẻ QC 10s"
| diff_in | Git diff vùng sửa | external |
| auto_gate | Auto Meta-Gate 1 dòng | security |
| fast_ast | Fast Loop vung-cham 15s | backend |
| flow_smoke | Changed-Flow E2E <60s | backend |
| dev_card | Dev Behavior QC Card 10s | messagebus |
| diff_in > auto_gate | lint · token · i18n · CLI |
| diff_in > fast_ast | Vá html và ruff_cache |
| fast_ast > flow_smoke | Bật smoke mặc định ở full |
| flow_smoke > dev_card | Accessibility Snapshot UI |

Chốt lõi TDQ chuyển xuống `Auto Meta-Gate`, vùng đổi chạy `Changed-Flow E2E Smoke` dưới `60` giây, và `Dev Behavior QC Card` cho biết kết quả ngay.

## 3. Phân ranh `5` module `M1`–`M5` triển khai `3` Wave {#module-0104}

@workflow id=wf-modules title="Bản đồ 5 module M1-M5 đồng bộ source gốc và plugins/tdq-workflow-agy v0.104.0"
| m1_runner | M1 Runner --workers auto | backend |
| m2_meta | M2 Timing & Auto Meta-Gate | backend |
| m3_markers | M3 pytest smoke/e2e markers | security |
| m4_rules | M4 Skills · Card · A11y UI | external |
| m5_release | M5 Bump 0.104.0 · AGY Build | messagebus |
| m1_runner > m3_markers | smoke-e2e router + pytest.ini |
| m2_meta > m4_rules | Meta-Gate + ẩn cột V2 rỗng |
| m3_markers > m4_rules | Mở smoke ở full giữ 2026-09-23 |
| m4_rules > m5_release | token-budget · agy validate 0 |

Năm module tách ranh giới không chồng lấn để triển khai song song theo đợt, khóa bằng test tự động rồi biên dịch sang bản `v0.104.0`.
