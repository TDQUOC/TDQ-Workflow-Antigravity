"""Hook chặn `[TDQ:LSP]` — `hooks/scripts/lsp_gate.py` (request 2026-10-07-2225, T4.1).

Ca gốc: `start_lsp` không `language_id` trên repo Python → agent-lsp bật hết server, TypeScript
thành server hiện hành → crash `0xc0000409` / "No Project". User chọn chặn (4A).
"""
import json
import os
import shutil
import sys
import tempfile
import time
import unittest

from helper import ROOT, run_hook

sys.path.insert(0, os.path.join(ROOT, "hooks", "scripts"))
import _common  # noqa: E402

HOOK = "lsp_gate.py"


class LspGate(unittest.TestCase):
    def setUp(self):
        self.cwd = tempfile.mkdtemp(prefix="tdq-lsp-gate-")
        self.addCleanup(shutil.rmtree, self.cwd, True)
        os.makedirs(os.path.join(self.cwd, "docs", "tdq"))
        with open(os.path.join(self.cwd, "docs", "tdq", ".tdq-lsp-module.json"), "w", encoding="utf-8") as fh:
            json.dump({"module": {"python:.": {"lang": "python", "goc": "."},
                                  "javascript:web": {"lang": "javascript", "goc": "web"}}}, fh)

    def goi(self, tool_input):
        payload = {"tool_name": "mcp__lsp__start_lsp", "tool_input": tool_input, "cwd": self.cwd,
                   "session_id": "phien-lsp-gate"}
        rc, out, _err = run_hook(HOOK, payload, env={"TDQ_LOG": "0", "TDQ_PROJECT_DIR": self.cwd})
        self.assertEqual(rc, 0)
        return json.loads(out)["hookSpecificOutput"] if out else None

    def test_deny_khi_thieu_language_id(self):
        ra = self.goi({"root_dir": self.cwd}) or {}
        self.assertEqual(ra["permissionDecision"], "deny")
        self.assertIn("[TDQ:LSP]", ra["permissionDecisionReason"])
        self.assertIn('"language_id": "python"', ra["permissionDecisionReason"])

    def test_deny_khi_cap_goc_ngon_ngu_khong_co_trong_bang(self):
        ra = self.goi({"root_dir": self.cwd, "language_id": "html"}) or {}
        self.assertEqual(ra["permissionDecision"], "deny")
        ra = self.goi({"root_dir": os.path.join(self.cwd, "web"), "language_id": "python"}) or {}
        self.assertEqual(ra["permissionDecision"], "deny")

    def test_allow_khi_dung_cap_va_ho_ts_dung_chung(self):
        self.assertIsNone(self.goi({"root_dir": self.cwd, "language_id": "python"}))
        self.assertIsNone(self.goi({"root_dir": os.path.join(self.cwd, "web"), "language_id": "typescript"}))

    def test_allow_khi_goc_ngoai_project_hoac_chua_co_bang(self):
        ngoai = tempfile.mkdtemp(prefix="tdq-ngoai-")
        self.addCleanup(shutil.rmtree, ngoai, True)
        self.assertIsNone(self.goi({"root_dir": ngoai, "language_id": "go"}))
        os.remove(os.path.join(self.cwd, "docs", "tdq", ".tdq-lsp-module.json"))
        self.assertIsNone(self.goi({"root_dir": self.cwd, "language_id": "go"}))

    def test_payload_hong_hoac_rong_khong_bao_gio_chan(self):
        rc, out, _err = run_hook(HOOK, {"tool_name": "mcp__lsp__start_lsp", "cwd": self.cwd},
                                 env={"TDQ_LOG": "0"})
        self.assertEqual((rc, out), (0, ""))
        import subprocess
        p = subprocess.run([sys.executable, os.path.join(ROOT, "hooks", "scripts", HOOK)],
                           input="{không phải json", capture_output=True, text=True, encoding="utf-8",
                           env={**os.environ, "TDQ_LOG": "0"})
        self.assertEqual((p.returncode, p.stdout.strip()), (0, ""))

    def test_ma_lsp_nam_trong_danh_sach_dong(self):
        self.assertIn("TDQ:LSP", _common.CODES)

    def test_thoi_gian_chay_duoi_200ms(self):
        payload = {"tool_name": "mcp__lsp__start_lsp", "cwd": self.cwd,
                   "tool_input": {"root_dir": self.cwd, "language_id": "python"}}
        do = []
        for _ in range(5):
            bat_dau = time.perf_counter()
            run_hook(HOOK, payload, env={"TDQ_LOG": "0"})
            do.append(time.perf_counter() - bat_dau)
        self.assertLess(min(do), 0.2, f"thời gian chạy: {do}")


