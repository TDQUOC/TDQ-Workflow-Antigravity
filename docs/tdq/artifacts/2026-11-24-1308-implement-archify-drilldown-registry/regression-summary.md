# Task T4.2 Regression & Hygiene Summary

- **Request**: `2026-11-24-1308-implement-archify-drilldown-registry`
- **Branch**: `feature/implement-archify-drilldown-registry` (`327b401b`)
- **Mode**: Artifact-only verification (no edits to `scripts/`, `hooks/`, `skills/`, `tests/`, `plugins/`, `docs/tdq/plan/`, or `C:\Users\admin\Documents\archify`)

## 1. Unified Regression & Archify Pytest Results

> Note: PowerShell does not glob unquoted `tests/test_archify_*.py` before invoking `python` (running unexpanded `tests/test_archify_*.py` exited `1` with `ERROR: file or directory not found: tests/test_archify_*.py`). Expanding the matching paths in PowerShell ran every file in the requested scope.

### 1.1 Unified Regression Suite (16 files)
- **Command**:
  ```powershell
  $files = (Get-ChildItem tests/test_archify_*.py).FullName + @("tests/test_tdq_archify.py", "tests/test_tdq_setup.py", "tests/test_agy_host_setup.py"); py -3 -X utf8 -m pytest @files -q
  ```
- **Result**: `431 passed, 4 skipped, 113 subtests passed in 78.58s (0:01:18)` (`0 failed`, exit `0`)

### 1.2 Archify-Only Breakout Suite (14 files, >= 250 target)
- **Command**:
  ```powershell
  $files = (Get-ChildItem tests/test_archify_*.py).FullName + @("tests/test_tdq_archify.py"); py -3 -X utf8 -m pytest @files -q
  ```
- **Result**: `362 passed, 4 skipped, 113 subtests passed in 66.83s (0:01:06)` (`0 failed`, exit `0`; `362 >= 250`)

### 1.3 Skip Reason Audit (`-rs`)
- **Command**:
  ```powershell
  py -3 -X utf8 -m pytest tests/test_archify_artifacts.py tests/test_archify_delivery.py tests/test_archify_distribution.py tests/test_archify_e2e.py -rs -q
  ```
- **Result**: `115 passed, 4 skipped, 6 subtests passed in 30.18s` (exit `0`)
- **Skipped tests (all 4 due to Windows non-elevated symlink restriction)**:
  - `tests/test_archify_artifacts.py:202` — `Symlinks not supported in this environment`
  - `tests/test_archify_artifacts.py:868` — `Symlinks not supported`
  - `tests/test_archify_artifacts.py:1371` — `Symlinks not supported in this environment`
  - `tests/test_archify_delivery.py:167` — `Symlinks not supported in this environment`

## 2. Ruff Lint Verification

- **Command**:
  ```powershell
  py -3 -X utf8 -m ruff check scripts/archify_registry.py scripts/archify_portal.py tests/test_archify_logging.py tests/test_archify_portal.py tests/test_archify_registry.py
  ```
- **Result**: `All checks passed!` (exit `0`)

## 3. Meta-Gate (`tdq_meta_gate.py`) & `i18n_check.py` Verification

### 3.1 Raw `tdq_meta_gate.py` Output
- **Command**: `py -3 -X utf8 scripts/tdq_meta_gate.py`
- **Result**: `Auto Meta-Gate: FAIL (3/4 checks, 0.43s)` (exit `1`, `files=346`, diffed against `dev`)
  - `doc_lint`: `checked 24 file(s), errors=0` (**PASS**)
  - `token_budget`: `checked root=C:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/plugins/tdq-workflow-agy, errors=0` (**PASS**)
  - `git_co_author`: `errors=0` (**PASS**)
  - `cli_flags`: `skip (no scenario/bug files)`
  - `i18n_check`: `checked 20 file(s), errors=740` (**FAIL** on whole-file scan)

### 3.2 Whole-File `i18n_check` Breakdown (740 findings across 10 unique paths × 2 mirror copies)
| File (root + `plugins/tdq-workflow-agy/` mirror) | Per-copy | Total | Reason |
|---|---:|---:|---|
| `scripts/tdq_setup.py` | 358 | 716 | Pre-existing Vietnamese comments, strings, and CLI messages |
| `scripts/archify_model.py` | 5 | 10 | Mandatory `"chưa xác minh"` evidence sentinel checks (`lines 733, 734, 807, 808, 831`) |
| `skills/tdq-build/references/archify-lifecycle.md` | 2 | 4 | Mandatory Vietnamese report/evidence terms (`lines 30, 36`) |
| `skills/tdq-intake/references/archify-quick.md` | 3 | 6 | Mandatory `"Hiện trạng: chưa có"` / `"mốc 2026-11-09-0143"` (`lines 7, 19, 20`) |
| `skills/tdq-spec/references/archify-ba.md` | 2 | 4 | Mandatory `"Hiện trạng: chưa có"` / `"mốc 2026-11-09-0143"` (`lines 18, 48`) |
| **Total** | **370** | **740** | All 740 are pre-existing or mandatory domain sentinels |

### 3.3 Targeted `i18n_check.py` & `git diff dev...HEAD` Added-Line Audit
- **Command**:
  ```powershell
  py -3 -X utf8 scripts/i18n_check.py scripts/archify_registry.py scripts/archify_portal.py tests/test_archify_logging.py tests/test_archify_portal.py tests/test_archify_registry.py
  ```
- **Result**: `0 Vietnamese line(s) in 5 file(s)` (exit `0`; all Vietnamese UI labels in `scripts/archify_portal.py` are tagged `# i18n-allow`).
- **Added (`+`) lines vs `dev` (`git diff dev...HEAD`)**:
  - `skills/`: `skills_vi_added= 0` (0 newly introduced Vietnamese lines).
  - `scripts/`: `27` Vietnamese UI dict lines in `scripts/archify_portal.py` (all tagged `# i18n-allow`), `2` relocated lines in `scripts/archify_model.py` (`_validate_master_flow` checking the pre-existing `"chưa xác minh"` sentinel), and `0` added Vietnamese lines in `scripts/archify_registry.py`, `scripts/tdq_archify.py`, `scripts/tdq_setup.py`, `scripts/archify_artifacts.py`, or `scripts/archify_delivery.py`.

## 4. Upstream `archify` & Repo Working Tree Cleanliness

- **Upstream `C:\Users\admin\Documents\archify` (`HEAD 25cf3708`)**:
  - Tracked files (`git -C C:\Users\admin\Documents\archify status --porcelain --untracked-files=no`): empty (`""`, `0` tracked modifications/stagings; `archify_upstream_dirty=""` for tracked files).
  - Full `git -C C:\Users\admin\Documents\archify status --porcelain`: `0` modified/staged files, plus `7` pre-existing untracked (`??`) paths dated `2026-10-24` (`.codex/`, `docs/archify-architecture-analysis.md`, `docs/archify-architecture-preview.html`, `docs/tdq/`, `docs/workinglog/`, `graphify-out/`, `test/archify-architecture-report.test.mjs`) — confirming `0` upstream edits during this work.
- **Current repo tracked status (`rtk bypass git status --short --untracked-files=no`)**:
  - `M docs/tdq/.tdq-phat-hanh.json`
  - `M graphify-out/graph.json`
  - `M graphify-out/manifest.json`
  - `0` dirty source or test files under `scripts/`, `hooks/`, `skills/`, `tests/`, or `plugins/`.
