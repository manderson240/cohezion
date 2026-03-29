# Interview Preparation: Research Engineer, Universes

---

## Code Walkthrough Outline (15 minutes)

### Setup (1 min)
- Open the repo. Point to the directory structure: `src/cohezion/environments/`, `src/cohezion/physics/`, `src/cohezion/rl/`, `src/cohezion/universe/`, `src/cohezion/eval/`.
- "This is Cohezion, a physics-grounded agentic training environment. I will walk through three components: the RL environment, the reward shaping, and the evaluation metrics."

### ManifoldEnv (5 min)
- **File**: `src/cohezion/environments/manifold_env.py`
- Show the class definition: Gymnasium `gym.Env` subclass, registered as `Cohezion/ManifoldEnv-v0`.
- **Observation space** (line 123): 19D = 12D state + 3D Bloch vector + 4D fiber base. Explain why the observation is larger than the state: the Bloch vector and fiber base provide the agent with derived physics quantities that would be expensive to compute from raw state.
- **Action space** (line 126): 12D continuous velocity vector. The agent applies force in the manifold, not teleportation.
- **Step function** (line 185): Walk through the physics pipeline: action as velocity perturbation -> Stormer-Verlet integration via `LagrangianDynamics` -> position clamping -> reward computation.
- **Key design decision**: The dynamics engine is selectable (Lagrangian or Hamiltonian). Lagrangian is default because it naturally handles constraints via the metric; Hamiltonian is available for symplectic analysis.
- Show `gym.register()` at line 315 -- standard Gymnasium registration.

### Reward Shaping (4 min)
- **File**: `src/cohezion/environments/manifold_env.py`, `_compute_reward` (line 290)
- Three components: coherence gain (delta toward HIHO 0.5), energy efficiency (lower potential = better), HIHO bonus (threshold bonus at convergence).
- **File**: `src/cohezion/universe/llm_training_bridge.py`
- Show `TrajectoryToReward` (line 113): how the same coherence signal is converted to RLHF scalar rewards. Show `PreferencePairGenerator`: how trajectory pairs are compared by HIHO proximity to generate DPO training data.
- **File**: `src/cohezion/rl/ppo_trainer.py`
- Show `TRIUNEPolicy` (line 40): the 3-tier Knower/Thinker/Doer hierarchy. Explain that the hierarchy separates abstraction levels so the policy can be partially frozen during fine-tuning (e.g., freeze Knower, train Doer).

### Evaluation Metrics (4 min)
- **File**: `src/cohezion/benchmarks/agentic_metrics.py`
- Show `AgenticMetrics` class: 6 metrics with bootstrap CIs, Mann-Whitney U, Bonferroni correction.
- **File**: `src/cohezion/eval/capability_scorecard.py`
- Show `CapabilityScorecard`: 6-axis radar chart, longitudinal tracking, swarm-vs-self-supervised comparison.
- **Key point**: metrics are derived from the environment physics, not invented separately. Coherence Amplitude measures the peak of what the environment is designed to optimize. Recovery Basin Radius measures resilience to the perturbations the environment generates.

### Closing (1 min)
- "The full pipeline: ManifoldEnv generates trajectories -> TrajectoryToReward/PreferencePairGenerator converts to training signals -> AgenticMetrics evaluates capability -> CapabilityScorecard tracks progress. 5,919 tests cover the stack."

---

## Technical Questions: Prepared Answers

### "Why 12 dimensions?"

Each dimension maps to a distinct agentic capability, grouped into 4 fabrics of 3:

- **Space** (0-2): Navigation, positioning, spatial reasoning.
- **Field** (3-5): Temporal awareness, environmental sensing, biological adaptation. These are the sensing channels.
- **Control** (6-8): Logic (classical reasoning), quantum (probabilistic reasoning), field control (meta-control). These are the decision channels.
- **Precipitation** (9-11): Awareness of output, novelty detection, actual output generation. These are the production channels.

The 4x3 structure is not arbitrary. It comes from Smith's 12-parameter model (1962), but gains computational content through the fiber bundle: the base space B^4 = (||Space||, ||Field||, ||Control||, ||Precip||) captures macroscopic state, while the fiber captures internal configuration. This gives a natural curriculum: you can train on base-space navigation first (4D problem), then fine-tune on full 12D dynamics.

The alternative -- flat high-dimensional spaces -- loses this structure. A 256D space has no natural decomposition into capability axes. The 12D manifold is low enough to be interpretable and high enough to represent the capabilities we want to train.

### "How does this scale?"

Three axes of scaling:

1. **More agents**: SwarmEnv scales to N agents via the gauge coupling mechanism. Each agent adds O(D) computation per step (the mean field update). For N > ~16, you would switch from shared-memory to Ray/SubprocVecEnv for parallel physics simulation. The PettingZoo-compatible API makes this a configuration change, not an architecture change.

