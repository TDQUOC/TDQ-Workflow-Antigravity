# Phụ lục — Danh mục Tính năng & Ma trận Điểm số Ứng dụng Paperclip

> Tài liệu này tổng hợp đầy đủ kiểm chứng từ mã nguồn `C:/Users/admin/Documents/paperclip` và đối chiếu với `TDQ-Workflow-Antigravity`. Mọi nhận định gắn kèm mã bằng chứng trong `evidence.jsonl` và nhãn độ tin cậy (`Verified`, `Single-source`, `Inferred`).

## Phần 1 — Kiểm kê 4 Trụ cột & Lộ trình (Code thật vs README/ROADMAP)

| Trụ cột | Nhóm tính năng | Trạng thái thật | Độ tin cậy | Ghi chú giới hạn & bằng chứng |
|---|---|---|---|---|
| **1. Task Manager** | Task phân cấp `goalId`/`parentId`, atomic checkout (`checkoutRunId`) | **Implemented** | `Verified` | Khóa 1 assignee chạy đồng thời (`6ed72ebf2102`) |
| **1. Task Manager** | Scheduled Routines & Webhook trigger (`routines`, `routineRuns`) | **Implemented** | `Verified` | Tự remap annotation khi mô tả thay đổi (`675b0fde5eca`) |
| **1. Task Manager** | `completionContracts` (SHA-256), `automaticRunBrakes`, `decisionQueues` | **Implemented** | `Verified` | Circuit breaker 3 pha `closed/open/half_open` (`939a5d60eb24`, `738f669f4a36`) |
| **1. Task Manager** | Artifacts, Document Revisions & Inline Annotations | **Implemented** | `Verified` | Theo dõi lịch sử phiên bản và bình luận (`675b0fde5eca`) |
| **1. Task Manager** | `Cases & Reusable Workflows` (`CasesExperimentalGate`) | **Partial-Experimental** | `Verified` | Phải bật cờ experimental ở instance (`9808e627df4b`) |
| **2. Org Chart** | Cây nhân sự hỗn hợp (`reportsTo`), Primary agent cá nhân | **Implemented** | `Verified` | Render Org Chart SVG và quản lý trạng thái agent (`bebe66c2b40b`) |
| **2. Org Chart** | Approvals gate (hiring, budget, action), Budget `hard_stop` | **Implemented** | `Verified` | Khóa transaction `for("update")`, hủy run ngay (`a8e553513c25`) |
| **2. Org Chart** | Multi-company isolation & Portable Company ZIP Export/Import | **Implemented** | `Verified` | Cloud còn thiếu blob-store relay cho bundle lớn (`7b601bcb0d2c`) |
| **3. Training** | Company Skills, Skill Studio, Versions, Test Inputs & Runs | **Implemented** | `Verified` | Hỗ trợ test và khôi phục phiên bản skill (`675b0fde5eca`) |
| **3. Training** | `skills-catalog` & `teams-catalog` cài đội ngũ mẫu nhanh | **Implemented** | `Verified` | Đóng gói sẵn Org Chart + Skills + Routines (`bf1d1856adaf`) |
| **4. Agentic OS** | BYO Agent (`16` builtin adapter types + plugin loader) | **Implemented** | `Verified` | Riêng Antigravity chỉ mới là candidate `darwin-arm64` (`4f327884e23c`, `0cd7c9e55dee`) |
| **4. Agentic OS** | MCP Tool Gateway (`Profile/Policy`, quarantine) & Secrets binding | **Implemented** | `Verified` | V1 chưa chặn tiến trình ngoài tự gọi thẳng MCP (`2f2a03922807`, `0b1938766c67`) |
| **4. Agentic OS** | Chat & Email Connectors (Slack, Discord, Telegram, GitHub, Voice) | **Partial-Experimental** | `Verified` | Chạy sau cổng experimental setting (`9808e627df4b`) |
| **4. Agentic OS** | Memory / Knowledge (Mem0, Zep, Supermemory, Cognee, Honcho) | **Partial-Experimental** | `Verified` | Tắt mặc định, không tự động sync hội thoại (`851aed075830`) |
| **4. Agentic OS** | Managed Cloud (`cloud.ts`) & `9` Cloud Sandbox Providers | **Partial-Experimental** | `Verified` | Dynamic plugin install chỉ dùng cho self-hosted single-tenant (`2bcfa6c78590`, `0569625de455`) |
| **Roadmap** | `MAXIMIZER MODE`, `Work Queues`, `Self-Organization`, `Auto Learning`, `Desktop App`, `BYO Ticket` | **Planned** | `Verified` | Chỉ mới xuất hiện trên `ROADMAP.md`, chưa có mã sản phẩm (`7b601bcb0d2c`) |

## Phần 2 — Tương thích 6 Công cụ BYO Agent Ưu tiên

