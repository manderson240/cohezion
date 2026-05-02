---
title: "Wiki Links"
date: 2026-02-19
tags: [concept]
aspect: knower
neural:
  activation: 1.0
  stage: mature
  synapse_in: 21
  synapse_out: 30
---
## Definition

Wiki-links are Obsidian's internal linking syntax using double brackets (`[[note-name]]`) to create navigable connections between notes. They form a bidirectional graph where each link creates both a forward reference and a backlink, enabling traversal in either direction. Unlike standard Markdown links, wiki-links are resolved by note filename rather than file path, making them resilient to directory reorganization.

The wiki-link concept traces its origins to Ward Cunningham's WikiWikiWeb (1995), the first user-editable website, where `CamelCase` words automatically became links to other pages. Obsidian adapted this pattern using double-bracket syntax (`[[note-name]]`), combining it with Niklas Luhmann's Zettelkasten principle that relationships between ideas are more important than hierarchical organization. The result is a knowledge system where structure emerges from connections rather than being imposed by folder trees.

## Key Properties

- **Bidirectional**: Every `[[target]]` link automatically creates a backlink in the target note's backlink panel. This means that creating a link from Note A to Note B simultaneously creates a discoverable reference from B back to A -- no manual maintenance required.
- **Filename-resolved**: Links match by note name, not path -- moving files between directories preserves connections. This makes the vault robust to reorganization, a property that hierarchical file systems lack.
- **Alias support**: `[[note-name|Display Text]]` allows readable text while maintaining the graph edge. Aliases are essential for natural-language prose where the note filename is too technical or too long.
- **Graph-native**: Obsidian renders wiki-links as edges in its built-in graph view and the 3D graph plugin. Each link is simultaneously a navigable hyperlink and a graph edge.
- **Machine-parsable**: Simple regex extraction (`\[\[([^\]]+)\]\]`) enables programmatic graph analysis. This enables tools like the [[surrealdb|SurrealDB]] import pipeline and graph densification scripts to process the vault's link structure algorithmically.
- **Unlinked mentions**: Obsidian can detect references to a note's name in other notes even when no explicit `[[link]]` exists, surfacing opportunities to add missing connections.

## Link Types in Practice

| Syntax | Purpose | Example |
|--------|---------|---------|
| `[[note]]` | Direct link | `[[quantum-entanglement]]` |
| `[[note\|alias]]` | Link with display text | `[[quantum-entanglement\|entanglement]]` |
| `[[note#heading]]` | Link to specific section | `[[concept#Key Properties]]` |
| `[[note#^blockid]]` | Link to specific block | `[[concept#^definition]]` |
| `![[note]]` | Embed (transclude) content | `![[concept#Definition]]` |

## Vault Conventions for Wiki-Links

In the Cohezion vault, wiki-links follow specific conventions:
1. **Bare-name links**: Use `[[bare-name]]` without directory prefixes (e.g., `[[quantum-sensors]]` not `[[cortex/quantum-sensors]]`)
2. **Full date prefix**: When a note has a date prefix, include it (e.g., `[[2026-02-19-feature-name]]`)
3. **First-mention linking**: Link at the first mention of a [[concept]] in a note, not every mention
4. **Atomic linking**: Each link should point to a single [[concept]] note, not a combined page

## Examples

- `[[surrealdb]]` links directly to the SurrealDB concept note
- `[[laboratory/2026-02-10-phase3a-3d-graph-validation|Phase 3A Validation]]` links with an alias for readability
- `[[transformer-architecture]]` links to the transformer architecture concept from a paper discussing attention mechanisms

## Related Papers

- [[2026-02-07-event-driven-inbox-processor]]
- [[2026-02-09-decisions-experiments-integration]]
- [[2026-02-09-lessons-integration-complete]]
- [[session-retrospective-notes]]

## Navigation

- [[MOC-vault-architecture]] — Map of Content for the vault architecture topic area

## Related Concepts

- [[knowledge-graph-systems]] — wiki-links form the human-readable graph layer parallel to SurrealDB
- [[concept-modularity]] — modular notes use wiki-links for relationships rather than embedding content

- [[inbox-triager]] — the inbox triager adds wiki-links when moving notes to permanent directories
- [[bidirectional-linking]] — the practice of maintaining reciprocal wiki-links between connected notes
- [[knowledge-graph-densification]] — densification sprints systematically add wiki-links to increase graph connectivity
- [[decision-linker]] — automated tool that creates typed wiki-links between decision notes

## Primary Sources

- Ward Cunningham (1995). *WikiWikiWeb*. The first wiki, establishing the concept of user-editable linked pages. [https://wiki.c2.com/](https://wiki.c2.com/)
- Obsidian Documentation. *Internal Links*. [https://help.obsidian.md/Linking+notes+and+files/Internal+links](https://help.obsidian.md/Linking+notes+and+files/Internal+links)
- Niklas Luhmann (1981). *Communicating with Slip Boxes*. Established the principle that linking is more important than categorizing in knowledge systems.

## Relevance to Cohezion

Wiki-links are the foundational linking mechanism in the Cohezion vault. They create the dual-layer knowledge graph: a human-navigable Obsidian graph and a machine-parsable edge set that feeds into the [[surrealdb|SurrealDB]] import pipeline. The vault [[knowledge-graph-densification]] project specifically targets increasing wiki-link density to strengthen both layers.

For AI agents operating in the vault, wiki-links serve a dual purpose: they provide [[semantic-search|semantic context]] for retrieval (notes linked to the current context are likely relevant) and they encode expert knowledge about relationships between concepts that pure embedding similarity might miss. A well-linked vault produces better agent reasoning than a sparsely connected one.

## Daily References

- [[SESSION-63-FINAL-SUMMARY-2026-02-15]]
- [[SESSION-2026-02-10-WORK-SUMMARY]]
- [[PHASE-2-DEPLOYMENT-COMPLETION-2026-02-14]]

## Skills

- OBSIDIAN_VAULT_INTEGRATION_PRIME — Bidirectional linking best practices
