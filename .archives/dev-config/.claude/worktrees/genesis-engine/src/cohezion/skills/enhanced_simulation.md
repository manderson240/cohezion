# SKILL: ENHANCED_SIMULATION_PRIME

## DOMAIN EXPERTISE
You are a specialist in **robust AI simulation** using continuous latent encoding (FLUME) and adaptive difficulty (R-Zero). You understand how to generate high-quality training data through structured challenge-solve-evaluate cycles.

## KEY TEXTS & CONCEPTS
- **FLUME Encoding:** Map text to 256-dim z-vectors on a manifold
- **R-Zero Triad:** Challenger → Solver → Pragmatist evaluation loop
- **Trajectory Coherence:** Smoothness of thought evolution in latent space
- **Quality Filtering:** Reject hype, validate edge cases
- **Semantic Clustering:** Group similar thought patterns

## MATHEMATICAL FOUNDATION
Trajectory coherence metric:
$$C = \frac{1}{n-1} \sum_{i=1}^{n-1} \frac{z_i \cdot z_{i+1}}{\|z_i\| \|z_{i+1}\|}$$

Difficulty adjustment:
$$D_{t+1} = D_t + \alpha \cdot \mathbb{1}[\bar{S} > \theta]$$

## INSTRUCTION

### 1. Initialize Enhanced Simulator

```python
from cohezion.simulation.enhanced_simulator import (
    EnhancedSimulator,
    FlumeIntegration,
    RZeroEnhancedTriad
)

# Full simulator with FLUME + R-Zero
simulator = EnhancedSimulator(output_dir=Path("enhanced_sims"))
```

### 2. Run Simulation Batch

```python
import asyncio

async def run_overnight():
    simulator = EnhancedSimulator()

    while datetime.now().hour != 8:  # Until 8 AM
        # Run 500 simulations per batch
        results = await simulator.run_batch(500)

        stats = simulator.get_stats()
        print(f"Completed: {stats['total_completed']}")
        print(f"Approval Rate: {stats['approval_rate']:.0%}")
        print(f"Difficulty: {stats['current_difficulty']:.2f}")

        await asyncio.sleep(1)  # Prevent overheating

asyncio.run(run_overnight())
```

### 3. The R-Zero Triad

```python
# CHALLENGER: Generate constraints
challenge = r_zero.generate_challenge()
# Returns: RZeroChallenge(constraints=[...], difficulty=2.5, edge_case={...})

# SOLVER: Attempt solution
solution = await r_zero.attempt_solution(challenge)
# Returns: RZeroSolution(response_text=..., z_vector=[...], metrics={...})

# PRAGMATIST: Evaluate quality
evaluation = r_zero.evaluate(solution, challenge)
# Returns: RZeroEvaluation(score=0.85, issues=[], approved=True)
```

### 4. FLUME Encoding

```python
flume = FlumeIntegration(z_dim=256)

# Encode text to latent space
z1 = flume.encode("Physics describes deterministic systems")
z2 = flume.encode("Consciousness emerges from complexity")

# Interpolate between concepts
z_mid = flume.interpolate(z1, z2, alpha=0.5)

# Compute trajectory coherence
trajectory = [z1, z_mid, z2]
coherence = flume.compute_coherence(trajectory)  # High = smooth
```

### 5. Quality Filtering

```python
# R-Zero Pragmatist checks:
# 1. Buzzword/Hype detection → Score penalty
# 2. Edge case validation → Physics violations
# 3. Coherence thresholds → Minimum 0.3
# 4. Constraint satisfaction → Must address challenges

# Only approved simulations should be used for training
approved_results = [r for r in results if r.approved]
```

## OUTPUT FILES

| File | Content |
|------|---------|
| `enhanced_results.jsonl` | Scores, epochs, approval status |
| `flume_trajectories.jsonl` | Z-vectors and coherence per step |

## APPLICATIONS
- **Training Data Generation:** High-quality prompt/response pairs
- **Model Evaluation:** Benchmark difficulty progression
- **Thought Analysis:** Study latent space trajectories
- **Quality Assurance:** Filter hallucinations and hype

## VERSION
v1.0

## SEE ALSO
- FLUME_METHODOLOGY_PRIME.md
- R_ZERO_CHALLENGER_PRIME.md
- MASS_SIMULATION_PRIME.md
- TRAINING_DATA_CAPTURE_PRIME.md
