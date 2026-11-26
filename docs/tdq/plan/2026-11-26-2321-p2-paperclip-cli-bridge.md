# PLAN — Triển khai Pha P2: Cầu nối CLI 1 chiều Paperclip Bridge

Ngày: 2026-11-27 · Spec: ../spec/2026-11-26-2321-p2-paperclip-cli-bridge.md (bản 1.0, ĐÃ DUYỆT)
Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md
Mode thực thi: main (đã chốt: 1a) — simulate thắng với chênh lệch 0.0 phút (main 12.2 phút vs team 12.3 phút ở hệ số agent 1.5, 6 task qua 4 đợt: Wave 1 có 2 task song song còn lại tuần tự)
Trạng thái plan: HOÀN THÀNH

> **Tóm tắt dễ hiểu:** Kế hoạch chia Pha P2 thành bốn giai đoạn tách biệt tệp sửa đổi để tránh xung đột. Đợt đầu tạo cấu hình mặc định tắt, xây dựng công cụ cầu nối CLI một chiều và viết bộ kiểm thử giả lập ngoại tuyến. Đợt tiếp theo mở danh sách đóng gói nhánh phát hành và đồng bộ toàn bộ sang gói Antigravity. Cuối cùng hệ thống kiểm tra log tĩnh, chạy toàn kho và thẩm định độc lập mức ultra trước khi báo cáo.

## Mục lục

- Phân bổ Model & Effort
- Quy tắc thi hành (áp cho mọi task)
- Thiết kế Trước vs Sau
- Ràng buộc toàn cục & Bản đồ Sở hữu Hợp đồng (Ownership Map)
- P1 — Cấu hình Tắt Mặc định & Cầu nối CLI 1 Chiều (Wave 1)
- P2 — Whitelist Đóng gói Nhánh phát hành `main` (Wave 2)
- P3 — Đồng bộ Bundle Antigravity & Xác minh Đóng gói (Wave 3)
- P4 — Kiểm chứng Tĩnh, Log Service & Nghiệm thu Mức `ultra` (Wave 4–5)
- Cụm song song
- Luật file nóng (một file, nhiều task chạm)
- Definition of Done

## Phân bổ Model & Effort
> User được quyền đổi `type model` hoặc `effort` lúc duyệt plan. Thang model: [subagent-tuning.md](../../tdq-conventions/references/subagent-tuning.md).

| Pha | Vai trò | Model | Effort | Ghi chú |
|---|---|---|---|---|
| `implement` | `self` hoặc `tdq-implementer` | `inherit` | `high` | Gồm 6 task qua 5 đợt tách file sở hữu; chọn chế độ chạy tại cổng mode sau khi duyệt plan |
| `qc` | `tdq-qc-tester` | `inherit` | `high` | Mức `ultra` (`3a`): rà bảo mật HTTP/che token, chạy `tron-bo`, `run_full_verification.py` và kiểm chéo độc lập |
| `report` | `self` | `inherit` | `medium` | Xuất báo cáo 2 tầng, Archify HTML `current` + Tailscale HTTP `200`, hỏi chốt commit và merge `dev` |

## Quy tắc thi hành (áp cho mọi task)
1. Thứ tự phase là thứ tự phụ thuộc — không đảo.
2. Mỗi task: đánh `[~]` khi bắt đầu → viết test trước (đỏ) → code → test xanh → đổi sang `[x]` NGAY vào file này. Trạng thái checkbox: `[ ]` chưa làm · `[~]` đang làm · `[x]` xong.
3. Mỗi bước: `tdq_test.py vung-cham`; trọn bộ chỉ ở QC.
4. Lệnh nào chạm state của workflow phải có `TDQ_PROJECT_DIR=<thư mục tạm>` ngay trên chính lệnh đó.
5. QC FAIL → thêm task fix vào mục QC của file này (không cần duyệt lại), loop đến khi pass.
6. Không commit/push cho đến khi user yêu cầu.
7. Tuân thủ 6 mã cấm cơ học (ANTI-1 Fake Red, ANTI-2 Blind Assertion, ANTI-3 Dirty State Git, ANTI-4 Late Tick, ANTI-5 Raw Dump, ANTI-6 Broad Area).

