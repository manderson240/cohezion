# Deep Synthesis Plan: ARC Prize 2026 (Cosmogonic Program Synthesis)

## Objective
To achieve state-of-the-art performance (>50%) on the ARC-AGI-2 and ARC-AGI-3 benchmarks by treating abstract reasoning not as deep learning pattern matching, but as a **thermodynamic phase transition of information** (Computational Cosmogony). 

We will build an Evolutionary Program Synthesizer inspired by the `Poetiq` architecture, heavily constrained by the 10-step symmetry-breaking chain of the `cohezion` universe.

## Background & Motivation
Current LLMs and CNNs fail on ARC because they lack causal "System 2" reasoning. The `cohezion` codebase contains a profound insight: the `SymmetryBreaking` engine (`physics/cosmogony.py`), which models the creation of structure from the Void through cooling temperatures (T=250 down to T=0.002).

By mapping an ARC task to this thermodynamic cooling process, we constrain the search space of possible programs drastically. We don't just guess the transformation; we *precipitate* it.

## Proposed Architecture: The Cosmogonic Synthesizer (Spearhead Edition)

We will build `arc_cosmogony_synthesizer.py` that implements the following pipeline, leveraging **Inference-Time Scaling** and **Test-Time Training (TTT)**:

1. **Stage 0: The Void (T=250) - Latent Encoding & TTT-LoRA**
   - Action: **Vision Transformer (ViT-Tiny)** encoder with 1x1 patches.
   - Breakthrough: **Test-Time Training (TTT-Discover)**. We will perform a brief LoRA fine-tuning of the encoder/predictor weights on the specific train pairs of the task to "specialize" the latent space for that task's unique logic.

2. **Stage 1: Quadrature (T=150) - System 2 Perception**
   - Action: Background vs. Foreground separation.
   - Refinement: Use **Self-Critique** to verify background detection before proceeding.

3. **Stage 2: SO(12) to SO(3)⁴ — "Organ" Discovery (T=100 to T=10)**
   - Action: `BioelectricCoupler` for object discovery.
   - Tracking: Measure **Latent Path Straightening**. Linearizing the trajectory between states indicates successful abstraction of physical invariants (S_straight metric).

4. **Stage 3: Phase and U(1)⁴ — Symmetry & Axis Selection (T=5 to T=1)**
   - Action: Extract invariant transformations.
   - Extension: **Poetiq-style Search**. Use an LLM (Gemini 3 Flash) to propose potential DSL programs based on the discovered objects and symmetries.

5. **Stage 4: HIHO Stabilization & Cohesion (T=0.01 to T=0.005) - Evolutionary Refinement**
   - Action: **Recursive Self-Improvement Loop**.
   - The system generates candidate programs, executes them, and uses the feedback (Prediction Error + Exact Match) to refine the logic.
   - **Topological Pruning**: Use the `TopologicalRouter` to detect if the search is stuck in a loop (PIVOT regime) and force a strategy change.

6. **Stage 5: Reality Precipitate (T=0.002)**
   - Action: Execute the "0.5 Coherence" (validated) program on the Test Input.

## Implementation Steps

### 1.1 Synthesizer Core (`arc_cosmogony_synthesizer.py`)
- [x] Create the temperature-stepped orchestrator.
- [x] Implement the Genetic Algorithm for AST generation (the "Poetiq-style" evolutionary loop).

### 1.2 Primitive Operations Library (`arc_dsl.py`)
- [x] Define the Domain Specific Language (DSL) for ARC: `move()`, `rotate()`, `fill()`, `recolor()`, `crop()`, `intersect()`.

### 1.3 ARC-AGI-2 Evaluation Pipeline (`evaluate_cosmogony.py`)
- [x] Run the synthesizer against the downloaded `arc-agi-2-repo` dataset.
- [x] Use the built-in `TDDIntegration` to ensure the DSL primitives work perfectly before launching the full evolutionary loop.

### 1.4 Paper Track Adaptation
- [x] Expand `paper_draft.md` to include "Cosmogonic Program Synthesis" as the primary driver, positioning it as a fundamental breakthrough in neuro-symbolic AI.

## Alternatives Considered
- *Pure LLM Prompting (e.g., GPT-4o / Claude 3.5)*: Rejected. Research shows a hard ceiling at ~20-30% for pure LLM approaches on ARC without massive external scaffolding.
- *Pure Test-Time Training (TTT)*: While useful for ARC-AGI-3 (interactive), it is too slow and sample-inefficient for the strict static bounds of ARC-AGI-2.

## Verification & Validation
- **TDD Cycle**: All DSL primitives will have 100% test coverage using the `TDDIntegration` framework.
- **Adversarial Review**: We will run the `AdversarialReviewSystem` over the AST generator to ensure we aren't memorizing the training set (overfitting), focusing heavily on the "Innovation" and "Reliability" perspectives.
