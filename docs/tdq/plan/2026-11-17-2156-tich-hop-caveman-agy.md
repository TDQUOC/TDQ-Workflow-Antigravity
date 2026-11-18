# PLAN — Tích hợp Caveman 5 hướng tối ưu ngữ cảnh và xin quyền vào TDQ-Workflow-Antigravity

Ngày: 2026-11-18 · Spec: ../spec/2026-11-17-2156-tich-hop-caveman-agy.md (bản 1.0, ĐÃ DUYỆT) · Lane: full
Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md
Mode thực thi: subagent — đo bằng tdq_bench.py simulate (hệ số agent 1.5): đội thắng main 12,1 phút (18,4 phút so với 30,5 phút) với 9/15 task giao subagent không trùng vùng file (ĐÃ CHỐT)
Trạng thái plan: HOÀN THÀNH

## Mục lục

- Quy tắc thi hành (áp cho mọi task)
- Thiết kế Trước vs Sau
- P1 — M1 Proxy thu gọn MCP Schema & Đo thuế tiền tố
- P2 — M2 Compact Handoff, Auto-Clarity & Hướng dẫn Browser CCR
- P3 — M3 Kho lossless CCR & Nhắc không chặn tại read_gate
- P4 — M4 Kiểm toán rò rỉ token đa host (Antigravity, Codex, Claude)
- P5 — M5 Cấu hình user-level, Xin quyền tdq_setup & Cài đặt
- P6 — Biên dịch Plugin, Khóa ngân sách, Đọc trạng thái & E2E cục bộ
- Cụm song song
- Luật file nóng (một file, nhiều task chạm)
- P7 — Log & test bắt buộc
- Definition of Done

## Quy tắc thi hành (áp cho mọi task)

1. Thứ tự phụ thuộc tuân theo `Cần:` và bảng `Cụm song song` — không đảo ngược.
2. Mỗi task: đánh `[~]` khi bắt đầu → viết test đỏ trước → code → test xanh → đổi sang `[x]` NGAY vào file này.
3. Mỗi bước: chạy `tdq_test.py vung-cham`; trọn bộ `tdq_test.py tron-bo` chạy ở cổng QC cuối (`muc_qc = full`).
4. Lệnh chạm state workflow trong test phải đặt `TDQ_PROJECT_DIR=<thư mục tạm>` ngay trên chính lệnh đó.
5. QC FAIL → thêm task fix vào mục QC/DoD của file này, lặp đến khi đạt.
6. Không commit/push cho đến khi user yêu cầu.
7. Tuân thủ `6` mã cấm cơ học (`ANTI-1` đến `ANTI-6`) và chuẩn ngôn ngữ 3 tầng (`i18n_check.py`).

## Thiết kế Trước vs Sau

| Khía cạnh | Hiện trạng (Trước) | Thiết kế mới (Sau) |
|---|---|---|
| Schema MCP | Tải thô `92.172 B` (`103` tool) gồm `$schema`, `title`, `examples`, văn xuôi dài | Proxy `tdq_mcp_shrink.py` opt-in cắt metadata thừa & văn xuôi dư (`-19%` đến `-25%`), giữ `100%` `tools/call` |
| Subagent & Browser | `6` agents chưa ép chuẩn `Auto-Clarity` / `Compact Handoff`; browser chưa nhắc `CCR` | Khuôn `path:line — symbol — note` + `Auto-Clarity` nội bộ; `tdq-browser-research` kết hợp `CCR` |
| Dữ liệu & DOM lớn | Đọc thô vào ngữ cảnh không có bản lưu khôi phục `SHA-256` | `tdq_ccr.py` lưu nguyên bản `.tdq-runtime/ccr/` (`> 32 KB` / `>= 200` dòng, trần `128 MB`) + `read_gate.py` nhắc `1` dòng |
| Kiểm toán token | `token_audit.py` chỉ đọc Claude Code (`--sessions 3`) | Hỗ trợ `Antigravity` + `Codex` + `Claude Code` (`--sessions 5`), gán nhãn `measured` / `inferred` |
| Xin quyền & Cài đặt | Chỉ có trigger xin quyền `RTK` (`--with-rtk`) | Bổ sung `caveman_config.py` (`~/.tdq/caveman.json`), `--with-caveman`, `--check-caveman`, `--mute-caveman-prompt` |

*Đối chiếu sơ đồ kiến trúc:* Tham chiếu [2026-11-17-2156-tich-hop-caveman-agy-preview.html](docs/tdq/spec/2026-11-17-2156-tich-hop-caveman-agy-preview.html) và manifest đã bind (`status=current`). Mọi thay đổi ở mã nguồn phải giữ phân tầng của `docs/kien-truc.md` (`scripts/` không import `hooks/`).

## P1 — M1 Proxy thu gọn MCP Schema & Đo thuế tiền tố

