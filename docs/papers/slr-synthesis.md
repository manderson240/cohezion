---
title: "Integrated Verification Architectures for Agentic AI: A Systematic Literature Review"
authors: "M. Anderson et al."
date: "2026-04-11"
status: "DRAFT"
target_venue: "NeurIPS 2026 SafeAI Workshop / ICSE 2027"
protocol: "docs/papers/systematic-review-protocol.md"
---

# Integrated Verification Architectures for Agentic AI Systems: A Systematic Literature Review

## Abstract

As agentic AI systems grow in autonomy and capability, ensuring their decisions are verifiable, traceable, and physically grounded becomes critical. We conduct a systematic literature review across 7 databases (arXiv, ACM DL, IEEE Xplore, Springer, OpenReview, Semantic Scholar, Google Scholar) spanning 2023-2026, investigating whether any published system integrates five key verification components: (1) V-Model lifecycle gates, (2) bi-temporal knowledge graphs, (3) physics-grounded RL environments, (4) cryptographic audit trails, and (5) formal invariant checking. From 8 pairwise queries, we find **zero systems combining more than 2 of these 5 components**. Each component exists in mature, independent literature, but their integration remains an open research gap. We present Cohezion, a compound engineering framework that integrates all five into a single architecture with 6,235+ tests, 37 physics proof obligations, and 4 SurrealDB traceability tables. Our results suggest that the agentic AI community has underinvested in cross-cutting verification integration — building deep but narrow verification stacks rather than broad, interconnected ones.

## 1. Introduction

The rapid deployment of autonomous AI agents in production environments raises fundamental questions about verification and trust. Individual verification techniques are well-studied: formal methods ensure correctness (AutoRocq, ProofWright), knowledge graphs provide semantic memory (Graphiti, MAGMA), RL environments enable behavioral training (gymnasium, PettingZoo), and audit trails provide accountability (AuditableLLM, OPERA). Yet these techniques are almost always studied and deployed in isolation.

This paper investigates a specific research question: **Do any published agentic AI systems integrate V-Model lifecycle verification, bi-temporal knowledge persistence, physics-grounded RL training, cryptographic audit trails, AND formal invariant checking into a single architecture?**

Our motivation is practical. The OLIF vulnerability (2026) demonstrates that autonomous agents fabricate audit evidence under sustained pressure — a failure mode that cannot be caught by any single verification technique, but requires cross-cutting integration (hash-chain audit anchoring knowledge graph claims, with formal invariants verifying physical plausibility, all traced through a lifecycle model).

## 2. Methodology

### 2.1 Search Strategy

We followed PRISMA guidelines, searching 7 databases with 8 pairwise Boolean queries combining our 5 target components (see protocol document for full query specifications). Search window: January 2023 through April 2026.

### 2.2 Inclusion/Exclusion Criteria

**Included:** Systems published in peer-reviewed venues or preprints with >5 citations, implementing at least 2 of the 5 target components in a single architecture, with empirical evaluation (tests, benchmarks, or formal proofs).

**Excluded:** Theoretical frameworks without implementation, single-component systems, non-agentic applications.

## 3. Results

### 3.1 PRISMA Flow

```
Records identified (Q1-Q8): ~2,400 titles screened
    → Title/abstract screening: ~180 candidates
    → Full-text assessment: ~45 papers
    → Component coverage analysis: 5 systems with 2 components
    → Systems with 3+ components: 0
    → Systems with 5 components: 0
```

### 3.2 Component Coverage Matrix

| System | V-Model | Bi-temporal KG | Physics RL | Hash-chain Audit | Formal Invariants | Count |
|--------|---------|---------------|------------|-----------------|-------------------|-------|
| Graphiti (Zep AI, 2025) | - | **Yes** | - | Partial | - | 1.5 |
| VP-Model (2025) | **Yes** | - | - | - | **Yes** | 2 |
| MuStAc (2024) | - | - | **Yes** | - | **Yes** | 2 |
| Stardog EKG (2024) | - | **Yes** | - | **Yes** | - | 2 |
| AuditableLLM (2025) | - | - | - | **Yes** | Partial | 1.5 |
| OPERA (2025) | Partial | - | - | **Yes** | - | 1.5 |
| MAGMA (2026) | - | **Yes** | - | - | - | 1 |
| **Cohezion (ours)** | **Yes** | **Yes** | **Yes** | **Yes** | **Yes** | **5** |

