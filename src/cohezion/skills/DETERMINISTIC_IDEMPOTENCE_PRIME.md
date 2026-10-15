# SKILL: DETERMINISTIC_IDEMPOTENCE_PRIME

## DOMAIN EXPERTISE
Mathematical and empirical deterministic idempotence verification across hyper-dimensional manifold projections, Bayesian and Copula parameter optimization, out-of-fold adversarial validation, synthetic task AST compilation, dead-end ledger graph linters, and two-party cryptographic attestation. Enforces strict bitwise invariance $\mathcal{T}^k(x) = \mathcal{T}(x)$ and cryptographic SHA-256 identity across all local silicon and agentic pipelines.

## KEY TEXTS & CONCEPTS
- **Idempotence Operator Axiom**: An operator $\mathcal{T}: \mathcal{X} \to \mathcal{X}$ is idempotent if and only if $\forall x \in \mathcal{X}, \mathcal{T}(\mathcal{T}(x)) = \mathcal{T}(x)$. By mathematical induction, $\forall k \ge 1, \mathcal{T}^k(x) = \mathcal{T}(x)$.
- **Cryptographic Bitwise Invariance**: Under deterministic execution, the SHA-256 digests of outputs across $k$ evaluations satisfy $\text{SHA-256}(\mathcal{T}^k(x)) = \text{SHA-256}(\mathcal{T}(x))$ with bitwise delta $\Delta_{\max} = 0.00\text{e}+00$.
- **Poincaré Ball Idempotent Retraction**: The metric projection $\Pi_{\mathbb{B}}(x) = \min(1, \frac{1 - \epsilon}{\|x\|}) x$ on the open conformal unit ball $\mathbb{B}^n$ guarantees $\Pi_{\mathbb{B}}(\Pi_{\mathbb{B}}(x)) \equiv \Pi_{\mathbb{B}}(x)$.
- **Deterministic Nelder-Mead Copula Convergence**: Seeded loss optimization converges to the exact identical global minimizer $\mathbf{w}^*$ with zero floating-point drift across runs.
- **Adversarial Validation Determinism**: Splitting, shuffling, and evaluating out-of-fold classifier distributions yield identical ROC-AUC scores and risk classifications.
- **Procedural AST Determinism**: Deterministic generator transformations $\mathcal{G}_{\text{DSL}}(S_0, \text{seed})$ compile bitwise identical abstract syntax trees.
- **Dead-End Linter Idempotence**: Static AST graph inspection returns bitwise identical violation sets $\mathcal{V}(P)$ across successive evaluations without non-deterministic side-effects.
- **Two-Party Adversarial IV&V Invariance**: Red-team exploration across state spaces (e.g., 10,000 Zobrist states) produces identical non-collision verification digests.

## INSTRUCTION

1. Formulate and verify an idempotent projection $\mathcal{T}(x)$:
   ```python
   import numpy as np
   import hashlib

   def poincare_project(x: np.ndarray, max_norm: float = 0.999) -> np.ndarray:
       norm = np.linalg.norm(x, axis=-1, keepdims=True)
       scale = np.where(norm >= max_norm, max_norm / (norm + 1e-12), 1.0)
       return x * scale

   x0 = np.random.RandomState(42).randn(10, 16) * 2.0
   x1 = poincare_project(x0)
   x2 = poincare_project(x1)

   diff = np.max(np.abs(x1 - x2))
   assert diff == 0.0, f"Non-zero idempotence drift: {diff}"
   ```

2. Verify cryptographic SHA-256 digest identity across $k$ iterations:
   ```python
   def compute_digest(data: np.ndarray) -> str:
       return hashlib.sha256(data.tobytes()).hexdigest()

   d1 = compute_digest(x1)
   d2 = compute_digest(x2)
   assert d1 == d2, f"Hash divergence: {d1} != {d2}"
   ```

3. Run the automated Deterministic Idempotence Proof Suite:
   ```bash
   python3 scripts/testing/prove_deterministic_idempotence.py
   ```
   All 6 domains (Poincaré Projection, Nelder-Mead Copula, Adversarial Validation, Synthetic Procedural AST, Dead-End Ledger Linter, Two-Party IV&V) must verify with `0.00e+00` variance and matching cryptographic digests.

4. Enforce fail-closed gatekeeping before model/code promotion:
   ```python
   from cohezion.authority import IVVPolicy

   # Require deterministic verification proof before promoting artifacts
   assert proof_results["all_passed"] is True
   ```

## VERSION
v1.0

## SEE ALSO
- `scripts/testing/prove_deterministic_idempotence.py`
- `docs/research/deterministic_idempotence_proof.json`
- `src/cohezion/skills/TWO_PARTY_CRYPTOGRAPHIC_IVV_PRIME.md`
- `src/cohezion/skills/PROPRIOCEPTIVE_CYBERNETICS_PRIME.md`
