# PLAN — Triển khai Pha P0: Lõi An toàn Runtime, Khóa NTFS/Rust & Cửa ngõ MCP

Ngày: 2026-11-25 · Spec: ../spec/2026-11-25-1834-p0-runtime-safety-rust-parity.md (bản 1.0, ĐÃ DUYỆT)
Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md
Mode thực thi: subagent (đã chốt: 1a) — simulate thắng với chênh lệch 13.2 phút (`subagent` 15.3 phút vs `main` 28.5 phút ở hệ số agent 1.5, 14 task qua 5 đợt: giao 9, leader giữ 5)
Trạng thái plan: HOÀN THÀNH

> **Tóm tắt dễ hiểu:** Bản kế hoạch chia nhỏ phần lõi an toàn thành năm giai đoạn tách biệt tệp sửa đổi để tránh xung đột. Bốn đợt đầu lần lượt xây dựng khóa chống ghi đè, nâng cấp trạng thái và hàng đợi, nối cổng bảo mật Python với Rust rồi biên dịch gói phát hành. Giai đoạn cuối chạy trọn bộ kiểm tra và gọi agent thẩm định độc lập trước khi báo cáo.

## Mục lục

- Phân bổ Model & Effort
- Quy tắc thi hành (áp cho mọi task)
- Thiết kế Trước vs Sau
- Ràng buộc toàn cục & Bản đồ Sở hữu Hợp đồng (Ownership Map)
- P1 — Khóa sidecar, cấu hình P0 & Rust lock.rs (Wave 1)
- P2 — Hub tdq_state v6, Hàng đợi tdq_team, Ngân sách & mcp_policy (Wave 2–3)
- P3 — Python Hooks, Rust pre_tool_use.rs, Manifests & Module nhánh main (Wave 3–4)
- P4 — Biên dịch Rust, Sync Bundle & Kiểm Đóng gói (Wave 5)
- P5 — Log & kiểm chứng bắt buộc mức ultra (Wave 6–7)
- Cụm song song
- Luật file nóng (một file, nhiều task chạm)
- Definition of Done

## Phân bổ Model & Effort
> User được quyền đổi `type model` hoặc `effort` lúc duyệt plan. Thang model: [subagent-tuning.md](../../tdq-conventions/references/subagent-tuning.md).

| Pha | Vai trò | Model | Effort | Ghi chú |
|---|---|---|---|---|
| `implement` | `self` hoặc `tdq-implementer` | `inherit` | `high` | Sửa `tdq_state.py`, Python hooks & Rust `pre_tool_use.rs` cần giữ parity; user có thể chọn `main` hoặc `subagent` lúc chốt mode |
| `qc` | `tdq-qc-tester` | `inherit` | `high` | Mức `ultra` (`3a`): đọc chéo mã Python/Rust mới, tái chạy trọn bộ test và parity độc lập |
| `report` | `self` | `inherit` | `medium` | Xuất báo cáo 2 tầng, Archify HTML `current` + Tailscale HTTP `200`, hỏi lệnh merge `dev` |

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
| Ghi state & khóa tác vụ | `tdq_state.save()` chỉ in `"overwriting anyway"` và `os.replace()`; chưa có thuê TTL | `tdq_lease.acquire_sidecar_lock()` giữ neo `.lock` bền đồng bộ `lock.rs` + `O_EXCL` TTL lease |
| Hàng đợi, Breaker & Budget | `tdq_team.chia_dot()` xếp tuyến tính; chưa có `blocked_by`, `p0_runtime` hay ngưỡng ngân sách | Hàng đợi 3 tầng (`OLDEST_DISPATCH_SHARE=4`), `blocked_by`, `idempotency_key`, `p0_runtime` v6, `80%`/`hard_stop` |
| Cửa ngõ MCP & Parity | `hooks.json:76` & `agy_manifests.py:72` bỏ lọt non-LSP; `agy_pretooluse_gate.py` bị exclude ở AGY | Mở rộng matcher non-LSP, nối `mcp_policy` + Breaker vào `lsp_gate`/`edit_gate`/`bash_gate` & `pre_tool_use.rs` mã `READONLY` |

*Đối chiếu sơ đồ kiến trúc:* Tham chiếu HTML preview đã bound ở spec: [2026-11-25-1834-p0-runtime-safety-rust-parity-preview.html](../spec/2026-11-25-1834-p0-runtime-safety-rust-parity-preview.html) và manifest `docs/tdq/spec/2026-11-25-1834-p0-runtime-safety-rust-parity-preview.manifest.json`. WBS dưới đây ánh xạ từng task đúng vào 11 ranh giới module ở spec §2b.

## Ràng buộc toàn cục & Bản đồ Sở hữu Hợp đồng (Ownership Map)

- Ngôn ngữ: English comments/CLI · `utf8_io` · `TDQ_LOG=0` tắt log `0B` stderr · hàm `<= 50` dòng (`cyc <= 10`, `cog <= 15`) · `GIỮ NGUYÊN` chữ ký công khai cũ và `0` import ngược từ `hooks/` vào `scripts/` · giữ tròn `23` mã `all_agy_codes` · giữ nguyên `schema_version=6` ở `docs/tdq/state.json`.

| Hợp đồng / Ký hiệu (§3c) | File & Task sở hữu | Task / File tiêu thụ |
|---|---|---|
| `acquire_sidecar_lock`, `acquire_lease`, `renew_lease`, `release_or_reclaim` | `scripts/tdq_lease.py` (`T1.1`) | `T2.1` (`tdq_state.py`), `T2.2` (`tdq_team.py`), `T2.4` (`mcp_policy.py`), `T3.4` (`test_build_portable.py`) |
| `scripts/defaults/mcp-policy.default.json` | `scripts/defaults/mcp-policy.default.json` (`T1.1`) | `T2.4` (`mcp_policy.py`), `T3.2` (`pre_tool_use.rs`), `T4.1` (`build_agy_plugin.py`) |
| `DEFAULT_CONFIG["p0"]` | `scripts/tdq_config.py` (`T1.2`) | `T2.1` (`tdq_state.py`), `T2.3` (`tdq_timing.py`), `T2.4` (`mcp_policy.py`), `T3.1` (`hooks`) |
| `SidecarLockGuard`, `acquire_sidecar_lock`, `acquire_lease` (Rust) | `hooks/rust/tdq-dispatch/src/lock.rs` (`T1.3`) | `T3.2` (`pre_tool_use.rs`) |
| `save()` sidecar-locked & `default_state()["p0_runtime"]` | `scripts/tdq_state.py` (`T2.1`) | `T2.2` (`tdq_team.py`), `T2.3` (`tdq_timing.py`), `T3.1` (`hooks`), `T3.2` (`pre_tool_use.rs`) |
| `prioritize_tasks`, `dispatch_ready_waves` (`OLDEST_DISPATCH_SHARE=4`) | `scripts/tdq_team.py` (`T2.2`) | `T3.1`, `T5.1`, `T5.2` |
| `check_budget_status` (`80%` / `hard_stop`) | `scripts/tdq_timing.py` (`T2.3`) | `T3.1` (`edit_gate.py`/`bash_gate.py`), `T3.2` (`pre_tool_use.rs`) |
| `evaluate_tool_call`, `approve` CLI, `reset` CLI | `scripts/mcp_policy.py` (`T2.4`) | `T3.1` (`lsp_gate.py`), `T3.2` (`pre_tool_use.rs`), `T3.4` (`test_build_portable.py`) |
| Non-LSP MCP matchers | `hooks/hooks.json`, `tools/patches/agy_manifests.py` (`T3.3`) | `T4.1` (`build_agy_plugin.py`) |

