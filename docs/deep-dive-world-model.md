# World Model — Deep Dive Documentation

**Generated:** 2026-04-22
**Scope:** `src/cohezion/world_model/`
**Files Analyzed:** 4 (3 Python modules + 1 empty `__init__.py`)
**Lines of Code:** 967
**Workflow Mode:** Exhaustive Deep-Dive (`bmad-document-project`)

## Overview

The `world_model` subsystem is Cohezion's **learned dynamics model** for the 12D agentic manifold. It predicts how the manifold evolves given actions, detects "surprising" transitions where predictions fail, and uses that surprise signal to drive exploration.

**Purpose:** Give agents a forward-simulable internal world model so they can plan in latent space (cheap) rather than always executing in the real manifold (expensive).

**Key responsibilities:**
1. Encode 12D manifold states → 64D latent embeddings (Variational, Gaussian prior)
2. Predict next-step latent embeddings from `(state_emb, action_emb)` pairs
3. Guard against latent collapse via **SIGReg** (random-projection Epps-Pulley test) + Gaussian KL
4. Identify **causally important** embedding dimensions via Causal-JEPA masking
5. Compute **surprise scores** on observed transitions — feeds exploration
6. Sample high-surprise regions and convert them into exploration tasks

**Integration points summary:**
- **Upstream**: `cohezion.physics.lagrangian`, `.riemannian_metric`, `.fiber_bundle`, `.gauge_theory`, `.spinor` — physics primitives feed both training data synthesis and surprise-context computation
- **Downstream**: `cohezion.api.services.world_model` exposes HTTP endpoints at `/api/world-model/*` (wired into the FastAPI app at `src/cohezion/api/__init__.py:1658-1660`)
- **Tests**: 34 pytest tests across two files (`tests/world_model/test_jepa_world_model.py` + `test_jepa_lewm.py`)
- **External consumer**: ARC Prize 2026 research uses JEPA for pattern learning (`tests/research/arc_prize_2026/test_arc_jepa.py`)

---

## ⚠️ Documentation drift detected

During this deep-dive, three claims in upstream docs were verified to be **false**:

| Claim source | Line | Claim | Reality |
|---|---|---|---|
| `CLAUDE.md` | Bioelectric directory row | `src/cohezion/world_model/bioelectric_model.py` (`BioelectricNetwork`) | **Wrong path.** The class exists, but at `src/cohezion/physics/bioelectric_model.py` — it's a physics-layer concept, not world_model. |
| `CLAUDE.md` | Natural Capital row | `src/cohezion/world_model/natural_capital.py` (`NaturalCapitalModel`) | **File does not exist anywhere.** No `NaturalCapitalModel` class in the tree. |
| `CLAUDE.md` | Evo Model row | `src/cohezion/world_model/evo_model.py` (`EvoModel`) | **File does not exist anywhere.** No `EvoModel` class in the tree. |
| `CLAUDE.md` | World Model row | "JEPA predictor (86K params, causal masking), Cosmogony, SymmetryBreaking" | Params: actual is **~2M** per `jepa_world_model.py:20`. `Cosmogony` and `SymmetryBreaking` exist in `src/cohezion/physics/cosmogony.py`, not `world_model/`. |
| `docs/architecture-backend.md:93` | World model row | `JEPAWorldModel (86K), BioelectricNetwork, NaturalCapitalModel, EvoModel, SymmetryBreaking` | All four non-JEPA classes are either mislocated (Bioelectric, SymmetryBreaking → physics/) or phantom (NaturalCapitalModel, EvoModel). Params: 86K → ~2M. |

**Recommended remediation** (not performed by this workflow — flagged for follow-up):
1. Update `CLAUDE.md:124-128` to reflect actual `world_model/` contents (JEPAWorldModel + SurpriseExplorer + SIGReg) and the ~2M parameter count
2. Update `docs/architecture-backend.md:93` with the same correction
3. Decide whether the missing `bioelectric_model.py` / `natural_capital.py` / `evo_model.py` files are (a) aspirational and should be created, or (b) deprecated and should be removed from docs

---

## Complete File Inventory

### `src/cohezion/world_model/__init__.py`

**Purpose:** Empty module initializer. Does NOT re-export the public API — callers must import from submodules directly (e.g. `from cohezion.world_model.jepa_world_model import JEPAWorldModel`).
**LOC:** 0
**File type:** Package init

**What future contributors must know:**
There's no package-level `__all__` or re-export. If you want a canonical `from cohezion.world_model import JEPAWorldModel` style import, you must add re-exports here. Current dependent code (`api/services/world_model.py`, tests) all use the long-form imports and will not break if this is populated, but any change should be additive.

