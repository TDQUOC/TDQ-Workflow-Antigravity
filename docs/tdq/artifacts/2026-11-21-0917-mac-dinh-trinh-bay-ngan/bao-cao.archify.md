# Báo cáo Mặc định Trình bày Report, Spec & Plan Ngắn gọn, Tự nhiên, Dễ hiểu {#tong-quan}

@meta locale=vi

Tổng quan kết quả: Hoàn tất `7/7` đầu việc trong `3` đợt (`T1.1`–`T3.2`) để mặc định hóa văn phong kể chuyện ngắn gọn, dễ hiểu theo mẫu `1.jpg` cho mọi `spec`, `plan`, `report` và luồng nhanh `quick` trong TDQ Workflow. Toàn bộ quy chuẩn và khuôn mẫu đều giữ dưới trần `3.500` token, khóa sạch `token-budget.json`, đồng bộ `30/30` dòng bảng `luat-hien-co.md`, đóng gói mới gói `plugins/tdq-workflow-agy/` trong repo (giữ nguyên thư mục `~/.gemini/`), và vượt qua trọn bộ kiểm thử `4.638` test (`4.602 passed, 36 skipped, 0 failed`).

## 1. Trước request: Khóa cú pháp & ép nén dấu `·` khiến bản trình bày khó đọc {#truoc-request}

@workflow id=bao-cao-truoc title="1. Trước request: Bảng kỹ thuật đi trước & ép nén '·'"
| luat_cu | Chi khoa 6 phan & ky tu | external |
| nen_dot | Ép 1 dòng nối '·' ở report | security |
| sat_tran | Template sát trần 3500 tok | messagebus |
| hoi_lai | User hỏi lại 1 lượt tóm tắt | backend |
| luat_cu > nen_dot |
| nen_dot > sat_tran |
| sat_tran > hoi_lai |

Trước đây, bộ quy chuẩn `user-facing-block.md` mới khóa mặt cú pháp (6 phần, 8 luật trang trí, 6 ký tự) mà chưa có quy tắc văn phong; tệ hơn, `report-template.md` còn yêu cầu ép mỗi mục thành một dòng nối bằng `·`, trong khi đầu file `spec`, `plan`, `report` đi thẳng vào nhãn và bảng kỹ thuật. Vì vậy người đọc thường phải nhắn thêm một lượt yêu cầu tóm tắt lại cho tự nhiên, dễ hiểu như ảnh `1.jpg`.

## 2. Sau request: Tầng kể chuyện Trước → Sau → Kết quả ở trên, Bảng kỹ thuật giữ nguyên bên dưới {#sau-request}

@workflow id=bao-cao-sau title="2. Sau request: Chuẩn kể chuyện 2 tầng & Đóng gói repo"
| van_phong | Kể Trước->Sau->Kết quả (1.jpg) | frontend |
| khuon_moi | Bỏ ép '·', thêm Tóm tắt đầu file | cloud |
| khoa_luat | Giữ <=3500 tok & đồng bộ bảng luật | security |
| build_repo | Đồng bộ setup & build plugin repo | backend |
| van_phong > khuon_moi |
| khuon_moi > khoa_luat |
| khoa_luat > build_repo |

Sau khi nâng cấp, TDQ Workflow tách rõ hai lớp: phần mở đầu chat và blockquote `Tóm tắt dễ hiểu` / `Tóm tắt nhanh` ngay dưới tiêu đề file `.md` mặc định kể ngắn gọn theo mạch "Trước đây → Sau khi làm xong → Kết quả" trong 10–15 giây đọc, lồng số liệu gọn vào câu và đẩy đường dẫn dài về link chi tiết; phần bảng/đề mục kỹ thuật bên dưới giữ nguyên vẹn. Mọi hướng dẫn chi tiết dời sang `*-huong-dan.md` nên `spec-template` (`3.372` tok), `plan-template` (`3.472` tok) và `report-template` (`3.288` tok) đều gọn dưới trần `3.500` token, đồng bộ vào `tdq_setup.py`, `docs/claude-md-mau.md`, `AGENTS.md` và gói `plugins/tdq-workflow-agy/` trong repo (không cài đè bản live `~/.gemini/` theo chọn `3b`).

## 3. Đã test gì: Từ test khóa luật/ký tự, token thật đến toàn bộ 222 module {#da-test}

@workflow id=bao-cao-kiem-tra title="3. Đã test gì: Đỏ -> Xanh 7 task & Toàn bộ 222 module"
| red_green | Test đỏ trước ở 6 module | external |
| lock_check | doc_lint 81 file & .venv-tokens | security |
| plugin_val | Build AGY, --dry-run, --strict | backend |
| tron_bo | tron-bo 222 module + QC-F2/F3/F4 | messagebus |
| red_green > lock_check |
| lock_check > plugin_val |
| plugin_val > tron_bo |

Tất cả `7/7` đầu việc chạy đúng chu trình viết test đỏ trước, sửa rồi chạy xanh: kiểm bảng ký tự `scan_block_symbols.py --chi-khoi`, kiểm mục lục động `doc_index.py`, đo và khóa token thật qua `.venv-tokens`, kiểm `doc_lint.py` trên `81` file, xác thực đóng gói `agy plugin validate --strict`, chạy kiểm thử vùng chạm `15` module + `3` module kiến trúc, quét AST `scripts/` và chạy trọn bộ `scripts/tdq_test.py tron-bo --workers 1 --fresh --reuse off` trên cả `222` module.

## 4. Kết quả test: Pass 100% Trọn bộ 4.638 Test & Chứng nhận QC Full {#ket-qua}

@workflow id=bao-cao-ket-qua title="4. Kết quả test: Xanh QC Q1–Q6 & 4.602/4.638 Passed"
| suite_full | 4602 passed, 36 skip, 0 fail | messagebus |
| locks_ok | 66/66 <=3500 tok · 0 lỗi lint | backend |
| plugin_ok | findings=[] · ~/.gemini nguyên | security |
| dod_pass | Đạt Q1–Q6, QC-F1–F4 & DoD 4/4 | external |
| suite_full > locks_ok |
| locks_ok > plugin_ok |
| plugin_ok > dod_pass |

Kết quả thực tế đạt chuẩn: `scripts/tdq_test.py tron-bo` **PASS** `4.602 passed, 36 skipped, 2.892 subtests` (`0` failed, `bo_sot = 0`); bộ test mới và vùng chạm `79 passed, 192 subtests` + `189 passed` + `29 passed` kiến trúc + `21/21` test tokenizer qua `.venv-tokens`; `scan_block_symbols.py` `0` ký tự lạ; `doc_lint.py` `0` lỗi trên `81` file; `agy plugin validate plugins/tdq-workflow-agy --strict --json` trả `findings: []`; thư mục live `C:\Users\admin\.gemini\config\plugins\tdq-workflow-agy` vẫn giữ nguyên mốc `11/19/2026`.
