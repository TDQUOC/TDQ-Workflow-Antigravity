#!/usr/bin/env python3
"""MCP tool policy classifier, schema SHA-256 baseline, and balanced quarantine.

Env: TDQ_LOG=0 disables ISO-timestamped diagnostics on stderr.
"""

from __future__ import annotations

import argparse
import contextlib
import copy
import hashlib
import json
import os
import sys
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCRIPT_ROOT = Path(__file__).resolve().parent
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

import tdq_config
import tdq_lease
import utf8_io  # noqa: F401

POLICY_DEFAULT_REL = "scripts/defaults/mcp-policy.default.json"
POLICY_PROJECT_REL = "docs/tdq/mcp-policy.json"
_DESTRUCTIVE_VERBS: tuple[str, ...] = (
    "delete",
    "remove",
    "drop",
    "destroy",
    "exec",
    "execute",
    "run",
    "push",
    "deploy",
    "reset",
)
_LIST_POLICY_KEYS: tuple[str, ...] = (
    "trusted_servers",
    "read_prefixes",
    "write_prefixes",
)
_BUILTIN_DEFAULT_POLICY: dict[str, Any] = {
    "schema_version": 1,
    "mode": "balanced",
    "trusted_servers": [
        "tdq-lsp",
        "tdq-workflow-agy_lsp",
        "gemini-api_gemini-api-docs",
        "chrome-devtools",
        "tdq-workflow-agy_chrome-devtools",
        "tavily-primary",
        "tdq-workflow-agy_tavily-primary",
    ],
    "read_prefixes": [
        "read_",
        "get_",
        "list_",
        "select_",
        "search_",
        "find_",
        "inspect_",
        "explore",
        "go_to_",
        "type_",
        "callers",
        "blast_radius",
        "start_lsp",
        "detect_",
        "preview_",
        "take_snapshot",
        "take_screenshot",
        "wait_for",
    ],
    "write_prefixes": [
        "write_",
        "edit_",
        "create_",
        "update_",
        "delete_",
        "remove_",
        "apply_",
        "replace_",
        "insert_",
        "rename_",
        "commit_",
        "execute_",
        "run_",
        "push_",
        "deploy_",
        "send_",
        "post_",
        "upload_",
        "fill",
        "click",
        "drag",
        "press_",
        "type_text",
        "evaluate_script",
        "handle_dialog",
    ],
    "approved_tools": {},
}


def _log_enabled() -> bool:
    """Return True unless TDQ_LOG=0 disables stderr logging."""
    return os.environ.get("TDQ_LOG", "1") != "0"


def _log(message: str) -> None:
    """Emit one ISO-8601 diagnostic line to stderr when TDQ_LOG is enabled."""
    if _log_enabled():
        stamp = datetime.now(UTC).isoformat(timespec="seconds")
        print(f"[{stamp}] mcp_policy: {message}", file=sys.stderr)


def _normalize_server(server: str | None) -> str:
    val = (server or "").strip()
    return "" if val in ("", "_") else val


def _tool_key(server: str | None, tool_name: str) -> str:
    srv = _normalize_server(server)
    tool = (tool_name or "").strip()
    return f"{srv}::{tool}" if srv else tool


def _strip_tool_prefix(srv_lower: str, tool_lower: str) -> str:
    stripped = tool_lower
    if srv_lower and tool_lower.startswith(f"mcp__{srv_lower}__"):
        stripped = tool_lower[len(f"mcp__{srv_lower}__") :]
    elif tool_lower.startswith("mcp__") and "__" in tool_lower[5:]:
        stripped = tool_lower.split("__", 2)[2]
    elif tool_lower.startswith("lsp."):
        stripped = tool_lower[4:]
    return stripped or tool_lower


def _lower_list(raw: Any) -> list[str]:
    if not isinstance(raw, list):
        return []
    return [str(item).strip().lower() for item in raw if str(item).strip()]


