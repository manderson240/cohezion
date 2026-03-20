---
title: "MOC — Vault Architecture"
date: 2026-03-04
tags: [moc, navigation, vault-architecture, triune-self, surrealdb]
aspect: knower
neural:
  activation: 1.0
  stage: mature
  synapse_in: 17
  synapse_out: 38
---

# Map of Content — Vault Architecture

## Overview

Vault architecture covers the structural design of the Cohezion knowledge base: organized as a **living brain** via the Triune Self architecture (Knower / Thinker / Doer / Connective). Notes are organized, linked, validated, and queried. Includes wiki-link conventions, knowledge graph densification strategies, the GraphRAG integration with SurrealDB 3.0, neural frontmatter, the Dreaming Engine, and HIHO coherence thresholds.

## The Triune Self Architecture

- [[VAULT_MANIFEST]] — Master map of the Triune architecture, routing rules, and conventions
- [[metabolism-dashboard]] — Vault-wide health: Country health, lifecycle distribution, HIHO events
- [[knowledge-graph-densification]] — Strategies for adding missing cross-links to reduce orphan nodes

## Core Concepts

- [[wiki-links]] — Obsidian's bidirectional linking syntax and how it creates a traversable graph
- [[knowledge-graph-systems]] — Graph-based knowledge representation combining nodes, edges, and semantic metadata
- [[knowledge-graph-densification]] — Strategies for adding missing cross-links to reduce orphan nodes
- [[graphrag-knowledge-graph-with-surrealdb]] — Combining retrieval-augmented generation with SurrealDB graph queries
- [[semantic-search]] — Finding notes by meaning rather than exact text match, using embeddings
- [[concept-modularity]] — Keeping notes atomic and composable for reuse across contexts
- [[concept-validation]] — Verifying that concept notes are well-formed, linked, and semantically coherent
- [[concept-testing]] — Automated checks that vault structure meets quality standards
- [[concept-caching]] — Caching resolved concept lookups to avoid repeated vault traversals
- [[concept-isolation]] — Ensuring concept notes are self-contained without implicit dependencies
- [[concept-versioning]] — Tracking semantic evolution of concepts over time via git history and frontmatter metadata
- [[cybernetics]] — The vault IS a cybernetic system: Beer's Viable System Model maps to vault-keeper (S2), task management (S3), research pipeline (S4)

## Infrastructure

- [[cloud-vault-mcp]] — MCP server on port 8360 providing programmatic vault read/write access
- [[mcp-infrastructure-architecture]] — The broader MCP infrastructure connecting agents to vault services
- [[surrealdb]] — Multi-model database storing the vault's knowledge graph with graph traversal support
- [[graph-databases]] — General principles of graph storage, traversal, and query languages
- [[api-design]] — Design conventions for the vault's programmatic interfaces

## Key Decisions

- [[2026-02-11-adopt-graphrag-for-vault-knowledge-graph]] — Decision to use GraphRAG pattern for vault knowledge retrieval
- [[2026-02-12-session-57-graphrag-complete-phases-1-4-delivered]] — Delivery of first four GraphRAG integration phases
- [[2026-02-13-next-10-phases-graphrag-roadmap]] — Roadmap for phases 5-14 of GraphRAG integration
- [[2026-03-03-vault-knowledge-graph-densification-complete-via-parallel-agent-teams]] — Densification sprint completed using parallel agent teams
- [[2026-02-17-singleton-consolidation-mandatory-during-file-splits]] — Rule for consolidating singletons when splitting large files

## Patterns

- [[safe-file-split-checklist]] — Step-by-step checklist for safely splitting large vault notes without breaking links
- [[session-retrospective-notes]] — Template for capturing session learnings as structured vault notes
- [[pattern-compound-engineering]] — Layered engineering approach applied to vault tooling design
- [[agent-logs-vault-schema]] — Schema for storing agent execution context as vault notes with frontmatter linking sessions to decisions and lessons
- [[lessons-graph-integration]] — Hybrid local-cloud pattern for integrating the lessons corpus bidirectionally into the knowledge graph via semantic analysis
- [[vault-first-session-protocol]] — Protocol for persisting session artifacts at each lifecycle point; prevents context-window knowledge loss
- [[parallel-session-coordination-via-vault-registry]] — Vault as shared session registry for multi-agent conflict avoidance; uses SurrealDB `owns` relations

## Research Papers

- [[knowledge-graph-semantic-relationships]] — Ontological modeling of semantic relationships in knowledge graphs
- [[knowledge-graphs-semantic-web]] — Survey of knowledge graph techniques from the Semantic Web tradition
- [[surrealdb-graph-databases]] — SurrealDB's graph-native multi-model architecture and query capabilities
- [[schema-design-relational]] — Relational schema design principles applied to structured vault data

## Lessons Learned

- [[lesson-surrealdb-schema-design]] — Hard-won lessons from designing the SurrealDB schema for the vault graph

## Projects

- [[vault-knowledge-graph-densification]] — Active project tracking cross-linking of papers, concepts, and decisions
- [[2026-03-04-vault-assessment-v3]] — Third vault assessment evaluating portfolio deadline impact on memory architecture
- [[2026-03-03-vault-as-platform-memory-recommendations]] — Six recommendations for strengthening vault-as-platform-memory: platform spine, machine-readable lessons, link typing, session memory protocol, intake separation, and memory API

## Experiments

- [[2026-02-11-graphrag-proof-of-concept-success]] — Initial proof that GraphRAG retrieval outperforms flat search on vault queries

## Agent Orientation

- VAULT_MANIFEST — The single-source-of-truth map that agents read at session start for directory routing, conventions, and entry points
- Each directory has a `_index.md` file — read any directory's index to understand its purpose and key notes

## Start Here

- **New to this topic?** Start with [[wiki-links]] to understand the linking primitive, then [[knowledge-graph-systems]] for the bigger picture
- **Agent onboarding?** Read VAULT_MANIFEST for the full vault map, then load the relevant MOC for your task
- **Looking for patterns?** See [[safe-file-split-checklist]] for the most frequently used vault maintenance pattern
- **Recent work:** [[2026-03-03-vault-knowledge-graph-densification-complete-via-parallel-agent-teams]] documents the latest densification sprint

## Related Maps

- [[MOC-agentic-ai]] — Agents that read from and write to the vault via MCP
- [[MOC-machine-learning]] — ML techniques (embeddings, semantic search) that power vault retrieval
- [[MOC-triune-self]] — The brain-inspired directory architecture (Knower/Thinker/Doer/Connective)