| Công cụ | Adapter trong Paperclip | Mức sẵn sàng | Windows vs Linux/macOS | Kết luận thực tế | ID |
|---|---|---|---|---|---|
| **Claude Code** | `claude_local` + `paperclip_runner` | **Recommended** | Chạy CLI tốt đa nền tảng; ACPX cho macOS/Linux | Dùng ngay cho tác vụ code và vận hành dài | `4f327884e23c`, `d0e96cdea61e` |
| **Codex** | `codex_local` + Native Rust | **Recommended** | Chạy CLI và Runner có khóa secret mutex an toàn | Tích hợp hoàn thiện, ổn định cao | `4f327884e23c`, `0b1938766c67` |
| **Gemini CLI** | `gemini_local` (`--acp` / `--resume`) | **Implemented** | Chạy CLI đa nền tảng qua `@google/gemini-cli` | Hỗ trợ đủ truyền context và nối session | `040177970640` |
| **OpenCode** | `opencode_local` + Native | **Implemented** | Chạy CLI đa nền tảng, probe model trước `ready` | Phù hợp khi muốn đa dạng `provider/model` | `4f327884e23c`, `d0e96cdea61e` |
| **OpenClaw** | `openclaw_gateway` (`ws://`/`wss://`) | **Implemented** | Độc lập OS do gọi từ xa qua WebSocket + auto-pair | Rất tiện khi tách Gateway chạy trên máy khác | `040177970640` |
| **Antigravity** | `paperclip_runner` (`acpxAgent="antigravity"`) | **Candidate-Only** | **Chưa hỗ trợ Windows** — khóa cứng `darwin-arm64`, ẩn UI | Trên Apple Silicon cần bật env gate; trên Windows phải đi vòng | `0cd7c9e55dee`, `c3f785b3a54d` |

## Phần 3 — Ma trận Đối chiếu Paperclip vs TDQ-Workflow-Antigravity

| Chiều so sánh | Paperclip | TDQ-Workflow-Antigravity | Lựa chọn tối ưu | ID |
|---|---|---|---|---|
| **Mục tiêu cốt lõi** | Quản trị công ty AI liên tục nhiều phòng ban | Kỷ luật phân tích, lập plan, viết code và QC cho dev/nhóm | Kết hợp: TDQ lo kỹ thuật code, Paperclip lo vận hành | `c4df6da485e1`, `486ed58ea0e8` |
| **Hỗ trợ Windows & Antigravity** | Antigravity khóa `darwin-arm64`; `local_trusted` thiếu chặn loopback Windows | Chạy tự nhiên trên Windows qua Node/Python + plugin `tdq-workflow-agy` | Dùng TDQ cho Antigravity trên Windows | `0cd7c9e55dee`, `f106298288d2`, `7c2529a5c8a9` |
| **Kiểm soát chi phí & vòng lặp** | `budgetMonthlyCents` `hard_stop` + `automaticRunBrakes` | Đo token/telemetry timing + `TDQ:GON` chống phình code | TDQ nên học thêm cơ chế Budget & Circuit Breaker | `a8e553513c25`, `738f669f4a36`, `480c1cafc303` |
| **Bảo mật MCP** | Gateway 4 lớp + Changed-Tool Quarantine | `tdq_mcp_launcher.mjs` đọc `secrets.env` + rule Pre-flight | TDQ nên học bảng Policy `allow/ask/block` theo role | `2f2a03922807`, `7c2529a5c8a9` |

## Phần 4 — Ma trận Chấm điểm & Phân nhóm 3 Hướng Ứng dụng

> Thang điểm `1`–`5`: **Giá trị** càng cao càng hữu ích (`5` cao nhất); **Độ khó** và **Rủi ro** càng cao càng tốn công hoặc dễ lỗi (`5` nặng nhất). Mỗi mục gắn rõ 1 trong 3 nhóm: **Nên áp dụng ngay**, **Cân nhắc sau**, **Không nên học theo**.

### Nhánh A — Dùng Paperclip trực tiếp (`Direct Use`)

