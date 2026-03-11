---
title: "Canvas — Directory Index"
purpose: "Standalone visual canvases — spatial relationship maps, architecture diagrams, decision landscapes"
type: directory-index
aspect: connective
neural:
  activation: 0.370
  stage: embryo
  cluster: canvas
---

# Canvas

**Purpose:** Standalone `.canvas` files that span multiple topics or don't belong to a single note. Canvases that companion a specific note live alongside that note (e.g., `decisions/2026-03-05-vault-surrealdb-architecture.canvas`).

**Naming:** `kebab-case-descriptive-name.canvas`

## Current Canvases

### Standalone (this directory)

| Canvas | Nodes | Edges | Content |
|--------|-------|-------|---------|
| `cohezion-architecture.canvas` | 33 | 18 | Full system architecture: orchestration, MCP, backend, vault, methodology |
| `papers-knowledge-graph.canvas` | 165 | 483 | All papers with cross-reference edges |

### Companion Canvases (alongside notes)

| Canvas | Companion Note | Content |
|--------|---------------|---------|
| `decisions/2026-03-05-vault-surrealdb-architecture.canvas` | [[2026-03-05-vault-surrealdb-architecture]] | Three-layer sync pipeline diagram |
| `specs/specs-landscape.canvas` | [[2026-03-05-vault-as-system-of-record]] | Full specs landscape: skills, agents, MCP, tools, integrations, cards (system, model, agent, embedding) |

## What Deserves a Canvas?

| Domain | When to Create | Type |
|--------|---------------|------|
| **Architecture decisions** | System has 3+ interacting layers | Layer diagram with groups and edges |
| **Research papers** | Paper cluster has 5+ cross-references | Relationship map with file nodes |
| **Experiments** | Experiment has decision tree or multiple outcomes | Decision flow with outcome cards |
| **Project PRDs** | Project has 3+ epics with dependencies | Epic/story dependency map |
| **Specs landscape** | System definitions span 3+ categories | Category groups with key components |
| **MOC visualization** | MOC has 10+ linked notes | Spatial cluster map |
| **Primary references** | Research lineage spans 3+ source papers | Citation network with file nodes |
| **Final reports** | Report synthesizes 5+ sources | Evidence map linking claims to sources |

**Related:** See VAULT_MANIFEST.md "Canvas Files" section for JSON format spec and layout tips.
