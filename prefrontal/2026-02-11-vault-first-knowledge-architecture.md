---
title: "Vault-First Knowledge Architecture"
date: "2026-02-11"
status: proposed
tags: [decision]

decision_reasoning:
  chosen_option: "Adopt vault-first architecture for knowledge management"
  rationale: "Local vault as source of truth enables offline-first workflows and eliminates dependency on external services"
  confidence_score: 0.9
  alternatives_rejected:
    - "Cloud-first (dependency on external services)"
    - "Hybrid (added complexity, sync issues)"
  reasoning_chain:
    - "Recognized vault is primary knowledge store"
    - "Cloud services are secondary (MCP bridge, Sheets)"
    - "Vault-first simplifies architecture and improves resilience"

metrics:
  estimated_cost: 0.0
  estimated_time_hours: 2.0
  actual_cost: 0.0
  actual_time_hours: 1.5
  tokens_used: 0
  cost_per_lesson: 0.0
  lessons_generated:
    - "decisions/2026-02-11-vault-first-knowledge-architecture"
aspect: thinker
neural:
  activation: 0.501
  stage: growing
  cluster: decisions
---

## Context

The Cohezion platform integrates multiple data stores and services: an Obsidian vault (local Markdown files), SurrealDB (graph database), Google Sheets (mobile research capture), and the Cloud Vault MCP server (programmatic access). As the system grew, a critical architectural question emerged: which data store is the source of truth?

Without a clear answer, several problems arose:
- **Sync conflicts**: If a paper's metadata is updated in SurrealDB but not in the vault file, which version is authoritative?
- **Offline fragility**: Cloud-dependent architectures break when the network is unavailable, blocking development sessions entirely
- **Community barriers**: External contributors would need access to SurrealDB, Google Sheets, and MCP to participate -- high friction for a knowledge base that should be simple Markdown
- **Recovery complexity**: If SurrealDB loses data, can it be reconstructed? If vault files are the source of truth, the answer is always yes.

## Decision

Adopt a **vault-first architecture** where the Obsidian vault (local Markdown files with YAML frontmatter) is the single source of truth. All other data stores are derived:

- **SurrealDB** is a derived index: its contents can be fully reconstructed by re-importing vault files
- **Google Sheets** is an intake pipeline: data flows from Sheets into the vault via the [[google-sheets-vault-bridge]], not the reverse
- **Cloud Vault MCP** is a programmatic accessor: it reads from and writes to vault files, not to a separate database
- **Embeddings** are cached computations: regenerated from vault content whenever the model or configuration changes

The vault is git-versioned, human-readable, and requires zero infrastructure to access.

## Consequences

**Positive:**
- **Offline-first**: Development sessions work without any external service running
- **Community-friendly**: Fork the repo, open in Obsidian, contribute via pull request -- no database setup required
- **Recovery is trivial**: `git clone` restores the entire knowledge base; SurrealDB can be rebuilt from vault files
- **Version control built-in**: Every change to knowledge is tracked in git history with author and timestamp
- **Simplifies architecture**: One authoritative store eliminates sync conflict resolution logic

**Negative:**
- **Query performance**: Complex graph queries must scan Markdown files or rely on the SurrealDB derived index; vault files alone do not support sub-millisecond graph traversals
- **Schema evolution**: Changing frontmatter schema requires updating all existing vault files (no ALTER TABLE equivalent)
- **Concurrent writes**: Multiple agents modifying the same vault file risk merge conflicts (mitigated by atomic notes and git branching)

## Alternatives Considered

### Alt 1: Cloud-First (SurrealDB as Source of Truth)
- **Rejected**: Creates dependency on running SurrealDB for all operations. If the database is lost, knowledge is lost. External contributors need database access. Violates the principle that knowledge should be portable and human-readable.

### Alt 2: Hybrid (Dual Source of Truth)
- **Rejected**: Dual-write systems inevitably diverge. Sync conflict resolution adds complexity proportional to the number of writes. The "which version is correct?" question has no automated answer when both stores are authoritative.

### Alt 3: Google Sheets as Coordination Layer
- **Rejected**: Sheets is excellent for mobile capture and tabular views but terrible for rich text, wiki-links, and git versioning. It would constrain the knowledge model to a flat table rather than an interconnected graph.

## See Also

- [[mcp-infrastructure-architecture]]
- [[mcp-model-context-protocol]]
- [[compound-engineering]]
- [[google-sheets-vault-bridge]]

## Related

- [[cohezion]] — the framework built on vault-first principles; persistent knowledge base is its foundational layer
- [[Obsidian-Best-Practices-for-AI-Agents]] — operational best practices for AI agents working with the vault-first architecture
- [[cloud-vault-mcp]] — the MCP server that provides programmatic access to the vault-first knowledge store
