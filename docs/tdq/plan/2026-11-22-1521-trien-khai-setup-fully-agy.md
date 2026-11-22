# PLAN — Triển khai quy trình Setupfully Zero-to-Full và Simulate Test 6 tầng cho Antigravity

Ngày: 2026-11-22 · Spec: ../spec/2026-11-22-1521-trien-khai-setup-fully-agy.md (bản 1.0, ĐÃ DUYỆT)
Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md
Mode thực thi: subagent — đo thực tế bằng tdq_bench thắng inline 2.0 phút (18.4 phút so với 20.4 phút trên 10 task / 6 đợt, hệ số agent 1.5) (ĐỀ XUẤT, user chốt lúc duyệt)
Trạng thái plan: HOÀN THÀNH

> **Tóm tắt dễ hiểu:** Trước đây trình cài đặt chưa tự chạy một mạch từ máy trắng tinh, còn đọc nhầm cấu hình cũ và mất dấu phiên khi đóng ứng dụng. Kế hoạch chia thành 4 giai đoạn để dựng bộ lưu dấu phiên, bộ mồi đa hệ điều hành, trình cài trọn gói và bộ kiểm thử giả lập 6 tầng. Kết quả là toàn bộ hệ sinh thái tìm kiếm, nén ngữ cảnh và xuất sơ đồ được biên dịch, cài lên máy hiện tại và nghiệm thu tự động hoàn chỉnh.

## Mục lục

- Phân bổ Model & Effort
- Quy tắc thi hành (áp cho mọi task)
- Thiết kế Trước vs Sau
- Ràng buộc toàn cục & Bản đồ Sở hữu Hợp đồng (Ownership Map)
- P1 — Nền tảng Trạng thái, Bootstrap Đa OS & Caveman/Tavily Launcher
- P2 — HostAdapter Antigravity, Điểm móc Hook Restart & Simulate Verifier 6 tầng
- P3 — Tài liệu Skill tdq-setup, Biên dịch Gói & Triển khai Kiểm chứng Máy thật
- Cụm song song
- Luật file nóng (một file, nhiều task chạm)
- P4 — Log & test bắt buộc
- Definition of Done

## Phân bổ Model & Effort
<!-- i18n-allow: canonical model/effort plan allocation table -->
> User được quyền đổi `type model` hoặc `effort` lúc duyệt plan. Thang model: [subagent-tuning.md](../../../plugins/tdq-workflow-agy/skills/tdq-conventions/references/subagent-tuning.md).

| Pha | Vai trò | Model | Effort | Ghi chú |
|---|---|---|---|---|
| `implement` (`T1.1`–`T1.3`, `T2.1`, `T2.3`, `T3.1`–`T3.2`, `T4.1`–`T4.2`) | `tdq-implementer` / inline | `inherit` (`gemini-4-hydrogen` / `gemini-4-neon`) | `high` | Leo thang lên `pro` (`gemini-4-carbon`) nếu trượt quá 2 lượt sửa |
| `implement` (`T2.2` Rust + Hook parity) | `tdq-implementer` / inline | `inherit` (`gemini-4-neon`) | `high` | Ưu tiên suy luận sâu cho đồng bộ Rust `tdq-dispatch` và Python `prompt_context` |
| `qc` (`muc_qc = ultra`) | `tdq-qc-tester` + `tdq-security-reviewer` | `inherit` / `pro` (`gemini-4-neon` + `gemini-4-carbon`) | `high` | Kiểm định độc lập 8 hạng mục DoD, bảo mật `secrets.env` và kiểm thử trực tiếp dưới 120 giây |
| `report` (Báo cáo + Archify HTML) | Phiên chính (`main`) | `inherit` | `high` | Kết xuất `docs/tdq/reports/<slug>.md` + `.html` và xác minh HTTP 200 qua Tailscale Serve |

## Quy tắc thi hành (áp cho mọi task)
1. Thứ tự phase là thứ tự phụ thuộc — không đảo.
2. Mỗi task: đánh `[~]` khi bắt đầu → viết test trước (đỏ) → code → test xanh → đổi sang `[x]` NGAY vào file này. Trạng thái checkbox: `[ ]` chưa làm · `[~]` đang làm · `[x]` xong.
3. Mỗi bước: `py -3 -X utf8 scripts/tdq_test.py vung-cham`; trọn bộ chỉ ở QC và `T4.2`.
4. Lệnh nào chạm state của workflow phải có `TDQ_PROJECT_DIR=<thư mục tạm>` ngay trên chính lệnh đó; mọi bài kiểm thử cài đặt đều đặt `TDQ_KHONG_CHAM_MAY=1` và `TDQ_SETUP_STATE_DIR=<thư mục tạm>`.
5. QC FAIL → thêm task fix dạng `R15-Compact` vào mục QC của file này (không cần duyệt lại), lặp đến khi pass 100%.
6. Không commit/push cho đến khi user yêu cầu; không chèn bất kỳ trailer đồng tác giả nào.
7. Tuân thủ 6 mã cấm cơ học (ANTI-1 Fake Red, ANTI-2 Blind Assertion, ANTI-3 Dirty State Git, ANTI-4 Late Tick, ANTI-5 Raw Dump, ANTI-6 Broad Area).

## Thiết kế Trước vs Sau
| Khía cạnh | Hiện trạng (Trước) | Thiết kế mới (Sau) |
|---|---|---|
| Cửa vào & tự động hóa | Cần cài sẵn Git/Python/`agy` và gọi lẻ từng cờ `--with-rtk`, `--with-caveman` | Hỗ trợ Cửa 0 (`bootstrap.ps1`/`bootstrap.sh` + `tdq_setup_probe.mjs`) và một câu `"setupfully tdq-workflow"` chạy trọn Pha 1 |
| Định vị cấu hình & Add-on | Nhánh Antigravity còn đọc `~/.claude*`, bọc Caveman bằng `sys.executable` cá nhân, chưa tự tải `Archify` | Tách nhánh Antigravity chuẩn `~/.gemini/config/`, bọc Caveman qua Node mode `"caveman"`, nạp mềm `secrets.env` và tự tải `Archify` |
| Nối tiếp Restart & Kiểm thử | Đóng mở lại IDE mất trạng thái chờ; `tdq_lsp.py check` lệ thuộc workspace hiện tại | `Host Session Fingerprint` + `setup-pending.flag` định tuyến từ Rust sang Python, tự kích hoạt `tdq_simulate_verify.py` 6 tầng trên sandbox tạm |

*Đối chiếu sơ đồ kiến trúc:* Kế hoạch bám sát trang xem trước đã kết xuất và khóa mã băm tại `docs/tdq/spec/2026-11-22-1521-trien-khai-setup-fully-agy-preview.html` cùng `docs/tdq/spec/2026-11-22-1521-trien-khai-setup-fully-agy-preview.manifest.json` (`status: current`, `binding.valid: true`). Từng task ánh xạ 1-1 tới các biên module `§2b`, 17 chữ ký hợp đồng `§3c` và 8 cổng nghiệm thu `Q1`–`Q8` mà không sinh thiết kế khác.

