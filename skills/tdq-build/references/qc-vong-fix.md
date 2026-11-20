# QC Fix-Loop Protocol (`QCn.x` · `R15-Compact` · Sweep)

Use this protocol whenever QC fails (`FAIL`). Main QC rules and DoD recording stay in `qc.md`.

## Fix-Round Budget (`<= 3` rounds before escalation)
- Limit repair loops to `3` rounds (`QC1.x`, `QC2.x`, `QC3.x`). If failures persist after round 3, stop and report the blocker to the user.
- Re-run ONLY the failing DoD items plus affected regression scope while fixing (`vung-cham`); run a full verification pass once all items return PASS.

## Compact Repair Task Format (`R15-Compact` · 5 fields)
Append fix tasks in the active phase or repair section using exact `QCn.x` IDs and compact `5`-field blocks so context stays lean (`R15-Compact`):
<!-- i18n-allow: canonical plan task field names -->
```markdown
- [ ] **QC1.1** (e6m) Fix `<root cause>` in `<src/file.py>` — Test: `<exact failing test cmd>`
  - Chạm: `<src/file.py>`, `<tests/test_x.py>`
  - Sinh ra: `<optional new artifact>`
  - Neo & Công cụ: `Edit` on `<src/file.py>` at `<symbol()>` (`Write` only for new file)
  - Trước → Sau: `<failing state> → <fixed invariant>`
  - Tiêu chí & Assert: `<concrete assertion proving defect closed>`
```

## File Isolation & Mechanical Sweeps
- Keep every `QCn.x` `Chạm:` list isolated by file if fixing in parallel waves (`tdq_team.py assign`). <!-- i18n-allow -->
- If a fix creates new helper/fixture files, declare them under `Sinh ra:` so `--verify-plan` and downstream tasks resolve them. <!-- i18n-allow -->
- For identical repetitive edits across `<= 6` files, tag `Uniform Mechanical Sweep` (or `dong-bo-chu-ky` for `<= 5` call sites).
- Re-tick `[x] QC1.1` immediately after its targeted test passes green.
