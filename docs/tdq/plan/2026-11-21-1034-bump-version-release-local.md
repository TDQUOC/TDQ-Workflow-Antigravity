# PLAN — Bump Version `0.103.0`, Build 3-OS Rust, Release `main` & Cập nhật Antigravity Local

Ngày: 2026-11-21 · Spec: ../spec/2026-11-21-1034-bump-version-release-local.md (bản 1.0, ĐÃ DUYỆT) · Lane: full
Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md
Mode thực thi: main — `tdq_bench.py simulate` (`--he-so-agent 1.5`) chấm `main` thắng `0.1` phút (`18.3` vs `18.4` phút trên `9` task / `6` wave do chuỗi phụ thuộc tuần tự `P3→P4→P5` và thao tác SSH/user-level cần kiểm soát chặt) (ĐỀ XUẤT, user chốt lúc duyệt)
Trạng thái plan: HOÀN THÀNH

> **Tóm tắt dễ hiểu:** Kế hoạch chia thành `5` đợt tuần tự: trước hết tách bớt mục cũ để `CHANGELOG.md` dưới `500` dòng và nâng mọi tệp phiên bản lên `0.103.0`; tiếp theo biên dịch lại đủ `3` nhị phân Rust trên Windows, Ubuntu (`ubuntu-100-95`) và macOS (`mbair`) kèm test mô phỏng và dọn sạch `100%` máy SSH; sau đó build gói `plugins/tdq-workflow-agy/`, chạy kiểm định `full` toàn repo; cuối cùng cài cập nhật cho Antigravity trên máy (`~/.gemini/` và `GEMINI.md`) rồi sau khi gộp `dev` sẽ xuất bản nhánh `main` sạch kèm tag `v0.103.0` ở local.

## Mục lục

- Phân bổ Model & Effort
- Quy tắc thi hành (áp cho mọi task)
- Thiết kế Trước vs Sau
- Ràng buộc toàn cục & Bản đồ Sở hữu Hợp đồng (Ownership Map)
- P1 — Đồng bộ Version `0.103.0`, Tách Archive & Tài liệu Phát hành
- P2 — Biên dịch Rust 3 Nền tảng (Windows + SSH Linux/macOS) & Dọn sạch
- P3 — Nâng Compiler AGY & Đóng gói `plugins/tdq-workflow-agy/`
- P4 — Log & Test Bắt buộc + Kiểm định Toàn repo
- P5 — Cài đặt Antigravity User-Level & Xuất bản `main` + Tag `v0.103.0`
- Cụm song song
- Luật file nóng (một file, nhiều task chạm)
- Definition of Done

## Phân bổ Model & Effort
<!-- i18n-allow: canonical model/effort plan allocation table -->
> User được quyền đổi `type model` hoặc `effort` lúc duyệt plan. Thang model: [subagent-tuning.md](../../tdq-conventions/references/subagent-tuning.md).

| Pha | Vai trò | Model | Effort | Ghi chú |
|---|---|---|---|---|
| `implement` | Leader / `tdq-implementer` | `inherit` (`gemini-4-neon`) | `high` | Có thao tác SSH 2 máy Linux/Mac, Rust build và cài user-level `~/.gemini/` cần độ chính xác cao |
| `qc` | `tdq-qc-tester` | `inherit` (`gemini-4-neon`) | `high` | Đối soát độc lập `Q1`–`Q7`, xác minh `0` tàn dư SSH và bản live `~/.gemini/` |
| `report` | Leader | `inherit` (`gemini-4-neon`) | `high` | Xuất cặp report `.md` + Archify HTML (Tailscale HTTP 200) theo văn phong ngắn gọn dễ hiểu |

## Quy tắc thi hành (áp cho mọi task)
1. Thứ tự phase là thứ tự phụ thuộc — không đảo.
2. Mỗi task: đánh `[~]` khi bắt đầu → chạy kiểm đỏ trước (hoặc xác nhận điểm lệch hiện tại) → thực hiện → kiểm xanh → đổi sang `[x]` NGAY vào file này.
3. Mỗi bước: `py -3 -X utf8 scripts/tdq_test.py vung-cham`; trọn bộ `tron-bo` chạy tại cổng QC (`P4`).
4. Lệnh nào chạm state của workflow trong test phải đặt `TDQ_PROJECT_DIR=<thư mục tạm>`.
5. QC FAIL → thêm task fix `QCn.x` vào file này (không cần duyệt lại), loop đến khi pass `0 failed`.
6. Không tự commit hoặc `git push` cho đến khi người dùng yêu cầu; `git push` nằm ngoài phạm vi (`3a`).
7. Tuân thủ `6` mã cấm cơ học (ANTI-1 Fake Red, ANTI-2 Blind Assertion, ANTI-3 Dirty State Git, ANTI-4 Late Tick, ANTI-5 Raw Dump, ANTI-6 Broad Area).