## Ràng buộc toàn cục & Bản đồ Sở hữu Hợp đồng (Ownership Map)

- Ngôn ngữ & Kiến trúc: Chú thích/docstring/CLI viết tiếng Anh · nạp `utf8_io` · ghi log ISO-8601 ra `stderr` bật mặc định và tắt hẳn khi `TDQ_LOG=0` · hàm `<= 50` dòng (`cyc <= 10`, `cog <= 15`) · chiều phụ thuộc một chiều `hooks/ -> scripts/` · khóa cứng schema trả về của `evaluate_restart_resume`: `{"action": "none" | "remind_restart" | "run_verify", "reason": str, "state": dict}` · không tạo mã cổng thứ 24 ngoài bộ 23 mã chuẩn Antigravity (dùng `[TDQ:SETUP]`) · sao lưu bản cài máy thật ra ngoài `~/.gemini/config/plugins/` tại `${PLUGIN_DATA}/backups/<timestamp>/`.

| Hợp đồng / Ký hiệu (§3c) | File & Task sở hữu | Task / File tiêu thụ |
|---|---|---|
| `resolve_plugin_data_dir(home)`, `compute_host_session_fingerprint()`, `load_setup_state(data_dir)`, `save_setup_state(state, pending, data_dir)`, `evaluate_restart_resume(is_new_turn, confirm_manual, data_dir)`, `save_tavily_secret(api_key, data_dir)`, `load_secrets_env(data_dir)` | `scripts/tdq_setup_state.py` (`T1.1`) | `T2.1` (`tdq_setup.py`), `T2.2` (`prompt_context.py`, `session_start.py`), `T2.3` (`tdq_simulate_verify.py`) |
| `probeToolchain(env, platform)` | `scripts/tdq_setup_probe.mjs` (`T1.2`) | `T1.2` (`bootstrap.ps1`, `bootstrap.sh`), `T2.3` (`tdq_simulate_verify.py`) |
| `buildSpawnSpec(mode, forwardedArgs, platform, lspCmd, pythonSpec)`, `_wrap_server_entry(entry, proxy_script)`, `_split_wrapped_args(entry)` | `tools/patches/agy_launchers.py`, `scripts/caveman_config.py` (`T1.3`) | `T2.1` (`tdq_setup.py`), `T2.3` (`tdq_simulate_verify.py`), `T3.2` (`build_agy_plugin.py`, `install_agy_plugin.py`) |
| `scan_setup_manifest(project)`, `apply_setup_manifest(project, setupfully, tavily_key)`, `ensure_archify_installed(home)` | `scripts/tdq_setup.py` (`T2.1`) | `T2.3` (`tdq_simulate_verify.py`), `T3.1` (`SKILL.md`, `zero-to-full-agy.md`), `T3.2` (triển khai máy thật) |
| `setup_pending_flag_exists()`, `extract_setupfully_trigger(prompt)` | `hooks/rust/tdq-dispatch/src/storage.rs`, `hooks/scripts/prompt_context.py` (`T2.2`) | `T2.2` (`pre_invocation.rs`, `_agy_pre_invocation_hook`), `T3.2` (`build_agy_plugin.py`) |
| `run_simulate_verify(plugin_root, data_dir)` | `scripts/tdq_simulate_verify.py` (`T2.3`) | `T2.3` (`tdq_setup.py --post-restart-verify` nạp trễ), `T3.2` (kiểm chứng hậu cài đặt trên máy hiện tại) |

## P1 — Nền tảng Trạng thái, Bootstrap Đa OS & Caveman/Tavily Launcher
- [x] **T1.1** (e14m) Tạo module trạng thái bền vững `scripts/tdq_setup_state.py`, quản lý `secrets.env` riêng tư và đo `Host Session Fingerprint` đa hệ điều hành — Test: `py -3 -X utf8 -m pytest tests/test_tdq_setup_state.py -q`
  - Dùng: `agy-customizations`
  - Để: đối chiếu cấu trúc `~/.gemini/config/`, đường dẫn dữ liệu plugin và thứ tự ưu tiên nạp của Antigravity, nạp skill TRƯỚC bước đỏ
  - Ra: module `scripts/tdq_setup_state.py` cùng bài kiểm thử `tests/test_tdq_setup_state.py`
  - Kiểm: `py -3 -X utf8 -m pytest tests/test_tdq_setup_state.py -q`
  - Không dùng cho: đóng gói `plugin.json` hoặc chỉnh sửa cấu hình plugin bên thứ ba
  - Req: `§2#O1`, `§3c` · Ngoài phạm vi: `GIỮ NGUYÊN` `docs/tdq/state.json` và `scripts/tdq_state.py`
  - Chạm: `scripts/tdq_setup_state.py`, `tests/test_tdq_setup_state.py`
  - Cần: Không
  - Giao tiếp: Consumes: `os.environ` | Produces: `resolve_plugin_data_dir(home)`, `compute_host_session_fingerprint()`, `load_setup_state(data_dir)`, `save_setup_state(state, pending, data_dir)`, `evaluate_restart_resume(is_new_turn, confirm_manual, data_dir)`, `save_tavily_secret(api_key, data_dir)`, `load_secrets_env(data_dir)`
  - Neo & Công cụ: `Write` tạo mới `scripts/tdq_setup_state.py`, `tests/test_tdq_setup_state.py`
  - Trước → Sau: mất dấu trạng thái khi đóng IDE và chưa có kho lưu khóa riêng → ghi nguyên tử `setup-state.json` + `setup-pending.flag`, lưu `secrets.env` riêng tư và đo dấu phiên tiến trình gốc dưới 20 ms
  - Tiêu chí chấp nhận (EARS): KHI ghi `awaiting_restart` rồi gọi `evaluate_restart_resume` từ dấu phiên tiến trình gốc mới (hoặc cờ quá hạn 24 giờ), HỆ THỐNG PHẢI chuyển sang `validating_after_restart` (hoặc tự thu hồi cờ quá hạn) dưới `20 ms` và che tuyệt đối giá trị khóa trên stdout/stderr
  - Logic cốt lõi: ưu tiên `TDQ_SETUP_STATE_DIR` và bỏ qua `PLUGIN_DATA` khi `TDQ_KHONG_CHAM_MAY=1`; duyệt tối đa 12 bậc cây tiến trình cha lấy `(root_pid, create_time)` trên Windows/macOS/Linux; ghi nguyên tử JSON + cờ và đặt quyền `0600` / Win32 DACL chủ sở hữu cho `secrets.env`
  - Ca góc hiểm & Assert: `TDQ_KHONG_CHAM_MAY=1` khi tiến trình cha có sẵn `PLUGIN_DATA` và tệp JSON bị cắt cụt · `assert resume["action"] == "run_verify" and elapsed_ms <= 20.0`
