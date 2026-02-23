---
title: Experience-Guided Execution Works: Past Session Context Materially Improves Current Session Quality
date: 2026-02-23
severity: HIGH
category: agent-workflow
tags: [session-continuity, memory, experience, agent-workflow, compound-engineering]
status: validated
---

# Lesson: Experience-Guided Execution Works: Past Session Context Materially Improves Current Session Quality

## Context

Sessions that start with injected context from prior sessions consistently outperform cold-start sessions on the same codebase. The experience of prior sessions guides execution quality.

## Core Learning

**Always inject prior session context before starting new work. 5 minutes of context loading saves hours of re-discovery.**

### What Experience Loading Means
```
1. Read continuation file from previous session
2. Query Pilot Memory for recent observations
3. Read recent decisions/ notes (last 5-10)
4. Check current project status in projects/ notes
5. Review active experiments/ notes

This 5-minute sequence replaces 30-60 minutes of re-orientation.
```

## Recommendations

### Do
- Load prior session context before every new session
- Write detailed continuation files at session end
- Save key decisions and discoveries to Pilot Memory immediately

### Don't
- Start new sessions without context loading (cold sessions are expensive)
- Rely on memory of the previous session (unreliable across sessions)

## Related Concepts

- [[compound-engineering]] - Experience-guided execution is the engine of compound knowledge growth
- [[agentic-ai]] - Memory and continuity as first-class agent properties

## Validation

**Discovered**: Feb 2026 across multiple compound engineering sessions
**Impact**: 30-60 minute re-orientation eliminated through context loading
**Status**: Validated -- referenced 11 times (high-impact lesson)
