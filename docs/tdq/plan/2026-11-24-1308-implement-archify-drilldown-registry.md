# PLAN — Triển khai trọn bộ cải thiện Archify (Drill-down nhiều tầng, Logic Node Registry và Tree-sitter Setup)

Ngày: 2026-11-24 · Spec: ../spec/2026-11-24-1308-implement-archify-drilldown-registry.md (bản 1.0, ĐÃ DUYỆT)
Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md
Mode thực thi: subagent — simulate chọn đội (chênh 9.1 phút: `subagent` 15.3 phút vs `main` 24.4 phút ở hệ số 1.5 trên 12 task, 5 đợt song song, 0 hot file; Leader giữ `T3.3` mang nhãn `(mcp)` và `T4.2`) (ĐỀ XUẤT, user chốt lúc duyệt)
Trạng thái plan: HOÀN THÀNH

> **Tóm tắt dễ hiểu:** Kế hoạch chia thành bốn đợt tách biệt để không có hai việc nào đụng chung một file. Đợt một dựng kho Logic Node dùng tree-sitter và vá danh sách bỏ qua cùng HTTP cục bộ. Đợt hai làm vỏ HTML drill-down nhẹ dưới 300 KB và nối vào lệnh chính. Đợt ba và bốn chạy thí điểm bốn tầng thật, đồng bộ gói plugin Antigravity và kiểm chứng trình duyệt Chrome.

## Mục lục

- Phân bổ Model & Effort
- Quy tắc thi hành (áp cho mọi task)
- Thiết kế Trước vs Sau
- Ràng buộc toàn cục & Bản đồ Sở hữu Hợp đồng (Ownership Map)
- P1 — Lõi Registry (`tree-sitter`), Artifacts, Delivery & Setup
- P2 — Vỏ HTML Drill-Down Portal, Validator Model & CLI Orchestrator
- P3 — Cụm Pilot 4 tầng, Hướng dẫn Skill, Đóng gói AGY & Kiểm thử Chrome
- P4 — Log & Test bắt buộc
- Cụm song song
- Luật file nóng (một file, nhiều task chạm)
- Definition of Done

## Phân bổ Model & Effort
<!-- i18n-allow: canonical model/effort plan allocation table -->
> User được quyền đổi `type model` hoặc `effort` lúc duyệt plan. Thang model: [subagent-tuning.md](../../tdq-conventions/references/subagent-tuning.md).

| Pha | Vai trò | Model | Effort | Ghi chú |
|---|---|---|---|---|
| `implement` (P1–P3 code) | `tdq-implementer` / Leader | `inherit` | `high` | Có thể đổi model khi duyệt; task có nhãn `(mcp)` (`T3.3`) Leader tự chạy |
| `implement` (P4 regression) | Leader | `inherit` | `medium` | Gom bộ unit test vùng chạm + log `TDQ_LOG=1/0` |
| `qc` (`muc_qc=full`) | Leader | `inherit` | `high` | Chạy đủ `Q1`–`Q6`, `QC-F1`–`F4` và trọn bộ test (không cần subagent QC riêng ở mức `full`) |
| `report` | Leader | `inherit` | `medium` | Xuất báo cáo MD + Archify HTML `current` + HTTP 200 Tailscale |

## Quy tắc thi hành (áp cho mọi task)

1. Thứ tự phụ thuộc (`Cần:`) giữa các task là bắt buộc — không đảo thứ tự pha.
2. Mỗi task: đánh `[~]` (hoặc `[>]` khi giao subagent) trước khi chạm file → viết test đỏ thật (`Red`) → code sạch → test xanh (`Green`) → đổi sang `[x]` NGAY vào file này.
3. Giữa các task chạy `py -3 -X utf8 scripts/tdq_test.py vung-cham`; trọn bộ suite chỉ chạy ở pha QC (`QC-F1`).
4. Mọi lệnh chạm state workflow trong test phải truyền `TDQ_PROJECT_DIR=<tempdir>` và `TDQ_KHONG_CHAM_MAY=1` để cô lập tuyệt đối.
5. QC FAIL → thêm task sửa `QCn.x` vào mục QC của file này, không cần duyệt lại plan, chạy lại đến khi PASS.
6. Không commit, merge nhánh `main` hay push cho đến khi user yêu cầu rõ.
7. Tuân thủ đủ 6 mã cấm cơ học (`ANTI-1` đến `ANTI-6`), giữ `0` chỉnh sửa trên `C:\Users\admin\Documents\archify` và không tiêm `onclick` vào node SVG native.

## Thiết kế Trước vs Sau

| Khía cạnh | Hiện trạng (Trước) | Thiết kế mới (Sau) |
|---|---|---|
| Luồng thực thi | `master.model.json` 1 tầng → băm toàn tệp 5,804 file (gồm `target/`) → render lại cả 6 view (~20.3s) → nhúng lặp 6 × ~276 KB `htmlGzip` vào `index.html` (2.62 MB) | `archify_registry.py` quét AST `tree-sitter` lọc `D` lát bẩn → `tt-a1i/archify` vẽ SVG lát `<= 5` node → `archify_portal.py` xuất 1 vỏ `< 300 KB` tải lười đa tầng + `render --type drilldown` tự chứa + `serve` cục bộ |
| Thành phần chạm | `scripts/{archify_model,archify_artifacts,archify_delivery,tdq_archify}.py`, `scripts/tdq_setup.py`, `docs/tdq/models/master.model.json`, `skills/*/references/archify-*.md` | Thêm `scripts/archify_registry.py`, `scripts/archify_portal.py`, `docs/tdq/models/registry/`, nâng cấp 5 module hiện có + đồng bộ `plugins/tdq-workflow-agy/` |

*Đối chiếu sơ đồ kiến trúc:* Tham chiếu trực tiếp bản xem trước Archify đã duyệt và xác minh `current` tại `docs/tdq/spec/2026-11-24-1308-implement-archify-drilldown-registry-preview.html` cùng manifest `docs/tdq/spec/2026-11-24-1308-implement-archify-drilldown-registry-preview.manifest.json`. WBS bên dưới ánh xạ 1–1 sang 6 đầu ra §2, 8 module §2b, 12 hợp đồng §3c và 6 cổng `Q1`–`Q6` của spec đã duyệt.

