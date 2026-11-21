# QC — quality control
<!-- muc-luc-dong:
  Table of contents=12-23 · The QC level — what each level runs=24-49 ·
  The three execution steps=50-78 · What to run=79-94 ·
  The 120-second cap on smoke and runtime checks=95-112 ·
  Investigation Evidence QC (`work_kind=investigate`)=113-115 · Recording the result=116-152 ·
  Explicit Anti-Patterns=153-159 · When it FAILs=160
-->

QC means running things for real and pasting the evidence. There is no "probably fine".

## Table of contents

- The QC level — what each level runs
- The three execution steps
- What to run
- The 120-second cap on smoke and runtime checks
- Investigation Evidence QC (`work_kind=investigate`)
- Recording the result
- Evidence
- Verdict
- When it FAILs

## The QC level — what each level runs

The level is a state key, settled by the USER at step 5c of intake (deep) or at the approval
gate (express). Read it, never assume it:

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/tdq_state.py" get muc_qc
```

Five columns, one row per level (only CÓ/KHÔNG — no ambiguous "as needed" cells): <!-- i18n-allow: canonical cell values in the default language -->

| Mức | DoD | unit test | smoke test | runtime test | QC độc lập (`tdq-qc-tester`) |
|---|---|---|---|---|---|
| `lite` | CÓ | CÓ (vùng chạm) | KHÔNG | KHÔNG | KHÔNG |
| `full` | CÓ | CÓ (trọn suite) | CÓ | KHÔNG | KHÔNG |
| `ultra` | CÓ | CÓ (trọn suite) | CÓ | CÓ | CÓ |

| Loại kiểm | Nghĩa | Chi phí |
|---|---|---|
| DoD | 1 CLI check per DoD line, real output | seconds |
| unit test | repo suite (`vùng chạm` = modules on `Chạm:` lines) | minutes |
| smoke test | main path CLI/`smoke-e2e` in temp dir (<60s) | seconds |
| runtime test | live long-lived hook/server/agent | HANGS |

`muc_qc=off` runs nothing (never offered; quotes user's exact words). **Default/fallback is `full`** (`normalize_muc_qc`): enables Changed-Flow E2E Smoke (`<60s`) while keeping `runtime test` off so slow live hangs never abort QC.

## The three execution steps

This is the whole of Part B of [SKILL.md](../SKILL.md) — moved here so the skill body does not
carry this branch on every call. On entering phase `qc` you **must** read all three steps below
before running the first item; working from memory is banned.

<!-- doc-lint: allow R1 -->
4. **The number of QC items = the number of Definition of Done lines**, plus the four fixed
   items QC-F1→F4. One command-run check per DoD line; beyond the fixed items, add nothing
   that is not in the DoD.
   Details: section `## What to run` in this file. Which of those items actually run comes from
   `muc_qc` — the table in `## The QC level` above. The `tdq-qc-tester` agent runs at `ultra`
   up to `qc.ultra_max_subagents` parallel shards per `tdq-config.json` (default `5`; `0`/`"unlimited"`
   = unbounded); at `full`, call lightweight `tdq-security-reviewer` / `tdq-reviewer` on risky diffs.

5. Follow the **5-step Fresh Evidence Gate**: (1) identify exact user-flow claim, (2) run fresh CLI/E2E/snapshot check after final edit, (3) read exit code + stdout/stderr/console errors, (4) cite fresh counts rather than cached receipts, (5) record PASS/FAIL + untested risk. Write `docs/tdq/qc/<slug>.md` using the `Dev Behavior QC Card` header + DoD table in `## Recording the result`.

6. FAIL → go back to the plan, **no re-approval needed**: add fix tasks to the plan under
   `## QC vòng N — fix` in exactly the shape `- [ ] **QCn.1** <the work> — Test: <check>`, and work <!-- i18n-allow: canonical section name of the plan -->
   them under Part A's rules (red→green, tick immediately). Then rerun the failed item plus any
   item the fix could have broken, plus `tdq_test.py vung-cham`; the full suite (`tron-bo`) runs
   once more only after the LAST fix round. Cap of 3 rounds; over the cap, STOP and
   tell the user (`pause --loai tran-qc`). Never pull the user in mid-way: an item that misses a
   spec threshold is recorded with `lech add` and passes as "PASS (lệch, chờ duyệt)" — it is not a
   FAIL and does not spin the fix loop. (Full version in section `## When it FAILs` of this file.)

Done when: every QC item PASSes and its evidence sits in the qc file.
Next step: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/tdq_state.py" set phase=report`.

## What to run

**The number of QC items = the number of Definition of Done lines in the plan, plus four fixed
items.** Each DoD line gets exactly one check runnable as a command, with the real output
pasted. Drop no DoD line. A DoD line that cannot be checked by command is a defect in the plan:
fix that line to be measurable before doing QC. The four fixed items always run, independent of
the DoD:

- QC-F1 — run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/tdq_meta_gate.py"` (`Auto Meta-Gate`, 1-line PASS/FAIL) and `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/tdq_test.py" smoke-e2e --changed` at `full`/`ultra`. Then run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/tdq_test.py" tron-bo --workers auto --fresh --reuse off` once after the last source edit (`lite`: touched area only). Record real output, `tdq_test.py so` (runs, radius misses), and executed/reused/joined counts; keep long logs on disk and quote failures.
- QC-F2 — touched-area regression: for every `Chạm:` line in the plan, run tests for the <!-- i18n-allow: canonical field name of the plan -->
  module holding the affected node. No test → write `KHÔNG CÓ TEST: <node>` as technical debt (not PASS). <!-- i18n-allow: canonical marker written into the qc file -->
