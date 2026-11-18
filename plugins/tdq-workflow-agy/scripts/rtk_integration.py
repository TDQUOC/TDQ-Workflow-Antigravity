#!/usr/bin/env python3
"""RTK integration: probe, safe rewrite, TOML config, and SHA256 installer."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)
import utf8_io  # noqa: E402,F401 — forces UTF-8 stdio on Windows

MIN_RTK_VERSION = (0, 25, 0)
MAX_CMD_LEN = 32768
DEFAULT_TIMEOUT = 120
RTK_RELEASE_API = "https://api.github.com/repos/rtk-ai/rtk/releases/latest"
RG_RELEASE_API = "https://api.github.com/repos/BurntSushi/ripgrep/releases/latest"

TDQ_INTERNAL_SCRIPTS = frozenset({
    "tdq_state.py",
    "tdq_test.py",
    "tdq_finish.py",
    "tdq_lsp.py",
    "tdq_setup.py",
    "tdq_archify.py",
    "tdq_team.py",
    "doc_lint.py",
})
SHELL_WRAPPERS = frozenset({"env", "sudo", "command", "time", "nohup", "nice", "&"})
PYTHON_VALUE_FLAGS = frozenset({"-X", "-W", "--check-hash-based-pycs"})
GIT_VALUE_FLAGS = frozenset({
    "-C", "-c", "--git-dir", "--work-tree", "--namespace", "--super-prefix",
})
AUDIT_ROLES = ("qc", "reviewer", "security")
DUMP_GIT_SUBCOMMANDS = frozenset({"log", "diff", "show"})
NON_RTK_BUILTINS = frozenset({
    "echo", "printf", "cd", "pwd", "pushd", "popd", "true", "false",
    "exit", "export", "set", "unset", "alias", "type", "mkdir", "rmdir",
    "touch", "cp", "mv", "rm", "ln", "chmod", "chown", "sleep", "wait",
    "test", "write-output", "set-location", "get-location", "new-item",
    "remove-item", "copy-item", "move-item", "out-null", "select-object",
    "format-table", "sort-object", "measure-object",
})
_REWRITE_CACHE_MAX = 128

REQUIRED_RTK_CONFIG = (
    ("telemetry", (("enabled", "false"),)),
    ("display", (("pro_hint", "false"), ("emoji", "false"))),
    ("retriever", (("mode", '"sqlite"'),)),
    ("awareness", (("level", '"default"'),)),
    ("hooks", (("suppress_hook_warning", "true"),)),
)
REQUIRED_EXCLUDE_COMMANDS = ("grep", "rg")


def _log(message: str) -> None:
    """Emit an ISO-timestamped diagnostic line to stderr unless TDQ_LOG=0."""
    if os.environ.get("TDQ_LOG", "1") != "0":
        from datetime import datetime
        stamp = datetime.now().isoformat(timespec="seconds")
        print(f"[{stamp}] rtk_integration: {message}", file=sys.stderr)


def _local_bin_dir() -> str:
    return os.path.expanduser(os.path.join("~", ".local", "bin"))


_WIN_SHIM_EXTS = (".cmd", ".bat", ".com")


def _is_windows() -> bool:
    return os.name == "nt" or sys.platform.startswith("win")


def _candidate_names(base: str) -> tuple[str, ...]:
    if _is_windows():
        return (base,) if base.lower().endswith(".exe") else (f"{base}.exe",)
    return (base,)


def _find_in_dirs(base: str, dirs: list[str]) -> str | None:
    """Find executable in explicit directory list, skipping CWD and shims."""
    win = _is_windows()
    for d in dirs:
        if not d:
            continue
        for name in _candidate_names(base):
            candidate = os.path.join(d, name)
            if not os.path.isfile(candidate):
                continue
            if win or os.access(candidate, os.X_OK):
                return candidate
    return None


def _find_in_local_bin(base: str) -> str | None:
    return _find_in_dirs(base, [_local_bin_dir()])


def _safe_path_dirs() -> list[str]:
    """Return PATH directories excluding '.', empty entries, and current CWD."""
    cwd_norm = os.path.abspath(os.getcwd()).casefold()
    safe = []
    for raw in os.environ.get("PATH", "").split(os.pathsep):
        cleaned = raw.strip().strip('"')
        if not cleaned or cleaned == ".":
            continue
        if os.path.abspath(cleaned).casefold() == cwd_norm:
            continue
        safe.append(cleaned)
    return safe


def _is_safe_path_binary(candidate: str | None) -> str | None:
    """Reject CWD matches and Windows .cmd/.bat/.com shims from which()."""
    if not candidate:
        return None
    norm = os.path.abspath(candidate)
    cwd_norm = os.path.abspath(os.getcwd()).casefold()
    if os.path.dirname(norm).casefold() == cwd_norm:
        return None
    if _is_windows() and not norm.lower().endswith(".exe"):
        return None
    return candidate


def _safe_which_binary(base: str) -> str | None:
    """Locate binary safely via non-CWD PATH .exe lookup then ~/.local/bin."""
    cand = shutil.which(base)
    if _is_safe_path_binary(cand):
        return cand
    if cand is not None:
        found = _find_in_dirs(base, _safe_path_dirs())
        if found:
            return found
    return _find_in_local_bin(base)


def locate_rtk_binary() -> str | None:
    """Locate rtk from TDQ_RTK_BIN, non-CWD PATH .exe, or ~/.local/bin."""
    env_bin = os.environ.get("TDQ_RTK_BIN", "").strip()
    if env_bin:
        if os.sep in env_bin or "/" in env_bin:
            if _is_windows() and env_bin.lower().endswith(_WIN_SHIM_EXTS):
                return None
            return env_bin if os.path.isfile(env_bin) else None
        return _safe_which_binary(env_bin)
    return _safe_which_binary("rtk")


def locate_rg_binary() -> str | None:
    """Locate ripgrep (rg) from non-CWD PATH .exe or ~/.local/bin."""
    return _safe_which_binary("rg")


def _default_runner(argv, **kwargs):
    kwargs.setdefault("encoding", "utf-8")
    kwargs.setdefault("errors", "replace")
    return subprocess.run(argv, **kwargs)


def _probe_result(
    valid: bool,
    version: str = "",
    path: str = "",
    reason: str = "",
    cached: bool = False,
    collision: bool = False,
) -> dict:
    return {
        "valid": valid,
        "version": version,
        "path": path,
        "reason": reason,
        "cached": cached,
        "collision": collision,
    }


def _read_probe_stamp(stamp: str, abs_path: str, st: os.stat_result) -> dict | None:
    try:
        with open(stamp, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict) or data.get("valid") is not True:
        return None
    same_file = (
        data.get("path") == abs_path
        and data.get("size") == st.st_size
        and data.get("mtime_ns") == st.st_mtime_ns
    )
    return data if same_file else None


def _write_json_best_effort(path: str, data: dict) -> None:
    try:
        parent = os.path.dirname(os.path.abspath(path))
        os.makedirs(parent, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=parent, prefix=".tdq-json-", suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
        os.replace(tmp, path)
    except OSError:
        pass


def _parse_semver(text: str) -> tuple[str, tuple[int, int, int]] | None:
    match = re.search(r"(\d+)\.(\d+)\.(\d+)", text or "")
    if not match:
        return None
    parts = (int(match.group(1)), int(match.group(2)), int(match.group(3)))
    return f"{parts[0]}.{parts[1]}.{parts[2]}", parts


def _run_version_check(exec_fn, resolved: str) -> tuple[bool, str, str]:
    try:
        proc = exec_fn(
            [resolved, "--version"], capture_output=True, text=True, timeout=2.0
        )
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        return False, "", f"version_probe_error:{type(exc).__name__}"
    if proc.returncode != 0:
        return False, "", f"version_rc_{proc.returncode}"
    parsed = _parse_semver(f"{proc.stdout or ''} {proc.stderr or ''}")
    if not parsed:
        return False, "", "version_parse_failed"
    ver_str, ver_tuple = parsed
    if ver_tuple < MIN_RTK_VERSION:
        return False, ver_str, f"version_too_old:{ver_str}"
    return True, ver_str, "ok"


def _run_gain_check(exec_fn, resolved: str) -> int | None:
    try:
        with tempfile.TemporaryDirectory(prefix="tdq-rtk-gain-") as tmp_db:
            gain_env = dict(os.environ)
            gain_env["RTK_DB_PATH"] = os.path.join(tmp_db, "history.db")
            gain_env["RTK_SUPPRESS_HOOK_WARNING"] = "1"
            proc = exec_fn(
                [resolved, "gain"],
                capture_output=True,
                text=True,
                timeout=8.0,
                env=gain_env,
            )
            return proc.returncode
    except (OSError, subprocess.SubprocessError, ValueError):
        return None


def probe_rtk(cwd=None, runner=None, bin_path=None) -> dict:
    """Verify rtk >= 0.25.0 with Collision Guard and stat-keyed stamp cache."""
    resolved = bin_path or locate_rtk_binary()
    if not resolved:
        return _probe_result(False, reason="not_found")
    try:
        st = os.stat(resolved)
    except OSError as exc:
        return _probe_result(False, path=resolved, reason=f"stat_failed:{exc}")
    abs_path = os.path.abspath(resolved)
    stamp = os.path.join(cwd or os.getcwd(), ".tdq-runtime", "rtk-probe.json")
    cached = _read_probe_stamp(stamp, abs_path, st)
    if cached is not None:
        ver = str(cached.get("version", ""))
        return _probe_result(True, ver, resolved, "cached", cached=True)
    exec_fn = runner or _default_runner
    ok_ver, ver_str, ver_reason = _run_version_check(exec_fn, resolved)
    if not ok_ver:
        return _probe_result(False, ver_str, resolved, ver_reason)
    gain_rc = _run_gain_check(exec_fn, resolved)
    if gain_rc is None:
        _log(f"probe_rtk: gain check failed at {resolved} (ver={ver_str})")
        return _probe_result(
            False, ver_str, resolved, "gain_probe_failed", collision=False
        )
    if gain_rc != 0:
        _log(f"probe_rtk: collision at {resolved} (ver={ver_str}, gain={gain_rc})")
        return _probe_result(
            False, ver_str, resolved, "collision_rust_type_kit", collision=True
        )
    stamp_obj = {
        "path": abs_path,
        "size": st.st_size,
        "mtime_ns": st.st_mtime_ns,
        "valid": True,
        "version": ver_str,
    }
    _write_json_best_effort(stamp, stamp_obj)
    _log(f"probe_rtk: verified rtk {ver_str} at {resolved}")
    return _probe_result(True, ver_str, resolved, "ok")


def _split_segments(cmd: str) -> list[tuple[str, str]]:
    """Split a shell command into (separator, segment) pairs outside quotes."""
    segments: list[tuple[str, str]] = []
    sep, start, idx, n = "", 0, 0, len(cmd)
    in_single, in_double = False, False
    while idx < n:
        ch = cmd[idx]
        if in_single:
            in_single = ch != "'"
        elif in_double:
            if ch == "\\" and idx + 1 < n and cmd[idx + 1] in ('"', "\\"):
                idx += 1
            elif ch == '"':
                in_double = False
        elif ch in ("'", '"'):
            in_single, in_double = ch == "'", ch == '"'
        elif cmd[idx:idx + 2] in ("&&", "||"):
            segments.append((sep, cmd[start:idx]))
            sep, start = cmd[idx:idx + 2], idx + 2
            idx += 2
            continue
        elif ch in (";", "|", "\n"):
            segments.append((sep, cmd[start:idx]))
            sep, start = ch, idx + 1
        idx += 1
    segments.append((sep, cmd[start:]))
    return segments


def _tokenize_segment(seg: str) -> list[str]:
    """Tokenize one shell segment while preserving Windows backslashes."""
    tokens, buf, active = [], [], False
    in_single, in_double = False, False
    idx, n = 0, len(seg)
    while idx < n:
        ch = seg[idx]
        if in_single or in_double:
            if (in_single and ch == "'") or (in_double and ch == '"'):
                in_single, in_double = False, False
            elif (
                in_double
                and ch == "\\"
                and idx + 1 < n
                and seg[idx + 1] in ('"', "\\")
            ):
                buf.append(seg[idx + 1])
                idx += 1
            else:
                buf.append(ch)
        elif ch in (" ", "\t", "\r"):
            if active:
                tokens.append("".join(buf))
                buf.clear()
                active = False
        elif ch in ("'", '"'):
            in_single, in_double, active = ch == "'", ch == '"', True
        else:
            buf.append(ch)
            active = True
        idx += 1
    if active:
        tokens.append("".join(buf))
    return tokens


def _strip_wrappers(tokens: list[str]) -> list[str]:
    idx = 0
    while idx < len(tokens):
        tok = tokens[idx]
        if re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", tok) or tok in SHELL_WRAPPERS:
            idx += 1
            continue
        break
    return tokens[idx:]


def _basename_stem(token: str) -> tuple[str, str, list[str]]:
    norm = token.replace("\\", "/")
    parts = [p.lower() for p in norm.split("/") if p]
    base = parts[-1] if parts else ""
    stem = base[:-4] if base.endswith(".exe") else base
    return base, stem, parts


def _is_python_skip(args: list[str]) -> str | None:
    idx = 0
    while idx < len(args):
        tok = args[idx]
        if tok == "-m" and idx + 1 < len(args):
            return "python_m_pytest" if args[idx + 1].lower() == "pytest" else None
        if tok.lower() == "-mpytest":
            return "python_m_pytest"
        if tok in PYTHON_VALUE_FLAGS:
            idx += 2
            continue
        if tok in ("-c", "-"):
            return None
        if tok.startswith("-"):
            idx += 1
            continue
        script_base = tok.replace("\\", "/").rsplit("/", 1)[-1].lower()
        return "tdq_script" if script_base in TDQ_INTERNAL_SCRIPTS else None
    return None


def _git_subcommand(tokens: list[str]) -> str | None:
    if not tokens:
        return None
    _, stem, _ = _basename_stem(tokens[0])
    if stem != "git":
        return None
    idx = 1
    while idx < len(tokens):
        tok = tokens[idx]
        if tok in GIT_VALUE_FLAGS:
            idx += 2
            continue
        if tok.startswith("-"):
            idx += 1
            continue
        return tok.lower()
    return None


def _segment_skip_reason(tokens: list[str], audit_role: bool) -> str | None:
    core = _strip_wrappers(tokens)
    if not core:
        return None
    base, stem, parts = _basename_stem(core[0])
    if ".venv" in parts or "venv" in parts:
        return "venv_command"
    if base in TDQ_INTERNAL_SCRIPTS:
        return "tdq_script"
    if stem in ("py", "python", "python3") or re.match(r"^python3\.\d+$", stem):
        py_skip = _is_python_skip(core[1:])
        if py_skip:
            return py_skip
    if audit_role and _git_subcommand(core) == "diff":
        return "audit_role_git_diff"
    return None


def _all_segments_non_rtk(segments: list[tuple[str, str]]) -> bool:
    """True when every non-empty command segment is a basic shell builtin never rewritten by rtk."""
    saw_segment = False
    for _, seg in segments:
        core = _strip_wrappers(_tokenize_segment(seg))
        if not core:
            continue
        saw_segment = True
        _, stem, _ = _basename_stem(core[0])
        if stem not in NON_RTK_BUILTINS:
            return False
    return saw_segment


def should_skip_rewrite(cmd: str, role: str = "") -> tuple[bool, str]:
    """Return (True, reason) when rtk rewrite must be bypassed."""
    if os.environ.get("TDQ_RTK", "1") == "0" or os.environ.get("RTK_DISABLED") == "1":
        return True, "disabled_by_env"
    if not isinstance(cmd, str) or not cmd.strip():
        return True, "empty"
    if len(cmd) > MAX_CMD_LEN:
        return True, "too_long"
    role_low = (role or "").lower()
    audit_role = any(tag in role_low for tag in AUDIT_ROLES)
    segments = _split_segments(cmd)
    for _, seg in segments:
        reason = _segment_skip_reason(_tokenize_segment(seg), audit_role)
        if reason:
            return True, reason
    if _all_segments_non_rtk(segments):
        return True, "non_rtk_builtin"
    return False, ""


def can_compress_dump_command(
    cmd: str, cwd=None, role: str = "", probe_fn=None
) -> bool:
    """Return True when git log/diff/show will be compressed by rtk."""
    skip, _ = should_skip_rewrite(cmd, role=role)
    if skip:
        return False
    has_dump = any(
        _git_subcommand(_strip_wrappers(_tokenize_segment(seg))) in DUMP_GIT_SUBCOMMANDS
        for _, seg in _split_segments(cmd)
    )
    if not has_dump:
        return False
    probe = (probe_fn or probe_rtk)(cwd=cwd)
    return bool(probe.get("valid"))


def _qualify_rtk_for_powershell(rewritten: str, bin_path: str) -> str:
    """Wrap leading rtk token for PowerShell when safe rtk is off non-CWD PATH."""
    if not sys.platform.startswith("win"):
        return rewritten
    on_safe_path = bool(
        _is_safe_path_binary(shutil.which("rtk"))
        and _find_in_dirs("rtk", _safe_path_dirs())
    )
    if on_safe_path:
        return rewritten
    quoted = "'" + bin_path.replace("'", "''") + "'"
    out: list[str] = []
    for sep, seg in _split_segments(rewritten):
        stripped = seg.lstrip(" \t")
        lead = seg[:len(seg) - len(stripped)]
        if stripped == "rtk" or stripped.startswith(("rtk ", "rtk\t")):
            seg = f"{lead}& {quoted}{stripped[3:]}"
        out.append(sep + seg)
    return "".join(out)


def _rewrite_cache_path() -> str:
    return os.path.join(tempfile.gettempdir(), "tdq-rtk-rewrite-cache.json")


def _rewrite_cache_sig(bin_path: str) -> str:
    """Build invalidation key from rtk binary path/mtime/size and config.toml mtime."""
    try:
        st = os.stat(bin_path)
        bin_sig = f"{os.path.abspath(bin_path)}:{st.st_size}:{st.st_mtime_ns}"
    except OSError:
        bin_sig = os.path.abspath(bin_path)
    try:
        cfg_st = os.stat(default_rtk_config_path())
        cfg_sig = f"{cfg_st.st_size}:{cfg_st.st_mtime_ns}"
    except OSError:
        cfg_sig = "nocfg"
    return f"{bin_sig}|{cfg_sig}"


def _read_rewrite_cache(sig: str, cmd: str) -> tuple[bool, str] | None:
    """Return (hit_rewritten_changed, raw_rewritten) on cache hit, else None."""
    try:
        with open(_rewrite_cache_path(), encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, dict) or data.get("sig") != sig:
            return None
        entries = data.get("entries")
        if isinstance(entries, dict) and cmd in entries:
            val = entries[cmd]
            if isinstance(val, str):
                return (val != cmd.strip() and bool(val)), val
    except (OSError, ValueError):
        pass
    return None


def _write_rewrite_cache(sig: str, cmd: str, rewritten: str) -> None:
    path = _rewrite_cache_path()
    entries: dict[str, str] = {}
    try:
        with open(path, encoding="utf-8") as fh:
            old = json.load(fh)
        if isinstance(old, dict) and old.get("sig") == sig and isinstance(old.get("entries"), dict):
            entries = dict(old["entries"])
    except (OSError, ValueError):
        pass
    entries.pop(cmd, None)
    entries[cmd] = rewritten
    if len(entries) > _REWRITE_CACHE_MAX:
        keep = list(entries.keys())[-_REWRITE_CACHE_MAX:]
        entries = {k: entries[k] for k in keep}
    _write_json_best_effort(path, {"sig": sig, "entries": entries})


def rewrite_command(
    cmd: str,
    cwd=None,
    role: str = "",
    timeout_s: float = 2.0,
    runner=None,
    probe_fn=None,
) -> tuple[str, bool, str]:
    """Rewrite a shell command via `rtk rewrite -- <cmd>`, failing open on error."""
    skip, reason = should_skip_rewrite(cmd, role=role)
    if skip:
        return cmd, False, reason
    probe = (probe_fn or probe_rtk)(cwd=cwd)
    if not probe.get("valid"):
        return cmd, False, probe.get("reason") or "rtk_unavailable"
    bin_path = probe.get("path") or locate_rtk_binary()
    if not bin_path:
        return cmd, False, "not_found"
    use_cache = runner is None and len(cmd) <= 512
    sig = _rewrite_cache_sig(bin_path) if use_cache else ""
    if use_cache:
        cached = _read_rewrite_cache(sig, cmd)
        if cached is not None:
            changed, cached_rew = cached
            if not changed:
                return cmd, False, "cached_unchanged"
            return _qualify_rtk_for_powershell(cached_rew, bin_path), True, "cached"
    exec_fn = runner or _default_runner
    try:
        proc = exec_fn(
            [bin_path, "rewrite", "--", cmd],
            capture_output=True,
            text=True,
            timeout=timeout_s,
            cwd=cwd,
        )
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        _log(f"rewrite_command: fail-open after {type(exc).__name__}")
        return cmd, False, f"rewrite_error:{type(exc).__name__}"
    rewritten = (proc.stdout or "").strip()
    if proc.returncode not in (0, 3) or not rewritten or rewritten == cmd.strip():
        if use_cache:
            _write_rewrite_cache(sig, cmd, cmd.strip())
        return cmd, False, f"unchanged_rc_{proc.returncode}"
    if use_cache:
        _write_rewrite_cache(sig, cmd, rewritten)
    final_cmd = _qualify_rtk_for_powershell(rewritten, bin_path)
    _log(f"rewrite_command: compressed ({len(cmd)} -> {len(final_cmd)} chars)")
    return final_cmd, True, "ok"


def default_rtk_config_path() -> str:
    """Return the platform-native user path for rtk config.toml."""
    if sys.platform.startswith("win"):
        home_roam = os.path.join(os.path.expanduser("~"), "AppData", "Roaming")
        appdata = os.environ.get("APPDATA") or home_roam
        return os.path.join(appdata, "rtk", "config.toml")
    if sys.platform == "darwin":
        return os.path.join(
            os.path.expanduser("~"),
            "Library",
            "Application Support",
            "rtk",
            "config.toml",
        )
    xdg = os.environ.get("XDG_CONFIG_HOME") or os.path.join(
        os.path.expanduser("~"), ".config"
    )
    return os.path.join(xdg, "rtk", "config.toml")


def _split_toml_sections(text: str) -> list[tuple[str, list[str]]]:
    sections: list[tuple[str, list[str]]] = [("", [])]
    header_re = re.compile(r"^\s*\[([A-Za-z0-9_.-]+)\]\s*(?:#.*)?$")
    for line in text.splitlines():
        match = header_re.match(line)
        if match:
            sections.append((match.group(1), [line]))
        else:
            sections[-1][1].append(line)
    return sections


def _upsert_toml_key(
    lines: list[str], key: str, value: str, overwrite: bool = True
) -> list[str]:
    key_re = re.compile(rf"^(\s*){re.escape(key)}\s*=.*$")
    for idx, line in enumerate(lines):
        if idx == 0 and line.lstrip().startswith("["):
            continue
        match = key_re.match(line)
        if match:
            if overwrite:
                lines[idx] = f"{match.group(1)}{key} = {value}"
            return lines
    insert_at = len(lines)
    while insert_at > 1 and not lines[insert_at - 1].strip():
        insert_at -= 1
    lines.insert(insert_at, f"{key} = {value}")
    return lines


def _merge_exclude_commands(lines: list[str]) -> list[str]:
    start_re = re.compile(r"^(\s*)exclude_commands\s*=\s*(.*)$")
    start_idx = next(
        (
            i for i, ln in enumerate(lines)
            if not (i == 0 and ln.lstrip().startswith("[")) and start_re.match(ln)
        ),
        None,
    )
    if start_idx is None:
        formatted = "[" + ", ".join(f'"{it}"' for it in REQUIRED_EXCLUDE_COMMANDS) + "]"
        return _upsert_toml_key(lines, "exclude_commands", formatted)
    end_idx, span = start_idx, lines[start_idx]
    while "[" in span and "]" not in span and end_idx + 1 < len(lines):
        end_idx += 1
        span += "\n" + lines[end_idx]
    existing: list[str] = []
    for q1, q2 in re.findall(r'"([^"]*)"|\'([^\']*)\'', span):
        item = q1 or q2
        if item and item not in existing:
            existing.append(item)
    for req in REQUIRED_EXCLUDE_COMMANDS:
        if req not in existing:
            existing.append(req)
    formatted = "[" + ", ".join(f'"{it}"' for it in existing) + "]"
    lines[start_idx:end_idx + 1] = [f"exclude_commands = {formatted}"]
    return lines


def _merge_rtk_toml(orig_text: str) -> str:
    sections = _split_toml_sections(orig_text)
    by_name = {name: lines for name, lines in sections if name}
    for sec_name, pairs in REQUIRED_RTK_CONFIG:
        if sec_name not in by_name:
            sec_lines = [f"[{sec_name}]"]
            sections.append((sec_name, sec_lines))
            by_name[sec_name] = sec_lines
        sec_lines = by_name[sec_name]
        for key, val in pairs:
            _upsert_toml_key(sec_lines, key, val)
        if sec_name == "display":
            # rtk v1.2.0 DisplayConfig lacks #[serde(default)] on colors & max_width
            _upsert_toml_key(sec_lines, "colors", "false", overwrite=False)
            _upsert_toml_key(sec_lines, "max_width", "120", overwrite=False)
        if sec_name == "hooks":
            _merge_exclude_commands(sec_lines)
    chunks = [
        "\n".join(lines).rstrip("\n")
        for name, lines in sections
        if name or any(ln.strip() for ln in lines)
    ]
    return "\n\n".join(chunks).rstrip() + "\n"


def _atomic_write_bytes(dest_path: str, data: bytes, mode: int | None = None) -> None:
    parent = os.path.dirname(os.path.abspath(dest_path))
    os.makedirs(parent, exist_ok=True)
    prefix = f".{os.path.basename(dest_path)}-"
    fd, tmp = tempfile.mkstemp(dir=parent, prefix=prefix, suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
        if mode is not None:
            os.chmod(tmp, mode)
        os.replace(tmp, dest_path)
    except OSError:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


def ensure_rtk_config(config_path=None) -> tuple[bool, str]:
    """Ensure rtk config.toml matches TDQ rules, backing up any existing file."""
    target = os.fspath(config_path) if config_path else default_rtk_config_path()
    try:
        if os.path.isfile(target):
            with open(target, encoding="utf-8") as fh:
                orig_text = fh.read()
        else:
            orig_text = ""
        merged = _merge_rtk_toml(orig_text)
        if orig_text == merged:
            return True, f"rtk config up to date: {target}"
        bak_path = target + ".truoc-tdq.bak"
        if os.path.isfile(target) and not os.path.exists(bak_path):
            shutil.copyfile(target, bak_path)
        _atomic_write_bytes(target, merged.encode("utf-8"))
        _log(f"ensure_rtk_config: updated {target}")
        return True, f"configured {target}"
    except OSError as exc:
        return False, f"config_write_failed:{type(exc).__name__}:{exc}"


def _default_fetcher(url: str) -> bytes:
    import urllib.request
    req = urllib.request.Request(url, headers={"User-Agent": "tdq-setup"})
    with urllib.request.urlopen(req, timeout=DEFAULT_TIMEOUT) as resp:  # noqa: S310
        return resp.read()


def _platform_arch(plat: str | None = None, mach: str | None = None) -> tuple[str, str]:
    import platform
    p = (plat or sys.platform).lower()
    os_kind = "windows" if p.startswith("win") else (
        "darwin" if p == "darwin" else "linux"
    )
    m = (mach or platform.machine()).lower()
    arch = "aarch64" if m in ("arm64", "aarch64") else "x86_64"
    return os_kind, arch


def _pick_rtk_asset(
    assets: dict[str, dict], edition: str, os_kind: str, arch: str
) -> dict | None:
    prefix = "rtk-oss" if edition == "oss" else "rtk"
    suffix_map = {
        "windows": (
            f"{prefix}-{arch}-pc-windows-msvc.zip",
            f"{prefix}-x86_64-pc-windows-msvc.zip",
        ),
        "darwin": (f"{prefix}-{arch}-apple-darwin.tar.gz",),
        "linux": (
            f"{prefix}-{arch}-unknown-linux-musl.tar.gz",
            f"{prefix}-{arch}-unknown-linux-gnu.tar.gz",
        ),
    }
    return next((assets[n] for n in suffix_map[os_kind] if n in assets), None)


def _pick_rg_asset(assets: dict[str, dict], os_kind: str, arch: str) -> dict | None:
    suffix_map = {
        "windows": (f"-{arch}-pc-windows-msvc.zip", "-x86_64-pc-windows-msvc.zip"),
        "darwin": (f"-{arch}-apple-darwin.tar.gz",),
        "linux": (
            f"-{arch}-unknown-linux-musl.tar.gz",
            f"-{arch}-unknown-linux-gnu.tar.gz",
        ),
    }
    for suf in suffix_map[os_kind]:
        for name, item in assets.items():
            if name.startswith("ripgrep-") and name.endswith(suf):
                return item
    return None


def _expected_sha256(asset: dict, assets: dict[str, dict], fetch_fn) -> str:
    name = asset.get("name", "")
    if "checksums.txt" in assets:
        url = assets["checksums.txt"]["browser_download_url"]
        txt = fetch_fn(url).decode("utf-8", "replace")
        for line in txt.splitlines():
            parts = line.split()
            if len(parts) >= 2 and os.path.basename(parts[-1].lstrip("*")) == name:
                return parts[0].lower()
    for sidecar in (f"{name}.sha256", f"{name}.sha256sum"):
        if sidecar in assets:
            url = assets[sidecar]["browser_download_url"]
            txt = fetch_fn(url).decode("utf-8", "replace")
            match = re.search(r"\b([0-9a-fA-F]{64})\b", txt)
            if match:
                return match.group(1).lower()
    digest = str(asset.get("digest") or "")
    if digest.lower().startswith("sha256:"):
        return digest.split(":", 1)[1].strip().lower()
    return ""


def _extract_binary(
    archive_bytes: bytes, asset_name: str, bin_name: str
) -> bytes | None:
    import io
    if asset_name.endswith(".zip"):
        import zipfile
        with zipfile.ZipFile(io.BytesIO(archive_bytes)) as zf:
            match = next(
                (n for n in zf.namelist() if os.path.basename(n) == bin_name), None
            )
            return zf.read(match) if match else None
    import tarfile
    with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode="r:gz") as tf:
        member = next(
            (
                m
                for m in tf.getmembers()
                if m.isfile() and os.path.basename(m.name) == bin_name
            ),
            None,
        )
        extracted = tf.extractfile(member) if member else None
        return extracted.read() if extracted else None


def _broadcast_env_change() -> None:
    if not sys.platform.startswith("win"):
        return
    try:
        import ctypes
        ctypes.windll.user32.SendMessageTimeoutW(
            0xFFFF, 0x001A, 0, "Environment", 0x0002, 2000, None
        )
    except (AttributeError, OSError):
        pass


def ensure_windows_user_path(bin_dir: str, reg_module=None, notify_fn=None) -> bool:
    """Append `bin_dir` to HKCU\\Environment\\Path on Windows if absent."""
    if reg_module is None:
        if not sys.platform.startswith("win"):
            return False
        import winreg
        reg_module = winreg
    norm_target = os.path.normcase(os.path.normpath(bin_dir))
    access = reg_module.KEY_READ | reg_module.KEY_SET_VALUE
    with reg_module.OpenKey(
        reg_module.HKEY_CURRENT_USER, "Environment", 0, access
    ) as key:
        try:
            current, reg_type = reg_module.QueryValueEx(key, "Path")
        except FileNotFoundError:
            current, reg_type = "", reg_module.REG_EXPAND_SZ
        entries = [
            os.path.normcase(os.path.normpath(p))
            for p in str(current).split(";")
            if p.strip()
        ]
        if norm_target in entries:
            return False
        sep = "" if (not current or current.endswith(";")) else ";"
        reg_module.SetValueEx(key, "Path", 0, reg_type, f"{current}{sep}{bin_dir}")
    (notify_fn or _broadcast_env_change)()
    _log(f"ensure_windows_user_path: added {bin_dir} to HKCU\\Environment\\Path")
    return True


def _install_release_binary(
    api_url: str, tool: str, pick_fn, target_bin_dir: str, os_kind: str, fetch_fn
) -> tuple[bool, str, str, str]:
    import hashlib
    rel = json.loads(fetch_fn(api_url))
    tag = str(rel.get("tag_name") or "?")
    assets = {a.get("name"): a for a in rel.get("assets") or [] if a.get("name")}
    asset = pick_fn(assets)
    if not asset:
        return False, tag, "", f"missing release asset for {tool} ({tag})"
    archive_bytes = fetch_fn(asset["browser_download_url"])
    expected = _expected_sha256(asset, assets, fetch_fn)
    actual = hashlib.sha256(archive_bytes).hexdigest().lower()
    if not expected or actual != expected:
        msg = f"SHA256 mismatch for {asset['name']} ({actual[:12]} != {expected[:12]})"
        return False, tag, "", msg
    bin_name = f"{tool}.exe" if os_kind == "windows" else tool
    binary = _extract_binary(archive_bytes, asset["name"], bin_name)
    if not binary:
        return False, tag, "", f"{asset['name']} missing {bin_name}"
    dest = os.path.join(target_bin_dir, bin_name)
    _atomic_write_bytes(dest, binary, mode=0o755)
    _log(f"install_{tool}: {tag} -> {dest} (sha256 {actual[:12]})")
    return True, tag, dest, "ok"


def _is_temp_path(path: str) -> bool:
    norm = os.path.normcase(os.path.abspath(path))
    temp_root = os.path.normcase(os.path.abspath(tempfile.gettempdir()))
    return norm == temp_root or norm.startswith(temp_root + os.sep)


def _install_both_tools(
    edition: str, target_bin: str, os_kind: str, arch: str, fetch_fn
) -> tuple[bool, dict]:
    import tarfile
    import zipfile
    try:
        ok_rtk, rtk_ver, rtk_dest, msg_rtk = _install_release_binary(
            RTK_RELEASE_API,
            "rtk",
            lambda a: _pick_rtk_asset(a, edition, os_kind, arch),
            target_bin,
            os_kind,
            fetch_fn,
        )
        if not ok_rtk:
            return False, {"reason": msg_rtk}
        ok_rg, rg_ver, rg_dest, msg_rg = _install_release_binary(
            RG_RELEASE_API, "rg", lambda a: _pick_rg_asset(a, os_kind, arch),
            target_bin, os_kind, fetch_fn,
        )
        if not ok_rg:
            return False, {"reason": msg_rg}
    except (OSError, ValueError, zipfile.BadZipFile, tarfile.TarError) as exc:
        return False, {"reason": f"install_error:{type(exc).__name__}:{exc}"}
    return True, {
        "rtk_path": rtk_dest,
        "rg_path": rg_dest,
        "rtk_version": rtk_ver,
        "rg_version": rg_ver,
    }


def install_rtk_and_rg(
    approve: bool = False,
    edition: str = "full",
    bin_dir=None,
    config_path=None,
    fetcher=None,
    update_path: bool = True,
) -> dict:
    """Install verified rtk and ripgrep releases and merge config.toml."""
    res = {
        "ok": False, "reason": "", "rtk_path": "", "rg_path": "",
        "rtk_version": "", "rg_version": "", "config_path": "", "path_updated": False,
    }
    if not approve:
        return {**res, "reason": "approval_required"}
    if fetcher is None and os.environ.get("TDQ_KHONG_CHAM_MAY") == "1":
        return {**res, "reason": "TDQ_KHONG_CHAM_MAY=1 - real machine install blocked"}
    if edition not in ("full", "oss"):
        return {**res, "reason": f"invalid_edition:{edition}"}
    target_bin = os.fspath(bin_dir) if bin_dir else _local_bin_dir()
    os_kind, arch = _platform_arch()
    ok_bins, info = _install_both_tools(
        edition, target_bin, os_kind, arch, fetcher or _default_fetcher
    )
    if not ok_bins:
        return {**res, **info}
    cfg_target = os.fspath(config_path) if config_path else default_rtk_config_path()
    cfg_ok, cfg_msg = ensure_rtk_config(cfg_target)
    if not cfg_ok:
        return {**res, "reason": cfg_msg}
    can_update_path = (
        update_path
        and sys.platform.startswith("win")
        and os.environ.get("TDQ_KHONG_CHAM_MAY") != "1"
        and not _is_temp_path(target_bin)
    )
    path_updated = ensure_windows_user_path(target_bin) if can_update_path else False
    return {
        **res,
        **info,
        "ok": True,
        "reason": "ok",
        "config_path": cfg_target,
        "path_updated": path_updated,
    }


def _default_prefs_path():
    from pathlib import Path
    return Path.home() / ".gemini" / "config" / "tdq-rtk-prefs.json"


def is_prompt_muted(prefs_path=None) -> bool:
    """Return True when the user muted SessionStart RTK setup reminders."""
    from pathlib import Path
    target = Path(prefs_path) if prefs_path else _default_prefs_path()
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
        return bool(isinstance(data, dict) and data.get("mute_prompt", False))
    except (OSError, ValueError):
        return False


def set_prompt_muted(muted: bool, prefs_path=None):
    """Persist the user's mute preference for SessionStart RTK setup."""
    from datetime import datetime
    from pathlib import Path
    target = Path(prefs_path) if prefs_path else _default_prefs_path()
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            data = {}
    except (OSError, ValueError):
        data = {}
    data["mute_prompt"] = bool(muted)
    if muted:
        data["muted_at"] = datetime.now().isoformat(timespec="seconds")
    else:
        data.pop("muted_at", None)
    payload = (json.dumps(data, indent=2) + "\n").encode("utf-8")
    _atomic_write_bytes(str(target), payload)
    _log(f"set_prompt_muted: {bool(muted)} -> {target}")
    return target
