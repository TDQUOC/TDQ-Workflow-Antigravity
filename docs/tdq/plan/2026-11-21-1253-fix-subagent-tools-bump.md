# PLAN — Sửa Lỗi Registry Tool 8 Subagent Antigravity, Build Rust 3 OS & Phát hành `0.103.1`

Ngày: 2026-11-21 · Spec: ../spec/2026-11-21-1253-fix-subagent-tools-bump.md (bản 1.0, ĐÃ DUYỆT) · Lane: full
Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md
Mode thực thi: subagent — `tdq_bench.py simulate` (`--he-so-agent 1.5`) chấm `đội (subagent)` thắng `2.0` phút (`18.4` vs `20.4` phút trên `10` task / `6` wave nhờ Sóng 1 `T1.1+T2.1+T2.2` và Sóng 2 SSH `T2.3+T2.4` chạy song song) (ĐỀ XUẤT, user chốt lúc duyệt)
Trạng thái plan: ĐÃ DUYỆT

> **Tóm tắt dễ hiểu:** Kế hoạch gồm `5` đợt (`10` task) giúp cả `8/8` subagent của `tdq-workflow-agy` hết sập khi khởi tạo trên Antigravity 2.0 và phát hành đồng bộ bản vá `0.103.1`. Trước hết sửa bộ tool chuẩn registry trong compiler `tools/patches/skills_and_agents.py`, xóa lặp `write_file` ở `agents/tdq-explorer.md` và khóa chặt bằng test âm tính, đồng thời nâng tài liệu, manifest và biên dịch lại nhị phân Rust trên `3` hệ điều hành (Windows local + SSH song song `ubuntu-100-95` và `mbair`, dọn `0` rác). Cuối cùng đóng gói lại `plugins/tdq-workflow-agy/`, chạy trọn bộ kiểm định đa worker (`--workers 6`), cài riêng cho Antigravity trên máy (`~/.gemini/`) rồi xuất nhánh local `main` và tag `v0.103.1` sau khi bạn duyệt commit.

## Mục lục

- Phân bổ Model & Effort
- Quy tắc thi hành (áp cho mọi task)
- Thiết kế Trước vs Sau
- Ràng buộc toàn cục & Bản đồ Sở hữu Hợp đồng (Ownership Map)
- P1 — Vá Registry Tool Subagent & Test Khóa Âm Tính
- P2 — Đồng bộ Version `0.103.1` & Biên dịch Rust 3 OS Song song
- P3 — Đóng gói Compiler `tdq-workflow-agy` `v0.103.1` & Kiểm Bundle
- P4 — Log & Test Bắt buộc + Kiểm định Toàn repo Đa Worker
- P5 — Cài đặt Antigravity User-Level `0.103.1`, Kiểm Subagent & Xuất bản `main` + Tag `v0.103.1`
- Cụm song song
- Luật file nóng (một file, nhiều task chạm)
- Definition of Done

## Phân bổ Model & Effort
<!-- i18n-allow: canonical model/effort plan allocation table -->
> User được quyền đổi `type model` hoặc `effort` lúc duyệt plan. Thang model: [subagent-tuning.md](../../tdq-conventions/references/subagent-tuning.md).

| Pha | Vai trò | Model | Effort | Ghi chú |
|---|---|---|---|---|
| `implement` | Leader / `tdq-implementer` | `inherit` | `high` | Sửa compiler agent, build Rust SSH 3 OS và cài user-level `~/.gemini/` cần độ chính xác cao |
| `qc` | `tdq-qc-tester` / `self` | `inherit` | `high` | Chạy `tron-bo --workers 6`, đối soát `Q1`–`Q7`; dùng `self` nếu IDE hiện tại còn cache catalog `0.103.0` trong RAM |
| `report` | Leader | `inherit` | `high` | Xuất cặp report `.md` + Archify HTML (Tailscale HTTP 200) ngắn gọn dễ hiểu |

## Quy tắc thi hành (áp cho mọi task)
1. Thứ tự phase là thứ tự phụ thuộc — không đảo.
2. Mỗi task: đánh `[~]` khi bắt đầu → chạy kiểm đỏ trước → viết/sửa mã → kiểm xanh → đổi sang `[x]` NGAY vào file này.
3. Mỗi bước: `py -3 -X utf8 scripts/tdq_test.py vung-cham`; trọn bộ `tron-bo` chạy tại cổng QC (`P4`).
4. Lệnh nào chạm state của workflow trong test phải đặt `TDQ_PROJECT_DIR=<thư mục tạm>`.
5. QC FAIL → thêm task fix `QCn.x` vào file này (không cần duyệt lại), loop đến khi pass `0 failed`.
6. Không tự commit hoặc `git push` cho đến khi người dùng yêu cầu; `git push` nằm ngoài phạm vi (`3a`).
7. Tuân thủ `6` mã cấm cơ học (ANTI-1 Fake Red, ANTI-2 Blind Assertion, ANTI-3 Dirty State Git, ANTI-4 Late Tick, ANTI-5 Raw Dump, ANTI-6 Broad Area).

## Thiết kế Trước vs Sau
| Khía cạnh | Hiện trạng (Trước) | Thiết kế mới (Sau) |
|---|---|---|
| Tool trong `agents/tdq-*.md` (`8/8`) | Khai `call_mcp_tool`, `grep_search`, `find_by_name`, `list_dir` làm executor sập; `tdq-explorer.md` lặp `write_file` | Chỉ khai tool chuẩn Antigravity (`read_file`, `edit_file`, `write_file`, `run_command`, `manage_task`, `search_web`, `send_message`) + test âm tính |
| Phiên bản & Rust 3 OS | `0.103.0` ở repo/Rust/`~/.gemini/`; chạy `tron-bo` `1` worker tốn ~22 phút | Toàn bộ repo, crate Rust 3 OS (`Windows` + SSH song song `ubuntu-100-95`/`mbair`) đồng bộ `0.103.1`; `tron-bo --workers 6` |
| Phát hành & Local Antigravity | `main` & `~/.gemini/` giữ bản `0.103.0` lỗi subagent | `main` & tag `v0.103.1` sạch ở local; `~/.gemini/` chạy `0.103.1` nguyên Caveman/RTK và không chạm `~/.claude/` |

