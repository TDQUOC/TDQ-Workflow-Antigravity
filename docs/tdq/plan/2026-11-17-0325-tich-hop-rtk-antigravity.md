# PLAN — Tích hợp cộng sinh RTK tối ưu token và tự động kiểm/cài cho Antigravity

Ngày: 2026-11-17 · Spec: ../spec/2026-11-17-0325-tich-hop-rtk-antigravity.md (bản 1.0, ĐÃ DUYỆT) · Lane: full
Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md
Mode thực thi: subagent — đo `tdq_bench.py simulate` (hệ số 1.5x) cho thấy đội thắng (`14.3` phút vs `22.4` phút, chênh `8.1` phút trên 11 task / 3 đợt với 0 HOT FILE) (ĐỀ XUẤT, user chốt lúc duyệt)
Trạng thái plan: HOÀN THÀNH

## Mục lục

- Quy tắc thi hành (áp cho mọi task)
- Thiết kế Trước vs Sau
- P1 — M1 & M2: Lõi `rtk_integration.py` và Chuẩn hóa `search_rules.py`
- P2 — M3: Collapse Cổng `PreToolUse` (`command_gate.py`, `_common.py`, `agy_manifests.py`)
- P3 — M4: Hệ thống Trigger Kiểm & Xin quyền Cài đặt (`install.py`, `tdq_setup.py`, `session_start.py`)
- P4 — M5: Biên dịch Plugin Antigravity & Cài thật E2E (`2a`)
- P5 — Log & test bắt buộc (`muc_qc = ultra`)
- Cụm song song
- Luật file nóng
- Definition of Done

## Quy tắc thi hành (áp cho mọi task)

1. Thứ tự phụ thuộc tuân theo trường `Cần:` và phân đợt song song.
2. Mỗi task: đánh `[~]` khi bắt đầu → viết test trước (`red`) → cài mã nguồn → chạy test xanh (`green`) → đánh `[x]` ngay vào file này.
3. Mỗi bước chạy `py -3 -X utf8 scripts/tdq_test.py vung-cham`; trọn bộ `tron-bo` và agent QC độc lập chạy ở pha QC (`muc_qc = ultra`).
4. Mọi lệnh chạm state workflow trong test phải gắn `TDQ_PROJECT_DIR=<thư mục tạm>` (tuyệt đối không đụng state thật của repo).
5. Không tự động cài thật `rtk`/`rg` ngoài phạm vi test mock khi chưa tới task `T4.2` đã được user duyệt (`2a`).
6. Không commit/push cho đến khi user yêu cầu.
7. Tuân thủ 6 mã cấm cơ học (`ANTI-1` Fake Red, `ANTI-2` Blind Assertion, `ANTI-3` Dirty State Git, `ANTI-4` Late Tick, `ANTI-5` Raw Dump, `ANTI-6` Broad Area).

## Thiết kế Trước vs Sau

| Khía cạnh | Hiện trạng (Trước) | Thiết kế mới (Sau) |
|---|---|---|
| Luồng thực thi `PreToolUse` | Hai tiến trình rời tuần tự (`bash_gate.py` + `search_gate.py`), trung vị `136.29 ms`, đầu ra CLI thô | Một tiến trình hợp nhất `command_gate.py`: chạy `eval_search` → `eval_bash` → `rtk_integration.rewrite_command` qua `overwrite.CommandLine` |
| Chuẩn hóa vỏ `rtk` | `_chuan_hoa` chưa bóc tiền tố `rtk`/`rtk bypass`/`rtk proxy` | Bóc sạch `rtk`, `rtk.exe`, cờ trước lệnh, `bypass`/`proxy`; đưa `rtk read` về `cat` (`DOC_FILE`) |
| Kiểm & xin quyền cài `rtk` + `rg` | Chưa kiểm tra `rtk`/`rg`; thiếu bảo vệ trùng tên *Rust Type Kit* | Trigger `install.py` (`[y/N]` ở TTY), `SessionStart` (`[TDQ:SETUP]` 1 lần/phiên + mute), `tdq_setup.py --with-rtk` kiểm `SHA256` + Collision Guard |

*Đối chiếu sơ đồ kiến trúc:* Tham chiếu [2026-11-17-0325-tich-hop-rtk-antigravity-preview.html](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/spec/2026-11-17-0325-tich-hop-rtk-antigravity-preview.html) (manifest `bf307b94…`, `tdq_archify.py verify` = `current`).

## P1 — M1 & M2: Lõi `rtk_integration.py` và Chuẩn hóa `search_rules.py`

