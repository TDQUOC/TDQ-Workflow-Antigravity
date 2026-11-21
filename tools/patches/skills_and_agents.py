"""Translate all 12 skills (M01-M20), 8 subagents, and relock token budgets."""
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple

from .common_utils import read_utf8, write_utf8


# Compact M01-M20 terminology replacements preserving token caps (notably qc.md <= 3500 tokens).
M01_M20_REPLACEMENTS: Tuple[Tuple[str, str], ...] = (
    ("~/.claude/CLAUDE.md", "rules/AGENTS.md"),
    ("${CLAUDE_PLUGIN_ROOT}", "${PLUGIN_ROOT}"),
    ("$CLAUDE_PLUGIN_ROOT", "${PLUGIN_ROOT}"),
    ("CLAUDE.md", "AGENTS.md"),
    ("EnterPlanMode", "enter_plan_mode"),
    ("ExitPlanMode", "exit_plan_mode"),
    ("AskUserQuestion", "ask_question"),
    ("UserPromptSubmit", "PreInvocation"),
    ("SubagentStart", "PreInvocation"),
    ("mcp__lsp__", "mcp_tdq-workflow-agy_lsp_"),
    ("mcp__plugin_tdq-workflow_lsp__", "mcp_tdq-workflow-agy_lsp_"),
    ("mcp__chrome-devtools__", "mcp_tdq-workflow-agy_chrome-devtools_"),
    ("mcp__tavily-primary__", "mcp_tdq-workflow-agy_tavily-primary_"),
)

_READONLY_TOOLS: List[str] = [
    "read_file",
    "grep_search",
    "find_by_name",
    "list_dir",
    "call_mcp_tool",
    "run_command",
    "send_message",
]
_WRITER_TOOLS: List[str] = [
    "read_file",
    "edit_file",
    "write_file",
    "grep_search",
    "find_by_name",
    "list_dir",
    "call_mcp_tool",
    "run_command",
    "send_message",
]
_STRICT_READONLY_AGENTS = frozenset({
    "tdq-security-reviewer.md",
})
_SCOPED_INVESTIGATION_AGENTS = frozenset({
    "tdq-reviewer.md",
    "tdq-explorer.md",
    "tdq-debugger.md",
})

# Strictly verified Antigravity 2.0 subagent specs (model in {inherit, flash_lite, flash, pro},
# tools as YAML array of real Antigravity tool names). All 8 inherit session model dynamically.
AGENT_FRONTMATTERS: Dict[str, Dict[str, object]] = {
    "tdq-implementer.md": {
        "name": "tdq-implementer",
        "description": "Implements one assigned task of an approved TDQ plan in an isolated git worktree, red-green, and reports structured handoff data.",
        "tools": _WRITER_TOOLS,
        "model": "inherit",
    },
    "tdq-qc-tester.md": {
        "name": "tdq-qc-tester",
        "description": "Independently verifies an implemented TDQ plan against its Definition of Done - reruns tests, probes edge cases and logging, reports PASS/FAIL with evidence.",
        "tools": _WRITER_TOOLS,
        "model": "inherit",
    },
    "tdq-reviewer.md": {
        "name": "tdq-reviewer",
        "description": "Reviews a TDQ spec or plan file for gaps, contradictions, missing tests, and over-engineering; scoped-write to investigation artifact shards only.",
        "tools": _WRITER_TOOLS,
        "model": "inherit",
    },
    "tdq-security-reviewer.md": {
        "name": "tdq-security-reviewer",
        "description": "Independent security auditor checking code changes for OWASP Top 10, hardcoded secrets, injection vulnerabilities, and least-privilege compliance. Read-only.",
        "tools": _READONLY_TOOLS,
        "model": "inherit",
    },
    "tdq-build-resolver.md": {
        "name": "tdq-build-resolver",
        "description": "Rapid-response subagent fixing compiler errors, build failures, syntax faults, and type check breaks with surgical, minimal diffs.",
        "tools": _WRITER_TOOLS,
        "model": "inherit",
    },
    "tdq-refactor-cleaner.md": {
        "name": "tdq-refactor-cleaner",
        "description": "Code cleaner eliminating dead code, removing duplicates, and enforcing clean code invariants with zero functional regression and deletion audit logs.",
        "tools": _WRITER_TOOLS,
        "model": "inherit",
    },
    "tdq-explorer.md": {
        "name": "tdq-explorer",
        "description": "3-tier codebase explorer mapping callers, symbol definitions, and blast radius across LSP, Graphify, and Grep into compact path:line digests and scoped artifact shards.",
        "tools": _WRITER_TOOLS,
        "model": "inherit",
    },
    "tdq-debugger.md": {
        "name": "tdq-debugger",
        "description": "Adversarial root-cause debugger isolating Point-of-Commitment vs Manifestation with counterfactual falsification tests and scoped artifact shards.",
        "tools": _WRITER_TOOLS,
        "model": "inherit",
    },
}


