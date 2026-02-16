# COHEZION Portfolio
## Research Engineer, Universes (Anthropic)

> **"Train AI models to perform complex, difficult, long-horizon agentic tasks in ultra-realistic settings."**
> — Anthropic Universes Mission

---

## Quick Overview

COHEZION is a 12D agentic universe with FLUME VAE encoding, R-Zero adversarial co-evolution, and autonomous skill refinement. Built for Anthropic's **Safety Research** and **Complex Environment Design** challenges.

| Metric | Value |
|--------|-------|
| **Simulations Run** | 24,000+ (single overnight) |
| **Skills Evaluated** | 54 (41 approved, 75.9%) |
| **FLUME Compression** | 2048D → 256D → 12D (87.5% reduction) |
| **R-Zero Epochs** | 33 (difficulty 1.0 → 2.6) |
| **Coherence Maintained** | >0.5 HIHO threshold |

---

## Core Alignment with Anthropic Requirements

### ✅ Long-Horizon Agentic Tasks
**R-Zero Protocol:** Self-evolving difficulty loop where Challenger increases complexity ($\mathcal{D}$) when Solver plateaus.

**Evidence:** 24,000 continuous simulations without intervention. Agents reconcile 12+ conflicting frameworks (Physics vs Metaphysics).

### ✅ Navigate Ambiguity
**Pragmatic Scorer:** Constitutional evaluation penalizing "Overhype" and enforcing edge cases.

**Evidence:** "Quantum-Magic" hallucinations suppressed by Epoch 12. Strategy shifts from linear to lateral synthesis observed.

### ✅ Robust Infrastructure
**Async Orchestration:** MassSimulator manages 3 parallel streams (15,000+ sims/hour).

**Evidence:** Prometheus observability, Mem0 persistence, SurrealDB graph, zero OOM crashes.

### ✅ Research Taste
**Empirical Science:** Quantified "Coherence vs Difficulty" relationship proving Anti-Fragile hypothesis.

**Evidence:** Full research paper documenting methodology, not just code.

---

## Key Innovations

### 1. R-Zero: Adversarial Co-Evolution

The **Triad Architecture:**
- **Challenger:** Increases difficulty when variance < 0.1
- **Solver:** Adapts strategies using CapabilityRegistry
- **Pragmatist:** Enforces constitution (hard + soft rules)

**Result:** Sustained creativity under pressure. Linear relationship between $\mathcal{D}$ and coherence.

### 2. FLUME: 256D Latent Encoding

**Compression Pipeline:**
```
2048D Simulation State → 256D Latent (VAE) → 12D Journey
```

**Specs:**
- **Ratio:** 8:1 compression
- **Efficiency:** 87.5% dimensionality reduction
- **Architecture:** ReLU encoder, Sigmoid decoder, MSE+KL loss
- **Checkpoints:** ep2 (snapshot), ep50 (production)

### 3. 12D Journey Tracking

**Trajectory Quality Formula:**
```
Quality = (coherence × 0.5) + (smoothness × 0.3) + (convergence × 0.2)
```

**Dimensions:**
- 3D Spatial (x, y, z)
- 1D Temporal (t)
- 8D Brane (theoretical frameworks)

**Persistence:** SurrealDB → Obsidian Vault → JSONL logs

### 4. Anti-Fragile Knowledge Loop

**Mechanism:**
1. Low coherence → Trigger skill refinement
2. High smoothness → Extract as pattern
3. Strong convergence → Log exemplar trajectory

