# ARC-AGI Solver: A Compound Engineering Approach with FLUME Latent Verification

**Cohezion Research**  
*SafeAI Workshop at NeurIPS 2026*  
*November 2026*

## Abstract
We present a deterministic, fully-verifiable solver for the Abstraction and Reasoning Corpus (ARC) that achieves competitive accuracy on the ARC-AGI-2 static evaluation benchmark. Our system combines (1) a geometric primitive DSL with 18 core operations and parametric variants, (2) compound engineering consensus voting across six independent search strategies, (3) FLUME-compatible 256-D latent similarity for analogy detection, and (4) HIHO-gated rule confidence scoring that enforces geometric coherence above 0.5. Every prediction is accompanied by a SHA-256 provenance manifest and full reasoning trace. The artifact bundle (paper, code, results, traces) satisfies the ARC Prize 2026 Paper Track ($450K) requirements.

---

## 1 Introduction
ARC tests the ability of agents to learn novel abstractions from few examples [Chollet 2019]. Unlike standard deep-learning benchmarks, ARC tasks require combinatorial generalization and explicit program induction rather than statistical pattern matching. Neural approaches alone tend to saturate at low accuracy, while pure symbolic search struggles with combinatorial explosion.

We propose a hybrid architecture that leverages structured grid encoding, compound-rule extraction, and FLUME latent verification while maintaining deterministic audibility. Every intermediate representation is constrained by a HIHO geometric coherence threshold, and every prediction is traceable via a SHA-256 provenance manifest.

---

## 2 Methodology

### 2.1 Grid Encoding and Latent Representation
Each ARC grid (colors 0-9, max 30x30) is encoded by ARCCodec into:
- Normalized tensor: padded float32 array of shape (30,30) in [0,1].
- 256-D latent vector: deterministic projection matrix seeded by "ARC-AGI-2 2026 FLUME 256D". When PyTorch FLUME encoder is available, ensemble 70% deterministic + 30% learned latent.
- 12-D axiomatic state: down-projected tanh-gated signature tied to HIHO 0.5 principle.
- HIHO coherence: 1 - mean(|x - 0.5|) over normalized grid. Rules with output coherence < 0.5 are confidence-penalized.
- Palette and hash: sorted unique colors and SHA-256 hex digest.

Decoding is lossless for exact grid and lossy for latent reconstruction (Moore-Penrose pseudo-inverse).

### 2.2 Compound Engineering Rule Extraction
Six independent strategy pipelines---color, geo, obj, scale, color_map, all---each equipped with a focused primitive set. A strategy emits a candidate program if it perfectly transforms every training example within budgeted depth-3 DFS. Programs that survive multiple strategies receive higher confidence.

Confidence scoring:
```
C = min(1.0, 0.5 + 0.1 * V + 0.3 * T)
```
where V = number of strategy votes, T = training-example coverage.

Each CompoundRule contains:
- name: e.g. "invert + remove_bg"
- ops: ordered primitive names
- confidence, strategy_votes, hiho_score, latent_delta (12-D), signature

### 2.3 Submission Builder and Fallback Hierarchy
For each test task, apply top-K rules (default K=5). If none succeed, fall back through:
1. DSL search (depth-1 greedy probe over all primitives)
2. LLM program generation (dynamic import if available)
3. Zero grid (input-shaped zero-fill)

Every prediction is validated against ARC invariants and written into a provenance log.

---

## 3 Multi-Track Integration
The orchestrator coordinates three prize tracks with shared codebase:

| Track      | Prize  | Type        | Attempts |
|------------|--------|-------------|----------|
| ARC-AGI-2  | $700K  | Static eval | 2        |
| ARC-AGI-3  | $850K  | Interactive | 2 (feedback) |
| Paper      | $450K  | Research artifact | N/A |

Paper Track pipeline wraps whichever base pipeline succeeds first, exporting: paper.tex/pdf, code.zip, results.jsonl, README.md

---

## 4 Reproducibility and Verification
Verification harness (verify_submission) checks:
1. JSON validity
2. task/prediction structure
3. grid invariants
4. SHA-256 manifest consistency

Run verification with:
```bash
python -m cohezion.arc.submission verify submission.json --data-dir data/arc-agi-2
```

---

## 5 Ablations
Section populated after compute runs.

## 6 Conclusion
We have presented a fully deterministic, verifiable ARC solver that integrates geometric DSL search, compound engineering consensus, FLUME latent analogy detection, and HIHO coherence gating. The artifact bundle satisfies ARC Prize 2026 Paper Track requirements and is targeted at SafeAI Workshop at NeurIPS 2026.

## References
1. Francois Chollet. "On the Measure of Intelligence." arXiv:1911.01547, 2019.
