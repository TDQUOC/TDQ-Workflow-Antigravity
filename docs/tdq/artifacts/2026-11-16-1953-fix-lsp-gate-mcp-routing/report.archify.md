# Báo cáo — Fix lsp_gate chặn nhầm call_mcp_tool và phân luồng MCP/LSP {#tong-quan}

@meta locale=vi

Tổng quan kết quả: Hợp nhất chuẩn hoá `call_mcp_tool` và nhận diện TDQ LSP về một nguồn tại `scripts/search_rules.py`. Phân luồng chặt 3 nhánh trong `lsp_gate.py` để hết chặn nhầm `chrome-devtools`, `tavily-primary`, `find_references` và server ngoài.

## Trước request: Mọi call_mcp_tool có tham số rơi nhầm vào start_lsp {#truoc-request}

@workflow id=bao-cao-truoc title="1. Trước request: Lỗi chặn nhầm trên PreToolUse"
| agy_matcher | Matcher gọi lsp_gate trên mọi call_mcp_tool | frontend |
| loose_lsp | Các hook tự khớp lỏng chuỗi lsp | messagebus |
| binary_branch | lsp_gate chỉ tách riêng blast_radius | backend |
| false_deny | Chặn oan chrome-devtools và find_references | security |
| agy_matcher > loose_lsp |
| loose_lsp > binary_branch |
| binary_branch > false_deny |

Trước khi sửa, `lsp_gate.py` chỉ kiểm tra chuỗi `blast_radius`, rồi đẩy mọi lệnh khác qua `phan_xu()` của `start_lsp`. Đồng thời, `_common.py`, `search_rules.py` và `search_observe.py` tự kiểm lỏng `"lsp" in srv`, khiến server ngoài `other_lsp` bị gom nhầm và mọi `call_mcp_tool` có tham số đều báo `[TDQ:LSP] start_lsp without language_id`.

## Sau request: Chuẩn hoá một nguồn và định tuyến chặt 3 nhánh {#sau-request}

@workflow id=bao-cao-sau title="2. Sau request: Chuẩn hoá đơn nguồn và 3 nhánh"
| single_rule | chuan_hoa_cong_cu_mcp ở search_rules | backend |
| state_flag | _common giữ _RUNTIME_STATE tool_args_present | messagebus |
| strict_route | _phan_xu_lenh rẽ 3 nhánh TDQ LSP | security |
| allow_others | Cho qua chrome-devtools và find_references | frontend |
| single_rule > state_flag |
| state_flag > strict_route |
| strict_route > allow_others |

Sau khi sửa, `scripts/search_rules.py` cung cấp chuẩn chung `TDQ_LSP_SERVER_RE` và `ten_lenh_tdq_lsp`, đồng bộ sang `_common.py`, `lsp_gate.py`, `search_observe.py`, `search_replay.py`, `tools/patches/` và gói `plugins/tdq-workflow-agy/`. Riêng `start_lsp` gửi `Arguments: {}` rỗng tường minh bị chặn bằng `[TDQ:LSP]`, còn payload thiếu khoá hoặc JSON hỏng vẫn giữ nguyên fail-open `allow`.

## Kiểm thử: Các hạng mục đã test và kết quả thực tế {#kiem-thu}

@workflow id=bao-cao-kiem-thu title="3–4. Đã test và Kết quả test thực tế"
| unit_e2e | 21 test Q1 và 171 test Q2 PASS | security |
| full_suite | scripts/tdq_test.py tron-bo 4246 PASS | backend |
| linters_agy | ruff, doc_lint, i18n, token và agy validate OK | messagebus |
| ultra_qc | tdq-qc-tester 2 vòng PASS everything | frontend |
| unit_e2e > full_suite |
| full_suite > linters_agy |
| linters_agy > ultra_qc |

Kết quả thực tế: Q1 (`21 passed` trong `8.80s`), Q2 (`171 passed, 68 subtests` trong `9.58s` và `29 passed` `test_agy_hooks`), Q3 (`5x` probe min `66.23 ms <= 200 ms`) và Q4 (`agy plugin validate` `0` findings, giữ nguyên bản cài local `3b`) đều đạt. Trọn bộ `scripts/tdq_test.py tron-bo` đạt `4246 passed` (`35` skipped, `0` failed trong `948.55s`), `tdq-qc-tester` Vòng 2 kết luận `PASS everything`. Giới hạn: mở đầu dùng `--bo-qua-lsp` vì `pyrightconfig.json` loại trừ `tools/patches/`, bản cài local giữ nguyên theo `3b`, và `eval` chưa kích hoạt (`opt-in`).
