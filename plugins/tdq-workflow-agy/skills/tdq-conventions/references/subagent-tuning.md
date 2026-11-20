# Choosing model & effort for a sub-agent

Goal: on every agent call, pick the "just enough" tier — do not burn Opus on wrapping a script,
do not force Haiku into work that needs deep reasoning.

## Two knobs, two different scopes

| Knob | Set where | Changeable at call time? |
|---|---|---|
| `model` | agent frontmatter (default) **and** the Agent tool's `model` parameter at call time | **Yes** — the call parameter overrides frontmatter |
| `effort` | **only** agent frontmatter (`low\|medium\|high\|xhigh\|max`) | **No** — the Agent tool has no `effort` parameter yet |

So: `effort` is a FIXED property of the role; `model` is the knob you turn per task.

## Defaults per role (already written into frontmatter)

| Agent | model | effort | Why |
|---|---|---|---|
| `tdq-implementer` | inherit | high | writes real code, red→green, commits worktree before handoff |
| `tdq-qc-tester` | inherit | high | suspicious DoD verification, scoped writes under `docs/tdq/qc/` |
| `tdq-reviewer` | inherit | high | finding semantic gaps/contradictions and plan resource parity |
| `tdq-security-reviewer` | inherit | high | diff-first security audit (OWASP, secrets, SCA, least privilege) |
| `tdq-build-resolver` | inherit | high | minimal surgical diffs for compiler, syntax, and type check breaks |
| `tdq-refactor-cleaner` | inherit | high | safe dead code removal, deduplication, and clean code invariants |
| `tdq-explorer` | inherit | high | read-only 3-tier LSP/Graphify/Grep reconnaissance with `path:line` map |
| `tdq-debugger` | inherit | high | read-only root-cause reproduction and trace isolation for escalations |
| `general-purpose` (research) | sonnet | medium | runs Tavily broadly, synthesises shallowly; no frontier needed |

`inherit` = follow the model the user has on in the main session. On Google Antigravity 2.0, `agents/*.md` keep `model: inherit` as the safe baseline so the orchestrator can allocate `model` dynamically per task without hardcoded downgrades.

## Google Antigravity 2.0 Model & Effort Ladder (`tdq-config.json`)

The canonical ladder lives in `tdq-config.json` (`scripts/tdq_config.py`): `gemini-3.8-flash` (Tier 1) → `gemini-4-hydrogen` (Tier 2) → `gemini-4-neon` (Tier 3) → `gemini-4-carbon` (Tier 4).

| Tier & Family | `invoke_subagent` `Model` | `swarm` Model + Effort IDs | Recommended Roles / Triggers |
|---|---|---|---|
| Tier 1 (`gemini-3.8-flash`) | `flash` / `flash_lite` | `gemini-3.8-flash-{low,medium,high}` | Fast read-only scans (`tdq-explorer`), trivial mechanical fixes |
| Tier 2 (`gemini-4-hydrogen`) | `inherit` | `gemini-4-hydrogen-{low,medium,high,xhigh}` | Standard implementation (`tdq-implementer`), `tdq-refactor-cleaner`, `tdq-build-resolver` |
| Tier 3 (`gemini-4-neon`) | `inherit` / `pro` | `gemini-4-neon-{low,medium,high,xhigh}` | Deep reasoning: Rust/hooks, `tdq-reviewer`, `tdq-debugger`, `tdq-qc-tester` (`ultra` shards) |
| Tier 4 (`gemini-4-carbon`) | `pro` | `gemini-4-carbon-{low,medium,high}` | Security audits (`tdq-security-reviewer`) and auto-escalation after 2 failed retries |

Note: `invoke_subagent` exposes `Model` (`inherit | flash_lite | flash | pro`) only and inherits session effort via `inherit`. Use `swarm` model IDs when targeting explicit `-low`/`-medium`/`-high`/`-xhigh` effort pairs, and follow user overrides recorded in the approved plan's `## Phân bổ Model & Effort` table.

## Rule for overriding `model` at call time (Agent tool parameter)

Turn it per task, in order — stop at the first matching row:

| If the task is | Pass `model` |
|---|---|
| Purely mechanical: run one command, read one file, return it verbatim | `haiku` |
| Search/read broadly then summarise, deciding nothing | `sonnet` |
| Writing code, fixing logic, design, review, QC | leave empty (keep the agent's default) |
| The hardest task of the plan, or one that already failed once on a lower model | `opus` |

Record the reason for an override in the working log whenever you deviate from the default —
one line is enough.

## Warning about `effort`

Frontmatter `effort` **overrides** the session's effort level (the env var still beats both).
Setting `effort: low` on an agent that does quality work means that agent thinks shallowly EVEN
WHEN the user has the session on `high`. Only set `low` on purely mechanical agents.

Making effort genuinely vary per task would require splitting each agent into several variants —
considered and REJECTED (spec 2026-08-04-workflow-linh-hoat §3): twice the files, easy to drift.

## Read-only sub-agents in any phase

The main agent may open research/analysis sub-agents in any phase, one job per sub-agent, several
in one batch. Each writes its findings under `docs/` (e.g. `docs/tdq/research/<slug>.md`) and
returns a short digest; the main agent decides and edits. A sub-agent never changes the project
before phase `implement`, and in implement only inside its task's `Chạm:` — `edit_gate` denies <!-- i18n-allow: canonical plan field name -->
both with `TDQ:TEAM`. Prefer agent types without Edit/Write (`Explore`, `Plan`, `tdq-reviewer`).

## Sources

- https://code.claude.com/docs/en/sub-agents — frontmatter field table (`model`,
  `effort`; plugin subagents only ignore `permissionMode`/`mcpServers`/`hooks`). Checked 2026-08-04.
- https://code.claude.com/docs/en/model-config — effort precedence: env var >
  frontmatter (when the agent is active) > session level > model default. Checked 2026-08-04.
- https://github.com/anthropics/claude-code/issues/43083 — the Agent tool has no `effort`
  parameter yet (open feature request). Checked 2026-08-04.