*Đối chiếu sơ đồ kiến trúc:* Tham chiếu Archify preview đã duyệt tại [2026-11-21-1253-fix-subagent-tools-bump-preview.html](../spec/2026-11-21-1253-fix-subagent-tools-bump-preview.html) và manifest `current` tại [2026-11-21-1253-fix-subagent-tools-bump-preview.manifest.json](../spec/2026-11-21-1253-fix-subagent-tools-bump-preview.manifest.json).

## Ràng buộc toàn cục & Bản đồ Sở hữu Hợp đồng (Ownership Map)

- Ngôn ngữ: English comments/CLI trong mã nguồn · `utf8_io` / `encoding="utf-8"` · `TDQ_LOG=0` tắt log · hàm mới `<= 50` dòng (`cyc <= 10`, `cog <= 15`) · `GIỮ NGUYÊN` chữ ký `transform_agents`, `transform_skills`, `_rewrite_skill_text`, `generate_plugin_json`, `build`, `main` và giữ nguyên `call_mcp_tool`/`grep_search` trong `hooks/`.

| Hợp đồng / Ký hiệu (§3c) | File & Task sở hữu | Task / File tiêu thụ |
|---|---|---|
| `_READONLY_TOOLS`, `_WRITER_TOOLS`, `AGY_ALLOWED_TOOLS`, `AGY_FORBIDDEN_TOOLS` | `tools/patches/skills_and_agents.py`, `agents/tdq-explorer.md`, `tests/test_agent_frontmatter.py` (`T1.1`) | `tools/build_agy_plugin.py:build` (`T3.1`), `plugins/tdq-workflow-agy/agents/tdq-*.md` (`Q1`) |
| `version = "0.103.1"` (manifests + changelog head) | `.claude-plugin/plugin.json`, `.codex-plugin/plugin.json`, `README.md`, `UPSTREAM-TRACE.md`, `CHANGELOG.md` (`T2.1`) | `tests/test_docs_consistency.py`, `tests/test_adapter_host.py`, `scripts/build_portable.py:plugin_version` (`T5.2`) |
| `tdq-dispatch` crate `0.103.1` & `3` native binaries | `hooks/rust/tdq-dispatch/Cargo.toml` (`T2.2`), `plugins/tdq-workflow-agy/bin/tdq-dispatch*` (`T2.2`–`T2.4`) | `tools/build_agy_plugin.py:_stage_rust_binaries` (`T3.1`), `tests/test_remote_linux_simulation.py`, `tests/test_remote_mac_simulation.py` (`T2.3`, `T2.4`) |
| `PLUGIN_VERSION = "0.103.1"` & compiled AGY bundle | `tools/patches/agy_manifests.py`, `tools/patches/__init__.py`, `tools/build_agy_plugin.py` (`T3.1`) | `plugins/tdq-workflow-agy/{plugin.json,manifest.json,README.md,agents/*.md}`, `install.py` (`T5.1`) |
| User-level `~/.gemini/` `0.103.1` & local `main` + tag `v0.103.1` | `C:\Users\admin\.gemini\config\plugins\tdq-workflow-agy` (`T5.1`), nhánh `main` + tag `v0.103.1` (`T5.2`) | `agy.EXE plugin list`, `agy.EXE plugin validate`, `git show main:.claude-plugin/plugin.json` (`Q6`, `Q7`) |

## P1 — Vá Registry Tool Subagent & Test Khóa Âm Tính

- [x] **T1.1** (e6m) Cập nhật danh sách tool chuẩn registry Antigravity `_READONLY_TOOLS` và `_WRITER_TOOLS` tại `tools/patches/skills_and_agents.py:28-47`, sửa lặp `(`Write`/`Edit`/`write_file`)` ở `agents/tdq-explorer.md:15` thành `(`Write`/`Edit`)`, và nâng cấp `tests/test_agent_frontmatter.py:34,120-144` với `AGY_DISCOVERY_TOOLS`, `AGY_ALLOWED_TOOLS`, `AGY_FORBIDDEN_TOOLS` kèm test âm tính — Test: `py -3 -X utf8 -m pytest tests/test_agent_frontmatter.py -k "not test_built_agy_agents" -q`
  - Dùng: `agy-customizations`, `migrate-agent-settings`, `antigravity-guide`, `plugin`
  - Để: đối chiếu bảng ánh xạ tên tool subagent hợp lệ và chuẩn frontmatter/plugin agent của Antigravity 2.0 (`read_file`, `edit_file`, `write_file`, `run_command`, `manage_task`, `search_web`, `send_message`), nạp trước bước đỏ
  - Ra: `tools/patches/skills_and_agents.py`, `agents/tdq-explorer.md`, `tests/test_agent_frontmatter.py` khớp chuẩn registry Antigravity
  - Kiểm: `py -3 -X utf8 -m pytest tests/test_agent_frontmatter.py -k "not test_built_agy_agents" -q` đạt `0 failed`
  - Không dùng cho: thay đổi bộ công cụ hook giám sát agent chính trong `hooks/` hoặc `tools/patches/agy_hooks.py`
  - Req: `§1, §2#1, §3, §3c B1` · Ngoài phạm vi: `GIỮ NGUYÊN` `call_mcp_tool` và `grep_search` trong `hooks.json`, `tools/patches/agy_hooks.py`, `hooks/rust/tdq-dispatch/`; giữ `model: inherit` và các notice `[TDQ:READONLY]`/`[TDQ:SCOPED-WRITE]`/`[TDQ:QC-SCOPED]`
  - Chạm: `tools/patches/skills_and_agents.py`, `agents/tdq-explorer.md`, `tests/test_agent_frontmatter.py`
  - Cần: Không
  - Giao tiếp: Consumes: bảng ánh xạ tool Antigravity (`_READONLY_TOOLS`, `_WRITER_TOOLS`) | Produces: `transform_agents()` xuất frontmatter hợp lệ và test khóa `AGY_FORBIDDEN_TOOLS`
  - Neo & Công cụ: `Edit` tại `tests/test_agent_frontmatter.py:34,120-144`, `tools/patches/skills_and_agents.py:28-47`, `agents/tdq-explorer.md:15`
  - Trước → Sau: `_READONLY_TOOLS`/`_WRITER_TOOLS` chứa `call_mcp_tool`, `grep_search`, `find_by_name`, `list_dir` → chỉ dùng tool chuẩn registry (`read_file`, `edit_file`, `write_file`, `run_command`, `manage_task`, `search_web`, `send_message`)
  - Tiêu chí chấp nhận (EARS): KHI chạy `test_skills_and_agents_tool_lists_forbid_unregistered_tools` sau khi sửa, HỆ THỐNG PHẢI thấy `_READONLY_TOOLS == ["read_file", "run_command", "manage_task", "send_message"]`, `_WRITER_TOOLS == ["read_file", "edit_file", "write_file", "run_command", "manage_task", "search_web", "send_message"]` và `0` xuất hiện `AGY_FORBIDDEN_TOOLS`
  - Logic cốt lõi: (1) Sửa `tests/test_agent_frontmatter.py` trước và chạy thấy Đỏ (`AssertionError` vì `_READONLY_TOOLS`/`_WRITER_TOOLS` còn chứa `call_mcp_tool`); (2) sửa `_READONLY_TOOLS`/`_WRITER_TOOLS` trong `tools/patches/skills_and_agents.py:28-47` và dòng `15` của `agents/tdq-explorer.md`; (3) chạy lại unit test xác nhận Xanh (giữ riêng test khóa bundle đã build `test_built_agy_agents_forbid_unregistered_tools` để kích hoạt Đỏ → Xanh khi rebuild ở `T3.1`)
  - Ca góc hiểm & Assert: `assert tools <= AGY_ALLOWED_TOOLS and not (tools & AGY_FORBIDDEN_TOOLS)` cho cả `AGENT_FRONTMATTERS` lẫn output `transform_agents()` vào `tmp_path`, và `assert "write_file/write_file" not in explorer_body`

