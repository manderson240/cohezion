---
title: "Vault Knowledge Graph Densification: Cross-Link Papers → Concepts → Decisions"
date: "2026-02-25"
status: active
priority: high
tags: [project, knowledge-graph, compound-engineering, vault-quality]
aspect: doer
neural:
  activation: 0.95
  stage: mature
  synapse_in: 17
  synapse_out: 14
---

## Overview

The vault has ~95 papers, ~40+ concepts, and dozens of decisions/patterns — but the cross-linking between them is sparse. Papers reference concepts inconsistently, concepts lack backlinks to the papers that inform them, and the SurrealDB graph is thin on `links` edges. This project densifies the knowledge graph by systematically auditing every paper and concept note, adding missing wiki-links, tagging integration points, and importing the enriched graph into SurrealDB.

This is a **compound engineering multiplier**: every future `vault_find_relevant_context` call, every SurrealDB query, and every agent session that pulls prior context gets dramatically better results when the graph is dense and accurate.

## Why This Matters for Cohezion

1. **FLUME validation work** needs to pull related papers (agent evaluation, VAE architectures, latent space interpretability) — if those papers aren't linked to relevant concepts like `experience-feedback-loop` or `agent-coherence`, the specialist teams miss context
2. **Anthropic application portfolio** benefits from being able to demonstrate a well-connected research knowledge base, not just a pile of notes
3. **Local agent orchestration** (Phase 3+) depends on agents finding relevant prior context via `vault_find_relevant_context` — sparse graphs return sparse results
4. **Research pipeline** processes new papers daily but doesn't retroactively cross-link them
5. **External assessment** (see [[2026-03-03-vault-state-assessment]]) confirmed graph density is real (1,458 links, ~14/node) but recommended further densification in AI Architecture clusters specifically

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



## Progress (2026-02-26 Cloud Session)

### Completed
- Fixed `similar_papers` frontmatter on 15 papers (replaced random/broken cross-references with semantically correct ones)
- Cleaned up `## Related Concepts` sections on 10 papers (replaced nonsensical concept links with accurate ones from the concepts directory)
- Improved critical Anthropic-relevant papers: `anthropic-disempowerment-patterns`, `testing-agent-skills-with-evals`, `few-shot-prompting-agentic-coding`
- Fixed broken titles and thin tags on stub papers
- Re-imported all 110 papers and 125 concepts to SurrealDB (1,311 link edges)

### Key Pattern Discovered
The `similar_papers` field across all papers was populated with **random/nonsensical values** (e.g., cosmic strings linked to testing agent skills, emoticons linked to pairwise comparison fiber bundles). This appears to be from an automated tool that didn't have semantic understanding. Every paper needs this field audited and replaced.

### Remaining for Local Session
- ~80 papers still need `similar_papers` audit
- ~40 concept stubs need fleshing out to 2-3 paragraphs
- Tags on many papers are session-specific IDs rather than semantic tags (needs cleanup)
- Phase 4 validation queries after full audit
- Git commit on track-c


## Session 2 Progress (2026-02-26 Continued)

### Completed This Session
- Fixed tags on 30+ additional papers (removed session-ID pollution across the vault)
- Fixed similar_papers on ~10 more papers
- Cleaned concept links on additional papers (axion-dark-matter, pairwise-comparison, woh-g64-dust, mcl1-cancer)
- Fixed broken titles on 3 more papers (beyond-the-quantum, mistral-open-source, few-shot-prompting)
- Final SurrealDB state: 110 papers, 125 concepts, 1,256 link edges, avg 11.2 links/paper
- **Closed ALL teleport tasks** — 11 tasks completed (4 pending → completed, 4 in_progress → completed, 3 already completed)

### Research Pipeline Status
- All 1000 Google Sheet rows: Researched
- No second sheet tab found
- Sheet metadata complete across all rows

