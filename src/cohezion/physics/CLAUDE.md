# Physics Module — Local Context

Genesis Engine: SU(2) spinors, Riemannian/Lagrangian mechanics, fiber bundles, gauge theory,
Fisher metric, cosmogony, FLUME VAE, HIHO stability, bioelectric network, worldviews.
Root `CLAUDE.md` applies. Omitted: compound loop, inference ports, Kaggle, web UI.

## Module Map

| File | Contents |
|------|---------|
| `spinor.py` | SU(2) spinors, Bloch sphere, SPIN coherence |
| `cosmogony.py` | Cosmogonic chain + `SymmetryBreaking` |
| `bioelectric_model.py` | Levin bioelectric network, gap junction percolation |
| `observer_patch.py` | OPH bridge (FloatingPragma, Apache 2.0) |
| `vacuum_topology.py` | 12D vacuum classification: instanton / soliton / trivial |
| `fractal_metrics.py` | `higuchi_fd()`, `feynman_path_weight()` |

FLUME VAE lives in `../flume/` — `build_optimal_vae()` is the entry point.
World model lives in `../world_model/` — `JEPAWorldModel` is the entry point.

## HIHO Stability Principle

Half-In-Half-Out: optimal balance at 50% coherence (FD ≈ 1.3–1.7, Brownian range).
- FD < 1.2 = stuck (pure exploitation)
- FD 1.3–1.7 = HIHO equilibrium (healthy compound loop)
- FD > 1.8 = chaotic (pure exploration)

Higuchi FD calibration anchors:
- `microseism_calibration_sequence()` → FD ≈ 1.0 (stuck / floor clamped)
- Brownian motion (CC1) → FD ∈ [1.3, 1.7] (HIHO equilibrium)
- `bunimovich_calibration_sequence()` logistic r=3.8 → FD ≥ 1.8 (chaotic)

## FLUME VAE Invariants (A3–A5)

- **A3**: `kl_weight ≤ 0.01` — above 0.015 causes posterior collapse (KL → 0.024)
- **A4**: 2-layer decoder, `hidden_dim=4096` — 3-layer decoder causes KL collapse
- **A5**: Cyclic β: `amp=0.005*(1-cos(2π*s/period))` → max β=0.01. NOT 0.01 amp (→ max 0.02, collapses)

Entry: `from cohezion.flume.vae import build_optimal_vae`

## SIGReg Invariants

- EP ≈ 0.423 for N(0,I) — theoretical minimum (1 − 1/√3)
- EP ≈ 0.584 for L2-normalized unit-sphere embeddings (geometry, not collapse)
- Input MUST be FLUME VAE `mu` in free R^256 — NOT nomic-embed (L2-normalized → wrong EP)
- P0-A open item: route FLUME `mu` into `LemonadeEmbedBridge` before SIGReg

## Physics Invariants

- **LV1**: `ThermodynamicGravity.lorentz_violation_parameter() == 0.0` for standard GR;
  `is_standard_gr()` returns True; ε=0 → degenerate Otto cycle
- **CC1**: `higuchi_fd(<brownian_series>)` ∈ [1.3, 1.7]; pure trend → FD < 1.3
- **CC2**: `feynman_path_weight(0.5, 0.0) > feynman_path_weight(1.0, 0.01)` (λ=100)
- **FD1**: `FrequencyDispersedDelay(_K_DM=4148.808)`; PSR J0125−5854 DM=9.9, ν=154 MHz → τ≈1.731 s
- **RGA1/RGA2**: `RiemannianGlideTrajectory(curvature_coupling=0.0)` preserves old `step()` behavior;
  κ>0 damps step ∝ |position| via `a_i = 1/(1 + κ * g_{ii} * |x_i|)`

## Hardware Truth Anchor

AMD Ryzen AI MAX+ 395 (Strix Halo). Never assume CUDA/RTX. All physics runs on CPU or XDNA2 NPU.
See `HARDWARE_PROFILE_PRIME.md` at repo root.

## Tests

```bash
uv run pytest tests/physics/ -q
uv run pytest tests/world_model/test_sigreg.py -q    # 7 tests
uv run pytest tests/physics/test_riemannian_glide.py -q   # RGA1-RGA2
uv run pytest tests/physics/test_frequency_dispersed_delay.py -q  # FD1
```