- [x] **T1.1** (e18m) Tạo proxy stdio MCP `scripts/tdq_mcp_shrink.py` và bộ unit + benchmark test `tests/test_tdq_mcp_shrink.py` — Test: `py -3 -m unittest tests/test_tdq_mcp_shrink.py -v`
  - Chạm: `scripts/tdq_mcp_shrink.py`, `tests/test_tdq_mcp_shrink.py`
  - Cần: không
  - Mục tiêu: Triển khai proxy `stdio` JSON-RPC 2.0 thuần Python stdlib để rút gọn văn xuôi & metadata thừa của `tools/list`, `prompts/list`, `resources/list` nhưng bảo toàn tuyệt đối khóa schema và `tools/call`.
  - Vị trí neo: Tạo mới hoàn toàn `scripts/tdq_mcp_shrink.py` và `tests/test_tdq_mcp_shrink.py` (không sửa file có sẵn).
  - Công cụ: Dùng `write_file` tạo hai file mới; tuân thủ `utf8_io` và log `stderr` (`TDQ_LOG=0` để tắt).
  - Ràng buộc: Thuần Python stdlib; trên Windows truyền `CREATE_NO_WINDOW` (`0x08000000`), `-u`, `PYTHONUTF8=1`, `PYTHONUNBUFFERED=1`; `stdout` chỉ phát JSON-RPC UTF-8 một dòng kết thúc `\n`.
  - Đặc tả kỹ thuật:
    `shrink_schema_node(node: Any) -> Any`, `shrink_description(text: str) -> str`, `transform_rpc_response(msg: dict, method: str | None) -> dict`, `run_proxy(cmd: list[str], stdin=None, stdout=None) -> int`
  - Logic cốt lõi:
    1. Bước 1: Đọc cấu hình target `--cmd` (hoặc phần sau `--`), nếu `TDQ_CAVEMAN == "0"` chạy passthrough nguyên dòng không biến đổi.
    2. Bước 2: Đọc từng dòng request từ client `stdin`, lưu ánh xạ `id -> method` cho `tools/list`, `prompts/list`, `resources/list`, chuyển thẳng xuống tiến trình con.
    3. Bước 3: Chặn response có `id` khớp danh sách trên: xóa đệ quy `$schema`, `title`, `examples`, `example`, `$comment` trong `inputSchema`; giữ nguyên `properties`, `required`, `enum`, `const`, `default`, `$ref`, `type`; tách câu mô tả, giữ nguyên mọi câu chứa token ràng buộc (`not`, `never`, `only`, `must`, `cannot`, `required`, `default`, `const`, `$ref`, `warning`, `deprecated`) và cắt filler ở câu dẫn còn lại.
  - Ca góc hiểm & TDD:
    - Ca hiểm: JSON lỗi/dòng rỗng (fail-open phát nguyên dòng), `tools/call` lồng JSON phức tạp, hoặc câu mô tả có từ khóa phủ định `never delete`.
    - Tiêu chí: `assert "never delete" in out_desc` và `assert out_schema["required"] == ["path"]` và `assert out_call == raw_call` và `assert elapsed_ms <= 100.0` và `assert reduction_pct >= 15.0`.

- [x] **T1.2** (e10m) Mở rộng `scripts/context_surface.py` quét thuế tiền tố thư mục MCP schema Antigravity (giữ nguyên tương thích `scripts/token_budget.py`) — Test: `py -3 scripts/context_surface.py --mcp-prefix --quiet && py -3 scripts/token_budget.py --kiem`
  - Chạm: `scripts/context_surface.py`, `scripts/token_budget.py`
  - Cần: T1.1
  - Mục tiêu: Bổ sung khả năng đo byte & ước lượng token các file schema MCP trong `~/.gemini/antigravity/mcp/` và báo cáo gộp vào bề mặt prefix tax mà không làm sai lệch `scan()` mặc định hay `token_budget.py --kiem`.
  - Vị trí neo: Sau hàm `totals(rows)` (dòng 154) và trong `main(argv=None)` (dòng 312) của `scripts/context_surface.py`; kiểm tra tương thích tại `kiem_khoa(goc=ROOT)` trong `scripts/token_budget.py`.
  - Công cụ: Dùng `edit_file` trên file có sẵn; CẤM dùng `write_file`.
  - Ràng buộc: Thuần Python stdlib; hàm thêm mới dưới `40` dòng, complexity `<= 10`; không làm thay đổi output mặc định khi không truyền `--mcp-prefix`.
  - Đặc tả kỹ thuật:
    `scan_mcp_schemas(mcp_dir: str | None = None) -> list[list[str]]`, `estimate_mcp_prefix_tax(mcp_dir: str | None = None) -> dict[str, int]`
  - Logic cốt lõi:
    1. Bước 1: Quét đệ quy các file `*.json` trong `mcp_dir` (mặc định `~/.gemini/antigravity/mcp/tdq-workflow-agy_*`).
    2. Bước 2: Đọc kích thước byte, ước lượng token (`BYTES_PER_TOKEN = 4`), tính toán thêm số byte sau khi chạy `tdq_mcp_shrink.shrink_schema_node`.
    3. Bước 3: Xuất bảng Markdown có cột trước/sau khi truyền cờ `--mcp-prefix` và log tổng kết sang `stderr`.
  - Ca góc hiểm & TDD:
    - Ca hiểm: Thư mục `~/.gemini/antigravity/mcp/` không tồn tại hoặc có JSON hỏng.
    - Tiêu chí: `assert scan_mcp_schemas("/nonexistent") == []` và `assert res["raw_bytes"] >= res["shrunk_bytes"]`.

**Xong P1 khi**: `test_tdq_mcp_shrink.py` xanh (`>= 15%` giảm byte `lsp` + `chrome-devtools`, trễ `<= 100 ms`, `tools/call` giữ nguyên `100%`) và `context_surface.py --mcp-prefix` chạy sạch.

## P2 — M2 Compact Handoff, Auto-Clarity & Hướng dẫn Browser CCR

