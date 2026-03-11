---
title: Humanity's Last Exam - Expert-Level AI Benchmark
date: 2026-02-07
tags: [ai-benchmarking, expert-evaluation, multi-domain, nature-publication, frontier-models]
connectivity: 0.07
cross_domain: 0.5
completion: 0.67
temporal: 1.0
recency: 1.0
connectivity_summary: ☆☆☆☆☆ (1/5 links)
completion_summary: 2/3 sections (66%)
conceptual_depth: 0.5
conceptual_label: Balanced
similar_papers:
- testing-agent-skills-with-evals
- grok4-ai-benchmarks
- emoticons-llm-silent-failures
- tonggeometry-olympiad-tree-search
dim_conceptual_depth: 0.5
source: https://www.nature.com/articles/s41586-025-09962-4
dimensions:
  connectivity: 0.05
  cross_domain: 0
  completion: 100
  temporal: 0.5
  recency: 0.7
  conceptual_depth: 0.667
  algorithm_complexity: 0.0
  implementation_difficulty: 0.0
  interdisciplinary_transfer: 0.0
  impact_score: 0.082
aspect: knower
neural:
  activation: 0.578
  stage: growing
  cluster: papers
---
# Humanity's Last Exam (HLE) Benchmark

## Summary

Published in Nature, HLE is a multi-modal benchmark of 2,500 expert-level questions across dozens of subjects designed to push beyond current AI evaluation limits, where state-of-the-art LLMs achieve over 90% on existing benchmarks.

## Key Findings

- 2,500 questions across mathematics, humanities, and natural sciences
- Developed globally by subject-matter experts with known, unambiguous, verifiable solutions
- ~14% of questions require comprehending both text and image (multimodal)
- 24% multiple-choice, remainder exact-match
- State-of-the-art LLMs demonstrate low accuracy and poor calibration
- Highlights marked gap between current LLM capabilities and expert human frontier

## Relevance to Cohezion

Directly relevant to `lab_agent.py` for designing evaluation frameworks. HLE's approach to multi-domain expert-level testing could inform how Cohezion agents are benchmarked across diverse knowledge domains., [[ai-agents]]

## Related Concepts

- [[concept-testing]] — HLE as a testing methodology for AI capability boundaries
- [[concept-validation]] — verifiable answers with unambiguous solutions
- [[machine-learning]] — benchmarking frontier model capabilities
- [[agent-journey-tracking]] — tracking model performance trajectories across benchmark versions
- [[tonggeometry-ai-math]] — TongGeometry's IMO-level geometry problems directly overlap with HLE's expert mathematics domain
- [[tonggeometry-olympiad-tree-search]] — neuro-symbolic tree search is the kind of approach needed to tackle HLE-level mathematical reasoning
- [[theorem-ai-formal-verification]] — formal verification of AI-generated mathematical reasoning is relevant to HLE's unambiguous, verifiable answer requirements
- [[grok4-ai-benchmarks]] — Grok 4 benchmark results include HLE performance (24%), providing a direct reference point for state-of-the-art on this benchmark
- [[2026-02-09-model-wrangler-strategy]]
- [[runbook-benchmarking-validation]]
- [[2026-02-10-performance-benchmarking-framework]]
- [[2026-02-10-benchmarking-framework-complete]]
- [[2026-02-10-phase-4-execution-complete]]
- [[2026-02-19-anthropic-job-alignment-benchmarks-and-training|Anthropic Job Alignment: Benchmarks and Training]] — builds evaluation frameworks including SWE-bench and AgentBench that complement HLE's expert-level testing
- [[reinforcement-learning]] — HLE evaluates RL-trained reasoning models against expert-level tasks, revealing where RLHF-tuned models hit capability boundaries