## Thiết kế Trước vs Sau
| Khía cạnh | Hiện trạng (Trước) | Thiết kế mới (Sau) |
|---|---|---|
| Phiên bản & Changelog | Manifests `0.102.0`, `CHANGELOG.md` `480/500` dòng chưa ghi 3 đợt mới | Khớp `0.103.0`, tách `0.61.0`–`0.60.0` sang `archive-3`, `CHANGELOG.md < 500` dòng |
| Nhị phân Rust 3 OS | `Cargo.toml` `0.101.0`; binary Linux/Mac mốc `11/19`; dư `/home/ubuntu/tdq-dispatch` | Build mới `0.103.0` trên Windows, Ubuntu (`musl`), macOS (`ARM64`), dọn sạch `100%` SSH |
| Release `main` & Local AGY | `main` `v0.100.0`; `~/.gemini/` `0.101.0` & thiếu quy tắc `1145` | `main` + tag `v0.103.0` local; `~/.gemini/` `0.103.0` giữ Caveman/RTK + `GEMINI.md` đồng bộ |

*Đối chiếu sơ đồ kiến trúc:* Tham chiếu Archify preview đã duyệt tại [2026-11-21-1034-bump-version-release-local-preview.html](../spec/2026-11-21-1034-bump-version-release-local-preview.html) và manifest `current` tại [2026-11-21-1034-bump-version-release-local-preview.manifest.json](../spec/2026-11-21-1034-bump-version-release-local-preview.manifest.json).

## Ràng buộc toàn cục & Bản đồ Sở hữu Hợp đồng (Ownership Map)

- Ngôn ngữ: English comments/CLI trong mã nguồn · `utf8_io` / `encoding="utf-8"` · `TDQ_LOG=0` tắt log · hàm mới `<= 50` dòng (`cyc <= 10`, `cog <= 15`) · `GIỮ NGUYÊN` chữ ký cũ của mọi hàm hiện có trong `tools/` và `scripts/`.

| Hợp đồng / Ký hiệu (§3c) | File & Task sở hữu | Task / File tiêu thụ |
|---|---|---|
| `version = "0.103.0"` (manifests + changelog head) | `.claude-plugin/plugin.json`, `.codex-plugin/plugin.json`, `CHANGELOG.md` (`T1.1`) | `tests/test_docs_consistency.py`, `tests/test_adapter_host.py`, `scripts/build_portable.py:plugin_version` (`T5.2`) |
| `tdq-dispatch` crate `0.103.0` & 3 native binaries | `hooks/rust/tdq-dispatch/Cargo.toml` (`T2.1`), `plugins/tdq-workflow-agy/bin/tdq-dispatch*` (`T2.1`–`T2.3`) | `tools/build_agy_plugin.py:_stage_rust_binaries` (`T3.1`), `tests/test_remote_*_simulation.py` (`T2.2`, `T2.3`) |
| `PLUGIN_VERSION = "0.103.0"` & compiled AGY bundle | `tools/patches/agy_manifests.py`, `tools/build_agy_plugin.py` (`T3.1`) | `plugins/tdq-workflow-agy/{plugin.json,manifest.json,README.md}`, `install.py` (`T5.1`) |
| `ghim_huong_dan_tool` + `install.py` AGY user-level | `C:\Users\admin\.gemini\config\plugins\tdq-workflow-agy`, `C:\Users\admin\.gemini\GEMINI.md` (`T5.1`) | `agy plugin list`, `agy plugin validate` (`T5.1`, `Q7`) |
| `sinh_nhanh_main` + annotated tag `v0.103.0` | Nhánh `main`, tag `v0.103.0` (`T5.2`) | `git show main:.claude-plugin/plugin.json` (`Q6`) |

## P1 — Đồng bộ Version `0.103.0`, Tách Archive & Tài liệu Phát hành

- [x] **T1.1** (e6m) Tách `0.61.0`–`0.60.0` từ `CHANGELOG.md` sang đầu `docs/CHANGELOG-archive-3.md`, chèn mục `## 0.103.0 — 2026-11-21` tổng hợp 3 đợt nâng cấp sau `0.102.0` (`4 trụ cột agent`, `investigate V2`, `trình bày ngắn gọn`), và nâng version `0.103.0` đồng bộ trên `.claude-plugin/plugin.json`, `.codex-plugin/plugin.json`, `README.md` (kèm số thực `scripts/` `73`, `tests/` `4.602 passed`), `UPSTREAM-TRACE.md` — Test: `py -3 -X utf8 -m pytest tests/test_docs_consistency.py tests/test_adapter_host.py -q && py -3 -X utf8 scripts/doc_lint.py CHANGELOG.md docs/CHANGELOG-archive-3.md` (`22 passed, 24 subtests`; `doc_lint` `0` lỗi; `CHANGELOG.md` `461` dòng)
  - Req: `§1, §2#1, §3c B1` · Ngoài phạm vi: `GIỮ NGUYÊN` trường `description` khớp giữa Claude và Codex manifest, giữ `skills/` (`11`), `agents/` (`8`), `hooks/` (`17`) khớp `test_docs_consistency.py`
  - Chạm: `.claude-plugin/plugin.json`, `.codex-plugin/plugin.json`, `CHANGELOG.md`, `docs/CHANGELOG-archive-3.md`, `README.md`, `UPSTREAM-TRACE.md`
  - Cần: Không
  - Giao tiếp: Consumes: báo cáo 3 đợt (`1230`, `0217`, `0917`) | Produces: `version == "0.103.0"` trên manifest và đỉnh `CHANGELOG.md`
  - Neo & Công cụ: `Edit` tại `.claude-plugin/plugin.json:4`, `.codex-plugin/plugin.json:3`, `CHANGELOG.md:5,449-480`, `docs/CHANGELOG-archive-3.md:1-10`, `README.md:3-4,144,234,237`, `UPSTREAM-TRACE.md:24`
  - Trước → Sau: Manifest `0.102.0` & `CHANGELOG.md` `480` dòng → `0.103.0` & `CHANGELOG.md` `<= 495` dòng
  - Tiêu chí chấp nhận (EARS): KHI chạy `test_docs_consistency.py`, `test_adapter_host.py` và `doc_lint.py CHANGELOG.md docs/CHANGELOG-archive-3.md`, HỆ THỐNG PHẢI trả `0 failed` và `0 violation(s)` với tổng dòng `CHANGELOG.md <= 500`
  - Logic cốt lõi: Cắt nguyên văn 2 mục `0.61.0`–`0.60.0` sang `docs/CHANGELOG-archive-3.md` trước, cập nhật chân trang archive ở `CHANGELOG.md`, rồi chèn mục `## 0.103.0 — 2026-11-21` và bump version đồng loạt
  - Ca góc hiểm & Assert: Kiểm không rớt ký tự UTF-8, `heads[0] == "0.103.0"`, `line_count(CHANGELOG.md) <= 500`

