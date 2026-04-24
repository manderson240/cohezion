---
title: "Day 1 — Setup and Your First Passing Test"
target_audience: new contributor, never touched Cohezion
estimated_time: 60-90 minutes
prerequisites:
  - Linux x86_64 workstation (the project also runs on macOS but ROCm/Lemonade specifics are AMD)
  - Python 3.11.x available (the project pins `>=3.11,<3.12` in `pyproject.toml`)
  - Git 2.30+
  - 30 GB free disk (the bundle is ~182 MB but pip caches and the test artifacts grow)
prior_tutorials: []
next_tutorial: 02-day-2-the-compound-loop.md
---

# Day 1 — Setup and Your First Passing Test

Welcome to Cohezion. By the end of this tutorial you will have cloned the repository, installed dependencies through `uv`, run a single test from the suite, edited a docstring in the codebase, re-run that test against your change, and made a local commit. You will not push anything.

This is the smallest valuable loop in the project: change one line, prove the change is correct, record it. Everything else in Cohezion — the eleven-step compound executor, the FLUME latent, the cosmogonic autonomy ladder, the polish-campaign-orchestrator — sits on top of this loop.

## What you will install

The project is a polyglot monorepo. Day 1 focuses on the Python surface (`src/cohezion/`). You will not touch the Rust crate (`src/cohezion-physics-core/`) or the Next.js dashboard (`src/web/anima_dashboard/`) yet. Those have their own setup paths and you do not need them to run the test suite.

The package manager is `uv`. The project's `CLAUDE.md` is explicit about this:

> Use 'uv' for package management - NEVER bare 'pip' or 'pip install'

If you do not yet have `uv` installed, install it now using whichever approach your platform documents. After `uv --version` prints something like `uv 0.5.x`, you are ready.

## Step 1 — Clone the repository

```bash
cd ~/dev          # or wherever you keep checkouts
git clone https://github.com/manderson240/cohezion.git
cd cohezion
```

The remote is `git@github.com:manderson240/cohezion.git` if you prefer SSH. Bundle size on disk is approximately 182 MB; Git LFS is active and tracks `.so`, `.whl`, `.pt`, `.pth`, `.pkl`, `.tar.gz`, `.bundle`, and `.jsonl` artifacts. You do not need to install Git LFS to read the repository, but if you intend to write to it (and especially if you intend to add binary files), install Git LFS now and run `git lfs install` once.

> **Why this matters.** The project's `CLAUDE.md` notes that the bundle was 14 GB before the LFS migration and is 182 MB after. Committing a binary without LFS regresses that decision. The pre-commit hook `lfs-pointer-check` enforces this on commit, but the cheaper habit is to know about LFS before you create a large binary in the first place.

## Step 2 — Create a virtualenv and install

```bash
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
```

The `.[dev]` extra pulls in `pytest`, `pytest-asyncio`, `pytest-cov`, `pytest-timeout`, `ruff`, `mypy`, `black`, and `flake8`. The base install pulls in the Cohezion runtime: `numpy`, `pydantic`, `surrealdb`, `fastapi`, `uvicorn`, `anthropic`, `sentence-transformers`, `scikit-learn`, `pandas`, `gymnasium`, `fastmcp`, and a handful of others. The full list is in `pyproject.toml`.

You will see a long resolve. The `[tool.uv.sources]` block in `pyproject.toml` directs `torch`, `torchvision`, `torchaudio`, and `pytorch-triton-rocm` to the `pytorch-rocm` index — this is the AMD ROCm 6.2 wheel index. **You do not need to install the `[ml]` extra for Day 1.** Skip it. The base test suite runs without PyTorch, and the ROCm wheels are large and slow to download.

> **Checkpoint.** After install completes, run:
>
> ```bash
> python -c "import cohezion; print(cohezion.__file__)"
> ```
>
> You should see something like `/home/you/dev/cohezion/src/cohezion/__init__.py`. The editable install means your edits to `src/cohezion/...` take effect without re-installing. If the import fails with `ModuleNotFoundError`, the venv did not activate or the install failed silently. Re-check `which python` returns a path inside `.venv/bin/`.

## Step 3 — Run a single test

The test suite has approximately 6,133 collected tests. You do not want to run the whole thing on Day 1. Pick one short test and run only it:

```bash
uv run pytest tests/compound/test_executor.py -q
```

The `-q` flag is mandatory project policy. From the project's Python rules:

> **Never use `-v`/`-s` unless debugging a specific test.** Verbose output burns context.

The first run will be slow because pytest collects the entire `tests/` tree before filtering. Subsequent runs against the same path are much faster.

> **Checkpoint.** You should see a green bar with a number of passes, possibly some warnings, possibly some xfail/skip markers. If you see `ImportError` or `ModuleNotFoundError`, the install failed for one of the test's transitive dependencies — most commonly `torch` or `surrealdb`. The `tests/conftest.py` fixture `mock_surreal` mocks SurrealDB so a live database is not required, but the import must still succeed.

If `tests/compound/test_executor.py` fails on your machine for environmental reasons, fall back to a smaller and more isolated test:

```bash
uv run pytest tests/compound/test_compound_cycle.py::test_compound_cycle_records_metrics -q
```

…or pick any single test name from `ls tests/compound/`. The point of this step is to see the green bar once before you change anything.

## Step 4 — Make a trivial change

Open `src/cohezion/compound/executor.py` in your editor. The file is the heart of the project — it implements the eleven-step compound execution loop that you will study in detail in Tutorial 2. For Day 1 you will not change behavior; you will only edit a docstring.

Find the `CompoundExecutor` class definition. The first lines look like this:

```python
class CompoundExecutor(CompoundContextMixin, ExecutorIntegrationMixin):
    """Executor for compound engineering tasks with vault integration.

    Lifecycle:
      1. get_experience_guidance() - Query vault for similar tasks
      2. execute_task() - Run the task with token-efficient client
      3. Logs are persisted to vault automatically
      4. extract_patterns() - Save reusable insights
    """
```

Add a new line at the bottom of the docstring (before the closing `"""`):

```
      5. (your initials) — read this on day 1 of onboarding.
```

The exact text does not matter. The point is that you have made an observable, reversible change to a file you do not yet understand. This is the safest possible first edit.

## Step 5 — Re-run the same test against your change

```bash
uv run pytest tests/compound/test_executor.py -q
```

The result should be identical to Step 3. Editing a docstring does not change behavior, so the test count, pass count, and skip count should match your earlier run.

> **Why this matters.** This is the verification rule the project's `verification-before-completion` standard codifies: **tests passing ≠ program working, but tests still passing after your change is the minimum bar before you claim the change is safe.** If your test count or pass count changes after a docstring edit, something is wrong with your environment (most commonly: the test suite was using a different Python interpreter than your editable install). Do not move on until the numbers match.

## Step 6 — Commit locally

Stage and commit your single-file change:

```bash
git status                         # confirm only one file changed
git diff src/cohezion/compound/executor.py
git add src/cohezion/compound/executor.py
git commit -m "docs(compound): add onboarding marker to CompoundExecutor docstring"
```

Conventional-commit prefixes are project policy: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`. Your docstring edit is a `docs:` change and should be scoped to the subsystem (`compound`).

> **Checkpoint.** Run `git log -1 --stat`. You should see exactly one file changed, exactly one commit ahead of `main` (or whichever branch you are on). If `git diff --cached --name-only` shows more than one file, something pulled in more than you intended — soft-reset and re-stage explicitly:
>
> ```bash
> git reset --soft HEAD~1
> git reset HEAD
> git add src/cohezion/compound/executor.py
> git commit -m "docs(compound): add onboarding marker to CompoundExecutor docstring"
> ```
>
> This is the surgical-commit discipline that the project's coding standards (Learning 363, extended by Learning 368) call out explicitly. Pre-commit hooks plus auto-formatters can silently pull additional files into a commit when they fix unrelated drift. Verifying the staged set before committing is cheap insurance.

## Step 7 — Do NOT push

This is project policy. From the project's git-operations rule:

> READ git state freely. NEVER execute git WRITE commands without EXPLICIT user permission.
> ...
> "Fix this bug" ≠ "commit it". Wait for user to say "commit" or "push".

For a real change you would now open a pull request via the workflow in `CONTRIBUTING.md`: branch from `develop`, push, open PR to `develop`. For a Day-1 onboarding edit, the local commit is the deliverable. You can `git reset --hard HEAD~1` to throw it away, or keep it as a personal marker. Either is fine.

## What you just learned

You have made the smallest possible round-trip on the project's tooling. Internalize these five things before moving on:

1. **`uv` is mandatory.** Bare `pip` is banned. The package manager pins reproducibility and binds the ROCm wheels to the right index. `pyproject.toml`'s `[tool.uv.sources]` block does the wiring; see the `pyproject.toml` `[tool.uv]` `required-environments` constraint that forces wheels to resolve for `linux + x86_64` even when your machine differs.
2. **Tests pass with `-q` quietly, not `-v` loudly.** The full suite is approximately 6,133 tests; verbose output destroys context. Find a single test or a single file and run only it during the inner loop.
3. **The project enforces conventional commits.** `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`. Subsystem in parentheses (e.g. `docs(compound):`).
4. **Surgical commits over batched commits.** When pre-commit hooks may rewrite files, re-verify the staged set before committing. The `git diff --cached --name-only` check is the cheapest insurance against accidentally including unrelated drift.
5. **Vault-first knowledge.** Cohezion's canonical project documentation is `CLAUDE.md` (architectural overview), the global rules under `~/.claude/rules/`, and the vault under `~/vaults/cohezion-vault/`. Treat the in-tree code comments and the vault learnings as paired; one is the surface, the other is the accumulated knowledge.

## Where you are now

You have a working installation and a one-commit branch. The compound executor's docstring has your initials in it. You ran the test you cared about and it stayed green. You did not push.

Tomorrow you will trace one execution end-to-end through the eleven-step loop. The docstring you edited today will guide your reading.

→ Continue to [Tutorial 2 — Day 2: The Compound Loop](./02-day-2-the-compound-loop.md).
