# Trước/Sau — Tích hợp Caveman 5 hướng tối ưu ngữ cảnh và xin quyền vào TDQ-Workflow-Antigravity {#tong-quan}

@meta locale=en

Hiện trạng: `3` máy chủ MCP (`lsp`, `chrome-devtools`, `tavily-primary`) tốn `92.172 B` (`~23.043` token) tiền tố schema mỗi phiên; `6` subagent chưa ép chuẩn trả về gọn `Auto-Clarity`; file dữ liệu và DOM lớn `> 32 KB` đi thẳng vào ngữ cảnh không có kho khôi phục; `token_audit.py` chỉ đọc nhật ký Claude Code; và chưa có cơ chế xin quyền bật Caveman trong `tdq_setup.py`. Thiết kế mới bổ sung bộ năm module Python chuẩn (`M1`–`M5`) cộng sinh `RTK v1.2.0` và giữ nguyên `100%` giấy phép `MIT`.

## Trước: Schema MCP thô, thiếu kho CCR và kiểm toán đơn host {#truoc}

@workflow id=kien-truc-truoc title="Hiện trạng: Tải thô schema MCP, chưa có CCR và kiểm toán 1 host"
| mcp_cfg | mcp_config.json (92 KB thô) | frontend |
| subagents_old | 6 agents chưa chuẩn gọn | backend |
| read_gate_old | read_gate thiếu nhắc CCR | messagebus |
| audit_old | token_audit chỉ đọc Claude | database |
| mcp_cfg > subagents_old | |
| subagents_old > read_gate_old | |
| read_gate_old > audit_old | |

Mọi công cụ MCP gửi nguyên mô tả và metadata dư thừa vào từng lượt suy luận, tệp dữ liệu lớn không có kho lưu nguyên bản để tóm tắt an toàn, và chưa đo được rò rỉ token trên phiên Antigravity hay Codex.

## Sau: Proxy M1 opt-in, Auto-Clarity M2, Kho CCR M3, Kiểm toán M4 và Xin quyền M5 {#sau}

@workflow id=kien-truc-sau title="Thiết kế mới: 5 module M1–M5 opt-in qua tdq_setup"
| setup_m5 | M5: tdq_setup --with-caveman | security |
| proxy_m1 | M1: tdq_mcp_shrink | messagebus |
| clarity_m2 | M2: Auto-Clarity | backend |
| ccr_m3 | M3: tdq_ccr SHA-256 | database |
| audit_m4 | M4: token_audit | frontend |
| setup_m5 > proxy_m1 | opt-in |
| proxy_m1 > clarity_m2 | |
| setup_m5 > ccr_m3 | opt-in |
| ccr_m3 > audit_m4 | |

Người dùng chủ động cấp quyền qua `tdq_setup.py --with-caveman` (lưu tại `~/.tdq/caveman.json`, tách rời `RTK`); `M1` chỉ rút gọn mô tả danh sách tool và bảo toàn mọi từ khóa ràng buộc (`not`, `never`, `only`, `const`, `required`); `M3` lưu nguyên bản khớp `100%` `SHA-256`; còn `M4` kiểm toán `5` phiên gần nhất trên cả `3` host với nhãn `measured`/`inferred` minh bạch.

## Luồng xử lý Proxy MCP & Kho khôi phục CCR {#luong-xu-ly}

@workflow id=luong-m1-m3 title="Luồng bảo toàn bất biến của M1 Proxy và M3 CCR"
| req_in | Yêu cầu MCP hoặc file tren 32KB | external |
| gate_check | Phân loại luồng xử lý? | messagebus |
| shrink_m1 | Rút gọn prose giữ khóa | backend |
| ccr_store | Lưu SHA-256 vào CCR | database |
| pass_call | Chuyển thẳng tools/call | frontend |
| req_in > gate_check | |
| gate_check > shrink_m1 | tools/list |
| gate_check > ccr_store | data tren 32KB |
| gate_check > pass_call | tools/call | emphasis |

Mọi lệnh thực thi `tools/call` đi thẳng không biến đổi; khi cần xem nguyên văn dữ liệu đã tóm tắt, `tdq_ccr.py retrieve <id>` trả về đúng từng byte gốc đã băm `SHA-256`.
