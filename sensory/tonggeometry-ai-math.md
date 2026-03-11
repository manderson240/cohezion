---
title: "TongGeometry: Chinese AI System for IMO-Level Geometry"
date: 2026-02-07
tags: [ai-mathematics, neuro-symbolic, geometry, olympiad, formal-reasoning, tree-search]
connectivity: 0.13
cross_domain: 0.5
completion: 0.67
temporal: 1.0
recency: 1.0
connectivity_summary: "★☆☆☆☆ (2/5 links)"
completion_summary: 2/3 sections (66%)
conceptual_depth: 0.0
conceptual_label: Pure Applied
similar_papers:
- tonggeometry-olympiad-tree-search
- theorem-ai-formal-verification
- humanitys-last-exam-benchmark
- grok4-ai-benchmarks
dim_conceptual_depth: 0.0
source: https://www.scmp.com/news/china/science/article/3341517/chinese-ai-goes-next-level-geometry-top-us-maths-olympiad
dimensions:
  connectivity: 0.1
  cross_domain: 0
  completion: 100
  temporal: 0.5
  recency: 0.7
  conceptual_depth: 0.0
  algorithm_complexity: 0.0
  implementation_difficulty: 0.0
  interdisciplinary_transfer: 0.0
  impact_score: 0.158
aspect: knower
neural:
  activation: 0.571
  stage: growing
  cluster: papers
---

# TongGeometry: AI System for IMO-Level Geometry

A neuro-symbolic AI system developed by the Beijing Institute for General Artificial Intelligence (BIGAI) and Peking University that both solves and generates olympiad-level geometry problems through principled tree search. Published in *Nature Machine Intelligence*, TongGeometry outperforms Google DeepMind's AlphaGeometry on standard benchmarks while using a fraction of the computational resources.

## Summary

TongGeometry represents a paradigm shift from "passive solver" AI (e.g., AlphaGeometry) to a system that can both solve existing problems and propose novel ones meeting the aesthetic and logical standards of expert mathematicians. As described by researchers, it is not merely an "honor student" capable of scoring full marks, but also a "master teacher" capable of creating elegant and novel mathematical problems. This "small data, big task" paradigm simulates the intuition and aesthetics of human mathematicians.

## Key Findings

### Benchmark Performance
- Solved all 30 problems in the IMO-AG-30 benchmark, outperforming average IMO gold medalists on this dataset
- Completed the benchmark within 38 minutes using consumer-grade hardware
- Hardware requirement: 32 CPU cores + single NVIDIA RTX 4090 GPU (vs. AlphaGeometry's 246 CPU cores + 4 NVIDIA V100 GPUs)

### Problem Generation
- Establishes a repository of 6.7 billion geometry theorems requiring auxiliary constructions, including 4.1 billion exhibiting geometric symmetry
- Uses normalized representation technology to compress the search space by several orders of magnitude, solving the path explosion problem inherent in traditional methods

### Real-World Validation
Three of TongGeometry's generated problems were selected for actual mathematical competitions:
- One problem selected as the sole geometry problem for the 2024 Beijing National High School Mathematics League
- Two problems shortlisted for the 2024 US Ersatz Math Olympiad
- AlphaGeometry solved only 3 of TongGeometry's 10 proposals

## Technical Architecture

TongGeometry employs a guided tree search approach combining neural network guidance with formal symbolic reasoning:

1. **Normalized representation**: Compresses the geometry problem search space, eliminating redundant configurations and symmetric duplicates
2. **Neural guidance**: Learned heuristics direct the tree search toward promising branches, mimicking mathematical intuition
3. **Symbolic verification**: Formal proofs validate discovered theorems, ensuring correctness
4. **Aesthetic filtering**: Generated problems are evaluated for elegance and competition suitability — not just solvability

This neuro-symbolic architecture contrasts with AlphaGeometry's approach, which relies heavily on large-scale synthetic datasets and costly computational resources as a "passive solver."

## Comparison with AlphaGeometry

| Aspect | TongGeometry | AlphaGeometry |
|--------|-------------|---------------|
| **Capability** | Solves AND generates problems | Solves problems only |
| **IMO-AG-30** | All 30 solved | Partial (fewer solved) |
| **Hardware** | 32 CPUs + 1 RTX 4090 | 246 CPUs + 4 V100s |
| **Paradigm** | Small data, big task | Large data, specialized task |
| **Competition use** | 3 problems in real olympiads | None |
| **Theorem repository** | 6.7B theorems | Not applicable |

## Implications

- **Efficiency over scale**: TongGeometry demonstrates that clever algorithmic design (normalized representation, guided search) can outperform brute-force compute — a counterpoint to the "scaling is all you need" narrative
- **Problem generation as capability**: The ability to generate competition-quality problems is a stronger test of mathematical understanding than solving alone
- **Neuro-symbolic vindication**: The system validates the neuro-symbolic approach where neural intuition guides formal reasoning, rather than replacing it
- **Educational applications**: AI systems that generate calibrated difficulty problems could transform mathematics education and competition preparation

## Primary Sources

- [Chinese AI goes next level in geometry at a top US maths Olympiad](https://www.scmp.com/news/china/science/article/3341517/chinese-ai-goes-next-level-geometry-top-us-maths-olympiad) — South China Morning Post
- [AI system TongGeometry generates and solves olympiad-level geometry problems](https://phys.org/news/2026-02-ai-tonggeometry-generates-olympiad-geometry.html) — Phys.org
- [Proposing and solving olympiad geometry with guided tree search](https://www.nature.com/articles/s42256-025-01164-x) — Nature Machine Intelligence
- [TongGeometry AI Breakthrough](https://www.aibusinessreview.org/2026/01/29/tonggeometry-ai-breakthrough/) — AI Business Review
- [Chinese researchers score breakthrough in general AI logical reasoning](https://english.news.cn/20260127/26a2c05ece9f493fbcb90525ce0201f0/c.html) — Xinhua

## Relevance to Cohezion

Relevant to [[enhanced-simulator]] for neuro-symbolic reasoning approaches. The guided tree search methodology could inform Cohezion's problem-solving architectures, particularly in agent planning where neural heuristics guide symbolic search over solution spaces.

## Related Papers

- [[tonggeometry-olympiad-tree-search]] — companion paper with full technical detail on the guided tree search architecture
- [[theorem-ai-formal-verification]] — both advance AI-powered formal mathematical reasoning; TongGeometry generates and proves geometry theorems, Theorem verifies code proofs
- [[humanitys-last-exam-benchmark]] — HLE benchmark includes mathematics at the olympiad level, where TongGeometry's problem-generation methodology is directly relevant
- [[grok4-ai-benchmarks]] — Grok 4 benchmark results on AIME math overlap with TongGeometry's olympiad-level scope

## Related Concepts

- [[machine-learning]] — neuro-symbolic AI combining neural guidance with formal search
- [[concept-testing]] — generating competition problems as a test of mathematical reasoning
- [[neural-network-architecture]] — neuro-symbolic architecture blending neural intuition with symbolic verification
- [[prompt-engineering]] — the guided search parallels prompt engineering: steering AI toward productive solution paths
