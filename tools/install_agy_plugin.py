#!/usr/bin/env python3
"""Safe installer for the compiled plugins/tdq-workflow-agy Antigravity plugin."""
import argparse
from datetime import datetime
import json
import os
import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
ROOT_DIR = TOOLS_DIR.parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))
from patches.common_utils import sync_tree_inplace


DEFAULT_SRC = ROOT_DIR / "plugins" / "tdq-workflow-agy"
DEFAULT_DST = Path.home() / ".gemini" / "config" / "plugins" / "tdq-workflow-agy"


def _log(message: str) -> None:
    """Emit an ISO-timestamped diagnostic line to stderr unless TDQ_LOG=0."""
    if os.environ.get("TDQ_LOG", "1") != "0":
        stamp = datetime.now().isoformat(timespec="seconds")
        print(f"[{stamp}] install_agy_plugin: {message}", file=sys.stderr)


def _copy_plugin(src: Path, dst: Path) -> int:
    return sync_tree_inplace(src, dst)


def _sync_local_mcp(dst: Path) -> dict:
    """Merge local non-repo lsp args / env (never committed to repo) into installed copy."""
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
                    cfg["mcpServers"]["lsp"]["args"] = [str(a) for a in lsp["args"]]
                synced.append("lsp")
        except (OSError, ValueError):
            pass
    mcp_file.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"synced_servers": synced}


def _import_rtk_integration(src: Path | None = None):
    """Import scripts/rtk_integration from repo root or fallback plugin directory."""
    candidates = [str(ROOT_DIR / "scripts")]
    if src is not None:
        candidates.append(str(Path(src) / "scripts"))
    for cand in candidates:
        if cand not in sys.path and os.path.isdir(cand):
            sys.path.insert(0, cand)
    import rtk_integration
    return rtk_integration


def _handle_rtk(src: Path, with_rtk: bool, skip_rtk: bool, dry_run: bool) -> tuple[int, dict]:
    """Probe rtk/rg status and install only when --with-rtk is explicitly passed."""
    if skip_rtk:
        _log("RTK/rg check skipped (--skip-rtk)")
        return 0, {
            "present": False, "valid": False, "rg_present": False,
            "version": "", "installed": False, "skipped": True, "reason": "skip_rtk",
        }
    rtk_mod = _import_rtk_integration(src)
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


def parse_args(argv=None) -> argparse.Namespace:
    """Parse CLI arguments for the Antigravity native plugin installer."""
    ap = argparse.ArgumentParser(description="Install tdq-workflow-agy native Antigravity plugin.")
    ap.add_argument("--src", type=Path, default=DEFAULT_SRC)
    ap.add_argument("--target", type=Path, default=DEFAULT_DST)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--sync-local-mcp", action="store_true")
    ap.add_argument("--with-rtk", action="store_true")
    ap.add_argument("--skip-rtk", action="store_true")
    return ap.parse_args(argv)


def main(argv=None) -> int:
    """Install the compiled plugin and report JSON status including optional RTK probe."""
    args = parse_args(argv)
    if not (args.src / "plugin.json").is_file():
        raise SystemExit(f"Compiled plugin missing at {args.src}; run build_agy_plugin.py first.")
    if args.dry_run:
        rtk_rc, rtk_status = _handle_rtk(args.src, args.with_rtk, args.skip_rtk, dry_run=True)
        print(json.dumps({"dry_run": True, "src": str(args.src), "target": str(args.target), "rtk": rtk_status}))
        return rtk_rc
    files_copied = _copy_plugin(args.src, args.target)
    mcp_res = _sync_local_mcp(args.target) if args.sync_local_mcp else {"synced_servers": []}
    rtk_rc, rtk_status = _handle_rtk(args.src, args.with_rtk, args.skip_rtk, dry_run=False)
    print(json.dumps({"installed_to": str(args.target), "files": files_copied, **mcp_res, "rtk": rtk_status}))
    return rtk_rc


if __name__ == "__main__":
    raise SystemExit(main())