## Thiết kế Trước vs Sau

| Khía cạnh | Hiện trạng (Trước) | Thiết kế mới (Sau) |
|---|---|---|
| Cầu nối CLI 1 chiều | Chưa có CLI kết nối Paperclip Docker/WSL2 sang TDQ | Có `scripts/tdq_paperclip_bridge.py` (`status`, `pull`, `push-report`) mặc định tắt (`enabled=false` thoát mã `3`) dùng thuần Python stdlib |
| Nối P1 Domain & State | Kéo ticket phải tạo tay slug `HHMM`, domain và brief | `pull` tự tạo slug `YYYY-MM-DD-HHMM-<kebab>`, gọi `tdq_domains.route_domain()`, `tdq_state.py init`/`set` và tạo sẵn tệp brief |
| Cấu hình & Đóng gói | `DEFAULT_CONFIG` chưa có `paperclip_bridge`; `APPROVED_RUNTIME_MODULES` chưa mở bridge | Thêm `paperclip_bridge.enabled=false` vào `tdq_config.py` + `tdq-config.json`, cập nhật whitelist `main` và sync `plugins/tdq-workflow-agy/` |

*Đối chiếu sơ đồ kiến trúc:* Tham chiếu HTML preview đã bound ở spec: [2026-11-26-2321-p2-paperclip-cli-bridge-preview.html](../spec/2026-11-26-2321-p2-paperclip-cli-bridge-preview.html) và manifest `docs/tdq/spec/2026-11-26-2321-p2-paperclip-cli-bridge-preview.manifest.json`. WBS dưới đây ánh xạ từng task đúng vào 6 ranh giới module ở spec §2b.

## Ràng buộc toàn cục & Bản đồ Sở hữu Hợp đồng (Ownership Map)

- Ngôn ngữ: English comments/CLI/JSON keys (`i18n_check.py` `0` lỗi) · static `import utf8_io` · `TDQ_LOG=0` tắt log `0B` stderr · hàm mới `<= 50` dòng (`cyc <= 10`, `cog <= 15`) · `0` import ngược `hooks/` trong `scripts/` · `0` ghi trực tiếp `state.json` (chỉ gọi `tdq_state.py`) · giữ nguyên `schema_version=6` và `23` mã `all_agy_codes` · `0` mạng thật trong test (`unittest.mock`).

| Hợp đồng / Ký hiệu (§3c) | File & Task sở hữu | Task / File tiêu thụ |
|---|---|---|
| `DEFAULT_CONFIG["paperclip_bridge"]`, `_normalize_p2_booleans`, `_apply_p2_env_overrides` | `scripts/tdq_config.py`, `tdq-config.json`, `tests/test_agent_upgrade_mvp.py` (`T1.1`) | `T1.2` (`load_bridge_config`), `T3.1` (`build_agy_plugin.py`, parity) |
| `scripts/defaults/paperclip-bridge.default.json`, `load_bridge_config`, `validate_base_url`, `build_endpoint_url`, `resolve_api_token`, `redact_secrets`, `http_json_request`, `fetch_issue_json`, `map_issue_to_tdq_init`, `extract_report_summary`, `run_status`, `run_pull`, `run_push_report`, `main` | `scripts/defaults/paperclip-bridge.default.json`, `scripts/tdq_paperclip_bridge.py`, `tests/test_paperclip_bridge.py` (`T1.2`) | `T2.1` (`test_build_portable.py`), `T3.1` (`build_agy_plugin.py`), `T4.1` (`log-verify.json`), `T4.2` (`qc.md`) |
| `APPROVED_RUNTIME_MODULES`, `APPROVED_RELEASE_DOCS` (`tdq_paperclip_bridge` + default JSON) | `tests/test_build_portable.py` (`T2.1`) | `T3.1` (`--sinh-main --dry-run`), `T4.2` (`tron-bo`) |
| `plugins/tdq-workflow-agy/` (`tdq_paperclip_bridge.py`, `scripts/defaults/paperclip-bridge.default.json`, `tdq-config.json`) | `plugins/tdq-workflow-agy/` (`T3.1`) | `T4.1` (`log-verify.json`), `T4.2` (`run_full_verification.py`) |

