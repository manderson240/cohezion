# AMD Strix Halo Optimization Guide

## Hardware
- **CPU**: AMD Ryzen AI MAX+ 395 (Zen 5, 16C/32T)
- **GPU**: AMD Radeon 8060S (RDNA 3.5, gfx1151)
- **NPU**: AMD XDNA2 (50 TOPS)
- **Memory**: 128GB LPDDR5x UMA (Unified Memory Architecture)

## Current Status
| Backend | Status | Peak TPS | Concurrency |
|---------|--------|----------|-------------|
| GPU (Vulkan) | ✅ Working | 121.5 | 4 optimal |
| NPU (XDNA2) | ✅ Working | 12.5 | Sequential only |
| GPU (ROCm) | ⚠️ Needs unlock | Unknown | TBD |

## Locked Optimizations

### 1. ROCm/HIP Backend (Locked: gfx1151)
**Issue**: ROCm doesn't officially support gfx1151 (Strix Halo)
**Unlock**: Set `HSA_OVERRIDE_GFX_VERSION=11.0.0`

```bash
export HSA_OVERRIDE_GFX_VERSION="11.0.0"
export HIP_VISIBLE_DEVICES="0"
```

**Expected Gain**: 0-20% depending on model size
- Smaller models: May be slower due to overhead
- Larger models: ROCm often beats Vulkan for >7B params
- Flash Attention: Better on ROCm

### 2. Power Profile (Locked: User Permissions)
**Issue**: GPU runs in "auto" power-saving mode
**Unlock**: Requires sudo to set "high" performance profile

```bash
echo 'high' | sudo tee /sys/class/drm/card1/device/power_dpm_force_performance_level
```

**Expected Gain**: +5-10% TPS, more consistent clocks

### 3. RADV Cooperative Matrix (Locked: Not Enabled)
**Issue**: Vulkan AI optimizations not enabled by default
**Unlock**: Enable shader extensions

```bash
export RADV_PERFTEST="aco,gpl,rt,nggc"
export RADV_COOPERATIVE_MATRIX="1"
```

**Expected Gain**: +20-30% for matrix-heavy operations

### 4. KV Cache Quantization (Locked: Not Default)
**Issue**: KV cache uses F16 (2 bytes per token per layer)
**Unlock**: Quantize to Q8_0 (1 byte per token per layer)

```bash
--cache-type-k q8_0 --cache-type-v q8_0
```

**Expected Gain**: 2x context window, or 50% memory for same context

### 5. Flash Attention (Locked: Not Default)
**Issue**: Standard attention O(n²) complexity
**Unlock**: Enable Flash Attention

```bash
--flash-attn
```

**Expected Gain**: 2x speed for context >2K tokens

### 6. Memory-Mapped I/O (Locked: Default)
**Issue**: MMAP can be slower on UMA architecture
**Unlock**: Disable memory mapping

```bash
--no-mmap
```

**Expected Gain**: +5-10% TPS on UMA systems

## Quick Start

### Set Environment (User-level)
```bash
# AMD GFX1151 Unlock
export HSA_OVERRIDE_GFX_VERSION="11.0.0"

# Vulkan RADV Optimizations
export RADV_PERFTEST="aco,gpl,rt,nggc"
export RADV_COOPERATIVE_MATRIX="1"
export MESA_SHADER_CACHE_MAX_SIZE="4GB"

# Add to PATH
export PATH="/opt/rocm/bin:$PATH"
```

### Set Power Profile (Requires sudo)
```bash
sudo bash -c 'echo high > /sys/class/drm/card1/device/power_dpm_force_performance_level'
```

### Launch Optimized Server
```bash
lemonade serve DeepSeek-R1-0528-Qwen3-8B-Q4_1 \
  --backend vulkan \
  --port 8002 \
  --ctx-size 4096 \
  --cache-type-k q8_0 \
  --cache-type-v q8_0 \
  --flash-attn \
  --no-mmap \
  --context-shift \
  --reasoning-format auto \
  -ngl 99
```

## Scripts

### 1. Check Status
```bash
python3 scripts/amd_optimization_unlocker.py --check
```

### 2. Generate Environment Script
```bash
python3 scripts/amd_optimization_unlocker.py --env-script
source ~/.amd_optimize_env.sh
```

### 3. Launch Optimized Server
```bash
python3 scripts/lemonade_amd_optimized_launcher.py gpu
```

## Testing ROCm

ROCm compatibility with gfx1151 is **experimental**:

```bash
# Test ROCm detection
export HSA_OVERRIDE_GFX_VERSION="11.0.0"
rocminfo | grep "Name:"  # Should show gfx1151

# Try ROCm backend (if available)
lemonade serve DeepSeek-R1-0528-Qwen3-8B-Q4_1 \
  --backend rocm \
  --port 8003
```

**Known Issues**:
- May hang on ctx-size > 4096
- May be slower than Vulkan for small models
- Flash Attention critical for ROCm performance

## Benchmark Results

### Current (Vulkan, Default Settings)
- **Throughput**: 121.5 TPS @ concurrency=4
- **Per-Request**: 30.4 TPS
- **Latency**: ~40ms TTFT

### Expected (With Optimizations)

| Config | TPS | Gain |
|--------|-----|------|
| Base | 121.5 | - |
| +RADV_PERFTEST | 136 | +12% |
| +KV Q8_0 | 145 | +19% |
| +Flash Attention | 165 | +36% (for >2K ctx) |
| +Power Profile | 176 | +45% |

### ROCm Comparison (Hypothetical)
Based on community benchmarks (Llama.cpp on RDNA3):
- Vulkan: 700-800 tok/s prefill
- ROCm: 1000-1200 tok/s prefill (with Flash Attention)
- ROCm overhead: +50-100ms cold start

## Safety Checks

Before enabling optimizations:
```bash
# Monitor thermals
watch -n 5 cat /sys/class/hwmon/hwmon*/temp1_input

# Max temp: 85°C (throttling)
# Optimal: <75°C
```

## Troubleshooting

### ROCm Hangs
- Check `HSA_OVERRIDE_GFX_VERSION` is set correctly
- Reduce ctx-size to 2048
- Try without flash attention

### Lower TPS Than Expected
- Check power profile: `cat /sys/class/drm/card1/device/power_dpm_force_performance_level`
- Verify RADV_PERFTEST: `echo $RADV_PERFTEST`
- Check thermal throttling: `rocm-smi`

### OOM Errors
- Use KV cache quantization: `--cache-type-k q8_0`
- Reduce ctx-size: `--ctx-size 2048`
- Check available VRAM: Only 512MB visible to GPU (rest is UMA)