- [x] **T1.2** (e12m) Xây dựng bộ mồi Cửa 0 (`bootstrap.ps1`, `bootstrap.sh`), Pre-flight Probe Node `tdq_setup_probe.mjs` và giữ bit thực thi `0755` cho `*.sh` — Test: `py -3 -X utf8 -m pytest tests/test_bootstrap_probe.py -q`
  - Req: `§2#O2`, `§3c` · Ngoài phạm vi: `GIỮ NGUYÊN` nhánh lọc `sinh_nhanh_main` của `scripts/build_portable.py`
  - Chạm: `scripts/tdq_setup_probe.mjs`, `scripts/bootstrap.ps1`, `scripts/bootstrap.sh`, `scripts/build_portable.py`, `install.py`, `tests/test_bootstrap_probe.py`
  - Cần: Không
  - Giao tiếp: Consumes: `process.env`, `process.platform` | Produces: `probeToolchain(env, platform)`
  - Neo & Công cụ: `Write` tạo mới `scripts/tdq_setup_probe.mjs`, `scripts/bootstrap.ps1`, `scripts/bootstrap.sh`, `tests/test_bootstrap_probe.py`; `Edit` trên `scripts/build_portable.py` tại `loc_muc_agy_release` (`L738-758`); `Edit` trên `install.py` tại `_adjust_hooks_for_platform` (`L68-112`)
  - Trước → Sau: máy mới chưa có Python/Git không chạy được trình cài và tệp `.sh` bị hạ về `100644` khi xuất nhánh release → có bộ mồi Cửa 0 không dùng quyền quản trị, probe Node độc lập và giữ `100755` cho `*.sh`
  - Tiêu chí chấp nhận (EARS): KHI chạy `node scripts/tdq_setup_probe.mjs --json` với `PATH` rỗng hoặc chỉ chứa stub `WindowsApps`, HỆ THỐNG PHẢI xuất JSON kiểm kê hợp lệ dưới `5 giây` với `python.usable == false` và `loc_muc_agy_release` gán mode `100755` cho `scripts/bootstrap.sh`
  - Logic cốt lõi: `probeToolchain` dò `git`, `node >= 18`, `uv`, `python3` (loại stub `WindowsApps`), `agy`, `agent-lsp`, `rtk`, `rg`, trình duyệt Chromium, `archify`; `bootstrap.ps1`/`bootstrap.sh` cài user-space và báo rõ lệnh hệ thống nếu Linux tối giản thiếu `git`; gắn `0755` cho `*.sh` ở `build_portable.py` và `install.py`
  - Ca góc hiểm & Assert: `PATH` chỉ có `WindowsApps\python.exe` và thư mục chứa khoảng trắng · `assert report["python"]["usable"] is False and sh_mode == "100755"`
- [x] **T1.3** (e14m) Nâng cấp `tdq_mcp_launcher.mjs` (mode `caveman`, nạp mềm `secrets.env`, mở rộng `PATH`), `caveman_config.py` và `install_agy_plugin.py` — Test: `py -3 -X utf8 -m pytest tests/test_caveman_agy_launcher.py tests/test_caveman_setup.py tests/test_agy_launchers.py -q`
  - Req: `§2#O3`, `§3c` · Ngoài phạm vi: `GIỮ NGUYÊN` danh sách 2 tệp trả về của `generate_launchers` và định dạng bọc `sys.executable` cho cấu hình Claude Code
  - Chạm: `tools/patches/agy_launchers.py`, `scripts/caveman_config.py`, `tools/install_agy_plugin.py`, `tests/test_caveman_agy_launcher.py`
  - Cần: Không
  - Giao tiếp: Consumes: `mcp_config.json`, `secrets.env` | Produces: `buildSpawnSpec(mode, forwardedArgs, platform, lspCmd, pythonSpec)`, `_wrap_server_entry(entry, proxy_script)`, `_split_wrapped_args(entry)`
  - Neo & Công cụ: `Edit` trên `tools/patches/agy_launchers.py` tại `generate_launchers` (`L260-266`); `Edit` trên `scripts/caveman_config.py` tại `_split_wrapped_args` (`L165-177`), `_wrap_server_entry` (`L180-195`), `probe_caveman` (`L292-321`); `Edit` trên `tools/install_agy_plugin.py` tại `_ensure_binary_executable_and_hooks` (`L81-126`); `Write` tạo mới `tests/test_caveman_agy_launcher.py`
  - Trước → Sau: bật `--with-caveman` ghi đè `sys.executable` cá nhân vào `mcp_config.json` và `tavily-primary` chưa nạp `secrets.env` → giữ nguyên `"command": "node"` qua mode `"caveman"` không lộ path cá nhân, tự nạp mềm `secrets.env` và mở rộng `PATH` user-space
  - Tiêu chí chấp nhận (EARS): KHI bọc `wrap_mcp_config` hai lần liên tiếp rồi `unwrap_mcp_config` trên `mcp_config.json` chuẩn Antigravity, HỆ THỐNG PHẢI giữ `"command": "node"`, đạt `0` đường dẫn máy cá nhân và trả về đúng cấu hình ban đầu
  - Logic cốt lõi: thêm nhánh `mode === "caveman"`, bộ đọc `secrets.env` (không ghi đè biến môi trường có sẵn) và mở rộng `PATH` (`~/.local/bin`, `~/.cargo/bin`, `fnm`, `nvm`) vào `MCP_LAUNCHER_MJS`; `_wrap_server_entry` và `_split_wrapped_args` hỗ trợ song song định dạng Node launcher lẫn Claude; `install_agy_plugin.py` gắn `0755` cho `*.sh` và hỗ trợ sao lưu ra ngoài `plugins/`
  - Ca góc hiểm & Assert: bọc lặp idempotent trên cả cấu hình Node lẫn Claude và khóa chứa ký tự `=` hoặc dấu nháy · `assert entry["command"] == "node" and entry["args"][1] == "caveman"`

**Xong P1 khi**: cả 3 bộ kiểm thử của `T1.1`, `T1.2`, `T1.3` cùng `tests/test_caveman_setup.py` và `tests/test_agy_launchers.py` đều xanh 100%.

