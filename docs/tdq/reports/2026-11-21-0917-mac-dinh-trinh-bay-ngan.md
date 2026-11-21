# REPORT — Mặc định Trình bày Report, Spec & Plan Ngắn gọn, Tự nhiên, Dễ hiểu (`2026-11-21-0917-mac-dinh-trinh-bay-ngan` · lane full · mode main · 7/7 task tick đủ)

Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

> **Tóm tắt nhanh:** Trước đây các bản `spec`, `plan` và `report` thường dồn nhiều ý bằng dấu `·` và mở đầu thẳng bằng bảng thông số, khiến người đọc khó nắm nhanh và hay phải nhắn thêm một lượt nhờ tóm tắt dễ hiểu hơn. Sau nâng cấp này, mọi bản trình bày trong chat và phần đầu file `.md` mặc định kể ngắn gọn theo mạch "Trước đây → Sau khi làm xong → Kết quả" trong 10–15 giây đọc (như ảnh mẫu `1.jpg`), giữ nguyên bảng kiểm bên dưới dưới trần `3.500` token và đã build sạch vào gói plugin trong repo.

**Trước request (trạng thái/flow):** Quy chuẩn `user-facing-block.md` mới chỉ khóa phần cú pháp kỹ thuật (6 phần, 8 luật trang trí, 6 ký tự) mà chưa định nghĩa văn phong kể chuyện; tệ hơn, `report-template.md` tại dòng 101 và 110–115 còn ép gộp mỗi mục thành một dòng nối bằng `·`, còn đầu `spec`, `plan` và `quick-lane-mini` vào thẳng nhãn kỹ thuật trong khi `spec-template.md` (`3.458/3.500` tok) và `plan-template.md` (`3.420/3.500` tok) gần chạm trần ngân sách.

**Sau request (trạng thái/flow):** Áp dụng thiết kế 2 lớp — tầng kể chuyện dễ hiểu ở mặt tiền, tầng bảng & neo máy kiểm giữ nguyên ở phía dưới:
- **Chuẩn văn phong tự nhiên (`tdq-conventions`):** Bổ sung `Plain-Language Narrative Rule` trong `user-facing-block.md` (`2.863` tok) yêu cầu viết cho mọi người hiểu trong 10–15 giây theo mạch `Trước → Sau → Kết quả`, lồng số liệu gọn vào câu và đẩy đường dẫn dài về link; thêm ví dụ đối chiếu phong cách `1.jpg` tại `user-facing-block-vi-du.md` (`2.089` tok).
- **Bỏ ép nén `·` trong `report` (`tdq-build`):** Gỡ câu `"compress each item into ONE line, separating ideas with ·"` khỏi `report-template.md` (`3.288` tok), thêm ô `> **Tóm tắt nhanh:**` và viết lại khung chat hỏi commit thoáng mắt theo đúng bố cục ảnh `1.jpg` (giữ nguyên 4 đề mục bắt buộc để `tdq_state.py` và bộ test kiểm bình thường).
- **Nâng cấp `spec`, `plan`, `quick` dưới trần `3.500` token:** Chèn ô `> **Tóm tắt dễ hiểu:**` ở đầu `spec-template.md` (`3.372` tok), `plan-template.md` (`3.472` tok) và `quick-lane-mini.md` (`1.178` tok); đưa phần hướng dẫn dài sang `spec-template-huong-dan.md` (`3.124` tok) và `plan-template-huong-dan.md` (`1.300` tok); viết lại khung chat trình `spec` và `plan` tự nhiên hơn (giữ nguyên `99 <= 100` dòng và `123 <= 132` dòng).
- **Đồng bộ prompt lõi & build plugin repo (`3b`):** Cập nhật `scripts/tdq_setup.py`, `docs/claude-md-mau.md` (`R5` sạch, `< 12.500` byte) và `tools/patches/agy_manifests.py`; chạy `doc_index.py --tat-ca`, khóa `token-budget.json` (`66/66` file `<= 3.500` tok), đồng bộ `30/30` dòng bảng `luat-hien-co.md`, và build mới `plugins/tdq-workflow-agy/` (không cài đè ra `~/.gemini/`).

