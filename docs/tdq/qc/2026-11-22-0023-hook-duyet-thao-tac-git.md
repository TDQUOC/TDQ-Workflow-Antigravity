# QC — Cập nhật hook cho phép thao tác git khi người dùng duyệt

Ngày: 2026-11-22 · Plan: [2026-11-22-0023-hook-duyet-thao-tac-git.md](../plan/2026-11-22-0023-hook-duyet-thao-tac-git.md) (Vòng 3)
Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

> **Tóm tắt dễ hiểu:** Bộ hook Rust và Python đã vượt qua trọn vẹn ba vòng rà soát bảo mật và toàn bộ bộ kiểm thử tự động của kho mã nguồn. Lệnh git đẩy nhánh, reset cứng hoặc dọn tệp thông thường chỉ chạy được khi có tin nhắn đồng ý trực tiếp từ người dùng trong đúng lượt hiện tại và thuộc phiên làm việc chính. Mọi chiêu lách qua ngoặc kép, chú thích PowerShell, chuyển hướng fd hay replay lượt cũ đều bị chặn đứng mà không chạm vào plugin cài sẵn trên máy.

## Dev Behavior QC Card

- **Auto Meta-Gate:** `PASS (2/2 checks, 0.07s)` khi kiểm tra các tài liệu và bài test mới (`--files docs/tdq/brief/2026-11-22-0023-hook-duyet-thao-tac-git.md docs/tdq/spec/2026-11-22-0023-hook-duyet-thao-tac-git.md docs/tdq/plan/2026-11-22-0023-hook-duyet-thao-tac-git.md tests/test_rust_dispatch_parity.py`); riêng delta `i18n_check.py` trên toàn bộ 9 tệp Python đã sửa so với nhánh `dev` đạt `+0` (`0` dòng mới phát sinh ngoài phần có sẵn từ nền `dev`).
- **Luồng đổi:** Hoàn tất cả 7 task kế hoạch gốc (`T1.1`–`T4.2`) cùng 3 vòng vá bảo mật (`QC1.1`–`QC1.5`, `QC2.1`–`QC2.4`, `QC3.1`–`QC3.4`) trên nhánh `feature/hook-duyet-thao-tac-git` (HEAD `f1e7fcfb`): trích xuất vé `git_grants` theo từng loại ở `PreInvocation`/`UserPromptSubmit`, lưu khóa `single-turn` trong `turn-meta-<sid>.json`, chặn ghi trực tiếp `.tdq-runtime/**`, chuẩn hóa phân tích token shell xuyên qua comment `#`/`<#...#>`, here-string và redirect fd, miễn trừ tạo nhánh Step 3b ở pha `analyze`/`idle`, cập nhật thẻ `GIT` (giữ đúng 23 mã) và đóng gói lại `plugins/tdq-workflow-agy/`.
- **Chạy thử thật (Before → After + Bằng chứng tươi):** `cargo test` (`38 passed, 0 failed`: 34 lib + 4 main, `0` warning); 6 module pytest cốt lõi parity & hook (`173 passed, 84 subtests passed in 201.58s`); `tdq_test.py smoke-e2e --changed` chạy SOLO (`411 passed, 4360 deselected, 227 subtests passed in 291.14s`, `details_complete=True`); `tdq_test.py tron-bo` chạy SOLO (`tests=4771`, `skipped=36`, `0 failed` trên `229` module trong `1425.56s`, `details_complete=True`, `tron_bo=2/2`, `bo_sot=0`); `tools/build_agy_plugin.py --upstream .` (`status=OK`, `ast_checked_py=85`, `SHA256` binary khớp `cccde5a46d2e5e86`); `agy plugin validate plugins/tdq-workflow-agy --strict --json` (`"findings": []`); tái kiểm tra độc lập vòng 3 của `tdq-security-reviewer` (`Verdict: PASS`, `0 CRITICAL, 0 HIGH, 0 MEDIUM, 0 LOW`).
- **Rủi ro còn lại:** Phiên bản cài sẵn trên máy tại `~/.gemini/config/plugins/tdq-workflow-agy/` vẫn là `0.103.1` theo đúng ranh giới phạm vi §5; người dùng cần đồng bộ thủ công sau khi kiểm tra báo cáo cuối nếu muốn kích hoạt ngay ở cấp global.