**Exports:** none
**Imports:** none
**Used by:** implicitly used when `cohezion.world_model` is imported as a package, but no current code relies on that behavior

---

### `src/cohezion/world_model/jepa_world_model.py`

**Purpose:** Core JEPA (Joint-Embedding Predictive Architecture) world model. Learns to predict next-step 12D manifold evolution in a learned 64D latent space, with three coupled losses: prediction MSE, anti-collapse SIGReg, and Gaussian KL regularizer. Extends JEPA with Causal-JEPA dimension masking and Le-WM's temporal-straightening monitoring.
**LOC:** 654
**File type:** Python module (PyTorch)

**What future contributors must know:**
- **~2M parameters** by default, designed to fit on Strix Halo iGPU / CPU — do NOT assume CUDA, see `HARDWARE_PROFILE_PRIME.md`
- The model is **auto-trained on first API call** via `api/services/world_model.py::_get_model()` using 200 synthetic samples — if you expose new endpoints, don't duplicate this auto-train logic
- Synthetic training data comes from `cohezion.physics.lagrangian.LagrangianDynamics` simulating `hiho_potential` trajectories — the dataset quality depends on the physics layer being correct
- The model uses the **reparameterization trick** in `ManifoldEncoder.forward` — it is stochastic at training time (mu + std*eps), deterministic at inference (uses mu)
- The `decoder` is a **single Linear layer** (embed_dim → state_dim), not an MLP — prediction accuracy in state space is bounded by this simplicity. Upgrading to an MLP decoder is the most obvious lever
- **Save/load format** contains `encoder`, `action_encoder`, `predictor`, `causal_mask`, `decoder`, `metrics`, `config` keys — changing any will break checkpoint compatibility

**Exports (ordered by `__all__`):**

| Symbol | Kind | Signature / Key attrs | Description |
|---|---|---|---|
| `ActionEncoder` | `nn.Module` | `__init__(action_dim=12, embed_dim=64, hidden_dim=128)`; `forward(action) -> Tensor` | 2-layer MLP: 12D action → 64D embedding |
| `CausalMask` | `nn.Module` | `__init__(embed_dim=64, mask_ratio=0.3)`; `forward(x, training=True) -> Tensor`; `causal_importance_scores() -> np.ndarray`; `top_k_causal_dims(k=None) -> list[int]` | Causal-JEPA dimension masker. Learns per-dim importance via a sigmoid-gated parameter. Default top-k = 10% of embed_dim |
| `JEPAWorldModel` | class | see methods table below | Orchestrator that owns encoder+action_encoder+predictor+causal_mask+decoder+sigreg+optimizer |
| `ManifoldEncoder` | `nn.Module` | `__init__(state_dim=12, embed_dim=64, hidden_dim=128)`; `forward(state) -> (z, mu, logvar)` | Variational encoder with Gaussian prior. Returns reparameterized `z`, raw `mu`, raw `logvar` |
| `Predictor` | `nn.Module` | `__init__(embed_dim=64, hidden_dim=128)`; `forward(state_emb, action_emb) -> Tensor` | 3-layer MLP over concatenated (state_emb, action_emb) → predicted next-state embedding |
| `TrainingMetrics` | `@dataclass` | fields: `epoch`, `prediction_loss`, `sigreg_loss`, `regularizer_loss`, `total_loss`, `temporal_curvature`, `n_samples`, `history` | Metrics container carried on every `JEPAWorldModel` |
| `generate_synthetic_training_data(n_samples=1000, state_dim=12)` | function | → `list[tuple[np.ndarray, np.ndarray, np.ndarray]]` | Generates `(state, action, next_state)` triples via Lagrangian physics simulation |

**`JEPAWorldModel` methods (selected):**

| Method | Purpose | Gradient? |
|---|---|---|
| `train_step(states, actions, next_states)` | One optimizer step. Loss = MSE + sigreg_weight·SIGReg + regularizer_lambda·KL | Yes |
| `train_epoch(dataset, batch_size=32)` | Shuffles + iterates batches; updates `self.metrics` | Yes |
| `predict_next_state(state, action)` | Encode → predict → decode → return 12D next state | No (`@torch.no_grad()`) |
| `surprise_score(state, action, observed_next)` | MSE between predicted and observed embeddings | No |
| `simulate_latent_trajectory(initial_state, actions)` | Roll out N steps in latent space, returns list of embeddings | No |
| `simulate_trajectory(initial_state, actions)` | Roll out N steps in state space (autoregressive through encoder/predictor/decoder) | No |
| `fast_predict(state, action, k=None)` | Top-k causal dim masking for ~8x speedup (Causal-JEPA) | No |
| `counterfactual_predict(state, actions)` | Predict next state for N candidate actions from one start state | No |
| `causal_importance()` | Proxy to `CausalMask.causal_importance_scores()` | No |
| `measure_temporal_straightening(trajectory)` | Mean curvature (1 - cos between consecutive velocity vectors) on a latent trajectory | No |
| `save(path)` / `load(path)` (classmethod) | Checkpoint I/O (PyTorch `torch.save` + `weights_only=True` on load) | No |
| `status()` | Dict for API response | No |
| `n_parameters` (property) | Sum of `.numel()` across all submodules | No |

