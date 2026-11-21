"""Smoke regression guard locking the v0.103.0 subagent tool-registry failure mode."""
from pathlib import Path
import re
import shutil
import sys

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.patches import skills_and_agents  # noqa: E402

pytestmark = pytest.mark.smoke

EXPECTED_AGENTS = tuple(sorted(skills_and_agents.AGENT_FRONTMATTERS.keys()))
VALID_AGY_MODELS = frozenset({"inherit", "flash_lite", "flash", "pro"})
READONLY_AGY_TOOLS = frozenset(skills_and_agents._READONLY_TOOLS)
ALLOWED_AGY_TOOLS = frozenset(skills_and_agents._WRITER_TOOLS)
WRITE_TOOLS = frozenset({
    "edit_file",
    "write_file",
    "write_to_file",
    "replace_file_content",
    "multi_replace_file_content",
})
BANNED_SOURCE_TOOLS = frozenset({
    "call_mcp_tool",
    "grep_search",
    "find_by_name",
    "list_dir",
})
BANNED_COMPILED_TOOLS = BANNED_SOURCE_TOOLS | frozenset({
    "Bash",
    "Read",
    "Write",
    "Edit",
    "Grep",
    "Glob",
    "Task",
})


def _split_frontmatter(text: str) -> tuple[dict[str, str] | None, str]:
    """Parse leading YAML frontmatter key/value pairs and return (fields, body)."""
    normalized = text.replace("\r\n", "\n")
    if not normalized.startswith("---\n"):
        return None, normalized
    end = normalized.find("\n---\n", 4)
    if end < 0:
        return None, normalized
    fields: dict[str, str] = {}
    for raw_line in normalized[4:end].splitlines():
        if not raw_line.strip():
            continue
        if ":" not in raw_line:
            return None, normalized
        key, _, value = raw_line.partition(":")
        clean_key = key.strip()
        if not clean_key:
            return None, normalized
        fields[clean_key] = value.strip()
    return fields, normalized[end + 5:]


def _parse_tools_field(raw_tools: str, *, require_brackets: bool) -> list[str] | None:
    """Parse frontmatter `tools` field into normalized tool names."""
    text = raw_tools.strip()
    if require_brackets:
        if not (text.startswith("[") and text.endswith("]")):
            return None
        text = text[1:-1]
    elif text.startswith("[") and text.endswith("]"):
        text = text[1:-1]
    return [item.strip() for item in text.split(",") if item.strip()]


def _check_enforcement_notice(name: str, body: str, tool_set: set[str]) -> list[str]:
    """Verify host-enforcement notices and read/write capabilities match agent role."""
    errors: list[str] = []
    if name in skills_and_agents._STRICT_READONLY_AGENTS:
        leaked = sorted(tool_set & WRITE_TOOLS)
        if leaked:
            errors.append(f"{name}: strict readonly agent exposes write tools: {', '.join(leaked)}")
        if tool_set != READONLY_AGY_TOOLS:
            errors.append(f"{name}: readonly tools mismatch: {sorted(tool_set)}")
        if "[TDQ:READONLY]" not in body:
            errors.append(f"{name}: missing [TDQ:READONLY] host-enforcement notice")
        return errors
    if tool_set != ALLOWED_AGY_TOOLS:
        errors.append(f"{name}: writer tools mismatch: {sorted(tool_set)}")
    if name in skills_and_agents._SCOPED_INVESTIGATION_AGENTS:
        if "[TDQ:SCOPED-WRITE]" not in body or "[TDQ:READONLY]" not in body:
            errors.append(f"{name}: missing [TDQ:SCOPED-WRITE]/[TDQ:READONLY] notice")
    elif name == "tdq-qc-tester.md":
        if "[TDQ:QC-SCOPED]" not in body or "docs/tdq/qc/*.md" not in body:
            errors.append(f"{name}: missing [TDQ:QC-SCOPED] host-enforcement notice")
    return errors


