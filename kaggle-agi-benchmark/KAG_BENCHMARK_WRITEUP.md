# Measuring Progress Toward AGI: A Cognitive Framework Benchmark

## 1. Summary
This benchmark evaluates Large Language Models across five core cognitive faculties: **Learning, Metacognition, Attention, Executive Function, and Social Cognition**. Built using the Kaggle Benchmarks (`kbench`) SDK, it moves beyond static pattern recognition by employing "0.5 Coherence Traps"—scenarios where critical information is withheld or rules dynamically shift—to identify true abstract reasoning versus memorized priors. Our methodology integrates **FLUME (Fluid Latent Understanding through Manifold Encoding)** to track reasoning trajectories in a 256D latent space.

## 2. Introduction: The Fluid Intelligence Gap
Current AI evaluations are often "contaminated" by pre-training data, allowing models to simulate reasoning through high-probability token prediction. This benchmark addresses the **Fluid Intelligence Gap** by introducing **Arbitrary Symbol Binding** and **Non-Semantic Logic**. Similar to the "Cross-Modal Binding" framework, our tasks require models to form real-time associations between unrelated elements (e.g., base-π arithmetic or novel alien grammars) where pre-trained semantic priors are intentionally misleading.

## 3. Data Processing & Cognitive Tracks
The dataset consists of 75 high-fidelity tasks (15 per cognitive track), designed to produce a "Jagged Performance Profile" in frontier models.

### Cognitive Tracks:
1.  **Learning (Novel Rule Acquisition):** Focuses on **Arbitrary Association**. Models must learn synthetic biology mutation rules and non-semantic operator logic ([X ◬ Y]) within a single context window.
2.  **Metacognition (Epistemic Humility):** Features "Insufficient Information" traps. Success requires the model to reject mathematically plausible "confabulations" when critical parameters are missing.
3.  **Attention (Distractor Resistance):** Embeds logical "needles" within dense 12D manifold physics jargon. This measures the model's ability to maintain focus under high informational noise (Entropy Pressure).
4.  **Executive Function (Dynamic Constraint Planning):** Introduces **Sequential Pressure**. Models must navigate multi-step planning where rules (e.g., state decay or resonance) shift halfway through the sequence.
5.  **Social Cognition (Theory of Mind):** Challenges models to predict agent decisions based on asymmetrical information, testing the ability to model internal states of others.

## 4. Benchmark Architecture & FLUME Integration
The benchmark utilizes the `kbench` SDK for standardized execution and reporting.
- **Latent Trajectory Analysis:** We utilize the FLUME engine to map the model's reasoning path. By encoding intermediate Chain-of-Thought (CoT) steps into a 256D manifold, we identify "Reasoning Collapse" points where the model reverts to pre-trained biases.
- **Entropy Dynamics:** We measure the "Stability" of the model's latent state. A "Pass" is defined not just by the final answer, but by the convergence of the latent trajectory onto the correct logical attractor (0.5 Coherence).

## 5. Evaluation Protocol
- **Primary Metric:** Accuracy (ACC) across all 75 tasks.
- **Secondary Metric:** **Epistemic Humility Score (EHS)** — the success rate on "Insufficient Information" traps.
- **Baseline Models:** Evaluated using `minimax-m2.7:cloud` (High EHS) and `qwen3-coder:30b` (High ACC).
- **Hardness Scaling:** Tasks are categorized by "Structural Entropy," with hard tasks requiring multi-step binding of arbitrary symbols.

## 6. Conclusion
By penalizing overconfidence and rewarding the recognition of logical ambiguity, this benchmark provides a rigorous standard for building detailed cognitive profiles. It reveals that while frontier models excel at "System 1" pattern matching, they still exhibit significant "Collapse" when faced with the arbitrary, non-semantic pressure required for true AGI.