**Xong P1 khi**: `test_docs_consistency.py`, `test_adapter_host.py` PASS `0 failed` và `doc_lint.py CHANGELOG.md docs/CHANGELOG-archive-3.md` exit `0`.

## P2 — Biên dịch Rust 3 Nền tảng (Windows + SSH Linux/macOS) & Dọn sạch

- [x] **T2.1** (e6m) Nâng `hooks/rust/tdq-dispatch/Cargo.toml` lên `version = "0.103.0"`, chạy `cargo test`, `cargo clippy --all-targets -- -D warnings`, biên dịch `cargo build --release` (`+crt-static`) trên Windows và cập nhật `plugins/tdq-workflow-agy/bin/tdq-dispatch.exe` — Test: `cargo test --manifest-path hooks/rust/tdq-dispatch/Cargo.toml && cargo clippy --manifest-path hooks/rust/tdq-dispatch/Cargo.toml --all-targets -- -D warnings` (`29 passed`, `0` clippy warnings, `tdq-dispatch.exe` `1,967,104` B SHA256 `BAB071B...`)
  - Req: `§1, §2#2, §3c B2` · Ngoài phạm vi: `GIỮ NGUYÊN` toàn bộ hành vi 6 sự kiện hook, `command_parser.rs`, `scoped-write` 5 lớp và `.cargo/config.toml` `+crt-static`
  - Chạm: `hooks/rust/tdq-dispatch/Cargo.toml`, `hooks/rust/tdq-dispatch/Cargo.lock`, `plugins/tdq-workflow-agy/bin/tdq-dispatch.exe`
  - Cần: Không
  - Giao tiếp: Consumes: crate `hooks/rust/tdq-dispatch/` | Produces: Windows PE `tdq-dispatch.exe` phiên bản `0.103.0` (`env!("CARGO_PKG_VERSION")`)
  - Neo & Công cụ: `Edit` tại `hooks/rust/tdq-dispatch/Cargo.toml:3`; `run_command` chạy `cargo test`, `cargo clippy`, `cargo build --release`
  - Trước → Sau: `Cargo.toml` `0.101.0` → `0.103.0` kèm `tdq-dispatch.exe` biên dịch mới
  - Tiêu chí chấp nhận (EARS): KHI chạy `cargo test`, `cargo clippy --all-targets -- -D warnings` và `cargo build --release`, HỆ THỐNG PHẢI trả `0 failed`, `0 warnings`, file `target/release/tdq-dispatch.exe` có magic header `MZ`
  - Logic cốt lõi: Đổi `version = "0.103.0"`, cập nhật `Cargo.lock` khi `cargo test`, build bản release tĩnh CRT, chép vào `plugins/tdq-workflow-agy/bin/tdq-dispatch.exe`
  - Ca góc hiểm & Assert: Không gọi `tdq-dispatch.exe --version` thiếu EOF stdin; kiểm `verify_binary_magic(..., "windows") == True` và `test_version()` trong `src/lib.rs` trả `"0.103.0"`

