---
adr_number: 002
title: Cost-Routing Tiers — 70/20/10 Local-First Model Selection
date: 2026-04-23
status: ACCEPTED
deciders: cohezion-project
consulted: [swarm orchestrators, budget enforcer team, Lemonade integration]
informed: [compound executor, cost tracking, model pool manager]
authored_by: synthetic-sniffing-panda Wave Ω10 retroactive ADR
---

# ADR-002: Cost-Routing Tiers — 70/20/10 Local-First Model Selection

## Status

ACCEPTED, 2026-04-23. This ADR is RETROACTIVE — no prior explicit decision document exists; the framing is reconstructed from `src/cohezion/swarm/cost_aware_router.py`, the cost-comment annotations on the `MODEL_COSTS` table (lines 283-296), and the "Cost routing tiers" line in CLAUDE.md ("Platform Coordination" section).

## Context

Compound engineering executes thousands of LM calls per day across many specialist roles. If every call routes to the highest-quality model (Opus, GPT-4-class, etc.), the monthly bill scales linearly with executor activity and quickly exceeds the project's budget envelope. Conversely, routing every call to the cheapest local model collapses output quality below the threshold where retrospection-gated skill refinement (ADR-001 step 5) can extract usable patterns — the loop accumulates noise instead of compounding signal.

Cohezion targets AMD Strix Halo hardware (Ryzen AI MAX+ 395, 128 GiB unified memory, Radeon 8060S iGPU) explicitly so that local inference is a first-class option, not a fallback. Lemonade and Ollama provide on-machine inference with $0 marginal cost. The architectural question is: under what policy should the executor decide *which* model to dispatch a given request to?

The constraints: (a) total monthly LM spend bounded by `BudgetEnforcer`, (b) quality on complex/architectural tasks must remain at Opus-class, (c) most executor traffic is in fact simple (status checks, formatting, single-fact lookups), (d) the router must be a *primitive* the rest of the system can call without reasoning about model availability, and (e) the policy must be transparent enough that cost reports are interpretable.

## Decision

We commit to a three-tier cost routing policy with target traffic split **70% simple → free local (Lemonade/Ollama) or near-free cloud (Gemini Flash-Lite, $0.075/M); 20% medium → Sonnet-class or Gemini 2.5 Flash ($0.30/M); 10% hard → Opus-class or Gemini 2.5 Pro ($2.00/M)**. The router is a singleton (`CostAwareRouter.get_default()`) that combines a `QueryComplexityAnalyzer` (keyword + token-count heuristics, `cost_aware_router.py:88-194`) with a model registry of cost, quality, TPS, and latency (lines 283-344) and a confidence-driven escalation rule: when the chosen model's quality-vs-task confidence falls below 0.7, escalate one tier (line 524). `BudgetEnforcer` provides hard stops; the router consults it before every dispatch.

## Rationale

The 70/20/10 split is not a measurement of where queries naturally fall — it is a *target* the router enforces by aggressive simple-tier routing (`aggressive_cost_reduction=True` default). The empirical observation behind the target is that the majority of executor calls are short, factual, or formatting tasks for which local 3B-7B models are sufficient. Reserving the expensive 10% for genuinely architectural/complex work is the discipline that keeps monthly spend bounded while preserving quality where it matters.

Confidence-driven escalation (line 524: `if confidence < 0.7: # Local models underperforming — escalate one tier`) is the safety valve that prevents the cost discipline from degrading quality silently. When the simple-tier model returns low confidence — measured via OI-MAS joint role+scale scoring, arXiv:2601.04861 — the router does not stay at the cheap tier; it promotes one rung. This makes the 70/20/10 split a *floor* on cheap traffic and a *target* on expensive traffic, not a hard quota that compromises quality.

The integration with `BudgetEnforcer` (lines 36-37, hard-stop checks) is the second discipline: even if the routing analyzer wants Opus, the budget enforcer can refuse and force a downgrade. This decouples the per-call routing decision from monthly-budget enforcement and lets the budget enforcer be replaced or tuned without rewriting the router.

## Alternatives considered

(Alternatives reconstructed from analogous patterns in the AI agentic-framework space.)

### Option A: Always-Opus (highest quality)
- Pros: Maximum quality on every call; simplest mental model.
- Cons: Monthly cost scales with executor activity; bankrupts the budget envelope after ~10⁴ daily calls.
- Why rejected: Incompatible with the project's solo-funded operating model and the Strix Halo investment in local inference.

### Option B: Always-cheapest (Lemonade only)
- Pros: $0 marginal cost; full local autonomy; no rate limits.
- Cons: Quality on architectural tasks falls below the threshold where retrospection produces usable patterns; skill refinement starts amplifying noise.
- Why rejected: Empirically, complex queries (design, optimize, debug — see `COMPLEX_KEYWORDS` at line 106) require capabilities current local models do not match. The 95%+ semantic cache hit rate (CLAUDE.md) makes "just retry on Opus" a viable manual escalation, but routing every call through it defeats the cache benefit.