class BlastRadiusGate(unittest.TestCase):
    def setUp(self):
        self.cwd = tempfile.mkdtemp(prefix="tdq-blast-gate-")
        self.addCleanup(shutil.rmtree, self.cwd, True)
        os.makedirs(os.path.join(self.cwd, "docs", "tdq"), exist_ok=True)
        self.ledger = os.path.join(self.cwd, "docs", "tdq", ".tdq-search.jsonl")

    def goi(self, tool_input):
        payload = {"tool_name": "mcp__lsp__blast_radius", "tool_input": tool_input, "cwd": self.cwd,
                   "session_id": "phien-blast-gate"}
        rc, out, _err = run_hook(HOOK, payload, env={"TDQ_LOG": "0", "TDQ_PROJECT_DIR": self.cwd})
        self.assertEqual(rc, 0)
        return json.loads(out)["hookSpecificOutput"] if out else None

    def test_deny_khi_changed_files_lon_hon_3(self):
        ra = self.goi({"changed_files": ["a.py", "b.py", "c.py", "d.py"]}) or {}
        self.assertEqual(ra.get("permissionDecision"), "deny")
        self.assertIn("4 files > 3", ra.get("permissionDecisionReason", ""))
        self.assertIn("find_references", ra.get("permissionDecisionReason", ""))

    def test_deny_khi_changed_files_rong_hoac_khong_phai_list(self):
        ra = self.goi({"changed_files": []}) or {}
        self.assertEqual(ra.get("permissionDecision"), "deny")
        ra2 = self.goi({"changed_files": "a.py"}) or {}
        self.assertEqual(ra2.get("permissionDecision"), "deny")

    def test_deny_khi_scope_khong_phai_exported(self):
        ra = self.goi({"changed_files": ["a.py"], "scope": "all"}) or {}
        self.assertEqual(ra.get("permissionDecision"), "deny")
        self.assertIn("scope='all'", ra.get("permissionDecisionReason", ""))

    def test_deny_khi_include_transitive_true(self):
        ra = self.goi({"changed_files": ["a.py"], "include_transitive": True}) or {}
        self.assertEqual(ra.get("permissionDecision"), "deny")
        self.assertIn("include_transitive", ra.get("permissionDecisionReason", ""))

    def test_deny_khi_circuit_breaker_mo(self):
        with open(self.ledger, "w", encoding="utf-8") as fh:
            fh.write(json.dumps({
                "ts": time.time(),
                "khoa": "phien:phien-blast-gate",
                "loai": "lsp_ket_qua",
                "cong_cu": "mcp__lsp__blast_radius",
                "outcome": "timeout"
            }) + "\n")
        ra = self.goi({"changed_files": ["a.py"]}) or {}
        self.assertEqual(ra.get("permissionDecision"), "deny")
        self.assertIn("Circuit breaker", ra.get("permissionDecisionReason", ""))

    def test_allow_khi_hop_le_va_mach_dong(self):
        ra = self.goi({"changed_files": ["a.py", "b.py"], "scope": "exported", "include_transitive": False})
        self.assertIsNone(ra)