**Xong P1 khi**: `tests/test_agent_frontmatter.py -k "not test_built_agy_agents"` đi từ Đỏ → Xanh `0 failed` và `test_built_agy_agents_forbid_unregistered_tools` đã sẵn sàng bắt lỗi trên bundle cũ.

## P2 — Đồng bộ Version `0.103.1` & Biên dịch Rust 3 OS Song song

- [x] **T2.1** (e5m) Nâng phiên bản lên `0.103.1` trong `.claude-plugin/plugin.json:4`, `.codex-plugin/plugin.json:3`, `README.md:3,144,237`, `UPSTREAM-TRACE.md:24` và chèn mục `## 0.103.1 — 2026-11-21` lên đầu `CHANGELOG.md:5` (giữ `CHANGELOG.md <= 500` dòng trên nền `461` dòng, không cần tách archive) — Test: `py -3 -X utf8 -m pytest tests/test_docs_consistency.py tests/test_adapter_host.py -q && py -3 -X utf8 scripts/doc_lint.py CHANGELOG.md`
  - Req: `§1, §2#2, §3c B2` · Ngoài phạm vi: `GIỮ NGUYÊN` `description` khớp giữa Claude và Codex manifest, giữ số đếm `skills/` (`11`), `agents/` (`8`), `hooks/` (`17`), `scripts/` (`73`), `docs/CHANGELOG-archive-3.md`
  - Chạm: `.claude-plugin/plugin.json`, `.codex-plugin/plugin.json`, `README.md`, `UPSTREAM-TRACE.md`, `CHANGELOG.md`
  - Cần: Không
  - Giao tiếp: Consumes: dữ kiện bản vá `0.103.1` | Produces: `version == "0.103.1"` trên manifest và đỉnh `CHANGELOG.md`
  - Neo & Công cụ: `Edit` tại `.claude-plugin/plugin.json:4`, `.codex-plugin/plugin.json:3`, `CHANGELOG.md:5`, `README.md:3,144,237`, `UPSTREAM-TRACE.md:24`
  - Trước → Sau: Tài liệu và manifest `0.103.0`, `CHANGELOG.md` `461` dòng → `0.103.1`, `CHANGELOG.md <= 490` dòng
  - Tiêu chí chấp nhận (EARS): KHI chạy `test_docs_consistency.py`, `test_adapter_host.py` và `doc_lint.py CHANGELOG.md`, HỆ THỐNG PHẢI trả `0 failed` và `0 violation(s)` với tổng dòng `CHANGELOG.md <= 500`
  - Logic cốt lõi: Cập nhật `"version": "0.103.1"` ở `.claude-plugin/plugin.json` và `.codex-plugin/plugin.json`; thêm mục ngắn gọn `## 0.103.1 — 2026-11-21` (~`12` dòng) vào `CHANGELOG.md:5`; cập nhật badge/mục tiêu ở `README.md` và `Release Tag: v0.103.1` ở `UPSTREAM-TRACE.md`
  - Ca góc hiểm & Assert: Kiểm không vượt trần `500` dòng của `doc_lint R6`, `assert claude_ver == codex_ver == "0.103.1"`

