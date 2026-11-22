"""Red-Green tests for Gate-0 bootstrap scripts, Node probe, and 0755 .sh release mode."""
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = WORKSPACE / "scripts"
PROBE_MJS = SCRIPTS_DIR / "tdq_setup_probe.mjs"
BOOTSTRAP_PS1 = SCRIPTS_DIR / "bootstrap.ps1"
BOOTSTRAP_SH = SCRIPTS_DIR / "bootstrap.sh"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

EXPECTED_TOOL_KEYS = (
    "git",
    "node",
    "uv",
    "python",
    "agy",
    "agent-lsp",
    "rtk",
    "rg",
    "browser",
    "archify",
)


def _run_cmd(cmd, env=None, timeout=15, input_text=None) -> subprocess.CompletedProcess:
    kw = {
        "capture_output": True,
        "text": True,
        "encoding": "utf-8",
        "errors": "replace",
        "timeout": timeout,
    }
    if env is not None:
        kw["env"] = env
    if input_text is not None:
        kw["input"] = input_text
    if os.name == "nt":
        kw["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
    return subprocess.run(cmd, check=False, **kw)


def _find_powershell() -> str | None:
    return shutil.which("pwsh") or shutil.which("powershell")


def _find_usable_bash() -> str | None:
    if os.name == "nt":
        for cand in (
            r"C:\Program Files\Git\usr\bin\bash.exe",
            r"C:\Program Files\Git\bin\bash.exe",
        ):
            if os.path.isfile(cand):
                return cand
        for cand in (shutil.which("bash") or "",):
            if cand and "system32" not in cand.lower() and "windowsapps" not in cand.lower():
                return cand
        return None
    return shutil.which("bash")


def _run_probe_fn(expr: str, env_extra=None) -> dict:
    uri = PROBE_MJS.resolve().as_uri()
    code = (
        f"import {{ probeToolchain }} from {json.dumps(uri)};\n"
        f"const res = ({expr});\n"
        "process.stdout.write(JSON.stringify(res));\n"
    )
    env = dict(os.environ, TDQ_LOG="0")
    if env_extra:
        env.update(env_extra)
    proc = _run_cmd(["node", "--input-type=module", "-"], env=env, timeout=10, input_text=code)
    assert proc.returncode == 0, f"probe helper failed: {proc.stderr}"
    return json.loads(proc.stdout)


def _create_mock_exe(path: Path, output: str = "") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if os.name == "nt" and path.suffix.lower() in (".cmd", ".bat"):
        body = f"@echo off\r\necho {output}\r\n" if output else "@echo off\r\nexit /b 0\r\n"
        path.write_text(body, encoding="utf-8")
    elif os.name == "nt":
        path.write_bytes(b"stub")
    else:
        body = f"#!/bin/sh\necho {json.dumps(output)}\n"
        path.write_text(body, encoding="utf-8")
        path.chmod(0o755)
    return path


def test_probe_mjs_syntax_and_zero_deps():
    assert PROBE_MJS.is_file(), f"Missing {PROBE_MJS}"
    chk = _run_cmd(["node", "--check", str(PROBE_MJS)])
    assert chk.returncode == 0, f"node --check failed: {chk.stderr}"
    text = PROBE_MJS.read_text(encoding="utf-8")
    imports = re.findall(r'from\s+["\']([^"\']+)["\']', text)
    assert imports, "Expected ESM imports in tdq_setup_probe.mjs"
    for mod in imports:
        assert mod.startswith("node:"), f"External dependency disallowed: {mod}"
    assert "export function probeToolchain" in text


def test_probe_empty_path_and_windowsapps_stub_reject_python(tmp_path: Path):
    assert PROBE_MJS.is_file(), f"Missing {PROBE_MJS}"
    t0 = time.monotonic()
    empty_report = _run_probe_fn('probeToolchain({ PATH: "" }, "win32")')
    elapsed = time.monotonic() - t0
    assert elapsed < 5.0, f"Probe took too long: {elapsed:.2f}s"
    assert empty_report["python"]["usable"] is False
    assert empty_report["node"]["usable"] is False
    assert empty_report["git"]["usable"] is False

    stub_dir = tmp_path / "Local" / "Microsoft" / "WindowsApps"
    _create_mock_exe(stub_dir / "python.exe")
    _create_mock_exe(stub_dir / "python3.exe")

    stub_report = _run_probe_fn(
        f'probeToolchain({{ PATH: {json.dumps(str(stub_dir))}, '
        f'HOME: {json.dumps(str(tmp_path))}, '
        f'USERPROFILE: {json.dumps(str(tmp_path))} }}, "win32")'
    )
    assert stub_report["python"]["usable"] is False
    assert stub_report["python"]["windowsapps_rejected"] is True

    node_bin = shutil.which("node")
    assert node_bin, "node is required on PATH"
    cli_env = {
        "PATH": str(stub_dir),
        "HOME": str(tmp_path),
        "USERPROFILE": str(tmp_path),
        "TDQ_LOG": "0",
    }
    if os.name == "nt" and "SystemRoot" in os.environ:
        cli_env["SystemRoot"] = os.environ["SystemRoot"]
    t1 = time.monotonic()
    cli_proc = _run_cmd([node_bin, str(PROBE_MJS), "--json"], env=cli_env, timeout=5)
    assert time.monotonic() - t1 < 5.0
    assert cli_proc.returncode == 0, cli_proc.stderr
    cli_data = json.loads(cli_proc.stdout)
    assert cli_data["python"]["usable"] is False
    assert cli_data["python"]["windowsapps_rejected"] is True


def test_probe_synthetic_env_with_spaces_and_real_node(tmp_path: Path):
    assert PROBE_MJS.is_file(), f"Missing {PROBE_MJS}"
    node_bin = shutil.which("node")
    assert node_bin, "node executable is required"

    spaced_bin = tmp_path / "tools with spaces" / "bin"
    spaced_bin.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        wrapper = spaced_bin / "node.cmd"
        wrapper.write_text(f'@"{node_bin}" %*\r\n', encoding="utf-8")
        browser_exe = _create_mock_exe(spaced_bin / "chrome.exe")
    else:
        wrapper = spaced_bin / "node"
        wrapper.symlink_to(node_bin)
        browser_exe = _create_mock_exe(spaced_bin / "google-chrome", "120.0.0")

    archify_dir = tmp_path / "custom archify"
    archify_bin = archify_dir / "bin" / "archify.mjs"
    archify_bin.parent.mkdir(parents=True, exist_ok=True)
    archify_bin.write_text("console.log('archify');\n", encoding="utf-8")

    synth_env = {
        "PATH": str(spaced_bin),
        "HOME": str(tmp_path),
        "USERPROFILE": str(tmp_path),
        "ARCHIFY_ROOT": str(archify_dir),
        "TDQ_LOG": "0",
    }
    if os.name == "nt":
        for keep in ("SystemRoot", "ComSpec"):
            if keep in os.environ:
                synth_env[keep] = os.environ[keep]

    report = _run_probe_fn(
        f"probeToolchain({json.dumps(synth_env)}, {json.dumps(sys.platform)})"
    )
    for key in EXPECTED_TOOL_KEYS:
        assert key in report, f"Missing expected tool key: {key}"
        assert isinstance(report[key], dict)
        assert isinstance(report[key]["usable"], bool)
    assert report["node"]["usable"] is True
    assert report["node"]["major"] >= 18
    assert report["archify"]["usable"] is True
    assert Path(report["archify"]["path"]) == archify_bin
    assert report["browser"]["usable"] is True
    assert Path(report["browser"]["path"]) == browser_exe

    cli_proc = _run_cmd([node_bin, str(PROBE_MJS), "--json"], env=synth_env, timeout=10)
    assert cli_proc.returncode == 0, cli_proc.stderr
    cli_report = json.loads(cli_proc.stdout)
    assert cli_report["node"]["usable"] is True


def test_probe_rejects_node_below_18_and_resolves_archify_home(tmp_path: Path):
    assert PROBE_MJS.is_file(), f"Missing {PROBE_MJS}"
    old_bin = tmp_path / "old node"
    mock_name = "node.cmd" if os.name == "nt" else "node"
    _create_mock_exe(old_bin / mock_name, "v16.20.0")

    old_env = {
        "PATH": str(old_bin),
        "HOME": str(tmp_path),
        "USERPROFILE": str(tmp_path),
        "TDQ_LOG": "0",
    }
    if os.name == "nt":
        for keep in ("SystemRoot", "ComSpec"):
            if keep in os.environ:
                old_env[keep] = os.environ[keep]
    old_rep = _run_probe_fn(f"probeToolchain({json.dumps(old_env)}, {json.dumps(sys.platform)})")
    assert old_rep["node"]["usable"] is False
    assert "18" in old_rep["node"]["reason"]

    local_archify = tmp_path / ".local" / "share" / "archify" / "bin" / "archify.mjs"
    local_archify.parent.mkdir(parents=True, exist_ok=True)
    local_archify.write_text("// ok\n", encoding="utf-8")

    rep1 = _run_probe_fn(
        f'probeToolchain({{ PATH: "", HOME: {json.dumps(str(tmp_path))}, '
        f'USERPROFILE: {json.dumps(str(tmp_path))} }}, "linux")'
    )
    assert rep1["archify"]["usable"] is True
    assert Path(rep1["archify"]["path"]) == local_archify

    local_archify.unlink()
    docs_archify = tmp_path / "Documents" / "archify" / "bin" / "archify.mjs"
    docs_archify.parent.mkdir(parents=True, exist_ok=True)
    docs_archify.write_text("// ok\n", encoding="utf-8")
    rep2 = _run_probe_fn(
        f'probeToolchain({{ PATH: "", HOME: {json.dumps(str(tmp_path))}, '
        f'USERPROFILE: {json.dumps(str(tmp_path))} }}, "win32")'
    )
    assert rep2["archify"]["usable"] is True
    assert Path(rep2["archify"]["path"]) == docs_archify


def test_probe_logging_default_and_tdq_log_zero(tmp_path: Path):
    assert PROBE_MJS.is_file(), f"Missing {PROBE_MJS}"
    base_env = {
        "PATH": "",
        "HOME": str(tmp_path),
        "USERPROFILE": str(tmp_path),
    }
    if os.name == "nt" and "SystemRoot" in os.environ:
        base_env["SystemRoot"] = os.environ["SystemRoot"]

    node_bin = shutil.which("node")
    assert node_bin

    res_on = _run_cmd([node_bin, str(PROBE_MJS), "--json"], env=base_env, timeout=5)
    assert res_on.returncode == 0, res_on.stderr
    assert json.loads(res_on.stdout)["python"]["usable"] is False
    assert re.search(
        r"\[\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\] tdq_setup_probe:",
        res_on.stderr,
    ), f"Expected ISO timestamp stderr log, got: {res_on.stderr!r}"

    res_off = _run_cmd(
        [node_bin, str(PROBE_MJS), "--json"],
        env={**base_env, "TDQ_LOG": "0"},
        timeout=5,
    )
    assert res_off.returncode == 0, res_off.stderr
    assert json.loads(res_off.stdout)["python"]["usable"] is False
    assert res_off.stderr == "", f"Expected empty stderr when TDQ_LOG=0, got: {res_off.stderr!r}"


def test_bootstrap_ps1_ast_path_order_and_dry_run(tmp_path: Path):
    assert BOOTSTRAP_PS1.is_file(), f"Missing {BOOTSTRAP_PS1}"
    text = BOOTSTRAP_PS1.read_text(encoding="utf-8")
    assert ".local" in text and "WindowsApps" in text
    assert "-DryRun" in text or "DryRun" in text
    assert "-StateDir" in text or "StateDir" in text
    assert "-KhongChamMay" in text or "KhongChamMay" in text
    assert "tdq_setup.py" in text and "--setupfully" in text
    assert "RunAs" not in text

    ps = _find_powershell()
    assert ps, "PowerShell parser required on Windows test host"
    escaped_ps1 = str(BOOTSTRAP_PS1).replace("'", "''")
    ast_cmd = (
        "$errs = $null; $tokens = $null; "
        "[void][System.Management.Automation.Language.Parser]::ParseFile("
        f"'{escaped_ps1}', [ref]$tokens, [ref]$errs); "
        "if ($errs -and $errs.Count -gt 0) { $errs | ForEach-Object { Write-Error $_.Message }; exit 1 }"
    )
    chk = _run_cmd([ps, "-NoProfile", "-NonInteractive", "-Command", ast_cmd])
    assert chk.returncode == 0, f"PowerShell AST error: {chk.stderr}"

    # Verify Build-OrderedPath places .local\bin ahead of WindowsApps even when WindowsApps came first
    order_cmd = (
        f". '{escaped_ps1}'; "
        "$localBin = 'C:\\Users\\Alice With Space\\.local\\bin'; "
        "$oldPath = 'C:\\Users\\Alice With Space\\AppData\\Local\\Microsoft\\WindowsApps;C:\\Windows\\System32'; "
        "$ordered = Build-OrderedPath -CurrentPath $oldPath -PrependDirs @($localBin); "
        "Write-Output $ordered"
    )
    ord_res = _run_cmd([ps, "-NoProfile", "-NonInteractive", "-Command", order_cmd])
    assert ord_res.returncode == 0, ord_res.stderr
    parts = [p for p in ord_res.stdout.strip().split(";") if p]
    assert parts[0].endswith(r".local\bin")
    assert parts.index(parts[0]) < next(i for i, p in enumerate(parts) if "WindowsApps" in p)

    state_dir = tmp_path / "state with spaces"
    dry_env = dict(os.environ, TDQ_LOG="1", TDQ_KHONG_CHAM_MAY="1")
    dry = _run_cmd(
        [
            ps,
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(BOOTSTRAP_PS1),
            "-DryRun",
            "-KhongChamMay",
            "-StateDir",
            str(state_dir),
        ],
        env=dry_env,
        timeout=20,
    )
    assert dry.returncode == 0, f"DryRun failed: {dry.stdout}\n{dry.stderr}"
    assert "[dry-run]" in dry.stderr
    assert re.search(r"\[\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\] bootstrap\.ps1:", dry.stderr)


def test_bootstrap_sh_syntax_no_sudo_and_missing_git(tmp_path: Path):
    assert BOOTSTRAP_SH.is_file(), f"Missing {BOOTSTRAP_SH}"
    raw = BOOTSTRAP_SH.read_bytes()
    assert b"\r" not in raw, "bootstrap.sh must use LF line endings"
    text = raw.decode("utf-8")
    assert text.startswith("#!/usr/bin/env bash\n")
    assert "set -euo pipefail" in text
    assert "--dry-run" in text
    assert "tdq_setup.py" in text and "--setupfully" in text
    assert "sudo apt-get install -y git" in text
    assert "dnf install -y git" in text

    for lineno, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        assert not re.match(r"^(?:command\s+)?sudo\b", stripped), (
            f"bootstrap.sh:{lineno} must not execute sudo directly: {stripped}"
        )

    bash_bin = _find_usable_bash()
    if bash_bin:
        chk = _run_cmd([bash_bin, "-n", str(BOOTSTRAP_SH)])
        assert chk.returncode == 0, f"bash -n failed: {chk.stderr}"

        for pkg_mgr, expected_cmd in (
            ("apt-get", "sudo apt-get install -y git"),
            ("dnf", "sudo dnf install -y git"),
        ):
            fake_bin = tmp_path / f"no git {pkg_mgr}"
            fake_bin.mkdir(parents=True, exist_ok=True)
            uname_mock = fake_bin / "uname"
            uname_mock.write_text("#!/bin/sh\necho Linux\n", encoding="utf-8")
            uname_mock.chmod(0o755)
            pm_mock = fake_bin / pkg_mgr
            pm_mock.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            pm_mock.chmod(0o755)
            no_git_env = {
                "PATH": str(fake_bin),
                "HOME": str(tmp_path),
                "TDQ_LOG": "0",
                "TDQ_KHONG_CHAM_MAY": "1",
            }
            if os.name == "nt" and "SystemRoot" in os.environ:
                no_git_env["SystemRoot"] = os.environ["SystemRoot"]
            res_nogit = _run_cmd([bash_bin, str(BOOTSTRAP_SH)], env=no_git_env, timeout=10)
            assert res_nogit.returncode != 0
            combined = res_nogit.stdout + "\n" + res_nogit.stderr
            assert expected_cmd in combined

        state_dir = tmp_path / "state with spaces"
        path_with_bash = os.pathsep.join(
            [str(Path(bash_bin).parent), os.environ.get("PATH", "")]
        )
        dry_env = dict(
            os.environ,
            PATH=path_with_bash,
            HOME=str(tmp_path),
            TDQ_LOG="1",
            TDQ_KHONG_CHAM_MAY="1",
        )
        dry = _run_cmd(
            [bash_bin, str(BOOTSTRAP_SH), "--dry-run", "--state-dir", str(state_dir)],
            env=dry_env,
            timeout=15,
        )
        assert dry.returncode == 0, f"bootstrap.sh --dry-run failed: {dry.stdout}\n{dry.stderr}"
        assert "[dry-run]" in dry.stderr

        # Also verify stdin pipe (`curl ... | bash`) works cleanly under `set -euo pipefail`
        piped = _run_cmd(
            [bash_bin, "-s", "--", "--dry-run", "--state-dir", str(state_dir)],
            env=dry_env,
            timeout=15,
            input_text=text,
        )
        assert piped.returncode == 0, f"piped bash -s failed: {piped.stdout}\n{piped.stderr}"
        assert "[dry-run]" in piped.stderr


def test_build_portable_loc_muc_agy_release_sets_0755_on_sh():
    import build_portable

    raw = (
        b"100644 blob " + (b"a" * 40) + b"\tplugins/tdq-workflow-agy/plugin.json\0"
        b"100644 blob " + (b"b" * 40) + b"\tplugins/tdq-workflow-agy/scripts/tdq_hook_launcher.mjs\0"
        b"100644 blob " + (b"c" * 40) + b"\tplugins/tdq-workflow-agy/scripts/bootstrap.sh\0"
        b"100644 blob " + (b"d" * 40) + b"\tplugins/tdq-workflow-agy/scripts/tdq_setup.py\0"
        b"100644 blob " + (b"e" * 40) + b"\tplugins/tdq-workflow-agy/bin/tdq-dispatch-linux-x86_64\0"
    )
    kept = [entry.decode("utf-8") for entry in build_portable.loc_muc_agy_release(raw)]
    assert "100644 blob " + ("a" * 40) + "\tplugin.json" in kept
    assert "100755 blob " + ("b" * 40) + "\tscripts/tdq_hook_launcher.mjs" in kept
    assert "100755 blob " + ("c" * 40) + "\tscripts/bootstrap.sh" in kept
    assert "100644 blob " + ("d" * 40) + "\tscripts/tdq_setup.py" in kept
    assert "100755 blob " + ("e" * 40) + "\tbin/tdq-dispatch-linux-x86_64" in kept
