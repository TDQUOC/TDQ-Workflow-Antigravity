#!/usr/bin/env python3
"""SubagentStop / AGY PostToolUse+Stop handler: verify clean commit, validate handoff, log telemetry & Blackboard."""

from __future__ import annotations

import os as _tdq_os, sys as _tdq_sys
_tdq_here = _tdq_os.path.dirname(_tdq_os.path.abspath(__file__))
_tdq_scripts = _tdq_os.path.normpath(_tdq_os.path.join(_tdq_here, '..', '..', 'scripts'))
for _p in (_tdq_scripts, _tdq_here):
    if _tdq_os.path.isdir(_p) and _p not in _tdq_sys.path:
        _tdq_sys.path.insert(0, _p)
import utf8_io  # noqa: E402,F401

import argparse
import json
import os
import re
import sys

_HOOKS_DIR = os.path.dirname(os.path.abspath(__file__))
if _HOOKS_DIR not in sys.path:
    sys.path.insert(0, _HOOKS_DIR)

import _common  # noqa: E402
from _common import (  # noqa: E402
    detect_subagent,
    emit_context,
    is_agy,
    payload_cwd,
    read_payload,
    register_subagent_role,
    session_id,
    stop_block,
)
import tdq_state  # noqa: E402
import tdq_team  # noqa: E402
import tdq_ten_lenh  # noqa: E402

_TASK_CODE_RE = re.compile(r"\b(T\d+[A-Za-z]*\.\d+[a-z]?|Q\d+)\b")
_WRITER_ROLES = ("implementer", "build-resolver", "refactor-cleaner")


def _extract_task_code(text: str) -> str:
    m = _TASK_CODE_RE.search(text or "")
    return m.group(1) if m else ""


def _parse_response_dict(raw) -> dict:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str) and raw.strip().startswith("{"):
        try:
            obj = json.loads(raw)
            return obj if isinstance(obj, dict) else {}
        except ValueError:
            return {}
    return {}


def _extract_spawn_meta(payload: dict) -> dict:
    tinput = payload.get("tool_input") if isinstance(payload.get("tool_input"), dict) else {}
    resp = _parse_response_dict(
        payload.get("response") or payload.get("output") or payload.get("tool_response")
    )
    nested = resp.get("result") if isinstance(resp.get("result"), dict) else {}
    conv_id = str(
        nested.get("conversationId")
        or resp.get("conversationId")
        or resp.get("agentId")
        or payload.get("agent_id")
        or ""
    ).strip()
    role = str(
        tinput.get("TypeName")
        or tinput.get("subagent_type")
        or tinput.get("name")
        or tinput.get("Role")
        or payload.get("agent_type")
        or ""
    ).strip()
    prompt_txt = str(tinput.get("Prompt") or tinput.get("brief") or tinput.get("prompt") or "")
    task_id = _extract_task_code(prompt_txt or role)
    model = str(tinput.get("Model") or tinput.get("model") or "").strip()
    effort = str(tinput.get("effort") or "").strip()
    return {
        "conv_id": conv_id,
        "role": role,
        "task_id": task_id,
        "model": model,
        "effort": effort,
        "prompt": prompt_txt,
    }


def _extract_last_message(payload: dict) -> str:
    for key in ("last_assistant_message", "response", "output", "tool_response"):
        val = payload.get(key)
        if isinstance(val, str) and val.strip():
            return val
        if isinstance(val, dict):
            return json.dumps(val, ensure_ascii=False)
    return ""


def _resolve_worktree_dir(cwd: str, task_id: str) -> str | None:
    real_cwd = os.path.realpath(cwd or ".")
    if (os.sep + ".tdq-worktrees" + os.sep) in (real_cwd + os.sep):
        return real_cwd
    if not task_id:
        return None
    st = tdq_state.load(cwd, heal=False) or {}
    slug = st.get("active_request") or ""
    if not slug:
        return None
    base = os.environ.get("TDQ_WORKTREE_DIR") or os.path.join(cwd, ".tdq-worktrees")
    cand = os.path.join(base, slug, task_id.lower())
    return cand if os.path.isdir(cand) else None


