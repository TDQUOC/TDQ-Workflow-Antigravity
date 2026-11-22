import { spawn } from "node:child_process";
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
