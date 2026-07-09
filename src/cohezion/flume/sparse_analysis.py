"""Sparse feature analysis for the FLUME 256D latent space.

Finds an overcomplete dictionary D (n_atoms × n_features) such that each
latent z ≈ D.T @ alpha where alpha is sparse.

Encoding paths
--------------
sklearn present (default)
    DictionaryLearning for fitting; SparseCoder with LASSO-LARS for encoding.
numpy-only fallback (sklearn absent or _force_numpy=True)
    SVD-based dictionary initialisation; greedy matching pursuit for encoding.
"""

from __future__ import annotations

import contextlib

import numpy as np


_DictionaryLearning = None
_SparseCoder = None
with contextlib.suppress(ImportError):
    from sklearn.decomposition import DictionaryLearning as _DictionaryLearning
    from sklearn.decomposition import SparseCoder as _SparseCoder


class SparseLatentAnalysis:
    """Dictionary learning over FLUME latent vectors.

    Parameters
    ----------
    n_atoms:
        Number of dictionary atoms.  May exceed ``n_features`` (overcomplete).
    sparsity_target:
        Fraction of atoms to activate (numpy path) *or* LASSO regularisation
        strength (sklearn path).  Values in ``(0, 1)`` work for both semantics.
    _force_numpy:
        Internal escape hatch — bypass sklearn even when it is installed.
        Useful for testing the numpy path in isolation.
    """

    def __init__(
        self,
        n_atoms: int = 512,
        sparsity_target: float = 0.05,
        *,
        _force_numpy: bool = False,
    ) -> None:
        self.n_atoms = n_atoms
        self.sparsity_target = sparsity_target
        self._use_sklearn = (_DictionaryLearning is not None) and not _force_numpy
        self._dictionary: np.ndarray | None = None  # (n_atoms, n_features)
        self._learner = None  # DictionaryLearning instance (sklearn path only)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fit(self, latents: np.ndarray) -> None:
        """Learn dictionary atoms from a batch of latent vectors.

        Parameters
        ----------
        latents:
            Array of shape ``(n_samples, n_features)``.
        """
        n_samples, n_features = latents.shape
        # n_samples is the hard constraint for sklearn; n_atoms may exceed n_features
        # (overcomplete dict is intentional — see module docstring).
        n_components = min(self.n_atoms, n_samples)

        if self._use_sklearn:
            assert _DictionaryLearning is not None  # invariant: set when _use_sklearn is True
            self._learner = _DictionaryLearning(
                n_components=n_components,
                transform_algorithm="lasso_lars",
                transform_alpha=self.sparsity_target,
                max_iter=500,
                random_state=42,
                n_jobs=1,
            )
            self._learner.fit(latents)
            self._dictionary = self._learner.components_  # (n_components, n_features)
        else:
            self._dictionary = self._numpy_fit(latents, n_components, n_features)

    def encode(self, z: np.ndarray) -> np.ndarray:
        """Return sparse code ``alpha`` for a single latent vector ``z``.

        Returns
        -------
        alpha:
            Shape ``(n_atoms,)`` where ``n_atoms = self._dictionary.shape[0]``.
            Satisfies ``z ≈ D.T @ alpha`` approximately.

        Raises
        ------
        RuntimeError
            If called before :meth:`fit`.
        """
        if self._dictionary is None:
            raise RuntimeError("Call fit() before encode().")

        if self._use_sklearn:
            assert _SparseCoder is not None  # invariant: set when _use_sklearn is True
            coder = _SparseCoder(
                dictionary=self._dictionary,
                transform_algorithm="lasso_lars",
                transform_alpha=self.sparsity_target,
            )
            return coder.transform(z.reshape(1, -1))[0]

        return self._matching_pursuit(z)

    def top_features(self, z: np.ndarray, k: int = 5) -> list[tuple[int, float]]:
        """Return the top-k (atom_index, activation) pairs sorted by |activation|.

        Always returns exactly ``min(k, n_atoms)`` items; activations may be
        zero for an all-sparse or zero input.
        """
        alpha = self.encode(z)
        k = min(k, len(alpha))
        top_idx = np.argsort(np.abs(alpha))[::-1][:k]
        return [(int(i), float(alpha[i])) for i in top_idx]

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _numpy_fit(self, latents: np.ndarray, n_components: int, n_features: int) -> np.ndarray:
        """SVD-based dictionary initialisation (pure-numpy path).

        The top ``n_svd`` principal directions (rows of Vt) form an orthonormal
        seed; extra atoms up to ``n_components`` are random unit vectors.
        """
        centred = latents - latents.mean(axis=0)
        n_svd = min(n_components, centred.shape[0], centred.shape[1])
        _, _, Vt = np.linalg.svd(centred, full_matrices=False)
        basis = Vt[:n_svd]  # (n_svd, n_features) — highest-variance directions

        if n_svd < n_components:
            rng = np.random.RandomState(42)
            extra = rng.randn(n_components - n_svd, n_features)
            norms = np.linalg.norm(extra, axis=1, keepdims=True)
            extra /= np.where(norms > 1e-8, norms, 1.0)
            basis = np.vstack([basis, extra])

        return basis  # (n_components, n_features)

    def _matching_pursuit(self, z: np.ndarray) -> np.ndarray:
        """Greedy matching pursuit (numpy-only fallback for :meth:`encode`).

        Runs at most ``max_active = max(1, int(sparsity_target × n_atoms))``
        iterations.  Each iteration picks the most-correlated atom, adds its
        contribution to ``alpha``, and subtracts from the residual.
        """
        assert self._dictionary is not None  # callers must call encode(), which guards
        D = self._dictionary  # (n_atoms, n_features)
        n_atoms = D.shape[0]
        max_active = max(1, int(self.sparsity_target * n_atoms))

        alpha = np.zeros(n_atoms, dtype=float)
        residual = z.astype(float).copy()
        norms_sq = np.einsum("ij,ij->i", D, D)  # ||d_i||^2 for each atom
        norms_sq = np.where(norms_sq > 1e-12, norms_sq, 1e-12)

        for _ in range(max_active):
            if np.dot(residual, residual) < 1e-14:
                break
            correlations = D @ residual
            idx = int(np.argmax(np.abs(correlations)))
            step = correlations[idx] / norms_sq[idx]
            alpha[idx] += step
            residual -= step * D[idx]

        return alpha
