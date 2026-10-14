---
name: arc2-mdl-program-synthesis-prime
description: "Minimum Description Length (MDL) Occam program synthesis, zero-error training verification, and non-destructive attempt-2 ensemble injection for ARC-AGI-2."
version: v0.1
---

# SKILL: ARC2_MDL_PROGRAM_SYNTHESIS_PRIME

## DOMAIN EXPERTISE
Neuro-symbolic program synthesis for ARC-AGI-2 grid puzzles combining parameter-free geometric primitives, fitted terminals, exact training set verification, Minimum Description Length (MDL) Occam penalty pruning, and strict non-destructive Attempt-2 ensemble placement.

## KEY TEXTS & CONCEPTS
* **Composed Program Space**: Expressing hypotheses as $p = \tau \circ \pi_k \circ \dots \circ \pi_1$ (depth $k \le 2$) combining parameter-free transforms $\pi$ with fitted terminals $\tau$.
* **Zero-Error Hard Verification**: Enforcing strict zero training error $L(p) = \sum_i \mathbb{I}[p(x_i) \ne y_i] = 0$ on all demonstration pairs.
* **MDL Occam-Posterior Weighting**: Weighting programs by description complexity $P(p|\mathcal{D}) \propto 2^{-\ell(p)} \cdot \mathbb{I}[L(p) = 0]$.
* **Semantic Behavior Grouping**: Aggregating programs by their distinct test prediction outputs on $x^*$ to prevent redundant syntax from inflating candidate votes.
* **Monotonic Improvement Invariant**: Strictly leaving neural model $\text{attempt\_1}$ intact, only substituting $\text{attempt\_2}$ when synthesis confidence $c \ge \theta$ and $\hat{y} \ne \text{attempt\_1}$.

## INSTRUCTION

1. **Primitive & Terminal Specification**:
```python
import numpy as np

def rot90(grid: np.ndarray) -> np.ndarray:
    return np.rot90(grid, -1)

def flip_h(grid: np.ndarray) -> np.ndarray:
    return np.fliplr(grid)

def gravity_fall(grid: np.ndarray, direction: int = 0) -> np.ndarray:
    """Drops non-zero cells in one of 4 directions (0: down, 1: up, 2: left, 3: right)."""
    g = np.array(grid, dtype=int)
    if direction == 1: g = np.flipud(g)
    elif direction == 2: g = g.T
    elif direction == 3: g = np.fliplr(g.T)

    H, W = g.shape
    out = np.zeros_like(g)
    for c in range(W):
        col = g[:, c]
        non_zeros = col[col != 0]
        out[H - len(non_zeros):, c] = non_zeros

    if direction == 1: out = np.flipud(out)
    elif direction == 2: out = out.T
    elif direction == 3: out = out.T[:, ::-1]
    return out
```

2. **Terminal Fitting (Consistent Color Map / CA)**:
```python
def fit_color_map(pairs: list[tuple[np.ndarray, np.ndarray]]) -> tuple[dict[int, int] | None, float]:
    """Fits consistent color mapping; returns None if inconsistent."""
    mapping = {}
    for x, y in pairs:
        if x.shape != y.shape:
            return None, 999.0
        for u, v in zip(x.ravel(), y.ravel()):
            if u in mapping and mapping[u] != v:
                return None, 999.0
            mapping[u] = v

    # Bit cost: ~3.3 bits per non-identity mapped color
    non_ident = sum(1 for k, v in mapping.items() if k != v)
    if non_ident == 0:
        return None, 999.0 # Reject trivial identity
    cost_bits = 6.0 + non_ident * 3.32
    return mapping, cost_bits
```

3. **Synthesis Engine with MDL Weighting**:
```python
def synthesize_mdl_program(train_pairs: list[tuple[np.ndarray, np.ndarray]],
                           test_input: np.ndarray,
                           min_conf: float = 0.5) -> tuple[np.ndarray | None, float]:
    """
    Synthesizes exact matching program and returns best test prediction with confidence.
    """
    candidates = [] # list of (output_grid, bit_cost)

    # 1. Evaluate Direct Color Map
    cmap, bits = fit_color_map(train_pairs)
    if cmap is not None:
        test_out = np.vectorize(lambda c: cmap.get(c, c))(test_input)
        candidates.append((test_out, bits))

    # 2. Evaluate Primitives + Color Map
    primitives = [
        ("rot90", rot90, 6.0),
        ("rot180", lambda g: np.rot90(g, 2), 6.0),
        ("flip_h", flip_h, 6.0),
        ("grav_down", lambda g: gravity_fall(g, 0), 8.0),
    ]

    for name, prim, prim_bits in primitives:
        # Transform inputs
        transformed_pairs = [(prim(x), y) for x, y in train_pairs]
        cmap_p, cmap_bits = fit_color_map(transformed_pairs)
        if cmap_p is not None:
            t_test = prim(test_input)
            test_out = np.vectorize(lambda c: cmap_p.get(c, c))(t_test)
            candidates.append((test_out, prim_bits + cmap_bits))

    if not candidates:
        return None, 0.0

    # Group by identical output grids (semantic equivalence)
    output_groups = {}
    for out_grid, bits in candidates:
        key = out_grid.tobytes()
        weight = 2.0 ** (-bits)
        if key not in output_groups:
            output_groups[key] = {"grid": out_grid, "weight": weight}
        else:
            output_groups[key]["weight"] = max(output_groups[key]["weight"], weight)

    total_weight = sum(g["weight"] for g in output_groups.values())
    best_group = max(output_groups.values(), key=lambda g: g["weight"])
    confidence = best_group["weight"] / total_weight

    if confidence >= min_conf:
        return best_group["grid"], confidence
    return None, confidence
```

4. **Non-Destructive Monotonic Attempt-2 Placement**:
```python
def apply_monotonic_invariant(neural_attempt1: list[list[int]],
                              neural_attempt2: list[list[int]],
                              synthesized_solution: np.ndarray | None,
                              confidence: float,
                              conf_threshold: float = 0.5) -> tuple[list[list[int]], list[list[int]]]:
    """
    Enforces Monotonic Improvement Invariant:
    - attempt_1 is strictly unchanged.
    - attempt_2 is replaced iff DSL has high confidence and differs from attempt_1.
    """
    final_attempt1 = neural_attempt1 # Inviolate
    final_attempt2 = neural_attempt2

    if synthesized_solution is not None and confidence >= conf_threshold:
        synth_list = synthesized_solution.tolist()
        if synth_list != neural_attempt1:
            final_attempt2 = synth_list

    return final_attempt1, final_attempt2
```

## VERSION
v0.1

## SEE ALSO
- KAGGLE_STRICT_MONOTONIC_ATTEMPT_ENSEMBLE_PRIME.md
- ARC3_GO_EXPLORE_AFFORDANCE_PRIME.md
- RETROSPECTIVE_SKILL.md
