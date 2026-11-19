# PLAN — Đóng gói Rust binary cho tầng hook và tích hợp kèm TDQ-Workflow Antigravity

Ngày: 2026-11-19 · Spec: ../spec/2026-11-19-0046-dong-rust-binary-hook.md (bản 1.0, ĐÃ DUYỆT) · Lane: full
Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md
Mode thực thi: subagent — các task chia theo 6 module độc lập không giao nhau (M1–M6), phân đợt song song giữa tầng Rust core và các patcher đóng gói (ĐỀ XUẤT, user chốt lúc duyệt)
Trạng thái plan: CHỜ DUYỆT

## Mục lục

- Quy tắc thi hành (áp cho mọi task)
- Thiết kế Trước vs Sau
- P1 — Hợp đồng dữ liệu 22 mã hướng dẫn & Nền tảng Crate Rust core
- P2 — 6 sự kiện Hook độc lập trong Crate Rust
- P3 — Đóng gói binary, cập nhật Patcher, Manifests & Bộ cài đặt
- P4 — Bộ kiểm thử vi phân 1-1, an toàn khóa tệp & độ trễ
- Cụm song song
- Luật file nóng (một file, nhiều task chạm)
- Khuôn khối hợp đồng skill
- Px — Log & test bắt buộc
- Definition of Done

## Quy tắc thi hành (áp cho mọi task)

1. Thứ tự phase là thứ tự phụ thuộc — không đảo.
2. Mỗi task: đánh `[~]` (hoặc `[>]` khi giao subagent) → viết test đỏ trước → code → test xanh → đổi sang `[x]` NGAY vào file này. Trạng thái checkbox: `[ ]` chưa làm · `[~]` đang làm · `[x]` xong.
3. Mỗi bước: `py -3 scripts/tdq_test.py vung-cham`; trọn bộ chỉ ở QC.
4. Lệnh nào chạm state của workflow phải có `TDQ_PROJECT_DIR=<thư mục tạm>` ngay trên chính lệnh đó.
5. QC FAIL → thêm task fix vào mục QC của file này (không cần duyệt lại), loop đến khi pass.
6. Không commit/push cho đến khi user yêu cầu.
7. Tuân thủ 6 mã cấm cơ học (ANTI-1 Fake Red, ANTI-2 Blind Assertion, ANTI-3 Dirty State Git, ANTI-4 Late Tick, ANTI-5 Raw Dump, ANTI-6 Broad Area) và `i18n_check.py`.

## Thiết kế Trước vs Sau

| Khía cạnh | Hiện trạng (Trước) | Thiết kế mới (Sau) |
|---|---|---|
| Luồng thực thi | Mỗi hook gọi qua trình thông dịch CPython (`python -X utf8 hooks/scripts/dispatch.py`), tốn chi phí nạp VM từ `45–55 ms` | Gọi thẳng Rust standalone binary `tdq-dispatch.exe` (Windows) hoặc `./bin/tdq-dispatch` (Unix), thời gian thực thi nội tại `2–4 ms` |
| Thành phần chạm | 17 tệp Python trong gói hook Antigravity, phụ thuộc CPython môi trường máy | Crate Rust độc lập `tdq-dispatch`, đóng sẵn binary tĩnh không phụ thuộc runtime bên ngoài, duy trì tệp Python làm dự phòng |
| Điểm nghẽn giải quyết | Tổng độ trễ hook khi qua vỏ `cmd.exe /c` mất `70–126 ms`, có nguy cơ lỗi môi trường Python | Kéo tổng thời gian thực thi qua `cmd.exe /c` xuống trung vị `14,75 ms`, loại bỏ rủi ro môi trường Python bị thiếu thư viện |

*Đối chiếu sơ đồ kiến trúc:* Tham chiếu `docs/tdq/spec/2026-11-19-0046-dong-rust-binary-hook-preview.html` và manifest đã duyệt (`current`). Đợt 1 xây dựng `M1_GUIDANCE_CONTRACT` và `M2_RUST_CORE`; Đợt 2 xây dựng `M3_RUST_EVENTS`; Đợt 3 xây dựng `M4_BUILD_PATCHERS` và `M5_INSTALL_PORTABILITY`; Đợt 4 khóa bộ kiểm thử `M6_TEST_SUITE`.

## P1 — Hợp đồng dữ liệu 22 mã hướng dẫn & Nền tảng Crate Rust core

