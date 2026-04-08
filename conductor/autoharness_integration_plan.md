# AutoHarness Local Integration Plan

## Objective
To integrate the methodology outlined in [AutoHarness: improving LLM agents by automatically synthesizing a code harness (arXiv:2603.03329v1)](https://arxiv.org/html/2603.03329v1) into the Cohezion ecosystem. By automatically synthesizing code harnesses locally using smaller, efficient models (like Ollama's `qwen3.5:coder` or `phi4-mini`), we can eliminate illegal actions ("Code-as-action-verifier") and completely hardcode deterministic behaviors ("Harness-as-policy") across our agent swarms.

## Key Concepts from Paper
1. **Iterative Code Refinement**: Use a small LLM to generate a Python wrapper/harness, test it against an environment simulator, feed the errors back to the LLM, and refine the code.
2. **Code-as-Action-Verifier**: Rather than fine-tuning models on validity rules or manually writing verifiers (which is labor-intensive and brittle), the LLM itself generates a function (e.g., `def is_valid_move(state, action) -> bool`) that prunes illegal outputs.
3. **Harness-as-Policy**: Push the technique further to generate the entire policy as code, completely bypassing the LLM at inference/decision time to maximize speed and minimize cost.

## Scope & Impact
By deploying `AutoHarness` locally:
*   **AIMO Progress Prize 3**: We can auto-generate specialized `SymbolicVerifiers` for specific problem classes, rather than relying on our hand-coded SymPy sandbox.
*   **ARC Prize 2026**: We can synthesize environment-specific "valid move" verifiers for the ARC grids, drastically reducing the search space for the 12D manifold routing.
*   **BirdCLEF 2026**: We can use it to auto-generate data augmentation policies (Harness-as-Policy) for audio processing, saving runtime compute.

## Proposed Solution

### 1. The `AutoHarnessSynthesizer` Module
Create a new module `src/cohezion/compound/autoharness.py` that implements the iterative refinement loop locally.

### 2. Integration with `AutonomousCompoundLoop`
Extend the existing `AutonomousCompoundLoop` (which already benchmarks PRIME skills) to include a "Harness Synthesis" phase. When a new environment or competition is registered, the loop will spawn a local `qwen3.5:cloud` or `phi-4` instance to generate the environment's verifier.

### 3. Code-as-Action-Verifier for Kaggle Swarms
Instead of relying on rigid, pre-defined rules, our Kaggle-native scripts will pull the locally-synthesized AutoHarness code files. This provides the safety of a strict programmatic sandbox (no illegal outputs, no 0 scores) without the manual development overhead.

## Implementation Steps
1. **Module Creation**: Develop `src/cohezion/compound/autoharness.py` with `synthesize_verifier()` and `synthesize_policy()` methods.
2. **Environment Mocking**: Build minimal mock environments (e.g., a dummy SymPy math environment, a dummy ARC grid environment) to provide immediate stack-trace feedback to the LLM during the synthesis loop.
3. **Swarm Injection**: Update `cohezion.swarm.team_execution` to check for and load an `auto_harness.py` file if it exists for a given task, using it to filter the LLM's raw generation before execution.
4. **Validation**: Test the loop locally by having it generate a verifiable chess-move or math-operation harness from scratch within 5 iterations.

## Verification & Testing
- Run `pytest tests/test_autoharness.py` to confirm the synthesizer can successfully generate a working Python verifier from a prompt description within the maximum iteration limit.
- Verify that the resulting code executes purely deterministically without requiring an LLM call at runtime.
