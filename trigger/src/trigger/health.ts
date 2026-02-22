/**
 * Health monitoring tasks for Cohezion.
 *
 * Scheduled background tasks that keep the project healthy:
 * - Test suite runs (every 6 hours)
 * - Repository hygiene checks (daily)
 * - Security audits (daily)
 * - System metrics snapshots (every 30 min)
 * - HIHO degradation checks (every 2 hours)
 * - Database pruning (weekly)
 */

import { schedules, task, queue } from "@trigger.dev/sdk";
import { python } from "@trigger.dev/python";

// Queue: health tasks share concurrency to avoid overloading the system
const healthQueue = queue({
  name: "cohezion-health",
  concurrencyLimit: 2,
});

// ---------------------------------------------------------------------------
// Test Suite (every 6 hours)
// ---------------------------------------------------------------------------

export const testSuiteTask = schedules.task({
  id: "health/test-suite",
  queue: healthQueue,
  cron: {
    pattern: "0 */6 * * *",
    timezone: "UTC",
  },
  run: async (payload) => {
    const args = JSON.stringify({ scope: "tests/", verbose: false });
    const result = await python.runScript(
      "../src/cohezion/triggers/runners/health.py",
      ["test-suite", args]
    );
    return JSON.parse(result.stdout);
  },
});

// On-demand test suite trigger
export const testSuiteOnDemand = task({
  id: "health/test-suite-ondemand",
  queue: healthQueue,
  run: async (payload: { scope?: string; markers?: string }) => {
    const args = JSON.stringify(payload);
    const result = await python.runScript(
      "../src/cohezion/triggers/runners/health.py",
      ["test-suite", args]
    );
    return JSON.parse(result.stdout);
  },
});

// ---------------------------------------------------------------------------
// Repository Hygiene (daily at 3 AM UTC)
// ---------------------------------------------------------------------------

export const repoHygieneTask = schedules.task({
  id: "health/repo-hygiene",
  queue: healthQueue,
  cron: {
    pattern: "0 3 * * *",
    timezone: "UTC",
  },
  run: async (payload) => {
    const result = await python.runScript(
      "../src/cohezion/triggers/runners/health.py",
      ["repo-hygiene"]
    );
    return JSON.parse(result.stdout);
  },
});

// ---------------------------------------------------------------------------
// Security Audit (daily at 4 AM UTC)
// ---------------------------------------------------------------------------

export const securityAuditTask = schedules.task({
  id: "health/security-audit",
  queue: healthQueue,
  cron: {
    pattern: "0 4 * * *",
    timezone: "UTC",
  },
  run: async (payload) => {
    const result = await python.runScript(
      "../src/cohezion/triggers/runners/health.py",
      ["security-audit"]
    );
    return JSON.parse(result.stdout);
  },
});

// ---------------------------------------------------------------------------
// Metrics Snapshot (every 30 minutes)
// ---------------------------------------------------------------------------

export const metricsSnapshotTask = schedules.task({
  id: "health/metrics-snapshot",
  queue: healthQueue,
  cron: {
    pattern: "*/30 * * * *",
    timezone: "UTC",
  },
  run: async (payload) => {
    const result = await python.runScript(
      "../src/cohezion/triggers/runners/health.py",
      ["metrics-snapshot"]
    );
    return JSON.parse(result.stdout);
  },
});

// ---------------------------------------------------------------------------
// Degradation Check (every 2 hours) - CRITICAL priority
// ---------------------------------------------------------------------------

export const degradationCheckTask = schedules.task({
  id: "health/degradation-check",
  queue: healthQueue,
  cron: {
    pattern: "0 */2 * * *",
    timezone: "UTC",
  },
  run: async (payload) => {
    const result = await python.runScript(
      "../src/cohezion/triggers/runners/health.py",
      ["degradation-check"]
    );
    const parsed = JSON.parse(result.stdout);

    // Alert on HIHO instability
    if (parsed.status === "warning" || parsed.status === "failure") {
      console.warn(
        `[ALERT] HIHO degradation detected: coherence=${parsed.metrics?.coherence}`
      );
    }

    return parsed;
  },
});

// ---------------------------------------------------------------------------
// Database Pruning (weekly on Sunday at 5 AM)
// ---------------------------------------------------------------------------

export const dbPruningTask = schedules.task({
  id: "health/db-pruning",
  queue: healthQueue,
  cron: {
    pattern: "0 5 * * 0",
    timezone: "UTC",
  },
  run: async (payload) => {
    const args = JSON.stringify({ retention_days: 7 });
    const result = await python.runScript(
      "../src/cohezion/triggers/runners/health.py",
      ["db-pruning", args]
    );
    return JSON.parse(result.stdout);
  },
});
