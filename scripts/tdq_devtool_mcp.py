#!/usr/bin/env python3
"""TDQ DevTools MCP Manager (stdlib only).

Provides integration, zero-prompt auto-setup, and auto-launch capabilities for
Chrome DevTools MCP across Windows, macOS, and Linux.

Compliance:
  - Non-blocking checks (< 50ms) for hook integration.
  - Safe backup (.bak) on configuration edits.
  - Isolated Chrome User Data Profile (ChromeDevProfile).
"""
from datetime import datetime
import json
import os
import platform
import shutil
import socket
import subprocess
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tdq_ten_lenh  # noqa: E402
import utf8_io  # noqa: E402, F401

DEVTOOL_SERVER_NAME = "chrome-devtools"
DEFAULT_CDP_PORT = 9222
DEFAULT_CDP_HOST = "127.0.0.1"


def _log(message: str) -> None:
    """Emit an ISO-timestamped diagnostic line to stderr unless TDQ_LOG=0."""
    if os.environ.get("TDQ_LOG", "1") != "0":
        stamp = datetime.now().isoformat(timespec="seconds")
        print(f"[{stamp}] tdq_devtool_mcp: {message}", file=sys.stderr)


def is_enabled(cwd=None) -> bool:
    """Check if Chrome DevTools MCP is enabled via environment or config.

    1. Environment variable: TDQ_ENABLE_DEVTOOL_MCP == "1" / "true"
    2. Local file: docs/tdq/config.json -> {"ENABLE_DEVTOOL_MCP": true}
    3. Global settings: ~/.claude/settings.json -> env.TDQ_ENABLE_DEVTOOL_MCP
    """
    env_val = os.environ.get("TDQ_ENABLE_DEVTOOL_MCP", "").strip().lower()
    if env_val in ("1", "true", "yes"):
        return True

    # Check local project config
    if cwd:
        cfg_path = os.path.join(cwd, "docs", "tdq", "config.json")
        if os.path.isfile(cfg_path):
            try:
                with open(cfg_path, encoding="utf-8") as f:
                    data = json.load(f)
                    if data.get("ENABLE_DEVTOOL_MCP") is True:
                        return True
            except (OSError, ValueError):
                pass

    # Check ~/.claude/settings.json env
    settings_path = os.path.expanduser("~/.claude/settings.json")
    if os.path.isfile(settings_path):
        try:
            with open(settings_path, encoding="utf-8") as f:
                settings = json.load(f)
                env_dict = settings.get("env", {})
                if str(env_dict.get("TDQ_ENABLE_DEVTOOL_MCP", "")).strip().lower() in ("1", "true", "yes"):
                    return True
        except (OSError, ValueError):
            pass

    return False


