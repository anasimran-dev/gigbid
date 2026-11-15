import { defineConfig, devices } from "@playwright/test";

// Starts the API (offline profile, runs inline so tests are deterministic) and the Vite dev server.
export default defineConfig({
  testDir: "tests/e2e",
  timeout: 60_000,
  reporter: [["html", { open: "never" }], ["list"]],
  use: { baseURL: "http://localhost:5173", trace: "retain-on-failure" },
  projects: [
    { name: "laptop", use: { ...devices["Desktop Chrome"] } },
    { name: "phone", use: { ...devices["Pixel 7"] } },
  ],
  webServer: [
    {
      command: "uvicorn apps.api.main:app --port 8000",
      cwd: "../..",
      url: "http://localhost:8000/health",
      reuseExistingServer: true,
      env: { MODEL_PROFILE: "offline", GIGBID_SYNC: "1", APP_DB: "data/processed/e2e.db", MARKETPLACE_RPM: "100000" },
    },
    { command: "npm run dev", url: "http://localhost:5173", reuseExistingServer: true },
  ],
});
