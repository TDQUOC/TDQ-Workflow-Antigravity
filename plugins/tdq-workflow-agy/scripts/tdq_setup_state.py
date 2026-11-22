#!/usr/bin/env python3
"""Persistent setup state, private secrets storage, and host session fingerprint.

Manages `${PLUGIN_DATA}/setup-state.json`, the O(1) `setup-pending.flag` marker,
private `secrets.env` credentials, and cross-platform root IDE process
fingerprinting for Windows, macOS, and Linux.

Env:
    TDQ_SETUP_STATE_DIR: Explicit override directory for state (highest priority).
    TDQ_KHONG_CHAM_MAY: Set to "1" to ignore PLUGIN_DATA in isolated tests.
    PLUGIN_DATA: Host-provided persistent plugin data directory.
    GEMINI_CONFIG_DIR: Antigravity configuration directory fallback.
    TDQ_LOG: Set to "0" to silence ISO-timestamped stderr logs.
"""

from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
from typing import Any, Optional

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)
import tdq_ten_lenh  # noqa: E402
import utf8_io  # noqa: E402,F401 — forces UTF-8 stdout/stderr on Windows

PLUGIN_ID = "tdq-workflow-agy"
STATE_FILENAME = "setup-state.json"
PENDING_FLAG_FILENAME = "setup-pending.flag"
SECRETS_FILENAME = "secrets.env"
SETUP_PENDING_TTL_SECONDS = 24 * 3600
MAX_PARENT_HOPS = 12

_HOST_SUBSTR_MARKERS = (
    "antigravity",
    "language_server",
    "cursor",
    "windsurf",
    "vscode",
)
_HOST_EXACT_NAMES = frozenset({
    "agy",
    "agy.exe",
    "code",
    "code.exe",
    "code-insiders",
    "code-insiders.exe",
    "electron",
    "electron.exe",
})
_OS_ROOT_NAMES = frozenset({
    "init",
    "systemd",
    "launchd",
    "explorer.exe",
    "wininit.exe",
    "services.exe",
    "smss.exe",
    "csrss.exe",
})
_ENV_KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_PS_LINE_RE = re.compile(
    r"^(\d+)\s+(.+?)\s+"
    r"([A-Z][a-z]{2}\s+[A-Z][a-z]{2}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}\s+\d{4})$"
)

_TH32CS_SNAPPROCESS = 0x00000002
_PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
_FILETIME_EPOCH_DIFF_TICKS = 116444736000000000


class _FILETIME(ctypes.Structure):
    """Win32 FILETIME structure (64-bit count of 100-ns intervals since 1601)."""

    _fields_ = [
        ("dwLowDateTime", wintypes.DWORD),
        ("dwHighDateTime", wintypes.DWORD),
    ]


class _PROCESSENTRY32W(ctypes.Structure):
    """Win32 PROCESSENTRY32W structure for CreateToolhelp32Snapshot."""

    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("cntUsage", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("th32DefaultHeapID", ctypes.c_size_t),
        ("th32ModuleID", wintypes.DWORD),
        ("cntThreads", wintypes.DWORD),
        ("th32ParentProcessID", wintypes.DWORD),
        ("pcPriClassBase", wintypes.LONG),
        ("dwFlags", wintypes.DWORD),
        ("szExeFile", wintypes.WCHAR * 260),
    ]


def _log(message: str) -> None:
    """Emit an ISO-8601 timestamped diagnostic line to stderr unless TDQ_LOG=0."""
    if os.environ.get("TDQ_LOG", "1") != "0":
        stamp = datetime.now().astimezone().isoformat(timespec="seconds")
        print(f"[{stamp}] tdq_setup_state: {message}", file=sys.stderr)


def _run_quiet_command(
    cmd: list[str], timeout: float = 3.0
) -> subprocess.CompletedProcess[str]:
    """Run a child command without shell and without flashing a Windows console."""
    return tdq_ten_lenh.chay_subprocess(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )


