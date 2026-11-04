# Cohezion architecture

A short map of what runs, where it lives, and how the pieces connect. Written 2026-11-04
from the code, not from plans; where the code has two ways of doing one thing, this page
says so. The previous overview (March 2026) is archived at
[`archive/architecture_2026-03.md`](archive/architecture_2026-03.md).

## The shape of the system

```
 You / a coding agent
        │  task
        ▼
 CompoundExecutor ──► guardrails ──► execute_fn ──► routing ──► local model fleet (:13305)
  (compound/executor.py)  (security/)               │            NPU → iGPU → CPU, cloud last
        │                                            └─► sandbox for any model-written code
        ▼
 Retrospection ──► SkillRefiner ──► versioned skill files ──► next run
        │
        ▼
 SurrealDB + Obsidian vault (journeys, metrics, learnings)

 MCP servers expose the same capabilities to agents as tools.
 CI gates and a landing guard decide what reaches main.
```

## 1. How code gets in: agents, review and gates

| Piece | Where | What it does |
|---|---|---|
| Agent contract | `CLAUDE.md`, `AGENTS.md`, `.claude/rules/` | Standing rules every agent inherits. Incidents become rules here. |
| Specialist agents | `.claude/agents/` (21) | Reviewer, test runner, MCP specialist and so on, each with a narrow tool list. |
| CI | `.github/workflows/` (27 workflows) | `ci.yml` runs lint, unit tests, validation and the custom scanners on every PR into `main`. |
| Agent review | `claude-code-review.yml`, `gemini-review.yml` | An independent model reviews each PR; the author agent never signs off on its own work. |
| Custom scanners | `scripts/ci/` | Dormant code, phantom attributes, unfalsifiable tests, unsandboxed exec, doc drift. Most have `--self-test`. |
| Landing guard | `scripts/ci/automerge_guard.sh` | Re-runs the gates on the PR merged onto the current tip of `main`, then lands it. |
| Repo hygiene | `src/cohezion/governance/scripts/root_health_guard.py` | Root allowlist, no stray empty files, no case-only path collisions. |

## 2. Routing and the local inference fleet

All local models are served by one Lemonade router on port `:13305` (NPU, iGPU and CPU on one
AMD Strix Halo machine). Cloud models are used only when a local quality gate fails.

| Step | Where | Notes |
|---|---|---|
| Classify the task | `inference/task_classifier.py` `classify()` | Zero model calls. Returns a tier and an output type, e.g. `NPU(short_categorical)`, `GPU(code)`. |
| Run the cascade | `inference/orchestrator.py` `TieredOrchestrator`, built by `inference/triune_orchestrator.py` | Cheapest tier first; escalates one tier when the output fails its quality gate. |
| Learn the entry tier | `compound/difficulty_estimator.py` | Per-skill history; picks the cheapest tier whose Wilson lower bound on clean successes clears 0.35. |
| Admit model loads | `inference/hotswap.py`, `inference/residency_service.py` | Prices weights plus KV cache against free RAM before loading, so the fleet cannot OOM the box. |

**Known duplication.** There is a second routing stack, `inference/unified_hybrid_router.py`
(`UnifiedHybridRouter`, 15 task classes with EVI gating), used by the core orchestrator and
many scripts, plus older routers under `swarm/`. The compound executor path above is the one
the CI invariants cover. Converging on one stack is open work.

## 3. Running model-written code

| Piece | Where | Notes |
|---|---|---|
| Out-of-process sandbox | `compound/sandboxed_exec.py` `run_untrusted()` | Used by the five places that execute generated code. `bwrap --unshare-all` when installed, otherwise kernel rlimits (CPU, memory, files, processes). Results are treated as untrusted. |
| In-process gate | `compound/safe_exec.py` | Import allowlist; defense in depth behind the sandbox. |
| Docker sandbox | `sandboxing/executor.py` `DockerSandbox` | Read-only root, no network, dropped capabilities, killed by name on timeout. Not yet called from production code. |
| CI enforcement | `scripts/ci/unrestricted_exec_scan.py` | Fails the build if generated code is executed outside these paths. |

## 4. The compound loop

`CompoundExecutor.execute_task` (`compound/executor.py`) wraps every task: input guardrails
(`security/guardrail_pipeline.py`), a pre-execution JEPA coherence check, tier selection,
execution, output quality checks, then metrics to `DegradationDetector` and the journey
tracker. Afterwards `core/compound/retrospection.py` extracts learnings and
`compound/skill_refiner.py` proposes a new version of the skill, blocked by a regression gate
when golden fixtures exist. Skills are markdown files in `src/cohezion/skills/` (about 230).

## 5. MCP servers

About 30 MCP server modules under `src/cohezion/mcp/` plus `cloud-vault-mcp/`. They share
`mcp/shared/` (auth middleware, sessions, logging, a common `run_server`); 13 servers use the
shared API-key middleware today.

## 6. Storage

SurrealDB holds journeys, metrics, cache rows and automerge logs; writes go through checked
statements (`checked_statements`, being rolled out to the remaining raw writers) so a SurrealDB
error returned as HTTP 200 is not mistaken for success. The Obsidian
vault (`~/vaults/cohezion-vault/`) holds human-readable decisions and learnings. Large binaries
are Git LFS.

## 7. Research, kept separate

Physics-inspired and exploratory work (`physics/`, `environments/`, `worldviews/`,
`research/`) is not on the request path above. Read it as research, not as platform.

## Try it

```bash
uv sync
uv run python examples/quickstart.py   # routing, scanner self-tests, sandbox; offline, ~5 s
```
