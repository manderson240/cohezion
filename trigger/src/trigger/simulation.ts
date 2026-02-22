/**
 * Universe simulation tasks for Cohezion.
 *
 * Long-running training pipelines and simulation tasks:
 * - Full training pipeline (weekly)
 * - Mass simulation data generation (Mon/Thu)
 * - FLUME VAE training (on-demand)
 * - RL policy training (on-demand)
 * - Universe bridge validation (on-demand)
 */

import { schedules, task, queue } from "@trigger.dev/sdk";
import { python } from "@trigger.dev/python";

// Simulation queue: strict concurrency to prevent resource contention
const simulationQueue = queue({
  name: "cohezion-simulation",
  concurrencyLimit: 1, // Only one simulation at a time
});

// ---------------------------------------------------------------------------
// Full Training Pipeline (weekly on Sunday midnight UTC)
// ---------------------------------------------------------------------------

export const trainingPipelineTask = schedules.task({
  id: "simulation/training-pipeline",
  queue: simulationQueue,
  cron: {
    pattern: "0 0 * * 0",
    timezone: "UTC",
  },
  // 8 hour max duration for overnight training
  maxDuration: 28800,
  run: async (payload) => {
    const args = JSON.stringify({ scale: "medium" });
    const result = await python.runScript(
      "../src/cohezion/triggers/runners/simulation.py",
      ["training-pipeline", args]
    );
    const parsed = JSON.parse(result.stdout);

    if (parsed.status === "failure") {
      console.error(
        `[PIPELINE] Training pipeline failed: ${parsed.errors?.join(", ")}`
      );
    } else {
      console.log(
        `[PIPELINE] Training pipeline completed: ${parsed.metrics?.steps_completed} steps`
      );
    }

    return parsed;
  },
});

// ---------------------------------------------------------------------------
// Mass Simulation (Mon and Thu at 2 AM UTC)
// ---------------------------------------------------------------------------

export const massSimTask = schedules.task({
  id: "simulation/mass-sim",
  queue: simulationQueue,
  cron: {
    pattern: "0 2 * * 1,4",
    timezone: "UTC",
  },
  run: async (payload) => {
    const args = JSON.stringify({ scale: "demo" });
    const result = await python.runScript(
      "../src/cohezion/triggers/runners/simulation.py",
      ["mass-sim", args]
    );
    return JSON.parse(result.stdout);
  },
});

// ---------------------------------------------------------------------------
// On-demand simulation tasks
// ---------------------------------------------------------------------------

export const flumeVaeTrainTask = task({
  id: "simulation/flume-vae-train",
  queue: simulationQueue,
  maxDuration: 7200,
  run: async (payload: { epochs?: number; data_dir?: string }) => {
    const args = JSON.stringify(payload);
    const result = await python.runScript(
      "../src/cohezion/triggers/runners/simulation.py",
      ["flume-vae-train", args]
    );
    return JSON.parse(result.stdout);
  },
});

export const rlPolicyTrainTask = task({
  id: "simulation/rl-policy-train",
  queue: simulationQueue,
  maxDuration: 7200,
  run: async (payload: { episodes?: number }) => {
    const args = JSON.stringify(payload);
    const result = await python.runScript(
      "../src/cohezion/triggers/runners/simulation.py",
      ["rl-policy-train", args]
    );
    return JSON.parse(result.stdout);
  },
});

export const universeBridgeTask = task({
  id: "simulation/universe-bridge",
  queue: simulationQueue,
  run: async (payload: Record<string, unknown>) => {
    const result = await python.runScript(
      "../src/cohezion/triggers/runners/simulation.py",
      ["universe-bridge"]
    );
    return JSON.parse(result.stdout);
  },
});

// ---------------------------------------------------------------------------
// Custom pipeline trigger (any scale)
// ---------------------------------------------------------------------------

export const pipelineOnDemand = task({
  id: "simulation/pipeline-ondemand",
  queue: simulationQueue,
  maxDuration: 43200, // 12 hours
  run: async (payload: { scale: "demo" | "medium" | "overnight" }) => {
    const args = JSON.stringify(payload);
    const result = await python.runScript(
      "../src/cohezion/triggers/runners/simulation.py",
      ["training-pipeline", args]
    );
    return JSON.parse(result.stdout);
  },
});
