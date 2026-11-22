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

MCP_LAUNCHER_MJS = r"""import { spawn } from "node:child_process";
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
  process.stderr.write(`[${stamp}] tdq_mcp_launcher: ${message}\n`);
}

export function isWindowsAppsStub(execPath) {
  return String(execPath || "").toLowerCase().includes("windowsapps");
}

function parseSemverTuple(name) {
  const match = /^v?(\d+)\.(\d+)\.(\d+)/.exec(String(name || ""));
  if (!match) return [0, 0, 0];
  return [Number(match[1]), Number(match[2]), Number(match[3])];
}

function compareSemverDesc(a, b) {
  const pa = parseSemverTuple(a);
  const pb = parseSemverTuple(b);
  for (let i = 0; i < 3; i += 1) {
    if (pb[i] !== pa[i]) return pb[i] - pa[i];
  }
  return String(b).localeCompare(String(a));
}

function selectPathApi(home, platform) {
  if (platform !== "win32" && !/^[A-Za-z]:/.test(String(home || ""))) {
    return path.posix;
  }
  return path;
}

function collectNvmNodeDirs(home, platform, pathApi) {
  const nvmRoot = pathApi.join(home, ".nvm", "versions", "node");
  try {
    const versions = fs
      .readdirSync(nvmRoot, { withFileTypes: true })
      .filter((entry) => entry.isDirectory())
      .map((entry) => entry.name)
      .sort(compareSemverDesc);
    if (versions.length === 0) return [];
    const latestDir = pathApi.join(nvmRoot, versions[0]);
    const binDir = pathApi.join(latestDir, "bin");
    if (platform === "win32" && !fs.existsSync(binDir)) return [latestDir];
    return [binDir];
  } catch {
    return [];
  }
}

function collectFnmDirs(home, platform, envVars, pathApi) {
  const bases = [pathApi.join(home, ".local", "share", "fnm"), pathApi.join(home, ".fnm")];
  if (platform === "win32" && envVars?.LOCALAPPDATA) {
    bases.push(pathApi.join(envVars.LOCALAPPDATA, "fnm"));
  }
  const dirs = [];
  for (const base of bases) {
    dirs.push(pathApi.join(base, "aliases", "default", "bin"));
    if (platform === "win32") dirs.push(pathApi.join(base, "aliases", "default"));
    dirs.push(base);
  }
  return dirs;
}

function dedupeDirs(dirs, platform) {
  const seen = new Set();
  const out = [];
  const win32 = platform === "win32";
  for (const dir of dirs) {
    if (!dir) continue;
    const key = win32 ? dir.toLowerCase() : dir;
    if (seen.has(key)) continue;
    seen.add(key);
    out.push(dir);
  }
  return out;
}

function buildUserBinDirs(homeDir, platform, envVars) {
  const home = homeDir || os.homedir();
  const pathApi = selectPathApi(home, platform);
  const dirs = [pathApi.join(home, ".local", "bin"), pathApi.join(home, ".cargo", "bin")];
  if (platform === "win32" && envVars?.USERPROFILE) {
    dirs.push(pathApi.join(envVars.USERPROFILE, ".local", "bin"));
    dirs.push(pathApi.join(envVars.USERPROFILE, ".cargo", "bin"));
  }
  dirs.push(...collectFnmDirs(home, platform, envVars, pathApi));
  dirs.push(...collectNvmNodeDirs(home, platform, pathApi));
  if (platform !== "win32") {
    dirs.push("/opt/homebrew/bin", "/usr/local/bin", "/usr/bin", "/bin");
  }
  return dedupeDirs(dirs, platform);
}

function candidateBinDirs(
  envPath = process.env.PATH || "",
  homeDir = os.homedir(),
  platform = process.platform,
  envVars = process.env
) {
  const sep = platform === "win32" ? ";" : ":";
  const existing = String(envPath || "").split(sep).filter(Boolean);
  const userDirs = buildUserBinDirs(homeDir, platform, envVars);
  if (platform === "win32") {
    const appsIdx = existing.findIndex((dir) => isWindowsAppsStub(dir));
    if (appsIdx >= 0) {
      return dedupeDirs(
        [...existing.slice(0, appsIdx), ...userDirs, ...existing.slice(appsIdx)],
        platform
      );
    }
  }
  return dedupeDirs([...existing, ...userDirs], platform);
}

export function expandUserPath(
  envPath = process.env.PATH || "",
  homeDir = os.homedir(),
  platform = process.platform,
  envVars = process.env
) {
  const sep = platform === "win32" ? ";" : ":";
  return candidateBinDirs(envPath, homeDir, platform, envVars).join(sep);
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
  return exeName;
}

function findRealExecutable(cmd, envPath, platform, rejectFn) {
  const sep = platform === "win32" ? ";" : ":";
  const exts = platform === "win32" ? [".exe", ".cmd", ".bat", ""] : [""];
  for (const dir of String(envPath || "").split(sep)) {
    if (!dir) continue;
    for (const ext of exts) {
      const candidate = path.join(dir, ext && !cmd.endsWith(ext) ? `${cmd}${ext}` : cmd);
      if (rejectFn && rejectFn(candidate)) continue;
      try {
        if (fs.statSync(candidate).isFile()) return candidate;
      } catch {}
    }
  }
  return null;
}

export function resolvePythonSpec(
  platform = process.platform,
  envPath = process.env.PATH || "",
  overrideSpec = null
) {
  if (overrideSpec) {
    if (typeof overrideSpec === "string") return { command: overrideSpec, prefix: [] };
    return {
      command: String(overrideSpec.command || overrideSpec.cmd || ""),
      prefix: Array.isArray(overrideSpec.prefix) ? [...overrideSpec.prefix] : [],
    };
  }
  const candidates =
    platform === "win32"
      ? [
          { cmd: "py", prefix: ["-3"] },
          { cmd: "python3", prefix: [] },
          { cmd: "python", prefix: [] },
        ]
      : [
          { cmd: "python3", prefix: [] },
          { cmd: "python", prefix: [] },
        ];
  if (envPath) {
    for (const cand of candidates) {
      const hit = findRealExecutable(cand.cmd, envPath, platform, isWindowsAppsStub);
      if (hit) return { command: hit, prefix: cand.prefix };
    }
  }
  return platform === "win32"
    ? { command: "py", prefix: ["-3"] }
    : { command: "python3", prefix: [] };
}

function defaultPluginDataDir(env, homeDir) {
  const home = homeDir || env?.HOME || env?.USERPROFILE || os.homedir();
  return path.join(home, ".gemini", "antigravity", "plugin_data", "tdq-workflow-agy");
}

export function resolveSecretsEnvPath(env = process.env, homeDir = os.homedir()) {
  const stateDir = String(env?.TDQ_SETUP_STATE_DIR || "").trim();
  if (stateDir) return path.join(stateDir, "secrets.env");
  if (env?.TDQ_KHONG_CHAM_MAY !== "1") {
    const pluginData = String(env?.PLUGIN_DATA || "").trim();
    if (pluginData) return path.join(pluginData, "secrets.env");
  }
  return path.join(defaultPluginDataDir(env, homeDir), "secrets.env");
}

function unescapeDoubleQuoted(raw) {
  return raw.replace(/\\(["\\ntr])/g, (_, ch) => {
    if (ch === "n") return "\n";
    if (ch === "r") return "\r";
    if (ch === "t") return "\t";
    return ch;
  });
}

export function parseSecretsEnv(content) {
  const out = {};
  for (const rawLine of String(content || "").split(/\r?\n/)) {
    let line = rawLine.trim();
    if (!line || line.startsWith("#")) continue;
    if (line.startsWith("export ")) line = line.slice(7).trimStart();
    const eqIdx = line.indexOf("=");
    if (eqIdx <= 0) continue;
    const key = line.slice(0, eqIdx).trim();
    if (!/^[A-Za-z_][A-Za-z0-9_]*$/.test(key)) continue;
    let val = line.slice(eqIdx + 1).trim();
    if (val.length >= 2 && val.startsWith('"') && val.endsWith('"')) {
      val = unescapeDoubleQuoted(val.slice(1, -1));
    } else if (val.length >= 2 && val.startsWith("'") && val.endsWith("'")) {
      val = val.slice(1, -1);
    } else {
      val = val.replace(/\s+#.*$/, "").trim();
    }
    out[key] = val;
  }
  return out;
}

export function loadSecretsEnv(
  env = process.env,
  homeDir = os.homedir(),
  explicitPath = null
) {
  const target = explicitPath || resolveSecretsEnvPath(env, homeDir);
  if (!target) return {};
  try {
    const content = fs.readFileSync(target, "utf8");
    const parsed = parseSecretsEnv(content);
    const count = Object.keys(parsed).length;
    if (count > 0) logInfo(`loaded ${count} env key(s) from secrets.env`);
    return parsed;
  } catch {
    return {};
  }
}

export function buildChildEnv(
  baseEnv = process.env,
  homeDir = os.homedir(),
  platform = process.platform
) {
  const env = { ...baseEnv };
  const secrets = loadSecretsEnv(baseEnv, homeDir);
  for (const [key, val] of Object.entries(secrets)) {
    if (!(key in env) || env[key] === undefined || env[key] === "") {
      env[key] = val;
    }
  }
  env.PATH = expandUserPath(env.PATH || "", homeDir, platform, env);
  return env;
}

export function buildSpawnSpec(
  mode,
  forwardedArgs = [],
  platform = process.platform,
  lspCmd = "agent-lsp",
  pythonSpec = null
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
  if (mode === "caveman") {
    const dashIdx = forwardedArgs.indexOf("--");
    if (dashIdx === -1) {
      throw new Error("Caveman mode requires '--' separator before target command");
    }
    const beforeDash = forwardedArgs.slice(0, dashIdx);
    const afterDash = forwardedArgs.slice(dashIdx + 1);
    if (afterDash.length === 0) {
      throw new Error("Caveman mode requires a target command after '--'");
    }
    const here = path.dirname(fileURLToPath(import.meta.url));
    const shrinkScriptPath = path.join(here, "tdq_mcp_shrink.py");
    const hostPath =
      platform === process.platform
        ? expandUserPath(process.env.PATH || "", os.homedir(), platform)
        : "";
    const py = resolvePythonSpec(platform, hostPath, pythonSpec);
    return {
      command: py.command,
      args: [...py.prefix, "-u", shrinkScriptPath, ...beforeDash, "--", ...afterDash],
      shell: false,
    };
  }
  throw new Error(`Unsupported MCP launcher mode: ${mode}`);
}

function expandTemplateArgs(args, pluginRoot, env) {
  const pluginData =
    String(env?.TDQ_SETUP_STATE_DIR || env?.PLUGIN_DATA || "").trim() ||
    defaultPluginDataDir(env, os.homedir());
  return args.map((arg) =>
    String(arg)
      .replaceAll("${PLUGIN_ROOT}", pluginRoot)
      .replaceAll("${PLUGIN_DATA}", pluginData)
  );
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
  const here = path.dirname(fileURLToPath(import.meta.url));
  const pluginRoot = path.resolve(here, "..");
  const childEnv = buildChildEnv(process.env, os.homedir(), process.platform);
  const resolvedArgs = expandTemplateArgs(forwarded, pluginRoot, childEnv);
  try {
    ensureUserDataDir(resolvedArgs);
  } catch (err) {
    logInfo(`failed creating userDataDir: ${err.message}`);
  }
  const override = childEnv.TDQ_MCP_OVERRIDE_CMD;
  const resolvedLsp =
    mode === "lsp" ? override || resolveAgentLspCommand(childEnv.PATH) : "agent-lsp";
  const pySpec =
    mode === "caveman" ? resolvePythonSpec(process.platform, childEnv.PATH) : null;
  const spec = buildSpawnSpec(mode, resolvedArgs, process.platform, resolvedLsp, pySpec);
  logInfo(`launching mode=${mode} cmd=${spec.command}`);

  const child = spawn(spec.command, spec.args, {
    env: childEnv,
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
