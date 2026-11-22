# BRIEF — Cập nhật hook cho phép thao tác git khi người dùng duyệt
Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

Ngày: 2026-11-22 · Mã yêu cầu: 2026-11-22-0023-hook-duyet-thao-tac-git · Lane: full · Nhánh đích: feature/hook-duyet-thao-tac-git (tách từ dev sau khi duyệt spec do hook v0.103.1 đang chặn `git switch -c` trước `spec_approved`)

## Nguyên văn

> hi tôi muốn mở request update lại hook sẽ cho phép thao tác git khi được người dùng cho phép hoặc duyệt

### Đọc hiểu bước đầu

- **Mục tiêu:** Cập nhật cơ chế hook bảo vệ lệnh git (`tdq-dispatch` Rust và đồng bộ hook Python) để thay vì chặn cứng vô điều kiện, hook cho phép thực thi thao tác git an toàn khi có sự cho phép hoặc duyệt xác thực từ người dùng.
- **Phạm vi dự kiến:** Tầng hook Rust (`hooks/rust/tdq-dispatch/src/command_parser.rs`, `pre_tool_use.rs`, `user_prompt_submit.rs`, `pre_invocation.rs`, `storage.rs`), tầng hook Python tương ứng (`hooks/scripts/prompt_context.py`, `bash_gate.py`, `edit_gate.py`, `agy_pretooluse_gate.py`, `tools/patches/agy_hooks.py`, `tools/patches/gate_guidance.json`), kiểm thử Rust/Python, tài liệu luật và gói plugin `plugins/tdq-workflow-agy/`.
- **Điểm cần làm rõ:** Đã giải đáp trọn vẹn ở vòng phỏng vấn 1 (`## Hỏi đáp`).

## Hiểu & kiến thức

### Năng lực dùng được

Phân vân → DÙNG. Kiểm kê ngày 2026-11-22: 42 skill trên đĩa (23 giữ lại sau lọc, 19 ẩn khác lĩnh vực), cộng các skill built-in trong context. Không xoá bảng này kể cả khi không có dòng DÙNG nào.

| Skill | Nguồn | Phán quyết | Dùng ở đâu / Lý do loại |
|---|---|---|---|
| tdq-intake, tdq-spec, tdq-plan, tdq-build, tdq-conventions, tdq-setup, tdq-status, tdq-check-status, tdq-lean, tdq-checkportable | plugin:tdq-workflow / plugin:tdq-workflow-agy | NỀN | Luồng TDQ Workflow đang chạy |
| Đã xét 32 skill khác (cả đĩa và built-in) | user/plugin/built-in | KHÔNG | khác lĩnh vực |

### Khảo sát mã nguồn 3 chiều (Grep · LSP · Graphify)

Đã chứng minh LSP thực tế cho cả hai module của dự án (`python:.` → 2 tham chiếu `ĐẠT`; `rust:hooks/rust/tdq-dispatch` → 3 tham chiếu `ĐẠT`). Hiện trạng mã nguồn ghi nhận 4 vấn đề gốc: (1) Rust `command_parser.rs:70-75` và Python patch `tools/patches/agy_hooks.py:1880-1885` chặn cứng vô điều kiện `git push`, `git reset --hard`, `git clean -f` mà không kiểm tra đồng thuận người dùng; (2) cả hai nơi dùng kiểm tra chuỗi con thô (`lower.contains(...)`) nên chặn nhầm cả lệnh không phải git nhưng có chuỗi đó trong đối số; (3) thẻ hướng dẫn `GIT` trong `tools/patches/gate_guidance.json:74-80` luôn báo chung là lỗi tên nhánh/trailer AI; (4) `pre_tool_use.rs:526` gom `git switch -c` vào `mutates_outside_docs_any` và chặn ngay sau `init` trước khi có `spec_approved`, xung đột trực tiếp với bước 3b của `tdq-intake`.