- [x] **T2.1** (e10m) Cập nhật chuẩn `Compact Handoff` (`path:line — symbol — note`) & quy tắc `Auto-Clarity` cho `6` subagent và patch biến đổi plugin — Test: `py -3 -m unittest tests/test_subagent_start.py -v`
  - Chạm: `agents/tdq-build-resolver.md`, `agents/tdq-implementer.md`, `agents/tdq-qc-tester.md`, `agents/tdq-refactor-cleaner.md`, `agents/tdq-reviewer.md`, `agents/tdq-security-reviewer.md`, `tools/patches/skills_and_agents.py`, `tools/patches/agy_hooks.py`, `tests/test_subagent_start.py`
  - Cần: không
  - Mục tiêu: Chuẩn hóa phong cách câu ngắn `ASD-STE100` và định dạng báo cáo `path:line — symbol — note` trong `6` subagent nội bộ, đồng thời đồng bộ vào `transform_agents()` và nhắc gọn ở `SUBAGENT_DISPATCH_GATE_PY`.
  - Vị trí neo: Trong `agents/tdq-*.md` (mục `Rules:` / `Return format`), sau `handoff_schema` trong `transform_skills()` và trong `transform_agents()` của `tools/patches/skills_and_agents.py`; trong `SUBAGENT_DISPATCH_GATE_PY` (dòng 710) của `tools/patches/agy_hooks.py`.
  - Công cụ: Dùng `edit_file` cho từng file có sẵn; CẤM dùng `write_file`.
  - Ràng buộc: Nội dung `agents/*.md` viết bằng tiếng Anh chuẩn `i18n_check.py`; giữ nguyên toàn bộ trường bắt buộc hiện có của `handoff-schema.json` và `REQUIRED_IMPL_FIELDS`; tổng dung lượng `agents/*.md` sau build không vượt ngưỡng kiểm tra.
  - Đặc tả kỹ thuật:
    `AUTO_CLARITY_NOTE: str` và `compact_handoff_hint(note_line: str)` trong `tools/patches/skills_and_agents.py`; giữ cấu trúc trả về hiện có của `SUBAGENT_DISPATCH_GATE_PY`.
  - Logic cốt lõi:
    1. Bước 1: Bổ sung khối ngắn `Auto-Clarity & Compact Handoff` (nêu rõ khuôn `path:line — symbol — note`, bỏ từ đệm, giữ nguyên dấu cảnh báo an ninh/blocker) vào cuối phần `Rules` của `6` file `agents/tdq-*.md`.
    2. Bước 2: Cập nhật `tools/patches/skills_and_agents.py` để giữ nguyên khối `Auto-Clarity` khi biên dịch `transform_agents()` và hỗ trợ trường tóm tắt `path:line — symbol — note`.
    3. Bước 3: Bổ sung test trong `tests/test_subagent_start.py` xác nhận cả `6` agent chứa quy tắc `Compact Handoff` / `Auto-Clarity` và không mất trường bắt buộc nào.
  - Ca góc hiểm & TDD:
    - Ca hiểm: Thay đổi từ ngữ làm rớt các test cũ kiểm `REQUIRED_IMPL_FIELDS` hoặc `handoff-schema.json`.
    - Tiêu chí: `assert all("Auto-Clarity" in Path(p).read_text(encoding="utf-8") for p in agent_files)` và `assert "TASK:" in impl_text`.

- [x] **T2.2** (e6m) Bổ sung hướng dẫn kết hợp DOM snapshot lớn với `tdq_ccr.py` trong `skills/tdq-browser-research/SKILL.md` — Test: `py -3 scripts/doc_lint.py skills/tdq-browser-research/SKILL.md`
  - Chạm: `skills/tdq-browser-research/SKILL.md`
  - Cần: T3.1
  - Dùng: `tdq-browser-research`
  - Để: Cập nhật mục `Data Extraction` hướng dẫn lưu/tóm tắt snapshot DOM `> 32 KB` qua lệnh CLI `tdq_ccr.py`, tránh nhồi thô DOM vào ngữ cảnh.
  - Ra: `skills/tdq-browser-research/SKILL.md` chứa chỉ dẫn gọi `tdq_ccr.py summarize` & `retrieve` đúng chuẩn tiếng Anh của `i18n_check.py`.
  - Kiểm: `py -3 scripts/doc_lint.py skills/tdq-browser-research/SKILL.md && py -3 scripts/i18n_check.py skills/tdq-browser-research/SKILL.md`
  - Không dùng cho: Không sửa code Python hay chạy scrape web ngoài.

**Xong P2 khi**: `tests/test_subagent_start.py` xanh, `tdq-browser-research/SKILL.md` vượt qua `doc_lint.py` và `i18n_check.py`.

## P3 — M3 Kho lossless CCR & Nhắc không chặn tại read_gate

- [x] **T3.1** (e18m) Xây dựng kho khôi phục lossless `scripts/tdq_ccr.py` và bộ unit test `tests/test_tdq_ccr.py` — Test: `py -3 -m unittest tests/test_tdq_ccr.py -v`
  - Chạm: `scripts/tdq_ccr.py`, `tests/test_tdq_ccr.py`
  - Cần: không
  - Mục tiêu: Tạo CLI `tdq_ccr.py` lưu nguyên bản byte gốc kèm `SHA-256` tại `.tdq-runtime/ccr/` khi dữ liệu `> 32 KB` hoặc `>= 200` dòng, tóm tắt theo định dạng (JSON/JSONL/CSV/Log/YAML/DOM), xoay vòng ở trần `128 MB`, và khôi phục nguyên văn `100%`.
  - Vị trí neo: Tạo mới hoàn toàn `scripts/tdq_ccr.py` và `tests/test_tdq_ccr.py`.
  - Công cụ: Dùng `write_file` tạo hai file mới; log ISO timestamp ra `stderr` mặc định (`TDQ_LOG=0` để tắt).
  - Ràng buộc: Thuần Python stdlib; `scripts/` không import `hooks/`; lưu dưới `.tdq-runtime/ccr/`; đường dẫn và thông điệp CLI viết tiếng Anh.
  - Đặc tả kỹ thuật:
    `ingest_bytes(raw: bytes, source_path: str = "", store_dir: Path | None = None, cap_bytes: int = 134217728) -> dict`, `summarize_file(path: str, store_dir: Path | None = None) -> str`, `retrieve_record(record_id: str, store_dir: Path | None = None) -> bytes`, `enforce_cap(store_dir: Path, cap_bytes: int) -> list[str]`
  - Logic cốt lõi:
    1. Bước 1: Tính `sha256 = hashlib.sha256(raw).hexdigest()` và `record_id = sha256[:12]`; ghi nguyên tử `<id>.raw` và `<id>.meta.json` vào `.tdq-runtime/ccr/`; gọi `enforce_cap` xóa bản cũ nhất theo `mtime` nếu tổng vượt `128 MB`.
    2. Bước 2: Phân tích loại tệp (`json`/`jsonl`/`csv`/`log`/`yaml`/fallback `head+tail`) sinh bản tóm tắt cấu trúc kèm dòng neo `CCR_ID=<id> sha256=<sha256[:12]>`.
    3. Bước 3: Khi gọi `retrieve <id>`, đọc `<id>.raw`, tính lại `SHA-256` đối chiếu với `meta["sha256"]`; nếu khớp trả đúng byte gốc, nếu sai lệch báo lỗi ra `stderr` và thoát mã `1`.
  - Ca góc hiểm & TDD:
    - Ca hiểm: File nhị phân/UTF-8 có lỗi decode nhẹ, file JSON lỗi cú pháp (fallback `head+tail`), kho vượt trần `128 MB`, hoặc tệp `.raw` bị sửa tay sai `SHA-256`.
    - Tiêu chí: `assert hashlib.sha256(retrieve_record(rec["id"], store_dir)).hexdigest() == rec["sha256"]` và `assert total_bytes_after_evict <= cap_bytes` và `pytest/unittest` bắt được `ValueError` khi `.raw` bị hỏng hash.

