# PLAN — Nhánh release Antigravity đa hệ điều hành và đồng bộ remote

Ngày: 2026-11-22 · Spec: ../spec/2026-11-22-1033-nhanh-release-agy-da-os.md (bản 1.0, ĐÃ DUYỆT)
Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md
Mode thực thi: main — đo thực tế bằng tdq_bench.py simulate (--he-so-agent 1.5): main 12.2 phút vs đội 12.3 phút (Winner: main, gap 0.0 phút qua 4 wave, 6 task) (ĐỀ XUẤT, user chốt lúc duyệt)
Trạng thái plan: HOÀN THÀNH

> **Tóm tắt dễ hiểu:** Kế hoạch chia thành ba pha qua bốn đợt thực thi không đụng chung tệp để hoàn thiện bản phát hành Antigravity đa hệ điều hành. Đợt đầu chạy song song ba mũi xây bộ khởi chạy Node đa nền tảng, bổ sung lệnh sinh nhánh phát hành sạch bằng Git plumbing và mở rộng cấu hình CI bốn kiến trúc. Các đợt kế tiếp tích hợp vào bộ biên dịch plugin, kiểm chứng trình cài cục bộ và thử cài cô lập trên nhánh phát hành trước khi đẩy đồng bộ lên kho GitHub.

## Mục lục

- Phân bổ Model & Effort
- Quy tắc thi hành (áp cho mọi task)
- Thiết kế Trước vs Sau
- Ràng buộc toàn cục & Bản đồ Sở hữu Hợp đồng (Ownership Map)
- P1 — Xây launcher đa hệ điều hành, lệnh sinh nhánh release và cấu hình CI
- P2 — Tích hợp biên dịch plugin không đường dẫn cứng và tương thích trình cài cục bộ
- P3 — Log & test bắt buộc
- Cụm song song
- Luật file nóng
- Definition of Done

## Phân bổ Model & Effort
<!-- i18n-allow: canonical model/effort plan allocation table -->
> User được quyền đổi `type model` hoặc `effort` lúc duyệt plan. Thang model: [subagent-tuning.md](../../tdq-conventions/references/subagent-tuning.md).

| Pha | Vai trò | Model | Effort | Ghi chú |
|---|---|---|---|---|
| `implement` | `tdq-implementer` (hoặc `main` inline theo lựa chọn cổng mode) | `inherit` | `high` | Triển khai đỏ sang xanh từng task, giữ hàm ngắn dưới 50 dòng và kiểm chặt không đường dẫn cá nhân |
| `qc` | Điều phối chính (`muc_qc = full`) | `inherit` | `high` | Chạy trọn suite kiểm thử, `agy plugin validate --strict`, thử cài cô lập và kiểm ranh giới kiến trúc |
| `report` | Điều phối chính | `inherit` | `high` | Xuất báo cáo 4 phần, sơ đồ Archify HTML qua Tailscale HTTPS, gộp về `dev` và đẩy đồng bộ `origin` |

## Quy tắc thi hành (áp cho mọi task)

1. Thứ tự phase là thứ tự phụ thuộc — không đảo.
2. Mỗi task: đánh `[~]` khi bắt đầu → viết test trước (đỏ) → code → test xanh → đổi sang `[x]` NGAY vào file này. Trạng thái checkbox: `[ ]` chưa làm · `[~]` đang làm · `[x]` xong.
3. Mỗi bước: `tdq_test.py vung-cham`; trọn bộ chỉ ở QC.
4. Lệnh nào chạm state của workflow phải có `TDQ_PROJECT_DIR=<thư mục tạm>` ngay trên chính lệnh đó.
5. QC FAIL → thêm task fix vào mục QC của file này (không cần duyệt lại), loop đến khi pass.
6. Chỉ thực hiện hợp nhất về `dev` và `git push origin dev` + `git push origin release/antigravity` ở cuối pha `report` sau khi toàn bộ QC `full` đạt xanh (theo chấp thuận `5b`).
7. Tuân thủ 6 mã cấm cơ học (ANTI-1 Fake Red, ANTI-2 Blind Assertion, ANTI-3 Dirty State Git, ANTI-4 Late Tick, ANTI-5 Raw Dump, ANTI-6 Broad Area).

## Thiết kế Trước vs Sau

| Khía cạnh | Hiện trạng (Trước) | Thiết kế mới (Sau) |
|---|---|---|
| Luồng thực thi cài từ GitHub | `origin/main` chỉ giữ bản Claude Code, `origin/dev` tụt 27 commit và chứa cả `docs/`/`tests/` | Nhánh `release/antigravity` đặt trực tiếp gói `tdq-workflow-agy` sạch ở thư mục gốc qua Git plumbing |
| Thành phần chạm (`hooks` & `MCP`) | `agy_manifests.py` sinh `bin\tdq-dispatch.exe`, `npx.cmd` và đường dẫn máy `admin` | `agy_launchers.py` sinh `tdq_hook_launcher.mjs` và `tdq_mcp_launcher.mjs` dùng thuần Node.js + `${PLUGIN_ROOT}` / `${PLUGIN_DATA}` |