**Đã test gì:** Viết test khóa trước khi sửa (Red → Green) cho 6 module kiểm thử khối chat, khuôn report, khuôn spec, 3 chiều, prompt lõi và plugin AGY; chạy `scan_block_symbols.py --chi-khoi`, `doc_lint.py` trên `81` file, `doc_index.py --tat-ca --kiem`, `token_budget.py --kiem` cùng `21` test tokenizer thật qua `.venv-tokens`, `tools/build_agy_plugin.py`, `tools/install_agy_plugin.py --dry-run`, `agy plugin validate plugins/tdq-workflow-agy --strict --json`, `py_compile`, quét AST `scripts/`, `189` test vùng chạm và chạy trọn bộ `py -3 -X utf8 scripts/tdq_test.py tron-bo --workers 1 --fresh --reuse off` trên toàn bộ `222` module.

**Kết quả test:**
- Trọn bộ `scripts/tdq_test.py tron-bo`: **PASS** `4.602 passed, 36 skipped, 2.892 subtests passed in 1327.59s` (`0` failed, `4.638` collected, `bo_sot = 0`, `tron_bo = 1/2`).
- Bộ test khóa văn phong, khuôn & plugin (`79` ca chọn lọc): `79 passed, 192 subtests passed in 3.91s`; vùng chạm mở rộng `189 passed, 5 skipped in 11.41s` và chạy `.venv-tokens` phủ đủ `21/21` test tokenizer (`0` skipped); `29 passed in 4.92s` nhóm kiến trúc (`AST_HOOKS_IMPORTS = []`).
- `scan_block_symbols.py --chi-khoi`: `5` ký tự whitelist, `0` ký tự lạ; `doc_lint.py`: `0` lỗi trên `81` file; `token_budget.py --kiem`: `66/66` file `<= 3.500` token; `agy plugin validate --strict`: `findings: []` (`agents: 8, hooks: 6, mcpServers: 3, rules: 10, skills: 12`); `--dry-run`: exit `0`.

**Đầu ra:**
- Quy chuẩn & khuôn mẫu: [user-facing-block.md](../../../skills/tdq-conventions/references/user-facing-block.md), [user-facing-block-vi-du.md](../../../skills/tdq-conventions/references/user-facing-block-vi-du.md), [report-template.md](../../../skills/tdq-build/references/report-template.md), [spec/SKILL.md](../../../skills/tdq-spec/SKILL.md), [spec-template.md](../../../skills/tdq-spec/references/spec-template.md), [spec-template-huong-dan.md](../../../skills/tdq-spec/references/spec-template-huong-dan.md), [plan/SKILL.md](../../../skills/tdq-plan/SKILL.md), [plan-template.md](../../../skills/tdq-plan/references/plan-template.md), [plan-template-huong-dan.md](../../../skills/tdq-plan/references/plan-template-huong-dan.md), [quick-lane-mini.md](../../../skills/tdq-intake/references/quick-lane-mini.md).
- Prompt, khóa & đóng gói repo: [tdq_setup.py](../../../scripts/tdq_setup.py), [claude-md-mau.md](../../../docs/claude-md-mau.md), [agy_manifests.py](../../../tools/patches/agy_manifests.py), [token-budget.json](../token-budget.json), [luat-hien-co.md](../audit/luat-hien-co.md), gói build [plugins/tdq-workflow-agy](../../../plugins/tdq-workflow-agy/manifest.json), và bộ test tại [tests/test_user_facing_block.py](../../../tests/test_user_facing_block.py), [test_report_visual.py](../../../tests/test_report_visual.py), [test_spec_template.py](../../../tests/test_spec_template.py), [test_khao_sat_3_chieu.py](../../../tests/test_khao_sat_3_chieu.py), [test_claude_md_core.py](../../../tests/test_claude_md_core.py), [test_agy_plugin_validate.py](../../../tests/test_agy_plugin_validate.py).

**Archify HTML:**
- Báo cáo trực quan: [2026-11-21-0917-mac-dinh-trinh-bay-ngan.html](2026-11-21-0917-mac-dinh-trinh-bay-ngan.html)
- Tailscale Serve URL: https://unity-pc-rtx3060.tail99896.ts.net/vlog/tdq-workflow-agy/reports/2026-11-21-0917-mac-dinh-trinh-bay-ngan.html
- Biểu đồ nguồn: [bao-cao.archify.md](../artifacts/2026-11-21-0917-mac-dinh-trinh-bay-ngan/bao-cao.archify.md)