**Dependencies:**
- `numpy` — state/action/next_state tensors at the API boundary
- `torch`, `torch.nn` — all neural net modules, optimizer (AdamW)
- `.sigreg.SIGReg` — imported **mid-file at line 155** (not at top) — minor style issue, should be moved to top
- `cohezion.physics.lagrangian.{LagrangianDynamics, hiho_potential}` — in `generate_synthetic_training_data` only (lazy import)
- `cohezion.physics.riemannian_metric.fabric_block_metric` — same
- stdlib: `logging`, `dataclasses`, `pathlib`, `typing`, `random`

**Used by:**
- `src/cohezion/api/services/world_model.py:41,48,101` — HTTP service wrapper (singleton pattern, lazy train)
- `tests/world_model/test_jepa_world_model.py` — 25 unit tests (class-based)
- `tests/world_model/test_jepa_lewm.py` — 9 Le-WM-specific tests
- `tests/research/arc_prize_2026/test_arc_jepa.py` — ARC Prize 2026 adapter

**Key implementation details:**

- **Three coupled losses** (line 316-320):
  ```python
  total_loss = (
      prediction_loss
      + self.sigreg_weight * sigreg_loss
      + self.regularizer_lambda * regularizer_loss
  )
  ```
  Default weights: `sigreg_weight=0.1`, `regularizer_lambda=0.1`. Setting `regularizer_lambda=0` returns a zero-tensor from `_compute_regularizer_loss` — the branch exists to avoid spurious gradient cost, not just for speed.

- **Target embedding is computed with `@torch.no_grad`** (line 305-306) — target doesn't backprop through encoder, matching the JEPA "prediction target is a stop-grad view" pattern

- **Causal masking at train time vs inference**:
  - Training: random Bernoulli mask with rescale (`scale = 1/(1-mask_ratio)`) — Dropout-like
  - Inference: `sigmoid(importance)` weighting — learned importance becomes soft gate

- **`_set_inference_mode`** (line 519-531) manually sets `requires_grad_(False)` and toggles `module.training` on every submodule. Does NOT call `.eval()` — intentional, but it means BatchNorm running stats would not be frozen if BatchNorm were ever added. No BatchNorm currently.

**Patterns used:**
- **Reparameterization trick** (VAE-standard) in `ManifoldEncoder`
- **Lazy import** of physics layer in `generate_synthetic_training_data` to avoid circular imports
- **Singleton with auto-init** (in the API wrapper) with lazy training

**State management:** Model weights held in `nn.Module.state_dict()`s. `TrainingMetrics.history` grows unbounded across epochs — **potential leak** for long-running servers.

**Side effects:** `save()` creates parent directories via `path.parent.mkdir(parents=True, exist_ok=True)`; `load()` reads disk via `torch.load`. No DB or network I/O in this file.

**Error handling:** No explicit try/except in this file. Empty dataset in `train_epoch` returns zero-loss dict. `load()` uses `weights_only=True` which will raise if checkpoint contains non-tensor pickled objects — good safety default.

**TODOs/comments:** None marked. All comments are explanatory.

---

### `src/cohezion/world_model/surprise_explorer.py`

**Purpose:** Surprise-driven manifold exploration. Given a trained `JEPAWorldModel`, scans probe points across the 12D space, computes surprise at each, and returns the top-k most surprising regions enriched with physics context (fiber decomposition, Yang-Mills action, HIHO deviation, charge polarity). Converts regions into exploration tasks that can feed back into the compound executor.
**LOC:** 247
**File type:** Python module

