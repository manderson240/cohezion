---
title: "Decision Vault First Knowledge Architecture"
date: 2026-02-19
tags: [concept]
aspect: knower
neural:
  activation: 0.77
  stage: growing
  synapse_in: 4
  synapse_out: 6
---
## Definition

The vault-first knowledge architecture decision established that the Obsidian vault (Markdown files with YAML frontmatter and wiki-links) is the primary source of truth for all Cohezion knowledge, with databases (SurrealDB) and APIs (MCP servers) serving as derived indexes rather than primary stores. This means new knowledge is always written to vault files first, then imported into SurrealDB and exposed via MCP tools — never the reverse.

## Key Properties

- **Markdown as source of truth**: All knowledge lives in version-controlled `.md` files with structured frontmatter
- **Databases as derived indexes**: SurrealDB imports from vault files; the vault is never generated from the database
- **Human-readable first**: Knowledge must be readable by humans in Obsidian before it is optimized for machine consumption
- **Git-versioned**: All knowledge changes are tracked through git, providing full audit history
- **Schema at the file level**: Frontmatter YAML schemas (tags, date, status, related_concepts) define the structured layer atop free-text Markdown

## Examples

- Agent logs are written to vault files with structured frontmatter, then the schema is imported into SurrealDB (see [[agent-logs-vault-schema]])
- Schema design for Phase 2 was driven by vault note structure, not database-first modeling (see [[2026-02-12-phase-2-schema-design]])

## Related Papers

- [[2026-02-11-phase1-step1-schema-complete]]
- [[2026-02-12-phase-2-schema-design]]
- [[agent-logs-vault-schema]]

## Related Concepts

- [[knowledge-graph-systems]] — the vault-first architecture creates a dual-layer graph (human-readable + machine-queryable)
- [[surrealdb]] — the derived database that indexes vault content
- [[decision-phase-1-surrealdb-agent-context]] — the subsequent decision that built on this architecture

## Relevance to Cohezion

This decision is one of the earliest and most consequential architectural choices in the Cohezion framework. By keeping Markdown as the source of truth, the system avoids database lock-in, maintains human readability, and enables git-based collaboration — while still providing the graph query and vector search capabilities that agents need through the derived SurrealDB layer.