---

## P1 — Khóa sidecar, cấu hình `P0` & Rust `lock.rs` (Wave 1)

- [x] **T1.1** (e12m) Dựng `scripts/tdq_lease.py` sidecar lock `.lock` (KHÔNG unlink sau unlock) + lease `O_EXCL` TTL + mẫu `scripts/defaults/mcp-policy.default.json` + unit test — Test: `py -3 -X utf8 -m pytest tests/test_tdq_lease.py`
  - Req: `§2#1, §2b lease-core, §3c#1, §4` · Ngoài phạm vi: `GIỮ NGUYÊN` `hooks/scripts/_common.py`, tuyệt đối `0` import từ `hooks/`
  - Chạm: `scripts/tdq_lease.py`, `scripts/defaults/mcp-policy.default.json`, `tests/test_tdq_lease.py` (tạo mới)
  - Sinh ra: `scripts/tdq_lease.py`, `scripts/defaults/mcp-policy.default.json`, `tests/test_tdq_lease.py`
  - Cần: `Không`
  - Giao tiếp: Consumes: `os`, `msvcrt`/`fcntl` stdlib | Produces: `sidecar_lock_path`, `acquire_sidecar_lock`, `acquire_lease`, `renew_lease`, `release_or_reclaim` và file JSON mặc định balanced
  - Neo & Công cụ: Tạo mới 3 tệp; tham chiếu quy ước `.lock` tại `hooks/rust/tdq-dispatch/src/lock.rs:15-86` (`SidecarLockGuard`, `acquire_sidecar_lock`)
  - Trước → Sau: Chưa có khóa sidecar ngoài thư mục `hooks/` hay thuê tác vụ TTL → Có `tdq_lease.py` khóa NTFS/POSIX giữ tệp `.lock` bền và `mcp-policy.default.json` chuẩn ASCII đóng gói được vào `main`
  - Tiêu chí chấp nhận (EARS): KHI hai tiến trình cạnh tranh `acquire_lease` hoặc `acquire_sidecar_lock`, HỆ THỐNG PHẢI cấp tối đa 1 chủ sở hữu, giữ tệp `.lock` sau khi thoát `with` và cho phép `release_or_reclaim(force_expired=True)` thu hồi lease hết hạn; `TDQ_LOG=0` phát `0B` stderr
  - Logic cốt lõi: Mở `.lock` (`O_CREAT|O_RDWR`), khóa byte với `msvcrt.locking(LK_NBLCK)` / `fcntl.flock` có backoff; tạo lease JSON bằng `os.O_CREAT | os.O_EXCL` trong `docs/tdq/leases/`
  - Ca góc hiểm & Assert:
    - Ca hiểm: Tiến trình giữ lease chết trước khi nhả → kiểm `expires_at` quá hạn được thu hồi mà không làm mất lock active khác
    - Tiêu chí: `assert reclaimed is True and os.path.exists(lock_file) and err_tdq_log_0 == b""`

- [x] **T1.2** (e6m) Bổ sung khối cấu hình `p0` cân bằng (`3a`) + `3` kill-switch vào `DEFAULT_CONFIG` trong `scripts/tdq_config.py` — Test: `py -3 -X utf8 -m pytest tests/test_state.py`
  - Req: `§2#2, §2b config-p0, §3c#2` · Ngoài phạm vi: `GIỮ NGUYÊN` toàn bộ khóa `qc` và `agents` trong `DEFAULT_CONFIG` (`L35-93`) và thứ tự `env > project (docs/tdq/config.json) > plugin (tdq-config.json)` (`L177-191`)
  - Chạm: `scripts/tdq_config.py`
  - Cần: `Không`
  - Giao tiếp: Consumes: `DEFAULT_CONFIG` (`L35-93`) | Produces: `DEFAULT_CONFIG["p0"]` (`lease_enabled`, `lease_ttl_sec`, `breaker_enabled`, `breaker_consecutive_failures`, `mcp_quarantine_enabled`, `mcp_mode`, `oldest_dispatch_share`, `budget_caps`)
  - Neo & Công cụ: Sửa `scripts/tdq_config.py` tại `DEFAULT_CONFIG` (`L35-93`) và `_deep_merge` (`L181-188`)
  - Trước → Sau: `DEFAULT_CONFIG` chỉ có `qc` và `agents` → Có sẵn nhánh `p0` mặc định cân bằng (tắt `hard_stop` khi chưa khai trần, bật `lease` & `breaker` & `mcp balanced`)
  - Tiêu chí chấp nhận (EARS): KHI gọi `load_config()` khi chưa có `docs/tdq/config.json`, HỆ THỐNG PHẢI trả về `cfg["p0"]["lease_enabled"] is True`, `cfg["p0"]["mcp_mode"] == "balanced"` và `cfg["p0"]["budget_caps"]["hard_stop_tokens"] is None`
  - Logic cốt lõi: Thêm nhánh `"p0"` vào `DEFAULT_CONFIG` với giá trị mặc định khớp bảng thiết kế và để `_deep_merge` nạp ghi đè từ `docs/tdq/config.json`
  - Ca góc hiểm & Assert:
    - Ca hiểm: File `docs/tdq/config.json` chỉ ghi đè 1 cờ (`breaker_enabled=false`) → các cờ `p0` khác vẫn giữ mặc định qua `_deep_merge`
    - Tiêu chí: `assert cfg["p0"]["mcp_quarantine_enabled"] is True and cfg["p0"]["breaker_enabled"] is False`

- [x] **T1.3** (e10m) Mở rộng `hooks/rust/tdq-dispatch/src/lock.rs` kiểm tra lease TTL & thu hồi lease hết hạn khớp `tdq_lease.py` — Test: `cargo test --manifest-path hooks/rust/tdq-dispatch/Cargo.toml lock`
  - Req: `§2#3, §2b rust-lock, §3c#1` · Ngoài phạm vi: `GIỮ NGUYÊN` hành vi không unlink `.lock` của `SidecarLockGuard::drop` (`L15-21`) và `acquire_sidecar_lock` (`L31-86`)
  - Chạm: `hooks/rust/tdq-dispatch/src/lock.rs`
  - Cần: `Không`
  - Giao tiếp: Consumes: `SidecarLockGuard`, `acquire_sidecar_lock`, `atomic_write_file` (`L11-95`) | Produces: `is_lease_expired(json_val, now_epoch)` và `cleanup_expired_leases(leases_dir, now_epoch)`
  - Neo & Công cụ: Sửa `hooks/rust/tdq-dispatch/src/lock.rs` (`L11-95`, `SidecarLockGuard`, `acquire_sidecar_lock`, `atomic_write_file`) thêm hàm lease helper + unit test Rust
  - Trước → Sau: `lock.rs` chỉ có sidecar lock thô → Có thêm hàm kiểm tra/dọn lease TTL khớp hợp đồng JSON của `tdq_lease.py`
  - Tiêu chí chấp nhận (EARS): KHI gặp file lease JSON có `expires_at` nhỏ hơn thời điểm hiện tại, HỆ THỐNG PHẢI nhận diện hết hạn (`true`) và thu hồi an toàn dưới `acquire_sidecar_lock`, không xóa lease còn hạn
  - Logic cốt lõi: Parse chuỗi epoch/ISO tối giản bằng `serde_json::Value` có sẵn trong Cargo, kiểm tra hết hạn trước khi xóa tệp dưới `acquire_sidecar_lock`
  - Ca góc hiểm & Assert:
    - Ca hiểm: Lease JSON hỏng hoặc thiếu `expires_at` → bỏ qua an toàn không xóa nhầm tệp hợp lệ, trả kết quả `false`
    - Tiêu chí: `assert_eq!(cleanup_expired_leases(&dir, now), 1)` trên test lease hết hạn + 1 lease còn hạn

