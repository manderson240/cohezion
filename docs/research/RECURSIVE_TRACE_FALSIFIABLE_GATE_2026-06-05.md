---
title: Recursive-Trace Logic — Pre-Registered Falsifiable Gate
date: 2026-06-05
status: COMPLETE (pre-registered BEFORE implementation; verdict corrected after advisor review)
author: Claude Code (V-model audit loop)
verdict: UNPROVEN (implemented + unit-tested; production value pending a real failure corpus — see §6)
---

# Recursive-Trace Logic — Pre-Registered Falsifiable Experiment

> **Pre-registration rule.** This document is written *before* `RecursiveTraceLoop.run()`
> exists. The baseline, metric, KEEP threshold, and RETIRE (false) condition below are
> fixed now and may not be edited after the data is in. If the result is RETIRE, the
> implementation is reverted and this finding stands as the deliverable.

## 0. Why this gate exists

`src/cohezion/recursive_trace/` is an **unfinished sketch**, not a leveraged capability:
- `core.py::RecursiveTraceLoop` has the algorithm in its docstring but **no `run()` method**.
- A shadowed `recursive_trace.py` (176 LOC) and a typo-dir `cohezioion/recursive_trace.py`
  (218 LOC, does not compile) contain partial copies. Left in place as documented findings;
  **not** re-tangled (advisor: keep the clean impl in `core.py`, don't resurrect dead copies).

The user asked: *"Are we fully leveraging recursive trace logic algorithms?"* — answer: **no**.
Before investing, we must answer the discriminating question the advisor posed:

> **"How is this not just autoresearch with a dedup cache?"**

## 1. The one-sentence mechanism claim (falsifiable)

> **Flat autoresearch samples the next candidate strategy *independent* of why the previous
> attempt failed; recursive-trace conditions the next candidate on the *typed failure-class*
> of the previous attempt (`failure_class → strategy` routing). Both dedup. The only variable
> is whether the failure signal informs selection.**

What autoresearch provably lacks (and recursive-trace adds): a **typed failure→strategy map**
consulted at selection time. The existing `OuroborosBridge._rotate_strategy` already encodes the
map this loop would use:

```
_KNOWN_STRATEGIES   = [standard_healer, contextual_modifier, semantic_remap, chain_insertion]
failure_strategies  = {latency:[semantic_remap], coherence_drop:[contextual_modifier],
                       structural_mismatch:[chain_insertion]}
```

If failure-class carries **no** real signal about which strategy solves the task, recursive-trace
**collapses to autoresearch-with-dedup** and must be retired. That collapse is the thing we test.

## 2. Experimental design — isolate exactly one variable

A **strategy-selection harness** runs each arm against a generated task. A task is solved when the
arm picks the task's hidden `solving_strategy`. Each arm tries strategies **without repeats** (both
dedup — that is held constant). The only difference:

| Arm | Selection rule | Models |
|---|---|---|
| **A (recursive-trace)** | next = the strategy mapped from the *latest failure-class*; fall back to unused strategies | failure-informed ordering |
| **B (fair baseline)** | next = uniform-random over *unused* strategies | memory-free, diverse, **non-repeating** |

Arm B is **not** the rigged strawman ("re-pick the same failing strategy"). It is a genuine
diverse sampler — it just ignores *why* the last attempt failed. This is the minimum-fair
control: the actual `autoresearch` loop also samples diverse candidates; the only thing it lacks
is the typed-failure conditioning, which is exactly what Arm B also lacks.

### 2.1 Task generator (the honesty mechanism)

Two regimes, generated with a controllable coupling probability `p` between the task's
`failure_class` and its `solving_strategy`:

- **INFORMATIVE** tasks: `p = 0.70` — the failure-class usually (not always) points at the solver.
- **NOISE** tasks: `p = 0.25` — `solving_strategy` is uniform over 4 strategies, **uncorrelated**
  with failure-class (0.25 = 1/4 = chance).

Arm A does **not** know which regime it is in — it always trusts the map. This is what makes the
gate falsifiable: on NOISE tasks the map is worthless and A *must* tie B. If A only ever wins
because the coupling was wired deterministically, that would be the strawman; `p=0.70`
(probabilistic, emergent over many trials) prevents that.

## 3. Metric

Primary: **mean iterations-to-solve** (number of strategy picks until the solver is found),
over `N = 2000` tasks per regime, fixed seed. Lower is better. Max 4 picks (= |strategies|),
so a uniform sampler averages `(1+2+3+4)/4 = 2.5` on noise.

## 4. Pre-registered decision rule (KEEP vs RETIRE)

Let `A_inf, B_inf` = mean iters on INFORMATIVE; `A_noise, B_noise` = mean iters on NOISE.

