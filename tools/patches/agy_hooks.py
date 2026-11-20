"""Upgrade dual-protocol lifecycle hooks for Antigravity 2.0 + Claude backward compat."""
from pathlib import Path

from .common_utils import ensure_utf8_import, read_utf8, replace_exact, write_utf8

COMMON_PY = r'''#!/usr/bin/env python3
"""Dual-protocol shared runtime helpers for TDQ lifecycle hooks (Claude Code + Antigravity 2.0)."""
import atexit
import contextlib
import importlib.util
import json
import os
import re
import sys
import time
import urllib.parse
from datetime import datetime

_HOOKS_DIR = os.path.dirname(os.path.abspath(__file__))
_SCRIPTS_DIR = os.path.normpath(os.path.join(_HOOKS_DIR, "..", "..", "scripts"))
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

import utf8_io  # noqa: E402,F401
import tdq_state  # noqa: E402
from tdq_state import (  # noqa: E402
    VALID_MODES,
    lenh_cho_project,
    mode_label,
    resolve_project_dir,
    turn_log_append,
    turn_log_read,
)
from search_rules import chuan_hoa_cong_cu_mcp  # noqa: E402

AGY_CODES = (
    "APPROVE",
    "GIT",
    "TEAM",
    "STATE",
    "READONLY",
    "VUNG",
    "ZERO-POPUP",
    "SUBAGENT",
    "UNFINISHED",
    "LSP",
    "SEARCH",
    "TICK",
    "DOC",
    "LOG",
    "OUTPUT",
    "SETUP",
    "GON",
    "NEXT",
    "WORKTREE",
    "ANCHOR",
    "DOD",
    "INTAKE",
)
CODES = AGY_CODES

MAX_REMIND_CHARS = 200
MAX_REMIND_LINES = 3
MAX_USER_MARKDOWN_CHARS = 1200

APPROVE_HINTS = {
    "spec": 'say "approve spec" or type "A"',
    "plan": 'say "approve plan" or type "A"',
    "mode": (
        'the plan proposes {mode} — say "inline" (I do it step by step right here) '
        'or "sub-agent" (several assistants in parallel), or type "A"/"B"; '
        'the old names main/subagent still work'
    ),
    "quick": 'say "approve quick" or type "A"',
}

_MODE_NHANH = "|".join(re.escape(m) for m in sorted(VALID_MODES, key=len, reverse=True))
_PLAN_MODE = re.compile(rf"Mode th\u1ef1c thi:\s*({_MODE_NHANH})", re.IGNORECASE)

_AGY_TOOLS = frozenset({
    "run_command",
    "edit_file",
    "write_file",
    "write_to_file",
    "replace_file_content",
    "multi_replace_file_content",
    "read_file",
    "view_file",
    "grep_search",
    "find_by_name",
    "list_dir",
    "search_directory",
    "find_file",
    "list_directory",
    "invoke_subagent",
    "swarm",
    "define_subagent",
    "ask_question",
    "ask_user_question",
    "call_mcp_tool",
    "manage_task",
    "send_message",
    "enter_plan_mode",
    "exit_plan_mode",
})
_AGY_PAYLOAD_KEYS = (
    "conversation_id",
    "conversationId",
    "trajectory_id",
    "transcriptPath",
    "workingDirectory",
    "user_message",
    "agent_step_idx",
    "toolName",
    "toolInput",
    "workspacePaths",
    "toolCall",
    "stepIdx",
    "invocationNum",
    "executionNum",
    "terminationReason",
    "lastUserInput",
    "continuationActive",
    "hookEventName",
)
TERMINAL_STOP_REASONS = frozenset({
    "USER_CANCELED",
    "ERROR",
    "MAX_INVOCATIONS",
    "MAX_FORCED_INVOCATIONS",
    "MAX_TOKEN_BUDGET_EXCEEDED",
    "TERMINAL_CUSTOM_HOOK",
})

_RUNTIME_STATE = {
    "event": None,
    "is_agy": False,
    "deny_reason": None,
    "stop_reason": None,
    "context_lines": [],
    "user_cards": [],
    "registered": False,
    "flushed": False,
    "tool_args_present": False,
    "overwrite": {},
    "raw_tool_name": "",
    "raw_args_is_str": False,
    "raw_arguments": {},
    "collapsed_payload": None,
    "new_user_turn": True,
}
_GUIDANCE_CACHE = None


def _log(message):
    """Emit ISO-timestamped stderr log line unless TDQ_LOG=0."""
    if os.environ.get("TDQ_LOG", "1") != "0":
        stamp = datetime.now().isoformat(timespec="seconds")
        print(f"[{stamp}] _common: {message}", file=sys.stderr)


def _load_gate_guidance():
    """Lazily load gate_guidance from hooks/scripts or tools/patches."""
    global _GUIDANCE_CACHE
    if _GUIDANCE_CACHE is not None:
        return _GUIDANCE_CACHE
    try:
        import gate_guidance
        _GUIDANCE_CACHE = gate_guidance
        return gate_guidance
    except ImportError:
        pass
    fallback_path = os.path.normpath(
        os.path.join(_HOOKS_DIR, "..", "..", "tools", "patches", "gate_guidance.py")
    )
    if os.path.isfile(fallback_path):
        try:
            spec = importlib.util.spec_from_file_location("gate_guidance", fallback_path)
            if spec is not None and spec.loader is not None:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                _GUIDANCE_CACHE = mod
                return mod
        except (ImportError, OSError, SyntaxError, ValueError) as exc:
            _log(f"fallback gate_guidance import failed: {type(exc).__name__}")
    return None


def _norm_code(code):
    """Normalize [TDQ:CODE] / TDQ:CODE / code to canonical uppercase key."""
    gg = _load_gate_guidance()
    if gg is not None:
        return gg.normalize_code(code)
    raw = str(code or "").strip().strip("[]").strip().upper()
    return raw[4:].strip() if raw.startswith("TDQ:") else raw


def has_tool_args():
    """Return True when the active payload carried a valid tool argument dict."""
    return bool(_RUNTIME_STATE.get("tool_args_present"))


def _parse_event_flag(argv=None):
    args = list(argv if argv is not None else sys.argv[1:])
    for idx, tok in enumerate(args):
        if tok == "--event" and idx + 1 < len(args):
            return args[idx + 1]
    return None


def _is_antigravity_payload(raw, event=None):
    """Detect Antigravity protocol strictly from flag/host/payload markers."""
    if event:
        return True
    if os.environ.get("TDQ_HOST") == "antigravity":
        return True
    if not isinstance(raw, dict):
        return False
    if any(k in raw for k in _AGY_PAYLOAD_KEYS):
        return True
    tname = str(raw.get("tool_name") or raw.get("toolName") or "")
    return tname in _AGY_TOOLS or (tname.startswith("mcp_") and not tname.startswith("mcp__"))


def is_agy():
    """Return True when the active hook invocation uses Antigravity protocol."""
    return bool(_RUNTIME_STATE["is_agy"])


def _agy_active(payload=None):
    return bool(_RUNTIME_STATE["is_agy"] or (payload is not None and _is_antigravity_payload(payload)))


def _unwrap_call_mcp(tool_name, tool_input):
    """Delegate call_mcp_tool and eager AGY unwrapping to scripts/search_rules.py."""
    tname, tinput, _ = chuan_hoa_cong_cu_mcp(tool_name, tool_input)
    return tname, tinput


def extract_workspace_path(payload):
    """Return first local workspace path from Antigravity `workspacePaths`, decoding file:// URIs."""
    if not isinstance(payload, dict):
        return None
    wpaths = payload.get("workspacePaths")
    if not isinstance(wpaths, list):
        return None
    for entry in wpaths:
        if not isinstance(entry, str) or not entry.strip():
            continue
        raw = entry.strip()
        if raw.lower().startswith("file://"):
            parsed = urllib.parse.unquote(urllib.parse.urlparse(raw).path or "")
            if os.name == "nt" and len(parsed) >= 3 and parsed[0] == "/" and parsed[2] == ":":
                parsed = parsed[1:]
            raw = parsed or raw
        if raw:
            return raw
    return None


def _decode_json_object(raw):
    """Decode dict or up to 3 JSON string layers into (dict, ok)."""
    if isinstance(raw, dict):
        return dict(raw), True
    if isinstance(raw, str):
        val = raw
        for _ in range(3):
            try:
                val = json.loads(val)
            except (TypeError, ValueError):
                return {}, False
            if isinstance(val, dict):
                return dict(val), True
            if not isinstance(val, str):
                return {}, False
    return {}, False


def _extract_raw_tool_container(payload, tool_call):
    """Return (raw_container, container_key_present) across AGY/Claude aliases."""
    for key in ("tool_input", "toolInput"):
        if key in payload and payload[key] is not None:
            return payload[key], True
    for key in ("args", "arguments"):
        if key in tool_call and tool_call[key] is not None:
            return tool_call[key], True
    for key in ("arguments", "input"):
        if key in payload and payload[key] is not None:
            return payload[key], True
    return None, False


def _save_raw_mcp_state(orig_tname, raw_container):
    """Capture raw tool name and call_mcp_tool Arguments shape before unwrapping."""
    _RUNTIME_STATE["raw_tool_name"] = orig_tname
    _RUNTIME_STATE["raw_args_is_str"] = False
    _RUNTIME_STATE["raw_arguments"] = {}
    if orig_tname != "call_mcp_tool":
        return
    container, ok = _decode_json_object(raw_container)
    if not ok:
        return
    if "Arguments" in container:
        raw_val = container["Arguments"]
    elif "arguments" in container:
        raw_val = container["arguments"]
    else:
        return
    _RUNTIME_STATE["raw_args_is_str"] = isinstance(raw_val, str)
    decoded_args, decoded_ok = _decode_json_object(raw_val)
    if decoded_ok:
        _RUNTIME_STATE["raw_arguments"] = decoded_args


def _normalize_search_aliases(tinput):
    """Map Antigravity grep_search/search_directory aliases to Grep keys."""
    if "pattern" not in tinput:
        for alias in ("Query", "query", "Pattern"):
            if isinstance(tinput.get(alias), str) and tinput[alias].strip():
                tinput["pattern"] = tinput[alias]
                break
    if "path" not in tinput:
        for alias in ("SearchPath", "TargetDir", "search_path"):
            if isinstance(tinput.get(alias), str) and tinput[alias].strip():
                tinput["path"] = tinput[alias]
                break
    if "glob" not in tinput and tinput.get("Includes"):
        inc = tinput["Includes"]
        if isinstance(inc, list) and inc:
            tinput["glob"] = str(inc[0])
        elif isinstance(inc, str) and inc.strip():
            tinput["glob"] = inc


def _normalize_tool_aliases(tname, tinput):
    """Map Antigravity tool input field aliases onto canonical Claude-compatible keys."""
    if "file_path" not in tinput:
        for alias in ("TargetFile", "Path", "AbsolutePath", "path", "target_file"):
            if isinstance(tinput.get(alias), str) and tinput[alias].strip():
                tinput["file_path"] = tinput[alias]
                break
    if "command" not in tinput:
        for alias in ("CommandLine", "cmd"):
            if isinstance(tinput.get(alias), str) and tinput[alias].strip():
                tinput["command"] = tinput[alias]
                break
    if tname in ("read_file", "view_file", "Read"):
        _normalize_read_ranges(tinput)
    elif tname in ("grep_search", "search_directory"):
        _normalize_search_aliases(tinput)


def _normalize_read_ranges(tinput):
    """Map StartLine/EndLine/ByteOffset aliases to offset/limit."""
    if "offset" not in tinput and "StartLine" in tinput:
        tinput["offset"] = tinput.get("StartLine")
    if "limit" not in tinput and "StartLine" in tinput and "EndLine" in tinput:
        try:
            sl = int(tinput["StartLine"])
            el = int(tinput["EndLine"])
            if el >= sl:
                tinput["limit"] = (el - sl) + 1
        except (TypeError, ValueError):
            pass
    if "limit" not in tinput and "ByteOffset" in tinput and "EndLine" not in tinput:
        tinput["limit"] = 150


def _sanitize_tool_input(payload):
    tool_input = payload.get("tool_input", {})
    expected = {
        "command": (str, list),
        "cmd": str,
        "file_path": str,
        "notebook_path": str,
        "path": str,
        "pattern": str,
        "root_dir": str,
        "language_id": str,
    }
    for field in tool_input.keys() & expected.keys():
        value = tool_input[field]
        valid = isinstance(value, expected[field])
        if isinstance(value, list):
            valid = all(isinstance(arg, str) for arg in value)
        if not valid:
            tdq_state._warn(f"Hook payload field rejected: tool_input.{field}")
            tool_input.pop(field)
            payload.pop("tool_name", None)


def _sanitize_payload_fields(payload, has_args):
    expected = {
        "cwd": str,
        "session_id": str,
        "tool_name": str,
        "hook_event_name": str,
        "prompt": str,
        "source": str,
        "agent_type": str,
        "stop_hook_active": bool,
        "tool_input": dict,
    }
    for field, kind in expected.items():
        if field in payload and not isinstance(payload[field], kind):
            tdq_state._warn(f"Hook payload field rejected: {field}")
            payload.pop(field)
            if field == "tool_input":
                payload["tool_input"] = {}
                payload.pop("tool_name", None)
                has_args = False
    _RUNTIME_STATE["tool_args_present"] = bool(has_args)
    _sanitize_tool_input(payload)


def _apply_agy_normalization(payload, event):
    """Normalize Antigravity protojson fields into canonical payload shape."""
    if not payload.get("hook_event_name") and event:
        payload["hook_event_name"] = event
    tool_call = payload.get("toolCall") if isinstance(payload.get("toolCall"), dict) else {}
    orig_tname = str(payload.get("tool_name") or payload.get("toolName") or tool_call.get("name") or "")
    if orig_tname.startswith("CORTEX_STEP_TYPE_"):
        orig_tname = orig_tname[len("CORTEX_STEP_TYPE_"):].lower()
    raw_container, has_container = _extract_raw_tool_container(payload, tool_call)
    _save_raw_mcp_state(orig_tname, raw_container if has_container else None)

    tname, tinput, args_present = chuan_hoa_cong_cu_mcp(
        orig_tname, raw_container if has_container else None
    )
    has_args = bool(has_container and args_present)
    if orig_tname != "call_mcp_tool" and tname != orig_tname:
        payload["original_tool_name"] = orig_tname
    tinput = dict(tinput) if isinstance(tinput, dict) else {}
    _normalize_tool_aliases(tname, tinput)

    if "tool_name" in payload or "toolName" in payload or tname:
        payload["tool_name"] = tname
    if any(k in payload for k in ("tool_input", "toolInput", "toolCall", "arguments", "input")) or tinput:
        payload["tool_input"] = tinput
    if not payload.get("prompt") and isinstance(payload.get("lastUserInput"), str) and payload["lastUserInput"].strip():
        payload["prompt"] = payload["lastUserInput"]
    if "continuationActive" in payload and "stop_hook_active" not in payload:
        payload["stop_hook_active"] = bool(payload["continuationActive"])
    return has_args


def normalize_payload(raw, event=None):
    """Normalize Antigravity 2.0 and Claude Code hook payloads into one canonical dict."""
    resolved_event = event if event is not None else _parse_event_flag()
    if not resolved_event and isinstance(raw, dict) and raw.get("hookEventName"):
        resolved_event = str(raw.get("hookEventName"))
    agy = _is_antigravity_payload(raw, event=resolved_event)
    _RUNTIME_STATE.update({
        "event": resolved_event or None,
        "is_agy": agy,
        "deny_reason": None,
        "stop_reason": None,
        "context_lines": [],
        "user_cards": [],
        "flushed": False,
        "tool_args_present": False,
        "overwrite": {},
        "raw_tool_name": "",
        "raw_args_is_str": False,
        "raw_arguments": {},
        "new_user_turn": True,
    })
    if not isinstance(raw, dict):
        return {}
    payload = dict(raw)
    has_args = "tool_input" in payload and isinstance(payload["tool_input"], dict)
    if agy:
        has_args = _apply_agy_normalization(payload, resolved_event)
    else:
        _RUNTIME_STATE["raw_tool_name"] = str(payload.get("tool_name") or "")
    _sanitize_payload_fields(payload, has_args)
    return payload


def _merge_user_markdown(cards):
    """Join or cap accumulated user_markdown blocks at <= 1,200 characters."""
    clean = [str(c).strip() for c in (cards or []) if str(c).strip()]
    if not clean:
        return ""
    joined = "\n\n".join(clean)
    if len(joined) <= MAX_USER_MARKDOWN_CHARS:
        return joined
    gg = _load_gate_guidance()
    if gg is not None:
        return gg._cap_text(joined, MAX_USER_MARKDOWN_CHARS)
    return joined[: MAX_USER_MARKDOWN_CHARS - 1].rstrip() + "…"


def _build_inject_response():
    """Build SessionStart / PreInvocation / PostInvocation protojson payload."""
    text = "\n".join(line for line in _RUNTIME_STATE["context_lines"] if line)
    user_md = _merge_user_markdown(_RUNTIME_STATE.get("user_cards"))
    if not text and not user_md:
        return {}
    msg_obj = {"systemMessage": text}
    if user_md:
        msg_obj["metadata"] = {"user_markdown": user_md}
    return {"injectSteps": [{"systemMessage": msg_obj}]}


def _build_legacy_response(text):
    """Build legacy fallback response when invoked without --event or hookEventName."""
    if _RUNTIME_STATE["deny_reason"]:
        reason = _RUNTIME_STATE["deny_reason"]
        return {
            "allow_tool": False,
            "decision": "deny",
            "reason": reason,
            "message": reason,
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            },
        }
    if _RUNTIME_STATE["stop_reason"]:
        return {"decision": "continue", "reason": _RUNTIME_STATE["stop_reason"]}
    user_md = _merge_user_markdown(_RUNTIME_STATE.get("user_cards"))
    if text or user_md:
        msg_obj = {"systemMessage": text}
        if user_md:
            msg_obj["metadata"] = {"user_markdown": user_md}
        return {"additionalContext": text, "injectSteps": [{"systemMessage": msg_obj}]}
    return {}


def build_agy_response():
    """Build the Antigravity 2.0 JSON output object from current _RUNTIME_STATE."""
    if not _RUNTIME_STATE["is_agy"]:
        return {}
    ev = _RUNTIME_STATE["event"]
    if ev == "PreToolUse":
        if _RUNTIME_STATE["deny_reason"]:
            return {"decision": "deny", "reason": _RUNTIME_STATE["deny_reason"]}
        out = {"decision": "allow"}
        if _RUNTIME_STATE.get("overwrite"):
            out["overwrite"] = dict(_RUNTIME_STATE["overwrite"])
        return out
    if ev == "PostToolUse":
        return {}
    if ev in ("SessionStart", "PreInvocation", "PostInvocation"):
        return _build_inject_response()
    if ev == "Stop":
        if _RUNTIME_STATE["stop_reason"]:
            return {"decision": "continue", "reason": _RUNTIME_STATE["stop_reason"]}
        return {"decision": "allow"}
    text = "\n".join(line for line in _RUNTIME_STATE["context_lines"] if line)
    return _build_legacy_response(text)


def _flush_agy_stdout():
    """Single-JSON stdout emitter called via atexit for Antigravity hook protocol."""
    if not _RUNTIME_STATE["is_agy"] or _RUNTIME_STATE.get("flushed"):
        return
    _RUNTIME_STATE["flushed"] = True
    out = build_agy_response()
    if not out and _RUNTIME_STATE["event"] is None:
        return
    sys.stdout.write(json.dumps(out, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def _ensure_atexit():
    if not _RUNTIME_STATE["registered"]:
        atexit.register(_flush_agy_stdout)
        _RUNTIME_STATE["registered"] = True


def set_overwrite(fields):
    """Set Antigravity PreToolUse `overwrite` fields, wrapping Arguments for call_mcp_tool."""
    if not isinstance(fields, dict) or not fields:
        return
    if _RUNTIME_STATE.get("raw_tool_name") == "call_mcp_tool":
        base = _RUNTIME_STATE.get("raw_arguments")
        merged = dict(base) if isinstance(base, dict) else {}
        for key, val in fields.items():
            if isinstance(key, str) and val is not None:
                merged[key] = val
        _RUNTIME_STATE["raw_arguments"] = merged
        encoded = (
            json.dumps(merged, ensure_ascii=False)
            if _RUNTIME_STATE.get("raw_args_is_str")
            else merged
        )
        _RUNTIME_STATE["overwrite"] = {"Arguments": encoded}
        return
    cur = _RUNTIME_STATE.setdefault("overwrite", {})
    for key, val in fields.items():
        if isinstance(key, str) and val is not None:
            cur[key] = val


def begin_collapsed_session(payload):
    """Normalize once (if needed) and cache payload for in-process gates."""
    raw = dict(payload) if isinstance(payload, dict) else {}
    already_norm = (
        _RUNTIME_STATE.get("event") is not None
        and "tool_input" in raw
        and "toolInput" not in raw
        and "toolCall" not in raw
    )
    norm = raw if already_norm else normalize_payload(raw)
    _RUNTIME_STATE["collapsed_payload"] = dict(norm)
    _RUNTIME_STATE["overwrite"] = {}
    return dict(norm)


def end_collapsed_session():
    """Clear cached collapsed payload while keeping overwrite/deny state."""
    _RUNTIME_STATE["collapsed_payload"] = None


def read_payload():
    """Read stdin JSON object fail-open and return normalized dict."""
    _ensure_atexit()
    cached = _RUNTIME_STATE.get("collapsed_payload")
    if cached is not None:
        return dict(cached)
    _RUNTIME_STATE["overwrite"] = {}
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw and raw.strip() else {}
    except (ValueError, OSError, UnicodeError):
        tdq_state._warn("Hook payload rejected: invalid JSON or unreadable stdin")
        return normalize_payload({})
    if not isinstance(payload, dict):
        tdq_state._warn("Hook payload rejected: expected an object")
        return normalize_payload({})
    return normalize_payload(payload)


def payload_cwd(payload):
    """Resolve canonical project root from payload cwd keys, workspacePaths, or os.getcwd()."""
    if isinstance(payload, dict):
        for key in ("cwd", "workingDirectory", "working_directory", "workspace_root", "project_root", "root"):
            val = payload.get(key)
            if isinstance(val, str) and val.strip():
                return resolve_project_dir(val)
        ws_path = extract_workspace_path(payload)
        if ws_path:
            return resolve_project_dir(ws_path)
    return resolve_project_dir(os.getcwd())


def session_id(payload):
    """Return canonical conversation/session identifier."""
    if not isinstance(payload, dict):
        return "default" if _RUNTIME_STATE["is_agy"] else ""
    if _agy_active(payload):
        for key in ("conversation_id", "conversationId", "session_id", "sessionId", "trajectory_id"):
            val = payload.get(key)
            if isinstance(val, str) and val.strip():
                return re.sub(r"[^A-Za-z0-9._-]", "_", val.strip())[:64]
        return "default"
    return str(payload.get("session_id") or "")


def _runtime_dir(cwd):
    return os.path.join(cwd, "docs", "tdq", ".tdq-runtime")


def _shard_turn_path(cwd, conv_id):
    return os.path.join(_runtime_dir(cwd), f"turns-{conv_id}.jsonl")


def _turn_meta_path(cwd, conv_id):
    return os.path.join(_runtime_dir(cwd), f"turn-meta-{conv_id}.json")


def read_turn_meta(cwd, conv_id):
    """Read per-session turn-meta JSON fail-open; returns {} when missing or invalid."""
    path = _turn_meta_path(cwd, conv_id)
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def write_turn_meta(cwd, conv_id, meta):
    """Persist per-session turn-meta JSON safely under NTFS lock."""
    path = _turn_meta_path(cwd, conv_id)
    payload = meta if isinstance(meta, dict) else {}
    with with_ntfs_lock(path + ".lock"):
        try:
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, ensure_ascii=False)
        except OSError:
            pass


def mark_turn_closed(cwd, conv_id):
    """Set turn_closed=True in turn-meta-<sid>.json so the next prompt starts a fresh turn."""
    if not conv_id:
        return
    meta = read_turn_meta(cwd, conv_id)
    if meta.get("turn_closed") is True:
        return
    meta["turn_closed"] = True
    write_turn_meta(cwd, conv_id, meta)


def _is_stale_runtime_file(name):
    """True when filename in .tdq-runtime belongs to the 7-day auto-cleanup allowlist."""
    if name.endswith(".lock"):
        return True
    if name.startswith("turns-") and name.endswith(".jsonl"):
        return True
    if name.startswith("pending-reminders-") and name.endswith(".jsonl"):
        return True
    return name.startswith("turn-meta-") and name.endswith(".json")


def cleanup_stale_runtime(cwd, max_age_seconds=7 * 86400):
    """Remove stale .tdq-runtime files older than max_age_seconds, failing open."""
    rdir = _runtime_dir(cwd)
    if not os.path.isdir(rdir):
        return 0
    cutoff = time.time() - max_age_seconds
    removed = 0
    try:
        entries = list(os.scandir(rdir))
    except OSError:
        return 0
    for entry in entries:
        if not entry.is_file() or not _is_stale_runtime_file(entry.name):
            continue
        try:
            if entry.stat().st_mtime < cutoff:
                os.remove(entry.path)
                removed += 1
        except OSError:
            continue
    if removed:
        _log(f"cleaned {removed} stale runtime file(s)")
    return removed


def _try_acquire_ntfs_lock(lock_path):
    """Attempt one non-blocking NTFS lock acquisition; return (fh, locked)."""
    if os.name != "nt":
        return None, True
    import msvcrt
    lf = open(lock_path, "a+b")
    lf.seek(0)
    msvcrt.locking(lf.fileno(), msvcrt.LK_NBLCK, 1)
    return lf, True


def _release_ntfs_lock(lf, locked):
    """Unlock and close NTFS lock file handle safely."""
    if lf is None:
        return
    if locked and os.name == "nt":
        import msvcrt
        try:
            lf.seek(0)
            msvcrt.locking(lf.fileno(), msvcrt.LK_UNLCK, 1)
        except OSError:
            pass
    try:
        lf.close()
    except OSError:
        pass


@contextlib.contextmanager
def with_ntfs_lock(lock_path, attempts=200):
    """Acquire a non-blocking Windows NTFS byte lock with bounded backoff."""
    parent = os.path.dirname(lock_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    lf, locked = None, False
    for attempt in range(attempts):
        try:
            lf, locked = _try_acquire_ntfs_lock(lock_path)
            break
        except OSError:
            _release_ntfs_lock(lf, False)
            lf = None
            if attempt == attempts - 1:
                yield False
                return
            time.sleep(min(0.02, 0.002 * (attempt % 10 + 1)))
    try:
        yield True
    finally:
        _release_ntfs_lock(lf, locked)


def _lock_and_append_jsonl(path, row):
    """Append one JSONL record under a dedicated NTFS lockfile."""
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    raw = (json.dumps(row, ensure_ascii=False) + "\n").encode("utf-8")
    with with_ntfs_lock(path + ".lock") as ok:
        if not ok:
            return False
        try:
            with open(path, "ab") as fh:
                fh.write(raw)
                fh.flush()
            return True
        except OSError:
            return False


def _read_jsonl(path):
    rows = []
    if not os.path.isfile(path):
        return rows
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                s = line.strip()
                if not s:
                    continue
                try:
                    rows.append(json.loads(s))
                except ValueError:
                    continue
    except OSError:
        pass
    return rows


def observe(cwd, payload, event, **fields):
    """Record one real observed action in the sharded or canonical turn ledger."""
    if isinstance(fields.get("path"), str):
        fields["path"] = fields["path"].replace(os.sep, "/")
    sid = session_id(payload)
    if _agy_active(payload):
        kind = fields.pop("kind", "observe")
        row = {"ts": tdq_state.now_iso(), "kind": kind, "event": event, "session": sid, **fields}
        _lock_and_append_jsonl(_shard_turn_path(cwd, sid), row)
        return
    turn_log_append(cwd, "observe", session=sid, event=event, **fields)


def turn_rows(cwd, payload=None):
    """Read current conversation turn rows combining canonical ledger and per-convId shard."""
    sid = session_id(payload) if payload is not None else None
    rows = turn_log_read(cwd, session=sid)
    if payload is not None and _agy_active(payload) and sid:
        shard = _read_jsonl(_shard_turn_path(cwd, sid))
        if shard:
            return list(rows) + shard
    return rows


def already_reminded(cwd, payload, code, rows=None):
    """True when normalized code was already reminded in the current turn."""
    if rows is None:
        rows = turn_rows(cwd, payload)
    target = _norm_code(code)
    return any(
        (r.get("kind") == "remind" or r.get("event") == "remind")
        and (_norm_code(r.get("code")) == target or r.get("code") == code)
        for r in rows
    )


def _fmt_tag(code):
    c = str(code)
    return f"[{c}]" if c.startswith("TDQ:") else f"[TDQ:{c}]"


def emit_context(lines):
    """Queue model context lines for Antigravity or print on stdout for Claude."""
    text = "\n".join(str(l) for l in lines if l) if isinstance(lines, (list, tuple)) else str(lines or "")
    if not text:
        return
    if _RUNTIME_STATE["is_agy"]:
        _ensure_atexit()
        _RUNTIME_STATE["context_lines"].append(text)
    else:
        print(text)


def emit_user_markdown(markdown_text):
    """Attach user-only 4-part Markdown guidance to injectSteps metadata."""
    text = str(markdown_text or "").strip()
    if not text or not _RUNTIME_STATE["is_agy"]:
        return
    _ensure_atexit()
    _RUNTIME_STATE["user_cards"].append(text)


def _build_queued_entry(norm_code, model_line="", user_card=""):
    """Build dual-channel queue entry (model_line <= 160, user_card <= 1,200)."""
    gg = _load_gate_guidance()
    raw_line = " ".join(str(model_line or "").split())
    if gg is None:
        tag = f"[TDQ:{norm_code}]"
        line = raw_line if raw_line.startswith("[TDQ:") else (f"{tag} {raw_line}".strip())
        return {
            "code": norm_code,
            "model_line": line[:160],
            "user_card": str(user_card or line)[:MAX_USER_MARKDOWN_CHARS],
            "text": line[:160],
        }
    detail = raw_line
    prefix = f"[TDQ:{norm_code}]"
    if detail.upper().startswith(prefix):
        detail = detail[len(prefix):].strip()
    built = gg.build_reminder_entry(norm_code, detail=detail)
    if norm_code in gg.GUIDANCE_TABLE:
        final_line = built["model_line"]
    elif raw_line.startswith("[TDQ:"):
        final_line = gg._cap_text(raw_line, gg.MAX_MODEL_HINT_CHARS)
    else:
        final_line = built["model_line"]
    final_card = str(user_card or "").strip() or built["user_card"]
    return {
        "code": norm_code,
        "model_line": final_line,
        "user_card": final_card,
        "text": final_line,
    }


def queue_remind(cwd, payload, code, model_line="", user_card="", check_turn=True):
    """Queue deduplicated dual-channel reminder to flush at PostInvocation/PreInvocation."""
    norm_code = _norm_code(code) or "UNKNOWN"
    if check_turn and already_reminded(cwd, payload, norm_code):
        return False
    sid = session_id(payload)
    qpath = os.path.join(_runtime_dir(cwd), f"pending-reminders-{sid}.jsonl")
    entry = _build_queued_entry(norm_code, model_line=model_line, user_card=user_card)
    os.makedirs(os.path.dirname(qpath), exist_ok=True)
    with with_ntfs_lock(qpath + ".lock") as ok:
        if not ok:
            return False
        existing = _read_jsonl(qpath)
        if any(_norm_code(r.get("code")) == norm_code for r in existing):
            return False
        raw = (json.dumps(entry, ensure_ascii=False) + "\n").encode("utf-8")
        try:
            with open(qpath, "ab") as fh:
                fh.write(raw)
                fh.flush()
            return True
        except OSError:
            return False


def _pop_pending_rows(cwd, conv_id):
    """Atomically read and clear pending-reminders-<conv_id>.jsonl under NTFS lock."""
    qpath = os.path.join(_runtime_dir(cwd), f"pending-reminders-{conv_id}.jsonl")
    if not os.path.isfile(qpath):
        return []
    with with_ntfs_lock(qpath + ".lock"):
        rows = _read_jsonl(qpath)
        if rows:
            try:
                os.remove(qpath)
            except OSError:
                pass
    return rows


def flush_pending_channels(cwd, conv_id):
    """Pop queued reminders and format (model_text <= 200, user_markdown <= 1,200)."""
    rows = _pop_pending_rows(cwd, conv_id)
    if not rows:
        return "", ""
    entries = []
    for row in rows:
        mline = str(row.get("model_line") or row.get("text") or "").strip()
        ucard = str(row.get("user_card") or "").strip()
        code = _norm_code(row.get("code")) or "UNKNOWN"
        if mline or ucard:
            entries.append({"code": code, "model_line": mline, "user_card": ucard})
    if not entries:
        return "", ""
    gg = _load_gate_guidance()
    if gg is not None:
        return gg.format_model_summary(entries), gg.format_user_markdown(entries)
    lines = [e["model_line"] for e in entries if e.get("model_line")]
    cards = [e["user_card"] for e in entries if e.get("user_card")]
    return trim(lines), _merge_user_markdown(cards)


def flush_pending_reminders(cwd, conv_id):
    """Pop queued PreToolUse reminders for conv_id and return list of model lines."""
    rows = _pop_pending_rows(cwd, conv_id)
    return [
        str(r.get("model_line") or r.get("text") or "")
        for r in rows
        if r.get("model_line") or r.get("text")
    ]


def _tuyet_doi(text, cwd):
    return lenh_cho_project(text, cwd)


def trim(lines):
    """Enforce <= 3 lines and <= 200 characters for legacy reminder strings."""
    lines = [l for l in lines if l][:MAX_REMIND_LINES]
    text = "\n".join(lines)
    if len(text) > MAX_REMIND_CHARS:
        text = text[: MAX_REMIND_CHARS - 1].rstrip() + "…"
    return text


def _as_lines(lines):
    if isinstance(lines, str):
        return lines.splitlines() or [lines]
    return [str(l) for l in (lines or [])]


def _format_hard_block_4part(code, raw_reason):
    """Format a 4-part Vietnamese block/continue reason via gate_guidance."""
    norm = _norm_code(code) or "UNKNOWN"
    text = " ".join(str(raw_reason or "").split())
    prefix = f"[TDQ:{norm}]"
    if text.upper().startswith(prefix):
        text = text[len(prefix):].strip()
    gg = _load_gate_guidance()
    if gg is not None:
        return gg.format_deny_4part(norm, detail=text)
    return f"{prefix} {text}".strip()


def _record_agy_remind(cwd, sid, code, event, force=False):
    row = {
        "ts": tdq_state.now_iso(),
        "kind": "remind",
        "event": "remind",
        "session": sid,
        "code": _norm_code(code) or code,
        "source_event": event,
    }
    if force:
        row["force"] = True
    _lock_and_append_jsonl(_shard_turn_path(cwd, sid), row)


def _emit_agy_reminder(cwd, payload, code, line_list, event, force=False):
    """Queue PreToolUse reminder or emit dual-channel reminder directly."""
    _ensure_atexit()
    sid = session_id(payload)
    norm_code = _norm_code(code) or "UNKNOWN"
    detail = " ".join(str(x).strip() for x in line_list if str(x).strip())
    active_ev = _RUNTIME_STATE["event"] or event
    if active_ev in ("PreToolUse", "Stop"):
        queue_remind(cwd, payload, norm_code, model_line=detail, check_turn=False)
        _record_agy_remind(cwd, sid, code, event, force=force)
        return True
    entry = _build_queued_entry(norm_code, model_line=detail)
    if entry["model_line"]:
        emit_context([entry["model_line"]])
    if entry["user_card"]:
        emit_user_markdown(entry["user_card"])
    _record_agy_remind(cwd, sid, code, event, force=force)
    return True


def remind(cwd, payload, code, lines, event="PreToolUse", rows=None, decide=True):
    """Emit (or queue under AGY) a non-blocking TDQ reminder once per turn."""
    if already_reminded(cwd, payload, code, rows=rows):
        if _agy_active(payload):
            return False
        sys.exit(0)
    line_list = _as_lines(lines)
    if _agy_active(payload):
        return _emit_agy_reminder(cwd, payload, code, line_list, event, force=False)
    tag = _fmt_tag(code)
    head = line_list[0] if line_list else ""
    prefixed = head if head.startswith(("[TDQ:", f"[{code}]")) else f"{tag} {head}"
    body = _tuyet_doi(trim([prefixed] + line_list[1:]), cwd)
    sid = session_id(payload)
    turn_log_append(cwd, "remind", session=sid, code=code)
    out = {"hookEventName": event}
    if decide:
        out["permissionDecision"] = "allow"
        out["permissionDecisionReason"] = "TDQ: a reminder, not a block."
    out["additionalContext"] = body
    print(json.dumps({"hookSpecificOutput": out}, ensure_ascii=False))
    sys.exit(0)


def format_denial(code, lines, repeat_count=0, day_du=False):
    """Format denial lines for Claude Code first vs repeat occurrence."""
    line_list = _as_lines(lines)
    tag_full = _fmt_tag(code)
    head = line_list[0] if line_list else ""
    first_line = head if head.startswith(("[TDQ:", f"[{code}]")) else f"{tag_full} {head}"
    dong = [first_line] + list(line_list[1:])
    if repeat_count <= 0:
        return "\n".join(l for l in dong if l) if day_du else trim(dong)
    tag = f"{tag_full} (repeat x{repeat_count + 1})" if repeat_count > 1 else f"{tag_full} (repeat)"
    action_summary = [l.strip() for l in line_list[1:] if l.strip()]
    repeat_body = [f"{tag} {head.strip()}"]
    if action_summary:
        primary = action_summary[0]
        if primary.endswith(":") and len(action_summary) > 1:
            primary = f"{primary} {action_summary[1]}"
        repeat_body.append(f"Quick fix: {primary}")
    res = "\n".join(repeat_body)
    return res if day_du else trim(repeat_body)


def block(cwd, payload, code, lines, event="PreToolUse", day_du=False):
    """Block a PreToolUse call cleanly across Claude Code and Antigravity 2.0."""
    rows = turn_rows(cwd, payload)
    line_list = _as_lines(lines)
    reason_key = line_list[0].strip() if line_list else ""
    norm_c = _norm_code(code) or code
    prev_blocks = [
        r for r in rows
        if r.get("kind") == "block" and (_norm_code(r.get("code")) or r.get("code")) == norm_c and r.get("reason_key") == reason_key
    ]
    repeat_count = len(prev_blocks)
    sid = session_id(payload)
    if _agy_active(payload):
        _ensure_atexit()
        raw_reason = _tuyet_doi(" ".join(l.strip() for l in line_list if l.strip()), cwd)
        ly_do = _format_hard_block_4part(code, raw_reason)
        row = {
            "ts": tdq_state.now_iso(),
            "kind": "block",
            "event": "block",
            "session": sid,
            "code": _norm_code(code) or code,
            "reason_key": reason_key,
            "repeat_count": repeat_count,
            "source_event": event,
        }
        _lock_and_append_jsonl(_shard_turn_path(cwd, sid), row)
        _RUNTIME_STATE["deny_reason"] = ly_do
        sys.exit(0)
    ly_do = _tuyet_doi(format_denial(code, line_list, repeat_count=repeat_count, day_du=day_du), cwd)
    turn_log_append(cwd, "block", session=sid, code=code, reason_key=reason_key, repeat_count=repeat_count)
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": event,
            "permissionDecision": "deny",
            "permissionDecisionReason": ly_do,
        }
    }, ensure_ascii=False))
    sys.exit(0)


def remind_force(cwd, payload, code, lines, event="PreToolUse"):
    """Emit/queue reminder without prior turn dedupe."""
    line_list = _as_lines(lines)
    if _agy_active(payload):
        return _emit_agy_reminder(cwd, payload, code, line_list, event, force=True)
    tag = _fmt_tag(code)
    head = line_list[0] if line_list else ""
    prefixed = head if head.startswith(("[TDQ:", f"[{code}]")) else f"{tag} {head}"
    body = _tuyet_doi(trim([prefixed] + line_list[1:]), cwd)
    sid = session_id(payload)
    turn_log_append(cwd, "remind", session=sid, code=code)
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": event,
            "permissionDecision": "allow",
            "permissionDecisionReason": "TDQ: a reminder, not a block.",
            "additionalContext": body,
        }
    }, ensure_ascii=False))
    sys.exit(0)


def stop_block(cwd, payload, reason, code="UNFINISHED", stop_hook_active=None):
    """Emit Stop block decision: decision='continue' for Antigravity, 'block' for Claude."""
    sid = session_id(payload)
    if _agy_active(payload):
        _ensure_atexit()
        formatted = _format_hard_block_4part(code, reason)
        row = {
            "ts": tdq_state.now_iso(),
            "kind": "stop_block",
            "event": "stop_block",
            "session": sid,
            "code": _norm_code(code) or code,
        }
        _lock_and_append_jsonl(_shard_turn_path(cwd, sid), row)
        _RUNTIME_STATE["stop_reason"] = formatted
        return
    out = {"decision": "block", "reason": reason}
    if stop_hook_active is not None:
        out["stop_hook_active"] = stop_hook_active
    print(json.dumps(out, ensure_ascii=False))


def echo_line(code, what):
    return f"When done, print: \u2713 [{code}] {what}"


def approve_hint(target, mode=None):
    hint = APPROVE_HINTS.get(target, "say approve")
    if target == "mode":
        return (
            f"\u27a4 Pick how to run it: {hint.format(mode=mode_label(mode or 'main'))}"
            " \u00b7 Feedback: just say it"
        )
    return f"\u27a4 Approve: {hint} \u00b7 Feedback: just say it"


def plan_mode(cwd, state):
    """Return the mode settled in plan_file, or None when absent."""
    rel = (state or {}).get("plan_file")
    if not rel:
        return None
    path = rel if os.path.isabs(rel) else os.path.join(cwd, rel)
    try:
        with open(path, encoding="utf-8") as fh:
            match = _PLAN_MODE.search(fh.read())
    except OSError:
        return None
    return match.group(1).lower() if match else None


def is_qc_report_target(target_path, cwd):
    """Allow tdq-qc-tester writes ONLY to markdown files strictly inside docs/tdq/qc/."""
    if not isinstance(target_path, str) or not target_path.strip():
        return False
    base = cwd or "."
    qc_root = os.path.realpath(os.path.join(base, "docs", "tdq", "qc"))
    abs_target = os.path.realpath(target_path if os.path.isabs(target_path) else os.path.join(base, target_path))
    try:
        common = os.path.commonpath([abs_target, qc_root])
    except ValueError:
        return False
    if common != qc_root or abs_target == qc_root:
        return False
    return abs_target.lower().endswith(".md")


_SCOPED_ARTIFACT_ROLES = frozenset({
    "tdq-explorer", "explorer", "tdq-debugger", "debugger", "tdq-reviewer", "reviewer",
})
_SCOPED_ARTIFACT_EXTS = frozenset({".md", ".json", ".jsonl"})
_SCOPED_SLUG_RE = re.compile(r"^[A-Za-z0-9._-]+$")
INVESTIGATE_GON_TEXT = (
    "[{ma}] muc_gat={muc} · investigate mode: cite file:line or URL+ts per claim.\n"
    "Write ONLY inside assigned artifact shard; never edit source files.\n"
    "Synthesize via evidence shards."
)


def _canonicalize_with_tail(abs_path):
    """Walk ancestors up to deepest existing dir, canonicalize, and re-append normalized tail."""
    cur = os.path.normpath(abs_path)
    tail = []
    while cur and not os.path.exists(cur):
        parent, seg = os.path.split(cur)
        if parent == cur or not seg or seg == "..":
            return None
        tail.append(seg)
        cur = parent
    if not cur:
        return None
    real_base = os.path.realpath(cur)
    return os.path.join(real_base, *reversed(tail)) if tail else real_base


def is_investigation_artifact_target(target_path, cwd, role=None, state=None):
    """5-layer scoped-write check for investigation artifact shards."""
    if not isinstance(target_path, str) or not target_path.strip() or "\x00" in target_path:
        return False
    after_drive = target_path[2:] if len(target_path) >= 2 and target_path[1] == ":" else target_path
    if ":" in after_drive or ".." in [seg for seg in re.split(r"[\\/]+", target_path) if seg]:
        return False
    r_low = str(role or "").strip().lower()
    if any(b in r_low for b in ("security-reviewer", "browser", "qc-tester")) or r_low not in _SCOPED_ARTIFACT_ROLES:
        return False
    if state is None:
        state = tdq_state.load(cwd, heal=False) or {}
    slug = str(state.get("active_request") or "").strip() if isinstance(state, dict) else ""
    if not slug or not _SCOPED_SLUG_RE.match(slug) or ".." in slug:
        return False
    base = cwd or "."
    root_real = os.path.realpath(base)
    raw_abs = target_path if os.path.isabs(target_path) else os.path.join(root_real, target_path)
    resolved = _canonicalize_with_tail(raw_abs)
    if not resolved:
        return False
    try:
        if os.path.commonpath([resolved, root_real]) != root_real or resolved == root_real:
            return False
    except ValueError:
        return False
    rel_posix = os.path.relpath(resolved, root_real).replace("\\", "/")
    fname = os.path.basename(rel_posix).lower()
    ext = os.path.splitext(fname)[1]
    if ext not in _SCOPED_ARTIFACT_EXTS:
        return False
    if fname.startswith("evidence") or ((fname.startswith("trial_") or fname.startswith("rec_")) and ext == ".json"):
        return False
    rel_cmp = rel_posix.lower() if sys.platform == "win32" else rel_posix
    slug_cmp = slug.lower() if sys.platform == "win32" else slug
    art_prefix = f"docs/tdq/artifacts/{slug_cmp}/"
    if rel_cmp.startswith(art_prefix) and len(rel_cmp) > len(art_prefix):
        return True
    res_prefix = "docs/tdq/research/"
    if rel_cmp.startswith(res_prefix):
        tail = rel_cmp[len(res_prefix):]
        if "/" not in tail and (tail == f"{slug_cmp}.md" or (tail.startswith(f"{slug_cmp}-") and ext == ".md" and len(tail) > len(slug_cmp) + 4)):
            return True
    return False


def append_agent_telemetry(cwd, record):
    """Append one per-role execution telemetry record to docs/tdq/.tdq-agent-telemetry.jsonl."""
    base = cwd or "."
    path = os.path.join(base, "docs", "tdq", ".tdq-agent-telemetry.jsonl")
    row = {
        "ts": record.get("ts") or tdq_state.now_iso(),
        "session": str(record.get("session") or ""),
        "role": str(record.get("role") or "unknown"),
        "task_id": str(record.get("task_id") or ""),
        "status": str(record.get("status") or "done"),
        "model": str(record.get("model") or ""),
        "effort": str(record.get("effort") or ""),
        "elapsed_s": record.get("elapsed_s"),
        "attempt": int(record.get("attempt") or 1),
        "files_count": int(record.get("files_count") or 0),
        "first_pass": bool(record.get("first_pass", True)),
        "outcome": str(record.get("outcome") or record.get("status") or "done"),
        "handoff_valid": bool(record.get("handoff_valid", False)),
    }
    _lock_and_append_jsonl(path, row)
    tdq_state._info(f"telemetry: role={row['role']} task={row['task_id']} status={row['status']}")
    return path


def register_subagent_role(cwd, conv_id, role, target_task="", model="", effort=""):
    """Persist dispatched subagent role under .tdq-runtime/sessions.json."""
    path = os.path.join(_runtime_dir(cwd), "sessions.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with with_ntfs_lock(path + ".lock"):
        data = {}
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
            except (OSError, ValueError):
                data = {}
        if not isinstance(data, dict):
            data = {}
        entry = {"role": role, "task": target_task, "at": time.time()}
        if model:
            entry["model"] = str(model)
        if effort:
            entry["effort"] = str(effort)
        data[str(conv_id)] = entry
        try:
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=2, ensure_ascii=False)
        except OSError:
            pass


def detect_subagent(payload, cwd):
    """Detect subagent invocation via sessions.json, agent_type/agentType, or step-0 transcriptPath."""
    sid = session_id(payload)
    spath = os.path.join(_runtime_dir(cwd), "sessions.json")
    if os.path.isfile(spath):
        try:
            with open(spath, "r", encoding="utf-8") as fh:
                reg = json.load(fh)
            if isinstance(reg, dict) and sid in reg:
                rec = reg[sid]
                return {
                    "is_subagent": True,
                    "role": rec.get("role"),
                    "task": rec.get("task", ""),
                    "model": rec.get("model", ""),
                    "effort": rec.get("effort", ""),
                }
        except (OSError, ValueError):
            pass
    if isinstance(payload, dict):
        explicit_role = payload.get("agent_type") or payload.get("agentType")
        if explicit_role:
            return {"is_subagent": True, "role": str(explicit_role), "task": ""}
    tpath = (payload or {}).get("transcriptPath") if isinstance(payload, dict) else None
    if isinstance(tpath, str) and os.path.isfile(tpath):
        try:
            with open(tpath, "r", encoding="utf-8", errors="replace") as fh:
                first_line = fh.readline()
            if first_line:
                rec = json.loads(first_line)
                txt = str(rec.get("content") or rec)
                for role_name in (
                    "tdq-security-reviewer",
                    "tdq-reviewer",
                    "tdq-qc-tester",
                    "tdq-implementer",
                    "tdq-build-resolver",
                    "tdq-refactor-cleaner",
                    "tdq-explorer",
                    "tdq-debugger",
                ):
                    if role_name in txt:
                        register_subagent_role(cwd, sid, role_name)
                        return {"is_subagent": True, "role": role_name, "task": ""}
        except (OSError, ValueError):
            pass
    return {"is_subagent": False, "role": None, "task": ""}
'''


