---
title: Architecture Decision Records — Index
date: 2026-04-23
campaign: synthetic-sniffing-panda Wave Ω10 (retroactive ADRs)
maintainer: cohezion-project
---

# Architecture Decision Records (ADRs)

Standard Michael Nygard format. Each ADR is a stand-alone document — read in 5 minutes, understand the WHY of one major design choice. New ADRs use `TEMPLATE.md` as a starting point and are numbered sequentially.

## Index

| # | Title | Status | Reversal cost |
|---|---|---|---|
| [001](./ADR-001-eleven-step-compound-loop.md) | The Eleven-Step Compound Engineering Loop | ACCEPTED | HIGH |
| [002](./ADR-002-cost-routing-tiers.md) | Cost-Routing Tiers — 70/20/10 Local-First Model Selection | ACCEPTED | MEDIUM |
| [003](./ADR-003-skill-consensus-voter.md) | Skill Consensus Voter — Multi-Agent Voting Over Single-Agent Authority | ACCEPTED | LOW |
| [004](./ADR-004-vault-first-knowledge.md) | Vault-First Knowledge — Markdown as Source of Truth, MEMORY.md as Compiled Cache | ACCEPTED | HIGH |
| [005](./ADR-005-flume-256d-latent.md) | FLUME 256-Dimensional Latent Space — System-Wide Thought-Vector Invariant | ACCEPTED | MEDIUM |

## One-line summaries

- **ADR-001** — Every compound task walks a fixed eleven-step pipeline so that trajectories, metrics, and skill refinements are comparable across executions; this is what compound engineering compounds against.
- **ADR-002** — Route 70% of LM calls to free local models, 20% to Sonnet-class, 10% to Opus-class, with confidence-based escalation and `BudgetEnforcer` hard stops.
- **ADR-003** — Skill mutations require multi-agent consensus (majority / weighted / unanimous) so that no single agent can drift the compounding surface.
- **ADR-004** — Markdown vault is the canonical knowledge store; `MEMORY.md` is a 95-line compiled cache regenerated weekly.
- **ADR-005** — All FLUME latents are 256-dimensional, enforced by a Pydantic validator; the invariant matters more than the specific number.

## Conventions

- File names: `ADR-NNN-short-slug.md`, three-digit zero-padded number.
- Status values: `ACCEPTED`, `PROPOSED`, `DEPRECATED`, `SUPERSEDED-by-ADR-N`.
- Mark `RETROACTIVE` in the Status section if no prior explicit decision document existed.
- Cite specific `file:line` for every implementation claim.
- Keep each ADR between 600 and 1,200 words.