- [x] **T2.2** (e12m) Đóng gói nguồn `hooks/rust/tdq-dispatch` (loại `target/`) gửi qua SSH lên `ubuntu-100-95` trong `/tmp/tdq-build-linux-<id>`, chạy `cargo test` và `cargo build --release --target x86_64-unknown-linux-musl`, tải về `plugins/tdq-workflow-agy/bin/tdq-dispatch-linux-x86_64`, chạy `test_remote_linux_simulation.py`, rồi dọn sạch tuyệt đối `/tmp/tdq*`, `/tmp/tdq_dispatch.tar.gz`, `/home/ubuntu/tdq-dispatch` và hậu kiểm `0` tệp sót — Test: `py -3 -X utf8 -m pytest tests/test_remote_linux_simulation.py -q` (`29` Cargo tests PASS, `1 passed in 2.04s`, `2,422,392` B SHA256 `1BAFFFB...`, `COUNT=0`)
  - Req: `§1, §2#2, §2#3, §3c B2` · Ngoài phạm vi: `GIỮ NGUYÊN` các tệp hệ thống, rustup toolchain và cấu hình khác của user `ubuntu` trên `ubuntu-100-95`
  - Chạm: `plugins/tdq-workflow-agy/bin/tdq-dispatch-linux-x86_64`
  - Cần: `T2.1`
  - Giao tiếp: Consumes: `hooks/rust/tdq-dispatch/{Cargo.toml,Cargo.lock,.cargo,src}` (`0.103.0`) | Produces: ELF x86-64 static-pie `tdq-dispatch-linux-x86_64` + xác nhận sạch `ubuntu-100-95`
  - Neo & Công cụ: `run_command` dùng Python tar stream + `ssh`/`scp` tới `ubuntu-100-95` và `pytest tests/test_remote_linux_simulation.py`
  - Trước → Sau: Binary Linux mốc `11/19` (`0.101.0`) và tồn dư `/home/ubuntu/tdq-dispatch`, `/tmp/tdq_dispatch.tar.gz` → binary `0.103.0` mới và `0` tàn dư
  - Tiêu chí chấp nhận (EARS): KHI hoàn thành build/test/cleanup trên `ubuntu-100-95`, HỆ THỐNG PHẢI đạt `cargo test` `0 failed`, `test_remote_linux_simulation.py` `1 passed` (`hot_median_ms < 50.0`), magic header `\x7fELF`, và `ssh ubuntu-100-95 "ls -d /tmp/tdq* /tmp/tdq_dispatch* ~/tdq* 2>/dev/null | wc -l"` trả `0`
  - Logic cốt lõi: Gửi tarball qua `ssh`, chạy `source ~/.cargo/env && cargo test && cargo build --release --target x86_64-unknown-linux-musl`, tải binary về `plugins/tdq-workflow-agy/bin/`, luôn dọn sạch `/tmp/tdq*`, `/tmp/tdq_dispatch.tar.gz`, `/home/ubuntu/tdq-dispatch` trong khối dọn chắc chắn, chạy simulation rồi hậu kiểm lại `ls`
  - Ca góc hiểm & Assert: Chạy dọn cả khi build/test lỗi; đối chiếu `sha256` binary mới khác binary cũ `11/19`

- [x] **T2.3** (e12m) Đóng gói nguồn `hooks/rust/tdq-dispatch` (loại `target/`) gửi qua SSH lên `mbair` trong `/tmp/tdq-build-mac-<id>`, chạy `cargo test` và `cargo build --release --target aarch64-apple-darwin`, tải về `plugins/tdq-workflow-agy/bin/tdq-dispatch-darwin-arm64`, chạy `test_remote_mac_simulation.py`, rồi dọn sạch tuyệt đối `/tmp/tdq*`, `~/tdq*` và hậu kiểm `0` tệp sót — Test: `py -3 -X utf8 -m pytest tests/test_remote_mac_simulation.py -q` (`29` Cargo tests PASS, `1 passed in 2.26s`, `1,845,840` B SHA256 `90CFDE7...`, `COUNT=0`)
  - Req: `§1, §2#2, §2#3, §3c B2` · Ngoài phạm vi: `GIỮ NGUYÊN` toàn bộ tệp hệ thống, Xcode CLT và rustup toolchain trên `mbair`
  - Chạm: `plugins/tdq-workflow-agy/bin/tdq-dispatch-darwin-arm64`
  - Cần: `T2.1`
  - Giao tiếp: Consumes: `hooks/rust/tdq-dispatch/{Cargo.toml,Cargo.lock,.cargo,src}` (`0.103.0`) | Produces: Mach-O ARM64 `tdq-dispatch-darwin-arm64` + xác nhận sạch `mbair`
  - Neo & Công cụ: `run_command` dùng Python tar stream + `ssh`/`scp` tới `mbair` và `pytest tests/test_remote_mac_simulation.py`
  - Trước → Sau: Binary macOS mốc `11/19` (`0.101.0`) → binary `0.103.0` mới và `0` tàn dư trên `mbair`
  - Tiêu chí chấp nhận (EARS): KHI hoàn thành build/test/cleanup trên `mbair`, HỆ THỐNG PHẢI đạt `cargo test` `0 failed`, `test_remote_mac_simulation.py` `1 passed` (`hot_median_ms < 50.0`), magic header Mach-O ARM64, và `ssh mbair "ls -d /tmp/tdq* ~/tdq* 2>/dev/null | wc -l"` trả `0`
  - Logic cốt lõi: Gửi tarball qua `ssh`, chạy `source ~/.cargo/env && cargo test && cargo build --release --target aarch64-apple-darwin`, tải binary về `plugins/tdq-workflow-agy/bin/`, luôn dọn sạch `/tmp/tdq*` và `~/tdq*`, chạy simulation rồi hậu kiểm lại `ls`
  - Ca góc hiểm & Assert: Xử lý shell `zsh` trên macOS (không nổ `no matches found` khi kiểm `ls`); đối chiếu `sha256` binary mới khác bản `11/19`

