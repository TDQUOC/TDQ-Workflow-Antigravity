# PLAN — Nâng phiên bản 0.108.0, phát hành đa nhánh, commit và push

Ngày: 2026-11-27 · Spec: ../spec/2026-11-27-0157-nang-version-release-commit-push.md (bản 1.0, ĐÃ DUYỆT)
Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md
Mode thực thi: subagent — kết quả đo `tdq_bench.py simulate` chọn đội, chênh 2.0 phút (12.3 vs 14.3 phút, 4 đợt, hệ số 1.5) (ĐÃ CHỐT: subagent)
Trạng thái plan: ĐÃ DUYỆT

> **Tóm tắt dễ hiểu:** Kế hoạch chia việc phát hành thành bốn chặng nối tiếp rõ ràng từ cập nhật số phiên bản gốc tới đẩy lên GitHub. Hai chặng đầu nâng đồng bộ khai báo đa nền tảng, biên dịch lại gói Rust cùng gói Antigravity và làm mới tài liệu kiến trúc. Hai chặng cuối kiểm chứng log cùng toàn kho kiểm thử, cài đặt cục bộ, xuất bản hai nhánh phát hành sạch và gắn nhãn lên kho chung.

## Mục lục

- Phân bổ Model & Effort
- Quy tắc thi hành (áp cho mọi task)
- Thiết kế Trước vs Sau
- Ràng buộc toàn cục & Bản đồ Sở hữu Hợp đồng (Ownership Map)
- P1 — Nâng version gốc, crate Rust và biên dịch nhị phân Windows
- P2 — Biên dịch gói AGY, cập nhật tài liệu và làm mới Master Map
- P3 — Log service, cài đặt cục bộ và kiểm chứng đa tầng
- P4 — Hợp nhất dev, xuất bản nhánh sạch, gắn tag và push origin
- Cụm song song
- Luật file nóng (một file, nhiều task chạm)
- Definition of Done

## Phân bổ Model & Effort

> User được quyền đổi `type model` hoặc `effort` lúc duyệt plan. Thang model: [subagent-tuning.md](../../plugins/tdq-workflow-agy/skills/tdq-conventions/references/subagent-tuning.md).

| Pha | Vai trò | Model | Effort | Ghi chú |
|---|---|---|---|---|
| `implement` | `main` (Leader) hoặc `tdq-implementer` | `gemini-4-neon` (`inherit`) | `high` | Phiên chính chạy trực tiếp chuỗi phát hành nối tiếp; user có thể đổi sang `gemini-4-hydrogen` lúc duyệt |
| `qc` | `main` (Leader, `muc_qc=full`) | `gemini-4-neon` (`inherit`) | `high` | Chạy đủ DoD `Q1`–`Q4`, `QC-F1`–`QC-F4`, `smoke-e2e --changed` và `tron-bo` |
| `report` | `main` (Leader) | `gemini-4-neon` (`inherit`) | `high` | Tổng hợp kết quả thật, dựng Archify report HTML và đóng `state.json` về `idle` |

## Quy tắc thi hành (áp cho mọi task)

1. Thứ tự phase là thứ tự phụ thuộc — không đảo.
2. Mỗi task: đánh `[~]` khi bắt đầu → chạy kiểm tra nền/test trước → sửa → chạy lệnh `Test:` xanh → đổi sang `[x]` NGAY vào file này. Trạng thái checkbox: `[ ]` chưa làm · `[~]` đang làm · `[x]` xong.
3. Giữa các bước dùng kiểm chứng đích và `tdq_test.py vung-cham`; trọn bộ `tron-bo` chạy ở cổng QC (`muc_qc=full`).
4. Lệnh nào chạm state mô phỏng phải có `TDQ_PROJECT_DIR=<thư mục tạm>`; state thật chỉ ghi qua `scripts/tdq_state.py`.
5. QC FAIL → thêm task fix `QCn.1` vào mục `## QC vòng N — fix` của file này (không cần duyệt lại), lặp đến khi pass.
6. Chỉ thực hiện commit, merge `dev`, xuất bản nhánh sạch và `git push origin` ở `T4.1` sau khi `P1`–`P3` đã đạt xanh, và tuyệt đối không thêm `Co-Authored-By:`.
7. Tuân thủ 6 mã cấm cơ học (`ANTI-1` Fake Red, `ANTI-2` Blind Assertion, `ANTI-3` Dirty State Git, `ANTI-4` Late Tick, `ANTI-5` Raw Dump, `ANTI-6` Broad Area).

## Thiết kế Trước vs Sau

