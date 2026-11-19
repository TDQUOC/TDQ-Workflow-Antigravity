# Trước/Sau — Đóng gói Rust binary cho tầng hook Antigravity {#tong-quan}

@meta locale=en

Hiện trạng: gói Antigravity chạy hook qua trình thông dịch Python `python -X utf8 dispatch.py`. Khởi tạo CPython VM tốn `188–198 ms` mỗi sự kiện. Thiết kế mới thay thế bằng standalone Rust binary `tdq-dispatch`. Tốc độ thực thi trực tiếp đạt trung vị `19,90 ms` (nhanh hơn 9,6 lần) và qua `cmd.exe /c` đạt `28,37 ms` (nhanh hơn 7,0 lần). Hệ thống hỗ trợ khóa an toàn sidecar và cơ chế dự phòng Python.

## Trước: Khởi tạo CPython VM mỗi lần gọi hook và phụ thuộc môi trường {#truoc}

@workflow id=hook-rust-truoc title="Hiện trạng: Chạy hook qua CPython VM tốn độ trễ khởi động"
| agy_ev_old | Sự kiện hook Antigravity | external |
| cmd_spawn | Vỏ cmd.exe /c hoặc sh -c | messagebus |
| cpython_vm | CPython VM python -X utf8 | backend |
| python_hook | 17 tệp Python trong gói hook | security |
| agy_ev_old > cmd_spawn | 10-15ms |
| cmd_spawn > cpython_vm | 180-190ms nạp VM |
| cpython_vm > python_hook | Tổng 198ms qua cmd |

Mỗi sự kiện gọi hook đều phải nạp lại toàn bộ trình thông dịch CPython. Quá trình này tốn nhiều tài nguyên CPU và làm chậm các thao tác gõ lệnh. Nếu môi trường thiếu thư viện hoặc lỗi đường dẫn, hook sẽ ngừng hoạt động.

## Sau: Standalone Rust binary tdq-dispatch với sidecar lock và fallback {#sau}

@workflow id=hook-rust-sau title="Thiết kế mới: Native Rust binary siêu tốc với sidecar lock an toàn"
| agy_ev_new | Sự kiện hook Antigravity | external |
| cmd_fast | Vỏ cmd.exe /c hoặc sh -c | messagebus |
| rust_binary | tdq-dispatch native binary | backend |
| safe_engine | Sidecar lock và fallback Python | security |
| agy_ev_new > cmd_fast | 8-10ms |
| cmd_fast > rust_binary | 19.90ms thực thi |
| rust_binary > safe_engine | Trung vị 28.37ms qua cmd |

Tiến trình native Rust được biên dịch tĩnh CRT và không cần runtime bên ngoài. Thao tác ghi được bảo vệ bằng tệp sidecar `.lock` tránh lỗi khóa tệp Windows. Nếu thiếu binary, hệ thống tự động chuyển tiếp xử lý sang script Python an toàn.

## Đóng gói đa nền tảng và phân giải đường dẫn 0-overhead {#phan-phoi}

@workflow id=hook-rust-phan-phoi title="Đóng gói 3 nền tảng và tự phân giải đường dẫn lúc cài đặt"
| pack_bin | 3 prebuilt binary trong bin/ | external |
| install_step | Bộ cài đặt install.py | messagebus |
| config_json | hooks.json chuẩn theo hệ điều hành | backend |
| ci_matrix | GitHub Actions 3 OS matrix | security |
| pack_bin > install_step | Windows, Linux, macOS |
| install_step > config_json | Phân giải 1 lần duy nhất |
| ci_matrix > pack_bin | Tự động biên dịch phát hành |

Đường dẫn lệnh hook được phân giải chuẩn xác một lần duy nhất lúc cài đặt. Trên Windows dùng `bin\tdq-dispatch.exe`, trên Unix dùng `./bin/tdq-dispatch`. Không phát sinh thêm lớp vỏ wrapper giúp loại bỏ hoàn toàn độ trễ dư thừa.