- [x] **T2.2** (e5m) Nâng `hooks/rust/tdq-dispatch/Cargo.toml:3` lên `version = "0.103.1"`, chạy `cargo test`, `cargo clippy --all-targets -- -D warnings`, biên dịch `cargo build --release` (`+crt-static`) trên Windows và cập nhật `plugins/tdq-workflow-agy/bin/tdq-dispatch.exe` — Test: `cargo test --manifest-path hooks/rust/tdq-dispatch/Cargo.toml && cargo clippy --manifest-path hooks/rust/tdq-dispatch/Cargo.toml --all-targets -- -D warnings`
  - Req: `§1, §2#3, §3c B3` · Ngoài phạm vi: `GIỮ NGUYÊN` logic parser `command_parser.rs`, `pre_tool_use.rs`, `scoped-write` `5` lớp và giữ nguyên quy tắc `call_mcp_tool`/`grep_search` trong Rust hook
  - Chạm: `hooks/rust/tdq-dispatch/Cargo.toml`, `hooks/rust/tdq-dispatch/Cargo.lock`, `plugins/tdq-workflow-agy/bin/tdq-dispatch.exe`
  - Cần: Không
  - Giao tiếp: Consumes: crate `hooks/rust/tdq-dispatch/` | Produces: `Cargo.toml`/`Cargo.lock` bản `0.103.1` và PE binary `tdq-dispatch.exe`
  - Neo & Công cụ: `Edit` tại `hooks/rust/tdq-dispatch/Cargo.toml:3`; `run_command` chạy `cargo test`, `cargo clippy`, `cargo build --release` và chép `target/release/tdq-dispatch.exe`
  - Trước → Sau: `Cargo.toml` và `tdq-dispatch.exe` bản `0.103.0` → bản `0.103.1` kèm `Cargo.lock` đồng bộ
  - Tiêu chí chấp nhận (EARS): KHI chạy `cargo test`, `cargo clippy --all-targets -- -D warnings` và `cargo build --release`, HỆ THỐNG PHẢI trả `0 failed`, `0` warnings và magic header `MZ`
  - Logic cốt lõi: Sửa `version = "0.103.1"` ở `Cargo.toml:3`, chạy `cargo test` cập nhật `Cargo.lock`, chạy `cargo clippy` với `-D warnings`, build release rồi copy đè `plugins/tdq-workflow-agy/bin/tdq-dispatch.exe`
  - Ca góc hiểm & Assert: `assert open('plugins/tdq-workflow-agy/bin/tdq-dispatch.exe','rb').read(2) == b'MZ'` và kiểm `Cargo.lock` chứa `name = "tdq-dispatch"` ở `version = "0.103.1"`

- [x] **T2.3** (e8m) Dùng `scratch/ssh_rust_build.py` gửi nguồn `hooks/rust/tdq-dispatch` (kèm `tools/patches/gate_guidance.json`) qua SSH lên `ubuntu-100-95`, chạy `cargo test` và `cargo build --release --target x86_64-unknown-linux-musl`, tải về `plugins/tdq-workflow-agy/bin/tdq-dispatch-linux-x86_64`, chạy `test_remote_linux_simulation.py` và hậu kiểm `0` tệp sót — Test: `py -3 -X utf8 -m pytest tests/test_remote_linux_simulation.py -q`
  - Req: `§1, §2#3, §2#4, §3c B3` · Ngoài phạm vi: `GIỮ NGUYÊN` rustup toolchain và mọi tệp ngoài `/tmp/tdq-build-*` của user `ubuntu` trên `ubuntu-100-95`
  - Chạm: `plugins/tdq-workflow-agy/bin/tdq-dispatch-linux-x86_64`
  - Cần: `T2.2`
  - Giao tiếp: Consumes: `hooks/rust/tdq-dispatch/{Cargo.toml,Cargo.lock,.cargo,src}` (`0.103.1`) và `tools/patches/gate_guidance.json` | Produces: ELF x86-64 static `tdq-dispatch-linux-x86_64` và xác nhận sạch `ubuntu-100-95`
  - Neo & Công cụ: `run_command` gọi `scratch/ssh_rust_build.py --host ubuntu-100-95` (chạy song song cùng `T2.4`) và `pytest tests/test_remote_linux_simulation.py`
  - Trước → Sau: `tdq-dispatch-linux-x86_64` bản `0.103.0` → nhị phân ELF `0.103.1` mới và `COUNT=0` tàn dư trên `ubuntu-100-95`
  - Tiêu chí chấp nhận (EARS): KHI hoàn thành build/test/cleanup trên `ubuntu-100-95`, HỆ THỐNG PHẢI đạt `cargo test` `0 failed`, `test_remote_linux_simulation.py` `1 passed`, magic `\x7fELF`, và `ssh ubuntu-100-95 "ls -d /tmp/tdq* /tmp/tdq_dispatch* ~/tdq* 2>/dev/null | wc -l"` trả `0`
  - Logic cốt lõi: Truyền `Cargo.lock` vừa cập nhật của `T2.2` cùng nguồn Rust và `gate_guidance.json`, build target `x86_64-unknown-linux-musl`, tải nhị phân về `plugins/tdq-workflow-agy/bin/`, dọn trong `finally`, rồi chạy simulation test
  - Ca góc hiểm & Assert: Luôn xóa `/tmp/tdq*` kể cả khi build thất bại; `assert data[:4] == b'\x7fELF'` và kiểm `leftover_count == 0`

- [x] **T2.4** (e8m) Dùng `scratch/ssh_rust_build.py` gửi nguồn `hooks/rust/tdq-dispatch` (kèm `tools/patches/gate_guidance.json`) qua SSH lên `mbair` song song với `T2.3`, chạy `cargo test` và `cargo build --release --target aarch64-apple-darwin`, tải về `plugins/tdq-workflow-agy/bin/tdq-dispatch-darwin-arm64`, chạy `test_remote_mac_simulation.py` và hậu kiểm `0` tệp sót — Test: `py -3 -X utf8 -m pytest tests/test_remote_mac_simulation.py -q`
  - Req: `§1, §2#3, §2#4, §3c B3` · Ngoài phạm vi: `GIỮ NGUYÊN` Xcode CLT, rustup toolchain và mọi tệp khác trên `mbair`
  - Chạm: `plugins/tdq-workflow-agy/bin/tdq-dispatch-darwin-arm64`
  - Cần: `T2.2`
  - Giao tiếp: Consumes: `hooks/rust/tdq-dispatch/{Cargo.toml,Cargo.lock,.cargo,src}` (`0.103.1`) và `tools/patches/gate_guidance.json` | Produces: Mach-O ARM64 `tdq-dispatch-darwin-arm64` và xác nhận sạch `mbair`
  - Neo & Công cụ: `run_command` gọi `scratch/ssh_rust_build.py --host mbair` song song với `T2.3`, rồi chạy `pytest tests/test_remote_mac_simulation.py`
  - Trước → Sau: `tdq-dispatch-darwin-arm64` bản `0.103.0` → nhị phân Mach-O `0.103.1` mới và `COUNT=0` tàn dư trên `mbair`
  - Tiêu chí chấp nhận (EARS): KHI hoàn thành build/test/cleanup trên `mbair`, HỆ THỐNG PHẢI đạt `cargo test` `0 failed`, `test_remote_mac_simulation.py` `1 passed`, magic Mach-O ARM64, và `ssh mbair "setopt NULL_GLOB; ls -d /tmp/tdq* ~/tdq* 2>/dev/null | wc -l"` trả `0`
  - Logic cốt lõi: Chạy song song cùng tiến trình SSH `ubuntu-100-95`, build target `aarch64-apple-darwin`, kéo binary về `plugins/tdq-workflow-agy/bin/`, giải phóng toàn bộ thư mục tạm `/tmp/tdq*` và chạy simulation test macOS
  - Ca góc hiểm & Assert: Bọc zsh `NULL_GLOB` (hoặc `/bin/sh`) khi kiểm `ls -d` trên macOS; `assert data[:4] == b'\xcf\xfa\xed\xfe'` và `leftover_count == 0`

