# Cohezion AI Agent Context

## Project Overview
Cohezion is an agentic AI framework with universe simulation, compound sessions, and semantic caching.

## Key Directories
- `src/cohezion/compound/` - Executor, SessionManager, SkillRefiner
- `src/cohezion/integrations/agentverse/` - AgentVerse integration
- `src/cohezion/swarm/` - Team orchestration, V-Model engineering
- `src/cohezion/cache/` - L1/L2/L3 semantic cache
- `src/cohezion/skills/` - PRIME skill definitions (*.md)
- `tests/` - Test suite (use `make test-fast` for quick feedback)

## Development Workflow
1. Use `make format` before committing
2. Use `make lint` to check style
3. Use `make type-check` for mypy validation
4. Use `make test-fast` for unit tests (<1s each)

## Critical Patterns
- Always mock external services at source level with `@patch("cohezion.module.function")`
- Reset singletons in tests: `cohezion.api._vae_trainer = None`
- All I/O must be async with timeouts
- Use Pydantic validation at API boundaries

## Autoresearch Mode
When in autoresearch mode:
- Check `autoresearch.md` for session objectives
- Review `autoresearch.ideas.md` for deferred optimizations
- Run experiments with `run_experiment` + `log_experiment`
- Metric: "lower" or "higher" direction matters
- Confidence score appears after 3+ runs

## Extensions Available
- `/diag` - System diagnostics
- `/cost` - Session spending analysis  
- `/oracle <question>` - Get second opinion from another model
- `/plan` - Toggle plan mode for safe exploration
- `/mem <instruction>` - Save instruction to AGENTS.md
- `/usage` - Token/cost dashboard
- `/agent <prompt>` - Spawn side agent (parallel work in tmux + worktree)
- `/agents` - List active side agents
