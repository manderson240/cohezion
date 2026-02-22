/**
 * Compound engineering tasks for Cohezion.
 *
 * Self-improvement loop tasks:
 * - Skill refinement (daily at 10 AM)
 * - Retrospection analysis (daily at 10 PM)
 * - Journey audit (daily at 2 PM)
 * - Vault compilation (weekly on Monday)
 */

import { schedules, task, queue } from "@trigger.dev/sdk";
import { python } from "@trigger.dev/python";

const compoundQueue = queue({
  name: "cohezion-compound",
  concurrencyLimit: 2,
});

// ---------------------------------------------------------------------------
// Skill Refinement (daily at 10 AM UTC)
// ---------------------------------------------------------------------------

export const skillRefinementTask = schedules.task({
  id: "compound/skill-refinement",
  queue: compoundQueue,
  cron: {
    pattern: "0 10 * * *",
    timezone: "UTC",
  },
  run: async (payload) => {
    const result = await python.runScript(
      "../src/cohezion/triggers/runners/compound.py",
      ["skill-refinement"]
    );
    const parsed = JSON.parse(result.stdout);

    if (parsed.refinements?.length > 0) {
      console.log(
        `[SKILLS] ${parsed.refinements.length} skill refinement(s) applied`
      );
    }

    return parsed;
  },
});

// ---------------------------------------------------------------------------
// Retrospection (daily at 10 PM UTC)
// ---------------------------------------------------------------------------

export const retrospectionTask = schedules.task({
  id: "compound/retrospection",
  queue: compoundQueue,
  cron: {
    pattern: "0 22 * * *",
    timezone: "UTC",
  },
  run: async (payload) => {
    const result = await python.runScript(
      "../src/cohezion/triggers/runners/compound.py",
      ["retrospection"]
    );
    return JSON.parse(result.stdout);
  },
});

// ---------------------------------------------------------------------------
// Journey Audit (daily at 2 PM UTC)
// ---------------------------------------------------------------------------

export const journeyAuditTask = schedules.task({
  id: "compound/journey-audit",
  queue: compoundQueue,
  cron: {
    pattern: "0 14 * * *",
    timezone: "UTC",
  },
  run: async (payload) => {
    const result = await python.runScript(
      "../src/cohezion/triggers/runners/compound.py",
      ["journey-audit"]
    );
    return JSON.parse(result.stdout);
  },
});

// ---------------------------------------------------------------------------
// Vault Compilation (weekly on Monday at 9 AM UTC)
// ---------------------------------------------------------------------------

export const vaultCompileTask = schedules.task({
  id: "compound/vault-compile",
  queue: compoundQueue,
  cron: {
    pattern: "0 9 * * 1",
    timezone: "UTC",
  },
  run: async (payload) => {
    const result = await python.runScript(
      "../src/cohezion/triggers/runners/compound.py",
      ["vault-compile"]
    );
    return JSON.parse(result.stdout);
  },
});

// ---------------------------------------------------------------------------
// On-demand compound task
// ---------------------------------------------------------------------------

export const compoundOnDemand = task({
  id: "compound/on-demand",
  queue: compoundQueue,
  run: async (payload: {
    task:
      | "skill-refinement"
      | "retrospection"
      | "journey-audit"
      | "vault-compile";
    params?: Record<string, unknown>;
  }) => {
    const cmdArgs = [payload.task];
    if (payload.params) {
      cmdArgs.push(JSON.stringify(payload.params));
    }

    const result = await python.runScript(
      "../src/cohezion/triggers/runners/compound.py",
      cmdArgs
    );
    return JSON.parse(result.stdout);
  },
});
