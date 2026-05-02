# Cohezion Autoresearch Program

Defines the hypothesis search space for autonomous training optimization across
Cohezion's three primary training targets. Read by `AutoresearchDriver` at loop start.

## Training Targets

| Target | Script | Metric | Direction |
|--------|--------|--------|-----------|
| `jepa` | `src/cohezion/world_model/jepa_world_model.py` | `total_loss` | minimize |
| `flume_vae` | `src/cohezion/flume/train_vae.py` | `val_loss` | minimize |
| `rl_ppo` | `src/cohezion/rl/ppo_trainer.py` | `episode_reward` | maximize |

## Hypothesis Space

Each hypothesis is a `key=value` string injected as an env-var override into the
training subprocess. Agents may add new hypotheses by appending to this list.

```
# Learning rate schedule
learning_rate=1e-4
learning_rate=3e-4
learning_rate=1e-3

# Batch size
batch_size=16
batch_size=32
batch_size=64

# Hidden dimension (JEPA embed_dim / FLUME latent_dim)
hidden_dim=128
hidden_dim=256
hidden_dim=512

# Loss weight balance (JEPA prediction vs sigreg)
sigreg_weight=0.1
sigreg_weight=0.3
sigreg_weight=0.5

# Attention heads (JEPA n_heads)
n_heads=2
n_heads=4
n_heads=8
```

## Constraints

- **Wall-clock budget**: 300 seconds per experiment (--budget flag passed to script)
- **Metric regression threshold**: 0.5% worse than current best → discard (status="regression")
- **Max iterations per session**: 12 (prevents runaway spending)
- **Error threshold**: 3 consecutive `status="error"` → abort loop and report

## K-Search Tree

State persisted at `~/.cohezion-research/ksearch/{target}.json`.
Selection policy: UCB1 with C=sqrt(2). Unexplored nodes always selected first.

To reset the tree (start fresh exploration):
```bash
rm ~/.cohezion-research/ksearch/{target}.json
```

## Output

All results persisted to SurrealDB `experiments` table in `cohezion:vault` database.
Query with:
```sql
SELECT * FROM experiments WHERE type = 'autoresearch' ORDER BY timestamp DESC LIMIT 20;
```
