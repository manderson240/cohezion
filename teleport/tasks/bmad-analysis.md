---
id: bmad-analysis
title: Analyze BMAD framework, extract patterns, and plan removal from cohezion repo
status: completed
priority: high
created_at: '2026-02-07T23:00:00+00:00'
updated_at: '2026-02-07T23:00:00+00:00'
assigned_to: cloud-claude-team
expected_output: |
  1. Key learnings document with patterns and antipatterns
  2. Abstracted patterns applicable to cohezion
  3. Removal plan with dependency analysis
date: 2026-02-07
tags: [teleport-task, bmad, framework-analysis, patterns, architecture]
---
# Analyze BMAD Framework, Extract Patterns, and Plan Removal

## Context

The cohezion repo at `/home/mike-anderson/dev/cohezion/` contains a `bmad/` directory
(112 files, ~7 directories) that is the "BMad Method" — an AI-driven agile development
framework for multi-agent orchestration. It was installed as a submodule/dependency but
is now cluttering the repo. The pre-commit hooks touch bmad files on every push (end-of-file
fixes, yaml checks) which adds noise.

BMAD is NOT directly imported by any Python code in cohezion. It's referenced only via:
- `.gemini/commands/` TOML files (IDE command mappings)
- `pyproject.toml` ruff config (`bmad/scripts/**/*.py` ignore, `known-first-party`)
- The current branch name (`feature/repository-management-workflow`) references a bmad workflow

## Description

### Phase 1: Extract Key Learnings (assign to Pattern Analyst)

Analyze these BMAD components and document patterns/antipatterns:

**Patterns to extract:**
1. **Workflow Orchestration** — YAML-based workflow composition with nested task invocation.
   BMAD uses `bmm/workflows/` with 4-phase lifecycle (Analysis → Planning → Solutioning → Implementation).
   How does this compare to cohezion's ExecutionOrchestrator/TeamPlanExecutor?

2. **Scale-Adaptive Documentation** — Level 0-4 auto-scaling (minimal → enterprise).
   Could this concept improve cohezion's template-driven development?

3. **Intent Extraction** — `bmad/scripts/intake_specialist.py` does NL→structured intent
   with keyword overlap validation. Compare to cohezion's InstructionExpander.

4. **Team Composition** — Pre-configured YAML teams (`team-fullstack.yaml`, `team-gamedev.yaml`).
   How does this compare to cohezion's TeamOrchestrator?

5. **Test Architecture (TEA)** — 9 specialized testing workflows, quality matrix, NFR assessment.
   What can cohezion adopt for its test strategy?

6. **Context Engineering** — `bmad/core/context_engineering.py` has a minimal tool registry.
   Compare to cohezion's ContextEngineeringInfrastructure.

7. **Agent Definition Pattern** — Agents defined as markdown files with personality, capabilities,
   and workflow bindings. Compare to cohezion's `.claude/agents/` YAML definitions.

## Related
- [[workflow-orchestration]]
- [[agent-architecture]]
- [[multi-agent-systems]]
- [[2026-02-08-bmad-framework-removal]]

**Antipatterns to identify:**
- Over-engineering: Is BMAD's 112-file structure justified for its scope?
- YAML sprawl: When do declarative workflows become harder to maintain than code?
- Schema vs code validation: BMAD uses JSON-Schema YAML; cohezion uses Pydantic. Which is better?
- Pre-commit hook pollution: bmad files trigger on every commit even when unrelated

### Phase 2: Abstract and Apply (assign to Integration Architect)

For each useful pattern identified:
1. Write a concrete implementation sketch showing how to apply it in cohezion
2. Identify which existing cohezion module it enhances
3. Estimate effort (small/medium/large)

Write results to `~/vaults/cohezion-vault/patterns/bmad-*.md` files.

### Phase 3: Removal Plan (assign to Repository Specialist)

Create a clean removal plan:
1. List all references to bmad in the codebase (pyproject.toml, .gemini/, CLAUDE.md, etc.)
2. Determine if any `.gemini/commands/` should be preserved (rewritten to reference cohezion agents)
3. Determine if `bmad/core/context_engineering.py` has any code worth merging into
   `src/cohezion/core/context_engineering.py` before deletion
4. Plan the git operations: single commit removing bmad/ + updating all references
5. Ensure pre-commit hooks stop touching bmad files after removal

Write the removal plan to `~/vaults/cohezion-vault/decisions/` as an ADR.

## Key Files to Analyze

- `bmad/core/context_engineering.py` — Compare with `src/cohezion/core/context_engineering.py`
- `bmad/scripts/intake_specialist.py` — NL intent extraction
- `bmad/bmm/workflows/repository-management-workflow.yaml` — Currently referenced by branch
- `bmad/bmm/agents/*.md` — Agent definition pattern
- `bmad/bmm/teams/*.yaml` — Team composition pattern
- `bmad/bmm/testarch/` — Testing framework
- `bmad/_cfg/manifest.yaml` — Module configuration pattern