## Ràng buộc toàn cục & Bản đồ Sở hữu Hợp đồng (Ownership Map)

- Ràng buộc chung: Ngôn ngữ English cho comments/docstring/CLI trong `scripts/` và nội dung `skills/` (`scripts/i18n_check.py`) · `utf8_io` · Log service bật mặc định có ISO timestamp, tắt khi `TDQ_LOG=0` · hàm `<= 50` dòng (`cyc <= 10`) · `scripts/` không import `hooks/` · giữ nguyên 100% chữ ký công khai cũ và 17 cụm từ hợp đồng trong `test_archify_workflow_contract.py`.

| Hợp đồng / Ký hiệu (§3c) | File & Task sở hữu | Task / File tiêu thụ |
|---|---|---|
| `TREE_SITTER_PACKAGES`, `check_tree_sitter_support`, `extract_symbol_ast_hash`, `validate_logic_node`, `detect_cycles`, `compute_dirty_set`, `sync_registry_index` | `scripts/archify_registry.py` (`T1.1`) | `T1.4`, `T2.1`, `T2.2`, `T2.3`, `T3.1`, `T4.1` |
| `EXCLUDED_DIR_NAMES` (`target`, `.pytest_cache`) & manifest lát cắt | `scripts/archify_artifacts.py` (`T1.2`) | `T2.3`, `T3.1` |
| `serve_directory(directory, host, port, open_browser)` | `scripts/archify_delivery.py` (`T1.3`) | `T2.3`, `T3.3`, `T4.1` |
| `kiem_tra_tree_sitter`, `ensure_tree_sitter_installed` | `scripts/tdq_setup.py` (`T1.4`) | `T3.2`, `T4.1`, `T4.2` |
| `build_portal_shell`, `build_registry_bundle_js`, `render_drilldown_standalone` | `scripts/archify_portal.py` (`T2.1`) | `T2.3`, `T3.1`, `T4.1` |
| `validate_model` (mở rộng `registry` giữ tương thích v1) | `scripts/archify_model.py` (`T2.2`) | `T2.3`, `T3.1` |
| CLI `sync-master --incremental`, `render --type drilldown`, `serve` | `scripts/tdq_archify.py` (`T2.3`) | `T3.1`, `T3.2`, `T3.3` |
| Kho Pilot 4 tầng (`hooks-and-gates` + `search-and-archify`) & `docs/architecture/` | `docs/tdq/models/registry/index.json` (`T3.1`) | `T3.3`, `T4.2` |
| Hợp đồng Skill `tdq-browser-test` / `chrome-devtools` `(mcp)` | `docs/tdq/artifacts/.../browser-e2e-audit.md` (`T3.3`) | `T4.2` & QC `Q5` |

## P1 — Lõi Registry (`tree-sitter`), Artifacts, Delivery & Setup

- [x] **T1.1** (e14m) Xây dựng `scripts/archify_registry.py` (schema Logic Node, hash AST 2 lớp bằng `tree-sitter` 0.25+ cho Python/JS/TS/Rust kèm fallback `python_ast`/`file_fallback`, relink `span_binding`, chống chu trình DFS `visited_stack`, tách `planned` vs `working-tree`) và unit test — Test: `python3 -m pytest tests/test_archify_registry.py -q`
  - Req: `§1, §2#1, §2b, §3c, §4, §6 Q1` · Ngoài phạm vi: `GIỮ NGUYÊN` toàn bộ `scripts/archify_model.py` và engine `C:\Users\admin\Documents\archify`
  - Chạm: `scripts/archify_registry.py` (tạo mới), `tests/test_archify_registry.py` (tạo mới)
  - Cần: Không
  - Giao tiếp: Consumes: file nguồn Python/JS/TS/Rust & JSON Logic Node | Produces: `TREE_SITTER_PACKAGES`, `check_tree_sitter_support`, `extract_symbol_ast_hash`, `validate_logic_node`, `detect_cycles`, `compute_dirty_set`, `sync_registry_index`
  - Neo & Công cụ: tạo mới bằng write_file cho `scripts/archify_registry.py` và `tests/test_archify_registry.py`
  - Trước → Sau: Chưa có kho Logic Node hay bộ băm cấp hàm → Có bộ băm AST `tree-sitter` 2 lớp, tự relink dòng và phát hiện chu trình
  - Tiêu chí chấp nhận (EARS): KHI sửa comment hoặc đẩy hàm xuống 15 dòng trên Python/JS/TS/Rust, HỆ THỐNG PHẢI giữ nguyên `ast_symbol_sha256`, cập nhật `span_binding.line` đúng vị trí mới và trả `dirty_slices == []`; KHI sửa thân hàm, HỆ THỐNG PHẢI đổi `ast_symbol_sha256` và đưa node vào `dirty_nodes`
  - Logic cốt lõi: (1) Duyệt nút khai báo `tree-sitter` lọc bỏ node comment và bỏ tọa độ tuyệt đối trước khi băm SHA-256; (2) Fallback `ast` cho `.py` khi thiếu `tree-sitter`, và `file_fallback` rõ cờ với đuôi file lạ; (3) `detect_cycles` duyệt DFS có `visited_stack` cap `max_depth=6`; (4) `sync_registry_index(..., include_planned=False)` từ chối node `planned`
  - Ca góc hiểm & Assert: Chu trình `A -> B -> A`, file nguồn thiếu, symbol không tồn tại, node `planned` lạc vào Master · `assert res["hash_mode"] == "tree_sitter_ast" and res_shifted["ast_symbol_sha256"] == res["ast_symbol_sha256"] and res_shifted["span_binding"]["line"] == 20 and len(cycles) == 1`

