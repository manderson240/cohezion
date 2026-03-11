---
title: Use Event-Driven Daemon for Entire-IO API
date: 2026-02-11
status: accepted
tags: [decision, architecture, io, daemon]
aspect: thinker
neural:
  activation: 0.509
  stage: growing
  cluster: decisions
---

# Use Event-Driven Daemon for Entire-IO API

## Context

The Entire-IO API requires persistent connection management and low-latency event processing. The initial integration approach used periodic polling to check for new IO events (file changes, sync updates, external triggers). This introduced unnecessary latency (polling interval delay before events were processed) and wasted resources on empty poll cycles. As the number of IO sources grew, polling overhead scaled linearly while most cycles returned no new data.

The Cohezion platform needs to react to IO events within seconds, not minutes. Agent sessions depend on timely context injection, and the [[experience-feedback-loop]] requires near-real-time observation capture to be effective. A synchronous request-response pattern would block the caller, making it unsuitable for multi-source IO aggregation.

## Decision

Implement an event-driven daemon pattern for the Entire-IO sync layer instead of polling or request-response. The daemon runs as a persistent background process using Python's `asyncio` event loop, listening for IO events via callbacks and pushing updates to consumers through an async queue.

Key design choices:
- **asyncio-based event loop** for non-blocking IO multiplexing across sources
- **Graceful shutdown** via signal handlers (`SIGTERM`, `SIGINT`) to ensure in-flight events complete
- **Systemd service unit** for process lifecycle management (restart-on-failure, logging to journald)
- **Health check endpoint** for monitoring daemon liveness

## Consequences

**Positive:**
- Sub-second latency for IO events (no polling delay)
- Efficient resource utilization — the daemon sleeps when idle, wakes on events
- Natural fit for [[multi-agent-systems]] where multiple agents consume IO streams concurrently
- Composable with [[non-blocking-observability]] — events flow through observable pipelines without blocking producers

**Negative:**
- Persistent daemon process required — adds operational complexity (must be monitored, restarted on failure)
- More complex lifecycle management than a simple cron job or polling script
- Event ordering guarantees require careful queue design
- Debugging is harder than synchronous request-response (distributed tracing needed)

## Alternatives Considered

**Polling with cron job:** Simple to implement but introduces unacceptable latency (minimum 1-minute granularity with cron). Rejected because agent sessions need sub-second responsiveness.

**Request-response API (synchronous):** Each consumer calls the Entire-IO API on demand. Rejected because it blocks the caller and doesn't support multi-source aggregation efficiently.

**Message broker (Redis Pub/Sub, RabbitMQ):** Adds external infrastructure dependency. Rejected for pre-alpha phase — the daemon provides equivalent functionality with fewer moving parts. Could revisit post-alpha if horizontal scaling is needed.

## Related

- [[entire-io-sync-daemon-design]] — detailed design document for the daemon architecture
- [[entire-io-sync-daemon-operations]] — operational runbook for managing the daemon in production
- [[compound-async-executor-pattern]] — the async executor pattern used within the daemon for task dispatch
- [[workflow-orchestration]] — event-driven daemons underpin the orchestration layer for persistent IO processing
- [[agent-architecture]] — daemon-based IO handling is an architectural choice for low-latency agent communication
- [[non-blocking-observability]] — event-driven patterns enable non-blocking observability of IO streams
- [[2026-02-13-track-b-entire-sync-daemon-complete]] — completion record for the daemon implementation