| Khía cạnh | Hiện trạng (Trước) | Thiết kế mới (Sau) |
|---|---|---|
| Phiên bản & Rust | Host/AGY ở `0.107.0`; `Cargo.toml` ở `0.105.0`; cài đặt `~/.gemini/` lệch phiên bản | Đồng nhất `0.108.0` ở host, `Cargo.toml`, `tdq-dispatch.exe`, `plugins/tdq-workflow-agy/` và bản cài cục bộ |
| Tài liệu & Master Map | `CHANGELOG.md` chưa có `P0`–`P2`; `README.md` ghi `4602 passed`; `docs/architecture/` `stale` (`24` thay đổi) | `CHANGELOG.md` có `0.108.0` (`<= 500` dòng), `README.md` ghi `0.108.0` + `5012 passed`, Master Map `current` |
| Nhánh phát hành & Remote | `dev` đi trước `origin/dev` `73` commit; `main`, `release/antigravity` và tag ở `v0.107.0` | `dev` hợp nhất sạch, `main` + `release/antigravity` dựng bằng git plumbing, annotated tag `v0.108.0` trên `main`, `origin` khớp SHA |

*Đối chiếu sơ đồ kiến trúc:* Tham chiếu Archify preview đã duyệt [truoc-sau-preview.html](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/spec/2026-11-27-0157-nang-version-release-commit-push-preview.html) và manifest `docs/tdq/spec/2026-11-27-0157-nang-version-release-commit-push-preview.manifest.json` (`binding: current`).

## Ràng buộc toàn cục & Bản đồ Sở hữu Hợp đồng (Ownership Map)

- Ngôn ngữ: docstring/comment ở `tools/` viết tiếng Anh (`i18n_check.py` `0` dòng tiếng Việt mới); tài liệu `CHANGELOG.md`/`README*.md` viết tiếng Việt chuẩn R6/R16; `TDQ_LOG=0` ra `0B` stderr; `GIỮ NGUYÊN` toàn bộ logic runtime `P0`–`P2`, `schema_version=6` và `23` mã cổng AGY.

| Hợp đồng / Ký hiệu (§3c) | File & Task sở hữu | Task / File tiêu thụ |
|---|---|---|
| `version = "0.108.0"` (host + Rust) | `.claude-plugin/plugin.json`, `.codex-plugin/plugin.json`, `docs/tdq/.tdq-phat-hanh.json`, `hooks/rust/tdq-dispatch/Cargo.toml` (`T1.1`) | `T2.1`, `T2.2`, `T4.1` (`build_portable.py`) |
| `PLUGIN_VERSION = "0.108.0"` & `plugins/tdq-workflow-agy/` | `tools/patches/agy_manifests.py`, `tools/build_agy_plugin.py`, `plugins/tdq-workflow-agy/` (`T2.1`) | `T2.3`, `T3.1`, `T3.2`, `T4.1` |
| `CHANGELOG.md` (`<= 500` dòng R6) & `README*.md` (`5012 passed`) | `CHANGELOG.md`, `README.md`, `README-Antigravity.md` (`T2.2`; không chạm `CHANGELOG-archive-4.md` vì dưới trần R6) | `T2.3`, `T3.2`, `T4.1` |
| Master Map `status == "current"` | `graphify-out/`, `docs/architecture/` (`T2.3`) | `T3.1`, `T4.1` |
| `log-verify.json` & cài đặt `~/.gemini/config/plugins/tdq-workflow-agy` | `docs/tdq/artifacts/2026-11-27-0157-nang-version-release-commit-push/log-verify.json` (`T3.1`) | `T3.2`, QC `Q2` |
| `docs/verification_evidence.json` (`24/24`, `0` findings) | `docs/verification_evidence.json` (`T3.2`) | `T4.1`, QC `Q2`/`Q4` |
| `release-receipt.json` (SHA `dev`/`main`/`release/antigravity`/`v0.108.0`) | `docs/tdq/artifacts/2026-11-27-0157-nang-version-release-commit-push/release-receipt.json` (`T4.1`) | QC `Q4`, Report |

## P1 — Nâng version gốc, crate Rust và biên dịch nhị phân Windows

