"""Generate Antigravity-native plugin manifests, hooks.json, mcp_config.json, and 2-tier rules."""
import json
from pathlib import Path
from typing import Dict

from .common_utils import EXCLUDED_SCRIPTS, make_rule_markdown, write_utf8


PLUGIN_VERSION = "0.106.0"


def generate_plugin_json(plugin_root: Path) -> None:
    """Write Antigravity-native plugin.json at plugin root (no userConfig/variables trap)."""
    payload = {
        "name": "tdq-workflow-agy",
        "displayName": "TDQ Workflow (Antigravity)",
        "version": PLUGIN_VERSION,
        "repository": "https://github.com/TDQUOC/TDQ-Workflow-Antigravity",
        "description": (
            "Spec-driven engineering workflow for Google Antigravity: intake -> spec -> plan -> "
            "implement -> QC -> report. Includes 23 [TDQ:*] lifecycle gates, LSP-first 3-tier "
            "search discipline, Chrome DevTools & Archify verification, and 8 domain subagents."
        ),
        "logo": "assets/logo.svg",
        "suggestedPrompts": [
            "/tdq-intake Open a new feature/bugfix/hotfix request under TDQ Workflow",
            "/tdq-check-status Recover or inspect current TDQ request state from disk evidence",
            "/tdq-setup Verify and configure 3-tier search (LSP, Graphify, Chrome DevTools)",
        ],
        "author": {"name": "TDQ"},
        "license": "MIT",
        "keywords": ["tdq-workflow-agy", "tdq-workflow", "spec-driven", "sdd", "lsp", "qc", "hooks", "antigravity"],
    }
    write_utf8(plugin_root / "plugin.json", json.dumps(payload, indent=2, ensure_ascii=False) + "\n")


def generate_logo_svg(plugin_root: Path) -> None:
    """Create crisp SVG icon at assets/logo.svg."""
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 96 96" fill="none">\n'
        '  <defs>\n'
        '    <linearGradient id="tdqGrad" x1="8" y1="8" x2="88" y2="88" gradientUnits="userSpaceOnUse">\n'
        '      <stop offset="0%" stop-color="#0F172A"/>\n'
        '      <stop offset="100%" stop-color="#1E3A8A"/>\n'
        '    </linearGradient>\n'
        '  </defs>\n'
        '  <rect x="4" y="4" width="88" height="88" rx="20" fill="url(#tdqGrad)" stroke="#38BDF8" stroke-width="2.5"/>\n'
        '  <path d="M22 30h52M48 30v38" stroke="#38BDF8" stroke-width="6" stroke-linecap="round"/>\n'
        '  <path d="M26 52l8 8 14-16" stroke="#22C55E" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/>\n'
        '  <circle cx="70" cy="60" r="8" fill="#F59E0B"/>\n'
        '</svg>\n'
    )
    write_utf8(plugin_root / "assets" / "logo.svg", svg)


def _hook_cmd(script_name: str, event_name: str) -> Dict[str, str]:
    """Return cross-platform unquoted Node.js launcher command for hooks.json."""
    _ = script_name
    return {
        "type": "command",
        "command": f"node scripts/tdq_hook_launcher.mjs --event {event_name}",
    }


def generate_hooks_json(plugin_root: Path) -> None:
    """Write top-level Antigravity hooks.json wiring all 6 active lifecycle events via dispatch.py."""
    pre_tool_matchers = (
        "edit_file|write_to_file|write_file|replace_file_content|multi_replace_file_content|notebook_edit",
        "read_file|view_file",
        "run_command",
        "grep_search|find_by_name|list_dir|search_directory|find_file|list_directory",
        "mcp_.*lsp_.*|call_mcp_tool",
        "ask_question|ask_user_question",
        "invoke_subagent|swarm|define_subagent",
    )
    spec = {
        "tdq-session-start": {
            "enabled": True,
            "SessionStart": [_hook_cmd("dispatch.py", "SessionStart")],
        },
        "tdq-pre-invocation": {
            "enabled": True,
            "PreInvocation": [_hook_cmd("dispatch.py", "PreInvocation")],
        },
        "tdq-pre-tool-gates": {
            "enabled": True,
            "PreToolUse": [
                {"matcher": matcher, "hooks": [_hook_cmd("dispatch.py", "PreToolUse")]}
                for matcher in pre_tool_matchers
            ],
        },
        "tdq-post-tool-observe": {
            "enabled": True,
            "PostToolUse": [
                {
                    "matcher": "grep_search|find_by_name|list_dir|search_directory|find_file|list_directory|mcp_.*(lsp|graphify|txtai).*|call_mcp_tool|invoke_subagent|swarm|define_subagent",
                    "hooks": [_hook_cmd("dispatch.py", "PostToolUse")],
                },
            ],
        },
        "tdq-post-invocation": {
            "enabled": True,
            "PostInvocation": [_hook_cmd("dispatch.py", "PostInvocation")],
        },
        "tdq-stop-gate": {
            "enabled": True,
            "Stop": [_hook_cmd("dispatch.py", "Stop")],
        },
    }
    write_utf8(plugin_root / "hooks.json", json.dumps(spec, indent=2, ensure_ascii=False) + "\n")