- [x] **T1.2** (e10m) Cập nhật `scripts/archify_artifacts.py` bổ sung `"target"` và `".pytest_cache"` vào `EXCLUDED_DIR_NAMES` cùng helper đóng gói/kiểm chứng danh sách `child_files` mảnh (`slices/`, `nodes/`, `registry-bundle.js`) — Test: `python3 -m pytest tests/test_archify_artifacts.py -q`
  - Req: `§1, §2#3, §2b, §6 Q3` · Ngoài phạm vi: `GIỮ NGUYÊN` luật `stdlib-only` (không import `archify_model`/`archify_delivery`) và chữ ký `build_manifest`/`check_manifest`/`mark_stale`
  - Chạm: `scripts/archify_artifacts.py`, `tests/test_archify_artifacts.py`
  - Cần: Không
  - Giao tiếp: Consumes: `EXCLUDED_DIR_NAMES`, `source_fingerprint`, `build_manifest`, `check_manifest` | Produces: bộ lọc loại bỏ `target`/`.pytest_cache` và kiểm chứng hash đệ quy các tệp con mảnh trong `child_files`
  - Neo & Công cụ: sửa trực tiếp `scripts/archify_artifacts.py` tại `EXCLUDED_DIR_NAMES` (`L32`) và `_check_single_child_file` (`L676`)
  - Trước → Sau: `source_fingerprint` quét cả `hooks/rust/tdq-dispatch/target/` gây stale liên tục → Loại sạch `target/` và `.pytest_cache/`, hỗ trợ đường dẫn con `slices/*.svg`, `nodes/*.json` trong `child_files`
  - Tiêu chí chấp nhận (EARS): KHI tạo tệp trong `target/release/deps/a.rmeta` hoặc `.pytest_cache/v/x`, HỆ THỐNG PHẢI bỏ qua hoàn toàn trong `source_fingerprint`; KHI `child_files` chứa `slices/s1.svg` bị sửa byte, `check_manifest` PHẢI báo `stale`
  - Logic cốt lõi: Thêm `"target"`, `".pytest_cache"` vào `EXCLUDED_DIR_NAMES`; cho phép đường dẫn POSIX tương đối có thư mục con (`slices/...`, `nodes/...`) trong `_check_single_child_file` vẫn giữ chặn `..` và symlink escape
  - Ca góc hiểm & Assert: Đường dẫn `../escape.svg` trong `child_files` bị từ chối fail-closed · `assert "target/x.rmeta" not in fp and res["status"] == "invalid"`

- [x] **T1.3** (e10m) Bổ sung `serve_directory` vào `scripts/archify_delivery.py` phục vụ HTTP cục bộ an toàn trên `127.0.0.1` cho Master Portal và Spec/Report — Test: `python3 -m pytest tests/test_archify_delivery.py -q`
  - Req: `§1, §2#3, §2b, §3c, §4, §6 Q3` · Ngoài phạm vi: `GIỮ NGUYÊN` toàn bộ `run_finalize`, `check_environment`, `atomic_delivery`, `open_artifact`
  - Chạm: `scripts/archify_delivery.py`, `tests/test_archify_delivery.py`
  - Cần: Không
  - Giao tiếp: Consumes: đường dẫn thư mục chứa HTML/SVG/JSON | Produces: `serve_directory(directory: Path, host: str = "127.0.0.1", port: int = 0, open_browser: bool = False) -> tuple[Any, str]`
  - Neo & Công cụ: sửa trực tiếp `scripts/archify_delivery.py` sau `open_artifact` (`L333`)
  - Trước → Sau: Chỉ có `open_artifact` mở URI `file://` dễ đụng CORS `fetch()` → Có server HTTP nội bộ `127.0.0.1` phục vụ mượt `slices/` & `nodes/` với MIME đúng và chặn thoát thư mục
  - Tiêu chí chấp nhận (EARS): KHI gọi `serve_directory` với `host="127.0.0.1", port=0`, HỆ THỐNG PHẢI mở cổng lắng nghe, trả HTTP `200` cho `index.html` và từ chối HTTP `403/404` với đường dẫn `../` hoặc symlink trỏ ngoài root; KHI truyền `host != "127.0.0.1"`, HỆ THỐNG PHẢI ném `ValueError`
  - Logic cốt lõi: Dùng `http.server.ThreadingHTTPServer` + handler tùy biến gắn `Cache-Control: no-store`, xác minh `_is_within` + từ chối symlink, log ISO timestamp (`TDQ_LOG`)
  - Ca góc hiểm & Assert: `host="0.0.0.0"` bị từ chối, thư mục không tồn tại ném `FileNotFoundError` · `assert resp.status == 200 and "127.0.0.1" in url`

- [x] **T1.4** (e12m) Tích hợp `tree-sitter` cùng 4 gói grammar lõi làm dependency chính thức trong `scripts/tdq_setup.py` và viết test cô lập — Test: `python3 -m pytest tests/test_tdq_setup.py tests/test_agy_host_setup.py -q`
  - Req: `§1, §2#4, §2b, §3c, §4, §6 Q4` · Ngoài phạm vi: `GIỮ NGUYÊN` toàn bộ các khóa JSON hiện hữu trong receipt setup và nhánh cài `archify`/`rtk`/`caveman`
  - Chạm: `scripts/tdq_setup.py`, `tests/test_tdq_setup.py`, `tests/test_agy_host_setup.py`
  - Cần: `T1.1`
  - Giao tiếp: Consumes: `archify_registry.TREE_SITTER_PACKAGES`, `check_tree_sitter_support` | Produces: `kiem_tra_tree_sitter() -> tuple[bool, str]`, `ensure_tree_sitter_installed(allow_network: bool = True) -> tuple[bool, str]` nối vào `_build_manifest_actions`, `build_setup_manifest`, `_apply_addons_agy` và luồng setup chuẩn
  - Neo & Công cụ: sửa trực tiếp `scripts/tdq_setup.py` cạnh `kiem_tra_archify` (`L1078`), `ensure_archify_installed` (`L2452`), `_apply_addons_agy` (`L2805`)
  - Trước → Sau: Bộ cài chưa kiểm tra hay tự cài `tree-sitter` → Setup kiểm tra đủ 5 gói `tree-sitter*`, hiển thị trạng thái trong `addons["tree_sitter"]` và cài tự động qua `pip install --user` khi thiếu và được phép nối mạng
  - Tiêu chí chấp nhận (EARS): KHI máy đã có đủ 5 gói `tree-sitter*`, `kiem_tra_tree_sitter()` PHẢI trả `(True, ...)` với phiên bản thật; KHI đặt `TDQ_KHONG_CHAM_MAY=1` hoặc `allow_network=False` và thiếu gói, `ensure_tree_sitter_installed` PHẢI không gọi `subprocess` cài mạng mà trả `(False, ...)` kèm gợi ý cài
  - Logic cốt lõi: Kiểm import `tree_sitter` và 4 gói grammar lõi; khi thiếu & `allow_network=True` & không đặt `TDQ_KHONG_CHAM_MAY=1`, gọi `[sys.executable, "-m", "pip", "install", "--user", *missing]` với timeout rõ ràng
  - Ca góc hiểm & Assert: Thiếu 1 grammar con vẫn báo đúng danh sách gói thiếu, không làm sập bước setup khác · `assert ok is False and "tree-sitter-rust" in detail and pip_called == 0`