- [x] **T1.1** (e6m) Nâng phiên bản lên `0.108.0` trong `.claude-plugin/plugin.json`, `.codex-plugin/plugin.json`, `docs/tdq/.tdq-phat-hanh.json` và `hooks/rust/tdq-dispatch/Cargo.toml`, rồi chạy `cargo test` và `cargo build --release` xuất nhị phân Windows mới — Test: `py -3 -X utf8 -c "import json, tomllib; from pathlib import Path; assert json.loads(Path('.claude-plugin/plugin.json').read_text(encoding='utf-8'))['version']=='0.108.0'; assert json.loads(Path('.codex-plugin/plugin.json').read_text(encoding='utf-8'))['version']=='0.108.0'; assert json.loads(Path('docs/tdq/.tdq-phat-hanh.json').read_text(encoding='utf-8'))['phien_ban']=='0.108.0'; assert tomllib.loads(Path('hooks/rust/tdq-dispatch/Cargo.toml').read_text(encoding='utf-8'))['package']['version']=='0.108.0'" && cargo test --manifest-path hooks/rust/tdq-dispatch/Cargo.toml && cargo build --manifest-path hooks/rust/tdq-dispatch/Cargo.toml --release`
  - Req: `§1`, `§2 #1`, `§3c B1`, `§6 Q1-Q2` · Ngoài phạm vi: `GIỮ NGUYÊN` toàn bộ logic trong `hooks/rust/tdq-dispatch/src/*.rs` và không sửa `userConfig` trong `.claude-plugin/plugin.json`.
  - Chạm: `.claude-plugin/plugin.json`, `.codex-plugin/plugin.json`, `docs/tdq/.tdq-phat-hanh.json`, `hooks/rust/tdq-dispatch/Cargo.toml`, `hooks/rust/tdq-dispatch/Cargo.lock`
  - Cần: Không
  - Giao tiếp: Consumes: hiện trạng `0.107.0`/`0.105.0` | Produces: manifest/TOML `"0.108.0"` và `hooks/rust/tdq-dispatch/target/release/tdq-dispatch.exe` mới
  - Neo & Công cụ: sửa bằng edit_file tại trường `"version"` / `"phien_ban"` / `version =` rồi chạy `cargo test` và `cargo build --release`
  - Trước → Sau: Host `0.107.0` + Rust `0.105.0` → đồng bộ `0.108.0` kèm `tdq-dispatch.exe` biên dịch mới và `Cargo.lock` khớp
  - Tiêu chí chấp nhận (EARS): KHI lệnh kiểm tra hoàn tất, HỆ THỐNG PHẢI trả `version == "0.108.0"` ở cả 4 file, `cargo test` đạt `0` failed và file `target/release/tdq-dispatch.exe` tồn tại với magic bytes `MZ`.
  - Logic cốt lõi: Sửa tuần tự 4 file cấu hình phiên bản (`cap_nhat` ISO ngày 2026-11-27 ở `.tdq-phat-hanh.json`), chạy `cargo test` rồi `cargo build --release` cập nhật `Cargo.lock` và `.exe`.
  - Ca góc hiểm & Assert: `docs/tdq/.tdq-phat-hanh.json` chống hạ cấp (`tach_version`) và phải hợp lệ JSON UTF-8 · `assert ver == "0.108.0"` và `cargo` exit `0`.

**Xong P1 khi**: Cả 4 tệp phiên bản khớp `"0.108.0"`, `cargo test` đạt `100%` pass và `target/release/tdq-dispatch.exe` biên dịch thành công.

## P2 — Biên dịch gói AGY, cập nhật tài liệu và làm mới Master Map

