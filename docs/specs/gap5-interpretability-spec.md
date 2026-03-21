# Gap 5 Spec: Interpretability — Foundation Layer

**Priority**: First (all other gaps depend on this)
**Timeline**: Weeks 1-2 of the research program
**Risk if skipped**: Every subsequent analysis operates on potentially meaningless coordinates

---

## Problem Statement

FLUME has two critical interpretability failures:

1. **88% of the 256D input is SHA-256 noise.** The ExperienceEncoder fills dims [29:256] with hash expansion (`_sha256_expand`). The VAE trained on these vectors devotes most of its capacity to reconstructing pseudorandom bytes, not learning semantic structure.

2. **Three incompatible 12D label sets.** The same dimensional index means different things depending on which module reads it:

| Index | JourneyTracker | UniverseBridge | SurrealMCP |
|-------|---------------|----------------|------------|
| 0 | novelty | spatial_x | x |
| 1 | logic | spatial_y | y |
| 2 | field | spatial_z | z |
| 3 | spatial | physics | time |
| 4 | temporal | biology | mass |
| 5 | precipitation | field | sentiment |
| 6 | coherence | logic | complexity |
| 7 | efficiency | quantum | factuality |
| 8 | convergence | control | connectivity |
| 9 | smoothness | temporal | stability |
| 10 | resonance | novelty | novelty |
| 11 | harmony | precipitation | precipitation |

**Source citations:**
- JourneyTracker: `src/cohezion/compound/journey_tracker.py:144-157` — `DIMENSION_LABELS` list
- UniverseBridge: `src/cohezion/flume/universe_bridge.py:43-44` — `AXIOMATIC_DIMS` list
- SurrealMCP: `src/cohezion/mcp/surreal_server.py` — dimension labels in the trajectory schema
  (verify exact line: search for `"x", "y", "z", "time"` in that file before implementing mappings)

Only indices 10-11 (novelty, precipitation) are consistent across all three.

---

## Component 1: CanonicalDimensionRegistry

**File**: `src/cohezion/flume/dimension_registry.py`

### Purpose

Single source of truth for 12D dimension semantics. All modules that read or write 12D vectors import labels from here. Mapping tables translate legacy label sets.

### Interface

```python
from dataclasses import dataclass
from enum import IntEnum

class AxisDimension(IntEnum):
    """Canonical 12D axis indices. Authoritative ordering."""
    SPATIAL_X = 0      # Physical/positional X coordinate
    SPATIAL_Y = 1      # Physical/positional Y coordinate
    SPATIAL_Z = 2      # Physical/positional Z coordinate
    TEMPORAL = 3        # Time/sequence position
    COHERENCE = 4       # Internal consistency (HIHO target = 0.5)
    EFFICIENCY = 5      # Resource utilization / token economy
    NOVELTY = 6         # Information-theoretic surprise
    LOGIC = 7           # Structural reasoning quality
    CONVERGENCE = 8     # Progress toward objective
    SMOOTHNESS = 9      # Trajectory continuity
    FIELD = 10          # Domain/context strength
    PRECIPITATION = 11  # Action crystallization / decision readiness

class CanonicalDimensionRegistry:
    """Registry for 12D dimension labels and cross-module mappings."""

    CANONICAL_LABELS: list[str]  # The 12 labels in index order
    CANONICAL_DESCRIPTIONS: dict[str, str]  # What each dimension measures

    @classmethod
    def get_labels(cls) -> list[str]:
        """Return canonical label list."""

    @classmethod
    def get_label(cls, index: int) -> str:
        """Return label for a specific dimension index."""

    @classmethod
    def from_journey_tracker(cls, jt_labels: dict[str, float]) -> np.ndarray:
        """Map JourneyTracker's label dict to canonical 12D vector."""

    @classmethod
    def from_universe_bridge(cls, ub_vector: np.ndarray) -> np.ndarray:
        """Reorder UniverseBridge's vector to canonical ordering."""

    @classmethod
    def from_surreal_mcp(cls, sm_dict: dict[str, float]) -> np.ndarray:
        """Map SurrealMCP's label dict to canonical 12D vector."""

    @classmethod
    def to_journey_tracker(cls, canonical: np.ndarray) -> dict[str, float]:
        """Reverse mapping: canonical → JourneyTracker labels."""

    @classmethod
    def to_universe_bridge(cls, canonical: np.ndarray) -> np.ndarray:
        """Reverse mapping: canonical → UniverseBridge ordering."""
```

### Design Decisions

