---
name: 'bmad'
description: 'BMAD Method hub - access all workflows, tasks, reviews, and utilities. Usage: /bmad <workflow-name> or /bmad to browse.'
---

# BMAD Method Dispatcher

Route to the requested BMAD workflow. User request: $ARGUMENTS

## If No Specific Workflow Requested

1. Call `bmad_help` MCP tool for guidance
2. Call `bmad_list_workflows` to show available workflows
3. Present the module categories below and wait for user selection

## Dispatch Instructions

Match the user's request against the **Keyword** column below. Then follow the dispatch pattern:

**Pattern A (workflow.md):** Read the indicated `.md` file and follow its instructions exactly.
**Pattern B (engine):** Load `_bmad/core/tasks/workflow.xml`, then pass the indicated `.yaml` path as the `workflow-config` parameter. Follow workflow.xml instructions exactly.
**Pattern C (xml-task):** Read the indicated `.xml` file and follow its instructions exactly.

---

## BMM - Business Method Module

### Analysis & Research
| Keyword | Description | Pattern | File |
|---------|-------------|---------|------|
| create-product-brief | Create product brief | A | `_bmad/bmm/workflows/1-analysis/create-product-brief/workflow.md` |
| domain-research | Domain research | A | `_bmad/bmm/workflows/1-analysis/research/workflow-domain-research.md` |
| market-research | Market research | A | `_bmad/bmm/workflows/1-analysis/research/workflow-market-research.md` |
| technical-research | Technical research | A | `_bmad/bmm/workflows/1-analysis/research/workflow-technical-research.md` |

### Planning
| Keyword | Description | Pattern | File |
|---------|-------------|---------|------|
| create-prd | Create PRD | A | `_bmad/bmm/workflows/2-plan-workflows/create-prd/workflow-create-prd.md` |
| edit-prd | Edit PRD | A | `_bmad/bmm/workflows/2-plan-workflows/create-prd/workflow-edit-prd.md` |
| validate-prd | Validate PRD | A | `_bmad/bmm/workflows/2-plan-workflows/create-prd/workflow-validate-prd.md` |
| create-ux-design | Create UX design | A | `_bmad/bmm/workflows/2-plan-workflows/create-ux-design/workflow.md` |

### Solutioning
| Keyword | Description | Pattern | File |
|---------|-------------|---------|------|
| create-architecture | Create architecture | A | `_bmad/bmm/workflows/3-solutioning/create-architecture/workflow.md` |
| create-epics-and-stories | Create epics and stories | A | `_bmad/bmm/workflows/3-solutioning/create-epics-and-stories/workflow.md` |
| check-implementation-readiness | Check implementation readiness | A | `_bmad/bmm/workflows/3-solutioning/check-implementation-readiness/workflow.md` |

### Implementation
| Keyword | Description | Pattern | File |
|---------|-------------|---------|------|
| bmm-code-review | Code review | B | `_bmad/bmm/workflows/4-implementation/code-review/workflow.yaml` |
| bmm-create-story | Create story | B | `_bmad/bmm/workflows/4-implementation/create-story/workflow.yaml` |
| bmm-dev-story | Dev story | B | `_bmad/bmm/workflows/4-implementation/dev-story/workflow.yaml` |
| bmm-correct-course | Correct course | B | `_bmad/bmm/workflows/4-implementation/correct-course/workflow.yaml` |
| bmm-sprint-planning | Sprint planning | B | `_bmad/bmm/workflows/4-implementation/sprint-planning/workflow.yaml` |
| bmm-sprint-status | Sprint status | B | `_bmad/bmm/workflows/4-implementation/sprint-status/workflow.yaml` |
| bmm-retrospective | Retrospective | B | `_bmad/bmm/workflows/4-implementation/retrospective/workflow.yaml` |

### Other BMM
| Keyword | Description | Pattern | File |
|---------|-------------|---------|------|
| quick-spec | Quick spec | A | `_bmad/bmm/workflows/bmad-quick-flow/quick-spec/workflow.md` |
| quick-dev | Quick dev | A | `_bmad/bmm/workflows/bmad-quick-flow/quick-dev/workflow.md` |
| generate-project-context | Generate project context | A | `_bmad/bmm/workflows/generate-project-context/workflow.md` |
| bmm-document-project | Document project | B | `_bmad/bmm/workflows/document-project/workflow.yaml` |
| qa-generate-e2e-tests | Generate E2E tests | B | `_bmad/bmm/workflows/qa-generate-e2e-tests/workflow.yaml` |

