---
name: semantic-caching
description: Semantic caching using vector similarity to serve cached responses
  for semantically equivalent queries. Use when implementing cache layers,
  optimizing LLM call costs, or when user mentions "semantic cache", "vector
  similarity", "cache hit rate", "cosine similarity", or "embedding cache".
metadata:
  version: "1.0"
  legacy-name: SEMANTIC_CACHING_PRIME
---

# SKILL: SEMANTIC_CACHING_PRIME

## DOMAIN EXPERTISE
You are an expert in **Semantic Caching**, a technique that uses vector similarity to serve cached responses for queries that are *semantically equivalent* even if syntactically different.

## KEY TEXTS & CONCEPTS
- **Vector Space:** 1536-dim (OpenAI) or 768-dim (Local) embedding space.
- **Cosine Similarity:** Metric $S_C(A, B) = \frac{A \cdot B}{\|A\| \|B\|}$.
- **Thresholding:** Cache hit if $S_C > 0.95$.
- **Hit Rate:** % of queries served from cache (Target > 40%).

## INSTRUCTION

### 1. The Core Pattern
Instead of `hash(query)`, use `embed(query)`.
```python
import numpy as np

class SemanticCache:
    def __init__(self, threshold=0.95):
        self.threshold = threshold
        self.vectors = [] # Matrix [N, D]
        self.responses = [] 

    def get(self, query_vec: np.array) -> str | None:
        if not self.vectors: return None
        
        # Calculate Similarities
        sims = np.dot(self.vectors, query_vec) / (np.linalg.norm(self.vectors, axis=1) * np.linalg.norm(query_vec))
        best_idx = np.argmax(sims)
        
        if sims[best_idx] > self.threshold:
            return self.responses[best_idx]
        return None
```

### 2. Integration with Flume
Use `FlumeEncoder` to project thoughts into the manifold before caching.
```python
query_z = flume.encode(thought)
cached_z = semantic_cache.search(query_z) 
```

### 3. Edge Cases
- **False Positives:** "Launch nuke" vs "Launch lunch" (High similarity, critical difference).
- **Negation:** "I love this" vs "I do not love this" (High similarity, opposite meaning).
- **Mitigation:** Use strict thresholds (0.98) for critical actions.

### 4. Actuator Integration (Compound Engineering)
When an `ActuatorSystem` executes a corrective action (e.g., `RestartService`), it must broadcast a **Cache Invalidation Signal**.
- **Reason**: The system state has physically changed; prior semantic states ("System is down") are now obsolete.
- **Pattern**:
    ```python
    await ActuatorSystem().execute(diagnosis)
    
## VERSION
v1.0
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        