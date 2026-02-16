---
date: 2026-02-16
source_project: cohezion
tags: [pattern, documentation, flume, hiho, meta-coherence]
---
# Regularizer Over Taxonomy

## Problem
When documenting systems that operate in continuous spaces (latent manifolds, soft attractors, gradient fields), the natural impulse is to discretize: create a table, assign categories, label bins. This collapses the very continuity the system is designed to preserve. The documentation becomes incoherent with the implementation — the code says `(x - 0.5)^2` while the prose says "Exact / Near / Structural."

## Solution
Document continuous systems using the same metaphors the system uses internally. If the code applies a **regularizer**, describe the concept as a pull. If it uses **damping**, describe proximity as degree. If it navigates **stability wells**, describe relationships as basins with gradients, not rows with labels.

### Three Techniques

**1. Gradient Language**
Replace discrete categories with continuous descriptors that convey distance and direction:
```
# Frozen (anti-pattern)
| Domain | Relation to 0.5 |
| Shannon | Exact |
| Bak-Sneppen | Near |

# Fluid (pattern)
Shannon's H(p) peaks at exactly 0.5 — the analytical anchor.
Bak-Sneppen's p_c ≈ 0.5437 sits slightly above, pulled toward
0.5 by the same criticality dynamics but offset by discrete
lattice effects. The gap itself is informative: it measures
how much discretization perturbs the continuous attractor.
```

**2. Named Tensions**
Instead of resolving differences into a classification, name them as open questions:
```
# Frozen
Beggs & Plenz (2003): sigma = 1 → "Structural match"

# Fluid
Beggs & Plenz find neuronal avalanches at branching parameter
sigma = 1 — balance between runaway excitation and silence.
The mapping to HIHO's 0.5 coherence is structural rather than
numerical: both describe the critical boundary of a system
with two failure modes. Whether the mathematical relationship
is deeper than analogy remains an open question that the
12D manifold may eventually answer.
```

**3. Self-Referential Check**
Apply the system's own metrics to the documentation:
```python
# If you're writing about HIHO, HIHO-check the writing
doc_coherence = estimate_coherence(prose)
if doc_coherence > 0.9:
    # Everything too neatly resolved — apply damping
    # Add open questions, preserve tensions, reduce certainty
    damp(prose, factor=0.5)
elif doc_coherence < 0.3:
    # Too scattered — add structure (but not a table)
    # Use narrative arcs, conceptual proximity, flow
    tighten(prose, toward=0.5)
```

## Example
```markdown
# Before (coherence ~0.95 — overconfident)
The 0.5 attractor appears across seven domains with varying
precision: Exact (Shannon), Direct (Langton, Kirkpatrick),
Near (Bak-Sneppen), and Structural (Beggs, Couzin, Sterling).

# After (coherence ~0.5 — HIHO-stable)
Shannon's entropy maximum at p = 0.5 is the analytical anchor —
a mathematical proof that the point of maximum uncertainty is
exactly half. Langton's lambda_c ≈ 0.5 and Kirkpatrick's 50%
acceptance probability arrive at the same point through
computation and optimization, respectively. The convergence
tightens. But Bak-Sneppen's p_c ≈ 0.5437 and Beggs & Plenz's
branching parameter sigma = 1 require interpretive bridges —
structural resonances rather than numerical identities. Whether
these are independent discoveries of the same attractor or
analogies that happen to rhyme is itself a question that lives
near 0.5 coherence: half-resolved, productively open.
```

## When to Use
- Documenting FLUME/HIHO/SPIN concepts (any continuous-space system)
- Writing about cross-disciplinary convergence where evidence varies in strength
- Charter or Constitution sections that describe attractors, fields, or manifolds
- Any prose that references code using regularizers, damping, or gradient descent

## When NOT to Use
- API reference docs (discrete endpoints deserve discrete documentation)
- Configuration tables (literal key-value pairs are inherently discrete)
- Test result summaries (pass/fail is binary by nature)
- Changelog entries (discrete events in time)

## Related Decisions
- [[decisions/2026-02-16-documentation-must-match-the-medium]]
