#!/usr/bin/env python3
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