*Đối chiếu sơ đồ kiến trúc:* Tham chiếu trực tiếp HTML Trước/Sau đã duyệt [2026-11-22-1033-nhanh-release-agy-da-os-preview.html](../spec/2026-11-22-1033-nhanh-release-agy-da-os-preview.html) và manifest `2026-11-22-1033-nhanh-release-agy-da-os-preview.manifest.json`. WBS ánh xạ `T1.1` + `T2.1` vào cụm `hook launcher` / `mcp launcher`, `T1.2` + `T3.1` vào cụm `release/antigravity` → `agy install`; không sinh thiết kế khác ngoài bản đã duyệt.

## Ràng buộc toàn cục & Bản đồ Sở hữu Hợp đồng (Ownership Map)

- Ngôn ngữ: English comments/CLI · `utf8_io` · `TDQ_LOG=0` tắt hoàn toàn log `stderr` · hàm `<= 50` dòng (`cyc <= 10`, `cog <= 15`) · thuần Python/Node.js stdlib (`0` dependency ngoài) · `GIỮ NGUYÊN` toàn bộ chữ ký cũ của `sinh_nhanh_main`, `verify_binary_magic`, `--sync-local-mcp`, `--with-caveman` và không chạm `~/.gemini/config/` thật.

| Hợp đồng / Ký hiệu (§3c) | File & Task sở hữu | Task / File tiêu thụ |
|---|---|---|
| `generate_launchers(plugin_root: Path) -> list[Path]` | `tools/patches/agy_launchers.py` (`T1.1`) | `tools/build_agy_plugin.py` (`T2.1`), `tests/test_agy_launchers.py` (`T1.1`) |
| `resolveBinaryName(platform: string, arch: string) -> string \| null` | `tools/patches/agy_launchers.py` (`T1.1`) | `plugins/tdq-workflow-agy/scripts/tdq_hook_launcher.mjs` (`T2.1`), `tests/test_agy_launchers.py` (`T1.1`) |
| `selectPythonFallback(platform: string) -> Array<{cmd: string, prefix: string[]}>` | `tools/patches/agy_launchers.py` (`T1.1`) | `plugins/tdq-workflow-agy/scripts/tdq_hook_launcher.mjs` (`T2.1`), `tests/test_agy_launchers.py` (`T1.1`) |
| `resolveAgentLspCommand(envPath: string, homeDir: string, platform: string) -> string` | `tools/patches/agy_launchers.py` (`T1.1`) | `plugins/tdq-workflow-agy/scripts/tdq_mcp_launcher.mjs` (`T2.1`), `tests/test_agy_launchers.py` (`T1.1`) |
| `buildSpawnSpec(mode: "lsp" \| "npx", forwardedArgs: string[], platform: string) -> {command: string, args: string[], shell: boolean}` | `tools/patches/agy_launchers.py` (`T1.1`) | `plugins/tdq-workflow-agy/scripts/tdq_mcp_launcher.mjs` (`T2.1`), `tests/test_agy_launchers.py` (`T1.1`) |
| `loc_muc_agy_release(raw_bytes: bytes, prefix: str = "plugins/tdq-workflow-agy/") -> list[bytes]` | `scripts/build_portable.py` (`T1.2`) | `sinh_nhanh_release_agy` (`T1.2`), `tests/test_build_portable.py` (`T1.2`) |
| `sinh_nhanh_release_agy(repo: str, nguon: str = "dev", nhanh_dich: str = "release/antigravity", plugin_prefix: str = "plugins/tdq-workflow-agy/", dry_run: bool = False) -> dict` | `scripts/build_portable.py` (`T1.2`) | CLI `--sinh-release-agy` (`T1.2`), `tests/test_agy_release_e2e.py` (`T3.1`) |

## P1 — Xây launcher đa hệ điều hành, lệnh sinh nhánh release và cấu hình CI

