---
title: "JourneyTracker and DegradationDetector as Research Contribution"
date: 2026-03-05
status: active
tags: [project, evaluation, anthropic, portfolio, agentic-ai]
aliases: ["JourneyTracker research framing", "agent evaluation methodology paper"]
aspect: doer
neural:
  activation: 0.459
  stage: growing
  cluster: projects
---

# JourneyTracker and DegradationDetector as Research Contribution

> [!abstract] Goal
> Write a 500-word research-style framing of JourneyTracker and DegradationDetector as a contribution to agent evaluation methodology. Transform engineering implementation notes into a statement legible to research evaluators.

## Overview

Evaluating whether an AI system is doing what you think it's doing is one of the hardest open problems in [[agentic-ai]] — and it's central to the Anthropic Universes work. JourneyTracker measures reasoning quality in trajectory space rather than action outcomes. DegradationDetector tracks when and how agent reasoning degrades over time.

> [!tip] Why This Matters
> These tools are direct, concrete answers to the agent evaluation problem. Right now this contribution is invisible because it's described in engineering terms, not research terms. A 500-word framing bridges that gap.

## Deliverable Structure

1. **Motivation** — Why action-outcome metrics are insufficient for evaluating agent reasoning quality
2. **Method** — What JourneyTracker and DegradationDetector measure and how
3. **Preliminary evidence** — What the metrics show on actual Cohezion trajectories
4. **Limitations** — What they don't measure, where they could be wrong

> [!warning] Research Maturity Signal
> The limitations section is the part that signals research maturity. Honestly stating what claims can and can't be made is exactly the epistemic honesty Anthropic evaluates for.

5. **Open questions** — What would need to be true for these to be rigorous

## What This Unlocks

- Core of the "evaluation methodology" section of the Anthropic application
- Forces clarity about what claims can and can't be made
- Demonstrates the difference between building tools and understanding what they measure

## Current Status

- [ ] Draft 500-word research framing
- [ ] Review against actual JourneyTracker implementation
- [ ] Extract preliminary evidence from existing trajectory data
- [ ] Write 2-paragraph version for application cover letter

## Related

- [[agent-journey-tracking]] — implementation details and session references
- [[compound-engineering]] — methodology context
- [[2026-03-03-claude-platform-skills-assessment]] — skills assessment context
- [[FLUME-Architecture]] — the trajectory system JourneyTracker evaluates
- [[concept-validation]] — validation methodology
- [[anomaly-detection]] — DegradationDetector uses anomaly detection principles