def _is_destructive_verb(tool_short: str) -> bool:
    return any(tool_short == verb or tool_short.startswith(verb) for verb in _DESTRUCTIVE_VERBS)


def _matches_any_prefix(tool_short: str, prefixes: list[str]) -> bool:
    return any(tool_short == prefix or tool_short.startswith(prefix) for prefix in prefixes)


def canonical_schema_hash(schema_obj: Any = None) -> str:
    """Return canonical SHA-256 hex digest for a JSON-serializable schema object."""
    payload = json.dumps(
        schema_obj if schema_obj is not None else {},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _read_json_dict(path: Path, label: str) -> tuple[dict[str, Any] | None, bool]:
    if not path.is_file():
        return None, False
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        _log(f"WARN unreadable {label} policy at {path}: {exc}")
        return None, True
    if not isinstance(parsed, dict):
        _log(f"WARN {label} policy at {path} is not a JSON object")
        return None, True
    return parsed, False


def _load_baseline() -> dict[str, Any]:
    default_path = SCRIPT_ROOT.parent / POLICY_DEFAULT_REL
    data, corrupt = _read_json_dict(default_path, "default")
    if corrupt or data is None:
        return copy.deepcopy(_BUILTIN_DEFAULT_POLICY)
    merged = copy.deepcopy(_BUILTIN_DEFAULT_POLICY)
    merged.update(data)
    if not isinstance(merged.get("approved_tools"), dict):
        merged["approved_tools"] = {}
    return merged


def _merge_list_overrides(
    merged: dict[str, Any], override: dict[str, Any]
) -> bool:
    for key in _LIST_POLICY_KEYS:
        if key not in override:
            continue
        if not isinstance(override[key], list):
            _log(f"WARN invalid {key!r} list in project mcp-policy.json")
            return False
        merged[key] = list(override[key])
    return True


def _merge_policy(
    baseline: dict[str, Any], override: dict[str, Any]
) -> tuple[dict[str, Any], bool]:
    merged = copy.deepcopy(baseline)
    if "mode" in override:
        raw_mode = override["mode"]
        if not isinstance(raw_mode, str) or not raw_mode.strip():
            _log("WARN invalid mode in project mcp-policy.json")
            return copy.deepcopy(baseline), True
        merged["mode"] = raw_mode.strip().lower()
    if not _merge_list_overrides(merged, override):
        return copy.deepcopy(baseline), True
    if "approved_tools" in override:
        approved = override["approved_tools"]
        if not isinstance(approved, dict):
            _log("WARN invalid approved_tools object in project mcp-policy.json")
            return copy.deepcopy(baseline), True
        merged["approved_tools"].update(copy.deepcopy(approved))
    return merged, False


def load_policy(cwd: str | Path) -> tuple[dict[str, Any], bool]:
    """Load baseline MCP policy merged with project overrides, flagging corruption."""
    baseline = _load_baseline()
    project_path = Path(cwd) / POLICY_PROJECT_REL
    project_data, corrupt = _read_json_dict(project_path, "project")
    if corrupt:
        return baseline, True
    if project_data is None:
        return baseline, False
    return _merge_policy(baseline, project_data)


def classify_tool_tier(server: str, tool_name: str, policy: dict[str, Any]) -> str:
    """Classify an MCP tool into 'read', 'write', or 'destructive'."""
    srv = _normalize_server(server).lower()
    tool = (tool_name or "").strip().lower()
    tool_short = _strip_tool_prefix(srv, tool)

    write_prefixes = _lower_list(policy.get("write_prefixes"))
    if _matches_any_prefix(tool_short, write_prefixes):
        return "destructive" if _is_destructive_verb(tool_short) else "write"

    trusted = set(_lower_list(policy.get("trusted_servers")))
    if srv in trusted or "lsp" in srv:
        return "read"

    read_prefixes = _lower_list(policy.get("read_prefixes"))
    if _matches_any_prefix(tool_short, read_prefixes):
        return "read"

    return "destructive" if _is_destructive_verb(tool_short) else "write"


def _load_p0_settings(cwd: str | Path) -> tuple[bool, str]:
    try:
        cfg = tdq_config.load_config(cwd)
    except Exception as exc:  # noqa: BLE001 — fail-closed defaults on config read error
        _log(f"WARN failed loading tdq_config: {exc}")
        return True, "balanced"
    p0_cfg = cfg.get("p0") if isinstance(cfg.get("p0"), dict) else {}
    raw_enabled = p0_cfg.get("mcp_quarantine_enabled", True)
    enabled = raw_enabled if isinstance(raw_enabled, bool) else True
    mode = str(p0_cfg.get("mcp_mode") or "balanced").strip().lower() or "balanced"
    return enabled, mode


def _lookup_approved_entry(
    approved: dict[str, Any], server: str, tool_name: str
) -> dict[str, Any] | None:
    norm_srv = _normalize_server(server)
    norm_tool = (tool_name or "").strip()
    candidates = [_tool_key(norm_srv, norm_tool)]
    if norm_srv:
        candidates.append(norm_tool)
        prefix = f"mcp__{norm_srv.lower()}__"
        if norm_tool.lower().startswith(prefix) and len(norm_tool) > len(prefix):
            candidates.append(f"{norm_srv}::{norm_tool[len(prefix) :]}")
    for key in candidates:
        entry = approved.get(key)
        if isinstance(entry, dict):
            return entry
    return None


def _allow_result(reason: str, tier: str, sha256: str) -> dict[str, Any]:
    return {
        "decision": "allow",
        "code": None,
        "reason": reason,
        "tier": tier,
        "sha256": sha256,
    }


def _deny_result(
    reason: str, tier: str, sha256: str, hint: str | None = None
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "decision": "deny",
        "code": "READONLY",
        "reason": reason,
        "tier": tier,
        "sha256": sha256,
    }
    if hint is not None:
        payload["hint"] = hint
    return payload


def is_denied(result: Any) -> bool:
    """Return True when an evaluate_tool_call result represents a quarantine deny."""
    return isinstance(result, dict) and result.get("decision") == "deny"


def split_eager_mcp_name(
    tool_name: str, policy: dict[str, Any] | None = None
) -> tuple[str | None, str | None]:
    """Split an MCP tool name (`mcp__srv__tool` or eager `mcp_srv_tool`) cleanly."""
    if not tool_name:
        return None, None
    if tool_name.startswith("mcp__"):
        parts = tool_name[5:].split("__", 1)
        return (parts[0], parts[1]) if len(parts) == 2 and parts[0] and parts[1] else (None, None)
    if not tool_name.startswith("mcp_"):
        return None, None
    rest = tool_name[4:]
    if "__" in rest:
        parts = rest.split("__", 1)
        return (parts[0], parts[1]) if len(parts) == 2 and parts[0] and parts[1] else (None, None)
    src_policy = policy if isinstance(policy, dict) else _BUILTIN_DEFAULT_POLICY
    trusted_raw = src_policy.get("trusted_servers")
    trusted_items = (
        [str(s).strip() for s in trusted_raw if isinstance(s, str) and str(s).strip()]
        if isinstance(trusted_raw, list)
        else []
    )
    rest_low = rest.lower()
    for srv in sorted(trusted_items, key=len, reverse=True):
        prefix_low = f"{srv.lower()}_"
        if rest_low.startswith(prefix_low) and len(rest) > len(prefix_low):
            return rest[: len(srv)], rest[len(srv) + 1 :]
    lsp_idx = rest_low.find("_lsp_")
    if lsp_idx > 0 and "_" not in rest[:lsp_idx] and lsp_idx + 5 < len(rest):
        return rest[: lsp_idx + 4], rest[lsp_idx + 5 :]
    parts = rest.split("_", 1)
    return (parts[0], parts[1]) if len(parts) == 2 and parts[0] and parts[1] else (None, None)


def _evaluate_approved_entry(
    policy: dict[str, Any],
    server: str,
    tool_name: str,
    tier: str,
    sha256: str,
) -> dict[str, Any]:
    approved = policy.get("approved_tools")
    approved_map = approved if isinstance(approved, dict) else {}
    entry = _lookup_approved_entry(approved_map, server, tool_name)
    key = _tool_key(server, tool_name)
    if entry is None or entry.get("sha256") != sha256:
        _log(f"deny server={server!r} tool={tool_name!r} tier={tier} key={key}")
        srv_arg = _normalize_server(server) or "_"
        return _deny_result(
            f"MCP tool '{key}' requires policy approval or schema hash changed.",
            tier,
            sha256,
            hint=f"py -3 scripts/mcp_policy.py approve {srv_arg} {tool_name}",
        )
    _log(f"allow server={server!r} tool={tool_name!r} tier={tier} key={key}")
    return _allow_result("approved_baseline_match", tier, sha256)


def evaluate_tool_call(
    cwd: str | Path,
    server: str,
    tool_name: str,
    schema_obj: Any = None,
) -> dict[str, Any]:
    """Evaluate whether an MCP tool call is allowed or quarantined under policy."""
    policy, corrupt = load_policy(cwd)
    tier = classify_tool_tier(server, tool_name, policy)
    sha256 = canonical_schema_hash(schema_obj)
    enabled, cfg_mode = _load_p0_settings(cwd)
    pol_mode = str(policy.get("mode") or "balanced").strip().lower() or "balanced"
    mode = pol_mode if pol_mode != "balanced" else cfg_mode

    if not enabled:
        _log(f"allow server={server!r} tool={tool_name!r} reason=mcp_quarantine_disabled")
        return _allow_result("mcp_quarantine_disabled", tier, sha256)

    srv = _normalize_server(server).lower()
    trusted = set(_lower_list(policy.get("trusted_servers")))
    if mode == "balanced" and (srv in trusted or "lsp" in srv or tier == "read"):
        _log(f"allow server={server!r} tool={tool_name!r} tier={tier} fast_path=1")
        return _allow_result("balanced_read_or_trusted", tier, sha256)

    if corrupt:
        _log(f"deny server={server!r} tool={tool_name!r} tier={tier} reason=corrupt_policy")
        return _deny_result(
            "Project mcp-policy.json is corrupt; write/destructive MCP tool blocked",
            tier,
            sha256,
        )

    return _evaluate_approved_entry(policy, server, tool_name, tier, sha256)


def _close_quietly(fd: int) -> None:
    with contextlib.suppress(OSError):
        os.close(fd)


def _write_all(fd: int, raw: bytes) -> None:
    view = memoryview(raw)
    written = 0
    while written < len(raw):
        written += os.write(fd, view[written:])
    os.fsync(fd)


def _replace_with_retry(src: Path, dst: Path) -> None:
    last_err: OSError | None = None
    for attempt in range(5):
        try:
            os.replace(src, dst)
            return
        except PermissionError as exc:
            last_err = exc
            time.sleep(0.005 * (attempt + 1))
        except OSError:
            src.unlink(missing_ok=True)
            raise
    src.unlink(missing_ok=True)
    if last_err is not None:
        raise last_err


def _atomic_write_json(target: Path, data: dict[str, Any]) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(data, indent=2) + "\n").encode("utf-8")
    tmp_name = f".tmp.{os.getpid()}.{threading.get_ident()}.{target.name}"
    tmp_path = target.with_name(tmp_name)
    fd = os.open(tmp_path, os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o666)
    try:
        _write_all(fd, raw)
    finally:
        _close_quietly(fd)
    _replace_with_retry(tmp_path, target)


