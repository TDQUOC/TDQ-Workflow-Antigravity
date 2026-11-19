# Brief: Triển khai Kiến trúc Hook Hybrid 2 tầng + Smart Hardening (P0 + P1 + P2)

Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

## Nguyên văn

> "commit và merge và xywr lí theo phương án Hybrid 2 tầng + Smart Hardening (cả 3 chặng) trong cùng 1 request"

- **Mục tiêu:**
  - Triển khai trọn bộ 3 chặng đã đề xuất trong báo cáo `docs/tdq/reports/2026-11-19-1612-research-behavior-va-hieu-nang.md` nhằm đạt **100% kỷ luật behavior (22/22 cổng, vá đủ 10/10 hạn chế từ audit `2026-11-19-1457`)** đồng thời giữ độ trễ `Hot-path <= 28 ms` (trung bình có trọng số `~35 ms`):
    - **Chặng 1 (P0):** Map đủ `PreInvocation`/`PostInvocation` trong `main.rs`, chuẩn hóa `protocol.rs` theo schema AGY 2.0 (`injectSteps`, `reason`, `toolCall`, `workspacePaths`, `write_to_file`/`replace_file_content`, bọc `Arguments`), hợp nhất 1 thư mục `docs/tdq/.tdq-runtime/`, và cài bộ định tuyến Cold-path delegate sang `dispatch.py`.
    - **Chặng 2 (P1):** Áp dụng 6 quy tắc `Smart Hardening` (bật lại chặn cứng `TDQ:TICK` 0/>1 `[~]`, `STREAK_NGUONG=8` + chặn `Stop` khi `plan_sha` đứng yên; khôi phục chặn cứng `TDQ:LOG` ở `Stop` trừ `docs/.staging*`/`docs/tdq/`/`graphify-out/`; sửa `continuationActive` theo `MAX_STREAK=2` gắn `plan_sha`; bịt lỗ hổng `TDQ:SEARCH` + ghi nhận `graphify`; thêm `"qc-tester"` vào `bash_gate.py` & chặn shell mutator cho `APPROVE`/`TEAM`/`READONLY`; bơm neo `[TDQ:GON]`/`[TDQ:QC]` đầu pha/sau compaction & fix cắt UTF-8 `session_start.rs`); hoàn thiện Rust `Hot-path` và build lại gói plugin.
    - **Chặng 3 (P2):** Xây dựng bộ Golden Parity Test Suite phủ đủ `22/22` mã cổng × `6` sự kiện trên payload AGY 2.0 thật, khóa 0 Behavior Drift giữa Rust Hybrid và Python `dispatch.py`.
- **Phạm vi chạm dự kiến:**
  - Crate Rust `hooks/rust/tdq-dispatch/src/**`
  - Các patcher Python `tools/patches/agy_hooks.py`, `tools/patches/agy_dispatch.py`, `tools/patches/agy_manifests.py`, `tools/build_agy_plugin.py`
  - Gói biên dịch `plugins/tdq-workflow-agy/**`
  - Bộ kiểm thử `tests/test_rust_*.py`, `tests/test_hook_dispatch_r1_r3.py`, `tests/test_agy_plugin_validate.py`
- **Điểm cần làm rõ khi vào phase analyze:**
  - Có cần rebuild và đồng bộ luôn cả 2 binary Linux (`ubuntu-100-95`) và macOS (`mbair`) qua SSH trong cùng request hay chỉ Windows + CI workflow.
  - Có cài đè lên local plugin `~/.gemini/config/plugins/tdq-workflow-agy` ngay sau QC hay chờ duyệt riêng.
  - Mức QC mục tiêu (`full` / `ultra`).

## Hiểu & kiến thức

### Năng lực dùng được

- **Skill cục bộ & plugin:** `tdq-intake`, `tdq-spec`, `tdq-plan`, `tdq-build`, `tdq-conventions`, `tdq-lean`, `tdq-checkportable`, `agy-customizations` (tài liệu hợp đồng `docs/hooks.md`).
- **Công cụ kiểm tra & tìm kiếm 3 tầng:**
  - LSP thật qua MCP `tdq-workflow-agy_lsp`: `rust:hooks/rust/tdq-dispatch` ĐẠT Bậc 8 (`symbols=3` tại `storage.rs:39`), `python:.` ĐẠT (`symbols=2` tại `agy_hooks.py:1715`).
  - Grep (`rg` / `run_command`) & Graphify (`god-nodes`, `affected`).
  - Runner kiểm thử (`cargo test`, `py -3 -m pytest`) và 2 host SSH sẵn sàng nếu rebuild binary đa nền tảng (`ubuntu-100-95` cho Linux x86_64, `mbair` cho macOS ARM64).

