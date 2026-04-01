# BlueQubit Submission: Little Dimple Challenge

This directory contains the code and methodology used to solve the 36-qubit "Little Dimple" circuit.

## Contents
- `peaked_solver.py`: The Matrix Product State (MPS) simulation engine with Manual Linear Routing.
- `verify_result.py`: Reclonstructs the qubit map and decodes sampled bitstrings.
- `DETAILED_SOLUTION.md`: In-depth technical explanation of the methodology and performance.
- `explanation.md`: Summary technical breakdown of the FLIER strategy.
- `solution.txt`: The identified heavy output bitstring.
- `P1_little_dimple.qasm`: Input quantum circuit.

## Requirements
- Python 3.10+
- `quimb`
- `numpy`
- `tqdm`
- `dill` or `pickle` (for state serialization)

Install dependencies:
```bash
pip install quimb numpy tqdm dill
```

## How to Reproduce

### 1. Run the Simulation
The simulation uses the FLIER (Bond 128) strategy with explicit renormalization.
```bash
python peaked_solver.py
```
This will generate `peaked_mps_final.dill` (the saved quantum state).

### 2. Verify the Bitstring
Once the simulation is complete, run the verifier to extract the heavy output:
```bash
python verify_result.py
```
This script deterministically replays the routing logic (15,000+ SWAPs) to unscramble the bits, performs a 250,000-shot SETI-protocol analysis, and prints the final sequence.

## Methodology Note
Our approach bypasses the $2^{36}$ state-vector memory requirement by using 1D Tensor Networks (MPS). The circuit's global connectivity is handled by a dynamic routing layer that swaps qubits into adjacency before gate application.
