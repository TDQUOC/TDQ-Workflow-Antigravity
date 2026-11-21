# QC — Sửa Lỗi Registry Tool 8 Subagent Antigravity, Build Rust 3 OS & Phát hành `0.103.1`

Ngày: 2026-11-21 · Spec: ../spec/2026-11-21-1253-fix-subagent-tools-bump.md · Plan: ../plan/2026-11-21-1253-fix-subagent-tools-bump.md · Vòng: 1 (`muc_qc=full`)
Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

| # | Hạng mục | Lệnh đã chạy | Kết quả | PASS/FAIL |
|---|---|---|---|---|
| T4.1 | Log service mặc định ISO (`TDQ_LOG=1` / unset) vs im lặng (`TDQ_LOG=0`) trên `build_agy_plugin.py`, `build_portable.py`, `tdq-dispatch.exe` & test `test_build_portable.py` + `test_rust_dispatch_parity.py` | Probe `TDQ_LOG` (unset/`1`/`0`) + `py -3 -X utf8 -m pytest tests/test_build_portable.py tests/test_rust_dispatch_parity.py -q` | Cả `3` công cụ đều exit `0`, có ISO timestamp trên `stderr` khi mặc định/`TDQ_LOG=1` và `stderr == ""` (`len=0`) khi `TDQ_LOG=0`; pytest `84 passed, 4 subtests passed in 78.85s` | PASS |
| Q1 | Vá `_READONLY_TOOLS` / `_WRITER_TOOLS`, `tdq-explorer.md` & test âm tính (`8/8` agents sạch tool cấm, không lặp `write_file`) | `CHỜ` (`py -3 -X utf8 -m pytest tests/test_agent_frontmatter.py -q`) | `CHỜ` (`T4.2`) | CHỜ |
| Q2 | Manifest, `README.md`, `UPSTREAM-TRACE.md` & `CHANGELOG.md` (`<= 500` dòng) đồng bộ `0.103.1` | `CHỜ` (`py -3 -X utf8 -m pytest tests/test_docs_consistency.py tests/test_adapter_host.py -q` + `doc_lint.py CHANGELOG.md`) | `CHỜ` (`T4.2`) | CHỜ |
| Q3 | Crate Rust `0.103.1` & `3` nhị phân native thật (`Windows`, `Linux musl`, `macOS ARM64`), parity/lock, mô phỏng SSH & `2` máy SSH sạch `0` tàn dư | `CHỜ` (`cargo test` + `test_rust_dispatch_parity.py` đã PASS ở `T4.1` + `test_rust_lock_safety.py` + `test_remote_*_simulation.py` + SSH cleanup) | `CHỜ` (`T4.2` · `test_rust_dispatch_parity.py` đã đo trong nhóm `84 passed` ở `T4.1`) | CHỜ |
| Q4 | Compiler & gói plugin `plugins/tdq-workflow-agy/` (`v0.103.1`) đạt chuẩn nghiêm ngặt | `CHỜ` (`tools/build_agy_plugin.py --upstream .` + `agy.EXE plugin validate plugins/tdq-workflow-agy --strict --json` + `token_budget.py --kiem`) | `CHỜ` (`T4.2`) | CHỜ |
| Q5 | Bộ kiểm thử toàn repo `muc_qc = full` (`--workers 6`) & QC độc lập | `CHỜ` (`py -3 -X utf8 scripts/tdq_test.py tron-bo --workers 6 --fresh --reuse off` + `tdq_test.py so` + QC độc lập) | `CHỜ` (`T4.2`) | CHỜ |
| Q6 | Cài Antigravity user-level `0.103.1` (`~/.gemini/`), kiểm gọi `invoke_subagent` & giữ nguyên `~/.claude/` | `CHỜ` (`install.py` + `agy.EXE plugin validate C:\Users\admin\.gemini\config\plugins\tdq-workflow-agy --strict --json` + `agy.EXE plugin list`) | `CHỜ` (`T5.1`) | CHỜ |
| Q7 | Nhánh phát hành local `main` (`--sinh-main` từ `dev`) & annotated tag `v0.103.1` (không `git push`) | `CHỜ` (`build_portable.py --sinh-main --nguon dev --nhanh-dich main` + `git show main:.claude-plugin/plugin.json` + `git rev-parse main`) | `CHỜ` (`T5.2`) | CHỜ |
| QC-F1 | Trọn bộ `tron-bo --workers 6 --fresh --reuse off` sau sửa code cuối | `CHỜ` (`T4.2`) | `CHỜ` (`T4.2`) | CHỜ |
| QC-F2 | Hồi quy vùng chạm theo mọi dòng `Chạm:` trong plan | `CHỜ` (`T4.1` đã chạy `test_build_portable.py` + `test_rust_dispatch_parity.py`; các module vùng chạm còn lại chạy ở `T4.2`) | `CHỜ` (`T4.1` phủ `84 passed, 4 subtests passed in 78.85s`; chờ phần còn lại ở `T4.2`) | CHỜ |
| QC-F3 | Ràng buộc kiến trúc phải giữ (Spec §5: `skills/` dùng chung, `CHANGELOG.md <= 500` dòng, `main` chỉ giữ phần lõi qua `--sinh-main`) | `CHỜ` (`T4.2`) | `CHỜ` (`T4.2`) | CHỜ |
| QC-F4 | Clean Code Self-check (`clean-code.md`, `5` câu hỏi SOLID) | `CHỜ` (`T4.1` không sửa mã nguồn; tổng hợp cho toàn bộ file sửa ở `T4.2`) | `CHỜ` (`T4.2`) | CHỜ |

