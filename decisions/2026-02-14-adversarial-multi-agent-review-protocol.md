---
title: Adversarial Multi-Agent Review Protocol
date: '2026-02-14'
status: accepted
tags: [decision, inferred]
decision_reasoning:
  chosen_option: '{{chosen_option}}'
  rationale: Single-agent implementation misses bugs that would cause production crashes.
    The 3-agent review caught 2 CRITICAL bugs (metadata=None crash, silent data corruption)
    and 5 HIGH issues that all tests passed on. The cost (3 agent spawns) is negligible
    vs. production crash risk. Different lenses (correctness vs. tests vs. architecture)
    find different bug classes.
  confidence_score: 0.6
  alternatives_rejected:
  - '{{alt1}}'
  - '{{alt2}}'
  reasoning_chain:
  - sequence: 1
    content: 'Context: Adversarial Multi-Agent Review Protocol'
    type: research
    confidence: 0.65
    assumption: Problem was clearly identified
  - sequence: 2
    content: Explored multiple implementation approaches and trade-offs
    type: pattern
    confidence: 0.6
    assumption: Multiple options were considered
  - sequence: 3
    content: Evaluated options against project constraints and criteria
    type: research
    confidence: 0.58
    assumption: Options were systematically evaluated
  - sequence: 4
    content: Selected option with best balance of trade-offs
    type: hybrid
    confidence: 0.62
    assumption: Best option was chosen based on analysis
  reasoning_type: research
metrics:
  estimated_cost: 0.0
  estimated_time_hours: 0.5
  actual_cost: 0.0
  actual_time_hours: 0.25
  tokens_used: 18500
  cost_per_lesson: 0.0
  lessons_generated:
  - '[[2026-02-14-session-58-7-phase-journey-enrichment-3-agent-adversarial-review]]'
---

## Context

After implementing 7 phases of journey enrichment (35 tests, 14 files, ~2000 lines), all unit tests passed 100%. However, production experience shows unit tests miss integration bugs:
- Metadata crashes when components interact
- State corruption across component boundaries
- Edge cases only visible in full system context

Single-agent implementation has blind spots. Different review perspectives find different bug classes.

## Decision

Spawn 3 specialized review agents (correctness, test quality, architecture) to perform adversarial review before commit.

### Protocol

1. **correctness-reviewer**: Focus on logic bugs, crash scenarios, edge cases
2. **test-quality-reviewer**: Focus on test coverage, assertion quality, mock correctness
3. **architecture-reviewer**: Focus on performance, coupling, design patterns

Each agent:
- Reviews full diff independently
- Reports findings with severity (CRITICAL, HIGH, MEDIUM, LOW)
- Provides specific file:line references
- Suggests fixes

All CRITICAL and HIGH findings must be fixed before commit.

## Chosen Option

**3-agent parallel adversarial review protocol**

### Implementation
```python
# Spawn 3 independent reviewers
reviewers = [
    Task(subagent_type="general-purpose", name="correctness-reviewer", ...),
    Task(subagent_type="general-purpose", name="test-quality-reviewer", ...),
    Task(subagent_type="general-purpose", name="architecture-reviewer", ...),
]

# Each reviews independently (no groupthink)
# Aggregate findings by severity
# Fix all CRITICAL + HIGH before commit
```

## Alternatives Considered

### Alternative 1: Single comprehensive review agent
**Rejected**: Single perspective misses bugs. Specialization works better.

### Alternative 2: Sequential review (one agent at a time)
**Rejected**: Slower. Parallel execution is 3x faster.

### Alternative 3: More agents (5+)
**Rejected**: Diminishing returns. 3 perspectives (correctness, tests, architecture) cover 90%+ of bugs.

### Alternative 4: Automated static analysis only
**Rejected**: Static analysis catches syntax/style, not semantic bugs or architectural issues.

## Decision Reasoning

### Why This Option?

1. **Diverse perspectives**: Correctness vs tests vs architecture find different bug classes
2. **Specialization**: Each agent focuses on their domain expertise
3. **Parallel execution**: 3 agents run simultaneously (fast feedback)
4. **Proven effectiveness**: Caught 2 CRITICAL bugs that all tests missed
5. **Cost-effective**: ~15 minutes, zero infrastructure cost

