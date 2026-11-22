#!/usr/bin/env python3
"""User-level Caveman opt-in config (~/.tdq/caveman.json) and MCP config wrapping."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)
import utf8_io  # noqa: F401 — forces UTF-8 stdio on Windows

CAVEMAN_MCP_SERVERS: tuple[str, ...] = ("lsp", "chrome-devtools", "tavily-primary")
PROXY_SCRIPT_NAME = "tdq_mcp_shrink.py"
LAUNCHER_SCRIPT_NAME = "tdq_mcp_launcher.mjs"
PROXY_ENV_VARS: dict[str, str] = {
    "PYTHONUTF8": "1",
    "PYTHONUNBUFFERED": "1",
}


def _log(message: str) -> None:
    """Emit an ISO-timestamped diagnostic line to stderr unless TDQ_LOG=0."""
    if os.environ.get("TDQ_LOG", "1") != "0":
        stamp = datetime.now().isoformat(timespec="seconds")
        print(f"[{stamp}] caveman_config: {message}", file=sys.stderr)


def _now_iso() -> str:
    """Return current local ISO-8601 timestamp with second precision."""
    return datetime.now().isoformat(timespec="seconds")


def _default_config() -> dict[str, Any]:
    """Return a fresh default Caveman user configuration dictionary."""
    return {
        "enabled": False,
        "prompt_muted": False,
        "wrapped_servers": [],
        "updated_at": "",
    }


def _atomic_write_text(path: Path, content: str) -> None:
    """Atomically write UTF-8 text to `path` via temp file + os.replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        dir=str(path.parent),
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(content)
        os.replace(tmp_name, path)
    except Exception:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)
        raise


def _atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    """Serialize `data` as formatted UTF-8 JSON and write atomically."""
    payload = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    _atomic_write_text(path, payload)


def config_path(home: str | None = None) -> Path:
    """Resolve user-level Caveman config path (~/.tdq/caveman.json)."""
    if home is not None:
        return Path(home).expanduser() / ".tdq" / "caveman.json"
    override = os.environ.get("TDQ_CAVEMAN_CONFIG", "").strip()
    if override:
        return Path(override).expanduser()
    env_home = os.environ.get("HOME") or os.environ.get("USERPROFILE")
    base = Path(env_home).expanduser() if env_home else Path.home()
    return base / ".tdq" / "caveman.json"


def load_config(home: str | None = None) -> dict[str, Any]:
    """Read Caveman config safely, returning opt-out defaults when missing or invalid."""
    cfg = _default_config()
    target = config_path(home=home)
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return cfg
    if not isinstance(raw, dict):
        return cfg
    servers = raw.get("wrapped_servers")
    cfg.update({
        "enabled": bool(raw.get("enabled", False)),
        "prompt_muted": bool(raw.get("prompt_muted", False)),
        "wrapped_servers": (
            [str(item) for item in servers] if isinstance(servers, list) else []
        ),
        "updated_at": str(raw.get("updated_at") or ""),
    })
    return cfg


def is_prompt_muted(home: str | None = None) -> bool:
    """Return True when the user muted SessionStart Caveman setup reminders."""
    return bool(load_config(home=home).get("prompt_muted", False))


def set_prompt_muted(muted: bool, home: str | None = None) -> Path:
    """Persist the user's SessionStart Caveman mute preference without enabling."""
    target = config_path(home=home)
    cfg = load_config(home=home)
    cfg["prompt_muted"] = bool(muted)
    cfg["updated_at"] = _now_iso()
    _atomic_write_json(target, cfg)
    _log(f"set_prompt_muted: {bool(muted)} -> {target}")
    return target


def enable_caveman(
    approve: bool = False,
    wrapped_servers: list[str] | None = None,
    home: str | None = None,
) -> dict[str, Any]:
    """Enable Caveman opt-in config only when explicit approval is provided."""
    target = config_path(home=home)
    cfg = load_config(home=home)
    if not approve:
        _log("enable_caveman: refused (approval_required)")
        return {
            **cfg,
            "ok": False,
            "reason": "approval_required",
            "config_path": str(target),
        }
    servers = (
        [str(item) for item in wrapped_servers]
        if wrapped_servers is not None
        else list(cfg.get("wrapped_servers") or [])
    )
    cfg["enabled"] = True
    cfg["wrapped_servers"] = servers
    cfg["updated_at"] = _now_iso()
    _atomic_write_json(target, cfg)
    _log(f"enable_caveman: enabled=True servers={servers} -> {target}")
    return {**cfg, "ok": True, "reason": "ok", "config_path": str(target)}


