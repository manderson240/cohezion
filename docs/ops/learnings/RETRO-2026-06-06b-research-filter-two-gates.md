---
title: "Retro — the research filter's two gates; verified ≠ actionable"
date: 2026-06-06
tags: [retro, research-filter, non-fabrication, build-loop, wiring-sweep]
---

# Retro 2026-06-06b — the research filter's two gates

Covers build-loop items 59/60/61/62 (RHO margin, least-adopted, coverage-gap) + 83 (video tasks),
wiring ticks (learning.deep_research, reporting.nightly), and research rounds 16–24 (nine user-shared
links: 2 real levers banked, 7 declined/parked).

## The one durable lesson: TWO gates, and they are different questions

Across 9 research rounds the filter's decisions reduced to two independent gates. A finding must pass
BOTH to earn a backlog item; failing either → feed-only with a NAMED promotion condition.

**Gate 1 — is it fleet-runnable NOW? (for model/tool findings)**
A model can be VERIFIED (`model_info` real id, permissive-ish license, high quality) and STILL fail:
- Gemma-4 drafter (r16): real GGUF, but llama.cpp `Gemma4Assistant` support is unmerged (PR #23398).
- BLS-Mini-Code (r17): real model, but 0 GGUF + `cohere2_moe` unsupported by llama.cpp + no license.
- Higgs-Audio (r18): real, high-quality TTS, but non-commercial license + transformers-only (no GGUF).
- Supra-50M (r18): permissive + GGUF-able, but below useful quality / would regress the pinned NPU tier.
Each → feed-only with the exact condition that would promote it (PR merges / a GGUF appears / a license).
Banking a not-yet-runnable model is the fabrication-adjacent error the backlog rule ("VERIFIED +
fleet-runnable + additive") exists to prevent.

**Gate 2 — is there a CONCRETE FALSIFIABLE INSTRUMENT on a REAL seam? (for idea/paper findings)**
This is the line between mine-principle and mere resonance:
- FAILED → declined: sophrosyne (r19), X-Stream (r20), model-selection (r22), floppy-disk (r23),
  Dify (r24). Each resonated with cohezion's ethos but offered no new measurable on a named seam —
  and several (model-selection, Dify) described things cohezion ALREADY does, better.
- PASSED → item: time-perception/Eagleman (r21) → item 95 `novelty_density`, because "subjective time
  ∝ novelty density" is a measurable that composes the EXISTING geometric-correspondence encoder.
The test: *can I name the function, its falsifiable check, and the existing seam it composes?* If not,
it is resonance — log it, add nothing. Manufacturing a metric for a resonant idea is the false
precision `metacognitive-calibration.md` forbids ("a number is a smell, not a verdict").

## Corollaries reused this arc
- **License is a first-class fleet constraint, encoded as a TEST not a comment** (Higgs item 93: a
  discriminating test asserts the product-surface selector never returns the NC model). A comment
  rots; a red test won't. NC-license calls are HUMAN decisions → feed, never autonomous backlog.
- **"Declare capability without fabricating it"**: adding `VIDEO_GEN`/`VIDEO_UNDERSTAND` Tasks with
  zero ModelEntries (`for_task → []`) is honest "capability declared, not yet served" — it opens the
  wiring point (items 87/96) without inventing a model. 4-line additive change because the substrate
  (the no-model-yet Task precedent) was ready.
- **Wiring: Class-B tests-only is a wiring TODO, not dead code.** `NightlyReporter` (reporting) and the
  learning orphans were re-exported (`X as X`) to make latent intent reachable, never deleted.

## Persisted
- Feed (`docs/research/BLEEDING_EDGE_FEED.md`) rounds 16–24 carry per-finding promotion conditions.
- Backlog items 92 (ExpInternalization-grounded) + 95 (Eagleman-grounded) banked; 96 (video-understand
  specialist) parked research-gated. Higgs item 93 guardrailed.
- Filter tally now 6 embraced/refined vs 6 declined + 5 overlaps + 3 not-runnable — a ~1:1 embrace:decline
  ratio that IS the health signal (a filter that embraces everything isn't filtering).

## What to avoid
- Don't bank a verified-but-not-runnable model "to not lose it" — the feed with a promotion condition
  is the correct park.
- Don't manufacture an instrument for a resonant idea — if you can't name the function + check + seam,
  it's resonance.
