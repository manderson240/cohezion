---
title: Telemetry Corruption Fix: Isolate Observability Writes from Primary Data
date: 2026-02-23
severity: MEDIUM
category: debugging
tags: [lesson, telemetry, debugging, data-corruption]
status: validated
---

# Lesson: Telemetry Corruption Fix: Isolate Observability Writes from Primary Data

When telemetry and primary data share a write path, telemetry errors silently corrupt primary data. The fix is always to isolate observability writes completely.

## Core Learning

**Telemetry must never share a write path with primary data. Separate them at the architecture level.**

## Related
- [[lesson-21-runtime-json-pollution]]
- [[lesson-28-non-critical-tracking-pattern]]
