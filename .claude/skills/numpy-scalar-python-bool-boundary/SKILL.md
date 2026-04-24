---
name: numpy-scalar-python-bool-boundary
description: |
  Fix for assertion failures like `np.True_ is True → False` or
  `isinstance(np.True_, bool) → False` when a function exposes a public
  boolean / float API but computes it via numpy math.
  Use when: (1) `assert result is True` fails but the value "looks" true,
  (2) `isinstance(x, bool)` returns False on something that looks like a bool,
  (3) `isinstance(x, float)` returns False on a numpy scalar,
  (4) type-check contract tests fail for a function that returns dict values
      from numpy operations (norms, dot products, tensor comparisons).
  Root cause: comparisons like `np_val > 0.5` return `np.True_`, not Python `True`.
author: Claude Code
version: 1.0.0
---

# numpy Scalar → Python bool/float Boundary

## Problem

A public API returns a dict/tuple of "simple" values (bools, floats) but
computes them from numpy. The numpy scalars are *duck-typed* compatible with
Python primitives — they pass `bool(x)`, `float(x)`, truthy-in-if, `==` — but
they **fail identity and isinstance checks**:

```python
>>> import numpy as np
>>> x = np.float64(0.7) > 0.5
>>> x
True
>>> type(x)
<class 'numpy.bool_'>
>>> x is True
False
>>> isinstance(x, bool)
False
>>> bool(x) is True
True
```

Tests that use `assert result is True` or `assert isinstance(x, bool)` to
verify a public contract will fail opaquely. The value *looks* correct in
any print, so diagnosis is tricky.

## Trigger Conditions

- `assert x is True` fails with `AssertionError: assert np.True_ is True`.
- `isinstance(result["flag"], bool)` returns False.
- `isinstance(result["coherence"], float)` returns False on a value that came
  from `np.linalg.norm`, `tensor.mean()`, or another numpy-producing call.
- Function docstring promises to return `float` / `bool`, test asserts the type.
- The code path computes via numpy/torch and comparisons like `value > threshold`,
  where `value` was silently promoted to `np.float64` upstream.

## Solution

Cast at the public API boundary, once, at the return site. Don't scatter
`float()` / `bool()` calls throughout the logic — just convert where the
contract is exposed:

```python
def check_threshold(self) -> dict[str, float | bool | str]:
    # ... compute via numpy ...
    coherence = float(self.coherence_score())  # may return np.float64

    # Comparisons on numpy scalars produce np.bool_ — explicitly cast.
    spontaneous = bool(free_energy < 0.0)
    precipitate = bool(coherence > 0.5)

    return {
        "precipitate": precipitate,       # now a real Python bool
        "coherence": coherence,           # now a real Python float
        "shannon_entropy_bits": float(shannon_h),
        "free_energy": float(free_energy),
        "spontaneous": spontaneous,
        "mechanism": "...",
    }
```

### Don't do this

```python
# WRONG — propagates numpy types into the contract
return {
    "precipitate": coherence > 0.5,  # np.True_ or np.False_
    "coherence": self.coherence_score(),  # possibly np.float64
}
```

### Alternative: numpy's own `.item()`

For a single numpy scalar, `.item()` returns the Python primitive:

```python
>>> np.float64(0.7).item()
0.7
>>> type(np.float64(0.7).item())
<class 'float'>
>>> np.bool_(True).item()
True
>>> isinstance(np.bool_(True).item(), bool)
True
```

Use `.item()` when you know the variable is always a numpy scalar; use
`float()`/`bool()` when the source might be either native Python or numpy.

## Verification

```python
result = thing.check_threshold()
assert result["flag"] is True            # identity, not equality
assert isinstance(result["value"], bool) # strict type check
assert isinstance(result["score"], float)
```

All three should pass, independent of whether the inputs were numpy or Python.

## Real-World Example (Cohezion)

**File:** `src/cohezion/universe/engine.py::AxiomaticState.check_precipitation()`

**Symptom:** Tests from `tests/universe/test_precipitation_gate.py` failed:
```
AssertionError: Should not precipitate at 0.0 coherence
assert np.False_ is False
```
```
AssertionError: assert False
  +  where False = isinstance(np.True_, bool)
```

**Root cause:** `coherence_score()` composes a float via
`spinor.hiho_deviation` — the spinor's hiho_deviation is derived from SU(2)
Pauli matrix expectation values via numpy/torch, so `coherence_score()`
returns `np.float64`. Subsequent `coherence > 0.5` produces `np.bool_`.

**Fix:** explicit `float()` / `bool()` casts at the return dict:

```python
coherence = float(self.coherence_score())
hiho_stability = float(max(0.0, min(1.0, 1.0 - abs(coherence - 0.5) * 2.0)))
spontaneous = bool(free_energy < 0.0)
precipitate = bool(coherence > 0.5)
```

All 12 precipitation gate tests green after the change.

## References

- numpy scalar types: https://numpy.org/doc/stable/reference/arrays.scalars.html
- `numpy.bool_` vs Python `bool`: https://numpy.org/doc/stable/reference/generated/numpy.bool_.html
- `.item()` for extracting Python scalars: https://numpy.org/doc/stable/reference/generated/numpy.ndarray.item.html
