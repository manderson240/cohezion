---
title: Inbox Triager
date: 2026-02-23
tags: [tool, compound-engineering, agent-workflow, automation]
status: active
aspect: knower
neural:
  activation: 0.7
  stage: growing
  synapse_in: 6
  synapse_out: 7
---

# Inbox Triager

An agent tool within the Cohezion compound engineering framework that processes raw inbox notes, researches their topics via web search and vault context, classifies them into the appropriate vault directory, applies proper YAML frontmatter, and inserts cross-referencing wiki-links. The triager transforms unstructured capture into structured, connected knowledge.

## How It Works

1. **Scan** — Reads all notes in `inbox/` and evaluates content type, length, and topic signals
2. **Research** — For thin or ambiguous notes, performs web search and vault-internal semantic search to gather context
3. **Classify** — Determines the target directory (`concepts/`, `papers/`, `decisions/`, `patterns/`, `experiments/`, `projects/`) based on content structure and topic
4. **Enrich** — Generates YAML frontmatter (title, date, status, tags as arrays) following the vault's schema conventions
5. **Link** — Inserts bidirectional wiki-links to related existing notes, strengthening the knowledge graph
6. **Move** — Relocates the note from `inbox/` to the target directory with the enriched content

## Key Design Decisions

- **Non-destructive:** The original inbox note content is preserved; the triager adds structure around it rather than rewriting
- **Research-backed:** Thin notes are expanded with researched content before classification, preventing stubs from accumulating in permanent directories
- **Template-aware:** Each target directory has a `_template.md`; the triager uses the appropriate template structure when enriching notes
- **Idempotent:** Running the triager on an already-processed note produces no changes

## Sources

- Internal vault pattern derived from Zettelkasten inbox processing workflows
- [Obsidian Community: Inbox Processing](https://forum.obsidian.md/t/link-notes-but-how/58831)

## Related

- [[compound-engineering]] — the inbox triager is a tool within the compound engineering agent framework
- [[cohezion]] — part of the Cohezion knowledge persistence system
- [[concept-automation]] — the triager is a specific instance of concept automation, auto-classifying and structuring notes
- [[wiki-links]] — the triager adds wiki-links when moving notes, strengthening the knowledge graph
- [[decision-linker]] — complementary agent tool; the triager routes notes while the linker connects them semantically
- [[bidirectional-linking]] — the triager implements bidirectional linking by inserting wiki-links in both the moved note and related targets
- [[knowledge-graph-densification]] — each triaged note adds new nodes and edges to the vault's knowledge graph

## Relevance to Cohezion

The inbox triager operationalizes the vault's capture-triage-link workflow. By automating the transition from raw capture to structured knowledge, it reduces the manual overhead of vault maintenance and ensures consistent frontmatter, cross-linking, and directory placement across all notes processed by the compound engineering pipeline.
