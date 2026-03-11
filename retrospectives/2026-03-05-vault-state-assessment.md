---
title: "Vault State Assessment — 2026-03-05 (Consolidated)"
date: 2026-03-05
tags: [retrospective, meta, vault-architecture, compound-engineering, portfolio]
aliases: ["vault state assessment march 5", "consolidated assessment 2026-03-05"]
aspect: doer
neural:
  activation: 0.790
  stage: mature
  cluster: retrospectives
---

# Vault State Assessment — 2026-03-05 (Consolidated)

*Consolidated from three progressive vault reads on 2026-03-05 (morning, evening, late night) by Claude (Sonnet 4.6). Companion to the [[2026-03-05-shoshin-assessment|Shoshin Assessment]] written earlier the same day.*

---

## The Vault Turned a Corner

Unlike prior assessments written against a vault accumulating unaddressed problems, this day produced concrete artifacts:

- `concepts/cohezion-platform-overview.md` — a cold-session entry point in plain language
- `concepts/FLUME-Architecture.md` (rewritten) — surfaces real experimental numbers, anti-patterns, open questions
- `concepts/agentic-system-failure-taxonomy.md` — 45 lessons organized into 6 named failure categories
- `missions/anthropic-portfolio/README.md` (rewritten) — opens with the problem, not cosmology
- `decisions/2026-03-05-separate-cohezion-a-from-cohezion-b.md` — the two-Cohezions framing, accepted
- `projects/2026-03-05-repo-sync-master-plan.md` — 7 phases with dependency graph
- `projects/2026-03-05-vault-surrealdb-sync-pipeline.md` — PRD with 5 epics and story-level estimates

The vault is compounding again. These are architectural decisions and PRDs, not assessments about assessments.

---

## Hidden Gems in `patterns/`

The patterns directory contains production-grade technical work that isn't surfaced in the portfolio narrative:

- [[structured-experience-vector-layout]] — a complete RL experience vector with typed offsets and numpy accessors, directly connected to FLUME training data
- [[predictive-throttling-via-12d-trajectory-velocity]] — real code using trajectory velocity in semantic space as a resource allocation signal; thresholds calibrated from 5.5M overnight simulation trajectories
- [[morphospace-stability-wells]] — KDE-based behavioral region detection with working sklearn implementation, drift detection, and documented prerequisites

These are the kind of artifacts that demonstrate research engineering capability.

---

## The Decisions Directory Is the Intellectual Core

130+ decision notes document not just what was built but what failed and why:

- [[2026-02-23-hash-based-journey-tracking-produces-meaningless-12d-trajectories]] — SHA-256 hashes produce random walks in 12D space (average step distance ~1.4, indistinguishable from noise). Research-grade documentation of a real empirical finding.
- 15+ [[2026-02-24-anti-pattern-character-level-tokenizer-for-semantic-embeddings|anti-pattern decisions]] documenting what not to do, each with quantified reasoning.

Most systems document successes. This one documents failures with equal rigor. **This decisions corpus is the portfolio.**

---

## Problem: Core Concept Notes Are Artifact Indexes

The README rewrite revealed that the concept notes visitors will follow links to are bloated:

**[[compound-engineering]]** — 4 paragraphs of strong definitional content buried under ~120 lines of Agent Outputs (16 implementation plan versions), Session References, and Daily References. The concept note has become a file index.

**[[cohezion]]** — Good four-paragraph definition at the top. Then 300 lines of agent output inventories including a business plan, tax strategy, manifesto, and brand guide. These are Cohezion B artifacts that overwhelm the concept.

**[[anthropic-research-engineer]]** — 5 lines defining the role, 12 lines of agent output entries. Should be an argument for role fit, not a file cabinet.

**Fix:** Strip artifact indexes from all three. Move agent output inventories to archive notes. Let concept notes be concepts (~400 words, not 400 lines).

---

## Problem: Shell ADRs

Three ADRs auto-generated on 2026-03-05 have populated `rationale` in YAML frontmatter but empty Markdown body sections (`## Context`, `## Decision`, `## Chosen Option`, `## Alternatives Considered`). The knowledge was captured in YAML but never migrated into readable Markdown.

