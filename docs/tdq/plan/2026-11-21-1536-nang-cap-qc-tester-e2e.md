# PLAN — Nâng cấp QC và Tester TDQ theo `3` Wave (Dev-First, E2E-First, `v0.104.0`)

Ngày: 2026-11-21 · Spec: ../spec/2026-11-21-1536-nang-cap-qc-tester-e2e.md (bản 1.0, ĐÃ DUYỆT) · Lane: full
Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md
Mode thực thi: subagent — Winner: đội (gap 13.2 minutes: subagent 9.2p vs main 22.4p với hệ số 1.5x qua 11 task / 3 wave theo tdq_bench.py simulate) (ĐÃ CHỐT)
Trạng thái plan: ĐANG CHẠY

> **Tóm tắt dễ hiểu:** Chia việc thành `4` đợt tuần tự từ nền tới phát hành: Wave 1 (`T1.1`–`T1.3`) vá `tdq_test.py` (`--workers auto`, `.html`, `.ruff_cache`, `smoke-e2e`), ẩn cột `[unavailable]` ở `tdq_timing.py`, và dựng `tdq_meta_gate.py`; Wave 2 (`T2.1`–`T2.3`) gắn marker `@pytest.mark.smoke`/`e2e` cho `15+` module test lõi kèm khóa lỗi `v0.103.0`; Wave 3 (`T3.1`–`T3.2`) cập nhật bộ luật QC (`full` mở `smoke`, `Dev Behavior QC Card`, Accessibility Snapshot); Wave 4 (`T4.1`–`T4.2`) bump `0.104.0`, khóa `token-budget.json` và build lại `plugins/tdq-workflow-agy/`.

## Mục lục

- Phân bổ Model & Effort
- Quy tắc thi hành
- Thiết kế Trước vs Sau
- Ràng buộc toàn cục & Bản đồ Sở hữu Hợp đồng
- P1 — Wave 1: Runner Core, Compact Timing & Auto Meta-Gate
- P2 — Wave 2: Smoke/E2E Suite Markers & Khóa lỗi v0.103.0
- P3 — Wave 3: Dev Behavior QC Card, Rules & Browser Accessibility Snapshot
- P4 — Wave 4: Version Bump 0.104.0, Token Budget & AGY Plugin Build
- P5 — Log & test bắt buộc
- Cụm song song
- Luật file nóng
- Definition of Done

## Phân bổ Model & Effort
<!-- i18n-allow: canonical model/effort plan allocation table -->
> User được quyền đổi `type model` hoặc `effort` lúc duyệt plan. Thang model: [subagent-tuning.md](../../tdq-conventions/references/subagent-tuning.md).

| Pha | Vai trò | Model | Effort | Ghi chú |
|---|---|---|---|---|
| `implement` (`Wave 1–2`, `Wave 4`) | `tdq-implementer` (mã nguồn Python, test, manifests) | `inherit` | `high` | Giữ baseline session `gemini-4-hydrogen`; lỗi >2x gọi `tdq-debugger` |
| `implement` (`Wave 3` `T3.2`) | Leader (`tu_lam` do nhãn `(mcp)`) | `inherit` | `high` | Có quyền gọi `chrome-devtools` MCP kiểm HTML thật ở `Q6` |
| `qc` | Leader (theo `muc_qc = full` từ `5a`) | `inherit` | `high` | `smoke-e2e --changed` + `tron-bo --workers auto` + `agy validate` |
| `report` | Leader | `inherit` | `high` | Xuất báo cáo `4` phần + Archify HTML + Tailscale `HTTP 200` |

## Quy tắc thi hành

1. Thứ tự wave là thứ tự phụ thuộc — không đảo ngược dependency `Cần:`.
2. Mỗi task: đánh `[~]` (hoặc `[>]` cho subagent) → viết test thất bại trước (Red) → sửa mã nguồn → test xanh (Green) → tick `[x]` ngay vào file này.
3. Giữa các bước dùng `tdq_test.py vung-cham` hoặc `smoke-e2e`; `tron-bo --workers auto` chạy ở cổng QC-F1.
4. Lệnh chạm state trong test luôn cách ly qua `TDQ_PROJECT_DIR` trong `TemporaryDirectory`.
5. QC FAIL → thêm task sửa `QCn.x` theo khuôn `R15-Compact`, chạy vòng sửa tối đa `3` lượt.
6. Không commit/push khi chưa được user đồng ý ở cổng report.
7. Tuân thủ `ANTI-1`..`ANTI-6` (không fake red, không blind assert, không sửa tay state).

## Thiết kế Trước vs Sau

| Khía cạnh | Hiện trạng (Trước `v0.103.1`) | Thiết kế mới (Sau `v0.104.0`) |
|---|---|---|
| Runner & Smoke | `tron-bo --workers 1` (`~19.8p`); `full` tắt `smoke`; `.ruff_cache` & `.html` gây fallback/hủy nhầm; `0` marker | Bổ sung `--workers auto` (`min(6, cpu)`), vá `.html`/`.ruff_cache`, gắn `@pytest.mark.smoke`/`e2e` + `smoke-e2e --changed <60s` ở `full` |
| Báo cáo & Browser QC | `tdq_timing.py show` in `5` cột `[unavailable]`; `48.8%` kiểm thủ tục tay; `tdq-browser-test` nặng visual pixel | `tdq_meta_gate.py` gom thành `1` dòng; ẩn cột `[unavailable]` khi rỗng (giữ JSON v2); mở đầu bằng `Dev Behavior QC Card` + Accessibility Snapshot |

