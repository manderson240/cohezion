# SKILL: ARC_TTT_DIHEDRAL_AND_GO_EXPLORE_RHAE_PRIME

## DOMAIN EXPERTISE
Test-Time Training (TTT) on D4 dihedral demonstration symmetries for static abstract reasoning (ARC-AGI-2) and Hierarchical Go-Explore with 64-bit SplitMix64 Zobrist hashing and BFS macro-action compilation under quadratic RHAE score decay (ARC-AGI-3).

## KEY TEXTS & CONCEPTS
- D4 Dihedral Group Symmetries: Augmenting demonstration pairs 8x to align spatial manifolds during test-time gradient adaptation
- L2 Anchor Regularization: Bounding low-rank adapter updates (W_q, W_v) with alpha * ||theta - theta_0||^2 to prevent catastrophic forgetting
- Relative Human Action Efficiency (RHAE): Quadratic penalty Score = min(1.15, (H/A)^2) necessitating macro-action pathfinding compression
- 64-bit SplitMix64 Zobrist Hashing: O(1) transposition tables enabling >15M state evals/sec on Kaggle CPU runners

## INSTRUCTION
1. **Generate D4 dihedral group transformations (r0, r90, r180, r270, sh, sv, sd, sad) for all demo pairs**
```python
def zobrist_hash(grid, table):
    h = 0
    for r in range(grid.shape[0]):
        for c in range(grid.shape[1]):
            h ^= table[r, c, grid[r, c]]
    return h
```

## VERSION
v1.0

## SEE ALSO
- KAGGLE_COMPETITIVE_EVALUATION_PRIME
- TWO_PARTY_CRYPTOGRAPHIC_IVV_PRIME
