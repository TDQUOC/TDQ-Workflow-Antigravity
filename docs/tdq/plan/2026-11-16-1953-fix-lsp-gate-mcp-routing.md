# PLAN — Fix triệt để lỗi lsp_gate chặn nhầm call_mcp_tool và chuẩn hoá phân luồng MCP/LSP

Ngày: 2026-11-16 · Spec: ../spec/2026-11-16-1953-fix-lsp-gate-mcp-routing.md (bản 1.0, ĐÃ DUYỆT) · Lane: full
Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md
Mode thực thi: subagent — đo `tdq_bench.py simulate` (hệ số 1.5x) cho thấy đội thắng (`16.3` phút vs `22.4` phút, chênh `6.1` phút với 3 đợt song song trên 11 task, 0 HOT FILE, 2 task `(mcp)` giữ ở leader) (ĐỀ XUẤT, user chốt lúc duyệt)
Trạng thái plan: HOÀN THÀNH

## Mục lục

- Quy tắc thi hành (áp cho mọi task)
- Thiết kế Trước vs Sau
- P1 — M1: Nguồn thuần chuẩn hoá MCP & nhận diện TDQ LSP
- P2 — M2: Chuẩn hoá payload & cờ tham số dùng chung
- P3 — M3: Định tuyến 3 nhánh `lsp_gate.py` & telemetry `search_observe.py`
- P4 — M4 & M5: Biên dịch gói Antigravity, E2E dual-protocol & Chrome DevTools
- Cụm song song
- Luật file nóng
- P5 — Log & test bắt buộc
- QC vòng 1 — fix
- Definition of Done

## Quy tắc thi hành (áp cho mọi task)

1. Thứ tự phase là thứ tự phụ thuộc — không đảo.
2. Mỗi task: đánh `[~]` khi bắt đầu → viết test trước (đỏ) → code → test xanh → đổi sang `[x]` NGAY vào file này. Trạng thái checkbox: `[ ]` chưa làm · `[~]` đang làm · `[x]` xong.
3. Mỗi bước: test vùng chạm (`pytest` file liên quan); trọn bộ + nhiều vòng agent `tdq-qc-tester` (`muc_qc = ultra`) ở pha QC.
4. Lệnh nào chạm state của workflow phải có `TDQ_PROJECT_DIR=<thư mục tạm>` ngay trên chính lệnh đó.
5. Không ghi đè hoặc đồng bộ sang bản cài plugin cục bộ `~/.gemini/config/plugins/tdq-workflow-agy` trong lúc thực thi/QC (chỉ xử lý sau khi commit/release theo chốt `3b`).
6. Không commit/push cho đến khi user yêu cầu.
7. Tuân thủ 6 mã cấm cơ học (`ANTI-1` Fake Red, `ANTI-2` Blind Assertion, `ANTI-3` Dirty State Git, `ANTI-4` Late Tick, `ANTI-5` Raw Dump, `ANTI-6` Broad Area).

## Thiết kế Trước vs Sau

| Khía cạnh | Hiện trạng (Trước) | Thiết kế mới (Sau) |
|---|---|---|
| Luồng thực thi `lsp_gate.py` | Chỉ tách `"blast_radius" in tool_name`; còn lại đều chạy `phan_xu()` của `start_lsp` khiến mọi `call_mcp_tool` có `Arguments` (`chrome-devtools`/`select_page`, `tavily_search`, `find_references`) bị chặn bởi `[TDQ:LSP]` | Gọi `ten_lenh_tdq_lsp(tool_name)`: không phải TDQ LSP → thoát `0` im lặng (`allow`); `"start_lsp"` (gồm `Arguments: {}`) → `phan_xu`; `"blast_radius"` → `phan_xu_blast_radius`; op LSP khác → thoát `0` |
| Chuẩn hoá MCP & nhận diện LSP | `"lsp" in srv` / `"_lsp_" in tname` lặp ở `_common.py`, `search_rules.py`, `search_observe.py`, `tools/patches/`, gom nhầm `other_lsp` | Một nguồn thuần duy nhất `chuan_hoa_cong_cu_mcp` / `TDQ_LSP_SERVER_RE` / `TDQ_LSP_TOOL_RE` tại `scripts/search_rules.py`, các hook import lại theo chiều `hooks/ -> scripts/` |
| Xử lý `Arguments: {}` vs payload thiếu khoá | `not tool_input` nuốt chung cả `start_lsp` gửi `Arguments: {}` rỗng tường minh | Cờ `_tool_args_present` phân biệt payload thiếu khoá / JSON hỏng (fail-open `allow`) với tham số rỗng tường minh `{}` trên `start_lsp` (fail-closed `[TDQ:LSP]`) |
| Thành phần chạm | `hooks/scripts/{_common,lsp_gate,search_observe}.py`, `scripts/search_rules.py`, `tools/patches/{agy_hooks,cli_fixes_a}.py` | Giữ đúng 6 file mã nguồn + gói biên dịch `plugins/tdq-workflow-agy/` + 5 file test hồi quy trong `tests/` (không chạm `hooks.json` matcher) |

*Đối chiếu sơ đồ kiến trúc:* Tham chiếu [truoc-sau-preview.html](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/spec/2026-11-16-1953-fix-lsp-gate-mcp-routing-preview.html) (manifest `e51c3800…`, verify `current`). Mọi task dưới ánh xạ 1–1 vào node `chuan_hoa_cong_cu_mcp`, `la_tool_tdq_lsp` và 3 nhánh ra trong sơ đồ đã duyệt.

## P1 — M1: Nguồn thuần chuẩn hoá MCP & nhận diện TDQ LSP

