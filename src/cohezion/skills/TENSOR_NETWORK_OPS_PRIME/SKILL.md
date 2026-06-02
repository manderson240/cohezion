---
name: TENSOR_NETWORK_OPS_PRIME
description: HPC for quantum simulation and LLM compression using tensor networks, targeting memory-constrained (VRAM/RAM < 80GB) hardware. Covers LLM embedding compression in the TensorGPT style (reshape token vectors into high-order tensors, SVD-factorize into MPS cores at a target bond dimension), Matrix Product States / Tensor-Train decomposition, Saten sparse-augmented networks, and quantum circuit simulation via cotengra/quimb contraction-path optimization with kahypar partitioning and index slicing. Pins numpy 1.26.4 (<2.0 for Numba).
---

# SKILL: TENSOR_NETWORK_OPS_PRIME

## DOMAIN EXPERTISE
High-Performance Computing (HPC) for Quantum Simulation and **LLM Compression** using Tensor Networks. Focus on memory-constrained (VRAM/RAM < 80GB) optimization of deep quantum circuits and massive embedding layers via Matrix Product States (MPS) and Tensor-Train (TT) Decomposition.

## KEY TEXTS & CONCEPTS
- **Matrix Product States (MPS)**: A physical representation of TT-Decomposition where high-dimensional tensors are factorized into a chain of low-rank cores.
- **TensorGPT**: A 2026 SOTA method for compressing LLM embedding layers by treating each token vector as an independent MPS, achieving up to 65x compression.
- **Bond Dimension (Rank)**: The primary hyperparameter controlling the trade-off between expressivity and compression ratio.
- **Cotengra/Quimb**: Foundation libraries for contraction path optimization and tensor-train manipulation.
- **Saten (Sparse Augmented Tensor Networks)**: A hybrid approach that captures global low-rank structure via MPS while preserving high-rank semantic outliers (theorems/rare tokens) via a sparse matrix.

## INSTRUCTION

### 1. LLM Embedding Compression (TensorGPT Style)
To fit massive reasoning models into constrained VRAM (e.g., Kaggle H100):
1. **Reshape**: Map the high-dimensional token vector $v \in \mathbb{R}^d$ into a high-order tensor $\mathcal{T}$.
2. **Factorize**: Use Singular Value Decomposition (SVD) to decompose $\mathcal{T}$ into MPS cores with a target bond dimension $\chi$.
3. **Compress**: Discard singular values below a threshold $\epsilon$ to achieve the desired compression ratio (target 2x-4x for zero reasoning loss).

### 2. Quantum Circuit Simulation (MPS Baseline)
For circuits > 30 qubits:
1. **Contraction Path**: Use `cotengra` with `kahypar` partitioning to find the optimal elimination order.
2. **Slicing**: Trade time for space by slicing high-degree indices.
   ```python
   opt = ctg.ReusableHyperOptimizer(slicing_opts={'target_size': 2**28})
   ```
3. **Verification**: Use the Pauli-Path Simulator as a 'Zero-Cost Verifier' to confirm peaks in QPU candidates.

### 3. Environment (2026 SOTA)
- **Numpy**: `1.26.4` (Strictly `< 2.0` for Numba compatibility).
- **Libraries**: `quimb`, `cotengra`, `kahypar`, `optuna`.

## VERSION
v1.1 (Neuro-Symbolic & MPS Optimized)

## SEE ALSO
- `MATH_REASONING_SWARM_PRIME`
- `KAGGLE_BLACKWELL_RUNNER_PRIME`
