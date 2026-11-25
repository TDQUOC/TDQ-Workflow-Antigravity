"""Unit tests for scripts/tdq_lease.py and scripts/defaults/mcp-policy.default.json."""
from __future__ import annotations

import ast
import importlib
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
tdq_lease = importlib.import_module("tdq_lease")

ISO_LOG_RE = re.compile(r"^\[([^\]]+)\]\s+tdq_lease:\s+")


class TestSidecarLock(unittest.TestCase):
    def test_sidecar_lock_path_preserves_existing_extension(self):
        target = Path("docs") / "tdq" / "state.json"
        self.assertEqual(
            tdq_lease.sidecar_lock_path(target),
            Path(f"{target}.lock"),
        )
        self.assertEqual(
            tdq_lease.sidecar_lock_path("sample.jsonl"),
            Path("sample.jsonl.lock"),
        )

    def test_sidecar_lock_mutual_exclusion_and_keeps_anchor_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "nested" / "pending.jsonl"
            lock_path = tdq_lease.sidecar_lock_path(target)
            entered = threading.Event()
            release = threading.Event()
            completed = False

            def holder():
                nonlocal completed
                with tdq_lease.acquire_sidecar_lock(
                    target, timeout_sec=1.0, poll_interval=0.005
                ):
                    entered.set()
                    release.wait(timeout=2.0)
                completed = True

            worker = threading.Thread(target=holder)
            worker.start()
            self.assertTrue(entered.wait(timeout=1.0))

            with (
                self.assertRaises(TimeoutError),
                tdq_lease.acquire_sidecar_lock(
                    target, timeout_sec=0.06, poll_interval=0.005
                ),
            ):
                pass

            release.set()
            worker.join(timeout=2.0)
            self.assertTrue(completed)

            self.assertTrue(
                lock_path.exists(),
                "sidecar .lock anchor must remain on disk after unlock",
            )

            with tdq_lease.acquire_sidecar_lock(
                target, timeout_sec=0.5, poll_interval=0.005
            ):
                self.assertTrue(lock_path.exists())
            self.assertTrue(lock_path.exists())


