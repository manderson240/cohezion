# autoresearch-amd lint report

**Repo:** `/home/mike-anderson/dev/autoresearch-amd/`
**Branch:** `autoresearch/apr9`
**Linter:** ruff 0.15.1 (no project ruff config; defaults applied)
**Patch generated:** No — repo has user-owned uncommitted changes (`M uv.lock` + untracked `run.log`, `watch_exp{2,3}.{log,sh}`)

## Status: SKIPPED (dirty)

Per Wave 5C hard constraint ("Skip if dirty"), no `--fix` was applied. The findings below are read-only.

## Lint count

| | Count |
|---|---|
| Total | 5 |
| Auto-fixable | 2 |
| Files affected | 2 (`analysis.ipynb`, `train.py`) |

## Findings

```
analysis.ipynb:cell 2:3:17: F401 [*] `numpy` imported but unused
analysis.ipynb:cell 6:51:26: F821 Undefined name `best`
analysis.ipynb:cell 6:52:13: F821 Undefined name `best`
train.py:12:8: F401 [*] `contextlib` imported but unused
train.py:66:1: E402 Module level import not at top of file
```

## Rule frequency

| Rule | Count | Description |
|---|---|---|
| F401 | 2 | Unused import (auto-fixable) |
| F821 | 2 | Undefined name — **likely real bug** in `analysis.ipynb` cell 6 |
| E402 | 1 | Module-level import not at top of file |

## Recommendations

1. **F821 (`best`) in `analysis.ipynb` cell 6 is a likely real defect** — investigate before fixing other lint.
2. After committing `uv.lock` (or stashing), re-run with `ruff check --fix .` to auto-resolve the 2 F401 imports.
3. The E402 in `train.py:66` may be intentional (e.g., conditional import after env setup) — review before fixing.

## How to run yourself

```bash
cd /home/mike-anderson/dev/autoresearch-amd
ruff check .                  # see findings
ruff check --fix .            # apply 2 auto-fixes (only after committing/stashing uv.lock)
```
