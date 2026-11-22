"""Generate zero-dependency multi-OS Node.js launchers for Antigravity hooks and MCP."""
import os
import stat
from pathlib import Path

from .common_utils import write_utf8

HOOK_LAUNCHER_MJS = """import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

const BINARY_BY_TARGET = Object.freeze({
  "win32:x64": "tdq-dispatch.exe",
  "darwin:arm64": "tdq-dispatch-darwin-arm64",
  "darwin:x64": "tdq-dispatch-darwin-x64",
  "linux:x64": "tdq-dispatch-linux-x86_64",
});

function logEnabled() {
  return process.env.TDQ_LOG !== "0";
}

function logInfo(message) {
  if (!logEnabled()) return;
  const stamp = new Date().toISOString().slice(0, 19);
  process.stderr.write(`[${stamp}] tdq_hook_launcher: ${message}\\n`);
}

export function resolveBinaryName(platform = process.platform, arch = process.arch) {
  return BINARY_BY_TARGET[`${platform}:${arch}`] ?? null;
}

export function isWindowsAppsStub(execPath) {
  return String(execPath || "").toLowerCase().includes("windowsapps");
}

export function selectPythonFallback(platform = process.platform) {
  if (platform === "win32") {
    return [
      { cmd: "py", prefix: ["-3", "-X", "utf8"] },
      { cmd: "python", prefix: ["-X", "utf8"] },
    ];
  }
  return [
    { cmd: "python3", prefix: ["-X", "utf8"] },
    { cmd: "python", prefix: ["-X", "utf8"] },
  ];
}

function resolveExecutableOnPath(cmd, envPath, platform) {
  const sep = platform === "win32" ? ";" : ":";
  const exts = platform === "win32" ? [".exe", ".cmd", ".bat", ""] : [""];
  for (const dir of String(envPath || "").split(sep)) {
    if (!dir) continue;
    for (const ext of exts) {
      const candidate = path.join(dir, cmd.endsWith(ext) ? cmd : `${cmd}${ext}`);
      try {
        if (fs.statSync(candidate).isFile()) return candidate;
      } catch {}
    }
  }
  return null;
}

function tryBinary(binPath, args, pluginRoot, platform) {
  if (platform !== "win32") {
    try {
      fs.chmodSync(binPath, 0o755);
    } catch {}
  }
  const res = spawnSync(binPath, args, {
    cwd: pluginRoot,
    env: { ...process.env, PLUGIN_ROOT: pluginRoot },
    stdio: "inherit",
    windowsHide: true,
  });
  if (!res.error && typeof res.status === "number") return res.status;
  logInfo(`rust binary failed (${res.error?.code || "error"}), trying fallback`);
  return null;
}

function tryPythonDispatch(dispatchScript, args, pluginRoot, platform) {
  if (!fs.existsSync(dispatchScript)) {
    logInfo(`dispatch script missing at ${dispatchScript}`);
    return null;
  }
  const env = { ...process.env, PLUGIN_ROOT: pluginRoot };
  for (const cand of selectPythonFallback(platform)) {
    const resolved = resolveExecutableOnPath(cand.cmd, process.env.PATH, platform);
    if (!resolved || isWindowsAppsStub(resolved)) continue;
    logInfo(`using python fallback via ${resolved}`);
    const res = spawnSync(resolved, [...cand.prefix, dispatchScript, ...args], {
      cwd: pluginRoot,
      env,
      stdio: "inherit",
      windowsHide: true,
    });
    if (!res.error && typeof res.status === "number") return res.status;
  }
  return null;
}

export function main(argv = process.argv.slice(2)) {
  const here = path.dirname(fileURLToPath(import.meta.url));
  const pluginRoot = path.resolve(here, "..");
  const primary = resolveBinaryName();
  const binNames = [primary, process.platform === "win32" ? null : "tdq-dispatch"]
    .filter((v, i, arr) => v && arr.indexOf(v) === i);

  for (const name of binNames) {
    const binPath = path.join(pluginRoot, "bin", name);
    if (!fs.existsSync(binPath)) continue;
    const rc = tryBinary(binPath, argv, pluginRoot, process.platform);
    if (rc !== null) return rc;
  }

  const pyRc = tryPythonDispatch(
    path.join(pluginRoot, "hooks", "scripts", "dispatch.py"),
    argv,
    pluginRoot,
    process.platform
  );
  if (pyRc !== null) return pyRc;

  logInfo("no hook runtime available; returning fail-open {}");
  process.stdout.write("{}\\n");
  return 0;
}

const isCli =
  process.argv[1] &&
  path.resolve(process.argv[1]) === path.resolve(fileURLToPath(import.meta.url));
if (isCli) process.exit(main());
"""