**What future contributors must know:**
- `SurpriseExplorer` accepts a `world_model: object | None` — it is **duck-typed** on `.surprise_score(state, action, next_state)`. Any object implementing that signature works; use this for mock world models in tests
- The physics context computation (line 173-200) is wrapped in `try/except Exception` that returns `{"error": str(e)}` — silent failure mode. If you change physics APIs, `_compute_physics_context` will degrade gracefully but silently. Tests should assert `"error" not in physics_context` when physics should work
- Surprise probes use `action = rng.normal(0, 0.05, 12)` and `next_state = probe + action` — this is a **Euclidean-space approximation**, not a Lagrangian-flow approximation. The resulting surprise is measured against a trivial baseline, so regions with non-trivial physics dynamics will always be flagged "surprising" even if the world model predicts them perfectly
- `rng = np.random.default_rng(42)` — seeded for reproducibility. If you want session-dependent exploration, inject a seed

**Exports (via `__all__`):**

| Symbol | Kind | Description |
|---|---|---|
| `SurpriseExplorer` | class | Main exploration orchestrator |
| `SurpriseRegion` | `@dataclass` | Center + surprise + suggested action + description + physics context, with `to_dict()` |

**`SurpriseExplorer` methods:**

| Method | Purpose |
|---|---|
| `set_world_model(world_model)` | Injects or updates the model |
| `scan_manifold(trajectory_history=None)` | Returns top-k `SurpriseRegion` objects. If history provided, uses 70% focused + 30% uniform probes; otherwise 100% uniform |
| `_generate_uniform_probes()` | `n_samples` points from `Uniform[0.1, 0.9]^12` |
| `_generate_focused_probes(history)` | `n_focused` perturbed around random history points + `n_uniform` uniform probes |
| `_compute_physics_context(point)` | Dict of `fiber_base`, `yang_mills_action`, `is_hiho`, `charge_polarity`, `coherence`, `hiho_deviation`. Returns `{"error": ...}` on any failure |
| `_describe_region(point, surprise, physics)` | Composes a semicolon-joined human-readable description |
| `suggest_exploration_tasks(regions=None)` | Maps regions → task dicts for the compound executor |

**Dependencies:**
- `numpy` — probe arrays, RNG
- `cohezion.physics.fiber_bundle.FiberBundle`
- `cohezion.physics.gauge_theory.FourFabricGauge`
- `cohezion.physics.spinor.SpinorState`
- stdlib: `logging`, `dataclasses`

**Used by:** No direct consumers in the current tree. The API service `world_model.py` does not yet expose surprise exploration endpoints — **this is a potential integration gap** (the module is architecturally wired but has no user-facing path beyond direct Python API).

**Key implementation details:**

- **Probe strategy** (`_generate_focused_probes`):
  - 70% focused: `np.clip(history[rand_idx] + normal(0, 0.1, 12), 0, 1)`
  - 30% uniform: `Uniform[0.1, 0.9]^12`
  - This is a classic exploit-explore balance. The 0.1 stdev on perturbations is tuned for the [0,1]-normalized 12D manifold

- **Task priority** (line 240): `max(0, min(1, surprise_score))` — clamps surprise to [0, 1] to act as a priority. Since surprise is an MSE and can be arbitrarily large, **high-surprise regions all get priority = 1.0**, losing ordering. Consider `exp(-1/surprise)` or log-softmax over regions.

**Patterns used:**
- Duck-typed dependency injection (world_model parameter)
- Dataclass with `to_dict()` for JSON serialization
- Defensive physics-context computation (try/except)

**State management:** `self._rng` is stateful. Multiple calls to `scan_manifold` will return different probes.

**Side effects:** None — pure computation after world_model is set.

**Error handling:** Two swallowed `Exception`s — in `_compute_physics_context` and in the inner surprise loop (line 116-117). Both degrade silently. Any physics API breakage here returns zero-surprise regions with error dicts.

---

### `src/cohezion/world_model/sigreg.py`

**Purpose:** Sketched Isotropic Gaussian Regularizer — the anti-collapse loss from LeWorldModel (Maes et al., 2026, arxiv:2603.19312). Projects high-dimensional latent embeddings onto random unit-norm 1D directions and applies the Epps-Pulley test statistic to measure how close each projection's distribution is to a standard Gaussian. Minimizing this enforces isotropy and prevents the JEPA latent from collapsing to a low-rank subspace.
**LOC:** 66
**File type:** Python module (PyTorch)

**What future contributors must know:**
- **Pairwise-difference computation is O(N² × M)** in memory and compute (line 55: `(N, N, M)` tensor). For batch size 32 and 1024 projections, this is 32·32·1024 = 1M floats — fine. For batch size 256, it's 67M floats — borderline. For batch size ≥1024, you'll need a chunked implementation
- `num_projections=1024` is hardcoded as the default — the paper uses between 256 and 4096. More projections = tighter Gaussianity test but linearly more compute
- Projections are **fixed at init** (`register_buffer`) — they ride along in `state_dict` but do NOT get optimizer gradients. If you reinitialize the model, the projections change, and a previously-trained SIGReg loss value is not comparable
- The loss value is bounded but not zero for a perfect Gaussian — the Epps-Pulley statistic has a floor around the number of projections. Don't compare absolute SIGReg values across different `num_projections`
- Returns zero-tensor for batch size < 2 (line 38-39) — prevents NaN on single-sample batches but silently skips regularization