def _read_existing_project_doc(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"schema_version": 1, "approved_tools": {}}
    data, corrupt = _read_json_dict(path, "project")
    if corrupt or data is None:
        raise ValueError(f"Corrupt project policy file: {path}")
    approved = data.get("approved_tools")
    if approved is None:
        data["approved_tools"] = {}
    elif not isinstance(approved, dict):
        raise ValueError(f"Invalid approved_tools in project policy file: {path}")
    return data


def _resolve_digest(schema_obj: Any, sha256_override: str | None) -> str:
    if sha256_override is None:
        return canonical_schema_hash(schema_obj)
    cleaned = sha256_override.strip().lower()
    if not cleaned or any(ch.isspace() for ch in cleaned):
        raise ValueError("sha256_override must be a non-empty digest string")
    return cleaned


def approve_tool(
    cwd: str | Path,
    server: str,
    tool_name: str,
    schema_obj: Any = None,
    sha256_override: str | None = None,
) -> dict[str, Any]:
    """Approve an MCP tool schema SHA-256 into docs/tdq/mcp-policy.json under sidecar lock."""
    clean_tool = (tool_name or "").strip()
    if not clean_tool:
        raise ValueError("tool_name must be a non-empty string")
    project_path = Path(cwd) / POLICY_PROJECT_REL
    digest = _resolve_digest(schema_obj, sha256_override)
    key = _tool_key(server, clean_tool)
    baseline = _load_baseline()

    with tdq_lease.acquire_sidecar_lock(project_path):
        doc = _read_existing_project_doc(project_path)
        merged, corrupt = _merge_policy(baseline, doc)
        tier = classify_tool_tier(server, clean_tool, baseline if corrupt else merged)
        entry = {
            "sha256": digest,
            "tier": tier,
            "approved_at": datetime.now(UTC).isoformat(timespec="seconds"),
        }
        doc.setdefault("schema_version", 1)
        doc["approved_tools"][key] = entry
        _atomic_write_json(project_path, doc)

    _log(f"approved tool_key={key} tier={tier} sha256={digest[:12]}")
    return {
        "ok": True,
        "tool_key": key,
        "sha256": digest,
        "tier": tier,
        "entry": entry,
        "policy_path": str(project_path),
    }


