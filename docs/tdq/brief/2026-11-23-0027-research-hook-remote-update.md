# BRIEF — Nghiên cứu tính khả thi hook kiểm tra phiên bản mới từ Git remote

Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

## Nguyên văn

> okay hãy resreach giúp tôi liệu có thể có hook check version mới trên nhánh trên git remote để mà khi có update sẽ nhắc trong chat xin quyền cập nhật và setup fully new ver, hãy check và phân tích và cho tôi biết là có khả thi không?

**Đọc hiểu ban đầu (`work_kind=investigate`):**
- **Mục tiêu:** Nghiên cứu, kiểm chứng hạ tầng hiện có trong `TDQ-Workflow-Antigravity` và cơ chế plugin/hook của Google Antigravity để đánh giá tính khả thi của luồng: hook tự kiểm tra phiên bản mới trên nhánh Git remote (`release/antigravity` / `dev`) → nhắc trực tiếp trong chat kèm xin quyền người dùng → khi được đồng ý thì tự cập nhật plugin bản mới và chạy nối tiếp `setupfully` (`--setupfully` + restart + `--post-restart-verify`).
- **Phạm vi:** Chỉ khảo sát mã nguồn hiện tại (`hooks/`, `scripts/tdq_setup.py`, `hooks/rust/tdq-dispatch/`, `tools/patches/agy_hooks.py`), kiểm tra cơ chế `agy plugin install` / GitHub API / `git ls-remote`, đánh giá rủi ro (độ trễ hot-path `< 50 ms`, offline, rate-limit, an ninh/quyền, xung đột bản cài đang chạy trên Windows) và đưa kết luận khả thi + phương án kiến trúc đề xuất. Không sửa mã nguồn sản phẩm trong request nghiên cứu này.
- **Điểm cần làm rõ khi phân tích sâu:** Nhánh remote mục tiêu (`release/antigravity` hay nhánh người dùng chọn), tần suất/TTL kiểm tra nền (ví dụ 6h–24h một lần, không chặn `SessionStart`/`PreInvocation`), cách so sánh version (`plugin.json` semver + commit SHA), và cơ chế ghi đè bản cài live trên Windows đang mở `tdq-dispatch.exe`.

## Hiểu & kiến thức

**Điểm vào đã xác nhận (khảo sát nông B1):**
- `plugins/tdq-workflow-agy/hooks.json:2-18`: Antigravity gọi `tdq_hook_launcher.mjs` tại `SessionStart` và `PreInvocation`, làm hai điểm neo hợp lệ để kích hoạt kiểm tra nền và hiển thị nhắc trong chat.
- `hooks/rust/tdq-dispatch/src/events/session_start.rs:10-62`: Trên Antigravity, `SessionStart` chạy bằng Rust thuần không mở Python subprocess. Nó dọn file runtime, kiểm `.tdq-san-sang.json` và đọc `state.json`, chưa gọi kiểm tra remote version.
- `hooks/scripts/session_start.py:229-246` và `scripts/tdq_setup.py:902-1003`: Mã nguồn đã có sẵn mẫu kiểm tra nền với TTL throttle (`can_kiem_tra_remote`, `kich_hoat_kiem_tra_remote_nen`, `doc_thong_bao_update_moi`), nhưng đang khóa riêng cho Claude (`if not is_agy():`) và gọi `claude plugin marketplace update` / `claude plugin update`.
- `hooks/scripts/prompt_context.py:180-222,439`: Antigravity đã có sẵn luồng phát directive `[TDQ:SETUP]`, thẻ `user_markdown` hiển thị cho người dùng, và bộ lọc câu kích hoạt tự nhiên `extract_setupfully_trigger`.
- `agy plugin --help` (đo trực tiếp trên máy): `agy.exe plugin` hỗ trợ `list`, `import`, `install <target>`, `uninstall`, `enable`, `disable`, `validate`, `link`, nhưng không có lệnh `update` hay `check-update` sẵn.
- `plugins/tdq-workflow-agy/plugin.json:4-5`: Lưu sẵn `version` (`0.105.0`) và `repository` (`https://github.com/TDQUOC/TDQ-Workflow-Antigravity`).

**Giả thuyết cần kiểm chứng sâu trong phase implement (có thể bác bỏ):**
- **H1 (Hook nền và nhắc trong chat không làm chậm hot-path):** Có thể tách việc kiểm tra remote ra tiến trình nền với cache TTL (`6–24` giờ), còn `SessionStart`/`PreInvocation` chỉ đọc file cache cục bộ `O(1)` để phát cảnh báo trong chat.
- **H2 (Cơ chế so sánh phiên bản nhánh git remote):** Có thể phát hiện bản mới trên nhánh remote (ví dụ `release/antigravity`) một cách tin cậy mà không clone toàn repo và không chạm giới hạn 60 req/giờ của GitHub API (so sánh `git ls-remote`, raw `plugin.json`, GitHub API, cả chế độ offline và repo private).
- **H3 (Xin quyền trong chat → cài bản mới → chạy `setupfully`):** Có thể ghép lớp xin quyền rõ ràng trong chat (chống kích hoạt nhầm từ câu hỏi hay trích dẫn) với lệnh cài ghi đè bản mới rồi nối thẳng vào `tdq_setup.py --setupfully`, `awaiting_restart` và `--post-restart-verify`.
- **H4 (Rủi ro thực thi trên Windows và bảo toàn hệ thống):** Cần kiểm tra xem `agy plugin install` hay `install_agy_plugin.py` có ghi đè an toàn plugin đang chạy trên Windows (khóa `tdq-dispatch.exe`, `agent-lsp`), giữ được cấu hình `caveman`, sao lưu bản cũ, và không phá hợp đồng 23 mã `[TDQ:*]` hay không.

## Hỏi đáp

- **Hỏi chọn lane:** Nhanh (`quick`, mặc định với nghiên cứu thuần) hay Đầy đủ (`full`)?
- **Người dùng trả lời:** `1a` (chọn luồng nhanh `quick`, loại nhánh `docs/research-hook-remote-update` gộp về `dev`).
