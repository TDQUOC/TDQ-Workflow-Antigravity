# TDQ Workflow (`tdq-workflow-agy`) — Google Antigravity Native Plugin (`v0.101.0`)

Spec-driven engineering workflow compiled for Google Antigravity (`agy`).
Forked and improved from upstream [TDQ-Workflow](https://github.com/TDQUOC/TDQ-Workflow.git) (`v0.97.0` @ `b423ee06`). Details: `UPSTREAM-TRACE.md`.

- **Hooks:** `hooks.json` at plugin root (`SessionStart`, `PreInvocation`, `PreToolUse`, `PostToolUse`, `PostInvocation`, `Stop`).
- **Rules:** 2-tier `rules/AGENTS.md` + `rules/lang-*.md` (`glob`) + `rules/domain-*.md` (`model_decision`).
- **Skills (12):** tdq-browser-research, tdq-browser-test, tdq-build, tdq-check-status, tdq-checkportable, tdq-conventions, tdq-intake, tdq-lean, tdq-plan, tdq-setup, tdq-spec, tdq-status.
- **Subagents (6):** tdq-build-resolver.md, tdq-implementer.md, tdq-qc-tester.md, tdq-refactor-cleaner.md, tdq-reviewer.md, tdq-security-reviewer.md.
- **MCP:** `lsp` (`agent-lsp`), `chrome-devtools`, `tavily-primary`.
