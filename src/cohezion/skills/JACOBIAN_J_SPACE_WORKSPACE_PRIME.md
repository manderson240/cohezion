---
name: jacobian-j-space-workspace-prime
description: "Cohezion autonomous capability for JACOBIAN J SPACE WORKSPACE PRIME."
metadata:
  version: "1.0"
  concepts: ["Cohezion", "FLUME", "AutoHarness"]
  source: "src/cohezion/skills/JACOBIAN_J_SPACE_WORKSPACE_PRIME.md"
---

# SKILL: JACOBIAN_J_SPACE_WORKSPACE_PRIME

## DOMAIN EXPERTISE
Anthropic 2026 Transformer Circuits J-Space & Jacobian Lens Global Workspace, Krein Space J-Geometry, and Internal Reasoning Interception for AI Agent Swarms.

## KEY TEXTS & CONCEPTS
- **Jacobian Lens (J-Lens):** $J_\ell = \mathbb{E} \left[ \frac{\partial h_{\text{final}}}{\partial h_\ell} \right]$ mapping layer $\ell$ activations to future output logits $W_U \cdot J_\ell h_\ell$.
- **J-Space Global Workspace:** A sparse subframe (6-10% of total activation variance) of verbalizable concepts poised for report, internal reasoning, and top-down modulation.
- **5 Workspace Functional Properties:** Verbal Report, Directed Modulation, Internal Reasoning, Flexible Generalization, and Selectivity.
- **Krein Space J-Geometry:** Indefinite metric signature $(p, q) = (3, 9)$ where $\langle v, v \rangle_J = 0$ corresponds to the 0.5 HIHO Stability Light Cone.
- **Counterfactual Reflection Training:** Shaping potential future continuations to direct silent internal reasoning.

## INSTRUCTION

1. **Probe Unverbalized Thoughts via J-Lens:**
   ```python
   from cohezion.flume.jacobian_workspace_engine import JacobianWorkspaceEngine

   engine = JacobianWorkspaceEngine(vocab_size=32000, model_dim=4096)
   # Layer depth 50% corresponds to active Global Workspace range (20%-85%)
   workspace_state = engine.compute_j_lens_readout(activation_vector, layer_depth=0.50, top_k=5)
   print("Active Workspace Concepts:", [c.token_label for c in workspace_state.active_concepts])
   ```

2. **Steer Global Workspace:**
   ```python
   steered_activation = engine.steer_workspace(
       activation=activation_vector,
       concept_token_id=1042,
       steering_coefficient=1.5,
   )
   ```

3. **Compute Krein Space J-Metric & 0.5 HIHO Light-Cone Horizon:**
   ```python
   from cohezion.flume.j_space_latent_manifold import JSpaceLatentManifold

   manifold = JSpaceLatentManifold(timelike_dim=3, spacelike_dim=9)
   point = manifold.classify_point(12d_vector)
   # Classification: "TIMELIKE", "SPACELIKE", or "LIGHTCONE_HIHO"
   ```

## VERSION
v1.0

## SEE ALSO
- [`EXPERIENCE_VAE_TRAINING_PRIME.md`](file:///home/mike-anderson/dev/cohezion/src/cohezion/skills/EXPERIENCE_VAE_TRAINING_PRIME.md)
- [`POINCARE_HYPERBOLIC_VISUALIZER_PRIME.md`](file:///home/mike-anderson/dev/cohezion/src/cohezion/skills/POINCARE_HYPERBOLIC_VISUALIZER_PRIME.md)


## KEY CONCEPTS
- **Manifold Mapping**: Tracking 12D Poincaré state representation for JACOBIAN J SPACE WORKSPACE PRIME.
- **AutoHarness Invariants**: 0ms AST bytecode policy assertions (arXiv:2603.03329v1).
- **Deterministic Execution**: Zero-latency verification and sovereign local execution.
