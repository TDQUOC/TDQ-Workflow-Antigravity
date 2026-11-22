# Spec Adversarial Review — `2026-11-22-1521-trien-khai-setup-fully-agy`

- **Đối tượng rà soát:** `docs/tdq/spec/2026-11-22-1521-trien-khai-setup-fully-agy.md` (Bản `1.0`)
- **Đối chiếu với:**
  - `docs/tdq/brief/2026-11-22-1521-trien-khai-setup-fully-agy.md` (`1a 2a 3a 4a 5a`, `muc_qc = ultra`)
  - `docs/tdq/research/2026-11-22-1424-phan-tich-setup-may-trong.md` (`EV-A01..C04`)
  - `docs/tdq/artifacts/2026-11-22-1521-trien-khai-setup-fully-agy/explore-codebase.md`
  - Mã nguồn thực tế: `scripts/doc_lint.py`, `scripts/tdq_plan_scaffold.py`, `scripts/caveman_config.py`, `tools/patches/*`, `tools/build_agy_plugin.py`, `tools/install_agy_plugin.py`, `hooks/rust/tdq-dispatch/`, `tests/test_rust_dispatch_parity.py`, `tests/test_caveman_setup.py`, `tests/test_agy_launchers.py`, `tests/test_tdq_setup_skill.py`.
- **Kết luận cổng Fail-Closed (`confidence >= 0.80`):** **6 phát hiện cần khóa trong Spec v1.1 trước khi trình duyệt / sinh Plan** (0 phát hiện về `doc_lint` R8/R10/R11/R12/R14/R16 hiện tại — các quy tắc máy của `doc_lint.py` đều đã thỏa).

---

## 1. Bảng Kiểm Tra Bất Biến & Quyết Định Người Dùng (`1a 2a 3a 4a 5a`)

| Hạng mục đối chiếu | Trạng thái | Bằng chứng cụ thể |
|---|---|---|
| `doc_lint.py` R8 (`§3b`), R10 (`§2b`), R11 (0 `test_*.py` / `-k`), R12 (`vi`), R14 (`Đo trước` + `Dự phòng`), R16 (`Tóm tắt dễ hiểu`) | **ĐẠT** | `spec:7` (~91 từ, 0 backtick, 0 path), `spec:66` (`§2b`), `spec:124` (`§3b`), `spec:206-217` (`Q1`–`Q8` đủ số đo & dự phòng, 0 tên file test). |
| Bất biến `23` mã cổng AGY (`[TDQ:SETUP]`) | **ĐẠT** | `spec:33,122,213` dùng lại `[TDQ:SETUP]` (khớp `gate_guidance.json` & `tests/test_rust_dispatch_parity.py:50`). |
| Trần `skills/tdq-setup/SKILL.md <= 132` dòng & `md_count == 22` (`< 24000 bytes`) | **ĐẠT** | `spec:63,215,216` tách tài liệu mở rộng sang `references/zero-to-full-agy.md`, giữ nguyên `12` skills & `10` rules. |
| Pipeline `tools/build_agy_plugin.py` + mỏ neo `replace_exact` trong `tools/patches/*` | **ĐẠT (cần giữ chặt ở Plan)** | `spec:59-61,201` đã nêu đồng bộ `agy_launchers.py`, `cli_fixes_a.py`, `agy_hooks.py`; giữ nguyên `generate_launchers` trả 2 tệp `.mjs` (`tests/test_agy_launchers.py:41`). |
| Quyết định `1a` (`"setupfully tdq-workflow"` 1 lệnh + Auto-Resume) | **CẦN BỔ SUNG GUARD** | Xem **Finding 4** (chống khớp nhầm câu trích dẫn/hỏi/phủ định và gỡ mâu thuẫn câu `"no exception"` ở `SKILL.md:29,91`). |
| Quyết định `2a` (Full ecosystem: Core + RTK + Caveman + `Archify` + `chrome-devtools-plugin` + `GEMINI.md` + Tavily `secrets.env`) | **CẦN LÀM RÕ 2 ĐIỂM** | Xem **Finding 2** (Caveman `_split_wrapped_args`) & **Finding 6** (`chrome-devtools-plugin` khi vắng mặt trên máy trắng + kiểm `< 24KB` cho `GEMINI.md`). |
| Quyết định `3a` & `4a` (Triển khai thật lên máy Windows hiện tại có backup + kiểm chứng kép + `muc_qc = ultra`) | **CẦN KHÓA VỊ TRÍ BACKUP & T6** | Xem **Finding 2** (vị trí thư mục backup ngoài `~/.gemini/config/plugins/`) & **Finding 5** (tách `T6` CLI vs Agent live probe dưới trần `120s`). |
| Tương thích `tdq_plan_scaffold.py --from-spec` (`§3c` Contract Signatures) | **LỖI CẤU TRÚC DÒNG** | Xem **Finding 1** (`_process_3c_line` gán `file=""` cho toàn bộ chữ ký hàm mới). |
| Cô lập `PLUGIN_DATA` dưới `TDQ_KHONG_CHAM_MAY=1` trên cả Python và Rust | **THIẾU PHÍA RUST** | Xem **Finding 3** (`pre_invocation.rs` & `_isolated_env` trong `test_rust_dispatch_parity.py:68`). |

