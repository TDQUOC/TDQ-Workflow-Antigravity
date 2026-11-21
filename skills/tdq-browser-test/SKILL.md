---
name: tdq-browser-test
description: E2E and visual UI/UX verification through Chrome DevTools MCP. Audits DOM structure, viewport responsiveness, element interactions, and console errors.
---

# TDQ Browser Test — Accessibility-First 5-Layer UI Audit
<!-- muc-luc-dong:
  Overview & Anti-Shallow Mandate=20-26 · Five Inspection Layers=27-28 ·
  Layer 1: Structural Tree & Accessibility DOM Audit (Default)=29-33 ·
  Layer 2: Viewport Responsiveness & Conditional Visual Diff=34-37 ·
  Layer 3: Interactive Element States (Fail-Closed by `uid`)=38-41 ·
  Layer 4: Silent Fault Detection (Fail-Closed Console & Network)=42-45 ·
  Layer 5: CSS Cascade & Styling Health=46-49 · Auto-Launch & Session Recovery=50-55 ·
  Reporting Checklist=56
-->

Load [tdq-conventions](../tdq-conventions/SKILL.md), [vision-test-loop](../tdq-build/references/vision-test-loop.md), and [scenario-template](references/scenario-template.md).
Default mode: **Accessibility Tree Snapshot** (`take_snapshot` + fail-closed `uid` actions + `list_console_messages`); treat screenshot pixel diff (`tdq_vision_diff.py`) as **conditional** for visual refs or CSS layout changes.

## Overview & Anti-Shallow Mandate

Never conclude that a web interface passes QC from static HTML or class existence checks.
Every UI task requires live verification through Chrome DevTools MCP using `7-19` line scenarios from [scenario-template](references/scenario-template.md) and a compact Bug Board when defects surface.

Pre-condition: Ensure Chrome runs with Remote Debugging on port 9222: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/tdq_devtool_mcp.py" launch`.

## Five Inspection Layers

### Layer 1: Structural Tree & Accessibility DOM Audit (Default)
1. Call `navigate_page` to the target local or remote URL.
2. Call `take_snapshot` to inspect the live Accessibility Tree (`uid`, roles, labels, and hierarchy).
3. Verify primary regions (Header, Nav, Main, Forms, Actions) are non-empty and addressable by `uid`.

### Layer 2: Viewport Responsiveness & Conditional Visual Diff
1. Resize desktop (`1440x900`) and mobile (`375x812`) via `resize_page`; confirm zero overflow in `take_snapshot`.
2. **Conditional pixel diff**: run `take_screenshot` + `tdq_vision_diff.py` ONLY when visual references (mockup/Figma/baseline) or CSS layout changes apply; skip screenshot diff for non-visual flows.

### Layer 3: Interactive Element States (Fail-Closed by `uid`)
1. Act using snapshot `uid` handles (`click`, `fill`, `fill_form`, `hover`); fail-closed immediately if target `uid` is missing, hidden, disabled, or covered.
2. Re-run `take_snapshot` after state transitions to verify real DOM/aria updates and error/success messages.

### Layer 4: Silent Fault Detection (Fail-Closed Console & Network)
1. Call `list_console_messages` with types `["error", "warn"]`; fail-closed on any unhandled JS error or console error.
2. Call `list_network_requests`; verify zero HTTP 4xx/5xx failures on critical assets or API responses.

### Layer 5: CSS Cascade & Styling Health
1. Call `get_css_styles` on disputed nodes only when Layer 1–4 isolate a styling defect.
2. Check font size, contrast, and `@layer` precedence without broad layout guesswork.

## Auto-Launch & Session Recovery

When Chrome DevTools MCP returns connection refused:
1. Run `python3 scripts/tdq_devtool_mcp.py launch` to start Chrome with `--remote-debugging-port=9222`.
2. Wait 2 seconds for readiness, then resume Layer 1 `navigate_page` + `take_snapshot`.

## Reporting Checklist

- **URL Tested**: target URL and `e2e_adapter` mode (`none` default unless project opted in).
- **Accessibility Tree**: validated `uid` regions and post-action snapshot deltas.
- **Console & Network Status**: `0` console errors and `0` critical HTTP errors.
- **Visual Diff / Bug Board**: skipped or `tdq_vision_diff.py` metrics + Bug Board status (`reproduced`/`verified`/`remaining`).

Done when: Layer 1, 3, and 4 pass fail-closed cleanly (plus conditional Layer 2/5 when applicable) and findings are recorded.
Next step: write QC evidence into `docs/tdq/qc/<slug>.md` or report blockers.
