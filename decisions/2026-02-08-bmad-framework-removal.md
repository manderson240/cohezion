---
title: Remove BMAD Framework from Cohezion Repository
date: '2026-02-08'
status: accepted
tags: [decision, architecture, repository-management, bmad, inferred]
decision_reasoning:
  reasoning_chain:
  - sequence: 1
    content: 'Context: Remove BMAD Framework from Cohezion Repository'
    type: research
    confidence: 0.65
    assumption: Problem was clearly identified
  - sequence: 2
    content: Explored multiple implementation approaches and trade-offs
    type: pattern
    confidence: 0.6
    assumption: Multiple options were considered
  - sequence: 3
    content: Evaluated options against project constraints and criteria
    type: research
    confidence: 0.58
    assumption: Options were systematically evaluated
  reasoning_type: research
  confidence_score: 0.6
---
## Context

The cohezion repository contained a `bmad/` directory (418 files, ~78K lines) implementing the "BMad Method" — an AI-driven agile development framework for multi-agent orchestration. BMAD was installed as a submodule via its own installer (`v6.0.0-alpha.3`, installed 2025-11-01) and included:

- **core/** — Foundation agents (bmad-master, intake-specialist, repository-specialist), a minimal `ContextEngineeringInfrastructure` class (15 lines), and workflow execution engine
- **bmm/** — The main development methodology: 10 agent personas, 34 workflow directories across a 4-phase lifecycle (Analysis → Planning → Solutioning → Implementation), team composition YAML, and a 9-workflow test architecture (TEA)
- **bmb/** — Meta-framework for creating new agents, modules, and workflows
- **cis/** — Creative Innovation Suite (brainstorming, design thinking, storytelling agents)

BMAD was **not imported** by any Python code in cohezion. References existed only in:
- `.github/PULL_REQUEST_TEMPLATE.md` (Scale Level, Story Lifecycle fields)
- `.github/ISSUE_TEMPLATE.md` (BMad Method Context section)
- `research/data/cohezion_dataset.json` (historical data)

Pre-commit hooks were touching BMAD files on every commit (end-of-file fixes, YAML checks), adding noise to unrelated changes.

## Decision

Remove the entire `bmad/` directory from the repository. Before removal, extract the three most valuable patterns into the Cohezion vault as permanent reference notes:

1. **Scale-Adaptive Documentation** (`patterns/bmad-scale-adaptive-documentation.md`) — Levels 0–4 system for proportional documentation
2. **Agent Persona Definition** (`patterns/bmad-agent-persona-definition.md`) — Structured agent definitions with persona, activation, and menu binding
3. **Workflow Orchestration** (`patterns/bmad-workflow-orchestration.md`) — YAML-based 4-phase workflow composition with gate checks

## Consequences

### Positive

- **78K lines removed** — massive reduction in repository noise
- **Pre-commit hooks** stop triggering on bmad files
- **Cognitive load** reduced — no more confusion about which context_engineering.py is authoritative
- **Pattern knowledge preserved** in vault — the useful concepts survive without the implementation overhead
- **Cleaner dependency surface** — no more bmad-related ruff ignores in pyproject.toml

### Negative

- `.gemini/commands/` directory was removed (was empty/unused) — if Gemini IDE integration is needed later, commands must be recreated
- Historical git blame for the removal commit is noisy (450 file deletions)
- The BMAD community is active; if the method evolves significantly, cohezion won't benefit automatically

### Remaining Cleanup

These BMAD references still exist and should be updated:

| File | Reference | Action |
|------|-----------|--------|
| `.github/PULL_REQUEST_TEMPLATE.md` | "BMad Method Information" section with Scale Level and Story Lifecycle | Replace with cohezion-native PR template |
| `.github/ISSUE_TEMPLATE.md` | "BMad Method Context" section | Remove section entirely |
| `research/data/cohezion_dataset.json` | Historical BMAD mentions in dataset | No action needed (historical data) |

## Alternatives Considered

### 1. Keep BMAD as a Git Submodule
**Rejected** — BMAD was already vendored (copied in), not a proper submodule. Converting to a submodule would add git complexity for a framework that wasn't being used.

### 2. Keep Only TEA (Test Architecture)
**Rejected** — The test architecture knowledge base (20 markdown files) contains genuinely good testing guidance, but it's designed for Playwright/Cypress web testing, not cohezion's Python test suite. The test-levels-framework and probability-impact concepts are captured at a higher level in the vault pattern notes.

### 3. Merge context_engineering.py
**Rejected** — BMAD's version was a 15-line toy (register/execute/list tools). Cohezion's version (229 lines) already supersedes it with full MCP integration, compound operations, and vault persistence. Nothing to merge.

### 4. Keep Agent Persona Definitions
**Rejected as files, accepted as pattern** — The XML-in-markdown format is fragile and tied to Gemini's execution model. The *concept* of structured agent personas is preserved in the vault pattern note, but the specific files aren't portable to Claude Code's `.claude/agents/` format.

## Removal Details

- **Commit**: `f4d6996b83a5` ("feat: Register Cloud Vault MCP server with Claude Code")
- **Files removed**: 450 (including docs/stories/*.yml)
- **Lines deleted**: 78,387
- **Branch**: `feature/repository-management-workflow`

## Key Learnings

### Patterns Worth Abstracting
1. **Scale-adaptive documentation** is a universally useful concept — classify project size before choosing process weight
2. **Named agent personas with principles** produce more consistent behavior than role-only descriptions
3. **Gate checks between workflow phases** prevent premature implementation
4. **Knowledge fragments** (TEA's 20 testing knowledge files) are an effective way to give agents domain expertise without bloating the base prompt

### Antipatterns Identified
1. **418 files for a process framework** is over-engineered — most were boilerplate YAML with identical config blocks
2. **XML embedded in markdown** is the worst of both worlds — fragile prompts that can't be validated by either XML or markdown tools
3. **Placeholder code shipped as features** — `intake_specialist.py` was 90% stubs with `# Placeholder for call to language model` comments
4. **YAML as a programming language** — when workflows need conditionals and loops, use actual code
5. **Framework-level installer** (`manifest.yaml`, `install-config.yaml`) for what should be a `pip install` or a git clone
6. **"NEVER break character"** instructions waste tokens and don't improve task-oriented agent behavior

## Related

- [[compound-engineering]] — cohezion's native approach replaces BMAD's workflow lifecycle
- [[bmad-scale-adaptive-documentation]]
- [[bmad-agent-persona-definition]]
- [[bmad-workflow-orchestration]]

## Related Lessons

- [[lesson-01-agent-has-great-content-but-claude-code-only-auto-reads]] (operational validation)

- [[lesson-11-team-agent-efficiency]] (operational validation)

## Related Concepts

- [[3d-graph-plugin-selection]]
- [[2026-02-09-ollama-context-management]]
- [[2026-02-12-claude-code-context-awareness-codification]]
- [[2026-02-12-charter-aligned-scoring-formula]]
- [[2026-02-13-local-model-roster-update-february-2026-sota-assessment]]
- [[2026-02-17-phase-2-full-verification-plan]]
- [[2026-02-13-gitlab-to-github-consolidation-with-artifact-governance]]
- [[2026-02-14-adversarial-multi-agent-review-protocol]]