- [x] **T1.1** (e14m) Tạo `scripts/rtk_integration.py` (stdlib-only + Collision Guard + `SHA256` installer + `rewrite_command` + mute prefs) cùng unit test viết đỏ trước — Test: `py -3 -X utf8 -m pytest tests/test_rtk_integration.py -q`
  - Dùng: `tdq-setup`
  - Để: đối chiếu mẫu `cai_agent_lsp` kiểm `SHA256`, ghi nguyên tử `~/.local/bin` và khóa `TDQ_KHONG_CHAM_MAY=1` trong `scripts/tdq_setup.py`
  - Ra: module `scripts/rtk_integration.py` và `tests/test_rtk_integration.py` xanh 100%
  - Kiểm: `py -3 -X utf8 -m pytest tests/test_rtk_integration.py -q`
  - Không dùng cho: tự chạy cài đặt lên máy khi chưa có `approve=True` / `--with-rtk`
  - Chạm: `scripts/rtk_integration.py`, `tests/test_rtk_integration.py`
  - Cần: không
  - Mục tiêu: Cung cấp 1 nguồn stdlib-only duy nhất xử lý probe có Collision Guard, rewrite lệnh an toàn trên PowerShell/venv/subagent QC, merge `config.toml`, cài đặt kiểm `SHA256` + User `PATH`, và lưu cờ mute.
  - Vị trí neo: Hai file tạo mới hoàn toàn tại `scripts/rtk_integration.py` và `tests/test_rtk_integration.py`.
  - Công cụ: Dùng `write_file` để tạo 2 file mới.
  - Ràng buộc: Thuần stdlib (không dependency ngoài), tuân thủ `i18n_check.py` (docstring/log tiếng Anh), log mặc định ISO timestamp ra `stderr` tắt bằng `TDQ_LOG=0`, mỗi hàm `<= 50` dòng.
  - Đặc tả kỹ thuật:
    `locate_rtk_binary() -> str | None`, `locate_rg_binary() -> str | None`
    `probe_rtk(cwd=None, runner=None) -> dict` (trả `valid, version, path, reason, cached`)
    `should_skip_rewrite(cmd: str, role: str = "") -> tuple[bool, str]`
    `rewrite_command(cmd: str, cwd=None, role: str = "", timeout_s: float = 2.0) -> tuple[str, bool, str]`
    `ensure_rtk_config(config_path=None) -> tuple[bool, str]`
    `install_rtk_and_rg(approve: bool = False, edition: str = "full", bin_dir=None, fetcher=None) -> dict`
    `is_prompt_muted(prefs_path=None) -> bool`, `set_prompt_muted(muted: bool, prefs_path=None) -> None`
  - Logic cốt lõi:
    1. Bước 1: `probe_rtk` đọc stat `(path, size, mtime_ns)` và kiểm stamp `.tdq-runtime/rtk-probe.json`; nếu lệch, chạy `--version` (`>= 0.25.0`) VÀ `gain` (`exit 0`, dùng `RTK_DB_PATH` tạm) để loại gói trùng tên *Rust Type Kit*, rồi ghi stamp cache.
    2. Bước 2: `should_skip_rewrite` trả `True` khi `TDQ_RTK=0` hoặc `RTK_DISABLED=1`, lệnh rỗng/`> 32768`, gọi script nội bộ `tdq_*.py` (chỉ kiểm đầu đoạn lệnh, không ăn nội dung commit/echo), gọi `.venv`/`py -3 -m pytest`, hoặc subagent `qc`/`reviewer`/`security` chạy `git diff`; `rewrite_command` chạy `rtk rewrite -- <cmd>` (nhận exit `0`/`3`, fail-open khi lỗi/timeout) và dùng `& '<full_path>'` trên PowerShell nếu `~/.local/bin` chưa nạp `PATH` phiên cha.
    3. Bước 3: `install_rtk_and_rg` từ chối ngay khi `approve=False` hoặc `TDQ_KHONG_CHAM_MAY=1` (nếu không truyền `fetcher`), đối chiếu `SHA256` từ `checksums.txt`/`.sha256` trước khi `os.replace` vào `~/.local/bin`, cập nhật `HKCU\Environment\Path` + `WM_SETTINGCHANGE` trên Windows, và merge `config.toml` có sao lưu `.truoc-tdq.bak`.
  - Ca góc hiểm & TDD:
    - Ca hiểm: Binary giả `rtk --version` ok nhưng `rtk gain` exit 2 (*Rust Type Kit*), đường dẫn `USERPROFILE` có dấu cách khi PowerShell gọi `rtk.exe`, `SHA256` không khớp bị hủy sạch, `TDQ_KHONG_CHAM_MAY=1` từ chối ghi thật.
    - Tiêu chí: `assert probe_rtk(cwd=tmp, runner=fake_typekit)["valid"] is False` và `assert rewrite_command("py -3 -m pytest -q")[1] is False` và `assert install_rtk_and_rg(approve=False)["ok"] is False`.

- [x] **T1.2** (e8m) Viết test đỏ tại `tests/test_search_rules.py` rồi mở rộng `_chuan_hoa` trong `scripts/search_rules.py` và đồng bộ `tools/patches/cli_fixes_a.py` — Test: `py -3 -X utf8 -m pytest tests/test_search_rules.py -q`
  - Chạm: `scripts/search_rules.py`, `tools/patches/cli_fixes_a.py`, `tests/test_search_rules.py`
  - Cần: không
  - Mục tiêu: Đóng đường lách cổng `[TDQ:SEARCH]` qua `rtk grep`, `rtk bypass rg`, `rtk proxy findstr`, `rtk.exe rg` và quy đổi `rtk read` về nhóm đọc file `DOC_FILE`.
  - Vị trí neo: Ngay cạnh `TIEN_TO` (dòng 44) và trong `_chuan_hoa(argv)` (dòng 382–412) của `scripts/search_rules.py`; cuối `_patch_search_rules` (dòng 240) trong `tools/patches/cli_fixes_a.py`; cuối file `tests/test_search_rules.py`.
  - Công cụ: Dùng `edit_file` cho cả 3 file. Cấm `write_file`.
  - Ràng buộc: Tuyệt đối giữ `scripts/search_rules.py` thuần không I/O (`print`/`open` bị cấm bởi `test_log_module_thuan_khong_tu_in`), complexity `<= 10`, độ dài hàm `_chuan_hoa <= 45` dòng.
  - Đặc tả kỹ thuật:
    `RTK_WRAPPER_FLAGS_VAL = {"--db-path", "-c", "--config"}`
    `_strip_rtk_prefix(argv: list[str]) -> list[str]` gọi bên trong `_chuan_hoa(argv)`
  - Logic cốt lõi:
    1. Bước 1: Trong vòng lặp `_chuan_hoa`, tách basename hạ chữ thường bỏ `.exe` của `argv[0]`.
    2. Bước 2: Nếu là `"rtk"`, tiêu thụ cờ trước subcommand (gồm cờ có giá trị), nếu token kế là `"bypass"` hoặc `"proxy"` thì bỏ qua tiếp token đó, nếu là `"read"` thì thay bằng `["cat"] + rest`, rồi tiếp tục vòng lặp bóc `env`/`sudo`/`xargs`.
    3. Bước 3: Đồng bộ vá chuỗi cho `_patch_search_rules` ở `tools/patches/cli_fixes_a.py` (kiểm tra idempotent khi chuỗi đã có sẵn trong nguồn copy).
  - Ca góc hiểm & TDD:
    - Ca hiểm: `C:\Users\admin\.local\bin\rtk.exe bypass rg foo src/`, `rtk --skip-env grep bar scripts/`, `rtk read scripts/search_rules.py`.
    - Tiêu chí: `assert sr.phan_loai("run_command", r"C:\Users\admin\.local\bin\rtk.exe bypass rg foo src/")["loai"] == sr.TIM_CODE` và `assert sr.phan_loai("run_command", "rtk read app.py")["loai"] == sr.KHONG`.

