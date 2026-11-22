---
name: tdq-setup
description: Install and prove every dependency the workflow searches with: 7 rungs from the agent-lsp binary to the import-root config and the graphify graph. Use when opening a request, when a search tool fails, or on a new machine.
---

# TDQ Setup - Zero-to-Full Toolchain & 3-Tier Search

Load [tdq-conventions](../tdq-conventions/SKILL.md).
The search-order rule lives in [references/uu-tien-tim-kiem.md](references/uu-tien-tim-kiem.md) and is binding on every phase. Companion rule section 6 lives in [references/uu-tien-tim-kiem-chi-tiet.md](references/uu-tien-tim-kiem-chi-tiet.md). Cross-OS Gate-0 bootstrap, Antigravity launchers, and restart-verify internals live in [references/zero-to-full-agy.md](references/zero-to-full-agy.md).

## 1. Consent Rule & Dual-Entry Setup Modes

**Default rule:** Never install packages or edit another plugin's files before the user approves. When `--readiness-cache auto` is passed (see [runtime speed](../tdq-build/references/runtime-speed.md)), only static probes may cache; connection, doctor, graph freshness, and effect checks still run live.

Two supported setup entries exist (both pure user-space, `0 sudo`, never reading `~/.claude*` on Antigravity):

1. **Direct `"setupfully tdq-workflow"` command:** Explicit trigger acts as upfront user-space consent. Run `python3 "${PLUGIN_ROOT}/scripts/tdq_setup.py" --setupfully --json`, instruct an Antigravity IDE restart, then run `--post-restart-verify` automatically on `[TDQ:SETUP]` resume.
2. **Standard `/tdq-setup`:** Run `--scan-json` first, print one concise manifest table (core + add-ons + optional Tavily/Chrome), ask ONCE for approval (and optional `TAVILY_API_KEY`), then run `--apply-manifest`.

## 2. Core 7-Rung Search Ladder (`tdq_lsp.py check`)

| Rung | Checks | Fix when missing |
|---|---|---|
| 1 | `agent-lsp` binary on `PATH` | Install user-level `agent-lsp` binary |
| 2 | `lsp` MCP entry in host config | Register `agent-lsp` with language args |
| 3 | Language server per active language (`>= 3` files) | See [references/languages.md](references/languages.md) |
| 4 | Non-interactive tool allowlist / launcher | Configure host MCP launcher cleanly |
| 5 | Conflicting outside plugin hook (`PreToolUse`) | Report path & ask user before backing up/editing |
| 6 | Import-root config (`pyrightconfig.json`, `tsconfig.json`...) | Blocking for Python/TS/Lua/C++; warning for build manifests |
| 7 | `graphify` graph newer than source files | Run `graphify extract . --code-only` (warning only) |

- Rungs 1-4 and blocking Rung 6 gaps return exit `3`; full smoke failure across grep/LSP/graphify returns exit `4`.

## 3. Add-ons, Pins & Optional Companions

- **RTK + ripgrep (`rg`):** Enabled via `--with-rtk` with SHA-256 verification and Collision Guard.
- **Caveman Token Shrink:** Enabled via `--with-caveman`; wraps installed `mcp_config.json` through Node `tdq_mcp_launcher.mjs` (never `sys.executable`).
- **Archify & Global Pin:** Clones `archify` into `~/.local/share/archify` if absent; updates idempotent `TDQ:TOOLS` block in `~/.gemini/GEMINI.md` strictly `< 24,000` bytes.
- **Optional Companions (`Optional Add-on Gate`):** `chrome-devtools-plugin` (see [references/chrome-devtools-mcp-guide.md](references/chrome-devtools-mcp-guide.md), [references/mcp-first-guide.md](references/mcp-first-guide.md)) and `TAVILY_API_KEY` (`--set-tavily-key "<key>"`, written to private `secrets.env`, never echoed). Missing Chrome or Tavily logs `SKIPPED` and NEVER blocks `Core Gate`.

## 4. Post-Restart Verify & Closed-Loop Check

1. Phase 1 persists `status="awaiting_restart"`, `Host Session Fingerprint`, and `setup-pending.flag` in `${PLUGIN_DATA}`.
2. After restarting Antigravity, `[TDQ:SETUP]` fires automatically; execute `python3 "${PLUGIN_ROOT}/scripts/tdq_setup.py" --post-restart-verify --json` (add `--confirm-restarted` only when verifying inside an unbroken process).
3. `tdq_simulate_verify.py` validates 6 layers (`T1` bundle+Gate-0, `T2` hooks `< 50 ms`, `T3` JSON-RPC MCP `initialize`/`tools/list`, `T4` mini LSP+Graphify, `T5` RTK+Archify HTML, `T6` 8 agents+subagent hook) in a self-cleaning `tdq_sim_*` sandbox (`< 90s`).
4. Close the loop live with 1 `mcp_tdq-workflow-agy_lsp_*` symbol query (`find_references` / `find_symbol`) and 1 subagent check (`tdq-explorer`) when claiming full readiness.
5. On a machine without Python/Node yet, bootstrap Gate-0 first per [references/zero-to-full-agy.md](references/zero-to-full-agy.md).

Done when: `Core Gate == "PASS"` in `--post-restart-verify`, `tdq_lsp.py check` exits `0`, and `setup-pending.flag` is cleared.
Next step: Return to the calling phase (phase does not change) and route search calls per [references/uu-tien-tim-kiem.md](references/uu-tien-tim-kiem.md).