*Đối chiếu sơ đồ kiến trúc:* Tuân thủ bản vẽ đã duyệt tại [2026-11-21-1536-nang-cap-qc-tester-e2e-preview.html](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/spec/2026-11-21-1536-nang-cap-qc-tester-e2e-preview.html) (`manifest`: `docs/tdq/spec/2026-11-21-1536-nang-cap-qc-tester-e2e-preview.manifest.json`, `5` module `M1`–`M5`).

## Ràng buộc toàn cục & Bản đồ Sở hữu Hợp đồng

- Ngôn ngữ: English cho toàn bộ nội dung luật ở `skills/`, `agents/`, docstring và CLI strings ở `scripts/` (giữ `i18n-allow` đúng chỗ cho chuỗi user thấy) · `utf8_io` · `TDQ_LOG=0` tắt log `stderr` · hàm `<= 50` dòng (`cyc <= 10`, `cog <= 15`) · `hooks/` gọi `scripts/` một chiều · `GIỮ NGUYÊN` `skills/tdq-conventions/references/clean-code.md` và cấu trúc JSON v2 của `tdq_timing.py`.

| Hợp đồng / Ký hiệu (§3c) | File & Task sở hữu | Task / File tiêu thụ |
|---|---|---|
| `_worker_count("auto")`, `DATA_EXTS`, `SMOKE_ROUTES`, `cmd_smoke_e2e` | `scripts/tdq_test.py` (`T1.1`) | `T2.1`–`T2.3`, `T3.1`, `tdq_runtime_bench.py` |
| `EXCLUDED_DIRS` (`.ruff_cache`) | `scripts/tdq_test_receipt.py` (`T1.1`) | `T1.1` runner receipt, `T5.1` |
| `pytest.ini` (`smoke`, `e2e`, `slow` markers) | `pytest.ini` (`T1.1`) | `T2.1`, `T2.2`, `T2.3`, `T3.1` |
| `bang_markdown()` ẩn cột `[unavailable]` khi rỗng | `scripts/tdq_timing.py` (`T1.2`) | `T3.1`, `token_audit.py`, `step_audit.py` |
| `tdq_meta_gate.py` & `doc_lint` check Scenario/Bug Board | `scripts/tdq_meta_gate.py`, `scripts/doc_lint.py` (`T1.3`) | `T3.1`, `T3.2`, `tdq_state.py` |
| Bảng `muc_qc`, `QC-F4` scoped, `Dev Behavior QC Card` | `skills/tdq-build/references/{qc.md,report-template.md}`, `agents/tdq-qc-tester.md` (`T3.1`) | `T4.2` build plugin & `token-budget.json` |
| Accessibility Tree Snapshot & `scenario-template.md` | `skills/tdq-browser-test/SKILL.md`, `skills/tdq-build/references/vision-test-loop.md` (`T3.2`) | `T4.2` build plugin & `token-budget.json` |
| Phiên bản `0.104.0`, `token-budget.json`, `plugins/tdq-workflow-agy/` | Manifests, `tools/`, `CHANGELOG.md`, `plugins/tdq-workflow-agy/` (`T4.1`, `T4.2`) | `Q7`, `Q8` |

## P1 — Wave 1: Runner Core, Compact Timing & Auto Meta-Gate

- [x] **T1.1** (e12m) Vá `DATA_EXTS` (`.html`, `.htm`), `EXCLUDED_DIRS` (`.ruff_cache`), thêm `--workers auto` (`min(6, cpu_count)`), subcommand `smoke-e2e` (`--changed`, `--files`, `--plan-only`, `--fail-fast`) và `pytest.ini` — Test: `py -3 -X utf8 -m pytest tests/test_tdq_test.py tests/test_tdq_test_receipt.py tests/test_smoke_e2e_routing.py -q`
  - Req: `§2#1, §3c#1, §3c#2, Q1` · Ngoài phạm vi: `GIỮ NGUYÊN` mặc định nội bộ `1` khi không truyền `--workers`, `GIỮ NGUYÊN` khóa SHA-256 receipt và `bo_sot`, không đụng `scripts/tdq_runtime_bench.py`
  - Chạm: `scripts/tdq_test.py`, `scripts/tdq_test_receipt.py`, `pytest.ini`, `tests/test_tdq_test.py`, `tests/test_tdq_test_receipt.py`, `tests/test_smoke_e2e_routing.py`
  - Sinh ra: `pytest.ini`, `tests/test_smoke_e2e_routing.py`
  - Cần: Không
  - Giao tiếp: Consumes: `args.workers`, `--files` / `git diff` | Produces: `_worker_count("auto") -> int`, `cmd_smoke_e2e(args) -> int`, `SMOKE_ROUTES`
  - Neo & Công cụ: Sửa `scripts/tdq_test.py` tại `DATA_EXTS` (`L104`), `_worker_count` (`L964`), `_add_run_options` (`L1478`), `main` (`L1492`); sửa `scripts/tdq_test_receipt.py` tại `EXCLUDED_DIRS` (`L29`); tạo mới `./pytest.ini` và `tests/test_smoke_e2e_routing.py`
  - Trước → Sau: thiếu `.html`/`.ruff_cache`, không nhận `--workers auto` hay `smoke-e2e` → lọc đúng data/cache, bật `--workers auto`, chạy `-m smoke` `< 60s` theo tuyến đổi
  - Tiêu chí chấp nhận (EARS): KHI truyền `--workers auto`, HỆ THỐNG PHẢI trả về `min(6, max(1, os.cpu_count() or 1))`; KHI sửa `.html` hoặc `.ruff_cache`, HỆ THỐNG PHẢI không fallback `tron-bo` và không gán `INCOMPLETE`; KHI chạy `smoke-e2e --changed`, HỆ THỐNG PHẢI ánh xạ đúng tuyến và thoát `0`
  - Logic cốt lõi: thêm `.html`/`.htm` vào `DATA_EXTS` và `.ruff_cache` vào `EXCLUDED_DIRS`; `_positive_or_auto_workers` đọc `"auto"`; `cmd_smoke_e2e` ánh xạ diff qua `SMOKE_ROUTES` rồi gọi `pytest -m` qua runner có `TDQ_LOG`
  - Ca góc hiểm & Assert: `--workers 0` → `ArgumentTypeError`; `--workers auto` kèm `--parallel` → `ValueError`; `git diff` rỗng → fallback `-m smoke`; `assert _worker_count("auto", False) <= 6`

