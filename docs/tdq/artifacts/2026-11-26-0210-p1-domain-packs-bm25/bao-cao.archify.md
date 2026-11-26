# Báo cáo Pha P1: Bộ 4 Domain Pack, KhoBM25 và Khóa Chống Hạ Cấp {#bao-cao-p1}

@meta locale=en

Trang giải thích trạng thái trước và sau nâng cấp Pha P1 cùng kết quả kiểm chứng toàn diện trên Python, Rust và gói Antigravity.

## 1. Trước khi nâng cấp: Thiếu phân loại lĩnh vực và khóa chống hạ cấp {#truoc-p1}

@workflow id=p1-before title="Trước: Chưa có Domain Pack, KhoBM25 bỏ qua domain và dễ hạ cấp"
| intake | tdq-intake chưa phân loại | backend |
| router | Thiếu route và --domain | backend |
| state | Thiếu domain_id và lock | database |
| guard | Chưa chặn ngoài docs | security |
| intake > router | |
| router > state | |
| state > guard | |

Trước khi làm, luồng intake chưa tách domain nghiên cứu khỏi build code. BM25 cũng bỏ qua domain và chưa có khóa chống hạ cấp trên Python lẫn Rust.

## 2. Sau khi nâng cấp: 4 Domain Pack ASCII, BM25 theo domain và Khóa 1 chiều {#sau-p1}

@workflow id=p1-after title="Sau: 4 Domain Pack, KhoBM25 1.25x và Parity Zero-Downgrade"
| packs | 4 Domain Pack + rollback p1 | backend |
| bm25 | KhoBM25 1.25x và sàn 0.05 | backend |
| lock | State v6 khóa 1 chiều | database |
| parity | Python/Rust chặn TDQ:APPROVE | security |
| packs > bm25 | |
| bm25 > lock | |
| lock > parity | |

Hệ thống định tuyến bốn gói lĩnh vực không dấu qua `tdq_domains.py`, giữ `skill_router.py` trên bản release với cờ `--domain`, giữ `schema_version=6` và khóa một chiều `escalate-to-build` đồng nhất trên Python và Rust.

## 3. Đã kiểm thử thực tế trên Python, Rust và AGY {#da-test-p1}

@workflow id=p1-tested title="Đã test: Đơn vị P1, Parity Rust, Đóng gói đa host và Ultra QC"
| unit | Unit P1, BM25 và State v6 | backend |
| rust | Cargo test 43/43 và Parity | security |
| bundle | Build AGY, validate và budget | cloud |
| qc | 2 lượt tron-bo và QC độc lập | security |
| unit > rust | |
| rust > bundle | |
| bundle > qc | |

Mọi sửa đổi kể cả bản vá chỉ mục dòng `QC1.1` trên `skills/tdq-intake/SKILL.md` đều được đồng bộ lại vào `plugins/tdq-workflow-agy/` và kiểm chứng lại trên toàn bộ cụm liên quan.

## 4. Kết quả thực tế: Xanh mọi cổng Q1–Q7 và Verdict PASS {#ket-qua-p1}

@workflow id=p1-results title="Kết quả: 43 Rust test, 24/24 AGY, tron-bo + tách ca và PASS"
| gates | Xanh 13, 26, 98, 101, 102 test | backend |
| verify | 24/24 AGY và 43/43 Rust | security |
| fullsuite | 4,998 pass + 100% ca tách | database |
| verdict | Ultra QC PASS, 0 defect | cloud |
| gates > verify | |
| verify > fullsuite | |
| fullsuite > verdict | |

Toàn bộ yêu cầu Pha P1 hoàn tất trên commit `92621dbf`, giữ nguyên 23 mã cổng AGY, `schema_version=6`, `0` import chéo và `0B` stderr khi `TDQ_LOG=0`.