def _reset_all_entries(project_path: Path) -> list[str]:
    if not project_path.is_file():
        return []
    data, corrupt = _read_json_dict(project_path, "project")
    if corrupt or data is None:
        _atomic_write_json(project_path, {"schema_version": 1, "approved_tools": {}})
        return []
    approved = data.get("approved_tools")
    cleared = sorted(approved.keys()) if isinstance(approved, dict) else []
    data["approved_tools"] = {}
    _atomic_write_json(project_path, data)
    return cleared


def _reset_single_entry(project_path: Path, key: str) -> list[str]:
    if not project_path.is_file():
        return []
    doc = _read_existing_project_doc(project_path)
    approved = doc["approved_tools"]
    if key not in approved:
        return []
    approved.pop(key)
    _atomic_write_json(project_path, doc)
    return [key]


def reset_policy(
    cwd: str | Path,
    server: str | None = None,
    tool_name: str | None = None,
) -> dict[str, Any]:
    """Clear one approved_tools entry (if both given) or all entries under sidecar lock."""
    if (server is None) != (tool_name is None):
        raise ValueError("Provide both server and tool_name, or neither to reset all")
    project_path = Path(cwd) / POLICY_PROJECT_REL
    with tdq_lease.acquire_sidecar_lock(project_path):
        if server is None and tool_name is None:
            cleared = _reset_all_entries(project_path)
        else:
            cleared = _reset_single_entry(project_path, _tool_key(server, str(tool_name)))

    _log(f"reset cleared={len(cleared)} path={project_path}")
    return {
        "ok": True,
        "cleared": cleared,
        "count": len(cleared),
        "policy_path": str(project_path),
    }


