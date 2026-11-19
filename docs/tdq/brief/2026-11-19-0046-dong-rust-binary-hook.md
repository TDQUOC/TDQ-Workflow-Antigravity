# BRIEF — Đóng gói Rust binary cho tầng hook và tích hợp kèm TDQ-Workflow Antigravity (`2026-11-19-0046-dong-rust-binary-hook`)

Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

## Nguyên văn

> "Okay mở request handle đóng rust binary và kèm theo tdq workflow antigravity thay vì dùng python như hiện tại"

- **Mục tiêu ban đầu:** Chuyển tầng thực thi hook của `TDQ-Workflow Antigravity` (`plugins/tdq-workflow-agy/`) từ gọi tiến trình Python (`python -X utf8 hooks/scripts/dispatch.py`) sang native **Rust binary** biên dịch sẵn và đi kèm gói plugin / bộ cài, nhằm loại bỏ chi phí khởi tạo CPython VM (`~45–55 ms`/lần) và kéo độ trễ hook xuống mức tối thiểu.
- **Nhánh làm việc:** `feature/dong-rust-binary-hook` (tách từ `dev`).

## Hiểu & kiến thức

### Năng lực dùng được

Phân vân → DÙNG. Kiểm kê ngày 2026-11-19: 42 skill trên đĩa, cộng skill built-in trong context. Không xoá bảng này kể cả khi không có dòng DÙNG nào.

| Skill | Nguồn | Phán quyết | Dùng ở đâu / Lý do loại |
|---|---|---|---|
| tdq-intake | plugin:tdq-workflow-agy | NỀN | mở request, khảo sát 3 chiều và phỏng vấn |
| tdq-spec | plugin:tdq-workflow-agy | NỀN | viết đặc tả kỹ thuật và sơ đồ Trước/Sau Archify |
| tdq-plan | plugin:tdq-workflow-agy | NỀN | lập kế hoạch checkbox TDD từng đợt |
| tdq-build | plugin:tdq-workflow-agy | NỀN | điều phối thực thi, kiểm định QC và viết báo cáo |
| tdq-conventions | plugin:tdq-workflow-agy | NỀN | chuẩn giao tiếp, chữ ký phê duyệt, i18n 3 tầng và quy tắc git |
| tdq-lean | plugin:tdq-workflow-agy | DÙNG | rà soát thiết kế crate Rust và tập phụ thuộc tối giản ở pha spec/QC |
| tdq-setup | plugin:tdq-workflow-agy | NỀN | kiểm tra bậc công cụ và đồng bộ mốc phát hành |
| tdq-status | plugin:tdq-workflow-agy | NỀN | theo dõi trạng thái tiến trình request |
| tdq-check-status | plugin:tdq-workflow-agy | NỀN | khôi phục trạng thái khi ngắt phiên |
| tdq-checkportable | plugin:tdq-workflow-agy | DÙNG | kiểm chứng tính khả chuyển của gói plugin sau khi nhúng binary Rust |
| agy-customizations | built-in | DÙNG | chuẩn cấu trúc `hooks.json` (`cmd /c` trên Windows, `sh -c` trên Unix, biến `PLUGIN_ROOT`), `plugin.json` và trình kiểm tra `agy plugin validate --strict` |
| plugin | built-in | DÙNG | quy tắc đóng gói, cài đặt và kiểm kê plugin Antigravity |
| Đã xét 48 skill khác | user/plugin/built-in | KHÔNG | khác lĩnh vực |

### Khảo sát mã nguồn 3 chiều & Đo thực nghiệm môi trường

