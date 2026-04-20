---
title: Compound Engineering Pattern
date: 2026-02-23
tags: [pattern, compound-engineering, methodology]
aspect: thinker
neural:
  activation: 0.87
  stage: mature
  synapse_in: 17
  synapse_out: 15
---

# Compound Engineering Pattern

The meta-pattern for how Cohezion compounds knowledge across agent sessions: execute, observe, extract, index, inject.

## Problem

Individual AI agent sessions are stateless: each session starts fresh, unaware of what previous sessions discovered, decided, or built. Without a mechanism to transfer knowledge between sessions, each session wastes tokens re-discovering context, re-making decisions, and re-learning lessons. This is the "Groundhog Day" problem of agentic AI — every day starts the same.

The waste compounds over time: a project with 100 sessions where each spends 20% of its token budget on re-discovery has effectively wasted 20 full sessions of work. The knowledge exists (in conversation transcripts, in code comments, in the developer's memory) but is not accessible to the next agent session.

## Solution

Implement a **five-phase compound cycle** that transfers knowledge between sessions through persistent, structured storage:

### The Cycle

1. **Execute** — Agent session performs work (coding, research, debugging, architecture)
2. **Observe** — During execution, observations are saved to persistent memory (key decisions, discoveries, errors encountered, solutions found)
3. **Extract** — At session end, a [[session-retrospective-notes]] pass creates structured vault notes (decisions, patterns, lessons) from the session's observations
4. **Index** — New vault notes are ingested into the knowledge graph ([[graphrag-knowledge-graph-with-surrealdb]]) and linked to existing nodes. The 3D graph visualization is updated.
5. **Inject** — The next session starts with context injection: relevant observations, decisions, and patterns from previous sessions are loaded based on the new session's task description

### Key Properties

- **Each cycle amplifies all previous cycles** — a decision made in Session 10 that is indexed and linked can be retrieved by Session 50, 100, or 1000
- **Quality over quantity** — one well-extracted pattern is worth more than 100 raw observations
- **The vault is the memory** — not conversation transcripts, not code comments, not human memory
- **Compound ROI** — investment in extraction today pays dividends in every future session

## Code Example

Typical compound cycle in a Cohezion session:

```python
# Phase 1-2: Execute + Observe (during session)
save_memory(
    text="SurrealDB RELATE requires both source and target to exist first. "
         "Creating edges before nodes causes silent failures.",
    title="SurrealDB edge creation ordering"
)

# Phase 3: Extract (session retrospective)
# Create: decisions/2026-02-13-surrealdb-edge-ordering.md
# Create: patterns/surrealdb-edge-creation-ordering.md

# Phase 4: Index (automated post-session)
# Vault notes ingested → SurrealDB graph nodes created
# Wiki-links → graph edges created
# Embeddings → semantic similarity edges

# Phase 5: Inject (next session start)
# Query: "working with SurrealDB edges"
# Returns: the decision + pattern from Phase 3
# → Next session avoids the silent failure entirely
```

## When to Use

- **Every non-trivial session** — if the session produced decisions, discoveries, or reusable approaches
- **After debugging sessions** — the root cause and fix are prime extraction targets
- **After architectural discussions** — decisions and their reasoning must be preserved
- **After failed experiments** — knowing what didn't work is as valuable as knowing what did
- **Skip for trivial sessions** — quick bug fixes, typo corrections, or single-file edits

## Related Patterns

- [[session-retrospective-notes]] — the extraction phase of the compound cycle
- [[experience-feedback-loop]] — the continuous improvement loop that compound engineering enables
- [[multi-session-compound-engineering-workflow]] — detailed operational workflow for multi-session compound execution
- [[implementation-first-infrastructure-later]] — implementation-first is the core validation principle within compound engineering
- [[token-efficiency-patterns]] — token efficiency patterns operationalize the cost awareness built into compound engineering
- [[staged-validation-long-horizon-tasks]] — phased validation across compound engineering sessions

## Related Decisions

- [[2026-02-10-canvas-driven-compound-engineering]] — unlocking Obsidian as a knowledge graph engine for compound engineering
- [[2026-02-10-compound-engineering-meta-learning]] — meta-learning applied to compound engineering cycles
- [[2026-02-10-token-efficient-compound-engineering-roadmap]] — token-efficient execution of compound engineering
- [[2026-02-10-phase-7-executor-pattern-launch]] — compound async executor pattern for automated execution
- [[2026-02-11-lessons-compound-engineering-phase-1-complete]] — lessons from the first complete compound cycle

## Related Concepts

- [[adversarial-review]] — adversarial review is a mandatory phase gate within the compound engineering pattern
- [[meta-learning]] — meta-learning is the retrospection phase that extracts reusable patterns from compound engineering sessions
- [[knowledge-graph-systems]] — the knowledge graph is the storage backbone for compound engineering
