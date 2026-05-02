---
title: Research Lineage
date: 2026-02-23
tags: [concept, knowledge-graph, compound-engineering, provenance]
status: active
aspect: knower
neural:
  activation: 0.89
  stage: growing
  synapse_in: 11
  synapse_out: 12
---

# Research Lineage

The traceable chain of research influence — how papers, experiments, and decisions build on each other over time. Research lineage tracks the provenance of knowledge: which paper cited which result, which experiment validated which hypothesis, and which decision was informed by which evidence. In the Cohezion vault, research lineage is encoded as typed edges in the knowledge graph, enabling compound knowledge accumulation.

## Definition

Research lineage is the directed acyclic graph (DAG) of intellectual dependencies between knowledge artifacts. Each edge represents a specific relationship: **cites** (paper references another), **implements** (code realizes a paper's method), **derives-from** (concept extracted from experimental result), **validates** (experiment confirms or refutes a hypothesis), or **supersedes** (newer work replaces older).

## Key Properties

- **Directed:** Lineage flows from foundational work to derivative work, creating a temporal ordering that reflects the actual sequence of discovery
- **Typed edges:** Different relationship types carry different semantics — a "cites" edge is weaker evidence than a "validates" edge
- **Transitive:** If paper C derives from paper B which derives from paper A, then C has indirect lineage to A, enabling multi-hop provenance queries
- **Incrementally constructed:** Each new paper, experiment, or decision added to the vault extends the lineage graph; lineage is never rewritten, only appended

## Examples

- The [[neutrinos-large-scale-structure-desi]] paper cites DESI survey data, which in turn derives from the DESI instrument calibration experiments — forming a three-hop lineage chain
- The [[graphrag-knowledge-graph-with-surrealdb]] concept implements ideas from the [[knowledge-graph-systems]] concept, which itself was informed by [[graph-databases]] foundational work
- The [[2026-02-14-phase-4-retrospective-and-phase-5-overnight-plan]] decision derives from experimental results in Phases 1-3, captured in [[2026-02-14-phases-1-3-retrospective-key-learnings]]

## Sources

- Provenance tracking concepts from the [W3C PROV Data Model](https://www.w3.org/TR/prov-dm/)
- Citation graph analysis from academic bibliometrics research

## Related

- [[compound-engineering]] — research lineage is the mechanism by which compound engineering achieves knowledge accumulation over time
- [[experience-feedback-loop]] — the feedback loop generates new lineage edges as agent experiences inform future decisions
- [[knowledge-graph-systems]] — the knowledge graph encodes research lineage as typed edges between nodes
- [[agent-journey-tracking]] — agent journey data forms part of the lineage chain, connecting execution traces to produced knowledge
- [[meta-learning]] — meta-learning extracts reusable patterns from the lineage, turning historical chains into predictive guidance
- [[knowledge-graph-densification]] — lineage tracking is a form of knowledge graph densification, adding provenance edges
- [[bidirectional-linking]] — each lineage relationship is recorded as a bidirectional wiki-link in the vault

## Relevance to Cohezion

Research lineage is the backbone of Cohezion's compound knowledge strategy. By explicitly tracking how each piece of knowledge builds on prior work, the vault enables agents to answer provenance questions ("why was this decision made?"), discover influence chains ("what depends on this paper?"), and identify knowledge gaps ("which foundational papers lack downstream validation?"). This transforms the vault from a flat document store into a temporal knowledge graph with traceable intellectual history.
