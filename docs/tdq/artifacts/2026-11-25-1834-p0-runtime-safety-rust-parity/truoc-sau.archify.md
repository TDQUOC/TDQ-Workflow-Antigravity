# Thiết kế Trước và Sau Nâng cấp Pha P0 {#truoc-sau}

@meta locale=en

Bản vẽ mô tả hai thay đổi lõi của pha một trên Python và Rust. Hiện trạng giữ làm đối chiếu bên trái để thấy rõ điểm mở khóa mới bên phải.

## 1. Khóa Ghi Trạng thái & Thuê Tác vụ {#khoa-ghi-state}

@workflow id=p0-lock-before title="Trước: save() ghi đè trực tiếp không sidecar lock"
| caller | Caller gọi tdq_state.save() | external |
| warn | Chỉ cảnh báo overwriting anyway | backend |
| replace | os.replace(tmp, state.json) | database |
| nolease | Chưa có lease TTL cho task | security |
| caller > warn | |
| warn > replace | |
| replace > nolease | |

Hàm `tdq_state.save()` cũ chưa giữ khóa NTFS liên tiến trình bên ngoài hook và chưa có khóa thuê `O_EXCL` cho tác vụ chạy song song.

@workflow id=p0-lock-after title="Sau: Sidecar .lock bền đồng bộ Rust lock.rs"
| caller | Caller gọi save() hoặc acquire_lease() | external |
| sidecar | tdq_lease giữ neo .lock (Python + Rust) | security |
| replace | os.replace(tmp, state.json) v6 | database |
| ttl | Lease O_EXCL TTL + Queue + Budget | backend |
| caller > sidecar | |
| sidecar > replace | |
| replace > ttl | |

Cả Python `tdq_lease` và Rust `SidecarLockGuard` giữ tệp `.lock` cố định để khóa byte OS trước khi ghi, tránh đua xóa tệp trên Windows.

## 2. Cửa ngõ MCP, Circuit Breaker & Parity Python–Rust {#cua-ngo-mcp}

@workflow id=p0-mcp-before title="Trước: Bỏ lọt non-LSP MCP và thiếu Breaker"
| tool | Gọi MCP lạ hoặc Edit/Bash | external |
| matcher | hooks.json & agy_manifests chỉ khớp LSP | backend |
| pass | lsp_gate thoát 0 khi op is None | security |
| nochk | Chưa chặn Breaker hay Budget | backend |
| tool > matcher | |
| matcher > pass | |
| pass > nochk | |

Các tool MCP ngoài `tdq-lsp` không qua kiểm tra chữ ký và `agy_pretooluse_gate.py` bị loại khỏi bản đóng gói Antigravity.

@workflow id=p0-mcp-after title="Sau: Chặn chọn lọc READONLY giữ tròn 23 mã AGY"
| tool | Mọi MCP (đã mở matcher) & Edit/Bash | external |
| check | mcp_policy + pre_tool_use.rs check | security |
| allow | Allow nhanh tool read / tdq-lsp | backend |
| block | Deny READONLY nếu write mới / Breaker | security |
| tool > check | |
| check > allow | |
| check > block | |

Chế độ cân bằng chỉ chặn tool ghi hoặc xóa mới xuất hiện bằng mã `READONLY` kèm lệnh `approve`, giữ fast-path cho thao tác đọc.