- [x] **T2.1** (e8m) Cập nhật `"0.108.0"` ở `tools/patches/agy_manifests.py` (`PLUGIN_VERSION`), `tools/patches/__init__.py` và `tools/build_agy_plugin.py`, rồi chạy `tools/build_agy_plugin.py` tái tạo gói `plugins/tdq-workflow-agy/` — Test: `py -3 -B tools/build_agy_plugin.py && agy.EXE plugin validate plugins/tdq-workflow-agy --strict --json && py -3 -X utf8 -c "import json; from pathlib import Path; assert json.loads(Path('plugins/tdq-workflow-agy/plugin.json').read_text(encoding='utf-8'))['version']=='0.108.0'; assert json.loads(Path('plugins/tdq-workflow-agy/manifest.json').read_text(encoding='utf-8'))['version']=='0.108.0'; assert 'v0.108.0' in Path('plugins/tdq-workflow-agy/README.md').read_text(encoding='utf-8')"`
  - Req: `§1`, `§2 #2`, `§3c B2`, `§6 Q1-Q2` · Ngoài phạm vi: `GIỮ NGUYÊN` toàn bộ patcher logic, `23` mã cổng AGY và 2 binary prebuilt Linux/macOS trong `plugins/tdq-workflow-agy/bin/`.
  - Chạm: `tools/patches/agy_manifests.py`, `tools/patches/__init__.py`, `tools/build_agy_plugin.py`, `plugins/tdq-workflow-agy/`
  - Cần: `T1.1`
  - Giao tiếp: Consumes: `tdq-dispatch.exe` từ `T1.1` | Produces: `plugins/tdq-workflow-agy/` bản `0.108.0` có `0` findings validator
  - Neo & Công cụ: sửa bằng edit_file trên `tools/patches/agy_manifests.py:9` (`PLUGIN_VERSION`), `tools/build_agy_plugin.py:2` (`main`) và `tools/patches/__init__.py:1`, rồi chạy `py -3 -B tools/build_agy_plugin.py`
  - Trước → Sau: `PLUGIN_VERSION = "0.107.0"` → `"0.108.0"` và gói `plugins/tdq-workflow-agy/` tái biên dịch đủ 3 OS binary hợp lệ magic bytes
  - Tiêu chí chấp nhận (EARS): KHI chạy `tools/build_agy_plugin.py` và `agy plugin validate --strict --json`, HỆ THỐNG PHẢI trả `findings == []`, `version == "0.108.0"` và giữ đủ 3 binary (`MZ`, ELF, Mach-O).
  - Logic cốt lõi: Cập nhật docstring tiếng Anh + hằng `PLUGIN_VERSION`, chạy `build_agy_plugin.py` để tự stage `tdq-dispatch.exe` mới và giữ 2 binary cross-OS qua `verify_binary_magic`.
  - Ca góc hiểm & Assert: Không để rò chuỗi `0.107.0` trong `tools/` hoặc đường dẫn cá nhân trong `mcp_config.json` · `assert data["findings"] == []` và `version == "0.108.0"`.

- [x] **T2.2** (e8m) Thêm mục `## 0.108.0 — 2026-11-27` tổng hợp 3 pha `P0`–`P2` lên đầu `CHANGELOG.md` (giữ `<= 500` dòng theo R6, xoay phần cũ sang `docs/CHANGELOG-archive-4.md` khi vượt `490` dòng), nâng `README.md` (`0.108.0`, `5012%20passed`) và `README-Antigravity.md` (`v0.108.0`) — Test: `py -3 -X utf8 scripts/doc_lint.py CHANGELOG.md README.md README-Antigravity.md && py -3 -X utf8 -c "from pathlib import Path; cl=Path('CHANGELOG.md').read_text(encoding='utf-8').splitlines(); assert len(cl)<=500 and any(l.startswith('## 0.108.0') for l in cl); rm=Path('README.md').read_text(encoding='utf-8'); assert 'version-0.108.0' in rm and 'tests-5012%20passed' in rm and 'v0.108.0' in rm; ra=Path('README-Antigravity.md').read_text(encoding='utf-8'); assert 'v0.108.0' in ra"`
  - Req: `§1`, `§2 #3`, `§3c B2`, `§5`, `§6 Q1,Q3` · Ngoài phạm vi: `GIỮ NGUYÊN` nguyên văn các mục lịch sử từ `0.107.0` trở về trước (nếu xoay archive thì chỉ di chuyển nguyên văn sang `docs/CHANGELOG-archive-4.md`).
  - Chạm: `CHANGELOG.md`, `README.md`, `README-Antigravity.md`
  - Cần: `T1.1`
  - Giao tiếp: Consumes: báo cáo đã chốt `P0`, `P1`, `P2` | Produces: `CHANGELOG.md <= 500` dòng và bộ `README*.md` đồng nhất `0.108.0` / `5012 passed`
  - Neo & Công cụ: sửa bằng edit_file trên `CHANGELOG.md:5`, `README.md:3-4,154,247` và `README-Antigravity.md:3`
  - Trước → Sau: `CHANGELOG.md` dừng ở `0.107.0` (`417` dòng) và `README.md` ghi `4602 passed` → có mục `0.108.0` (`<= 500` dòng) và `README.md` ghi `0.108.0` + `5012 passed`
  - Tiêu chí chấp nhận (EARS): KHI chạy `doc_lint.py` và kiểm chuỗi, HỆ THỐNG PHẢI thoát `0` (`0` vi phạm), tổng dòng `CHANGELOG.md <= 500` và cả `README.md`, `README-Antigravity.md` đều chứa `0.108.0`.
  - Logic cốt lõi: Chèn tóm tắt `P0` (khóa sidecar/lease, hàng đợi 3 tầng, breaker/budget, MCP policy, parity Rust), `P1` (4 Domain Pack, BM25, Zero-Downgrade Lock) và `P2` (Paperclip CLI bridge tắt mặc định); đo lại số dòng `CHANGELOG.md` và cập nhật badge test ở `README.md`.
  - Ca góc hiểm & Assert: Trần cứng `500` dòng R6 ở `CHANGELOG.md` và URL badge `tests-5012%20passed` không lỗi encode · `assert len(cl) <= 500` và `doc_lint` exit `0`.

