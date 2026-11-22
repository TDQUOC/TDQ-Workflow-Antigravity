# BÁO CÁO — Cập nhật hook cho phép thao tác git khi người dùng duyệt

Ngày: 2026-11-22 · Mã yêu cầu: 2026-11-22-0023-hook-duyet-thao-tac-git (20/20 task tick đủ)
Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

> **Tóm tắt dễ hiểu:** Trước khi sửa, bộ hook chặn cứng mọi lệnh đẩy mã và dọn kho dù người dùng đã đồng ý. Hệ thống cũng hay chặn nhầm lệnh thường có chuỗi giống lệnh git và làm kẹt bước tạo nhánh đầu quy trình. Nay bộ hook cấp vé một lượt khi có lời đồng ý trực tiếp từ người dùng ở phiên chính. Bộ phân tích cấu trúc lệnh khóa chặt vùng lưu vé và vẫn giữ nguyên lệnh cấm đẩy ép hay nhánh AI. Toàn bộ 4771 kiểm thử toàn kho cùng ba vòng rà soát bảo mật đã đạt trọn vẹn.

## 1. Trước request (trạng thái/flow)

Trước khi thay đổi, tầng hook Rust (`tdq-dispatch`) và Python (`hooks/scripts/`, `tools/patches/`) chặn vô điều kiện toàn bộ `git push`, `git reset --hard` và `git clean -f` mà không xét ngữ cảnh cho phép của người dùng:

- Người dùng đồng ý đẩy nhánh lên remote hay đặt lại kho trong chat vẫn bị cổng `TDQ:GIT` chặn ở `PreToolUse`.
- Bộ phân tích dò bằng chuỗi thô dễ chặn nhầm lệnh hợp lệ mang chuỗi `git push` trong tham số hoặc thông điệp commit, còn phản hồi `TDQ:GIT` gom chung nguyên nhân nên khó phân biệt lỗi thiếu duyệt hay lệnh cấm vĩnh viễn.
- Ở pha `analyze` khi vừa mở nhánh làm việc bằng `git switch -c <loại>/<mô-tả>` theo bước 3b, bộ hook chặn `TDQ:APPROVE` vì coi là sửa mã ngoài `docs/`.
- Thư mục `docs/tdq/.tdq-runtime/` chưa bị khóa ghi ở cổng sửa tệp và shell, tiềm ẩn rủi ro agent tự ghi tệp runtime.

## 2. Sau request (trạng thái/flow)

Luồng kiểm soát thao tác git mới đồng bộ 1-1 giữa Rust binary (`tdq-dispatch.exe`), Python hooks (`hooks/scripts/`) và bản patch Antigravity (`tools/patches/agy_hooks.py`):