- **Môi trường máy hiện tại (đã đo trực tiếp):**
  - Toolchain Rust: `rustc 1.99.0` & `cargo 1.99.0` (`host: x86_64-pc-windows-msvc`, LLVM `23.1.1`).
  - Thử nghiệm `std::fs::File::try_lock()` chuẩn Rust `1.99`: biên dịch `rc=0`; thử nghiệm static CRT (`-C target-feature=+crt-static`): biên dịch `rc=0` (`~240 KB` cho binary tối thiểu, không phụ thuộc `vcruntime140.dll`).
  - Thử nghiệm Cargo cache với `serde`, `serde_json`, `regex`, `sha2`: `cargo check` đạt `rc=0` trong `~12s`.
  - **Phát hiện quan trọng trên `agy.EXE plugin validate --strict` & `cmd.exe /c` (Windows):**
    - Antigravity chạy lệnh `hooks.json` qua `cmd /c` trên Windows và `sh -c` trên Unix với thư mục làm việc là gốc plugin (`docs/hooks.md` dòng 129–131).
    - Đường dẫn gạch chéo xuôi `bin/tdq-dispatch --event SessionStart` bị **cả** `agy plugin validate --strict` cảnh báo (`findings` 1 warning) **lẫn** `cmd.exe /c` báo lỗi (`'bin' is not recognized`).
    - Đường dẫn gạch chéo ngược `bin\tdq-dispatch.exe --event SessionStart` (hoặc `bin\tdq-dispatch --event SessionStart`) trên Windows đạt **`validate_rc=0, findings=[]`** và thực thi qua `cmd.exe /c` mất trung vị **`14,75 ms`** (so với `70–126 ms` của `python -X utf8`, nhanh hơn **5–8,5 lần** tính cả vỏ `cmd.exe`, còn gọi trực tiếp tiến trình chỉ `~2–4 ms`). Trên macOS/Linux, bộ cài điều chỉnh sang `./bin/tdq-dispatch --event <Event>`.
- **Ràng buộc từ `docs/kien-truc.md` & `.graphifyignore`:**
  - Mã nguồn mới cần đặt trong `hooks/` (ví dụ `hooks/rust/tdq-dispatch/`) để đồ thị `graphify` quét được `.rs` (đồng thời loại `hooks/rust/tdq-dispatch/target/` trong `.gitignore` và `.graphifyignore`).
  - `docs/tdq/state.json` vẫn chỉ được **ghi** bởi `scripts/tdq_state.py`; tầng hook Rust chỉ **đọc** `state.json` và chỉ ghi các tệp runtime riêng của hook (`.tdq-runtime/`, `turns-<sid>.jsonl`, `turn-meta-<sid>.json`, `.tdq-search.jsonl`, `.tdq-read.jsonl`, `stop_streak.json`, cache `repo_root` / `rtk` / `tdq_ccr`).

| Vùng file chạm | Phát hiện qua lớp nào (Grep/LSP/Graphify) | Tác động & quan hệ |
|---|---|---|
| `hooks/rust/tdq-dispatch/` (mới) | Kiến trúc (`docs/kien-truc.md` + `.graphifyignore`) | Crate Rust thực thi dispatcher + các cổng hook Antigravity |
| `tools/patches/agy_dispatch.py`, `agy_hooks.py`, `gate_guidance.py` | Graphify `query` + `affected` | Nguồn quy chiếu 17 file hook AGY hiện tại (`~5.605` dòng Python) và `dispatch.py` fallback |
| `scripts/search_rules.py`, `scripts/rtk_integration.py`, `scripts/tdq_ccr.py`, `scripts/tdq_state.py` | Graphify `affected` + AST | Logic bóc lệnh PowerShell/POSIX, cache `rtk` rewrite, kho CCR `>32KB`/`>=200` dòng và cấu trúc `state.json` / `repo_root` cache |
| `tools/patches/agy_manifests.py`, `tools/patches/common_utils.py` | Grep `hooks.json` + Graphify | Sinh `hooks.json` trỏ vào binary Rust, cập nhật `manifest.json` và loại trừ thư mục build tạm |
| `tools/build_agy_plugin.py` | Graphify `build()` | Gọi `cargo build --release`, chép binary vào `plugins/tdq-workflow-agy/bin/` và kiểm tra tính toàn vẹn |
| `tools/install_agy_plugin.py`, `install.py`, `install.ps1`, `install.sh` | Grep + Graphify | Cài đặt binary sang `~/.gemini/config/plugins/tdq-workflow-agy`, tự điều chỉnh đường dẫn `hooks.json` theo OS (Windows `bin\tdq-dispatch.exe`, Unix `./bin/tdq-dispatch`) hoặc tự compile / fallback `dispatch.py` |
| `scripts/build_portable.py`, `scripts/tdq_checkportable.py` | Grep `hooks.json` | Đảm bảo xuất nhánh `main` và kiểm tra tính khả chuyển không báo lỗi với lệnh binary trong `hooks.json` |
| `tests/test_hook_dispatch_r1_r3.py`, `tests/test_agy_plugin_validate.py`, `tests/test_command_gate.py` + test đối chiếu Rust mới | Grep `dispatch.py` | Khóa tương đương hành vi 1-1 (differential testing) giữa Rust binary và Python, kiểm độ trễ và `agy plugin validate --strict` |

