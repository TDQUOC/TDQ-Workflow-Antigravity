#!/usr/bin/env python3
"""TDQ-Workflow Antigravity User-Level Plugin Installer (`tdq-workflow-agy`).

Installs the TDQ-Workflow native plugin directly into the user-level configuration directory:
  Windows: %USERPROFILE%\\.gemini\\config\\plugins\\tdq-workflow-agy
  macOS/Linux: ~/.gemini/config/plugins/tdq-workflow-agy

Usage:
  python install.py
  python install.py --update
  python install.py --dry-run
"""
import argparse
import json
import os
import platform
import shutil
import stat
import subprocess
import sys
from pathlib import Path


PLUGIN_NAME = "tdq-workflow-agy"
ROOT_DIR = Path(__file__).resolve().parent
PLUGIN_SRC = ROOT_DIR / "plugins" / PLUGIN_NAME
USER_PLUGINS_DIR = Path.home() / ".gemini" / "config" / "plugins"
TARGET_DIR = USER_PLUGINS_DIR / PLUGIN_NAME


def _copy_tree(src: Path, dst: Path) -> int:
    """Sync plugin files in-place without removing dst root (avoids WinError 32)."""
    dst.mkdir(parents=True, exist_ok=True)
    expected_files, expected_dirs, count = set(), set(), 0
    for root, dirs, files in os.walk(src):
        rel_root = Path(root).relative_to(src)
        if rel_root != Path("."):
            expected_dirs.add(rel_root)
        out_dir = dst / rel_root
        out_dir.mkdir(parents=True, exist_ok=True)
        for d in dirs:
            expected_dirs.add(rel_root / d if rel_root != Path(".") else Path(d))
        for name in files:
            rel_file = rel_root / name if rel_root != Path(".") else Path(name)
            expected_files.add(rel_file)
            target_file = out_dir / name
            if target_file.exists():
                os.chmod(target_file, stat.S_IWRITE)
            shutil.copy2(Path(root) / name, target_file)
            count += 1
    for root, _dirs, files in os.walk(dst, topdown=False):
        rel_root = Path(root).relative_to(dst)
        for name in files:
            rel_file = rel_root / name if rel_root != Path(".") else Path(name)
            if rel_file not in expected_files:
                stale = Path(root) / name
                os.chmod(stale, stat.S_IWRITE)
                stale.unlink()
        if rel_root != Path(".") and rel_root not in expected_dirs:
            try:
                os.chmod(Path(root), stat.S_IWRITE)
                Path(root).rmdir()
            except PermissionError:
                pass
    return count


