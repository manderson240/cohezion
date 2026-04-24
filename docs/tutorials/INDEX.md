---
title: "Cohezion Onboarding — Tutorial Index"
audience: new contributors
total_tutorials: 5
estimated_total_time: ~12-20 hours of focused work spread over 30 days
created: 2026-04-23
campaign: synthetic-sniffing-panda (Wave Ω16)
---

# Cohezion Onboarding — Tutorial Index

A five-tutorial series that takes a new contributor from "fresh checkout" to "I can make an architectural change with proper process." The series is paced over 30 days because architectural maturity in this project is paced; you cannot read a 26 KB `CLAUDE.md` once and absorb the eleven-step compound loop, the vault-first knowledge architecture, the cosmogonic autonomy ladder, and the polish-campaign-orchestrator pattern in one sitting. Each tutorial isolates one layer.

## Suggested order

Read the tutorials in numerical order. Each tutorial assumes the previous ones; skipping ahead breaks the conceptual scaffold.

| # | Tutorial | Day | Estimated time | What you will be able to do after |
|---|---|---|---|---|
| 1 | [Setup and Your First Passing Test](./01-day-1-setup-and-first-test.md) | Day 1 | 60-90 min | Clone, install via `uv`, run a single test, edit a docstring, re-run, commit locally. |
| 2 | [The Eleven-Step Compound Loop](./02-day-2-the-compound-loop.md) | Day 2 | 2-3 hours | Trace one execution end-to-end through `CompoundExecutor.execute_task()`. Name the learning arc, diagnostics arc, and safety check. |
| 3 | [Skills and the Vault](./03-day-3-skills-and-vault.md) | Day 3 | 2-3 hours | Read a PRIME skill. Write a new one. Register it in the metadata-only registry. Explain why the vault is canonical. |
| 4 | [Running a Polish Campaign](./04-day-7-running-a-campaign.md) | Day 7 | 3-4 hours wallclock | Run a 4-wave micro-campaign with parallel agents and verification gates. Produce a vault retrospective. |
| 5 | [Contributing an Architectural Change](./05-day-30-contributing-an-architectural-change.md) | Day 30 | 6-12 hours over 2-3 days | Write an ADR. Get adversarial review. Implement with TDD. Run verification. Write retrospective. Update `CLAUDE.md`. |

## Background reading (do before Tutorial 1)

These are the canonical project documents. The tutorials reference them throughout; reading them first reduces the amount of cross-link chasing.

- [`CLAUDE.md`](../../CLAUDE.md) — architectural overview, ~26 KB. Read once linearly, then use as lookup.
- [`CONTRIBUTING.md`](../../CONTRIBUTING.md) — branch strategy, conventional commits, pre-commit hooks.
- [`pyproject.toml`](../../pyproject.toml) — dependency pins, ruff config, mypy config, pytest config.

## Background reading (do alongside Tutorial 2 onward)

- [ADR-001 — The Eleven-Step Compound Engineering Loop](../adrs/ADR-001-eleven-step-compound-loop.md) — the rationale for the loop's invariant ordering. Read with Tutorial 2.
- [ADR-002 — Cost-Routing Tiers (70/20/10 Local-First)](../adrs/ADR-002-cost-routing-tiers.md) — the rationale for the cost-aware router's tier policy. Useful background for Tutorial 3.
- `research/distillates/2026-04-23-vault-decisions-distillate.md` — distilled summary of the vault's decisions corpus. Useful for Tutorial 3.
- `research/prfaq/2026-04-23-cohezion-prfaq.md` — Working-Backwards exercise that frames *why* Cohezion exists. Useful for Tutorial 5.
- `~/vaults/cohezion-vault/retrospectives/2026-04-23-synthetic-sniffing-panda.md` — the reference 17-hour campaign's retrospective. Read before Tutorial 4.
- `~/.claude/skills/polish-campaign-orchestrator/SKILL.md` — the canonical campaign-orchestration skill. Read before Tutorial 4.
- `~/.claude/plans/synthetic-sniffing-panda.md` — the reference 17-hour campaign's plan markdown. Read before Tutorial 4.

## What this series does NOT cover

The tutorials are deliberately scoped to the contributor's *engineering* arc. The following surfaces are out of scope and have their own onboarding paths:

- **The Rust physics core (`src/cohezion-physics-core/`).** Has its own Cargo workspace and toolchain. See its `README.md`.
- **The Next.js dashboard (`src/web/anima_dashboard/`).** Three.js + Tone.js + React; substantial frontend onboarding of its own.
- **The FLUME VAE training pipeline.** Documented in `docs/deep-dive-world-model.md` and the FLUME manuscript under `research/manuscripts/`.
- **The cosmogonic autonomy ladder.** Conceptually introduced in `CLAUDE.md` and the PRFAQ; the production wiring lives in `src/cohezion/governance/` (autonomy_engine + cosmogonic tiers).
- **Kaggle / competition-related work.** Lives in dedicated worktrees (`.worktrees/nemotron-june/`, `.worktrees/agi-golf/`); see `~/.claude/rules/kaggle-portfolio.md` for the orientation.
- **Multi-IDE coordination (BMAD, Cline, Cursor, Gemini CLI).** In progress per learnings 371-376; partial.

When you are ready to extend into one of these areas, treat its primary documentation as a Tutorial 6 of the appropriate flavor — read it linearly, take a small first edit, verify, commit.

## Conventions used across the tutorials

- **Absolute paths in code blocks.** The tutorials assume your checkout is at `~/dev/cohezion`; substitute as needed.
- **`uv` for all Python operations.** `uv run pytest`, `uv pip install`, `uv venv`. Bare `pip` is banned.
- **`-q` for all pytest invocations** unless explicitly debugging a single test.
- **Conventional-commit prefixes** for all suggested commit messages: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`.
- **Surgical-commit discipline (Learnings 363, 368).** The `git diff --cached --name-only` check before commit is referenced repeatedly.
- **No-push policy.** None of the tutorials instruct you to `git push`. Project policy treats push as a write operation requiring explicit user permission.

## Feedback and improvements

If you find a step that does not work, a command that has rotted, a checkpoint that is wrong, or a section that is unclear: edit the tutorial. The tutorials live in the repo (`docs/tutorials/`) and are versioned with the rest of the codebase. Open a PR. Reference the change in the relevant retrospective.

The series itself was produced by the synthetic-sniffing-panda Wave Ω16 (the 5-tutorial onboarding-series wave). The Wave Ω10 retroactive ADRs ([001](../adrs/ADR-001-eleven-step-compound-loop.md), [002](../adrs/ADR-002-cost-routing-tiers.md)) supplied the architectural framing; the Wave Ω8 PRFAQ exercise supplied the "why"; the Wave Ω5 retrospective supplied the campaign-orchestration model. This is the project's own compound-engineering thesis applied to its own onboarding documentation: every prior wave makes the next wave's deliverable cheaper.
