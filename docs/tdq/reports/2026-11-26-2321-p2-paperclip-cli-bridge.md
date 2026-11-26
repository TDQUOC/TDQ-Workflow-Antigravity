# BÁO CÁO — Triển khai Pha P2: Cầu nối CLI 1 chiều Paperclip Bridge

Ngày: 2026-11-27 · Mã yêu cầu: `2026-11-26-2321-p2-paperclip-cli-bridge` (`6` task tick đủ, `7/7` DoD)
Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

> **Tóm tắt dễ hiểu:** Trước đây, TDQ đã xong phần lõi P0 và định tuyến P1, nhưng người dùng Docker hoặc WSL2 chưa có cầu nối kéo ticket từ Paperclip. Nay hệ thống thêm cầu nối dòng lệnh một chiều tắt mặc định bằng thư viện chuẩn Python để kéo ticket và gửi báo cáo. Lệnh kéo ticket nối thẳng định tuyến lĩnh vực, ghi nhận phiên làm việc đúng chuẩn và có thể tháo sạch mà không đụng hai pha trước. Toàn bộ kiểm thử giả lập ngoại tuyến, đóng gói đa host, thẩm định độc lập và toàn kho năm nghìn test đều đạt trọn vẹn.

**Trước request (trạng thái/flow):** Sau khi hoàn tất `P0` và hợp nhất `P1` lên `dev@24acb575`, dự án chưa có mẫu cấu hình `paperclip-bridge.default.json`, chưa có khối `paperclip_bridge` trong `tdq_config.py` / `tdq-config.json`, chưa có CLI `scripts/tdq_paperclip_bridge.py` và chưa mở whitelist đóng gói cho bridge. Người dùng chạy Docker hoặc WSL2 muốn đưa ticket Paperclip vào TDQ phải tự gõ tay slug có giờ-phút `HHMM`, gán `domain_id` P1 và tạo brief, trong khi không được phép chạy daemon nền hay db ngoài trên Windows.

**Sau request (trạng thái/flow):** Pha `P2` hoàn thành trọn vẹn add-on cầu nối CLI `1` chiều cô lập hoàn toàn theo đúng lộ trình [dev-plan-p2.md](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/artifacts/2026-11-25-1633-paperclip-3phase-dev-plan/dev-plan-p2.md) và lựa chọn `1a2a3a4a`:
- **Cấu hình tắt mặc định an toàn (`paperclip_bridge.enabled: false`):** Thêm `scripts/defaults/paperclip-bridge.default.json` thuần ASCII, khóa `"paperclip_bridge": {"enabled": false}` vào `DEFAULT_CONFIG` (`scripts/tdq_config.py`) và đồng bộ `tdq-config.json` gốc lẫn plugin (`env > docs/tdq/ > defaults`, hỗ trợ `PAPERCLIP_BRIDGE_ENABLED` và `TDQ_PAPERCLIP_BRIDGE_ENABLED`). Khi tắt hoặc khi `docs/tdq/paperclip-bridge.json` hỏng JSON, mọi lệnh cầu nối thoát mã `3` và mở đúng `0` socket.
- **Cầu nối CLI một chiều (`status`, `pull`, `push-report`):** Xây dựng `scripts/tdq_paperclip_bridge.py` (`25` hàm, tối đa `46` dòng/hàm, thuần stdlib `urllib.request`, `TDQ_LOG=1/0`, `0` import `hooks/`). Chỉ chấp nhận `http`/`https`, URL-quote `issue_id`, che token `***` trong mọi lỗi. `status` ping `/health` không buộc token; `pull` buộc Bearer token, gọi `tdq_domains.route_domain()`, tự sinh slug `YYYY-MM-DD-HHMM-<kebab>`, gọi CLI `scripts/tdq_state.py init` + `set domain_id=... brief_file=...` (giữ đơn chủ ghi `state.json` `schema_version=6`) và tạo sẵn brief; `push-report` rút trích tóm tắt + `tdq_state.py get` để `POST` comment.
- **Đóng gói đa host và hoàn nguyên sạch:** Cập nhật `APPROVED_RUNTIME_MODULES` (`"tdq_paperclip_bridge"`) và `APPROVED_RELEASE_DOCS` (`"scripts/defaults/paperclip-bridge.default.json"`) trong `tests/test_build_portable.py`, chạy `tools/build_agy_plugin.py` đồng bộ sạch sang `plugins/tdq-workflow-agy/` (giữ nguyên `23` mã cổng AGY, `0` chạm `hooks/` hay Rust `tdq-dispatch`), và xác minh xóa 3 tệp P2 không ảnh hưởng `P0`/`P1`.

