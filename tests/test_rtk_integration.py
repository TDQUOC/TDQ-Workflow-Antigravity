#!/usr/bin/env python3
"""Unit tests for scripts/rtk_integration.py (TDD red -> green, mocked I/O)."""
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import rtk_integration as rtk  # noqa: E402


def _make_zip_archive(member_path: str, data: bytes) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(member_path, data)
        zf.writestr("README.md", "ok")
    return buf.getvalue()


def _make_tar_gz_archive(member_path: str, data: bytes) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        info = tarfile.TarInfo(name=member_path)
        info.size = len(data)
        tf.addfile(info, io.BytesIO(data))
    return buf.getvalue()


class TestLocateBinaries(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="tdq-rtk-loc-")
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def test_locate_rtk_prefers_env_override(self):
        fake_bin = os.path.join(self.tmp, "custom-rtk.exe")
        with open(fake_bin, "wb") as fh:
            fh.write(b"MZ")
        with mock.patch.dict(os.environ, {"TDQ_RTK_BIN": fake_bin}):
            self.assertEqual(rtk.locate_rtk_binary(), fake_bin)

    def test_locate_binary_ignores_cwd_and_cmd_shims(self):
        repo_dir = os.path.join(self.tmp, "hostile_repo")
        safe_dir = os.path.join(self.tmp, "safe_bin")
        empty_home = os.path.join(self.tmp, "empty_home")
        os.makedirs(repo_dir, exist_ok=True)
        os.makedirs(safe_dir, exist_ok=True)
        os.makedirs(empty_home, exist_ok=True)
        # Drop CWD hijackers (.cmd, .bat, and .exe) in repo root
        for hijack in ("rtk.cmd", "rtk.bat", "rtk.exe", "rg.cmd", "rg.bat", "rg.exe"):
            with open(os.path.join(repo_dir, hijack), "wb") as fh:
                fh.write(b"@echo hijacked\n")
        # Safe dir initially holds only .cmd shims (must NOT match on Windows)
        for shim in ("rtk.cmd", "rg.cmd"):
            with open(os.path.join(safe_dir, shim), "wb") as fh:
                fh.write(b"@echo shim\n")

        old_cwd = os.getcwd()
        env_patch = {
            "PATH": safe_dir,
            "HOME": empty_home,
            "USERPROFILE": empty_home,
            "TDQ_RTK_BIN": "",
        }
        try:
            os.chdir(repo_dir)
            with (
                mock.patch.dict(os.environ, env_patch),
                mock.patch("os.path.expanduser", side_effect=lambda p: p.replace("~", empty_home)),
            ):
                if os.name == "nt":
                    self.assertIsNone(rtk.locate_rtk_binary())
                    self.assertIsNone(rtk.locate_rg_binary())
                # Now place real binaries in safe_dir -> must resolve safe_dir, NOT repo_dir
                rtk_name = "rtk.exe" if os.name == "nt" else "rtk"
                rg_name = "rg.exe" if os.name == "nt" else "rg"
                safe_rtk = os.path.join(safe_dir, rtk_name)
                safe_rg = os.path.join(safe_dir, rg_name)
                for p in (safe_rtk, safe_rg):
                    with open(p, "wb") as fh:
                        fh.write(b"MZ")
                    os.chmod(p, 0o755)
                self.assertEqual(os.path.abspath(rtk.locate_rtk_binary()), os.path.abspath(safe_rtk))
                self.assertEqual(os.path.abspath(rtk.locate_rg_binary()), os.path.abspath(safe_rg))
        finally:
            os.chdir(old_cwd)

    def test_locate_rtk_falls_back_to_which_then_local_bin(self):
        home_dir = os.path.join(self.tmp, "home")
        local_bin = os.path.join(home_dir, ".local", "bin")
        os.makedirs(local_bin, exist_ok=True)
        bin_name = "rtk.exe" if os.name == "nt" else "rtk"
        local_rtk = os.path.join(local_bin, bin_name)
        with open(local_rtk, "wb") as fh:
            fh.write(b"#!/bin/sh\n")
        os.chmod(local_rtk, 0o755)
        with mock.patch.dict(os.environ, {"TDQ_RTK_BIN": ""}, clear=False):
            with mock.patch("shutil.which", return_value="C:/bin/rtk.exe"):
                self.assertEqual(rtk.locate_rtk_binary(), "C:/bin/rtk.exe")
            with mock.patch("shutil.which", return_value=None), mock.patch(
                "os.path.expanduser", side_effect=lambda p: p.replace("~", home_dir)
            ):
                self.assertEqual(rtk.locate_rtk_binary(), local_rtk)

    def test_locate_rg_binary(self):
        home_dir = os.path.join(self.tmp, "home")
        local_bin = os.path.join(home_dir, ".local", "bin")
        os.makedirs(local_bin, exist_ok=True)
        bin_name = "rg.exe" if os.name == "nt" else "rg"
        local_rg = os.path.join(local_bin, bin_name)
        with open(local_rg, "wb") as fh:
            fh.write(b"#!/bin/sh\n")
        os.chmod(local_rg, 0o755)
        with mock.patch("shutil.which", return_value=None), mock.patch(
            "os.path.expanduser", side_effect=lambda p: p.replace("~", home_dir)
        ):
            self.assertEqual(rtk.locate_rg_binary(), local_rg)
        empty_home = os.path.join(self.tmp, "empty")
        with mock.patch("shutil.which", return_value=None), mock.patch(
            "os.path.expanduser", side_effect=lambda p: p.replace("~", empty_home)
        ):
            self.assertIsNone(rtk.locate_rg_binary())


