# Cohezion AI Agent Context

> **Mandate**: Antigravity is the **Master Orchestrator & Evaluator**. You direct local silicon hardware (NPU, iGPU, CPU) and cloud model swarms, evaluate all execution trajectories using AutoHarness zero-cost bytecode verifiers and ZKFV polynomial proofs, and drive continuous recursive self-improvement ("Cohezion improving Cohezion").
> **Core Principle**: **QUALITY OVER SPEED ("Leave plenty of time for the fat to render")**. Prioritize deep reasoning, unhurried multi-pass verification, complete solution synthesis, and zero code truncation over rapid responses. Allow local thinking models all the time they need to cook and render edge-case entropy cleanly.

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

## Core AGI Mandates (2026-08-03)
1. **AutoHarness (arXiv:2603.03329v1)**: Mandate `AutoHarness` deterministic code-as-action verifiers and bytecode compilers to bypass LLM calls at inference time with 0 ms latency (`src/cohezion/agi/autoharness_policy.py`).
2. **AutoContext**: Maintain continuous 2048D Poincaré state tracking and dynamic conformal factor resolution for context injection (`src/cohezion/physics/poincare_manifold.py`).
3. **Bleeding Edge Research**: Implement continuous topological auto-calibration (CTAC), zero-knowledge formal verification (ZKFV), and continuous geodesic flow Neural ODEs (`src/cohezion/physics/ctac_engine.py`, `src/cohezion/agi/zkfv_compiler.py`).
4. **Recursive Learning**: Every agent swarm cycle extracts retrospectives into SurrealDB (`learning` table) and Obsidian Vault (`01-Learnings/`) to continuously refine system code and policies ("Cohezion improving Cohezion") (`src/cohezion/agi/recursive_learning.py`).
5. **EventBus & Agentic Kanban Bridge**: All agent swarms and GAIA SDK tasks MUST leverage the `EventBus` (`src/cohezion/core/event_bus.py`) and `CrossSessionEventBridge` (`src/cohezion/core/cross_session_event_bridge.py`) for inter-session collaboration, and record durable task cards via `kanban_bridge.persist_item()` into SurrealDB `kanban_item` and Obsidian Vault `kanban/` simultaneously (`src/cohezion/data_mesh/kanban_bridge.py`).
6. **Proactive Hybrid Delegation**: Proactively offload routine research, code generation, and background diagnostics to Tier 1 local silicon (`deepseek-r1-0528-8b-FLM`, `qwen3.6-moe-35b-a3b-FLM`, `Qwen3-Coder-30B`) and Tier 2 Ollama Cloud models (`deepseek-v4-pro:cloud`, `glm-5.2:cloud`, `qwen3.5:397b-cloud`) via `UnifiedHybridRouter` and subagents (`invoke_subagent`). Maintain Expected Value of Intervention threshold ($\text{EVI} > 0.75$) to trigger autonomous background self-healing (`src/cohezion/inference/unified_hybrid_router.py`, `src/cohezion/proactive/`).
7. **Local Model Next-Step Consultation Mandate**: Whenever wondering what next step to take, encountering branching choices, or navigating ambiguous execution paths, Antigravity MUST proactively consult a local silicon model (Tier 1 Lemonade port `13305` or Ollama port `11434`, e.g., `deepseek-r1-0528-8b-FLM`, `Qwen3-Coder-30B`) to reason through candidate directions, evaluate trade-offs, and recommend the optimal high-leverage action before proceeding.
8. **Kaggle Active Competition Reporting Filter**: Never report on expired or closed competitions. Strictly filter all leaderboard audits, submission tracking, and status reports to currently ACTIVE, unexpired competitions (e.g. ARC Prize 2026 tracks, Pokémon TCG AI Challenge).

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

## Automated CI/CD Pipeline

### AutoMerge Guard (`scripts/ci/automerge_guard.sh <PR_NUMBER>`)
Runs all CI gates locally (format, lint ratchet, unit tests, import smoke,
inference tests, version governance), then merges the PR via `gh pr merge --squash`
if all pass. Logs to SurrealDB `automerge_log`. Use instead of manual `--admin` merges.

