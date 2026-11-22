#!/usr/bin/env python3
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
        or payload.get("agentId")
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