- [x] **T1.1** (e10m) Viết unit test đỏ trước rồi hợp nhất chuẩn hoá `call_mcp_tool` / eager AGY và bộ nhận diện chặt TDQ LSP vào `scripts/search_rules.py` — Test: `py -3 -X utf8 -m pytest tests/test_search_rules.py -q`
  - Dùng: `tdq-setup`
  - Để: đối chiếu quy ước tên MCP server `lsp` (`tdq-workflow-agy_lsp`) trong `uu-tien-tim-kiem.md` trước bước đỏ
  - Ra: hằng `TDQ_LSP_SERVER_RE`, `TDQ_LSP_TOOL_RE` và hàm thuần `chuan_hoa_cong_cu_mcp` tại `scripts/search_rules.py`
  - Kiểm: `py -3 -X utf8 -m pytest tests/test_search_rules.py -q`
  - Không dùng cho: tự chạy cài dependency môi trường hay sửa `mcp_config.json`
  - Chạm: `scripts/search_rules.py`, `tests/test_search_rules.py`
  - Cần: không
  - Mục tiêu: Đưa toàn bộ logic giải gói `call_mcp_tool`, eager AGY (`mcp_...`) và nhận diện tập đóng server TDQ LSP về một nguồn thuần stdlib duy nhất tại `scripts/search_rules.py`.
  - Vị trí neo: Ngay trước `LSP = re.compile(...)` ở khoảng dòng 894 (và thay logic trùng tại `_agy_unwrap_tool` dòng 1154–1186) trong `scripts/search_rules.py`; cuối lớp test LSP trong `tests/test_search_rules.py` (sau dòng 551).
  - Công cụ: Dùng `edit_file` cho cả hai file. CẤM dùng `write_file` trên file có sẵn.
  - Ràng buộc: Thuần stdlib (`import json` được phép, CẤM `print(...)` hoặc `open(...)` để giữ `test_log_module_thuan_khong_tu_in`), giữ tương thích `_agy_unwrap_tool(ten_tool, tool_input)` và `la_goi_khai_niem`. Complexity mỗi hàm `<= 8`, độ dài `<= 35` dòng.
  - Đặc tả kỹ thuật:
    `TDQ_LSP_SERVER_RE = re.compile(r"^(?:(?:plugin_)?tdq-workflow(?:-agy)?_)?lsp$", re.IGNORECASE)`
    `_AGY_TDQ_LSP_PREFIX_RE = re.compile(r"^mcp_((?:(?:plugin_)?tdq-workflow(?:-agy)?_)?lsp)_(.+)$", re.IGNORECASE)`
    `TDQ_LSP_TOOL_RE = re.compile(r"^(?:mcp__(?:(?:(?:plugin_)?tdq-workflow(?:-agy)?_)?lsp)__|lsp\.)(.+)$", re.IGNORECASE)`
    `_decode_json_dict(raw: Any) -> tuple[dict, bool]`
    `chuan_hoa_cong_cu_mcp(ten_tool: str, tool_input: Any) -> tuple[str, dict, bool]`
    `ten_lenh_tdq_lsp(ten_tool: str) -> str | None`
    `la_tool_tdq_lsp(ten_tool: str) -> bool`
  - Logic cốt lõi:
    1. Bước 1: Trong `_decode_json_dict(raw)`, nếu `raw` là `dict` trả `(dict(raw), True)`; nếu là `str`, lặp tối đa 3 lần `json.loads` chừng nào kết quả vẫn là `str`, khi ra `dict` trả `(dict(val), True)`; mọi trường hợp khác trả `({}, False)`.
    2. Bước 2: Trong `chuan_hoa_cong_cu_mcp(ten_tool, tool_input)`, giải mã `inp, has_inp = _decode_json_dict(tool_input)`. Nếu `ten == "call_mcp_tool"` và `has_inp`: đọc `srv`, `tname`; kiểm `"Arguments" in inp` rồi `"arguments" in inp` bằng `_decode_json_dict`; nếu `srv` khớp `TDQ_LSP_SERVER_RE` và `tname` khác rỗng trả `(f"mcp__lsp__{tname}", args_dict, has_args)`; nếu `srv` khác rỗng trả `(f"mcp__{srv}__{tname}", args_dict, has_args)`. Nếu `_AGY_TDQ_LSP_PREFIX_RE.match(ten)` khớp trả `(f"mcp__lsp__{m.group(2)}", inp, has_inp)`; mặc định giữ `(ten, inp, has_inp)`.
    3. Bước 3: Cập nhật `LSP = TDQ_LSP_TOOL_RE`, `_agy_unwrap_tool` uỷ quyền cho `chuan_hoa_cong_cu_mcp(ten_tool, tool_input)[:2]`, và `la_goi_khai_niem` dùng kết quả chuẩn hoá để giữ `mcp__other_lsp__*` và `mcp_other_lsp_*` trả `None`.
  - Ca góc hiểm & TDD:
    - Ca hiểm: `Arguments` lồng 2 tầng chuỗi JSON `"{\"language_id\": \"python\"}"`, `Arguments: "{}"`, `Arguments: "{bad"`, thiếu hẳn `Arguments`, `ServerName="other_lsp"`, `mcp_tdq-workflow-agy_lsp_start_lsp`, `mcp_other_lsp_find_symbol`.
    - Tiêu chí: `assert sr.la_goi_khai_niem("call_mcp_tool", {"ServerName": "other_lsp", "ToolName": "find_symbol", "Arguments": {}}) is None` và `assert sr.ten_lenh_tdq_lsp("mcp__other_lsp__find_symbol") is None` và `assert sr.chuan_hoa_cong_cu_mcp("call_mcp_tool", {"ServerName": "tdq-workflow-agy_lsp", "ToolName": "start_lsp", "Arguments": "{}"}) == ("mcp__lsp__start_lsp", {}, True)`.

- [x] **T1.2** (e5m) Đồng bộ `_patch_search_rules` trong `tools/patches/cli_fixes_a.py` dùng đúng tập đóng `TDQ_LSP_SERVER_RE` và `_decode_json_dict` khớp với `T1.1` — Test: `py -3 -X utf8 -c "import pathlib; t = pathlib.Path('tools/patches/cli_fixes_a.py').read_text(encoding='utf-8'); assert 'TDQ_LSP_SERVER_RE' in t and '_AGY_TDQ_LSP_PREFIX_RE' in t"`
  - Chạm: `tools/patches/cli_fixes_a.py`
  - Cần: T1.1
  - Mục tiêu: Bảo đảm nhánh compiler fallback `_patch_search_rules` sinh ra hàm nhận diện TDQ LSP giống hệt `search_rules.py`.
  - Vị trí neo: Sau `def _patch_search_rules(scripts_dir: Path)` dòng 103, thay khối `addon = ''' ... '''` ở dòng 112–145 trong `tools/patches/cli_fixes_a.py`.
  - Công cụ: Dùng `edit_file`. CẤM dùng `write_file`.
  - Ràng buộc: Thuần stdlib (`import json` nếu chưa có), giữ nguyên sentinel `"_ORIG_LA_GOI_KHAI_NIEM"` để idempotent, complexity `<= 8`.
  - Đặc tả kỹ thuật:
    `_patch_search_rules(scripts_dir: Path) -> None` cập nhật `addon` định nghĩa `TDQ_LSP_SERVER_RE`, `_AGY_TDQ_LSP_PREFIX_RE`, `_decode_json_dict`, `_agy_unwrap_tool`, `la_goi_khai_niem`.
  - Logic cốt lõi:
    1. Bước 1: Kiểm tra và chèn `import json\n` nếu thiếu trong `search_rules.py` nguồn cũ.
    2. Bước 2: Cập nhật `addon` dùng `TDQ_LSP_SERVER_RE` thay cho `"lsp" in srv` và `_AGY_TDQ_LSP_PREFIX_RE` thay cho `"_lsp_" in ten`, kèm `_decode_json_dict` an toàn.
    3. Bước 3: Kiểm chứng bằng python one-liner chạy `_patch_search_rules` trên bản sao tổng hợp tối thiểu trong `tempfile.TemporaryDirectory()` và assert `la_goi_khai_niem("call_mcp_tool", {"ServerName": "other_lsp", "ToolName": "find_symbol", "Arguments": {}}) is None`.
  - Ca góc hiểm & TDD:
    - Ca hiểm: `_patch_search_rules` chạy 2 lần liên tiếp (idempotent), `Arguments` kiểu chuỗi JSON.
    - Tiêu chí: `assert mod.la_goi_khai_niem("mcp_other_lsp_find_symbol", {}) is None` và `assert mod.la_goi_khai_niem("call_mcp_tool", {"ServerName": "tdq-workflow-agy_lsp", "ToolName": "find_symbol", "Arguments": "{}"}) == "lsp:find_symbol"`.

