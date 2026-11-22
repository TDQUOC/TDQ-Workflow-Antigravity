#!/usr/bin/env python3
"""Compile TDQ-Workflow v0.105.0 source into plugins/tdq-workflow-agy/."""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from patches import (
    agy_dispatch,
    agy_hooks,
    agy_launchers,
    agy_manifests,
    cli_fixes_a,
    cli_fixes_b,
    common_utils,
    skills_and_agents,
)

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
_EXTERNAL_UPSTREAM_ENV = os.environ.get("TDQ_EXTERNAL_UPSTREAM", "").strip()
DEFAULT_UPSTREAM = (
    WORKSPACE_ROOT
    if (WORKSPACE_ROOT / "portable_src").is_dir() and (WORKSPACE_ROOT / "hooks" / "scripts").is_dir()
    else (Path(_EXTERNAL_UPSTREAM_ENV) if _EXTERNAL_UPSTREAM_ENV else WORKSPACE_ROOT)
)
PLUGIN_OUT = WORKSPACE_ROOT / "plugins" / "tdq-workflow-agy"
_BINARY_TARGETS: tuple[tuple[str, str], ...] = (
    ("windows", "tdq-dispatch.exe"),
    ("linux", "tdq-dispatch-linux-x86_64"),
    ("darwin", "tdq-dispatch-darwin-arm64"),
)
_OPTIONAL_BINARY_TARGETS: tuple[tuple[str, str], ...] = (
    ("darwin", "tdq-dispatch-darwin-x64"),
)
_MAGIC_PREFIXES: dict[str, tuple[bytes, ...]] = {
    "windows": (b"MZ",),
    "linux": (b"\x7fELF",),
    "darwin": (
        b"\xcf\xfa\xed\xfe",
        b"\xfe\xed\xfa\xcf",
        b"\xce\xfa\xed\xfe",
        b"\xca\xfe\xba\xbe",
    ),
}


def _log(message: str) -> None:
    """Emit an ISO-timestamped diagnostic line to stderr unless TDQ_LOG=0."""
    if os.environ.get("TDQ_LOG", "1") != "0":
        stamp = datetime.now().isoformat(timespec="seconds")
        print(f"[{stamp}] build_agy_plugin: {message}", file=sys.stderr)


def verify_binary_magic(path: Path, target: str) -> bool:
    """Validate binary header bytes against expected target OS magic prefixes."""
    prefixes = _MAGIC_PREFIXES.get(target)
    if prefixes is None:
        return False
    candidate = Path(path)
    if not candidate.is_file():
        return False
    try:
        with candidate.open("rb") as fh:
            header = fh.read(4)
    except OSError:
        return False
    if not header:
        return False
    return any(header.startswith(prefix) for prefix in prefixes)


def _current_host_os() -> str:
    """Return normalized target OS key for the currently executing host."""
    if os.name == "nt":
        return "windows"
    if sys.platform == "darwin":
        return "darwin"
    if sys.platform.startswith("linux"):
        return "linux"
    return sys.platform


def _rust_binary_stale(rust_crate_dir: Path, rust_exe: Path) -> bool:
    """Return True when rust_exe is missing or older than Cargo.toml / src/*.rs."""
    if not rust_exe.is_file():
        return True
    exe_mtime = rust_exe.stat().st_mtime
    sources = [rust_crate_dir / "Cargo.toml", *list((rust_crate_dir / "src").rglob("*.rs"))]
    return any(src.is_file() and src.stat().st_mtime > exe_mtime for src in sources)