**Xong P2 khi**: Bộ kiểm tài liệu/manifest `0.103.1` xanh, `3` nhị phân Rust (`Windows`/`Linux musl`/`macOS ARM64`) PASS `cargo test` + simulation test, và `2` máy SSH còn `0` tàn dư.

## P3 — Đóng gói Compiler `tdq-workflow-agy` `v0.103.1` & Kiểm Bundle

- [x] **T3.1** (e6m) Nâng `PLUGIN_VERSION = "0.103.1"` tại `tools/patches/agy_manifests.py:11` và chuỗi phiên bản ở `tools/patches/__init__.py:1`, `tools/build_agy_plugin.py:2,275`; xác nhận `test_built_agy_agents_forbid_unregistered_tools` báo Đỏ trên gói `0.103.0` cũ; chạy `py -3 -X utf8 tools/build_agy_plugin.py --upstream .`; rồi chạy xanh toàn bộ test agent/plugin/parity/lock, `agy.EXE plugin validate --strict` và `token_budget.py --kiem` — Test: `py -3 -X utf8 -m pytest tests/test_agent_frontmatter.py tests/test_agy_plugin_validate.py tests/test_rust_dispatch_parity.py tests/test_rust_lock_safety.py -q && agy.EXE plugin validate plugins/tdq-workflow-agy --strict --json`
  - Dùng: `tdq-checkportable`
  - Để: kiểm tra tính toàn vẹn, cấu trúc manifest và khả năng chuyển dịch của gói `plugins/tdq-workflow-agy/` sau khi build `0.103.1`, nạp trước bước kiểm cuối
  - Ra: `plugins/tdq-workflow-agy/{plugin.json,manifest.json,README.md}` và `8` file `plugins/tdq-workflow-agy/agents/tdq-*.md` sạch tool cấm ở phiên bản `0.103.1`
  - Kiểm: `agy.EXE plugin validate plugins/tdq-workflow-agy --strict --json` trả `findings == []` và `token_budget.py --kiem` trả `0` vi phạm
  - Không dùng cho: cài trực tiếp ra `~/.gemini/` (để riêng ở `T5.1`)
  - Req: `§1, §2#5, §3c B4` · Ngoài phạm vi: `GIỮ NGUYÊN` chữ ký `generate_plugin_json`, `generate_manifest_and_readme`, `_stage_rust_binaries`, `build`, `main`
  - Chạm: `tools/patches/agy_manifests.py`, `tools/patches/__init__.py`, `tools/build_agy_plugin.py`, `plugins/tdq-workflow-agy/plugin.json`, `plugins/tdq-workflow-agy/manifest.json`, `plugins/tdq-workflow-agy/README.md`, `plugins/tdq-workflow-agy/agents/tdq-implementer.md`, `plugins/tdq-workflow-agy/agents/tdq-qc-tester.md`, `plugins/tdq-workflow-agy/agents/tdq-reviewer.md`, `plugins/tdq-workflow-agy/agents/tdq-security-reviewer.md`, `plugins/tdq-workflow-agy/agents/tdq-build-resolver.md`, `plugins/tdq-workflow-agy/agents/tdq-refactor-cleaner.md`, `plugins/tdq-workflow-agy/agents/tdq-explorer.md`, `plugins/tdq-workflow-agy/agents/tdq-debugger.md`
  - Cần: `T1.1`, `T2.1`, `T2.3`, `T2.4`
  - Giao tiếp: Consumes: `transform_agents()` (`T1.1`), `.claude-plugin/plugin.json` (`T2.1`), `3` nhị phân Rust (`T2.2`–`T2.4`) | Produces: gói `plugins/tdq-workflow-agy/` `v0.103.1` hợp lệ `0` lỗi
  - Neo & Công cụ: `Edit` tại `tools/patches/agy_manifests.py:11`, `tools/patches/__init__.py:1`, `tools/build_agy_plugin.py:2,275`; chạy `build_agy_plugin.py --upstream .`
  - Trước → Sau: Gói `plugins/tdq-workflow-agy/` ở `0.103.0` chứa `call_mcp_tool` trong `8/8` agents → gói `0.103.1` sạch `0` tool cấm, giữ `call_mcp_tool`/`grep_search` trong `hooks/`
  - Tiêu chí chấp nhận (EARS): KHI chạy xong `build_agy_plugin.py --upstream .`, HỆ THỐNG PHẢI trả `"status": "OK"`, `test_agent_frontmatter.py` + `test_agy_plugin_validate.py` `0 failed`, `agy plugin validate --strict` `findings == []` và `token_budget.py --kiem` exit `0`
  - Logic cốt lõi: Sửa `PLUGIN_VERSION = "0.103.1"`, chạy test khóa `test_built_agy_agents_forbid_unregistered_tools` lấy bằng chứng Đỏ trên gói cũ `0.103.0`, chạy `build_agy_plugin.py --upstream .` sinh lại toàn bộ gói `plugins/tdq-workflow-agy/`, rồi xác minh Xanh bằng `pytest`, `agy plugin validate` và `token_budget.py --kiem`
  - Ca góc hiểm & Assert: `assert pjson["version"] == "0.103.1" and mjson["version"] == "0.103.1"` và mọi `md` trong `plugins/tdq-workflow-agy/agents/` thỏa `assert not (tools & AGY_FORBIDDEN_TOOLS)`