### Tam giác khảo sát 3 chiều (Grep · LSP · Graphify)

| Vùng file chạm | Phát hiện qua lớp nào | Tác động & quan hệ |
|---|---|---|
| `hooks/rust/tdq-dispatch/src/main.rs` | Grep + LSP Rust | Thiếu nhánh `"PreInvocation"` và `"PostInvocation"` ở `match event_name.as_str()` (`L123-131`); hàm `execute_python_fallback` (`L41-62`) tìm `dispatch.py` theo `workspace_root/plugins/...` thay vì `PLUGIN_ROOT` / `current_exe()`, sẽ gãy ở mọi project ngoài repo TDQ; cần bổ sung bộ định tuyến Cold-path delegate tự động về `hooks/scripts/dispatch.py`. |
| `hooks/rust/tdq-dispatch/src/protocol.rs` | Grep + đối chiếu `hooks.md` | `HookPayload` (`L90-107`) thiếu trường AGY 2.0 (`workspacePaths`, `workingDirectory`, `toolCall`, `conversationId`, `lastUserInput`, `continuationActive`, `toolInput`); `HookDecision` (`L24-34`) xuất sai tên trường (`additional_context`, `explanation`) thay vì `injectSteps` / `reason`. |
| `hooks/rust/tdq-dispatch/src/storage.rs` | LSP Rust (`symbols=3` tại `L39`) | `get_runtime_dir` (`L32-36`) dùng `<root>/.tdq-runtime`, lệch hoàn toàn với `<root>/docs/tdq/.tdq-runtime` bên Python (`_common.py`), làm mất đồng bộ streak và cache giữa Rust và Python. |
| `hooks/rust/tdq-dispatch/src/events/pre_tool_use.rs`, `post_tool_use.rs`, `session_start.rs`, `command_parser.rs` | Grep + LSP Rust | `pre_tool_use.rs:13-16` chỉ kiểm `write_file`/`edit_file` + key `Path`, bỏ sót `write_to_file`/`replace_file_content`/`multi_replace_file_content`/`TargetFile`/`file_path`, mới cài 4/22 cổng và `overwrite` cho `start_lsp` chưa bọc `"Arguments"` khi đi qua `call_mcp_tool`; `session_start.rs:47-51` cắt `&rules_content[..1500]` theo byte có nguy cơ panic UTF-8 với tiếng Việt. |
| `tools/patches/agy_hooks.py`, `tools/patches/agy_dispatch.py`, `tools/patches/agy_manifests.py` | LSP Python + Graphify (`apply_all()` → `build()`) | Áp dụng 6 quy tắc Smart Hardening (`TDQ:TICK`, `TDQ:LOG`, `TDQ:UNFINISHED`, `TDQ:SEARCH`, `bash_gate` thêm `"qc-tester"` + chặn shell mutator cho `APPROVE`/`TEAM`/`READONLY`, bơm 1 dòng neo `[TDQ:GON]`/`[TDQ:QC]` đầu pha & sau compaction). |
| `tools/build_agy_plugin.py`, `tools/install_agy_plugin.py` | Grep + đọc trực tiếp | **Lỗi chí mạng (`build_agy_plugin.py:84-92`):** `stage` là thư mục tạm rỗng nên luôn copy đè `rust_exe` (Windows PE `.exe`) thành cả `tdq-dispatch-linux-x86_64` và `tdq-dispatch-darwin-arm64`, sau đó `sync_tree_inplace` (`L105`) ghi đè xóa 2 bản binary Unix thật trong `plugins/tdq-workflow-agy/bin/`. Cần bảo toàn prebuilt hợp lệ và kiểm tra magic bytes (`MZ` / `\x7fELF` / Mach-O). |
| `plugins/tdq-workflow-agy/**` | Output build của `build_agy_plugin.py` | Gói biên dịch đầu ra đồng bộ 3 binary Rust + Python hooks đã patch Smart Hardening + `hooks.json`. |
| `tests/test_rust_dispatch_parity.py` (mới), `tests/test_rust_*.py`, `tests/test_hook_dispatch_r1_r3.py`, `tests/test_agy_plugin_validate.py` | Grep | Bộ Golden Parity Test Suite `22/22` mã cổng × `6` sự kiện trên payload AGY 2.0 thật + test kiểm tra magic bytes đa nền tảng và đường dẫn tìm `dispatch.py`. |

