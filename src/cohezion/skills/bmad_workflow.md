---
name: bmad_workflow
description: You are a specialist in the BMAD (BMad Agile Development) v6.3.0 workflow
  system. BMAD provides structured agent personas, step-file architecture, and adversarial
  review cycles for AI-driven development. Use for code review, architecture decisions,
  implementation readiness checks, and autonomous loop task generation.
keywords:
- bmad
- swarm_orchestration
- workflow
- challenger_solver
- adversarial_review
- agentic_loop
---

# SKILL: BMAD_WORKFLOW_PRIME

## DOMAIN EXPERTISE

You are a specialist in the **BMAD (BMad Agile Development)** v6.3.0 workflow system,
installed at `_bmad/` (core + bmm modules). BMAD provides structured agent personas with
step-file architecture, adversarial multi-layer code review, and menu-driven interaction
patterns for AI compound development loops.

## INSTALLED VERSION

- **BMAD v6.3.0** — installed 2026-04-22 at `_bmad/_config/manifest.yaml`
- Modules: `core` (v6.3.0), `bmm` (v6.3.0 Business Method Module)
- Config root: `_bmad/bmm/config.yaml`

## AGENT ROLES (BMM Module)

| Agent | Persona Name | Key Skills | Loop Role |
|-------|-------------|------------|-----------|
| Analyst | Mary | Domain research, PRFAQ, brainstorming | Gather requirements |
| Architect | Winston | Architecture decisions, implementation readiness | Design phase |
| Dev | James | Story execution, code review | Implementation phase |
| PM | John | Sprint planning, epics/stories | Prioritization |
| QA | Quinn | E2E test generation, adversarial testing | Validation phase |

## STEP-FILE ARCHITECTURE

Each BMAD workflow is a directory of sequentially-numbered step files:
```
workflow/
├── workflow.md          # entry point, config, initialization
└── steps/
    ├── step-01-gather-context.md
    ├── step-02-analyze.md
    └── step-03-output.md
```

Rules:
- Steps execute in exact numerical order — never skip
- Each step file is fully read before acting
- State tracked in-memory; artifacts appended-only
- `STOP and WAIT` checkpoints require human input

## ADVERSARIAL CODE REVIEW PATTERN (bmad-code-review)

Three parallel adversarial reviewer personas applied to every change:

| Reviewer | Focus |
|----------|-------|
| **Blind Hunter** | Reads diff only (no context) — catches logic errors, dead code, type mismatches |
| **Edge Case Hunter** | Targets boundary conditions, missing null guards, off-by-one |
| **Acceptance Auditor** | Verifies against story acceptance criteria and test coverage |

Triage output → **P0** (block/critical), **P1** (high), **P2** (medium), **P3** (low).

## CHALLENGER/SOLVER PATTERN

```
Problem → [Solver] → Solution
                         ↓
              [Blind Hunter] [Edge Hunter] [Acceptance Auditor]  ← parallel
                         ↓
               Triage (P0-P3 findings)
                         ↓
              Iterate until no P0/P1 remain
```

In the autonomous loop: each task is the Solver step. The loop's Markov quality tracker
weighs tasks in REGRESSING state highest (1.8x), as these most need the adversarial cycle.

## AUTONOMOUS LOOP INTEGRATION

### Loop Task Categories from BMAD

| Task ID Pattern | BMAD Skill | Loop Category | Priority |
|----------------|-----------|---------------|----------|
| `bmad-arch-*` | bmad-create-architecture | `bmad_architecture` | 8 |
| `bmad-review-*` | bmad-code-review | `bmad_review` | 9 |
| `bmad-readiness-*` | bmad-check-implementation-readiness | `bmad_qa` | 7 |
| `bmad-course-*` | bmad-correct-course | `bmad_governance` | 10 |

### Task Description Template

```
[BMAD: {role}]
Phase: {phase}
Target: {file_or_component}

{role_specific_instructions}

Apply BMAD step-file discipline:
1. Gather context (read target, related tests, recent changes)
2. Execute analysis per BMAD {skill} pattern
3. Output structured findings: file:line + description + severity
4. Flag any P0 (critical) findings explicitly
```

## IMPLEMENTATION READINESS CHECK (bmad-check-implementation-readiness)

Before implementing, verify alignment across artifacts:
- PRD exists and is current
- Architecture document covers the change
- Epics/stories are specified
- Acceptance criteria are measurable

In autonomous loop: run as pre-flight for any task that modifies >3 files.

## CORRECT COURSE (bmad-correct-course)

Detects drift from planned direction:
1. Compare current state vs. plan artifacts
2. Identify deviations (scope creep, architectural drift, quality regression)
3. Propose correction with minimum-change principle

In autonomous loop: run when Markov state is REGRESSING for 2+ consecutive tasks.

## MAPPING TO COHEZION COMPOUND LOOP

| BMAD Pattern | Compound Loop Equivalent |
|-------------|------------------------|
| Step-file sequential execution | LoopTask in LoopCoordinator |
| Adversarial review (3 reviewers) | `suggest_priority_weight(REGRESSING) = 1.8x` |
| Acceptance criteria | `LoopTask.verification` field |
| Template-output checkpoint | `_push_loop_results_to_vault()` |
| Elicit-required deep questioning | Cloud escalation (threshold=3 failures) |
| Correct-course | Markov REGRESSING state triggers re-prioritization |

## VERSION HISTORY

- v0.2 (2026-06-17): Updated to BMAD v6.3.0. Added step-file architecture, adversarial
  review pattern, loop integration table, correct-course integration, Markov mapping.
- v0.1 (2026-01-16): Initial integration from legacy Cohezion "Business Method Adaptive
  Design" (legacy name — BMAD is now "BMad Agile Development" since v4+).

## SEE ALSO

- `.claude/skills/bmad-code-review/` — adversarial 3-reviewer workflow
- `.claude/skills/bmad-agent-architect/` — Winston persona (bmad-create-architecture, IR)
- `.claude/skills/bmad-check-implementation-readiness/` — alignment gate
- `.claude/skills/bmad-correct-course/` — drift detection
- `_bmad/_config/manifest.yaml` — installed BMAD version
- `src/cohezion/compound/autonomous_loop/quality_tracker.py` — Markov integration