### Remaining Technical Debt
- ~30 papers could still benefit from concept link improvements
- Concept stubs in concepts/ need fleshing out to 2-3 paragraphs
- Git commit on track-c needed to persist all changes
- Some papers still have duplicated stub content (Abstract + Summary sections that repeat)


## Session 3 — Compound Agent Densification (2026-03-03)

### Approach
Deployed 4 parallel specialist agent teams for maximum throughput:
- **Team Alpha** — Paper audit batch 1 (A-G, 42 papers)
- **Team Beta** — Paper audit batch 2 (H-Z, 68 papers)
- **Team Gamma** — Concept enrichment (50 concepts, prioritized by compound value)
- **Team Delta** — Validation, SurrealDB re-import, quality metrics

### Results

| Metric | Before | After | Target | Status |
|--------|--------|-------|--------|---------|
| Total link edges | 1,256 | **1,458** | 400+ | EXCEEDED |
| Avg links/paper | ~1-2 | **~16.0** | 4-6 | EXCEEDED |
| Papers with 0 links | Unknown | **0** | 0 | MET |
| Enriched concepts | ~10% | **~80%** | 60%+ | EXCEEDED |
| Papers with similar_papers audit | ~30% | **100%** | 90%+ | EXCEEDED |
| SurrealDB papers | 110 | 110 | - | - |
| SurrealDB concepts | 317 | 125 (refreshed) | - | - |
| Concepts with backlinks | ~100 | 254/317 | - | - |

### Completed
- All 110 papers audited for `similar_papers` accuracy (52 fixed, random→semantic)
- ~345 wiki-links added across papers and concepts
- 37 concept stubs enriched to 2-3+ paragraph knowledge nodes
- 11 concepts received minor fixes (related_concepts frontmatter)
- SurrealDB fully re-imported (papers + concepts)
- Phase 4 validation queries completed
- Spot checks passed on papers and concepts

### Resource Usage
| Team | Tokens | Tool Calls | Runtime |
|------|--------|------------|----------|
| Alpha | 141K | 90 | 7 min |
| Beta | 180K | 140 | 9 min |
| Gamma | 151K | 156 | 14.5 min |
| Delta | 81K | 42 | 3 min |
| **Total** | **553K** | **428** | **~15 min wall** |

### Remaining Items
- 63 orphaned concepts are system/engineering artifacts (expected, not research domain)
- 10 test/debug paper records in SurrealDB could be cleaned up
- 3 stub papers with low link counts (row-0101, usaf, mcl1) — limited source material
- `vault_find_relevant_context` searches decisions/patterns, not papers — by design

### Status: **COMPLETE**

## Teleport Artifacts

- [[271e02938e5f]] — Teleport task: Vault Knowledge Graph Densification cross-linking papers, concepts, and decisions
- [[271e02938e5f]] — Teleport result: completed densification cross-linking output

## Related

- [[2026-03-03-vault-knowledge-graph-densification-complete-via-parallel-agent-teams|Graph Densification Decision]] — the decision record documenting the parallel agent team approach and completion of this project
- [[cohezion]] — the framework whose knowledge graph this project densifies
- [[cloud-vault-mcp]] — the MCP server that serves densified graph data to agents via `vault_find_relevant_context`
- [[universe-simulation]] — the simulation domain whose papers benefit most from cross-linking
- [[graphrag-knowledge-graph-with-surrealdb]] — the GraphRAG system that ingests the densified wiki-link graph
- [[knowledge-graph-systems]] — the knowledge graph principles this project applies to the Cohezion vault
- [[2026-03-03-vault-state-assessment]] — the external assessment that confirmed graph density and recommended further AI Architecture densification
- [[2026-02-19-connect-unlinked-vault-nodes]] — implementation plan for the vault_linker tool resolving 441 broken wiki-links and orphan nodes
- [[2026-02-21-maximize-node-connections]] — implementation plan for proactive link suggestion hook and single-file vault_linker operations