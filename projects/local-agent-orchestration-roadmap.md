# Local Agent Orchestration Roadmap

**Created**: 2026-02-13
**Status**: Active
**Tags**: #compound-engineering #agent-orchestration #local-models #roadmap

## Vision

Transform Cohezion from cloud-dependent agent orchestration into a fully autonomous local agent swarm running on Strix Halo (128GB RAM), using specialized local models for each EDL role, with compound learning from every execution.

## Phase 1: Foundation Update (Session 59 — ~2 hours)

### 1.1 Update CompoundConfig operation→model mapping
- `analyze` → `glm-4.7-flash` (was phi3:mini)
- `search` → `phi4-mini-reasoning` (was phi3:mini)
- `default_model` → `phi4-mini-reasoning` (was phi3:mini)

### 1.2 Expand CostAwareRouter model profiles
Add profiles for all 8 local models with quality/speed/cost scores:
- phi4-mini-reasoning: quality=0.75, speed=70 t/s, latency=30ms
- glm-4.7-flash: quality=0.90, speed=25 t/s, latency=80ms
- qwen3-coder:30b: quality=0.88, speed=25 t/s, latency=80ms
- gpt-oss:20b: quality=0.85, speed=35 t/s, latency=60ms
- deepcoder:14b: quality=0.82, speed=17 t/s, latency=120ms
- nemotron-3-nano: quality=0.80, speed=20 t/s, latency=100ms
- snowflake-arctic-embed2: quality=0.92 (embedding), speed=200 t/s
- nomic-embed-text: quality=0.85 (embedding), speed=300 t/s

### 1.3 Update TeamOrchestrator task→model mapping
- reason/architect/plan → glm-4.7-flash (was deepseek-r1:70b)
- code/implement/refactor → qwen3-coder:30b (unchanged)
- verify/test/lint → phi4-mini-reasoning (was phi3:mini)

### 1.4 Configure Ollama environment
Create systemd override or startup script:
```bash
OLLAMA_MAX_LOADED_MODELS=4
OLLAMA_NUM_PARALLEL=2
OLLAMA_KEEP_ALIVE=30m
OLLAMA_FLASH_ATTENTION=1
OLLAMA_KV_CACHE_TYPE=q8_0
```

### 1.5 Add model preloading to system startup
Create `scripts/preload_models.sh` — Tier 1+2 warm-up sequence.

**Success criteria**: All 5 tests pass, compound cycle runs with new model mapping.

---

## Phase 2: Model Pool Manager (Session 60 — ~3 hours)

### 2.1 Create ModelPoolManager class
`src/cohezion/swarm/model_pool_manager.py`
- Track loaded/loading/unloaded state for each model
- Implement hot/warm/cold tier assignment
- Expose `ensure_loaded(model, tier)` and `force_unload(model)`
- Monitor memory pressure via psutil
- Per-request `keep_alive` override based on tier

### 2.2 Integrate with OllamaGate
- ModelPoolManager wraps OllamaGate
- Before acquiring semaphore slot, ensure target model is loaded
- If loading would exceed memory budget, preemptively unload Tier 3

### 2.3 Add model lifecycle metrics
- Track load/unload count per model
- Track cold-start latency per model
- Track memory pressure at time of load
- Expose via GlobalMetricsAggregator

**Success criteria**: ModelPoolManager controls all model lifecycle, cold starts < 60s.

---

## Phase 3: Specialized Agent Definitions (Sessions 61-62 — ~5 hours)

### 3.1 Define PRIME skills for each EDL agent
Create specialized PRIME skill definitions:
- `ARCHITECT_AGENT_PRIME.md` → glm-4.7-flash, decompose complex requests
- `ENGINEER_AGENT_PRIME.md` → qwen3-coder:30b, implement code
- `ANALYST_AGENT_PRIME.md` → glm-4.7-flash, multi-perspective analysis
- `CRITIC_AGENT_PRIME.md` → phi4-mini-reasoning, fast validation
- `SYNTHESIZER_AGENT_PRIME.md` → glm-4.7-flash, merge outputs
- `ROUTER_AGENT_PRIME.md` → phi4-mini-reasoning, classify + route

