---
title: Team Agent Efficiency: Coordination Overhead Exceeds Benefits Below Task Threshold
date: 2026-02-23
severity: CRITICAL
category: agent-workflow
tags: [team-agents, efficiency, coordination, multi-agent, token-efficiency]
status: validated
---

# Lesson: Team Agent Efficiency: Coordination Overhead Exceeds Benefits Below Task Threshold

## Context

Multi-agent team configurations incur significant coordination overhead: context passing, result aggregation, and inter-agent communication. For tasks below a complexity threshold, a single skilled agent outperforms a team.

## Core Learning

**Use team agents only when task parallelism and specialization benefits exceed coordination costs. Single agents are faster for most tasks under 4 hours.**

### Why This Matters
- Each agent handoff costs 2-5K tokens in context passing
- Aggregating results from 5 agents requires another agent pass
- Coordination failures cascade across the team
- This is the most frequently referenced lesson in the vault (25 refs)

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
- [[scaling-agent-systems]] - Google Research quantitative validation: capability saturation at 45% accuracy means single agents outperform teams on most tasks; tool-heavy tasks suffer disproportionate multi-agent overhead — the paper provides the empirical foundation for this lesson's thresholds

## Validation

**Discovered**: Feb 2026 across phases 1-3 retrospectives
**Impact**: Reduced wasted agent coordination cycles across the project
**Status**: CRITICAL -- most frequently referenced lesson in vault (25 refs)
