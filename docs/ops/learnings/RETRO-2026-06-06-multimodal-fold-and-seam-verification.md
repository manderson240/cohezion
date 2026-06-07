---
title: "Retro — folding a large feature request into an autonomous loop; seam-verification discipline"
date: 2026-06-06
tags: [retro, build-loop, wiring-sweep, non-fabrication, research-filter, multimodal]
---

# Retro 2026-06-06 — multimodal fold + seam verification

Covers a continuation session: L4 journey-spatial (user pushback), three build-loop ticks
(items 59/60 + scope-expansions 81/82), one wiring-sweep tick (learning.skill_acquisition),
and folding the user's multimodal-local-inference directive into the loop as Thread M (83–90).

## What worked (reuse)

1. **Verify every seam BEFORE writing backlog items.** The user asked for video/audio/image/
   multimodal local inference "as part of the loop." The disciplined move was NOT to write 8
   aspirational items — it was to `grep` the actual seams first (`inference/registry.py` Task enum,
   `fleet.py:_dispatch_one`, `audio/narrator.py::CosmoNarrator`, `experiential_learning_hook.py`,
   `triune_orchestrator.py`) and classify each capability by what's *actually* there:
   **loop-buildable-additive** (Tasks/coverage/registration/instrument/envelope) vs
   **human-infra-gated** (sd.cpp Vulkan serving needs a lanes-up window) vs **research-gated**
   (video — NO verified model artifact exists; the slot stays TODO with no model named). This is
   the non-fabrication rule applied to *feature-folding*: a backlog slot with no verified artifact
   is honest "capability declared, not yet served," never an invented repo.

2. **Judge a research artifact's transferable PRINCIPLE separately from its modality/artifact.**
   OVO-S-Bench was first declined on modality (egocentric video) — correct for the *artifact* (no
   servable model) but it missed that the *structural* spatial-reasoning HIERARCHY (L1 position →
   L2 tracking → L3 simulation → L4 allocentric map) is modality-independent and maps onto
   cohezion's 12D/256D agentic-journey substrate. The L4 allocentric map was the genuine gap;
   building it (`compound/journey_spatial.py`) was the right mine-the-principle outcome. Lesson:
   an off-modality artifact can still carry an on-substrate idea — separate the two judgments.

3. **Same-leaf-name hazard is real and load-bearing in the wiring sweep.** `learning/shadow_scripter`
   is a DIFFERENT module from the referenced `mycelium/shadow_scripter`; a naive "is this name
   imported anywhere?" grep would have wrongly classified the learning one as wired. Always confirm
   the import target's *full dotted path*, not the leaf name, before classifying an orphan.

4. **Refactor toward the richer primitive, behind unchanged tests.** Both `gated_targets_from_ledger`
   (→ keys of the new reasons map) and `low_adoption_report` (→ shared `_counts_per_registered_skill`)
   were rewritten onto richer cores WITHOUT touching their existing tests — the green sibling suites
   (17 + 12) are the proof the refactor was behaviour-preserving. DRY without regression.

## What to avoid

- Don't write backlog items for capabilities whose seam you haven't grepped — aspirational rows are
  fabrication by another name.
- Don't let a serving/lanes-up/research gate masquerade as a TODO the loop can auto-clear; mark the
  gate explicitly (needs-experiment / research-gated) so the loop doesn't spin on it.

## Persisted

- Thread M added to `docs/IMPROVEMENT_BACKLOG.md` (items 83–90 + a Notes legend documenting the
  verified seams) — the durable scope the loop now owns.
- Wiring ledger updated (learning classified; deep_research queued next tick).
