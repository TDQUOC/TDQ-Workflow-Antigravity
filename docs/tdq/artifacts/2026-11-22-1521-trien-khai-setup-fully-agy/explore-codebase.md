# Codebase Reconnaissance — `2026-11-22-1521-trien-khai-setup-fully-agy`

Ngày khảo sát: 2026-11-22 · Vai trò: `tdq-explorer` · Tham chiếu gốc: `docs/tdq/research/2026-11-22-1424-phan-tich-setup-may-trong.md`.

---

## 1. Host Path & Config Drift (`Claude Code` vs `Google Antigravity`)

### 1.1. `scripts/tdq_setup.py`
- `scripts/tdq_setup.py:72` — `DUONG_INSTRUCTION = "~/.claude/CLAUDE.md"` — Hằng số instruction mặc định vẫn trỏ Claude Code; được truyền ở L1547 (`thuc_hien_setup_bu`), L1861 (`khoi_tao_nen`), L2105 (`main`).
- `scripts/tdq_setup.py:77-83` — `TIEN_TO_CAI_DUOC` — Whitelist lệnh cài chỉ cho phép `("uv tool install ", "brew install ", "npm i -g ", "npm install -g ", "pipx install ")`; `KY_TU_SHELL` (L90) chặn mọi ký tự `; & | $ > <` và `_chay_lenh` (L106-132) dùng `shlex.split` + `shell=False`. Bootstrap/cài runtime mới cần hàm cài chuyên biệt có kiểm soát thay vì đi qua `_duoc_cai` cũ.
- `scripts/tdq_setup.py:159-160` — `_khong_cham_may()` — Đọc `os.environ.get("TDQ_KHONG_CHAM_MAY") == "1"`; dùng để khóa chạm máy thật ở `cai_agent_lsp` (L196), `khai_server_mcp` (L377), `don_may` (L415), `_cai_dat_env_timeout_mcp` (L568), `dong_bo_mcp_plugin_cache` (L675), `kiem_plugin_user` (L715), `tu_dong_cap_nhat_plugin_user` (L811, L821), `thuc_hien_cap_nhat_remote` (L924), `kiem_va_them_user_scripts_path` (L1003).
- `scripts/tdq_setup.py:335-365` — `_ghi_args_mcp(duong, duong_cau_hinh, args_moi)` — Nếu `duong_cau_hinh == "~/.claude.json"` và có `claude` CLI thì gọi `claude mcp remove/add-json`; trên Antigravity cần ghi hoặc giữ nguyên cấu hình `tdq_mcp_launcher.mjs` mà không phá tính đa OS.
- `scripts/tdq_setup.py:368-410` — `khai_server_mcp(project, duong_cau_hinh="~/.claude.json", ...)` — Mặc định sửa `~/.claude.json`; L2134-2136 in nhắc `"Claude Code chỉ đọc cấu hình MCP lúc khởi động: gõ /mcp..."`.
- `scripts/tdq_setup.py:512-549` — `va_hook_xung_dot()` — L525-526 đang có guard `if is_antigravity_host(): return [], []` (bỏ qua hoàn toàn trên Antigravity).
- `scripts/tdq_setup.py:552-563` — `_ban_cai_user(home)` — Đọc cứng `~/.claude/plugins/installed_plugins.json` tìm `tdq-workflow@*`.
- `scripts/tdq_setup.py:566-597` — `_cai_dat_env_timeout_mcp(duong_settings, cham_may=None)` — Ghi `CLAUDE_CODE_MCP_TOOL_IDLE_TIMEOUT=90000` vào `~/.claude/settings.json`.
- `scripts/tdq_setup.py:612-634` — `_tim_cache_plugin_active(home)` — Quét `~/.claude/plugins/installed_plugins.json` và `~/.claude/plugins/cache/tdq-local/tdq-workflow`.
- `scripts/tdq_setup.py:636-671` — `_cap_nhat_permissions_allow(home)` — Ghi `mcp__lsp__*`, `mcp__plugin_tdq-workflow_lsp__*`, `mcp__plugin_tdq-workflow_chrome-devtools__*` vào `~/.claude/settings.json`.
- `scripts/tdq_setup.py:673-698` — `dong_bo_mcp_plugin_cache(home=None, duong_cau_hinh="~/.claude.json", cham_may=None)` — Đồng bộ `~/.claude.json` vào `<cache>/.mcp.json` của Claude.
- `scripts/tdq_setup.py:706-745` — `kiem_plugin_user(home=None, goc_plugin=None, cham_may=None)` — Kiểm bản cài Claude user-scope; khi chạy trên Antigravity mà không cài Claude sẽ báo nợ giả `"plugin tdq-workflow chưa cài ở scope user — chạy /plugin install tdq-workflow@tdq-local"` (L720-721).
- `scripts/tdq_setup.py:755-766` — `la_project_that(cwd)` — Chỉ nhận `.git` hoặc `.claude-plugin` (chưa nhận `.agents` hay `plugin.json` gốc của Antigravity).
- `scripts/tdq_setup.py:768-998` — `tu_dong_cap_nhat_plugin_user`, `THU_MUC_PLUGINS_STAMP = ".claude/plugins"` (L858), `thuc_hien_cap_nhat_remote` (L915) — Toàn bộ luồng auto-update xoay quanh `claude plugin marketplace update tdq-local` và `~/.claude/plugins/marketplaces/tdq-local`.
- `scripts/tdq_setup.py:1108-1171` — `KHOI_HUONG_DAN` & `khoi_huong_dan(goc=None)` — Văn bản mẫu còn `mcp__lsp__start_lsp` (L1110), `EnterPlanMode`/`ExitPlanMode` (L1122, L1127), `AskUserQuestion` (L1128), `bien_plugin="${CLAUDE_PLUGIN_ROOT}"` (L1170).
- `scripts/tdq_setup.py:1414-1431` — `no_skill_khong_ton_tai(project)` — Quét `docs/claude-md-mau.md` và tìm skill ở `[project/skills, ~/.claude/skills]` (L1426).
- `scripts/tdq_setup.py:1508-1520` — `doc_phien_ban_plugin(goc_plugin=None)` — Chỉ đọc `.claude-plugin/plugin.json` và `.codex-plugin/plugin.json`; thiếu `plugin.json` ở gốc gói `tdq-workflow-agy`!
- `scripts/tdq_setup.py:1962-1975` — `_caveman_targets(plugin_root)` — Đã trỏ đúng `~/.gemini/config/plugins/tdq-workflow-agy/mcp_config.json` và `plugin_root/mcp_config.json`.
- `scripts/tdq_setup.py:1989-2025` — `_xu_ly_caveman_flags(args, project)` — Gọi `caveman_config.wrap_mcp_config(Path(mcp_path), proxy_script)` (hiện ghi `sys.executable` vào `mcp_config.json`).
- `scripts/tdq_setup.py:2161-2180` — `is_antigravity_host()` & `_sync_agy_guard_ghim` — Nhận diện qua `TDQ_HOST == "antigravity"` hoặc đường dẫn chứa `/.gemini/config/plugins/`, `/plugins/tdq-workflow-agy/`, `/plugins/tdq-workflow/`, `/antigravity_portable/`; mới chỉ chặn sửa `~/.claude/CLAUDE.md`, chưa tách nhánh cho `kiem_plugin_user`, `khai_server_mcp`, `dong_bo_mcp_plugin_cache`, `tdq_devtool_mcp`.

