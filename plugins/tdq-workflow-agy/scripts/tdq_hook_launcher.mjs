import { spawnSync } from "node:child_process";
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
  process.stderr.write(`[${stamp}] tdq_hook_launcher: ${message}\n`);
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
  process.stdout.write("{}\n");
  return 0;
}

const isCli =
  process.argv[1] &&
  path.resolve(process.argv[1]) === path.resolve(fileURLToPath(import.meta.url));
if (isCli) process.exit(main());