- [x] **T1.1** (e10m) Viết `tools/patches/agy_launchers.py` sinh hai tập lệnh `tdq_hook_launcher.mjs` và `tdq_mcp_launcher.mjs` kèm bộ kiểm thử đơn vị `tests/test_agy_launchers.py` — Test: `py -3 -X utf8 -m pytest tests/test_agy_launchers.py -q`
  - Dùng: `agy-customizations`
  - Để: Đối chiếu quy ước `cwd = <plugin-root>` của hook và biến môi trường `PLUGIN_ROOT`/`PLUGIN_DATA` của MCP, nạp skill TRƯỚC bước đỏ
  - Ra: `tools/patches/agy_launchers.py` và `tests/test_agy_launchers.py`
  - Kiểm: `py -3 -X utf8 -m pytest tests/test_agy_launchers.py -q`
  - Không dùng cho: Không tự ý sửa `~/.gemini/config/` cá nhân hay các tệp ngoài `tools/patches/agy_launchers.py`
  - Req: `§2 #1`, `§3c`, `§4`, `§6 Q1`, `§6 Q2` · Ngoài phạm vi: `GIỮ NGUYÊN` `tools/patches/common_utils.py`
  - Chạm: `tools/patches/agy_launchers.py`, `tests/test_agy_launchers.py`
  - Cần: `Không`
  - Giao tiếp: Consumes: `common_utils.write_utf8` | Produces: `generate_launchers(plugin_root: Path) -> list[Path]` xuất `scripts/tdq_hook_launcher.mjs` và `scripts/tdq_mcp_launcher.mjs`
  - Neo & Công cụ: tạo mới bằng write_file trên `tools/patches/agy_launchers.py` (`generate_launchers`) và `tests/test_agy_launchers.py`
  - Trước → Sau: Chưa có bộ khởi chạy đa hệ điều hành cho hook/MCP → Có cặp launcher ESM thuần Node stdlib định tuyến đúng theo OS/arch kèm fallback Python và log `TDQ_LOG`
  - Tiêu chí chấp nhận (EARS): KHI chạy `node --check` và gọi các hàm export/CLI trên hai tệp `.mjs`, HỆ THỐNG PHẢI thoát `0`, chọn đúng binary cho `win32`/`darwin`/`linux`, bỏ qua stub `WindowsApps`, phân giải `agent-lsp`/`npx.cmd` đúng nền tảng và tắt hẳn `stderr` khi `TDQ_LOG=0`
  - Logic cốt lõi: Cài đặt `resolveBinaryName`, `selectPythonFallback` (kèm fail-open `{}` nếu thiếu cả Rust lẫn Python), `resolveAgentLspCommand` (`PATH` + `~/.local/bin` + `~/.cargo/bin` + Homebrew), `buildSpawnSpec` (`shell: true` cho `npx.cmd` trên `win32`, `shell: false` cho `npx` trên POSIX) và đặt `chmod 0o755` trên POSIX
  - Ca góc hiểm & Assert: Đường dẫn Python chứa `WindowsApps` hoặc thiếu hoàn toàn binary `bin/` → `assert res.returncode == 0` và `assert json.loads(res.stdout) == {}` hoặc trả đúng JSON từ `dispatch.py` giả lập; khi `TDQ_LOG=0` → `assert res.stderr == ""`

- [x] **T1.2** (e10m) Bổ sung `loc_muc_agy_release`, `sinh_nhanh_release_agy` và cờ CLI `--sinh-release-agy` vào `scripts/build_portable.py` kèm kiểm thử trong `tests/test_build_portable.py` — Test: `py -3 -X utf8 -m pytest tests/test_build_portable.py -q -k release`
  - Req: `§2 #4`, `§3c`, `§4`, `§5`, `§6 Q4` · Ngoài phạm vi: `GIỮ NGUYÊN` `la_duong_dan_release`, `loc_muc_ls_tree` và `sinh_nhanh_main`
  - Chạm: `scripts/build_portable.py`, `tests/test_build_portable.py`
  - Cần: `Không`
  - Giao tiếp: Consumes: `_git_text`, `_tao_tree_release`, `plugin_version`, `log` | Produces: `loc_muc_agy_release`, `sinh_nhanh_release_agy` và cờ `--sinh-release-agy`
  - Neo & Công cụ: sửa bằng edit_file trên `scripts/build_portable.py` tại `sinh_nhanh_main` (`L738-780`), `_xay_parser` (`L783-810`), `main` (`L828-854`) và trên `tests/test_build_portable.py` tại `test_release_cli_sinh_main_va_log_service` (`L777-794`)
  - Trước → Sau: `build_portable.py` chỉ sinh nhánh `main` cho Claude Code → Hỗ trợ thêm `--sinh-release-agy` dựng nhánh `release/antigravity` có `plugin.json` ngay tại gốc nhánh không chạm working tree
  - Tiêu chí chấp nhận (EARS): KHI chạy `build_portable.py --sinh-release-agy --nguon dev --nhanh-dich release/antigravity`, HỆ THỐNG PHẢI tạo nhánh có `plugin.json` ở gốc, giữ mode `100755` cho `bin/*` và `scripts/*.mjs`, trả `changed=False` khi chạy lặp không đổi nguồn và báo lỗi mã thoát `1` nếu thiếu `plugin.json`
  - Logic cốt lõi: Lọc các dòng `git ls-tree -r -z` dưới `plugins/tdq-workflow-agy/`, cắt tiền tố để đưa lên gốc, bỏ `__pycache__`/`.pyc`, nâng mode blob `100644` thành `100755` cho `bin/` và `scripts/*.mjs`, kiểm tra bắt buộc có `plugin.json`, rồi gọi `_tao_tree_release` + `commit-tree` + `update-ref`
  - Ca góc hiểm & Assert: Chạy `dry_run=True` không được tạo `refs/heads/release/antigravity`; thiếu `plugins/tdq-workflow-agy/plugin.json` → raise `RuntimeError`; chạy lần 2 liên tiếp → `assert kq2["changed"] is False` và `assert kq2["commit_sha"] == kq1["commit_sha"]`