**Xong P1 khi**: `T1.1`–`T1.3` đều `[x]`, `tests/test_tdq_lease.py`, `tests/test_state.py` và `cargo test ... lock` pass `100%`, `TDQ_LOG=0` ra `0B` stderr.

---

## P2 — Hub `tdq_state` v6, Hàng đợi `tdq_team`, Ngân sách & `mcp_policy` (Wave 2–3)

- [x] **T2.1** (e12m) Bọc `tdq_lease.acquire_sidecar_lock` vào `tdq_state.save()` và bổ sung nhánh tùy chọn `p0_runtime` giữ `schema_version=6` trong `scripts/tdq_state.py` — Test: `py -3 -X utf8 -m pytest tests/test_state.py tests/test_ntfs_concurrency.py`
  - Req: `§2#4, §2b state-v6, §3c#2, §5` · Ngoài phạm vi: `GIỮ NGUYÊN` `schema_version=6`, chữ ký `save(cwd, state, expect_updated_at=_MISSING)`, tất cả CLI con hiện có
  - Chạm: `scripts/tdq_state.py`
  - Cần: `T1.1, T1.2`
  - Giao tiếp: Consumes: `tdq_lease.acquire_sidecar_lock` (`T1.1`), `tdq_config.load_config` (`T1.2`) | Produces: `default_state()["p0_runtime"]`, `save()` sidecar-locked, `reset_p0_breaker(cwd)` helper
  - Neo & Công cụ: Sửa `scripts/tdq_state.py` tại `default_state` (`L259-275`) và `save` (`L579-597`), `_atomic_write` (`L555-577`)
  - Trước → Sau: `save()` ghi tạm + `os.replace` không khóa sidecar (`overwriting anyway`) → Được bọc bởi `tdq_lease.acquire_sidecar_lock(state_path(cwd))` và mang nhánh tùy chọn `p0_runtime`
  - Tiêu chí chấp nhận (EARS): KHI hai luồng gọi `save()` hoặc `load()` nạp file `state.json` v6 cũ thiếu khóa `p0_runtime`, HỆ THỐNG PHẢI giữ khóa tuần tự qua `.lock` và tự điền mặc định `p0_runtime` mà giữ nguyên `schema_version == 6`
  - Logic cốt lõi: Nếu cờ `p0.lease_enabled` bật, bọc `save()` trong `with tdq_lease.acquire_sidecar_lock(state_path(cwd)):`; bổ sung `p0_runtime: {breaker, budget, quarantined_tools}` vào `default_state()`
  - Ca góc hiểm & Assert:
    - Ca hiểm: Tệp `state.json` cũ từ `dev` không có `p0_runtime` → `load()` giữ nguyên khóa cũ và backfill `p0_runtime["breaker"]["open"] is False`
    - Tiêu chí: `assert loaded["schema_version"] == 6 and loaded["p0_runtime"]["breaker"]["open"] is False`

- [x] **T2.4** (e14m) Dựng `scripts/mcp_policy.py` (hash SHA-256 baseline, chế độ cân bằng `3a`, CLI `approve` + `reset`, tự ghi log chuẩn `TDQ_LOG=0` không phụ thuộc `tdq_state`) + unit test `tests/test_mcp_policy.py` — Test: `py -3 -X utf8 -m pytest tests/test_mcp_policy.py`
  - Req: `§2#7, §2b mcp-policy, §3c#3, §4` · Ngoài phạm vi: `GIỮ NGUYÊN` bộ `tdq-lsp` qua thẳng fast-path, `0` import ngược từ `hooks/` hoặc `tdq_state`
  - Chạm: `scripts/mcp_policy.py`, `tests/test_mcp_policy.py` (tạo mới)
  - Sinh ra: `scripts/mcp_policy.py`, `tests/test_mcp_policy.py`
  - Cần: `T1.1, T1.2`
  - Giao tiếp: Consumes: `scripts/defaults/mcp-policy.default.json` (`T1.1`), `tdq_config` (`T1.2`), `tdq_lease` | Produces: `evaluate_tool_call(cwd, server, tool_name, schema_obj)`, CLI `approve <server> <tool>`, `approve_tool()` lưu SHA-256 vào `docs/tdq/mcp-policy.json`
  - Neo & Công cụ: Tạo mới 2 tệp; đối chiếu cấu hình từ `scripts/tdq_config.py` (`load_config`, `L174-191`)
  - Trước → Sau: Chưa có động cơ chấm rủi ro hay SHA-256 schema MCP → Có `mcp_policy.py` cân bằng `3a`: cho qua `read`/`tdq-lsp`/`trusted_servers`, chặn `READONLY` với tool `write`/`destructive` mới hoặc đổi SHA-256
  - Tiêu chí chấp nhận (EARS): KHI gọi `evaluate_tool_call` với tool `read` lạ → trả `"allow"`; KHI gọi với tool `write`/`destructive` lạ hoặc bị sửa mô tả schema → trả `"deny"` mã `READONLY` kèm gợi ý lệnh `approve`; chạy `approve` xong lần sau trả `"allow"` và `TDQ_LOG=0` ra `0B` stderr
  - Logic cốt lõi: Phân loại tier bằng bảng prefix/từ khóa (`read`/`get`/`list`/`search` vs `write`/`edit`/`delete`/`exec`); tính canonical SHA-256 từ JSON schema; khóa sidecar khi ghi `docs/tdq/mcp-policy.json`
  - Ca góc hiểm & Assert:
    - Ca hiểm: File `docs/tdq/mcp-policy.json` chứa JSON hỏng → log stderr khi `TDQ_LOG=1` và fail-closed chặn riêng `write`/`destructive`
    - Tiêu chí: `assert res_write["decision"] == "deny" and res_write["code"] == "READONLY" and res_read["decision"] == "allow"`

