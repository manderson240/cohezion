---
title: "Separate Cohezion A (Empirical Platform) from Cohezion B (Cosmological Framing)"
date: 2026-03-05
status: accepted
tags: [decision, anthropic, portfolio, compound-engineering, communication]
aliases: ["two Cohezions decision", "Cohezion A vs B", "portfolio framing decision"]
aspect: thinker
neural:
  activation: 0.474
  stage: growing
  cluster: decisions
---

# Separate Cohezion A (Empirical Platform) from Cohezion B (Cosmological Framing)

> [!success] Status: ACCEPTED — README rewritten 2026-03-05
> The plain-language README has been written and replaces the cosmological framing. All external-facing materials now pass the cold-reader test.

## Context

Reading across the full vault revealed a split between two distinct versions of Cohezion:

**Cohezion A** — the empirically-grounded platform found in `experiments/`, `lessons/`, `concepts/compound-engineering.md`, session notes:
- 45 hard-won lessons from actual failures
- VAE training run with real numbers (KL divergence 4.2 nats, 53% reconstruction improvement)
- N-body simulation producing 5.5M real trajectories overnight
- Technical debt explicitly tracked and named

**Cohezion B** — the cosmological framing found in the prior `missions/anthropic-portfolio/README.md`:
- "The Awareness of Nothing precipitates the Tensor Beam across the 4 Fabrics"
- HIHO_STABILITY_PRIME, REALITY_PRECIPITATION_PRIME, void-to-swarm precipitation
- References to Bob Greenyer's FTM, Wilbert Smith's Tensor Beam, Ken Shoulders' EVO
- "Source Code for Reality" framing
- Adversarial review concluding "Submit immediately. This is unignorable."

The adversarial review verified internal consistency but did not ask the prior question: *does this framing make sense to an external reader who doesn't share the conceptual vocabulary?*

### The Vocabulary Compound Trap

The vault's internal language evolved in a closed loop. Each session built on the vocabulary of the prior session. What started as evocative shorthand became load-bearing terminology that cannot be understood without reading weeks of session history. This is a real risk of [[compound-engineering]]: the vocabulary compounds along with the knowledge, and eventually becomes a barrier rather than a bridge.

## Decision (Accepted)

1. **External presentation** — grounded, precise, free of private vocabulary. Every sentence must pass: *could a senior ML engineer at Anthropic understand this without having read any prior vault content?*
2. **Internal vocabulary** — keep cosmological framing if useful as a thinking tool. Never mix into submission-facing content.
3. **README rewritten from scratch** — completed 2026-03-05. See `missions/anthropic-portfolio/README.md`.

## What Was Done

- `missions/anthropic-portfolio/README.md` — fully rewritten in plain technical language. Opens with the problem being solved, not cosmological vocabulary. Surfaces real experimental numbers (4.2 nats KL, 53% reconstruction improvement, 424x VLIW speedup). Includes explicit "What's Not Done Yet" section for honesty.
- `concepts/FLUME-Architecture.md` — rewritten to surface the actual experimental results table and anti-patterns clearly
- `concepts/cohezion-platform-overview.md` — new Platform Spine note written for cold-session orientation
- `concepts/agentic-system-failure-taxonomy.md` — 45 lessons organized into 6 failure categories as a publishable taxonomy

## Consequences Going Forward

- Night council asset generation should be directed at Cohezion A framing only
- All new portfolio content must pass the cold-reader test before being considered portfolio-ready
- Internal vocabulary (HIHO, precipitation, FTM) remains available for internal sessions

## Related

- [[compound-engineering]] — the methodology whose vocabulary became a barrier
- [[adversarial-review]] — review methodology now needs to include cold-reader test
- [[FLUME-Architecture]] — rewritten to surface real numbers
- [[cohezion-platform-overview]] — new Platform Spine note
- [[agentic-system-failure-taxonomy]] — lessons corpus promoted to taxonomy
- [[ai-safety]] — constitutional constraint discipline is the Anthropic-relevant story
