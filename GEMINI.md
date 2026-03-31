# GEMINI.md - Cohezion Orchestration Layer

This document serves as the primary instructional context for Gemini CLI agents working on the **Cohezion** project. It establishes the core identity, architectural patterns, and engineering standards for the workspace.

## 1. Project Overview
**COHEZION** is a systemic AI orchestration ecosystem governed by **Quadrature Nexus Orchestration** and **Hermetic Compound Engineering**. It implements the **FLUME** methodology combined with **JEPA-aligned World Models** for high-fidelity simulation, autonomous research, and value precipitation.

### Core Concepts
- **12D/2048D Manifold**: Agents operate in a dual-state manifold. The 12D axiomatic layer captures observable state (Spatial, Time, Physics, etc.), while the 2048D latent layer encodes semantic intent.
- **HIHO Stability (0.5 Coherence)**: The fundamental attractor for stable "reality precipitation" is exactly 50% coherence overlap. Systems strive for this "Half-In-Half-Out" balance.
- **FLUME**: Fluid Latent Understanding through Manifold Encoding. A VAE-based system for continuous thought-vector interpolation.
- **Journeys & Trajectories**: Every task is a "journey" recorded as a 12D trajectory.

## 2. Technical Stack
- **Language**: Python 3.13+ (Strictly managed via **UV**).
- **Core Frameworks**:
  - **ML**: PyTorch (VAE, RL), Gymnasium (Sim Environments).
  - **API**: FastAPI (Async, 125+ endpoints).
  - **Database**: SurrealDB (ws://localhost:8000) with JSONL fallback.
  - **Inference**: Ollama (Local, 13+ models), GeminiProvider (Cloud: Flash-Lite/Flash/Pro), Anthropic (Cloud).
  - **Frontend**: Next.js 16 + Three.js + Tone.js (Genesis webapp on port 3001).
- **Infrastructure**: Docker, systemd, GitHub Actions.
- **Governance**: AutonomyEngine (cosmogonic tiers), ConciergeAgent, MCP Registry (18 servers).

### Multi-Provider Routing (NEW)
| Tier | Model | Cost | Use Case |
|------|-------|------|----------|
| HOT (always loaded) | phi4-mini, nomic-embed, qwen3.5:0.8b | $0.00 | Embeddings, simple queries |
| WARM (startup) | qwen3-coder:30b, glm-4.7-flash | $0.00 | Code, moderate reasoning |
| COLD (on-demand) | deepcoder:14b, nemotron | $0.00 | Advanced reasoning |
| CLOUD (API fallback) | gemini-2.5-flash, gemini-2.5-pro | $0.30-$2.00/M | When local models can't handle it |

**Cost routing**: 70% simple (Ollama, free) → 20% medium (Gemini Flash, $0.30/M) → 10% hard (Gemini Pro, $2.00/M).

## 3. Development Standards

### Coding Conventions
- **Line Length**: Strict **88-character** limit.
- **Formatting**: `ruff format` and `ruff check --fix`.
- **Type Safety**: Mandatory type hints for all public signatures (Mypy compatible).
- **Documentation**: **NumPy-style** docstrings for all modules, classes, and functions.
- **Async First**: Use `async`/`await` for all I/O operations with mandatory timeouts and circuit breakers.

### Workflow: Plan -> Act -> Validate
1. **Research**: Map the codebase and validate assumptions (e.g., `grep_search`, `read_file`).
2. **Strategy**: Formulate a grounded plan.
3. **Execution**: Apply surgical changes with tests.
4. **Validation**: Run `pytest`, `ruff`, and `mypy` to confirm integrity.

## 4. Key Commands

### Build & Setup
```bash
uv sync                # Sync dependencies
make onboard           # Full environment setup and health check
```

### Quality & Testing
```bash
make format            # Format code with ruff
make lint              # Lint and auto-fix with ruff
make type-check        # Run mypy
make test              # Run full test suite (~3,500 tests)
make test-fast         # Run fast unit tests only
```

### Running the System
```bash
uv run uvicorn cohezion.api:app --reload --port 8080      # Start API
uv run python -m cohezion journey start "Your Intent"    # Start an AI journey
uv run python -m cohezion simulate --example coherence_walk  # Run simulation
```

## 5. Directory Structure
- `src/cohezion/`: Core package source.
  - `universe/`: 12D simulation engine.
  - `swarm/`: Multi-agent orchestration + model routing (6 routers, 2 providers).
  - `flume/`: FLUME VAE (256D latent space) and latent navigation.
  - `compound/`: Execution loops, journey tracking, skill refinement.
  - `governance/`: AutonomyEngine, ConciergeAgent, FlumeBridge, KnowledgeBridge.
  - `data_mesh/`: DataProduct types with SLA for 18 MCP servers.
  - `physics/`: SU(2) spinors, Observer Patch Holography, cosmogony.
  - `api/`: FastAPI backend (125+ endpoints, AG-UI SSE streaming).
  - `providers/`: OllamaProvider, GeminiProvider (ModelProvider interface).
- `src/web/anima_dashboard/`: Next.js Genesis webapp (A2UI catalog, 9 components).
- `tests/`: 5,000+ tests (pytest + 9 Playwright e2e).
- `.agent/`: Constitution, Charter, operational guardrails.
- `.claude/`: Claude Code config (hooks, agents, MCP servers, settings).
- `.gemini/`: Gemini CLI config (6 MCP servers: skills, research, surreal, swarm, knowledge, bmad).

## 6. Gemini CLI Integration

### MCP Servers (`.gemini/settings.json`)
6 MCP servers configured: skills, research, surreal, swarm, knowledge, bmad. These provide tool access to Cohezion's internal systems.

### Google ADK Integration Path
- A2A agent cards (`.well-known/agent.json`) define capability-based task routing
- Use Google ADK for multi-protocol orchestration (MCP for tools, A2A for agent discovery)
- 7 specialist agents: vault-keeper, surreal-dba, claude-specialist, gemini-specialist, ollama-specialist, mcp-specialist, platform-coordinator

### Gemini-Specific Patterns
- **Flash-Lite for simple routing**: 200x cheaper than Pro for embeddings and classification
- **Flash for code generation**: 1M context window handles full module context
- **Pro for architectural decisions**: 2M context, deepest reasoning
- **Never use Pro for simple tasks** — Flash-Lite handles 70% of queries at near-zero cost

### Cross-Platform Coordination
- `AGENTS.md` (366 lines) is the cross-platform Rosetta Stone
- `TipOfTheSpearRouter` implements HOT→WARM→COLD→CLOUD routing
- `config/providers.yaml` defines fallback chains
- Platform-coordinator CONSUMES existing configs, doesn't rebuild them

## 7. Operational Guardrails
- **No Large Files**: Files > 1MB must use `git-lfs` or external storage.
- **Circuit Breakers**: Use `cohezion.reliability.get_circuit()` for external calls.
- **Ralph Loop & Autoresearch**: For every significant change or fix, execute a recursive [Benchmark -> Gate -> Propose -> Apply -> Verify] loop. Use `pytest` and diagnostic tools to ensure work is functional before posting. Aim for ≥0.5 HIHO coherence.
- **Reward System**: Agent progress is tracked via XP and achievements (see `cohezion rewards status`).
- **Ouroboros**: System flight recorder for self-healing (see `cohezion ouroboros`).

## 8. Kaggle Blackwell Handshake (Critical)
When orchestrating jobs on Kaggle G4 (Blackwell) infrastructure, standard `accelerator` requests will fail. You MUST follow this handshake:
1.  **Metadata**: Set `"machine_shape": "NvidiaRtxPro6000"` and `"dockerImageVersionId": 31287` in the internal `.ipynb` metadata.
2.  **Environment**: Copy the `nvidia_utility_script` to `/tmp` and `chmod +x` the `ptxas-blackwell` binary.
3.  **Triton**: Set `os.environ["TRITON_PTXAS_PATH"]` to the `/tmp` binary path.
4.  **Auth**: Pre-authorize models in the `"model_sources"` metadata array.

> [!IMPORTANT]
> Always use `uv run` for executing Python scripts to ensure environment consistency. Refer to `.agent/CONSTITUTION.md` for ethical and behavioral guidelines.