## P2 — HostAdapter Antigravity, Điểm móc Hook Restart & Simulate Verifier 6 tầng
- [x] **T2.1** (e18m) Chuẩn hóa nhánh Antigravity, thêm `--setupfully`, One-Shot Manifest, ghim `GEMINI.md` và tự cài `Archify` — Test: `py -3 -X utf8 -m pytest tests/test_agy_host_setup.py -q`
  - Req: `§2#O4`, `§3c` · Ngoài phạm vi: `GIỮ NGUYÊN` toàn bộ luồng cài đặt và kiểm tra cho máy chủ Claude Code khi `is_antigravity_host() == False`
  - Chạm: `scripts/tdq_setup.py`, `scripts/tdq_lsp.py`, `scripts/setup_status.py`, `scripts/tdq_devtool_mcp.py`, `scripts/archify_delivery.py`, `tools/patches/cli_fixes_a.py`, `tests/test_agy_host_setup.py`
  - Cần: T1.1, T1.3
  - Giao tiếp: Consumes: `resolve_plugin_data_dir(home)`, `save_setup_state(state, pending, data_dir)`, `evaluate_restart_resume(is_new_turn, confirm_manual, data_dir)`, `save_tavily_secret(api_key, data_dir)`, `_wrap_server_entry(entry, proxy_script)` | Produces: `scan_setup_manifest(project)`, `apply_setup_manifest(project, setupfully, tavily_key)`, `ensure_archify_installed(home)`
  - Neo & Công cụ: `Edit` trên `scripts/tdq_setup.py` tại `kiem_tra_archify` (`L1074-1095`), `parse_args` (`L1891-1921`), `main` (`L2046-2155`), `is_antigravity_host` (`L2161-2168`); `Edit` trên `scripts/tdq_lsp.py` tại `_all_mcp_configs` (`L299-303`), `bac2_mcp` (`L329-336`), `_chay_doctor` (`L398-416`), `bac3_language_server` (`L419-464`), `bac4_quyen_tool` (`L467-479`), `hook_xung_dot` (`L564-583`); `Edit` trên `scripts/setup_status.py` tại `thu_thuc_nhan` (`L429-464`); `Edit` trên `scripts/tdq_devtool_mcp.py` tại `check_devtool_setup` (`L126-189`); `Edit` trên `scripts/archify_delivery.py` tại `_gather_candidate_roots` (`L100-121`); `Edit` trên `tools/patches/cli_fixes_a.py` tại `_patch_lsp_module` (`L65-100`), `_patch_tdq_setup_and_lsp` (`L432-526`); `Write` tạo mới `tests/test_agy_host_setup.py`
  - Trước → Sau: nhánh Antigravity đọc nhầm `~/.claude*` và `~/.gemini/antigravity/mcp_config.json`, trượt giả Gate 3 / `doctor` vì tham số `.mjs`, ghim sai `GEMINI.md` và thiếu tự cài `Archify` → tách nhánh Antigravity chuẩn `~/.gemini/config/`, thêm 6 cờ điều phối mới (kèm `--state-dir` cô lập và nạp trễ `import tdq_simulate_verify`), ghim `GEMINI.md < 24000 bytes` và tự tải `Archify` vào `~/.local/share/archify`
  - Tiêu chí chấp nhận (EARS): KHI chạy `--scan-json`, `tdq_lsp.py check` và `--setupfully` với `TDQ_KHONG_CHAM_MAY=1` trên `HOME` giả lập chỉ có `~/.gemini`, HỆ THỐNG PHẢI trả `0` nợ giả Claude, đạt Bậc 2/3/4/5 của `tdq_lsp.py` với launcher `.mjs`, không gọi cài mạng và sinh khối ghim `GEMINI.md` chuẩn Antigravity dưới `24000 bytes`
  - Logic cốt lõi: sửa đường dẫn `~/.gemini/config/mcp_config.json`, lọc bỏ đối số `.mjs` trước khi gọi `agent-lsp doctor`, miễn Gate 3 `lang_mcp` khi `args` dùng `tdq_mcp_launcher.mjs` (`"lsp"`/`"caveman"`), quét xung đột hook tại `~/.gemini/config/plugins/*/hooks.json`, xếp `chrome-devtools-plugin` chưa cài vào `Optional Companion`, thêm `~/.local/share/archify` + `ensure_archify_installed` và đồng bộ `cli_fixes_a.py`
  - Ca góc hiểm & Assert: `HOME` trống chưa có `~/.claude.json`, vắng `chrome-devtools-plugin` và bật `TDQ_KHONG_CHAM_MAY=1` · `assert manifest["claude_debt_count"] == 0 and len(gemini_pin.encode("utf-8")) < 24000`
- [x] **T2.2** (e16m) Tích hợp kiểm cờ `setup-pending.flag` trong Rust `tdq-dispatch` và điều phối `"setupfully"` / nối tiếp hậu Restart trong Python hooks — Test: `py -3 -X utf8 -m pytest tests/test_hook_setup_resume.py -q`
  - Req: `§2#O5`, `§3c` · Ngoài phạm vi: `GIỮ NGUYÊN` đúng bộ 23 mã cổng chuẩn Antigravity và tính đối xứng JSON của `test_rust_dispatch_parity.py`
  - Chạm: `hooks/rust/tdq-dispatch/src/storage.rs`, `hooks/rust/tdq-dispatch/src/main.rs`, `hooks/rust/tdq-dispatch/src/events/pre_invocation.rs`, `hooks/scripts/prompt_context.py`, `hooks/scripts/session_start.py`, `tools/patches/agy_hooks.py`, `.github/workflows/build-rust-hooks.yml`, `tests/test_rust_dispatch_parity.py`, `tests/test_hook_setup_resume.py`
  - Cần: T1.1, T2.1
  - Giao tiếp: Consumes: `evaluate_restart_resume(is_new_turn, confirm_manual, data_dir)`, `load_setup_state(data_dir)` | Produces: `setup_pending_flag_exists()`, `extract_setupfully_trigger(prompt)`
  - Neo & Công cụ: `Edit` trên `hooks/rust/tdq-dispatch/src/storage.rs` tại `get_runtime_dir` (`L87-91`); `Edit` trên `hooks/rust/tdq-dispatch/src/main.rs` tại `execute_python_fallback` (`L162-185`); `Edit` trên `hooks/rust/tdq-dispatch/src/events/pre_invocation.rs` tại `handle_pre_invocation` (`L189-224`); `Edit` trên `hooks/scripts/prompt_context.py` tại `_has_prompt_grant_blockers` (`L136-151`), `_agy_pre_invocation_hook` (`L326-347`); `Edit` trên `hooks/scripts/session_start.py` tại `kiem_can_setup_lan_dau` (`L198-206`); `Edit` trên `tools/patches/agy_hooks.py` tại `_patch_prompt_context` (`L2456-2696`), `_patch_session_start` (`L2920-2961`); `Edit` trên `.github/workflows/build-rust-hooks.yml`; `Edit` trên `tests/test_rust_dispatch_parity.py` tại `_isolated_env` (`L57-99`); `Write` tạo mới `tests/test_hook_setup_resume.py`
  - Trước → Sau: mất dấu trạng thái chờ Restart giữa các lượt gọi và fallback Python dễ vấp stub `WindowsApps` → kiểm cờ `O(1)` ở Rust ủy quyền sang Python, lọc chặt câu lệnh `"setupfully tdq-workflow"` và tự bơm mã `[TDQ:SETUP]` hậu Restart khi `action == "run_verify"`
  - Tiêu chí chấp nhận (EARS): KHI không có `setup-pending.flag` thì đường nóng `PostInvocation` hoàn tất dưới `50 ms`; KHI có cờ và `evaluate_restart_resume` trả `action == "run_verify"`, HỆ THỐNG PHẢI phát quyết định `inject` mang mã `[TDQ:SETUP]` kèm `user_markdown` kích hoạt `--post-restart-verify`
  - Logic cốt lõi: `setup_pending_flag_exists()` tuân thủ thứ tự cô lập `TDQ_SETUP_STATE_DIR` → `TDQ_KHONG_CHAM_MAY=1` → `PLUGIN_DATA` → mặc định; `execute_python_fallback` thử tiếp ứng viên Python sau nếu tiến trình trả lỗi mà `stdout` rỗng; `extract_setupfully_trigger` loại câu hỏi/phủ định/trích dẫn và subagent; dọn `PLUGIN_DATA` trong `_isolated_env`; `test_hook_setup_resume.py` gọi `cargo test`/`cargo build --release` và dựng `agy_hooks.apply_all` trên `tmp_path` (không chạm `plugins/` trước `T3.2`)
  - Ca góc hiểm & Assert: câu hỏi `"setupfully tdq-workflow là gì?"`, câu phủ định `"không chạy setupfully"`, lượt subagent và mở tab mới cùng PID cũ (`action == "remind_restart"`) · `assert extract_setupfully_trigger("setupfully tdq-workflow") is True and extract_setupfully_trigger("setupfully tdq-workflow là gì?") is False`
  - Tiến độ inline: đã xong toàn bộ T2.2 (`tests/test_hook_setup_resume.py` 5 passed, `cargo test` 39 passed, `cargo build --release` OK, `test_rust_dispatch_parity.py` 63 passed tổng cộng cùng setup resume).
