# SKILL: TENSOR_NETWORK_OPS_PRIME

## DOMAIN EXPERTISE
High-Performance Computing (HPC) for Quantum Simulation using Tensor Networks. Focus on memory-constrained (RAM < 1TB) simulation of deep quantum circuits (30-100+ qubits) via contraction path optimization.

## KEY TEXTS & CONCEPTS
- **Quimb**: Quantum Information Many-Body library. Primary interface for TN construction.
- **Cotengra**: Contraction Tree Optimizer. Essential for finding efficient contraction paths (`flops` vs `write` cost).
- **Kahypar**: Karlsruhe Hypergraph Partitioning. The gold-standard graph partitioner for variable elimination ordering in TNs.
- **Slicing**: Technique to cut high-degree edges (indices) to fit a contraction in memory, trading time (summing over cuts) for space.
- **Version Pinning**: Critical due to Numba/LLVM/Numpy ABI compatibility issues.

## INSTRUCTION

### 1. Environment Stabilization
The stack is fragile. Use this exact dependency graph:
- **Python**: 3.10 - 3.12 (3.13 is bleeding edge, use caution)
- **Numpy**: `1.26.4` (Strictly `< 2.0` due to Numba constraints as of early 2026)
- **Numba**: `> 0.60.0`
- **Quimb**: `> 1.8.0`
- **Cotengra**: `> 0.6.0`
- **Kahypar**: `> 1.3.0` (Linux only wheels usually available)
- **Optuna**: Required for `cotengra`'s `auto-hq` optimization.

```bash
uv pip install "numpy==1.26.4" numba quimb cotengra kahypar optuna scipy networkx
```

### 2. Validation Script
Always verify the ABI link before running heavy jobs:
```python
import numpy, numba, kahypar
import quimb.tensor as qtn
print(f"Numpy: {numpy.__version__}") # Must be 1.26.x
# Trigger JIT
@numba.jit(nopython=True)
def test(): return 1
assert test() == 1
```

### 3. Simulation Strategy (Memory Constrained)
For circuits > 30 qubits:
1. **Estimate**: Use `cotengra` to build a path without contracting.
   ```python
   opt = ctg.ReusableHyperOptimizer(methods=['kahypar'], max_repeats=128)
   tree = opt.search(inputs, output, size_dict)
   print(f"Max Memory: {tree.max_size() / 1e9} GB")
   ```
2. **Slice**: If `Max Memory` > limit, force slicing.
   ```python
   opt = ctg.ReusableHyperOptimizer(..., slicing_opts={'target_size': 2**28}) # ~4GB slice target
   ```
3. **Contract**: Use `joblib` or similar for parallel slice evaluation if needed.

## VERSION
v1.0

## SEE ALSO
- [Cotengra Documentation](https://cotengra.readthedocs.io/)
- [Quimb Tensor Networks](https://quimb.readthedocs.io/)
