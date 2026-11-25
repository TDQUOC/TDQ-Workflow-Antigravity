#!/usr/bin/env python3
"""Cross-platform sidecar file lock and TTL lease manager (stdlib only).

Matches the Rust tdq-dispatch sidecar lock protocol (`<target>.lock` anchor files
kept on disk after unlock to avoid Windows create/unlink races).

Env: TDQ_LOG=0 mutes ISO-timestamped stderr diagnostic logs.
"""
from __future__ import annotations

import argparse
import contextlib
import errno
import json
import math
import os
import re
import sys
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import utf8_io  # noqa: F401

_SAFE_ID_CHARS_RE = re.compile(r"[^A-Za-z0-9._-]+")
_MULTI_UNDERSCORE_RE = re.compile(r"_+")
_CONTENTION_ERRNOS = frozenset(
    err
    for err in (
        getattr(errno, "EACCES", None),
        getattr(errno, "EAGAIN", None),
        getattr(errno, "EWOULDBLOCK", None),
        getattr(errno, "EDEADLK", None),
    )
    if err is not None
)


def _log_enabled() -> bool:
    """Return True unless TDQ_LOG=0 disables stderr logging."""
    return os.environ.get("TDQ_LOG", "1") != "0"


def _log(message: str) -> None:
    """Emit one ISO-8601 timezone-aware diagnostic line to stderr if enabled."""
    if _log_enabled():
        stamp = datetime.now(UTC).isoformat(timespec="seconds")
        print(f"[{stamp}] tdq_lease: {message}", file=sys.stderr)


def _iso_utc(epoch_sec: float) -> str:
    return datetime.fromtimestamp(epoch_sec, tz=UTC).isoformat()


def sidecar_lock_path(target_path: str | os.PathLike[str]) -> Path:
    """Return canonical `<target_path>.lock` path without replacing extensions."""
    return Path(f"{os.fspath(target_path)}.lock")


def _close_quietly(fd: int) -> None:
    try:
        os.close(fd)
    except OSError:
        pass


def _flock_fd(fd: int, unlock: bool) -> None:
    """Lock or unlock a file descriptor via msvcrt on Windows or flock on POSIX."""
    if os.name == "nt":
        import msvcrt

        os.lseek(fd, 0, os.SEEK_SET)
        msvcrt.locking(fd, msvcrt.LK_UNLCK if unlock else msvcrt.LK_NBLCK, 1)
    else:
        import fcntl

        fcntl.flock(fd, fcntl.LOCK_UN if unlock else fcntl.LOCK_EX | fcntl.LOCK_NB)


def _lock_fd(fd: int) -> None:
    _flock_fd(fd, False)


def _unlock_fd(fd: int) -> None:
    _flock_fd(fd, True)


def _is_lock_contention(exc: OSError) -> bool:
    return isinstance(exc, (BlockingIOError, PermissionError)) or (
        exc.errno in _CONTENTION_ERRNOS
    )


def _try_open_and_lock(lock_path: Path) -> int | None:
    fd: int | None = None
    try:
        fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o666)
        _lock_fd(fd)
        return fd
    except OSError as exc:
        if fd is not None:
            _close_quietly(fd)
        if _is_lock_contention(exc):
            return None
        raise


def _acquire_lock_with_backoff(
    lock_path: Path, deadline: float, poll_interval: float, timeout_sec: float
) -> int:
    attempt = 0
    cap = max(0.001, poll_interval)
    while True:
        fd = _try_open_and_lock(lock_path)
        if fd is not None:
            return fd
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError(
                f"Timed out acquiring sidecar lock {lock_path} after {timeout_sec}s"
            )
        step = min(cap, 0.002 * (2 ** min(attempt, 5)), remaining)
        if step > 0:
            time.sleep(step)
        attempt += 1


@contextlib.contextmanager
def acquire_sidecar_lock(
    target_path: str | os.PathLike[str],
    timeout_sec: float = 5.0,
    poll_interval: float = 0.02,
):
    """Acquire an exclusive OS byte lock on `<target_path>.lock` without unlinking."""
    lock_path = sidecar_lock_path(target_path)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + max(0.0, float(timeout_sec))
    fd = _acquire_lock_with_backoff(
        lock_path, deadline, float(poll_interval), timeout_sec
    )
    try:
        yield lock_path
    finally:
        try:
            _unlock_fd(fd)
        finally:
            _close_quietly(fd)


