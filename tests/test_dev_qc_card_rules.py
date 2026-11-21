"""Contract tests for Dev Behavior QC Card, Auto Meta-Gate, and scoped QC-F4 rules."""
import os
import unittest

import pytest

from helper import ROOT

pytestmark = pytest.mark.smoke

QC_MD = os.path.join(ROOT, "skills", "tdq-build", "references", "qc.md")
REPORT_TEMPLATE_MD = os.path.join(ROOT, "skills", "tdq-build", "references", "report-template.md")
QC_TESTER_AGENT = os.path.join(ROOT, "agents", "tdq-qc-tester.md")


def _read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


class DevBehaviorQcCardContractTest(unittest.TestCase):
    def setUp(self):
        self.qc = _read(QC_MD)
        self.report = _read(REPORT_TEMPLATE_MD)
        self.tester = _read(QC_TESTER_AGENT)

    def test_qc_md_uses_workers_auto_and_smoke_e2e(self):
        self.assertIn("--workers auto", self.qc)
        self.assertNotIn("tron-bo --workers 1", self.qc)
        self.assertIn("smoke-e2e --changed", self.qc)
        self.assertIn("tdq_meta_gate.py", self.qc)

    def test_qc_md_scopes_f4_oop_to_classes_and_adds_script_checks(self):
        f4_block = self.qc.split("- QC-F4", 1)[1].split("\n\n", 1)[0]
        self.assertRegex(f4_block, r"(?i)only when .*class|arch")
        self.assertIn("clean-code.md", f4_block)
        self.assertRegex(f4_block, r"(?i)fail-closed")
        self.assertRegex(f4_block, r"(?i)50\s*lines")

    def test_qc_md_has_dev_behavior_qc_card_and_five_step_gate(self):
        self.assertIn("Dev Behavior QC Card", self.qc)
        self.assertIn("5-step Fresh Evidence Gate", self.qc)
        self.assertIn("smoke test", self.qc)

    def test_report_template_references_qc_card_and_preserves_quick_summary(self):
        self.assertIn("Dev Behavior QC Card", self.report)
        self.assertIn("Tóm tắt dễ hiểu:", self.report)
        self.assertIn("tdq_timing.py show", self.report)

    def test_qc_tester_agent_aligns_with_card_smoke_e2e_and_meta_gate(self):
        self.assertIn("Dev Behavior QC Card", self.tester)
        self.assertIn("smoke-e2e", self.tester)
        self.assertIn("tdq_meta_gate.py", self.tester)


if __name__ == "__main__":
    unittest.main()
