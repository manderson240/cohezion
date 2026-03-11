---
title: 'Triune Navigation: Observatory / Vault / Cockpit mapped to Knower / Thinker / Doer'
date: '2026-02-27'
status: proposed
tags: [decision, ux, navigation, cohezion-method]
decision_reasoning:
  chosen_option: 'Three cognitive modes — Observatory (KNOWER), Vault (THINKER), Cockpit (DOER) — with embodied transition animations rather than flat tabs'
  rationale: 'Maps the product''s own Triune Self principle (Method Principle 4) directly to navigation, making the interface an expression of the product''s philosophy. Solves dual-audience problem: reviewers enter via Observatory (awe), practitioners via Cockpit (agency), both pass through Vault (trust).'
  confidence_score: 0.9
  alternatives_rejected:
  - 'Simple View/Cockpit binary toggle (Figma-style)'
  - 'Tab-based navigation (Vercel-style)'
  - 'Sidebar resource navigation (Kubernetes-style)'
aspect: thinker
neural:
  activation: 0.462
  stage: growing
  cluster: decisions
---

## Context

UX design session for Cohezion portfolio (2026-02-27). Needed a navigation model that serves both the daily practitioner (Mike, operator) and the Anthropic reviewer (Research Engineer, Universes), while honoring the product's own design philosophy. The Cohezion Method Principle 4 defines the Triune Self: Knower (observing/understanding), Thinker (planning/deciding), Doer (acting/executing).

Party mode dialogue with Sally (UX Designer), Maya (Design Thinking Coach), Victor (Innovation Strategist), Sophia (Storyteller), and Caravaggio (Presentation Master) surfaced this mapping.

## Decision

Three primary modes, not tabs — cognitive states:

- **KNOWER = Observatory**: Entry point. Full-screen FLUME visualization with three lenses. Re-entry narrative. Emotional register: arrival, awe.
- **THINKER = Vault**: The Three Pillars (◇ Decisions · ⬡ Experiments · ◎ Patterns). Natural language search. Emotional register: discovery, recognition.
- **DOER = Cockpit**: Compound cycle controls, agent management, live log stream, autonomic health panels. Emotional register: agency, competence.

## Transition Animations (Rituals)

- **Observatory → Vault**: Manifold contracts, falls toward a node, expands into a document. Duration: 600ms ease-in-out. Metaphor: zooming in.
- **Vault → Cockpit**: Horizontal slide + color temperature brightening + panels arrive. Duration: 400ms, snappier. Metaphor: activating.
- **Cockpit → Observatory**: Panels retract, interface breathes out, manifold expands. Duration: 800ms. Metaphor: releasing.
- Honors `prefers-reduced-motion`. Transitions abbreviate with familiarity.

## Chosen Option

Three cognitive modes with embodied transitions.

## Alternatives Considered

- **View/Cockpit binary** (Figma pattern): Misses the THINKER/Vault dimension which is the product's core IP
- **Flat tabs**: Treats fundamentally different cognitive states as equivalent
- **Sidebar navigation**: Kubernetes/Datadog style — works for resource browsing, wrong for spatial/immersive UX

## Decision Reasoning

### Why This Option?

The Triune Self principle already exists in the Cohezion Method. Mapping navigation to it means the interface IS the product's philosophy made interactive. No external navigation paradigm needed — the theory generates the structure.

### Confidence Level

High (0.9). The mapping is tight, the precedents are clear, and the emotional registers for each mode are well-defined and distinct.

## Expected Outcomes

- Reviewers understand the navigation model without documentation
- Practitioners develop muscle memory across the three modes
- The transition animations become a recognizable Cohezion signature
- The Triune Self principle becomes legible through use, not explanation

## Related

- [[cohezion]] — the Triune Self (Knower/Thinker/Doer) is Cohezion Method Principle 4, mapped directly to navigation
- [[cohezion-brand-guidelines|COHEZION Brand Guidelines]] — the brand's visual identity (palette, typography, spacing) applied across all three cognitive modes
- [[2026-02-27-ux-flume-as-foreground-three-lenses]] — the three FLUME lenses populate the Observatory (KNOWER) mode defined here
- [[2026-02-27-ux-provenance-over-poetry]] — provenance tags apply across all three navigation modes
- [[2026-02-27-ux-reentry-narrative-system-speaks-first]] — the re-entry narrative is the first experience in the Observatory (KNOWER) mode
- [[workflow-orchestration]] — the Cockpit (DOER) mode maps to the workflow orchestration layer with compound cycle controls and agent management
