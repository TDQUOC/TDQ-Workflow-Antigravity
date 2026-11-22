# Plan Adversarial Audit — `2026-11-22-1521-trien-khai-setup-fully-agy`

- **Đối tượng kiểm toán:** `docs/tdq/plan/2026-11-22-1521-trien-khai-setup-fully-agy.md`
- **Đối chiếu với Spec đã niêm phong SHA256:** `docs/tdq/spec/2026-11-22-1521-trien-khai-setup-fully-agy.md` (Bản `1.0`, ĐÃ DUYỆT — tuyệt đối không sửa Spec)
- **Kết luận cổng Fail-Closed (`confidence >= 0.80`):** **5 phát hiện cần chỉnh ngay trong Plan trước khi trình người dùng duyệt** (để tránh gãy khi thi hành `Mode thực thi: subagent` và `muc_qc = ultra`).

---

## 1. Bảng Đối Chiếu Toàn Diện Spec ↔ Plan

| Hạng mục kiểm toán | Kết quả | Bằng chứng kiểm chứng |
|---|---|---|
| Độ phủ `§2` (`O1`–`O8`) & `§2b` (7 ranh giới module) | **ĐẠT 100%** | `O1→T1.1`, `O2→T1.2`, `O3→T1.3`, `O4→T2.1`, `O5→T2.2`, `O6→T2.3`, `O7→T3.1`, `O8→T3.2` + `T4.1/T4.2` cho `§4`. |
| Hợp đồng năng lực `§3b` (`DÙNG`: `agy-customizations`, `plugin`) | **ĐẠT (cần sửa path `Kiểm:` ở `T3.2`)** | Cả 2 khối ở `T1.1` (`plan:68-72`) và `T3.2` (`plan:151-155`) có đủ 5 trường `Dùng/Để/Ra/Kiểm/Không dùng cho` trong phạm vi 8 dòng của `doc_lint --pair`, nhưng `plan:154` đang ghi cứng đường dẫn máy cá nhân `C:/Users/admin/...` (xem **Finding 4**). |
| Độ phủ 17 chữ ký hợp đồng `§3c` & `Ownership Map` | **17/17 CÓ MẶT (cần khóa schema trả về & lazy import)** | Toàn bộ 17 hàm/symbol của `spec:153-169` đều có đúng 1 chủ sở hữu trong `plan:57-64`, nhưng thiếu khóa schema dict của `evaluate_restart_resume` giữa các subagent và chiều gọi ngược `T2.1 -> T2.3` (xem **Finding 3**). |
| Ràng buộc `§5`, `tools/patches/*` & va chạm tập `Chạm:` | **0 TRÙNG FILE (cần bổ sung neo `tdq_lsp.py` & bỏ sửa tay `plugins/`)** | Đã khai đủ `agy_launchers.py`, `cli_fixes_a.py`, `agy_hooks.py`, `build_agy_plugin.py`, `install_agy_plugin.py`; 0 cặp task trùng `Chạm:`, nhưng `T2.1` sót 4 neo của `tdq_lsp.py`/`cli_fixes_a.py` (**Finding 2**) và `T3.2` hướng dẫn `Edit` tay `plugins/tdq-workflow-agy/{mcp_config,hooks}.json` (**Finding 4**). |
| Chất lượng `R15-Full` (`<= 30` dòng/task, EARS, ANTI-2, R16, Model & Effort) | **ĐẠT** | Cả 10 task dài `8–15` dòng (`<= 30`), đủ trường `R15-Full`, 0 placeholder cấm, 9 biểu thức `assert` hợp lệ AST không mù (`ANTI-2`), `## Phân bổ Model & Effort` phủ đủ `implement/qc/report` (chỉ có 1 link tương đối lệch bậc ở `plan:26`). |
| Đối xứng `§6` `Q1`–`Q8` ↔ `Definition of Done` (`plan:206-213`) | **8/8 DÒNG KHỚP (cần chỉnh lệnh `Q6` & `Q8`)** | Có đủ 8 dòng `Q1`–`Q8`, mọi lệnh chạy được trên PowerShell Windows (`py -3 -X utf8`), nhưng lệnh `Q6` chạm thẳng `${PLUGIN_DATA}` thật và `Q8` chưa phản ánh bước kiểm runtime MCP/subagent dưới `120s` (**Finding 5**). |

