---
name: funsearch-evolutionary-coder-prime
description: "Expertise in adapting Google DeepMind's FunSearch pipeline: pairing local LLMs (Qwen3-Coder-30B) with island-based genetic programming to evolve verified deterministic AST verification harnesses (arXiv:2603.03329v1)."
metadata:
  version: "v1.0"
  concepts: ["Evolutionary Program Search", "Island Model Genetic Algorithm", "Function Mutator", "AST Code Verifier"]
  see_also: ["KAGGLE_AUTOHARNESS_PRIME", "COMPOUND_ENGINEERING_PRIME"]
  source: "src/cohezion/skills/FUNSEARCH_EVOLUTIONARY_CODER_PRIME.md"
---

# SKILL: FUNSEARCH_EVOLUTIONARY_CODER_PRIME

## DOMAIN EXPERTISE
Expertise in adapting Google DeepMind's FunSearch framework to autonomously discover and evolve mathematical policies and deterministic AST verifiers using local LLMs as mutation operators.

## KEY TEXTS & CONCEPTS
- **DeepMind FunSearch**: Mathematical discovery via program evolution using paired LLMs and deterministic sandboxed evaluators (Romera-Paredes et al., *Nature* 2023).
- **Island Genetic Architecture**: Isolated population clusters evolving code variants to prevent premature convergence on local optima.
- **Deterministic Action-Verifier Synthesis**: Evolving 0-cost AST functions that replace inference calls for Kaggle ARC Prize and AIMO tasks.

## INSTRUCTION
1. Define the target function signature and deterministic evaluation sandbox.
2. Initialize islands with base seed implementations generated via local silicon (`Qwen3-Coder-30B`).
3. Run the evolutionary loop:
   ```python
   def mutate_program(program_code: str, evaluator_score: float) -> str:
       # Local LLM acts as an evolutionary mutation operator
       prompt = f"Improve this Python program to increase its score (current: {evaluator_score}):\n{program_code}"
       return local_llm_mutate(prompt)
   ```
4. Register verified breakthrough policies directly into `src/cohezion/registry/`.

## VERSION
v1.0
