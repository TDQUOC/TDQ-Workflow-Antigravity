"""P2 — mọi agent phải khai rõ `model` và `effort` trong frontmatter.

Lý do: `effort` CHỈ đặt được ở frontmatter (Agent tool không có tham số `effort`),
nên bỏ trống = agent chạy theo mức của phiên, không kiểm soát được chi phí/chất
lượng. `model` khai sẵn để agent cơ học không đắt theo model user đang bật.
Bảng mặc định + lý do: skills/tdq-conventions/references/subagent-tuning.md.
"""
import hashlib
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
import unittest

from helper import ROOT

AGENTS = os.path.join(ROOT, "agents")
AGY_AGENTS = os.path.join(ROOT, "plugins", "tdq-workflow-agy", "agents")
EXPECTED_AGENTS = (
    "tdq-implementer.md",
    "tdq-qc-tester.md",
    "tdq-reviewer.md",
    "tdq-security-reviewer.md",
    "tdq-build-resolver.md",
    "tdq-refactor-cleaner.md",
    "tdq-explorer.md",
    "tdq-debugger.md",
)
STRICT_READONLY_AGENTS = ("tdq-security-reviewer.md",)
SCOPED_INVESTIGATION_AGENTS = (
    "tdq-reviewer.md",
    "tdq-explorer.md",
    "tdq-debugger.md",
)
READONLY_AGENTS = STRICT_READONLY_AGENTS
AGY_ALLOWED_TOOLS = {
    "read_file",
    "edit_file",
    "write_file",
    "run_command",
    "manage_task",
    "search_web",
    "send_message",
}
AGY_FORBIDDEN_TOOLS = {"call_mcp_tool", "grep_search", "find_by_name", "list_dir"}
AGY_DISCOVERY_TOOLS = {"read_file", "run_command", "manage_task", "send_message"}
AGY_WRITE_TOOLS = {
    "edit_file",
    "write_file",
    "write_to_file",
    "replace_file_content",
    "multi_replace_file_content",
}
MODEL_ALIASES = {"sonnet", "opus", "haiku", "fable", "inherit"}
MODEL_ID = re.compile(r"^claude-[\w.-]+$")
EFFORTS = {"low", "medium", "high", "xhigh", "max"}
FIELD = r"^{}:\s*(.+?)\s*$"


def frontmatter(path):
    with open(path, encoding="utf-8") as f:
        text = f.read()
    if not text.startswith("---\n"):
        return None
    return text.split("---", 2)[1]


def field(head, name):
    match = re.search(FIELD.format(name), head, re.MULTILINE)
    return match.group(1) if match else None


def _parse_tools_list(head):
    """Parse YAML inline bracket list `[a, b, c]` from frontmatter tools field."""
    raw = (field(head, "tools") or "").strip()
    if raw.startswith("[") and raw.endswith("]"):
        raw = raw[1:-1]
    return {item.strip() for item in raw.split(",") if item.strip()}


