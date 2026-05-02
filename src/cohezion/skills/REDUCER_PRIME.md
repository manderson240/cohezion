---
name: reducer-prime
description: "Expert in semantic compression, conceptual distillation, and latent abstraction. Specializes in reducing high-dimensional agentic trajectories into compact, portable \"knowledge kernels\" that can be transferred across simulation universes."
metadata:
  version: "v1.0"
  concepts: ["Manifold Reduction", "Knowledge Kernels", "Abstraction Cascades", "HIHO Stability"]
  source: "src/cohezion/skills/REDUCER_PRIME.md"
---

# SKILL: REDUCER_PRIME

## DOMAIN EXPERTISE
Expert in **semantic compression, conceptual distillation, and latent abstraction**. Specializes in reducing high-dimensional agentic trajectories into compact, portable "knowledge kernels" that can be transferred across simulation universes.

## KEY TEXTS & CONCEPTS
- **Manifold Reduction**: The process of mapping 256-dim thought vectors into highly compressed 12D physical representations without losing causality.
- **Knowledge Kernels**: Discrete, self-contained units of learned logic extracted from continuous simulations.
- **Abstraction Cascades**: Layered distillation where specific simulation observations become generalized principles.
- **HIHO Stability**: Maintaining 0.5 coherence overlap when abstracting to ensure the resulting principle is both grounded and generalized.

## INSTRUCTION

1. **Capture Trajectories**: Collect the full 256-dim latent history of a simulation journey.
2. **identify Pivot Points**: Use the `TrajectoryPredictor` to find moments of high "Pragmatic Displacement" where the simulation discovered a novel state.
3. **Perform Distillation**:
   ```python
   # Pseudocode for REDUCER_PRIME extraction
   z_history = get_journey_vectors(journey_id)
   kernel = flume.distill(z_history, ratio=0.01) # 100:1 compression
   ```
4. **Abstract to Skill**: Translate the distilled vector back into human-readable instructions for inclusion in a `SKILL.md` file.
5. **Verify Fidelity**: Ensure the abstracted skill can recreate the successful simulation outcome with ≤ 10% error in the sandbox.

## VERSION
v1.0

## SEE ALSO
FLUME_PRIME, PHYSICS_PRIME, JOURNEY_TRACKING_PRIME
