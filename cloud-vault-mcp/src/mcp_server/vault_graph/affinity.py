"""FLUME PCA affinity pipeline — importable module extracted from compute_pca_matrix.py."""

import json
import os as _os
import urllib.request
from pathlib import Path

import numpy as np


# VAULT_PCA_MATRIX_PATH env var overrides in production and tests.
# Default falls back to the standard vault layout for local dev only.
_default = (
    Path(_os.environ.get("VAULT_PATH", "/home/mike-anderson/vaults/cohezion-vault"))
    / "scripts"
    / "dba"
    / "pca_matrix.npy"
)
PCA_PATH = Path(_os.environ.get("VAULT_PCA_MATRIX_PATH", str(_default)))


def load_pca_matrix() -> np.ndarray | None:
    """Load the pre-computed PCA matrix. Returns None if not found."""
    if PCA_PATH.exists():
        return np.load(str(PCA_PATH)).astype(np.float32)
    return None


def project_to_12d(vec_768: list[float], pca_matrix: np.ndarray) -> list[float]:
    """Project a 768D embedding vector to 12D using the PCA matrix."""
    v = np.array(vec_768, dtype=np.float32)
    return (pca_matrix @ v).tolist()


def normalize_l2(vec: list[float]) -> list[float]:
    """L2-normalize a vector. Returns zeros if input is zero vector."""
    v = np.array(vec, dtype=np.float32)
    norm = float(np.linalg.norm(v))
    if norm < 1e-8:
        return [0.0] * len(vec)
    return (v / norm).tolist()


def embed_and_project(
    text: str,
    pca_matrix: np.ndarray,
    ollama_url: str = "http://localhost:11434",
) -> list[float] | None:
    """Embed text via Ollama nomic-embed-text, project to 12D. Returns None on failure."""
    try:
        payload = json.dumps({"model": "nomic-embed-text", "prompt": text}).encode()
        req = urllib.request.Request(
            f"{ollama_url}/api/embeddings",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            emb = json.loads(resp.read())["embedding"]
        projected = project_to_12d(emb, pca_matrix)
        return normalize_l2(projected)
    except Exception:
        return None
