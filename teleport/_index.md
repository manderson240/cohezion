---
title: "Teleport — Directory Index"
purpose: "Cloud-to-local file synchronization tasks and their results"
type: directory-index
neural:
  activation: 0.3
  stage: embryo
  synapse_in: 0
  synapse_out: 0
---

# Teleport

**Purpose:** Manages cloud-to-local file sync operations via the Cloud Vault MCP Teleport tool.

**Put here when:** A teleport sync task is created (tasks/) or completed (results/).

**Naming:** `<hash-id>.md` (auto-generated hash IDs) or descriptive names like `bmad-analysis.md`

**Required frontmatter:** Auto-populated by the Teleport MCP tool.

**Current count:** 24 notes (12 tasks, 12 results)

**Subdirectories:**
- `tasks/` — Pending or in-progress sync task definitions
- `results/` — Completed sync results with output data

**Workflow:**
1. Task created in `tasks/<id>.md` via MCP
2. Sync executes cloud-to-local transfer
3. Result written to `results/<id>.md` with outcome