- [x] **T3.2** (e12m) Tích hợp nhắc `CCR` không chặn khi đọc file dữ liệu/log lớn `> 32 KB` trong `hooks/scripts/read_gate.py` và bổ sung test trong `tests/test_read_gate.py` — Test: `py -3 -m unittest discover -s tests -p test_read_gate.py -v`
  - Chạm: `hooks/scripts/read_gate.py`, `tests/test_read_gate.py`
  - Cần: T3.1
  - Mục tiêu: Bổ sung nhánh nhắc `1` dòng `[TDQ:DOC]` gợi ý `tdq_ccr.py summarize` khi agent sắp đọc nguyên file dữ liệu/log (`.json`, `.jsonl`, `.csv`, `.log`, `.yaml`, `.yml`) lớn `> 32 KB` hoặc `>= 200` dòng mà giữ nguyên `100%` nguyên tắc chỉ nhắc không chặn.
  - Vị trí neo: Sau `_tao_thong_diep(ten, kb, dau, cuoi, lap_count)` (dòng 180) và trong `main()` (dòng 212–233) của `hooks/scripts/read_gate.py`.
  - Công cụ: Dùng `edit_file` trên file có sẵn; CẤM dùng `write_file`.
  - Ràng buộc: Thuần Python stdlib; giữ nguyên toàn bộ hành vi nhắc đọc lặp cũ (`NGUONG_BYTE = 2048`, `SO_SACH`, `TRAN_DONG = 400`); không kích hoạt nhắc CCR cho file code (`.py`, `.ts`, `.md`); luôn trả `allow` (không bao giờ trả `deny`).
  - Đặc tả kỹ thuật:
    `CCR_DATA_EXTS = frozenset({".json", ".jsonl", ".csv", ".log", ".yaml", ".yml"})`, `CCR_MIN_BYTES = 32768`, `_should_hint_ccr(path: str, size_bytes: int, start_line: int, end_line: int) -> bool`, `_tao_thong_diep_ccr(ten: str, kb: int, path: str) -> list[str]`
  - Logic cốt lõi:
    1. Bước 1: Kiểm tra đuôi file thuộc `CCR_DATA_EXTS`, đọc toàn file (`dau == 0 and cuoi == 0`) hoặc chưa có nhắc CCR trước đó trong sổ phiên, và `size_bytes > 32768`.
    2. Bước 2: Nếu đạt điều kiện và chưa có nhắc đọc lặp, phát nhắc `1`–`2` dòng `[TDQ:DOC]` gợi ý chạy `py -3 scripts/tdq_ccr.py summarize "<path>"` và ghi cờ vào sổ đọc.
    3. Bước 3: Xuất qua `_common.remind_force` (AGY) hoặc `permissionDecision="allow"` (Claude), bảo toàn độ trễ `< 80 ms`.
  - Ca góc hiểm & TDD:
    - Ca hiểm: File `.py` lớn `> 32 KB` không được nhắc nhầm; file `.json` nhỏ `<= 32 KB` giữ im lặng ở lần đọc đầu; đọc cắt dòng (`offset`/`limit`) không bị nhắc CCR.
    - Tiêu chí: `assert decision == "allow"` và `assert "tdq_ccr.py summarize" in ctx` cho file `.log` `40 KB`, và `assert silent` cho file `.py` `40 KB`.

**Xong P3 khi**: `test_tdq_ccr.py` và `test_read_gate.py` xanh `100%`, khôi phục `SHA-256` khớp tuyệt đối và `read_gate.py` chỉ nhắc không chặn.

## P4 — M4 Kiểm toán rò rỉ token đa host (Antigravity, Codex, Claude)

- [x] **T4.1** (e18m) Mở rộng `scripts/tdq_transcript.py` và `scripts/token_audit.py` hỗ trợ kiểm toán rò rỉ token đa host (`Antigravity`, `Codex`, `Claude Code`) với `--sessions 5` và nhãn `measured`/`inferred` — Test: `py -3 -m unittest tests/test_transcript.py -v && py -3 -m unittest discover -s tests -p test_token_audit.py -v`
  - Chạm: `scripts/tdq_transcript.py`, `scripts/token_audit.py`, `tests/test_transcript.py`, `tests/test_token_audit.py`
  - Cần: không
  - Mục tiêu: Cho phép `token_audit.py --host all|agy|codex|claude --sessions 5` đọc chính xác phiên Antigravity (`PLANNER_RESPONSE`/`TOOL_RESPONSE`/`GENERIC`) và Codex (`event_msg`/`response_item`) bên cạnh Claude Code, xếp hạng top tool call/file đọc lặp/subagent tốn token kèm nhãn `measured` hoặc `inferred`.
  - Vị trí neo: Sau `_read_agy(record, source)` (dòng 579) trong `scripts/tdq_transcript.py`; tại `iter_events(path)`, `_scan(path)`, `usage_totals(paths)`, và `main(argv=None)` (dòng 447) của `scripts/token_audit.py`.
  - Công cụ: Dùng `edit_file` trên file có sẵn; CẤM dùng `write_file`.
  - Ràng buộc: Bảo toàn `100%` hành vi & API cũ của `token_audit.py` cho Claude Code (`carry_cost`, `usage_totals`, `cost_equivalent`); bỏ qua dòng JSON gãy an toàn; log ra `stderr` (`TDQ_AUDIT_LOG=0` hoặc `TDQ_LOG=0`).
  - Đặc tả kỹ thuật:
    `discover_host_sessions(host: str = "all", project_dir: str | None = None, limit: int = 5, home: str | None = None) -> list[tuple[str, str]]`, `audit_multi_host(host: str = "all", project_dir: str | None = None, limit: int = 5, top: int = 10, home: str | None = None) -> dict`
  - Logic cốt lõi:
    1. Bước 1: Dùng `_agy_directories` và thư mục `~/.codex/sessions` + `claude_transcript_dir` gom tối đa `limit` phiên mới nhất theo từng host.
    2. Bước 2: Chuyển đổi bản ghi `PLANNER_RESPONSE` (lấy usage `input_tokens`/`output_tokens`/`cache_read_tokens` nếu có và `tool_calls`) và `TOOL_RESPONSE`/`GENERIC` của Antigravity, cũng như `event_msg`/`response_item` của Codex thành luồng sự kiện chuẩn cho `_scan()`.
    3. Bước 3: Tính `carry-cost`, danh sách file đọc lặp và subagent tốn nhiều nhất; gán nhãn `measured` khi có usage API hoặc tokenizer thật và `inferred` khi dùng ước lượng cho định dạng không có usage trực tiếp.
  - Ca góc hiểm & TDD:
    - Ca hiểm: File `transcript.jsonl` có dòng truncated/hỏng JSON giữa chừng, phiên rỗng, hoặc thiếu `anthropic-tokenizer` ở một host ngoài Anthropic.
    - Tiêu chí: `assert report["sessions_scanned"] >= 1` trên fixture AGY/Codex, `assert all(row["basis"] in ("measured", "inferred") for row in report["hosts"])`, và toàn bộ test cũ của `test_token_audit.py` + `test_transcript.py` xanh.

