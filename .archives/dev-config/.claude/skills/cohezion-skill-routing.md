---
name: cohezion-skill-routing
description: Skill routing decision tree and keyword-to-skill mapping for Cohezion's 7-layer skill ecosystem. Covers lifecycle phase routing, domain routing (BMM vs GDS), keyword tables, overlap resolution (spec vs quick-spec, BMM vs PR toolkit, retrospect vs BMM retrospective). Use when deciding which skill to use, routing a request, resolving skill ambiguity, or when user asks "which skill", "what command", "help me route".
---

# Skill Routing Quick Reference

## Decision Tree (Priority Order)

When a natural language request arrives, route using this priority:

1. **Exact match** — Does it match a `/slash-command`? Execute directly
2. **Lifecycle phase** — What phase of work?
   - Research/Analysis: `bmad-bmm-technical-research`, `bmad-bmm-domain-research`, `bmad-bmm-market-research`
   - Planning/Design: `bmad-bmm-create-prd`, `bmad-bmm-create-architecture`, `bmad-bmm-create-ux-design`
   - Implementation: `bmad-bmm-dev-story`, `bmad-bmm-quick-dev`, or `/spec` (structured TDD)
   - Testing: `bmad-tea-testarch-test-design`, `test-fix`
   - Review: `bmad-bmm-code-review`, `pr-review-toolkit:review-pr`
   - Maintenance: `retrospect`, `bmad-bmm-correct-course`, `deploy`, `heal`
3. **Domain** — Game dev? Use `bmad-gds-*` variant. General product? Use `bmad-bmm-*`
4. **Meta** — About BMAD itself? Use `bmad-bmb-*` (agent/workflow/module builder)
5. **Creative** — Ideation/innovation? `bmad-brainstorming`, `bmad-cis-design-thinking`
6. **Tool need** — External data? Library docs: `context7` | Papers: `cohezion-research` | GitHub: `github` MCP | Knowledge graph: `cohezion-surreal` | Multi-perspective: `cohezion-swarm`

## Top Keyword-to-Skill Routing

| Keywords | Primary Skill | Fallback |
|----------|---------------|----------|
| "research", "investigate" | `bmad-bmm-technical-research` | `bmad-bmm-domain-research` |
| "PRD", "requirements" | `bmad-bmm-create-prd` | `bmad-bmm-edit-prd` |
| "architecture", "system design" | `bmad-bmm-create-architecture` | — |
| "story", "epic" | `bmad-bmm-create-story` | `bmad-bmm-create-epics-and-stories` |
| "sprint", "planning" | `bmad-bmm-sprint-planning` | `bmad-bmm-sprint-status` |
| "implement", "build", "code this" | `bmad-bmm-dev-story` | `bmad-bmm-quick-dev` |
| "test", "QA" | `bmad-tea-testarch-test-design` | `test-fix` |
| "review", "code review" | `bmad-bmm-code-review` | `pr-review-toolkit:review-pr` |
| "brainstorm", "ideate" | `bmad-brainstorming` | `bmad-cis-design-thinking` |
| "game", "gameplay" | Route to `bmad-gds-*` variant | — |
| "deploy", "ship" | `deploy` | — |
| "fix tests", "failing tests" | `test-fix` | — |
| "commit", "push", "PR" | `commit-commands:commit` | `commit-commands:commit-push-pr` |
| "spec", "structured dev" | `/spec` | — |
| "what now", "help" | `bmad-help` | — |

## Overlap Resolution (Key Ambiguities)

| Ambiguity | Resolution |
|-----------|------------|
| BMM vs GDS variants (code-review, sprint, story) | Domain context: game project = GDS, otherwise = BMM |
| `bmad-brainstorming` vs `superpowers:brainstorming` | `superpowers` is a meta-prompt enhancer; `bmad-brainstorming` is the interactive workflow |
| `/spec` vs `bmad-bmm-quick-spec` | `/spec` = full TDD workflow; `quick-spec` = lightweight for small changes |
| `bmad-bmm-code-review` vs `pr-review-toolkit:review-pr` | BMM = general code review; PR toolkit = PR-specific with GitHub integration |
| `retrospect` vs `bmad-bmm-retrospective` | `retrospect` = dev-focused (flows into core files); BMM = product lifecycle |

**When in doubt**: `bmad-help` — analyzes context and suggests the best next action.

**Skill sources (7 layers)**: BMAD commands (~90), project commands (3), project skills (1), global commands (7), global rules (~15), plugin skills (~40), MCP tools (~80).