**Exports:** `SIGReg` (class, `nn.Module`)

**`SIGReg` signature:**
```python
SIGReg(embed_dim: int, num_projections: int = 1024)
  .forward(z: torch.Tensor) -> torch.Tensor   # z: (batch_size, embed_dim) → scalar loss
```

**Dependencies:**
- `torch`, `torch.nn`, `torch.nn.functional` — only framework deps

**Used by:**
- `src/cohezion/world_model/jepa_world_model.py:155` (imported inside `jepa_world_model.py`, not at top of file)
- `tests/world_model/test_jepa_lewm.py` — Le-WM test suite

**Key implementation details:**

- **Epps-Pulley decomposed into three terms** (line 47-64):
  - Term 1: `(1/n²) · Σᵢⱼ exp(-0.5 · (xᵢ - xⱼ)²)` — pairwise similarity; peaks when distribution is concentrated
  - Term 2: `-√2 · (1/n) · Σᵢ exp(-0.25 · xᵢ²)` — "attraction to zero"; most negative when values are near 0
  - Constant `+1.0`
  - Summed across all projections, then mean

- `register_buffer("projections", ...)` puts the random unit vectors into the module's state but excludes them from `parameters()` — important because `JEPAWorldModel.optimizer` concatenates `.parameters()` from every submodule, so any accidental registration as a Parameter would train these vectors (defeating the point).

**Patterns used:**
- **Fixed random projection** (à la Johnson-Lindenstrauss and random features)
- **Module-as-loss** pattern — `SIGReg` is an `nn.Module` but acts as a loss fn

**State management:** Immutable after `__init__` — no internal stats.

**Side effects:** None.

**Error handling:** Guard on batch size < 2 returns zero loss. No try/except.

---

## Contributor Checklist

- **Risks & gotchas:**
  1. **Silent failures in `surprise_explorer.py`** — two broad `except Exception` blocks mask physics API drift. Assert no `"error"` key in physics context during integration tests.
  2. **CLAUDE.md and `docs/architecture-backend.md` contain false references** to `bioelectric_model.py`, `natural_capital.py`, `evo_model.py`, and "86K params". Do not rely on those docs; source is truth.
  3. **`TrainingMetrics.history` grows unbounded** — for long-running servers, either cap it (e.g. last 100 epochs) or persist + truncate.
  4. **Singleton model in the API service** — `_MODEL` is module-global in `api/services/world_model.py`. Tests that mutate the trained model will leak state across tests unless you set `_MODEL = None` in a fixture. The project's `tests/conftest.py` already has singleton-reset patterns for FLUME/RL — extend it to cover `_MODEL` if flakiness appears.
  5. **Checkpoint schema** is pinned: `{encoder, action_encoder, predictor, causal_mask, decoder, metrics, config}`. Changes to any key break `load()` on older checkpoints.
  6. **Decoder is a single `Linear` layer** — accuracy in state space is bounded. If decode-quality matters, upgrade to an MLP.
  7. **`SIGReg` is O(batch²)** in memory — safe at batch ≤ 256, borderline at 512+, must be chunked at 1024+.

- **Pre-change verification steps:**
  1. `uv run pytest tests/world_model/ -q` → expect 34/34 passing
  2. `uv run pytest tests/research/arc_prize_2026/test_arc_jepa.py -q` → ensure ARC adapter still works
  3. `uv run uvicorn cohezion.api:app --reload` then `curl http://localhost:8080/api/world-model/status` → expect JSON with `n_parameters`, `trained`, `epoch`, losses
  4. `basedpyright src/cohezion/world_model` → zero type errors
  5. `ruff check src/cohezion/world_model` → zero lint violations

- **Suggested tests before PR:**
  1. Unit: round-trip an encode → predict → decode on a known manifold point; assert MSE bounded
  2. Unit: train one epoch on synthetic data, assert `prediction_loss` decreased
  3. Integration: hit `POST /api/world-model/train` + `POST /api/world-model/predict` via TestClient
  4. Property: `counterfactual_predict(s, [a₁, a₂, ...])` returns same length as action list
  5. Regression: load a committed checkpoint under `tests/fixtures/` (if any) and assert `status()` matches recorded values

---