- [x] **T1.1** (e10m) Trích xuất hợp đồng 22 mã hướng dẫn sang JSON dùng chung `tools/patches/gate_guidance.json` và đồng bộ `tools/patches/gate_guidance.py` — Test: `py -3 -c "import json; d=json.load(open('tools/patches/gate_guidance.json', encoding='utf-8')); assert len(d['guidance_codes'])==22 and len(d['lean_removed_codes'])==7"`
  - Chạm: `tools/patches/gate_guidance.json`, `tools/patches/gate_guidance.py`
  - Cần: không
  - Mục tiêu: cung cấp nguồn quy chiếu duy nhất (Single Source of Truth) cho bảng 22 mã cổng Antigravity, giúp Rust crate và Python dispatch đồng bộ 100%.
  - Vị trí neo: tệp mới `tools/patches/gate_guidance.json` và cập nhật hàm nạp dữ liệu trong `tools/patches/gate_guidance.py`.
  - Công cụ: Dùng Write cho `gate_guidance.json`; Dùng Edit cho `gate_guidance.py`.
  - Ràng buộc: thuần stdlib, dữ liệu JSON hợp lệ chuẩn UTF-8, không thêm dependency bên ngoài.
  - Đặc tả kỹ thuật:
    `gate_guidance.json` chứa cấu trúc `{ "hard_deny_codes": [...], "overwrite_codes": [...], "guidance_codes": { "<CODE>": { "chuyen_gi": "...", "vi_sao": "...", "lam_gi": "...", "bo_qua": "...", "model_hint": "..." } }, "lean_removed_codes": [...] }`.
  - Logic cốt lõi:
    1. Bước 1: Trích xuất toàn bộ từ điển `USER_CARDS`, `MODEL_HINTS`, `HARD_DENY_CODES`, `OVERWRITE_CODES`, `LEAN_REMOVED_CODES` từ `gate_guidance.py` ra `gate_guidance.json`.
    2. Bước 2: Bổ sung cơ chế tự động đọc từ `gate_guidance.json` trong `gate_guidance.py` nếu tệp tồn tại để bảo đảm tính nhất quán.
    3. Bước 3: Kiểm chứng cú pháp JSON và số lượng mã.
  - Ca góc hiểm & TDD:
    - Ca hiểm: tệp JSON thiếu trường, mã không có tiền tố `[TDQ:`, chuỗi rỗng.
    - Tiêu chí: `assert len(d['guidance_codes']) == 22` và `100%` mã có đủ 5 trường nội dung không rỗng.

- [x] **T1.2** (e15m) Khởi tạo Crate Rust `hooks/rust/tdq-dispatch/` với cấu hình Cargo.toml defender-safe và static CRT — Test: `cargo check --manifest-path hooks/rust/tdq-dispatch/Cargo.toml`
  - Chạm: `hooks/rust/tdq-dispatch/Cargo.toml`, `hooks/rust/tdq-dispatch/.cargo/config.toml`, `.gitignore`, `.graphifyignore`
  - Cần: T1.1
  - Mục tiêu: tạo cấu trúc dự án Rust chuẩn mực, cấu hình cờ biên dịch phòng ngừa cảnh báo nhầm của Defender và liên kết tĩnh thư viện CRT trên Windows MSVC.
  - Vị trí neo: thư mục mới `hooks/rust/tdq-dispatch/` và cập nhật `.gitignore`, `.graphifyignore`.
  - Công cụ: Dùng Write cho các tệp cấu hình mới; Dùng Edit cho `.gitignore`, `.graphifyignore`.
  - Ràng buộc: Rust edition 2021, thư viện phụ thuộc tối giản (`serde`, `serde_json`, `regex`), không dùng runtime async nặng.
  - Đặc tả kỹ thuật:
    `Cargo.toml` khai báo profile release: `opt-level = 3`, `lto = "thin"`, `codegen-units = 1`, `panic = "abort"`, `strip = "symbols"`.
    `.cargo/config.toml` trên target `x86_64-pc-windows-msvc`: `rustflags = ["-C", "target-feature=+crt-static"]`.
  - Logic cốt lõi:
    1. Bước 1: Tạo tệp `Cargo.toml` với thông tin gói `tdq-dispatch`, phiên bản `0.1.0`.
    2. Bước 2: Thiết lập cấu hình `.cargo/config.toml` với cờ `+crt-static`.
    3. Bước 3: Khai báo bỏ qua `hooks/rust/tdq-dispatch/target/` trong `.gitignore` và `.graphifyignore`.
  - Ca góc hiểm & TDD:
    - Ca hiểm: xung đột cờ biên dịch trên môi trường non-Windows.
    - Tiêu chí: `cargo check` hoàn thành với mã thoát 0.

- [x] **T1.3** (e20m) Hiện thực Module giao thức `src/protocol.rs`, bộ phân tích câu lệnh `src/command_parser.rs` và cơ chế khóa an toàn `src/lock.rs` — Test: `cargo test --manifest-path hooks/rust/tdq-dispatch/Cargo.toml --lib`
  - Chạm: `hooks/rust/tdq-dispatch/src/lib.rs`, `hooks/rust/tdq-dispatch/src/protocol.rs`, `hooks/rust/tdq-dispatch/src/command_parser.rs`, `hooks/rust/tdq-dispatch/src/lock.rs`
  - Cần: T1.2
  - Mục tiêu: cung cấp mô hình dữ liệu hook Antigravity, bộ bóc tách lệnh PowerShell/POSIX và cơ chế sidecar `.lock` locking với thời gian chờ 200 ms.
  - Vị trí neo: các tệp mã nguồn Rust mới dưới `hooks/rust/tdq-dispatch/src/`.
  - Công cụ: Dùng Write cho các tệp Rust mới.
  - Ràng buộc: xử lý lỗi phòng thủ triệt để, không hoảng loạn (`unwrap` mất an toàn), quản lý giải phóng khóa tự động qua trait `Drop`.
  - Đặc tả kỹ thuật:
    `struct HookPayload`, `struct HookDecision`, `struct SidecarLockGuard`.
    `fn parse_command_tokens(cmd: &str) -> Vec<String>`; `fn acquire_sidecar_lock(target_path: &Path, timeout: Duration) -> Result<SidecarLockGuard, LockError>`.
  - Logic cốt lõi:
    1. Bước 1 (`protocol.rs`): Định nghĩa các cấu trúc dữ liệu phản hồi hook Antigravity: `decision` (`allow`, `deny`), `explanation`, `user_markdown`, `arguments_overwrite`.
    2. Bước 2 (`command_parser.rs`): Phân tích cú pháp chuỗi lệnh loại bỏ here-strings PowerShell `@'...'@` và bóc tách các token thực thi để kiểm tra lệnh cấm.
    3. Bước 3 (`lock.rs`): Mở tệp `<target>.lock`, gọi cơ chế khóa chia sẻ/độc quyền với vòng lặp thử lại tối đa 200 ms. Tự động xóa hoặc nhả khóa khi guard ra khỏi phạm vi (RAII).
  - Ca góc hiểm & TDD:
    - Ca hiểm: lệnh chứa chuỗi nháy kép lồng nhau, tệp khóa bị tiến trình khác giữ quá hạn, đường dẫn tệp không tồn tại.
    - Tiêu chí: các bài unit test trong `src/lock.rs` và `src/command_parser.rs` vượt qua 100%.