POST_INVOCATION_PY = r'''#!/usr/bin/env python3
"""PostInvocation hook — flush queued PreToolUse reminders via dual channels."""
import sys
from _common import (
    emit_context,
    emit_user_markdown,
    flush_pending_channels,
    observe,
    payload_cwd,
    read_payload,
    session_id,
)


def main():
    payload = read_payload()
    cwd = payload_cwd(payload)
    sid = session_id(payload)
    model_text, user_markdown = flush_pending_channels(cwd, sid)
    if model_text or user_markdown:
        count = len(model_text.splitlines()) if model_text else 1
        observe(cwd, payload, "PostInvocation", flushed=count)
    if model_text:
        emit_context([model_text])
    if user_markdown:
        emit_user_markdown(user_markdown)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.exit(0)
'''


SUBAGENT_DISPATCH_GATE_PY = r'''#!/usr/bin/env python3
"""PreToolUse gate for invoke_subagent / swarm / define_subagent (AGY 2.0)."""
import re
import sys
from _common import (
    _log,
    block,
    is_agy,
    observe,
    payload_cwd,
    read_payload,
    register_subagent_role,
    remind,
    set_overwrite,
)
from tdq_state import effective_phase, load


REQUIRED_IMPL_FIELDS = ("TASK:", "WORKTREE:", "VÙNG FILE:", "TEST:", "TRẢ VỀ:")  # i18n-allow
_TASK_CODE_RE = re.compile(r"\b(T\d+[A-Za-z]*\.\d+[a-z]?|Q\d+)\b")


def _extract_task(text):
    match = _TASK_CODE_RE.search(text or "")
    return match.group(1) if match else ""


def _record_spawn_metadata(cwd, payload, tinput, prompt, role):
    """Extract spawn metadata and register role when an explicit child session ID exists."""
    task = _extract_task(prompt or role)
    model = str(tinput.get("Model") or tinput.get("model") or "").strip()
    effort = str(tinput.get("effort") or "").strip()
    target_sid = str(
        tinput.get("conversationId")
        or tinput.get("conversation_id")
        or tinput.get("agentId")
        or tinput.get("agent_id")
        or payload.get("agent_id")
        or ""
    ).strip()
    if role and target_sid:
        register_subagent_role(cwd, target_sid, role, target_task=task, model=model, effort=effort)
    observe(cwd, payload, "subagent_dispatch", role=role, task=task, model=model, effort=effort)
    _log(f"subagent_dispatch: role={role or '-'} task={task or '-'} sid={target_sid or '-'}")


def main():
    payload = read_payload()
    cwd = payload_cwd(payload)
    tname = payload.get("tool_name") or ""
    if tname not in ("invoke_subagent", "swarm", "define_subagent", "Task", "Agent"):
        return
    tinput = payload.get("tool_input") or {}
    state = load(cwd, heal=False) or {}
    phase = effective_phase(state, warn=False)
    mode = state.get("implement_mode") or ""
    prompt = str(tinput.get("Prompt") or tinput.get("prompt") or tinput.get("brief") or "")
    role = str(
        tinput.get("TypeName")
        or tinput.get("subagent_type")
        or tinput.get("name")
        or tinput.get("Role")
        or tinput.get("role")
        or ""
    ).strip()
    _record_spawn_metadata(cwd, payload, tinput, prompt, role)

    if tname == "swarm" and tinput.get("action") == "add" and phase == "implement" and mode != "subagent":
        block(cwd, payload, "SUBAGENT", [
            f"Swarm add blocked while implement_mode={mode or 'unset'}.",
            "Set implement_mode=subagent after user plan approval first.",
        ])
        return

    if "WORKTREE:" in prompt and str(tinput.get("Workspace") or "").lower() in ("branch", "share"):
        if is_agy():
            set_overwrite({"Workspace": "inherit"})
        else:
            block(cwd, payload, "SUBAGENT", [
                "TDQ already isolated a git worktree (WORKTREE:); pass Workspace='inherit' to invoke_subagent.",
            ])
            return

    if phase == "implement" and ("tdq-implementer" in role.lower() or "TASK:" in prompt):
        is_no_wt = (
            "WORKTREE: none" in prompt
            or "WORKTREE: (no_worktree" in prompt
            or "worktree_required: false" in prompt.lower()
            or "no_worktree" in prompt
        )
        req_fields = tuple(
            f for f in REQUIRED_IMPL_FIELDS if not (is_no_wt and f == "WORKTREE:")
        )
        missing = [f for f in req_fields if f not in prompt]
        if missing:
            remind(cwd, payload, "SUBAGENT", [
                f"Implementer assignment missing fields: {', '.join(missing)}. Check team-mode.md.",
                "Pre-build grounded prompt via: python3 scripts/tdq_team.py packet <task_id>.",
            ])


if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.exit(0)
'''