## Architecture & Design Patterns

### Code organization

Flat module layout — no subpackages. The four files form a **linear dependency chain**:

```
sigreg.py (leaf) ──► jepa_world_model.py ──► surprise_explorer.py
                                              (peer; depends on duck-typed WM)
```

### Design patterns

- **JEPA (Joint-Embedding Predictive Architecture)**: predict in embedding space, not pixel/state space. Target embeddings are stop-grad (implicit via `@torch.no_grad`).
- **Variational encoder**: Gaussian prior via reparameterization trick, KL regularizer as auxiliary loss.
- **Causal-JEPA masking**: random Bernoulli during training → learned sigmoid importance at inference.
- **Random-projection Gaussianity test (SIGReg)**: trade exact multivariate test for M random 1D tests with Johnson-Lindenstrauss-style guarantees.
- **Surprise as exploration signal**: `|prediction - observation|` drives attention, à la intrinsic curiosity modules.
- **Duck typing for world model injection** in `SurpriseExplorer` — enables trivially-mockable tests.

### State management strategy

- **Model weights**: standard PyTorch `state_dict` via `save()`/`load()` classmethod.
- **Training metrics**: carried in a `TrainingMetrics` dataclass on the model instance; history list grows with each `train_epoch`.
- **API singleton**: `_MODEL` in `api/services/world_model.py`; lazy-created, auto-trained on first access.

### Error handling philosophy

- **Core model (`jepa_world_model.py`)**: no defensive error handling — assumes tensor shapes and types are correct. Fails loudly. This is the right choice inside a tight numerical core.
- **Exploration layer (`surprise_explorer.py`)**: defensive — swallows physics exceptions and inner surprise computation exceptions. Users get empty/degraded results rather than stack traces. This is **potentially too forgiving**; consider replacing with `logger.warning` + structured error surfaces.

### Testing strategy

- 25 tests in `test_jepa_world_model.py` (class-based) cover API surface, train/predict/simulate round-trips, save/load, counterfactual prediction, and causal importance
- 9 tests in `test_jepa_lewm.py` cover Le-WM-specific features: SIGReg anti-collapse behavior, dual-loss training, temporal straightening monitoring
- Property-style checks (counts, shapes, monotonicity of loss) dominate over concrete-value assertions — robust against rng changes

---

## Data Flow

```
┌─────────────────────────────────────────────────────────┐
│ cohezion.physics.lagrangian                             │
│   LagrangianDynamics.simulate(q0, v0, steps, dt)        │
│     └──► trajectory of 12D positions                    │
└───────────────────┬─────────────────────────────────────┘
                    │ (state, action, next_state) triples
                    ▼
┌─────────────────────────────────────────────────────────┐
│ generate_synthetic_training_data(n_samples)             │
│   └──► list[tuple[ndarray, ndarray, ndarray]]           │
└───────────────────┬─────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│ JEPAWorldModel.train_epoch(dataset, batch_size)         │
│   ├──► ManifoldEncoder    : state    → (z, mu, logvar)  │
│   ├──► CausalMask         : z        → masked_z         │
│   ├──► ActionEncoder      : action   → action_emb       │
│   ├──► Predictor          : (masked_z, action_emb)      │
│   │                                    → predicted_z    │
│   ├──► SIGReg(z)          : anti-collapse loss          │
│   ├──► KL(mu, logvar)     : Gaussian regularizer loss   │
│   └──► total_loss.backward() + optimizer.step()         │
└───────────────────┬─────────────────────────────────────┘
                    │ weights updated
                    ▼
┌─────────────────────────────────────────────────────────┐
│ Inference paths                                         │
│   predict_next_state(s, a)       → decoder(predicted_z) │
│   fast_predict(s, a, k)          → top-k dim masking    │
│   counterfactual_predict(s, [a]) → N outcomes           │
│   simulate_latent_trajectory     → list of embeddings   │
│   surprise_score(s, a, s_obs)    → MSE in latent space  │
└───────────────────┬─────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│ SurpriseExplorer.scan_manifold(history?)                │
│   ├──► generate probes (focused or uniform)             │
│   ├──► for each probe: world_model.surprise_score(...)  │
│   ├──► physics_context via cohezion.physics.{fiber,     │
│   │    gauge_theory, spinor}                            │
│   └──► top-k SurpriseRegion                             │
└───────────────────┬─────────────────────────────────────┘
                    │ regions
                    ▼
┌─────────────────────────────────────────────────────────┐
│ suggest_exploration_tasks(regions)                      │
│   └──► list[dict] consumed by compound executor         │
└─────────────────────────────────────────────────────────┘
```