**Xong P1 khi**: `T1.1`, `T1.2` `[x]` và `py -3 -X utf8 -m pytest tests/test_rtk_integration.py tests/test_search_rules.py -q` PASS 100%.

## P2 — M3: Collapse Cổng `PreToolUse` (`command_gate.py`, `_common.py`, `agy_manifests.py`)

- [x] **T2.1** (e10m) Viết test đỏ tại `tests/test_hook_windows.py` rồi nâng cấp `hooks/scripts/_common.py` (cache phiên gộp + `set_overwrite`) và đồng bộ fallback `tools/patches/agy_hooks.py` — Test: `py -3 -X utf8 -m pytest tests/test_hook_windows.py -q`
  - Dùng: `agy-customizations`
  - Để: đối chiếu hợp đồng `PreToolUse` `"overwrite": {"CommandLine": ...}` trong `hooks.md` trước khi thêm emitter
  - Ra: hàm `begin_collapsed_session`, `set_overwrite` và xuất `"overwrite"` ở `_flush_agy_stdout` trong `_common.py`
  - Kiểm: `py -3 -X utf8 -m pytest tests/test_hook_windows.py -q`
  - Không dùng cho: thay đổi schema `PostToolUse` hay danh sách 24 `CODES`
  - Chạm: `hooks/scripts/_common.py`, `tools/patches/agy_hooks.py`, `tests/test_hook_windows.py`
  - Cần: T1.1, T1.2
  - Mục tiêu: Cho phép một tiến trình hook đọc payload một lần cho nhiều gate và trả `"overwrite": {"CommandLine": ...}` hợp chuẩn Antigravity mà không đổi hành vi các hook chạy rời.
  - Vị trí neo: Tại `_RUNTIME_STATE` (dòng 124–133), `_flush_agy_stdout()` (dòng 198–212), `read_payload()` (dòng 362–373) của `hooks/scripts/_common.py`; cùng vùng tương ứng trong `COMMON_PY` của `tools/patches/agy_hooks.py`; cuối `TestCommonMcpNormalization` (sau dòng 294) của `tests/test_hook_windows.py`.
  - Công cụ: Dùng `edit_file` cho cả 3 file. Cấm `write_file`.
  - Ràng buộc: Giữ nguyên `CODES`/`AGY_CODES` đúng 24 mã (`test_hooks_dual_protocol.py`); `_flush_agy_stdout` chỉ chèn `"overwrite"` khi `_RUNTIME_STATE["deny_reason"]` là `None` và `overwrite` không rỗng.
  - Đặc tả kỹ thuật:
    `begin_collapsed_session(payload: dict) -> dict`
    `end_collapsed_session() -> None`
    `set_overwrite(fields: dict[str, str]) -> None`
  - Logic cốt lõi:
    1. Bước 1: Thêm khóa `"overwrite": {}` và `"collapsed_payload": None` vào `_RUNTIME_STATE`.
    2. Bước 2: Trong `read_payload()`, nếu `collapsed_payload` đang bật thì trả bản copy nông mà không đọc lại `sys.stdin` hay xóa `_RUNTIME_STATE`; bình thường chạy y nguyên cũ.
    3. Bước 3: `set_overwrite` hợp nhất `fields` vào `_RUNTIME_STATE["overwrite"]`; `_flush_agy_stdout` ở nhánh `PreToolUse` khi `deny_reason` rỗng và `overwrite` có dữ liệu sẽ thêm `"overwrite": dict(_RUNTIME_STATE["overwrite"])` vào JSON output.
  - Ca góc hiểm & TDD:
    - Ca hiểm: Đã `set_overwrite` rồi sau đó `bash_gate` gọi `block` → output `PreToolUse` chỉ được chứa `"decision": "deny"` và `"reason"`, tuyệt đối không kèm `"overwrite"`.
    - Tiêu chí: `assert json.loads(out) == {"decision": "allow", "overwrite": {"CommandLine": "rtk git status"}}` khi allow và `assert "overwrite" not in json.loads(deny_out)` khi deny.

