---
adr_number: 001
title: The Eleven-Step Compound Engineering Loop
date: 2026-04-23
status: ACCEPTED
deciders: cohezion-project
consulted: [compound team, retrospection engine designers, vault keepers]
informed: [swarm orchestrators, skill refinement consumers, observability engineers]
authored_by: synthetic-sniffing-panda Wave Ω10 retroactive ADR
---

# ADR-001: The Eleven-Step Compound Engineering Loop

## Status

ACCEPTED, 2026-04-23. This ADR is RETROACTIVE — no prior explicit decision document exists; the framing is reconstructed from the implementation in `src/cohezion/compound/executor.py` (post Wave 2D), the SPIN-coherence manuscript (`research/manuscripts/2026-04-23-spin-coherence-compound-loop.md`), and the project-wide commitment to "compound engineering" recorded in CLAUDE.md.

## Context

Long-horizon agentic systems exhibit a characteristic failure mode: each language-model invocation incrementally shifts the agent's implicit beliefs, eventually producing trajectories that no longer align with the original task intent ("belief drift"). Most agent frameworks address this with ad-hoc pipelines that compose whatever steps the current task seems to need. The cost is that observability becomes per-task, retrospection becomes opportunistic, and skill refinement has nothing stable to refine against.

Cohezion's animating thesis is that *every* interaction should make subsequent interactions easier. This is impossible to satisfy if the executor's structure varies per task — there is no fixed surface against which patterns can accumulate, no canonical place to log a trajectory, and no place to attach a degradation alarm. A compound system needs a *fixed-order* pipeline that every execution walks through, even when the work itself is heterogeneous.

The constraint set the loop must satisfy: (a) every task produces a comparable trajectory record, (b) skill refinement is gated by retrospection so it never mutates skills on a single noisy outcome, (c) coherence is measured continuously and surfaces a HIHO-band degradation flag, (d) optional collaborators (alignment analyzer, universe bridge, mycelium capture) can be attached without re-ordering the core steps, and (e) the loop runs on Strix Halo hardware — no datacenter dependence.

## Decision

We commit to a fixed eleven-step pipeline executed by `CompoundExecutor.execute_task()` for *every* compound task: (1) Query Vault for experience guidance, (2) Execute with token-efficient client, (3) Log Trajectory to vault, (4) Extract Patterns via retrospection, (5) Skill Refinement (gated), (6) Quality Checks (input + output guardrails), (7) Persistence, (8) Alignment Check (`RequestAlignmentAnalyzer`), (9) Metrics (`GlobalMetricsAggregator`), (10) Degradation Detection (HIHO band), (11) Journey Tracking (12-D state update). Optional sub-steps (5.8 cohesion score, 7.6 bioelectric, 10.5 Ouroboros, 10.6 Mycelium) attach to step boundaries without altering core ordering. Every collaborator is *injected* into the constructor and is independently optional, but the *sequence* is fixed.

## Rationale

The fixed-order constraint converts the loop from a coding pattern into an *architectural invariant*. Because steps 3, 7, 9, and 11 are guaranteed to fire on every task, downstream consumers (vault search, metrics aggregator, journey tracker, skill refiner) can assume their inputs exist and stop defending against missing data. This is the structural reason compound effects accumulate: each new task adds a comparable point to a comparable population.

Steps 4-7 form the learning arc — pattern extraction feeds skill refinement which feeds persistence which seeds the next iteration's step 1. Steps 8-11 form the diagnostics arc — alignment, metrics, degradation, and journey tracking all read the same trajectory record. The split is deliberate: learning is allowed to be slow and gated, diagnostics must be cheap and unconditional. By placing the diagnostics arc *after* learning, a degraded skill update is detected on the same execution that produced it.

The choice to inject collaborators (rather than bake them in) preserves testability and lets the system run in degraded modes where, say, the universe bridge is offline but the loop still completes. Every collaborator slot in the constructor (`src/cohezion/compound/executor.py:74-93`) is `Any | None`, and the per-step blocks (`# Step N` comments at lines 380-1013) check for the collaborator before invoking. This is the dependency-injection contract that makes the loop both rigid in shape and flexible in components.

## Alternatives considered

(Alternatives reconstructed from analogous patterns in the AI agentic-framework space; no prior internal options doc was located.)

### Option A: Ad-hoc per-task pipeline
- Pros: Maximum flexibility; each task uses only what it needs.
- Cons: No comparable trajectory record across tasks; metrics aggregation becomes a bespoke join; skill refinement has no stable input shape.
- Why rejected: Defeats the compound-engineering thesis. If executions are not comparable, patterns cannot compound.

### Option B: Agent-graph framework (LangGraph-style state machine)
- Pros: Explicit graph topology; easy to visualize; supports branching.
- Cons: Branching topology means different tasks traverse different node sequences, re-introducing the comparability problem; the framework's own state-machine semantics become a moving target.
- Why rejected: The compound loop is not a workflow engine. Its job is to produce a *uniform* execution shadow, not to express arbitrary control flow.

