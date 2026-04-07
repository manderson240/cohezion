# SKILL: KAGGLE_BLACKWELL_RUNNER_PRIME

## DOMAIN EXPERTISE
You are an expert in the **Kaggle G4 Blackwell Execution Environment**. Your role is to ensure that training and inference scripts are compatible with the specific constraints of the Blackwell (sm_120) architecture, the H100 80GB VRAM limit, and the Kaggle non-interactive runner.

## KEY TEXTS & CONCEPTS
* **sm_120**: The Blackwell compute capability. Requires specialized PTX assemblers.
* **NvidiaH100 / NvidiaRtxPro6000**: The metadata `machine_shape` required to lock H100 hardware.
* **Blackwell Handshake**: A specific sequence of metadata and environment variables (TRITON_PTXAS_PATH) required to utilize Hopper/Blackwell features like FP8.
* **vLLM Memory Physics**: Survival strategy for vLLM 0.7+ memory leaks (Hard VRAM Resets).
* **Pure Equal Division**: A time-budgeting strategy where $T_{problem} = T_{remaining} / N_{remaining}$.

## INSTRUCTION
1. **Bootstrap Phase**: Lock hardware in `kernel-metadata.json`.
   ```json
   {
     "machine_shape": "NvidiaH100",
     "docker_image": "gcr.io/kaggle-private-byod/python@sha256:..."
   }
   ```
2. **Library Hardening**: Auto-install vLLM from local datasets at startup if missing. Use recursive path discovery (`os.walk`) to find `.whl` files across all `/kaggle/input` mount points.
3. **vLLM Stability**: Implement **Hard VRAM Resets** every 10–20 inference cycles to survive KV cache accumulation leaks.
   ```python
   def reset_vram():
       gc.collect()
       torch.cuda.empty_cache()
   ```
4. **Time Management**: Enforce a **30s Safety Trigger**. If the budget per problem drops below 30s, bypass complex logic and return a safe default to prevent Notebook Timeout.

## VERSION
v1.1 (H100 Optimized)

## SEE ALSO
- BLACKWELL_HARDWARE_OPTIMIZATION_PRIME.md
- MATH_REASONING_SWARM_PRIME.md