**Xong P1 khi**: `T1.1`, `T1.2` `[x]` và `py -3 -X utf8 -m pytest tests/test_search_rules.py -q` PASS 100%.

## P2 — M2: Chuẩn hoá payload & cờ tham số dùng chung

- [x] **T2.1** (e8m) Viết test đỏ tại `tests/test_hook_windows.py` rồi cập nhật `hooks/scripts/_common.py` dùng `chuan_hoa_cong_cu_mcp` và gắn cờ `_tool_args_present` — Test: `py -3 -X utf8 -m pytest tests/test_hook_windows.py -q`
  - Chạm: `hooks/scripts/_common.py`, `tests/test_hook_windows.py`
  - Cần: T1.1
  - Mục tiêu: Loại bỏ bản sao logic `_unwrap_call_mcp` trong `_common.py`, kế thừa 1 nguồn từ `search_rules.py`, đồng thời đánh dấu `_tool_args_present` chính xác trên cả Antigravity lẫn Claude Code payload.
  - Vị trí neo: Sau dòng `from tdq_state import (...)` (dòng 32–33), tại `def _unwrap_call_mcp` (dòng 164–178) và bên trong `def normalize_payload(raw)` (dòng 289–353) của `hooks/scripts/_common.py`; thêm lớp/hàm test cuối `tests/test_hook_windows.py`.
  - Công cụ: Dùng `edit_file` cho cả hai file. CẤM dùng `write_file`.
  - Ràng buộc: Giữ nguyên thứ tự `_SCRIPTS_DIR` trong `sys.path` trước `from search_rules import chuan_hoa_cong_cu_mcp`; dùng `from-import` để Graphify dựng cạnh gọi; không làm đổi schema output cho `read_gate`, `edit_gate`, `bash_gate`, `stop_gate`.
  - Đặc tả kỹ thuật:
    `from search_rules import chuan_hoa_cong_cu_mcp  # noqa: E402`
    `_unwrap_call_mcp(tool_name: str, tool_input: Any) -> tuple[str, dict]` (uỷ quyền `chuan_hoa_cong_cu_mcp(tool_name, tool_input)[:2]`)
    `normalize_payload(raw: Any) -> dict` đặt `payload["_tool_args_present"]: bool`.
  - Logic cốt lõi:
    1. Bước 1: Trước nhánh `if agy`, kiểm tra có key tham số gốc nào xuất hiện trong `raw` (`tool_input`, `toolInput`, `toolCall.args`, `arguments`, `input`).
    2. Bước 2: Trong nhánh `agy`: tìm container đầu tiên trong `("tool_input", "toolInput")` hoặc `toolCall.args` hoặc `("arguments", "input")`; ghi nhận `outer_present` khi giá trị decode được thành `dict`; gọi `new_tname, tinput, args_present = chuan_hoa_cong_cu_mcp(tname, raw_container)`. Nếu `tname == "call_mcp_tool"`, đặt `has_args = args_present`; ngược lại đặt `has_args = outer_present`. Lưu `payload["original_tool_name"]` nếu `tname != "call_mcp_tool"` và `new_tname != tname`. Đặt `payload["_tool_args_present"] = has_args` và nếu `has_args` hoặc `tinput` hoặc có container key gốc thì gán `payload["tool_input"] = tinput`.
    3. Bước 3: Trong nhánh `not agy`: đặt `payload["_tool_args_present"] = ("tool_input" in payload and isinstance(payload["tool_input"], dict))` trước vòng check `expected` (nếu `tool_input` sai kiểu bị pop ở dòng 349–351 thì ép `payload["_tool_args_present"] = False`).
  - Ca góc hiểm & TDD:
    - Ca hiểm: `{"tool_name": "mcp__lsp__start_lsp", "cwd": "."}` (`_tool_args_present is False`); `{"tool_name": "call_mcp_tool", "tool_input": {"ServerName": "tdq-workflow-agy_lsp", "ToolName": "start_lsp", "Arguments": {}}, "cwd": "."}` (`_tool_args_present is True`, `tool_name == "mcp__lsp__start_lsp"`); `Arguments: "{bad"` (`_tool_args_present is False`); `ServerName: "chrome-devtools"` (`tool_name == "mcp__chrome-devtools__select_page"`).
    - Tiêu chí: `assert out["tool_name"] == "mcp__chrome-devtools__select_page"` và `assert out_empty["_tool_args_present"] is True` và `assert out_missing["_tool_args_present"] is False`.

