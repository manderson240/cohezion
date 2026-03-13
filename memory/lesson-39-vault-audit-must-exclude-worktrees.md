---
title: Vault Audit Must Exclude Worktrees
date: 2026-02-24
severity: HIGH
category: vault-integrity
cost_of_forgetting: "Broken link counts inflated 3-5x by worktree artifacts; false positive fixes applied to current content"
tags: [lesson, vault, audit, worktrees, obsidian]
status: active
aspect: knower
neural:
  activation: 0.73
  stage: growing
  synapse_in: 3
  synapse_out: 8
---

# Lesson 39: Vault Audit Must Exclude Worktrees

## Context

During the vault link integrity sprint on 2026-02-24, an automated audit script was run to find and fix broken wiki-links across the vault. The script used `vault.rglob("*.md")` to find all markdown files, then checked each wiki-link for a valid target. The results showed 351 broken link targets -- far more than expected.

## Problem

The audit was including files from `.worktrees/` directories, which are git worktree snapshots of older branch states:

1. **Stale worktree content**: `.worktrees/spec-maximize-node-connections-73e14f48/` contained notes from an older branch where `[[agent context]]` (with a space) had not yet been fixed to `[[agent-context]]` (with a hyphen). This single pattern accounted for 21 "broken" instances.
2. **Worktree-only content**: `.worktrees/daily-notes-wiki-links/` contained experimental notes that only existed on that branch, generating 15 false positives for `[[MCP Infrastructure Architecture]]`.
3. **3-5x inflation**: The actual broken link count (current branch only) was 236, not 351. The 115 extra "broken" links were all in worktree snapshots.

Other non-vault directories also contributed noise: `.obsidian/` contains plugin data with wiki-link-like strings, `node_modules/` contains library markdown, and `tools/` contains Python source code with markdown docstrings.

## Core Learning

Git worktrees (`.worktrees/`) are full copies of the repo at a branch snapshot. Including them in a vault audit inflates broken link counts by 3-5x and produces false positive fixes. Always exclude `.worktrees/`, `.git/`, `node_modules/`, and `tools/` before scanning.

## The Fix

```python
SKIP = {'.worktrees', '.git', '.obsidian', 'node_modules', 'tools'}

all_md = [
    f for f in vault.rglob("*.md")
    if not any(part in SKIP for part in f.parts)
]
```

## Prevention

- **Filter by `f.parts`**: Check directory components, not just path prefix. Subdirectory names can appear anywhere in the path.
- **Exclude `.obsidian/`**: Plugin data contains wiki-link-like strings that are not vault content
- **Exclude `tools/`**: Source code is not vault content
- **Use `rglob` not `glob`**: `glob("*.md")` is non-recursive and misses subdirectories like `concepts/cs249r/`
- **Validate audit scope before running fixes**: Always review the file list before applying automated changes

## Cost of Forgetting

- **3-5x inflated broken link counts** from worktree artifacts
- **False positive fixes** applied to current content based on worktree-only issues
- **Wasted audit time** investigating "broken" links that are artifacts of older branch states

## Do / Don't

- Always filter by `f.parts` (not just prefix) -- subdirectory names can appear anywhere in the path
- Exclude `.obsidian/` -- it contains plugin data with wiki-link-like strings
- Exclude `tools/` -- source code, not vault content
- Never use `glob("*.md")` (non-recursive) -- misses subdirectories like `concepts/cs249r/`
- Never include worktrees -- they are branch snapshots, not current state

## Related

- [[2026-02-24-vault-link-integrity-sprint]]
- [[vault-link-audit-pattern]]
- [[lesson-git-worktrees-multi-session-isolation]] - worktrees provide session isolation but create audit scope hazards
- [[bidirectional-linking]] - vault link integrity depends on correct audit scope
- [[wiki-links]] - wiki-link validation must operate on current branch content only
