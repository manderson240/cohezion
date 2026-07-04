---
date: 2026-06-04
project: cohezion
status: completed
outcome: success
tags: [experiment, dogfood, claims-verification, gaia]
---
# GAIA and HarnessPool Claims Dogfooding Verification

## Hypothesis
Executing `claim_kl_pool_and_gaia.py` will successfully verify deterministic local inference engine and adapter claims without raising errors.

## Results
- **Claim K**: HarnessPool successfully discovered installed harnesses on PATH (`hermes`, `opencode`, `pi`).
- **Claim L**: `rank_models_by_amd_optimization` correctly sorted model lists (NPU < iGPU < CPU < Cloud).
- **Claim M**: `amd_optimized_hierarchy` built a 4-tier local orchestrator with NPU Gemma-4-E2B-it-GGUF as the first tier.
- All verification steps passed successfully.
