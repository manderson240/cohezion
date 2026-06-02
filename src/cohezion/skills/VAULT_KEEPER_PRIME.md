---
name: vault-keeper-prime
description: "Expert in Obsidian-style knowledge vault maintenance. Specializes in graph health monitoring, orphan detection, frontmatter enforcement, and brain-region vault organization for the Cohezion knowledge system."
---

# SKILL: VAULT_KEEPER_PRIME

## DOMAIN EXPERTISE
Expert in **Obsidian-style knowledge vault maintenance**. Specializes in graph health monitoring, orphan detection, frontmatter enforcement, and brain-region vault organization for the Cohezion knowledge system.

## KEY TEXTS & CONCEPTS
- **Brain-Region Architecture**: cerebellum (procedural), cortex (analytical), prefrontal (strategic), hippocampus (episodic/archive).
- **Graph HIHO Metric**: Composite health score from connectivity (>0.8), reciprocity (>0.6), freshness (>0.3), orphan ratio (<0.1).
- **Wikilink Integrity**: Bidirectional `[[links]]` are the vault's connective tissue. Broken links = knowledge decay.
- **Frontmatter Enforcement**: Every note needs `tags`, `created`, `updated`, `status` in YAML frontmatter.
- **Stale Note Archival**: Notes untouched >90 days move to `hippocampus/archive/` (never deleted).

## INSTRUCTION

1. **Run Health Diagnostics**:
   Use MCP tools `graph_stats()` and `vault_health_check()` to get current vault metrics. Parse the response for orphan count, broken links, and connectivity scores.

2. **Detect Orphan Notes**:
   Scan all `.md` files in the vault. For each file, grep all other files for `[[filename]]` references. Zero matches = orphan. Collect into a report sorted by age (oldest first -- most likely to archive).

3. **Enforce Frontmatter**:
   ```yaml
   ---
   tags: [brain-region, topic]
   created: 2026-01-15
   updated: 2026-03-27
   status: active
   ---
   ```
   Missing fields get sensible defaults: `created` from git log, `updated` from file mtime, `status: active`.

4. **Archive Stale Notes**:
   Move experiments older than 90 days from `hippocampus/experiments/` to `hippocampus/archive/`. Update any wikilinks pointing to moved files.

5. **Fix Broken Wikilinks**:
   For each broken `[[link]]`, search for fuzzy matches (case-insensitive, partial). Suggest corrections or flag for manual review.

6. **Reindex SurrealDB**:
   After structural changes (moves, renames, deletes), trigger reindex via `maintenance-mcp` to keep the graph database in sync with the vault filesystem.

7. **Report Graph HIHO**:
   Calculate and report: `HIHO = mean(connectivity, reciprocity, freshness, 1 - orphan_ratio)`. Target: >0.6 overall.

## PATTERNS
- Run health check weekly or after bulk vault operations
- Archive before reindex (reduces noise in graph)
- Fix broken links before calculating HIHO (inflates orphan count otherwise)

## ANTI-PATTERNS
- Deleting notes instead of archiving (knowledge loss)
- Ignoring orphans (graph fragmentation)
- Reindexing without fixing broken links first (propagates errors)

## VERSION
v1.0

## SEE ALSO
SURREALDB_ADVANCED_PRIME, CONNECTIVITY_GUIDE_PRIME, DATABASE_PRIME
