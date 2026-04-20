---
title: "Concept Modularity"
date: 2026-02-19
tags: [concept, compound-engineering, knowledge-graph-systems, meta-learning]
related_concepts: [compound-engineering, knowledge-graph-systems, agent-context, token-efficiency-patterns]
aspect: knower
neural:
  activation: 0.86
  stage: growing
  synapse_in: 17
  synapse_out: 10
---
## Definition

Concept modularity is the principle that knowledge nodes in a knowledge graph should be self-contained, independently reusable, and minimally coupled to each other. A modular concept note can be retrieved and injected into agent context without requiring the entire connected graph — it carries its own definition, key properties, and enough context to be useful in isolation. This property is what makes semantic retrieval effective: a retrieved note contributes value on its own, not just as part of a larger document.

In software systems, modularity reduces coupling and enables independent evolution. The same principle applied to knowledge nodes means: don't embed long procedural explanations in concept notes (extract them as patterns or lessons), don't make concept definitions depend on other concepts being present (make them self-contained), and keep concept notes focused on a single concept rather than combining multiple concerns.

For Cohezion's vault enrichment work, modularity is the guiding principle: each concept note should be enrichable independently, linkable to other concepts without requiring them, and retrievable as a standalone context unit. The `related_concepts` frontmatter field and `[[wiki-links]]` in body text create the graph edges without embedding one concept's content inside another.

## Key Properties

- **Self-contained**: Each concept note is independently useful without needing other notes present
- **Single responsibility**: One concept per note; split notes that cover multiple distinct concepts
- **Explicit linking**: Relationships expressed as wiki-links, not embedded content
- **Stable identity**: Concept filenames serve as stable identifiers for cross-linking
- **Independent enrichment**: Each note can be improved without modifying linked notes

## Related Papers

- [[lesson-04-surgery-lesson]]
- [[lesson-18-mock-live-services-in-tests]]
- [[lesson-21-runtime-json-pollution]]

## Related Concepts

- [[compound-engineering]] — the methodology that benefits from modular, reusable knowledge nodes
- [[knowledge-graph-systems]] — the graph that modular concepts form nodes in
- [[agent-context]] — what gets assembled from modular concept notes during context retrieval
- [[token-efficiency-patterns]] — modularity enables scoped context reads (fetch one concept, not the whole graph)

## Key Lesson Links

- [[lesson-08-import-graph]] — map the full import graph before refactoring any module; 50+ transitive dependents can break simultaneously
- [[lesson-04-surgery-lesson]] — make the smallest possible change that satisfies the requirement; resist all scope creep during implementation

## Skills

- EXTRACTED_BLOCK_D41D8CD9 — Autonomously extracted pattern for refactoring repeated code into helper functions

## Relevance to Cohezion

Modularity governs the quality of the Cohezion vault's concept notes. The vault enrichment process explicitly targets modular enrichment: each concept gets its own self-contained definition, its own `related_concepts` frontmatter, and its own wiki-link graph rather than embedding explanation of other concepts. This enables `vault_find_relevant_context` to retrieve individual concept notes that are immediately useful without requiring the entire linked graph — keeping context injection within [[token-efficiency]] bounds.