### 3.2 Update AgentFactory for new model assignments
- Each agent spec includes preferred model + fallback
- Factory respects ModelPoolManager tier assignments
- Fallback chain: preferred → warm alternative → Tier 3 cold load

### 3.3 Implement structured output for agent communication
- Use Ollama's `format` parameter for JSON schema enforcement
- Define inter-agent message schemas (TaskRequest, TaskResult, CritiqueResult)
- Enable tool calling for agents that need external actions

**Success criteria**: All 6 agent types functional, end-to-end team execution works.

---

## Phase 4: Autonomous Compound Loop (Sessions 63-64 — ~4 hours)

### 4.1 Wire experience collection into compound executor
- Auto-persist JourneyTracker data to Parquet after each execution
- Feed into ExperienceTrainingPipeline (Session 58 work)
- Schedule periodic VAE retraining (every 50 executions)

### 4.2 Implement skill refinement from real data
- RetrospectionEngine analyzes execution patterns
- SkillRefiner updates PRIME definitions based on failure modes
- SkillConsensusVoter validates refinements across agents

### 4.3 Add degradation-triggered model swaps
- If agent coherence drops below 0.5 (HIHO threshold), swap to higher-quality model
- DegradationDetector triggers ModelPoolManager tier promotion
- Auto-demote back when coherence recovers

**Success criteria**: Compound loop runs autonomously, skill refinement produces measurable improvements.

---

## Phase 5: Long-Context & Specialization (Sessions 65-66 — ~4 hours)

### 5.1 Nemotron-3-nano integration for document analysis
- Load on-demand for tasks requiring >32K context
- Auto-detect context requirements from request analysis
- Unload immediately after completion (keep_alive=0)

### 5.2 Deepcoder:14b for mathematical/algorithmic tasks
- Route algorithm-heavy requests to dense 14B model
- Benchmark against MoE alternatives for quality comparison
- Update CostAwareRouter with empirical quality scores

### 5.3 Multi-model pipeline orchestration
- Chain: phi4 (classify) → glm-4.7 (plan) → qwen3 (implement) → phi4 (validate)
- Minimize inter-model latency via preloading next model during current execution
- Track end-to-end pipeline latency and optimize

**Success criteria**: Full fleet utilized, each model demonstrably better at its specialty.

---

## Phase 6: Swarm Autonomy (Sessions 67-70 — ~8 hours)

### 6.1 Self-directed task decomposition
- Architect agent generates task graphs from high-level goals
- TeamOrchestrator plans optimal wave execution
- ExecutionOrchestrator runs with full observability

### 6.2 Dynamic model budget allocation
- Per-session token budget enforcement across all agents
- Cost-aware routing considers remaining budget
- Graceful degradation: reduce model quality as budget depletes

### 6.3 Cross-session learning
- Persist agent performance metrics to SurrealDB
- Load historical context on startup via vault_pull_session_context
- Compound score trending across sessions

**Success criteria**: System handles multi-step tasks autonomously with measurable compound improvement.

---

## Key Metrics to Track

| Metric | Baseline | Phase 1 Target | Phase 6 Target |
|--------|----------|----------------|----------------|
| Compound score | 0.0 (no loop) | 0.5 | 0.75+ |
| Token efficiency | unknown | track baseline | 30% improvement |
| Cold-start frequency | every request | <2/session | <1/session |
| Agent coherence | 0.5 (default) | 0.6 | 0.7+ |
| Skill refinement cycles | 0 | 1/session | auto-triggered |
| Real experience records | 5 | 50 | 500+ |

## Dependencies

- [[decisions/2026-02-14-agent-orchestration-design-3-tier-hotwarmcold-model-rotation]]
- [[decisions/2026-02-13-local-model-roster-update-february-2026-sota-assessment]]
- [[decisions/2026-02-13-experience-vae-training-pipeline-session-58]]
- [[patterns/3-tier-hotwarmcold-model-rotation-for-local-llm-orchestration]]
- [[patterns/experience-feedback-loop]]