**Đã test gì:**
- Kiểm thử đơn vị và mock ngoại tuyến `100%` (`tests/test_paperclip_bridge.py`, `tests/test_agent_upgrade_mvp.py`, `tests/test_build_portable.py`, `tests/test_state.py`, `tests/test_tdq_domains.py`, `tests/test_rust_dispatch_parity.py`) theo nhịp `Red -> Green` cho từng wave `T1.1`–`T4.2`.
- Đo log service `TDQ_LOG=1` vs `TDQ_LOG=0` trên CLI bridge gốc, plugin AGY và `tdq_config.py`; kiểm tĩnh `ruff check`, `i18n_check.py`, `token_budget.py --kiem`, `doc_lint.py`, `tdq_meta_gate.py --files`, AST quét `82` tệp `scripts/*.py` và độ phức tạp hàm.
- Kiểm chứng mức `ultra`: `tools/run_full_verification.py`, `tdq_test.py smoke-e2e --changed --workers auto --fresh`, `2` lượt `tdq_test.py tron-bo --workers auto --fresh --reuse off` toàn kho `249` module, cùng kiểm toán độc lập bởi `tdq-qc-tester` (`3d439881`) chạy cả `5` probe adversarial `(a)`–`(e)` và giả lập xóa sạch rollback trong tempdir.

**Kết quả test:**
- Cụm test mục tiêu: `tests/test_paperclip_bridge.py` `12 passed, 3 subtests` (`0.58s`); bộ lọc config/paperclip `22 passed, 16 subtests` (`1.42s`); `tests/test_build_portable.py` `39 passed, 4 subtests` (`11.84s`); cụm `6` module vùng P2 do `tdq-qc-tester` chạy đạt **`218 passed, 74 subtests, 0 skipped, 0 failed`** (`89.49s`), chốt **`Verdict: PASS`** và **`DEFECTS: None`**.
- Toàn bộ cổng hệ thống: `tools/run_full_verification.py` đạt **`24/24` pytest** và **`0` findings** trên `agy validate` (cả bản cài lẫn staging); `tdq_meta_gate.py --files` đạt `PASS (2/2 checks, 0.06s)`; `token_budget.py --kiem` thoát `0`; `i18n_check.py` `0 Vietnamese line(s)`; `ruff check` trên 3 tệp P2 đạt `All checks passed!`; `82` tệp `scripts/*.py` có `0` import `hooks/`; `TDQ_LOG=0` đạt `0B` stderr và `TDQ_LOG=1` xuất ISO timestamp (`260B` bridge, `117B` config).
- Toàn kho `tron-bo` & `smoke-e2e`: `smoke-e2e --changed --workers auto --fresh` đạt `418 passed, 239 subtests` (`111.24s` exec / `125.87s` wrapper; lượt `-n 0` ban đầu chạm trần `120s` đã được ngắt). `tron-bo --workers auto --fresh --reuse off` lượt cuối đạt **`[TDQ:TEST] PASS`** với **`5012 passed, 37 skipped, 3090 subtests passed`** (`361.29s` exec / `383.33s` wrapper, `5049` ca thu thập trên `249` module, `details_complete=True`, `full-suite runs: 2 of budget 3`, `radius misses: 0`; lượt 1 trước đó cũng xanh `5012/37` nhưng wrapper báo `INCOMPLETE` vì cập nhật `workinglog` giữa lúc chạy). Chi tiết đầy đủ xem tại [qc.md](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/qc/2026-11-26-2321-p2-paperclip-cli-bridge.md).