- **Cơ chế vé một lượt (`git_grants`) có kiểm chứng chính chủ:** Tại `PreInvocation` (hỗ trợ Antigravity `transcriptPath`/`USER_INPUT` nguồn `USER_EXPLICIT` hoặc trống) và `UserPromptSubmit`, `extract_git_grants` phân tích câu lệnh người dùng, lọc bỏ phủ định, câu hỏi `?`, trích dẫn, thẻ hệ thống và thảo luận về spec/hook, chỉ cấp đúng các khóa cần thiết trong `{"push", "reset_hard", "clean_f"}` vào `docs/tdq/.tdq-runtime/turn-meta-<sid>.json` kèm ghi sổ `turns-<sid>.jsonl` và log timestamp `stderr` (`TDQ_LOG=0` tắt được).
- **Khóa single-turn, phân tách quyền và chống giả mạo:** Mọi `git push` thường, `git reset --hard`, `git clean -f` chỉ đi qua khi `turn_closed == false`, có đúng vé trong `git_grants`, không phải subagent (kể cả camelCase `agentId`/`agentType`), và không chạy trong lệnh ghép kèm phân đoạn chưa được duyệt; khi kết thúc lượt (`mark_turn_closed`) hoặc nhận tín hiệu `compact`/`resume`/`system`/replay chữ ký lượt đã đóng, vé bị xóa trắng fail-closed.
- **Bất biến cấm tuyệt đối giữ nguyên:** Mọi dạng force-push (`--force`, `-f`, `--force-with-lease`, `--force-if-includes`, refspec `+`), trailer `Co-Authored-By:` / `generated with ...` và nhánh/worktree tiền tố AI (`claude|antigravity|gemini|codex`) vẫn chặn cứng `TDQ:GIT` ở mọi lớp.
- **Khóa `.tdq-runtime/**`, chuẩn hóa parser và miễn trừ bước 3b:** Chặn `TDQ:STATE` trên cả tool sửa tệp (chuẩn hóa đường dẫn không phân biệt hoa thường trên Windows) lẫn shell khi tác động `docs/tdq/state.json`, `STATE.md` hoặc `.tdq-runtime/` (bao gồm redirect `1>`/`1>>`, `cd docs/tdq/.tdq-runtime`, PowerShell aliases, Python `shutil`/`os.replace`, bọc shell đệ quy tới độ sâu 4, vô hiệu hóa dấu nháy trong comment `#`/`<#...#>` và chặn thoát nháy/non-PS trên here-string). Cập nhật thẻ `GIT` giữ nguyên đúng 23 mã trong `gate_guidance.json`, đồng thời mở miễn trừ bước 3b cho `git switch -c` / `git checkout -b` đúng 5 tiền tố (`feature|bugfix|hotfix|chore|docs`) khi đang ở `analyze`/`idle`.
- **Đóng gói sạch trong repo (không chạm bản cài global):** Bản dựng mới nằm tại `plugins/tdq-workflow-agy/`. Sau khi nghiệm thu, bạn có thể đồng bộ ra thư mục plugin global bằng lệnh:
  `py -3 -X utf8 tools/build_agy_plugin.py --upstream . --output "$env:USERPROFILE\.gemini\config\plugins\tdq-workflow-agy"`

## 3. Đã test gì

- Chạy kiểm thử đơn vị Rust (`hooks/rust/tdq-dispatch/Cargo.toml`) trên `command_parser.rs`, `protocol.rs`, `storage.rs` và toàn bộ bộ sự kiện `events/*.rs`, phủ đủ cả 3 vòng vá bảo mật (`QC1`–`QC3`).
- Chạy đối chiếu parity 1-1 giữa Rust binary thật `tdq-dispatch.exe` và Python `dispatch.py` cùng 5 bộ test cổng hook/guidance: `tests/test_rust_dispatch_parity.py`, `tests/test_bash_gate.py`, `tests/test_agy_hooks.py`, `tests/test_hooks_dual_protocol.py`, `tests/test_gate_guidance.py` và `tests/test_agy_plugin_validate.py`.
- Chạy đơn độc (`SOLO`, không tiến trình song song) hai bộ runner chuẩn `scripts/tdq_test.py smoke-e2e --changed` và `scripts/tdq_test.py tron-bo` toàn bộ 229 module trong repo.
- Kiểm tra dựng release (`cargo build --release`), đóng gói plugin (`tools/build_agy_plugin.py --upstream .`), `agy plugin validate plugins/tdq-workflow-agy --strict --json`, `doc_lint.py`, `tdq_meta_gate.py`, delta `i18n_check.py` và `ruff check` so với `dev`, kiểm tra ranh giới không chạm `~/.gemini/` hay nhánh `main`, cùng 3 vòng tái kiểm tra bảo mật độc lập qua subagent `tdq-security-reviewer`.

## 4. Kết quả test

Toàn bộ `10/10` hạng mục QC (`Q1`–`Q6` và `QC-F1`–`QC-F4`) trong [phiếu QC](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/qc/2026-11-22-0023-hook-duyet-thao-tac-git.md) và `20/20` task trong [plan](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/plan/2026-11-22-0023-hook-duyet-thao-tac-git.md) đều hoàn tất và đạt `PASS`:

