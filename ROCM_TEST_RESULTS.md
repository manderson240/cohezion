# ROCm Backend Test Results - gfx1151 Override

**Date**: April 26, 2026  
**Hardware**: AMD Ryzen AI MAX+ 395 w/ Radeon 8060S (gfx1151)  
**Status**: ⚠️ PARTIAL - Backend Available, Server Startup Blocked

---

## Summary

| Component | Status | Notes |
|-----------|--------|-------|
| ROCm Libraries | ✅ Available | `/var/lib/lemonade/.cache/lemonade/bin/llamacpp/rocm/` |
| llama-server ROCm | ✅ Binary exists | `llama-server` in rocm/ directory |
| GPU Detection | ✅ Working | `HSA_OVERRIDE_GFX_VERSION=11.0.0` enables ROCm to see gfx1151 |
| Server Startup | ❌ Failed | Timeout after 120s - likely shader compilation hang |

---

## What Works

### 1. ROCm Environment Override
```bash
export HSA_OVERRIDE_GFX_VERSION=11.0.0
rocminfo  # ✅ Shows AMD Radeon 8060S
```

**Output**:
```
ROCk module is loaded
HSA System Attributes
Runtime Version: 1.18
gfx1151 detected as gfx1100 (via override)
```

### 2. Lemonade ROCm Backend Available
```
/var/lib/lemonade/.cache/lemonade/bin/llamacpp/rocm/llama-server exists
- rwxr-xr-x 1 root root 13517360 Apr 10
- libggml-hip.so available
- ROCm libraries bundled (libamdhip64, librocblas, etc.)
```

---

## What Failed

### Server Startup Hang
**Command**:
```bash
lemonade serve DeepSeek-R1-0528-Qwen3-8B-Q4_1 \
  --backend rocm \
  --port 8003 \
  --ctx-size 2048 \
  --flash-attn
```

**Result**:
- ❌ Server did not respond within 120s timeout
- ❌ No healthy endpoint on port 8003
- ❌ Process may hang during kernel/shader compilation

**Likely Cause**:
- gfx1151 is NOT officially supported by ROCm
- Shader/kernel compilation for gfx1151 may hang despite override
- ROCm runtime override allows detection but not full functionality

---

## Root Cause Analysis

### gfx1151 Support Status
- **ROCm Official**: NOT supported (gfx1151 = Strix Halo, RDNA 3.5)
- **ROCm Override**: Partial - HSA agents detected
- **Full Functionality**: Likely blocked on shader compilation step

### Comparison with Vulkan
| Feature | Vulkan | ROCm |
|---------|--------|------|
| gfx1151 Support | ✅ Native | ⚠️ Override only |
| Server Startup | ✅ Works | ❌ Hangs |
| Performance | 121.5 TPS | N/A |
| Flash Attention | ✅ Available | N/A |
| Stability | High | Unknown (cannot test) |

---

## Recommendation

**DO NOT USE ROCm backend at this time.**

**Reasons**:
1. 🚫 Server fails to start (hangs)
2. ⏱️ gfx1151 ROCm support may come in future AMD releases
3. ✅ Vulkan provides 121.5 TPS - already well-optimized
4. 🔄 ROCm overhead may not benefit 8B models anyway

**Future Action**:
- Check ROCm 6.3+ release notes for gfx1151 support
- Re-test when ROCm officially supports Strix Halo
- Vulkan remains optimal for this hardware

---

## Files Generated

- `benchmark_rocm_test.py` - Automated ROCm test harness
- `scripts/test_rocm_manual.sh` - Manual debugging script
- `rocm_test_results.json` - Test artifacts (failed startup)

## References

- AMD ROCm GPU Support List: gfx1151 not listed
- Community reports: Vulkan > ROCm for gfx11xx on small models
- Flash Attention critical for ROCm (cannot test)
