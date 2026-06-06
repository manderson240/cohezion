# Contributing to Cohezion

Thanks for your interest — contributions are genuinely welcome, from typo fixes to new
RL baselines. This guide gets you from clone to merged PR.

## Ways to contribute

You don't need to understand the gauge theory to help. Useful contributions, roughly
easiest-first:

- **Docs & examples** — fix unclear wording, add a usage snippet, improve the quick start.
- **Bug reports** — open an issue with steps to reproduce (a failing `make` target or a
  short script is ideal).
- **New baselines** — add another agent/algorithm to compare against in `eval/`.
- **New reward modes or environments** — extend `ManifoldEnv` / `SwarmEnv`, or add a
  reward shaping variant and report results.
- **Tests** — coverage for `physics/`, `environments/`, and `eval/` is always valuable.

If you're planning something larger than a bug fix, **open an issue first** so we can
agree on the approach before you invest time.

## Your first PR

```bash
# 1. Set up
git clone https://github.com/manderson240/cohezion.git
cd cohezion
uv sync

# 2. Branch off main
git checkout -b feat/my-change main

# 3. Make your change, then verify locally
ruff format src/ tests/        # format
ruff check src/ tests/         # lint
uv run pytest tests/unit/ -q   # fast tests
mypy src/cohezion/ --ignore-missing-imports   # types (optional but appreciated)

# 4. Commit (Conventional Commits — see below) and push
git commit -m "feat(environments): add sparse reward mode"
git push -u origin feat/my-change

# 5. Open a PR against main
gh pr create --base main
```

A maintainer reviews, CI runs, and once it's green the PR is squash-merged. You don't
need to manage the merge yourself.

## Contributor License Agreement (required)

Cohezion is **dual-licensed** (AGPL-3.0 + commercial — see [LICENSING.md](LICENSING.md)).
To keep that model possible, contributions are accepted under the
[Contributor License Agreement](CONTRIBUTOR_LICENSE_AGREEMENT.md). By opening a pull
request you agree to its terms. This lets your contribution ship in both the open-source
and commercial builds; it does **not** take away your own rights to your work.

## Commit convention

Commits and PR titles follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` — new feature (minor version bump)
- `fix:` — bug fix (patch bump)
- `docs:`, `test:`, `refactor:`, `chore:` — no version bump
- `!` after the type — breaking change (major bump)

Example: `feat(compound): add recursive self-improvement loop`

## What CI checks

Every PR must pass four required checks before merge:

- **lint** — `ruff` formatting and syntax
- **validate** — skill/config compilation + registry consistency
- **ci-status** — aggregate gate (tests, compound loop, type-check)
- **commit-lint** — Conventional Commit format on the PR title

You can run the full local verification before pushing:

```bash
python .claude/rules/harness_check.py
```

## Quick command reference

| Action | Command |
|--------|---------|
| Format | `ruff format src/ tests/` |
| Lint | `ruff check src/ tests/` |
| Type-check | `mypy src/cohezion/ --ignore-missing-imports` |
| Fast tests | `uv run pytest tests/unit/ -q` |
| Full verification | `python .claude/rules/harness_check.py` |
| Open PR | `gh pr create --base main` |

## Directory map

| Path | Purpose |
|------|---------|
| `src/cohezion/` | Python package |
| `src/cohezion/physics/` | Manifold, spinors, Lagrangian dynamics, gauge theory |
| `src/cohezion/environments/` | Gymnasium RL environments |
| `src/cohezion/eval/` | Evaluation + baselines |
| `src/cohezion/skills/` | PRIME skill definitions (`*.md`) |
| `tests/` | Test suite (organized by subpackage) |
| `scripts/` | Utility and CI scripts |
| `docs/` | Documentation |
| `.github/` | CI workflows, issue/PR templates |

Questions? Open an issue — we're happy to help you land your first change.