**Xong P1 khi**: Cả 4 bài test `test_archify_registry`, `test_archify_artifacts`, `test_archify_delivery`, `test_tdq_setup`/`test_agy_host_setup` đều xanh `0` lỗi.

## P2 — Vỏ HTML Drill-Down Portal, Validator Model & CLI Orchestrator

- [x] **T2.1** (e14m) Xây dựng `scripts/archify_portal.py` sinh vỏ HTML Drill-Down Portal dùng chung (`< 300 KB`), bundle `<script>` fallback cho `file://` và chế độ tự chứa `render_drilldown_standalone` (`<= 4` tầng) cho Spec/Report — Test: `python3 -m pytest tests/test_archify_portal.py -q`
  - Req: `§1, §2#2, §2b, §3c, §4, §6 Q2` · Ngoài phạm vi: `GIỮ NGUYÊN` SVG gốc do `tt-a1i/archify` sinh ra (cấm chèn thuộc tính `onclick` vào thẻ SVG native)
  - Chạm: `scripts/archify_portal.py` (tạo mới), `tests/test_archify_portal.py` (tạo mới)
  - Cần: `T1.1`
  - Giao tiếp: Consumes: `registry_index`, `slices: dict[str, str]`, `nodes: dict[str, dict]` | Produces: `build_portal_shell`, `build_registry_bundle_js`, `render_drilldown_standalone`
  - Neo & Công cụ: tạo mới bằng write_file cho `scripts/archify_portal.py` và `tests/test_archify_portal.py`
  - Trước → Sau: Explainer cũ nhúng lặp `~276 KB htmlGzip` cho mỗi diagram và chỉ zoom 1 tầng → Vỏ Portal duy nhất `< 300 KB` hỗ trợ click `[data-node-id]` đi sâu nhiều tầng, hiện giải thích tự nhiên + hợp đồng vào/ra + mini-flowchart + breadcrumb + neo chống chu trình + thẻ nguồn `path:line`
  - Tiêu chí chấp nhận (EARS): KHI gọi `build_portal_shell(..., mode="lazy")`, HỆ THỐNG PHẢI sinh HTML `< 300,000` bytes, chứa listener `closest('[data-node-id]')` ở container ngoài, không chèn `onclick=` vào SVG, hỗ trợ tải lười qua `fetch` có fallback `window.__TDQ_ARCHIFY_REGISTRY__`; KHI gọi `render_drilldown_standalone`, HỆ THỐNG PHẢI trả 1 HTML tự chứa chạy độc lập không cần file ngoài
  - Logic cốt lõi: Sanitize JSON an toàn chống `</script>` XSS; giao diện đọc sắc nét (light/dark, thanh breadcrumb, drawer 2 cột giải thích tự nhiên + mini-flow SVG, huy hiệu `reused_by`, huy hiệu `planned`/`working-tree`, thẻ neo `↺ Quay về ...` khi gặp `cycle_back_to` hoặc `visited_stack`)
  - Ca góc hiểm & Assert: Node chứa ký tự `</script>` được escape an toàn, nút trỏ vào chu trình không tạo vòng lặp DOM · `assert len(html.encode("utf-8")) < 300_000 and "onclick=" not in svg_region and "window.__TDQ_ARCHIFY_REGISTRY__" in bundle_js`

- [x] **T2.2** (e10m) Mở rộng `scripts/archify_model.py` chấp nhận trường `registry` tùy chọn trong `master.model.json` mà giữ 100% tương thích ngược với schema v1 (`39` tham chiếu LSP) — Test: `python3 -m pytest tests/test_archify_model.py -q`
  - Req: `§1, §2#3, §2b, §6 Q6` · Ngoài phạm vi: `GIỮ NGUYÊN` toàn bộ quy tắc thẩm định `master.model.json` v1 khi không khai báo trường `registry`
  - Chạm: `scripts/archify_model.py`, `tests/test_archify_model.py`
  - Cần: `T1.1`
  - Giao tiếp: Consumes: `archify_registry.validate_logic_node` | Produces: `validate_model` hỗ trợ trường tùy chọn `registry` (`path`, `root_flows[]`, `max_depth`)
  - Neo & Công cụ: sửa trực tiếp `scripts/archify_model.py` tại `_validate_master` (`L728`) và `validate_model` (`L769`)
  - Trước → Sau: `_validate_master` từ chối mọi khóa ngoài `{overview, flows}` → Cho phép thêm khóa tùy chọn `registry` (kiểm đường dẫn tương đối an toàn, `max_depth` 1..8) đồng thời vẫn từ chối khóa lạ không hợp lệ
  - Tiêu chí chấp nhận (EARS): KHI truyền `master.model.json` v1 cũ không có `registry`, HỆ THỐNG PHẢI giữ nguyên 100% kết quả cũ; KHI truyền `registry.path` chứa `../` thoát repo, HỆ THỐNG PHẢI ném `ValueError`
  - Logic cốt lõi: Thêm `"registry"` vào tập khóa hợp lệ của `master` (tùy chọn); kiểm kiểu `dict`, kiểm `_is_safe_relative_path(registry["path"])`, kiểm `root_flows` và `max_depth` nguyên `1..8`
  - Ca góc hiểm & Assert: Khóa lạ `"unknown_key"` vẫn bị từ chối fail-closed · `assert validated["master"]["registry"]["path"] == "docs/tdq/models/registry"`