2. **More complex tasks**: The 5 task archetypes x 4 difficulty levels provide a natural curriculum. Adding new archetypes means defining a new TaskSpec (target well, horizon, noise level, interruption points). The evaluation metrics generalize automatically because they are defined on the trajectory, not on the task.

3. **More environments per training run**: Gymnasium's VectorEnv API (AsyncVectorEnv, SyncVectorEnv) handles parallel environment instances natively. The physics engine is stateless between steps (pure function of position + velocity + action), so environments do not interfere.

The constraint is the physics engine: Stormer-Verlet integration is O(D^2) per step (metric tensor multiplication). For D=12, this is negligible. For D=2048 (the full FLUME space), you would need batched GPU computation. The Fisher projection to 12D exists precisely to make the dynamics tractable while preserving the information content.

### "Design an environment for interruption handling."

This is FLUME archetype #3, Interruption Recovery. Here is how I implemented it:

**Setup**: ManifoldEnv with `interruption_points` in the TaskSpec (e.g., steps [100, 200] in a 300-step episode).

**Mechanism**: At each interruption point:
1. Save the agent's current state (position, velocity, coherence, SPIN alignment).
2. Inject noise into the SPIN dimensions (dims 6-8): multiply by a random rotation matrix with angle drawn from Uniform(0, pi/4). This breaks coherence without destroying positional information.
3. Resume the episode. The agent must recover SPIN coherence while maintaining positional progress.

**Reward**: The standard HIHO reward, plus a recovery bonus proportional to 1/(steps_to_recover). Fast recovery is better.

**Evaluation**: Recovery Basin Radius measures the maximum perturbation angle the agent can recover from. Phase Locking Rate measures how quickly SPIN alignment is restored post-interruption.

**Curriculum**: Difficulty levels control the perturbation magnitude (level 1: pi/8, level 4: pi/2) and the number of interruptions (1 to 4 per episode). Level 4 also adds context drift: the TRIUNE balance weights shift at each interruption, testing whether the agent can adapt its strategy.

**Extension for the Universes team**: Replace SPIN perturbation with context window truncation or tool availability changes, depending on what you are training. The evaluation metrics (Recovery Basin Radius, Phase Locking Rate) generalize to any interruption type as long as you define a coherence measure.

### "How do you generate training data from environment runs?"

The LLM Training Bridge (`src/cohezion/universe/llm_training_bridge.py`) converts trajectories into three formats:

1. **RLHF rewards**: `TrajectoryToReward` maps each trajectory to a scalar. The reward combines HIHO proximity (primary), SPIN alignment bonus, tempic stability (low rate-of-change), and precipitation bonus (did the agent produce output). This scalar is the reward signal for PPO/REINFORCE.

2. **DPO preference pairs**: `PreferencePairGenerator` takes pairs of trajectories on the same task and compares their HIHO-alignment scores. The trajectory with higher alignment is "chosen", the other is "rejected". The margin (score difference) is preserved for weighted DPO. This does not require human labeling -- the physics provides the preference ordering.

3. **Judgment assessments**: `JudgmentEvaluator` examines decision points within a trajectory (where the agent chose between multiple valid actions) and scores whether the chosen action was HIHO-optimal. This produces (context, decision, optimal_decision, alignment_score) tuples for fine-tuning judgment quality.

The `JourneyToTrainingBridge` handles the format conversion from JourneyTracker's native format (journey points with 12D coordinates) to `AgentTrajectory` (steps with state/action/reward), then calls `ExperienceDataset.export_all()` to write training-ready files.

---

## Behavioral Questions: Prepared Answers

### "Tell me about a time you dealt with uncertainty." (AMD kernel ceiling, K-Search pivot)

During the Luma AMD Speedrun, I hit a ceiling after three iterations of the GEMM kernel. Each iteration improved throughput by less than 5%, and the gap to the leaderboard was still over 2x. The kernel parameters were already near-optimal for the MI355X wavefront configuration.

I stopped tuning. The evidence said the algorithm was at a local optimum, not that I needed better parameters. I generated three fundamentally different approaches: (1) cooperative tiling with LDS (shared memory), (2) K-Search -- a systematic exploration of tile sizes, vector widths, and unroll factors across the parameter space, (3) fused MoE+GEMM to eliminate memory roundtrips.

I chose K-Search because it was systematic (guaranteed to find the global optimum within the search space) and because it would produce knowledge reusable for the MoE and MLA kernels. The key insight was that the MI355X has different performance characteristics than the MI300X that most published techniques target -- you have to search, not copy.

### "Give an example of impact-driven work." (VLIW 423x)

The Anthropic VLIW Challenge result (423x speedup, 349 cycles, bit-exact) was not the product of a clever trick. It was the product of systematic debugging applied to an optimization problem. I started by instrumenting the cycle budget: which operations consumed cycles, which were data-dependent, which could be reordered. I built a cycle-accurate simulation (`src/cohezion/flume/vliw_kernel_sim.py`) to test reorderings without running on hardware. Then I applied the standard debugging loop: reproduce, hypothesize, test one change, verify.

