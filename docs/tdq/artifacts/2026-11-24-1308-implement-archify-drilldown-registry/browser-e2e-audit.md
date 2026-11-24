# Browser E2E Audit — Archify Drill-Down Portal & Standalone Drilldown

## Tóm tắt kiểm thử sống (Chrome DevTools MCP)

Kiểm thử trình duyệt thật trên `tdq-workflow-agy_chrome-devtools` cho cả 3 kịch bản phân phối của Option A:
- Portal qua máy chủ HTTP cục bộ (`tdq_archify.py serve docs/architecture --port 8765`): `http://127.0.0.1:8765/`
- Portal mở trực tiếp từ đĩa qua giao thức `file://` (`registry-bundle.js` fallback): `file:///C:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/architecture/index.html`
- Bản render độc lập `render --type drilldown`: `file:///C:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/artifacts/2026-11-24-1308-implement-archify-drilldown-registry/drilldown-sample.html`

## Chỉ số kiểm chứng bắt buộc

- `depth=4`
- `console_errors=0`
- `file_fallback=PASS`
- `standalone_drilldown=PASS`
- `lazy_slice_http_200=PASS`

## Nhật ký kiểm thử tương tác

### 1. HTTP Portal (`http://127.0.0.1:8765/`)
1. Mở trang ban đầu: Title `TDQ-Workflow — Master Architecture Portal`, 2 nút luồng gốc (`Luồng Cổng Chặn Hooks & Verify-by-Effect`, `Luồng Tìm Kiếm 3 Tầng & Đồng Bộ Archify Portal`), breadcrumb `Tổng quan › Tầng 1: ...`, shell `< 300 KB` (`205,750` bytes), `registry-bundle.js` (`269,810` bytes).
2. Đi sâu 4 tầng (`depth=4`) trên cụm Pilot Hooks:
   - Tầng 1: `flow_hooks_gates` (4 bước con trong `#drawer-mini-flow` + sơ đồ tổng quan)
   - Click `gate_stop_verify` → Tầng 2 (`Cổng Stop Verify-by-Effect & Vòng Lặp Sửa Lỗi`), nạp slice SVG và panel giải thích tiếng Việt (`Tóm tắt`, `Dữ liệu đi đâu`, `Vì sao tồn tại`, `Trường hợp biên`, `Đầu vào`, `Đầu ra`, `Tác động phụ`, chip nguồn `hooks/scripts/stop_gate.py:274-387`)
   - Click neo chu trình `↺ Sửa -> chạy lại Hook` (`cycle -> flow_hooks_gates`): hiển thị biểu ngữ `↺ Quay về "Luồng Cổng Chặn Hooks & Verify-by-Effect" (Tầng 1)` với nút `Nhảy về tầng này`, không sinh thêm tầng lặp vô hạn.
   - Click `stop_disk_diff_check` trên SVG chính → Tầng 3 (`Đối Chiếu Dấu Vân Tay Repo Đầu/Cuối Lượt`), mạng ghi nhận nạp lười `GET http://127.0.0.1:8765/slices/slice-stop-disk-diff-check.svg [200]`.
   - Click `detail_stop_unfinished_check` trên SVG chính → Tầng 4 (`Hàm Thuần Kiểm Tra Task Kế Hoạch Còn Mở`), breadcrumb đủ 4 tầng, panel hiển thị `Nút lá — không có tầng con sâu hơn.` và `hooks/scripts/stop_gate.py:155-175`.
3. Chuyển luồng sang `flow_search_archify` và tìm kiếm `#portal-search` với từ khóa `"cycle"` → mở `Bộ Phát Hiện Chu Trình DFS Có Giới Hạn Độ Sâu` (`scripts/archify_registry.py:774-818`), thử nút đổi giao diện `Sáng / Tối`.
4. Sửa lỗi console phát hiện khi kiểm sống: Lần tải HTTP đầu tiên phát hiện 1 lỗi `404 /favicon.ico`; đã thêm `<link rel="icon" href="data:,">` vào `_render_portal_document` (`scripts/archify_portal.py`), chạy lại `sync-master --incremental` (tự nhận `shifted=1`, `0` re-render thừa), reload HTTP bỏ qua cache → `list_console_messages` trả về `0` lỗi/cảnh báo (`console_errors=0`) và `list_network_requests` chỉ có HTTP `200`.

### 2. Fallback ngoại tuyến `file://` (`docs/architecture/index.html`)
- Mở trực tiếp `file:///.../docs/architecture/index.html` (`window.__TDQ_ARCHIFY_REGISTRY__` từ `registry-bundle.js`), bấm đi sâu từ Tầng 1 → Tầng 2 (`gate_stop_verify`) → Tầng 3 (`stop_disk_diff_check`) → Tầng 4 (`detail_stop_unfinished_check`).
- Toàn bộ SVG, giải thích tự nhiên và chip bằng chứng hiển thị đầy đủ không cần HTTP server; `list_console_messages` ghi nhận `0` lỗi/cảnh báo (`file_fallback=PASS`, `console_errors=0`).

### 3. Bản render độc lập `render --type drilldown` (`drilldown-sample.html`)
- Sinh từ `tdq_archify.py render --type drilldown` (`engine=archify-portal`, `127,540` bytes), mở qua `file://`, bấm đi sâu đủ Tầng 1 → Tầng 2 → Tầng 3 → Tầng 4 từ mini-flowchart nhúng (`buildSubflowSvg`); `list_console_messages` ghi nhận `0` lỗi/cảnh báo (`console_errors=0`).