**Xong P4 khi**: `test_transcript.py` và `test_token_audit.py` xanh `100%` và `token_audit.py --host agy --sessions 5 --top 10` chạy ra bảng thật trên phiên Antigravity hiện tại.

## P5 — M5 Cấu hình user-level, Xin quyền tdq_setup & Cài đặt

- [x] **T5.1** (e14m) Tạo trình quản lý cấu hình user-level `scripts/caveman_config.py` (mô phỏng khuôn `rtk_integration.py`) và bộ unit test `tests/test_caveman_setup.py` — Test: `py -3 -m unittest tests/test_caveman_setup.py -v`
  - Chạm: `scripts/caveman_config.py`, `tests/test_caveman_setup.py`
  - Cần: T1.1
  - Mục tiêu: Quản lý trạng thái opt-in (`~/.tdq/caveman.json`) và hàm bọc/gỡ `3` server MCP (`lsp`, `chrome-devtools`, `tavily-primary`) trong `mcp_config.json` của plugin một cách nguyên tử kèm bản sao lưu.
  - Vị trí neo: Tạo mới hoàn toàn `scripts/caveman_config.py` và `tests/test_caveman_setup.py`.
  - Công cụ: Dùng `write_file` tạo hai file mới; log ISO timestamp ra `stderr`.
  - Ràng buộc: Thuần Python stdlib; mặc định `enabled = False`, `prompt_muted = False`; tôn trọng biến môi trường kiểm thử `TDQ_CAVEMAN_CONFIG` hoặc `HOME`/`USERPROFILE`; tuyệt đối không tự bật nếu user chưa gọi `enable_caveman(approve=True)`.
  - Đặc tả kỹ thuật:
    `config_path(home: str | None = None) -> Path`, `load_config(home: str | None = None) -> dict`, `set_prompt_muted(muted: bool, home: str | None = None) -> Path`, `wrap_mcp_config(mcp_file: Path, proxy_script: Path) -> list[str]`, `unwrap_mcp_config(mcp_file: Path) -> list[str]`, `probe_caveman(plugin_root: Path | None = None, home: str | None = None) -> dict`
  - Logic cốt lõi:
    1. Bước 1: Đọc/ghi nguyên tử `~/.tdq/caveman.json` (temp file + `os.replace`) chứa `enabled`, `prompt_muted`, `wrapped_servers`, `updated_at`.
    2. Bước 2: Khi `wrap_mcp_config()` chạy: sao lưu `mcp_config.json.bak` nếu chưa có; bọc lệnh của `lsp`, `chrome-devtools`, `tavily-primary` qua `[sys.executable, "-u", str(proxy_script), "--", orig_cmd, *orig_args]` kèm `PYTHONUTF8="1"`, `PYTHONUNBUFFERED="1"` (không bọc trùng nếu đã bọc).
    3. Bước 3: Khi `unwrap_mcp_config()` chạy: bóc wrapper về đúng `command`/`args` gốc (hoặc khôi phục từ bản lưu `orig` trong cấu hình) và đặt `enabled = False`.
  - Ca góc hiểm & TDD:
    - Ca hiểm: Gọi `wrap_mcp_config()` nhiều lần liên tiếp phải idempotent (không bọc lồng proxy 2 lần); `mcp_config.json` thiếu một trong `3` server vẫn bọc các server hiện có an toàn.
    - Tiêu chí: `assert wrapped == ["lsp", "chrome-devtools", "tavily-primary"]`, bọc lần 2 trả `[]` hoặc giữ nguyên 1 lớp wrapper, và `unwrap_mcp_config()` khôi phục byte-for-byte khớp lệnh gốc.