The 423x number was a side effect of not stopping early. Most competitors found 10-50x improvements and stopped. I kept instrumenting because the cycle budget said there was more room. The compound engineering loop (execute -> retrospect -> refine -> execute again) is the same methodology I use for everything in Cohezion.

### "Demonstrate high agency." (Cohezion: 2,684 commits solo)

Cohezion is 2,684 commits, 5,919 tests, a physics engine, three RL environments, a training pipeline, and a research paper. All built by one person on consumer hardware (AMD Ryzen AI MAX+ 395, 128GB RAM, integrated GPU).

The constraints forced creative solutions. No CUDA meant I could not use standard GPU RL training pipelines -- I built CPU-trainable architectures (JEPA at 86K params, TRIUNE policy with efficient dimensionality). No cloud budget meant aggressive cost optimization -- the CostAwareRouter saves 27.3% by routing queries to the cheapest model that can handle the complexity. The SemanticCache (95%+ hit rate) eliminates redundant computation.

I extracted 160+ learnings into a vault system that compounds knowledge across sessions. This is not documentation -- it is a queryable knowledge base that the executor consults before every task, producing 87-98% token savings via template reuse.

---

## Questions for Anthropic

### 1. Environment complexity vs. training signal quality

"How does the Universes team think about the tradeoff between environment complexity and training signal quality? Specifically: when you add more realistic features to an environment (interruptions, tool failures, ambiguous instructions), does the reward signal get noisier, and how do you handle that? In Cohezion, I use the Fisher metric to derive reward signals from the same object that defines the dynamics, which keeps the signal grounded in the environment physics. Does your team have an analogous principle, or is reward engineering mostly empirical?"

### 2. Evaluation metrics and benchmark gaming

"What is the team's approach to evaluation metrics that capture genuine capability versus benchmark gaming? One thing I have found is that scalar metrics invite Goodhart's Law: the agent optimizes the metric, not the capability. My approach is the 6-axis CapabilityScorecard with statistical rigor (bootstrap CIs, Bonferroni correction) to make gaming harder. But I am curious whether you have seen cases where multi-axis evaluation still gets gamed, and what the next line of defense is."

### 3. Environment fidelity vs. training efficiency

"How do you handle the tension between environment fidelity and training efficiency? Full-fidelity environments (realistic tool APIs, actual network latency, real file systems) are expensive to run at training scale. Low-fidelity environments train faster but may not transfer. In Cohezion, the 256D-to-12D Fisher projection is my answer: train on the 12D compressed manifold (cheap), then validate on the full 256D space (expensive but infrequent). Does your team use a similar compression strategy, or do you prefer full-fidelity environments with engineering tricks to make them fast?"

---

## Logistics

### Materials to bring / have ready
- Laptop with repo checked out and environments runnable
- Paper (`docs/papers/genesis-engine-paper.md`) printed or on screen
- ManifoldEnv demo: `python -c "from cohezion.environments import ManifoldEnv; env = ManifoldEnv(); obs, info = env.reset(); print(f'Obs shape: {obs.shape}, Coherence: {info[\"coherence\"]:.3f}')"` ready to run

### Key numbers to know from memory
- 12D manifold, 19D observation, 12D action space
- 5 task archetypes, 4 difficulty levels, 20 TaskSpecs
- 6 evaluation metrics with bootstrap CIs and Mann-Whitney U
- JEPA: ~86K params, 12D state -> 64D embedding
- TRIUNE: 256D -> 2048D -> 512D -> 12D (Knower/Thinker/Doer)
- FLUME VAE: 256D latent, 4 heads, 2 layers
- 5,919 tests, 2,684 commits
- 423x VLIW speedup, 36-qubit quantum (SNR 9,947 sigma)
- 27.3% cost reduction (CostAwareRouter), 95%+ cache hit rate
- Fisher metric: 4 simultaneous roles (geometry, dynamics, thermodynamics, projection)

### Potential weak spots to prepare for
- **"Where are the quantitative results?"** The evaluation framework is built but E1-E10 benchmarks are in progress. Be direct about this. The framework is the contribution, not the numbers. The numbers will come from running the framework at scale.
- **"This is complex. Does the complexity help?"** Be ready to argue that the physics is not decorative. The Fisher metric unification eliminates an entire class of engineering decisions (how to define the metric, the reward, the projection, the dynamics). Complexity in the math reduces complexity in the engineering.
- **"Have you worked on a team?"** Cohezion is solo work. Address this head-on: the compound engineering loop with multi-agent consensus (QuadratureNexus, SkillConsensusVoter) was designed as a team-of-agents precisely because there was no human team. In a real team, the architecture would be simpler because the consensus mechanism would be human discussion rather than automated voting.