- [x] **T1.2** (e10m) Cập nhật `scripts/tdq_timing.py` ẩn các cột telemetry V2 có `quality == "unavailable"` trên tất cả các hàng trong `bang_markdown` nhưng giữ nguyên JSON v2 và giữ cột khi có dữ liệu thật — Test: `py -3 -X utf8 -m pytest tests/test_timing.py tests/test_phase1_contract.py -q`
  - Req: `§2#2, §3c#4, Q2` · Ngoài phạm vi: `GIỮ NGUYÊN` `tong_hop()` schema JSON v2, `dong_ho_ngan()`, `_legacy_markdown()`, không sửa `scripts/token_audit.py` hay `scripts/step_audit.py`
  - Chạm: `scripts/tdq_timing.py`, `tests/test_timing.py`, `tests/test_phase1_contract.py`
  - Cần: Không
  - Giao tiếp: Consumes: `so_lieu: dict` schema v2 (`phases`, `metrics`) | Produces: `bang_markdown(so_lieu) -> str`
  - Neo & Công cụ: Sửa `scripts/tdq_timing.py` tại `bang_markdown` (`L430-L449`), cập nhật `tests/test_timing.py` (`L624-L636`) và `tests/test_phase1_contract.py` (`L180`)
  - Trước → Sau: luôn in cả `5` cột dù mọi hàng đều là `— [unavailable]` → chỉ in cột có ít nhất một giá trị khác `unavailable`; cả `5` rỗng thì gộp chú thích `1` dòng
  - Tiêu chí chấp nhận (EARS): KHI cả `5` metric đều `unavailable`, HỆ THỐNG PHẢI in bảng chỉ gồm `Phase`, `Wall clock`, `Times entered` và `0` ô `[unavailable]`; KHI có ít nhất `1` ô `partial`/`complete`, HỆ THỐNG PHẢI giữ nguyên cột đó và bảo toàn JSON v2
  - Logic cốt lõi: tính `active_keys` gồm các key trong `METRIC_KEYS` có ít nhất `1` hàng (`phases` + `Total`) khác `"unavailable"`; chỉ render header và cell cho `active_keys`, ghi dòng tóm tắt các metric ẩn nếu rỗng toàn phần
  - Ca góc hiểm & Assert: toàn bộ `5` cột unavailable → `assert "— [unavailable]" not in md`; dữ liệu mixed (`api` complete, 4 cột khác unavailable) → giữ cột `API request`

- [x] **T1.3** (e12m) Tạo `scripts/tdq_meta_gate.py` (`Auto Meta-Gate` `1` dòng với `TDQ_LOG=1/0`) và mở rộng `scripts/doc_lint.py` kiểm định dạng kịch bản & cờ CLI trong Bug Board — Test: `py -3 -X utf8 -m pytest tests/test_meta_gate.py tests/test_doc_lint.py -q`
  - Req: `§2#3, §3c#3, Q4` · Ngoài phạm vi: `GIỮ NGUYÊN` toàn bộ luật `R1`–`R15` cũ và chữ ký CLI `doc_lint.py`; không import `hooks/`
  - Chạm: `scripts/tdq_meta_gate.py`, `scripts/doc_lint.py`, `tests/test_meta_gate.py`, `tests/test_doc_lint.py`
  - Sinh ra: `scripts/tdq_meta_gate.py`, `tests/test_meta_gate.py`
  - Cần: Không
  - Giao tiếp: Consumes: `--files`, `--check-cli`, `TDQ_LOG` env | Produces: `run_meta_gate(files, check_cli) -> int`, `validate_cli_flags(doc)` trong `doc_lint.py`
  - Neo & Công cụ: Tạo mới `scripts/tdq_meta_gate.py` và `tests/test_meta_gate.py`; sửa `scripts/doc_lint.py` tại `rule_r15` và `main`
  - Trước → Sau: phải gọi rời rạc `4` script kiểm tài liệu và không bắt lỗi cờ CLI sai trong Bug Board → `1` lệnh `Auto Meta-Gate: PASS (...)` hoặc fail-closed exit `1`
  - Tiêu chí chấp nhận (EARS): KHI mọi check đạt, HỆ THỐNG PHẢI in `1` dòng `Auto Meta-Gate: PASS` và exit `0` (`<= 15s`); KHI Bug Board chứa cờ `--khong-ton-tai` trên script `scripts/*.py`, HỆ THỐNG PHẢI trả finding và exit `1`
  - Logic cốt lõi: gom kết quả `doc_lint`, `i18n_check`, `token_budget` (nếu đụng `skills/`), kiểm `Co-Authored-By:` sạch; trong `doc_lint.py` rà các lệnh `scripts/<tool>.py` ở `docs/tdq/bugs/` và `docs/tdq/scenarios/` đối chiếu tập cờ hợp lệ từ `--help`/AST
  - Ca góc hiểm & Assert: file scenario/bug trống hoặc không có dòng lệnh → pass sạch không crash; gặp script không tồn tại hoặc flag sai trong bug board → `assert exit_code == 1`

