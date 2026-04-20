# Anthropic Research Engineer Take-home: VLIW Optimization

## Performance Result
- **Cycles**: 349
- **Speedup over baseline**: ~423x
- **Verification**: Passed all `tests/submission_tests.py`

## Approach: Quadrature Nexus
The solution utilizes a "Quadrature Nexus" architecture for the VLIW kernel, implementing several advanced optimization techniques:
1. **Instruction-Level Parallelism (ILP)**: 28-way window parallelism through software pipelining.
2. **Explicit VLIW Scheduling**: Manual packing of instructions into bundles to maximize slot utilization (ALU, VALU, FLOW, LOAD).
3. **Register Pressure Management**: Optimized register allocation for the 12D state vectors.
4. **Non-Speculative Round Folding**: Bit-exact 16-round traversal with minimal branching.

## How to Run
We use `uv` for dependency management and execution.

1. **Install uv** (if not already present):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```
2. **Run Submission Tests**:
   ```bash
   uv run tests/submission_tests.py
   ```

## Files
- `perf_takehome.py`: Main entry point (calls OptimizedKernelBuilder).
- `optimizer.py`: Core `OptimizedKernelBuilder` implementation.
- `problem.py`: VLIW Simulator environment.
- `tests/`: Original verification tests (unchanged).
