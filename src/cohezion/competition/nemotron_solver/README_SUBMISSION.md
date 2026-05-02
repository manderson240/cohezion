# NVIDIA Nemotron Reasoning Challenge — Pure Symbolic Solver

## Overview
A pure symbolic solver for the [NVIDIA Nemotron Model Reasoning Challenge](https://www.kaggle.com/competitions/nvidia-nemotron-model-reasoning-challenge) that achieves **~54.6%** on the full 9,500-example training set **without any LLM**.

The hybrid version (with local Gemma-4 fallback) achieves **55.4%**, with the model adding only **+0.8%**. The pure-symbolic approach is the practical choice for Kaggle notebooks because it requires no external model server, runs in under a minute, and beats the user\'s current live score of **49%**.

## Quick Start (Kaggle Notebook)

Upload `kaggle_pure_symbolic.py` as a Kaggle notebook. It reads the competition `test.csv` and writes `submission.csv` entirely via symbolic solvers.

## Solver Breakdown by Type

| Type | Symbolic Solver | Accuracy (9,500 train) | Notes |
|---|---|---|---|
| Numeral | Roman numeral conversion | **100%** | Perfect |
| Unit Conversion | Linear regression | **82.5%** | Robust to scaling offsets |
| Gravity | Grid search for g in d=0.5gt² | **72.2%** | Rounding noise limits ceiling |
| Bit Manip | Per-bit mapping + partial + affine | **30.7%** | Biggest area of improvement |
| Encryption | Character substitution mapping | **32.1%** | Model fallback adds nothing |
| Equations | Simple heuristics | **~0-1%** | Critical gap — needs better model |

## Files

| File | Purpose |
|---|---|
| `solve.py` | Hybrid solver (symbolic + Gemma-4 via Lemonade) |
| `kaggle_pure_symbolic.py` | Kaggle-ready notebook, no LLM dependency |
| `submit.py` | Local CSV generator from test.csv |

## Experiments Summary (Autoresearch)

17 experiments explored symbolic and hybrid approaches:
- Baseline: 49.0% (100-sample)
- After gravity grid search: +4% on gravity
- After partial bit-manip mapping: +1.5% on bit_manip
- After 4-example model prompts: marginal
- Final full-set results: **55.4% hybrid / 54.6% pure symbolic**

### Key Finding
The model (Gemma-4 via Lemonade) contributes only **0.8 percentage points** on the full training set because it fails at:
- **Equations**: Custom multi-operator algebra is too hard for 26B 4-bit model
- **Encryption**: The model is no better than simple character mapping
- **Bit Manip**: Complex 8-bit pattern induction is beyond its capability

## Recommended Actions

1. **Submit the pure symbolic notebook to Kaggle** — it should score ~54-55% on the public/private leaderboard, improving your current 49%.
2. **For further gains**, the only high-impact path is using a much stronger model (GPT-4/Claude/Nemotron) for equations specifically. A 20% accuracy on equations would add ~3 points overall.
3. **All other AI-experimentable paths are exhausted** — 17 experiments confirm the ceiling for symbolic + Gemma-4.

## Installation (Local Testing)

```bash
# Data should be downloaded from Kaggle to /tmp/
python kaggle_pure_symbolic.py  # writes /tmp/submission.csv
```

## License
MIT — part of the Cohezion project.
