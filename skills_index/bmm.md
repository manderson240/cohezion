---
title: "BMM — Business Model Module Skills Index"
date: 2026-03-07
tags: [skills-index, bmad, bmm, product-lifecycle]
---

# BMM — Business Model Module

**Prefix:** `bmad-bmm-*` | **Source:** `.claude/commands/bmad-bmm-*.md`

## Agent Personas
`architect`, `dev`, `qa`, `sm`, `pm`, `analyst`, `tech-writer`, `ux-designer`, `quick-flow-solo-dev`

## Skills by Lifecycle Phase

### Analysis
| Skill | Trigger |
|-------|---------|
| `bmad-bmm-technical-research` | "research X", "investigate Y" |
| `bmad-bmm-domain-research` | "domain research", "industry analysis" |
| `bmad-bmm-market-research` | "market research", "competitive analysis" |

### Planning
| Skill | Trigger |
|-------|---------|
| `bmad-bmm-create-prd` | "create a PRD" |
| `bmad-bmm-edit-prd` | "edit the PRD" |
| `bmad-bmm-validate-prd` | "validate PRD" |
| `bmad-bmm-create-product-brief` | "create product brief" |
| `bmad-bmm-create-architecture` | "design the architecture" |
| `bmad-bmm-create-ux-design` | "plan the UX" |

### Solutioning
| Skill | Trigger |
|-------|---------|
| `bmad-bmm-create-epics-and-stories` | "break into stories" |
| `bmad-bmm-create-story` | "create a story" |
| `bmad-bmm-sprint-planning` | "plan the sprint" |
| `bmad-bmm-sprint-status` | "check sprint status" |

### Implementation
| Skill | Trigger |
|-------|---------|
| `bmad-bmm-dev-story` | "implement story X" |
| `bmad-bmm-quick-dev` | "quick fix", "quick implementation" |
| `bmad-bmm-quick-spec` | "quick spec" |
| `bmad-bmm-qa-generate-e2e-tests` | "generate e2e tests" |
| `bmad-bmm-code-review` | "review this code" |

### Cross-cutting
| Skill | Trigger |
|-------|---------|
| `bmad-bmm-check-implementation-readiness` | "are we ready to build?" |
| `bmad-bmm-correct-course` | "course correct" |
| `bmad-bmm-retrospective` | "run retro" |
| `bmad-bmm-document-project` | "document this project" |
| `bmad-bmm-generate-project-context` | "generate project context" |

## Lifecycle Flow
```
research → product-brief → PRD → architecture → UX-design
  → epics-and-stories → sprint-planning → dev-story → code-review
  → sprint-status → retrospective
```

## Related
- [[skill-taxonomy-7-layer-architecture]]
- [[skill-routing-decision-tree]]
