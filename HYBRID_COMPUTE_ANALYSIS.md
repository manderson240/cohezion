# Hybrid Compute Analysis - Complete Findings

## Current State

### What's Actually Running

| Service | Port | Model | Backend | Status |
|---------|------|-------|---------|--------|
| **Lemonade** | 13307, 8002 | Qwen3-8B | Vulkan (GPU) | ✅ Active |
| **Ollama** | 11434 | phi4-14B | Vulkan (GPU) | ⚠️ Also uses GPU |
| **NPU** | - | - | XDNA2 | ❌ Not available |
| **CPU** | - | - | Zen 5 | ❌ No models loaded |

### Key Discovery

**Both Lemonade and Ollama are using the SAME GPU!** They compete for:
- GPU compute units
- UMA memory bandwidth
- Vulkan context

This explains the terrible combined throughput (15.1 TPS vs 138.9 TPS solo).

## Performance Comparison

| Configuration | Throughput | Status |
|--------------|-----------|--------|
| Lemonade GPU only (optimal concurrency=4) | **138.9 TPS** | ✅ Best |
| Ollama GPU (phi4) | ~20-30 TPS | ⚠️ Competes with Lemonade |
| Combined (GPU contention) | **15.1 TPS** | ❌ 89% slower |
| CPU (no models loaded) | 0 TPS | ❌ Not configured |
| NPU | 0 TPS | ❌ Driver installed, device not exposed |

## Root Causes

### Problem 1: Ollama Uses GPU (Not CPU)
```
phi4:latest    19 GB    100% GPU     16384      4 minutes from now
```
Ollama auto-selected GPU for phi4. Need to force CPU mode for CPU benchmarks.

### Problem 2: NPU Not Available
```
# Driver installed
amdxdna-dkms  7.0.0-rc1  DKMS source for AMD XDNA NPU driver

# But device not exposed
ls /dev/xdna*  # No such file
```

Possible reasons:
- NPU disabled in BIOS
- Requires specific initialization
- Needs RyzenAI SDK (`ryzenai-ctrl` not found)

### Problem 3: CPU Mode Not Tested
With proper configuration:
- Small models (<3B) should run on CPU at 10-30 TPS
- Would allow true hybrid compute

## Recommendation

**DON'T run both Lemonade and Ollama simultaneously on the same GPU.**

### Optimal Configuration

**Option A: Lemonade GPU Only (Current Best)**
```python
# Use Lemonade with optimal concurrency=4
results = await asyncio.gather(*[
    lemonade_client.generate(p) for p in prompts[:4]
])  # 138.9 TPS
```

**Option B: True Hybrid (Requires Setup)**

1. **Configure Ollama for CPU-only**:
```bash
# In Ollama systemd service or config
OLLAMA_CPU_ONLY=1 ollama run llama3.2:1b
```

2. **Route small models to CPU**:
- llama3.2:1b (1B) → CPU
- phi4 (14B) → GPU (but won't fit with Qwen3)

3. **Keep large models on GPU**:
- Qwen3-8B → GPU via Lemonade

**Option C: NPU Enablement** (Future work)

1. Check BIOS for XDNA2 enablement
2. Install RyzenAI SDK
3. Quantize models for XDNA2 (ONNX format)
4. Expected: 60-80 TPS for small quantized models

## What We Learned

1. **GPU contention kills performance** - never run two GPU workloads
2. **NPU is installed but not active** - needs investigation
3. **CPU inference path not tested** - Ollama auto-selects GPU
4. **Current optimal: Single GPU workload at concurrency=4**

## Files Created

- `benchmark_hybrid_compute.py` - Multi-unit benchmark (GPU only working)
- `benchmark_hybrid_dual.py` - GPU+CPU simultaneous test (shows contention)
- `lemonade_client.py` - Production client (GPU optimal)

## Conclusion

The **138.9 TPS on GPU alone is optimal** for current configuration. Hybrid compute requires:
1. NPU enablement in BIOS/SW
2. CPU-only Ollama configuration
3. Proper model sizing (<3B for CPU, >3B for GPU)

**Current status**: Maximize GPU throughput with concurrency=4. Other compute units need additional setup.

---

*Analysis Complete: April 26, 2026*