_LSP_O1_HELPER = r'''
_ROOT_LANG_MARKERS = {
    "pyproject.toml": "python",
    "requirements.txt": "python",
    "setup.py": "python",
    "tsconfig.json": "typescript",
    "package.json": "typescript",
    "jsconfig.json": "javascript",
    "go.mod": "go",
    "Cargo.toml": "rust",
    "pom.xml": "java",
    "build.gradle": "java",
    "build.gradle.kts": "java",
}


def _lang_family(lang):
    return "typescript" if lang in HO_TS else lang


def _pick_from_module_table(cap, goc):
    if not cap:
        return None, None
    if goc:
        goc_c = _chuan(goc)
        matched = [(g, l) for g, l in cap if _chuan(g) == goc_c and l]
        families = {_lang_family(l) for _, l in matched}
        if len(families) == 1:
            return matched[0][1], matched[0][0]
        return None, None
    families = {_lang_family(l) for _, l in cap if l}
    if len(families) == 1:
        return cap[0][1], cap[0][0]
    return None, None


def _detect_unique_lang_o1(cwd, goc=""):
    """Detect unique project language in O(1) without calling lsp_module.do_module."""
    cap = doc_cap_hop_le(cwd)
    if cap:
        return _pick_from_module_table(cap, goc)
    if not cwd or not os.path.isdir(cwd):
        return None, None
    found = []
    try:
        entries = list(os.scandir(cwd))
    except OSError:
        return None, None
    for entry in entries:
        if not entry.is_file():
            continue
        if entry.name in _ROOT_LANG_MARKERS:
            found.append(_ROOT_LANG_MARKERS[entry.name])
        elif entry.name.lower().endswith((".csproj", ".sln")):
            found.append("csharp")
    families = {_lang_family(l) for l in found}
    if len(families) != 1:
        return None, None
    chosen = "typescript" if "typescript" in found else found[0]
    return chosen, cwd
'''


