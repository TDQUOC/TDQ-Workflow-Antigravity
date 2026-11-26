# Brief — Triển khai Pha P2: Cầu nối CLI 1 chiều Paperclip Bridge
Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

## Nguyên văn

> okay mở request triển khai nốt pha p2 đi

- **Mục tiêu:** Triển khai trọn vẹn Pha P2 theo `docs/tdq/artifacts/2026-11-25-1633-paperclip-3phase-dev-plan/dev-plan-p2.md` và `master-roadmap.md`: xây dựng cầu nối CLI 1 chiều tắt mặc định (`"enabled": false`) giữa Paperclip và TDQ (`scripts/tdq_paperclip_bridge.py` + `scripts/defaults/paperclip-bridge.default.json`), dùng thuần Python stdlib (`urllib.request`, `subprocess` gọi `scripts/tdq_state.py init`, `TDQ_LOG=1/0`), kèm bộ test mock offline 100%, khóa cấu hình mặc định trong `scripts/tdq_config.py`, cập nhật `APPROVED_RUNTIME_MODULES` trong `tests/test_build_portable.py`, đồng bộ gói `plugins/tdq-workflow-agy/` và kiểm chứng toàn phần.
- **Phạm vi dự kiến:**
  - `scripts/defaults/paperclip-bridge.default.json` (tạo mới, pure ASCII)
  - `scripts/tdq_paperclip_bridge.py` (tạo mới, lệnh `status`, `pull`, `push-report`, nạp tĩnh `utf8_io`, `TDQ_LOG=1/0`, 0 import `hooks/`)
  - `tests/test_paperclip_bridge.py` (tạo mới, mock 100% offline không gọi mạng thật)
  - `scripts/tdq_config.py` (thêm khối `"paperclip_bridge": {"enabled": false}` vào `DEFAULT_CONFIG` và `tdq-config.json` nếu đồng bộ cấu hình mặc định)
  - `tests/test_build_portable.py` (cập nhật whitelist `APPROVED_RUNTIME_MODULES` và bản portable)
  - `plugins/tdq-workflow-agy/` (đồng bộ qua `tools/build_agy_plugin.py`)
- **Định tuyến P1 đã chạy ở Bước 1b:**
  - `tdq_domains.py route` → `code-build` (`work_kind=build`, `reason=no_keyword_match_fallback`)
  - `skill_router.py --tra ... --domain code-build` → top `#1 tdq-intake (11.24)`
  - `tdq_lsp.py check` → smoke 3/3 tầng (`grep`, `LSP`, `graphify`) ĐẠT; Bậc 8 `python:.` CHUA_KIEM / `javascript:.` & `rust` HET_HAN (xử lý khi `init` sau khi chốt pipeline).
- **Điểm cần làm rõ trong pha phân tích:**
  - Xác nhận chi tiết hợp đồng ánh xạ `pull` (truyền cờ `--domain` / `--kind` / brief tự động hay chỉ `tdq_state.py init` + ghi brief), định dạng endpoint HTTP của `status`/`pull`/`push-report`, cơ chế đồng bộ `tdq-config.json` gốc lẫn plugin, và xác nhận mức kiểm chứng (`ultra` theo `master-roadmap.md` hay `chuẩn`).

## Hiểu & kiến thức

### Năng lực dùng được

| Kỹ năng / Năng lực | Nguồn | Phán quyết | Lý do |
|---|---|---|---|
| `tdq-intake`, `tdq-spec`, `tdq-plan`, `tdq-build`, `tdq-conventions` | `plugin:tdq-workflow-agy` | **DÙNG** | Chủ pipeline full từ `analyze` → `spec` → `plan` → `implement` → `qc` → `report` |
| `tdq-lean` | `plugin:tdq-workflow-agy` | **DÙNG** | Giữ Pha P2 tối giản, đúng scope 1 chiều stdlib, không over-engineer |
| `tdq-browser-research`, `tdq-browser-test`, `chrome-devtools`, `a11y-debugging`, `cookie-debugging`, `debug-optimize-lcp`, `memory-leak-debugging` | `plugin:tdq-workflow-agy` / `chrome-devtools-plugin` | **BỎ QUA** | Pha P2 là cầu nối CLI offline/mock, không có UI trình duyệt |
| `gemini-api-*`, `gdocs`, `gdrive`, `gsheets`, `gslides`, `generative_ui`, `mcp-app-development`, `automation`, `conversations`, `plugin`, `run-workflow` | Built-in / External plugins | **BỎ QUA** | Ngoài phạm vi cầu nối CLI thuần Python stdlib |

### Khảo sát mã nguồn 3 chiều (Triangulation)

