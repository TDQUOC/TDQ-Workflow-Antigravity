#!/usr/bin/env python3
"""Stdio JSON-RPC 2.0 MCP proxy that shrinks schema metadata and filler prose.

Intercepts `tools/list`, `prompts/list`, and `resources/list` responses to strip
redundant JSON Schema metadata (`$schema`, `title`, `examples`, `example`,
`$comment`) and trim filler prose in descriptions while preserving structural
keys (`properties`, `required`, `enum`, `const`, `default`, `$ref`, `type`) and
sentences containing constraint tokens verbatim. All `tools/call` payloads and
unparsed lines pass through untouched.

Env:
    TDQ_CAVEMAN=0: Disable shrinking and run raw line-by-line passthrough.
    TDQ_LOG=0: Silence ISO-timestamped diagnostic logs on stderr.
"""

from __future__ import annotations

import argparse
import io
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import threading
from datetime import datetime
from typing import Any

import utf8_io  # noqa: F401 — forces UTF-8 stdio on Windows

SHRINK_METHODS = frozenset({"tools/list", "prompts/list", "resources/list"})
DROP_SCHEMA_KEYS = frozenset({"$schema", "title", "examples", "example", "$comment"})
PROPERTY_MAP_KEYS = frozenset({"properties", "patternProperties", "$defs", "definitions"})
VERBATIM_SCHEMA_KEYS = frozenset({"const", "default", "enum"})
CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)

_CONSTRAINT_RE = re.compile(
    r"(?:\b(?:not|never|only|must|cannot|required|default|const|warning|deprecated)\b"
    r"|\b\w+n't\b|\$ref)",
    re.IGNORECASE,
)
_SENT_SPLIT_RE = re.compile(
    r"(?<!e\.g)(?<!i\.e)(?<!etc)(?<!vs)(?<=[.!?])\s+(?=[A-Z0-9`\"'(\[])"
)
_PAREN_EG_RE = re.compile(
    r"\s*\((?:e\.g\.|for example|such as)(?=[\W_])[^)]*\)",
    re.IGNORECASE,
)
_LEAD_FILLER_RE = re.compile(
    r"^(?:(?:This tool|Use this(?:\s+tool)?\s+to|Allows you to|Enables you to|"
    r"Used to|In order to)\s+)+",
    re.IGNORECASE,
)
_FILLER_WORD_RE = re.compile(
    r"\b(?:please|simply|just|basically|actually|essentially|generally|"
    r"typically|usually)\b\s*",
    re.IGNORECASE,
)


def _log(message: str) -> None:
    """Write an ISO-timestamped diagnostic line to stderr unless TDQ_LOG=0."""
    if os.environ.get("TDQ_LOG", "1") != "0":
        stamp = datetime.now().isoformat(timespec="seconds")
        print(f"[{stamp}] tdq_mcp_shrink: {message}", file=sys.stderr, flush=True)


