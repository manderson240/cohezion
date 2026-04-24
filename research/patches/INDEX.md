# Cross-Repo Lint Patches (Wave 5C)

Generated 2026-04-23 by `synthetic-sniffing-panda` Wave 5C against 4 sibling repos.
**No commits or pushes were made to any source repo.** Patches are read-only artifacts.

## Summary

| Repo | Status | Files modified | Lint before | Lint after | Patch |
|---|---|---|---|---|---|
| autoresearch-amd | SKIPPED (dirty) | — | 5 | 5 | (report only) |
| geak | PATCH READY | 19 | 105 | 21 | `geak-lint-autofix.patch` |
| A2UI | PATCH READY | 48 | 327 | 177 | `A2UI-lint-autofix.patch` |
| observer-patch-holography | PATCH READY | 5 | 32 | 27 | `observer-patch-holography-lint-autofix.patch` |
| **Totals** | **3 patches** | **72** | **464** | **225** | **— 239 fixes** |

All three patches were verified with `git apply --check` against a clean working tree of each repo.

## Per-repo notes

### autoresearch-amd — SKIPPED
Pre-existing user dirty state (`M uv.lock`, untracked experiment logs/scripts). Per Wave 5C "skip if dirty" constraint, no `--fix` was applied. Read-only report at `autoresearch-amd-lint-report.md` lists 5 findings — including 2 likely-real `F821 Undefined name` defects in `analysis.ipynb` cell 6.

### geak
105 → 21 lint errors, 89 auto-fixed across 19 files (mostly `P006`/`I001`/`P032`/`F401`). Tracked tree was clean; only untracked scratch files exist. Note: 6 invalid `# noqa` directives in `tests/conftest.py:32-36` need manual repair.

### A2UI
327 → 177 lint errors, 148 auto-fixed across 48 files (mostly `F401` unused imports). Residual is dominated by `F405`/`F403` star-import patterns that need a manual refactor; 5 `F821` undefined-name findings are likely real bugs.

### observer-patch-holography
32 → 27 lint errors, 5 auto-fixed across 5 files (all unused-import removal). Residual is mostly `E402`/`F841` patterns that are typical/intentional in scientific Python (env mutation before CUDA import, debug locals).

## How to apply (per repo)

```bash
cd /home/mike-anderson/dev/<repo>
git status                # confirm working tree clean
git apply /home/mike-anderson/dev/cohezion/.claude/worktrees/synthetic-sniffing-panda/research/patches/<repo>-lint-autofix.patch
git diff                  # review
ruff check .              # confirm residual count matches report
# Run repo's tests before committing (e.g., uv run pytest -q)
git commit -am "style: ruff auto-fixes from synthetic-sniffing-panda Wave 5C"
```

## Linter

All scans used `ruff 0.15.1` from `~/.local/bin/ruff`, default rule set (no `--select` / `--ignore` overrides). For `geak`, the project's own `pyproject.toml` `[tool.ruff]` config was honored.
