"""Single-process Antigravity 2.0 hook dispatcher and gate_guidance deployment."""
from pathlib import Path

from .common_utils import read_utf8, write_utf8

DISPATCH_PY = r'''#!/usr/bin/env python3
"""Single-process Antigravity 2.0 lifecycle hook dispatcher.

Routes SessionStart, PreInvocation, PreToolUse, PostToolUse, PostInvocation, and
Stop events in-process without spawning child Python interpreters.

Env: TDQ_PROJECT_DIR anchors project root; TDQ_LOG=0 mutes stderr logs.
"""
from __future__ import annotations

import importlib
import json
import os
import re
import sys
import time
from datetime import datetime

_HERE = os.path.dirname(os.path.abspath(__file__))
_PLUGIN_ROOT = os.path.dirname(os.path.dirname(_HERE))
_SCRIPTS_DIR = os.path.join(_PLUGIN_ROOT, "scripts")
for _path in (_SCRIPTS_DIR, _HERE):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import utf8_io  # noqa: E402,F401
import _common  # noqa: E402

_EDIT_TOOLS = frozenset({
    "edit_file",
    "write_to_file",
    "write_file",
    "replace_file_content",
    "multi_replace_file_content",
    "notebook_edit",
    "Edit",
    "Write",
    "MultiEdit",
    "NotebookEdit",
})
_READ_TOOLS = frozenset({"read_file", "view_file", "Read"})
_CMD_TOOLS = frozenset({"run_command", "Bash", "PowerShell"})
_SEARCH_TOOLS = frozenset({
    "grep_search",
    "find_by_name",
    "list_dir",
    "search_directory",
    "find_file",
    "list_directory",
    "Grep",
})
_ASK_TOOLS = frozenset({"ask_question", "ask_user_question", "AskUserQuestion"})
_SUBAGENT_TOOLS = frozenset({
    "invoke_subagent",
    "swarm",
    "define_subagent",
    "Task",
    "Agent",
})
_MCP_LSP_RE = re.compile(r"^(?:mcp_.*lsp_.*|mcp__lsp__|lsp\.)", re.IGNORECASE)
_MCP_ANY_RE = re.compile(r"^mcp_", re.IGNORECASE)

_PRETOOL_TABLE = (
    (_EDIT_TOOLS, "edit_gate"),
    (_READ_TOOLS, "read_gate"),
    (_SEARCH_TOOLS, "search_gate"),
    (_ASK_TOOLS, "ask_gate"),
    (_SUBAGENT_TOOLS, "subagent_dispatch_gate"),
)


def _log_enabled() -> bool:
    return os.environ.get("TDQ_LOG", "1") != "0"


def _log_dispatch(event: str, tool: str, decision: str, elapsed_ms: float) -> None:
    """Emit one ISO-timestamped stderr telemetry line unless TDQ_LOG=0."""
    if not _log_enabled():
        return
    stamp = datetime.now().isoformat(timespec="seconds")
    print(
        f"[{stamp}] dispatch event={event} tool={tool} decision={decision} ms={elapsed_ms:.1f}",
        file=sys.stderr,
    )


def _log_error(target: str, exc: Exception) -> None:
    """Log an unexpected in-process gate failure without breaking the hook call."""
    if not _log_enabled():
        return
    stamp = datetime.now().isoformat(timespec="seconds")
    print(
        f"[{stamp}] dispatch error target={target} err={type(exc).__name__}: {exc}",
        file=sys.stderr,
    )


def _parse_event(argv: list[str] | None = None) -> str:
    """Extract `--event <EventName>` flag from argv cleanly without argparse overhead."""
    args = list(argv if argv is not None else sys.argv[1:])
    for idx, tok in enumerate(args):
        if tok == "--event" and idx + 1 < len(args):
            return str(args[idx + 1]).strip()
    return ""


def _read_stdin_json() -> dict:
    """Read stdin JSON fail-open; return empty dict on invalid or non-object payloads."""
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw and raw.strip() else {}
        return data if isinstance(data, dict) else {}
    except Exception as exc:  # noqa: BLE001
        _log_error("stdin", exc)
        return {}


def _run_module(mod_name: str, argv: list[str] | None = None) -> None:
    """Import mod_name lazily and execute main(), catching SystemExit fail-open."""
    try:
        mod = importlib.import_module(mod_name)
        entry = getattr(mod, "main", None)
        if callable(entry):
            entry(argv) if argv is not None else entry()
    except SystemExit:
        pass
    except Exception as exc:  # noqa: BLE001
        _log_error(mod_name, exc)


def _is_mcp_tool(raw_name: str, norm_name: str) -> bool:
    if raw_name == "call_mcp_tool":
        return True
    if _MCP_LSP_RE.match(raw_name) or _MCP_LSP_RE.match(norm_name):
        return True
    return bool(_MCP_ANY_RE.match(raw_name) or _MCP_ANY_RE.match(norm_name))


def _route_pre_tool_use(norm: dict) -> None:
    """Dispatch PreToolUse in-process according to normalized and raw tool names."""
    raw_name = str(_common._RUNTIME_STATE.get("raw_tool_name") or "")
    tname = str(norm.get("tool_name") or "")

    for tool_set, mod_name in _PRETOOL_TABLE:
        if tname in tool_set:
            _run_module(mod_name)
            return

    if tname in _CMD_TOOLS:
        _run_module("command_gate")
        if _common._RUNTIME_STATE.get("deny_reason") is None:
            cmd = str((norm.get("tool_input") or {}).get("command") or "").lower()
            if "graphify" in cmd:
                _common._RUNTIME_STATE["collapsed_payload"] = dict(norm)
                _run_module("search_observe")
        return

    if _is_mcp_tool(raw_name, tname):
        _run_module("lsp_gate")
        if _common._RUNTIME_STATE.get("deny_reason") is None:
            _common._RUNTIME_STATE["collapsed_payload"] = dict(norm)
            _run_module("search_observe")


def _route_pre_invocation(norm: dict) -> None:
    """Run prompt_context and record prompt tokens via search_observe when present."""
    _run_module("prompt_context")
    if (
        norm.get("prompt")
        and "tool_name" not in norm
        and _common._RUNTIME_STATE.get("new_user_turn", True)
    ):
        _common._RUNTIME_STATE["collapsed_payload"] = dict(norm)
        _run_module("search_observe")


def _route_post_tool_use(norm: dict) -> None:
    """Route PostToolUse subagent completions to subagent_stop and others to search_observe."""
    if str(norm.get("tool_name") or "") in _SUBAGENT_TOOLS:
        _run_module("subagent_stop", argv=["--event", "PostToolUse"])
        return
    _run_module("search_observe")


def _route_stop(norm: dict) -> None:
    """Dispatch Stop gate while preserving continuationActive telemetry state."""
    if norm.get("continuationActive") or norm.get("continuation_active"):
        _common._RUNTIME_STATE["continuation_active"] = True
    _run_module("stop_gate")


def route_event(event: str, payload: dict) -> dict:
    """Normalize payload once, execute target hook modules in-process, and return AGY JSON."""
    raw = payload if isinstance(payload, dict) else {}
    ev = str(event or raw.get("hookEventName") or raw.get("hook_event_name") or "").strip()
    norm = _common.normalize_payload(raw, event=ev or None)
    _common._RUNTIME_STATE["collapsed_payload"] = dict(norm)
    try:
        if ev == "SessionStart":
            _run_module("session_start")
        elif ev == "PreInvocation":
            _route_pre_invocation(norm)
        elif ev == "PreToolUse":
            _route_pre_tool_use(norm)
        elif ev == "PostToolUse":
            _route_post_tool_use(norm)
        elif ev == "PostInvocation":
            _run_module("post_invocation")
        elif ev == "Stop":
            _route_stop(norm)
        elif ev == "SubagentStop":
            _run_module("subagent_stop", argv=["--event", "SubagentStop"])
    finally:
        _common._RUNTIME_STATE["collapsed_payload"] = None

    out = _common.build_agy_response()
    _common._RUNTIME_STATE["flushed"] = True
    return out


def _decision_label(event: str, out: dict) -> str:
    """Return compact telemetry label summarizing hook output."""
    if not isinstance(out, dict):
        return "allow"
    if "decision" in out:
        return str(out["decision"])
    if "injectSteps" in out:
        return "inject"
    if event == "PostToolUse":
        return "ok"
    return "noop"


def _extract_tool_label(raw: dict) -> str:
    """Extract concise tool name for stderr dispatch logging."""
    raw_name = str(_common._RUNTIME_STATE.get("raw_tool_name") or "")
    if raw_name:
        return raw_name
    tc = raw.get("toolCall") if isinstance(raw.get("toolCall"), dict) else {}
    return str(tc.get("name") or raw.get("toolName") or raw.get("tool_name") or "-")


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for single-process Antigravity hook execution."""
    t0 = time.perf_counter()
    event = _parse_event(argv)
    raw = _read_stdin_json()
    if not event and raw.get("hookEventName"):
        event = str(raw["hookEventName"])
    out = route_event(event, raw)
    sys.stdout.write(json.dumps(out, ensure_ascii=False) + "\n")
    sys.stdout.flush()
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    _log_dispatch(event or "-", _extract_tool_label(raw), _decision_label(event, out), elapsed_ms)
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''


def apply_dispatch(hooks_scripts_dir: Path) -> None:
    """Copy gate_guidance.py, gate_guidance.json and write dispatch.py into hooks_scripts_dir."""
    hooks_scripts_dir.mkdir(parents=True, exist_ok=True)
    patches_dir = Path(__file__).resolve().parent
    src_guidance = patches_dir / "gate_guidance.py"
    if not src_guidance.is_file():
        raise FileNotFoundError(f"gate_guidance.py not found at {src_guidance}")
    write_utf8(hooks_scripts_dir / "gate_guidance.py", read_utf8(src_guidance))
    src_json = patches_dir / "gate_guidance.json"
    if src_json.is_file():
        write_utf8(hooks_scripts_dir / "gate_guidance.json", read_utf8(src_json))
    write_utf8(hooks_scripts_dir / "dispatch.py", DISPATCH_PY)