- [x] **T2.2** (e5m) Đồng bộ `COMMON_PY` trong `tools/patches/agy_hooks.py` import `chuan_hoa_cong_cu_mcp` và đặt `_tool_args_present` giống hệt `T2.1` — Test: `py -3 -X utf8 -c "import pathlib; t = pathlib.Path('tools/patches/agy_hooks.py').read_text(encoding='utf-8'); assert 'chuan_hoa_cong_cu_mcp' in t and '_tool_args_present' in t"`
  - Chạm: `tools/patches/agy_hooks.py`
  - Cần: T1.1
  - Mục tiêu: Đảm bảo fallback `COMMON_PY` trong `tools/patches/agy_hooks.py` khi sinh `_common.py` cho cây cũ vẫn thống nhất hành vi chuẩn hoá MCP và `_tool_args_present`.
  - Vị trí neo: Sau `from tdq_state import (...)` (dòng 24–27), tại `def _unwrap_call_mcp` (dòng 91–105), và trong `def normalize_payload(raw)` (dòng 127–178) bên trong chuỗi `COMMON_PY` của `tools/patches/agy_hooks.py`.
  - Công cụ: Dùng `edit_file`. CẤM dùng `write_file`.
  - Ràng buộc: Giữ `SCRIPTS_DIR` được chèn vào `sys.path` trước `from search_rules import chuan_hoa_cong_cu_mcp`; không thay đổi danh sách 24 `CODES`.
  - Đặc tả kỹ thuật:
    `COMMON_PY`: `from search_rules import chuan_hoa_cong_cu_mcp` + `_unwrap_call_mcp` mỏng + `normalize_payload` đặt `out["_tool_args_present"]`.
  - Logic cốt lõi:
    1. Bước 1: Thêm `from search_rules import chuan_hoa_cong_cu_mcp` sau khối `from tdq_state import (...)` của `COMMON_PY`.
    2. Bước 2: Rút gọn `_unwrap_call_mcp` gọi `chuan_hoa_cong_cu_mcp(tool_name, tool_input)[:2]`.
    3. Bước 3: Cập nhật `normalize_payload(raw)` trong `COMMON_PY` ghi nhận container & `_tool_args_present` đồng bộ với `_common.py`.
  - Ca góc hiểm & TDD:
    - Ca hiểm: `_common.py` sinh từ `COMMON_PY` khi thư mục gốc chưa có `AGY_CODES = (`.
    - Tiêu chí: `assert mod.normalize_payload({"tool_name": "call_mcp_tool", "tool_input": {"ServerName": "chrome-devtools", "ToolName": "select_page", "Arguments": {"pageId": 1}}})["tool_name"] == "mcp__chrome-devtools__select_page"` và `assert mod.normalize_payload({"tool_name": "mcp__lsp__start_lsp", "cwd": "."})["_tool_args_present"] is False`.

**Xong P2 khi**: `T2.1`, `T2.2` `[x]` và `py -3 -X utf8 -m pytest tests/test_hook_windows.py -q` PASS 100%.

## P3 — M3: Định tuyến 3 nhánh `lsp_gate.py` & telemetry `search_observe.py`

- [x] **T3.1** (e10m) Viết unit test đỏ tại `tests/test_lsp_gate.py` rồi cập nhật `hooks/scripts/lsp_gate.py` định tuyến chặt 3 nhánh TDQ LSP và giữ fail-open / `< 200 ms` — Test: `py -3 -X utf8 -m pytest tests/test_lsp_gate.py -q`
  - Chạm: `hooks/scripts/lsp_gate.py`, `tests/test_lsp_gate.py`
  - Cần: T2.1, T3.2
  - Mục tiêu: Ngăn `lsp_gate.py` chạy `phan_xu()` trên mọi `call_mcp_tool` hoặc tool LSP không phải `start_lsp`/`blast_radius`, đồng thời bắt chặt `start_lsp` gửi `Arguments: {}` rỗng tường minh.
  - Vị trí neo: Dòng 30 `from search_rules import trang_thai_lsp` và hàm `def main()` (dòng 129–163) của `hooks/scripts/lsp_gate.py`; thêm class/hàm test cuối `tests/test_lsp_gate.py` (sau dòng 137).
  - Công cụ: Dùng `edit_file` cho cả hai file. CẤM dùng `write_file`.
  - Ràng buộc: Độ phức tạp cyclomatic `<= 8`, `main() <= 35` dòng; chuỗi log viết tiếng Anh có ISO timestamp mặc định bật (`TDQ_LOG=0` tắt); không gọi `lsp_module` để giữ `< 200 ms`.
  - Đặc tả kỹ thuật:
    Import thêm `ten_lenh_tdq_lsp` từ `search_rules`.
    Trong `main() -> None`: đọc `payload`, tách `op = ten_lenh_tdq_lsp(tool_name)` và `has_args = bool(payload.get("_tool_args_present") or (isinstance(tool_input, dict) and tool_input))`.
  - Logic cốt lõi:
    1. Bước 1: Sau khi đọc `payload`, kiểm `op = ten_lenh_tdq_lsp(tool_name)`. Nếu `op is None`: `_log(f"non-tdq-lsp tool={tool_name!r} — allow")` và `sys.exit(0)`.
    2. Bước 2: Nếu `not has_args`: `_log(f"tdq-lsp op={op} without tool_input — allow (fail-open)")` và `sys.exit(0)`.
    3. Bước 3: Rẽ nhánh `op`: `op == "blast_radius"` gọi `phan_xu_blast_radius(cwd, tool_input, rows)`; `op == "start_lsp"` gọi `phan_xu(cwd, tool_input)`; mọi `op` còn lại (`find_references`, `find_symbol`, `go_to_definition`, …) ghi `_log(f"tdq-lsp op={op} — allow")` và `sys.exit(0)`. Nếu `dong` khác rỗng gọi `_common.block(cwd, payload, MA, dong, day_du=True)`.
  - Ca góc hiểm & TDD:
    - Ca hiểm: `call_mcp_tool` tới `chrome-devtools`/`select_page`, `chrome-devtools`/`list_pages`, `tavily-primary`/`tavily_search`, `tdq-workflow-agy_lsp`/`find_references`, `tdq-workflow-agy_lsp`/`find_symbol` (eager + lazy), `other_lsp`/`start_lsp` (tất cả đều ALLOW); `tdq-workflow-agy_lsp`/`start_lsp` với `Arguments: {}` và `Arguments: "{}"` (DENY `[TDQ:LSP]`); payload thiếu `tool_input` hoặc JSON hỏng của `start_lsp` (ALLOW); `TDQ_LOG=1` in stderr log, `TDQ_LOG=0` im lặng; thời gian chạy `< 0.2s`.
    - Tiêu chí: `assert out_select["decision"] == "allow"` và `assert out_empty_start["decision"] == "deny" and "[TDQ:LSP]" in out_empty_start["reason"]` và `assert out_other_lsp["decision"] == "allow"`.

