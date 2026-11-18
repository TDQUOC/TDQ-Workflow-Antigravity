#!/usr/bin/env python3
"""Compile TDQ-Workflow v0.100.0 source into plugins/tdq-workflow-agy/."""
import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from patches import agy_dispatch, agy_hooks, agy_manifests, cli_fixes_a, cli_fixes_b, common_utils, skills_and_agents


WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
_EXTERNAL_UPSTREAM = Path(r"C:\Users\admin\Documents\Projects\ForAgentCode\TDQ-Workflow")
DEFAULT_UPSTREAM = (
    WORKSPACE_ROOT
    if (WORKSPACE_ROOT / "portable_src").is_dir() and (WORKSPACE_ROOT / "hooks" / "scripts").is_dir()
    else _EXTERNAL_UPSTREAM
)
PLUGIN_OUT = WORKSPACE_ROOT / "plugins" / "tdq-workflow-agy"


def _upstream_sha(upstream: Path) -> str:
    """Read upstream HEAD commit hash cleanly without mutating upstream."""
    kw = {"capture_output": True, "text": True, "encoding": "utf-8", "timeout": 15}
    if os.name == "nt":
        kw["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
    res = subprocess.run(["git", "-C", str(upstream), "rev-parse", "--short", "HEAD"], **kw)
    return res.stdout.strip() if res.returncode == 0 else "unknown"


def build(upstream: Path = DEFAULT_UPSTREAM, output: Path = PLUGIN_OUT) -> dict:
    """Compile the full standalone Antigravity native plugin and return verification stats."""
    if not (upstream / "scripts").is_dir() or not (upstream / "skills").is_dir():
        raise FileNotFoundError(f"Upstream TDQ-Workflow repo not found at {upstream}")

    sha = _upstream_sha(upstream)
    with tempfile.TemporaryDirectory() as tmpdir:
        stage = Path(tmpdir)

        # 1. Copy runtime assets cleanly from upstream read-only source
        n_scripts = common_utils.copy_clean_tree(
            upstream / "scripts", stage / "scripts", exclude_names=common_utils.EXCLUDED_SCRIPTS
        )
        n_hooks = common_utils.copy_clean_tree(
            upstream / "hooks" / "scripts",
            stage / "hooks" / "scripts",
            exclude_names=common_utils.EXCLUDED_AGY_HOOKS,
        )
        n_skills = common_utils.copy_clean_tree(upstream / "skills", stage / "skills")
        cp_skill = upstream / "portable_src" / "skills" / "tdq-checkportable"
        if cp_skill.is_dir():
            n_skills += common_utils.copy_clean_tree(cp_skill, stage / "skills" / "tdq-checkportable")
        n_agents = common_utils.copy_clean_tree(upstream / "agents", stage / "agents")

        # 2. Apply CLI & host fixes (NEW-01..NEW-28 + hotfix + AGY parsers)
        cli_fixes_a.apply_all(stage / "scripts")
        cli_fixes_b.apply_all(stage / "scripts")

        # 3. Generate Antigravity native plugin manifests, hooks.json, mcp_config.json, 2-tier rules
        agy_manifests.generate_plugin_json(stage)
        agy_manifests.generate_logo_svg(stage)
        agy_manifests.generate_hooks_json(stage)
        agy_manifests.generate_mcp_config(stage)
        agy_manifests.generate_two_tier_rules(stage)

        # 4. Translate 12 skills (M01-M20), 6 subagents, and relock token-budget.json
        skills_and_agents.transform_skills(stage)
        skills_and_agents.transform_agents(stage)
        agy_hooks.apply_all(stage / "hooks" / "scripts")
        agy_dispatch.apply_dispatch(stage / "hooks" / "scripts")
        skills_and_agents.relock_token_budget(stage)

        # 5. Emit final manifest.json & README.md
        agy_manifests.generate_manifest_and_readme(stage, sha)

        # 6. Immediate AST & Markdown byte-budget checks before syncing to live output dir
        py_count, ast_errors = common_utils.verify_all_py_ast(stage)
        if ast_errors:
            raise RuntimeError("Python AST errors:\n" + "\n".join(ast_errors))
        md_count, md_violations = common_utils.check_md_byte_budgets(stage)
        if md_violations:
            raise RuntimeError("Markdown byte budget exceeded:\n" + "\n".join(md_violations))

        common_utils.sync_tree_inplace(stage, output)

    return {
        "upstream": str(upstream),
        "upstream_sha": sha,
        "output": str(output),
        "copied": {"scripts": n_scripts, "hooks": n_hooks, "skills_files": n_skills, "agents": n_agents},
        "ast_checked_py": py_count,
        "md_checked_budget": md_count,
        "status": "OK",
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Compile TDQ-Workflow v0.100.0 into Antigravity plugin.")
    ap.add_argument("--upstream", type=Path, default=DEFAULT_UPSTREAM, help="Source TDQ-Workflow directory.")
    ap.add_argument("--output", type=Path, default=PLUGIN_OUT, help="Destination compiled plugin directory.")
    args = ap.parse_args(argv)
    stats = build(upstream=args.upstream, output=args.output)
    print(json.dumps(stats, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
