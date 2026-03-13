---
title: Experience-Guided Execution Works: Past Session Context Materially Improves Current Session Quality
date: 2026-02-23
severity: HIGH
category: agent-workflow
cost_of_forgetting: "30-60 minutes wasted on re-discovery every session; repeated mistakes from lost context"
tags: [session-continuity, memory, experience, agent-workflow, compound-engineering]
status: validated
aspect: knower
neural:
  activation: 0.82
  stage: mature
  synapse_in: 17
  synapse_out: 11
---

# Lesson: Experience-Guided Execution Works: Past Session Context Materially Improves Current Session Quality

## Context

During Cohezion compound engineering sessions in February 2026, a clear pattern emerged: sessions that began with injected context from prior sessions consistently outperformed cold-start sessions on the same codebase. Cold-start sessions would spend 30-60 minutes re-discovering project structure, re-reading decisions, and re-learning patterns that the previous session had already mastered. The compounding effect was dramatic -- experienced sessions made fewer mistakes, chose better approaches on the first attempt, and avoided known pitfalls documented in prior sessions.

## Problem

Without experience loading, each new agent session is effectively a fresh hire who has never seen the codebase:

1. **Re-discovery waste**: The agent spends 30-60 minutes reading files, exploring structure, and building a mental model that the previous session already had.
2. **Repeated mistakes**: Known pitfalls (documented in lessons, decisions, experiments) are re-encountered and re-debugged.
3. **Contradictory decisions**: Without knowledge of prior architectural choices, the new session may make decisions that conflict with established patterns.
4. **Lost momentum**: Compound engineering depends on accumulating knowledge across sessions. Cold starts break the compound chain entirely.

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

## Solution

The Cohezion continuation protocol now makes experience loading mandatory at session start:

1. **Continuation files** are written at session end (or at 90% context) with exact state: what was done, what is in progress, what comes next.
2. **Pilot Memory** stores key observations that survive across sessions and can be queried semantically.
3. **Plan files** track task status (PENDING/COMPLETE/VERIFIED) so the new session knows exactly where to resume.
4. **Session awareness protocol** (see [[lesson-19-session-awareness-protocol]]) formalizes the startup sequence.

The result: sessions that follow this protocol achieve productive work within 5 minutes instead of 30-60 minutes.

## Prevention

- **Automate context injection**: Use hooks or startup scripts that load continuation files automatically
- **Write continuation files proactively**: Do not wait for the 90% context warning; write state summaries after completing major tasks
- **Save discoveries immediately**: When you learn something non-obvious, save it to Pilot Memory in that same turn -- do not defer
- **Review the decision log**: Read the 5 most recent decisions/ notes to understand the current architectural direction

## Cost of Forgetting

- **30-60 minutes wasted per session** on re-orientation that context loading eliminates
- **Repeated debugging** of problems already solved in prior sessions
- **Architectural drift** from contradictory decisions across sessions
- **Broken compound chain**: The entire value of multi-session compound engineering evaporates without continuity

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
- [[agentic-ai-memory-hierarchies]] - The KV cache hierarchy paper explains the hardware challenge that makes software-side session memory injection (loading prior context) so important for long-running agent workflows
- [[langchain-deep-agents-context-management]] - LangChain's three-tier context management (offload, truncate, summarize) is the technical mechanism that enables experience-guided execution across long sessions
- [[agent-architecture]] - architecture must support context injection for experience-guided execution
- [[ai-agents]] - agents with prior context materially outperform cold-start agents
- [[experience-feedback-loop]] - this lesson empirically validates the experience feedback loop concept
- [[context-management]] - context injection at session start is the mechanism of experience-guided execution
- [[lesson-19-session-awareness-protocol]] - the concrete startup sequence that implements experience-guided execution
- [[session-retrospective]] - retrospectives produce the observations that fuel experience-guided execution in subsequent sessions
- [[agent-journey-tracking]] - tracking agent journeys across sessions provides the longitudinal data that validates this lesson

## Validation

**Discovered**: Feb 2026 across multiple compound engineering sessions
**Impact**: 30-60 minute re-orientation eliminated through context loading
**Status**: Validated -- referenced 21+ times (high-impact lesson)
