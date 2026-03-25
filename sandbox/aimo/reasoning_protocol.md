# AIMO Reasoning Protocol

## Goal
Maximize **Penalized Accuracy** on AIME/IMO-level mathematical problems within a **150-second per problem** time budget.

## Reasoning Primitives
You may mutate the following parameters to improve performance:
1. **Specialist Prompts**: Adjust the persona, instructions, and few-shot examples for Algebraist, NumberTheorist, Geometer, and Combinatorist.
2. **Verification Strategy**: Toggle between purely analytical reasoning, SymPy-driven symbolic execution, and Monte Carlo numerical simulation.
3. **Voting Thresholds**: Adjust the stability threshold required to commit an answer vs. triggering a tie-breaker.
4. **Model Routing**: Decide which problems require the high-reasoning "Thinker" (DeepSeek-R1) vs. the efficient "Verifier" (Phi-4).

## Constraints
- **Total Time**: 5 hours for 110 problems.
- **Memory**: 128GB RAM / 12GB VRAM (Strictly sequential).
- **Offline**: No external API calls during the "Solve" phase.

## Research Loop
1. **Hypothesis**: Propose a specific change (e.g., "Adding a step to check prime factorization for all integer problems").
2. **Experiment**: Run the `swarm_driver.py` on the `reference_problems.json`.
3. **Evaluation**: Compare results against `Last Best`.
4. **Conclusion**: Keep or Revert.
