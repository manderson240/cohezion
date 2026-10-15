# First Principles Invariant Rule

## Mandatory Policy
1. **Never Chase Leaderboard Noise**: Always verify physical and geometric invariants before submitting (e.g. Dihedral $D_4$ equivariance in ARC, mass conservation in spectrometry, gravitational load monotonicity in RSNA knee).
2. **Kaggle Code Competition Submission Protocol**: Code competitions strictly require notebook submissions. Always dispatch via `scripts/kaggle/kaggle_submit.py notebook` with `kernel_version`. Never upload raw local files.
3. **Silicon Discipline**: Zero large model loads on UMA iGPU/Vulkan/ROCm. Keep local inference on NPU (`FastFlowLM`) and CPU (`llamacpp`), reserving heavy loads for Kaggle Cloud / Ollama Cloud.
