---
title: 'Provenance over poetry: every UX claim traceable to a real file and running system'
date: '2026-02-27'
status: proposed
tags: [decision, ux, honesty, portfolio, alignment]
decision_reasoning:
  chosen_option: 'Hover provenance tags on every live data point; Soul layer status indicator; failures displayed with dignity; "link it with reality" as core design principle'
  rationale: 'Mike stated explicitly: "We just have to make sure we link it with reality." Every UI claim is only as strong as its provenance. The interface is only as trustworthy as its honesty about what is live vs. seeded.'
  confidence_score: 0.95
  alternatives_rejected:
  - 'Full poetic narrative without source attribution'
  - 'Hide Soul layer placeholder status'
  - 'Present 2048D claims without qualification'
aspect: thinker
neural:
  activation: 0.71
  stage: growing
  synapse_in: 6
  synapse_out: 6
---

## Context

During UX design party mode session, after significant discussion about the 2048D Soul layer and FLUME's scope, Mike said: "We just have to make sure we link it with reality."

This became the single most important design principle of the session. The party mode agents had been building toward increasingly dramatic claims about FLUME's capabilities. Mike's grounding note redirected everything toward honest, verifiable design.

Sally (UX Designer): "The interface is only as trustworthy as its provenance."
Victor (Innovation Strategist): "Beautiful architecture diagrams that don't run. Poetic metaphors that don't have a git blame. That's what kills AI portfolios."
Sophia (Storyteller): "The story that's actually true is better than the story we were building."

## Decision

**Provenance tags:** Every live data point in the Observatory gets a hover-accessible source tag. Format: Space Mono, 0.6rem, iron `#566573`. Examples:
- Coherence `0.512` → hover → `brane[7] via ws://localhost:8080/pulse`
- Particle color → hover → `novelty dimension, FLUME HIHOShader`
- Git trajectory node → hover → `commit a3f2b1, Session 47, FLUME z_dim=256`

**Soul layer status:** Small indicator showing what % of the 2048D pipeline is flowing real data vs. seeded with `[0.5] * 2048` placeholders. Named honestly. Not hidden.

**Failures displayed with dignity:** Red-bordered experiments in the Vault are never hidden. The count of logged failures is a feature, not a confession. "I have failed 89 experiments — and kept every one."

**The compound promise:** "Come back in 10 sessions." Not a claim about current state — a promise about trajectory. Honest. Confident. Verifiable over time.

## Chosen Option

Provenance-first rendering throughout.

## Decision Reasoning

### Why This Option?

For an Anthropic audience evaluating alignment and interpretability, the most powerful signal is a system that shows its work without being asked. The Vault as "auditable reasoning made navigable" is the interpretability argument made into a UX surface. Every decision logged is evidence the system reasoned transparently. Every failure displayed is evidence it doesn't hide failures.

Caravaggio (Presentation Master): "Provenance tags — not intrusive. Always available. The system wears its own source code lightly — accessible to the curious, invisible to the casual viewer."

### Confidence Level

Very high (0.95). This principle was explicitly stated by the user.

## Expected Outcomes

- Reviewers trust the interface because it's been honest about smaller things
- Soul layer status indicator demonstrates engineering maturity
- The provenance pattern becomes a signature of Cohezion's design voice
- Failures-as-assets supports the brand voice principle from the guidelines

## Related

- [[alignment]] — provenance-first rendering is an alignment practice: the system shows its work without being asked
- [[cohezion-brand-guidelines|COHEZION Brand Guidelines]] — the brand voice principles (failures-as-assets, technical honesty) this decision operationalizes
- [[2026-02-27-ux-reentry-narrative-system-speaks-first]] — the re-entry narrative uses provenance tags to source its claims from live system physics
- [[2026-02-27-ux-flume-as-foreground-three-lenses]] — FLUME lenses are the primary surface where provenance tags appear on live data points
- [[2026-02-27-ux-triune-navigation-observatory-vault-cockpit]] — provenance applies across all three cognitive modes (Observatory, Vault, Cockpit)
- [[honest-metrics-over-inflated-claims]] — provenance over poetry operationalizes the honest-metrics principle at the UX layer
