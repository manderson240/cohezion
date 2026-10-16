---
name: first-principles-invariant-science
metadata:
  version: "1.0.0"
description: >-
  First-principles physical, chemical, topological, and stylometric invariant engineering for ARC-AGI, RSNA Knee, CASMI-2026, Name That LLM, and NFL Big Data Bowl 2027.
---

# SKILL: FIRST_PRINCIPLES_INVARIANT_SCIENCE_PRIME

## DOMAIN EXPERTISE
Expertise in grounding competitive AI systems and autonomous agent swarms in physical laws, geometric manifolds, and causal invariants (Dihedral $D_4$ symmetry, tandem mass conservation, monotonic joint space narrowing, stylometric syntactic/morphological entropy, Voronoi spatial field control, and hyperbolic Poincaré tree search) rather than superficial leaderboard chasing.

## KEY TEXTS & CONCEPTS
- **The Leaderboard Chasing Anti-Pattern**: Overfitting public test splits via ungrounded black-box stacking or arbitrary prompt mutations.
- **Dihedral Group $D_4$ Equivariance**: Visual transformations must commute with planar rotations and reflections: $\forall g \in D_4, f(g \cdot X) = g \cdot f(X)$ (ARC-AGI-2/3).
- **Poincaré Ball Tree Embedding $\mathbb{D}^n$**: Hyperbolic metric spaces naturally accommodate exponential decision-tree branching with bounded distortion.
- **Sub-Graph Mass Conservation**: In tandem mass spectrometry, every daughter fragment ion obeys strict mass balance with the precursor ion ($m_{\text{precursor}} = m_{\text{fragment}} + m_{\text{neutral\_loss}} \pm \delta_{\text{ppm}}$) (CASMI26).
- **Anatomical Monotonicity & Bilateral Symmetry**: Joint space narrowing (JSN) and subchondral sclerosis severity must follow monotonic degeneration ordering constrained by contralateral knee ratios (RSNA Knee).
- **Stylometric Invariant Density & Sinkhorn Optimal Transport**: Generative LLMs exhibit distinct tokenizer-free character transition matrices and function-word distributions; Balanced Accuracy optimization requires Sinkhorn uniform marginal prior balancing across model classes (Name That LLM).
- **Kinematic Conservation & Field Tessellation**: Player velocity and acceleration vectors obey $a = dv/dt \le a_{\max}$; pass-rush impact is strictly bounded by Voronoi field control areas (NFL BDB 2027).
- **AutoHarness Zero-Cost Bytecode Verification**: Deterministic formal verification gating every candidate action prior to execution.

## INSTRUCTION
1. Define Domain Invariant Specification:
   Identify physical conservation laws (mass, momentum, topological continuity, D4 symmetry).
2. Synthesize Deterministic AutoHarness Verifier:
   ```python
   class DomainInvariantVerifier:
       @staticmethod
       def verify_conservation(precursor_mz: float, fragment_mz: float, neutral_loss_mz: float, tol_ppm: float = 10.0) -> bool:
           delta = abs(precursor_mz - (fragment_mz + neutral_loss_mz))
           return (delta / precursor_mz) * 1e6 <= tol_ppm
   ```
3. Apply Poincaré Distance Metric for Hierarchical Trees:
   ```python
   def poincare_dist(u: np.ndarray, v: np.ndarray) -> float:
       sq_dist = np.sum((u - v) ** 2)
       u_sq = np.sum(u ** 2)
       v_sq = np.sum(v ** 2)
       denom = (1.0 - u_sq) * (1.0 - v_sq)
       return float(np.arccosh(1.0 + 2.0 * sq_dist / max(1e-12, denom)))
   ```
4. Gate All Dispatches Through Formal IV&V:
   Reject any candidate model whose predictions violate domain physical monotonicity or symmetry invariants.

## VERSION
v1.0

## SEE ALSO
- LUKYANENKO_INVARIANT_ENGINEERING_PRIME
- ARC_TOPOLOGICAL_PIVOT_PRIME
- ALGORITHMIC_FOUNDATIONS_PRIME
