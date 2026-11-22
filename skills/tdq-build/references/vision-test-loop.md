# User-Scenario-Driven Testing and the Vision Test Loop
<!-- muc-luc-dong:
  Table of contents=13-23 · Trigger decision table=24-36 · Three-tier scenario framework=37-49 ·
  Six banned test anti-patterns (ANTI-1 to ANTI-6)=50-76 ·
  The 6 steps of the Vision Test Loop=77-97 · Bounding box to CSS mapping table=98-109 ·
  Loop caps and Reviewer Sub-agent=110-114 · Human-in-the-loop escalations=115-125 ·
  Self-check=126
-->

Soul: chất lượng > runtime > context cost · luật gốc: ../../tdq-conventions/references/soul.md <!-- i18n-allow: canonical Soul line -->
This reference gives a mechanical, step-by-step runbook so every model tier executes scenario tests and visual verification identically.

## Table of contents

- [Trigger decision table](#Trigger decision table)
- [Three-tier scenario framework](#Three-tier scenario framework)
- [Six banned test anti-patterns (ANTI-1 to ANTI-6)](#Six banned test anti-patterns (ANTI-1 to ANTI-6))
- [The 6 steps of the Vision Test Loop](#The 6 steps of the Vision Test Loop)
- [Bounding box to CSS mapping table](#Bounding box to CSS mapping table)
- [Loop caps and Reviewer Sub-agent](#Loop caps and Reviewer Sub-agent)
- [Human-in-the-loop escalations](#Human-in-the-loop escalations)
- [Self-check](#Self-check)

## Trigger decision table

Default UI mode: verify every web flow first via **Accessibility Tree Snapshot** (`take_snapshot`, `uid`-based `click`/`fill` fail-closed if hidden/disabled, and fail-closed `list_console_messages`). Treat `tdq_vision_diff.py` pixel comparison as **conditional** — run only when a visual reference or CSS layout change applies.

| Reference artifact provided or mentioned | Pixel Loop required? | CLI flag / Action | When artifact is missing or locked |
|---|---|---|---|
| Local mockup image (`.png`, `.jpg`, `.webp`) | YES — CONDITIONAL | `tdq_vision_diff.py --source <path/to/mockup.png>` | Run `pause --loai dau-vao-user` for path | <!-- i18n-allow: canonical pause kind -->
| Wireframe or layout sketch image | YES — CONDITIONAL | `--source <path/to/wireframe.png> --threshold 0.05` | Run `pause --loai dau-vao-user` for wireframe | <!-- i18n-allow: canonical pause kind -->
| Reference screenshot or baseline UI capture | YES — CONDITIONAL | `--source <path/to/screenshot.png>` | Run `pause --loai dau-vao-user` for baseline | <!-- i18n-allow: canonical pause kind -->
| HTML/web prototype or live reference URL | YES — CONDITIONAL | Capture `source.png`, then `--source source.png` | Run `pause --loai dau-vao-user` if unreachable | <!-- i18n-allow: canonical pause kind -->
| Figma link (`https://www.figma.com/...`) | YES — CONDITIONAL | `--figma-url "<url>"` (`FIGMA_TOKEN` from env) | Exit `3` → `pause --loai dau-vao-user` for export | <!-- i18n-allow: canonical pause kind -->
| Functional UI / CSS-unchanged / CLI / backend | NO — SKIP PIXEL DIFF | Use `take_snapshot` + `list_console_messages` default | Select scenarios via [scenario-template](../../tdq-browser-test/references/scenario-template.md) |

## Three-tier scenario framework

Every test in `spec`, `plan`, `implement`, and `qc` must represent a real user journey rather than an implementation detail.
Write each selected scenario using `Given - When - Then`. Map feature/risk to a public entry point, isolated simulation fixture, observable oracle and case ID before adding a test. The tiers are a risk checklist, not a fixed number of cases per feature. Keep security, data-loss and regression negatives even when smoke is over budget. For an absent boundary or failure scenario, state why that risk cannot occur or which existing case covers it; never add a no-op case to fill a quota.

| Tier | Name | Given - When - Then and selection criterion |
|---|---|---|
| Tier 1 | Core User Journey (Happy Path) | **Given** realistic user state and input · **When** the user triggers the public entry point · **Then** the final output and persisted state match the expected result. Select the smallest real journey proving the feature. |
| Tier 2 | Boundary & Edge Scenarios | **Given** a relevant empty, maximum-length, Unicode or concurrent input · **When** the action runs · **Then** state stays intact without crash. Select only boundaries with a plausible distinct failure and oracle. |
| Tier 3 | Failure & Recovery Scenarios | **Given** a reachable timeout, missing token or invalid payload · **When** the call fails · **Then** the error is clear and safe state remains. Keep negative and recovery cases when the failure is reachable. |

Before execution, list selector, mapped feature/risk, reason and expected module count. Run affected tests while implementing; keep one final full fresh suite for deep QC. Do not treat old receipts as a fresh verdict or count joined/reused work as executed.

## Six banned test anti-patterns (ANTI-1 to ANTI-6)

Never write a test that matches any of the six patterns below; `tdq-qc-tester` rejects a task on sight when any `ANTI-*` pattern appears.

| Code | Anti-Pattern name | Mechanical detection rule | Required replacement |
|---|---|---|---|
| `ANTI-1` | Tautological / Mock-Returns-Mock | Mocking the function under test and asserting the mock's own return value | Call the real function or pipeline and assert on the produced output |
| `ANTI-2` | Existence-Only Assertion | Asserting only `is not None`, `True`, or `status == 200` without checking payload fields | Assert exact field values, data structure invariants, and state transitions |
| `ANTI-3` | Happy-Path-Only Bias | Ignoring reachable malformed or missing inputs with distinct risk | Test relevant Tier 2/Tier 3 risks or cite existing coverage; do not add cases solely to fill tiers |
| `ANTI-4` | Source-String / Regex Scraping | Reading `.py` or `.html` source text with `in` or regex instead of executing the code | Import and run the function, CLI, or DOM render and check runtime behavior |
| `ANTI-5` | Implementation-Coupled Spying | Asserting internal private helper call counts instead of public outputs | Assert only on the public return value, files written, or observable side effects |
| `ANTI-6` | Blind Visual / DOM-Only UI Check | Checking `<div class="card">` text without browser snapshot or conditional diff | Default to Accessibility Tree (`take_snapshot` + `uid` fail-closed + console `0` errors); add `tdq_vision_diff.py` conditionally for visual/CSS diffs |

```python
# WRONG (ANTI-1 + ANTI-2 + ANTI-4) — mocks the unit under test and checks only not-None:
def test_bad_report(mocker):
    mocker.patch("tdq_vision_diff.write_reports", return_value={"passed": True})
    result = tdq_vision_diff.write_reports()
    assert result is not None

# RIGHT (Tier 1 + Tier 3) — runs the real function on real images and asserts exact metrics:
def test_real_report_and_missing_token(tmp_path):
    rc = tdq_vision_diff.main(["--figma-url", "https://figma.com/file/abc/x?node-id=1-2",
                               "--dist", str(tmp_path / "d.png"), "--out-dir", str(tmp_path)])
    assert rc == 3  # Tier 3: missing FIGMA_TOKEN returns exit code 3 cleanly
```

## The 6 steps of the Vision Test Loop

When visual parity is required (conditional Layer 2), execute steps 1–6 after passing default Layer 1 (`take_snapshot` + `list_console_messages`):

1. Capture `source.png` and rendered `dist.png` at matching width and height.
2. Run `scripts/tdq_vision_diff.py` to normalize, mask dynamic boxes, draw `[1]`, `[2]`, and emit `.md` + `.html` reports:
   ```bash
   python3 "${PLUGIN_ROOT}/scripts/tdq_vision_diff.py" \
     --source "<path/to/source.png>" --dist "<path/to/dist.png>" \
     --out-dir "docs/tdq/reports/vision-<slug>" --slug "<slug>" \
     --threshold 0.02 --color-tolerance 12 --ignore-boxes "0,0,0,0" --round 1
   ```
   Append `--embed-base64` for a self-contained single-file HTML report.
3. Check exit code and `docs/tdq/reports/vision-<slug>/metrics.json`:
   - `0` (`passed: true`, `mismatch_rate <= threshold`): go to Step 5.
   - `1` (`passed: false`, `mismatch_rate > threshold`): go to Step 4.
   - `3` (`FIGMA_TOKEN` missing or URL locked): run `dau-vao-user` pause below. <!-- i18n-allow: canonical pause kind -->
4. Fix every `[1]`, `[2]` in `diff_highlight.png` + `<slug>.md` via `(x, y, w, h)` and the CSS table below, recapture `dist.png`, bump `--round`, rerun Step 2.
5. Dispatch `tdq-qc-tester` (max **1 feedback round**) for semantic checks (truncation, icons, overlap, contrast).
6. Link `docs/tdq/reports/vision-<slug>/<slug>.md` and `<slug>.html` in QC and Report.

## Bounding box to CSS mapping table

Map each red box `[N]` on `diff_highlight.png` to a DOM/CSS fix:

| Visual symptom inside `[N]` | Root cause | CSS / HTML property |
|---|---|---|
| Thin shifted outline on card/button | Offset spacing or size | `margin`, `padding`, `gap`, `top`, `left`, `box-sizing` |
| Block covers heading/paragraph width | Typography mismatch | `font-size`, `font-weight`, `line-height`, `max-width` |
| Solid red container or badge fill | Surface styling diff | `background-color`, `background-image`, `border-radius`, `border-color` |
| Boxes `[1]`, `[2]`, `[3]` shift together | Parent layout alignment | `display`, `justify-content`, `align-items`, `grid-template-columns` |
| Box covers clock, avatar, or banner | Dynamic region diff | Pass `x,y,w,h` to `--ignore-boxes` |

## Loop caps and Reviewer Sub-agent

- **3 rounds max**: stop after `--round 3`; **early plateau**: stop if improvement `< 0.002` (`0.2%`).
- **1 Reviewer turn**: apply feedback in one pass without re-looping.

## Human-in-the-loop escalations

- Missing reference, locked URL, or exit `3`:
  ```bash
  python3 "${PLUGIN_ROOT}/scripts/tdq_state.py" pause --loai dau-vao-user --ly-do "Missing visual reference or FIGMA_TOKEN for Vision Test Loop"
  ```
- Still above `--threshold` after 3 rounds or plateau:
  ```bash
  python3 "${PLUGIN_ROOT}/scripts/tdq_state.py" pause --loai tran-qc --ly-do "Vision Test Loop reached 3-round cap; see <slug>.html and diff_highlight.png"
  ```

## Self-check

- [ ] Checked Trigger table and [scenario-template](../../tdq-browser-test/references/scenario-template.md) (`e2e_adapter` default `none`)
- [ ] Executed Layer 1 `take_snapshot` + `uid` fail-closed checks + `list_console_messages` (`0` errors) first
- [ ] Selected Tier 1–3 `Given - When - Then` scenarios with zero `ANTI-1..ANTI-6` violations
- [ ] When conditional pixel diff ran: verified `metrics.json`, `diff_highlight.png`, `<slug>.md`, `<slug>.html`, and `[1]`, `[2]` fixed within cap