_SEARCH_HUONG_A_HELPER = r'''
_RTK_BYPASS_RE = _re.compile(
    r"(?:^|[;&|])\s*rtk(?:\.exe)?(?:\s+-[^\s]+)*\s+bypass\b",
    _re.IGNORECASE,
)


def _is_rtk_bypass(ten_tool, vao):
    if ten_tool == "Grep" or not isinstance(vao, dict):
        return False
    cmd = vao.get("command") or vao.get("cmd") or ""
    if isinstance(cmd, list):
        cmd = " ".join(str(x) for x in cmd)
    return bool(_RTK_BYPASS_RE.search(str(cmd)))


def _search_grace_state(cwd, phien):
    """Return latest consecutive search_grace state from turns-<sid>.jsonl."""
    rows = _common._read_jsonl(_common._shard_turn_path(cwd, phien))
    state_val = "clean"
    for row in rows:
        if row.get("type") == "search_grace" or row.get("event") == "search_grace":
            val = row.get("state")
            if val in ("warned", "reset", "clean"):
                state_val = val
    return state_val


_SEARCH_CMD_LEAK_RE = _re.compile(r"(?:\b(?:rg|grep|findstr)\b|Select-String)", _re.IGNORECASE)
_PS_HERESTRING_RE = _re.compile(r"(?s)@'\r?\n.*?\r?\n'@|@\"\r?\n.*?\r?\n\"@")


def _has_search_leak(ten_tool, vao):
    """Detect raw search CLI invocations inside malformed shell strings outside PS here-strings."""
    if ten_tool in ("Grep", "grep_search", "search_directory") or not isinstance(vao, dict):
        return False
    cmd = vao.get("command") or vao.get("cmd") or ""
    if isinstance(cmd, list):
        cmd = " ".join(str(x) for x in cmd)
    stripped = _PS_HERESTRING_RE.sub(" ", str(cmd))
    return bool(_SEARCH_CMD_LEAK_RE.search(stripped))


def _mark_search_grace(cwd, phien, state_val, tool_name):
    row = {
        "ts": _common.tdq_state.now_iso(),
        "kind": "observe",
        "event": "search_grace",
        "type": "search_grace",
        "state": state_val,
        "session": phien,
        "tool": tool_name,
    }
    _common._lock_and_append_jsonl(_common._shard_turn_path(cwd, phien), row)
'''


_PROMPT_TURN_META_HELPER = r'''
_TAIL_BYTES = 65536


def _prompt_sha(payload):
    text = str((payload or {}).get("prompt") or (payload or {}).get("lastUserInput") or "")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16] if text else ""


def _extract_transcript_user_sig(tpath, prev_meta, prompt_sha=""):
    """Read <= 64 KB tail of transcriptPath in O(1) for the last USER_INPUT signature."""
    if not isinstance(tpath, str) or not tpath or not os.path.isfile(tpath):
        return None
    try:
        with open(tpath, "rb") as fh:
            fh.seek(0, os.SEEK_END)
            size = fh.tell()
            start = max(0, size - _TAIL_BYTES)
            fh.seek(start)
            if start > 0:
                fh.readline()
            last_rec = None
            last_end = start
            while True:
                raw_line = fh.readline()
                if not raw_line:
                    break
                cur_end = fh.tell()
                text = raw_line.decode("utf-8", "replace").strip()
                if not text:
                    continue
                try:
                    rec = json.loads(text)
                except ValueError:
                    continue
                if isinstance(rec, dict) and rec.get("type") == "USER_INPUT":
                    last_rec = rec
                    last_end = cur_end
    except OSError:
        return None
    if last_rec is not None:
        step_idx = last_rec.get("step_index")
        created = last_rec.get("created_at") or last_rec.get("timestamp") or ""
        if step_idx is not None or created:
            return f"ui:{step_idx}:{created}"
        return f"ui_pos:{last_end}"
    prev_sig = str((prev_meta or {}).get("last_user_sig") or "")
    prev_psha = str((prev_meta or {}).get("prompt_sha") or "")
    if prompt_sha and prev_psha and prompt_sha != prev_psha:
        return f"ui_big:{prompt_sha}"
    if prev_sig.startswith("ui") and not (prev_meta or {}).get("turn_closed"):
        return prev_sig
    return None


def _extract_user_turn_sig(payload, prev_meta):
    """Compute user-turn signature from transcriptPath tail or fallback prompt."""
    tpath = (payload or {}).get("transcriptPath") or (payload or {}).get("transcript_path")
    psha = _prompt_sha(payload)
    sig = _extract_transcript_user_sig(tpath, prev_meta, prompt_sha=psha)
    if sig is not None:
        return sig
    if psha:
        return "prompt:" + psha
    return ""


def _detect_new_user_turn(cwd, payload, sid):
    """Detect whether this PreInvocation starts a new user turn or continues mid-turn."""
    meta = read_turn_meta(cwd, sid)
    sig = _extract_user_turn_sig(payload, meta)
    turns_exists = os.path.isfile(_shard_turn_path(cwd, sid))
    if not meta:
        return True, sig
    if meta.get("turn_closed"):
        return True, sig
    if sig != meta.get("last_user_sig"):
        return True, sig
    if not sig and not turns_exists:
        return True, sig
    return False, sig
'''


