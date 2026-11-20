# QC — quality control
<!-- muc-luc-dong:
  Table of contents=12-23 · The QC level — what each level runs=24-59 ·
  The three execution steps=60-90 · What to run=91-124 ·
  The 120-second cap on smoke and runtime checks=125-142 ·
  Investigation Evidence QC (`work_kind=investigate`)=143-145 · Recording the result=146-176 ·
  Explicit Anti-Patterns=177-183 · When it FAILs=184
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

Five columns, one row per level. Every cell is CÓ or KHÔNG — a cell reading "as needed" is a <!-- i18n-allow: canonical cell values in the default language -->
cell each turn reads differently, which is what the key exists to end:

| Mức | DoD | unit test | smoke test | runtime test | QC độc lập (`tdq-qc-tester`) |
|---|---|---|---|---|---|
| `lite` | CÓ | CÓ (vùng chạm) | KHÔNG | KHÔNG | KHÔNG |
| `full` | CÓ | CÓ (trọn suite) | KHÔNG | KHÔNG | KHÔNG |
| `ultra` | CÓ | CÓ (trọn suite) | CÓ | CÓ | CÓ |

What the four kinds mean here, so nobody has to guess:

| Loại kiểm | Nghĩa | Chi phí điển hình |
|---|---|---|
| DoD | one command per Definition-of-Done line, real output pasted | seconds |
| unit test | the repo's own suite — `vùng chạm` = only the modules on the plan's `Chạm:` lines | minutes |
| smoke test | the main path end to end through the real CLI, in a temp dir | seconds |
| runtime test | a real long-lived process: a hook inside a live session, a server, a background agent | the one that HANGS |

`muc_qc=off` runs nothing and is never offered in a question; the qc file then holds exactly one
line quoting the user's own words. The level only sizes QC — it never excuses a red test, a
known bug, or a missing fix.

**The default is `full`, and every unreadable value lands there too** (`normalize_muc_qc`), so a
typo can never quietly buy a cheaper QC. `full` deliberately holds no runtime test: measured on
this repo, runtime checks are the ones that hang, and a QC round that hangs gets abandoned —
which costs more coverage than it buys.

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

5. Write `docs/tdq/qc/<slug>.md`: each DoD item → PASS/FAIL with **evidence** (the command plus
   its real output). Assert nothing you have not run. (File template in section
   `## Recording the result` of this file.)

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

- QC-F1 — at `full`/`ultra`, run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/tdq_test.py" tron-bo --workers 1 --fresh --reuse off` once after the last source edit. At `lite`, use touched-area tests only, per the level table. Record real results, `tdq_test.py so` (run count, radius misses), and separate executed/reused/joined counts. Earlier receipts are not final verdicts. A radius miss is a failed module never selected by `vung-cham`. For long suites, keep output in a log and quote failures.
- QC-F2 — touched-area regression: for every `Chạm:` line in the plan, run the tests of the <!-- i18n-allow: canonical field name of the plan -->
  module holding the affected node. A node with no test → write `KHÔNG CÓ TEST: <node>` into the <!-- i18n-allow: canonical marker written into the qc file -->
  QC file; that is technical debt to raise in the report and must not count as PASS.
- QC-F3 — architectural constraints: every line of the "Ràng buộc kiến trúc phải giữ" block in <!-- i18n-allow: canonical section name of the spec -->
  spec §5 is one check that the change did not break that line.
- QC-F4 — clean code: if this turn changed a source file, answer the 5 questions in the
  `## Self-check` section of `skills/tdq-conventions/references/clean-code.md` and record each
  yes/no answer in the qc file. Any "no" → fix the code and record what was fixed, never fix the
  answer. No source file touched → write `KHÔNG ÁP DỤNG — không sửa file code`. <!-- i18n-allow: canonical marker written into the qc file -->

Beyond the items above, add no item that is not in the DoD. Ultracode: [contract](../../tdq-conventions/references/ultracode.md).

The things below run only when the DoD reaches them:

- Edges/errors: empty, wrong type, missing file, permission/network failure.
- Log service: on by default, timestamped, switchable off/down through config; visual & 3-tier scenario checks per [vision-test-loop.md](vision-test-loop.md).
- No placeholders; eval is opt-in ([skill eval](skill-eval.md)).
- Skill contract: for EVERY `Dùng:` block in the plan, run the command in its `Kiểm` field; the <!-- i18n-allow: canonical field names of the plan -->
  artifact in its `Ra` field must exist. No artifact → change that spec §3b line to `KHÔNG` plus <!-- i18n-allow: canonical verdict value -->
  a closing reason, then rerun
  `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/doc_lint.py" --pair <spec> <plan>` until it exits 0.
  Editing §3b edits the spec's CONTENT, so the sha still shifts and the hook still demands
  re-approval — by design: changing a capability verdict changes intent, so the user must be
  asked. Present the one-line diff and ask `approve spec` inside QC. Header lines do not shift sha, and §6 holds conditions rather than commands.

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
