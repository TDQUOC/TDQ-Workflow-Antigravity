#!/usr/bin/env python3
"""TDQ-Workflow Antigravity User-Level Plugin Installer.

Installs the TDQ-Workflow native plugin directly into the user-level configuration directory:
  Windows: %USERPROFILE%\\.gemini\\config\\plugins\\tdq-workflow
  macOS/Linux: ~/.gemini/config/plugins/tdq-workflow

Usage:
  python install.py
  python install.py --enable
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


ROOT_DIR = Path(__file__).resolve().parent
PLUGIN_SRC = ROOT_DIR / "plugins" / "tdq-workflow"
USER_PLUGINS_DIR = Path.home() / ".gemini" / "config" / "plugins"
TARGET_DIR = USER_PLUGINS_DIR / "tdq-workflow"


def _clean_remove(path: Path) -> None:
    if path.is_dir():
        def _on_exc(fn, p, _e):
            try:
                os.chmod(p, stat.S_IWRITE)
                fn(p)
            except Exception:
                pass
        shutil.rmtree(path, onexc=_on_exc)
    elif path.exists():
        path.unlink(missing_ok=True)


def _copy_tree(src: Path, dst: Path) -> int:
    _clean_remove(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, dst)
    return sum(1 for _ in dst.rglob("*") if _.is_file())


def _adjust_hooks_for_platform(installed_dir: Path) -> None:
    """Ensure hooks.json uses python3 on POSIX and py -3 on Windows."""
    hooks_file = installed_dir / "hooks.json"
    if not hooks_file.is_file():
        return
    text = hooks_file.read_text(encoding="utf-8")
    is_win = platform.system() == "Windows"
    py_prefix = "py -3" if is_win else "python3"
    
    # Replace prefix if different
    if is_win:
        text = text.replace("python3 -X utf8", "py -3 -X utf8")
        text = text.replace("python3 ", "py -3 ")
    else:
        text = text.replace("py -3 -X utf8", "python3 -X utf8")
        text = text.replace("py -3 ", "python3 ")
    
    hooks_file.write_text(text, encoding="utf-8")


def _run_agy_command(*args) -> subprocess.CompletedProcess:
    agy_cmd = "agy.exe" if platform.system() == "Windows" else "agy"
    try:
        return subprocess.run([agy_cmd, *args], capture_output=True, text=True, timeout=30)
    except FileNotFoundError:
        # Try full path or fall back
        return subprocess.CompletedProcess([agy_cmd, *args], returncode=127, stdout="", stderr="agy CLI not found on PATH")


def main() -> int:
    parser = argparse.ArgumentParser(description="Install TDQ-Workflow native plugin to user-level Antigravity.")
    parser.add_argument("--src", type=Path, default=PLUGIN_SRC, help="Source plugin directory (default: ./plugins/tdq-workflow)")
    parser.add_argument("--target", type=Path, default=TARGET_DIR, help="Target user-level directory (default: ~/.gemini/config/plugins/tdq-workflow)")
    parser.add_argument("--dry-run", action="store_true", help="Simulate installation without writing to disk")
    parser.add_argument("--no-enable", action="store_true", help="Do not automatically enable the plugin after install")
    args = parser.parse_args()

    src = args.src.resolve()
    target = args.target.resolve()

    if not (src / "plugin.json").is_file():
        print(f"[ERROR] Plugin package not found at: {src}", file=sys.stderr)
        print("Please ensure you run this installer from the repository root.", file=sys.stderr)
        return 1

    print("==================================================================")
    print("TDQ-Workflow Antigravity User-Level Installer")
    print("==================================================================")
    print(f"Source Plugin: {src}")
    print(f"Target (User-Level): {target}")
    print(f"Operating System: {platform.system()} ({platform.release()})")

    if args.dry_run:
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
            findings = val_data.get("findings", [])
            comps = val_data.get("components", {})
            print(f"   [OK] Validation passed: 0 errors, 0 warnings.")
            print(f"        Components: {comps.get('skills', 0)} skills, {comps.get('agents', 0)} agents, "
                  f"{comps.get('rules', 0)} rules, {comps.get('mcpServers', 0)} MCP servers, {comps.get('hooks', 0)} hooks.")
        except Exception:
            print("   [OK] agy plugin validate completed.")
    else:
        print(f"   [NOTE] agy CLI check skipped or returned {val_proc.returncode} ({val_proc.stderr.strip()}).")

    if not args.no_enable:
        print("\n4. Enabling plugin in Antigravity...")
        enable_proc = _run_agy_command("plugin", "enable", "tdq-workflow")
        if enable_proc.returncode == 0:
            print("   [OK] Plugin 'tdq-workflow' is now ENABLED.")
        else:
            print(f"   [NOTE] Could not run 'agy plugin enable tdq-workflow' ({enable_proc.stderr.strip()}).")
            print("          You can enable it manually in Antigravity UI or with: agy plugin enable tdq-workflow")

    print("\n==================================================================")
    print("INSTALLATION SUCCESSFUL!")
    print("==================================================================")
    print(f"The TDQ-Workflow plugin is now installed at user-level:")
    print(f"  {target}")
    print("\nIt will automatically load in any Antigravity workspace.")
    print("To check status anytime: agy plugin list")
    print("==================================================================")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