def disable_caveman(home: str | None = None) -> dict[str, Any]:
    """Disable Caveman opt-in config while preserving mute preference."""
    target = config_path(home=home)
    cfg = load_config(home=home)
    cfg["enabled"] = False
    cfg["wrapped_servers"] = []
    cfg["updated_at"] = _now_iso()
    _atomic_write_json(target, cfg)
    _log(f"disable_caveman: enabled=False -> {target}")
    return {**cfg, "ok": True, "reason": "disabled", "config_path": str(target)}


def _script_basename(token: str) -> str:
    """Return cross-platform filename component from a slash or backslash path."""
    return str(token).replace("\\", "/").rsplit("/", 1)[-1]


def _parse_wrapped_entry(entry: dict[str, Any]) -> tuple[str, str, list[str]] | None:
    """Return `(mode, orig_cmd, orig_args)` for node or python wrapped entries."""
    args = entry.get("args")
    if not isinstance(args, list) or "--" not in args:
        return None
    dash_idx = args.index("--")
    prefix = [str(item) for item in args[:dash_idx]]
    tail = [str(item) for item in args[dash_idx + 1 :]]
    if not tail:
        return None
    if any(_script_basename(item) == PROXY_SCRIPT_NAME for item in prefix):
        return "python_proxy", tail[0], tail[1:]
    if (
        len(prefix) >= 2
        and _script_basename(prefix[0]) == LAUNCHER_SCRIPT_NAME
        and "caveman" in prefix[1:]
    ):
        return "node_launcher", tail[0], tail[1:]
    return None


def _split_wrapped_args(entry: dict[str, Any]) -> tuple[str, list[str]] | None:
    """Extract `(orig_cmd, orig_args)` if an MCP server entry is Caveman-wrapped."""
    parsed = _parse_wrapped_entry(entry)
    if parsed is None:
        return None
    return parsed[1], parsed[2]


def _is_agy_node_launcher(orig_args: list[str]) -> bool:
    """Return True when entry already delegates through tdq_mcp_launcher.mjs."""
    return bool(orig_args) and _script_basename(orig_args[0]) == LAUNCHER_SCRIPT_NAME


def _wrap_server_entry(entry: dict[str, Any], proxy_script: Path) -> bool:
    """Wrap one MCP server entry in-place; return False if skipped/already wrapped."""
    if _split_wrapped_args(entry) is not None:
        return False
    orig_cmd = entry.get("command")
    if not isinstance(orig_cmd, str) or not orig_cmd:
        return False
    raw_args = entry.get("args")
    orig_args = [str(item) for item in raw_args] if isinstance(raw_args, list) else []
    if _is_agy_node_launcher(orig_args):
        entry["command"] = orig_cmd
        entry["args"] = [orig_args[0], "caveman", "--", orig_cmd, *orig_args]
    else:
        entry["command"] = sys.executable
        entry["args"] = ["-u", str(proxy_script), "--", orig_cmd, *orig_args]
    raw_env = entry.get("env")
    env = dict(raw_env) if isinstance(raw_env, dict) else {}
    env.update(PROXY_ENV_VARS)
    entry["env"] = env
    return True


def _unwrap_server_entry(entry: dict[str, Any]) -> bool:
    """Restore original command/args on one wrapped MCP entry; return False if raw."""
    parsed = _split_wrapped_args(entry)
    if parsed is None:
        return False
    orig_cmd, orig_args = parsed
    entry["command"] = orig_cmd
    entry["args"] = orig_args
    raw_env = entry.get("env")
    if isinstance(raw_env, dict):
        for key in PROXY_ENV_VARS:
            raw_env.pop(key, None)
        if not raw_env:
            entry.pop("env", None)
    return True


def wrap_mcp_config(mcp_file: Path, proxy_script: Path) -> list[str]:
    """Idempotently wrap target MCP servers through `tdq_mcp_shrink.py` with backup."""
    mcp_path = Path(mcp_file)
    proxy_path = Path(proxy_script)
    raw_text = mcp_path.read_text(encoding="utf-8")
    data = json.loads(raw_text)
    if not isinstance(data, dict):
        raise TypeError(f"Expected JSON object in {mcp_path}")
    servers = data.get("mcpServers")
    if not isinstance(servers, dict):
        return []
    wrapped: list[str] = []
    for name in CAVEMAN_MCP_SERVERS:
        entry = servers.get(name)
        if isinstance(entry, dict) and _wrap_server_entry(entry, proxy_path):
            wrapped.append(name)
    if not wrapped:
        _log(f"wrap_mcp_config: no changes needed for {mcp_path}")
        return []
    bak_path = mcp_path.with_name(f"{mcp_path.name}.bak")
    if not bak_path.exists():
        _atomic_write_text(bak_path, raw_text)
    _atomic_write_json(mcp_path, data)
    _log(f"wrap_mcp_config: wrapped {wrapped} in {mcp_path}")
    return wrapped


