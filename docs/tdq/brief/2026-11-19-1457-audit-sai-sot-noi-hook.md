# Brief: Audit Sai sót Behavior khi nới Hook và 10 Nguy cơ tiềm ẩn

Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

## Nguyên văn

> "okay bây giờ mở request check giúp tôi, có vẻ từ khi nới hook, behavior của tdq-workflow có sai sot, như ở request vừa rồi ko tick plan. hãy check và phân tích và list ra cho tôi 10 hạn chế về nguy cơ gây sai behavior từ khi nới hook và report cho tôi"

- **Mục tiêu:**
  - Điều tra nguyên nhân gốc rễ việc bỏ sót tick checkbox plan trong request trước (`2026-11-19-0046-dong-rust-binary-hook`).
  - Phân tích toàn diện luồng nới lỏng hook từ các đợt tối ưu gần đây (R1–R3, mềm hóa gate trên Antigravity, đóng gói Rust binary).
  - Xác lập 10 hạn chế/nguy cơ kỹ thuật gây sai lệch behavior (Behavior Drift) làm giảm kỷ luật tự động của agent.
  - Xuất báo cáo Markdown chi tiết và Archify HTML phục vụ qua Tailscale Serve.
- **Phạm vi:**
  - `plugins/tdq-workflow-agy/hooks/scripts/` (`edit_gate.py`, `stop_gate.py`, `prompt_context.py`, `gate_guidance.py`).
  - Crate Rust `hooks/rust/tdq-dispatch/src/` (`events/pre_tool_use.rs`, `events/stop_streak.rs`, `protocol.rs`).
  - So sánh đối chiếu cơ chế chặn/nhắc giữa Python Engine và Rust Engine trên Antigravity.

## Hiểu & kiến thức

- **Bằng chứng thực tế từ request trước (`2026-11-19-0046-dong-rust-binary-hook`):**
  - Trong `docs/tdq/plan/2026-11-19-0046-dong-rust-binary-hook.md`, các task P1–P4 đã hoàn thành và tick `[x]`, nhưng ở mục `## Khuôn khối hợp đồng skill` có 3 task `T1.1`, `T3.1`, `T3.2` bị bỏ sót không tick (`- [ ]`).
  - Suốt quá trình sửa code và kết thúc lượt, hook không hề phát ra cảnh báo hay chặn đứng model.
- **Nguyên nhân gốc rễ 1: Mềm hóa gate trên Antigravity (`agy_hooks.py`):**
  - Trong Python `edit_gate.py`: `_tick_notify` chuyển `block` thành `remind` khi `is_agy() == True`, đồng thời điều kiện kiểm tra task `[~]` bị vô hiệu hóa trên AGY (`if not is_agy() and tick["exists"] and tick["has_doing"]:`).
  - Trong Python `stop_gate.py`: `TDQ:TICK` và `TDQ:LOG` bị chuyển từ `stop_block` thành `queue_remind` trên AGY để tránh làm gián đoạn lượt thực thi của Antigravity.
- **Nguyên nhân gốc rễ 2: Rust standalone binary (`tdq-dispatch`) chưa chuyển đổi đủ các gate kỷ luật:**
  - Rust `pre_tool_use.rs` chỉ kiểm tra 9 hard gates bảo mật cơ bản (`docs/tdq/state.json`, `git push`, git reset, remote script, `start_lsp`, `invoke_subagent`).
  - Rust hoàn toàn KHÔNG đọc nội dung file plan markdown để kiểm tra task `[~]` hay hash checksum, cũng không kiểm tra `TDQ:APPROVE` hay `TDQ:TEAM`.
  - Rust `stop_streak.rs` chỉ theo dõi streak dừng liên tiếp, không kiểm tra plan checkbox updates.
- **Hiện tượng Behavior Drift (Sai lệch hành vi):**
  - Khi thiếu áp lực chặn cơ học (Hard Gates), LLM có xu hướng tối ưu hóa tốc độ hoàn thành mà bỏ qua các bước kỷ luật phụ trợ (tick checkbox từng bước, ghi log từng turn).

## Hỏi đáp

- Không có điểm mờ cần hỏi thêm; yêu cầu đã rõ ràng: điều tra, phân tích, liệt kê 10 hạn chế/nguy cơ và lập báo cáo.
