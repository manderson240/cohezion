---
title: Team Agent Efficiency: Coordination Overhead Exceeds Benefits Below Task Threshold
date: 2026-02-23
severity: CRITICAL
category: agent-workflow
cost_of_forgetting: "Wasted tokens, slower delivery, cascade failures from unnecessary multi-agent coordination"
tags: [team-agents, efficiency, coordination, multi-agent, token-efficiency]
status: validated
aspect: knower
neural:
  activation: 0.84
  stage: mature
  synapse_in: 16
  synapse_out: 11
---

# Lesson: Team Agent Efficiency: Coordination Overhead Exceeds Benefits Below Task Threshold

## Context

During Cohezion phases 1-3, the platform experimented extensively with multi-agent team configurations for various development tasks. The hypothesis was that more agents working in parallel would accelerate delivery. In practice, the coordination overhead -- context passing between agents, result aggregation, error recovery across agent boundaries -- consistently exceeded the parallelism benefits for tasks below a complexity threshold. Retrospectives across multiple sessions quantified this: a single skilled agent completed tasks under 4 hours faster than a team of 3-5 agents attempting the same work.

## Problem

The core failure mode was threefold:

1. **Context passing tax**: Each agent handoff required serializing context (2-5K tokens per handoff). A team of 5 agents working on a 2-hour task could spend more tokens on coordination than on actual work.
2. **Aggregation overhead**: Combining results from multiple agents required a separate aggregation pass, adding latency and another failure point.
3. **Cascade failures**: When one agent in a team stalled or produced incorrect output, the error propagated through dependent agents, requiring expensive recovery cycles.

The result was that team configurations for simple tasks were 40-60% slower and 2-3x more expensive in token usage than a single agent approach.

## Core Learning

**Use team agents only when task parallelism and specialization benefits exceed coordination costs. Single agents are faster for most tasks under 4 hours.**

### Why This Matters
- Each agent handoff costs 2-5K tokens in context passing
- Aggregating results from 5 agents requires another agent pass
- Coordination failures cascade across the team
- This is the most frequently referenced lesson in the vault (35+ refs)

### Decision Framework
```
Task duration estimate:
  < 2 hours  -- Single agent (always)
  2-4 hours  -- Single agent with checkpoints
  4-8 hours  -- Team of 2-3 specialists
  8+ hours   -- Full team with orchestrator

Task parallelism:
  Sequential dependencies -- Single agent
  Independent subtasks    -- Team agents
  Shared state           -- Single agent (coordination cost too high)
```

## Solution

The resolution was a strict decision framework (above) applied at task planning time. Before spinning up a team, every task is evaluated against two axes: estimated duration and degree of parallelism. Tasks with sequential dependencies or shared state default to single-agent execution regardless of size.

For tasks that do qualify for team execution (genuinely parallel, independent subtasks over 4 hours), the following safeguards were added:
- Explicit timeout on every agent task to prevent cascade stalls
- Clear interface contracts between agents (structured JSON, not free-text)
- A dedicated orchestrator agent responsible only for coordination, not execution

## Prevention

- **Profile first**: Always benchmark single-agent completion time before adding agents to a task
- **Classify at planning time**: Use the decision framework during plan creation, not ad hoc
- **Measure coordination cost**: Track tokens spent on inter-agent context passing vs. actual work tokens
- **Review retrospectively**: After team tasks, compare actual overhead against the single-agent baseline

## Cost of Forgetting

Ignoring this lesson leads to:
- **2-3x token cost inflation** from unnecessary coordination overhead
- **40-60% slower delivery** for tasks that don't benefit from parallelism
- **Cascade failure risk** when one agent's error propagates across the team
- **Developer frustration** from debugging multi-agent interaction failures instead of solving the actual problem

## Recommendations

### Do
- Profile single-agent completion time before adding agents
- Use teams only for genuinely parallel subtasks with clear boundaries
- Set timeouts on all agent tasks to prevent cascade stalls

### Don't
- Add agents to speed up tasks that are fundamentally sequential
- Assume more agents = more throughput
- Use teams for tasks under 2 hours estimated duration

## Related Concepts

- [[compound-engineering]] - Team efficiency is a prerequisite for compound scalability
- [[agentic-ai]] - Agent coordination patterns and anti-patterns
- [[token-efficiency]] - Coordination overhead directly impacts token costs
- [[agent-architecture]] - informs when to use single vs. multi-agent architectural designs
- [[multi-agent-systems]] - CRITICAL calibration: coordination overhead exceeds benefits below task complexity threshold
- [[ai-agents]] - empirical finding that single agents outperform teams for tasks under ~2 hours
- [[agent-context]] - inter-agent context passing costs 2-5K tokens per handoff
- [[scaling-agent-systems]] - Google Research quantitative validation: capability saturation at 45% accuracy means single agents outperform teams on most tasks; tool-heavy tasks suffer disproportionate multi-agent overhead -- the paper provides the empirical foundation for this lesson's thresholds
- [[workflow-orchestration]] - orchestrator agents are justified only for 8+ hour multi-agent tasks
- [[agent-loop-architecture]] - agent loops must account for coordination overhead in their iteration budgets
- [[session-retrospective]] - this lesson emerged from systematic retrospective analysis across phases 1-3

## Validation

**Discovered**: Feb 2026 across phases 1-3 retrospectives
**Impact**: Reduced wasted agent coordination cycles across the project
**Status**: CRITICAL -- most frequently referenced lesson in vault (35+ refs)
