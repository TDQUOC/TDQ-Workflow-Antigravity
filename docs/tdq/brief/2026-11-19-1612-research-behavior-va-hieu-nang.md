# Brief: Research & Đề xuất Kiến trúc Hook giữ đúng Behavior và Hiệu năng

Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

## Nguyên văn

> "okay commit và resreach và đề xuất phương án làm sao giữ đúng behavior và vẫn cố gắng keep performance giúp tôi"

- **Mục tiêu:**
  - Nghiên cứu chuyên sâu các phương án kiến trúc cho tầng hook TDQ trên Antigravity 2.0 nhằm khôi phục 100% kỷ luật behavior (khắc phục 10 hạn chế đã audit: `TDQ:TICK`, `PreInvocation`/`PostInvocation`, schema AGY 2.0, 22 cổng kỷ luật, `continuationActive`, `.tdq-runtime` thống nhất, chống vượt rào shell) trong khi vẫn duy trì độ trễ thực thi thấp (`<= 25 ms` trên hot-path).
- **Phạm vi khảo sát dự kiến:**
  - So sánh định lượng các phương án kiến trúc (Full-Rust 100% parity 22 mã, Hybrid 2 tầng Rust hot-path + Python cold-path, Persistent Sidecar/Daemon, và phân tầng cơ chế chặn cứng vs nhắc mềm theo rủi ro), kết hợp phân tích chi phí I/O & subprocess thực tế trong 13 script Python và crate Rust `tdq-dispatch`.
- **Điểm cần làm rõ:**
  - Chỉ dừng ở nghiên cứu & đề xuất phương án để user chốt, hay triển khai luôn trong cùng request; mức độ ưu tiên giữa tốc độ `< 25 ms` với độ trễ chấp nhận được ở các sự kiện hiếm (`SessionStart`, `Stop`, `PreInvocation`).

## Hiểu & kiến thức

- **Giới hạn nền tảng Antigravity 2.0 (`agy-customizations/docs/hooks.md:127-131, 428-429`):**
  - Antigravity chỉ hỗ trợ `type: "command"` chạy đồng bộ (*"Hooks run synchronously and block the agent loop"*), qua vỏ `cmd /c` (Windows) hoặc `sh -c` (Unix); không có HTTP hook hay chạy nền bất đồng bộ.
  - Chi phí vỏ `cmd.exe /c` gần như cố định (~`8–10 ms`/spawn). Đo trực tiếp (`test_rust_latency_benchmark.py`, N=30): Rust trực tiếp đạt **19,90 ms** (qua `cmd /c` **28,37 ms**); Python trực tiếp **190,21 ms** (qua `cmd /c` **199,36 ms**). Bản `dispatch.py` R1–R3 đạt **69,5–126,1 ms** (`bench_dispatch.py`), riêng launcher `py -3` tốn thêm **+17,62 ms/spawn** (`bench_hooks.json`).
- **Quy mô codebase & phân bố tần suất thực tế (`docs/tdq/research/2026-11-18-1346-scan-hook-anh-huong-runtime.md`, 120 transcript / 4 ngày):**
  - Tổng lưu lượng: `11.241` lời gọi model (`PreInvocation` + `PostInvocation`), `17.429` bước tool (`PreToolUse` + `PostToolUse`), `105` `SessionStart`, `60` `Stop` block. Trong `60` lượt dài (`>= 10` phút, tổng `2.377,38` phút), toàn bộ chi phí hook ước tính chỉ chiếm **`2,67%`** (`63,55` phút + `3,27` phút chờ deny), trong khi **`~74%`** thời lượng nằm ở model sinh (`46,42%`), chờ subagent (`20,00%`) và timeout API (`15,20%`).
  - Codebase Python hiện tại trong `plugins/tdq-workflow-agy/hooks/scripts/`: **5.634 dòng** trên 17 file (`_common.py` 1.280, `gate_guidance.py` 612, `prompt_context.py` 559, `session_start.py` 452, `stop_gate.py` 425, `edit_gate.py` 322, `bash_gate.py` 295, `read_gate.py` 282, `lsp_gate.py` 271, `search_gate.py` 271, `search_observe.py` 256, `dispatch.py` 247, `command_gate.py` 115, `luat_gon.py` 83, `ask_gate.py` 79, `subagent_dispatch_gate.py` 52, `post_invocation.py` 33).
  - Codebase Rust (`hooks/rust/tdq-dispatch/src/`): **1.502 dòng** trên 13 file — mới phủ ~25% logic và đang lệch schema AGY 2.0.