**Xong P2 khi**: Cả 3 nhị phân `Windows`/`Linux musl`/`macOS ARM64` phiên bản `0.103.0` đều PASS `cargo test` + simulation test và cả 2 máy SSH báo `0` tàn dư.

## P3 — Nâng Compiler AGY & Đóng gói `plugins/tdq-workflow-agy/`

- [x] **T3.1** (e8m) Nâng `PLUGIN_VERSION = "0.103.0"` trong `tools/patches/agy_manifests.py:11` và chuỗi phiên bản tại `tools/patches/__init__.py:1`, `tools/build_agy_plugin.py:2,275`, chạy `build_agy_plugin.py --upstream .` biên dịch lại `plugins/tdq-workflow-agy/`, bổ sung test khóa đồng bộ phiên bản plugin AGY khớp `.claude-plugin/plugin.json` vào `tests/test_agy_plugin_validate.py` và xác minh tính khả chuyển — Test: `py -3 -X utf8 -m pytest tests/test_agy_plugin_validate.py tests/test_rust_dispatch_parity.py tests/test_rust_lock_safety.py -q && agy.EXE plugin validate plugins/tdq-workflow-agy --strict --json` (`55 passed in 71.56s`, `agy validate` `findings: []`, `token_budget` `0` lỗi)
  - Dùng: `tdq-checkportable`
  - Để: kiểm tra tính nguyên vẹn & khả chuyển của gói plugin sau biên dịch, nạp trước bước kiểm cuối
  - Ra: `plugins/tdq-workflow-agy/manifest.json` và `plugins/tdq-workflow-agy/plugin.json` phiên bản `0.103.0`
  - Kiểm: `py -3 -X utf8 scripts/tdq_checkportable.py --root plugins/tdq-workflow-agy check` hoặc `agy.EXE plugin validate plugins/tdq-workflow-agy --strict --json` trả `findings == []`
  - Không dùng cho: ghi đè trực tiếp vào `~/.gemini/` (để riêng ở `T5.1`)
  - Req: `§1, §2#4, §3c B3` · Ngoài phạm vi: `GIỮ NGUYÊN` toàn bộ chữ ký hàm `generate_plugin_json`, `generate_manifest_and_readme`, `_stage_rust_binaries`, `build`, `main`
  - Chạm: `tools/patches/agy_manifests.py`, `tools/patches/__init__.py`, `tools/build_agy_plugin.py`, `plugins/tdq-workflow-agy/plugin.json`, `plugins/tdq-workflow-agy/manifest.json`, `plugins/tdq-workflow-agy/README.md`, `tests/test_agy_plugin_validate.py`
  - Cần: `T1.1`, `T2.2`, `T2.3`
  - Giao tiếp: Consumes: `plugins/tdq-workflow-agy/bin/tdq-dispatch*` (`T2.1`–`T2.3`) và `.claude-plugin/plugin.json` (`T1.1`) | Produces: gói `plugins/tdq-workflow-agy/` (`0.103.0`) đạt `agy plugin validate --strict`
  - Neo & Công cụ: `Edit` tại `tools/patches/agy_manifests.py:11`, `tools/patches/__init__.py:1`, `tools/build_agy_plugin.py:2,275`, cuối `tests/test_agy_plugin_validate.py:241`; chạy `tools/build_agy_plugin.py --upstream .`
  - Trước → Sau: Compiler & bundle `0.102.0` → `0.103.0` với đủ 3 nhị phân mới và test khóa chống lệch version
  - Tiêu chí chấp nhận (EARS): KHI chạy `tools/build_agy_plugin.py --upstream .` và `pytest tests/test_agy_plugin_validate.py`, HỆ THỐNG PHẢI trả `"status": "OK"`, `findings == []`, `plugin.json["version"] == manifest.json["version"] == "0.103.0"` và `3` kích thước binary riêng biệt hợp lệ
  - Logic cốt lõi: Viết test đỏ kiểm version `plugins/tdq-workflow-agy/{plugin.json,manifest.json}` khớp `.claude-plugin/plugin.json` trước → nâng `PLUGIN_VERSION` & docstrings → bảo đảm không có `hooks/rust/tdq-dispatch/prebuilt/` cũ chen ngang → chạy `build_agy_plugin.py --upstream .` → chạy xanh test + `agy plugin validate --strict`
  - Ca góc hiểm & Assert: `assert pjson["version"] == claude_ver and mjson["version"] == claude_ver`; kiểm `token_budget.py --kiem` `0` vi phạm

**Xong P3 khi**: `plugins/tdq-workflow-agy/` phiên bản `0.103.0` đạt `agy plugin validate --strict` (`findings == []`) và toàn bộ `test_agy_plugin_validate.py`, `test_rust_dispatch_parity.py`, `test_rust_lock_safety.py` PASS.

## P4 — Log & Test Bắt buộc + Kiểm định Toàn repo

