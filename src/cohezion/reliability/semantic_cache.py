"""
Semantic Caching Utility for Cohezion.
Uses vector similarity to retrieve cached agent responses.
"""

import json
import os
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Optional

class SemanticCache:
    def __init__(self, cache_dir: str = "cache/semantic", threshold: float = 0.95):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.threshold = threshold
        self.index_path = self.cache_dir / "index.json"
        self.vectors_path = self.cache_dir / "vectors.npy"
        
        self.vectors: List[np.ndarray] = []
        self.metadata: List[Dict[str, Any]] = []
        self._load_cache()

    def _load_cache(self):
        """Load existing cache from disk if available."""
        if self.index_path.exists() and self.vectors_path.exists():
            try:
                self.metadata = json.loads(self.index_path.read_text())
                raw_vectors = np.load(self.vectors_path)
                self.vectors = [v for v in raw_vectors]
            except Exception as e:
                # If loading fails, start fresh to avoid corruption
                self.metadata = []
                self.vectors = []

    def save(self):
        """Persist cache index and vectors to disk."""
        if not self.vectors:
            return
            
        try:
            self.index_path.write_text(json.dumps(self.metadata, indent=2))
            np.save(self.vectors_path, np.array(self.vectors))
        except Exception:
            pass

    def search(self, query_vec: np.ndarray, top_k: int = 1) -> Optional[Dict[str, Any]]:
        """Perform semantic similarity search."""
        if not self.vectors:
            return None
            
        # Standardize query vector shape
        q_norm = np.linalg.norm(query_vec)
        if q_norm == 0:
            return None
        
        # Convert list of vectors to matrix for fast calculation
        matrix = np.array(self.vectors)
        norms = np.linalg.norm(matrix, axis=1)
        
        # Avoid division by zero
        norms[norms == 0] = 1e-10
        
        # Calculate Cosine Similarity
        cosine_sim = np.dot(matrix, query_vec) / (norms * q_norm)
        
        best_idx = np.argmax(cosine_sim)
        score = cosine_sim[best_idx]
        
        if score >= self.threshold:
            result = self.metadata[best_idx].copy()
            result["semantic_score"] = float(score)
            return result
            
        return None

    def add(self, vector: np.ndarray, response: str, metadata: Dict[str, Any]):
        """Add a new entry to the semantic cache."""
        # Check if already exists (exact match on response to avoid bloat)
        for idx, m in enumerate(self.metadata):
             if m.get("response") == response:
                 # Update vector and timestamp
                 self.vectors[idx] = vector
                 self.metadata[idx] = {**m, **metadata, "timestamp": os.path.getmtime(self.index_path) if self.index_path.exists() else 0}
                 return

        self.vectors.append(vector)
        self.metadata.append({
            "response": response,
            "timestamp": 0, # Will be set on save/load
            **metadata
        })
        self.save()

    def get_stats(self) -> Dict[str, Any]:
        """Return cache health and size metrics."""
        return {
            "size": len(self.vectors),
            "threshold": self.threshold,
            "dimension": self.vectors[0].shape[0] if self.vectors else 0
        }
