# World Model Tutorial: Training, Prediction, and Surprise

The JEPA world model learns to predict how the 12D manifold evolves. Trained on (state, action, next_state) tuples, it predicts future states and detects physically implausible transitions.

## Architecture

```
ManifoldEncoder (12D → 64D)  +  ActionEncoder (12D → 64D)
                    ↓                        ↓
              Predictor (128D → 64D predicted next embedding)
                    ↓
              Decoder (64D → 12D predicted next state)
```

Two losses only (following LeWorldModel/JEPA):
1. **Next-embedding prediction**: MSE(predicted, target)
2. **Gaussian regularizer**: KL(enc(s) || N(0,I))

~86K parameters. CPU-trainable.

## Training

### Option 1: API

```bash
# Train on 500 synthetic Lagrangian trajectory samples, 10 epochs
curl -X POST http://localhost:8080/api/world-model/train \
  -H "Content-Type: application/json" \
  -d '{"n_samples": 500, "n_epochs": 10, "batch_size": 32}'
```

Response includes loss curve and final metrics.

### Option 2: Python

```python
from cohezion.world_model.jepa_world_model import (
    JEPAWorldModel,
    generate_synthetic_training_data,
)

model = JEPAWorldModel(state_dim=12, action_dim=12, embed_dim=64)
data = generate_synthetic_training_data(n_samples=1000)

for epoch in range(20):
    metrics = model.train_epoch(data, batch_size=32)
    print(f"Epoch {epoch}: loss={metrics['total_loss']:.6f}")

model.save("checkpoints/jepa_v1.pt")
```

## Prediction

```bash
curl -X POST http://localhost:8080/api/world-model/predict \
  -H "Content-Type: application/json" \
  -d '{"state": [0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5],
       "action": [0.01,0.01,0.01,0.01,0.01,0.01,0.01,0.01,0.01,0.01,0.01,0.01]}'
```

## Surprise Scoring

Surprise = MSE between predicted and actual next-state embeddings.

```bash
curl -X POST http://localhost:8080/api/world-model/surprise \
  -H "Content-Type: application/json" \
  -d '{"state": [0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5],
       "action": [0.01,0.01,0.01,0.01,0.01,0.01,0.01,0.01,0.01,0.01,0.01,0.01],
       "observed_next": [0.9,0.1,0.9,0.1,0.9,0.1,0.9,0.1,0.9,0.1,0.9,0.1]}'
```

High surprise = the world model didn't predict this transition. These are the most interesting regions to explore.

## Surprise-Driven Exploration

```python
from cohezion.world_model.surprise_explorer import SurpriseExplorer

explorer = SurpriseExplorer(world_model=model, n_samples=100, top_k=5)
regions = explorer.scan_manifold()

for r in regions:
    print(f"Surprise={r.surprise_score:.4f}: {r.description}")

# Generate exploration tasks
tasks = explorer.suggest_exploration_tasks(regions)
```

## Trajectory Simulation

Roll out N steps autoregressively:

```bash
curl -X POST http://localhost:8080/api/world-model/simulate \
  -H "Content-Type: application/json" \
  -d '{"initial_state": [0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5],
       "actions": [[0.01,0,0,0,0,0,0,0,0,0,0,0],
                   [0,0.01,0,0,0,0,0,0,0,0,0,0],
                   [0,0,0.01,0,0,0,0,0,0,0,0,0]]}'
```

## The Self-Improving Loop

```
journey → SurrealDB → train JEPA → compute surprise →
identify gaps → suggest exploration → new journey → ...
```

The world model drives curiosity: agents explore where the model is most uncertain.