- [x] **T5.2** (e14m) Tích hợp cờ xin quyền Caveman vào `scripts/tdq_setup.py`, chẩn đoán ở `scripts/tdq_lsp.py` và nhắc `[TDQ:SETUP]` ở `hooks/scripts/session_start.py` — Test: `py -3 scripts/tdq_setup.py --check-caveman && py -3 scripts/tdq_lsp.py check`
  - Chạm: `scripts/tdq_setup.py`, `scripts/tdq_lsp.py`, `hooks/scripts/session_start.py`
  - Cần: T5.1
  - Mục tiêu: Bổ sung bộ cờ `--with-caveman`, `--without-caveman`, `--check-caveman`, `--mute-caveman-prompt`, `--unmute-caveman-prompt` vào `tdq_setup.py` (tuyệt đối không chạy ngầm trong `--nen`), in trạng thái Caveman ở `tdq_lsp.py check` và nhắc `1` dòng ở `session_start.py`.
  - Vị trí neo: Sau `_xu_ly_rtk_flags(args, project)` (dòng 1915) và trong `parse_args()`/`main()` (dòng 1892, 1967) của `scripts/tdq_setup.py`; sau `_in_cong_cu_bo_tro(project)` (dòng 756) của `scripts/tdq_lsp.py`; ngay sau khối `nhac_rtk` (dòng 289) của `hooks/scripts/session_start.py`.
  - Công cụ: Dùng `edit_file` trên file có sẵn; CẤM dùng `write_file`.
  - Ràng buộc: Giữ nguyên `8` bậc exit code của `tdq_lsp.py check`; `--nen` không bao giờ bật Caveman hay ghi `~/.tdq/caveman.json`; `session_start.py` chỉ nhắc tối đa `1` lần/phiên (`already_reminded(..., "SETUP-CAVEMAN")`) và tắt được qua `mute`.
  - Đặc tả kỹ thuật:
    `_xu_ly_caveman_flags(args, project) -> int | None` trong `scripts/tdq_setup.py`; mở rộng `kiem_tra_cong_cu_bo_tro(project)` / `_in_cong_cu_bo_tro(project)` trong `scripts/tdq_lsp.py`; khối `nhac_caveman` trong `hooks/scripts/session_start.py`.
  - Logic cốt lõi:
    1. Bước 1: Trong `tdq_setup.py`, xử lý `--mute/unmute-caveman-prompt`, `--check-caveman`, `--with-caveman` (bật `caveman.json` + bọc `mcp_config.json` của plugin hiện tại), `--without-caveman` (tắt + gỡ bọc); đặt trước nhánh `if args.nen:`.
    2. Bước 2: Trong `tdq_lsp.py`, mở rộng `_in_cong_cu_bo_tro()` in dòng `Công cụ bổ trợ (Caveman): ...` và gợi ý `py -3 scripts/tdq_setup.py --with-caveman` khi chưa bật.
    3. Bước 3: Trong `session_start.py`, kiểm tra `caveman_config.probe_caveman()` khi chưa muted và chưa nhắc `SETUP-CAVEMAN` để chèn 1 dòng `[TDQ:SETUP]`.
  - Ca góc hiểm & TDD:
    - Ca hiểm: Khi `--nen` chạy, trạng thái `caveman.json` vẫn giữ nguyên chưa bật; khi `prompt_muted=True`, `session_start.py` im lặng hoàn toàn về Caveman.
    - Tiêu chí: `assert not probe_caveman()["enabled"]` sau `--nen`, và `assert "[TDQ:SETUP]" in output` khi chưa bật & chưa mute.

- [x] **T5.3** (e14m) Cập nhật `tools/patches/agy_manifests.py`, `tools/install_agy_plugin.py`, `install.py`, `install.ps1`, `install.sh` giữ mặc định không bọc và hỗ trợ `--with-caveman` / `--skip-caveman` khi cài đặt — Test: `py -3 tools/install_agy_plugin.py --dry-run && py -3 install.py --dry-run --skip-rtk --skip-caveman`
  - Chạm: `tools/patches/agy_manifests.py`, `tools/install_agy_plugin.py`, `install.py`, `install.ps1`, `install.sh`
  - Cần: T5.1
  - Mục tiêu: Đảm bảo `generate_mcp_config()` mặc định giữ sạch `3` server MCP gốc (không bọc ngầm), còn `install_agy_plugin.py` và `install.*` hỗ trợ hỏi/truyền cờ `--with-caveman` và `--skip-caveman` tương tự `--with-rtk` / `--skip-rtk`.
  - Vị trí neo: Trong `generate_mcp_config(plugin_root)` (dòng 142) và `generate_two_tier_rules(plugin_root)` (dòng 165) của `tools/patches/agy_manifests.py`; sau `_handle_rtk()` (dòng 62) và trong `parse_args()`/`main()` (dòng 112–160) của `tools/install_agy_plugin.py`; sau `_handle_rtk_trigger()` (dòng 143) của `install.py` và tham số tương ứng ở `install.ps1`, `install.sh`.
  - Công cụ: Dùng `edit_file` trên file có sẵn; CẤM dùng `write_file`.
  - Ràng buộc: `generate_mcp_config()` mặc định KHÔNG bọc proxy khi chưa opt-in; nếu cài mới hoặc update mà `~/.tdq/caveman.json` đã từng được user bật (`enabled=True`) hoặc có truyền `--with-caveman`, `install_agy_plugin.py` mới thực hiện bọc `mcp_config.json` tại đích.
  - Đặc tả kỹ thuật:
    `_handle_caveman(src: Path, dst: Path, with_caveman: bool, skip_caveman: bool, dry_run: bool) -> tuple[int, dict]` trong `tools/install_agy_plugin.py`; `_handle_caveman_trigger(...)` trong `install.py`; switch `$WithCaveman`/`$SkipCaveman` trong `install.ps1`.
  - Logic cốt lõi:
    1. Bước 1: Thêm nhắc ngắn về `tdq_ccr.py` & `Compact Handoff` vào rule `AGENTS.md` (giữ dưới `24 KB` và không vượt `token_budget`).
    2. Bước 2: Trong `install_agy_plugin.py`, bổ sung `--with-caveman`, `--without-caveman`, `--skip-caveman`; sau `_sync_local_mcp()`, gọi `_handle_caveman()` kiểm tra trạng thái cấu hình và chỉ bọc khi được phép.
    3. Bước 3: Chuyển tiếp `--with-caveman` / `--skip-caveman` trong `install.py`, `install.ps1`, `install.sh` theo đúng mẫu của `--with-rtk` / `--skip-rtk`.
  - Ca góc hiểm & TDD:
    - Ca hiểm: Chạy `install.py --dry-run` không được ghi vào `~/.tdq/caveman.json` hay sửa `~/.gemini/config/plugins/`.
    - Tiêu chí: `assert "mcpServers" in default_cfg` với lệnh `lsp`/`npx` gốc khi chưa opt-in, và `dry_run` in JSON có cả `"rtk"` lẫn `"caveman"`.

**Xong P5 khi**: `test_caveman_setup.py` xanh, `--check-caveman` và `--dry-run` của `install_agy_plugin.py` + `install.py` trả về trạng thái chính xác mà không tự bật ngầm.

## P6 — Biên dịch Plugin, Khóa ngân sách, Đọc trạng thái & E2E cục bộ

