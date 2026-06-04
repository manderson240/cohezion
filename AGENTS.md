# Cohezion AI Agent Context

## Project Overview
Cohezion is an agentic AI framework with universe simulation, compound sessions, and semantic caching.

## Key Directories
- `src/cohezion/compound/` - Executor, SessionManager, SkillRefiner
- `src/cohezion/integrations/agentverse/` - AgentVerse integration
- `src/cohezion/swarm/` - Team orchestration, V-Model engineering
- `src/cohezion/cache/` - L1/L2/L3 semantic cache
- `src/cohezion/skills/` - PRIME skill definitions (*.md)
- `src/cohezion/researcher/` - Daily researcher (4 lanes, WS1+WS2)
- `scripts/lanes/` - The four lane scripts (WS2B)
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

## Local Inference Discipline ("Quarter on the String")

Local inference on Strix Halo is memory-tight (122 GiB unified, 39 GiB swap).
A concurrent-load race on the iGPU aperture can fault the kernel and
require a cold-boot recovery. The rules below prevent that.

1. **Before launching any local inference swarm** (cohezion swarm,
   Eigent, GAIA agent, ollama batch, daily researcher), run
   `bash scripts/preflight_fleet.sh`. Exit non-zero = do not start.
2. **All model loads** must acquire `fleet_lock:modelload` via
   `cohezion.researcher.daily_researcher.FleetLock` (or the
   `scripts/fleet_lock.py` helper) before calling `lemonade load`,
   `extend_claude`, `extend_claude_aligned`, `gaia llm`, or
   `ollama pull`. Two concurrent loads = aperture race = potential
   kernel fault.
3. **Queue, don't block**: a second swarm waits for the first to
   release the lock. Never spawn parallel loaders.
4. **Recovery**: if the box is in zombie state (preflight fails on
   dmesg fault or VRAM-without-PID), run `bash scripts/recover_fleet.sh`
   (soft path). If it prints `cold boot required`, do that — do not
   retry loads. Soft path runs unattended; hard path (cold boot) is
   human-only, never automated.
5. **Daily researcher cron**: `crontab.example` is the schedule. The
   03:50 dry-run catches a broken cron entry before 04:00; the 04:00
   run is the real one. The 6-hourly preflight log catches zombie
   state before the next swarm.

## Card-Aligned Recipes

No model is ever called with default params. A default param set is a
bug, not a fallback.

- Build params via `ModelCardHarness.aligned_params(model_id, task)`,
  or `ModelCardHarness.profile_for(model_id)` to inspect the card.
- `RecipeGuard.assert_aligned(params)` is a runtime check that fails
  closed if a default `InferenceParams` is passed to `extend_claude_aligned`.
- `RecipeGuard.check_file_for_default_params(path)` is the AST-based
  lint that flags `extend_claude(` calls without `params=`. Run via
  `ruff` / the ratchet in CI.
- Card-aware dispatch goes through `route_by_capability(task, ...)`
  which returns a `(ModelEntry, InferenceParams)` pair where the
  params carry the card's `sampling_sweet_spot` and the
  `required_modes` filter rejects candidates whose `supported_modes`
  don't include the requested capabilities.
- Cardless `ModelEntry` records (profile=None) cannot be dispatched;
  this is the fail-closed `assert_card_present` rule.

## Extensions Available
- `/diag` - System diagnostics
- `/cost` - Session spending analysis  
- `/oracle <question>` - Get second opinion from another model
- `/plan` - Toggle plan mode for safe exploration
- `/mem <instruction>` - Save instruction to AGENTS.md
- `/usage` - Token/cost dashboard
- `/agent <prompt>` - Spawn side agent (parallel work in tmux + worktree)
- `/agents` - List active side agents