---

## P1 — Cấu hình Tắt Mặc định & Cầu nối CLI 1 Chiều (Wave 1)

- [x] **T1.1** (e6m) Bổ sung khối `"paperclip_bridge": {"enabled": False}` vào `DEFAULT_CONFIG` của `scripts/tdq_config.py` (kèm chuẩn hóa boolean và ghi đè env `PAPERCLIP_BRIDGE_ENABLED` / `TDQ_PAPERCLIP_BRIDGE_ENABLED`), đồng bộ `tdq-config.json` gốc và viết unit test cấu hình trong `tests/test_agent_upgrade_mvp.py` — Test: `py -3 -X utf8 -m pytest -q tests/test_state.py tests/test_agent_upgrade_mvp.py -k "not test_agy_tdq_config_byte_for_byte_parity_with_root"`
  - Req: `§2#2, §2b tdq-config, §3c, §4` · Ngoài phạm vi: `GIỮ NGUYÊN` toàn bộ khối `qc`, `agents`, `p0`, `p1` và thứ tự `env > project > plugin`
  - Chạm: `scripts/tdq_config.py`, `tdq-config.json`, `tests/test_agent_upgrade_mvp.py`
  - Cần: `Không`
  - Giao tiếp: Consumes: `DEFAULT_CONFIG` (`L51-127`), `_parse_bool_value`, `_merge_config_layer`, `_apply_env_override` | Produces: `DEFAULT_CONFIG["paperclip_bridge"] == {"enabled": False}` và đọc env override boolean
  - Neo & Công cụ: Sửa `scripts/tdq_config.py` (`DEFAULT_CONFIG`, `_merge_config_layer`, `_apply_env_override`), đồng bộ `tdq-config.json` (`L78-82`), thêm test cấu hình P2 trong `tests/test_agent_upgrade_mvp.py`
  - Trước → Sau: `DEFAULT_CONFIG` và `tdq-config.json` chưa có khối `paperclip_bridge` → Có khối `paperclip_bridge` tắt mặc định (`enabled: false`), hỗ trợ override qua project config và biến môi trường
  - Tiêu chí chấp nhận (EARS): KHI gọi `tdq_config.load_config()`, HỆ THỐNG PHẢI trả `cfg["paperclip_bridge"]["enabled"] is False` và `json.loads(tdq-config.json) == DEFAULT_CONFIG`; KHI đặt `PAPERCLIP_BRIDGE_ENABLED=1` hoặc `TDQ_PAPERCLIP_BRIDGE_ENABLED=true`, `cfg["paperclip_bridge"]["enabled"]` PHẢI là `True`; giá trị lạ bị bỏ qua kèm cảnh báo stderr
  - Logic cốt lõi: Thêm nhánh `"paperclip_bridge": {"enabled": False}` vào `DEFAULT_CONFIG` và `tdq-config.json`; tái dụng `_parse_bool_value` chuẩn hóa khóa ở `load_config` và env
  - Ca góc hiểm & Assert:
    - Ca hiểm: Giá trị sai kiểu `"maybe"` trong `docs/tdq/config.json` hay biến môi trường → không crash, fallback giữ nguyên `False`
    - Tiêu chí: `assert cfg["paperclip_bridge"]["enabled"] is False and env_on_cfg["paperclip_bridge"]["enabled"] is True`