class TestLeaseLifecycle(unittest.TestCase):
    def test_acquire_lease_o_excl_race_single_winner(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            n_threads = 10
            barrier = threading.Barrier(n_threads)
            winners: list[dict] = []
            conflicts: list[FileExistsError] = []
            lock = threading.Lock()

            def racer(idx: int):
                barrier.wait(timeout=2.0)
                try:
                    lease = tdq_lease.acquire_lease(
                        cwd, "race-lease", f"owner-{idx}", ttl_sec=120
                    )
                    with lock:
                        winners.append(lease)
                except FileExistsError as exc:
                    with lock:
                        conflicts.append(exc)

            threads = [
                threading.Thread(target=racer, args=(i,)) for i in range(n_threads)
            ]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=5.0)

            self.assertEqual(len(winners), 1)
            self.assertEqual(len(conflicts), n_threads - 1)

            winner = winners[0]
            for key in (
                "lease_id",
                "owner",
                "acquired_at",
                "expires_at",
                "expires_at_iso",
                "ttl_sec",
            ):
                self.assertIn(key, winner)
            self.assertEqual(winner["lease_id"], "race-lease")
            self.assertEqual(winner["ttl_sec"], 120)
            parsed_iso = datetime.fromisoformat(winner["expires_at_iso"])
            self.assertIsNotNone(parsed_iso.tzinfo)

    def test_acquire_lease_rejects_existing_even_when_expired(self):
        with tempfile.TemporaryDirectory() as tmp:
            tdq_lease.acquire_lease(tmp, "expired-one", "owner-a", ttl_sec=-5)
            with self.assertRaises(FileExistsError):
                tdq_lease.acquire_lease(tmp, "expired-one", "owner-b", ttl_sec=60)

    def test_lease_id_sanitization_prevents_traversal(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            lease = tdq_lease.acquire_lease(
                cwd, "../../outside/escape", "owner-a", ttl_sec=60
            )
            self.assertEqual(lease["lease_id"], "../../outside/escape")
            leases_dir = (cwd / "docs" / "tdq" / "leases").resolve()
            files = [p for p in leases_dir.iterdir() if p.suffix == ".json"]
            self.assertEqual(len(files), 1)
            self.assertEqual(files[0].resolve().parent, leases_dir)
            self.assertFalse((cwd / "outside").exists())

            for bad_id in ("", "   ", "..", ".", "///"):
                with self.assertRaises(ValueError):
                    tdq_lease.acquire_lease(cwd, bad_id, "owner-a", ttl_sec=60)

    def test_renew_lease_success_and_rejections(self):
        with tempfile.TemporaryDirectory() as tmp:
            created = tdq_lease.acquire_lease(tmp, "renew-1", "owner-a", ttl_sec=30)
            time.sleep(0.02)
            renewed = tdq_lease.renew_lease(tmp, "renew-1", "owner-a", ttl_sec=300)
            self.assertEqual(renewed["acquired_at"], created["acquired_at"])
            self.assertGreater(renewed["expires_at"], created["expires_at"])
            self.assertEqual(renewed["ttl_sec"], 300)

            with self.assertRaises(PermissionError):
                tdq_lease.renew_lease(tmp, "renew-1", "owner-b", ttl_sec=300)

            with self.assertRaises(FileNotFoundError):
                tdq_lease.renew_lease(tmp, "missing-lease", "owner-a", ttl_sec=300)

            tdq_lease.acquire_lease(tmp, "expired-renew", "owner-a", ttl_sec=-1)
            with self.assertRaises(TimeoutError):
                tdq_lease.renew_lease(tmp, "expired-renew", "owner-a", ttl_sec=300)

    def test_release_or_reclaim_respects_owner_and_expiry(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.assertFalse(tdq_lease.release_or_reclaim(cwd, "missing", owner="a"))

            tdq_lease.acquire_lease(cwd, "active-lease", "owner-a", ttl_sec=120)
            self.assertFalse(
                tdq_lease.release_or_reclaim(
                    cwd, "active-lease", owner="owner-b", force_expired=True
                )
            )
            lease_file = cwd / "docs" / "tdq" / "leases" / "active-lease.json"
            self.assertTrue(lease_file.exists())

            self.assertTrue(
                tdq_lease.release_or_reclaim(cwd, "active-lease", owner="owner-a")
            )
            self.assertFalse(lease_file.exists())
            self.assertTrue(tdq_lease.sidecar_lock_path(lease_file).exists())

            tdq_lease.acquire_lease(cwd, "stale-lease", "owner-a", ttl_sec=-2)
            stale_file = cwd / "docs" / "tdq" / "leases" / "stale-lease.json"
            self.assertFalse(
                tdq_lease.release_or_reclaim(
                    cwd, "stale-lease", owner="owner-b", force_expired=False
                )
            )
            self.assertTrue(stale_file.exists())

            self.assertTrue(
                tdq_lease.release_or_reclaim(cwd, "stale-lease", force_expired=True)
            )
            self.assertFalse(stale_file.exists())
            self.assertTrue(tdq_lease.sidecar_lock_path(stale_file).exists())

            reacquired = tdq_lease.acquire_lease(
                cwd, "stale-lease", "owner-b", ttl_sec=60
            )
            self.assertEqual(reacquired["owner"], "owner-b")

    def test_release_or_reclaim_corrupt_json_fail_safe(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            leases_dir = cwd / "docs" / "tdq" / "leases"
            leases_dir.mkdir(parents=True, exist_ok=True)
            corrupt = leases_dir / "corrupt.json"
            corrupt.write_text("{not-valid-json", encoding="utf-8")

            self.assertFalse(
                tdq_lease.release_or_reclaim(cwd, "corrupt", force_expired=True)
            )
            self.assertTrue(corrupt.exists())


class TestCliLoggingAndPolicyDefaults(unittest.TestCase):
    def _run_cli(self, args: list[str], tdq_log: str) -> subprocess.CompletedProcess:
        env = dict(os.environ)
        env["TDQ_LOG"] = tdq_log
        return subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "tdq_lease.py"), *args],
            check=False,
            capture_output=True,
            env=env,
            timeout=15,
        )

    def test_cli_status_and_reclaim_logging_toggle(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            tdq_lease.acquire_lease(cwd, "keep-me", "owner-a", ttl_sec=120)
            tdq_lease.acquire_lease(cwd, "drop-me", "owner-b", ttl_sec=-5)

            proc_on = self._run_cli(["status", "--cwd", str(cwd)], tdq_log="1")
            self.assertEqual(proc_on.returncode, 0, proc_on.stderr)
            payload = json.loads(proc_on.stdout.decode("utf-8"))
            self.assertEqual(payload["count"], 2)

            stderr_text = proc_on.stderr.decode("utf-8").strip()
            self.assertTrue(stderr_text)
            first_line = stderr_text.splitlines()[0]
            match = ISO_LOG_RE.match(first_line)
            self.assertIsNotNone(match, f"Bad log format: {first_line!r}")
            stamp = datetime.fromisoformat(match.group(1))
            self.assertIsNotNone(stamp.tzinfo)

            proc_off = self._run_cli(["reclaim", "--cwd", str(cwd)], tdq_log="0")
            self.assertEqual(proc_off.returncode, 0, proc_off.stderr)
            self.assertEqual(proc_off.stderr, b"")
            reclaimed = json.loads(proc_off.stdout.decode("utf-8"))
            self.assertEqual(reclaimed["reclaimed"], ["drop-me"])
            self.assertEqual(reclaimed["count"], 1)
            leases_dir = cwd / "docs" / "tdq" / "leases"
            self.assertTrue((leases_dir / "keep-me.json").exists())
            self.assertFalse((leases_dir / "drop-me.json").exists())

    def test_default_mcp_policy_json_contract(self):
        policy_path = SCRIPTS_DIR / "defaults" / "mcp-policy.default.json"
        raw = policy_path.read_text(encoding="utf-8")
        raw.encode("ascii")
        data = json.loads(raw)
        self.assertEqual(data["schema_version"], 1)
        self.assertEqual(data["mode"], "balanced")
        self.assertIn("tdq-lsp", data["trusted_servers"])
        self.assertIn("read_", data["read_prefixes"])
        self.assertIn("write_", data["write_prefixes"])
        self.assertEqual(data["approved_tools"], {})

    def test_zero_imports_from_hooks(self):
        src = (SCRIPTS_DIR / "tdq_lease.py").read_text(encoding="utf-8")
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertNotIn("hooks", alias.name)
                    self.assertNotEqual(alias.name, "_common")
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                self.assertNotIn("hooks", mod)
                self.assertNotEqual(mod, "_common")


if __name__ == "__main__":
    unittest.main()