- [x] **T1.3** (e7m) Mở rộng `.github/workflows/build-rust-hooks.yml` đủ 4 target đa OS, kiểm tra build đồng bộ binary Linux/macOS qua SSH nếu trực tuyến và cập nhật `README-Antigravity.md` — Test: `py -3 -X utf8 -c "import pathlib; w=pathlib.Path('.github/workflows/build-rust-hooks.yml').read_text(encoding='utf-8'); r=pathlib.Path('README-Antigravity.md').read_text(encoding='utf-8'); assert all(t in w for t in ('x86_64-pc-windows-msvc','x86_64-unknown-linux-musl','aarch64-apple-darwin','x86_64-apple-darwin')) and 'release/antigravity' in r and 'v0.105.0' in r"`
  - Req: `§2 #5`, `§2 #6`, `§6 Q5`, `§6 Q6` · Ngoài phạm vi: `GIỮ NGUYÊN` mã nguồn Rust trong `hooks/rust/tdq-dispatch/src/`
  - Chạm: `.github/workflows/build-rust-hooks.yml`, `README-Antigravity.md`, `hooks/rust/tdq-dispatch/prebuilt/`
  - Cần: `Không`
  - Giao tiếp: Consumes: cấu hình SSH `ubuntu-100-95` / `mbair` (nếu online) | Produces: workflow CI 4 target, tài liệu cài đặt `release/antigravity` và binary prebuilt cập nhật (nếu SSH online)
  - Neo & Công cụ: sửa bằng edit_file trên `.github/workflows/build-rust-hooks.yml` (`L20-33`) và `README-Antigravity.md` (`L1-30`); chạy run_command thăm dò SSH không chặn (`ConnectTimeout=5`)
  - Trước → Sau: CI thiếu `x86_64-apple-darwin` và `README-Antigravity.md` còn ghi `v0.97.0` chưa có lệnh cài từ GitHub → CI đủ 4 target, tài liệu ghi rõ `v0.105.0` kèm lệnh cài `agy plugin install` một bước từ `release/antigravity`
  - Tiêu chí chấp nhận (EARS): KHI kiểm tra `.github/workflows/build-rust-hooks.yml` và `README-Antigravity.md`, HỆ THỐNG PHẢI chứa đủ 4 target biên dịch và hướng dẫn cài đặt từ `https://github.com/TDQUOC/TDQ-Workflow-Antigravity/tree/release/antigravity`
  - Logic cốt lõi: Thêm mục `macos-13` / `macos-latest` cross-target `x86_64-apple-darwin` (`tdq-dispatch-darwin-x64`) vào matrix CI; probe SSH `ubuntu-100-95` và `mbair` — máy nào online thì chạy `cargo build --release` đồng bộ về `prebuilt/` và kiểm magic bytes, máy nào offline thì ghi nhận rõ không làm gãy build; cập nhật `README-Antigravity.md`
  - Ca góc hiểm & Assert: Máy SSH ngoại tuyến hoặc timeout `5s` → không treo lệnh, không ghi đè tệp rỗng vào `prebuilt/`; kiểm `assert all(t in workflow_text for t in ('x86_64-apple-darwin', 'tdq-dispatch-darwin-x64'))`

**Xong P1 khi**: Cặp launcher `.mjs`, hàm `sinh_nhanh_release_agy`, workflow CI 4 target và `README-Antigravity.md` đều hoàn tất và vượt test riêng từng task.

## P2 — Tích hợp biên dịch plugin không đường dẫn cứng và tương thích trình cài cục bộ