- [x] **T6.1** (e10m) Biên dịch lại `plugins/tdq-workflow-agy/` qua `build_agy_plugin.py`, khóa lại `docs/tdq/token-budget.json`, kiểm tính di động và xác thực `agy.EXE plugin validate --strict --json` — Test: `py -3 tools/build_agy_plugin.py && py -3 scripts/token_budget.py --kiem && agy.EXE plugin validate --strict --json plugins/tdq-workflow-agy`
  - Chạm: `plugins/tdq-workflow-agy/**`, `docs/tdq/token-budget.json`
  - Cần: T1.2, T2.1, T2.2, T3.2, T4.1, T5.2, T5.3
  - Dùng: `tdq-checkportable`
  - Để: Xác minh gói plugin biên dịch trong `plugins/tdq-workflow-agy/` giữ tính di động (không lộ API key hay đường dẫn máy cá nhân trong `mcp_config.json` mặc định).
  - Ra: Báo cáo pass của `tdq_checkportable.py`, `build_agy_plugin.py` và `agy.EXE plugin validate --strict --json` (`0 findings`).
  - Kiểm: `py -3 tools/build_agy_plugin.py && py -3 scripts/tdq_checkportable.py && agy.EXE plugin validate --strict --json plugins/tdq-workflow-agy`
  - Không dùng cho: Không chỉnh tay tệp đã biên dịch trong `plugins/tdq-workflow-agy/`.

- [x] **T6.2** (e10m) Cập nhật bản cài plugin cục bộ tại `~/.gemini/config/plugins/tdq-workflow-agy`, chạy nghiệm thu E2E sống (`M1` stdio, `M3` CCR, `M4` AGY/Codex audit, `M5` `--with-caveman`/`--check-caveman`) và kiểm trạng thái setup/token — Test: `py -3 tools/install_agy_plugin.py --sync-local-mcp --with-caveman && py -3 scripts/tdq_setup.py --check-caveman && py -3 scripts/context_surface.py --mcp-prefix --quiet`
  - Chạm: (không sửa tệp nguồn repo — đồng bộ bản cài cục bộ và chạy E2E)
  - Cần: T6.1
  - Dùng: `tdq-setup`, `tdq-check-status`, `tdq-status`, `tdq-lean`
  - Để: Kiểm tra trạng thái setup Caveman, đo bề mặt ngữ cảnh (`tdq-lean` / `context_surface.py`) và đối chiếu trạng thái `tdq-check-status` / `tdq-status` sau khi đồng bộ bản cài cục bộ.
  - Ra: Kết quả E2E sống của proxy `M1`, khôi phục `M3` `SHA-256`, audit `M4` trên phiên Antigravity hiện tại và đầu ra `--check-caveman` đạt.
  - Kiểm: `py -3 scripts/tdq_setup.py --check-caveman && py -3 scripts/context_surface.py --mcp-prefix --quiet && py -3 scripts/token_audit.py --host agy --sessions 5 --top 5`
  - Không dùng cho: Không tự ý sửa state.json hay tắt các cổng QC.

- [x] **T6.3** (e6m) Điều phối tổng hợp nếu user chọn chạy đội `subagent` qua `self` cho các cụm độc lập — Test: `py -3 scripts/tdq_team.py assign`
  - Chạm: (không sửa file — rà soát hợp đồng giao việc & gom kết quả nếu chạy `subagent`)
  - Cần: T6.2
  - Dùng: `self`
  - Để: Giữ quy chuẩn điều phối subagent/tổng hợp wave khi thực thi ở chế độ `subagent` (hoặc bỏ qua gọn khi chạy `main`).
  - Ra: Kết quả kiểm tra tích hợp sạch sau khi toàn bộ wave đã hợp nhất.
  - Kiểm: `py -3 scripts/tdq_test.py vung-cham`
  - Không dùng cho: Không thay thế bước QC cuối hay tự ý đổi `implement_mode`.

**Xong P6 khi**: `agy.EXE plugin validate` đạt `0 findings`, `token_budget.py --kiem` xanh và E2E trên bản cài cục bộ chạy thành công.

## Cụm song song

Bảng dưới đây cắt kế hoạch thành các cụm tách biệt theo `Chạm:` để có thể chạy tuần tự (`main`) hoặc song song theo wave (`subagent`) mà không xung đột tệp:

| Đợt (Wave) | Các task chạy song song được | Vùng `Chạm:` tách biệt |
|---|---|---|
| Wave 1 (Độc lập hoàn toàn) | `T1.1` (`M1-Proxy`), `T2.1` (`M2-Clarity`), `T3.1` (`M3-CCR`), `T4.1` (`M4-Audit`) | `tdq_mcp_shrink.py` · `agents/tdq-*.md` + `skills_and_agents.py` + `agy_hooks.py` · `tdq_ccr.py` · `tdq_transcript.py` + `token_audit.py` |
| Wave 2 (Sau khi T1.1 & T3.1 xong) | `T1.2` (`M1` surface), `T2.2` (`M2` skill browser), `T3.2` (`M3` `read_gate.py`), `T5.1` (`M5` `caveman_config.py`) | `context_surface.py` + `token_budget.py` · `tdq-browser-research/SKILL.md` · `read_gate.py` · `caveman_config.py` |
| Wave 3 (Sau khi T5.1 xong) | `T5.2` (`tdq_setup.py` + `tdq_lsp.py` + `session_start.py`), `T5.3` (`agy_manifests.py` + `install_*`) | Không trùng đường dẫn nào giữa `T5.2` và `T5.3` |
| Wave 4 (Tích hợp tuần tự) | `T6.1` → `T6.2` → `T6.3` → `T7.1` → `T7.2` | Build `plugins/tdq-workflow-agy/`, khóa `token-budget.json`, E2E cục bộ, `tron-bo` & linter |

## Luật file nóng (một file, nhiều task chạm)

Kiểm tra toàn bộ danh sách `Chạm:` từ `T1.1` đến `T6.3`: **không có tệp mã nguồn nào xuất hiện ở 2 task khác nhau** (bằng chứng tách vùng ở §2b và bảng `Cụm song song` trên). Tệp biên dịch `plugins/tdq-workflow-agy/**` và `docs/tdq/token-budget.json` chỉ có **một chủ ghi duy nhất** là `T6.1` (`build_agy_plugin.py`) sau khi tất cả cụm nguồn đã hoàn tất.

