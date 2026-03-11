---
title: "GraphRAG Phase 1: SQL syntax errors block imports"
date: "2026-02-12"
status: complete
tags: [experiment, graphrag, surrealdb, sql, debugging]
aspect: thinker
neural:
  activation: 0.638
  stage: growing
  cluster: experiments
---

# GraphRAG Phase 1: SQL Syntax Errors Block Imports

## Hypothesis

SurrealDB SQL syntax differences from standard SQL would cause import failures when bulk-loading vault knowledge graph data during GraphRAG Phase 1. Specifically, SurrealDB's SurrealQL has unique syntax for record IDs, relation definitions, and CONTENT/SET clauses that diverge from standard SQL and would require adaptation of auto-generated import scripts.

## Method

1. Attempted bulk import of vault papers, concepts, and relationships into SurrealDB using auto-generated SurrealQL statements
2. Collected and categorized all SQL syntax errors encountered during import
3. Identified root causes: YAML frontmatter parsing issues (especially folded scalars), unescaped special characters in record IDs, and SurrealQL-specific syntax requirements
4. Fixed each error category systematically, validating individual statements before re-running batch imports
5. Verified final import via SurrealDB query validation against expected node and edge counts

## Results

- **Root cause categories identified**:
  - YAML folded scalar trap ([[lesson-24-yaml-folded-scalar-trap]]) — multiline strings in frontmatter were silently truncated, producing malformed SurrealQL
  - SurrealDB record ID format requires specific escaping for special characters (hyphens, spaces)
  - RELATE statements require different syntax from INSERT for graph edges
  - CONTENT clause vs. SET clause distinction not consistently applied
- **Resolution**: All syntax errors resolved by building a robust SurrealQL statement generator that handles frontmatter edge cases, properly escapes record IDs, and uses the correct clause syntax per statement type
- **Import completed**: Full vault graph imported successfully after fixes

## Learnings

1. **SurrealQL is not SQL** — despite surface similarity, SurrealDB's query language has enough divergences that treating it as standard SQL guarantees failures. Always consult SurrealDB-specific documentation.
2. **YAML parsing is a minefield** — folded scalars, block scalars, and multi-line strings in frontmatter require defensive parsing. Test with adversarial frontmatter samples.
3. **Batch vs. individual validation** — running individual SurrealQL statements first catches syntax errors before they cascade in batch imports.
4. **Record ID escaping** — SurrealDB record IDs with special characters need backtick escaping (`\`record-id\``), which is easy to miss in auto-generation.

## Related

**Decisions**: [[2026-02-11-adopt-graphrag-for-vault-knowledge-graph]], [[2026-02-12-phase1-complete-vault-and-surrealdb-integration]]
**Patterns**: [[graphrag-knowledge-graph-with-surrealdb]], [[surrealdb-query-driven-analysis]]
**Concepts**: [[mcp-infrastructure-architecture]], [[surrealdb]], [[graph-databases]]
**Lessons**: [[lesson-05-surrealdb]], [[lesson-24-yaml-folded-scalar-trap]]
**Experiments**: [[2026-02-11-graphrag-proof-of-concept-success]], [[2026-02-12-graphrag-implementation-session-56]]

## Related Concepts

- [[2026-02-11-entire-io-api-investigation]]
- [[2026-02-11-phase1-production-validation-results]]
- [[2026-02-12-session-56-compact-retrospective]]
- [[2026-02-17-spec-verify-token-efficiency-analysis]]
- [[2026-02-14-session-58-7-phase-journey-enrichment-3-agent-adversarial-review]]
- [[2026-02-19-journal-vacuum-during-crash-loop-recovery]]
- [[2026-02-11-large-repositories-26gb-with-virtual-environment-files-wi]]
- [[2026-02-13-git-filter-repo-can-reduce-65gb-git-repository-to-5gb-by-r]]
