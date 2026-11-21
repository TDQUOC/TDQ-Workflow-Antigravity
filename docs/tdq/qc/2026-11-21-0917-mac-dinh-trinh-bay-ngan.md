# QC — Mặc định Trình bày Report, Spec & Plan Ngắn gọn, Tự nhiên, Dễ hiểu

Ngày: 2026-11-21 · Spec: ../spec/2026-11-21-0917-mac-dinh-trinh-bay-ngan.md · Plan: ../plan/2026-11-21-0917-mac-dinh-trinh-bay-ngan.md · Vòng: 1 (`muc_qc=full`)
Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

| # | Hạng mục | Lệnh đã chạy | Kết quả | PASS/FAIL |
|---|---|---|---|---|
| Q1 | Quy chuẩn văn phong & ký tự (`user-facing-block`, `report-template`, 6 ký tự) | `scan_block_symbols.py --chi-khoi` + `pytest tests/test_user_facing_block.py tests/test_report_visual.py tests/test_luat_gate_chat.py` | `5` ký tự chuẩn, `0` ngoài whitelist; `0` lỗi test khối chat & report | PASS |
| Q2 | Khuôn `spec`, `plan`, `quick` & giới hạn dòng/mục lục | `doc_lint.py` (`81` file), `doc_index.py --tat-ca --kiem`, `pytest tests/test_spec_template.py tests/test_khao_sat_3_chieu.py tests/test_luat_skill.py` | `0` lỗi lint (`R14: 0`), `doc_index` exit `0`, `tdq-spec` `99<=100` dòng, `tdq-plan` `123<=132` dòng | PASS |
| Q3 | Prompt lõi & build `plugins/tdq-workflow-agy/` không đè `~/.gemini/` | `tools/build_agy_plugin.py`, `tools/install_agy_plugin.py --dry-run`, `agy plugin validate plugins/tdq-workflow-agy --strict --json`, `Get-Item ~/.gemini/...` | Build `OK` (`67` scripts, `79` skills, `84` AST py, `22` md); `findings: []`; `--dry-run` exit `0`; `~/.gemini` giữ `mtime 11/19/2026` | PASS |
| Q4 | Khóa ngân sách `<= 3500` token & i18n | `token_budget.py --kiem` + `.venv-tokens` chạy `test_token_budget_lock.py test_token_budget.py` | `66/66` file `<= 3500` tok (`spec-template=3372`, `plan-template=3472`, `report-template=3288`); `21/21` test tokenizer thật PASS (`0` skip) | PASS |
| Q5 | Trải nghiệm đọc 10–15 giây & mạch Trước → Sau → Kết quả | `pytest tests/test_user_facing_block.py tests/test_report_visual.py tests/test_spec_template.py tests/test_khao_sat_3_chieu.py tests/test_claude_md_core.py tests/test_agy_plugin_validate.py -q` | `79 passed, 192 subtests passed in 3.91s`; sạch cụm ép nén `"compress each item into ONE line"` | PASS |
| Q6 / QC-F1 | Toàn bộ bộ kiểm thử hồi quy (`222` module, `muc_qc=full`) | `py -3 -X utf8 scripts/tdq_test.py tron-bo --workers 1 --fresh --reuse off` + `tdq_test.py so` | `4602 passed, 36 skipped, 2892 subtests passed in 1327.59s`; `tron_bo=1/2`, `bo_sot=0` | PASS |
| QC-F2 | Hồi quy vùng chạm theo các dòng `Chạm:` trong plan | `pytest` `15` module chạm + `.venv-tokens` phủ nốt `5` test `@CAN_TOKENIZER` | `189 passed, 5 skipped` (`11.41s`) + `21/21` tokenizer PASS; không có node `KHÔNG CÓ TEST` | PASS |
| QC-F3 | Ràng buộc kiến trúc Spec §5 (`scripts/` không import `hooks/`, `qc.md` 1 bảng, `doc_lang=vi`) | Quét AST `scripts/*.py` + `pytest tests/test_kien_truc.py tests/test_muc_qc_qc_md.py tests/test_approve_do_truoc.py` | `AST_HOOKS_IMPORTS=[]`; `29 passed in 4.92s` | PASS |
| QC-F4 | Clean Code Self-check (`clean-code.md`) & `py_compile` | `py -3 -X utf8 -m py_compile ...` + rà `SRP / OCP / LSP / ISP / DIP` (`ruff` không cài → ghi `not checked yet`) | `py_compile` exit `0`; đạt cả `5/5` câu hỏi SOLID | PASS |

---

## Bằng chứng

### Q1 & Q5 — Văn phong tự nhiên, Ký tự & Bỏ ép nén dấu `·`

```text
py -3 -X utf8 scripts/scan_block_symbols.py --chi-khoi
Total: 5 distinct symbol(s) across 9 file(s) · 0 character(s) OUTSIDE the whitelist need a decision.
py -3 -X utf8 -m pytest tests/test_user_facing_block.py tests/test_report_visual.py tests/test_spec_template.py tests/test_khao_sat_3_chieu.py tests/test_claude_md_core.py tests/test_agy_plugin_validate.py -q
79 passed, 192 subtests passed in 3.91s
```

