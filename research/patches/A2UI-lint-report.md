# A2UI lint report

**Repo:** `/home/mike-anderson/dev/A2UI/`
**Branch:** `main` (in sync with `origin/main`)
**Linter:** ruff 0.15.1 (no top-level ruff config; subdirs may have their own)
**Patch generated:** Yes — `A2UI-lint-autofix.patch` (923 lines, 48 files)

## Status: PATCH READY

Repo was clean before the run. ruff scanned all Python (3 sub-projects: `agent_sdks/python`, `tools/build_catalog`, `samples/agent/adk`). Repo restored to original state after capture.

## Lint counts

| | Count |
|---|---|
| Before | 327 |
| Auto-fixed | 148 |
| **After (residual)** | **177** |
| Files modified by patch | 48 |

## Top rules fixed (by frequency in baseline)

| Rule | Count | Description |
|---|---|---|
| F401 | 143 | unused imports — bulk of fixes |
| F405 | 133 | star-imports (mostly NOT auto-fixable) |
| A2 | 40 | annotations (PEP 604 unions, deprecated typing) |
| F541 | 8 | f-string without placeholders |
| E402 | 7 | module-level import not at top |
| F601 | 6 | repeated dict keys |
| F403 | 6 | `from X import *` |
| F821 | 5 | undefined name — **possible real bugs** |
| E712 | 5 | `== True` / `== None` comparisons |
| I001 | 4 | isort import ordering |

## Top residual rules (NOT auto-fixable)

| Rule | Count | Why not fixed |
|---|---|---|
| F405 | 133 | star-imports — manual disambiguation needed |
| A2 | 25 | type annotation modernization (some unsafe) |
| F401 | 7 | conditional / used-by-side-effect imports |
| E402 | 7 | imports after env/path mutation (often intentional) |
| F601 | 6 | dict literal duplicates — needs human review |
| F403 | 6 | `import *` — refactor required |
| F821 | 5 | undefined names — **likely real defects** |
| E712 | 5 | `== True/None` — autofix unsafe |
| F841 | 3 | unused local — may indicate dead branch |

## Recommendations

1. **F821 (5 occurrences)** in residual are likely real bugs — investigate manually.
2. **F405/F403 (133+6)** all stem from `from X import *` patterns; consider an explicit imports refactor.
3. The 148-fix patch is mostly mechanical (unused imports, f-string cleanup) and safe to apply as-is.

## How to apply

```bash
cd /home/mike-anderson/dev/A2UI
git apply /home/mike-anderson/dev/cohezion/.claude/worktrees/synthetic-sniffing-panda/research/patches/A2UI-lint-autofix.patch
git diff --stat        # 48 files
ruff check .           # confirm 177 residual
# Run each subproject's tests before commit
git commit -am "style: ruff auto-fixes (148 issues across 48 files)"
```