### 1.2. `scripts/tdq_lsp.py` & `scripts/lsp_module.py`
- `scripts/tdq_lsp.py:289` — `bac1_binary()` — `static_probe` truyền `os.path.expanduser("~/.claude.json")` làm dependency hash input.
- `scripts/tdq_lsp.py:299-304` — `_all_mcp_configs(duong="~/.claude.json")` — Trả về `[duong, os.path.expanduser("~/.gemini/antigravity/mcp_config.json"), plugin_cfg]`: đường dẫn thứ 2 bị lệch (chuẩn Antigravity user MCP là `~/.gemini/config/mcp_config.json` và plugin cài ở `~/.gemini/config/plugins/tdq-workflow-agy/mcp_config.json`).
- `scripts/tdq_lsp.py:329-337` — `bac2_mcp()` — Thông báo lỗi mặc định vẫn ghi `"chưa đăng ký trong ~/.claude.json"` và gợi ý `"agent-lsp init"`.
- `scripts/tdq_lsp.py:346-349` — `_readiness_inputs(project)` — Băm `~/.claude.json` và `~/.claude/settings.json`.
- `scripts/tdq_lsp.py:443-449` — `bac3_language_server(project)` — Gate 3 kiểm `lang_mcp(args, l)`: chú ý trên Antigravity, `plugins/tdq-workflow-agy/mcp_config.json` dùng `"args": ["${PLUGIN_ROOT}/scripts/tdq_mcp_launcher.mjs", "lsp"]` (không có chuỗi `python:pyright...` vì `agent-lsp` tự auto-detect server trên `PATH`!). Do đó `args` có độ dài > 0 nhưng không chứa `:` khiến `chua_khai` đánh trượt Bậc 3 trên Antigravity nếu không nhận diện launcher mode `"lsp"`!
- `scripts/tdq_lsp.py:409-411` — `_chay_doctor(project)` — Lấy `server.get("args")` ghép thẳng vào `[agent_lsp, "doctor"] + args`! Nếu `mcp_config.json` có `"${PLUGIN_ROOT}/scripts/tdq_mcp_launcher.mjs", "lsp"` thì lệnh thành `agent-lsp doctor ${PLUGIN_ROOT}/scripts/tdq_mcp_launcher.mjs lsp` (sai tham số cho `agent-lsp doctor`, cần lọc chỉ lấy arg có dạng `<lang>:<bin>`).
- `scripts/tdq_lsp.py:467-480` — `bac4_quyen_tool()` — L469-471 đã trả `True` nếu thấy `mcp_config.json` cạnh `scripts/`, nhưng nếu gọi từ repo gốc (`scripts/tdq_lsp.py` nơi `mcp_config.json` nằm trong `plugins/tdq-workflow-agy/` hoặc `~/.gemini/config/plugins/tdq-workflow-agy/`) thì rơi xuống đọc `~/.claude/settings.json`!
- `scripts/tdq_lsp.py:535-583` — `_plugin_dang_bat()` & `hook_xung_dot()` — Chỉ quét `~/.claude/plugins/installed_plugins.json` và `~/.claude/plugins/synced/*/*/hooks/hooks.json`; chưa quét `~/.gemini/config/plugins/*/hooks.json`, `~/.gemini/config/hooks.json`, `.agents/hooks.json`.
- `scripts/tdq_lsp.py:747-763` — `kiem_tra_cong_cu_bo_tro(project=None)` — Đã kiểm `~/.gemini/config/plugins/tdq-workflow-agy/mcp_config.json` cho Caveman và probe RTK + `rg`.
- `tools/patches/cli_fixes_a.py:88-96` — `_agy_mcp_candidate_files()` (vá vào `plugins/tdq-workflow-agy/scripts/lsp_module.py`) — Có dòng `os.path.expanduser("~/.gemini/antigravity/mcp_config.json")` cần đổi/bổ sung `~/.gemini/config/mcp_config.json`.

