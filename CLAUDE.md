# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# Cohezion - Compound AI Orchestration

COHEZION: 12D agentic universe with FLUME VAE, compound engineering, multi-agent swarm, and autonomous skill refinement. **Governed by Constitution (`.agent/CONSTITUTION.md`) and Charter (`.agent/COHEZION_CHARTER.md`).**

## Token-Efficient Essentials

### ⚡ Core Commands
```bash
uv run pytest tests/ -q              # Full test suite (5,200+ tests)
uv run pytest tests/compound/ -v     # Run module tests
uv run pytest tests/test_*.py::name  # Single test
make format && make lint && make all # Check → fix → verify
```

### ⚡ Security Standards (MANDATORY)
```bash
# NEVER print, echo, or display any passwords or secrets
# NEVER store SUDO_PASSWORD in .env for scripts - use passwordless sudo
# NEVER write secrets to temp files that persist

# ALWAYS use 'uv' for package management - NEVER bare 'pip' or 'pip install'
uv pip install package              # Install package
uv venv && source .venv/bin/activate && uv pip install -e .  # New project setup

# For sudo: configure passwordless sudo for automation OR run interactively
# Do NOT attempt to parse .env for SUDO_PASSWORD - this is a security risk
```

### ⚡ Critical Principles (Sessions 40-55)
1. **Implement ONE feature, validate manually, write 5 tests** (NOT 600 pre-implementation tests)
2. **Use proven templates** (e.g., cloud-vault-mcp: 40+ tools) over greenfield exploration
3. **Mock live services at source**: `@patch("cohezion.swarm.compound_client.get_compound_client")`
4. **Report honest metrics** (98.8% beats inflated 100% for decision-making)
5. **Never write infrastructure for products that don't exist**

### ⚡ Execution Priority (Sessions 56+)

**EXECUTE FIRST. PLAN SECOND. INFRASTRUCTURE NEVER (unless explicitly requested).**

When given a task:
1. **Can you execute it RIGHT NOW with existing tools?** If yes, do it. No planning phase needed.
2. **Does it need a plan?** Only if 10+ files or architectural. Ask user if they want `/spec`.
3. **Are you building a helper/framework/tool?** STOP. Re-read the original task. Build the deliverable, not tools to build the deliverable.

**Session budget:** If >30 minutes have passed without producing a runnable artifact (code change, submission, commit), you are in infrastructure drift. STOP and deliver something concrete.

**Evidence of drift (any one = STOP):**
- Creating a new class/module not in the original request
- Writing >100 lines of "framework" code before the first test passes
- Researching dependencies for a tool you are building to build the actual thing
- The phrase "first we need to set up..." when the thing already exists

### ⚡ Vault-First Knowledge Management (NEW: Session 56)

**CRITICAL**: All session learnings MUST be logged to vault, not MEMORY.md directly.

**MEMORY.md = Compiled Cache** (auto-generated weekly):
- 95 lines (vs 1177 lines old version)
- Recent decisions (last 7 days)
- Most-used patterns (top 10)
- Quick reference only

**Vault = Single Source of Truth**:
- `~/vaults/cohezion-vault/` (150+ decisions, patterns, experiments)
- Searchable via `vault_find_relevant_context(query)`
- Survives across sessions, compounds knowledge

See skill: `cohezion-vault-workflow` for vault API examples (log decisions, experiments, patterns) and MEMORY.md regeneration.