**Xong P3 khi**: `plugins/tdq-workflow-agy/` (`v0.103.1`) PASS toàn bộ `test_agent_frontmatter.py`, `test_agy_plugin_validate.py`, `test_rust_dispatch_parity.py`, `test_rust_lock_safety.py`, `agy plugin validate --strict` (`findings == []`) và `token_budget.py --kiem`.

## P4 — Log & Test Bắt buộc + Kiểm định Toàn repo Đa Worker

- [>] **T4.1** (e4m) Kiểm chứng log service bật mặc định có timestamp ISO (`TDQ_LOG=1`) và im lặng hoàn toàn khi tắt (`TDQ_LOG=0`) trên `tools/build_agy_plugin.py`, `scripts/build_portable.py --sinh-main --nguon HEAD --dry-run` và `plugins/tdq-workflow-agy/bin/tdq-dispatch.exe`; khởi tạo biên bản QC `docs/tdq/qc/2026-11-21-1253-fix-subagent-tools-bump.md` — Test: `py -3 -X utf8 -m pytest tests/test_build_portable.py tests/test_rust_dispatch_parity.py -q`
  - Req: `§4` · Ngoài phạm vi: `GIỮ NGUYÊN` toàn bộ mã nguồn runtime (chỉ đo kiểm và ghi hồ sơ QC)
  - Chạm: `docs/tdq/qc/2026-11-21-1253-fix-subagent-tools-bump.md`
  - Cần: `T3.1`
  - Giao tiếp: Consumes: `tools/build_agy_plugin.py`, `scripts/build_portable.py`, `plugins/tdq-workflow-agy/bin/tdq-dispatch.exe` | Produces: bằng chứng log `TDQ_LOG=1` / `TDQ_LOG=0` trong file QC
  - Neo & Công cụ: `run_command` chạy cặp `TDQ_LOG=1` và `TDQ_LOG=0`; `Write` tạo `docs/tdq/qc/2026-11-21-1253-fix-subagent-tools-bump.md`
  - Trước → Sau: Chưa có biên bản kiểm log cho `0.103.1` → ghi nhận đủ bằng chứng timestamp ISO (`TDQ_LOG=1`) và im lặng (`TDQ_LOG=0`)
  - Tiêu chí chấp nhận (EARS): KHI chạy `build_portable.py --sinh-main --nguon HEAD --dry-run` với `TDQ_LOG=0`, HỆ THỐNG PHẢI thoát `0` và `stderr` rỗng hoàn toàn (`stderr.strip() == ""`)
  - Logic cốt lõi: Chạy đối chiếu `TDQ_LOG=1` và `TDQ_LOG=0` qua môi trường tách biệt, xác nhận test parity + build portable xanh, lưu log vào biên bản QC
  - Ca góc hiểm & Assert: `assert proc_on.returncode == 0 and len(proc_on.stderr) > 0 and proc_off.returncode == 0 and proc_off.stderr.strip() == ""`

- [ ] **T4.2** (e8m) Chạy trọn bộ kiểm thử toàn repo đa worker `py -3 -X utf8 scripts/tdq_test.py tron-bo --workers 6 --fresh --reuse off` (dự phòng `--workers 2` hoặc `--workers 1` nếu gặp race lock đa tiến trình trên Windows), chạy `token_budget.py --kiem`, `doc_lint.py`, hậu kiểm cuối `0` tàn dư trên `ubuntu-100-95` & `mbair`, và thực hiện QC độc lập (`muc_qc = full`; dùng `self` subagent nếu phiên IDE đang mở còn cache RAM agent `0.103.0`) — Test: `py -3 -X utf8 scripts/tdq_test.py tron-bo --workers 6 --fresh --reuse off && py -3 -X utf8 scripts/token_budget.py --kiem`
  - Req: `§6 Q1–Q5` · Ngoài phạm vi: Không sửa code trừ khi phát hiện lỗi hồi quy (khi đó mở task `QCn.x`)
  - Chạm: `docs/tdq/qc/2026-11-21-1253-fix-subagent-tools-bump.md`
  - Cần: `T4.1`
  - Giao tiếp: Consumes: toàn bộ thay đổi `P1`–`P3` | Produces: biên bản QC hoàn chỉnh PASS `Q1`–`Q5`
  - Neo & Công cụ: `run_command` chạy `tdq_test.py tron-bo --workers 6 --fresh --reuse off`, `tdq_test.py so`, `token_budget.py --kiem`, `doc_lint.py`; `invoke_subagent` (`tdq-qc-tester` hoặc `self` nếu còn cache IDE); `Edit` cập nhật `docs/tdq/qc/2026-11-21-1253-fix-subagent-tools-bump.md`
  - Trước → Sau: Chưa có kết quả `tron-bo` trên bản vá `0.103.1` → đạt `0 failed`, `bo_sot == 0` và hoàn tất QC độc lập
  - Tiêu chí chấp nhận (EARS): KHI chạy xong `tdq_test.py tron-bo` và `tdq_test.py so`, HỆ THỐNG PHẢI đạt `0 failed`, `bo_sot == 0`, `token_budget.py --kiem` `0` lỗi và `0` rác trên `2` máy SSH
  - Logic cốt lõi: Chạy `tron-bo --workers 6 --fresh --reuse off` không sửa đồng thời file repo; nếu có race worktree/lock giữa các worker thì chạy lại module trượt bằng `--workers 2`/`1` để xác định lỗi môi trường hay lỗi code; chạy `doc_lint.py` và cử agent QC độc lập kiểm lại bằng chứng `Q1`–`Q5`
  - Ca góc hiểm & Assert: Kiểm `bo_sot == 0` và ghi rõ kết quả từng test thực chạy trong biên bản QC

**Xong P4 khi**: `tdq_test.py tron-bo` đạt `0 failed` (`bo_sot == 0`), `token_budget.py --kiem` + `doc_lint.py` `0` lỗi, `2` máy SSH sạch `0` tàn dư và QC độc lập PASS `Q1`–`Q5`.

## P5 — Cài đặt Antigravity User-Level `0.103.1`, Kiểm Subagent & Xuất bản `main` + Tag `v0.103.1`