def validate_compiled_agent_file(path: Path) -> list[str]:
    """Validate one compiled Antigravity agent markdown file."""
    fields, body = _split_frontmatter(path.read_text(encoding="utf-8"))
    if fields is None:
        return [f"{path.name}: missing or malformed YAML frontmatter"]
    errors: list[str] = []
    for key in ("name", "description", "tools", "model"):
        if not fields.get(key):
            errors.append(f"{path.name}: missing required frontmatter key `{key}`")
    if fields.get("name") and fields["name"] != path.stem:
        errors.append(f"{path.name}: name `{fields['name']}` != `{path.stem}`")
    model = fields.get("model", "")
    if model and model not in VALID_AGY_MODELS:
        errors.append(f"{path.name}: invalid model `{model}`")
    tools = _parse_tools_field(fields.get("tools", ""), require_brackets=True)
    if tools is None:
        return [*errors, f"{path.name}: `tools` must be a YAML inline bracket list"]
    if not tools:
        return [*errors, f"{path.name}: empty tools list"]
    tool_set = set(tools)
    banned = sorted(tool_set & BANNED_COMPILED_TOOLS)
    if banned:
        errors.append(f"{path.name}: banned tools present: {', '.join(banned)}")
    unknown = sorted(tool_set - ALLOWED_AGY_TOOLS)
    if unknown:
        errors.append(f"{path.name}: unregistered AGY tools present: {', '.join(unknown)}")
    errors.extend(_check_enforcement_notice(path.name, body, tool_set))
    return errors


def validate_compiled_agents_dir(agents_dir: Path) -> list[str]:
    """Validate all 8 compiled `tdq-*.md` agent files in `agents_dir`."""
    found = tuple(sorted(p.name for p in agents_dir.glob("tdq-*.md")))
    if found != EXPECTED_AGENTS:
        return [f"expected 8 agents {EXPECTED_AGENTS}, found {found}"]
    errors: list[str] = []
    for name in EXPECTED_AGENTS:
        errors.extend(validate_compiled_agent_file(agents_dir / name))
    return errors


def assert_valid_compiled_agents(agents_dir: Path) -> None:
    """Fail loudly with full diagnostic list if any compiled agent violates v0.103.0 rules."""
    errors = validate_compiled_agents_dir(agents_dir)
    if errors:
        raise AssertionError("\n".join(errors))


def validate_source_agents_dir(agents_dir: Path) -> list[str]:
    """Validate source `agents/tdq-*.md` frontmatter and guard against AGY-banned tool leaks."""
    found = tuple(sorted(p.name for p in agents_dir.glob("tdq-*.md")))
    if found != EXPECTED_AGENTS:
        return [f"source agents mismatch: expected {EXPECTED_AGENTS}, found {found}"]
    errors: list[str] = []
    for name in EXPECTED_AGENTS:
        fields, _ = _split_frontmatter((agents_dir / name).read_text(encoding="utf-8"))
        if fields is None:
            errors.append(f"source {name}: missing or malformed YAML frontmatter")
            continue
        for key in ("name", "description", "model", "effort"):
            if not fields.get(key):
                errors.append(f"source {name}: missing `{key}`")
        if fields.get("model") not in VALID_AGY_MODELS:
            errors.append(f"source {name}: invalid model `{fields.get('model')}`")
        if "tools" in fields:
            tools = _parse_tools_field(fields["tools"], require_brackets=False) or []
            leaked = sorted(set(tools) & BANNED_SOURCE_TOOLS)
            if leaked:
                errors.append(f"source {name}: unregistered tools leaked: {', '.join(leaked)}")
    return errors


def _compile_agents_copy(tmp_path: Path) -> Path:
    """Copy source `agents/` into `tmp_path` and compile via `transform_agents`."""
    shutil.copytree(REPO_ROOT / "agents", tmp_path / "agents")
    converted = skills_and_agents.transform_agents(tmp_path)
    assert converted == len(EXPECTED_AGENTS)
    return tmp_path / "agents"


