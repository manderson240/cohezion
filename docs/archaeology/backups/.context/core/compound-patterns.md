---
title: Compound Patterns
description: Compound AI engineering patterns for Cohezion
created: 2026-03-08
traced_from:
  - source: .claude/skills/compound-engineering
    section: Instructions
    commit: 810f2e10
  - source: .claude/skills/compound-engineering/references/key-concepts.md
    section: All
    commit: 810f2e10
coherence_threshold: 0.5
---

# Compound Engineering Patterns

## 11-Step Pipeline
```
Request → RequestAlignmentAnalyzer (coherence check)
        → SkillSelector (find relevant skills)
        → PlanExecutor (tactical plan)
        → ExecutionOrchestrator (execute)
        → GlobalMetricsAggregator (record metrics)
        → DegradationDetector (check thresholds)
        → JourneyTracker (12D position)
        → RetrospectionEngine (extract learnings)
        → SkillRefiner (update skill)
        → SkillConsensusVoter (validate)
        → Result
```

## Coherence Gates (HIHO)
Check alignment before execution:

```python
from cohezion.compound.request_alignment_analyzer import RequestAlignmentAnalyzer

analyzer = RequestAlignmentAnalyzer()
alignment = analyzer.analyze(request_state, available_skills, agent_context)
if alignment.coherence < 0.5:  # HIHO threshold
    # Escalate or decompose into smaller requests
    pass
```

## Offload Pattern
Route menial tasks to local SLMs:
- **phi3:mini**: Verification tasks
- **qwen3-coder**: Code generation

```python
# Use offload_task or BaseAgent.offload_to_local
result = await agent.offload_to_local("format_docstrings", code)
```

## Future Hooks Requirement
Every new skill/feature MUST include a `## FUTURE HOOKS` section with at least 3 ways this feature makes future tasks easier.

## FUTURE HOOKS (for this context system)
1. **Context coherence tracking**: Future sessions will auto-check context coherence before loading
2. **Skill-aware loading**: Future system will only load context sections relevant to active skills
3. **Trace evolution**: Future retrospection will track how context rules evolve over commits
