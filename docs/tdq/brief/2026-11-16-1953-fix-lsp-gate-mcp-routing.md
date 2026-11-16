# BRIEF — Fix triệt để lỗi lsp_gate chặn nhầm call_mcp_tool và chuẩn hoá phân luồng MCP/LSP

Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

## Nguyên văn

- Prompt mở request: "okay bây giờ tôi muốn check lỗi này" (kèm ảnh chụp báo lỗi `PreToolUse` hook chặn `chrome-devtools -> select_page` với `[TDQ:LSP] start_lsp without language_id...`).
- Prompt chốt pipeline: "1b và tôi muốn fix triệt để" (`lane=full`, `loai_request=bugfix`, nhánh `bugfix/fix-lsp-gate-mcp-routing` mở từ `dev`).
- Ghi chú LSP ở `init`: Mở qua `--bo-qua-lsp` (`pyrightconfig.json` chỉ include `scripts/hooks/tests` nên symbol mẫu ở `tools/patches/agy_manifests.py` trả `symbols=1`; bản thân `start_lsp` cho `python` hoạt động, nhưng chính lỗi `lsp_gate.py` đang chặn `call_mcp_tool -> find_references` trực tiếp trong phiên).

## Hiểu & kiến thức

### Năng lực dùng được

Phân vân → DÙNG. Kiểm kê ngày 2026-11-16: 42 dòng skill trên đĩa (nguồn `plugin:tdq-workflow`, `plugin:tdq-workflow-agy`, `user`), cộng built-in skills trong context.

| Skill | Nguồn | Phán quyết | Dùng ở đâu / Lý do loại |
|---|---|---|---|
| `tdq-setup` | `plugin:tdq-workflow` | `DÙNG` | đối chiếu quy ước 3 tầng tìm kiếm (`uu-tien-tim-kiem.md`) và định danh MCP server `lsp` (`tdq_lsp.py`) |
| `tdq-browser-research` | `plugin:tdq-workflow-agy` | `DÙNG` | tham chiếu chuỗi gọi thật của `chrome-devtools` qua `call_mcp_tool` cho ca test tái hiện |
| `tdq-browser-test` | `plugin:tdq-workflow-agy` | `DÙNG` | kiểm chứng tương thích các tool tương tác Chrome DevTools (`select_page`, `click`, `evaluate_script`…) |
| `tdq-conventions` · `tdq-intake` · `tdq-spec` · `tdq-plan` · `tdq-build` · `tdq-lean` · `tdq-check-status` · `tdq-status` · `tdq-checkportable` | `plugin:tdq-workflow` / `plugin:tdq-workflow-agy` | `NỀN` | quy trình TDQ Workflow đang chạy |
| Đã xét 19 skill ẩn theo từ khoá + skill built-in khác | user/plugin/built-in | `KHÔNG` | `khác lĩnh vực` |

### Phạm vi đã chốt

- Mặt CHỌN: Sửa đúng định tuyến `lsp_gate.py`, siết chuẩn hoá TDQ LSP vs server ngoài ở `_common.py` / `search_observe.py` / `search_rules.py` / `tools/patches/`, gom helper chuẩn hoá MCP dùng chung ở `scripts/search_rules.py`, biên dịch đồng bộ `plugins/tdq-workflow-agy/` trong repo, chặn `start_lsp` tường minh với `Arguments: {}` (giữ fail-open khi thiếu khoá tham số / JSON hỏng), và chạy `muc_qc = ultra` kèm `tdq-qc-tester` nhiều vòng nếu còn lỗi.
- Mặt LOẠI: Chưa đồng bộ ra bản cài cục bộ `C:/Users/admin/.gemini/config/plugins/tdq-workflow-agy` trước khi hỏi commit (theo chốt `3b`); không thay đổi matcher `"mcp_.*lsp_.*|call_mcp_tool"` ở `hooks.json` vì host Antigravity chỉ lọc theo tên tool.
- Bối cảnh: Kho mã nguồn TDQ-Workflow-Antigravity `v0.97.1`, Python `3.13` stdlib hooks, ngưỡng hiệu năng `lsp_gate.py <= 200 ms` (đo hiện tại `66.4 – 72.2 ms`).
- Mức đầu tư suy ra: đầy đủ (`muc_qc = ultra`) — vì sửa tầng hook `PreToolUse` đa host ảnh hưởng trực tiếp tới toàn bộ tool MCP & LSP.

### Bối cảnh & Tam giác khảo sát 3 chiều