### Entry points (not imported by anything in scope)
- `JEPAWorldModel` — called from API service
- `SurpriseExplorer` — no current in-tree consumer

### Leaf nodes (don't import anything else in scope)
- `sigreg.py` — pure torch

### Integration points

**APIs exposed** (via `src/cohezion/api/services/world_model.py`, mounted at `/api/world-model/*`):

| Endpoint | Method | Request | Response |
|---|---|---|---|
| `/api/world-model/status` | GET | — | `{n_parameters, trained, epoch, losses, dims}` |
| `/api/world-model/train` | POST | `{n_samples?, batch_size?}` | Training metrics dict |
| `/api/world-model/predict` | POST | `{state: float[12], action: float[12]}` | `{predicted_next: float[12]}` |
| `/api/world-model/simulate` | POST | `{initial_state: float[12], actions: float[N][12]}` | `{trajectory: float[N+1][12]}` |
| `/api/world-model/surprise` | POST | `{state, action, observed_next}` | `{surprise: float}` |

*Note: precise request/response shapes should be verified against `src/cohezion/api/services/world_model.py` Pydantic models after this deep-dive — we sampled the first 60 lines.*

**Shared state:**
- `_MODEL` module-global singleton in `api/services/world_model.py` — auto-initialized, auto-trained on first API call

**Events:** None published/subscribed by this subsystem.

**Database access:** None direct. The module docstring (`jepa_world_model.py:3-4`) mentions training on data "stored in SurrealDB", but the current code does NOT read from SurrealDB — `generate_synthetic_training_data` builds data from physics simulation. The docstring overstates the current wiring; any SurrealDB → training pipeline needs to be built.

### Dependency graph

```
sigreg.py ◄── jepa_world_model.py ◄── surprise_explorer.py
                ▲                         │
                │                         │
                └──physics.{lagrangian,   └── physics.{fiber_bundle,
                   riemannian_metric}         gauge_theory, spinor}

api/services/world_model.py ──► jepa_world_model.py
tests/world_model/*.py       ──► jepa_world_model.py, sigreg.py
tests/research/.../test_arc_jepa.py ──► jepa_world_model.py
```

**Circular dependencies:** ✓ none.

---

## Testing Analysis

### Test files

| File | Tests | Approach |
|---|---|---|
| `tests/world_model/test_jepa_world_model.py` | 25 (class-based) | Unit tests on model API, shape/dtype checks, round-trips, save/load |
| `tests/world_model/test_jepa_lewm.py` | 9 | Le-WM features (SIGReg, dual loss, temporal straightening) |
| `tests/research/arc_prize_2026/test_arc_jepa.py` | — | Downstream integration for ARC Prize research |

**Combined LOC**: 496 lines of test code for 967 lines of source — **~0.51 ratio**, modest. Matches CLAUDE.md's "LeWM JEPA: 34" claim exactly.

### Testing gaps

1. **No `SurpriseExplorer` tests in the tree scan above.** The exploration layer is untested — any refactor to probe strategy or physics-context computation has no safety net.
2. **No API-level integration tests** for `/api/world-model/*` endpoints were found under `tests/world_model/`. Search `tests/api/` separately if needed.
3. **Singleton leakage** in `_MODEL` is not asserted against — flaky test risk under parallel test execution.
4. **No property-based tests** (Hypothesis) on shape/type invariants — the torch contract is implicit.
5. **No checkpoint-compatibility regression test** — if you change the save schema, only runtime failure on old checkpoints surfaces the break.

---

## Related Code & Reuse Opportunities

### Similar features elsewhere

| Feature | Path | Similarity | Use as reference for |
|---|---|---|---|
| FLUME VAE | `src/cohezion/flume/` | Also a 256D variational latent over Cohezion states | Encoder design, latent-space operations |
| Cosmogony / Symmetry breaking | `src/cohezion/physics/cosmogony.py` | Another latent-manifold dynamical system | Temporal straightening ideas |
| ExecutionTraces (Meta-Harness) | `src/cohezion/persistence/` | Source of `(state, action, next_state)` from production runs | Replace synthetic training data with real logs |

### Reusable utilities available

- `cohezion.physics.lagrangian.LagrangianDynamics` — ground-truth dynamics; re-use for any "physics-plausible data" needs
- `cohezion.physics.fiber_bundle.FiberBundle.decompose` — physics context for any 12D point
- `cohezion.physics.gauge_theory.FourFabricGauge` — gauge action and HIHO detection

### Patterns to follow

- **Singleton + lazy auto-init** (see `api/services/world_model.py::_get_model`) — use this for any new heavy model in the API layer
- **Duck-typed dependency injection** (see `SurpriseExplorer.set_world_model`) — use for any explorer/probe classes that might be mocked