def _resolve_cli_cwd(raw_cwd: str | None) -> Path:
    if raw_cwd is not None:
        return Path(raw_cwd)
    env_dir = os.environ.get("TDQ_PROJECT_DIR", "").strip()
    return Path(env_dir) if env_dir else Path.cwd()


def _parse_schema_json(raw: str | None) -> Any:
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except ValueError as exc:
        raise ValueError(f"Invalid --schema-json payload: {exc}") from exc


def _emit_output(payload: dict[str, Any], as_json: bool, summary: str) -> None:
    if as_json:
        print(json.dumps(payload, indent=2, ensure_ascii=True))
    else:
        print(summary)


def _cmd_approve(args: argparse.Namespace) -> int:
    schema_obj = _parse_schema_json(args.schema_json)
    result = approve_tool(
        _resolve_cli_cwd(args.cwd),
        args.server,
        args.tool,
        schema_obj=schema_obj,
        sha256_override=args.sha256,
    )
    _emit_output(
        result,
        args.json,
        f"approved {result['tool_key']} tier={result['tier']} sha256={result['sha256']}",
    )
    return 0


def _cmd_reset(args: argparse.Namespace) -> int:
    result = reset_policy(_resolve_cli_cwd(args.cwd), server=args.server, tool_name=args.tool)
    _emit_output(result, args.json, f"reset cleared={result['count']}")
    return 0


