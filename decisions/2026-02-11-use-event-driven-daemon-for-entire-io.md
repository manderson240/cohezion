---
title: Use Event-Driven Daemon for Entire-IO API
date: 2026-02-11
status: accepted
tags: [decision, architecture, io, daemon]
---

# Use Event-Driven Daemon for Entire-IO API

## Context

The Entire-IO API requires persistent connection management and low-latency event processing. A polling approach creates unnecessary latency and resource usage.

## Decision

Implement an event-driven daemon pattern for the Entire-IO sync layer instead of polling or request-response.

## Consequences

- Lower latency for IO events
- Persistent daemon process required
- More complex lifecycle management
- Better resource utilization at scale

## Related

- [[entire-io-sync-daemon-design]]
- [[event-driven-daemon-pattern]]