- [x] **T1.4** (e15m) Hiện thực Module lưu trữ `src/storage.rs` quản lý `.tdq-runtime/`, bộ đệm `state.json`, CCR store và ghi nguyên tử `atomic_write` — Test: `cargo test --manifest-path hooks/rust/tdq-dispatch/Cargo.toml --lib storage`
  - Chạm: `hooks/rust/tdq-dispatch/src/storage.rs`
  - Cần: T1.3
  - Mục tiêu: quản lý bộ nhớ đệm trạng thái phiên, ghi tệp nhật ký nguyên tử (atomic write qua file tạm) và lưu trữ khối dữ liệu lớn CCR (`>32KB`/`>=200` dòng).
  - Vị trí neo: tệp mới `hooks/rust/tdq-dispatch/src/storage.rs`.
  - Công cụ: Dùng Write cho `storage.rs`.
  - Ràng buộc: chỉ đọc tệp `docs/tdq/state.json`, không ghi đè `state.json`; ghi dữ liệu runtime qua cơ chế `tempfile + rename`.
  - Đặc tả kỹ thuật:
    `fn read_state_json(workspace_root: &Path) -> Option<TdqState>`;
    `fn atomic_write_file(target_path: &Path, content: &[u8]) -> std::io::Result<()>`;
    `fn append_jsonl(log_path: &Path, row: &serde_json::Value) -> std::io::Result<()>`;
    `fn check_and_store_ccr(content: &str, storage_dir: &Path) -> Option<CcrReference>`.
  - Logic cốt lõi:
    1. Bước 1: Đọc và giải mã an toàn tệp `state.json` lấy các thông tin `phase`, `lane`, `muc_gat`, `spec_approved`.
    2. Bước 2: Hiện thực hàm `atomic_write_file` tạo tệp tạm `.tmp.<uuid>` cùng thư mục và thực hiện đổi tên nguyên tử thay thế tệp đích.
    3. Bước 3: Hiện thực kiểm tra kích thước văn bản phản hồi công cụ; nếu vượt 32 KB hoặc 200 dòng thì lưu mã băm SHA256 vào `.tdq-runtime/ccr/` và trả về thẻ tham chiếu.
  - Ca góc hiểm & TDD:
    - Ca hiểm: thư mục đích chưa tồn tại, tệp JSON trạng thái bị định dạng sai, dung lượng đĩa đầy.
    - Tiêu chí: test ghi nguyên tử và đọc `state.json` giả lập thành công không có lỗi.

**Xong P1 khi**: Crate Rust `tdq-dispatch` biên dịch sạch và vượt qua 100% unit test của các module nền tảng (`protocol`, `command_parser`, `lock`, `storage`), `tools/patches/gate_guidance.json` hợp lệ.

## P2 — 6 sự kiện Hook độc lập trong Crate Rust

- [x] **T2.1** (e20m) Hiện thực sự kiện `SessionStart` thuần Rust — Test: `cargo test --manifest-path hooks/rust/tdq-dispatch/Cargo.toml --lib session_start`
  - Chạm: `hooks/rust/tdq-dispatch/src/events/session_start.rs`, `hooks/rust/tdq-dispatch/src/events/mod.rs`
  - Cần: T1.4
  - Mục tiêu: xử lý khởi động phiên làm việc thuần Rust 100% không spawn Python nền (dọn rác `.tdq-runtime` cũ hơn 7 ngày, nạp `state.json`, nạp luật gọn `luat_gon`, kiểm tra `.tdq-san-sang.json` và phát cảnh báo `[TDQ:SETUP]` / `[TDQ:SEARCH]`).
  - Vị trí neo: tệp mới `hooks/rust/tdq-dispatch/src/events/session_start.rs`.
  - Công cụ: Dùng Write cho `session_start.rs`.
  - Ràng buộc: thực thi nhanh dưới 5 ms, không gọi bất kỳ tiến trình con bên ngoài.
  - Đặc tả kỹ thuật:
    `fn handle_session_start(payload: &HookPayload, workspace_root: &Path) -> HookDecision`.
  - Logic cốt lõi:
    1. Bước 1: Quét thư mục `.tdq-runtime/`, xóa các tệp có thời gian sửa đổi cũ hơn 7 ngày.
    2. Bước 2: Đọc `docs/tdq/state.json`. Nếu tệp trạng thái tồn tại, nạp luật rút gọn từ `skills/tdq-build/references/rules/chung.md` tương ứng với mức gắt `muc_gat`.
    3. Bước 3: Kiểm tra sự tồn tại của tệp `.tdq-san-sang.json`. Nếu chưa sẵn sàng, xuất thông điệp `[TDQ:SETUP]` và hướng dẫn `[TDQ:SEARCH]`.
  - Ca góc hiểm & TDD:
    - Ca hiểm: thư mục `.tdq-runtime` chưa tồn tại, tệp luật bị xóa, dự án mới chưa mở request.
    - Tiêu chí: unit test mô phỏng phiên chưa setup trả về thông điệp `[TDQ:SETUP]` chính xác.

