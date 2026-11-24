# BÁO CÁO — Triển khai trọn bộ cải thiện Archify (Drill-down nhiều tầng, Logic Node Registry và Tree-sitter Setup)

Ngày: 2026-11-24 · Mã yêu cầu: `2026-11-24-1308-implement-archify-drilldown-registry` (12/12 task kế hoạch + 1 task QC1.1 tick đủ)
Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

> **Tóm tắt dễ hiểu:** Trước khi làm, bản đồ tổng bị phình nặng 2.62 MB, bốn trên sáu luồng bị tràn khung đọc, chỉ xem được một tầng và thiếu trình phân tích tree-sitter trong bộ cài đặt. Nay hệ thống giữ nguyên engine gốc và dùng Logic Node Registry băm AST hai lớp qua tree-sitter để chỉ vẽ lại đúng lát cắt đổi. Vỏ Portal mới gọn 206,297 bytes, hỗ trợ mở sâu bốn tầng cả ngoại tuyến, đạt 100% ở 431 bài test Archify với Setup và 0 lỗi Chrome.

**Trước request (trạng thái/flow):** `docs/architecture/index.html` phình tới 2.62 MB vì nhúng lặp sáu runtime hoàn chỉnh, 4/6 view nội dòng bị ẩn SVG vì quá khổ khung nhìn và chỉ hỗ trợ modal 1 tầng. Lệnh `sync-master` quét 5,804 file (gồm cả `target/` và `.pytest_cache/`), chưa có kho node tái sử dụng chéo luồng và `tdq_setup.py` chưa kiểm hay cài đặt `tree-sitter`.

**Sau request (trạng thái/flow):** Triển khai trọn vẹn 4 đợt cải thiện trên nền No-Fork Hybrid (`0%` fork `C:\Users\admin\Documents\archify`):
- **Kho Logic Node & Băm AST 2 lớp:** Tạo mới `scripts/archify_registry.py` hỗ trợ `tree-sitter` 0.25+ cho Python, JS/TS và Rust cùng fallback AST Python và hash file; đổi comment hoặc dời dòng chỉ tự nối lại `span_binding` mà không gây bẩn nhầm, chặn tham chiếu sai, chặn node `planned` trên Master và phát hiện chu trình bằng DFS.
- **Vỏ Portal `< 300 KB`, Offline & Lệnh mới:** Tạo mới `scripts/archify_portal.py` sinh vỏ lười `index.html` (206,297 bytes), tệp fallback `registry-bundle.js` chạy thẳng qua `file://`, lệnh `render --type drilldown` (tối đa 4 tầng tự chứa) và `serve` mở máy chủ HTTP `127.0.0.1` an toàn.
- **Tối ưu Đồng bộ & Setup Tree-sitter:** Loại trừ `target/`, `.pytest_cache/` ở `scripts/archify_artifacts.py`; cô lập file tạm sidecar trong `TemporaryDirectory` khi render slice để tránh vượt giới hạn `MAX_PATH` 260 ký tự trên Windows; bổ sung `kiem_tra_tree_sitter` và `ensure_tree_sitter_installed` vào `scripts/tdq_setup.py` tôn trọng `TDQ_KHONG_CHAM_MAY=1`.
- **Pilot 4 tầng & Đồng bộ AGY:** Xây dựng 20 Pilot Logic Nodes thật qua 4 tầng (`hooks-and-gates` và `search-and-archify`, 3 node dùng chéo, 2 neo chu trình), cập nhật 3 file skill reference, đồng bộ gói `plugins/tdq-workflow-agy/` và khóa test log `TDQ_LOG=1/0` cho 5 module.