### Local Code Review (`scripts/ci/local_review.sh <PR_NUMBER>`)
Pre-warms a review model (Qwen3-Coder-30B) on Lemonade, chunks the PR diff,
and sends each chunk to the local model for adversarial review. Also runs
static import analysis. Writes report to `/tmp/opencode/reviews/`. Logs to
SurrealDB `review_log`.

### Pre-warm Model (`scripts/prewarm_review_model.sh [model] [ctx_size]`)
Acquires `fleet_lock:modelload`, loads a model via Lemonade OmniRouter, waits
for it to appear in `/v1/models`, releases lock. Run before any local inference
session to prevent LRU eviction.

### Import Smoke Test (`tests/unit/test_import_smoke.py`)
Parametrized test that imports every changed Python source file. Only fails
on `SyntaxError` (real merge bug). Skips `ImportError`, `SystemExit`, and
other runtime errors (optional deps, env vars). Catches the class of bugs
that the consolidation campaign introduced (duplicate `__init__`, missing
functions, broken re-exports).

### Bleeding-Edge Policy
- `pyproject.toml` uses `requires-python = ">=3.13"` (newest stable, no-GIL ready)
- All CI workflows use `python-version: "3.13"`
- Dependencies should always use the newest compatible versions
- `uv lock` should be regenerated when upgrading

### PR Landing Workflow (for agents)

When you have a PR ready to merge, follow this sequence:

1. **Pre-warm the review model** (prevents LRU eviction):
   ```bash
   bash scripts/prewarm_review_model.sh
   ```

2. **Run local code review** (adversarial review via local inference):
   ```bash
   bash scripts/ci/local_review.sh <PR_NUMBER>
   ```
   Read the report at `/tmp/opencode/reviews/pr_<PR_NUMBER>_review.md`.
   Fix any findings before proceeding.

3. **Run automerge guard** (all CI gates locally, then merge if green):
   ```bash
   bash scripts/ci/automerge_guard.sh <PR_NUMBER>
   ```
   Gates: ruff format, ruff ratchet, unit tests, import smoke, inference tests,
   version governance. Lint check and inference tests are advisory (the ratchet
   is the real lint gate; live inference tests skip without Lemonade).
   The guard logs to SurrealDB `automerge_log` on both success and failure.

4. **If automerge fails**: fix the failing gate, push the fix, re-run the guard.
   Do NOT use `gh pr merge --admin` to bypass — that's what caused the
   consolidation campaign's CI debt. The guard exists to enforce quality.

### Consolidation Campaign Lessons (2026-07-09)

The first major consolidation merged 289 commits / 15 branches via 17 PRs.
Key lessons captured in vault retrospective
(`~/vaults/cohezion-vault/retros/2026-07-10-consolidation-final.md`) and
SurrealDB (`experiment_run:consolidation_20260709`):

- **Squash merge drops functions**: `extend_claude_aligned` and `build_gaia_mcp_tier`
  were lost during squash merges. Always verify key functions survive.
- **Blanket xfail hides real test results**: marking entire files xfail
  silenced both failing AND passing tests (79 xpassed noise). Mark individual tests.
- **Import smoke test catches merge bugs**: 5 of 11 consolidation bugs were
  import-breaking (missing functions, SyntaxError, broken re-exports). The
  smoke test would have caught them immediately.
- **Pre-warm models before local inference**: Qwen3-Coder-30B was evicted by
  LRU during the code review, forcing a fallback to Bonsai-8B which produced
  only false positives. Always pre-warm.
- **Branch hygiene**: 372 branches → 2 after cleanup. 83 archive tags preserve
  recovery points. 93 worktrees → 1. 36 stashes → 0.

## Extended Availability (Added 2026-07-29)

Agents MUST leverage local inference infrastructure to extend availability
beyond premium API models (Gemini, Claude). Use these in priority order:

1. **Lemonade OmniRouter** (port `13305`): Primary local inference gateway.
   Routes to NPU/iGPU/CPU lanes automatically. Use for code gen, summaries,
   and routine reasoning before escalating to cloud.
