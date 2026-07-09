# Two Mycelium Systems in Cohezion — Architecture Note

**Date:** 2026-06-03
**Author:** Cohezion compound engineering (harness-bash-unification followup)
**Related commits:** `82ed8e366` (ouroboros patterns), `bac56cb28` (mycelium auto-promote), `WS1` (executor wiring)

## Why two systems?

The Cohezion codebase has two parallel mycelium subsystems with overlapping
purpose but different architectures. The two-system split grew organically:

| Module | Driver | Use case | Wired to bus? |
|---|---|---|---|
| `cohezion.learning.mycelium_registry.MyceliumRegistry` | imperative (executor calls `ingest_entry` at end of every skill execution) | Per-skill execution journal; aggregates into `run_audit()` for skill synthesis | **No** |
| `cohezion.mycelium.registry.MyceliumRegistry` | reactive (subscribes to `PrecipitationBus`) | Cross-universe pattern clustering with 12D + fabric similarity; auto-promotes cross-universe clusters to Obsidian vault + SurrealDB | **Yes** (after WS1) |

Both registries are correct in their own right. The split exists because
they answer different questions:

- **Journal-based** answers: "did skill X succeed on task Y? synthesize a
  refinement." Per-skill, per-execution. Optimized for low-latency skill
  refiner feedback.

- **Bus-based** answers: "is there a pattern across N agents / N
  universes that we should capture as durable knowledge?" Cross-cutting,
  slower. Optimized for slow-moving emergent insight.

## What's wired where (post-WS1)

- **CompoundExecutor** still drives the journal-based registry (line 1247) —
  unchanged. Per-skill execution insight stays fast.
- **CompoundExecutor** *also* emits a `PrecipitationEvent(kind=WITNESS_MARK)`
  to the bus after a successful skill execution (new Step 10.55). The
  bus-based registry's subscriber clusters the event with others from
  the same universe. When 3+ events span 2+ universes, auto-promotion
  to vault+DB fires.
- **Cooldown**: single-universe clusters are NOT auto-promoted (avoids
  vault spam from any single agent). See `MyceliumRegistry._promote_pattern`
  for the guard.

## Why not unify?

A unified registry was considered. Rejected for now because:

1. The journal-based registry's `JournalEntry` schema is fundamentally
   different from the bus-based `PrecipitationEvent` schema. Unifying
   would require a translation layer that adds complexity without
   removing the journal's low-latency edge.
2. The bus has its own graph-of-thought topology (12D + fabric) that
   the journal does not. Forcing the bus to ingest journal entries
   would require fabricating 12D coordinates per entry — not
   meaningful.
3. The cross-universe cooldown in the bus is a different invariant
   than the per-skill refinement gate in the journal. They can co-exist.

## Future work

- If the journal-based registry's `run_audit()` ever needs to consider
  cross-universe patterns, it can call into `BusMyceliumRegistry` rather
  than re-implementing the clustering.
- If the bus-based registry's auto-promote cooldown is too aggressive
  (only fires on cross-universe), a future refinement could lower it
  to "cross-agent" (2+ agent_ids in the same universe).

## How to subscribe a third system

If you build a third mycelium-like system:

1. Decide which question it answers: per-skill (use the journal) or
   cross-universe (use the bus).
2. If bus-based, instantiate `BusMyceliumRegistry(bus=get_bus())` and
   call `subscribe()` once per process. The registry's
   `_promote_pattern` cooldown is per-cluster, so multiple subscribers
   are safe.
3. If journal-based, follow the `cohezion.learning.mycelium_registry`
   pattern: imperative `ingest_entry` after every execution.
4. Document here so the next agent doesn't repeat the mistake.