### Kết quả nghiên cứu chuyên sâu (`docs/tdq/research/2026-11-19-0046-dong-rust-binary-hook.md`)

- **Khóa tệp đa nền tảng (`std::fs::File::lock` / `try_lock`):** Trên Windows, `LockFileEx` là khóa bắt buộc (mandatory byte-range lock) theo từng `HANDLE` — nếu khóa trực tiếp lên `state.json` hay `turns-<sid>.jsonl`, mọi tiến trình khác mở đọc không khóa sẽ lỗi `ERROR_LOCK_VIOLATION` (`os error 33`). Do đó **bắt buộc khóa trên tệp sidecar `.lock` riêng** (tương thích trực tiếp với cơ chế `.lock` hiện hữu của Python `msvcrt`) kết hợp ghi nguyên tử `temp + rename`.
- **Cấu hình biên dịch chống false-positive của Windows Defender:** Tổ hợp `+crt-static` + `lto = true` (fat) + `strip = true` trên file `.exe` chưa ký số dễ kích hoạt cảnh báo nhầm `Wacatac.B!ml` (`os error 225`). Khuyến nghị chỉ bật `+crt-static` cho `windows-msvc` cùng `lto = "thin"`, `codegen-units = 1`, `panic = "abort"`, `strip = "symbols"` và không kéo async runtime nặng.
- **Chiến lược phân phối & fallback 0-overhead lúc chạy:** Phân giải đường dẫn binary **1 lần lúc build/install** (Windows trỏ thẳng `bin\tdq-dispatch.exe`, macOS/Linux trỏ `./bin/tdq-dispatch` sau khi có binary hoặc `cargo build --release`; nếu thiếu cả prebuilt lẫn `cargo` thì ghi `hooks.json` về fallback `python -X utf8 hooks/scripts/dispatch.py`), tránh tốn thêm lớp vỏ wrapper ở mỗi lần gọi hook.

### Phạm vi đã chốt

- **Ngôn ngữ & Crate:** Viết crate Rust `tdq-dispatch` tại `hooks/rust/tdq-dispatch/` theo chuẩn Rust 2021 / 1.99, static CRT trên Windows (`+crt-static`), `lto = "thin"`, `codegen-units = 1`, `panic = "abort"`, `strip = "symbols"`.
- **6 sự kiện hook Antigravity xử lý độc lập bằng Rust:**
  1. `SessionStart`: Thuần Rust 100% (không spawn Python nền), dọn dẹp `.tdq-runtime` cũ hơn 7 ngày, đọc `state.json`, tải và áp dụng luật gọn `luat_gon`, kiểm tra `.tdq-san-sang.json` và phát cảnh báo/hướng dẫn `[TDQ:SETUP]` / `[TDQ:SEARCH]`.
  2. `UserPromptSubmit`: Kiểm tra gate hướng dẫn dựa trên `state.json` và luật gọn, ghi nhận trạng thái prompt.
  3. `PreToolUse`: Chặn lệnh nguy hiểm (cmdlet bypass, curl/powershell tải script, phá hủy git/lịch sử), ghi nhận token/command.
  4. `PostToolUse`: Ghi nhận nhật ký lượt công cụ (`.tdq-search.jsonl`, `.tdq-read.jsonl`, `turns-<sid>.jsonl`), tính toán CCR store (`>32KB` hoặc `>=200` dòng) và gắn thẻ tóm tắt.
  5. `StopStreak`: Phát hiện vòng lặp dừng (`stop_streak.json`) và đưa ra cảnh báo can thiệp.
  6. `Notification`: Xử lý thông báo tiến trình và sự kiện nền.
