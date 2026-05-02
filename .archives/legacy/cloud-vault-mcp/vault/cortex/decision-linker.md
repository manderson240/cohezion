---
title: Decision Linker
date: 2026-02-23
tags: [tool, compound-engineering, agent-workflow, knowledge-graph]
status: active
aspect: knower
neural:
  activation: 0.86
  stage: growing
  synapse_in: 9
  synapse_out: 10
---

# Decision Linker

An agent tool within the Cohezion compound engineering framework that automatically discovers and creates semantic links between decision notes (ADRs). The linker analyzes decision content, identifies shared concepts, causal chains, and supersession relationships, then inserts bidirectional wiki-links to make the decision graph navigable and complete.

## How It Works

1. **Index** — Reads all notes in `decisions/` and extracts key entities: technologies mentioned, problem domains, status values, and tags
2. **Embed** — Generates semantic embeddings for each decision's context and consequences sections using the Ollama MCP server
3. **Match** — Computes pairwise similarity scores and applies a threshold to identify candidate link pairs
4. **Classify** — Categorizes each relationship as one of:
   - **Supersedes** — a newer decision replaces an older one (e.g., deprecated -> accepted)
   - **Extends** — a decision builds on the foundations of another
   - **Conflicts** — decisions that chose opposing approaches for similar problems
   - **Related** — shared domain or technology without direct dependency
5. **Link** — Inserts typed wiki-links in the Related section of both decisions, preserving existing links

## Key Properties

- **Typed edges:** Unlike generic wiki-links, the decision linker annotates each link with its relationship type, enabling downstream tools like the [[DecisionExplorer]] to render typed graph edges
- **Bidirectional:** Every link is inserted in both the source and target decision, maintaining the vault's bidirectional linking convention
- **Incremental:** Processes only new or modified decisions since the last run, using file modification timestamps
- **Non-destructive:** Never removes existing links; only adds new ones that pass the similarity threshold

## Sources

- Internal vault pattern inspired by Architecture Decision Record (ADR) linking practices
- [ADR GitHub Organization](https://adr.github.io/)
- Semantic similarity via Ollama embeddings (see [[ollama-context-management]])

## Related

- [[compound-engineering]] — the decision linker is a tool within the compound engineering agent framework
- [[cohezion]] — part of the Cohezion knowledge persistence system
- [[semantic-search]] — decision linking relies on semantic similarity to find related notes
- [[knowledge-graph-systems]] — the linker strengthens the knowledge graph by creating typed edges between decisions
- [[DecisionExplorer]] — the UI component that visualizes the relationships the linker creates
- [[inbox-triager]] — complementary agent tool; the triager routes notes while the linker connects them semantically
- [[DecisionHealthDashboard]] — monitors the health of decision links created by this tool
- [[bidirectional-linking]] — the linker enforces bidirectional connections between all linked decisions
- [[knowledge-graph-densification]] — decision linking is a primary driver of knowledge graph density

## Relevance to Cohezion

The decision linker ensures that the vault's architectural decision records form a connected, navigable graph rather than isolated documents. By automatically discovering and typing relationships between decisions, it enables the DecisionExplorer to render meaningful visualizations and supports the compound engineering principle that knowledge compounds through connections.
