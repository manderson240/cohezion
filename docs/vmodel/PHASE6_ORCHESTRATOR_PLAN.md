# V-Model Phase 6 — Tiered Orchestrator (Smarter-Advises-Dumber)

**Workstream:** sorted-churning-toucan — Phase 6
**Date:** 2026-04-18
**Pairs with:** `scripts/validation/vmodel/phase6_orchestrator_harness.py`, `src/cohezion/inference/orchestrator.py`, `tests/inference/test_orchestrator.py`.

## 1. Requirement

Abstract Claude Code's `/advisor` pattern (primary model invokes a smarter secondary model mid-task) and apply it to the whole Cohezion fleet, recursively: **agents → sub-agents → sub-sub-agents**, where each tier is a more capable model advising or delegating to the tier below it.

Concretely: make it possible for an agent at the NPU-Gemma-E2B tier to propose an action, have Sonnet (or Opus) review it silently, and re-run with a better prompt if the smarter model flags the response as low-confidence. Every tier is optional and independently configurable.

## 2. Descending Path

### 2.1 Tier hierarchy (default)

```
Tier 4 ARBITER    claude-opus-4-7          final adjudicator when tiers disagree
Tier 3 REVIEWER   claude-sonnet-4-6        reviews proposals, escalates if needed
Tier 2 ADVISOR    claude-haiku-4-5         first cloud fallback / quality gate
Tier 1 MIDSIZE    Gemma-4-26B-A4B or       iGPU reasoning
                  phi4:latest (Ollama)
Tier 0 PRIMARY    Gemma-4-E2B-it-GGUF      NPU — does the work
                  (or qwen3.5:4b-FLM)
```

Primary executes; each higher tier (if wired) can step in on escalation.

### 2.2 Module shape

```python
from cohezion.inference.orchestrator import TieredOrchestrator, QualityGate

orch = TieredOrchestrator(
    tiers=[
        ("Gemma-4-E2B-it-GGUF", QualityGate(min_chars=20)),
        ("Gemma-4-26B-A4B-it-GGUF", QualityGate(min_chars=40)),
        ("claude-haiku-4-5", QualityGate(min_chars=60)),
        ("claude-sonnet-4-6", QualityGate.TRUST),
    ],
    max_cost_usd=0.02,  # hard cap
)
result = await orch.run("Summarize this 500-line diff.")
# result.primary_model, result.final_model, result.escalations, result.cost_usd
```

**Recursive delegation:** a tier can itself be a `TieredOrchestrator`, so sub-agents can have their own sub-sub-agents:

```python
coder_sub = TieredOrchestrator(tiers=[
    ("qwen3-coder:30b", QualityGate(min_chars=30)),
    ("claude-sonnet-4-6", QualityGate.TRUST),
])
planner = TieredOrchestrator(tiers=[
    ("Gemma-4-E2B-it-GGUF", QualityGate(min_chars=20)),
    (coder_sub, QualityGate.TRUST),  # tier = another orchestrator
    ("claude-opus-4-7", QualityGate.TRUST),
])
```

### 2.3 Invariants

| # | Invariant | Rationale |
|---|-----------|-----------|
| O1 | Tiers are **ordered by priority** (tier[0] tried first); higher tiers never run if tier[0] passes its quality gate | Cost discipline |
| O2 | Every escalation is **logged** with (tier_from, tier_to, reason, timestamp) | Observability |
| O3 | `max_cost_usd` is **enforced** — orchestrator short-circuits before a tier that would exceed it | Budget gate |
| O4 | A tier can itself be a `TieredOrchestrator` (composable recursion) | Agents → sub-agents → sub-sub-agents |
| O5 | `QualityGate.TRUST` always passes; `QualityGate(min_chars=N)` passes if `len(result.text) >= N` | Deterministic gate semantics |
| O6 | Orchestrator returns a structured `OrchestrationResult` with primary_model, final_model, escalation_count, tier_path, cost_usd, latency_ms | Downstream telemetry |
| O7 | When every tier fails its gate, return a clearly-flagged **exhausted** result (`error="all tiers exhausted"`), not raise | Don't crash mid-loop |
| O8 | Orchestrator is an `async def` — composes with existing `route()` / `extend_claude()` | Reuse, no new dispatch code |

### 2.4 Acceptance criterion

`make vmodel-phase6` passes all 8 invariants. `tests/inference/test_orchestrator.py` covers:
- Tier 0 gate passes → only tier 0 runs
- Tier 0 gate fails → tier 1 runs
- All gates fail → returns exhausted result
- Budget cap stops escalation early
- Recursive composition (orchestrator-as-tier) works
- Escalation log is ordered and complete

## 3. Apex

- `src/cohezion/inference/orchestrator.py` (target ≤ 300 LOC)
- Public export: `TieredOrchestrator`, `QualityGate`, `OrchestrationResult`
- Wired into `cohezion.inference.__init__.py`

## 4. Ascending Path

- **Unit** → new pytest file
- **System** → live demo: NPU proposes, Sonnet reviews, counts match expectation
- **Acceptance** → `vmodel_acceptance.py` logs `{name: 'orchestrator', status: 'verified'}`

## 5. Why this matters for Universes

Universes-team agents don't just call one model — they *compose* models. A planner delegates to specialists, each specialist may spawn sub-agents. The orchestrator is the API that makes that composition cheap, observable, and cost-bounded. It turns the fleet from "model router" into "agent-swarm substrate."