- [x] **T3.2** (e6m) Viết unit test đỏ tại `tests/test_search_observe.py` khoá telemetry `lsp_ket_qua` rồi cập nhật `hooks/scripts/search_observe.py` dùng `la_tool_tdq_lsp` — Test: `py -3 -X utf8 -m pytest tests/test_search_observe.py -q`
  - Chạm: `hooks/scripts/search_observe.py`, `tests/test_search_observe.py`
  - Cần: T1.1, T2.1
  - Mục tiêu: Chặn nhiễu dữ liệu circuit-breaker `lsp_ket_qua` từ các server MCP không thuộc TDQ LSP nhưng tên tình cờ chứa chuỗi `"lsp"` (như `other_lsp`).
  - Vị trí neo: Dòng 50 `from search_rules import TOKEN, la_goi_khai_niem, phan_loai_ket_qua_lsp, trang_thai` và dòng 181 `if "lsp" in tool_name.lower():` trong `hooks/scripts/search_observe.py`; cuối lớp `GhiKhaiNiem` hoặc lớp test `LspKetQua` trong `tests/test_search_observe.py`.
  - Công cụ: Dùng `edit_file` cho cả hai file. CẤM dùng `write_file`.
  - Ràng buộc: Dùng `from-import` chuẩn `from search_rules import (..., la_tool_tdq_lsp)`; giữ nguyên schema JSONL của `.tdq-search.jsonl`.
  - Đặc tả kỹ thuật:
    `from search_rules import (TOKEN, la_goi_khai_niem, la_tool_tdq_lsp, phan_loai_ket_qua_lsp, trang_thai)`
    Thay điều kiện dòng 181 thành `if la_tool_tdq_lsp(tool_name):`.
  - Logic cốt lõi:
    1. Bước 1: Import `la_tool_tdq_lsp` từ `search_rules` tại dòng 50 của `hooks/scripts/search_observe.py`.
    2. Bước 2: Ở nhánh `PostToolUse` / `PostToolUseFailure` dòng 181, kiểm `la_tool_tdq_lsp(tool_name)` thay cho `"lsp" in tool_name.lower()`.
    3. Bước 3: Bổ sung ca test gọi `PostToolUseFailure` trên `mcp__other_lsp__find_symbol` (không sinh dòng `lsp_ket_qua`) và `call_mcp_tool` tới `tdq-workflow-agy_lsp`/`find_references` (ghi đúng `lsp_ket_qua`).
  - Ca góc hiểm & TDD:
    - Ca hiểm: `PostToolUseFailure` của `call_mcp_tool(ServerName="other_lsp", ToolName="find_references")` không được kích hoạt circuit breaker cho TDQ LSP.
    - Tiêu chí: `assert not any(r.get("loai") == "lsp_ket_qua" for r in rows_other)` và `assert any(r.get("loai") == "lsp_ket_qua" for r in rows_tdq)`.

**Xong P3 khi**: `T3.1`, `T3.2` `[x]` và `py -3 -X utf8 -m pytest tests/test_lsp_gate.py tests/test_search_observe.py -q` PASS 100%.

## P4 — M4 & M5: Biên dịch gói Antigravity, E2E dual-protocol & Chrome DevTools

- [x] **T4.1** (e5m) Biên dịch lại gói `plugins/tdq-workflow-agy/` bằng `tools/build_agy_plugin.py` và chạy `agy plugin validate --strict --json`, giữ nguyên bản cài cục bộ (`3b`) — Test: `py -3 -X utf8 tools/build_agy_plugin.py && agy.EXE plugin validate --strict --json plugins/tdq-workflow-agy`
  - Chạm: `plugins/tdq-workflow-agy/manifest.json`, `hooks/scripts/lsp_gate.py`
  - Cần: T1.2, T2.2, T3.1, T3.2
  - Mục tiêu: Đóng gói đầy đủ bản sửa M1–M3 vào plugin Antigravity phát hành trong repo mà không ghi đè sang `~/.gemini/config/plugins/`.
  - Đặc tả kỹ thuật: Gọi `tools/build_agy_plugin.py` (hàm `build()`) đồng bộ `scripts/`, `hooks/scripts/`, `tools/patches/` sang `plugins/tdq-workflow-agy/` và kiểm chứng qua `agy.EXE plugin validate --strict --json`.
  - Logic cốt lõi:
    1. Bước 1: Chạy `py -3 -X utf8 tools/build_agy_plugin.py` để biên dịch đầy đủ cây plugin Antigravity.
    2. Bước 2: Chạy `agy.EXE plugin validate --strict --json plugins/tdq-workflow-agy` xác nhận `0` lỗi và `0` cảnh báo.
  - Kiểm thực hiện: Chạy trình biên dịch `tools/build_agy_plugin.py`, đối chiếu hash/cú pháp AST và chạy `agy.EXE plugin validate --strict --json plugins/tdq-workflow-agy` đạt `0` lỗi và `0` cảnh báo.

- [x] **T4.2** (e8m) Thu mẫu payload `chrome-devtools` thực tế và bổ sung bộ kiểm chứng E2E `cmd /c` vào `tests/test_hooks_dual_protocol.py` + `tests/test_cli_fixes_new01_28.py` trên gói đã biên dịch — Test: `py -3 -X utf8 -m pytest tests/test_hooks_dual_protocol.py tests/test_cli_fixes_new01_28.py -q`
  - Dùng: `tdq-browser-research` (mcp)
  - Để: lấy mẫu payload `call_mcp_tool` thật của `chrome-devtools` (`select_page`, `list_pages`, `click`, `navigate_page`) làm ca test E2E tại `tests/test_hooks_dual_protocol.py`
  - Ra: các assertion E2E trong `tests/test_hooks_dual_protocol.py` và `tests/test_cli_fixes_new01_28.py` kiểm chứng bản `plugins/tdq-workflow-agy/` đã biên dịch
  - Kiểm: `py -3 -X utf8 -m pytest tests/test_hooks_dual_protocol.py tests/test_cli_fixes_new01_28.py -q`
  - Không dùng cho: tự động điều khiển hoặc gửi dữ liệu ra web bên ngoài
  - Chạm: `tests/test_hooks_dual_protocol.py`, `tests/test_cli_fixes_new01_28.py`
  - Cần: T4.1
  - Mục tiêu: Xác thực end-to-end qua tiến trình con `cmd /c py -3` đúng giao thức Antigravity trên `plugins/tdq-workflow-agy/` sau biên dịch.
  - Vị trí neo: Cuối hàm `test_ec01_to_ec14_live_cmd_hooks` (sau dòng 264) trong `tests/test_hooks_dual_protocol.py` và trong hàm `test_new02_03_04_lsp_module_and_search_rules` (sau dòng 97) của `tests/test_cli_fixes_new01_28.py`.
  - Công cụ: Dùng `edit_file`. CẤM dùng `write_file`.
  - Ràng buộc: Phải test qua `cmd /c py -3` trỏ thẳng `plugins/tdq-workflow-agy/hooks/scripts/lsp_gate.py --event PreToolUse`; giữ nguyên các test EC-01..EC-14 hiện hữu.
  - Đặc tả kỹ thuật:
    Bổ sung `test_ec16_lsp_gate_mcp_routing_and_empty_args(tmp_path)` trong `tests/test_hooks_dual_protocol.py` và assert `other_lsp` + `Arguments` chuỗi JSON trong `tests/test_cli_fixes_new01_28.py`.
  - Logic cốt lõi:
    1. Bước 1: Dùng dữ liệu schema/payload thực tế của `chrome-devtools` (`select_page`, `list_pages`, `click`) dựng cặp ca test `call_mcp_tool` + `tavily-primary`/`tavily_search` + `tdq-workflow-agy_lsp`/`find_references` + `other_lsp`/`start_lsp` (đều trả `{"decision": "allow"}`).
    2. Bước 2: Gọi `lsp_gate.py --event PreToolUse` với `start_lsp` có `Arguments: {}` và `Arguments: "{}"` (đều trả `{"decision": "deny"}` chứa `[TDQ:LSP]`) và `Arguments: "{broken"` (trả `{"decision": "allow"}`).
    3. Bước 3: Kiểm chứng trong `tests/test_cli_fixes_new01_28.py` rằng `plugins/tdq-workflow-agy/scripts/search_rules.py` giữ nguyên `other_lsp` trả `None` và giải mã được `Arguments` chuỗi JSON kép.
  - Ca góc hiểm & TDD:
    - Ca hiểm: `Arguments` double-encoded `"\"{\\\"root_dir\\\": \\\".\\\"}\""` thiếu `language_id` -> phải DENY; `Arguments` JSON lỗi -> phải ALLOW.
    - Tiêu chí: `assert json.loads(res.stdout)["decision"] == "allow"` cho `select_page` / `find_references` và `assert "[TDQ:LSP]" in json.loads(deny_res.stdout)["reason"]`.

