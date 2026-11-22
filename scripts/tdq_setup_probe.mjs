#!/usr/bin/env node
/**
 * Zero-dependency Node ESM pre-flight toolchain probe for Google Antigravity setup.
 * Used at Gate 0/1 when Python is absent or points to a WindowsApps Store stub.
 */
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

const MIN_NODE_MAJOR = 18;
const PROBE_TIMEOUT_MS = 1500;

function logEnabled(env = process.env) {
  return env?.TDQ_LOG !== "0";
}

function logInfo(message, env = process.env) {
  if (!logEnabled(env)) return;
  const stamp = new Date().toISOString().slice(0, 19);
  process.stderr.write(`[${stamp}] tdq_setup_probe: ${message}\n`);
}

export function isWindowsAppsStub(execPath) {
  return String(execPath || "").toLowerCase().includes("windowsapps");
}

export function parseSemver(text) {
  const match = String(text || "").match(/v?(\d+)\.(\d+)(?:\.(\d+))?/);
  if (!match) return null;
  const major = Number.parseInt(match[1], 10);
  const minor = Number.parseInt(match[2], 10);
  const patch = Number.parseInt(match[3] || "0", 10);
  return { raw: `${major}.${minor}.${patch}`, major, minor, patch };
}

function isExecutableFile(candidate, platform) {
  try {
    const st = fs.statSync(candidate);
    if (!st.isFile()) return false;
    if (platform !== "win32" && process.platform !== "win32") {
      return (st.mode & 0o111) !== 0;
    }
    return true;
  } catch {
    return false;
  }
}

function firstExistingDir(dirs) {
  return dirs.filter((d) => typeof d === "string" && d.length > 0);
}

function resolveNvmNodeBins(home) {
  const nvmVersions = path.join(home, ".nvm", "versions", "node");
  const out = [path.join(home, ".nvm", "current", "bin")];
  try {
    const entries = fs.readdirSync(nvmVersions).sort().reverse();
    for (const ver of entries.slice(0, 3)) {
      out.push(path.join(nvmVersions, ver, "bin"));
    }
  } catch {}
  return out;
}

function collectUserSpaceDirs(env, platform) {
  const home = env?.HOME || env?.USERPROFILE || "";
  if (!home) return [];
  const base = [
    path.join(home, ".local", "bin"),
    path.join(home, ".cargo", "bin"),
    path.join(home, ".npm-global", "bin"),
  ];
  if (platform === "win32") {
    const appData = env.APPDATA || path.join(home, "AppData", "Roaming");
    const localAppData = env.LOCALAPPDATA || path.join(home, "AppData", "Local");
    base.push(
      path.join(localAppData, "agy", "bin"),
      path.join(appData, "fnm", "aliases", "default"),
      path.join(home, ".local", "share", "fnm", "aliases", "default")
    );
    if (env.NVM_SYMLINK) base.push(env.NVM_SYMLINK);
    return base;
  }
  base.push(
    path.join(home, ".local", "share", "fnm", "aliases", "default"),
    path.join(home, ".fnm", "aliases", "default"),
    ...resolveNvmNodeBins(home)
  );
  if (platform === "darwin") base.push("/opt/homebrew/bin");
  base.push("/usr/local/bin");
  return base;
}

function collectSearchDirs(env = process.env, platform = process.platform) {
  const sep = platform === "win32" ? ";" : ":";
  const rawPath = env?.PATH ?? env?.Path ?? "";
  const fromPath = String(rawPath)
    .split(sep)
    .map((p) => p.trim().replace(/^"+|"+$/g, ""))
    .filter((p) => p && p !== ".");
  const merged = [...fromPath, ...collectUserSpaceDirs(env, platform)];
  const seen = new Set();
  const out = [];
  for (const dir of firstExistingDir(merged)) {
    const norm = platform === "win32" ? dir.toLowerCase() : dir;
    if (!seen.has(norm)) {
      seen.add(norm);
      out.push(dir);
    }
  }
  return out;
}

function extensionsFor(name, platform) {
  if (platform !== "win32") return [""];
  if (/\.(exe|cmd|bat)$/i.test(name)) return [""];
  return [".exe", ".cmd", ".bat"];
}

function findCandidates(names, dirs, platform) {
  const hits = [];
  for (const dir of dirs) {
    for (const name of names) {
      for (const ext of extensionsFor(name, platform)) {
        const cand = path.join(dir, `${name}${ext}`);
        if (isExecutableFile(cand, platform)) {
          hits.push({ name, path: cand });
        }
      }
    }
  }
  return hits;
}