---

## 2. Danh Sách Phát Hiện Chi Tiết (Xếp Theo Mức Độ Nghiêm Trọng)

### 1. `[ordering]` `docs/tdq/plan/2026-11-22-1521-trien-khai-setup-fully-agy.md:116,121,124` — `confidence: 0.98` (BLOCKING)
- **Bằng chứng mã nguồn:** `tests/test_rust_dispatch_parity.py:22-25` chạy nhị phân đã đóng gói tại `plugins/tdq-workflow-agy/bin/tdq-dispatch.exe` và `plugins/tdq-workflow-agy/hooks/scripts/dispatch.py`.
- **Vấn đề:** `T2.2` chạy ở **Đợt 3** (`Chạm:` chỉ gồm nguồn `hooks/rust/tdq-dispatch/src/*`, `hooks/scripts/*`, `tools/patches/agy_hooks.py`), trong khi bước biên dịch `tools/build_agy_plugin.py` cập nhật `plugins/tdq-workflow-agy/` nằm ở **`T3.2` (Đợt 5)**. Nếu `tests/test_hook_setup_resume.py` ở `T2.2` gọi vào `plugins/tdq-workflow-agy/`, bài test sẽ đỏ ở Đợt 3 vì gói chưa biên dịch; ngược lại nếu subagent `T2.2` tự chạy `build_agy_plugin.py` ở Đợt 3 thì sẽ làm bẩn hàng trăm tệp trong `plugins/tdq-workflow-agy/**` ngoài vùng `Chạm:` (vi phạm `edit_gate` / `TDQ:TEAM` và gây xung đột merge worktree với Đợt 4–5).
- **Cách sửa cụ thể:** Ghi rõ trong `Logic cốt lõi` và `Test:` của `T2.2`: chạy `cargo test --manifest-path hooks/rust/tdq-dispatch/Cargo.toml` và thiết kế `tests/test_hook_setup_resume.py` kiểm trực tiếp nhị phân `hooks/rust/tdq-dispatch/target/release/tdq-dispatch*` cùng bản vá `agy_hooks.apply_all` dựng trên `tmp_path` (không phụ thuộc và không ghi vào `plugins/tdq-workflow-agy/` trước `T3.2`).

### 2. `[gaps]` `docs/tdq/plan/2026-11-22-1521-trien-khai-setup-fully-agy.md:108,111,114` — `confidence: 0.97` (BLOCKING)
- **Bằng chứng mã nguồn:** Trong `scripts/tdq_lsp.py` và `scripts/setup_status.py` hiện tại có 4 điểm gãy cụ thể trên Antigravity (đã ghi nhận tại `brief:52` & `explore-codebase.md:32-41`):
  1. `tdq_lsp.py:299-304` (`_all_mcp_configs`) và `tools/patches/cli_fixes_a.py:93` (`_agy_mcp_candidate_files`) trỏ nhầm `~/.gemini/antigravity/mcp_config.json` thay vì `~/.gemini/config/mcp_config.json`;
  2. `tdq_lsp.py:443-449` (`bac3_language_server`, Gate 3): kiểm `lang_mcp(args, l)` — trên Antigravity, `args` là `["${PLUGIN_ROOT}/scripts/tdq_mcp_launcher.mjs", "lsp"]` (hoặc bọc `"caveman"`) không chứa chuỗi `<lang>:<bin>`, nên Gate 3 luôn đánh trượt Bậc 3 và báo nợ giả!
  3. `tdq_lsp.py:409-411` (`_chay_doctor`) và `setup_status.py:448` (`thu_thuc_nhan`): truyền nguyên danh sách `args` chứa tệp `.mjs` vào `agent-lsp doctor`, làm hỏng lời gọi CLI;
  4. `tdq_lsp.py:535-583` (`hook_xung_dot`): chỉ quét `~/.claude/plugins/` mà chưa quét `~/.gemini/config/plugins/*/hooks.json` và `~/.gemini/config/hooks.json`.
