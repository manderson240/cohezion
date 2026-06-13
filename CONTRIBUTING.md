# Contributing to Cohezion

## Quick Reference

| Action | Command |
|--------|---------|
| Format | `ruff format src/ tests/` |
| Lint | `ruff check src/ tests/` |
| Type-check | `mypy src/cohezion/ --ignore-missing-imports` |
| Fast tests | `uv run pytest tests/unit/ --import-mode=append -q` |
| All verification | `python .claude/rules/harness_check.py` |
| Open PR | `gh pr create --repo manderson240/cohezion --base main` |
| Auto-merge | `gh pr merge --auto --squash --delete-branch` |

## CI Pipeline

All PRs must pass 4 required checks before merge:
- **lint**: `ruff` syntax and formatting
- **validate**: skill stub/config compilation + registry consistency
- **ci-status**: aggregate gate (test, compound, typecheck)
- **commit-lint**: conventional commit format on PR title

## V-Model Gate

Every PR must satisfy the V-Model verification harness:
1. Run `python .claude/rules/harness_check.py` before opening PR
2. All 4 CI checks must pass
3. Branch auto-deleted after squash merge

## Commit Convention

All commits and PR titles follow [Conventional Commits](https://www.conventionalcommits.org/):
- `feat:` — new feature (MINOR version bump)
- `fix:` — bug fix (PATCH version bump)
- `chore:`, `docs:`, `test:`, `refactor:` — no version bump
- `!` after type — breaking change (MAJOR version bump)

Example: `feat(compound): add recursive self-improvement loop`

## Git Workflow

Trunk-based development on `main`:
1. `git checkout -b feat/my-feature main`
2. Make changes, commit with conventional format
3. `python .claude/rules/harness_check.py`
4. `git push -u origin feat/my-feature`
5. `gh pr create --base main`
6. After CI passes: `gh pr merge --auto --squash --delete-branch`

## Directory Map

| Path | Purpose |
|------|---------|
| `src/cohezion/` | Python package (79 subpackages) |
| `src/cohezion/skills/` | PRIME skill definitions (*.md) |
| `src/cohezion/registry/` | Skill + capability registries |
| `tests/` | Test suite (organized by subpackage) |
| `scripts/` | Utility and CI scripts |
| `docs/` | Technical documentation |
| `.github/` | CI workflows, templates, CODEOWNERS |
| `.claude/rules/` | AutoHarness verification rules |
