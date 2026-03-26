# PHASE 7: Capability Scorecard + HuggingFace Export

## Overview

Phase 7 implements the **CapabilityScorecard** (6-axis radar chart + longitudinal tracking) and **HuggingFace Export** (research dataset + dataset card) for the FLUME Journey Benchmark Platform.

## CapabilityScorecard

### 6-Axis Radar Chart

The scorecard maps each EVO physics metric family to a radar chart axis:

| Axis | Metric Family | What It Measures |
|------|--------------|-----------------|
| HIHO Coherence | `coherence` | Ability to maintain coherence near 0.5 |
| TRIUNE Balance | `triune_balance` | Equal Doer/Thinker/Knower activation |
| Stability | `stability` | Low variance, consistent HIHO proximity |
| Exotic Charge | `exotic_charge` | Sustained high charge accumulation |
| Kordylewski Orbit | `kordylewski_orbit` | Stable L4/L5 Lagrange orbit maintenance |
| SPIN Phase | `spin_phase` | Monotonic phase accumulation |

### RadarChart

**Plotly** primary, **matplotlib** fallback. Overlaid radar charts for swarm vs self-supervised comparison.

```python
radar = RadarChart()
fig = radar.plot(
    [0.85, 0.62, 0.78, 0.90, 0.71, 0.88],
    title="FLUME EVO Capability Scorecard — Run 42"
)
```

### LongitudinalTracker

Tracks scorecards across multiple benchmark runs:
- Per-axis trend slopes (improving / stable / declining)
- Weakest axis identification (lowest average score)
- Strongest axis identification (highest average score)

```python
tracker = LongitudinalTracker()
tracker.record("run_001", {"coherence": 0.85, "triune_balance": 0.62, ...})
tracker.record("run_002", {"coherence": 0.88, "triune_balance": 0.65, ...})
weakest = tracker.get_weakest_axis()  # → "TRIUNE Balance"
```

### CapabilityScorecard Usage

```python
scorecard = CapabilityScorecard()
scorecard.record_run("run_001", episodes=[...], biographies=[...])
scorecard.record_run("run_002", episodes=[...], biographies=[...])

report = scorecard.generate_report()
fig = scorecard.plot_radar(run_id="run_002")
comparisons = scorecard.compare_runs("run_001", "run_002")
```

## HuggingFace Export

### HuggingFaceExporter

Exports benchmark results as a HuggingFace-compatible dataset:

```
output_dir/
├── data.jsonl       # One record per episode
├── metadata.json     # Aggregated statistics
└── spec.json        # Dataset specification
```

### Dataset Card (README.md)

Generated via `generate_dataset_card()`:
- YAML frontmatter with dataset metadata
- Task categories and tags
- Hardware and model architecture
- Metric family descriptions
- Citation block

### Record Format (data.jsonl)

```json
{
  "episode_id": "ep_001",
  "run_id": "run_001",
  "task_name": "cohezion/hiho_basin_easy",
  "archetype": "HIHO_BASIN",
  "difficulty": "easy",
  "reward": 1.5,
  "mean_coherence": 0.82,
  "final_coherence": 0.85,
  "success": true,
  "steps": 142,
  "duration_seconds": 2.3,
  "biography_length": 142,
  "biography": [
    {"coherence": 0.5, "doer_weight": 0.33, ...},
    ...
  ],
  "metrics": {
    "coherence": {"mean": 0.82, "std": 0.04, ...},
    ...
  }
}
```

## Key Classes

| Class | File | Purpose |
|-------|------|---------|
| `CapabilityScorecard` | capability_scorecard.py | 6-axis tracking + reporting |
| `RadarChart` | capability_scorecard.py | Plotly/matplotlib radar |
| `LongitudinalTracker` | capability_scorecard.py | Multi-run trend analysis |
| `StatisticalComparison` | capability_scorecard.py | Swarm vs self-sup comparison |
| `HuggingFaceExporter` | huggingface_export.py | JSONL dataset export |
| `HuggingFaceDatasetSpec` | huggingface_export.py | Dataset metadata spec |
| `generate_dataset_card` | huggingface_export.py | README.md generator |

## Tests

- 57 tests in `tests/eval/test_capability_scorecard.py`
- 32 tests in `tests/eval/test_huggingface_export.py`

## Integration Points

### Scorecard ↔ EvalPipeline
```python
scorecard = CapabilityScorecard()
pipeline = EvalPipeline(verbose=False)
scorecard = pipeline.run(policy, n_episodes=100)
```

### Scorecard → SkillRefiner (Weak-Axis Curriculum)
```python
weakest = scorecard._longitudinal_tracker.get_weakest_axis()
# Oversample TaskSpecs targeting weakest axis
```

### Scorecard → FastAPI
```python
@app.get("/scorecard/{run_id}")
def get_scorecard(run_id: str):
    scorecard = load_scorecard(run_id)
    return scorecard.generate_report()
```

### HuggingFace Export → ArXiv
```python
card = generate_dataset_card(exporter)
# Include paper_url in dataset_card
# Submit to arxiv.org
# Publish dataset to huggingface.co/datasets/cohezion/flume-journey-bench
```