- [x] **T2.2** (e15m) Hiện thực sự kiện `UserPromptSubmit` và `Notification` trong Rust — Test: `cargo test --manifest-path hooks/rust/tdq-dispatch/Cargo.toml --lib prompt_notification`
  - Chạm: `hooks/rust/tdq-dispatch/src/events/user_prompt_submit.rs`, `hooks/rust/tdq-dispatch/src/events/notification.rs`
  - Cần: T2.1
  - Mục tiêu: xử lý nhắc việc theo giai đoạn request và ghi nhận nhật ký thông báo sự kiện nền.
  - Vị trí neo: các tệp mới `user_prompt_submit.rs` và `notification.rs`.
  - Công cụ: Dùng Write cho 2 tệp mới.
  - Ràng buộc: không chặn tiến trình người dùng, phản hồi ngay lập tức.
  - Đặc tả kỹ thuật:
    `fn handle_user_prompt_submit(payload: &HookPayload, workspace_root: &Path) -> HookDecision`;
    `fn handle_notification(payload: &HookPayload, workspace_root: &Path) -> HookDecision`.
  - Logic cốt lõi:
    1. Bước 1: Kiểm tra `phase` trong `state.json`. Nếu ở giai đoạn yêu cầu tuân thủ luật gọn, chèn dòng nhắc nhở vào `additionalContext` hoặc `user_markdown`.
    2. Bước 2: Ghi nhận thông báo vào nhật ký giám sát nếu cần thiết và trả về quyết định `allow`.
  - Ca góc hiểm & TDD:
    - Ca hiểm: prompt rỗng, thông báo không có nội dung.
    - Tiêu chí: trả về mã quyết định cho phép `allow` trên mọi ca kiểm thử.

- [x] **T2.3** (e25m) Hiện thực sự kiện `PreToolUse` trong Rust — Test: `cargo test --manifest-path hooks/rust/tdq-dispatch/Cargo.toml --lib pre_tool_use`
  - Chạm: `hooks/rust/tdq-dispatch/src/events/pre_tool_use.rs`
  - Cần: T2.1
  - Mục tiêu: kiểm tra và thực thi 9 cổng chặn an toàn, phân tích câu lệnh dòng lệnh, cơ chế ân xá lần 1 cho tìm kiếm và tự động ghi đè tham số thiếu (`overwrite` cho LSP và Subagent Workspace).
  - Vị trí neo: tệp mới `hooks/rust/tdq-dispatch/src/events/pre_tool_use.rs`.
  - Công cụ: Dùng Write cho `pre_tool_use.rs`.
  - Ràng buộc: bám sát hành vi của 9 cổng chặn an toàn (`APPROVE`, `GIT`, `TEAM`, `STATE`, `READONLY`, `VUNG`, `ZERO-POPUP`, `SUBAGENT`, `UNFINISHED`), tự điền `language_id` thiếu cho `start_lsp`.
  - Đặc tả kỹ thuật:
    `fn handle_pre_tool_use(payload: &HookPayload, workspace_root: &Path) -> HookDecision`.
  - Logic cốt lõi:
    1. Bước 1: Trích xuất tên công cụ và đối số. Kiểm tra danh sách lệnh cấm phá hủy git (`git push`, `git reset --hard`) hoặc vượt sandbox.
    2. Bước 2: Kiểm tra công cụ `start_lsp`. Nếu thiếu `language_id`, tự động dò ngôn ngữ và trả về quyết định `overwrite`.
    3. Bước 3: Nếu gọi subagent, tự động điền `Workspace="inherit"` nếu chưa được thiết lập.
    4. Bước 4: Kiểm tra hành vi tìm kiếm mã nguồn; nếu vi phạm tầng tìm kiếm lần 1 thì xuất thẻ hướng dẫn 4 phần, nếu vi phạm liên tiếp lần 2 thì trả về `deny`.
  - Ca góc hiểm & TDD:
    - Ca hiểm: đối số công cụ là chuỗi JSON lồng nhau, lệnh PowerShell alias (`curl`, `wget`, `cat`), công cụ không xác định.
    - Tiêu chí: chặn đúng 100% các câu lệnh nguy hiểm trong bộ kiểm thử chuẩn.

- [x] **T2.4** (e20m) Hiện thực sự kiện `PostToolUse` và `StopStreak` trong Rust — Test: `cargo test --manifest-path hooks/rust/tdq-dispatch/Cargo.toml --lib post_tool_use`
  - Chạm: `hooks/rust/tdq-dispatch/src/events/post_tool_use.rs`, `hooks/rust/tdq-dispatch/src/events/stop_streak.rs`
  - Cần: T2.3
  - Mục tiêu: ghi nhận nhật ký lượt công cụ (`.tdq-search.jsonl`, `.tdq-read.jsonl`, `turns-<sid>.jsonl`), nén lưu trữ CCR store và phát hiện vòng lặp dừng liên tiếp.
  - Vị trí neo: các tệp mới `post_tool_use.rs` và `stop_streak.rs`.
  - Công cụ: Dùng Write cho 2 tệp mới.
  - Ràng buộc: sử dụng sidecar lock khi ghi tệp nhật ký, không làm chậm chu kỳ thực thi công cụ.
  - Đặc tả kỹ thuật:
    `fn handle_post_tool_use(payload: &HookPayload, workspace_root: &Path) -> HookDecision`;
    `fn handle_stop_streak(payload: &HookPayload, workspace_root: &Path) -> HookDecision`.
  - Logic cốt lõi:
    1. Bước 1: Ghi nhận công cụ tìm kiếm hoặc đọc tệp vào các tệp nhật ký tương ứng.
    2. Bước 2: Đo dung lượng kết quả phản hồi của công cụ; nếu vượt 32 KB hoặc 200 dòng thì chuyển sang lưu tại kho CCR và trả về thông báo tóm tắt.
    3. Bước 3: Đọc và cập nhật số đếm dừng liên tiếp trong `stop_streak.json`. Nếu vượt ngưỡng 3 lần, xuất cảnh báo can thiệp.
  - Ca góc hiểm & TDD:
    - Ca hiểm: kết quả công cụ rỗng, tệp `stop_streak.json` bị hỏng cấu trúc.
    - Tiêu chí: ghi nhận nhật ký chính xác và nén CCR thành công.