- **Vấn đề:** `T2.1` (`plan:111,114`) mới chỉ liệt kê sửa `bac2_mcp` (`L329-336`) và `bac4_quyen_tool` (`L467-479`) của `tdq_lsp.py`, bỏ sót cả 4 điểm trên nên `tdq_lsp.py check` (cổng `Q4`) vẫn sẽ báo trượt Bậc 3 trên môi trường Antigravity thuần!
- **Cách sửa cụ thể:** Bổ sung vào `Neo & Công cụ` và `Logic cốt lõi` của `T2.1` các neo `_all_mcp_configs` (`L299-304`), `_chay_doctor` (`L409-411`), `bac3_language_server` (`L443-449`), `hook_xung_dot` (`L535-583`) trong `tdq_lsp.py` cùng `_agy_mcp_candidate_files` (`cli_fixes_a.py:88-96`) và bộ lọc tham số `<lang>:<bin>` cho `agent-lsp doctor` ở cả `tdq_lsp.py` lẫn `setup_status.py` (miễn Gate 3 khi `args` dùng `tdq_mcp_launcher.mjs` mode `"lsp"`/`"caveman"`).

### 3. `[contract-parity]` `docs/tdq/plan/2026-11-22-1521-trien-khai-setup-fully-agy.md:59,64,76,81,110,120` — `confidence: 0.95` (BLOCKING)
- **Bằng chứng mã nguồn:**
  1. `T1.1` (`plan:81`) kiểm `assert resume["action"] == "run_verify"`, nhưng `Ownership Map` (`plan:59`) và `Giao tiếp:` của `T2.1` (`plan:110`) / `T2.2` (`plan:120`) không khai báo các giá trị hợp lệ của trường `"action"`, trong khi tài liệu nghiên cứu tiền nhiệm (`research:168-184`) từng viết `"trigger_verify"`.
  2. `Ownership Map` (`plan:64`) ghi `T2.1` (`tdq_setup.py --post-restart-verify`, chạy ở **Đợt 2**) tiêu thụ `run_simulate_verify` của `T2.3` (`scripts/tdq_simulate_verify.py`, mãi tới **Đợt 4** mới được tạo).
- **Vấn đề:** Ở chế độ `subagent`, mỗi task chạy trong một worktree độc lập: (a) subagent `T2.2` rất dễ kiểm lệch tên khóa/giá trị (`"trigger_verify"` thay vì `"run_verify"`), làm đứt mạch nối tiếp hậu Restart; (b) nếu subagent `T2.1` đặt `import tdq_simulate_verify` ở đầu `scripts/tdq_setup.py`, mọi lệnh nạp `tdq_setup` ở Đợt 2 và Đợt 3 sẽ sập vì `ModuleNotFoundError`.
- **Cách sửa cụ thể:** Khóa rõ schema trả về của `evaluate_restart_resume` ngay tại `Ràng buộc toàn cục` / `Ownership Map` (`{"action": "none" | "remind_restart" | "run_verify", "reason": str, "state": dict}`); đồng thời quy định trong `T2.1` rằng cờ `--post-restart-verify` nạp trễ `import tdq_simulate_verify` bên trong hàm xử lý và chuyển bài test gọi tích hợp `tdq_setup.py --post-restart-verify` về `T2.3` (Đợt 4).

### 4. `[contradictions]` `docs/tdq/plan/2026-11-22-1521-trien-khai-setup-fully-agy.md:26,154,157,160` — `confidence: 0.93` (BLOCKING)
- **Bằng chứng mã nguồn:**
  1. `tools/build_agy_plugin.py:253-254,287` tự sinh sạch `hooks.json` và `mcp_config.json` (chưa bọc Caveman theo `tests/test_agy_plugin_validate.py:160`) rồi đồng bộ đè toàn bộ thư mục `plugins/tdq-workflow-agy/`.
  2. `plan:154` ghi cứng `C:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/plugins/tdq-workflow-agy` trong trường `Kiểm:` của `T3.2`.
  3. `plan:26` ghi `[subagent-tuning.md](../../plugins/...)` từ vị trí `docs/tdq/plan/` (thiếu một bậc `../`).