- [x] **T4.1** (e4m) Kiểm chứng log service bật mặc định có timestamp (`TDQ_LOG=1`) và im lặng hoàn toàn (`TDQ_LOG=0`) trên `tools/build_agy_plugin.py`, `scripts/build_portable.py --sinh-main --nguon HEAD --dry-run` và `tdq-dispatch.exe` — Test: `py -3 -X utf8 -m pytest tests/test_build_portable.py tests/test_rust_dispatch_parity.py -q` (`84 passed, 4 subtests in 76.03s`; `TDQ_LOG=0` `STDERR_LEN=0`)
  - Req: `§4` · Ngoài phạm vi: `GIỮ NGUYÊN` toàn bộ mã nguồn runtime (thuần xác minh hành vi log đang có, không sửa thêm script)
  - Chạm: `docs/tdq/qc/2026-11-21-1034-bump-version-release-local.md`
  - Cần: `T3.1`
  - Giao tiếp: Consumes: `tools/build_agy_plugin.py`, `scripts/build_portable.py`, `plugins/tdq-workflow-agy/bin/tdq-dispatch.exe` | Produces: bằng chứng kiểm `TDQ_LOG=1` / `TDQ_LOG=0` ghi vào biên bản QC
  - Neo & Công cụ: `run_command` chạy thử với `TDQ_LOG=1` và `TDQ_LOG=0`; `Write` tạo mới `docs/tdq/qc/2026-11-21-1034-bump-version-release-local.md`
  - Trước → Sau: Chưa có biên bản kiểm log cho bản `0.103.0` → có đủ bằng chứng `TDQ_LOG=1` (có timestamp ISO) và `TDQ_LOG=0` (`stderr == ""`)
  - Tiêu chí chấp nhận (EARS): KHI chạy `build_portable.py --sinh-main --nguon HEAD --dry-run` với `TDQ_LOG=0`, HỆ THỐNG PHẢI thoát `0` và không in dòng log chẩn đoán nào ra `stderr`
  - Logic cốt lõi: Chạy thực tế cặp lệnh `TDQ_LOG=1` vs `TDQ_LOG=0`, xác nhận `--sinh-main --dry-run` đếm đúng `kept`/`dropped`, ghi số đo vào hồ sơ QC
  - Ca góc hiểm & Assert: `proc_off.returncode == 0 and proc_off.stderr.strip() == ""`

- [x] **T4.2** (e22m) Chạy trọn bộ kiểm thử toàn repo `tdq_test.py tron-bo --workers 1 --fresh --reuse off`, `token_budget.py --kiem`, `doc_lint.py`, hậu kiểm lần cuối `0` tàn dư trên `ubuntu-100-95` & `mbair`, và cử `tdq-qc-tester` đối soát độc lập — Test: `py -3 -X utf8 scripts/tdq_test.py tron-bo --workers 1 --fresh --reuse off && py -3 -X utf8 scripts/token_budget.py --kiem`
  - Req: `§6 Q1–Q5` · Ngoài phạm vi: Không sửa code trừ khi phát hiện lỗi hồi quy (khi đó mở task `QCn.x`)
  - Chạm: `docs/tdq/qc/2026-11-21-1034-bump-version-release-local.md`
  - Cần: `T4.1`
  - Giao tiếp: Consumes: toàn bộ thay đổi `P1`–`P3` | Produces: biên bản QC độc lập PASS `Q1`–`Q5`
  - Neo & Công cụ: `run_command` chạy `tdq_test.py tron-bo`, `token_budget.py --kiem`, `doc_lint.py`; `invoke_subagent` gọi `tdq-qc-tester`; `Write` cập nhật `docs/tdq/qc/2026-11-21-1034-bump-version-release-local.md`
  - Trước → Sau: Chưa kiểm toàn bộ suite sau bump `0.103.0` → toàn bộ `tron-bo` `0 failed` (`bo_sot == 0`) và `tdq-qc-tester` xác nhận
  - Tiêu chí chấp nhận (EARS): KHI chạy `tdq_test.py tron-bo` và `tdq_test.py so`, HỆ THỐNG PHẢI đạt `0 failed` và `bo_sot == 0`
  - Logic cốt lõi: Chạy tĩnh trọn bộ suite sau khi hoàn tất chỉnh sửa, chạy `token_budget.py --kiem` và `doc_lint.py`, xác nhận `0` tàn dư trên 2 máy SSH, rồi gọi `tdq-qc-tester` nghiệm thu độc lập
  - Ca góc hiểm & Assert: Không chạy song song tiến trình ghi file vào repo trong lúc `tron-bo` đang chạy để tránh kết quả `INCOMPLETE`

**Xong P4 khi**: `tdq_test.py tron-bo` đạt `0 failed` (`bo_sot == 0`), `token_budget.py --kiem` `0` lỗi và `tdq-qc-tester` xác nhận `Q1`–`Q5` PASS.

## P5 — Cài đặt Antigravity User-Level & Xuất bản `main` + Tag `v0.103.0`