- **`Q1` (`cargo test`):** `38 passed, 0 failed` (`34` lib + `4` main, `0` warning).
- **`Q2` (`6` module pytest cốt lõi):** `173 passed, 84 subtests passed in 201.58s` (`0` fail; `gate_guidance` giữ đúng `23` mã).
- **`Q3` (`smoke-e2e --changed` & `tron-bo` SOLO):** `smoke-e2e` đạt `PASS` (`411 passed, 4360 deselected, 227 subtests passed in 291.14s`, `details_complete=True`); `tron-bo` đạt `PASS` (`4771` ca ở `229` module: `4735` pass, `36` skip, `0` fail trong `1425.56s`, `details_complete=True`, `tron_bo=2/2`, `bo_sot=0`).
- **`Q4` (Build & Package Plugin):** `cargo build --release` (`12.44s`, `0` warning), `tools/build_agy_plugin.py --upstream .` trả `"status": "OK"` (`ast_checked_py=85`, `md_checked_budget=22`), `tdq-dispatch.exe` `2.016.256` byte khớp `SHA256 cccde5a46d2e5e86`, `agy plugin validate --strict --json` trả `"findings": []`.
- **`Q5`–`Q6` (Security Audit 3 vòng, Lint, `i18n`, `ruff` & Clean Code):** `tdq-security-reviewer` chuyển từ vòng 1 `FAIL (2C/1H/1M/1L)` → vòng 2 `FAIL (3C/1H/0M/3L)` → vòng 2 re-check `FAIL (0C/1H/0M/1L)` → vòng 3 `PASS (0 CRITICAL, 0 HIGH, 0 MEDIUM, 0 LOW)` trên commit `f1e7fcfb`; `Auto Meta-Gate` `PASS (2/2, 0.07s)`; delta `i18n_check.py = +0` và `ruff = +0` trên toàn bộ 9 tệp Python chạm so với `dev`; `doc_lint.py --pair` `0` lỗi; `TDQ_LOG=1/0` đạt chuẩn; `SCRIPTS_IMPORT_HOOKS: []`, `AI_TRAILERS: False`, `~/.gemini` giữ nguyên `0.103.1`, nhánh `main` giữ nguyên `91db3046...`.

## Đầu ra

- **Đầu ra mã nguồn & cấu hình:** `hooks/rust/tdq-dispatch/src/{command_parser.rs,protocol.rs,storage.rs,events/*.rs}`, `hooks/scripts/{prompt_context.py,bash_gate.py,edit_gate.py,agy_pretooluse_gate.py}`, `tools/patches/{agy_hooks.py,gate_guidance.json}`, `tests/{test_rust_dispatch_parity.py,test_bash_gate.py,test_agy_hooks.py,test_gate_guidance.py}`, bản dựng đồng bộ tại `plugins/tdq-workflow-agy/`.
- **Tài liệu & kiểm chứng:** [spec](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/spec/2026-11-22-0023-hook-duyet-thao-tac-git.md), [plan](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/plan/2026-11-22-0023-hook-duyet-thao-tac-git.md), [phiếu QC](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/qc/2026-11-22-0023-hook-duyet-thao-tac-git.md), báo cáo này và **Archify HTML:** `docs/tdq/reports/2026-11-22-0023-hook-duyet-thao-tac-git.html`.
- **Giới hạn:** Plugin cài sẵn tại `~/.gemini/config/plugins/tdq-workflow-agy/` giữ nguyên bản `0.103.1` ngoài workspace theo yêu cầu; `eval` opt-in giữ tắt; nợ `i18n_check` tồn đọng trên nhánh `dev` trước request không nằm trong phạm vi sửa (`delta = +0`). Archify master tổng (`docs/architecture/status.json`) đang `stale` trước khi đồng bộ nhánh, còn bản báo cáo riêng của request được render và verify trực tiếp theo `evidence_kind=working-tree`.
- **Lệch spec chờ duyệt:** không có
- **Git:** Nhánh `feature/hook-duyet-thao-tac-git` (tách từ `dev`) đã checkpoint mã nguồn đến commit `f1e7fcfb`; phần hồ sơ `qc`, báo cáo, Archify HTML và sổ log cuối đang chờ bạn xác nhận để commit và gộp về nhánh `dev` (chưa thực hiện `git push`).

## Thời gian