- [x] **T2.3** (e6m) Cập nhật đồ thị mã nguồn `graphify extract . --code-only` và chạy `scripts/tdq_archify.py sync-master` làm mới Master Map `docs/architecture/` từ `stale` sang `current` — Test: `graphify extract . --code-only && py -3 -X utf8 scripts/tdq_archify.py sync-master --model docs/tdq/models/master.model.json --project . --out docs/architecture --incremental && py -3 -X utf8 -c "import json, subprocess; out=subprocess.check_output(['py','-3','-X','utf8','scripts/tdq_archify.py','status'], text=True, encoding='utf-8'); data=json.loads(out); assert data['status']=='current' and data['reasons']==[]"`
  - Req: `§1`, `§2 #3`, `§3c B2`, `§6 Q3` · Ngoài phạm vi: `GIỮ NGUYÊN` các báo cáo Archify cũ của `P0`–`P2` trong `docs/tdq/reports/`.
  - Chạm: `graphify-out/`, `docs/architecture/`
  - Cần: `T2.1`, `T2.2`
  - Giao tiếp: Consumes: mã nguồn và gói đã cập nhật từ `T2.1`–`T2.2` | Produces: `graphify-out/graph.json` mới và `docs/architecture/status.json` có `status == "current"`
  - Neo & Công cụ: `run_command` chạy `graphify extract . --code-only` rồi `py -3 -X utf8 scripts/tdq_archify.py sync-master` và kiểm `tdq_archify.py status`
  - Trước → Sau: `docs/architecture/status.json` ở trạng thái `stale` (`24` lý do) và đồ thị cũ hơn `146` phút → đồ thị tươi và Master Map đạt `current` (`0` lý do `stale`)
  - Tiêu chí chấp nhận (EARS): KHI `sync-master` hoàn tất, lệnh `tdq_archify.py status` PHẢI trả JSON có `"status": "current"` và `"reasons": []`.
  - Logic cốt lõi: Tái trích xuất đồ thị mã nguồn trước, sau đó gọi `tdq_archify.py sync-master` để cập nhật manifest hash toàn bộ nguồn mới của `P0`–`P2` và render lại Master Map.
  - Ca góc hiểm & Assert: Nếu `sync-master --incremental` giữ lại lý do `stale` do tệp mới thêm thì chạy `sync-master --full` (hoặc đồng bộ `master.model.json`) · `assert data["status"] == "current"`.

**Xong P2 khi**: `plugins/tdq-workflow-agy/` mang `0.108.0` (`0` findings), `CHANGELOG.md <= 500` dòng, `README*` cập nhật đủ và `tdq_archify.py status` trả `current`.

## P3 — Log service, cài đặt cục bộ và kiểm chứng đa tầng

