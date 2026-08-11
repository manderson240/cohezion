---
name: kaggle-blackwell-handshake
description: Kaggle G4 (Blackwell / NvidiaRtxPro6000) notebook handshake — required metadata, ptxas-blackwell environment setup, TRITON_PTXAS_PATH, and model_sources pre-authorization. Use when orchestrating any Kaggle job on G4/Blackwell infrastructure or when a Kaggle accelerator request fails.
---

# Kaggle Blackwell Handshake (Critical)

Moved verbatim from root `CLAUDE.md` on 2026-07-17 (doctor context-trim — loads on demand instead of every session).

When orchestrating jobs on Kaggle G4 (Blackwell) infrastructure, standard `accelerator` requests will fail. You MUST follow this handshake:
1.  **Metadata**: Set `"machine_shape": "NvidiaRtxPro6000"` and `"dockerImageVersionId": 31287` in the internal `.ipynb` metadata.
2.  **Environment**: Copy the `nvidia_utility_script` to `/tmp` and `chmod +x` the `ptxas-blackwell` binary.
3.  **Triton**: Set `os.environ["TRITON_PTXAS_PATH"]` to the `/tmp` binary path.
4.  **Auth**: Pre-authorize models in the `"model_sources"` metadata array.
