"""Tests for T3.2 RTK integration in tdq_setup, tdq_lsp, and session_start."""
import io
import os
import sys
import tempfile
import unittest
from unittest import mock

from helper import HOOKS, ROOT

SCRIPTS = os.path.join(ROOT, "scripts")
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)


class TestTdqSetupAndLspRtk(unittest.TestCase):
    """Verify explicit RTK CLI flags in tdq_setup.py and non-breaking tdq_lsp summary."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.cwd = self._tmp.name
        os.makedirs(os.path.join(self.cwd, ".git"), exist_ok=True)
        os.makedirs(os.path.join(self.cwd, "docs", "tdq"), exist_ok=True)

    def tearDown(self):
        self._tmp.cleanup()

    def test_parse_args_accepts_rtk_flags(self):
        import tdq_setup
        ns = tdq_setup.parse_args(["--with-rtk"])
        self.assertTrue(ns.with_rtk)
        ns_chk = tdq_setup.parse_args(["--check-rtk"])
        self.assertTrue(ns_chk.check_rtk)
        ns_mute = tdq_setup.parse_args(["--mute-rtk-prompt"])
        self.assertTrue(ns_mute.mute_rtk_prompt)
        ns_unmute = tdq_setup.parse_args(["--unmute-rtk-prompt"])
        self.assertTrue(ns_unmute.unmute_rtk_prompt)

    def test_with_rtk_invokes_installer_with_approve_true(self):
        import rtk_integration
        import tdq_setup
        called = {}

        def fake_install(**kw):
            called.update(kw)
            return {"ok": True, "rtk_version": "1.2.0", "rg_version": "15.2.0",
                    "rtk_path": "/bin/rtk", "rg_path": "/bin/rg", "config_path": "/cfg"}

        buf = io.StringIO()
        with (
            mock.patch.object(tdq_setup.tdq_lsp, "_project_dir", return_value=self.cwd),
            mock.patch.object(rtk_integration, "install_rtk_and_rg", side_effect=fake_install),
            mock.patch("sys.stdout", buf),
        ):
            rc = tdq_setup.main(["--khong-log", "--with-rtk"])
        self.assertEqual(rc, 0)
        self.assertTrue(called.get("approve"))

    def test_nen_background_mode_never_installs_rtk(self):
        import rtk_integration
        import tdq_setup
        with (
            mock.patch.object(tdq_setup.tdq_lsp, "_project_dir", return_value=self.cwd),
            mock.patch.object(rtk_integration, "install_rtk_and_rg", side_effect=AssertionError("must not install")),
            mock.patch.object(tdq_setup, "khoi_tao_nen", return_value=None),
        ):
            rc = tdq_setup.main(["--khong-log", "--nen"])
        self.assertEqual(rc, 0)

    def test_tdq_lsp_chay_kiem_keeps_eight_rungs_and_prints_rtk_summary(self):
        import tdq_lsp
        import rtk_integration
        with mock.patch.object(rtk_integration, "probe_rtk", return_value={"valid": False, "collision": False, "reason": "not_found"}):
            with mock.patch.object(rtk_integration, "locate_rg_binary", return_value=None):
                info = tdq_lsp.kiem_tra_cong_cu_bo_tro(self.cwd)
        self.assertFalse(info["rtk"]["valid"])
        self.assertIsNone(info["rg_path"])


class TestSessionStartRtkNotice(unittest.TestCase):
    """Verify SessionStart [TDQ:SETUP] 1-line notice respects mute and single-per-session dedupe."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.cwd = self._tmp.name
        os.makedirs(os.path.join(self.cwd, ".git"), exist_ok=True)
        os.makedirs(os.path.join(self.cwd, "docs", "tdq"), exist_ok=True)

    def tearDown(self):
        self._tmp.cleanup()

    def _run_session_start(self, sid, muted):
        sys.path.insert(0, HOOKS)
        try:
            import rtk_integration
            import session_start
        finally:
            if sys.path and sys.path[0] == HOOKS:
                sys.path.pop(0)
        captured = []
        payload = {
            "cwd": self.cwd,
            "session_id": sid,
            "hookEventName": "SessionStart",
            "source": "startup",
        }
        with (
            mock.patch.object(session_start, "read_payload", return_value=payload),
            mock.patch.object(session_start, "emit_context", side_effect=lambda lines: captured.extend(lines)),
            mock.patch.object(session_start, "can_khoi_tao", return_value=False),
            mock.patch.object(session_start, "kiem_can_setup_lan_dau", return_value=False),
            mock.patch.object(session_start, "kich_hoat_nen", return_value=False),
            mock.patch.object(rtk_integration, "is_prompt_muted", return_value=muted),
            mock.patch.object(rtk_integration, "probe_rtk", return_value={"valid": False, "collision": False, "reason": "not_found"}),
            mock.patch.object(rtk_integration, "locate_rg_binary", return_value=None),
        ):
            session_start.main()
        return "\n".join(captured)

    def test_session_start_emits_setup_once_and_respects_mute(self):
        out1 = self._run_session_start("sid-unmuted", muted=False)
        self.assertIn("[TDQ:SETUP]", out1)
        self.assertIn("--with-rtk", out1)
        # Second fire in same session is deduplicated
        out2 = self._run_session_start("sid-unmuted", muted=False)
        self.assertNotIn("Missing rtk/rg", out2)
        # Muted session stays silent about RTK
        out_muted = self._run_session_start("sid-muted", muted=True)
        self.assertNotIn("Missing rtk/rg", out_muted)


if __name__ == "__main__":
    unittest.main()