## P7 — Log & test bắt buộc

- [x] **T7.1** (e5m) Xác nhận toàn bộ module mới/mở rộng (`M1`–`M5`) bật log timestamp ra `stderr` và tắt được qua `TDQ_LOG=0` — Test: `py -3 -c "import subprocess, sys; r=subprocess.run([sys.executable,'scripts/tdq_ccr.py','--help'],capture_output=True,text=True); assert r.returncode==0"`
  - Chạm: (chỉ chạy kiểm tra runtime logging trên các script đã hoàn tất, không sửa tệp mã nguồn)
  - Cần: T6.2
  - Mục tiêu: Đảm bảo dịch vụ log ISO timestamp hoạt động mặc định trên `stderr` và im lặng sạch khi đặt `TDQ_LOG=0`.
  - Vị trí neo: Kiểm tra hàm `_log()` tại các module đã tạo ở Wave 1–3.
  - Công cụ: Chỉ chạy lệnh kiểm tra bằng `run_command`.
  - Ràng buộc: `stdout` của proxy MCP và installer JSON tuyệt đối sạch không lẫn log.
  - Đặc tả kỹ thuật:
    `TDQ_LOG=0` tắt dòng `[YYYY-MM-DDTHH:MM:SS] ...` trên `stderr`; mặc định `TDQ_LOG=1` phát dòng chẩn đoán.
  - Logic cốt lõi:
    1. Bước 1: Chạy `tdq_ccr.py`, `caveman_config.py`, `tdq_mcp_shrink.py` với `TDQ_LOG=1` và kiểm `stderr` có ISO timestamp.
    2. Bước 2: Chạy lại với `TDQ_LOG=0` và kiểm `stderr` rỗng.
    3. Bước 3: Kiểm tra `stdout` của `tdq_mcp_shrink.py` chỉ chứa JSON-RPC hợp lệ.
  - Ca góc hiểm & TDD:
    - Ca hiểm: Quên kiểm tra `TDQ_LOG=0` ở một module mới khiến log làm nhiễu output.
    - Tiêu chí: `assert "T" in err_on` và `assert err_off == ""`.

- [x] **T7.2** (e12m) Chạy trọn bộ unit test & linter (`tdq_test.py tron-bo`, `doc_lint`, `i18n_check`, `token_budget --kiem`, `ruff`) sau lần sửa cuối — Test: `py -3 scripts/tdq_test.py tron-bo && py -3 scripts/i18n_check.py && py -3 scripts/doc_lint.py`
  - Chạm: (chạy kiểm định toàn repo ở cổng `muc_qc = full`)
  - Cần: T7.1
  - Mục tiêu: Khóa `0` regression và `0` vi phạm linter trước khi chuyển pha `report`.
  - Vị trí neo: Bộ kiểm định toàn kho tdq_test.py.
  - Công cụ: Chạy `run_command`.
  - Ràng buộc: Mọi unit test phải xanh sau lần sửa cuối, không bỏ qua hay nới lỏng assertion.
  - Đặc tả kỹ thuật:
    Chạy lần lượt `tdq_test.py tron-bo`, `i18n_check.py`, `doc_lint.py`, `token_budget.py --kiem`, `ruff check scripts hooks tools tests`.
  - Logic cốt lõi:
    1. Bước 1: Chạy `tdq_test.py tron-bo`.
    2. Bước 2: Chạy các linter chuẩn ngôn ngữ, tài liệu, ngân sách token và `ruff`.
    3. Bước 3: Ghi kết quả thực đo vào file báo cáo QC của request.
  - Ca góc hiểm & TDD:
    - Ca hiểm: Một test mới phá ngầm `test_agy_plugin_validate.py` hoặc `i18n_check.py`.
    - Tiêu chí: Toàn bộ lệnh trả mã thoát `0`, `0` fail.

## Definition of Done

- [x] Q1 Bảo toàn bất biến Proxy MCP (`M1`): `100%` khóa schema & câu chứa từ phủ định + `tools/call` giữ nguyên, trễ `<= 100 ms` — `py -3 -m unittest tests/test_tdq_mcp_shrink.py -v`
- [x] Q2 Giảm thuế schema `>= 15%` & `6` subagent chuẩn `Auto-Clarity` (`M1` + `M2`) — `py -3 -m unittest tests/test_tdq_mcp_shrink.py tests/test_subagent_start.py -v && py -3 scripts/context_surface.py --mcp-prefix --quiet`
- [x] Q3 Kho `CCR` `> 32 KB` / `>= 200` dòng, trần `128 MB`, khôi phục `100%` `SHA-256` & `read_gate.py` nhắc không chặn (`M3`) — `py -3 -m unittest tests/test_tdq_ccr.py tests/test_read_gate.py -v`
- [x] Q4 Kiểm toán token đa host (`Antigravity`, `Codex`, `Claude Code`) mặc định `5` phiên với nhãn `measured`/`inferred` (`M4`) — `py -3 -m unittest tests/test_transcript.py tests/test_token_audit.py -v && py -3 scripts/token_audit.py --host agy --sessions 5 --top 5`
- [x] Q5 Xin quyền `M5`, `--nen` không tự bật ngầm, build & validate plugin `0` lỗi và trọn suite xanh — `py -3 -m unittest tests/test_caveman_setup.py -v && py -3 tools/build_agy_plugin.py && py -3 scripts/token_budget.py --kiem && py -3 scripts/i18n_check.py && py -3 scripts/doc_lint.py && agy.EXE plugin validate --strict --json plugins/tdq-workflow-agy && py -3 scripts/tdq_test.py tron-bo`
- [x] Q6 Nghiệm thu E2E sống trên bản cài cục bộ `~/.gemini/config/plugins/tdq-workflow-agy` (`M1` stdio, `M3` CCR, `M4` audit, `M5` `--check-caveman`) — `py -3 scripts/tdq_setup.py --check-caveman && py -3 scripts/tdq_lsp.py check`