- [x] **T5.1** (e6m) Cài gói `plugins/tdq-workflow-agy/` (`0.103.0`) ra `C:\Users\admin\.gemini\config\plugins\tdq-workflow-agy` qua `py -3 -X utf8 install.py` (giữ nguyên Caveman + RTK và tự kích hoạt `agy`), đồng bộ khối `<!-- TDQ:TOOLS -->` trong `C:\Users\admin\.gemini\GEMINI.md` bằng `tdq_setup.ghim_huong_dan_tool`, kiểm chứng `agy plugin list`, `agy plugin validate` tại thư mục user-level và xác nhận không chạm `~/.claude/` — Test: `agy.EXE plugin validate C:\Users\admin\.gemini\config\plugins\tdq-workflow-agy --strict --json && agy.EXE plugin list`
  - Dùng: `tdq-setup`
  - Để: đồng bộ khối `<!-- TDQ:TOOLS -->` trong `C:\Users\admin\.gemini\GEMINI.md` theo đúng hàm `ghim_huong_dan_tool`
  - Ra: `C:\Users\admin\.gemini\GEMINI.md` cập nhật dòng `1145` và giữ nguyên phần `## Ngôn ngữ trong chat`
  - Kiểm: Đọc `C:\Users\admin\.gemini\GEMINI.md` xác nhận có dòng `"Mặc định cho cả"` và phần `"Ngôn ngữ trong chat"` nguyên vẹn
  - Không dùng cho: sửa `~/.claude/CLAUDE.md` hay `~/.claude/plugins/` (bị cấm theo yêu cầu chỉ update Antigravity)
  - Dùng: `agy-customizations`, `antigravity-guide`, `plugin`
  - Để: đối chiếu cấu trúc plugin & rule toàn cục user-level của Google Antigravity (`~/.gemini/config/plugins/` và `~/.gemini/GEMINI.md`)
  - Ra: `C:\Users\admin\.gemini\config\plugins\tdq-workflow-agy\plugin.json` phiên bản `0.103.0` đang `enabled`
  - Kiểm: `agy.EXE plugin list` hiện `tdq-workflow-agy (enabled, 0.103.0)` và `mcp_config.json` giữ bọc `tdq_mcp_shrink.py` trên `3` server
  - Không dùng cho: tạo plugin mới hay cài marketplace ngoài
  - Req: `§1, §2#5, §3c B5, §6 Q7` · Ngoài phạm vi: `GIỮ NGUYÊN` toàn bộ `~/.claude/` và `~/.codex/` (xác nhận `mtime` của `installed_plugins.json` không đổi)
  - Chạm: `docs/tdq/qc/2026-11-21-1034-bump-version-release-local.md`
  - Cần: `T4.2`
  - Giao tiếp: Consumes: gói đã qua QC `plugins/tdq-workflow-agy/` (`0.103.0`) và `scripts/tdq_setup.py:ghim_huong_dan_tool` | Produces: bản cài live `~/.gemini/` `0.103.0` + `GEMINI.md` đồng bộ
  - Neo & Công cụ: Ghi `mtime` trước của `~/.claude/plugins/installed_plugins.json`, chạy `py -3 -X utf8 install.py`, gọi `tdq_setup.ghim_huong_dan_tool` cho `~/.gemini/GEMINI.md`; `Write` ghi kết quả `Q7` vào `docs/tdq/qc/2026-11-21-1034-bump-version-release-local.md`
  - Trước → Sau: `~/.gemini/` chạy `0.101.0` & `GEMINI.md` cũ → `0.103.0`, Caveman `3` server nguyên vẹn, `GEMINI.md` đồng bộ
  - Tiêu chí chấp nhận (EARS): KHI chạy xong `T5.1`, HỆ THỐNG PHẢI trả `findings == []` cho thư mục user-level, `agy plugin list` hiện `0.103.0`, `mcp_config.json` bọc đủ `lsp`/`chrome-devtools`/`tavily-primary`, và `mtime` `~/.claude/plugins/installed_plugins.json` không đổi
  - Logic cốt lõi: Chụp `mtime` `~/.claude/`, chạy `install.py`, chạy `ghim_huong_dan_tool` chỉ cho `~/.gemini/GEMINI.md`, hậu kiểm `plugin.json`, `mcp_config.json`, `GEMINI.md`, `agy plugin validate` và `agy plugin list`
  - Ca góc hiểm & Assert: Không truyền cờ làm gỡ Caveman; kiểm `GEMINI.md` không trùng marker `<!-- TDQ:TOOLS -->`

- [x] **T5.2** (e4m) Sau khi người dùng xác nhận commit & merge về `dev`, chạy `py -3 -X utf8 scripts/build_portable.py --sinh-main --nguon dev --nhanh-dich main` để xuất bản nhánh `main` sạch tại local và gắn annotated tag `v0.103.0` lên `main` (tuyệt đối không `git push`) — Test: `git show main:.claude-plugin/plugin.json && git rev-parse v0.103.0^{commit} main`
  - Req: `§1, §2#6, §3c B5, §6 Q6` · Ngoài phạm vi: Không chạy `git push` lên bất kỳ remote nào (`3a`); không thêm trailer `Co-Authored-By:`
  - Chạm: `docs/tdq/reports/2026-11-21-1034-bump-version-release-local.md`
  - Cần: `T5.1`
  - Giao tiếp: Consumes: commit `dev` đã gộp sạch `0.103.0` | Produces: nhánh local `main` tinh gọn + tag annotated `v0.103.0`
  - Neo & Công cụ: `run_command` chạy `git merge --no-ff`, `scripts/build_portable.py --sinh-main --nguon dev --nhanh-dich main`, `git tag -a v0.103.0 main -m "Release v0.103.0: ..."`; `Write` tạo mới `docs/tdq/reports/2026-11-21-1034-bump-version-release-local.md`
  - Trước → Sau: `main` ở `v0.100.0`, tag mới nhất `v0.99.0` → `main` ở `v0.103.0`, tag `v0.103.0` khớp `main` HEAD
  - Tiêu chí chấp nhận (EARS): KHI chạy xong `T5.2`, HỆ THỐNG PHẢI cho `git show main:.claude-plugin/plugin.json` có `"version": "0.103.0"` và `git rev-parse v0.103.0^{commit} == git rev-parse main`
  - Logic cốt lõi: Chỉ chạy sau khi merge `--no-ff` xong về `dev`; dùng Git plumbing `--sinh-main` giữ working tree sạch; tạo tag annotated trỏ đúng `main`
  - Ca góc hiểm & Assert: Kiểm nhánh `main` không chứa `docs/tdq/`, `tests/`, `hooks/rust/` và không phát sinh lệnh `git push`