- [x] **T1.2** (e12m) Tạo `scripts/defaults/paperclip-bridge.default.json` (pure ASCII, `"enabled": false`, `endpoints: {health, issue, comments}`), tạo `scripts/tdq_paperclip_bridge.py` (`status`, `pull`, `push-report`, `import utf8_io`, `TDQ_LOG=1/0`, `0` import `hooks/`, thoát `0/2/3/4`, kiểm tra URL `http`/`https`, `quote(issue_id, safe="")`, `redact_secrets`, `pull` nối `tdq_domains.route_domain` + `subprocess` `tdq_state.py init`/`set` + tạo brief) và tạo bộ test mock ngoại tuyến 100% `tests/test_paperclip_bridge.py` — Test: `py -3 -X utf8 -m pytest -q tests/test_paperclip_bridge.py`
  - Req: `§2#1, §2#3, §2#4, §2b bridge-default-config, §2b paperclip-bridge-cli, §2b bridge-mock-suite, §3c, §4` · Ngoài phạm vi: `0` ghi trực tiếp `docs/tdq/state.json`, `0` import `hooks/`, `0` mạng thật trong test, `0` chuỗi tiếng Việt trong 3 file mới (`i18n_check.py`), mọi hàm `<= 50` dòng
  - Chạm: `scripts/defaults/paperclip-bridge.default.json`, `scripts/tdq_paperclip_bridge.py`, `tests/test_paperclip_bridge.py` (tạo mới)
  - Sinh ra: `scripts/defaults/paperclip-bridge.default.json`, `scripts/tdq_paperclip_bridge.py`, `tests/test_paperclip_bridge.py`
  - Cần: `Không`
  - Giao tiếp: Consumes: `tdq_config.load_config` (đọc an toàn `cfg.get("paperclip_bridge", {})`), `tdq_domains.route_domain`, CLI `scripts/tdq_state.py` (`init`/`set`/`get`) | Produces: `load_bridge_config`, `validate_base_url`, `build_endpoint_url`, `resolve_api_token`, `redact_secrets`, `http_json_request`, `fetch_issue_json`, `map_issue_to_tdq_init`, `extract_report_summary`, `run_status`, `run_pull`, `run_push_report`, `main`
  - Neo & Công cụ: Tạo mới 3 tệp theo hợp đồng spec §3c bằng thư viện chuẩn Python 3.11+ (gọi HTTP, xử lý URL, subprocess, argparse, JSON, regex) và test giả lập ngoại tuyến
  - Trước → Sau: Chưa có cấu hình mặc định hay CLI cầu nối Paperclip → Có CLI 1 chiều tắt mặc định (`exit 3`, `0` socket), `status` không bắt token, `pull` mở request đủ domain/state/brief và `push-report` đẩy tóm tắt một chiều kèm bảo vệ URL/token
  - Tiêu chí chấp nhận (EARS): KHI `enabled=false` (mặc định hoặc file project hỏng JSON), mọi lệnh PHẢI thoát mã `3` với `0` socket mở; KHI bật và gọi `status`, `GET /health` chạy không cần token; KHI gọi `pull --issue <id>` có token, hệ thống tạo slug `YYYY-MM-DD-HHMM-<kebab>`, chạy `route_domain`, gọi `tdq_state.py init`, rồi `set domain_id/brief_file` và tạo tệp brief; KHI `tdq_state.py init` lỗi hoặc HTTP `401`/`500`/timeout hoặc URL `file://`, hệ thống thoát mã `2`/`4` và che token `***` trong mọi thông báo; `TDQ_LOG=0` ra `0B` stderr
  - Logic cốt lõi: Nạp config theo tầng (`env > docs/tdq/paperclip-bridge.json > scripts/defaults/paperclip-bridge.default.json` kết hợp `tdq_config`); kiểm URL + Bearer token + `redact_secrets`; thực thi từng lệnh con qua helper đơn mục đích `<= 50` dòng
  - Ca góc hiểm & Assert:
    - Ca hiểm: URL `file:///etc/passwd`, `issue_id="PAP/../../secret"`, HTTP `401` mang secret token trong error body, `docs/tdq/paperclip-bridge.json` hỏng JSON, `init` trả exit `2` không được để lại file brief mồ côi
    - Tiêu chí: `assert rc_disabled == 3 and mock_urlopen.call_count == 0 and secret not in stderr_err and rc_init_fail == 4 and not brief_exists`

**Xong P1 khi**: `T1.1` và `T1.2` đều `[x]`, `tests/test_paperclip_bridge.py` và `tests/test_state.py` xanh `100%`.

---

## P2 — Whitelist Đóng gói Nhánh phát hành `main` (Wave 2)

