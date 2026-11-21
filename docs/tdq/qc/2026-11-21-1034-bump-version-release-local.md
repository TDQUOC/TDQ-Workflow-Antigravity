# QC — Bump Version `0.103.0`, Build 3-OS Rust, Release `main` & Cập nhật Antigravity Local

Ngày: 2026-11-21 · Spec: ../spec/2026-11-21-1034-bump-version-release-local.md · Plan: ../plan/2026-11-21-1034-bump-version-release-local.md · Vòng: 1 (`muc_qc=full`)
Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

| # | Hạng mục | Lệnh đã chạy | Kết quả | PASS/FAIL |
|---|---|---|---|---|
| Q1 | Manifest, `README.md`, `UPSTREAM-TRACE.md`, `CHANGELOG.md` (`<= 500` dòng) & `docs/CHANGELOG-archive-3.md` đồng bộ `0.103.0` | `py -3 -X utf8 -m pytest tests/test_docs_consistency.py tests/test_adapter_host.py -q && py -3 -X utf8 scripts/doc_lint.py CHANGELOG.md docs/CHANGELOG-archive-3.md README.md UPSTREAM-TRACE.md` | `22 passed, 24 subtests passed in 0.54s`; `doc_lint` `0` lỗi; `CHANGELOG.md` `461 <= 500` dòng (`0.60.0`–`0.61.0` ở `archive-3` `110` dòng) | PASS |
| Q2 | Crate Rust `0.103.0` & 3 nhị phân native thật (`Windows`, `Linux musl`, `macOS ARM64`) PASS `cargo test`, `clippy`, parity/lock và simulation SSH | `cargo test` (3 OS) + `cargo clippy --all-targets -- -D warnings` + `pytest test_rust_dispatch_parity.py test_rust_lock_safety.py test_remote_linux_simulation.py test_remote_mac_simulation.py -q` + `TDQ_LOG=1/0` | Win/Linux/Mac mỗi OS `29 passed`; `clippy` `0` warning; `test_build_portable` + parity `84 passed`; simulation Linux `1 passed`, Mac `1 passed`; header `MZ`/`ELF`/`Mach-O`; `TDQ_LOG=0` `stderr_len=0` | PASS |
| Q3 | Hai máy test SSH (`ubuntu-100-95`, `mbair`) sạch `0` tàn dư sau build & test | `ssh ubuntu-100-95 "ls -d /tmp/tdq* /tmp/tdq_dispatch* ~/tdq* 2>/dev/null \| wc -l"` & `ssh mbair "ls -d /tmp/tdq* ~/tdq* 2>/dev/null \| wc -l"` | `0` trên `ubuntu-100-95` (đã dọn cả `/home/ubuntu/tdq-dispatch` & `/tmp/tdq_dispatch.tar.gz`) · `0` trên `mbair` | PASS |
| Q4 | Compiler & gói plugin `plugins/tdq-workflow-agy/` (`v0.103.0`) đạt chuẩn nghiêm ngặt | `py -3 -X utf8 tools/build_agy_plugin.py --upstream . && agy.EXE plugin validate plugins/tdq-workflow-agy --strict --json && py -3 -X utf8 scripts/token_budget.py --kiem` | `"status": "OK"` (`ast_checked_py: 84`, `md_checked_budget: 22`); `"findings": []` (`8` agents, `6` hooks, `3` mcpServers, `10` rules, `12` skills); `token_budget` exit `0`; không tồn tại `prebuilt/` | PASS |
| Q5 | Bộ kiểm thử toàn repo (`muc_qc = full`) đạt `0 failed` (`bo_sot == 0`) & QC độc lập PASS | `py -3 -X utf8 scripts/tdq_test.py tron-bo --workers 1 --fresh --reuse off && py -3 -X utf8 scripts/tdq_test.py so` + `tdq-qc-tester` (`37328511`) | `4603 passed, 36 skipped, 2892 subtests passed in 1332.27s (0:22:12)` (`tests_run=4639`, `tron_bo=1/2`, `bo_sot=0`); `tdq-qc-tester` → `VERDICT: PASS everything` (`Q1`–`Q5`) | PASS |
| Q6 | Nhánh phát hành local `main` (`--sinh-main` từ `dev`) & annotated tag `v0.103.0` hợp lệ, không `git push` | `py -3 -X utf8 scripts/build_portable.py --sinh-main --nguon HEAD --dry-run` (chính thức chạy ngay tại `T5.2` sau khi user chốt `"commit"` + merge `--no-ff` vào `dev`) | `dry-run HEAD@c3b2a0a → main · kept=190 dropped=6944` (`TDQ_LOG=1` on / `0` silent); chưa commit/push theo quy tắc giữ cây tới khi user xác nhận | CHỜ COMMIT (`T5.2`) |
| Q7 | Antigravity user-level (`~/.gemini/config/plugins/tdq-workflow-agy` + `~/.gemini/GEMINI.md`) chạy `0.103.0` nguyên Caveman/RTK và không chạm `~/.claude/` | `py -3 -X utf8 install.py && agy.EXE plugin validate C:\Users\admin\.gemini\config\plugins\tdq-workflow-agy --strict --json && agy.EXE plugin list` | `253 files` installed, `"findings": []`, `enabled, 0.103.0`, `mcp_config.json` bọc `tdq_mcp_shrink.py` (`lsp`, `chrome-devtools`, `tavily-primary`), `GEMINI.md` có dòng `1145` & giữ `Ngôn ngữ trong chat`, `~/.claude/plugins/installed_plugins.json` giữ `mtime` `2026-11-18T18:17:13.1908711+07:00` | PASS |
| QC-F1 | Trọn bộ `222` module sau toàn bộ thay đổi mã nguồn/cấu hình | `py -3 -X utf8 scripts/tdq_test.py tron-bo --workers 1 --fresh --reuse off` | `4603 passed, 36 skipped, 2892 subtests passed`, `bo_sot=0`, `result.json` mới hơn mọi file sửa (`11:29:34 >= 11:02:52`) | PASS |
| QC-F2 | Kiểm thử đơn vị, hồi quy vùng chạm & kiểm chứng nhị phân sống | `pytest tests/test_agy_plugin_validate.py tests/test_rust_dispatch_parity.py tests/test_rust_lock_safety.py tests/test_build_portable.py -q` + live binary probe | `55 passed` (AGY + Rust parity/lock) + `84 passed` (`test_build_portable` + parity); `live_rc: 0`, `{"decision": "allow"}`, `stderr_len: 0` | PASS |
| QC-F3 | Ràng buộc kiến trúc `docs/kien-truc.md` (`skills/` dùng chung 4 host, không bundle thừa) | `py -3 -X utf8 -m pytest tests/test_kien_truc.py tests/test_muc_qc_qc_md.py tests/test_approve_do_truoc.py -q` | `29 passed, 23 subtests passed in 4.81s`; `doc_lint.py` (`7` files) `0 violation(s)` | PASS |
| QC-F4 | Clean Code Self-check (`clean-code.md`), `py_compile`, `clippy` | `py -3 -X utf8 -m py_compile ...` + rà `SRP / OCP / LSP / ISP / DIP` (`ruff` chưa cài trên PATH) | `py_compile` exit `0`; `clippy` `0` warning; đạt `5/5` SOLID (`ruff: not checked yet`) | PASS |