## Bảng tổng hợp `Q1`–`Q6` và `QC-F1`–`QC-F4`

| # | Hạng mục | Lệnh đã chạy | Kết quả | PASS/FAIL |
|---|---|---|---|---|
| Q1 | Kiểm thử Rust `tdq-dispatch` | `rtk bypass cargo test --manifest-path hooks/rust/tdq-dispatch/Cargo.toml` | `38 passed, 0 failed` (`34` lib + `4` bin, `0` warning), gồm test vé single-turn, khóa `.tdq-runtime/`, bước 3b, comment & PS here-string | PASS |
| Q2 | Parity Rust ↔ Python & 6 module hook | `rtk bypass py -3 -X utf8 -m pytest tests/test_rust_dispatch_parity.py tests/test_bash_gate.py tests/test_agy_hooks.py tests/test_hooks_dual_protocol.py tests/test_gate_guidance.py tests/test_agy_plugin_validate.py -q` | `173 passed, 84 subtests passed in 201.58s`, `0` fail; `gate_guidance` giữ đúng `23` mã | PASS |
| Q3 | Trọn bộ hồi quy Python (`tron-bo`) | `rtk bypass py -3 -X utf8 scripts/tdq_test.py tron-bo` (SOLO) + `tdq_test.py so` | `PASS` (`4771` ca ở `229` module: `4735` pass, `36` skip, `0` fail, `1425.56s`, `details_complete=True`); `tron_bo=2/2`, `bo_sot=0` | PASS |
| Q4 | Build release & đóng gói plugin `agy` | `cargo build --release` + `tools/build_agy_plugin.py --upstream .` + `agy plugin validate plugins/tdq-workflow-agy --strict --json` | `status=OK` (`ast_checked_py=85`), `tdq-dispatch.exe` `2.016.256` byte khớp `SHA256 cccde5a46d2e5e86`, strict validate `0 findings` | PASS |
| Q5 | Ràng buộc kiến trúc, `i18n_check` & `doc_lint` | `i18n_check.py --json` delta vs `dev` + `doc_lint.py --pair` + `lech list` + kiểm tra ranh giới | `i18n_check` delta `+0` trên 9 file sửa; `doc_lint --pair` & `brief` `0` lỗi; `lech list` `0`; `~/.gemini` (`0.103.1`) & `main` (`91db3046...`) nguyên vẹn | PASS |
| Q6 | Clean Code, `ruff`, `TDQ_LOG=0/1` & Security Audit | `py -3 -m ruff check` delta vs `dev` + AST line check + test `TDQ_LOG=1/0` + `tdq-security-reviewer` vòng 3 | `ruff` delta `+0`; mọi hàm mới/sửa `<= 50` dòng; `TDQ_LOG=1/0` đạt ở cả Rust và Python; Security Audit vòng 3: `PASS` (`0C/0H/0M/0L`) | PASS |
| QC-F1 | `Meta-Gate`, `smoke-e2e --changed`, `tron-bo` | `tdq_meta_gate.py --files ...` + `smoke-e2e --changed` (SOLO) + `tron-bo` (SOLO) | Meta-Gate `PASS (2/2, 0.07s)`; `smoke-e2e` `411 passed, 0 failed` (`291.14s`); `tron-bo` `PASS` (`4771` ca, `0` fail) | PASS |
| QC-F2 | Hồi quy toàn vùng chạm theo `Chạm:` | Kết hợp kết quả trực tiếp 6 module cốt lõi (`Q2`), `cargo test` (`Q1`) và `tron-bo` (`Q3`) | Mọi node tại `hooks/rust/`, `hooks/scripts/`, `tools/patches/`, `plugins/tdq-workflow-agy/` đều có test chạy xanh `0` fail | PASS |
| QC-F3 | Ràng buộc kiến trúc spec §5 & Git | Kiểm tra AST cross-import `scripts/` → `hooks/`, `git log -n 12`, `~/.gemini/`, `main` | `SCRIPTS_IMPORT_HOOKS: []`; `AI_TRAILERS: False` (`0` trailer Co-Authored-By); `~/.gemini` & `main` không đổi | PASS |
| QC-F4 | Clean Code (hàm gọn, fail-closed, không stub) | AST length check + rà `TODO`/placeholder trên `git diff dev...HEAD` | Mọi hàm mới/sửa `<= 50` dòng; fail-closed khi JSON hỏng hoặc turn đóng; không trùng lặp logic giữa Rust và Python | PASS |