- **Điểm gãy khiến 2 đợt trước làm rơi behavior:**
  - `v0.100.0` (R1–R3) hạ cấp cứng thành nhắc mềm quá tay (`TDQ:TICK` do `STREAK_NGUONG=3` quá nhỏ gây 30 ca `tick_loop`; `TDQ:LOG` do chặn nhầm `docs/.staging*`; `Stop` thoát mù bằng `continuationActive=true` ở `stop_gate.py:300`).
  - `v0.101.0` (Rust) gắn trực tiếp binary thiếu tính năng vào toàn bộ 6 sự kiện trong `hooks.json` mà không fallback chọn lọc và không có Parity Test đủ 22 mã.
- **4 trục phương án sẽ phân tích & đối chiếu định lượng trong báo cáo:**
  1. **Phương án A — Hybrid 2 tầng (Rust Fast-Path Router ~90–95% lời gọi + Python Cold-Path Delegate ~5–10%):** Rust chuẩn hóa hoàn chỉnh schema AGY 2.0 để xử lý đường nóng file-based (`PreInvocation` mid-turn, `PostInvocation`, `PostToolUse`, `read_gate`, `edit_gate`, phần lớn `PreToolUse`) ở ~`20–28 ms`; chỉ gọi Python `dispatch.py` ở ca lạnh (`SessionStart`, `PreInvocation` đầu lượt user mới, `Stop` có active request, `rtk rewrite`, `tdq_team` phức tạp). Giữ 100% parity 22/22 cổng, độ trễ TB có trọng số thấp, không phải nhân đôi 5.634 dòng code.
  2. **Phương án B — Full-Rust 100% Parity:** Viết lại toàn bộ 5.634 dòng Python sang Rust. Nhanh nhất (~`25–30 ms` mọi sự kiện) nhưng phải bảo trì 2 codebase song song (Claude/Codex Python vs AGY Rust) — rủi ro Behavior Drift cao về dài hạn.
  3. **Phương án C — Persistent Local Sidecar / Daemon (Python thường trú + client CLI mỏng):** Tái dùng 100% code Python, bỏ nạp CPython VM nhưng vẫn tốn vỏ `cmd /c` + IPC (`~18–25 ms`) và phát sinh bài toán vòng đời daemon/zombie/stale code trên 3 OS (do AGY không có HTTP hook).
  4. **Phương án D — Chính sách "Siết Cổng Thông Minh" (Smart Hardening, kết hợp với A/B/C):** Giữ chặn cứng `TDQ:TICK` khi `0` hoặc `>1` `[~]`, nâng `STREAK_NGUONG` từ `3` → `8` + chặn `Stop` khi `plan_sha` đứng yên; khôi phục chặn cứng `TDQ:LOG` ở `Stop` (trừ sạch `docs/.staging*`); đổi `continuationActive` sang trần `MAX_STREAK=2` gắn `plan_sha`; bịt lỗ hổng shell mutator cho `APPROVE`/`TEAM`/`READONLY` (thêm `qc-tester`); bơm nhắc gọn sau compaction; khóa hồi quy bằng Golden Parity Suite `22/22` mã × `6` sự kiện.

## Hỏi đáp

- Không có điểm mơ hồ cản trở việc lập báo cáo nghiên cứu & đề xuất phương án (user muốn nghiên cứu sâu và nhận đề xuất kiến trúc rõ ràng trước khi quyết định triển khai ở request tiếp theo).