- [x] **T2.1** (e5m) Cập nhật cả 2 whitelist trong `tests/test_build_portable.py`: thêm `"tdq_paperclip_bridge"` vào `APPROVED_RUNTIME_MODULES` và `"scripts/defaults/paperclip-bridge.default.json"` vào `APPROVED_RELEASE_DOCS`, giữ ngân sách tệp ngoài whitelist `<= 161` — Test: `py -3 -X utf8 -m pytest -q tests/test_build_portable.py`
  - Req: `§2#5, §2b portable-whitelist, §5, §6 Q4` · Ngoài phạm vi: `GIỮ NGUYÊN` trần `<= 161` tại `test_release_budget_excludes_only_approved_runtime_modules` (`L701`) và mọi hàm kiểm tra của `build_portable.py`
  - Chạm: `tests/test_build_portable.py`
  - Cần: `T1.1, T1.2`
  - Giao tiếp: Consumes: `scripts/tdq_paperclip_bridge.py`, `scripts/defaults/paperclip-bridge.default.json` (`T1.2`) | Produces: Whitelist đóng gói nhánh `main` đầy đủ cho Pha P2
  - Neo & Công cụ: Sửa `tests/test_build_portable.py` tại `APPROVED_RUNTIME_MODULES` (`L37-49`) và `APPROVED_RELEASE_DOCS` (`L50-81`)
  - Trước → Sau: Whitelist đóng gói chỉ có P0/P1 → Ghi nhận cả `tdq_paperclip_bridge` và `scripts/defaults/paperclip-bridge.default.json` đúng chuẩn phát hành `main`
  - Tiêu chí chấp nhận (EARS): KHI chạy `tests/test_build_portable.py`, toàn bộ bộ kiểm tra bao gồm `test_release_budget_excludes_only_approved_runtime_modules` và bao đóng import bắc cầu PHẢI pass `100%`
  - Logic cốt lõi: Thêm 1 tên module vào `APPROVED_RUNTIME_MODULES` và 1 đường dẫn JSON vào `APPROVED_RELEASE_DOCS`
  - Ca góc hiểm & Assert:
    - Ca hiểm: Bảo đảm mọi import nội bộ của `tdq_paperclip_bridge.py` (`utf8_io`, `tdq_config`, `tdq_domains`, `tdq_state`) đều nằm trong `kept_py` của `--sinh-main`
    - Tiêu chí: `assert "tdq_paperclip_bridge" in APPROVED_RUNTIME_MODULES and "scripts/defaults/paperclip-bridge.default.json" in APPROVED_RELEASE_DOCS`

**Xong P2 khi**: `T2.1` là `[x]` và `tests/test_build_portable.py` pass `100%`.

---

## P3 — Đồng bộ Bundle Antigravity & Xác minh Đóng gói (Wave 3)

- [x] **T3.1** (e8m) Đồng bộ `plugins/tdq-workflow-agy/` qua `tools/build_agy_plugin.py` (mang theo `tdq_paperclip_bridge.py`, `scripts/defaults/paperclip-bridge.default.json`, `tdq-config.json`), chạy toàn bộ `test_paperclip_bridge.py`, `test_agent_upgrade_mvp.py` (kể cả kiểm khớp byte `tdq-config.json`), `test_build_portable.py`, `test_rust_dispatch_parity.py`, `build_portable.py --sinh-main --dry-run` và `token_budget.py --kiem` — Test: `py -3 -X utf8 tools/build_agy_plugin.py && py -3 -X utf8 -m pytest -q tests/test_paperclip_bridge.py tests/test_agent_upgrade_mvp.py tests/test_build_portable.py tests/test_rust_dispatch_parity.py && py -3 -X utf8 scripts/build_portable.py --sinh-main --dry-run && py -3 -X utf8 scripts/token_budget.py --kiem`
  - Req: `§2#5, §2b agy-bundle, §6 Q1, §6 Q4` · Ngoài phạm vi: `0` sửa tay các tệp trong `plugins/tdq-workflow-agy/`; mọi đồng bộ đi qua `tools/build_agy_plugin.py`
  - Chạm: `plugins/tdq-workflow-agy/`
  - Cần: `T2.1`
  - Giao tiếp: Consumes: Các thay đổi từ `T1.1`, `T1.2`, `T2.1` và `tools/build_agy_plugin.py` | Produces: Bundle `plugins/tdq-workflow-agy/` đồng bộ sạch với `tdq-config.json` khớp từng byte, đủ tệp P2 trong `manifest.json`
  - Neo & Công cụ: Chạy `tools/build_agy_plugin.py`, cụm pytest đóng gói/parity và `build_portable.py --sinh-main --dry-run`
  - Trước → Sau: `plugins/tdq-workflow-agy/` còn ở trạng thái P1 cũ → Chứa đầy đủ `tdq_paperclip_bridge.py`, `paperclip-bridge.default.json`, `tdq-config.json` mới và pass kiểm khớp byte
  - Tiêu chí chấp nhận (EARS): KHI chạy `build_agy_plugin.py`, đầu ra PHẢI là `status="OK"`; `test_agy_tdq_config_byte_for_byte_parity_with_root` và `test_manifest_liet_ke_du_file_moi` PHẢI pass; dry-run `--sinh-main` giữ đủ bridge và config mặc định; `token_budget.py --kiem` exit `0`
  - Logic cốt lõi: Chạy script dựng bundle chính thức và xác minh toàn bộ cụm test phụ thuộc bundle AGY/portable
  - Ca góc hiểm & Assert:
    - Ca hiểm: Kiểm tra `plugins/tdq-workflow-agy/tdq-config.json` khớp chính xác từng byte với `tdq-config.json` gốc và không phát sinh cảnh báo `telemetry`
    - Tiêu chí: `assert root_cfg_bytes == agy_cfg_bytes and build_res["status"] == "OK"`

