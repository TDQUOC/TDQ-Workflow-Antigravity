# Thiết kế Cổng Duyệt Thao Tác Git Theo Lượt {#thiet-ke}

Chuyển cơ chế hook bảo vệ lệnh git từ chặn cứng vô điều kiện sang mở khóa an toàn theo từng loại trong đúng lượt được người dùng xác nhận, đồng thời loại bỏ chặn nhầm chuỗi con và kẹt mở nhánh bước 3b.

## 1. Xác thực đồng thuận người dùng và hiệu lực single-turn {#ve-duyet-luot}

@workflow id=wf-git-grant title="Trước và sau khi có vé duyệt git theo lượt chống AI vượt cổng"
| b_user | Người dùng đồng ý đẩy mã trong chat | external |
| b_deny | Hook tdq-dispatch chặn cứng vô điều kiện | messagebus |
| a_prompt | PreInvocation lọc tin nhắn gốc người dùng | backend |
| a_meta | Ghi git_grants vào .tdq-runtime đã khóa | database |
| a_allow | PreToolUse khớp loại lệnh và cho chạy | security |
| b_user > b_deny | Không có kênh xác thực đồng thuận |
| a_prompt > a_meta | Chặn thẻ hệ thống, phủ định, thảo luận meta |
| a_meta > a_allow | Tự xóa vé khi đóng lượt; subagent bị chặn |

Mọi thao tác cấm tuyệt đối (force-push, Co-Authored-By, tên nhánh mang tiền tố AI) vẫn luôn bị chặn cứng bất kể trạng thái vé lượt.

## 2. Phân tích token lệnh shell và mở nhánh bước 3b {#phan-tich-token}

@workflow id=wf-shell-parse title="Trước và sau khi chuyển sang phân tích token lệnh shell"
| p_raw | Quét chuỗi con thô trên cả dòng lệnh | external |
| p_fp | Chặn nhầm đối số đọc và kẹt git switch | messagebus |
| p_tok | Tách phân đoạn, vỏ bọc và cờ toàn cục git | backend |
| p_ok | Phân loại đúng lệnh git và mở bước 3b | security |
| p_raw > p_fp | Gây chặn oan và sai thông điệp TDQ:GIT |
| p_tok > p_ok | Bắt đủ bash -c, pwsh -Command và git -C |

Cả tầng Rust tdq-dispatch và tầng Python dự phòng đều chia sẻ cùng bộ quy tắc và kiểm thử đối chiếu parity 1-1.