def _rewrite_skill_text(text: str) -> str:
    """Apply M01-M20 replacements carefully without inflating qc.md above 3,500 tokens."""
    out = text
    for old, new in M01_M20_REPLACEMENTS:
        out = out.replace(old, new)
    # Tool names inside backticks only, avoiding prose corruptions
    tool_subs = (
        ("`Bash`", "`run_command`"),
        ("`Read`", "`read_file`"),
        ("`Edit`", "`edit_file`"),
        ("`Write`", "`write_file`"),
        ("`Grep`", "`grep_search`"),
        ("`Glob`", "`find_by_name`"),
        ("`Task`", "`invoke_subagent`"),
    )
    for old, new in tool_subs:
        out = out.replace(old, new)
    return out


def transform_skills(plugin_root: Path) -> int:
    """Transform all markdown files across the 12 skills cleanly (preserve handoff-schema.json)."""
    skills_dir = plugin_root / "skills"
    changed = 0
    for md in sorted(skills_dir.rglob("*.md")):
        raw = read_utf8(md)
        updated = _rewrite_skill_text(raw)
        if updated != raw:
            write_utf8(md, updated)
            changed += 1
    return changed


def transform_agents(plugin_root: Path) -> int:
    """Rewrite all 8 agents/tdq-*.md to valid Antigravity 2.0 frontmatter & tool names."""
    agents_dir = plugin_root / "agents"
    converted = 0
    for md in sorted(agents_dir.glob("tdq-*.md")):
        meta = AGENT_FRONTMATTERS.get(md.name)
        if not meta:
            continue
        raw = read_utf8(md)
        body = raw
        if raw.startswith("---\n"):
            end = raw.find("\n---\n", 4)
            if end > 0:
                body = raw[end + 5:]
        body = _rewrite_skill_text(body)
        tools_yaml = ", ".join(meta["tools"])  # type: ignore[arg-type]
        fm = (
            "---\n"
            f"name: {meta['name']}\n"
            f"description: {meta['description']}\n"
            f"tools: [{tools_yaml}]\n"
            f"model: {meta['model']}\n"
            "---\n\n"
        )
        # Explicit host enforcement notice matching bash_gate/edit_gate guards.
        if md.name in _STRICT_READONLY_AGENTS:
            body += (
                "\n> **Host Enforcement:** Write tools are omitted and shell mutations "
                "are blocked by TDQ `bash_gate.py` (`[TDQ:READONLY]`).\n"
            )
        elif md.name in _SCOPED_INVESTIGATION_AGENTS:
            body += (
                "\n> **Host Enforcement (`[TDQ:SCOPED-WRITE]`):** Writes are strictly scoped "
                "to assigned shards under `docs/tdq/artifacts/<active_slug>/` (`.md`/`.json`/`.jsonl`, "
                "excluding `evidence*`, `trial_*.json`, `rec_*.json`) and flat `docs/tdq/research/<slug>*.md`. "
                "Source/test/plan/spec/state edits and shell mutations are blocked (`[TDQ:READONLY]`).\n"
            )
        elif md.name == "tdq-qc-tester.md":
            body += (
                "\n> **Host Enforcement:** Writes are strictly scoped to `docs/tdq/qc/*.md` "
                "and source/test/plan/spec/state edits or shell mutations are blocked by TDQ "
                "`edit_gate.py` / `bash_gate.py` (`[TDQ:QC-SCOPED]`).\n"
            )
        write_utf8(md, fm + body.lstrip())
        converted += 1
    return converted


def relock_token_budget(plugin_root: Path) -> int:
    """Run token_budget.py against plugin_root so docs/tdq/token-budget.json is exact."""
    tb_script = plugin_root / "scripts" / "token_budget.py"
    env = dict(os.environ)
    up_venv = Path(r"C:\Users\admin\Documents\Projects\ForAgentCode\TDQ-Workflow\.venv-tokens\Scripts\python.exe")
    if up_venv.is_file() and "TDQ_TOKENS_VENV" not in env:
        env["TDQ_TOKENS_VENV"] = str(up_venv)
    kw = {"capture_output": True, "text": True, "encoding": "utf-8", "timeout": 60, "env": env}
    if os.name == "nt":
        kw["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
    res = subprocess.run([sys.executable, "-X", "utf8", str(tb_script), "--goc", str(plugin_root)], **kw)
    if res.returncode != 0:
        raise RuntimeError(f"token_budget.py failed ({res.returncode}): {res.stderr or res.stdout}")
    check = subprocess.run([sys.executable, "-X", "utf8", str(tb_script), "--kiem", "--goc", str(plugin_root)], **kw)
    if check.returncode != 0:
        raise RuntimeError(f"token_budget --kiem failed:\n{check.stdout}\n{check.stderr}")
    return 0