- **Kiến trúc (`docs/kien-truc.md`):** `hooks/` gọi được `scripts/`; `scripts/` không import `hooks/` và `scripts/search_rules.py` giữ thuần I/O (`test_log_module_thuan_khong_tu_in`); chuỗi máy và docstring viết tiếng Anh cố định (`i18n_check.py`).
- **Tài liệu host:** Đã kiểm trực tiếp từ `builtin/skills/agy-customizations/docs/{hooks,plugins}.md` (không cần web research ngoài).

| Vùng file chạm | Phát hiện qua lớp nào (Grep / LSP / Graphify) | Tác động & quan hệ |
|---|---|---|
| `hooks/scripts/lsp_gate.py` | Grep + Tái hiện thực tế | Rẽ nhánh nhị phân `if "blast_radius" ... else phan_xu` chặn nhầm `chrome-devtools`, `tavily`, lẫn `find_references`/`find_symbol`; bỏ sót `start_lsp` với `Arguments: {}`. |
| `hooks/scripts/_common.py` | Grep (`_unwrap_call_mcp`) | Quy đổi lỏng `"lsp" in srv` và `"_lsp_" in tname`; chưa phân biệt rõ thiếu khoá tham số vs `Arguments: {}` rỗng. |
| `hooks/scripts/search_observe.py` | Grep + Đọc mã | Dòng 181 `"lsp" in tool_name.lower()` ghi nhầm `lsp_ket_qua` cho server/tool ngoài chứa chuỗi `lsp`. |
| `scripts/search_rules.py` | Grep + Graphify (`_agy_unwrap_tool` L1162) | Nhân bản logic unwrap theo `"lsp" in srv` / `"_lsp_" in ten`, chưa decode `Arguments` chuỗi double-JSON, xung đột ca `mcp__other_lsp__find_symbol`. |
| `tools/patches/{agy_hooks,cli_fixes_a}.py` | Grep + Graphify | Giữ đồng bộ `COMMON_PY` và patch `_agy_unwrap_tool` khi biên dịch `plugins/tdq-workflow-agy/`. |
| `tests/{test_lsp_gate,test_search_rules,test_search_observe,test_hooks_dual_protocol}.py` | Grep | Khoá unit test & E2E dual-protocol (`cmd /c`) + `test_agy_plugin_validate.py`. |

### Lộ trình

| Bước/phase | Chạy? | Vì sao |
|---|---|---|
| Research web | BỎ | Lỗi thuần nội bộ giữa mã TDQ và đặc tả Antigravity đã xác thực ngay trên đĩa |
| Interview | CÓ (xong) | Đã chốt đủ 5 câu hỏi (`1a 2a 3b 4c agent QC nhiều round 5a`) và `muc_qc = ultra` |
| Spec + Archify Preview | CÓ | Chạm `hooks/`, `scripts/`, `tools/patches/`, biên dịch plugin |
| Plan + Implement (`mode` do user chọn) | CÓ | Triển khai red → green theo từng module rời M1–M5 |
| QC độc lập (`tdq-qc-tester`) | CÓ (`ultra`, nhiều vòng nếu cần) | Đúng yêu cầu `4c agent QC nhiều round`, xác minh full suite + `agy plugin validate` + live `cmd /c` |
| Report + Archify HTML | CÓ | Xuất báo cáo kèm sơ đồ, hỏi commit (và cập nhật local sau commit theo `3b`) |

## Hỏi đáp

- **Phỏng vấn chốt ngày 2026-11-16T20:10:**
  1. Phạm vi "fix triệt để" → User chọn `1a`: trọn 4 lớp (sửa `lsp_gate.py`, siết chuẩn hoá TDQ LSP vs server ngoài ở `_common.py`/`search_observe.py`/`search_rules.py`/`tools/patches/`, gộp helper giải gói MCP về 1 nguồn dùng chung trong `scripts/search_rules.py`, biên dịch đồng bộ `plugins/tdq-workflow-agy/`).
  2. Xử lý `start_lsp` với `Arguments: {}` rỗng → User chọn `2a`: chặn `deny` với `[TDQ:LSP]`, vẫn giữ fail-open khi payload hỏng JSON hoặc thiếu khoá tham số.
  3. Đồng bộ bản cài local trước hỏi commit → User chọn `3b`: chỉ sửa & biên dịch `plugins/tdq-workflow-agy/` trong repo; cập nhật local sau khi duyệt commit/release.
  4. Mức QC → User chọn `4c` + `"agent QC nhiều round"` (`muc_qc = ultra`, có `tdq-qc-tester` độc lập kiểm kỹ nhiều vòng nếu phát hiện lỗi).
  5. Bổ sung → User chọn `5a`: không bổ sung thêm.
