# RETROSPECTIVE: Phase 16 - FLUME Rust Acceleration

**Date**: 2026-02-01
**Topic**: Parallel Systems & Foreign Function Interface (FFI)
**Phase**: S16 (Rust Acceleration)

## 1. The Challenge
The FLUME physics engine (calculating 12D manifold trajectories) became the bottleneck. Python's GIL prevented true parallelism, capping us at ~150 simulated trajectories per second. To achieve "Swarm Intuition" (MCTS), we needed >10,000 trajectories/sec.

## 2. Issues Encountered & Solutions

### A. The Byte Barrier
**Problem**: Marshaling data between Python and Rust has overhead. Initial ports were *slower* due to serialization costs of complex objects.
**Solution**: **Zero-Copy Arrays**. We switched to passing raw `numpy` buffers (via `PyO3` + `numpy` crate) instead of pickling Python objects. We essentially treat the Python layer as a "Command & Control" dashboard and the Rust layer as the "Engine Room."

### B. Parallelism Safety
**Problem**: Rust's borrow checker fought with our desire for shared mutable state in the "Universe" object.
**Solution**: **Rayon Parallel Iterators**. We restructured the simulation to be "stateless per step." Instead of modifying a global universe, each trajectory calculates its next step based on a read-only snapshot.
```rust
// The core unlock
trajectories.par_iter_mut().for_each(|t| {
    t.evolve(snapshot);
});
```

### C. Build Complexity
**Problem**: Distributing a mixed Python/Rust project is painful.
**Solution**: **Maturin**. We adopted `maturin` as the build backend, allowing us to `pip install .` and have the Rust crate compiled automatically into the python environment.

## 3. Metrics & Validation
- **Benchmark**: 1000 Trajectories x 100 Steps.
- **Python Time**: 7.40s
- **Rust Time**: 0.52s
- **Speedup**: **14.09x**
- **Correctness**: 12D output vectors match Python baseline to 1e-6 tolerance.

## 4. Key Takeaways
- **Rust is Logic, Python is Glue**: Keep the heavy math in Rust. Keep the agent prompts in Python.
- **Rayon is Magic**: `par_iter()` is the single highest ROI line of code in the project.
- **Type Safety**: Rust forced us to handle edge cases (div-by-zero in manifolds) that Python silently ignored (`NaN` propagation).
