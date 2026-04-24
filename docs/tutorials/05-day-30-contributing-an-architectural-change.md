---
title: "Day 30 — Contributing an Architectural Change"
target_audience: contributor with one month of project experience and one campaign under their belt
estimated_time: 6-12 hours of focused work spread over 2-3 days
prerequisites:
  - Tutorials 1-4 completed
  - You have run at least one polish campaign and produced one vault retrospective
  - You are comfortable with the project's git workflow, conventional commits, and surgical-commit discipline
prior_tutorials:
  - 01-day-1-setup-and-first-test.md
  - 02-day-2-the-compound-loop.md
  - 03-day-3-skills-and-vault.md
  - 04-day-7-running-a-campaign.md
related_adrs:
  - docs/adrs/ADR-001-eleven-step-compound-loop.md
  - docs/adrs/ADR-002-cost-routing-tiers.md
related_skills:
  - bmad-code-review (~/.claude/skills equivalent)
  - peer-review
---

# Day 30 — Contributing an Architectural Change

You have spent a month with the project. You can name the eleven steps of the compound loop without looking. You have run a multi-agent campaign. You understand vault-first knowledge architecture. Today you graduate from "polish work" to **contributing an architectural change**: a substantive change that affects the project's invariants — the kind of change that warrants an Architectural Decision Record (ADR), adversarial review by multiple agents, a test-driven implementation, a verification suite, a written retrospective, and an update to `CLAUDE.md`.

The two ADRs in `docs/adrs/` ([ADR-001](../adrs/ADR-001-eleven-step-compound-loop.md), [ADR-002](../adrs/ADR-002-cost-routing-tiers.md)) were written *retroactively* during the synthetic-sniffing-panda Wave Ω10. That campaign produced them because the project had been making architectural commitments without recording the rationale, and the retrospective surfaced the gap. From now on the expectation is **forward-looking ADRs**: write the ADR *before* the change, not after.

The lifecycle today follows seven stages. Each stage is mandatory for a real architectural change.

1. Decide whether your change actually warrants an ADR.
2. Write the ADR, following the Wave Ω10 template.
3. Get adversarial review (multiple reviewer skills, in parallel).
4. Implement the change with TDD (failing test first, minimal implementation, refactor).
5. Run the verification suite (lint, type-check, full tests, hand-execution of the runnable artifact).
6. Write the retrospective into the vault.
7. Update `CLAUDE.md` if the change affects the architecture-row table.

By the end of today (or this week, since real architectural work is rarely done in a single session) you will have made a substantive contribution that future contributors can read about, learn from, and challenge.

## What you will do today

Pick one architectural change. Examples that fit the Day-30 brief:

| Candidate change | Why it warrants an ADR |
|---|---|
| Add a new "Step 12" to the compound loop | Modifies a HIGH-reversal-cost invariant ([ADR-001](../adrs/ADR-001-eleven-step-compound-loop.md) gates this) |
| Replace the keyword-based `QueryComplexityAnalyzer` with a learned classifier | Changes the routing-decision algorithm ([ADR-002](../adrs/ADR-002-cost-routing-tiers.md) called this out as the next iteration) |
| Add a new vault subdirectory (e.g. `~/vaults/cohezion-vault/contracts/`) | Changes the vault-first knowledge taxonomy |
| Introduce a new MCP server for an external service | Adds a new agent-protocol surface |
| Migrate one persistence table from SurrealKV to Postgres | Changes the persistence-layer invariant |

For this tutorial we use **"Add a new vault subdirectory for ADRs themselves"** as the running example — small enough to actually do in one tutorial, large enough to require an ADR. Substitute your real change as appropriate.

## Stage 1 — Decide whether you need an ADR

Not every change warrants an ADR. The two written so far (ADR-001, ADR-002) cover the eleven-step compound loop and the cost-routing tiers — both **HIGH** reversal cost, both load-bearing for downstream consumers. A docstring fix does not warrant an ADR. A new MCP server might.

Use this triage:

| Indicator | ADR? |
|---|---|
| Change touches a downstream contract (other modules assume a specific shape from this code) | **Yes** |
| Change introduces a new invariant or removes an existing one | **Yes** |
| Reversal cost is MEDIUM or HIGH (multiple person-weeks to undo) | **Yes** |
| Change is reasoned-about: you considered alternatives and rejected them | **Yes** |
| Change is a bug fix that restores intended behavior | No |
| Change is a docstring, formatting, or refactor with no semantic delta | No |
| Change is a single-file addition with no other module reading it | No |

If you answer "Yes" to any of the first four, write the ADR.

