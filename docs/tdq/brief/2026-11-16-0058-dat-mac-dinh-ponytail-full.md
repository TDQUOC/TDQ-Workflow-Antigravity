# Brief: Đặt lại mặc định mức gắt Ponytail (muc_gat) về full

Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

## Nguyên văn

- **Lời người dùng:** "Set lại mặc định ở mức full thôi"
- **Mục tiêu đọc lần đầu:**
  1. Đổi mức gắt mặc định và mức dự phòng fail-closed của luật tinh gọn Ponytail (`muc_gat`) từ `ultra` về lại `full` trên state mới, state thiếu khoá hoặc mang giá trị không hợp lệ.
  2. Đồng bộ bộ lọc thân luật trong hook, bảng cường độ trong tài liệu luật chung, bản plugin Antigravity (`plugins/tdq-workflow-agy/`) và các unit test kiểm chứng mặc định `muc_gat`.
  3. Giữ nguyên khả năng chọn tường minh `lite`, `full`, `ultra`, `off` và giữ nguyên `muc_qc` mặc định `full`.

## Hiểu & kiến thức

### Khảo sát mã nguồn 3 chiều (Triangulation B1)

| Chiều khảo sát | Công cụ & Truy vấn | Phát hiện chính |
|---|---|---|
| Grep diện rộng | `git grep -n "MUC_GAT_MAC_DINH\|MUC_MAC_DINH\|muc_gat"` | Chỉ có `2` hằng mặc định gốc: `MUC_GAT_MAC_DINH = "ultra"` tại `scripts/tdq_state.py:166` và `MUC_MAC_DINH = "ultra"` tại `hooks/scripts/luat_gon.py:33`, kèm bảng cường độ tại `skills/tdq-build/references/rules/chung.md:143-150`. |
| LSP cấu trúc | `find_references` trên `MUC_GAT_MAC_DINH` (`symbols=4`) và `muc_gat_hieu_luc` (`symbols=12`) | `prompt_context.py`, `session_start.py`, `subagent_start.py`, `render_next()` và `render_state_md()` đều đọc qua `muc_gat_hieu_luc(state)` chứ không gán cứng `"ultra"`. |
| Graphify vỡ lan | `graphify query "muc_gat MUC_GAT_MAC_DINH luat_gon"` (`depth=2`, `133` nút) | Vùng chạm lan sang khóa `docs/tdq/token-budget.json` (khi sửa `chung.md`), trình biên dịch `tools/build_agy_plugin.py` → `plugins/tdq-workflow-agy/` (kèm `tools/install_agy_plugin.py`), và `3` tệp test (`tests/test_state_muc_gat.py`, `tests/test_luat_gon.py`, `tests/test_state_muc_qc.py`). |

### Quy tắc nghiệp vụ đã chốt
- `default_state()["muc_gat"] == "full"`, `normalize_muc_gat(<rác/rỗng/None>) == "full"`, `loc_than_luat(than, <rác/rỗng/None>)` lọc giống `"full"` (giữ bảng cường độ, cắt ví dụ dài và mục riêng của `ultra`).
- Giá trị hợp lệ tường minh `lite`, `full`, `ultra`, `off` giữ nguyên; `muc_qc` giữ mặc định `full` và độc lập hoàn toàn với `muc_gat`.

## Hỏi đáp

- **2026-11-16T01:04:13+07:00 — Chọn pipeline & loại request:**
  - Câu hỏi: `1. Bạn muốn chạy pipeline nào?` (`A`: express · `B`: deep; đề xuất `loai_request = chore`).
  - Người dùng trả lời nguyên văn: `"1a"` → chốt `lane = quick`, `loai_request = chore`, mở nhánh `chore/dat-mac-dinh-ponytail-full` từ `dev`.
