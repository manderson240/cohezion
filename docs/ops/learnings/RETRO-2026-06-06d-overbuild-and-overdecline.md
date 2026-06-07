---
date: 2026-06-06
kind: retro
thread: [B, P, research-filter, calibration]
prompted_by: user
status: captured
related_items: [119, 120]
related_seams:
  - src/cohezion/inference/orchestrator.py:547  # run_batch
  - src/cohezion/inference/triune_orchestrator.py:32  # build_triune_orchestrator
  - src/cohezion/recursive_trace/core.py:46  # TraceMemory, Stage-2 deferred
related_feed: docs/research/BLEEDING_EDGE_FEED.md  # Round 23 (reclassified)
---

# Retro — over-build and over-decline are the same miscalibration

## What the user said (two sentences, one lesson)

1. "the real lesson is you need more competent local inference approaches."
2. "I still think there is a recursive Trace logic lesson to be learned from floppy disk."

On the surface these are unrelated — one about inference infra, one about a research
filter verdict. They are the **same failure**, run in opposite directions.

## The failure, named

| Direction | What I did | What was true | The tell |
|---|---|---|---|
| **Over-build** | Wrote a naive SEQUENTIAL urllib batch loop (`scripts/research/distill_tutorials.py`) | The concurrent multi-tier batcher already existed, harness-blessed: `orchestrator.py:547 run_batch` (`asyncio.gather`, 3.44× XDNA2, `max_concurrent` cap) | I built infra for a capability the platform already had — the CLAUDE.md anti-pattern "Never write infrastructure for products that exist" |
| **Over-decline** | Clean-declined the floppy-disk piece in research Round 23 ("storage-density maps to NO actionable lever") | The principle (storage-density EVOLUTION) maps to a real DEFERRED seam: `recursive_trace/core.py:46 TraceMemory` Stage-2 latent retrieval (`enabled=False`) | I rejected the *one wrong direction* (turbovec/KV-quant) then generalized to "no lever at all" |

Both are a **missing check against the existing surface before deciding**:
- over-build = "I'll make a batcher" without checking `run_batch` exists →
- over-decline = "this maps to nothing" without checking `TraceMemory`'s deferred Stage-2 exists.

The corrective is identical and cheap: **grep the seam before you commit to "absent" or
"insufficient."** I verified both seams in ~30s of `grep`/`sed` this turn — the same 30s
would have prevented both mistakes a week ago.

## Why over-decline is the more dangerous one

Over-build is loud — it leaves a redundant file the next audit flags. Over-decline is
*silent*: a clean-decline reads exactly like correct restraint. The research-filter
discipline I'd internalized ("don't fabricate a link") has a blind spot — it only guards
the over-ACCEPT failure (manufacturing a connection that isn't there). It said nothing
about the over-REJECT failure (refusing a connection that IS there). Same week, same
shape: the tutorial-distillation pass I logged as "0 levers from my filter" was *also*
over-decline (adjacent ≠ identical, only 71/431 seen) — the user caught that one too.

> The filter's failure mode is NOT only fabrication. "We already have X" and "this maps
> to nothing" need a **tool-verified bar**, not a prior. Adjacent ≠ identical cuts BOTH
> ways: it forbids forcing a false link AND forbids dismissing a true one.

## What changed (durable)

- **Item 119** (thread B): `run_batch_local` adapter delegating batches to
  `TieredOrchestrator.run_batch` — stops the bespoke sequential bypass; falsifiable
  (fake orchestrator must see ONE concurrent call, not N sequential).
- **Item 120** (thread P): `trace_compaction_ratio` — operationalizes the floppy
  density-evolution principle on the `TraceMemory` Stage-2 seam; report-only, the latent
  retrieval itself stays gated (no fabrication).
- **Feed Round 23 reclassified** DECLINE → declined-product/mined-principle, with the
  original error preserved and named (honest correction, not a retroactive rewrite).

## Reusable rule

Before declaring a capability **absent** ("we have nothing for this") or **insufficient**
("I need to build my own"), run the cheap existence check: `grep -rn` the obvious symbol,
read the one signature. The platform is large and sophisticated; my prior about what it
lacks is a guess, and a guess gets the same verification bar as a claim about what it has.
