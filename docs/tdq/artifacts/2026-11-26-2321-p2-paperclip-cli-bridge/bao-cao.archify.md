# Báo cáo Pha P2: Cầu nối CLI 1 chiều Paperclip Bridge {#bao-cao-p2}

@meta locale=en

Trang giải thích trạng thái trước và sau nâng cấp Pha P2 cùng kết quả kiểm chứng ngoại tuyến, đóng gói đa host và nghiệm thu toàn kho.

## 1. Trước khi nâng cấp: Thiếu cầu nối kéo ticket và gửi báo cáo Paperclip {#truoc-p2}

@workflow id=p2-before title="Trước: Chưa có CLI kết nối Paperclip Docker/WSL2 sang TDQ"
| user | Người dùng Docker hoặc WSL2 | external |
| missing | Chưa có CLI 1 chiều cho Paperclip | backend |
| config | Config gốc chưa có paperclip_bridge | database |
| norpt | Thiếu bộ mock test và whitelist | security |
| user > missing | |
| missing > config | |
| config > norpt | |

Trước khi làm, hệ thống mới hoàn thành `P0` và `P1`. Người dùng Docker hoặc WSL2 muốn đưa ticket từ Paperclip sang TDQ phải tạo thủ công slug `HHMM`, gán `domain_id` và chép brief.

## 2. Sau khi nâng cấp: Cầu nối CLI 1 chiều tắt mặc định nối thẳng P1 và State v6 {#sau-p2}

@workflow id=p2-after title="Sau: CLI stdlib tắt mặc định, nối P1, State v6 và bảo vệ URL/token"
| cli | tdq_paperclip_bridge CLI 1 chiều | external |
| cfg | Đọc defaults + env (enabled=false thoát 3) | security |
| pull | status/pull/push-report + che *** | backend |
| state | route_domain + tdq_state init + brief | database |
| cli > cfg | |
| cfg > pull | |
| pull > state | |

Công cụ mới giữ nguyên luồng Windows vì mặc định `enabled=false` thoát mã `3` với `0` socket. Khi bật, ba lệnh con nối thẳng `tdq_domains`, `tdq_state.py init`/`set` và giữ sạch `schema_version=6` cùng `23` mã cổng AGY.

## 3. Đã kiểm thử thực tế trên mock offline, đóng gói đa host và toàn kho {#da-test-p2}

@workflow id=p2-tested title="Đã test: Mock stdlib, đóng gói main/AGY, log TDQ_LOG và Ultra QC"
| mock | Bộ test mock HTTP và lỗi 401/timeout | security |
| bundle | Whitelist main, build AGY và 24/24 verify | cloud |
| suite | Toàn kho 249 module và AST không hooks | database |
| qc | Kiểm chứng độc lập và thử nghiệm adversarial | security |
| mock > bundle | |
| bundle > suite | |
| suite > qc | |

Toàn bộ ca kiểm chứng chạy ngoại tuyến với `unittest.mock`, kiểm cả `TDQ_LOG=1/0` (`0B` stderr khi tắt), xóa sạch hoàn nguyên không chạm `P0`/`P1`, cùng kiểm tra độc lập của `tdq-qc-tester`.

## 4. Kết quả thực tế: Xanh Q1–Q7, 5.012 pass và Ultra QC Verdict PASS {#ket-qua-p2}

@workflow id=p2-results title="Kết quả: 12 mock pass, 24/24 AGY, 5.012 pass toàn kho và Verdict PASS"
| p2test | 12 mock pass, 218 cụm P2 pass | backend |
| verify | 24/24 AGY, 39 portable và 0 VI mới | cloud |
| full | tron-bo PASS 5.012 pass và 37 skip | database |
| verdict | Ultra QC Verdict PASS, 0 defect | security |
| p2test > verify | |
| verify > full | |
| full > verdict | |

Bản triển khai Pha P2 đạt `7/7` cổng `Q1`–`Q7`, `0` lỗi mới từ `ruff`, `0` import ngược `hooks/`, giữ nguyên `23` mã AGY và kết xuất Archify HTML `current`.