- [x] **T2.2** (e12m) Bổ sung hàng đợi 3 tầng + aging `OLDEST_DISPATCH_SHARE=4` + `blocked_by` + `idempotency_key` nối trên `chia_dot` & `detect_tcas_collision` trong `scripts/tdq_team.py` — Test: `py -3 -X utf8 -m pytest tests/test_tdq_queue.py`
  - Req: `§2#5, §2b team-queue, §3c#2, §5` · Ngoài phạm vi: `GIỮ NGUYÊN` `TRAN_SONG_SONG=4`, hành vi chia wave khi danh sách task không khai `priority`/`blocked_by`, giữ nguyên `detect_tcas_collision` (`TCAS`)
  - Chạm: `scripts/tdq_team.py`, `tests/test_tdq_queue.py`
  - Sinh ra: `tests/test_tdq_queue.py`
  - Cần: `T1.1, T2.1`
  - Giao tiếp: Consumes: `chia_dot`, `detect_tcas_collision` (`L594-685`), `tdq_lease`, `tdq_state` | Produces: `OLDEST_DISPATCH_SHARE`, `prioritize_tasks`, `dispatch_ready_waves` và bộ test `tests/test_tdq_queue.py`
  - Neo & Công cụ: Sửa `scripts/tdq_team.py` tại `chia_dot` (`L594-652`) và `detect_tcas_collision` (`L654-685`); tạo mới `tests/test_tdq_queue.py`
  - Trước → Sau: `tdq_team.chia_dot()` xếp tuyến tính, dễ bỏ đói task thấp và không lọc `blocked_by` → Có `prioritize_tasks` 3 tầng xen 1 task chờ lâu sau mỗi 4 lượt, lọc `blocked_by` và chống trùng `idempotency_key`
  - Tiêu chí chấp nhận (EARS): KHI hàng đợi có task `blocked_by` chưa `done` và `idempotency_key` trùng lặp, HỆ THỐNG PHẢI giữ task bị chặn lại ở vòng chờ, loại bản trùng khóa và đôn 1 task lâu tuổi nhất lên sau mỗi 4 lượt
  - Logic cốt lõi: Tách 3 hàng `high`/`normal`/`low`; vòng ghép lượt đếm `share`; lọc `done_ids` đối chiếu `blocked_by` rồi gọi tiếp `chia_dot()` và `detect_tcas_collision()`
  - Ca góc hiểm & Assert:
    - Ca hiểm: Toàn bộ task còn `blocked_by` chéo → trả danh sách ready rỗng `[]` không vòng lặp vô tận
    - Tiêu chí: `assert [t["id"] for t in out][:5] == ["h1", "h2", "h3", "h4", "low_old"]`

- [x] **T2.3** (e8m) Thêm bộ đếm ngân sách mềm `80%` và dừng cứng `hard_stop` (chỉ dừng khi khai trần) vào `scripts/tdq_timing.py` — Test: `py -3 -X utf8 -m pytest tests/test_tdq_timing_budget.py`
  - Req: `§2#6, §2b timing-budget, §3c#2` · Ngoài phạm vi: `GIỮ NGUYÊN` định dạng dòng `TIMING_REL`, `TELEMETRY_REL` (`L33-53`) và khóa `TDQ_LOG=0`
  - Chạm: `scripts/tdq_timing.py`, `tests/test_tdq_timing_budget.py`
  - Sinh ra: `tests/test_tdq_timing_budget.py`
  - Cần: `T1.2, T2.1`
  - Giao tiếp: Consumes: `TELEMETRY_REL`, `tdq_config.load_config()["p0"]["budget_caps"]` (`T1.2`), `tdq_state` | Produces: `check_budget_status(cwd, config)` trả `{"state": "ok"|"soft_warn"|"hard_stop", "ratio": float}`
  - Neo & Công cụ: Sửa `scripts/tdq_timing.py` (`TIMING_REL`, `TELEMETRY_REL`, `L33-53`); tạo mới `tests/test_tdq_timing_budget.py`
  - Trước → Sau: `tdq_timing.py` chỉ ghi telemetry chứ chưa chấm tỷ lệ ngân sách → Có `check_budget_status` cảnh báo ở `>= 80%` và bật `hard_stop` khi vượt trần khai báo
  - Tiêu chí chấp nhận (EARS): KHI `hard_stop_tokens` và `hard_stop_usd` đều là `null`, HỆ THỐNG PHẢI luôn trả `"state": "ok"`; KHI người dùng đặt trần trong `docs/tdq/config.json` và dùng tới `80%` / `100%`, PHẢI trả `"soft_warn"` / `"hard_stop"`
  - Logic cốt lõi: Tổng hợp `tokens` / `cost_usd` từ `telemetry.jsonl` (bỏ qua dòng lỗi format); tính `max(ratios)` đối chiếu ngưỡng `0.8` và `1.0`
  - Ca góc hiểm & Assert:
    - Ca hiểm: File `telemetry.jsonl` chưa tồn tại hoặc chứa dòng cắt cụt → tổng `0`, trả `{"state": "ok", "ratio": 0.0}` không văng lỗi
    - Tiêu chí: `assert res["state"] == "hard_stop" and res["ratio"] >= 1.0`

**Xong P2 khi**: `T2.1`–`T2.4` đều `[x]`, `tests/test_state.py`, `tests/test_ntfs_concurrency.py`, `tests/test_tdq_queue.py`, `tests/test_tdq_timing_budget.py`, `tests/test_mcp_policy.py` pass `100%`.

---

## P3 — Python Hooks, Rust `pre_tool_use.rs`, Manifests & Module nhánh `main` (Wave 3–4)

- [x] **T3.2** (e16m) Đồng bộ `handle_mcp_tool()` và `Circuit Breaker`/`Budget` guard trong `hooks/rust/tdq-dispatch/src/events/pre_tool_use.rs` (tái dụng mã `READONLY`, giữ tròn `23` AGY code) — Test: `cargo test --manifest-path hooks/rust/tdq-dispatch/Cargo.toml pre_tool_use`
  - Req: `§2#9, §2b rust-pretool, §3c#3, §5` · Ngoài phạm vi: `GIỮ NGUYÊN` fast-path allow `< 0.5 ms` cho `start_lsp` có `language_id` và mọi tool MCP đọc/đã duyệt
  - Chạm: `hooks/rust/tdq-dispatch/src/events/pre_tool_use.rs`
  - Cần: `T1.3, T2.4`
  - Giao tiếp: Consumes: `docs/tdq/mcp-policy.json` / `scripts/defaults/mcp-policy.default.json`, `docs/tdq/state.json` (`p0_runtime`), `docs/tdq/config.json` (`p0`) | Produces: `evaluate_non_lsp_mcp_rust()`, `check_p0_runtime_guard()`, unit tests mới trong `pre_tool_use::tests`
  - Neo & Công cụ: Sửa `hooks/rust/tdq-dispatch/src/events/pre_tool_use.rs` tại `handle_mcp_tool` (`L723-794`) và `handle_pre_tool_use` (`L797-830`)
  - Trước → Sau: Rust `handle_mcp_tool` mặc định `allow()` mọi non-LSP MCP, chưa đọc `mcp-policy` hay `p0_runtime.breaker` → Đọc nhanh JSON tĩnh trong `< 0.5 ms` và deny `READONLY` khớp `100%` quyết định của Python
  - Tiêu chí chấp nhận (EARS): KHI `handle_mcp_tool` nhận tool `write`/`destructive` mới chưa có trong baseline HOẶC `p0_runtime.breaker.open == true`, HỆ THỐNG PHẢI trả `Deny` với mã `READONLY` kèm lệnh CLI mở khóa; với tool `read` trả `Allow` trực tiếp không gọi subprocess Python
  - Logic cốt lõi: Phân loại tier tool MCP khớp chuẩn prefix với `mcp_policy.py`; đọc `docs/tdq/mcp-policy.json` fallback `scripts/defaults/mcp-policy.default.json`; kiểm cờ kill-switch `p0` trong config
  - Ca góc hiểm & Assert:
    - Ca hiểm: Không tìm thấy file policy hoặc `p0.mcp_quarantine_enabled == false` → xử lý đúng cờ balanced/kill-switch, không panic Rust hook
    - Tiêu chí: `assert!(matches!(outcome, RouteOutcome::Decided(ref d) if d.is_deny() && d.reason().contains("READONLY")))`

