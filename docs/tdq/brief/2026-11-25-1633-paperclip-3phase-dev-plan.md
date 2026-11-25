# BRIEF — Phân tích và lập Development Plan chi tiết tối ưu cho 3 pha tích hợp Paperclip (P0–P2)

Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

## Nguyên văn

> 1 và mở request phân tích và tạo development plan chi tiết tối ưu cho cả 3 pha đề xuất

- **Tài liệu nền vừa chốt & merge vào `dev` (`7d9c6a97`):** [integration-blueprint.md](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/artifacts/2026-11-25-1439-paperclip-tdq-integration-sim/integration-blueprint.md) và [2026-11-25-1439-paperclip-tdq-integration-sim.md](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/reports/2026-11-25-1439-paperclip-tdq-integration-sim.md).
- **Mục tiêu:** Khảo sát sâu mã nguồn thật của `TDQ-Workflow-Antigravity` (`scripts/`, `hooks/scripts/`, `plugins/tdq-workflow-agy/`, `tools/`, `tests/`) để lập hồ sơ phân tích kiến trúc và **Development Plan chi tiết, tối ưu, chia wave/task/contract/test rõ ràng** cho đủ cả `3` pha đề xuất (`P0`: khóa `O_EXCL` + Lease TTL, 3-tier queue + aging + `blockedBy`, circuit breaker + budget `hard_stop`, MCP policy + quarantine; `P1`: `4` `Domain Pack` + nối `KhoBM25` + khóa Zero-Downgrade; `P2`: add-on `Hybrid Bridge` tắt mặc định) mà bảo toàn `100%` hành vi và chất lượng TDQ gốc.
- **Phạm vi dự kiến:** Toàn bộ điểm chạm giữa `P0`, `P1`, `P2`, thứ tự phụ thuộc liên pha, hợp đồng JSON/CLI/hook, chiến lược test hồi quy (`Red -> Green`, smoke, runtime) và đồng bộ plugin (`tools/build_agy_plugin.py`).
- **Điểm cần làm rõ khi vào `analyze`:**
  1. Request này chỉ dừng ở sản phẩm phân tích + bộ Development Plan & hợp đồng chi tiết cho `3` pha (để tách các request `feature` thi công từng pha sau), hay gộp luôn phần code?
  2. Mức độ chi tiết mong muốn của kế hoạch (`file`/`symbol`/`contract`/`test-case`/`acceptance` cho từng task, bản đồ tách request con `P0`/`P1`/`P2`, thứ tự ưu tiên hoặc điều chỉnh phạm vi `P2`).
- **Ghi chú tầng tìm kiếm (Step 1b — `tdq_lsp.py check`):** `5/8` bậc ĐẠT, smoke `3/3` tầng (`grep`, `LSP`, `graphify`) trả lời được; `Bậc 6` thiếu `jsconfig.json`/`Cargo.toml`, `Bậc 7` đồ thị `graphify` cũ `1040` phút, `Bậc 8` `3` module `HET_HAN`. Không tự chạy `tdq_setup.py`; sau khi chốt pipeline và loại request sẽ kiểm hiệu ứng LSP cho `python:.` hoặc áp dụng `--bo-qua-lsp` phù hợp.

## Hiểu & kiến thức

### Năng lực dùng được

Phân vân → DÙNG. Kiểm kê ngày 2026-11-25: 42 skill trên đĩa (23 khớp lọc, 19 ẩn), cộng skill built-in trong context. Không xoá bảng này kể cả khi không có dòng DÙNG nào.

| Skill | Nguồn | Phán quyết | Dùng ở đâu / Lý do loại |
|---|---|---|---|
| `tdq-conventions`, `tdq-intake`, `tdq-spec`, `tdq-plan`, `tdq-build`, `tdq-setup`, `tdq-lean`, `tdq-status`, `tdq-check-status`, `tdq-checkportable`, `tdq-browser-research`, `tdq-browser-test` | `plugin:tdq-workflow` / `plugin:tdq-workflow-agy` | NỀN | Bộ khung điều phối TDQ-Workflow đang chạy cho toàn bộ request |
| Đã xét 19 skill đĩa khác + skill built-in | user/plugin/built-in | KHÔNG | khác lĩnh vực |

### Hồ sơ kiến trúc & Bảng đối chiếu vùng chạm (B1 Triangulation nông)

