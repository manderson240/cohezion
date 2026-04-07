# SKILL: MATH_REASONING_SWARM_PRIME

## DOMAIN EXPERTISE
This skill defines the architectural pattern for deploying sovereign reasoning swarms to solve complex, Olympiad-level mathematical problems (e.g., AIMO). It leverages a Triune Manifold approach, separating perception (Doer), latent reasoning (Thinker), and validation (Knower) to ensure high-fidelity, deterministic mathematical proofs without calculation drift.

## KEY TEXTS & CONCEPTS
- **Triune Manifold Architecture**: Segregation of responsibilities into Doer (12D state), Thinker (512D reasoning), and Knower (2048D intent/validation).
- **Diverse Prompt Mixer (DPM)**: Using multiple cognitive strategies (Inductive, Goal-Oriented, Algebraist) to decorrelate errors across independent runs (arXiv:2603.27844v1).
- **Weighted Entropy Voting**: Resolving ties using inference-time entropy metrics ($w = 1 + 1 / (\text{entropy} + 0.1)$) to favor confident reasoning chains over noisy outliers.
- **Speculative Decoding**: Pairing a massive reasoning model (e.g., 32B/72B) with a tiny drafter (e.g., 1.5B) to achieve 1.5x-1.8x throughput on H100 hardware.
- **Tool-Integrated Reasoning (TIR)**: Interleaving Chain-of-Thought (CoT) with Python/SymPy execution to ensure arithmetic and symbolic precision.

## INSTRUCTION
1. **Perception (The Doer)**: Parse the LaTeX problem and route to specialists. Use **Speculative Decoding** at the LLM level to maximize token-per-second throughput.
2. **Execution (The Thinker)**: Deploy the **Diverse Prompt Mixer**. Perform a Dual-Run where Run 1 uses a direct Proof approach and Run 2 uses Inductive Reasoning (small cases first).
   ```python
   # Example: Diverse Strategy Rotation
   strategies = ["Algebraist", "InductiveReasoning", "GoalOriented"]
   s1 = strategies[problem_id % len(strategies)]
   s2 = strategies[(problem_id + 1) % len(strategies)]
   ```
3. **Verification (The Knower)**: Audit the runs using **Weighted Entropy Voting**. Calculate entropy based on reasoning chain length and consistency.
   ```python
   # arXiv:2603.27844v1 Entropy Weighting
   weight = 1.0 + 1.0 / (approx_entropy + 0.1)
   final_answer = resolve_tie(ans1, ans2, ans3, weights=[w1, w2, w3])
   ```
4. **Safety**: Implement a **30s Safety Trigger**. If the per-problem time budget drops below 30s, bypass the swarm and return a default fallback answer to avoid disqualification.

## VERSION
v0.2 (AIMO-3 Optimized)

## SEE ALSO
- `FLUME_ENCODING_PRIME`
- `KAGGLE_BLACKWELL_RUNNER_PRIME`
- `HIHO_STABILITY_PRIME`