MCP_LAUNCHER_MJS = """import { spawn } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

function logEnabled() {
  return process.env.TDQ_LOG !== "0";
}

function logInfo(message) {
  if (!logEnabled()) return;
  const stamp = new Date().toISOString().slice(0, 19);
  process.stderr.write(`[${stamp}] tdq_mcp_launcher: ${message}\\n`);
}

function candidateBinDirs(envPath, homeDir, platform) {
  const sep = platform === "win32" ? ";" : ":";
  const fromPath = String(envPath || "").split(sep).filter(Boolean);
  const home = homeDir || os.homedir();
  const standard = [path.join(home, ".local", "bin"), path.join(home, ".cargo", "bin")];
  if (platform !== "win32") standard.push("/opt/homebrew/bin", "/usr/local/bin", "/usr/bin");
  return [...new Set([...fromPath, ...standard])];
}

export function resolveAgentLspCommand(
  envPath = process.env.PATH || "",
  homeDir = os.homedir(),
  platform = process.platform
) {
  const exeName = platform === "win32" ? "agent-lsp.exe" : "agent-lsp";
  for (const dir of candidateBinDirs(envPath, homeDir, platform)) {
    const candidate = path.join(dir, exeName);
    try {
      if (fs.statSync(candidate).isFile()) return candidate;
    } catch {}
  }
  return platform === "win32" ? "agent-lsp.exe" : "agent-lsp";
}

export function buildSpawnSpec(
  mode,
  forwardedArgs = [],
  platform = process.platform,
  lspCmd = "agent-lsp"
) {
  if (mode === "npx") {
    if (platform === "win32") {
      return {
        command: "cmd.exe",
        args: ["/d", "/s", "/c", "npx.cmd", ...forwardedArgs],
        shell: false,
      };
    }
    return { command: "npx", args: [...forwardedArgs], shell: false };
  }
  if (mode === "lsp") {
    return { command: lspCmd, args: [...forwardedArgs], shell: false };
  }
  throw new Error(`Unsupported MCP launcher mode: ${mode}`);
}

function ensureUserDataDir(args) {
  for (const arg of args) {
    if (arg.startsWith("--userDataDir=")) {
      const target = arg.slice("--userDataDir=".length);
      if (target) fs.mkdirSync(target, { recursive: true });
    }
  }
}

export function main(argv = process.argv.slice(2)) {
  const [mode = "lsp", ...forwarded] = argv;
  try {
    ensureUserDataDir(forwarded);
  } catch (err) {
    logInfo(`failed creating userDataDir: ${err.message}`);
  }
  const override = process.env.TDQ_MCP_OVERRIDE_CMD;
  const resolvedLsp =
    mode === "lsp" ? override || resolveAgentLspCommand() : "agent-lsp";
  const spec = buildSpawnSpec(mode, forwarded, process.platform, resolvedLsp);
  logInfo(`launching mode=${mode} cmd=${spec.command}`);

  const child = spawn(spec.command, spec.args, {
    stdio: "inherit",
    shell: spec.shell,
    windowsHide: true,
  });
  for (const sig of ["SIGINT", "SIGTERM"]) {
    process.on(sig, () => {
      try {
        child.kill(sig);
      } catch {}
    });
  }
  child.on("error", (err) => {
    logInfo(`spawn error for ${spec.command}: ${err.message} (run /tdq-setup if missing)`);
    process.exit(1);
  });
  child.on("exit", (code, signal) => {
    if (signal) process.kill(process.pid, signal);
    process.exit(code ?? 1);
  });
}

const isCli =
  process.argv[1] &&
  path.resolve(process.argv[1]) === path.resolve(fileURLToPath(import.meta.url));
if (isCli) main();
"""


def _write_executable_script(path: Path, content: str) -> Path:
    """Write script UTF-8 cleanly and mark 0755 on POSIX."""
    write_utf8(path, content)
    if os.name != "nt":
        path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return path


def generate_launchers(plugin_root: Path) -> list[Path]:
    """Write tdq_hook_launcher.mjs and tdq_mcp_launcher.mjs into plugin_root/scripts/."""
    scripts_dir = Path(plugin_root) / "scripts"
    return [
        _write_executable_script(scripts_dir / "tdq_hook_launcher.mjs", HOOK_LAUNCHER_MJS),
        _write_executable_script(scripts_dir / "tdq_mcp_launcher.mjs", MCP_LAUNCHER_MJS),
    ]