function runCandidate(exePath, args, env, platform) {
  const isBatch = platform === "win32" && /\.(cmd|bat)$/i.test(exePath);
  const cmd = isBatch ? env?.ComSpec || process.env.ComSpec || "cmd.exe" : exePath;
  const fullArgs = isBatch ? ["/d", "/c", exePath, ...args] : args;
  return spawnSync(cmd, fullArgs, {
    env,
    encoding: "utf8",
    timeout: PROBE_TIMEOUT_MS,
    windowsHide: true,
    stdio: ["ignore", "pipe", "pipe"],
  });
}

function probeBinary(names, versionArgs, dirs, env, platform, validateFn = null) {
  const candidates = findCandidates(names, dirs, platform);
  if (candidates.length === 0) {
    return { usable: false, path: null, version: null, reason: "not_found" };
  }
  let lastReason = "exec_failed";
  for (const cand of candidates) {
    const res = runCandidate(cand.path, versionArgs, env, platform);
    if (res.error || res.status !== 0) {
      lastReason = res.error?.code || `exit_${res.status ?? "err"}`;
      continue;
    }
    const output = `${res.stdout || ""}\n${res.stderr || ""}`.trim();
    const semver = parseSemver(output);
    const ver = semver?.raw || output.split(/\r?\n/)[0]?.trim() || null;
    if (validateFn) {
      const check = validateFn(cand.path, output, semver);
      if (!check.ok) {
        lastReason = check.reason;
        continue;
      }
    }
    return { usable: true, path: cand.path, version: ver, reason: "ok" };
  }
  return { usable: false, path: candidates[0].path, version: null, reason: lastReason };
}

function probeNode(dirs, env, platform) {
  const base = probeBinary(
    ["node"],
    ["--version"],
    dirs,
    env,
    platform,
    (_p, _out, semver) => {
      if (!semver) return { ok: false, reason: "version_parse_failed" };
      if (semver.major < MIN_NODE_MAJOR) {
        return { ok: false, reason: `version_below_${MIN_NODE_MAJOR}` };
      }
      return { ok: true };
    }
  );
  const semver = parseSemver(base.version);
  return { ...base, major: semver?.major ?? null, min_major: MIN_NODE_MAJOR };
}

function probePython(dirs, env, platform) {
  const candidates = findCandidates(["python3", "python", "py"], dirs, platform);
  let windowsAppsRejected = false;
  let lastReason = "not_found";
  for (const cand of candidates) {
    if (isWindowsAppsStub(cand.path)) {
      windowsAppsRejected = true;
      lastReason = "windowsapps_stub_rejected";
      continue;
    }
    const args =
      cand.name === "py"
        ? ["-3", "-c", "import sys; print(sys.version.split()[0])"]
        : ["-c", "import sys; print(sys.version.split()[0])"];
    const res = runCandidate(cand.path, args, env, platform);
    if (res.error || res.status !== 0) {
      lastReason = res.error?.code || `exit_${res.status ?? "err"}`;
      continue;
    }
    const ver = parseSemver(res.stdout);
    if (!ver || ver.major < 3) {
      lastReason = ver ? `python_major_${ver.major}` : "invalid_python_output";
      continue;
    }
    return {
      usable: true,
      path: cand.path,
      command: cand.name === "py" ? "py -3" : cand.name,
      version: ver.raw,
      windowsapps_rejected: windowsAppsRejected,
      reason: "ok",
    };
  }
  return {
    usable: false,
    path: null,
    command: null,
    version: null,
    windowsapps_rejected: windowsAppsRejected,
    reason: windowsAppsRejected && lastReason === "not_found" ? "windowsapps_stub_only" : lastReason,
  };
}

function probeRtk(dirs, env, platform) {
  return probeBinary(["rtk"], ["--version"], dirs, env, platform, (exePath) => {
    const gainRes = runCandidate(exePath, ["gain", "--help"], env, platform);
    if (gainRes.error || gainRes.status !== 0) {
      return { ok: false, reason: "collision_or_invalid_rtk" };
    }
    return { ok: true };
  });
}