- [x] **T3.3** (e8m) Mở rộng matcher `PreToolUse` cho non-LSP MCP tại `hooks/hooks.json:76` và `tools/patches/agy_manifests.py:72` — Test: `py -3 -X utf8 -m pytest tests/test_rust_dispatch_parity.py`
  - Req: `§2#8, §2b host-manifests, §3` · Ngoài phạm vi: `GIỮ NGUYÊN` toàn bộ matcher `Edit`, `Bash`, `Search`, `PostToolUse` và cơ chế `tdq_hook_launcher.mjs`
  - Chạm: `hooks/hooks.json`, `tools/patches/agy_manifests.py`
  - Cần: `T2.4`
  - Giao tiếp: Consumes: `hooks/hooks.json:76`, `tools/patches/agy_manifests.py:67-76` (`generate_hooks_json`) | Produces: Matcher `mcp__.*|call_mcp_tool` (Claude/portable) và `mcp_.*|call_mcp_tool` (Antigravity `hooks.json`)
  - Neo & Công cụ: Sửa `hooks/hooks.json` (`L75-83`); sửa `tools/patches/agy_manifests.py` tại `generate_hooks_json` (`L65-76`)
  - Trước → Sau: Non-LSP MCP bị lọt hoàn toàn vì matcher chỉ bắt `lsp` → Mọi tool MCP kể cả bên thứ ba đều đi qua `PreToolUse` để kiểm tra `mcp_policy`
  - Tiêu chí chấp nhận (EARS): KHI tool MCP bên thứ ba được kích hoạt trên Claude Code hay Antigravity, HỆ THỐNG PHẢI định tuyến lời gọi vào `lsp_gate.py` / `tdq-dispatch.exe` thay vì bỏ qua
  - Logic cốt lõi: Thay chuỗi matcher dòng `76` (`hooks/hooks.json`) và phần tử `L72` (`pre_tool_matchers` trong `agy_manifests.py`)
  - Ca góc hiểm & Assert:
    - Ca hiểm: Tool nội bộ `mcp__lsp__*` vẫn phải khớp matcher mới để tiếp tục đi qua rào `start_lsp`/`blast_radius`
    - Tiêu chí: `assert re.match(matcher, "mcp__lsp__start_lsp") and re.match(matcher, "mcp__github__create_issue")`

- [x] **T3.1** (e14m) Nối `mcp_policy.evaluate_tool_call()` vào `hooks/scripts/lsp_gate.py:main()` (`op is None`) và gắn `Circuit Breaker`/`Budget` guard vào `edit_gate.py` + `bash_gate.py` — Test: `py -3 -X utf8 -m pytest tests/test_mcp_policy.py`
  - Req: `§2#8, §2b python-hooks, §3, §5` · Ngoài phạm vi: `GIỮ NGUYÊN` chuỗi neo `replace_exact` trong `tools/patches/agy_hooks.py` (`_patch_lsp_gate`, `_patch_edit_gate`, `_patch_bash_gate`); KHÔNG dùng `agy_pretooluse_gate.py`
  - Chạm: `hooks/scripts/lsp_gate.py`, `hooks/scripts/edit_gate.py`, `hooks/scripts/bash_gate.py`
  - Cần: `T2.1, T2.2, T2.3, T2.4`
  - Giao tiếp: Consumes: `mcp_policy.evaluate_tool_call` (`T2.4`), `tdq_state.load` (`T2.1`), `tdq_timing.check_budget_status` (`T2.3`) | Produces: Rào Python `PreToolUse` nhất quán cho non-LSP MCP, Breaker đang mở & Budget `hard_stop`
  - Neo & Công cụ: Sửa `hooks/scripts/lsp_gate.py` tại `main` (`L146-170`), `hooks/scripts/edit_gate.py` sau `main` (`L109-170`), `hooks/scripts/bash_gate.py` tại `eval_bash` & `main` (`L924-966`)
  - Trước → Sau: `lsp_gate.py` bỏ qua khi `op is None`; `edit_gate.py`/`bash_gate.py` chưa kiểm `p0_runtime.breaker` hay `budget_caps` → Đều kiểm và block mã `READONLY` kèm lệnh `approve` / `reset-breaker`
  - Tiêu chí chấp nhận (EARS): KHI non-LSP MCP `write` mới gọi qua `lsp_gate.py` HOẶC `p0_runtime.breaker.open == True` khi gọi `edit_gate.py`/`bash_gate.py`, HỆ THỐNG PHẢI trả block mã `READONLY`; mọi chuỗi neo trong `agy_hooks.py` vẫn khớp nguyên văn
  - Logic cốt lõi: Khi `op is None` trong `lsp_gate.py:main()`, gọi helper `_kiem_mcp_ngoai_lsp(cwd, payload, tool_name, tool_input)`; tại `edit_gate.py` & `bash_gate.py` gọi helper `_kiem_p0_breaker_va_ngan_sach(cwd, state)`
  - Ca góc hiểm & Assert:
    - Ca hiểm: Payload bị lỗi JSON hoặc rỗng → fail-open với cảnh báo `_log` giống `L153-165` của `lsp_gate.py` để không khóa nhầm công cụ
    - Tiêu chí: `assert blocked_non_lsp["decision"] == "block" and allow_read.returncode == 0`

- [x] **T3.4** (e6m) Bổ sung `"tdq_lease"` và `"mcp_policy"` vào `APPROVED_RUNTIME_MODULES` trong `tests/test_build_portable.py` — Test: `py -3 -X utf8 -m pytest tests/test_build_portable.py`
  - Req: `§2#9, §2b agy-bundle, §5` · Ngoài phạm vi: `GIỮ NGUYÊN` `RELEASE_EXCLUDE_SCRIPTS` đối với `skill_router.py` (`P1` mới gỡ)
  - Chạm: `tests/test_build_portable.py`
  - Cần: `T1.1, T2.4`
  - Giao tiếp: Consumes: `scripts/tdq_lease.py`, `scripts/mcp_policy.py` | Produces: Tập `APPROVED_RUNTIME_MODULES` hợp lệ cho nhánh `main` sạch
  - Neo & Công cụ: Sửa `tests/test_build_portable.py` tại `APPROVED_RUNTIME_MODULES` (`L37-45`)
  - Trước → Sau: `APPROVED_RUNTIME_MODULES` chưa có 2 module mới ở `P0` → Cho phép đóng gói `tdq_lease`, `mcp_policy` và giữ nguyên kiểm soát `main`
  - Tiêu chí chấp nhận (EARS): KHI chạy `tests/test_build_portable.py` và dry-run `--sinh-main`, HỆ THỐNG PHẢI giữ lại `tdq_lease.py`, `mcp_policy.py`, `scripts/defaults/mcp-policy.default.json` và exit `0`
  - Logic cốt lõi: Thêm 2 tên module mới vào bộ danh sách module runtime được duyệt
  - Ca góc hiểm & Assert:
    - Ca hiểm: Đảm bảo không đưa nhầm `tests/` hay `docs/` vào danh sách phát hành `main`
    - Tiêu chí: `assert {"tdq_lease", "mcp_policy"} <= APPROVED_RUNTIME_MODULES`

**Xong P3 khi**: `T3.1`–`T3.4` đều `[x]`, matcher non-LSP đã mở, Python hooks + Rust `pre_tool_use.rs` + `test_build_portable.py` pass `100%`.

---

## P4 — Biên dịch Rust, Sync Bundle & Kiểm Đóng gói (Wave 5)

