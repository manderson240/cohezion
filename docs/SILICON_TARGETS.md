---
title: Silicon targets — AMD local, CUDA remote
updated: 2026-10-21
---

# Silicon targets — AMD local, CUDA remote

Two different machines run our code, and each gets its own stack. Do not let one
leak into the other.

| Target | Where | Accelerator | Stack |
|---|---|---|---|
| **Local** | Strix Halo (Ryzen AI MAX+ 395, 128 GB unified) | NPU (XDNA2), iGPU (gfx1151), CPU (AVX-512) | Lemonade on :13305 → FLM (NPU), llama.cpp Vulkan/CPU. No CUDA, ever. |
| **Remote** | Kaggle / cloud GPU (T4, L4, Blackwell G4, …) | NVIDIA | The platform image's own CUDA torch. Our `uv.lock` is not used there. |

## Local (AMD) rules

- **Inference never goes through torch.** It goes through Lemonade (`:13305`, the
  admission proxy). Torch in the main venv is the **CPU** build on purpose
  (`[tool.uv.sources]` → `pytorch-cpu`); it keeps ~4.6 GB of CUDA libraries off
  the box.
- **Backend choice:** Vulkan beats ROCm llama.cpp on gfx1151 (measured ~32% lower
  TTFT, ~12–18% more tok/s) but ROCm uses ~25% less memory. The fleet is currently
  pinned to `llamacpp.backend=cpu` + FLM so the iGPU stays free for other work.
- **iGPU torch (finetuning)** needs AMD's gfx1151 wheels, in a **separate venv**:
  `uv pip install torch==2.11.0+rocm7.13.0 --index-url https://repo.amd.com/rocm/whl/gfx1151/`.
  **Untested here:** the wheel exists on that index (checked 2026-10-21), but it
  has not been installed or run on this iGPU yet. The old `torch==2.8.0+rocm6.3`
  recipe predates gfx1151 support; do not use it.
- **Never install the `unsloth` extra locally.** It pulls `bitsandbytes`,
  `xformers` and `triton`, which are CUDA-only.

### Memory (the OOM side)

Unified RAM is the binding constraint, not compute. What actually protects the box:

1. **The admission proxy floor** (`GET :13305/admission/status` → `floor_gb`, 25 GB
   as of 2026-10-21). It refuses LLM requests below the floor. Read it live; do
   not hardcode it.
2. **Lemonade idle eviction** (`evict_idle_timeout=300` per model) already unloads
   idle models after 5 minutes.
3. **App-level gating for non-LLM jobs.** numpy/torch jobs bypass the proxy, so
   gate them on `MemAvailable >= floor_gb + job_peak_gb`.

What does **not** protect the box:

- `MemoryMax` on `lemond.service`. GPU (GTT) memory is not charged to any cgroup.
- `max_loaded_models`. It caps count, not bytes.
- Lemonade `auto_evict` (currently off), until verified. **Unverified:** the
  `lemond` binary's strings suggest it measures through a GPU/GTT proxy
  (`get_available_memory_gb: CPU/NPU (AMD iGPU proxy)`), which may not track
  CPU-backend RAM use. Test it before relying on it.

On 2026-10-21 the pressure was mostly **not** inference: Chrome ~10 GB, the agy
daemon ~8 GB, Claude desktop ~7 GB, Konsole ~5 GB, and ~10 GB of agent scratch
files in the RAM-backed `/tmp` tmpfs. Inference held ~1 GB. The proxy had refused
more requests (58.6k) than it had forwarded (43k). Free those pools before blaming
the fleet.

## Remote (CUDA) rules

- Ship code that **detects** its device. Never assume CUDA in shared code:
  `device = "cuda" if torch.cuda.is_available() else "cpu"`.
- Rely on the platform image for torch/CUDA. Add only what is missing
  (`pip install` inside the kernel, or `model_sources`/dataset wheels offline).
- Match dtype and machine shape to the card using the `kaggle-critical-findings`
  checklist (not this doc). Blackwell G4 needs the handshake in the
  `kaggle-blackwell-handshake` skill.
- CUDA-only libraries (`unsloth`, `bitsandbytes`, `xformers`, `flash-attn`) belong
  in the kernel's own install step, not in our lockfile's default set.
- Use the local box for what it is good at: offline search/simulation on 32 AVX-512
  threads and large-memory inference to precompute artifacts. Then ship a small
  artifact to the CUDA runtime.

## Version state (2026-10-21)

| Component | Installed | Latest | Note |
|---|---|---|---|
| Lemonade | 2026.42.1 | 2026.42.1 | current |
| FLM (system) | 1.0.9 | 1.0.9 | Lemonade uses its own bundled **1.0.7** (`flm.prefer_system=false`); 1.0.8/1.0.9 add `minicpm-v-4.7:1b` + a `flm validate` fix, no speed changes. Wait for Lemonade's pin bump. |
| llama.cpp (Lemonade) | b11393 (cpu/vulkan), b11395 (rocm) | b11799 | Lemonade owns this pin; do not swap binaries by hand. |
| amd-gaia | 0.25.0 (this branch) | 0.25.0 | `LemonadeClient` lost `ready`/`set_params` (unused here). New latent hazards: `launch_server()` can kill a Python listener on its port (our :13305 proxy is Python), and `embeddings()` re-pins GAIA's default embedder to the GPU. We call neither. |
| torch (venv) | 2.14.1+cpu | — | intentional CPU build |
