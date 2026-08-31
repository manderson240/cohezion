# SKILL: LOCAL_TO_KAGGLE_HARNESS_SYNERGY_PRIME

## DOMAIN EXPERTISE
Dual-substrate optimization strategy: Leveraging local heterogeneous hardware (AMD Strix Halo 128GB UMA, XDNA2 NPU, Radeon iGPU) to train, distill, and verify models, compiling them into lightweight self-contained weights and AST action verifiers, then deploying them to maximize Kaggle's dual-T4 GPUs and 9-hour execution runtime.

## KEY TEXTS & CONCEPTS
- **Substrate Asymmetry & Sovereign Division of Labor**:
  * **Local Workstation (Strix Halo 128GB RAM / NPU / iGPU)**: Unlimited runtime, massive context windows (128K FP4), offline training/distillation, and iterative hyperparameter tuning.
  * **Kaggle Cloud Runners (Dual T4 30GB VRAM / 4 vCPUs / 9 Hours)**: Strict offline execution, 9-hour continuous anytime evaluation, parallel GPU batching.
- **The 4-Stage Synergy Pipeline**:
  1. **Phase 1 (Local Distillation & AST Synthesis)**: Mine training invariants and compile deterministic AST verifiers locally in <1ms.
  2. **Phase 2 (Model Card & Weights Packaging)**: Quantize models (AWQ/GGUF/FP16) to fit precisely within 15GB VRAM boundaries on Kaggle `cuda:0` and `cuda:1`.
  3. **Phase 3 (Anytime Runtime Maximization)**: Distribute the 32,400-second Kaggle window dynamically across private test evaluation tasks.
  4. **Phase 4 (Zero-Cost Verification)**: AutoHarness sandboxed verification (arXiv:2603.03329v1) guarantees only 100% invariant-compliant candidates are emitted.

## INSTRUCTION

1. **Local Distillation & Verification Harness**:
```python
def local_synthesize_and_verify(task_data, n_samples=1000):
    # Run locally on Strix Halo NPU/iGPU
    candidates = generate_candidates_local(task_data, count=n_samples)
    verified = [c for c in candidates if autoharness_verify(c, task_data)]
    return verified
```

2. **Kaggle Kernel Dual-GPU Dispatch**:
```python
def kaggle_dual_gpu_dispatch(task, time_budget=120.0):
    # GPU 0: DeepSeek R1 Reasoning (15GB VRAM)
    # GPU 1: Qwen Coder Synthesizer (15GB VRAM)
    # CPU: Fast AST Invariant Verification (30GB RAM)
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        f0 = executor.submit(reasoning_pass, task, "cuda:0")
        f1 = executor.submit(coding_pass, task, "cuda:1")
        for f in [f0, f1]:
            candidate = f.result()
            if candidate and autoharness_verify(candidate, task):
                return candidate
    return default_heuristic(task)
```

## VERSION
v1.0

## SEE ALSO
- `KAGGLE_HETEROGENEOUS_SWARM_PRIME`
- `KAGGLE_OFFLINE_AGENT_MODEL_HARNESS_PRIME`
- `AUTOHARNESS_POLICY_PRIME`
