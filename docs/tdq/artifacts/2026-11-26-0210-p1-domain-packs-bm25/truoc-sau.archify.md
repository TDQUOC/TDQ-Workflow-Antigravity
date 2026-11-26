# Thiết kế Trước và Sau Nâng cấp Pha P1 {#truoc-sau-p1}

@meta locale=en

Bản vẽ mô tả hai thay đổi lõi của Pha P1. Bên trái là hiện trạng rời rạc, còn bên phải là cơ chế định tuyến và khóa một chiều mới.

## 1. Bộ 4 Domain Pack, KhoBM25 & Đóng gói Nhánh Phát hành {#domain-bm25}

@workflow id=p1-router-before title="Trước: KhoBM25 rời rạc và bị loại khỏi nhánh main"
| prompt | Prompt mới vào tdq-intake | external |
| manual | Chọn work_kind và skill thủ công | backend |
| proto | skill_router.py bị chặn ở RELEASE_EXCLUDE_SCRIPTS | security |
| nodom | Chưa có thư mục scripts/defaults/domains | database |
| prompt > manual | |
| manual > proto | |
| proto > nodom | |

Hiện tại `skill_router.py` mới là nguyên mẫu đo độc lập, bị `RELEASE_EXCLUDE_SCRIPTS` loại khỏi nhánh `main` và chưa có gói cấu hình lĩnh vực.

@workflow id=p1-router-after title="Sau: 4 Domain Pack ASCII + KhoBM25 --domain trên cả main và AGY"
| prompt | Prompt vào tdq-intake (trỏ <= 4 dòng) | external |
| domains | tdq_domains nạp defaults + override docs/tdq/domains | database |
| bm25 | KhoBM25 --domain tăng hạng preferred_skills | backend |
| release | Đóng gói sạch main & AGY (i18n 0 lỗi, <= 3500 token) | security |
| prompt > domains | |
| domains > bm25 | |
| bm25 > release | |

4 gói lĩnh vực dùng `keywords_vi_ascii` giúp khớp tiếng Việt có dấu qua `bo_dau()`, vượt `i18n_check.py` và đi tự động lên nhánh `main` cùng bundle Antigravity.

## 2. Khóa Chống Hạ Cấp (Zero-Downgrade Lock) Python và Rust {#zero-downgrade}

@workflow id=p1-lock-before title="Trước: Chưa khóa sửa code khi đang ở phiên điều tra đã duyệt plan"
| edit | Gọi Edit/Write ngoài docs/ | external |
| state | state.json v6 chỉ có work_kind (thiếu domain_id) | database |
| gate | edit_gate & pre_tool_use chỉ kiểm cong_dang_cho | backend |
| leak | Phiên investigate có thể sửa nhầm mã nguồn | security |
| edit > state | |
| state > gate | |
| gate > leak | |

Khi phiên nghiên cứu đã qua bước duyệt kế hoạch, hook cũ chưa kiểm tra ràng buộc phi-code. Trạng thái cũng chưa khóa hạ cấp theo lĩnh vực.

@workflow id=p1-lock-after title="Sau: Khóa 1 chiều APPROVE đồng bộ Python và Rust (23 mã AGY)"
| edit | Gọi Edit/Write ngoài docs/ | external |
| check | edit_gate.py & Rust pre_tool_use.rs kiểm p1 + domain | security |
| block | Deny [TDQ:APPROVE] nếu phi-code hoặc investigate | security |
| upgrade | escalate-to-build -> code-build + downgrade_locked=true | database |
| edit > check | |
| check > block | |
| block > upgrade | |

Cả Python và Rust đều chặn sửa ngoài docs/ bằng mã sẵn có APPROVE cho tới khi có lệnh escalate-to-build. Hệ thống cũng từ chối mọi hạ ngược cùng phiên.