### Lý do bỏ qua B2 và Scope Round

- **Bỏ qua B2 research ngoài:** Hợp đồng hook Antigravity (`agy-customizations/docs/hooks.md`), mã nguồn cục bộ và 2 báo cáo phân tích `2026-11-19-1457-audit-sai-sot-noi-hook.md` + `2026-11-19-1612-research-behavior-va-hieu-nang.md` đã cung cấp đầy đủ căn cứ, không còn điểm mù ngoài repo.
- Vòng scope: BỎ — người dùng đã chốt trọn phạm vi 3 chặng (`P0 + P1 + P2`) của phương án Hybrid 2 tầng + Smart Hardening từ báo cáo `1612`, mọi vùng chạm đều suy ra trực tiếp từ code.

### Ràng buộc & mục tiêu đã chốt

- **Độ phủ behavior:** Đạt `100%` parity trên toàn bộ `22/22` mã cổng, khắc phục đủ `10/10` hạn chế từ audit `2026-11-19-1457`.
- **Hiệu năng mục tiêu:** `Hot-path` Rust đạt `<= 28 ms` (trung bình có trọng số `~35 ms`), không có nhánh rơi im lặng về `allow()` đối với `Cold-path`.
- **An toàn quy trình:** Commit không chứa `Co-Authored-By`; mọi file HTML preview/report phục vụ qua Tailscale Serve (`https://unity-pc-rtx3060.tail99896.ts.net/vlog/tdq-workflow-agy/...`).

### Lộ trình

| Bước/phase | CÓ-BỎ | Vì sao |
|---|---|---|
| Analyze + phỏng vấn chi tiết | CÓ | Đã hoàn tất chốt 5 câu hỏi (`1a 2b 3a 4c 5a`) cố định phạm vi 3 OS, phạm vi hook gốc và mức QC `ultra`. |
| Research web ngoài (B2) | BỎ | Hợp đồng `hooks.md` và mã nguồn nội bộ đã đủ `100%`. |
| Spec + Archify BA Preview | CÓ | Chốt đặc tả Hybrid 2 tầng, 6 quy tắc Smart Hardening, sửa 2 lỗi mới phát hiện (`build_agy_plugin.py`, `main.rs`), và ma trận Parity `22/22` mã cổng. |
| Plan chia đợt + subagent | CÓ | Tách rõ 4 module độc lập (Rust protocol/fallback, Rust hot-path/UTF-8, Python Smart Hardening + build fix, Golden Parity Test + benchmark) để triển khai song song an toàn. |
| Implement (red → green từng task) | CÓ | Thực thi và tick tuần tự `[~]` → `[x]` từng task. |
| Build & test đa nền tảng (3 OS) | CÓ | Theo lựa chọn `1a`: build Windows tại chỗ + SSH rebuild & test thật trên Linux (`ubuntu-100-95`) và macOS (`mbair`) để đồng bộ 3 binary. |
| Cài lên local plugin | BỎ | Theo lựa chọn `2b`: chỉ cập nhật `plugins/tdq-workflow-agy/` trong repo, chưa chạy `install.py` đè local plugin. |
| QC (`ultra`) | CÓ | Theo lựa chọn `4c`: DoD + trọn unit test + hồi quy vùng chạm + ràng buộc kiến trúc + clean code + smoke/runtime test + agent `tdq-qc-tester` độc lập soi lại. |
| Report + Archify HTML (Tailscale Serve) | CÓ | Xuất báo cáo 4 phần chuẩn (Trước/Sau/Đã test/Kết quả) kèm link Tailscale Serve. |

## Hỏi đáp