| Vùng file chạm | Phát hiện qua lớp nào (Grep/LSP/Graphify) | Tác động & quan hệ |
|---|---|---|
| `scripts/tdq_config.py` (`DEFAULT_CONFIG`, `L51-127`, `load_config`, `_apply_env_override`) + `tdq-config.json` | Grep (`rg`) + Graphify (`affected` → `tdq_domains.py`) | Thêm khối `"paperclip_bridge": {"enabled": false}` vào `DEFAULT_CONFIG` và **BẮT BUỘC** đồng bộ root `tdq-config.json` vì `tests/test_agent_upgrade_mvp.py:675-678` kiểm khớp tuyệt đối `json.loads(tdq-config.json) == DEFAULT_CONFIG` và `root == plugins/tdq-workflow-agy/tdq-config.json` |
| `scripts/tdq_state.py` (`cli`, `L3594-3670`) | Read + Graphify (`god-nodes`: `cli()` 46 edges) | `init` bắt buộc slug có `HHMM` (`YYYY-MM-DD-HHMM-<kebab>`), nhận `--kind`, `--lang`, `--bo-qua-lsp`, `--json`; không có cờ `--domain` (nếu gán domain phải gọi tiếp `tdq_state.py set domain_id=<id>`). Giữ bất biến đơn chủ ghi `state.json` và `schema_version=6` |
| `tests/test_build_portable.py` (`L37-81`, `L369-371`, `L632-705`) + `scripts/build_portable.py` | Grep (`rg`) + Read | Cần cập nhật **CẢ HAI** tập whitelist: thêm `"tdq_paperclip_bridge"` vào `APPROVED_RUNTIME_MODULES` và thêm `"scripts/defaults/paperclip-bridge.default.json"` vào `APPROVED_RELEASE_DOCS` để giữ `len(paths - approved_paths) <= 161` và bản phát hành `main` (`kept=209` hiện tại) xanh |
| `scripts/tdq_domains.py` (`L1-90`) + `scripts/i18n_check.py` (`L35-44`) | Read + Graphify | `tdq_paperclip_bridge.py` theo chuẩn P1: nạp tĩnh `import utf8_io`, `TDQ_LOG=1` mặc định ISO timestamp trên stderr và `TDQ_LOG=0` xuất `0B` stderr; toàn bộ file mới (`paperclip-bridge.default.json`, `tdq_paperclip_bridge.py`, `test_paperclip_bridge.py`) thuần ASCII (`0` dòng tiếng Việt qua `i18n_check.py`), `0` import `hooks/` |
| `tools/build_agy_plugin.py` (`L304-318`) + `tools/patches/common_utils.py` (`L12-20`) | Grep (`rg`) + Read | `EXCLUDED_SCRIPTS` không loại `tdq_paperclip_bridge.py`; `build_agy_plugin.py` tự chép `scripts/defaults/paperclip-bridge.default.json`, `scripts/tdq_paperclip_bridge.py` và `tdq-config.json` sang `plugins/tdq-workflow-agy/`. Không chạm `hooks/` hay Rust `tdq-dispatch` (giữ nguyên `23` mã cổng AGY) |

- **Trạng thái LSP Python:** `start_lsp(language_id="python")` báo `no server configured for language "python"` (đã ghi nhận qua `--bo-qua-lsp`); đã bù bằng Graphify (`query`, `affected`, `god-nodes`), `rg` và đọc trực tiếp mã nguồn.

### Ràng buộc & Quyết định nền

- **Bỏ qua vòng Scope (Tier 1):** Phạm vi Pha P2 đã được khóa rõ trong `docs/tdq/artifacts/2026-11-25-1633-paperclip-3phase-dev-plan/dev-plan-p2.md` và `master-roadmap.md` (add-on CLI 1 chiều tắt mặc định, 3 wave, 0 DB/daemon/hook/Rust).
- **Bỏ qua Research ngoài (Bước 3):** Bài toán hoàn toàn nội bộ trên Python stdlib (`urllib.request`, `subprocess`, `argparse`, `json`); tài liệu khảo sát Paperclip đã có sẵn trên đĩa (`2026-11-24-2359-research-paperclip-features-apps`, `2026-11-25-1439-paperclip-tdq-integration-sim`).
- **6 mục CẤM sao chép từ Paperclip:** `0` DB/Postgres nhúng, `0` Same-Origin Web UI/daemon, `0` bỏ xác thực `local_trusted`, `0` binary `darwin-arm64`, `0` heartbeat timer poll rỗng, `0` nới lỏng TCAS/Verify-by-Effect.
- **An toàn HTTP/CLI:** Chỉ chấp nhận scheme `http://`/`https://`, mã hóa path segment `issue_id` tránh path traversal, timeout mặc định `5s`, che token trong log/thông báo lỗi, mã thoát `3` khi `enabled=false` (không mở socket).

### Lộ trình

