---
type: antigravity-artifact
session_id: 79dcc0e1-d6a5-4401-8b10-c47abe6b23dd
date: 2026-03-04
title: "Implementation Plan"
aspect: doer
neural:
  activation: 0.355
  stage: embryo
  cluster: Agents
---

# Antigravity IDE Hooks and BMAD Traceability Loop

This plan addresses the requirement to ensure all work loops back through PRD, Architecture, Epics, and Stories, and that all Antigravity artifacts are persisted to the Obsidian Vault.

## Proposed Changes

### 1. File Watcher Daemon (Antigravity Vault Sync)

We will create a lightweight background script using `watchdog` that monitors the `/home/mike-anderson/.gemini/antigravity/brain/` directory for new artifacts (e.g., `implementation_plan.md`, `walkthrough.md`, `task.md`).

#### [NEW] `src/cohezion/hooks/antigravity_sync_daemon.py`

This script will:

- Detect when Antigravity finishes a session (e.g., when a `walkthrough.md` is generated or when the session transitions to `notify_user` with completed tasks).
- Automatically copy all markdown and image artifacts from the `.gemini` brain directory to `/home/mike-anderson/vaults/cohezion-vault/Agents/Antigravity/{session_id}/`.
- Embed metadata frontmatter into the synced artifacts matching the Obsidian vault's required properties (e.g., `type: antigravity-artifact`, `date: YYYY-MM-DD`).

### 2. BMAD Traceability Hook

To ensure everything loops back through PRD, Architecture, Epics, and Stories, the daemon will use a Traceability Analyzer.

#### [NEW] `src/cohezion/hooks/bmad_traceability.py`

This module will:

- Parse `.gemini` generated artifacts (`task.md`, `walkthrough.md`) to extract mentioned Epics, Stories, PRDs, and Architecture documents.
- If an Epic (e.g., `EPIC-101`) or Story is mentioned, it will locate that Epic/Story in the Obsidian Vault.
- Append a standard block to the bottom of the Epic/Story/PRD file in the Vault:
  ```markdown
  ## Antigravity Implementation ({Date})

  - [Implementation Plan](obsidian://open?vault=cohezion-vault&file=Agents/Antigravity/{session}/implementation_plan.md)
  - [Walkthrough](obsidian://open?vault=cohezion-vault&file=Agents/Antigravity/{session}/walkthrough.md)
  ```
- This perfectly matches the "Compound Engineering" principle by persistently tracking work.

### 3. Workflow Trigger for Manual Enforcement

For cases where manual enforcement is preferred or the daemon is paused, we will add a slash command workflow.

#### [NEW] `.agent/workflows/bmad-antigravity-sync.md`

A workflow defining the `/bmad-antigravity-sync` command, instructing agents to run `uv run src/cohezion/hooks/antigravity_sync_daemon.py --sync-now` to flush artifacts to the Vault immediately.

## Verification Plan

### Automated Tests

- Unit test the traceability parser to verify it correctly extracts Epic and Story IDs from markdown text.
- Mock the file system to verify the Obsidian Vault artifact copying correctly preserves images and generates valid JSON Canvas or Markdown files.

### Manual Verification

1. I will run a simulated task completion to generate a mock `walkthrough.md` referencing `EPIC-10-honest-status`.
2. Ensure the daemon correctly creates the artifact in `/home/mike-anderson/vaults/cohezion-vault/Agents/Antigravity/`.
3. Check that the original `EPIC-10-honest-status.md` in the Vault is modified to include the Antigravity backlink.

## Related Vault Notes

- [[cohezion]]
- [[compound-engineering]]