- [x] **T2.5** (e15m) Hiện thực điểm vào `src/main.rs`, điều phối CLI `--event <Event>` và cơ chế dự phòng `TDQ_HOOK_ENGINE=python` — Test: `cargo test --manifest-path hooks/rust/tdq-dispatch/Cargo.toml --bin tdq-dispatch`
  - Chạm: `hooks/rust/tdq-dispatch/src/main.rs`
  - Cần: T2.1, T2.2, T2.3, T2.4
  - Mục tiêu: hoàn thiện điểm vào nhị phân của binary `tdq-dispatch`, phân tích tham số dòng lệnh `--event`, đọc stdin UTF-8, gọi router tương ứng và xử lý dự phòng tự động sang `dispatch.py` khi có yêu cầu.
  - Vị trí neo: tệp `hooks/rust/tdq-dispatch/src/main.rs`.
  - Công cụ: Dùng Write cho `main.rs`.
  - Ràng buộc: luôn trả về mã thoát 0 cho máy chủ Antigravity; in kết quả quyết định ra stdout dạng JSON.
  - Đặc tả kỹ thuật:
    `fn main()`; kiểm tra biến môi trường `std::env::var("TDQ_HOOK_ENGINE") == Ok("python")`; gọi `dispatch_python_fallback()`.
  - Logic cốt lõi:
    1. Bước 1: Đọc tham số `--event`.
    2. Bước 2: Đọc toàn bộ stdin vào bộ đệm chuỗi UTF-8.
    3. Bước 3: Nếu phát hiện cờ môi trường `TDQ_HOOK_ENGINE=python`, chuyển toàn bộ dữ liệu stdin sang tiến trình con `python -X utf8 hooks/scripts/dispatch.py` và xuất nguyên văn kết quả.
    4. Bước 4: Nếu chạy native Rust, chuyển tiếp luồng dữ liệu vào router sự kiện tương ứng và in kết quả ra stdout.
  - Ca góc hiểm & TDD:
    - Ca hiểm: tham số `--event` không hợp lệ, stdin rỗng, không tìm thấy tiến trình Python khi fallback.
    - Tiêu chí: binary thực thi thành công và trả về JSON chuẩn xác trên cả 6 sự kiện.

**Xong P2 khi**: Crate Rust `tdq-dispatch` hoàn thành toàn bộ 6 sự kiện hook, biên dịch nhị phân `tdq-dispatch.exe` thành công và vượt qua trọn bộ bài kiểm thử đơn vị nội bộ.

## P3 — Đóng gói binary, cập nhật Patcher, Manifests & Bộ cài đặt

- [x] **T3.1** (e20m) Cập nhật các patcher `tools/patches/agy_manifests.py`, `tools/patches/agy_hooks.py`, `tools/patches/agy_dispatch.py` và build script `tools/build_agy_plugin.py` — Test: `py -3 tools/build_agy_plugin.py && agy plugin validate plugins/tdq-workflow-agy --strict`
  - Chạm: `tools/build_agy_plugin.py`, `tools/patches/agy_manifests.py`, `tools/patches/agy_hooks.py`, `tools/patches/agy_dispatch.py`
  - Cần: T2.5
  - Mục tiêu: tự động gọi `cargo build --release`, chép binary vào `plugins/tdq-workflow-agy/bin/`, cập nhật `hooks.json` trỏ vào binary chuẩn cú pháp OS (`bin\tdq-dispatch.exe` trên Windows, `./bin/tdq-dispatch` trên Unix) và kiểm tra tính toàn vẹn của plugin.
  - Vị trí neo: hàm `build()` trong `tools/build_agy_plugin.py` và các hàm tạo hook trong `tools/patches/agy_manifests.py`.
  - Công cụ: Dùng Edit cho các tệp Python trên.
  - Ràng buộc: kiểm tra nghiêm ngặt `agy plugin validate --strict` đạt 0 cảnh báo.
  - Đặc tả kỹ thuật:
    `def build_rust_binary(repo_root: Path, target_bin_dir: Path) -> Path`; cập nhật lệnh hook trong `hooks.json`.
  - Logic cốt lõi:
    1. Bước 1: Trong `tools/build_agy_plugin.py`, thêm bước gọi `cargo build --release` cho crate `hooks/rust/tdq-dispatch/`.
    2. Bước 2: Tạo thư mục `plugins/tdq-workflow-agy/bin/` và chép binary vừa biên dịch vào.
    3. Bước 3: Cập nhật `agy_manifests.py` sinh `hooks.json` dùng `bin\tdq-dispatch.exe --event <Event>` trên Windows và `./bin/tdq-dispatch --event <Event>` trên Unix.
    4. Bước 4: Chạy kiểm định plugin `agy plugin validate --strict`.
  - Ca góc hiểm & TDD:
    - Ca hiểm: máy chưa cài đặt cargo lúc build (phải báo lỗi rõ ràng hoặc dùng prebuilt binary).
    - Tiêu chí: `agy plugin validate --strict` trả về mã thoát 0 và danh sách `findings` rỗng.

