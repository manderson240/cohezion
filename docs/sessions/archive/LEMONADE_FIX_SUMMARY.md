# Lemonade Local Models Response Rate - Autoresearch Summary

## Executive Summary

**Status**: ⚠️ **BLOCKED** - ROCm compatibility issue with AMD Radeon 8060S (gfx1151)

**Recommendation**: Use **Ollama** for immediate needs while pursuing Lemonade fix

---

## Findings (2 Experiments)

### Experiment 1: Baseline
- Result: 0 TPS (server connects but model load fails)
- Issue: `llama-server` hangs on `common_init_result: fitting params to device memory`
- GPU: AMD Radeon 8060S Graphics (gfx1151, Strix Halo)
- ROCm: Detected but incompatible architecture

### Experiment 2: Backend Switch Attempt  
- Changed config: `~/.config/lemonade/config.toml` → `backend = "vulkan"`
- Result: Lemonade still uses ROCm (ignores config)
- CLI timeout: 30 seconds insufficient for model loading

---

## Available Models (Downloaded)

| Model | Size | Status |
|-------|------|--------|
| Gemma-4-E2B-it | 3.1 GB | ✅ Downloaded |
| Gemma-4-E4B-it | 5.0 GB | ✅ Downloaded |
| Gemma-4-26B-A4B-it | 16.9 GB | ✅ Downloaded |
| Gemma-4-31B-it | 18.3 GB | ✅ Downloaded |

---

## Current State

### What's Working:
- ✅ Lemonade Server: `http://localhost:13305`
- ✅ Ollama Server: `http://localhost:11434` (Alternative)
- ✅ Ollama has: `gemma4:e2b`, `gemma4:e4b` (7.2GB, 9.6GB)

### What's Not Working:
- ❌ Lemonade ROCm backend on gfx1151
- ❌ Model loading times out at 30s
- ❌ Config file backend change ignored

---

## Recommended Fix Path

### Option 1: Use Ollama (Immediate)
```bash
# Already running on port 11434
ollama run gemma4:e4b
# Response rate: ~25-35 TPS expected on Strix Halo
```

### Option 2: Fix Lemonade (Requires Development)

**Root Cause**: llama.cpp ROCm backend needs gfx1151 support

**Potential Solutions**:
1. Update Lemonade's llama.cpp binary with gfx1151 support
2. Force Vulkan backend in Lemonade code
3. Wait for Lemonade update with gfx1151 support

**Code Location**:
```
~/.cache/lemonade/bin/llamacpp/rocm/llama-server
```

### Option 3: Custom Build (Advanced)
```bash
# Build llama.cpp with gfx1151 support
export AMDGPU_TARGETS="gfx1151"
# Rebuild Lemonade's llamacpp backend
```

---

## Next Steps

1. **Immediate**: Continue using Ollama for local models
2. **Short-term**: File issue with Lemonade SDK for gfx1151 support  
3. **Long-term**: Test Lemonade Vulkan backend when fixed

---

## Additional Model Research

### Prism ML Bonsai (1-bit models):
- `Bonsai-1.7B-gguf`: ~80M parameters - Ultra-fast NPU
- `Bonsai-4B-gguf`: ~188M parameters - Balanced
- `Bonsai-8B-gguf`: ~384M parameters - Best quality

### H Company Holo (Vision-Language):
- Holo1-3B/7B: GUI automation
- Holo2-4B/8B: Cross-platform agents
- Holo3-35B-A3B: State-of-the-art computer use

---

*Autoresearch session: 2 experiments, blocked by hardware compatibility*