## P2 — Wave 2: Smoke/E2E Suite Markers & Khóa lỗi `v0.103.0`

- [ ] **T2.1** (e8m) Gắn marker `pytestmark = pytest.mark.smoke` cho `5` module kiểm định plugin, agent frontmatter, token budget và i18n — Test: `py -3 -X utf8 -m pytest -m smoke tests/test_agent_frontmatter.py tests/test_agy_plugin_validate.py tests/test_build_portable.py tests/test_token_budget.py tests/test_i18n_check.py -q`
  - Req: `§2#4, Q3` · Ngoài phạm vi: `GIỮ NGUYÊN` toàn bộ logic assertion sẵn có của từng file test
  - Chạm: `tests/test_agent_frontmatter.py`, `tests/test_agy_plugin_validate.py`, `tests/test_build_portable.py`, `tests/test_token_budget.py`, `tests/test_i18n_check.py`
  - Cần: `T1.1`
  - Giao tiếp: Consumes: `pytest.ini` (`smoke` marker) | Produces: `pytestmark` trên `5` file plugin/contract
  - Neo & Công cụ: Sửa dòng đầu `5` file test để gắn `import pytest` và khai báo marker cấp module
  - Trước → Sau: `0` test plugin/budget được gắn tầng `smoke` → cả `5` module được chọn qua `pytest -m smoke`
  - Tiêu chí chấp nhận (EARS): KHI chạy `pytest -m smoke --collect-only` trên `5` file này, HỆ THỐNG PHẢI thu thập đủ test case và chạy PASS không warning marker lạ
  - Logic cốt lõi: bổ sung khai báo `pytestmark = pytest.mark.smoke` cấp module đúng chuẩn `pytest.ini`
  - Ca góc hiểm & Assert: chạy `--strict-markers` thoát `0` với số test collected `> 0`

- [ ] **T2.2** (e8m) Gắn marker `pytestmark = [pytest.mark.smoke, pytest.mark.e2e]` cho `5` module hook, Rust dispatch parity và state gate — Test: `py -3 -X utf8 -m pytest -m "smoke and e2e" tests/test_agy_hooks.py tests/test_rust_dispatch_parity.py tests/test_bash_gate.py tests/test_command_gate.py tests/test_state_muc_qc.py -q`
  - Req: `§2#4, Q3` · Ngoài phạm vi: `GIỮ NGUYÊN` test logic và không gọi SSH sang máy ngoài
  - Chạm: `tests/test_agy_hooks.py`, `tests/test_rust_dispatch_parity.py`, `tests/test_bash_gate.py`, `tests/test_command_gate.py`, `tests/test_state_muc_qc.py`
  - Cần: `T1.1`
  - Giao tiếp: Consumes: `pytest.ini` (`smoke`, `e2e`) | Produces: `pytestmark` trên `5` file hook/state
  - Neo & Công cụ: Sửa dòng đầu `5` file test để gắn `import pytest` và khai báo marker cấp module
  - Trước → Sau: parity Rust và hook gates chưa tách riêng vào luồng `Changed-Flow E2E Smoke` → chạy tức thì khi `smoke-e2e` chọn tuyến `hooks/` hoặc `tdq_state`
  - Tiêu chí chấp nhận (EARS): KHI chạy `pytest -m "smoke and e2e"` trên `5` file, HỆ THỐNG PHẢI pass dưới `--strict-markers`
  - Logic cốt lõi: khai báo `pytestmark` cấp module không làm thay đổi tập case trong mỗi class `unittest.TestCase`
  - Ca góc hiểm & Assert: chạy `--strict-markers` đạt `exit_code == 0`, `0` skipped bất thường

