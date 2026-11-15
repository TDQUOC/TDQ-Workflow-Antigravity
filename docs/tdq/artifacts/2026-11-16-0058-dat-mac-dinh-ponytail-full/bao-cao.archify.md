# Báo cáo — Đặt lại mặc định mức gắt Ponytail (muc_gat) về full {#tong-quan}

@meta locale=vi

Tổng quan kết quả: Đưa hằng mặc định và mức dự phòng fail-closed của `muc_gat` từ `ultra` về `full` trong mã nguồn gốc, khóa token, bản biên dịch `plugins/tdq-workflow-agy/` và bản cài đặt người dùng; giữ nguyên `lite|full|ultra|off` tường minh và `muc_qc = full` độc lập.

## Trước request: Mặc định và fallback muc_gat ghim ở ultra {#truoc-request}

@workflow id=bao-cao-truoc title="1. Trước request: Luồng mặc định ultra"
| state_init | State mới hay khóa muc_gat rỗng | backend |
| ultra_fallback | tdq_state và luat_gon trả ultra | security |
| nap_nang | Nạp ví dụ dài và đòi bậc thang | messagebus |
| chung_md_ultra | chung.md ghim mặc định tại ultra | frontend |
| state_init > ultra_fallback |
| ultra_fallback > nap_nang |
| nap_nang > chung_md_ultra |

Trước thay đổi, `MUC_GAT_MAC_DINH` (`scripts/tdq_state.py`), `MUC_MAC_DINH` (`hooks/scripts/luat_gon.py`) và bảng cường độ `chung.md` cùng đặt mặc định tại `ultra` từ phiên `0.85.1`, làm tăng tải ngữ cảnh mặc định và ép khai báo bậc thang trên từng tạo mới.

## Sau request: Mặc định và fallback muc_gat trở về full {#sau-request}

@workflow id=bao-cao-sau title="2. Sau request: Luồng mặc định full đồng bộ"
| state_init_moi | State mới hay khóa muc_gat rỗng | backend |
| full_fallback | tdq_state và luat_gon chuẩn hóa full | security |
| bang_chung_md | chung.md đổi default và khóa token | messagebus |
| plugin_sync | Plugin AGY đồng bộ 186 file | frontend |
| state_init_moi > full_fallback |
| full_fallback > bang_chung_md |
| bang_chung_md > plugin_sync |

Sau khi cập nhật, mọi phiên mới khởi tạo ở `full`, giữ trọn thang 7 bậc và bảng cường độ, tái tạo khóa `docs/tdq/token-budget.json` (62 file), biên dịch `plugins/tdq-workflow-agy/`, đồng bộ bản cài `~/.gemini/config/plugins/tdq-workflow-agy`, và giữ nguyên lựa chọn tường minh `lite`, `full`, `ultra`, `off` cùng `muc_qc = full`.

## Kiểm thử: Các hạng mục đã test và kết quả thực tế {#kiem-thu}

@workflow id=bao-cao-kiem-thu title="3–4. Đã test và Kết quả test thực tế"
| unit_tests | 38/38 unit test muc_gat PASS | security |
| regression_tests | 54/54 test luật và hooks PASS | backend |
| lint_budget | doc_lint, token lock và ruff sạch | messagebus |
| qc_sync | QC full 4/4 PASS và SYNC_OK | frontend |
| unit_tests > regression_tests |
| regression_tests > lint_budget |
| lint_budget > qc_sync |

Kết quả thực tế: 38/38 unit test (`tests.test_state_muc_gat`, `tests.test_luat_gon`, `tests.test_state_muc_qc`) PASS trong 2.192s với `default_muc_gat=full`; 54/54 test hồi quy (`tests.test_rules_library`, `tests.test_context_hooks`) PASS trong 11.929s; `doc_lint.py` 0 vi phạm (`exit 0`); `token_budget.py --kiem` 62 file `exit 0`; `ruff` F/E/B sạch; QC mức `full` PASS 4/4 mục Q1–Q4. Giới hạn: request mở qua `--bo-qua-lsp` (`pyrightconfig.json` loại trừ `tools/patches/`) và `eval` chưa kích hoạt (opt-in).