function fixedBrowserPaths(env, platform) {
  const home = env?.HOME || env?.USERPROFILE || "";
  if (platform === "win32") {
    const roots = firstExistingDir([
      env?.ProgramFiles,
      env?.["ProgramFiles(x86)"],
      env?.LOCALAPPDATA || (home ? path.join(home, "AppData", "Local") : ""),
    ]);
    const rels = [
      path.join("Google", "Chrome", "Application", "chrome.exe"),
      path.join("Microsoft", "Edge", "Application", "msedge.exe"),
      path.join("Chromium", "Application", "chrome.exe"),
      path.join("BraveSoftware", "Brave-Browser", "Application", "brave.exe"),
    ];
    return roots.flatMap((root) => rels.map((rel) => path.join(root, rel)));
  }
  if (platform === "darwin") {
    const list = [
      "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
      "/Applications/Chromium.app/Contents/MacOS/Chromium",
      "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    ];
    if (home) {
      list.push(path.join(home, "Applications/Google Chrome.app/Contents/MacOS/Google Chrome"));
    }
    return list;
  }
  return [
    "/usr/bin/google-chrome",
    "/usr/bin/google-chrome-stable",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
    "/usr/bin/microsoft-edge",
  ];
}

function probeBrowser(dirs, env, platform) {
  const binNames =
    platform === "win32"
      ? ["chrome", "msedge", "chromium", "brave"]
      : ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "microsoft-edge"];
  for (const cand of findCandidates(binNames, dirs, platform)) {
    return { usable: true, path: cand.path, version: null, reason: "ok" };
  }
  for (const fixed of fixedBrowserPaths(env, platform)) {
    if (isExecutableFile(fixed, platform)) {
      return { usable: true, path: fixed, version: null, reason: "ok" };
    }
  }
  return { usable: false, path: null, version: null, reason: "not_found" };
}

function readPackageVersion(rootDir) {
  try {
    const pkg = JSON.parse(fs.readFileSync(path.join(rootDir, "package.json"), "utf8"));
    return pkg?.version ? String(pkg.version) : null;
  } catch {
    return null;
  }
}

function resolveArchifyEntry(rootDir) {
  for (const sub of [path.join(rootDir, "bin", "archify.mjs"), path.join(rootDir, "archify", "bin", "archify.mjs")]) {
    try {
      if (fs.statSync(sub).isFile()) {
        const pkgDir = path.dirname(path.dirname(sub));
        return { root: pkgDir, bin: sub, version: readPackageVersion(pkgDir) };
      }
    } catch {}
  }
  return null;
}

function probeArchify(env) {
  const explicit = String(env?.ARCHIFY_ROOT || "").trim();
  if (explicit) {
    const hit = resolveArchifyEntry(explicit);
    return hit
      ? { usable: true, path: hit.bin, root: hit.root, version: hit.version, reason: "ok" }
      : { usable: false, path: null, root: explicit, version: null, reason: "invalid_archify_root" };
  }
  const home = env?.HOME || env?.USERPROFILE || "";
  if (!home) {
    return { usable: false, path: null, root: null, version: null, reason: "not_found" };
  }
  const candidates = [
    path.join(home, ".local", "share", "archify"),
    path.join(home, "Documents", "archify"),
  ];
  for (const root of candidates) {
    const hit = resolveArchifyEntry(root);
    if (hit) {
      return { usable: true, path: hit.bin, root: hit.root, version: hit.version, reason: "ok" };
    }
  }
  return { usable: false, path: null, root: null, version: null, reason: "not_found" };
}

export function probeToolchain(env = process.env, platform = process.platform) {
  const t0 = Date.now();
  const safeEnv = env || {};
  const dirs = collectSearchDirs(safeEnv, platform);
  logInfo(`probing toolchain on ${platform} (${dirs.length} search dirs)`, safeEnv);

  const report = {
    schema_version: 1,
    platform,
    arch: process.arch,
    probed_at: new Date().toISOString().slice(0, 19) + "Z",
    git: probeBinary(["git"], ["--version"], dirs, safeEnv, platform),
    node: probeNode(dirs, safeEnv, platform),
    uv: probeBinary(["uv"], ["--version"], dirs, safeEnv, platform),
    python: probePython(dirs, safeEnv, platform),
    agy: probeBinary(["agy"], ["--version"], dirs, safeEnv, platform),
    "agent-lsp": probeBinary(["agent-lsp"], ["--version"], dirs, safeEnv, platform),
    rtk: probeRtk(dirs, safeEnv, platform),
    rg: probeBinary(["rg"], ["--version"], dirs, safeEnv, platform),
    browser: probeBrowser(dirs, safeEnv, platform),
    archify: probeArchify(safeEnv),
    elapsed_ms: Date.now() - t0,
  };
  logInfo(
    `probe complete in ${report.elapsed_ms}ms (node=${report.node.usable}, python=${report.python.usable}, git=${report.git.usable})`,
    safeEnv
  );
  return report;
}

export function main(argv = process.argv.slice(2)) {
  if (argv.includes("--help") || argv.includes("-h")) {
    process.stdout.write("Usage: node scripts/tdq_setup_probe.mjs [--json]\n");
    return 0;
  }
  const report = probeToolchain(process.env, process.platform);
  if (argv.includes("--json") || argv.length === 0) {
    process.stdout.write(JSON.stringify(report, null, 2) + "\n");
    return 0;
  }
  process.stderr.write("Unsupported flag; use --json or --help\n");
  return 2;
}

const isCli =
  process.argv[1] &&
  path.resolve(process.argv[1]) === path.resolve(fileURLToPath(import.meta.url));
if (isCli) process.exit(main());
