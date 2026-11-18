# RESEARCH — Tích hợp Caveman MCP Proxy và Nén Schema cho TDQ
Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

> Ghi chú công cụ: `tavily-primary` báo lỗi vượt hạn mức gói (usage limit). Nghiên cứu dùng công cụ `search_web` thay thế.

## Truy vấn 1: Đặc tả truyền tải stdio của Model Context Protocol (MCP)
- **Nguồn:** Đặc tả chính thức MCP (modelcontextprotocol.io), tài liệu lifecycle và JSON-RPC 2.0 (github.com, eseospace.com, sudoall.com).
- **Kết quả chính:**
  - Giao thức MCP qua `stdio` chạy server như tiến trình con của client.
  - Mọi thông điệp dùng định dạng JSON-RPC 2.0 mã hóa UTF-8.
  - Mỗi thông điệp nằm trên một dòng riêng và kết thúc bằng ký tự `\n`.
  - Bản tin JSON không được chứa ký tự xuống dòng lồng bên trong.
  - Kênh `stdout` chỉ dành riêng cho bản tin MCP hợp lệ.
  - Mọi log hay gỡ lỗi phải ghi ra `stderr` để tránh làm hỏng luồng parse.
  - Trình tự bắt tay bắt buộc gồm `initialize` từ client, phản hồi server, rồi thông báo `initialized`.
  - Sau bắt tay, proxy phải chuyển tiếp chuẩn các lệnh `tools/list` và `tools/call` theo đúng `id`.
- **Kết luận áp dụng vào TDQ:**
  - Proxy Caveman không được in bất kỳ log nào ra `stdout`.
  - Proxy phải đọc từng dòng UTF-8 từ `stdin` và phát từng dòng JSON-RPC ra `stdout`.
  - Mọi thông báo chẩn đoán của proxy phải đẩy hết sang `stderr`.
  - Proxy chỉ nén schema khi chặn phản hồi `tools/list` và giữ nguyên cấu trúc `tools/call`.

## Truy vấn 2: Chạy MCP stdio trên Windows với Antigravity và Gemini CLI
- **Nguồn:** Tài liệu cấu hình `mcp_config.json` và `settings.json` (github.io, medium.com), lỗi stdio Python trên Windows (github.com, eseospace.com, reddit.com).
- **Kết quả chính:**
  - Trên Windows, Python mặc định bật bộ đệm `stdout` khi chạy qua pipe.
  - Bộ đệm này làm client Antigravity bị treo hoặc timeout khi chờ phản hồi MCP.
  - Cần truyền cờ `-u` hoặc đặt `PYTHONUNBUFFERED=1` trong `env` của `mcp_config.json`.
  - Windows thường dùng code page ANSI như `cp1252`, dễ gây lỗi `UnicodeEncodeError`.
  - Cần đặt `PYTHONUTF8=1` để ép Python dùng UTF-8 cho cả `stdin` và `stdout`.
  - Khi tiến trình con gọi lệnh `.cmd` hoặc spawn process trên Windows, cửa sổ console dễ nháy lên.
  - Wrapper Python trên `win32` cần truyền `creationflags=subprocess.CREATE_NO_WINDOW` (`0x08000000`) khi tạo subprocess.
- **Kết luận áp dụng vào TDQ:**
  - Cấu hình `mcp_config.json` cho proxy phải dùng `args: ["-u", ...]` kèm `PYTHONUTF8=1` và `PYTHONUNBUFFERED=1`.
  - Khi proxy bọc hoặc gọi server MCP đích trên Windows, phải dùng `CREATE_NO_WINDOW`.
  - Nếu lệnh đích là file `.cmd` trên Windows, proxy cần gọi ổn định và tránh nháy cửa sổ console.

## Truy vấn 3: Nén schema công cụ và bảo toàn ràng buộc phủ định theo ASD-STE100
- **Nguồn:** Tài liệu ASD-STE100 (themenonlab.blog), nghiên cứu nén prompt và schema công cụ LLM (arxiv.org, medium.com).
- **Kết quả chính:**
  - Thuật toán nén mất dữ liệu thường xóa các từ ngắn như `not`, `never`, `only`, `default`.
  - Việc xóa từ phủ định làm đảo ngược ranh giới an toàn và gây gọi sai công cụ.
  - Nếu nén JSON Schema làm mất `const` hoặc `$ref`, mô hình sẽ tự bịa tham số.
  - Nén mô tả quá mức khiến mô hình không phân biệt được các tool có tên gần giống nhau.
  - Chuẩn ASD-STE100 ưu tiên câu mệnh lệnh ngắn, chủ động, đơn nghĩa cho phần mô tả công cụ.
  - Cần khóa cứng các token ranh giới gồm `not`, `never`, `only`, `default`, `const`, `$ref`, `required`.
- **Kết luận áp dụng vào TDQ:**
  - Bộ nén Caveman chỉ được rút gọn văn xuôi mô tả, tuyệt đối giữ nguyên token `not`, `never`, `only`.
  - Schema JSON phải bảo toàn nguyên vẹn các khóa cấu trúc `const`, `$ref`, `default`, `required`.
  - Các câu điều kiện và ranh giới an toàn phải đặt ở vùng neo không bị cắt xén.
  - Cần kiểm thử đối chứng độ chính xác chọn tool trước và sau khi nén schema.