- [x] **T2.3** (e16m) Xây dựng trình kiểm thử giả lập 6 tầng `scripts/tdq_simulate_verify.py` chạy trên sandbox tạm sạch rác — Test: `py -3 -X utf8 -m pytest tests/test_tdq_simulate_verify.py -q`
  - Req: `§2#O6`, `§3c` · Ngoài phạm vi: `GIỮ NGUYÊN` nguyên trạng `~/.gemini/config/` và `docs/tdq/state.json` của kho dự án thật
  - Chạm: `scripts/tdq_simulate_verify.py`, `tests/test_tdq_simulate_verify.py`
  - Cần: T1.1, T1.2, T1.3, T2.1, T2.2
  - Giao tiếp: Consumes: `load_setup_state(data_dir)`, `save_setup_state(state, pending, data_dir)`, `load_secrets_env(data_dir)`, `probeToolchain(env, platform)`, `scan_setup_manifest(project)` | Produces: `run_simulate_verify(plugin_root, data_dir)`
  - Neo & Công cụ: `Write` tạo mới `scripts/tdq_simulate_verify.py`, `tests/test_tdq_simulate_verify.py`
  - Trước → Sau: thiếu trình nghiệm thu tự động độc lập với workspace đang mở → có `tdq_simulate_verify.py` chạy đủ 6 tầng (`T1`–`T6`) qua JSON-RPC pipe tương tác trên thư mục tạm `tdq_sim_*`
  - Tiêu chí chấp nhận (EARS): KHI gọi `run_simulate_verify` (hoặc `tdq_setup.py --post-restart-verify`), HỆ THỐNG PHẢI hoàn tất `T1`–`T6` dưới `90 giây`, xóa sạch `tdq_sim_*` trong khối `finally`, giữ bất biến danh sách tệp `~/.gemini/config/` và chuyển trạng thái sang `verified` khi `Core Gate PASS`
  - Logic cốt lõi: tạo kho mẫu Python/TS + Git trong `tempfile.TemporaryDirectory(prefix="tdq_sim_")`; thực thi `T1` (`agy plugin validate` + `probeToolchain`), `T2` (6 sự kiện hook < 50 ms), `T3` (`Popen` JSON-RPC `initialize` + `tools/list` cho `lsp`, `caveman`, `tavily-primary`), `T4` (LSP `find_symbol`/`find_references` + `graphify` mini), `T5` (`rtk`/`rg` + `archify_delivery` render mẫu), `T6` (kiểm 8 `agents/*.md` + vòng đời hook subagent); tách bạch `Core Gate` với `Optional Add-on Gate`
  - Ca góc hiểm & Assert: vắng trình duyệt Chrome hoặc vắng `TAVILY_API_KEY` (xếp `SKIPPED` ở `Optional Gate`) và lỗi cưỡng bức giữa chừng vẫn dọn sạch thư mục tạm · `assert result["core_gate"] == "PASS" and result["temp_cleaned"] is True`

**Xong P2 khi**: `cargo test` trong `hooks/rust/tdq-dispatch/` và toàn bộ bài kiểm thử `T2.1`, `T2.2`, `T2.3` xanh 100% (đối xứng gói biên dịch `tests/test_rust_dispatch_parity.py` khóa tiếp ngay tại `T3.2`).

## P3 — Tài liệu Skill tdq-setup, Biên dịch Gói & Triển khai Kiểm chứng Máy thật
- [x] **T3.1** (e10m) Cập nhật `skills/tdq-setup/SKILL.md` v2 (`<= 132` dòng), tạo `zero-to-full-agy.md`, cập nhật `README` và khóa lại `token-budget.json` — Test: `py -3 -X utf8 -m pytest tests/test_tdq_setup_skill.py -q`
  - Req: `§2#O7`, `§5` · Ngoài phạm vi: `GIỮ NGUYÊN` con trỏ `uu-tien-tim-kiem-chi-tiet.md` và cấm chép lại `CAU_LUAT` vào `SKILL.md`
  - Chạm: `skills/tdq-setup/SKILL.md`, `skills/tdq-setup/references/zero-to-full-agy.md`, `skills/tdq-setup/references/chrome-devtools-mcp-guide.md`, `README.md`, `README-Antigravity.md`, `docs/tdq/token-budget.json`, `tests/test_tdq_setup_skill.py`
  - Cần: T2.1, T2.2
  - Giao tiếp: Consumes: `scan_setup_manifest(project)`, `apply_setup_manifest(project, setupfully, tavily_key)` | Produces: `zero-to-full-agy.md`
  - Neo & Công cụ: `Edit` trên `skills/tdq-setup/SKILL.md`; `Write` tạo mới `skills/tdq-setup/references/zero-to-full-agy.md`; `Edit` trên `skills/tdq-setup/references/chrome-devtools-mcp-guide.md`, `README.md`, `README-Antigravity.md`, `docs/tdq/token-budget.json`; `Edit` trên `tests/test_tdq_setup_skill.py` tại `LuatKhongMoFileTruoc` (`L87-120`)
  - Trước → Sau: `SKILL.md` chỉ mô tả luồng kiểm bậc cũ và còn đường dẫn cá nhân `Add_on_for_claude` → chuẩn hóa quy trình 2 chế độ (`"setupfully tdq-workflow"` consent 1 lượt + One-Shot Manifest `/tdq-setup`), nối tiếp hậu Restart, xóa path cá nhân và khóa `token-budget.json`
  - Tiêu chí chấp nhận (EARS): KHI chạy `doc_lint.py skills/tdq-setup`, `i18n_check.py`, `token_budget.py --kiem` và `test_tdq_setup_skill.py`, HỆ THỐNG PHẢI đạt `0` vi phạm với `SKILL.md <= 132` dòng và mọi tệp tham chiếu `< 24000 bytes`
  - Logic cốt lõi: viết lại `skills/tdq-setup/SKILL.md` bằng tiếng Anh gọn dưới 132 dòng (nêu rõ luật ngoại lệ `"setupfully tdq-workflow"`, bảng kê 1 lần cho `/tdq-setup` thường, lưu khóa qua `--set-tavily-key` và bước đóng vòng MCP/subagent sau `--post-restart-verify`), tách bảng Cửa 0 đa hệ điều hành sang `references/zero-to-full-agy.md` và chạy `scripts/token_budget.py` cập nhật khóa băm
  - Ca góc hiểm & Assert: kiểm tra không vượt trần 132 dòng, giữ nguyên con trỏ 1 tầng tới `zero-to-full-agy.md` và không chứa đường dẫn cá nhân · `assert len(skill_lines) <= 132 and "Add_on_for_claude" not in skill_text`
