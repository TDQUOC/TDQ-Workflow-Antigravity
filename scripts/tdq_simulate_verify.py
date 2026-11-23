#!/usr/bin/env python3
"""Six-layer isolated post-restart verification suite for Google Antigravity setup.

Runs inside a temporary `tdq_sim_*` sandbox without mutating `~/.gemini/config/`,
real `docs/tdq/state.json`, or host user directories. Always cleans up temporary
directories and child process trees in `finally`.

Layers:
  T1: Plugin manifest/structure validation (`agy plugin validate`) + `tdq_setup_probe.mjs`
  T2: All 6 lifecycle hooks (`SessionStart`..`Stop`) with `< 50ms` Rust hot-path check
  T3: Interactive JSON-RPC pipe handshakes (`lsp` + `caveman` + optional `tavily-primary`/`chrome-devtools`)
  T4: Live `agent-lsp` semantic check (`start_lsp` + `find_symbol`) + `graphify` on sample repo
  T5: Collision-free `rtk` + `rg` smoke check + sandboxed `archify_delivery` HTML render
  T6: Integrity of 8 `agents/*.md` manifests + subagent lifecycle hook simulation

Env:
  TDQ_LOG: Set to "0" to silence ISO-timestamped stderr and log-file output.
  TAVILY_API_KEY: Optional Tavily key (read-only; never echoed or logged).
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import queue
import re
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import archify_delivery
import rtk_integration
import tdq_devtool_mcp
import tdq_lsp
import tdq_setup_state
import tdq_ten_lenh
import utf8_io  # noqa: F401 — forces UTF-8 stdio on Windows

SANDBOX_PREFIX = "tdq_sim_"
HOT_HOOK_BUDGET_MS = 50.0
DEFAULT_TIMEOUT_SEC = 90.0
LIFECYCLE_EVENTS = (
    "SessionStart",
    "PreInvocation",
    "PreToolUse",
    "PostToolUse",
    "PostInvocation",
    "Stop",
)
HOT_EVENTS = frozenset({"PreToolUse", "PostToolUse", "PostInvocation", "Stop"})
EXPECTED_AGENTS = (
    "tdq-build-resolver.md",
    "tdq-debugger.md",
    "tdq-explorer.md",
    "tdq-implementer.md",
    "tdq-qc-tester.md",
    "tdq-refactor-cleaner.md",
    "tdq-reviewer.md",
    "tdq-security-reviewer.md",
)
_PERSONAL_PATH_RE = re.compile(r"(?:/Users/|C:\\\\?Users\\\\?)", re.IGNORECASE)
_FRONTMATTER_RE = re.compile(r"^---\r?\n(.*?)\r?\n---\r?\n(.*)$", re.DOTALL)
_RECOVERABLE_ERRORS = (
    OSError,
    ValueError,
    TypeError,
    KeyError,
    RuntimeError,
    subprocess.SubprocessError,
    TimeoutError,
)


def _log_enabled() -> bool:
    """Return True unless stderr/file logging is muted via TDQ_LOG=0."""
    return os.environ.get("TDQ_LOG", "1") != "0"


def _log(message: str, log_file: Path | None = None) -> None:
    """Write an ISO-timestamped line to stderr and optional log file."""
    if not _log_enabled():
        return
    stamp = datetime.now().astimezone().isoformat(timespec="seconds")
    line = f"[{stamp}] tdq_simulate_verify: {message}"
    print(line, file=sys.stderr)
    if log_file is None:
        return
    try:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        with open(log_file, "a", encoding="utf-8", newline="\n") as fh:
            fh.write(line + "\n")
    except OSError:
        pass


def _is_temp_path(path: Path) -> bool:
    """Return True when `path` is inside the OS temporary directory."""
    try:
        resolved = path.resolve()
        tmp_root = Path(tempfile.gettempdir()).resolve()
        return resolved == tmp_root or tmp_root in resolved.parents
    except OSError:
        return False


def _resolve_log_file(data_dir: Path, explicit_data_dir: bool) -> Path | None:
    """Return log file path when disk logging is permitted."""
    dry_mode = os.environ.get("TDQ_KHONG_CHAM_MAY", "").strip() == "1"
    has_override = bool(os.environ.get("TDQ_SETUP_STATE_DIR", "").strip())
    if explicit_data_dir or not dry_mode or has_override or _is_temp_path(data_dir):
        return data_dir / "logs" / "tdq-simulate-verify.log"
    return None


def _resolve_plugin_root(plugin_root: Path | None) -> Path:
    """Resolve active plugin root or repository root."""
    if plugin_root is not None:
        return Path(plugin_root).expanduser().resolve()
    base = Path(__file__).resolve().parent.parent
    bundled = base / "plugins" / "tdq-workflow-agy"
    if not (base / "plugin.json").is_file() and (bundled / "plugin.json").is_file():
        return bundled.resolve()
    return base.resolve()


def _resolve_real_gemini_cfg() -> Path:
    """Resolve active ~/.gemini/config directory for snapshot invariance."""
    cfg_env = os.environ.get("GEMINI_CONFIG_DIR", "").strip()
    if cfg_env:
        return Path(cfg_env).expanduser()
    home = os.environ.get("HOME", "").strip() or os.environ.get("USERPROFILE", "").strip()
    base = Path(home).expanduser() if home else Path.home()
    return base / ".gemini" / "config"


def _find_repo_state_file(plugin_root: Path) -> Path | None:
    """Locate real docs/tdq/state.json near plugin_root if present."""
    for base in (plugin_root, *plugin_root.parents[:3]):
        cand = base / "docs" / "tdq" / "state.json"
        if cand.is_file():
            return cand
    return None


def _snapshot_tree(root: Path) -> dict[str, tuple[int, int]]:
    """Capture rel_path -> (size, mtime_ns) without mutating `root`."""
    if not root.is_dir():
        return {}
    snap: dict[str, tuple[int, int]] = {}
    try:
        for item in sorted(root.rglob("*")):
            if "__pycache__" in item.parts or item.suffix == ".pyc":
                continue
            if item.is_file():
                st = item.stat()
                snap[item.relative_to(root).as_posix()] = (st.st_size, st.st_mtime_ns)
    except OSError:
        return snap
    return snap


def _snapshot_file(path: Path | None) -> tuple[bool, int, int] | None:
    """Capture (exists, size, mtime_ns) for a single state file."""
    if path is None:
        return None
    if not path.is_file():
        return (False, 0, 0)
    st = path.stat()
    return (True, st.st_size, st.st_mtime_ns)


def _sub_kwargs() -> dict[str, Any]:
    """Build cross-platform subprocess kwargs hiding Windows consoles."""
    kw: dict[str, Any] = dict(tdq_ten_lenh.tham_so_subprocess_an_cua_so())
    if os.name != "nt":
        kw["start_new_session"] = True
    return kw


def _run_cmd(
    cmd: list[str],
    cwd: Path,
    env: dict[str, str],
    timeout_sec: float,
    stdin_text: str | None = None,
) -> tuple[int, str, str, float]:
    """Run command quietly with bounded timeout and return (rc, out, err, ms)."""
    t0 = time.perf_counter()
    proc = tdq_ten_lenh.chay_subprocess(
        cmd,
        cwd=str(cwd),
        env=env,
        input=stdin_text,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=max(1.0, timeout_sec),
    )
    elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
    return proc.returncode, proc.stdout or "", proc.stderr or "", elapsed_ms


def _kill_process_group(proc: subprocess.Popen[bytes]) -> None:
    """Terminate an active subprocess tree across Windows and POSIX."""
    if proc.poll() is not None:
        return
    if os.name == "nt":
        try:
            tdq_ten_lenh.chay_subprocess(
                ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                capture_output=True,
                timeout=3,
            )
        except (OSError, subprocess.SubprocessError):
            pass
    else:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except OSError:
            pass
    if proc.poll() is None:
        try:
            proc.kill()
        except OSError:
            pass


def _terminate_process_tree(proc: subprocess.Popen[bytes]) -> None:
    """Close stdio pipes and guarantee child process termination."""
    if proc.stdin is not None:
        try:
            proc.stdin.close()
        except OSError:
            pass
    _kill_process_group(proc)
    try:
        proc.wait(timeout=2)
    except (OSError, subprocess.SubprocessError):
        pass
    for stream in (proc.stdout, proc.stderr):
        if stream is not None:
            try:
                stream.close()
            except OSError:
                pass


def _handle_remove_readonly(func: Any, path: str, exc: BaseException) -> None:
    """Clear Windows read-only attribute (such as `.git/objects/*`) and retry."""
    if isinstance(exc, PermissionError):
        os.chmod(path, stat.S_IWRITE)
        func(path)
        return
    raise exc


def _rmtree_with_readonly(target: Path) -> None:
    """Remove directory tree handling read-only files across Python versions."""
    if sys.version_info >= (3, 12):
        shutil.rmtree(target, onexc=_handle_remove_readonly)
        return

    def _legacy_handler(func: Any, path: str, exc_info: Any) -> None:
        _handle_remove_readonly(func, path, exc_info[1])

    shutil.rmtree(target, onerror=_legacy_handler)


def _kill_pid_tree(pid: int) -> None:
    """Terminate an OS process tree by PID across Windows and POSIX."""
    if pid <= 0:
        return
    if os.name == "nt":
        try:
            tdq_ten_lenh.chay_subprocess(
                ["taskkill", "/F", "/T", "/PID", str(pid)],
                capture_output=True,
                timeout=3,
            )
        except (OSError, subprocess.SubprocessError):
            pass
        return
    try:
        os.kill(pid, signal.SIGKILL)
    except OSError:
        pass


def _stop_sandbox_daemons(sandbox: Path) -> None:
    """Terminate any detached agent-lsp daemons anchored inside `sandbox`."""
    try:
        pid_files = list(sandbox.rglob("daemon.pid"))
    except OSError:
        return
    for pid_file in pid_files:
        try:
            raw = pid_file.read_text(encoding="utf-8", errors="replace").strip()
            pid = int(raw)
        except (OSError, ValueError):
            continue
        _kill_pid_tree(pid)


def _cleanup_sandbox(sandbox: Path) -> bool:
    """Stop sandbox daemons and remove temporary directory cleanly."""
    if not sandbox.exists():
        return True
    _stop_sandbox_daemons(sandbox)
    for attempt in range(15):
        try:
            _rmtree_with_readonly(sandbox)
            return True
        except OSError:
            time.sleep(0.05 * min(attempt + 1, 4))
    return not sandbox.exists()


def _remaining_sec(deadline: float, cap: float = 15.0) -> float:
    """Return bounded remaining timeout in seconds."""
    left = deadline - time.monotonic()
    if left <= 0.2:
        raise TimeoutError("Verification wall-clock budget exceeded")
    return min(cap, left)


def _sandbox_env(sandbox: Path, plugin_root: Path, sample_repo: Path) -> dict[str, str]:
    """Build isolated subprocess environment anchored inside `sandbox`."""
    fake_home = sandbox / "home"
    fake_state = sandbox / "state"
    fake_home.mkdir(parents=True, exist_ok=True)
    fake_state.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env["HOME"] = str(fake_home)
    env["USERPROFILE"] = str(fake_home)
    env["GEMINI_CONFIG_DIR"] = str(fake_home / ".gemini" / "config")
    env["ANTIGRAVITY_GEMINI_DIR"] = str(fake_home / ".gemini")
    env["TDQ_SETUP_STATE_DIR"] = str(fake_state)
    env["PLUGIN_DATA"] = str(fake_state)
    env["PLUGIN_ROOT"] = str(plugin_root)
    env["TDQ_PROJECT_DIR"] = str(sample_repo)
    env["TDQ_HOST"] = "antigravity"
    env["TDQ_KHONG_CHAM_MAY"] = "1"
    env["TDQ_KHOI_TAO_NEN"] = "0"
    env["TDQ_LOG"] = "0"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def _create_sample_repo(sample_repo: Path) -> Path:
    """Create tiny Python + TS + Git repository inside sandbox."""
    sample_repo.mkdir(parents=True, exist_ok=True)
    (sample_repo / "pyrightconfig.json").write_text('{"include": ["."]}\n', encoding="utf-8")
    (sample_repo / "tsconfig.json").write_text(
        '{"compilerOptions": {"target": "ES2022", "baseUrl": "."}}\n',
        encoding="utf-8",
    )
    (sample_repo / "util.py").write_text(
        "def calc_sum(a: int, b: int) -> int:\n    return a + b\n",
        encoding="utf-8",
    )
    (sample_repo / "main.py").write_text(
        "from util import calc_sum\n\ndef run() -> int:\n    return calc_sum(2, 3)\n",
        encoding="utf-8",
    )
    (sample_repo / "helper.ts").write_text(
        'export function greetUser(name: string): string {\n  return "Hello " + name;\n}\n',
        encoding="utf-8",
    )
    (sample_repo / "app.ts").write_text(
        'import { greetUser } from "./helper";\nexport const msg = greetUser("tdq");\n',
        encoding="utf-8",
    )
    (sample_repo / "docs" / "tdq").mkdir(parents=True, exist_ok=True)
    (sample_repo / "docs" / "tdq" / "state.json").write_text(
        '{"active_request": "", "phase": "idle"}\n',
        encoding="utf-8",
    )
    git_bin = shutil.which("git")
    if git_bin:
        env = dict(os.environ, GIT_TERMINAL_PROMPT="0")
        _run_cmd([git_bin, "init", "-b", "main"], sample_repo, env, 10.0)
        _run_cmd([git_bin, "config", "user.email", "sim@tdq.local"], sample_repo, env, 5.0)
        _run_cmd([git_bin, "config", "user.name", "TDQ Sim"], sample_repo, env, 5.0)
        _run_cmd([git_bin, "add", "."], sample_repo, env, 10.0)
        _run_cmd([git_bin, "commit", "-m", "sim init"], sample_repo, env, 10.0)
    return sample_repo


def _rpc_wait_id(
    msg_q: queue.Queue[Any], req_id: int, deadline: float, method: str
) -> dict[str, Any]:
    """Wait until queue produces JSON-RPC response matching `req_id`."""
    while True:
        wait_for = deadline - time.monotonic()
        if wait_for <= 0:
            raise TimeoutError(f"JSON-RPC timeout waiting for {method} (id={req_id})")
        try:
            item = msg_q.get(timeout=wait_for)
        except queue.Empty as exc:
            raise TimeoutError(f"JSON-RPC timeout waiting for {method} (id={req_id})") from exc
        if item is None:
            raise RuntimeError(f"JSON-RPC server exited before {method} reply")
        if isinstance(item, dict) and item.get("id") == req_id:
            return item


def _send_rpc_line(proc: subprocess.Popen[bytes], payload: dict[str, Any]) -> None:
    """Write one newline-delimited JSON-RPC frame to process stdin."""
    if proc.stdin is None:
        raise RuntimeError("JSON-RPC process missing stdin pipe")
    raw = (json.dumps(payload) + "\n").encode("utf-8")
    proc.stdin.write(raw)
    proc.stdin.flush()


def _start_jsonrpc_reader(proc: subprocess.Popen[bytes], msg_q: queue.Queue[Any]) -> threading.Thread:
    """Spawn daemon thread decoding newline-delimited JSON-RPC frames."""

    def _reader() -> None:
        if proc.stdout is None:
            msg_q.put(None)
            return
        for raw_line in iter(proc.stdout.readline, b""):
            text = raw_line.decode("utf-8", errors="replace").strip()
            if not text:
                continue
            try:
                msg_q.put(json.loads(text))
            except ValueError:
                continue
        msg_q.put(None)

    thread = threading.Thread(target=_reader, daemon=True)
    thread.start()
    return thread


def _drive_jsonrpc_session(
    proc: subprocess.Popen[bytes],
    msg_q: queue.Queue[Any],
    deadline: float,
    extra_calls: list[tuple[str, dict[str, Any]]] | None,
) -> tuple[dict[str, Any], list[str], list[dict[str, Any]]]:
    """Perform initialize, tools/list, and optional tool calls on active RPC pipes."""
    _send_rpc_line(proc, {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "tdq-simulate-verify", "version": "1.0"},
        },
    })
    init_msg = _rpc_wait_id(msg_q, 1, deadline, "initialize")
    _send_rpc_line(proc, {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})
    _send_rpc_line(proc, {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
    tools_msg = _rpc_wait_id(msg_q, 2, deadline, "tools/list")
    extra_res: list[dict[str, Any]] = []
    for idx, (method, params) in enumerate(extra_calls or [], start=3):
        _send_rpc_line(proc, {"jsonrpc": "2.0", "id": idx, "method": method, "params": params})
        extra_res.append(_rpc_wait_id(msg_q, idx, deadline, method))
    tools = (tools_msg.get("result") or {}).get("tools") or []
    names = [str(t.get("name", "")) for t in tools if isinstance(t, dict)]
    return init_msg.get("result") or {}, names, extra_res


def run_mcp_jsonrpc_handshake(
    cmd: list[str],
    cwd: Path,
    env: dict[str, str],
    timeout_sec: float = 10.0,
    extra_calls: list[tuple[str, dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    """Execute interactive JSON-RPC initialize + tools/list handshake over stdio pipes."""
    t0 = time.perf_counter()
    deadline = time.monotonic() + max(0.1, float(timeout_sec))
    proc = subprocess.Popen(
        cmd,
        cwd=str(cwd),
        env=env,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        **_sub_kwargs(),
    )
    msg_q: queue.Queue[Any] = queue.Queue()
    thread = _start_jsonrpc_reader(proc, msg_q)
    try:
        init_res, names, extra_res = _drive_jsonrpc_session(proc, msg_q, deadline, extra_calls)
        return {
            "init": init_res,
            "tools": names,
            "tools_count": len(names),
            "extra": extra_res,
            "latency_ms": round((time.perf_counter() - t0) * 1000.0, 2),
        }
    finally:
        _terminate_process_tree(proc)
        thread.join(timeout=1.0)


def _find_bundle_root(plugin_root: Path) -> tuple[str, Path]:
    """Identify compiled plugin layout vs repository checkout."""
    if (plugin_root / "plugin.json").is_file():
        return "compiled", plugin_root
    bundled = plugin_root / "plugins" / "tdq-workflow-agy"
    if (bundled / "plugin.json").is_file():
        return "repo_with_bundle", bundled
    return "repo", plugin_root


def _validate_manifest_files(layout: str, bundle_root: Path, plugin_root: Path) -> list[str]:
    """Validate JSON syntax and path portability of plugin manifest files."""
    errors: list[str] = []
    targets = (
        (bundle_root / "plugin.json", bundle_root / "hooks.json", bundle_root / "mcp_config.json")
        if layout in ("compiled", "repo_with_bundle")
        else (plugin_root / ".claude-plugin" / "plugin.json", plugin_root / "hooks" / "hooks.json")
    )
    for path in targets:
        if not path.is_file():
            errors.append(f"missing_manifest:{path.name}")
            continue
        raw = path.read_text(encoding="utf-8")
        try:
            data = json.loads(raw)
        except ValueError as exc:
            errors.append(f"invalid_json:{path.name}:{exc}")
            continue
        if not isinstance(data, dict):
            errors.append(f"non_object_json:{path.name}")
        if path.name in ("mcp_config.json", "hooks.json") and _PERSONAL_PATH_RE.search(raw):
            errors.append(f"personal_path_leak:{path.name}")
    return errors


def _run_agy_validate(bundle_root: Path, env: dict[str, str], timeout_sec: float) -> dict[str, Any]:
    """Execute `agy plugin validate --strict --json` when `agy` and plugin.json exist."""
    agy_bin = shutil.which("agy.EXE") or shutil.which("agy")
    if not agy_bin or not (bundle_root / "plugin.json").is_file():
        return {"ok": True, "skipped": True, "reason": "agy_or_plugin_json_absent"}
    rc, out, err, ms = _run_cmd(
        [agy_bin, "plugin", "validate", str(bundle_root), "--strict", "--json"],
        bundle_root,
        env,
        timeout_sec,
    )
    if rc != 0:
        return {"ok": False, "skipped": False, "elapsed_ms": ms, "detail": (out or err)[:200]}
    try:
        parsed = json.loads(out)
    except ValueError:
        return {"ok": False, "skipped": False, "elapsed_ms": ms, "detail": "invalid_validate_json"}
    findings = parsed.get("findings") or []
    return {"ok": len(findings) == 0, "skipped": False, "elapsed_ms": ms, "findings": findings}


def _run_toolchain_probe(plugin_root: Path, env: dict[str, str], timeout_sec: float) -> dict[str, Any]:
    """Run `tdq_setup_probe.mjs --json` and verify core binaries."""
    probe = plugin_root / "scripts" / "tdq_setup_probe.mjs"
    if not probe.is_file():
        probe = Path(__file__).resolve().parent / "tdq_setup_probe.mjs"
    node_bin = shutil.which("node")
    if not node_bin or not probe.is_file():
        return {"ok": False, "reason": "node_or_probe_missing"}
    rc, out, err, ms = _run_cmd([node_bin, str(probe), "--json"], plugin_root, env, timeout_sec)
    if rc != 0:
        return {"ok": False, "reason": f"probe_rc_{rc}", "detail": err[:160]}
    try:
        report = json.loads(out)
    except ValueError:
        return {"ok": False, "reason": "probe_invalid_json"}
    core_ok = all(bool((report.get(k) or {}).get("usable")) for k in ("node", "python", "git", "agent-lsp"))
    report["ok"] = core_ok and report.get("schema_version") == 1
    report["invoke_ms"] = ms
    return report


def _run_t1_manifest_and_probe(
    plugin_root: Path, env: dict[str, str], deadline: float, log_file: Path | None
) -> dict[str, Any]:
    """T1: Validate plugin manifests and probe host toolchain via Node ESM."""
    t0 = time.perf_counter()
    layout, bundle_root = _find_bundle_root(plugin_root)
    manifest_errors = _validate_manifest_files(layout, bundle_root, plugin_root)
    agy_res = _run_agy_validate(bundle_root, env, _remaining_sec(deadline, 15.0))
    probe_res = _run_toolchain_probe(plugin_root, env, _remaining_sec(deadline, 10.0))
    passed = not manifest_errors and bool(agy_res.get("ok")) and bool(probe_res.get("ok"))
    elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
    _log(f"T1 status={'PASS' if passed else 'FAIL'} layout={layout} ms={elapsed_ms}", log_file)
    return {
        "status": "PASS" if passed else "FAIL",
        "gate": "core",
        "elapsed_ms": elapsed_ms,
        "details": {
            "layout": layout,
            "manifest_errors": manifest_errors,
            "agy_validate": agy_res,
            "toolchain": probe_res,
        },
    }


def _resolve_rust_binary(plugin_root: Path) -> Path | None:
    """Locate compiled Rust `tdq-dispatch` binary in `plugin_root/bin` if present."""
    bin_dir = plugin_root / "bin"
    if not bin_dir.is_dir():
        return None
    plat = sys.platform
    arch = platform.machine().lower()
    if plat.startswith("win"):
        names: tuple[str, ...] = ("tdq-dispatch.exe",)
    elif plat == "darwin":
        arch_name = "tdq-dispatch-darwin-arm64" if "arm" in arch or "aarch64" in arch else "tdq-dispatch-darwin-x64"
        names = (arch_name, "tdq-dispatch")
    else:
        names = ("tdq-dispatch-linux-x86_64", "tdq-dispatch")
    for name in names:
        cand = bin_dir / name
        if cand.is_file():
            return cand
    return None


def _hook_cmd_for_event(
    plugin_root: Path, event: str, rust_bin: Path | None
) -> tuple[str, list[str] | None]:
    """Resolve subprocess command for one lifecycle hook event."""
    if rust_bin is not None:
        return "rust_binary", [str(rust_bin), "--event", event]
    dispatch_py = plugin_root / "hooks" / "scripts" / "dispatch.py"
    if dispatch_py.is_file():
        return "python_fallback", [sys.executable, "-X", "utf8", str(dispatch_py), "--event", event]
    script_map = {
        "SessionStart": "session_start.py",
        "PreInvocation": "prompt_context.py",
        "PreToolUse": "read_gate.py",
        "PostToolUse": "search_observe.py",
        "PostInvocation": "post_invocation.py",
        "Stop": "stop_gate.py",
        "SubagentStart": "subagent_start.py",
        "SubagentStop": "subagent_stop.py",
    }
    target = plugin_root / "hooks" / "scripts" / script_map.get(event, "")
    if target.is_file():
        return "python_fallback", [sys.executable, "-X", "utf8", str(target), "--event", event]
    return "python_fallback", None


def _event_payloads(sample_repo: Path) -> dict[str, dict[str, Any]]:
    """Construct minimal valid Antigravity payloads for the 6 lifecycle events."""
    return {
        "SessionStart": {"cwd": str(sample_repo), "conversation_id": "sim-t2", "source": "startup"},
        "PreInvocation": {"cwd": str(sample_repo), "conversation_id": "sim-t2", "user_message": "status check"},
        "PreToolUse": {
            "cwd": str(sample_repo),
            "conversation_id": "sim-t2",
            "toolName": "read_file",
            "toolInput": {"AbsolutePath": str(sample_repo / "util.py"), "StartLine": 1, "EndLine": 2},
        },
        "PostToolUse": {
            "cwd": str(sample_repo),
            "conversation_id": "sim-t2",
            "toolName": "grep_search",
            "toolInput": {"Query": "calc_sum"},
        },
        "PostInvocation": {"cwd": str(sample_repo), "conversation_id": "sim-t2"},
        "Stop": {"cwd": str(sample_repo), "conversation_id": "sim-t2", "continuationActive": False},
    }


def _is_json_dict_output(out: str) -> bool:
    """Return True when hook stdout is empty or ends with a JSON object."""
    stripped = out.strip()
    if not stripped:
        return True
    try:
        return isinstance(json.loads(stripped.splitlines()[-1]), dict)
    except ValueError:
        return False


def _evaluate_hook_attempt(
    cmd: list[str],
    sample_repo: Path,
    sandbox_env: dict[str, str],
    deadline: float,
    raw_payload: str,
    must_be_hot: bool,
    best_ms: float | None,
) -> tuple[bool, int, str, float, bool]:
    """Run one hook invocation and evaluate exit code, JSON dict, and hot latency."""
    rc, out, err, cur_ms = _run_cmd(
        cmd, sample_repo, sandbox_env, _remaining_sec(deadline, 10.0), raw_payload
    )
    json_ok = _is_json_dict_output(out)
    new_best = cur_ms if best_ms is None else min(best_ms, cur_ms)
    hot_ok = (not must_be_hot) or (new_best < HOT_HOOK_BUDGET_MS)
    return json_ok, rc, err, new_best, hot_ok


def _format_hook_result(
    rc: int, json_ok: bool, hot_ok: bool, best_ms: float | None, err: str
) -> tuple[bool, dict[str, Any]]:
    """Package verdict and diagnostic payload for one lifecycle hook run."""
    ev_ok = (rc == 0) and json_ok and hot_ok
    return ev_ok, {
        "returncode": rc,
        "elapsed_ms": float(best_ms or 0.0),
        "json_ok": json_ok,
        "hot_ok": hot_ok,
        "err_head": "" if ev_ok else err.strip()[:120],
    }


def _run_single_lifecycle_hook(
    plugin_root: Path,
    event: str,
    payload: dict[str, Any],
    rust_bin: Path | None,
    engine: str,
    sample_repo: Path,
    sandbox_env: dict[str, str],
    deadline: float,
) -> tuple[bool, dict[str, Any]]:
    """Execute one lifecycle hook event and evaluate exit code, JSON, and latency."""
    _, cmd = _hook_cmd_for_event(plugin_root, event, rust_bin)
    if cmd is None:
        return True, {"returncode": 0, "elapsed_ms": 0.0, "skipped": True}
    raw_payload = json.dumps(payload)
    must_be_hot = (engine == "rust_binary") and (event in HOT_EVENTS)
    attempts = 3 if must_be_hot else 1
    best_ms: float | None = None
    rc, err, json_ok, hot_ok = 1, "", False, False
    for _ in range(attempts):
        json_ok, rc, err, best_ms, hot_ok = _evaluate_hook_attempt(
            cmd, sample_repo, sandbox_env, deadline, raw_payload, must_be_hot, best_ms
        )
        if rc != 0 or not json_ok or hot_ok:
            break
    return _format_hook_result(rc, json_ok, hot_ok, best_ms, err)


def _run_t2_lifecycle_hooks(
    plugin_root: Path,
    sample_repo: Path,
    sandbox_env: dict[str, str],
    deadline: float,
    log_file: Path | None,
) -> dict[str, Any]:
    """T2: Simulate all 6 lifecycle hooks in sandbox and enforce < 50ms hot Rust paths."""
    t0 = time.perf_counter()
    rust_bin = _resolve_rust_binary(plugin_root)
    engine = "rust_binary" if rust_bin is not None else "python_fallback"
    results: dict[str, dict[str, Any]] = {}
    passed = True
    for event, payload in _event_payloads(sample_repo).items():
        ev_ok, row = _run_single_lifecycle_hook(
            plugin_root, event, payload, rust_bin, engine, sample_repo, sandbox_env, deadline
        )
        passed = passed and ev_ok
        results[event] = row
    elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
    _log(f"T2 status={'PASS' if passed else 'FAIL'} engine={engine} ms={elapsed_ms}", log_file)
    return {
        "status": "PASS" if passed else "FAIL",
        "gate": "core",
        "elapsed_ms": elapsed_ms,
        "details": {"engine": engine, "events": results},
    }


def _load_mcp_config(plugin_root: Path) -> tuple[Path, dict[str, Any]]:
    """Load `mcp_config.json` from plugin root or bundled plugin directory."""
    for cand in (
        plugin_root / "mcp_config.json",
        plugin_root / "plugins" / "tdq-workflow-agy" / "mcp_config.json",
        plugin_root / ".mcp.json",
    ):
        if cand.is_file():
            try:
                data = json.loads(cand.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    return cand.parent, data
            except (OSError, ValueError) as exc:
                _log(f"_load_mcp_config: failed reading {cand}: {type(exc).__name__}")
    return plugin_root, {}


def _expand_mcp_command(entry: dict[str, Any], cfg_root: Path, sandbox_data: Path) -> list[str]:
    """Expand ${PLUGIN_ROOT} and ${PLUGIN_DATA} safely inside sandbox."""
    cmd = str(entry.get("command") or "")
    raw_args = entry.get("args") or []
    args = [
        str(a)
        .replace("${PLUGIN_ROOT}", str(cfg_root))
        .replace("${PLUGIN_DATA}", str(sandbox_data))
        for a in raw_args
    ]
    return [cmd, *args]


def _locate_agent_lsp() -> str | None:
    """Find `agent-lsp` binary on PATH or standard user bin directory."""
    found = shutil.which("agent-lsp")
    if found:
        return found
    home = os.environ.get("USERPROFILE") or os.environ.get("HOME") or str(Path.home())
    exe = "agent-lsp.exe" if os.name == "nt" else "agent-lsp"
    for cand in (Path(home) / ".local" / "bin" / exe, Path(home) / ".cargo" / "bin" / exe):
        if cand.is_file():
            return str(cand)
    return None


def _probe_lsp_handshake(
    mcp_cfg: dict[str, Any],
    cfg_root: Path,
    sandbox_data: Path,
    env: dict[str, str],
    timeout_sec: float,
) -> dict[str, Any]:
    """Run interactive JSON-RPC handshake on `lsp` server entry."""
    servers = mcp_cfg.get("mcpServers") or {}
    lsp_entry = servers.get("lsp") if isinstance(servers, dict) else None
    if isinstance(lsp_entry, dict) and lsp_entry.get("command"):
        cmd = _expand_mcp_command(lsp_entry, cfg_root, sandbox_data)
    else:
        lsp_bin = _locate_agent_lsp()
        if not lsp_bin:
            return {"ok": False, "reason": "agent_lsp_not_found", "tools_count": 0}
        cmd = [lsp_bin]
    res = run_mcp_jsonrpc_handshake(cmd, cfg_root, env, timeout_sec=timeout_sec)
    tools = res["tools"]
    ok = res["tools_count"] > 0 and "start_lsp" in tools and "find_symbol" in tools
    return {"ok": ok, "tools_count": res["tools_count"], "latency_ms": res["latency_ms"]}


def _probe_caveman_wrapper(
    cfg_root: Path, env: dict[str, str], timeout_sec: float
) -> dict[str, Any]:
    """Verify Caveman MCP wrapper script via live JSON-RPC pipe."""
    shrink = cfg_root / "scripts" / "tdq_mcp_shrink.py"
    if not shrink.is_file():
        shrink = Path(__file__).resolve().parent / "tdq_mcp_shrink.py"
    launcher = cfg_root / "scripts" / "tdq_mcp_launcher.mjs"
    lsp_bin = _locate_agent_lsp()
    if not shrink.is_file() or not lsp_bin:
        return {"shrink_verified": False, "reason": "shrink_or_lsp_missing"}
    supports_node_caveman = False
    if launcher.is_file():
        txt = launcher.read_text(encoding="utf-8", errors="replace")
        supports_node_caveman = ('"caveman"' in txt or "'caveman'" in txt) and "buildSpawnSpec" in txt
    node_bin = shutil.which("node")
    if supports_node_caveman and node_bin:
        mode = "node_launcher"
        cmd = [node_bin, str(launcher), "caveman", "--", lsp_bin]
    else:
        mode = "python_proxy"
        cmd = [sys.executable, "-u", str(shrink), "--", lsp_bin]
    res = run_mcp_jsonrpc_handshake(cmd, cfg_root, env, timeout_sec=timeout_sec)
    ok = res["tools_count"] > 0 and "start_lsp" in res["tools"]
    return {
        "shrink_verified": ok,
        "wrapper_mode": mode,
        "tools_count": res["tools_count"],
        "latency_ms": res["latency_ms"],
    }


def _probe_optional_chrome(mcp_cfg: dict[str, Any]) -> dict[str, Any]:
    """Check optional Chrome browser + chrome-devtools-plugin without launching UI."""
    servers = mcp_cfg.get("mcpServers") or {}
    if not isinstance(servers, dict) or "chrome-devtools" not in servers:
        return {"status": "SKIPPED", "reason": "server_not_configured"}
    chrome_path = tdq_devtool_mcp.get_chrome_executable()
    if not chrome_path:
        return {"status": "SKIPPED", "reason": "chrome_not_found"}
    plugins_dir = _resolve_real_gemini_cfg() / "plugins" / "chrome-devtools-plugin"
    if not plugins_dir.is_dir():
        return {"status": "SKIPPED", "reason": "chrome_devtools_plugin_missing"}
    if not (shutil.which("npx") or shutil.which("npx.cmd")):
        return {"status": "SKIPPED", "reason": "npx_not_found"}
    return {"status": "PASS", "reason": "ready", "chrome_path": chrome_path}


def _probe_optional_tavily(
    mcp_cfg: dict[str, Any],
    cfg_root: Path,
    data_dir: Path,
    env: dict[str, str],
    timeout_sec: float,
) -> dict[str, Any]:
    """Probe optional tavily-primary MCP when TAVILY_API_KEY exists, never leaking secret."""
    key_env = os.environ.get("TAVILY_API_KEY", "").strip()
    secrets = tdq_setup_state.load_secrets_env(data_dir=data_dir)
    key = key_env or secrets.get("TAVILY_API_KEY", "").strip()
    if not key:
        return {"status": "SKIPPED", "reason": "skipped_no_key"}
    servers = mcp_cfg.get("mcpServers") or {}
    entry = servers.get("tavily-primary") if isinstance(servers, dict) else None
    if not isinstance(entry, dict) or not entry.get("command"):
        return {"status": "SKIPPED", "reason": "server_not_configured"}
    child_env = {**env, "TAVILY_API_KEY": key}
    cmd = _expand_mcp_command(entry, cfg_root, data_dir)
    try:
        res = run_mcp_jsonrpc_handshake(cmd, cfg_root, child_env, timeout_sec=timeout_sec)
        ok = res["tools_count"] > 0
        return {"status": "PASS" if ok else "FAIL", "tools_count": res["tools_count"]}
    except (OSError, subprocess.SubprocessError, TimeoutError, RuntimeError) as exc:
        return {"status": "FAIL", "reason": f"handshake_error:{type(exc).__name__}"}


def _compute_optional_gate(addons: dict[str, dict[str, Any]]) -> str:
    """Aggregate optional companion statuses into PASS | SKIPPED | FAIL."""
    statuses = [str(item.get("status", "SKIPPED")) for item in addons.values()]
    if any(st == "FAIL" for st in statuses):
        return "FAIL"
    if all(st == "PASS" for st in statuses):
        return "PASS"
    return "SKIPPED"


def _run_t3_mcp_handshakes(
    plugin_root: Path,
    sandbox: Path,
    data_dir: Path,
    env: dict[str, str],
    deadline: float,
    log_file: Path | None,
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    """T3: Interactive JSON-RPC MCP handshakes + optional add-on separation."""
    t0 = time.perf_counter()
    cfg_root, mcp_cfg = _load_mcp_config(plugin_root)
    sandbox_data = sandbox / "mcp_data"
    sandbox_data.mkdir(parents=True, exist_ok=True)
    lsp_res = _probe_lsp_handshake(mcp_cfg, cfg_root, sandbox_data, env, _remaining_sec(deadline, 12.0))
    caveman_res = _probe_caveman_wrapper(cfg_root, env, _remaining_sec(deadline, 12.0))
    optional_addons = {
        "chrome_devtools": _probe_optional_chrome(mcp_cfg),
        "tavily_primary": _probe_optional_tavily(
            mcp_cfg, cfg_root, data_dir, env, _remaining_sec(deadline, 10.0)
        ),
    }
    passed = bool(lsp_res.get("ok")) and bool(caveman_res.get("shrink_verified"))
    elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
    _log(f"T3 status={'PASS' if passed else 'FAIL'} ms={elapsed_ms}", log_file)
    layer = {
        "status": "PASS" if passed else "FAIL",
        "gate": "core",
        "elapsed_ms": elapsed_ms,
        "details": {"lsp": lsp_res, "caveman": caveman_res},
    }
    return layer, optional_addons


def _extract_rpc_text(msg: dict[str, Any]) -> str:
    """Concatenate MCP `result.content[*].text` strings safely."""
    res = msg.get("result") or {}
    parts = res.get("content") or []
    return "\n".join(str(p.get("text", "")) for p in parts if isinstance(p, dict))


def _probe_graphify_sample(
    sample_repo: Path, env: dict[str, str], deadline: float
) -> tuple[bool, dict[str, Any]]:
    """Run tiny `graphify update` + `graphify query` when `graphify` CLI exists."""
    graphify_bin = shutil.which("graphify")
    if not graphify_bin:
        return True, {"status": "SKIPPED", "reason": "graphify_not_installed"}
    rc1, out1, err1, ms1 = _run_cmd(
        [graphify_bin, "update", str(sample_repo), "--no-cluster"],
        sample_repo,
        env,
        _remaining_sec(deadline, 15.0),
    )
    rc2, out2, err2, ms2 = _run_cmd(
        [graphify_bin, "query", "calc_sum"],
        sample_repo,
        env,
        _remaining_sec(deadline, 10.0),
    )
    ok = (rc1 == 0) and (rc2 == 0) and ("calc_sum" in out2)
    return ok, {
        "status": "PASS" if ok else "FAIL",
        "update_ms": ms1,
        "query_ms": ms2,
        "detail": (out2 or err2 or out1 or err1)[:120],
    }


def _prepare_lsp_socket_env(env: dict[str, str]) -> tuple[dict[str, str], Path | None]:
    """Ensure HOME/USERPROFILE stays short enough for OS AF_UNIX daemon sockets."""
    cur_home = env.get("USERPROFILE") or env.get("HOME") or ""
    limit = 50 if sys.platform == "darwin" else 54
    if len(cur_home) <= limit:
        return env, None
    job_root = os.environ.get("TDQ_TEST_JOB_ROOT", "").strip()
    base = Path(job_root) if (job_root and len(job_root) <= limit - 6) else Path(tempfile.gettempdir())
    if len(str(base)) > limit - 6:
        return env, None
    short_home = base / f"l{os.getpid() & 0xfff:x}{int(time.monotonic() * 100) % 100:02d}"
    short_home.mkdir(parents=True, exist_ok=True)
    lsp_env = dict(env)
    lsp_env["HOME"] = str(short_home)
    lsp_env["USERPROFILE"] = str(short_home)
    lsp_env["XDG_CACHE_HOME"] = str(short_home / ".c")
    lsp_env["LOCALAPPDATA"] = str(short_home / "l")
    return lsp_env, short_home


def _verify_lsp_symbol_calls(
    lsp_bin: str, sample_repo: Path, env: dict[str, str], deadline: float
) -> bool:
    """Invoke live start_lsp + find_symbol via JSON-RPC and confirm `calc_sum` hits."""
    calls = [
        ("tools/call", {"name": "start_lsp", "arguments": {"root_dir": str(sample_repo), "language_id": "python"}}),
        ("tools/call", {"name": "find_symbol", "arguments": {"query": "calc_sum"}}),
    ]
    lsp_env, short_home = _prepare_lsp_socket_env(env)
    try:
        extra = run_mcp_jsonrpc_handshake(
            [lsp_bin], sample_repo, lsp_env, timeout_sec=_remaining_sec(deadline, 15.0), extra_calls=calls
        )["extra"]
    finally:
        if short_home is not None and not _cleanup_sandbox(short_home):
            _log(f"_verify_lsp_symbol_calls cleanup incomplete: {short_home}")
    if len(extra) < 2:
        return False
    has_err = any(bool((item.get("result") or {}).get("isError")) for item in extra[:2])
    return (not has_err) and ("calc_sum" in _extract_rpc_text(extra[1]))


def _run_t4_lsp_and_graphify(
    sample_repo: Path, env: dict[str, str], deadline: float, log_file: Path | None
) -> dict[str, Any]:
    """T4: Live `agent-lsp` start_lsp+find_symbol + `graphify` check on sample repo."""
    t0 = time.perf_counter()
    lsp_bin = _locate_agent_lsp()
    if not lsp_bin:
        return {"status": "FAIL", "gate": "core", "elapsed_ms": 0.0, "details": {"reason": "agent_lsp_missing"}}
    symbol_found = _verify_lsp_symbol_calls(lsp_bin, sample_repo, env, deadline)
    rung6 = tdq_lsp.bac6_cau_hinh_goc_import(str(sample_repo))
    graph_ok, graph_info = _probe_graphify_sample(sample_repo, env, deadline)
    passed = symbol_found and bool(rung6.dat) and graph_ok
    elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
    _log(f"T4 status={'PASS' if passed else 'FAIL'} ms={elapsed_ms}", log_file)
    return {
        "status": "PASS" if passed else "FAIL",
        "gate": "core",
        "elapsed_ms": elapsed_ms,
        "details": {
            "lsp_semantic": {"symbol_found": symbol_found, "rung6_ok": bool(rung6.dat)},
            "graphify": graph_info,
        },
    }


def _probe_rtk_rg_smoke(sample_repo: Path, env: dict[str, str]) -> tuple[bool, dict[str, Any]]:
    """Verify collision-free `rtk` and live `rg` search on sample repo."""
    rtk_probe = rtk_integration.probe_rtk(cwd=str(sample_repo))
    rg_bin = rtk_integration.locate_rg_binary() or ""
    if rtk_probe.get("collision"):
        return False, {"status": "FAIL", "collision": True, "reason": rtk_probe.get("reason", "")}
    if rtk_probe.get("valid") and rg_bin:
        rc, out, _, ms = _run_cmd([rg_bin, "--no-config", "calc_sum", str(sample_repo)], sample_repo, env, 8.0)
        rg_hit = (rc == 0) and ("calc_sum" in out)
        return rg_hit, {"status": "PASS" if rg_hit else "FAIL", "collision": False, "rg_ms": ms}
    return True, {"status": "SKIPPED", "collision": False, "reason": "rtk_or_rg_absent"}


def _probe_archify_sandbox(sandbox: Path, timeout_sec: float) -> tuple[bool, dict[str, Any]]:
    """Render a sample Archify explainer HTML strictly inside `sandbox`."""
    arch_env = archify_delivery.check_environment()
    explicit_arch = bool(os.environ.get("ARCHIFY_ROOT", "").strip())
    if not arch_env.get("ready"):
        return (not explicit_arch), {
            "status": "FAIL" if explicit_arch else "SKIPPED",
            "reason": arch_env.get("error") or "archify_not_ready",
        }
    arch_dir = sandbox / "archify"
    arch_dir.mkdir(parents=True, exist_ok=True)
    cand = arch_dir / "candidate.archify.md"
    out_html = arch_dir / "sim-preview.html"
    cand.write_text(
        "# Sim Verify\n\n**Sandbox Archify render test.**\n\n"
        "@meta locale=en style=editorial\n\n## Flow {#flow}\n\n- Verify\n",
        encoding="utf-8",
    )
    res = archify_delivery.run_finalize(
        "explainer",
        cand,
        out_html,
        quality="standard",
        repo_root=arch_dir,
        timeout=max(5, int(min(25.0, timeout_sec))),
    )
    in_sandbox = sandbox.resolve() in out_html.resolve().parents
    ok = bool(res.status) and out_html.is_file() and out_html.stat().st_size > 0 and in_sandbox
    return ok, {
        "status": "PASS" if ok else "FAIL",
        "output_path": str(out_html),
        "bytes": out_html.stat().st_size if out_html.is_file() else 0,
    }


def _run_t5_rtk_and_archify(
    sample_repo: Path,
    sandbox: Path,
    env: dict[str, str],
    timeout_sec: float,
    log_file: Path | None,
) -> dict[str, Any]:
    """T5: Collision-free `rtk`+`rg` smoke check + sandboxed `archify_delivery` HTML render."""
    t0 = time.perf_counter()
    rtk_ok, rtk_info = _probe_rtk_rg_smoke(sample_repo, env)
    arch_ok, arch_info = _probe_archify_sandbox(sandbox, timeout_sec)
    passed = rtk_ok and arch_ok
    elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
    _log(f"T5 status={'PASS' if passed else 'FAIL'} ms={elapsed_ms}", log_file)
    return {
        "status": "PASS" if passed else "FAIL",
        "gate": "core",
        "elapsed_ms": elapsed_ms,
        "details": {"rtk_rg": rtk_info, "archify": arch_info},
    }


def _validate_agent_markdown(path: Path, *, require_tools: bool = True) -> bool:
    """Return True when agent markdown has valid frontmatter and non-empty body."""
    if not path.is_file():
        return False
    text = path.read_text(encoding="utf-8", errors="replace")
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return False
    header, body = match.group(1), match.group(2).strip()
    if not body:
        return False
    req_keys = ("name:", "description:", "tools:", "model:") if require_tools else ("name:", "description:", "model:")
    for key in req_keys:
        if not re.search(rf"^{re.escape(key)}\s*\S+", header, re.MULTILINE):
            return False
    return bool(re.search(rf"^name:\s*{re.escape(path.stem)}\s*$", header, re.MULTILINE))


def _simulate_subagent_hooks(
    plugin_root: Path,
    sample_repo: Path,
    sandbox_env: dict[str, str],
    deadline: float,
) -> tuple[bool, dict[str, dict[str, Any]]]:
    """Run PreInvocation, SubagentStop, and optional SubagentStart inside sandbox."""
    rust_bin = _resolve_rust_binary(plugin_root)
    sub_payloads: dict[str, dict[str, Any]] = {
        "PreInvocation": {
            "cwd": str(sample_repo),
            "conversation_id": "sim-sub-1",
            "agent_type": "tdq-explorer",
            "source": "resume",
        },
        "SubagentStop": {
            "cwd": str(sample_repo),
            "conversation_id": "sim-sub-1",
            "agent_type": "tdq-explorer",
            "last_assistant_message": "Done.",
        },
    }
    if (plugin_root / "hooks" / "scripts" / "subagent_start.py").is_file():
        sub_payloads["SubagentStart"] = {
            "cwd": str(sample_repo),
            "session_id": "sim-sub-1",
            "agent_type": "tdq-explorer",
        }
    sub_events: dict[str, dict[str, Any]] = {}
    hooks_ok = True
    for ev, payload in sub_payloads.items():
        _, cmd = _hook_cmd_for_event(plugin_root, ev, rust_bin if ev != "SubagentStart" else None)
        if cmd is None:
            continue
        rc, _, err, ms = _run_cmd(
            cmd, sample_repo, sandbox_env, _remaining_sec(deadline, 10.0), json.dumps(payload)
        )
        hooks_ok = hooks_ok and (rc == 0)
        sub_events[ev] = {"returncode": rc, "elapsed_ms": ms, "err_head": err.strip()[:120] if rc else ""}
    return hooks_ok, sub_events


def _run_t6_agents_and_subagent_hooks(
    plugin_root: Path,
    sample_repo: Path,
    sandbox_env: dict[str, str],
    deadline: float,
    log_file: Path | None,
) -> dict[str, Any]:
    """T6: Validate 8 `agents/*.md` definitions and simulate subagent hooks."""
    t0 = time.perf_counter()
    agents_dir = plugin_root / "agents"
    require_tools = (plugin_root / "plugin.json").is_file()
    invalid_agents = [
        name
        for name in EXPECTED_AGENTS
        if not _validate_agent_markdown(agents_dir / name, require_tools=require_tools)
    ]
    hooks_ok, sub_events = _simulate_subagent_hooks(plugin_root, sample_repo, sandbox_env, deadline)
    passed = (len(invalid_agents) == 0) and hooks_ok
    elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
    _log(f"T6 status={'PASS' if passed else 'FAIL'} ms={elapsed_ms}", log_file)
    return {
        "status": "PASS" if passed else "FAIL",
        "gate": "core",
        "elapsed_ms": elapsed_ms,
        "details": {
            "agents_count": len(EXPECTED_AGENTS) - len(invalid_agents),
            "invalid_agents": invalid_agents,
            "subagent_hooks": sub_events,
        },
    }


def _execute_all_layers(
    root: Path,
    sandbox: Path,
    target_data: Path,
    deadline: float,
    log_file: Path | None,
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    """Execute T1-T6 sequentially inside isolated `sandbox`."""
    sample_repo = _create_sample_repo(sandbox / "sample_repo")
    s_env = _sandbox_env(sandbox, root, sample_repo)
    layers: dict[str, Any] = {
        "T1": _run_t1_manifest_and_probe(root, s_env, deadline, log_file),
        "T2": _run_t2_lifecycle_hooks(root, sample_repo, s_env, deadline, log_file),
    }
    t3_layer, optional_addons = _run_t3_mcp_handshakes(
        root, sandbox, target_data, s_env, deadline, log_file
    )
    layers["T3"] = t3_layer
    layers["T4"] = _run_t4_lsp_and_graphify(sample_repo, s_env, deadline, log_file)
    layers["T5"] = _run_t5_rtk_and_archify(
        sample_repo, sandbox, s_env, _remaining_sec(deadline, 30.0), log_file
    )
    layers["T6"] = _run_t6_agents_and_subagent_hooks(root, sample_repo, s_env, deadline, log_file)
    return layers, optional_addons


def _build_verify_report(
    root: Path,
    target_data: Path,
    layers: dict[str, Any],
    optional_addons: dict[str, dict[str, Any]],
    errors: list[str],
    temp_cleaned: bool,
    config_untouched: bool,
    elapsed_sec: float,
    timeout: float,
    log_file: Path | None,
) -> dict[str, Any]:
    """Assemble final 6-layer summary dictionary and log completion."""
    all_ok = len(layers) == 6 and all(
        str(layers[k].get("status", "")).upper() == "PASS" for k in ("T1", "T2", "T3", "T4", "T5", "T6")
    )
    core_pass = all_ok and (not errors) and temp_cleaned and config_untouched and (elapsed_sec < timeout)
    core_gate = "PASS" if core_pass else "FAIL"
    optional_gate = _compute_optional_gate(optional_addons) if optional_addons else "SKIPPED"
    _log(
        f"done core_gate={core_gate} optional_gate={optional_gate} "
        f"temp_cleaned={temp_cleaned} elapsed_sec={elapsed_sec}",
        log_file,
    )
    return {
        "schema_version": 1,
        "core_gate": core_gate,
        "optional_gate": optional_gate,
        "temp_cleaned": temp_cleaned,
        "config_untouched": config_untouched,
        "elapsed_sec": elapsed_sec,
        "plugin_root": str(root),
        "data_dir": str(target_data),
        "layers": layers,
        "optional_addons": optional_addons,
        "errors": errors,
    }


def run_simulate_verify(
    plugin_root: Path | None = None,
    data_dir: Path | None = None,
    timeout: float = DEFAULT_TIMEOUT_SEC,
) -> dict[str, Any]:
    """Run all 6 isolated verification layers inside a temporary sandbox."""
    t_start = time.perf_counter()
    deadline = time.monotonic() + max(5.0, float(timeout))
    root = _resolve_plugin_root(plugin_root)
    target_data = Path(data_dir) if data_dir is not None else tdq_setup_state.resolve_plugin_data_dir()
    log_file = _resolve_log_file(target_data, explicit_data_dir=data_dir is not None)
    gemini_cfg_dir, repo_state_file = _resolve_real_gemini_cfg(), _find_repo_state_file(root)
    before_cfg, before_state = _snapshot_tree(gemini_cfg_dir), _snapshot_file(repo_state_file)
    sandbox = Path(tempfile.mkdtemp(prefix=SANDBOX_PREFIX))
    layers: dict[str, Any] = {}
    optional_addons: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    temp_cleaned = False
    _log(f"start plugin_root={root} sandbox={sandbox.name}", log_file)
    try:
        layers, optional_addons = _execute_all_layers(root, sandbox, target_data, deadline, log_file)
    except _RECOVERABLE_ERRORS as exc:
        errors.append(f"{type(exc).__name__}: {exc}")
        _log(f"ERROR {type(exc).__name__}: {exc}", log_file)
    finally:
        temp_cleaned = _cleanup_sandbox(sandbox)
    config_untouched = (
        before_cfg == _snapshot_tree(gemini_cfg_dir)
        and before_state == _snapshot_file(repo_state_file)
    )
    elapsed_sec = round(time.perf_counter() - t_start, 3)
    return _build_verify_report(
        root, target_data, layers, optional_addons, errors,
        temp_cleaned, config_untouched, elapsed_sec, timeout, log_file,
    )


def _build_parser() -> argparse.ArgumentParser:
    """Build CLI parser for `tdq_simulate_verify.py`."""
    parser = argparse.ArgumentParser(description="Run 6-layer isolated TDQ simulation verify.")
    parser.add_argument("--plugin-root", type=Path, default=None, help="Override plugin root dir.")
    parser.add_argument("--state-dir", type=Path, default=None, help="Override plugin data dir.")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_SEC, help="Budget in sec.")
    parser.add_argument("--json", action="store_true", help="Print JSON verification report.")
    parser.add_argument("--khong-log", action="store_true", help="Silence stderr/file logging.")
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint running 6-layer verification."""
    args = _build_parser().parse_args(argv)
    if args.khong_log:
        os.environ["TDQ_LOG"] = "0"
    res = run_simulate_verify(
        plugin_root=args.plugin_root,
        data_dir=args.state_dir,
        timeout=args.timeout,
    )
    if args.json:
        print(json.dumps(res, indent=2, ensure_ascii=False))
    else:
        print(
            f"tdq_simulate_verify · core_gate={res['core_gate']} | "
            f"optional_gate={res['optional_gate']} | temp_cleaned={res['temp_cleaned']} | "
            f"elapsed_sec={res['elapsed_sec']}"
        )
    return 0 if res["core_gate"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