def _patch_ask_gate(hooks_scripts_dir: Path) -> None:
    """Keep ZERO-POPUP hard block while dropping TDQ:ASK on Antigravity."""
    ask_path = hooks_scripts_dir / "ask_gate.py"
    ask_text = read_utf8(ask_path)
    if "ZERO-POPUP" not in ask_text:
        ask_text = ask_text.replace(
            "def main():",
            "from _common import block, payload_cwd, read_payload\n"
            "from tdq_state import load\n\n\n"
            "def _agy_zero_popup_main():\n"
            "    payload = read_payload()\n"
            '    tname = payload.get("tool_name") or ""\n'
            '    if tname not in ("ask_question", "ask_user_question", "AskUserQuestion"):\n'
            "        return\n"
            "    cwd = payload_cwd(payload)\n"
            "    st = load(cwd, heal=False) or {}\n"
            '    if st.get("active_request"):\n'
            '        block(cwd, payload, "ZERO-POPUP", [\n'
            '            "Popup question UI is banned during an active TDQ request.",\n'
            '            "Ask numbered options (1a 2b 3c) directly in chat instead.",\n'
            "        ])\n\n\n"
            "def main():\n"
            "    _agy_zero_popup_main()",
            1,
        )
        write_utf8(ask_path, ask_text)
    replace_exact(
        ask_path,
        '    phase = effective_phase(state, warn=False) if isinstance(state, dict) else None',
        '    if _common.is_agy():\n'
        '        sys.exit(0)\n'
        '    phase = effective_phase(state, warn=False) if isinstance(state, dict) else None',
        label="ask_gate_drop_agy_ask",
        sentinel="if _common.is_agy():\n        sys.exit(0)",
    )


def _patch_bash_gate(hooks_scripts_dir: Path) -> None:
    """Enforce read-only subagent, STATE (merging GATE), and GIT blocks on Antigravity."""
    bash_path = hooks_scripts_dir / "bash_gate.py"
    bash_text = read_utf8(bash_path)
    if "_PS_WRITE_PATTERN" not in bash_text:
        ps_guard = '''
import re as _re_ps
_PS_WRITE_PATTERN = _re_ps.compile(
    r"(?:Set-Content|Add-Content|Out-File|Copy-Item|Move-Item|Remove-Item|New-Item)\\b",
    _re_ps.IGNORECASE,
)


def _enforce_agy_bash_guards(payload, cwd):
    from _common import block, detect_subagent
    cmd = str((payload.get("tool_input") or {}).get("command") or "")
    info = detect_subagent(payload, cwd)
    role = (info.get("role") or "").lower()
    if any(r in role for r in ("reviewer", "qc-tester", "browser")) and (
        ">" in cmd or _PS_WRITE_PATTERN.search(cmd) or any(w in cmd for w in ("tee ", "sed -i", "rm ", "mv "))
    ):
        block(cwd, payload, "READONLY", [f"Read-only subagent `{role}` cannot mutate files via shell."])
        return True
    if _PS_WRITE_PATTERN.search(cmd) and ("docs/tdq/state.json" in cmd.replace("\\\\", "/") or "docs/tdq/STATE.md" in cmd.replace("\\\\", "/")):
        block(cwd, payload, "STATE", ["Do not mutate TDQ state via PowerShell; use tdq_state.py CLI."])
        return True
    if _re_ps.search(r"git\\s+(?:checkout\\s+-[bB]|switch\\s+-[cC]|branch)\\s+['\\x22]?(?:claude|antigravity|gemini|codex)[-_]", cmd, _re_ps.IGNORECASE):
        block(cwd, payload, "TDQ:GIT", ["AI-prefixed branch names are banned; name the branch after the work."])
        return True
    return False
'''
        bash_text = bash_text.replace("def main():", ps_guard + "\n\ndef main():", 1)
        write_utf8(bash_path, bash_text)
        replace_exact(
            bash_path,
            "    cwd = payload_cwd(payload)\n    rows = turn_rows(cwd, payload)",
            "    cwd = payload_cwd(payload)\n    if _enforce_agy_bash_guards(payload, cwd):\n        return\n    rows = turn_rows(cwd, payload)",
            label="bash_gate_agy_guards",
        )
    replace_exact(
        bash_path,
        'block(cwd, payload, "GATE", ["Do not mutate TDQ state via PowerShell; use tdq_state.py CLI."])',
        'block(cwd, payload, "STATE", ["Do not mutate TDQ state via PowerShell; use tdq_state.py CLI."])',
        label="bash_gate_merge_gate_to_state",
        sentinel='block(cwd, payload, "STATE"',
    )
    replace_exact(
        bash_path,
        '    if agy and re.search(r"git\\s+(?:checkout\\s+-[bB]|switch\\s+-[cC]|branch)\\s+[\'\\"]?(?:claude|antigravity|gemini|codex)[-_]", cmd, re.IGNORECASE):\n'
        '        block(cwd, payload, "TDQ:GIT", ["AI-prefixed branch names are banned; name the branch after the work."])\n'
        '        return True',
        '    if agy and _has_banned_agy_git(cmd, cwd, payload):\n        return True',
        label="bash_gate_hard_git_checks",
        sentinel="if agy and _has_banned_agy_git(",
    )
    if "def _has_banned_agy_git(" not in read_utf8(bash_path):
        git_helper = (
            "\n\ndef _has_banned_agy_git(cmd, cwd, payload):\n"
            "    from _common import block\n"
            "    branch_names = []\n"
            "    for pattern in BRANCH_PATTERNS:\n"
            "        branch_names += [_clean(m) for m in pattern.findall(cmd)]\n"
            "    for b_name, w_path in WORKTREE.findall(cmd):\n"
            "        if b_name:\n"
            "            branch_names.append(_clean(b_name))\n"
            "        if w_path:\n"
            '            branch_names.append(os.path.basename(_clean(w_path).rstrip("/")))\n'
            "    for name in branch_names:\n"
            "        if BAN.match(name):\n"
            '            block(cwd, payload, "TDQ:GIT", [f"AI-prefixed branch/worktree name {name!r} is banned; name it after the work."])\n'
            "            return True\n"
            '    if re.search(r"git\\b.*\\bcommit\\b", cmd, re.DOTALL) and any(p.search(cmd) for p in BAD_MSG):\n'
            '        block(cwd, payload, "TDQ:GIT", ["AI trailers (Co-Authored-By / generated with) are banned in commit messages."])\n'
            "        return True\n"
            '    low = cmd.lower()\n'
            '    if "git push" in low:\n'
            '        block(cwd, payload, "TDQ:GIT", ["git push is forbidden by TDQ policy; only push when explicitly asked."])\n'
            "        return True\n"
            '    if "git reset --hard" in low or "git clean -f" in low:\n'
            '        block(cwd, payload, "TDQ:GIT", ["Destructive git reset/clean is prohibited to protect user worktree."])\n'
            "        return True\n"
            '    cleaned = re.sub(r"(?s)@\'\\r?\\n.*?\\r?\\n\'@|@\\"\\r?\\n.*?\\r?\\n\\"@", " ", cmd).lower()\n'
            '    if any(w in cleaned for w in ("curl ", "wget ", "invoke-webrequest")) and any(p in cleaned for p in ("| bash", "| sh", "| iex")):\n'
            '        block(cwd, payload, "TDQ:VUNG", ["Piping remote downloads to shell is forbidden."])\n'
            "        return True\n"
            '    if "-executionpolicy bypass" in cleaned or "-ep bypass" in cleaned:\n'
            '        block(cwd, payload, "TDQ:VUNG", ["PowerShell ExecutionPolicy bypass is blocked."])\n'
            "        return True\n"
            "    return False\n"
        )
        txt_b = read_utf8(bash_path).replace("def _enforce_agy_bash_guards(", git_helper + "\n\ndef _enforce_agy_bash_guards(", 1)
        write_utf8(bash_path, txt_b)
    replace_exact(
        bash_path,
        '    if payload.get("agent_id") and state.get("active_request") \\',
        '    if (payload.get("agent_id") or (is_agy() and detect_subagent(payload, cwd).get("is_subagent"))) and state.get("active_request") \\',
        label="bash_gate_agy_team_guard",
        sentinel="is_agy() and detect_subagent(payload, cwd)",
    )
    replace_exact(
        bash_path,
        '        block(cwd, payload, "TDQ:TEAM", [\n'
        '            "A sub-agent may not mutate the project through Bash/PowerShell before implement.",\n'
        '            "Return structured output, or write only the assigned report under docs/tdq/artifacts/.",\n'
        '            "The TDQ leader remains the state and source writer.",\n'
        '        ])\n'
        '        return False\n\n'
        '    # (1) observe',
        '        block(cwd, payload, "TDQ:TEAM", [\n'
        '            "A sub-agent may not mutate the project through Bash/PowerShell before implement.",\n'
        '            "Return structured output, or write only the assigned report under docs/tdq/artifacts/.",\n'
        '            "The TDQ leader remains the state and source writer.",\n'
        '        ])\n'
        '        return False\n'
        '    _mutates_src_shell = any(\n'
        '        (SHELL_MUTATOR.search(part) and not re.search(r"(?:^|[\\s\'\\"=])docs[\\\\/]", part, re.IGNORECASE))\n'
        '        or any(not re.search(r"^(?:\\./)?docs[\\\\/]", t.lstrip("\'\\"").replace("\\\\", "/"), re.IGNORECASE)\n'
        '               for t in _part_stdout_targets(part))\n'
        '        for part in parts)\n'
        '    if is_agy() and state.get("active_request") and _mutates_src_shell:\n'
        '        from tdq_state import cong_dang_cho\n'
        '        _pending_gate = cong_dang_cho(state)\n'
        '        if _pending_gate:\n'
        '            block(cwd, payload, "TDQ:APPROVE", [\n'
        '                f"{_pending_gate} has no recorded approval — do not mutate source via shell.",\n'
        '            ])\n'
        '            return False\n\n'
        '    # (1) observe',
        label="bash_gate_agy_approve_shell_mutator",
        sentinel="do not mutate source via shell.",
    )
    replace_exact(
        bash_path,
        '    if agy and _PS_WRITE_PATTERN.search(cmd) and ("docs/tdq/state.json" in norm_cmd or "docs/tdq/STATE.md" in norm_cmd):\n'
        '        block(cwd, payload, "STATE", ["Do not mutate TDQ state via PowerShell; use tdq_state.py CLI."])\n'
        '        return True',
        '    if agy and ("docs/tdq/state.json" in norm_cmd or "docs/tdq/STATE.md" in norm_cmd) and (\n'
        '        _PS_WRITE_PATTERN.search(cmd)\n'
        '        or any(p.search(norm_cmd) for p in STATE_WRITES[:5])\n'
        '        or re.search(r"\\bopen\\([^)]*docs/tdq/(?:state\\.json|STATE\\.md)[^)]*[\'\\"](?:w|a|x)[a-z+]*[\'\\"]", norm_cmd)\n'
        '    ):\n'
        '        block(cwd, payload, "STATE", ["Do not mutate TDQ state directly; use tdq_state.py CLI."])\n'
        '        return True',
        label="bash_gate_agy_state_shell_block",
        sentinel="Do not mutate TDQ state directly; use tdq_state.py CLI.",
    )


def _patch_edit_gate(hooks_scripts_dir: Path) -> None:
    """Soften TDQ:TICK to reminder, harden TDQ:STATE, and drop TDQ:RULE on Antigravity."""
    edit_path = hooks_scripts_dir / "edit_gate.py"
    edit_text = read_utf8(edit_path)
    if "detect_subagent" not in edit_text:
        guard = '''
def _enforce_agy_readonly_subagent(payload, cwd):
    from _common import block, detect_subagent
    info = detect_subagent(payload, cwd)
    role = (info.get("role") or "").lower()
    if any(r in role for r in ("reviewer", "qc-tester", "browser")):
        block(cwd, payload, "READONLY", [
            f"Subagent role `{role}` is strictly read-only and cannot modify files.",
        ])
        return True
    return False
'''
        edit_text = edit_text.replace("def main():", guard + "\n\ndef main():", 1)
        write_utf8(edit_path, edit_text)
        replace_exact(
            edit_path,
            '    payload = read_payload()\n    tool_input = payload.get("tool_input") or {}\n'
            '    target = tool_input.get("file_path") or tool_input.get("notebook_path") or ""\n'
            '    if not target or not isinstance(target, str):\n        return\n    cwd = payload_cwd(payload)',
            '    payload = read_payload()\n    cwd = payload_cwd(payload)\n'
            '    if _enforce_agy_readonly_subagent(payload, cwd):\n        return\n'
            '    tool_input = payload.get("tool_input") or {}\n'
            '    target = tool_input.get("file_path") or tool_input.get("notebook_path") or ""\n'
            '    if not target or not isinstance(target, str):\n        return',
            label="edit_gate_readonly_guard",
        )
    replace_exact(
        edit_path,
        "from _common import (already_reminded, block, detect_subagent, echo_line, observe,\n"
        "                     payload_cwd, read_payload, remind, turn_rows)",
        "from _common import (already_reminded, block, detect_subagent, echo_line, is_agy,\n"
        "                     observe, payload_cwd, read_payload, remind, turn_rows)",
        label="edit_gate_import_is_agy",
        sentinel="detect_subagent, echo_line, is_agy,",
    )
    replace_exact(
        edit_path,
        '    if abs_target in (state_file, state_md) and payload.get("agent_id"):',
        '    if abs_target in (state_file, state_md) and (payload.get("agent_id") or is_agy()):',
        label="edit_gate_agy_state_block",
        sentinel='(payload.get("agent_id") or is_agy())',
    )
    replace_exact(
        edit_path,
        '    if abs_target in (state_file, state_md) and (payload.get("agent_id") or is_agy()):\n'
        '        block(cwd, payload, "TDQ:STATE", [\n'
        '            "A sub-agent may not write TDQ state or its generated mirror.",\n'
        '            "Return structured output to the TDQ leader; only tdq_state.py writes state.",\n'
        '        ])',
        '    if abs_target in (state_file, state_md) and (payload.get("agent_id") or is_agy()):\n'
        '        block(cwd, payload, "TDQ:STATE", [\n'
        '            "A sub-agent may not write TDQ state or its generated mirror.",\n'
        '            "Return structured output to the TDQ leader; only tdq_state.py writes state.",\n'
        '        ])\n'
        '        return',
        label="edit_gate_state_block_return",
        sentinel="Return structured output to the TDQ leader; only tdq_state.py writes state.\n        ])\n        return",
    )
    replace_exact(
        edit_path,
        '    if isinstance(payload.get("agent_id"), str) and payload["agent_id"] \\\n'
        '            and within(abs_target, os.path.realpath(cwd)) \\',
        '    if ((isinstance(payload.get("agent_id"), str) and payload["agent_id"]) \\\n'
        '            or (is_agy() and detect_subagent(payload, cwd).get("is_subagent"))) \\\n'
        '            and within(abs_target, os.path.realpath(cwd)) \\',
        label="edit_gate_agy_team_subagent_block",
        sentinel='or (is_agy() and detect_subagent(payload, cwd).get("is_subagent")))',
    )
    replace_exact(
        edit_path,
        '            if streak >= STREAK_NGUONG:\n'
        '                block(cwd, payload, "TDQ:TICK", [\n'
        '                    f"{streak} edits in a row with no tick in the plan — close the task before editing on.",\n'
        '                    "Task still in progress → update notes or tasks in the plan file to reset the streak.",\n'
        '                    "Test green → flip to [x] now; a different task → tick it before coding.",\n'
        '                    "Request already finished → tdq_state.py set phase=idle.",\n'
        '                ])',
        '            streak_limit = 8 if is_agy() else STREAK_NGUONG\n'
        '            if streak >= streak_limit:\n'
        '                block(cwd, payload, "TDQ:TICK", [\n'
        '                    f"{streak} edits in a row with no tick in the plan — close the task before editing on.",\n'
        '                    "Task still in progress → update notes or tasks in the plan file to reset the streak.",\n'
        '                    "Test green → flip to [x] now; a different task → tick it before coding.",\n'
        '                    "Request already finished → tdq_state.py set phase=idle.",\n'
        '                ])\n'
        '            elif is_agy() and streak >= 4:\n'
        '                remind(cwd, payload, "TICK", [\n'
        '                    f"{streak}/8 source edits without a plan checkbox tick (blocks at 8).",\n'
        '                ])',
        label="edit_gate_agy_smart_tick",
        sentinel="streak_limit = 8 if is_agy() else STREAK_NGUONG",
    )
    replace_exact(
        edit_path,
        '        if tick["exists"] and tick["has_doing"]:',
        '        if not is_agy() and tick["exists"] and tick["has_doing"]:',
        label="edit_gate_drop_agy_rule",
        sentinel='if not is_agy() and tick["exists"] and tick["has_doing"]:',
    )


