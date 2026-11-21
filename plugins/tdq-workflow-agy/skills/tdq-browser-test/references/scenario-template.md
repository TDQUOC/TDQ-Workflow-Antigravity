# Browser Scenario Template, Bug Board & E2E Adapter Policy

Keep every browser scenario and bug card concise, executable, and grounded in Accessibility Tree observables before reaching for screenshots or external runners.

## Concise E2E Scenario Format (`7-19` lines)

Write interactive or release scenarios to `docs/tdq/scenarios/<slug>-<case>.md`. Target `7-19` lines per file (never exceed `40` lines; verified by `scripts/doc_lint.py`).

```markdown
# Scenario: <short user journey title>

- **Feature / Risk:** <public entry point and failure risk>
- **Fixture:** <isolated server/file/seed setup>
- **Oracle:** <Accessibility Tree `uid`/role/text state + console = 0 errors>
- **Adapter:** `none` (default Chrome DevTools MCP `take_snapshot`)

1. **Given:** `navigate_page` opens `<target URL>` cleanly.
2. **When:** `take_snapshot` locates `<control>` by `uid`, then `click`/`fill` acts on it.
3. **Then:** Updated `take_snapshot` confirms `<expected text/role/state>` and `list_console_messages(types=["error"])` returns empty.
```

Rules for scenarios:
- Cite only verified commands and flags when referencing `scripts/*.py` (`doc_lint.py` checks flags against `--help`/AST).
- Require Accessibility Tree Snapshot verification (`take_snapshot`, fail-closed `uid` interaction, `list_console_messages`) by default; add pixel diff (`tdq_vision_diff.py`) conditionally only when layout/CSS or mockup parity is in scope.
- Never invent unprinted timings, counts, or routes; state the actual fixture and command output observed.

## Bug Board (`docs/tdq/bugs/<slug>.md`)

Track defects discovered during exploration, browser QC, or regression sweeps in one compact board before fixing:

```markdown
# Bug Board — <slug>

| ID | Severity | Surface | Status | Evidence |
|---|---|---|---|---|
| B1 | high | `<url or command>` | `reproduced` | `<uid/console error/exit code>` |
| B2 | medium | `<component>` | `verified` | `<rerun snapshot or test output>` |
```

Allowed statuses:
- `reproduced`: isolated steps + failing Accessibility Tree, console, network, or command evidence captured.
- `verified`: root cause fixed and failing scenario re-run passed without relaxing assertions.
- `remaining`: unresolved or blocked with exact exit code / missing dependency noted.

## Opt-In `e2e_adapter` Policy

- **Default `e2e_adapter: none`**: use built-in `tdq-workflow-agy_chrome-devtools` (`take_snapshot`, `click`, `fill`, `list_console_messages`, `list_network_requests`) for zero-install E2E verification.
- **When to opt in**: set `e2e_adapter` (`playwright` / `cypress` / `puppeteer`) only when the target project already declares that runner in its test suite and the spec/plan explicitly calls it.
- **No unrequested installs**: never install a headless framework just to avoid `take_snapshot`, and never trade fail-closed Accessibility Tree checks for weak CSS-selector existence asserts.

Back to [tdq-browser-test](../SKILL.md) and [vision-test-loop](../../tdq-build/references/vision-test-loop.md).