- [x] **T4.3** (e5m) Pre-flight probe `chrome-devtools` MCP và xác thực tương thích luồng tương tác Chrome DevTools trên `lsp_gate.py` đã biên dịch, ghi bằng chứng ra `docs/tdq/artifacts/2026-11-16-1953-fix-lsp-gate-mcp-routing/chrome-devtools-smoke.md` — Test: kiểm file artifact ghi đủ kết quả pre-flight probe và `{"decision": "allow"}` cho các lệnh Chrome DevTools
  - Dùng: `tdq-browser-test` (mcp)
  - Để: thực hiện pre-flight probe `chrome-devtools` (`list_pages`) và đối chiếu tương thích luồng `select_page` / `click` / `navigate_page` với `plugins/tdq-workflow-agy/hooks/scripts/lsp_gate.py`
  - Ra: `docs/tdq/artifacts/2026-11-16-1953-fix-lsp-gate-mcp-routing/chrome-devtools-smoke.md`
  - Kiểm: `py -3 -X utf8 -c "import pathlib; t=pathlib.Path('docs/tdq/artifacts/2026-11-16-1953-fix-lsp-gate-mcp-routing/chrome-devtools-smoke.md').read_text(encoding='utf-8'); assert 'allow' in t and 'select_page' in t"`
  - Không dùng cho: tự động ghi đè plugin cục bộ `~/.gemini/config/plugins/` hay chạy full test suite
  - Chạm: `docs/tdq/artifacts/2026-11-16-1953-fix-lsp-gate-mcp-routing/chrome-devtools-smoke.md`
  - Cần: T4.2
  - Ghi chú thực thi: Gọi `list_pages` (`Arguments: {}`) để thăm dò runtime `chrome-devtools` (lưu ý bản cài cục bộ giữ nguyên theo `3b` nên các lệnh `chrome-devtools` có `Arguments` thực thi kiểm chứng thẳng qua `plugins/tdq-workflow-agy/hooks/scripts/lsp_gate.py --event PreToolUse`), ghi rõ bằng chứng trong artifact.

**Xong P4 khi**: `T4.1`–`T4.3` `[x]`, `agy plugin validate --strict --json` 0 lỗi/cảnh báo, và E2E `test_hooks_dual_protocol.py` + `test_cli_fixes_new01_28.py` PASS 100%.

## Cụm song song

- Đợt 1 (`T1.1` → `T1.2`): chuẩn hoá nguồn thuần M1 (`scripts/search_rules.py` + `tests/test_search_rules.py`, rồi `tools/patches/cli_fixes_a.py`).
- Đợt 2 (`T2.1` → `T2.2` + `T3.2`): `hooks/scripts/_common.py` xong rồi đồng bộ fallback `tools/patches/agy_hooks.py` song song được với `T3.2` (`search_observe.py` + `tests/test_search_observe.py`) vì khác đường dẫn `Chạm:`.
- Đợt 3 (`T3.1`): `lsp_gate.py` + `test_lsp_gate.py` (chạy sau `T2.1` và `T3.2` do `lsp_gate.py` import `doc_so`, `khoa_hien_tai` từ `search_observe.py`).
- Đợt 4 (`T4.1` → `T4.2` `(mcp)` → `T4.3` `(mcp)` → `T5.1`, `T5.2`): biên dịch `plugins/tdq-workflow-agy/`, E2E dual-protocol và xác minh MCP + full check trước QC `ultra` nhiều vòng.

## Luật file nóng

Mọi task `T1.1`–`T4.3` đều được chia `Chạm:` rời nhau hoàn toàn (`0` file xuất hiện ở hai dòng `Chạm:` khác nhau). Nếu trong lúc thực thi hoặc QC phát sinh chỉnh sửa chéo file giữa hai task, áp dụng nguyên tắc **một chủ ghi duy nhất** tại task sở hữu file đó hoặc nâng phần chung lên phase trước.

## P5 — Log & test bắt buộc

- [x] **T5.1** (e3m) Xác minh log service bật mặc định (ISO timestamp, tắt qua `TDQ_LOG=0`) của `lsp_gate.py` & `search_observe.py` và bất biến thuần I/O (`search_rules.py` không tự gọi `print`/`open`) — Test: `py -3 -X utf8 -m pytest tests/test_lsp_gate.py tests/test_search_rules.py -k "log or LogQuaNguoiGoi" -q`
  - Cần: T3.1, T3.2
- [x] **T5.2** (e8m) Chạy trọn bộ kiểm thử tự động (`tdq_test.py vung-cham`), linter (`ruff check --select F,B`, `doc_lint.py`, `i18n_check.py`, `token_budget.py --kiem`) và kiểm tra bản cài local `~/.gemini/config/plugins/` còn nguyên vẹn (`3b`) trước khi bước vào pha QC `ultra` với `tdq-qc-tester` — Test: `py -3 -X utf8 "plugins/tdq-workflow-agy/scripts/tdq_test.py" vung-cham`
  - Cần: T4.3, T5.1
  - Tiến độ: Chuyển `tool_args_present` vào `_common._RUNTIME_STATE` + `has_tool_args()` để giữ nguyên hợp đồng `test_common`. Đã chạy `219 passed, 226 subtests passed`.