**Why this specific label ordering?**

The canonical ordering follows conceptual grouping:
- **Spatial** (0-2): Position in semantic space — the "where"
- **Temporal** (3): Sequence position — the "when"
- **Quality** (4-5): Coherence + efficiency — the "how well"
- **Information** (6-7): Novelty + logic — the "what kind of thinking"
- **Dynamics** (8-9): Convergence + smoothness — the "trajectory quality"
- **Context** (10-11): Field + precipitation — the "environmental conditions"

**Mapping table derivation:**

The mapping from JourneyTracker labels to canonical indices is determined by semantic alignment, not positional correspondence. For example, JourneyTracker's "novelty" at index 0 maps to canonical index 6, because the canonical ordering groups spatial dimensions first.

```python
# JourneyTracker → Canonical index mapping
_JT_TO_CANONICAL = {
    "novelty": 6,       # Was JT[0], now canonical[6]
    "logic": 7,         # Was JT[1], now canonical[7]
    "field": 10,        # Was JT[2], now canonical[10]
    "spatial": 0,       # Was JT[3], now canonical[0]
    "temporal": 3,      # Was JT[4], now canonical[3]
    "precipitation": 11,# Was JT[5], now canonical[11]
    "coherence": 4,     # Was JT[6], now canonical[4]
    "efficiency": 5,    # Was JT[7], now canonical[5]
    "convergence": 8,   # Was JT[8], now canonical[8]
    "smoothness": 9,    # Was JT[9], now canonical[9]
    "resonance": 0,     # Was JT[10], PROVISIONAL merge with spatial_x — see note below
    "harmony": 1,       # Was JT[11], PROVISIONAL merge with spatial_y — see note below
}
```

**Note on "resonance" and "harmony" (PROVISIONAL — requires Gap 3 re-validation):**

These JourneyTracker labels have no clear semantic definition distinct from spatial positioning
based on code inspection alone. They are *provisionally* mapped to spatial_x and spatial_y.

**This mapping must be treated as a hypothesis, not a fact.** If resonance/harmony encode
genuine signal distinct from spatial position (e.g., inter-agent coupling, field resonance
frequencies, or harmonic phase relationships), merging them with spatial_x/y destroys that
information irreversibly.

**Required Gap 3 validation step** (before finalizing this merge):
1. Collect 200+ trajectories with both resonance/harmony values and task outcomes
2. Train linear probes on resonance and harmony separately
3. Test if probe accuracy on resonance/harmony exceeds probe accuracy on spatial_x/y alone
4. If Δaccuracy > 5% for either: **DO NOT merge** — keep as separate canonical dimensions
   (expand canonical from 12 to 13 or 14 dimensions if needed)
5. Only if Δaccuracy < 5%: confirm merge as the canonical mapping

Flag: `_RESONANCE_HARMONY_MERGE_VALIDATED = False` — set to True only after Gap 3 confirms.
Until validated, downstream consumers should treat SPATIAL_X and SPATIAL_Y as potentially
contaminated with resonance/harmony signal.

### Migration Path

1. Create `dimension_registry.py` with all mappings
2. Add a `_canonical_reorder()` call to JourneyTracker's `_step_to_axiomatic()` output — behind a feature flag
3. Add `_canonical_reorder()` to UniverseBridge's `_vector_to_axiomatic()` — behind same flag
4. Once all three modules produce canonical ordering, remove the flag
5. All downstream consumers (DegradationDetector, ThermodynamicMetrics, etc.) get consistent labels

---

## Component 2: SemanticEmbedder

**File**: `src/cohezion/flume/semantic_embedder.py`

### Purpose

Replace the SHA-256 hash expansion (dims [29:256]) with learned semantic embeddings that preserve meaning. The VAE can then learn semantic structure instead of reconstructing noise.

### Interface