- [x] **T2.2** (e8m) Viết test đỏ tại `tests/test_bash_gate.py` rồi tách hàm `eval_search` (`search_gate.py`) và `eval_bash` (`bash_gate.py`) dùng chung trong tiến trình — Test: `py -3 -X utf8 -m pytest tests/test_bash_gate.py tests/test_search_gate.py -q`
  - Chạm: `hooks/scripts/bash_gate.py`, `hooks/scripts/search_gate.py`, `tests/test_bash_gate.py`
  - Cần: T1.2, T2.1
  - Mục tiêu: Tách phần xử lý logic khỏi `read_payload()` để `command_gate.py` gọi trực tiếp in-process đồng thời giữ 100% tương thích module cũ và tắt nhắc `[TDQ:OUTPUT]` khi RTK đã nén.
  - Vị trí neo: Tại `def main():` của `hooks/scripts/bash_gate.py` (dòng 152–237) và `hooks/scripts/search_gate.py` (dòng 167–198); cuối `TestNhacTranOutput` của `tests/test_bash_gate.py`.
  - Công cụ: Dùng `edit_file` cho cả 3 file. Cấm `write_file`.
  - Ràng buộc: Giữ nguyên toàn bộ hằng số công khai (`APPROVE_CLI`, `SETPHASE_CLI`, `_enforce_agy_bash_guards`, `quyet`, `do_ngon_ngu_du_an`) để không vỡ `test_bash_gate.py`, `test_search_gate.py`, `test_lane_label.py`, `context_surface.py`.
  - Đặc tả kỹ thuật:
    `bash_gate.eval_bash(payload: dict, suppress_output_remind: bool = False) -> bool` (trả `True` nếu tiếp tục cho qua, `False` nếu đã chặn/dừng)
    `search_gate.eval_search(payload: dict) -> bool` (trả `True` nếu tiếp tục, `False` nếu chặn)
  - Logic cốt lõi:
    1. Bước 1: Rút ruột `bash_gate.main()` vào `eval_bash(payload, suppress_output_remind=False)`: chỉ chạy khối nhắc `DUMP`/`TDQ:OUTPUT` khi `not suppress_output_remind`.
    2. Bước 2: Rút ruột `search_gate.main()` vào `eval_search(payload)` chạy `quyet()` và gọi `_common.block()` khi từ chối.
    3. Bước 3: `main()` của cả hai file chỉ còn gọi `read_payload()` rồi ủy quyền cho `eval_bash`/`eval_search`.
  - Ca góc hiểm & TDD:
    - Ca hiểm: Gọi `bash_gate.eval_bash(payload, suppress_output_remind=True)` với `git diff` không nhắc `[TDQ:OUTPUT]`, còn gọi `bash_gate.main()` trực tiếp với `git diff` vẫn nhắc bình thường cho `test_bash_gate.py`.
    - Tiêu chí: `assert eval_bash(git_diff_payload, suppress_output_remind=True)` không ghi dòng `TDQ:OUTPUT` vào sổ turn.

- [x] **T2.3** (e12m) Tạo `hooks/scripts/command_gate.py`, cập nhật `hooks.json` + `AGENTS.md` trong `tools/patches/agy_manifests.py`, và viết test đỏ/xanh ở `tests/test_command_gate.py` — Test: `py -3 -X utf8 -m pytest tests/test_command_gate.py -q`
  - Chạm: `hooks/scripts/command_gate.py`, `tools/patches/agy_manifests.py`, `tests/test_command_gate.py`
  - Cần: T1.1, T1.2, T2.1, T2.2
  - Mục tiêu: Hợp nhất cổng `run_command` trên Antigravity vào 1 tiến trình `command_gate.py`, gọi `rtk rewrite` xuất `overwrite.CommandLine` và gắn hướng dẫn ngắn `rtk recall`/`bypass` trong `AGENTS.md`.
  - Vị trí neo: Hai file tạo mới `hooks/scripts/command_gate.py` và `tests/test_command_gate.py`; trong `tools/patches/agy_manifests.py` tại `generate_hooks_json` (dòng 117–118) và cuối `generate_two_tier_rules` `agents_md` (trước dòng 202).
  - Công cụ: Dùng `write_file` cho 2 file mới; dùng `edit_file` cho `tools/patches/agy_manifests.py`.
  - Ràng buộc: Lệnh trong `hooks.json` không chứa dấu nháy kép `"` (`test_agy_plugin_validate.py:60`); giữ đủ 6 top-level keys trong `hooks.json`; mọi lỗi bất ngờ fail-open (`sys.exit(0)`), trừ block hợp lệ từ gate.
  - Đặc tả kỹ thuật:
    `command_gate.process_payload(payload: dict) -> str | None` (trả `rewritten_cmd` hoặc `None`)
    `hooks.json` (`agy_manifests.py`): `{"matcher": "run_command", "hooks": [_hook_cmd("command_gate.py", "PreToolUse")]}` và thu hẹp `search_gate.py` về `"grep_search|find_by_name|list_dir|search_directory|find_file|list_directory"`.
  - Logic cốt lõi:
    1. Bước 1: Đọc payload, bật `begin_collapsed_session(payload)`, xác định `cwd`, `role` (`detect_subagent`).
    2. Bước 2: Chạy `search_gate.eval_search(payload)` (bọc bảo vệ `SystemExit` khi bị deny); tiếp theo kiểm tra trước liệu RTK có thể xử lý lệnh này (cho các lệnh `git log`/`git diff`/`git show` đủ điều kiện nén) rồi gọi `bash_gate.eval_bash(payload, suppress_output_remind=...)`.
    3. Bước 3: Nếu không có `deny_reason` và `is_agy()` và tool là `run_command`: gọi `rewrite_command(cmd, cwd, role=role)`; nếu có viết lại, gọi `_common.set_overwrite({"CommandLine": rewritten})` và log ISO ra `stderr`; cuối cùng thoát `end_collapsed_session()`.
  - Ca góc hiểm & TDD:
    - Ca hiểm: `rtk grep foo src/` vẫn bị `[TDQ:SEARCH]` chặn `deny` không bao giờ gọi tới `rtk rewrite`; `git checkout -b claude-x` bị chặn `deny`; `git status` trên máy có `rtk` trả `{"decision": "allow", "overwrite": {"CommandLine": "rtk git status"}}`; payload `{}` rỗng trả exit `0` + `{"decision": "allow"}`.
    - Tiêu chí: `assert resp["decision"] == "deny" and "[TDQ:SEARCH]" in resp["reason"]` cho `rtk bypass rg foo`, và `assert resp["overwrite"]["CommandLine"] == "rtk git status"`.