- [x] **T4.1** (e12m) Biên dịch `tdq-dispatch.exe` (`cargo build --release`), chạy `tools/build_agy_plugin.py` sync vào `plugins/tdq-workflow-agy/`, kiểm `test_rust_dispatch_parity.py`, `i18n_check.py`, `token_budget.py` và `--sinh-main --dry-run` — Test: `py -3 -X utf8 tools/build_agy_plugin.py; py -3 -X utf8 -m pytest tests/test_rust_dispatch_parity.py; py -3 -X utf8 scripts/i18n_check.py; py -3 -X utf8 scripts/token_budget.py`
  - Req: `§2#9, §2b agy-bundle, §6 Q3-Q4` · Ngoài phạm vi: `GIỮ NGUYÊN` toàn bộ 42 skill gốc dưới `skills/` không tăng byte/token
  - Chạm: `plugins/tdq-workflow-agy/`
  - Cần: `T3.1, T3.2, T3.3, T3.4`
  - Giao tiếp: Consumes: `scripts/`, `hooks/`, `tools/build_agy_plugin.py`, `cargo build --release` | Produces: Bundle `plugins/tdq-workflow-agy/` đồng bộ mã mới và nhị phân Rust Windows mới nhất
  - Neo & Công cụ: Chạy `cargo build --release`, `tools/build_agy_plugin.py` (`_copy_upstream_assets`, `_verify_staged_bundle`, `build`), `tests/test_rust_dispatch_parity.py`, `scripts/i18n_check.py`, `scripts/token_budget.py`, `scripts/build_portable.py`
  - Trước → Sau: Nhị phân `.exe` và bundle `plugins/tdq-workflow-agy/` còn code cũ trước `P0` → Đồng bộ đầy đủ Python/Rust/defaults và xác nhận đủ `23` mã AGY + `0` lỗi ngôn ngữ/token
  - Tiêu chí chấp nhận (EARS): KHI chạy xong chuỗi đóng gói, `build_agy_plugin.py` PHẢI áp sạch mọi `_patch_*` mà không báo lỗi anchor, `test_rust_dispatch_parity.py` giữ tròn `23` mã và pass `100%`, `i18n_check.py` + `token_budget.py` exit `0`
  - Logic cốt lõi: Biên dịch Rust release trước để `build_agy_plugin.py` đóng gói nhị phân mới, sau đó chạy test parity và kiểm đóng gói cả hai nhánh
  - Ca góc hiểm & Assert:
    - Ca hiểm: Kiểm bundle sau build có chứa `scripts/defaults/mcp-policy.default.json` và `hooks.json` có matcher `mcp_.*|call_mcp_tool`
    - Tiêu chí: `assert os.path.isfile("plugins/tdq-workflow-agy/scripts/defaults/mcp-policy.default.json") and "mcp_.*|call_mcp_tool" in hooks_json`

**Xong P4 khi**: `T4.1` là `[x]`, `plugins/tdq-workflow-agy/` đồng bộ sạch, parity Python–Rust và các kiểm tra đa host exit `0`.

---

## P5 — Log & kiểm chứng bắt buộc mức `ultra` (Wave 6–7)

- [x] **T5.1** (e6m) Kiểm chứng Log service bật mặc định (`TDQ_LOG=1` có ISO timestamp stderr; `TDQ_LOG=0` ra `0B` stderr), `ruff check` sạch và `0` import ngược `scripts/` → `hooks/` — Test: `py -3 -X utf8 -m ruff check scripts/tdq_lease.py scripts/mcp_policy.py scripts/tdq_state.py scripts/tdq_team.py scripts/tdq_timing.py scripts/tdq_config.py hooks/scripts/lsp_gate.py hooks/scripts/edit_gate.py hooks/scripts/bash_gate.py`
  - Req: `§4, §5, §6 Q1, §6 Q5` · Ngoài phạm vi: Chỉ kiểm read-only và ghi bằng chứng JSON vào thư mục artifact của request
  - Chạm: `docs/tdq/artifacts/2026-11-25-1834-p0-runtime-safety-rust-parity/log-verify.json` (tạo mới)
  - Sinh ra: `docs/tdq/artifacts/2026-11-25-1834-p0-runtime-safety-rust-parity/log-verify.json`
  - Cần: `T4.1`
  - Giao tiếp: Consumes: Các module `scripts/*.py` và `hooks/scripts/*.py` đã hoàn tất ở `P1`–`P4` | Produces: `log-verify.json` xác nhận `TDQ_LOG=1/0` và AST `0` vi phạm import `hooks`
  - Neo & Công cụ: Chạy `ruff check`, AST import trong `scripts/*.py`, và đo `stderr` byte khi `TDQ_LOG=0` với `tdq_lease.py` & `mcp_policy.py`
  - Trước → Sau: Chưa đo đồng loạt độ sạch lint, AST layer và byte stderr sau mọi chỉnh sửa → Có bằng chứng JSON đo trực tiếp exit `0` và `0B` khi tắt log
  - Tiêu chí chấp nhận (EARS): KHI chạy các CLI mới dưới `TDQ_LOG=0`, luồng `stderr` PHẢI bằng đúng `0` bytes; `ruff check` exit `0` và `0` tệp trong `scripts/` import `hooks`
  - Logic cốt lõi: Chạy từng lệnh kiểm và ghi tóm tắt chỉ số vào `log-verify.json`
  - Ca góc hiểm & Assert:
    - Ca hiểm: Phân biệt chính xác `stderr` tắt hẳn vs vô tình in chuỗi xuống dòng `\n` khi `TDQ_LOG=0`
    - Tiêu chí: `assert lease_err0_bytes == 0 and mcp_err0_bytes == 0 and hooks_imports_in_scripts == 0`

- [x] **T5.2** (e14m) Nghiệm thu mức `ultra` (`Q1`–`Q7`): chạy `tools/run_full_verification.py`, `scripts/tdq_test.py tron-bo`, gọi `tdq-qc-tester` độc lập kiểm chéo đến khi `Verdict: PASS` (`DEFECTS: None`), viết `qc.md`, `report.md` và dựng Archify HTML `current` + Tailscale HTTP `200` — Test: `py -3 -X utf8 tools/run_full_verification.py; py -3 -X utf8 scripts/tdq_test.py tron-bo`
  - Req: `§2, §6 Q1-Q7` · Ngoài phạm vi: `0` chỉnh sửa ngoài `docs/tdq/` ở bước QC cuối; không commit hay đặt `phase=idle` nếu chưa hỏi người dùng
  - Chạm: `docs/tdq/qc/2026-11-25-1834-p0-runtime-safety-rust-parity.md`, `docs/tdq/reports/2026-11-25-1834-p0-runtime-safety-rust-parity.md`, `docs/tdq/reports/2026-11-25-1834-p0-runtime-safety-rust-parity.html` (tạo mới)
  - Sinh ra: `docs/tdq/qc/2026-11-25-1834-p0-runtime-safety-rust-parity.md`, `docs/tdq/reports/2026-11-25-1834-p0-runtime-safety-rust-parity.md`, `docs/tdq/reports/2026-11-25-1834-p0-runtime-safety-rust-parity.html`
  - Cần: `T5.1`
  - Giao tiếp: Consumes: Toàn bộ code `P0` + `log-verify.json` | Produces: Biên bản `qc.md`, báo cáo `report.md`, trang Archify HTML `current` + Tailscale HTTP `200`
  - Neo & Công cụ: Chạy full suite, `tdq-qc-tester` độc lập, `scripts/tdq_archify.py` (lệnh render và verify), `scripts/doc_lint.py`
  - Trước → Sau: Mới xanh từng phần rời → Có xác nhận độc lập từ `tdq-qc-tester` (`DEFECTS: None`), trọn bộ `tron-bo` PASS và báo cáo Archify `current` HTTP `200`
  - Tiêu chí chấp nhận (EARS): KHI hoàn tất `T5.2`, `7/7` cổng `Q1`–`Q7` PHẢI đạt `PASS`, `tdq-qc-tester` trả `Verdict: PASS`, `tdq_archify.py verify` trả `status=current` và Tailscale HTTP `200`
  - Logic cốt lõi: Chạy hồi quy toàn bộ, giao `tdq-qc-tester` kiểm độc lập mọi bài test và mã Rust/Python, sửa ngay vào `## QC vòng N — fix` nếu `FAIL`, cuối cùng hoàn thiện `qc.md` + `report.md` + re-render Archify HTML
  - Ca góc hiểm & Assert:
    - Ca hiểm: Sửa dù 1 dòng trong `report.md` sau khi dựng HTML → phải chạy lại `tdq_archify.py render` + `verify` ngay lập tức để manifest không `stale`
    - Tiêu chí: `assert verify_res["status"] == "current" and tailscale_http == 200 and qc_verdict == "PASS"`