> **Why this matters.** The synthetic-sniffing-panda PRFAQ exercise (`research/prfaq/2026-04-23-cohezion-prfaq.md`) noted under "Hardest objections" that the project's structural-safety claims rest on commitments that were made implicitly. Retroactive ADRs were necessary because the rationale was scattered across `CLAUDE.md`, code comments, and individual session memories. Writing ADRs *before* the change keeps the rationale in one durable place, makes the change reviewable, and gives future contributors the ability to challenge the decision on its own terms.

## Stage 2 — Write the ADR

Open the existing ADRs as templates:

```bash
cat docs/adrs/ADR-001-eleven-step-compound-loop.md
cat docs/adrs/ADR-002-cost-routing-tiers.md
```

Both follow this structure (extract the section headers; this is the canonical Cohezion ADR shape):

```markdown
---
adr_number: 003
title: <Short Imperative Title>
date: YYYY-MM-DD
status: PROPOSED | ACCEPTED | DEPRECATED | SUPERSEDED
deciders: <names or roles>
consulted: [<who you talked to>]
informed: [<who needs to know>]
authored_by: <campaign or person>
---

# ADR-003: <Title>

## Status
<one sentence + date>

## Context
<3-6 paragraphs: why this decision is needed, what constraints apply, what alternatives the system imposes>

## Decision
<one paragraph: the chosen approach, stated as a commitment>

## Rationale
<2-4 paragraphs: why this is the right choice given the context>

## Alternatives considered
### Option A: <name>
- Pros: <list>
- Cons: <list>
- Why rejected: <one sentence>

### Option B: <name>
...

### Option C (chosen): <name>
- Pros: <list>
- Cons: <list>
- Why chosen: <one sentence>

## Consequences
### Positive
### Negative
### Neutral

## Implementation
- Primary files: <paths>
- Test files: <paths>
- Documentation: <where this is referenced>

## Verification
- Static check: <command + expected output>
- Runtime check: <command + expected output>
- Test: <command + expected output>

## Reversal cost
**LOW | MEDIUM | HIGH.** <one paragraph: what undoing this would require>

## Related ADRs
- Depends on: <list>
- Informs: <list>
- Tension with: <list>

## References
- <links to research, papers, prior internal docs>
```

Create your ADR file at `docs/adrs/ADR-003-<your-title-slug>.md` and fill in every section. Skipping sections is not optional — the structure is the contract. The synthetic-sniffing-panda Wave Ω10 produced ADR-001 and ADR-002 with this exact structure; future ADRs are read against the same shape, so a missing section signals an incomplete decision.

For the running example ("Add a new vault subdirectory for ADRs themselves"), the ADR would explain: the `docs/adrs/` directory was added to the project tree but ADRs are *project-knowledge*, not just project-source — they should be canonicalized in the vault under `~/vaults/cohezion-vault/decisions/` (or a new `~/vaults/cohezion-vault/adrs/` subdirectory), with the project tree's `docs/adrs/` being a derived mirror. This is the same vault-first / project-derived pattern as skills (Tutorial 3); you are extending it to ADRs.

> **Checkpoint.** Read your draft ADR aloud (or in your head). Does the "Decision" sentence stand on its own? Could a future contributor accept or challenge the decision based only on what is in this file? If you have to say "well, you also need to know about X," that X belongs in the Context or Rationale section. Add it.

## Stage 3 — Get adversarial review

Cohezion's review discipline is *adversarial in parallel*: spawn three reviewers concurrently, each with a different lens, then synthesize.

The three lenses (from `~/.claude/skills/bmad-code-review` and `peer-review`):

1. **Scientific rigor / Blind Hunter** — looks for unstated assumptions, gaps in the argument, false claims of precedent.
2. **Edge case hunter** — walks every branching path and boundary condition; reports unhandled cases.
3. **Acceptance auditor** — asks "if I were the future contributor reading this, would I be able to act on it?"

Dispatch them in a single message (three `Agent` tool calls in one turn, if you have agent-spawning tools), each with a copy of your ADR and the lens-specific prompt. Each returns a list of findings classified by severity. You then synthesize: must-fix findings get fixed in the ADR before Stage 4 begins; should-fix findings get logged in the ADR's "Negative consequences" or in a "Followups" section; nit-pick findings get fixed silently.

If you do not have multi-agent dispatch in your harness, the alternative is sequential review:

```bash
# Open three Claude conversations (or whichever LLM)
# In each, paste the ADR plus one of the three review prompts
# Synthesize the findings yourself
```

Sequential is slower (~3x wallclock) but produces equivalent quality. The reason parallel is preferred is the campaign-orchestrator insight: parallel reviews cross-pollinate at the synthesis step, and reviewers are not influenced by each other's findings.

> **Why this matters.** The PRFAQ's "Internal-only addendum" lists "the bus factor is one" as the project's #1 risk and "no second engineer reviewing pull requests" as the highest-leverage productisation step. Adversarial multi-agent review is the partial mitigation: it is not a second human, but it is three independent perspectives forced into the conversation before commit. Skipping this step on an architectural change is the project anti-pattern most likely to introduce a bug that an extra reviewer would have caught.

