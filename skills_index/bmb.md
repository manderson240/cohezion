---
title: "BMB — BMAD Module Builder Skills Index"
date: 2026-03-07
tags: [skills-index, bmad, bmb, meta, module-builder]
---

# BMB — BMAD Module Builder (Meta)

**Prefix:** `bmad-bmb-*` | **Source:** `.claude/commands/bmad-bmb-*.md`

## Agent Personas
`agent-builder`, `module-builder`, `workflow-builder`

## Skills

### Agent Operations
| Skill | Trigger |
|-------|---------|
| `bmad-bmb-create-agent` | "create a BMAD agent" |
| `bmad-bmb-edit-agent` | "edit agent" |
| `bmad-bmb-validate-agent` | "validate agent" |

### Workflow Operations
| Skill | Trigger |
|-------|---------|
| `bmad-bmb-create-workflow` | "create workflow" |
| `bmad-bmb-edit-workflow` | "edit workflow" |
| `bmad-bmb-validate-workflow` | "validate workflow" |
| `bmad-bmb-rework-workflow` | "rework workflow to V6" |
| `bmad-bmb-validate-max-parallel-workflow` | "validate parallel workflow" |

### Module Operations
| Skill | Trigger |
|-------|---------|
| `bmad-bmb-create-module` | "create BMAD module" |
| `bmad-bmb-edit-module` | "edit module" |
| `bmad-bmb-validate-module` | "validate module" |
| `bmad-bmb-create-module-brief` | "create module brief" |

## Meta Flow
```
create-module-brief → create-module
create-agent / create-workflow (independently)
validate-agent / validate-workflow / validate-module (quality gates)
edit-* (modifications)
rework-workflow (V6 compliance upgrade)
```

## Related
- [[skill-taxonomy-7-layer-architecture]]
- [[bmad-workflow-orchestration]]
