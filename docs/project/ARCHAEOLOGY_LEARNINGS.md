# Archaeology Learnings Extraction

**Date**: 2026-04-19
**Source**: Session archaeology-execution
**Scope**: Root cleanup (424 → 37 items)

## Patterns Extracted

### 1. Status File Proliferation Pattern
- **Symptom**: SESSION_45_COMPLETE_FINAL.md, BREAKTHROUGH_FINAL_REPORT.md, HANDOFF_*.md multiply
- **Root cause**: No filing system for ephemeral session artifacts
- **Prevention**: Route sessions to docs/sessions/{date}/ on creation
- **Skill created**: `src/cohezion/skills/root-archaeology.md`

### 2. Dev Config Entropy
- **Symptom**: .pi/, .zed/, .vscode/, .claude/ accumulate 150+ files
- **Root cause**: Personal tooling configs in shared repo
- **Prevention**: .config/development/ convention or gitignore

### 3. The Compound Anti-Pattern
Small decisions ("I'll just save this status file here") compound into structural debt.

## Metrics

| Metric | Value |
|--------|-------|
| Items filed | 387 |
| Root reduction | 91% (424→37) |
| Deletions | 0 |
| Commits | 5 |
| Time | 4 hours |

## Files Created

1. `src/cohezion/skills/root-archaeology.md` - Reusable skill
2. Extraction doc (this file)
3. Structured JSON at /tmp/archaeology_learnings.json

## SurrealDB Storage Pending

Run vault sync when SurrealDB is available to persist individual learnings.
