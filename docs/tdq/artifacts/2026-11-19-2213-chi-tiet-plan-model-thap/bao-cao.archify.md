# Báo cáo Nghiệm thu — Kiến trúc Plan Chi tiết cho Model Tier Thấp V2 {#tong-quan}

@meta locale=en

Khảo sát `236` plan cho thấy chỉ `20.8%` task sau `2026-11-11` đạt chuẩn `>= 12/14`. Qua `2` vòng phân tích và `3` luồng Red-Team, thiết kế V2 vá kín `12/12` nhược điểm cho cả Weak Planner lẫn Weak Executor.

## Trước: Task Mơ Hồ, R15 Rỗng & Đụng Trần Kĩ Thuật {#truoc}

@workflow id=v2-truoc title="Hiện trạng (5.08–7.42/14): Task Theater, Mega-Task 2.8x và Flash Mò Code"
| old_plan | Weak Planner | external |
| theater | Task Theater | security |
| team_err | Bug _PATH | messagebus |
| flash_err | Flash Mù LSP | backend |
| old_plan > theater | Thiếu neo/I-O |
| theater > team_err | Mega-task 2.8x |
| team_err > flash_err | Nổ HOT FILE |

Trong kho `48` task chấm sâu, `58.3%` thiếu Trước → Sau và `60.9%` thiếu neo. Luật `R15` chỉ dò `1` từ khóa nên để lọt `QC1.1` và `quick-lane`. Subagent `flash` không có LSP nên dễ bịa schema và gãy hợp đồng.

## Vòng 2 Red-Team: Phanh Chặn 12 Nhược Điểm V1 {#redteam}

@workflow id=v2-redteam title="Tái phân tích 3 luồng A/B/C → Phát hiện ND-1..ND-12"
| prop_v1 | Bản V1 (3 Lớp) | external |
| red_a | Red-Team A | security |
| red_b | Red-Team B | security |
| red_c | Red-Team C | messagebus |
| nd12 | 12 Mã ND-1..12 | backend |
| prop_v1 > red_a | Tải nhận thức |
| prop_v1 > red_b | Trần 3500 tok |
| prop_v1 > red_c | 3 Ca thật |
| red_a > nd12 | IFScale / Drift |
| red_b > nd12 | R12 / AGY / Team |
| red_c > nd12 | 9.3x / Sweep |

Red-Team A bắt lỗi IFScale trên chính Weak Planner và bẫy stale SHA. Red-Team B phát hiện `qc.md` chỉ còn `4` token và file AGY bị ghi đè. Red-Team C chứng minh tách cứng `2` file làm nổ `6` task và vỡ `QC1.1`.

## Sau: Thiết Kế Hoàn Chỉnh V2 (End-to-End 2b + 3a) {#sau}

@workflow id=v2-sau title="Giải pháp V2 (12–14/14): Two-Pass + Symbol-Span Packet + R15 2 Profile"
| twopass | Two-Pass Plan | external |
| scaff | Scaffolder AST | messagebus |
| packet | Symbol Packet | backend |
| r15v2 | R15 & ANTI-2 | security |
| twopass > scaff | Pass 1 DAG |
| scaff > packet | Cô lập Chạm: |
| packet > r15v2 | Trước Trình |

Weak Planner chạy Two-Pass và `--emit-cards` để điền `R15-Full` hoặc `R15-Compact`. Scaffolder hỗ trợ `--refs`, `--from-spec`, ngoại lệ `Uniform Sweep` và nhãn `Sinh ra:`. Cổng `R15` + `ANTI-2` chặn trước trình duyệt và kiểm sạch tại `approve plan`/`quick`.

## Bằng chứng Nghiệm thu: Điểm Số Tăng Vọt Trên 3 Ca Thật {#kiemchung}

@workflow id=v2-kiemchung title="Stress-Test 3 Ca Thất Bại Lịch Sử Trước → Sau Theo V2"
| ca1 | Ca 0046:T2.3 | external |
| ca2 | Ca 1632:T2.1+QC | messagebus |
| ca3 | Ca 1457+0058 | backend |
| pass_all | QC Full PASS | security |
| ca1 > pass_all | 5 → 14/14 |
| ca2 > pass_all | 8/2 → 14/13 |
| ca3 > pass_all | 0/6.5 → 12/13 |

Ca `0046:T2.3` nhảy từ `5/14` lên `14/14` nhờ `--from-spec` và `--refs`. Ca `1632:QC1.1` giữ gọn `1` task sweep thay vì xé `3` task mà vẫn đạt `13/14`. Ca `1457` và `0058` sạch `ANTI-2` và giữ gọn trong `quick-lane`.