- [x] **T2.3** (e16m) Nâng cấp `scripts/tdq_archify.py` tích hợp `sync-master --incremental` / `--full`, `render --type drilldown`, và subcommand `serve` — Test: `python3 -m pytest tests/test_tdq_archify.py tests/test_archify_pipeline.py -q`
  - Req: `§1, §2#3, §2b, §3c, §4, §6 Q2, Q3` · Ngoài phạm vi: `GIỮ NGUYÊN` toàn bộ hành vi mặc định của `check`, `bridge`, `test-bridge`, `open`, `status`, `verify` và `render --type explainer/workflow/architecture`
  - Chạm: `scripts/tdq_archify.py`, `tests/test_archify_pipeline.py`, `tests/test_tdq_archify.py`
  - Cần: `T1.1`, `T1.2`, `T1.3`, `T2.1`, `T2.2`
  - Giao tiếp: Consumes: `archify_registry`, `archify_portal`, `archify_model`, `archify_artifacts`, `archify_delivery` | Produces: CLI `sync-master [--incremental|--full]`, `render --type drilldown`, `serve <dir> [--port N] [--open]`
  - Neo & Công cụ: sửa trực tiếp `scripts/tdq_archify.py` tại `sync_master` (`L900`), `handle_render` (`L1284`), `main` (`L1493`)
  - Trước → Sau: `sync_master` luôn render lại cả 6 view nối tiếp và nhúng full `htmlGzip`; chưa có `render --type drilldown` hay `serve` → Khi model có `registry` (hoặc `--incremental`), chỉ chạy `finalize` cho lát cắt bẩn (hoặc 0 lần khi clean), trích `<svg>` sạch sang `slices/*.svg` + `nodes/*.json` + `registry-bundle.js` + `index.html < 300 KB` và ghi `manifest.json` `schema_version=1` xác minh `current`
  - Tiêu chí chấp nhận (EARS): KHI chạy `sync-master --incremental` lần 2 không đổi AST code, số lần gọi `run_finalize` PHẢI bằng `0` và `check_master_status` trả `current`; KHI sửa thân 1 hàm gắn với lát cắt S, chỉ lát cắt S gọi `run_finalize`; KHI chạy `render --type drilldown` trên candidate JSON có `nodes`, HỆ THỐNG PHẢI sinh 1 HTML tự chứa, bind vào document và `verify` trả `current`
  - Logic cốt lõi: Trích `<svg ...>...</svg>` nguyên vẹn từ HTML đầu ra của `run_finalize` (không sửa thuộc tính `data-node-id`); cache `render_slice_sha256` trong `slices/.cache.json` / manifest để tái dùng lát cắt sạch khi đồng bộ nguyên tử qua `publish_bundle`
  - Ca góc hiểm & Assert: Nếu bất kỳ lát cắt bẩn nào fail `finalize` → bảo toàn bản phát hành tốt trước đó (atomic rollback) · `assert finalize_calls_second_run == 0 and verify_res["status"] == "current"`

**Xong P2 khi**: `test_archify_portal`, `test_archify_model`, `test_tdq_archify`, `test_archify_pipeline` đạt 100% PASS.

## P3 — Cụm Pilot 4 tầng, Hướng dẫn Skill, Đóng gói AGY & Kiểm thử Chrome

- [x] **T3.1** (e14m) Tạo kho Logic Node Registry Pilot 4 tầng (`>= 12` Logic Nodes với `path:line` thật, `>= 2` node dùng chung `reused_by >= 2`, có nhánh lỗi và neo chu trình) cho cụm `hooks-and-gates` + `search-and-archify`, nối vào `docs/tdq/models/master.model.json` và chạy `sync-master --incremental` xuất lại `docs/architecture/` — Test: `python3 -X utf8 scripts/tdq_archify.py status`
  - Req: `§1, §2#5, §2b, §6 Q2, Q5` · Ngoài phạm vi: `GIỮ NGUYÊN` 4 view cũ (`overview`, `pipeline-lifecycle`, `runtime-verification`, `optimization-report`) vẫn truy cập bình thường từ Portal
  - Chạm: `docs/tdq/models/registry/index.json` (tạo mới), `docs/tdq/models/master.model.json`, `docs/architecture/index.html`, `docs/architecture/manifest.json`
  - Cần: `T2.3`
  - Giao tiếp: Consumes: `tdq_archify.py sync-master --incremental`, mã nguồn thật `hooks/scripts/{command_gate,search_gate,edit_gate,stop_gate}.py` và `scripts/{tdq_archify,archify_registry,archify_portal,archify_artifacts}.py` | Produces: `docs/tdq/models/registry/nodes/*.json`, `docs/architecture/slices/*.svg`, `docs/architecture/index.html` (`< 300 KB`), `docs/architecture/manifest.json` (`status=current`)
  - Neo & Công cụ: tạo kho `docs/tdq/models/registry/`, cập nhật `docs/tdq/models/master.model.json` và chạy `tdq_archify.py sync-master --incremental`
  - Trước → Sau: `docs/architecture/index.html` nặng `2.62 MB`, 4/6 view tràn khung đọc, chỉ có 1 tầng → Vỏ `index.html < 300 KB`, 2 luồng `hooks-and-gates` và `search-and-archify` có thể bấm đi sâu đủ 4 tầng với giải thích tiếng Việt tự nhiên và dẫn chứng code thật
  - Tiêu chí chấp nhận (EARS): KHI chạy `sync-master --incremental` xong, HỆ THỐNG PHẢI sinh `docs/architecture/index.html < 300,000` bytes, `tdq_archify.py status` trả `"status": "current"`, và chạy lại `sync-master --incremental` lần 2 không đổi code có `0` lát cắt phải render lại
  - Logic cốt lõi: Xây cây 4 tầng (Tầng 1: Cổng kiểm soát & Tìm kiếm 3 tầng → Tầng 2: `command_gate` / `search_gate` / `edit_gate` / `stop_gate` & `tdq_archify` → Tầng 3: cơ chế `rtk_integration`, `ast_symbol_sha256`, `span_binding`, nhánh chặn `deny` → Tầng 4: chi tiết kiểm SHA-256 & hồi quy chu trình sửa lỗi `QC -> Implement -> Stop Gate`)
  - Ca góc hiểm & Assert: Mọi `path:line` trong node Pilot đều phải tồn tại thật trên đĩa và trong biên số dòng của file · `assert Path("docs/architecture/index.html").stat().st_size < 300_000 and status["status"] == "current"`

