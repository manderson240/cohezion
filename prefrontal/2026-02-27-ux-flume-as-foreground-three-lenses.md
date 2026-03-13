---
title: 'FLUME as foreground: three Observatory lenses over the 2048D→256D→12D pipeline'
date: '2026-02-27'
status: proposed
tags: [decision, ux, flume, observatory]
decision_reasoning:
  chosen_option: 'Three switchable FLUME lenses (Coherence Field / Git Trajectory / Skill Manifold) as primary Observatory UI, with persistent depth indicator showing the 2048D→256D→12D hierarchy'
  rationale: 'FLUME is the paradigm, not the decoration. The three-lens structure makes the same manifold legible from three angles. The 2048D Soul layer is the most distinctive technical claim and must be surfaced, not hidden.'
  confidence_score: 0.9
  alternatives_rejected:
  - 'FLUME as background hologram (current state)'
  - 'Separate apps for each lens (morphospace-loom is currently separate)'
  - 'Single lens with layer toggles (Earth Engine style)'
aspect: thinker
neural:
  activation: 0.71
  stage: growing
  synapse_in: 6
  synapse_out: 6
---

## Context

The current webapp treats FLUME's HIHOShader as a background hologram. The HIHOShader already encodes 4 live dimensions (awareness, stability, novelty, precipitation per the shader source) but nothing in the UI explains this. FLUME is Cohezion's most significant technical contribution:

- **2048D Semantic Hypervolume ("Soul")** — intent, meaning, reasoning; SurrealDB vector index with cosine similarity
- **256D FLUME VAE** — compressed latent space; FlumeEncoder z_dim=256
- **12D Observable State** — holographic projection; brane dimensions mapped to coherence/stability/entropy

FLUME encodes across three domains: system coherence, git commit sequences (git_encoder.py), and VLIW instruction alignment (vliw_latent_alignment.py).

Mike confirmed during session: "I think we even had 7048 or some other higher dimension" — actual current implementation is 2048D, but architecture may evolve. Interface should be dimensionality-agnostic at display layer (show ratio, not hardcoded numbers).

## Decision

Three switchable lenses within the Observatory viewport:

1. **Coherence Field** — live 12D manifold projection; particles colored green→purple by novelty, sharpened by stability (per HIHOShader); green spheres = stability wells
2. **Git Trajectory** — codebase path through 256D latent space as luminous commit trail; 73 nodes = 73 sessions; color-coded by session; curves reveal convergence vs. exploration
3. **Skill Manifold** — 74 PRIME skills as points in latent space; distance = semantic similarity; watch a skill move after compound cycle refinement; click any node to inspect full definition and evolution history

Persistent depth indicator: `"Viewing 12D projection of 2048D semantic state"` — Space Mono caption, iron #566573, bottom corner of Observatory. Honest about projection.

Soul layer status indicator: shows what percentage of the 2048D pipeline is flowing real data vs. seeded placeholders. Honest about completion state.

## Chosen Option

Three FLUME lenses, unified Observatory viewport.

## Decision Reasoning

### Why This Option?

FLUME is the paradigm. Every competitor visualizes outputs (loss curves, traces, metrics). Cohezion visualizes the shape of understanding itself. The three-lens structure makes that claim legible in three ways simultaneously. The git trajectory is a surface nobody has built before — codebase evolution as a geometric journey through meaning-space.

### Confidence Level

High (0.9). The lenses map cleanly to the three FLUME use cases already in the code.

## Expected Outcomes

- Reviewers understand FLUME's multi-domain capability within 3 lens switches
- The git trajectory becomes the "tell a friend" moment for the portfolio
- The depth indicator + Soul layer status establish technical honesty without documentation

## Related

- [[cohezion]] — FLUME VAE is a core Cohezion component; this decision makes it the primary UI surface
- [[cohezion-brand-guidelines|COHEZION Brand Guidelines]] — the visual identity system (Circuit Moss palette, Space Mono typography) this decision applies to the Observatory
- [[2026-02-27-ux-triune-navigation-observatory-vault-cockpit]] — the Observatory is one of three cognitive modes; FLUME lenses populate its viewport
- [[2026-02-27-ux-provenance-over-poetry]] — the provenance principle ensures every FLUME lens data point is traceable to a live system source
- [[2026-02-27-ux-reentry-narrative-system-speaks-first]] — the re-entry narrative opens the Observatory before lenses render, using FLUME shader values
- [[agent-journey-tracking]] — the Git Trajectory lens visualizes codebase paths through 256D latent space, built on journey tracking data