| Vùng file chạm | Phát hiện qua lớp nào (Grep/LSP/Graphify) | Tác động & quan hệ |
|---|---|---|
| `hooks/rust/tdq-dispatch/src/command_parser.rs` | LSP (`find_references`: 9 refs cho `inspect_command_safety`, 3 refs cho `needs_python_command_gate`) + Grep | Phân tích an toàn lệnh shell (`CommandSafetyViolation`), tách phân đoạn/token shell, `mutates_outside_docs_any`, khóa ghi `docs/tdq/.tdq-runtime/` |
| `hooks/rust/tdq-dispatch/src/events/pre_tool_use.rs` | LSP + Grep | `handle_command_tool` (L484-537) và `handle_edit_tool` (L403-410) kiểm tra vé duyệt theo lượt, khóa `.tdq-runtime/`, miễn trừ `git switch -c` bước 3b |
| `hooks/rust/tdq-dispatch/src/events/pre_invocation.rs`, `user_prompt_submit.rs`, `storage.rs` | Grep (`turn_meta`, `last_user_input`, `user_prompt`) | Đọc `USER_INPUT` từ transcript/prompt gốc, chuẩn hóa `TurnMeta` thêm `git_grants`, xóa `git_grants` khi `mark_turn_closed` |
| `hooks/scripts/prompt_context.py`, `hooks/scripts/bash_gate.py`, `hooks/scripts/edit_gate.py`, `hooks/scripts/agy_pretooluse_gate.py` | Grep (`TDQ:GIT`) + Read | Tầng hook Python: lọc lời nhắc người dùng ghi `git_grants` + dòng `signal`, khóa `.tdq-runtime/`, đồng bộ luật git |
| `tools/patches/agy_hooks.py`, `tools/patches/gate_guidance.json` | Grep (`TDQ:GIT`, `turn_meta`) + Read | Patch dựng `plugins/tdq-workflow-agy/`: `_has_banned_agy_git`, `_patch_prompt_context`, `_patch_edit_gate`, cập nhật nội dung thẻ `GIT` (giữ nguyên 23 mã) |
| `tests/test_rust_dispatch_parity.py`, `tests/test_bash_gate.py`, `tests/test_agy_hooks.py`, `tests/test_hooks_dual_protocol.py`, `tests/test_gate_guidance.py` | Grep (`TDQ:GIT`) | Kiểm thử nền hiện tại: Rust `29 passed`, Python 5 module `137 passed, 19 subtests passed` |
| `plugins/tdq-workflow-agy/` | Kiến trúc build | Gói plugin đầu ra chứa `bin/tdq-dispatch.exe` và script đã patch (`cargo build --release` + `tools/build_agy_plugin.py --upstream .`) |

### Quyết định đã chốt

- **Nhóm lệnh được duyệt theo từng loại (1a):** `git push` thường (không force), `git reset --hard`, `git clean -f`. Chặn cứng tuyệt đối không ngoại lệ: mọi dạng force-push (`--force`, `-f`, `--force-with-lease`, `--force-if-includes`, refspec `+...`), **`Co-Authored-By:`** AI trailer (nhấn mạnh trực tiếp của người dùng), trailer `generated with` AI, và tên nhánh/worktree tiền tố AI (`claude|antigravity|gemini|codex`).
- **Cơ chế xác thực 2 lớp chống AI vượt cổng (2a):** Xác thực trực tiếp từ lời nhắc gốc của người dùng tại `PreInvocation`/`UserPromptSubmit` (ưu tiên `USER_INPUT` trong `transcriptPath` hoặc `prompt`/`user_prompt`, lọc thẻ hệ thống/trích dẫn/câu hỏi/phủ định/thảo luận meta) → ghi vé `git_grants` theo đúng loại thao tác vào `docs/tdq/.tdq-runtime/turn-meta-<sid>.json` + ghi dòng `signal` vào `turns-<sid>.jsonl`; khóa cứng thư mục `docs/tdq/.tdq-runtime/` không cho agent sửa qua cả tool file lẫn shell; subagent không kế thừa vé duyệt git.
- **Hiệu lực single-turn (3a):** Vé chỉ có hiệu lực trong đúng lượt chat hiện tại (`!turn_closed`), tự xóa sạch khi sang lượt mới hoặc khi `mark_turn_closed`.
- **Sửa trọn gói 3 lỗi kèm theo (4a):** Chuyển kiểm tra chuỗi con sang phân tích phân đoạn/token lệnh shell thực sự (bắt cả vỏ bọc `bash -c`/`pwsh -Command`/`cmd /c`/`git -C`), cập nhật thông điệp thẻ `GIT` (giữ nguyên 23 mã) với chi tiết rõ từng lỗi, và miễn trừ lệnh mở nhánh request thuần túy `git switch -c <loại>/<mô-tả>` / `git checkout -b` ở pha `analyze`/`idle` (bước 3b).
- **Ranh giới triển khai (5a):** Chỉ build, test và đóng gói trong repo (`plugins/tdq-workflow-agy/`); cung cấp lệnh đồng bộ sang `~/.gemini/config/plugins/tdq-workflow-agy/` ở báo cáo cuối để người dùng tự chạy.
- **Mức QC (6a):** `full` (DoD + trọn unit test + hồi quy vùng chạm + ràng buộc kiến trúc + clean code).
- **Nghiên cứu ngoài (B2):** Bỏ qua — toàn bộ bài toán nằm trong mã nguồn hook nội bộ của repo.
- Vòng scope: BỎ — Môi trường chạy, đa nền tảng Rust/Python, bất biến bảo mật và cấu trúc plugin đã xác định rõ từ mã nguồn và `docs/kien-truc.md`; đi thẳng vào các quyết định thiết kế lõi của cổng duyệt thao tác git.