def generate_mcp_config(plugin_root: Path) -> None:
    """Write portable multi-OS mcp_config.json without personal machine paths."""
    cfg = {
        "mcpServers": {
            "lsp": {
                "command": "node",
                "args": ["${PLUGIN_ROOT}/scripts/tdq_mcp_launcher.mjs", "lsp"],
            },
            "chrome-devtools": {
                "command": "node",
                "args": [
                    "${PLUGIN_ROOT}/scripts/tdq_mcp_launcher.mjs",
                    "npx",
                    "-y",
                    "chrome-devtools-mcp@latest",
                    "--userDataDir=${PLUGIN_DATA}/chrome-devtools-profile",
                ],
            },
            "tavily-primary": {
                "command": "node",
                "args": [
                    "${PLUGIN_ROOT}/scripts/tdq_mcp_launcher.mjs",
                    "npx",
                    "-y",
                    "tavily-mcp@latest",
                ],
            },
        }
    }
    write_utf8(plugin_root / "mcp_config.json", json.dumps(cfg, indent=2, ensure_ascii=False) + "\n")


def generate_two_tier_rules(plugin_root: Path) -> None:
    """Generate Tier-1 AGENTS.md (< 24KB) and Tier-2 glob/model_decision rules/."""
    rules_dir = plugin_root / "rules"
    rules_dir.mkdir(parents=True, exist_ok=True)

    agents_md = """# TDQ Workflow — Google Antigravity Core Rules (Soul & Constitution)

> Soul: **chất lượng > runtime > context cost** <!-- i18n-allow: canonical Soul line --> · Source of Truth: `skills/tdq-conventions/references/soul.md`

## 1. Mandatory Entry & Phase Sequence
- **Every user request MUST begin with `tdq-intake`** (`skills/tdq-intake/SKILL.md`). NEVER switch into harness `EnterPlanMode` on your own (`[TDQ:NO-PLAN-MODE]`).
- Full pipeline: `analyze -> spec -> [approve spec] -> plan -> [approve plan] -> mode -> implement (red -> green per task) -> qc -> report -> [set phase=idle]`.
- Express lane (`quick`): `analyze -> quick_analyze -> mini-plan -> [approve quick] -> implement -> report -> [set phase=idle]`.
- Zero-Popup UI Policy (`ask_question` blocked mid-request): Ask numbered options (`1a 2b 3c`) and receive approvals directly in chat text. Use `--by "<exact user words>"` when recording approvals via CLI.
- All Python helpers use `python3 -X utf8 "<plugin_dir>/scripts/<script>.py"` on macOS/Linux or `py -3 -X utf8 "<plugin_dir>/scripts/<script>.py"` on Windows.

## 2. Clean Code Invariants & 7-Rung `TDQ:GON` Ladder
Before creating any symbol, file, or test: climb the 7-rung ladder (`skills/tdq-build/references/rules/chung.md`):
1. Read exact line ranges (`read_file` with `StartLine`/`EndLine`); never invent signatures or read whole huge files unnecessarily.
2. Delete dead code instead of commenting it out; reuse existing helpers before adding new ones.
3. Keep functions <= 50 lines, shallow nesting with early returns, zero duplicated blocks.
4. No silent fallbacks or swallowed errors — fail closed on invariant checks; surface real diagnostics.
5. **Triage Before Touch** (Clean Architecture Refactor Exemption): understand design intent before editing; do NOT flatten structured layers just to minimize diff lines.
6. Every built artifact MUST include default-on timestamped stderr/file logging (`TDQ_LOG=0` toggles off) and real behavior tests (`red -> green`).
7. Digest cap `<= 1,500 chars` in subagent reports & chat updates; detailed evidence goes to `docs/tdq/reports/<slug>.md` or `docs/tdq/qc/<slug>.md`.

## 3. 3-Tier Search & MCP-First Autonomy
- Start code sessions with `start_lsp` (and `open_document` for TS/JS) to unlock `Grep`/`run_command` search quotas.
- Order: **LSP** (`find_symbol`, `find_references`, `go_to_definition`) -> **Grep/ripgrep** (exact literals) -> **Graphify** (`graphify query`, blast radius).
- **MCP-First**: Check real tool inventory & connectivity before falling back to scripts.
- **LSP-Autonomy**: Decide `--bo-qua-lsp "<reason>"` autonomously for pure doc/research requests; never interrupt the user for LSP permission prompts when diagnostics suffice.
- Never claim `Done` before working log (`docs/workinglog/YYYY-MM-DD.md`), plan ticks (`- [x] **T...**`), real tests, and clean git working tree (only whitelisted docs auto-carry).

## 4. User-Facing Presentation & 6-Symbol Whitelist
- Whitelisted symbols in user-facing blocks: `➤`, `·`, `—`, `→`, `–`, `…` (emojis and box-drawing characters are strictly banned per `user-facing-block-vi-du.md`).
- Default plain-language narrative across `spec`, `plan`, and `report` (chat + top markdown summary): lead with a concise Before -> After -> Result arc anyone grasps in 10-15s without middle-dot packed lines (`user-facing-block.md`).
- Reports require 4 sections: **Before Request**, **After Request**, **What Was Tested**, **Test Result** + Archify HTML (`docs/tdq/reports/<slug>.html`).
- RTK CLI compression: when `rtk` rewrites noisy command output, recover lossless lines via `rtk recall <hash>`; need an explicit unfiltered pass → use `rtk bypass <cmd>`.
- Caveman CCR & Compact Handoff: offload >32 KB data/DOM via `tdq_ccr.py summarize` (lossless `retrieve <id>`); keep subagent notes to `path:line — symbol — note`.
"""
    write_utf8(rules_dir / "AGENTS.md", agents_md)

    lang_specs = [
        ("lang-python.md", "**/*.py", "Python Rules (PEP 8 / UTF-8 / Stdlib & Logging)",
         "- Import `utf8_io` or pass `encoding='utf-8'` on every file open.\n"
         "- Set `creationflags=subprocess.CREATE_NO_WINDOW` on Windows subprocess calls; never use `shell=True` with untrusted inputs.\n"
         "- Annotate boundary functions, keep functions <= 50 lines, wrap atomic writes cleanly with retry on Windows `PermissionError`."),
        ("lang-typescript.md", "**/*.ts, **/*.tsx, **/*.js, **/*.jsx", "TypeScript & JS Rules",
         "- Call `open_document` via LSP before symbol queries on TS/JS projects.\n"
         "- Keep strict types (`no any` in new contracts), validate runtime JSON schemas at module boundaries, dispose listeners cleanly."),
        ("lang-go.md", "**/*.go", "Go Rules",
         "- Handle all returned errors explicitly (`if err != nil`); never discard errors silently with `_`.\n"
         "- Run `go test ./...` per task; keep packages cohesive and race-clean (`-race` in QC)."),
        ("lang-rust.md", "**/*.rs", "Rust Rules",
         "- Avoid `.unwrap()` / `.expect()` in library or production paths; propagate `Result<T, E>` with clear context.\n"
         "- Run `cargo check` and targeted `cargo test` on every task transition."),
        ("lang-csharp.md", "**/*.cs", "C# / .NET Rules",
         "- Respect nullable reference types, `async`/`await` with `CancellationToken` propagation, and `using` disposal for unmanaged handles."),
        ("lang-sql-migration.md", "**/*.sql", "SQL & Migration Safety",
         "- Wrap DDL/data migrations cleanly; never emit destructive `DROP`/`TRUNCATE` without explicit `pha-huy` pause confirmation."),
        ("lang-shell-powershell.md", "**/*.ps1, **/*.sh", "Windows PowerShell 5.1 & Shell Rules",
         "- Prefer PowerShell 5.1 compatible syntax (`;` separators, `[Console]::OutputEncoding = [System.Text.Encoding]::UTF8`, no `&&` assumptions in PS 5.1) or Python stdlib CLIs (`py -3`)."),
    ]
    for fname, globs, title, body in lang_specs:
        content = make_rule_markdown(fname, {"trigger": "glob", "globs": globs}, f"# {title}\n\n{body}")
        write_utf8(rules_dir / fname, content)

    domain_specs = [
        ("domain-mcp-first.md",
         "When choosing tools for web research, browser testing, code navigation, AST architecture diagrams, or external integrations.",
         "Domain Rule: MCP-First & Companion Extensions",
         "- Prioritize MCP tools over shell workarounds: `lsp` (65 tools via agent-lsp), `chrome-devtools` (E2E browser inspection), `tavily-primary` (external web search).\n"
         "- Use Archify (`tdq_archify.py`) for Spec preview & Report HTML manifests, Graphify (`tdq_graphify.py`) for blast-radius graphs, Vision Diff (`tdq_vision_diff.py`) for pixel comparisons, and Codex CLI (`tdq_codex.py`) when `--mode codex` is active."),
        ("domain-git-safety.md",
         "When creating branches, worktrees, commits, merges, or running git cleanup operations in TDQ Workflow.",
         "Domain Rule: Git Isolation & Forbidden Prefixes",
         "- NEVER start branch or worktree names with `claude`, `antigravity`, `gemini`, or `codex`.\n"
         "- NEVER include `Co-Authored-By:` or AI attribution trailers in commit messages.\n"
         "- On Windows, pass `-c core.longpaths=true` when creating deep worktrees under `.tdq-worktrees/`. Only auto-carry clean docs (`docs/**`, `*.md`, `logs/**`, `graphify-out/**`)."),
    ]
    for fname, desc, title, body in domain_specs:
        content = make_rule_markdown(fname, {"trigger": "model_decision", "description": desc}, f"# {title}\n\n{body}")
        write_utf8(rules_dir / fname, content)