- [x] **T3.2** (e12m) Biên dịch `plugins/tdq-workflow-agy/`, sao lưu và cài lên `~/.gemini/config/plugins/tdq-workflow-agy` kèm kiểm chứng thực tế trên máy này — Test: `py -3 -X utf8 -m pytest tests/test_agy_plugin_validate.py tests/test_rust_dispatch_parity.py tests/test_setup_bundle_e2e.py -q`
  - Dùng: `plugin`
  - Để: đối chiếu quy chuẩn cấu trúc gói `plugin.json`, cổng `agy plugin validate --strict --json` và quy tắc không sửa tay `config.json`, nạp skill TRƯỚC bước đỏ
  - Ra: gói biên dịch `plugins/tdq-workflow-agy/`, bản sao lưu ngoài `plugins/` và bản cài đã xác minh tại `~/.gemini/config/plugins/tdq-workflow-agy`
  - Kiểm: `agy plugin validate --strict --json plugins/tdq-workflow-agy`
  - Không dùng cho: tự động cài ngầm plugin bên thứ ba hoặc ghi trực tiếp vào `~/.gemini/config/config.json`
  - Req: `§2#O8`, `§5`, `§6#Q8` · Ngoài phạm vi: `GIỮ NGUYÊN` số lượng 8 agents, 6 hooks, 3 mcpServers (mẫu kho mã không bọc sẵn Caveman), 10 rules, 12 skills của gói Antigravity
  - Chạm: `tools/build_agy_plugin.py`, `tests/test_setup_bundle_e2e.py`
  - Cần: T1.2, T1.3, T2.1, T2.2, T2.3, T3.1
  - Giao tiếp: Consumes: `buildSpawnSpec(mode, forwardedArgs, platform, lspCmd, pythonSpec)`, `apply_setup_manifest(project, setupfully, tavily_key)`, `run_simulate_verify(plugin_root, data_dir)` | Produces: `build(upstream, output)`
  - Neo & Công cụ: `Edit` trên `tools/build_agy_plugin.py` tại `build` (`L219-297`); `Write` tạo mới `tests/test_setup_bundle_e2e.py`
  - Trước → Sau: gói `plugins/tdq-workflow-agy/` và bản cài máy thật chưa đồng bộ nhị phân Rust mới, launcher mới và bộ kiểm thử 6 tầng → biên dịch tự động toàn gói qua `tools/build_agy_plugin.py`, sao lưu bản cũ sang `${PLUGIN_DATA}/backups/<timestamp>/`, cài đặt lên máy hiện tại và vượt cổng `Simulate Test` thật
  - Tiêu chí chấp nhận (EARS): KHI chạy `tools/build_agy_plugin.py`, `agy plugin validate --strict --json`, `test_rust_dispatch_parity.py` và `--post-restart-verify` trên cả gói kho mã lẫn bản cài đích, HỆ THỐNG PHẢI trả `0` lỗi cấu trúc, `0` bản sao lưu nằm nhầm trong `~/.gemini/config/plugins/` và đạt `Core Gate PASS`
  - Logic cốt lõi: cập nhật `tools/build_agy_plugin.py` kiểm cú pháp mọi tệp `*.mjs` mới và biên dịch đồng bộ toàn bộ `plugins/tdq-workflow-agy/` (không sửa tay tệp sinh tự động); sao lưu bản cài máy thật ra `${PLUGIN_DATA}/backups/<timestamp>/`; chạy `tools/install_agy_plugin.py --with-rtk --with-caveman` (chỉ bọc Caveman ở thư mục đích cài đặt) và kiểm chứng bằng `tests/test_setup_bundle_e2e.py`
  - Ca góc hiểm & Assert: kiểm tra không lọt đường dẫn cá nhân vào `plugins/tdq-workflow-agy/` và `agy plugin list --json` không báo trùng ID plugin sau khi sao lưu · `assert val_res["valid"] is True and dup_plugin_ids == []`

**Xong P3 khi**: `tools/build_agy_plugin.py`, `agy plugin validate --strict --json`, `tests/test_agy_plugin_validate.py` và `tests/test_setup_bundle_e2e.py` đều xanh 100%, bản cài trực tiếp trên máy đạt `Core Gate PASS`.

## Cụm song song

Bảng phân đợt tự động theo DAG phụ thuộc `Cần:`, kiểm tra va chạm import AST (TCAS) và tập `Chạm:` rời nhau hoàn toàn:

- **Đợt 1 (3 task song song — nền tảng độc lập):** `T1.1` (`setup-state`), `T1.2` (`bootstrap-probe`), `T1.3` (`mcp-caveman-launcher`) — 0 tệp giao nhau.
- **Đợt 2 (1 task — HostAdapter Antigravity):** `T2.1` (`agy-host-setup`, cần `T1.1, T1.3`).
- **Đợt 3 (1 task — điểm móc Hook Rust/Python):** `T2.2` (`hook-restart-router`, cần `T1.1, T2.1` do `session_start.py` import `tdq_setup` và `tdq_devtool_mcp`).
- **Đợt 4 (2 task song song — trình kiểm thử 6 tầng & tài liệu skill):** `T2.3` (`simulate-verifier`, cần `T1.1..T2.2`), `T3.1` (`setup-docs`, cần `T2.1, T2.2`) — 0 tệp giao nhau.
- **Đợt 5 (1 task hội tụ — biên dịch gói & triển khai máy thật):** `T3.2` (`bundle-deploy-verify`, cần `T1.2..T3.1`).
- **Đợt 6–7 (kiểm chứng log service & hội quy toàn bộ):** `T4.1` (cần `T3.2`) → `T4.2` (cần `T3.2, T4.1`).

