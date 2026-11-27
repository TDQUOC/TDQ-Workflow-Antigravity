# QC — Nâng phiên bản 0.108.0, phát hành đa nhánh, commit và push

> **Tóm tắt dễ hiểu:** Toàn bộ bốn tiêu chí hoàn thành và bốn vòng kiểm tra mức đầy đủ đều đạt sạch không lỗi. Phiên bản 0.108.0 đã đồng bộ từ mã gốc Rust tới gói Antigravity, cài đặt xong lên máy, vượt qua trọn bộ 5049 bài kiểm thử và khớp mã commit trên cả bốn nhánh, nhãn tại kho GitHub origin.

## Dev Behavior QC Card
- Auto Meta-Gate: PASS (2/2 checks, 0.21s)
- Luồng đổi: Từ nền `dev@42467fe9` mang nhãn `0.107.0` (`Cargo.toml` `0.105.0`), đồng bộ thành `0.108.0` xuyên suốt đa host + Rust Windows + gói AGY + tài liệu + Master Map (`current`), hợp nhất `dev`, sinh `main` và `release/antigravity`, gắn tag `v0.108.0`, đẩy đủ lên `origin` và cài bản `0.108.0` vào `~/.gemini/config/plugins/tdq-workflow-agy`.
- Chạy thử thật (Before → After + Bằng chứng tươi): `cargo test` `43/43` passed, `run_full_verification.py` `24/24` (`0` AGY findings), `smoke-e2e --changed` `418` passed (`239` subtests), `tron-bo --workers auto --fresh --reuse off` `5049` collected (`5012` passed, `37` platform-skipped, `0` failed), `git ls-remote origin` khớp SHA `dev` (`89e9f159`), `main` (`bb9af8e6`), `release/antigravity` (`b2c0183b`) và tag `v0.108.0` (`317e8bcf` → `bb9af8e6`).
- Rủi ro còn lại: Sau khi chốt `report` và đóng `idle` sẽ tạo thêm commit tài liệu báo cáo trên `dev` và đẩy `origin dev` (hai nhánh sạch `main` và `release/antigravity` giữ nguyên vì lọc bỏ `docs/`).

| # | Hạng mục | Lệnh đã chạy | Kết quả | PASS/FAIL |
|---|---|---|---|---|
| Q1 | Đồng bộ 0.108.0 đa host, `Cargo.toml`, `CHANGELOG.md <= 500` dòng và `doc_lint` | `py -3 -X utf8 -c "..." && py -3 -X utf8 scripts/doc_lint.py CHANGELOG.md README.md README-Antigravity.md` | Root + `.codex-plugin` + `.tdq-phat-hanh` + `Cargo.toml` = `0.108.0`; `CHANGELOG.md` `425 <= 500` dòng; `doc_lint` `0 violation(s)` | PASS |
| Q2 | Rust Windows + gói AGY (`0` findings) + cài cục bộ `~/.gemini/` (`0.108.0`) | `cargo test` + `cargo build --release` + `py -3 -X utf8 tools/run_full_verification.py` + kiểm `plugin.json` local | Cargo `43 passed`; `run_full_verification.py` `24/24` passed, `agy_validate_findings=0`; `~/.gemini/.../plugin.json` = `0.108.0` (`281` file, `TDQ_LOG=1/0` đạt) | PASS |
| Q3 | `README.md` (`0.108.0` + `5012 passed`) và Master Map `docs/architecture/` `current` | Kiểm chuỗi `README.md` + `py -3 -X utf8 scripts/tdq_archify.py status` | `version-0.108.0` & `tests-5012%20passed` hiện diện; `status=current`, `reasons=[]` | PASS |
| Q4 | Kiểm thử full (`tron-bo` + `smoke-e2e --changed` + `tdq_meta_gate.py`) + xuất bản & push `origin` | `tdq_meta_gate.py` + `smoke-e2e --changed --workers auto --fresh` + `tron-bo --workers auto --fresh --reuse off` + `git push origin` + `git ls-remote origin` | `meta_gate` `PASS (2/2)`; `smoke-e2e` `418 passed`; `tron-bo` `5049` (`5012 passed, 37 skipped, 0 error`); 4 SHA `origin` khớp `release-receipt.json` | PASS |
| QC-F1 | Cổng tĩnh & hồi quy vùng chạm | `tdq_meta_gate.py` + `pytest` 5 file (`test_build_portable`, `test_agy_plugin_validate`, `test_agy_release_e2e`, `test_agy_launchers`, `test_rust_dispatch_parity`) | `5/5` file pytest `110 passed, 4 subtests passed` (`15.85s`); `ruff check` `No issues found`; `i18n_check` `0` dòng tiếng Việt | PASS |
| QC-F2 | Hành vi toàn kho & log | `tron-bo --workers auto --fresh --reuse off` + `log-verify.json` | `5049` collected (`5012` passed, `37` skipped, `0` failed, `368.74s`); `overall_pass: true` | PASS |
| QC-F3 | Ràng buộc kiến trúc & nhánh sạch | `build_portable.py --sinh-main` & `--sinh-release-agy` + kiểm `mcp_config` cá nhân | `main` kept `211`/dropped `7799`; `release/antigravity` kept `216`/dropped `7794`; không đụng `mcp_config` cá nhân | PASS |
| QC-F4 | Vệ sinh mã & Git | Kiểm `git log`, worktree, `.pytest_tmp` | `0` trailer `Co-Authored-By:`; `0` worktree mở; đã dọn `.pytest_tmp`; không push `local-upstream`/`upstream` | PASS |

## Bằng chứng

### Q1 & Q3 & Meta-Gate
```text
DOD_Q1_Q4_LOCAL_REMOTE_OK
[2026-11-27T12:37:57] doc_lint: lint 3 file: CHANGELOG.md, README-Antigravity.md, README.md
[2026-11-27T12:37:57] doc_lint: done — 0 violation(s) total, exit 0
{
  "status": "current",
  "reasons": [],
  "manifest_path": "docs/architecture/manifest.json"
}
Auto Meta-Gate: PASS (2/2 checks, 0.21s)
```

### Q2 & Q4 (Cargo, run_full_verification, smoke-e2e, tron-bo, ls-remote origin)
```text
cargo test: 39 passed (lib) + 4 passed (bin) = 43 passed; cargo build --release Finished in 15.92s (2119680 bytes)
run_full_verification.py: pytest_passed="24/24", agy_validate_findings=0
pytest 5-file: 110 passed, 4 subtests passed in 15.85s
smoke-e2e --changed --workers auto --fresh: 418 passed, 239 subtests passed in 109.27s (status=PASS)
tron-bo --workers auto --fresh --reuse off: [TDQ:TEST] PASS — scope=full backend=pytest tests=5049 skipped=37 in 368.74s
result.json sha256: 0542807a3bfab6d057aba471ebedd7384e14e10b807ed556d972399604cc184b
git ls-remote origin:
  89e9f159f7e0569085c039fb02e8ebfe389ee019	refs/heads/dev
  bb9af8e6f1288d92359ac9fb4683bf05f0a0e912	refs/heads/main
  b2c0183bdb1feef5a9a0ceaa4d5f4ff2eee5f06c	refs/heads/release/antigravity
  317e8bcff3b33e14d7662314eae9acd81736d994	refs/tags/v0.108.0 (^{commit} == bb9af8e6f1288d92359ac9fb4683bf05f0a0e912)
```

## Lệch spec chờ duyệt
không có

## Kết luận
PASS toàn bộ (`4/4` DoD, `QC-F1`–`QC-F4` đạt 100%).
