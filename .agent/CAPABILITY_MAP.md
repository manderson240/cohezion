# Cohezion Capability Map

Verified capabilities organized by domain. Last updated: 2026-02-06.

## 1. Simulation & Physics

| Capability | Module | Status |
|------------|--------|--------|
| Mass Simulation | `mass_sim/` (batch_runner, exporter, persistence) | Tuned: 0.5019 mean coherence, 92.7% within HIHO |
| Rust FlumePhysics | `cohezion_core_rs` (PyO3 + WASM) | Running: delta_scale=0.01, hiho_damping=0.01 |
| HIHO Attractor | 3 fixes: agent init, LayerNorm beta, Rust damping | Verified: 25M cycles stable at 0.5 |
| Hamiltonian Dynamics | `physics/hamiltonian.py` | Built: double-well, harmonic, HIHO-well potentials |
| Fractal Universe | `universe/fractal_universe.py` | Active: 12D sim with biological traits |
| Quantum Solver | `physics/peaked_solver.py` | Verified: 36-qubit MPS (Bond 64), bit-exact |

## 2. Machine Learning

| Capability | Module | Status |
|------------|--------|--------|
| FLUME VAE | `flume/autoencoder.py` + `training.py` + `dataset.py` | Trained: MSE 0.1322 on real data, KL 0.4329 |
| RL REINFORCE | `rl/environment.py` + `trainer.py` + `reward_shaping.py` | Trained: 200 ep, 0.991 coherence |
| Gymnasium Env | `cohezion/FlumeNav-v0` | Registered, Hamiltonian dynamics |
| Data Pipeline | `mass_sim/exporter.py` + `pipeline/` | Working: 61 .npy, 11K vectors |
| Weight Bridge | `pipeline/weight_bridge.py` | Built: PolicyNetwork → FlumePhysics (3-layer collapse) |
| Trained Navigator | `pipeline/trained_navigator.py` | Built: deterministic batch navigation for mass sim |
| Hyperparam Debate | `pipeline/hyperparameter_debate.py` | Built: DemocraticDebate → structured RL params |
| Incremental Training | `pipeline/incremental_trainer.py` | Built: resume VAE/RL from checkpoint |

## 3. API (FastAPI)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/simulate/step` | POST | Single simulation step |
| `/wallet/{agent_id}` | GET | Agent credit balance |
| `/health` | GET | System health check |
| `/flume/encode` | POST | Encode text to 256D latent |
| `/flume/decode` | POST | Decode latent to text |
| `/flume/interpolate` | POST | Interpolate between latent points |
| `/rl/step` | POST | Single RL environment step |
| `/rl/episode` | POST | Run full RL episode |
| `/rl/policy-info` | GET | Current policy parameters |

Server: `uv run uvicorn cohezion.api:app --reload --port 8080`

## 4. Infrastructure

| Capability | Module | Description |
|------------|--------|-------------|
| Circuit Breaker | `reliability/__init__.py` | CLOSED/OPEN/HALF_OPEN, failure threshold, auto-recovery |
| Resource Monitor | `reliability/monitor.py` | CPU/RAM/VRAM tracking, concurrency semaphore (limit=4) |
| Connection Pool | `reliability/pool.py` | Shared httpx.AsyncClient, socket reuse |
| Semantic Cache | `reliability/semantic_cache.py` | Vector similarity-based response cache |
| Prompt Guard | `security/prompt_guard.py` | 70+ injection patterns, multilingual |
| Output Filter | `security/output_filter.py` | PII redaction |
| SurrealDB Client | `core/persistence/surreal_client.py` | Async with in-memory fallback |
| OOM Protection | `mass_sim/memory_guard.py` | /proc-based, abort at RSS>115GB |

## 5. Templates & Skills

| Capability | Module | Description |
|------------|--------|-------------|
| Template Engine | `core/template_engine.py` | Parses PRIME .md → SkillSpec → agent stubs |
| PRIME Skills | `skills/` (123 markdown files) | Indexed in `skill_registry.json` |
| Capability Registry | `registry/capability_registry.py` | TF-IDF search, usage tracking |
| Skill Generator | `learning/__init__.py` | Auto-generates agent stubs from skills |
| Team Orchestrator | `swarm/team_orchestrator.py` | PRIME skills → Claude Code agent specs |
| Retrospection Engine | `core/compound/retrospection.py` | Pattern analysis, compound scoring |
| Agent File Validation | `validation/agent_schema.py` | Pydantic schema for `.claude/agents/*.md` frontmatter |

## 6. Agents

### Python Agents (Ollama-backed)
| Agent | Module | Role |
|-------|--------|------|
| BaseAgent | `agents/base.py` | ABC with caching, security, refinement loop |
| LabAgent | `agents/lab_agent.py` | Research and experimentation |
| AlignmentAgent | `agents/alignment_agent.py` | Constitutional audit |
| NarrativeAgent | `agents/narrative_agent.py` | Journey narration |
| ModelWranglerAgent | `swarm/model_wrangler_agent.py` | Model lifecycle management |
| DemocraticDebate | `swarm/democratic_debate.py` | 7-persona consensus |

### Claude Code Agents (`.claude/agents/`)
| Agent | Tools | Role |
|-------|-------|------|
| test-runner | Bash, Read | Run pytest, no edits |
| code-reviewer | Read, Glob, Grep | Review-only, no execution |
| simulation-runner | Bash, Read, Edit, Write | Sandboxed simulation execution |
| compound-planner | Read, Glob, Grep, Bash | Planning only, no edits |
| skill-researcher | Read, Glob, Grep, Write | PRIME skill generation |

## 7. Model Routing

| Task Type | Local Model | Claude Model |
|-----------|-------------|--------------|
| Verification | phi3:mini | haiku |
| Coding | qwen3-coder:30b | sonnet |
| Reasoning | deepseek-r1:70b | opus |
| General | phi3:mini (default) | sonnet |

**Hardware**: AMD Ryzen AI MAX+ 395, 128GB LPDDR5X, Radeon 8060S iGPU (UMA).
**Concurrency**: Global limit = 4. Cost guardrail: Cloud Run Free Tier only.
