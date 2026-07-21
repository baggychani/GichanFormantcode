import { execFileSync } from "node:child_process";
import {
  cpSync,
  existsSync,
  mkdirSync,
  renameSync,
  rmSync,
} from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const scriptDir = dirname(fileURLToPath(import.meta.url));
const desktopRoot = resolve(scriptDir, "..");
const projectRoot = resolve(desktopRoot, "..");
const tauriRoot = join(desktopRoot, "src-tauri");
const binariesDir = join(tauriRoot, "binaries");
const stagingDir = join(tauriRoot, ".sidecar-build");
const isWindows = process.platform === "win32";
const extension = isWindows ? ".exe" : "";
const baseName = "gichan-formant-sidecar";

function hostTriple() {
  try {
    return execFileSync("rustc", ["--print", "host-tuple"], {
      encoding: "utf8",
    }).trim();
  } catch {
    const verbose = execFileSync("rustc", ["-Vv"], { encoding: "utf8" });
    const host = verbose.match(/^host:\s+(.+)$/m)?.[1]?.trim();
    if (!host) throw new Error("Rust target triple을 확인할 수 없습니다.");
    return host;
  }
}

const targetTriple = process.env.TAURI_ENV_TARGET_TRIPLE || hostTriple();
const outputName = `${baseName}-${targetTriple}${extension}`;
const outputPath = join(binariesDir, outputName);
const internalOut = join(binariesDir, "_internal");
// onedir layout: dist/<name>/<name>.exe + dist/<name>/_internal/
const stagedDir = join(stagingDir, "dist", baseName);
const stagedExecutable = join(stagedDir, `${baseName}${extension}`);
const stagedInternal = join(stagedDir, "_internal");

// Never silently reuse an old sidecar. The binary is intentionally ignored by
// git, so reuse can package code from a different checkout/commit and make the
// desktop app disagree with the Python sources. Build caching belongs to uv
// and PyInstaller's caches, not to an unversioned executable in binaries/.
if (existsSync(outputPath)) {
  console.log(`Refreshing bundled sidecar: ${outputPath}`);
}

mkdirSync(binariesDir, { recursive: true });
rmSync(stagingDir, { recursive: true, force: true });
mkdirSync(stagingDir, { recursive: true });

const separator = isWindows ? ";" : ":";
const pyinstallerArgs = [
  "run",
  "pyinstaller",
  "--noconfirm",
  "--clean",
  // onedir avoids extract-to-temp on every launch (onefile tax on laptops/AV).
  "--onedir",
  "--console",
  "--name",
  baseName,
  "--distpath",
  join(stagingDir, "dist"),
  "--workpath",
  join(stagingDir, "work"),
  "--specpath",
  join(stagingDir, "spec"),
  "--add-data",
  `${join(projectRoot, "assets")}${separator}assets`,
  "--hidden-import",
  "sidecar.desktop",
  "--hidden-import",
  "ui.desktop_window_coordinator",
  join(projectRoot, "sidecar_main.py"),
];

console.log(`Preparing bundled sidecar for ${targetTriple}...`);
execFileSync("uv", pyinstallerArgs, {
  cwd: projectRoot,
  stdio: "inherit",
});

if (!existsSync(stagedExecutable)) {
  throw new Error(`PyInstaller output was not created: ${stagedExecutable}`);
}
if (!existsSync(stagedInternal)) {
  throw new Error(`PyInstaller _internal folder missing: ${stagedInternal}`);
}

rmSync(outputPath, { force: true });
rmSync(internalOut, { recursive: true, force: true });
renameSync(stagedExecutable, outputPath);
cpSync(stagedInternal, internalOut, { recursive: true });
rmSync(stagingDir, { recursive: true, force: true });
console.log(`Bundled sidecar ready: ${outputPath}`);
console.log(`Bundled sidecar deps: ${internalOut}`);
