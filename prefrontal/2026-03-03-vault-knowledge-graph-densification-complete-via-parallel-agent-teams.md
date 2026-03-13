---
title: 'Vault Knowledge Graph Densification Complete via Parallel Agent Teams'
date: '2026-03-03'
status: accepted
tags: [decision, vault, knowledge-graph, multi-agent, densification]
aspect: thinker
neural:
  activation: 0.8
  stage: mature
  synapse_in: 8
  synapse_out: 11
---

# Vault Knowledge Graph Densification Complete via Parallel Agent Teams

## Context

The Cohezion vault had grown to 900+ notes, but many notes had few or no outbound wiki-links. The knowledge graph was sparse: notes existed as isolated islands rather than a connected web. Sparse graphs degrade the value of every graph-dependent feature: [[semantic-search]] traversals find fewer paths, [[graphrag-knowledge-graph-with-surrealdb]] queries return incomplete neighborhoods, and the 3D visualization shows disconnected clusters.

Manual linking was infeasible at scale — reviewing 900+ notes and identifying meaningful connections would take days of human effort. The densification task was embarrassingly parallel: each note could be enriched independently, and the work could be divided by note type (concepts, papers, decisions, patterns).

## Decision

Execute vault knowledge graph densification using **parallel agent teams**, each with a focused mission and clear batch boundaries:

- **Team Alpha:** Concepts and core definitions (~80 notes)
- **Team Beta:** Research papers and references (~130 notes)
- **Team Gamma:** Decisions and ADRs (~120 notes)
- **Team Delta:** Patterns and lessons (~100 notes)

Each team operated within a single session, processing notes in batches of 10-20. Teams ran in parallel across separate terminal sessions, with no cross-team dependencies. Each agent added bidirectional `[[wiki-links]]` to semantically related notes, using the existing vault structure as context.

Two rounds of densification were executed:
- **Round 1:** ~305 new bidirectional links added
- **Round 2:** ~500 additional links, focusing on cross-domain connections (e.g., linking a physics paper to a pattern it inspired)

## Consequences

**Positive:**
- ~805 new bidirectional links added across the vault in two sessions
- Every future `vault_find_relevant_context` call, SurrealDB query, and agent context pull benefits from the denser graph
- Parallel execution maximized throughput — 4 agents working simultaneously completed in ~2 hours what would have taken ~8 hours sequentially
- No overlap or wasted work — batch boundaries prevented duplicate processing
- ROI compounds with every session that uses the knowledge graph

**Negative:**
- Some links added by agents may be low-quality (tangential connections) — requires periodic audit via [[vault-link-audit-pattern]]
- Parallel agents could not coordinate cross-team linking in real-time (addressed in Round 2 with cross-domain focus)
- Increased vault file sizes due to additional Related sections in each note

## Alternatives Considered

**Sequential single-agent processing:** One agent processes all 900+ notes. Rejected because it would take 4x longer (wall-clock time) and risk hitting context limits before completing.

**Automated link inference (embedding similarity):** Use embedding cosine similarity to automatically add links above a threshold. Rejected because similarity-based links lack semantic precision — two notes about "Python" might be similar by embedding but unrelated in practice (one about Python the language, one about Monty Python). Agent-curated links are higher quality.

**Human manual linking:** Review each note manually and add links. Rejected for infeasibility at 900+ note scale — would take days and is error-prone.

## Related

- [[vault-knowledge-graph-densification]] — the project this decision completes; contains full session progress and metrics
- [[knowledge-graph-systems]] — the knowledge graph infrastructure that densification improves
- [[multi-agent-systems]] — parallel agent teams (Alpha/Beta/Gamma/Delta) are a concrete multi-agent coordination pattern
- [[role-based-multi-agent-coordination]] — each team had a specialized role with clear batch boundaries
- [[compound-engineering]] — graph densification is a compound engineering task where each new link compounds the value of every future context retrieval
- [[semantic-search]] — denser wiki-link graphs improve the quality of semantic search results by providing more traversal paths
- [[experience-feedback-loop]] — densification feeds the experience loop by making prior decisions and patterns more discoverable in future sessions
- [[vault-link-audit-pattern]] — post-densification audit to verify link quality
- [[2026-02-24-vault-link-integrity-first-principle]] — the integrity standard that densification work must respect