- [x] **T2.1** (e10m) Cập nhật `tools/patches/agy_manifests.py` và `tools/build_agy_plugin.py` để sinh `hooks.json` + `mcp_config.json` dùng launcher đa OS không đường dẫn cá nhân, biên dịch lại `plugins/tdq-workflow-agy/` và đồng bộ `tests/test_command_gate.py` — Test: `py -3 -X utf8 -m pytest tests/test_command_gate.py -q`
  - Dùng: `plugin`
  - Để: Đảm bảo cấu trúc `plugin.json`, `hooks.json`, `mcp_config.json` tuân thủ schema Antigravity và không rò rỉ đường dẫn máy cá nhân, nạp skill TRƯỚC bước đỏ
  - Ra: `plugins/tdq-workflow-agy/hooks.json`, `plugins/tdq-workflow-agy/mcp_config.json`, `plugins/tdq-workflow-agy/scripts/tdq_hook_launcher.mjs`, `plugins/tdq-workflow-agy/scripts/tdq_mcp_launcher.mjs`
  - Kiểm: `agy.EXE plugin validate plugins/tdq-workflow-agy --strict --json`
  - Không dùng cho: Không gọi RPC thay đổi trạng thái hay ghi vào `~/.gemini/config/config.json`
  - Req: `§2 #2`, `§3`, `§6 Q1`, `§6 Q2`, `§6 Q3` · Ngoài phạm vi: `GIỮ NGUYÊN` `generate_plugin_json`, `generate_logo_svg`, `_stage_rust_binaries` (chỉ thêm hỗ trợ nhận diện `tdq-dispatch-darwin-x64` nếu có sẵn)
  - Chạm: `tools/patches/agy_manifests.py`, `tools/build_agy_plugin.py`, `plugins/tdq-workflow-agy/`, `tests/test_command_gate.py`
  - Cần: `T1.1`, `T1.3`
  - Giao tiếp: Consumes: `agy_launchers.generate_launchers` (`T1.1`) | Produces: gói biên dịch `plugins/tdq-workflow-agy/` sạch đa hệ điều hành
  - Neo & Công cụ: sửa bằng edit_file trên `tools/patches/agy_manifests.py` tại `_hook_cmd` (`L90-100`), `generate_mcp_config` (`L151-171`), `generate_two_tier_rules` (`L174-215`); trên `tools/build_agy_plugin.py` tại `build` (`L202-271`) và `_EXTERNAL_UPSTREAM` (`L25`); trên `tests/test_command_gate.py` (`L210-235`)
  - Trước → Sau: `mcp_config.json` và `hooks.json` đóng cứng đường dẫn máy `admin` và `.exe` → Chuyển hoàn toàn sang `node scripts/tdq_hook_launcher.mjs` và `node` + `${PLUGIN_ROOT}/scripts/tdq_mcp_launcher.mjs` + `${PLUGIN_DATA}/chrome-devtools-profile`, đồng thời bỏ đường dẫn cứng `admin` ở `_EXTERNAL_UPSTREAM` (chuyển sang `TDQ_EXTERNAL_UPSTREAM` env tùy chọn) và cập nhật dòng lệnh Python đa OS trong `rules/AGENTS.md`
  - Tiêu chí chấp nhận (EARS): KHI chạy `tools/build_agy_plugin.py` và `agy.EXE plugin validate plugins/tdq-workflow-agy --strict --json`, HỆ THỐNG PHẢI đạt `status == "OK"`, `findings == []`, `0` chuỗi `Users\admin` / `Users/admin` / `npx.cmd` / `bin\tdq-dispatch.exe` trong toàn bộ `plugins/tdq-workflow-agy/`
  - Logic cốt lõi: `_hook_cmd` trả `"node scripts/tdq_hook_launcher.mjs --event <event_name>"` trên mọi hệ điều hành; `generate_mcp_config` xuất 3 server qua `"command": "node"` và `"args": ["${PLUGIN_ROOT}/scripts/tdq_mcp_launcher.mjs", "<mode>"]`; `build_agy_plugin.py` gọi `agy_launchers.generate_launchers(stage)` và kiểm `node --check` trên các tệp `.mjs`
  - Ca góc hiểm & Assert: Quét toàn bộ tệp văn bản dưới `plugins/tdq-workflow-agy/` → `assert "Users\\admin" not in text and "Users/admin" not in text and "npx.cmd" not in text`; kiểm `hooks.json` không có ký tự `"` bên trong chuỗi lệnh