### Option C: Dynamic-bandit (online learning)
- Pros: Adapts to observed quality/cost trade-offs without manual tuning.
- Cons: Cold start is poor; reward signal is noisy (skill refinement happens downstream of routing); explainability suffers — cost reports become "the bandit chose Opus on this query" with no further interpretable reason.
- Why rejected: Not chosen *yet*. The project's current scale doesn't justify bandit overhead, and the explainability cost is real. Reconsider when daily-call volume exceeds 10⁵ and the static thresholds are demonstrably miscalibrated.

### Option D (chosen): Three-tier static policy with confidence escalation + budget enforcement
- Pros: Predictable cost; transparent reports; escalation handles the "this should be expensive" cases; local-first preserves the Strix Halo investment.
- Cons: Static thresholds drift relative to model improvements; the 70/20/10 split is a target, not a measurement, so the router can over-route to cheap if the analyzer is biased.
- Why chosen: The right primitive for the project's current scale and budget. The escalation rule plus budget enforcer cover the failure modes that pure static routing would suffer.

## Consequences

### Positive
- Monthly LM spend is bounded by the 10%-Opus tier and `BudgetEnforcer` hard stops.
- Local-first routing exercises the Strix Halo hardware investment.
- Cost reports are interpretable: "70% local, 20% Sonnet, 10% Opus" tells a budget reviewer exactly what is happening.
- The router is a swappable singleton — alternative policies can be tested by swapping `CostAwareRouter.get_default()`.

### Negative
- Static thresholds need periodic re-tuning as new models ship (e.g., when local 7B catches Sonnet-3, the simple→medium boundary shifts).
- The keyword-based complexity analyzer (lines 92-122) misclassifies queries that lack explicit signal words; a query that is genuinely complex but phrased innocuously gets under-routed.
- The 70/20/10 target is enforced by `aggressive_cost_reduction=True` (line 355); turning that off changes the realised distribution dramatically.

### Neutral
- The router does not handle multi-model debate or ensemble routing; that lives in `swarm/democratic_debate.py`.
- The escalation rule fires on `confidence < 0.7`; this threshold is itself static and could be promoted to a config field.

## Implementation

- Primary files:
  - `src/cohezion/swarm/cost_aware_router.py` (1049 lines; `CostAwareRouter` class; `MODEL_COSTS` at lines 284-296; `MODEL_QUALITY` at lines 306-318; `select_model` at line 414; escalation at line 524).
  - `src/cohezion/cost_optimization/budget_enforcer.py` (`BudgetEnforcer`).
  - `src/cohezion/cost_optimization/cost_tracker.py` (`SessionCostTracker`).
  - `src/cohezion/swarm/dynamic_model_router.py` (per-task pool-availability routing layer above the cost router).
- Test files: `tests/swarm/test_cost_aware_router.py`, `tests/cost_optimization/test_budget_enforcer.py`.
- Documentation: CLAUDE.md "Cost routing tiers" line; this ADR.

## Verification

- Static check: `grep -E "0\.000075|0\.0003|0\.002" src/cohezion/swarm/cost_aware_router.py` returns the three-tier Gemini cost annotations (lines 293-295).
- Runtime check: `uv run python -c "from cohezion.swarm.cost_aware_router import CostAwareRouter; r = CostAwareRouter.get_default(); print(r.get_routing_statistics())"` after a representative session — `phi3_routed / total_queries` should be ≥ 0.6 in steady state.
- Test: `uv run pytest tests/swarm/test_cost_aware_router.py::test_routing_distribution_70_20_10 -q` (if absent, this is the test to write).

## Reversal cost

**MEDIUM.** The router is a single swappable component (`CostAwareRouter.get_default()` is the only public entry point), so substituting a different policy is mechanically easy. The cost is in the *downstream callers* that depend on the cost-tracking data shape produced by `RoutingStatistics` (lines 73-85) and the metrics aggregator's per-model cost slices. Estimated effort to swap the policy: 1-2 person-weeks; estimated effort to also re-shape downstream cost reporting: an additional 1-2 weeks.

## Related ADRs

- Depends on: ADR-001 (the eleven-step loop's step 2 invokes this router).
- Informs: future ADR on bandit-style online routing if/when scale justifies it.
- Tension with: ADR-003 (consensus voter — multi-agent voting multiplies LM calls; the cost router must understand that consensus tasks dispatch N calls and budget accordingly).

## References

- CLAUDE.md, "Platform Coordination" → "Cost routing tiers" line.
- `research/distillates/2026-04-23-vault-decisions-distillate.md` (Decision #7: Model Wrangler Strategy; Decision #10: MCP Infrastructure Architecture).
- OI-MAS confidence scoring: arXiv:2601.04861 (cited in `cost_aware_router.py:60`).
- Strix Halo hardware profile: `HARDWARE_PROFILE_PRIME.md`.
