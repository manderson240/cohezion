# NeuroGolf 2026 — Hybrid ARC Solver

**Competition**: The 2026 NeuroGolf Championship
**Team**: Cohezion
**Approach**: Hybrid symbolic+neural solver

## Model Summary

| Property | Value |
|---|---|
| Architecture | 5-layer residual conv + batch norm |
| Parameters | 73,410 |
| Budget | < 100K ✓ |
| Solver type | DSL program search + conv fallback |

## How It Works

1. **DSL Search** (budget=5000): Brute-force symbolic program search over 23 primitives.
2. **Neural Fallback**: If DSL fails, fine-tune a 73K-parameter conv net on the task's training pairs for 200 steps.
3. **Hybrid Result**: The two methods solve *disjoint* tasks — combined accuracy is ~5% on training test tasks.

## Files

- `neurogolf_kaggle.ipynb` — self-contained Kaggle notebook
- `hybrid_ensemble.py` — reproducible solver script
- `kaggle_submission.py` — standalone submission generator

## Expected Score

~2-5% on ARC-AGI evaluation set. The small parameter count is the primary innovation.

## License

MIT — see parent repo LICENSE.
