# Cohezion - Claude Code Orchestration

COHEZION is a systemic AI orchestration ecosystem governed by **Quadrature Nexus Orchestration** and **Hermetic Compound Engineering** ("As Above, So Below"). We implement **FLUME** (Fluid Latent Understanding through Manifold Encoding) combined with **JEPA-aligned World Models** for high-fidelity 12D universe simulation, autonomous research, and value precipitation via **UCP/MCP**.

## Constitutional Framework

All actions are governed by two documents (read them for ethical/behavioral ambiguity):
- **Core Constitution**: `.agent/CONSTITUTION.md` - January 2026 Claude Edition. Defines principal hierarchy (Anthropic > Operators > Users), hard constraints, and the 0.5 Coherence Rule.
- **Project Charter**: `.agent/COHEZION_CHARTER.md` - SPIN theory, FLUME evolution, Expert Domain Lattice, Observable AI, Deterministic Responsibility.

### Hard Constraints (Never Violate)
- No WMD uplift, no critical infrastructure attacks, no malicious code, no undermining human oversight
- All agentic actions must be **idempotent** (preserve 0.5 coherence baseline)
- **Honesty is non-negotiable**: Assert only what is believed true, with appropriate uncertainty

## Quick Reference

- **Language**: Python 3.13+ | **Package Manager**: `uv` (always use `uv run`)
- **Formatter**: `ruff format` (88-char line length) | **Linter**: `ruff check`
- **Type Checker**: `mypy` | **Tests**: `uv run pytest`
- **Database**: SurrealDB (ws://localhost:8000/rpc, ns=cohezion, db=core)
- **Source Layout**: `src/cohezion/` (212 Python files across 30+ packages, 124 skill definitions in `src/cohezion/skills/`)
- **Tests**: 634 passing, 2 skipped (`uv run pytest tests/ -q --ignore=tests/test_resource_adversarial.py`)
- **Entry Point**: `cohezion = "cohezion.__main__:main"`
- **Local Dev Server**: `uv run uvicorn cohezion.api:app --reload --port 8080`

## Repository Layout

```
src/cohezion/          # Core framework
  agents/              # Agent implementations
  swarm/               # Multi-agent orchestration (Quadrature Nexus)
  skills/              # 124 PRIME skill definitions (markdown + python)
  universe/            # 12D simulation engine (3 Spatial + 1 Time + 8 Brane)
  flume/               # FLUME manifold encoding (256D latent space)
  physics/             # QGP, magnetohydrodynamics simulation
  mcp/                 # Model Context Protocol integration
  persistence/         # SurrealDB persistence layer
  healing/             # Autonomic self-healing (immune_system, platform_audit)
  validation/          # Great Expectations + schema validation
  knowledge_graph/     # Persistent memory: MISSION_JOURNAL.md, KEY_LEARNINGS.md
  reliability/         # Circuit breakers (get_circuit())
  compound/            # Compound engineering (executor, feedback loop, metrics, persistence)
  mass_sim/            # Mass simulation engine (batch runner, exporter, persistence)
  rl/                  # Reinforcement learning (Gymnasium FlumeNav-v0, REINFORCE trainer)
  pipeline/            # Data pipeline (mass sim → .npy → training)
  api/                 # FastAPI backend (46 endpoints: compound, FLUME, RL, metrics, skills)
apps/                  # Web applications
  webapp/              # Main frontend (Vite/React/WebGL/WASM)
.agent/                # Agent charter, constitution, capability map, workflows
config/                # MCP and deployment configuration
scripts/               # Utility and workflow scripts
tests/                 # Test suites (pytest)
```

## Coding Standards

- **Type hints**: Mandatory on all public function signatures (mypy --strict compatible)
- **Docstrings**: NumPy-style for modules, classes, and functions
- **Comments**: Explain "Why" (intent), not "How" (mechanics)
- **Async**: Prefer `async/await` for all I/O. Every external call MUST have a timeout
- **Error handling**: Use specific exceptions, never bare `except Exception:`. Use `cohezion.reliability.get_circuit()` for external integrations
- **Validation**: Pydantic at boundaries. Fail fast with assertions and schema validation
- **KISS**: If simple one-pass logic works, do not use a multi-agent swarm
- **Every directory in `src/`** MUST have an `__init__.py`
- **Template Driven**: New features must be preceded by a PRIME skill definition in `src/cohezion/skills/`

## Operational Protocols

- **Hallucination Resolution**: Ground system specs in HARDWARE_PROFILE_PRIME.md truth anchors. Never assume RTX/CUDA
- **Verification First**: Always run validation (lint, test, Great Expectations) before considering a task complete
- **Delegate Specialized Tasks**: Use sub-agent contexts for focused work (security audits, etc.) to prevent context bloat
- **Retrospection**: Each completed phase requires explicit retrospection before advancing
- **Token Efficiency**: Batch operations, cache results, delegate to local models where appropriate
- **Mock Live Services**: API endpoint tests must mock `get_compound_client()` to avoid hanging on Ollama. Patch at source: `cohezion.swarm.compound_client.get_compound_client`
- **Compound Loop**: PRIME skill → InstructionExpander → PlanExecutor → ExecutionOrchestrator → RetrospectionEngine → SkillRefiner → updated skill. CLI: `make compound-cycle` (dry-run) or `make compound-live` (Ollama)

## Hardware Profile (Strix Halo)

- **CPU**: AMD Ryzen AI MAX+ 395 (Zen 5, 16C/32T, AVX-512, AMX)
- **GPU**: AMD Radeon 8060S (RDNA 3.5 iGPU, unified memory) - NOT a discrete GPU
- **RAM**: 128 GiB LPDDR5X-8000 (unified CPU/GPU/NPU pool)
- **Storage**: 2TB NVMe SSD, 32GB ZVOL swap (ZFS)
- **Optimization**: Prefer zero-copy strategies and AVX-512/SIMD. Use `ndarray` (Rust) or `numpy` with AVX-512 flags
- **Local Models**: Ollama (deepseek-r1:70b, qwen3-coder:30b, phi3:mini). **Global concurrency limit = 4**

## Cost Guardrails

- Cloud Run: **Free Tier only** (min-instances=0, max-instances=1, ephemeral storage)
- Prefer local Ollama models over cloud API calls when possible
- Move compute-heavy simulations (QGP, Magnetohydrodynamics) to **Rust** via PyO3 bindings

## Git Hygiene

- Never commit files > 1MB (use git-lfs)
- Keep `.gitignore` comprehensive; check `git status` before committing
- Run `python scripts/assess_git_health.py` weekly for bloat/drift checks
- Ignored patterns: `**/venv/`, `*.dill`, `audio/`, `*.zip`

## Key Principles

- **HIHO Stability**: Maximum stability at exactly 50% coherence overlap (Half-In-Half-Out)
- **SPIN**: Fundamental unit of information = Rotation + Precession. Coherence when aligned
- **Compound Engineering**: Every feature makes every future feature easier to achieve
- **Observable AI**: Full transparency in swarm operations. Expose states and confidence levels before action
- **Deterministic Responsibility**: All significant actions use idempotency keys for reproducible outcomes
- **Expert Domain Lattice**: Route complex problems through 5 streams (Architect, Engineer, Biologist, Quantum HW, Quantum Algo)

## Context Modules (Read on Demand)

| Module | Location | Purpose |
|--------|----------|---------|
| Constitution | `.agent/CONSTITUTION.md` | Core ethics & behavioral pillars |
| Charter | `.agent/COHEZION_CHARTER.md` | SPIN, FLUME, HIHO, EDL |
| Capability Map | `.agent/CAPABILITY_MAP.md` | Skill registry & model routing |
| Coding Standards | `.agent/CODING_STANDARDS.md` | Technical baseline |
| Evolution Protocol | `.agent/EVOLUTION_PROTOCOL.md` | Autonomous improvement & healing |
| Hardware Profile | `.agent/HARDWARE_PROFILE_PRIME.md` | Verified system specs (truth anchor) |
| Git Hygiene | `.agent/GIT_HYGIENE.md` | Repository maintenance |
| Mission Journal | `src/cohezion/knowledge_graph/MISSION_JOURNAL.md` | Historical developments |
| Key Learnings | `src/cohezion/knowledge_graph/KEY_LEARNINGS.md` | Extracted wisdom |