2. **GAIA SDK Agents & TMUX Swarms**: Use `gaia llm` and GAIA agent framework
   for multi-step autonomous tasks locally. GAIA agent swarms can be controlled
   and monitored via TMUX sessions (`tmux new-session -s gaia-swarm`).

3. **Ollama Cloud Models**: Use Ollama-hosted models for overflow when
   Lemonade lanes are saturated or for models not loaded locally.

Respect fleet lock discipline (§ Local Inference Discipline above) when
loading models through any of these backends.

## Persistent Memory Storage (Added 2026-07-29)

All agent memory, recall, and session state MUST use these two backends:

| Backend | Location | Use For |
|---------|----------|---------|
| **Cohezion Obsidian Vault** | `~/vaults/cohezion-vault/` | Structured knowledge: retros, decisions, research notes, learnings |
| **SurrealDB** | `http://localhost:8001` | Structured data: experiment logs, metrics, session state, audit trails |

- Write retrospectives and design decisions to the vault as markdown.
- Write experiment results, metrics, and structured logs to SurrealDB.
- Both stores are the system of record — do not rely on ephemeral
  conversation context for recall across sessions.

## Preexisting Condition Logging (Added 2026-07-29)

When agents discover **preexisting conditions** during audits, exploration,
or implementation (tech debt, broken tests, stale modules, naming conflicts,
OOM risks, deprecated patterns), they MUST log them durably — not just
mention them in conversation.

Use these two channels:

1. **Event Bus** (`cohezion.core.event_bus`): Publish a typed event so
   monitoring/healing systems can react in real time.
   ```python
   from cohezion.core.event_bus import Event, EventBus
   bus = EventBus()
   await bus.publish(Event.agent_complete(
       agent="audit-init-modules",
       result={"finding": "api/__init__.py has 1594 LOC inline logic",
               "severity": "critical", "category": "tech_debt"},
   ))
   ```

2. **Agentic Kanban** (`cohezion.data_mesh.kanban_bridge`): Create a
   kanban item that persists to both SurrealDB and the Obsidian vault.
   ```python
   from cohezion.data_mesh.kanban_bridge import persist_item
   persist_item({
       "id": "init-audit-api-bloat",
       "title": "api/__init__.py contains 1594 LOC of inline logic",
       "status": "backlog",
       "priority": "high",
       "source": "audit/init-modules",
       "category": "tech_debt",
   })
   ```

This ensures findings survive session crashes (including OOM) and are
visible to future agents, the Obsidian vault, and SurrealDB dashboards.

## Proactive Delegation Policy (Added 2026-08-03)

> **Core Mandate**: *Local inference first. Ollama cloud second. Premium APIs only when local/cloud cannot satisfy the task.*

Every agent MUST evaluate this three-tier decision tree **before** sending any inference request:

### Tier 1 — Lemonade OmniRouter (NPU/iGPU/CPU, port 13305)

Preferred for all routine inference. Select lane by task class:

| Task Class | Model | Lane | Port | Ctx |
|------------|-------|------|------|-----|
| Reasoning / planning | `deepseek-r1-0528-8b-FLM` | NPU | 13305 | 40 960 |
| Coding / multi-file refactor | `Qwen3-Coder-30B` (GGUF/Vulkan) | iGPU | 13305 | 32 768 |
| Coding + tools (small) | `qwen3-4b-FLM` | NPU | 13305 | 32 768 |
| Vision / UI / diagram | `qwen3vl-it-4b-FLM` | NPU | 13305 | 16 384 |
| Research summary | `qwen3.6-moe-35b-a3b-FLM` *(pinned)* | NPU | 13305 | 16 384 |
| Fast Q&A / retrieval | `llama3.2-1b-FLM` *(pre-warmed)* | NPU | 13305 | 4 096 |
| Embeddings | `embed-gemma-300m-FLM` | NPU | 13305 | 8 192 |

**Fleet-lock discipline MUST be respected**: only one model load active at a time.
Use `FleetLock("modelload")` before any `lemonade load` call.

### Tier 2 — Ollama Cloud Models

Use when:
- Required task context > available NPU/iGPU context window, OR
- Tier 1 is saturated (preflight reports VRAM > 90%), OR
- Task requires a capability not in the local roster (e.g., 397B-scale reasoning).