def _build_host_rust_binary(rust_crate_dir: Path, host_os: str) -> Path:
    """Build release Rust dispatcher for current host OS when missing or stale."""
    exe_name = "tdq-dispatch.exe" if host_os == "windows" else "tdq-dispatch"
    rust_exe = rust_crate_dir / "target" / "release" / exe_name
    manifest = rust_crate_dir / "Cargo.toml"
    if manifest.is_file() and _rust_binary_stale(rust_crate_dir, rust_exe):
        _log(f"building native {host_os} binary via cargo build --release")
        kw: dict[str, object] = {}
        if os.name == "nt":
            kw["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
        subprocess.run(
            ["cargo", "build", "--manifest-path", str(manifest), "--release"],
            check=True,
            **kw,
        )
    return rust_exe


def _resolve_binary_source(
    target_os: str,
    bin_name: str,
    host_os: str,
    rust_exe: Path,
    prebuilt_dir: Path,
    existing_output_bin: Path,
    upstream_plugin_bin: Path | None = None,
) -> Path | None:
    """Resolve a magic-verified binary path for target_os without cross-OS copying."""
    candidates: list[Path] = []
    if target_os == host_os:
        candidates.append(rust_exe)
    candidates.append(prebuilt_dir / bin_name)
    candidates.append(existing_output_bin / bin_name)
    if upstream_plugin_bin is not None:
        candidates.append(upstream_plugin_bin / bin_name)
    for cand in candidates:
        if not cand.is_file():
            continue
        if verify_binary_magic(cand, target_os):
            return cand
        _log(f"rejected {bin_name} at {cand}: invalid magic bytes for {target_os}")
        return None
    return None


def _stage_rust_binaries(
    upstream: Path, stage_bin: Path, existing_output_bin: Path
) -> dict[str, Path]:
    """Stage and magic-verify native binaries for all three target OSes into stage_bin."""
    stage_bin.mkdir(parents=True, exist_ok=True)
    host_os = _current_host_os()
    rust_crate_dir = upstream / "hooks" / "rust" / "tdq-dispatch"
    prebuilt_dir = rust_crate_dir / "prebuilt"
    upstream_plugin_bin = upstream / "plugins" / "tdq-workflow-agy" / "bin"
    rust_exe = _build_host_rust_binary(rust_crate_dir, host_os)

    staged: dict[str, Path] = {}
    failures: list[str] = []
    for target_os, bin_name in _BINARY_TARGETS:
        source = _resolve_binary_source(
            target_os,
            bin_name,
            host_os,
            rust_exe,
            prebuilt_dir,
            existing_output_bin,
            upstream_plugin_bin=upstream_plugin_bin,
        )
        if source is None:
            failures.append(
                f"{bin_name} (expected OS: {target_os}; checked "
                f"{prebuilt_dir / bin_name} and {existing_output_bin / bin_name})"
            )
            continue
        dest = stage_bin / bin_name
        if source.resolve() != dest.resolve():
            shutil.copy2(source, dest)
        if os.name != "nt":
            os.chmod(dest, 0o755)
        if not verify_binary_magic(dest, target_os):
            failures.append(
                f"{bin_name} (expected OS: {target_os}; staged {dest} failed magic check)"
            )
            continue
        _log(f"staged {target_os} binary {bin_name} from {source}")
        staged[target_os] = dest

    for target_os, bin_name in _OPTIONAL_BINARY_TARGETS:
        source = _resolve_binary_source(
            target_os, bin_name, host_os, rust_exe, prebuilt_dir, existing_output_bin,
            upstream_plugin_bin=upstream_plugin_bin,
        )
        if source is None:
            continue
        dest = stage_bin / bin_name
        shutil.copy2(source, dest)
        if os.name != "nt":
            os.chmod(dest, 0o755)
        staged[f"{target_os}_optional_{bin_name}"] = dest

    if failures:
        detail = "; ".join(failures)
        raise RuntimeError(
            "Missing or invalid multi-OS Rust binaries; populate "
            "hooks/rust/tdq-dispatch/prebuilt/ or run SSH cargo build --release "
            f"on target host: {detail}"
        )
    return staged


def _upstream_sha(upstream: Path) -> str:
    """Read upstream HEAD commit hash cleanly without mutating upstream."""
    kw = {"capture_output": True, "text": True, "encoding": "utf-8", "timeout": 15}
    if os.name == "nt":
        kw["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
    res = subprocess.run(
        ["git", "-C", str(upstream), "rev-parse", "--short", "HEAD"], check=False, **kw
    )
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
        config_src = upstream / "tdq-config.json"
        if config_src.is_file():
            shutil.copy2(config_src, stage / "tdq-config.json")

        # 2. Apply CLI & host fixes (NEW-01..NEW-28 + hotfix + AGY parsers)
        cli_fixes_a.apply_all(stage / "scripts")
        cli_fixes_b.apply_all(stage / "scripts")

        # 3. Generate Antigravity native plugin manifests, hooks.json, mcp_config.json, 2-tier rules
        agy_manifests.generate_plugin_json(stage)
        agy_manifests.generate_logo_svg(stage)
        agy_manifests.generate_hooks_json(stage)
        agy_manifests.generate_mcp_config(stage)
        agy_manifests.generate_two_tier_rules(stage)

        # 4. Translate 12 skills (M01-M20), 8 subagents, and relock token-budget.json
        skills_and_agents.transform_skills(stage)
        skills_and_agents.transform_agents(stage)
        agy_hooks.apply_all(stage / "hooks" / "scripts")
        agy_dispatch.apply_dispatch(stage / "hooks" / "scripts")
        skills_and_agents.relock_token_budget(stage)

        # 4b. Generate cross-platform Node launchers & embed standalone Rust binaries
        agy_launchers.generate_launchers(stage)
        _stage_rust_binaries(upstream, stage / "bin", output / "bin")

        # 5. Emit final manifest.json & README.md
        agy_manifests.generate_manifest_and_readme(stage, sha)

        # 6. Immediate AST, Node syntax & Markdown byte-budget checks before syncing
        py_count, ast_errors = common_utils.verify_all_py_ast(stage)
        if ast_errors:
            raise RuntimeError("Python AST errors:\n" + "\n".join(ast_errors))
        if shutil.which("node"):
            for mjs in sorted((stage / "scripts").glob("*.mjs")):
                kw_node = {"capture_output": True, "text": True, "check": False}
                if os.name == "nt":
                    kw_node["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
                chk = subprocess.run(["node", "--check", str(mjs)], **kw_node)
                if chk.returncode != 0:
                    raise RuntimeError(f"Node syntax error in {mjs.name}: {chk.stderr}")
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
    ap = argparse.ArgumentParser(description="Compile TDQ-Workflow v0.105.0 into Antigravity plugin.")
    ap.add_argument("--upstream", type=Path, default=DEFAULT_UPSTREAM, help="Source TDQ-Workflow directory.")
    ap.add_argument("--output", type=Path, default=PLUGIN_OUT, help="Destination compiled plugin directory.")
    args = ap.parse_args(argv)
    stats = build(upstream=args.upstream, output=args.output)
    print(json.dumps(stats, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