def _sanitize_lease_id(lease_id: str) -> str:
    if not isinstance(lease_id, str) or not lease_id.strip():
        raise ValueError("lease_id must be a non-empty string")
    cleaned = _SAFE_ID_CHARS_RE.sub("_", lease_id.strip())
    while ".." in cleaned:
        cleaned = cleaned.replace("..", "_")
    cleaned = _MULTI_UNDERSCORE_RE.sub("_", cleaned).strip("._")
    if not cleaned or not any(ch.isalnum() for ch in cleaned):
        raise ValueError(f"Invalid lease_id: {lease_id!r}")
    return cleaned[:128]


def _leases_dir(cwd: str | os.PathLike[str]) -> Path:
    return Path(cwd) / "docs" / "tdq" / "leases"


def _lease_path(cwd: str | os.PathLike[str], lease_id: str) -> Path:
    leases_root = _leases_dir(cwd)
    safe_id = _sanitize_lease_id(lease_id)
    abs_root = Path(os.path.abspath(os.fspath(leases_root)))
    candidate = Path(os.path.abspath(os.fspath(abs_root / f"{safe_id}.json")))
    if candidate.parent != abs_root:
        raise ValueError(f"Lease path escaped leases directory: {lease_id!r}")
    target = leases_root / f"{safe_id}.json"
    if target.is_symlink():
        raise ValueError(f"Lease path cannot be a symlink: {lease_id!r}")
    return target


def _validate_owner(owner: str) -> str:
    if not isinstance(owner, str) or not owner.strip():
        raise ValueError("owner must be a non-empty string")
    return owner


def _validate_ttl(ttl_sec: float) -> float:
    if isinstance(ttl_sec, bool) or not isinstance(ttl_sec, (int, float)):
        raise TypeError("ttl_sec must be a finite number")
    val = float(ttl_sec)
    if not math.isfinite(val):
        raise ValueError("ttl_sec must be a finite number")
    return val


def _parse_expires_at(raw: Any, default: float) -> float:
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        return default
    val = float(raw)
    return val if math.isfinite(val) else default


def _build_lease_payload(
    lease_id: str,
    owner: str,
    acquired_at: float,
    ttl_val: float,
    ttl_raw: float,
) -> dict[str, Any]:
    expires_at = acquired_at + ttl_val
    return {
        "lease_id": lease_id,
        "owner": owner,
        "acquired_at": acquired_at,
        "expires_at": expires_at,
        "expires_at_iso": _iso_utc(expires_at),
        "ttl_sec": ttl_raw,
    }


def _write_all(fd: int, raw: bytes) -> None:
    view = memoryview(raw)
    written = 0
    while written < len(raw):
        written += os.write(fd, view[written:])
    os.fsync(fd)


def _write_exclusive(lease_path: Path, raw: bytes) -> None:
    fd = os.open(lease_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o666)
    try:
        _write_all(fd, raw)
    except Exception:
        _close_quietly(fd)
        lease_path.unlink(missing_ok=True)
        raise
    _close_quietly(fd)


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


def _atomic_replace_json(target: Path, data: dict[str, Any]) -> None:
    raw = (json.dumps(data, indent=2) + "\n").encode("utf-8")
    tmp_name = f".tmp.{os.getpid()}.{threading.get_ident()}.{target.name}"
    tmp_path = target.with_name(tmp_name)
    fd = os.open(tmp_path, os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o666)
    try:
        _write_all(fd, raw)
    finally:
        _close_quietly(fd)
    _replace_with_retry(tmp_path, target)


def _read_json_dict(path: Path) -> dict[str, Any] | None:
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return parsed if isinstance(parsed, dict) else None


def acquire_lease(
    cwd: str | os.PathLike[str],
    lease_id: str,
    owner: str,
    ttl_sec: float = 300,
) -> dict[str, Any]:
    """Create a lease JSON atomically via O_CREAT | O_EXCL | O_WRONLY."""
    _validate_owner(owner)
    ttl_val = _validate_ttl(ttl_sec)
    lease_path = _lease_path(cwd, lease_id)
    lease_path.parent.mkdir(parents=True, exist_ok=True)
    with acquire_sidecar_lock(lease_path):
        now_float = time.time()
        payload = _build_lease_payload(lease_id, owner, now_float, ttl_val, ttl_sec)
        raw = (json.dumps(payload, indent=2) + "\n").encode("utf-8")
        _write_exclusive(lease_path, raw)
    _log(f"acquired lease_id={lease_id} owner={owner} ttl_sec={ttl_sec}")
    return payload