def _adjust_hooks_for_platform(installed_dir: Path) -> None:
    """Ensure hooks.json uses python3 on POSIX and py -3 on Windows."""
    hooks_file = installed_dir / "hooks.json"
    if not hooks_file.is_file():
        return
    text = hooks_file.read_text(encoding="utf-8").replace("\r\n", "\n")
    if platform.system() == "Windows":
        text = text.replace("python3 -X utf8", "py -3 -X utf8")
        text = text.replace("python3 ", "py -3 ")
    else:
        text = text.replace("py -3 -X utf8", "python3 -X utf8")
        text = text.replace("py -3 ", "python3 ")
    with open(hooks_file, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def _find_agy_cli() -> str:
    if platform.system() == "Windows":
        found = shutil.which("agy.EXE") or shutil.which("agy.exe") or shutil.which("agy")
        if found:
            return found
        fallback = Path.home() / "AppData" / "Local" / "Programs" / "Antigravity" / "bin" / "agy.EXE"
        if fallback.is_file():
            return str(fallback)
        return "agy.exe"
    return shutil.which("agy") or "agy"


def _run_agy_command(*args) -> subprocess.CompletedProcess:
    agy_cmd = _find_agy_cli()
    kw = {"capture_output": True, "text": True, "encoding": "utf-8", "errors": "replace", "timeout": 30}
    if platform.system() == "Windows":
        kw["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
    try:
        return subprocess.run([agy_cmd, *args], **kw)
    except FileNotFoundError:
        return subprocess.CompletedProcess([agy_cmd, *args], returncode=127, stdout="", stderr="agy CLI not found on PATH")


def _git_pull_ff_only(repo_root: Path) -> bool:
    print("\n0. Pulling latest updates from git remote (git pull --ff-only)...")
    kw = {"cwd": str(repo_root), "capture_output": True, "text": True, "encoding": "utf-8", "errors": "replace", "timeout": 60}
    if platform.system() == "Windows":
        kw["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
    try:
        proc = subprocess.run(["git", "-C", str(repo_root), "pull", "--ff-only"], **kw)
    except FileNotFoundError:
        print("   [ERROR] git CLI not found on PATH.", file=sys.stderr)
        return False
    if proc.returncode != 0:
        print(f"   [ERROR] git pull --ff-only failed ({proc.returncode}): {proc.stderr.strip() or proc.stdout.strip()}", file=sys.stderr)
        return False
    print(f"   [OK] {proc.stdout.strip() or 'Repository is up to date.'}")
    return True


def _prompt_rtk_install(args, stdin_tty=None, ask_fn=input) -> bool:
    """Return True when --with-rtk is passed or interactive user approves."""
    if getattr(args, "with_rtk", False):
        return True
    is_tty = bool(stdin_tty) if stdin_tty is not None else bool(sys.stdin.isatty())
    if not is_tty:
        return False
    print("\n   Optional token-saving tools missing (rtk + rg).")
    print(
        "   Sources: github.com/rtk-ai/rtk & BurntSushi/ripgrep"
        " (SHA256-verified -> ~/.local/bin)"
    )
    try:
        ans = ask_fn("   Install rtk + rg user-level now? [y/N]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        return False
    return ans in ("y", "yes")


def _handle_rtk_trigger(
    args, src: Path | None = None, stdin_tty=None, ask_fn=input
) -> int:
    """Detect rtk/rg after install and ask consent before user-level setup."""
    tools_dir = str(ROOT_DIR / "tools")
    if tools_dir not in sys.path:
        sys.path.insert(0, tools_dir)
    from patches.common_utils import import_rtk_integration

    rtk_mod = import_rtk_integration(ROOT_DIR, src)
    if getattr(args, "skip_rtk", False):
        print("   [NOTE] RTK/rg trigger skipped (--skip-rtk).")
        return 0
    st_rtk = rtk_mod.probe_rtk(cwd=str(ROOT_DIR))
    rg_bin = rtk_mod.locate_rg_binary()
    if st_rtk.get("valid") and rg_bin:
        if not getattr(args, "dry_run", False):
            rtk_mod.ensure_rtk_config()
        print(f"   [OK] rtk ({st_rtk.get('version')}) & rg ready.")
        return 0
    if getattr(args, "dry_run", False):
        msg = (
            "Would install SHA256-verified rtk + rg into ~/.local/bin."
            if getattr(args, "with_rtk", False)
            else "Missing rtk/rg detected; run with --with-rtk or approve prompt."
        )
        print(f"[DRY-RUN] {msg}")
        return 0
    if not _prompt_rtk_install(args, stdin_tty=stdin_tty, ask_fn=ask_fn):
        print(
            "   [NOTE] rtk/rg not installed. Install with permission anytime:"
            " py -3 install.py --with-rtk"
        )
        return 0
    res = rtk_mod.install_rtk_and_rg(approve=True)
    if res.get("ok"):
        print(
            f"   [OK] Installed rtk ({res.get('rtk_version')})"
            f" & rg ({res.get('rg_version')})."
        )
        return 0
    print(f"   [WARN] rtk/rg install failed: {res.get('reason')}", file=sys.stderr)
    return 1 if getattr(args, "with_rtk", False) else 0


def _import_caveman_config(src: Path | None = None):
    """Import caveman_config from repo scripts or compiled plugin scripts."""
    candidates = [str(ROOT_DIR / "scripts")]
    if src is not None:
        candidates.append(str(Path(src) / "scripts"))
    for cand in candidates:
        if cand not in sys.path and os.path.isdir(cand):
            sys.path.insert(0, cand)
    import caveman_config

    return caveman_config


def _prompt_caveman_enable(args, stdin_tty=None, ask_fn=input) -> bool:
    """Return True when --with-caveman is passed or interactive user approves."""
    if getattr(args, "with_caveman", False):
        return True
    is_tty = bool(stdin_tty) if stdin_tty is not None else bool(sys.stdin.isatty())
    if not is_tty:
        return False
    print("\n   Optional Caveman MCP schema shrink proxy (opt-in).")
    print("   Wraps lsp, chrome-devtools, tavily-primary via tdq_mcp_shrink.py (~/.tdq/caveman.json).")
    try:
        ans = ask_fn("   Enable Caveman MCP schema shrink now? [y/N]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        return False
    return ans in ("y", "yes")


def _wrap_target_mcp(caveman_mod, src: Path | None, target: Path | None) -> list[str]:
    """Wrap installed target mcp_config.json if present; return wrapped server names."""
    if target is None:
        return []
    mcp_file = Path(target) / "mcp_config.json"
    if not mcp_file.is_file():
        return []
    proxy_script = Path(target) / "scripts" / caveman_mod.PROXY_SCRIPT_NAME
    if not proxy_script.is_file() and src is not None:
        src_proxy = Path(src) / "scripts" / caveman_mod.PROXY_SCRIPT_NAME
        if src_proxy.is_file():
            proxy_script = src_proxy
    caveman_mod.wrap_mcp_config(mcp_file, proxy_script)
    after = caveman_mod.probe_caveman(plugin_root=Path(target))
    return list(after.get("mcp_wrapped_servers") or [])


def _handle_caveman_trigger(
    args,
    src: Path | None = None,
    target: Path | None = None,
    stdin_tty=None,
    ask_fn=input,
) -> int:
    """Detect Caveman opt-in state and wrap MCP config only with explicit consent."""
    if getattr(args, "skip_caveman", False):
        print("   [NOTE] Caveman MCP shrink trigger skipped (--skip-caveman).")
        return 0
    caveman_mod = _import_caveman_config(src)
    dry_run = bool(getattr(args, "dry_run", False))
    probe_root = target if (target is not None and not dry_run) else src
    probe = caveman_mod.probe_caveman(plugin_root=probe_root)
    if probe.get("enabled"):
        if dry_run:
            print("[DRY-RUN] Caveman MCP shrink already enabled; would wrap installed mcp_config.json.")
            return 0
        wrapped = _wrap_target_mcp(caveman_mod, src, target)
        caveman_mod.enable_caveman(approve=True, wrapped_servers=wrapped)
        print(f"   [OK] Caveman MCP shrink active (wrapped: {', '.join(wrapped) or 'none'}).")
        return 0
    if dry_run:
        msg = (
            "Would enable Caveman opt-in (~/.tdq/caveman.json) and wrap mcp_config.json."
            if getattr(args, "with_caveman", False)
            else "Caveman MCP shrink is opt-in (disabled); run with --with-caveman or approve prompt."
        )
        print(f"[DRY-RUN] {msg}")
        return 0
    if not _prompt_caveman_enable(args, stdin_tty=stdin_tty, ask_fn=ask_fn):
        print(
            "   [NOTE] Caveman MCP shrink left disabled (opt-in). Enable anytime:"
            " py -3 scripts/tdq_setup.py --with-caveman"
        )
        return 0
    wrapped = _wrap_target_mcp(caveman_mod, src, target)
    caveman_mod.enable_caveman(approve=True, wrapped_servers=wrapped)
    print(f"   [OK] Caveman MCP shrink enabled (wrapped: {', '.join(wrapped) or 'none'}).")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=f"Install {PLUGIN_NAME} native plugin to user-level Antigravity.")
    parser.add_argument("--src", type=Path, default=PLUGIN_SRC, help=f"Source plugin directory (default: ./plugins/{PLUGIN_NAME})")
    parser.add_argument("--target", type=Path, default=TARGET_DIR, help=f"Target user-level directory (default: ~/.gemini/config/plugins/{PLUGIN_NAME})")
    parser.add_argument("--dry-run", action="store_true", help="Simulate installation without writing to disk")
    parser.add_argument("--no-enable", action="store_true", help="Do not automatically enable the plugin after install")
    parser.add_argument("--update", action="store_true", help="Run 'git pull --ff-only' in the repository before reinstalling")
    parser.add_argument(
        "--with-rtk",
        action="store_true",
        help="Download and install SHA256-verified rtk + rg into ~/.local/bin",
    )
    parser.add_argument(
        "--skip-rtk",
        action="store_true",
        help="Skip rtk + rg installation check/prompt",
    )
    parser.add_argument(
        "--with-caveman",
        action="store_true",
        help="Enable Caveman MCP schema shrink proxy (opt-in -> ~/.tdq/caveman.json)",
    )
    parser.add_argument(
        "--skip-caveman",
        action="store_true",
        help="Skip Caveman MCP schema shrink check/prompt",
    )
    args = parser.parse_args()

    if args.update and not args.dry_run:
        if not _git_pull_ff_only(ROOT_DIR):
            return 1

    src = args.src.resolve()
    target = args.target.resolve()

    if not (src / "plugin.json").is_file():
        print(f"[ERROR] Plugin package not found at: {src}", file=sys.stderr)
        print("Please ensure you run this installer from the repository root.", file=sys.stderr)
        return 1

    print("==================================================================")
    print(f"TDQ-Workflow Antigravity User-Level Installer ({PLUGIN_NAME})")
    print("==================================================================")
    print(f"Source Plugin: {src}")
    print(f"Target (User-Level): {target}")
    print(f"Operating System: {platform.system()} ({platform.release()})")

    if args.dry_run:
        if args.update:
            print("[DRY-RUN] Would run: git -C <repo> pull --ff-only")
        _handle_rtk_trigger(args, src=src)
        _handle_caveman_trigger(args, src=src, target=target)
        print("[DRY-RUN] Verification complete. No files were copied.")
        return 0

    print("\n1. Installing plugin files into user-level directory...")
    file_count = _copy_tree(src, target)
    print(f"   [OK] {file_count} files installed to {target}")

    print("\n2. Adjusting runtime commands for current operating system...")
    _adjust_hooks_for_platform(target)
    print("   [OK] Runtime hook commands configured.")

    print("\n3. Validating installed user-level plugin with Antigravity validator...")
    val_proc = _run_agy_command("plugin", "validate", str(target), "--strict", "--json")
    if val_proc.returncode == 0:
        try:
            val_data = json.loads(val_proc.stdout)
            comps = val_data.get("components", {})
            print("   [OK] Validation passed: 0 errors, 0 warnings.")
            print(f"        Components: {comps.get('skills', 0)} skills, {comps.get('agents', 0)} agents, "
                  f"{comps.get('rules', 0)} rules, {comps.get('mcpServers', 0)} MCP servers, {comps.get('hooks', 0)} hooks.")
        except Exception:
            print("   [OK] agy plugin validate completed.")
    else:
        print(f"   [NOTE] agy CLI check skipped or returned {val_proc.returncode} ({val_proc.stderr.strip()}).")

    if not args.no_enable:
        print(f"\n4. Enabling plugin '{PLUGIN_NAME}' in Antigravity...")
        enable_proc = _run_agy_command("plugin", "enable", PLUGIN_NAME)
        if enable_proc.returncode == 0:
            print(f"   [OK] Plugin '{PLUGIN_NAME}' is now ENABLED.")
        else:
            print(f"   [NOTE] Could not run 'agy plugin enable {PLUGIN_NAME}' ({enable_proc.stderr.strip()}).")
            print(f"          You can enable it manually in Antigravity UI or with: agy plugin enable {PLUGIN_NAME}")

    print("\n5. Checking optional token-saving tools (rtk + rg)...")
    rtk_rc = _handle_rtk_trigger(args, src=src)

    print("\n6. Checking optional Caveman MCP schema shrink (opt-in)...")
    caveman_rc = _handle_caveman_trigger(args, src=src, target=target)

    print("\n==================================================================")
    print("INSTALLATION SUCCESSFUL!")
    print("==================================================================")
    print(f"The {PLUGIN_NAME} plugin is now installed at user-level:")
    print(f"  {target}")
    print("\nIt will automatically load in any Antigravity workspace.")
    print("To check status anytime: agy plugin list")
    print("==================================================================")
    return rtk_rc or caveman_rc


if __name__ == "__main__":
    raise SystemExit(main())
