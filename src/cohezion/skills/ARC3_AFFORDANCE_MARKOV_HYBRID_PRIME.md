# SKILL: ARC3_AFFORDANCE_MARKOV_HYBRID_PRIME

## DOMAIN EXPERTISE
Interactive Grid World Affordance Search & Soft Monadic Markov Policy

## KEY TEXTS & CONCEPTS
- Monadic Markov cycle evasion with Zobrist 64-bit state hashing
- Soft affordance navigation: non-background entities as interactive goals rather than rigid obstacles
- Bounded lookahead advice bonus (-15.0) preserving dynamic cycle and orbit trap penalties
- Avoidance of the obstacle trap in discrete interactive environment search

## INSTRUCTION
1. **Compute 64-bit SplitMix64 Zobrist hash of input frame for O(1) state lookup.**
```python
def hash_frame(frame_layers: list) -> int:
    colors = np.clip(grid, 0, 9)
    return int(np.bitwise_xor.reduce(ZOBRIST_TABLE[:h, :w, :][r_idx, c_idx, colors].ravel()))
```

2. **Identify foreground connected components sorted by rarity ascending.**
```python
def soft_bfs_suggested_action(grid: np.ndarray, start: tuple, goal: tuple, bg_color: int) -> int:
    # 0-1 BFS with soft edge cost 1 for background/goal, 2 for soft obstacle/item
    ...
```

3. **Use 0-1 BFS with soft edge costs (1 for background/target, 2 for non-background entities) to derive single-step directional advice.**
```python
# Integrate directional advice as soft bonus into candidate action scoring
preferred_scores[suggested_act] -= 15.0
```

## VERSION
v0.1

## SEE ALSO
- KAGGLE_COMPETITIVE_EVALUATION_PRIME
- TWO_PARTY_CRYPTOGRAPHIC_IVV_PRIME