- QC-F3 — architectural constraints: verify every line of "Ràng buộc kiến trúc phải giữ" in spec §5 still holds. <!-- i18n-allow: canonical section name of the spec -->
- QC-F4 — clean code: if source changed, apply the 5 SOLID questions in `skills/tdq-conventions/references/clean-code.md` ONLY when adding/editing classes or architectural layers; for procedural/script edits check 3 items: fail-closed errors, no duplicated logic, and functions <= 50 lines. Any "no" → fix code and record fix. No source edit → `KHÔNG ÁP DỤNG — không sửa file code`. <!-- i18n-allow: canonical marker written into the qc file -->

Add no item outside DoD + `QC-F1..F4` ([ultracode](../../tdq-conventions/references/ultracode.md)). Only when DoD reaches them, check: edges/errors, `TDQ_LOG=1/0` + [vision-test-loop.md](vision-test-loop.md) (`take_snapshot` default), no placeholders ([skill eval](skill-eval.md)), and every `Dùng:` block's `Kiểm` + `Ra` artifact (missing artifact → set spec §3b `KHÔNG` + rerun `doc_lint.py --pair` + `approve spec`). <!-- i18n-allow: canonical field names of the plan -->

## The 120-second cap on smoke and runtime checks

Every smoke or runtime check at `ultra` runs under a **120-second cap per check**. Set it on the
command itself (`timeout=120` in `subprocess.run`, or `timeout 120 <command>` in a shell), never
by watching the clock yourself.

Hitting the cap:

1. Kill the process. A check left running is a turn that never ends — this is the failure mode
   the cap exists for, measured on this repo before the cap existed.
2. Write it up as **FAIL**, with the command, the 120-second cap, and the tail of the output.
   A timeout is never a silent skip and never a PASS.
3. Then work out WHY it hung, and say which of the two it was: a real defect (a deadlock, a
   process waiting on input nobody sends, an infinite loop) or a check that genuinely needs
   longer than two minutes.

**Never raise the cap on your own.** Only when step 3 shows the second case may you ask the user (naming check, measured duration, and proposed cap). Fix hangs; do not widen timeouts.

## Investigation Evidence QC (`work_kind=investigate`)
When `work_kind=investigate`, keep the `lite/full/ultra` table above unchanged for scope depth and run `QC-I1..I4` per [investigate-mode.md](../../tdq-conventions/references/investigate-mode.md); any diff outside `docs/tdq/` re-enables `QC-F1` + `QC-F4`.

## Recording the result

`docs/tdq/qc/<slug>.md`:

<!-- i18n-allow: qc file template written in the default document language -->
```markdown
# QC — <tên việc>
Ngày: YYYY-MM-DD · Plan: ../plan/<slug>.md · Vòng: 1
Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

## Dev Behavior QC Card
- Auto Meta-Gate: PASS/FAIL (<N>/<N> checks, <t>s)
- Luồng đổi: <mô tả luồng người dùng vừa đổi bằng ngôn ngữ đời thường>
- Chạy thử thật (Before → After + Bằng chứng tươi): <lệnh thật, exit code, snapshot/counts>
- Rủi ro còn lại: <vùng ngoài phạm vi hoặc chưa kiểm>

| # | Hạng mục | Lệnh đã chạy | Kết quả | PASS/FAIL |
|---|---|---|---|---|
| Q1 | | | | |

## Bằng chứng
### Q1
```
<output thật, cắt gọn phần dài> <!-- i18n-allow: qc template line in the default document language -->
```

## Lệch spec chờ duyệt <!-- i18n-allow: qc template line in the default document language -->
<chép `tdq_state.py lech list`: Qn · ngưỡng · đo được · phương án đã áp — hoặc "không có"> <!-- i18n-allow: qc template line in the default document language -->

## Kết luận <!-- i18n-allow: qc template line in the default document language -->
<PASS toàn bộ | FAIL: liệt kê hạng mục fail và task fix đã thêm vào plan> <!-- i18n-allow: qc template line in the default document language -->
```

An item that missed its threshold but carries a recorded deviation is written
`PASS (lệch, chờ duyệt)` — not FAIL: the fallback was applied on purpose and only the user can
approve or reject it, which happens in the report.

## Explicit Anti-Patterns

- `ANTI-1 (Fake Red)`: Test failing on syntax error/bad import/wrong path is NOT valid RED.
- `ANTI-2 (Blind Assertion)`: Assertions that cannot fail (`assert True`, empty checks) are banned.
- `ANTI-5 (Raw Dump)`: Pasting test logs >15 lines into chat is banned; summarize outcome.
- `ANTI-6 (False Clean PASS)`: Treating timeout/crash/missing evidence/unverified as PASS is banned (O04); mark FAIL or HOLD/CHỜ.

## When it FAILs

Add `R15-Compact` `- [ ] **QCn.1**` tasks under `## QC vòng N — fix` per [qc-vong-fix.md](qc-vong-fix.md), fix red → green, re-run failed items + `tdq_test.py vung-cham` (`tron-bo` after last round): <!-- i18n-allow -->

4. Repeat until every item PASSes. **Cap of 3 rounds** — over the cap, STOP and tell the user.

Never ask mid-run. A spec threshold the fix cannot reach → `lech add`, mark the item "PASS (lệch, chờ duyệt)", and the report asks the user.
