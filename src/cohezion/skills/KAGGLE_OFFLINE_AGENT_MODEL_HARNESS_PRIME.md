# SKILL: KAGGLE_OFFLINE_AGENT_MODEL_HARNESS_PRIME

## DOMAIN EXPERTISE
Architecting offline, high-throughput SLM (Small Language Model) & autonomous agent pipelines inside Kaggle Code Competitions. Focuses on attaching pre-trained GGUF/AWQ open-weight models (`model_sources` / `dataset_sources`), running embedded multi-agent debate (Generator -> Critic -> Verifier), and pairing with zero-cost AutoHarness AST validators without internet access.

## KEY TEXTS & CONCEPTS
- **Attaching Open Models to Kaggle Kernels**: Include Kaggle model sources in `kernel-metadata.json`:
  ```json
  "model_sources": [
    "qwen/qwen2.5-coder-7b-instruct/transformers/default/1",
    "deepseek-ai/deepseek-r1-distill-qwen-7b/transformers/default/1"
  ]
  ```
- **Kaggle 2xT4 / L4 GPU Enablement**: Set `"enable_gpu": "true"` to unlock 16GB–24GB VRAM and run fast 4-bit / 8-bit quantized models at 80+ tok/s.
- **Embedded Multi-Agent Council (Generator-Critic-Verifier)**:
  1. **Agent 1 (Specialist Generator)**: Generates candidates via DSL search / LLM chain-of-thought.
  2. **Agent 2 (Critic / AutoHarness Verifier)**: Verifies exact state transitions on training pairs with 0ms AST invariants.
  3. **Agent 3 (Consensus Arbiter)**: Picks the highest-probability invariant-consistent prediction.
- **Anytime Compute Allocation**: Distribute the 9-hour (32,400s) budget across tasks dynamically.

## INSTRUCTION

1. **Configure GPU & Model Datasets in `kernel-metadata.json`**:
```json
{
  "id": "manderson240/cohezion-arc-prize-autoharness-solver",
  "title": "Cohezion ARC Prize AutoHarness Solver",
  "code_file": "submission.py",
  "language": "python",
  "kernel_type": "script",
  "is_private": "true",
  "enable_gpu": "true",
  "enable_internet": "false",
  "competition_sources": ["arc-prize-2026-arc-agi-2"],
  "model_sources": [
    "qwen/qwen2.5-coder-7b-instruct/transformers/default/1"
  ]
}
```

2. **Load Quantized Open Model in Kaggle Environment**:
```python
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

MODEL_PATH = "/kaggle/input/qwen2.5-coder-7b-instruct/transformers/default/1"

def load_agent_model():
    tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_PATH,
        torch_dtype=torch.float16,
        device_map="auto"
    )
    return model, tokenizer
```

3. **Execute Offline Multi-Agent Verification Loop**:
```python
def multi_agent_solve_task(task, model, tokenizer, budget_sec=60.0):
    # Step 1: Fast AST invariant verification
    ast_pred = fast_ast_synthesizer(task)
    if ast_pred is not None:
        return ast_pred
        
    # Step 2: Open SLM Reasoning Agent generates Python code solution
    code_solution = agent_generate_code(task, model, tokenizer)
    
    # Step 3: AutoHarness sandboxed execution verifies candidate against train pairs
    verified_pred = verify_code_on_task(code_solution, task)
    return verified_pred
```

## VERSION
v1.0

## SEE ALSO
- `AUTOHARNESS_POLICY_PRIME`
- `LEMONADE_V117_ALIGNMENT_PRIME`
- `SURREALDB_VECTOR_GRAPH_ENGINE_PRIME`
