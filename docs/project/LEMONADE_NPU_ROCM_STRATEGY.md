# Lemonade NPU + ROCm Dual Strategy

## Current State (April 2025)

### Hardware Confirmed
- **CPU**: AMD Ryzen AI MAX+ 395 (16 cores)
- **GPU**: Radeon 8060S Graphics (gfx1151)
- **NPU**: XDNA2 (8 columns) - `/dev/accel/accel0` ✓
- **RAM**: 128GB Unified Memory

### Backend Status

| Backend | Status | Gemma 4 Support | Notes |
|---------|--------|-----------------|-------|
| **FLM NPU** | ✅ Working | ❌ Gemma 3 only | 2-4x faster for small models |
| **Lemonade ROCm** | ❌ Hanging | ✅ Downloaded | gfx1151 compatibility issue |
| **Lemonade Vulkan** | ❓ Untested | ✅ Yes | May work as fallback |
| **Ollama Cloud** | ✅ Working | ✅ Yes | For 31B+ models |

## Strategy: Tiered Model Deployment

### Tier 1: NPU (FLM) - Production Ready
```bash
# These work NOW with XDNA2 acceleration
flm pull gemma3:4b
flm pull qwen3.5:4b
flm pull llama3.1:8b
flm pull phi4-mini-it:4b

# Serve with NPU
flm serve gemma3:4b --ctx-len 32768 --port 13306
```

**Expected Performance**:
- Gemma 3:4b: ~60-80 TPS on NPU
- Context: Up to 32K tokens
- Power: ~15W (vs 40W+ on GPU)

### Tier 2: ROCm GPU (Lemonade) - Pending Fix
```bash
# Once gfx1151 resolved:
export HSA_OVERRIDE_GFX_VERSION=11.5.1
lemonade load Gemma-4-E2B-it-GGUF --llamacpp rocm --ngl 99
```

**Expected Performance**:
- Gemma 4 E2B: ~25-35 TPS on GPU
- Context: Up to 256K tokens
- Memory: Shared with NPU in UMA

### Tier 3: Cloud (Ollama) - Always Available
```bash
# For 31B+ models
ollama run gemma4:31b-cloud
```

## The gfx1151 Issue

### Root Cause
llama.cpp ROCm backend hangs during `common_init_result` memory fitting on gfx1151.

### Attempted Fixes
1. ✅ `HSA_OVERRIDE_GFX_VERSION=11.5.1` - No effect
2. ✅ `--fit off` - No effect
3. ❓ Update llama.cpp binary in Lemonade
4. ❓ Use `--verbose` flags for debugging

### Resolution Path
According to user: "Lemonade server said this has been resolved"
- Likely needs Lemonade Server update beyond 10.2.0
- Or specific configuration not yet applied

## Hybrid Architecture

```
┌──────────────────────────────────────────────────┐
│           Cohezion Swarm Controller            │
├────────────┬────────────┬────────────┬─────────┤
│  FLM NPU   │  Lemonade  │  Ollama    │  Cloud  │
│  (XDNA2)   │  (ROCm)    │  (Local)   │  (API)  │
├────────────┼────────────┼────────────┼─────────┤
│ gemma3:4b  │ gemma4-e2b │ gemma4:e2b │ 31B+    │
│ qwen3.5:4b │ gemma4-e4b │ gemma4:e4b │ etc     │
│ llama3.1:8b│ gemma4-26b │            │         │
│ phi4-mini  │ gemma4-31b │            │         │
└────────────┴────────────┴────────────┴─────────┘
```

### Model Routing Logic
```python
if prompt_tokens < 1000 and model_size <= 4e9:
    return "flm://gemma3:4b"       # NPU - fastest
elif "gemma-4" in model_id:
    if rocm_working:
        return "lemonade://Gemma-4-E2B"  # GPU
    else:
        return "ollama://gemma4:e2b"     # Fallback
else:
    return "ollama://cloud"            # Cloud
```

## Immediate Actions

### 1. Deploy FLM NPU Now
```bash
# Install FLM models
flm pull gemma3:4b
flm pull qwen3.5:4b

# Start NPU server
flm serve gemma3:4b --port 13306 --ctx-len 32768
```

### 2. Test Lemonade Update
```bash
# Check for updates
lemonade --version  # Currently 10.2.0
# If update available:
# sudo apt update && sudo apt install lemonade
```

### 3. Verify ROCm Fix
```bash
# After Lemonade update, test:
lemonade load Gemma-4-E2B-it-GGUF --llamacpp rocm

# Check logs for success:
tail -f ~/.cache/lemonade/lemonade.log
```

## Performance Targets

| Model | Backend | Context | TPS | TTFT |
|-------|---------|---------|-----|------|
| Gemma 3:4b | FLM NPU | 32K | 60-80 | ~15ms |
| Gemma 4 E2B | ROCm | 256K | 25-35 | ~40ms |
| Gemma 4 31B | Cloud | 128K | 8-12 | ~150ms |

## Decision Tree

```
User Query
    │
    ├─── Context > 100K ───→ Gemma 4 E2B (ROCm/Cloud)
    │
    ├─── Fast response ───→ FLM NPU (Gemma 3:4b)
    │
    ├─── Code generation ───→ Qwen3.5:4b (FLM) or GPT-4 Cloud
    │
    └─── Research/Analysis ───→ Gemma 4 31B (Cloud)
```

## Next Steps

1. **Deploy FLM NPU** immediately for 4B-class models
2. **Update Lemonade** to get ROCm gfx1151 fix
3. **Test hybrid routing** between NPU/GPU/Cloud
4. **Monitor for Gemma 4** support in FLM NPU

---
*Status: FLM NPU operational, ROCm pending gfx1151 fix*
