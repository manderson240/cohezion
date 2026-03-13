---
title: 'Daily CLI Tool Update via Systemd Timer'
date: '2026-02-22'
status: accepted
tags: [decision, tooling, automation, systemd]
aspect: thinker
neural:
  activation: 0.7
  stage: growing
  synapse_in: 5
  synapse_out: 6
---

# Daily CLI Tool Update via Systemd Timer

## Context

CLI tools used by the Cohezion platform (e.g., `cz`, `claude`, `uv`, `gh`, `mcp-cli`) are updated frequently. Stale versions cause subtle compatibility issues: changed command-line flags, deprecated features, and missing capabilities that newer sessions expect. These issues manifest as cryptic errors during agent sessions, wasting tokens on debugging rather than productive work.

Manual `pip install --upgrade` or `npm update` cycles are easy to forget, especially across multiple tools. The project already uses a `cohezion-guardian.timer` systemd pattern for scheduled background tasks, so extending this pattern to CLI tool updates is low friction.

## Decision

Implement a **systemd timer** that runs daily to check for CLI tool updates and apply them. The timer pattern matches the existing `cohezion-guardian.timer` for consistency. A complementary Claude Code skill enables manual `/update-tools` invocation from any agent session when an update is needed immediately.

Key design choices:
- **Version comparison before update** — check current vs. latest version to avoid unnecessary reinstalls (the [[daily-cli-tool-update-with-version-comparison]] pattern)
- **Idempotent execution** — safe to run multiple times; if already up-to-date, exits cleanly
- **Logging to journald** — all update activity is visible via `journalctl -u cohezion-tool-update`
- **Non-blocking** — runs in background, never blocks agent sessions

## Consequences

**Positive:**
- CLI tools are always current — eliminates version-skew debugging
- Zero manual maintenance — fire-and-forget once the timer is installed
- Consistent with existing systemd patterns in the project
- Manual override available via `/update-tools` skill for urgent updates

**Negative:**
- Breaking changes in updated tools could disrupt workflows — mitigated by version pinning for critical tools
- Systemd dependency — only works on Linux hosts with systemd
- Network dependency — updates fail silently if the host is offline (acceptable; retries next day)

## Alternatives Considered

**Cron job:** Functionally equivalent but lacks systemd's restart-on-failure, logging integration, and timer randomization (to avoid thundering herd on shared infra). Rejected for inferior observability.

**Pre-session check in Claude Code hooks:** Would run before every session, adding startup latency. Version checks are fast (~1s each) but multiplied across 5+ tools and 10+ sessions/day, the overhead adds up. Rejected in favor of once-daily background execution.

**Manual updates only:** Relies on the user remembering to update. In practice, tools drift 2-4 weeks behind, and the user only discovers the issue when something breaks. Rejected for the debugging cost.

## Related

- [[daily-cli-tool-update-with-version-comparison]] — the reusable pattern this decision implements
- [[2026-02-22-cz-spec-workflow-retrospective]] — context from the same session where CLI tooling was evaluated
- [[workflow-orchestration]] — systemd timers are a lightweight orchestration mechanism for automated maintenance tasks
- [[tool-use]] — CLI tool updates ensure agents always have current tool versions available for execution
- [[non-blocking-observability]] — automated version checks run in the background without blocking agent workflows
- [[log-rotation-and-monitoring]] — complementary systemd timer pattern for scheduled maintenance tasks
