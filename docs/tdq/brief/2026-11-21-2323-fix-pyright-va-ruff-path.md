# BRIEF — Cấu hình Pyright quét tools/ và đưa ruff vào PATH

Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

## Nguyên văn

> "Xử lí 1,2 bỏ qua 3,4"

Đọc hiểu ban đầu:

- **Mục tiêu:** Xử lý 2 điểm đã nêu ở phần Giới hạn ghi nhận, bỏ qua mục 3 (`eval` opt-in) và mục 4 (nợ `i18n_check` có sẵn trên nhánh `dev`).
- **Mục 1 (Cổng LSP / Pyright):** Cập nhật cấu hình phân tích Python (`pyrightconfig.json`) để quét thêm thư mục `tools/` (gồm `tools/patches/`), tránh lỗi bỏ sót tham chiếu ngoài phạm vi khi kiểm tra hiệu ứng LSP đầu phiên.
- **Mục 2 (`ruff` trong PATH):** Đưa lệnh `ruff` vào đường dẫn thực thi `PATH` ở mức người dùng. Hiện `ruff.exe` (`0.17.3`) đã cài tại `C:\Users\admin\AppData\Roaming\Python\Python313\Scripts\ruff.exe`, trong khi `PATH` đang trỏ tới `~/.local/bin` và thư mục `Scripts` của Python cài đặt chứ chưa chứa thư mục `Roaming\...\Scripts`.
- **Điểm cần chốt:** Chọn cách lộ diện `ruff` mức người dùng (thêm đường dẫn vào User `PATH` hoặc tạo shim tại `~/.local/bin`) và phạm vi kiểm thử sau khi chỉnh `pyrightconfig.json`.

## Hiểu & kiến thức

- **Mục 1 (`pyrightconfig.json`):** Tệp gốc hiện chỉ khai báo `"include": ["scripts", "hooks", "tests"]` và `"extraPaths": ["scripts", "hooks/scripts"]`. Kịch bản kiểm tra hiệu ứng LSP (`scripts/tdq_lsp.py kich-ban`) bốc `generate_manifest_and_readme` tại `tools/patches/agy_manifests.py:259` nên Pyright không index thư mục `tools/`. Cần bổ sung `"tools"` vào `"include"` và `"extraPaths"`, đồng thời thêm `"plugins"` vào `"exclude"` để tránh index trùng bản biên dịch.
- **Mục 2 (`ruff` và tự thêm User `PATH`):** Tệp `ruff.exe` (`0.17.3`) đã cài sẵn tại `C:\Users\admin\AppData\Roaming\Python\Python313\Scripts\ruff.exe`, nhưng thư mục `Scripts` user-site này chưa nằm trong `PATH` (trong khi `~/.local/bin` và `Python313\Scripts` đã có). Mô-đun `scripts/tdq_checkportable.py:492` đã có sẵn `them_thu_muc_user_path_windows(thu_muc)` và `scripts/tdq_setup.py:1001` đã gắn `kiem_va_cai_shim_python3()` tại 3 điểm khởi tạo (`thuc_hien_setup_bu:1530`, `khoi_tao_nen:1816`, `main:2074`).
- **Hướng giải quyết chung cho các ca như mục 2:** Thêm hàm `dam_bao_user_scripts_tren_path()` trong `scripts/tdq_checkportable.py`. Hàm này tìm các thư mục `Scripts` của Python user-site đang tồn tại và có công cụ thực thi (`.exe`/`.cmd`/binary) sẵn có, rồi tự động nạp vào `os.environ["PATH"]` và User `PATH` (`HKCU\Environment\Path`) khi thiếu. Cơ chế này chạy theo quyền user hiện có, không cài thêm gói mới và tôn trọng cờ `TDQ_KHONG_CHAM_MAY=1`.
- **Đồng bộ luật & gói:** Nối hàm mới vào `scripts/tdq_setup.py`, đồng bộ câu luật tự phục hồi tại `docs/claude-md-mau.md:73` và `scripts/tdq_setup.py:1115` (còn 329 byte trống dưới trần 12.500 byte), chạy thực tế để đưa `ruff` vào `PATH` và dựng lại `plugins/tdq-workflow-agy/`.

## Hỏi đáp

- Người dùng trả lời: `"1a và những case như 2 thì cho phép auto add path"`.
- Kết luận: chọn Express lane (`quick`), `loai_request=chore`, được phép tự động bổ sung thư mục công cụ Python user-level có sẵn vào User `PATH`.
