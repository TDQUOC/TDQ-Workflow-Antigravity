# Chrome DevTools MCP Setup & Antigravity Browser Guide

This reference summarizes Chrome DevTools MCP setup via `scripts/tdq_devtool_mcp.py` across Google Antigravity and Claude Code.

## 1. Architecture & Optional Gate Behavior

```text
Host Agent <--(stdio / plugin MCP)--> chrome-devtools-mcp <--(CDP 127.0.0.1:9222)--> Chrome (Isolated Profile)
```

- On Google Antigravity, `chrome-devtools` is served via `chrome-devtools-plugin` (or optional `chrome_devtools` server config) using an isolated user data directory (`${PLUGIN_DATA}/chrome-devtools-profile`).
- Under `tdq-setup`, Chrome & `chrome-devtools-plugin` belong to the **Optional Add-on Gate**: when absent or offline, verification records `SKIPPED` cleanly without blocking the `Core Gate`.

## 2. Host Registration

- **Antigravity:** Install/enable `chrome-devtools-plugin` via Antigravity Plugins or use `scripts/tdq_mcp_launcher.mjs chrome_devtools` with `--isolated`. Probe with `python3 scripts/tdq_devtool_mcp.py status`.
- **Claude Code / Generic stdio:** Register `chrome-devtools` in `~/.claude.json` running `npx -y chrome-devtools-mcp@latest --browserUrl=http://127.0.0.1:9222` and add `"mcp_tdq-workflow-agy_chrome-devtools_*"` / `"mcp__chrome_devtools__*"` to `permissions.allow` in `~/.claude/settings.json`.

## 3. Isolated Chrome Launch (Zero Personal Profile Mutation)

- Automated setup NEVER closes personal Chrome windows or overwrites personal profiles.
- Launch a dedicated debug instance via `python3 scripts/tdq_devtool_mcp.py launch` (defaults to port `9222` with `--user-data-dir` set to an isolated profile and `--remote-allow-origins=*`).

## 4. Troubleshooting

| Symptom | Cause | Resolution |
|---|---|---|
| `ECONNREFUSED 127.0.0.1:9222` | Debug Chrome instance is not running | Run `python3 scripts/tdq_devtool_mcp.py launch` |
| Profile lock error | Stale debug Chrome process holds lock | Close only the dedicated debug Chrome window |
| Missing plugin in Antigravity | `chrome-devtools-plugin` not installed | Optional Add-on Gate skips cleanly; install in Plugins UI if UI audit needed |
| Repeated permission prompts | Wildcard tool rule missing | Add `"mcp_tdq-workflow-agy_chrome-devtools_*"` to host allowlist |