- [x] **T3.2** (e12m) Cập nhật hướng dẫn vận hành tại 3 file `skills/*/references/archify-*.md`, bổ sung module mới vào `tests/test_archify_distribution.py` / `scripts/build_portable.py` (nếu cần), chạy `build_portable.py --sinh-agy` đồng bộ sang `plugins/tdq-workflow-agy/` và kiểm `i18n_check.py` — Test: `python3 -m pytest tests/test_archify_workflow_contract.py tests/test_archify_distribution.py tests/test_build_portable.py -q`
  - Req: `§1, §2#6, §2b, §5, §6 Q4` · Ngoài phạm vi: `GIỮ NGUYÊN` toàn bộ 17 cụm từ hợp đồng bắt buộc trong `test_archify_workflow_contract.py` và nguyên tắc tiếng Anh cho tầng `skills/`
  - Chạm: `skills/tdq-build/references/archify-lifecycle.md`, `skills/tdq-spec/references/archify-ba.md`, `skills/tdq-intake/references/archify-quick.md`, `scripts/build_portable.py`, `tests/test_archify_distribution.py`, `plugins/tdq-workflow-agy/`
  - Cần: `T1.4`, `T2.3`
  - Giao tiếp: Consumes: lệnh CLI mới `sync-master --incremental`, `render --type drilldown`, `serve` và module `archify_registry.py`/`archify_portal.py` | Produces: 3 file skill reference cập nhật, test phân phối phủ 6 module Archify, bản `plugins/tdq-workflow-agy/` đồng bộ mới nhất
  - Neo & Công cụ: bổ sung đoạn ngắn gọn (tiếng Anh) vào 3 file `skills/` và `tests/test_archify_distribution.py`; chạy `py -3 -X utf8 scripts/build_portable.py --sinh-agy` và `py -3 -X utf8 scripts/i18n_check.py`
  - Trước → Sau: Tài liệu skill chưa hướng dẫn dùng Logic Node Registry, `--incremental`, `--type drilldown` hay `serve`; bản `plugins/tdq-workflow-agy/` chưa có 2 module mới → Tài liệu đầy đủ mà vẫn qua `token_budget` và `i18n_check`, gói AGY đồng bộ khớp 100%
  - Tiêu chí chấp nhận (EARS): KHI chạy xong `build_portable.py --sinh-agy`, HỆ THỐNG PHẢI có đủ `plugins/tdq-workflow-agy/scripts/{archify_registry,archify_portal}.py`, vượt qua `test_archify_workflow_contract`, `test_archify_distribution`, `test_build_portable` và `i18n_check.py` với exit `0`
  - Logic cốt lõi: Thêm hướng dẫn ngắn về `sync-master --incremental`, `render --type drilldown`, `serve`, và phân tách `planned` vs `working-tree` vào đúng chỗ mà không sửa/xóa các câu hợp đồng cũ
  - Ca góc hiểm & Assert: Chạy `tdq_finish.py` tái sinh `token-budget.json` sau khi sửa `skills/` để không vỡ `doc_lint R13` · `assert Path("plugins/tdq-workflow-agy/scripts/archify_registry.py").is_file() and i18n_rc == 0`

- [x] **T3.3** (e10m) Kiểm thử trình duyệt sống qua Chrome DevTools MCP trên `docs/architecture/index.html` (cả qua `tdq_archify.py serve` lẫn `file://` fallback) và mẫu `render --type drilldown` — Test: `python3 -c "import pathlib; t=pathlib.Path('docs/tdq/artifacts/2026-11-24-1308-implement-archify-drilldown-registry/browser-e2e-audit.md').read_text(encoding='utf-8'); assert 'depth=4' in t and 'console_errors=0' in t and 'file_fallback=PASS' in t"`
  - Dùng: `tdq-browser-test` / `chrome-devtools` (mcp)
  - Để: Mở trang Portal qua HTTP cục bộ (`serve`) và trực tiếp `file://`, bấm kiểm tra đào sâu đủ 4 tầng trên cụm Pilot, kiểm breadcrumb, cycle anchor, giải thích tự nhiên, mini-flowchart và 0 console error; nạp skill trước khi kiểm
  - Ra: `docs/tdq/artifacts/2026-11-24-1308-implement-archify-drilldown-registry/browser-e2e-audit.md`
  - Kiểm: `py -3 -c "import pathlib; t=pathlib.Path('docs/tdq/artifacts/2026-11-24-1308-implement-archify-drilldown-registry/browser-e2e-audit.md').read_text(encoding='utf-8'); assert 'depth=4' in t and 'console_errors=0' in t"`
  - Không dùng cho: Không chỉnh sửa mã nguồn trong task này; không duyệt các trang web ngoài phạm vi Portal/Spec Archify
  - Req: `§1, §2#5, §3b, §6 Q2, Q5` · Ngoài phạm vi: `GIỮ NGUYÊN` toàn bộ mã nguồn và `C:\Users\admin\Documents\archify`
  - Chạm: `docs/tdq/artifacts/2026-11-24-1308-implement-archify-drilldown-registry/browser-e2e-audit.md` (tạo mới)
  - Cần: `T3.1`
  - Giao tiếp: Consumes: `docs/architecture/index.html` + `tdq_archify.py serve` | Produces: biên bản kiểm duyệt trình duyệt `browser-e2e-audit.md` kèm snapshot thực tế
  - Neo & Công cụ: Pre-flight `chrome-devtools` (`list_pages`/`new_page`), `take_snapshot`, `click` đi sâu từ Tầng 1 → Tầng 4, bấm breadcrumb lùi về Tầng 1, kiểm tra `list_console_messages`, tắt tab thử nghiệm & tắt server tạm
  - Trước → Sau: Chưa xác minh thao tác click đa tầng thật trên trình duyệt → Xác nhận người dùng bấm mượt đủ 4 tầng, giải thích tiếng Việt tự nhiên rõ ràng, fallback `file://` chạy tốt và `0` console error
  - Tiêu chí chấp nhận (EARS): KHI bấm liên tiếp 3 lần từ Tầng 1 xuống Tầng 4 trên cụm Pilot, HỆ THỐNG PHẢI cập nhật breadcrumb đủ 4 mốc, hiển thị văn bản giải thích + nguồn `path:line`, không có cảnh báo tràn khung đọc trên các lát cắt Pilot và `list_console_messages(types=["error","warn"])` trả rỗng (`0` lỗi)
  - Ca góc hiểm & Assert: Kiểm thử cả khi mở trực tiếp `file:///.../docs/architecture/index.html` (xác nhận `registry-bundle.js` cứu CORS) · `assert "depth=4" in audit and "console_errors=0" in audit`

