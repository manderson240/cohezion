---
title: Session Awareness Protocol: Agents Must Establish Context at Session Start
date: 2026-02-23
severity: HIGH
category: agent-workflow
cost_of_forgetting: "30-60 min wasted re-discovering context; contradictory decisions across sessions"
tags: [session-management, context, agent-workflow, continuity]
status: validated
aspect: knower
neural:
  activation: 0.78
  stage: growing
  synapse_in: 10
  synapse_out: 8
---

# Lesson: Session Awareness Protocol: Agents Must Establish Context at Session Start

## Context

Across multiple session boundaries in Cohezion's compound engineering workflow (February 2026), a recurring pattern emerged: new sessions that started without loading prior context would spend their first 30-60 minutes re-reading files, re-discovering project structure, and re-learning patterns that the previous session had already mastered. Worse, sessions without context loading sometimes made decisions that directly contradicted prior architectural choices, because the new session had no knowledge of those decisions.

## Problem

Without a formal startup protocol, each new agent session is effectively a blank slate:

1. **Context amnesia**: The agent has no knowledge of what the previous session accomplished, what decisions were made, or what problems were encountered
2. **Repeated work**: The agent re-reads the same files, re-explores the same directories, and re-discovers the same patterns
3. **Contradictory decisions**: Without knowledge of prior architectural choices (stored in `decisions/`), the new session may choose a different approach, creating inconsistency
4. **Plan status blindness**: The agent does not know whether a plan is PENDING, COMPLETE, or VERIFIED, leading to re-implementation of completed work or skipping of incomplete work

This was documented in multiple retrospective sessions and validated by [[lesson-37-experience-guided-execution-works-new]], which quantified the improvement when context loading was applied.

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

## Solution

The startup sequence was formalized and encoded in the `context-continuation.md` rules file. It is now a mandatory protocol for every session, enforced by convention:

1. **Continuation file**: Written at session end (or at 90% context), read at session start. Contains exact state, completed tasks, and next steps.
2. **Memory query**: Pilot Memory stores key observations that survive across sessions and can be queried semantically.
3. **Plan status check**: `cz plan status --json` shows whether work is in progress, and where it left off.
4. **Git log review**: Shows what was committed in the previous session(s), providing a code-level view of progress.
5. **TaskList check**: Reveals any pending tasks from the previous session that should be resumed.

The acknowledgment step ("Continuing from...") serves as a human-verifiable confirmation that context was loaded correctly.

## Prevention

- **Always write continuation files**: Do not wait for the 90% context warning; write state summaries proactively
- **Make startup sequence non-skippable**: Encode it in rules files so every agent session follows it automatically
- **Review the decision log**: Read the 5 most recent `decisions/` notes to understand current architectural direction
- **Trust the continuation file**: The previous session wrote it for exactly this purpose

## Cost of Forgetting

- **30-60 minutes wasted per session** on re-orientation
- **Contradictory architectural decisions** that create technical debt
- **Repeated debugging** of problems already solved
- **Broken compound chain**: Multi-session compound engineering fails without continuity

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
- [[agentic-ai-memory-hierarchies]] - The startup context-loading sequence is a software workaround for hardware KV caches that don't persist across session boundaries
- [[langchain-deep-agents-context-management]] - LangChain's three-tier strategy (offload, truncate, summarize) is the technical mechanism enabling the session continuity this protocol depends on
- [[agent-context]] - session awareness protocol is the practical implementation of agent context management
- [[context-management]] - explicit context-loading at session start is the core context management discipline
- [[lesson-37-experience-guided-execution-works-new]] - the empirical validation that this protocol delivers 30-60 min savings per session
- [[session-retrospective]] - retrospectives are the source material for continuation files

## Validation

**Discovered**: Feb 2026 across multiple session boundaries
**Impact**: 30-60 minute re-orientation eliminated through formalized startup protocol
**Status**: Validated -- now encoded in context-continuation.md rules