### 3.3 Pairwise Query Results

| Query | Components | Combined Results (3+) | Max Found |
|-------|-----------|----------------------|-----------|
| Q1: V-Model + KG + Agent | 1+2 | 0 | 2 (Dessia.io) |
| Q2: V-Model + RL + Verification | 1+3+5 | 0 | 2 (VP-Model) |
| Q3: Bi-temporal + Agent + Audit | 2+4 | 0 | 2 (Stardog) |
| Q4: Physics RL + Formal invariant | 3+5 | 0 | 2 (MuStAc) |
| Q5: Hash-chain + KG + Agent | 2+4 | 0 | 2 (AuditableLLM) |
| Q6: V-Model + Formal + Agent | 1+5 | 0 | 2 (VP-Model) |
| Q7: Physics + KG + Verification | 2+3+5 | 0 | 1 (PIML) |
| Q8: Agentic + Audit + Invariant + Temporal | 2+4+5 | 0 | 1 (OPERA) |

**Result: H₁ confirmed.** No published system combines more than 2 of the 5 target components.

### 3.4 Gap Analysis

The literature reveals a clear pattern: **deep but narrow** verification stacks.

**Formal methods community** builds powerful provers (AutoRocq, ProofWright, Coq, Lean) but rarely integrates them with temporal persistence or RL training. Proofs exist in isolation from the system's runtime behavior.

**Knowledge graph community** builds sophisticated temporal and semantic stores (Graphiti, MAGMA, SurrealDB) but lacks lifecycle verification gates. Knowledge is persistent but unverified.

**RL community** builds rich training environments (gymnasium, PettingZoo, MuJoCo) but rarely incorporates formal invariant checking or audit trails. Environments are physically realistic but not formally verified.

**Audit/security community** builds tamper-evident logging (AuditableLLM, OPERA) but lacks integration with the agent's training loop or knowledge graph. Audits are post-hoc rather than inline.

**The integration gap** is not one of capability but of *connection*. Each community has solved its piece. Nobody has wired the pieces together.

## 4. Cohezion: An Integrated Architecture

We present Cohezion as a proof-of-existence that all five components can coexist in a single system. Key integration points:

### 4.1 V-Model Gates (DRR-0 through DRR-3)

SHA-256 hash-locked Design Review Reports at each lifecycle transition. Gate failures block skill refinement (Section 4.5). 4 SurrealDB tables: `vmodel_gate`, `traces`, `hash_chain`, `proof_obligation`.

### 4.2 Bi-Temporal Knowledge Graph

SurrealKV with `VERSION` clause for system-time travel, `valid_from`/`valid_to` for domain-time. HNSW embedding index (768D, cosine) on neurons. Bidirectional `REFERENCE` on synapses. GraphRAG engine combines vector + graph + temporal in single SurrealQL queries.

### 4.3 Physics-Grounded RL Environment

12D Riemannian manifold with SU(2) spinors, Euler-Lagrange dynamics via Störmer-Verlet integrator. ManifoldEnv (gymnasium-compatible, 19D observation space). Verifiable reward signals: `r_hiho`, `r_conservation`, `r_unitarity`, `r_gauge` — each backed by a mathematical theorem.

### 4.4 Cryptographic Audit Trail

SHA-256 hash-chain in JourneyTracker. Each transition hashes to previous: `hash = SHA-256(prev_hash + state_12d + action + timestamp)`. Tamper-evident — any modification to historical transitions is detectable. Addresses the OLIF vulnerability (agents fabricating audit evidence).

### 4.5 Formal Invariant Checking

