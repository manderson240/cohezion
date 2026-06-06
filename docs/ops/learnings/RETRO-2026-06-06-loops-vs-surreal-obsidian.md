---
title: "The self-improvement loops do NOT leverage SurrealDB-8001 / Obsidian — the neuron write path is dormant"
date: 2026-06-06
tags: [wiring, neurogenesis, surrealdb, observability, retro, verified]
verified: true
---

# Retro — loops vs SurrealDB/Obsidian (answering "are we leveraging them in our loops?")

## Finding (verified 2026-06-06, evidence-based)
The three loops (build / wiring-sweep / research) persist to **repo markdown + git**, NOT to
SurrealDB-on-8001 or Obsidian. Concretely:
- **SurrealDB 8001 is UP and used by the broader system**, NOT by the loops: `vault.neurons`
  has **1777 rows, all `country=null`** (legacy, pre-date the country schema); `main.learnings`
  has 10 rows written by the per-session **retro rule** (not the build loop).
- **The neurogenesis write path (items 15/16/24/29/37) is built + tested but UNWIRED.** The deposit
  helpers (`deposit_inference/skill/cerebellum_neuron` → `deposit_neuron_record`, target
  `surreal-db: vault`, country-allowlisted, fail-soft, pytest no-op) exist and pass against
  *injected* stores. But the ONLY non-test caller is `compound/fleet_health_specialist.py` (item 36),
  and **nothing in production runs `fleet_health_specialist`** (no driver/cron/api/`__main__`). So 0
  country-tagged neurons reach the live graph.
- The audit/telemetry instruments (`loop_telemetry`, `specialist_coverage_report`,
  `complexity_outliers`, `skill_adoption_report`) are libraries — invokable, not invoked on any schedule.
- Obsidian `~/vaults/cohezion-vault` is active (154 md since 06-05) but **no loop artifacts** are
  mirrored there as notes; that churn is the retro/learn/MEMORY rules, not the loops.

## How to verify (re-runnable)
```bash
curl -s http://localhost:8001/sql -H "surreal-ns: cohezion" -H "surreal-db: vault" \
  -H "Content-Type: text/plain" -u root:root --data "SELECT country, count() FROM neurons GROUP BY country;"
# → all country=null today. When the write path is live, country='inference'/'skill'/'cerebellum' appear.
grep -rln "FleetHealthSpecialist\|deposit_.*_neuron" src/ scripts/ | grep -v test
# → only fleet_health_specialist.py itself; no production runner.
```

## The gap → next falsifiable step (additive, not yet a backlog item unless user opts in)
A small production driver (or a `CompoundExecutor` step) that runs `fleet_health_specialist` / the
deposit sinks on a cadence, **falsifiable check: a rewarded routing decision round-trips into the live
`vault.neurons` table WITH its `country` tag** (currently provable only against injected stores).
Behavior-changing (writes the real graph) → gate it behind that check.

## Reusable methodology already persisted elsewhere (don't re-derive)
- **String-ref ≠ static edge / lazy-but-literal IS a static edge** — `docs/audits/WIRING_SWEEP_LEDGER.md`
  (knowledge_graph + mycelium sections). The per-tick orphan grep must require a leading `from`/`import`
  token (a quoted dotted path in `canonical_modules`/registry keys/`importlib` args false-positives), and
  a deferred in-function literal import still counts.
- Skill extraction via `/learn` is blocked this session (`.claude/skills/` + `~/.claude/` read-only);
  durable learnings land in `docs/` instead.