```python
class SemanticEmbedder:
    """Generate learned 227D semantic embeddings for experience fingerprints.

    Replaces ExperienceEncoder._sha256_expand() with embeddings from
    a pre-trained text encoder (Ollama nomic-embed-text or fallback).
    """

    def __init__(
        self,
        target_dim: int = 227,
        model: str = "nomic-embed-text",
        cache_size: int = 10_000,
    ):
        """
        Parameters
        ----------
        target_dim : int
            Output dimensionality (must match _FINGERPRINT_DIM = 227).
        model : str
            Ollama embedding model name.
        cache_size : int
            LRU cache size for repeated texts.
        """

    async def embed(self, text: str) -> np.ndarray:
        """Embed text into target_dim floats.

        Pipeline:
        1. Call Ollama nomic-embed-text (768D output) via async HTTP, with timeout
        2. Project 768D → 227D via PCA/random projection
        3. Normalize to [0, 1] range
        4. Cache result

        Falls back to SHA-256 hash if Ollama unavailable or times out.

        Uses ``asyncio.wait_for`` internally so the caller is never blocked
        indefinitely by a slow or unresponsive Ollama instance::

            raw = await asyncio.wait_for(
                _call_ollama_http(text, self.model),
                timeout=5.0,
            )

        Raises
        ------
        asyncio.TimeoutError
            Propagated when Ollama does not respond within the configured
            timeout and no fallback is appropriate.
        """

    async def embed_batch(self, texts: list[str]) -> np.ndarray:
        """Batch embedding for training efficiency."""

    async def embed_experience(self, experience: dict) -> np.ndarray:
        """Build fingerprint text from experience dict, then embed.

        Uses same key extraction as ExperienceEncoder._build_fingerprint_text()
        for backward compatibility.
        """

    @property
    def is_learned(self) -> bool:
        """True if using learned embeddings, False if SHA-256 fallback."""
```

### Architecture Detail

```
                Input text
                    │
                    ▼
    ┌───────────────────────────────┐
    │  Ollama nomic-embed-text      │  768D dense embedding
    │  (local, no API cost)         │
    └───────────────┬───────────────┘
                    │ 768D
                    ▼
    ┌───────────────────────────────┐
    │  Dimensionality Reduction     │  768D → 227D
    │  Random projection (fixed     │  (preserves distances via
    │  seed=42 for determinism)     │   Johnson-Lindenstrauss)
    └───────────────┬───────────────┘
                    │ 227D
                    ▼
    ┌───────────────────────────────┐
    │  Min-max normalization        │  Scale to [0, 1]
    │  (per-dimension, computed     │  (matches SHA-256 output range)
    │   from fixed calibration set) │
    └───────────────┬───────────────┘
                    │ 227D ∈ [0,1]
                    ▼
            Output (227,) float32
```

### Calibration Set Specification

Min-max normalization statistics (per-dimension min/max) are computed **once** from a fixed
calibration set and frozen. This ensures embeddings are comparable across training runs.

**Calibration set**: `data/calibration/semantic_embedder_calibration.jsonl`
- 1000 diverse task descriptions sampled from the existing 11K simulation trajectory corpus
- Covers all 5 operation types (200 per type), spanning the full semantic range
- Frozen at project initialization — **never updated** with new data
- Commit checksum to git: `data/calibration/semantic_embedder_calibration.sha256`

**Normalization procedure**:
```python
# Computed once and saved to data/calibration/normalizer_stats.npz
projected = random_projection(embed_batch(calibration_texts))  # (1000, 227)
per_dim_min = projected.min(axis=0)   # (227,) — frozen
per_dim_max = projected.max(axis=0)   # (227,) — frozen
np.savez("data/calibration/normalizer_stats.npz", min=per_dim_min, max=per_dim_max)
```

**At inference**:
```python
normalized = (projected - per_dim_min) / (per_dim_max - per_dim_min + 1e-8)
normalized = np.clip(normalized, 0.0, 1.0)  # Values outside calibration range → clipped
```

**Why fixed calibration?** If normalization statistics were recomputed on each training run,
embeddings from different runs would be on incompatible scales, making cross-run trajectory
comparison impossible. The fixed calibration set acts as a universal reference frame.

**Why nomic-embed-text?**
- Already available on Ollama (no download)
- 768D output provides sufficient information for 227D projection
- Local inference: zero API cost, ~5ms per embedding
- Strong semantic similarity properties (MTEB benchmark)

**Why random projection instead of PCA?**
- PCA requires computing eigenvectors on a training set, introducing data dependency
- Random projection (Johnson-Lindenstrauss lemma) preserves pairwise distances with high probability
- Fixed seed ensures determinism: same text always produces same embedding
- Can be replaced with trained projection later (Gap 2)

### Integration with ExperienceEncoder

```python
# experience_encoder.py (MODIFIED)

class ExperienceEncoder:
    def __init__(self, embedder: SemanticEmbedder | None = None):
        self._embedder = embedder

    async def encode(self, experience: dict) -> np.ndarray:
        vec = np.zeros(TOTAL_DIM, dtype=np.float32)

        # ... dims [0:29] unchanged ...

        # Dims [29:256]: semantic fingerprint
        if self._embedder is not None:
            vec[29:256] = await self._embedder.embed_experience(experience)
        else:
            # Legacy SHA-256 fallback
            fingerprint_text = self._build_fingerprint_text(experience)
            vec[29:256] = self._sha256_expand(fingerprint_text, _FINGERPRINT_DIM)

        return vec
```