def _patch_read_gate(hooks_scripts_dir: Path) -> None:
    """Use merged DOC code on Antigravity instead of removed READ alias."""
    rg_path = hooks_scripts_dir / "read_gate.py"
    rg_text = read_utf8(rg_path)
    if "_RUNTIME_STATE" not in rg_text and "_common.is_agy()" not in rg_text:
        old_rg_tail = (
            '    print(_common.json.dumps({\n'
            '        "hookSpecificOutput": {\n'
            '            "hookEventName": "PreToolUse",\n'
            '            "permissionDecision": "allow",\n'
            '            "permissionDecisionReason": "TDQ: a reminder, not a block.",\n'
            '            "additionalContext": _common.trim(_tao_thong_diep(ten, kb, dau, cuoi, lap_count)),\n'
            '        }\n'
            '    }, ensure_ascii=False))'
        )
        new_rg_tail = (
            '    if _common._RUNTIME_STATE.get("is_agy"):\n'
            '        _common.remind_force(cwd, payload, "DOC", _tao_thong_diep(ten, kb, dau, cuoi, lap_count))\n'
            '    else:\n'
            '        print(_common.json.dumps({\n'
            '            "hookSpecificOutput": {\n'
            '                "hookEventName": "PreToolUse",\n'
            '                "permissionDecision": "allow",\n'
            '                "permissionDecisionReason": "TDQ: a reminder, not a block.",\n'
            '                "additionalContext": _common.trim(_tao_thong_diep(ten, kb, dau, cuoi, lap_count)),\n'
            '            }\n'
            '        }, ensure_ascii=False))'
        )
        replace_exact(rg_path, old_rg_tail, new_rg_tail, label="read_gate_agy_remind")
    replace_exact(
        rg_path,
        '_common.remind_force(cwd, payload, "READ", messages)',
        '_common.remind_force(cwd, payload, "DOC", messages)',
        label="read_gate_doc_code",
        sentinel='_common.remind_force(cwd, payload, "DOC", messages)',
    )


def _patch_lsp_gate(hooks_scripts_dir: Path) -> None:
    """Enable O(1) language detection and allow+overwrite for start_lsp & blast_radius."""
    lsp_path = hooks_scripts_dir / "lsp_gate.py"
    replace_exact(
        lsp_path,
        "def _phan_xu_lenh(cwd, phien, op, tool_input):\n"
        '    """Route a TDQ LSP call to blast_radius, start_lsp, or allow."""\n'
        '    if op == "blast_radius":\n'
        "        khoa = khoa_hien_tai(cwd, phien)\n"
        "        rows = doc_so(cwd, khoa, phien)\n"
        "        dong = phan_xu_blast_radius(cwd, tool_input, rows)\n"
        "        _log(f\"blast_radius files={len(tool_input.get('changed_files') or [])} · {'deny' if dong else 'allow'}\")\n"
        "        return dong\n"
        '    if op == "start_lsp":\n'
        "        dong = phan_xu(cwd, tool_input)\n"
        "        _log(f\"language_id={tool_input.get('language_id')!r} root={tool_input.get('root_dir')!r} · \"\n"
        "             f\"{'deny' if dong else 'allow'}\")\n"
        "        return dong\n"
        '    _log(f"tdq-lsp op={op} — allow")\n'
        "    return []",
        _LSP_O1_HELPER.lstrip("\n")
        + "\n\ndef _agy_blast_radius(cwd, phien, tool_input):\n"
        "    khoa = khoa_hien_tai(cwd, phien)\n"
        "    rows = doc_so(cwd, khoa, phien)\n"
        '    scope = tool_input.get("scope", "exported")\n'
        '    transitive = bool(tool_input.get("include_transitive")) is True\n'
        '    if _common.is_agy() and (scope != "exported" or transitive):\n'
        '        patched = dict(tool_input, scope="exported", include_transitive=False)\n'
        "        dong = phan_xu_blast_radius(cwd, patched, rows)\n"
        "        if not dong:\n"
        '            _common.set_overwrite({"scope": "exported", "include_transitive": False})\n'
        '            _log("blast_radius auto-overwrite scope=exported · allow")\n'
        "            return []\n"
        "        return dong\n"
        "    dong = phan_xu_blast_radius(cwd, tool_input, rows)\n"
        "    _log(f\"blast_radius files={len(tool_input.get('changed_files') or [])} - {'deny' if dong else 'allow'}\")\n"
        "    return dong\n\n\n"
        "def _agy_start_lsp(cwd, tool_input):\n"
        '    lang = str(tool_input.get("language_id") or "").strip()\n'
        '    goc = str(tool_input.get("root_dir") or "").strip()\n'
        "    if _common.is_agy() and not lang:\n"
        "        det_lang, det_root = _detect_unique_lang_o1(cwd, goc)\n"
        "        if det_lang:\n"
        '            ov = {"language_id": det_lang}\n'
        "            if not goc and det_root:\n"
        '                ov["root_dir"] = det_root\n'
        "            _common.set_overwrite(ov)\n"
        '            _log(f"start_lsp auto-overwrite language_id={det_lang!r} - allow")\n'
        "            return []\n"
        "    dong = phan_xu(cwd, tool_input)\n"
        "    _log(f\"language_id={tool_input.get('language_id')!r} root={tool_input.get('root_dir')!r} - \"\n"
        "         f\"{'deny' if dong else 'allow'}\")\n"
        "    return dong\n\n\n"
        "def _phan_xu_lenh(cwd, phien, op, tool_input):\n"
        '    """Route a TDQ LSP call to blast_radius, start_lsp, or allow."""\n'
        '    if op == "blast_radius":\n'
        "        return _agy_blast_radius(cwd, phien, tool_input)\n"
        '    if op == "start_lsp":\n'
        "        return _agy_start_lsp(cwd, tool_input)\n"
        '    _log(f"tdq-lsp op={op} - allow")\n'
        "    return []",
        label="lsp_gate_o1_overwrite",
        sentinel="def _detect_unique_lang_o1(",
    )


def _patch_search_gate(hooks_scripts_dir: Path) -> None:
    """Apply Option A (1st-time soft reminder + 2nd-time deny, malformed allow) on AGY."""
    sg_path = hooks_scripts_dir / "search_gate.py"
    replace_exact(
        sg_path,
        "import json\nimport os",
        "import json\nimport os\nimport re as _re",
        label="search_gate_import_re",
        sentinel="import re as _re",
    )
    replace_exact(
        sg_path,
        "def quyet(cwd, phien, ten_tool, vao):",
        _SEARCH_HUONG_A_HELPER.lstrip("\n") + "\n\ndef quyet(cwd, phien, ten_tool, vao):",
        label="search_gate_huong_a_helpers",
        sentinel="def _search_grace_state(",
    )
    replace_exact(
        sg_path,
        '    if ten_tool == "Grep":\n        return vao',
        '    if ten_tool in ("Grep", "grep_search", "search_directory"):\n        return vao',
        label="search_gate_lenh_agy_grep",
        sentinel='if ten_tool in ("Grep", "grep_search", "search_directory"):',
    )
    replace_exact(
        sg_path,
        '    cong_cu = "Grep" if ten_tool == "Grep" else "Bash"',
        '    cong_cu = "Grep" if ten_tool in ("Grep", "grep_search", "search_directory") else "Bash"',
        label="search_gate_agy_grep_tool",
        sentinel='cong_cu = "Grep" if ten_tool in',
    )
    replace_exact(
        sg_path,
        '        if ten_tool != "Grep" and ten_tool.lower() not in search_rules.CONG_CU_SHELL:',
        '        if ten_tool not in ("Grep", "grep_search", "search_directory") and ten_tool.lower() not in search_rules.CONG_CU_SHELL:',
        label="search_gate_eval_agy_grep",
        sentinel='ten_tool not in ("Grep", "grep_search", "search_directory")',
    )
    replace_exact(
        sg_path,
        "    ok, ly_do = search_rules.quyet_dinh(pl, tt)\n"
        "    dung_xuong = None\n"
        "    if not ok:\n"
        "        _log(f\"nhắc tầng: {', '.join(tt['tang_song']) if tt['tang_song'] is not None else 'mọi tầng (không có mốc)'}\")  # i18n-allow\n"
        "        dung_xuong = ly_do_dung_xuong(moc, tt)\n"
        "        if dung_xuong:\n"
        "            ok, ly_do = True, dung_xuong\n"
        '    if pl.get("loai") == search_rules.TIM_CODE or pl.get("status") == "unknown":\n'
        "        # Only a search that RAN counts toward the unlock window: a denied one never executed.\n"
        '        search_observe.ghi_so(cwd, {"ts": time.time(), "khoa": khoa, "loai": "tim",\n'
        '                                    "cho_phep": ok, "tinh_cua_so": ok,\n'
        '                                    "doan_mo": bool(pl.get("doan_mo"))})\n'
        "    return ok, ly_do, pl, bool(dung_xuong)",
        '    if _common.is_agy() and pl.get("status") == "unknown":\n'
        '        if _has_search_leak(ten_tool, vao):\n'
        '            pl = dict(pl, loai=search_rules.TIM_CODE, status="leak_search")\n'
        '        else:\n'
        '            if pl.get("loai") == search_rules.TIM_CODE:\n'
        '                search_observe.ghi_so(cwd, {"ts": time.time(), "khoa": khoa, "loai": "tim",\n'
        '                                            "cho_phep": True, "tinh_cua_so": False, "doan_mo": False})\n'
        '                if pha in ("implement", "qc"):\n'
        '                    return True, "agy_malformed_remind", pl, False\n'
        '            return True, "agy_malformed_allow", pl, False\n'
        '    if _common.is_agy() and pl.get("loai") == search_rules.TIM_CODE and _is_rtk_bypass(ten_tool, vao):\n'
        '        search_observe.ghi_so(cwd, {"ts": time.time(), "khoa": khoa, "loai": "tim",\n'
        '                                    "cho_phep": False, "tinh_cua_so": False, "doan_mo": bool(pl.get("doan_mo"))})\n'
        '        return False, "[TDQ:SEARCH] rtk bypass grep/rg is denied; query LSP or Graphify first.", pl, False\n'
        "    ok, ly_do = search_rules.quyet_dinh(pl, tt)\n"
        "    dung_xuong = None\n"
        "    if not ok:\n"
        "        dung_xuong = ly_do_dung_xuong(moc, tt)\n"
        "        if dung_xuong:\n"
        "            ok, ly_do = True, dung_xuong\n"
        "    if _common.is_agy() and not ok and not dung_xuong:\n"
        "        if _search_grace_state(cwd, phien) != \"warned\":\n"
        '            _mark_search_grace(cwd, phien, "warned", ten_tool)\n'
        '            search_observe.ghi_so(cwd, {"ts": time.time(), "khoa": khoa, "loai": "tim",\n'
        '                                        "cho_phep": True, "tinh_cua_so": False, "doan_mo": bool(pl.get("doan_mo"))})\n'
        '            return True, "agy_search_grace", pl, False\n'
        '    if pl.get("loai") == search_rules.TIM_CODE or pl.get("status") == "unknown":\n'
        '        search_observe.ghi_so(cwd, {"ts": time.time(), "khoa": khoa, "loai": "tim",\n'
        '                                    "cho_phep": ok, "tinh_cua_so": ok,\n'
        '                                    "doan_mo": bool(pl.get("doan_mo"))})\n'
        "    return ok, ly_do, pl, bool(dung_xuong)",
        label="search_gate_quyet_huong_a",
        sentinel='"agy_malformed_allow"',
    )
    replace_exact(
        sg_path,
        "    if dung_xuong:\n"
        "        # Say it — once per turn (`remind` dedupes by code): a gate that silently stops gating\n"
        "        # leaves the agent believing the rule holds (review 2026-10-03, spec §2 row 3).\n"
        '        _common.remind(cwd, payload, MA, [ly_do, "Concept layer: LSP find_symbol/find_references, "\n'
        '                                      "graphify query."])\n'
        "    if ok:\n"
        "        return True",
        '    if ly_do == "agy_malformed_remind":\n'
        '        _common.remind(cwd, payload, MA, [f"Malformed command suspected search ({ten_tool})"])\n'
        '    elif ly_do == "agy_search_grace":\n'
        '        _common.queue_remind(cwd, payload, MA, f"Use LSP or Graphify before consecutive {ten_tool}", check_turn=False)\n'
        "    elif dung_xuong:\n"
        '        _common.remind(cwd, payload, MA, [ly_do, "Concept layer: LSP find_symbol/find_references, graphify query."])\n'
        "    if ok:\n"
        "        return True",
        label="search_gate_eval_huong_a",
        sentinel='if ly_do == "agy_malformed_remind":',
    )


