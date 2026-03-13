---
task_id: bmad-analysis
title: Analyze BMAD framework, extract patterns, and plan removal from cohezion repo
completed_at: '2026-02-08T12:00:00+00:00'
assigned_to: local-claude-code
date: 2026-02-08
tags: [teleport-result, bmad, framework-analysis, patterns, architecture]
neural:
  activation: 0.76
  stage: growing
  synapse_in: 0
  synapse_out: 7
---
# Result: Analyze BMAD Framework, Extract Patterns, and Plan Removal

## Status: COMPLETED

BMAD was already removed in commit `f4d6996b83a5` (418 files, 78,387 lines). Analysis was performed from git history.

## Deliverable 1: Key Learnings Document

### Patterns Extracted (written to vault)

1. **Scale-Adaptive Documentation** (`patterns/bmad-scale-adaptive-documentation.md`)
   - Levels 0-4 proportional documentation system
   - Keyword-based auto-detection of project scale
   - Greenfield vs brownfield workflow paths
   - **Applicable to cohezion**: Add `level` field to decisions/experiments frontmatter

2. **Agent Persona Definition** (`patterns/bmad-agent-persona-definition.md`)
   - Structured agent definitions: persona + activation + menu + handlers
   - Named agents with distinct communication styles ("Winston" the Architect, "Mary" the Analyst)
   - First-person principles statements for behavioral anchoring
   - **Applicable to cohezion**: Create simplified YAML agent definitions in `.claude/agents/`

3. **Workflow Orchestration** (`patterns/bmad-workflow-orchestration.md`)
   - 4-phase lifecycle: Analysis → Planning → Solutioning → Implementation
   - YAML workflow schema with variable interpolation
   - Gate checks between phases
   - Router pattern for type-specific dispatch
   - **Applicable to cohezion**: Add gate checks to CompoundExecutor

### Antipatterns Identified

1. **File explosion** (418 files) — most were boilerplate YAML with identical config blocks
2. **XML-in-markdown** agent definitions — fragile, unvalidatable
3. **Placeholder code** shipped as features (`intake_specialist.py` was 90% stubs)
4. **YAML as programming language** — workflows needing conditionals should use code
5. **Framework installer** for what should be a pip install
6. **"NEVER break character"** wastes tokens in task-oriented agents

## Deliverable 2: Abstracted Patterns

Three pattern notes written to `~/vaults/cohezion-vault/patterns/bmad-*.md`:
- `bmad-scale-adaptive-documentation.md`
- `bmad-agent-persona-definition.md`
- `bmad-workflow-orchestration.md`

Each includes: Problem → Solution → Application to Cohezion → Effort estimate → When to Use.

## Deliverable 3: Removal Plan (ADR)

Written to `decisions/2026-02-08-bmad-framework-removal.md`.

### Remaining References (post-removal)

| File | BMAD Reference | Recommended Action |
|------|---------------|-------------------|
| `.github/PULL_REQUEST_TEMPLATE.md` | "BMad Method Information" section | Replace with cohezion-native template |
| `.github/ISSUE_TEMPLATE.md` | "BMad Method Context" section | Remove section |
| `research/data/cohezion_dataset.json` | Historical mentions | No action (historical data) |

### Context Engineering Comparison

- **BMAD**: 15-line toy class (`register_tool`, `execute_tool`, `list_tools`)
- **Cohezion**: 229-line MCP-integrated class with `log_decision`, `log_experiment`, `extract_pattern`, `find_relevant_context`
- **Verdict**: Nothing to merge. Cohezion already supersedes BMAD completely.

### Code Worth Preserving: None

All useful BMAD concepts have been captured as vault pattern notes. The code itself (Python scripts, YAML workflows, XML-in-markdown agents) is not portable to cohezion's architecture.

## Related
- [[workflow-orchestration]]
- [[agent-architecture]]
- [[multi-agent-systems]]
- [[2026-02-08-bmad-framework-removal]]
- [[bmad-scale-adaptive-documentation]]
- [[bmad-agent-persona-definition]]
- [[bmad-workflow-orchestration]]
