---
title: "Concept Versioning"
date: 2026-02-19
tags: [concept, knowledge-management, vault-architecture, semantic-web]
aspect: knower
neural:
  activation: 1.0
  stage: mature
  synapse_in: 10
  synapse_out: 14
---

# Concept Versioning

## Definition

Concept versioning is the practice of tracking how knowledge concepts evolve over time within a knowledge graph. Unlike code versioning (which tracks file diffs), concept versioning captures **semantic evolution**: a concept's definition may be refined, its relationships may shift, or its accuracy may improve as new evidence emerges. The version history of a concept preserves the **reasoning trajectory**, not just the current state.

This is fundamentally different from document versioning. A document version is a snapshot of text; a concept version is a snapshot of *understanding*. When the definition of "agent architecture" shifts from "single LLM loop" to "multi-agent orchestration with role specialization," that's a semantic version bump — the concept itself has evolved, not just the words describing it.

## Key Properties

- **Semantic IDs over sequential numbering**: Concepts use filename-based identifiers (e.g., `surrealdb.md`) rather than sequential numbers, which are fragile across corpus boundaries. See [[lesson-40-sequential-numbering-offset-corrupts-indexes]] for the failure mode.
- **Git-backed history**: Concept evolution is tracked through git commits on vault files, providing full diff history with `git log --follow <file>`
- **Frontmatter metadata**: The `date` field records creation; git log tracks modification history; `status` tracks lifecycle stage
- **Non-destructive updates**: Existing concept notes are edited in place rather than replaced, preserving all inbound backlinks — the cardinal rule of wiki-link stability
- **Schema evolution**: As the vault matures, concept frontmatter schemas evolve (adding `aspect`, `neural`, `related_concepts` fields) without breaking existing notes
- **Append-only enrichment**: The vault-keeper and flesh-out skills expand notes by *adding* sections, never removing existing content (unless factually wrong)

## Versioning Strategies Compared

| Strategy | Pros | Cons | Cohezion Uses? |
|----------|------|------|----------------|
| **In-place editing** (current) | Backlinks stable, single source of truth | History only via git | Yes (primary) |
| **Copy-on-write** (v1, v2 files) | Easy comparison | Backlink fragmentation, naming proliferation | No |
| **Branching** (git branches per concept version) | Full isolation | Merge conflicts, lost cross-links | No |
| **Append-only log** (changelog section) | Readable evolution within file | File bloat | Partial (for decisions) |
| **Graph-native versioning** (SurrealDB temporal) | Query any point in time | Infrastructure complexity | Planned |

## Examples

- A concept note starts as an auto-generated stub (~200 bytes), gets expanded with real research content (~3KB), then later gains `related_concepts` frontmatter, `aspect` field, and 5+ outbound wiki-links (~5KB). Each stage is a semantic version.
- Lesson notes (e.g., [[lesson-40-sequential-numbering-offset-corrupts-indexes]]) capture versioning failures and corrections
- The `neural.stage` field (`embryo` → `growing` → `mature`) is itself a versioning signal — it tracks conceptual maturity, not just file age
- Decision records (ADRs in `prefrontal/`) use explicit `status` versioning: `proposed` → `accepted` → `deprecated`

## Anti-Patterns

| Anti-Pattern | Failure Mode | Resolution |
|-------------|-------------|------------|
| Sequential numbering across corpora | IDs collide or leave gaps when merged | Use semantic slug IDs |
| Renaming files without redirects | All inbound backlinks break silently | Use Obsidian aliases or never rename |
| Duplicating instead of linking | Same concept described differently in multiple notes | Merge into canonical note, redirect others |
| Schema-breaking frontmatter changes | Existing notes fail validation | Make schema additions backward-compatible |

## Related Lessons

- [[lesson-40-sequential-numbering-offset-corrupts-indexes]] — sequential numbering offsets across corpus boundaries corrupt indexes; semantic IDs are resilient
- [[lesson-10-gitlab-ci-runner]]
- [[lesson-13-8-6m-file-incident]]
- [[lesson-19-session-awareness-protocol]]
- [[lesson-21-runtime-json-pollution]]
- [[lesson-22-gitignore-ordering]]
- [[lesson-23-stash-branch-switch-hazard]]
- [[lesson-26-never-print-credentials]]
- [[lesson-27-hook-file-revert]]

## Related Concepts

- [[concept-modularity]] — modular concepts can be versioned independently without cascading changes
- [[concept-validation]] — validation ensures versioned updates maintain accuracy
- [[knowledge-graph-systems]] — the graph that concept versions populate
- [[wiki-links]] — the linking mechanism that concept versioning must preserve
- [[Obsidian-Best-Practices-for-AI-Agents]] — conventions that support stable concept versioning

## Primary Sources

1. Berners-Lee, T. (2006). "Linked Data." *Design Issues*, W3C. [The web architecture principle that concept versioning implements at vault scale]
2. Sowa, J.F. (2000). *Knowledge Representation: Logical, Philosophical, and Computational Foundations.* Brooks/Cole. [Formal semantics of concept evolution]
3. Git documentation: `git log --follow` for tracking file history through renames

## Relevance to Cohezion

Concept versioning is the vault's immune system against knowledge decay. Each lesson and concept note evolves through multiple sessions, and the versioning approach (semantic filenames + git history + non-destructive updates) ensures that cross-references remain stable even as content is refined. The `neural.stage` field adds a second versioning axis: not just *what changed* but *how mature the understanding is*. The vault-keeper skill enforces versioning invariants (no orphaned backlinks, no broken frontmatter) as part of every maintenance cycle.
