# Trước/Sau — Định tuyến MCP/LSP trong lsp_gate và nhận diện TDQ LSP {#tong-quan}

@meta locale=vi

Hiện trạng: Antigravity gắn `lsp_gate.py` lên toàn bộ `call_mcp_tool` nên mọi lệnh MCP có tham số đều rơi vào nhánh kiểm `start_lsp`, chặn cả `chrome-devtools`, `tavily` lẫn `find_references`/`find_symbol`. Sau khi sửa, hệ thống chuẩn hoá tên MCP về một hàm thuần duy nhất tại `scripts/search_rules.py`, tách rõ server TDQ LSP với server ngoài và chỉ chặn đúng `start_lsp` / `blast_radius` vi phạm.

## Trước: Matcher rộng cộng rẽ nhánh thiếu lọc tool {#truoc}

@workflow id=luong-truoc title="Trước: Mọi call_mcp_tool rơi vào phan_xu start_lsp"
| agy_matcher | Matcher gọi lsp_gate trên mọi call_mcp_tool | frontend |
| unwrap_loose | Giải gói gộp lỏng theo chuỗi lsp | messagebus |
| binary_branch | Rẽ nhánh chỉ trừ blast_radius | backend |
| deny_all_mcp | Chặn nhầm chrome-devtools và find_references | security |
| agy_matcher > unwrap_loose |
| unwrap_loose > binary_branch |
| binary_branch > deny_all_mcp |

Do `lsp_gate.py` thiếu bước lọc `start_lsp` và `_common.py` bắt lỏng `"lsp" in srv`, cả `chrome-devtools -> select_page`, `tavily_search` lẫn `find_references` đều bị từ chối bằng `[TDQ:LSP] start_lsp without language_id`.

## Sau: Một nguồn chuẩn hoá MCP và rẽ đúng 3 nhánh {#sau}

@workflow id=luong-sau title="Sau: Lọc đúng TDQ LSP và rẽ đủ 3 nhánh"
| single_unwrap | Giải gói một nguồn ở search_rules | messagebus |
| check_tdq_lsp | Khớp chặt server TDQ LSP đóng | security |
| route_three | Tách start_lsp, blast_radius và tool khác | backend |
| allow_others | Cho qua chrome-devtools và find_references | frontend |
| single_unwrap > check_tdq_lsp |
| check_tdq_lsp > route_three |
| route_three > allow_others |

Hàm thuần hợp nhất từ chối server ngoài (`other_lsp`), chặn `start_lsp` gọi tường minh `Arguments: {}` rỗng, giữ fail-open khi thiếu khoá/JSON hỏng, và đồng bộ toàn bộ sang `plugins/tdq-workflow-agy/`.
