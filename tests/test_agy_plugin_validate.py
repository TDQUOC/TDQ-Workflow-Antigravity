"""V1 & V2 Verification: Antigravity strict validator, staged installer, AST, and doc linters."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parent.parent
PLUGIN_DIR = WORKSPACE / "plugins" / "tdq-workflow-agy"
TOOLS_DIR = WORKSPACE / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))
import build_agy_plugin
from patches import common_utils  # noqa: E402


def _run(cmd, cwd=WORKSPACE):
    kw = {"cwd": str(cwd), "capture_output": True, "text": True, "encoding": "utf-8", "timeout": 60}
    if os.name == "nt":
        kw["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
    return subprocess.run(cmd, **kw)


def test_v1_agy_plugin_validate_strict_json():
    res = _run(["agy.EXE", "plugin", "validate", str(PLUGIN_DIR), "--strict", "--json"])
    assert res.returncode == 0, f"agy validate failed: {res.stdout}\n{res.stderr}"
    data = json.loads(res.stdout)
    assert data["name"] == "tdq-workflow-agy"
    assert data["findings"] == []
    assert data["components"] == {
        "agents": 8,
        "hooks": 6,
        "mcpServers": 3,
        "rules": 10,
        "sidecars": 0,
        "skills": 12,
    }


def test_v1_hooks_json_windows_cmd_c_no_quotes_and_protojson():
    import os
    import subprocess

    hooks_data = json.loads((PLUGIN_DIR / "hooks.json").read_text(encoding="utf-8"))
    commands = []

    def _walk(node):
        if isinstance(node, dict):
            if "command" in node:
                commands.append(node["command"])
            for v in node.values():
                _walk(v)
        elif isinstance(node, list):
            for item in node:
                _walk(item)

    _walk(hooks_data)
    assert commands, "hooks.json must contain hook commands"
    valid_prefixes = (
        "bin\\tdq-dispatch.exe --event ",
        "./bin/tdq-dispatch --event ",
        "python -X utf8 hooks/scripts/dispatch.py --event ",
    )
    for cmd in commands:
        assert '"' not in cmd, f"Windows cmd /c escapes double quotes in command: {cmd!r}"
        assert any(cmd.startswith(prefix) for prefix in valid_prefixes), (
            f"Unexpected hook command: {cmd!r}"
        )

    post_entries = hooks_data["tdq-post-tool-observe"]["PostToolUse"]
    assert len(post_entries) == 1
    for removed in ("run_command", "read_file", "view_file"):
        assert removed not in post_entries[0]["matcher"]

    scripts_dir = PLUGIN_DIR / "hooks" / "scripts"
    assert (scripts_dir / "dispatch.py").is_file()
    assert (scripts_dir / "gate_guidance.py").is_file()
    assert not (scripts_dir / "stop_batch_checker.py").exists()
    assert not (scripts_dir / "doc_file_gate.py").exists()
    assert not (scripts_dir / "strategic_compact_gate.py").exists()

    if os.name == "nt":
        for cmd in dict.fromkeys(commands):
            res = subprocess.run(
                ["cmd", "/c", cmd],
                cwd=str(PLUGIN_DIR),
                input="{}",
                text=True,
                capture_output=True,
                encoding="utf-8",
                check=False,
            )
            assert res.returncode == 0, f"cmd /c {cmd!r} failed: {res.stderr}\n{res.stdout}"
            parsed = json.loads(res.stdout.strip())
            assert isinstance(parsed, dict)


def test_v1_install_dry_run_and_staged_validate(tmp_path):
    installer = WORKSPACE / "tools" / "install_agy_plugin.py"
    dry = _run([sys.executable, str(installer), "--dry-run", "--target", str(tmp_path / "tdq-workflow-agy")])
    assert dry.returncode == 0
    assert json.loads(dry.stdout)["dry_run"] is True

    staged = tmp_path / "tdq-workflow-agy"
    inst = _run([sys.executable, str(installer), "--target", str(staged), "--sync-local-mcp"])
    assert inst.returncode == 0
    val = _run(["agy.EXE", "plugin", "validate", str(staged), "--strict", "--json"])
    assert val.returncode == 0, val.stdout
    assert json.loads(val.stdout)["findings"] == []

    stale_marker = staged / "stale_obsolete.txt"
    stale_marker.write_text("stale", encoding="utf-8")
    reinst = _run([sys.executable, str(installer), "--target", str(staged)], cwd=staged)
    assert reinst.returncode == 0, f"in-place reinstall failed under locked dir: {reinst.stderr}"
    assert not stale_marker.exists()


def test_v2_python_ast_and_md_budgets_and_no_traps():
    py_count, ast_errs = common_utils.verify_all_py_ast(PLUGIN_DIR)
    assert py_count >= 80
    assert ast_errs == []

    md_count, md_violations = common_utils.check_md_byte_budgets(PLUGIN_DIR)
    assert md_count == 22
    assert md_violations == []

    pjson = json.loads((PLUGIN_DIR / "plugin.json").read_text(encoding="utf-8"))
    assert "userConfig" not in pjson
    mcp = json.loads((PLUGIN_DIR / "mcp_config.json").read_text(encoding="utf-8"))
    assert "variables" not in mcp
    assert set(mcp["mcpServers"].keys()) == {"lsp", "chrome-devtools", "tavily-primary"}

    tb = _run([sys.executable, "-X", "utf8", "scripts/token_budget.py", "--kiem"], cwd=PLUGIN_DIR)
    assert tb.returncode == 0, tb.stdout + tb.stderr

    for folder in ("skills", "rules", "agents"):
        dl = _run([sys.executable, "-X", "utf8", "scripts/doc_lint.py", folder], cwd=PLUGIN_DIR)
        assert dl.returncode == 0, f"doc_lint failed on {folder}: {dl.stdout}\n{dl.stderr}"


def test_v2_multiplatform_binary_magic_bytes():
    """Verify the 3 packaged Rust binaries carry distinct native PE, ELF, and Mach-O headers."""
    bin_dir = PLUGIN_DIR / "bin"
    win_bin = bin_dir / "tdq-dispatch.exe"
    linux_bin = bin_dir / "tdq-dispatch-linux-x86_64"
    darwin_bin = bin_dir / "tdq-dispatch-darwin-arm64"

    for path in (win_bin, linux_bin, darwin_bin):
        assert path.is_file(), f"Missing packaged binary: {path}"

    win_hdr = win_bin.read_bytes()[:4]
    linux_hdr = linux_bin.read_bytes()[:4]
    darwin_hdr = darwin_bin.read_bytes()[:4]

    assert win_hdr.startswith(b"MZ"), f"Unexpected Windows header: {win_hdr!r}"
    assert linux_hdr.startswith(b"\x7fELF"), f"Unexpected Linux header: {linux_hdr!r}"
    assert darwin_hdr in (
        b"\xcf\xfa\xed\xfe",
        b"\xfe\xed\xfa\xcf",
        b"\xca\xfe\xba\xbe",
    ), f"Unexpected macOS Mach-O header: {darwin_hdr!r}"

    distinct_sizes = {win_bin.stat().st_size, linux_bin.stat().st_size, darwin_bin.stat().st_size}
    assert len(distinct_sizes) == 3, f"Expected 3 distinct binary sizes, got {distinct_sizes}"
    assert min(distinct_sizes) > 0

    assert build_agy_plugin.verify_binary_magic(win_bin, "windows")
    assert build_agy_plugin.verify_binary_magic(linux_bin, "linux")
    assert build_agy_plugin.verify_binary_magic(darwin_bin, "darwin")
    assert not build_agy_plugin.verify_binary_magic(win_bin, "linux")
    assert not build_agy_plugin.verify_binary_magic(win_bin, "darwin")


def test_v2_build_verify_binary_magic_and_stage_guard(tmp_path: Path):
    """Verify verify_binary_magic and _stage_rust_binaries reject cross-OS PE overrides."""
    pe_fake = tmp_path / "fake.exe"
    elf_fake = tmp_path / "fake-linux"
    macho_fake = tmp_path / "fake-darwin"
    pe_fake.write_bytes(b"MZ\x90\x00dummy")
    elf_fake.write_bytes(b"\x7fELF\x02\x01dummy")
    macho_fake.write_bytes(b"\xcf\xfa\xed\xfedummy")

    assert build_agy_plugin.verify_binary_magic(pe_fake, "windows")
    assert not build_agy_plugin.verify_binary_magic(pe_fake, "linux")
    assert not build_agy_plugin.verify_binary_magic(pe_fake, "darwin")
    assert build_agy_plugin.verify_binary_magic(elf_fake, "linux")
    assert not build_agy_plugin.verify_binary_magic(elf_fake, "windows")
    assert build_agy_plugin.verify_binary_magic(macho_fake, "darwin")
    assert not build_agy_plugin.verify_binary_magic(tmp_path / "missing", "linux")
    assert not build_agy_plugin.verify_binary_magic(pe_fake, "unknown-os")

    upstream = tmp_path / "upstream"
    prebuilt = upstream / "hooks" / "rust" / "tdq-dispatch" / "prebuilt"
    prebuilt.mkdir(parents=True)
    existing_bin = tmp_path / "existing_bin"
    existing_bin.mkdir(parents=True)
    stage_bin = tmp_path / "stage_bin"

    # Cross-OS PE masquerading as Linux ELF must raise RuntimeError
    (prebuilt / "tdq-dispatch.exe").write_bytes(b"MZ\x90\x00pe")
    (existing_bin / "tdq-dispatch-linux-x86_64").write_bytes(b"MZ\x90\x00wrong-pe")
    (existing_bin / "tdq-dispatch-darwin-arm64").write_bytes(b"\xcf\xfa\xed\xfemacho")
    with pytest.raises(RuntimeError, match="tdq-dispatch-linux-x86_64"):
        build_agy_plugin._stage_rust_binaries(upstream, stage_bin, existing_bin)

    # Cross-OS PE masquerading as macOS Mach-O must also raise RuntimeError
    (existing_bin / "tdq-dispatch-linux-x86_64").write_bytes(b"\x7fELF\x02\x01elf")
    (existing_bin / "tdq-dispatch-darwin-arm64").write_bytes(b"MZ\x90\x00wrong-pe")
    with pytest.raises(RuntimeError, match="tdq-dispatch-darwin-arm64"):
        build_agy_plugin._stage_rust_binaries(upstream, stage_bin, existing_bin)

    # Valid native headers across all 3 targets succeed
    (existing_bin / "tdq-dispatch-darwin-arm64").write_bytes(b"\xcf\xfa\xed\xfemacho")
    staged = build_agy_plugin._stage_rust_binaries(upstream, stage_bin, existing_bin)
    assert set(staged.keys()) == {"windows", "linux", "darwin"}
    for target, path in staged.items():
        assert build_agy_plugin.verify_binary_magic(path, target)


def test_v2_plain_language_presentation_synced_in_plugin():
    """Verify compiled AGY plugin carries plain-language presentation updates."""
    agents_md = (PLUGIN_DIR / "rules" / "AGENTS.md").read_text(encoding="utf-8")
    assert "Default plain-language narrative across `spec`, `plan`, and `report`" in agents_md

    block_md = (
        PLUGIN_DIR / "skills" / "tdq-conventions" / "references" / "user-facing-block.md"
    ).read_text(encoding="utf-8")
    assert "## Plain-Language Narrative Rule" in block_md

    report_md = (
        PLUGIN_DIR / "skills" / "tdq-build" / "references" / "report-template.md"
    ).read_text(encoding="utf-8")
    assert "Tóm tắt nhanh:" in report_md
    assert "compress each item into ONE line" not in report_md

    spec_md = (
        PLUGIN_DIR / "skills" / "tdq-spec" / "references" / "spec-template.md"
    ).read_text(encoding="utf-8")
    assert "Tóm tắt dễ hiểu:" in spec_md


def test_v2_version_synced_with_claude_plugin():
    """Verify compiled AGY plugin version matches .claude-plugin/plugin.json."""
    claude_ver = json.loads(
        (WORKSPACE / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
    )["version"]
    pjson = json.loads((PLUGIN_DIR / "plugin.json").read_text(encoding="utf-8"))
    mjson = json.loads((PLUGIN_DIR / "manifest.json").read_text(encoding="utf-8"))
    assert pjson["version"] == claude_ver
    assert mjson["version"] == claude_ver
    assert (PLUGIN_DIR / "README.md").read_text(encoding="utf-8").startswith(
        f"# TDQ Workflow (`tdq-workflow-agy`) — Google Antigravity Native Plugin (`v{claude_ver}`)"
    )
