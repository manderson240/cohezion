---
type: antigravity-artifact
session_id: 9beaa943-900b-4596-aedd-2d40c52c8831
date: 2026-03-04
title: "Implementation Plan"
aspect: doer
neural:
  activation: 0.342
  stage: embryo
  cluster: Agents
---

# Implementation Plan: 2D Tensor Network (PEPS) Solver

## Goal
Optimize the 36-qubit "Little Dimple" circuit simulation by moving from a 1D Matrix Product State (MPS) to a 2D Tensor Network (PEPS-like) representation. This aims to reduce the massive SWAP overhead (15,000+ gates) encountered in the 1D approach.

## User Review Required
> [!IMPORTANT]
> The circuit connectivity is extremely dense (mean qubit degree ~80). A 2D grid mapping will still require some routing or long-range contractions. I will use a graph-based layout (Spectral Embedding) to map qubits to a 6x6 grid to minimize the average Manhattan distance of gates.

## Proposed Changes

## Proposed Changes

### Environment Layer
#### [MODIFY] [venv](file:///home/mike-anderson/dev/cohezion/bluequbit_challenge/little_dimple_submission/venv/)
- Upgrade to **PyTorch 2.10.0** to leverage new tensor-core optimized contraction (TOC) kernels and improved `torch.compile` latency.

### Quantum Simulation Layer
#### [NEW] [peps_solver.py](file:///home/mike-anderson/dev/cohezion/bluequbit_challenge/little_dimple_submission/peps_solver.py)
- **2D Mapping**: Use `networkx` to find an optimal 6x6 grid embedding.
- **Quimb 2D Engine**: Initialize a `qtn.TensorNetwork` and use **PyTorch 2.10.0** as the contractor backend for GPU/multi-core acceleration.
- **Contraction Optimization**: Use `cotengra` with `kahypar` or `greedy` methods to find efficient contraction paths for the 2D lattice.
- **Resource Guard**: Integrate `psutil` to monitor memory usage. If >= 100GB, trigger emergency SVD truncation or slicing.

### Verification Layer
#### [MODIFY] [mission_manager.py](file:///home/mike-anderson/dev/cohezion/bluequbit_challenge/little_dimple_submission/mission_manager.py)
- Update to include `peps_solver.py` in the experiment rotation.
- Increase timeout for high-bond 2D runs.

## Verification Plan

### Automated Tests
1. **Connectivity Check**: Verify the 6x6 mapping reduces the total "routing distance" compared to the 1D line.
   - Command: `python3 -c "import peps_solver; peps_solver.analyze_mapping()"`
2. **Small Scale Test**: Run a 12-qubit version (first 100 gates) to verify the 2D TN produces the same bitstrings as MPS.
3. **Full Run**: Execute the 36-qubit simulation with Bond Dimension 64 to establish a 2D baseline.
   - Command: `MAX_BOND=64 ./venv/bin/python3 peps_solver.py`

### Manual Verification
- Monitor `top` or `mission.log` to ensure memory stays below 110GB.