| Task Class | Model |
|------------|-------|
| Deep reasoning / math | `deepseek-v4-pro:cloud` |
| Advanced coding | `qwen3.5:397b-cloud` |
| Science / frontier research | `glm-5.2:cloud` |
| General overflow | `deepseek-v4-pro:cloud` |

Route via `UnifiedHybridRouter` using `backend="ollama_cloud"` parameter.

### Tier 3 — Premium APIs & Thinking Models (agy 1.1.21 Spec)

| Tier 3 Model | Effort / Mode | Best For |
|---|---|---|
| `gemini-3.7-flash-high` | High (Thinking) | Complex orchestration, fast reasoning, multi-turn architecture |
| `gemini-3.7-flash-medium` | Medium | Iterative development, fast agentic loop synthesis |
| `gemini-3.1-pro-high` | High | Deepest multi-modal reasoning & mathematical proofs |
| `claude-sonnet-4-6` | High (Thinking) | Large-scale multi-file refactoring & code generation |
| `claude-opus-4-6-thinking` | Deep (Thinking) | Frontier systems engineering & formal verification |
| `gpt-oss-120b-medium` | Medium | Transparent open-weight benchmark validation |

**Reserved exclusively for**:
- Architecture decisions requiring synthesis across >100K token context
- Final quality gate review of Tier-1/2 outputs
- User-interactive sessions requiring low latency and premium reasoning

Do NOT use Tier-3 for: routine refactors, test generation, or any task where a Tier-1 model scores ≥ 0.7
on the AutoHarness verifier.

### EVI Gating Rule

Before escalating from Tier 1 → Tier 2 → Tier 3, compute:

```
EVI = (quality_gap × task_importance) / escalation_cost
```

Escalate only when `EVI > 0.75`. Log the EVI score and escalation reason to
SurrealDB `delegation_log` table for every escalation event.

### Subagent Default Model Selection

When invoking subagents via `invoke_subagent`:
- **Research / read-only**: `Model: "flash"` (delegates to fast Gemini flash, local when available)
- **Code implementation**: `Model: "inherit"` + Lemonade Tier-1 call inside the subagent
- **Architecture / deep reasoning**: `Model: "pro"` only after Tier-1/2 attempt fails quality gate
- **Quick edits**: `Model: "flash_lite"`

## AMD Official AI Agent Skills Catalog (Added 2026-08-04)

The repository [`https://github.com/amd/skills`](https://github.com/amd/skills) is integrated into `src/cohezion/skills/amd/skills-repo/`.

Use these native AMD skills for hardware-optimized workflows on Strix Halo NPU, Radeon iGPU, and Ryzen/EPYC CPUs:

| AMD Skill | Location | Purpose |
|-----------|----------|---------|
| `local-ai-use` | `src/cohezion/skills/amd/skills-repo/skills/local-ai-use/` | Routes image generation (SD-Turbo), TTS (Kokoro), and STT (Whisper) locally through Lemonade Server to eliminate cloud token costs. |
| `local-ai-app-integration` | `src/cohezion/skills/amd/skills-repo/skills/local-ai-app-integration/` | Bundles Embeddable Lemonade (`lemond`) for private, offline app inference. |
| `serving-llms-on-epyc` | `src/cohezion/skills/amd/skills-repo/skills/serving-llms-on-epyc/` | Serves LLMs on AMD CPUs with vLLM + Zentorch. |
| `serving-llms-on-instinct` | `src/cohezion/skills/amd/skills-repo/skills/serving-llms-on-instinct/` | End-to-end LLM serving on AMD Instinct GPUs via ROCm + vLLM / SGLang. |
| `magpie-kernel-evaluator` | `src/cohezion/skills/amd/skills-repo/skills/magpie-kernel-evaluator/` | Evaluates GPU kernel correctness and performance benchmarking. |
| `tracelens-analysis-orchestrator` | `src/cohezion/skills/amd/skills-repo/skills/tracelens-analysis-orchestrator/` | Orchestrates modular PyTorch profiler trace analysis with TraceLens. |
