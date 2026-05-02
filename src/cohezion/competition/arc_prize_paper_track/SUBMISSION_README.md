# ARC Prize 2026 — Paper Track Submission

**Paper Title**: The Compound Loop: Metacognitive Alignment Gates for Autonomous Program Synthesis

**Authors**: Cohezion Research

**Repository**: github.com/cohezion/research

**License**: MIT

---

## Reproduction Instructions

### 1. Prerequisites

- Python 3.13+
- `uv` package manager
- `ollama` for local LLM inference (optional)

```bash
uv sync
```

### 2. Reproduce Solver Results

```bash
uv run python src/cohezion/competition/arc_solver.py
```

Expected output on training set (1000 tasks):
- Solve rate: ~3.4%
- Average solve time: < 0.13s

### 3. Reproduce Ablation Study

```bash
cd src/cohezion/competition/arc_prize_paper_track
uv run python ablation_study.py
```

Expected output (100-task sample):
- geo (7 ops): 0.0%
- geo+color (15 ops): 1.0%
- all primitives (33 ops): 1.0%

This demonstrates diminishing returns from raw primitive expansion without metacognitive control.

### 3. Reproduce Alignment Gate

```bash
uv run python -c "from cohezion.flume.alignment import LatentAligner; ..."
```

### 4. Paper Draft

- **DRAFT_v2.md**: Main paper (Markdown)
- **figure1_compound_loop.png**: Architecture diagram
- **ablation_results.json**: Raw ablation data
- **VMODEL_ANALYSIS.md**: Systems engineering analysis

---

## Cohezion Systems Used in This Work

| System | Role in Paper |
|--------|--------------|
| Compound Loop | Metacognitive architecture |
| Alignment Gate | HIHO threshold validation |
| Journey Tracker | Execution trace logging |
| Skill Refiner | Primitive library growth |
| FLUME VAE | Latent state representation (256D) |
| Ouroboros | Failure detection & self-healing |
| Mycelium | Cross-project knowledge sharing |

---

## Citation

```bibtex
@software{cohezion_arc_2026,
  author = {Cohezion Research},
  title = {The Compound Loop: Metacognitive Alignment Gates for Autonomous Program Synthesis},
  year = {2026},
  url = {https://github.com/cohezion/research},
  license = {MIT}
}
```