def _cmd_check(args: argparse.Namespace) -> int:
    schema_obj = _parse_schema_json(args.schema_json)
    result = evaluate_tool_call(
        _resolve_cli_cwd(args.cwd),
        args.server,
        args.tool,
        schema_obj=schema_obj,
    )
    _emit_output(
        result,
        args.json,
        f"{result['decision']} tier={result['tier']} reason={result['reason']}",
    )
    return 0 if result["decision"] == "allow" else 1


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage and evaluate TDQ MCP tool policy.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    app_cmd = subparsers.add_parser("approve", help="Approve an MCP tool schema hash.")
    app_cmd.add_argument("server", help="MCP server name, or '_' for bare tool.")
    app_cmd.add_argument("tool", help="MCP tool name.")
    app_cmd.add_argument("--cwd", default=None, help="Project working directory.")
    app_cmd.add_argument("--schema-json", default=None, help="Tool schema JSON string.")
    app_cmd.add_argument("--sha256", default=None, help="Explicit SHA-256 hex digest.")
    app_cmd.add_argument("--json", action="store_true", help="Emit JSON output.")

    rst_cmd = subparsers.add_parser("reset", help="Reset approved MCP tools.")
    rst_cmd.add_argument("--cwd", default=None, help="Project working directory.")
    rst_cmd.add_argument("--server", default=None, help="Optional MCP server name.")
    rst_cmd.add_argument("--tool", default=None, help="Optional MCP tool name.")
    rst_cmd.add_argument("--json", action="store_true", help="Emit JSON output.")

    chk_cmd = subparsers.add_parser("check", help="Evaluate an MCP tool call.")
    chk_cmd.add_argument("server", help="MCP server name, or '_' for bare tool.")
    chk_cmd.add_argument("tool", help="MCP tool name.")
    chk_cmd.add_argument("--cwd", default=None, help="Project working directory.")
    chk_cmd.add_argument("--schema-json", default=None, help="Tool schema JSON string.")
    chk_cmd.add_argument("--json", action="store_true", help="Emit JSON output.")
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for approve, reset, and check commands."""
    args = _build_parser().parse_args(argv)
    try:
        if args.command == "approve":
            return _cmd_approve(args)
        if args.command == "reset":
            return _cmd_reset(args)
        if args.command == "check":
            return _cmd_check(args)
    except ValueError as exc:
        _log(f"ERROR {exc}")
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    sys.exit(main())
