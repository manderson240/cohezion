---
title: "Repo and Process Debt"
date: "2026-02-22"
status: active
priority: high
tags: [project, technical-debt, process, repository]
aspect: doer
neural:
  activation: 0.87
  stage: mature
  synapse_in: 7
  synapse_out: 14
---

## Overview

Three foundational gaps that block sustainable development on Cohezion. These are not feature work — they are the scaffolding that makes all other work reliable and repeatable. A dedicated session should tackle each in order.

## Goals

1. **Coding standards** — Consistent style, linting, type checking, and formatting enforced via CI across all components (TypeScript plugin, Python tools, Python MCP server)
2. **Repo management** — Resolve the disconnected `track-c` / `main` branch histories; define a clear branching strategy; enforce branch protection rules
3. **Project management** — Establish lightweight PM conventions (issue tracking, milestone naming, PR templates, definition of done)

## Current Status

All three areas are currently ad-hoc. This creates compounding friction:
- Security reviews fail because `/security-review` assumes a common merge base (worked around locally, not fixed)
- No linting or type-checking CI — bugs only surface at runtime
- No standard PR template or definition of done — review quality is inconsistent
- Branch model is undocumented and confusing to new sessions

See [[2026-02-22-security-fixes-session-id-path-traversal-and-github-date]] for the security work done so far.

## Recommended Approach

### Phase 1 — Coding Standards (start here)

- Python: add `ruff`, `mypy`, `black` to all Python components; wire into pre-commit and CI
- TypeScript: enforce `eslint` + `prettier` in the 3d-graph-plugin
- Define a `CONTRIBUTING.md` with the standards clearly stated

### Phase 2 — Repo Management

- Decision: separate `track-c` content into its own repo OR graft histories
- If separate repos: vault repo (this one) + platform repo; update CI/CD accordingly
- If keep unified: create an orphan `root` commit that both branches reference (risky — see ADR)
- Enforce branch protection on `track-c` and `main` via GitHub settings

### Phase 3 — Project Management

- Add GitHub issue templates (bug, feature, security)
- Add PR template with checklist (tests, linting, security scan)
- Define milestone naming convention (v0.x = alpha, v1.x = stable)
- Establish a lightweight sprint cadence or kanban board

## Key Decisions

- [ ] Separate repos or stay unified? → ADR needed
- [ ] Which CI system? (GitHub Actions already partially in use)
- [ ] Monorepo tooling if staying unified? (nx, turborepo, or plain makefiles)

## Related ADRs

- [[2026-03-05-gc-fix-requires-fresh-clone-corrupt-objects-too-deeply-embedded]] — decision to fresh-clone after discovering 170+ corrupt objects in pack files
- [[2026-03-05-fresh-clone-completed-swap-pending-user-action]] — follow-up: clone completed, user action needed for swap
- [[2026-03-05-pr-33-merged-bmad-restoration-and-ci-fixes-on-main]] — PR #33 restored BMAD and fixed CI; 3,196 tests passing

## Related Experiments

- [[2026-03-05-ci-pipeline-debugging-cascading-failures-from-dev-deps-and-permissions]] — CI cascading failure investigation
- [[2026-03-05-gc-corruption-root-cause-entire-auto-commits-and-submodule-conflicts]] — root cause analysis of GC corruption
- [[2026-03-05-gc-corruption-severity-170-bad-objects-across-all-pack-files-3gb-data-file-in-hi]] — severity assessment of corrupt objects
- [[2026-03-05-unblocking-pr-33-ci-fixes-for-branch-protection]] — experiment to unblock PR #33 CI

## Related

- [[2026-02-19-github-flow-appropriate-for-pre-alpha]] — the decision establishing GitHub Flow as the branching strategy; directly addresses the repo management debt
- [[2026-02-13-gitlab-to-github-consolidation-with-artifact-governance]] — the consolidation decision that created the current track-c/main split being tracked here
- [[2026-02-22-security-fixes-session-id-path-traversal-and-github-date]] — security work that surfaced the impact of the disconnected branch histories on the security review process
- [[circleci-ai-cicd-validation]] — the CI/CD pattern that would implement the automated coding standards enforcement described in Phase 1
- [[data-governance-prevention-through-pre-commit-enforcement]] — pre-commit hooks for coding standards enforcement (ruff, mypy, black) are a form of data governance prevention applied to code quality
- [[compound-engineering]] — addressing process debt compounds reliability: each debt item fixed makes all future sessions more productive
- [[production-ready-definition-checklist]] — the "definition of done" Phase 3 goal maps directly to the production readiness checklist pattern