- **Kiến trúc hiện hữu (`docs/kien-truc.md:1-118`):** Chia `6` tầng (`skills/`, adapter đa host `.claude-plugin/`·`.codex-plugin/`·`.agents/plugins/`·`.opencode/plugins/`, `scripts/`, `hooks/scripts/`, `tests/`, `docs/tdq/`). Bất biến lõi: `scripts/` không bao giờ import `hooks/`; chỉ `scripts/tdq_state.py` được ghi `docs/tdq/state.json`; `build_portable.py --sinh-main` xuất nhánh `main` sạch; `tools/build_agy_plugin.py` biên dịch bundle sang `plugins/tdq-workflow-agy/`.
- **Ghi chú LSP & tầng tìm kiếm:** Gọi thử MCP `start_lsp(language_id="python")` báo `no server configured for language "python"` (mô-đun `python:.`, `javascript:.`, `rust:hooks/rust/tdq-dispatch` đã ghi nhận qua `--bo-qua-lsp` để phân tích docs-only); đã kiểm chéo bằng `rg` và `graphify affected tdq_state`.

| Vùng file chạm | Phát hiện qua lớp nào (Grep/LSP/Graphify) | Tác động & quan hệ |
|---|---|---|
| `scripts/tdq_state.py:579` (`def save`) | Grep + Graphify (`affected tdq_state`, 2 bước nhảy) | Hub trung tâm: hơn `35` module `scripts/`, `hooks/scripts/` và `plugins/tdq-workflow-agy/` phụ thuộc trực tiếp; sửa schema/lock ảnh hưởng diện rộng |
| `hooks/scripts/_common.py:467` & `tools/patches/agy_hooks.py:778` (`with_ntfs_lock`) | Grep (`rg`) | Đã có primitive NTFS lock (200 lần thử); P0 nên đánh giá tái sử dụng thay vì tự viết lại lockfile lệch chuẩn giữa Claude/AGY |
| `scripts/tdq_team.py:594,654` (`chia_dot`, `detect_tcas_collision`) | Grep (`rg`) + Graphify (`imports tdq_state` ở `L104`) | Xếp wave & chống va chạm AST; P0 cần nối `OLDEST_DISPATCH_SHARE`, 3-tier queue, `blockedBy` và `idempotencyKey` |
| `scripts/token_budget.py:45,117,142` (`TRAN_TOKEN = 3500`) | Grep (`rg`) | Khóa CI static `3500` token cho `skills/*/references/**/*.md`; P0 bổ sung runtime budget watchdog nhưng P1 bắt buộc không làm phình token luật vượt trần |
| `scripts/skill_router.py:141` (`class KhoBM25`) | Grep (`rg`) | Đã có lớp BM25 sẵn sàng trong repo; P1 nối vào `tdq-intake` và `Domain Pack` |
| `hooks/rust/tdq-dispatch/src/main.rs:12,197` & `events/pre_tool_use.rs:797` | Grep (`rg`) | Fast-path Rust `<0.5ms` cho `PreToolUse` (`[TDQ:GIT]`, `[TDQ:READONLY]`, `[TDQ:STATE]`, `[TDQ:TICK]`); cần quyết định mức parity Python/Rust ở P0 |
| `scripts/build_portable.py:12,17,738,831,865,870` & `tools/build_agy_plugin.py:2` | Grep (`rg`) | Chuỗi đóng gói `plugins/tdq-workflow-agy/` (`--sinh-agy`) và phát hành nhánh `main` (`--sinh-main`); mọi file mới cho P0/P1 phải qua dây chuyền này |

### 4 Giả thuyết thiết kế cần giải quyết ở pha implement (H1–H4)

- **H1:** `P0` khóa thuê (`O_EXCL` + TTL) + 3-tier Queue + Circuit Breaker + Budget `hard_stop` có thể tái dụng `with_ntfs_lock` / `lock.rs` mà giữ `0` hồi quy trên `tdq_state.py` single-writer và `test_rust_dispatch_parity.py`.
- **H2:** `P0` bảo mật MCP Policy + SHA-256 `Changed-Tool Quarantine` có thể gắn sạch vào `agy_pretooluse_gate.py`, `bash_gate.py` và `hooks/rust/tdq-dispatch/src/events/pre_tool_use.rs` dưới độ trễ `< 2 ms` mà không phá `2` luật shell cố định.
- **H3:** `P1` khung `Domain Pack` (`code-build`, `research-rca`, `pm-ba-content`, `ops-checklist`) + nối `skill_router.py` (`KhoBM25`) + Zero-Downgrade Lock (`escalate-to-build`) tương thích trọn vẹn với `token_budget.py` (`TRAN_TOKEN = 3500`), `i18n_check.py`, `build_portable.py --sinh-main` và `tools/build_agy_plugin.py`.
- **H4:** Lộ trình `P0`–`P2` chia được thành các request/wave thực thi độc lập (`TRAN_SONG_SONG=4`, không file nóng, có tiêu chí rollback và test matrix `vung-cham`/`tron-bo`/`run_full_verification.py`), trong đó `P2` (`Hybrid Bridge`) cô lập hoàn toàn và tắt mặc định.

