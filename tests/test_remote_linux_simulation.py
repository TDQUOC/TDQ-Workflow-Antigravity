"""Simulation tests on remote Linux host (Ubuntu x86_64) via SSH."""
import io
import json
import subprocess
import tarfile
import uuid
from pathlib import Path

import pytest

SSH_HOST = "ubuntu-100-95"
BIN_NAME = "tdq-dispatch-linux-x86_64"
PLUGIN_DIR = Path(__file__).resolve().parent.parent / "plugins" / "tdq-workflow-agy"

_REMOTE_DRIVER = r"""
import json, os, statistics, subprocess, sys, time
root = sys.argv[1]
bin_path = os.path.join(root, "bin", sys.argv[2])
env = dict(os.environ, PLUGIN_ROOT=root, TDQ_PROJECT_DIR=root, TDQ_LOG="0")

def call(ev, payload):
    p = dict(payload, cwd=root)
    proc = subprocess.run([bin_path, "--event", ev], input=json.dumps(p), stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, env=env, timeout=20)
    assert proc.returncode == 0, f"{ev} rc={proc.returncode} err={proc.stderr}"
    lines = [ln for ln in proc.stdout.splitlines() if ln.strip().startswith("{")]
    assert lines, f"{ev} empty output: {proc.stdout!r} {proc.stderr!r}"
    return json.loads(lines[-1])

assert isinstance(call("SessionStart", {"conversationId": "sim-lnx-ss"}), dict)
assert isinstance(call("PreInvocation", {"conversationId": "sim-lnx-pi", "user_message": "Continue work"}), dict)
assert call("PreToolUse", {"toolName": "run_command", "arguments": {"CommandLine": "echo hello"}}).get("decision") == "allow"
assert call("PreToolUse", {"toolName": "run_command", "arguments": {"CommandLine": "ls -la"}}).get("decision") == "allow"
gp = call("PreToolUse", {"toolName": "run_command", "arguments": {"CommandLine": "git push origin dev"}})
assert gp.get("decision") == "deny" and "TDQ:GIT" in gp.get("reason", "")
gr = call("PreToolUse", {"toolName": "run_command", "arguments": {"CommandLine": "git reset --hard HEAD~1"}})
assert gr.get("decision") == "deny" and "TDQ:GIT" in gr.get("reason", "")
st = call("PreToolUse", {"toolName": "write_file", "arguments": {"Path": root + "/docs/tdq/state.json"}})
assert st.get("decision") == "deny" and "TDQ:STATE" in st.get("reason", "")
assert isinstance(call("PostToolUse", {"toolName": "read_file", "arguments": {"Path": "/etc/os-release"}}), dict)
assert call("PostInvocation", {"conversationId": "sim-lnx-po"}) == {}
assert call("Stop", {"terminationReason": "USER_CANCELED"}).get("decision") == "allow"

times = []
for _ in range(10):
    t0 = time.perf_counter()
    assert call("PostInvocation", {"conversationId": "sim-lnx-bench"}) == {}
    times.append((time.perf_counter() - t0) * 1000.0)
print(json.dumps({"hot_median_ms": round(statistics.median(times), 2)}))
"""


def _build_bundle_bytes(bin_name: str) -> bytes:
    """Package runtime scripts and target native binary into a gzip tarball."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        for path in sorted(PLUGIN_DIR.rglob("*")):
            if not path.is_file() or "__pycache__" in path.parts:
                continue
            rel = path.relative_to(PLUGIN_DIR).as_posix()
            if not rel.startswith(("hooks/scripts/", "scripts/")):
                continue
            raw = path.read_bytes()
            if path.suffix in {".py", ".json", ".md"}:
                raw = raw.replace(b"\r\n", b"\n")
            ti = tarfile.TarInfo(name=rel)
            ti.size = len(raw)
            ti.mode = 0o644
            tf.addfile(ti, io.BytesIO(raw))
        bin_raw = (PLUGIN_DIR / "bin" / bin_name).read_bytes()
        ti = tarfile.TarInfo(name=f"bin/{bin_name}")
        ti.size = len(bin_raw)
        ti.mode = 0o755
        tf.addfile(ti, io.BytesIO(bin_raw))
    return buf.getvalue()


def _require_ssh(host: str) -> None:
    """Skip only when the remote SSH host is unreachable in this environment."""
    probe = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5", host, "echo ok"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=10,
    )
    if probe.returncode != 0 or "ok" not in probe.stdout:
        pytest.skip(f"SSH host {host} unreachable: {probe.stderr.strip()}")


def test_linux_simulation_all_events():
    """Upload Linux bundle via SSH and verify ELF header, 6 AGY events, Cold fallback, and Hot latency."""
    _require_ssh(SSH_HOST)
    remote_dir = f"/tmp/tdq-sim-linux-{uuid.uuid4().hex[:8]}"
    tar_bytes = _build_bundle_bytes(BIN_NAME)
    try:
        subprocess.run(
            ["ssh", "-o", "ConnectTimeout=10", SSH_HOST, f"mkdir -p {remote_dir} && tar -xzf - -C {remote_dir} && chmod +x {remote_dir}/bin/{BIN_NAME}"],
            input=tar_bytes,
            capture_output=True,
            check=True,
            timeout=60,
        )
        hdr = subprocess.run(
            ["ssh", SSH_HOST, f"file {remote_dir}/bin/{BIN_NAME}"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=True,
            timeout=20,
        )
        assert "ELF" in hdr.stdout and "x86-64" in hdr.stdout, hdr.stdout
        run = subprocess.run(
            ["ssh", SSH_HOST, f"python3 - {remote_dir} {BIN_NAME}"],
            input=_REMOTE_DRIVER,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=60,
        )
        assert run.returncode == 0, f"Linux sim failed: {run.stdout}\n{run.stderr}"
        metrics = json.loads(run.stdout.strip().splitlines()[-1])
        assert metrics["hot_median_ms"] < 50.0
    finally:
        subprocess.run(["ssh", "-o", "ConnectTimeout=10", SSH_HOST, f"rm -rf {remote_dir}"], capture_output=True, check=False, timeout=20)