**Xong P2 khi**: `T2.1`, `T2.2`, `T2.3` `[x]` và `py -3 -X utf8 -m pytest tests/test_hook_windows.py tests/test_bash_gate.py tests/test_search_gate.py tests/test_command_gate.py -q` PASS 100%.

## P3 — M4: Hệ thống Trigger Kiểm & Xin quyền Cài đặt (`install.py`, `tdq_setup.py`, `session_start.py`)

- [x] **T3.1** (e10m) Viết test đỏ tại `tests/test_installer_rtk_trigger.py` rồi bổ sung trigger kiểm & xin quyền cài `rtk` + `rg` vào `install.py`, `install.ps1`, `install.sh`, `tools/install_agy_plugin.py` — Test: `py -3 -X utf8 -m pytest tests/test_installer_rtk_trigger.py -q`
  - Chạm: `install.py`, `install.ps1`, `install.sh`, `tools/install_agy_plugin.py`, `tests/test_installer_rtk_trigger.py`
  - Cần: T1.1
  - Mục tiêu: Tự động kiểm tra `rtk` + `rg` sau khi cài plugin `tdq-workflow-agy`, hỏi `[y/N]` xin quyền khi chạy TTY tương tác và hỗ trợ cờ tự động `--with-rtk`/`--skip-rtk`.
  - Vị trí neo: Tại `main()` và phần `argparse` (dòng 128–202) của `install.py`; `param(...)` của `install.ps1`; cuối `main()` (dòng 42–58) của `tools/install_agy_plugin.py`; thêm chú thích hỗ trợ tham số ở `install.sh`; file test mới `tests/test_installer_rtk_trigger.py`.
  - Công cụ: Dùng `edit_file` cho 4 file sẵn có; `write_file` cho file test mới.
  - Ràng buộc: Khi chạy không tương tác (`not sys.stdin.isatty()`) và không truyền `--with-rtk` (kể cả lúc `test_v1_install_dry_run_and_staged_validate` gọi `install_agy_plugin.py`), tuyệt đối không chờ `input()` và không tự cài thật.
  - Đặc tả kỹ thuật:
    `install.py`: thêm cờ `--with-rtk`, `--skip-rtk` và hàm `_handle_rtk_trigger(args, stdin_tty=None, ask_fn=input) -> int`
    `tools/install_agy_plugin.py`: thêm `--with-rtk`, `--skip-rtk` và in trạng thái `rtk` trong JSON đầu ra.
  - Logic cốt lõi:
    1. Bước 1: Nhập `rtk_integration` từ `scripts/` (an toàn khi chạy ở thư mục gốc hoặc plugin).
    2. Bước 2: Sau bước bật plugin ở `install.py`, gọi `probe_rtk()` và `locate_rg_binary()`; nếu đủ cả hai → in `[OK] rtk (<ver>) & rg ready.` và đảm bảo config hợp chuẩn TDQ (hoặc giữ config sẵn).
    3. Bước 3: Nếu thiếu và không có `--skip-rtk`: nếu `--with-rtk` được truyền → gọi `install_rtk_and_rg(approve=True)`; nếu là TTY tương tác → hiển thị nguồn chính thức (`github.com/rtk-ai/rtk` + `BurntSushi/ripgrep` kiểm `SHA256`, cài vào `~/.local/bin`) và hỏi `[y/N]` trước khi gọi `install_rtk_and_rg(approve=True)`; nếu non-TTY hoặc user chọn No → in hướng dẫn chạy `py -3 install.py --with-rtk` rồi vẫn thoát `0`.
  - Ca góc hiểm & TDD:
    - Ca hiểm: TTY user nhập `"n"` → `install_rtk_and_rg` không bao giờ được gọi; non-TTY chạy CI không treo; `--dry-run --with-rtk` chỉ in kế hoạch không chạm mạng/đĩa.
    - Tiêu chí: `assert install_rtk_called is False` khi user đáp `"n"` hoặc non-TTY, và `assert install_rtk_called is True` khi `--with-rtk` hoặc user đáp `"y"`.