def _clean_lead_sentence(sentence: str) -> str:
    """Strip parenthetical examples and filler phrases from a non-constraint sentence."""
    cleaned = _PAREN_EG_RE.sub("", sentence)
    cleaned = _LEAD_FILLER_RE.sub("", cleaned)
    cleaned = _FILLER_WORD_RE.sub("", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if cleaned and cleaned[0].islower():
        return cleaned[0].upper() + cleaned[1:]
    return cleaned


def shrink_description(text: str) -> str:
    """Shorten a description while keeping every constraint sentence verbatim."""
    if not isinstance(text, str):
        return text
    stripped = text.strip()
    if not stripped:
        return ""
    sentences = [s.strip() for s in _SENT_SPLIT_RE.split(stripped) if s.strip()]
    if not sentences:
        return stripped
    kept: list[str] = []
    for idx, sent in enumerate(sentences):
        if _CONSTRAINT_RE.search(sent):
            kept.append(sent)
        elif idx == 0:
            cleaned = _clean_lead_sentence(sent)
            if cleaned:
                kept.append(cleaned)
    return " ".join(kept) if kept else sentences[0]


def _shrink_schema_dict(node: dict[str, Any], in_prop_map: bool) -> dict[str, Any]:
    """Recursively shrink one JSON Schema dictionary node."""
    if in_prop_map:
        return {key: shrink_schema_node(val) for key, val in node.items()}
    out: dict[str, Any] = {}
    for key, val in node.items():
        if key in DROP_SCHEMA_KEYS:
            continue
        if key in VERBATIM_SCHEMA_KEYS:
            out[key] = val
        elif key == "description" and isinstance(val, str):
            out[key] = shrink_description(val)
        elif key in PROPERTY_MAP_KEYS and isinstance(val, dict):
            out[key] = _shrink_schema_dict(val, True)
        else:
            out[key] = shrink_schema_node(val)
    return out


def shrink_schema_node(node: Any) -> Any:
    """Recursively remove redundant schema metadata while keeping constraints intact."""
    if isinstance(node, list):
        return [shrink_schema_node(item) for item in node]
    if isinstance(node, dict):
        return _shrink_schema_dict(node, False)
    return node


def _shrink_tool_entry(tool: Any) -> Any:
    """Shrink description and input/output schema on a single tools/list entry."""
    if not isinstance(tool, dict):
        return tool
    out = dict(tool)
    if isinstance(out.get("description"), str):
        out["description"] = shrink_description(out["description"])
    for key in ("inputSchema", "outputSchema", "parameters"):
        if key in out:
            out[key] = shrink_schema_node(out[key])
    return out


def _shrink_prompt_entry(prompt: Any) -> Any:
    """Shrink description and argument descriptions on a prompts/list entry."""
    if not isinstance(prompt, dict):
        return prompt
    out = dict(prompt)
    if isinstance(out.get("description"), str):
        out["description"] = shrink_description(out["description"])
    args = out.get("arguments")
    if isinstance(args, list):
        out["arguments"] = [_shrink_resource_entry(arg) for arg in args]
    return out


def _shrink_resource_entry(item: Any) -> Any:
    """Shrink description on a resources/list entry or prompt argument."""
    if not isinstance(item, dict):
        return item
    out = dict(item)
    if isinstance(out.get("description"), str):
        out["description"] = shrink_description(out["description"])
    return out


def transform_rpc_response(msg: dict[str, Any], method: str | None) -> dict[str, Any]:
    """Transform list responses for tracked MCP methods; leave all else untouched."""
    if not isinstance(msg, dict) or method not in SHRINK_METHODS:
        return msg
    result = msg.get("result")
    if not isinstance(result, dict):
        return msg
    new_result = dict(result)
    if method == "tools/list" and isinstance(new_result.get("tools"), list):
        new_result["tools"] = [_shrink_tool_entry(t) for t in new_result["tools"]]
    elif method == "prompts/list" and isinstance(new_result.get("prompts"), list):
        new_result["prompts"] = [_shrink_prompt_entry(p) for p in new_result["prompts"]]
    elif method == "resources/list" and isinstance(new_result.get("resources"), list):
        new_result["resources"] = [
            _shrink_resource_entry(r) for r in new_result["resources"]
        ]
    out = dict(msg)
    out["result"] = new_result
    return out


def _id_key(msg_id: Any) -> tuple[str, Any]:
    """Build a collision-free lookup key for JSON-RPC request IDs."""
    return (type(msg_id).__name__, msg_id)


def _is_binary_stream(stream: Any) -> bool:
    """Return True if stream reads or writes raw bytes rather than str."""
    if isinstance(stream, io.TextIOBase):
        return False
    return isinstance(stream, (io.RawIOBase, io.BufferedIOBase)) or hasattr(
        stream, "read1"
    )


def _read_line_bytes(stream: Any) -> bytes | None:
    """Read one line from a binary or text stream, returning None at EOF."""
    raw = stream.readline()
    if not raw:
        return None
    if isinstance(raw, bytes):
        return raw
    return raw.encode("utf-8", errors="replace")


def _write_line_bytes(stream: Any, data: bytes) -> None:
    """Write bytes to a binary or text stream and flush immediately."""
    if _is_binary_stream(stream):
        stream.write(data)
    else:
        stream.write(data.decode("utf-8", errors="replace"))
    stream.flush()


def _resolve_command(cmd: list[str]) -> list[str]:
    """Resolve executable path on PATH when not already an explicit file."""
    if not cmd:
        return cmd
    head = cmd[0]
    if os.path.exists(head):
        return cmd
    resolved = shutil.which(head)
    if resolved:
        return [resolved, *cmd[1:]]
    return cmd


def _build_popen_kwargs(platform: str | None = None) -> dict[str, Any]:
    """Build subprocess.Popen kwargs with UTF-8/unbuffered env and Windows flag."""
    env = dict(os.environ)
    env["PYTHONUTF8"] = "1"
    env["PYTHONUNBUFFERED"] = "1"
    kwargs: dict[str, Any] = {
        "stdin": subprocess.PIPE,
        "stdout": subprocess.PIPE,
        "stderr": None,
        "env": env,
    }
    target_platform = platform or sys.platform
    if target_platform.startswith("win"):
        kwargs["creationflags"] = CREATE_NO_WINDOW
    return kwargs


def _track_request_line(
    raw_line: bytes,
    pending: dict[tuple[str, Any], str],
    lock: threading.Lock,
) -> None:
    """Record id -> method for tracked JSON-RPC list requests; ignore invalid JSON."""
    text = raw_line.strip()
    if not text:
        return
    try:
        msg = json.loads(text.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return
    if not isinstance(msg, dict):
        return
    method = msg.get("method")
    msg_id = msg.get("id")
    if method in SHRINK_METHODS and msg_id is not None:
        with lock:
            pending[_id_key(msg_id)] = method


def _forward_client_to_child(
    in_stream: Any,
    child_stdin: Any,
    pending: dict[tuple[str, Any], str],
    lock: threading.Lock,
    passthrough: bool,
) -> None:
    """Pump lines from client stdin to child stdin and close child stdin at EOF."""
    try:
        while True:
            raw_line = _read_line_bytes(in_stream)
            if raw_line is None:
                break
            if not passthrough:
                _track_request_line(raw_line, pending, lock)
            child_stdin.write(raw_line)
            child_stdin.flush()
    except (BrokenPipeError, OSError, ValueError):
        pass
    finally:
        try:
            child_stdin.close()
        except OSError:
            pass


def _process_server_line(
    raw_line: bytes,
    pending: dict[tuple[str, Any], str],
    lock: threading.Lock,
    passthrough: bool,
) -> bytes:
    """Shrink tracked MCP list responses; pass all other lines through safely."""
    if passthrough:
        return raw_line
    stripped = raw_line.rstrip(b"\r\n")
    if not stripped.strip():
        return b"\n" if raw_line.endswith(b"\n") else raw_line
    try:
        msg = json.loads(stripped.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return stripped + b"\n" if raw_line.endswith(b"\n") else raw_line
    if isinstance(msg, dict) and "id" in msg and "method" not in msg:
        with lock:
            method = pending.pop(_id_key(msg["id"]), None)
        if method in SHRINK_METHODS:
            shrunk = transform_rpc_response(msg, method)
            payload = json.dumps(shrunk, ensure_ascii=False, separators=(",", ":"))
            out_bytes = (payload + "\n").encode("utf-8")
            _log(f"shrunk {method} ({len(raw_line)}B -> {len(out_bytes)}B)")
            return out_bytes
    return stripped + b"\n"


def run_proxy(cmd: list[str], stdin: Any = None, stdout: Any = None) -> int:
    """Spawn target MCP stdio server and proxy JSON-RPC lines between stdio pipes."""
    if not cmd:
        _log("missing target command")
        return 2
    in_stream = stdin if stdin is not None else getattr(sys.stdin, "buffer", sys.stdin)
    out_stream = stdout if stdout is not None else getattr(sys.stdout, "buffer", sys.stdout)
    passthrough = os.environ.get("TDQ_CAVEMAN", "1") == "0"
    resolved_cmd = _resolve_command(cmd)
    _log(f"starting proxy (passthrough={passthrough}) cmd={resolved_cmd[0]}")
    try:
        proc = subprocess.Popen(resolved_cmd, **_build_popen_kwargs())
    except OSError as exc:
        _log(f"failed to start target command: {exc}")
        return 1

    pending: dict[tuple[str, Any], str] = {}
    lock = threading.Lock()
    writer = threading.Thread(
        target=_forward_client_to_child,
        args=(in_stream, proc.stdin, pending, lock, passthrough),
        daemon=True,
    )
    writer.start()

    try:
        while proc.stdout is not None:
            raw_line = _read_line_bytes(proc.stdout)
            if raw_line is None:
                break
            out_line = _process_server_line(raw_line, pending, lock, passthrough)
            _write_line_bytes(out_stream, out_line)
    except (BrokenPipeError, OSError):
        pass
    finally:
        writer.join(timeout=0.2)
    rc = proc.wait()
    _log(f"proxy exiting rc={rc}")
    return int(rc)


def _split_cmd_string(raw_cmd: str) -> list[str]:
    """Split a single command string into argv tokens safely across Windows/POSIX."""
    tokens = shlex.split(raw_cmd, posix=(os.name != "nt"))
    cleaned: list[str] = []
    for token in tokens:
        if len(token) >= 2 and token[0] == token[-1] and token[0] in ('"', "'"):
            cleaned.append(token[1:-1])
        else:
            cleaned.append(token)
    return cleaned


def parse_args(argv: list[str] | None = None) -> list[str]:
    """Extract target MCP server command from `-- <cmd...>` or `--cmd <cmd...>`."""
    args_list = list(sys.argv[1:] if argv is None else argv)
    if "--" in args_list:
        idx = args_list.index("--")
        return args_list[idx + 1 :]

    parser = argparse.ArgumentParser(
        prog="tdq_mcp_shrink.py",
        description="Stdio JSON-RPC 2.0 MCP proxy that shrinks schema descriptions.",
    )
    parser.add_argument(
        "--cmd",
        nargs="+",
        required=True,
        help="Target MCP server command and arguments.",
    )
    ns = parser.parse_args(args_list)
    if len(ns.cmd) == 1 and " " in ns.cmd[0] and not os.path.exists(ns.cmd[0]):
        return _split_cmd_string(ns.cmd[0])
    return list(ns.cmd)


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for tdq_mcp_shrink."""
    cmd = parse_args(argv)
    return run_proxy(cmd)


if __name__ == "__main__":
    sys.exit(main())
