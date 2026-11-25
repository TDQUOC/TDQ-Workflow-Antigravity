# Paperclip dùng được gì và hợp với TDQ ở đâu? {#tong-quan}

@meta locale=en

Paperclip quản trị đội ngũ AI như một công ty thật. Hệ thống rất mạnh ở điều phối dài hạn, nhưng chưa chạy được Google Antigravity trên Windows.

- Tổng hợp từ 28 bằng chứng thật trong mã nguồn Paperclip và TDQ-Workflow-Antigravity.
- Phân tách rõ phần đã chạy ổn định, phần thử nghiệm bật cờ và 6 tính năng mới nằm trên lộ trình.
- Chỉ ra 3 hướng ứng dụng: dùng trực tiếp qua Docker hoặc WSL2, học chọn lọc cho TDQ và tái dùng pattern tốt cho dự án riêng.
- Không sửa bất kỳ file mã nguồn nào ở cả hai repository trong suốt đợt nghiên cứu.

## 1. Bốn trụ cột thực tế của Paperclip {#tru-cot}

@workflow id=paperclip-pillars title="Bốn trụ cột từ mã nguồn thật đến vận hành"
| board | Board UI và Org Chart | backend |
| plane | Control Plane và Budgets | backend |
| training | Skill Studio và Catalog | backend |
| os | Agentic OS và Sandbox | security |
| board > plane | giao việc và khóa ngân sách | |
| plane > training | đo kết quả và test skill | |
| training > os | cấp quyền tool và sandbox | |

Paperclip vượt xa mức thử nghiệm ở tầng lưu trữ giao dịch với 192 schema Drizzle PostgreSQL, atomic task checkout và circuit breaker chống lặp lỗi. Các phần như Cases, Chat Connectors và Memory Connectors hiện vẫn nằm sau cổng thử nghiệm hoặc tắt mặc định.

## 2. Tương thích 6 công cụ AI ưu tiên {#tuong-thich-agent}

@workflow id=agent-compat title="Thực trạng 6 agent ưu tiên trên máy Windows"
| core | Claude, Codex, Gemini, OpenCode | backend |
| gw | OpenClaw Gateway WebSocket | backend |
| agy | Google Antigravity ACPX | external |
| gate | Khóa darwin-arm64 trên Paperclip | security |
| core > gw | gọi chung trong Org Chart | |
| agy > gate | chưa có bản Windows | security |

Claude Code, Codex, Gemini CLI, OpenCode và OpenClaw đều đã có adapter chính thức hoàn chỉnh. Riêng Google Antigravity mới dừng ở trạng thái candidate ẩn trên giao diện, bị khóa cứng nền tảng Apple Silicon và chưa có bản phân phối cho Windows.

## 3. Chiến lược ứng dụng cho 3 hướng {#chien-luoc-ung-dung}

@workflow id=three-paths title="Lộ trình ứng dụng chọn lọc theo 3 hướng"
| direct | Dùng trực tiếp qua Docker/WSL2 | external |
| tdq | Nâng TDQ: Brake và MCP Policy | backend |
| custom | Dự án mới: Checkout và Secrets | backend |
| avoid | Tránh: local_trusted và Postgres | security |
| direct > tdq | |
| tdq > custom | |
| custom > avoid | |

Không nên chép toàn bộ server PostgreSQL và 11 bản vá pnpm của Paperclip sang TDQ để giữ sự gọn nhẹ Git-native. Thay vào đó, hãy chọn lọc các cơ chế kiểm soát lặp lỗi, chính sách MCP tool gateway và chuẩn khóa ngân sách.
