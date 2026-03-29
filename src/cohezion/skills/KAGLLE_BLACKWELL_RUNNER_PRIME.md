# SKILL: KAGLLE_BLACKWELL_RUNNER_PRIME

## DOMAIN EXPERTISE
You are an expert in the **Kaggle G4 Blackwell Execution Environment**. Your role is to ensure that training and inference scripts are compatible with the specific constraints of the Blackwell (sm_120) architecture and the Kaggle non-interactive runner.

## KEY TEXTS & CONCEPTS
* **sm_120**: The Blackwell compute capability. Requires specialized PTX assemblers.
* **ptxas-blackwell**: The specific binary provided by NVIDIA to handle Blackwell compilation within Triton.
* **Non-Interactive Model Attachment**: Programmable kernels must pre-authorize models in the metadata or they cannot be downloaded via `kagglehub`.
* **Private BYOD Images**: Blackwell uses a specific Google Cloud Artifact Registry image (`gcr.io/kaggle-private-byod/...`).

## INSTRUCTION
1. **Bootstrap Phase**: Always copy `nvidia_utility_script` to `/tmp` and set `+x` permissions on `ptxas-blackwell`.
2. **Triton Patching**: Set `os.environ["TRITON_PTXAS_PATH"]` to the `/tmp` location of the blackwell binary.
3. **Mamba Compatibility**: If `mamba_ssm` fails with "no kernel image," patch `is_fast_path_available` to `False` to force the pure-PyTorch fallback, which is slower but functional on `sm_120`.
4. **Metadata Lock**: Ensure `"machine_shape": "NvidiaRtxPro6000"` and `"dockerImageVersionId": 31287` are set.

## VERSION
v1.0

## SEE ALSO
- BLACKWELL_HARDWARE_OPTIMIZATION_PRIME.md
- MOE_HYBRID_ENGINEERING_PRIME.md
