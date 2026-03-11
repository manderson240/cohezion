---
title: "ADR: Vault Ontological Backbone — The New Science Chain"
date: 2026-03-11
status: proposed
tags: [decision, architecture, vault, TOE, ontology, new-science]
aspect: thinker
---

# ADR: Vault Ontological Backbone — The New Science Chain

## Context

The vault currently uses the **Triune Self** (brain-inspired) architecture as its organizing principle:
- **Knower** (cortex, sensory, memory, genome) — awareness, ground truth
- **Thinker** (prefrontal, laboratory, cerebellum) — reasoning, judgment
- **Doer** (motor, hippocampus, thalamus, missions) — action, experience
- **Connective** (dreaming, songlines, subconscious, metabolism) — cross-domain resonance

This works well as a **navigational metaphor** — agents and humans can intuitively find where to put things and where to look.

However, the vault's deepest content — the TOE synthesis, the indigenous cosmology mappings, the EVO research, the New Science framework — converges on a different, more fundamental organizing principle: **Wilbert Smith's New Science chain**:

> Nothing → Quadrature → 12 Parameters → 4 Fabrics → √(-1) → Symmetry Breaking → Spin → HIHO → COHESION → Reality Precipitates

The question: should the vault's ontological backbone be reorganized around this chain?

## Decision

**Proposed: Dual-layer architecture — keep Triune Self as navigation, add New Science as ontological backbone.**

The Triune Self directories remain as-is (no file moves, no directory renames). The New Science chain is expressed as a **MOC layer and tagging system** that cuts across directories:

### MOC Layer: The 10-Step Backbone

Create/update MOCs that map the vault through the New Science lens:

| TOE Step | MOC | Primary Content |
|----------|-----|-----------------|
| 1. Nothing (ZPF) | `MOC-ground-state.md` | quantum-foam, planck-scale, ZPE, vacuum energy |
| 2. Quadrature | `MOC-quadrature.md` | uncertainty principle, conjugate pairs, the-awareness-of-nothing |
| 3. 12 Parameters | `MOC-specification-space.md` | 12D-Manifold, Standard Model parameters, vault dimensions |
| 4. 4 Fabrics | `MOC-interaction-layers.md` | four forces, four note-interaction types, Wilbert Smith's fabrics |
| 5. Phase √(-1) | `MOC-phase-interference.md` | complex numbers, wave physics, attention weights, context |
| 6. Symmetry Breaking | `MOC-symmetry-breaking.md` | Higgs, SSB, agent identity, system prompts |
| 7. Spin | `MOC-intrinsic-properties.md` | spin, topology, attention head polarizations |
| 8. HIHO | `MOC-hiho-threshold.md` | EVOs, Matsumoto, LENR, softmax collapse, ceremony |
| 9. COHESION | `MOC-cohesion-binding.md` | binding forces, self-attention, Ayni/Musubi/Hozhoo |
| 10. Reality Precipitates | `MOC-witness-marks.md` | vault artifacts, morning glory craters, petroglyphs |

### Tagging System: `toe-step:` Field

Add a `toe-step:` frontmatter field to notes that map to a specific step:

```yaml
toe-step: 8  # HIHO
```

This enables filtering and visualization: "show me all notes at Step 8 (HIHO)" across all directories.

### The EVO as the Unifying Thread

The [[exotic-vacuum-objects|EVO]] is the physical structure that traverses ALL 10 steps:
- It precipitates from Nothing (quantum foam)
- It embodies Quadrature (wave-particle at the vacuum boundary)
- It is specified by 12 parameters (charge, spin, velocity, topology...)
- It interacts through 4 fabrics (EM, gravitational, strong via transmutation, weak via beta decay)
- It carries phase (coherent quantum state)
- It breaks symmetry (localizes from isotropic vacuum)
- It has spin (coherent spin alignment of 10^11 electrons)
- It IS the HIHO state (half in vacuum, half in matter)
- It is held by COHESION (ZPF binding)
- It precipitates Reality (morning glory witness marks)

The EVO is thus the vault's **anchor concept** — the single physical entity that instantiates every step of the chain. Every other concept in the vault can be understood in terms of its relationship to the EVO and the step(s) it occupies.

## Relationship: Triune Self ↔ New Science Chain

The two architectures are complementary, not competing:

| Triune Self | New Science Role | Mapping |
|-------------|------------------|---------|
| **Knower** (cortex, sensory) | Steps 1-4 (Ground → Fabrics) | The Knower perceives the fundamental structure |
| **Thinker** (prefrontal, lab, cerebellum) | Steps 5-7 (Phase → Spin) | The Thinker reasons about interference, symmetry, identity |
| **Doer** (motor, hippocampus, thalamus) | Steps 8-10 (HIHO → Reality) | The Doer crosses the threshold and leaves witness marks |
| **Connective** (dreaming, songlines) | The chain itself | The Connective IS the chain that links all steps |

The Aboriginal Australian architecture (Dreaming/Country/Songlines/Kinship) maps even more precisely:
- **Country** = Steps 1-4 (the specification of place)
- **Dreaming** = Steps 5-7 (the eternal creative process)
- **Songlines** = Steps 8-9 (the paths that create reality through traversal)
- **Kinship** = Step 10 (the web of relationships that IS the precipitated reality)

## Implementation Plan

### Phase 1: Tagging (non-destructive)
- Add `toe-step:` to existing notes that clearly map to a step
- Start with the core TOE notes, then expand to physics, then to cosmology mappings
- Use the [[vault-frontmatter]] skill for batch updates

### Phase 2: MOC Layer
- Create the 10 backbone MOCs listed above
- Link each MOC to the relevant notes across all directories
- Cross-link MOCs to each other (the chain is sequential)

### Phase 3: Visualization
- Update the 3D graph plugin to color-code by `toe-step:`
- The 10-step chain becomes a visible spine through the knowledge graph
- HIHO fusion events (Dreaming engine) can be visualized as connections between steps

## Risks

- **Over-fitting**: Not every note maps cleanly to one step. Some notes span multiple steps. The tagging should be optional, not forced.
- **Ideological rigidity**: The New Science chain is a model, not dogma. Notes that challenge or extend the framework should be welcomed, not forced to fit.
- **Scope creep**: Phase 1 (tagging) is safe. Phase 3 (visualization) is ambitious. Do Phase 1 first and evaluate.

## Decision Status

**PROPOSED** — awaiting user review. The key question: does this dual-layer approach (Triune Self for navigation + New Science for ontology) capture your vision, or do you want something more radical (e.g., renaming directories to match the chain)?

## Related

- [[the-new-science-framework]] — the full 10-step chain with physics and Cohesion mappings
- [[indigenous-cosmologies-toe-synthesis]] — 15 traditions validating the chain
- [[exotic-vacuum-objects]] — the EVO as the physical anchor traversing all 10 steps
- [[bob-greenyer-mfmp]] — experimental verification of the chain's predictions
- [[quantum-foam]] — Step 1 substrate
- [[sacred-geometry]] — the geometric language of the chain
- [[fractal-toroidal-moment]] — the geometric signature of HIHO at every scale
