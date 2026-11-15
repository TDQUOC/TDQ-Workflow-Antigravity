# Trước/Sau — Đặt lại mặc định mức gắt Ponytail (muc_gat) về full {#tong-quan}

@meta locale=vi

Hiện trạng: Từ bản 0.85.1, hằng mặc định và mức dự phòng fail-closed của luật tinh gọn Ponytail (muc_gat) đang đặt ở ultra khiến mọi phiên mới đều nạp toàn bộ ví dụ dài và bắt buộc khai báo bậc thang trên từng tạo mới. Bản cập nhật đưa mặc định và fallback muc_gat về lại full, tiết kiệm ngữ cảnh trong khi vẫn giữ trọn thang 7 bậc và bảng cường độ, đồng thời giữ nguyên lựa chọn tường minh lite, full, ultra, off.

## Trước: Mặc định và fallback muc_gat đang ở mức ultra {#truoc}

@workflow id=luong-truoc title="Trước: State mới và bộ lọc luật mặc định ở mức ultra"
| state_init | Mở state mới hoặc đọc khóa muc_gat rỗng hay lạ | backend |
| fallback_ultra | tdq_state và luat_gon chuẩn hóa fail-closed về ultra | security |
| load_heavy | Nạp cả ví dụ dài và mục riêng ultra vào ngữ cảnh | messagebus |
| loud_always | Bắt buộc ghi dòng bậc thang cho mọi tạo mới nhỏ lẻ | frontend |
| state_init > fallback_ultra |
| fallback_ultra > load_heavy |
| load_heavy > loud_always |

Đặc điểm hiện tại: `scripts/tdq_state.py` (`MUC_GAT_MAC_DINH = "ultra"`), `hooks/scripts/luat_gon.py` (`MUC_MAC_DINH = "ultra"`) và `skills/tdq-build/references/rules/chung.md` đều ghim mặc định tại `ultra`.

## Sau: Mặc định và fallback muc_gat trở về mức cân bằng full {#sau}

@workflow id=luong-sau title="Sau: State mới và bộ lọc luật mặc định ở mức full"
| state_init | Mở state mới hoặc đọc khóa muc_gat rỗng hay lạ | backend |
| fallback_full | tdq_state và luat_gon chuẩn hóa fail-closed về full | security |
| load_balanced | Giữ đủ thang 7 bậc và bảng cường độ, cắt ví dụ dài | messagebus |
| explicit_keep | Giữ nguyên quyền đặt tường minh lite, full, ultra, off | frontend |
| state_init > fallback_full |
| fallback_full > load_balanced |
| load_balanced > explicit_keep |

Đặc điểm sau cập nhật: Mặc định `muc_gat` trở về `full` đồng bộ trên nguồn gốc, khóa `token-budget.json`, bản biên dịch `plugins/tdq-workflow-agy/` và bộ unit test hồi quy; `muc_qc` vẫn giữ mặc định `full` độc lập.