**Đầu ra:**
- Tạo mới: [paperclip-bridge.default.json](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/scripts/defaults/paperclip-bridge.default.json), [tdq_paperclip_bridge.py](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/scripts/tdq_paperclip_bridge.py), [test_paperclip_bridge.py](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/tests/test_paperclip_bridge.py), [log-verify.json](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/artifacts/2026-11-26-2321-p2-paperclip-cli-bridge/log-verify.json), [qc.md](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/qc/2026-11-26-2321-p2-paperclip-cli-bridge.md), [bao-cao.archify.md](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/artifacts/2026-11-26-2321-p2-paperclip-cli-bridge/bao-cao.archify.md).
- Cập nhật & đồng bộ: [tdq_config.py](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/scripts/tdq_config.py), [tdq-config.json](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/tdq-config.json), [test_agent_upgrade_mvp.py](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/tests/test_agent_upgrade_mvp.py), [test_build_portable.py](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/tests/test_build_portable.py), và bundle `plugins/tdq-workflow-agy/` ([manifest.json](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/plugins/tdq-workflow-agy/manifest.json), [tdq-config.json](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/plugins/tdq-workflow-agy/tdq-config.json), [tdq_paperclip_bridge.py](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/plugins/tdq-workflow-agy/scripts/tdq_paperclip_bridge.py), [paperclip-bridge.default.json](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/plugins/tdq-workflow-agy/scripts/defaults/paperclip-bridge.default.json)).
- **Archify HTML:** `docs/tdq/reports/2026-11-26-2321-p2-paperclip-cli-bridge.html` (Tailscale: https://unity-pc-rtx3060.tail99896.ts.net/vlog/tdq-workflow-agy/reports/2026-11-26-2321-p2-paperclip-cli-bridge.html).

**Giới hạn:**
- Yêu cầu mở qua `--bo-qua-lsp`: `ly_do = "LSP python:. khong co server cau hinh (start_lsp bao no server configured for language python); da doi chieu Graphify va rg tren toan bo anchor P2"`, `module = ["javascript:. → HET_HAN (kết quả cũ hơn 24 giờ)", "python:. → CHUA_KIEM (chưa chạy kịch bản)", "rust:hooks/rust/tdq-dispatch → HET_HAN (kết quả cũ hơn 24 giờ)"]` (đã bù bằng Graphify, `rg`, đọc trực tiếp toàn bộ neo và kiểm thử đầy đủ).
- `tests/test_build_portable.py` vẫn giữ `7` cảnh báo `ruff` có sẵn từ `HEAD@24acb575` (`6` dòng P2 thêm mới sạch `0` lỗi); `tdq_meta_gate.py` chạy không lọc báo `11` dòng tiếng Việt có sẵn trong file gốc được đồng bộ lại ở `plugins/tdq-workflow-agy/hooks/scripts/edit_gate.py` và `plugins/tdq-workflow-agy/skills/tdq-intake/SKILL.md`.
- Lượt `smoke-e2e --changed` không truyền `--workers auto` (`-n 0`) vượt trần `120s` và bị ngắt; tham số `--slug` ở `push-report` tin cậy slug nội bộ trong `docs/tdq/reports/<slug>.md` theo spec §3c; kiểm tra thực tế với server Paperclip live ngoài localhost chưa chạy (ngoài phạm vi mock offline `100%`).
- `eval: chưa kích hoạt (opt-in)`

**Lệch spec chờ duyệt:** không có (`tdq_state.py lech list` → `0 item(s), 0 pending`).

**Git:** Đã commit `77126b11` trên `feat/p2-paperclip-cli-bridge`, hợp nhất `--no-ff` (`fb88116e`) vào `dev` và xóa nhánh `feat/p2-paperclip-cli-bridge` (chưa push).

---

## Thời gian

Request `2026-11-26-2321-p2-paperclip-cli-bridge` · lane full · opened at 2026-11-26T23:34:02+07:00

| Phase | Wall clock | Times entered |
|---|---|---|
| idle | 0s | 1 |
| analyze | 4 min | 1 |
| spec | 1h 04min | 1 |
| plan | 4 min | 1 |
| mode | 5 min | 1 |
| implement | 14 min | 1 |
| qc | 30 min | 1 |
| report | 0s | 1 |
| Total | 2h 01min |  |

<!-- doc-lint: allow R12 -->
Model compute time is unavailable (`model_giay=null`). API includes network/provider latency; tool time is host wait. Observed metrics may overlap; unattributed time is not assumed user/model time.
Transcript attribution: project_window. Complete covers selected supported observations only.
Host metrics unavailable (5 hidden: api_request_seconds, tool_call_seconds, background_job_seconds, observed_union_seconds, unattributed_seconds): no_usable_source, no_usable_observations, wall_minus_observed_union;no_usable_observations

## Agent Role Telemetry

| Role | Runs | First pass | Rate | Retries | Avg elapsed | Models |
|---|---|---|---|---|---|---|
| self | 7 | 7 | 100% | 0 | — | — |
| tdq-qc-tester | 6 | 6 | 100% | 0 | — | — |
| tdq-implementer | 2 | 2 | 100% | 0 | — | — |

---

## Thân PR (soạn sẵn)

**Tóm tắt:** Thêm add-on cầu nối CLI `1` chiều Paperclip Bridge tắt mặc định (`scripts/tdq_paperclip_bridge.py`, `scripts/defaults/paperclip-bridge.default.json`, khóa `paperclip_bridge` trong `tdq_config.py`/`tdq-config.json`), nối thẳng `tdq_domains.route_domain()` (`P1`) và `tdq_state.py init/set/get`, kèm bộ test mock stdlib offline `100%`, whitelist phát hành `main` và bundle `plugins/tdq-workflow-agy/` đồng bộ.

**Trước/Sau:** [truoc-sau-preview](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/spec/2026-11-26-2321-p2-paperclip-cli-bridge-preview.html) · [bao-cao-html](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/reports/2026-11-26-2321-p2-paperclip-cli-bridge.html)

**Đã kiểm:**
- `py -3 -X utf8 -m pytest -q tests/test_paperclip_bridge.py` (`12 passed, 3 subtests in 0.58s`)
- `py -3 -X utf8 -m pytest -q -n auto tests/test_paperclip_bridge.py tests/test_agent_upgrade_mvp.py tests/test_build_portable.py tests/test_rust_dispatch_parity.py tests/test_state.py tests/test_tdq_domains.py` (`218 passed, 74 subtests, 0 failed in 89.49s`; `tdq-qc-tester` chốt `Verdict: PASS`, `DEFECTS: None`)
- `py -3 -X utf8 tools/run_full_verification.py` (`pytest_passed=24/24`, `agy_validate_findings=0`, `status=OK`)
- `py -3 -X utf8 scripts/tdq_test.py smoke-e2e --changed --workers auto --fresh` (`418 passed, 239 subtests in 111.24s` exec / `125.87s` tổng)
- `py -3 -X utf8 scripts/tdq_test.py tron-bo --workers auto --fresh --reuse off` (`5012 passed, 37 skipped, 3090 subtests passed in 361.29s` / `[TDQ:TEST] PASS`)

**Rủi ro hồi quy:** Luồng Windows mặc định không thay đổi vì `paperclip_bridge.enabled` là `false` (thoát mã `3`, `0` socket mở); không chỉnh `hooks/` hay Rust `tdq-dispatch` (giữ `schema_version=6` và `23` mã cổng AGY); xóa 3 tệp P2 giữ nguyên hoàn toàn `P0`/`P1` (`test_state.py`, `tdq_domains.py`, `tdq_config.py` đều xanh).
<!-- tdq-archify-binding:start -->
<!-- manifest: 2026-11-26-2321-p2-paperclip-cli-bridge.manifest.json -->
<!-- manifest_digest: b2c205598a179961cc37db407d4e25f239fbfe561dab30196e99eb9d5ea73960 -->
<!-- tdq-archify-binding:end -->