- [ ] **T5.1** (e5m) Ghi `mtime` trước của `~/.claude/plugins/installed_plugins.json`, chạy `py -3 -X utf8 install.py` cài gói `0.103.1` chỉ ra `C:\Users\admin\.gemini\config\plugins\tdq-workflow-agy` (giữ nguyên bọc Caveman `3` server + RTK), kiểm chứng `agy.EXE plugin validate --strict`, `agy.EXE plugin list`, xác nhận `0/8` file `agents/tdq-*.md` tại `~/.gemini/` chứa tool cấm, đối chiếu `~/.claude/` không đổi `mtime`, và gọi thử `invoke_subagent(TypeName="tdq-explorer")` để kiểm chứng runtime (ghi nhận rõ trạng thái RAM cache nếu phiên IDE hiện tại chưa restart) — Test: `agy.EXE plugin validate C:\Users\admin\.gemini\config\plugins\tdq-workflow-agy --strict --json && agy.EXE plugin list`
  - Dùng: `tdq-setup`, `tdq-checkportable`
  - Để: kiểm tra môi trường tìm kiếm/hướng dẫn user-level (`tdq-setup`) và tính toàn vẹn gói plugin đã cài tại `~/.gemini/` (`tdq-checkportable`) mà không ghi đè `~/.claude/CLAUDE.md`
  - Ra: xác nhận cấu hình `~/.gemini/` đồng bộ `0.103.1` cùng Caveman và RTK intact
  - Kiểm: `py -3 -X utf8 scripts/tdq_lsp.py check` và đọc `~/.gemini/GEMINI.md` giữ nguyên block `<!-- TDQ:TOOLS -->`
  - Không dùng cho: chỉnh sửa `~/.claude/CLAUDE.md` hoặc `~/.claude/plugins/`
  - Dùng: `agy-customizations`, `antigravity-guide`, `plugin`
  - Để: đối chiếu cấu trúc plugin user-level (`~/.gemini/config/plugins/`), `mcp_config.json` và cơ chế nạp agent frontmatter của Antigravity
  - Ra: bản cài live `C:\Users\admin\.gemini\config\plugins\tdq-workflow-agy` ở `0.103.1` `enabled` và kiểm gọi thử subagent
  - Kiểm: `agy.EXE plugin validate C:\Users\admin\.gemini\config\plugins\tdq-workflow-agy --strict --json` trả `findings == []` và `agy.EXE plugin list` hiện `0.103.1`
  - Không dùng cho: cài thêm plugin từ marketplace hoặc sửa cấu hình Codex
  - Req: `§1, §2#6, §3c B5, §6 Q6` · Ngoài phạm vi: `GIỮ NGUYÊN` toàn bộ `~/.claude/` và `~/.codex/` (`mtime` của `installed_plugins.json` giữ nguyên `1795000633.190871`)
  - Chạm: `docs/tdq/qc/2026-11-21-1253-fix-subagent-tools-bump.md`
  - Cần: `T4.2`
  - Giao tiếp: Consumes: `plugins/tdq-workflow-agy/` (`0.103.1`) đã qua QC | Produces: bản cài live `~/.gemini/` `0.103.1` sạch `call_mcp_tool` và kết quả kiểm gọi `invoke_subagent` trong QC
  - Neo & Công cụ: `run_command` chụp `mtime`, chạy `install.py`, kiểm `agy.EXE plugin validate`, `agy.EXE plugin list`, quét `8/8` file `~/.gemini/config/plugins/tdq-workflow-agy/agents/tdq-*.md`; gọi `invoke_subagent(TypeName="tdq-explorer")`; `Edit` cập nhật `Q6` vào `docs/tdq/qc/2026-11-21-1253-fix-subagent-tools-bump.md`
  - Trước → Sau: `~/.gemini/` chạy `0.103.0` (`8/8` agents chứa `call_mcp_tool`) → `0.103.1` (`0/8` agents chứa tool cấm, Caveman `3` server nguyên vẹn)
  - Tiêu chí chấp nhận (EARS): KHI cài xong `install.py`, HỆ THỐNG PHẢI trả `findings == []` tại `~/.gemini/config/plugins/tdq-workflow-agy`, `plugin.json["version"] == "0.103.1"`, `0` tool cấm trong `8/8` agent đã cài, `mcp_config.json` giữ bọc `tdq_mcp_shrink.py` trên `3` server và `mtime` `~/.claude/plugins/installed_plugins.json` không đổi
  - Logic cốt lõi: Đo `mtime` `~/.claude/`, chạy `install.py`, kiểm `agy plugin validate` + `agy plugin list` + `8/8` file agent trên đĩa + `mcp_config.json`, gọi thử `invoke_subagent(TypeName="tdq-explorer")` để đo hành vi live trong phiên hiện tại (nếu IDE còn cache catalog `0.103.0` trong RAM trước khi restart thì ghi rõ vào mục `Giới hạn` của QC và Report để người dùng kiểm sau `1` lần restart)
  - Ca góc hiểm & Assert: `assert after_mtime == before_mtime` và `assert forbidden_hits == 0` trên cả `8` file agent tại `~/.gemini/`

