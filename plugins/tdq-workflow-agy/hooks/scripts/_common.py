#!/usr/bin/env python3
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
    "PLAIN",
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
