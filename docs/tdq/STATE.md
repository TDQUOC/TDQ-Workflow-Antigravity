# TDQ STATE (generated — do not hand-edit)
Updated: 2026-11-25T16:13:52+07:00 · Project: C:\Users\admin\Documents\Projects\TDQ-Workflow-Antigravity · schema 3

| Field | Value |
|---|---|
| Request | 2026-11-25-1439-paperclip-tdq-integration-sim |
| Work kind | investigate |
| Lane | full |
| Phase | report |
| Spec | docs/tdq/spec/2026-11-25-1439-paperclip-tdq-integration-sim.md — ✔ approved |
| Plan | docs/tdq/plan/2026-11-25-1439-paperclip-tdq-integration-sim.md — ✔ approved |
| Quick approval | (not applicable) |
| Doc language | vi |
| Lean level | full |
| QC level | ultra |
| Run mode | main |

## Where we are
QC has PASSed. Forbidden: Committing or pushing before the user asks for it.

## What comes next
Write docs/tdq/reports/<slug>.html + Markdown: before/after state & flow, what was tested & actual test results; ask about commit.
```
python3 scripts/tdq_state.py set phase=idle
```
Done when: The report is written and the user has been asked about committing

> Write state only through `python3 scripts/tdq_state.py …`. Unsure where you stand → run `tdq_state.py next`.
