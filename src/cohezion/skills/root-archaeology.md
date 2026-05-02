---
skill_id: root-archaeology
name: Root Archaeology
description: Systematic repo root cleanup for professional presentation
category: maintenance
difficulty: beginner
v_model_phase: 1  # Requirements
---

# Root Archaeology

**Trigger**: Repository root has 50+ items, preparing for public release, or onboarding friction complaints.

**Goal**: Reduce root items to 20-40 while preserving all history.

## Prerequisites

- Git worktree with clean main branch
- Understanding of project structure
- No open feature branches using root files

## Steps

### 1. Inventory (5 min)
```python
import os
items = [f for f in os.listdir('.') if not f.startswith('.git')]
categories = {
    'essential': [],      # README, LICENSE, src/, tests/, docs/
    'research': [],         # Competition outputs, papers
    'project_docs': [],     # Guides, architecture docs
    'sessions': [],          # Status reports, handoffs
    'infrastructure': [],    # Docker, k8s, deployment
    'data': [],            # Artifacts, submissions
    'archives': [],        # Old backups, experiments
}
```

### 2. Define Filing System

| Category | Destination | Example |
|----------|-------------|---------|
| Competition outputs | `research/challenges/<competition>/` | aimo/, birdclef/ |
| Research papers | `research/papers/` | THEORY_OF_EVERYTHING.md |
| Project guides | `docs/project/` | ARCHITECTURE.md, QUICKSTART.md |
| Session reports | `docs/sessions/{recent,archive}/` | HANDOFF_*.md |
| Data artifacts | `data/external/` | submission.jsonl |
| Docker configs | `infrastructure/docker/` | Dockerfile, compose |
| Dev tools | `.config/development/` | .vscode/, .zed/ |
| Old backups | `archives/backups/` | v20_meta/, debug_logs/ |

### 3. Execute (No Deletions)

**CRITICAL**: Use `git mv` for tracked files, `mv + git add` for untracked.

```bash
# Batch by category - commit after each
mkdir -p research/challenges docs/project docs/sessions infrastructure

# Competition outputs
git mv aimo_v22_final research/challenges/aimo/
git mv birdclef-baseline research/challenges/birdclef/

# Project docs
git mv ARCHITECTURE.md docs/project/
git mv QUICKSTART.md docs/project/

# Status files (archive old, keep recent)
git mv HANDOFF_2026-01-01.md docs/sessions/archive/
git mv HANDOFF_2026-04-18.md docs/sessions/recent/  # Keep accessible
```

### 4. Verify

Target: 20-40 root items

**Industry benchmarks:**
- JAX: ~20 items
- vLLM: ~25 items
- Transformers: ~20 items

**Essential at root:**
- README.md, LICENSE, CHANGELOG.md
- src/, tests/, docs/, scripts/
- Makefile, pyproject.toml, .gitignore

### 5. Commit

```bash
git add -A
git commit -m "chore(archaeology): File root items - no deletions

Moves X items to organized structure:
- Competitions → research/challenges/
- Guides → docs/project/
- Sessions → docs/sessions/
- Archives → archives/backups/

Result: NNN → YY items at root."
```

## Anti-patterns Discovered

### Status File Proliferation
Each session creates 5-10 status files at root (SESSION_45_COMPLETE_FINAL.md, etc). Over 100 sessions = chaos.

**Fix**: Route sessions to `docs/sessions/{YY-MM}/` or archive.

### Dev Tool Sprawl
.vscode/, .zed/, .pi/, .claude/ = 150+ items for personal configs.

**Fix**: Move to `.config/development/` or .gitignore.

### Cache in Repo
__pycache__/, .mypy_cache/, node_modules/ at root.

**Fix**: Already .gitignored, but also move to `archives/backups/` if present.

## Verification

```bash
# Check root count
ls -1 | wc -l

# Check essential structure
for item in README.md LICENSE src tests docs Makefile; do
    [ -e "$item" ] && echo "✓ $item" || echo "✗ $item MISSING"
done
```

## Related Skills

- v-model-change-control (for directory restructuring)
- compound-git-workflow (for clean history)
- repository-health-monitoring (to prevent future clutter)

## Post-Archaeology

- Update onboarding docs to mention new structure
- Add to CI: check root item count < 50
- Document recovery: everything in `archives/` can be restored

## Learnings from Experience

This skill was extracted from filing 350+ items from Cohezion root (424 → 37 items) in April 2026. Key insight: the "no deletions" policy preserved history while the systematic taxonomy made recovery possible.

## Tags

#maintenance #repository-health #onboarding #git #documentation #compound-engineering