**Xong P5 khi**: Antigravity user-level chạy `0.103.0` (`Q7` PASS) và nhánh `main` + tag `v0.103.0` đã xuất bản sạch ở local (`Q6` PASS).

## Cụm song song

- **Cụm 1 (Khởi đầu):** `T1.1` (manifests/docs) và `T2.1` (Windows Rust `0.103.0`) chạm vùng file tách rời nên có thể nối tiếp nhanh hoặc chạy song song.
- **Cụm 2 (SSH 2 OS — sau `T2.1`):** `T2.2` (SSH `ubuntu-100-95`) và `T2.3` (SSH `mbair`) chạy trên 2 máy khác nhau và xuất 2 file nhị phân tách biệt trong `plugins/tdq-workflow-agy/bin/`.
- **Cụm 3 (Đóng gói, QC, Cài đặt & Release — tuần tự):** `T3.1` → `T4.1` → `T4.2` → `T5.1` → `T5.2` có phụ thuộc cứng dữ liệu đầu vào/đầu ra và cổng duyệt nên chạy tuần tự.

## Luật file nóng (một file, nhiều task chạm)

- `docs/tdq/qc/2026-11-21-1034-bump-version-release-local.md` được ghi nối tiếp qua `T4.1` → `T4.2` → `T5.1` theo thứ tự `Cần:` tuần tự (một chủ ghi tại từng thời điểm, không ghi song song). Không có tệp mã nguồn nào bị 2 task cùng sóng chạm đồng thời.

## Definition of Done

- [x] Q1 Manifest, `README.md`, `UPSTREAM-TRACE.md`, `CHANGELOG.md` (`<= 500` dòng) & `docs/CHANGELOG-archive-3.md` đồng bộ `0.103.0` — `py -3 -X utf8 -m pytest tests/test_docs_consistency.py tests/test_adapter_host.py -q && py -3 -X utf8 scripts/doc_lint.py CHANGELOG.md docs/CHANGELOG-archive-3.md`
- [x] Q2 Crate Rust `0.103.0` & 3 nhị phân native thật (`Windows`, `Linux musl`, `macOS ARM64`) PASS `cargo test`, `clippy`, parity/lock và simulation SSH — `cargo test --manifest-path hooks/rust/tdq-dispatch/Cargo.toml && py -3 -X utf8 -m pytest tests/test_rust_dispatch_parity.py tests/test_rust_lock_safety.py tests/test_remote_linux_simulation.py tests/test_remote_mac_simulation.py -q`
- [x] Q3 Hai máy test SSH (`ubuntu-100-95`, `mbair`) sạch `0` tàn dư sau build & test — `ssh ubuntu-100-95 "ls -d /tmp/tdq* /tmp/tdq_dispatch* ~/tdq* 2>/dev/null | wc -l" && ssh mbair "ls -d /tmp/tdq* ~/tdq* 2>/dev/null | wc -l"`
- [x] Q4 Compiler & gói plugin `plugins/tdq-workflow-agy/` (`v0.103.0`) đạt chuẩn nghiêm ngặt — `py -3 -X utf8 tools/build_agy_plugin.py --upstream . && agy.EXE plugin validate plugins/tdq-workflow-agy --strict --json && py -3 -X utf8 scripts/token_budget.py --kiem`
- [x] Q5 Bộ kiểm thử toàn repo (`muc_qc = full`) đạt `0 failed` (`bo_sot == 0`) & QC độc lập PASS — `py -3 -X utf8 scripts/tdq_test.py tron-bo --workers 1 --fresh --reuse off`
- [x] Q6 Nhánh phát hành local `main` (`--sinh-main` từ `dev`) & annotated tag `v0.103.0` hợp lệ, không `git push` — `git show main:.claude-plugin/plugin.json && git rev-parse v0.103.0^{commit} main`
- [x] Q7 Antigravity user-level (`~/.gemini/config/plugins/tdq-workflow-agy` + `~/.gemini/GEMINI.md`) chạy `0.103.0` nguyên Caveman/RTK và không chạm `~/.claude/` — `agy.EXE plugin validate C:\Users\admin\.gemini\config\plugins\tdq-workflow-agy --strict --json && agy.EXE plugin list`
