import { defineConfig, devices } from "@playwright/test";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";

// End-to-end tests drive the real backend (FAKE face engine, throwaway database)
// and the static build of the app. Build first: `npm run build`.
const venv = resolve(__dirname, "..", "backend", ".venv");
const python = `"${process.platform === "win32" ? join(venv, "Scripts", "python.exe") : join(venv, "bin", "python")}"`;
const backendDir = `"${resolve(__dirname, "..", "backend")}"`;
const db = join(tmpdir(), `armor-e2e-${Date.now()}.db`).replace(/\\/g, "/");

export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  fullyParallel: false,
  workers: 1,
  reporter: [["list"]],
  use: {
    baseURL: "http://localhost:3100",
    ...devices["Pixel 7"],
    // CI installs Playwright Chromium; on Windows laptops the installed Chrome is used.
    channel: process.env.PW_CHANNEL ?? (process.platform === "win32" ? "chrome" : undefined),
    permissions: ["camera"],
    launchOptions: {
      args: ["--use-fake-device-for-media-stream", "--use-fake-ui-for-media-stream"],
    },
  },
  webServer: [
    {
      command: `${python} -m uvicorn app.main:app --app-dir ${backendDir} --port 8100`,
      url: "http://localhost:8100/health",
      reuseExistingServer: false,
      env: {
        ARMOR_ENV_FILE: "",
        DATABASE_URL: `sqlite:///${db}`,
        JWT_SECRET: "e2e-secret-e2e-secret-e2e-secret-e2e",
        ARMOR_EMBEDDING_KEY: "0uU6ncXf6QZ7hU0T8y6W3Ja4rHfEo5h7m8yGxS2sR1E=",
        CORS_ORIGINS: "http://localhost:3100",
        FACE_ENGINE: "fake",
        BCRYPT_ROUNDS: "4",
        MODEL_DIR: join(tmpdir(), "armor-e2e-models"),
      },
    },
    {
      command: `${python} -m http.server 3100 --directory out`,
      url: "http://localhost:3100/",
      reuseExistingServer: false,
    },
  ],
});
