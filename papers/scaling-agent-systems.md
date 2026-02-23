---
title: Towards a Science of Scaling Agent Systems
date: 2026-02-07
tags: [scaling-agent-systems, surrealdb-agent-context-quick-reference, surrealdb-agent-context-visual-guide, surrealdb-agent-context-phase1-step3-query-testing, agentic-ai-memory-hierarchies]
connectivity: 0.27
cross_domain: 0.5
completion: 0.67
temporal: 1.0
recency: 1.0
connectivity_summary: ★☆☆☆☆ (4/5 links)
completion_summary: 2/3 sections (66%)
conceptual_depth: 0.0
conceptual_label: Pure Applied
similar_papers:
- helimagnetism-ferromagnetism-mode-locking
- jwst-red-nova-remnants
- llm-training-methodology-changes
- mom-z14-farthest-galaxy
- dna-origami-2d-semiconductor-patterning
dim_conceptual_depth: 0.0
source: https://arxiv.org/abs/2512.08296
dimensions:
  connectivity: 0.2
  cross_domain: 0
  completion: 100
  temporal: 0.5
  recency: 0.7
  conceptual_depth: 0.333
  algorithm_complexity: 1
  implementation_difficulty: 0.5
  interdisciplinary_transfer: 0.8
  impact_score: 0.322
---
# Towards a Science of Scaling Agent Systems

Google Research paper deriving quantitative scaling principles for agent systems.

## Summary

Evaluated five canonical agent architectures (Single-Agent, Independent, Centralized, Decentralized, Hybrid) across three LLM families in 180 configurations to determine when and why multi-agent systems outperform single agents.

## Key Findings

- **Tool-Coordination Trade-off**: Under fixed compute budgets, tool-heavy tasks suffer disproportionately from multi-agent overhead
- **Capability Saturation**: Coordination yields diminishing or negative returns once single-agent baselines exceed ~45% accuracy
- **Error Amplification**: Independent multi-agent systems amplify errors by 17.2x; centralized systems contain amplification to 4.4x via an orchestrator "validation bottleneck"
- **Task-Dependent Performance**: Centralized coordination improves parallelizable tasks (e.g. financial reasoning) by 80.9%; decentralized excels on dynamic web navigation; all multi-agent variants degrade sequential reasoning by 39-70%
- **Predictive Framework**: Uses measurable task properties (tool count, decomposability) to predict optimal architecture, correct for 87% of unseen task configurations

## Relevance to Cohezion

Directly applicable to [[lab-agent]] multi-agent orchestration design. The error amplification findings and capability saturation threshold inform when to use multi-agent vs single-agent approaches. The predictive framework could guide automatic architecture selection., [[multi-agent-systems]], [[agentic-ai]], [[agent-architecture]]

## Related Concepts

- [[langchain-deep-agents-context-management]]
- [[openai-codex-agent-loop]]
- [[llamaagents-builder]]
- [[testing-agent-skills-with-evals]]
- [[llm-in-sandbox-agentic-intelligence]]
- [[agentic-ai-memory-hierarchies]]