---

## GDS - Game Design Studio

### Pre-production
| Keyword | Description | Pattern | File |
|---------|-------------|---------|------|
| create-game-brief | Create game brief | A | `_bmad/gds/workflows/1-preproduction/game-brief/workflow.md` |
| brainstorm-game | Brainstorm game | B | `_bmad/gds/workflows/1-preproduction/brainstorm-game/workflow.yaml` |
| game-brief | Game brief (engine) | B | `_bmad/gds/workflows/1-preproduction/game-brief/workflow.yaml` |

### Design
| Keyword | Description | Pattern | File |
|---------|-------------|---------|------|
| create-gdd, gdd | Game design document | A | `_bmad/gds/workflows/2-design/gdd/workflow.md` |
| gds-gdd | GDD (engine) | B | `_bmad/gds/workflows/2-design/gdd/workflow.yaml` |
| narrative | Narrative design | B | `_bmad/gds/workflows/2-design/narrative/workflow.yaml` |

### Technical
| Keyword | Description | Pattern | File |
|---------|-------------|---------|------|
| game-architecture | Game architecture | B | `_bmad/gds/workflows/3-technical/game-architecture/workflow.yaml` |
| gds-generate-project-context | Generate project context | A | `_bmad/gds/workflows/3-technical/generate-project-context/workflow.md` |

### Production
| Keyword | Description | Pattern | File |
|---------|-------------|---------|------|
| gds-code-review | Code review | B | `_bmad/gds/workflows/4-production/code-review/workflow.yaml` |
| gds-create-story | Create story | B | `_bmad/gds/workflows/4-production/create-story/workflow.yaml` |
| gds-dev-story | Dev story | B | `_bmad/gds/workflows/4-production/dev-story/workflow.yaml` |
| gds-correct-course | Correct course | B | `_bmad/gds/workflows/4-production/correct-course/workflow.yaml` |
| gds-sprint-planning | Sprint planning | B | `_bmad/gds/workflows/4-production/sprint-planning/workflow.yaml` |
| gds-sprint-status | Sprint status | B | `_bmad/gds/workflows/4-production/sprint-status/workflow.yaml` |
| gds-retrospective | Retrospective | B | `_bmad/gds/workflows/4-production/retrospective/workflow.yaml` |
| gds-document-project | Document project | B | `_bmad/gds/workflows/document-project/workflow.yaml` |
| gds-quick-spec | Quick spec | A | `_bmad/gds/workflows/gds-quick-flow/quick-spec/workflow.md` |
| gds-quick-dev | Quick dev | A | `_bmad/gds/workflows/gds-quick-flow/quick-dev/workflow.md` |

### Game Testing
| Keyword | Description | Pattern | File |
|---------|-------------|---------|------|
| gametest-automate | Automated test scenarios | B | `_bmad/gds/workflows/gametest/automate/workflow.yaml` |
| gametest-framework | Test framework | B | `_bmad/gds/workflows/gametest/test-framework/workflow.yaml` |
| gametest-performance | Performance testing | B | `_bmad/gds/workflows/gametest/performance/workflow.yaml` |
| gametest-playtest-plan | Playtest plan | B | `_bmad/gds/workflows/gametest/playtest-plan/workflow.yaml` |
| gametest-test-design | Test design | B | `_bmad/gds/workflows/gametest/test-design/workflow.yaml` |
| gametest-test-review | Test review | B | `_bmad/gds/workflows/gametest/test-review/workflow.yaml` |

---

## BMB - BMAD Module Builder

