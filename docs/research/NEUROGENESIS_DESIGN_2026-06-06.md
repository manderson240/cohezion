---
title: "Neurogenesis — making 'local inference forms new neurons' literally true"
created: 2026-06-06
owner: "/loop self-improvement (thread C)"
status: design-note (grounding + falsifiable backlog items 14-16; NO code yet)
directive: "local inference across the full local silicon neural net should be forming new neurons"
policy: "non-destructive — every track WIRES existing subsystems; none builds a new graph."
---

# Neurogenesis design note

## The directive, made precise

> "Local inference across the full local silicon neural net should be forming new neurons."

This is **aspirational today, not current.** Before proposing how to satisfy it, this note
grounds *every* "neuron"-like growth surface in the codebase against what actually exists,
so we wire reality rather than build fiction (anti-drift; Wire-at-Creation).

## The four neuron graphs (grounded against the code)

| Substrate | Grows today? | Grows FROM | A "new neuron" would be | Evidence |
|---|---|---|---|---|
| **Knowledge graph** `neurons`/`synapses` | ✅ **yes** (5,119 synapses) | Learnings / vault notes | a promoted Learning → addressable `country='cerebellum'` node w/ embedding | `governance/knowledge_bridge.py:118` `CREATE neuron SET … country='cerebellum'`; `hookify/vault_writer.py:426` `create_rule_neuron_in_graph`; vault-keeper populates from Obsidian |
| **Fleet** `FleetRegistry.models` | ❌ no (static dict) | hand edits / loop ticks | a recruited `ModelEntry` specialist for a task class | `inference/registry.py:434` `models: dict = _build_default_registry()` |
| **Bioelectric net** | ❌ no (fixed lattice) | — | adding a cell to an `n_cells` lattice | `physics/bioelectric_model.py:74` `n_cells: int = 16` — fixed; conductance dynamics only |
| **Skills / KV** | ⚠️ partial (promotion exists) | usage + value gate | a distilled skill+KV that survived the gate | `compound/distillation_pipeline.py:run_distillation`; recursive_trace value gate; SkillMutationQueue bi-temporal refund |

**Key honest finding:** the one graph that *does* grow (`neurons`) grows from **knowledge**,
never from **inference**. The directive asks for the missing edge: inference → neuron.

## The unifying principle

> **A neuron forms when a transient pattern that proves its value is promoted to a
> persistent, addressable node.**

Map the directive onto this:

```
 inference runs ──► transient pattern ──► value gate ──► persistent addressable node
 (NPU/iGPU/CPU)     (routing_log.jsonl,      (reward /     (neurons table, embedding-
                     shipped 2026-06-05)      outcome)      keyed, queryable)
```

Three of the four boxes already exist. The routing-decision corpus (item 2, shipped
yesterday) is the **first sensory organ** that captures the transient pattern. What's
missing is the promotion edge from a *rewarded inference path* to a *persistent neuron*.

## The three tracks (→ backlog items 14-16)

### Item 14 · Hebbian fleet recruitment (the "fire together, specialize" neuron)
When the routing corpus shows a `task_class` **chronically falls back** (`fell_back=True`)
with poor outcomes, propose a **new `ModelEntry` specialist** for it. Hebbian: the path
used-and-rewarded gets reinforced into a dedicated unit. **Human-gated** — proposes, does
not auto-register (a new specialist touches the fleet; that stays permission-gated).
*Falsifiable:* a synthetic fallback-heavy corpus yields a concrete new-specialist proposal;
a healthy corpus yields none. *Gating:* needs-experiment / report-only.

### Item 15 · Inference → neuron deposition (THE cheap, real coupling — recommended first)
A **rewarded** inference path deposits a neuron into the **existing** `neurons` table —
`CREATE neuron SET country='inference', name=<task_class>, content=<model+lane>,
embedding=<prompt-embedding>, reward=<outcome>` — reusing `KnowledgeBridge`'s exact write
path. This makes "local inference forms new neurons" **literally true** and is purely
*wiring two existing subsystems* (routing_log → KnowledgeBridge), zero new graph.
Over time, dense `country='inference'` regions = learned routing competence; the same
embedding store the knowledge lives in now holds inference memory too.
*Falsifiable:* a logged successful routing decision round-trips into a queryable neuron;
pytest writes nothing to the real graph (reuse the routing_log pytest-skip guard).
*Gating:* additive. **Lowest-risk, highest-leverage — recommended as the next additive build.**

### Item 16 · Skill/KV neurons via the value gate
Formalize "**a new neuron = a distilled skill+KV that survived the value gate**." The
nightly distillation pipeline promotes survivors into addressable skill-neurons (knowledge
graph, `country='skill'`). Closes the loop the other way: a skill the fleet *uses* and that
*passes* the gate becomes a persistent unit.
*Falsifiable:* a skill that fails the gate deposits no neuron; one that passes deposits
exactly one. *Gating:* needs-experiment.

## What this is NOT

- **Not** growing the bioelectric lattice (fixed `n_cells`; that's a physics sim, not a
  store). If lattice growth is ever wanted it's a separate, larger design.
- **Not** auto-registering fleet specialists without a human (item 14 proposes only).
- **Not** a new neuron graph — every track writes into structures that already exist.

## Recommended sequence

1. **Item 15 first** (additive, cheap, makes the directive literally true).
2. Then **item 14** (recruitment proposals from the now-richer corpus).
3. Then **item 16** (skill-neuron promotion) once 15's deposition pattern is proven.

Items 14-16 are appended to `docs/IMPROVEMENT_BACKLOG.md`. The build loop implements them
one per tick, TDD + falsifiable, non-destructively.