class AgentFrontmatterTest(unittest.TestCase):
    def agent_files(self):
        names = sorted(n for n in os.listdir(AGENTS) if n.endswith(".md"))
        self.assertTrue(names, "không tìm thấy file agent nào")
        return names

    def test_every_agent_declares_model_and_effort(self):
        for name in self.agent_files():
            with self.subTest(agent=name):
                head = frontmatter(os.path.join(AGENTS, name))
                self.assertIsNotNone(head, f"{name}: thiếu frontmatter")
                model = field(head, "model")
                effort = field(head, "effort")
                self.assertIsNotNone(model, f"{name}: thiếu trường model")
                self.assertIsNotNone(effort, f"{name}: thiếu trường effort")
                self.assertTrue(
                    model in MODEL_ALIASES or MODEL_ID.match(model),
                    f"{name}: model {model!r} không hợp lệ")
                self.assertIn(effort, EFFORTS, f"{name}: effort {effort!r} không hợp lệ")

    def test_quality_agents_are_not_throttled(self):
        """Agent làm việc chất lượng không được ép nghĩ nông (effort thấp)."""
        for name in ("tdq-implementer.md", "tdq-qc-tester.md", "tdq-reviewer.md"):
            with self.subTest(agent=name):
                head = frontmatter(os.path.join(AGENTS, name))
                self.assertIn(field(head, "effort"), {"high", "xhigh", "max"})

    def test_tuning_reference_exists_and_lists_every_agent(self):
        ref = os.path.join(ROOT, "skills", "tdq-conventions", "references",
                           "subagent-tuning.md")
        self.assertTrue(os.path.isfile(ref), "thiếu references/subagent-tuning.md")
        with open(ref, encoding="utf-8") as f:
            text = f.read()
        for name in self.agent_files():
            self.assertIn(name[:-3], text, f"subagent-tuning.md thiếu dòng cho {name}")

    def test_all_eight_agents_exist_in_both_trees_with_model_inherit(self):
        """All 8 expected agents exist in root and AGY bundle with model: inherit."""
        root_names = set(self.agent_files())
        agy_names = sorted(n for n in os.listdir(AGY_AGENTS) if n.endswith(".md"))
        self.assertLessEqual(set(EXPECTED_AGENTS), root_names)
        self.assertEqual(agy_names, sorted(EXPECTED_AGENTS))
        for name in EXPECTED_AGENTS:
            for label, folder in (("root", AGENTS), ("agy", AGY_AGENTS)):
                with self.subTest(tree=label, agent=name):
                    path = os.path.join(folder, name)
                    self.assertTrue(os.path.isfile(path), f"missing {label} agent: {name}")
                    head = frontmatter(path)
                    self.assertIsNotNone(head, f"{label}/{name}: missing frontmatter")
                    self.assertEqual(field(head, "model"), "inherit")

    def test_skills_and_agents_tool_lists_forbid_unregistered_tools(self):
        """AGY compiler lists and transform_agents() output only valid Antigravity 2.0 tools."""
        if ROOT not in sys.path:
            sys.path.insert(0, ROOT)
        from tools.patches import skills_and_agents

        self.assertEqual(
            skills_and_agents._READONLY_TOOLS,
            ["read_file", "run_command", "manage_task", "send_message"],
        )
        self.assertEqual(
            skills_and_agents._WRITER_TOOLS,
            [
                "read_file",
                "edit_file",
                "write_file",
                "run_command",
                "manage_task",
                "search_web",
                "send_message",
            ],
        )
        for name, meta in skills_and_agents.AGENT_FRONTMATTERS.items():
            tools = set(meta["tools"])
            self.assertLessEqual(tools, AGY_ALLOWED_TOOLS, f"{name}: invalid tools {tools}")
            self.assertEqual(tools & AGY_FORBIDDEN_TOOLS, set(), f"{name}: forbidden tools")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_root = Path(tmp)
            tmp_agents = tmp_root / "agents"
            shutil.copytree(AGENTS, tmp_agents)
            self.assertEqual(skills_and_agents.transform_agents(tmp_root), len(EXPECTED_AGENTS))
            for name in EXPECTED_AGENTS:
                path = tmp_agents / name
                tools = _parse_tools_list(frontmatter(path))
                self.assertLessEqual(tools, AGY_ALLOWED_TOOLS, f"transformed {name}: invalid tools")
                self.assertEqual(tools & AGY_FORBIDDEN_TOOLS, set(), f"transformed {name}: forbidden")
                self.assertLessEqual(AGY_DISCOVERY_TOOLS, tools, f"transformed {name}: missing base")
                if name in STRICT_READONLY_AGENTS:
                    self.assertEqual(tools & AGY_WRITE_TOOLS, set())
            explorer_body = (tmp_agents / "tdq-explorer.md").read_text(encoding="utf-8")
            self.assertNotIn("(`write_file`/`edit_file`/`write_file`)", explorer_body)

    def test_built_agy_agents_forbid_unregistered_tools(self):
        """Built plugins/tdq-workflow-agy/agents/tdq-*.md must forbid unregistered tools."""
        for name in EXPECTED_AGENTS:
            with self.subTest(agent=name):
                path = os.path.join(AGY_AGENTS, name)
                tools = _parse_tools_list(frontmatter(path))
                self.assertTrue(tools, f"{name}: empty tools list")
                self.assertLessEqual(tools, AGY_ALLOWED_TOOLS, f"{name}: unregistered tools {tools}")
                self.assertEqual(
                    tools & AGY_FORBIDDEN_TOOLS,
                    set(),
                    f"{name}: forbidden tools {tools & AGY_FORBIDDEN_TOOLS}",
                )
        explorer_body = Path(AGY_AGENTS, "tdq-explorer.md").read_text(encoding="utf-8")
        self.assertNotIn("(`write_file`/`edit_file`/`write_file`)", explorer_body)

    def test_built_agy_agents_tools_and_readonly_notices(self):
        """AGY agents declare discovery tools, strict READONLY notices, and scoped QC notice."""
        for name in EXPECTED_AGENTS:
            with self.subTest(agent=name):
                path = os.path.join(AGY_AGENTS, name)
                with open(path, encoding="utf-8") as fh:
                    body = fh.read()
                head = frontmatter(path)
                tools = _parse_tools_list(head)
                self.assertLessEqual(
                    AGY_DISCOVERY_TOOLS, tools, f"{name}: missing AGY discovery tools"
                )
                self.assertLessEqual(
                    tools, AGY_ALLOWED_TOOLS, f"{name}: unregistered AGY tools {tools}"
                )
                self.assertEqual(
                    tools & AGY_FORBIDDEN_TOOLS,
                    set(),
                    f"{name}: forbidden AGY tools {tools & AGY_FORBIDDEN_TOOLS}",
                )
                if name in STRICT_READONLY_AGENTS:
                    self.assertEqual(
                        tools & AGY_WRITE_TOOLS, set(), f"{name}: read-only has write tools"
                    )
                    self.assertIn("[TDQ:READONLY]", body, f"{name}: missing [TDQ:READONLY]")
                elif name in SCOPED_INVESTIGATION_AGENTS:
                    self.assertIn("write_file", tools, f"{name}: missing scoped write_file tool")
                    self.assertIn("edit_file", tools, f"{name}: missing scoped edit_file tool")
                    self.assertIn("[TDQ:SCOPED-WRITE]", body, f"{name}: missing [TDQ:SCOPED-WRITE]")
                elif name == "tdq-qc-tester.md":
                    self.assertIn("docs/tdq/qc/*.md", body)
                    self.assertIn("[TDQ:QC-SCOPED]", body)

    def test_handoff_schema_sha256_parity(self):
        """Root and AGY handoff-schema.json copies must share identical SHA-256 digests."""
        root_path = os.path.join(
            ROOT, "skills", "tdq-conventions", "references", "handoff-schema.json"
        )
        agy_path = os.path.join(
            ROOT, "plugins", "tdq-workflow-agy",
            "skills", "tdq-conventions", "references", "handoff-schema.json",
        )
        self.assertTrue(os.path.isfile(root_path), "missing root handoff-schema.json")
        self.assertTrue(os.path.isfile(agy_path), "missing AGY handoff-schema.json")
        with open(root_path, "rb") as rf, open(agy_path, "rb") as af:
            root_sha = hashlib.sha256(rf.read()).hexdigest()
            agy_sha = hashlib.sha256(af.read()).hexdigest()
        self.assertEqual(root_sha, agy_sha)