## Luật file nóng (một file, nhiều task chạm)

Không có FILE NÓNG chồng chéo đường dẫn (`0` cặp task trùng file trong `Chạm:`): liên kết import xuyên module duy nhất giữa `hooks/scripts/session_start.py` (`T2.2`) và `scripts/tdq_setup.py` + `scripts/tdq_devtool_mcp.py` (`T2.1`) đã được tuần tự hóa tường minh bằng `Cần: T1.1, T2.1`. Các tệp sinh tự động trong `plugins/tdq-workflow-agy/` do một chủ ghi duy nhất là `T3.2` đảm nhiệm sau khi `T1.1`–`T3.1` hoàn tất.

## P4 — Log & test bắt buộc
- [x] **T4.1** (e6m) Kiểm chứng dịch vụ log bật mặc định (nhãn thời gian ISO-8601, tệp log `PLUGIN_DATA/logs/`, tắt hoàn toàn khi `TDQ_LOG=0`) trên mọi module mới — Test: `py -3 -X utf8 -m pytest tests/test_setup_log_service.py -q`
  - Req: `§4`, `§6#Q1` · Ngoài phạm vi: `GIỮ NGUYÊN` định dạng stdout JSON thuần của MCP stdio và hook output
  - Chạm: `tests/test_setup_log_service.py`
  - Cần: T3.2
  - Giao tiếp: Consumes: `load_setup_state(data_dir)`, `run_simulate_verify(plugin_root, data_dir)`, `probeToolchain(env, platform)` | Produces: `test_default_iso_log_and_mute_across_modules()`
  - Neo & Công cụ: `Write` tạo mới `tests/test_setup_log_service.py`
  - Trước → Sau: chưa có bài kiểm tra tự động đối chiếu đồng loạt `TDQ_LOG=1` và `TDQ_LOG=0` trên cả Python lẫn Node `.mjs` mới → khóa chặt hợp đồng log ISO-8601 trên `stderr` và không làm bẩn `stdout` JSON
  - Tiêu chí chấp nhận (EARS): KHI chạy `tdq_setup_state.py`, `tdq_simulate_verify.py`, `tdq_setup_probe.mjs`, `tdq_mcp_launcher.mjs` mặc định thì `stderr` có dòng `[YYYY-MM-DDTHH:MM:SS]`; KHI đặt `TDQ_LOG=0`, HỆ THỐNG PHẢI xuất `stderr` rỗng và giữ `stdout` JSON nguyên vẹn
  - Logic cốt lõi: gọi subprocess thực cho từng script Python và Node ở hai chế độ `TDQ_LOG=1` và `TDQ_LOG=0` trên thư mục tạm `TDQ_SETUP_STATE_DIR`, kiểm regex nhãn thời gian ISO-8601 và kiểm che mật khẩu `TAVILY_API_KEY`
  - Ca góc hiểm & Assert: truyền khóa giả `tvly-secret-test-999` qua `save_tavily_secret` khi `TDQ_LOG=1` · `assert "tvly-secret-test-999" not in stderr_on and stderr_off == ""`
- [x] **T4.2** (e8m) Chạy hội quy một lệnh cho toàn bộ suite unit test, parity Rust-Python và kiểm tra tài liệu toàn kho — Test: `py -3 -X utf8 -m pytest tests/test_tdq_setup_state.py tests/test_bootstrap_probe.py tests/test_caveman_agy_launcher.py tests/test_caveman_setup.py tests/test_agy_launchers.py tests/test_agy_host_setup.py tests/test_hook_setup_resume.py tests/test_tdq_simulate_verify.py tests/test_tdq_setup_skill.py tests/test_agy_plugin_validate.py tests/test_setup_bundle_e2e.py tests/test_setup_log_service.py tests/test_rust_dispatch_parity.py -q`
  - Req: `§4`, `§6#Q1`–`§6#Q8` · Ngoài phạm vi: `GIỮ NGUYÊN` toàn bộ bài test hiện hữu ngoài vùng setup
  - Chạm: `docs/tdq/artifacts/2026-11-22-1521-trien-khai-setup-fully-agy/unit-suite-summary.md`
  - Cần: T3.2, T4.1
  - Neo & Công cụ: `Write` tạo mới `docs/tdq/artifacts/2026-11-22-1521-trien-khai-setup-fully-agy/unit-suite-summary.md`
  - Trước → Sau: các tệp kiểm thử chạy rời từng phần → gom kiểm định hội quy một lệnh phủ trọn 13 tệp test trọng tâm cùng toàn bộ suite kho mã và ghi biên bản tóm tắt thời gian chạy
  - Logic cốt lõi: thực thi lệnh `pytest` hợp nhất với `TDQ_KHONG_CHAM_MAY=1` để xác nhận không có xung đột biến môi trường hoặc rò rỉ trạng thái giữa các bài test, ghi kết quả đếm pass/fail vào artifact
  - Tiêu chí chấp nhận (EARS): KHI chạy lệnh `pytest` hội quy một lệnh với `TDQ_KHONG_CHAM_MAY=1`, HỆ THỐNG PHẢI đạt `0` failed và mã thoát `0`

## QC vòng 1 — fix
- [x] **QC1.1** (e12m) Vá 5 phát hiện an ninh từ `tdq-security-reviewer` (`bootstrap.ps1`/`sh` ép TLS 1.2 + kiểm URL repo + tải file trước khi chạy kèm xác nhận, `agy_launchers.py` giới hạn khóa `TAVILY_API_KEY` theo máy chủ đích `tavily-primary`, `tdq_setup.py` kiểm `origin` & giới hạn clone Archify ở `setupfully=True`, `tdq_setup_state.py`/`tdq_setup.py` fail-closed `icacls` & nhận key qua stdin `--set-tavily-key -`, `caveman_config.py`/`prompt_context.py`/`agy_hooks.py` siết guard câu hỏi & host Antigravity) — Test: `py -3 -X utf8 -m pytest tests/test_tdq_setup_state.py tests/test_bootstrap_probe.py tests/test_caveman_agy_launcher.py tests/test_caveman_setup.py tests/test_agy_host_setup.py tests/test_hook_setup_resume.py -q`
  - Tiến độ inline: đã xong 54/54 test `QC1.1`.
