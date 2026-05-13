# Autoresearch Ideas — Future Experiments

Generated from session discoveries. These are the most promising
next steps for compound engineering optimization.

## Immediate (next session)

### ID-1: Rules file trimming (high token value, blocked on human review)
- 15 rules files, ~15,552t total
- 2 high-overlap candidates: python-rules.md (356t, 61%), memory.md (413t, 61%)
- Action: Review each for content that's covered by CLAUDE.md
- Expected savings: up to ~770t/turn if both trimmed
- Risk: LOW (additive-only rule ensures nothing lost)

### ID-2: Real compound loop routing accuracy measurement
- Current: tested on 13 synthetic compound loop prompts (all correct)
- Need: extract actual compound loop prompts from session history
  - Run `jq` on ~/.claude/projects/**/jsonl files for "user" messages
  - Filter prompts > 50 chars, not system injections
  - Run classifier on each, compare expected vs actual routing
- Expected: find 5-10% edge cases for further pattern refinement

### ID-3: context_engineering ↔ model_card_harness integration
- Currently: two parallel modules with overlapping model data
- Opportunity: use model_card_harness.from_live_api() to auto-populate
  context_engineering registry with live model labels + ctx_size
- Would eliminate need for manual card maintenance
- Risk: MEDIUM (live API required, but graceful fallback exists)

## Medium-term

### ID-4: NPU throughput batching experiment
- llama3.2-1b-FLM achieves 42 TPS for sequential requests
- Hypothesis: batch short categorical tasks (e.g., 5 classifications at once)
  could improve throughput to 60+ TPS via queue effects
- Test: send 5 simultaneous requests, measure aggregate TPS vs sequential

### ID-5: Adaptive quality gate thresholds
- Current: fixed min_chars per tier (0 for categorical, 10 for short_answer)
- Idea: measure actual response length distribution per output_type
  and set gate = p10(length) to pass 90% of good responses
- Requires: 100+ live responses per output_type to measure distribution

### ID-6: Compound lift with task classifier on production traces
- Current: 6.354x lift measured on 5 synthetic tasks
- Need: measure on real compound loop iteration traces
- Method: replay last 10 compound loop task sets with/without classifier

## Future

### ID-7: Semantic cache hit rate measurement
- Claims 95%+ hit rate but never measured empirically
- Method: add hit/miss logging to SemanticCache, run 100 prompts
- Expected: validate or find where cache is missing

### ID-8: Post-compact hook: inject compound loop task distribution
- Currently injects: plan, autoresearch, NPU status, config, token savings
- Missing: what % of tasks are NPU-suitable (from recent session history)
- Would help re-orient next session's routing decisions immediately
