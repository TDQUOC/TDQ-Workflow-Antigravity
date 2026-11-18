#!/usr/bin/env python3
"""Unit and CLI tests for scripts/tdq_ccr.py (lossless CCR store & summaries)."""

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import tdq_ccr


def _total_store_bytes(store_dir: Path) -> int:
    return sum(p.stat().st_size for p in store_dir.iterdir() if p.is_file())


class TestTdqCcr(unittest.TestCase):
    """Verify lossless storage, SHA-256 checks, cap rotation, summaries, and CLI."""

    def test_threshold_detection(self):
        small = b"a" * 32768
        self.assertFalse(tdq_ccr.should_ccr(small))
        over_bytes = b"a" * 32769
        self.assertTrue(tdq_ccr.should_ccr(over_bytes))
        many_lines = b"\n".join(b"x" for _ in range(200))
        self.assertTrue(tdq_ccr.should_ccr(many_lines))
        under_lines = b"\n".join(b"x" for _ in range(199))
        self.assertFalse(tdq_ccr.should_ccr(under_lines))

    def test_ingest_and_retrieve_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            store_dir = Path(tmp) / "ccr"
            payload = ("line\n" * 250).encode("utf-8")
            rec = tdq_ccr.ingest_bytes(payload, source_path="big.txt", store_dir=store_dir)
            self.assertEqual(rec["id"], rec["sha256"][:12])
            restored = tdq_ccr.retrieve_record(rec["id"], store_dir=store_dir)
            self.assertEqual(restored, payload)
            self.assertEqual(hashlib.sha256(restored).hexdigest(), rec["sha256"])

    def test_binary_and_broken_utf8_lossless(self):
        with tempfile.TemporaryDirectory() as tmp:
            store_dir = Path(tmp) / "ccr"
            broken = b"hdr\xff\xfe\x00\x80\x81tail\xc3\x28\nERROR boom\n"
            rec = tdq_ccr.ingest_bytes(broken, source_path="raw.bin", store_dir=store_dir)
            self.assertEqual(tdq_ccr.retrieve_record(rec["id"], store_dir=store_dir), broken)

            bad_log = Path(tmp) / "broken.log"
            bad_log.write_bytes(b"2026-01-01 INFO ok\n\xff\xfeERROR corrupt\xc3\x28\n")
            summary = tdq_ccr.summarize_file(str(bad_log), store_dir=store_dir)
            self.assertIn("CCR_ID=", summary)
            self.assertIn("errors=1", summary)

    def test_tampered_raw_and_missing_record_raise_value_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            store_dir = Path(tmp) / "ccr"
            rec = tdq_ccr.ingest_bytes(b"original bytes", source_path="a.txt", store_dir=store_dir)
            raw_path = store_dir / f"{rec['id']}.raw"
            raw_path.write_bytes(b"tampered bytes")
            with self.assertRaises(ValueError):
                tdq_ccr.retrieve_record(rec["id"], store_dir=store_dir)
            with self.assertRaises(ValueError):
                tdq_ccr.retrieve_record("deadbeef0000", store_dir=store_dir)
            with self.assertRaises(ValueError):
                tdq_ccr.retrieve_record("../escape", store_dir=store_dir)

    def test_enforce_cap_evicts_oldest_by_mtime(self):
        with tempfile.TemporaryDirectory() as tmp:
            store_dir = Path(tmp) / "ccr"
            recs = []
            for idx in range(4):
                payload = f"record-{idx}-".encode("ascii") + (b"x" * 300)
                rec = tdq_ccr.ingest_bytes(payload, source_path=f"f{idx}.txt", store_dir=store_dir)
                recs.append(rec)
                ts = 1_700_000_000 + idx * 100
                os.utime(store_dir / f"{rec['id']}.raw", (ts, ts))
                os.utime(store_dir / f"{rec['id']}.meta.json", (ts, ts))

            cap_bytes = 1200
            evicted = tdq_ccr.enforce_cap(store_dir, cap_bytes)
            self.assertTrue(len(evicted) >= 1)
            self.assertIn(recs[0]["id"], evicted)
            total_after = _total_store_bytes(store_dir)
            self.assertLessEqual(total_after, cap_bytes)
            with self.assertRaises(ValueError):
                tdq_ccr.retrieve_record(recs[0]["id"], store_dir=store_dir)
            newest = tdq_ccr.retrieve_record(recs[-1]["id"], store_dir=store_dir)
            self.assertTrue(newest.startswith(b"record-3-"))

    def test_summarize_json_and_invalid_json_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            store_dir = Path(tmp) / "ccr"
            valid_path = Path(tmp) / "items.json"
            data = {
                "meta": {"version": 2, "source": "sensor"},
                "items": [{"id": i, "name": f"n{i}"} for i in range(6)],
            }
            valid_path.write_text(json.dumps(data), encoding="utf-8")
            summary = tdq_ccr.summarize_file(str(valid_path), store_dir=store_dir)
            self.assertIn("kind=json", summary)
            self.assertIn("items", summary)
            self.assertIn("CCR_ID=", summary)
            self.assertIn("retrieve: py -3 scripts/tdq_ccr.py retrieve ", summary)

            invalid_path = Path(tmp) / "broken.json"
            invalid_bytes = b'{"a": 1,\n"b": [broken\n}\n'
            invalid_path.write_bytes(invalid_bytes)
            fallback = tdq_ccr.summarize_file(str(invalid_path), store_dir=store_dir)
            self.assertIn("CCR_ID=", fallback)
            self.assertIn("head:", fallback)
            rid = fallback.split("CCR_ID=")[1].split()[0]
            self.assertEqual(tdq_ccr.retrieve_record(rid, store_dir=store_dir), invalid_bytes)

    def test_summarize_jsonl_csv_log_yaml_dom(self):
        with tempfile.TemporaryDirectory() as tmp:
            store_dir = Path(tmp) / "ccr"

            jsonl_p = Path(tmp) / "events.jsonl"
            jsonl_p.write_text(
                "\n".join(json.dumps({"ts": i, "ok": True}) for i in range(5)) + "\n",
                encoding="utf-8",
            )
            s_jsonl = tdq_ccr.summarize_file(str(jsonl_p), store_dir=store_dir)
            self.assertIn("kind=jsonl", s_jsonl)
            self.assertIn("records=5", s_jsonl)

            csv_p = Path(tmp) / "rows.csv"
            csv_rows = ["id,name,score"] + [f"{i},user{i},{i * 10}" for i in range(8)]
            csv_p.write_text("\n".join(csv_rows) + "\n", encoding="utf-8")
            s_csv = tdq_ccr.summarize_file(str(csv_p), store_dir=store_dir)
            self.assertIn("kind=csv", s_csv)
            self.assertIn("rows=8", s_csv)
            self.assertIn("user4", s_csv)

            log_p = Path(tmp) / "app.log"
            log_p.write_text(
                "INFO start\nWARN low disk\nERROR failed open\nERROR timeout\nINFO end\n",
                encoding="utf-8",
            )
            s_log = tdq_ccr.summarize_file(str(log_p), store_dir=store_dir)
            self.assertIn("kind=log", s_log)
            self.assertIn("errors=2", s_log)
            self.assertIn("warns=1", s_log)

            yaml_p = Path(tmp) / "cfg.yaml"
            yaml_p.write_text(
                "server:\n  host: localhost\n  port: 8080\nroutes:\n  - /api\n  - /health\n",
                encoding="utf-8",
            )
            s_yaml = tdq_ccr.summarize_file(str(yaml_p), store_dir=store_dir)
            self.assertIn("kind=yaml", s_yaml)
            self.assertIn("server", s_yaml)

            dom_p = Path(tmp) / "page.html"
            dom_p.write_text(
                "<html><head><title>Demo</title></head>"
                "<body><main id='app'><div class='card'>A</div><p>B</p></main></body></html>",
                encoding="utf-8",
            )
            s_dom = tdq_ccr.summarize_file(str(dom_p), store_dir=store_dir)
            self.assertIn("kind=dom", s_dom)
            self.assertIn("Demo", s_dom)

    def test_cli_workflow_and_tdq_log_mute(self):
        with tempfile.TemporaryDirectory() as tmp:
            store_dir = Path(tmp) / "ccr_cli"
            src = Path(tmp) / "payload.bin"
            raw = b"\x00\x01\xffCCR-CLI-TEST\xfe\n"
            src.write_bytes(raw)

            env_logged = {**os.environ, "TDQ_LOG": "1"}
            proc_ing = subprocess.run(
                [sys.executable, str(SCRIPTS_DIR / "tdq_ccr.py"),
                 "--store-dir", str(store_dir), "ingest", str(src)],
                capture_output=True, text=True, encoding="utf-8", env=env_logged, check=True,
            )
            meta = json.loads(proc_ing.stdout)
            self.assertEqual(meta["sha256"], hashlib.sha256(raw).hexdigest())
            self.assertIn("tdq_ccr:", proc_ing.stderr)

            env_muted = {**os.environ, "TDQ_LOG": "0"}
            proc_ret = subprocess.run(
                [sys.executable, str(SCRIPTS_DIR / "tdq_ccr.py"),
                 "--store-dir", str(store_dir), "retrieve", meta["id"]],
                capture_output=True, env=env_muted, check=True,
            )
            self.assertEqual(proc_ret.stdout, raw)
            self.assertEqual(proc_ret.stderr, b"")

            (store_dir / f"{meta['id']}.raw").write_bytes(b"corrupted")
            proc_bad = subprocess.run(
                [sys.executable, str(SCRIPTS_DIR / "tdq_ccr.py"),
                 "--store-dir", str(store_dir), "retrieve", meta["id"]],
                check=False, capture_output=True, env=env_muted,
            )
            self.assertNotEqual(proc_bad.returncode, 0)

            proc_sum = subprocess.run(
                [sys.executable, str(SCRIPTS_DIR / "tdq_ccr.py"),
                 "summarize", str(src), "--store-dir", str(store_dir)],
                capture_output=True, text=True, encoding="utf-8", env=env_muted, check=True,
            )
            self.assertIn("CCR_ID=", proc_sum.stdout)

            proc_gc = subprocess.run(
                [sys.executable, str(SCRIPTS_DIR / "tdq_ccr.py"),
                 "--store-dir", str(store_dir), "gc", "--cap-bytes", "0"],
                capture_output=True, text=True, encoding="utf-8", env=env_muted, check=True,
            )
            gc_res = json.loads(proc_gc.stdout)
            self.assertIn(meta["id"], gc_res["evicted"])


if __name__ == "__main__":
    unittest.main()
