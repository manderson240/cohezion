---
adr_number: 005
title: FLUME 256-Dimensional Latent Space — System-Wide Thought-Vector Invariant
date: 2026-04-23
status: ACCEPTED
deciders: cohezion-project
consulted: [FLUME team, semantic cache, journey tracker, dashboard team]
informed: [all components encoding through FLUME, downstream similarity-search consumers]
authored_by: synthetic-sniffing-panda Wave Ω10 retroactive ADR
---

# ADR-005: FLUME 256-Dimensional Latent Space — System-Wide Thought-Vector Invariant

## Status

ACCEPTED, 2026-04-23. This ADR is RETROACTIVE — no prior explicit decision document exists; the framing is reconstructed from the FLUME manuscript (`research/manuscripts/2026-04-23-flume-vae-compositional-latent.md`), the `ThoughtVector` Pydantic validator (`src/cohezion/flume/vae.py:41-57`), and the FLUME-First and Wire-at-Creation principles in CLAUDE.md.

## Context

Cohezion encodes agent context — skill prompts, prior trajectories, completed-task artefacts — into a continuous latent space rather than carrying it as flat text through the prompt. The architectural reason is in ADR-001 and ADR-004: a latent surface is composable in ways that text concatenation is not (linear interpolation, similarity search, latent algebra), and it is bounded in size. Once the decision to use a VAE-style latent has been made, the *width* of the latent becomes a load-bearing parameter: every component that encodes through FLUME must agree on the dimensionality, every similarity index must be sized for it, every checkpoint and storage allocation depends on it.

Three forces pull in different directions on the latent width. (1) Posterior-collapse risk and discriminability across distinct agent contexts argue for *more* dimensions — a 64-D latent would compress so aggressively that distinguishable contexts could be projected to indistinguishable points. (2) Geometric coherence and storage cost argue for *fewer* dimensions — a 1024-D latent would inflate similarity-search cost, dilute the meaningfulness of cosine similarity, and consume disproportionate memory for the latent population. (3) Hardware constraints (Strix Halo: 128 GiB unified memory, no datacenter GPU) cap the practical training and inference budgets.

The constraint set: (a) the latent must be compact enough to train and serve on Strix Halo with the executor pipeline running concurrently, (b) the dimensionality must be a *system-wide* invariant — multiple components depend on it and the value must be enforced rather than negotiated per-call, (c) the latent must support similarity search at agent-query latency (<100 ms target for `SemanticCache` L2 lookups), and (d) the value must be defensible against the standard alternatives (512, 768, sentence-BERT 384/768, no compression).

## Decision

We commit to a **256-dimensional FLUME latent space** as a system-wide invariant. The dimensionality is enforced by a Pydantic validator (`ThoughtVector` in `src/cohezion/flume/vae.py:41-57`) that rejects any tensor whose shape is not `(256,)`. The FLUME architecture is a 2-layer / 4-head transformer encoder + decoder with 256-D embeddings, 512-D feedforward, vocab 32,000, max sequence length 512 — trained as a standard β-VAE with KL weight 0.01 (updated from 0.1 — autoresearch 2026-05-15 confirmed β≥0.1 causes posterior collapse). Six HTTP endpoints (`/flume/encode`, `/flume/decode`, `/flume/train`, `/flume/status`, `/flume/interpolate`, `/flume/latent-space`) expose the model. The 256-D figure also matches the embedding dimension elsewhere in cohezion, so no projection layer is needed when bridging FLUME latents into the semantic cache, the journey tracker, or the dashboard.

## Rationale

The 256-D choice is a *deliberate compromise* between the three forces above (FLUME manuscript §3.1). At 256 dimensions the latent is wide enough that posterior collapse has not been observed in qualitative training, and distinct agent contexts encode to discriminable cosine-similarity points. It is narrow enough that one million latents fit in 1 GiB, well within the Strix Halo budget. It matches the embedding dimension elsewhere in cohezion, so FLUME outputs interoperate with the semantic cache and journey tracker without a projection layer.

Most importantly, 256 is enforced as an *invariant* rather than a default. The `ThoughtVector` Pydantic validator rejects any tensor with shape ≠ `(256,)` at construction, so a downstream component that produces a 768-D vector fails loudly rather than corrupting the latent population. The invariant is the architectural property; 256 is the parameter chosen to satisfy it. Changing to 384 or 512 would be mechanically expensive (re-train, re-index) but architecturally simple — change one constant. Switching to a *non-invariant* policy (different widths per context) would require redesigning every bridge between FLUME and its consumers.

The choice of a VAE over a transformer encoder of the same width is covered by FLUME manuscript §6 and is out of scope here; the short answer is that the VAE's regularised latent supports interpolation and latent algebra essential to ADR-001's compounding loop, which a deterministic encoder does not.

## Alternatives considered

### Option A: 512-D latent
- Pros: More room for distinct contexts; closer to BERT-base hidden width.
- Cons: 2× similarity-search and storage cost; concentration-of-measure makes cosine less discriminating.
- Why rejected: Discriminability gain is empirically marginal at the cohezion training corpus; cost is real.

### Option B: 768-D latent matching transformer hidden state
- Pros: Direct interoperability with sentence-BERT-class embeddings.
- Cons: 3× cost; requires a projection layer to bridge cohezion's 256-D embedding code paths; Strix Halo memory pressure.
- Why rejected: Off-the-shelf 768-D interoperability is not a primary requirement.

### Option C: Dense embedding from sentence-BERT (no VAE training)
- Pros: No training cost; well-characterised quality.
- Cons: No latent-algebra support — interpolation produces meaningless points; not adaptive to cohezion's trajectory distribution.
- Why rejected: Defeats the compositional thesis. Excellent for similarity, useless for interpolation.