- [ ] **T2.3** (e10m) Gắn marker `smoke` cho `5` module runner/finish/lint/MCP và viết `tests/test_v01030_regression_smoke.py` khóa lỗi `v0.103.0` (`call_mcp_tool` trên bundle compile) — Test: `py -3 -X utf8 scripts/tdq_test.py smoke-e2e --files agents/tdq-explorer.md tools/patches/skills_and_agents.py --fail-fast`
  - Req: `§2#4, Q3` · Ngoài phạm vi: không sửa `tools/patches/skills_and_agents.py`; test phải chạy độc lập trên bản compile thật/TemporaryDirectory không cần gọi Antigravity host
  - Chạm: `tests/test_tdq_runner_integration.py`, `tests/test_tdq_finish.py`, `tests/test_doc_lint_r15.py`, `tests/test_devtool_mcp_integration.py`, `tests/test_read_gate.py`, `tests/test_v01030_regression_smoke.py`
  - Sinh ra: `tests/test_v01030_regression_smoke.py`
  - Cần: `T1.1`, `T1.3`
  - Giao tiếp: Consumes: `SMOKE_ROUTES`, `build_agy_plugin` | Produces: `16+` module `smoke` + test khóa `v0.103.0`
  - Neo & Công cụ: Sửa `5` file test hiện có thêm marker; tạo mới `tests/test_v01030_regression_smoke.py`
  - Trước → Sau: từng lọt `call_mcp_tool` khi `tdq-qc-tester` đọc cache cũ → `smoke-e2e` bắt trực tiếp gói plugin compile chứa tool cấm trong `< 60s`
  - Tiêu chí chấp nhận (EARS): KHI mô phỏng tiêm `call_mcp_tool` hoặc `grep_search` vào bản patch agent trong `TemporaryDirectory`, HỆ THỐNG PHẢI thất bại kiểm tra frontmatter; KHI kiểm bản nguồn thật, HỆ THỐNG PHẢI pass dưới `< 60s`
  - Logic cốt lõi: test âm tính compile/patch vào `tmp_path` kiểm `tools` allowlist cho cả `8` agent `tdq-*.md` tách bạch khỏi cache `.agents/`
  - Ca góc hiểm & Assert: tiêm `"call_mcp_tool"` vào agent giả lập → assertion báo mismatch tool cấm; toàn bộ `>= 15` file `smoke` chạy không treo

## P3 — Wave 3: Dev Behavior QC Card, Rules & Browser Accessibility Snapshot

- [ ] **T3.1** (e12m) Cập nhật `qc.md` (`full` mở `smoke test = CÓ`, `--workers auto`, `QC-F4` OOP giới hạn cho class/tầng, `Auto Meta-Gate`, `Dev Behavior QC Card`, 5-step Fresh Evidence Gate), `report-template.md`, `agents/tdq-qc-tester.md` và tests hợp đồng — Test: `py -3 -X utf8 -m pytest tests/test_muc_qc_qc_md.py tests/test_dev_qc_card_rules.py tests/test_clean_code_rule.py tests/test_i18n_check.py -q`
  - Req: `§2#5, §5, Q5` · Ngoài phạm vi: `GIỮ NGUYÊN` `skills/tdq-conventions/references/clean-code.md`, `runtime test = KHÔNG` ở `full`, `tdq-qc-tester = KHÔNG` ở `full` và `CÓ` ở `ultra`
  - Chạm: `skills/tdq-build/references/qc.md`, `skills/tdq-build/references/report-template.md`, `agents/tdq-qc-tester.md`, `tests/test_muc_qc_qc_md.py`, `tests/test_dev_qc_card_rules.py`
  - Sinh ra: `tests/test_dev_qc_card_rules.py`
  - Cần: `T1.1`, `T1.2`, `T1.3`
  - Giao tiếp: Consumes: `tdq_test.py smoke-e2e`, `tdq_meta_gate.py`, `tdq_timing.py` | Produces: chuẩn `Dev Behavior QC Card`, `qc.md` (`muc_qc`), `test_dev_qc_card_rules.py`
  - Neo & Công cụ: Sửa `skills/tdq-build/references/qc.md` (`L36-L40`, `L99-L108`, `L148-L171`), `skills/tdq-build/references/report-template.md` (`L111-L139`), `agents/tdq-qc-tester.md` (`L1-L31`), `tests/test_muc_qc_qc_md.py` (`BangMucTest`, `L56-L77`); tạo mới `tests/test_dev_qc_card_rules.py`
  - Trước → Sau: `full` tắt `smoke`, ép `--workers 1`, dán log thô + `5` SOLID OOP cho mọi file → `full` bật `smoke test = CÓ` (`--workers auto`), `Auto Meta-Gate` `1` dòng, `Dev Behavior QC Card` đầu QC & `5`-step Gate Function
  - Tiêu chí chấp nhận (EARS): KHI kiểm bảng `muc_qc` mới, HỆ THỐNG PHẢI giữ `runtime test = KHÔNG` & `tdq-qc-tester = KHÔNG` ở `full` nhưng xác nhận `smoke test = CÓ`; KHI chạy `i18n_check.py` trên `qc.md` và `tdq-qc-tester.md`, HỆ THỐNG PHẢI trả `0` lỗi
  - Logic cốt lõi: cập nhật bảng `muc_qc` (`CÓ (vùng đổi)` hoặc `CÓ` theo `hop_le` trong `test_muc_qc_qc_md.py`), đổi `QC-F1` sang `--workers auto`, tách `QC-F4` thành nhánh OOP vs script thực dụng, thêm khối `Dev Behavior QC Card` vào đầu `qc.md` & `report-template.md`
  - Ca góc hiểm & Assert: toàn bộ text hướng dẫn luật viết tiếng Anh chuẩn trừ phần `i18n-allow`; `assert "smoke test" in qc_text` & `tests/test_clean_code_rule.py` vẫn pass

