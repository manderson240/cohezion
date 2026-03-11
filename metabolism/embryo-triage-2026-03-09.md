---
title: "Embryo Triage Report — 2026-03-09"
date: 2026-03-09
tags: [metabolism, triage, lifecycle, report]
aspect: connective
neural:
  activation: 0.600
  stage: growing
  cluster: metabolism
---

# Embryo Triage Report

> 478 notes in embryo stage (<3 synapses AND <500 words). Categorized into compost, tiny stubs, and flesh-out candidates.

## Summary

| Category | Count | Description |
|----------|-------|-------------|
| Compost candidates | 18 | <50 words, 0 synapses — generated scaffolding |
| Tiny stubs | 90 | <100 words, some links — minimal content |
| Flesh-out candidates | 370 | 100-500 words — has substance, needs expansion and linking |

## By Country

| Country | Embryos | Notes |
|---------|---------|-------|
| **Agents** | 361 | 360 are Antigravity agent task/walkthrough files |
| **hippocampus** | 72 | Session logs with few cross-links |
| **prefrontal** | 9 | Short decisions needing expansion |
| **teleport** | 8 | Teleport result files |
| **cerebellum** | 7 | Pattern stubs |
| **laboratory** | 6 | Experiment stubs |
| **genome** | 4 | Spec templates and stubs |
| Other | 11 | Scattered across skills_index, motor, cortex, etc. |

## Recommended Actions

### 1. Agents/Antigravity — Bulk Composting (360 notes)

These are auto-generated agent session files (task.md, walkthrough.md, implementation_plan.md) from the Antigravity multi-agent system. They have:
- No wiki-links to the broader vault
- Self-contained content per session
- UUID-based directory names (not human-navigable)

**Recommendation:** Keep in SurrealDB as historical records but mark as `stage = "composting"`. They feed the Akashic Records but don't need active graph participation. Alternatively, add batch wiki-links to relevant concepts (e.g., link all "implementation_plan.md" files to [[agent-architecture]]).

### 2. Hippocampus Stubs — Link Enrichment (72 notes)

Session logs and daily notes that lack cross-references. Most have decent content (100-400 words) but no outbound links.

**Recommendation:** Run the `/link` skill on these to add bidirectional wiki-links. Many reference decisions, patterns, and concepts that should be connected.

### 3. Non-Agents Flesh-out Candidates (17 notes)

High-value stubs outside the Agents directory:

| Path | Words |
|------|-------|
| `genome/models/_template.md` | 475 |
| `genome/embeddings/_template.md` | 459 |
| `hippocampus/2026-02-10-12d-graph-phase1-kickoff.md` | 453 |
| `prefrontal/2026-02-16-phases-4b-7-master-execution-plan-revised.md` | ~300 |
| `cerebellum/phase-5b-completion-pattern.md` | ~250 |
| `laboratory/2026-03-05-flume-kl-collapse-diagnostic.md` | ~200 |

**Recommendation:** Use `/flesh-out` skill to expand these with researched content.

## Compost Candidates (18 notes, <50 words)

These are essentially empty or near-empty files:

- Index files (`_index.md`) with only a title
- Placeholder templates
- Abandoned stubs

**Recommendation:** Either flesh out with content or mark as `stage = "composting"` to remove from active graph metrics.

## Related

- [[metabolism-dashboard]] — Full vault health dashboard
- [[2026-03-09-latent-associations]] — Subconscious report showing unlinked pairs
- [[2026-03-09-resonances]] — Current Dreaming resonances