### Lộ trình

| Bước/phase | Chạy? | Vì sao |
|---|---|---|
| Research web | BỎ | Bài toán 100% nội bộ trên tầng hook Rust/Python của repo, không phụ thuộc API ngoài |
| Interview | CÓ | Đã hoàn tất 1 vòng 7 câu, chốt rõ phạm vi lệnh, chống vượt cổng, hiệu lực lượt, sửa lỗi kèm theo và mức QC |
| Spec + Archify preview | CÓ | Bắt buộc ở chế độ `full`; khóa thiết kế bảo mật, ranh giới module và DoD đo được trước khi lập plan |
| Plan | CÓ | Bắt buộc ở chế độ `full`; chia nhỏ từng task có test red → green |
| Implement | CÓ | Sửa Rust hook, Python hook/patches, test parity, build release và đóng gói `plugins/tdq-workflow-agy/` |
| QC (`full`) | CÓ | Người dùng chọn `6a` (`full`): DoD + trọn unit test Rust/Python + hồi quy vùng chạm + ràng buộc kiến trúc + clean code |
| QC độc lập (agent) | BỎ | Mức `full` không yêu cầu agent QC độc lập (chỉ ở `ultra`), vẫn chạy đầy đủ kiểm thử thật và `agy plugin validate --strict` |
| Report + Archify HTML | CÓ | Xuất báo cáo 4 phần Markdown + Archify HTML tiếng Việt (HTTP 200 qua Tailscale) kèm lệnh đồng bộ plugin global cho người dùng |

## Hỏi đáp

- **Người dùng trả lời vòng 1:** `1a vẫn chặng việc co author by: nha2a3a  4a 5a 6a 7a`
  - **Câu 1 (nhóm thao tác git):** Chọn **A** — mở theo từng loại `git push` thường (không force), `git reset --hard`, `git clean -f`; giữ chặn cứng tuyệt đối force-push, **`Co-Authored-By:`** và tên nhánh tiền tố AI.
  - **Câu 2 (cơ chế xác thực):** Chọn **A** — xác thực trực tiếp từ lời nhắc gốc của người dùng tại `PreInvocation`/`UserPromptSubmit` và ghi vé theo loại vào `.tdq-runtime/` đã khóa chống agent sửa.
  - **Câu 3 (hiệu lực duyệt):** Chọn **A** — single-turn trong đúng lượt chat hiện tại, tự xóa khi đóng lượt hoặc sang lượt mới.
  - **Câu 4 (3 lỗi kèm theo):** Chọn **A** — sửa trọn gói lỗi chặn nhầm chuỗi con, thông điệp thẻ `GIT`, và mở nhánh bước 3b `git switch -c`.
  - **Câu 5 (đồng bộ plugin global):** Chọn **A** — chỉ build và đóng gói trong repo, xuất sẵn lệnh đồng bộ sang `~/.gemini/config/plugins/tdq-workflow-agy/` để người dùng chủ động chạy.
  - **Câu 6 (mức QC):** Chọn **A** — `full`.
  - **Câu 7 (bổ sung):** Chọn **A** — không bổ sung, đủ để viết spec.