- [ ] **T3.2** (e12m) Cập nhật `skills/tdq-browser-test/SKILL.md` và `vision-test-loop.md` dùng mặc định Accessibility Tree Snapshot (`take_snapshot` + `console`/`errors` fail-closed), thêm `scenario-template.md` (`7–19` dòng + Bug Board + opt-in `e2e_adapter`) và kiểm thử HTML thực tế — Test: `py -3 -X utf8 -m pytest tests/test_vision_test_loop_doc.py tests/test_i18n_check.py -q`
  - Dùng: `tdq-browser-test` (mcp)
  - Để: thực thi luồng Accessibility Tree Snapshot (`take_snapshot` + `list_console_messages`) trên Archify HTML preview thật để nghiệm thu thiết kế mới tại `Q6`, nạp skill TRƯỚC bước đỏ
  - Ra: `skills/tdq-browser-test/SKILL.md`, `skills/tdq-browser-test/references/scenario-template.md`, `skills/tdq-build/references/vision-test-loop.md` đã chuẩn hóa và bằng chứng snapshot HTML `0` console error
  - Kiểm: `py -3 -X utf8 scripts/doc_lint.py skills/tdq-browser-test/SKILL.md skills/tdq-build/references/vision-test-loop.md`
  - Không dùng cho: chỉnh sửa script runner `tdq_test.py` hay cấu trúc `qc.md`
  - Dùng: `chrome-devtools` (mcp)
  - Để: gọi `navigate_page`, `take_snapshot`, `list_console_messages` kiểm giao diện Archify HTML sau khi cập nhật tài liệu E2E (`Q6`)
  - Ra: kết quả `take_snapshot` cấu trúc HTML và log `0` unhandled console error trên trang `docs/tdq/spec/2026-11-21-1536-nang-cap-qc-tester-e2e-preview.html`
  - Kiểm: `py -3 -X utf8 -m pytest tests/test_vision_test_loop_doc.py tests/test_devtool_mcp_integration.py -q`
  - Không dùng cho: cào dữ liệu web bên ngoài (`tdq-browser-research`) hoặc thay đổi mã nguồn JS của Archify
  - Req: `§2#6, Q5, Q6` · Ngoài phạm vi: `GIỮ NGUYÊN` khung `Tier 1..3`, `Given-When-Then`, `ANTI-1..ANTI-6` mà `test_vision_test_loop_doc.py` đang khóa; chỉ tạo file template một tầng (`references/`), không lồng `ref -> ref2`
  - Chạm: `skills/tdq-browser-test/SKILL.md`, `skills/tdq-browser-test/references/scenario-template.md`, `skills/tdq-build/references/vision-test-loop.md`, `tests/test_vision_test_loop_doc.py`
  - Sinh ra: `skills/tdq-browser-test/references/scenario-template.md`
  - Cần: `T1.3`
  - Giao tiếp: Consumes: `doc_lint.py` check scenario/bug-board (`T1.3`) | Produces: quy trình mặc định A11y Tree Snapshot, mẫu `7–19` dòng, Bug Board & opt-in adapter doc
  - Neo & Công cụ: Sửa `skills/tdq-browser-test/SKILL.md` (`L25-L77`), `skills/tdq-build/references/vision-test-loop.md`, `tests/test_vision_test_loop_doc.py` (`TestVisionTestLoopDoc`); tạo mới `skills/tdq-browser-test/references/scenario-template.md`
  - Trước → Sau: ép `take_screenshot` + `tdq_vision_diff.py` cho mọi UI test → ưu tiên `take_snapshot` + fail-closed click + `console`/`errors`, chỉ dùng pixel diff khi sửa layout/CSS
  - Tiêu chí chấp nhận (EARS): KHI kiểm `vision-test-loop.md` & `tdq-browser-test/SKILL.md`, HỆ THỐNG PHẢI giữ đủ `ANTI-1..ANTI-6`, `Given-When-Then`, có chỉ dẫn `take_snapshot` mặc định + mẫu `7–19` dòng + `i18n_check.py` sạch `0` lỗi
  - Logic cốt lõi: đặt Accessibility Tree Snapshot là Lớp 1 mặc định (`fail-closed` khi phần tử ẩn/bị che), chuyển Layer 2 screenshot sang có điều kiện (layout/CSS), ghi rõ adapter opt-in (`Playwright MCP` / `TesterArmy`) trong `scenario-template.md`
  - Ca góc hiểm & Assert: giữ nguyên các khóa `Given/When/Then/Tier 1..3/ANTI-1..6` và `--source`/`--figma-url` để `test_vision_test_loop_doc.py` pass

## P4 — Wave 4: Version Bump `0.104.0`, Token Budget & AGY Plugin Build