| Keyword | Description | Pattern | File |
|---------|-------------|---------|------|
| bmb-create-agent | Create agent | A | `_bmad/bmb/workflows/agent/workflow-create-agent.md` |
| bmb-edit-agent | Edit agent | A | `_bmad/bmb/workflows/agent/workflow-edit-agent.md` |
| bmb-validate-agent | Validate agent | A | `_bmad/bmb/workflows/agent/workflow-validate-agent.md` |
| bmb-create-module | Create module | A | `_bmad/bmb/workflows/module/workflow-create-module.md` |
| bmb-create-module-brief | Create module brief | A | `_bmad/bmb/workflows/module/workflow-create-module-brief.md` |
| bmb-edit-module | Edit module | A | `_bmad/bmb/workflows/module/workflow-edit-module.md` |
| bmb-validate-module | Validate module | A | `_bmad/bmb/workflows/module/workflow-validate-module.md` |
| bmb-create-workflow | Create workflow | A | `_bmad/bmb/workflows/workflow/workflow-create-workflow.md` |
| bmb-edit-workflow | Edit workflow | A | `_bmad/bmb/workflows/workflow/workflow-edit-workflow.md` |
| bmb-rework-workflow | Rework workflow | A | `_bmad/bmb/workflows/workflow/workflow-rework-workflow.md` |
| bmb-validate-workflow | Validate workflow | A | `_bmad/bmb/workflows/workflow/workflow-validate-workflow.md` |
| bmb-validate-max-parallel | Validate max parallel | A | `_bmad/bmb/workflows/workflow/workflow-validate-max-parallel-workflow.md` |

---

## TEA - Testing Education Academy

| Keyword | Description | Pattern | File |
|---------|-------------|---------|------|
| teach-me-testing | Interactive testing education | A | `_bmad/tea/workflows/testarch/teach-me-testing/workflow.md` |
| testarch-atdd | ATDD workflow | B | `_bmad/tea/workflows/testarch/atdd/workflow.yaml` |
| testarch-automate | Test automation | B | `_bmad/tea/workflows/testarch/automate/workflow.yaml` |
| testarch-ci | CI testing | B | `_bmad/tea/workflows/testarch/ci/workflow.yaml` |
| testarch-framework | Test framework | B | `_bmad/tea/workflows/testarch/framework/workflow.yaml` |
| testarch-nfr | NFR assessment | B | `_bmad/tea/workflows/testarch/nfr-assess/workflow.yaml` |
| testarch-test-design | Test design | B | `_bmad/tea/workflows/testarch/test-design/workflow.yaml` |
| testarch-test-review | Test review | B | `_bmad/tea/workflows/testarch/test-review/workflow.yaml` |
| testarch-trace | Traceability | B | `_bmad/tea/workflows/testarch/trace/workflow.yaml` |

---

## CIS - Creative & Innovation Studio

| Keyword | Description | Pattern | File |
|---------|-------------|---------|------|
| brainstorming | Brainstorming session | A | `_bmad/core/workflows/brainstorming/workflow.md` |
| design-thinking | Design thinking | B | `_bmad/cis/workflows/design-thinking/workflow.yaml` |
| innovation-strategy | Innovation strategy | B | `_bmad/cis/workflows/innovation-strategy/workflow.yaml` |
| problem-solving | Problem solving | B | `_bmad/cis/workflows/problem-solving/workflow.yaml` |
| storytelling | Storytelling | B | `_bmad/cis/workflows/storytelling/workflow.yaml` |

---

## Core Utilities & Reviews

| Keyword | Description | Pattern | File |
|---------|-------------|---------|------|
| help | Get guidance on next steps | A | `_bmad/core/tasks/help.md` |
| party-mode | Multi-agent group discussion | A | `_bmad/core/workflows/party-mode/workflow.md` |
| review-adversarial | Adversarial/cynical review | C | `_bmad/core/tasks/review-adversarial-general.xml` |
| review-edge-case | Edge case hunting | C | `_bmad/core/tasks/review-edge-case-hunter.xml` |
| editorial-prose | Prose review | C | `_bmad/core/tasks/editorial-review-prose.xml` |
| editorial-structure | Structure review | C | `_bmad/core/tasks/editorial-review-structure.xml` |
| index-docs | Index documentation | C | `_bmad/core/tasks/index-docs.xml` |
| shard-doc | Shard large documents | C | `_bmad/core/tasks/shard-doc.xml` |

---

## MCP Tools (Direct Access)

These BMAD MCP tools can be called directly without the routing table:
`bmad_help`, `bmad_list_workflows`, `bmad_list_agents`, `bmad_status`,
`bmad_bmm_create_prd`, `bmad_bmm_create_story`, `bmad_bmm_dev_story`,
`bmad_bmm_code_review`, `bmad_bmm_sprint_planning`,
`bmad_bmb_create_agent`, `bmad_cis_brainstorming`,
`bmad_gds_create_game_brief`, `bmad_gds_game_architecture`,
`bmad_tea_test_design`, `bmad_index_docs`, `bmad_party_mode`
