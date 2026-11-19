# RESEARCH — Đóng gói Rust CLI binary cho hook dispatcher đa nền tảng
Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md
Ngày: 2026-11-19 · Request: `2026-11-19-0046-dong-rust-binary-hook`

## (a) Kết luận ngắn

Khi biên dịch bộ điều phối hook TDQ thành binary Rust độc lập trên Windows, macOS và Linux, ba rủi ro kỹ thuật cấp hệ điều hành phải được khóa cứng ngay từ tầng thiết kế:

1. **Khóa tệp (`std::fs::File::lock` / `try_lock`):** Trên Windows, `File::lock()` ánh xạ xuống `LockFileEx` (khóa byte-range **bắt buộc / mandatory** trên toàn bộ dải byte `0..u64::MAX` gắn theo từng `HANDLE`), trái ngược hoàn toàn với `flock(2)` mang tính **khuyến nghị / advisory** trên Unix. Nếu tiến trình A giữ `File::lock()` trực tiếp trên tệp dữ liệu (như `state.json` hay `.jsonl`), mọi tiến trình B (ví dụ script Python chưa chuyển đổi hoặc reader không gọi lock) gọi `ReadFile`/`WriteFile` trên cùng tệp đó — hoặc thậm chí chính tiến trình A mở lại đường dẫn tệp lần hai bằng handle mới — sẽ bị nhân Windows từ chối ngay với mã lỗi Win32 `ERROR_LOCK_VIOLATION` (mã `33` / `0x21`). Giải pháp bắt buộc cho TDQ là **khóa trên tệp sidecar `.lock` tách rời** kết hợp ghi nguyên tử (temp + rename) cho tệp trạng thái chính.
2. **Cấu hình MSVC tĩnh, cold-start và Windows Defender:** Trên `x86_64-pc-windows-msvc`, tổ hợp `+crt-static` + `lto = true` (fat LTO) + `panic = "abort"` + `strip = true` dễ kích hoạt cảnh báo nhầm của Windows Defender (`Trojan:Win32/Wacatac.B!ml`) trên binary không chữ ký số do mất bảng import `vcruntime140.dll` và cấu trúc section bị nén mạnh. Đồng thời, nhúng tĩnh toàn bộ CRT làm tăng dung lượng ảnh `.exe` và có thể gây thêm hard page fault nếu cold-start từ ổ đĩa lạnh, dù giảm phụ thuộc VC++ Redistributable. Cấu hình cân bằng cho CLI sống ngắn (`<15 ms`) là giữ `+crt-static` để chạy độc lập (zero-dependency), nhưng hạ xuống `lto = "thin"`, `strip = "symbols"` (hoặc giữ bảng cấu trúc chuẩn), `codegen-units = 1`, `panic = "abort"`, kèm cơ chế kiểm tra/ký local cert hoặc cho phép fallback sang build tại máy đích nếu bị chặn.
3. **Phân phối binary đa hệ điều hành và fallback biên dịch nguồn:** Do Cargo không tự gắn hậu tố nền tảng vào tên binary đầu ra, mẫu chuẩn cho CLI plugin đa OS là lưu hoặc tải theo định danh target triple / cặp `<os>-<arch>` (ví dụ `bin/tdq-hook-x86_64-pc-windows-msvc.exe`, `bin/tdq-hook-aarch64-apple-darwin`, `bin/tdq-hook-x86_64-unknown-linux-musl`), tại bước `tdq_setup.py` chọn đúng binary cho máy hiện tại và chép/trỏ về đường dẫn thực thi cố định; khi thiếu binary khớp OS/arch (hoặc không chạy được), installer tự động chạy `cargo build --release --manifest-path ...` nếu máy có `cargo`, và rơi tiếp về đường Python hiện hữu nếu không có Rust toolchain.

---

## (b) Bảng ánh xạ truy vấn -> nguồn -> bài học kỹ thuật cho TDQ

