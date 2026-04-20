# Lemonade SDK Integration Guide - GFX1151 Fix Implementation

**Date**: 2026-04-10  
**Status**: Implementation path identified

## What We Downloaded

The Lemonade SDK nightly (`llama-b1236-ubuntu-rocm-gfx1151-x64.zip`) contains:
- `libggml-hip.so` - Optimized HIP/ROCm backend for gfx1151
- `libllama.so` - Core llama.cpp library with gfx1151 optimizations
- ROCm libraries (`librocblas.so`, `librocroller.so`, etc.)
- **Note**: This is a **library package**, not standalone binaries

## Implementation Options

### Option 1: Replace Lemonade Server Libraries (Recommended)

The SDK libraries need to replace the ones in Lemonade Server's bundled llama.cpp:

```bash
# Back up original libraries
sudo cp /var/lib/lemonade/.cache/lemonade/bin/llamacpp/rocm/libggml-hip.so \
  /var/lib/lemonade/.cache/lemonade/bin/llamacpp/rocm/libggml-hip.so.backup

# Extract SDK libraries
cd /tmp/lemonade-sdk-gfx1151

# Copy to Lemonade's ROCm backend directory
sudo cp libggml-hip.so libllama.so libggml*.so \
  /var/lib/lemonade/.cache/lemonade/bin/llamacpp/rocm/

# Restart Lemonade server
sudo systemctl restart lemonade-server
```

### Option 2: Build llama.cpp from Source

If Option 1 doesn't work, build from source with specific optimizations:

```bash
# Clone latest llama.cpp
git clone https://github.com/ggml-org/llama.cpp
cd llama.cpp

# Configure with gfx1151 optimizations
cmake -B build \
  -DGGML_HIP=ON \
  -DAMDGPU_TARGETS="gfx1151" \
  -DGGML_HIP_ROCWMMA_FATTN=ON \
  -DCMAKE_BUILD_TYPE=Release

# Build
cmake --build build --config Release -j$(nproc)

# Result: Working llama-server binary in build/bin/
```

### Option 3: Use Standalone llama.cpp

Run llama.cpp directly without Lemonade Server wrapper:

```bash
# After building from source (Option 2)
./build/bin/llama-server \
  -m /path/to/model.gguf \
  -ngl 99 \
  -fa on \
  --no-mmap \
  --port 8080

# Connect via OpenAI-compatible API
# Endpoint: http://localhost:8080
```

## Verification Steps

### 1. Check Library Versions
```bash
# Verify optimized libraries are in place
ls -la /var/lib/lemonade/.cache/lemonade/bin/llamacpp/rocm/*.so

# Check library linking
ldd /var/lib/lemonade/.cache/lemonade/bin/llamacpp/rocm/llama-server | grep ggml
```

### 2. Test Model Loading
```bash
# Via Lemonade CLI
lemonade load Qwen3-0.6B-GGUF --llamacpp rocm --ctx-size 4096

# Or via API
curl -X POST http://localhost:13305/api/v1/load \
  -H "Content-Type: application/json" \
  -d '{"model_name": "Qwen3-0.6B-GGUF", "llamacpp_backend": "rocm"}'
```

### 3. Verify Performance
```bash
# Check if ROCWMMA is active (look for rocWMMA in logs)
tail -f ~/.cache/lemonade/lemonade.log

# Expected output should show:
# - "ggml_cuda_init: found 1 ROCm devices"
# - "Device 0: AMD Radeon Graphics, gfx1151"
# - Flash Attention enabled messages
```

## Expected Performance Improvements

With the SDK libraries/optimized build:

| Model | Before (bundled) | After (optimized) | Improvement |
|-------|------------------|-------------------|-------------|
| Qwen3.5 35B | Hangs | ~25-35 TPS | ✅ Working |
| Qwen3.5 122B | Hangs | ~15-20 TPS | ✅ Working |
| Gemma 4 E2B | Hangs | ~25-35 TPS | ✅ Working |

With ROCWMMA Flash Attention (`-fa on`):
- **2x faster prompt processing**
- **70% faster at long context** (up to 96% improvement at 32K tokens)

## Rollback Procedure

If issues occur:

```bash
# Restore original libraries
sudo cp /var/lib/lemonade/.cache/lemonade/bin/llamacpp/rocm/libggml-hip.so.backup \
  /var/lib/lemonade/.cache/lemonade/bin/llamacpp/rocm/libggml-hip.so

# Restart service
sudo systemctl restart lemonade-server
```

## Important Notes

1. **NPU Still Works**: FLM NPU remains unaffected (`flm validate` still passes)
2. **Hybrid Execution**: Full NPU+GPU hybrid only works on Windows (`ryzenai-llm`)
3. **Linux Limitation**: On Linux, NPU and GPU are separate backends - choose one per model load
4. **Memory**: Large models (>26B) require significant RAM/VRAM. With 128GB unified memory, you can run up to ~120B models.

## Next Steps

1. **Try Option 1 first** (library replacement) - lowest effort
2. If that fails, **build from source** (Option 2) - more control
3. Use **standalone llama.cpp** (Option 3) if you want to bypass Lemonade Server entirely
4. **Monitor**: Watch for Lemonade Server updates beyond 10.2.0 that should include these fixes

## References

- Lemonade SDK Releases: https://github.com/lemonade-sdk/llamacpp-rocm/releases
- llama.cpp Build Docs: https://github.com/ggml-org/llama.cpp/blob/master/docs/build.md
- AMD Strix Halo Guide: https://www.amd.com/de/developer/resources/technical-articles/2026/how-to-run-a-one-trillion-parameter-llm-locally-an-amd.html

---

**Downloaded SDK Location**: `/tmp/lemonade-sdk-gfx1151/`  
**Original Libraries Backup**: (see Option 1 above)  
**Status**: Ready for implementation