- [x] **T3.2** (e10m) Tích hợp kiểm/cài RTK (`--with-rtk`, `--check-rtk`, `--mute-rtk-prompt`) vào `tdq_setup.py`, `tdq_lsp.py`, `setup_status.py`, `session_start.py` kèm test `tests/test_tdq_setup_rtk.py` & `tests/test_setup_status.py` — Test: `py -3 -X utf8 -m pytest tests/test_tdq_setup_rtk.py tests/test_setup_status.py -q`
  - Chạm: `scripts/tdq_setup.py`, `scripts/tdq_lsp.py`, `scripts/setup_status.py`, `hooks/scripts/session_start.py`, `tests/test_setup_status.py`, `tests/test_tdq_setup_rtk.py`
  - Cần: T1.1, T1.2, T2.1
  - Mục tiêu: Đưa trạng thái `rtk` + `rg` vào công cụ chẩn đoán (`tdq_lsp`, `setup_status`), cho phép cài theo lệnh tường minh `tdq_setup.py --with-rtk`, và phát đúng 1 dòng nhắc `[TDQ:SETUP]` ở `SessionStart` khi thiếu công cụ (có thể mute).
  - Vị trí neo: Tại `parse_args` & `main` (dòng 1880–1945) của `scripts/tdq_setup.py`; tại `kiem_mot_lenh` (dòng 720–742) của `scripts/tdq_lsp.py`; tại `CONG_CU` & `thu_dependency` (dòng 52–57, 205–220) của `scripts/setup_status.py` và `test_du_bon_cong_cu_du_ca_khi_thieu` (dòng 135) của `tests/test_setup_status.py`; tại phần `nhac` (dòng 258–278) của `hooks/scripts/session_start.py`.
  - Công cụ: Dùng `edit_file` cho 5 file sẵn có; `write_file` cho `tests/test_tdq_setup_rtk.py`.
  - Ràng buộc: Tuyệt đối giữ nguyên danh sách 8 bậc trả về của `tdq_lsp.chay_kiem()` để không vỡ `test_tdq_lsp.py`/`test_tdq_readiness.py`; `khoi_tao_nen()` (`--nen`) tuyệt đối không tự tải/cài `rtk`/`rg`; giữ trần `session_start.py` (`TOAN_MAX_LINES = 160`, `TOAN_MAX_CHARS = 8200`).
  - Đặc tả kỹ thuật:
    `tdq_setup.py`: cờ `--with-rtk`, `--check-rtk`, `--mute-rtk-prompt`, `--unmute-rtk-prompt`
    `setup_status.CONG_CU`: thêm `("rtk", ["--version"], ...)` và `("rg", ["--version"], ...)`, kiểm `rtk gain` với Collision Guard
    `session_start.py`: kiểm `rtk_integration.probe_rtk` & `locate_rg_binary` & `is_prompt_muted`, chỉ chèn `[TDQ:SETUP]` 1 lần mỗi phiên (`already_reminded`).
  - Logic cốt lõi:
    1. Bước 1: Trong `tdq_setup.py`, xử lý `--check-rtk`, `--mute-rtk-prompt`, `--unmute-rtk-prompt`, `--with-rtk` (gọi `install_rtk_and_rg(approve=True)`), còn `khoi_tao_nen` và `main` mặc định chỉ kiểm báo trạng thái nếu chưa có `--with-rtk`.
    2. Bước 2: Trong `tdq_lsp.kiem_mot_lenh`, gọi helper phụ `kiem_tra_cong_cu_bo_tro()` in thông tin `rtk` + `rg` cạnh dòng tổng mà không làm đổi số bậc hay mã thoát của 8 bậc LSP; trong `setup_status.py` cập nhật `CONG_CU` và hiển thị cảnh báo `"trùng tên Rust Type Kit"` nếu `rtk --version` chạy được nhưng `rtk gain` thất bại.
    3. Bước 3: Trong `session_start.py`, nếu `is_agy()` (hoặc bất kỳ host nào chưa mute và chưa có đủ `rtk` + `rg` và chưa nhắc trong phiên), phát 1 dòng `[TDQ:SETUP] Missing rtk/rg for token savings — ask user permission to run py -3 scripts/tdq_setup.py --with-rtk (or --mute-rtk-prompt to hide).`
  - Ca góc hiểm & TDD:
    - Ca hiểm: `khoi_tao_nen()` chạy không cài `rtk`; `rtk gain` giả fail bị `setup_status` báo không hợp lệ; `set_prompt_muted(True)` làm `session_start.py` im lặng hoàn toàn dòng nhắc `rtk`.
    - Tiêu chí: `assert "[TDQ:SETUP]" not in out_when_muted` và `assert [h["ten"] for h in setup_status.thu_dependency()] == ["graphify", "agent-lsp", "rtk", "rg"]`.

**Xong P3 khi**: `T3.1`, `T3.2` `[x]` và `py -3 -X utf8 -m pytest tests/test_installer_rtk_trigger.py tests/test_tdq_setup_rtk.py tests/test_setup_status.py tests/test_tdq_lsp.py tests/test_tdq_readiness.py -q` PASS 100%.

## P4 — M5: Biên dịch Plugin Antigravity & Cài thật E2E (`2a`)

- [x] **T4.1** (e8m) Biên dịch đồng bộ `plugins/tdq-workflow-agy/` qua `tools/build_agy_plugin.py`, bổ sung E2E test dual-protocol vào `tests/test_hooks_dual_protocol.py`, và kiểm định `agy plugin validate` — Test: `py -3 -X utf8 -m pytest tests/test_hooks_dual_protocol.py tests/test_agy_plugin_validate.py -q`
  - Chạm: `plugins/tdq-workflow-agy/`, `tests/test_hooks_dual_protocol.py`
  - Cần: T1.2, T2.3, T3.1, T3.2
  - Mục tiêu: Đảm bảo gói plugin xuất bản `plugins/tdq-workflow-agy/` đồng bộ 100% với mã nguồn gốc, đạt chuẩn nghiêm ngặt của `agy.EXE plugin validate`, không chạm `skill` làm lệch `token_budget.py --kiem`.
  - Vị trí neo: Toàn bộ gói biên dịch `plugins/tdq-workflow-agy/`; thêm ca test `test_ec17_command_gate_rtk_collapse_and_setup_notice` ở cuối `tests/test_hooks_dual_protocol.py` (sau dòng 344).
  - Công cụ: Chạy `tools/build_agy_plugin.py` bằng `run_command` và dùng `edit_file` cập nhật `tests/test_hooks_dual_protocol.py`.
  - Ràng buộc: `agy.EXE plugin validate plugins/tdq-workflow-agy --strict --json` trả `0` findings và `components` giữ nguyên (`agents: 6, hooks: 6, mcpServers: 3, rules: 10, sidecars: 0, skills: 12`).
  - Đặc tả kỹ thuật:
    `build_agy_plugin.py` → `"status": "OK"`, `agy.EXE plugin validate` → `findings == []`
    `test_ec17_command_gate_rtk_collapse_and_setup_notice` chạy qua `cmd /c py -3 -X utf8 hooks/scripts/command_gate.py --event PreToolUse` trên bản đã biên dịch.
  - Logic cốt lõi:
    1. Bước 1: Chạy `py -3 -X utf8 tools/build_agy_plugin.py` để biên dịch từ nguồn gốc và kiểm tra `git status` không sót file rác.
    2. Bước 2: Viết ca test E2E chạy thật `command_gate.py` qua `cmd /c`: kiểm tra chặn `rtk bypass grep foo src/` với `[TDQ:SEARCH]`, chặn nhánh `claude-bad` với `[TDQ:GIT]`, phát `overwrite.CommandLine` khi giả lập `rtk` trên PATH tạm, và kiểm tra `session_start.py` nhắc `[TDQ:SETUP]` khi thiếu `rtk`.
    3. Bước 3: Chạy `test_agy_plugin_validate.py` và `token_budget.py --kiem` trong `plugins/tdq-workflow-agy/`.
  - Ca góc hiểm & TDD:
    - Ca hiểm: File `plugins/tdq-workflow-agy/hooks.json` vẫn không có dấu `"`, mọi command trong `hooks.json` chạy với stdin `{}` đều thoát `0`.
    - Tiêu chí: `assert val_data["findings"] == []` và `assert ec17_search_block["decision"] == "deny"`.