## QC vòng 1 — fix

- [x] **QC1.1** (e3m) Cô lập `_common._RUNTIME_STATE` trong `tests/test_hook_windows.py` (`TestCommonMcpNormalization`) để không làm nhiễu các test cùng tiến trình — Test: `py -3 -X utf8 -m pytest tests/test_hook_windows.py tests/test_kenh_luat_dedupe.py tests/test_prompt_context.py tests/test_reminder_contract.py -q`
  - Chạm: `tests/test_hook_windows.py`
  - Cần: T5.2
  - Mục tiêu: Đưa `TestCommonMcpNormalization` về trạng thái sạch sau mỗi test case vì `normalize_payload` đặt `_RUNTIME_STATE["is_agy"] = True` làm ảnh hưởng tới các test chạy tiếp trong cùng phiên `pytest`.
  - Vị trí neo: Lớp `TestCommonMcpNormalization` (dòng 187–274) trong `tests/test_hook_windows.py`.
  - Công cụ: Dùng `edit_file`. CẤM dùng `write_file`.
  - Ràng buộc: Lưu và khôi phục nông `_common._RUNTIME_STATE` (sao chép riêng list `context_lines`), giữ nguyên tất cả assertion sẵn có.
  - Đặc tả kỹ thuật: Thêm `setUp(self)` lưu `dict(self._common._RUNTIME_STATE)` kèm `list(context_lines)` và `tearDown(self)` gọi `clear()` rồi `update(saved)`.
  - Logic cốt lõi:
    1. Bước 1: Chạy `pytest tests/test_hook_windows.py tests/test_kenh_luat_dedupe.py tests/test_reminder_contract.py -q` ghi nhận lỗi đỏ ở chế độ đơn tiến trình.
    2. Bước 2: Thêm `setUp` / `tearDown` trong `TestCommonMcpNormalization` và test xác nhận `_RUNTIME_STATE["is_agy"]` được khôi phục sau `tearDown`.
    3. Bước 3: Chạy lại cả 4 file test cùng lúc xác nhận 100% PASS.
  - Ca góc hiểm & TDD:
    - Ca hiểm: `_RUNTIME_STATE["context_lines"]` là list mutable; phải copy list để tránh chia sẻ tham chiếu.
    - Tiêu chí: `assert self._common._RUNTIME_STATE["is_agy"] is saved_is_agy` sau `tearDown()` và 0 lỗi ở `test_kenh_luat_dedupe.py`, `test_prompt_context.py`, `test_reminder_contract.py`.

- [x] **QC1.2** (e4m) Đồng bộ `COMMON_PY` trong `tools/patches/agy_hooks.py` dùng `_extract_raw_tool_container` và chuẩn hoá đơn nguồn khớp `hooks/scripts/_common.py` — Test: `py -3 -X utf8 -m pytest tests/test_agy_hooks.py -q`
  - Chạm: `tools/patches/agy_hooks.py`
  - Cần: QC1.1
  - Mục tiêu: Xoá vòng lặp giải mã JSON 3 tầng trùng lặp trong `COMMON_PY.normalize_payload` và kiểm tra `is not None` cho khóa container giống hệt `hooks/scripts/_common.py`.
  - Vị trí neo: Khối `normalize_payload` (dòng 103–175) bên trong chuỗi `COMMON_PY` của `tools/patches/agy_hooks.py`.
  - Công cụ: Dùng `edit_file`. CẤM dùng `write_file`.
  - Ràng buộc: Không thay đổi bộ 24 mã `CODES` hoặc API `has_tool_args()`, giữ tương thích test `tests/test_agy_hooks.py`.
  - Đặc tả kỹ thuật: Bổ sung `_extract_raw_tool_container(payload, tool_call)` kiểm tra `if key in payload and payload[key] is not None:` và gọi `chuan_hoa_cong_cu_mcp(orig_tname, raw_container)`.
  - Logic cốt lõi:
    1. Bước 1: Thêm `_extract_raw_tool_container(payload, tool_call)` trước `normalize_payload` trong `COMMON_PY`.
    2. Bước 2: Thay vòng lặp `json.loads` thủ công trong `normalize_payload` bằng `chuan_hoa_cong_cu_mcp(tname, raw_container)` và `has_args = bool(container_found and args_present)`.
    3. Bước 3: Kiểm chứng lại qua `tests/test_agy_hooks.py`.
  - Ca góc hiểm & TDD:
    - Ca hiểm: `{"tool_name": "call_mcp_tool", "tool_input": None, "toolCall": {"args": {"ServerName": "chrome-devtools", "ToolName": "select_page", "Arguments": "{}"}}}` không được nuốt `tool_input=None` thay vì fallback sang `toolCall.args`.
    - Tiêu chí: `assert out["tool_name"] == "mcp__chrome-devtools__select_page"` và `assert _has_args is True`.

