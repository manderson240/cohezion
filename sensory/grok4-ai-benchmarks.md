---
title: 'Artificial Analysis benchmarks: Grok 4 leading at 73 across reasoning and
  coding tasks'
date: 2026-02-07
tags: [ai-benchmarks, llm-evaluation, grok, reasoning, coding-performance]
connectivity: 0.07
cross_domain: 0.12
completion: 1.0
temporal: 1.0
recency: 1.0
connectivity_summary: ☆☆☆☆☆ (1/5 links)
completion_summary: 3/3 sections (100%)
conceptual_depth: 1.0
conceptual_label: Pure Theory
similar_papers:
- humanitys-last-exam-benchmark
- testing-agent-skills-with-evals
- tonggeometry-ai-math
- llm-training-methodology-changes
domain: AI Evaluation
source: 'Source: X'
dimensions:
  connectivity: 0.05
  cross_domain: 1
  completion: 100
  temporal: 0.5
  recency: 0.7
  conceptual_depth: 0.6
  algorithm_complexity: 0.0
  implementation_difficulty: 0.0
  interdisciplinary_transfer: 0.25
  impact_score: 0.082
aspect: knower
neural:
  activation: 0.538
  stage: growing
  cluster: papers
---
## Abstract

Grok 4 achieved the highest score on Artificial Analysis benchmarks with an Intelligence Index of 73, demonstrating leading performance in reasoning, coding, and math tasks. The model surpasses competitors including Claude Opus, Gemini 2.5, and OpenAI o3 on multiple challenging evaluations.

## Key Findings

- Grok 4 scores 73 on the Artificial Analysis Intelligence Index, surpassing OpenAI o3 (70), Google Gemini 2.5 (70), and Claude Opus
- Achieves all-time high scores on GPQA Diamond (88%, beating Gemini's 84%) and Humanity's Last Exam (24%, beating Gemini's 21%)
- Outperforms competitors on LiveCodeBench coding tasks and AIME 2024 competition mathematics
- Notable tradeoffs include slower inference speed (40 tokens/second) and verbose outputs (88M tokens vs. 11M average)

## Source

https://artificialanalysis.ai/models/grok-4

# Artificial Analysis benchmarks: Grok 4 leading at 73 across reasoning and coding tasks

## Summary

Artificial Analysis benchmarks: Grok 4 leading at 73 across reasoning and coding tasks.

## Key Findings

- Artificial Analysis benchmarks: Grok 4 leading at 73 across reasoning and coding tasks.

## Integration Point

lab_agent.py

## Relevance to Cohezion

AI Evaluation resource captured via mobile link pipeline. lab_agent.py, [[ai-agents]]

## Related Papers

- [[humanitys-last-exam-benchmark]] — HLE is one of the key benchmarks on which Grok 4 scores (24%), making these two directly complementary
- [[tonggeometry-ai-math]] — Grok 4's AIME math scores and TongGeometry's olympiad-level geometry achievements are comparable milestones in AI mathematical reasoning
- [[llm-training-methodology-changes]] — the training methodology shifts discussed there directly affect benchmark outcomes like Grok 4's scores
- [[transformers-v5-huggingface-release]] — the benchmark leaders like Grok 4 are trained using infrastructure that Transformers v5's pre-training scale support and modular architecture enable; benchmark progress tracks library infrastructure maturity
- [[nvidia-nemotron-3-nano-nemo-gym]] — NeMo Gym's standardized RL training environments are the kind of infrastructure that would train models to improve on the reasoning/coding benchmarks where Grok 4 leads

## Related Concepts

- [[machine-learning]] — frontier model training and evaluation
- [[concept-testing]] — benchmark design and evaluation methodology
- [[agent-journey-tracking]] — tracking model capability evolution over time
- [[machine-learning-optimization]] — training efficiency vs. benchmark performance trade-offs
- [[token-efficiency]] — Grok 4's 88M token verbosity vs. 11M average highlights token efficiency as a key cost trade-off
- [[transformer-architecture]] — frontier reasoning models build on transformer architecture foundations

## Cohezion Integration

Grok 4 benchmark results inform COHEZION's model selection strategy: for reasoning-heavy orchestration tasks, Grok 4's 73 Intelligence Index justifies the higher token cost, while for worker-bee execution tasks, faster/cheaper alternatives are preferred. This directly maps to COHEZION's CostAwareRouter logic: match model capability to task complexity.