### 1.3. `scripts/setup_status.py`
- `scripts/setup_status.py:41` — `CAU_HINH_CLAUDE = os.path.expanduser("~/.claude.json")`.
- `scripts/setup_status.py:72-74` — `GHI_CHU_SKILL_BUILTIN` nhắc cứng Claude Code.
- `scripts/setup_status.py:328-332` — `_cau_hinh_lsp()` mở cứng `CAU_HINH_CLAUDE` (`~/.claude.json`).
- `scripts/setup_status.py:339-359, 437-445` — `_doc_mcp()` & `thu_thuc_nhan()` gọi cứng `_run_tool("claude", ["mcp", "list"])` và đọc `CAU_HINH_CLAUDE`, chưa có nhánh Antigravity (`agy plugin list --json`, `agy plugin validate --json`, `${PLUGIN_DATA}/setup-state.json`).

### 1.4. `scripts/tdq_devtool_mcp.py`
- `scripts/tdq_devtool_mcp.py:54-63` — `is_enabled(cwd)` đọc `~/.claude/settings.json` (`env.TDQ_ENABLE_DEVTOOL_MCP`).
- `scripts/tdq_devtool_mcp.py:93-119` — `get_chrome_executable()` tìm Google Chrome / Chromium (chưa có Microsoft Edge fallback nếu cần trên Windows mới tinh).
- `scripts/tdq_devtool_mcp.py:121-124` — `get_dev_profile_dir()` trả `~/ChromeDevProfile`, trong khi `plugins/tdq-workflow-agy/mcp_config.json:17` dùng `${PLUGIN_DATA}/chrome-devtools-profile`.
- `scripts/tdq_devtool_mcp.py:126-189` — `check_devtool_setup()` kiểm `plugin_mcp` cạnh `scripts/` (L143), `~/.claude.json` (L139) và `~/.claude/settings.json` (L140).
- `scripts/tdq_devtool_mcp.py:192-256` — `setup_devtool_mcp()` ghi thẳng `npx -y chrome-devtools-mcp@latest` vào `~/.claude.json` và `~/.claude/settings.json` (KHÔNG kiểm `TDQ_KHONG_CHAM_MAY` và không có chế độ Antigravity!).

### 1.5. `scripts/plugin_tiers.py`
- `scripts/plugin_tiers.py:19-25, 61-80` — Quản lý riêng `~/.claude/plugin-tiers.json`, `~/.claude/settings.json` (`enabledPlugins`) và log `~/.claude/logs/plugin-tiers.log`. Hàm `bat_khoa(path, key)` (L110-129) được `tdq_setup.kiem_plugin_user` (L738) gọi cho Claude Code; trên Antigravity bật plugin dùng `agy plugin enable tdq-workflow-agy` hoặc `~/.gemini/config/config.json`.

### 1.6. `scripts/caveman_config.py`
- `scripts/caveman_config.py:74-84` — `config_path(home)` lưu opt-in tại `~/.tdq/caveman.json` (hoặc `TDQ_CAVEMAN_CONFIG`).
- `scripts/caveman_config.py:165-196` — `_split_wrapped_args` & `_wrap_server_entry(entry, proxy_script)` — Ghi đè `entry["command"] = sys.executable`, `entry["args"] = ["-u", str(proxy_script), "--", orig_cmd, *orig_args]` và thêm `entry["env"] = {"PYTHONUTF8": "1", "PYTHONUNBUFFERED": "1"}`.
  - **Hệ quả nghiêm trọng trên Antigravity:** Phá vỡ `"command": "node"` + `"${PLUGIN_ROOT}/scripts/tdq_mcp_launcher.mjs"` trong `mcp_config.json`, chèn đường dẫn Python tuyệt đối của máy cá nhân (sẽ làm rớt test `test_v1_hooks_json_windows_cmd_c_no_quotes_and_protojson` kiểm tra leak đường dẫn cá nhân ở `tests/test_agy_plugin_validate.py:79-81`!).
  - **Lưu ý tương thích ngược:** `tests/test_caveman_setup.py:152-158` đang assert hành vi cũ (`srv["command"] == sys.executable`) khi truyền `SAMPLE_MCP_CONFIG` kiểu Claude (`C:/bin/agent-lsp.exe`, `npx.cmd`). Nếu phát hiện entry dùng `tdq_mcp_launcher.mjs` (hoặc cờ `launcher_mode="node"` / tự động nhận diện `"${PLUGIN_ROOT}/scripts/tdq_mcp_launcher.mjs"` trong `orig_args`), bọc thành `["${PLUGIN_ROOT}/scripts/tdq_mcp_launcher.mjs", "caveman", "--", ...]` với `"command": "node"` sẽ vừa giữ nguyên 100% tính đa OS trên Antigravity vừa giữ xanh toàn bộ unit test cũ của `test_caveman_setup.py`!

### 1.7. `scripts/rtk_integration.py`
- `scripts/rtk_integration.py:69-71` — `_local_bin_dir()` trả `~/.local/bin`.
- `scripts/rtk_integration.py:618-636` — `default_rtk_config_path()` trả đúng chuẩn từng OS (`%APPDATA%\rtk\config.toml`, `~/Library/Application Support/rtk/config.toml`, `~/.config/rtk/config.toml`).
- `scripts/rtk_integration.py:873-901` — `ensure_windows_user_path()` cập nhật `HKCU\Environment\Path` + `SendMessageTimeoutW(HWND_BROADCAST, WM_SETTINGCHANGE)`.
- `scripts/rtk_integration.py:967-1011` — `install_rtk_and_rg(approve=False, ...)` đã tôn trọng `approve=True` và `TDQ_KHONG_CHAM_MAY == "1"` (L982-983).
- `scripts/rtk_integration.py:1014-1017` — `_default_prefs_path()` đã lưu tại `~/.gemini/config/tdq-rtk-prefs.json` (tôn trọng `Path.home()`).