def _dirty_worktree_lines(wt_dir: str | None) -> list[str]:
    if not wt_dir or not os.path.exists(os.path.join(wt_dir, ".git")):
        return []
    proc = tdq_ten_lenh.chay_subprocess(
        ["git", "-C", wt_dir, "status", "--porcelain"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=10,
    )
    if proc.returncode != 0:
        return []
    return [ln for ln in proc.stdout.splitlines() if ln.strip()]


def _handle_spawn_event(payload: dict, cwd: str, event_name: str) -> int:
    meta = _extract_spawn_meta(payload)
    if meta["conv_id"] and meta["role"]:
        register_subagent_role(
            cwd, meta["conv_id"], meta["role"],
            target_task=meta["task_id"], model=meta["model"], effort=meta["effort"],
        )
        tdq_state._info(
            f"subagent_stop({event_name}): registered {meta['conv_id']} -> {meta['role']}"
        )
    if event_name == "PostToolUse" and meta["role"]:
        sub_sid = meta["conv_id"] or session_id(payload)
        handle_subagent_stop(
            {
                **payload,
                "agent_type": meta["role"],
                "conversationId": sub_sid,
                "conversation_id": sub_sid,
                "session_id": sub_sid,
            },
            cwd,
            allow_stop_block=False,
        )
    return 0


def _record_stop_outcomes(
    cwd: str, payload: dict, role: str, task_id: str, status: str,
    model: str, effort: str, parsed: dict, msg: str, handoff_valid: bool,
    allow_stop_block: bool,
) -> None:
    files = parsed.get("files") if isinstance(parsed.get("files"), list) else []
    telemetry_dir = os.path.join(cwd, "docs", "tdq")
    tel_fn = getattr(_common, "append_agent_telemetry", None)
    if os.path.isdir(telemetry_dir) and callable(tel_fn):
        tel_fn(cwd, {
            "session": session_id(payload), "role": role, "task_id": task_id,
            "status": status, "model": model, "effort": effort,
            "elapsed_s": parsed.get("elapsed_s"), "attempt": parsed.get("attempt") or 1,
            "files_count": len(files), "first_pass": status in ("done", "completed"),
            "outcome": status, "handoff_valid": handoff_valid,
        })
    if status in ("failed", "blocked"):
        notes = str(parsed.get("notes") or msg[:300] or "subagent failed")
        blocker = str(parsed.get("blocker") or "")
        tdq_team.blackboard_record(
            cwd, task_id or "UNKNOWN", status, notes, role=role, model=model,
            files=files, error=blocker or notes, test_command=str(parsed.get("test_result") or ""),
        )
        if allow_stop_block and not is_agy():
            emit_context([f"[TDQ:BLACKBOARD] Recorded {status} diagnostic for {task_id or role}."])


def handle_subagent_stop(payload: dict, cwd: str, allow_stop_block: bool = True) -> bool:
    """Validate subagent exit state, append telemetry, and sync Blackboard on failures."""
    info = detect_subagent(payload, cwd)
    role = str(info.get("role") or payload.get("agent_type") or "").strip()
    is_sub = bool(info.get("is_subagent")) or bool(payload.get("agent_id")) or bool(role)
    if not is_sub:
        return False
    role = role or "unknown"
    msg = _extract_last_message(payload)
    parsed = tdq_team.parse_handoff_from_text(msg)
    handoff_valid = False
    if parsed:
        handoff_valid, errs = tdq_team.validate_handoff_payload(parsed, project=cwd)
        if not handoff_valid:
            tdq_state._info(f"subagent_stop: invalid handoff for {role}: {'; '.join(errs[:2])}")
    task_id = str(parsed.get("task_id") or info.get("task") or _extract_task_code(msg) or "")
    status = str(parsed.get("status") or ("failed" if payload.get("error") else "done")).lower()
    if allow_stop_block and not payload.get("stop_hook_active") and status not in ("failed", "blocked"):
        if any(w in role.lower() for w in _WRITER_ROLES):
            dirty = _dirty_worktree_lines(_resolve_worktree_dir(cwd, task_id))
            if dirty:
                reason = (
                    f"[TDQ:WORKTREE] Uncommitted changes in {task_id or 'worktree'} ({dirty[0][:60]}). "
                    "Run `git add` on VÙNG FILE and `git commit` inside the worktree before returning."
                )
                stop_block(cwd, payload, reason, code="TDQ:WORKTREE", stop_hook_active=False)
                return True
    model = str(parsed.get("model") or info.get("model") or "")
    effort = str(parsed.get("effort") or info.get("effort") or "")
    _record_stop_outcomes(
        cwd, payload, role, task_id, status, model, effort, parsed, msg, handoff_valid, allow_stop_block,
    )
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Handle SubagentStop and subagent PostToolUse telemetry.")
    parser.add_argument("--event", default=None, help="Hook event hint (PreToolUse|PostToolUse|SubagentStop|Stop)")
    args = parser.parse_args(argv)
    payload = read_payload()
    cwd = payload_cwd(payload)
    event_name = args.event or str(payload.get("hook_event_name") or payload.get("hookEventName") or "SubagentStop")
    if event_name in ("PreToolUse", "PostToolUse"):
        return _handle_spawn_event(payload, cwd, event_name)
    handle_subagent_stop(payload, cwd, allow_stop_block=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