---

## 2. Danh Sách Phát Hiện Chi Tiết (Xếp Theo Mức Độ Nghiêm Trọng)

### 1. `[contract-parity]` `docs/tdq/spec/2026-11-22-1521-trien-khai-setup-fully-agy.md:150-157` — `confidence: 0.98` (BLOCKING)
- **Bằng chứng mã nguồn:** Trong `scripts/tdq_plan_scaffold.py:365-385` (`_process_3c_line`), bộ phân tích hợp đồng `--from-spec` xóa `state["file"] = ""` ở đầu mỗi dòng gạch đầu dòng cùng cấp (`elif indent <= state["file_indent"]`) rồi duyệt các cụm backtick **từ trái sang phải**.
- **Vấn đề:** Tất cả các dòng ở `spec:150-157` đều viết theo mẫu `` - `ten_ham(...)` trong `scripts/ten_file.py`: ... ``. Hệ quả là lúc gặp `` `ten_ham(...)` ``, `state["file"]` đang rỗng `""` nên cả 11 hàm mới (`resolve_plugin_data_dir`, `compute_host_session_fingerprint`, `load_setup_state`, `save_setup_state`, `evaluate_restart_resume`, `save_tavily_secret`, `load_secrets_env`, `scan_setup_manifest`, `apply_setup_manifest`, `ensure_archify_installed`, `run_simulate_verify`, `buildSpawnSpec`) đều bị gán `file=""`; ngược lại các token phía sau tên file như `` `TDQ_KHONG_CHAM_MAY=1` `` (`=` trong chuỗi) hoặc `` `PLUGIN_DATA` `` lại bị nhận nhầm thành symbol của file đó! Ngoài ra `§3c` chưa khai chữ ký sửa đổi của `scripts/caveman_config.py`.
- **Cách sửa cụ thể:** Chuyển danh sách chữ ký ở `§3c` sang bảng Markdown 2 cột `| Đường dẫn file | Chữ ký hợp đồng |` (với cột 1 là `` `scripts/...` `` và cột 2 chỉ chứa các chữ ký `` `def ...` `` / `` `function ...` ``), đồng thời bổ sung chữ ký hàm bọc/gỡ của `scripts/caveman_config.py`.