Affected:
- `decisions/2026-03-05-fresh-clone-completed-swap-pending-user-action.md`
- `decisions/2026-03-05-gc-fix-requires-fresh-clone-corrupt-objects-too-deeply-embedded.md`
- `decisions/2026-03-05-pr-33-merged-bmad-restoration-and-ci-fixes-on-main.md`

Likely more throughout `decisions/` — any template-generated ADR where only frontmatter was filled in.

---

## Problem: SurrealDB Is Stale

The graph shows 317 concepts but all notes written on 2026-03-05 are missing:

- `surrealdb_import_concepts` errors with `[Errno 2] No such file or directory` (path problem)
- `vault_search` does exact-string matching, not semantic search — returns no results for FLUME, EcoAgent, JourneyTracker, or ShadowScripter queries
- The 3D graph plugin's `SurrealDBClient.ts` sends queries without auth headers — it has never read from SurrealDB
- The health check tests `/health` (unauthenticated) and reports "ok" regardless of credential validity

**Impact:** Any agent using SurrealDB-backed retrieval works from a stale snapshot that predates the day's most important changes.

---

## Problem: Branch Inventory Reveals Unknown Scope

68 local branches exist, many with hundreds of unique commits:

- `feat/flume-vae-clean` — 16 unique commits (clean FLUME VAE implementation)
- `feat/flume-vae-phase1-phase2` — 505 unique commits
- `feat/hf-integration-v1.1.0` — 524 unique commits
- `feat/surrealdb-3.0-repository-implementation` — 490 unique commits

None of this is on `main` or in the vault. The FLUME numbers cited in the README (4.2 nats KL, 53% reconstruction improvement) come from experiment notes, not from a run of `feat/flume-vae-clean`. Whether the branch code matches the reported results is **unknown**.

---

## FLUME Diagnostic Remains Unrun

`experiments/2026-03-05-flume-kl-collapse-diagnostic.md` has status: `proposed`, results section: empty. Named as highest priority in every assessment this week. The 53% reconstruction improvement and 4.2 nats KL numbers are from 30 epochs, last updated February 24, and are presented as if they are final results.

---

## Priority Stack

Ordered by impact on April submission:

1. **Run FLUME KL diagnostic** — highest information-per-hour, validates or invalidates the core technical claim
2. **Rebuild 3 concept notes** (compound-engineering, cohezion, anthropic-research-engineer) — 1-2 hrs, fixes second-impression problem
3. **Fix shell ADRs** — migrate rationale from frontmatter YAML into readable Markdown bodies
4. **Fix `surrealdb_import_concepts` path error** — one-line fix enables graph-based retrieval of today's notes
5. **Clarify `feat/flume-vae-clean` relationship to README numbers** — validate that cited results match current code

Items 2-3 are a single focused session. Item 4 is a single command if the path is diagnosed. Item 5 requires the user to run code.

**Defer to post-submission:** `vault-surrealdb-architecture.md` sync daemon, specs migration — good work, but competes with submission-critical tasks.

---

## Related

- [[2026-03-05-shoshin-assessment]] — beginner's mind reading written earlier the same day
- [[cortex/compound-engineering]] — needs artifact index stripped
- [[cortex/cohezion]] — needs artifact index separated from definition
- [[cortex/anthropic-research-engineer]] — needs to become an argument, not a file cabinet
- [[cortex/FLUME-Architecture]] — rewritten today, not yet in SurrealDB
- [[cortex/cohezion-platform-overview]] — new today, not yet in SurrealDB
- [[cortex/agentic-system-failure-taxonomy]] — new today, not yet in SurrealDB
- [[laboratory/2026-03-05-flume-kl-collapse-diagnostic]] — highest priority unblocked task
- [[prefrontal/2026-03-05-separate-cohezion-a-from-cohezion-b]] — accepted
- [[prefrontal/2026-03-05-vault-surrealdb-architecture]] — fix for stale graph
- [[motor/2026-03-05-repo-sync-master-plan]] — 7-phase repo consolidation plan
- [[motor/2026-03-05-vault-surrealdb-sync-pipeline]] — PRD for sync pipeline
- [[motor/2026-03-05-branch-inventory]] — 68 branches with unknown relationship to vault
- [[structured-experience-vector-layout]] — exemplary pattern note
- [[predictive-throttling-via-12d-trajectory-velocity]] — exemplary pattern note
- [[2026-02-23-hash-based-journey-tracking-produces-meaningless-12d-trajectories]] — exemplary research-grade decision