---

## Bằng chứng

### T4.1 — Kiểm chứng Log Service (`TDQ_LOG=1` vs `TDQ_LOG=0`) & Bộ test Portable/Parity

#### 1. `tools/build_agy_plugin.py` (build ra thư mục tạm ngoài repo qua `--output <tmp>`)

- Lưu ý: cờ `--help` thoát ở bước phân tích tham số của `argparse` trước khi gọi `_log()` (`rc=0`, `stderr=''`, dòng đầu `usage: build_agy_plugin.py [-h] [--upstream UPSTREAM] [--output OUTPUT]`). Chạy build ra `TemporaryDirectory` ngoài repo kích hoạt `_log()` thật mà giữ worktree sạch `0` file bẩn:

```text
# TDQ_LOG unset (mặc định): rc=0, 4 dòng ISO trên stderr (1 dòng cargo build lần đầu + 3 dòng staged binary)
[2026-11-21T13:47:21] build_agy_plugin: building native windows binary via cargo build --release

# TDQ_LOG=1: rc=0, 3 dòng ISO trên stderr
[2026-11-21T13:48:36] build_agy_plugin: staged windows binary tdq-dispatch.exe from hooks\rust\tdq-dispatch\target\release\tdq-dispatch.exe
[2026-11-21T13:48:36] build_agy_plugin: staged linux binary tdq-dispatch-linux-x86_64 from plugins\tdq-workflow-agy\bin\tdq-dispatch-linux-x86_64
[2026-11-21T13:48:36] build_agy_plugin: staged darwin binary tdq-dispatch-darwin-arm64 from plugins\tdq-workflow-agy\bin\tdq-dispatch-darwin-arm64

# TDQ_LOG=0: rc=0, stderr rỗng hoàn toàn (len=0), stdout JSON status="OK"
```

#### 2. `scripts/build_portable.py --sinh-main --nguon HEAD --dry-run`

```text
# TDQ_LOG unset (mặc định): rc=0
[2026-11-21T13:47:41+07:00] build_portable: dry-run HEAD@74f953f -> main · kept=190 dropped=6976

# TDQ_LOG=1: rc=0
[2026-11-21T13:47:41+07:00] build_portable: dry-run HEAD@74f953f -> main · kept=190 dropped=6976

# TDQ_LOG=0: rc=0, stderr rỗng hoàn toàn (len=0)
```

#### 3. `plugins/tdq-workflow-agy/bin/tdq-dispatch.exe` (môi trường cô lập `TemporaryDirectory`)

- Chạy qua Python `subprocess.run` với `TDQ_PROJECT_DIR`, `HOME`, `USERPROFILE`, `GEMINI_CONFIG_DIR` trỏ vào `TemporaryDirectory` cô lập, `PLUGIN_ROOT=plugins/tdq-workflow-agy`, `TDQ_KHONG_CHAM_MAY=1`, `TDQ_KHOI_TAO_NEN=0`, `TDQ_RTK=0`, `RTK_DISABLED=1`:

```text
# Stdin EOF thuần (input="", mặc định SessionStart):
# - TDQ_LOG unset: rc=0, out_len=1169
[2026-11-21T13:48:52] rtk_integration: probe_rtk: verified rtk 1.2.0 at C:\Users\admin\.local\bin\rtk.EXE
[2026-11-21T13:48:52] session_start: SETUP-CAVEMAN opt-in disabled
[2026-11-21T13:48:52] dispatch event=SessionStart tool=- decision=inject ms=2187.3
[2026-11-21T06:48:52Z] tdq-dispatch: event=SessionStart route=cold sid=default ms=2277.09
# - TDQ_LOG=1: rc=0, out_len=865
[2026-11-21T13:48:52] dispatch event=SessionStart tool=- decision=inject ms=77.7
[2026-11-21T06:48:52Z] tdq-dispatch: event=SessionStart route=cold sid=default ms=162.68
# - TDQ_LOG=0: rc=0, stderr="" (len=0), out_len=865

# Stdin EOF với --event PostInvocation (hot path):
# - TDQ_LOG unset: rc=0, stderr=[2026-11-21T06:47:41Z] tdq-dispatch: event=PostInvocation route=hot sid=default ms=0.79, stdout={}
# - TDQ_LOG=1:     rc=0, stderr=[2026-11-21T06:47:41Z] tdq-dispatch: event=PostInvocation route=hot sid=default ms=0.24, stdout={}
# - TDQ_LOG=0:     rc=0, stderr="" (len=0), stdout={}

# Payload JSON mẫu {"cwd": "<tmp_repo>", "conversationId": "t41-probe"}:
# - PostInvocation TDQ_LOG=1: rc=0, stderr=[2026-11-21T06:47:41Z] tdq-dispatch: event=PostInvocation route=hot sid=t41-probe ms=0.25, stdout={}
# - PostInvocation TDQ_LOG=0: rc=0, stderr="" (len=0), stdout={}
# - SessionStart   TDQ_LOG=1: rc=0, stderr=[2026-11-21T13:47:44] dispatch ... + [2026-11-21T06:47:44Z] tdq-dispatch: event=SessionStart route=cold sid=t41-probe ms=149.84
# - SessionStart   TDQ_LOG=0: rc=0, stderr="" (len=0), stdout={"injectSteps": ...}
```

#### 4. Bộ test `tests/test_build_portable.py` & `tests/test_rust_dispatch_parity.py`

```text
py -3 -X utf8 -m pytest tests/test_build_portable.py tests/test_rust_dispatch_parity.py -q
.................................................................... [ 80%]
................                                                         [100%]
84 passed, 4 subtests passed in 78.85s (0:01:18)
```

### Q1
CHỜ (`T4.2`).

### Q2
CHỜ (`T4.2`).

### Q3
CHỜ (`T4.2` — riêng `tests/test_rust_dispatch_parity.py` đã PASS trong nhóm `84 passed, 4 subtests passed in 78.85s` ở `T4.1`).

### Q4
CHỜ (`T4.2`).

### Q5
CHỜ (`T4.2`).

### Q6
CHỜ (`T5.1`).

### Q7
CHỜ (`T5.2`).

### QC-F1
CHỜ (`T4.2`).

### QC-F2
CHỜ (`T4.1` đã kiểm chứng `tests/test_build_portable.py` + `tests/test_rust_dispatch_parity.py` → `84 passed, 4 subtests passed in 78.85s`; các module vùng chạm còn lại chờ `T4.2`).

### QC-F3
CHỜ (`T4.2`).

### QC-F4
CHỜ (`T4.1` không sửa mã nguồn; đánh giá SOLID đầy đủ cho toàn đợt ở `T4.2`).

---

## Lệch spec chờ duyệt

CHỜ (cập nhật đầy đủ ở `T4.2` khi chạy `tdq_state.py lech list` và nghiệm thu toàn bộ `Q1`–`Q7`).

## Kết luận

CHỜ — đã hoàn tất `T4.1` (**PASS** kiểm chứng log service `TDQ_LOG=1` / mặc định vs `TDQ_LOG=0` trên `build_agy_plugin.py`, `build_portable.py`, `tdq-dispatch.exe` và `84 passed, 4 subtests passed in 78.85s` cho `tests/test_build_portable.py` + `tests/test_rust_dispatch_parity.py`); còn `Q1`–`Q7` và `QC-F1`–`QC-F4` chờ hoàn tất ở `T4.2`, `T5.1`, `T5.2`.
