# geak lint report

**Repo:** `/home/mike-anderson/dev/geak/`
**Branch:** `main` (in sync with `origin/main`)
**Linter:** ruff 0.15.1 (project ruff config in `pyproject.toml`)
**Patch generated:** Yes — `geak-lint-autofix.patch` (601 lines, 19 files)

## Status: PATCH READY

Tracked files were clean before the run; only untracked files exist (`.geak_env/`, `*.md` scratch notes, `LUMA_SPEEDRUN_COMMANDS.sh`). All ruff `--fix` changes apply cleanly to 19 tracked files. Repo was restored to its original state after capture.

## Lint counts

| | Count |
|---|---|
| Before | 105 |
| Auto-fixed | 89 |
| **After (residual)** | **21** |
| Files modified by patch | 19 |

(Note: ruff reported "110 errors (89 fixed, 21 remaining)" mid-fix — re-scans converge on 105 baseline / 21 residual.)

## Top rules fixed (by frequency in baseline)

| Rule | Count | Description |
|---|---|---|
| P006 | 21 | flake8-pytest-style |
| I001 | 19 | isort import ordering |
| P032 | 16 | pytest fixture issues |
| F401 | 14 | unused imports |
| P045 | 8 | pytest issues |
| H118 | 6 | flake8-import-conventions |
| F541 | 4 | f-string without placeholders |
| H120 | 4 | flake8-import-conventions |
| P035 | 4 | pytest issues |
| T504 | 3 | flake8-todos |

## Top residual rules (NOT auto-fixable)

| Rule | Count |
|---|---|
| H118 | 6 |
| H120 | 4 |
| T504 | 3 |
| H100 | 3 |
| B007 | 3 |
| F841 | 1 |
| T028 | 1 |

## Warnings during fix

ruff reported 6 invalid `# noqa` directives in `tests/conftest.py:32-36` — directive format expects comma-separated codes (e.g., `# noqa: F401, F841`). These should be repaired before re-running.

## How to apply

```bash
cd /home/mike-anderson/dev/geak
git apply /home/mike-anderson/dev/cohezion/.claude/worktrees/synthetic-sniffing-panda/research/patches/geak-lint-autofix.patch
git diff                # review
ruff check .            # confirm 21 residual
uv run pytest -q        # smoke-test before commit
git commit -am "style: ruff auto-fixes (89 issues across 19 files)"
```