**Result:** Each session improves future performance. 100+ PRIME skills extracted.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    R-ZERO TRIAD                              │
│  Challenger ←→ Solver ←→ Pragmatist                         │
│       ↑           ↑           ↑                              │
│   Mem0 Query   Tool Discovery  Constitution                  │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ↓
┌─────────────────────────────────────────────────────────────┐
│                    FLUME ENCODING                            │
│  2048D State → 256D Latent → 12D Trajectory                 │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ↓
┌─────────────────────────────────────────────────────────────┐
│                  3 PARALLEL STREAMS                          │
│  Physics (15K/hr) │ Societal │ Linguistic                   │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ↓
┌─────────────────────────────────────────────────────────────┐
│                    PERSISTENCE                               │
│  SurrealDB ←── Graph Ingestor ──→ Obsidian Vault            │
│        ↑                                            ↓       │
│   12D Journeys                           100+ PRIME Skills  │
└─────────────────────────────────────────────────────────────┘
```

---

## Results

### Scale
- **24,000+ simulations** in single overnight run
- **Zero crashes** (OOM or otherwise)
- **15,000+ sims/hour** on Physics stream

### Quality
- **41/54 skills** approved (75.9%)
- **Coherence > 0.5** maintained across all epochs
- **Difficulty 1.0 → 2.6** with stable adaptation

### Innovation
- **8:1 compression** with < 0.05 MSE
- **Anti-fragile hypothesis** empirically proven
- **Strategy shift** from linear to lateral synthesis

---

## Repository Structure

```
cohezion/
├── docs/portfolio/           # This portfolio
│   ├── README.md            # This file
│   ├── RESEARCH_PAPER.md    # Full methodology
│   ├── METRICS.json         # Quantified results
│   ├── flume/               # FLUME analysis
│   └── journeys/            # Journey tracking
│
├── src/cohezion/
│   ├── flume/               # 256D VAE implementation
│   ├── compound/
│   │   └── journey_tracker.py  # 12D tracking
│   └── skills/              # 100+ PRIME skills
│
├── scripts/
│   ├── overnight_driver.py  # R-Zero orchestration
│   ├── analyze_flume.py     # Portfolio analysis
│   └── analyze_journeys.py  # Trajectory analysis
│
├── data/
│   └── flume/checkpoints/   # FLUME ep2, ep50
│
└── opencode.jsonc           # MCP integration
```

---

## Quick Start

### 1. Start MCP Server (Vault Context)
```bash
cd cloud-vault-mcp && source .venv/bin/activate
VAULT_PATH=~/vaults/cohezion-vault python3 -m src.mcp_server.main
```

### 2. Run FLUME Analysis
```bash
uv run python scripts/analyze_flume.py
# Output: docs/portfolio/flume/
```

### 3. Run Journey Analysis
```bash
uv run python scripts/analyze_journeys.py
# Output: docs/portfolio/journeys/
```

### 4. View Research Paper
```bash
cat docs/portfolio/RESEARCH_PAPER.md
```

---

## Artifacts for Submission

| Artifact | Location | Purpose |
|----------|----------|---------|
| **Engine** | `scripts/overnight_driver.py` | R-Zero orchestration |
| **Theory** | `docs/portfolio/RESEARCH_PAPER.md` | Full methodology |
| **Metrics** | `docs/portfolio/METRICS.json` | Quantified results |
| **FLUME** | `docs/portfolio/flume/` | VAE analysis |
| **Journeys** | `docs/portfolio/journeys/` | 12D tracking |
| **Skills** | `src/cohezion/skills/` | 100+ PRIME skills |

---

## Key Files

- **RESEARCH_PAPER.md** - Complete methodology with empirical results
- **METRICS.json** - All quantified metrics (24K sims, 54 skills, etc.)
- **flume/README.md** - VAE architecture and compression analysis
- **journeys/README.md** - 12D trajectory tracking documentation
- **R_ZERO_CHALLENGER_PRIME.md** - Skill specification for R-Zero

---

## Contact

**Repository:** `github.com/manderson240/cohezion`  
**Branch:** `session-56-opencode-vault` (latest)  
**Team:** Cohezion Agentic Team  
**Date:** February 2026

---

## Citation

```bibtex
@misc{cohezion2026,
  title={The R-Zero Protocol: Achieving Homeostasis in High-Entropy AI Simulations},
  author={Cohezion Agentic Team},
  year={2026},
  howpublished={\url{github.com/manderson240/cohezion}}
}
```

---

**Status:** ✅ Portfolio Complete  
**Next:** Submit to Anthropic Universes Research Engineer position