class AgentDigestLimitTest(unittest.TestCase):
    """Request toi-uu-token-vong-2 (T5.1/T5.2) — agent trả DIGEST, không trả
    nguyên output tool: thân agent phải nêu ngưỡng ≤ 1.500 ký tự và cấm dán thô."""

    def agent_files(self):
        return sorted(n for n in os.listdir(AGENTS) if n.endswith(".md"))

    def _body(self, name):
        with open(os.path.join(AGENTS, name), encoding="utf-8") as f:
            text = f.read()
        return text.split("---", 2)[2] if text.startswith("---\n") else text

    def test_moi_agent_neu_nguong_digest(self):
        for name in self.agent_files():
            with self.subTest(agent=name):
                # Từ 2026-08-22 thân agent viết tiếng Anh; nhận cả hai cách viết ngưỡng.
                self.assertTrue(
                    any(m in self._body(name)
                        for m in ("1,500 characters", "1.500 ký tự")),
                    f"{name}: thiếu ngưỡng digest ≤ 1.500 ký tự")

    def test_moi_agent_cam_dan_output_tool_tho(self):
        pattern = re.compile(
            r"(?i)((cấm|không) dán[^\n]{0,60}(thô|nguyên văn output|toàn bộ output)"
            r"|pasting[^\n]{0,120}?is banned)")
        for name in self.agent_files():
            with self.subTest(agent=name):
                self.assertRegex(self._body(name), pattern,
                                 f"{name}: thiếu câu cấm dán kết quả tool thô")


if __name__ == "__main__":
    unittest.main()