### Q2 & Q4 — Ngân sách Token, Mục lục & Bảng luật `luat-hien-co.md`

- Token khóa mới trong `docs/tdq/token-budget.json` (`<= 3500` tok):
  - `user-facing-block.md`: `2863` · `user-facing-block-vi-du.md`: `2089` · `report-template.md`: `3288`
  - `spec-template.md`: `3372` · `spec-template-huong-dan.md`: `3124` · `plan-template.md`: `3472`
  - `plan-template-huong-dan.md`: `1300` · `quick-lane-mini.md`: `1178`
- `doc_lint.py` quét `81` file (`docs/claude-md-mau.md`, `skills/`, `docs/tdq/brief|spec|plan`): `0 violation(s) total, exit 0`.
- `doc_index.py --tat-ca --kiem`: exit `0`; `luat-hien-co.md`: đồng bộ `30/30` dòng lệch giữ `100%` neo ký tự nguyên vẹn.
- Chạy test tokenizer thật qua `.venv-tokens`: `Ran 21 tests in 5.963s — OK` (`0` skipped).

### Q3 — Đồng bộ Prompt lõi & Build `plugins/tdq-workflow-agy/`

- `py -3 -X utf8 tools/build_agy_plugin.py`: `"status": "OK"`, `{"scripts": 67, "hooks": 14, "skills_files": 79, "agents": 8}`, `"ast_checked_py": 84`, `"md_checked_budget": 22`.
- `agy plugin validate plugins/tdq-workflow-agy --strict --json`: `"findings": []` (`agents: 8, hooks: 6, mcpServers: 3, rules: 10, skills: 12`).
- `py -3 -X utf8 tools/install_agy_plugin.py --dry-run`: exit `0`, `"dry_run": true`.
- Kiểm `C:\Users\admin\.gemini\config\plugins\tdq-workflow-agy\plugin.json`: `LastWriteTimeUtc = 11/19/2026 06:21:34` (giữ nguyên chưa ghi đè đúng chọn `3b`).

### Q6 / QC-F1 & QC-F2 — Trọn bộ `222` module & Vùng chạm

```text
py -3 -X utf8 scripts/tdq_test.py tron-bo --workers 1 --fresh --reuse off
[TDQ:TEST] PASS — scope=full backend=pytest tests=4638 skipped=36 in 1327.59s
4602 passed, 36 skipped, 2892 subtests passed in 1327.59s (0:22:07)
py -3 -X utf8 scripts/tdq_test.py so
request: 2026-11-21-0917-mac-dinh-trinh-bay-ngan (phase qc)
full-suite runs: 1 of budget 2 · radius misses: 0
```

### QC-F3 & QC-F4 — Ràng buộc kiến trúc & Clean Code Self-check

- **QC-F3:** `AST_HOOKS_IMPORTS= []`; `tests/test_kien_truc.py tests/test_muc_qc_qc_md.py tests/test_approve_do_truoc.py` → `29 passed in 4.92s`.
- **QC-F4 (`skills/tdq-conventions/references/clean-code.md`):**
  1. **SRP:** Đạt — `scripts/tdq_setup.py` giữ nguyên vai trò sinh khối ghim; `tools/patches/agy_manifests.py` giữ trách nhiệm sinh `AGENTS.md`; các hàm test mới tách riêng từng hợp đồng.
  2. **OCP:** Đạt — Mục `AGENTS.md` và `user-facing-block.md` thêm quy tắc dạng dòng/mục độc lập, không rẽ nhánh `if/elif` vào logic hiện có.
  3. **LSP:** Đạt — Không đổi chữ ký hay kiểu trả về của bất kỳ hàm công khai nào (`khoi_huong_dan()`, `generate_two_tier_rules()`).
  4. **ISP:** Đạt — Test mới đọc đúng tệp cần kiểm tra (`BLOCK`, `VI_DU`, `PATH_TEMPLATE`, `PLUGIN_DIR`), không kéo phụ thuộc thừa.
  5. **DIP:** Đạt — Các thay đổi đi qua điểm chuẩn chung (`token_budget.py`, `doc_index.py`, `tools/build_agy_plugin.py`, `tdq_state.py`), `py_compile` exit `0` (`ruff`: `not checked yet` do máy chưa cài `ruff`).

## Lệch spec chờ duyệt

không có (`py -3 -X utf8 scripts/tdq_state.py lech list` → `0 item(s), 0 pending`).
Ghi chú vận hành: ở pha `implement` có chèn 1 dòng `Soul:` vào đầu file `spec` để thỏa test `SoulRequestDangMo`; SHA-256 của file `spec` thay đổi so với lúc ký nên cần xác nhận lại cùng lượt chốt báo cáo.

## Kết luận

PASS toàn bộ (`Q1`–`Q6`, `QC-F1`–`QC-F4`)