class McpRoutingVaLog(unittest.TestCase):
    def setUp(self):
        self.cwd = tempfile.mkdtemp(prefix="tdq-lsp-routing-")
        self.addCleanup(shutil.rmtree, self.cwd, True)
        os.makedirs(os.path.join(self.cwd, "docs", "tdq"), exist_ok=True)
        with open(os.path.join(self.cwd, "docs", "tdq", ".tdq-lsp-module.json"), "w", encoding="utf-8") as fh:
            json.dump({"module": {"python:.": {"lang": "python", "goc": "."}}}, fh)

    def goi_agy(self, payload, log="0"):
        full = dict(payload, cwd=self.cwd, session_id="phien-routing", hookEventName="PreToolUse")
        rc, out, err = run_hook(HOOK, full, env={"TDQ_LOG": log, "TDQ_PROJECT_DIR": self.cwd})
        self.assertEqual(rc, 0, err)
        return json.loads(out), err

    def test_allow_chrome_devtools_tavily_other_lsp_va_lsp_query(self):
        cases = (
            {
                "tool_name": "call_mcp_tool",
                "tool_input": {
                    "ServerName": "chrome-devtools",
                    "ToolName": "select_page",
                    "Arguments": {"bringToFront": True, "pageId": 1},
                },
            },
            {
                "tool_name": "call_mcp_tool",
                "tool_input": {"ServerName": "chrome-devtools", "ToolName": "list_pages", "Arguments": {}},
            },
            {
                "tool_name": "call_mcp_tool",
                "tool_input": {
                    "ServerName": "tdq-workflow-agy_tavily-primary",
                    "ToolName": "tavily_search",
                    "Arguments": {"query": "tdq workflow"},
                },
            },
            {
                "tool_name": "call_mcp_tool",
                "tool_input": {
                    "ServerName": "tdq-workflow-agy_lsp",
                    "ToolName": "find_references",
                    "Arguments": {"file_path": "a.py"},
                },
            },
            {
                "tool_name": "call_mcp_tool",
                "tool_input": {
                    "ServerName": "tdq-workflow-agy_lsp",
                    "ToolName": "find_symbol",
                    "Arguments": {"query": "foo"},
                },
            },
            {
                "tool_name": "mcp_tdq-workflow-agy_lsp_find_symbol",
                "tool_input": {"query": "foo"},
            },
            {
                "tool_name": "call_mcp_tool",
                "tool_input": {
                    "ServerName": "other_lsp",
                    "ToolName": "start_lsp",
                    "Arguments": {"root_dir": self.cwd},
                },
            },
            {
                "tool_name": "mcp_other_lsp_start_lsp",
                "tool_input": {"root_dir": self.cwd},
            },
        )
        for case in cases:
            out, _err = self.goi_agy(case)
            self.assertEqual(out.get("decision"), "allow", (case, out))

    def test_deny_start_lsp_voi_arguments_rong_tuong_minh(self):
        for args in ({}, "{}"):
            out, _err = self.goi_agy({
                "tool_name": "call_mcp_tool",
                "tool_input": {
                    "ServerName": "tdq-workflow-agy_lsp",
                    "ToolName": "start_lsp",
                    "Arguments": args,
                },
            })
            self.assertEqual(out.get("decision"), "deny", (args, out))
            self.assertIn("[TDQ:LSP]", out.get("reason", ""))

    def test_allow_fail_open_khi_arguments_hong_hoac_thieu_khoa(self):
        for tinp in (
            {"ServerName": "tdq-workflow-agy_lsp", "ToolName": "start_lsp", "Arguments": "{bad json"},
            {"ServerName": "tdq-workflow-agy_lsp", "ToolName": "start_lsp"},
        ):
            out, _err = self.goi_agy({"tool_name": "call_mcp_tool", "tool_input": tinp})
            self.assertEqual(out.get("decision"), "allow", (tinp, out))

    def test_log_service_bat_mac_dinh_va_tat_bang_tdq_log_0(self):
        payload = {
            "tool_name": "call_mcp_tool",
            "tool_input": {
                "ServerName": "chrome-devtools",
                "ToolName": "select_page",
                "Arguments": {"bringToFront": True, "pageId": 1},
            },
        }
        out_on, err_on = self.goi_agy(payload, log="1")
        self.assertEqual(out_on.get("decision"), "allow")
        self.assertRegex(err_on, r"\[\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\] lsp_gate:")
        self.assertIn("non-tdq-lsp", err_on)

        out_off, err_off = self.goi_agy(payload, log="0")
        self.assertEqual(out_off.get("decision"), "allow")
        self.assertEqual(err_off, "")


if __name__ == "__main__":
    unittest.main()