## Stage 4 — Implement with TDD

The project's testing rule is unambiguous:

> **Core Rule:** No production code without a failing test first.

The Red-Green-Refactor cycle:

1. **RED.** Write one minimal failing test that proves the intended behavior is missing. Naming convention: `test_<function>_<scenario>_<expected_result>`. For our example: `test_vault_finds_adr_by_number_returns_path`.
2. **VERIFY RED.** Run the test, confirm it fails *because the feature is missing*, not because of a syntax error.
3. **GREEN.** Write the simplest possible code that makes the test pass.
4. **VERIFY GREEN.** Run the test (and the suite around it) and confirm it passes.
5. **REFACTOR.** Improve the implementation while keeping tests green.

For the running example:

```bash
# RED: write the test first
$EDITOR tests/vault/test_adr_lookup.py
uv run pytest tests/vault/test_adr_lookup.py -q   # should fail

# GREEN: minimal implementation
$EDITOR src/cohezion/vault/adr_index.py
uv run pytest tests/vault/test_adr_lookup.py -q   # should pass

# REFACTOR: clean up
uv run ruff format src/cohezion/vault/adr_index.py
uv run pytest tests/vault/ -q   # full vault suite still green
```

Commit at the GREEN stage with a `feat:` or `refactor:` message. Use the surgical-commit discipline you practiced on Day 7:

```bash
git diff --cached --name-only   # confirm staged set is what you intended
git commit -m "feat(vault): add ADR index lookup (per ADR-003)"
```

If you forgot to write the test first and have already written production code, the recovery procedure is documented in the project's testing rule:

> **Recovery:** If you already wrote production code before tests, write tests immediately (they'll pass — that's fine). Apply TDD properly for remaining work.

This is forgiveness, not permission. Recovery is for the case where you slipped; do not slip on purpose.

## Stage 5 — Run the verification suite

Tests passing is necessary but not sufficient. Verification is what the project's `verification-before-completion.md` rule calls "evidence before claims." Before declaring the change complete, run:

```bash
make format       # ruff format
make lint         # ruff check --fix
make type-check   # mypy
make test         # full pytest suite (uv run pytest tests/)
```

Or if you prefer to run them directly:

```bash
uv run ruff format .
uv run ruff check src/ tests/
uv run mypy src/cohezion --ignore-missing-imports --no-strict-optional --exclude 'mcp-builder'
uv run pytest tests/ -q
```

For the test suite specifically: the count should be at least one greater than baseline (your new tests), no previously-passing test should now fail, and any new failures are bugs in your implementation.

If your change has a runnable artifact (script, CLI command, API endpoint), run it. The project's verification rule is explicit on this:

> Tests use mocks and fixtures — they don't prove the real program works. **If there's a runnable program, RUN IT.**

For our running example, a runnable verification might look like:

```bash
uv run python -c "
from cohezion.vault.adr_index import find_adr_by_number
path = find_adr_by_number(1)
print(f'ADR-001 resolved to: {path}')
"
```

Output should be the actual filesystem path. If it is `None`, the implementation has a bug the tests did not catch — fix immediately, add a test that catches the failure mode, repeat.

> **Checkpoint.** Capture the verification output and paste it into the ADR's "Verification" section as the canonical evidence:
>
> ```markdown
> ## Verification
> - Static check: `ls docs/adrs/` shows ADR-001, ADR-002, ADR-003.
> - Runtime check: `python -c "from cohezion.vault.adr_index import find_adr_by_number; print(find_adr_by_number(1))"` returns `docs/adrs/ADR-001-eleven-step-compound-loop.md`.
> - Test: `uv run pytest tests/vault/test_adr_lookup.py -q` reports `5 passed`.
> ```
>
> The ADR is now self-validating: a future contributor can re-run those exact commands and confirm the change is intact.

## Stage 6 — Write the retrospective

Now the campaign discipline from Day 7 returns. Even for a single-developer architectural change, write a retrospective into the vault:

```bash
$EDITOR ~/vaults/cohezion-vault/retrospectives/<today>-<change-slug>.md
```

The structure mirrors the synthetic-sniffing-panda retrospective at `~/vaults/cohezion-vault/retrospectives/2026-04-23-synthetic-sniffing-panda.md`. The minimal sections:

- **Goal** — one sentence. What was the change.
- **Strategy** — one paragraph. How you approached it (ADR, review, TDD).
- **Numeric deltas** — table of before/after for any quantifiable thing (test count, coverage, LOC, etc.).
- **Commits** — list of SHAs with one-line descriptions.
- **Lessons** — 2-5 things you learned that are not in any existing rule, learning, or skill. These are candidates for the next learnings INDEX entry.
- **Next steps** — what is left undone, what should the next contributor pick up.