- [x] **T3.1** (e5m) Xác minh dịch vụ log (`TDQ_LOG=1` có ISO timestamp, `TDQ_LOG=0` ra `0B` stderr) trên `build_portable.py` và `install_agy_plugin.py --dry-run`, cài đồng bộ `0.108.0` vào `~/.gemini/config/plugins/tdq-workflow-agy`, và ghi biên bản `log-verify.json` — Test: `py -3 -X utf8 tools/install_agy_plugin.py && py -3 -X utf8 -c "import json, os, subprocess; from pathlib import Path; env0={**os.environ,'TDQ_LOG':'0'}; p0=subprocess.run(['py','-3','-X','utf8','scripts/build_portable.py','--sinh-main','--dry-run'], env=env0, capture_output=True, text=True, encoding='utf-8', check=True); assert p0.stderr==''; env1={**os.environ,'TDQ_LOG':'1'}; p1=subprocess.run(['py','-3','-X','utf8','scripts/build_portable.py','--sinh-main','--dry-run'], env=env1, capture_output=True, text=True, encoding='utf-8', check=True); assert '[' in p1.stderr and 'build_portable' in p1.stderr; inst=json.loads((Path.home()/'.gemini'/'config'/'plugins'/'tdq-workflow-agy'/'plugin.json').read_text(encoding='utf-8')); assert inst['version']=='0.108.0'; lv=json.loads(Path('docs/tdq/artifacts/2026-11-27-0157-nang-version-release-commit-push/log-verify.json').read_text(encoding='utf-8')); assert lv['overall_pass'] is True"`
  - Req: `§1`, `§2 #2`, `§4`, `§6 Q2` · Ngoài phạm vi: `GIỮ NGUYÊN` cấu hình MCP cá nhân/Caveman/RTK hiện có trong `~/.gemini/config/plugins/tdq-workflow-agy`.
  - Chạm: `docs/tdq/artifacts/2026-11-27-0157-nang-version-release-commit-push/log-verify.json` (tạo mới)
  - Cần: `T2.1`, `T2.3`
  - Giao tiếp: Consumes: `plugins/tdq-workflow-agy/` `0.108.0` | Produces: bản cài `~/.gemini/.../tdq-workflow-agy` `0.108.0` và biên bản `log-verify.json`
  - Neo & Công cụ: chạy `tools/install_agy_plugin.py` và đo `TDQ_LOG=1/0` thực tế, rồi tạo mới file `docs/tdq/artifacts/2026-11-27-0157-nang-version-release-commit-push/log-verify.json`
  - Trước → Sau: Chưa cài bản `0.108.0` trên máy local và chưa có biên bản đo log đợt release → `~/.gemini/` mang `0.108.0` và `log-verify.json` có `overall_pass: true`
  - Tiêu chí chấp nhận (EARS): KHI `TDQ_LOG=0`, stderr PHẢI đạt đúng `0` byte; KHI `TDQ_LOG=1`, stderr PHẢI có ISO timestamp; tệp `plugin.json` trong `~/.gemini/config/plugins/tdq-workflow-agy/` PHẢI mang `"version": "0.108.0"`.
  - Logic cốt lõi: Chạy `install_agy_plugin.py` (không dùng `--sync-local-mcp` để không đụng file MCP cá nhân), kiểm `TDQ_LOG=1/0` trên 2 CLI, kiểm `i18n_check.py` trên các file `tools/` vừa sửa, rồi ghi kết quả vào `log-verify.json`.
  - Ca góc hiểm & Assert: Nếu file bị khóa WinError 32 khi chép vào `~/.gemini/`, kiểm lỗi trả về từ `sync_tree_inplace` (fail-closed, không nuốt lỗi) · `assert inst["version"] == "0.108.0"` và `assert lv["overall_pass"] is True`.

- [x] **T3.2** (e10m) Chạy kiểm chứng đa tầng `tools/run_full_verification.py`, cụm unit test đóng gói/AGY/parity và `tdq_test.py smoke-e2e --changed --workers auto --fresh` để xác nhận sạch `0` lỗi trước bước hợp nhất và xuất bản — Test: `py -3 -X utf8 tools/run_full_verification.py && py -3 -X utf8 -m pytest -q -n auto tests/test_build_portable.py tests/test_agy_plugin_validate.py tests/test_agy_release_e2e.py tests/test_agy_launchers.py tests/test_rust_dispatch_parity.py && py -3 -X utf8 scripts/tdq_test.py smoke-e2e --changed --workers auto --fresh`
  - Req: `§1`, `§2 #2`, `§4`, `§6 Q2,Q4` · Ngoài phạm vi: `GIỮ NGUYÊN` toàn bộ mã test hiện có (chỉ cập nhật kết quả bằng chứng tại `docs/verification_evidence.json`).
  - Chạm: `docs/verification_evidence.json`
  - Cần: `T3.1`
  - Giao tiếp: Consumes: gói `plugins/tdq-workflow-agy/` và toàn bộ thay đổi `T1.1`–`T3.1` | Produces: `docs/verification_evidence.json` (`24/24` passed, `0` findings)
  - Neo & Công cụ: `run_command` chạy `run_full_verification.py`, cụm `pytest` đóng gói/parity và `tdq_test.py smoke-e2e --changed --workers auto --fresh`
  - Trước → Sau: `docs/verification_evidence.json` còn ghi phiên bản/hash trước `0.108.0` → cập nhật bằng chứng mới cho `0.108.0` với `0` failed
  - Tiêu chí chấp nhận (EARS): KHI kết thúc cả 3 lệnh kiểm chứng, HỆ THỐNG PHẢI thoát mã `0`, `run_full_verification.py` đạt `24/24` pytest + `0` findings AGY, cụm đóng gói/parity và `smoke-e2e --changed` đạt `0` failed.
  - Logic cốt lõi: Chạy `run_full_verification.py` đầu tiên để sinh bằng chứng và kiểm `agy validate --strict` cả bản local lẫn staging, tiếp đó chạy cụm test đóng gói/parity và `smoke-e2e --changed`.
  - Ca góc hiểm & Assert: Chạy `smoke-e2e --changed` bắt buộc có `--workers auto --fresh` tránh vượt trần `120s` như đã ghi nhận ở P2 · `returncode == 0` trên cả 3 lệnh.