- [x] **T3.2** (e15m) Cập nhật bộ cài đặt `tools/install_agy_plugin.py`, `install.py`, `install.ps1`, `install.sh` và `scripts/tdq_checkportable.py` — Test: `py -3 scripts/tdq_checkportable.py`
  - Chạm: `tools/install_agy_plugin.py`, `install.py`, `install.ps1`, `install.sh`, `scripts/tdq_checkportable.py`
  - Cần: T3.1
  - Mục tiêu: tự động phát hiện hệ điều hành khi cài đặt, chép đúng binary tương ứng vào thư mục cài đặt `~/.gemini/config/plugins/tdq-workflow-agy`, gán quyền thực thi trên Unix và tự động chuyển về script Python dự phòng nếu môi trường không có binary.
  - Vị trí neo: các hàm cài đặt plugin trong `tools/install_agy_plugin.py`, `install.py`, `install.ps1`, `install.sh` và hàm kiểm tra trong `scripts/tdq_checkportable.py`.
  - Công cụ: Dùng Edit cho các tệp trên.
  - Ràng buộc: không làm vỡ các kịch bản cài đặt tự động hiện hành; kiểm tra tính khả chuyển đạt mã thoát 0.
  - Đặc tả kỹ thuật:
    Hàm chọn binary: `get_platform_binary_name() -> str`; hàm cấu hình hook: `ensure_hook_engine(plugin_dir: Path) -> None`.
  - Logic cốt lõi:
    1. Bước 1: Xác định OS (`windows`, `linux`, `darwin`).
    2. Bước 2: Chọn tệp binary phù hợp từ thư mục `bin/` và đổi tên thành `tdq-dispatch.exe` (Windows) hoặc `tdq-dispatch` (Unix).
    3. Bước 3: Nếu trên Unix, cấp quyền `chmod +x`.
    4. Bước 4: Cập nhật kiểm tra khả chuyển `tdq_checkportable.py` công nhận binary nhúng trong plugin.
  - Ca góc hiểm & TDD:
    - Ca hiểm: thiếu quyền ghi thư mục bin, hệ điều hành không xác định.
    - Tiêu chí: `tdq_checkportable.py` hoàn thành với mã thoát 0.

- [x] **T3.3** (e15m) Thiết lập GitHub Actions workflow `.github/workflows/build-rust-hooks.yml` — Test: `py -3 -c "import yaml; yaml.safe_load(open('.github/workflows/build-rust-hooks.yml'))"`
  - Chạm: `.github/workflows/build-rust-hooks.yml`
  - Cần: T3.1
  - Mục tiêu: tự động biên dịch ma trận 3 hệ điều hành (Windows x86_64, Linux x86_64 musl, macOS arm64) trên hạ tầng CI và tải lên các bản phát hành nhị phân.
  - Vị trí neo: tệp mới `.github/workflows/build-rust-hooks.yml`.
  - Công cụ: Dùng Write cho tệp workflow.
  - Ràng buộc: YAML hợp lệ chuẩn GitHub Actions, sử dụng cache cargo để tối ưu thời gian build.
  - Đặc tả kỹ thuật:
    Matrix: `[{ os: windows-latest, target: x86_64-pc-windows-msvc }, { os: ubuntu-latest, target: x86_64-unknown-linux-musl }, { os: macos-latest, target: aarch64-apple-darwin }]`.
  - Logic cốt lõi:
    1. Bước 1: Thiết lập sự kiện kích hoạt khi có thay đổi trong `hooks/rust/tdq-dispatch/**`.
    2. Bước 2: Cài đặt toolchain Rust tương ứng với từng target.
    3. Bước 3: Chạy `cargo build --release` và đóng gói binary thành artifacts.
  - Ca góc hiểm & TDD:
    - Ca hiểm: lỗi liên kết thư viện musl trên Ubuntu.
    - Tiêu chí: cú pháp YAML hợp lệ, cấu hình ma trận đầy đủ 3 nền tảng.

**Xong P3 khi**: Plugin Antigravity được biên dịch với binary Rust sẵn sàng trong `bin/`, `agy plugin validate --strict` đạt 0 cảnh báo, bộ cài đặt và kịch bản CI sẵn sàng.

## P4 — Bộ kiểm thử vi phân 1-1, an toàn khóa tệp & độ trễ