def test_source_and_compiled_transform_agents_pass_v01030_guard(tmp_path: Path) -> None:
    """Both source agents and compiled Antigravity agents pass frontmatter & tool checks."""
    source_errors = validate_source_agents_dir(REPO_ROOT / "agents")
    assert source_errors == []

    compiled_dir = _compile_agents_copy(tmp_path)
    assert_valid_compiled_agents(compiled_dir)

    built_dir = REPO_ROOT / "plugins" / "tdq-workflow-agy" / "agents"
    assert_valid_compiled_agents(built_dir)


@pytest.mark.parametrize(
    "banned_tool",
    [
        "call_mcp_tool",
        "grep_search",
        "find_by_name",
        "list_dir",
        "Bash",
        "Read",
        "Write",
        "Edit",
        "Grep",
        "Glob",
        "Task",
    ],
)
def test_negative_validator_rejects_injected_banned_tool(tmp_path: Path, banned_tool: str) -> None:
    """Injecting any v0.103.0 or legacy Claude tool into a compiled agent fails loudly."""
    compiled_dir = _compile_agents_copy(tmp_path)
    target = compiled_dir / "tdq-qc-tester.md"
    original = target.read_text(encoding="utf-8")
    assert "tools: [" in original
    target.write_text(
        original.replace("tools: [", f"tools: [{banned_tool}, ", 1),
        encoding="utf-8",
    )

    errors = validate_compiled_agents_dir(compiled_dir)
    assert any("tdq-qc-tester.md" in err and banned_tool in err for err in errors), errors
    with pytest.raises(AssertionError, match=re.escape(banned_tool)):
        assert_valid_compiled_agents(compiled_dir)


def test_negative_validator_rejects_v01030_combo_and_enforcement_regressions(tmp_path: Path) -> None:
    """Detect combined v0.103.0 tool leaks, stripped notices, readonly write leaks, and bad model."""
    compiled_dir = _compile_agents_copy(tmp_path)

    explorer = compiled_dir / "tdq-explorer.md"
    explorer.write_text(
        explorer.read_text(encoding="utf-8").replace(
            "tools: [", "tools: [call_mcp_tool, grep_search, ", 1
        ),
        encoding="utf-8",
    )

    qc_tester = compiled_dir / "tdq-qc-tester.md"
    qc_tester.write_text(
        qc_tester.read_text(encoding="utf-8").replace("[TDQ:QC-SCOPED]", "REMOVED-TAG"),
        encoding="utf-8",
    )

    sec_rev = compiled_dir / "tdq-security-reviewer.md"
    sec_rev.write_text(
        sec_rev.read_text(encoding="utf-8")
        .replace("tools: [", "tools: [write_file, ", 1)
        .replace("model: inherit", "model: invalid_model", 1),
        encoding="utf-8",
    )

    errors = validate_compiled_agents_dir(compiled_dir)
    joined = "\n".join(errors)
    assert "call_mcp_tool" in joined
    assert "grep_search" in joined
    assert "[TDQ:QC-SCOPED]" in joined
    assert "write_file" in joined
    assert "invalid_model" in joined
    with pytest.raises(AssertionError):
        assert_valid_compiled_agents(compiled_dir)


def test_negative_validator_rejects_missing_frontmatter_and_empty_tools(tmp_path: Path) -> None:
    """Missing YAML frontmatter or empty tools brackets fail validation loudly."""
    compiled_dir = _compile_agents_copy(tmp_path)
    impl = compiled_dir / "tdq-implementer.md"
    impl.write_text("# TDQ Implementer\nNo frontmatter here.\n", encoding="utf-8")

    resolver = compiled_dir / "tdq-build-resolver.md"
    resolver.write_text(
        re.sub(r"^tools: \[.*\]$", "tools: []", resolver.read_text(encoding="utf-8"), flags=re.MULTILINE),
        encoding="utf-8",
    )

    errors = validate_compiled_agents_dir(compiled_dir)
    joined = "\n".join(errors)
    assert "tdq-implementer.md: missing or malformed YAML frontmatter" in joined
    assert "tdq-build-resolver.md: empty tools list" in joined
    with pytest.raises(AssertionError):
        assert_valid_compiled_agents(compiled_dir)
