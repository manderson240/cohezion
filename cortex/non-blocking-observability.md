---
title: Non-Blocking Observability
date: 2026-02-23
tags: [observability, patterns, async, agent-journey-tracking]
related_concepts: [agent-journey-tracking, workflow-orchestration, compound-engineering, agent-architecture]
status: active
aspect: knower
neural:
  activation: 0.89
  stage: mature
  synapse_in: 28
  synapse_out: 18
---

# Non-Blocking Observability

Non-blocking observability is the pattern of collecting telemetry, metrics, and execution traces without allowing instrumentation code to block, slow, or crash the primary execution path. It is the discipline of "observe without interfering" — the observer effect problem in distributed systems, solved by wrapping all tracking calls in try/except handlers and offloading I/O to background tasks.

In agentic AI systems, observability is especially critical because agent behavior is complex, emergent, and hard to reproduce. Without traces, debugging a 20-step agent workflow becomes guesswork. But naive observability — synchronous writes to external systems, blocking metric uploads, exception propagation from tracking code — can introduce latency and failure modes that alter the very behavior being observed. Non-blocking observability resolves this by treating tracking as best-effort: valuable when available, never at the cost of correctness.

In Cohezion, the `JourneyTracker` implements this pattern with explicit try/except wrappers around all state transition recordings. If SurrealDB is unavailable, the agent continues executing and logs fall back to JSONL format. Metrics are batched and flushed asynchronously. The `GlobalMetricsAggregator` uses in-memory accumulation with periodic background flushes, ensuring agent loop throughput is never gated on metrics I/O.

## Key Properties

- **Best-effort**: Tracking failures are logged as warnings, never raised as errors
- **Try/except wrapping**: All instrumentation code is wrapped to prevent propagation
- **Async/background flush**: Metrics accumulate in-memory and flush on a timer or at session end
- **Graceful degradation**: If the observability backend is unavailable, execution continues normally
- **Fallback persistence**: In-memory → JSONL → SurrealDB as availability allows

## Related
- [[agent-journey-tracking]] — the primary use case for non-blocking observability in Cohezion
- [[workflow-orchestration]] — the execution context being observed
- [[compound-engineering]] — the methodology that requires reliable journey data
- [[lesson-35-non-blocking-observability-pattern-new]] — the lesson that formalized this pattern
- [[error-handling-with-dlq]] — DLQ complements non-blocking observability by capturing failed operations for retry rather than discarding them
- [[Ouroboros-Loop]] -- the Ouroboros Loop implements non-blocking observation of system state during agent execution
- [[event-driven-daemon-pattern]] — daemons require non-blocking observability to track events without disrupting the event loop
- [[edge-computing]] — edge-deployed services require non-blocking observability to minimize latency impact on local processing
- [[lesson-28-non-critical-tracking-pattern]] — related lesson on non-critical tracking
- [[2026-02-24-overnight-simulation-55m-12d-trajectories|Overnight Simulation: 5.5M 12D Trajectories]] — overnight trajectory generation requires non-blocking observability to avoid impacting simulation throughput
- [[2026-02-11-use-event-driven-daemon-for-entire-io|Event-Driven Daemon for IO]] — event-driven patterns enable non-blocking observability of IO streams
- [[2026-02-11-session-55-compound-engineering-approach-for-universe-simulation-preservation|Session 55: Universe Simulation Preservation]] — simulation preservation requires non-blocking data capture
- [[2026-02-22-daily-cli-tool-update-via-systemd-timer|Daily CLI Update Timer]] — automated version checks run in the background without blocking agent workflows

## Related Patterns & Projects

- [[local-agent-orchestration-roadmap]] — ModelPoolManager lifecycle metrics and GlobalMetricsAggregator use non-blocking observability for model pool monitoring
- [[daily-cli-tool-update-with-version-comparison]] — version comparison logging provides observability into tool drift without blocking the update process

## Missions

- REPOSITORY_HEALTH_PRIME — Monitoring, alerting, and health metrics for repository size governance

## Session References

- [[SESSION-46-COMPLETE]] — non-blocking design patterns applied to Cost Dashboard and Forecast Engine

## Skills

- common_codebase_health — Codebase sustainability and monitoring
- observable_ai — AI observability and transparency
- REPO_HYGIENE_PRIME — Repository file entropy monitoring
- REPOSITORY_HEALTH_PRIME — Repository bloat prevention
- SYSTEM_MONITORING_PRIME — Real-time system performance monitoring
- USAGE_ANALYTICS_PRIME — Usage tracking and analytics

## Meta Recordings
- [[recording-self-20260304-072338-1|Self-Recording Session 1]] — Cohezion observing itself with non-blocking instrumentation
- [[recording-self-20260304-094201-1|Self-Recording Session 2]] — self-recording demonstrating observability of the observation process
