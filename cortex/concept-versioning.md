---
title: "Concept Versioning"
date: 2026-02-19
tags: [concept]
aspect: knower
neural:
  activation: 0.523
  stage: growing
  cluster: concepts
---
## Definition

Concept versioning is the practice of tracking how knowledge concepts evolve over time within a knowledge graph. Unlike code versioning (which tracks file diffs), concept versioning captures semantic evolution: a concept's definition may be refined, its relationships may shift, or its accuracy may improve as new evidence emerges. The version history of a concept preserves the reasoning trajectory, not just the current state.

## Key Properties

- **Semantic IDs over sequential numbering**: Concepts use filename-based identifiers (e.g., `surrealdb.md`) rather than sequential numbers, which are fragile across corpus boundaries
- **Git-backed history**: Concept evolution is tracked through git commits on vault files, providing full diff history
- **Frontmatter metadata**: The `date` field records creation; git log tracks modification history
- **Non-destructive updates**: Existing concept notes are edited in place rather than replaced, preserving backlinks
- **Schema evolution**: As the vault matures, concept frontmatter schemas evolve (adding `related_concepts`, `status` fields)

## Examples

- A concept note starts as an auto-generated stub, gets expanded with real content, then later gains `related_concepts` frontmatter and additional wiki-links
- Lesson notes (e.g., [[lesson-40-sequential-numbering-offset-corrupts-indexes]]) capture versioning failures and corrections

## Related Papers

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

## Key Lesson Links

- [[lesson-40-sequential-numbering-offset-corrupts-indexes]] — sequential numbering offsets across corpus boundaries corrupt indexes; semantic IDs are resilient, sequential offsets are fragile

## Relevance to Cohezion

Concept versioning underpins the vault's reliability as a growing knowledge system. Each lesson and concept note evolves through multiple sessions, and the versioning approach (semantic filenames + git history) ensures that cross-references remain stable even as content is refined. The linked lessons document specific versioning failures that shaped the current approach.