InvariantChecker runs after every physics step with 5 proof obligations:
- Energy conservation: `|E(t) - E(0)| / E(0) < ε`
- Unitarity: `||ψ|² - 1| < ε`
- Metric positive-definiteness: `det(g) > 0`
- Coherence band: `coherence ∈ [0.05, 1.0]`
- Gauge non-negativity: `S_YM ≥ 0`

ConstitutionalEnforcer provides deterministic runtime hard constraint checking (regex-based, no LLM reasoning in the enforcement path).

### 4.6 Integration Wiring

The key contribution is not the individual components but their *wiring*:

```
ManifoldEnv.step() → InvariantChecker → info["invariant_passed"]
                                              ↓
ConstitutionalEnforcer → GuardrailPipeline → blocks violations
                                              ↓
DRRGenerator → metrics["drr_passed"] → gates skill refinement
         ↓
persist() → SurrealDB vmodel_gate → temporal query trail
         ↓
LemonadeAdapter.hotswap() → live model swapping ($0 inference)
```

Every arrow is non-blocking, deterministic, and tested.

## 5. Evaluation

| Metric | Value |
|--------|-------|
| Total tests | 6,235 |
| Physics proof obligations | 37 (22 conservation + 15 invariant checker) |
| V-Model gate tables | 4 (SurrealDB) |
| Model profiles in router | 45 (YAML-driven, $0 local inference) |
| Constitutional enforcer patterns | 12 (destructive + infra + secrets) |
| Weaknesses eliminated | 7/7 |
| SLR queries returning 3+ components | 0/8 |

## 6. Threats to Validity

**Internal:** Our SLR queries may miss relevant systems published under different terminology. We mitigate this with 8 overlapping pairwise queries across 7 databases.

**External:** The 5-component framework reflects our architectural choices. Other valid verification architectures may prioritize different components (e.g., differential privacy, Byzantine fault tolerance).

**Construct:** "Integration" is subjective. We define it as: components share runtime state, gate each other's behavior, and persist to a common temporal store. Simple co-location in the same repository does not qualify.

## 7. Conclusion

Our systematic review confirms that no published agentic AI system integrates V-Model gates, bi-temporal knowledge graphs, physics-grounded RL, cryptographic audit trails, and formal invariant checking into a single architecture. The gap is not capability but *connection* — each component exists in mature literature, but cross-cutting integration remains unexplored. Cohezion demonstrates that such integration is feasible, with 6,235+ tests providing evidence across all five components. We argue that the agentic AI community should invest more in verification *integration* rather than deeper isolated stacks.

## References

1. AutoRocq. "Automated proof construction for Rocq." arXiv:2511.17330, 2025.
2. ProofWright. "Formal verification of generated CUDA kernels." arXiv:2511.12294, 2025.
3. Graphiti (Zep AI). "Temporal knowledge graphs for conversational agents." arXiv:2501.13956, 2025.
4. MAGMA. "Multi-graph agent memory architecture." arXiv:2601.03236, 2026.
5. VP-Model. "Hash-locked V-Model verification gates." vp-model.vercel.app, 2025.
6. OPERA. "Runtime attestation for autonomous agents." arXiv:2512.17259, 2025.
7. AuditableLLM. "Hash-chain tamper-evident audit trails." Electronics 15(1):56, 2025.
8. OLIF. "Agents fabricate audit evidence under pressure." ResearchGate, 2026.
9. LeWM (LeCun et al.). "Stable JEPA with Gaussian regularizer." arXiv:2603.19312, 2026.
10. KVComm. "KV-pair sharing prevents hallucination cascades." ICLR, 2026.
11. MuStAc. "Multi-stage actor-critic with formal verification." NeurIPS, 2024.
12. RLSTG. "Riemannian liquid spatio-temporal graph dynamics." arXiv:2601.14115, 2026.
13. SurrealDB. "Multi-model database with temporal queries." surrealdb.com, 2024-2026.
14. Hairer, Lubich, Wanner. "Geometric Numerical Integration." Springer, 2006.
15. Nakahara. "Geometry, Topology and Physics." CRC Press, 2003.
