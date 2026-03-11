---
title: 'Anthropic Job Alignment — Benchmarks and Training'
date: '2026-02-19'
status: accepted
tags: [decision, benchmarks, training, alignment, research]
aspect: thinker
neural:
  activation: 0.477
  stage: growing
  cluster: decisions
---

# Anthropic Job Alignment — Benchmarks and Training

## Context

To demonstrate research engineering capabilities relevant to agentic environment development, the project needed a concrete portfolio of benchmark integrations and training infrastructure. The Cohezion platform's FLUME (Feedback Loop for Unsupervised Model Enhancement) architecture required quantitative evaluation to validate that agentic capabilities improve over training iterations.

Existing evaluation was qualitative (manual inspection of agent outputs). Without standardized benchmarks, there was no way to measure whether changes to the agent architecture, training pipeline, or prompting strategy actually improved performance. This gap also limited the ability to compare Cohezion's approach against published baselines.

## Decision

Build benchmark integrations and training support as a cohesive portfolio:

1. **SWE-bench integration** — evaluate code generation and bug-fixing capabilities using the standard SWE-bench dataset
2. **HumanEval integration** — measure pass@k on function-level code generation tasks
3. **AgentBench integration** — evaluate multi-step agentic task completion across diverse environments
4. **FLUME paper draft** — document the feedback loop architecture with benchmark results as evidence
5. **FSDP training support** — Fully Sharded Data Parallel training for efficient fine-tuning on multi-GPU setups

## Consequences

**Positive:**
- Quantitative evaluation enables data-driven decisions about architecture changes
- Benchmark scores provide a common language for comparing approaches
- FSDP support enables fine-tuning on consumer hardware (multi-GPU with memory sharding)
- Portfolio demonstrates research engineering breadth (benchmarks + training + paper writing)

**Negative:**
- Benchmark integration is maintenance-heavy — upstream datasets and evaluation harnesses change
- Baseline results from local models were discouraging (0% pass rate on HumanEval for non-code-tuned models) — though this was expected and motivates fine-tuning
- FSDP adds complexity to the training pipeline (distributed state management, gradient synchronization)

## Alternatives Considered

**Custom benchmarks only:** Design Cohezion-specific evaluation tasks. Rejected because custom benchmarks lack external credibility and comparability. Standard benchmarks (SWE-bench, HumanEval) have published baselines from major labs.

**Evaluation without training infrastructure:** Run benchmarks on pre-trained models only, without fine-tuning capability. Rejected because the value of benchmarks is measuring improvement over training iterations — static evaluation provides a snapshot but no trajectory.

**Cloud-only training (no FSDP):** Use single-GPU or cloud TPU for training. Rejected because FSDP enables local fine-tuning on available hardware without cloud costs, which is important for rapid iteration during pre-alpha.

## Related

- [[ai-safety-alignment]] — the formal alignment theory this benchmarks-and-training work targets
- [[alignment]] — Cohezion's alignment mechanisms (RequestAlignmentAnalyzer, adversarial review) that this work evaluates
- [[humanitys-last-exam-benchmark]] — expert-level benchmark relevant to the evaluation frameworks built here
- [[machine-learning-optimization]] — FSDP is a distributed training optimization that enables efficient fine-tuning
- [[experience-feedback-loop]] — FLUME is the concrete implementation of the experience feedback loop, with benchmarks providing the measurement layer
- [[2026-02-19-benchmark-infrastructure-complete-baseline-runs]] — the baseline runs produced by this infrastructure
- [[2026-02-19-benchmark-improvement-system-complete]] — the improvement system that automates benchmark-driven iteration
