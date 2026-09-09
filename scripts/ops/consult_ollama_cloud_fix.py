#!/usr/bin/env python3
"""Consult Tier 2 Ollama Cloud Fleet on Zero-Dependency GPU Inference Fix.

Queries `deepseek-v4-pro:cloud` and `qwen3.5:397b-cloud` on how to run fast GPU inference
in offline Kaggle kernels without missing package dependencies (e.g. `gptqmodel` or `autoawq`).
"""

import httpx
import json

prompt = """You are a Kaggle Systems Engineering & PyTorch Inference Grandmaster.
Problem:
In our offline Kaggle submission kernel ("enable_internet": "false", Dual NVIDIA T4 16GB GPUs, PyTorch 2.5 / CUDA 12.4), loading `hongbinguokaggle/deepseek-r1-distill-qwen-7b-awq` with `AutoModelForCausalLM.from_pretrained` failed with:
`Loading an AWQ quantized model requires gptqmodel. Please install it with pip install gptqmodel`

We want a 100% offline, zero-missing-dependency, bulletproof solution.
Options to consider:
1. Native `torch.float16` with unquantized 7B/1.5B model (e.g. `Qwen/Qwen2.5-Coder-1.5B-Instruct` or `Qwen2.5-Coder-7B-Instruct` directly in native PyTorch/Transformers without external C++ packages).
2. Pure PyTorch FP16/BF16 weights using standard transformers (built into Kaggle's default image).
3. Attaching pre-packaged wheels dataset or using standard Torch/Transformers native loading.

Provide:
1. The most reliable model source and native `from_pretrained` call that works out-of-the-box in offline Kaggle GPU kernels.
2. The exact Python loader code.
3. Updated `kernel-metadata.json` dataset/model sources.
Keep it concise, production-ready, and under 250 words."""

try:
    resp = httpx.post("http://127.0.0.1:11434/api/generate", json={
        "model": "deepseek-v4-pro:cloud",
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.1, "num_predict": 600}
    }, timeout=45.0)
    
    if resp.status_code == 200:
        data = resp.json()
        print("💡 OLLAMA CLOUD EXPERT SOLUTION:")
        print("=" * 80)
        print(data.get("response", ""))
        print("=" * 80)
    else:
        print(f"HTTP {resp.status_code}: {resp.text}")
except Exception as e:
    print(f"Notice: {e}")