### 2. `[contradictions]` `docs/tdq/spec/2026-11-22-1521-trien-khai-setup-fully-agy.md:59,157,203` — `confidence: 0.95` (BLOCKING)
- **Bằng chứng mã nguồn:**
  1. `scripts/caveman_config.py:165-177,287` (`_split_wrapped_args` & `_inspect_mcp_file`): chỉ nhận diện entry đã bọc khi phần trước `"--"` chứa tệp tên `PROXY_SCRIPT_NAME` (`"tdq_mcp_shrink.py"`), và `_wrap_server_entry` (`L191-194`) luôn chèn `env: {"PYTHONUTF8": "1", "PYTHONUNBUFFERED": "1"}` + ghi `mcp_config.json.bak` cạnh `mcp_config.json` (`L234-236`).
  2. `tests/test_caveman_setup.py:152-158`: khóa cứng hành vi cũ (`command == sys.executable` + `tdq_mcp_shrink.py`) cho cấu hình kiểu Claude (`C:/bin/agent-lsp.exe`, `npx.cmd`).
- **Vấn đề:**
  1. Nếu trên Antigravity bọc thành `"command": "node"`, `"args": ["${PLUGIN_ROOT}/scripts/tdq_mcp_launcher.mjs", "caveman", "--", ...]` mà không cập nhật `_split_wrapped_args` & `_unwrap_server_entry`, thì `probe_caveman()` trả `mcp_wrapped_servers == []` (làm trượt tầng `T5`), gọi `wrap_mcp_config` lần 2 sẽ bọc chồng 2 lớp (mất tính idempotent), và `unwrap_mcp_config` không gỡ được!
  2. Ở `spec:203` & `Q8` (`spec:216`), nếu sao lưu thư mục `~/.gemini/config/plugins/tdq-workflow-agy` sang một thư mục anh em ngay bên trong `~/.gemini/config/plugins/` (ví dụ `tdq-workflow-agy.bak`), `agy plugin list` sẽ quét trúng 2 plugin trùng tên `"tdq-workflow-agy"` trong `~/.gemini/config/plugins/`.
- **Cách sửa cụ thể:** Khóa rõ trong `§3c` & `O3`: `caveman_config._wrap_server_entry` tự động chọn chế độ Node launcher (`["${PLUGIN_ROOT}/scripts/tdq_mcp_launcher.mjs", "caveman", "--", orig_cmd, *orig_args]`, không chèn `sys.executable`) khi thấy `tdq_mcp_launcher.mjs` trong `entry["args"]` (giữ nguyên nhánh `sys.executable` cho entry kiểu Claude để xanh `test_caveman_setup.py`), còn `_split_wrapped_args` nhận diện cả hai mẫu bọc; khóa rõ bản sao lưu thư mục plugin máy thật (`3a`) phải đặt tại `${PLUGIN_DATA}/backups/<timestamp>/` (bên ngoài `~/.gemini/config/plugins/`).

### 3. `[contradictions]` `docs/tdq/spec/2026-11-22-1521-trien-khai-setup-fully-agy.md:33,61,150,162` — `confidence: 0.92` (BLOCKING)
- **Bằng chứng mã nguồn:** `hooks/rust/tdq-dispatch/src/events/pre_invocation.rs:189` chạy trong tiến trình Rust, còn `tests/test_rust_dispatch_parity.py:57-99` (`_isolated_env`) khởi tạo `env = dict(os.environ)` (sao chép nguyên `PLUGIN_DATA` thật nếu đang chạy test từ bên trong phiên Antigravity IDE) rồi chỉ ghi đè `HOME`, `USERPROFILE`, `GEMINI_CONFIG_DIR`, `TDQ_KHONG_CHAM_MAY="1"`.
- **Vấn đề:** `spec:150,173` chỉ định nghĩa thứ tự cô lập `TDQ_SETUP_STATE_DIR` / `TDQ_KHONG_CHAM_MAY=1` cho hàm Python `resolve_plugin_data_dir()`, chưa định nghĩa hàm tương đương phía Rust `tdq-dispatch` và chưa nêu cập nhật `_isolated_env`. Nếu trên máy thật đang có `setup-pending.flag` trong `${PLUGIN_DATA}` (ví dụ ngay cuối Pha 1 hoặc khi chạy test), nhị phân Rust đọc thẳng `PLUGIN_DATA` sẽ ép mọi lượt mid-turn `PreInvocation` sang `DelegatePython`, phá vỡ các bài test đường nóng trong `test_rust_dispatch_parity.py` và `test_rust_latency_benchmark.py`.
- **Cách sửa cụ thể:** Khóa đồng bộ quy tắc phân giải đường dẫn `setup-pending.flag` ở cả Rust (`hooks/rust/tdq-dispatch/src/storage.rs` / `pre_invocation.rs`) và Python: `TDQ_SETUP_STATE_DIR` -> nếu `TDQ_KHONG_CHAM_MAY == "1"` thì bỏ qua `PLUGIN_DATA` và dùng `<GEMINI_CONFIG_DIR>/antigravity/plugin_data/tdq-workflow-agy` -> `PLUGIN_DATA` -> `<HOME>/.gemini/antigravity/plugin_data/tdq-workflow-agy`; đồng thời dọn `PLUGIN_DATA` trong `_isolated_env` của `tests/test_rust_dispatch_parity.py`.

