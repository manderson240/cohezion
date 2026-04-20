---
title: "Root Archaeology: 424 → 37 Items"
category: maintenance
date: 2026-04-19
status: completed
skill: [[root-archaeology]]
---

# Root Archaeology: Massive Repo Cleanup

## Context
Repository root had **424 items**, making first impression unprofessional for Anthropic Universes application.

## Actions Taken
- Filed **387 items** using systematic taxonomy
- Achieved **37 root items** (target: 20-40)
- Created skill: `src/cohezion/skills/root-archaeology.md`

## Key Insights

### 1. Status File Proliferation (HIGH)
Each session creating 5-10 status files at root → chaos at 100 sessions
- **Before**: SESSION_45_COMPLETE_FINAL.md, etc.
- **After**: docs/sessions/{date}/
- **Prevention**: Route on creation

### 2. Dev Config Entropy (MEDIUM)
Personal configs (.pi/, .zed/, .vscode/) reached 150+ items
- **Solution**: Move to .config/development/
- **Prevention**: gitignore patterns

### 3. No-Deletions Policy (HIGH)
Preserved history, enables rollback
- **Discipline**: git mv everything
- **Recovery**: archives/backups/

### 4. Worktree Isolation (HIGH)
Prevented mixing cleanup with feature work
- **Pattern**: Use isolated worktree from main
- **Benefit**: Clean commit history

## Filing Schema

| Destination | Purpose |
|-------------|---------|
| `research/challenges/` | Competition outputs |
| `docs/project/` | Guides, architecture |
| `docs/sessions/` | Status, handoffs |
| `infrastructure/` | Docker, deployment |
| `archives/backups/` | Old versions, debug |
| `data/external/` | Artifacts, submissions |

## Metrics

| Metric | Value |
|--------|-------|
| Start | 424 items |
| End | 37 items |
| Reduction | 91% |
| Deletions | 0 |
| Commits | 5 |
| Time | 4 hours |

## Dogfooding

### Root Health Guard
- Added `make root-guard` to Makefile
- CI check: root items < 50
- Alert on dev config sprawl

### Session Template
- Auto-route HANDOFF_*.md to docs/sessions/
- Status reports → archive on creation

### Onboarding
- New devs learn root-archaeology skill
- Understand filing taxonomy

## Links

- Skill: [[root-archaeology]]
- Code: `src/cohezion/skills/root-archaeology.md`
- Extraction: [[2026-04-19 Archaeology Learnings]]

## Tags
#repository-health #maintenance #compound-engineering #onboarding