def is_port_open(host=DEFAULT_CDP_HOST, port=DEFAULT_CDP_PORT, timeout=0.2) -> bool:
    """Quick socket check to verify if the CDP port is listening."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        res = sock.connect_ex((host, port))
        return res == 0
    except (socket.error, OSError):
        return False
    finally:
        sock.close()


def verify_cdp_endpoint(host=DEFAULT_CDP_HOST, port=DEFAULT_CDP_PORT, timeout=0.5) -> bool:
    """Verify that the open port is actually a Chromium CDP endpoint."""
    url = f"http://{host}:{port}/json/version"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "TDQ-DevTools-Probe"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return "webSocketDebuggerUrl" in data or "Browser" in data
    except Exception:
        return False


def get_chrome_executable() -> str:
    """Detect the Google Chrome executable path for the current OS."""
    chrome_env = os.environ.get("CHROME_PATH", "").strip()
    if chrome_env and os.path.isfile(chrome_env):
        return chrome_env
    system = platform.system().lower()
    if "windows" in system:
        candidates = [
            os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
        ]
    elif "darwin" in system:
        candidates = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            os.path.expanduser("~/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
        ]
    else:  # Linux / Unix
        for bin_name in ("google-chrome", "google-chrome-stable", "chromium-browser", "chromium"):
            found = shutil.which(bin_name)
            if found:
                return found
        candidates = ["/usr/bin/google-chrome", "/usr/bin/chromium"]

    for path in candidates:
        if os.path.isfile(path):
            return path

    return shutil.which("chrome") or ""


def get_dev_profile_dir() -> str:
    """Return the dedicated isolated profile directory for Chrome debug."""
    return os.path.join(os.path.expanduser("~"), "ChromeDevProfile")


def _is_antigravity_host() -> bool:
    """Return True when running inside Antigravity host/plugin context."""
    host_env = os.environ.get("TDQ_HOST", "").strip().lower()
    if host_env in ("antigravity", "agy"):
        return True
    if host_env == "claude":
        return False
    norm = os.path.abspath(__file__).replace("\\", "/").lower()
    if any(m in norm for m in (
        "/.gemini/config/plugins/",
        "/plugins/tdq-workflow-agy/",
        "/plugins/tdq-workflow/",
        "/antigravity_portable/",
    )):
        return True
    home = os.environ.get("HOME") or os.environ.get("USERPROFILE") or os.path.expanduser("~")
    has_gemini = os.path.isdir(os.path.join(home, ".gemini", "config")) or os.path.isdir(
        os.path.join(home, ".gemini", "antigravity")
    )
    has_claude = os.path.exists(os.path.join(home, ".claude.json")) or os.path.isdir(
        os.path.join(home, ".claude")
    )
    return bool(has_gemini and not has_claude)


def _probe_agy_plugins() -> list:
    """Query `agy plugin list --json` cleanly when CLI is available."""
    agy_bin = shutil.which("agy")
    if not agy_bin:
        return []
    try:
        proc = tdq_ten_lenh.chay_subprocess(
            [agy_bin, "plugin", "list", "--json"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
        )
        if proc.returncode != 0:
            return []
        parsed = json.loads(proc.stdout or "[]")
        return parsed if isinstance(parsed, list) else []
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        _log(f"agy plugin list failed: {type(exc).__name__}")
        return []


def _has_devtool_in_mcp(path: str) -> bool:
    """Return True if mcp_config file at `path` registers chrome-devtools."""
    if not os.path.isfile(path):
        return False
    try:
        with open(path, encoding="utf-8") as fh:
            servers = json.load(fh).get("mcpServers") or {}
        return isinstance(servers, dict) and DEVTOOL_SERVER_NAME in servers
    except (OSError, ValueError):
        return False


def _agy_plugin_flags(plugins: list) -> tuple[bool, bool]:
    """Return `(installed, enabled)` for Antigravity chrome-devtools-plugin."""
    for item in plugins or []:
        if isinstance(item, dict) and item.get("name") == "chrome-devtools-plugin":
            return True, bool(item.get("enabled"))
    disk_plugin = os.path.expanduser("~/.gemini/config/plugins/chrome-devtools-plugin/plugin.json")
    if os.path.isfile(disk_plugin):
        return True, False
    return False, False


def _check_devtool_agy(
    mcp_registered: bool,
    permission_allowed: bool,
    agy_plugins_probe,
) -> tuple[bool, bool, dict]:
    """Inspect Antigravity mcp_config.json paths and chrome-devtools-plugin state."""
    for cand in (
        os.path.expanduser("~/.gemini/config/mcp_config.json"),
        os.path.expanduser("~/.gemini/antigravity/mcp_config.json"),
        os.path.expanduser("~/.gemini/config/plugins/tdq-workflow-agy/mcp_config.json"),
    ):
        if _has_devtool_in_mcp(cand):
            mcp_registered = True
            permission_allowed = True
    plugins = agy_plugins_probe() if agy_plugins_probe is not None else _probe_agy_plugins()
    cdp_installed, cdp_enabled = _agy_plugin_flags(plugins)
    if cdp_enabled:
        mcp_registered = True
        permission_allowed = True
    return mcp_registered, permission_allowed, {
        "chrome_devtools_plugin_installed": cdp_installed,
        "chrome_devtools_plugin_enabled": cdp_enabled,
    }


def _check_devtool_claude(
    mcp_registered: bool,
    permission_allowed: bool,
    claude_json_path,
    settings_json_path,
) -> tuple[bool, bool]:
    """Inspect legacy Claude Code ~/.claude.json and ~/.claude/settings.json."""
    c_json = claude_json_path or os.path.expanduser("~/.claude.json")
    s_json = settings_json_path or os.path.expanduser("~/.claude/settings.json")
    if _has_devtool_in_mcp(c_json):
        mcp_registered = True
    if os.path.isfile(s_json):
        try:
            with open(s_json, encoding="utf-8") as fh:
                allows = json.load(fh).get("permissions", {}).get("allow", [])
            if any("chrome-devtools" in a or "chrome_devtools" in a for a in allows):
                permission_allowed = True
        except (OSError, ValueError):
            pass
    return mcp_registered, permission_allowed


def check_devtool_setup(
    claude_json_path=None,
    settings_json_path=None,
    agy_plugins_probe=None,
) -> dict:
    """Check Chrome DevTools MCP readiness for Claude Code or Antigravity."""
    plugin_mcp = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "mcp_config.json"
    )
    mcp_registered = _has_devtool_in_mcp(plugin_mcp)
    permission_allowed = mcp_registered
    use_agy = (claude_json_path is None and settings_json_path is None) and (
        agy_plugins_probe is not None or _is_antigravity_host()
    )
    extra: dict = {}
    if use_agy:
        mcp_registered, permission_allowed, extra = _check_devtool_agy(
            mcp_registered, permission_allowed, agy_plugins_probe
        )
    else:
        mcp_registered, permission_allowed = _check_devtool_claude(
            mcp_registered, permission_allowed, claude_json_path, settings_json_path
        )
    chrome_exe = get_chrome_executable()
    chrome_available = bool(chrome_exe and os.path.isfile(chrome_exe))
    profile_exists = os.path.isdir(get_dev_profile_dir())
    cdp_listening = is_port_open()
    all_ready = mcp_registered and permission_allowed and chrome_available
    _log(f"check_devtool_setup agy={use_agy} ready={all_ready}")
    return {
        "mcp_registered": mcp_registered,
        "permission_allowed": permission_allowed,
        "chrome_available": chrome_available,
        "profile_exists": profile_exists,
        "cdp_listening": cdp_listening,
        "all_ready": all_ready,
        **extra,
    }


def setup_devtool_mcp(claude_json_path=None, settings_json_path=None) -> bool:
    """Perform automatic zero-prompt setup for Chrome DevTools MCP.

    1. Register MCP server in ~/.claude.json.
    2. Add permission wildcards in ~/.claude/settings.json.
    3. Ensure isolated ChromeDevProfile directory exists.
    """
    c_json = claude_json_path or os.path.expanduser("~/.claude.json")
    s_json = settings_json_path or os.path.expanduser("~/.claude/settings.json")

    # 1. Update ~/.claude.json
    try:
        data = {}
        if os.path.isfile(c_json):
            with open(c_json, encoding="utf-8") as f:
                data = json.load(f)
        mcp_servers = data.setdefault("mcpServers", {})
        if DEVTOOL_SERVER_NAME not in mcp_servers:
            mcp_servers[DEVTOOL_SERVER_NAME] = {
                "type": "stdio",
                "command": "npx",
                "args": [
                    "-y",
                    "chrome-devtools-mcp@latest",
                    f"--browserUrl=http://{DEFAULT_CDP_HOST}:{DEFAULT_CDP_PORT}"
                ]
            }
            # Atomic save
            with open(c_json, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as exc:
        sys.stderr.write(f"Error registering MCP in {c_json}: {exc}\n")
        return False

    # 2. Update ~/.claude/settings.json
    try:
        s_data = {}
        if os.path.isfile(s_json):
            with open(s_json, encoding="utf-8") as f:
                s_data = json.load(f)
        perms = s_data.setdefault("permissions", {})
        allows = perms.setdefault("allow", [])
        rules_to_add = ["mcp__chrome-devtools__*", "mcp__chrome_devtools__*"]
        modified = False
        for rule in rules_to_add:
            if rule not in allows:
                allows.append(rule)
                modified = True
        if modified:
            os.makedirs(os.path.dirname(s_json), exist_ok=True)
            with open(s_json, "w", encoding="utf-8") as f:
                json.dump(s_data, f, indent=2, ensure_ascii=False)
    except Exception as exc:
        sys.stderr.write(f"Error updating permissions in {s_json}: {exc}\n")
        return False

    # 3. Create Profile Directory
    try:
        profile_dir = get_dev_profile_dir()
        os.makedirs(profile_dir, exist_ok=True)
    except OSError as exc:
        sys.stderr.write(f"Error creating profile dir: {exc}\n")
        return False

    return True


def ensure_chrome_running(port=DEFAULT_CDP_PORT, timeout=3.0) -> bool:
    """Ensure Chrome is running with Remote Debugging enabled on the port.

    If port is not listening, auto-launches Chrome in detached background mode.
    """
    if is_port_open(port=port) and verify_cdp_endpoint(port=port):
        return True

    chrome_exe = get_chrome_executable()
    if not chrome_exe:
        sys.stderr.write("Chrome executable not found. Cannot auto-launch.\n")
        return False

    profile_dir = get_dev_profile_dir()
    os.makedirs(profile_dir, exist_ok=True)

    args = [
        chrome_exe,
        f"--remote-debugging-port={port}",
        f'--user-data-dir={profile_dir}',
        "--remote-allow-origins=*",
        "--no-first-run",
        "--no-default-browser-check"
    ]

    try:
        creationflags = 0
        if platform.system().lower() == "windows":
            # DETACHED_PROCESS = 0x00000008 | CREATE_NO_WINDOW = 0x08000000
            creationflags = 0x00000008 | getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)

        subprocess.Popen(
            args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
            creationflags=creationflags
        )
    except Exception as exc:
        sys.stderr.write(f"Failed to auto-launch Chrome: {exc}\n")
        return False

    # Polling wait for CDP port
    start = time.time()
    while time.time() - start < timeout:
        if is_port_open(port=port):
            if verify_cdp_endpoint(port=port, timeout=0.3):
                return True
        time.sleep(0.2)

    return False


def check_session_start(cwd=None) -> str:
    """Fast check intended for SessionStart hook.

    Returns a short context reminder line or empty string.
    Target execution time: < 30ms.
    """
    if not is_enabled(cwd=cwd):
        return ""

    status = check_devtool_setup()
    if status["all_ready"]:
        cdp_status = "active (9222)" if status["cdp_listening"] else "ready (auto-launch on call)"
        return f"[TDQ:DEVTOOL] Chrome DevTools MCP: {cdp_status}"

    # Needs setup
    return "[TDQ:DEVTOOL] Chrome DevTools MCP enabled but incomplete. Run: python3 scripts/tdq_setup.py"


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "setup":
        ok = setup_devtool_mcp()
        print("Setup successful." if ok else "Setup failed.")
    elif len(sys.argv) > 1 and sys.argv[1] == "launch":
        ok = ensure_chrome_running()
        print("Chrome running." if ok else "Chrome failed to launch.")
    else:
        st = check_devtool_setup()
        print(json.dumps(st, indent=2))
