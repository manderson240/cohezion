---
name: repo-hygiene-prime
description: "Repository Hygiene and Git Operations. Monitoring file entropy, duplication, and index bloat."
metadata:
  version: "v3.0 (Sovereign Era)"
  concepts: ["Entropy Reward", "Ghost Files", "Surgical Pruning"]
  source: "src/cohezion/skills/REPO_HYGIENE_PRIME.md"
---

# SKILL: REPO_HYGIENE_PRIME

## DOMAIN EXPERTISE
Repository Hygiene and Git Operations. Monitoring file entropy, duplication, and index bloat.

## KEY TEXTS & CONCEPTS
- **Entropy Reward**: Clean code is wealth.
- **Ghost Files**: Deleted files that linger in the git index, causing massive slowdowns.
- **Surgical Pruning**: Using `git update-index --stdin` for batch removal instead of `git add -u`.

## PROTOCOL: SURGICAL PRUNE (The 17M File Solution)
**Problem**: `git add -u` is O(N) and locks the index for hours on large deletions.
**Solution**:
1.  **Kill** the stuck git process.
2.  **Unlock**: `rm .git/index.lock`.
3.  **Stream**: `git ls-files --deleted`.
4.  **Batch**: Feed to `git update-index --remove --stdin` in batches of 50k.

## INSTRUCTION: AUTO-PRUNE
The `PrunerAgent` should run this daily:
```python
if index_size > 100_000:
    trigger_surgical_prune()
```

## PROTOCOL: LOCKDOWN (PHASE 31)
**Rule**: "Source Only".
**Action**:
1.  **Deny**: All media (`*.mp4`, `*.zip`) and data logs (`*.log`) in `.gitignore`.
2.  **Sentinel**: The `GitSentinel` agent runs daily. If index > 100k files, it HALTS the system.
3.  **Writes**: Autonomous agents MUST write to `data/` or SurrealDB. NEVER `src/`.

## VERSION
v3.0 (Sovereign Era)