def _patch_search_observe(hooks_scripts_dir: Path) -> None:
    """Reset consecutive search_grace when search_observe sees LSP or Graphify."""
    so_path = hooks_scripts_dir / "search_observe.py"
    replace_exact(
        so_path,
        "import json\nimport os",
        "import json\nimport os\nimport re",
        label="search_observe_import_re",
        sentinel="import re\nimport sys",
    )
    replace_exact(
        so_path,
        "from search_rules import (TOKEN, la_goi_khai_niem, la_tool_tdq_lsp,  # noqa: E402,F401\n"
        "                          phan_loai_ket_qua_lsp, trang_thai)",
        "import search_rules  # noqa: E402\n"
        "from search_rules import (TOKEN, la_goi_khai_niem, la_tool_tdq_lsp,  # noqa: E402,F401\n"
        "                          phan_loai_ket_qua_lsp, trang_thai)\n\n\n"
        "_SHELL_GRAPHIFY_RE = re.compile(\n"
        '    r"(?:^|[;&|]\\s*)(?:(?:py|python3?)(?:\\s+-\\S+)*\\s+(?:\\S*tdq_graphify\\.py|-m\\s+graphify)|graphify)\\s+"\n'
        '    r"(query|explain|path|god-nodes|affected)\\b",\n'
        "    re.IGNORECASE,\n"
        ")\n\n\n"
        "def _shell_graphify_label(norm_name, tool_input):\n"
        '    if str(norm_name or "").lower() not in (search_rules.CONG_CU_SHELL | {"powershell"}):\n'
        "        return None\n"
        "    if not isinstance(tool_input, dict):\n"
        "        return None\n"
        '    cmd = str(tool_input.get("command") or tool_input.get("cmd") or "")\n'
        "    m = _SHELL_GRAPHIFY_RE.search(cmd)\n"
        '    return f"graphify:{m.group(1).lower()}" if m else None\n\n\n'
        "def _maybe_reset_search_grace(cwd, phien, tool_name, tool_input, nhan):\n"
        "    if not _common.is_agy():\n"
        "        return\n"
        "    norm_name, _ = search_rules._agy_unwrap_tool(tool_name, tool_input)\n"
        "    is_graphify = bool(re.match(r\"^mcp_+(?:[A-Za-z0-9_-]+_)?graphify\", str(norm_name or \"\"), re.I))\n"
        "    if not (nhan or la_tool_tdq_lsp(norm_name) or is_graphify):\n"
        "        return\n"
        '    row = {"ts": _common.tdq_state.now_iso(), "kind": "observe", "event": "search_grace",\n'
        '           "type": "search_grace", "state": "reset", "session": phien, "tool": str(norm_name)}\n'
        "    _common._lock_and_append_jsonl(_common._shard_turn_path(cwd, phien), row)",
        label="search_observe_reset_helper",
        sentinel="def _shell_graphify_label(",
    )
    replace_exact(
        so_path,
        "    if su_kien == \"PreToolUse\":\n"
        "        nhan = la_goi_khai_niem(tool_name, tool_input)\n"
        "        if nhan:",
        "    if su_kien == \"PreToolUse\":\n"
        "        nhan = la_goi_khai_niem(tool_name, tool_input) or _shell_graphify_label(tool_name, tool_input)\n"
        "        _maybe_reset_search_grace(cwd, phien, tool_name, tool_input, nhan)\n"
        "        if nhan:",
        label="search_observe_pre_reset",
        sentinel="nhan = la_goi_khai_niem(tool_name, tool_input) or _shell_graphify_label(tool_name, tool_input)\n        _maybe_reset_search_grace(cwd, phien, tool_name, tool_input, nhan)\n        if nhan:",
    )
    replace_exact(
        so_path,
        "        if su_kien == \"PostToolUse\":\n"
        "            nhan = la_goi_khai_niem(tool_name, tool_input)\n"
        "            if nhan:",
        "        if su_kien == \"PostToolUse\":\n"
        "            nhan = la_goi_khai_niem(tool_name, tool_input) or _shell_graphify_label(tool_name, tool_input)\n"
        "            _maybe_reset_search_grace(cwd, phien, tool_name, tool_input, nhan)\n"
        "            if nhan:",
        label="search_observe_post_reset",
        sentinel="if su_kien == \"PostToolUse\":\n            nhan = la_goi_khai_niem(tool_name, tool_input) or _shell_graphify_label",
    )
    replace_exact(
        so_path,
        "    # Fallback for events without explicit hook_event_name\n"
        "    nhan = la_goi_khai_niem(tool_name, tool_input)",
        "    # Fallback for events without explicit hook_event_name\n"
        "    nhan = la_goi_khai_niem(tool_name, tool_input) or _shell_graphify_label(tool_name, tool_input)\n"
        "    _maybe_reset_search_grace(cwd, phien, tool_name, tool_input, nhan)",
        label="search_observe_fallback_reset",
        sentinel="nhan = la_goi_khai_niem(tool_name, tool_input) or _shell_graphify_label",
    )


def _patch_prompt_context(hooks_scripts_dir: Path) -> None:
    """Detect user turns via transcriptPath/turn_closed, drop FEEDBACK/GON/QC/same-as-last-turn on AGY."""
    pc_path = hooks_scripts_dir / "prompt_context.py"
    replace_exact(
        pc_path,
        "import hashlib\nimport os",
        "import hashlib\nimport json\nimport os",
        label="prompt_context_import_json",
        sentinel="import hashlib\nimport json\nimport os",
    )
    replace_exact(
        pc_path,
        "from _common import (INVESTIGATE_GON_TEXT, _shard_turn_path,\n"
        "                     already_reminded, approve_hint,\n"
        "                     detect_subagent, emit_context, flush_pending_reminders,\n"
        "                     is_agy, payload_cwd, plan_mode, read_payload, session_id)",
        "from _common import (INVESTIGATE_GON_TEXT, _RUNTIME_STATE, _shard_turn_path,\n"
        "                     already_reminded, approve_hint, detect_subagent, emit_context,\n"
        "                     emit_user_markdown, flush_pending_channels, is_agy,\n"
        "                     payload_cwd, plan_mode, read_payload, read_turn_meta,\n"
        "                     session_id, write_turn_meta)",
        label="prompt_context_imports",
        sentinel="flush_pending_channels",
    )
    old_hook = (
        "def _agy_pre_invocation_hook(payload, cwd):\n"
        "    sid = session_id(payload)\n"
        "    queued = flush_pending_reminders(cwd, sid)\n"
        "    if queued:\n"
        "        emit_context(queued)\n"
        "    sub = detect_subagent(payload, cwd)\n"
        '    if sub.get("is_subagent"):\n'
        "        anc = _subagent_anchor_line(cwd, payload, sub)\n"
        "        if anc:\n"
        "            emit_context([anc])\n"
        "        return True\n"
        "    shard = _shard_turn_path(cwd, sid)\n"
        "    if os.path.isfile(shard):\n"
        "        try:\n"
        "            os.remove(shard)\n"
        "        except OSError:\n"
        "            pass\n"
        '    prompt = str(payload.get("prompt") or payload.get("user_message") or "")\n'
        "    low = prompt.lower()\n"
        '    if any(k in low for k in ("lỗi", "bug", "sửa lại", "broken", "fail", "không chạy", "sai rồi")):  # i18n-allow\n'
        '        emit_context(["[TDQ:FEEDBACK] User reported bug/feedback: run `py -3 scripts/tdq_state.py hotfix <slug>` or open express fix cycle before editing."])\n'
        "    return False"
    )
    if old_hook in read_utf8(pc_path):
        replace_exact(
            pc_path,
            old_hook,
            _PROMPT_TURN_META_HELPER.lstrip("\n")
            + "\n\ndef _agy_pre_invocation_hook(payload, cwd):\n"
            "    sid = session_id(payload)\n"
            "    model_text, user_md = flush_pending_channels(cwd, sid)\n"
            "    if model_text:\n"
            "        emit_context([model_text])\n"
            "    if user_md:\n"
            "        emit_user_markdown(user_md)\n"
            "    sub = detect_subagent(payload, cwd)\n"
            '    if sub.get("is_subagent"):\n'
            '        _RUNTIME_STATE["new_user_turn"] = False\n'
            "        anc = _subagent_anchor_line(cwd, payload, sub)\n"
            "        if anc:\n"
            "            emit_context([anc])\n"
            "        return True, False\n"
            "    is_new, sig = _detect_new_user_turn(cwd, payload, sid)\n"
            '    _RUNTIME_STATE["new_user_turn"] = is_new\n'
            "    if is_new:\n"
            "        prev_meta = read_turn_meta(cwd, sid)\n"
            "        shard = _shard_turn_path(cwd, sid)\n"
            "        if os.path.isfile(shard):\n"
            "            try:\n"
            "                os.remove(shard)\n"
            "            except OSError:\n"
            "                pass\n"
            '        st_cur = load(cwd, heal=False) or {}\n'
            '        write_turn_meta(cwd, sid, {"last_user_sig": sig, "turn_closed": False, "prompt_sha": _prompt_sha(payload), "phase_anchor": str(prev_meta.get("phase_anchor") or ""), "mode": str(st_cur.get("implement_mode") or "")})\n'
            "    return False, is_new\n\n\n"
            "def _agy_phase_anchor(cwd, state, payload, sid):\n"
            '    """Inject 1-line [TDQ:GON] or [TDQ:QC] once per phase entry or post-compaction."""\n'
            '    req = str((state or {}).get("active_request") or "")\n'
            '    pha = effective_phase(state, warn=False)\n'
            '    if not req or pha not in ("implement", "qc"):\n'
            "        return\n"
            "    meta = read_turn_meta(cwd, sid)\n"
            '    anchor = f"{req}:{pha}"\n'
            '    is_compact = str(payload.get("source") or "").lower() in ("compact", "resume")\n'
            '    if not is_compact and meta.get("phase_anchor") == anchor:\n'
            "        return\n"
            '    if pha == "implement":\n'
            '        muc = muc_gat_hieu_luc(state)\n'
            '        if muc != "off":\n'
            '            tmpl = INVESTIGATE_GON_TEXT if work_kind_hieu_luc(state) == "investigate" else NHAC_GON\n'
            '            cap_lim = MAX_GON_CHARS if work_kind_hieu_luc(state) == "investigate" else min(MAX_GON_CHARS, 160)\n'
            "            dong = _truncate(tmpl.format(ma=MA_GON, muc=muc), cap_lim)\n"
            "            emit_context([dong])\n"
            "    else:\n"
            '        emit_context(["[TDQ:QC] QC gate: verify DoD with evidence, run tdq-qc-tester, check clean-code invariants."])\n'
            '    meta["phase_anchor"] = anchor\n'
            "    write_turn_meta(cwd, sid, meta)",
            label="prompt_context_agy_turn_hook",
        )
    replace_exact(
        pc_path,
        "    if is_agy() and _agy_pre_invocation_hook(payload, cwd):\n"
        "        return\n"
        "    sub = detect_subagent(payload, cwd)\n"
        '    if sub.get("is_subagent"):\n'
        "        anc = _subagent_anchor_line(cwd, payload, sub)\n"
        "        if anc:\n"
        "            emit_context([anc])\n"
        "            return\n"
        "    sid = session_id(payload)\n"
        "    turn_log_clear(cwd, sid)\n"
        "    # Start-of-turn disk snapshot — so stop_gate can tell at end of turn what REALLY changed,\n"
        "    # even when the change went through the shell (the turn ledger only sees Edit/Write).\n"
        "    # Written to the ledger, NOT printed into context → costs the model no tokens.\n"
        '    turn_log_append(cwd, "turn_start", session=sid, **turn_snapshot(cwd))\n'
        "    _nhac_worktree(cwd)",
        "    sid = session_id(payload)\n"
        "    agy_mode = is_agy()\n"
        "    is_new_turn = True\n"
        "    if agy_mode:\n"
        "        should_stop, is_new_turn = _agy_pre_invocation_hook(payload, cwd)\n"
        "        if should_stop:\n"
        "            return\n"
        "    else:\n"
        "        sub = detect_subagent(payload, cwd)\n"
        '        if sub.get("is_subagent"):\n'
        "            anc = _subagent_anchor_line(cwd, payload, sub)\n"
        "            if anc:\n"
        "                emit_context([anc])\n"
        "                return\n"
        "    if not agy_mode or is_new_turn:\n"
        "        turn_log_clear(cwd, sid)\n"
        '        turn_log_append(cwd, "turn_start", session=sid, **turn_snapshot(cwd))\n'
        "        _nhac_worktree(cwd)",
        label="prompt_context_conditional_snapshot",
        sentinel="should_stop, is_new_turn = _agy_pre_invocation_hook",
    )
    replace_exact(
        pc_path,
        "    _emit(cwd, sid, lines, critical=drifted)\n"
        "    # AFTER the standing block: _emit cuts from the tail, and the law pointer must not be\n"
        "    # what pushes the NEXT line out of the 240-char ceiling.\n"
        "    _nhac_gon(cwd, state, payload, sid)\n"
        "    _nhac_qc(cwd, state, payload, sid)",
        "    _emit(cwd, sid, lines, critical=drifted)\n"
        "    if agy_mode:\n"
        "        _agy_phase_anchor(cwd, state, payload, sid)\n"
        "    else:\n"
        "        _nhac_gon(cwd, state, payload, sid)\n"
        "        _nhac_qc(cwd, state, payload, sid)",
        label="prompt_context_agy_phase_anchor",
        sentinel="if agy_mode:\n        _agy_phase_anchor(cwd, state, payload, sid)",
    )
    replace_exact(
        pc_path,
        "def _emit(cwd, session, lines, critical=False):\n"
        '    """critical=True: a warning/action specific to this turn (ambiguous approval, mode\n'
        "    mismatch, spec drift) — never compacted, even when it repeats last turn word for word.\"\"\"\n"
        "    # Paths are made absolute AFTER the cap, for the reason `_common._tuyet_doi` gives: a cut\n"
        "    # command is a command the agent cannot run.\n"
        '    text = lenh_cho_project(_truncate("\\n".join(lines[:MAX_LINES])), cwd)\n'
        "    if critical:\n"
        "        emit_context([text])\n"
        "        return\n"
        '    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()\n'
        "    if prompt_context_last(cwd, session) == digest:\n"
        "        text = _compact(text)\n"
        "    else:\n"
        "        prompt_context_save(cwd, session, digest)\n"
        "    emit_context([text])",
        "def _emit(cwd, session, lines, critical=False):\n"
        '    """Emit standing prompt context, skipping same-as-last-turn repeats on Antigravity."""\n'
        '    text = lenh_cho_project(_truncate("\\n".join(lines[:MAX_LINES])), cwd)\n'
        '    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()\n'
        "    if is_agy():\n"
        '        is_new = bool(_RUNTIME_STATE.get("new_user_turn", True))\n'
        "        if is_new or prompt_context_last(cwd, session) != digest:\n"
        "            prompt_context_save(cwd, session, digest)\n"
        "            emit_context([text])\n"
        "        return\n"
        "    if critical:\n"
        "        emit_context([text])\n"
        "        return\n"
        "    if prompt_context_last(cwd, session) == digest:\n"
        "        text = _compact(text)\n"
        "    else:\n"
        "        prompt_context_save(cwd, session, digest)\n"
        "    emit_context([text])",
        label="prompt_context_emit_no_same_as_last_turn",
        sentinel="if is_agy():\n        is_new = bool(_RUNTIME_STATE.get(",
    )


