# Capability-Orphan Cluster — Classification Table (item 143)

**Date:** 2026-06-07  **Mode:** report-only (NO forced wires)  **Authored by:** build loop, escalated to human

## Why this exists

Three consecutive build-loop ticks (140 `cost_dashboard`, 141 `surprise_explorer`,
142 `concierge`) each resolved to *capability-orphan → HUMAN*: a real component that
reads real data, but whose consumer is an **architecture/surface decision**, not a
mechanical wire. That is Learning-227 "build-then-forget" debt **clustering**. Rather
than the loop hitting each remaining module one-by-one and punting, this table surfaces
the whole cluster at once so the decisions can be **batched**.

## The discriminating test (how each row was classified)

> **Is there a LIVE production seam (a reachable, non-test, non-`__init__` call site)
> that merely needs *populating* with this component — and does the component degrade
> gracefully if its backend is absent?**
>
> - **Yes, live seam + graceful** → `mechanically-wireable` (the loop can clear it next
>   tick with a discriminating test; do NOT park as "architecture").
> - **No live seam; the missing consumer is a design/surface/backend choice** →
>   `architecture-decision` (human batches it).
> - **The "missing consumer" is external activation (an IDE host, a trained model, a
>   backend that doesn't exist yet), not missing code** → `dormant-by-design`.

Every row below was verified by grep for a production constructor/caller of the module's
main class, **excluding** the module's own file, `__init__.py` re-exports, and tests.

## Table

| Module | Main class | Live seam? | Classification | Natural consumer / decision |
|---|---|---|---|---|
| `flux.cache_flux` | `CacheFlux` | **YES** — `compile_natural_language()` → `VibeOrchestrator(flux_aggregator=…)`; specifier `_find_similar_workflows` queries it **and the return reaches the spec** (`specifier.py:239 similar_past_workflows=similar`). `SemanticCache` **is** populated in prod (harness CB4) → real data flows. Degrades gracefully (`cache=None → []`). | **mechanically-wireable** | Construct `FluxAggregator([CacheFlux(SemanticCache.get_instance())])` at the live seam; discriminating test: seed SemanticCache L2 with a workflow-tagged entry → compile NL → assert `spec.similar_past_workflows` non-empty (asserts **real** prod data, not a test-only precondition). |
| `flux.history_flux` | `HistoryFlux` | seam yes, but its **write path** (`record_history`) runs only on `graph/engine.py`'s aggregator, which itself defaults `None` and is **never constructed-with-providers in prod**. A *separate* vibe-seam aggregator's HistoryFlux is therefore **always empty** in prod. | **architecture-decision** | A test would only pass by seeding history itself (tautological). Real surfacing needs graph-engine writes and vibe reads to **share one aggregator** — a "context bus" decision (exists only in `tests/graph/test_context_bus.py`). Decide: should the NL compiler be stateful across the session via a shared FLUX bus? |
| `flux.surreal_flux` | `SurrealFlux` | seam yes, but `__init__(surreal_client)` **requires** a live client (no graceful no-backend ctor). | **architecture-decision** | Decide whether NL-compilation should hit SurrealDB vector search live → needs a backend-client wiring decision. |
| `eval.pipeline` | `EvalPipeline` / `RalphLoop` | no | **architecture-decision** | eval subsystem has no driver. Decision: what triggers an eval run, and where do results land? |
| `eval.universe_evaluator` | `UniverseEvaluator` | no | **architecture-decision** | RL-env evaluation harness with no caller. Decision: scheduled? on-PR? CLI? |
| `eval.huggingface_export` (`huggingface_export.py`) | `HuggingFaceExporter` | no | **architecture-decision** | Exports EVO research data. Decision: export target + cadence (a publishing surface). |
| `vanguard.attribution` | `AttributionEngine` | no | **architecture-decision** | License/attribution compliance with no ingestion point. Decision: when/where is attribution computed? |
| `vanguard.connectors` | `VanguardScoutReport` | no | **architecture-decision** | Multi-source scout with no consumer. Decision: what consumes scout reports (a feed? the research loop?). |
| `environments.auto_generator` | `AutoEnvGenerator` | no | **architecture-decision** | Auto env-generation with no trigger. Decision: what asks for a new env, and when? |
| `knowledge_graph.graphrag_engine` | `GraphRAGEngine` | no | **architecture-decision** | vector+graph+temporal recall that **overlaps** existing vault-recall / SemanticCache L3. Decision: replace, augment, or retire current recall? |
| `observability.cost_dashboard` (item 140) | — | no | **architecture-decision** | Reads real spend; needs a **surface** decision (CLI? API route? Genesis tab?). |
| `governance.concierge` (item 142) | `ConciergeAgent` | no | **architecture-decision** | Real routing component; needs a **routing-architecture** decision (where in the session path it plugs in). |
| `platform.agnostic_integrations` | `IDEIntegrationAdapter` | no | **dormant-by-design** | Activated by an IDE/host environment, not by in-repo code. Standby adapter. |
| `world_model.surprise_explorer` (item 141) | `SurpriseExplorer` | no | **dormant-by-design** | Needs a trained JEPA + an exploration loop; the surprise signal is also the *wrong KIND* for the routing consumer (item-141 lesson). Dormant until the world-model training path runs. |
| `inference.lynx_gate` (item 139) | `EscalationProbe` | n/a | **done-wired** | Already wired into `extend_claude` (escalation_probe param). Listed for completeness. |

## Batched recommendation for the human

- **1 row the loop can clear without you** (`flux.cache_flux`): one additive wire of
  `CacheFlux(SemanticCache.get_instance())` into the existing live NL-compile seam,
  behind a discriminating test that asserts **real** SemanticCache neighbors surface
  into the spec (not a test-seeded precondition).
  *Two corrections from verification: (1) my pre-draft thought there were more mechanical
  wins — tracing showed `FluxAggregator` is never constructed-with-providers in prod, so
  the rest have no live data flow; (2) `flux.history_flux` looked mechanical but its write
  path (`record_history`) only runs on a different, never-populated aggregator, so via the
  vibe seam it is always empty — its test would be tautological. It is therefore an
  architecture (shared-context-bus) decision, not a mechanical wire.*
- **10 architecture decisions, naturally grouped into 5 subsystems** — decide per group,
  not per module:
  1. **flux context bus** — `history_flux` (share one aggregator across graph-engine
     writes + vibe reads → stateful compiler?) and `surreal_flux` (does NL-compile hit
     SurrealDB live?)
  2. **eval subsystem** — `pipeline`, `universe_evaluator`, `huggingface_export`
     (one driver/cadence decision covers all three)
  3. **vanguard subsystem** — `attribution`, `connectors` (one ingestion-consumer decision)
  4. **standalone surfaces** — `auto_generator` (env-gen trigger), `graphrag_engine`
     (recall overlap), `cost_dashboard` (surface), `concierge` (routing seam)
- **2 dormant-by-design** (`agnostic_integrations`, `surprise_explorer`): leave parked;
  they activate on an external host / a trained model, not on missing code. No action.

## Invariant honored

Non-destructive: nothing is recommended for deletion. Every architecture-decision row is
a **wiring TODO awaiting a consumer decision**, per the Wire-at-Creation principle
(Learning 227) and the non-destructive-wiring policy.
