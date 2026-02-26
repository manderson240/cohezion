---
title: 'Emu3: Multimodal Learning via Next-Token Prediction'
date: 2026-02-07
tags: [emu3-multimodal-next-token-prediction, 2026-02-14-phases-1-3-retrospective-key-learnings, meta-learning, 2026-02-09-operational-principle-no-destructive-operations-without-learning, 2026-02-10-compound-engineering-meta-learning]
connectivity: 0.07
cross_domain: 0.5
completion: 0.67
temporal: 1.0
recency: 1.0
connectivity_summary: ☆☆☆☆☆ (1/5 links)
completion_summary: 2/3 sections (66%)
conceptual_depth: 1.0
conceptual_label: Pure Theory
similar_papers:
- fast-radio-bursts-binary-star-origin
- usaf-stealthy-electromagnetic-attack
- woh-g64-dust-obscured-companion
- diffraction-gratings-fourier-transforms
- cu45-superatom-co2-ethylene
dim_conceptual_depth: 1.0
source: https://www.nature.com/articles/s41586-025-10041-x
dimensions:
  connectivity: 0.05
  cross_domain: 0
  completion: 100
  temporal: 0.5
  recency: 0.7
  conceptual_depth: 0.5
  algorithm_complexity: 0.0
  implementation_difficulty: 0.333
  interdisciplinary_transfer: 0.0
  impact_score: 0.082
---
# Emu3: Multimodal Next-Token Prediction

## Summary

Published in Nature, Emu3 is a family of multimodal models trained solely with next-token prediction that matches the performance of specialized task-specific models across perception and generation, without requiring diffusion or compositional architectures.

## Key Findings

- Unified next-token prediction approach across text, images, and video
- Matches flagship systems for vision-language tasks without diffusion models
- Demonstrates coherent, high-fidelity video generation
- Supports interleaved vision-language generation
- Enables vision-language-action modeling for robotic manipulation
- Addresses fundamental challenge of learning from and generating across multiple modalities

## Relevance to Cohezion

Unified multimodal architecture directly relevant to `lab_agent.py` design. The next-token prediction paradigm as a universal learning objective across modalities could inform how Cohezion agents handle diverse input/output types., [[ai-agents]]

## Related Papers

- [[llm-training-methodology-changes]] — Emu3's unified next-token prediction approach is a concrete example of the "train smarter" paradigm: one training objective across all modalities instead of separate specialized architectures
- [[yann-lecun-agi-world-models]] — Emu3's video generation capability is exactly the kind of world-model grounding LeCun argues is necessary for human-level AI; learning from video prediction is AMI Labs' stated approach
- [[transformers-v5-huggingface-release]] — Transformers v5's modular architecture is designed to accommodate unified multi-modal models like Emu3; the library's pre-training support enables the scale at which Emu3-class models are trained
- [[time-series-foundation-models-2026]] — Emu3's next-token prediction paradigm applied to temporal video sequences is architecturally equivalent to time series foundation models; both treat temporal data as token streams for unified prediction

## Related Concepts

- [[operational-data-ai-agents]]
- [[superfluid-to-supersolid-transition]]
- [[2026-02-10-claude-log-mining-architecture]]
- [[2026-02-10-compound-engineering-meta-learning]]
- [[2026-02-10-framework-driven-prioritization]]
- [[prompt-optimization-hypotheses]]
- [[2026-02-10-redesigned-pilot-complete]]
- [[2026-02-10-meta-pattern-extraction]]
