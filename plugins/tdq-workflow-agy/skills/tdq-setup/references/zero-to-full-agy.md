# Zero-to-Full Antigravity Setup & Verification Runbook

This reference holds the cross-OS Gate-0 bootstrap, Antigravity host configuration, restart-resume contract, and 6-layer sandbox simulation details referenced by [SKILL.md](../SKILL.md).

## 1. Dual-Entry Consent & State Contract

| Trigger / Mode | Consent Scope | Execution Flow | State Artifact (`${PLUGIN_DATA}`) |
|---|---|---|---|
| `"setupfully tdq-workflow"` | Explicit user-space consent (`0 sudo`) | Phase 1 (`tdq_setup.py --setupfully`) -> prompt IDE restart -> auto `[TDQ:SETUP]` -> `--post-restart-verify` | `tdq-setup-state.json` + `setup-pending.flag` |
| Standard `/tdq-setup` | Prints One-Shot Manifest first (`--scan-json`) | Single user approval (optional Tavily key) -> `--apply-manifest` -> restart -> verify | `tdq-setup-state.json` + `setup-pending.flag` |

- State files stay strictly inside `${PLUGIN_DATA}` (`TDQ_SETUP_STATE_DIR` overrides for isolated tests; `TDQ_KHONG_CHAM_MAY=1` switches writes to in-memory dry-run).
- Optional `TAVILY_API_KEY` is saved via `python3 scripts/tdq_setup.py --set-tavily-key "<key>"` into private `secrets.env` (`0600` on POSIX, user ACL on Windows) and is NEVER echoed in stdout, stderr, logs, or state JSON.
- `scripts/tdq_setup.py` runs in pure Antigravity host context during `/tdq-setup` (`claude_debt_count == 0`) — never modifies `~/.claude.json` or `~/.claude/settings.json`.

## 2. Cross-Platform Gate-0 Bootstrap & Core Stack

Run Gate-0 before Python hooks/CLI if Python `>= 3.10` or Node.js `>= 18` is not on `PATH`:
- **Windows (PowerShell):** `.\scripts\bootstrap.ps1` (probes via Node `scripts/tdq_setup_probe.mjs`, checks `py -3`, `node`, `cargo` / prebuilt `tdq-dispatch.exe`).
- **macOS / Linux:** `./scripts/bootstrap.sh` (runs `scripts/tdq_setup_probe.mjs`, verifies `python3`, `node`, `chmod 0755` launchers, suggests Homebrew / apt / nvm only when missing).

| Component | Purpose | Antigravity Location / Behavior | Verification Check |
|---|---|---|---|
| **3-Tier Search (`agent-lsp`, LS, `graphify`)** | Compiler symbols, blast radius, import roots (`pyrightconfig.json`, `tsconfig.json`) | User binary path + `lsp` entry in `~/.gemini/antigravity/mcp_config.json` | `python3 scripts/tdq_lsp.py check` exits `0` |
| **RTK + ripgrep (`rg`)** | CLI output compression & exact search | User bin path + config via `rtk_integration.py` (Collision Guard safe) | `python3 scripts/tdq_setup.py --check-rtk` |
| **Caveman Token Shrink** | MCP JSON compaction & terse style | Node `scripts/tdq_mcp_launcher.mjs` wraps installed `mcp_config.json` (never `sys.executable`) | `python3 scripts/tdq_setup.py --check-caveman` |
| **Archify HTML Engine** | Interactive spec/plan/report diagrams & Master Map | Auto-cloned from `https://github.com/tt-a1i/archify.git` into `~/.local/share/archify` (Node `>= 18`) | `python3 scripts/tdq_setup.py --kiem-archify` |
| **`~/.gemini/GEMINI.md` Pin** | Global Antigravity rule pointer | Idempotent `TDQ:TOOLS` block kept strictly under `24,000` bytes | `scan_setup_manifest(".")["core"]["gemini_md"]` |
| **Optional Companions** | Visual browser QC & live web search | `chrome-devtools-plugin`, Chrome CDP `9222`, `TAVILY_API_KEY` (`secrets.env`) | Degrades cleanly to `SKIPPED` in Optional Gate |

## 3. IDE Restart Resume & 6-Layer Simulation (`T1`-`T6`)

1. Phase 1 writes `host_fingerprint` (`Host Session Fingerprint`, `< 20 ms` to compute) + `status="awaiting_restart"` + `setup-pending.flag`.
2. In `hooks/rust/tdq-dispatch`, hot events check `setup_pending_flag_exists()` in `O(1)`. While no flag exists, overhead stays `< 50 ms`; when present, `PreInvocation` delegates to Python hooks.
3. On the first prompt after restarting Antigravity, the fingerprint mismatches (or `--confirm-restarted` is supplied), so hooks emit `[TDQ:SETUP]` with a 4-part user card instructing `--post-restart-verify`. Same-PID tabs remind the user to restart without falsely marking verified.
4. `python3 scripts/tdq_setup.py --post-restart-verify --json` invokes `scripts/tdq_simulate_verify.py` inside a self-cleaning `tdq_sim_*` temp sandbox (`< 90s`, real `~/.gemini/config/` and `docs/tdq/state.json` snapshot-unchanged):
   - **T1 Bundle & Gate-0:** `agy plugin validate --strict --json` + `probeToolchain` (`tdq_setup_probe.mjs`).
   - **T2 Hook Latency & Routing:** 6 lifecycle events (`SessionStart`..`Stop`) `< 50 ms` on hot path.
   - **T3 MCP Handshake:** Interactive `Popen` JSON-RPC `initialize` + `tools/list` (`lsp`, `caveman`, optional `tavily-primary`).
   - **T4 3-Tier Search:** Mini Python/TS/Git repo LSP `find_symbol` / `find_references` + `graphify` check.
   - **T5 Add-ons & Archify:** `rtk` / `rg` smoke run + sandbox HTML render in `tdq_sim_*`.
   - **T6 Agents:** Validates 8 agent definitions (`agents/*.md`) and subagent lifecycle hook routing.
5. **Core vs Optional Gates:** `core_gate == "PASS"` clears `setup-pending.flag` and sets `status="verified"` even if `optional_gate == "SKIPPED"`. Missing Chrome or Tavily never fails setup.
6. **Live Closed-Loop Sign-off:** Run 1 real `mcp_tdq-workflow-agy_lsp_*` symbol call and 1 subagent check (`tdq-explorer`) after `--post-restart-verify` returns `verified`.
7. **Logging:** Every setup/verify script emits ISO-8601 stderr + `${PLUGIN_DATA}/logs/` by default (`TDQ_LOG=0` disables both).
