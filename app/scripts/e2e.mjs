// Build the static app against the e2e backend (port 8100), then run Playwright.
import { spawnSync } from "node:child_process";

const env = { ...process.env, NEXT_PUBLIC_API_URL: "http://localhost:8100" };
const run = (cmd, args) => spawnSync(cmd, args, { stdio: "inherit", env, shell: process.platform === "win32" });

const build = run("npm", ["run", "build"]);
if (build.status !== 0) process.exit(build.status ?? 1);
const tests = run("npx", ["playwright", "test", ...process.argv.slice(2)]);
process.exit(tests.status ?? 1);