**Đã test gì:**
- Kiểm thử đơn vị và tích hợp theo từng wave rồi chạy gộp toàn bộ 16 file test Archify + Setup, kiểm thử log `TDQ_LOG=1/0`, kiểm tra phân phối gói plugin AGY và hợp đồng skill.
- Sau sửa đổi cuối (`QC1.1` tại `0d26c4f9`), chạy lại đầy đủ `Q1`–`Q6`: cụm Q1–Q3, cụm Q4 (gồm `test_agy_host_setup`, `test_build_portable`, `test_tdq_setup`, `test_agy_plugin_validate`, `test_sinh_agy`), `test_archify_logging.py`, `smoke-e2e --changed --workers 4`, `tdq_test.py tron-bo --workers auto --fresh --reuse off`, `tdq_meta_gate.py`, kiểm AST SOLID/import và kiểm tra sạch `C:\Users\admin\Documents\archify`.
- Kiểm thử trình duyệt sống trên Chrome DevTools MCP (`tdq-workflow-agy_chrome-devtools`) với cả `http://127.0.0.1:8765/` (`serve`), `file://` (`registry-bundle.js`) và `drilldown-sample.html` (`render --type drilldown`).

**Kết quả test:**
- Cụm Q1–Q3 (sau `0d26c4f9`): `202 passed, 4 skipped, 12 subtests passed` (`19.39s`; 4 skip đều do Windows non-elevated symlink).
- Cụm Q4 (sau `QC1.1`): `151 passed, 203 subtests passed` (`31.25s`, exit 0); cụm 16 file Archify + Setup ở T4.2 đạt `431 passed, 4 skipped, 113 subtests passed` (riêng 14 file Archify đạt `362 passed`, vượt mốc `>= 250`).
- Nhật ký log `test_archify_logging.py`: `33 passed in 2.94s` (`TDQ_LOG=1` in ISO timestamp, `TDQ_LOG=0` im lặng hoàn toàn).
- `smoke-e2e --changed --workers 4`: `417 passed, 227 subtests passed, 0 failed` (`118.14s`).
- `tdq_archify.py status`: `"status": "current"`, `docs/architecture/index.html` = `206,297` bytes (`< 300,000`), `15` slice SVG, `0` `onclick=`, `pilot_nodes=20`, `reused_ge2=3`, `cycles=2`.
- Chrome DevTools MCP (`docs/tdq/artifacts/2026-11-24-1308-implement-archify-drilldown-registry/browser-e2e-audit.md`): `depth=4`, `console_errors=0`, `file_fallback=PASS`, HTTP `200` lazy fetch `/slices/slice-stop-disk-diff-check.svg`, bấm neo chu trình `↺` không lặp vô hạn.
- `tron-bo` toàn repo (`242` module, `4,961` test): `4,920 passed, 37 skipped, 3,034 subtests passed, 4 failed in 345.56s`; trong 4 ca lỗi có 3 ca lệch version nền `dev` và 1 ca contention ở `test_tdq_simulate_verify.py` (đạt `9/9 PASS` khi chạy riêng).
- `C:\Users\admin\Documents\archify`: `0` sửa đổi/staging trên file tracked (`git status --porcelain --untracked-files=no` rỗng; `7` file untracked cũ ngày `2026-10-24` giữ nguyên).
- QC tổng hợp: Đạt `PASS` đầy đủ 6/6 DoD (`Q1`–`Q6`) và `QC-F1`–`F4` (`docs/tdq/qc/2026-11-24-1308-implement-archify-drilldown-registry.md`).