### 4. `[contradictions]` `docs/tdq/spec/2026-11-22-1521-trien-khai-setup-fully-agy.md:33,63,160` — `confidence: 0.88` (BLOCKING)
- **Bằng chứng mã nguồn:** `hooks/scripts/prompt_context.py:136-151` (`_has_prompt_grant_blockers`) bảo vệ các lệnh nhạy cảm khỏi câu hỏi (`?`), phủ định, trích dẫn (`"..."`) và prompt thảo luận spec/hook; trong khi `skills/tdq-setup/SKILL.md:29,91` hiện khẳng định `"each one needs the user's yes first — that rule has no exception"`.
- **Vấn đề:**
  1. Nếu `prompt_context.py` khớp chuỗi `"setupfully tdq-workflow"` bằng phép tìm chuỗi con đơn giản (`in low`), bất kỳ lượt chat nào nhắc tới cụm này trong ngoặc kép (khi review spec, viết tài liệu, hỏi đáp) cũng sẽ bị bơm nhầm chỉ dẫn `[TDQ:SETUP]` chạy `--setupfully`!
  2. Nếu cập nhật `SKILL.md` mà không sửa câu `"has no exception"` ở mục `The one hard rule`, luật trong `SKILL.md` sẽ tự mâu thuẫn với hành vi chạy thẳng 1 mạch của `"setupfully tdq-workflow"` (quyết định `1a`).
- **Cách sửa cụ thể:** Khóa rõ trong `§3c` rằng bộ nhận diện lệnh `"setupfully tdq-workflow"` trong `prompt_context.py` chỉ kích hoạt ở lượt người dùng thật (`is_new`), không nằm trong trích dẫn/câu hỏi/phủ định/meta-prompt (tái sử dụng `_has_prompt_grant_blockers`), và cập nhật `skills/tdq-setup/SKILL.md` (`<= 132` dòng) xác định câu lệnh tường minh `"setupfully tdq-workflow"` chính là sự phê duyệt trọn gói user-space của người dùng (trong khi `/tdq-setup` thông thường vẫn trình bảng kê 1 lần và không bao giờ tự sửa plugin bên thứ ba).