def renew_lease(
    cwd: str | os.PathLike[str],
    lease_id: str,
    owner: str,
    ttl_sec: float = 300,
) -> dict[str, Any]:
    """Renew an active lease held by `owner` under the sidecar lock."""
    _validate_owner(owner)
    ttl_val = _validate_ttl(ttl_sec)
    lease_path = _lease_path(cwd, lease_id)
    with acquire_sidecar_lock(lease_path):
        if not lease_path.exists():
            raise FileNotFoundError(f"Lease not found: {lease_id!r}")
        data = _read_json_dict(lease_path)
        if data is None:
            raise ValueError(f"Corrupt lease file for {lease_id!r}")
        if data.get("owner") != owner:
            raise PermissionError(f"Lease {lease_id!r} is owned by another owner")
        now_float = time.time()
        expires_at = _parse_expires_at(data.get("expires_at"), default=-1.0)
        if expires_at < now_float:
            raise TimeoutError(f"Lease {lease_id!r} has already expired")
        new_exp = now_float + ttl_val
        data["expires_at"] = new_exp
        data["expires_at_iso"] = _iso_utc(new_exp)
        data["ttl_sec"] = ttl_sec
        _atomic_replace_json(lease_path, data)
    _log(f"renewed lease_id={lease_id} owner={owner} ttl_sec={ttl_sec}")
    return data


def release_or_reclaim(
    cwd: str | os.PathLike[str],
    lease_id: str,
    owner: str | None = None,
    force_expired: bool = False,
) -> bool:
    """Release a lease owned by `owner` or reclaim an expired lease."""
    lease_path = _lease_path(cwd, lease_id)
    removed = False
    action = ""
    with acquire_sidecar_lock(lease_path):
        if not lease_path.exists():
            return False
        data = _read_json_dict(lease_path)
        if data is None:
            return False
        owner_ok = owner is not None and data.get("owner") == owner
        expires_at = _parse_expires_at(data.get("expires_at"), default=float("inf"))
        expired_ok = bool(force_expired) and expires_at < time.time()
        if owner_ok or expired_ok:
            lease_path.unlink(missing_ok=True)
            removed = True
            action = "released" if owner_ok else "reclaimed"
    if removed:
        _log(f"{action} lease_id={lease_id}")
    return removed


def _list_lease_files(cwd: str | os.PathLike[str]) -> list[Path]:
    leases_root = _leases_dir(cwd)
    if not leases_root.is_dir():
        return []
    return sorted(
        p
        for p in leases_root.glob("*.json")
        if not p.name.startswith(".tmp.") and p.is_file()
    )


def _inspect_lease(path: Path, now_float: float) -> dict[str, Any]:
    data = _read_json_dict(path)
    if data is None:
        return {"lease_id": path.stem, "corrupt": True, "expired": False}
    expires_at = _parse_expires_at(data.get("expires_at"), default=float("inf"))
    return {**data, "expired": expires_at < now_float}


def _cmd_status(cwd: str, lease_id: str | None) -> int:
    now_float = time.time()
    if lease_id is not None:
        target = _lease_path(cwd, lease_id)
        files = [target] if target.is_file() else []
    else:
        files = _list_lease_files(cwd)
    entries = [_inspect_lease(path, now_float) for path in files]
    print(json.dumps({"leases": entries, "count": len(entries)}, indent=2))
    _log(f"status checked cwd={cwd} count={len(entries)}")
    return 0


def _cmd_reclaim(cwd: str) -> int:
    reclaimed: list[str] = []
    for path in _list_lease_files(cwd):
        data = _read_json_dict(path)
        if data is None:
            continue
        raw_id = data.get("lease_id")
        target_id = raw_id if isinstance(raw_id, str) and raw_id.strip() else path.stem
        if release_or_reclaim(cwd, target_id, force_expired=True):
            reclaimed.append(target_id)
    print(json.dumps({"reclaimed": reclaimed, "count": len(reclaimed)}, indent=2))
    _log(f"reclaim completed cwd={cwd} reclaimed={len(reclaimed)}")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage TDQ sidecar locks and leases.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    status_parser = subparsers.add_parser(
        "status", help="Inspect active and expired leases."
    )
    status_parser.add_argument("--cwd", default=".", help="Project working directory.")
    status_parser.add_argument("--lease-id", default=None, help="Optional lease ID.")

    reclaim_parser = subparsers.add_parser(
        "reclaim", help="Reclaim expired leases in docs/tdq/leases."
    )
    reclaim_parser.add_argument("--cwd", default=".", help="Project working directory.")
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for lease status and expired lease reclamation."""
    args = _build_parser().parse_args(argv)
    if args.command == "status":
        return _cmd_status(args.cwd, args.lease_id)
    if args.command == "reclaim":
        return _cmd_reclaim(args.cwd)
    return 2


if __name__ == "__main__":
    sys.exit(main())
