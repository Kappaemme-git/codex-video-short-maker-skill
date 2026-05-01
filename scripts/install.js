#!/usr/bin/env node

const { spawnSync } = require("child_process");
const fs = require("fs");
const os = require("os");
const path = require("path");

const args = process.argv.slice(2);

function usage() {
  console.log(`
Codex Video Short Maker Skill installer

Usage:
  npx codex-video-short-maker-skill
  npx codex-video-short-maker-skill --with-captions
  codex-video-short-maker-skill --skills-dir ~/.codex/skills

Options:
  --with-captions      Install local Whisper captions support too
  --caption-model NAME Model for setup: tiny.en, base.en, tiny, base
  --skills-dir PATH    Install into a custom Codex skills directory
  --help              Show this help
`);
}

function expandHome(value) {
  if (!value) return value;
  if (value === "~") return os.homedir();
  if (value.startsWith("~/")) return path.join(os.homedir(), value.slice(2));
  return value;
}

function parseArgs(argv) {
  const options = { withCaptions: false, captionModel: "tiny.en" };

  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];

    if (arg === "--help" || arg === "-h") {
      options.help = true;
      continue;
    }

    if (arg === "--with-captions") {
      options.withCaptions = true;
      continue;
    }

    if (arg === "--caption-model") {
      const value = argv[index + 1];
      if (!value) throw new Error("--caption-model requires a value");
      options.captionModel = value;
      index += 1;
      continue;
    }

    if (arg === "--skills-dir") {
      const value = argv[index + 1];
      if (!value) throw new Error("--skills-dir requires a path");
      options.skillsDir = expandHome(value);
      index += 1;
      continue;
    }

    throw new Error(`Unknown option: ${arg}`);
  }

  return options;
}

function defaultSkillsDir() {
  const codexHome = process.env.CODEX_HOME || path.join(os.homedir(), ".codex");
  return path.join(codexHome, "skills");
}

function copyDirectory(source, destination) {
  fs.mkdirSync(destination, { recursive: true });

  for (const entry of fs.readdirSync(source, { withFileTypes: true })) {
    const sourcePath = path.join(source, entry.name);
    const destinationPath = path.join(destination, entry.name);

    if (entry.isDirectory()) {
      copyDirectory(sourcePath, destinationPath);
    } else if (entry.isFile()) {
      fs.copyFileSync(sourcePath, destinationPath);
    }
  }
}

function run(command, args, cwd) {
  const result = spawnSync(command, args, {
    cwd,
    stdio: "inherit",
    shell: false,
  });
  if (result.status !== 0) {
    process.exit(result.status || 1);
  }
}

function main() {
  const options = parseArgs(args);

  if (options.help) {
    usage();
    return;
  }

  const source = path.resolve(__dirname, "..", "video-short-maker");
  const skillsDir = path.resolve(options.skillsDir || defaultSkillsDir());
  const destination = path.join(skillsDir, "video-short-maker");

  if (!fs.existsSync(source)) {
    throw new Error(`Cannot find bundled skill at ${source}`);
  }

  fs.mkdirSync(skillsDir, { recursive: true });
  fs.rmSync(destination, { recursive: true, force: true });
  copyDirectory(source, destination);

  console.log("Installed video-short-maker skill.");
  console.log(`Location: ${destination}`);

  if (options.withCaptions) {
    console.log("");
    console.log("Setting up local captions support...");
    run("python3", [
      path.join(destination, "scripts", "setup_captions.py"),
      "--model",
      options.captionModel,
    ], destination);
  }

  console.log("");
  console.log("Restart Codex, then run:");
  console.log(
    "  Use $video-short-maker to create a 30s vertical short with English captions from ./demo.mp4 using aggressive cut style."
  );
}

try {
  main();
} catch (error) {
  console.error(`Error: ${error.message}`);
  process.exit(1);
}
