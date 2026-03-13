---
title: "Branch Inventory — Non-Destructive Triage"
date: "2026-03-05"
status: active
priority: high
tags: [inventory, branches, triage, non-destructive, preservation]
aspect: doer
neural:
  activation: 0.65
  stage: growing
  synapse_in: 2
  synapse_out: 3
---

## Principle

> **Everything was created for a reason.** Never assume a branch won't contribute to the bigger picture.
> No deletions. Only triage, categorize, and preserve.

## Inventory (2026-03-05)

### Active Feature Work (unmerged, significant unique commits)

| Branch | Unique Commits | Description |
|--------|---------------|-------------|
| `feat/epic-5-shadowscripter-v1.3.0` | 523 | ShadowScripter epic |
| `feat/epic-8-unified-registry-v2` | 523 | Unified registry v2 |
| `feat/hf-integration-v1.1.0` | 524 | HuggingFace integration |
| `feat/yolo-party-mode-10k-tasks` | 524 | Large-scale task handling |
| `feat/flume-vae-clean` | 16 | Clean FLUME VAE implementation |
| `feat/flume-vae-phase1-phase2` | 505 | FLUME VAE multi-phase |
| `feat/flume-vae-pipeline` | 492 | FLUME VAE pipeline |
| `feat/compound-checkpoint-transparency-v2.0.0` | 491 | Compound checkpoint transparency |
| `feat/compound-coherence-dashboard-v2.0.0` | 491 | Coherence dashboard |
| `feat/compound-cost-visibility-v2.0.0` | 491 | Cost visibility |
| `feat/compound-progressive-api-v2.0.0` | 491 | Progressive API |
| `feat/compound-session-unified-api-v2.0.0` | 492 | Unified session API |
| `feat/model-pool-v1.1.0` | 491 | Model pool management |
| `feat/parallel-sprint-expansion-v1.2.0` | 492 | Parallel sprint expansion |
| `feat/semantic-release` | 497 | Semantic release automation |
| `feat/surrealdb-3.0-repository-implementation` | 490 | SurrealDB 3.0 repo layer |
| `feat/worktree-enforcement` | 493 | Worktree enforcement tooling |

### Spec/Investigation Branches

| Branch | Unique Commits | Description |
|--------|---------------|-------------|
| `docs/spec/cs249r-book-integration` | 477 | CS249R textbook integration |
| `docs/spec/fix-technical-debt` | 491 | Technical debt spec |
| `docs/spec/improved-universe-simulations` | 474 | Universe simulation improvements |
| `docs/spec/planning-vs-thinking-routing` | 473 | Planning vs thinking routing |
| `docs/spec/routes-consolidation` | 474 | Route consolidation |

### Fix/Security Branches

| Branch | Unique Commits | Description |
|--------|---------------|-------------|
| `fix/restore-bmad-and-critical-infrastructure` | 6 | **CURRENT** — PR #33 |
| `fix/bmad-memory-physics-restore` | 498 | BMAD memory + physics |
| `fix/guardrail-backend-wiring` | 494 | Guardrail backend |
| `fix/ide-error-resolution` | 503 | IDE error fixes |
| `fix/journey-substrate-hardening` | 455 | Journey substrate |
| `fix/vault-and-provenance-nfrs-v1.1.0-backup` | 501 | Vault + provenance NFRs |
| `security/hardening-clean-20260303` | 494 | Security hardening (clean) |
| `security/hardening-pr-20260304` | 2 | Security hardening PR |
| `security/hardening-review-20260303` | 555 | Security hardening review |

### Session/Archive Branches

| Branch | Unique Commits | Description |
|--------|---------------|-------------|
| `feat/session-56-opencode-vault` | 470 | Session 56 vault work |
| `feat/session-56-test` | 478 | Session 56 testing |
| `feat/session-57-session-start` | 463 | Session 57 start |
| `feat/session-58-audit-remediation` | 499 | Session 58 audit |
| `archive/entire/checkpoints/v1` | 366 | Checkpoint archive |
| `archive/legacy/codebase-review` | 481 | Legacy codebase review |
| `archive/legacy/swarm/audit_session_1` | 455 | Legacy swarm audit |
| Various `archive/entire/*` | 1-27 each | Auto-generated worktree snapshots |

### Release/Infrastructure

| Branch | Unique Commits | Description |
|--------|---------------|-------------|
| `release/v1.1.0` | 495 | Release branch |
| `main` | 491 | Main (note: diverged from track-c) |
| `tmp/worktree-setup` | 554 | Worktree setup tooling |

### Untracked Valuable Artifacts (working tree)

Located in `/home/mike-anderson/dev/cohezion/_bmad-output/`:

**Planning Artifacts:**
- `cosmogenesis-prd.md` — Product requirements for cosmogenesis
- `cosmogenesis-architecture.md` — Architecture for cosmogenesis
- `cosmogenesis-epics.md` — Epic breakdown
- `epics-vault-mcp-improvement.md` — Vault MCP improvement epics
- `prd-vault-mcp-improvement.md` — Vault MCP improvement PRD
- `architecture-unified-frontmatter-schema.md` — Unified frontmatter schema
- `research/tech-impl-contextual-swarm-grounding-2026-03-04.md` — Swarm grounding research

**Implementation Artifacts:**
- `6-1-ironwood-tpu-vm-provisioning.md` — TPU VM provisioning
- `6-2-xla-accelerated-latent-sharding.md` — XLA latent sharding
- `6-3-planetary-scale-cosmogenesis.md` — Planetary scale cosmogenesis
- `epic-6-retro-2026-03-05.md` — Epic 6 retrospective
- `hardware-assumptions-epic6.md` — Hardware assumptions
- `inception-labs-integration-report.md` — Inception Labs integration
- `production-scaling-plan.md` — Production scaling plan
- `sprint-status.yaml` — Sprint status
- Templates: `spike-story-template.md`, `aspirational-story-template.md`

**Test Artifacts:**
- Security violation test results (4 files)

**Other:**
- `design-thinking-2026-03-04.md` — Design thinking session output

## Triage Status

- [ ] Catalog unique content per branch in vault
- [ ] Identify branches that are truly redundant (same commits as merged PRs)
- [ ] Create spike branches for anything needing investigation
- [ ] Ensure _bmad-output/ artifacts are committed (currently untracked on main repo)

## Related

- [[2026-03-05-repo-sync-master-plan]] — master plan
- [[2026-03-05-vault-first-enforcement-protocol]] — enforcement protocol
- [[2026-03-05-non-destructive-operations-only-preserve-all-branch-work]] — governing decision
