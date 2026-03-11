---
title: "GDS — Game Development Studio Skills Index"
date: 2026-03-07
tags: [skills-index, bmad, gds, game-development]
---

# GDS — Game Development Studio

**Prefix:** `bmad-gds-*` | **Source:** `.claude/commands/bmad-gds-*.md`
**Status:** Dormant unless game project active. See [[2026-03-07-skill-pruning-consolidation-plan]].

## Agent Personas
`game-architect`, `game-designer`, `game-dev`, `game-qa`, `game-scrum-master`, `game-solo-dev`, `tech-writer`

## Skills by Phase

### Preproduction
| Skill | Trigger |
|-------|---------|
| `bmad-gds-create-game-brief` | "create game brief" |
| `bmad-gds-game-brief` | "game brief" (duplicate — see pruning plan) |
| `bmad-gds-brainstorm-game` | "brainstorm a game" |

### Design
| Skill | Trigger |
|-------|---------|
| `bmad-gds-create-gdd` | "create game design doc" |
| `bmad-gds-gdd` | "GDD" (duplicate — see pruning plan) |
| `bmad-gds-narrative` | "write narrative" |

### Technical
| Skill | Trigger |
|-------|---------|
| `bmad-gds-game-architecture` | "design game architecture" |
| `bmad-gds-quick-spec` | "quick game spec" |
| `bmad-gds-quick-dev` | "quick game dev" |

### Production
| Skill | Trigger |
|-------|---------|
| `bmad-gds-dev-story` | "implement game story" |
| `bmad-gds-create-story` | "create game story" |
| `bmad-gds-sprint-planning` | "game sprint planning" |
| `bmad-gds-sprint-status` | "game sprint status" |
| `bmad-gds-code-review` | "review game code" |
| `bmad-gds-correct-course` | "game course correct" |
| `bmad-gds-retrospective` | "game retro" |
| `bmad-gds-document-project` | "document game project" |
| `bmad-gds-generate-project-context` | "generate game project context" |

### Testing
| Skill | Trigger |
|-------|---------|
| `bmad-gds-gametest-framework` | "create test framework" |
| `bmad-gds-gametest-test-design` | "design game tests" |
| `bmad-gds-gametest-automate` | "automate game tests" |
| `bmad-gds-gametest-test-review` | "review game tests" |
| `bmad-gds-gametest-playtest-plan` | "playtest plan" |
| `bmad-gds-gametest-performance` | "game performance tests" |

## Lifecycle Flow
```
brainstorm-game → game-brief → GDD → narrative → game-architecture
  → sprint-planning → create-story → dev-story → code-review
  → gametest-* → sprint-status → retrospective
```

## Related
- [[skill-taxonomy-7-layer-architecture]]
- [[bmm]] (shared production skills pattern)
