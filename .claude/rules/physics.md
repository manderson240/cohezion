---
paths:
  - "src/cohezion/physics/**"
  - "src/cohezion/universe/**"
  - "src/cohezion/simulation/**"
---

# Physics & Simulation Rules

- Ground all hardware assumptions in `.agent/HARDWARE_PROFILE_PRIME.md` — this system has NO discrete GPU, NO CUDA
- The GPU is AMD Radeon 8060S (RDNA 3.5 iGPU) with unified memory — use ROCm/HIP if GPU compute is needed
- Prefer `numpy` with AVX-512 flags or `ndarray` (Rust via PyO3) for compute-heavy paths
- `peaked_solver.py` is the reference for real physics implementation (tensor network quantum sim) — follow its patterns
- Universe simulation uses 12 dimensions: 3 Spatial + 1 Time + 8 Brane
- HIHO stability target: 0.5 coherence overlap — validate this invariant in tests
- Move compute-heavy simulations (QGP, magnetohydrodynamics) to Rust via PyO3 bindings when performance matters
- All simulation code must be sandboxed — use `SandboxManager.run_simulation()` for untrusted or generated physics code
