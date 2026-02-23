---
title: Holographic Projection Fallback: Dimensionality Reduction Requires Singular Matrix Guard
date: 2026-02-23
severity: MEDIUM
category: ml
tags: [ml, dimensionality-reduction, linear-algebra, fallback, vae]
status: validated
---

# Lesson: Holographic Projection Fallback: Dimensionality Reduction Requires Singular Matrix Guard

## Context

Holographic projection fails when the covariance matrix is singular or near-singular. This occurs with small batches or identical inputs during VAE training.

## Core Learning

**All holographic/projection operations must include a fallback for singular matrix cases.**

### Pattern
```python
def holographic_project(vectors, target_dim):
    try:
        cov = np.cov(vectors.T)
        cov += np.eye(cov.shape[0]) * 1e-6  # epsilon regularization
        eigenvalues, eigenvectors = np.linalg.eigh(cov)
        projection = eigenvectors[:, -target_dim:]
        return vectors @ projection
    except np.linalg.LinAlgError:
        logger.warning("Holographic projection failed -- using truncation fallback")
        return vectors[:, :target_dim]
```

## Recommendations

### Do
- Always add epsilon regularization to covariance matrices
- Implement a fallback projection (PCA or truncation)
- Check for NaN in projection output before continuing

### Don't
- Assume projection will succeed for all batch sizes
- Let LinAlgError propagate through the pipeline

## Related Concepts

- [[meta-learning]] - Projection stability enables reliable meta-learning across sessions

## Validation

**Discovered**: Feb 2026 during first VAE training run
**Status**: Validated