**Xong P3 khi**: `T3.1` là `[x]`, `build_agy_plugin.py`, parity/portable pytest và `token_budget --kiem` đều xanh.

---

## P4 — Kiểm chứng Tĩnh, Log Service & Nghiệm thu Mức `ultra` (Wave 4–5)

- [x] **T4.1** (e6m) Kiểm chứng `TDQ_LOG=1` (ISO timestamp) & `TDQ_LOG=0` (`0B` stderr), `ruff check` `0` lỗi trên file P2, `i18n_check.py` `0` dòng tiếng Việt mới trong 3 tệp P2, AST `0` import `hooks/` trong `scripts/`, độ dài hàm `<= 50` dòng, `schema_version == 6`, `len(all_agy_codes) == 23` và ghi `docs/tdq/artifacts/2026-11-26-2321-p2-paperclip-cli-bridge/log-verify.json` — Test: `py -3 -X utf8 -m ruff check scripts/tdq_paperclip_bridge.py scripts/tdq_config.py tests/test_paperclip_bridge.py tests/test_build_portable.py && py -3 -X utf8 scripts/i18n_check.py scripts/tdq_paperclip_bridge.py scripts/defaults/paperclip-bridge.default.json tests/test_paperclip_bridge.py`
  - Req: `§4, §5, §6 Q3, §6 Q4, §6 Q5, §6 Q6` · Ngoài phạm vi: Chỉ kiểm tra chỉ đọc và ghi kết quả JSON vào thư mục artifact của request
  - Chạm: `docs/tdq/artifacts/2026-11-26-2321-p2-paperclip-cli-bridge/log-verify.json` (tạo mới)
  - Sinh ra: `docs/tdq/artifacts/2026-11-26-2321-p2-paperclip-cli-bridge/log-verify.json`
  - Cần: `T3.1`
  - Giao tiếp: Consumes: `scripts/tdq_paperclip_bridge.py`, `scripts/tdq_config.py`, `scripts/defaults/paperclip-bridge.default.json`, `tests/test_paperclip_bridge.py` | Produces: Biên bản tĩnh `log-verify.json` (`overall_pass: true`)
  - Neo & Công cụ: Chạy kiểm tra ruff, i18n, quét AST thư mục scripts và đo kích thước luồng lỗi khi bật hoặc tắt log service
  - Trước → Sau: Chưa có hồ sơ kiểm chứng tĩnh tập trung cho P2 → Có tệp JSON bằng chứng tươi xác nhận sạch i18n, lint, AST, độ dài hàm và log service
  - Tiêu chí chấp nhận (EARS): KHI chạy `tdq_paperclip_bridge.py status` dưới `TDQ_LOG=0`, `stderr` PHẢI bằng đúng `0B`; `i18n_check.py` trả `0` dòng VI trên 3 tệp mới; `0` script trong `scripts/` import `hooks`; mọi hàm trong `tdq_paperclip_bridge.py` dài `<= 50` dòng
  - Logic cốt lõi: Thực thi tất cả phép đo tĩnh và log runtime rồi tổng hợp trường kết quả vào `log-verify.json`
  - Ca góc hiểm & Assert:
    - Ca hiểm: Bảo đảm `TDQ_LOG=0` vẫn im lặng `0B` kể cả khi lệnh thoát mã `3` do bridge tắt mặc định
    - Tiêu chí: `assert bridge_err0_bytes == 0 and hooks_imports_in_scripts == 0 and max_func_lines <= 50 and overall_pass is True`

