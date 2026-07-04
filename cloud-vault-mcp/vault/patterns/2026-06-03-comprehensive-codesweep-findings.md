---
date: 2026-06-03
source_project: cohezion
tags: [pattern, dev]
---
# Comprehensive Codesweep Findings

## Problem
Ensuring strict adherence to code standards, async safety, type hints, and exception safety across 1,000+ files.

## Solution
An AST-based codesweep tool was run to automatically inspect code patterns.

## Details
- Scanned all 1,075 modules (278,278 LOC) with 100% test imports coverage.
- Found 15 blocking calls in async, 6 exception tuple collisions catching `Exception`, 15 leftover placeholders, and 1,585 wide exceptions.
- Highlights:
  - Sync `open()` inside async in `lab_agent.py:263`.
  - `time.sleep` and `requests.get` inside async in `fail_hook.py:8-9`.
  - Double catch tuple collisions catching `Exception` with custom subclasses in `executor_factory.py`.

## Related Decisions
- [[2026-06-03-ouroboros-mycelium-integration]]
