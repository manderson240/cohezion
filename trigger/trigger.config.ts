import { defineConfig } from "@trigger.dev/sdk";
import { pythonExtension } from "@trigger.dev/python/extension";

export default defineConfig({
  project: process.env.TRIGGER_PROJECT_REF ?? "cohezion",
  runtime: "node",
  logLevel: "info",
  maxDuration: 28800, // 8 hours max for training pipelines
  retries: {
    enabledInDev: false,
    default: {
      maxAttempts: 3,
      minTimeoutInMs: 1000,
      maxTimeoutInMs: 30000,
      factor: 2,
    },
  },
  dirs: ["src/trigger"],
  build: {
    extensions: [
      pythonExtension({
        // Include all Python runner scripts
        scripts: ["../src/cohezion/triggers/runners/**/*.py"],
        requirementsFile: "../requirements-trigger.txt",
        devPythonBinaryPath: "../.venv/bin/python",
      }),
    ],
  },
});
