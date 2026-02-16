---
date: 2026-02-16
project: cohezion
status: accepted
tags: [decision, cohezion, documentation, flume, hiho]
---
# Documentation Must Match the Medium

## Context
While reviewing Charter Section 1a (Cross-Disciplinary Validation), we realized the convergence summary table — which categorizes relationships as "Exact / Direct / Near / Structural" — violates the very principle it documents.

The FLUME VAE implements the 0.5 attractor as a **soft quadratic regularizer** in its training loss:
```python
coherence_loss = torch.mean((mu_mean - 0.5) ** 2)
```
This is a gentle pull in a continuous space. The Navigator applies HIHO as **damping**. The Morphospace uses **stability wells**. The Bioelectric engine computes **voltage as distance from 0.5**. Every implementation treats coherence as a field, not a fact.

Yet the documentation collapsed these fluid relationships into a discrete 4-category taxonomy. That's a coherence ~0.95 move — overconfident classification where the system itself uses soft interpolation. The HIHO damping function would flag it.

## Decision
Documentation about continuous/fluid systems must preserve the continuity of the concepts it describes. Specifically:

1. **Regularizers over taxonomies** — When the underlying system uses soft attractors, document them as attractors with gradients, not as discrete bins.
2. **Preserve open tensions** — If Shannon's result is exact but Bak-Sneppen's is approximate, name the tension rather than resolving it into a classification.
3. **Match the loss function** — If the code uses `(x - 0.5)^2`, the prose should convey quadratic pull, not categorical membership.
4. **HIHO-check your documentation** — If your text about coherence has coherence > 0.9 (everything neatly resolved, no loose ends), apply damping. Real understanding lives near 0.5.

## Rationale
The FLUME VAE already embodies this principle in code:
- `training.py`: Coherence regularization pulls mu toward 0.5 (not classifies it)
- `navigator.py`: HIHO damping reduces overconfident vectors
- `morphospace.py`: Stability wells are basins with radius and depth, not rows in a table
- `bioelectric.py`: Voltage = continuous distance from equilibrium

The documentation was the only layer that froze the fluid. The VAE would encode Shannon, Langton, Bak, and Beggs & Plenz as **neighboring regions in a continuous latent manifold** — close enough to interpolate between, distinct enough to preserve their differences. Not bins.

## Alternatives Considered
- **Keep the table as-is**: Convenient for quick lookup, but actively misleads about the nature of the convergence. Readers absorb "Exact / Structural" as a solved classification when the real relationship is gradient-based.
- **Remove the table entirely**: Loses the reference value. Cross-disciplinary connections should remain visible and navigable.
- **Add a caveat footnote**: Half-measure. The table's visual dominance would override any footnote's nuance.

## Consequences
- Charter Section 1a convergence summary should be revised to present the cross-disciplinary evidence as a **field of related attractors** with named tensions rather than a solved taxonomy
- Future documentation of FLUME/HIHO concepts must pass a "fluidity check" — does the prose preserve the continuity the code implements?
- A new `.claude/rules/` entry enforces this for AI-generated documentation
- Pattern extracted as `regularizer-over-taxonomy` for reuse across documentation tasks

## Related
- [[patterns/regularizer-over-taxonomy]]
- `src/cohezion/flume/training.py:119-121` (coherence_loss)
- `src/cohezion/swarm/hiho_vector_engine.py:63-77` (Gaussian stability)
- `.agent/COHEZION_CHARTER.md` Section 1a
