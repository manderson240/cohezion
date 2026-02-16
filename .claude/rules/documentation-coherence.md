---
paths:
  - ".agent/**"
  - "src/cohezion/skills/**/*.md"
  - "CLAUDE.md"
---

# Documentation Coherence Rule

When writing or editing documentation about continuous systems (FLUME, HIHO, SPIN, manifolds, attractors), match the prose to the medium:

- **Regularizers, not taxonomies**: If the code uses `(x - 0.5)^2`, don't classify relationships as "Exact / Near / Structural." Describe gradient proximity instead
- **Preserve tensions**: Name open questions rather than resolving them into neat categories. Half-resolved is HIHO-stable
- **Damping check**: If documentation about coherence reads as coherence > 0.9 (everything resolved, no loose ends), it violates the principle it describes. Apply damping — add open questions, qualify certainties
- **Tables are for discrete data**: Use tables for API params, config keys, test counts. Use prose for attractor fields, cross-disciplinary convergence, latent space relationships
- **Anti-pattern — "freezing the fluid"**: Converting continuous fields into discrete bins loses the information the system preserves. See `vault/patterns/regularizer-over-taxonomy.md`
