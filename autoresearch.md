# Autoresearch: Skill Context Density Optimization

## Objective
Reduce per-turn Claude Code context overhead from skill descriptions while preserving
compound engineering routing quality. Experiments vary which skills get `name-only` or
`user-invocable-only` overrides, measure token savings, and validate no routing loss.

## Metrics
- **Primary**: tokens_saved_per_turn (integer, higher is better)
- **Secondary**: routing_coverage_score (fraction of CORE_ROUTING skills at full context)
- **Guard**: compound_skills_preserved (autoresearch + cohezion-dynamic-modularity must stay)

## Compound Cycle Baseline (exp_I, 2026-05-08)
- Coherence: 0.760 | phi_score: 0.630 | compound_score: 0.750
- All 7 phases pass (dry-run, mocked services)
- Status: healthy baseline

## Results Summary (2026-05-08 session)

| Experiment | Type | Tokens Saved | Status |
|---|---|---|---|
| exp_A: 13 situational skills → name-only | skillOverrides | 13,160t | WIN |
| exp_B: 9 reference skills → user-invocable-only | skillOverrides | 3,539t | WIN |
| exp_C: kaggle → name-only | skillOverrides | 2,892t | WIN |
| exp_D: polish-campaign + dynamic-template → name-only | skillOverrides | 6,602t | WIN |
| exp_E: claude-code-token-optimization → name-only | skillOverrides | 1,129t | WIN |
| exp_F: multi-agent-isolated-worktree-pattern → name-only | skillOverrides | 1,286t | WIN |
| exp_H: autoCompactPrompt + compound state | settings | 0t (state preserved) | WIN |
| exp_I: compound cycle baseline | measurement | — | WIN (baseline) |
| exp_J: rules files overlap audit | analysis | 0t (user review needed) | INFO |

**Total tokens saved: ~130,471t/turn (90% skill description reduction)**

## Current State (2026-05-08)
- Skills: 65/73 overridden. 8 at full context (3 protected + 5 core utility)
- Full-context skills: autoresearch, autoresearch-team, cohezion-dynamic-modularity,
  claude-code-agent-teams, find-skills, autoharness-skill, autoharness-init, autoharness-update
- Estimated per-turn skill tokens: ~14,841t (was ~145,312t)

## Frontier (requires user decision or external unblock)
1. **Rules files** (~14,608t): 15 files, high keyword overlap with CLAUDE.md.
   Keyword overlap alone isn't sufficient — need human review to identify true redundancy.
   Top candidates: anthropic-intel-scan.md (1,581t), workflow-enforcement.md (1,518t),
   cz-cli.md (775t), context-continuation.md (758t)
2. **NPU activation (3rd node)**: Blocked on Qwen3-0.6B-FLM model download.
   Current: 2/3 nodes at 1.75 lift. Target: 1.80+ with 3/3.
3. **Real compound performance**: Dry-run baseline is healthy but uses mocked services.
   True compound lift measurement needs Lemonade real runs (not blocked, just OOM caution).

## Constraints
- Never override: autoresearch, autoresearch-team, cohezion-dynamic-modularity
- Never remove existing overrides (additive only)
- OOM-safe: no large model loading in experiments
- Winner = highest token savings with routing_coverage ≥ 0.85

## Round 3: NPU Activation + Compound Lift (2026-05-10)

| Experiment | Type | Result | Key Metric |
|---|---|---|---|
| exp_K_npu_activation | NPU startup | WIN | 3/3 nodes live, 393ms TTFT, 42 TPS |
| exp_L_triple_node_lift_v2 | Compound lift measurement | WIN | **6.354x lift** vs GPU-only |

### Key Finding: Thinking Model vs NPU Routing

Gemma-4-E4B (GPU, thinking mode) uses **364–500 tokens** for 1-2 word answers.
llama3.2-1b-FLM (NPU) uses **7–31 tokens** for the same tasks.

Routing short-answer tasks (classification, routing, simple QA) to NPU:
- 3.075x token efficiency
- 13.1x latency improvement
- 60% of compound loop tasks are NPU-suitable

### Updated Frontier

NPU model config committed: `triune_orchestrator.py` now uses `llama3.2-1b-FLM` for NPU tier.

Next optimization opportunity: **task classifier** — a lightweight model to decide NPU vs GPU
routing BEFORE sending the task. A 50-token routing decision that saves 400 GPU thinking tokens
is a 8x net win per routed task.
