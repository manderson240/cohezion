---
title: "Night Council Directive: Validate, Don't Plan"
date: 2026-03-05
tags: [mission, multi-agent, flume, portfolio, directive]
aliases: ["night council validation directive", "validate don't plan"]
aspect: doer
neural:
  activation: 0.440
  stage: growing
  cluster: missions
---

# Night Council Directive: Validate, Don't Plan

> [!warning] Problem
> The 2026-03-04 night session produced excellent planning artifacts but zero validated outputs and 35 dead wikilinks. The council is a capable planning system that needs to be redirected toward execution.

## Directive

> [!tip] Primary Mission
> Run one FLUME validation diagnostic end to end. Not plan it. Not document plans to do it. **Run it, capture the output, and write the result as a vault experiment note.**

Specifically: the KL collapse diagnostic from [[2026-03-05-flume-kl-collapse-diagnostic]].

### Why This Diagnostic

- Requires no financial commitments
- Requires no HF_TOKEN or VRAM unknowns
- Requires no human approval
- Requires running diagnostics on existing FLUME code and recording what the numbers say

> [!success] Secondary Mission (If KL Diagnostic Completes)
> Write the result as a formal experiment note in `experiments/2026-03-XX-flume-kl-validation.md` with actual numbers, not narrative.

## Context: Why This Directive Change Matters

The constraint discipline in the last session was correct — deferring destructive operations and financial commitments while Mike was asleep shows well-calibrated authority scoping. But that same discipline should be applied to planning:

> [!quote] Key Insight
> The difference between "we have a plan to validate FLUME" and "we ran the diagnostic and KL is healthy / KL has collapsed" is the difference between a planning system and a research system.

The council should not generate plans when it could generate validated results instead.

## Success Criteria

- [ ] KL loss trajectory plotted across epochs
- [ ] Reconstruction fidelity measured on 50 trajectories
- [ ] Results recorded as experiment note with actual numbers
- [ ] Zero new planning-only artifacts created

## Related

- [[multi-agent-systems]] — council architecture
- [[2026-03-04-anthropic-portfolio-night-session]] — previous session that triggered this directive
- [[FLUME-Architecture]] — the system under validation
- [[compound-engineering]] — compounding requires execution, not just planning
- [[ai-safety]] — authority scoping and constraint discipline
- [[2026-03-05-flume-kl-collapse-diagnostic]] — the experiment this directive points to