- [x] **T4.2** (e8m) Thực thi cài thật user-level `rtk` + `rg` vào `C:\Users\admin\.local\bin` & `%APPDATA%\rtk\config.toml` theo quyền `2a` và nghiệm thu E2E sống — Test: `py -3 -X utf8 scripts/tdq_setup.py --with-rtk; rtk --version; rtk gain; rg --version`
  - Cần: T4.1
  - Mục tiêu: Chứng minh quy trình tải GitHub Release kiểm `SHA256`, cài `~/.local/bin/{rtk,rg}.exe`, cấu hình User `PATH` + `%APPDATA%\rtk\config.toml`, viết lại lệnh qua `command_gate.py --event PreToolUse` và nén output thực qua `rtk git status` + `rtk gain` chạy thông suốt trên máy thật.
  - Ca kiểm: Chạy `py -3 -X utf8 scripts/tdq_setup.py --with-rtk`, kiểm `rtk --version` (`>= 0.25.0`), `rtk gain` (`exit 0`), `rg --version`, thử chạy hook `command_gate.py --event PreToolUse` với đầu vào `git status` kiểm JSON `overwrite.CommandLine`, đo tốc độ trung vị `< 150 ms`, kiểm `tdq_lsp.py check` hiển thị trạng thái `rtk`/`rg` sẵn sàng, và ghi lại hướng dẫn gỡ sạch vào report.

**Xong P4 khi**: `T4.1`, `T4.2` `[x]` và bản cài `rtk` + `rg` sống vượt qua đủ các phép kiểm thực tế trên Windows.

## P5 — Log & test bắt buộc

- [x] **T5.1** (e4m) Kiểm tra Log service bật mặc định có ISO timestamp ra `stderr` và tắt được qua `TDQ_LOG=0` trên `rtk_integration.py`, `command_gate.py`, `tdq_setup.py` — Test: `py -3 -X utf8 -c "import os, subprocess, sys; r1 = subprocess.run([sys.executable, 'hooks/scripts/command_gate.py', '--event', 'PreToolUse'], input='{\"tool_name\":\"run_command\",\"tool_input\":{\"command\":\"git status\"}}', text=True, capture_output=True); r2 = subprocess.run([sys.executable, 'hooks/scripts/command_gate.py', '--event', 'PreToolUse'], input='{\"tool_name\":\"run_command\",\"tool_input\":{\"command\":\"git status\"}}', text=True, capture_output=True, env={**os.environ, 'TDQ_LOG': '0'}); assert r1.returncode == 0 and r2.returncode == 0 and r2.stderr == ''"`
- [x] **T5.2** (e12m) Chạy trọn bộ `scripts/tdq_test.py tron-bo`, các linter (`ruff check --select F,E,B`, `doc_lint.py`, `i18n_check.py`, `token_budget.py --kiem`), cài plugin cục bộ khi được duyệt bước kiểm và gọi agent QC độc lập `tdq-qc-tester` (`muc_qc = ultra`) — Test: `py -3 -X utf8 scripts/tdq_test.py tron-bo --workers 1 --fresh --reuse off --timeout 1800`

### Sửa khuyết điểm QC Vòng 1 (`muc_qc = ultra`)

