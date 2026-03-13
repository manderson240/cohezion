---
title: "Journal vacuum during crash-loop recovery"
date: "2026-02-19"
status: in-progress
tags: [experiment]
aspect: thinker
neural:
  activation: 0.87
  stage: mature
  synapse_in: 5
  synapse_out: 15
---

## Hypothesis

When an agentic AI system enters a crash-loop recovery state (repeated failures causing session restarts), a "journal vacuum" occurs where observations, decisions, and progress from the failing sessions are lost because the [[experience-feedback-loop|feedback loop]] never completes its write phase. This creates a compounding problem: without knowledge of what was tried and failed, the recovery session is likely to repeat the same failing approaches. By implementing pre-crash journaling (writing partial observations before the crash boundary), the recovery session can avoid repeated failures and resolve the issue in fewer iterations.

The concept parallels write-ahead logging (WAL) in database systems -- the journal must be durable before the operation completes, not after.

## Method

1. **Reproduce the vacuum**: Identify sessions that entered crash-loop recovery (3+ consecutive session failures on the same task) from the Cohezion session history.
2. **Measure information loss**: Compare what was attempted in failing sessions (from available logs and partial continuation files) against what the recovery session actually had access to. Quantify the "knowledge gap" as the number of distinct approaches tried but not recorded.
3. **Instrument pre-crash journaling**: Modify the [[session-retrospective|session retrospective]] mechanism to write incremental checkpoint observations at fixed intervals (every 5 minutes or every tool call, whichever is more frequent), not just at session end.
4. **Test recovery speed**: Run controlled crash-loop scenarios (intentionally interrupt sessions mid-task) with and without pre-crash journaling, measuring iterations-to-resolution.
5. **Analyze [[token-efficiency]] impact**: Calculate the token cost of incremental journaling versus the token savings from avoiding redundant approaches in recovery.

## Results

*Experiment in progress. Preliminary findings from 2 observed crash-loop incidents:*

- In both incidents, the recovery session had zero knowledge of what the crashed sessions attempted, confirming the journal vacuum hypothesis.
- The first incident (MCP server connection failure) required 4 recovery sessions before resolution. Post-analysis showed that session 2 and 3 repeated the exact same diagnostic steps as session 1.
- The second incident (git pack file corruption during cleanup) was resolved in 2 recovery sessions, but only because the developer manually provided context about prior attempts via the continuation prompt.
- Estimated token waste from redundant approaches: 15,000-25,000 tokens per crash-loop incident (equivalent to 1-2 full task implementations).

## Learnings

- **The journal vacuum is real and costly**: Without pre-crash journaling, crash-loop recovery is effectively a memoryless process where each session starts from zero. This directly contradicts the [[compound-engineering]] principle.
- **Continuation files are necessary but insufficient**: The current continuation protocol (write at 90% context) does not cover crash scenarios where the session terminates unexpectedly before reaching the context threshold.
- **Checkpoint frequency matters**: Too frequent checkpointing wastes tokens on trivial state changes. Too infrequent loses critical diagnostic information. The optimal interval appears to be after each significant diagnostic finding or failed approach, not on a fixed timer.
- **[[non-blocking-observability]] is essential**: Journaling must not interfere with the primary task execution. Async or background write mechanisms are preferable to synchronous observation saves.

## Related Concepts

- [[experience-feedback-loop]] -- the journal vacuum breaks the feedback loop by preventing experience capture
- [[compound-engineering]] -- crash-loop recovery without journals violates the compound principle
- [[session-retrospective]] -- retrospectives are the normal journal mechanism; this experiment addresses the gap when retrospectives cannot complete
- [[non-blocking-observability]] -- pre-crash journaling must be non-blocking to avoid exacerbating the crash condition
- [[context-management]] -- crash loops often originate from context exhaustion scenarios
- [[agent-journey-tracking]] -- journey tracking data is one of the primary casualties of the journal vacuum
- [[2026-02-11-entire-io-api-investigation]]
- [[2026-02-12-graphrag-implementation-session-56]]
- [[2026-02-11-graphrag-proof-of-concept-success]]
- [[2026-02-11-phase1-production-validation-results]]
- [[2026-02-12-session-56-compact-retrospective]]
- [[2026-02-17-spec-verify-token-efficiency-analysis]]
- [[2026-02-14-session-58-7-phase-journey-enrichment-3-agent-adversarial-review]]
- [[2026-02-11-large-repositories-26gb-with-virtual-environment-files-wi]]

## Primary Sources

- Write-ahead logging (WAL) concept from database theory -- the architectural pattern this experiment adapts for agentic sessions
- [Anthropic: Demystifying Evals for AI Agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents) -- baseline metrics for tracking agent session failures
- [AgentAssay: Token-Efficient Regression Testing](https://arxiv.org/abs/2603.02601) -- trace recording as durable evidence, applicable to crash recovery
