---
title: "Scale-Adaptive Documentation (from BMAD)"
date: "2026-02-08"
tags: [pattern, documentation, process-scaling, extracted-from-bmad]
aspect: thinker
neural:
  activation: 0.72
  stage: growing
  synapse_in: 10
  synapse_out: 11
---
## Problem

Projects range from single-line bug fixes to enterprise-scale rewrites, but teams tend to apply the same documentation process to all of them. Small changes drown in unnecessary PRDs and architecture docs; large changes ship with a one-line commit message.

## Solution

Define 5 discrete **project levels** (0–4) and scale documentation requirements proportionally:

| Level | Name | Stories | Documentation Required |
|-------|------|---------|----------------------|
| 0 | Single Atomic Change | 1 | Commit message only |
| 1 | Small Feature | 1–10 | Tech spec |
| 2 | Medium Project | 5–15 | PRD + optional tech spec |
| 3 | Complex System | 12–40 | PRD + architecture + JIT tech specs |
| 4 | Enterprise Scale | 40+ | PRD + architecture + JIT tech specs |

Architecture documents are only produced at Level 3+. Below that, the overhead isn't justified.

### Level Detection

Use keyword heuristics to auto-suggest the level:

```yaml
detection_hints:
  keywords:
    level_0: ["fix", "bug", "typo", "small change", "quick update", "patch"]
    level_1: ["simple", "basic", "small feature", "add", "minor"]
    level_2: ["dashboard", "several features", "admin panel", "medium"]
    level_3: ["platform", "integration", "complex", "system", "architecture"]
    level_4: ["enterprise", "multi-tenant", "multiple products", "ecosystem"]
```

### Greenfield vs Brownfield Paths

Each level has two workflow paths — greenfield (new project) and brownfield (existing codebase) — because the documentation needs differ. A greenfield Level 3 needs full architecture; a brownfield Level 3 may only need delta documentation against the existing architecture.

## Application to Cohezion

Cohezion's compound engineering vault could adopt this by:

1. Adding a `level` field to `decisions/` and `experiments/` frontmatter (0–4)
2. Adjusting template completeness based on level — Level 0 decisions skip the Alternatives section; Level 3+ require full ADR format
3. Using the level in `find_relevant_context()` to weight results — prior Level 3+ decisions are more architecturally significant

**Effort**: Small — frontmatter field + template conditionals.

## When to Use

- Starting any new project or feature — classify it first
- Onboarding contributors who over- or under-document
- Sprint planning, to calibrate documentation expectations

## When NOT to Use

- Research-only work (papers, concepts) — doesn't follow the story model
- Ops/infrastructure changes where runbook matters more than PRDs

## Origin

Extracted from BMAD `bmm/workflows/workflow-status/project-levels.yaml` and the greenfield/brownfield path system. BMAD implemented this with 11 YAML path files — the concept is sound but the implementation was over-engineered for its scope.

## Related

- [[compound-engineering]] — level classification makes compound records more useful
- [[bmad-workflow-orchestration]] — levels determine which workflows are activated

## Decisions & Experiments
- 📋 [[2026-02-08-bmad-framework-removal]] - 2026-02-08-bmad-framework-removal

## Related Concepts

- [[dna-origami-2d-semiconductor-patterning]]
- [[entire-io-to-vault-mapping]]
- [[automated-concept-extraction]]
- [[sheetsbr idge-mcp-testing]]
- [[phase1-production-validation-runbook]]
- [[typescript-error-diagnostic]]
- [[phase1-mcp-tool-reference]]
- [[surrealdb-query-driven-analysis]]