- [x] **QC1.3** (e5m) Tách helper `_phan_xu_lenh` để rút gọn `lsp_gate.py:main()` `<= 25` dòng và chuẩn hoá `scripts/search_replay.py` dùng `chuan_hoa_cong_cu_mcp` + `la_tool_tdq_lsp` — Test: `py -3 -X utf8 -m pytest tests/test_lsp_gate.py tests/test_search_replay.py tests/test_search_observe.py tests/test_search_rules.py -q`
  - Chạm: `hooks/scripts/lsp_gate.py`, `scripts/search_replay.py`, `tests/test_search_replay.py`
  - Cần: QC1.2
  - Mục tiêu: Đưa `lsp_gate.py:main()` về đúng ràng buộc `<= 35` dòng và loại bỏ chuỗi khớp lỏng `"lsp" in name.lower()` cuối cùng ở `scripts/search_replay.py`.
  - Vị trí neo: Hàm `main()` (dòng 129–169) trong `hooks/scripts/lsp_gate.py`; hàm `phan_tich_lsp_telemetry` (dòng 180–190) trong `scripts/search_replay.py`; lớp `TestLspTelemetryReplay` (dòng 172–198) trong `tests/test_search_replay.py`.
  - Công cụ: Dùng `edit_file`. CẤM dùng `write_file`.
  - Ràng buộc: `main() <= 25` dòng đo bằng AST; `search_replay.py` vẫn giữ luật không import `hooks/` và vẫn ghi đúng `cong_cu` đã chuẩn hoá.
  - Đặc tả kỹ thuật: Thêm `_phan_xu_lenh(cwd: str, phien: str, op: str, tool_input: dict) -> list[str]` trong `lsp_gate.py`; trong `search_replay.py`, gọi `ten_cong_cu, _inp, _ok = search_rules.chuan_hoa_cong_cu_mcp(c.get("name"), c.get("input"))` và kiểm tra `if search_rules.la_tool_tdq_lsp(ten_cong_cu):`.
  - Logic cốt lõi:
    1. Bước 1: Viết test mới tại `tests/test_search_replay.py` xác nhận `other_lsp` không bị đếm vào telemetry còn `call_mcp_tool(tdq-workflow-agy_lsp, find_references)` được đếm (`Red`).
    2. Bước 2: Tách `_phan_xu_lenh` khỏi `lsp_gate.py:main()` và cập nhật `scripts/search_replay.py` dùng `chuan_hoa_cong_cu_mcp` + `la_tool_tdq_lsp` (`Green`).
    3. Bước 3: Kiểm tra số dòng AST của `main()` (`<= 25`) và chạy toàn bộ bộ test LSP/replay/observe/rules.
  - Ca góc hiểm & TDD:
    - Ca hiểm: Transcript chứa song song `mcp__other_lsp__find_symbol` và `call_mcp_tool` trỏ tới `tdq-workflow-agy_lsp`/`find_references` (với `Arguments` JSON string).
    - Tiêu chí: `assert kq["tong_so"] == 1` và `ast` đếm `end_lineno - lineno + 1 <= 25` cho `lsp_gate.main`.

- [x] **QC1.4** (e8m) Biên dịch lại `plugins/tdq-workflow-agy/`, kiểm linter/validate/bản cài local `3b`, và chạy trọn bộ `scripts/tdq_test.py tron-bo` lấy biên nhận `PASS` — Test: `py -3 -X utf8 scripts/tdq_test.py tron-bo --workers 1 --fresh --reuse off --timeout 1800`
  - Chạm: `plugins/tdq-workflow-agy/manifest.json`
  - Cần: QC1.3
  - Mục tiêu: Đóng gói mọi bản sửa `QC1.1`–`QC1.3` vào `plugins/tdq-workflow-agy/`, xác nhận `agy plugin validate --strict`, linter sạch, và ghi biên nhận `PASS` đầy đủ ở `docs/tdq/.tdq-test.jsonl`.
  - Vị trí neo: Trình biên dịch `tools/build_agy_plugin.py` và manifest đích `plugins/tdq-workflow-agy/manifest.json`.
  - Công cụ: Dùng `run_command`.
  - Ràng buộc: Tuyệt đối giữ nguyên bản cài cục bộ theo chốt `3b`; dùng `scripts/tdq_test.py` gốc (tránh lệch `PYTHONPATH` giữa `plugins/` và `scripts/` ở `test_tdq_test_receipt.py`) với `--workers 1 --fresh --reuse off --timeout 1800`.
  - Đặc tả kỹ thuật: Chạy `tools/build_agy_plugin.py`, `agy plugin validate --strict --json`, `ruff`, `i18n_check`, `token_budget`, `scripts/tdq_test.py tron-bo`, và `scripts/tdq_test.py so`.
  - Logic cốt lõi:
    1. Bước 1: Chạy `tools/build_agy_plugin.py` đồng bộ thay đổi sang `plugins/tdq-workflow-agy/` và kiểm `agy.EXE plugin validate --strict --json plugins/tdq-workflow-agy`.
    2. Bước 2: Chạy `py -3 -X utf8 scripts/tdq_test.py tron-bo --workers 1 --fresh --reuse off --timeout 1800` và kiểm tra biên nhận `PASS` qua `scripts/tdq_test.py so`.
    3. Bước 3: Đánh `[x] QC1.4` và chạy `scripts/tdq_team.py assign`.
  - Ca góc hiểm & TDD:
    - Ca hiểm: Ngưỡng `--timeout 900` ngắt ở ~95% bộ test (`4045/4246`), và gọi qua `plugins/` gây lệch `_implementation_identity()`; dùng `scripts/tdq_test.py` + `--timeout 1800` và `--workers 1`.
    - Tiêu chí: Biên nhận cuối trong `scripts/tdq_test.py so` có `status == "PASS"` và 0 test fail.

## Definition of Done

- [x] Q1 `lsp_gate.py` cho qua `chrome-devtools` (`select_page`, `list_pages`), `tavily-primary`, `find_references`, `find_symbol` và `other_lsp`; chặn đúng `start_lsp` (kể cả `Arguments: {}`) thiếu `language_id` và `blast_radius` vi phạm ngưỡng — Test: `py -3 -X utf8 -m pytest tests/test_lsp_gate.py tests/test_hooks_dual_protocol.py -q`
- [x] Q2 Chuẩn hoá hợp nhất tại `scripts/search_rules.py` được dùng chung bởi `_common.py`, `lsp_gate.py`, `search_observe.py` (đồng bộ `tools/patches/`); từ chối `mcp__other_lsp__*` ở cả `la_goi_khai_niem` và `lsp_ket_qua` — Test: `py -3 -X utf8 -m pytest tests/test_search_rules.py tests/test_search_observe.py tests/test_hook_windows.py tests/test_cli_fixes_new01_28.py -q`
- [x] Q3 Fail-open khi thiếu khoá `tool_input` / `Arguments` hoặc JSON hỏng và độ trễ `lsp_gate.py <= 200 ms` — Test: `py -3 -X utf8 -m pytest tests/test_lsp_gate.py -k "payload_hong or duoi_200ms" -q`
- [x] Q4 Biên dịch `plugins/tdq-workflow-agy/` sạch khớp gốc, `agy.EXE plugin validate --strict --json` đạt `0` lỗi / `0` cảnh báo, và giữ nguyên bản cài cục bộ `~/.gemini/config/plugins/` (`3b`) — Test: `py -3 -X utf8 tools/build_agy_plugin.py && agy.EXE plugin validate --strict --json plugins/tdq-workflow-agy`
- [x] Q5 Đạt chuẩn sạch AST thuần I/O (`search_rules.py`), linter (`ruff`, `doc_lint`, `i18n_check`, `token_budget`), full suite (`tdq_test.py tron-bo`) và QC `ultra` nhiều vòng với `tdq-qc-tester` — Test: `py -3 -X utf8 -m ruff check --select F,B scripts/search_rules.py hooks/scripts/_common.py hooks/scripts/lsp_gate.py hooks/scripts/search_observe.py tools/patches/agy_hooks.py tools/patches/cli_fixes_a.py`
