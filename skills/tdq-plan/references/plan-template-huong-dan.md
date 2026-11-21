# Guidance for whoever WRITES the plan

Split out of `plan-template.md` on 2026-10-02. The three sections below are about writing and
self-checking, not about what gets copied into the plan — so they do not belong in context every
time a plan is written. The line-index block at the top of this file gives each section's exact
line range.

## The minute estimate `(eNm)` — six rules, and what it does NOT promise

`eNm` = the number of **minutes** Claude estimates it needs to EXECUTE that task itself (agent
runtime, not human waiting time). The unit is always minutes, an integer 1–999, never `1h` or
`0.5m`. The ETA of the whole plan = the sum of `eNm` over unfinished tasks.

- Score it as you write the task, never score it later.
- Estimate the time spent WORKING, not the time waiting for approval or interview answers.
- Unsure → score the number you actually believe, do not pad for safety.
- `eNm` is **optional**: missing on a task means that task is skipped in the ETA sum, and the
  plan still runs.
- `eNm` changes nothing about the tick rule `[ ] [~] [x]`: a `(e60m)` task ticks like a `(e5m)` one.
- `eNm` is NOT a promise of time to the user — it is the number the report compares to reality.

## The `Mode thực thi` line <!-- i18n-allow: canonical line name of the plan -->

- It MUST sit on **a line of its own**, never merged into another header line — tooling reads it.
- The value here is the **machine identifier**: `main`, `subagent` or `codex`. Which of them the
  machine can actually offer is what `tdq_state.py modes --json` answers; the labels the user
  reads at gate `mode` live in [mode-gate.md](mode-gate.md).
- This is only Claude's **proposal**. After the user approves the plan, phase `mode` asks; the
  mode written into state is the one the user SAID, never the proposal taken as settled. An
  approval sentence that already names a mode skips that gate and goes straight to implement.

## Check before presenting

- Top summary `> **Tóm tắt dễ hiểu:**` sits right under `Trạng thái plan:` so any reader grasps what each phase delivers (Trước → Sau → Kết quả) in 10–15 seconds without technical jargon. <!-- i18n-allow -->
- Every output in spec §2 maps to ≥ 1 task.
- Every task holds exactly one piece of work and one measurable check — no task shaped like
  "finish X".
- The first task of each phase opens a red → green path early.
- No task depends on a task placed after it.

## Adaptive 3-Tier Granularity (`R15-Full` / `R15-Compact` / Sweep)

1. **Full code & config/script changes (`R15-Full`):** Code and rule/config tasks MUST carry the Per-Task Mini-Spec (`Req:`, `Ngoài phạm vi:` / `GIỮ NGUYÊN`, `Chạm:`, `Cần:`, `Giao tiếp:`, `Neo & Công cụ:`, `Trước → Sau:`, `Tiêu chí chấp nhận (EARS):`, `Logic cốt lõi:`, `Ca góc hiểm & Assert:`). <!-- i18n-allow -->
   Keep each task within `<= 30` lines (`<= 35` hard cap). Place shared `Ràng buộc toàn cục` and `Ownership Map` once at top. <!-- i18n-allow -->
2. **Pure doc / template edits & `QCn.x` fix loops (`R15-Compact`):** Use the 5-field compact form (`- [ ] **Tx.y** (eNm) ... — Test: ...`, `Chạm:`, `Neo & Công cụ:`, `Trước → Sau:`, `Tiêu chí & Assert:`) to save context tokens. <!-- i18n-allow -->
3. **Uniform Mechanical Sweep & Signature Sync:** Homogeneous pattern changes use `Uniform Mechanical Sweep` (`<= 6` files) or `dong-bo-chu-ky` (`<= 5` call sites). Any `quick` code task touching `> 4` source files must escalate to `full`.

## 4 Mechanical Safety Anchors for Small Models

1. **Exact Symbol-Span Anchors:** Name enclosing function/class signatures and real symbols verified by `tdq_plan_scaffold.py --files`/`--refs`, not bare guesses.
2. **Strict Tool Directives:** Always specify `Edit` on existing files and `Write` strictly for new files (`CẤM` / ban overwriting existing code with `Write`). <!-- i18n-allow -->
3. **Executable Test Oracles:** Put real input → expected output asserts in `Ca góc hiểm & Assert:` — `ANTI-2` blind assertions (`assert True`, `is not None`) are blocked. <!-- i18n-allow -->
4. **Environment Invariants:** Declare stdlib-only / dependency boundaries upfront under `Ràng buộc toàn cục` and `Ngoài phạm vi:`. <!-- i18n-allow -->