**Xong P5 khi**: Đủ `Q1`–`Q7` `[x]`, `tdq-qc-tester` trả `Verdict: PASS`, `DEFECTS: None` và Archify HTML `status=current` + Tailscale HTTP `200`.

### QC vòng 1 — fix

- [x] **QC1.1** (e4m) Bổ sung `chrome-devtools`, `tavily-primary` vào `trusted_servers` và `select_` vào `read_prefixes` — Test: `py -3 -X utf8 -m pytest tests/test_hooks_dual_protocol.py tests/test_lsp_gate.py tests/test_mcp_policy.py`
  - Chạm: `scripts/defaults/mcp-policy.default.json`, `scripts/mcp_policy.py`
  - Sinh ra: Không có
  - Neo & Công cụ: `edit_file` vào `scripts/defaults/mcp-policy.default.json` và `_BUILTIN_DEFAULT_POLICY`
  - Trước → Sau: `chrome-devtools::select_page` bị chặn `READONLY` → Được phép ở chế độ cân bằng đồng bộ Rust `include_str!`
  - Logic cốt lõi: Thêm danh sách server tin cậy đi kèm vào baseline mặc định và tiền tố đọc `select_` để chế độ cân bằng cho phép thao tác kiểm thử trình duyệt
  - Tiêu chí & Assert: `test_ec16_lsp_gate_mcp_routing_and_empty_args` và `test_allow_chrome_devtools_tavily_other_lsp_va_lsp_query` PASS
- [x] **QC1.2** (e3m) Nạp tĩnh `import utf8_io` ở entrypoint `tdq_lease.py` và `mcp_policy.py` — Test: `py -3 -X utf8 -m pytest tests/test_utf8_io.py`
  - Chạm: `scripts/tdq_lease.py`, `scripts/mcp_policy.py`
  - Sinh ra: Không có
  - Neo & Công cụ: `edit_file` phần đầu tệp thay `importlib.import_module("utf8_io")`
  - Trước → Sau: `test_entrypoint_moi_file_deu_toi_duoc_utf8_io` báo thiếu 2 tệp → `0` entrypoint thiếu `utf8_io`
  - Logic cốt lõi: Đưa `import utf8_io` ra cấp module ngay sau thiết lập `sys.path` thay cho nạp động để kiểm AST entrypoint đạt chuẩn
  - Tiêu chí & Assert: `test_utf8_io.py` PASS toàn bộ
- [x] **QC1.3** (e4m) Chuẩn hóa kiểm tra `is_denied()` trong `lsp_gate.py` và bổ sung ngoại lệ thư viện `mcp_policy.py` vào `test_compliance_protocol.py` — Test: `py -3 -X utf8 -m pytest tests/test_compliance_protocol.py`
  - Chạm: `scripts/mcp_policy.py`, `hooks/scripts/lsp_gate.py`, `tests/test_compliance_protocol.py`
  - Sinh ra: Không có
  - Neo & Công cụ: `edit_file` thêm `is_denied()`, dùng tại `_kiem_mcp_ngoai_lsp` và thêm vào `deny_allowed`
  - Trước → Sau: Grep `"deny"` bắt trúng `lsp_gate.py` và `mcp_policy.py` → `0` hit sai luật hook
  - Logic cốt lõi: Tách hàm kiểm tra kết quả `is_denied()` thay cho chuỗi trần `"deny"` tại `lsp_gate.py` và ghi danh `mcp_policy.py` trong `deny_allowed`
  - Tiêu chí & Assert: `test_no_transcript_no_deny` PASS (`hits == []`)
- [x] **QC1.4** (e3m) Gộp 1 chỗ `import fcntl` có guard trong `tdq_lease.py` và cập nhật mốc báo cáo nền tảng — Test: `py -3 -X utf8 -m pytest tests/test_bao_cao_da_nen_tang.py`
  - Chạm: `scripts/tdq_lease.py`, `docs/tdq/report/2026-09-03-1648-kiem-da-nen-tang-host-tuong-thich.md`
  - Sinh ra: Không có
  - Neo & Công cụ: `edit_file` gộp `_flock_fd` trong `scripts/tdq_lease.py` và cập nhật dòng POSIX ở báo cáo
  - Trước → Sau: `import_chi_posix` trả `3 != 1` → Gộp còn `2` và khớp mốc báo cáo `2`
  - Logic cốt lõi: Gom `_lock_fd` và `_unlock_fd` về chung một nhánh POSIX có guard trong `_flock_fd` và cập nhật số lượng import POSIX lịch sử thành `2`
  - Tiêu chí & Assert: `test_so_import_posix_khop` PASS (`2 == 2`)
- [x] **QC1.5** (e5m) Tách tên `mcp_<server>_<tool>` nhận diện `trusted_servers` và `*_lsp_*` đồng bộ Python–Rust — Test: `py -3 -X utf8 -m pytest tests/test_lsp_gate.py tests/test_mcp_policy.py; cargo test --manifest-path hooks/rust/tdq-dispatch/Cargo.toml`
  - Chạm: `scripts/mcp_policy.py`, `hooks/scripts/lsp_gate.py`, `hooks/rust/tdq-dispatch/src/events/pre_tool_use.rs`, `tests/test_mcp_policy.py`
  - Sinh ra: Không có
  - Neo & Công cụ: `edit_file` thêm `split_eager_mcp_name()` và cập nhật `extract_mcp_server_and_tool()` theo longest-match `trusted_servers` + single-segment `_lsp_`
  - Trước → Sau: `mcp_other_lsp_start_lsp` bị chẻ sai thành `other::lsp_start_lsp` → Tách chuẩn `other_lsp::start_lsp`, chặn `mcp_evil_delete_lsp_entry`
  - Logic cốt lõi: Tách tiền tố theo thứ tự dài nhất khớp `trusted_servers`, chỉ nhận `_lsp_` khi phần đầu không chứa dấu gạch dưới để chặn giả mạo LSP
  - Tiêu chí & Assert: `test_lsp_gate.py`, `test_mcp_policy.py` và `cargo test` PASS 100%

### QC vòng 2 — fix

