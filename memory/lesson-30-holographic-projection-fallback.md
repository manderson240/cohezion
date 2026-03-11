---
title: Holographic Projection Fallback: Dimensionality Reduction Requires Singular Matrix Guard
date: 2026-02-23
severity: MEDIUM
category: ml
cost_of_forgetting: "LinAlgError crashes pipeline during inference; NaN propagation corrupts downstream embeddings"
tags: [ml, dimensionality-reduction, linear-algebra, fallback, vae]
status: validated
aspect: knower
neural:
  activation: 0.449
  stage: growing
  cluster: lessons
---

# Lesson: Holographic Projection Fallback: Dimensionality Reduction Requires Singular Matrix Guard

## Context

During the first Cohezion VAE training run in February 2026, the holographic projection step (a dimensionality reduction technique that projects high-dimensional embeddings into a lower-dimensional space using covariance-based projection) crashed with `numpy.linalg.LinAlgError: Singular matrix`. The crash occurred on a batch of size 3 where two of the three input vectors were near-identical, producing a near-singular covariance matrix.

## Problem

Holographic projection uses the eigendecomposition of the covariance matrix to find optimal projection directions. This fails in two specific conditions:

1. **Small batches**: With fewer vectors than dimensions, the covariance matrix is rank-deficient (more columns than independent rows), making it singular.
2. **Identical/near-identical inputs**: Duplicate or near-duplicate vectors in a batch reduce the effective rank, producing zero or near-zero eigenvalues.

Both conditions are common during training (early batches are small) and during inference (repeated inputs from cache). The crash is unrecoverable without error handling, and even with error handling, NaN values can propagate from near-singular matrices through the rest of the pipeline.

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

## Solution

A three-layer defense was implemented:

1. **Epsilon regularization**: Add `np.eye(n) * 1e-6` to the covariance matrix before eigendecomposition. This ensures the matrix is always positive definite, preventing singular matrix errors in most cases.
2. **Exception handler with fallback**: If eigendecomposition still fails, fall back to simple truncation (take the first N dimensions). This is lower quality but always works.
3. **NaN check**: After projection, check the output for NaN values. If any are found, fall back to truncation.

## Prevention

- **Always regularize covariance matrices**: Add epsilon to the diagonal before any decomposition
- **Implement a fallback for every projection**: Truncation is the simplest always-correct fallback
- **Check for NaN in output**: Near-singular matrices may produce valid decompositions with NaN-contaminated results
- **Test with edge cases**: Small batches (1-3 vectors) and identical inputs should be part of the test suite

## Cost of Forgetting

- **Pipeline crash**: LinAlgError terminates the entire training or inference pipeline
- **NaN propagation**: Near-singular results produce NaN that silently corrupts all downstream operations
- **Small batch fragility**: Early training batches and inference on repeated inputs trigger the failure regularly

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
- [[concept-optimization]] - singular matrix guard with epsilon regularization is the key optimization
- [[neural-network-architecture]] - dimensionality reduction is a foundational neural network operation
- [[machine-learning-optimization]] - epsilon regularization and fallback projections are standard ML robustness techniques

## Validation

**Discovered**: Feb 2026 during first VAE training run -- batch size 3 with near-identical inputs
**Status**: Validated -- epsilon regularization and fallback now standard for all projection operations