### Option D: No compression (carry full text)
- Pros: Lossless.
- Cons: Unbounded prompt growth; no similarity surface; defeats the latent-substrate architecture.
- Why rejected: Empirically dominated.

### Option E (chosen): 256-D VAE latent enforced as system-wide invariant
- Pros: Compact; matches existing embedding width (no projection); VAE supports interpolation and latent algebra; Pydantic-enforced invariant prevents silent shape drift.
- Cons: Re-training cost on any future width change; 256-D may be too narrow for the most diverse trajectories (FLUME manuscript §6 — hierarchical FLUME is the future-work mitigation).
- Why chosen: Best compromise across the three forces and the Strix Halo constraint, with enforcement at the boundary.

## Consequences

### Positive
- Storage and search costs are predictable: 256 floats × 4 bytes = 1 KiB per latent; 1 million latents fits in 1 GiB.
- The invariant is enforced at the type boundary (`ThoughtVector`), so shape drift fails loudly.
- No projection layer is needed when bridging FLUME ↔ semantic cache ↔ journey tracker (they all use 256-D).
- 95% semantic cache hit rate (CLAUDE.md) is achievable in part because the latent is wide enough to discriminate cohezion-specific agent contexts.

### Negative
- The latent width may be too narrow for the full diversity of trajectories the executor accumulates over time (FLUME manuscript §6).
- Changing the width is expensive (re-train, re-index, re-checkpoint); the invariant means any change cascades.
- The hash-based fallback in `FlumeVAEEncoder` (used when no checkpoint is loaded) preserves dimensionality but discards semantic structure — agents running before training has completed get a degraded latent.

### Neutral
- A future hierarchical FLUME (FLUME manuscript §7) would maintain 256-D at each level and use learned projections between levels, preserving the invariant.
- 256-D is the *latent* width; the embedding and feedforward widths inside the encoder/decoder (256, 512) are independent design parameters of the same value.

## Implementation

- Primary files:
  - `src/cohezion/flume/vae.py` (321 lines; `FlumeVAEConfig` at line 10; `ThoughtVector` validator at line 41; `FlumeVAE` model at line 60; encoder at line 110; reparameterise at line 104).
  - `src/cohezion/flume/vae_encoder.py` (production wrapper with hash-based fallback).
  - `src/cohezion/flume/training.py`, `train_vae.py` (training utilities).
  - `src/cohezion/flume/dataset.py` (synthetic + trajectory-derived datasets).
  - `src/cohezion/api/routes/flume.py` and `src/cohezion/api/routes/flume_inline.py` (HTTP endpoints).
  - `src/cohezion/cache/semantic_cache.py` (L2 cosine layer over 256-D latents).
  - `src/cohezion/compound/journey_tracker.py` (12-D projection from 256-D FLUME latent).
- Test files: `tests/flume/test_vae.py`, `tests/flume/test_vae_encoder.py`, `tests/flume/test_evaluate_vae.py` (27 test files in `tests/flume/`).
- Documentation: FLUME manuscript (`research/manuscripts/2026-04-23-flume-vae-compositional-latent.md`); CLAUDE.md "FLUME-First" coding standard; this ADR.

## Verification

- Static check: `grep -n "z_dim: int = 256\|shape != (256,)" src/cohezion/flume/vae.py` — both the default config (line 24) and the validator (line 55) must contain the literal 256.
- Runtime check: `curl -X POST http://localhost:8080/flume/encode -d '{"text":"hello"}'` should return a `mu` of length 256 and `log_var` of length 256.
- Test: `uv run pytest tests/flume/test_vae.py -q` — confirms encode/decode/reparameterise shapes; the `ThoughtVector` test confirms the invariant rejects non-256-D tensors with `ValueError`.

## Reversal cost

**MEDIUM.** The width is enforced at one place (`ThoughtVector`) and defined at one place (`FlumeVAEConfig`); changing the constant is a one-line edit. The cost cascades: re-train the model, re-encode every stored latent, rebuild the semantic cache index, and invalidate every on-disk checkpoint. Estimated effort: 1-2 person-weeks of code plus 1-2 weeks of training and re-indexing, with an operational degradation window. Architecturally simple, operationally non-trivial.

## Related ADRs

- Depends on: ADR-001 (the eleven-step loop's step 1 retrieves through FLUME; step 11 encodes the journey through FLUME); ADR-004 (vault content is encoded through FLUME for similarity search).
- Informs: future ADR on hierarchical FLUME if the 256-D bottleneck becomes the limiting factor; future ADR on shared encoder weights between FLUME and the JEPA world model.
- Tension with: none currently identified; downstream consumers all depend on the 256-D invariant cooperatively.

## References

- `research/manuscripts/2026-04-23-flume-vae-compositional-latent.md` (full architecture rationale; §3.1 covers the 256-D choice; §6 covers the limitation).
- CLAUDE.md, "FLUME-First" coding standard; "Wire-at-Creation" principle; FLUME row in the Architecture-at-a-Glance table.
- Kingma, D. P., & Welling, M. (2013). Auto-encoding variational Bayes. arXiv:1312.6114.
- Higgins, I. et al. (2017). β-VAE: Learning basic visual concepts with a constrained variational framework. ICLR. (KL-weighting precedent.)
- Bowman, S. R. et al. (2016). Generating sentences from a continuous space. CoNLL. arXiv:1511.06349. (Posterior-collapse risk.)
- Hardware: `HARDWARE_PROFILE_PRIME.md` (Strix Halo memory budget).
