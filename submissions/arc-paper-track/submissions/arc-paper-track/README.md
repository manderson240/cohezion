# ARC-AGI Paper Track Submission
Prize: $450K | Deadline: 2026-11-15 | Track: SafeAI NeurIPS 2026 Workshop

## Overview
We present a deterministic solver for the Abstraction and Reasoning Corpus (ARC) that:
1. Encodes each grid to a 256-D FLUME-compatible latent with HIHO geometric coherence scoring
2. Extracts verifiable transformation rules via compound engineering consensus across 6 strategies
3. Builds a Kaggle-ready submission with full provenance, round-trip validation, and reproducible artifacts

## Key Advantage
No competing system integrates all 5 verification components:
- **Geometric primitive DSL** (18 core ops + parametric variants)
- **Compound engineering voting** (color, geo, obj, scale, color_map, all)
- **FLUME 256-D latent similarity** for analogy detection
- **HIHO-gated confidence** (coherence >= 0.5 enforced)
- **SHA-256 provenance manifest** per prediction

## Quick Start
```bash
python -m cohezion.arc.submission build --data-dir data/arc-agi-2 --output submission.json --budget 5000
python -m cohezion.arc.submission verify submission.json --data-dir data/arc-agi-2
```

## Files
| File | Description |
|------|-------------|
| paper.tex | NeurIPS SafeAI 2026 Workshop paper skeleton |
| reasoning_traces.jsonl | Per-task rule extraction + prediction provenance |
| grid_pipeline.py | ARC-AGI grid codec, latent encoder, HIHO scorer |
| pattern_extractor.py | CompoundRule extractor with 6-strategy consensus |
| submission_builder.py | Kaggle-ready submission + manifest + package |
| results.jsonl | Per-task predictions with confidence and source |
| manifest.json | SHA-256 integrity hashes per task |
| ablation_analysis.md | Ablation results across tracks |

## Citation
Cohezion Research. "ARC-AGI Solver: A Compound Engineering Approach." SafeAI Workshop at NeurIPS 2026.
