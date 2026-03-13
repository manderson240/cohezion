---
title: 'TongGeometry: Neuro-Symbolic Olympiad Geometry via Guided Tree Search'
date: 2026-02-07
tags: [ai-mathematics, neuro-symbolic, theorem-proving, olympiad, tree-search]
connectivity: 0.07
cross_domain: 0.62
completion: 0.67
temporal: 1.0
recency: 1.0
connectivity_summary: ☆☆☆☆☆ (1/5 links)
completion_summary: 2/3 sections (66%)
conceptual_depth: 0.5
conceptual_label: Balanced
similar_papers:
- tonggeometry-ai-math
- theorem-ai-formal-verification
- humanitys-last-exam-benchmark
- testing-agent-skills-with-evals
dim_conceptual_depth: 0.5
source: https://www.nature.com/articles/s42256-025-01164-x
dimensions:
  connectivity: 0.05
  cross_domain: 0
  completion: 100
  temporal: 0.5
  recency: 0.7
  conceptual_depth: 0.0
  algorithm_complexity: 1
  implementation_difficulty: 1
  interdisciplinary_transfer: 0.5
  impact_score: 0.082
aspect: knower
neural:
  activation: 0.76
  stage: growing
  synapse_in: 2
  synapse_out: 11
---
# TongGeometry: Olympiad Geometry with Guided Tree Search

## Summary

Published in Nature Machine Intelligence, TongGeometry is a neuro-symbolic system that both discovers and proves olympiad-level geometry theorems using guided tree search, establishing a repository of 6.7 billion geometry theorems.

## Key Findings

- 6.7 billion theorems requiring auxiliary constructions, including 4.1 billion with geometric symmetry
- Three discoveries selected for regional mathematical olympiads (China national qualifying exam, top US civil olympiad)
- Combines neural network guidance with symbolic tree search
- Operates within same computational budget as existing state-of-the-art systems but produces far more results

## Relevance to Cohezion

Neuro-symbolic approach combining neural guidance with structured search directly relevant to `lab_agent.py` reasoning architecture. Tree search with neural pruning is a powerful pattern for agent problem-solving., [[agentic-ai]]

## Related Concepts

- [[machine-learning]] — neuro-symbolic AI combining neural networks and symbolic search
- [[neural-network-architecture]] — neural guidance architecture for tree search pruning
- [[meta-learning]] — learning to search effectively across proof spaces
- [[tonggeometry-ai-math]] — companion paper covering TongGeometry's results and competitive standing; this paper provides the deep technical architecture
- [[theorem-ai-formal-verification]] — both use structured proof decomposition: TongGeometry applies guided tree search to geometry proofs, Theorem uses fractional proof decomposition for code verification
- [[humanitys-last-exam-benchmark]] — HLE's expert-level math questions represent the broader evaluation context in which neuro-symbolic approaches like TongGeometry are assessed
- [[testing-agent-skills-with-evals]] — the eval methodology for agent skills (outcome, process, style goals) applies to evaluating mathematical problem-solving agents like TongGeometry

## Cross-Domain Bridges

- [[yann-lecun-agi-world-models]] — TongGeometry's neuro-symbolic architecture is the closest existing realization of LeCun's world-model vision: neural networks provide learned geometric intuitions, while symbolic tree search provides causal chain verification. The hybrid overcomes pure pattern-matching by grounding search in verifiable symbolic steps.
- [[comb-jellies-animal-tree-of-life]] — the tree-of-life phylogenetics problem and the geometry theorem tree are both enormous search spaces (billions of possible topologies / 6.7 billion theorems) where the core algorithmic challenge is which branch to explore next — neural-guided tree pruning is the shared solution, whether the domain is evolutionary biology or formal geometry.
- [[pairwise-comparison-fiber-bundles]] — fiber bundle decomposition (a topological tool for analyzing comparison matrices) and TongGeometry's guided tree search are both approaches to navigating high-dimensional mathematical spaces by imposing geometric structure on the search problem. Topology and tree search meet in the challenge of finding consistent solutions in complex constraint spaces.