| Hạng mục ứng dụng | Giá trị | Độ khó | Rủi ro | Phân nhóm | Hướng hành động cụ thể & độ tin cậy | ID |
|---|---|---|---|---|---|---|
| Chạy trong Docker hoặc WSL2 với `authenticated + private` | `5` | `2` | `1` | **Nên áp dụng ngay** | Tránh lỗ hổng Windows `local_trusted` và tận dụng CLI cài sẵn (`Verified`) | `d0e96cdea61e`, `f106298288d2` |
| Giao tác vụ cho `Claude Code`, `Codex`, `Gemini CLI`, `OpenClaw` kèm `hard_stop` | `5` | `2` | `2` | **Nên áp dụng ngay** | Bắt buộc đặt trần ngân sách để chặn đốt token khi poll routine (`Verified` / `Inferred`) | `a8e553513c25`, `040177970640` |
| Dùng `npx paperclipai` khi agent tương tác CLI | `4` | `1` | `1` | **Nên áp dụng ngay** | Tuân thủ cảnh báo skill để tránh shell injection từ `pnpm` (`Verified`) | `e519d1712f1d` |
| Kết nối `Cases`, `Chat Connectors`, `Memory Connectors` | `3` | `3` | `3` | **Cân nhắc sau** | Chỉ bật thử nghiệm nội bộ vì vẫn sau experimental gate (`Verified`) | `851aed075830`, `9808e627df4b` |
| Chờ dùng `Antigravity` trực tiếp trên Windows qua `acpx` | `2` | `5` | `4` | **Không nên học theo** | Mã nguồn khóa `darwin-arm64`, chưa có binary Windows (`Verified`) | `0cd7c9e55dee`, `c3f785b3a54d` |
| Mở chế độ `local_trusted` thuần trên máy Windows nối Internet | `1` | `1` | `5` | **Không nên học theo** | Thiếu cơ chế chặn process-tree truy cập board qua loopback (`Verified`) | `f106298288d2` |

### Nhánh B — Học kiến trúc nâng cấp TDQ Workflow (`tdq-workflow-agy`)

| Ý tưởng / Cơ chế học từ Paperclip | Giá trị | Độ khó | Rủi ro | Phân nhóm | Cách ứng dụng vào TDQ & độ tin cậy | ID |
|---|---|---|---|---|---|---|
| Circuit Breaker kiểu `automaticRunBrakes` cho wave subagent | `5` | `2` | `1` | **Nên áp dụng ngay** | Tự dừng vòng lặp retry khi subagent fail liên tiếp để tiết kiệm token (`Verified` / `Inferred`) | `738f669f4a36` |
| Ma trận `MCP Policy` + `Changed-Tool Quarantine` | `5` | `3` | `2` | **Nên áp dụng ngay** | Phân quyền tool theo role và chặn ngầm tool ghi mới từ MCP ngoài (`Verified`) | `2f2a03922807` |
| `Completion Contracts` SHA-256 + Eval Matrix fail-closed | `4` | `2` | `1` | **Nên áp dụng ngay** | Dùng để kiểm chứng báo cáo và benchmark skill định kỳ (`Verified`) | `939a5d60eb24`, `17f1800f1c31` |
| Ngắt ngân sách `hard_stop` theo session / request | `4` | `3` | `2` | **Cân nhắc sau** | Ghép cùng `tdq_timing.py` để dừng wave vượt ngưỡng token đặt trước (`Inferred`) | `a8e553513c25` |
| Inline Document Annotation anchored theo revision | `3` | `3` | `2` | **Cân nhắc sau** | Mở rộng Archify UI để góp ý trực tiếp lên từng đoạn `spec`/`plan` (`Single-source`) | `675b0fde5eca` |
| Đưa PostgreSQL nhúng và `11` patch npm vào TDQ | `1` | `5` | `5` | **Không nên học theo** | Phá vỡ cấu trúc nhẹ, zero-server và đa nền tảng của TDQ (`Verified`) | `ec1f5f6fc365`, `480c1cafc303` |

### Nhánh C — Tham khảo cho Dự án Riêng / Sản phẩm Đa-Agent

| Pattern kiến trúc từ Paperclip | Giá trị | Độ khó | Rủi ro | Phân nhóm | Ghi chú thiết kế & độ tin cậy | ID |
|---|---|---|---|---|---|---|
| Atomic Task Checkout (`checkoutRunId` + `executionLockedAt`) | `5` | `2` | `1` | **Nên áp dụng ngay** | Ngăn hai worker tranh nhận cùng một ticket bằng DB lock (`Verified`) | `6ed72ebf2102` |
| Secrets theo phiên bản + Binding target + Run Redaction | `5` | `2` | `1` | **Nên áp dụng ngay** | Kiểm toán `secretAccessEvents` và tự che token khỏi log (`Verified`) | `0b1938766c67` |
| Plugin SDK đa tầng (`protocol` / `ui` / `testing` / `dev-server`) | `4` | `3` | `2` | **Cân nhắc sau** | Học phân tách API SDK nhưng phải thêm iframe sandbox cho UI (`Verified`) | `bf1d1856adaf`, `2bcfa6c78590` |
| Export/Import toàn công ty thành Portable ZIP | `4` | `3` | `2` | **Cân nhắc sau** | Chuẩn hóa gói bàn giao cấu hình Org Chart + Skills + Routines (`Verified`) | `675b0fde5eca` |
| Tái dùng nguyên kiến trúc Plugin UI same-origin JS | `1` | `2` | `5` | **Không nên học theo** | Rủi ro bảo mật cao do plugin gọi thẳng HTTP API cùng session (`Verified`) | `2bcfa6c78590` |
