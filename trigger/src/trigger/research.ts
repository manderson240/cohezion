/**
 * Research lab tasks for Cohezion.
 *
 * Automated research operations:
 * - Model scouting (daily at 6 AM)
 * - Paper ingestion (daily at 8 AM)
 * - Experiment analysis (daily at noon)
 */

import { schedules, task, queue } from "@trigger.dev/sdk";
import { python } from "@trigger.dev/python";

const researchQueue = queue({
  name: "cohezion-research",
  concurrencyLimit: 2,
});

// ---------------------------------------------------------------------------
// Model Scout (daily at 6 AM UTC)
// ---------------------------------------------------------------------------

export const modelScoutTask = schedules.task({
  id: "research/model-scout",
  queue: researchQueue,
  cron: {
    pattern: "0 6 * * *",
    timezone: "UTC",
  },
  run: async (payload) => {
    const result = await python.runScript(
      "../src/cohezion/triggers/runners/research.py",
      ["model-scout"]
    );
    const parsed = JSON.parse(result.stdout);

    // Log recommendations
    if (parsed.findings?.length > 0) {
      const installs = parsed.findings.filter(
        (f: any) => f.action === "install"
      );
      if (installs.length > 0) {
        console.log(
          `[SCOUT] ${installs.length} model upgrade(s) recommended:`,
          installs.map((i: any) => i.model).join(", ")
        );
      }
    }

    return parsed;
  },
});

// ---------------------------------------------------------------------------
// Paper Ingestion (daily at 8 AM UTC)
// ---------------------------------------------------------------------------

export const paperIngestTask = schedules.task({
  id: "research/paper-ingest",
  queue: researchQueue,
  cron: {
    pattern: "0 8 * * *",
    timezone: "UTC",
  },
  run: async (payload) => {
    const result = await python.runScript(
      "../src/cohezion/triggers/runners/research.py",
      ["paper-ingest"]
    );
    return JSON.parse(result.stdout);
  },
});

// ---------------------------------------------------------------------------
// Experiment Analysis (daily at noon UTC)
// ---------------------------------------------------------------------------

export const experimentAnalysisTask = schedules.task({
  id: "research/experiment-analysis",
  queue: researchQueue,
  cron: {
    pattern: "0 12 * * *",
    timezone: "UTC",
  },
  run: async (payload) => {
    const result = await python.runScript(
      "../src/cohezion/triggers/runners/research.py",
      ["experiment-analysis"]
    );
    return JSON.parse(result.stdout);
  },
});

// ---------------------------------------------------------------------------
// On-demand research task
// ---------------------------------------------------------------------------

export const researchOnDemand = task({
  id: "research/on-demand",
  queue: researchQueue,
  run: async (payload: {
    task: "model-scout" | "paper-ingest" | "experiment-analysis";
    params?: Record<string, unknown>;
  }) => {
    const args = payload.params ? JSON.stringify(payload.params) : "";
    const cmdArgs = [payload.task];
    if (args) cmdArgs.push(args);

    const result = await python.runScript(
      "../src/cohezion/triggers/runners/research.py",
      cmdArgs
    );
    return JSON.parse(result.stdout);
  },
});