---

## Bằng chứng & Chi tiết Kỹ thuật

### Q1 & Q4 — Manifest, Changelog (`461 <= 500` dòng) & Plugin AGY `0.103.0`

- Toàn bộ `.claude-plugin/plugin.json`, `.codex-plugin/plugin.json`, `hooks/rust/tdq-dispatch/Cargo.toml`, `hooks/rust/tdq-dispatch/Cargo.lock`, `tools/patches/agy_manifests.py`, `tools/patches/__init__.py`, `tools/build_agy_plugin.py`, `plugins/tdq-workflow-agy/plugin.json`, `plugins/tdq-workflow-agy/manifest.json`, `README.md` và `UPSTREAM-TRACE.md` đều ghi `0.103.0`.
- Lưu ý số liệu `README.md`: giữ `4602 passed` (mốc vừa chốt ở `dev` trước khi thêm `1` test khóa mới `test_v2_version_synced_with_claude_plugin` trong `T3.1`, nâng tổng thực chạy sau build lên `4603 passed, 36 skipped / 4639 collected`).
- `docs/CHANGELOG-archive-3.md` nhận trọn phần `0.61.0`–`0.60.0` (`110` dòng), giúp `CHANGELOG.md` sau khi thêm mục `## 0.103.0 — 2026-11-21` còn `461` dòng (`doc_lint.py` exit `0`).
- Test Red → Green ở `T3.1`: `test_v2_version_synced_with_claude_plugin` (`tests/test_agy_plugin_validate.py:244-256`) Fail với `AssertionError: assert '0.102.0' == '0.103.0'` trước khi nâng `PLUGIN_VERSION`, sau đó rebuild `tools/build_agy_plugin.py --upstream .` → PASS `16 passed, 51 subtests passed` (`tests/test_agy_plugin_validate.py tests/test_agent_frontmatter.py`).

### Q2 & Q3 — Rust `0.103.0` trên 3 OS thật & Dọn sạch SSH

- **Windows (`tdq-dispatch.exe`):** `1,967,104` bytes · SHA-256 `BAB071B154F12112F86E16448313934956FA9E463D2B1E341C8DE27E28C41569` (khớp `target/release/tdq-dispatch.exe`) · `cargo test` `29 passed` · `cargo clippy` `0` warning · boundary `not-json` → exit `0` `{"decision":"allow"}` · `BogusEvent` → exit `0` `{}`.
- **Linux `ubuntu-100-95` (`tdq-dispatch-linux-x86_64`):** `2,422,392` bytes · SHA-256 `1BAFFFBDE86E71B8D80B1087364F47DBFDE49C2A13247157955084DEBC75E463` · `ELF 64-bit LSB pie executable, x86-64, static-pie linked, stripped` · `cargo test` `29 passed` · `test_remote_linux_simulation.py` `1 passed`.
- **macOS `mbair` (`tdq-dispatch-darwin-arm64`):** `1,845,840` bytes · SHA-256 `90CFDE7351E9864462AD17C2970BBEBA36836FC66FE4BB1166ABADE485CBF7F8` · `Mach-O 64-bit executable arm64` · `cargo test` `29 passed` · `test_remote_mac_simulation.py` `1 passed`.
- **SSH Cleanup hậu kiểm trực tiếp trong pha QC:** `ssh ubuntu-100-95` và `ssh mbair` đều trả `0` mục `/tmp/tdq* /tmp/tdq_dispatch* ~/tdq*` (`tdq-qc-tester` cũng xác nhận lại `0` trên cả 2 máy).