---

## 2. Build, Patch & Sync Pipeline (`tools/` + `scripts/build_portable.py` + `install.py`)

> **Phát hiện kiến trúc cực kỳ quan trọng:** `plugins/tdq-workflow-agy/` KHÔNG phải chỉnh tay trực tiếp mà được **biên dịch từ gốc repo** qua `tools/build_agy_plugin.py` và bộ patch `tools/patches/*.py`! Mọi chỉnh sửa trực tiếp trong `plugins/tdq-workflow-agy/` mà không cập nhật nguồn gốc hoặc `tools/patches/` sẽ bị ghi đè sạch khi chạy `tools/build_agy_plugin.py` hoặc `tools/run_full_verification.py`!

### 2.1. Luồng biên dịch chính: `tools/build_agy_plugin.py` -> `plugins/tdq-workflow-agy/`
- `tools/build_agy_plugin.py:229-245` — `build()`:
  1. Copy `scripts/` sang `stage/scripts` trừ `common_utils.EXCLUDED_SCRIPTS` (`tools/patches/common_utils.py:12-20`: chỉ loại `build_portable.py` và 6 file `canvas_*.py`). **Mọi file mới đặt trong `scripts/` (`tdq_setup_state.py`, `tdq_simulate_verify.py`, `tdq_setup_probe.mjs`, `bootstrap.ps1`, `bootstrap.sh`) sẽ tự động được copy sang `plugins/tdq-workflow-agy/scripts/`!**
  2. Copy `hooks/scripts/` trừ `EXCLUDED_AGY_HOOKS` (`common_utils.py:22-30`).
  3. Copy `skills/` + `portable_src/skills/tdq-checkportable` + `agents/` + `tdq-config.json`.
- `tools/build_agy_plugin.py:247-266` — Thứ tự áp patch:
  - `cli_fixes_a.apply_all(stage / "scripts")` (`tools/patches/cli_fixes_a.py:432-527`): vá `tdq_setup.py`, `tdq_lsp.py`, `tdq_devtool_mcp.py`, `lsp_module.py` bằng `replace_exact` / `.replace()`. **CẢNH BÁO:** `cli_fixes_a.py:435-443` gọi `replace_exact` tìm chuỗi `'    if not nguon_list and GOC_REPO:\n        v_repo = doc_phien_ban_plugin(GOC_REPO)'` (có sentinel `'globals().get("GOC_REPO")'`). Nếu sửa `scripts/tdq_setup.py` hoặc `scripts/tdq_lsp.py`, phải giữ sentinel hoặc cập nhật `cli_fixes_a._patch_tdq_setup_and_lsp` tương ứng!
  - `cli_fixes_b.apply_all(stage / "scripts")` (`tools/patches/cli_fixes_b.py`): vá `tdq_transcript.py`, `tdq_eval_hosts.py`, `skill_inventory.py`, `ensure_utf8_import`.
  - `agy_manifests.generate_*` (`tools/patches/agy_manifests.py:12-259`): sinh đè `plugin.json`, `assets/logo.svg`, `hooks.json`, `mcp_config.json`, `rules/*.md`, `manifest.json`, `README.md`. Lưu ý `generate_manifest_and_readme` (L232-235) hiện chỉ quét `(plugin_root / "scripts").glob("*.py")`.
  - `skills_and_agents.transform_skills` & `transform_agents` (`tools/patches/skills_and_agents.py:12-185`): tự động đổi `${CLAUDE_PLUGIN_ROOT}` -> `${PLUGIN_ROOT}`, `~/.claude/CLAUDE.md` -> `rules/AGENTS.md`, `mcp__lsp__` -> `mcp_tdq-workflow-agy_lsp_`, rồi chạy `relock_token_budget(stage)` (`token_budget.py --goc stage`).
  - `agy_hooks.apply_all` (`tools/patches/agy_hooks.py:2985-3014`): ghi đè `_common.py`, `post_invocation.py`, `subagent_dispatch_gate.py` và chạy `_patch_prompt_context` (L2456), `_patch_session_start` (L2920)... bằng `replace_exact`! **CẢNH BÁO:** Nếu sửa `hooks/scripts/prompt_context.py` hoặc `hooks/scripts/session_start.py`, PHẢI kiểm tra các neo `replace_exact` trong `tools/patches/agy_hooks.py:2456-2962`!
  - `agy_dispatch.apply_dispatch` (`tools/patches/agy_dispatch.py:268-279`): copy `tools/patches/gate_guidance.py` + `gate_guidance.json` và ghi đè `hooks/scripts/dispatch.py`.
  - `agy_launchers.generate_launchers(stage)` (`tools/patches/agy_launchers.py:260-266`): **GHI ĐÈ `scripts/tdq_hook_launcher.mjs` và `scripts/tdq_mcp_launcher.mjs` từ chuỗi hằng `HOOK_LAUNCHER_MJS` và `MCP_LAUNCHER_MJS`!** Mọi thay đổi cho `tdq_mcp_launcher.mjs` (mode `"caveman"`, nạp `${PLUGIN_DATA}/secrets.env`) BẮT BUỘC phải sửa trong `tools/patches/agy_launchers.py`! (Lưu ý: `tests/test_agy_launchers.py:41` assert `generate_launchers` trả đúng `["tdq_hook_launcher.mjs", "tdq_mcp_launcher.mjs"]` — nếu tạo `tdq_setup_probe.mjs` thì đặt ở `scripts/tdq_setup_probe.mjs` hoặc hàm riêng để không phá test này, hoặc cập nhật test).