- [x] **QC1.2** (e8m) Vá 2 lỗi ổn định `smoke-e2e --changed` (`tests/test_build_portable.py` khai báo 6 tệp mới được duyệt vào `APPROVED_RUNTIME_MODULES`/`APPROVED_RELEASE_DOCS`, `scripts/tdq_simulate_verify.py` chuyển `T3` tránh nghẽn buffer `stderr` và thử lại tối đa 2 lần chỉ khi `T2` hot-hook dính nhiễu CPU song song `> 50 ms`) — Test: `py -3 -X utf8 -m pytest tests/test_build_portable.py tests/test_tdq_simulate_verify.py tests/test_setup_bundle_e2e.py -q`
- [x] **QC1.3** (e8m) Sửa 3 câu dài `[R5]` ở `README.md`/`README-Antigravity.md`, giữ `prompt_context.py:171` sạch `# i18n-allow`, biên dịch lại `plugins/tdq-workflow-agy/`, cập nhật bản cài máy thật & xác minh lại toàn diện — Test: `py -3 -X utf8 scripts/doc_lint.py README.md README-Antigravity.md && py -3 -X utf8 -m pytest tests/test_agy_plugin_validate.py tests/test_rust_dispatch_parity.py -q`
  - Tiến độ inline: đã pass 91/91 test (`test_agy_plugin_validate`, `test_caveman_setup`, `test_agy_host_setup`, `test_hook_setup_resume`, `test_rust_dispatch_parity`), live install & `--post-restart-verify` đạt `status=verified`, `core_gate=PASS` (`7.925s`).

## QC vòng 2 — fix
- [x] **QC2.1** (e10m) Khắc phục toàn bộ 4 khiếm khuyết của `tdq-qc-tester` (`tests/test_setup_log_service.py` kiểm riêng `"lsp"` vs `"--tavily"`, tách helper giảm cyclomatic complexity xuống `<= 10` & `<= 50` dòng cho 11 hàm + `bootstrap.ps1:Invoke-Main`, bổ sung log chẩn đoán tôn trọng `TDQ_LOG=0` ở 3 khối `except`, chỉnh `zero-to-full-agy.md`) — Test: `py -3 -X utf8 -m pytest tests/test_setup_log_service.py tests/test_bootstrap_probe.py tests/test_tdq_setup_state.py -q`
  - Tiến độ inline: đã qua toàn bộ re-audit `tdq-qc-tester` (`Q1`–`Q8`, `QC-F3`, `QC-F4`: PASS 100%, 0 defect).
- [x] **QC2.2** (e12m) Sửa ổn định chạy trong `IsolatedJob` (`tdq_simulate_verify.py` `_prepare_lsp_socket_env` né giới hạn socket `AF_UNIX <= 107` byte của Windows + `_cleanup_sandbox(short_home)`, `tdq_setup.py` nhận `TDQ_TEST_JOB_ROOT` trong `_is_temp_path` & truyền `caller_file` vào `tdq_lsp._is_antigravity_host`, `SKILL.md:50` ghi rõ `(phase does not change)`, `test_hook_setup_resume.py` giữ `RUSTUP_HOME`/`CARGO_HOME`, `test_agy_host_setup.py` cô lập không chạm mạng) — Test: `py -3 -X utf8 scripts/tdq_test.py smoke-e2e --changed --workers auto --fresh --reuse off && py -3 -X utf8 scripts/tdq_test.py tron-bo --workers auto --fresh --reuse off`
  - Tiến độ inline: `smoke-e2e` đạt `417 passed` (`0` failed); `tron-bo` đạt `4809 passed, 37 skipped, 2984 subtests passed` (exit `0`).

## Definition of Done
Trỏ về `§6` của spec (`docs/tdq/spec/2026-11-22-1521-trien-khai-setup-fully-agy.md`). Mỗi dòng một ô tick kèm lệnh kiểm chứng thực tế:

- [x] Q1 Trạng thái bền vững `setup-state.json` + `setup-pending.flag`, bảo mật `secrets.env` không lộ khóa và đo `Host Session Fingerprint` đạt `<= 20 ms` — `py -3 -X utf8 -m pytest tests/test_tdq_setup_state.py tests/test_setup_log_service.py -q`
- [x] Q2 Bộ Bootstrap Cửa 0 (`bootstrap.ps1`, `bootstrap.sh`), `tdq_setup_probe.mjs` xuất JSON hợp lệ dưới `5 giây` và tệp `.sh` mang mode `100755` — `py -3 -X utf8 -m pytest tests/test_bootstrap_probe.py -q`
- [x] Q3 Caveman Node Launcher giữ nguyên `"command": "node"` với `0` đường dẫn cá nhân, nạp mềm `secrets.env` và tương thích ngược Claude (idempotent) — `py -3 -X utf8 -m pytest tests/test_caveman_agy_launcher.py tests/test_caveman_setup.py tests/test_agy_launchers.py -q`
- [x] Q4 HostAdapter Antigravity trả `0` nợ giả Claude, `GEMINI.md` chuẩn Antigravity `< 24000 bytes` và `ensure_archify_installed` cài/kiểm đúng `Archify` (tôn trọng `TDQ_KHONG_CHAM_MAY=1`) — `py -3 -X utf8 -m pytest tests/test_agy_host_setup.py -q`
- [x] Q5 Đường nóng Rust `tdq-dispatch` không có cờ hoàn tất `< 50 ms`, giữ nguyên `23` mã cổng chuẩn và bộ định tuyến `"setupfully"` / hậu Restart phát đúng `[TDQ:SETUP]` — `py -3 -X utf8 -m pytest tests/test_hook_setup_resume.py tests/test_rust_dispatch_parity.py -q`
- [x] Q6 Bộ kiểm thử giả lập 6 tầng `tdq_simulate_verify.py` hoàn tất `T1`–`T6` dưới `90 giây` trên thư mục trạng thái cô lập, trả `Core Gate PASS`, xóa sạch `tdq_sim_*` và giữ nguyên `~/.gemini/config/` — `py -3 -X utf8 -m pytest tests/test_tdq_simulate_verify.py -q`
- [x] Q7 Tài liệu `skills/tdq-setup/SKILL.md` đạt `<= 132` dòng, mọi tệp rule/skill trong gói biên dịch `< 24000 bytes`, `0` lỗi `doc_lint`/`i18n_check` và khớp `token-budget.json` — `py -3 -X utf8 -m pytest tests/test_tdq_setup_skill.py -q`
- [x] Q8 Biên dịch `plugins/tdq-workflow-agy/`, `agy plugin validate --strict --json` trả `0` lỗi trên cả gói repo lẫn bản cài `~/.gemini/config/plugins/tdq-workflow-agy` (có sao lưu tại `${PLUGIN_DATA}/backups/`) và hoàn tất kiểm chứng runtime MCP/subagent thực tế dưới `120 giây` ở mức `ultra` — `py -3 -X utf8 -m pytest tests/test_agy_plugin_validate.py tests/test_setup_bundle_e2e.py -q`
