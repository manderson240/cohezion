---
title: "spec-verify token efficiency analysis"
date: "2026-02-17"
status: in-progress
tags: [experiment]
aspect: thinker
neural:
  activation: 0.85
  stage: mature
  synapse_in: 8
  synapse_out: 14
---

## Hypothesis

The `/spec` workflow's verification phase (spec-verify) consumes a disproportionate share of total session tokens compared to planning and implementation phases. By analyzing token distribution across plan, implement, and verify stages, we can identify specific verification sub-steps where tokens are wasted on redundant revalidation rather than novel quality insights, and reduce overall verification cost by 30-50% without sacrificing defect detection rates.

This hypothesis is motivated by observations from [AgentTaxo (ICLR 2025)](https://openreview.net/pdf?id=0iLbiYYIpC), which found that multi-agent verification systems often consume a substantial fraction of tokens on redundant re-checking. The [AgentAssay framework](https://arxiv.org/abs/2603.02601) demonstrated that trace-first offline analysis can eliminate live agent executions for four of six test types, achieving 78-100% cost reduction while maintaining statistical guarantees.

## Method

1. **Instrument the spec workflow**: Capture [[token-efficiency|token counts]] at each phase boundary -- plan approval, implementation start/end, and each verification sub-step (compliance review, quality review, test execution, execution verification).
2. **Collect baseline data**: Run 5+ complete spec workflows on tasks of varying complexity (small: 2-3 files, medium: 5-8 files, large: 10+ files) and record token consumption per phase.
3. **Analyze distribution**: Calculate the percentage of total tokens consumed by each phase and sub-step. Identify which verification steps contribute the most tokens with the least unique defect detection.
4. **Compare against alternatives**: Evaluate whether trace-based verification (analyzing recorded tool outputs rather than re-executing) can replace live verification for specific sub-steps, following the AgentAssay model.
5. **Measure defect detection**: Track defects found per verification token spent to establish a cost-per-defect baseline.

Key metrics:
- Tokens per phase (plan / implement / verify)
- Defects found per 1000 verification tokens
- Redundant revalidation rate (tokens spent re-checking already-verified properties)
- [[context-management|Context utilization]] at verification entry vs exit

## Results

*Experiment in progress. Preliminary observations from 3 completed spec workflows:*

- Verification consistently consumes 25-40% of total session tokens across all task sizes
- The dual-agent verification pattern (compliance + quality reviewers running in parallel) produces overlapping findings in approximately 30% of cases
- Test execution verification is the most token-efficient sub-step (high defect-per-token ratio)
- Code review verification has the lowest defect-per-token ratio but catches architectural issues that tests miss
- Context pressure at verification entry (typically 60-75%) limits the depth of review possible

## Learnings

- **Verification is not monolithic**: Different verification sub-steps have dramatically different cost-effectiveness profiles. Treating verification as a single phase obscures optimization opportunities.
- **Trace-first analysis is promising**: For compliance checks (does the code match the plan?), analyzing file diffs against plan tasks offline could replace a live review agent, aligning with the [AgentAssay approach](https://arxiv.org/abs/2603.02601) of zero-cost trace analysis.
- **Overlap between reviewers is both a cost and a feature**: While 30% overlap sounds wasteful, the overlapping findings increase confidence. The question is whether the confidence gain justifies the token cost -- this requires more data.
- **Context budget is the binding constraint**: Even if verification could be more thorough, [[context-management|context limits]] at 80-90% usage force premature handoffs. Token efficiency in earlier phases directly enables deeper verification.

## Related Concepts

- [[token-efficiency]] -- the core metric this experiment measures and optimizes
- [[token-efficiency-patterns]] -- patterns that emerged from this analysis for reducing verification cost
- [[compound-engineering]] -- efficient verification is a compound asset; cheaper verification means more iterations per session
- [[adversarial-review]] -- the dual-reviewer pattern analyzed in this experiment
- [[concept-testing]] -- verification as a form of concept testing applied to implementation
- [[context-management]] -- context budget constraints that shape verification depth
- [[2026-02-11-entire-io-api-investigation]]
- [[2026-02-12-graphrag-implementation-session-56]]
- [[2026-02-11-graphrag-proof-of-concept-success]]
- [[2026-02-11-phase1-production-validation-results]]
- [[2026-02-12-session-56-compact-retrospective]]
- [[2026-02-14-session-58-7-phase-journey-enrichment-3-agent-adversarial-review]]
- [[2026-02-19-journal-vacuum-during-crash-loop-recovery]]
- [[2026-02-11-large-repositories-26gb-with-virtual-environment-files-wi]]

## Primary Sources

- [AgentAssay: Token-Efficient Regression Testing for Non-Deterministic AI Agent Workflows](https://arxiv.org/abs/2603.02601) -- 78-100% cost reduction via trace-first analysis
- [AgentTaxo: Systematic Token Usage Analysis for Multi-Agent Systems (ICLR 2025)](https://openreview.net/pdf?id=0iLbiYYIpC) -- communication tax quantification framework
- [Anthropic: Demystifying Evals for AI Agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents) -- baseline metrics for agent evaluation including token usage tracking
- [Optimizing Token Usage for AI Efficiency in 2025](https://sparkco.ai/blog/optimizing-token-usage-for-ai-efficiency-in-2025) -- strategies for token optimization in agentic systems
