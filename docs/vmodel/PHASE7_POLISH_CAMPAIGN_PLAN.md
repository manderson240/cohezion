# V-Model Phase 7 — Polish Campaign Verification (Retrofit)

**Workstream:** synthetic-sniffing-panda — full campaign (Waves 1-5 + D + Ω + ψ)
**Status:** implementation shipped 2026-04-23 (97 commits across 6 polish/* branches); this doc is the retrofit plan that names the invariants the shipped polish must satisfy.
**Pairs with:** `scripts/validation/vmodel/phase7_polish_campaign_harness.py` (AutoHarness), the merged content on `main` (post-merge), and the campaign artifacts in `research/`, `docs/`, `~/vaults/cohezion-vault/`.

## 1. Requirement

A multi-wave parallel-agent polish campaign on the cohezion ecosystem, producing measurable improvements across code quality, test coverage, knowledge consolidation, and design — with NO regressions to existing test/lint/mypy baselines and NO unaddressed CRITICAL security findings.

## 2. Descending Path

### 2.1 Workstream design
- Wave 1 (Reclaim & Stabilize) — disk + lint + mypy install + worktree triage
- Wave 2 (Code Quality) — bare-except, monolith splits, mypy ramp, shell-safety
- Wave 3 (Tests & Coverage) — coverage push, skip triage, sleep removal, conftest hardening
- Wave 4 (Knowledge & Vault) — Learning INDEX, vault dedup, skill consolidation, rules merge, anthropic-intel adoption, hook hardening
- Wave 5 (Close-Out) — plan close-out, orphan audit, cross-repo lint, branch hygiene, retrospective, polish-campaign-orchestrator skill
- Wave D (Design) — Figma diagrams, dashboard mockups, algorithmic art
- Wave Ω (Deep Inference) — manuscripts, ADRs, distillates, adversarial reviews, security review, refactor proposal, remediation plan, market research, canvas poster, themed mockups, onboarding tutorials, worldview essay
- Wave ψ (Merge Pipeline) — branch organization, MERGE_READINESS, out-of-tree audit, non-interference audit, Ω12 patch application, push, auto-merge

### 2.2 Invariants

| # | Invariant | Verification | Rationale |
|---|-----------|--------------|-----------|
| P1 | `src/cohezion/api/__init__.py` ≤ 400 LOC | structural | Wave 2B target (was 2,099) |
| P2 | `src/cohezion/skills/cohezion_mcp.py` ≤ 400 LOC | structural | Wave 2C target (was 1,530) |
| P3 | `src/cohezion/api/routes/` directory contains ≥ 7 router files | structural | Wave 2B router extraction |
| P4 | `src/cohezion/compound/executor_helpers/` exists with ≥ 3 helper files | structural | Wave 2D extraction |
| P5 | `src/cohezion/compound/executor.py` contains top-level `import asyncio` | structural | Ω12 Patch 1 (Ω5 must-fix #1) |
| P6 | `src/cohezion/mcp/hookify_server.py` defines `_validate_identifier` | structural | Ω12 Patch 2 (Ω6 CRITICAL-1+2) |
| P7 | `src/cohezion/mcp/servers/report/server.py` does NOT contain `shell=True` | structural | Ω12 Patch 4 (Ω6 CRITICAL-4) |
| P8 | Stealth-bare-except violations ≤ 2 (`grep -rn "except (.*Exception" src/cohezion`) | structural | Wave 2A + Learning 359 |
| P9 | S603/S607 ruff violations = 0 | tool-based | Wave 2F target |
| P10 | `tests/compound/` test count ≥ 968 passing | test-suite | Wave 3 floor |
| P11 | `tests/swarm/test_cost_aware_router_coverage_wave3b.py` exists with ≥ 15 tests | structural | Wave 3B |
| P12 | `tests/cache/test_semantic_cache_coverage_wave3c.py` exists with ≥ 10 tests | structural | Wave 3C |
| P13 | `tests/knowledge_graph/` directory contains ≥ 1 test file with ≥ 8 tests | structural | Wave 3D |
| P14 | `research/manuscripts/` contains ≥ 4 manuscript files | structural | Waves Ω1, Ω2, Ω3, Ω9 |
| P15 | `docs/adrs/` contains ADR-001 through ADR-005 + INDEX.md + TEMPLATE.md | structural | Wave Ω10 |
| P16 | `docs/tutorials/` contains 5 tutorial files + INDEX.md | structural | Wave Ω16 |
| P17 | `research/reviews/2026-04-23-omega6-security-review.md` exists | structural | Wave Ω6 audit landed |
| P18 | `research/remediation/2026-04-23-omega5-omega6-remediation-plan.md` exists | structural | Wave Ω12 plan landed |
| P19 | Project mypy error count ≤ 785 (Wave 2E target) | tool-based | Wave 2E ceiling |
| P20 | Project ruff error count ≤ 1026 (Wave 1C+ target) | tool-based | Wave 1C ceiling |

### 2.3 Acceptance criterion

`make vmodel-phase7` runs the harness; exit 0 confirms all 20 invariants hold on the currently-checked-in code. If the harness fails on a structural invariant, the polish work has drifted from its acceptance contract; if it fails on tool-based count (P9, P19, P20), regression has occurred.

## 3. Apex

The merged content on `main` after PRs #76-#81 land (currently auto-merge-queued). The harness verifies the post-merge state.

## 4. Ascending Path

- **Unit** → existing pytest suite (especially Wave 3 additions)
- **Integration** → this harness (`phase7_polish_campaign_harness.py`)
- **System** → manual review of MERGE_PLAN.md + per-branch PR descriptions
- **Acceptance** → user signoff via PR merge to main