def _resolve_home_dir(home: Optional[str]) -> Path:
    """Resolve user home from explicit arg, HOME, USERPROFILE, or Path.home."""
    if home is not None and str(home).strip():
        return Path(str(home)).expanduser()
    env_home = os.environ.get("HOME", "").strip()
    if not env_home:
        env_home = os.environ.get("USERPROFILE", "").strip()
    return Path(env_home).expanduser() if env_home else Path.home()


def _from_gemini_config_dir(raw_cfg: str) -> Path:
    """Derive Antigravity plugin_data directory from GEMINI_CONFIG_DIR."""
    cfg_path = Path(raw_cfg).expanduser()
    base = cfg_path.parent if cfg_path.name == "config" else cfg_path
    return base / "antigravity" / "plugin_data" / PLUGIN_ID


def resolve_plugin_data_dir(home: Optional[str] = None) -> Path:
    """Resolve persistent plugin data dir with strict test-isolation precedence."""
    state_override = os.environ.get("TDQ_SETUP_STATE_DIR", "").strip()
    if state_override:
        return Path(state_override).expanduser()
    no_touch = os.environ.get("TDQ_KHONG_CHAM_MAY", "").strip() == "1"
    if not no_touch:
        plugin_data = os.environ.get("PLUGIN_DATA", "").strip()
        if plugin_data:
            return Path(plugin_data).expanduser()
    rel_data = Path(".gemini") / "antigravity" / "plugin_data" / PLUGIN_ID
    if home is not None and str(home).strip():
        return _resolve_home_dir(home) / rel_data
    gemini_cfg = os.environ.get("GEMINI_CONFIG_DIR", "").strip()
    if gemini_cfg:
        return _from_gemini_config_dir(gemini_cfg)
    return _resolve_home_dir(None) / rel_data


def _is_host_process(name: str) -> bool:
    """Return True if process name belongs to Antigravity or a supported IDE."""
    lower = name.strip().lower()
    if not lower:
        return False
    base = Path(lower.replace("\\", "/")).name
    if base in _HOST_EXACT_NAMES:
        return True
    return any(marker in lower for marker in _HOST_SUBSTR_MARKERS)


def _is_os_root_process(pid: int, name: str) -> bool:
    """Return True for OS init/session root processes stopped below in fallback."""
    if pid <= 1:
        return True
    base = Path(name.strip().lower().replace("\\", "/")).name
    return base in _OS_ROOT_NAMES


def _configure_kernel32() -> Any:
    """Bind Win32 Toolhelp and ProcessTime argtypes/restypes for 64-bit safety."""
    windll = getattr(ctypes, "windll", None)
    if windll is None:
        return None
    kernel32 = windll.kernel32
    kernel32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel32.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.c_void_p]
    kernel32.Process32FirstW.restype = wintypes.BOOL
    kernel32.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.c_void_p]
    kernel32.Process32NextW.restype = wintypes.BOOL
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    ft_ptr = ctypes.POINTER(_FILETIME)
    kernel32.GetProcessTimes.argtypes = [
        wintypes.HANDLE,
        ft_ptr,
        ft_ptr,
        ft_ptr,
        ft_ptr,
    ]
    kernel32.GetProcessTimes.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL
    return kernel32


def _win32_snapshot_table(kernel32: Any) -> dict[int, tuple[int, str]]:
    """Build {pid: (ppid, exe_name)} via one Win32 Toolhelp snapshot."""
    invalid_handle = ctypes.c_void_p(-1).value
    snap = kernel32.CreateToolhelp32Snapshot(_TH32CS_SNAPPROCESS, 0)
    if snap in (None, 0, invalid_handle):
        return {}
    table: dict[int, tuple[int, str]] = {}
    try:
        entry = _PROCESSENTRY32W()
        entry.dwSize = ctypes.sizeof(_PROCESSENTRY32W)
        if not kernel32.Process32FirstW(snap, ctypes.byref(entry)):
            return table
        while True:
            table[int(entry.th32ProcessID)] = (
                int(entry.th32ParentProcessID),
                str(entry.szExeFile),
            )
            if not kernel32.Process32NextW(snap, ctypes.byref(entry)):
                break
    finally:
        kernel32.CloseHandle(snap)
    return table