**Đầu ra:** `scripts/archify_registry.py`, `scripts/archify_portal.py`, `scripts/archify_artifacts.py`, `scripts/archify_delivery.py`, `scripts/archify_model.py`, `scripts/tdq_archify.py`, `scripts/tdq_setup.py`, `docs/tdq/models/registry/`, `docs/architecture/`, `plugins/tdq-workflow-agy/`, `tests/test_archify_*.py`, `docs/tdq/qc/2026-11-24-1308-implement-archify-drilldown-registry.md` · **Archify HTML:** [2026-11-24-1308-implement-archify-drilldown-registry.html](file:///C:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/reports/2026-11-24-1308-implement-archify-drilldown-registry.html) (Tailscale Serve: `https://unity-pc-rtx3060.tail99896.ts.net/vlog/tdq-workflow-agy/reports/2026-11-24-1308-implement-archify-drilldown-registry.html`)

**Giới hạn:**
- `build_portable.py --sinh-agy` gặp `WinError 32` khi thay thư mục user-level `C:\Users\admin\.gemini\config\plugins\tdq-workflow` vì tiến trình IDE đang chạy giữ khóa file trong thư mục đó; trong khi `tools/build_agy_plugin.py` đã build và kiểm chứng sạch gói `plugins/tdq-workflow-agy/` (`8 passed` ở `test_agy_plugin_validate`). Người dùng có thể chạy lại `py -3 -X utf8 scripts/build_portable.py --sinh-agy` khi tắt tiến trình giữ khóa nếu cần cập nhật bản user-level ngoài repo.
- `tdq_meta_gate.py` trả `3/4` (`doc_lint=0 lỗi`, `token_budget=0 lỗi`, `git_co_author=0 lỗi`) vì `i18n_check` quét toàn tệp vẫn đếm `740` dòng tiếng Việt có sẵn trên `dev` trong `tdq_setup.py` và chuỗi hợp đồng bắt buộc ở `archify_model.py`/`skills/`; nhánh này thêm `0` dòng tiếng Việt mới.
- Toàn suite `tron-bo` còn 3 ca lỗi lệch phiên bản có sẵn từ trước trên nhánh `dev` (`.claude-plugin/plugin.json` `0.106.0` vs `.codex-plugin/plugin.json` và `CHANGELOG.md` `0.105.0`, `git diff dev` rỗng) cùng 4 test symlink Windows non-elevated skip.

**Lệch spec chờ duyệt:** không có

**Git:** Chưa tạo commit chốt cuối; đã có 17 commit trung gian hợp nhất task và sửa lỗi chặn trên nhánh `feature/implement-archify-drilldown-registry`:
- `561b8a14` chore(tdq): sync tracked state and graphify before wave merges
- `38959e93` feat(archify_delivery): add safe loopback serve_directory helper (T1.3)
- `ae738d71` archify(artifacts): exclude target/.pytest_cache and validate fragment files (T1.2)
- `913ad731` feat(archify): add Logic Node Registry and 2-layer tree-sitter AST hashing (T1.1)
- `eecd045f` chore(tdq): sync status and graphify before Wave 2 merges
- `380b6b55` feat(archify): support optional master.registry schema in archify_model (T2.2)
- `105d7575` feat(archify): add lazy drilldown portal shell and standalone renderer (T2.1)
- `ca2d859a` chore(tdq): sync archify status before T2.1 merge
- `5f8a91e6` feat(setup): add tree-sitter core dependencies to tdq_setup (T1.4)
- `ce399efe` chore(tdq): sync archify status before T2.3 merge
- `4f61ccb3` feat(archify): integrate incremental sync-master, drilldown render, and serve CLI (T2.3)
- `cce92bbc` chore(t3.2): update archify skill docs, distribution tests, and AGY plugin bundle (T3.2)
- `ad4bf243` test(archify): add TDQ_LOG logging parity suite across all 5 modules (T4.1)
- `e2e23b98` fix(archify): isolate temporary slice render sidecars and clean atomic swap failures
- `6b7b865f` feat(archify): add 4-level Pilot Logic Node Registry and regenerate docs/architecture (T3.1)
- `327b401b` fix(portal): add data-URI favicon for zero HTTP console errors and sync root portal
- `0d26c4f9` test(qc1.1): isolate TDQ_LOG in _isolate_agy_env across pytest worker tests

## Thời gian

```
Request `2026-11-24-1308-implement-archify-drilldown-registry` · lane full · opened at 2026-11-24T13:19:36+07:00

| Phase | Wall clock | Times entered |
|---|---|---|
| idle | 1 min | 1 |
| analyze | 9 min | 1 |
| spec | 31 min | 1 |
| plan | 10 min | 1 |
| mode | 8 min | 1 |
| implement | 1h 19min | 1 |
| qc | 21 min | 1 |
| report | 1s | 1 |
| Total | 2h 39min |  |

Model compute time is unavailable (`model_giay=null`). API includes network/provider latency; tool time is host wait. Observed metrics may overlap; unattributed time is not assumed user/model time.
Transcript attribution: project_window. Complete covers selected supported observations only.
Host metrics unavailable (5 hidden: api_request_seconds, tool_call_seconds, background_job_seconds, observed_union_seconds, unattributed_seconds): no_usable_source, no_usable_observations, wall_minus_observed_union;no_usable_observations

## Agent Role Telemetry

| Role | Runs | First pass | Rate | Retries | Avg elapsed | Models |
|---|---|---|---|---|---|---|
| self | 7 | 7 | 100% | 0 | — | — |
| tdq-qc-tester | 6 | 6 | 100% | 0 | — | — |
| tdq-implementer | 2 | 2 | 100% | 0 | — | — |
```

Ghi chú phân rã đội: 10/12 task (`T1.1`–`T1.4`, `T2.1`–`T2.3`, `T3.1`, `T4.1`, `T4.2`) được thực thi qua sub-agent `tdq-implementer` trong worktree riêng; Leader giữ `T3.2` (cập nhật skill và đồng bộ bundle AGY), `T3.3` (kiểm thử trình duyệt Chrome DevTools MCP), các bản sửa unblocking (`_render_single_slice`, favicon, `QC1.1`), QC `full` và report.

## Thân PR (soạn sẵn)

**Tóm tắt:** Triển khai kiến trúc No-Fork Hybrid cho Archify trên TDQ Workflow gồm kho Logic Node Registry băm AST 2 lớp bằng `tree-sitter`, vỏ HTML Portal lười dưới 300 KB (kèm fallback `file://` và `render --type drilldown`), lệnh `sync-master --incremental`, `serve` cục bộ, cụm Pilot 4 tầng 20 node và tích hợp kiểm/cài `tree-sitter` trong `tdq_setup.py`.
**Trước/Sau:** [truoc-sau.html](file:///C:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/spec/2026-11-24-1308-implement-archify-drilldown-registry-preview.html) và [bao-cao.html](file:///C:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/reports/2026-11-24-1308-implement-archify-drilldown-registry.html)
**Đã kiểm:**
- `py -3 -X utf8 -m pytest tests/test_archify_registry.py tests/test_archify_portal.py tests/test_archify_pipeline.py tests/test_archify_artifacts.py tests/test_archify_delivery.py tests/test_tdq_archify.py -q` → `202 passed, 4 skipped, 12 subtests passed`
- `py -3 -X utf8 -m pytest tests/test_tdq_setup.py tests/test_agy_host_setup.py tests/test_archify_workflow_contract.py tests/test_archify_distribution.py tests/test_build_portable.py tests/test_agy_plugin_validate.py tests/test_sinh_agy.py -q` → `151 passed, 203 subtests passed`
- `py -3 -X utf8 -m pytest tests/test_archify_logging.py -q` → `33 passed in 2.94s`
- `py -3 -X utf8 scripts/tdq_test.py smoke-e2e --changed --workers 4` → `417 passed, 227 subtests passed in 118.14s`
- `py -3 -X utf8 scripts/tdq_archify.py status` → `status=current` (`index.html=206,297` bytes)
- Chrome DevTools MCP E2E → `depth=4`, `console_errors=0`, `file_fallback=PASS`, HTTP `200`
- `py -3 -X utf8 scripts/tdq_test.py tron-bo --workers auto --fresh --reuse off` → `4,920 passed, 37 skipped, 4 failed` (3 lệch version nền `dev` + 1 contention đạt `9/9` solo)
- `git -C C:\Users\admin\Documents\archify status --porcelain --untracked-files=no` → sạch `0` sửa đổi tracked
**Rủi ro hồi quy:** Thay đổi lớn nhất nằm ở luồng xuất bản `docs/architecture/` khi bật `master.registry` và việc cô lập `TDQ_LOG` trong `_isolate_agy_env`. Đã khóa bằng 362 test Archify (`>= 250` mục tiêu), 69 test Setup và 33 test log `TDQ_LOG=1/0`, vẫn giữ tương thích ngược hoàn toàn cho model không có `master.registry`.
<!-- tdq-archify-binding:start -->
<!-- manifest: 2026-11-24-1308-implement-archify-drilldown-registry.manifest.json -->
<!-- manifest_digest: 8bb2cb7b1193dc1b219a5b879db6e97300cce9a56c33efeebf1aad9ec7553cd6 -->
<!-- tdq-archify-binding:end -->