- `tools/build_agy_plugin.py:143-205` — `_stage_rust_binaries()`:
  - Tự chạy `cargo build --release` cho OS hiện tại (`windows` -> `tdq-dispatch.exe`) khi `Cargo.toml` hoặc `src/*.rs` mới hơn binary (`_rust_binary_stale`, L89-96).
  - Với 2 OS còn lại (`tdq-dispatch-linux-x86_64`, `tdq-dispatch-darwin-arm64`), lấy từ `hooks/rust/tdq-dispatch/prebuilt/` hoặc giữ từ `plugins/tdq-workflow-agy/bin/` và kiểm tra magic bytes (`MZ`, `\x7fELF`, Mach-O). Nếu sửa Rust `src/*.rs`, cần build bản Windows tại chỗ và lưu ý đồng bộ/cross-build cho Linux/macOS nếu test parity trên OS đó.
- `tools/build_agy_plugin.py:271-286` — Cổng kiểm tự động ngay trong lúc build:
  1. `verify_all_py_ast(stage)` parse AST mọi file `.py`.
  2. `node --check` trên **mọi file `stage/scripts/*.mjs`** (nên `tdq_setup_probe.mjs` sẽ tự động được kiểm cú pháp Node!).
  3. `check_md_byte_budgets(stage)` ép mọi `rules/*.md` và `skills/*/SKILL.md` `< 24,000` bytes.

### 2.2. Xuất bản nhánh Release & Bundle cũ: `scripts/build_portable.py`
- `scripts/build_portable.py:738-758, 827-849` — `loc_muc_agy_release` & `sinh_nhanh_release_agy` (`--sinh-release-agy`):
  - Lấy cây `plugins/tdq-workflow-agy/` từ commit nguồn (`dev`) đưa lên gốc nhánh `release/antigravity` (phục vụ `agy plugin install https://github.com/.../tree/release/antigravity`).
  - **Điểm cần chú ý ở L753:** Hiện chỉ ép mode `100755` cho `parts[0] == "bin"` hoặc `(parts[0] == "scripts" and inner.endswith(".mjs"))`. Nếu thêm `scripts/bootstrap.sh`, nên mở rộng điều kiện L753 thành `inner.endswith((".mjs", ".sh"))` để `bootstrap.sh` giữ quyền thực thi `+x` trên Git tree POSIX!
- `scripts/build_portable.py:500-564, 618-633` — `sinh_ban_antigravity` & `sinh_agy_tai_cho` (`--sinh-agy`):
  - Sinh gói portable cũ `tdq-workflow` (vẫn được test bởi `tests/test_sinh_agy.py` và `tests/test_tuong_thich_host.py`). `copy_loc` (L517) copy toàn bộ `scripts/`.

### 2.3. Hai bộ cài User-Level: `tools/install_agy_plugin.py` & `install.py` (+ `install.ps1`/`install.sh`)
- `tools/install_agy_plugin.py:81-126` (`_ensure_binary_executable_and_hooks`) & `install.py:68-113` (`_adjust_hooks_for_platform`):
  - Đều `chmod(0o755)` cho `(dst / "scripts").glob("*.mjs")` và `bin/tdq-dispatch*` trên POSIX (nên bổ sung `*.sh` nếu có `scripts/bootstrap.sh`).
  - `tools/install_agy_plugin.py:135-160` (`_sync_local_mcp`): chỉ chạy khi truyền `--sync-local-mcp`, đọc `~/.claude.json`.
  - Cả hai đều gọi `caveman_config.wrap_mcp_config` khi `--with-caveman` hoặc khi `~/.tdq/caveman.json` đã `enabled: true` (`install_agy_plugin.py:250-272`, `install.py:248-263`) — nên khi sửa `caveman_config.wrap_mcp_config` sang Node launcher mode `"caveman"`, cả hai trình cài đều hưởng lợi tự động!

### 2.4. Cổng nghiêm ngặt `agy plugin validate --strict --json`
- Được khóa tại `tests/test_agy_plugin_validate.py:28-42` và `tests/test_agy_release_e2e.py:81-93`:
  - `findings == []` (0 errors, 0 warnings).
  - `components == {"agents": 8, "hooks": 6, "mcpServers": 3, "rules": 10, "sidecars": 0, "skills": 12}`.
  - `plugin.json` CẤM có `userConfig`; `mcp_config.json` CẤM có `variables` và CẤM lộ đường dẫn máy cá nhân (`Users\admin`, `npx.cmd`, `sys.executable` cứng).
  - Thêm file vào `scripts/` KHÔNG làm đổi bộ đếm `components` của `agy plugin validate`, nhưng thêm skill mới hoặc rule mới sẽ làm đổi số lượng `skills: 12` / `rules: 10` và `md_count == 22` (`test_agy_plugin_validate.py:153`)! Vì vậy mọi tài liệu mở rộng của `tdq-setup` nên đặt trong `skills/tdq-setup/references/*.md` (giữ nguyên 12 skills, 10 rules).

---

## 3. Hook Dispatch Pipeline, Env Vars & JSON Schema

### 3.1. Luồng gọi từ Antigravity Host -> Launcher -> Rust -> Python
1. `plugins/tdq-workflow-agy/hooks.json` (`agy_manifests.py:65-110`): cả 6 events (`SessionStart`, `PreInvocation`, `PreToolUse`, `PostToolUse`, `PostInvocation`, `Stop`) gọi `node scripts/tdq_hook_launcher.mjs --event <Event>`.
2. `tdq_hook_launcher.mjs` (`agy_launchers.py:67-125`):
   - Đặt `cwd: pluginRoot` và gán `env: { ...process.env, PLUGIN_ROOT: pluginRoot }` (giữ nguyên `PLUGIN_DATA` từ tiến trình cha Antigravity nếu có).
   - Ưu tiên chạy Rust binary `bin/tdq-dispatch*`; nếu lỗi/thiếu thì fallback sang Python (`py -3 -X utf8` trên Windows, `python3 -X utf8` trên POSIX, có `isWindowsAppsStub` guard) gọi `hooks/scripts/dispatch.py --event <Event>`.