### Kiến thức đã chốt

- **Cấu trúc đầu ra (`3a`) & Mặt chất lượng (`1abcd`):** Xuất `1` Master Roadmap (`master-roadmap.md`) + `3` Development Plan chi tiết (`dev-plan-p0.md`, `dev-plan-p1.md`, `dev-plan-p2.md`), phủ trọn Độ tin cậy & Song song, Bảo mật & Cửa ngõ MCP, Tương thích đa host & Đóng gói (`build_agy_plugin.py`, `build_portable.py --sinh-main`, `i18n_check.py`, `TRAN_TOKEN = 3500`), và Khả năng bảo trì & Tách sprint.
- **Đóng gói `P0` thành `1` request `feature` lớn (`1c`) kèm kiểm soát nổ bán kính:** Không tách rời `P0a`/`P0b` mà gom `P0` thành `1` request `feature` thống nhất, tổ chức bên trong thành các wave file tách rời, checkpoint rollback rõ ràng và giữ parity Python + Rust (`hooks/rust/tdq-dispatch/src/lock.rs`, `events/pre_tool_use.rs`, `test_rust_dispatch_parity.py`) ngay trong `P0` (`4a`).
- **Phân tầng lưu trữ & tương thích ngược (`2a`, `3a`):** Đặt template mặc định (4 `Domain Pack`, mẫu `mcp-policy.json`) trong runtime bundle (`scripts/defaults/`) để `build_portable.py --sinh-main` và `build_agy_plugin.py` đóng gói; dữ liệu chạy & override (`leases/`, `mcp-policy.json`, `domains/` tùy biến) đặt trong `docs/tdq/`; giữ nguyên `schema_version=6` ở `state.json` (chỉ thêm trường tùy chọn). Mặc định bật cân bằng (`Lease` + `Breaker` enforce ngay; `MCP Quarantine` chặn/hỏi riêng tool `write`/`destructive` mới phát sinh; `Budget hard_stop` kích hoạt khi khai trần trong `tdq-config.json`).
- **Host đích & Cầu nối `P2` (`2a`, `4a`, `5a`):** Tối ưu cho Antigravity Windows (người dùng cá nhân hằng ngày, `0` dependency ngoài, không DB nền) kèm tương thích ngược không vỡ test cho Claude Code, Codex, OpenCode và nhánh `main`. Pha `P2` (`Hybrid Bridge`, tắt mặc định, Docker/WSL2) dùng cầu nối CLI một chiều (`scripts/tdq_paperclip_bridge.py`), `state.json` giữ quyền chân lý duy nhất.
- **Mức QC (`5c`):** Đã chốt **`ultra`** (`muc_qc=ultra`).
- **Các phương án đã loại:** Loại tách `P0` 2–3 PR (`1a`/`1b` theo lựa chọn `1c`), loại nâng `state.json` lên `schema_version=7`, loại strict-block mọi tool MCP đọc ngay ngày đầu, và loại đồng bộ 2 chiều HTTP webhook daemon cho `P2`.

### Lộ trình