- [x] **T4.2** (e14m) Nghiệm thu mức `ultra` (`Q1`–`Q7`): chạy `tools/run_full_verification.py`, `scripts/tdq_test.py tron-bo --workers auto --fresh --reuse off`, gọi `tdq-qc-tester` độc lập đến khi `Verdict: PASS` (`DEFECTS: None`), viết `qc.md`, `report.md`, kết xuất và xác minh Archify HTML `current` + Tailscale HTTP `200` — Test: `py -3 -X utf8 tools/run_full_verification.py; py -3 -X utf8 scripts/tdq_test.py tron-bo --workers auto --fresh --reuse off`
  - Req: `§2, §6 Q1-Q7` · Ngoài phạm vi: `0` sửa code sản phẩm trong bước viết báo cáo cuối; không commit chốt cuối hay đặt `phase=idle` khi chưa hỏi người dùng
  - Chạm: `docs/tdq/qc/2026-11-26-2321-p2-paperclip-cli-bridge.md`, `docs/tdq/reports/2026-11-26-2321-p2-paperclip-cli-bridge.md`, `docs/tdq/reports/2026-11-26-2321-p2-paperclip-cli-bridge.html` (tạo mới)
  - Sinh ra: `docs/tdq/qc/2026-11-26-2321-p2-paperclip-cli-bridge.md`, `docs/tdq/reports/2026-11-26-2321-p2-paperclip-cli-bridge.md`, `docs/tdq/reports/2026-11-26-2321-p2-paperclip-cli-bridge.html`
  - Cần: `T4.1`
  - Giao tiếp: Consumes: Toàn bộ mã P2 + `log-verify.json` | Produces: `qc.md`, `report.md`, Archify HTML `current` + Tailscale HTTP `200`
  - Neo & Công cụ: `tools/run_full_verification.py`, `scripts/tdq_test.py tron-bo`, `tdq-qc-tester`, `scripts/tdq_archify.py`, `scripts/doc_lint.py`, `scripts/tdq_finish.py`
  - Trước → Sau: Mới kiểm từng cụm → Có toàn kho `tron-bo` xanh, `tdq-qc-tester` (`Verdict: PASS`, `DEFECTS: None`) và báo cáo Archify HTML phục vụ HTTP `200`
  - Tiêu chí chấp nhận (EARS): KHI hoàn tất `T4.2`, `7/7` cổng `Q1`–`Q7` PHẢI đạt `PASS`, `run_full_verification.py` đạt `0` finding, `tdq-qc-tester` chốt `Verdict: PASS`, `tdq_archify.py verify` trả `status=current` và Tailscale HEAD trả `200`
  - Logic cốt lõi: Chạy xác minh toàn kho và gói AGY, điều phối `tdq-qc-tester` thẩm định độc lập, chạy tách ca nhiễu CPU nếu gặp trong `xdist`, viết `qc.md`/`report.md`, render Archify HTML và chạy `doc_lint` + `tdq_finish`
  - Ca góc hiểm & Assert:
    - Ca hiểm: Mọi chỉnh sửa `report.md` đều phải chạy lại `tdq_archify.py render` + `verify` để tránh manifest bị `stale`
    - Tiêu chí: `assert verify_res["status"] == "current" and tailscale_http == 200 and qc_verdict == "PASS"`

**Xong P4 khi**: Đủ `Q1`–`Q7` `[x]`, `tdq-qc-tester` trả `Verdict: PASS`, `DEFECTS: None` và Archify HTML `status=current` + Tailscale HTTP `200`.