- [x] **QC2.1** (e6m) Siết kiểm tra lệnh mở khóa P0 theo token argv (`python/py + tdq_state.py/mcp_policy.py`) và chặn `&`, `\r`, `#`, `>`, `<` đồng bộ Python–Rust — Test: `py -3 -X utf8 -m pytest tests/test_bash_gate.py tests/test_rust_dispatch_parity.py; cargo test --manifest-path hooks/rust/tdq-dispatch/Cargo.toml`
  - Chạm: `hooks/scripts/bash_gate.py`, `hooks/rust/tdq-dispatch/src/events/pre_tool_use.rs`, `tests/test_bash_gate.py`
  - Sinh ra: Không có
  - Neo & Công cụ: `edit_file` trên `_is_p0_unlock_cmd()` và `is_p0_unlock_command()` thay khớp chuỗi con bằng phân tích token chuẩn + kiểm tra ký tự chuyển hướng/bình luận/nối lệnh
  - Trước → Sau: `&`, `\r`, `#`, `>` hay đối số giả lọt qua mở khóa khi Breaker mở → Bị chặn `TDQ:READONLY` trên cả Python và Rust
  - Logic cốt lõi: Tách token từng đoạn lệnh, chỉ cho phép `cd` thư mục hoặc trình thông dịch Python gọi thẳng `tdq_state.py reset-breaker` / `mcp_policy.py approve|reset`
  - Tiêu chí & Assert: Các ca `& rm`, `# reset-breaker`, `> evil.py`, `-c evil`, dummy args đều bị chặn `READONLY`; lệnh `reset-breaker` và `mcp_policy approve` hợp lệ vẫn qua
- [x] **QC2.2** (e6m) Bổ sung kiểm tra ngân sách trực tiếp từ `.tdq-agent-telemetry.jsonl` với `p0.budget_caps` trong Rust `check_p0_runtime_guard()` — Test: `cargo test --manifest-path hooks/rust/tdq-dispatch/Cargo.toml; py -3 -X utf8 -m pytest tests/test_rust_dispatch_parity.py`
  - Chạm: `hooks/rust/tdq-dispatch/src/events/pre_tool_use.rs`
  - Sinh ra: Không có
  - Neo & Công cụ: `edit_file` thêm `is_budget_hard_stop_reached()` vào `check_p0_runtime_guard()` khớp công thức `tdq_timing.check_budget_status()`
  - Trước → Sau: Rust chỉ đọc `state.json` `p0_runtime.budget.hard_stopped` và bỏ qua `.tdq-agent-telemetry.jsonl` → Chặn `[TDQ:READONLY]` khi tổng token hoặc USD vượt ngưỡng như Python
  - Logic cốt lõi: Cộng tổng token và chi phí USD từ `.tdq-agent-telemetry.jsonl` đối chiếu với `hard_stop_tokens` và `hard_stop_usd` theo công thức làm tròn 9 chữ số thập phân giống Python
  - Tiêu chí & Assert: Với `hard_stop_tokens=100` và telemetry `200`, Rust `edit_file` và `run_command` đều trả `Deny` `[TDQ:READONLY]`

---

## Cụm song song

Mỗi đợt `Wave 1`–`Wave 4` giữ `<= 4` task, tập `Chạm:` hoàn toàn không giao nhau và `0` va chạm `TCAS`:
- **Wave 1 (`P1`, `Worktree: branch`):** `T1.1` (`tdq_lease.py`, `mcp-policy.default.json`, `test_tdq_lease.py`) · `T1.2` (`tdq_config.py`) · `T1.3` (`lock.rs`).
- **Wave 2 (`P2a`, sau Wave 1):** `T2.1` (`tdq_state.py`) · `T2.4` (`mcp_policy.py`, `test_mcp_policy.py` — độc lập `tdq_state`).
- **Wave 3 (`P2b + P3a`, sau Wave 2):** `T2.2` (`tdq_team.py`, `test_tdq_queue.py`) · `T2.3` (`tdq_timing.py`, `test_tdq_timing_budget.py`) · `T3.2` (`pre_tool_use.rs`) · `T3.3` (`hooks/hooks.json`, `agy_manifests.py`).
- **Wave 4 (`P3b`, sau Wave 3):** `T3.1` (`hooks/scripts/{lsp,edit,bash}_gate.py`) · `T3.4` (`test_build_portable.py`).
- **Wave 5–7 (tuần tự trên Leader):** `T4.1` (`build_agy_plugin.py` + `parity`) → `T5.1` → `T5.2` (cộng `tdq-qc-tester` độc lập).

## Luật file nóng (một file, nhiều task chạm)

Không có file nguồn nào bị từ `2` task trở lên cùng sửa trong toàn bộ `P1`–`P5`: hub `scripts/tdq_state.py` thuộc duy nhất `T2.1`, `scripts/tdq_config.py` thuộc duy nhất `T1.2`, `hooks/rust/tdq-dispatch/src/events/pre_tool_use.rs` thuộc duy nhất `T3.2`, và thư mục đầu ra `plugins/tdq-workflow-agy/` chỉ được dựng tập trung tại `T4.1`.

## Definition of Done

Trỏ về §6 của spec `2026-11-25-1834-p0-runtime-safety-rust-parity.md` (`muc_qc=ultra`):

- [x] Q1 Unit test mới (`T1.1`, `T2.2`, `T2.3`, `T2.4`) & `TDQ_LOG=1/0` (`0B` stderr) — `py -3 -X utf8 -m pytest tests/test_tdq_lease.py tests/test_tdq_queue.py tests/test_tdq_timing_budget.py tests/test_mcp_policy.py`
- [x] Q2 Khóa NTFS & tương thích `schema_version=6` ở `tdq_state` — `py -3 -X utf8 -m pytest tests/test_state.py tests/test_ntfs_concurrency.py`
- [x] Q3 Rust build/test & Parity Python–Rust (`23` mã cổng AGY giữ nguyên) — `cargo build --release --manifest-path hooks/rust/tdq-dispatch/Cargo.toml; cargo test --manifest-path hooks/rust/tdq-dispatch/Cargo.toml; py -3 -X utf8 -m pytest tests/test_rust_dispatch_parity.py`
- [x] Q4 Đóng gói đa host (`build_agy_plugin.py`, `--sinh-main --dry-run`, `i18n`, `token`) — `py -3 -X utf8 tools/build_agy_plugin.py; py -3 -X utf8 -m pytest tests/test_build_portable.py; py -3 -X utf8 scripts/build_portable.py --sinh-main --dry-run; py -3 -X utf8 scripts/i18n_check.py; py -3 -X utf8 scripts/token_budget.py`
- [x] Q5 Hồi quy toàn dự án, lint & luật import `scripts/` không gọi `hooks/` — `py -3 -X utf8 tools/run_full_verification.py; py -3 -X utf8 scripts/tdq_test.py tron-bo`
- [x] Q6 Thẩm định độc lập `ultra` (`tdq-qc-tester`) — subagent `tdq-qc-tester` kiểm chéo toàn bộ code Python/Rust mới & xuất `docs/tdq/qc/2026-11-25-1834-p0-runtime-safety-rust-parity.md` với `Verdict: PASS`, `DEFECTS: None`
- [x] Q7 Báo cáo, working log & Archify HTML (`current`, Tailscale HTTP `200`) — `py -3 -X utf8 scripts/tdq_archify.py verify --document docs/tdq/reports/2026-11-25-1834-p0-runtime-safety-rust-parity.md --manifest docs/tdq/reports/2026-11-25-1834-p0-runtime-safety-rust-parity.manifest.json`
