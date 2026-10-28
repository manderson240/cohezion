# SKILL: SLEEP_CONTINUAL_LEARNING_PRIME

## DOMAIN EXPERTISE
Bio-inspired continual learning and memory consolidation for Large Language Models and autonomous agent swarms. Based on Google Research's SLEEP framework (arXiv:2606.03979), this skill replaces static deployment and catastrophic forgetting with a cyclical rhythm: an active wake phase for fast episodic experience gathering and an offline sleep phase for upward memory consolidation and synthetic dream rehearsal.

## KEY TEXTS & CONCEPTS
- **The Continual Learning Trilemma**: Fixed weights suffer from knowledge cutoffs; continuous fine-tuning suffers from catastrophic forgetting; context windows remain ephemeral and expensive.
- **The Wake Phase**: High-plasticity episodic buffer captures real-time interactions, task trajectories, rewards, losses, and surprisals without perturbing core parametric weights.
- **Stage 1 - Memory Consolidation (Knowledge Seeding)**: Upward distillation of episodic experiences into stable long-term parameters using Generalized Distillation (on-policy distillation combined with reinforcement learning imitation).
- **Elastic Weight Consolidation (EWC)**: Quadratic parameter penalty weighted by the empirical Fisher Information matrix diagonal ($F_i$) to protect critical prior knowledge from interference:
  $$\mathcal{L}_{\text{total}} = \mathcal{L}_{\text{distill}} + \frac{\lambda_{\text{ewc}}}{2} \sum_i F_i (\theta_i - \theta_{i,\text{prior}})^2$$
- **Stage 2 - Dreaming (Autonomous Self-Improvement)**: Self-supervised generation of synthetic counterfactual scenarios to explore boundary states, verified deterministically via AutoHarness invariants before locking updates.
- **Phase Reset**: Clean flushing of temporary episodic capacity upon sleep completion, preparing clean context for subsequent operational cycles.

## INSTRUCTION

### 1. Capture Active Traces During Wake Phase
During runtime task execution, stream operational steps into the high-plasticity episodic buffer:

```python
from cohezion.agi.sleep_framework import SleepFramework

framework = SleepFramework(dimension=12, ewc_lambda=100.0)

# Record waking task trajectory
framework.record_experience(
    task_description="Execute invariant check on DeFi adapter",
    action_sequence=["inspect_ast", "detect_desync", "build_proof"],
    state_vector=[0.1, 0.4, 0.8, 0.05, 0.2, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    reward=0.95,
    loss=0.04,
    entropy=0.12,
    session_id="session_42",
)
```

### 2. Trigger Offline Sleep Consolidation
When daytime work ends or when the agent enters an idle/cron window:
- Sample prioritized experiences using surprisal ($\delta = |\text{loss}| + |\text{reward} - 0.5| + 0.1 \cdot \text{entropy}$).
- Perform upward distillation with EWC protection.

```python
# Execute offline sleep cycle
summary = framework.sleep(batch_size=64, num_dreams=12)

print(f"Consolidated: {summary.consolidation.experiences_consolidated} experiences")
print(f"Knowledge Retention: {summary.consolidation.knowledge_retention_score:.4f}")
print(f"EWC Penalty: {summary.consolidation.ewc_penalty:.4f}")
```

### 3. Generate and Verify Synthetic Dreams
Stage 2 autonomously generates synthetic edge cases, testing invariant limits without human data:

```python
print(f"Dreams Simulated: {summary.dreaming.dreams_generated}")
print(f"Verification Rate: {summary.dreaming.verification_rate * 100:.1f}%")
print(f"Counterfactual Discoveries: {summary.dreaming.counterfactual_discoveries}")
```

### 4. Lock Prior Baselines and Flush Capacity
Upon completing Stage 2, the framework freezes updated parameters into $\theta_{\text{prior}}$, updates the Fisher information metric, and flushes the buffer to prevent memory leaks and maintain context fidelity.

## VERSION
v0.1

## SEE ALSO
- `src/cohezion/skills/DREAM_LOGIC_PRIME.md`
- `src/cohezion/skills/AUTOHARNESS_PRIME.md`
- `src/cohezion/skills/KARPATHY_COGNITIVE_COMPRESSION_PRIME.md`