def _win32_process_create_time(kernel32: Any, pid: int) -> str:
    """Query process creation timestamp via OpenProcess + GetProcessTimes."""
    handle = kernel32.OpenProcess(_PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return f"pid:{pid}"
    try:
        ft_create = _FILETIME()
        ft_exit, ft_kernel, ft_user = _FILETIME(), _FILETIME(), _FILETIME()
        ok = kernel32.GetProcessTimes(
            handle,
            ctypes.byref(ft_create),
            ctypes.byref(ft_exit),
            ctypes.byref(ft_kernel),
            ctypes.byref(ft_user),
        )
        if not ok:
            return f"pid:{pid}"
        ticks = (int(ft_create.dwHighDateTime) << 32) | int(ft_create.dwLowDateTime)
        if ticks <= _FILETIME_EPOCH_DIFF_TICKS:
            return f"ft:{ticks}"
        us = (ticks - _FILETIME_EPOCH_DIFF_TICKS) // 10
        return datetime.fromtimestamp(us / 1_000_000, tz=timezone.utc).isoformat(
            timespec="microseconds"
        )
    finally:
        kernel32.CloseHandle(handle)


def _lookup_win32_ancestors(
    self_pid: int,
) -> tuple[tuple[int, str, str], list[tuple[int, str, str]]]:
    """Walk up <= 12 ancestor PIDs on Windows using a single process snapshot."""
    kernel32 = _configure_kernel32()
    if kernel32 is None:
        return (self_pid, "python.exe", f"pid:{self_pid}"), []
    table = _win32_snapshot_table(kernel32)
    self_row = table.get(self_pid)
    if self_row is None:
        return (self_pid, "python.exe", f"pid:{self_pid}"), []
    next_pid, self_name = self_row
    ancestors: list[tuple[int, str, str]] = []
    seen = {self_pid}
    for _ in range(MAX_PARENT_HOPS):
        if next_pid <= 0 or next_pid in seen:
            break
        seen.add(next_pid)
        row = table.get(next_pid)
        if row is None:
            break
        ancestors.append((next_pid, row[1], ""))
        next_pid = row[0]
    return (self_pid, self_name, ""), ancestors


def _read_proc_stat_text(pid: int) -> Optional[str]:
    """Read /proc/<pid>/stat safely on Linux."""
    try:
        return Path(f"/proc/{pid}/stat").read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def _parse_linux_proc_stat(text: str) -> Optional[tuple[int, str, str]]:
    """Parse (ppid, comm, start_ticks) handling spaces/parens inside comm."""
    lparen = text.find("(")
    rparen = text.rfind(")")
    if lparen < 0 or rparen <= lparen:
        return None
    comm = text[lparen + 1 : rparen]
    rest = text[rparen + 2 :].split()
    if len(rest) <= 19:
        return None
    try:
        ppid = int(rest[1])
    except ValueError:
        return None
    return ppid, comm, f"ticks:{rest[19]}"


def _query_macos_proc(pid: int) -> Optional[tuple[int, str, str]]:
    """Query (ppid, comm, lstart) for one PID on macOS using ps."""
    cmd = ["ps", "-o", "ppid=,comm=,lstart=", "-p", str(pid)]
    try:
        proc = _run_quiet_command(cmd, timeout=2.0)
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0 or not proc.stdout.strip():
        return None
    first_line = proc.stdout.strip().splitlines()[0].strip()
    match = _PS_LINE_RE.match(first_line)
    if not match:
        return None
    ctime = " ".join(match.group(3).split())
    return int(match.group(1)), match.group(2).strip(), ctime


def _lookup_posix_proc(pid: int, is_darwin: bool) -> Optional[tuple[int, str, str]]:
    """Dispatch single-PID lookup to macOS ps or Linux /proc/<pid>/stat."""
    if is_darwin:
        return _query_macos_proc(pid)
    raw = _read_proc_stat_text(pid)
    return _parse_linux_proc_stat(raw) if raw is not None else None


def _lookup_posix_ancestors(
    self_pid: int, is_darwin: bool
) -> tuple[tuple[int, str, str], list[tuple[int, str, str]]]:
    """Walk up <= 12 ancestor PIDs on Linux or macOS."""
    self_info = _lookup_posix_proc(self_pid, is_darwin)
    if self_info is None:
        return (self_pid, "python3", f"pid:{self_pid}"), []
    next_pid, self_name, self_ctime = self_info
    ancestors: list[tuple[int, str, str]] = []
    seen = {self_pid}
    for _ in range(MAX_PARENT_HOPS):
        if next_pid <= 0 or next_pid in seen:
            break
        seen.add(next_pid)
        info = _lookup_posix_proc(next_pid, is_darwin)
        if info is None:
            break
        ancestors.append((next_pid, info[1], info[2]))
        next_pid = info[0]
    return (self_pid, self_name, self_ctime), ancestors


def _select_root_ancestor(
    self_entry: tuple[int, str, str], ancestors: list[tuple[int, str, str]]
) -> tuple[int, str, str]:
    """Pick topmost IDE ancestor, falling back to highest non-OS-root ancestor."""
    host_matches = [item for item in ancestors if _is_host_process(item[1])]
    if host_matches:
        return host_matches[-1]
    non_roots = [
        item for item in ancestors if not _is_os_root_process(item[0], item[1])
    ]
    if non_roots:
        return non_roots[-1]
    return ancestors[0] if ancestors else self_entry


def compute_host_session_fingerprint() -> dict[str, Any]:
    """Compute deterministic SHA-256 fingerprint of the root IDE host process."""
    started = time.perf_counter()
    self_pid = os.getpid()
    plat = sys.platform
    if plat.startswith("win"):
        self_entry, ancestors = _lookup_win32_ancestors(self_pid)
        root_pid, root_name, create_time = _select_root_ancestor(self_entry, ancestors)
        if not create_time:
            kernel32 = _configure_kernel32()
            create_time = (
                _win32_process_create_time(kernel32, root_pid)
                if kernel32 is not None
                else f"pid:{root_pid}"
            )
    else:
        self_entry, ancestors = _lookup_posix_ancestors(self_pid, plat == "darwin")
        root_pid, root_name, create_time = _select_root_ancestor(self_entry, ancestors)
    digest_input = f"{plat}|{root_pid}|{create_time}"
    fingerprint = hashlib.sha256(digest_input.encode("utf-8")).hexdigest()
    elapsed_ms = round((time.perf_counter() - started) * 1000.0, 3)
    _log(f"fingerprint root_pid={root_pid} root_name={root_name} ms={elapsed_ms}")
    return {
        "root_pid": int(root_pid),
        "root_name": str(root_name),
        "create_time": str(create_time),
        "fingerprint": fingerprint,
        "elapsed_ms": elapsed_ms,
        "platform": plat,
    }


def _default_setup_state() -> dict[str, Any]:
    """Return fresh baseline setup-state schema."""
    return {
        "version": 2,
        "status": "idle",
        "pending_flag": False,
    }


def _atomic_write_text(path: Path, text: str, private: bool = False) -> None:
    """Write text atomically into path's directory using tempfile + os.replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent)
    )
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
        if private:
            _apply_private_permissions(tmp_path)
        os.replace(tmp_path, path)
    except BaseException:
        tmp_path.unlink(missing_ok=True)
        raise


def load_setup_state(data_dir: Optional[Path] = None) -> dict[str, Any]:
    """Read setup-state.json safely, failing closed on missing or corrupt JSON."""
    target_dir = Path(data_dir) if data_dir is not None else resolve_plugin_data_dir()
    state_path = target_dir / STATE_FILENAME
    if not state_path.is_file():
        _log("setup-state.json absent; returning idle default")
        return _default_setup_state()
    try:
        raw = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        _log(f"WARN corrupt setup-state.json ({type(exc).__name__}); using default")
        return _default_setup_state()
    if not isinstance(raw, dict):
        _log("WARN setup-state.json root is not a JSON object; using default")
        return _default_setup_state()
    state = dict(raw)
    state.setdefault("version", 2)
    state.setdefault("status", "idle")
    state.setdefault("pending_flag", False)
    _log(f"loaded setup-state status={state['status']}")
    return state


def save_setup_state(
    state: dict[str, Any], pending: bool, data_dir: Optional[Path] = None
) -> Path:
    """Atomically persist setup-state.json and synchronize setup-pending.flag."""
    target_dir = Path(data_dir) if data_dir is not None else resolve_plugin_data_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")
    payload = dict(state or {})
    payload.setdefault("version", 2)
    payload.setdefault("status", "idle")
    payload.setdefault("created_at", now_iso)
    payload["updated_at"] = now_iso
    payload["pending_flag"] = bool(pending)

    state_path = target_dir / STATE_FILENAME
    flag_path = target_dir / PENDING_FLAG_FILENAME
    body = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    _atomic_write_text(state_path, body)
    if pending:
        _atomic_write_text(flag_path, "")
    else:
        flag_path.unlink(missing_ok=True)
    _log(f"saved setup-state status={payload['status']} pending={bool(pending)}")
    return state_path


def _parse_iso_timestamp(raw: Any) -> Optional[datetime]:
    """Parse an ISO-8601 timestamp string into a UTC-aware datetime or None."""
    if not isinstance(raw, str) or not raw.strip():
        return None
    text = raw.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed


def _is_state_expired(state: dict[str, Any]) -> bool:
    """Return True when updated_at/created_at is older than the 24h TTL."""
    ts = _parse_iso_timestamp(state.get("updated_at") or state.get("created_at"))
    if ts is None:
        return False
    age_seconds = (datetime.now(timezone.utc) - ts).total_seconds()
    return age_seconds > SETUP_PENDING_TTL_SECONDS


def _remind_reason(is_new_turn: bool, current_fp: str, saved_fp: str) -> str:
    """Classify why restart verification is still waiting."""
    if not is_new_turn:
        return "not_new_turn"
    if not (current_fp and saved_fp):
        return "missing_fingerprint"
    return "same_host_fingerprint"


def _expire_pending_state(state: dict[str, Any], target_dir: Path) -> dict[str, Any]:
    """Mark timed-out setup state expired and remove the pending flag."""
    expired_state = dict(state)
    expired_state["status"] = "expired"
    save_setup_state(expired_state, pending=False, data_dir=target_dir)
    _log("evaluate_restart_resume action=none reason=expired_ttl")
    return {"action": "none", "reason": "expired_ttl", "state": expired_state}


def _accept_restart_verify(
    state: dict[str, Any], reason: str, current_fp: str, target_dir: Path
) -> dict[str, Any]:
    """Transition awaiting_restart state to validating_after_restart."""
    next_state = dict(state)
    next_state["status"] = "validating_after_restart"
    next_state["resume_reason"] = reason
    next_state["resumed_host_fingerprint"] = current_fp
    save_setup_state(next_state, pending=True, data_dir=target_dir)
    _log(f"evaluate_restart_resume action=run_verify reason={reason}")
    return {"action": "run_verify", "reason": reason, "state": next_state}


def _decide_awaiting_restart(
    state: dict[str, Any], is_new_turn: bool, confirm_manual: bool, target_dir: Path
) -> dict[str, Any]:
    """Decide whether an awaiting_restart session is ready to verify or must wait."""
    current_fp = str(compute_host_session_fingerprint().get("fingerprint", "") or "")
    saved_fp = str(state.get("host_fingerprint", "") or "")
    fp_changed = bool(current_fp and saved_fp and current_fp != saved_fp)
    if confirm_manual:
        return _accept_restart_verify(state, "confirm_manual", current_fp, target_dir)
    if is_new_turn and fp_changed:
        return _accept_restart_verify(state, "new_host_fingerprint", current_fp, target_dir)
    reason = _remind_reason(is_new_turn, current_fp, saved_fp)
    _log(f"evaluate_restart_resume action=remind_restart reason={reason}")
    return {"action": "remind_restart", "reason": reason, "state": state}


def evaluate_restart_resume(
    is_new_turn: bool,
    confirm_manual: bool = False,
    data_dir: Optional[Path] = None,
) -> dict[str, Any]:
    """Evaluate setup-pending state and decide none | remind_restart | run_verify."""
    target_dir = Path(data_dir) if data_dir is not None else resolve_plugin_data_dir()
    flag_path = target_dir / PENDING_FLAG_FILENAME
    state = load_setup_state(data_dir=target_dir)
    status = str(state.get("status", "idle"))
    if not flag_path.is_file() and status != "awaiting_restart":
        _log("evaluate_restart_resume action=none reason=no_pending_setup")
        return {"action": "none", "reason": "no_pending_setup", "state": state}
    if _is_state_expired(state):
        return _expire_pending_state(state, target_dir)
    if status != "awaiting_restart":
        if status in ("idle", "verified", "expired"):
            flag_path.unlink(missing_ok=True)
        _log(f"evaluate_restart_resume action=none reason=status_{status}")
        return {"action": "none", "reason": f"status_{status}", "state": state}
    return _decide_awaiting_restart(state, is_new_turn, confirm_manual, target_dir)


def _validate_secret_value(api_key: str) -> str:
    """Validate API key without echoing or leaking its characters in errors."""
    if not isinstance(api_key, str):
        raise ValueError("API key must be a non-empty string")
    if any(ch in api_key for ch in ("\r", "\n", "\x00")):
        raise ValueError("API key must not contain newline or null characters")
    cleaned = api_key.strip()
    if not cleaned:
        raise ValueError("API key must not be empty or whitespace")
    return cleaned


def _windows_principal() -> str:
    """Resolve current Windows user principal for icacls ACL hardening."""
    user = os.environ.get("USERNAME", "").strip()
    domain = os.environ.get("USERDOMAIN", "").strip()
    if domain and user:
        return f"{domain}\\{user}"
    return user


def _apply_private_permissions(path: Path) -> None:
    """Apply owner-only permissions (0o600 POSIX, fail-closed icacls DACL on Windows)."""
    if os.name != "nt":
        os.chmod(path, 0o600)
        return
    principal = _windows_principal()
    if not principal:
        raise PermissionError("Unable to resolve Windows user principal for private file ACL")
    try:
        proc = _run_quiet_command(
            ["icacls", str(path), "/inheritance:r", "/grant:r", f"{principal}:F"],
            timeout=5.0,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise PermissionError(f"icacls ACL hardening failed: {type(exc).__name__}") from exc
    if proc is None or proc.returncode != 0:
        rc = getattr(proc, "returncode", "none")
        raise PermissionError(f"icacls ACL hardening returned non-zero exit ({rc})")


def _parse_secret_line(raw_line: str) -> Optional[tuple[str, str]]:
    """Parse one KEY=VALUE line from secrets.env, returning None to skip."""
    stripped = raw_line.strip()
    if not stripped or stripped.startswith("#"):
        return None
    if stripped.startswith("export "):
        stripped = stripped[7:].lstrip()
    if "=" not in stripped:
        return None
    key, raw_val = stripped.split("=", 1)
    key = key.strip()
    if not _ENV_KEY_RE.match(key):
        return None
    val = raw_val.strip()
    if len(val) >= 2 and val[0] == val[-1] and val[0] in ('"', "'"):
        val = val[1:-1]
    return key, val


def load_secrets_env(data_dir: Optional[Path] = None) -> dict[str, str]:
    """Parse KEY=VALUE pairs from secrets.env while ignoring comments and quotes."""
    target_dir = Path(data_dir) if data_dir is not None else resolve_plugin_data_dir()
    secrets_path = target_dir / SECRETS_FILENAME
    if not secrets_path.is_file():
        _log("secrets.env absent; returning 0 secret key(s)")
        return {}
    try:
        text = secrets_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        _log(f"WARN unreadable secrets.env ({type(exc).__name__})")
        return {}
    loaded: dict[str, str] = {}
    for line in text.splitlines():
        parsed = _parse_secret_line(line)
        if parsed is not None:
            loaded[parsed[0]] = parsed[1]
    _log(f"loaded {len(loaded)} secret key(s) from secrets.env")
    return loaded


def save_tavily_secret(api_key: str, data_dir: Optional[Path] = None) -> Path:
    """Validate and atomically store TAVILY_API_KEY in private secrets.env."""
    cleaned = _validate_secret_value(api_key)
    target_dir = Path(data_dir) if data_dir is not None else resolve_plugin_data_dir()
    secrets_path = target_dir / SECRETS_FILENAME
    existing = load_secrets_env(data_dir=target_dir)
    existing["TAVILY_API_KEY"] = cleaned
    lines: list[str] = []
    for key, val in existing.items():
        if not _ENV_KEY_RE.match(key):
            continue
        if any(ch in val for ch in ("\r", "\n", "\x00")):
            continue
        lines.append(f"{key}={val}\n")
    _atomic_write_text(secrets_path, "".join(lines), private=True)
    _log("saved TAVILY_API_KEY to secrets.env (value redacted)")
    return secrets_path


def _build_parser() -> argparse.ArgumentParser:
    """Build CLI parser supporting --state-dir and --khong-log."""
    parser = argparse.ArgumentParser(description="Inspect and manage TDQ setup state.")
    parser.add_argument("--state-dir", default=None, help="Override state dir.")
    parser.add_argument("--khong-log", action="store_true", help="Silence stderr log.")
    parser.add_argument("--json", action="store_true", help="Emit JSON output.")
    sub = parser.add_subparsers(dest="command")

    for name in ("status", "fingerprint"):
        cmd = sub.add_parser(name, help=f"Show setup {name}.")
        cmd.add_argument("--state-dir", default=None, help="Override state dir.")
        cmd.add_argument("--json", action="store_true", help="Emit JSON output.")

    res = sub.add_parser("resume", help="Evaluate restart resume state.")
    res.add_argument("--state-dir", default=None, help="Override state dir.")
    res.add_argument("--new-turn", action="store_true", help="Mark new prompt turn.")
    res.add_argument("--confirm-manual", action="store_true", help="Confirm restart.")
    res.add_argument("--json", action="store_true", help="Emit JSON output.")
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    """CLI entrypoint emitting JSON on stdout and ISO diagnostics on stderr."""
    args = _build_parser().parse_args(argv)
    if args.khong_log:
        os.environ["TDQ_LOG"] = "0"
    state_dir = Path(args.state_dir).expanduser() if args.state_dir else None
    command = args.command or "status"
    if command == "fingerprint":
        payload: dict[str, Any] = compute_host_session_fingerprint()
    elif command == "resume":
        payload = evaluate_restart_resume(
            is_new_turn=bool(args.new_turn),
            confirm_manual=bool(args.confirm_manual),
            data_dir=state_dir,
        )
    else:
        resolved = state_dir or resolve_plugin_data_dir()
        payload = {
            "data_dir": str(resolved),
            "pending_flag": (resolved / PENDING_FLAG_FILENAME).is_file(),
            "state": load_setup_state(data_dir=resolved),
        }
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