---

## Component 3: DimensionProbe

**File**: `src/cohezion/flume/dimension_probe.py`

### Purpose

Test whether each 12D dimension actually encodes what its label claims. Uses linear probing: train a simple classifier on labeled data, measure accuracy. If a "coherence" dimension doesn't correlate with actual coherence, the label is wrong.

### Interface

```python
@dataclass
class ProbeResult:
    """Result of probing a single dimension."""
    dimension_index: int
    dimension_label: str
    accuracy: float          # Classification/regression accuracy
    baseline_accuracy: float # Majority class or mean prediction
    cohen_d: float           # Effect size
    p_value: float           # Statistical significance
    n_samples: int
    is_validated: bool       # accuracy > baseline + threshold AND p < 0.05

class DimensionProbe:
    """Linear probing classifiers for 12D dimension validation.

    For each dimension, trains a logistic regression / linear regression
    to predict a ground-truth label from that dimension's value alone.
    """

    def __init__(self, min_samples: int = 100, significance: float = 0.05):
        ...

    def probe_dimension(
        self,
        dim_index: int,
        dim_values: np.ndarray,       # (N,) values of this dimension
        ground_truth: np.ndarray,     # (N,) ground truth labels
        task: str = "regression",     # "regression" or "classification"
    ) -> ProbeResult:
        """Probe whether dim_values predict ground_truth."""

    def probe_all_dimensions(
        self,
        trajectories: np.ndarray,     # (N, 12) trajectory data
        ground_truths: dict[int, np.ndarray],  # dim_idx → ground truth
    ) -> list[ProbeResult]:
        """Probe all dimensions with available ground truth."""

    def generate_report(self, results: list[ProbeResult]) -> str:
        """Human-readable validation report."""
```

### Ground Truth Sources

| Dimension | Ground Truth Source | Measurement |
|-----------|-------------------|-------------|
| COHERENCE (4) | Test pass rate from TaskOutcome | Pearson r |
| EFFICIENCY (5) | tokens_used / output_quality from metrics | Pearson r |
| NOVELTY (6) | Information-theoretic surprise (n-gram entropy) | Pearson r |
| LOGIC (7) | Code quality metrics (lint score, type-check pass) | Pearson r |
| CONVERGENCE (8) | Task completion progress (0→1 over steps) | Pearson r |
| SMOOTHNESS (9) | Trajectory L2 jerk (numerical derivative) | Pearson r (inverted) |
| SPATIAL (0-2) | Cluster assignment in embedding space | Classification acc |
| TEMPORAL (3) | Sequence position within execution | Pearson r |
| FIELD (10) | Domain classifier (which skill type) | Classification acc |
| PRECIPITATION (11) | Time-to-action (latency before decision) | Pearson r |

---

## Component 4: LatentTraversalTool

**File**: `src/cohezion/flume/latent_traversal.py`

### Purpose

Walk along individual dimensions in the 256D latent space to discover what semantic concepts are encoded. Essential for understanding the ThoughtEncoder's learned representations.

### Interface

```python
@dataclass
class TraversalResult:
    """Result of walking along one latent dimension."""
    dimension_index: int
    values: list[float]              # The traversal values
    decoded_texts: list[str]         # Decoded text at each value
    coherence_scores: list[float]    # Coherence at each point
    semantic_shift: str              # Human-readable description of what changed

class LatentTraversalTool:
    """Explore ThoughtEncoder's 256D latent space via dimension traversals."""

    def __init__(self, encoder: FlumeEncoder):
        self.encoder = encoder

    def traverse_dimension(
        self,
        base_text: str,
        dim_index: int,
        n_steps: int = 11,
        range_std: float = 3.0,
    ) -> TraversalResult:
        """Traverse a single dimension while holding others fixed.

        1. Encode base_text → z (256D)
        2. Vary z[dim_index] from -range_std to +range_std
        3. Decode each modified z back to text
        4. Analyze what semantic property changed
        """

    def find_most_active_dimensions(
        self,
        texts: list[str],
        top_k: int = 10,
    ) -> list[tuple[int, float]]:
        """Find which dimensions have highest variance across a text corpus.

        Returns list of (dim_index, variance) sorted descending.
        """

    def interpolation_path(
        self,
        text_a: str,
        text_b: str,
        n_steps: int = 10,
    ) -> list[TraversalResult]:
        """Walk the linear path from text_a to text_b in latent space.

        Returns decoded texts at each step + which dimensions changed most.
        """
```