### ⚡ Architecture at a Glance
| Layer | Components | Entry |
|-------|-----------|-------|
| **Compound** | Executor, SkillRefiner, RetrospectionEngine, JourneyTracker | `CompoundExecutor` |
| **Swarm** | TeamOrchestrator, ExecutionOrchestrator, DynamicModelRouter | `TeamExecutor` |
| **Cache** | SemanticCache (L1 hash + L2 cosine + L3 vault, 95%+ hit rate) | `SemanticCache` |
| **Cost Opt** | CostAwareRouter (27.3% savings), BudgetEnforcer, ModelQualityClassifier | `CostAwareRouter` |
| **Persistence** | SessionPersistence (vault + JSONL), MetricsCollector, DegradationDetector, ExecutionTraces (Meta-Harness L225) | `SessionManager` |
| **Physics** | SU(2) Spinors, Riemannian/Lagrangian, FiberBundle, GaugeTheory, Fisher metric | `SpinorState` |
| **World Model** | JEPA predictor (86K params, causal masking), Cosmogony, SymmetryBreaking | `JEPAWorldModel` |
| **Bioelectric** | Levin bioelectric network, gap junction percolation, HIHO phase transition | `BioelectricNetwork` |
| **Natural Capital** | InVEST habitat quality model, HIHO proximity as habitat quality | `NaturalCapitalModel` |
| **Evo Model** | Agents-as-EVOs physics, evolutionary dynamics on manifold | `EvoModel` |
| **Worldviews** | 16 indigenous traditions x 10 cosmogony steps, Worldview Explorer | `WorldviewExplorer` |
| **Ouroboros** | Ouroboros bridge + Mycelium network wired into Genesis chain | `OuroborosBridge` |
| **Environments** | ManifoldEnv (gymnasium, 19D obs), SwarmEnv (multi-agent gauge coupling) | `gym.make('Cohezion/ManifoldEnv-v0')` |
| **Governance** | AutonomyEngine (cosmogonic tiers), ConciergeAgent, KnowledgeBridge, FlumeBridge | `AutonomyEngine` |
| **Data Mesh** | DataProduct (typed SLA), MCP Registry (tier access control + call tracking) | `get_cohezion_data_products()` |
| **Providers** | OllamaProvider (local), GeminiProvider (cloud: Flash-Lite/Flash/Pro) | `get_model_provider("gemini")` |
| **Genesis UI** | 12 components across 8 tabs: BlochSphere, GenesisScene, FlumeLatentViz, SwarmTopologyViz, etc. | `/genesis` route |
| **Knowledge** | Vault-First (decisions/patterns/experiments), auto-compiled MEMORY.md | `vault_find_relevant_context` |

### ⚡ Agent Protocol Stack (6-Protocol Architecture)
| Protocol | Purpose | Cohezion Status |
|----------|---------|----------------|
| **MCP** | Agent ↔ Tool connectivity | **Strong** (41+ tools via cloud-vault-mcp, compound-mcp, maintenance-mcp) |
| **A2A** | Agent ↔ Agent discovery/coordination | **In Progress** (7 specialist agents with agent cards) |
| **UCP** | Commerce lifecycle | N/A |
| **AP2** | Payment authorization | N/A |
| **A2UI** | Agent ↔ UI composition | **Strong** (8-component catalog, declarative experience scripts, A2UIRenderer) |
| **AG-UI** | Event streaming transport | **Strong** (typed SSE events, /api/agui/stream, 15+ event types) |

### ⚡ Platform Coordination
| Specialist | Role | Format |
|-----------|------|--------|
| `vault-keeper` | Vault health, orphan detection, frontmatter enforcement | Agent + PRIME |
| `surreal-dba` | Schema validation, index optimization, graph health | Agent + PRIME |
| `claude-specialist` | Claude Code/API optimization, agent teams | Agent + PRIME |
| `gemini-specialist` | Gemini CLI, Google ADK, ecosystem integration | Agent + PRIME |
| `ollama-specialist` | Local model lifecycle, VRAM, DynamicModelRouter | Agent + PRIME |
| `mcp-specialist` | MCP server lifecycle, tool schemas, health monitoring | Agent + PRIME |
| `platform-coordinator` | Cross-platform routing, cost tiers, fallback chains | Agent + PRIME |

**Cost routing tiers**: 70% simple (Ollama/Flash-Lite, free) → 20% medium (Sonnet, $3/M) → 10% hard (Opus, $15/M)

