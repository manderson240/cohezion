---
title: "Vault Knowledge Graph Densification: Cross-Link Papers → Concepts → Decisions"
date: "2026-02-25"
status: active
priority: high
tags: [project, knowledge-graph, compound-engineering, vault-quality]
---

## Overview

The vault has ~95 papers, ~40+ concepts, and dozens of decisions/patterns — but the cross-linking between them is sparse. Papers reference concepts inconsistently, concepts lack backlinks to the papers that inform them, and the SurrealDB graph is thin on `links` edges. This project densifies the knowledge graph by systematically auditing every paper and concept note, adding missing wiki-links, tagging integration points, and importing the enriched graph into SurrealDB.

This is a **compound engineering multiplier**: every future `vault_find_relevant_context` call, every SurrealDB query, and every agent session that pulls prior context gets dramatically better results when the graph is dense and accurate.

## Why This Matters for Cohezion

1. **FLUME validation work** needs to pull related papers (agent evaluation, VAE architectures, latent space interpretability) — if those papers aren't linked to relevant concepts like `experience-feedback-loop` or `agent-coherence`, the specialist teams miss context
2. **Anthropic application portfolio** benefits from being able to demonstrate a well-connected research knowledge base, not just a pile of notes
3. **Local agent orchestration** (Phase 3+) depends on agents finding relevant prior context via `vault_find_relevant_context` — sparse graphs return sparse results
4. **Research pipeline** processes new papers daily but doesn't retroactively cross-link them

## Scope

### Phase 1: Paper Audit (~2-3 hours)

For each of the ~95 papers in `papers/`:
1. Read the paper note
2. Identify concepts it should link to (check `concepts/` directory)
3. Add missing `[[concept-name]]` wiki-links in the paper body
4. Ensure frontmatter `tags` are consistent and useful
5. Add `similar_papers` frontmatter field where missing (list of 2-3 related paper filenames)
6. Ensure every paper has a `## Cohezion Integration` section with concrete connection to the codebase

### Phase 2: Concept Enrichment (~1-2 hours)

For each concept in `concepts/`:
1. Check that it has backlinks from relevant papers (use `vault_backlinks`)
2. If a concept is thin/stub, flesh it out with 2-3 paragraphs from knowledge + linked papers
3. Add `related_concepts` in frontmatter
4. Ensure tags are arrays (not multi-line YAML)

### Phase 3: SurrealDB Graph Rebuild (~30 min)

1. Run `surrealdb_import_papers` to re-import all papers with new links
2. Run `surrealdb_import_concepts` to re-import concepts
3. Verify link density with: `SELECT count() FROM links GROUP BY type;`
4. Run quality check: `SELECT id, count(->links) as link_count FROM paper ORDER BY link_count ASC LIMIT 10;` (find least-connected papers)

### Phase 4: Validation Queries (~30 min)

Run analytical queries to verify graph quality:
- Papers with zero concept links
- Concepts with zero paper backlinks
- Orphaned notes (no incoming or outgoing links)
- Tag distribution analysis
- Domain coverage gaps

## Success Criteria

| Metric | Before | Target |
|--------|--------|--------|
| Avg links per paper | ~1-2 | 4-6 |
| Concepts with 3+ backlinks | ~10% | 60%+ |
| Papers with `similar_papers` | ~20% | 90%+ |
| Papers with `## Cohezion Integration` | ~50% | 100% |
| SurrealDB `links` edges | unknown | 400+ |

## Implementation Notes

- Use `vault_read` + `vault_edit` for surgical updates (don't rewrite entire notes)
- Use `vault_backlinks` and `vault_forward_links` to audit connectivity
- Batch SurrealDB imports after all edits are complete (not per-file)
- Log decisions about ambiguous categorizations in `decisions/`

## Dependencies

- [[google-sheets-vault-integration]] — new papers flowing in need same treatment
- [[repo-and-process-debt]] — linting/CI could validate frontmatter schemas
- [[local-agent-orchestration-roadmap]] — Phase 3+ agents consume this graph