- [ ] **T4.1** (e8m) Uniform Mechanical Sweep: bump phiên bản `0.103.1` → `0.104.0` đồng bộ trong `6` tệp cấu hình, manifest và công cụ build (`Cargo.toml`, `.claude-plugin`, `.codex-plugin`, `tools/`) — Test: `py -3 -X utf8 -c "from pathlib import Path; files=['.claude-plugin/plugin.json','.codex-plugin/plugin.json','hooks/rust/tdq-dispatch/Cargo.toml','tools/patches/agy_manifests.py','tools/patches/__init__.py','tools/build_agy_plugin.py']; texts=[Path(f).read_text(encoding='utf-8') for f in files]; assert all('0.104.0' in t and '0.103.1' not in t for t in texts)"`
  - Req: `§2#7, Q7` · Ngoài phạm vi: `GIỮ NGUYÊN` code `.rs` và binary Rust đã biên dịch (`v0.103.1` runtime protocol không đổi); `Cargo.toml` chỉ nâng trường `version`
  - Chạm: `.claude-plugin/plugin.json`, `.codex-plugin/plugin.json`, `hooks/rust/tdq-dispatch/Cargo.toml`, `tools/patches/agy_manifests.py`, `tools/patches/__init__.py`, `tools/build_agy_plugin.py`
  - Cần: `T2.1`, `T2.2`, `T2.3`, `T3.1`, `T3.2`
  - Giao tiếp: Consumes: nguồn `0.103.1` | Produces: `PLUGIN_VERSION = "0.104.0"` trên cả `6` file
  - Neo & Công cụ: Sửa `.claude-plugin/plugin.json` (`L4`), `.codex-plugin/plugin.json` (`L3`), `hooks/rust/tdq-dispatch/Cargo.toml` (`L3`), `tools/patches/agy_manifests.py` (`PLUGIN_VERSION`), `tools/patches/__init__.py` (`L1`), `tools/build_agy_plugin.py` (`main`)
  - Trước → Sau: chuỗi phiên bản `0.103.1` → `0.104.0` đồng nhất
  - Tiêu chí chấp nhận (EARS): KHI quét cả `6` tệp, HỆ THỐNG PHẢI chứa `"0.104.0"` và có `0` chuỗi `"0.103.1"`
  - Logic cốt lõi: cập nhật đồng bộ trường version ở manifest JSON, `Cargo.toml` dòng 3 và `tools/patches`
  - Ca góc hiểm & Assert: kiểm parse JSON hợp lệ trên `.claude-plugin/plugin.json` và `.codex-plugin/plugin.json`

- [ ] **T4.2** (e12m) Cập nhật `README.md`, `UPSTREAM-TRACE.md`, `CHANGELOG.md` (`<= 500` dòng), đồng bộ `docs/tdq/token-budget.json`, biên dịch lại `plugins/tdq-workflow-agy/` và kiểm `agy.EXE plugin validate --strict` — Test: `py -3 -X utf8 -m pytest tests/test_token_budget.py tests/test_token_budget_lock.py tests/test_agy_plugin_validate.py -q`
  - Req: `§2#7, §2#8, Q7` · Ngoài phạm vi: KHÔNG cài đè ra `~/.gemini/config/plugins/` và KHÔNG chạy `build_portable.py --sinh-main` hay `git push`
  - Chạm: `README.md`, `UPSTREAM-TRACE.md`, `CHANGELOG.md`, `docs/archive/`, `docs/tdq/token-budget.json`, `plugins/tdq-workflow-agy/`
  - Cần: `T4.1`
  - Giao tiếp: Consumes: `skills/`, `agents/`, `scripts/`, `tools/build_agy_plugin.py` (`0.104.0`) | Produces: `plugins/tdq-workflow-agy/` (`v0.104.0`), `docs/tdq/token-budget.json` khớp SHA-256
  - Neo & Công cụ: Sửa `README.md`, `UPSTREAM-TRACE.md`, `CHANGELOG.md`; chạy `scripts/token_budget.py`, `tools/build_agy_plugin.py`, `agy.EXE plugin validate --strict plugins/tdq-workflow-agy`
  - Trước → Sau: gói `plugins/tdq-workflow-agy/` ở bản `0.103.1` và `token-budget.json` chưa khóa bản sửa → đồng bộ `0.104.0`, xoay `CHANGELOG.md <= 500` dòng và validate `0` findings
  - Tiêu chí chấp nhận (EARS): KHI chạy `tools/build_agy_plugin.py` và `agy.EXE plugin validate --strict`, HỆ THỐNG PHẢI trả về `"findings": []` và version `0.104.0`; KHI kiểm `CHANGELOG.md`, HỆ THỐNG PHẢI giữ `<= 500` dòng
  - Logic cốt lõi: cập nhật doc version + thêm mục `v0.104.0` (chuyển đoạn cũ sang `docs/archive/` nếu vượt `500` dòng), chạy `token_budget.py` cập nhật hash cho các file `skills/` vừa đổi, build lại `plugins/tdq-workflow-agy/` rồi kiểm strict
  - Ca góc hiểm & Assert: `len(CHANGELOG.md.splitlines()) <= 500`, `0` `"0.103.1"` ở `README.md`/`UPSTREAM-TRACE.md`, `test_token_budget_lock.py` xanh

## P5 — Log & test bắt buộc

- [ ] **T5.1** (e4m) Kiểm tra hợp đồng `TDQ_LOG=1/0` (ISO timestamp mặc định bật trên `stderr`, tắt khi `TDQ_LOG=0`) trên tất cả script runtime mới và đã sửa (`tdq_test.py`, `tdq_timing.py`, `tdq_meta_gate.py`, `doc_lint.py`) — Test: `py -3 -X utf8 -m pytest tests/test_phase1_logging.py tests/test_runtime_logging.py tests/test_meta_gate.py -q`
  - Req: `§4#1, Q8` · Ngoài phạm vi: `GIỮ NGUYÊN` định dạng ISO prefix của `tdq_finish.py`
  - Chạm: `tests/test_meta_gate.py`
  - Cần: `T1.1`, `T1.2`, `T1.3`
  - Giao tiếp: Consumes: `TDQ_LOG` env | Produces: kiểm chứng `stderr` ON/OFF parity
  - Neo & Công cụ: Chạy subprocess kiểm `TDQ_LOG=0` tắt log `stderr` sạch ở `scripts/tdq_meta_gate.py` và `scripts/tdq_test.py`
  - Trước → Sau: chưa khóa `TDQ_LOG` cho `tdq_meta_gate.py` mới → đồng bộ `100%` với chuẩn logging của toàn bộ `scripts/`
  - Tiêu chí chấp nhận (EARS): KHI chạy `TDQ_LOG=1`, HỆ THỐNG PHẢI in timestamp ISO ra `stderr`; KHI đặt `TDQ_LOG=0`, HỆ THỐNG PHẢI giữ `stderr` không có dòng `[YYYY-...]`
  - Logic cốt lõi: chạy subprocess kiểm chứng cả `TDQ_LOG=1` và `TDQ_LOG=0`
  - Ca góc hiểm & Assert: `assert err_off.strip() == ""` hoặc không chứa tiền tố timestamp khi `TDQ_LOG=0`

