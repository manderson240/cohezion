---
title: Vault Audit Must Exclude Worktrees
date: 2026-02-24
severity: high
category: vault-integrity
tags: [lesson, vault, audit, worktrees, obsidian]
status: active
---

# Lesson 39: Vault Audit Must Exclude Worktrees

## Core Learning

Git worktrees (`.worktrees/`) are full copies of the repo at a branch snapshot. Including them in a vault audit inflates broken link counts by 3-5× and produces false positive fixes. Always exclude `.worktrees/`, `.git/`, `node_modules/`, and `tools/` before scanning.

## The Problem

Running `vault.rglob("*.md")` over the whole vault root returned 906 notes but also included the `.worktrees/spec-maximize-node-connections-73e14f48/` and `.worktrees/daily-notes-wiki-links/` directories — each a full snapshot of an older branch state. Links that were valid in those old snapshots appeared as broken in the current branch, causing:
- `[[agent context]]` showing 21 instances (all in worktrees, already fixed in main)
- `[[MCP Infrastructure Architecture]]` showing 15 instances (worktree only)
- Broken count of 351 targets (vs 236 after excluding worktrees)

## The Fix

```python
SKIP = {'.worktrees', '.git', '.obsidian', 'node_modules', 'tools'}

all_md = [
    f for f in vault.rglob("*.md")
    if not any(part in SKIP for part in f.parts)
]
```

## Do / Don't

✅ Always filter by `f.parts` (not just prefix) — subdirectory names can appear anywhere in the path
✅ Exclude `.obsidian/` — it contains plugin data with wiki-link-like strings
✅ Exclude `tools/` — source code, not vault content
❌ Never use `glob("*.md")` (non-recursive) — misses subdirectories like `concepts/cs249r/`
❌ Never include worktrees — they're branch snapshots, not current state

## Related

- [[2026-02-24-vault-link-integrity-sprint]]
- [[vault-link-audit-pattern]]