| # | Truy vấn trọng tâm | Nguồn đối chiếu chính | Bài học kỹ thuật cụ thể cho TDQ (`Engineering Takeaway`) |
|---|---|---|---|
| 1 | Hành vi `std::fs::File::try_lock` / `lock_shared` trên Windows (`LockFileEx`) so với Unix (`flock`) và lỗi `ERROR_LOCK_VIOLATION` | - [Rust std `std::fs::File` (`lock`, `try_lock`, `lock_shared`)](https://doc.rust-lang.org/std/fs/struct.File.html)<br>- [Microsoft Win32 `LockFileEx`](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-lockfileex)<br>- [Case study xung đột multi-handle `ERROR_LOCK_VIOLATION`](https://github.com/compozy/compozy/issues/717) | **Tuyệt đối không gọi `File::lock()` trực tiếp lên `state.json` / `observe.jsonl`.** Luôn khóa trên tệp sidecar riêng (ví dụ `<file>.lock` mở với quyền `.read(true).write(true).create(true)` — không mở `.append(true)` đơn độc vì Windows từ chối khóa handle chỉ-append). Nhờ đó script Python hoặc công cụ ngoài đọc `state.json` không khóa vẫn không dính `ERROR_LOCK_VIOLATION`, còn các writer Rust/Python đồng bộ qua sidecar `.lock`. Trong cùng tiến trình Rust, không mở lại đường dẫn `.lock` lần 2 khi đang giữ khóa. |
| 2 | Lưu ý khi biên dịch `x86_64-pc-windows-msvc` với `+crt-static` + release profile (`lto`, `codegen-units`, `panic = "abort"`, `strip`) đối với Defender và cold-start | - [Rustup / Rust CLI Windows Defender heuristic false-positive (`rust-lang/rustup#4891`)](https://github.com/rust-lang/rustup/issues/4891)<br>- [Microsoft Security Intelligence Portal](https://www.microsoft.com/en-us/wdsi/filesubmission) | **Dùng `lto = "thin"` và `strip = "symbols"` thay vì `lto = true` + `strip = true` toàn phần** khi kết hợp `+crt-static` và `panic = "abort"` để giảm xác suất nhận diện nhầm `Wacatac.B!ml` trên binary chưa ký Authenticode. Với hook CLI chạy hàng chục nghìn lần/tuần trong cache RAM của OS, `+crt-static` loại bỏ phụ thuộc `vcruntime140.dll` và khởi động chỉ vài mili-giây sau lần nạp đầu. Nếu biên dịch bằng `cargo build --release` ngay trên máy người dùng ở bước cài đặt, SmartScreen/Mark-of-the-Web ít chặn hơn so với binary tải trực tiếp từ Internet không chữ ký. |
| 3 | Mẫu đặt tên phân phối binary đa nền tảng (`bin/`) kèm cơ chế fallback `cargo build --release` khi cài CLI plugin | - [Rust Users Forum — Đặt tên binary theo target triple](https://users.rust-lang.org/t/auto-rename-binary-target-according-to-triple/105991)<br>- [Orhun Parmaksız — Đóng gói & phân phối Rust CLI đa nền tảng](https://blog.orhun.dev/packaging-rust-for-npm/)<br>- [Sentry Engineering — Phân phối prebuilt binary kèm install fallback](https://blog.sentry.io/publishing-binaries-on-npm/) | **Chuẩn hóa chuỗi cung ứng 3 bậc trong `tdq_setup.py`:** (1) Tra cứu binary đóng sẵn theo bảng ánh xạ `(sys.platform, platform.machine())` sang tên chuẩn `bin/tdq-hook-<target-triple>[.exe]` và chạy thử `--version` để xác minh thực thi được (không lỗi glibc/arch/AV); (2) Nếu vắng binary cho nền tảng đích hoặc smoke-check thất bại, kiểm tra `shutil.which("cargo")` và chạy `cargo build --release` tại chỗ để sinh binary bản địa; (3) Nếu máy không có `cargo`, giữ nguyên cấu hình fallback sang Python script để plugin không bao giờ gãy cài đặt. |

---

## (c) Phân tích chi tiết từng chủ đề

### 1. `std::fs::File::lock` / `try_lock` / `lock_shared` (Windows `LockFileEx` vs Unix `flock`)

Từ Rust 1.89, thư viện chuẩn ổn định nhóm API khóa tệp trên `std::fs::File`: `lock()`, `lock_shared()`, `try_lock()`, `try_lock_shared()` và `unlock()`. Dù bề mặt kiểu trả về đồng nhất (`TryLockError::WouldBlock` khi khóa đang bận), cơ chế hạt nhân bên dưới khác biệt căn bản:

- **Trên Unix (`flock`):** Hệ điều hành áp dụng khóa **khuyến nghị (advisory)** gắn với *open file description*. Nếu tiến trình Rust gọi `file.lock()` (tương ứng `flock(fd, LOCK_EX)`), một tiến trình khác (chẳng hạn script Python đọc `open("state.json").read()` mà không gọi `fcntl.flock`) **vẫn đọc/ghi bình thường**, không gặp lỗi I/O từ kernel.
- **Trên Windows (`LockFileEx`):** Rust gọi `LockFileEx` khóa toàn bộ dải byte của tệp (`LOCKFILE_EXCLUSIVE_LOCK` cho `lock`/`try_lock`, bỏ cờ này cho `lock_shared`/`try_lock_shared`, thêm `LOCKFILE_FAIL_IMMEDIATELY` cho biến thể `try_*`). Đây là **khóa bắt buộc (mandatory byte-range lock)** do nhân NT thực thi trực tiếp trên đường dẫn I/O:
  - Khi Handle A đang giữ `File::lock()` độc quyền trên tệp `X`, mọi lệnh `ReadFile` hoặc `WriteFile` từ Handle B (ở tiến trình khác **hoặc ngay trong cùng tiến trình** nhưng mở từ `File::open(X)` mới) chạm vào vùng byte đã khóa đều bị từ chối tức thì với lỗi Win32 **`ERROR_LOCK_VIOLATION`** (Error Code `33` / `0x21`, trong `std::io::Error` xuất hiện dưới dạng lỗi OS `33` thay vì chờ khóa nhả ra!).
  - Ngược lại, khi Handle A giữ `lock_shared()`, Handle B không khóa vẫn có thể `ReadFile`, nhưng mọi `WriteFile` không khóa từ Handle B sẽ nổ `ERROR_LOCK_VIOLATION`.
  - Ngoài ra, Windows từ chối `LockFileEx` nếu tệp chỉ được mở với cờ `.append(true)` mà không bật `.read(true)` hoặc `.write(true)`.

**Thiết kế áp dụng cho TDQ Hook Binary:**
- **Sidecar `.lock` bắt buộc:** Tách riêng tệp điều phối khóa (ví dụ `.tdq-state.lock` hoặc `<target>.lock` mở bằng `OpenOptions::new().read(true).write(true).create(true).open(...)`, trên Windows mặc định Rust truyền `FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE` nên không nổ `ERROR_SHARING_VIOLATION` lúc mở).
- **Đọc không khóa an toàn trên Windows:** Nhờ khóa nằm ở tệp `.lock` (không ai gọi `ReadFile`/`WriteFile` dữ liệu nghiệp vụ lên `.lock`), còn tệp `state.json` được cập nhật theo mẫu ghi tệp tạm cùng thư mục rồi đổi tên nguyên tử (`atomic rename`), các bước đọc nhanh (`PreInvocation`, `PreToolUse`) hoặc các script Python song hành có thể đọc `state.json` mà không bao giờ dính `ERROR_LOCK_VIOLATION`.
- **Với tệp nhật ký nối đuôi (`jsonl`):** Nếu nhiều hook cùng ghi vào một tệp log/counter, cả bên ghi Rust lẫn bên ghi Python đều phải lấy khóa qua cùng tệp sidecar `.lock` trước khi append, tránh khóa trực tiếp lên chính tệp `.jsonl`.

### 2. Cấu hình `x86_64-pc-windows-msvc` (`+crt-static` + release profile), Defender và Cold-Start

Trong hệ thống hook đồng bộ của Antigravity/Claude/Codex, binary điều phối được gọi ở mỗi lượt model và mỗi lần gọi tool (`11.241` model calls + `17.429` bước tool trong 4 ngày khảo sát trước đó, so với baseline `python.exe` tốn `~26 ms` và `py -3` tốn `~43,6 ms` chỉ để khởi động). Khi đóng gói binary trên Windows:

- **Tác động của `target-feature=+crt-static`:**
  - *Ưu điểm:* Liên kết tĩnh `libcmt.lib` thay vì `msvcrt.lib` / `vcruntime140.dll`, giúp `.exe` chạy ngay trên máy Windows sạch chưa cài gói *Visual C++ Redistributable*.
  - *Nhược điểm kích thước & cold-start đầu tiên:* Kích thước tệp `.exe` tăng thêm khoảng `100–250 KB` mã runtime tĩnh. Ở lần chạy lạnh đầu tiên sau khi khởi động máy (chưa nằm trong Windows Standby/File System Cache), OS phải đọc thêm vài trang nhớ từ đĩa. Tuy nhiên, từ lần gọi thứ hai trở đi (đặc trưng của hook liên hoàn trong một phiên agent), ảnh thực thi nằm sẵn trong page cache của RAM nên thời gian spawn thực tế chỉ còn `~2–5 ms`, nhanh hơn gấp `8–15` lần so với khởi chạy Python interpreter.
- **Tương tác với Windows Defender (`Wacatac` / `!ml` heuristics):**
  - Thực tế từ cộng đồng Rust và `rust-lang/rustup#4891` cho thấy binary Windows biên dịch không có chữ ký Authenticode khi bật đồng thời `+crt-static`, `lto = true` (fat LTO), `panic = "abort"` và `strip = true` (xóa sạch symbol + bảng phụ) thường bị mô hình máy học của Defender đánh dấu nhầm là dropper nén/ẩn danh (`Trojan:Win32/Wacatac.B!ml`). Nếu Defender thực hiện quét đám mây đồng bộ (cloud block at first sight) hoặc cách ly tệp, lần gọi hook đầu tiên có thể bị treo vài trăm mili-giây đến vài giây hoặc thất bại với `PermissionDenied` / `os error 225`.
  - Binary biên dịch cục bộ ngay trên máy người dùng (`cargo build --release`) không mang luồng dữ liệu phụ *Mark-of-the-Web* (`Zone.Identifier`) nên ít bị SmartScreen và quét đám mây giữ chân hơn binary tải rời không chữ ký.

**Khuyến nghị cấu hình `.cargo/config.toml` và `Cargo.toml` cho TDQ:**
- Chỉ bật `+crt-static` có điều kiện cho target MSVC (`[target.x86_64-pc-windows-msvc] rustflags = ["-C", "target-feature=+crt-static"]`), không ép cờ này lên `x86_64-unknown-linux-gnu` (vì static glibc trên Linux gây lỗi NSS/DNS; trên Linux nếu cần tĩnh hoàn toàn thì dùng target `musl`).
- Trong `[profile.release]`: dùng `lto = "thin"`, `codegen-units = 1`, `panic = "abort"`, `strip = "symbols"` (tránh `strip = true` xóa quá sâu metadata PE trên Windows). Giữ binary nhỏ gọn (thường `< 1,5 MB` nếu chỉ dùng `std` + `serde_json` tối giản, không kéo runtime async nặng như `tokio`).

### 3. Phân phối Binary đa OS (`bin/`) và cơ chế Fallback sang nguồn

Vì plugin TDQ được cài đặt qua kho mã nguồn / thư mục cục bộ (`tdq_setup.py`) trên Windows, macOS (Intel & Apple Silicon) và Linux (x86_64 & ARM64), việc quản lý thực thi cần tách bạch **nơi lưu trữ binary theo nền tảng** và **điểm vào thống nhất trong `hooks.json`**:

1. **Quy ước đặt tên theo Target Triple chuẩn của Rust:**
   - `bin/tdq-hook-x86_64-pc-windows-msvc.exe`
   - `bin/tdq-hook-aarch64-pc-windows-msvc.exe` (tùy chọn mở rộng)
   - `bin/tdq-hook-aarch64-apple-darwin`
   - `bin/tdq-hook-x86_64-apple-darwin`
   - `bin/tdq-hook-x86_64-unknown-linux-musl` (ưu tiên `musl` thay vì `gnu` trên Linux để không lệ thuộc phiên bản `GLIBC_2.xx` giữa Ubuntu cũ, Debian, Alpine)
   - `bin/tdq-hook-aarch64-unknown-linux-musl`
2. **Cơ chế phân giải & cài đặt trong `tdq_setup.py` (Install-time Resolution, không tốn chi phí Runtime Wrapper):**
   - Khác với gói npm thường đặt một Node.js wrapper (`wrapper.js`) chạy ở *mọi lần gọi* (làm mất lại `25–40 ms` spawn Node mỗi lần chạy hook!), TDQ phải phân giải **một lần lúc chạy `tdq_setup.py`**:
     - **Bước 1 (Prebuilt):** Dò `(os, arch)` hiện tại -> kiểm tra tệp tương ứng trong `bin/`. Nếu tồn tại, cấp quyền thực thi (`chmod +x` trên Unix), chạy kiểm chứng nhanh `tdq-hook --self-check` (xác nhận exit `0`, không bị OS/AV/kiến trúc chặn).
     - **Bước 2 (Source Fallback):** Nếu chưa có prebuilt binary cho kiến trúc máy (hoặc `--self-check` lỗi) và phát hiện `cargo` trong `PATH`, chạy `cargo build --release --manifest-path rust/tdq-hook/Cargo.toml` để biên dịch trực tiếp binary bản địa tối ưu cho máy đó.
     - **Bước 3 (Python Fallback an toàn):** Nếu không có cả prebuilt lẫn `cargo` (hoặc người dùng chưa duyệt cài toolchain), `tdq_setup.py` ghi nhận trạng thái và sinh `hooks.json` trỏ về script Python hiện hữu như cũ — đảm bảo tính chất tự phục hồi (graceful degradation), không bao giờ làm hỏng môi trường làm việc.
   - Khi Bước 1 hoặc Bước 2 thành công, `tdq_setup.py` chép binary đã kiểm chứng ra đường dẫn đích cố định của bản cài plugin (ví dụ `<plugin_dir>/bin/tdq-hook[.exe]`) và xuất `hooks.json` gọi **trực tiếp** binary này mà không qua bất kỳ lớp shell/Python/Node trung gian nào.
