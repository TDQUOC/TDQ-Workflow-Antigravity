#!/usr/bin/env python3
"""Unified Antigravity PreToolUse gate for `run_command`: search + bash + RTK rewrite.

Collapses search_gate.eval_search and bash_gate.eval_bash into one Python process,
then rewrites eligible commands with `rtk rewrite` via `overwrite.CommandLine`.
Any unexpected fault fails open (`sys.exit(0)`), never blocking valid tool calls.

Env: TDQ_PROJECT_DIR anchors the project; TDQ_LOG=0 mutes stderr; TDQ_RTK=0 disables RTK.
"""
import os as _tdq_os, sys as _tdq_sys
_tdq_here = _tdq_os.path.dirname(_tdq_os.path.abspath(__file__))
_tdq_scripts = _tdq_os.path.normpath(_tdq_os.path.join(_tdq_here, '..', '..', 'scripts'))
for _p in (_tdq_scripts, _tdq_here):
    if _tdq_os.path.isdir(_p) and _p not in _tdq_sys.path:
        _tdq_sys.path.insert(0, _p)
import utf8_io  # noqa: E402,F401
from datetime import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common  # noqa: E402 — injects `scripts/` onto sys.path
import bash_gate  # noqa: E402
import search_gate  # noqa: E402
from rtk_integration import can_compress_dump_command, rewrite_command  # noqa: E402


def _log_enabled():
    return os.environ.get("TDQ_LOG", "1") != "0"


def _log(message):
    """Log one ISO-timestamped event to stderr unless TDQ_LOG=0."""
    if _log_enabled():
        print(f"[{datetime.now().isoformat(timespec='seconds')}] {message}", file=sys.stderr)


def _run_gates(norm, cmd, cwd, role):
    """Execute search then bash gates in-process; return True if tool call remains allowed."""
    try:
        if not search_gate.eval_search(norm):
            return False
    except SystemExit:
        return False
    suppress_dump = bool(
        isinstance(cmd, str) and cmd and can_compress_dump_command(cmd, cwd=cwd, role=role)
    )
    try:
        return bool(bash_gate.eval_bash(norm, suppress_output_remind=suppress_dump))
    except SystemExit:
        return False


def process_payload(payload):
    """Run collapsed PreToolUse gates and rewrite command when eligible; return str or None."""
    norm = _common.begin_collapsed_session(payload or {})
    try:
        tool_name = norm.get("tool_name") or ""
        cmd = (norm.get("tool_input") or {}).get("command") or ""
        cwd = _common.payload_cwd(norm)
        role = (_common.detect_subagent(norm, cwd).get("role") or "")
        if not _run_gates(norm, cmd, cwd, role):
            return None
        if (
            _common._RUNTIME_STATE.get("deny_reason") is None
            and _common._RUNTIME_STATE.get("is_agy")
            and tool_name == "run_command"
            and isinstance(cmd, str)
            and cmd
        ):
            rewritten, changed, reason = rewrite_command(cmd, cwd=cwd, role=role)
            if changed and rewritten:
                _common.set_overwrite({"CommandLine": rewritten})
                _log(f"command_gate: overwrite CommandLine ({reason})")
                return rewritten
        return None
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001 — fail open so hook never breaks tool calls
        _log(f"command_gate: fail-open after {type(exc).__name__}: {exc}")
        return None
    finally:
        _common.end_collapsed_session()


def main():
    payload = _common.read_payload()
    process_payload(payload)
    sys.exit(0)


if __name__ == "__main__":
    main()