**Giới hạn:**
- **Phạm vi đóng gói (`3b`):** Mới build mới vào `plugins/tdq-workflow-agy/` trong repo và kiểm `--dry-run`; bản live `C:\Users\admin\.gemini\config\plugins\tdq-workflow-agy` vẫn giữ nguyên mốc `11/19/2026` theo chọn `3b`.
- **Lint style Python:** Máy chưa cài `ruff` nên kết quả `ruff check` là `not checked yet`; toàn bộ file Python sửa đã qua `py_compile` và `ast.parse`.
- **Bổ sung dòng `Soul:` ở Spec:** Trong lúc chạy test `test_soul_rules.py`, có thêm `1` dòng `Soul:` vào đầu file `spec` nên SHA-256 của file `spec` thay đổi so với lần duyệt đầu (nội dung đặc tả giữ nguyên 100%).

**Lệch spec chờ duyệt:** không có

**Git:** Nhánh làm việc `feature/mac-dinh-trinh-bay-ngan` (nhánh gốc `dev`), chưa commit, chưa merge.

## Thời gian

Request `2026-11-21-0917-mac-dinh-trinh-bay-ngan` · lane full · opened at 2026-11-21T09:21:50+07:00

| Phase | Wall clock | API request | Tool wait | Background job | Observed union | Unattributed | Times entered |
|---|---|---|---|---|---|---|---|
| idle | 0s | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | 1 |
| analyze | 7 min | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | 1 |
| spec | 10 min | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | 1 |
| plan | 4 min | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | 1 |
| mode | 57s | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | 1 |
| implement | 13 min | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | 1 |
| qc | 27 min | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | 1 |
| report | 0s | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | 1 |
| Total | 1h 02min | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] |  |

Model compute time is unavailable (`model_giay=null`). API includes network/provider latency; tool time is host wait. Observed metrics may overlap; unattributed time is not assumed user/model time.
Transcript attribution: project_window. Complete covers selected supported observations only.
- api_request_seconds: no_usable_source
- tool_call_seconds: no_usable_source
- background_job_seconds: no_usable_source
- observed_union_seconds: no_usable_observations
- unattributed_seconds: wall_minus_observed_union;no_usable_observations

## Agent Role Telemetry

| Role | Runs | First pass | Rate | Retries | Avg elapsed | Models |
|---|---|---|---|---|---|---|
| self | 7 | 7 | 100% | 0 | — | — |
| tdq-qc-tester | 6 | 6 | 100% | 0 | — | — |
| tdq-implementer | 2 | 2 | 100% | 0 | — | — |

## Thân PR (soạn sẵn)

```markdown
## Summary
- Make plain-language storytelling (`Trước → Sau → Kết quả`, 10–15s readability, inspired by user sample `1.jpg`) the default across `spec`, `plan`, `report`, and `quick-lane-mini` in TDQ Workflow.
- Remove `"compress each item into ONE line, separating ideas with ·"` from `report-template.md`, add top executive summaries (`> **Tóm tắt dễ hiểu:**` / `> **Tóm tắt nhanh:**`) to templates without breaching the 3,500-token cap, and update chat presentation blocks across skills and prompt templates.
- Relock `docs/tdq/token-budget.json`, align `docs/tdq/audit/luat-hien-co.md`, add regression tests, and rebuild `plugins/tdq-workflow-agy/` in-repo without overwriting live `~/.gemini/`.

## Test plan
- [x] `py -3 -X utf8 scripts/tdq_test.py tron-bo --workers 1 --fresh --reuse off` → `4,602 passed, 36 skipped, 2,892 subtests passed` (`0` failed, `bo_sot=0`)
- [x] `py -3 -X utf8 -m pytest tests/test_user_facing_block.py tests/test_report_visual.py tests/test_spec_template.py tests/test_khao_sat_3_chieu.py tests/test_claude_md_core.py tests/test_agy_plugin_validate.py -q` → `79 passed, 192 subtests passed`
- [x] `py -3 -X utf8 scripts/doc_lint.py` (`81` files, `0` violations), `token_budget.py --kiem` (`66/66 <= 3500`), `agy plugin validate plugins/tdq-workflow-agy --strict --json` (`findings: []`)
```
<!-- tdq-archify-binding:start -->
<!-- manifest: 2026-11-21-0917-mac-dinh-trinh-bay-ngan.manifest.json -->
<!-- manifest_digest: 411480db75c412ac47438e78a0175e895fe493d38070b905bf6371006caa9f28 -->
<!-- tdq-archify-binding:end -->