**KEEP** (recursive-trace is leveraged into the loop) **iff BOTH**:
1. **Exploits signal:** `A_inf < B_inf − 0.15` (A reaches the solver meaningfully faster when
   signal exists; 0.15 iters ≈ a real, not-noise gap at N=2000), **and**
2. **Harmless on noise:** `A_noise ≤ B_noise + 0.10` (A does not *mislead* when signal is absent —
   it ties within tolerance).

**RETIRE** (revert `run()`, keep this doc as the finding) **iff EITHER**:
- `A_inf ≥ B_inf − 0.15` → the failure→strategy routing carries no exploitable signal even when
  signal exists by construction ⇒ **it is autoresearch with a dedup cache**, or
- `A_noise > B_noise + 0.10` → the routing actively *hurts* when signal is absent (worse than
  random) ⇒ net-negative, retire.

## 5. Scope honesty (what a KEEP does and does not prove)

This is **Stage 1**: *"can the mechanism exploit failure-class signal when it exists?"* A KEEP
here is **provisional** — it does not prove cohezion's *real* failure stream carries that signal.
**Stage 2** (future, needs a real failure corpus from `OuroborosBridge.load_failure_analysis`)
must confirm the coupling `p` in production is meaningfully > 0.25. The pre-registration records
this so a Stage-1 KEEP is never over-claimed as "recursive-trace helps in production."

## 6. Results — VERDICT: UNPROVEN (corrected after advisor review)

### 6.0 The synthetic A/B was circular — it could not return RETIRE

The first run of this gate used a synthetic task generator (`p=0.70` INFORMATIVE,
`p=0.25` NOISE) and produced A_inf=1.593 vs B_inf=2.473 (gap +0.879), NOISE tie −0.017 →
a mechanical "KEEP". **That KEEP is not evidence and has been withdrawn.** Advisor review
caught the fatal flaw, confirmed by the transcript: the means were *hand-derived before the
run* — a falsifiable experiment is one whose verdict you do not already know.

The circularity: the task generator drew `solving_strategy` from the **same** `failure_map`
that Arm A consults. So criterion 1 (`A_inf < B_inf − 0.15`) is guaranteed for *any* coupling
`p` meaningfully above 0.25 — the verdict was fixed by the `p` I chose, not discovered.
The synthetic A/B proves only *"a correct lookup table retrieves correct answers when the
table is correct"* — which the unit test `test_failure_map_routes_to_mapped_strategy_first`
already proves. The N=2000 harness added nothing on top of the unit test.

### 6.1 The only measurement that can return RETIRE: real coupling `p`

The entire value of recursive-trace reduces to **§5's Stage 2**: does cohezion's *real* failure
stream have `p = P(fixing_strategy == failure_map[failure_class]) > 0.25`? That can only be
measured from outcomes the code did **not** generate.

`scripts/experiments/recursive_trace_gate.py` (rewritten) is now that measurement. It scans the
known corpus locations, and returns:

| Finding | Verdict |
|---|---|
| corpus exists, `p > 0.25 + 0.10` | **KEEP** — value proven on real data |
| corpus exists, `p ≈ 0.25` | **RETIRE** — confirmed "autoresearch with a dedup cache" |
| no corpus | **UNPROVEN** — implemented + tested; value pending data |

**Run 2026-06-05:** `corpus pairs found: 0`. No `(failure_class, fixing_strategy)` records
exist in any known location (`~/.cohezion-research/ouroboros/debug` absent; `…/logs/traces.jsonl`
absent; `…/logs/` present but no healing-outcome pairs). A codebase-wide grep for
`solving_strategy|fixing_strategy|resolved_by` matched only the new `core.py` — **nothing in
cohezion currently records which strategy resolved which failure class.**

### 6.2 VERDICT: UNPROVEN — and what that licenses

- **Kept (solid, per advisor):** `RecursiveTraceLoop.run()` + `TraceTask`/`RecursiveTraceResult`
  in `core.py`; the 4 discriminating unit tests; the non-destructive handling of the two dead
  copies; the deferred cli/`swarm_service` breadcrumb. The code is correct, reachable, tested,
  wired via `orphan_bridge`.
- **Withdrawn:** any "KEEP" / "improves healing" claim. The mechanism is a *plausible,
  implemented, but in-situ-unproven* capability.
- **Path to a real verdict:** to record `(failure_class, fixing_strategy)` pairs, the healing
  path (`OuroborosBridge` / DegradationDetector routing) must log the strategy that actually
  resolved each typed failure to one of the corpus locations. Once ≥ a few dozen pairs exist,
  re-run the value gate — it returns KEEP or RETIRE, no further code change needed. **Until then
  this stands as the honest finding: recursive-trace is built and tested, value unproven.**
