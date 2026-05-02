# Cohezion - Claude Code Project Guide

## Project Overview

Cohezion is an AI-driven agentic framework built on the BMad Method v6.0.0-alpha.3. It orchestrates AI agents for autonomous software development through three modules:

- **BMM** (BMad Method Module): Core development workflow with 7 agent roles (PM, Analyst, Architect, SM, DEV, TEA, UX)
- **BMB** (BMad Builder Module): Tools for creating and extending BMad components
- **CIS** (Creative Intelligence Suite): AI-powered creative facilitation with 5 specialized agents

## Tech Stack

- **Language**: Python 3.10
- **Formatter**: black (line-length 88)
- **Linter**: ruff (rules: E, F, W)
- **Testing**: pytest
- **Config**: pyproject.toml
- **CI**: GitHub Actions (lint.yml runs black --check and ruff check on PRs)

## Development Commands

```bash
# Format code
black .

# Lint
ruff check .

# Run tests
pytest tests/

# Run tests with coverage
pytest --cov=bmad --cov-report=term-missing tests/
```

## Project Structure

```
bmad/                   # Main framework
  core/                 # Core infrastructure (context_engineering.py, agents, tasks, tools, workflows)
  bmm/                  # Development methodology module (agents, workflows, teams, tasks, testarch)
  bmb/                  # Builder module (agents, workflows)
  cis/                  # Creative Intelligence Suite (agents, workflows, teams)
  _cfg/                 # Manifests (agent, workflow, task, tool, file CSVs)
  schemas/              # Data validation schemas
  scripts/              # Utility scripts (intake_specialist.py, database.py)
tests/                  # Test suite (mirrors bmad/ structure)
docs/                   # Documentation and stories
db/migrations/          # Database migrations
```

## Conventions

- Agent definitions use XML (`.xml`) and Markdown (`.md`) formats
- Manifests in `bmad/_cfg/` are the single source of truth for component registration
- Workflow definitions are in Markdown
- Commit messages follow conventional format: `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`

## Plugin: everything-claude-code

This project uses the [everything-claude-code](https://github.com/affaan-m/everything-claude-code) plugin, providing:

- **Agents**: planner, architect, code-reviewer, python-reviewer, security-reviewer, tdd-guide, and more
- **Skills**: python-patterns, python-testing, backend-patterns, postgres-patterns, security-review, tdd-workflow, continuous-learning
- **Commands**: `/plan`, `/tdd`, `/code-review`, `/python-review`, `/security`, `/build-fix`, `/verify`
- **Rules**: Common and Python-specific rules in `.claude/rules/`

### Key Workflows

1. **Plan First**: Use `/plan` or planner agent for complex features
2. **TDD**: Use `/tdd` for test-driven development (RED -> GREEN -> IMPROVE)
3. **Code Review**: Use `/code-review` or `/python-review` after writing code
4. **Security**: Use security-reviewer agent before commits
5. **Retrospect**: Use `/retrospect` after major milestones to flow learnings into core files

### Session 80 Patterns

- **"As Above, So Below"**: Worktree structure mirrors unified codebase. Archive with git bundles, extract to PRIME skills.
- **Competition Sustainment**: Parallel monitoring during infrastructure work. Document blockers in BLOCKER_REGISTRY.md.
- **Genesis Engine**: Compound executor + 120+ PRIME skills + unified registry. Activate after construction.
- **AMD Optimization**: Triton FP4 KeyError on runner → use ASM path or manual packing.