def generate_manifest_and_readme(plugin_root: Path, upstream_sha: str) -> None:
    """Write standalone manifest.json and plugin README.md."""
    scripts = sorted(
        f.name for f in (plugin_root / "scripts").glob("*.py")
        if f.name not in EXCLUDED_SCRIPTS
    )
    skills = sorted(d.name for d in (plugin_root / "skills").iterdir() if d.is_dir())
    agents = sorted(f.name for f in (plugin_root / "agents").glob("*.md"))
    manifest = {
        "name": "tdq-workflow-agy",
        "version": PLUGIN_VERSION,
        "host": "antigravity",
        "upstream_commit": upstream_sha,
        "scripts": scripts,
        "skills": skills,
        "agents": agents,
        "mcp_servers": ["lsp", "chrome-devtools", "tavily-primary"],
    }
    write_utf8(plugin_root / "manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    readme = (
        f"# TDQ Workflow (`tdq-workflow-agy`) — Google Antigravity Native Plugin (`v{PLUGIN_VERSION}`)\n\n"
        "Spec-driven engineering workflow compiled for Google Antigravity (`agy`).\n"
        "Forked and improved from upstream [TDQ-Workflow](https://github.com/TDQUOC/TDQ-Workflow.git) (`v0.97.0` @ `b423ee06`). Details: `UPSTREAM-TRACE.md`.\n\n"
        "- **Hooks:** `hooks.json` at plugin root (`SessionStart`, `PreInvocation`, `PreToolUse`, `PostToolUse`, `PostInvocation`, `Stop`).\n"
        "- **Rules:** 2-tier `rules/AGENTS.md` + `rules/lang-*.md` (`glob`) + `rules/domain-*.md` (`model_decision`).\n"
        f"- **Skills ({len(skills)}):** {', '.join(skills)}.\n"
        f"- **Subagents ({len(agents)}):** {', '.join(agents)}.\n"
        "- **MCP:** `lsp` (`agent-lsp`), `chrome-devtools`, `tavily-primary`.\n"
    )
    write_utf8(plugin_root / "README.md", readme)