- [x] **T4.1** (e20m) Xây dựng bài kiểm thử vi phân `tests/test_rust_dispatch_parity.py` đối chiếu 100% kết quả giữa Rust và Python — Test: `py -3 -m pytest tests/test_rust_dispatch_parity.py -q`
  - Chạm: `tests/test_rust_dispatch_parity.py`
  - Cần: T3.1
  - Mục tiêu: thực hiện kiểm thử vi phân (differential testing) bằng cách gửi cùng một tập payload đầu vào cho cả `tdq-dispatch.exe` và `dispatch.py`, so sánh từng trường dữ liệu JSON đầu ra để chứng minh tương đương hành vi 1-1.
  - Vị trí neo: tệp mới `tests/test_rust_dispatch_parity.py`.
  - Công cụ: Dùng Write cho tệp kiểm thử mới.
  - Ràng buộc: kiểm tra bao quát cả 6 sự kiện hook và 22 mã hướng dẫn.
  - Đặc tả kỹ thuật:
    `def test_differential_all_events(event_name, mock_payload)`: so sánh `decision`, `explanation`, `user_markdown`.
  - Logic cốt lõi:
    1. Bước 1: Tạo bộ dữ liệu thử nghiệm chuẩn cho 6 sự kiện hook (`SessionStart`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `StopStreak`, `Notification`).
    2. Bước 2: Thực thi lần lượt qua binary Rust và script Python với cùng tham số môi trường.
    3. Bước 3: Khẳng định tính tương đồng tuyệt đối trên các trường dữ liệu cốt lõi.
  - Ca góc hiểm & TDD:
    - Ca hiểm: sai lệch khoảng trắng hoặc dấu phân cách dòng, thứ tự các trường trong JSON.
    - Tiêu chí: 100% các ca kiểm thử đối chiếu đều vượt qua.

- [x] **T4.2** (e15m) Xây dựng bài kiểm thử an toàn khóa tệp đa tiến trình `tests/test_rust_lock_safety.py` — Test: `py -3 -m pytest tests/test_rust_lock_safety.py -q`
  - Chạm: `tests/test_rust_lock_safety.py`
  - Cần: T3.1
  - Mục tiêu: kiểm chứng cơ chế sidecar lock trên hệ thống tệp Windows NTFS không gây ra lỗi xung đột `ERROR_LOCK_VIOLATION` (`os error 33`) khi có nhiều tiến trình ghi đồng thời.
  - Vị trí neo: tệp mới `tests/test_rust_lock_safety.py`.
  - Công cụ: Dùng Write cho tệp kiểm thử mới.
  - Ràng buộc: chạy thử nghiệm ít nhất 20 tiến trình con thực thi đồng thời.
  - Đặc tả kỹ thuật:
    `def test_concurrent_sidecar_locks()`: khởi tạo 20 tiến trình con gọi `tdq-dispatch` ghi nhật ký cùng lúc vào thư mục tạm.
  - Logic cốt lõi:
    1. Bước 1: Khởi tạo 20 tiến trình con gọi hook `PostToolUse` đồng thời vào cùng một thư mục phiên tạm.
    2. Bước 2: Chờ toàn bộ tiến trình kết thúc và kiểm tra mã thoát của từng tiến trình (phải là 0).
    3. Bước 3: Đọc tệp nhật ký `.jsonl` tổng hợp, đếm số dòng để đảm bảo không bị mất mát bản ghi.
  - Ca góc hiểm & TDD:
    - Ca hiểm: deadlock giữa các tiến trình, tệp nhật ký bị ghi đè cụt lủn.
    - Tiêu chí: không có lỗi `os error 33`, số dòng nhật ký ghi lại đúng bằng 20.

- [x] **T4.3** (e15m) Xây dựng bài kiểm thử hiệu năng và độ trễ `tests/test_rust_latency_benchmark.py` — Test: `py -3 -m pytest tests/test_rust_latency_benchmark.py -q -s`
  - Chạm: `tests/test_rust_latency_benchmark.py`
  - Cần: T3.1
  - Mục tiêu: đo kiểm thời gian thực thi của hook Rust khi gọi trực tiếp và khi gọi qua vỏ `cmd.exe /c`, so sánh với phiên bản Python và ghi nhận báo cáo số liệu.
  - Vị trí neo: tệp mới `tests/test_rust_latency_benchmark.py`.
  - Công cụ: Dùng Write cho tệp kiểm thử mới.
  - Ràng buộc: đo đạc tối thiểu 30 lần lặp để tính giá trị trung vị (median) đáng tin cậy.
  - Đặc tả kỹ thuật:
    `def test_measure_hook_latency()`: đo thời gian chạy của `cmd /c bin\tdq-dispatch.exe --event SessionStart` vs `cmd /c python -X utf8 dispatch.py --event SessionStart`.
  - Logic cốt lõi:
    1. Bước 1: Khởi động vòng lặp đo đạc 30 lượt cho từng lệnh.
    2. Bước 2: Tính toán giá trị trung vị, phân vị 95 (P95) và độ lệch chuẩn.
    3. Bước 3: Xuất kết quả đối sánh hiệu năng ra màn hình và kiểm tra đạt mục tiêu mềm `<= 25 ms` qua `cmd.exe /c`.
  - Ca góc hiểm & TDD:
    - Ca hiểm: biến động tải CPU bất thường làm sai lệch kết quả đo.
    - Tiêu chí: trung vị đo được ghi nhận rõ ràng, khẳng định tốc độ cải thiện vượt trội so với bản Python.

**Xong P4 khi**: Toàn bộ các bài kiểm thử vi phân, kiểm thử an toàn khóa tệp và đo kiểm độ trễ đều hoàn tất và cho kết quả xanh.

## Cụm song song

- **Cụm 1 (Độc lập nền tảng):** Task T1.1 (`gate_guidance.json`) và T1.2 (`Cargo.toml`, defender-safe) có thể chạy độc lập.
- **Cụm 2 (Rust events):** Các task T2.1 (`SessionStart`), T2.2 (`UserPromptSubmit`/`Notification`), T2.3 (`PreToolUse`), T2.4 (`PostToolUse`/`StopStreak`) thao tác trên các file mã nguồn Rust riêng biệt trong thư mục `src/events/`, có thể giao cho các subagent độc lập sau khi hoàn thành P1.
- **Cụm 3 (Kiểm thử & Đóng gói):** Task T3.3 (GitHub Actions CI workflow) có thể triển khai song song với T3.1 và T3.2.

