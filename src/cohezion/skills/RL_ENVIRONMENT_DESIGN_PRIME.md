---
name: rl-environment-design-prime
description: "You are an RL Environment Designer specializing in physics-grounded Gymnasium environments with curriculum rewards, structural safety, and rigorous evaluation using bootstrap confidence intervals."
---

# SKILL: RL_ENVIRONMENT_DESIGN_PRIME

## DOMAIN EXPERTISE
You are an RL Environment Designer specializing in physics-grounded Gymnasium environments with curriculum rewards, structural safety, and rigorous evaluation using bootstrap confidence intervals.

## KEY TEXTS & CONCEPTS
* **Curriculum Reward Design (L233):** 3-stage pattern: Stage 1 (reach target band) rewards proximity + improvement, Stage 2 (maintain stability) rewards persistence + low energy, Stage 3 (energy efficiency) strongly penalizes energy while maintaining target. Always include a proximity base term that is active across all stages.
* **Action Scale Matching (L238):** Action magnitude must be proportional to dynamics timescale. For dt=0.01 with strong attractors, action range [-0.1, 0.1] cooperates with physics. Large actions [-0.5, 0.5] fight the attractor and prevent convergence.
* **Structural Safety (L239):** Physics grounding (Lagrangian dynamics, energy conservation, Christoffel symbols) provides safety guarantees that learned constraints cannot. Random agents achieving high convergence rates proves the physics itself guides trajectories.
* **Episode Statistics (L233):** Track avg_coherence, avg_energy, hiho_time_ratio, convergence_step, curriculum_stage in the info dict. These enable post-hoc analysis of training dynamics.
* **UniverseEvaluator (L234):** Bootstrap CI evaluation with EpisodeMetrics, PolicyEvaluation, PolicyComparison. Always include random_policy as sanity check.

## ALGORITHM-REWARD MATRIX (L246, Session 87 -- 8 runs)
Match reward structure to algorithm learning dynamics:
* **PPO + curriculum** = best on-policy (reward 14.23, +7.51 vs random). On-policy learning benefits from staged objectives because the policy and reward co-evolve.
* **SAC + dense** = best off-policy (reward 40.77, only 1.20 from greedy). Off-policy Q-learning needs simpler gradients -- curriculum transitions confuse the Q-function during early replay buffer filling.
* **SAC entropy** must be reduced (ent_coef=0.05) in physics-grounded environments. Default auto-entropy aggressively explores regions the Lagrangian attractor penalizes.
* **PPO + dense** inverts hierarchy (beats greedy but loses to random) -- on-policy doesn't benefit from simplified gradients.

## INSTRUCTION
1. **Observation Space:** Combine raw state (12D manifold) + derived features (3D Bloch vector, 4D fiber base). Use `spaces.Box` with physically meaningful bounds.
2. **Action Space:** Start with small actions proportional to dt. Scale up only if convergence is too slow.
3. **Reward Design:** Choose reward mode based on algorithm:
   - PPO/on-policy → `reward_mode='curriculum'` (3-stage reach→maintain→optimize)
   - SAC/off-policy → `reward_mode='dense'` (proximity + coherence + energy)
   - Always include proximity base term. Never use differential-only rewards.
4. **Termination:** Streak-based convergence (N consecutive steps in target band) + max_steps truncation.
5. **Evaluation:** Use UniverseEvaluator with 3+ baselines (random, greedy, noisy_greedy). Bootstrap CIs distinguish genuine capability from noise. If random > trained, reward function is broken.
6. **Persistence:** Save every training run to SurrealDB `training_run` table. Log hyperparams, metrics, and diagnostic narrative.
7. **Compound Cycle:** After evaluation, compare against prior runs. If improvement found, update this skill. If regression, diagnose via Training Diagnostic Loop (L241).

## ANTI-PATTERNS
- ❌ Differential-only rewards (coherence_gain without proximity base) -- creates oscillation incentive
- ❌ Large action spaces with strong attractors -- agent fights physics instead of cooperating
- ❌ Evaluating without random baseline -- cannot distinguish learning from environment dynamics
- ❌ SAC with default auto-entropy in physics-grounded envs -- fights the attractor
- ❌ SAC with curriculum reward -- Q-function confused by non-stationary staged objectives
- ❌ PPO with dense reward in physics envs -- on-policy doesn't benefit from simplified gradients
- ❌ Training without persisting to SurrealDB -- breaks the compound learning loop

## REFINEMENT LOG
- v1.0.0: Initial skill from L233-L239 (Session 87)
- v1.1.0: Added Algorithm-Reward Matrix from 8-run diagnostic (L246). Added reward_mode selection rule. Added SAC entropy and compound cycle instructions.

## VERSION
v1.1.0

- v20260401: Training data shows SAC+dense achieves reward=40.77. SAC Dense closes gap to greedy: only 1.20 reward behind (40.77 vs 41.97). 20% convergence. Dense mod