### ⚡ Quick Reference
- **Language**: Python 3.13+ | **Package Manager**: `uv` (never bare python)
- **DB**: SurrealDB (ws://localhost:8000) | **API**: FastAPI :8080
- **Tests**: 5,160 passing / 47 failing (98.5%) — verified 2026-03-27 | **Coverage**: html report in `htmlcov/`
- **CI**: `make lint-check && uv run pytest` before commit
- **Entry point**: `cohezion = "cohezion.__main__:main"`
- **Vault**: `~/vaults/cohezion-vault/` — Query via `vault_find_relevant_context(query)`

## The Compound Engineering Loop (Production-Ready)

```
PRIME Skill (markdown)
  ↓
InstructionExpander (parse → tasks)
  ↓
PlanExecutor (tactical plan)
  ↓
ExecutionOrchestrator (execute with 11-step pipeline)
  ├─ RequestAlignmentAnalyzer (coherence check)
  ├─ GlobalMetricsAggregator (record instance metrics)
  ├─ DegradationDetector (thermal, quality thresholds) → healing/ + resilience/ + CostAwareRouter feedback
  └─ JourneyTracker (12D universe position) + JEPA surprise + bioelectric percolation
  ↓
RetrospectionEngine (extract learnings, flag anomalies, pivot detection)
  ↓
SkillRefiner (update skill definition)
  ↓
SkillConsensusVoter (multi-agent validation)
  ↓
Updated Skill (loop again)
```
**CLI**: `uv run python scripts/drivers/compound_cycle.py` (dry-run) or via `/compound` API endpoint.

## Key Directories (Find Anything Fast)

| Path | Purpose | Key Files |
|------|---------|-----------|
| `src/cohezion/compound/` | Executor, SkillRefiner, RetrospectionEngine, JourneyTracker | `executor.py` (11-step) |
| `src/cohezion/swarm/` | Team orchestration, cost routing, model quality | `team_executor.py`, `cost_aware_router.py` |
| `src/cohezion/cache/` | L1/L2/L3 semantic cache (95%+ hit rate) | `semantic_cache.py` |
| `src/cohezion/skills/` | 183 PRIME skill definitions (*.md + *.py) | `skill_registry.json` |
| `src/cohezion/persistence/` | SurrealDB, checkpoints, session recovery | `surreal_client.py` |
| `src/cohezion/environments/` | Gymnasium RL envs: ManifoldEnv (single), SwarmEnv (multi-agent) | `manifold_env.py`, `swarm_env.py` |
| `src/cohezion/api/` | FastAPI backend (190+ endpoints) | `__init__.py`, `services/genesis.py` |
| `src/cohezion/flume/` | FLUME VAE (256D latent space) | `flume_vae.py` |
| `src/cohezion/physics/` | **Genesis Engine**: SU(2) spinors, Riemannian, Lagrangian, fiber bundles, gauge theory, Fisher metric, cosmogony | `spinor.py`, `cosmogony.py` |
| `src/cohezion/world_model/` | JEPA world model (86K params, causal masking, CPU-trainable) | `jepa_world_model.py` |
| `src/cohezion/world_model/bioelectric_model.py` | Levin bioelectric network, gap junction percolation | `BioelectricNetwork` |
| `src/cohezion/world_model/natural_capital.py` | InVEST habitat quality, HIHO proximity mapping | `NaturalCapitalModel` |
| `src/cohezion/world_model/evo_model.py` | Agents-as-EVOs evolutionary physics | `EvoModel` |
| `src/cohezion/worldviews/` | 16 indigenous traditions x 10 cosmogony steps | `WorldviewExplorer` |
| `src/cohezion/ouroboros/` | Ouroboros bridge + Mycelium network | `OuroborosBridge` |
| `src/cohezion/audio/` | PocketTTS narrator, Kyutai Labs integration | `narrator.py` |
| `src/web/anima_dashboard/` | Next.js 16 + Three.js + Tone.js webapp | `/genesis` route (4 tabs) |
| `tests/conftest.py` | **CRITICAL**: Singleton reset for FLUME VAE, RL policy, loggers | **Read this first** |

## Coding Standards (Cohezion-Specific)

- **FLUME-First**: New modules MUST encode/decode through FLUME. Start with `encode()` → latent reasoning → `decode()`. Don't retrofit — wire from the start (Learning 215)
- **Wire-at-Creation**: New modules MUST declare a wiring target (DegradationDetector, CapabilityMatrix, CompoundExecutor step, or Hookify rule) at creation time. Build-then-forget = 41 orphaned modules (Learning 227)
- **Async**: All I/O must be `async/await` with timeouts. No blocking calls in executors
- **Error handling**: Specific exceptions + circuit breakers (`cohezion.reliability.get_circuit()`)
- **Validation**: Pydantic at boundaries (input/output). Fail fast with assertions
- **Every `src/` dir**: MUST have `__init__.py`. Enables vault skill discovery
- **Observability**: Log state transitions (input → processing → output). Track coherence

## Token Budgets (Conservative Estimates)

| Task | Tokens | Pattern |
|------|--------|---------|
| Implement 1 feature | 500-1,500 | Copy template → code → manual test → 5 tests |
| Research + implement | 2,000-3,000 | Quick survey → proof of concept → tests |
| Full test suite run | 100 | `uv run pytest tests/ -q` (no code changes) |
| Single test debug | 200-500 | Add print → run → check output → fix → verify |
| Skill refinement loop | 1,500-2,500 | Analyze failures → update PRIME skill → retest |
| **ANTI-PATTERN**: Research-first | 5,000-10,000 | 1,200 lines research + 600 tests + 0 implementation = wasted |
| **ANTI-PATTERN**: Infrastructure play | 8,000+ | Dependency research, 4,400 placeholder tests, product doesn't exist |

**Rule**: If feature doesn't exist yet, DON'T build infrastructure. Implement, validate, THEN test.

## Operational Patterns

See skills: `cohezion-debugging-scenarios` for test isolation, singleton resets, and flaky test fixes. See global rules: `tdd-enforcement.md` for mocking patterns, `verification-before-completion.md` for verification protocol.

### ⚡ Measurement Integrity
- **Report actual numbers**: 2,675/2,700 passing (98.1%) > 1,599 passing (inflated)
- **Flag discrepancies**: If independent test shows different count, request re-verification immediately
- **Verify claims**: "Complete" = files exist AND tests pass, not projected

## Hardware & Constraints (Strix Halo)

- **CPU**: AMD Ryzen AI MAX+ 395 (16C/32T, AVX-512, AMX) | **GPU**: Radeon 8060S (iGPU, unified memory)
- **RAM**: 128 GiB LPDDR5X | **Storage**: 2TB NVMe + 32GB swap (ZFS)
- **Local Models**: Ollama (deepseek-r1:70b, qwen3-coder:30b, phi3:mini). **Global limit = 4 concurrent**
- **Cost**: Cloud Run = Free Tier only (no instances when idle). Prefer local Ollama over API calls
- **Truth Anchor**: See `HARDWARE_PROFILE_PRIME.md` (never assume RTX/CUDA)

## Multi-Session Worktree Pattern (MANDATORY)

See skill: `cohezion-worktree-workflow` — covers session scripts (start/end/list_sessions.sh), manual git worktree commands, commit format with Co-Authored-By, and recommended git config.

## Design Principles (Compound-Aligned)

- **HIHO Stability** (50% coherence): Optimal balance between exploitation + exploration
- **Compound Engineering**: Every feature makes future features easier (loop → skill updates → better routing)
- **Observable AI**: Log states before action. Track coherence. Expose confidence. Enable rollback
- **Deterministic Responsibility**: Idempotency keys for all external calls. Replay from checkpoints
- **Expert Domain Lattice**: Route complex requests through specialist agents (Architect, Engineer, Biologist, QHW, QAlgo)
- **SPIN Coherence**: Information unit = Rotation + Precession. Alignment when phases match

## Critical References (Read First)

| Document | Purpose | Key Insight |
|----------|---------|------------|
| `tests/conftest.py` | **TEST ISOLATION** | FLUME VAE + RL policy + logger resets prevent flaky tests |
| `.agent/CONSTITUTION.md` | **HARD CONSTRAINTS** | No WMD/infrastructure attacks. Honesty mandatory. Idempotency required |
| `.agent/COHEZION_CHARTER.md` | **DESIGN THEORY** | SPIN, FLUME, HIHO, Expert Domain Lattice |
| `HARDWARE_PROFILE_PRIME.md` | **TRUTH ANCHOR** | Never assume RTX/CUDA. AMD Ryzen AI MAX+ 395 only |
| `src/cohezion/knowledge_graph/KEY_LEARNINGS.md` | **LESSONS EXTRACTED** | Historical patterns, anti-patterns, cost lessons |
| `.claude/rules/git-workflow.md` | **GIT PATTERNS** | Conventional commits, branch naming, PR targets |
| `.claude/rules/testing.md` | **TEST RULES** | Avoid `walk_packages`, mock at source, HIHO invariant |
| `cloud-vault-mcp/` | **MCP TEMPLATE** | 40+ tools, FastMCP proven. Copy when building MCP servers |
| `src/cohezion/physics/observer_patch.py` | **OPH BRIDGE** | Observer Patch Holography axioms → SPIN coherence. FloatingPragma (Apache 2.0) |
| `src/cohezion/data_mesh/data_product.py` | **DATA MESH** | Typed data products with SLA for 17+ MCP servers. Dehghani (2022) |
| `src/web/anima_dashboard/src/a2ui/` | **A2UI CATALOG** | 9 declarative components + experience scripts. Google A2UI v0.9 (Apache 2.0) |
| `src/cohezion/api/agui_events.py` | **AG-UI EVENTS** | 15+ typed SSE event types. CopilotKit AG-UI (Apache 2.0) |

## Agent Journey Tracking & Request Alignment

See skill: `cohezion-journey-tracking` — covers JourneyTracker API (record_state, record_transition, save_checkpoint, rollback), RequestAlignmentAnalyzer (coherence/completeness/drift-risk), and alignment anti-patterns.

## Metrics & Observability (Production Monitoring)

See skill: `cohezion-metrics-observability` — covers GlobalMetricsAggregator (record_execution, get_metrics_snapshot, get_skill_metrics), BudgetEnforcer (monthly budget checks, token control), and cost tracking.

## Data Storage Architecture for Simulations

See skill: `cohezion-data-governance` — covers three-tier storage (Git/SurrealDB/External), pre-commit hook for >50MB files, JourneyTracker artifact registration, deterministic recovery, and success metrics.

---

## Common Debugging Scenarios

See skill: `cohezion-debugging-scenarios` — covers test isolation/singleton pollution, flaky tests with random seeds, Ollama timeouts, journey tracking silent failures, and token count mismatches.

## Skill Routing

See skill: `cohezion-skill-routing` for the decision tree, keyword-to-skill routing table, and overlap resolution guide. When in doubt: `bmad-help`.

## Quick Lookup

| Need | Command | File |
|------|---------|------|
| Run tests (all) | `uv run pytest tests/ -q` | `pytest.ini` |
| Run tests (module) | `uv run pytest tests/compound/ -v` | `tests/conftest.py` |
| Format + lint | `make format && make lint` | `Makefile` |
| Check types | `make type-check` | `pyproject.toml` |
| Start API | `uv run uvicorn cohezion.api:app --reload` | `src/cohezion/api/__init__.py` |
| Find skill | `grep -r "skill_name" src/cohezion/skills/` | `skill_registry.json` |
| Debug journeys | `JourneyTracker.get_journey(agent_id)` | `src/cohezion/compound/journey_tracker.py` |
| Check alignment | `RequestAlignmentAnalyzer.analyze(...)` | `src/cohezion/compound/request_alignment_analyzer.py` |

## Kaggle Blackwell Handshake (Critical)
When orchestrating jobs on Kaggle G4 (Blackwell) infrastructure, standard `accelerator` requests will fail. You MUST follow this handshake:
1.  **Metadata**: Set `"machine_shape": "NvidiaRtxPro6000"` and `"dockerImageVersionId": 31287` in the internal `.ipynb` metadata.
2.  **Environment**: Copy the `nvidia_utility_script` to `/tmp` and `chmod +x` the `ptxas-blackwell` binary.
3.  **Triton**: Set `os.environ["TRITON_PTXAS_PATH"]` to the `/tmp` binary path.
4.  **Auth**: Pre-authorize models in the `"model_sources"` metadata array.
