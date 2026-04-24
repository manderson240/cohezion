---
title: "Day 7 — Running a Polish Campaign"
target_audience: contributor with one week of project experience
estimated_time: 3-4 hours of wallclock; ~2 hours of agent-time
prerequisites:
  - Tutorials 1-3 completed
  - Comfortable invoking sub-agents (the project's `Agent` tool or equivalent)
  - 2 hours of focused time (the campaign uses a real test suite and real commits)
prior_tutorials:
  - 01-day-1-setup-and-first-test.md
  - 02-day-2-the-compound-loop.md
  - 03-day-3-skills-and-vault.md
next_tutorial: 05-day-30-contributing-an-architectural-change.md
related_skills:
  - polish-campaign-orchestrator (~/.claude/skills/polish-campaign-orchestrator/)
related_artifacts:
  - ~/.claude/plans/synthetic-sniffing-panda.md (the reference 17-hour campaign)
  - ~/vaults/cohezion-vault/retrospectives/2026-04-23-synthetic-sniffing-panda.md (its retrospective)
---

# Day 7 — Running a Polish Campaign

You have spent six days reading and editing one file at a time. Today you will run a *campaign* — a structured multi-agent burst of work that touches many files in parallel, gated by verification, ending in a written retrospective that lands in the vault.

The reference for this practice is the **`polish-campaign-orchestrator`** skill at `~/.claude/skills/polish-campaign-orchestrator/SKILL.md`. The skill was *itself* extracted from the synthetic-sniffing-panda campaign — a 17-hour-budgeted effort that completed in 2.81 wall-clock hours by orchestrating five waves of three-to-six parallel sub-agents under inter-wave verification gates. Today you will run a much smaller version: a 2-hour micro-campaign on a single subsystem, three to five agents, the same five-wave structure compressed.

The point is to teach you the *shape* of a campaign, not to make you produce 100 commits. By the end you will have run a real wave with a real verification gate and produced a real retrospective.

## What you will do today

1. Read the `polish-campaign-orchestrator` skill end-to-end.
2. Pick a small subsystem to polish (recommendation: `src/cohezion/cache/` — modest size, clear boundaries).
3. Set up: capture the baseline, identify the worktree, list the user-decision gates.
4. Run **Wave 1** (Reclaim & Stabilize) with two parallel agents on safe cleanup.
5. Run **Wave 2** (Code Quality) with one or two agents on a focused refactor.
6. Run **Wave 3** (Tests & Coverage) with one agent writing focused tests.
7. Run **Wave 5** (Close-Out) with one agent producing the retrospective. (You will skip Wave 4 — Knowledge & Vault — to keep the scope small.)
8. Confirm the retrospective lands in the vault.

The full campaign reference is at `~/.claude/plans/synthetic-sniffing-panda.md`. Re-read its "Wave 1" through "Wave 5" sections after this tutorial; the same structure scales from 17 hours down to 2 and back up.

## Step A — Read the orchestrator skill

```bash
cat ~/.claude/skills/polish-campaign-orchestrator/SKILL.md
```

Pay attention to the three sections that govern correctness:

- **"Critical rules"** (8 numbered rules, including "User Decision Gates first," "Test baseline lock," "Surgical commits (L363/L368)," "Concurrency cap," "Wave gates").
- **"Anti-patterns to avoid"** (7 items, including "Spawning agents that touch the same file in parallel" and "Skipping Wave 5F — the recursive skill extraction").
- **"How to dispatch a wave"** (the seven-step procedure: re-measure, update plan, fire 3-6 agents in one message, wait, gate verification, synthesize, advance).

The wave-prompt template is at `~/.claude/skills/polish-campaign-orchestrator/templates/wave-prompt-template.md`. Read it now. Every agent you dispatch will receive a prompt structured by this template (working directory, baseline, goal, steps, hard constraints, critical paths, reporting). The constraint that matters most: **agents commit in surgical commits and do not push**. The orchestrator (you) is responsible for inter-wave synthesis.

## Step B — Pick your subsystem and capture the baseline

For a 2-hour micro-campaign on Day 7, pick a small subsystem. Recommendations in decreasing order of safety:

| Subsystem | Path | Why |
|---|---|---|
| Cache | `src/cohezion/cache/` | Small, well-scoped, easy to test, low risk of touching the executor invariant. |
| Cost optimization | `src/cohezion/cost_optimization/` | Modular, has existing tests, isolated. |
| Knowledge graph | `src/cohezion/knowledge_graph/` | Wave 3 of synthetic-sniffing-panda lifted this from 0% to 53% coverage; there's still room to push. |

Pick one. The rest of this tutorial uses `src/cohezion/cache/` as the example; substitute your choice.

Capture the baseline:

```bash
# Lint count for your subsystem
uv run ruff check src/cohezion/cache/ 2>&1 | tail -1

# Test pass/fail for your subsystem
uv run pytest tests/cache/ -q 2>&1 | tail -3

# Coverage for your subsystem
uv run pytest tests/cache/ --cov=src/cohezion/cache --cov-report=term -q 2>&1 | tail -10

# LOC for your subsystem
find src/cohezion/cache/ -name "*.py" -exec wc -l {} + | tail -1
```

Write these numbers into a small plan file at `~/.claude/plans/day-7-cache-polish.md`:

```markdown
---
title: "Day 7 micro-campaign — cache subsystem polish"
slug: day-7-cache-polish
status: PENDING
created: <today>
estimated_duration_hours: 2
strategy: 4-wave-micro-campaign
worktree_root: <pwd>
---

# Day 7 — Cache subsystem polish

## Baseline (captured <timestamp>)

| Metric | Value |
|---|---|
| `ruff check src/cohezion/cache/` | <count> |
| `pytest tests/cache/ -q` pass count | <N> |
| `pytest tests/cache/ -q` fail count | <N> |
| `pytest --cov=src/cohezion/cache` coverage % | <N> |
| Cache subsystem LOC | <N> |

## User Decision Gates

(list ALL destructive ops here for one-pass approval before Wave 1.)

1. (none — this micro-campaign is read-only-plus-additive; no deletes proposed.)

## Waves

### Wave 1 — Reclaim & Stabilize (h0–h0.5)
- 1A: __pycache__ + .pytest_cache cleanup (agent, safe)
- 1B: ruff auto-fixes for cache/ subsystem only (agent, safe)

### Wave 2 — Code Quality (h0.5–h1)
- 2A: docstring pass on cache/ public methods (agent)

### Wave 3 — Tests & Coverage (h1–h1.5)
- 3A: write 3-5 unit tests for the lowest-covered cache/ file (agent)

### Wave 5 — Close-Out (h1.5–h2)
- 5A: retrospective + numeric deltas + vault write (agent or you directly)
```

Notice you are skipping Waves 4 and the Design track for the micro-campaign. The reference 17-hour campaign uses all five waves plus Wave D (design). For 2 hours, four waves with one or two agents each is plenty.

> **Why this matters.** The plan file is the campaign's anchor. Every agent reads it, every wave gate updates it, the retrospective references it. The synthetic-sniffing-panda campaign's plan (`~/.claude/plans/synthetic-sniffing-panda.md`) was the single document that 30 agents coordinated against without a chat thread between them. The plan is the chat thread.

## Step C — Wave 1: Reclaim & Stabilize

Dispatch two agents in **a single message**. (If your harness is Claude Code or equivalent, this is two `Agent` tool calls in the same turn; if you are running these manually, run two terminals in parallel.)

**Agent 1A — pycache cleanup.** Prompt scaffold (use the wave-prompt template):

> Working directory: `<repo root>`. Goal: remove `__pycache__/` and `.pytest_cache/` directories under `src/cohezion/cache/` and `tests/cache/`. Steps: `find src/cohezion/cache tests/cache -type d \\( -name __pycache__ -o -name .pytest_cache \\) -exec rm -rf {} +`. Verify with `find src/cohezion/cache tests/cache -name __pycache__` returning empty. Hard constraint: do not delete anything outside those two paths. No commit needed (caches are gitignored).

**Agent 1B — ruff auto-fixes scoped to cache/.** Prompt scaffold:

> Working directory: `<repo root>`. Goal: run `uv run ruff check --fix src/cohezion/cache/` (safe fixes only — no `--unsafe-fixes`), then run `uv run pytest tests/cache/ -q` and confirm pass count is unchanged. If green, commit the changes: `git add src/cohezion/cache/ && git commit -m "chore(cache): ruff safe auto-fixes (Day 7 micro-campaign)"`. Verify staged set with `git diff --cached --name-only` before committing — must contain only `src/cohezion/cache/` paths. Report: number of fixes applied, test pass count before and after, commit SHA.

Wait for both agents to return. Their reports go to your synthesis pass.

> **Wave 1 gate (you run this manually).** Re-measure the baseline:
>
> ```bash
> uv run ruff check src/cohezion/cache/ 2>&1 | tail -1   # lint count delta
> uv run pytest tests/cache/ -q 2>&1 | tail -3            # test pass/fail delta
> ```
>
> The lint count should have decreased; the test pass count should be unchanged. If a test failed that was passing before, **the gate has failed** — do not advance to Wave 2. Spawn a single fixer agent or roll back the offending commit.

## Step D — Wave 2: Code Quality

For a micro-campaign, one agent in Wave 2 is enough. The reference 17-hour campaign ran six agents in this wave; your version uses one focused agent on a docstring pass.

**Agent 2A — docstring pass.** Prompt scaffold:

> Working directory: `<repo root>`. Goal: ensure every public class and public method (non-leading-underscore) in `src/cohezion/cache/` has a one-line docstring. If a docstring exists, leave it alone. If a docstring is missing, add a one-line description that summarizes what the method does. Do not change behavior. Steps: list public methods with `grep -nE "^    def [a-z]" src/cohezion/cache/*.py`, identify docstring-less ones, add one-liners, run `uv run pytest tests/cache/ -q` to confirm no regression. Hard constraint: docstrings only, no behavior changes. Commit: `docs(cache): add missing one-line docstrings to public API`. Report: methods updated, test pass count, commit SHA.

Let it run. Then:

> **Wave 2 gate.** Re-measure tests; confirm no regression. The doc count is harder to quantify automatically; trust the agent's report and spot-check one file with `git diff HEAD~1 src/cohezion/cache/<some_file>.py`.

## Step E — Wave 3: Tests & Coverage

One agent. The reference campaign ran six in this wave.

**Agent 3A — coverage uplift on lowest-covered file.** Prompt scaffold:

> Working directory: `<repo root>`. Goal: write 3-5 new unit tests for the cache/ file with the lowest coverage. Steps: (1) run `uv run pytest tests/cache/ --cov=src/cohezion/cache --cov-report=term -q` and identify the file with the lowest coverage percentage; (2) write 3-5 tests targeting uncovered branches; (3) use the `mock_surreal` fixture from `tests/conftest.py` for any SurrealDB-touching code; (4) run the focused suite and verify the new tests pass and the coverage percentage rose. Commit: `test(cache): add unit tests for <filename> (coverage <before>% → <after>%)`. Report: file targeted, coverage delta, commit SHA.

Wait. Then:

> **Wave 3 gate.** Re-measure coverage:
>
> ```bash
> uv run pytest tests/cache/ --cov=src/cohezion/cache --cov-report=term -q 2>&1 | tail -10
> ```
>
> The targeted file should be higher; the overall cache/ coverage should be at least slightly higher. Test pass count should have increased by 3-5; pass count for previously existing tests must be unchanged.

## Step F — Wave 5: Close-Out & Retrospective

Skip Wave 4 (Knowledge & Vault) for the micro-campaign — there is not enough material in 2 hours of work to justify a vault consolidation pass.

**Agent 5E — retrospective writer.** Prompt scaffold:

> Working directory: `<repo root>`. Goal: produce a retrospective markdown for the day-7-cache-polish micro-campaign. Steps: (1) read `~/.claude/plans/day-7-cache-polish.md` for the baseline numbers; (2) re-measure each metric and produce a delta table; (3) read `~/.claude/skills/polish-campaign-orchestrator/templates/retrospective-template.md` for the scaffold; (4) write the retrospective to `~/vaults/cohezion-vault/retrospectives/<today>-day-7-cache-polish.md`; (5) include sections: Goal, Strategy, Numeric deltas (table), Commits (list of SHAs with one-line descriptions), Lessons (2-3 things learned), and Next steps (what a future campaign should pick up). Hard constraint: numbers must be re-measured, not copied from the plan baseline. Report: retrospective path, lessons-learned count.

Wait for the agent. Verify the file exists:

```bash
ls -la ~/vaults/cohezion-vault/retrospectives/ | grep day-7-cache-polish
```

> **Checkpoint.** The retrospective should be a few hundred words, contain a numeric-delta table with measurable improvements over baseline, and end with a "Next steps" section. If the file is much longer than that, the agent over-wrote — that is fine for a learning exercise but trim before treating it as canonical. If the file is much shorter, re-prompt the agent for missing sections.

## Step G — Update the plan and the orchestrator skill

Mark the plan COMPLETE:

```bash
# Edit ~/.claude/plans/day-7-cache-polish.md and change `status: PENDING` → `status: COMPLETE`
```

If you discovered something the orchestrator skill should warn about — for example, an anti-pattern you tripped over that was not in the existing "Anti-patterns to avoid" list — propose an edit to `~/.claude/skills/polish-campaign-orchestrator/SKILL.md`. This is the Wave 5F discipline: **every campaign produces a learning that improves the next campaign**. The reference campaign produced the orchestrator skill itself; your micro-campaign produces an incremental refinement.

## Optional Step H — Sync the worktree (if you used one)

If you ran the campaign in a worktree (recommended; see the `cz-cli.md` rule for the `cz worktree` commands), squash-merge it back to the base branch via `cz worktree sync --json day-7-cache-polish` and then `cz worktree cleanup --json day-7-cache-polish`. The reference 17-hour campaign was run in `.claude/worktrees/synthetic-sniffing-panda/` and synced back via the same path.

For Day 7, if you ran the campaign on your main checkout instead, the commits are already on your branch.

## What you just learned

1. **Campaigns are five-wave parallel-agent orchestrations gated by verification.** Wave 1 reclaims and stabilizes; Wave 2 improves code quality; Wave 3 lifts tests and coverage; Wave 4 consolidates knowledge; Wave 5 closes out with audit and retrospective. The structure scales from 2 hours to 17 with the same shape.
2. **The plan markdown is the chat thread.** Thirty agents coordinated against the synthetic-sniffing-panda plan with no inter-agent messaging. The plan + the wave-prompt template + the in-tree code is enough state for parallel agents to converge on a coherent outcome.
3. **Wave gates are non-negotiable.** Re-measure between waves. If a wave regressed the baseline, do not advance — spawn a fixer agent or roll back. The reference campaign documents one such regression (the `compound test fail` count stayed at 86 because errors were recategorized; the gate caught the mismatch and the retrospective noted the cause).
4. **Surgical commits with explicit staging are mandatory at high concurrency.** With many agents committing in parallel, a non-surgical commit can pull in another agent's in-flight changes. The wave-prompt template's "verify staged set before committing" line is the cheapest insurance against this. Learnings 363 and 368 capture the pattern.
5. **Every campaign leaves a retrospective in the vault.** This is the mechanism by which campaign-level work compounds. The next campaign reads prior retrospectives at step 1 of the compound loop (vault experience guidance) and starts with the prior campaign's lessons in context.

## What you will do on Day 30

Days 1-7 took you from "fresh checkout" to "I can run a multi-agent campaign and produce a vault retrospective." Day 30 is about the substantial architectural change — the kind that warrants an ADR, peer review, a TDD implementation, a verification suite, and an update to `CLAUDE.md`'s architecture row. You will write the ADR using the same pattern as the Wave Ω10 retroactive ADRs ([ADR-001](../adrs/ADR-001-eleven-step-compound-loop.md) and [ADR-002](../adrs/ADR-002-cost-routing-tiers.md) in `docs/adrs/`), get adversarial review, implement the change with TDD, and write the retrospective. The discipline is the discipline you have already practiced. The scale is one architectural decision instead of one micro-cleanup.

→ Continue to [Tutorial 5 — Day 30: Contributing an Architectural Change](./05-day-30-contributing-an-architectural-change.md).

→ Back to [Tutorial 3 — Day 3: Skills and the Vault](./03-day-3-skills-and-vault.md).
