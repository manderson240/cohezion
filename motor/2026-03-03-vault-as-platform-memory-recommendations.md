---
title: "Vault as Platform Memory — Enhancement Recommendations"
date: 2026-03-03
status: proposed
tags: [project, vault-architecture, memory, platform, recommendations, knowledge-graph]
aspect: doer
neural:
  activation: 0.913
  stage: mature
  cluster: projects
---

# Vault as Platform Memory — Enhancement Recommendations — 2026-03-03
*Written by Claude after examining vault structure, graph topology, lesson corpus, and session patterns.*

---

## The Core Problem

The vault currently serves two jobs that are in tension:

1. **Coordination layer** — helping Claude Code pick up where it left off across [[agentic-ai|agent sessions]]
2. **Knowledge base** — storing what the platform has learned over time

These need different structures. Right now the vault is good at #1 and weak at #2. To serve as genuine platform memory, it needs to be restructured so that what the platform *knows* is as accessible as what it *did*.

The evidence: `vault_search` returns nothing for "FLUME," "EcoAgent," "platform architecture," or "[[compound-engineering]]." The platform's core intellectual content isn't in a form the vault can retrieve. That's the primary failure mode to fix.

---

## Recommendation 1 — Build a Platform Spine

**What**: A small set of canonical concept notes (~10-15) that define the platform's core identity. These are the notes that every new Claude Code [[agent-context|session should read at startup]].

**Why**: Currently there is no single place that describes what [[cohezion|COHEZION]] *is*, how [[FLUME-Architecture|FLUME]] works, what EcoAgent does, or what [[compound-engineering]] means operationally. These ideas exist in [[session-retrospective|session notes]] and commit messages, but they're not retrievable as first-class vault content.

**What to create**:

```
concepts/
  cohezion-platform-overview.md      <- What the platform is, why it exists
  flume-architecture.md              <- VAE design, 256D latent space, training status
  ecoagent-environment.md            <- Gymnasium env, observation/action spaces, reward structure
  compound-engineering-theory.md     <- The philosophy, formally stated
  multi-agent-orchestration.md       <- How parallel Claude Code sessions work
  experience-feedback-loop.md        <- The experience -> VAE training pipeline
  platform-current-state.md          <- Living doc: what's working, what's broken, open questions
```

Each of these should be a full note with: definition, current status, open questions, and links to related papers and lessons. Not stubs — actual content.

**How to maintain**: `platform-current-state.md` gets updated at the end of every session, similar to a continuation file but at the conceptual level rather than the task level.

---

## Recommendation 2 — Make the Lessons Corpus Machine-Readable

**What**: Add structured frontmatter to every lesson so they can be queried systematically at session startup.

**Why**: The 40-lesson corpus is the platform's most operationally valuable knowledge — hard-won, specific, and directly actionable. But right now a Claude Code session can't ask "what lessons are relevant to the task I'm about to do?" because there's no way to filter by category, severity, or applicability.

**What to add to each lesson's frontmatter**:
```yaml
---
severity: HIGH | MEDIUM | LOW
category: agent-workflow | testing | git | ci-cd | performance | security | data
applies_to: [executor, mcp, surrealdb, ollama, vault]  <- which platform components
cost_of_forgetting: 30min | 2hr | session-loss        <- what happens if ignored
---
```

**The payoff**: A session startup script can then do:
```
SELECT * FROM lessons WHERE severity = 'HIGH' AND applies_to CONTAINS 'executor'
```
...and inject only the relevant lessons into [[agent-context|context]], not all 40. This is how the lessons corpus becomes a precision [[semantic-search|memory system]] rather than a document dump.

---

## Recommendation 3 — Introduce Link Types

**What**: Differentiate between types of edges in the [[knowledge-graph-systems|knowledge graph]].

**Why**: The current graph has 1,458 links all with `strength: 1.0` and no type. This means a "this paper *proves* this concept" link is indistinguishable from a "this paper *mentions* this concept" link. The graph looks dense but the signal is diluted.

**Proposed link types**:
```
IMPLEMENTS    — code/pattern implements this concept
VALIDATES     — evidence supports this claim
CONTRADICTS   — challenges or limits this idea
EXTENDS       — builds on this concept
MENTIONS      — topically related but not deeply connected
INFORMS       — informed a design decision
```

**Practical approach**: Don't re-type all 1,458 existing links — that's a boil-the-ocean task. Instead, start typing new links going forward and retroactively type only the links connected to the Platform Spine concepts. The highest-value links are the ones touching [[FLUME-Architecture|FLUME]], EcoAgent, [[compound-engineering]], and the lesson corpus.

**The payoff**: [[graph-databases|Graph]] traversal becomes meaningful. "Show me everything that VALIDATES the [[experience-feedback-loop]] concept" becomes a real query.

---

## Recommendation 4 — Add a Session Memory Protocol

**What**: A standardised end-of-session write to the vault that future [[agentic-ai|agent sessions]] can reliably load.

**Why**: Lesson 37 (experience-guided execution) validates that [[context-management|context loading]] at session start eliminates 30-60 minutes of re-orientation. But the *source* of that context — the continuation file — lives outside the vault and isn't connected to the [[knowledge-graph-systems|knowledge graph]]. The vault doesn't know what happened last session.

**Structure**:
```
daily/
  YYYY-MM-DD-session-{id}.md         <- already exists (auto-generated)

Add to each [[session-retrospective|session note]]:
  ## Decisions Made
  - [[decision-node]] with rationale
  ## Lessons Activated
  - [[lesson-XX]] triggered by [event]
  ## Open Questions
  - unresolved issues for next session
  ## Platform State Delta
  - what changed in the platform (not just the code)
```