- **Thời điểm trả lời:** `2026-11-19T16:54:56+07:00`
- **Nguyên văn người dùng trả lời:** `1a 2b 3a 4c 5a`

1. **Câu 1 — Xử lý 3 binary đa nền tảng sau khi hoàn tất Rust Hybrid và sửa lỗi `build_agy_plugin.py`:**
   - **A (đề xuất):** Sửa lỗi `build_agy_plugin.py` (bảo toàn prebuilt và kiểm tra magic bytes PE/ELF/Mach-O), build Windows tại chỗ và SSH rebuild + test luôn Linux (`ubuntu-100-95`) và macOS (`mbair`).
   - **B:** Sửa lỗi `build_agy_plugin.py` và chỉ build/test Windows tại chỗ.
   - **Người dùng chọn:** `1a` — Build Windows tại chỗ và SSH rebuild + test đầy đủ cả Linux (`ubuntu-100-95`) và macOS (`mbair`), bảo toàn 3 binary hợp lệ đồng bộ.

2. **Câu 2 — Cập nhật thẳng lên local plugin (`C:\Users\admin\.gemini\config\plugins\tdq-workflow-agy`) sau QC:**
   - **A (đề xuất):** Có, chạy `install.py` cài ngay lên local plugin.
   - **B:** Không, chỉ cập nhật trong thư mục `plugins/tdq-workflow-agy/` của repo.
   - **Người dùng chọn:** `2b` — Không chạy `install.py` cài đè local plugin; chỉ đóng gói cập nhật trong `plugins/tdq-workflow-agy/` của repo.

3. **Câu 3 — Phạm vi áp dụng 6 quy tắc Smart Hardening đối với bộ hook gốc của Claude Code / Codex:**
   - **A (đề xuất):** Giữ nguyên `hooks/scripts/` gốc cho Claude/Codex, áp dụng Smart Hardening trên tầng patch AGY (`tools/patches/agy_hooks.py`) và Rust crate (riêng bổ sung `"qc-tester"` vào `_enforce_agy_bash_guards` ở `hooks/scripts/bash_gate.py` giữ an toàn không phá test cũ).
   - **B:** Đồng bộ toàn bộ Smart Hardening thẳng xuống `hooks/scripts/` gốc cho cả Claude/Codex.
   - **Người dùng chọn:** `3a` — Giữ nguyên hành vi Claude/Codex tại `hooks/scripts/` gốc, chỉ vá AGY tại `tools/patches/agy_hooks.py` + Rust crate (kèm thêm `"qc-tester"` an toàn vào guard AGY của `bash_gate.py`).

4. **Câu 4 — Mức QC mong muốn:**
   - **A (đề xuất):** `full` — DoD + trọn unit test + hồi quy vùng chạm + ràng buộc kiến trúc + clean code.
   - **B:** `lite` — DoD + unit test của riêng vùng chạm.
   - **C:** `ultra` — như `full`, thêm smoke test, runtime test và một agent QC độc lập soi lại.
   - **Người dùng chọn:** `4c` — `muc_qc = ultra`.

5. **Câu 5 — Bổ sung thêm:**
   - **A (đề xuất):** Không, đủ rồi — làm tiếp đi.
   - **B:** Có — tôi nói thêm.
   - **Người dùng chọn:** `5a` — Chốt đủ yêu cầu, chuyển tiếp sang viết spec.

| Câu | Lựa chọn | Quyết định chốt vào Spec |
|---|---|---|
| 1 | `1a` | Sửa `build_agy_plugin.py` magic-byte guard + rebuild & test đủ 3 OS (Windows, `ubuntu-100-95`, `mbair`) |
| 2 | `2b` | Không chạy `install.py` đè local plugin người dùng; chỉ cập nhật `plugins/tdq-workflow-agy/` |
| 3 | `3a` | Smart Hardening trên `tools/patches/agy_hooks.py` + Rust crate (thêm `"qc-tester"` an toàn ở `bash_gate.py`) |
| 4 | `4c` | Thiết lập `muc_qc = ultra` (thêm smoke/runtime test + agent `tdq-qc-tester` độc lập) |
| 5 | `5a` | Đóng phỏng vấn, chuyển sang `phase=spec` |