def _patch_stop_gate(hooks_scripts_dir: Path) -> None:
    """Enforce continuationActive single-stop, soften LOG/TICK/DOD, drop STUCK, set turn_closed."""
    stop_path = hooks_scripts_dir / "stop_gate.py"
    replace_exact(
        stop_path,
        "from _common import TERMINAL_STOP_REASONS, emit_context, is_agy, payload_cwd, queue_remind, read_payload, stop_block, turn_rows",
        "from _common import (TERMINAL_STOP_REASONS, emit_context, is_agy, mark_turn_closed,\n"
        "                     payload_cwd, queue_remind, read_payload, session_id, stop_block, turn_rows)",
        label="stop_gate_imports",
        sentinel="mark_turn_closed",
    )
    replace_exact(
        stop_path,
        "    if dem > MAX_STREAK:",
        "    if dem > (2 if is_agy() else MAX_STREAK):",
        label="stop_gate_max_streak_2_agy",
        sentinel="if dem > (2 if is_agy() else MAX_STREAK):",
    )
    replace_exact(
        stop_path,
        "        _info(f\"stop_gate: TDQ:UNFINISHED stepped down after {dem - 1} block(s) with no progress\")\n"
        '        stuck_msg = (f"[TDQ:STUCK] {task_open_count(cwd)} open task(s).{next_step} "\n'
        '                     "Finish plan or declare a genuine blocker with "\n'
        '                     "`tdq_state.py pause --loai <kind> --ly-do \\"<why>\\"`.")\n'
        "        if is_agy():\n"
        '            if _common._RUNTIME_STATE.get("event") == "Stop":\n'
        '                queue_remind(cwd, payload or {}, "STOP", stuck_msg)\n'
        "            else:\n"
        "                emit_context([stuck_msg])\n"
        "        else:\n"
        '            print(json.dumps({"hookSpecificOutput": {\n'
        '                "hookEventName": "Stop",\n'
        '                "additionalContext": stuck_msg,\n'
        "            }}, ensure_ascii=False))\n"
        "        return True",
        "        _info(f\"stop_gate: TDQ:UNFINISHED stepped down after {dem - 1} block(s) with no progress\")\n"
        "        if is_agy():\n"
        '            queue_remind(cwd, payload or {}, "UNFINISHED", f"{task_open_count(cwd)} open task(s){next_step}")\n'
        "            return False\n"
        '        stuck_msg = (f"[TDQ:STUCK] {task_open_count(cwd)} open task(s).{next_step} "\n'
        '                     "Finish plan or declare a genuine blocker with "\n'
        '                     "`tdq_state.py pause --loai <kind> --ly-do \\"<why>\\"`.")\n'
        '        print(json.dumps({"hookSpecificOutput": {\n'
        '            "hookEventName": "Stop",\n'
        '            "additionalContext": stuck_msg,\n'
        "        }}, ensure_ascii=False))\n"
        "        return True",
        label="stop_gate_drop_agy_stuck",
        sentinel='queue_remind(cwd, payload or {}, "UNFINISHED"',
    )
    replace_exact(
        stop_path,
        '    if str(payload.get("terminationReason") or "") in TERMINAL_STOP_REASONS:\n'
        "        return\n"
        "    # Claude Code sets this flag after a block, as loop protection. The two older gates\n"
        "    # honour it; the [TDQ:UNFINISHED] gate must not, or a single stop would end the run\n"
        "    # with the plan half done — which is the whole defect it exists to close.\n"
        '    lap_lai = bool(payload.get("stop_hook_active"))\n'
        "    cwd = payload_cwd(payload)\n"
        "    state = load(cwd)\n"
        '    if state is None or not state.get("active_request"):\n'
        "        return\n"
        "    if lap_lai and _chan_chua_xong(cwd, state, payload):\n"
        "        return\n"
        "    if lap_lai:\n"
        "        return",
        "    cwd = payload_cwd(payload)\n"
        "    sid = session_id(payload)\n"
        '    if str(payload.get("terminationReason") or "") in TERMINAL_STOP_REASONS:\n'
        "        if is_agy():\n"
        "            mark_turn_closed(cwd, sid)\n"
        "        return\n"
        '    cont_active = bool(payload.get("continuationActive") or payload.get("continuation_active") or payload.get("stop_hook_active"))\n'
        "    lap_lai = cont_active\n"
        "    state = load(cwd)\n"
        '    if state is None or not state.get("active_request"):\n'
        "        if is_agy():\n"
        "            mark_turn_closed(cwd, sid)\n"
        "        return\n"
        "    if lap_lai and _chan_chua_xong(cwd, state, payload):\n"
        "        return\n"
        "    if lap_lai:\n"
        "        if is_agy():\n"
        "            mark_turn_closed(cwd, sid)\n"
        "        return",
        label="stop_gate_continuation_active",
        sentinel="lap_lai = cont_active\n",
    )
    replace_exact(
        stop_path,
        '    edited = [r.get("path", "") for r in rows\n'
        '              if r.get("kind") == "observe" and r.get("event") == "edit"\n'
        '              and not str(r.get("path", "")).startswith(log_dir)]\n'
        '    logged = any(r.get("kind") == "observe" and r.get("event") == "log_written" for r in rows)\n\n'
        "    # Second piece of evidence, independent of the tool name: the real effect on disk.\n"
        "    # Truncate the path here, not only in _shell_changed_path: a path read off the turn ledger\n"
        "    # also goes straight into `reason`, and a long path pushes the block past 300 chars.\n"
        '    culprit = edited[0][:MAX_PATH_CHARS] if edited else ""\n'
        '    source = "turn ledger" if culprit else "—"\n'
        "    if snap:\n"
        "        if not logged:\n"
        "            logged = _log_changed(cwd, snap)\n"
        "        if not culprit and _repo_changed(cwd, snap):\n"
        "            culprit = _shell_changed_path(cwd, snap)\n"
        '            source = "repo fingerprint"\n\n'
        "    if culprit and not logged:\n"
        "        # §6: a block decision has to be traceable — a wrong block must name its source at once.\n"
        '        _info(f"stop_gate: block TDQ:LOG · source={source} · path={culprit}")\n'
        '        reason = (f"[TDQ:LOG] Repo changed ({culprit}), {log_rel} not appended. "\n'
        '                  "Run `tdq_finish.py --files <file> --log \\"<summary>\\"`, no hand Edit. "\n'
        '                  "Then reprint the last chat block VERBATIM (question + options + "\n'
        '                  "the ➤ line), no summarising.")\n'
        '        stop_block(cwd, payload, reason, code="TDQ:LOG")\n'
        "        return",
        '    edited = [r.get("path", "") for r in rows\n'
        '              if r.get("kind") == "observe" and r.get("event") == "edit"\n'
        '              and not str(r.get("path", "")).startswith(log_dir)\n'
        '              and not (is_agy() and _is_agy_log_exempt(r.get("path", "")))]\n'
        '    logged = any(r.get("kind") == "observe" and r.get("event") == "log_written" for r in rows)\n'
        '    culprit = edited[0][:MAX_PATH_CHARS] if edited else ""\n'
        '    source = "turn ledger" if culprit else "—"\n'
        "    if snap:\n"
        "        if not logged:\n"
        "            logged = _log_changed(cwd, snap)\n"
        "        if not culprit:\n"
        "            changed, cand = _shell_change_check(cwd, snap)\n"
        "            if changed and cand and not (is_agy() and _is_agy_log_exempt(cand)):\n"
        "                culprit = cand\n"
        '                source = "repo fingerprint"\n'
        "    if culprit and not logged:\n"
        '        _info(f"stop_gate: block TDQ:LOG · source={source} · path={culprit}")\n'
        '        reason = (f"[TDQ:LOG] Repo changed ({culprit}), {log_rel} not appended. "\n'
        '                  "Run `tdq_finish.py --files <file> --log \\"<summary>\\"`, no hand Edit. "\n'
        '                  "Then reprint the last chat block VERBATIM (question + options + "\n'
        '                  "the ➤ line), no summarising.")\n'
        '        stop_block(cwd, payload, reason, code="TDQ:LOG")\n'
        "        return",
        label="stop_gate_hard_log_agy_exemptions",
        sentinel="_is_agy_log_exempt(cand)",
    )
    replace_exact(
        stop_path,
        "def _repo_changed(cwd, snap):",
        "def _is_agy_log_exempt(path):\n"
        '    p = str(path or "").replace("\\\\", "/").lstrip("./").lower()\n'
        "    if not p:\n"
        "        return True\n"
        '    if p.startswith(("docs/.staging", "docs/tdq/", "graphify-out/")) or "/.staging" in p:\n'
        "        return True\n"
        '    return p.endswith(".tmp")\n\n\n'
        "def _shell_change_check(cwd, snap):\n"
        '    before = snap.get("repo_sha")\n'
        "    if not isinstance(before, str):\n"
        '        return False, ""\n'
        "    from tdq_state import _EXCLUDE as _tdq_exc, _git as _tdq_git\n"
        '    status = _tdq_git(cwd, "status", "--porcelain", "--untracked-files=all", "--", ":(top)", *_tdq_exc)\n'
        "    if status is None:\n"
        '        return False, ""\n'
        "    now = repo_status_digest(cwd, status=status)\n"
        "    if not isinstance(now, str) or now == before:\n"
        '        return False, ""\n'
        '    prev = snap.get("repo_paths")\n'
        "    prev_set = set(prev) if isinstance(prev, list) else set()\n"
        '    fresh, known = "", ""\n'
        "    for p in repo_status_paths(cwd, status=status):\n"
        "        if not isinstance(p, str) or p.startswith(BOOKKEEPING) or (is_agy() and _is_agy_log_exempt(p)):\n"
        "            continue\n"
        "        if p not in prev_set:\n"
        "            fresh = fresh or p\n"
        "        else:\n"
        "            known = known or p\n"
        "    return True, (fresh or known)[:MAX_PATH_CHARS]\n\n\n"
        "def _repo_changed(cwd, snap):",
        label="stop_gate_single_git_status_helper",
        sentinel="def _shell_change_check(",
    )
    replace_exact(
        stop_path,
        "    if not hints:\n"
        "        return\n"
        '    text = "\\n".join(hints[:MAX_LINES])\n'
        "    if len(text) > MAX_CHARS:\n"
        '        text = text[:MAX_CHARS - 1].rstrip() + "…"\n'
        "    if is_agy():\n"
        '        if _common._RUNTIME_STATE.get("event") == "Stop":\n'
        '            queue_remind(cwd, payload, "STOP", text)\n'
        "        else:\n"
        "            emit_context([text])\n"
        "    else:\n"
        "        print(json.dumps({\n"
        '            "hookSpecificOutput": {"hookEventName": "Stop", "additionalContext": text}\n'
        "        }, ensure_ascii=False))",
        "    if is_agy():\n"
        "        dod_lines = _dod_hint(cwd, state)\n"
        "        if dod_lines:\n"
        '            queue_remind(cwd, payload, "DOD", dod_lines[0])\n'
        "        for code, (event, message) in EFFECTS.items():\n"
        '            short_code = code[4:] if code.startswith("TDQ:") else code\n'
        "            if (code in reminded or short_code in reminded) and event not in done:\n"
        "                queue_remind(cwd, payload, short_code, message)\n"
        '        if "TDQ:APPROVE" in reminded or "APPROVE" in reminded:\n'
        "            target = cong_dang_cho(state)\n"
        "            if target:\n"
        '                queue_remind(cwd, payload, "APPROVE", f"{target} approval pending")\n'
        '        if "TDQ:GIT" in reminded or "GIT" in reminded:\n'
        '            queue_remind(cwd, payload, "GIT", "Re-check branch/commit convention")\n'
        "        mark_turn_closed(cwd, sid)\n"
        "        return\n"
        "    if not hints:\n"
        "        return\n"
        '    text = "\\n".join(hints[:MAX_LINES])\n'
        "    if len(text) > MAX_CHARS:\n"
        '        text = text[:MAX_CHARS - 1].rstrip() + "…"\n'
        "    print(json.dumps({\n"
        '        "hookSpecificOutput": {"hookEventName": "Stop", "additionalContext": text}\n'
        "    }, ensure_ascii=False))",
        label="stop_gate_agy_soft_hints_and_turn_closed",
        sentinel='queue_remind(cwd, payload, "DOD"',
    )


def _patch_session_start(hooks_scripts_dir: Path) -> None:
    """Add 7-day .tdq-runtime cleanup and disable TDQ:DEVTOOL on Antigravity."""
    ss_path = hooks_scripts_dir / "session_start.py"
    ss_text = read_utf8(ss_path)
    if "emit_context(" not in ss_text:
        ss_text = ss_text.replace(
            "from _common import (",
            "from _common import (\n    emit_context,",
            1,
        )
        ss_text = ss_text.replace("    print(rewritten)", "    emit_context([rewritten])", 1)
        write_utf8(ss_path, ss_text)
    replace_exact(
        ss_path,
        "from _common import (INVESTIGATE_GON_TEXT, already_reminded, emit_context, is_agy, payload_cwd,",
        "from _common import (INVESTIGATE_GON_TEXT, already_reminded, cleanup_stale_runtime, emit_context, is_agy, payload_cwd,",
        label="session_start_import_cleanup",
        sentinel="cleanup_stale_runtime",
    )
    replace_exact(
        ss_path,
        "    payload = read_payload()\n    cwd = payload_cwd(payload)",
        "    payload = read_payload()\n    cwd = payload_cwd(payload)\n    cleanup_stale_runtime(cwd)",
        label="session_start_run_cleanup",
        sentinel="cleanup_stale_runtime(cwd)",
    )
    replace_exact(
        ss_path,
        '    nhac_devtool = ""\n'
        "    try:\n"
        "        nhac_devtool = tdq_devtool_mcp.check_session_start(cwd=cwd)\n"
        "    except Exception:\n"
        "        pass",
        '    nhac_devtool = ""\n'
        "    if not is_agy():\n"
        "        try:\n"
        "            nhac_devtool = tdq_devtool_mcp.check_session_start(cwd=cwd)\n"
        "        except Exception:\n"
        "            pass",
        label="session_start_skip_devtool_agy",
        sentinel="if not is_agy():\n        try:\n            nhac_devtool = tdq_devtool_mcp.check_session_start",
    )


def _patch_subagent_stop(hooks_scripts_dir: Path) -> None:
    """Place utf8_io after __future__ import on subagent_stop.py (PostToolUse registers role only)."""
    sub_path = hooks_scripts_dir / "subagent_stop.py"
    if not sub_path.is_file():
        return
    replace_exact(
        sub_path,
        "from __future__ import annotations\n",
        "from __future__ import annotations\n\n"
        "import os as _tdq_os, sys as _tdq_sys\n"
        "_tdq_here = _tdq_os.path.dirname(_tdq_os.path.abspath(__file__))\n"
        "_tdq_scripts = _tdq_os.path.normpath(_tdq_os.path.join(_tdq_here, '..', '..', 'scripts'))\n"
        "for _p in (_tdq_scripts, _tdq_here):\n"
        "    if _tdq_os.path.isdir(_p) and _p not in _tdq_sys.path:\n"
        "        _tdq_sys.path.insert(0, _p)\n"
        "import utf8_io  # noqa: E402,F401\n",
        label="subagent_stop_utf8_io",
        sentinel="import utf8_io",
    )


def apply_all(hooks_scripts_dir: Path) -> None:
    """Write dual-protocol _common.py, new AGY hooks, and upgrade all hook gates."""
    write_utf8(hooks_scripts_dir / "_common.py", COMMON_PY)
    write_utf8(hooks_scripts_dir / "post_invocation.py", POST_INVOCATION_PY)
    write_utf8(hooks_scripts_dir / "subagent_dispatch_gate.py", SUBAGENT_DISPATCH_GATE_PY)

    for py_file in sorted(hooks_scripts_dir.glob("*.py")):
        if py_file.name in (
            "_common.py",
            "post_invocation.py",
            "subagent_dispatch_gate.py",
            "subagent_stop.py",
            "codex_edit_gate.py",
            "dispatch.py",
            "gate_guidance.py",
        ):
            continue
        ensure_utf8_import(py_file)

    _patch_ask_gate(hooks_scripts_dir)
    _patch_bash_gate(hooks_scripts_dir)
    _patch_edit_gate(hooks_scripts_dir)
    _patch_read_gate(hooks_scripts_dir)
    _patch_lsp_gate(hooks_scripts_dir)
    _patch_search_gate(hooks_scripts_dir)
    _patch_search_observe(hooks_scripts_dir)
    _patch_prompt_context(hooks_scripts_dir)
    _patch_stop_gate(hooks_scripts_dir)
    _patch_session_start(hooks_scripts_dir)
    _patch_subagent_stop(hooks_scripts_dir)