**Xong P3 khi**: `docs/architecture/` đạt `status=current` với `index.html < 300 KB`, `plugins/tdq-workflow-agy/` đồng bộ xanh mọi contract test, và `browser-e2e-audit.md` ghi nhận `depth=4`, `console_errors=0`, `file_fallback=PASS`.

## P4 — Log & Test bắt buộc

- [x] **T4.1** (e5m) Xác minh dịch vụ log mặc định (`TDQ_LOG=1` có ISO timestamp, `TDQ_LOG=0` im lặng tuyệt đối) cho toàn bộ module mới và mở rộng qua `tests/test_archify_logging.py` — Test: `python3 -m pytest tests/test_archify_logging.py -q`
  - Req: `§4, §6 Q6` · Ngoài phạm vi: `GIỮ NGUYÊN` hành vi chức năng của các module trong `scripts/`
  - Chạm: `tests/test_archify_logging.py` (tạo mới)
  - Cần: `T1.4`, `T2.3`
  - Giao tiếp: Consumes: `scripts/archify_registry.py`, `scripts/archify_portal.py`, `scripts/archify_delivery.py`, `scripts/tdq_archify.py`, `scripts/tdq_setup.py` | Produces: bộ test xác minh `TDQ_LOG=1` vs `TDQ_LOG=0`
  - Neo & Công cụ: tạo mới `tests/test_archify_logging.py` chạy subprocess hoặc capture stderr có kiểm soát với biến môi trường `TDQ_LOG=1` và `TDQ_LOG=0`
  - Trước → Sau: Chưa có bài kiểm chuyên biệt khóa chuẩn log cho các module mới → Khóa chặt quy tắc log mặc định bật và tắt sạch bằng `TDQ_LOG=0`
  - Tiêu chí chấp nhận (EARS): KHI gọi hàm chính của `archify_registry` và `archify_portal` với `TDQ_LOG=1`, `stderr` PHẢI chứa dòng ISO timestamp `[YYYY-MM-DDTHH:MM:SS]`; KHI gọi lại với `TDQ_LOG=0`, `stderr` PHẢI rỗng `""`
  - Logic cốt lõi: Chạy từng hàm lõi dưới `TDQ_LOG=1` kiểm regex timestamp và dưới `TDQ_LOG=0` kiểm chuỗi rỗng
  - Ca góc hiểm & Assert: Không rò rỉ dữ liệu nhạy cảm hay traceback thô ra log · `assert re.search(r"\[\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\]", err_on) and err_off == ""`

- [x] **T4.2** (e6m) Chạy hồi quy toàn bộ bộ test Archify + Setup (`>= 218` test cũ + toàn bộ test mới) kèm `tdq_meta_gate.py` và kiểm chứng `0` chỉnh sửa trên `C:\Users\admin\Documents\archify` — Test: `python3 -m pytest tests/test_archify_*.py tests/test_tdq_archify.py tests/test_tdq_setup.py tests/test_agy_host_setup.py -q`
  - Req: `§4, §5, §6 Q6` · Ngoài phạm vi: `GIỮ NGUYÊN` trọn bộ suite chính sẽ chạy lại lần cuối ở pha QC (`QC-F1`)
  - Chạm: `docs/tdq/artifacts/2026-11-24-1308-implement-archify-drilldown-registry/regression-summary.md` (tạo mới)
  - Cần: `T3.2`, `T3.3`, `T4.1`
  - Giao tiếp: Consumes: toàn bộ `tests/test_*archify*.py`, `tests/test_tdq_setup.py`, `tests/test_agy_host_setup.py`, `scripts/tdq_meta_gate.py` | Produces: biên bản tóm tắt `regression-summary.md` với số test chạy/pass/skip thật
  - Neo & Công cụ: Chạy lệnh unittest + `tdq_meta_gate.py` + `git -C C:\Users\admin\Documents\archify status --porcelain`; ghi tóm tắt ngắn ra `regression-summary.md`
  - Trước → Sau: Các test mới chạy rời từng phần → Xác nhận toàn bộ cụm Archify + Setup + Meta-Gate chạy xanh đồng loạt trước khi bước vào pha QC trọn bộ
  - Tiêu chí chấp nhận (EARS): KHI chạy gom toàn bộ `test_*archify*.py` + `test_tdq_setup.py` + `test_agy_host_setup.py` + `tdq_meta_gate.py`, tổng số test Archify PHẢI `>= 250` với `0` fail/error, `Auto Meta-Gate` trả `PASS` và `git -C C:\Users\admin\Documents\archify status --porcelain` trả rỗng
  - Ca góc hiểm & Assert: Không bỏ sót lỗi import `helper` (luôn thiết lập `PYTHONPATH=tests`) · `assert fail_count == 0 and archify_upstream_dirty == ""`

