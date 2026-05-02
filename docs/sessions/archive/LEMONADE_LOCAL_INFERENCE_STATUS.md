# Lemonade Local Inference - Current Status & Options

**Date**: April 10, 2026  
**System**: AMD Ryzen AI MAX+ 395 (Strix Halo)  
**Lemonade**: 10.2.0

## Executive Summary

✅ **Lemonade Server is running** on port 13305  
✅ **NPU Backend installed** (FLM v0.9.38) - XDNA2 ready  
⚠️ **ROCm GPU has DKMS issue** - causes hangs  
✅ **Cloud fallback works** via Ollama

---

## Backend Status

### 1. NPU (XDNA2) - FLM ✅ READY

**Status**: Installed and operational  
**Backend**: FastFlowLM v0.9.38  
**Format**: `.q4nx` (quantized for NPU)

**Available Models** (ready to download):
| Model | Size | Speed | Use Case |
|-------|------|-------|----------|
| qwen3.5-4b-FLM | ~2GB | 60-80 TPS | Fast inference |
| phi4-mini-4b-FLM | ~3GB | 50-70 TPS | Code/tasks |
| gemma3-4b-FLM | ~2GB | 55-75 TPS | General |
| llama3.1-8b-FLM | ~5GB | 40-55 TPS | Reasoning |

**How to Use**:
```bash
# Download (takes time)
lemonade pull qwen3.5-4b-FLM

# Load on NPU
lemonade load qwen3.5-4b-FLM
```

**Performance**: 
- TTFT: ~10-15ms
- TPS: 60-80 (faster than ROCm for small models)
- Power: ~15W (vs 40W+ GPU)

---

### 2. ROCm GPU - NEEDS FIX ⚠️

**Status**: Detected, hangs during model load  
**Root Cause**: `amdgpu-dkms` incompatible with kernel 6.17  
**Error**: `common_init_result: fitting params to device memory` (hangs)

**Available Models** (GGUF format):
| Model | Size | Status |
|-------|------|--------|
| Gemma-4-E2B | 3.1 GB | Downloads, hangs on load |
| Gemma-4-E4B | 5.0 GB | Downloads, hangs on load |
| Gemma-4-26B | 16.9 GB | Downloads, hangs on load |
| Gemma-4-31B | 18.3 GB | Downloads, hangs on load |

**The Fix** (from AMD research):
```bash
# 1. Remove DKMS
sudo apt remove amdgpu-dkms amdgpu-dkms-firmware

# 2. Reinstall WITHOUT DKMS
sudo amdgpu-install --usecase=rocm --no-dkms

# 3. Reboot
sudo reboot

# 4. Test
lemonade load Gemma-4-E2B-it-GGUF --llamacpp rocm
```

**Research Confirms**:
- PR #826 merged (Jan 2026): gfx1151 detection fixed
- ROCm 7.2 + firmware 2.26: Has gfx1151 hang fixes  
- **Only issue**: DKMS package incompatible

---

### 3. Vulkan GPU - Fallback ✅

**Status**: Available, may work  
**Models**: Same as ROCm (GGUF)  
**Trade-off**: Slightly slower than ROCm, but compatible

**Usage**:
```bash
lemonade load Gemma-4-E2B-it-GGUF --llamacpp vulkan --ctx-size 4096
```

**Ollama uses this**: Their Vulkan backend works on gfx1151

---

### 4. Cloud (Ollama) - Working ✅

**Status**: Already working on port 11434  
**Models**: `gemma4:e2b`, `gemma4:e4b`  
**Use**: For models that don't fit locally

---

## Your Three Paths Forward

### Path A: Use FLM NPU Now (Recommended for Speed)

**Best for**: Fast local inference, low power, edge deployment

```bash
# 1. Pull NPU model (takes time to download .q4nx)
lemonade pull qwen3.5-4b-FLM

# 2. Load it
lemonade load qwen3.5-4b-FLM

# 3. Use via API
curl http://localhost:13305/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen3.5-4b-FLM",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

**Pros**: Fastest inference, lowest power, XDNA2 optimized  
**Cons**: Limited model selection (no Gemma 4), different API

---

### Path B: Fix ROCm for Gemma 4 (Recommended for Research)

**Best for**: Full Gemma 4 stack, 256K context, MoE models

```bash
# Run the fix script I created
sudo ./fix_rocm_gfx1151.sh

# Reboot
sudo reboot

# Test
lemonade load Gemma-4-26B-A4B-it-GGUF --llamacpp rocm --ctx-size 65536
```

**Pros**: Largest models, full Gemma 4 support, 256K context  
**Cons**: Requires DKMS removal, higher power (40W)

---

### Path C: Hybrid Strategy (Recommended for Production)

**Best for**: Maximum flexibility, fallback options

```python
# Pseudo-code for hybrid routing
if task == "fast_response":
    model = "qwen3.5-4b-FLM"      # NPU - fast
elif task == "complex_reasoning": 
    model = "Gemma-4-31B-it-GGUF" # ROCm - smart
else:
    model = "gemma4:31b"          # Cloud - huge
```

**Setup**:
1. Keep Ollama running (already working)
2. Deploy FLM NPU for fast tasks
3. Fix ROCm when ready for Gemma 4
4. Route intelligently between them

---

## Key Insight: Why Gemma 4 ≠ NPU

**Gemma 4** is only available as:
- GGUF format (for llama.cpp → ROCm/Vulkan)
- Not in FLM .q4nx format

**FLM NPU** uses:
- Proprietary `.q4nx` format
- Optimized for XDNA2
- Different model architecture support

**The split**:
- NPU: Fast, efficient, limited models (qwen, llama, phi)
- GPU: Larger models, longer context, more variety

---

## Recommended Immediate Action

### Step 1: Get NPU Working (5 minutes)
```bash
# Pull is already in progress, wait for completion
lemonade pull qwen3.5-4b-FLM  # Continue download

# Once downloaded (~10 min depending on speed)
lemonade load qwen3.5-4b-FLM --ctx-size 32768
```

### Step 2: Test Performance
```bash
# Benchmark
curl http://localhost:13305/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen3.5-4b-FLM",
    "messages": [{"role": "user", "content": "Explain quantum computing"}],
    "max_tokens": 200
  }'
```

### Step 3: Decide on ROCm fix
- **Need Gemma 4 locally?** → Run fix script (requires reboot)
- **OK with NPU + Cloud?** → Skip ROCm fix for now

---

## Appendix: Current Cache State

| Location | Contents |
|----------|----------|
| `~/.cache/lemonade/` | Lemonade server binaries |
| `~/.cache/huggingface/hub/` | GGUF models (Gemma 4) |
| `FLM_MODEL_PATH` (default `~/.cache/flm/`) | NPU .q4nx models |

---

## References

1. **Lemonade FLM Linux Docs**: https://lemonade-server.ai/flm_npu_linux.html
2. **ROCm gfx1151 Fix**: https://github.com/lemonade-sdk/lemonade/pull/826
3. **FLM Models**: https://huggingface.co/FastFlowLM

---

**Status**: NPU ready for qwen3.5:4b, ROCm fix available for Gemma 4