- **Vấn đề:**
  1. `T3.2` (`plan:160`) hướng dẫn `` `Edit` trên `plugins/tdq-workflow-agy/mcp_config.json`, `plugins/tdq-workflow-agy/hooks.json` `` — vi phạm bất biến không sửa tay thư mục gói biên dịch và sẽ bị `build_agy_plugin.py` ghi đè hoặc làm bẩn `mcp_config.json` mẫu của kho mã!
  2. Đường dẫn cứng `C:/Users/admin/...` trong `Kiểm:` (`plan:154`) vừa lộ đường dẫn máy cá nhân vừa trỏ nhầm về thư mục gốc cũ khi subagent `T3.2` chạy bên trong `.tdq-worktrees/`.
- **Cách sửa cụ thể:** Tại `T3.2`, đổi đường dẫn `Kiểm:` (`plan:154`) thành tương đối `plugins/tdq-workflow-agy`, thay thao tác `Edit` tay trên `plugins/tdq-workflow-agy/{mcp_config,hooks}.json` (`plan:160`) bằng chạy `py -3 -X utf8 tools/build_agy_plugin.py` (chỉ bọc `--with-caveman` trên bản cài đích `~/.gemini/config/plugins/tdq-workflow-agy` hoặc `tmp_path` kiểm thử), và sửa link ở `plan:26` thành `../../../plugins/tdq-workflow-agy/skills/tdq-conventions/references/subagent-tuning.md`.

### 5. `[testability]` `docs/tdq/plan/2026-11-22-1521-trien-khai-setup-fully-agy.md:211,213` — `confidence: 0.88` (BLOCKING)
- **Bằng chứng mã nguồn:** Quy tắc thi hành số 4 (`plan:39`) bắt buộc đặt `TDQ_KHONG_CHAM_MAY=1` và `TDQ_SETUP_STATE_DIR=<thư mục tạm>` cho kiểm thử cài đặt; trong pha `qc` ở `muc_qc = ultra` (`skills/tdq-build/references/qc.md:62,82,103`), các subagent `tdq-qc-tester` chạy dưới chế độ `[TDQ:SCOPED-WRITE]` và trần `120 giây` mỗi phép kiểm.
- **Vấn đề:**
  1. Lệnh DoD `Q6` (`plan:211`: `py -3 -X utf8 plugins/tdq-workflow-agy/scripts/tdq_setup.py --post-restart-verify`) không truyền thư mục trạng thái cô lập, nên khi `tdq-qc-tester` thực thi sẽ ghi trực tiếp vào `${PLUGIN_DATA}/setup-state.json` thật của máy (trái với `[TDQ:SCOPED-WRITE]` và dễ đụng độ khi chạy song song nhiều shard QC).
  2. Dòng DoD `Q8` (`plan:213`) chưa nêu tường minh bước kiểm chứng runtime MCP/subagent sống dưới trần `120 giây` đã khóa tại Spec `§6#Q8` (`spec:228`).
- **Cách sửa cụ thể:** Đổi lệnh kiểm của DoD `Q6` (`plan:211`) sang `py -3 -X utf8 -m pytest tests/test_tdq_simulate_verify.py -q` (hoặc hỗ trợ cờ `--state-dir` tạm trên `--post-restart-verify` để chạy cô lập sạch), và ghi rõ trong DoD `Q8` (`plan:213`) phép kiểm `agy plugin validate --strict --json` trên cả gói repo lẫn bản cài `~/.gemini/config/plugins/tdq-workflow-agy` kèm kiểm chứng runtime MCP/subagent dưới `120 giây`.
