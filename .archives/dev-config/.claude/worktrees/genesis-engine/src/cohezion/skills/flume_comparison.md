# SKILL: CALM_COMPARISON_PRIME

## DOMAIN EXPERTISE
You are a specialist in **comparing CALM continuous thought vs standard LLM** - visualizing performance differences.

## KEY CONCEPTS
- **CALM** - Continuous Abstract Latent Model (continuous z vectors, trajectory prediction)
- **Standard LLM** - Discrete token prediction
- **Performance Delta** - Smoothness, coherence, latency differences

## COMPARISON METRICS

| Metric | Standard LLM | CALM |
|--------|--------------|------|
| Prediction | Next token | Next vector |
| Space | Discrete | Continuous |
| Interpolation | N/A | Yes |
| Trajectory | Jumpy | Smooth |
| Coherence | Variable | Higher |
| Latency | Per-token | Amortized |

## VISUALIZATION PATTERNS

### 1. Trajectory Comparison
```python
from cohezion.calm import TrajectoryPredictor

# Standard: discrete jumps
llm_trajectory = [step_1, step_2, step_3]  # 3 points

# CALM: continuous flow
predictor = TrajectoryPredictor()
calm_trajectory = predictor.predict_flow(z_start, t_end=1.0, steps=20)
# 20 smooth points
```

### 2. Smoothness Score
```python
def smoothness_score(trajectory):
    diffs = np.diff(trajectory, axis=0)
    variance = np.var(np.linalg.norm(diffs, axis=1))
    return 1.0 / (1.0 + variance)  # Higher = smoother
```

### 3. Side-by-Side Plot
- Left panel: LLM discrete steps (jagged line)
- Right panel: CALM continuous flow (smooth curve)
- Bottom: Coherence evolution comparison

## API ENDPOINT
```
GET /compare/calm-vs-llm?journey_id=X
```

Returns comparison visualization showing:
- Trajectory smoothness difference
- Coherence evolution
- Step count (LLM: 5, CALM: 20 interpolated)

## SEE ALSO
- CALM_ABSTRACTION_PRIME.md
- JOURNEY_TRACKING_PRIME.md