## Cụm song song

- **Wave 1 (chạy song song không đụng file):** `T1.1` (`M1`: `tdq_test.py`, `tdq_test_receipt.py`, `pytest.ini`), `T1.2` (`M2a`: `tdq_timing.py`), `T1.3` (`M2b`: `tdq_meta_gate.py`, `doc_lint.py`).
- **Wave 2 (chạy song song sau `T1.1` / `T1.3`, mỗi task `<= 6` file tách rời hoàn toàn):** `T2.1` (`5` file test plugin/budget/i18n), `T2.2` (`5` file test hook/state/parity), `T2.3` (`5` file test runner/lint + `test_v01030_regression_smoke.py`).
- **Wave 3 (chạy song song sau Wave 1):** `T3.1` (`skills/tdq-build/references/qc.md`, `report-template.md`, `agents/tdq-qc-tester.md`), `T3.2` (`skills/tdq-browser-test/`, `vision-test-loop.md` — Leader tự làm do có nhãn `(mcp)`).
- **Wave 4a (tuần tự sau Wave 2 & 3):** `T4.1` (Uniform Mechanical Sweep `6` file bump `0.104.0`).
- **Wave 4b (tuần tự sau `T4.1`):** `T4.2` + `T5.1` (`README.md`, `CHANGELOG.md`, `token-budget.json`, build `plugins/tdq-workflow-agy/`, kiểm `TDQ_LOG`).

## Luật file nóng

Không có file nóng nào nằm chồng lấn giữa các task trong cùng một wave: `T1.1`–`T1.3`, `T2.1`–`T2.3` và `T3.1`–`T3.2` sở hữu các tập `Chạm:` rời nhau hoàn toàn. Riêng `T3.2` có nhãn `(mcp)` do dùng `tdq-browser-test` / `chrome-devtools` nên trong mode `subagent` sẽ do Leader trực tiếp thực hiện.

## Definition of Done

- [ ] Q1 Wave 1 runner fixes (`--workers auto`, `.html` ở `DATA_EXTS`, `.ruff_cache` ở `EXCLUDED_DIRS`) pass — `py -3 -X utf8 -m pytest tests/test_tdq_test.py tests/test_tdq_test_receipt.py tests/test_smoke_e2e_routing.py -q`
- [ ] Q2 `tdq_timing.py` ẩn `5` cột `[unavailable]` & giữ JSON v2 — `py -3 -X utf8 -m pytest tests/test_timing.py tests/test_phase1_contract.py -q`
- [ ] Q3 Wave 2 `Changed-Flow E2E Smoke` (`>= 15` file marker `smoke`/`e2e`, `< 60s`, bắt lỗi `v0.103.0`) pass — `py -3 -X utf8 scripts/tdq_test.py smoke-e2e --files agents/tdq-explorer.md tools/patches/skills_and_agents.py --fail-fast`
- [ ] Q4 Wave 2 `Auto Meta-Gate` (`<= 15s`, `1` dòng `PASS`) & `doc_lint.py` kiểm cờ CLI Bug Board pass — `py -3 -X utf8 scripts/tdq_meta_gate.py --files docs/tdq/spec/2026-11-21-1536-nang-cap-qc-tester-e2e.md`
- [ ] Q5 Wave 1–3 `skills/` & `agents/` hợp đồng + `i18n_check` pass — `py -3 -X utf8 scripts/i18n_check.py; py -3 -X utf8 -m pytest tests/test_muc_qc_qc_md.py tests/test_dev_qc_card_rules.py tests/test_clean_code_rule.py tests/test_vision_test_loop_doc.py -q`
- [ ] Q6 Wave 3 Accessibility Tree Snapshot E2E (`take_snapshot` + `0` console errors trên Archify HTML preview) pass — `py -3 -X utf8 -m pytest tests/test_vision_test_loop_doc.py tests/test_devtool_mcp_integration.py -q` (+ kiểm MCP `chrome-devtools` trong phiên)
- [ ] Q7 Version `0.104.0` đồng bộ (`CHANGELOG.md <= 500` dòng), `token-budget.json` & `agy plugin validate --strict` (`0` findings) pass — `py -3 -X utf8 -m pytest tests/test_token_budget.py tests/test_token_budget_lock.py tests/test_agy_plugin_validate.py -q`
- [ ] Q8 `QC-F1`: `tron-bo --workers auto --fresh --reuse off` (`<= 420s`, `0` failed, `0` `INCOMPLETE`, `bo_sot=0`) & `TDQ_LOG=1/0` pass — `py -3 -X utf8 scripts/tdq_test.py tron-bo --workers auto --fresh --reuse off`