---

## Implementation Notes

### Code quality observations

- **Internal import at line 155 of `jepa_world_model.py`** (`from .sigreg import SIGReg`) — should be moved to top of file with the other imports
- **Internal `import random` at line 347** inside `train_epoch` — same; hoist to top
- **Two broad `except Exception`** in `surprise_explorer.py` (lines 116-117, 199-200) — convert to specific exceptions + `logger.warning`
- **Empty `__init__.py`** — either add `__all__` re-exports or delete and mark the dir as namespace package (former is preferred for discoverability)
- **`simulate_trajectory` is autoregressive through `predict_next_state`**, but `simulate_latent_trajectory` is autoregressive through `Predictor` directly — two similar APIs with different semantics. Document which to prefer, or rename for clarity

### TODOs and known issues

No inline TODOs or FIXMEs were found in this scan. The known issues are the doc-drift findings above + the testing gaps.

### Optimization opportunities

1. **Replace `Linear` decoder with 2-layer MLP** — small param cost, large decode-quality gain. Benchmark `simulate_trajectory` accuracy before and after.
2. **Chunked SIGReg** for batch ≥ 512 to eliminate the O(N²M) memory ceiling.
3. **Use `LagrangianDynamics.simulate` with larger `dt`** in `generate_synthetic_training_data` — current `dt=0.01` over 50 steps is 0.5 time units per trajectory. Larger steps = more diverse (state, action) coverage per training example.
4. **Cache `_compute_physics_context` by point** — the same probe point being scanned repeatedly recomputes fiber decomposition + Yang-Mills.
5. **Replace synthetic training data with real `ExecutionTraces`** from SurrealDB — closes the docstring-vs-reality gap and gives the model ecologically valid training distribution.

### Technical debt

- **Doc drift in CLAUDE.md and `docs/architecture-backend.md`** (see top of document)
- **Surprise explorer has no tests**
- **API request/response schemas documented here are inferred** — verify against actual Pydantic models in `api/services/world_model.py`
- **Singleton model is not reset in tests** — potential leakage
- **Unbounded training history** growth

---

## Modification Guidance

### To add new functionality

- **New metric**: extend `TrainingMetrics` dataclass + update `train_step` return dict + update `save()/load()` history record. Remember to add a corresponding field in `status()` if it should surface via API.
- **New loss term**: add to `train_step`; keep total_loss weighting explicit with a module-level hyperparameter; update `TrainingMetrics` and `_compute_regularizer_loss`-style helpers.
- **New inference method**: decorate with `@torch.no_grad()`; call `self._set_inference_mode()` first; document in this deep-dive.
- **New API endpoint**: add Pydantic request/response models at bottom of `api/services/world_model.py`, add handler on `world_model_router`, update this doc's Integration Points table.

### To modify existing functionality

- **Changing encoder architecture**: update `ManifoldEncoder.__init__` signature; bump a `config_version` field into `save()/load()` payload to invalidate old checkpoints cleanly.
- **Changing causal-mask ratio default**: update `JEPAWorldModel.__init__`'s `causal_mask_ratio` default AND the `_get_model` call in the API service if the API should see the new default.
- **Changing SIGReg projection count**: accept this will invalidate SIGReg loss comparability across checkpoints; note in release notes.

### To remove / deprecate

- **Removing `SurpriseExplorer`**: safe — no in-tree consumers. But the compound executor design doc may reference it; search the vault before removing.
- **Removing `sigreg.py`**: must also strip `self.sigreg = ...` and the sigreg loss term in `jepa_world_model.py`. Rebuild `n_parameters` property.

### Testing checklist for changes

- [ ] `uv run pytest tests/world_model/ -q` returns 34/34 passing
- [ ] `uv run pytest tests/research/arc_prize_2026/test_arc_jepa.py -q` still passes
- [ ] `basedpyright src/cohezion/world_model` reports zero errors
- [ ] `ruff check src/cohezion/world_model && ruff format --check src/cohezion/world_model` clean
- [ ] `curl http://localhost:8080/api/world-model/status` returns expected JSON after `uv run uvicorn cohezion.api:app`
- [ ] For checkpoint changes: load an existing checkpoint and assert `status()` matches pre-change values
- [ ] For API changes: `uv run pytest tests/api/` passes any world-model-related tests

---

_Generated by `bmad-document-project` workflow (deep-dive mode)._
_Base documentation: [`index.md`](./index.md)._
_Analysis mode: Exhaustive._
_Scan date: 2026-04-22._
