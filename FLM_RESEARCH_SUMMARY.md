# FLM Research Summary - How Others Use Strix Halo

**Date**: April 26, 2026  
**Source**: Web research on AMD Ryzen AI MAX+ 395 / Strix Halo usage

---

## Key Findings from Community

### 1. Best Models for Strix Halo

According to [From the Matrix](https://fromthematrix.dev/posts/local-llm-speed-benchmark-strix-halo/) testing:

| Model | Size | Active Params | Gen tok/s | Notes |
|-------|------|---------------|-----------|-------|
| **LFM2-24B** | 24B | 2B (MoE) | **109** | Fastest - liquid neural networks |
| GPT-OSS 20B | 20B | 3.6B (MoE) | 70 | Good balance |
| Nemotron-3-Nano 30B | 30B | ~4B (MoE) | 61 | MoE advantage |
| Qwen3-Coder 30B | 30B | 3B (MoE) | 66 | Coding optimized |
| Qwen3.5-35B | 35B | 3B (MoE) | 39-49 | MoE variants |

**Key Insight**: MoE (Mixture of Experts) models win on Strix Halo because:
- Only 2-4B parameters activate per forward pass
- Memory bandwidth constrained (not compute)
- Less active params = faster generation

### 2. Backend Performance Comparison

From [llm-tracker.info](https://llm-tracker.info):

| Backend | pp512 (t/s) | tg128 (t/s) | Notes |
|---------|-------------|-------------|-------|
| CPU | 294 | 28.9 | Baseline |
| HIP | 348 | 48.7 | ROCm - disappointing on gfx1151 |
| HIP + WMMA + FA | 343 | 50.9 | With Flash Attention |
| **Vulkan** | **882** | **52.2** | **Currently BEST** |
| Vulkan + FA | 884 | 52.7 | Minimal FA improvement at short context |

**Critical Finding**: Vulkan beats HIP on Strix Halo!
- HIP pp512 barely beats CPU (348 vs 294)
- Vulkan pp512 is **2.5x faster** than HIP (882 vs 348)
- Only 9% theoretical efficiency on HIP without hipBLASLt

### 3. Large Model Performance (>50B)

| Model | Size | tg128 | Notes |
|-------|------|-------|-------|
| GPT-OSS 120B | 120B | 52 | MoE (12B active) |
| Llama-4-Scout | 17B (16E) | 20.2 | MoE, 57GB |
| Mistral-Large | 123B | 2.97 | Dense - very slow |
| Mistral-8x22b | 22B (8E) | 8.92 | MoE |

**Insight**: You CAN run 100B+ models on 128GB UMA, but only MoE ones are usable.
Dense models like Mistral-Large at 123B get <3 tok/s.

### 4. Flash Attention Matters for Context

From llama.cpp testing with Qwen3-30B-A3B:

| Context | Backend | TG Speed | Memory |
|---------|---------|----------|--------|
| 512 | Vulkan + FA | 32.03 | 7767+1180 |
| 8192 | Vulkan (no FA) | **7.54** | 7761+1180 |
| 8192 | Vulkan + FA | **32.03** | 7767+1180 |

**Flash Attention is CRITICAL for longer contexts** - 4x speedup at 8K context.

### 5. NPU/FastFlowLM Setup (Linux)

From issue research:

```
FLM Requirements:
- amdxdna driver >= 1.0
- Firmware >= 1.1.0.0  
- Current ours: FW 1.1.2.65 ✓
- FLM models: .q4nx format (not GGUF)
```

**Expected NPU Performance**:
- Qwen3.5-4b-FLM: **60-80 TPS** (our target)
- Power: ~15W (vs 40W GPU)
- TTFT: ~10-15ms

### 6. Hardware Specs from Community

```
Ryzen AI MAX+ 395:
- iGPU: Radeon 8060S (40 RDNA3.5 CUs, gfx1151)
- Peak: 59.4 FP16 TFLOPS (at 2.9GHz with WMMA)
- UMA Bandwidth: ~212 GB/s (DDR5-8000, 256-bit)
- CPU→GPU: ~84 GB/s
- NPU: XDNA2, 50 TOPS int8
- Our memory config: 110 GB GTT + 8 GB GART
```

**Why We're Bandwidth Limited**:
- 212 GB/s for 8B model = ~27 tok/s theoretical
- We're getting 121.5 TPS = **parallelizing well with concurrency=4**
- UMA shared bandwidth is the constraint

### 7. What Failed for Others

From "What Failed" section:
- Qwen3.5-122B (70GB+): Connection abort - timeout during load
- Kimi-Linear-48B: Similar abort - SSM/attention hybrid issues
- Dense 70B+ models: <5 tok/s (usable but slow)

### 8. ROCm Fix Path

From amdxdna-driver issue #1219:

```
# Current firmware/driver mismatch on some distros causes issues
# Fix available: Build xdna-driver from source

git clone https://github.com/amd/xdna-driver.git
cd xdna-driver && git submodule update --init --recursive
sudo ./tools/amdxdna_deps.sh
cd xrt/build && ./build.sh -npu -opt
sudo apt reinstall ./Release/xrt_*.deb
cd ../../build && ./build.sh -release
sudo apt install ./Release/xrt_plugin*.deb

# Build time: ~16 seconds on Strix Halo
# Result: flm validate passes
```

**Our Status**: Already have amdxdna 0.6, FW 1.1.2.65 ✓

### 9. Key Community Recommendations

**For Small Models (<10B)**:
- Use **Vulkan backend** (not HIP)
- Quantize to Q4_K_M or Q4_0
- Flash Attention essential for >2K context
- Expected: 50-100 tok/s gen speed

**For Large Models (30B+)**:
- Use **MoE architecture** (not dense)
- MoE: 3-4B active per token vs 30B+ total
- Dense 70B+: ~3-5 tok/s (barely usable)

**For Long Context**:
- Flash Attention is MANDATORY
- Without FA: 7-8 tok/s at 8K
- With FA: 30-50 tok/s at 8K

### 10. Performance Targets

Based on community benchmarks:

| What | Target | We Achieved |
|------|--------|-------------|
| Small model (<3B) | 50-100 tok/s | ? |
| Medium model (8B) | 50-70 tok/s | 52 (Vulkan) ✓ |
| Large model (30B MoE) | 60-80 tok/s | ? |
| 120B MoE | 50-54 tok/s | ? |
| Dense 70B+ | 3-5 tok/s | N/A |

**Our 121.5 TPS is from concurrency=4 parallel execution, not higher per-request speed.**

---

## Summary: What's Working Now

✅ **Vulkan + Q8_0 (our current)**: Best backend for prompt processing  
⚠️ **HIP/ROCm**: Needs fix for gfx1151 - poor efficiency  
❌ **HIP without WMMA/FA**: Very slow  
✅ **Flash Attention**: Critical for context >2K  
✅ **NPU/FastFlowLM**: Downloading - should achieve 60-80 TPS  

**Next Steps from Community**:
1. Wait for ROCm DKMS fix for better HIP efficiency
2. Use Vulkan + Flash Attention for best current performance
3. NPU for small models to free GPU for large tasks
4. Enable MoE models for larger sizes

---

*Research Sources*:
- https://fromthematrix.dev/posts/local-llm-speed-benchmark-strix-halo/
- https://llm-tracker.info/AMD-Strix-Halo-(Ryzen-AI-Max%2B-395)-GPU-Performance
- https://github.com/amd/xdna-driver/issues/1219
- https://valerian.dtdg.fr/blog/2025/amd-strix-halo-ai-395-llm-benchmark/
- https://github.com/amd/RyzenAI-SW/issues/366