- [x] **T2.2** (e8m) Cập nhật `tools/install_agy_plugin.py`, `install.py` và `tests/test_agy_plugin_validate.py` để tương thích hoàn toàn với launcher mới, `--sync-local-mcp` và `--with-caveman` — Test: `py -3 -X utf8 -m pytest tests/test_agy_plugin_validate.py tests/test_installer_rtk_trigger.py -q`
  - Req: `§2 #3`, `§6 Q1`, `§6 Q2`, `§6 Q3` · Ngoài phạm vi: `GIỮ NGUYÊN` giao diện cờ CLI của `install_agy_plugin.py` và `install.py`
  - Chạm: `tools/install_agy_plugin.py`, `install.py`, `tests/test_agy_plugin_validate.py`
  - Cần: `T2.1`
  - Giao tiếp: Consumes: gói `plugins/tdq-workflow-agy/` (`T2.1`) | Produces: trình cài cục bộ giữ nguyên launcher đa OS, cấp quyền `+x` cho binary/launcher và hỗ trợ `--sync-local-mcp` đè riêng mục `lsp` khi người dùng yêu cầu
  - Neo & Công cụ: sửa bằng edit_file trên `tools/install_agy_plugin.py` tại `_ensure_binary_executable_and_hooks` (`L71-104`) và `_sync_local_mcp` (`L113-137`); trên `install.py` tại `_adjust_hooks_for_platform` (`L68-99`); trên `tests/test_agy_plugin_validate.py` tại `test_v1_hooks_json_windows_cmd_c_no_quotes_and_protojson` (`L44-100`) và `test_v1_install_dry_run_and_staged_validate` (`L102-120`)
  - Trước → Sau: Trình cài cục bộ và test validator chỉ nhận tiền tố `bin\tdq-dispatch.exe` / `./bin/tdq-dispatch` → Nhận chuẩn `node scripts/tdq_hook_launcher.mjs --event `, đảm bảo `chmod 0o755` cho `bin/*` và `scripts/*.mjs` trên POSIX, fallback Python khi cả Node lẫn binary đều vắng, và kiểm chứng chạy thật `cmd /c` trên đủ 6 sự kiện
  - Tiêu chí chấp nhận (EARS): KHI chạy `test_agy_plugin_validate.py` và `test_installer_rtk_trigger.py`, HỆ THỐNG PHẢI vượt sạch 100% bài kiểm tra gồm `cmd /c` trên `hooks.json`, staged install kèm `--sync-local-mcp`, cài đè tại chỗ và kiểm magic bytes
  - Logic cốt lõi: Giữ `hooks.json` dùng `node scripts/tdq_hook_launcher.mjs --event ` nếu `shutil.which("node")` có sẵn (chỉ ghi đè fallback Python trực tiếp khi máy cài cục bộ hoàn toàn thiếu `node` và thiếu binary OS); cập nhật `valid_prefixes` và thêm bài kiểm tra không rò rỉ đường dẫn cá nhân trong `test_agy_plugin_validate.py`
  - Ca góc hiểm & Assert: Máy giả lập thiếu cả `node` lẫn binary OS khi cài bằng `install_agy_plugin.py` → tự hạ về fallback Python hợp lệ không lỗi; cài bình thường có `--sync-local-mcp` → chỉ bản đích `staged/mcp_config.json` nhận cấu hình cục bộ còn `plugins/tdq-workflow-agy/mcp_config.json` trong repo giữ nguyên portable

**Xong P2 khi**: `plugins/tdq-workflow-agy/` biên dịch sạch không còn đường dẫn cá nhân, `agy plugin validate --strict --json` đạt `0 findings` và toàn bộ test trình cài cục bộ xanh.

## P3 — Log & test bắt buộc

