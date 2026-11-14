#!/usr/bin/env python3
"""Safe installer for the compiled plugins/tdq-workflow-agy Antigravity plugin."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from patches.common_utils import sync_tree_inplace


DEFAULT_SRC = Path(__file__).resolve().parent.parent / "plugins" / "tdq-workflow-agy"
DEFAULT_DST = Path.home() / ".gemini" / "config" / "plugins" / "tdq-workflow-agy"


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


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Install tdq-workflow-agy native Antigravity plugin.")
    ap.add_argument("--src", type=Path, default=DEFAULT_SRC)
    ap.add_argument("--target", type=Path, default=DEFAULT_DST)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--sync-local-mcp", action="store_true")
    args = ap.parse_args(argv)

    if not (args.src / "plugin.json").is_file():
        raise SystemExit(f"Compiled plugin missing at {args.src}; run build_agy_plugin.py first.")
    if args.dry_run:
        print(json.dumps({"dry_run": True, "src": str(args.src), "target": str(args.target)}))
        return 0
    files_copied = _copy_plugin(args.src, args.target)
    mcp_res = _sync_local_mcp(args.target) if args.sync_local_mcp else {"synced_servers": []}
    print(json.dumps({"installed_to": str(args.target), "files": files_copied, **mcp_res}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