The retrospective is the artifact that makes the change *compound*. The ADR explains the decision; the retrospective explains the experience of executing it. Future contributors making similar changes will read both.

## Stage 7 — Update CLAUDE.md if the architecture changed

`CLAUDE.md` contains an "Architecture at a Glance" table with one row per major subsystem (Compound, Swarm, Cache, Cost Opt, Persistence, Physics, World Model, Bioelectric, Cosmogony, Worldviews, Ouroboros, Environments, Governance, Data Mesh, Providers, Genesis UI, Knowledge, Anthropic Intel). If your architectural change adds, removes, or substantially changes one of these subsystems, **update the table row**.

For the running example, you would add a row for "ADR Index" or update the "Knowledge" row to mention ADR lookup. Use the same column shape: `Layer | Components | Entry`.

If your change does not affect the table, do not touch it. `CLAUDE.md` is approximately 26 KB and is read on every session start; bloat is real cost.

> **Why this matters.** The PRFAQ exercise lists "Read CLAUDE.md (~26 KB)" as part of the Cohezion onboarding experience that is currently *too long* — and an architectural change that does not update CLAUDE.md is a mismatch between the running architecture and the documented architecture. The next contributor will read the documented version and be confused. Keeping the table in sync is the cheapest discipline for the largest payoff.

## Optional Stage 8 — Push and open a PR

If your change is intended to land on the shared remote, follow the workflow in `CONTRIBUTING.md`:

1. Create a feature branch from `develop` (not `main`).
2. Push the branch.
3. Open a PR targeting `develop`.
4. Reference the ADR in the PR body.
5. Reference the retrospective.
6. Wait for review (human or AI), iterate, merge when green.

For a Day-30 tutorial, the local branch with all artifacts is the deliverable. Push only if the user has explicitly authorized push (the project's git-operations rule is unambiguous: "NEVER execute git WRITE commands without EXPLICIT user permission" for write operations including push).

## What you just learned

1. **The full Cohezion contribution lifecycle has seven stages.** Triage (does it warrant an ADR?), ADR draft, adversarial review, TDD implementation, verification suite, retrospective, CLAUDE.md sync. Skipping a stage is the anti-pattern; the cost of skipping shows up in the next person's onboarding or the next contributor's bug.
2. **ADRs are forward-looking, not retroactive.** The two existing ADRs (ADR-001, ADR-002) were written retroactively because the project predated the discipline. From now on, write the ADR *before* the change. The ADR is the spec; the implementation is the deliverable.
3. **Adversarial review in parallel is the partial mitigation for "bus factor of one."** Three concurrent reviewers with different lenses (scientific rigor, edge cases, acceptance) catch issues a single reviewer would miss. The synthesis step is where cross-pollination happens. This is the closest the project has to a second human reviewer.
4. **TDD is non-negotiable for production code.** Red-Green-Refactor with the failing-test-first cycle. Recovery exists if you slip but is not the default.
5. **Verification is "evidence before claims."** Tests passing is necessary; running the actual program is the supplementary verification. Both go into the ADR's "Verification" section as canonical evidence the change is intact.
6. **Retrospectives compound.** Every change leaves a retrospective in the vault. The next change reads prior retrospectives via the compound loop's step-1 vault query. This is how the project gets better over time at making changes — not just at running them.
7. **Keep CLAUDE.md and the architecture in sync.** When you change the architecture, update the row. When you do not change the architecture, do not bloat the file. Both disciplines protect onboarding for the next contributor.

## Where you are now

You have completed the five-tutorial onboarding series. You can:

- Set up the project from a fresh clone, run a single test, make a trivial change, commit it surgically.
- Trace one execution end-to-end through the eleven-step compound loop and explain the learning arc, the diagnostics arc, and the safety check.
- Write a PRIME-format skill, register it in the metadata-only registry, and explain why the vault is canonical.
- Run a multi-wave parallel-agent polish campaign with verification gates and a written retrospective.
- Make a substantive architectural change with an ADR, adversarial review, TDD, verification, retrospective, and CLAUDE.md sync.

The project is unfinished. The PRFAQ exercise lists three over-claimed things, three under-claimed things, and three missing things — those are your future-month topics. The synthetic-sniffing-panda retrospective lists deferred work and "next campaign should pick up" items — those are your future-week topics. Read both when you are ready.

You are no longer onboarding. You are contributing.

→ Back to [Tutorial 4 — Day 7: Running a Campaign](./04-day-7-running-a-campaign.md).

→ Back to [Tutorial 1 — Day 1: Setup and First Test](./01-day-1-setup-and-first-test.md).

→ See the [tutorial INDEX](./INDEX.md) for the full series.
