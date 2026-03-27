# Cohezion Capability Map

Verified capabilities organized by domain. Last updated: 2026-03-27 (Session 76).

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

**125+ route definitions** across 7 mounted files + `__init__.py`. Key groups:

| Group | Prefix | Endpoints | Source |
|-------|--------|-----------|--------|
| Core | `/` | 55 | `api/__init__.py` |
| Genesis Engine | `/api/genesis` | 19 | `services/genesis.py` |
| Modules | `/api/modules` | 11 | `services/modules_api.py` |
| Physics Extended | `/api/physics` | 9 | `services/physics_extended.py` |
| Research | `/research` | 7 | `research_endpoints.py` |
| Universe | `/api/universe` | 7 | `services/universe.py` |
| Worldviews | `/api/worldviews` | 7 | `services/worldviews.py` |
| Journeys | `/api/journeys` | 7 | `journeys.py` |
| World Model | `/api/world-model` | 5 | `services/world_model.py` |
| Ouroboros | `/api/ouroboros` | 3 | `services/ouroboros_api.py` |
| Mycelium | `/api/mycelium` | 3 | `services/mycelium_api.py` |
| Telemetry | `/telemetry` | 1 | `telemetry.py` |

**Defined but not mounted:** `streaming.py` (6), `observability_endpoints.py` (9), `journey_status.py` (6), `anima.py` (4), `architecture.py` (1), `brand.py` (1).

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
| Maintenance MCP | `cohezion-maintenance-mcp/` | 6 tools: graph_health, graph_prune_orphans, graph_compact, verify_graph_schema, vault_audit, surreal_table_stats |
| Graph HIHO Metric | `maintenance_mcp/graph_health.py` | Weighted: connectivity 0.3, reciprocity 0.2, freshness 0.2, (1-orphan_ratio) 0.3. Target: 0.5 +/- 0.15 |

## 5. Templates & Skills

| Capability | Module | Description |
|------------|--------|-------------|
| Template Engine | `core/template_engine.py` | Parses PRIME .md → SkillSpec → agent stubs |
| PRIME Skills | `skills/` (178 markdown files) | Indexed in `skill_registry.json` |
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

### Claude Code Agents (`.claude/agents/` — 18 agent definitions)
| Agent | Role |
|-------|------|
| test-runner | Run pytest, no edits |
| code-reviewer | Review-only, no execution |
| simulation-runner | Sandboxed simulation execution |
| compound-planner | Planning only, no edits |
| compound-executor | Full compound cycle execution |
| skill-researcher | PRIME skill generation |
| skill-refiner | Skill refinement loop |
| security-reviewer | Security audit |
| kernel-researcher | Kaggle kernel research |
| kernel-writer | Kaggle kernel authoring |
| tree-evolver | Evolutionary tree optimization |

### Specialist Agents (A2A agent cards + PRIME skills)
| Agent | Role |
|-------|------|
| vault-keeper | Vault health, orphan detection, frontmatter enforcement |
| surreal-dba | Schema validation, index optimization, graph health |
| claude-specialist | Claude Code/API optimization, agent teams |
| gemini-specialist | Gemini CLI, Google ADK, ecosystem integration |
| ollama-specialist | Local model lifecycle, VRAM, DynamicModelRouter |
| mcp-specialist | MCP server lifecycle, tool schemas, health monitoring |
| platform-coordinator | Cross-platform routing, cost tiers, fallback chains |

## 7. Model Routing

| Task Type | Local Model | Claude Model |
|-----------|-------------|--------------|
| Verification | phi3:mini | haiku |
| Coding | qwen3-coder:30b | sonnet |
| Reasoning | deepseek-r1:70b | opus |
| Scientific | Intern-S1-mini (8B) | sonnet |
| General | phi3:mini (default) | sonnet |

**Ollama inventory**: 47 models pulled locally (verified 2026-03-27).
**Notable additions**: Intern-S1-mini (8B scientific reasoning model).
**Hardware**: AMD Ryzen AI MAX+ 395, 128GB LPDDR5X, Radeon 8060S iGPU (UMA).
**Concurrency**: Global limit = 4. Cost guardrail: Cloud Run Free Tier only.
**Cost routing tiers**: 70% simple (Ollama/Flash-Lite, free) -> 20% medium (Sonnet, $3/M) -> 10% hard (Opus, $15/M).

## 8. Codebase Scale (verified 2026-03-27)

| Metric | Count |
|--------|-------|
| Python files | 702 |
| Packages (`__init__.py`) | 109 |
| PRIME skill definitions | 178 |
| Claude Code agents | 18 |
| Specialist agents (A2A) | 7 |
| API endpoints (mounted) | 125+ |
| Tests passing | 5,160 / 5,237 (98.5%) |
| MCP servers | 3 (cloud-vault-mcp, compound-mcp, cohezion-maintenance-mcp) |

## 9. Competition Capabilities (active 2026-03-27)

| Competition | Status | Key Details |
|-------------|--------|-------------|
| AMD Speedrun | Active | 3 kernels ranked; MoE closest to parity (1.41x gap); GEMM quant ceiling confirmed |
| Nemotron | Active | v20 adapter trained (LoRA r=32); submission uploading |
| AIMO3 | Scaffolded | Sandbox exists; evaluation framework built; H100 compute available |
| Kaggle API | Restored | KGAT_ token auth via `KAGGLE_API_TOKEN` env var |