- **Cơ chế khóa tệp & an toàn đồng thời:**
  - Tuyệt đối không dùng `std::fs::File::lock()` trực tiếp lên file dữ liệu chính (`state.json`, `.jsonl`) trên Windows để tránh `ERROR_LOCK_VIOLATION` (`os error 33`).
  - Dùng sidecar lock `.lock` riêng biệt và ghi nguyên tử `tempfile + rename` tương thích với Python `msvcrt.locking`.
- **Phân phối & Tự phục hồi đa nền tảng:**
  - Đóng sẵn 3 binary trong `plugins/tdq-workflow-agy/bin/`:
    - `windows_x86_64`: `tdq-dispatch.exe`
    - `linux_x86_64`: `tdq-dispatch-linux-x86_64` (musl)
    - `darwin_arm64`: `tdq-dispatch-darwin-arm64`
  - Bộ cài `install.py` / `tools/install_agy_plugin.py` tự sao chép binary tương ứng với OS mục tiêu thành `bin/tdq-dispatch` (hoặc `bin\tdq-dispatch.exe` trên Windows) và gán quyền thực thi (`chmod +x`).
  - Sinh cấu hình `hooks.json` theo đúng chuẩn đường dẫn của OS: `bin\tdq-dispatch.exe --event <Event>` trên Windows và `./bin/tdq-dispatch --event <Event>` trên Unix.
  - Cơ chế dự phòng (fallback): Khi đặt biến môi trường `TDQ_HOOK_ENGINE=python` hoặc khi thiếu binary và không thể compile, tự động fallback sang `python -X utf8 hooks/scripts/dispatch.py`.
- **Nguồn dữ liệu hợp nhất (Single Source of Truth):**
  - Trích xuất bảng 22 mã hướng dẫn từ `tools/patches/gate_guidance.py` ra file JSON dùng chung hoặc sync protocol để Rust crate và Python dispatch đồng bộ 100%.

### Lộ trình

- **Pha spec:** Đặc tả chi tiết 13 mục chuẩn TDQ, hợp đồng CLI của `tdq-dispatch`, cấu trúc crate, cơ chế lock sidecar, schema fallback, tiêu chí nghiệm thu và sơ đồ Archify Trước/Sau.
- **Pha plan:** Lập danh sách công việc TDD từng đợt theo kiến trúc 6 module độc lập.
- **Pha build:**
  - Đợt 1: Khởi tạo crate Rust `tdq-dispatch`, cấu hình static CRT, defender-safe, modules parsing CLI và sidecar locking.
  - Đợt 2: Hiện thực 6 sự kiện hook (`SessionStart`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `StopStreak`, `Notification`).
  - Đợt 3: Tích hợp CCR store, luật gọn, cache rtk và bóc tách câu lệnh PowerShell/POSIX.
  - Đợt 4: Cập nhật build script `tools/build_agy_plugin.py`, patchers sinh `hooks.json`, installer và GitHub Actions CI matrix.
  - Đợt 5: Viết bộ test đối chiếu vi phân (differential testing) giữa Rust binary và Python hook; đo kiểm độ trễ hot-path.
