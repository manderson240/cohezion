---
title: "The 'consider [link]' research-filter taxonomy — verify, map, name the caveat, classify"
date: 2026-06-06
tags: [research-loop, non-fabrication, measurement-integrity, retro, verified]
verified: true
---

# Retro — how to triage a user-shared link without fabricating work

Refined across 12 BLEEDING_EDGE_FEED rounds (verified 2026-06-06). The discipline that keeps the
self-improvement loop honest: a shared paper/repo/article is NOT automatically a backlog item.

## The four steps (every link)
1. **VERIFY first.** WebFetch the source (HF id via `model_info`, PyPI via JSON API, arXiv via the
   abstract). Unverifiable → omit, never cite from memory. No model artifact (methodology/dataset
   paper) → say so (DRIFT, round 11).
2. **MAP to a REAL cohezion seam.** Name the exact module the idea touches. If you can't, it doesn't
   land. (DRIFT → `tape_logger`/`journey_tracker`/`retrospection_validator`; DSPy → `rho_selector`/
   `skill_refiner`; turbovec → `knowledge_bridge` neuron recall.)
3. **NAME the caveat that would bite.** The off-philosophy or regression-risk that gates adoption
   (cloud judge vs local-$0; quantization needs CA1 recalibration; a framework dep duplicates
   existing code). If there's no honest caveat, you haven't looked hard enough.
4. **CLASSIFY into one of FOUR outcomes** (this is the part that prevents fabrication):

| Outcome | When | Action |
|---|---|---|
| **Embrace** | verified + on-philosophy ($0/local) + GGUF/seam exists + additive | new backlog TODO (Gemma-QAT→50, PaddleOCR→54, turbovec→56) |
| **Decline-but-mine** | off-stack/off-philosophy product, but a transferable PRINCIPLE | mine the principle into a report-only instrument; NO product adoption (LangChain→48, BigSet→49, TaskMem→52) |
| **Overlaps-existing → validate** | cohezion ALREADY has the capability | do NOT fabricate a "new capability" item; queue a VALIDATION benchmark instead (DSPy already = RHO items 22/33/42 → item 70: DSPy-on-fleet vs RHO, not a framework swap) |
| **Map-to-needs-experiment** | verified + fleet-runnable but quality/serving unproven | report-only structural instrument with an INJECTED dependency; production quality = needs-experiment (DRIFT→69: claim-support audit with an injectable judge) |

## The two anti-fabrication rules (the heart of it)
- **Never invent a model/paper/capability to fill a slot.** Research-gated ids stay TODO until
  verified. A backlog item with no real seam is drift, not progress.
- **"We already have this" is a valid, common outcome.** When a shared tool overlaps an existing
  cohezion subsystem (DSPy↔RHO), the honest move is a *validation benchmark* ("is our hand-rolled
  loop competitive with the canonical framework, $0 on the fleet?"), NOT a duplicate-capability item
  or a silent framework swap (that's a human/architecture decision).

## Docs-only discipline
The research loop NEVER modifies `src/` — it appends to `BLEEDING_EDGE_FEED.md` (date-stamped,
classified) and, only on a real lever, a backlog TODO. Implementation is the BUILD loop's job later.

## This session's tally (user-shared links)
4 embraced · 4 declined-but-mined · 1 needs-experiment-instrument (DRIFT) · 1 overlaps-existing-validate
(DSPy). The filter manufactured ZERO fake items across 12 rounds — that is the success metric.
