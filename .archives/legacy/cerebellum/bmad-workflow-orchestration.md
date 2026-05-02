---
title: "Workflow Orchestration Pattern (from BMAD)"
date: "2026-02-08"
tags: [pattern, workflow, orchestration, extracted-from-bmad]
aspect: thinker
neural:
  activation: 0.75
  stage: mature
  synapse_in: 8
  synapse_out: 12
---

## Problem

Complex development processes (analysis → planning → architecture → implementation) involve many steps, each with different agents, templates, checklists, and output formats. Without a structured orchestration layer, agents improvise and skip steps.

## Solution

BMAD implemented a **4-phase workflow lifecycle** with YAML-defined workflows:

### Phase Structure

```
Phase 1: Analysis     → brainstorming, product brief, research
Phase 2: Planning     → PRD, tech spec, UX design, game design
Phase 3: Solutioning  → architecture, solutioning gate check
Phase 4: Implementation → stories, dev, code review, sprint planning, retrospective
```

### Workflow YAML Schema

Each workflow is a YAML file with standardized fields:

```yaml
name: research
description: "Adaptive research workflow"
config_source: "{project-root}/bmad/bmm/config.yaml"
output_folder: "{config_source}:output_folder"

installed_path: "{project-root}/bmad/bmm/workflows/1-analysis/research"
instructions: "{installed_path}/instructions-router.md"
validation: "{installed_path}/checklist.md"

# Router pattern: type-specific instruction variants
instructions_market: "{installed_path}/instructions-market.md"
instructions_technical: "{installed_path}/instructions-technical.md"

default_output_file: "{output_folder}/research-{{type}}-{{date}}.md"
standalone: true
```

### Key Design Elements

1. **Variable interpolation**: `{project-root}`, `{config_source}:field_name`, `{{date}}`
2. **Separation of concerns**: workflow.yaml defines *what*; instructions.md defines *how*; checklist.md defines *done*
3. **Router pattern**: A single workflow entry point dispatches to type-specific instructions
4. **Validation at each step**: Checklists are loaded and verified before proceeding
5. **Gate checks**: Phase transitions require explicit gate validation (e.g., solutioning-gate-check before implementation)

### Workflow Engine

A central `workflow.xml` file acts as the execution engine:
1. Load the workflow YAML
2. Resolve all variable references
3. Load instructions and checklist
4. Execute steps, saving output after each
5. Run validation checklist before marking complete

## Application to Cohezion

Cohezion's `CompoundExecutor` already implements a simpler version of this:

```
1. get_experience_guidance() — query vault (analogous to Phase 1)
2. execute_task() — run with logging (analogous to Phase 4)
3. extract_patterns() — save reusable insights (post-Phase 4)
```

**Worth adopting:**
- **Gate checks between phases** — `CompoundExecutor.execute_task()` could verify prerequisites (e.g., "has an ADR been logged for this?") before execution
- **Checklist validation** — structured completion criteria rather than just success/failure booleans
- **The router pattern** — dispatch to different execution strategies based on task type

**NOT worth adopting:**
- The 4-phase lifecycle itself — too heavyweight for cohezion's compound engineering model
- Variable interpolation engine — unnecessary when Python code handles configuration
- Separate instructions/checklist/template files per workflow — creates the 418-file problem

**Effort**: Medium — gate check concept can be added to `CompoundExecutor`; checklist validation is a new primitive.

## Antipatterns Observed

- **File explosion**: 34 workflow directories × (workflow.yaml + instructions.md + checklist.md + template.md) = 100+ files for workflow definitions alone
- **Path indirection**: 3+ levels of variable resolution (`{config_source}:output_folder` → read config → resolve path) makes debugging difficult
- **YAML as code**: When workflows need conditionals and loops, YAML becomes harder to maintain than Python
- **Duplicate boilerplate**: Every workflow.yaml repeats the same `config_source`, `output_folder`, `user_name` block

## Origin

Extracted from BMAD `bmm/workflows/` (34 workflow directories across 4 phases + testarch + document-project + workflow-status). The testarch module alone had 9 specialized testing workflows.

## Related

- [[bmad-agent-persona-definition]] — agents are the executors of workflows
- [[bmad-scale-adaptive-documentation]] — project level determines which workflows activate
- [[agent-loop-architecture]] — cohezion's loop is a simpler equivalent

## Decisions & Experiments
- 📋 [[2026-02-08-bmad-framework-removal]] - 2026-02-08-bmad-framework-removal

## Related Concepts

- [[dna-origami-2d-semiconductor-patterning]]
- [[entire-io-to-vault-mapping]]
- [[automated-concept-extraction]]
- [[sheetsbr idge-mcp-testing]]
- [[phase1-production-validation-runbook]]
- [[typescript-error-diagnostic]]
- [[surrealdb-query-driven-analysis]]
- [[agent-logs-vault-schema]]