**Xong P3 khi**: `log-verify.json` đạt `overall_pass: true`, `~/.gemini/` mang `0.108.0`, `docs/verification_evidence.json` đạt `24/24` (`0` findings) và cụm test + `smoke-e2e --changed` đạt `0` failed.

## P4 — Hợp nhất dev, xuất bản nhánh sạch, gắn tag và push origin

- [>] **T4.1** (e6m) Sau khi chạy đủ kiểm chứng `P1`–`P3`, commit bản nâng cấp `0.108.0` trên nhánh `chore/nang-version-release-commit-push`, hợp nhất `--no-ff` vào `dev`, xuất bản 2 nhánh sạch `main` (`--sinh-main`) và `release/antigravity` (`--sinh-release-agy`), gắn annotated tag `v0.108.0` trên `main`, đẩy `dev`, `main`, `release/antigravity`, `v0.108.0` lên `origin`, và ghi `release-receipt.json` — Test: `py -3 -X utf8 -c "import json, subprocess; from pathlib import Path; r=json.loads(Path('docs/tdq/artifacts/2026-11-27-0157-nang-version-release-commit-push/release-receipt.json').read_text(encoding='utf-8')); assert r['version']=='0.108.0' and r['tag_points_to_main'] is True; ls=subprocess.check_output(['git','ls-remote','origin','refs/heads/dev','refs/heads/main','refs/heads/release/antigravity','refs/tags/v0.108.0'], text=True, encoding='utf-8'); assert r['dev_sha'] in ls and r['main_sha'] in ls and r['release_agy_sha'] in ls and r['tag_sha'] in ls"`
  - Req: `§1`, `§2 #4`, `§3c B3`, `§5`, `§6 Q4` · Ngoài phạm vi: `GIỮ NGUYÊN` nguyên tắc không `--force` push, không push lên `local-upstream` hay `upstream`, và `0` trailer `Co-Authored-By:`.
  - Chạm: `docs/tdq/artifacts/2026-11-27-0157-nang-version-release-commit-push/release-receipt.json` (tạo mới)
  - Cần: `T3.2`
  - Giao tiếp: Consumes: nhánh `chore/nang-version-release-commit-push` đã kiểm chứng xanh ở `T3.2` | Produces: `dev`, `main`, `release/antigravity`, tag `v0.108.0` đồng bộ trên `origin` và `release-receipt.json`
  - Neo & Công cụ: chạy lệnh git merge và `scripts/build_portable.py` (`sinh_nhanh_main`, `sinh_nhanh_release_agy`), gắn tag v0.108.0, push lên origin, rồi tạo mới `docs/tdq/artifacts/2026-11-27-0157-nang-version-release-commit-push/release-receipt.json`
  - Trước → Sau: `origin/dev` trễ `73` commit và `main`/`release/antigravity`/tag dừng ở `v0.107.0` → cả `4` ref khớp SHA `v0.108.0` trên `origin`
  - Tiêu chí chấp nhận (EARS): KHI đối chiếu `git ls-remote origin`, HỆ THỐNG PHẢI khớp chính xác SHA của `dev`, `main`, `release/antigravity` và annotated tag `v0.108.0`, đồng thời `git rev-parse v0.108.0^{commit} == git rev-parse main`.
  - Logic cốt lõi: Kiểm `git tag -l v0.108.0` rỗng trước khi gắn; merge `--no-ff` vào `dev` (xóa nhánh `chore` sau khi merge sạch); chạy 2 lệnh `build_portable.py` bằng git plumbing; gắn tag trên `main`; push `origin` và đối chiếu `git ls-remote origin`.
  - Ca góc hiểm & Assert: Không push nhánh `chore/...` lên remote; nếu bước `report`/đóng `idle` tạo thêm commit tài liệu trên `dev` sau QC thì push tiếp `origin dev` (nhánh `main`/`release/antigravity` không đổi vì lọc bỏ `docs/`) · `assert r["tag_points_to_main"] is True` và cả 4 SHA khớp `origin`.