## Luật file nóng (một file, nhiều task chạm)

- `hooks/rust/tdq-dispatch/src/main.rs`: Chỉ được chỉnh sửa tại task T2.5 (một chủ ghi duy nhất).
- `tools/build_agy_plugin.py`: Chỉ được chỉnh sửa tại task T3.1 (một chủ ghi duy nhất).
- `tools/install_agy_plugin.py`: Chỉ được chỉnh sửa tại task T3.2 (một chủ ghi duy nhất).
- Các task trong P1 và P2 thao tác trên các file lá độc lập không giao nhau, tuân thủ nguyên tắc không tranh chấp vùng ghi file.

## Khuôn khối hợp đồng skill

- [ ] **T1.1** Trích xuất hợp đồng 22 mã hướng dẫn sang JSON dùng chung — Test: `py -3 -c "import json; d=json.load(open('tools/patches/gate_guidance.json', encoding='utf-8')); assert len(d['guidance_codes'])==22"`
  - Dùng: `tdq-conventions`
  - Để: tuân thủ chuẩn 3 tầng ngôn ngữ `i18n_check.py`, đặt mã cho chuỗi tiếng Việt người dùng thấy và chuỗi máy tiếng Anh, nạp skill TRƯỚC bước đỏ
  - Ra: `tools/patches/gate_guidance.json` sạch `i18n_check.py` và chuẩn hóa hợp đồng dữ liệu
  - Kiểm: `py -3 scripts/i18n_check.py tools/patches/gate_guidance.py`
  - Không dùng cho: chỉnh sửa các tài liệu quy tắc trong `skills/`

- [ ] **T3.1** Cập nhật các patcher và build script đóng gói plugin Antigravity — Test: `agy plugin validate plugins/tdq-workflow-agy --strict`
  - Dùng: `agy-customizations`
  - Để: áp dụng đúng chuẩn cú pháp lệnh hook trên Windows (`cmd /c` với `bin\tdq-dispatch.exe`) và Unix (`sh -c` với `./bin/tdq-dispatch`), nạp skill TRƯỚC bước đỏ
  - Ra: `plugins/tdq-workflow-agy/hooks.json` đạt chuẩn kiểm định nghiêm ngặt
  - Kiểm: `agy plugin validate plugins/tdq-workflow-agy --strict`
  - Không dùng cho: cấu hình plugin của các host khác ngoài Antigravity

- [ ] **T3.2** Cập nhật bộ cài đặt và kiểm tra tính khả chuyển — Test: `py -3 scripts/tdq_checkportable.py`
  - Dùng: `tdq-checkportable`
  - Để: kiểm chứng cấu hình nhúng binary không gây rò rỉ mã nguồn build tạm và giữ gói plugin khả chuyển, nạp skill TRƯỚC bước đỏ
  - Ra: báo cáo kiểm tra khả chuyển đạt mã thoát 0
  - Kiểm: `py -3 scripts/tdq_checkportable.py`
  - Không dùng cho: đóng gói bộ cài cho Claude Code hoặc Codex

## Px — Log & test bắt buộc

- [x] **Tx.1** (e5m) Log service bật qua cờ môi trường `TDQ_DEBUG=1` in stderr, mặc định chạy yên lặng — Test: `cargo test --manifest-path hooks/rust/tdq-dispatch/Cargo.toml --lib`
- [x] **Tx.2** (e10m) Unit test cho từng thành phần chạy bằng một câu lệnh duy nhất — Test: `cargo test --manifest-path hooks/rust/tdq-dispatch/Cargo.toml && py -3 -m pytest tests/test_rust_dispatch_parity.py tests/test_rust_lock_safety.py tests/test_rust_latency_benchmark.py -q`

## Definition of Done

Trỏ về §6 của spec. Liệt kê lại từng hạng mục QC + lệnh kiểm, MỖI DÒNG MỘT Ô TICK:

- [x] Q1 Kiểm tra cú pháp tài liệu doc_lint — `py -3 scripts/doc_lint.py docs/tdq/brief/2026-11-19-0046-dong-rust-binary-hook.md docs/tdq/spec/2026-11-19-0046-dong-rust-binary-hook.md docs/tdq/plan/2026-11-19-0046-dong-rust-binary-hook.md`
- [x] Q2 Biên dịch crate Rust trên Windows — `cargo build --manifest-path hooks/rust/tdq-dispatch/Cargo.toml --release`
- [x] Q3 Tương thích chuẩn hook Antigravity — `agy plugin validate plugins/tdq-workflow-agy --strict`
- [x] Q4 Kiểm thử đối chiếu vi phân 1-1 — `py -3 -m pytest tests/test_rust_dispatch_parity.py -q`
- [x] Q5 An toàn khóa tệp đa tiến trình — `py -3 -m pytest tests/test_rust_lock_safety.py -q`
- [x] Q6 Cơ chế dự phòng khi thiếu binary — `py -3 -c "import os, subprocess; env=dict(os.environ, TDQ_HOOK_ENGINE='python'); res=subprocess.run(['plugins/tdq-workflow-agy/bin/tdq-dispatch.exe', '--event', 'SessionStart'], input='{}', text=True, capture_output=True, env=env); assert res.returncode==0"`
- [x] Q7 Mục tiêu độ trễ hook đường nóng — `py -3 -m pytest tests/test_rust_latency_benchmark.py -q -s`