```text
Request `2026-11-22-0023-hook-duyet-thao-tac-git` · lane full · opened at 2026-11-22T00:30:08+07:00

| Phase | Wall clock | Times entered |
|---|---|---|
| idle | 2 min | 1 |
| analyze | 12 min | 1 |
| spec | 7 min | 1 |
| plan | 12 min | 1 |
| implement | 1h 06min | 1 |
| qc | 1h 58min | 1 |
| report | 20 min | 1 |
| Total | 3h 57min |  |

Model compute time is unavailable (`model_giay=null`). API includes network/provider latency; tool time is host wait. Observed metrics may overlap; unattributed time is not assumed user/model time.
Transcript attribution: project_window. Complete covers selected supported observations only.
Host metrics unavailable (5 hidden: api_request_seconds, tool_call_seconds, background_job_seconds, observed_union_seconds, unattributed_seconds): no_usable_source, no_usable_observations, wall_minus_observed_union;no_usable_observations

## Agent Role Telemetry

| Role | Runs | First pass | Rate | Retries | Avg elapsed | Models |
|---|---|---|---|---|---|---|
| self | 7 | 7 | 100% | 0 | — | — |
| tdq-qc-tester | 6 | 6 | 100% | 0 | — | — |
| tdq-implementer | 2 | 2 | 100% | 0 | — | — |
```

## Thân PR (soạn sẵn)

**Tóm tắt:** Nâng cấp đồng bộ hook Rust (`tdq-dispatch`) và Python (`hooks/scripts/`, `tools/patches/`) để cho phép chạy `git push` thường, `git reset --hard` và `git clean -f` bằng cơ chế vé một lượt (`git_grants`) khi được người dùng duyệt trực tiếp trong lượt hiện tại, đồng thời khóa `docs/tdq/.tdq-runtime/**`, chuẩn hóa phân tích token/comment shell và mở miễn trừ bước 3b tại `analyze`/`idle` trong khi giữ nguyên 100% lệnh cấm force-push, `Co-Authored-By:` và tiền tố nhánh AI.

**Trước/Sau:** Xem sơ đồ luồng Trước/Sau ở `docs/tdq/spec/2026-11-22-0023-hook-duyet-thao-tac-git-preview.html` và báo cáo trực quan tại `docs/tdq/reports/2026-11-22-0023-hook-duyet-thao-tac-git.html`.

**Đã kiểm:**
- `rtk bypass cargo test --manifest-path hooks/rust/tdq-dispatch/Cargo.toml` → `38 passed, 0 failed` (`34` lib + `4` main)
- `rtk bypass py -3 -X utf8 -m pytest tests/test_rust_dispatch_parity.py tests/test_bash_gate.py tests/test_agy_hooks.py tests/test_hooks_dual_protocol.py tests/test_gate_guidance.py tests/test_agy_plugin_validate.py -q` → `173 passed, 84 subtests passed in 201.58s`
- `rtk bypass py -3 -X utf8 scripts/tdq_test.py smoke-e2e --changed` (SOLO) → `PASS` (`411 passed, 0 failed in 291.14s`, `details_complete=True`)
- `rtk bypass py -3 -X utf8 scripts/tdq_test.py tron-bo` (SOLO) → `PASS` (`4771` ca ở `229` module: `4735` pass, `36` skip, `0` fail trong `1425.56s`)
- `agy plugin validate plugins/tdq-workflow-agy --strict --json` → `"findings": []` (SHA256 `tdq-dispatch.exe`: `cccde5a46d2e5e86`)
- `tdq-security-reviewer` vòng 3 trên `f1e7fcfb` → `PASS (0 CRITICAL, 0 HIGH, 0 MEDIUM, 0 LOW)`

**Rủi ro hồi quy:** Chạm sâu vào bộ phân tích lệnh shell/PowerShell và vòng đời vé `turn-meta-<sid>.json` trên cả Rust lẫn Python; đã khóa bằng bộ parity hai động cơ (`173` ca pytest + `38` test Rust) và xác nhận miễn nhiễu từ comment `#`/`<#...#>`, quote here-string, `1>` redirect và replay chữ ký lượt đã đóng.
<!-- tdq-archify-binding:start -->
<!-- manifest: 2026-11-22-0023-hook-duyet-thao-tac-git.manifest.json -->
<!-- manifest_digest: 62169d1948ebf1e11ae8d9a497b4522a79e31013d7a501f7cca3ea473d0f5b22 -->
<!-- tdq-archify-binding:end -->