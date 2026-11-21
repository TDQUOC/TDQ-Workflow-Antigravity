"""Behavioral tests for pyrightconfig tools coverage and auto-adding user Scripts PATH."""
import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest import mock

from helper import ROOT  # noqa: F401 — ensures scripts/ is on sys.path
import tdq_checkportable
import tdq_setup


class PyrightToolsConfigTest(unittest.TestCase):
    def test_pyrightconfig_includes_tools_and_excludes_plugins(self):
        cfg_path = Path(ROOT) / "pyrightconfig.json"
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        self.assertIn("tools", cfg.get("include", []))
        self.assertIn("tools", cfg.get("extraPaths", []))
        self.assertIn("plugins", cfg.get("exclude", []))


class UserScriptsPathAutoAddTest(unittest.TestCase):
    def test_adds_existing_scripts_dir_with_executable_when_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            scripts_dir = os.path.join(tmp, "Roaming", "Python", "Python313", "Scripts")
            os.makedirs(scripts_dir, exist_ok=True)
            with open(os.path.join(scripts_dir, "ruff.exe"), "wb") as fh:
                fh.write(b"MZ")
            env = {"PATH": r"C:\Python313\Scripts;C:\Users\demo\.local\bin"}
            added_calls = []

            def fake_add(path):
                added_calls.append(path)
                return True

            with mock.patch.dict(os.environ, {"TDQ_LOG": "1"}):
                buf = io.StringIO()
                with redirect_stderr(buf):
                    da_lam, ghi_chu = tdq_checkportable.dam_bao_user_scripts_tren_path(
                        nen_tang="win32",
                        thu_muc_list=[scripts_dir],
                        them_path_fn=fake_add,
                        env=env,
                    )
            self.assertEqual(added_calls, [scripts_dir])
            self.assertTrue(da_lam)
            self.assertTrue(any("added" in line.lower() for line in ghi_chu))
            self.assertIn(scripts_dir.lower(), [p.lower() for p in env["PATH"].split(os.pathsep)])
            self.assertIn("added user scripts dir to PATH", buf.getvalue())

    def test_idempotent_when_dir_already_on_path_case_insensitive(self):
        with tempfile.TemporaryDirectory() as tmp:
            scripts_dir = os.path.join(tmp, "Roaming", "Python", "Python313", "Scripts")
            os.makedirs(scripts_dir, exist_ok=True)
            with open(os.path.join(scripts_dir, "ruff.exe"), "wb") as fh:
                fh.write(b"MZ")
            env = {"PATH": scripts_dir.lower() + os.pathsep + r"C:\Windows\System32"}
            added_calls = []

            da_lam, ghi_chu = tdq_checkportable.dam_bao_user_scripts_tren_path(
                nen_tang="win32",
                thu_muc_list=[scripts_dir],
                them_path_fn=lambda p: added_calls.append(p) or True,
                env=env,
            )
            self.assertEqual(added_calls, [])
            self.assertEqual(da_lam, [])
            self.assertEqual(ghi_chu, [])

    def test_skips_missing_empty_non_exec_and_stub_dirs(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = os.path.join(tmp, "missing", "Scripts")
            empty_dir = os.path.join(tmp, "empty", "Scripts")
            os.makedirs(empty_dir, exist_ok=True)
            txt_only = os.path.join(tmp, "txt_only", "Scripts")
            os.makedirs(txt_only, exist_ok=True)
            with open(os.path.join(txt_only, "notes.txt"), "w", encoding="utf-8") as fh:
                fh.write("not executable")
            stub_dir = os.path.join(tmp, "Microsoft", "WindowsApps")
            os.makedirs(stub_dir, exist_ok=True)
            with open(os.path.join(stub_dir, "python3.exe"), "wb") as fh:
                fh.write(b"MZ")

            env = {"PATH": r"C:\Windows\System32"}
            added_calls = []
            da_lam, ghi_chu = tdq_checkportable.dam_bao_user_scripts_tren_path(
                nen_tang="win32",
                thu_muc_list=[missing, empty_dir, txt_only, stub_dir],
                them_path_fn=lambda p: added_calls.append(p) or True,
                env=env,
            )
            self.assertEqual(added_calls, [])
            self.assertEqual(da_lam, [])
            self.assertEqual(ghi_chu, [])

    def test_respects_tdq_log_0_suppression(self):
        with tempfile.TemporaryDirectory() as tmp:
            scripts_dir = os.path.join(tmp, "Scripts")
            os.makedirs(scripts_dir, exist_ok=True)
            with open(os.path.join(scripts_dir, "ruff.exe"), "wb") as fh:
                fh.write(b"MZ")
            env = {"PATH": ""}
            buf = io.StringIO()
            with mock.patch.dict(os.environ, {"TDQ_LOG": "0"}):
                with redirect_stderr(buf):
                    tdq_checkportable.dam_bao_user_scripts_tren_path(
                        nen_tang="win32",
                        thu_muc_list=[scripts_dir],
                        them_path_fn=lambda _p: True,
                        env=env,
                    )
            self.assertEqual(buf.getvalue(), "")

    def test_setup_helper_respects_khong_cham_may_and_delegates_when_enabled(self):
        with mock.patch.dict(os.environ, {"TDQ_KHONG_CHAM_MAY": "1"}):
            with mock.patch.object(tdq_checkportable, "dam_bao_user_scripts_tren_path") as mocked:
                res = tdq_setup.kiem_va_them_user_scripts_path()
                self.assertEqual(res, ([], [], []))
                mocked.assert_not_called()

        with mock.patch.dict(os.environ, {"TDQ_KHONG_CHAM_MAY": "0"}):
            with mock.patch.object(
                tdq_checkportable,
                "dam_bao_user_scripts_tren_path",
                return_value=(["added PATH"], ["registry ok"]),
            ) as mocked:
                da_lam, ghi_chu, no = tdq_setup.kiem_va_them_user_scripts_path()
                self.assertEqual(da_lam, ["added PATH"])
                self.assertEqual(ghi_chu, ["registry ok"])
                self.assertEqual(no, [])
                mocked.assert_called_once()


class SelfHealingRuleSyncTest(unittest.TestCase):
    def test_claude_md_and_tdq_setup_carry_user_path_self_healing_rule(self):
        needle = "thư mục Scripts/bin mức người dùng"
        core_text = (Path(ROOT) / "docs" / "claude-md-mau.md").read_text(encoding="utf-8")
        khoi = tdq_setup.khoi_huong_dan(tdq_setup.GOC_MAU)
        self.assertIn(needle, core_text)
        self.assertIn(needle, khoi)
        self.assertIn("User `PATH`", core_text)
        self.assertIn("User `PATH`", khoi)


if __name__ == "__main__":
    unittest.main()