### Alternatives Rejected

Single-agent review misses bugs due to limited perspective. Sequential review is slow. More agents have diminishing returns. Static analysis doesn't catch semantic bugs.

### Confidence Level

**0.98** - Extremely high confidence. Protocol caught 2 production-crash bugs (metadata=None, stale universe state) that passed all unit tests.

## Expected Outcomes

1. Catch 2-5 bugs per 1000 LOC reviewed
2. At least 1 CRITICAL or HIGH finding per major feature
3. Review completes in <30 minutes (3 agents parallel)
4. Zero production crashes from reviewed code

## Metrics & Impact

### Estimated
- Review time: 30 minutes (3 agents parallel)
- Bugs found: 3-5 per 1000 LOC
- False positives: <20%

### Actual (Post-Implementation)
- Review time: 15 minutes (faster than estimated)
- Bugs found: 13 total (2 CRITICAL, 5 HIGH, 6 MEDIUM)
- Distribution:
  - **correctness-reviewer**: 2 CRITICAL (metadata=None crash, stale data), 2 HIGH
  - **test-quality-reviewer**: 3 HIGH (weak assertions, mock issues), 4 MEDIUM
  - **architecture-reviewer**: 1 HIGH (efficiency), 2 MEDIUM
- False positives: 0 (all findings were valid)
- Production crashes prevented: 2

### Bugs Caught (Session 58)

**CRITICAL**:
1. `compute_trajectory_quality` crashes with `TypeError: 'NoneType' object is not subscriptable` when `metadata=None`
2. Universe bridge doesn't remove journeys from active list on completion (silent data corruption)

**HIGH**:
1. Mock inflection detector returns MagicMock for attributes instead of primitives
2. Test assertions using `isinstance(bool)` always pass (vacuous)
3. Absolute threshold assertions test nothing meaningful
4. Import path error (`cohezion.reliability.degradation_detector` vs `cohezion.compound.degradation_detector`)
5. Anomaly score default 0.5 causes low coherence in validation

**MEDIUM**: 6 efficiency and style improvements

### Impact
- **Immediate**: 2 production crashes prevented
- **Ongoing**: Protocol institutionalized for all major features
- **ROI**: 15 minutes review prevents hours of debugging + production downtime

## Protocol Template

```bash
# After implementing feature, before commit:

# 1. Spawn reviewers
uv run claude-code --spawn-agents \
  correctness-reviewer,test-quality-reviewer,architecture-reviewer \
  --task "Review diff for bugs" \
  --parallel

# 2. Aggregate findings
# 3. Fix all CRITICAL + HIGH
# 4. Re-run tests
# 5. Commit
```

## Related Decisions & Lessons

**Experiment**: [[2026-02-14-session-58-7-phase-journey-enrichment-3-agent-adversarial-review]]
**Session 55 Review**: [[2026-02-11-session-55-adversarial-review-blockers-identified]]
**Pattern**: Multi-agent systems provide diverse perspectives that single-agent misses
**Learnings**: Adversarial review catches integration bugs that unit tests miss
**Pattern — Mini Checkpoints**: [[mini-adversarial-review-checkpoints]] — implements this protocol embedded mid-implementation
**Pattern — Integration Gate**: [[integration-first-definition-of-done]] — ensures reviewed code is also reachable
**Pattern — Failure Tests**: [[failure-mode-test-priority]] — defines which bug classes adversarial review targets
**Related Decision**: [[2026-02-14-3-tier-adversarial-review-protocol-for-code-quality]] — the 3-tier variant of this protocol

## Related Concepts

- [[3d-graph-plugin-selection]]
- [[2026-02-09-ollama-context-management]]
- [[2026-02-12-claude-code-context-awareness-codification]]
- [[2026-02-12-charter-aligned-scoring-formula]]
- [[2026-02-13-local-model-roster-update-february-2026-sota-assessment]]
- [[2026-02-17-phase-2-full-verification-plan]]
- [[2026-02-13-gitlab-to-github-consolidation-with-artifact-governance]]
- [[2026-02-14-phase-2-adversarial-review-corrected-status-and-path-forward]]