| Bước/phase | Chạy? | Vì sao |
|---|---|---|
| Research web | BỎ | Toàn bộ mã nguồn TDQ-Workflow-Antigravity và bản thiết kế nền (`7d9c6a97`) đã có sẵn trong repo |
| Interview sâu | CÓ | Đã hoàn tất 2 vòng chốt phạm vi (`1abcd 2a 3a 4a 5a`), tách P0 (`1c`), lưu trữ (`2a`), bảo vệ (`3a`), P2 (`4a`) và `muc_qc=ultra` (`5c`) |
| Khảo sát mã nguồn sâu (`implement`) | CÓ | Chia `3` shard `s1`–`s3` đọc trực tiếp `scripts/`, `hooks/scripts/`, `hooks/rust/tdq-dispatch/`, `tools/`, `tests/` để khóa từng symbol |
| Lập bộ Development Plan + `verify_plans.py` | CÓ | Xuất `1` Master Roadmap + `3` dev plan pha (`P0`–`P2`) + script Python tự kiểm schema JSON, luật import và bất biến wave |
| QC độc lập (`tdq-qc-tester`, mức `ultra`) | CÓ | Người dùng chốt `5c` (`muc_qc=ultra`): chạy kiểm `Q1`–`Q6`, `verify_plans.py` (`TDQ_LOG=1/0`), `QC-I1..I4` và agent QC độc lập |
| Archify HTML & Tailscale | CÓ | `work_kind=investigate`: miễn preview trước duyệt spec, dựng HTML một lần ở pha `report` và xác nhận HTTP `200` |

## Hỏi đáp

### Vòng 1 — Phạm vi & Bối cảnh (Scope Round — Đã chốt `1abcd 2a 3a 4a 5a`)

1. **Mặt chất lượng bao quanh bộ Development Plan P0–P2:** **A, B, C, D** (`1abcd`) — phủ đủ Độ tin cậy & Song song, Bảo mật & Cửa ngõ MCP, Tương thích đa host & Đóng gói (`build_agy_plugin.py`, `build_portable.py --sinh-main`, `i18n_check.py`, `TRAN_TOKEN = 3500`), và Khả năng bảo trì & Tách sprint (`P0a`/`P0b`/`P1`/`P2`, wave, EARS, test matrix `Red -> Green`).
2. **Phạm vi host đích ưu tiên hỗ trợ:** **A** (`2a`) — Antigravity Windows làm đích chính, đồng thời giữ tương thích ngược không vỡ test cho Claude Code, Codex, OpenCode và nhánh `main`.
3. **Cấu trúc đầu ra Development Plan:** **A** (`3a`) — `1` Master Roadmap (`P0`–`P2`) + `3` Development Plan tách pha (`dev-plan-p0.md`, `dev-plan-p1.md`, `dev-plan-p2.md`) kèm hợp đồng JSON/CLI/test matrix sẵn sàng mở từng request `feature`.
4. **Mức độ đồng bộ Rust dispatcher (`hooks/rust/tdq-dispatch`) ở P0:** **A** (`4a`) — giữ parity Python + Rust (`lock.rs`, `events/pre_tool_use.rs`, `test_rust_dispatch_parity.py`) ngay trong `P0`.
5. **Ngữ cảnh vận hành thực tế neo ràng buộc:** **A** (`5a`) — máy Windows cá nhân chạy hằng ngày (`1` người bảo trì chính, có phát hành nhánh `main` sạch; `0` dependency ngoài, không DB nền).

### Vòng 2 — Chi tiết Thiết kế & Chốt mức QC (Detail Round — Đã chốt `1c 2a 3a 4a 5c`)

1. **Đóng gói pha P0 thành request feature:** **C** (`1c`) — Gom trọn `P0` vào `1` request `feature` lớn duy nhất (tổ chức theo wave nội bộ tách file nóng và có checkpoint rollback).
2. **Quy ước lưu template mặc định & tương thích ngược `state.json`:** **A** (`2a`) — Template chuẩn trong runtime bundle (`scripts/defaults/`), override/dữ liệu chạy trong `docs/tdq/`, giữ nguyên `state.json` `schema_version=6` với trường tùy chọn tương thích ngược.
3. **Chế độ mặc định rào chắn P0 hằng ngày:** **A** (`3a`) — Bật cân bằng: `Lease` và `Breaker` enforce ngay; `MCP Quarantine` chỉ chặn/hỏi tool `write`/`destructive` mới; `Budget hard_stop` dừng cứng khi user khai trần chi phí trong `tdq-config.json`.
4. **Giao thức tích hợp pha P2 (`Hybrid Bridge`):** **A** (`4a`) — Cầu nối CLI một chiều có kiểm soát (`scripts/tdq_paperclip_bridge.py`), `state.json` giữ chân lý duy nhất của TDQ.
5. **Mức QC cho request hiện tại (`5c`):** **C** (`5c`) — `ultra` (DoD + trọn unit test + hồi quy + kiến trúc + clean code + smoke/verification script + `tdq-qc-tester` độc lập).
