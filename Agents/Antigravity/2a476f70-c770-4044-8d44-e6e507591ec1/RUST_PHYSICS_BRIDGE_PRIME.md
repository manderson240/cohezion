---
type: antigravity-artifact
session_id: 2a476f70-c770-4044-8d44-e6e507591ec1
date: 2026-03-04
title: "Rust Physics Bridge Prime"
aspect: doer
neural:
  activation: 0.333
  stage: embryo
  cluster: Agents
---

# SKILL: RUST_PHYSICS_BRIDGE_PRIME

## DOMAIN EXPERTISE
**High-Performance Simulation Bridges (Python <-> Rust)**
Integrating safe, concurrent Rust kernels into the Python-based Cohezion ecosystem to handle N-body physics, Quark Gluon Plasma flows, and Lattice QCD calculations at speed.

## KEY TEXTS & CONCEPTS
*   **PyO3**: The standard for Rust bindings in Python.
*   **Maturin**: Build system for Rust crates to Python wheels (compatible with `uv`).
*   **Zero-Copy Buffer Sharing**: Sharing NumPy arrays with Rust `ndarray` without serialization overhead.
*   **Rayon**: Rust's data-parallelism library for multi-core scaling.

## ARCHITECTURE

```mermaid
graph LR
    A[Python Agent (Logic)] -->|Action Vector| B(Rust Bridge);
    B -->|Physics Update| C{Rust QGP Engine};
    C -->|Sim Step| C;
    C -->|State Tensor| B;
    B -->|NumPy View| A;
```

## INSTRUCTION: IMPLEMENTING A BRIDGE

### 1. The Rust Crate (`src/lib.rs`)
```rust
use pyo3::prelude::*;
use numpy::PyReadwriteArray2;

#[pyclass]
struct QGPSimulator {
    temperature: f64,
    grid: Vec<f64>,
}

#[pymethods]
impl QGPSimulator {
    #[new]
    fn new(temp: f64) -> Self {
        QGPSimulator { temperature: temp, grid: vec![0.0; 1000] }
    }

    fn step(&mut self, _py: Python<'_>, mut array: PyReadwriteArray2<f64>) {
        // High-speed hydrodynamics calculation
        let slice = array.as_array_mut();
        // ... Rayon parallel update ...
    }
}
```

### 2. The Python Interface
```python
from cohezion.physics.rust_core import QGPSimulator
import numpy as np

sim = QGPSimulator(200.0)
state_grid = np.zeros((100, 100))
sim.step(state_grid) # Zero-copy update
```

## STRATEGY: WHEN TO MIGRATE
*   **Pure Logic/IO**: Stay in **Python** (Agents, Networking).
*   **O(N^2) Interactions**: Migrate to **Rust** (Gravity, QGP Flow, Attention Masks).
*   **Web Dashboard**: Use **Typescript/React** (as currently done in `apps/`).

## VERSION
v1.0 (Hypothetical Design)

## SEE ALSO
*   [SKILL: UNIVERSE_DESIGN_PRIME](UNIVERSE_DESIGN_PRIME.md) (Requires this speed for 10k agents)

## Related Vault Notes

- [[cohezion]]
- [[quark-gluon-plasma]]