3. `hooks/rust/tdq-dispatch/src/main.rs:187-202` (`route_event`):
   - `"SessionStart"` -> **`RouteOutcome::DelegatePython`** (L189)! Nghĩa là `SessionStart` hiện LUÔN ủy quyền sang Python `dispatch.py` -> `session_start.py` (file `src/events/session_start.rs` chỉ là thư viện dự phòng/unit test, chưa nối vào `main.rs:189`).
   - `"PreInvocation"` -> **`handle_pre_invocation(payload, workspace_root)`** (`src/events/pre_invocation.rs:189-224`):
     - Nếu là subagent (`is_subagent`, L191-202): xử lý nóng trong Rust (`subagent_resume_decision`).
     - Nếu lượt mới của user (`read_turn_meta` là `None`, hoặc `meta.turn_closed == true`, hoặc `sig != meta.last_user_sig`, hoặc `source` là `compact`/`resume`): trả **`RouteOutcome::DelegatePython`** -> chạy `dispatch.py` -> `prompt_context.py`!
     - Nếu đang giữa lượt (`mid-turn`, `turn_closed == false` và cùng `sig`): xử lý nóng trong Rust, trả `RouteOutcome::Decided(handle_post_invocation(...))`!

### 3.2. Biến môi trường (`PLUGIN_DATA`, `CLAUDE_PLUGIN_DATA`, `PLUGIN_ROOT`, `CLAUDE_PLUGIN_ROOT`)
- `PLUGIN_DATA`:
  - Đã dùng trong `mcp_config.json:17` (`--userDataDir=${PLUGIN_DATA}/chrome-devtools-profile`).
  - **Chưa có bất kỳ dòng đọc `PLUGIN_DATA` nào trong `hooks/rust/tdq-dispatch/` hay `scripts/*.py` hay `hooks/scripts/*.py`!** (Cũng không có `CLAUDE_PLUGIN_DATA`).
  - Khi thiết kế `resolve_plugin_data_dir()` trong cả Python (`scripts/tdq_setup_state.py`) và Rust (`hooks/rust/tdq-dispatch/src/storage.rs` hoặc module mới):
    1. Đọc `PLUGIN_DATA` nếu khác rỗng.
    2. Nếu không có, kiểm tra biến môi trường cô lập `GEMINI_CONFIG_DIR` (dùng bởi `tests/test_rust_dispatch_parity.py:77` và `tdq_test_process.py`!) hoặc `USERPROFILE` / `HOME` -> `<home>/.gemini/antigravity/plugin_data/tdq-workflow-agy`.
    3. **Cảnh báo test cô lập (`tests/test_rust_dispatch_parity.py:57-99`):** `_isolated_env()` sao chép `os.environ` thật rồi ghi đè `HOME`/`USERPROFILE`/`GEMINI_CONFIG_DIR`, nhưng chưa xóa `PLUGIN_DATA`! Nếu chạy `pytest` bên trong phiên Antigravity có sẵn `PLUGIN_DATA` trong `os.environ`, test có thể đọc nhầm `${PLUGIN_DATA}` thật của máy trừ khi `_isolated_env` ghi đè/xóa `PLUGIN_DATA` hoặc `resolve_plugin_data_dir` ưu tiên `TDQ_SETUP_STATE_DIR` / bỏ qua máy thật khi `TDQ_KHONG_CHAM_MAY=1`!
- `PLUGIN_ROOT` & `CLAUDE_PLUGIN_ROOT`:
  - `tdq_hook_launcher.mjs` luôn bơm `PLUGIN_ROOT=<pluginRoot>` vào `env` cho cả Rust (`main.rs:128`) và Python (`dispatch.py`).
  - Trong `dispatch.py:20` (`agy_dispatch.py:25`), `_PLUGIN_ROOT` tính từ `__file__`; trong `session_start.py:56,75`, `GOC_LUAT` và `GOC_PLUGIN` cũng tính từ `__file__`.
  - Trong `skills/*.md`, nguồn dùng `${CLAUDE_PLUGIN_ROOT}` và `tools/patches/skills_and_agents.py:14-15` tự dịch thành `${PLUGIN_ROOT}` khi build sang `plugins/tdq-workflow-agy/`.

### 3.3. Schema JSON Output chuẩn của Antigravity Hook (`injectSteps`)
Khớp 1-1 giữa Rust (`hooks/rust/tdq-dispatch/src/protocol.rs:74-178`, `HookDecision::inject(model_text, user_md)`) và Python (`tools/patches/agy_hooks.py:495-505`, `_build_inject_response()` dùng `emit_context([...])` + `emit_user_markdown(...)`):
```json
{
  "injectSteps": [
    {
      "systemMessage": {
        "systemMessage": "<model_text gửi cho Agent>",
        "metadata": {
          "user_markdown": "<Markdown hiển thị cho User, tối đa 1200 ký tự>"
        }
      }
    }
  ]
}
```
- **Ràng buộc mã cổng (`23 codes`) cực kỳ quan trọng:**
  - `tools/patches/gate_guidance.json:32-56`, `tools/patches/gate_guidance.py:44-46`, `COMMON_PY` (`agy_hooks.py:36-60`) và `tests/test_rust_dispatch_parity.py:46-51` đang khóa cứng `assert len(codes) == 23`!
  - Mã `"SETUP"` (`[TDQ:SETUP]`) **ĐÃ CÓ SẴN** trong 23 mã chuẩn (`GUIDANCE_CODES`)! Nếu dùng tiền tố `[TDQ:SETUP]` (ví dụ `[TDQ:SETUP] Post-restart verification ready — run NOW: ...` hoặc thẻ `GuidanceRepo::format_4part_card("SETUP", ...)`) thì tương thích 100% với toàn bộ hạ tầng hiện có mà không làm gãy `test_rust_dispatch_parity.py:50`! (Nếu muốn thêm mã thứ 24 `SETUP-RESUME` vào `gate_guidance.json`, bắt buộc phải cập nhật đồng bộ cả 4 nơi + `test_rust_dispatch_parity.py:50`).