**Xong P4 khi**: `test_archify_logging.py`, toàn bộ `test_*archify*.py`, `test_tdq_setup.py`, `test_agy_host_setup.py` và `tdq_meta_gate.py` đạt `0` fail, `C:\Users\admin\Documents\archify` sạch 100%.

## Cụm song song

- **Đợt 1 (chạy song song 3 luồng, `Chạm:` tách rời 100%):**
  - `T1.1` (`scripts/archify_registry.py`, `tests/test_archify_registry.py`)
  - `T1.2` (`scripts/archify_artifacts.py`, `tests/test_archify_artifacts.py`)
  - `T1.3` (`scripts/archify_delivery.py`, `tests/test_archify_delivery.py`)
- **Đợt 2 (sau `T1.1`, chạy song song 3 luồng độc lập):**
  - `T1.4` (`scripts/tdq_setup.py`, `tests/test_tdq_setup.py`, `tests/test_agy_host_setup.py`)
  - `T2.1` (`scripts/archify_portal.py`, `tests/test_archify_portal.py`)
  - `T2.2` (`scripts/archify_model.py`, `tests/test_archify_model.py`)
- **Đợt 3 (điểm hội tụ CLI):** `T2.3` (`scripts/tdq_archify.py`, `tests/test_archify_pipeline.py`, `tests/test_tdq_archify.py`)
- **Đợt 4 (sau `T2.3` và `T1.4`, chạy song song 3 luồng độc lập):**
  - `T3.1` (Pilot 4 tầng `docs/tdq/models/registry/` & `docs/architecture/`)
  - `T3.2` (Skill guides + `build_portable.py --sinh-agy` + `plugins/tdq-workflow-agy/`)
  - `T4.1` (`tests/test_archify_logging.py`)
- **Đợt 5 (tuần tự trên Leader vì có nhãn `(mcp)`):** `T3.3` (Chrome DevTools audit) → `T4.2` (Tổng hợp hồi quy).

## Luật file nóng (một file, nhiều task chạm)

Không có file nóng trong toàn bộ 12 task: mọi đường dẫn khai trong dòng `Chạm:` của `T1.1`–`T4.2` đều tách rời 100%, không có 2 task nào ghi cùng một tệp. Riêng `tests/test_archify_logging.py` được tách riêng ở `T4.1` thay vì ghi chung vào `tests/test_archify_registry.py` để tránh tranh chấp ghi.

## Definition of Done

Trỏ về §6 của spec `2026-11-24-1308-implement-archify-drilldown-registry.md` (`muc_qc=full`):

- [x] Q1 Bộ Hash 2 lớp `tree-sitter` chống false-dirty, relink `span_binding` và chống chu trình — `python3 -m pytest tests/test_archify_registry.py -q`
- [x] Q2 Vỏ HTML Drill-Down Portal `< 300 KB`, không `onclick` trong SVG gốc, fallback `file://` và `render --type drilldown` tự chứa — `python3 -m pytest tests/test_archify_portal.py tests/test_archify_pipeline.py -q` và kiểm kích thước `docs/architecture/index.html < 300000` bytes
- [x] Q3 `sync-master --incremental` (0 `finalize` khi sạch), bỏ `target`/`.pytest_cache` khỏi `source_fingerprint` và lệnh `serve` `127.0.0.1` — `python3 -m pytest tests/test_archify_artifacts.py tests/test_archify_delivery.py tests/test_tdq_archify.py -q`
- [x] Q4 Dependency `tree-sitter` trong `tdq_setup.py`, đồng bộ `plugins/tdq-workflow-agy/`, hợp đồng skill & `i18n_check` — `python3 -m pytest tests/test_tdq_setup.py tests/test_agy_host_setup.py tests/test_archify_workflow_contract.py tests/test_archify_distribution.py tests/test_build_portable.py -q` và `python3 scripts/i18n_check.py`
- [x] Q5 Cụm Pilot 4 tầng (`>= 12` Logic Nodes thật) và kiểm chứng Chrome DevTools (`depth=4`, `console_errors=0`, `file_fallback=PASS`) — `python3 -X utf8 scripts/tdq_archify.py status` và kiểm tra biên bản `docs/tdq/artifacts/2026-11-24-1308-implement-archify-drilldown-registry/browser-e2e-audit.md`
- [x] Q6 Toàn bộ `>= 218` test cũ + test mới + trọn bộ suite dự án + `Auto Meta-Gate` + `TDQ_LOG=1/0` + `0` thay đổi tại `C:\Users\admin\Documents\archify` — `python3 scripts/tdq_meta_gate.py`, `python3 -m pytest tests/test_archify_logging.py -q`, `python3 scripts/tdq_test.py tron-bo --workers auto --fresh --reuse off` và `git -C C:\Users\admin\Documents\archify status --porcelain`

## QC vòng 1 — fix

- [x] **QC1.1** Cách ly `TDQ_LOG` trong `_isolate_agy_env` tại `tests/test_agy_host_setup.py` để `--khong-log` không rò `os.environ["TDQ_LOG"]="0"` sang `tests/test_build_portable.py` khi chạy nối tiếp — Test: `py -3 -X utf8 -m pytest tests/test_agy_host_setup.py tests/test_build_portable.py -q`
<!-- tdq-archify-binding:start -->
<!-- manifest: C:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/artifacts/2026-11-24-1308-implement-archify-drilldown-registry/drilldown-sample.manifest.json -->
<!-- manifest_digest: bd0b6d281b14bdadefeea1251b3268f8f6e2d5a703dd57e64473066bdf57d5db -->
<!-- tdq-archify-binding:end -->