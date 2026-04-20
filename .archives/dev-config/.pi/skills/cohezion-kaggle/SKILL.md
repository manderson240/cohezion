---
name: cohezion-kaggle
description: Work with Kaggle competitions, notebooks, and datasets in the Cohezion system. Covers Blackwell GPU handshake, kernel push, competition submission, and credential management.
---

# Cohezion Kaggle Workflow

## Blackwell Handshake (CRITICAL)
When orchestrating jobs on Kaggle G4 (Blackwell) infrastructure:
1. **Metadata**: Set `"machine_shape": "NvidiaRtxPro6000"` and `"dockerImageVersionId": 31287` in internal `.ipynb` metadata
2. **Environment**: Copy `nvidia_utility_script` to `/tmp` and `chmod +x` the `ptxas-blackwell` binary
3. **Triton**: Set `os.environ["TRITON_PTXAS_PATH"]` to the `/tmp` binary path
4. **Auth**: Pre-authorize models in the `"model_sources"` metadata array

## Quick Commands
```bash
# Check Kaggle auth
uv run python -c "from kaggle.api.kaggle_api_extended import KaggleApi; KaggleApi().read_config_file(); print('Auth OK')"

# Push notebook
uv run python scripts/push_kaggle_kernel.py

# Check competition leaderboard
uv run python check_leaderboard.py
```

## Hardware Profile
- **NEVER assume RTX/CUDA** — This is AMD Ryzen AI MAX+ 395 only
- **GPU**: Radeon 8060S (iGPU, unified memory, ROCm)
- **RAM**: 128 GiB LPDDR5X (unified CPU/GPU)

## Cost Routing
- 70% simple → Ollama/Flash-Lite (free)
- 20% medium → Sonnet ($3/M)
- 10% hard → Opus ($15/M)
- **Kaggle compute is free** — prefer for long-running training