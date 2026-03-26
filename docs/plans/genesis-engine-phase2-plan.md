# Cohezion Genesis Engine Phase 2: Full Observatory + Anthropic Portfolio

> **Status**: LONG-HORIZON AUTONOMOUS TASK
> **Target**: Wire ALL untapped codebase components into the Genesis Engine webapp, creating a complete showcase for the Anthropic "Research Engineer, Universes" role.
> **Predecessor**: Genesis Engine Phase 1 (11 commits, 9,364 lines, 163 tests — EXEMPLARY)
> **Branch**: `spec/genesis-engine` (continue in existing worktree)

## Context

The Genesis Engine Phase 1 grounded the cosmology in real math (SU(2), Lagrangian, gauge theory, Fisher metric) and built the foundation of the webapp. But only ~40% of Cohezion's capabilities are visible. The compound engineering loop, swarm orchestration, semantic cache, cost routing, thermodynamic metrics, topological persistence, FLUME latent space, and RL training are all implemented in the backend but INVISIBLE in the webapp.

The Anthropic "Research Engineer, Universes" role requires demonstrating: agentic environments, RL environments, simulation systems, rigorous evaluations, long-horizon tasks, and sandboxing. Cohezion has ALL of these — they just need to be wired into the showcase.

**Additionally**: Switch from npx to bun for frontend tooling, ensure Obsidian Vault and SurrealDB are integrated, capture agentic journeys for model improvements, and update the retrospect command.

## Research-Backed Vision

This phase integrates cutting-edge research into a transformational showcase:

| Research | Key Insight | Cohezion Integration |
|----------|------------|---------------------|
| [Agent World Model (AWM)](https://arxiv.org/html/2602.10090v2) | Programming-based env synthesis > LLM simulation for RL | Make 12D manifold an executable agentic environment |
| [OpenEnv (Meta+HuggingFace)](https://huggingface.co/blog/openenv) | Gym-style API (reset/step/action/obs) for agent envs | Make Cohezion OpenEnv-compatible, publish to HF Hub |
| [Topology-Aware MAS](https://arxiv.org/abs/2505.22467) | "Model and dynamically optimize inter-agent topology" | We already have TDA — wire it into swarm optimization |
| [Scaling Agent Systems](https://arxiv.org/abs/2512.08296) | Centralized coord contains errors to 4.4x vs 17.2x | Our swarm orchestrator IS centralized coordination |
| [TDA for Neural Networks](https://arxiv.org/abs/2312.05840) | Persistent homology reveals training dynamics structure | Apply TDA to JEPA world model training |
| [LeWorldModel (JEPA)](https://arxiv.org/abs/2603.19312) | 2-loss end-to-end world model from embeddings | Already implemented (M5) — extend with TDA analysis |
| [Kyutai Labs](https://kyutai.org/) | PocketTTS + Moshi + Mimi + MoshiVis | Multimodal narration already wired (M6) |
| Brahmagupta (628 CE) | Zero as generative ground, not absence | HIHO = δ₀ (already implemented, L176) |
| [VAEs Admit Kähler Structure](https://arxiv.org/html/2511.15172) | VAE latent spaces naturally have Riemannian/Fisher structure | Independent validation of our Fisher metric bridge |
| [LLM Training via Info Geometry + Quantum](https://arxiv.org/html/2506.15830v1) | Fisher ↔ Fubini-Study metric ↔ quantum state geometry | Theoretical backing for our SU(2) Bloch sphere approach |
| [OpenEnv + TRL](https://huggingface.co/docs/trl/en/openenv) | OpenEnv envs integrate with TRL GRPOTrainer | ManifoldEnv → TRL for GRPO/RLHF training |
| [PH-Enhanced Graph RL](https://arxiv.org/html/2603.06964) | Persistent homology → 9-18% higher RL rewards | Validates our M19 TDA-driven swarm optimization |
| [Neural Differential Manifold](https://arxiv.org/pdf/2510.25113) | Neural net layers as coordinate charts on manifold | Architecture pattern for FLUME encoder as manifold chart |
| [VAE-DLM Geometric Flows](https://arxiv.org/html/2410.10137v3) | Riemannian VAE with geometric flows, 25% OOD reduction | Pattern for FLUME latent dynamics |
| [CVPR 2026 GigaBrain Challenge](https://huggingface.co/datasets/open-gigaai/CVPR-2026-WorldModel-Track-Dataset) | World model evaluation benchmark for embodied AI | Potential benchmark target for JEPA world model |
| [Friston FEP / Active Inference](https://pmc.ncbi.nlm.nih.gov/articles/PMC5167251/) | Agents minimize variational free energy F = E - TS | **HIHO IS active inference**: F minimization = coherence → 0.5 |
| [Score-Based Riemannian Metric](https://arxiv.org/abs/2505.11128) | Diffusion model score → Riemannian metric on data manifold | FLUME decoder score = Fisher metric = manifold geometry |
| [Riemannian Diffusion Models](https://arxiv.org/abs/2202.02763) | Score-based generative modeling on Riemannian manifolds | Generative model for agent trajectories on the 12D manifold |
| [Horizontal Diffusion on Frame Bundles](https://openreview.net/forum?id=wd9p3TBbbz) | Diffusion via orthonormal frame bundle geometry | Our fiber bundle IS a frame bundle — natural fit |

## Design Principles

1. **Total artifact persistence** — ALL artifacts stored in SurrealDB (L183)
2. **Vertical slices** — Each milestone delivers working math + API + UI (L182)
3. **Exemplary depth** — Real math, real data, real code (exemplary-deep-planning skill)
4. **Obsidian Vault integration** — Knowledge flows vault ↔ SurrealDB ↔ webapp
5. **Bun over npx** — Faster builds, native TypeScript, modern tooling
6. **OpenEnv compatibility** — Gym-style API for the 12D manifold, publishable to HF Hub
7. **Topology-aware orchestration** — TDA drives swarm optimization, not just visualization

---

## Milestone 10: Tooling Migration (Bun + Infrastructure)

### 10.1 Switch frontend from npx to bun
- [ ] Install bun: `curl -fsSL https://bun.sh/install | bash`
- [ ] In `src/web/anima_dashboard/`: `bun install` (replaces npm install)
- [ ] Update `package.json` scripts to use `bun run` instead of `next`
- [ ] Verify `bun run build` produces identical output to `npx next build`
- [ ] Update CLAUDE.md commands: `bun run dev` / `bun run build`
- [ ] Remove `package-lock.json`, use `bun.lockb` instead

### 10.2 SurrealDB genesis schema activation
- [ ] Start SurrealDB: verify `ws://localhost:8000` is reachable
- [ ] Apply `genesis_schema.surql` migration: `surreal import --conn http://localhost:8000 --ns cohezion --db genesis src/cohezion/knowledge_graph/genesis_schema.surql`
- [ ] Verify 6 tables created: journey_transitions, universe_snapshots, prompt_artifacts, model_artifacts, simulation_artifacts, internal_state_snapshots
- [ ] Wire `journey_persistence_manager.py` to write to genesis tables on every journey

### 10.3 Obsidian Vault ↔ SurrealDB bridge
- [ ] Create `src/cohezion/persistence/vault_surreal_bridge.py`
  - Sync vault learnings (KEY_LEARNINGS.md) → SurrealDB `vault_learnings` table
  - Sync vault decisions → SurrealDB `vault_decisions` table
  - Bi-directional: query SurrealDB from vault, persist vault writes to SurrealDB
- [ ] Add API endpoint: `GET /api/vault/learnings` — serve vault knowledge to webapp
- [ ] Add webapp component: `VaultExplorer.tsx` — browse/search vault from Genesis UI

**Done when**: `bun run build` succeeds, SurrealDB has genesis tables, vault learnings queryable from webapp.

---

## Milestone 11: Compound Engineering Observatory

### 11.1 Compound Executor Pipeline Visualization
- [ ] Create `src/web/anima_dashboard/src/components/genesis/CompoundPipelineViz.tsx`
  - 11-step pipeline as animated flow diagram (vertical or horizontal)
  - Each step shows: status (pending/active/complete/error), duration, token count
  - Real-time updates via WebSocket or polling from `/api/compound/health`
  - Color coding: green=complete, yellow=active, gray=pending, red=error
  - Expandable detail panels showing vault query results, skill refinement diffs
- [ ] Create `useCompoundPipeline.ts` hook — fetch pipeline state from `/api/compound/health` + `/api/compound/history`
- [ ] Add API endpoint: `GET /api/compound/pipeline-state` — returns current 11-step state

### 11.2 Skill Refinement Loop Visualization
- [ ] Create `SkillRefinementViz.tsx`
  - Show skill before/after refinement diffs
  - SkillConsensusVoter results (approve/reject with reasons)
  - Refinement count per skill over time
  - Link to PRIME skill source files

### 11.3 Request Alignment Dashboard
- [ ] Create `AlignmentDashboard.tsx`
  - RequestAlignmentAnalyzer coherence/completeness/drift-risk scores
  - Real-time alignment monitoring for active executions
  - Historical alignment trends

**Done when**: User sees the 11-step pipeline animating in real-time on the Genesis `/compound` tab. Skill refinements visible. Alignment scores tracked.

---

## Milestone 12: Swarm Orchestration Visualization

### 12.1 Swarm Topology Graph
- [ ] Create `SwarmTopologyViz.tsx`
  - Team members as nodes (color by model: phi3=cyan, qwen=amber, deepseek=purple)
  - Task dependencies as directed edges (DAG)
  - Live status per node: idle/executing/complete/error
  - Throughput and latency metrics per agent
  - Democratic debate results shown as consensus indicators
- [ ] Create `useSwarm.ts` hook — fetch from `/api/swarm/metrics`

### 12.2 Model Router Decision Stream
- [ ] Create `ModelRouterViz.tsx`
  - Real-time stream of routing decisions (query → complexity assessment → model choice)
  - Cost per query with running total
  - Model utilization pie chart
  - Quality vs. cost tradeoff scatter plot

**Done when**: Swarm topology visible as interactive graph, model routing decisions stream in real-time.

---

## Milestone 13: Semantic Cache + Cost Dashboard

### 13.1 Cache Topology Visualization
- [ ] Create `CacheTopologyViz.tsx`
  - Three stacked tiers: L1 (hash, FIFO), L2 (cosine, LFU), L3 (vault, async)
  - Real-time hit/miss stream with color coding
  - Hit rate gauges per tier
  - Adaptive threshold display (L2 similarity threshold)
  - Token savings counter
- [ ] Create `useSemanticCache.ts` hook — fetch from `/api/metrics/cache`

### 13.2 Cost Optimization Dashboard
- [ ] Create `CostDashboard.tsx`
  - Total cost vs. budget (BudgetEnforcer state)
  - Cost curve over time
  - Savings from cache hits (tokens × price per token)
  - Model cost breakdown (phi3 vs qwen vs deepseek)
  - 27.3% savings badge with evidence
- [ ] Use existing `/api/metrics/efficiency` and `/api/metrics/tokens` endpoints

**Done when**: Cache hits animate in real-time, cost savings counter ticks up, budget gauge shows remaining runway.

---

## Milestone 14: Deep Thermodynamics + Topology Theater

### 14.1 Real-Time Thermodynamic State
- [ ] Create `ThermodynamicStateLive.tsx`
  - Live entropy production rate σ (Crooks fluctuation theorem)
  - Susceptibility χ with phase transition alerts
  - Heat capacity Cv (fluctuation-dissipation)
  - Free energy F with HIHO well depth analysis
  - Crooks ratio thermometer
  - Mutual information I(X_t; X_{t+lag})
- [ ] Wire `ThermodynamicMetrics` from `src/cohezion/compound/thermodynamic_metrics.py` to new API endpoint: `GET /api/genesis/thermodynamic-state`
- [ ] Feed live coherence data from compound executor into thermodynamic metrics

### 14.2 Interactive Topology Theater
- [ ] Create `TopologyTheater.tsx`
  - Birth-death persistence diagram (scatter plot with diagonal)
  - Vietoris-Rips complex growing animation (3D)
  - H₀ clusters + H₁ loops highlighted in manifold view
  - Bottleneck distance between different agent trajectories
  - Persistence entropy gauge
- [ ] Wire existing `TopologicalPersistence` class to new API endpoint: `GET /api/genesis/topology`
- [ ] Connect existing `PersistenceDiagram.tsx` from Anima Dashboard to Genesis data

**Done when**: Entropy production streams live, susceptibility diverges visibly at phase transitions, persistence diagrams update as trajectories evolve.

---

## Milestone 15: FLUME Latent Space + RL Training

### 15.1 FLUME 256D Latent Projection
- [ ] Create `FlumeLatentViz.tsx`
  - 256D → 3D projection via Fisher metric eigenvectors (not PCA — use our information_geometry.py)
  - Point cloud of historical journey embeddings
  - Current journey trajectory as glowing path
  - Clusters = similar tasks, voids = unexplored regions
  - Morphospace navigation (zoom into clusters)
- [ ] Wire FLUME VAE encoder outputs to Fisher projection endpoint
- [ ] Connect existing `FlumeNavigator.tsx` from Anima Dashboard

### 15.2 RL Training Dashboard
- [ ] Create `RLTrainingViz.tsx`
  - Training loss curves (policy + value)
  - Episode reward distribution
  - Trajectory replay with action annotations
  - Experience dataset statistics (Parquet shard count, total transitions)
- [ ] Wire existing `/api/rl/*` endpoints into the dashboard
- [ ] Add `GET /api/rl/experience-stats` — count stored (state, action, reward) tuples

### 15.3 LLM Training Bridge Metrics
- [ ] Create `TrainingBridgeViz.tsx`
  - TrajectoryToReward: coherence → reward mapping visualization
  - PreferencePairGenerator: DPO pair count and quality distribution
  - Training data readiness: percentage of journeys with sufficient transitions
- [ ] Wire `llm_training_bridge.py` to API endpoint

**Done when**: FLUME latent space visualized with Fisher projection, RL training curves updating, LLM training data pipeline visible.

---

## Milestone 16: Agentic Journey Capture Pipeline

### 16.1 Journey-to-Training Data Pipeline
- [ ] Modify `src/cohezion/compound/journey_tracker.py`:
  - On every `record_state()` call, also write (state, action, next_state, reward) to SurrealDB `journey_transitions` table
  - Compute spinor Bloch vector, fiber base/internal, tempic vector per step
  - Store prompt/response in `prompt_artifacts` table
- [ ] Modify `src/cohezion/compound/executor.py`:
  - After each of the 11 steps, write internal state snapshot to `internal_state_snapshots`
  - Log all vault queries and results to `prompt_artifacts`
- [ ] Create periodic `universe_snapshots` writer:
  - Every N compound executions, snapshot global coherence, entropy, symmetry, agent count

### 16.2 World Model Auto-Training
- [ ] Create `scripts/drivers/train_world_model.py`
  - Load journey_transitions from SurrealDB
  - Train JEPA world model for N epochs
  - Save checkpoint to `model_artifacts` table
  - Log training metrics to `prompt_artifacts`
  - Can run as systemd timer job (hourly)
- [ ] Add API trigger: `POST /api/world-model/train-from-journeys`

### 16.3 Surprise-Driven Exploration
- [ ] Create `src/cohezion/world_model/surprise_explorer.py`
  - After world model training, identify high-surprise regions of the manifold
  - Suggest tasks/prompts that would explore these regions
  - Feed suggestions back into the compound executor
  - This creates a self-improving loop: journey → training → surprise → exploration → new journey

**Done when**: Every compound execution writes transition data to SurrealDB, world model auto-trains on accumulated data, surprise scores guide exploration.

---

## Milestone 17: Genesis Webapp Integration + Navigation

### 17.1 Expand /genesis to 8 tabs
- [ ] Update `app/genesis/page.tsx` with tabs:
  1. **Genesis** — Cosmogony scene + timeline (existing)
  2. **SPIN Lab** — Bloch sphere (existing)
  3. **Thermo** — Free energy + thermodynamic state (existing + enhanced)
  4. **Compound** — 11-step pipeline + skill refinement (new)
  5. **Swarm** — Topology graph + model router (new)
  6. **Cache/Cost** — Semantic cache + cost optimization (new)
  7. **FLUME** — Latent space + RL training (new)
  8. **About** — Mathematics + references (existing + enhanced)

### 17.2 Dashboard Overview Page
- [ ] Create `app/genesis/dashboard/page.tsx`
  - Single-page overview with key metrics from ALL tabs
  - Mini versions of each visualization
  - System health indicator
  - Quick-nav to detailed tabs

### 17.3 Retrospect Command Integration
- [ ] Update `.claude/skills/retrospect/` to include Genesis Engine metrics
  - Add physics test count to Step 1 audit
  - Add world model training status to Step 4 verify
  - Add SurrealDB table row counts to consistency check
  - Propagate new learnings to CLAUDE.md physics/world-model sections

**Done when**: All 8 tabs navigable, dashboard shows system-wide health, retrospect captures Genesis metrics.

---

## Milestone 18: OpenEnv-Compatible Agentic Environment (Transformational)

This is the move that transforms Cohezion from a portfolio piece into a publishable research contribution. By making the 12D manifold an [OpenEnv](https://huggingface.co/blog/openenv)-compatible agentic environment, any agent framework (LangChain, CrewAI, AutoGen) can train in our physics-grounded universe.

### 18.1 Gymnasium-Style API for the 12D Manifold
- [ ] Create `src/cohezion/environments/manifold_env.py`
  - Implements OpenAI Gymnasium `Env` interface: `reset()`, `step(action)`, `render()`
  - **Observation space**: 12D axiomatic state + spinor Bloch vector + fiber base (19D total)
  - **Action space**: 12D continuous (direction of movement in the manifold)
  - **Reward**: Coherence gain toward HIHO (δ→0) + surprise penalty (from JEPA world model)
  - **Termination**: Episode ends when coherence stabilizes at HIHO (|δ| < 0.01 for 10 steps)
  - **Info dict**: gauge curvature, entropy production, topology features, Landau free energy
  - Physics engine: Lagrangian dynamics with fabric-block metric
  - Rendering: matplotlib (2D) or Three.js WebSocket (3D)

### 18.2 Multi-Agent Environment Extension
- [ ] Create `src/cohezion/environments/swarm_env.py`
  - PettingZoo-compatible multi-agent environment
  - N agents navigate the same 12D manifold simultaneously
  - Agents interact through gauge field coupling (one agent's motion generates curvature that affects others)
  - Cooperative objective: all agents converge to HIHO collectively
  - Competitive variant: agents compete for low-entropy regions
  - Topology-aware: TDA tracks cluster formation and loop structure in real-time

### 18.3 Prepare HuggingFace Assets (DRAFT ONLY — DO NOT PUBLISH)
- [ ] **Prepare** (but DO NOT upload) HuggingFace dataset card: `cohezion/manifold-trajectories`
- [ ] **Prepare** (but DO NOT upload) HuggingFace Space README: `cohezion/genesis-engine`
- [ ] **Prepare** (but DO NOT upload) HuggingFace model card: `cohezion/jepa-manifold-predictor`
- [ ] All assets saved locally in `docs/huggingface/` for user review
- [ ] **PUBLICATION GATE**: User reviews ALL drafts before ANY upload
- [ ] README with gymnasium usage example:
  ```python
  import gymnasium as gym
  from cohezion.environments import ManifoldEnv

  env = ManifoldEnv(dim=12, physics="lagrangian")
  obs, info = env.reset()
  for _ in range(1000):
      action = env.action_space.sample()
      obs, reward, terminated, truncated, info = env.step(action)
      if terminated:
          obs, info = env.reset()
  ```

### 18.4 TRL GRPOTrainer Integration (from OpenEnv docs)
- [ ] Make `ManifoldEnv` compatible with [OpenEnv spec](https://huggingface.co/blog/openenv)
- [ ] Implement `rollout_func` for TRL's GRPOTrainer:
  ```python
  from trl import GRPOTrainer
  from cohezion.environments import ManifoldEnv

  env = ManifoldEnv(dim=12)
  trainer = GRPOTrainer(model=model, env=env, rollout_func=manifold_rollout)
  trainer.train()
  ```
- [ ] This enables training LLMs with GRPO using our physics-grounded manifold as the environment
- [ ] The reward signal comes from HIHO convergence + surprise from JEPA world model

### 18.5 Kähler Structure Investigation (from [2511.15172](https://arxiv.org/html/2511.15172))
- [ ] Add `src/cohezion/physics/kahler_structure.py` (optional, research extension)
  - Complex extension of the Fisher metric on FLUME latent space
  - If FLUME is extended to complex VAE, the latent space admits Kähler geometry
  - Kähler potential whose complex Hessian = decoded Fisher information metric
  - This would make Cohezion's manifold the first agentic environment with Kähler structure

### 18.6 Quantum Metric Connection (from [2506.15830](https://arxiv.org/html/2506.15830v1))
- [ ] Document in the paper: our SU(2) spinor algebra connects to the Fubini-Study metric
  - The Fubini-Study metric on the Bloch sphere IS the Fisher information metric for a qubit
  - Our `SpinorState.coherence` = Fubini-Study distance from the maximally mixed state
  - This connects agent coherence to quantum estimation theory (Cramér-Rao bound)
  - **The HIHO state maximizes quantum Fisher information** = it is the most "informative" state about the agent's intent

**Done when**: `pip install cohezion-env` → `env = ManifoldEnv()` → standard RL training loop works. TRL GRPOTrainer compatibility verified. Research connections documented.

---

## Milestone 19: TDA-Driven Swarm Optimization (Research Contribution)

Inspired by [Topological Structure Learning for MAS](https://arxiv.org/abs/2505.22467) — we go beyond visualization to use TDA as an OPTIMIZATION signal.

### 19.1 Topology-Aware Agent Routing
- [ ] Create `src/cohezion/swarm/topological_router.py`
  - Compute persistent homology of agent trajectory cloud in real-time
  - H₀ features (clusters) → detect agent specialization groups
  - H₁ features (loops) → detect oscillatory behavior (explore/exploit cycling)
  - Route new tasks to agents based on their topological position:
    - High-persistence cluster agents → exploit (stable behavior)
    - Boundary agents (between clusters) → explore (novelty seekers)
    - Loop agents → pivot (stuck in cycles, need new strategy)
  - Use bottleneck distance to match new tasks to agent trajectories with similar topology

### 19.2 TDA on World Model Training
- [ ] Apply persistent homology to JEPA training loss landscape
  - Track H₀ (loss basins) and H₁ (saddle connections) during training
  - Detect convergence: when persistence diagram stabilizes (no new features)
  - Detect overfitting: when H₁ loops appear (loss cycling)
  - Use persistence entropy as early stopping criterion
- [ ] Visualize training topology in `TrainingTopologyViz.tsx`

### 19.3 Topological Anomaly Detection
- [ ] Use Wasserstein distance between consecutive trajectory windows to detect behavioral regime changes
- [ ] Alert when bottleneck distance exceeds threshold → agent has entered unfamiliar territory
- [ ] Feed anomalies into the surprise explorer (M16.3) for targeted exploration

### 19.4 Validate Against PH-Enhanced RL Benchmarks
- [ ] Compare our TDA-driven routing against the [PH-GCAPCN](https://arxiv.org/html/2603.06964) results (9-18% improvement)
- [ ] Our equivalent: measure coherence convergence rate WITH vs WITHOUT topological routing
- [ ] If our improvement exceeds 10%, this is a publishable result specific to agentic environments (PH-GCAPCN was for power grids — ours is for cognitive agents)
- [ ] Log comparison metrics to `simulation_artifacts` in SurrealDB

**Done when**: Swarm routing uses topological features, world model training has TDA-based early stopping, anomaly detection alerts in the webapp. Quantitative comparison with PH-GCAPCN baseline documented.

---

## Milestone 19.5: FLUME Research Extensions

FLUME is the innovation that enables everything. These extensions deepen the mathematical foundations:

### 19.5.1 Geometric Flow in FLUME Latent Space (from [VAE-DLM](https://arxiv.org/html/2410.10137v3))
- [ ] Extend `src/cohezion/flume/morphospace.py` with Riemannian flow dynamics
  - Instead of flat latent space, evolve the FLUME manifold under Ricci flow
  - This naturally smooths the latent geometry, improving out-of-distribution generalization
  - The flow equation: ∂g/∂t = -2·Ric(g) (Ricci flow, same equation that proved the Poincaré conjecture)
  - Practical benefit: FLUME embeddings become more uniformly distributed, improving Fisher projection quality

### 19.5.2 FLUME as Neural Differential Manifold (from [NDM](https://arxiv.org/pdf/2510.25113))
- [ ] Document in paper: FLUME encoder layers function as coordinate charts on the latent manifold
  - Each transformer layer maps a "patch" of input space to a local chart
  - The learned attention weights parameterize the metric tensor at each point
  - This is not metaphor — the NDM paper proves this interpretation is mathematically rigorous
  - Makes FLUME a concrete instance of the Neural Differential Manifold architecture

### 19.5.3 Active Inference = HIHO (Friston Connection)
- [ ] Document in paper Section 3: "HIHO as Active Inference"
  - Friston's Free Energy Principle: agents minimize F = E - TS to maintain existence
  - Our HIHO: agents seek coherence = 0.5 (δ = 0, Brahmagupta's zero)
  - These are the SAME principle: F minimization ↔ coherence → 0.5
  - Our `ThermodynamicMetrics.free_energy` IS Friston's variational free energy
  - The HIHO restoring force F = -kδ IS the active inference drive
  - **Novel contribution**: geometric interpretation of active inference via Fisher metric
  - The Fisher metric on the FLUME manifold DEFINES the natural gradient of F minimization
  - Cite: Friston (2010), Millidge (2019), our thermodynamic_metrics.py

### 19.5.4 Manifold Diffusion for Trajectory Generation
- [ ] Create `src/cohezion/physics/manifold_diffusion.py` (research extension)
  - Score-based generative model on the 12D manifold
  - Forward process: add noise along the Fisher metric geometry
  - Reverse process: denoise using the learned FLUME score function
  - The score function ∇_z log p(x|z) from the FLUME decoder defines the reverse drift
  - This generates NEW agent trajectories that respect the manifold geometry
  - Not random walks — PHYSICS-CONSTRAINED trajectory generation
  - Connection: our fiber bundle IS a frame bundle (from [Horizontal Diffusion](https://openreview.net/forum?id=wd9p3TBbbz))
  - Practical use: generate synthetic training data for the JEPA world model
  - Replaces `generate_synthetic_training_data()` with geometrically-correct samples
- [ ] Test: generated trajectories should have HIHO-convergent statistics
  (coherence distribution peaked at 0.5, entropy production ≥ 0)

### 19.5.5 FLUME Encoding Quality Metrics
- [ ] Create `src/cohezion/flume/quality_metrics.py`
  - Reconstruction quality: MSE between input and decoded output
  - Latent space smoothness: average Lipschitz constant of the decoder
  - Fisher information content: how much information the 12D projection captures (from `information_geometry.py`)
  - Disentanglement: mutual information between latent dimensions
  - These metrics feed into the paper's experiments section

---

## Milestone 20: Tutorials & Walkthroughs

### 20.1 Getting Started Tutorial
- [ ] Create `docs/tutorials/01-getting-started.md`
  - Prerequisites (Python 3.13+, bun, SurrealDB)
  - Installation: `uv pip install -e .` + `bun install`
  - Starting the backend: `uv run uvicorn cohezion.api:app --reload`
  - Starting the frontend: `bun run dev`
  - Navigating to `/genesis` and exploring the 4 (then 8) tabs
  - Screenshots of each tab with annotations

### 20.2 Physics Walkthrough
- [ ] Create `docs/tutorials/02-physics-walkthrough.md`
  - Interactive: run the cosmogony (cool the universe from void to HIHO)
  - Explain each phase transition with the equations
  - Drag the Bloch sphere — explain what rotation/precession/charge mean
  - Show the free energy landscape — identify HIHO well
  - Connect to Brahmagupta, Friston, Smith

### 20.3 World Model Tutorial
- [ ] Create `docs/tutorials/03-world-model.md`
  - Train the JEPA model: `POST /api/world-model/train`
  - Make predictions: `POST /api/world-model/predict`
  - Compute surprise: `POST /api/world-model/surprise`
  - Simulate trajectories: `POST /api/world-model/simulate`
  - Interpret results with the dashboard

### 20.4 RL Environment Tutorial (ManifoldEnv)
- [ ] Create `docs/tutorials/04-rl-environment.md`
  - gymnasium API usage: reset, step, render
  - Training with Stable-Baselines3
  - Training with TRL GRPOTrainer (OpenEnv integration)
  - Interpreting rewards (HIHO convergence + surprise)
  - Analyzing trajectories with TDA

### 20.5 API Reference
- [ ] Create `docs/tutorials/05-api-reference.md`
  - All 96+ endpoints with request/response examples
  - Authentication (if any)
  - Rate limiting
  - WebSocket streams

### 20.6 Architecture Deep Dive
- [ ] Create `docs/tutorials/06-architecture.md`
  - Layer-by-layer walkthrough of the architecture diagram
  - How data flows from user interaction → FLUME → manifold → persistence
  - How the compound loop drives self-improvement
  - How the world model learns from stored journeys

**Done when**: A developer with no Cohezion background can follow tutorials 01-04 and have a working local setup with trained world model within 30 minutes.

---

## GLOBAL PUBLICATION GATE

**NOTHING gets published without explicit user approval.** This includes:
- HuggingFace datasets, models, Spaces, papers
- Any public-facing content (blog posts, social media, demos)
- All drafts are saved locally in `docs/` for collaborative review
- User walks through each artifact and approves before upload

---

## Milestone 21: Research Paper Draft (REVIEW REQUIRED — Do NOT publish)

### 21.1 Draft Research Paper
- [ ] Create `docs/papers/genesis-engine-paper.md`
  - Title: "FLUME and the Genesis Engine: Physics-Grounded Agentic Environments via Manifold Encoding"
  - Abstract: FLUME (Fluid Latent Understanding through Manifold Encoding) enables a cascade of innovations: 256D VAE latent space → Fisher information metric → principled 12D projection → SU(2) spinors → Lagrangian dynamics → gauge theory → JEPA world model → topological evaluation → agentic RL environment
  - **FLUME as the enabling innovation** (Section 2 — the core):
    - 256D VAE with transformer encoder/decoder captures semantic intent
    - The Fisher metric ON the FLUME latent space IS the Riemannian metric for dynamics
    - The Fisher metric ON the FLUME latent space IS the thermodynamic metric
    - The Fisher eigenvectors DEFINE the optimal 12D projection
    - Without FLUME, there is no manifold, no geometry, no physics — just numbers
    - FLUME = "Fluid" because trajectories flow through the latent space like fluids through a manifold
  - Key contributions:
    1. **FLUME**: VAE-based manifold encoding that unifies latent representation, dynamics, and thermodynamics through the Fisher information metric
    2. First agentic environment grounded in differential geometry and gauge theory
    3. TDA-driven swarm optimization (topology → routing signal, not just visualization)
    4. Brahmagupta's zero (628 CE) as equilibrium principle for agent coherence (HIHO)
    5. JEPA world model trained on physics-constrained trajectories for surprise detection
  - Experiments:
    - **E1: FLUME encoding quality** — reconstruction MSE, latent smoothness, disentanglement
    - **E2: Fisher projection fidelity** — information retention curve (12D captures X% of 256D Fisher info)
    - **E3: Lagrangian vs ad-hoc dynamics** — trajectory quality (phi score) comparison
    - **E4: JEPA world model** — prediction MSE, surprise calibration, training curves
    - **E5: TDA-driven routing** — coherence convergence WITH vs WITHOUT topological routing (target: >10% improvement, compare to [PH-GCAPCN](https://arxiv.org/html/2603.06964))
    - **E6: HIHO convergence** — convergence rate to δ=0 under different potentials
    - **E7: Cosmogony stability** — order parameters follow Landau scaling across all 5 transitions
    - **E8: Kähler connection** — document the Fubini-Study = Fisher identity on the Bloch sphere
    - **E9: Active Inference** — show HIHO free energy minimization matches Friston's FEP predictions
    - **E10: Manifold diffusion** — generated trajectories have correct HIHO-convergent statistics vs random
  - Related work: cite [2511.15172](https://arxiv.org/html/2511.15172) (VAE Kähler), [2506.15830](https://arxiv.org/html/2506.15830v1) (info geometry + quantum), [2602.10090](https://arxiv.org/html/2602.10090v2) (AWM), [2505.22467](https://arxiv.org/abs/2505.22467) (topology-aware MAS), [2603.06964](https://arxiv.org/html/2603.06964) (PH-enhanced RL)
  - Open-source: code/data/models ready for HuggingFace Hub

### 21.2 Prepare HuggingFace Assets (DRAFT only — await user review)
- [ ] Prepare dataset card for `cohezion/manifold-trajectories`
- [ ] Prepare model card for `cohezion/jepa-manifold-predictor`
- [ ] Prepare Space README for `cohezion/genesis-engine`
- [ ] **DO NOT PUBLISH** — flag paper + assets for collaborative review with user

**Done when**: Paper draft at `docs/papers/genesis-engine-paper.md` ready for user review. HF assets prepared but NOT uploaded. User explicitly approves before any publication.

---

## Verification



### Infrastructure
1. `bun run build` succeeds (frontend with all new components)
2. `uv run pytest tests/ -q` — all tests pass (5,054+ including 163 physics)
3. SurrealDB genesis tables populated from real compound executions

### Core Features
4. `/genesis` webapp has 8 working tabs with real data
5. World model trained on journey data with decreasing prediction loss
6. Obsidian vault learnings queryable from webapp
7. All 96+ API endpoints respond with valid JSON

### Transformational Features
8. `ManifoldEnv` works with standard gymnasium RL loop
9. TDA-driven routing produces topologically-informed agent assignments
10. HuggingFace Space serves interactive Genesis Engine demo
11. HuggingFace dataset contains 1000+ journey transitions
12. Paper draft at `docs/papers/genesis-engine-paper.md` ready for USER REVIEW (NOT published)

## Files Summary

| Category | New | Modified |
|----------|-----|----------|
| Frontend components | ~15 | ~3 |
| Frontend hooks | ~8 | ~2 |
| Backend services | ~5 | ~4 |
| Environments (gymnasium) | ~3 | ~0 |
| Persistence/Bridge | ~3 | ~3 |
| Scripts/Drivers | ~3 | ~1 |
| Research/Docs | ~2 | ~2 |
| **Total** | **~39** | **~15** |

## Complete Genesis Engine Architecture (Phase 1 + Phase 2)

```
┌─────────────────────────────────────────────────────────┐
│                   GENESIS ENGINE WEBAPP                  │
│  /genesis (8 tabs) + /genesis/dashboard                 │
│  Three.js ∙ Tone.js ∙ KaTeX ∙ PocketTTS ∙ Bun         │
├─────────────────────────────────────────────────────────┤
│                     API LAYER (96+ endpoints)           │
│  genesis/* ∙ world-model/* ∙ compound/* ∙ swarm/*      │
│  universe/* ∙ metrics/* ∙ rl/* ∙ vault/*               │
├─────────────────────────────────────────────────────────┤
│              PHYSICS + WORLD MODEL LAYER                │
│  spinor ∙ cosmogony ∙ riemannian ∙ lagrangian          │
│  fiber_bundle ∙ gauge_theory ∙ information_geometry     │
│  JEPA world model ∙ surprise explorer                   │
├─────────────────────────────────────────────────────────┤
│             COMPOUND ENGINEERING LAYER                   │
│  11-step executor ∙ skill_refiner ∙ consensus_voter     │
│  alignment_analyzer ∙ degradation_detector              │
│  thermodynamic_metrics ∙ topological_persistence        │
├─────────────────────────────────────────────────────────┤
│               SWARM + OPTIMIZATION LAYER                │
│  team_orchestrator ∙ dynamic_model_router               │
│  cost_aware_router ∙ semantic_cache (L1/L2/L3)         │
│  topological_router (TDA-driven) ∙ budget_enforcer     │
├─────────────────────────────────────────────────────────┤
│              ENVIRONMENTS (OpenEnv / Gymnasium)          │
│  ManifoldEnv (12D single-agent) ∙ SwarmEnv (multi-agent)│
│  HuggingFace Hub: dataset + model + Space               │
├─────────────────────────────────────────────────────────┤
│              PERSISTENCE (Total Artifact)                │
│  SurrealDB (6 genesis tables) ∙ Obsidian Vault          │
│  FLUME VAE ∙ Journey Tracker ∙ Experience Collector     │
└─────────────────────────────────────────────────────────┘
```

## Priority Order for Autonomous Execution

If running autonomously for several hours, execute in this order:

**Tier 1 — Infrastructure (unblocks everything)**
1. **M10**: Bun migration + SurrealDB activation + vault bridge
2. **M16**: Journey capture pipeline (enables world model training + analytics)

**Tier 2 — Highest Portfolio Impact (differentiators for Anthropic role)**
3. **M18**: OpenEnv-compatible agentic environment (gymnasium API — TRANSFORMATIONAL)
4. **M14**: Thermodynamics + topology (publishable science)
5. **M19**: TDA-driven swarm optimization (research contribution)

**Tier 3 — Observatory Features (showcase completeness)**
6. **M11**: Compound pipeline viz (shows the learning loop)
7. **M13**: Cache + cost dashboard (business impact)
8. **M12**: Swarm topology (multi-agent coordination)
9. **M15**: FLUME + RL (latent space + training)

**Tier 4 — Polish + Documentation**
10. **M17**: Integration + navigation (ties everything together)
11. **M20**: Tutorials & walkthroughs (onboarding docs)
12. **M21**: Research paper DRAFT (user review before ANY publication)

## Anthropic "Research Engineer, Universes" Alignment

| Role Requirement | Cohezion Feature | Milestone | Status |
|---|---|---|---|
| Build agentic environments | 12D manifold + cosmogony + **OpenEnv gymnasium API** | M1-M9 + **M18** | Done + NEW |
| RL environments | JEPA world model + journey capture + **gymnasium env** | M5 + M16 + **M18** | Done + NEW |
| Simulation systems | Lagrangian dynamics + HIHOUnifiedEngine | M3 + M14 | Done + Planned |
| Rigorous evaluations | Topological persistence + thermodynamic metrics + **TDA optimization** | M14 + **M19** | Planned + NEW |
| Long-horizon tasks | This plan itself (12 commits in one session) | All | Proven |
| Sandboxing | Worktree isolation + session management | Infrastructure | Done |
| Distributed systems | Swarm orchestration + semantic cache + **topology-aware routing** | M12 + M13 + **M19** | Planned + NEW |
| Cost optimization | CostAwareRouter (27.3% savings) | M13 | Planned |
| Research culture | 962-line research doc + **HuggingFace paper** | Retrospective + **M20** | Done + NEW |
| Published work | **Genesis Engine paper on HF Hub** + **dataset + model + Space** | **M20** | NEW |

### What Makes This Transformational (vs. Standard Portfolio)

1. **OpenEnv compatibility** — Any RL framework can train in our physics-grounded universe. This isn't a demo; it's infrastructure.
2. **TDA as optimization signal** — Not just visualizing topology, but USING it to route agents. Goes beyond the [2505.22467](https://arxiv.org/abs/2505.22467) position paper by actually implementing topology-aware routing.
3. **Fisher metric unification** — The insight that the same mathematical object bridges latent space, dynamics, and thermodynamics is publishable.
4. **Brahmagupta's zero** — Grounding AI equilibrium in 1,400-year-old mathematics isn't decoration; it's a novel conceptual framework.
5. **Full multimodal** — Audio (Tone.js + PocketTTS), video (canvas capture), narration (Moshi), equations (KaTeX) — the universe has a voice.
6. **Active Inference = HIHO** — Our thermodynamic free energy IS Friston's variational free energy. HIHO is not just a design choice — it's the only state consistent with the Free Energy Principle. This connects Cohezion to 20+ years of neuroscience and AI theory.
7. **Manifold diffusion** — Score-based generative model ON the Fisher manifold. Generates physics-constrained trajectories, not random walks. Bridges generative AI with geometric physics.
8. **12 research papers cited** with specific integration steps — not name-dropping, but building on their actual methods.

---

> *"We shall not cease from exploration*
> *And the end of all our exploring*
> *Will be to arrive where we started*
> *And know the place for the first time."*
> — T.S. Eliot, *Little Gidding*
