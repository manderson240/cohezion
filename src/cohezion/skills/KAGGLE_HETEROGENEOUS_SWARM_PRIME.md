# SKILL: KAGGLE_HETEROGENEOUS_SWARM_PRIME

## DOMAIN EXPERTISE
Deploying heterogeneous multi-model specialist swarms tailored to Kaggle dual-device silicon topology (2x NVIDIA T4 / L4 GPUs + multi-core x86_64 host CPU). Mirrors Cohezion's local silicon discipline (NPU/iGPU/CPU lane routing) inside Kaggle's offline evaluation runner.

## KEY TEXTS & CONCEPTS
- **Kaggle Silicon Topology Allocation**:
  * **GPU 0 (16GB VRAM)**: Dedicated Reasoning Specialist (`DeepSeek-R1-Distill-Qwen-7B` / `14B`).
  * **GPU 1 (16GB VRAM)**: Dedicated Code & AST Synthesizer (`Qwen2.5-Coder-7B`).
  * **Host CPU (4 Cores / 30GB RAM)**: Fast Deterministic AST Invariant Engine + Cellular Automata Rule Induction + Consensus Arbiter.
- **Pipelined Council Execution**:
  1. **CPU Fast-Path**: 0ms AST checks (Color Remap, D4 Dihedral, Euler characteristic).
  2. **Parallel GPU Dispatch**: GPU 0 (Reasoning Chain-of-Thought) and GPU 1 (Code DSL Synthesis) run simultaneously using `concurrent.futures.ThreadPoolExecutor`.
  3. **AutoHarness Sandbox Filter**: Both candidates verified against train pairs; valid AST programs accepted immediately.
- **Model Sources Configuration**:
  Attach both specialist models concurrently via `kernel-metadata.json`:
  ```json
  "model_sources": [
    "deepseek-ai/deepseek-r1/transformers/deepseek-r1-distill-qwen-7b/2",
    "qwen-lm/qwen2.5-coder/transformers/qwen2.5-coder-7b-instruct/1"
  ]
  ```

## INSTRUCTION

1. **Initialize Silicon-Specific Device Maps**:
```python
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


def load_heterogeneous_fleet():
    # GPU 0: Reasoning Agent
    r1_path = "/kaggle/input/deepseek-r1/transformers/deepseek-r1-distill-qwen-7b/2"
    tok_r1 = AutoTokenizer.from_pretrained(r1_path)
    model_r1 = AutoModelForCausalLM.from_pretrained(
        r1_path, torch_dtype=torch.float16, device_map={"": "cuda:0"}
    )

    # GPU 1: Code Synthesizer Agent
    coder_path = "/kaggle/input/qwen2.5-coder/transformers/qwen2.5-coder-7b-instruct/1"
    tok_coder = AutoTokenizer.from_pretrained(coder_path)
    model_coder = AutoModelForCausalLM.from_pretrained(
        coder_path, torch_dtype=torch.float16, device_map={"": "cuda:1"}
    )
    return (model_r1, tok_r1), (model_coder, tok_coder)
```

2. **Parallel Swarm Generation & Verification**:
```python
import concurrent.futures


def run_swarm_synthesis(task, r1_agent, coder_agent):
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        f_r1 = executor.submit(agent_r1_generate, task, *r1_agent)
        f_coder = executor.submit(agent_coder_generate, task, *coder_agent)

        for f in [f_r1, f_coder]:
            fn = f.result()
            if fn is not None and check_transform_fit(task["train"], fn):
                return fn
    return None
```

## VERSION
v1.0

## SEE ALSO
- `KAGGLE_OFFLINE_AGENT_MODEL_HARNESS_PRIME`
- `LEMONADE_V117_ALIGNMENT_PRIME`
- `AUTOHARNESS_POLICY_PRIME`
