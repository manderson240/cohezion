---
title: "Concept"
date: 2026-02-19
tags: [concept]
aspect: knower
neural:
  activation: 1.0
  stage: mature
  synapse_in: 13
  synapse_out: 23
---
## Definition

A **concept** is the atomic unit of knowledge in the Cohezion vault. Each concept note captures a single, self-contained idea -- a definition, a pattern, a principle, or a domain term -- that can be retrieved independently, linked to other concepts, and injected into agent contexts. Concepts are designed to be composable: individually understandable, but more powerful when connected through [[wiki-links]] into a [[knowledge-graph-systems|knowledge graph]].

Unlike papers (which capture research findings) or decisions (which record choices), concept notes distill reusable knowledge that persists across projects and sessions. They form the backbone of the vault's semantic structure.

The concept note pattern draws directly from Niklas Luhmann's Zettelkasten method, where over 90,000 atomic index cards formed an interconnected knowledge system that Luhmann described as a "communication partner." Luhmann's key insight -- that constraining notes to atomic building blocks of thought enables emergent structures to arise organically -- is the foundational design principle behind the Cohezion vault's concept layer.

## Key Properties

- **Atomicity**: One concept per note. If you need "and" to describe it, split into two notes. This mirrors the Zettelkasten principle where each slip captures exactly one idea, ensuring clarity and reusability.
- **Self-containment**: The definition must be useful without requiring the reader to follow links first. A reader should understand the concept from the note alone, even if links provide deeper context.
- **Linkability**: Every concept should link to related concepts and be linked from papers, lessons, or decisions that reference it. Links are the primary organizational mechanism -- concepts gain meaning through their connections, not their folder placement.
- **Verifiability**: Concept definitions should be testable against primary sources via [[concept-testing]]. Claims should cite real literature or documented experiments.
- **Stability**: Concepts change infrequently compared to papers or daily notes; they represent settled knowledge.
- **Evergreen**: Concepts are designed for longevity. Unlike daily notes or session logs, a well-written concept note remains valid and useful across months or years of project evolution.

## Concept Lifecycle

1. **Capture**: A new idea enters the vault through `inbox/` or is created directly in `concepts/` with minimal content.
2. **Research**: The topic is researched using authoritative sources (papers, documentation, verified experiments).
3. **Expansion**: The note is fleshed out with definition, key properties, examples, and primary sources.
4. **Linking**: Outbound [[wiki-links]] connect the concept to related notes. Inbound links accumulate as other notes reference it.
5. **Validation**: [[concept-testing]] verifies accuracy against primary sources. [[concept-validation]] checks structural completeness.
6. **Densification**: Periodic [[knowledge-graph-densification]] sprints add missing cross-references, strengthening the graph.

## Examples

- [[particle-physics]] -- a scientific domain concept defining a field of study
- [[concept-testing]] -- a meta-concept about validating concept notes themselves
- [[token-efficiency]] -- a practical concept capturing a measurable optimization property
- [[transformer-architecture]] -- a technical concept capturing a specific ML architecture
- [[compound-engineering]] -- a methodological concept capturing a development practice

## Primary Sources

- Niklas Luhmann. *Communicating with Slip Boxes: An Empirical Account* (1981). Described the Zettelkasten as a communication partner that produces surprising connections through atomic, linked notes.
- Sonke Ahrens. *How to Take Smart Notes* (2017). Popularized Luhmann's method for modern knowledge workers, emphasizing atomic notes and emergent structure.
- Zettelkasten.de. *Introduction to the Zettelkasten Method*. [https://zettelkasten.de/introduction/](https://zettelkasten.de/introduction/)

## Related Papers

- [[2026-02-09-12d-graph-refined-plan]]
- [[2026-02-09-vault-completion-status]]
- [[2026-02-10-canvas-driven-compound-engineering]]
- [[2026-02-10-canvas-driven-compound-engineering-refined]]
- [[2026-02-10-compound-linking-plan-summary]]
- [[2026-02-10-compound-node-linking-plan]]
- [[2026-02-10-retrospective-refined-plan]]
- [[canvas-driven-manual-linking]]

## Related Concepts

- [[concept-testing]] -- validating that concept notes are accurate and complete
- [[concept-optimization]] -- improving concept notes for clarity and retrieval quality
- [[concept-automation]] -- automating the creation and maintenance of concept notes
- [[knowledge-graph-systems]] -- the graph structure that concepts form nodes within
- [[concept-modularity]] -- designing concepts to be composable and independently useful
- [[wiki-links]] -- the linking syntax that connects concepts into a navigable graph
- [[bidirectional-linking]] -- the practice of maintaining reciprocal links that make concept discovery bidirectional
- [[semantic-search]] -- the embedding-based search layer that surfaces concepts by meaning rather than keyword
- [[concept-isolation]] -- ensuring concepts are independently retrievable and testable

## Relevance to Cohezion

Concepts are the foundational knowledge layer of the Cohezion framework. When agents call `vault_find_relevant_context`, they retrieve concept notes to inform decisions. The quality of agent reasoning depends directly on the quality of concept definitions -- accurate, atomic, well-linked concepts produce better agent outputs than vague or bloated ones.

The dual-layer architecture of the vault -- human-navigable Obsidian graph plus machine-parsable SurrealDB import -- means concepts serve both human knowledge workers and AI agents simultaneously. Each concept note is both a readable document and a node in a queryable knowledge graph, making the vault a practical implementation of Luhmann's vision at scale with AI augmentation.