---

## Validation Criteria (Gap 5 Complete When)

1. `CanonicalDimensionRegistry` deployed; all modules produce identically-ordered 12D vectors
2. `SemanticEmbedder` produces 227D learned embeddings; VAE retrained on new data shows lower reconstruction loss than SHA-256 baseline
3. `DimensionProbe` results show ≥6 of 12 dimensions have statistically significant correlation (p < 0.05) with ground truth, Cohen's d ≥ 0.5
4. `LatentTraversalTool` demonstrates interpretable semantic variation along ≥3 ThoughtEncoder dimensions

---

## Tests

```python
# tests/flume/test_dimension_registry.py
def test_canonical_labels_length():
    assert len(CanonicalDimensionRegistry.get_labels()) == 12

def test_journey_tracker_roundtrip():
    original = {"novelty": 0.5, "logic": 0.8, ...}
    canonical = CanonicalDimensionRegistry.from_journey_tracker(original)
    roundtrip = CanonicalDimensionRegistry.to_journey_tracker(canonical)
    assert roundtrip == original

def test_all_modules_same_ordering():
    # Same semantic concept maps to same index regardless of source module
    jt_coherence_idx = CanonicalDimensionRegistry.from_journey_tracker(
        {"coherence": 1.0, **{k: 0.0 for k in OTHER_LABELS}}
    ).argmax()
    assert jt_coherence_idx == AxisDimension.COHERENCE

# tests/flume/test_semantic_embedder.py
import asyncio
from unittest.mock import AsyncMock, patch
import numpy as np

# A fixed fake 768D vector returned by the mocked Ollama HTTP call.
_FAKE_768D = np.random.default_rng(42).random(768).astype(np.float32)

@patch(
    "cohezion.flume.semantic_embedder._call_ollama_http",
    new_callable=AsyncMock,
    return_value=_FAKE_768D,
)
def test_deterministic_output(mock_ollama):
    emb = SemanticEmbedder()
    a = asyncio.run(emb.embed("test input"))
    b = asyncio.run(emb.embed("test input"))
    np.testing.assert_array_equal(a, b)
    # Second call should hit the LRU cache — Ollama called exactly once.
    mock_ollama.assert_called_once()

@patch(
    "cohezion.flume.semantic_embedder._call_ollama_http",
    new_callable=AsyncMock,
    return_value=_FAKE_768D,
)
def test_output_shape(mock_ollama):
    emb = SemanticEmbedder()
    result = asyncio.run(emb.embed("test"))
    assert result.shape == (227,)

@patch(
    "cohezion.flume.semantic_embedder._call_ollama_http",
    new_callable=AsyncMock,
)
def test_similar_texts_closer(mock_ollama):
    # Give each text a distinct fake 768D vector so the projection can
    # distinguish them; the ab-pair is intentionally closer in cosine space.
    vec_a = np.ones(768, dtype=np.float32) * 0.9
    vec_b = np.ones(768, dtype=np.float32) * 0.8   # close to vec_a
    vec_c = np.zeros(768, dtype=np.float32)          # far from vec_a

    mock_ollama.side_effect = [vec_a, vec_b, vec_c]

    emb = SemanticEmbedder()
    a = asyncio.run(emb.embed("python function for sorting"))
    b = asyncio.run(emb.embed("python method for ordering"))
    c = asyncio.run(emb.embed("recipe for chocolate cake"))

    # Use cosine similarity (normalize before dot product) for distance comparison
    def cosine_sim(x: np.ndarray, y: np.ndarray) -> float:
        return float(np.dot(x, y) / (np.linalg.norm(x) * np.linalg.norm(y) + 1e-8))

    sim_ab = cosine_sim(a, b)
    sim_ac = cosine_sim(a, c)
    assert sim_ab > sim_ac  # Related texts are more similar

# tests/flume/test_dimension_probe.py
def test_coherence_probe():
    probe = DimensionProbe()
    # Synthetic: coherence dim should correlate with test pass rate
    dim_values = np.random.rand(200)
    ground_truth = dim_values + np.random.randn(200) * 0.1  # Correlated
    result = probe.probe_dimension(4, dim_values, ground_truth)
    assert result.is_validated
```