- [x] **T3.1** (e8m) Viết kiểm thử tích hợp đầu–cuối `tests/test_agy_release_e2e.py` khóa nhật ký `TDQ_LOG` mặc định/tắt, xuất bản nhánh `release/antigravity` thật và cài thử cô lập bằng `agy plugin install` — Test: `py -3 -X utf8 -m pytest tests/test_agy_release_e2e.py -q`
  - Req: `§4`, `§6 Q4`, `§6 Q6` · Ngoài phạm vi: `GIỮ NGUYÊN` toàn bộ `371` tệp trong `~/.gemini/config/` thật của máy hiện tại
  - Chạm: `tests/test_agy_release_e2e.py`
  - Cần: `T1.2`, `T2.2`
  - Giao tiếp: Consumes: `build_portable.sinh_nhanh_release_agy` (`T1.2`), `plugins/tdq-workflow-agy/` (`T2.1`/`T2.2`), `agy.EXE` | Produces: bằng chứng tự động hóa E2E cho log service, nhánh `release/antigravity` và cài đặt cô lập
  - Neo & Công cụ: tạo mới bằng write_file trên `tests/test_agy_release_e2e.py`
  - Trước → Sau: Chưa có bài kiểm thử tự động chứng minh máy khác cài được từ nhánh `release/antigravity` → Có bài test tạo kho Git tạm từ gói vừa build, chạy `--sinh-release-agy`, checkout nhánh `release/antigravity`, chạy `agy plugin validate --strict` và `agy plugin install` với `HOME`/`USERPROFILE` cô lập hoàn toàn
  - Tiêu chí chấp nhận (EARS): KHI chạy `pytest tests/test_agy_release_e2e.py -q`, HỆ THỐNG PHẢI xác nhận: (1) log ISO xuất trên `stderr` mặc định và rỗng khi `TDQ_LOG=0` cho cả 2 launcher lẫn `--sinh-release-agy`, (2) gốc nhánh `release/antigravity` đạt `validate --strict` `0 findings`, (3) `agy plugin install` vào thư mục `HOME` tạm cài đủ `12 skills, 8 agents, 10 rules, 3 mcpServers, 6 hooks` và chạy thử hook sau cài trả JSON hợp lệ, (4) số tệp `~/.gemini/config/` thật trước–sau không đổi
  - Logic cốt lõi: Dựng repo Git tạm chứa bản `plugins/tdq-workflow-agy/` thực tế trên đĩa, chạy `sinh_nhanh_release_agy`, xuất cây nhánh `release/antigravity` ra thư mục sạch, gọi `agy.EXE plugin validate --strict --json` + `agy.EXE plugin install` với `env={"USERPROFILE": tmp_home, "HOME": tmp_home}`, rồi kích hoạt lệnh hook trực tiếp từ thư mục plugin vừa cài trong `tmp_home`
  - Ca góc hiểm & Assert: So khớp số lượng tệp và mtime mới nhất của `~/.gemini/config/` thật trước và sau khi test chạy → `assert after_snapshot == before_snapshot`; kiểm `assert installed_components == {"agents": 8, "hooks": 6, "mcpServers": 3, "rules": 10, "sidecars": 0, "skills": 12}`

**Xong P3 khi**: `tests/test_agy_release_e2e.py` xanh 100%, xác nhận trọn vẹn cả nhật ký `TDQ_LOG` lẫn luồng xuất bản và cài đặt nhánh `release/antigravity` trong môi trường cô lập.

## QC vòng 1 — fix

- [x] **QC1.1** (e2m) Bổ sung `encoding="utf-8"` cho lệnh `subprocess.run` trong `tests/test_agy_launchers.py` (`test_moi_loi_goi_van_ban_deu_khai_encoding`) — Test: `py -3 -X utf8 -m pytest tests/test_ma_hoa_subprocess.py tests/test_agy_launchers.py -q`
  - Chạm: `tests/test_agy_launchers.py`
  - Neo & Công cụ: `edit_file` trên `tests/test_agy_launchers.py` tại `test_generate_launchers_creates_valid_mjs_files` (`L45`)
  - Trước → Sau: Gọi `subprocess.run(..., text=True)` thiếu `encoding=` làm đỏ `test_ma_hoa_subprocess.py` → Khai đủ `encoding="utf-8"` trên mọi lệnh con văn bản
  - Logic cốt lõi: Thêm tham số `encoding="utf-8"` vào lời gọi `subprocess.run(["node", "--check", ...])` để chuẩn UTF-8 trên Windows
  - Tiêu chí & Assert: `pytest tests/test_ma_hoa_subprocess.py -q` trả `thieu == []` và mã thoát `0`
- [x] **QC1.2** (e3m) Cập nhật `tests/test_e2e_workflow.py` phân giải `${PLUGIN_ROOT}` và kiểm chứng live JSON-RPC qua `node ${PLUGIN_ROOT}/scripts/tdq_mcp_launcher.mjs lsp` — Test: `py -3 -X utf8 -m pytest tests/test_e2e_workflow.py -v`
  - Chạm: `tests/test_e2e_workflow.py`
  - Neo & Công cụ: `edit_file` trên `tests/test_e2e_workflow.py` tại `test_v5_live_mcp_agent_lsp_stdio_and_7_companion_extensions` (`L52-84`)
  - Trước → Sau: Kiểm định `Path(lsp["command"]).is_file()` giả định đường dẫn tuyệt đối cũ → Tìm `node` trên `PATH`, mở rộng `${PLUGIN_ROOT}` và bắt tay live JSON-RPC `initialize` + `tools/list` qua `tdq_mcp_launcher.mjs`
  - Logic cốt lõi: Kiểm tra `shutil.which(lsp["command"])`, thay `${PLUGIN_ROOT}` thành `str(PLUGIN_DIR)` trong `args` và chạy kiểm thử stdio JSON-RPC live
  - Tiêu chí & Assert: `pytest tests/test_e2e_workflow.py -v` đạt `2 passed` (`>= 20` MCP tools trả về từ `agent-lsp` qua launcher)

## Cụm song song