### Q7 — Bản cài User-Level Antigravity (`~/.gemini/`)

- `py -3 -X utf8 install.py` cài `253 files` ra `C:\Users\admin\.gemini\config\plugins\tdq-workflow-agy`, tự giữ Caveman wrapper `tdq_mcp_shrink.py` trên cả `3` server (`lsp`, `chrome-devtools`, `tavily-primary`), kiểm `rtk (1.2.0) & rg ready`, kích hoạt `tdq-workflow-agy (enabled, 0.103.0)`.
- `C:\Users\admin\.gemini\GEMINI.md` giữ nguyên tool Antigravity (`start_lsp`, `/plan`, `ask_question`), khối Tailscale Serve, khối `## Ngôn ngữ trong chat`, `1` cặp marker `<!-- TDQ:TOOLS -->` / `<!-- /TDQ:TOOLS -->` duy nhất, và bổ sung dòng chuẩn trình bày mặc định `Mặc định cho cả spec, plan và report...`.
- `C:\Users\admin\.claude\plugins\installed_plugins.json` giữ nguyên `LastWriteTime = 2026-11-18T18:17:13.1908711+07:00`.

### QC-F4 — Clean Code Self-check (`clean-code.md`)

1. **SRP:** Đạt — M1 (`manifests/CHANGELOG`), M2 (`Cargo.toml` & SSH 3-OS build), M3 (`tools/patches/` & `build_agy_plugin.py`), M4 (`~/.gemini/`) tách bạch hoàn toàn trách nhiệm; không trộn logic mới vào dispatcher Rust.
2. **OCP:** Đạt — Đưa lịch sử cũ ra `docs/CHANGELOG-archive-3.md` và cập nhật tham số version qua hằng số `PLUGIN_VERSION` / `Cargo.toml` thay vì rẽ nhánh code.
3. **LSP:** Đạt — Không làm gãy chữ ký hay hợp đồng giao diện bất kỳ module CLI, Python hook hoặc binary `tdq-dispatch --event <Event>` nào.
4. **ISP:** Đạt — Test mới `test_v2_version_synced_with_claude_plugin` chỉ đọc 2 manifest JSON cần đối chiếu, không kéo phụ thuộc nặng.
5. **DIP:** Đạt — Mọi bước build/install/release dùng đúng công cụ chuẩn sẵn có (`build_agy_plugin.py`, `install.py`, `build_portable.py`, `tdq_state.py`), bật log `TDQ_LOG=1` mặc định và tắt sạch ở `TDQ_LOG=0`.

## Phát hiện & Lệch spec chờ duyệt

- **Lệch spec chờ duyệt:** `0` (`py -3 -X utf8 scripts/tdq_state.py lech list` → `0 item(s), 0 pending`).
- **Ghi nhận ngoài phạm vi bump version (pre-existing từ `0.102.0`, ghi vào `Giới hạn` của Report):**
  1. `tdq-qc-tester` & thực nghiệm runtime ghi nhận `tools/patches/skills_and_agents.py:28-47` đưa `call_mcp_tool`, `grep_search`, `find_by_name`, `list_dir` vào frontmatter `agents/*.md` của plugin `plugins/tdq-workflow-agy/` (và `tdq-explorer.md:14` lặp chuỗi `write_file`); khi gọi trực tiếp agent mới chưa cache (`tdq-security-reviewer`), runtime Antigravity báo `unknown component: tool "call_mcp_tool" not found in registry` (trong khi `.agents/agents/tdq-qc-tester/agent.md` đã cache trước đó chạy bình thường và `agy plugin validate --strict` vẫn trả `findings: []`). Không chỉnh `skills_and_agents.py` trong đợt bump version `0.103.0` để tránh đổi scope ngoài spec đã duyệt; nên tách 1 request fix riêng sau release này.
  2. `ruff` chưa có trên `PATH` (`ruff: not checked yet`); thay thế bằng `cargo clippy -- -D warnings`, `py_compile`, `tools/build_agy_plugin.py` (kiểm AST `84` file Python) và `4.639` bài test thật.

## Kết luận

**PASS `Q1`–`Q5`, `Q7` và `QC-F1`–`QC-F4`** (`tdq-qc-tester` xác nhận `VERDICT: PASS everything`). Còn duy nhất `Q6` (`T5.2`: merge `--no-ff` về `dev`, `build_portable.py --sinh-main`, gắn tag `v0.103.0`) sẵn sàng thi hành ngay sau khi người dùng xác nhận `"commit"` tại cổng Report.