## Bằng chứng

### `Q1`, `Q2`, `Q4` — Kết quả test sau vòng vá bảo mật 3 (`f1e7fcfb`)

```text
rtk bypass py -3 -X utf8 -m pytest tests/test_rust_dispatch_parity.py tests/test_bash_gate.py tests/test_agy_hooks.py tests/test_hooks_dual_protocol.py tests/test_gate_guidance.py tests/test_agy_plugin_validate.py -q
→ 173 passed, 84 subtests passed in 201.58s (0:03:21) · exit 0

rtk bypass cargo test --manifest-path hooks/rust/tdq-dispatch/Cargo.toml
→ test result: ok. 34 passed; 0 failed (lib) + 4 passed; 0 failed (main) = 38 passed, 0 failed

tools/build_agy_plugin.py --upstream .
→ "status": "OK", "ast_checked_py": 85, "md_checked_budget": 22
agy plugin validate plugins/tdq-workflow-agy --strict --json
→ "findings": [], exit 0 · EXE: 2016256 bytes · SHA_MATCH: True cccde5a46d2e5e86
```

### `Q3`, `QC-F1` — Chạy SOLO `smoke-e2e --changed` và `tron-bo`

```text
rtk bypass py -3 -X utf8 scripts/tdq_test.py smoke-e2e --changed
→ [TDQ:TEST] PASS — scope=smoke-e2e backend=pytest tests=411 skipped=0 in 291.14s (411 passed, 4360 deselected, 227 subtests passed, details_complete=True)

rtk bypass py -3 -X utf8 scripts/tdq_test.py tron-bo
→ [TDQ:TEST] PASS — scope=full backend=pytest tests=4771 skipped=36 in 1425.56s (229 modules, details_complete=True, 0 failed) · 707de1733946435eac6667c950a845ea/result.json

py -3 -X utf8 scripts/tdq_test.py so
→ tron_bo=2 · bo_sot=0 · budget=2
```

### `Q5`, `Q6` — Tái kiểm tra bảo mật 3 vòng, `i18n_check`, `ruff` và ranh giới

```text
tdq-security-reviewer tiến trình 3 vòng:
- Vòng 1 (14f5463d): FAIL (2C/1H/1M/1L) → mở QC1.1-QC1.5 (vá parser, stale-sig, camelCase, Windows normcase)
- Vòng 2 (db14027c): FAIL (3C/1H/0M/3L) → mở QC2.1-QC2.4 (vá 1> redirect, cd .tdq-runtime, empty herestring, PS-ctx, -B/-C, agentId)
- Vòng 2 re-check (f90935c6): FAIL (0C/1H/0M/1L) → mở QC3.1-QC3.4 (vá comment #/<#...#> và --git-dir regex)
- Vòng 3 (7598c9dc trên f1e7fcfb): Verdict PASS · Counts: 0 CRITICAL, 0 HIGH, 0 MEDIUM, 0 LOW

Delta vs dev (9 file Python chạm): I18N_NEW: 0 · RUFF_DELTA: 0 · SCRIPTS_IMPORT_HOOKS: [] · HOST: 0.103.1 · MAIN: 91db304635f142b457284d55accf82c28a813239
```

## Lệch spec chờ duyệt

không có

## Kết luận

PASS toàn bộ (`10/10` hạng mục `Q1`–`Q6` & `QC-F1`–`QC-F4` đạt `PASS`, `tdq-security-reviewer` vòng 3 đạt `0` lỗi ở mọi mức). Sẵn sàng chuyển sang pha `report`.
