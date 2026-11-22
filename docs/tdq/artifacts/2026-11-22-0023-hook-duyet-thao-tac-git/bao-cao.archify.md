# Báo cáo Cơ chế Duyệt Thao tác Git một lượt trên Hook TDQ {#bao-cao}

Hoàn tất nâng cấp đồng bộ bộ hook Rust (`tdq-dispatch`) và Python (`hooks/scripts/`, `tools/patches/`) nhằm cho phép thao tác git thông thường khi có xác nhận rõ ràng của người dùng trong đúng lượt hiện tại, đi kèm ba vòng vá và rà soát bảo mật đạt không lỗi nghiêm trọng.

## 1. Luồng duyệt thao tác git Trước và Sau thay đổi {#git-approval-before-after}

@workflow id=wf-git-before-after title="Luồng kiểm tra git trước và sau khi nâng cấp"
| b_user | Lời duyệt push / bước 3b | external |
| b_blk | Chặn cứng theo chuỗi thô | security |
| a_user | Lời duyệt chính chủ | external |
| a_mint | Cấp vé git_grants | messagebus |
| a_gate | Tách token & kiểm vé | backend |
| a_ok | Qua hợp lệ, chặn ép | security |
| b_user > b_blk | Chặn nhầm & kẹt |
| a_user > a_mint | Lọc phủ định |
| a_mint > a_gate | Vé một lượt |
| a_gate > a_ok | Miễn 3b analyze |

Bộ phân tích lệnh mới đồng bộ giữa Rust và Python để tách phân đoạn thực thi, mở vỏ bọc đệ quy và loại bỏ chặn nhầm trong đối số lệnh không phải git.

## 2. Hàng rào bảo mật 3 vòng và đóng gói sạch {#security-hardening-qc}

@workflow id=wf-security-three-rounds title="Ba vòng vá và tái kiểm tra bảo mật đến Đạt"
| r1 | Vòng 1: Parser & stale sig | external |
| r2 | Vòng 2: Redirect & runtime | messagebus |
| r3 | Vòng 3: Comment nháy PS | backend |
| v_pass | Đóng gói repo, 0 lỗi | security |
| r1 > r2 | Vá QC1.1–QC1.5 |
| r2 > r3 | Vá QC2.1–QC2.4 |
| r3 > v_pass | Đạt 4771 test |

Bản dựng mới chỉ nằm trong cây plugin nội bộ của kho mã nguồn để người dùng chủ động kiểm tra và đồng bộ khi sẵn sàng.