### 3.4. Điểm cắm chính xác cho `setup-pending.flag` & `Host Session Fingerprint`
1. **Trong Rust `hooks/rust/tdq-dispatch/src/events/pre_invocation.rs:189` (`handle_pre_invocation`):**
   - Ngay sau khi kiểm `is_subagent` (L200-202) — để subagent không bị bơm lệnh setup — kiểm tra `O(1)` sự tồn tại của `<plugin_data>/setup-pending.flag` (`Path::is_file()`, `< 0.05ms` khi không tồn tại).
   - **Chiến lược gọn sạch nhất (Hybrid 2-tier đúng triết lý `tdq-dispatch`):** Khi `setup-pending.flag` KHÔNG tồn tại (99.99% lượt), đi tiếp đường nóng Rust như cũ (`0` chi phí). Khi `setup-pending.flag` CÓ tồn tại, Rust chỉ cần `return RouteOutcome::DelegatePython;`! Khi đó 100% logic đọc `setup-state.json`, kiểm TTL 24h, đo `Host Session Fingerprint` đa OS (`ctypes` Win32 / `/proc` / `ps`) và phát `[TDQ:SETUP]` kèm `emit_user_markdown(...)` nằm tập trung tại **1 nguồn sự thật duy nhất** trong `scripts/tdq_setup_state.py` được gọi bởi `prompt_context.py` (`_agy_pre_invocation_hook`), tránh viết lặp 2 bản Win32/POSIX process tree bằng cả Rust lẫn Python!
2. **Trong Python `hooks/scripts/prompt_context.py` + `tools/patches/agy_hooks.py:2538` (`_agy_pre_invocation_hook`):**
   - Ngay sau khi `sub.get("is_subagent")` trả `False`, kiểm tra `<plugin_data>/setup-pending.flag` qua `tdq_setup_state`:
     - Nếu `status == "awaiting_restart"` và `current_fp == state.host_fingerprint`: `emit_context` + `emit_user_markdown` nhắc nhẹ đóng hẳn và mở lại Antigravity IDE (chỉ nhắc 1 lần mỗi lượt mới `is_new` để không spam mid-turn!).
     - Nếu `status == "awaiting_restart"` và `current_fp != state.host_fingerprint`: chuyển `status = "validating_after_restart"`, ghi `last_resume_fingerprint = current_fp`, `emit_context` + `emit_user_markdown` yêu cầu Agent chạy ngay `--post-restart-verify`.
3. **Trong Python `hooks/scripts/session_start.py:198-326` (+ `tools/patches/agy_hooks.py:2920`):**
   - `kiem_can_setup_lan_dau(cwd)` (L198) hiện bỏ qua khi `not la_project_that(cwd)` (ví dụ mở Antigravity ở màn hình Home trống!). Trên Antigravity (`is_agy()`), cần kiểm thêm `${PLUGIN_DATA}/setup-state.json`: nếu chưa `verified` (hoặc đang có `setup-pending.flag`), vẫn phát nhắc `[TDQ:SETUP]` kể cả khi mở ở thư mục trống, đồng thời gộp gọn với `nhac_rtk` / `nhac_caveman` để không in 3 dòng `[TDQ:SETUP]` rời rạc trên máy mới.

---

## 4. Bản Đồ Các File Test Hiện Hữu Cần Chạy & Bảo Toàn (`tests/test_*.py`)