def unwrap_mcp_config(mcp_file: Path) -> list[str]:
    """Restore original command/args on all Caveman-wrapped MCP servers."""
    mcp_path = Path(mcp_file)
    if not mcp_path.is_file():
        return []
    try:
        data = json.loads(mcp_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    if not isinstance(data, dict):
        return []
    servers = data.get("mcpServers")
    if not isinstance(servers, dict):
        return []
    unwrapped: list[str] = []
    for name in CAVEMAN_MCP_SERVERS:
        entry = servers.get(name)
        if isinstance(entry, dict) and _unwrap_server_entry(entry):
            unwrapped.append(name)
    if not unwrapped:
        _log(f"unwrap_mcp_config: no wrapped servers in {mcp_path}")
        return []
    _atomic_write_json(mcp_path, data)
    _log(f"unwrap_mcp_config: unwrapped {unwrapped} in {mcp_path}")
    return unwrapped


def _inspect_mcp_file_details(
    mcp_file: Path,
) -> tuple[list[str], list[str], str]:
    """Return `(present_servers, wrapped_servers, wrapper_mode)` for MCP config."""
    if not mcp_file.is_file():
        return [], [], "none"
    try:
        data = json.loads(mcp_file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return [], [], "none"
    servers = data.get("mcpServers") if isinstance(data, dict) else None
    if not isinstance(servers, dict):
        return [], [], "none"
    present: list[str] = []
    wrapped: list[str] = []
    modes: set[str] = set()
    for name in CAVEMAN_MCP_SERVERS:
        entry = servers.get(name)
        if not isinstance(entry, dict):
            continue
        present.append(name)
        parsed = _parse_wrapped_entry(entry)
        if parsed is not None:
            wrapped.append(name)
            modes.add(parsed[0])
    mode = next(iter(modes)) if len(modes) == 1 else ("mixed" if modes else "none")
    return present, wrapped, mode


def _inspect_mcp_file(mcp_file: Path) -> tuple[list[str], list[str]]:
    """Return `(present_servers, wrapped_servers)` for known Caveman MCP targets."""
    present, wrapped, _ = _inspect_mcp_file_details(mcp_file)
    return present, wrapped


def probe_caveman(
    plugin_root: Path | None = None,
    home: str | None = None,
) -> dict[str, Any]:
    """Inspect user Caveman config, proxy script, and plugin mcp_config.json."""
    root = (
        Path(plugin_root)
        if plugin_root is not None
        else Path(__file__).resolve().parent.parent
    )
    cfg = load_config(home=home)
    cfg_file = config_path(home=home)
    proxy_path = root / "scripts" / PROXY_SCRIPT_NAME
    launcher_path = root / "scripts" / LAUNCHER_SCRIPT_NAME
    mcp_file = root / "mcp_config.json"
    present, mcp_wrapped, wrapper_mode = _inspect_mcp_file_details(mcp_file)
    return {
        "enabled": bool(cfg["enabled"]),
        "prompt_muted": bool(cfg["prompt_muted"]),
        "wrapped_servers": list(cfg["wrapped_servers"]),
        "updated_at": str(cfg["updated_at"]),
        "config_path": str(cfg_file),
        "config_exists": cfg_file.is_file(),
        "proxy_script": str(proxy_path),
        "proxy_exists": proxy_path.is_file(),
        "launcher_script": str(launcher_path),
        "launcher_exists": launcher_path.is_file(),
        "mcp_config_path": str(mcp_file),
        "mcp_config_exists": mcp_file.is_file(),
        "mcp_present_servers": present,
        "mcp_wrapped_servers": mcp_wrapped,
        "mcp_wrapper_mode": wrapper_mode,
        "active": bool(cfg["enabled"]) and bool(mcp_wrapped),
    }


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for probing user-level Caveman configuration."""
    parser = argparse.ArgumentParser(
        description="Inspect user-level Caveman configuration and MCP wrapper state."
    )
    parser.add_argument("--plugin-root", type=Path, default=None)
    parser.add_argument("--home", default=None)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)
    status = probe_caveman(plugin_root=args.plugin_root, home=args.home)
    _log(
        f"probe: enabled={status['enabled']} "
        f"wrapped={len(status['mcp_wrapped_servers'])}"
    )
    if not args.quiet:
        print(json.dumps(status, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
