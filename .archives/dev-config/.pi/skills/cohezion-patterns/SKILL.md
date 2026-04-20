---
name: cohezion-patterns
description: Search and apply Cohezion's 212 PRIME skills and compound engineering patterns. Use when working on compound loops, skill refinement, coherence optimization, FLUME encoding, or any Cohezion-specific task. Also use when asked about "how does X work in cohezion" or "find the pattern for X".
---

# Cohezion Patterns

Quick access to Cohezion's 212 PRIME skills and compound engineering patterns.

## How to Use

1. **Search for relevant skills**: Use `kg_search` tool with your query
2. **Read the skill file**: Skills are in `src/cohezion/skills/` as markdown files
3. **Apply the pattern**: Follow the skill's instructions

## Key Skill Categories

### Compound Engineering
- `COMPOUND_EXECUTOR_PRIME` — 11-step compound execution pipeline
- `SKILL_REFINER_PRIME` — Append-only skill refinement from execution
- `RETROSPECTION_ENGINE_PRIME` — Extract learnings, flag anomalies
- `JOURNEY_TRACKER_PRIME` — 12D FLUME universe tracking

### Reliability & Cost
- `SELF_HEALING_PRIME` — Automatic healing from degradation
- `COST_AWARE_ROUTING_PRIME` — 27% cost savings via model quality classification
- `ANTI_PATTERN_GUARDIAN_PRIME` — Detect and prevent anti-patterns
- `API_ERROR_RESILIENCE_PRIME` — Circuit breakers and fallbacks

### Physics & World Model
- `HIHO_STABILITY_PRIME` — High Intent / High Observed alignment theory
- `SPIN_COHERENCE_PRIME` — Information unit = Rotation + Precession
- `FLUME_VAE_PRIME` — 256D latent space encode/decode
- `BIOELECTRIC_NETWORK_PRIME` — Levin gap junction percolation

### Infrastructure
- `AUTORESEARCH_PRIME` — Autonomous optimization loop
- `PI_INTEGRATION_PRIME` — Pi-Cohezion bridge patterns
- `KAGGLE_BLACKWELL_PRIME` — Blackwell handshake for G4 compute

## Quick Reference

```bash
# Search skills from command line
grep -l "PATTERN_NAME" src/cohezion/skills/*.md

# Read a specific skill
cat src/cohezion/skills/COMPOUND_EXECUTOR_PRIME.md

# Search knowledge graph
# (use kg_search tool in pi)
```

## Constraints
- NEVER retroactively add FLUME encoding — wire from creation
- NEVER build infrastructure for products that don't exist yet
- NEVER store secrets in .env for scripts — use passwordless sudo
- ALWAYS use `uv` for package management