#!/usr/bin/env python3
"""Safe installer for the compiled plugins/tdq-workflow-agy Antigravity plugin."""
import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
ROOT_DIR = TOOLS_DIR.parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))
from patches.common_utils import import_rtk_integration, sync_tree_inplace

DEFAULT_SRC = ROOT_DIR / "plugins" / "tdq-workflow-agy"
DEFAULT_DST = Path.home() / ".gemini" / "config" / "plugins" / "tdq-workflow-agy"


def _log(message: str) -> None:
    """Emit an ISO-timestamped diagnostic line to stderr unless TDQ_LOG=0."""
    if os.environ.get("TDQ_LOG", "1") != "0":
        stamp = datetime.now().isoformat(timespec="seconds")
        print(f"[{stamp}] install_agy_plugin: {message}", file=sys.stderr)


def probe_python_path_command(timeout: float = 5.0) -> dict:
    """Verify `python -X utf8` on PATH executes real Python 3 rather than a WindowsApps stub."""
    resolved = shutil.which("python")
    kw = {"capture_output": True, "text": True, "timeout": timeout}
    if os.name == "nt":
        kw["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
    err_note = ""
    try:
        proc = subprocess.run(
            ["python", "-X", "utf8", "-c", "pass"], check=False, **kw
        )
        rc = proc.returncode
    except (OSError, subprocess.SubprocessError) as exc:
        rc = -1
        err_note = str(exc)

    is_windowsapps_stub = ("windowsapps" in (resolved or "").lower()) or (rc != 0)
    ok = (rc == 0) and not is_windowsapps_stub
    warning = ""
    if not ok:
        detail = f" ({err_note})" if err_note else ""
        warning = (
            f"python -X utf8 probe failed (resolved={resolved or 'not found'}, rc={rc}){detail}. "
            "Place a real Python 3 directory above WindowsApps on PATH or disable the "
            "Microsoft Store App Execution Alias for python.exe; fallback: py -3 -X utf8."
        )
        _log(f"WARNING: {warning}")
    else:
        _log(f"python probe ok ({resolved or 'python'})")
    return {
        "ok": ok,
        "command": "python -X utf8",
        "resolved": resolved,
        "is_windowsapps_stub": is_windowsapps_stub,
        "returncode": rc,
        "warning": warning,
        "fallback": "py -3 -X utf8",
    }


def _unix_target_binary_name() -> str:
    """Return compiled tdq-dispatch binary filename for current POSIX platform/arch."""
    if sys.platform == "darwin":
        import platform

        arch = platform.machine().lower()
        return "tdq-dispatch-darwin-arm64" if arch in ("arm64", "aarch64") else "tdq-dispatch-darwin-x64"
    return "tdq-dispatch-linux-x86_64"


def _chmod_executable_scripts(scripts_dir: Path) -> None:
    """Mark .mjs and .sh scripts executable on POSIX hosts."""
    for pattern in ("*.mjs", "*.sh"):
        for script_path in scripts_dir.glob(pattern):
            try:
                script_path.chmod(0o755)
            except OSError:
                pass


def _prepare_unix_binary(bin_dir: Path) -> str | None:
    """Copy arch-specific tdq-dispatch binary into bin/tdq-dispatch and chmod 0755."""
    target_name = _unix_target_binary_name()
    unix_bin = bin_dir / "tdq-dispatch"
    specific_bin = bin_dir / target_name
    if specific_bin.is_file() and not unix_bin.exists():
        shutil.copy2(specific_bin, unix_bin)
    if not unix_bin.is_file():
        return None
    try:
        unix_bin.chmod(0o755)
    except OSError:
        pass
    return str(unix_bin)


def _rewrite_hooks_python_fallback(hooks_file: Path) -> None:
    """Rewrite hooks.json commands to invoke dispatch.py directly when binary/Node absent."""
    py_cmd = (
        "py -3 -X utf8 hooks/scripts/dispatch.py --event"
        if os.name == "nt"
        else "python3 -X utf8 hooks/scripts/dispatch.py --event"
    )
    new_content = hooks_file.read_text(encoding="utf-8")
    for old_prefix in (
        "node scripts/tdq_hook_launcher.mjs --event",
        "bin\\tdq-dispatch.exe --event",
        "./bin/tdq-dispatch --event",
    ):
        new_content = new_content.replace(old_prefix, py_cmd)
    hooks_file.write_text(new_content, encoding="utf-8")


def _ensure_binary_executable_and_hooks(dst: Path) -> dict:
    """Ensure binaries/launchers are executable on POSIX and fall back cleanly when missing."""
    bin_dir = dst / "bin"
    hooks_file = dst / "hooks.json"
    status = {"engine": "rust", "binary": None}

    if os.name == "nt":
        exe = bin_dir / "tdq-dispatch.exe"
        if exe.is_file():
            status["binary"] = str(exe)
    else:
        _chmod_executable_scripts(dst / "scripts")
        status["binary"] = _prepare_unix_binary(bin_dir)

    has_node = bool(shutil.which("node")) and (dst / "scripts" / "tdq_hook_launcher.mjs").is_file()
    if status["binary"] or has_node:
        if not status["binary"]:
            status["engine"] = "node_python_fallback"
        return status

    if hooks_file.is_file():
        _rewrite_hooks_python_fallback(hooks_file)
        status["engine"] = "python_fallback"
    return status


def _resolve_backup_base_dir(data_dir: Path | None = None) -> Path:
    """Resolve persistent plugin data dir for backups outside plugins/."""
    if data_dir is not None:
        return Path(data_dir)
    state_dir = os.environ.get("TDQ_SETUP_STATE_DIR", "").strip()
    if state_dir:
        return Path(state_dir).expanduser()
    if os.environ.get("TDQ_KHONG_CHAM_MAY") != "1":
        plugin_data = os.environ.get("PLUGIN_DATA", "").strip()
        if plugin_data:
            return Path(plugin_data).expanduser()
    env_home = os.environ.get("HOME") or os.environ.get("USERPROFILE")
    home = Path(env_home).expanduser() if env_home else Path.home()
    return home / ".gemini" / "antigravity" / "plugin_data" / "tdq-workflow-agy"


def backup_plugin_dir(dst: Path, data_dir: Path | None = None) -> Path | None:
    """Back up an existing plugin dir into ${PLUGIN_DATA}/backups/<timestamp>/."""
    dst_path = Path(dst)
    if not dst_path.is_dir() or not any(dst_path.iterdir()):
        return None
    base_dir = _resolve_backup_base_dir(data_dir=data_dir)
    backup_root = base_dir / "backups"
    resolved_dst = dst_path.resolve()
    resolved_parent = dst_path.parent.resolve()
    resolved_root = backup_root.resolve()
    if resolved_root == resolved_dst or resolved_dst in resolved_root.parents:
        raise ValueError(f"Backup path {backup_root} must stay outside {dst_path}")
    if dst_path.parent.name == "plugins" and (
        resolved_root == resolved_parent or resolved_parent in resolved_root.parents
    ):
        raise ValueError(
            f"Backup path {backup_root} must stay outside plugins dir {dst_path.parent}"
        )
    backup_root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    target = backup_root / stamp
    if target.exists():
        target = backup_root / f"{stamp}-{datetime.now().strftime('%f')}"
    shutil.copytree(dst_path, target)
    _log(f"backed up plugin {dst_path} -> {target}")
    return target


def _copy_plugin(src: Path, dst: Path) -> int:
    count = sync_tree_inplace(src, dst)
    _ensure_binary_executable_and_hooks(dst)
    return count


def _sync_local_mcp(dst: Path) -> dict:
    """Merge local non-repo lsp args/env into installed mcp_config.json."""
    mcp_file = dst / "mcp_config.json"
    cfg = json.loads(mcp_file.read_text(encoding="utf-8"))
    claude_json = Path.home() / ".claude.json"
    synced = []
    if claude_json.is_file():
        try:
            cdata = json.loads(claude_json.read_text(encoding="utf-8"))
            cservers = cdata.get("mcpServers") or {}
            lsp = cservers.get("lsp")
            if isinstance(lsp, dict) and lsp.get("command"):
                cfg["mcpServers"]["lsp"]["command"] = lsp["command"]
                if isinstance(lsp.get("args"), list):
                    cfg["mcpServers"]["lsp"]["args"] = [
                        str(a) for a in lsp["args"]
                    ]
                synced.append("lsp")
        except (OSError, ValueError):
            pass
    mcp_file.write_text(
        json.dumps(cfg, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"synced_servers": synced}


def _handle_rtk(
    src: Path, with_rtk: bool, skip_rtk: bool, dry_run: bool
) -> tuple[int, dict]:
    """Probe rtk/rg status and install only when --with-rtk is explicitly passed."""
    if skip_rtk:
        _log("RTK/rg check skipped (--skip-rtk)")
        return 0, {
            "present": False, "valid": False, "rg_present": False,
            "version": "", "installed": False, "skipped": True,
            "reason": "skip_rtk",
        }
    rtk_mod = import_rtk_integration(ROOT_DIR, src)
    probe = rtk_mod.probe_rtk(cwd=str(ROOT_DIR))
    rg_bin = rtk_mod.locate_rg_binary()
    valid = bool(probe.get("valid"))
    rg_present = bool(rg_bin)
    status = {
        "present": valid or bool(probe.get("path")),
        "valid": valid,
        "rg_present": rg_present,
        "version": str(probe.get("version") or ""),
        "installed": False,
        "skipped": False,
        "reason": str(probe.get("reason") or ""),
    }
    if valid and rg_present:
        if not dry_run:
            rtk_mod.ensure_rtk_config()
        _log(f"rtk ({status['version']}) and rg ready")
        return 0, status
    if dry_run:
        status["would_install"] = bool(with_rtk)
        return 0, status
    if not with_rtk:
        _log("rtk/rg missing; skipping non-interactive install without --with-rtk")
        return 0, status
    res = rtk_mod.install_rtk_and_rg(approve=True)
    if res.get("ok"):
        status.update({
            "present": True, "valid": True, "rg_present": True,
            "version": str(res.get("rtk_version") or status["version"]),
            "installed": True, "reason": "installed",
        })
        _log(f"installed rtk ({status['version']}) and rg")
        return 0, status
    status["reason"] = str(res.get("reason") or "install_failed")
    _log(f"rtk/rg install failed: {status['reason']}")
    return 1, status


def _import_caveman_config(src: Path):
    """Import caveman_config from repo scripts or compiled plugin scripts."""
    for cand in (str(ROOT_DIR / "scripts"), str(Path(src) / "scripts")):
        if cand not in sys.path and os.path.isdir(cand):
            sys.path.insert(0, cand)
    import caveman_config

    return caveman_config


def _caveman_dry_run_status(
    probe: dict, with_caveman: bool, without_caveman: bool
) -> dict:
    """Build read-only Caveman status summary for --dry-run mode."""
    enabled = bool(probe.get("enabled"))
    wrapped = list(probe.get("mcp_wrapped_servers") or [])
    if without_caveman:
        return {
            "enabled": enabled,
            "active": bool(probe.get("active")),
            "wrapped_servers": wrapped,
            "skipped": False,
            "would_disable": True,
            "would_unwrap": bool(wrapped),
            "reason": "dry_run_without_caveman",
        }
    would_wrap = bool(with_caveman or enabled)
    return {
        "enabled": enabled,
        "active": bool(probe.get("active")),
        "wrapped_servers": wrapped,
        "skipped": False,
        "would_enable": bool(with_caveman and not enabled),
        "would_wrap": would_wrap,
        "reason": "dry_run_with_caveman" if with_caveman else "dry_run_probe",
    }


def _apply_caveman_wrap(
    caveman_mod, src: Path, dst: Path, reason: str
) -> dict:
    """Wrap installed mcp_config.json and persist enabled Caveman state."""
    mcp_file = dst / "mcp_config.json"
    proxy_script = dst / "scripts" / caveman_mod.PROXY_SCRIPT_NAME
    if not proxy_script.is_file():
        src_proxy = src / "scripts" / caveman_mod.PROXY_SCRIPT_NAME
        if src_proxy.is_file():
            proxy_script = src_proxy
    if mcp_file.is_file():
        caveman_mod.wrap_mcp_config(mcp_file, proxy_script)
    after = caveman_mod.probe_caveman(plugin_root=dst)
    servers = list(after.get("mcp_wrapped_servers") or [])
    caveman_mod.enable_caveman(approve=True, wrapped_servers=servers)
    _log(f"caveman active ({reason}): wrapped={servers}")
    return {
        "enabled": True,
        "active": bool(servers),
        "wrapped_servers": servers,
        "skipped": False,
        "reason": reason,
    }


def _handle_caveman(
    src: Path,
    dst: Path,
    with_caveman: bool,
    without_caveman: bool,
    skip_caveman: bool,
    dry_run: bool,
) -> tuple[int, dict]:
    """Probe or apply opt-in Caveman MCP wrapping without silent activation."""
    if skip_caveman:
        _log("Caveman MCP wrap check skipped (--skip-caveman)")
        return 0, {
            "enabled": False,
            "active": False,
            "wrapped_servers": [],
            "skipped": True,
            "reason": "skip_caveman",
        }
    caveman_mod = _import_caveman_config(src)
    probe_root = dst if dst.is_dir() else src
    probe = caveman_mod.probe_caveman(plugin_root=probe_root)
    if dry_run:
        return 0, _caveman_dry_run_status(probe, with_caveman, without_caveman)
    if without_caveman:
        caveman_mod.unwrap_mcp_config(dst / "mcp_config.json")
        caveman_mod.disable_caveman()
        _log("caveman disabled and mcp_config.json unwrapped (--without-caveman)")
        return 0, {
            "enabled": False,
            "active": False,
            "wrapped_servers": [],
            "skipped": False,
            "reason": "disabled",
        }
    if with_caveman:
        return 0, _apply_caveman_wrap(caveman_mod, src, dst, "with_caveman")
    if probe.get("enabled"):
        return 0, _apply_caveman_wrap(caveman_mod, src, dst, "preserved_opt_in")
    _log("caveman opt-in not enabled; keeping mcp_config.json unwrapped")
    return 0, {
        "enabled": False,
        "active": False,
        "wrapped_servers": [],
        "skipped": False,
        "reason": "opt_in_required",
    }


def parse_args(argv=None) -> argparse.Namespace:
    """Parse CLI arguments for the Antigravity native plugin installer."""
    ap = argparse.ArgumentParser(
        description="Install tdq-workflow-agy native Antigravity plugin."
    )
    ap.add_argument("--src", type=Path, default=DEFAULT_SRC)
    ap.add_argument("--target", type=Path, default=DEFAULT_DST)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--sync-local-mcp", action="store_true")
    ap.add_argument("--with-rtk", action="store_true")
    ap.add_argument("--skip-rtk", action="store_true")
    ap.add_argument("--with-caveman", action="store_true")
    ap.add_argument("--without-caveman", action="store_true")
    ap.add_argument("--skip-caveman", action="store_true")
    ap.add_argument("--backup", action="store_true")
    return ap.parse_args(argv)


def _run_dry_run(args: argparse.Namespace, python_probe: dict) -> int:
    """Execute read-only dry-run probes and print JSON summary."""
    rtk_rc, rtk_status = _handle_rtk(
        args.src, args.with_rtk, args.skip_rtk, dry_run=True
    )
    caveman_rc, caveman_status = _handle_caveman(
        args.src,
        args.target,
        args.with_caveman,
        args.without_caveman,
        args.skip_caveman,
        dry_run=True,
    )
    print(json.dumps({
        "dry_run": True,
        "src": str(args.src),
        "target": str(args.target),
        "python_probe": python_probe,
        "rtk": rtk_status,
        "caveman": caveman_status,
    }))
    return rtk_rc or caveman_rc


def main(argv=None) -> int:
    """Install plugin and print JSON status including optional RTK & Caveman."""
    args = parse_args(argv)
    if not (args.src / "plugin.json").is_file():
        raise SystemExit(
            f"Compiled plugin missing at {args.src}; run build_agy_plugin.py first."
        )
    python_probe = probe_python_path_command()
    if args.dry_run:
        return _run_dry_run(args, python_probe)
    should_backup = args.backup or (
        os.environ.get("TDQ_KHONG_CHAM_MAY") != "1"
        and args.target.resolve() == DEFAULT_DST.resolve()
    )
    backup_path = backup_plugin_dir(args.target) if should_backup else None
    files_copied = _copy_plugin(args.src, args.target)
    mcp_res = (
        _sync_local_mcp(args.target)
        if args.sync_local_mcp
        else {"synced_servers": []}
    )
    caveman_rc, caveman_status = _handle_caveman(
        args.src,
        args.target,
        args.with_caveman,
        args.without_caveman,
        args.skip_caveman,
        dry_run=False,
    )
    rtk_rc, rtk_status = _handle_rtk(
        args.src, args.with_rtk, args.skip_rtk, dry_run=False
    )
    payload = {
        "installed_to": str(args.target),
        "files": files_copied,
        **mcp_res,
        "python_probe": python_probe,
        "rtk": rtk_status,
        "caveman": caveman_status,
    }
    if backup_path is not None:
        payload["backup_path"] = str(backup_path)
    print(json.dumps(payload))
    return rtk_rc or caveman_rc


if __name__ == "__main__":
    raise SystemExit(main())