- [x] **QC1.1** (e6m) Tách nhỏ hàm quá dài/phức tạp (`bash_gate._check_bash_reminders`, `search_rules._chuan_hoa`, `cli_fixes_a._sync_rtk_search_rules`) xuống `<= 35` dòng & `C901 <= 10` — Test: `py -3 -X utf8 -m pytest tests/test_bash_gate.py tests/test_search_rules.py tests/test_command_gate.py -q`
- [x] **QC1.2** (e5m) Khử trùng lặp `import_rtk_integration` qua `tools/patches/common_utils.py`, bỏ biến thừa `py_prefix` (`F841`) + giữ LF `hooks.json` ở `install.py`, rút ngắn dòng `E501` trong `hooks/scripts/command_gate.py` & `tools/install_agy_plugin.py` — Test: `py -3 -X utf8 -m pytest tests/test_installer_rtk_trigger.py tests/test_command_gate.py -q`
- [x] **QC1.3** (e4m) Bổ sung ISO stderr `_log` mặc định (tắt qua `TDQ_LOG=0`/`--khong-log`) vào `scripts/tdq_setup.py` và dòng nhắc RTK ở `hooks/scripts/session_start.py` kèm test ở `tests/test_tdq_setup_rtk.py` — Test: `py -3 -X utf8 -m pytest tests/test_tdq_setup_rtk.py -q`
- [x] **QC1.5** (e8m) Vá 4+2 phát hiện bảo mật từ `tdq-security-reviewer` (chống CWD/`.cmd` hijack trong `scripts/rtk_integration.py` + `scripts/setup_status.py` + `tests/test_hooks_dual_protocol.py` dùng PE `.exe` launcher; chặn lách `rtk bypass --`, `.cmd/.bat`, `/usr/bin/env`, wrapper `-u/-s` và `(C:\...)` trong `scripts/search_rules.py` + `tools/patches/cli_fixes_a.py`), gọn `tdq_setup._xu_ly_rtk_flags <= 40` dòng, LF `install.sh` + `.gitattributes`, thêm `.tdq-runtime/` vào `.gitignore` — Test: `py -3 -X utf8 -m pytest tests/test_rtk_integration.py tests/test_search_rules.py tests/test_installer_rtk_trigger.py tests/test_tdq_setup_rtk.py tests/test_setup_status.py tests/test_hooks_dual_protocol.py -q`
- [x] **QC1.4** (e20m) Biên dịch lại `plugins/tdq-workflow-agy/`, đồng bộ bản cài cục bộ kiểm `BYTE_DIFFS=[]` & `agy plugin validate`, và chạy lại trọn bộ sạch `scripts/tdq_test.py tron-bo --workers 1 --fresh --reuse off --timeout 1800` — Test: `py -3 -X utf8 scripts/tdq_test.py tron-bo --workers 1 --fresh --reuse off --timeout 1800`

## Cụm song song

- **Đợt 1:** `T1.1` (`scripts/rtk_integration.py`, `tests/test_rtk_integration.py`) và `T1.2` (`scripts/search_rules.py`, `tools/patches/cli_fixes_a.py`, `tests/test_search_rules.py`) — hai cụm tách biệt hoàn toàn đường dẫn, chạy song song được ngay.
- **Đợt 2:** `T2.1` → `T2.2` → `T2.3` nối tiếp theo phụ thuộc (`_common.py` → `bash_gate`/`search_gate` → `command_gate`).
- **Đợt 3:** `T3.1` (`install.*`, `tools/install_agy_plugin.py`, `tests/test_installer_rtk_trigger.py`) và `T3.2` (`scripts/{tdq_setup,tdq_lsp,setup_status}.py`, `hooks/scripts/session_start.py`, `tests/{test_setup_status,test_tdq_setup_rtk}.py`) — tách biệt hoàn toàn vùng file sau `T1.1`, chạy song song được.
- **Đợt 4:** `T4.1` → `T4.2` → `T5.1` → `T5.2` tuần tự hoàn tất biên dịch, cài thật theo `2a`, trọn bộ test và QC độc lập `ultra`.

## Luật file nóng

Không có **FILE NÓNG** nào (`0 HOT FILES`): mọi đường dẫn trong trường `Chạm:` giữa toàn bộ các task `T1.1`–`T4.1` đều được tách phân quyền sở hữu đơn nhất để tránh xung đột hợp nhất khi chạy tuần tự lẫn song song.

## Definition of Done

- [x] **Q1 Hiệu năng cổng `PreToolUse` Collapse:** Độ trễ trung vị `command_gate.py` không có `rtk` `<= 110 ms` và khi gọi `rtk rewrite` `<= 150 ms` — `py -3 -X utf8 -m pytest tests/test_command_gate.py -q` và phép đo trung vị trực tiếp bằng `subprocess`
- [x] **Q2 Chặn lách `[TDQ:SEARCH]` và bảo vệ biến thể `rtk`:** `search_rules.phan_loai` bắt trúng `rtk grep`, `rtk bypass rg`, `rtk proxy findstr`, `rtk.exe rg` và giữ thuần không I/O — `py -3 -X utf8 -m pytest tests/test_search_rules.py -q`
- [x] **Q3 Collapse `command_gate`, giữ API cũ & cài `SHA256`:** Xuất `overwrite.CommandLine`, giữ `bash_gate`/`search_gate` cho test/Codex, `TDQ_KHONG_CHAM_MAY=1` chặn chạm máy, `SHA256` và `timeout <= 2 s` fail-open — `py -3 -X utf8 -m pytest tests/test_rtk_integration.py tests/test_hook_windows.py tests/test_bash_gate.py tests/test_installer_rtk_trigger.py tests/test_tdq_setup_rtk.py tests/test_setup_status.py -q`
- [x] **Q4 Biên dịch plugin Antigravity & giữ sạch MIT / token budget:** `build_agy_plugin.py` pass, `agy.EXE plugin validate` trả `0` findings, `token_budget.py --kiem` exit `0` — `py -3 -X utf8 -m pytest tests/test_agy_plugin_validate.py tests/test_hooks_dual_protocol.py -q`
- [x] **Q5 Nghiệm thu sống `rtk` + `rg` (`2a`) & QC `ultra`:** `rtk --version >= 0.25.0`, `rtk gain` exit `0`, hook live + trọn suite + linter + `tdq-qc-tester` đều PASS — `py -3 -X utf8 scripts/tdq_test.py tron-bo --workers 1 --fresh --reuse off --timeout 1800` và `py -3 -X utf8 -m ruff check --select F,E,B scripts hooks tools tests`