class TestProbeRtk(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="tdq-rtk-probe-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.fake_bin = os.path.join(self.tmp, "rtk.exe")
        with open(self.fake_bin, "wb") as fh:
            fh.write(b"fake-rtk-v1")

    def test_missing_binary_returns_not_found(self):
        missing = os.path.join(self.tmp, "missing.exe")
        with mock.patch.dict(os.environ, {"TDQ_RTK_BIN": missing}):
            res = rtk.probe_rtk(cwd=self.tmp)
        self.assertFalse(res["valid"])
        self.assertFalse(res["collision"])
        self.assertEqual(res["reason"], "not_found")

    def test_valid_probe_uses_temp_db_and_caches_stamp(self):
        calls = []

        def fake_runner(argv, **kwargs):
            calls.append((argv, kwargs.get("env", {}).get("RTK_DB_PATH")))
            if argv[1] == "--version":
                return SimpleNamespace(returncode=0, stdout="rtk 1.2.0\n", stderr="")
            return SimpleNamespace(returncode=0, stdout="Savings: 0\n", stderr="")

        with mock.patch.dict(os.environ, {"TDQ_RTK_BIN": self.fake_bin}):
            first = rtk.probe_rtk(cwd=self.tmp, runner=fake_runner)
            second = rtk.probe_rtk(cwd=self.tmp, runner=fake_runner)

        self.assertTrue(first["valid"])
        self.assertFalse(first["cached"])
        self.assertFalse(first["collision"])
        self.assertEqual(first["version"], "1.2.0")
        self.assertEqual(len(calls), 2)
        db_path = calls[1][1]
        self.assertTrue(db_path and "tdq-rtk-gain-" in db_path)
        self.assertTrue(second["valid"])
        self.assertTrue(second["cached"])
        self.assertEqual(len(calls), 2)

        with open(self.fake_bin, "wb") as fh:
            fh.write(b"fake-rtk-v1-updated-longer")
        with mock.patch.dict(os.environ, {"TDQ_RTK_BIN": self.fake_bin}):
            third = rtk.probe_rtk(cwd=self.tmp, runner=fake_runner)
        self.assertFalse(third["cached"])
        self.assertEqual(len(calls), 4)

    def test_collision_guard_detects_rust_type_kit(self):
        def fake_typekit(argv, **kwargs):
            if argv[1] == "--version":
                return SimpleNamespace(returncode=0, stdout="rtk 1.0.0\n", stderr="")
            return SimpleNamespace(returncode=2, stdout="", stderr="unknown cmd")

        with mock.patch.dict(os.environ, {"TDQ_RTK_BIN": self.fake_bin}):
            res = rtk.probe_rtk(cwd=self.tmp, runner=fake_typekit)
        self.assertFalse(res["valid"])
        self.assertTrue(res["collision"])

    def test_old_rtk_version_rejected(self):
        def old_runner(argv, **kwargs):
            return SimpleNamespace(returncode=0, stdout="rtk 0.24.9\n", stderr="")

        with mock.patch.dict(os.environ, {"TDQ_RTK_BIN": self.fake_bin}):
            res = rtk.probe_rtk(cwd=self.tmp, runner=old_runner)
        self.assertFalse(res["valid"])
        self.assertFalse(res["collision"])

    def test_probe_timeout_fails_closed(self):
        def slow_runner(argv, **kwargs):
            raise subprocess.TimeoutExpired(argv, 2.0)

        with mock.patch.dict(os.environ, {"TDQ_RTK_BIN": self.fake_bin}):
            res = rtk.probe_rtk(cwd=self.tmp, runner=slow_runner)
        self.assertFalse(res["valid"])

    def test_gain_timeout_is_not_misclassified_as_collision(self):
        def slow_gain(argv, **kwargs):
            if argv[1] == "--version":
                return SimpleNamespace(returncode=0, stdout="rtk 1.2.0\n", stderr="")
            raise subprocess.TimeoutExpired(argv, kwargs.get("timeout", 8.0))

        with mock.patch.dict(os.environ, {"TDQ_RTK_BIN": self.fake_bin}):
            res = rtk.probe_rtk(cwd=self.tmp, runner=slow_gain)
        self.assertFalse(res["valid"])
        self.assertFalse(res["collision"])
        self.assertEqual(res["reason"], "gain_probe_failed")


class TestSkipAndRewrite(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="tdq-rtk-rw-")
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def test_skip_by_env_and_size(self):
        with mock.patch.dict(os.environ, {"TDQ_RTK": "0"}):
            self.assertTrue(rtk.should_skip_rewrite("git status")[0])
        with mock.patch.dict(os.environ, {"RTK_DISABLED": "1"}):
            self.assertTrue(rtk.should_skip_rewrite("git status")[0])
        self.assertTrue(rtk.should_skip_rewrite("   ")[0])
        self.assertTrue(rtk.should_skip_rewrite("x" * 32769)[0])

    def test_skip_tdq_scripts_and_ignore_commit_messages(self):
        cmd1 = "py -3 -X utf8 scripts/tdq_state.py next"
        cmd2 = "cd sub && python3 scripts/tdq_lsp.py check"
        cmd3 = "python3 scripts/doc_lint.py docs/"
        commit = 'git commit -m "fix scripts/tdq_state.py and git diff and pytest"'
        self.assertTrue(rtk.should_skip_rewrite(cmd1)[0])
        self.assertTrue(rtk.should_skip_rewrite(cmd2)[0])
        self.assertTrue(rtk.should_skip_rewrite(cmd3)[0])
        self.assertFalse(rtk.should_skip_rewrite(commit)[0])

    def test_skip_venv_and_python_m_pytest(self):
        self.assertTrue(rtk.should_skip_rewrite("py -3 -m pytest tests/x.py -q")[0])
        self.assertTrue(rtk.should_skip_rewrite("python -m pytest -q")[0])
        self.assertTrue(
            rtk.should_skip_rewrite(r".venv\Scripts\python.exe -m pytest -q")[0]
        )
        self.assertTrue(rtk.should_skip_rewrite(".venv/bin/pytest -q")[0])
        self.assertFalse(rtk.should_skip_rewrite("pytest -q")[0])

    def test_skip_git_diff_only_for_audit_roles(self):
        self.assertTrue(
            rtk.should_skip_rewrite("git diff HEAD~1", role="tdq-qc-tester")[0]
        )
        self.assertTrue(
            rtk.should_skip_rewrite("git -C repo diff", role="tdq-security-reviewer")[0]
        )
        self.assertTrue(
            rtk.should_skip_rewrite("git diff", role="tdq-reviewer")[0]
        )
        self.assertFalse(
            rtk.should_skip_rewrite("git status", role="tdq-qc-tester")[0]
        )
        self.assertFalse(
            rtk.should_skip_rewrite("git diff HEAD~1", role="implementer")[0]
        )

    def test_can_compress_dump_command(self):
        def valid_probe(cwd=None):
            return {"valid": True, "path": "/bin/rtk", "version": "1.2.0"}

        def bad_probe(cwd=None):
            return {"valid": False, "path": "", "version": ""}

        self.assertTrue(
            rtk.can_compress_dump_command("git log -n 20", probe_fn=valid_probe)
        )
        self.assertTrue(
            rtk.can_compress_dump_command("git diff HEAD~1", probe_fn=valid_probe)
        )
        self.assertTrue(
            rtk.can_compress_dump_command("git show HEAD", probe_fn=valid_probe)
        )
        self.assertFalse(
            rtk.can_compress_dump_command("git status", probe_fn=valid_probe)
        )
        self.assertFalse(
            rtk.can_compress_dump_command(
                "git diff HEAD~1", role="tdq-qc-tester", probe_fn=valid_probe
            )
        )
        self.assertFalse(
            rtk.can_compress_dump_command("git log -n 20", probe_fn=bad_probe)
        )

    def test_rewrite_command_accepts_rc_0_and_3_and_fails_open(self):
        def probe_ok(cwd=None):
            return {"valid": True, "path": "C:/bin/rtk.exe", "version": "1.2.0"}

        for rc in (0, 3):
            def ok_runner(argv, _rc=rc, **kw):
                return SimpleNamespace(
                    returncode=_rc, stdout="rtk git status\n", stderr=""
                )

            with mock.patch("shutil.which", return_value="C:/bin/rtk.exe"):
                out, changed, _ = rtk.rewrite_command(
                    "git status", runner=ok_runner, probe_fn=probe_ok
                )
            self.assertTrue(changed)
            self.assertEqual(out, "rtk git status")

        def rc1_runner(argv, **kw):
            return SimpleNamespace(returncode=1, stdout="", stderr="")

        out, changed, _ = rtk.rewrite_command(
            "git status", runner=rc1_runner, probe_fn=probe_ok
        )
        self.assertFalse(changed)
        self.assertEqual(out, "git status")

        def boom(argv, **kw):
            raise subprocess.TimeoutExpired(argv, 2.0)

        out, changed, _ = rtk.rewrite_command(
            "git status", runner=boom, probe_fn=probe_ok
        )
        self.assertFalse(changed)
        self.assertEqual(out, "git status")

    def test_powershell_qualifies_rtk_with_spaces_when_not_on_path(self):
        bin_space = r"C:\Users\My Name\.local\bin\rtk.exe"

        def probe_ok(cwd=None):
            return {"valid": True, "path": bin_space, "version": "1.2.0"}

        def runner(argv, **kw):
            return SimpleNamespace(
                returncode=0,
                stdout="cd sub && rtk git status; echo 'rtk literal'\n",
                stderr="",
            )

        with mock.patch("sys.platform", "win32"), mock.patch(
            "shutil.which", return_value=None
        ):
            out, changed, _ = rtk.rewrite_command(
                "cd sub && git status; echo 'rtk literal'",
                runner=runner,
                probe_fn=probe_ok,
            )
        self.assertTrue(changed)
        expected = f"cd sub && & '{bin_space}' git status; echo 'rtk literal'"
        self.assertEqual(out, expected)


class TestConfigAndInstaller(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="tdq-rtk-inst-")
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def test_default_config_paths_per_os(self):
        win_env = {"APPDATA": r"C:\Users\u\AppData\Roaming"}
        with mock.patch("sys.platform", "win32"), mock.patch.dict(os.environ, win_env):
            cfg_win = rtk.default_rtk_config_path()
            self.assertTrue(cfg_win.endswith(os.path.join("rtk", "config.toml")))
        with mock.patch("sys.platform", "darwin"), mock.patch(
            "os.path.expanduser", return_value="/Users/u"
        ):
            expected_mac = os.path.join(
                "/Users/u", "Library", "Application Support", "rtk", "config.toml"
            )
            self.assertEqual(rtk.default_rtk_config_path(), expected_mac)
        with mock.patch("sys.platform", "linux"), mock.patch.dict(
            os.environ, {"XDG_CONFIG_HOME": "/home/u/.cfg"}
        ):
            self.assertEqual(
                rtk.default_rtk_config_path(),
                os.path.join("/home/u/.cfg", "rtk", "config.toml"),
            )

    def test_ensure_rtk_config_creates_and_preserves_user_keys_with_backup(self):
        cfg = os.path.join(self.tmp, "rtk", "config.toml")
        ok, _ = rtk.ensure_rtk_config(cfg)
        self.assertTrue(ok)
        text = Path(cfg).read_text(encoding="utf-8")
        for expected in (
            "enabled = false",
            "pro_hint = false",
            "emoji = false",
            "colors = false",
            "max_width = 120",
            'mode = "sqlite"',
            'level = "default"',
            "suppress_hook_warning = true",
            '"grep"',
            '"rg"',
        ):
            self.assertIn(expected, text)

        custom_cfg = os.path.join(self.tmp, "custom", "config.toml")
        os.makedirs(os.path.dirname(custom_cfg), exist_ok=True)
        orig = (
            "# user comment\n"
            "[telemetry]\n"
            "enabled = true\n\n"
            "[display]\n"
            "colors = true\n"
            "max_width = 100\n\n"
            "[hooks]\n"
            'exclude_commands = ["ls"]\n\n'
            "[user_extra]\n"
            'theme = "dark"\n'
        )
        Path(custom_cfg).write_text(orig, encoding="utf-8")
        ok2, _ = rtk.ensure_rtk_config(custom_cfg)
        self.assertTrue(ok2)
        updated_custom = Path(custom_cfg).read_text(encoding="utf-8")
        self.assertIn("colors = true", updated_custom)
        self.assertIn("max_width = 100", updated_custom)
        bak_text = Path(custom_cfg + ".truoc-tdq.bak").read_text(encoding="utf-8")
        self.assertEqual(bak_text, orig)
        merged = Path(custom_cfg).read_text(encoding="utf-8")
        self.assertIn("enabled = false", merged)
        self.assertNotIn("enabled = true", merged)
        self.assertIn("[user_extra]", merged)
        self.assertIn('theme = "dark"', merged)
        self.assertIn('"ls"', merged)
        self.assertIn('"grep"', merged)
        self.assertIn('"rg"', merged)

    def test_install_refuses_without_approve_or_under_khong_cham_may(self):
        res = rtk.install_rtk_and_rg(approve=False, bin_dir=self.tmp)
        self.assertFalse(res["ok"])
        with mock.patch.dict(os.environ, {"TDQ_KHONG_CHAM_MAY": "1"}):
            res2 = rtk.install_rtk_and_rg(approve=True, bin_dir=self.tmp)
        self.assertFalse(res2["ok"])
        self.assertIn("TDQ_KHONG_CHAM_MAY", res2["reason"])

    def test_install_verifies_sha256_and_rejects_mismatch(self):
        rtk_zip = _make_zip_archive("rtk.exe", b"RTK_BIN")
        rg_zip = _make_zip_archive("ripgrep-15.2.0/rg.exe", b"RG_BIN")
        rtk_sha = hashlib.sha256(rtk_zip).hexdigest()
        rg_sha = hashlib.sha256(rg_zip).hexdigest()
        rtk_asset = "rtk-x86_64-pc-windows-msvc.zip"
        rg_asset = "ripgrep-15.2.0-x86_64-pc-windows-msvc.zip"
        store = {
            rtk.RTK_RELEASE_API: json.dumps({
                "tag_name": "v1.2.0",
                "assets": [
                    {"name": rtk_asset, "browser_download_url": "https://x/rtk.zip"},
                    {"name": "checksums.txt", "browser_download_url": "https://x/rtk.sum"},
                ],
            }).encode(),
            "https://x/rtk.zip": rtk_zip,
            "https://x/rtk.sum": f"{rtk_sha}  {rtk_asset}\n".encode(),
            rtk.RG_RELEASE_API: json.dumps({
                "tag_name": "15.2.0",
                "assets": [
                    {
                        "name": rg_asset,
                        "browser_download_url": "https://x/rg.zip",
                        "digest": f"sha256:{rg_sha}",
                    },
                ],
            }).encode(),
            "https://x/rg.zip": rg_zip,
        }
        bin_dir = os.path.join(self.tmp, "bin")
        cfg_path = os.path.join(self.tmp, "cfg", "config.toml")
        with mock.patch("sys.platform", "win32"), mock.patch(
            "platform.machine", return_value="AMD64"
        ):
            ok_res = rtk.install_rtk_and_rg(
                approve=True,
                bin_dir=bin_dir,
                config_path=cfg_path,
                fetcher=store.__getitem__,
                update_path=False,
            )
        self.assertTrue(ok_res["ok"], ok_res)
        self.assertEqual(
            Path(os.path.join(bin_dir, "rtk.exe")).read_bytes(), b"RTK_BIN"
        )
        self.assertEqual(Path(os.path.join(bin_dir, "rg.exe")).read_bytes(), b"RG_BIN")
        self.assertTrue(os.path.isfile(cfg_path))

        bad_bin = os.path.join(self.tmp, "bad_bin")
        bad_store = dict(store)
        bad_store["https://x/rtk.sum"] = f"{'0' * 64}  {rtk_asset}\n".encode()
        with mock.patch("sys.platform", "win32"), mock.patch(
            "platform.machine", return_value="AMD64"
        ):
            bad_res = rtk.install_rtk_and_rg(
                approve=True,
                bin_dir=bad_bin,
                config_path=cfg_path,
                fetcher=bad_store.__getitem__,
                update_path=False,
            )
        self.assertFalse(bad_res["ok"])
        self.assertFalse(os.path.exists(os.path.join(bad_bin, "rtk.exe")))

    def test_install_oss_edition_on_linux_tar_gz(self):
        rtk_tgz = _make_tar_gz_archive("rtk", b"RTK_ELF")
        rg_tgz = _make_tar_gz_archive("ripgrep/rg", b"RG_ELF")
        rtk_sha = hashlib.sha256(rtk_tgz).hexdigest()
        rg_sha = hashlib.sha256(rg_tgz).hexdigest()
        rtk_asset = "rtk-oss-x86_64-unknown-linux-musl.tar.gz"
        rg_asset = "ripgrep-15.2.0-x86_64-unknown-linux-musl.tar.gz"
        store = {
            rtk.RTK_RELEASE_API: json.dumps({
                "tag_name": "v1.2.0",
                "assets": [
                    {"name": rtk_asset, "browser_download_url": "https://x/rtk.tgz"},
                    {"name": "checksums.txt", "browser_download_url": "https://x/rtk.sum"},
                ],
            }).encode(),
            "https://x/rtk.tgz": rtk_tgz,
            "https://x/rtk.sum": f"{rtk_sha}  {rtk_asset}\n".encode(),
            rtk.RG_RELEASE_API: json.dumps({
                "tag_name": "15.2.0",
                "assets": [
                    {"name": rg_asset, "browser_download_url": "https://x/rg.tgz"},
                    {
                        "name": f"{rg_asset}.sha256",
                        "browser_download_url": "https://x/rg.sha256",
                    },
                ],
            }).encode(),
            "https://x/rg.tgz": rg_tgz,
            "https://x/rg.sha256": f"{rg_sha}  {rg_asset}\n".encode(),
        }
        bin_dir = os.path.join(self.tmp, "linux_bin")
        cfg_path = os.path.join(self.tmp, "linux_cfg", "config.toml")
        with mock.patch("sys.platform", "linux"), mock.patch(
            "platform.machine", return_value="x86_64"
        ):
            res = rtk.install_rtk_and_rg(
                approve=True,
                edition="oss",
                bin_dir=bin_dir,
                config_path=cfg_path,
                fetcher=store.__getitem__,
                update_path=False,
            )
        self.assertTrue(res["ok"], res)
        self.assertEqual(Path(os.path.join(bin_dir, "rtk")).read_bytes(), b"RTK_ELF")
        self.assertEqual(Path(os.path.join(bin_dir, "rg")).read_bytes(), b"RG_ELF")

    def test_windows_user_path_helper_with_mocked_registry(self):
        state = {"Path": r"C:\Windows\System32"}
        notified = []

        class FakeKey:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        class FakeWinreg:
            HKEY_CURRENT_USER = 1
            KEY_READ = 2
            KEY_SET_VALUE = 4
            REG_EXPAND_SZ = 2

            def OpenKey(self, root, subkey, reserved, access):
                return FakeKey()

            def QueryValueEx(self, key, name):
                if name not in state:
                    raise FileNotFoundError(name)
                return state[name], self.REG_EXPAND_SZ

            def SetValueEx(self, key, name, reserved, typ, value):
                state[name] = value

        fake_reg = FakeWinreg()
        target = r"C:\Users\admin\.local\bin"
        added = rtk.ensure_windows_user_path(
            target, reg_module=fake_reg, notify_fn=lambda: notified.append(1)
        )
        self.assertTrue(added)
        self.assertIn(target, state["Path"])
        self.assertEqual(len(notified), 1)
        again = rtk.ensure_windows_user_path(
            target, reg_module=fake_reg, notify_fn=lambda: notified.append(1)
        )
        self.assertFalse(again)


class TestMutePrefsAndLogging(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="tdq-rtk-prefs-")
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def test_mute_prefs_roundtrip(self):
        prefs = os.path.join(self.tmp, "tdq-rtk-prefs.json")
        self.assertFalse(rtk.is_prompt_muted(prefs))
        out_path = rtk.set_prompt_muted(True, prefs)
        self.assertEqual(Path(out_path), Path(prefs))
        self.assertTrue(rtk.is_prompt_muted(prefs))
        rtk.set_prompt_muted(False, prefs)
        self.assertFalse(rtk.is_prompt_muted(prefs))

    def test_logging_on_by_default_and_silenced_by_tdq_log_0(self):
        prefs = os.path.join(self.tmp, "prefs.json")
        err_on = io.StringIO()
        with mock.patch.dict(os.environ, {"TDQ_LOG": "1"}), mock.patch(
            "sys.stderr", err_on
        ):
            rtk.set_prompt_muted(True, prefs)
        self.assertIn("rtk_integration:", err_on.getvalue())

        err_off = io.StringIO()
        with mock.patch.dict(os.environ, {"TDQ_LOG": "0"}), mock.patch(
            "sys.stderr", err_off
        ):
            rtk.set_prompt_muted(False, prefs)
        self.assertEqual(err_off.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
