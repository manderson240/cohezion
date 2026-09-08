# Phase 7: CapabilityScorecard + HuggingFace Export

## Overview

Phase 7 implements capability tracking and benchmark export infrastructure for the Cohezion EVO system. This phase provides quantitative assessment of EVO capabilities across 6 axes, longitudinal tracking over episodes, and statistical comparison between swarm-advisor and self-supervised learning paradigms.

## Deliverables

- `src/cohezion/eval/capability_scorecard.py` - 6-axis capability tracking
- `src/cohezion/eval/huggingface_export.py` - Dataset and benchmark export
- `tests/eval/test_capability_scorecard.py` - Test suite

## Capability Model (6 Axes)

### 1. Coherence Amplitude
Peak HIHO (Half-Integral Harmonic Oscillator) stability reached during the episode (0.0 to 1.0).

### 2. Phase Locking
Degree of synchronization with vacuum oscillations. Measures how well the EVO phase aligns with environmental oscillations.

### 3. Exotic Charge Lifetime
Duration that exotic vacuum excitation persists. Longer lifetimes indicate more stable exotic vacuum structures.

### 4. Orbit Quality
Stability of TRIUNE (Doer/Thinker/Knower) structure orbits. High orbit quality means consistent cycling through identity states.

### 5. TRIUNE Balance
Equilibrium between Doer (action), Thinker (reasoning), and Knower (intent) components. Balanced EVs maintain all three aspects.

### 6. Recovery Basin Radius
Size of the accessible stability well. Larger radius means more resilience to perturbations.

## API Reference

### CapabilityScorecard

```python
from cohezion.eval.capability_scorecard import CapabilityScorecard

scorecard = CapabilityScorecard()

# Generate radar chart
fig = scorecard.generate_radar_chart(
    {
        "coherence_amplitude": 0.85,
        "phase_locking": 0.72,
        "exotic_charge_lifetime": 0.91,
        "orbit_quality": 0.68,
        "triune_balance": 0.77,
        "recovery_basin_radius": 0.63,
    }
)

# Track longitudinal evolution
checkpoints = [
    {"episode": 1, "capability_vector": {...}, "checkpoint_path": "...", "timestamp": "..."},
    {"episode": 2, "capability_vector": {...}, "checkpoint_path": "...", "timestamp": "..."},
]
df = scorecard.track_longitudinal(checkpoints)

# Compare swarm vs self-supervised
comparison = scorecard.compare_swarm_vs_selfsupervised(swarm_results, self_supervised_results)
print(comparison.delta_capability)  # Δ per axis
print(comparison.p_values)  # Statistical significance

# 3D morphospace trajectory
fig = scorecard.generate_3d_morphospace_trajectory(checkpoints)
```

### HuggingFaceExporter

```python
from cohezion.eval.huggingface_export import HuggingFaceExporter
from pathlib import Path

exporter = HuggingFaceExporter()

# Export research dataset
evos = [evo.to_exotic_vacuum_biography() for evo in completed_evos]
await exporter.export_research_dataset(evos, Path("output/"))

# Export benchmark harness
await exporter.export_benchmark_harness(Path("output/"))
```

## Statistical Comparison

The `compare_swarm_vs_selfsupervised` method computes:

- **Delta Capability**: Mean difference (swarm - self-supervised) per axis
- **P-values**: Two-tailed t-test significance
- **Effect Sizes**: Cohen's d for practical significance

Interpretation:
- Δ > 0: Swarm advisor outperforms
- Δ < 0: Self-supervised outperforms
- p < 0.05: Statistically significant
- d > 0.5: Practically significant

## Longitudinal Tracking

The `track_longitudinal` method produces a DataFrame:

| episode | coherence_amplitude | phase_locking | ... | checkpoint_path | timestamp |
|---------|--------------------|---------------|-----|-----------------|-----------|
| 1 | 0.72 | 0.65 | ... | /data/cpt_001.pt | 2024-01-15T10:30:00 |
| 2 | 0.75 | 0.68 | ... | /data/cpt_002.pt | 2024-01-15T10:35:00 |

## 3D Morphospace Trajectory

Uses SVD-based projection from 6D capability space to 3D for visualization:
- PC1 captures primary variance (typically coherence-related)
- PC2 captures secondary variance (typically balance-related)
- PC3 captures tertiary variance (typically recovery-related)

## Implementation Notes

- Plotly is preferred for visualization with matplotlib fallback
- All capability values normalized to [0.0, 1.0]
- Statistical tests useWelch's t-test (unequal variances assumed)
- SVD projection preserves maximum variance in 3D

## Integration with Phase 6

The CapabilityScorecard consumes checkpoints produced by EvalPipeline:
1. EvalPipeline.run() produces EpisodeResults with final states
2. Final states are serialized as capability vectors
3. CapabilityScorecard tracks and compares across runs

## Testing

```bash
make test-fast
# Runs: tests/eval/test_capability_scorecard.py

# Full test suite
make test
```

## Next Steps

- Phase 8: Integration with arXiv paper submission
- Add visualization animations for trajectory evolution
- Implement online capability tracking during episodes