---

## Cụm song song

Mỗi đợt giữ `<= 4` task, tập `Chạm:` rời nhau hoàn toàn (`0` va chạm `TCAS`):
- **Wave 1 (`P1`, song song):** `T1.1` (`tdq_config.py`, `tdq-config.json`, `test_agent_upgrade_mvp.py`) · `T1.2` (`paperclip-bridge.default.json`, `tdq_paperclip_bridge.py`, `test_paperclip_bridge.py`).
- **Wave 2 (`P2`, sau Wave 1):** `T2.1` (`test_build_portable.py`).
- **Wave 3 (`P3`, sau Wave 2):** `T3.1` (`plugins/tdq-workflow-agy/`).
- **Wave 4–5 (`P4`, tuần tự):** `T4.1` (`log-verify.json`) → `T4.2` (`qc.md`, `report.md`, `report.html`).

## Luật file nóng (một file, nhiều task chạm)

Không có bất kỳ tệp nguồn hay tệp kiểm thử nào bị từ 2 task trở lên chạm trong toàn bộ `P1`–`P4`: `scripts/tdq_config.py`, `tdq-config.json` và `tests/test_agent_upgrade_mvp.py` thuộc riêng `T1.1`; `scripts/defaults/paperclip-bridge.default.json`, `scripts/tdq_paperclip_bridge.py` và `tests/test_paperclip_bridge.py` thuộc riêng `T1.2`; `tests/test_build_portable.py` thuộc riêng `T2.1`; `plugins/tdq-workflow-agy/` thuộc riêng `T3.1`.

## Definition of Done

Trỏ về §6 của spec `2026-11-26-2321-p2-paperclip-cli-bridge.md` (`muc_qc=ultra`):

- [x] Q1 Cấu hình tắt mặc định & `tdq-config.json` sync — `py -3 -X utf8 -m pytest -q tests/test_agent_upgrade_mvp.py tests/test_paperclip_bridge.py -k "config or paperclip"`
- [x] Q2 CLI `status`, `pull`, `push-report` & tích hợp P1/state (`1a`, `2a`) — `py -3 -X utf8 -m pytest -q tests/test_paperclip_bridge.py`
- [x] Q3 Bảo mật HTTP & Bộ kiểm thử mock ngoại tuyến `100%` — `py -3 -X utf8 -m pytest -q tests/test_paperclip_bridge.py`
- [x] Q4 Đóng gói đa host (`main`, AGY), `i18n_check` & `token_budget` — `py -3 -X utf8 tools/build_agy_plugin.py && py -3 -X utf8 -m pytest -q tests/test_build_portable.py && py -3 -X utf8 scripts/build_portable.py --sinh-main --dry-run && py -3 -X utf8 scripts/token_budget.py --kiem && py -3 -X utf8 scripts/i18n_check.py scripts/tdq_paperclip_bridge.py scripts/defaults/paperclip-bridge.default.json tests/test_paperclip_bridge.py`
- [x] Q5 Hồi quy toàn kho (`tron-bo`), Ruff, AST `0` import ngược & thẩm định độc lập `ultra` (`tdq-qc-tester`) — `py -3 -X utf8 tools/run_full_verification.py && py -3 -X utf8 scripts/tdq_test.py tron-bo --workers auto --fresh --reuse off`
- [x] Q6 Sạch Clean Code, độ dài hàm `<= 50` dòng & Rollback xóa sạch — `py -3 -X utf8 -m ruff check scripts/tdq_paperclip_bridge.py scripts/tdq_config.py tests/test_paperclip_bridge.py tests/test_build_portable.py && py -3 -X utf8 -m pytest -q tests/test_state.py tests/test_paperclip_bridge.py`
- [x] Q7 Báo cáo, working log & Archify HTML (`current`, HTTP `200`) — `py -3 -X utf8 scripts/tdq_archify.py verify --document docs/tdq/reports/2026-11-26-2321-p2-paperclip-cli-bridge.md --manifest docs/tdq/reports/2026-11-26-2321-p2-paperclip-cli-bridge.manifest.json`