**The key addition**: "Lessons Activated" — which lessons from the corpus were *actually relevant* this session. This creates an [[experience-feedback-loop]] where the most-frequently-activated lessons become visible as the highest-priority ones to have loaded at startup. It also surfaces lessons that are *never* activated (possibly obsolete or incorrectly categorised).

---

## Recommendation 5 — Separate Intake from Knowledge

**What**: Create a clear structural boundary between the research intake stream and the platform knowledge base.

**Why**: Right now the 999-item research sheet and the 102 papers in [[surrealdb|SurrealDB]] are mixed with platform-specific [[concept-modularity|concept notes]]. A paper about JWST dark matter maps is in the same namespace as [[compound-engineering]] workflow notes. This creates noise when the platform tries to retrieve knowledge about itself.

**Proposed structure**:
```
knowledge/              <- Platform's knowledge about itself
  concepts/             <- Core platform concepts (the Spine lives here)
  lessons/              <- Operational lessons (already exists, keep it)
  decisions/            <- Architecture decisions (already exists)

research/               <- External intake (currently mixed in)
  papers/               <- arXiv and other papers
  concepts/             <- Concepts derived from external research
```

**The rule**: When the platform needs to know something about *itself*, it queries `knowledge/`. When it wants external context or inspiration, it queries `research/`. The session startup [[workflow-orchestration|protocol]] loads from `knowledge/` first, then optionally from `research/` if relevant.

---

## Recommendation 6 — A Platform Memory API

**What**: A thin abstraction over the vault that the platform calls at session start and end, rather than using raw [[cloud-vault-mcp|vault tools]] directly.

**Why**: Currently every session re-implements [[context-management|context loading]] ad hoc (read continuation file, query Pilot Memory, check recent decisions...). This means the [[workflow-orchestration|protocol]] drifts — some sessions do all five steps, some do two, depending on how the session started. The lesson corpus itself (Lesson 19, Lesson 37) documents this problem.

**What it looks like** — a simple MCP tool or Python function:

```python
def platform_memory_load(focus: str = None) -> PlatformContext:
    """
    Returns: current platform state, relevant lessons, recent decisions,
    open questions, and spine concept summaries.
    Optional focus filters lessons/concepts to a specific component.
    """

def platform_memory_save(session: SessionSummary) -> None:
    """
    Writes: decisions made, lessons activated, platform state delta,
    open questions. Called at session end.
    """
```

**The payoff**: Every session starts and ends the same way, regardless of which Claude Code instance is running. The vault genuinely becomes a shared memory across instances rather than each instance having its own ad hoc loading strategy. This connects directly to the [[Autonomous-Context-Hooks-Guide|autonomous context hooks]] pattern — the Platform Memory API is the standardised interface those hooks would call.

---

## Priority Order

These six recommendations range from "do this week" to "architectural investment":

| Priority | Recommendation | Effort | Payoff |
|---|---|---|---|
| 1 | Platform Spine (7 core concept notes) | 1-2 sessions | Immediate — vault becomes self-describing |
| 2 | Session Memory Protocol (structured end-of-session) | 1 session | Immediate — sessions compound more reliably |
| 3 | Lessons frontmatter (structured metadata) | 1 session | High — lessons become queryable |
| 4 | Intake/knowledge separation | 1 session | Medium — cleaner signal/noise |
| 5 | Link typing (new links only) | Ongoing | Medium — graph becomes navigable |
| 6 | Platform Memory API | 2-3 sessions | High once 1-3 are done |

The first two are the unlock. Once the vault can describe the platform and reliably load that description at session start, everything else builds on a solid foundation.

---

## What Success Looks Like

A new Claude Code session starts, runs the memory load, and within 5 minutes knows:
- What [[cohezion|COHEZION]] is and what it's trying to do
- The current state of [[FLUME-Architecture|FLUME]] and EcoAgent
- The 5 most relevant lessons for the day's planned work
- What was decided last session and why
- What questions remain open

That's platform memory. The vault can do this — it just needs the [[concept-modularity|structure]] to support it.

*-- Claude, March 3 2026*

## Related Assessments

- [[2026-03-04-vault-assessment-v3]] — third vault assessment identifying portfolio deadline as forcing function for memory architecture improvements

## Related Concepts

- [[cohezion]] — the platform this assessment targets
- [[FLUME-Architecture]] — VAE architecture referenced throughout
- [[compound-engineering]] — the core methodology the vault serves
- [[experience-feedback-loop]] — the learning cycle recommendations aim to strengthen
- [[multi-agent-systems]] — multi-agent orchestration patterns discussed in Rec 1
- [[knowledge-graph-systems]] — knowledge graph structure improvements in Recs 3 and 5
- [[context-management]] — context loading at session start, central to Recs 4 and 6
- [[token-efficiency]] — token/context efficiency gains from structured memory
- [[session-retrospective]] — session memory and note structure in Rec 4
- [[concept-modularity]] — note structure and separation in Rec 5
- [[semantic-search]] — vault search and retrieval improvements
- [[cloud-vault-mcp]] — MCP vault tools abstracted by Rec 6
- [[workflow-orchestration]] — session protocols and standardization
- [[agentic-ai]] — agent session patterns throughout
- [[agent-context]] — agent context loading improvements
- [[non-blocking-observability]] — monitoring and feedback patterns
- [[graph-databases]] — graph database traversal in Rec 3
- [[surrealdb]] — SurrealDB as knowledge graph backend
- [[Autonomous-Context-Hooks-Guide]] — autonomous hooks that Rec 6's API would standardise
- [[data-analysis]] — data querying patterns for lessons corpus