| Bước/phase | CÓ-BỎ | Vì sao |
|---|---|---|
| `analyze` | CÓ | Đối soát đủ anchor `tdq_config`, `tdq_state`, `test_build_portable`, `build_agy_plugin` và chốt chi tiết ánh xạ/endpoint/QC qua phỏng vấn |
| `research ngoài` | BỎ | Thuần nội bộ Python stdlib và đã có sẵn kết quả khảo sát Paperclip tại `2026-11-24-2359` & `2026-11-25-1439` |
| `spec` | CÓ | Chốt hợp đồng JSON/CLI, bảng DoD có `Đo trước`/`Dự phòng` và thiết kế bảo mật HTTP trước khi lập kế hoạch |
| `plan` | CÓ | Phân rã `3` wave không chồng file sở hữu (`P2-W1`..`P2-W3`) bám `dev-plan-p2.md` |
| `implement` | CÓ | Thi công theo mode người dùng chọn (`subagent` hoặc `main`) trên `feat/p2-paperclip-cli-bridge` |
| `qc` | CÓ | Đã chốt `3a` → chạy mức `ultra` (đủ `full` + smoke/runtime/đóng gói + `tdq-qc-tester` độc lập) |
| `report` | CÓ | Xuất báo cáo Markdown + Archify HTML, xin duyệt chốt commit và hợp nhất về `dev` |

## Hỏi đáp

### Vòng 1 (2026-11-26T23:33:11+07:00 — trả lời lúc 2026-11-26T23:35:05+07:00)

1. Hành vi lệnh `pull --issue <id>` khi khởi tạo phiên TDQ?
   - A (đề xuất): Tự sinh slug chuẩn có giờ-phút (`YYYY-MM-DD-HHMM-<kebab>`), gọi `tdq_state.py init`, định tuyến domain qua `tdq_domains.py` + `tdq_state.py set domain_id=...` và tạo sẵn file brief phần Nguyên văn — nối liền mạch với P1, mở xong vào thẳng pha phân tích.
   - B: Chỉ sinh slug có giờ-phút, gọi `tdq_state.py init` và in JSON ánh xạ ra stdout, không tự ghi brief hay gán `domain_id` — tối giản tối đa theo khung cơ bản.
   - Đã chọn (`1a2a3a4a` verbatim): `1a` — Tự sinh slug chuẩn `YYYY-MM-DD-HHMM-<kebab>`, gọi `tdq_state.py init`, định tuyến `tdq_domains.route_domain()` + `tdq_state.py set domain_id=... brief_file=...` và tạo sẵn `docs/tdq/brief/<slug>.md` phần `## Nguyên văn`.

2. Định dạng endpoint REST và xác thực token cho `status`, `pull`, `push-report`?
   - A (đề xuất): Mặc định 3 đường dẫn REST chuẩn (`GET /health`, `GET /issues/<id>`, `POST /issues/<id>/comments`) có thể ghi đè qua trường `endpoints` trong cấu hình, chỉ cho phép `http`/`https`, gửi Bearer token từ biến môi trường và che token trong mọi log lỗi; `status` cho phép ping không cần token, còn `pull` và `push-report` bắt buộc token — vừa an toàn vừa dễ tùy chỉnh khi API Paperclip thay đổi.
   - B: Cố định cứng 3 đường dẫn REST trên không thêm khóa `endpoints` và bắt buộc có token cho cả 3 lệnh `status`, `pull`, `push-report` — gọn cấu hình hơn, kiểm tra chặt xác thực ngay từ bước ping.
   - Đã chọn (`1a2a3a4a` verbatim): `2a` — Mặc định 3 endpoint REST (`GET /health`, `GET /issues/{issue_id}`, `POST /issues/{issue_id}/comments`) cho phép ghi đè qua `endpoints`, chỉ chấp nhận `http`/`https`, Bearer token từ `token_env_var`, che token khi log lỗi; `status` cho phép không token, `pull`/`push-report` bắt buộc token.

3. Request này bạn muốn QC tới mức nào?
   - A (đề xuất): `ultra` — đồng nhất với `P0` và `P1` theo lộ trình chung: đủ `full` cộng thêm kiểm chứng toàn bộ đóng gói, chạy toàn kho và một subagent QC độc lập soi lại.
   - B: `full` — DoD + trọn unit test + hồi quy vùng chạm + ràng buộc kiến trúc + clean code. Không chạy subagent QC độc lập.
   - C: `lite` — DoD + unit test của riêng vùng chạm. Nhanh nhất, đổi lại không chạy trọn suite.
   - Đã chọn (`1a2a3a4a` verbatim): `3a` (`muc_qc=ultra`).

4. Bạn muốn bổ sung thêm gì không?
   - A (đề xuất): Không, đủ rồi — làm tiếp đi.
   - B: Có — tôi nói thêm.
   - Đã chọn (`1a2a3a4a` verbatim): `4a` — Không, đủ rồi — làm tiếp đi.
