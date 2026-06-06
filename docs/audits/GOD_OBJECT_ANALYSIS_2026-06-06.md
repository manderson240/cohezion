---
title: "God-object analysis — cohesion metric over the large files (report-only)"
created: 2026-06-06
owner: "/loop self-improvement (item 10)"
verdict: "0 true god-objects among 137 files >500 LOC. LOC is a poor god-object proxy — the cohesion metric (LCOM4 + 2nd-cluster size) DISCONFIRMS the split hypothesis for every large file. Report-only, no splits proposed (none warranted). Reusable instrument: scripts/audits/cohesion_audit.py."
---

# God-object analysis

## The falsifiable requirement
"Each god-object call must be backed by a **cohesion metric**, not just LOC." So no file is
called a god-object on size alone — every claim is gated on a measured metric, and the metric
is allowed to come back *negative* (no god-objects). It did.

## Metric — LCOM4, refined by 2nd-cluster size
**LCOM4** = the number of connected components in a class's method graph, where two methods are
linked if they share an instance attribute (`self.x`) or one calls the other. LCOM4 == 1 is
cohesive; LCOM4 ≥ 2 *suggests* multiple responsibilities.

**The refinement that matters** (discovered via the cluster dump): raw LCOM4 **over-counts
singleton utility methods**. `CostAwareRouter` has LCOM4 = 5 — but the clusters are a single
**23-method cohesive core** plus four 1-method utilities (`reset`, `reset_singleton`,
`get_default`, `_get_model_attr` — staticmethod-style helpers that touch no `self` state).
That is **one** responsibility plus utilities, not five. The honest god-object signal is the
**size of the 2nd-largest cluster**: a true god-object splits into two *substantial*
responsibilities (≥4 methods each), not one core + singletons.

## Result — 0 true god-objects (the metric disconfirms the hypothesis)
Across **137** files >500 LOC (the backlog's "36" was a large undercount), ranked by
2nd-cluster size:

| LOC | LCOM4 | methods | 2nd-cluster | flag | worst class @ file |
|---|---|---|---|---|---|
| 549 | 3 | 10 | **2** | watch | `ContextPolicy` @ compound/context_policy.py |
| 1408 | 5 | 27 | 1 | cohesive | `CostAwareRouter` @ swarm/cost_aware_router.py |
| 1016 | 4 | 22 | 1 | cohesive | `JourneyTracker` @ compound/journey_tracker.py |
| 754 | 5 | 20 | 1 | cohesive | `BMADEngine` @ mcp/servers/bmad/engine.py |
| 862 | 3 | 17 | 1 | cohesive | `ExperimentTracker` @ universe/experiment_tracker.py |
| 654 | 3 | 17 | 1 | cohesive | `JEPAWorldModel` @ world_model/jepa_world_model.py |

- **GOD (2nd-cluster ≥ 4): 0 files.** Not one large class splits into two substantial,
  state-disjoint responsibilities.
- **watch (2nd-cluster == 2): 1 file** — `ContextPolicy` (a 10-method class with one 2-method
  side-cluster). Marginal; an optional human review, not a mandate.
- **cohesive (2nd-cluster ≤ 1): 135 files.** The biggest files in the repo
  (`CostAwareRouter` 1408 LOC, `JourneyTracker` 1016, `BMADEngine` 754) are large because the
  domain is rich, not because they're incohesive — every method hangs off one shared-state core.

## Interpretation
**LOC is a poor god-object proxy.** The hypothesis "the big files need splitting" is *falsified*
by the cohesion metric: the large files earn their size on a single cohesive responsibility.
Splitting them on LOC grounds would *reduce* cohesion (scatter one responsibility across files)
— the opposite of the intent. Non-destructive policy is doubly satisfied: there is nothing to
split, and the instrument proves it rather than asserting it.

## Reusable instrument
`scripts/audits/cohesion_audit.py` — `python scripts/audits/cohesion_audit.py` ranks all
>500-LOC files by 2nd-cluster size; `python scripts/audits/cohesion_audit.py <file> <Class>`
dumps a class's responsibility-clusters (the split targets, if any ever appear). Run it in CI
or after large additions to catch a *future* god-object the moment a 2nd substantial cluster forms.