**Xong P4 khi**: `dev`, `main`, `release/antigravity` và tag `v0.108.0` khớp SHA giữa local và `origin`, working tree không có thay đổi mã nguồn bẩn.

## Cụm song song

- Wave 1: `T1.1` (chốt gốc version + biên dịch Rust Windows).
- Wave 2: `T2.1` và `T2.2` có vùng `Chạm:` hoàn toàn tách rời (gói AGY vs tài liệu `CHANGELOG`/`README*`) nên chạy song song được trên lý thuyết; tuy nhiên tổng thời gian gọn và `T2.3` → `T3.1` → `T3.2` → `T4.1` nối tiếp phụ thuộc chặt chẽ (build → Master Map → install/verify → merge/push).
- Wave 3 → Wave 6: `T2.3` → `T3.1` → `T3.2` → `T4.1` chạy tuần tự.

## Luật file nóng (một file, nhiều task chạm)

Không có file nóng (`0` đường dẫn bị từ 2 task trở lên cùng khai ở `Chạm:`); mọi đường dẫn đều do đúng 1 task sở hữu theo `Ownership Map`.

## Definition of Done

Trỏ về `§6` của spec (`docs/tdq/spec/2026-11-27-0157-nang-version-release-commit-push.md`):

- [ ] Q1 Đồng bộ chuỗi phiên bản `0.108.0` đa host, `Cargo.toml` và `CHANGELOG.md <= 500` dòng (R6) — `py -3 -X utf8 -c "import json, tomllib; from pathlib import Path; assert json.loads(Path('.claude-plugin/plugin.json').read_text(encoding='utf-8'))['version']=='0.108.0'; assert json.loads(Path('.codex-plugin/plugin.json').read_text(encoding='utf-8'))['version']=='0.108.0'; assert json.loads(Path('docs/tdq/.tdq-phat-hanh.json').read_text(encoding='utf-8'))['phien_ban']=='0.108.0'; assert tomllib.loads(Path('hooks/rust/tdq-dispatch/Cargo.toml').read_text(encoding='utf-8'))['package']['version']=='0.108.0'; assert len(Path('CHANGELOG.md').read_text(encoding='utf-8').splitlines())<=500" && py -3 -X utf8 scripts/doc_lint.py CHANGELOG.md README.md README-Antigravity.md`
- [ ] Q2 Biên dịch Rust Windows, gói `plugins/tdq-workflow-agy/` (`0` findings) và cài đặt cục bộ `~/.gemini/` mang `0.108.0` — `cargo test --manifest-path hooks/rust/tdq-dispatch/Cargo.toml && py -3 -X utf8 tools/run_full_verification.py && py -3 -X utf8 -c "import json; from pathlib import Path; assert json.loads((Path.home()/'.gemini'/'config'/'plugins'/'tdq-workflow-agy'/'plugin.json').read_text(encoding='utf-8'))['version']=='0.108.0'"`
- [ ] Q3 Cập nhật `README.md` (`0.108.0` + `5012 passed`) và làm mới Master Map `docs/architecture/` đạt `current` — `py -3 -X utf8 -c "import json, subprocess; from pathlib import Path; rm=Path('README.md').read_text(encoding='utf-8'); assert 'version-0.108.0' in rm and 'tests-5012%20passed' in rm; st=json.loads(subprocess.check_output(['py','-3','-X','utf8','scripts/tdq_archify.py','status'], text=True, encoding='utf-8')); assert st['status']=='current' and st['reasons']==[]"`
- [ ] Q4 Kiểm thử toàn kho mức `full` (`tron-bo` + `smoke-e2e --changed` + `tdq_meta_gate.py`) xanh `0` lỗi, xuất bản `main` + `release/antigravity`, gắn tag `v0.108.0` trên `main` và push khớp SHA trên `origin` — `py -3 -X utf8 scripts/tdq_meta_gate.py && py -3 -X utf8 scripts/tdq_test.py tron-bo --workers auto --fresh --reuse off && py -3 -X utf8 -c "import json, subprocess; from pathlib import Path; r=json.loads(Path('docs/tdq/artifacts/2026-11-27-0157-nang-version-release-commit-push/release-receipt.json').read_text(encoding='utf-8')); ls=subprocess.check_output(['git','ls-remote','origin','refs/heads/dev','refs/heads/main','refs/heads/release/antigravity','refs/tags/v0.108.0'], text=True, encoding='utf-8'); assert r['tag_points_to_main'] is True and all(r[k] in ls for k in ('dev_sha','main_sha','release_agy_sha','tag_sha'))"`
