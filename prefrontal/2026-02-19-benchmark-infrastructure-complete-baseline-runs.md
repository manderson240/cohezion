---
title: 'Benchmark Infrastructure Complete — Baseline Runs'
date: '2026-02-19'
status: accepted
tags: [decision, benchmarks, infrastructure, baseline]
aspect: thinker
neural:
  activation: 0.476
  stage: growing
  cluster: decisions
---

# Benchmark Infrastructure Complete — Baseline Runs

## Context

The Cohezion platform lacked quantitative evaluation capability. Agent improvements were assessed qualitatively ("it seems better") without measurable baselines. To establish a data-driven improvement loop, benchmark infrastructure was needed that could execute standardized evaluation suites, record results, and produce comparable metrics across model versions and configuration changes.

The initial target was running baseline evaluations on locally-hosted models via [[2026-02-09-ollama-context-management]] to establish a performance floor before any fine-tuning or prompt optimization.

## Decision

Build benchmark infrastructure capable of executing standardized evaluation suites and producing baseline measurements:

1. **Evaluation harness** — adapter layer that translates benchmark suite protocols (SWE-bench, HumanEval, AgentBench) into Cohezion API calls
2. **Result storage** — structured JSON output with per-problem pass/fail, error messages, and timing data
3. **Baseline runs** — execute all suites against `qwen2.5-coder` (local Ollama model) to establish the performance floor
4. **pass@k metric** — implement pass@k (k=1,5,10) to account for non-deterministic generation

Initial baseline results: `qwen2.5-coder` achieved 0% pass@1 on HumanEval — expected for a non-code-specialized model and motivating the fine-tuning work in [[2026-02-19-anthropic-job-alignment-benchmarks-and-training]].

## Consequences

**Positive:**
- Quantitative performance floor established — all future improvements can be measured against this baseline
- Infrastructure is model-agnostic — swap in any Ollama model or API-accessible model for comparison
- pass@k metric accounts for generation variance, producing more reliable results than single-sample evaluation
- Result storage enables longitudinal analysis of improvement trajectory

**Negative:**
- 0% baseline is discouraging but expected — validates that fine-tuning is necessary, not just prompt engineering
- Benchmark execution is compute-intensive — full HumanEval suite takes ~30 minutes on local hardware
- Infrastructure maintenance burden — upstream benchmark datasets and evaluation scripts change

## Alternatives Considered

**Cloud API baselines (GPT-4, Claude):** Run baselines against cloud models for comparison. Deferred rather than rejected — cloud baselines are valuable but expensive to run repeatedly. Local model baselines come first because they are free to re-run.

**Custom micro-benchmarks:** Design small, Cohezion-specific evaluation tasks. Rejected as the primary approach because custom benchmarks lack published baselines for comparison. Used as a supplement to standard suites.

**Skip baselines, go directly to fine-tuning:** Start training without measuring the starting point. Rejected because without a baseline, there is no way to measure the impact of fine-tuning — you cannot demonstrate improvement without a "before" measurement.

## Related

- [[2026-02-19-benchmark-improvement-system-complete]] — the improvement system built on top of this baseline infrastructure
- [[2026-02-19-benchmark-infrastructure-improvements-and-learnings]] — learnings from the same benchmark session (pass@k, journey tracking)
- [[runbook-benchmarking-validation]] — benchmarking runbook for repeatable validation runs
- [[2026-02-09-ollama-context-management]] — the Ollama integration layer that benchmark harness calls into
- [[machine-learning]] — benchmark infrastructure is a prerequisite for measured machine learning improvement
- [[2026-02-13-local-model-roster-update-february-2026-sota-assessment]] — model roster that informs which models to benchmark