- **Pha report:** Báo cáo nghiệm thu cặp `.md` / `.html` phục vụ qua Tailscale Serve.

## Hỏi đáp

### Vòng 1 — Phạm vi & Bối cảnh (ĐÃ CHỐT)

- **1 (Các mặt chất lượng):** `1abcd` — bao gồm cả 4 mặt: Hiệu năng hot-path & tương thích 1-1 (`A`), Đa nền tảng & tự phục hồi khi cài đặt Windows/macOS/Linux (`B`), An toàn khóa tệp NTFS & phòng tránh cảnh báo Windows Defender (`C`), và Bảo toàn tương thích ngược cho Claude Code & Codex (`D`).
- **2 (Đóng gói & phân phối):** `2c` — biên dịch chéo và đóng sẵn cả 3 binary (`Windows x86_64`, `macOS arm64`, `Linux x86_64`) ngay trong gói plugin.
  - *Kiểm tra toolchain thực tế trên máy:* Có sẵn `rustup` (`x86_64-pc-windows-msvc`), `docker`, `wsl`, `gh`, `.github/workflows/`; **chưa có** `zig`, `cargo-zigbuild`, `x86_64-unknown-linux-musl`, `aarch64-apple-darwin`.
- **3 (Phạm vi chuyển đổi Rust):** `3b` — chuyển tuyệt đối `100%` mọi nhánh của cả 6 sự kiện hook sang Rust hoàn toàn (tuyệt đối không gọi bất kỳ script Python nào từ hook).
- **4 (Độ trễ mục tiêu):** `4a` (mục tiêu hướng tới, **không khóa cứng làm cổng chặn**) — hướng tới trung vị `<= 25 ms` qua `cmd.exe /c` / `sh -c` và `<= 5 ms` khi gọi trực tiếp binary.
- **5 (Bổ sung):** `5a` — không bổ sung thêm.
- **Suy luận mức đầu tư:** Mức đầu tư **đầy đủ (`full`)** — spec/plan sẽ có đầy đủ ngưỡng hiệu năng mềm, kiểm thử đối chiếu 1-1, an toàn khóa NTFS và quy trình build/validate đa nền tảng.

### Vòng 2 — Chi tiết kỹ thuật & Mức QC (ĐÃ CHỐT)

- **1 (Dựng 3 binary đa nền tảng):** `1a` — Đề xuất cài đặt user-level cho toolchain cross-compile (`rustup target add x86_64-unknown-linux-musl aarch64-apple-darwin`, `winget install -e --id zig.zig --scope user`, `cargo install --locked cargo-zigbuild`) trình bày trong spec chờ user duyệt; đồng thời thiết lập GitHub Actions CI matrix `.github/workflows/build-rust-hooks.yml` tự động build 3 nền tảng.
- **2 (Đồng bộ mã hướng dẫn & Fallback):** `2a` — Đồng bộ hợp đồng 22 mã hướng dẫn qua nguồn dữ liệu chung (`gate_guidance.json`), khóa hành vi 1-1 bằng kiểm thử vi phân (differential testing), giữ `hooks/scripts/dispatch.py` làm phương án dự phòng khi môi trường thiếu binary hoặc biến môi trường `TDQ_HOOK_ENGINE=python`.
- **3 (Hành vi SessionStart & Dự phòng):** `3a` kèm ghi chú dự phòng — `SessionStart` chạy thuần Rust 100% không spawn Python nền (dọn dẹp `.tdq-runtime` > 7 ngày, đọc `state.json`, lọc `luat_gon`, kiểm tra mốc `.tdq-san-sang.json` và phát `[TDQ:SETUP]` / `[TDQ:SEARCH]`). Vẫn hỗ trợ fallback sang Python khi người dùng chỉ định.
- **4 (Mức QC):** `4a` — `full` (DoD + unit test trọn bộ + hồi quy vùng chạm + ràng buộc kiến trúc + clean code).
- **5 (Bổ sung):** `5a` — Không bổ sung thêm.


