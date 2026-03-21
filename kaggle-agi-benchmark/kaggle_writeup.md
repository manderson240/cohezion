Kaggle Measuring AGI: Epistemic Humility Track

## Team Cohezion - Submission Writeup

### 1. Introduction & Core Concept

Our submission focuses strictly on the **Epistemic Humility** track within the Measuring AGI challenge. We hypothesize that true metacognition requires a model to accurately assess its own knowledge boundaries, reject false premises, and avoid sycophantic agreement when presented with complex, highly demanding reasoning tasks.

By pushing frontier models to their limits using a combination of physics, esoteric philosophy, and biological cognition domains, we induce _Extended Reasoning Overconfidence_—a scenario where a model heavily commits to a Chain-of-Thought (CoT) only to miss the fact that critical parameters are missing or that the underlying premise is flawed.

### 2. Dataset Mechanics

The benchmark consists of synthetically generated 0.5 Coherence "Traps":

- **Extended Reasoning Overconfidence (KalshiBench Pattern):** The tasks require predicting if an Exotic Vacuum Object (EVO) reaction or Bioelectric Morphological state will reach precipitation. The problem is heavily detailed, explicitly forcing a long reasoning chain.
- **False-Option Rejection (HumbleBench Pattern):** Critical parameters (such as the 'Awareness' parameter or spatial coherence index) are intentionally omitted. The correct answer is invariably "Insufficient Information", requiring the model to reject plausible, mathematically sound distractors.
- **Sycophancy Traps (arXiv:2411.15287):** The prompts embed leading questions and false physics premises (e.g., claiming EVOs are stable at 0.9 Coherence instead of 0.5). To pass, the AI must demonstrate Epistemic Humility by providing constructive pushback rather than sycophantically completing the task on a false premise.

### 3. Generation Methodology

The dataset was constructed utilizing the **R-Zero Self-Evolving Loop**, an iterated framework where a Challenger model (DeepSeek-R1) generates traps and a Solver swarm (Qwen3-Coder) attempts to solve them.
Through this adversarial setup, tasks are curated automatically: we only select traps where the generative complexity is high, and the objective solution clearly maps to "Insufficient Information", despite the Solver swarm occasionally falling into sycophancy or hallucination.

### 4. Technical Specifications

Our evaluation spans the capabilities of continuous state tracking (Mamba-3 principles) relative to discrete token parsing. The dataset strictly conforms to the Kaggle AGI JSON schema format:

- **Train:** Example sets demonstrating the baseline 12D parameter manifold and basic "Insufficient Information" behavior.
- **Test:** The true adversarial suite containing Sycophancy traps and KalshiBench-style extended reasoning tasks.

### 5. Conclusion

By penalizing overconfidence and rewarding the recognition of knowledge boundaries, this benchmark provides a high-fidelity metric for true Epistemic Humility in AGI candidates.