Đồ thị phụ thuộc tách thành 4 đợt với `0` tệp giao nhau giữa các task cùng đợt:
- **Đợt 1 (song song 3 task độc lập):** `T1.1` (`agy_launchers.py` + test), `T1.2` (`build_portable.py` + test), `T1.3` (`build-rust-hooks.yml` + `README-Antigravity.md` + `prebuilt/`) — hoàn toàn rời nhau.
- **Đợt 2 (tuần tự sau `T1.1` và `T1.3`):** `T2.1` (`agy_manifests.py`, `build_agy_plugin.py`, biên dịch `plugins/tdq-workflow-agy/`, `test_command_gate.py`).
- **Đợt 3 (tuần tự sau `T2.1`):** `T2.2` (`install_agy_plugin.py`, `install.py`, `test_agy_plugin_validate.py`).
- **Đợt 4 (tuần tự sau `T1.2` và `T2.2`):** `T3.1` (`test_agy_release_e2e.py`).

## Luật file nóng

Không có file nóng (`HOT FILE = 0`): mọi tệp và thư mục khai ở dòng `Chạm:` đều thuộc đúng một chủ ghi duy nhất trong toàn bộ kế hoạch.

## Definition of Done

Trỏ về §6 của spec `docs/tdq/spec/2026-11-22-1033-nhanh-release-agy-da-os.md` (mức QC `full`, mỗi dòng kiểm chứng bằng một lệnh thực tế):

- [x] Q1 Launcher hook đa hệ điều hành (`node scripts/tdq_hook_launcher.mjs --event <Event>`) không chứa dấu `"` hay `bin\tdq-dispatch.exe`, chạy xanh qua `cmd /c` trên đủ `6` sự kiện lifecycle và vượt đầy đủ test chọn OS + fallback Python — `py -3 -X utf8 -m pytest tests/test_agy_launchers.py tests/test_agy_plugin_validate.py tests/test_command_gate.py -q`
- [x] Q2 `mcp_config.json` không chứa bất kỳ đường dẫn cá nhân nào (`Users\admin`, `Users/admin`, `npx.cmd`), định tuyến đủ `3` server qua `node` + `${PLUGIN_ROOT}/scripts/tdq_mcp_launcher.mjs` + `${PLUGIN_DATA}/chrome-devtools-profile` và giữ tương thích `--sync-local-mcp` + `--with-caveman` — `py -3 -X utf8 -c "import pathlib; p=pathlib.Path('plugins/tdq-workflow-agy/mcp_config.json').read_text(encoding='utf-8'); assert all(b not in p for b in ('Users\\\\admin','Users/admin','npx.cmd')) and '${PLUGIN_ROOT}/scripts/tdq_mcp_launcher.mjs' in p and '${PLUGIN_DATA}/chrome-devtools-profile' in p"`
- [x] Q3 Gói `plugins/tdq-workflow-agy/` biên dịch sạch (`0` lỗi AST Python / `node --check`), giữ đủ `12 skills, 8 agents, 10 rules, 3 mcpServers, 6 hooks`, đạt `0 findings` với `agy plugin validate --strict --json` và vượt trọn bộ kiểm thử đơn vị của repo (`QC-F1`) — `agy.EXE plugin validate plugins/tdq-workflow-agy --strict --json`
- [x] Q4 Lệnh `--sinh-release-agy` tạo/cập nhật nhánh `release/antigravity` idempotent đặt `plugin.json` tại gốc nhánh không chạm working tree và nhánh `main`, vượt cài cô lập `agy plugin install` giữ nguyên `371` tệp `~/.gemini/config/` thật — `py -3 -X utf8 -m pytest tests/test_build_portable.py tests/test_agy_release_e2e.py -q -k release`
- [x] Q5 Workflow `.github/workflows/build-rust-hooks.yml` khai đủ `4` mục tiêu (`windows-x86_64`, `linux-x86_64-musl`, `darwin-arm64`, `darwin-x86_64`), binary trên đĩa vượt kiểm magic bytes PE/ELF/Mach-O và đã kiểm tra đồng bộ SSH Linux/macOS — `py -3 -X utf8 -m pytest tests/test_agy_plugin_validate.py -q -k magic`
- [x] Q6 Nhật ký `TDQ_LOG` bật mặc định / tắt sạch khi `TDQ_LOG=0`, `README-Antigravity.md` cập nhật chuẩn lệnh cài `release/antigravity`, `doc_lint.py` đạt `0` lỗi trên toàn bộ tài liệu request, và sau khi gộp về `dev` đã đồng bộ sạch `origin/dev` cùng `origin/release/antigravity` — `py -3 -X utf8 scripts/doc_lint.py docs/tdq/brief/2026-11-22-1033-nhanh-release-agy-da-os.md docs/tdq/spec/2026-11-22-1033-nhanh-release-agy-da-os.md docs/tdq/plan/2026-11-22-1033-nhanh-release-agy-da-os.md`