- [ ] **T5.2** (e4m) Sau khi người dùng duyệt `"commit"` ở cuối `report`, commit sạch trên nhánh `bugfix/fix-subagent-tools-bump`, merge `--no-ff` vào `dev`, xóa nhánh request, chạy `py -3 -X utf8 scripts/build_portable.py --sinh-main --nguon dev --nhanh-dich main`, gắn annotated tag `v0.103.1` trên `main` (tuyệt đối không `git push`, không thêm trailer `Co-Authored-By:`) và khóa báo cáo + Archify HTML — Test: `git show main:.claude-plugin/plugin.json && git log -1 --format="%H" v0.103.1 && git rev-parse main`
  - Req: `§1, §2#7, §3c B5, §6 Q7` · Ngoài phạm vi: Không chạy `git push` lên remote (`3a`); không thêm trailer `Co-Authored-By:` vào commit/tag
  - Chạm: `docs/tdq/reports/2026-11-21-1253-fix-subagent-tools-bump.md`
  - Cần: `T5.1`
  - Giao tiếp: Consumes: nhánh `dev` đã gộp sạch `0.103.1` | Produces: nhánh local `main`, tag `v0.103.1`, báo cáo `.md` + Archify HTML `HTTP 200` qua Tailscale
  - Neo & Công cụ: `run_command` chạy `git merge --no-ff`, `scripts/build_portable.py --sinh-main --nguon dev --nhanh-dich main`, `git tag -a v0.103.1 main -m "Release v0.103.1: fix AGY subagent tool registry & 3-OS binaries"`; `Write` tạo `docs/tdq/reports/2026-11-21-1253-fix-subagent-tools-bump.md` và render Archify HTML
  - Trước → Sau: `main` và tag ở `v0.103.0` (`38f7ce6`) → `main` ở `0.103.1` và tag `v0.103.1` khớp `main` HEAD
  - Tiêu chí chấp nhận (EARS): KHI chạy xong `--sinh-main` và gắn tag `v0.103.1`, HỆ THỐNG PHẢI cho `git show main:.claude-plugin/plugin.json` chứa `"version": "0.103.1"` và `git log -1 --format="%H" v0.103.1 == git rev-parse main`
  - Logic cốt lõi: Xuất `report` (`.md` + Archify HTML qua Tailscale `HTTP 200`), dừng chờ `"commit"` → sau khi duyệt commit thì merge `--no-ff` vào `dev`, chạy `--sinh-main --nguon dev --nhanh-dich main`, tạo annotated tag `v0.103.1` trên `main`, cập nhật hash/trạng thái báo cáo, refresh binding và đặt `phase=idle`
  - Ca góc hiểm & Assert: Kiểm nhánh `main` chỉ giữ phần lõi runtime (không có `docs/tdq/`, `tests/`, `hooks/rust/`) và đối chiếu hash bằng `git log -1 --format="%H" v0.103.1` thay vì `^{commit}` để tránh lỗi dấu `^` trên PowerShell

**Xong P5 khi**: Bản cài `~/.gemini/` (`0.103.1`) PASS `Q6`, nhánh `main` + tag `v0.103.1` PASS `Q7`, và báo cáo `.md` + Archify HTML (`HTTP 200` trên Tailscale) hoàn tất.

## Cụm song song

- **Cụm 1 (Khởi đầu — Sóng 1):** `T1.1` (vá compiler `skills_and_agents.py`, `tdq-explorer.md`, test âm tính), `T2.1` (bump manifests/docs `0.103.1`) và `T2.2` (Rust Windows `0.103.1`) chạm vùng file tách rời nên chạy được song song.
- **Cụm 2 (SSH 2 OS — Sóng 2, sau `T2.2`):** `T2.3` (`ubuntu-100-95`) và `T2.4` (`mbair`) chạy trên `2` máy SSH tách biệt và ghi ra `2` nhị phân khác nhau trong `plugins/tdq-workflow-agy/bin/` nên chạy song song.
- **Cụm 3 (Đóng gói, QC, Cài đặt & Release — Sóng 3–7, tuần tự):** `T3.1` → `T4.1` → `T4.2` → `T5.1` → `T5.2` có phụ thuộc cứng dữ liệu đầu vào/đầu ra và cổng `"commit"` nên chạy tuần tự.

## Luật file nóng (một file, nhiều task chạm)

- `docs/tdq/qc/2026-11-21-1253-fix-subagent-tools-bump.md` là file nóng duy nhất được `T4.1` tạo mới, rồi `T4.2` và `T5.1` cập nhật nối tiếp theo chuỗi `Cần:` tuần tự (một chủ ghi tại từng thời điểm). Không có file mã nguồn nào bị `2` task cùng sóng chạm đồng thời.

## Definition of Done

- [ ] Q1 Vá `_READONLY_TOOLS` / `_WRITER_TOOLS`, `tdq-explorer.md` & test âm tính: `8/8` tệp `plugins/tdq-workflow-agy/agents/tdq-*.md` sạch `call_mcp_tool`/`grep_search`/`find_by_name`/`list_dir` ở `tools:`, không lặp `write_file` — `py -3 -X utf8 -m pytest tests/test_agent_frontmatter.py -q`
- [ ] Q2 Manifest, `README.md`, `UPSTREAM-TRACE.md` & `CHANGELOG.md` (`<= 500` dòng) đồng bộ `0.103.1` — `py -3 -X utf8 -m pytest tests/test_docs_consistency.py tests/test_adapter_host.py -q && py -3 -X utf8 scripts/doc_lint.py CHANGELOG.md`
- [ ] Q3 Crate Rust `0.103.1` & `3` nhị phân native thật (`Windows`, `Linux musl`, `macOS ARM64`) PASS `cargo test`, `clippy`, parity/lock, mô phỏng SSH và `2` máy SSH sạch `0` tàn dư — `cargo test --manifest-path hooks/rust/tdq-dispatch/Cargo.toml && py -3 -X utf8 -m pytest tests/test_rust_dispatch_parity.py tests/test_rust_lock_safety.py tests/test_remote_linux_simulation.py tests/test_remote_mac_simulation.py -q`
- [ ] Q4 Compiler & gói plugin `plugins/tdq-workflow-agy/` (`v0.103.1`) đạt chuẩn nghiêm ngặt — `py -3 -X utf8 tools/build_agy_plugin.py --upstream . && agy.EXE plugin validate plugins/tdq-workflow-agy --strict --json && py -3 -X utf8 scripts/token_budget.py --kiem`
- [ ] Q5 Bộ kiểm thử toàn repo (`muc_qc = full`) đạt `0 failed` (`bo_sot == 0`) & QC độc lập PASS — `py -3 -X utf8 scripts/tdq_test.py tron-bo --workers 6 --fresh --reuse off`
- [ ] Q6 Antigravity user-level (`~/.gemini/config/plugins/tdq-workflow-agy`) chạy `0.103.1` sạch `call_mcp_tool` trong `8/8` agents, giữ nguyên Caveman/RTK, không chạm `~/.claude/` & kiểm gọi subagent — `agy.EXE plugin validate C:\Users\admin\.gemini\config\plugins\tdq-workflow-agy --strict --json && agy.EXE plugin list`
- [ ] Q7 Nhánh phát hành local `main` (`--sinh-main` từ `dev`) & annotated tag `v0.103.1` khớp `main` HEAD, không `git push` — `git show main:.claude-plugin/plugin.json && git log -1 --format="%H" v0.103.1 && git rev-parse main`
