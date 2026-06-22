"""Greedy max-min diversity filter and latent direction probing for FLUME 256D vectors.

Iteratively selects vectors maximising minimum cosine distance to the already-selected
set, approximating gradient-entropy diversity used in G-Vendi (Yeh et al., 2025).

Also provides ``LatentDirectionProbe`` — mechanistic interpretability for the FLUME
latent space. Identifies sparse linear directions via truncated SVD (sklearn-free PCA
approximation) corresponding to named concepts, enabling ``DegradationDetector`` to
attribute quality drops to specific concept dimension drifts rather than opaque scalars.

Example::
    import numpy as np
    vecs = [np.random.randn(256) for _ in range(1000)]
    indices = gvendi_diversity_filter(vecs, target_n=200)
    diverse = [vecs[i] for i in indices]

    probe = LatentDirectionProbe(n_directions=8)
    probe.fit(np.stack(diverse))
    probe.label_direction(0, "uncertainty")
    score = probe.concept_alignment(vecs[0], "uncertainty")
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


def gvendi_diversity_filter(
    vectors: list[np.ndarray],
    target_n: int,
) -> list[int]:
    """Return indices of target_n vectors that maximise pairwise diversity.

    Uses greedy max-min cosine distance selection (O(n * target_n)).
    Falls back to all indices when len(vectors) <= target_n.
    """
    n = len(vectors)
    if n <= target_n:
        return list(range(n))

    norms = np.array([np.linalg.norm(v) for v in vectors], dtype=np.float32)
    # Avoid division by zero for zero vectors
    safe_norms = np.where(norms == 0, 1.0, norms)
    mat = np.stack([v.astype(np.float32) / safe_norms[i] for i, v in enumerate(vectors)])

    # Seed: pick the vector closest to the mean (most representative start)
    mean_vec = mat.mean(axis=0)
    mean_vec /= max(np.linalg.norm(mean_vec), 1e-9)
    first = int(np.argmax(mat @ mean_vec))

    selected = [first]
    # min_cos_dist[i] = 1 - max cosine similarity to any selected vector so far
    sim_to_selected = mat @ mat[first]
    min_cos_dist = 1.0 - sim_to_selected

    while len(selected) < target_n:
        # Exclude already selected (set their dist to -inf so they're never picked)
        candidates = min_cos_dist.copy()
        for idx in selected:
            candidates[idx] = -np.inf
        next_idx = int(np.argmax(candidates))
        selected.append(next_idx)
        # Update min distances
        new_sim = mat @ mat[next_idx]
        min_cos_dist = np.minimum(min_cos_dist, 1.0 - new_sim)

    return selected


# ---------------------------------------------------------------------------
# Mechanistic interpretability: latent direction probing
# ---------------------------------------------------------------------------


@dataclass
class ConceptDirection:
    """A named linear direction in the FLUME latent space."""

    index: int
    label: str = ""
    explained_variance_ratio: float = 0.0
    direction: np.ndarray = field(default_factory=lambda: np.zeros(256))


class LatentDirectionProbe:
    """Identifies principal directions in a set of FLUME 256D trajectories.

    Implements mechanistic interpretability for the FLUME latent space:
    each principal component captures a named semantic axis (e.g. "uncertainty",
    "reasoning_depth", "code_vs_prose"). Once labeled, ``concept_alignment``
    measures how strongly a new vector activates a named concept.

    Design intent (interpretability loop):
      1. ``fit(samples)`` — PCA over a representative trajectory corpus
      2. ``label_direction(i, name)`` — human labels the top directions
      3. ``concept_alignment(v, name)`` — DegradationDetector reads this to
         attribute quality drops to specific concept drifts, not just opaque scalars
      4. ``top_concepts(v, k)`` — RecursiveTraceLoop uses this to build evidence-backed
         failure_map entries rather than heuristic strings

    Sklearn-free: uses numpy's ``linalg.svd`` (truncated via power iteration for
    large n) so it runs on the NPU/iGPU without a heavyweight dependency.
    """

    def __init__(self, n_directions: int = 8, seed: int = 42) -> None:
        self.n_directions = n_directions
        self.seed = seed
        self._directions: list[ConceptDirection] = []
        self._mean: np.ndarray | None = None
        self._fitted = False

    def fit(self, samples: np.ndarray) -> LatentDirectionProbe:
        """Fit principal directions from an (n_samples, dim) matrix.

        Uses power-iteration SVD bounded to ``n_directions`` components.
        Stores mean-centred directions for projection.
        """
        if samples.ndim != 2:
            raise ValueError(f"Expected 2D array, got shape {samples.shape}")
        n, dim = samples.shape
        self._mean = samples.mean(axis=0).astype(np.float32)
        centred = (samples - self._mean).astype(np.float32)

        # Truncated SVD via Gram matrix (efficient when n << dim)
        k = min(self.n_directions, n, dim)
        gram = centred @ centred.T  # (n, n)
        eigenvalues, eigenvectors = np.linalg.eigh(gram)
        # eigh returns ascending order — reverse
        idx = np.argsort(eigenvalues)[::-1][:k]
        eigenvalues = eigenvalues[idx]
        eigenvectors = eigenvectors[:, idx]  # (n, k)

        # Project back to feature space: V = X^T U / singular_values
        singular_vals = np.sqrt(np.maximum(eigenvalues, 1e-10))
        components = (centred.T @ eigenvectors) / singular_vals  # (dim, k)
        total_variance = float(np.sum(np.maximum(eigenvalues, 0)))

        self._directions = []
        for i in range(k):
            vec = components[:, i].astype(np.float32)
            vec /= max(float(np.linalg.norm(vec)), 1e-9)
            evr = float(eigenvalues[i]) / max(total_variance, 1e-10)
            self._directions.append(
                ConceptDirection(index=i, explained_variance_ratio=evr, direction=vec)
            )

        self._fitted = True
        return self

    def label_direction(self, index: int, label: str) -> None:
        """Assign a human-readable concept name to a principal direction."""
        if not self._fitted:
            raise RuntimeError("Call fit() before labeling directions.")
        if index >= len(self._directions):
            raise IndexError(f"Direction {index} out of range (fitted {len(self._directions)})")
        self._directions[index].label = label

    def project(self, vector: np.ndarray) -> np.ndarray:
        """Project a 256D vector onto the principal direction basis.

        Returns a k-dimensional activation vector (one scalar per direction).
        """
        if not self._fitted or self._mean is None:
            raise RuntimeError("Call fit() before projecting.")
        v = vector.astype(np.float32) - self._mean
        return np.array([float(np.dot(v, d.direction)) for d in self._directions])

    def concept_alignment(self, vector: np.ndarray, concept: str) -> float:
        """Return the activation strength of a named concept in the vector.

        Returns 0.0 if the concept label has not been assigned.
        """
        activations = self.project(vector)
        for i, d in enumerate(self._directions):
            if d.label == concept:
                return float(activations[i])
        return 0.0

    def top_concepts(self, vector: np.ndarray, k: int = 3) -> list[tuple[str, float]]:
        """Return the k most activated labeled concepts for a vector.

        Unlabeled directions are skipped. Useful for RecursiveTraceLoop
        failure_map construction from attributed evidence.
        """
        activations = self.project(vector)
        labeled = [
            (d.label, float(activations[i])) for i, d in enumerate(self._directions) if d.label
        ]
        labeled.sort(key=lambda x: abs(x[1]), reverse=True)
        return labeled[:k]

    @property
    def directions(self) -> list[ConceptDirection]:
        return list(self._directions)

    @property
    def fitted(self) -> bool:
        return self._fitted
