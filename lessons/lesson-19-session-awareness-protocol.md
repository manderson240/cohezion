---
title: Session Awareness Protocol: Agents Must Establish Context at Session Start
date: 2026-02-23
severity: HIGH
category: agent-workflow
tags: [session-management, context, agent-workflow, continuity]
status: validated
---

# Lesson: Session Awareness Protocol: Agents Must Establish Context at Session Start

## Context

Agentic sessions start fresh -- they don't inherit context from previous sessions automatically. Without explicit session startup protocols, agents repeat work, miss prior decisions, and contradict earlier conclusions.

## Core Learning

**Every agent session MUST begin with an explicit context-loading step: read continuation files, query memory, check plan status.**

### Startup Sequence
```
1. Read continuation file (if exists)
2. Query Pilot Memory for recent observations
3. Check active plan status (PENDING/COMPLETE/VERIFIED)
4. Review recent git log (last 10 commits)
5. TaskList -- check for pending tasks from previous session
6. Acknowledge continuity to user: "Continuing from..."
```

## Recommendations

### Do
- Always execute the full startup sequence at session begin
- Write a detailed continuation file before any session end

### Don't
- Skip startup sequence because "you remember the context" (new session has no memory)
- Start implementing before verifying plan status

## Related Concepts

- [[compound-engineering]] - Session continuity enables compound work across time
- [[agentic-ai]] - Memory and continuity as first-class agent properties
- [[agentic-ai-memory-hierarchies]] - The startup context-loading sequence is a software workaround for hardware KV caches that don't persist across session boundaries; loading prior context at startup replaces what hardware cannot retain
- [[langchain-deep-agents-context-management]] - LangChain's three-tier strategy (offload, truncate, summarize) is the technical mechanism enabling the session continuity this protocol depends on
- [[agent-context]] - session awareness protocol is the practical implementation of agent context management
- [[context-management]] - explicit context-loading at session start is the core context management discipline

## Validation

**Discovered**: Feb 2026 across multiple session boundaries
**Status**: Validated -- now encoded in context-continuation.md rules
