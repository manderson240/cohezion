# Git Hygiene Standards

## The 8.6M File Incident (2026-01-25)
Autonomous overnight simulations generated 8.6 million tracked files, freezing IDEs and bloating the git index to 50MB+. Recovery required 3 cleanup passes across 2 branches. This incident established all rules below.

## Ignore Rules — Layered Defense

### Layer 1: Output Directories (block agent write targets)
- `data/`, `results/`, `renders/`, `exports/`, `logs/` — agents WILL write here
- `src/cohezion/knowledge_graph/universe_nodes/` — simulation artifacts
- `.archive/`, `.artifacts/`, `.sandbox/`, `temp/`

### Layer 2: Build Artifacts
- `apps/dashboard/assets/` — Vite/Marimo bundles, fonts, CodeMirror language files
- `**/node_modules/`, `**/target/`, `**/build/`, `**/dist/`
- `**/*.safetensors` — ML model weights

### Layer 3: Binary Patterns (category-level block)
- `*.pt`, `*.pdf`, `*.so`, `*.dll`, `*.mp3`, `*.wav`, `*.webp`
- `*.zip`, `*.tar.gz`, `*.iso`, `*.img`, `*.mp4`, `*.mkv`

### Layer 4: Source Protection (negation whitelist)
- `!src/**/*.py`, `!scripts/**/*.py`, `!apps/**/*.tsx`, `!apps/**/*.ts`
- `!**/favicon*.png`, `!**/logo.png`
- Order matters: negations MUST come AFTER the block rule

### Virtual Environments
- `**/venv/`, `.venv`, `**/env/`

## Pre-commit Hooks

### On Commit (fast, every commit)
- `ruff --fix` + `ruff-format` — auto-fix lint/formatting
- `mypy` — type checking (warn-only until errors fixed)
- `trailing-whitespace`, `end-of-file-fixer` — whitespace normalization
- `check-file-count` — blocks if >1000 untracked files (runaway prevention)
- `check-complexity` — warns on functions >80 lines or files >800 lines
- `detect-private-key`, `check-added-large-files` (>1MB)

### On Push (slower, before sharing)
- `pytest -x -q` — full test suite, stop on first failure
- `import-check` — verify critical module imports
- `check-file-count`, `detect-private-key`, `check-added-large-files`

### Stage Override Gotcha
The `pre-commit-hooks` repo internally sets `stages: [commit, push]` on ALL hooks, overriding `default_stages`. Must add explicit `stages: [pre-commit]` to hooks that should only run on commit.

## The Untrack & Mine Protocol
When removing tracked files:
1. **Read first** — extract knowledge, patterns, config values
2. **Add to .gitignore** — prevent re-tracking
3. **`git rm --cached`** — untrack without deleting from disk
4. **Verify** — `git status` should show clean
5. NEVER delete without reading. Knowledge > disk space.

## Maintenance
- Run `python scripts/assess_git_health.py` weekly to check for bloat and drift
- Budget 2-3 passes for any major cleanup (each removal reveals the next layer)
- Simulation output directories must be .gitignored BEFORE simulations run