| Nhóm kiểm thử | Các file test chính (`tests/`) | Ràng buộc / Hợp đồng đang khóa |
|---|---|---|
| **Setup & Auto-Update** | `test_tdq_setup.py`, `test_auto_update_setup.py`, `test_mcp_first_auto_setup.py`, `test_shim_python3.py`, `test_user_scripts_path.py`, `test_auto_fix_python3_hook.py`, `test_tu_khoi_tao.py` | `tests/helper.py:22-26` bật mặc định `TDQ_KHOI_TAO_NEN="0"` và `TDQ_KHONG_CHAM_MAY="1"`; test truyền fake runner / fake home |
| **LSP & 8 Rungs** | `test_tdq_lsp.py`, `test_lsp_module.py`, `test_bac3_khoi_dong.py`, `test_bac_graphify.py`, `test_mot_lenh_kiem.py`, `test_smoke_ngon_ngu.py`, `test_tdq_readiness.py`, `test_setup_status.py`, `test_setup_status_render.py` | Khóa 8 bậc kiểm của `tdq_lsp.py`, parser `agent-lsp doctor`, mã thoát `EXIT_OK=0`, `EXIT_THIEU=3`, `EXIT_SMOKE=4`, và masking secret trong `setup_status.py` |
| **Add-ons (RTK, Caveman, DevTools)** | `test_rtk_integration.py`, `test_tdq_setup_rtk.py`, `test_installer_rtk_trigger.py`, `test_caveman_setup.py`, `test_tdq_mcp_shrink.py`, `test_devtool_mcp_integration.py` | `test_caveman_setup.py:152` kiểm `wrap_mcp_config` trên config kiểu Claude; `test_tdq_setup_rtk.py:156` kiểm định dạng log ISO trên `stderr` và tắt sạch khi `--khong-log` / `TDQ_LOG=0` |
| **AGY Plugin, Build & Release** | `test_agy_plugin_validate.py`, `test_agy_launchers.py`, `test_agy_release_e2e.py`, `test_build_portable.py`, `test_sinh_agy.py`, `test_tuong_thich_host.py`, `test_checkportable.py`, `test_cli_fixes_new01_28.py` | `agy plugin validate --strict --json` 0 lỗi, `components` (8/6/3/10/0/12), 3 binary PE/ELF/Mach-O khác kích thước, `mcp_config.json` không lộ path cá nhân, `generate_launchers` tạo `.mjs` sạch `node --check` |
| **Hooks (Rust & Python Parity)** | `test_rust_dispatch_parity.py`, `test_rust_latency_benchmark.py`, `test_rust_lock_safety.py`, `test_agy_hooks.py`, `test_hooks_dual_protocol.py`, `test_hook_dispatch_contract.py`, `test_hook_dispatch_r1_r3.py`, `test_prompt_context.py` | `test_rust_dispatch_parity.py:50` khóa `len(all_agy_codes) == 23`; stdout 1 dòng JSON hợp lệ; `_isolated_env` cô lập `HOME`/`USERPROFILE` |
| **Skill Docs & Token Budget** | `test_tdq_setup_skill.py`, `test_doc_lint.py`, `test_doc_index.py`, `test_skill_tokens.py`, `test_token_budget.py`, `test_token_budget_lock.py` | `scripts/doc_lint.py:83` khóa `SKILL_LINE_LIMITS["tdq-setup"] = 132`; `doc_index.py` kiểm `<!-- muc-luc-dong -->`; `test_tdq_setup_skill.py:119` bắt buộc `SKILL.md` trỏ tới `uu-tien-tim-kiem-chi-tiet.md`; `token_budget.py --kiem` kiểm ngân sách khóa |

---

## 5. Rà Soát Mọi Đề Cập Tới `Add-on`, `Extension`, `Marketplace` & Phụ Thuộc Plugin

1. **Đường dẫn cá nhân cũ còn sót trong `SKILL.md`:**
   - `skills/tdq-setup/SKILL.md:15-16` & `plugins/tdq-workflow-agy/skills/tdq-setup/SKILL.md:15-16` — Còn ghi cứng đường dẫn máy cá nhân cũ: ``local clone on this machine: `~/Documents/Add_on_for_claude/agent-lsp` ``. Nên dọn sạch khi viết lại `SKILL.md`.
   - `skills/tdq-setup/SKILL.md:54,56,110-122` & `plugins/tdq-workflow-agy/skills/tdq-setup/SKILL.md:54,56,110-122` — Vẫn hướng dẫn `claude mcp add --scope user lsp`, `~/.claude.json`, `~/.claude/settings.json`.
   - `skills/tdq-setup/references/chrome-devtools-mcp-guide.md:1-35` (và bản trong `plugins/tdq-workflow-agy/`) — Chỉ mô tả cấu hình `~/.claude.json` và `~/.claude/settings.json` cho Claude Code, chưa có mục cấu hình tự động qua `tdq_mcp_launcher.mjs` + `${PLUGIN_DATA}/chrome-devtools-profile` của Antigravity.
2. **Quy ước Companion Extensions & Add-ons trong Rules & Docs:**
   - `plugins/tdq-workflow-agy/rules/domain-mcp-first.md:6-9` (`tools/patches/agy_manifests.py:213-217`) — Định nghĩa `Domain Rule: MCP-First & Companion Extensions`: liệt kê 3 MCP servers (`lsp`, `chrome-devtools`, `tavily-primary`) và 4 CLI engines (`Archify`, `Graphify`, `Vision Diff`, `Codex CLI`), cộng thêm `RTK` và `Caveman CCR / MCP Shrink` trong `rules/AGENTS.md:33-34` (`agy_manifests.py:182-183`).
   - `docs/AUDIT-AND-PORTING-PLAN.md:53,131-145` & `docs/MASTER-VERIFICATION-CHECKLIST-AND-EVIDENCE.md:16,21-50` — Phân loại rõ **7 Companion Extensions & MCP Servers** (`lsp`, `chrome-devtools`, `tavily-primary`, `archify`, `graphify`, `vision`, `codex`) + **Host Add-ons** (`rtk` + `rg`, `caveman` MCP shrink proxy).
3. **Đề cập tới `Marketplace` & Cách cài đặt trong `README*` / `UPSTREAM-TRACE.md`:**
   - `README.md:98-100` — Mục `4.1` mô tả `tdq_setup.py` vẫn ghi cứng `~/.claude.json` và `mcp__lsp__*`.
   - `README.md:141-206` — Bảng 4 Hosts: Claude Code & Codex dùng `marketplace.json` (`.claude-plugin/marketplace.json`, `.agents/plugins/marketplace.json`); Antigravity dùng `install.py` / `install.ps1` / `install.sh` hoặc `agy plugin install` (chưa cập nhật Cửa 0 `bootstrap.ps1`/`bootstrap.sh` và URL nhánh `release/antigravity`).
   - `README-Antigravity.md:7-16` — Đã hướng dẫn `agy plugin install https://github.com/TDQUOC/TDQ-Workflow-Antigravity/tree/release/antigravity`, nhưng dòng 7 vẫn giả định máy **đã cài sẵn `agy` và `Node.js`** (nơi sẽ bổ sung Cửa 0 Terminal Bootstrap One-Liner cho máy trắng tinh).
   - `UPSTREAM-TRACE.md:81-88` — Ghi chú cũ nói `agy plugin install` chỉ cài từ thư mục cục bộ (trước khi có nhánh `release/antigravity`).