### 5. `[testability]` `docs/tdq/spec/2026-11-22-1521-trien-khai-setup-fully-agy.md:156,214,216` — `confidence: 0.90` (BLOCKING)
- **Bằng chứng mã nguồn:** `docs/tdq/research/2026-11-22-1424-phan-tich-setup-may-trong.md:211` xác định tầng `T6` gồm lời gọi thật vào công cụ `mcp_tdq-workflow-agy_lsp_*` và subagent `tdq-explorer` của phiên Antigravity; `skills/tdq-build/references/qc.md:101-108` áp trần `120 giây` cho mỗi phép kiểm smoke/runtime ở `muc_qc = ultra`.
- **Vấn đề:** `spec:156` và `Q6` (`spec:214`) đặt toàn bộ `T1`–`T6` nằm trọn bên trong hàm CLI `run_simulate_verify()` của `scripts/tdq_simulate_verify.py`. Tuy nhiên, một tiến trình con Python độc lập không có quyền gọi vào runtime tool bus nội bộ `mcp_tdq-workflow-agy_*` hay tạo subagent thật của Antigravity Host — nếu không phân tách rõ phần việc của CLI vs phần việc của Agent ở `T6`, lúc viết code dễ rơi vào kiểm tra giả tạo (`ANTI-6`).
- **Cách sửa cụ thể:** Nêu rõ ranh giới `T6` ở `§3c`, `Q6` và `Q8`: trong `tdq_simulate_verify.py` (`< 90s`), `T6` kiểm tra tính toàn vẹn của `8` tệp `agents/*.md` và giả lập luồng hook subagent (`PreInvocation` với `agent_type`/`is_subagent=true` + `SubagentStop`); còn phép gọi sống `mcp_tdq-workflow-agy_lsp_*` + điều phối subagent thật được thực thi bởi chính Agent hậu Restart và trong cổng runtime test `muc_qc=ultra` (`Q8`, mỗi phép kiểm dưới trần `120s`).

### 6. `[gaps]` `docs/tdq/spec/2026-11-22-1521-trien-khai-setup-fully-agy.md:31,58,59,161,212,215` — `confidence: 0.85` (BLOCKING)
- **Bằng chứng mã nguồn:**
  1. Quyết định `2a` (`brief:92`): bao gồm kiểm/bật `chrome-devtools-plugin` và ghim `GEMINI.md` chuẩn Antigravity (`<= 24,000 bytes`, `research:104,210`).
  2. `tools/install_agy_plugin.py:92`: hiện chỉ `chmod(0o755)` cho `(dst / "scripts").glob("*.mjs")`, chưa gồm `*.sh` như `brief:51` đã chỉ ra.
  3. `scripts/tdq_setup.py:1108-1171`: `KHOI_HUONG_DAN` hiện tại chứa cứng `mcp__lsp__start_lsp`, `EnterPlanMode`, `AskUserQuestion`, `${CLAUDE_PLUGIN_ROOT}`.
- **Vấn đề:**
  1. Trên máy trắng tinh mới chạy Cửa 0, chỉ có `tdq-workflow-agy` được cài (vốn đã đóng gói sẵn MCP `chrome-devtools` trong `mcp_config.json`), còn plugin rời `chrome-devtools-plugin` có thể chưa được cài trong `~/.gemini/config/plugins/`. Nếu `tdq_setup.py --setupfully` gọi thẳng `agy plugin enable chrome-devtools-plugin` khi thư mục plugin đó chưa tồn tại, lệnh sẽ báo lỗi.
  2. `O2` (`spec:58`) mới liệt kê gắn `0755` cho `*.sh` ở `build_portable.py` và `install.py`, bỏ sót `tools/install_agy_plugin.py:92`.
  3. `Q4`/`Q7` (`spec:212,215`) chưa có điều kiện PASS kiểm `~/.gemini/GEMINI.md` đạt `< 24000 bytes` và không rò chuỗi của Claude (`mcp__lsp__`, `CLAUDE_PLUGIN_ROOT`, `EnterPlanMode`).
- **Cách sửa cụ thể:** Quy định rõ ở `§1`/`§3c` rằng `chrome-devtools-plugin` được kiểm qua `agy plugin list --json` (nếu đã cài thì đảm bảo `enabled: true`, nếu chưa cài thì xếp vào `Optional Companion` không chặn `Core Gate` vì `tdq-workflow-agy` đã có sẵn server `chrome-devtools`); bổ sung `chmod 0755` cho `*.sh` vào `tools/install_agy_plugin.py` ở `O2`/`O3`; và thêm điều kiện kiểm `~/.gemini/GEMINI.md` (`< 24000 bytes`, chuẩn Antigravity, idempotent) vào `Q4`.
