---
title: 'Benchmark Infrastructure Improvements and Learnings'
date: '2026-02-19'
status: accepted
tags: [decision, benchmarks, learnings, pass-at-k]
aspect: thinker
neural:
  activation: 0.466
  stage: growing
  cluster: decisions
---

# Benchmark Infrastructure Improvements and Learnings

## Context

After completing [[2026-02-19-benchmark-infrastructure-complete-baseline-runs]], several insights emerged from the first round of benchmark execution that required infrastructure changes. The initial implementation had three gaps:

1. **Single-sample evaluation** was unreliable — a model might solve a problem on attempt 3 but fail on attempt 1, making pass@1 an underestimate of capability
2. **No connection between benchmarks and the FLUME training loop** — benchmark results existed in isolation, not feeding back into the improvement pipeline
3. **Local model performance was uniformly poor (0-10%)** — suggesting that prompt formatting or context management (not just model capability) might be contributing factors

## Decision

Implement three key improvements to the benchmark infrastructure:

1. **pass@k evaluation** — generate k samples per problem (k=1,5,10) and report the probability that at least one sample passes. This dramatically improves result reliability and reveals cases where the model "knows" the answer but doesn't consistently produce it.

2. **Journey tracking integration** — connect benchmark execution to [[agent-journey-tracking]] so that each benchmark run creates a journey entry with 12D trajectory data. This enables the [[experience-feedback-loop]] to treat benchmark performance as a training signal.

3. **Prompt format investigation** — systematic evaluation of prompt templates (zero-shot, few-shot, chain-of-thought) to isolate whether poor performance is due to model capability or prompt engineering. Finding: few-shot prompting improved pass@5 from 0% to ~8% on local models — a meaningful signal that prompt engineering matters even for weak models.

## Consequences

**Positive:**
- pass@k reveals hidden capability — models that score 0% on pass@1 may score 5-15% on pass@5
- Journey tracking creates a permanent compound learning record for benchmark trajectories
- Prompt format investigation produced actionable findings (few-shot > zero-shot) applicable across all model interactions
- Infrastructure now supports the full improve-measure-learn cycle

**Negative:**
- pass@k requires k times more inference calls, increasing benchmark execution time proportionally
- Journey tracking adds write overhead to each benchmark run (SurrealDB inserts)
- Local models still struggle (0-10% even with improvements) — fine-tuning or code-specialized models are needed for meaningful pass rates

## Alternatives Considered

**Majority voting instead of pass@k:** Generate k samples and take the majority answer. Rejected because pass@k is the standard metric in code generation literature (Codex paper, HumanEval), enabling direct comparison with published results.

**Separate prompt optimization project:** Treat prompt engineering as a standalone effort rather than integrating with benchmarks. Rejected because prompts and benchmarks are tightly coupled — the benchmark is the evaluation mechanism for prompt changes.

## Related

- [[2026-02-19-benchmark-infrastructure-complete-baseline-runs]] — the baseline infrastructure these improvements build upon
- [[2026-02-19-benchmark-improvement-system-complete]] — the system that automates the improvement loop (BenchmarkOrchestrator, SelfCorrectionLoop)
- [[runbook-benchmarking-validation]] — benchmarking runbook for repeatable validation runs
- [[agent-journey-tracking]] — journey tracking integration for recording benchmark improvement trajectories
- [[prompt-engineering]] — the prompt format investigation findings feed into broader prompt engineering patterns
- [[experience-feedback-loop]] — benchmark results as training signals for the experience feedback loop