### Option C (chosen): Fixed-order eleven-step pipeline with injected collaborators
- Pros: Uniform trajectory shape; collaborators independently optional; learning and diagnostics arcs are structurally separated; HIHO degradation flag is meaningful because it always fires at step 10.
- Cons: Adding a new core step requires touching every executor call site; the eleven number is arbitrary and risks ossifying.
- Why chosen: The architectural invariant is more valuable than the local flexibility. The eleven steps are the canonical surface that compound engineering compounds *against*.

## Consequences

### Positive
- Every execution produces a comparable trajectory; downstream consumers can assume input shape.
- Retrospection-gated skill refinement (step 4 → step 5) prevents single-outcome noise from corrupting skills.
- Degradation flag (step 10) is meaningful because it fires on every execution.
- New collaborators integrate by attaching to a step boundary, not by re-architecting the loop.

### Negative
- The eleven steps are now load-bearing; reordering or removing one is an architectural change.
- Optional sub-steps (5.8, 7.6, 10.5, 10.6) accumulate, drifting toward an effective 15-step loop without that being explicit.
- Constructor signature is heavy (15+ optional collaborators); discoverability suffers.

### Neutral
- The loop is single-task; multi-task batching is a separate concern (handled by `swarm/team_executor.py`).
- The HIHO threshold at coherence ≈ 0.5 is empirical and lives outside this ADR.

## Implementation

- Primary files:
  - `src/cohezion/compound/executor.py` (1060 lines; class `CompoundExecutor` at line 59; `execute_task` at line 307; per-step markers at lines 380, 435, 438, 523, 544, 586, 684, 730, 879, 897, 971, 984, 1013).
  - `src/cohezion/compound/exp_persistence/vault.py` (`VaultLogger`, used at step 3).
  - `src/cohezion/compound/retrospection.py` (step 4).
  - `src/cohezion/compound/skill_refiner.py` (step 5).
  - `src/cohezion/security/guardrail_pipeline.py` (step 6).
  - `src/cohezion/compound/request_alignment_analyzer.py` (step 8).
  - `src/cohezion/compound/global_metrics_aggregator.py` (step 9).
  - `src/cohezion/compound/degradation_detector.py` (step 10).
  - `src/cohezion/compound/journey_tracker.py` (step 11; `AXIOMATIC_DIMS = 12` at line 105).
- Test files: `tests/compound/test_executor.py`, `tests/compound/test_journey_tracker.py`, `tests/compound/test_retrospection.py`.
- Documentation: CLAUDE.md "The Compound Engineering Loop (Production-Ready)" section; this ADR.

## Verification

- Static check: `grep -nE "# Step [0-9]" src/cohezion/compound/executor.py | wc -l` should yield ≥ 11. The per-step comment markers are part of the contract.
- Runtime check: `uv run python scripts/drivers/compound_cycle.py --dry-run` exercises the full loop and reports each step's collaborator status.
- Test: `uv run pytest tests/compound/test_executor.py -q` — confirms the loop runs end-to-end with all collaborators stubbed.

## Reversal cost

**HIGH.** The eleven-step loop is the compound-engineering thesis incarnate. Reversing it would require re-defining how the vault, retrospection engine, skill refiner, alignment analyzer, metrics aggregator, degradation detector, and journey tracker each receive their inputs — they all assume the trajectory shape produced by `execute_task`. Estimated effort to remove or substantially re-architect: 3-5 person-weeks across the compound, swarm, and persistence layers, plus a re-baseline of the metrics history. Practical reversal threshold: only if a different uniform-shape primitive (e.g., trace-based observability via OpenTelemetry spans) provably outperforms the current logger on cost and discoverability.

## Related ADRs

- Depends on: ADR-004 (vault-first knowledge — step 1 and step 7 both read/write the vault).
- Informs: ADR-002 (cost routing — step 2 invokes the cost-aware router); ADR-003 (skill consensus voter — step 5 can be configured to use multi-agent voting); ADR-005 (FLUME — step 1's experience guidance and step 11's journey tracking both encode through FLUME).
- Tension with: none currently identified; the loop is a foundational invariant.

## References

- CLAUDE.md, "The Compound Engineering Loop (Production-Ready)" section.
- `research/manuscripts/2026-04-23-spin-coherence-compound-loop.md` (§4 walks each step's re-alignment role).
- `research/distillates/2026-04-23-vault-decisions-distillate.md` (Decision #4: compound-engineering meta-learning expansion).
- Schmidhuber, J. (2007). Gödel machines. (Theoretical antecedent for self-improving loops.)
- Wang, G. et al. (2023). Voyager: An open-ended embodied agent with large language models. arXiv:2305.16291. (Skill-library precedent.)
