# SKILL: ALGORITHMIC_FOUNDATIONS_PRIME

## DOMAIN EXPERTISE
Designing, profiling, and executing mathematically rigorous, elegantly simple algorithms and zero-allocation data structures across autonomous AI swarms, competitive Kaggle ascensions, and real-time host cybernetics—replacing continuous approximations and heap-allocated abstractions with bitboards, exact convex simplex solvers, bipartite matching, and discrete rate-filtering.

## KEY TEXTS & CONCEPTS
- **The Bitboard Invariance Principle**: In discrete grids ($\le 32 \times 32$), representing spatial states as bitplanes of integer row masks eliminates Python object overhead and reduces bounding boxes, translations, color overlaps, and symmetry operations to single-cycle CPU SIMD bitwise instructions (`&`, `|`, `^`, `<<`, `>>`, `popcount`).
- **Convex Simplex Duality**: When optimizing multi-model or multi-label ensemble weights, weighted cross-entropy is strictly convex over the probability simplex $\mathbf{w} \in \Delta^{K-1}$. Replacing derivative-free heuristics (Nelder-Mead) with analytical gradients $\nabla \mathcal{L}(\mathbf{w})$ and SLSQP or Projected Gradient Descent (PGD) guarantees global convergence with zero entrapment.
- **Exact Bipartite Matching vs Greedy Tolerance**: In high-resolution mass spectrometry (CASMI26), greedy peak assignment fails on dense multiplets. Formulating peak alignment as Linear Sum Assignment with tolerance-bounded cost matrices guarantees maximum bipartite edge cardinality and minimal aggregate mass defect in $O(V^3)$.
- **Discrete EMA Proprioceptive Smoothing**: High-frequency differential rate estimates ($\dot{M} = \Delta M / \Delta t$) suffer from operating system buffer-flush jitter. A first-order Exponential Moving Average filter ($\bar{\dot{M}}_t = \alpha \dot{M}_t + (1 - \alpha) \bar{\dot{M}}_{t-1}$, $\alpha = 0.40$) eliminates spurious alarms while maintaining immediate response to sustained memory drain.

## INSTRUCTION

1. **Deploy Bitboards for Discrete Grid Transformations**:
   ```python
   from cohezion.kaggle.arc_bitboard import ArcBitboard
   bb = ArcBitboard.from_grid(grid)
   translated = bb.translate(dy=1, dx=2)
   symmetries = bb.d4_symmetries()  # Exact 8 D4 group operations
   overlap = bb.total_overlap(other_bb)
   ```

2. **Optimize Ensemble Mixture Weights via Convex SLSQP**:
   ```python
   from cohezion.kaggle.convex_ensemble_optimizer import ConvexEnsembleOptimizer
   optimizer = ConvexEnsembleOptimizer()
   result = optimizer.optimize_multi_label_log_loss(
       predictions=[model1_preds, model2_preds, model3_preds],
       targets=ground_truth_binary,
       label_weights=class_weights,
   )
   best_weights = result.weights  # Guaranteed sum(w) == 1.0, w >= 0
   ```

3. **Compute Exact Spectrum Alignment via Bipartite Assignment**:
   ```python
   from cohezion.kaggle.casmi_bipartite_matcher import CasmiBipartiteMatcher
   matcher = CasmiBipartiteMatcher(tolerance_ppm=15.0)
   alignment = matcher.match_spectra(exp_mz, theo_mz, exp_intensities)
   coverage = alignment.coverage_score
   ```

4. **Smooth Somatosensory Rate Reflexes**:
   ```python
   from scripts.fleet_sentry import EmaRateFilter
   ema = EmaRateFilter(alpha=0.40)
   smooth_m_dot = ema.update(raw_m_dot)
   ```

## VERSION
v0.1

## SEE ALSO
- `PROPRIOCEPTIVE_CYBERNETICS_PRIME.md`
- `DETERMINISTIC_IDEMPOTENCE_PRIME.md`
- `AUTOHARNESS_PRIME.md`
- `FASTFLOWLM_PRIME.md`
